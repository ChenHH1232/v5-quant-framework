from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.date_utils import parse_iso_date_or_none
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import to_float


EV_NBV_FIELDS = {"embedded_value", "new_business_value"}
PANEL_EXTRA_FIELDS = [
    "embedded_value",
    "embedded_value_visible_date",
    "embedded_value_report_period",
    "embedded_value_source_url",
    "new_business_value",
    "new_business_value_visible_date",
    "new_business_value_report_period",
    "new_business_value_source_url",
    "price_to_embedded_value",
    "price_to_new_business_value",
    "embedded_value_yoy",
    "new_business_value_yoy",
    "ev_nbv_repair_status",
]


def build_insurance_ev_nbv_panel(
    panel_csv: Path,
    ev_nbv_csv: Path,
    out_dir: Path,
    *,
    strategy_id: str = "insurance_pev_nbv_v53f",
    min_coverage_ratio: float = 0.8,
    min_validation_years: int = 4,
) -> Path:
    panel_rows = read_csv_rows(panel_csv)
    evidence_rows = _usable_evidence_rows(read_csv_rows(ev_nbv_csv))
    evidence_by_code_field = _evidence_by_code_field(evidence_rows)
    enriched_rows = [_enrich_panel_row(row, evidence_by_code_field) for row in panel_rows]
    coverage_rows = _coverage_rows(enriched_rows)
    summary = _summary(
        panel_csv,
        ev_nbv_csv,
        enriched_rows,
        coverage_rows,
        strategy_id,
        min_coverage_ratio,
        min_validation_years,
    )

    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)
    fieldnames = _merged_fieldnames(panel_rows, PANEL_EXTRA_FIELDS)
    write_csv_rows(out / "panel_with_ev_nbv.csv", fieldnames, enriched_rows)
    write_csv_rows(out / "panel_with_ev_nbv_covered_only.csv", fieldnames, _covered_only_rows(enriched_rows))
    write_csv_rows(out / "ev_nbv_coverage_by_date.csv", _coverage_fieldnames(), coverage_rows)
    write_json_file(out / "ev_nbv_panel_summary.json", summary)
    (out / "ev_nbv_panel_report.md").write_text(_render_report(summary), encoding="utf-8")
    return out / "ev_nbv_panel_report.md"


def _usable_evidence_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    usable = []
    for row in rows:
        if row.get("field") not in EV_NBV_FIELDS:
            continue
        if (row.get("pit_status") or "").strip().lower() != "pit_usable":
            continue
        if (row.get("original_announcement_checked") or "").strip().lower() != "true":
            continue
        if (row.get("review_status") or "").strip().lower() != "reviewed":
            continue
        if to_float(row.get("value")) is None:
            continue
        if parse_iso_date_or_none(row.get("visible_date")) is None:
            continue
        if parse_iso_date_or_none(row.get("report_period")) is None:
            continue
        usable.append(row)
    return usable


def _evidence_by_code_field(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    result: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        result[(row["code"], row["field"])].append(row)
    for values in result.values():
        values.sort(key=lambda row: (row.get("visible_date", ""), row.get("report_period", "")))
    return dict(result)


def _enrich_panel_row(row: dict[str, str], evidence_by_code_field: dict[tuple[str, str], list[dict[str, str]]]) -> dict[str, Any]:
    enriched: dict[str, Any] = dict(row)
    trade_date = parse_iso_date_or_none(row.get("trade_date"))
    code = row.get("code", "")
    latest_by_field = {}
    for field in EV_NBV_FIELDS:
        latest = _latest_visible(evidence_by_code_field.get((code, field), []), trade_date)
        latest_by_field[field] = latest
        if latest:
            enriched[field] = latest["value"]
            enriched[f"{field}_visible_date"] = latest.get("visible_date", "")
            enriched[f"{field}_report_period"] = latest.get("report_period", "")
            enriched[f"{field}_source_url"] = latest.get("source_url", "")
        else:
            enriched[field] = ""
            enriched[f"{field}_visible_date"] = ""
            enriched[f"{field}_report_period"] = ""
            enriched[f"{field}_source_url"] = ""

    market_cap = to_float(row.get("market_cap"))
    ev = to_float(enriched.get("embedded_value"))
    nbv = to_float(enriched.get("new_business_value"))
    enriched["price_to_embedded_value"] = _ratio_market_cap_to_value(market_cap, ev)
    enriched["price_to_new_business_value"] = _ratio_market_cap_to_value(market_cap, nbv)
    enriched["embedded_value_yoy"] = _growth_vs_previous(latest_by_field["embedded_value"], evidence_by_code_field.get((code, "embedded_value"), []))
    enriched["new_business_value_yoy"] = _growth_vs_previous(latest_by_field["new_business_value"], evidence_by_code_field.get((code, "new_business_value"), []))
    enriched["ev_nbv_repair_status"] = "ev_nbv_pit_visible" if ev is not None and nbv is not None else "ev_nbv_missing_or_not_yet_visible"
    return enriched


def _latest_visible(rows: list[dict[str, str]], trade_date: Any) -> dict[str, str] | None:
    if trade_date is None:
        return None
    latest = None
    for row in rows:
        visible_date = parse_iso_date_or_none(row.get("visible_date"))
        if visible_date is not None and visible_date <= trade_date:
            latest = row
    return latest


def _ratio_market_cap_to_value(market_cap_100m: float | None, value_cny_million: float | None) -> float | str:
    if market_cap_100m is None or value_cny_million is None or value_cny_million <= 0:
        return ""
    return market_cap_100m * 100.0 / value_cny_million


def _growth_vs_previous(current: dict[str, str] | None, rows: list[dict[str, str]]) -> float | str:
    if current is None:
        return ""
    current_period = current.get("report_period", "")
    previous = [row for row in rows if row.get("report_period", "") < current_period]
    if not previous:
        return ""
    previous_row = sorted(previous, key=lambda row: row.get("report_period", ""))[-1]
    current_value = to_float(current.get("value"))
    previous_value = to_float(previous_row.get("value"))
    if current_value is None or previous_value is None or previous_value == 0:
        return ""
    return current_value / previous_value - 1.0


def _coverage_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_date[str(row.get("trade_date", ""))].append(row)
    result = []
    for trade_date, date_rows in sorted(by_date.items()):
        total = len(date_rows)
        ev_rows = [row for row in date_rows if to_float(row.get("embedded_value")) is not None]
        nbv_rows = [row for row in date_rows if to_float(row.get("new_business_value")) is not None]
        pev_rows = [row for row in date_rows if to_float(row.get("price_to_embedded_value")) is not None]
        result.append(
            {
                "trade_date": trade_date,
                "row_count": total,
                "embedded_value_rows": len(ev_rows),
                "new_business_value_rows": len(nbv_rows),
                "price_to_embedded_value_rows": len(pev_rows),
                "embedded_value_coverage_ratio": _ratio(len(ev_rows), total),
                "new_business_value_coverage_ratio": _ratio(len(nbv_rows), total),
                "price_to_embedded_value_coverage_ratio": _ratio(len(pev_rows), total),
                "covered_codes": ";".join(sorted(str(row.get("code", "")) for row in pev_rows if row.get("code"))),
            }
        )
    return result


def _covered_only_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if to_float(row.get("price_to_embedded_value")) is not None]


def _summary(
    panel_csv: Path,
    ev_nbv_csv: Path,
    rows: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
    strategy_id: str,
    min_coverage_ratio: float,
    min_validation_years: int,
) -> dict[str, Any]:
    covered_dates = [row for row in coverage_rows if float(row["price_to_embedded_value_coverage_ratio"]) >= min_coverage_ratio]
    covered_years = sorted({str(row["trade_date"])[:4] for row in covered_dates})
    status = (
        "ev_nbv_pev_panel_ready_for_formal_validation"
        if len(covered_years) >= min_validation_years
        else "ev_nbv_pev_panel_insufficient_history"
    )
    return {
        "strategy_id": strategy_id,
        "status": status,
        "panel_csv": str(panel_csv),
        "ev_nbv_csv": str(ev_nbv_csv),
        "row_count": len(rows),
        "date_count": len(coverage_rows),
        "covered_date_count": len(covered_dates),
        "covered_years": covered_years,
        "min_coverage_ratio": min_coverage_ratio,
        "min_validation_years": min_validation_years,
        "first_covered_date": covered_dates[0]["trade_date"] if covered_dates else "",
        "last_covered_date": covered_dates[-1]["trade_date"] if covered_dates else "",
        "formal_validation_allowed": status == "ev_nbv_pev_panel_ready_for_formal_validation",
        "pm_gate": "block_formal_validation_until_multi_year_pit_ev_nbv_history" if status.endswith("insufficient_history") else "quant_validation_allowed",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def _render_report(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Insurance EV/NBV/P/EV Panel Report",
            "",
            f"Status: `{summary['status']}`",
            "",
            f"- Rows: `{summary['row_count']}`",
            f"- Dates: `{summary['date_count']}`",
            f"- Covered dates above threshold: `{summary['covered_date_count']}`",
            f"- Covered years: `{', '.join(summary['covered_years']) if summary['covered_years'] else 'none'}`",
            f"- First covered date: `{summary['first_covered_date'] or 'none'}`",
            f"- Last covered date: `{summary['last_covered_date'] or 'none'}`",
            f"- Formal validation allowed: `{str(summary['formal_validation_allowed']).lower()}`",
            f"- PM gate: `{summary['pm_gate']}`",
            "",
            "This report checks whether repaired EV/NBV data is old and broad enough for PIT validation. It does not approve a strategy.",
            "",
        ]
    )


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _coverage_fieldnames() -> list[str]:
    return [
        "trade_date",
        "row_count",
        "embedded_value_rows",
        "new_business_value_rows",
        "price_to_embedded_value_rows",
        "embedded_value_coverage_ratio",
        "new_business_value_coverage_ratio",
        "price_to_embedded_value_coverage_ratio",
        "covered_codes",
    ]


def _merged_fieldnames(rows: list[dict[str, str]], extra: list[str]) -> list[str]:
    names = list(rows[0].keys()) if rows else []
    for name in extra:
        if name not in names:
            names.append(name)
    return names

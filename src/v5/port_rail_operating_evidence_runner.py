from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import fmt_float, to_float


DEFAULT_OUT_DIR = Path("\u6570\u636e\u5e93") / "processed" / "port_rail_operating_evidence_v55h"

SEGMENT_EVIDENCE_FIELDS = [
    "code",
    "ts_code",
    "report_period",
    "report_type",
    "notice_date",
    "visible_date",
    "selected_mainop_type",
    "port_revenue_share",
    "rail_revenue_share",
    "port_rail_revenue_share",
    "largest_non_port_rail_item",
    "largest_non_port_rail_revenue_ratio",
    "approved_port_rail_business_tag",
    "source_name",
    "source_url",
    "pit_usable",
    "review_status",
    "notes",
]

PORT_TERMS = (
    "\u6e2f\u53e3",
    "\u7801\u5934",
    "\u6e2f\u52a1",
    "\u88c5\u5378",
    "\u96c6\u88c5\u7bb1",
    "\u6563\u8d27",
    "\u5806\u5b58",
)
RAIL_TERMS = (
    "\u94c1\u8def",
    "\u8d27\u8fd0",
    "\u5ba2\u8fd0",
    "\u8fd0\u8f93",
    "\u8f66\u7ad9",
)
NON_CORE_TERMS = (
    "\u9ad8\u901f",
    "\u516c\u8def",
    "\u822a\u7a7a",
    "\u673a\u573a",
    "\u822a\u8fd0",
    "\u8239\u8236",
    "\u7269\u6d41",
    "\u4ed3\u50a8",
    "\u8d38\u6613",
    "\u623f\u5730\u4ea7",
)


def classify_port_rail_eastmoney_segments(
    raw_csv: Path,
    disclosure_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> Path:
    raw_rows = read_csv_rows(raw_csv)
    disclosures = _disclosures_by_code_period(disclosure_csv)
    evidence_rows = _build_segment_evidence(raw_rows, disclosures)

    out_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = out_dir / "port_rail_segment_business_evidence_eastmoney.csv"
    manifest_path = out_dir / "port_rail_segment_business_evidence_manifest.json"
    write_csv_rows(evidence_path, SEGMENT_EVIDENCE_FIELDS, evidence_rows)

    usable = [row for row in evidence_rows if str(row.get("pit_usable", "")).lower() == "true"]
    tag_counts = Counter(row.get("approved_port_rail_business_tag", "") for row in evidence_rows)
    usable_tag_counts = Counter(row.get("approved_port_rail_business_tag", "") for row in usable)
    write_json_file(
        manifest_path,
        {
            "dataset": "port_rail_segment_business_evidence_eastmoney",
            "raw_input": str(raw_csv),
            "disclosure_csv": str(disclosure_csv),
            "evidence_output": str(evidence_path),
            "raw_row_count": len(raw_rows),
            "evidence_row_count": len(evidence_rows),
            "pit_usable_rows": len(usable),
            "covered_company_count": len({row["code"] for row in usable if row.get("code")}),
            "tag_counts": dict(sorted(tag_counts.items())),
            "usable_tag_counts": dict(sorted(usable_tag_counts.items())),
            "source_policy": "Eastmoney public F10 BusinessAnalysis/PageAjax is used as first-layer structured evidence; Tushare disclosure_date supplies report visibility.",
            "ratio_policy": "Industry segment is preferred over product segment to avoid duplicate counting; ratios fall back to Eastmoney income_ratio when revenue amount is missing.",
            "limitations": [
                "Eastmoney segment evidence is not final proof; annual or interim report spot checks remain required before platform replication.",
                "Throughput, freight volume, tariff policy and capex commitments are not certified by this file.",
                "This runner fixes Windows command-line Chinese keyword corruption by storing classifier terms as unicode escapes in source code.",
            ],
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return evidence_path


def _build_segment_evidence(
    raw_rows: list[dict[str, Any]],
    disclosures: dict[tuple[str, str], dict[str, str]],
) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        code = str(row.get("code") or "")
        report_period = str(row.get("report_period") or "")
        if code and report_period:
            by_key[(code, report_period)].append(row)

    evidence_rows: list[dict[str, Any]] = []
    for (code, report_period), rows in sorted(by_key.items()):
        selected_type, selected = _select_segment_layer(rows)
        ratios = _port_rail_segment_ratios(selected)
        disclosure = disclosures.get((code, report_period), {})
        visible_date = disclosure.get("notice_date", "")
        tag = _approved_port_rail_business_tag(ratios)
        pit_usable = bool(visible_date and tag != "non_core_or_needs_review")
        evidence_rows.append(
            {
                "code": code,
                "ts_code": _to_ts_code(code),
                "report_period": report_period,
                "report_type": "semiannual" if report_period.endswith("-06-30") else "annual" if report_period.endswith("-12-31") else "other",
                "notice_date": visible_date,
                "visible_date": visible_date,
                "selected_mainop_type": selected_type,
                "port_revenue_share": fmt_float(ratios["port_revenue_share"]),
                "rail_revenue_share": fmt_float(ratios["rail_revenue_share"]),
                "port_rail_revenue_share": fmt_float(ratios["port_rail_revenue_share"]),
                "largest_non_port_rail_item": ratios["largest_non_port_rail_item"],
                "largest_non_port_rail_revenue_ratio": fmt_float(ratios["largest_non_port_rail_revenue_ratio"]),
                "approved_port_rail_business_tag": tag,
                "source_name": "Eastmoney F10 BusinessAnalysis/PageAjax + Tushare disclosure_date",
                "source_url": f"https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/Index?type=web&code={_to_eastmoney_code(code)}",
                "pit_usable": "true" if pit_usable else "false",
                "review_status": "eastmoney_segment_needs_spot_check" if pit_usable else "needs_review_or_not_core",
                "notes": _segment_notes(selected, ratios),
            }
        )
    return evidence_rows


def _select_segment_layer(rows: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    for mainop_type in ("industry", "product"):
        selected = [row for row in rows if row.get("mainop_type") == mainop_type and not _is_region_or_subitem(row)]
        if selected:
            return mainop_type, selected
    selected = [row for row in rows if not _is_region_or_subitem(row)]
    return "all_non_region" if selected else "all", selected or rows


def _port_rail_segment_ratios(rows: list[dict[str, Any]]) -> dict[str, Any]:
    amounts = [_segment_weight(row) for row in rows]
    total = sum(amount for amount in amounts if amount > 0)
    port_total = 0.0
    rail_total = 0.0
    non_port_rail: list[tuple[str, float]] = []
    for row, amount in zip(rows, amounts):
        name = str(row.get("item_name") or "")
        bucket = _segment_bucket(name)
        if bucket == "port":
            port_total += amount
        elif bucket == "rail":
            rail_total += amount
        else:
            non_port_rail.append((name, amount))
    port_rail_total = port_total + rail_total
    largest_non_name, largest_non_amount = ("", 0.0)
    if non_port_rail:
        largest_non_name, largest_non_amount = max(non_port_rail, key=lambda item: item[1])
    return {
        "port_revenue_share": _safe_ratio(port_total, total),
        "rail_revenue_share": _safe_ratio(rail_total, total),
        "port_rail_revenue_share": _safe_ratio(port_rail_total, total),
        "largest_non_port_rail_item": largest_non_name,
        "largest_non_port_rail_revenue_ratio": _safe_ratio(largest_non_amount, total),
    }


def _segment_weight(row: dict[str, Any]) -> float:
    amount = to_float(row.get("main_business_income"))
    if amount is not None and amount > 0:
        return amount
    income_ratio = to_float(row.get("income_ratio"))
    if income_ratio is None:
        return 0.0
    return income_ratio * 100.0 if income_ratio <= 1.5 else income_ratio


def _segment_bucket(name: str) -> str:
    if any(term in name for term in PORT_TERMS):
        return "port"
    if any(term in name for term in RAIL_TERMS) and not any(term in name for term in NON_CORE_TERMS):
        return "rail"
    return "non_port_rail"


def _approved_port_rail_business_tag(ratios: dict[str, Any]) -> str:
    port_ratio = to_float(ratios.get("port_revenue_share")) or 0.0
    rail_ratio = to_float(ratios.get("rail_revenue_share")) or 0.0
    combined = to_float(ratios.get("port_rail_revenue_share")) or 0.0
    if port_ratio >= 0.5:
        return "core_port_operator"
    if rail_ratio >= 0.5:
        return "core_rail_operator"
    if combined >= 0.5:
        return "mixed_port_rail_operator"
    if combined >= 0.35:
        return "mixed_transport_infrastructure_operator"
    return "non_core_or_needs_review"


def _segment_notes(rows: list[dict[str, Any]], ratios: dict[str, Any]) -> str:
    items = [str(row.get("item_name") or "") for row in rows if row.get("item_name")]
    return (
        f"selected_items={'|'.join(items[:10])}; "
        f"largest_non_port_rail={ratios.get('largest_non_port_rail_item')}; "
        "Eastmoney structured segment evidence requires original report spot check before final PIT promotion."
    )


def _is_region_or_subitem(row: dict[str, Any]) -> bool:
    mainop_type = str(row.get("mainop_type") or "")
    name = str(row.get("item_name") or "")
    return mainop_type == "region" or name.startswith("\u5176\u4e2d") or name.startswith("\u5176\u4e2d:")


def _disclosures_by_code_period(disclosure_csv: Path) -> dict[tuple[str, str], dict[str, str]]:
    if not disclosure_csv.exists():
        return {}
    result: dict[tuple[str, str], dict[str, str]] = {}
    for row in read_csv_rows(disclosure_csv):
        code = row.get("code", "")
        report_period = row.get("report_period", "")
        if code and report_period:
            result[(code, report_period)] = row
    return result


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def _to_ts_code(code: str) -> str:
    if code.endswith(".XSHG"):
        return code.replace(".XSHG", ".SH")
    if code.endswith(".XSHE"):
        return code.replace(".XSHE", ".SZ")
    return code


def _to_eastmoney_code(code: str) -> str:
    if code.endswith(".XSHG"):
        return f"SH{code[:6]}"
    if code.endswith(".XSHE"):
        return f"SZ{code[:6]}"
    return code

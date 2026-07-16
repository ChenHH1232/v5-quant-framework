from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from v5.coal_external_state_runner import STATE_FIELDS, validate_coal_external_state


DEFAULT_DATABASE_DIR = Path("数据库")
DEFAULT_PROCESSED_DIR = DEFAULT_DATABASE_DIR / "processed"
DEFAULT_MANIFEST_DIR = DEFAULT_DATABASE_DIR / "manifests"

MANUAL_STATE_TEMPLATE_ROWS = [
    {
        "visible_date": "",
        "state_date": "",
        "state_scope": "national",
        "sub_industry": "all_coal",
        "metric": "coal_inventory_or_output_state",
        "value": "",
        "unit": "10k_ton_or_percent",
        "source_name": "National Bureau of Statistics",
        "source_url": "https://www.stats.gov.cn/sj/zxfb/",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "manual_template",
        "notes": "Monthly raw coal output or raw coal output YoY. Fill from NBS Energy Production Situation release with conservative visible_date.",
    },
    {
        "visible_date": "",
        "state_date": "",
        "state_scope": "circulation_market",
        "sub_industry": "thermal_coal",
        "metric": "thermal_coal_price_state",
        "value": "",
        "unit": "cny_per_ton",
        "source_name": "National Bureau of Statistics",
        "source_url": "https://www.stats.gov.cn/sj/zxfb/",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "manual_template",
        "notes": "NBS circulation production-material price, e.g. Shanxi mixed coal or ordinary mixed coal.",
    },
    {
        "visible_date": "",
        "state_date": "",
        "state_scope": "circulation_market",
        "sub_industry": "coking_coal",
        "metric": "coking_coal_price_state",
        "value": "",
        "unit": "cny_per_ton",
        "source_name": "National Bureau of Statistics",
        "source_url": "https://www.stats.gov.cn/sj/zxfb/",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "manual_template",
        "notes": "NBS circulation production-material price for coking coal if available.",
    },
    {
        "visible_date": "",
        "state_date": "",
        "state_scope": "port_or_market",
        "sub_industry": "thermal_coal",
        "metric": "thermal_coal_price_state",
        "value": "",
        "unit": "cny_per_ton_or_index",
        "source_name": "CCTD / Qinhuangdao coal market / national coal trading center",
        "source_url": "",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "manual_template_license_check_required",
        "notes": "Use only if licensed/manual download is permitted. Do not scrape blocked or paywalled pages.",
    },
    {
        "visible_date": "",
        "state_date": "",
        "state_scope": "port_or_market",
        "sub_industry": "all_coal",
        "metric": "coal_inventory_or_output_state",
        "value": "",
        "unit": "10k_ton_or_days",
        "source_name": "CCTD / port inventory / coal association / NDRC",
        "source_url": "",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "manual_template_license_check_required",
        "notes": "Inventory, port inventory, or inventory days. Use only with clear publication date and access permission.",
    },
]


def write_coal_manual_state_template(out_dir: Path = DEFAULT_PROCESSED_DIR / "coal_external_state") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    template_path = out_dir / "coal_manual_state_import_template.csv"
    _write_csv(template_path, STATE_FIELDS, MANUAL_STATE_TEMPLATE_ROWS)
    _write_json(
        out_dir / "coal_manual_state_import_manifest.json",
        {
            "dataset": "coal_manual_state_import_template",
            "template": str(template_path),
            "fields": STATE_FIELDS,
            "row_count": len(MANUAL_STATE_TEMPLATE_ROWS),
            "required_rule": "Set pit_usable=true only when source_publication_date and visible_date are filled and visible_date <= rebalance date.",
            "anti_crawler_rule": "Manual download is allowed only from sources with permitted access. Do not bypass login, paywall, robots policy, or anti-crawler controls.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return template_path


def merge_coal_manual_state(
    base_state_csv: Path,
    manual_state_csv: Path,
    out_dir: Path = DEFAULT_PROCESSED_DIR / "coal_external_state",
) -> Path:
    base_rows = _read_csv(base_state_csv) if base_state_csv.exists() else []
    manual_rows = _read_csv(manual_state_csv)
    merged_rows = base_rows + manual_rows
    merged_rows = sorted(merged_rows, key=lambda row: (row.get("visible_date", ""), row.get("metric", ""), row.get("sub_industry", "")))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "coal_external_state_enriched.csv"
    _write_csv(out_path, STATE_FIELDS, merged_rows)
    validation = validate_coal_external_state(out_path)
    _write_json(
        out_dir / "coal_external_state_enriched_manifest.json",
        {
            "dataset": "coal_external_state_enriched",
            "base_state_csv": str(base_state_csv),
            "manual_state_csv": str(manual_state_csv),
            "output": str(out_path),
            "row_count": len(merged_rows),
            "manual_row_count": len(manual_rows),
            "validation": validation,
            "governance": "Manual rows require source review before formal candidate promotion.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return out_path


def audit_coal_business_tags(panel_csv: Path, out_dir: Path = DEFAULT_MANIFEST_DIR / "coal_business_tag_audit") -> Path:
    rows = _read_csv(panel_csv)
    out_dir.mkdir(parents=True, exist_ok=True)
    by_code: dict[str, dict[str, Any]] = {}
    for row in rows:
        code = row.get("code", "")
        if not code:
            continue
        item = by_code.setdefault(
            code,
            {
                "code": code,
                "company_name": row.get("company_name", ""),
                "coal_business_tag": row.get("coal_business_tag", ""),
                "first_trade_date": row.get("trade_date", ""),
                "last_trade_date": row.get("trade_date", ""),
                "row_count": 0,
                "business_tag_source": row.get("business_tag_source", ""),
                "business_tag_visible_date_min": row.get("business_tag_visible_date", ""),
                "formal_pit_usable": "false",
                "audit_status": "blocked_manual_current_classification",
                "required_action": "Audit annual/interim report publication dates and segment revenue/profit exposure before formal use.",
            },
        )
        item["row_count"] += 1
        item["first_trade_date"] = min(str(item["first_trade_date"]), str(row.get("trade_date", "")))
        item["last_trade_date"] = max(str(item["last_trade_date"]), str(row.get("trade_date", "")))
        if row.get("coal_business_tag") != item["coal_business_tag"]:
            item["audit_status"] = "blocked_tag_changes_need_review"
    audit_rows = list(by_code.values())
    audit_path = out_dir / "coal_business_tag_audit.csv"
    _write_csv(audit_path, list(audit_rows[0].keys()) if audit_rows else ["code"], audit_rows)
    summary = {
        "dataset": "coal_business_tag_audit",
        "panel": str(panel_csv),
        "row_count": len(audit_rows),
        "formal_pit_usable_count": sum(1 for row in audit_rows if row["formal_pit_usable"] == "true"),
        "blocked_count": sum(1 for row in audit_rows if row["formal_pit_usable"] != "true"),
        "status": "blocked",
        "reason": "Current coal_business_tag values are manual classifications without company-report visible-date audit.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    _write_json(out_dir / "coal_business_tag_audit_summary.json", summary)
    _write_report(out_dir / "coal_business_tag_audit_report.md", "Coal Business Tag Audit", summary)
    return out_dir / "coal_business_tag_audit_report.md"


def audit_coal_capex_fcf(panel_csv: Path, out_dir: Path = DEFAULT_MANIFEST_DIR / "coal_capex_fcf_audit") -> Path:
    rows = _read_csv(panel_csv)
    audit_rows = []
    capex_burdens = []
    fcf_yields = []
    ocf_yields = []
    for row in rows:
        ocf_yield = _to_float(row.get("operating_cash_flow_yield"))
        fcf_yield = _to_float(row.get("free_cash_flow_yield"))
        capex_burden = _to_float(row.get("capex_burden"))
        if ocf_yield is not None:
            ocf_yields.append(ocf_yield)
        if fcf_yield is not None:
            fcf_yields.append(fcf_yield)
        if capex_burden is not None:
            capex_burdens.append(capex_burden)
        flags = []
        if capex_burden is None:
            flags.append("missing_capex_burden")
        elif capex_burden < 0:
            flags.append("negative_capex_burden")
        elif capex_burden > 1:
            flags.append("capex_exceeds_ocf")
        if ocf_yield is not None and fcf_yield is not None and fcf_yield > ocf_yield:
            flags.append("fcf_greater_than_ocf")
        if fcf_yield is not None and fcf_yield < 0:
            flags.append("negative_fcf_yield")
        if flags:
            audit_rows.append(
                {
                    "trade_date": row.get("trade_date", ""),
                    "code": row.get("code", ""),
                    "company_name": row.get("company_name", ""),
                    "coal_business_tag": row.get("coal_business_tag", ""),
                    "operating_cash_flow_yield": row.get("operating_cash_flow_yield", ""),
                    "free_cash_flow_yield": row.get("free_cash_flow_yield", ""),
                    "capex_burden": row.get("capex_burden", ""),
                    "flags": ";".join(flags),
                }
            )

    out_dir.mkdir(parents=True, exist_ok=True)
    audit_path = out_dir / "coal_capex_fcf_audit_flags.csv"
    _write_csv(
        audit_path,
        ["trade_date", "code", "company_name", "coal_business_tag", "operating_cash_flow_yield", "free_cash_flow_yield", "capex_burden", "flags"],
        audit_rows,
    )
    summary = {
        "dataset": "coal_capex_fcf_audit",
        "panel": str(panel_csv),
        "panel_rows": len(rows),
        "flagged_rows": len(audit_rows),
        "flagged_ratio": _ratio(len(audit_rows), len(rows)),
        "ocf_yield_median": _median(ocf_yields),
        "fcf_yield_median": _median(fcf_yields),
        "capex_burden_median": _median(capex_burdens),
        "capex_burden_p90": _quantile(capex_burdens, 0.9),
        "negative_fcf_rows": sum(1 for row in audit_rows if "negative_fcf_yield" in row["flags"]),
        "capex_exceeds_ocf_rows": sum(1 for row in audit_rows if "capex_exceeds_ocf" in row["flags"]),
        "status": "needs_review" if audit_rows else "pass",
        "interpretation": "FCF yield is useful only if capex outliers and negative FCF cases are reviewed before formal candidate promotion.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    _write_json(out_dir / "coal_capex_fcf_audit_summary.json", summary)
    _write_report(out_dir / "coal_capex_fcf_audit_report.md", "Coal Capex / FCF Audit", summary)
    return out_dir / "coal_capex_fcf_audit_report.md"


def _write_report(path: Path, title: str, summary: dict[str, Any]) -> None:
    lines = [f"# {title}", ""]
    for key, value in summary.items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _to_float(value: Any) -> float | None:
    if value in {None, "", "nan", "NaN", "None"}:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _ratio(numerator: float | int, denominator: float | int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _median(values: list[float]) -> float | None:
    return median(values) if values else None


def _quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * q))))
    return ordered[index]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-coal-data-audit")
    subparsers = parser.add_subparsers(dest="command", required=True)
    template_parser = subparsers.add_parser("manual-state-template")
    template_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_external_state")
    merge_parser = subparsers.add_parser("merge-manual-state")
    merge_parser.add_argument("base_state_csv", type=Path)
    merge_parser.add_argument("manual_state_csv", type=Path)
    merge_parser.add_argument("--out-dir", type=Path, default=DEFAULT_PROCESSED_DIR / "coal_external_state")
    tag_parser = subparsers.add_parser("audit-business-tags")
    tag_parser.add_argument("panel", type=Path)
    tag_parser.add_argument("--out-dir", type=Path, default=DEFAULT_MANIFEST_DIR / "coal_business_tag_audit")
    capex_parser = subparsers.add_parser("audit-capex-fcf")
    capex_parser.add_argument("panel", type=Path)
    capex_parser.add_argument("--out-dir", type=Path, default=DEFAULT_MANIFEST_DIR / "coal_capex_fcf_audit")
    args = parser.parse_args(argv)
    if args.command == "manual-state-template":
        print(write_coal_manual_state_template(args.out_dir))
        return 0
    if args.command == "merge-manual-state":
        print(merge_coal_manual_state(args.base_state_csv, args.manual_state_csv, args.out_dir))
        return 0
    if args.command == "audit-business-tags":
        print(audit_coal_business_tags(args.panel, args.out_dir))
        return 0
    if args.command == "audit-capex-fcf":
        print(audit_coal_capex_fcf(args.panel, args.out_dir))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

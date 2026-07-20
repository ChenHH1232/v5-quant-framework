from __future__ import annotations

import argparse
import calendar
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.paths import DEFAULT_PROCESSED_DIR


DEFAULT_OUT_DIR = DEFAULT_PROCESSED_DIR / "oil_gas_source_gate_v58e"
DEFAULT_PANEL = DEFAULT_PROCESSED_DIR / "oil_gas_state_conditioned_panel_v58d" / "oil_gas_state_conditioned_ocf_v58d" / "panel.csv"

STATE_FIELDS = [
    "visible_date",
    "state_date",
    "state_scope",
    "sub_industry",
    "metric",
    "value",
    "unit",
    "source_name",
    "source_url",
    "source_publication_date",
    "pit_usable",
    "review_status",
    "notes",
]

CORE_V58D_STATE_METRICS = [
    "crude_oil_price_state",
    "bitumen_price_state",
    "gas_liquid_price_state",
    "refining_spread_proxy_state",
]

PROMOTION_STATE_METRICS = [
    *CORE_V58D_STATE_METRICS,
    "inventory_or_demand_state",
    "pipeline_tariff_policy_state",
]

REVIEWED_STATUSES = {"reviewed", "official_seed_reviewed", "licensed_reviewed", "exchange_official_reviewed", "nbs_official_reviewed"}

SOURCE_REGISTER_FIELDS = [
    "source_role",
    "metric",
    "preferred_source",
    "source_url",
    "access_mode",
    "anti_crawler_policy",
    "pit_visible_date_rule",
    "review_status",
    "notes",
]


@dataclass(frozen=True)
class OilGasSourceGateResult:
    summary_path: Path
    report_path: Path
    status: str
    core_ready: bool
    promotion_ready: bool


def write_oil_gas_official_source_register(out_dir: Path = DEFAULT_OUT_DIR) -> Path:
    rows = [
        {
            "source_role": "official_exchange_crude",
            "metric": "crude_oil_price_state",
            "preferred_source": "Shanghai International Energy Exchange crude oil futures market data",
            "source_url": "https://www.ine.cn/eng/market/futures/energy/sc/",
            "access_mode": "manual_or_permitted_export",
            "anti_crawler_policy": "Do not bypass WAF, login, rate limits or robots controls. Use official download/export or licensed vendor if automated access is blocked.",
            "pit_visible_date_rule": "Use official exchange publication/update date; if only end-of-day file is available, visible_date is next calendar day.",
            "review_status": "source_registered_not_imported",
            "notes": "Preferred replacement for Sina/akshare crude futures proxy.",
        },
        {
            "source_role": "official_exchange_bitumen",
            "metric": "bitumen_price_state",
            "preferred_source": "Shanghai Futures Exchange bitumen futures market data",
            "source_url": "https://www.shfe.com.cn/eng/Market/Futures/Energy/bu_f/",
            "access_mode": "manual_or_permitted_export",
            "anti_crawler_policy": "Use official market-data export or licensed vendor. Do not scrape protected dynamic endpoints.",
            "pit_visible_date_rule": "visible_date is the official publication/update date or next calendar day after end-of-day close.",
            "review_status": "source_registered_not_imported",
            "notes": "Official exchange source for bitumen state.",
        },
        {
            "source_role": "official_nbs_petroleum_gas",
            "metric": "gas_liquid_price_state",
            "preferred_source": "NBS market prices of important means of production in circulation: LNG / LPG",
            "source_url": "https://www.stats.gov.cn/english/PressRelease/",
            "access_mode": "manual_public_html_export",
            "anti_crawler_policy": "Prefer manual download or official public HTML/PDF. Do not depend on hidden dynamic APIs.",
            "pit_visible_date_rule": "visible_date equals NBS release date; state_date is the release's monitored period end date.",
            "review_status": "source_registered_not_imported",
            "notes": "NBS public releases contain LNG and LPG rows and are suitable reviewed public sources when values and publication dates are recorded.",
        },
        {
            "source_role": "official_nbs_refined_products",
            "metric": "refining_spread_proxy_state",
            "preferred_source": "NBS gasoline/diesel prices plus reviewed crude state, or a licensed crack-spread source",
            "source_url": "https://www.stats.gov.cn/english/PressRelease/",
            "access_mode": "manual_public_html_export_or_licensed_vendor",
            "anti_crawler_policy": "Derive only from reviewed inputs; record the formula and source rows.",
            "pit_visible_date_rule": "visible_date is max visible_date of the reviewed source components.",
            "review_status": "source_registered_not_imported",
            "notes": "This remains a proxy unless a true refining margin source is licensed and reviewed.",
        },
        {
            "source_role": "official_nbs_or_industry_demand",
            "metric": "inventory_or_demand_state",
            "preferred_source": "NBS energy production / crude processing / apparent demand, or reviewed industry inventory source",
            "source_url": "https://www.stats.gov.cn/sj/zxfb/",
            "access_mode": "manual_public_html_export_or_licensed_vendor",
            "anti_crawler_policy": "Use official releases or licensed data exports; no protected scraping.",
            "pit_visible_date_rule": "visible_date equals publication date.",
            "review_status": "source_registered_not_imported",
            "notes": "Promotion enhancer for weak-year explanation; not required for opening a research rerun.",
        },
        {
            "source_role": "official_policy_tariff",
            "metric": "pipeline_tariff_policy_state",
            "preferred_source": "NDRC, company announcements, annual reports or official pipeline tariff policy releases",
            "source_url": "https://www.ndrc.gov.cn/",
            "access_mode": "manual_policy_event_register",
            "anti_crawler_policy": "Manual source registration preferred. Store event date, visible date and link.",
            "pit_visible_date_rule": "visible_date equals official policy publication date or company announcement date.",
            "review_status": "source_registered_not_imported",
            "notes": "Required before pipeline-heavy formal promotion.",
        },
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "oil_gas_official_source_register.csv"
    write_csv_rows(path, SOURCE_REGISTER_FIELDS, rows)
    write_json_file(
        out_dir / "oil_gas_official_source_register_manifest.json",
        {
            "dataset": "oil_gas_official_source_register_v58e",
            "output": str(path),
            "row_count": len(rows),
            "status": "source_register_ready_manual_import_required",
            "anti_crawler_rule": "Use official download/export or licensed vendor access. Do not bypass WAF, login, robots, rate limits or paywalls.",
            "created_at_utc": _now_utc(),
        },
    )
    return path


def write_oil_gas_official_state_import_template(
    out_dir: Path = DEFAULT_OUT_DIR,
    start_year: int = 2021,
    end_year: int = 2026,
) -> Path:
    rows: list[dict[str, Any]] = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            if year == 2026 and month > 6:
                continue
            state_date = _month_end_date(year, month)
            rows.extend(
                [
                    _template_row(state_date, "exchange_market", "upstream_integrated", "crude_oil_price_state", "cny_per_barrel_or_usd_per_barrel", "INE / Brent / WTI reviewed source row."),
                    _template_row(state_date, "exchange_market", "refining", "bitumen_price_state", "cny_per_ton", "SHFE bitumen reviewed source row."),
                    _template_row(state_date, "official_statistics", "natural_gas_lpg", "gas_liquid_price_state", "cny_per_ton", "NBS LNG/LPG or DCE LPG reviewed source row."),
                    _template_row(state_date, "derived_reviewed", "refining", "refining_spread_proxy_state", "documented_formula", "Reviewed product-price minus crude formula or licensed refining margin."),
                    _template_row(state_date, "official_statistics", "all_oil_gas", "inventory_or_demand_state", "index_or_yoy", "NBS crude processing / apparent demand / reviewed inventory source."),
                ]
            )
        policy_state_date = f"{year:04d}-12-31"
        rows.append(
            _template_row(
                policy_state_date,
                "policy_event",
                "pipeline_storage_lng",
                "pipeline_tariff_policy_state",
                "policy_state_index",
                "NDRC / company announcement / annual report policy event row.",
            )
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "oil_gas_official_state_import_template.csv"
    write_csv_rows(path, STATE_FIELDS, rows)
    write_json_file(
        out_dir / "oil_gas_official_state_import_manifest.json",
        {
            "dataset": "oil_gas_official_state_import_template_v58e",
            "output": str(path),
            "start_year": start_year,
            "end_year": end_year,
            "row_count": len(rows),
            "pit_usable_count": 0,
            "core_metrics": CORE_V58D_STATE_METRICS,
            "promotion_metrics": PROMOTION_STATE_METRICS,
            "required_rule": "Rows become PIT usable only after value, visible_date, source_publication_date and review_status are filled from official/reviewed sources.",
            "anti_crawler_rule": "Manual download or licensed export is preferred. Do not bypass WAF, login, robots, rate limits or paywalls.",
            "created_at_utc": _now_utc(),
        },
    )
    return path


def merge_oil_gas_state_sources(out_dir: Path, *state_csvs: Path, panel_path: Path = DEFAULT_PANEL) -> Path:
    rows: list[dict[str, str]] = []
    for path in state_csvs:
        if path.exists():
            rows.extend(read_csv_rows(path))
    rows = sorted(rows, key=lambda row: (row.get("visible_date", ""), row.get("state_date", ""), row.get("metric", ""), row.get("sub_industry", "")))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "oil_gas_official_state_formal_candidate.csv"
    write_csv_rows(out_path, STATE_FIELDS, rows)
    audit = audit_oil_gas_source_gate(out_path, panel_path=panel_path, out_dir=out_dir)
    write_json_file(
        out_dir / "oil_gas_official_state_formal_candidate_manifest.json",
        {
            "dataset": "oil_gas_official_state_formal_candidate_v58e",
            "sources": [str(path) for path in state_csvs],
            "output": str(out_path),
            "row_count": len(rows),
            "audit_summary": str(audit.summary_path),
            "status": audit.status,
            "created_at_utc": _now_utc(),
        },
    )
    return out_path


def audit_oil_gas_source_gate(
    state_csv: Path,
    panel_path: Path = DEFAULT_PANEL,
    out_dir: Path = DEFAULT_OUT_DIR,
    min_coverage_ratio: float = 0.8,
) -> OilGasSourceGateResult:
    rows = read_csv_rows(state_csv) if state_csv.exists() else []
    trade_dates = _trade_dates(panel_path)
    validation = _validate_rows(rows)
    core_coverage = _coverage(rows, trade_dates, CORE_V58D_STATE_METRICS)
    promotion_coverage = _coverage(rows, trade_dates, PROMOTION_STATE_METRICS)
    core_ready = validation["blocker_count"] == 0 and _coverage_ready(core_coverage, min_coverage_ratio)
    promotion_ready = core_ready and _coverage_ready(promotion_coverage, min_coverage_ratio)
    status = "ready_for_quant_review" if promotion_ready else "core_state_ready_needs_promotion_sources" if core_ready else "source_repair_blocked"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": 1,
        "experiment_layer": "data_availability_gate",
        "status": status,
        "state_csv": str(state_csv),
        "panel_path": str(panel_path),
        "trade_date_count": len(trade_dates),
        "row_count": len(rows),
        "validation": validation,
        "core_metrics": CORE_V58D_STATE_METRICS,
        "promotion_metrics": PROMOTION_STATE_METRICS,
        "core_coverage": core_coverage,
        "promotion_coverage": promotion_coverage,
        "core_ready": core_ready,
        "promotion_ready": promotion_ready,
        "min_coverage_ratio": min_coverage_ratio,
        "pm_rule": "Core official/reviewed state coverage can reopen research validation; promotion still requires inventory/demand and pipeline tariff/policy evidence.",
        "created_at_utc": _now_utc(),
    }
    summary_path = out_dir / "oil_gas_source_gate_summary.json"
    report_path = out_dir / "oil_gas_source_gate_report.md"
    write_json_file(summary_path, summary)
    report_path.write_text(_report(summary), encoding="utf-8")
    return OilGasSourceGateResult(summary_path, report_path, status, core_ready, promotion_ready)


def _validate_rows(rows: list[dict[str, str]]) -> dict[str, Any]:
    missing_required = []
    future_visible = 0
    unreviewed_usable = 0
    pit_usable_count = 0
    metric_counts: dict[str, int] = {}
    usable_metric_counts: dict[str, int] = {}
    for index, row in enumerate(rows, start=2):
        metric = str(row.get("metric") or "")
        if metric:
            metric_counts[metric] = metric_counts.get(metric, 0) + 1
        is_pit_usable = str(row.get("pit_usable", "")).lower() == "true"
        if is_pit_usable:
            for field in ["visible_date", "state_date", "metric", "value", "source_name", "source_url", "source_publication_date", "pit_usable", "review_status"]:
                if not row.get(field):
                    missing_required.append(f"line {index}: missing {field}")
        visible = str(row.get("visible_date") or "")[:10]
        publication = str(row.get("source_publication_date") or "")[:10]
        if is_pit_usable and visible and publication and visible < publication:
            future_visible += 1
        if is_pit_usable:
            pit_usable_count += 1
            usable_metric_counts[metric] = usable_metric_counts.get(metric, 0) + 1
            if str(row.get("review_status") or "") not in REVIEWED_STATUSES:
                unreviewed_usable += 1
    blocker_count = len(missing_required) + future_visible + unreviewed_usable
    return {
        "missing_required": missing_required,
        "future_or_invalid_visible_dates": future_visible,
        "unreviewed_pit_usable_rows": unreviewed_usable,
        "pit_usable_count": pit_usable_count,
        "metric_counts": metric_counts,
        "usable_metric_counts": usable_metric_counts,
        "blocker_count": blocker_count,
    }


def _coverage(rows: list[dict[str, str]], trade_dates: list[str], metrics: Iterable[str]) -> dict[str, Any]:
    usable = [row for row in rows if str(row.get("pit_usable", "")).lower() == "true" and str(row.get("review_status") or "") in REVIEWED_STATUSES]
    result: dict[str, Any] = {}
    for metric in metrics:
        metric_rows = [row for row in usable if row.get("metric") == metric and row.get("visible_date") and row.get("value")]
        metric_rows.sort(key=lambda row: str(row.get("visible_date"))[:10])
        covered_dates = []
        for trade_date in trade_dates:
            if any(str(row.get("visible_date"))[:10] <= trade_date for row in metric_rows):
                covered_dates.append(trade_date)
        result[metric] = {
            "usable_rows": len(metric_rows),
            "covered_trade_dates": len(covered_dates),
            "coverage_ratio": len(covered_dates) / len(trade_dates) if trade_dates else 0.0,
            "first_covered_trade_date": covered_dates[0] if covered_dates else "",
            "last_covered_trade_date": covered_dates[-1] if covered_dates else "",
        }
    return result


def _coverage_ready(coverage: dict[str, Any], min_ratio: float) -> bool:
    return bool(coverage) and all(float(item["coverage_ratio"]) >= min_ratio for item in coverage.values())


def _trade_dates(panel_path: Path) -> list[str]:
    if not panel_path.exists():
        return []
    return sorted({str(row.get("trade_date") or "")[:10] for row in read_csv_rows(panel_path) if row.get("trade_date")})


def _template_row(state_date: str, state_scope: str, sub_industry: str, metric: str, unit: str, notes: str) -> dict[str, str]:
    return {
        "visible_date": "",
        "state_date": state_date,
        "state_scope": state_scope,
        "sub_industry": sub_industry,
        "metric": metric,
        "value": "",
        "unit": unit,
        "source_name": "",
        "source_url": "",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "template_pending_review",
        "notes": notes,
    }


def _month_end_date(year: int, month: int) -> str:
    return date(year, month, calendar.monthrange(year, month)[1]).isoformat()


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _report(summary: dict[str, Any]) -> str:
    lines = [
        "# Oil / Gas Source Gate V5.8e",
        "",
        f"- Status: `{summary['status']}`",
        f"- Rows: `{summary['row_count']}`",
        f"- Trade dates: `{summary['trade_date_count']}`",
        f"- Core ready: `{summary['core_ready']}`",
        f"- Promotion ready: `{summary['promotion_ready']}`",
        "",
        "## Core Coverage",
        "",
    ]
    for metric, item in summary["core_coverage"].items():
        lines.append(f"- `{metric}`: `{item['covered_trade_dates']}/{summary['trade_date_count']}` coverage `{item['coverage_ratio']}`")
    lines.extend(["", "## Promotion Coverage", ""])
    for metric, item in summary["promotion_coverage"].items():
        lines.append(f"- `{metric}`: `{item['covered_trade_dates']}/{summary['trade_date_count']}` coverage `{item['coverage_ratio']}`")
    lines.extend(
        [
            "",
            "## Validation",
            "",
            f"- Row-level blockers: `{summary['validation']['blocker_count']}`",
            f"- Coverage blocker: `{not summary['core_ready']}`",
        ]
    )
    if summary["validation"].get("missing_required"):
        lines.append(f"- Missing required examples: `{summary['validation']['missing_required'][:5]}`")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-oil-gas-source-gate")
    subparsers = parser.add_subparsers(dest="command", required=True)
    register_parser = subparsers.add_parser("source-register")
    register_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    template_parser = subparsers.add_parser("state-template")
    template_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    template_parser.add_argument("--start-year", type=int, default=2021)
    template_parser.add_argument("--end-year", type=int, default=2026)
    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("state_csv", type=Path)
    audit_parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    audit_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    merge_parser = subparsers.add_parser("merge")
    merge_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    merge_parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    merge_parser.add_argument("state_csvs", nargs="+", type=Path)
    args = parser.parse_args(argv)
    if args.command == "source-register":
        print(write_oil_gas_official_source_register(args.out_dir))
        return 0
    if args.command == "state-template":
        print(write_oil_gas_official_state_import_template(args.out_dir, args.start_year, args.end_year))
        return 0
    if args.command == "audit":
        print(audit_oil_gas_source_gate(args.state_csv, args.panel, args.out_dir))
        return 0
    if args.command == "merge":
        print(merge_oil_gas_state_sources(args.out_dir, *args.state_csvs, panel_path=args.panel))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

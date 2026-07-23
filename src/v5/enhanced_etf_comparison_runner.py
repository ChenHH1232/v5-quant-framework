from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import write_csv_rows, write_json_file


DEFAULT_OUT_DIR = Path("enhanced_etf_production_lines_v5") / "current"
DEFAULT_PRODUCTION_SUMMARY = DEFAULT_OUT_DIR / "production_line_summary.json"

COMPARISON_FIELDS = [
    "strategy_id",
    "sector_id",
    "label_en",
    "label_zh",
    "governance_group",
    "strategy_return",
    "annualized_return",
    "benchmark_return",
    "excess_return",
    "max_drawdown",
    "sharpe",
    "information_ratio",
    "strategy_volatility",
    "benchmark_volatility",
    "daily_count",
    "comparison_window_start",
    "comparison_window_end",
    "comparison_window_policy",
    "benchmark_type",
    "benchmark_id",
    "is_directly_comparable_to_v57f",
    "order_health_status",
    "eligible_for_core",
    "can_promote_to_v57f",
    "exclusion_reason",
    "allowed_next_action",
    "blocked_action",
    "next_gate",
    "source_summary_path",
]


@dataclass(frozen=True)
class ComparisonItem:
    strategy_id: str
    sector_id: str
    label_en: str
    label_zh: str
    governance_group: str
    summary_path: Path
    comparison_window_policy: str
    benchmark_type: str
    benchmark_id: str
    is_directly_comparable_to_v57f: str
    eligible_for_core: str
    can_promote_to_v57f: str
    exclusion_reason: str
    allowed_next_action: str
    blocked_action: str
    next_gate: str


@dataclass(frozen=True)
class EnhancedEtfComparisonResult:
    output_dir: Path
    all_csv: Path
    best_csv: Path
    core_csv: Path
    observation_csv: Path
    summary_json: Path
    report_path: Path
    row_count: int


DEFAULT_ITEMS = [
    ComparisonItem(
        strategy_id="dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f",
        sector_id="enhanced_etf_basket",
        label_en="V57f enhanced ETF basket",
        label_zh="V57f 红利低波现金流增强 ETF",
        governance_group="current_best",
        summary_path=Path("local_daily_backtests_v57f_etf")
        / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
        / "summary.json",
        comparison_window_policy="basket local daily window; platform confirmation only, not acceptance evidence",
        benchmark_type="same_pool_equal_weight_total_return_proxy",
        benchmark_id="v57f_same_pool_equal_weight",
        is_directly_comparable_to_v57f="yes",
        eligible_for_core="yes",
        can_promote_to_v57f="already_current_frozen_mainline",
        exclusion_reason="",
        allowed_next_action="Wait for 2026-10-08 clean paper signal or JoinQuant exports for daily attribution.",
        blocked_action="Do not tune, accept, or mark platform_replication_passed from local performance alone.",
        next_gate="wait_until_2026_10_08_or_joinquant_exports_for_daily_attribution",
    ),
    ComparisonItem(
        strategy_id="bank_high_dividend_sustainability_v3",
        sector_id="bank",
        label_en="Bank V3 sleeve",
        label_zh="银行 V3 袖子",
        governance_group="core_sleeve",
        summary_path=Path("local_daily_backtests_v3_formal_candidate_extended_202604")
        / "bank_high_dividend_sustainability_v3"
        / "summary.json",
        comparison_window_policy="single sleeve local daily window; not a full ETF replacement",
        benchmark_type="sector_or_etf_proxy",
        benchmark_id="bank_sector_proxy",
        is_directly_comparable_to_v57f="no",
        eligible_for_core="yes",
        can_promote_to_v57f="already_in_core_refresh_only",
        exclusion_reason="Single sleeve result cannot replace the frozen basket by return ranking.",
        allowed_next_action="Refresh PIT panel, dividends, order health and paper signal without tuning.",
        blocked_action="Do not change frozen V57f sleeve logic from this comparison.",
        next_gate="core_sleeve_refresh_only",
    ),
    ComparisonItem(
        strategy_id="utilities_demand_state_v51f",
        sector_id="utilities_electricity",
        label_en="Utilities / electricity V5.1f sleeve",
        label_zh="公共服务/电力 V5.1f 袖子",
        governance_group="core_sleeve",
        summary_path=Path("local_daily_backtests_utilities_v51f") / "utilities_demand_state_v51f" / "summary.json",
        comparison_window_policy="single sleeve local daily window; golden template, not a full ETF replacement",
        benchmark_type="sector_benchmark",
        benchmark_id="utilities_sector_proxy",
        is_directly_comparable_to_v57f="no",
        eligible_for_core="yes",
        can_promote_to_v57f="already_in_core_refresh_only",
        exclusion_reason="Golden sleeve evidence is useful as a template but not directly comparable to the basket.",
        allowed_next_action="Keep as golden template and refresh paper-trading inputs.",
        blocked_action="Do not use high single-sleeve return to retune V57f.",
        next_gate="golden_template_refresh_only",
    ),
    ComparisonItem(
        strategy_id="highway_dividend_reviewed_operating_v54h_repaired_2021",
        sector_id="highway_infrastructure",
        label_en="Highway infrastructure V5.4h sleeve",
        label_zh="高速公路运营 V5.4h 袖子",
        governance_group="core_sleeve",
        summary_path=Path("local_daily_backtests_highway_v54h_repaired_2021_final")
        / "highway_dividend_reviewed_operating_v54h_repaired_2021"
        / "summary.json",
        comparison_window_policy="single sleeve local daily window; not a full ETF replacement",
        benchmark_type="sector_benchmark",
        benchmark_id="highway_transport_proxy",
        is_directly_comparable_to_v57f="no",
        eligible_for_core="yes",
        can_promote_to_v57f="already_in_core_refresh_only",
        exclusion_reason="Single sleeve, shorter governance history than V57f.",
        allowed_next_action="Refresh local daily and order-health evidence only.",
        blocked_action="Do not promote by return ranking or tune V57f.",
        next_gate="core_sleeve_refresh_only",
    ),
    ComparisonItem(
        strategy_id="port_rail_cashflow_value_operating_diagnostic_v55j_reviewed_business_sources",
        sector_id="port_rail_infrastructure",
        label_en="Port / rail infrastructure V5.5j sleeve",
        label_zh="港口/铁路基础设施 V5.5j 袖子",
        governance_group="core_sleeve",
        summary_path=Path("local_daily_backtests_port_rail_v55j_reviewed_business_sources")
        / "port_rail_cashflow_value_operating_diagnostic_v55j_reviewed_business_sources"
        / "summary.json",
        comparison_window_policy="single sleeve local daily window; not a full ETF replacement",
        benchmark_type="sector_benchmark",
        benchmark_id="port_rail_transport_proxy",
        is_directly_comparable_to_v57f="no",
        eligible_for_core="yes",
        can_promote_to_v57f="already_in_core_refresh_only",
        exclusion_reason="Pending platform/paper maturity; single sleeve cannot replace V57f.",
        allowed_next_action="Refresh local daily and order-health evidence only.",
        blocked_action="Do not promote by return ranking or tune V57f.",
        next_gate="core_sleeve_refresh_only",
    ),
    ComparisonItem(
        strategy_id="gas_water_v57b_text_debt_state_guard_v59b",
        sector_id="gas_water_operators",
        label_en="Gas / water V5.9b observation sleeve",
        label_zh="燃气/水务 V5.9b 观察袖子",
        governance_group="observation",
        summary_path=Path("local_daily_backtests_v59b_gas_water_state_guard_repaired_2021_07")
        / "gas_water_v57b_text_debt_state_guard_v59b"
        / "summary.json",
        comparison_window_policy="observation sleeve local daily window; not direct V57f comparison",
        benchmark_type="sector_benchmark",
        benchmark_id="gas_water_sector_proxy",
        is_directly_comparable_to_v57f="no",
        eligible_for_core="no",
        can_promote_to_v57f="no",
        exclusion_reason="Rank 1 observation sleeve, but core inclusion still requires separate PM gate and clean paper evidence.",
        allowed_next_action="Paper tracking only; refresh future signal when the clean window arrives.",
        blocked_action="Do not add to frozen V57f or optimize by 2021-2026 return.",
        next_gate="wait_for_next_clean_forward_rebalance_signal",
    ),
    ComparisonItem(
        strategy_id="insurance_pev_value_v53g",
        sector_id="insurance",
        label_en="Insurance V5.3g observation sleeve",
        label_zh="保险 V5.3g 观察袖子",
        governance_group="observation",
        summary_path=Path("local_daily_backtests_insurance_v53g") / "insurance_pev_value_v53g" / "summary.json",
        comparison_window_policy="specialist small-sample local daily window; not direct V57f comparison",
        benchmark_type="sector_benchmark",
        benchmark_id="insurance_sector_proxy",
        is_directly_comparable_to_v57f="no",
        eligible_for_core="no",
        can_promote_to_v57f="no",
        exclusion_reason="Insurance needs specialist EV/NBV/P/EV and has small-sample concentration risk.",
        allowed_next_action="Platform attribution or paper tracking only; no return tuning.",
        blocked_action="Do not add to core ETF without specialist-data PM approval.",
        next_gate="export_joinquant_daily_transaction_position_log_for_attribution",
    ),
    ComparisonItem(
        strategy_id="dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay",
        sector_id="telecom_operators",
        label_en="Telecom overlay observation sleeve",
        label_zh="电信运营商观察袖子",
        governance_group="observation",
        summary_path=Path("local_daily_backtests_v58_telecom_overlay_matched")
        / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay"
        / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay"
        / "summary.json",
        comparison_window_policy="overlay basket window; sample is too small for direct replacement comparison",
        benchmark_type="same_pool_or_overlay_proxy",
        benchmark_id="telecom_overlay_proxy",
        is_directly_comparable_to_v57f="no",
        eligible_for_core="no",
        can_promote_to_v57f="no",
        exclusion_reason="Telecom sample is small and overlay construction is not the same contract as V57f.",
        allowed_next_action="Observation/paper tracking only.",
        blocked_action="Do not promote to V57f from overlay return.",
        next_gate="small_sample_observation_only",
    ),
    ComparisonItem(
        strategy_id="home_appliances_ocf_quality_v5a5c",
        sector_id="home_appliances",
        label_en="Home appliances V5a.5e observation sleeve",
        label_zh="家电 V5a.5e 观察袖子",
        governance_group="observation",
        summary_path=Path("local_daily_backtests_home_appliances_v5a5e")
        / "home_appliances_ocf_quality_v5a5c"
        / "summary.json",
        comparison_window_policy="observation sleeve local daily window; high return is not promotion evidence",
        benchmark_type="sector_benchmark",
        benchmark_id="home_appliances_sector_proxy",
        is_directly_comparable_to_v57f="no",
        eligible_for_core="no",
        can_promote_to_v57f="no",
        exclusion_reason="Observation candidate; promotion queue does not allow core inclusion yet.",
        allowed_next_action="Paper tracking and source-state review.",
        blocked_action="Do not add to V57f or retune V57f weights from this result.",
        next_gate="pm_review_for_observation_sleeve_or_paper_tracking",
    ),
    ComparisonItem(
        strategy_id="oil_gas_state_conditioned_ocf_v58g",
        sector_id="oil_gas_pipeline_integrated",
        label_en="Oil / gas V5.8g observation sleeve",
        label_zh="油气管道/综合能源 V5.8g 观察袖子",
        governance_group="observation",
        summary_path=Path("validation_daily_v58h_oil_gas_sector_benchmark")
        / "oil_gas_state_conditioned_ocf_v58g"
        / "summary.json",
        comparison_window_policy="cycle/state-conditioned local daily window; not direct V57f comparison",
        benchmark_type="sector_benchmark",
        benchmark_id="oil_gas_sector_proxy",
        is_directly_comparable_to_v57f="no",
        eligible_for_core="no",
        can_promote_to_v57f="no",
        exclusion_reason="External state and platform/paper event are pending; high return is not core evidence.",
        allowed_next_action="Wait for external platform or forward event; no tuning.",
        blocked_action="Do not add to V57f by historical return.",
        next_gate="external_event_or_platform_export_wait",
    ),
    ComparisonItem(
        strategy_id="food_beverage_packaged_food_ocf_quality_v5a9a",
        sector_id="food_beverage",
        label_en="Food / beverage V5a.9a repair sleeve",
        label_zh="食品饮料 V5a.9a 修复袖子",
        governance_group="blocked_or_failed",
        summary_path=Path("local_daily_backtests_food_beverage_v5a9")
        / "food_beverage_packaged_food_ocf_quality_v5a9a"
        / "summary.json",
        comparison_window_policy="engineering-needs-review local daily window; not direct V57f comparison",
        benchmark_type="sector_benchmark",
        benchmark_id="food_beverage_sector_proxy",
        is_directly_comparable_to_v57f="no",
        eligible_for_core="no",
        can_promote_to_v57f="no",
        exclusion_reason="Order-health/dividend issues still need PM review before any sleeve decision.",
        allowed_next_action="Repair order health and dividend evidence.",
        blocked_action="Do not include in core or paper basket before engineering review clears.",
        next_gate="rebalance_order_health_review_gate",
    ),
    ComparisonItem(
        strategy_id="coal_cashflow_cycle_value_v52b_capex_policy",
        sector_id="coal",
        label_en="Coal V5.2b failed high-return sample",
        label_zh="煤炭 V5.2b 失败高收益样本",
        governance_group="blocked_or_failed",
        summary_path=Path("local_daily_backtests_coal_v52b")
        / "coal_cashflow_cycle_value_v52b_capex_policy"
        / "summary.json",
        comparison_window_policy="failed candidate local daily window; cyclical data gate failed",
        benchmark_type="sector_benchmark",
        benchmark_id="coal_sector_proxy",
        is_directly_comparable_to_v57f="no",
        eligible_for_core="no",
        can_promote_to_v57f="no",
        exclusion_reason="Failed candidate despite high return; official cycle state and PIT business exposure data gates remain incomplete.",
        allowed_next_action="Archive or repair commodity/output/inventory/spread and segment PIT data only.",
        blocked_action="Do not rerun factor tuning or add to V57f.",
        next_gate="cyclical_sector_data_gate_repair_only",
    ),
]


def build_v57f_comparison_packet(
    out_dir: Path = DEFAULT_OUT_DIR,
    production_summary_path: Path = DEFAULT_PRODUCTION_SUMMARY,
    *,
    items: list[ComparisonItem] | None = None,
) -> EnhancedEtfComparisonResult:
    comparison_items = items or DEFAULT_ITEMS
    rows = [_build_row(item) for item in comparison_items]
    _assert_clean_labels(rows)
    _assert_order_health_status(rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    all_csv = out_dir / "v57f_best_and_sector_comparison.csv"
    best_csv = out_dir / "v57f_best_version_metrics.csv"
    core_csv = out_dir / "v57f_core_sleeve_comparison.csv"
    observation_csv = out_dir / "v57f_observation_blocked_comparison.csv"
    summary_json = out_dir / "v57f_comparison_summary.json"
    report_path = out_dir / "v57f_comparison_report.md"

    best_rows = [row for row in rows if row["governance_group"] == "current_best"]
    core_rows = [row for row in rows if row["governance_group"] in {"current_best", "core_sleeve"}]
    observation_rows = [row for row in rows if row["governance_group"] in {"observation", "blocked_or_failed"}]

    write_csv_rows(all_csv, COMPARISON_FIELDS, rows)
    write_csv_rows(best_csv, COMPARISON_FIELDS, best_rows)
    write_csv_rows(core_csv, COMPARISON_FIELDS, core_rows)
    write_csv_rows(observation_csv, COMPARISON_FIELDS, observation_rows)

    production_summary = _read_json_if_exists(production_summary_path)
    summary = _build_summary(rows, production_summary, all_csv, best_csv, core_csv, observation_csv, report_path)
    write_json_file(summary_json, summary)
    report_path.write_text(_build_report(summary, best_rows, core_rows, observation_rows), encoding="utf-8")

    return EnhancedEtfComparisonResult(
        output_dir=out_dir,
        all_csv=all_csv,
        best_csv=best_csv,
        core_csv=core_csv,
        observation_csv=observation_csv,
        summary_json=summary_json,
        report_path=report_path,
        row_count=len(rows),
    )


def _build_row(item: ComparisonItem) -> dict[str, Any]:
    payload = _read_json_if_exists(item.summary_path)
    metrics = payload.get("metrics", {}) if isinstance(payload, dict) else {}
    window = payload.get("window", {}) if isinstance(payload, dict) else {}
    start = str(window.get("start_date") or "")
    end = str(window.get("end_date") or "")
    daily_count = payload.get("daily_count", "")
    if (not start or not end or daily_count == "") and item.summary_path.exists():
        daily_path = item.summary_path.parent / "daily_returns.csv"
        inferred = _infer_daily_window(daily_path)
        start = start or inferred["start"]
        end = end or inferred["end"]
        daily_count = daily_count if daily_count != "" else inferred["daily_count"]

    return {
        "strategy_id": item.strategy_id,
        "sector_id": item.sector_id,
        "label_en": item.label_en,
        "label_zh": item.label_zh,
        "governance_group": item.governance_group,
        "strategy_return": _metric(metrics, "strategy_return"),
        "annualized_return": _metric(metrics, "annualized_return"),
        "benchmark_return": _metric(metrics, "benchmark_return"),
        "excess_return": _metric(metrics, "excess_return"),
        "max_drawdown": _metric(metrics, "max_drawdown"),
        "sharpe": _metric(metrics, "sharpe"),
        "information_ratio": _metric(metrics, "information_ratio"),
        "strategy_volatility": _metric(metrics, "strategy_volatility"),
        "benchmark_volatility": _metric(metrics, "benchmark_volatility"),
        "daily_count": daily_count,
        "comparison_window_start": start,
        "comparison_window_end": end,
        "comparison_window_policy": item.comparison_window_policy,
        "benchmark_type": item.benchmark_type,
        "benchmark_id": item.benchmark_id,
        "is_directly_comparable_to_v57f": item.is_directly_comparable_to_v57f,
        "order_health_status": _order_health_status(payload),
        "eligible_for_core": item.eligible_for_core,
        "can_promote_to_v57f": item.can_promote_to_v57f,
        "exclusion_reason": item.exclusion_reason,
        "allowed_next_action": item.allowed_next_action,
        "blocked_action": item.blocked_action,
        "next_gate": item.next_gate,
        "source_summary_path": str(item.summary_path),
    }


def _metric(metrics: dict[str, Any], key: str) -> Any:
    value = metrics.get(key)
    if isinstance(value, float):
        return f"{value:.12g}"
    return "" if value is None else value


def _order_health_status(payload: dict[str, Any]) -> str:
    health = payload.get("rebalance_order_health") if isinstance(payload, dict) else None
    if not isinstance(health, dict) or not health:
        return "unknown"
    if bool(health.get("needs_review")):
        return "needs_review"
    return "pass"


def _infer_daily_window(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"start": "", "end": "", "daily_count": ""}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        dates = []
        for row in reader:
            date_value = row.get("date") or row.get("trade_date") or row.get("datetime") or row.get("day")
            if date_value:
                dates.append(str(date_value)[:10])
    return {
        "start": dates[0] if dates else "",
        "end": dates[-1] if dates else "",
        "daily_count": len(dates),
    }


def _build_summary(
    rows: list[dict[str, Any]],
    production_summary: dict[str, Any],
    all_csv: Path,
    best_csv: Path,
    core_csv: Path,
    observation_csv: Path,
    report_path: Path,
) -> dict[str, Any]:
    group_counts: dict[str, int] = {}
    order_health_counts: dict[str, int] = {}
    for row in rows:
        group_counts[str(row["governance_group"])] = group_counts.get(str(row["governance_group"]), 0) + 1
        order_health_counts[str(row["order_health_status"])] = order_health_counts.get(str(row["order_health_status"]), 0) + 1
    return {
        "schema_version": 1,
        "created_at_utc": _now(),
        "strategy_id": "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f",
        "status": "comparison_packet_hardened_not_strategy_acceptance",
        "production_line_status": production_summary.get("status", ""),
        "pm_gate_status": _safe_nested(production_summary, ["evidence", "pm_gate_summary", "status"]),
        "dashboard_status": _safe_nested(production_summary, ["evidence", "dashboard_summary", "status"]),
        "action_route_status": _safe_nested(production_summary, ["evidence", "action_route_summary", "status"]),
        "not_status": [
            "platform_replication_passed",
            "accepted_strategy",
            "live_trading_approved",
        ],
        "next_clean_rebalance_date": production_summary.get("next_clean_rebalance_date", "2026-10-08"),
        "next_gate": "wait_until_2026_10_08_or_joinquant_exports_for_daily_attribution",
        "row_count": len(rows),
        "group_counts": group_counts,
        "order_health_counts": order_health_counts,
        "outputs": {
            "all_csv": str(all_csv),
            "best_csv": str(best_csv),
            "core_csv": str(core_csv),
            "observation_csv": str(observation_csv),
            "report": str(report_path),
        },
        "pm_rules": [
            "Rows with different windows, benchmarks or portfolio contracts are not directly comparable to V57f.",
            "High-return non-mainline rows must keep eligible_for_core=false unless a separate PM promotion gate passes.",
            "Blank order-health values are forbidden; unknown is not pass.",
            "Historical performance alone is never sufficient evidence for accepting a strategy.",
        ],
    }


def _build_report(
    summary: dict[str, Any],
    best_rows: list[dict[str, Any]],
    core_rows: list[dict[str, Any]],
    observation_rows: list[dict[str, Any]],
) -> str:
    best = best_rows[0] if best_rows else {}
    lines = [
        "# V57f Governed Comparison Packet",
        "",
        f"Created at UTC: `{summary['created_at_utc']}`",
        "",
        "## PM Conclusion",
        "",
        "V57f remains the frozen mainline enhanced ETF candidate. It is not accepted, not live-trading approved, and not platform-replication passed.",
        "",
        f"Next gate: `{summary['next_gate']}`.",
        "",
        "## Best Version Snapshot",
        "",
        "| Strategy | Return | Benchmark | Excess | Max drawdown | Sharpe | Order health |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    if best:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{best['strategy_id']}`",
                    _pct(best["strategy_return"]),
                    _pct(best["benchmark_return"]),
                    _pct(best["excess_return"]),
                    _pct(best["max_drawdown"]),
                    _num(best["sharpe"]),
                    f"`{best['order_health_status']}`",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Core Sleeve View",
            "",
            "These rows support sleeve monitoring. They are not direct replacements for the full V57f basket.",
            "",
            "| Sector | Return | Benchmark | Window | Directly comparable | Order health | Next gate |",
            "| --- | ---: | ---: | --- | --- | --- | --- |",
        ]
    )
    for row in core_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['sector_id']}`",
                    _pct(row["strategy_return"]),
                    _pct(row["benchmark_return"]),
                    f"{row['comparison_window_start']} to {row['comparison_window_end']}",
                    row["is_directly_comparable_to_v57f"],
                    f"`{row['order_health_status']}`",
                    f"`{row['next_gate']}`",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Observation / Blocked View",
            "",
            "High historical return in this table is explicitly not a promotion signal.",
            "",
            "| Sector | Return | Governance group | Core eligible | Order health | Exclusion reason |",
            "| --- | ---: | --- | --- | --- | --- |",
        ]
    )
    for row in observation_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['sector_id']}`",
                    _pct(row["strategy_return"]),
                    f"`{row['governance_group']}`",
                    row["eligible_for_core"],
                    f"`{row['order_health_status']}`",
                    row["exclusion_reason"],
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- Do not sort all rows by return and treat the top sector as a replacement for V57f.",
            "- `unknown` order health is not a pass.",
            "- Observation sleeves require a separate PM promotion gate before any basket inclusion.",
            "- Coal remains a failed high-return example unless its cyclical data gate is reopened and repaired.",
            "",
        ]
    )
    return "\n".join(lines)


def _pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return ""


def _num(value: Any) -> str:
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return ""


def _assert_clean_labels(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        for field in ["label_en", "label_zh"]:
            value = str(row.get(field) or "")
            if "??" in value or "\ufffd" in value:
                raise ValueError(f"mojibake label detected in {field}: {value}")


def _assert_order_health_status(rows: list[dict[str, Any]]) -> None:
    allowed = {"pass", "needs_review", "unknown", "not_applicable"}
    for row in rows:
        value = str(row.get("order_health_status") or "")
        if value not in allowed:
            raise ValueError(f"invalid order_health_status for {row.get('sector_id')}: {value}")


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        return {}
    return payload


def _safe_nested(payload: dict[str, Any], keys: list[str]) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
    return "" if current is None else current


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

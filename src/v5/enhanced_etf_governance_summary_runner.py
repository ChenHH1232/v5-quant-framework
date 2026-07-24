from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows_if_exists, write_csv_rows, write_json_file
from v5.math_utils import to_float


DEFAULT_STATUS_REGISTRY = Path("docs/governance/status_registry.json")
DEFAULT_PRODUCTION_SUMMARY = Path("enhanced_etf_production_lines_v5") / "current" / "production_line_summary.json"
DEFAULT_SLEEVE_REGISTRY = Path("enhanced_etf_production_lines_v5") / "current" / "sleeve_registry.csv"
DEFAULT_OUT_DIR = Path("enhanced_etf_governance_v5") / "current"
DEFAULT_MAIN_STRATEGY_ID = "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
DEFAULT_PROMOTION_AUDIT = DEFAULT_OUT_DIR / "promotion_policy" / "sleeve_promotion_eligibility_audit.csv"

CORE_FIELDS = [
    "row_type",
    "sector_id",
    "strategy_id",
    "role",
    "governance_status",
    "strategy_return",
    "max_drawdown",
    "information_ratio",
    "order_health_status",
    "paper_status",
    "can_change_v57f",
    "allowed_next_action",
    "blocked_action",
    "next_gate",
    "source_summary_path",
]

OBSERVATION_FIELDS = [
    "sector_id",
    "strategy_id",
    "label_en",
    "observation_class",
    "latest_stage",
    "strategy_return",
    "max_drawdown",
    "information_ratio",
    "order_health_status",
    "paper_tracking_status",
    "promotion_decision",
    "can_promote_to_core_candidate",
    "required_next_evidence",
    "can_join_v57f_core",
    "can_platform_replication",
    "allowed_next_action",
    "blocked_action",
    "next_gate",
    "source_summary_path",
]

QUEUE_FIELDS = ["queue_rank", "owner", "task", "input_artifacts", "output_artifacts", "gate", "blocked_actions"]


@dataclass(frozen=True)
class ObservationSpec:
    sector_id: str
    strategy_id: str
    label_en: str
    observation_class: str
    summary_path: Path
    paper_summary_path: Path | None
    allowed_next_action: str
    blocked_action: str
    next_gate: str


@dataclass(frozen=True)
class EnhancedEtfGovernanceSummaryResult:
    output_dir: Path
    summary_json: Path
    report_md: Path
    core_dashboard_csv: Path
    observation_registry_csv: Path
    next_agent_queue_csv: Path
    status: str


OBSERVATION_SPECS = [
    ObservationSpec(
        "gas_water_operators",
        "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57g_gas_water_observation",
        "Gas / water observation basket",
        "observation_basket",
        Path("local_daily_backtests_v57g_gas_water_observation_etf")
        / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57g_gas_water_observation"
        / "summary.json",
        Path("paper_trading_signals")
        / "gas_water_v59b_promotion_queue"
        / "gas_water_v57b_text_debt_state_guard_v59b"
        / "gas_water_paper_tracking_summary.json",
        "Keep paper tracking only; do not add to frozen V57f.",
        "do_not_modify_V57f;do_not_tune;do_not_platform_replication",
        "wait_until_clean_forward_window",
    ),
    ObservationSpec(
        "telecom_operators",
        "dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay",
        "Telecom capped observation overlay",
        "small_sample_capped_observation",
        Path("local_daily_backtests_v5a_telecom_observation_refresh")
        / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay"
        / "summary.json",
        Path("paper_trading_signals")
        / "telecom_v5a_observation_queue"
        / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay"
        / "telecom_paper_tracking_summary.json",
        "Keep capped paper tracking only.",
        "do_not_modify_V57f;do_not_tune;do_not_promote_standalone;do_not_platform_replication",
        "wait_until_clean_forward_window",
    ),
    ObservationSpec(
        "home_appliances",
        "home_appliances_ocf_quality_v5a5c",
        "Home appliances observation sleeve",
        "observation_paper_tracking_candidate",
        Path("local_daily_backtests_home_appliances_v5a5e") / "home_appliances_ocf_quality_v5a5c" / "summary.json",
        Path("paper_trading_signals")
        / "home_appliances_v5a5e_promotion_queue"
        / "home_appliances_ocf_quality_v5a5c"
        / "home_appliances_paper_tracking_summary.json",
        "Observation paper tracking and source-state review only.",
        "do_not_modify_V57f;do_not_tune;do_not_add_to_core_by_return",
        "pm_review_for_observation_sleeve_or_paper_tracking",
    ),
    ObservationSpec(
        "insurance",
        "insurance_pev_value_v53g",
        "Insurance specialist observation",
        "specialist_small_sample_observation",
        Path("local_daily_backtests_insurance_v53g") / "insurance_pev_value_v53g" / "summary.json",
        Path("docs/governance/v53g_insurance_forward_paper_trading_log.md"),
        "Specialist paper record or platform attribution only; no return tuning.",
        "do_not_add_to_core_without_EV_NBV_policy;do_not_tune",
        "track_v53g_platform_replication_and_paper_trading",
    ),
    ObservationSpec(
        "oil_gas_pipeline_integrated",
        "oil_gas_state_conditioned_ocf_v58g",
        "Oil / gas observation",
        "cycle_state_observation",
        Path("validation_daily_v58h_oil_gas_sector_benchmark") / "oil_gas_state_conditioned_ocf_v58g" / "summary.json",
        None,
        "Wait for external event or platform export; no tuning.",
        "do_not_modify_V57f;do_not_promote_by_return;do_not_skip_cycle_state_gate",
        "external_event_or_platform_export_wait",
    ),
    ObservationSpec(
        "food_beverage",
        "food_beverage_packaged_food_ocf_quality_v5a9a",
        "Food / beverage engineering review",
        "engineering_review_or_research_repair",
        Path("local_daily_backtests_food_beverage_v5a9") / "food_beverage_packaged_food_ocf_quality_v5a9a" / "summary.json",
        None,
        "Repair or explain order-health and dividend blockers before any paper tracking.",
        "do_not_modify_V57f;do_not_tune;do_not_ignore_order_health",
        "engineering_repair_or_archive",
    ),
    ObservationSpec(
        "coal",
        "coal_cashflow_cycle_value_v52b",
        "Coal archived data-gate case",
        "archived_data_gate_failed",
        Path("local_daily_backtests_coal_v52b") / "coal_cashflow_cycle_value_v52b_capex_policy" / "summary.json",
        None,
        "Keep archived unless official cycle data gate is repaired.",
        "do_not_model_without_cycle_state;do_not_promote_by_high_return",
        "cyclical_sector_data_gate_repair_only",
    ),
]


def build_enhanced_etf_governance_summary(
    *,
    status_registry: Path = DEFAULT_STATUS_REGISTRY,
    production_summary: Path = DEFAULT_PRODUCTION_SUMMARY,
    sleeve_registry: Path = DEFAULT_SLEEVE_REGISTRY,
    promotion_audit: Path = DEFAULT_PROMOTION_AUDIT,
    out_dir: Path = DEFAULT_OUT_DIR,
    main_strategy_id: str = DEFAULT_MAIN_STRATEGY_ID,
) -> EnhancedEtfGovernanceSummaryResult:
    registry = _read_json(status_registry)
    production = _read_json(production_summary)
    sleeve_rows = read_csv_rows_if_exists(sleeve_registry)
    promotion_rows = {str(row.get("sector_id") or ""): row for row in read_csv_rows_if_exists(promotion_audit)}
    registry_by_id = {str(item.get("strategy_id") or ""): item for item in registry.get("strategies", [])}

    main = registry_by_id.get(main_strategy_id, {})
    core_rows = _core_rows(main_strategy_id, main, production, sleeve_rows)
    observation_rows = [
        _observation_row(spec, registry_by_id.get(spec.strategy_id, {}), promotion_rows.get(spec.sector_id, {}))
        for spec in OBSERVATION_SPECS
    ]
    next_queue = _next_queue(core_rows, observation_rows)
    status = "v57f_core_and_observation_governance_completed"

    out_dir.mkdir(parents=True, exist_ok=True)
    core_dashboard_csv = out_dir / "v57f_core_dashboard.csv"
    observation_registry_csv = out_dir / "observation_sleeve_registry.csv"
    next_agent_queue_csv = out_dir / "governance_next_agent_queue.csv"
    summary_json = out_dir / "enhanced_etf_governance_summary.json"
    report_md = out_dir / "enhanced_etf_governance_report.md"

    write_csv_rows(core_dashboard_csv, CORE_FIELDS, core_rows, encoding="utf-8-sig")
    write_csv_rows(observation_registry_csv, OBSERVATION_FIELDS, observation_rows, encoding="utf-8-sig")
    write_csv_rows(next_agent_queue_csv, QUEUE_FIELDS, next_queue, encoding="utf-8-sig")
    summary = {
        "schema_version": 1,
        "project": "v5_enhanced_etf_governance_summary",
        "strategy_id": main_strategy_id,
        "experiment_layer": "pm_decision_gate",
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "core_sleeve_count": sum(1 for row in core_rows if row["row_type"] == "core_sleeve"),
        "observation_sleeve_count": len(observation_rows),
        "mainline_decision": "V57f remains frozen mainline; no sleeve, factor, weight, sector-cap, rebalance, or timing change.",
        "paper_runner_scope": "excluded_from_this_run",
        "paper_runner_note": "Future 2026-10 paper refresh belongs to a separate simulation/paper workflow, not this V5 governance summary.",
        "core_status_counts": _count(core_rows, "governance_status"),
        "observation_stage_counts": _count(observation_rows, "latest_stage"),
        "promotion_decision_counts": _count(observation_rows, "promotion_decision"),
        "outputs": {
            "core_dashboard_csv": str(core_dashboard_csv),
            "observation_registry_csv": str(observation_registry_csv),
            "next_agent_queue_csv": str(next_agent_queue_csv),
            "report_md": str(report_md),
        },
        "source_paths": {
            "status_registry": str(status_registry),
            "production_summary": str(production_summary),
            "sleeve_registry": str(sleeve_registry),
            "promotion_audit": str(promotion_audit),
        },
        "pm_rules": [
            "Historical performance alone cannot promote an observation sleeve.",
            "Observation sleeves cannot enter V57f core without a separate PM stage gate.",
            "This run does not update or generate the 2026-10 paper runner.",
            "Platform replication and accepted/live statuses remain blocked unless their own evidence gates pass.",
        ],
    }
    write_json_file(summary_json, summary)
    report_md.write_text(_report(summary, core_rows, observation_rows, next_queue), encoding="utf-8")

    return EnhancedEtfGovernanceSummaryResult(
        output_dir=out_dir,
        summary_json=summary_json,
        report_md=report_md,
        core_dashboard_csv=core_dashboard_csv,
        observation_registry_csv=observation_registry_csv,
        next_agent_queue_csv=next_agent_queue_csv,
        status=status,
    )


def _core_rows(main_strategy_id: str, main: dict[str, Any], production: dict[str, Any], sleeve_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    daily = production.get("evidence", {}).get("daily_summary", {})
    metrics = daily.get("metrics", {}) if isinstance(daily, dict) else {}
    order = daily.get("rebalance_order_health", {}) if isinstance(daily, dict) else {}
    rows = [
        {
            "row_type": "mainline_basket",
            "sector_id": "enhanced_etf_basket",
            "strategy_id": main_strategy_id,
            "role": "frozen_mainline",
            "governance_status": _status_label(main),
            "strategy_return": _num(metrics.get("strategy_return")),
            "max_drawdown": _num(metrics.get("max_drawdown")),
            "information_ratio": _num(metrics.get("information_ratio")),
            "order_health_status": _order_status(order),
            "paper_status": _paper_status(main),
            "can_change_v57f": "no",
            "allowed_next_action": "Maintain frozen state and consume only externally approved evidence.",
            "blocked_action": "do_not_tune;do_not_add_observation_sleeves;do_not_mark_accepted",
            "next_gate": str(main.get("next_gate") or production.get("registry_next_gate") or ""),
            "source_summary_path": str(daily.get("path") or ""),
        }
    ]
    for sleeve in sleeve_rows:
        if str(sleeve.get("is_active_v57f_sleeve") or "") != "yes":
            continue
        rows.append(
            {
                "row_type": "core_sleeve",
                "sector_id": sleeve.get("sector_id", ""),
                "strategy_id": "",
                "role": sleeve.get("basket_role", ""),
                "governance_status": "core_frozen_refresh_only",
                "strategy_return": "",
                "max_drawdown": "",
                "information_ratio": "",
                "order_health_status": "covered_by_mainline_order_health",
                "paper_status": "covered_by_mainline_future_window",
                "can_change_v57f": "no",
                "allowed_next_action": "Refresh source data and local health only when PM opens a refresh window.",
                "blocked_action": "do_not_change_core_membership_or_weights",
                "next_gate": "core_refresh_only",
                "source_summary_path": "",
            }
        )
    return rows


def _observation_row(spec: ObservationSpec, registry_item: dict[str, Any], promotion: dict[str, str]) -> dict[str, Any]:
    summary = _read_json(spec.summary_path)
    metrics = summary.get("metrics", {}) if isinstance(summary, dict) else {}
    order = summary.get("rebalance_order_health", {}) if isinstance(summary, dict) else {}
    paper_status = _paper_file_status(spec.paper_summary_path)
    return {
        "sector_id": spec.sector_id,
        "strategy_id": spec.strategy_id,
        "label_en": spec.label_en,
        "observation_class": spec.observation_class,
        "latest_stage": _observation_stage(registry_item, spec, summary),
        "strategy_return": _num(metrics.get("strategy_return")),
        "max_drawdown": _num(metrics.get("max_drawdown")),
        "information_ratio": _num(metrics.get("information_ratio")),
        "order_health_status": _order_status(order),
        "paper_tracking_status": paper_status,
        "promotion_decision": promotion.get("promotion_decision", "promotion_audit_not_run"),
        "can_promote_to_core_candidate": promotion.get("can_promote_to_core_candidate", "no"),
        "required_next_evidence": promotion.get("required_next_evidence", "run sleeve_promotion_policy_v1 audit"),
        "can_join_v57f_core": "no",
        "can_platform_replication": "no",
        "allowed_next_action": spec.allowed_next_action,
        "blocked_action": spec.blocked_action,
        "next_gate": str(registry_item.get("next_gate") or spec.next_gate),
        "source_summary_path": str(spec.summary_path),
    }


def _observation_stage(registry_item: dict[str, Any], spec: ObservationSpec, summary: dict[str, Any]) -> str:
    statuses = set(str(item) for item in registry_item.get("current_status", []))
    if "waiting_for_clean_forward_window" in statuses or "paper_tracking_preparation_ready" in statuses:
        return "paper_tracking_ready_waiting"
    if "engineering_local_refresh_passed" in statuses or "engineering_local_daily_simulation_completed" in statuses:
        return "engineering_local_refresh_passed"
    if "strategy_candidate_failed" in statuses or spec.observation_class.startswith("archived"):
        return "archived_or_failed"
    if "not_engineering_handoff" in statuses:
        return "research_or_data_repair"
    if summary:
        return "local_summary_available_needs_pm_review"
    return "missing_or_blocked"


def _next_queue(core_rows: list[dict[str, Any]], observation_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "queue_rank": "1",
            "owner": "Project Manager Agent",
            "task": "Keep V57f frozen and use this governance summary as the single status entry point.",
            "input_artifacts": "enhanced_etf_governance_summary.json;v57f_core_dashboard.csv;observation_sleeve_registry.csv",
            "output_artifacts": "none",
            "gate": "governance_reference_only",
            "blocked_actions": "do_not_modify_V57f;do_not_start_paper_runner_here;do_not_promote_observation_sleeves",
        },
        {
            "queue_rank": "2",
            "owner": "Project Manager Agent",
            "task": "When a separate simulation/paper workflow is opened, use this table to decide which sleeves are eligible for refresh.",
            "input_artifacts": "observation_sleeve_registry.csv",
            "output_artifacts": "separate_future_workflow_only",
            "gate": "external_or_future_window_only",
            "blocked_actions": "do_not_mix_future_paper_runner_into_this_v5_governance_package",
        },
    ]


def _report(summary: dict[str, Any], core_rows: list[dict[str, Any]], observation_rows: list[dict[str, Any]], next_queue: list[dict[str, str]]) -> str:
    lines = [
        "# Enhanced ETF Governance Summary",
        "",
        f"Status: `{summary['status']}`",
        "",
        "## Mainline",
        "",
        "V57f remains the frozen mainline. This package does not change sleeves, factors, weights, timing, or any future paper runner.",
        "",
        "| Type | Sector | Status | Return | Drawdown | Order health | Next gate |",
        "| --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in core_rows:
        lines.append(
            f"| `{row['row_type']}` | `{row['sector_id']}` | `{row['governance_status']}` | {_pct(row['strategy_return'])} | {_pct(row['max_drawdown'])} | `{row['order_health_status']}` | `{row['next_gate']}` |"
        )
    lines.extend(
        [
            "",
            "## Observation Sleeves",
            "",
            "| Sector | Class | Stage | Promotion decision | Return | Drawdown | Paper | Required next evidence |",
            "| --- | --- | --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    for row in observation_rows:
        lines.append(
            f"| `{row['sector_id']}` | `{row['observation_class']}` | `{row['latest_stage']}` | `{row['promotion_decision']}` | {_pct(row['strategy_return'])} | {_pct(row['max_drawdown'])} | `{row['paper_tracking_status']}` | {row['required_next_evidence']} |"
        )
    lines.extend(["", "## Next Queue", "", "| Rank | Owner | Task | Gate |", "| ---: | --- | --- | --- |"])
    for row in next_queue:
        lines.append(f"| {row['queue_rank']} | {row['owner']} | {row['task']} | `{row['gate']}` |")
    lines.extend(["", "## Rules", ""])
    for rule in summary["pm_rules"]:
        lines.append(f"- {rule}")
    lines.append("")
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def _status_label(item: dict[str, Any]) -> str:
    statuses = [str(value) for value in item.get("current_status", [])]
    if "accepted_strategy" in statuses:
        return "invalid_accepted_status_needs_review"
    if "formal_etf_candidate" in statuses:
        return "formal_etf_candidate_frozen_not_accepted"
    return statuses[0] if statuses else "unknown"


def _paper_status(item: dict[str, Any]) -> str:
    statuses = set(str(value) for value in item.get("current_status", []))
    if "waiting_for_future_refresh_window" in statuses or "queued_for_future_refresh_window" in statuses:
        return "waiting_for_future_window"
    if "paper_trading_process_started" in statuses:
        return "paper_process_started"
    return "not_started_or_unknown"


def _paper_file_status(path: Path | None) -> str:
    if path is None:
        return "not_applicable_or_missing"
    return "paper_artifact_exists" if path.exists() else "missing"


def _order_status(order: dict[str, Any]) -> str:
    if not order:
        return "unknown"
    if bool(order.get("needs_review")):
        return "needs_review"
    return "passed"


def _count(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        key = str(row.get(field) or "")
        result[key] = result.get(key, 0) + 1
    return result


def _num(value: Any) -> str:
    parsed = to_float(value)
    return "" if parsed is None else f"{parsed:.12g}"


def _pct(value: Any) -> str:
    parsed = to_float(value)
    return "" if parsed is None else f"{parsed * 100:.2f}%"

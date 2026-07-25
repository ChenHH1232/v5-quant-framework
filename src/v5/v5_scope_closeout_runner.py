from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows_if_exists, write_csv_rows, write_json_file
from v5.math_utils import to_float


DEFAULT_OUT_DIR = Path("v5_scope_closeout") / "current"
DEFAULT_ALL_CANDIDATES = Path("sector_extension_all_candidates_v5") / "current" / "all_candidates_status_matrix.csv"
DEFAULT_V57F_SUMMARY = (
    Path("local_daily_backtests_v57f_etf")
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
    / "summary.json"
)
DEFAULT_FOOD_REVIEW = Path("food_beverage_engineering_reviews_v5") / "current" / "food_beverage_engineering_review_summary.json"
DEFAULT_SCOPE_END_DATE = "2026-05-31"

FLOW_FIELDS = ["step", "stage", "owner", "input", "action", "output", "gate", "forbidden_action"]
STATUS_FIELDS = [
    "candidate_id",
    "role",
    "v5_final_status",
    "engineering_window_end",
    "engineering_status",
    "v5_scope_future_signal_policy",
    "core_promotion_allowed",
    "platform_replication_allowed",
    "food_beverage_pm_decision",
    "main_reason",
    "allowed_next_action_inside_v5",
    "blocked_action",
    "evidence_primary",
    "evidence_secondary",
]
FOOD_DECISION_FIELDS = [
    "decision_id",
    "status",
    "strategy_return",
    "max_drawdown",
    "first_signal_date",
    "partial_skipped_order_count",
    "high_cash_rebalance_dates",
    "startup_gap_status",
    "dividend_status",
    "pm_decision",
    "allowed_next_action",
    "blocked_action",
]
QUEUE_FIELDS = ["queue_rank", "owner", "task", "input_artifacts", "output_artifacts", "gate", "blocked_actions"]


@dataclass(frozen=True)
class V5ScopeCloseoutResult:
    output_dir: Path
    flow_table_csv: Path
    final_status_csv: Path
    food_decision_csv: Path
    food_decision_json: Path
    summary_json: Path
    report_md: Path
    next_queue_csv: Path
    status: str


def build_v5_scope_closeout_packet(
    *,
    all_candidates_csv: Path = DEFAULT_ALL_CANDIDATES,
    v57f_summary: Path = DEFAULT_V57F_SUMMARY,
    food_review_json: Path = DEFAULT_FOOD_REVIEW,
    out_dir: Path = DEFAULT_OUT_DIR,
    scope_end_date: str = DEFAULT_SCOPE_END_DATE,
    as_of_date: str = "2026-07-25",
) -> V5ScopeCloseoutResult:
    candidates = read_csv_rows_if_exists(all_candidates_csv)
    v57f = _read_json(v57f_summary)
    food_review = _read_json(food_review_json)
    food_decision = _food_beverage_decision(food_review)
    status_rows = _status_rows(
        candidates=candidates,
        v57f=v57f,
        food_decision=food_decision,
        scope_end_date=scope_end_date,
        v57f_summary=v57f_summary,
    )
    flow_rows = _flow_rows(scope_end_date)
    next_queue = _next_queue(status_rows)
    status = "v5_scope_closed_local_engineering_to_2026_05_31"

    out_dir.mkdir(parents=True, exist_ok=True)
    flow_table_csv = out_dir / "v5_scope_boundary_flow_table.csv"
    final_status_csv = out_dir / "v5_final_candidate_status.csv"
    food_decision_csv = out_dir / "food_beverage_pm_tradability_decision.csv"
    food_decision_json = out_dir / "food_beverage_pm_tradability_decision.json"
    summary_json = out_dir / "v5_scope_closeout_summary.json"
    report_md = out_dir / "v5_scope_closeout_report.md"
    next_queue_csv = out_dir / "v5_scope_next_queue.csv"

    write_csv_rows(flow_table_csv, FLOW_FIELDS, flow_rows, encoding="utf-8-sig")
    write_csv_rows(final_status_csv, STATUS_FIELDS, status_rows, encoding="utf-8-sig")
    write_csv_rows(food_decision_csv, FOOD_DECISION_FIELDS, [food_decision], encoding="utf-8-sig")
    write_json_file(food_decision_json, food_decision)
    write_csv_rows(next_queue_csv, QUEUE_FIELDS, next_queue, encoding="utf-8-sig")

    summary = {
        "schema_version": 1,
        "project": "v5_scope_closeout",
        "experiment_layer": "pm_scope_boundary",
        "status": status,
        "as_of_date": as_of_date,
        "scope_end_date": scope_end_date,
        "scope_rule": "V5 local engineering and JoinQuant-aligned backtest evidence ends at 2026-05-31. Future/paper signals are outside V5 scope.",
        "candidate_count": len(status_rows),
        "core_promotion_allowed_count": sum(1 for row in status_rows if row["core_promotion_allowed"] == "yes"),
        "platform_replication_allowed_count": sum(1 for row in status_rows if row["platform_replication_allowed"] == "yes"),
        "food_beverage_pm_decision": food_decision["pm_decision"],
        "outputs": {
            "flow_table_csv": str(flow_table_csv),
            "final_status_csv": str(final_status_csv),
            "food_decision_csv": str(food_decision_csv),
            "food_decision_json": str(food_decision_json),
            "next_queue_csv": str(next_queue_csv),
            "report_md": str(report_md),
        },
        "inputs": {
            "all_candidates_csv": str(all_candidates_csv),
            "v57f_summary": str(v57f_summary),
            "food_review_json": str(food_review_json),
        },
        "pm_rules": [
            "Do not wait for or generate a 2026-10 signal inside V5.",
            "Do not add observation sleeves to frozen V57f from this closeout.",
            "Do not tune historical 2021-2026 results.",
            "Food/beverage is adjudicated by tradability, PIT coverage, drawdown and contribution quality, not by a single skipped order.",
        ],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_json_file(summary_json, summary)
    report_md.write_text(_report(summary, flow_rows, status_rows, food_decision, next_queue), encoding="utf-8")

    return V5ScopeCloseoutResult(
        output_dir=out_dir,
        flow_table_csv=flow_table_csv,
        final_status_csv=final_status_csv,
        food_decision_csv=food_decision_csv,
        food_decision_json=food_decision_json,
        summary_json=summary_json,
        report_md=report_md,
        next_queue_csv=next_queue_csv,
        status=status,
    )


def _status_rows(
    *,
    candidates: list[dict[str, str]],
    v57f: dict[str, Any],
    food_decision: dict[str, str],
    scope_end_date: str,
    v57f_summary: Path,
) -> list[dict[str, str]]:
    rows = [_v57f_row(v57f, scope_end_date, v57f_summary)]
    for candidate in candidates:
        rows.append(_candidate_row(candidate, food_decision, scope_end_date))
    return rows


def _v57f_row(v57f: dict[str, Any], scope_end_date: str, evidence: Path) -> dict[str, str]:
    window = v57f.get("window", {}) if isinstance(v57f, dict) else {}
    metrics = v57f.get("metrics", {}) if isinstance(v57f, dict) else {}
    return {
        "candidate_id": str(v57f.get("strategy_id") or "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"),
        "role": "frozen_mainline",
        "v5_final_status": "formal_etf_candidate_frozen_local_engineering_scope_closed",
        "engineering_window_end": str(window.get("end_date") or scope_end_date),
        "engineering_status": "local_daily_completed",
        "v5_scope_future_signal_policy": "outside_v5_scope",
        "core_promotion_allowed": "not_applicable_current_mainline",
        "platform_replication_allowed": "no",
        "food_beverage_pm_decision": "",
        "main_reason": f"V57f remains frozen; local return={metrics.get('strategy_return', '')}, max_drawdown={metrics.get('max_drawdown', '')}; platform replication is outside this closeout.",
        "allowed_next_action_inside_v5": "none_scope_closed",
        "blocked_action": "do_not_tune;do_not_wait_for_2026_10_inside_v5;do_not_mark_accepted",
        "evidence_primary": str(evidence),
        "evidence_secondary": "",
    }


def _candidate_row(candidate: dict[str, str], food_decision: dict[str, str], scope_end_date: str) -> dict[str, str]:
    sector_id = candidate.get("sector_id", "")
    engineering = candidate.get("engineering_test_status", "")
    if sector_id == "food_beverage":
        return _base_candidate(
            candidate,
            "observation_candidate_closed_failed_pm_tradability_review",
            "closed_in_v5",
            "not_applicable",
            food_decision["pm_decision"],
            food_decision["status"],
            "none_scope_closed_unless_new_research_hypothesis",
            "order/cash/PIT/drawdown quality is not sufficient for observation promotion inside V5",
            scope_end_date,
        )
    if sector_id == "gas_water_operators":
        return _base_candidate(candidate, "engineering_passed_observation_parked_v5_scope_closed", "passed", "outside_v5_scope", "", "none", "none_scope_closed", "engineering passed; observation only; V5 does not wait for future paper signals", scope_end_date)
    if sector_id == "home_appliances":
        return _base_candidate(candidate, "engineering_passed_observation_high_drawdown_v5_scope_closed", "passed", "outside_v5_scope", "", "high_drawdown_review", "none_scope_closed", "engineering passed but drawdown/state risk blocks core promotion", scope_end_date)
    if sector_id == "telecom_operators":
        return _base_candidate(candidate, "capped_observation_engineering_passed_v5_scope_closed", "passed", "outside_v5_scope", "", "small_sample_policy", "none_scope_closed", "small sample blocks ordinary core sleeve treatment", scope_end_date)
    if sector_id == "insurance":
        return _base_candidate(candidate, "specialist_observation_local_smoke_refreshed_v5_scope_closed", engineering, "outside_v5_scope", "", "specialist_order_health_not_standardized", "optional_backlog_standardize_order_health", "specialist EV/NBV small-sample policy remains outside ordinary sleeve promotion", scope_end_date)
    if sector_id == "oil_gas_pipeline_integrated":
        return _base_candidate(candidate, "research_data_gate_partial_v5_blocked", "not_allowed", "outside_v5_scope", "", "missing_inventory_demand_and_pipeline_policy_state", "optional_backlog_repair_data_gate", "promotion state sources incomplete", scope_end_date)
    if sector_id == "consumer_staples_cashflow":
        return _base_candidate(candidate, "research_signal_only_not_engineering_handoff_v5_scope_closed", "not_allowed", "outside_v5_scope", "", "PIT_source_contract_not_engineering_ready", "optional_backlog_research_repair", "research signal exists but source contract is not Engineering-ready", scope_end_date)
    return _base_candidate(candidate, "parked_unknown_v5_scope_closed", engineering or "unknown", "outside_v5_scope", "", "unknown", "none_scope_closed", "no route", scope_end_date)


def _base_candidate(
    candidate: dict[str, str],
    final_status: str,
    engineering_status: str,
    future_policy: str,
    food_decision: str,
    blocker: str,
    allowed_action: str,
    reason: str,
    scope_end_date: str,
) -> dict[str, str]:
    return {
        "candidate_id": candidate.get("sector_id", ""),
        "role": "observation_or_repair_candidate",
        "v5_final_status": final_status,
        "engineering_window_end": scope_end_date,
        "engineering_status": engineering_status,
        "v5_scope_future_signal_policy": future_policy,
        "core_promotion_allowed": "no",
        "platform_replication_allowed": "no",
        "food_beverage_pm_decision": food_decision,
        "main_reason": reason,
        "allowed_next_action_inside_v5": allowed_action,
        "blocked_action": "do_not_modify_V57f;do_not_tune;do_not_start_joinquant_test;do_not_wait_for_2026_10_inside_v5",
        "evidence_primary": candidate.get("primary_evidence", ""),
        "evidence_secondary": candidate.get("secondary_evidence", ""),
    }


def _food_beverage_decision(review: dict[str, Any]) -> dict[str, str]:
    metrics = review.get("local_metrics", {}) if isinstance(review, dict) else {}
    order = review.get("order_health", {}) if isinstance(review, dict) else {}
    startup = review.get("startup_gap", {}) if isinstance(review, dict) else {}
    dividend = review.get("dividend_gap", {}) if isinstance(review, dict) else {}
    strategy_return = to_float(metrics.get("strategy_return")) or 0.0
    max_drawdown = to_float(metrics.get("max_drawdown")) or 0.0
    partial_skips = int(order.get("partial_skipped_order_count") or 0)
    first_signal_date = str(startup.get("first_signal_date") or "")
    status = "closed_failed_v5_observation_candidate"
    pm_decision = "archive_in_v5_do_not_promote_to_observation_or_engineering_next_layer"
    allowed_next_action = "only_restart_with_new_research_hypothesis_and_repaired_2021_PIT_contract"
    blocked_action = "modify_V57f_or_start_platform_replication_or_tune_food_beverage_returns"
    if strategy_return > 0.25 and max_drawdown < 0.30 and partial_skips == 0 and not startup.get("has_startup_gap"):
        status = "review_passed_observation_possible"
        pm_decision = "observation_possible_but_still_no_core_promotion"
        allowed_next_action = "PM may open a separate observation gate"
    return {
        "decision_id": "food_beverage_pm_tradability_decision_v1",
        "status": status,
        "strategy_return": f"{strategy_return:.10g}",
        "max_drawdown": f"{max_drawdown:.10g}",
        "first_signal_date": first_signal_date,
        "partial_skipped_order_count": str(partial_skips),
        "high_cash_rebalance_dates": ";".join(order.get("high_cash_rebalance_dates") or []),
        "startup_gap_status": str(startup.get("status") or ""),
        "dividend_status": str(dividend.get("status") or ""),
        "pm_decision": pm_decision,
        "allowed_next_action": allowed_next_action,
        "blocked_action": blocked_action,
    }


def _flow_rows(scope_end_date: str) -> list[dict[str, str]]:
    return [
        _flow("1", "Scope boundary", "PM Agent", "current V5 outputs", f"Lock V5 local engineering window to {scope_end_date}", "scope boundary packet", "joinquant_aligned_window", "wait_for_or_generate_future_signal_inside_v5"),
        _flow("2", "Candidate inventory", "PM Agent", "all_candidates_status_matrix.csv", "Load V57f plus all observation / repair candidates", "final candidate status table", "one_row_per_candidate", "drop_failed_or_uncomfortable_candidates"),
        _flow("3", "Future signal cleanup", "PM Agent", "paper readiness artifacts", "Classify future signal references as outside V5 scope", "outside_v5_scope policy", "no_2026_10_dependency", "treat_future_signal_as_v5_next_step"),
        _flow("4", "Food/beverage PM decision", "PM Agent", "food_beverage_engineering_review_summary.json", "Judge tradability, PIT startup gap, return quality and drawdown", "food decision packet", "pm_tradability_decision", "tune_food_beverage_returns"),
        _flow("5", "Final closeout", "PM Agent", "all evidence", "Write final status, allowed actions and blocked actions", "V5 closeout report", "no_core_promotion_from_this_run", "modify_V57f_or_start_platform_replication"),
    ]


def _flow(step: str, stage: str, owner: str, input_path: str, action: str, output: str, gate: str, forbidden: str) -> dict[str, str]:
    return {
        "step": step,
        "stage": stage,
        "owner": owner,
        "input": input_path,
        "action": action,
        "output": output,
        "gate": gate,
        "forbidden_action": forbidden,
    }


def _next_queue(status_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    optional = [row for row in status_rows if row["allowed_next_action_inside_v5"].startswith("optional_backlog")]
    if not optional:
        return [
            {
                "queue_rank": "1",
                "owner": "Project Manager Agent",
                "task": "No required V5 action remains. Keep V57f frozen and treat future/forward records as outside V5.",
                "input_artifacts": "v5_final_candidate_status.csv",
                "output_artifacts": "scope_closed_checkpoint",
                "gate": "v5_scope_closed",
                "blocked_actions": "do_not_wait_for_2026_10_inside_v5;do_not_tune;do_not_modify_V57f",
            }
        ]
    queue: list[dict[str, str]] = []
    for index, row in enumerate(optional, start=1):
        queue.append(
            {
                "queue_rank": str(index),
                "owner": "Backlog Agent",
                "task": f"{row['candidate_id']}: {row['allowed_next_action_inside_v5']}",
                "input_artifacts": row["evidence_primary"],
                "output_artifacts": "optional_backlog_packet",
                "gate": row["allowed_next_action_inside_v5"],
                "blocked_actions": row["blocked_action"],
            }
        )
    return queue


def _report(
    summary: dict[str, Any],
    flow_rows: list[dict[str, str]],
    status_rows: list[dict[str, str]],
    food_decision: dict[str, str],
    next_queue: list[dict[str, str]],
) -> str:
    lines = [
        "# V5 Scope Closeout",
        "",
        f"- Status: `{summary['status']}`",
        f"- Scope end date: `{summary['scope_end_date']}`",
        f"- Rule: {summary['scope_rule']}",
        f"- Core promotion allowed count: `{summary['core_promotion_allowed_count']}`",
        f"- Platform replication allowed count: `{summary['platform_replication_allowed_count']}`",
        "",
        "## Detailed Flow",
        "",
        "| Step | Stage | Owner | Input | Action | Output | Gate | Forbidden Action |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in flow_rows:
        lines.append(f"| {row['step']} | {row['stage']} | {row['owner']} | `{row['input']}` | {row['action']} | `{row['output']}` | `{row['gate']}` | `{row['forbidden_action']}` |")
    lines.extend(["", "## Food/Beverage PM Decision", ""])
    lines.append(f"- Status: `{food_decision['status']}`")
    lines.append(f"- PM decision: `{food_decision['pm_decision']}`")
    lines.append(f"- Strategy return: `{food_decision['strategy_return']}`")
    lines.append(f"- Max drawdown: `{food_decision['max_drawdown']}`")
    lines.append(f"- First signal date: `{food_decision['first_signal_date']}`")
    lines.append(f"- Partial skipped orders: `{food_decision['partial_skipped_order_count']}`")
    lines.extend(["", "## Final Candidate Status", "", "| Candidate | Role | Final Status | Engineering | Future Signal Policy | Main Reason |", "| --- | --- | --- | --- | --- | --- |"])
    for row in status_rows:
        lines.append(f"| {row['candidate_id']} | {row['role']} | `{row['v5_final_status']}` | `{row['engineering_status']}` | `{row['v5_scope_future_signal_policy']}` | {row['main_reason']} |")
    lines.extend(["", "## Next Queue", "", "| Rank | Owner | Task | Gate |", "| ---: | --- | --- | --- |"])
    for row in next_queue:
        lines.append(f"| {row['queue_rank']} | {row['owner']} | {row['task']} | `{row['gate']}` |")
    lines.extend(
        [
            "",
            "## PM Closeout",
            "",
            "- V5 no longer waits for or generates a 2026-10 signal.",
            "- Local Engineering evidence is capped at 2026-05-31 to match the current JoinQuant backtest window.",
            "- V57f remains a frozen formal ETF candidate, not an accepted strategy.",
        ]
    )
    return "\n".join(lines) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}

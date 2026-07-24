from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows_if_exists, write_csv_rows, write_json_file


DEFAULT_PROMOTION_QUEUE = Path("enhanced_etf_production_lines_v5") / "current" / "sleeve_promotion_queue.csv"
DEFAULT_OUT_DIR = Path("sector_extension_all_candidates_v5") / "current"

FLOW_FIELDS = ["step", "stage", "owner", "input", "action", "output", "gate", "forbidden_action"]
STATUS_FIELDS = [
    "sector_id",
    "rank",
    "display_name",
    "execution_status",
    "furthest_stage_reached",
    "can_enter_engineering_now",
    "engineering_test_status",
    "paper_tracking_status",
    "core_promotion_allowed",
    "main_blocker",
    "allowed_next_action",
    "blocked_action",
    "primary_evidence",
    "secondary_evidence",
]
QUEUE_FIELDS = ["queue_rank", "sector_id", "owner", "task", "input_artifacts", "output_artifacts", "gate", "blocked_actions"]


@dataclass(frozen=True)
class SectorExtensionAllCandidatesResult:
    output_dir: Path
    flow_table_csv: Path
    status_matrix_csv: Path
    summary_json: Path
    report_md: Path
    next_agent_queue_csv: Path
    status: str


def summarize_sector_extension_all_candidates(
    *,
    promotion_queue: Path = DEFAULT_PROMOTION_QUEUE,
    out_dir: Path = DEFAULT_OUT_DIR,
    as_of_date: str = "2026-07-24",
) -> SectorExtensionAllCandidatesResult:
    promotion_rows = read_csv_rows_if_exists(promotion_queue)
    status_rows = [_candidate_status(row) for row in promotion_rows]
    next_queue = _next_queue(status_rows)
    flow_rows = _flow_rows()
    status = "all_candidates_advanced_and_classified"
    if any(row["execution_status"].endswith("needs_review") for row in status_rows):
        status = "all_candidates_advanced_with_review_items"

    out_dir.mkdir(parents=True, exist_ok=True)
    flow_table_csv = out_dir / "all_candidates_execution_flow_table.csv"
    status_matrix_csv = out_dir / "all_candidates_status_matrix.csv"
    next_agent_queue_csv = out_dir / "all_candidates_next_agent_queue.csv"
    summary_json = out_dir / "all_candidates_execution_summary.json"
    report_md = out_dir / "all_candidates_execution_report.md"

    write_csv_rows(flow_table_csv, FLOW_FIELDS, flow_rows, encoding="utf-8-sig")
    write_csv_rows(status_matrix_csv, STATUS_FIELDS, status_rows, encoding="utf-8-sig")
    write_csv_rows(next_agent_queue_csv, QUEUE_FIELDS, next_queue, encoding="utf-8-sig")

    summary = {
        "schema_version": 1,
        "project": "v5_sector_extension_all_candidates",
        "experiment_layer": "pm_execution_closeout",
        "status": status,
        "as_of_date": as_of_date,
        "candidate_count": len(status_rows),
        "status_counts": _count(status_rows, "execution_status"),
        "engineering_passed_count": sum(1 for row in status_rows if row["engineering_test_status"] == "passed"),
        "paper_ready_count": sum(1 for row in status_rows if row["paper_tracking_status"] == "ready_waiting_future_window"),
        "core_promotion_allowed_count": sum(1 for row in status_rows if row["core_promotion_allowed"] == "yes"),
        "outputs": {
            "flow_table_csv": str(flow_table_csv),
            "status_matrix_csv": str(status_matrix_csv),
            "next_agent_queue_csv": str(next_agent_queue_csv),
            "report_md": str(report_md),
        },
        "pm_rules": [
            "Every candidate is advanced to its currently allowed furthest gate.",
            "V57f remains frozen; no observation sleeve is added to core.",
            "Historical return does not decide promotion.",
            "Engineering means local daily simulation plus trades, holdings, dividends and rebalance/order-health evidence when the runner supports it.",
            "This packet does not start JoinQuant platform replication and does not generate a 2026-10 live paper signal.",
        ],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_json_file(summary_json, summary)
    report_md.write_text(_report(summary, flow_rows, status_rows, next_queue), encoding="utf-8")
    return SectorExtensionAllCandidatesResult(
        output_dir=out_dir,
        flow_table_csv=flow_table_csv,
        status_matrix_csv=status_matrix_csv,
        summary_json=summary_json,
        report_md=report_md,
        next_agent_queue_csv=next_agent_queue_csv,
        status=status,
    )


def _candidate_status(row: dict[str, str]) -> dict[str, str]:
    sector_id = row.get("sector_id", "")
    if sector_id == "gas_water_operators":
        return _gas_water(row)
    if sector_id == "home_appliances":
        return _home_appliances(row)
    if sector_id == "telecom_operators":
        return _telecom(row)
    if sector_id == "food_beverage":
        return _food_beverage(row)
    if sector_id == "oil_gas_pipeline_integrated":
        return _oil_gas(row)
    if sector_id == "insurance":
        return _insurance(row)
    if sector_id == "consumer_staples_cashflow":
        return _consumer_staples(row)
    return _base(row, "not_executed_unknown_candidate", "unknown", "no", "unknown", "unknown", "no", "unknown", "Keep parked until PM adds a route.", "")


def _gas_water(row: dict[str, str]) -> dict[str, str]:
    paper = Path("paper_trading_signals/gas_water_v59b_promotion_queue/gas_water_v57b_text_debt_state_guard_v59b/gas_water_paper_tracking_summary.json")
    local = Path("local_daily_backtests_v59b_gas_water_state_guard_repaired_2021_07/gas_water_v57b_text_debt_state_guard_v59b/summary.json")
    paper_payload = _read_json(paper)
    local_payload = _read_json(local)
    return _base(
        row,
        "observation_paper_ready",
        "engineering_local_daily_plus_paper_preparation",
        "no",
        "passed" if _local_passed(local_payload) else "needs_review",
        _paper_status(paper_payload),
        "no",
        "none",
        "Wait for clean future paper window; do not add to V57f.",
        str(paper),
        str(local),
    )


def _home_appliances(row: dict[str, str]) -> dict[str, str]:
    paper = Path("paper_trading_signals/home_appliances_v5a5e_promotion_queue/home_appliances_ocf_quality_v5a5c/home_appliances_paper_tracking_summary.json")
    local = Path("local_daily_backtests_home_appliances_v5a5e/home_appliances_ocf_quality_v5a5c/summary.json")
    paper_payload = _read_json(paper)
    local_payload = _read_json(local)
    return _base(
        row,
        "observation_paper_ready_high_drawdown_review",
        "engineering_local_daily_plus_paper_preparation",
        "no",
        "passed" if _local_passed(local_payload) else "needs_review",
        _paper_status(paper_payload),
        "no",
        "high_drawdown_review_before_any_future_core_policy",
        "Keep observation paper tracking only; review drawdown and industry state ex ante.",
        str(paper),
        str(local),
    )


def _telecom(row: dict[str, str]) -> dict[str, str]:
    execution = Path("telecom_engineering_execution_v5/current/telecom_engineering_execution_summary.json")
    readiness = Path("telecom_engineering_readiness_v5/current/telecom_engineering_readiness_summary.json")
    payload = _read_json(execution)
    return _base(
        row,
        "capped_observation_paper_ready",
        "small_sample_engineering_refresh_plus_paper_preparation",
        "no",
        "passed" if str(payload.get("status", "")).startswith("paper_tracking_ready") else "needs_review",
        "ready_waiting_future_window" if str(payload.get("status", "")).startswith("paper_tracking_ready") else "needs_review",
        "no",
        "sample_size_too_small_for_ordinary_core_sleeve",
        "Keep capped observation only; do not use as ordinary V57f sleeve.",
        str(execution),
        str(readiness),
    )


def _food_beverage(row: dict[str, str]) -> dict[str, str]:
    review = Path("food_beverage_engineering_reviews_v5/current/food_beverage_engineering_review_summary.json")
    local = Path("local_daily_backtests_food_beverage_v5a9/food_beverage_packaged_food_ocf_quality_v5a9a/summary.json")
    payload = _read_json(review)
    return _base(
        row,
        "engineering_review_completed_needs_pm_tradability_review",
        "local_daily_plus_engineering_blocker_review",
        "no",
        "needs_review",
        "not_ready",
        "no",
        str(payload.get("next_gate") or "tradability_and_cash_drag_review"),
        "PM must decide whether price-limit skips/cash drag block observation tracking.",
        str(review),
        str(local),
    )


def _oil_gas(row: dict[str, str]) -> dict[str, str]:
    summary = Path("数据库/processed/oil_gas_source_gate_v58e/oil_gas_source_gate_summary.json")
    payload = _read_json(summary)
    promotion_ready = bool(payload.get("promotion_ready"))
    return _base(
        row,
        "research_data_gate_partial",
        "official_state_source_gate",
        "no",
        "not_allowed",
        "not_ready",
        "no",
        "missing_inventory_demand_and_pipeline_policy_state" if not promotion_ready else "none",
        "Keep parked until promotion state sources are completed.",
        str(summary),
        "",
    )


def _insurance(row: dict[str, str]) -> dict[str, str]:
    local = Path("local_daily_backtests_insurance_v53g/insurance_pev_value_v53g/summary.json")
    ev = Path("insurance_ev_nbv_panel_v53g_2020_2025/insurance_pev_value_v53g/ev_nbv_panel_summary.json")
    local_payload = _read_json(local)
    return _base(
        row,
        "specialist_observation_local_daily_refreshed",
        "specialist_ev_nbv_local_daily_smoke_test",
        "no",
        "passed_smoke_test_order_health_not_standardized" if _local_passed(local_payload) else "needs_review",
        "not_ready",
        "no",
        "small_sample_specialist_policy_and_standard_order_health_packet_required",
        "Keep specialist observation; standardize order-health before any paper/core route.",
        str(local),
        str(ev),
    )


def _consumer_staples(row: dict[str, str]) -> dict[str, str]:
    subsector = Path("validation_formal_v5a6_consumer_subsector/consumer_staples_cashflow/consumer_subsector_validation_summary.json")
    wc = Path("数据库/processed/consumer_working_capital_state_v5a6/consumer_staples_cashflow/working_capital_state_summary.json")
    payload = _read_json(subsector)
    return _base(
        row,
        "research_signal_found_not_engineering_handoff",
        "working_capital_state_plus_subsector_validation",
        "no",
        "not_allowed",
        "not_ready",
        "no",
        str(payload.get("status") or "research_repair_still_required"),
        "Return to Research/Quant; do not hand to Engineering until PIT/source contract is complete.",
        str(subsector),
        str(wc),
    )


def _base(
    row: dict[str, str],
    execution_status: str,
    furthest_stage: str,
    can_engineer: str,
    engineering_status: str,
    paper_status: str,
    can_core: str,
    blocker: str,
    allowed_action: str,
    primary: str,
    secondary: str = "",
) -> dict[str, str]:
    return {
        "sector_id": row.get("sector_id", ""),
        "rank": row.get("rank", ""),
        "display_name": row.get("display_name", ""),
        "execution_status": execution_status,
        "furthest_stage_reached": furthest_stage,
        "can_enter_engineering_now": can_engineer,
        "engineering_test_status": engineering_status,
        "paper_tracking_status": paper_status,
        "core_promotion_allowed": can_core,
        "main_blocker": blocker,
        "allowed_next_action": allowed_action,
        "blocked_action": "do_not_modify_V57f;do_not_tune;do_not_start_joinquant_test;do_not_claim_accepted",
        "primary_evidence": primary,
        "secondary_evidence": secondary,
    }


def _next_queue(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    queue: list[dict[str, str]] = []
    for row in rows:
        status = row["execution_status"]
        if "needs_pm_tradability_review" in status:
            queue.append(_queue(len(queue) + 1, row, "Project Manager Agent", "Decide whether the explained food/beverage tradability and cash-drag issues block observation tracking.", "pm_tradability_review"))
        elif status == "research_signal_found_not_engineering_handoff":
            queue.append(_queue(len(queue) + 1, row, "Research Agent", "Repair consumer staples PIT/source contract and turn research signal into a Quant-ready hypothesis.", "research_repair"))
        elif status == "research_data_gate_partial":
            queue.append(_queue(len(queue) + 1, row, "Research Agent", "Complete oil/gas inventory-demand and pipeline-policy state sources before any Engineering route.", "data_gate_repair"))
        elif status == "specialist_observation_local_daily_refreshed":
            queue.append(_queue(len(queue) + 1, row, "Engineering Agent", "Standardize insurance rebalance_order_health packet if PM wants paper tracking later.", "specialist_order_health_standardization"))
    if not queue:
        queue.append(
            {
                "queue_rank": "1",
                "sector_id": "all",
                "owner": "Project Manager Agent",
                "task": "All candidates are parked in observation/wait states.",
                "input_artifacts": "all_candidates_status_matrix.csv",
                "output_artifacts": "pm_checkpoint",
                "gate": "no_action_until_external_event",
                "blocked_actions": "do_not_modify_V57f;do_not_tune",
            }
        )
    return queue


def _queue(rank: int, row: dict[str, str], owner: str, task: str, gate: str) -> dict[str, str]:
    return {
        "queue_rank": str(rank),
        "sector_id": row["sector_id"],
        "owner": owner,
        "task": task,
        "input_artifacts": row["primary_evidence"],
        "output_artifacts": "updated PM decision packet",
        "gate": gate,
        "blocked_actions": row["blocked_action"],
    }


def _flow_rows() -> list[dict[str, str]]:
    return [
        _flow("1", "Candidate queue", "PM Agent", "sleeve_promotion_queue.csv", "Load all current expansion candidates", "candidate universe", "all_candidates_present", "modify_V57f"),
        _flow("2", "Research/data gate", "Research Agent", "sector research artifacts", "Advance data-gated sectors to latest source gate", "research/data packets", "no_model_without_data_gate", "invent_missing_state_data"),
        _flow("3", "Quant/validation gate", "Quant Agent", "formal/local summaries", "Use existing frozen hypotheses only; no return tuning", "validation evidence", "frozen_logic", "change_weights_or_selection_count"),
        _flow("4", "Engineering gate", "Engineering Agent", "local daily runners", "Run or refresh local daily, dividends, trades, holdings and order-health where allowed", "engineering evidence", "local_only_no_joinquant", "start_platform_replication"),
        _flow("5", "Paper prep gate", "Engineering Agent", "passed engineering evidence", "Build readiness packet waiting for future clean window", "paper readiness", "no_late_signal_generation", "generate_2026_10_signal_now"),
        _flow("6", "PM closeout", "PM Agent", "all evidence", "Classify every candidate as observe, repair, wait or specialist", "status matrix", "one_status_per_candidate", "promote_by_backtest_return"),
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


def _paper_status(payload: dict[str, Any]) -> str:
    status = str(payload.get("status") or "")
    if status.startswith("paper_tracking_ready"):
        return "ready_waiting_future_window"
    return "needs_review" if status else "missing"


def _local_passed(payload: dict[str, Any]) -> bool:
    status = str(payload.get("status") or "")
    engineering_gate = str(payload.get("engineering_gate") or "")
    return "passed" in status or "passed" in engineering_gate or status.endswith("completed_not_platform_replication")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def _count(rows: list[dict[str, str]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = row.get(field, "")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _report(summary: dict[str, Any], flow_rows: list[dict[str, str]], status_rows: list[dict[str, str]], queue_rows: list[dict[str, str]]) -> str:
    lines = [
        "# V5 Sector Extension All-Candidates Execution",
        "",
        f"- Status: `{summary['status']}`",
        f"- Candidate count: `{summary['candidate_count']}`",
        f"- Engineering passed count: `{summary['engineering_passed_count']}`",
        f"- Paper-ready count: `{summary['paper_ready_count']}`",
        f"- Core promotion allowed count: `{summary['core_promotion_allowed_count']}`",
        "",
        "## Detailed Flow",
        "",
        "| Step | Stage | Owner | Input | Action | Output | Gate | Forbidden Action |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in flow_rows:
        lines.append(f"| {row['step']} | {row['stage']} | {row['owner']} | `{row['input']}` | {row['action']} | `{row['output']}` | `{row['gate']}` | `{row['forbidden_action']}` |")
    lines.extend(["", "## Candidate Status Matrix", "", "| Rank | Sector | Status | Engineering | Paper | Main Blocker | Next Action |", "| ---: | --- | --- | --- | --- | --- | --- |"])
    for row in status_rows:
        lines.append(
            f"| {row['rank']} | {row['sector_id']} | `{row['execution_status']}` | `{row['engineering_test_status']}` | `{row['paper_tracking_status']}` | {row['main_blocker']} | {row['allowed_next_action']} |"
        )
    lines.extend(["", "## Next Agent Queue", "", "| Rank | Sector | Owner | Task | Gate |", "| ---: | --- | --- | --- | --- |"])
    for row in queue_rows:
        lines.append(f"| {row['queue_rank']} | {row['sector_id']} | {row['owner']} | {row['task']} | `{row['gate']}` |")
    lines.extend(["", "## PM Closeout", "", "- V57f remains frozen.", "- No candidate is allowed to enter V57f core from this run.", "- Candidates that reached paper readiness are waiting for a clean future window, not a retroactive signal."])
    return "\n".join(lines) + "\n"

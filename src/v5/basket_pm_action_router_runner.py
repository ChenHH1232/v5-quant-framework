from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import write_json_file


DEFAULT_OUT_DIR = Path("basket_pm_action_routes")


@dataclass(frozen=True)
class BasketPMActionRouteResult:
    summary_path: Path
    report_path: Path
    route_status: str
    should_continue_agent_loop: bool
    user_decision_required: bool


def route_basket_pm_action(
    *,
    governance_dashboard_summary: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
    as_of_date: str | None = None,
) -> BasketPMActionRouteResult:
    dashboard = _read_json(governance_dashboard_summary)
    strategy_id = str(dashboard.get("strategy_id") or "basket_strategy")
    route = _route(dashboard)

    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "experiment_layer": "pm_decision_gate",
        "as_of_date": as_of_date,
        "dashboard_summary": str(governance_dashboard_summary),
        "dashboard_status": dashboard.get("status"),
        "route_status": route["route_status"],
        "pm_decision": route["pm_decision"],
        "should_continue_agent_loop": route["should_continue_agent_loop"],
        "user_decision_required": route["user_decision_required"],
        "user_decision_reason": route["user_decision_reason"],
        "next_owner": route["next_owner"],
        "allowed_next_action": route["allowed_next_action"],
        "next_trigger": route["next_trigger"],
        "blocked_actions": dashboard.get("blocked_actions", []),
        "source_statuses": dashboard.get("source_statuses", {}),
        "key_dates": dashboard.get("key_dates", {}),
        "checks": dashboard.get("checks", []),
        "pm_rule": "The PM router may only route existing evidence; it must not refresh data, run JoinQuant, tune parameters, or generate a signal.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    summary_path = out / "basket_pm_action_route_summary.json"
    report_path = out / "basket_pm_action_route_report.md"
    write_json_file(summary_path, summary)
    report_path.write_text(_report(summary), encoding="utf-8")
    return BasketPMActionRouteResult(
        summary_path=summary_path,
        report_path=report_path,
        route_status=route["route_status"],
        should_continue_agent_loop=route["should_continue_agent_loop"],
        user_decision_required=route["user_decision_required"],
    )


def _route(dashboard: dict[str, Any]) -> dict[str, Any]:
    status = str(dashboard.get("status") or "")
    source_statuses = dashboard.get("source_statuses") or {}
    key_dates = dashboard.get("key_dates") or {}
    next_rebalance = key_dates.get("next_rebalance_date")

    if status == "blocked":
        return {
            "route_status": "repair_blockers",
            "pm_decision": "stop_and_repair_blockers",
            "should_continue_agent_loop": False,
            "user_decision_required": False,
            "user_decision_reason": "",
            "next_owner": "Project Manager Agent",
            "allowed_next_action": "create_blocker_packet_then_assign_repair_owner",
            "next_trigger": "blocker packet created",
        }

    platform_status = str(source_statuses.get("platform_export_intake") or "")
    refresh_status = str(source_statuses.get("paper_refresh_status") or "")
    preflight_status = str(source_statuses.get("paper_input_preflight") or "")

    if platform_status == "ready_for_platform_attribution":
        return {
            "route_status": "platform_exports_ready",
            "pm_decision": "run_platform_attribution_without_tuning",
            "should_continue_agent_loop": True,
            "user_decision_required": False,
            "user_decision_reason": "",
            "next_owner": "Engineering Agent",
            "allowed_next_action": "run_platform_attribution_and_replication_packet_only",
            "next_trigger": "platform exports are present and non-empty",
        }

    if refresh_status == "ready_for_clean_paper_signal_gate" and preflight_status == "ready_to_construct_clean_paper_signal":
        return {
            "route_status": "clean_paper_signal_gate_ready",
            "pm_decision": "construct_clean_paper_signal_without_tuning",
            "should_continue_agent_loop": True,
            "user_decision_required": False,
            "user_decision_reason": "",
            "next_owner": "Engineering Agent",
            "allowed_next_action": "construct_clean_paper_signal_from_frozen_config_only",
            "next_trigger": "refresh status and preflight are ready",
        }

    if status == "frozen_candidate_waiting_for_future_paper_window_platform_deferred":
        return {
            "route_status": "no_action_until_external_event",
            "pm_decision": "hold_frozen_candidate",
            "should_continue_agent_loop": False,
            "user_decision_required": False,
            "user_decision_reason": "",
            "next_owner": "Project Manager Agent",
            "allowed_next_action": "wait_for_future_refresh_window_or_user_supplied_platform_exports",
            "next_trigger": f"{next_rebalance} refresh window or JoinQuant exports supplied by user",
        }

    if _is_external_wait_state(status, source_statuses):
        return {
            "route_status": "no_action_until_external_event",
            "pm_decision": "hold_frozen_candidate",
            "should_continue_agent_loop": False,
            "user_decision_required": False,
            "user_decision_reason": "",
            "next_owner": "Project Manager Agent",
            "allowed_next_action": "wait_for_future_refresh_window_or_user_supplied_platform_exports",
            "next_trigger": f"{next_rebalance} refresh window or JoinQuant exports supplied by user",
        }

    if status == "ready_for_pm_clean_paper_signal_gate":
        return {
            "route_status": "pm_gate_review_required",
            "pm_decision": "review_before_signal_generation",
            "should_continue_agent_loop": False,
            "user_decision_required": False,
            "user_decision_reason": "",
            "next_owner": "Project Manager Agent",
            "allowed_next_action": "review_dashboard_checks_then_route_to_engineering",
            "next_trigger": "PM gate review completed",
        }

    return {
        "route_status": "needs_pm_review",
        "pm_decision": "stop_and_review_missing_or_ambiguous_status",
        "should_continue_agent_loop": False,
        "user_decision_required": False,
        "user_decision_reason": "",
        "next_owner": "Project Manager Agent",
        "allowed_next_action": "inspect_governance_dashboard_and_source_summaries",
        "next_trigger": "ambiguous dashboard status resolved",
    }


def _is_external_wait_state(status: str, source_statuses: dict[str, Any]) -> bool:
    platform_status = str(source_statuses.get("platform_export_intake") or "")
    forward_status = str(source_statuses.get("forward_paper_gate") or "")
    refresh_status = str(source_statuses.get("paper_refresh_status") or "")
    preflight_status = str(source_statuses.get("paper_input_preflight") or "")
    queue_status = str(source_statuses.get("paper_refresh_queue") or "")
    return (
        status == "needs_pm_review"
        and platform_status in {"missing", "platform_test_deferred_by_user_waiting_for_exports"}
        and forward_status == "pending_clean_future_rebalance"
        and refresh_status == "waiting_for_future_refresh_window"
        and preflight_status == "pending_future_data_window"
        and queue_status == "queued_for_future_refresh_window"
    )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _report(summary: dict[str, Any]) -> str:
    lines = [
        f"# Basket PM Action Route: {summary['strategy_id']}",
        "",
        f"- Dashboard status: `{summary['dashboard_status']}`",
        f"- Route status: `{summary['route_status']}`",
        f"- PM decision: `{summary['pm_decision']}`",
        f"- Continue agent loop: `{summary['should_continue_agent_loop']}`",
        f"- User decision required: `{summary['user_decision_required']}`",
        f"- Next owner: `{summary['next_owner']}`",
        f"- Allowed next action: `{summary['allowed_next_action']}`",
        f"- Next trigger: `{summary['next_trigger']}`",
        "",
        "## Key Dates",
        "",
    ]
    for key, value in summary.get("key_dates", {}).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Source Statuses", ""])
    for key, value in summary.get("source_statuses", {}).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Blocked Actions", ""])
    for item in summary.get("blocked_actions", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## PM Rule", "", summary["pm_rule"]])
    return "\n".join(lines)

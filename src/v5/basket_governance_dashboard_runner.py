from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import write_json_file


DEFAULT_OUT_DIR = Path("basket_governance_dashboards")


@dataclass(frozen=True)
class BasketGovernanceDashboardResult:
    summary_path: Path
    report_path: Path
    status: str
    blocker_count: int
    needs_review_count: int


def build_basket_governance_dashboard(
    *,
    strategy_id: str,
    out_dir: Path = DEFAULT_OUT_DIR,
    pm_gate_summary: Path | None = None,
    platform_export_intake_summary: Path | None = None,
    forward_paper_gate_summary: Path | None = None,
    paper_input_preflight_summary: Path | None = None,
    paper_refresh_queue_summary: Path | None = None,
    paper_refresh_status_summary: Path | None = None,
) -> BasketGovernanceDashboardResult:
    sources = {
        "pm_gate": _read_optional(pm_gate_summary),
        "platform_export_intake": _read_optional(platform_export_intake_summary),
        "forward_paper_gate": _read_optional(forward_paper_gate_summary),
        "paper_input_preflight": _read_optional(paper_input_preflight_summary),
        "paper_refresh_queue": _read_optional(paper_refresh_queue_summary),
        "paper_refresh_status": _read_optional(paper_refresh_status_summary),
    }
    checks = _checks(sources)
    blocker_count = sum(1 for item in checks if item["severity"] == "blocker")
    needs_review_count = sum(1 for item in checks if item["severity"] == "needs_review")
    status = _status(checks, sources)
    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "experiment_layer": "pm_decision_gate",
        "status": status,
        "blocker_count": blocker_count,
        "needs_review_count": needs_review_count,
        "checks": checks,
        "source_statuses": {name: _source_status(payload) for name, payload in sources.items()},
        "key_dates": _key_dates(sources),
        "next_gate": _next_gate(status, sources),
        "blocked_actions": [
            "accepted_strategy",
            "live_trading_approved",
            "return_tuning",
            "platform_replication_passed_without_exports",
            "late_recorded_clean_paper_signal",
        ],
        "pm_rule": "Historical performance alone is never sufficient evidence for accepting a strategy.",
        "input_paths": {
            "pm_gate_summary": str(pm_gate_summary) if pm_gate_summary else None,
            "platform_export_intake_summary": str(platform_export_intake_summary) if platform_export_intake_summary else None,
            "forward_paper_gate_summary": str(forward_paper_gate_summary) if forward_paper_gate_summary else None,
            "paper_input_preflight_summary": str(paper_input_preflight_summary) if paper_input_preflight_summary else None,
            "paper_refresh_queue_summary": str(paper_refresh_queue_summary) if paper_refresh_queue_summary else None,
            "paper_refresh_status_summary": str(paper_refresh_status_summary) if paper_refresh_status_summary else None,
        },
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    summary_path = out / "basket_governance_dashboard_summary.json"
    report_path = out / "basket_governance_dashboard_report.md"
    write_json_file(summary_path, summary)
    report_path.write_text(_report(summary), encoding="utf-8")
    return BasketGovernanceDashboardResult(summary_path, report_path, status, blocker_count, needs_review_count)


def _read_optional(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _checks(sources: dict[str, dict[str, Any] | None]) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    pm_gate = sources["pm_gate"]
    platform = sources["platform_export_intake"]
    forward = sources["forward_paper_gate"]
    preflight = sources["paper_input_preflight"]
    queue = sources["paper_refresh_queue"]
    refresh_status = sources["paper_refresh_status"]

    if pm_gate is None:
        checks.append(_check("pm_gate", "needs_review", "PM gate summary is missing."))
    else:
        status = str(pm_gate.get("status") or "")
        blockers = int(pm_gate.get("blocker_count") or 0)
        if blockers:
            checks.append(_check("pm_gate", "blocker", f"PM gate has {blockers} blockers."))
        else:
            checks.append(_check("pm_gate", "pass", f"PM gate status is {status}."))

    if platform is None:
        checks.append(_check("platform_export_intake", "needs_review", "Platform export intake summary is missing."))
    else:
        status = str(platform.get("status") or "")
        if status == "ready_for_platform_attribution":
            checks.append(_check("platform_export_intake", "needs_review", "Platform exports are ready; attribution can run if user allows."))
        elif status == "platform_test_deferred_by_user_waiting_for_exports":
            checks.append(_check("platform_export_intake", "pass", "Platform test is explicitly deferred by user."))
        elif status == "waiting_for_joinquant_exports":
            checks.append(_check("platform_export_intake", "needs_review", "Waiting for platform exports."))
        else:
            checks.append(_check("platform_export_intake", "needs_review", f"Platform export intake status is {status}."))

    if forward is None:
        checks.append(_check("forward_paper_gate", "needs_review", "Forward paper gate summary is missing."))
    else:
        status = str(forward.get("status") or "")
        if status == "pending_clean_future_rebalance":
            checks.append(_check("forward_paper_gate", "pass", f"Next clean rebalance is {forward.get('next_rebalance_date')}."))
        elif status == "blocked_rebalance_date_not_future":
            checks.append(_check("forward_paper_gate", "blocker", "Forward paper gate points to a non-future rebalance date."))
        else:
            checks.append(_check("forward_paper_gate", "needs_review", f"Forward paper gate status is {status}."))

    if preflight is None:
        checks.append(_check("paper_input_preflight", "needs_review", "Paper input preflight summary is missing."))
    else:
        status = str(preflight.get("status") or "")
        if status == "pending_future_data_window":
            checks.append(_check("paper_input_preflight", "pass", "Paper input preflight is waiting for the future data window."))
        elif status == "ready_to_construct_clean_paper_signal":
            checks.append(_check("paper_input_preflight", "needs_review", "Preflight is ready; PM must gate signal construction."))
        elif status == "blocked_missing_or_stale_inputs":
            checks.append(_check("paper_input_preflight", "blocker", "Paper input preflight is blocked by missing or stale inputs."))
        else:
            checks.append(_check("paper_input_preflight", "needs_review", f"Paper input preflight status is {status}."))

    if queue is None:
        checks.append(_check("paper_refresh_queue", "needs_review", "Paper refresh queue summary is missing."))
    else:
        status = str(queue.get("status") or "")
        if status == "queued_for_future_refresh_window":
            checks.append(_check("paper_refresh_queue", "pass", f"Refresh queue has {queue.get('task_count')} tasks queued."))
        elif status == "refresh_tasks_required_before_signal":
            checks.append(_check("paper_refresh_queue", "needs_review", "Refresh tasks are required before signal generation."))
        else:
            checks.append(_check("paper_refresh_queue", "needs_review", f"Refresh queue status is {status}."))

    if refresh_status is None:
        checks.append(_check("paper_refresh_status", "needs_review", "Paper refresh status summary is missing."))
    else:
        status = str(refresh_status.get("status") or "")
        if status == "waiting_for_future_refresh_window":
            checks.append(_check("paper_refresh_status", "pass", "Refresh status is waiting for future window with no blockers."))
        elif status == "ready_for_clean_paper_signal_gate":
            checks.append(_check("paper_refresh_status", "needs_review", "Refresh status is ready; PM gate is required before signal."))
        elif status == "blocked":
            checks.append(_check("paper_refresh_status", "blocker", "Refresh status has blockers."))
        else:
            checks.append(_check("paper_refresh_status", "needs_review", f"Refresh status is {status}."))

    return checks


def _status(checks: list[dict[str, str]], sources: dict[str, dict[str, Any] | None]) -> str:
    if any(item["severity"] == "blocker" for item in checks):
        return "blocked"
    refresh_status = sources.get("paper_refresh_status") or {}
    platform = sources.get("platform_export_intake") or {}
    if refresh_status.get("status") == "waiting_for_future_refresh_window" and platform.get("status") == "platform_test_deferred_by_user_waiting_for_exports":
        return "frozen_candidate_waiting_for_future_paper_window_platform_deferred"
    if refresh_status.get("status") == "ready_for_clean_paper_signal_gate":
        return "ready_for_pm_clean_paper_signal_gate"
    return "needs_pm_review"


def _source_status(payload: dict[str, Any] | None) -> str:
    if payload is None:
        return "missing"
    return str(payload.get("status") or "present_no_status")


def _key_dates(sources: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    forward = sources.get("forward_paper_gate") or {}
    preflight = sources.get("paper_input_preflight") or {}
    refresh = sources.get("paper_refresh_status") or {}
    return {
        "next_rebalance_date": forward.get("next_rebalance_date") or preflight.get("target_rebalance_date") or refresh.get("target_rebalance_date"),
        "last_recorded_signal_date": forward.get("last_recorded_signal_date"),
        "dashboard_as_of_date": refresh.get("as_of_date") or preflight.get("as_of_date") or forward.get("as_of_date"),
    }


def _next_gate(status: str, sources: dict[str, dict[str, Any] | None]) -> str:
    if status == "frozen_candidate_waiting_for_future_paper_window_platform_deferred":
        return "wait_until_refresh_window_or_user_supplies_platform_exports"
    if status == "ready_for_pm_clean_paper_signal_gate":
        return "pm_gate_clean_paper_signal_without_tuning"
    if status == "blocked":
        return "repair_blockers"
    return "pm_review_missing_or_needs_review_items"


def _check(name: str, severity: str, detail: str) -> dict[str, str]:
    return {"check": name, "severity": severity, "detail": detail}


def _report(summary: dict[str, Any]) -> str:
    lines = [
        f"# Basket Governance Dashboard: {summary['strategy_id']}",
        "",
        f"- Status: `{summary['status']}`",
        f"- Blockers: `{summary['blocker_count']}`",
        f"- Needs review: `{summary['needs_review_count']}`",
        f"- Next gate: `{summary['next_gate']}`",
        "",
        "## Key Dates",
        "",
    ]
    for key, value in summary["key_dates"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Source Statuses", ""])
    for key, value in summary["source_statuses"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Checks", ""])
    for item in summary["checks"]:
        lines.append(f"- `{item['severity']}` {item['check']}: {item['detail']}")
    lines.extend(["", "## PM Rule", "", summary["pm_rule"]])
    return "\n".join(lines)


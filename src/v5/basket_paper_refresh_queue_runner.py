from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import write_csv_rows, write_json_file


DEFAULT_OUT_DIR = Path("paper_refresh_queues")


@dataclass(frozen=True)
class BasketPaperRefreshQueueResult:
    summary_path: Path
    queue_path: Path
    report_path: Path
    status: str
    task_count: int


def build_basket_paper_refresh_queue(
    preflight_summary: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> BasketPaperRefreshQueueResult:
    summary = _read_json(preflight_summary)
    strategy_id = str(summary.get("strategy_id") or "basket_paper_refresh")
    tasks = _build_tasks(summary)
    status = _status(summary, tasks)

    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)
    queue_path = out / "paper_refresh_task_queue.csv"
    summary_path = out / "paper_refresh_task_queue_summary.json"
    report_path = out / "paper_refresh_task_queue_report.md"
    write_csv_rows(
        queue_path,
        [
            "priority",
            "owner_agent",
            "sector_id",
            "task_type",
            "reason",
            "required_before",
            "input_path",
            "completion_check",
            "blocked_action_until_done",
        ],
        tasks,
    )
    payload = {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "experiment_layer": "paper_trading_preparation",
        "status": status,
        "preflight_summary": str(preflight_summary),
        "target_rebalance_date": summary.get("target_rebalance_date"),
        "as_of_date": summary.get("as_of_date"),
        "target_date_is_future": summary.get("target_date_is_future"),
        "task_count": len(tasks),
        "task_counts_by_type": _counts(tasks, "task_type"),
        "task_counts_by_owner": _counts(tasks, "owner_agent"),
        "queue_csv": str(queue_path),
        "next_gate": _next_gate(status),
        "pm_rules": [
            "This queue prepares paper trading inputs only; it does not change the frozen V5.7f model.",
            "Refresh tasks must be completed before constructing a clean paper signal.",
            "If stale fallback remains, it must be disclosed in the paper signal log.",
            "No return tuning is allowed.",
        ],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_json_file(summary_path, payload)
    report_path.write_text(_report(payload, tasks), encoding="utf-8")
    return BasketPaperRefreshQueueResult(summary_path, queue_path, report_path, status, len(tasks))


def _build_tasks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    target = str(summary.get("target_rebalance_date") or "")
    prior = str(summary.get("prior_trading_date") or target)
    tasks: list[dict[str, Any]] = []
    priority = 10
    for sector in summary.get("sector_checks", []):
        sector_id = str(sector.get("sector_id") or "")
        if _needs_panel_refresh(sector, target):
            tasks.append(
                _task(
                    priority,
                    "Engineering Agent",
                    sector_id,
                    "refresh_pit_panel",
                    f"latest_panel_trade_date={sector.get('latest_panel_trade_date')} target_rows={sector.get('target_panel_rows')}",
                    target,
                    str(sector.get("panel_csv") or ""),
                    f"panel has target trade_date {target} with required fields populated",
                )
            )
            priority += 10
        if _needs_price_refresh(sector, prior):
            tasks.append(
                _task(
                    priority,
                    "Engineering Agent",
                    sector_id,
                    "refresh_real_daily_prices",
                    f"latest_price_date={sector.get('latest_price_date')} prior_trading_date={prior}",
                    prior,
                    str(sector.get("price_csv") or ""),
                    f"price file includes unadjusted open/close through {prior}",
                )
            )
            priority += 10
        if _needs_dividend_refresh(sector, prior):
            tasks.append(
                _task(
                    priority,
                    "Engineering Agent",
                    sector_id,
                    "refresh_cash_dividends",
                    f"latest_dividend_pay_date={sector.get('latest_dividend_pay_date')} prior_trading_date={prior}",
                    prior,
                    str(sector.get("dividend_csv") or ""),
                    "dividend file is refreshed with 20% tax-adjusted net_cash_per_share",
                )
            )
            priority += 10
        stale_rows = int(sector.get("target_stale_fallback_rows") or 0) + int(sector.get("latest_stale_fallback_rows") or 0)
        if stale_rows:
            tasks.append(
                _task(
                    priority,
                    "Engineering Agent",
                    sector_id,
                    "audit_or_repair_stale_fallback",
                    f"stale_fallback_rows={stale_rows}",
                    target,
                    str(sector.get("panel_csv") or ""),
                    "stale fallback rows are either refreshed from PIT sources or explicitly logged in paper record",
                )
            )
            priority += 10
    tasks.append(
        _task(
            priority,
            "Project Manager Agent",
            "all",
            "rerun_paper_input_preflight",
            "confirm all sleeve inputs are fresh before signal construction",
            target,
            str(summary.get("config") or ""),
            "preflight status is ready_to_construct_clean_paper_signal or PM-approved ready_with_review",
            blocked_action="clean_paper_signal_generation",
        )
    )
    tasks.append(
        _task(
            priority + 10,
            "Project Manager Agent",
            "all",
            "construct_clean_paper_signal_gate",
            "only after preflight passes; do not generate late-recorded signal",
            target,
            str(summary.get("config") or ""),
            "signal is generated on or before target rebalance date and logged as clean forward evidence",
            blocked_action="paper_trading_log_update",
        )
    )
    return tasks


def _task(
    priority: int,
    owner: str,
    sector_id: str,
    task_type: str,
    reason: str,
    required_before: str,
    input_path: str,
    completion_check: str,
    *,
    blocked_action: str = "clean_paper_signal_generation",
) -> dict[str, Any]:
    return {
        "priority": priority,
        "owner_agent": owner,
        "sector_id": sector_id,
        "task_type": task_type,
        "reason": reason,
        "required_before": required_before,
        "input_path": input_path,
        "completion_check": completion_check,
        "blocked_action_until_done": blocked_action,
    }


def _needs_panel_refresh(sector: dict[str, Any], target: str) -> bool:
    latest = str(sector.get("latest_panel_trade_date") or "")
    return not sector.get("panel_exists") or int(sector.get("target_panel_rows") or 0) <= 0 or latest < target or int(sector.get("target_rows_missing_required_fields") or 0) > 0


def _needs_price_refresh(sector: dict[str, Any], prior: str) -> bool:
    latest = str(sector.get("latest_price_date") or "")
    return not sector.get("price_exists") or not latest or latest < prior


def _needs_dividend_refresh(sector: dict[str, Any], prior: str) -> bool:
    latest = str(sector.get("latest_dividend_pay_date") or "")
    return not sector.get("dividend_exists") or not latest or latest < prior


def _status(summary: dict[str, Any], tasks: list[dict[str, Any]]) -> str:
    if summary.get("target_date_is_future"):
        return "queued_for_future_refresh_window"
    if tasks:
        return "refresh_tasks_required_before_signal"
    return "no_refresh_tasks_required"


def _next_gate(status: str) -> str:
    if status == "queued_for_future_refresh_window":
        return "wait_until_refresh_window_then_execute_queue"
    if status == "refresh_tasks_required_before_signal":
        return "execute_refresh_queue_then_rerun_preflight"
    return "construct_clean_paper_signal_without_tuning"


def _counts(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        key = str(row.get(field) or "")
        result[key] = result.get(key, 0) + 1
    return result


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _report(summary: dict[str, Any], tasks: list[dict[str, Any]]) -> str:
    lines = [
        f"# Paper Refresh Task Queue: {summary['strategy_id']}",
        "",
        f"- Status: `{summary['status']}`",
        f"- As of date: `{summary['as_of_date']}`",
        f"- Target rebalance date: `{summary['target_rebalance_date']}`",
        f"- Task count: `{summary['task_count']}`",
        f"- Next gate: `{summary['next_gate']}`",
        "",
        "## Tasks",
        "",
        "| Priority | Owner | Sector | Task | Required before |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for task in tasks:
        lines.append(
            f"| {task['priority']} | {task['owner_agent']} | {task['sector_id']} | "
            f"`{task['task_type']}` | {task['required_before']} |"
        )
    lines.extend(["", "## PM Rules", ""])
    for item in summary["pm_rules"]:
        lines.append(f"- {item}")
    return "\n".join(lines)


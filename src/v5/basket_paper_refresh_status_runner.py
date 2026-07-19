from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file


DEFAULT_OUT_DIR = Path("paper_refresh_status_checks")


@dataclass(frozen=True)
class BasketPaperRefreshStatusResult:
    summary_path: Path
    status_csv: Path
    report_path: Path
    status: str
    task_count: int
    completed_count: int
    pending_count: int


def check_basket_paper_refresh_status(
    *,
    queue_csv: Path,
    preflight_summary: Path,
    as_of_date: str,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> BasketPaperRefreshStatusResult:
    queue = read_csv_rows(queue_csv)
    preflight = _read_json(preflight_summary)
    strategy_id = str(preflight.get("strategy_id") or "basket_paper_refresh")
    as_of = date.fromisoformat(as_of_date)
    target = date.fromisoformat(str(preflight.get("target_rebalance_date") or as_of_date))
    sector_map = {str(item.get("sector_id") or ""): item for item in preflight.get("sector_checks", [])}
    rows = [_task_status(row, sector_map, preflight, as_of, target) for row in queue]
    completed_count = sum(1 for row in rows if row["task_status"] in {"completed", "ready_for_pm_gate"})
    pending_count = sum(1 for row in rows if row["task_status"] in {"pending_refresh", "not_due_yet", "needs_review"})
    blocker_count = sum(1 for row in rows if row["task_status"] == "blocked")
    status = _summary_status(rows, as_of, target, blocker_count)

    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)
    status_csv = out / "paper_refresh_task_status.csv"
    summary_path = out / "paper_refresh_task_status_summary.json"
    report_path = out / "paper_refresh_task_status_report.md"
    write_csv_rows(
        status_csv,
        [
            "priority",
            "owner_agent",
            "sector_id",
            "task_type",
            "task_status",
            "status_reason",
            "required_before",
            "input_path",
            "completion_check",
            "blocked_action_until_done",
        ],
        rows,
    )
    summary = {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "experiment_layer": "paper_trading_preparation",
        "status": status,
        "as_of_date": as_of_date,
        "target_rebalance_date": preflight.get("target_rebalance_date"),
        "target_date_is_future": target > as_of,
        "queue_csv": str(queue_csv),
        "preflight_summary": str(preflight_summary),
        "task_count": len(rows),
        "completed_count": completed_count,
        "pending_count": pending_count,
        "blocker_count": blocker_count,
        "task_counts_by_status": _counts(rows, "task_status"),
        "task_counts_by_owner": _counts(rows, "owner_agent"),
        "status_csv": str(status_csv),
        "next_gate": _next_gate(status),
        "pm_rule": "This status check does not refresh data, tune the model, or generate a paper signal.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_json_file(summary_path, summary)
    report_path.write_text(_report(summary, rows), encoding="utf-8")
    return BasketPaperRefreshStatusResult(summary_path, status_csv, report_path, status, len(rows), completed_count, pending_count)


def _task_status(
    task: dict[str, str],
    sector_map: dict[str, dict[str, Any]],
    preflight: dict[str, Any],
    as_of: date,
    target: date,
) -> dict[str, Any]:
    task_type = str(task.get("task_type") or "")
    sector_id = str(task.get("sector_id") or "")
    sector = sector_map.get(sector_id, {})
    status, reason = _evaluate(task_type, sector, preflight, as_of, target)
    row = dict(task)
    row["task_status"] = status
    row["status_reason"] = reason
    return row


def _evaluate(
    task_type: str,
    sector: dict[str, Any],
    preflight: dict[str, Any],
    as_of: date,
    target: date,
) -> tuple[str, str]:
    if target > as_of and task_type in {
        "refresh_pit_panel",
        "refresh_real_daily_prices",
        "refresh_cash_dividends",
        "audit_or_repair_stale_fallback",
        "construct_clean_paper_signal_gate",
    }:
        return "not_due_yet", "target rebalance date is still in the future"
    if task_type == "refresh_pit_panel":
        if int(sector.get("target_panel_rows") or 0) > 0 and int(sector.get("target_rows_missing_required_fields") or 0) == 0:
            return "completed", "target panel rows exist and required fields are populated"
        return "pending_refresh", "target panel rows or required fields are still missing"
    if task_type == "refresh_real_daily_prices":
        if sector.get("price_reaches_prior_trading_date"):
            return "completed", "price data reaches the prior trading date"
        return "pending_refresh", "price data does not reach the prior trading date"
    if task_type == "refresh_cash_dividends":
        latest = str(sector.get("latest_dividend_pay_date") or "")
        prior = str(preflight.get("prior_trading_date") or preflight.get("target_rebalance_date") or "")
        if latest and latest >= prior:
            return "completed", "cash dividend file reaches the prior trading date"
        return "pending_refresh", "cash dividend file needs refresh before signal generation"
    if task_type == "audit_or_repair_stale_fallback":
        stale = int(sector.get("target_stale_fallback_rows") or 0) + int(sector.get("latest_stale_fallback_rows") or 0)
        if stale:
            return "needs_review", f"stale fallback rows remain: {stale}"
        return "completed", "no stale fallback rows remain"
    if task_type == "rerun_paper_input_preflight":
        if str(preflight.get("status") or "") in {"ready_to_construct_clean_paper_signal", "ready_with_review"}:
            return "ready_for_pm_gate", f"preflight status is {preflight.get('status')}"
        return "pending_refresh", f"preflight status is {preflight.get('status')}"
    if task_type == "construct_clean_paper_signal_gate":
        if str(preflight.get("status") or "") == "ready_to_construct_clean_paper_signal" and target >= as_of:
            return "ready_for_pm_gate", "clean signal gate may proceed without late-recording"
        return "not_due_yet" if target > as_of else "blocked", "clean signal gate is not ready"
    return "pending_refresh", "unknown task type requires manual review"


def _summary_status(rows: list[dict[str, Any]], as_of: date, target: date, blocker_count: int) -> str:
    if blocker_count:
        return "blocked"
    if target > as_of:
        return "waiting_for_future_refresh_window"
    if all(row["task_status"] in {"completed", "ready_for_pm_gate"} for row in rows):
        return "ready_for_clean_paper_signal_gate"
    return "refresh_tasks_pending"


def _next_gate(status: str) -> str:
    if status == "waiting_for_future_refresh_window":
        return "wait_until_refresh_window"
    if status == "ready_for_clean_paper_signal_gate":
        return "construct_clean_paper_signal_without_tuning"
    if status == "blocked":
        return "repair_blockers_before_signal_generation"
    return "execute_pending_refresh_tasks"


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


def _report(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        f"# Paper Refresh Task Status: {summary['strategy_id']}",
        "",
        f"- Status: `{summary['status']}`",
        f"- As of date: `{summary['as_of_date']}`",
        f"- Target rebalance date: `{summary['target_rebalance_date']}`",
        f"- Task count: `{summary['task_count']}`",
        f"- Completed: `{summary['completed_count']}`",
        f"- Pending: `{summary['pending_count']}`",
        f"- Blockers: `{summary['blocker_count']}`",
        f"- Next gate: `{summary['next_gate']}`",
        "",
        "## Task Status",
        "",
        "| Priority | Owner | Sector | Task | Status |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['priority']} | {row['owner_agent']} | {row['sector_id']} | "
            f"`{row['task_type']}` | `{row['task_status']}` |"
        )
    lines.extend(["", "## PM Rule", "", summary["pm_rule"]])
    return "\n".join(lines)


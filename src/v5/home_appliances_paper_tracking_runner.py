from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from v5.agent_loop_packet_runner import create_agent_loop_packet
from v5.home_appliances_daily_backtest_runner import (
    DEFAULT_BENCHMARK_CSV,
    DEFAULT_DIVIDEND_CASH_CSV,
    DEFAULT_EXECUTION_PRICE_CSV,
    DEFAULT_PANEL,
)
from v5.io_utils import read_csv_rows, read_csv_rows_if_exists, write_csv_rows, write_json_file


DEFAULT_STRATEGY_ID = "home_appliances_ocf_quality_v5a5c"
DEFAULT_LOCAL_DAILY_DIR = Path("local_daily_backtests_home_appliances_v5a5e") / DEFAULT_STRATEGY_ID
DEFAULT_PROMOTION_QUEUE = Path("enhanced_etf_production_lines_v5") / "current" / "sleeve_promotion_queue.csv"
DEFAULT_OUT_DIR = Path("paper_trading_signals") / "home_appliances_v5a5e_promotion_queue"
DEFAULT_PACKET_DIR = Path("agent_loop_packets_v5a5") / "home_appliances_paper_tracking"

FLOW_FIELDS = ["stage", "owner", "input", "action", "output", "gate", "status"]
HEALTH_FIELDS = ["check", "status", "detail"]


@dataclass(frozen=True)
class HomeAppliancesPaperTrackingResult:
    output_dir: Path
    flow_table_csv: Path
    health_check_csv: Path
    summary_json: Path
    report_path: Path
    agent_packet_json: Path
    status: str
    next_gate: str


def build_home_appliances_paper_tracking_packet(
    *,
    strategy_id: str = DEFAULT_STRATEGY_ID,
    local_daily_dir: Path = DEFAULT_LOCAL_DAILY_DIR,
    panel_csv: Path = DEFAULT_PANEL,
    price_csv: Path = DEFAULT_EXECUTION_PRICE_CSV,
    dividend_csv: Path = DEFAULT_DIVIDEND_CASH_CSV,
    benchmark_csv: Path = DEFAULT_BENCHMARK_CSV,
    promotion_queue_csv: Path = DEFAULT_PROMOTION_QUEUE,
    out_dir: Path = DEFAULT_OUT_DIR,
    agent_packet_dir: Path = DEFAULT_PACKET_DIR,
    as_of_date: str = "2026-07-22",
    next_clean_rebalance_date: str = "2026-10-08",
) -> HomeAppliancesPaperTrackingResult:
    summary_path = local_daily_dir / "summary.json"
    order_health_path = local_daily_dir / "rebalance_order_health.csv"
    rebalance_signals_path = local_daily_dir / "rebalance_signals.csv"
    local_summary = _read_json(summary_path)
    order_health_rows = read_csv_rows(order_health_path)
    signal_rows = read_csv_rows(rebalance_signals_path)
    promotion_rows = read_csv_rows_if_exists(promotion_queue_csv)

    data_health = _build_data_health(
        panel_csv=panel_csv,
        price_csv=price_csv,
        dividend_csv=dividend_csv,
        benchmark_csv=benchmark_csv,
        next_clean_rebalance_date=next_clean_rebalance_date,
    )
    order_summary = local_summary.get("rebalance_order_health", {})
    health_rows = _build_health_rows(
        local_summary=local_summary,
        order_summary=order_summary,
        data_health=data_health,
        promotion_rows=promotion_rows,
        next_clean_rebalance_date=next_clean_rebalance_date,
        as_of_date=as_of_date,
    )
    flow_rows = _build_flow_rows(
        strategy_id=strategy_id,
        as_of_date=as_of_date,
        next_clean_rebalance_date=next_clean_rebalance_date,
        health_rows=health_rows,
    )
    status, next_gate = _status_and_gate(health_rows, as_of_date, next_clean_rebalance_date)

    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)
    flow_table_csv = out / "home_appliances_paper_tracking_flow_table.csv"
    health_check_csv = out / "home_appliances_paper_tracking_health_check.csv"
    summary_json = out / "home_appliances_paper_tracking_summary.json"
    report_path = out / "home_appliances_paper_tracking_report.md"
    write_csv_rows(flow_table_csv, FLOW_FIELDS, flow_rows)
    write_csv_rows(health_check_csv, HEALTH_FIELDS, health_rows)

    payload = {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "experiment_layer": "paper_trading_preparation",
        "status": status,
        "as_of_date": as_of_date,
        "next_clean_rebalance_date": next_clean_rebalance_date,
        "target_date_is_future": date.fromisoformat(next_clean_rebalance_date) > date.fromisoformat(as_of_date),
        "promotion_queue_rank": _candidate_rank(promotion_rows),
        "local_daily_dir": str(local_daily_dir),
        "inputs": {
            "panel_csv": str(panel_csv),
            "price_csv": str(price_csv),
            "dividend_csv": str(dividend_csv),
            "benchmark_csv": str(benchmark_csv),
            "promotion_queue_csv": str(promotion_queue_csv),
        },
        "data_health": data_health,
        "local_daily_summary": {
            "engineering_gate": local_summary.get("engineering_gate"),
            "signal_count": local_summary.get("signal_count"),
            "daily_count": local_summary.get("daily_count"),
            "rebalance_order_health": order_summary,
            "signal_coverage": local_summary.get("signal_coverage"),
        },
        "latest_artifact_dates": {
            "last_signal_date": _latest_date(signal_rows, "trade_date"),
            "last_order_health_date": _latest_date(order_health_rows, "trade_date"),
        },
        "outputs": {
            "flow_table_csv": str(flow_table_csv),
            "health_check_csv": str(health_check_csv),
            "report_path": str(report_path),
        },
        "next_gate": next_gate,
        "pm_rules": [
            "Home appliances remains an observation sleeve and cannot be silently added to frozen V57f.",
            "No factor, weight, selection count, timing or sector-cap tuning is allowed.",
            "No JoinQuant platform test is started by this packet.",
            "A clean forward paper signal can only be recorded on or before the future rebalance date.",
            "2021-2026 performance remains Engineering context, not accepted-strategy evidence.",
        ],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_json_file(summary_json, payload)
    report_path.write_text(_report(payload, flow_rows, health_rows), encoding="utf-8")

    packet = create_agent_loop_packet(
        packet_type="checkpoint_packet",
        objective="home_appliances_observation_sleeve_paper_tracking_refresh",
        agent="Engineering Agent",
        experiment_layer="paper_trading_preparation",
        decision="continue_next_timebox",
        next_owner="Engineering Agent",
        out_dir=agent_packet_dir,
        timebox_minutes=60,
        artifacts=[str(flow_table_csv), str(health_check_csv), str(summary_json), str(report_path)],
        evidence=[
            f"Promotion queue rank={payload['promotion_queue_rank']}",
            f"Order health needs_review={order_summary.get('needs_review')} normal_rebalance_count={order_summary.get('normal_rebalance_count')}",
            f"Next clean rebalance date {next_clean_rebalance_date} is future relative to {as_of_date}",
        ],
        blockers=[
            "No blocker for paper-tracking preparation.",
            "Clean forward signal cannot be generated until the future rebalance window.",
        ],
        allowed_next_action="wait_until_clean_forward_window_then_refresh_inputs_without_tuning",
        restart_condition=f"run again near {next_clean_rebalance_date} with refreshed PIT panel, prices and dividends",
        loop_id=f"home_appliances_paper_tracking_{as_of_date.replace('-', '')}",
    )
    payload["agent_packet"] = {"packet_path": str(packet.packet_path), "report_path": str(packet.report_path)}
    write_json_file(summary_json, payload)
    return HomeAppliancesPaperTrackingResult(
        output_dir=out,
        flow_table_csv=flow_table_csv,
        health_check_csv=health_check_csv,
        summary_json=summary_json,
        report_path=report_path,
        agent_packet_json=packet.packet_path,
        status=status,
        next_gate=next_gate,
    )


def _build_data_health(
    *,
    panel_csv: Path,
    price_csv: Path,
    dividend_csv: Path,
    benchmark_csv: Path,
    next_clean_rebalance_date: str,
) -> dict[str, Any]:
    panel_rows = read_csv_rows_if_exists(panel_csv)
    price_rows = read_csv_rows_if_exists(price_csv)
    dividend_rows = read_csv_rows_if_exists(dividend_csv)
    benchmark_rows = read_csv_rows_if_exists(benchmark_csv)
    return {
        "panel_exists": panel_csv.exists(),
        "price_exists": price_csv.exists(),
        "dividend_exists": dividend_csv.exists(),
        "benchmark_exists": benchmark_csv.exists(),
        "panel_row_count": len(panel_rows),
        "price_row_count": len(price_rows),
        "dividend_row_count": len(dividend_rows),
        "benchmark_row_count": len(benchmark_rows),
        "latest_panel_trade_date": _latest_date(panel_rows, "trade_date"),
        "latest_price_date": _latest_date(price_rows, "date"),
        "latest_dividend_pay_date": _latest_date(dividend_rows, "pay_date"),
        "latest_benchmark_date": _latest_date(benchmark_rows, "date"),
        "target_panel_rows": sum(1 for row in panel_rows if _row_date(row, "trade_date") == next_clean_rebalance_date),
    }


def _build_health_rows(
    *,
    local_summary: dict[str, Any],
    order_summary: dict[str, Any],
    data_health: dict[str, Any],
    promotion_rows: list[dict[str, str]],
    next_clean_rebalance_date: str,
    as_of_date: str,
) -> list[dict[str, str]]:
    rank = _candidate_rank(promotion_rows)
    return [
        _health("promotion_queue_rank_exists", rank > 0, f"rank={rank or ''}"),
        _health("promotion_queue_observation_route", _candidate_gate(promotion_rows) == "paper_tracking_only_no_core_inclusion", _candidate_gate(promotion_rows)),
        _health("local_daily_engineering_passed", "passed" in str(local_summary.get("engineering_gate") or ""), str(local_summary.get("engineering_gate") or "")),
        _health("signal_coverage_passed", str(local_summary.get("signal_coverage", {}).get("status") or "") == "passed", json.dumps(local_summary.get("signal_coverage") or {}, ensure_ascii=False)),
        _health("rebalance_order_health_passed", not bool(order_summary.get("needs_review")) and int(order_summary.get("normal_rebalance_count") or 0) > 0, json.dumps(order_summary, ensure_ascii=False)),
        _health("panel_file_exists", bool(data_health["panel_exists"]), f"latest={data_health['latest_panel_trade_date']} rows={data_health['panel_row_count']}"),
        _health("price_file_exists", bool(data_health["price_exists"]), f"latest={data_health['latest_price_date']} rows={data_health['price_row_count']}"),
        _health("dividend_file_exists", bool(data_health["dividend_exists"]), f"latest={data_health['latest_dividend_pay_date']} rows={data_health['dividend_row_count']}"),
        _health("benchmark_file_exists", bool(data_health["benchmark_exists"]), f"latest={data_health['latest_benchmark_date']} rows={data_health['benchmark_row_count']}"),
        _health("future_window_not_due", date.fromisoformat(next_clean_rebalance_date) > date.fromisoformat(as_of_date), f"as_of={as_of_date} target={next_clean_rebalance_date}"),
        _health("target_panel_rows_pending_is_expected", int(data_health["target_panel_rows"] or 0) == 0, f"target_rows={data_health['target_panel_rows']}"),
    ]


def _build_flow_rows(*, strategy_id: str, as_of_date: str, next_clean_rebalance_date: str, health_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    core_status = "passed" if all(row["status"] == "passed" for row in health_rows[:9]) else "needs_review"
    return [
        _flow("1", "Project Manager Agent", "sleeve_promotion_queue.csv", "Confirm home_appliances is observation paper-tracking candidate, not V57f sleeve", "PM scoped task", "paper_tracking_only_no_core_inclusion", "completed"),
        _flow("2", "Engineering Agent", strategy_id, "Load frozen home-appliances local daily artifacts", "local evidence snapshot", "no_strategy_change", "completed"),
        _flow("3", "Engineering Agent", "rebalance_signals.csv", "Confirm every formal rebalance date has a generated local signal", "signal coverage audit", "20/20_signals_required", core_status),
        _flow("4", "Engineering Agent", "rebalance_order_health.csv", "Check every rebalance signal produced normal orders and post-rebalance holdings", "health_check.csv", "order_health_passed", core_status),
        _flow("5", "Engineering Agent", "PIT panel / prices / dividends / benchmark", "Check source files exist and capture latest dates", "data freshness snapshot", "files_exist", core_status),
        _flow("6", "Project Manager Agent", f"as_of={as_of_date}", "Do not generate a late paper signal before the clean future date arrives", "future-window gate", "target_date_future", "waiting"),
        _flow("7", "Engineering Agent", next_clean_rebalance_date, "Near the target window, refresh PIT panel, prices and dividends, then rerun this packet", "clean paper input packet", "no_tuning", "pending_future_window"),
        _flow("8", "Project Manager Agent", "clean paper input packet", "Append future signal to paper log only if generated on time", "paper trading log entry", "forward_evidence_only", "pending_future_window"),
    ]


def _status_and_gate(health_rows: list[dict[str, str]], as_of_date: str, next_clean_rebalance_date: str) -> tuple[str, str]:
    failed_non_future = [row for row in health_rows[:9] if row["status"] != "passed"]
    if failed_non_future:
        return "needs_review_before_paper_tracking", "repair_failed_health_checks"
    if date.fromisoformat(next_clean_rebalance_date) > date.fromisoformat(as_of_date):
        return "paper_tracking_ready_waiting_for_future_window", "wait_until_clean_forward_window"
    return "ready_for_clean_paper_signal_generation", "generate_clean_paper_signal_without_tuning"


def _candidate_rank(rows: list[dict[str, str]]) -> int:
    for row in rows:
        if row.get("sector_id") == "home_appliances":
            return int(row.get("rank") or 0)
    return 0


def _candidate_gate(rows: list[dict[str, str]]) -> str:
    for row in rows:
        if row.get("sector_id") == "home_appliances":
            return str(row.get("pm_gate") or "")
    return ""


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _latest_date(rows: list[dict[str, str]], field: str) -> str:
    dates = sorted({_row_date(row, field) for row in rows if _row_date(row, field)})
    return dates[-1] if dates else ""


def _row_date(row: dict[str, str], field: str) -> str:
    return str(row.get(field) or "")[:10]


def _health(check: str, ok: bool, detail: str) -> dict[str, str]:
    return {"check": check, "status": "passed" if ok else "needs_review", "detail": detail}


def _flow(stage: str, owner: str, input_path: str, action: str, output: str, gate: str, status: str) -> dict[str, str]:
    return {
        "stage": stage,
        "owner": owner,
        "input": input_path,
        "action": action,
        "output": output,
        "gate": gate,
        "status": status,
    }


def _report(summary: dict[str, Any], flow_rows: list[dict[str, str]], health_rows: list[dict[str, str]]) -> str:
    lines = [
        f"# Home Appliances Paper Tracking Packet: {summary['strategy_id']}",
        "",
        f"- Status: `{summary['status']}`",
        f"- As of date: `{summary['as_of_date']}`",
        f"- Next clean rebalance date: `{summary['next_clean_rebalance_date']}`",
        f"- Next gate: `{summary['next_gate']}`",
        f"- Promotion queue rank: `{summary['promotion_queue_rank']}`",
        "",
        "## Detailed Flow Table",
        "",
        "| Stage | Owner | Input | Action | Output | Gate | Status |",
        "| ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for row in flow_rows:
        lines.append(
            f"| {row['stage']} | {row['owner']} | `{row['input']}` | {row['action']} | `{row['output']}` | `{row['gate']}` | `{row['status']}` |"
        )
    lines.extend(["", "## Health Checks", "", "| Check | Status | Detail |", "| --- | --- | --- |"])
    for row in health_rows:
        lines.append(f"| `{row['check']}` | `{row['status']}` | {row['detail']} |")
    lines.extend(["", "## PM Rules", ""])
    for item in summary["pm_rules"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"

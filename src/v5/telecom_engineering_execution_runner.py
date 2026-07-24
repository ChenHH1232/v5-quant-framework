from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from v5.agent_loop_packet_runner import create_agent_loop_packet
from v5.basket_daily_backtest_runner import run_basket_daily_backtest
from v5.io_utils import read_csv_rows, read_csv_rows_if_exists, write_csv_rows, write_json_file
from v5.telecom_engineering_readiness_runner import (
    DEFAULT_BENCHMARK_CSV,
    DEFAULT_DIVIDEND_CSV,
    DEFAULT_OVERLAY_ID,
    DEFAULT_PANEL,
    DEFAULT_PRICE_CSV,
)


DEFAULT_CONFIG = Path("config/dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay.json")
DEFAULT_SIGNALS = Path("validation_formal_v58_telecom_overlay_basket_constructor") / "basket_rebalance_signals.csv"
DEFAULT_READINESS_SUMMARY = Path("telecom_engineering_readiness_v5") / "current" / "telecom_engineering_readiness_summary.json"
DEFAULT_LOCAL_DAILY_OUT = Path("local_daily_backtests_v5a_telecom_observation_refresh")
DEFAULT_OUT_DIR = Path("telecom_engineering_execution_v5") / "current"
DEFAULT_PAPER_OUT_DIR = Path("paper_trading_signals") / "telecom_v5a_observation_queue"
DEFAULT_PACKET_DIR = Path("agent_loop_packets_v5a") / "telecom_engineering_execution"

FLOW_FIELDS = ["step", "owner", "input", "action", "output", "gate", "status", "forbidden_action"]
HEALTH_FIELDS = ["check", "status", "detail"]
QUEUE_FIELDS = ["queue_rank", "sector_id", "owner", "task", "input_artifacts", "output_artifacts", "gate", "blocked_actions"]


@dataclass(frozen=True)
class TelecomEngineeringExecutionResult:
    output_dir: Path
    local_daily_dir: Path
    summary_json: Path
    report_md: Path
    flow_table_csv: Path
    health_check_csv: Path
    paper_summary_json: Path
    paper_report_md: Path
    agent_packet_json: Path
    status: str
    next_gate: str


def execute_telecom_engineering_queue(
    *,
    config_path: Path = DEFAULT_CONFIG,
    signals_csv: Path = DEFAULT_SIGNALS,
    readiness_summary: Path = DEFAULT_READINESS_SUMMARY,
    panel_csv: Path = DEFAULT_PANEL,
    price_csv: Path = DEFAULT_PRICE_CSV,
    dividend_csv: Path = DEFAULT_DIVIDEND_CSV,
    benchmark_csv: Path = DEFAULT_BENCHMARK_CSV,
    local_daily_out: Path = DEFAULT_LOCAL_DAILY_OUT,
    out_dir: Path = DEFAULT_OUT_DIR,
    paper_out_dir: Path = DEFAULT_PAPER_OUT_DIR,
    agent_packet_dir: Path = DEFAULT_PACKET_DIR,
    as_of_date: str = "2026-07-24",
    next_clean_rebalance_date: str = "2026-10-08",
    initial_cash: float = 2_000_000.0,
    target_exposure: float = 0.995,
    lot_size: int = 100,
) -> TelecomEngineeringExecutionResult:
    local_result = run_basket_daily_backtest(
        config_path=config_path,
        signals_csv=signals_csv,
        out_dir=local_daily_out,
        initial_cash=initial_cash,
        target_exposure=target_exposure,
        lot_size=lot_size,
    )
    local_summary = _read_json(local_result.summary_path)
    readiness = _read_json(readiness_summary)
    order_health_rows = read_csv_rows(local_result.order_health_path)
    signal_rows = read_csv_rows(local_result.output_dir / "rebalance_signals.csv")
    data_health = _data_health(panel_csv, price_csv, dividend_csv, benchmark_csv, next_clean_rebalance_date)
    health_rows = _health_rows(
        readiness=readiness,
        local_summary=local_summary,
        data_health=data_health,
        order_health_rows=order_health_rows,
        signal_rows=signal_rows,
        as_of_date=as_of_date,
        next_clean_rebalance_date=next_clean_rebalance_date,
    )
    status, next_gate = _status_and_gate(health_rows, as_of_date, next_clean_rebalance_date)
    flow_rows = _flow_rows(status)
    queue_rows = _next_queue(status, next_clean_rebalance_date)

    out_dir.mkdir(parents=True, exist_ok=True)
    flow_table_csv = out_dir / "telecom_engineering_execution_flow_table.csv"
    health_check_csv = out_dir / "telecom_engineering_execution_health_checks.csv"
    queue_csv = out_dir / "telecom_engineering_execution_next_queue.csv"
    summary_json = out_dir / "telecom_engineering_execution_summary.json"
    report_md = out_dir / "telecom_engineering_execution_report.md"
    write_csv_rows(flow_table_csv, FLOW_FIELDS, flow_rows, encoding="utf-8-sig")
    write_csv_rows(health_check_csv, HEALTH_FIELDS, health_rows, encoding="utf-8-sig")
    write_csv_rows(queue_csv, QUEUE_FIELDS, queue_rows, encoding="utf-8-sig")

    paper_dir = paper_out_dir / DEFAULT_OVERLAY_ID
    paper_dir.mkdir(parents=True, exist_ok=True)
    paper_summary_json = paper_dir / "telecom_paper_tracking_summary.json"
    paper_report_md = paper_dir / "telecom_paper_tracking_report.md"
    paper_payload = _paper_payload(
        local_summary=local_summary,
        data_health=data_health,
        health_rows=health_rows,
        local_daily_dir=local_result.output_dir,
        as_of_date=as_of_date,
        next_clean_rebalance_date=next_clean_rebalance_date,
    )
    write_json_file(paper_summary_json, paper_payload)
    paper_report_md.write_text(_paper_report(paper_payload), encoding="utf-8")

    payload = {
        "schema_version": 1,
        "strategy_id": DEFAULT_OVERLAY_ID,
        "sector_id": "telecom_operators",
        "experiment_layer": "engineering_smoke_test",
        "status": status,
        "next_gate": next_gate,
        "as_of_date": as_of_date,
        "next_clean_rebalance_date": next_clean_rebalance_date,
        "local_daily_dir": str(local_result.output_dir),
        "readiness_summary": str(readiness_summary),
        "local_daily_summary": {
            "summary_json": str(local_result.summary_path),
            "daily_returns": str(local_result.daily_returns_path),
            "holdings": str(local_result.holdings_path),
            "trades": str(local_result.trades_path),
            "dividends": str(local_result.dividends_path),
            "rebalance_order_health": str(local_result.order_health_path),
            "metrics": local_summary.get("metrics", {}),
            "rebalance_order_health_summary": local_summary.get("rebalance_order_health", {}),
            "signal_count": local_summary.get("signal_count"),
            "daily_count": local_summary.get("daily_count"),
            "trade_count": local_summary.get("trade_count"),
            "dividend_count": local_summary.get("dividend_count"),
        },
        "data_health": data_health,
        "paper_tracking": {
            "summary_json": str(paper_summary_json),
            "report_md": str(paper_report_md),
        },
        "outputs": {
            "flow_table_csv": str(flow_table_csv),
            "health_check_csv": str(health_check_csv),
            "next_queue_csv": str(queue_csv),
            "report_md": str(report_md),
        },
        "pm_rules": [
            "Telecom remains a capped observation sleeve.",
            "Do not modify V57f core sleeves, factors, weights, sector caps, or rebalance rules.",
            "Do not tune telecom from this local refresh.",
            "Do not start JoinQuant platform replication or write JoinQuant code.",
            "Do not promote telecom standalone, accepted, or live-trading status.",
        ],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_json_file(summary_json, payload)
    report_md.write_text(_report(payload, flow_rows, health_rows, queue_rows), encoding="utf-8")

    packet = create_agent_loop_packet(
        packet_type="checkpoint_packet",
        objective="telecom_engineering_queue_execution",
        agent="Engineering Agent",
        experiment_layer="paper_trading_preparation",
        decision="continue_next_timebox",
        next_owner="Engineering Agent",
        out_dir=agent_packet_dir,
        timebox_minutes=60,
        artifacts=[str(summary_json), str(report_md), str(health_check_csv), str(paper_summary_json), str(paper_report_md)],
        evidence=[
            f"Local daily status: {status}",
            f"Order health needs_review={local_summary.get('rebalance_order_health', {}).get('needs_review')}",
            f"Paper tracking waits for {next_clean_rebalance_date}.",
        ],
        blockers=[
            "No engineering blocker for observation paper-tracking preparation.",
            "Clean future paper signal cannot be generated until the next rebalance window.",
        ],
        allowed_next_action="wait_until_clean_forward_window_then_refresh_telecom_observation_without_tuning",
        restart_condition=f"rerun near {next_clean_rebalance_date} after PIT panel, prices and dividends are refreshed",
        loop_id=f"telecom_engineering_execution_{as_of_date.replace('-', '')}",
    )
    payload["agent_packet"] = {"packet_path": str(packet.packet_path), "report_path": str(packet.report_path)}
    write_json_file(summary_json, payload)
    return TelecomEngineeringExecutionResult(
        output_dir=out_dir,
        local_daily_dir=local_result.output_dir,
        summary_json=summary_json,
        report_md=report_md,
        flow_table_csv=flow_table_csv,
        health_check_csv=health_check_csv,
        paper_summary_json=paper_summary_json,
        paper_report_md=paper_report_md,
        agent_packet_json=packet.packet_path,
        status=status,
        next_gate=next_gate,
    )


def _health_rows(
    *,
    readiness: dict[str, Any],
    local_summary: dict[str, Any],
    data_health: dict[str, Any],
    order_health_rows: list[dict[str, str]],
    signal_rows: list[dict[str, str]],
    as_of_date: str,
    next_clean_rebalance_date: str,
) -> list[dict[str, str]]:
    order_summary = local_summary.get("rebalance_order_health", {})
    return [
        _health("pm_readiness_allows_engineering", readiness.get("status") == "engineering_observation_sleeve_ready", str(readiness.get("status") or "")),
        _health("engineering_scope_observation_only", readiness.get("pm_decision", {}).get("can_join_v57f_core") is False, json.dumps(readiness.get("pm_decision", {}), ensure_ascii=False)),
        _health("local_daily_refreshed", bool(local_summary.get("metrics")), f"daily_count={local_summary.get('daily_count')}"),
        _health("real_dividends_recorded", int(local_summary.get("dividend_count") or 0) > 0, f"dividend_count={local_summary.get('dividend_count')}"),
        _health("trades_holdings_outputs_exist", int(local_summary.get("trade_count") or 0) > 0, f"trade_count={local_summary.get('trade_count')}"),
        _health("rebalance_order_health_output_exists", bool(order_health_rows), f"rows={len(order_health_rows)}"),
        _health("rebalance_order_health_passed", not bool(order_summary.get("needs_review")), json.dumps(order_summary, ensure_ascii=False)),
        _health("all_signal_dates_present", int(local_summary.get("signal_count") or 0) == len({row.get("trade_date") for row in signal_rows if row.get("trade_date")}), f"summary={local_summary.get('signal_count')} signal_dates={len({row.get('trade_date') for row in signal_rows if row.get('trade_date')})}"),
        _health("panel_file_exists", bool(data_health["panel_exists"]), f"latest={data_health['latest_panel_trade_date']} rows={data_health['panel_row_count']}"),
        _health("price_file_exists", bool(data_health["price_exists"]), f"latest={data_health['latest_price_date']} rows={data_health['price_row_count']}"),
        _health("dividend_file_exists", bool(data_health["dividend_exists"]) and int(data_health["dividend_row_count"] or 0) > 0, f"latest={data_health['latest_dividend_pay_date']} rows={data_health['dividend_row_count']}"),
        _health("benchmark_file_exists", bool(data_health["benchmark_exists"]), f"latest={data_health['latest_benchmark_date']} rows={data_health['benchmark_row_count']}"),
        _health("current_window_ends_2026_05_31", str(local_summary.get("window", {}).get("end_date")) == "2026-05-31", str(local_summary.get("window", {}))),
        _health("future_window_not_due", date.fromisoformat(next_clean_rebalance_date) > date.fromisoformat(as_of_date), f"as_of={as_of_date} target={next_clean_rebalance_date}"),
    ]


def _data_health(panel_csv: Path, price_csv: Path, dividend_csv: Path, benchmark_csv: Path, next_clean_rebalance_date: str) -> dict[str, Any]:
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


def _flow_rows(status: str) -> list[dict[str, str]]:
    core = "completed" if status.startswith("paper_tracking") else "needs_review"
    return [
        _flow("1", "Project Manager Agent", "telecom_engineering_next_agent_queue.csv", "Confirm Engineering scope is capped observation only", "scope lock", "no_v57f_change", "completed", "modify V57f"),
        _flow("2", "Engineering Agent", "frozen telecom overlay config + signals", "Rerun local daily simulation through 2026-05-31", "local daily refresh", "no_tuning", core, "change factors or weights"),
        _flow("3", "Engineering Agent", "real daily prices + cash dividends", "Record daily returns, trades, holdings, cash dividends and benchmark", "local output files", "real_data_outputs", core, "ignore dividends"),
        _flow("4", "Engineering Agent", "rebalance_signals + trades + holdings", "Generate and review rebalance_order_health", "order health evidence", "no_empty_rebalance_bug", core, "ignore no-order dates"),
        _flow("5", "Engineering Agent", "refreshed outputs", "Build telecom paper tracking readiness packet", "paper packet", "future_window_gate", core, "generate late paper signal"),
        _flow("6", "Project Manager Agent", "paper packet", "Route to wait for the next clean rebalance window", "next queue", "no_platform_replication", core, "write JoinQuant code"),
    ]


def _next_queue(status: str, next_clean_rebalance_date: str) -> list[dict[str, str]]:
    if not status.startswith("paper_tracking"):
        return [
            {
                "queue_rank": "1",
                "sector_id": "telecom_operators",
                "owner": "Engineering Agent",
                "task": "Repair failed telecom engineering health checks before paper tracking.",
                "input_artifacts": "telecom_engineering_execution_health_checks.csv",
                "output_artifacts": "repaired local daily refresh packet",
                "gate": "engineering_repair",
                "blocked_actions": "do_not_modify_V57f;do_not_tune;do_not_platform_replication",
            }
        ]
    return [
        {
            "queue_rank": "1",
            "sector_id": "telecom_operators",
            "owner": "Engineering Agent",
            "task": f"Wait until {next_clean_rebalance_date}, then refresh PIT/prices/dividends and generate clean telecom observation paper signal without tuning.",
            "input_artifacts": "telecom paper tracking readiness packet",
            "output_artifacts": "clean forward telecom observation paper signal",
            "gate": "future_paper_tracking_window",
            "blocked_actions": "do_not_modify_V57f;do_not_tune;do_not_platform_replication;do_not_write_joinquant_code",
        }
    ]


def _paper_payload(
    *,
    local_summary: dict[str, Any],
    data_health: dict[str, Any],
    health_rows: list[dict[str, str]],
    local_daily_dir: Path,
    as_of_date: str,
    next_clean_rebalance_date: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "strategy_id": DEFAULT_OVERLAY_ID,
        "sector_id": "telecom_operators",
        "experiment_layer": "paper_trading_preparation",
        "status": "paper_tracking_ready_waiting_for_future_window" if all(row["status"] == "passed" for row in health_rows[:-1]) else "needs_review_before_paper_tracking",
        "as_of_date": as_of_date,
        "next_clean_rebalance_date": next_clean_rebalance_date,
        "target_date_is_future": date.fromisoformat(next_clean_rebalance_date) > date.fromisoformat(as_of_date),
        "local_daily_dir": str(local_daily_dir),
        "local_daily_summary": {
            "signal_count": local_summary.get("signal_count"),
            "daily_count": local_summary.get("daily_count"),
            "trade_count": local_summary.get("trade_count"),
            "dividend_count": local_summary.get("dividend_count"),
            "rebalance_order_health": local_summary.get("rebalance_order_health", {}),
            "metrics": local_summary.get("metrics", {}),
        },
        "data_health": data_health,
        "health_checks": health_rows,
        "pm_rules": [
            "Telecom remains observation only.",
            "No core V57f inclusion, platform replication, JoinQuant code, or tuning is allowed.",
            "The next usable paper signal must be generated at the future rebalance window, not retroactively.",
        ],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def _status_and_gate(health_rows: list[dict[str, str]], as_of_date: str, next_clean_rebalance_date: str) -> tuple[str, str]:
    failed_core = [row for row in health_rows[:-1] if row["status"] != "passed"]
    if failed_core:
        return "needs_review_before_paper_tracking", "repair_failed_engineering_health_checks"
    if date.fromisoformat(next_clean_rebalance_date) > date.fromisoformat(as_of_date):
        return "paper_tracking_ready_waiting_for_future_window", "wait_until_clean_forward_window"
    return "ready_for_clean_paper_signal_generation", "generate_clean_paper_signal_without_tuning"


def _report(payload: dict[str, Any], flow_rows: list[dict[str, str]], health_rows: list[dict[str, str]], queue_rows: list[dict[str, str]]) -> str:
    metrics = payload["local_daily_summary"]["metrics"]
    order = payload["local_daily_summary"]["rebalance_order_health_summary"]
    lines = [
        "# Telecom Engineering Execution Report",
        "",
        f"Status: `{payload['status']}`",
        f"Next gate: `{payload['next_gate']}`",
        "",
        "## Local Refresh",
        "",
        f"- Window: `{payload['local_daily_summary']['summary_json']}`",
        f"- Strategy return: `{_pct(metrics.get('strategy_return'))}`",
        f"- Max drawdown: `{_pct(metrics.get('max_drawdown'))}`",
        f"- Trade count: `{payload['local_daily_summary']['trade_count']}`",
        f"- Dividend count: `{payload['local_daily_summary']['dividend_count']}`",
        f"- Order health needs review: `{order.get('needs_review')}`",
        "",
        "## Detailed Flow Table",
        "",
        "| Step | Owner | Action | Gate | Status | Forbidden action |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for row in flow_rows:
        lines.append(f"| {row['step']} | {row['owner']} | {row['action']} | `{row['gate']}` | `{row['status']}` | {row['forbidden_action']} |")
    lines.extend(["", "## Health Checks", "", "| Check | Status | Detail |", "| --- | --- | --- |"])
    for row in health_rows:
        lines.append(f"| `{row['check']}` | `{row['status']}` | {row['detail']} |")
    lines.extend(["", "## Next Queue", "", "| Rank | Owner | Task | Gate |", "| ---: | --- | --- | --- |"])
    for row in queue_rows:
        lines.append(f"| {row['queue_rank']} | {row['owner']} | {row['task']} | `{row['gate']}` |")
    lines.extend(["", "## Rules", ""])
    for rule in payload["pm_rules"]:
        lines.append(f"- {rule}")
    lines.append("")
    return "\n".join(lines)


def _paper_report(payload: dict[str, Any]) -> str:
    metrics = payload["local_daily_summary"]["metrics"]
    lines = [
        "# Telecom Paper Tracking Readiness",
        "",
        f"Status: `{payload['status']}`",
        f"As of: `{payload['as_of_date']}`",
        f"Next clean rebalance date: `{payload['next_clean_rebalance_date']}`",
        "",
        f"Local refresh return: `{_pct(metrics.get('strategy_return'))}`; max drawdown: `{_pct(metrics.get('max_drawdown'))}`.",
        "",
        "Telecom remains a capped observation sleeve. This packet prepares future paper tracking only; it does not generate a retroactive paper signal.",
        "",
    ]
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def _health(name: str, passed: bool, detail: str) -> dict[str, str]:
    return {"check": name, "status": "passed" if passed else "failed", "detail": detail}


def _flow(step: str, owner: str, input_: str, action: str, output: str, gate: str, status: str, forbidden_action: str) -> dict[str, str]:
    return {
        "step": step,
        "owner": owner,
        "input": input_,
        "action": action,
        "output": output,
        "gate": gate,
        "status": status,
        "forbidden_action": forbidden_action,
    }


def _latest_date(rows: list[dict[str, str]], field: str) -> str:
    values = [str(row.get(field) or "")[:10] for row in rows if row.get(field)]
    return max(values) if values else ""


def _row_date(row: dict[str, str], field: str) -> str:
    return str(row.get(field) or "")[:10]


def _pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return ""

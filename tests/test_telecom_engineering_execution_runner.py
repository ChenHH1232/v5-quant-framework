from __future__ import annotations

import csv
import json
from pathlib import Path

from v5.telecom_engineering_execution_runner import execute_telecom_engineering_queue


def test_execute_telecom_engineering_queue_builds_paper_packet(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    price = tmp_path / "prices.csv"
    dividend = tmp_path / "dividends.csv"
    benchmark = tmp_path / "benchmark.csv"
    panel = tmp_path / "panel.csv"
    signals = tmp_path / "signals.csv"
    readiness = tmp_path / "readiness.json"

    _write_json(
        config,
        {
            "project": "telecom_overlay_test",
            "sectors": [{"sector_id": "telecom_operators", "price_csv": str(price), "dividend_csv": str(dividend)}],
            "portfolio": {"start_date": "2026-01-01", "end_date": "2026-05-31"},
        },
    )
    _write_csv(
        price,
        ["date", "code", "open", "close", "high_limit", "low_limit", "paused"],
        [
            ["2026-01-05", "600050.XSHG", "10", "10.2", "11", "9", "0"],
            ["2026-01-06", "600050.XSHG", "10.2", "10.4", "11", "9", "0"],
            ["2026-04-01", "600050.XSHG", "10.4", "10.6", "11.5", "9.5", "0"],
            ["2026-04-02", "600050.XSHG", "10.6", "10.8", "11.5", "9.5", "0"],
            ["2026-05-29", "600050.XSHG", "10.8", "11.0", "12", "10", "0"],
        ],
    )
    _write_csv(dividend, ["ex_date", "pay_date", "code", "net_cash_per_share"], [["2026-04-02", "2026-04-02", "600050.XSHG", "0.1"]])
    _write_csv(benchmark, ["date", "benchmark_id", "close"], [["2026-05-29", "telecom", "1"]])
    _write_csv(panel, ["trade_date", "code"], [["2026-01-05", "600050.XSHG"], ["2026-04-01", "600050.XSHG"]])
    _write_csv(
        signals,
        ["trade_date", "code", "target_weight"],
        [["2026-01-05", "600050.XSHG", "0.5"], ["2026-04-01", "600050.XSHG", "0.5"]],
    )
    _write_json(
        readiness,
        {
            "status": "engineering_observation_sleeve_ready",
            "pm_decision": {"can_join_v57f_core": False},
        },
    )

    result = execute_telecom_engineering_queue(
        config_path=config,
        signals_csv=signals,
        readiness_summary=readiness,
        panel_csv=panel,
        price_csv=price,
        dividend_csv=dividend,
        benchmark_csv=benchmark,
        local_daily_out=tmp_path / "local",
        out_dir=tmp_path / "out",
        paper_out_dir=tmp_path / "paper",
        agent_packet_dir=tmp_path / "packets",
        as_of_date="2026-07-24",
        next_clean_rebalance_date="2026-10-08",
    )

    assert result.status == "paper_tracking_ready_waiting_for_future_window"
    payload = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert payload["local_daily_summary"]["dividend_count"] == 1
    assert payload["local_daily_summary"]["rebalance_order_health_summary"]["needs_review"] is False
    assert payload["paper_tracking"]["summary_json"] == str(result.paper_summary_json)
    paper = json.loads(result.paper_summary_json.read_text(encoding="utf-8"))
    assert paper["target_date_is_future"] is True
    assert paper["status"] == "paper_tracking_ready_waiting_for_future_window"
    health = list(csv.DictReader(result.health_check_csv.open("r", encoding="utf-8-sig")))
    assert all(row["status"] == "passed" for row in health)
    assert result.agent_packet_json.exists()


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_csv(path: Path, fieldnames: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fieldnames)
        writer.writerows(rows)

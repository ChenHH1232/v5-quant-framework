from __future__ import annotations

import csv
import json
from pathlib import Path

from v5.gas_water_paper_tracking_runner import build_gas_water_paper_tracking_packet


def test_gas_water_paper_tracking_packet_waits_for_future_window(tmp_path: Path) -> None:
    local_daily = tmp_path / "local_daily" / "gas_water"
    local_daily.mkdir(parents=True)
    (local_daily / "summary.json").write_text(
        json.dumps(
            {
                "strategy_id": "gas_water_v57b_text_debt_state_guard_v59b",
                "status": "engineering_local_daily_simulation_passed_ready_for_platform_preparation",
                "signal_count": 2,
                "daily_count": 3,
                "state_guard": {"blocked_count": 1, "blocked_dates": ["2026-04-01"]},
                "rebalance_order_health": {
                    "needs_review": False,
                    "unexpected_rebalance_issue_count": 0,
                    "intentional_guard_cash_block_count": 1,
                },
            }
        ),
        encoding="utf-8",
    )
    _write_csv(local_daily / "rebalance_order_health.csv", ["trade_date", "order_health_status"], [["2026-04-01", "intentional_guard_cash_block_no_order_needed"]])
    _write_csv(local_daily / "guard_decisions.csv", ["trade_date", "blocked"], [["2026-04-01", "1"]])
    _write_csv(local_daily / "rebalance_signals.csv", ["trade_date", "selected_codes"], [["2026-04-01", ""]])

    panel = tmp_path / "panel.csv"
    price = tmp_path / "price.csv"
    dividend = tmp_path / "dividend.csv"
    benchmark = tmp_path / "benchmark.csv"
    _write_csv(panel, ["trade_date", "code"], [["2026-04-01", "000001.XSHG"]])
    _write_csv(price, ["date", "code", "open", "close"], [["2026-05-31", "000001.XSHG", "1", "1"]])
    _write_csv(dividend, ["pay_date", "code", "net_cash_per_share"], [["2026-05-20", "000001.XSHG", "0.1"]])
    _write_csv(benchmark, ["date", "benchmark_id", "close"], [["2026-05-31", "gas_water", "1"]])

    promotion_queue = tmp_path / "sleeve_promotion_queue.csv"
    _write_csv(promotion_queue, ["rank", "sector_id"], [["1", "gas_water_operators"]])
    selected_queue = tmp_path / "selected_candidate_agent_queue.csv"
    _write_csv(selected_queue, ["queue_rank", "sector_id", "owner"], [["1", "gas_water_operators", "Engineering Agent"]])

    result = build_gas_water_paper_tracking_packet(
        local_daily_dir=local_daily,
        panel_csv=panel,
        price_csv=price,
        dividend_csv=dividend,
        benchmark_csv=benchmark,
        promotion_queue_csv=promotion_queue,
        selected_agent_queue_csv=selected_queue,
        out_dir=tmp_path / "out",
        agent_packet_dir=tmp_path / "packets",
        as_of_date="2026-07-22",
        next_clean_rebalance_date="2026-10-08",
    )

    assert result.status == "paper_tracking_ready_waiting_for_future_window"
    assert result.next_gate == "wait_until_clean_forward_window"
    payload = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert payload["selected_from_promotion_queue"] == "gas_water_operators"
    assert payload["data_health"]["target_panel_rows"] == 0
    assert result.agent_packet_json.exists()
    report = result.report_path.read_text(encoding="utf-8")
    assert "Detailed Flow Table" in report
    assert "Do not tune" not in report
    assert "No factor, weight" in report


def _write_csv(path: Path, fields: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerows(rows)

from __future__ import annotations

import csv
import json
from pathlib import Path

from v5.home_appliances_paper_tracking_runner import build_home_appliances_paper_tracking_packet


def test_home_appliances_paper_tracking_packet_waits_for_future_window(tmp_path: Path) -> None:
    local_daily = tmp_path / "local_daily"
    local_daily.mkdir()
    (local_daily / "summary.json").write_text(
        json.dumps(
            {
                "engineering_gate": "engineering_local_daily_simulation_passed",
                "signal_count": 20,
                "daily_count": 1228,
                "signal_coverage": {"status": "passed", "actual_signal_count": 20, "expected_rebalance_count": 20},
                "rebalance_order_health": {
                    "needs_review": False,
                    "normal_rebalance_count": 20,
                    "first_executed_order_date": "2021-07-01",
                    "first_position_date": "2021-07-01",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    _write_csv(local_daily / "rebalance_order_health.csv", ["trade_date", "status"], [["2021-07-01", "normal"]])
    _write_csv(local_daily / "rebalance_signals.csv", ["trade_date", "selected_codes"], [["2026-04-01", "000001.XSHE"]])

    promotion_queue = tmp_path / "sleeve_promotion_queue.csv"
    _write_csv(
        promotion_queue,
        ["rank", "sector_id", "pm_gate"],
        [
            ["1", "gas_water_operators", "paper_tracking_only_no_core_inclusion"],
            ["2", "home_appliances", "paper_tracking_only_no_core_inclusion"],
        ],
    )
    panel = tmp_path / "panel.csv"
    price = tmp_path / "prices.csv"
    dividends = tmp_path / "dividends.csv"
    benchmark = tmp_path / "benchmark.csv"
    _write_csv(panel, ["trade_date", "code"], [["2026-04-01", "000001.XSHE"]])
    _write_csv(price, ["date", "code", "open", "close"], [["2026-05-29", "000001.XSHE", "1", "1"]])
    _write_csv(dividends, ["pay_date", "code", "net_cash_per_share"], [["2026-05-29", "000001.XSHE", "0.1"]])
    _write_csv(benchmark, ["date", "close"], [["2026-05-29", "1"]])

    result = build_home_appliances_paper_tracking_packet(
        local_daily_dir=local_daily,
        panel_csv=panel,
        price_csv=price,
        dividend_csv=dividends,
        benchmark_csv=benchmark,
        promotion_queue_csv=promotion_queue,
        out_dir=tmp_path / "paper",
        agent_packet_dir=tmp_path / "packet",
        as_of_date="2026-07-22",
        next_clean_rebalance_date="2026-10-08",
    )

    payload = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert result.status == "paper_tracking_ready_waiting_for_future_window"
    assert payload["promotion_queue_rank"] == 2
    assert payload["next_gate"] == "wait_until_clean_forward_window"
    assert "silently added to frozen V57f" in payload["pm_rules"][0]
    health = list(csv.DictReader(result.health_check_csv.open("r", encoding="utf-8")))
    assert all(row["status"] == "passed" for row in health[:9])


def _write_csv(path: Path, fieldnames: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fieldnames)
        writer.writerows(rows)

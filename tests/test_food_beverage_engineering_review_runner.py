from __future__ import annotations

import csv
import json
from pathlib import Path

from v5.food_beverage_engineering_review_runner import run_food_beverage_engineering_review


def test_food_beverage_engineering_review_explains_skips_and_blocks_empty_dividends(tmp_path: Path) -> None:
    local_daily = tmp_path / "local"
    local_daily.mkdir()
    _write_json(
        local_daily / "summary.json",
        {
            "strategy_id": "food_beverage_packaged_food_ocf_quality_v5a9a",
            "window": {"start_date": "2021-05-01", "end_date": "2026-05-31"},
            "metrics": {
                "strategy_return": 0.05,
                "benchmark_return": -0.03,
                "excess_return": 0.08,
                "max_drawdown": 0.45,
                "sharpe": 0.16,
            },
            "rebalance_order_health": {
                "rebalance_signal_count": 1,
                "normal_rebalance_count": 1,
                "no_order_rebalance_count": 0,
                "no_order_no_position_count": 0,
                "blocked_or_unfilled_rebalance_count": 0,
            },
        },
    )
    _write_csv(
        local_daily / "rebalance_order_health.csv",
        [
            "trade_date",
            "selected_count",
            "holding_count_after_rebalance",
            "cash_weight_after_rebalance",
        ],
        [["2022-01-04", "2", "1", "0.40"]],
    )
    _write_csv(local_daily / "rebalance_signals.csv", ["trade_date", "selected_codes"], [["2022-01-04", "000001.XSHE;000002.XSHE"]])
    _write_csv(
        local_daily / "trades.csv",
        ["trade_date", "code", "side", "amount", "price", "value", "commission", "target_amount", "reason"],
        [
            ["2022-01-04", "000001.XSHE", "buy_skipped", "1000", "10.0", "0", "0", "1000", "high_limit"],
            ["2022-01-04", "000002.XSHE", "buy", "100", "20.0", "2000", "5", "1000", ""],
        ],
    )
    _write_csv(local_daily / "dividends.csv", ["trade_date", "code", "amount", "net_cash_per_share", "dividend_cash"], [])
    price_csv = tmp_path / "prices.csv"
    _write_csv(
        price_csv,
        ["date", "code", "open", "close", "high_limit", "low_limit", "paused"],
        [["2022-01-04", "000001.XSHE", "10.0", "9.5", "10.0", "8.0", "0"]],
    )
    dividend_csv = tmp_path / "cash_dividends.csv"
    _write_csv(
        dividend_csv,
        ["code", "report_period", "announce_date", "record_date", "ex_date", "pay_date", "cash_per_share"],
        [],
    )

    result = run_food_beverage_engineering_review(
        local_daily_dir=local_daily,
        price_csv=price_csv,
        dividend_cash_csv=dividend_csv,
        out_dir=tmp_path / "out",
    )

    assert result.status == "engineering_data_blocker_confirmed"
    payload = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert payload["pm_decision"]["can_join_v57f_core"] is False
    assert payload["pm_decision"]["can_enter_platform_replication"] is False
    assert payload["dividend_gap"]["status"] == "dividend_source_empty"
    assert payload["order_health"]["status"] == "explained_needs_review"
    assert payload["startup_gap"]["status"] == "research_pit_window_gap"

    skip_rows = list(csv.DictReader((tmp_path / "out" / "food_beverage_order_skip_diagnosis.csv").open("r", encoding="utf-8-sig")))
    assert skip_rows[0]["tradability_check"] == "confirmed_buy_open_at_high_limit"
    partial_rows = list(csv.DictReader((tmp_path / "out" / "food_beverage_partial_fill_diagnosis.csv").open("r", encoding="utf-8-sig")))
    assert partial_rows[0]["code"] == "000002.XSHE"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_csv(path: Path, fieldnames: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fieldnames)
        writer.writerows(rows)

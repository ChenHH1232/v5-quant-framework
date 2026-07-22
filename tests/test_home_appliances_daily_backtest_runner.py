from __future__ import annotations

import csv
import json
from pathlib import Path

from v5.home_appliances_daily_backtest_runner import run_home_appliances_daily_backtest


def test_home_appliances_daily_backtest_requires_gate_and_writes_order_health(tmp_path: Path) -> None:
    spec = tmp_path / "strategy.json"
    spec.write_text(
        json.dumps(
            {
                "meta": {"strategy_id": "home_appliances_test", "name": "Home Appliances Test", "objective": "test"},
                "universe": {"name": "test", "construction": "test", "point_in_time": True},
                "data": {"vendor": "test", "price_frequency": "daily", "financial_as_of_policy": "test"},
                "signals": {
                    "factors": [
                        {
                            "name": "operating_cash_flow_yield",
                            "source": "test",
                            "direction": "higher_is_better",
                            "definition": "test",
                            "as_of": "test",
                            "disclosure_lag_days": 1,
                            "missing_policy": "drop",
                        },
                        {
                            "name": "operating_cash_flow_to_net_profit",
                            "source": "test",
                            "direction": "higher_is_better",
                            "definition": "test",
                            "as_of": "test",
                            "disclosure_lag_days": 1,
                            "missing_policy": "drop",
                        },
                    ],
                    "scoring": {
                        "method": "weighted_composite",
                        "weights": {"operating_cash_flow_yield": 0.7, "operating_cash_flow_to_net_profit": 0.3},
                    },
                },
                "schedule": {"signal_frequency": "quarterly", "rebalance_frequency": "quarterly", "rebalance_months": [7]},
                "portfolio": {"selection_count": 2, "weighting": "equal", "max_position_weight": 0.5},
                "risk": {"defensive_asset": "cash", "defensive_rule": {"enabled": False}},
                "validation": {"method": "test", "train_years": 1, "test_years": 1},
                "execution": {"commission_bps": 3, "slippage_bps": 5, "suspension_policy": "skip", "limit_policy": "skip"},
                "outputs": {"save_holdings": True, "save_rebalance_signals": True, "report": "markdown"},
            }
        ),
        encoding="utf-8",
    )
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps(
            {
                "status": "engineering_handoff_ready_local_daily_only",
                "state_policy": {"decision": "no_state_scoring_or_guard_policy_accepted_for_engineering_smoke_test"},
            }
        ),
        encoding="utf-8",
    )
    panel = tmp_path / "panel.csv"
    _write_csv(
        panel,
        ["trade_date", "code", "operating_cash_flow_yield", "operating_cash_flow_to_net_profit", "future_return"],
        [
            ["2021-07-01", "000001.XSHE", "0.2", "1.2", "0.01"],
            ["2021-07-01", "000002.XSHE", "0.1", "1.0", "0.02"],
            ["2021-07-01", "000003.XSHE", "-0.1", "0.1", "-0.01"],
        ],
    )
    price = tmp_path / "price.csv"
    _write_csv(
        price,
        ["date", "code", "open", "close", "high_limit", "low_limit", "paused"],
        [
            ["2021-07-01", "000001.XSHE", "10", "11", "12", "8", "0"],
            ["2021-07-01", "000002.XSHE", "20", "21", "24", "16", "0"],
            ["2021-07-02", "000001.XSHE", "11", "12", "13", "9", "0"],
            ["2021-07-02", "000002.XSHE", "21", "22", "25", "17", "0"],
        ],
    )
    dividend = tmp_path / "dividend.csv"
    _write_csv(dividend, ["pay_date", "code", "net_cash_per_share"], [["2021-07-02", "000001.XSHE", "0.1"]])
    benchmark = tmp_path / "benchmark.csv"
    _write_csv(
        benchmark,
        ["date", "code", "close"],
        [["2021-07-01", "B", "100"], ["2021-07-02", "B", "101"]],
    )

    result = run_home_appliances_daily_backtest(
        spec_path=spec,
        panel_csv=panel,
        execution_price_csv=price,
        dividend_cash_csv=dividend,
        benchmark_csv=benchmark,
        engineering_gate_summary=gate,
        out_dir=tmp_path / "out",
        benchmark_id="B",
        start_date="2021-07-01",
        end_date="2021-07-02",
        initial_cash=100_000,
        lot_size=100,
    )

    assert result.status == "engineering_local_daily_simulation_passed"
    payload = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "home_appliances_daily_joinquant_like_no_state_policy"
    assert payload["engineering_gate"] == "engineering_local_daily_simulation_passed"
    assert (result.summary_path.parent / "rebalance_order_health.csv").exists()
    assert (result.summary_path.parent / "trades.csv").exists()
    assert (result.summary_path.parent / "dividends.csv").exists()


def _write_csv(path: Path, fields: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerows(rows)

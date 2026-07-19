from __future__ import annotations

import json
from pathlib import Path

from v5.basket_daily_backtest_runner import run_basket_daily_backtest


def test_basket_daily_backtest_writes_daily_trades_dividends_and_benchmark(tmp_path: Path) -> None:
    prices = tmp_path / "prices.csv"
    prices.write_text(
        "date,code,open,close,high_limit,low_limit,paused\n"
        "2021-01-04,A,10,10,11,9,0\n"
        "2021-01-05,A,10,11,11,9,0\n"
        "2021-01-06,A,11,12,12.1,9.9,0\n",
        encoding="utf-8",
    )
    dividends = tmp_path / "dividends.csv"
    dividends.write_text(
        "code,ex_date,pay_date,net_cash_per_share,stock_dividend_ratio\n"
        "A,2021-01-05,2021-01-05,0,1\n"
        "A,2021-01-06,2021-01-06,1,0\n",
        encoding="utf-8",
    )
    signals = tmp_path / "signals.csv"
    signals.write_text(
        "trade_date,code,target_weight\n"
        "2021-01-04,A,1\n",
        encoding="utf-8",
    )
    config = {
        "project": "test_basket",
        "portfolio": {"start_date": "2021-01-04", "end_date": "2021-01-06"},
        "sectors": [{"sector_id": "s", "strategy_id": "x", "price_csv": str(prices), "dividend_csv": str(dividends)}],
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    result = run_basket_daily_backtest(
        config_path,
        signals,
        tmp_path / "out",
        initial_cash=10000,
        target_exposure=1.0,
        lot_size=100,
        open_commission=0.0,
        close_commission=0.0,
        min_commission=0.0,
    )

    assert result.daily_count == 3
    assert result.trade_count == 1
    assert result.dividend_count == 1
    assert result.corporate_action_count == 1
    assert (result.output_dir / "rebalance_signals.csv").exists()
    assert (result.output_dir / "corporate_actions.csv").exists()
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert summary["metrics"]["strategy_return"] > 0
    benchmark_text = result.benchmark_path.read_text(encoding="utf-8")
    assert "dividend_constituent_count" in benchmark_text

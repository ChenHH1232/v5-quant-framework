from __future__ import annotations

import json
from pathlib import Path

from v5.basket_failure_attribution_runner import run_basket_failure_attribution


def test_basket_failure_attribution_writes_diagnostic_outputs(tmp_path: Path) -> None:
    prices = tmp_path / "prices.csv"
    prices.write_text(
        "date,code,open,close\n"
        "2025-01-02,A,10,10\n"
        "2025-01-03,A,11,11\n"
        "2025-01-02,B,10,10\n"
        "2025-01-03,B,12,12\n",
        encoding="utf-8",
    )
    dividends = tmp_path / "dividends.csv"
    dividends.write_text(
        "code,ex_date,pay_date,net_cash_per_share,stock_dividend_ratio\n"
        "A,2025-01-03,2025-01-03,0.1,0\n",
        encoding="utf-8",
    )
    signals = tmp_path / "signals.csv"
    signals.write_text(
        "trade_date,code,sector_id,target_weight,score\n"
        "2025-01-02,A,s,1,1\n",
        encoding="utf-8",
    )
    daily_dir = tmp_path / "daily"
    daily_dir.mkdir()
    (daily_dir / "daily_returns.csv").write_text(
        "trade_date,strategy_return,benchmark_return,excess_return,cash_weight,rebalance\n"
        "2025-01-02,0,0,0,0.01,1\n"
        "2025-01-03,0.11,0.15,-0.04,0.01,0\n",
        encoding="utf-8",
    )
    config = {
        "project": "test_basket",
        "sectors": [{"sector_id": "s", "strategy_id": "x", "price_csv": str(prices), "dividend_csv": str(dividends)}],
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    result = run_basket_failure_attribution(
        config_path,
        daily_dir,
        signals,
        tmp_path / "out",
        focus_years=(2025,),
    )

    assert result.yearly_count == 1
    assert (result.output_dir / "yearly_performance.csv").exists()
    assert (result.output_dir / "yearly_sector_attribution.csv").exists()
    assert (result.output_dir / "missed_winners_2025_2026.csv").exists()
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "local_failure_attribution_completed_not_acceptance"

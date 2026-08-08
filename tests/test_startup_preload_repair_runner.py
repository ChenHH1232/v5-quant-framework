from __future__ import annotations

import json
from pathlib import Path

from v5.startup_preload import build_startup_date_model
from v5.v5_startup_preload_repair_runner import run_v5_startup_preload_repair


def test_startup_date_model_blocks_when_warmup_history_missing() -> None:
    model = build_startup_date_model(
        deployment_date="2021-05-01",
        trading_days=["2021-05-06", "2021-05-07"],
        regular_rebalance_dates=["2021-10-08"],
    )
    assert model.first_tradable_date == "2021-05-06"
    assert model.startup_ready is False
    assert model.blocker_reason == "insufficient_pre_deployment_price_history_for_required_lookback"


def test_startup_preload_repair_runner_outputs_blocker_without_predeployment_prices(tmp_path: Path) -> None:
    _write_minimal_workspace(tmp_path)

    summary = run_v5_startup_preload_repair(tmp_path)

    assert summary["status"] == "blocked_requires_warmup_price_data"
    assert summary["deployment_model"]["deployment_date"] == "2021-05-01"
    assert summary["deployment_model"]["first_tradable_date"] == "2021-05-06"
    assert summary["pre_post"]["old_first_signal_date"] == "2021-10-08"
    blockers = (tmp_path / "v5_startup_preload_repair" / "current" / "v5_startup_blockers.csv").read_text(encoding="utf-8-sig")
    assert "missing_pre_deployment_warmup_prices" in blockers


def _write_minimal_workspace(root: Path) -> None:
    (root / "config").mkdir()
    (root / "validation_formal_v57f_etf_constructor").mkdir()
    (root / "local_daily_backtests_v57f_etf" / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f").mkdir(parents=True)
    for path in [
        root / "v5c_closeout" / "current",
        root / "v5d_closeout" / "current",
        root / "v5b_non_core_sector_disposition" / "current",
        root / "data",
    ]:
        path.mkdir(parents=True, exist_ok=True)

    panel = root / "data" / "panel.csv"
    panel.write_text(
        "trade_date,code,dividend_yield,low_vol_score,volatility_120d,max_drawdown_120d,operating_cash_flow_yield\n"
        "2021-05-06,A,1,,,,1\n"
        "2021-10-08,A,1,1,0.1,0.1,1\n",
        encoding="utf-8",
    )
    prices = root / "data" / "prices.csv"
    prices.write_text(
        "date,code,open,close,high_limit,low_limit,paused\n"
        "2021-05-06,A,10,10,11,9,0\n"
        "2021-10-08,A,10,10,11,9,0\n",
        encoding="utf-8",
    )
    dividends = root / "data" / "dividends.csv"
    dividends.write_text("code,ex_date,pay_date,net_cash_per_share,stock_dividend_ratio\n", encoding="utf-8")
    config = {
        "project": "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f",
        "sectors": [{"sector_id": "bank", "strategy_id": "x", "panel_csv": str(panel), "price_csv": str(prices), "dividend_csv": str(dividends)}],
        "signals": {
            "factors": [{"name": "operating_cash_flow_yield", "direction": "higher_is_better"}],
            "scoring": {"method": "weighted_composite", "min_factor_count": 1, "weights": {"operating_cash_flow_yield": 1}},
        },
        "portfolio": {
            "start_date": "2021-05-01",
            "end_date": "2021-10-08",
            "required_fields": ["low_vol_score", "volatility_120d", "dividend_yield"],
            "target_count": 1,
            "sector_weight_cap": 1.0,
            "single_stock_weight_cap": 1.0,
        },
    }
    (root / "config" / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f.json").write_text(json.dumps(config), encoding="utf-8")
    (root / "validation_formal_v57f_etf_constructor" / "basket_rebalance_signals.csv").write_text(
        "trade_date,code,sector_id,selected_rank,selected_count,target_weight\n"
        "2021-10-08,A,bank,1,1,1\n",
        encoding="utf-8",
    )
    old_summary = {
        "metrics": {"strategy_return": 0.1, "max_drawdown": 0.02},
        "trade_count": 1,
        "rebalance_order_health": {
            "first_executed_order_date": "2021-10-08",
            "first_position_date": "2021-10-08",
            "blocked_or_unfilled_rebalance_count": 0,
        },
    }
    (root / "local_daily_backtests_v57f_etf" / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f" / "summary.json").write_text(json.dumps(old_summary), encoding="utf-8")
    (root / "v5c_closeout" / "current" / "v5c_closeout_summary.json").write_text(json.dumps({"status": "ok"}), encoding="utf-8")
    (root / "v5d_closeout" / "current" / "v5d_closeout_summary.json").write_text(json.dumps({"status": "ok"}), encoding="utf-8")
    (root / "v5b_non_core_sector_disposition" / "current" / "v5b_non_core_sector_disposition_summary.json").write_text(json.dumps({"status": "ok"}), encoding="utf-8")

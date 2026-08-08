from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from v5.basket_constructor_runner import construct_dividend_low_vol_fcf_basket


def test_basket_constructor_applies_sector_cap(tmp_path: Path) -> None:
    panel_a = tmp_path / "a.csv"
    panel_b = tmp_path / "b.csv"
    panel_a.write_text(
        "trade_date,code,dividend_yield,operating_cash_flow_yield,free_cash_flow_yield,low_price_to_book,low_vol_score,volatility_120d,max_drawdown_120d,capex_burden\n"
        "2021-01-01,A1,10,1,1,1,1,0.1,0.1,0.1\n"
        "2021-01-01,A2,9,1,1,1,1,0.1,0.1,0.1\n"
        "2021-01-01,A3,8,1,1,1,1,0.1,0.1,0.1\n",
        encoding="utf-8",
    )
    panel_b.write_text(
        "trade_date,code,dividend_yield,operating_cash_flow_yield,free_cash_flow_yield,low_price_to_book,low_vol_score,volatility_120d,max_drawdown_120d,capex_burden\n"
        "2021-01-01,B1,7,1,1,1,1,0.1,0.1,0.1\n"
        "2021-01-01,B2,6,1,1,1,1,0.1,0.1,0.1\n"
        "2021-01-01,B3,5,1,1,1,1,0.1,0.1,0.1\n",
        encoding="utf-8",
    )
    config = {
        "project": "test",
        "sectors": [
            {"sector_id": "a", "strategy_id": "sa", "panel_csv": str(panel_a)},
            {"sector_id": "b", "strategy_id": "sb", "panel_csv": str(panel_b)},
        ],
        "signals": {
            "factors": [
                {"name": "dividend_yield", "direction": "higher_is_better"},
                {"name": "volatility_120d", "direction": "lower_is_better"},
            ],
            "scoring": {"method": "weighted_composite", "min_factor_count": 1, "weights": {"dividend_yield": 1}},
        },
        "portfolio": {"target_count": 4, "sector_weight_cap": 0.5, "single_stock_weight_cap": 0.25},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    result = construct_dividend_low_vol_fcf_basket(config_path, tmp_path / "out")

    signals = result.signals_path.read_text(encoding="utf-8")
    assert "A1" in signals
    assert "A3" not in signals
    assert result.holding_count == 4


def test_basket_constructor_does_not_renormalize_past_sector_cap_when_selection_is_short(tmp_path: Path) -> None:
    panel_a = tmp_path / "a.csv"
    panel_b = tmp_path / "b.csv"
    panel_a.write_text(
        "trade_date,code,dividend_yield,volatility_120d\n"
        "2021-01-01,A1,10,0.1\n"
        "2021-01-01,A2,9,0.1\n",
        encoding="utf-8",
    )
    panel_b.write_text(
        "trade_date,code,dividend_yield,volatility_120d\n"
        "2021-01-01,B1,8,0.1\n"
        "2021-01-01,B2,7,0.1\n",
        encoding="utf-8",
    )
    config = {
        "project": "test_short",
        "sectors": [
            {"sector_id": "a", "strategy_id": "sa", "panel_csv": str(panel_a)},
            {"sector_id": "b", "strategy_id": "sb", "panel_csv": str(panel_b)},
        ],
        "signals": {
            "factors": [{"name": "dividend_yield", "direction": "higher_is_better"}],
            "scoring": {"method": "weighted_composite", "min_factor_count": 1, "weights": {"dividend_yield": 1}},
        },
        "portfolio": {"target_count": 6, "sector_weight_cap": 0.35, "single_stock_weight_cap": 0.2},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    result = construct_dividend_low_vol_fcf_basket(config_path, tmp_path / "out")

    rows = result.signals_path.read_text(encoding="utf-8").splitlines()
    weights = [float(line.split(",")[6]) for line in rows[1:] if line]
    assert sum(weights) < 1.0
    assert max(weights) <= 0.2


def test_basket_constructor_marks_initial_rebalance_event_when_startup_fields_available(tmp_path: Path) -> None:
    panel = tmp_path / "panel.csv"
    panel.write_text(
        "trade_date,code,dividend_yield,low_vol_score,volatility_120d,max_drawdown_120d,operating_cash_flow_yield\n"
        "2021-01-04,A,1,1,0.1,0.1,3\n"
        "2021-01-04,B,1,1,0.1,0.1,2\n"
        "2021-01-04,C,1,1,0.1,0.1,1\n"
        "2021-04-01,A,1,1,0.1,0.1,3\n"
        "2021-04-01,B,1,1,0.1,0.1,2\n"
        "2021-04-01,C,1,1,0.1,0.1,1\n",
        encoding="utf-8",
    )
    prices = tmp_path / "prices.csv"
    price_rows = ["date,code,open,close,high_limit,low_limit,paused"]
    start = date(2020, 1, 1)
    for i in range(280):
        day = start + timedelta(days=i)
        for code in ["A", "B", "C"]:
            price_rows.append(f"{day.isoformat()},{code},10,10,11,9,0")
    for code in ["A", "B", "C"]:
        price_rows.append(f"2021-01-04,{code},10,10,11,9,0")
    prices.write_text("\n".join(price_rows) + "\n", encoding="utf-8")
    config = {
        "project": "startup_test",
        "sectors": [{"sector_id": "a", "strategy_id": "sa", "panel_csv": str(panel), "price_csv": str(prices)}],
        "signals": {
            "factors": [{"name": "operating_cash_flow_yield", "direction": "higher_is_better"}],
            "scoring": {"method": "weighted_composite", "min_factor_count": 1, "weights": {"operating_cash_flow_yield": 1}},
        },
        "portfolio": {
            "start_date": "2021-01-01",
            "end_date": "2021-04-30",
            "required_fields": ["low_vol_score", "volatility_120d", "dividend_yield"],
            "target_count": 3,
            "sector_weight_cap": 1.0,
            "single_stock_weight_cap": 1.0,
        },
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    result = construct_dividend_low_vol_fcf_basket(config_path, tmp_path / "out")

    text = result.signals_path.read_text(encoding="utf-8")
    assert "initial_rebalance_event" in text
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert summary["startup_preload"]["initial_rebalance_event"] == "2021-01-04"

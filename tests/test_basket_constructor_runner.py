from __future__ import annotations

import json
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

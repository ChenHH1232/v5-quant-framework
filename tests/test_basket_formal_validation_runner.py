from __future__ import annotations

import json
from pathlib import Path

from v5.basket_formal_validation_runner import run_basket_formal_validation


def test_basket_formal_validation_writes_core_outputs(tmp_path: Path) -> None:
    panel = tmp_path / "panel.csv"
    panel.write_text(
        "trade_date,code,future_return,dividend_yield,operating_cash_flow_yield,free_cash_flow_yield,low_price_to_book,low_vol_score,volatility_120d,max_drawdown_120d,capex_burden,factor_visible_date,universe_visible_date\n"
        "2021-01-01,A,0.05,4,1,1,1,2,0.10,0.12,0.3,2020-12-31,2020-01-01\n"
        "2021-01-01,B,0.01,2,1,1,1,1,0.20,0.20,0.4,2020-12-31,2020-01-01\n"
        "2021-01-01,C,-0.01,1,1,1,1,0.5,0.30,0.30,0.5,2020-12-31,2020-01-01\n",
        encoding="utf-8",
    )
    signals = tmp_path / "signals.csv"
    signals.write_text(
        "trade_date,code,sector_id,target_weight,score,selected_count\n"
        "2021-01-01,A,s,0.5,1,2\n"
        "2021-01-01,B,s,0.5,0.5,2\n",
        encoding="utf-8",
    )
    daily = tmp_path / "daily.csv"
    daily.write_text(
        "trade_date,strategy_return,benchmark_return\n"
        "2021-01-01,0.01,0.005\n"
        "2021-01-04,0.02,0.004\n",
        encoding="utf-8",
    )
    config = {
        "project": "test_basket",
        "sectors": [{"sector_id": "s", "strategy_id": "x", "panel_csv": str(panel)}],
        "signals": {
            "factors": [
                {"name": "dividend_yield", "direction": "higher_is_better"},
                {"name": "volatility_120d", "direction": "lower_is_better"},
            ],
            "scoring": {"method": "weighted_composite", "min_factor_count": 1, "weights": {"dividend_yield": 1}},
        },
        "portfolio": {"start_date": "2021-01-01", "end_date": "2021-01-04", "required_fields": ["low_vol_score", "volatility_120d"]},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    result = run_basket_formal_validation(config_path, signals, daily, tmp_path / "out")

    assert result.panel_row_count == 3
    assert result.status in {"formal_validation_completed_not_acceptance", "needs_review"}
    assert (result.output_dir / "factor_ic_rankic.csv").exists()
    assert (result.output_dir / "rolling_validation.csv").exists()

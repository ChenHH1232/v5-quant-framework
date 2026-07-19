from __future__ import annotations

from v5.basket_ablation_runner import _build_cases


def test_basket_ablation_uses_short_case_ids_for_windows_paths() -> None:
    config = {
        "project": "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f",
        "signals": {
            "factors": [
                {"name": "operating_cash_flow_yield", "direction": "higher_is_better"},
                {"name": "volatility_120d", "direction": "lower_is_better"},
            ],
            "scoring": {
                "min_factor_count": 1,
                "weights": {"operating_cash_flow_yield": 1.0, "volatility_120d": 1.0},
            },
        },
        "portfolio": {"required_fields": ["operating_cash_flow_yield", "volatility_120d"]},
    }

    cases = dict(_build_cases(config))

    assert "drop_ocf_yield" in cases
    assert "drop_operating_cash_flow_yield" not in cases
    assert cases["drop_ocf_yield"]["governance"]["ablation_dropped_factor"] == "operating_cash_flow_yield"

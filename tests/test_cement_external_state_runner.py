from __future__ import annotations

import csv
import json
from pathlib import Path

from v5.cement_external_state_runner import build_cement_state_enriched_panel, run_cement_state_bucket_validation


def _write_csv(path: Path, rows: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_cement_state_enrichment_and_bucket_validation(tmp_path: Path) -> None:
    panel = _write_csv(
        tmp_path / "panel.csv",
        [
            {
                "trade_date": date,
                "code": code,
                "future_return": future_return,
                "total_return": future_return,
                "operating_cash_flow_yield": ocf,
                "low_vol_score": low_vol,
                "factor_visible_date": date,
            }
            for date, guard, returns in [
                ("2025-01-02", "true", [0.1, 0.05, -0.02]),
                ("2025-04-01", "false", [-0.04, 0.02, 0.01]),
            ]
            for code, future_return, ocf, low_vol in [
                ("000001.XSHE", returns[0], 0.3, 0.2),
                ("000002.XSHE", returns[1], 0.2, 0.3),
                ("000003.XSHE", returns[2], 0.1, 0.1),
            ]
        ],
    )
    state = _write_csv(
        tmp_path / "state.csv",
        [
            {
                "trade_date": "2025-01-02",
                "cement_price_proxy_date": "2024-12-31",
                "cement_price_proxy_value": "100",
                "cement_price_proxy_change_1y": "5",
                "real_estate_prosperity_date": "2024-11-01",
                "real_estate_prosperity_value": "95",
                "real_estate_prosperity_change_1y": "1",
                "fixed_asset_investment_date": "2024-11-01",
                "fixed_asset_investment_yoy": "3",
                "fixed_asset_investment_mom": "1",
                "commodity_price_date": "2024-11-01",
                "energy_cost_yoy": "-2",
                "mineral_product_yoy": "1",
                "cement_cycle_score": "0.4",
                "cement_cycle_guard_pass": "true",
            },
            {
                "trade_date": "2025-04-01",
                "cement_price_proxy_date": "2025-03-31",
                "cement_price_proxy_value": "90",
                "cement_price_proxy_change_1y": "-8",
                "real_estate_prosperity_date": "2025-02-01",
                "real_estate_prosperity_value": "91",
                "real_estate_prosperity_change_1y": "-3",
                "fixed_asset_investment_date": "2025-02-01",
                "fixed_asset_investment_yoy": "-5",
                "fixed_asset_investment_mom": "-1",
                "commodity_price_date": "2025-02-01",
                "energy_cost_yoy": "4",
                "mineral_product_yoy": "-2",
                "cement_cycle_score": "-0.5",
                "cement_cycle_guard_pass": "false",
            },
        ],
    )
    spec = _write_json(
        tmp_path / "spec.json",
        {
            "meta": {"strategy_id": "test_cement_state", "name": "Test Cement State", "objective": "test"},
            "universe": {"name": "test", "construction": "test", "point_in_time": True},
            "data": {"vendor": "test", "price_frequency": "quarterly", "financial_as_of_policy": "test"},
            "signals": {
                "factors": [
                    {
                        "name": "operating_cash_flow_yield",
                        "source": "test",
                        "direction": "higher_is_better",
                        "definition": "test",
                        "as_of": "test",
                        "disclosure_lag_days": 0,
                        "missing_policy": "drop_security",
                    },
                    {
                        "name": "low_vol_score",
                        "source": "test",
                        "direction": "higher_is_better",
                        "definition": "test",
                        "as_of": "test",
                        "disclosure_lag_days": 0,
                        "missing_policy": "drop_security",
                    },
                ],
                "scoring": {
                    "method": "weighted_composite",
                    "weights": {"operating_cash_flow_yield": 0.7, "low_vol_score": 0.3},
                    "min_factor_count": 2,
                },
            },
            "schedule": {"signal_frequency": "quarterly", "rebalance_frequency": "quarterly"},
            "portfolio": {"selection_count": 2, "weighting": "equal_weight", "max_position_weight": 0.5},
            "risk": {"defensive_asset": "cash", "defensive_rule": {"enabled": False}},
            "validation": {"method": "rolling", "train_years": 1, "test_years": 1},
            "execution": {"status": "not_started", "commission_bps": 0, "slippage_bps": 0, "suspension_policy": "skip", "limit_policy": "skip"},
            "outputs": {"save_holdings": True, "save_rebalance_signals": True, "report": "markdown"},
        },
    )

    enriched = build_cement_state_enriched_panel(panel, state, tmp_path / "enriched")
    rows = list(csv.DictReader(enriched.open("r", encoding="utf-8")))
    assert rows[0]["cement_cycle_guard_pass"] == "true"

    report = run_cement_state_bucket_validation(enriched, spec, tmp_path / "state_validation", "test_cement_state")
    summary = json.loads((report.parent / "cement_state_bucket_validation_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "state_bucket_validation_completed_not_acceptance"
    assert {row["bucket"] for row in summary["bucket_validation"]} == {"all", "cycle_guard_pass", "cycle_guard_fail"}

from __future__ import annotations

import json
from pathlib import Path

from v5.home_appliances_state_diagnostic_runner import run_home_appliances_state_diagnostic
from v5.home_appliances_state_gate_runner import build_home_appliances_state_gate


def test_home_appliances_state_gate_enriches_panel_with_dividends_and_external_state(tmp_path: Path) -> None:
    panel = tmp_path / "panel.csv"
    panel.write_text(
        "\n".join(
            [
                "trade_date,code,sub_industry,future_return,operating_cash_flow_yield,operating_cash_flow_to_net_profit,cash_collection_quality,capex_burden,asset_liability_ratio,low_vol_score,dividend_yield,factor_visible_date",
                "2021-07-01,000001.XSHE,white,0.10,0.05,1.2,0.8,0.2,0.4,-0.1,2.0,2021-06-30",
                "2021-07-01,000002.XSHE,white,0.02,0.02,0.9,0.7,1.2,0.5,-0.2,1.5,2021-06-30",
                "2021-07-01,000003.XSHE,kitchen,-0.01,-0.01,0.5,0.6,1.5,0.6,-0.3,0.5,2021-06-30",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    dividends = tmp_path / "dividends.csv"
    dividends.write_text(
        "\n".join(
            [
                "code,pay_date,net_cash_per_share",
                "000001.XSHE,2021-06-01,0.12",
                "000002.XSHE,2020-01-01,0.10",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    external = tmp_path / "external.csv"
    external.write_text(
        "\n".join(
            [
                "trade_date,visible_date,scope,sub_industry,metric,value,unit,source_name,pit_usable,review_status,notes",
                "2021-07-01,2021-06-15,official_proxy,,real_estate_climate_index,98.1,index,test,true,reviewed,",
                "2021-07-01,2021-06-20,official_proxy,,china_exports_yoy,10.0,percent,test,true,reviewed,",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = build_home_appliances_state_gate(panel, dividends, external, tmp_path / "out", strategy_id="test_home")

    assert result.status == "research_state_gate_proxy_repaired_needs_review"
    summary = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert summary["dividend_event_count"] == 2
    enriched = result.enriched_panel_csv.read_text(encoding="utf-8")
    assert "code_net_cash_per_share_trailing_365d" in enriched
    assert "external_real_estate_climate_index" in enriched
    assert "0.12" in enriched


def test_home_appliances_state_diagnostic_outputs_bucket_summary(tmp_path: Path) -> None:
    panel = tmp_path / "panel.csv"
    header = (
        "trade_date,code,future_return,operating_cash_flow_yield,operating_cash_flow_to_net_profit,"
        "factor_visible_date,external_china_exports_yoy,sector_capex_burden_median"
    )
    rows = [header]
    dates = ["2021-01-01", "2021-04-01", "2021-07-01", "2021-10-01", "2022-01-01"]
    for date_index, trade_date in enumerate(dates):
        for code_index in range(3):
            rows.append(
                ",".join(
                    [
                        trade_date,
                        f"00000{code_index + 1}.XSHE",
                        str(0.01 * (code_index + 1)),
                        str(0.02 * (code_index + 1)),
                        str(1.0 + code_index),
                        trade_date,
                        str(date_index),
                        str(0.5 + date_index),
                    ]
                )
            )
    panel.write_text("\n".join(rows) + "\n", encoding="utf-8")
    spec = tmp_path / "spec.json"
    spec.write_text(
        json.dumps(
            {
                "meta": {"strategy_id": "test_home_state", "name": "Test Home State", "objective": "Test state diagnostic."},
                "universe": {"name": "test", "construction": "test", "point_in_time": True},
                "data": {"vendor": "test", "price_frequency": "quarterly", "financial_as_of_policy": "test"},
                "signals": {
                    "factors": [
                        {
                            "name": "operating_cash_flow_yield",
                            "direction": "higher_is_better",
                            "source": "test",
                            "definition": "test",
                            "as_of": "trade_date",
                            "disclosure_lag_days": 1,
                            "missing_policy": "drop_security",
                        },
                        {
                            "name": "operating_cash_flow_to_net_profit",
                            "direction": "higher_is_better",
                            "source": "test",
                            "definition": "test",
                            "as_of": "trade_date",
                            "disclosure_lag_days": 1,
                            "missing_policy": "drop_security",
                        },
                    ],
                    "scoring": {
                        "method": "weighted_composite",
                        "weights": {"operating_cash_flow_yield": 0.7, "operating_cash_flow_to_net_profit": 0.3},
                        "min_factor_count": 2,
                    },
                },
                "schedule": {"signal_frequency": "quarterly", "rebalance_frequency": "quarterly"},
                "portfolio": {"selection_count": 2, "weighting": "equal_weight", "max_position_weight": 0.5},
                "risk": {"defensive_asset": "cash", "defensive_rule": {"enabled": False}},
                "validation": {"method": "rolling", "train_years": 1, "test_years": 1},
                "execution": {"commission_bps": 3, "slippage_bps": 5, "suspension_policy": "skip", "limit_policy": "skip"},
                "outputs": {"save_holdings": True, "save_rebalance_signals": True, "report": "markdown"},
            }
        ),
        encoding="utf-8",
    )

    result = run_home_appliances_state_diagnostic(spec, panel, tmp_path / "out", strategy_id="test_home_state", min_history=1)

    assert result.status == "state_diagnostic_completed_not_engineering_handoff"
    assert "external_china_exports_yoy" in result.bucket_csv.read_text(encoding="utf-8")

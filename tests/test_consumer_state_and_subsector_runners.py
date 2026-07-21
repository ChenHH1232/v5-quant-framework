from __future__ import annotations

from pathlib import Path

from v5.consumer_subsector_validation_runner import run_consumer_subsector_validation
from v5.consumer_working_capital_state_runner import _derive_fields


def test_consumer_working_capital_derive_fields() -> None:
    fields = _derive_fields(
        {
            "inventories": 20,
            "account_receivable": 10,
            "bill_receivable": 5,
            "contract_assets": 2,
            "contract_liability": 7,
            "operating_revenue": 100,
            "operating_cost": 60,
            "total_current_assets": 80,
            "total_current_liability": 40,
        },
        "2025-01-02",
    )

    assert fields["inventory_to_revenue"] == "0.2"
    assert fields["receivables_to_revenue"] == "0.15"
    assert fields["working_capital_pressure_to_revenue"] == "0.3"
    assert fields["gross_margin"] == "0.4"
    assert fields["current_ratio"] == "2"


def test_consumer_subsector_validation_routes_subindustry(tmp_path: Path) -> None:
    panel = tmp_path / "panel.csv"
    header = [
        "trade_date",
        "code",
        "sub_industry",
        "future_return",
        "operating_cash_flow_yield",
        "operating_cash_flow_to_net_profit",
        "factor_visible_date",
    ]
    dates = [f"202{year}-01-02" for year in range(1, 7)] + [f"202{year}-07-01" for year in range(1, 7)]
    rows = [",".join(header)]
    for date_index, trade_date in enumerate(sorted(dates)):
        for code_index in range(9):
            strength = code_index + 1
            future_return = 0.01 * strength
            rows.append(
                ",".join(
                    [
                        trade_date,
                        f"0000{code_index + 1:02d}.XSHE",
                        "test_food",
                        str(future_return),
                        str(0.01 * strength),
                        str(0.5 + strength),
                        trade_date,
                    ]
                )
            )
    panel.write_text("\n".join(rows) + "\n", encoding="utf-8")

    result = run_consumer_subsector_validation("food_beverage", panel, tmp_path / "out", min_codes_per_date=8)

    assert result.status == "subsector_research_signal_found_not_engineering_handoff"
    text = result.result_csv.read_text(encoding="utf-8")
    assert "test_food" in text
    assert "research_signal_candidate_needs_state_review" in text


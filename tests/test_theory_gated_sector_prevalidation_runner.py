from __future__ import annotations

import json
from pathlib import Path

from v5.theory_gated_sector_prevalidation_runner import run_theory_gated_sector_prevalidation


def test_theory_gated_sector_prevalidation_routes_core_research_blocked_and_excluded(tmp_path: Path) -> None:
    source_config = tmp_path / "source_sectors.json"
    config = tmp_path / "v5a3.json"
    registry = tmp_path / "status_registry.json"

    source_config.write_text(
        json.dumps(
            {
                "candidate_sectors": [
                    {
                        "sector_id": "bank",
                        "display_name": "Bank",
                        "sector_type": "financial_stable_cash_flow",
                        "basket_role": "core_candidate",
                        "strategy_ids": ["bank_v1"],
                        "data_gate": "passed",
                        "pit_universe_gate": "passed",
                        "business_purity_gate": "passed",
                        "dividend_gate": "passed",
                        "fcf_gate": "not_primary",
                        "low_vol_gate": "passed",
                        "external_state_burden": "medium",
                        "sample_size_risk": "medium",
                        "notes": "core",
                    },
                    {
                        "sector_id": "coal",
                        "display_name": "Coal",
                        "sector_type": "cyclical",
                        "basket_role": "blocked",
                        "strategy_ids": [],
                        "data_gate": "blocked",
                        "pit_universe_gate": "needs_review",
                        "business_purity_gate": "incomplete",
                        "dividend_gate": "likely_pass",
                        "fcf_gate": "capex_policy_required",
                        "low_vol_gate": "can_build_from_daily_prices",
                        "external_state_burden": "high",
                        "sample_size_risk": "medium",
                        "notes": "cycle",
                    },
                    {
                        "sector_id": "consumer_staples_cashflow",
                        "display_name": "Consumer Staples",
                        "sector_type": "non_regulated_stable_cash_flow",
                        "basket_role": "watchlist_candidate",
                        "strategy_ids": [],
                        "data_gate": "needs_manual_research",
                        "pit_universe_gate": "needs_business_quality_screen",
                        "business_purity_gate": "needs_review",
                        "dividend_gate": "mixed",
                        "fcf_gate": "potentially_usable_after_working_capital_review",
                        "low_vol_gate": "can_build_from_daily_prices",
                        "external_state_burden": "medium",
                        "sample_size_risk": "medium",
                        "notes": "consumer",
                    },
                    {
                        "sector_id": "computer_software",
                        "display_name": "Computer / Software",
                        "sector_type": "growth_intangible",
                        "basket_role": "excluded",
                        "strategy_ids": [],
                        "data_gate": "excluded_by_business_model",
                        "pit_universe_gate": "can_build",
                        "business_purity_gate": "needs_review",
                        "dividend_gate": "weak",
                        "fcf_gate": "not_comparable",
                        "low_vol_gate": "can_build_from_daily_prices",
                        "external_state_burden": "medium",
                        "sample_size_risk": "medium",
                        "notes": "excluded",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    config.write_text(
        json.dumps(
            {
                "project": "test_v5a3",
                "experiment_layer": "research_pit_prevalidation",
                "source_sector_config": str(source_config),
                "candidate_sectors": [],
            }
        ),
        encoding="utf-8",
    )
    registry.write_text(
        json.dumps(
            {
                "strategies": [
                    {
                        "strategy_id": "bank_v1",
                        "current_status": ["formal_strategy_candidate", "platform_replication_passed"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = run_theory_gated_sector_prevalidation(config, registry, tmp_path / "out")

    assert result.sector_count == 4
    assert result.decision_counts["passed_prevalidation_shadow_basket_refresh"] == 1
    assert result.decision_counts["blocked_by_cycle_data_gate_before_initial_validation"] == 1
    assert result.decision_counts["research_gate_before_quant_initial_validation"] == 1
    assert result.decision_counts["excluded_before_initial_validation"] == 1
    report = result.report_path.read_text(encoding="utf-8")
    assert "OCF" in report
    csv_text = result.csv_path.read_text(encoding="utf-8")
    assert "sector_specific_value_and_balance_sheet_quality" in csv_text
    assert "cash_flow_quality_and_defensive_demand" in csv_text


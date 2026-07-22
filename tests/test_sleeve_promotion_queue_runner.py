from __future__ import annotations

import csv
import json
from pathlib import Path

from v5.sleeve_promotion_queue_runner import build_sleeve_promotion_queue


def test_sleeve_promotion_queue_ranks_by_cost_and_fit_not_returns(tmp_path: Path) -> None:
    sleeve_registry = tmp_path / "sleeve_registry.csv"
    fieldnames = [
        "sector_id",
        "display_name",
        "production_lane",
        "data_gate",
        "external_state_burden",
        "sample_size_risk",
        "panel_exists",
        "price_exists",
        "dividend_exists",
    ]
    with sleeve_registry.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "sector_id": "gas_water_operators",
                "display_name": "Gas / Water",
                "production_lane": "observation_refresh_only",
                "data_gate": "needs_manual_research",
                "external_state_burden": "medium",
                "sample_size_risk": "medium",
                "panel_exists": "no",
                "price_exists": "no",
                "dividend_exists": "no",
            }
        )
        writer.writerow(
            {
                "sector_id": "insurance",
                "display_name": "Insurance",
                "production_lane": "observation_refresh_only",
                "data_gate": "specialist_data_partial",
                "external_state_burden": "high",
                "sample_size_risk": "high",
                "panel_exists": "no",
                "price_exists": "no",
                "dividend_exists": "no",
            }
        )
        writer.writerow(
            {
                "sector_id": "home_appliances",
                "display_name": "Home Appliances",
                "production_lane": "research_repair_queue",
                "data_gate": "needs_manual_research",
                "external_state_burden": "medium",
                "sample_size_risk": "medium",
                "panel_exists": "no",
                "price_exists": "no",
                "dividend_exists": "no",
            }
        )

    status_registry = tmp_path / "status_registry.json"
    status_registry.write_text(
        json.dumps(
            {
                "strategies": [
                    {
                        "strategy_id": "gas_water_v57b_text_debt_state_guard_v59b",
                        "sector": "gas_water_operators",
                        "current_status": [
                            "formal_state_guard_candidate",
                            "engineering_local_daily_simulation_passed",
                            "paper_trading_preparation_started",
                            "rebalance_order_health_passed",
                        ],
                        "evidence_paths": [
                            "data/processed/gas_water/panel_with_low_vol.csv",
                            "data/processed/gas_water/cash_dividends.csv",
                            "local_daily_backtests_v59b_gas_water/summary.json",
                            "local_daily_backtests_v59b_gas_water/rebalance_order_health.csv",
                        ],
                        "blockers": ["wait for next clean forward signal"],
                    },
                    {
                        "strategy_id": "insurance_pev_value_v53g",
                        "sector": "insurance",
                        "current_status": ["paper_trading_started"],
                        "evidence_paths": [
                            "insurance_ev_nbv_panel/panel.csv",
                            "local_daily_backtests_insurance/summary.json",
                            "insurance_cash_dividends.csv",
                        ],
                        "blockers": ["Only five names; EV / NBV specialist data required."],
                    },
                    {
                        "strategy_id": "home_appliances_ocf_quality_v5a5d",
                        "sector": "home_appliances",
                        "current_status": ["research_pit_validation_completed", "cash_dividend_events_collected"],
                        "evidence_paths": [
                            "data/processed/home_appliances/panel_with_low_vol.csv",
                            "home_appliances_cash_dividend_events.csv",
                        ],
                        "blockers": ["Engineering local daily simulation is blocked until reviewed state policy."],
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = build_sleeve_promotion_queue(
        sleeve_registry=sleeve_registry,
        status_registry=status_registry,
        out_dir=tmp_path / "out",
        candidate_ids=["gas_water_operators", "insurance", "home_appliances"],
    )

    rows = list(csv.DictReader(result.queue_csv.open("r", encoding="utf-8")))
    assert [row["sector_id"] for row in rows] == ["gas_water_operators", "home_appliances", "insurance"]
    assert rows[0]["recommended_next_owner"] == "Engineering Agent"
    assert rows[0]["can_promote_to_v57f"] == "no"
    assert rows[1]["missing_local_daily_simulation"] == "yes"
    assert rows[2]["sample_size_too_small"] == "yes"

    agent_queue = list(csv.DictReader(result.selected_agent_queue_csv.open("r", encoding="utf-8")))
    assert len(agent_queue) == 1
    assert agent_queue[0]["sector_id"] == "gas_water_operators"
    assert "do_not_modify_V57f" in agent_queue[0]["blocked_actions"]

    report = result.report_path.read_text(encoding="utf-8")
    assert "Historical performance alone" in report
    assert "Only the first-ranked candidate" in report


def test_sleeve_promotion_queue_routes_engineering_passed_sleeve_to_paper_tracking(tmp_path: Path) -> None:
    sleeve_registry = tmp_path / "sleeve_registry.csv"
    fieldnames = [
        "sector_id",
        "display_name",
        "production_lane",
        "data_gate",
        "external_state_burden",
        "sample_size_risk",
        "panel_exists",
        "dividend_exists",
    ]
    with sleeve_registry.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "sector_id": "home_appliances",
                "display_name": "Home Appliances",
                "production_lane": "research_repair_queue",
                "data_gate": "needs_specialist_review",
                "external_state_burden": "medium",
                "sample_size_risk": "medium",
                "panel_exists": "yes",
                "dividend_exists": "yes",
            }
        )

    status_registry = tmp_path / "status_registry.json"
    status_registry.write_text(
        json.dumps(
            {
                "strategies": [
                    {
                        "strategy_id": "home_appliances_ocf_quality_v5a5e_engineering_handoff",
                        "sector": "home_appliances",
                        "current_status": [
                            "engineering_local_daily_simulation_passed",
                            "rebalance_order_health_passed",
                            "observation_candidate_not_v57f_sleeve",
                        ],
                        "evidence_paths": [
                            "local_daily_backtests_home_appliances/summary.json",
                            "local_daily_backtests_home_appliances/rebalance_order_health.csv",
                            "data/processed/home_appliances/panel_with_low_vol.csv",
                            "home_appliances_cash_dividends.csv",
                        ],
                        "blockers": [
                            "PM must separately approve any observation-basket or paper-trading route.",
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = build_sleeve_promotion_queue(
        sleeve_registry=sleeve_registry,
        status_registry=status_registry,
        out_dir=tmp_path / "out",
        candidate_ids=["home_appliances"],
    )

    rows = list(csv.DictReader(result.queue_csv.open("r", encoding="utf-8")))
    assert rows[0]["recommended_next_owner"] == "Engineering Agent"
    assert rows[0]["promotion_lane"] == "observation_paper_tracking"
    assert rows[0]["pm_gate"] == "paper_tracking_only_no_core_inclusion"
    assert rows[0]["specialist_data_required"] == "no"


def test_sleeve_promotion_queue_routes_food_beverage_handoff_to_local_daily_engineering(tmp_path: Path) -> None:
    sleeve_registry = tmp_path / "sleeve_registry.csv"
    fieldnames = [
        "sector_id",
        "display_name",
        "production_lane",
        "data_gate",
        "external_state_burden",
        "sample_size_risk",
        "panel_exists",
        "dividend_exists",
    ]
    with sleeve_registry.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "sector_id": "food_beverage",
                "display_name": "Food / Beverage",
                "production_lane": "research_repair_queue",
                "data_gate": "needs_manual_research",
                "external_state_burden": "medium",
                "sample_size_risk": "medium",
                "panel_exists": "yes",
                "dividend_exists": "yes",
            }
        )

    status_registry = tmp_path / "status_registry.json"
    status_registry.write_text(
        json.dumps(
            {
                "strategies": [
                    {
                        "strategy_id": "food_beverage_packaged_food_ocf_quality_v5a9a",
                        "sector": "food_beverage",
                        "current_status": [
                            "research_pit_validation_completed",
                            "food_beverage_engineering_handoff_ready",
                        ],
                        "evidence_paths": [
                            "validation_formal_v5a9_food_beverage_research_repair/panels/food_beverage_packaged_food_ocf_quality_v5a9a.csv",
                            "food_beverage_cash_dividends.csv",
                            "low_volatility_factors/food_beverage/panel_with_low_vol.csv",
                        ],
                        "blockers": [
                            "Engineering has not yet run local daily simulation and rebalance_order_health.",
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = build_sleeve_promotion_queue(
        sleeve_registry=sleeve_registry,
        status_registry=status_registry,
        out_dir=tmp_path / "out",
        candidate_ids=["food_beverage"],
    )

    rows = list(csv.DictReader(result.queue_csv.open("r", encoding="utf-8")))
    assert rows[0]["recommended_next_owner"] == "Engineering Agent"
    assert rows[0]["promotion_lane"] == "engineering_smoke_test_candidate"
    assert rows[0]["pm_gate"] == "local_daily_engineering_gate"
    assert rows[0]["specialist_data_required"] == "no"


def test_sleeve_promotion_queue_routes_food_beverage_engineering_needs_review_to_pm(tmp_path: Path) -> None:
    sleeve_registry = tmp_path / "sleeve_registry.csv"
    fieldnames = [
        "sector_id",
        "display_name",
        "production_lane",
        "data_gate",
        "external_state_burden",
        "sample_size_risk",
        "panel_exists",
        "dividend_exists",
    ]
    with sleeve_registry.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "sector_id": "food_beverage",
                "display_name": "Food / Beverage",
                "production_lane": "research_repair_queue",
                "data_gate": "needs_manual_research",
                "external_state_burden": "medium",
                "sample_size_risk": "medium",
                "panel_exists": "yes",
                "dividend_exists": "yes",
            }
        )

    status_registry = tmp_path / "status_registry.json"
    status_registry.write_text(
        json.dumps(
            {
                "strategies": [
                    {
                        "strategy_id": "food_beverage_packaged_food_ocf_quality_v5a9a",
                        "sector": "food_beverage",
                        "current_status": [
                            "research_pit_validation_completed",
                            "food_beverage_engineering_handoff_ready",
                            "engineering_local_daily_simulation_completed",
                            "engineering_local_daily_simulation_needs_review",
                        ],
                        "evidence_paths": [
                            "validation_formal_v5a9_food_beverage_research_repair/panels/food_beverage_packaged_food_ocf_quality_v5a9a.csv",
                            "food_beverage_cash_dividends.csv",
                            "low_volatility_factors/food_beverage/panel_with_low_vol.csv",
                            "local_daily_backtests_food_beverage/summary.json",
                            "local_daily_backtests_food_beverage/rebalance_order_health.csv",
                        ],
                        "blockers": [
                            "Partial price-limit skipped orders require PM review.",
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = build_sleeve_promotion_queue(
        sleeve_registry=sleeve_registry,
        status_registry=status_registry,
        out_dir=tmp_path / "out",
        candidate_ids=["food_beverage"],
    )

    rows = list(csv.DictReader(result.queue_csv.open("r", encoding="utf-8")))
    assert rows[0]["recommended_next_owner"] == "Project Manager Agent"
    assert rows[0]["promotion_lane"] == "engineering_needs_review"
    assert rows[0]["pm_gate"] == "rebalance_order_health_review_gate"
    assert rows[0]["missing_local_daily_simulation"] == "no"
    assert rows[0]["missing_rebalance_order_health"] == "no"

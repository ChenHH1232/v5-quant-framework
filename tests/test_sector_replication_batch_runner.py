from __future__ import annotations

import json
from pathlib import Path

from v5.sector_replication_batch_runner import run_sector_replication_batch


def test_run_sector_replication_batch_routes_all_lanes(tmp_path: Path) -> None:
    sector_config = tmp_path / "sectors.json"
    registry = tmp_path / "status_registry.json"
    roadmap_config = tmp_path / "roadmap.json"

    sector_config.write_text(
        json.dumps(
            {
                "project": "test_sector_batch",
                "experiment_layer": "data_availability_gate",
                "candidate_sectors": [
                    {
                        "sector_id": "bank",
                        "display_name": "Bank",
                        "sector_type": "financial_stable_cash_flow",
                        "basket_role": "core_candidate",
                        "strategy_ids": ["bank_v1"],
                        "knowledge_artifacts": [],
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
                        "sector_id": "consumer_staples_cashflow",
                        "display_name": "Consumer",
                        "sector_type": "stable_cash_flow",
                        "basket_role": "watchlist_candidate",
                        "strategy_ids": [],
                        "knowledge_artifacts": [],
                        "data_gate": "needs_manual_research",
                        "pit_universe_gate": "needs_review",
                        "business_purity_gate": "needs_review",
                        "dividend_gate": "mixed",
                        "fcf_gate": "needs_review",
                        "low_vol_gate": "can_build",
                        "external_state_burden": "medium",
                        "sample_size_risk": "medium",
                        "notes": "research",
                    },
                    {
                        "sector_id": "coal",
                        "display_name": "Coal",
                        "sector_type": "cyclical",
                        "basket_role": "blocked",
                        "strategy_ids": [],
                        "knowledge_artifacts": [],
                        "data_gate": "blocked",
                        "pit_universe_gate": "needs_review",
                        "business_purity_gate": "incomplete",
                        "dividend_gate": "likely",
                        "fcf_gate": "capex",
                        "low_vol_gate": "can_build",
                        "external_state_burden": "high",
                        "sample_size_risk": "medium",
                        "notes": "blocked",
                    },
                ],
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
                        "current_status": ["formal_strategy_candidate", "paper_trading_started"],
                        "blockers": [],
                        "next_gate": "paper_trading",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    roadmap_config.write_text(
        json.dumps(
            {
                "project": "test_roadmap",
                "experiment_layer": "pm_decision_gate",
                "source_sector_config": str(sector_config),
                "source_screening_results": str(tmp_path / "old.csv"),
                "source_screening_summary": str(tmp_path / "old.json"),
                "objective": "test",
                "timebox_policy": {"default_minutes": 30, "deep_research_minutes": 60, "stop_after_no_new_evidence_loops": 2},
                "lane_policy": {
                    "basket_core_shadow_pool": {
                        "next_agent": "Engineering Agent",
                        "loop_type": "refresh",
                        "timebox_minutes": 30,
                        "required_packet": "checkpoint_packet",
                        "allowed_next_action": "refresh only",
                        "forbidden_action": "do not tune",
                    },
                    "manual_research_before_formal": {
                        "next_agent": "Research Agent",
                        "loop_type": "research",
                        "timebox_minutes": 60,
                        "required_packet": "checkpoint_packet",
                        "allowed_next_action": "repair",
                        "forbidden_action": "no modeling",
                    },
                    "blocked_data_repair": {
                        "next_agent": "Research Agent",
                        "loop_type": "blocker",
                        "timebox_minutes": 60,
                        "required_packet": "blocker_packet",
                        "allowed_next_action": "repair data",
                        "forbidden_action": "no backtest",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    result = run_sector_replication_batch(
        screen_config=sector_config,
        roadmap_config=roadmap_config,
        status_registry=registry,
        out_dir=tmp_path / "batch",
    )

    assert result.sector_count == 3
    assert result.lane_counts["basket_core_shadow_pool"] == 1
    assert result.lane_counts["manual_research_before_formal"] == 1
    assert result.lane_counts["blocked_data_repair"] == 1
    packet = json.loads(result.packet_path.read_text(encoding="utf-8"))
    assert packet["status"] == "batch_sector_replication_routed_not_model_acceptance"
    assert len(packet["next_execution_order"]) == 3
    assert "Agent" in result.report_path.read_text(encoding="utf-8")

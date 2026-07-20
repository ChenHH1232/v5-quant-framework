from __future__ import annotations

import json
from pathlib import Path

from v5.dividend_low_vol_fcf_screener_runner import run_dividend_low_vol_fcf_batch_screening


def test_dividend_low_vol_fcf_batch_screening_classifies_candidates(tmp_path: Path) -> None:
    artifact = tmp_path / "knowledge.md"
    artifact.write_text("ok\n", encoding="utf-8")
    config = {
        "project": "test",
        "experiment_layer": "data_availability_gate",
        "global_missing_modules": ["low_volatility_factor_runner"],
        "candidate_sectors": [
            {
                "sector_id": "stable",
                "display_name": "Stable",
                "sector_type": "stable_cash_flow",
                "basket_role": "core_candidate",
                "strategy_ids": ["stable_strategy"],
                "knowledge_artifacts": [str(artifact)],
                "data_gate": "passed",
                "pit_universe_gate": "passed",
                "business_purity_gate": "passed",
                "dividend_gate": "passed",
                "fcf_gate": "usable",
                "low_vol_gate": "pending_global_module",
                "external_state_burden": "low",
                "sample_size_risk": "medium",
                "notes": "stable note",
            },
            {
                "sector_id": "cycle",
                "display_name": "Cycle",
                "sector_type": "cyclical",
                "basket_role": "blocked_observation_pool",
                "strategy_ids": ["cycle_strategy"],
                "knowledge_artifacts": [],
                "data_gate": "blocked",
                "pit_universe_gate": "needs_repair",
                "business_purity_gate": "incomplete",
                "dividend_gate": "likely_pass",
                "fcf_gate": "capex_policy_required",
                "low_vol_gate": "pending_global_module",
                "external_state_burden": "high",
                "sample_size_risk": "medium",
                "notes": "cycle note",
            },
            {
                "sector_id": "failed",
                "display_name": "Failed",
                "sector_type": "stable_cash_flow",
                "basket_role": "archived",
                "strategy_ids": [],
                "knowledge_artifacts": [],
                "data_gate": "strategy_candidate_failed",
                "pit_universe_gate": "passed",
                "business_purity_gate": "passed",
                "dividend_gate": "mixed",
                "fcf_gate": "failed",
                "low_vol_gate": "can_build",
                "external_state_burden": "medium",
                "sample_size_risk": "medium",
                "notes": "failed note",
            },
            {
                "sector_id": "platform_pending",
                "display_name": "Platform Pending",
                "sector_type": "cycle_aware_cash_flow",
                "basket_role": "platform_pending",
                "strategy_ids": [],
                "knowledge_artifacts": [],
                "data_gate": "platform_replication_pending_exports",
                "pit_universe_gate": "passed",
                "business_purity_gate": "needs_review",
                "dividend_gate": "passed",
                "fcf_gate": "needs_review",
                "low_vol_gate": "passed",
                "external_state_burden": "high",
                "sample_size_risk": "medium",
                "notes": "pending note",
            },
        ],
    }
    registry = {
        "strategies": [
            {
                "strategy_id": "stable_strategy",
                "current_status": ["formal_strategy_candidate"],
                "blockers": [],
                "next_gate": "paper_trading",
            },
            {
                "strategy_id": "cycle_strategy",
                "current_status": ["blocked_by_manual_research_data"],
                "blockers": ["missing cycle state"],
                "next_gate": "data_repair",
            },
        ]
    }
    config_path = tmp_path / "config.json"
    registry_path = tmp_path / "status.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    result = run_dividend_low_vol_fcf_batch_screening(config_path, registry_path, tmp_path / "out")

    assert result.sector_count == 4
    assert result.core_candidate_count == 1
    assert result.blocked_count == 1
    report = result.report_path.read_text(encoding="utf-8")
    assert "ready_for_basket_shadow_pool" in report
    assert "blocked_by_cycle_data_gate" in report
    assert "archived_strategy_candidate_failed" in report
    assert "platform_replication_pending_before_basket" in report

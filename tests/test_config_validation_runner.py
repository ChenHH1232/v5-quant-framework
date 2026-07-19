from __future__ import annotations

import json
from pathlib import Path

from v5.config_validation_runner import detect_config_type, validate_config_file


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_validate_detects_basket_runtime_config(tmp_path: Path) -> None:
    path = _write_json(
        tmp_path / "basket.json",
        {
            "schema_version": 1,
            "project": "basket_test",
            "sectors": [
                {
                    "sector_id": "utilities",
                    "strategy_id": "utilities_test",
                    "panel_csv": "panel.csv",
                    "price_csv": "prices.csv",
                    "dividend_csv": "dividends.csv",
                }
            ],
            "signals": {"factors": [{"name": "ocf_yield", "direction": "higher_is_better"}], "scoring": {"method": "weighted_composite"}},
            "portfolio": {"target_count": 10},
        },
    )

    result = validate_config_file(path)

    assert result["config_type"] == "basket_runtime_config"
    assert result["audit"]["passed"] is True


def test_validate_detects_research_candidate_without_legacy_schedule(tmp_path: Path) -> None:
    path = _write_json(
        tmp_path / "candidate.json",
        {
            "meta": {"strategy_id": "candidate", "name": "Candidate", "objective": "Test a candidate."},
            "signals": {"factors": [{"name": "low_vol", "direction": "lower_is_better", "as_of": "trade_date_lagged"}], "scoring": {"method": "weighted_composite"}},
            "portfolio": {"selection_count": 5},
            "validation": {"method": "rolling"},
            "execution": {"status": "pending"},
        },
    )

    result = validate_config_file(path)

    assert result["config_type"] == "research_candidate_spec"
    assert result["audit"]["passed"] is True
    assert any(issue["code"] == "FINANCIAL_AS_OF_POLICY_MISSING" for issue in result["audit"]["issues"])


def test_detects_agent_operating_protocol() -> None:
    raw = {
        "protocol_id": "agent_operating_protocol_v1",
        "default_timebox_minutes": 30,
        "action_classes": {},
        "stop_rules": [],
        "allowed_pm_decisions": [],
    }

    assert detect_config_type(raw) == "agent_operating_protocol"


def test_validate_detects_sector_screening_config(tmp_path: Path) -> None:
    path = _write_json(
        tmp_path / "screening.json",
        {
            "schema_version": 1,
            "project": "sector_screen",
            "experiment_layer": "data_availability_gate",
            "candidate_sectors": [
                {
                    "sector_id": "utilities",
                    "display_name": "Utilities",
                    "basket_role": "core_candidate",
                    "data_gate": "passed",
                    "pit_universe_gate": "passed",
                    "business_purity_gate": "passed",
                    "dividend_gate": "passed",
                    "fcf_gate": "support",
                    "low_vol_gate": "passed",
                }
            ],
        },
    )

    result = validate_config_file(path)

    assert result["config_type"] == "sector_screening_config"
    assert result["audit"]["passed"] is True


def test_validate_detects_sector_replication_roadmap_config(tmp_path: Path) -> None:
    path = _write_json(
        tmp_path / "roadmap.json",
        {
            "schema_version": 1,
            "project": "sector_roadmap",
            "experiment_layer": "pm_decision_gate",
            "source_sector_config": "config/source.json",
            "timebox_policy": {"default_minutes": 30},
            "lane_policy": {
                "core": {
                    "next_agent": "Engineering Agent",
                    "timebox_minutes": 30,
                    "required_packet": "checkpoint_packet",
                    "allowed_next_action": "refresh",
                    "forbidden_action": "tune",
                }
            },
        },
    )

    result = validate_config_file(path)

    assert result["config_type"] == "sector_replication_roadmap_config"
    assert result["audit"]["passed"] is True

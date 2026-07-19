from __future__ import annotations

import json
from pathlib import Path

from v5.strategy_state_gate_runner import run_strategy_state_gate


def _write_registry(path: Path, strategies: list[dict]) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "updated_at": "2026-07-20",
                "governance_rule": "Evidence first.",
                "strategies": strategies,
            }
        ),
        encoding="utf-8",
    )
    return path


def _strategy(**overrides: object) -> dict:
    base = {
        "strategy_id": "candidate",
        "sector": "utilities",
        "current_status": ["formal_strategy_candidate"],
        "not_status": ["accepted_strategy", "platform_replication_passed"],
        "experiment_layer": "research_pit_validation",
        "evidence_paths": ["docs/governance/candidate_formal_validation_pm_decision_v1.md"],
        "blockers": [],
        "next_gate": "platform_replication",
    }
    base.update(overrides)
    return base


def test_state_gate_reports_already_has_status(tmp_path: Path) -> None:
    registry = _write_registry(tmp_path / "registry.json", [_strategy(current_status=["formal_strategy_candidate", "platform_replication_passed"])])

    result = run_strategy_state_gate(
        strategy_id="candidate",
        target_status="platform_replication_passed",
        registry_path=registry,
        out_dir=tmp_path / "out",
    )

    assert result.status == "already_has_status"
    assert result.blocker_count == 0
    assert result.user_decision_required is False


def test_state_gate_blocks_accepted_strategy_without_platform_and_paper(tmp_path: Path) -> None:
    registry = _write_registry(tmp_path / "registry.json", [_strategy()])

    result = run_strategy_state_gate(
        strategy_id="candidate",
        target_status="accepted_strategy",
        registry_path=registry,
        out_dir=tmp_path / "out",
    )

    assert result.status == "blocked"
    assert result.blocker_count > 0


def test_state_gate_requires_user_stage_gate_when_platform_evidence_is_ready(tmp_path: Path) -> None:
    registry = _write_registry(tmp_path / "registry.json", [_strategy()])

    result = run_strategy_state_gate(
        strategy_id="candidate",
        target_status="platform_replication_passed",
        registry_path=registry,
        out_dir=tmp_path / "out",
        proposed_evidence=["platform_replication_packets/candidate/platform_replication_packet.json"],
    )

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert result.status == "ready_for_user_stage_gate"
    assert result.blocker_count == 0
    assert result.user_decision_required is True
    assert summary["blocked_actions"] == ["auto_mark_platform_replication_passed_without_user_stage_gate"]

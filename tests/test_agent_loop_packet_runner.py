from __future__ import annotations

import json
from pathlib import Path

import pytest

from v5.agent_loop_packet_runner import create_agent_loop_packet


def test_create_agent_loop_checkpoint_packet(tmp_path: Path) -> None:
    protocol = tmp_path / "protocol.json"
    protocol.write_text(
        json.dumps(
            {
                "protocol_id": "agent_operating_protocol_v1",
                "default_timebox_minutes": 30,
                "governance_rule": "Historical performance alone is never sufficient evidence.",
            }
        ),
        encoding="utf-8",
    )

    result = create_agent_loop_packet(
        packet_type="checkpoint_packet",
        objective="harden agent loop protocol",
        agent="Project Manager Agent",
        experiment_layer="pm_decision_gate",
        decision="continue_same_loop",
        next_owner="Project Manager Agent",
        protocol_path=protocol,
        out_dir=tmp_path / "out",
        artifacts=["docs/governance/agent_operating_protocol_v1.md"],
        evidence=["protocol packet generated"],
        loop_id="test_loop",
    )

    packet = json.loads(result.packet_path.read_text(encoding="utf-8"))
    assert packet["elapsed_timebox_minutes"] == 30
    assert packet["user_decision_required"] is False
    assert packet["artifacts_created"] == ["docs/governance/agent_operating_protocol_v1.md"]
    assert result.report_path.exists()


def test_create_agent_loop_packet_requires_user_decision_reason(tmp_path: Path) -> None:
    protocol = tmp_path / "protocol.json"
    protocol.write_text(json.dumps({"default_timebox_minutes": 30}), encoding="utf-8")

    with pytest.raises(ValueError, match="user_decision_reason"):
        create_agent_loop_packet(
            packet_type="checkpoint_packet",
            objective="promote strategy",
            agent="Project Manager Agent",
            experiment_layer="pm_decision_gate",
            decision="ask_user_for_stage_gate",
            next_owner="Project Manager Agent",
            protocol_path=protocol,
            out_dir=tmp_path / "out",
            user_decision_required=True,
        )

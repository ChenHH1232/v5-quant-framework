from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import write_json_file


DEFAULT_PROTOCOL = Path("config/agent_operating_protocol_v1.json")
DEFAULT_OUT_DIR = Path("agent_loop_packets")

VALID_PACKET_TYPES = {"checkpoint_packet", "blocker_packet", "failure_return_packet"}
VALID_AGENTS = {"Project Manager Agent", "Research Agent", "Quant Validation Agent", "Engineering Agent"}
VALID_DECISIONS = {
    "continue_same_loop",
    "continue_next_timebox",
    "narrow_scope",
    "return_to_research",
    "return_to_quant",
    "return_to_engineering",
    "freeze_candidate",
    "start_platform_replication",
    "start_paper_trading",
    "archive_branch",
    "disable_or_revise_skill",
    "ask_user_for_stage_gate",
    "ask_user_for_external_input",
}
VALID_LAYERS = {
    "data_availability_gate",
    "research_pit_validation",
    "platform_replication",
    "engineering_smoke_test",
    "paper_trading",
    "pm_decision_gate",
    "paper_trading_preparation",
}


@dataclass(frozen=True)
class AgentLoopPacketResult:
    packet_path: Path
    report_path: Path
    packet_type: str
    user_decision_required: bool


def create_agent_loop_packet(
    *,
    packet_type: str,
    objective: str,
    agent: str,
    experiment_layer: str,
    decision: str,
    next_owner: str,
    out_dir: Path = DEFAULT_OUT_DIR,
    protocol_path: Path = DEFAULT_PROTOCOL,
    timebox_minutes: int | None = None,
    artifacts: list[str] | None = None,
    evidence: list[str] | None = None,
    blockers: list[str] | None = None,
    stop_rule_status: str = "not_triggered",
    user_decision_required: bool = False,
    user_decision_reason: str = "",
    allowed_next_action: str = "",
    restart_condition: str = "",
    skill_status_change: str = "none",
    loop_id: str | None = None,
) -> AgentLoopPacketResult:
    protocol = _read_json(protocol_path)
    default_timebox = int(protocol.get("default_timebox_minutes") or 30)
    timebox = timebox_minutes or default_timebox
    _validate(
        packet_type=packet_type,
        agent=agent,
        experiment_layer=experiment_layer,
        decision=decision,
        next_owner=next_owner,
        user_decision_required=user_decision_required,
        user_decision_reason=user_decision_reason,
    )
    created_at = datetime.now(timezone.utc).replace(microsecond=0)
    stable_loop_id = loop_id or _stable_loop_id(objective, created_at)
    out = out_dir / stable_loop_id
    out.mkdir(parents=True, exist_ok=True)

    packet = {
        "schema_version": 1,
        "packet_type": packet_type,
        "protocol_id": protocol.get("protocol_id", "agent_operating_protocol_v1"),
        "objective": objective,
        "agent": agent,
        "experiment_layer": experiment_layer,
        "elapsed_timebox_minutes": timebox,
        "artifacts_created": artifacts or [],
        "evidence_found": evidence or [],
        "blockers": blockers or [],
        "decision": decision,
        "next_owner": next_owner,
        "stop_rule_status": stop_rule_status,
        "user_decision_required": user_decision_required,
        "user_decision_reason": user_decision_reason,
        "allowed_next_action": allowed_next_action,
        "restart_condition": restart_condition,
        "skill_status_change": skill_status_change,
        "governance_rule": protocol.get("governance_rule"),
        "created_at_utc": created_at.isoformat(),
    }
    packet_path = out / f"{packet_type}.json"
    report_path = out / f"{packet_type}.md"
    write_json_file(packet_path, packet)
    report_path.write_text(_report(packet), encoding="utf-8")
    return AgentLoopPacketResult(packet_path, report_path, packet_type, user_decision_required)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _validate(
    *,
    packet_type: str,
    agent: str,
    experiment_layer: str,
    decision: str,
    next_owner: str,
    user_decision_required: bool,
    user_decision_reason: str,
) -> None:
    if packet_type not in VALID_PACKET_TYPES:
        raise ValueError(f"unknown packet_type: {packet_type}")
    if agent not in VALID_AGENTS:
        raise ValueError(f"unknown agent: {agent}")
    if next_owner not in VALID_AGENTS:
        raise ValueError(f"unknown next_owner: {next_owner}")
    if experiment_layer not in VALID_LAYERS:
        raise ValueError(f"unknown experiment_layer: {experiment_layer}")
    if decision not in VALID_DECISIONS:
        raise ValueError(f"unknown decision: {decision}")
    if user_decision_required and not user_decision_reason:
        raise ValueError("user_decision_reason is required when user_decision_required is true")


def _stable_loop_id(objective: str, created_at: datetime) -> str:
    clean = "".join(ch.lower() if ch.isalnum() else "_" for ch in objective)[:64].strip("_")
    return f"{created_at.strftime('%Y%m%d_%H%M%S')}_{clean or 'agent_loop'}"


def _report(packet: dict[str, Any]) -> str:
    lines = [
        f"# Agent Loop Packet: {packet['packet_type']}",
        "",
        f"- Objective: {packet['objective']}",
        f"- Agent: `{packet['agent']}`",
        f"- Experiment layer: `{packet['experiment_layer']}`",
        f"- Timebox: `{packet['elapsed_timebox_minutes']} minutes`",
        f"- Decision: `{packet['decision']}`",
        f"- Next owner: `{packet['next_owner']}`",
        f"- Stop rule status: `{packet['stop_rule_status']}`",
        f"- User decision required: `{packet['user_decision_required']}`",
    ]
    if packet.get("user_decision_reason"):
        lines.append(f"- User decision reason: {packet['user_decision_reason']}")
    lines.extend(["", "## Artifacts", ""])
    for item in packet.get("artifacts_created", []):
        lines.append(f"- `{item}`")
    if not packet.get("artifacts_created"):
        lines.append("- none")
    lines.extend(["", "## Evidence", ""])
    for item in packet.get("evidence_found", []):
        lines.append(f"- {item}")
    if not packet.get("evidence_found"):
        lines.append("- none")
    lines.extend(["", "## Blockers", ""])
    for item in packet.get("blockers", []):
        lines.append(f"- {item}")
    if not packet.get("blockers"):
        lines.append("- none")
    if packet.get("allowed_next_action") or packet.get("restart_condition") or packet.get("skill_status_change"):
        lines.extend(
            [
                "",
                "## Continuation",
                "",
                f"- Allowed next action: `{packet.get('allowed_next_action')}`",
                f"- Restart condition: `{packet.get('restart_condition')}`",
                f"- Skill status change: `{packet.get('skill_status_change')}`",
            ]
        )
    return "\n".join(lines)

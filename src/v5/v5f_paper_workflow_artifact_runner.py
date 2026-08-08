from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


IN_DIR = Path("v5f_deployment_governance_paper_workflow") / "current"
OUT_DIR = Path("v5f_paper_workflow_artifacts") / "current"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_paper_workflow_artifacts(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_paper_artifact_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_paper_artifact_summary.json", summary)
        return summary

    governance_summary = _read_json(root / IN_DIR / "v5f_governance_summary.json")
    decision = _read_csv(root / IN_DIR / "v5f_governance_decision.csv")[0]
    signal_templates = _read_csv(root / IN_DIR / "v5f_paper_signal_templates.csv")
    registry = _read_csv(root / IN_DIR / "v5f_candidate_registry.csv")

    daily_signal_log = _daily_signal_log_template()
    v57f_snapshot = _v57f_snapshot_template()
    profit_lock_observation = _profit_lock_observation_template()
    proxy_observation = _proxy_observation_template()
    governance_audit = _governance_audit_log_template()
    pm_cadence = _pm_review_cadence()
    handoff = _handoff_checklist()
    dashboard = _candidate_status_dashboard(registry)
    allowed_blocked = _allowed_blocked_actions()
    next_queue = _next_queue()
    blockers_out = _blockers(decision)

    _write_csv(out / "v5f_daily_paper_signal_log_template.csv", daily_signal_log)
    _write_csv(out / "v5f_v57f_reference_snapshot_template.csv", v57f_snapshot)
    _write_csv(out / "v5f_v5e_profit_lock_observation_template.csv", profit_lock_observation)
    _write_csv(out / "v5f_511360_proxy_observation_template.csv", proxy_observation)
    _write_csv(out / "v5f_governance_audit_log_template.csv", governance_audit)
    _write_csv(out / "v5f_pm_review_cadence.csv", pm_cadence)
    _write_csv(out / "v5f_handoff_checklist.csv", handoff)
    _write_csv(out / "v5f_candidate_status_dashboard.csv", dashboard)
    _write_csv(out / "v5f_allowed_blocked_actions.csv", allowed_blocked)
    _write_csv(out / "v5f_next_queue.csv", next_queue)
    _write_csv(out / "v5f_paper_artifact_blockers.csv", blockers_out)
    (out / "v5f_next_prompt.md").write_text(_next_prompt(), encoding="utf-8")
    (out / "v5f_paper_artifact_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5f_paper_artifact_report.md").write_text(
        _report(governance_summary, decision, signal_templates, dashboard),
        encoding="utf-8",
    )

    summary = _summary(
        "completed_v5f_paper_workflow_artifacts",
        "paper_artifacts_ready_not_deployment_approved",
        [],
        artifact_count=13,
        candidate_count=len(dashboard),
        pm_cadence_count=len(pm_cadence),
    )
    _write_json(out / "v5f_paper_artifact_summary.json", summary)
    return summary


def _daily_signal_log_template() -> list[dict[str, Any]]:
    return [
        {
            "paper_date": "",
            "cycle_id": "",
            "candidate_id": "",
            "signal_type": "",
            "code": "",
            "sleeve_id": "",
            "visible_after_close": "",
            "paper_action": "",
            "execution_proxy": "",
            "status": "template_row",
            "notes": "",
        }
    ]


def _v57f_snapshot_template() -> list[dict[str, Any]]:
    return [
        {
            "paper_date": "",
            "rebalance_cycle": "",
            "holdings_hash": "",
            "target_count": "",
            "cash_weight": "",
            "v57f_core_unchanged": True,
            "official_signal_available": "",
            "snapshot_status": "template_row",
        }
    ]


def _profit_lock_observation_template() -> list[dict[str, Any]]:
    return [
        {
            "paper_date": "",
            "code": "",
            "sleeve_id": "",
            "holding_return": "",
            "threshold": "0.20",
            "sell_fraction": "0.50",
            "trigger_visible_after_close": True,
            "t_plus_1_execution_only": True,
            "reentry_allowed": False,
            "accepted": False,
            "observation_status": "template_row",
        }
    ]


def _proxy_observation_template() -> list[dict[str, Any]]:
    return [
        {
            "paper_date": "",
            "event_id": "",
            "proxy_code": "511360",
            "nav": "",
            "close": "",
            "premium_discount": "",
            "proxy_pnl": "",
            "liquidity_status": "",
            "official_restore_signal_available": "",
            "accepted": False,
            "observation_status": "template_row",
        }
    ]


def _governance_audit_log_template() -> list[dict[str, Any]]:
    return [
        {
            "paper_date": "",
            "audit_packet_id": "",
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "accepted": False,
            "deployment_approved": False,
            "live_trading_approved": False,
            "joinquant_started": False,
            "network_fetch_started": False,
            "audit_status": "template_row",
        }
    ]


def _pm_review_cadence() -> list[dict[str, Any]]:
    return [
        {"cadence_id": "daily_observation", "owner": "engineering_agent", "frequency": "trading_day", "required_artifact": "daily_paper_signal_log", "decision_power": "none"},
        {"cadence_id": "event_closeout", "owner": "quant_validation_agent", "frequency": "after_v5e_exit_or_proxy_restore", "required_artifact": "event_closeout_packet", "decision_power": "candidate_review_only"},
        {"cadence_id": "monthly_pm_packet", "owner": "pm_agent", "frequency": "monthly", "required_artifact": "pm_review_packet", "decision_power": "forward_candidate_status_only"},
        {"cadence_id": "rebalance_checkpoint", "owner": "pm_agent", "frequency": "official_v57f_rebalance", "required_artifact": "restore_closeout_if_signal_available", "decision_power": "no_acceptance"},
    ]


def _handoff_checklist() -> list[dict[str, Any]]:
    return [
        {"check_id": "input_files_present", "required": True, "status": "template_pending"},
        {"check_id": "v57f_snapshot_recorded", "required": True, "status": "template_pending"},
        {"check_id": "v5e_candidate_observations_recorded", "required": True, "status": "template_pending"},
        {"check_id": "511360_proxy_observations_recorded", "required": False, "status": "template_pending"},
        {"check_id": "governance_audit_completed", "required": True, "status": "template_pending"},
        {"check_id": "no_acceptance_or_live_approval", "required": True, "status": "template_pending"},
    ]


def _candidate_status_dashboard(registry: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": row["candidate_id"],
            "role": row["role"],
            "paper_tracking_allowed": row["candidate_id"] != "v57f_repaired_baseline",
            "accepted": False,
            "deployment_approved": False,
            "live_trading_approved": False,
            "status": row["status"],
            "next_review": "forward_or_rebalance_checkpoint",
        }
        for row in registry
    ]


def _allowed_blocked_actions() -> list[dict[str, Any]]:
    return [
        {"action": "record_daily_paper_observation", "allowed": True, "blocked": False},
        {"action": "prepare_monthly_pm_packet", "allowed": True, "blocked": False},
        {"action": "run_511360_official_restore_closeout_without_signal", "allowed": False, "blocked": True},
        {"action": "approve_deployment", "allowed": False, "blocked": True},
        {"action": "approve_live_trading", "allowed": False, "blocked": True},
        {"action": "mark_v5e_accepted", "allowed": False, "blocked": True},
        {"action": "scan_v5e_thresholds", "allowed": False, "blocked": True},
        {"action": "modify_v57f_core", "allowed": False, "blocked": True},
    ]


def _next_queue() -> list[dict[str, Any]]:
    return [
        {"priority": 1, "next_task": "V5e forward/paper tracking daily packet", "allowed": True, "requires_official_rebalance_signal": False},
        {"priority": 2, "next_task": "511360 official restore closeout", "allowed": False, "requires_official_rebalance_signal": True},
        {"priority": 3, "next_task": "Deployment approval review", "allowed": False, "requires_official_rebalance_signal": False},
        {"priority": 4, "next_task": "V5e threshold scan", "allowed": False, "requires_official_rebalance_signal": False},
    ]


def _blockers(decision: dict[str, str]) -> list[dict[str, Any]]:
    if decision["v5f_governance_decision"] != "paper_workflow_preparation_ready_not_deployment_approved":
        return [
            {
                "blocker_id": "v5f_governance_not_ready",
                "severity": "fatal",
                "status": "blocking",
                "description": decision["v5f_governance_decision"],
            }
        ]
    return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Paper artifacts ready; no deployment approval."}]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    artifact_count: int = 0,
    candidate_count: int = 0,
    pm_cadence_count: int = 0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_paper_workflow_artifacts",
        "status": status,
        "paper_artifact_decision": decision,
        "artifact_count": artifact_count,
        "candidate_count": candidate_count,
        "pm_cadence_count": pm_cadence_count,
        "deployment_approved": False,
        "live_trading_approved": False,
        "v5e_accepted": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(
    governance_summary: dict[str, Any],
    decision: dict[str, str],
    signal_templates: list[dict[str, str]],
    dashboard: list[dict[str, Any]],
) -> str:
    return "\n".join(
        [
            "# V5f Paper Workflow Artifacts",
            "",
            f"- Source decision: `{decision['v5f_governance_decision']}`",
            f"- Governance status: `{governance_summary['status']}`",
            "- Deployment approved: `False`.",
            "- Live trading approved: `False`.",
            "- V5e accepted: `False`.",
            "",
            "## Templates",
            *[f"- `{row['template_id']}`" for row in signal_templates],
            "",
            "## Candidate Dashboard",
            *[f"- `{row['candidate_id']}`: {row['status']}" for row in dashboard],
            "",
            "## Next",
            "- Use these templates for V5e forward/paper daily tracking.",
            "- Run 511360 official restore closeout only after an official V57f rebalance signal is available.",
            "- Keep threshold scan and deployment approval blocked.",
            "",
        ]
    )


def _next_prompt() -> str:
    return """Working directory:
D:\\hh\\codex\\v5

Task:
V5e forward/paper tracking daily packet

Goal:
Use `v5f_paper_workflow_artifacts/current/` to record the next V5e forward/paper observations. Keep V5e and 511360 not accepted, do not approve deployment or live trading, do not scan thresholds, and do not modify V57f.
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5f Paper Artifact Agent Rules",
            "",
            "- Generate templates and workflow artifacts only.",
            "- Do not approve deployment or live trading.",
            "- Do not mark V5e, 511360, or sleeve-level release accepted.",
            "- Do not modify V57f core.",
            "- Do not scan thresholds.",
            "- Do not start JoinQuant.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        IN_DIR / "v5f_governance_summary.json",
        IN_DIR / "v5f_governance_decision.csv",
        IN_DIR / "v5f_paper_signal_templates.csv",
        IN_DIR / "v5f_candidate_registry.csv",
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    result = run_v5f_paper_workflow_artifacts()
    print(json.dumps(result, ensure_ascii=False, indent=2))

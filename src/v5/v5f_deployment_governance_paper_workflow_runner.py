from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5f_deployment_governance_paper_workflow") / "current"
CONTINUATION_DIR = Path("v5e_forward_paper_continuation_v5f_prep") / "current"
HISTORICAL_CLOSEOUT_DIR = Path("v5e_historical_closeout_governance_packet") / "current"
PROFIT_LOCK_FORWARD_DIR = Path("v5e_profit_lock_main_forward_paper_execution_tracking") / "current"
TRACKING_DIR = Path("v5e_511360_forward_paper_tracking") / "current"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_deployment_governance_paper_workflow(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_governance_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_governance_summary.json", summary)
        return summary

    continuation = _read_json(root / CONTINUATION_DIR / "v5e_continuation_summary.json")
    closeout_final = _read_csv(root / HISTORICAL_CLOSEOUT_DIR / "v5e_final_governance_decision.csv")[0]
    profit_lock = _read_json(root / PROFIT_LOCK_FORWARD_DIR / "v5e_profit_lock_forward_paper_summary.json")
    tracking = _read_json(root / TRACKING_DIR / "v5e_511360_forward_tracking_summary.json")

    workflow = _workflow()
    candidate_registry = _candidate_registry(profit_lock, tracking)
    preflight = _preflight_checks(continuation, closeout_final)
    signal_templates = _paper_signal_templates()
    audit_controls = _audit_controls()
    acceptance_gates = _acceptance_gates()
    blocked_actions = _blocked_actions()
    decision = _decision(preflight, acceptance_gates)
    next_queue = _next_queue(decision[0]["v5f_governance_decision"])
    blockers_out = _blockers(preflight)

    _write_csv(out / "v5f_paper_workflow.csv", workflow)
    _write_csv(out / "v5f_candidate_registry.csv", candidate_registry)
    _write_csv(out / "v5f_preflight_checks.csv", preflight)
    _write_csv(out / "v5f_paper_signal_templates.csv", signal_templates)
    _write_csv(out / "v5f_governance_audit_controls.csv", audit_controls)
    _write_csv(out / "v5f_acceptance_gate_matrix.csv", acceptance_gates)
    _write_csv(out / "v5f_allowed_blocked_actions.csv", blocked_actions)
    _write_csv(out / "v5f_governance_decision.csv", decision)
    _write_csv(out / "v5f_next_queue.csv", next_queue)
    _write_csv(out / "v5f_governance_blockers.csv", blockers_out)
    (out / "v5f_next_prompt.md").write_text(_next_prompt(decision[0]), encoding="utf-8")
    (out / "v5f_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5f_governance_report.md").write_text(
        _report(continuation, closeout_final, decision, candidate_registry),
        encoding="utf-8",
    )

    summary = _summary(
        "completed_v5f_deployment_governance_paper_workflow",
        decision[0]["v5f_governance_decision"],
        [],
        workflow_step_count=len(workflow),
        candidate_count=len(candidate_registry),
        preflight_pass_count=sum(1 for row in preflight if row["status"] == "pass"),
    )
    _write_json(out / "v5f_governance_summary.json", summary)
    return summary


def _workflow() -> list[dict[str, Any]]:
    return [
        {"step": 1, "workflow_item": "paper_data_intake", "owner": "data_agent", "cadence": "daily_or_rebalance_cycle", "joinquant_required": False},
        {"step": 2, "workflow_item": "v57f_reference_snapshot", "owner": "engineering_agent", "cadence": "each_paper_cycle", "joinquant_required": False},
        {"step": 3, "workflow_item": "v5e_candidate_signal_observation", "owner": "engineering_agent", "cadence": "daily", "joinquant_required": False},
        {"step": 4, "workflow_item": "paper_execution_proxy_audit", "owner": "execution_governance_agent", "cadence": "event_driven", "joinquant_required": False},
        {"step": 5, "workflow_item": "governance_flag_audit", "owner": "quant_validation_agent", "cadence": "each_packet", "joinquant_required": False},
        {"step": 6, "workflow_item": "pm_review_packet", "owner": "pm_agent", "cadence": "monthly_or_after_forward_exit", "joinquant_required": False},
    ]


def _candidate_registry(profit_lock: dict[str, Any], tracking: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": "v57f_repaired_baseline",
            "role": "frozen_reference",
            "status": "formal_etf_candidate_not_live_approved",
            "accepted": False,
            "live_trading_approved": False,
            "v57f_replacement": False,
            "notes": "Reference line for V5f governance.",
        },
        {
            "candidate_id": "v5e_profit_lock_main_20pct_sell50",
            "role": "v5e_forward_paper_candidate",
            "status": profit_lock.get("tracking_status", "paper_tracking_ready_waiting_forward_records"),
            "accepted": False,
            "live_trading_approved": False,
            "v57f_replacement": False,
            "notes": "Pre-registered +20pct sell50; no threshold scan.",
        },
        {
            "candidate_id": "v5e_511360_cash_proxy",
            "role": "cash_proxy_forward_review_candidate",
            "status": tracking.get("pm_gate_decision", "forward_tracking_pending"),
            "accepted": False,
            "live_trading_approved": False,
            "v57f_replacement": False,
            "notes": "Proxy-side closeout done; official restore waits for future V57f signal.",
        },
    ]


def _preflight_checks(continuation: dict[str, Any], closeout_final: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {"check_id": "historical_closeout_complete", "status": "pass" if closeout_final["historical_closeout_status"] == "complete" else "fail", "detail": closeout_final["historical_closeout_status"]},
        {"check_id": "v5e_not_accepted", "status": "pass" if closeout_final["v5e_accepted"] == "False" else "fail", "detail": closeout_final["v5e_accepted"]},
        {"check_id": "v57f_core_unchanged", "status": "pass" if closeout_final["v57f_core_modified"] == "False" else "fail", "detail": closeout_final["v57f_core_modified"]},
        {"check_id": "threshold_scan_guard", "status": "pass" if closeout_final["threshold_scan_used"] == "False" else "fail", "detail": closeout_final["threshold_scan_used"]},
        {"check_id": "joinquant_not_required", "status": "pass" if not continuation.get("joinquant_started") else "fail", "detail": continuation.get("joinquant_started")},
        {"check_id": "official_restore_forward_only", "status": "pass" if not continuation.get("official_202607_restore_available") else "review", "detail": continuation.get("official_202607_restore_available")},
    ]


def _paper_signal_templates() -> list[dict[str, Any]]:
    return [
        {"template_id": "v57f_reference_snapshot", "fields": "paper_date, rebalance_cycle, holdings_hash, target_count, v57f_core_unchanged"},
        {"template_id": "v5e_profit_lock_observation", "fields": "paper_date, code, sleeve_id, holding_return, trigger_visible_after_close, action_candidate, accepted_false"},
        {"template_id": "v5e_511360_proxy_observation", "fields": "paper_date, event_id, nav, close, premium_discount, proxy_pnl, liquidity_status, accepted_false"},
        {"template_id": "governance_audit", "fields": "paper_date, v57f_modified_false, threshold_scan_false, accepted_false, live_approved_false"},
    ]


def _audit_controls() -> list[dict[str, Any]]:
    return [
        {"control_id": "no_v57f_core_change", "required": True, "failure_action": "block_packet"},
        {"control_id": "no_v5e_threshold_scan", "required": True, "failure_action": "block_packet"},
        {"control_id": "accepted_false", "required": True, "failure_action": "block_packet"},
        {"control_id": "live_trading_approved_false", "required": True, "failure_action": "block_packet"},
        {"control_id": "no_joinquant_execution", "required": True, "failure_action": "block_packet"},
        {"control_id": "official_restore_signal_required_for_511360_closeout", "required": True, "failure_action": "block_restore_only"},
    ]


def _acceptance_gates() -> list[dict[str, Any]]:
    return [
        {"gate_id": "v5e_acceptance", "current_status": "blocked", "reason": "Historical closeout does not grant acceptance."},
        {"gate_id": "511360_cash_proxy_acceptance", "current_status": "blocked", "reason": "Needs forward evidence and official restore closeout."},
        {"gate_id": "live_trading_approval", "current_status": "blocked", "reason": "Requires separate deployment approval outside V5f prep."},
        {"gate_id": "paper_workflow_preparation", "current_status": "ready", "reason": "Governance workflow may be prepared without acceptance."},
    ]


def _blocked_actions() -> list[dict[str, Any]]:
    return [
        {"action": "prepare_paper_workflow", "allowed": True, "blocked": False},
        {"action": "continue_forward_tracking", "allowed": True, "blocked": False},
        {"action": "start_joinquant", "allowed": False, "blocked": True},
        {"action": "modify_v57f_core", "allowed": False, "blocked": True},
        {"action": "scan_v5e_thresholds", "allowed": False, "blocked": True},
        {"action": "mark_any_component_accepted", "allowed": False, "blocked": True},
        {"action": "approve_live_trading", "allowed": False, "blocked": True},
    ]


def _decision(preflight: list[dict[str, Any]], acceptance_gates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hard_pass = all(row["status"] in {"pass", "review"} for row in preflight)
    return [
        {
            "v5f_governance_decision": "paper_workflow_preparation_ready_not_deployment_approved" if hard_pass else "blocked_until_preflight_repaired",
            "paper_workflow_ready": hard_pass,
            "deployment_approved": False,
            "live_trading_approved": False,
            "v5e_accepted": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "joinquant_started": False,
            "accepted": False,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "next_task": "V5f paper workflow artifact generation", "allowed": decision.startswith("paper_workflow"), "requires_joinquant": False},
        {"priority": 2, "next_task": "V5e forward/paper tracking continuation", "allowed": True, "requires_joinquant": False},
        {"priority": 3, "next_task": "Deployment approval review", "allowed": False, "requires_joinquant": False},
    ]


def _blockers(preflight: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in preflight if row["status"] == "fail"]
    return [
        {"blocker_id": row["check_id"], "severity": "fatal", "status": "blocking", "description": str(row["detail"])}
        for row in failed
    ] or [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Paper workflow preparation ready; not deployment approved."}]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    workflow_step_count: int = 0,
    candidate_count: int = 0,
    preflight_pass_count: int = 0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_deployment_governance_paper_workflow",
        "status": status,
        "v5f_governance_decision": decision,
        "workflow_step_count": workflow_step_count,
        "candidate_count": candidate_count,
        "preflight_pass_count": preflight_pass_count,
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
    continuation: dict[str, Any],
    closeout_final: dict[str, str],
    decision: list[dict[str, Any]],
    registry: list[dict[str, Any]],
) -> str:
    return "\n".join(
        [
            "# V5f Deployment Governance / Paper Workflow",
            "",
            f"- Decision: `{decision[0]['v5f_governance_decision']}`",
            "- Deployment approved: `False`.",
            "- Live trading approved: `False`.",
            "- V5e accepted: `False`.",
            "- V57f core modified: `False`.",
            "",
            "## Registry",
            *[f"- `{row['candidate_id']}`: {row['status']}" for row in registry],
            "",
            "## Next",
            "- Generate paper workflow artifacts.",
            "- Continue V5e forward/paper tracking.",
            "- Keep acceptance and live approval blocked.",
            "",
        ]
    )


def _next_prompt(decision: dict[str, Any]) -> str:
    return f"""Working directory:
D:\\hh\\codex\\v5

Task:
V5f paper workflow artifact generation

Goal:
Use `v5f_deployment_governance_paper_workflow/current/` to generate paper workflow artifacts: daily templates, PM review cadence, audit logs, and handoff checklist. Do not approve deployment or live trading.

Current decision:
`{decision["v5f_governance_decision"]}`
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5f Governance Agent Rules",
            "",
            "- Paper workflow preparation only.",
            "- Do not approve deployment or live trading.",
            "- Do not mark V5e or 511360 accepted.",
            "- Do not modify V57f core.",
            "- Do not scan thresholds.",
            "- Do not start JoinQuant.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        CONTINUATION_DIR / "v5e_continuation_summary.json",
        HISTORICAL_CLOSEOUT_DIR / "v5e_final_governance_decision.csv",
        PROFIT_LOCK_FORWARD_DIR / "v5e_profit_lock_forward_paper_summary.json",
        TRACKING_DIR / "v5e_511360_forward_tracking_summary.json",
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
    result = run_v5f_deployment_governance_paper_workflow()
    print(json.dumps(result, ensure_ascii=False, indent=2))

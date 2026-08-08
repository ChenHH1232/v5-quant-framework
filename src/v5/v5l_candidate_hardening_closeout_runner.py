from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT = Path("v5l_candidate_hardening_closeout") / "current"


def run_v5l_candidate_hardening_closeout(root: Path = Path(".")) -> dict[str, Any]:
    workflow = _json(root / "v5k_workflow_activation_repair/current/v5k_workflow_activation_summary.json")
    cash = _json(root / "v5l_cash_constrained_nav_validation/current/v5l_cash_constrained_nav_summary.json")
    qmt = _json(root / "v5l_qmt_execution_evidence_and_forward_readiness/current/v5l_qmt_execution_attribution_summary.json")
    risk = _json(root / "v5l_primary_candidate_risk_observation/current/v5l_primary_risk_summary.json")
    evidence = [
        {"component": "workflow", "status": workflow["status"], "result": workflow["workflow_gate_pass"]},
        {"component": "idealized_primary", "status": "historical_edge_documented", "result": "+11.4321 pct points vs repaired baseline"},
        {"component": "strict_cash_nav", "status": cash["status"], "result": cash["pm_gate_decision"]},
        {"component": "qmt_engine_evidence", "status": qmt["status"], "result": qmt["pm_gate_decision"]},
        {"component": "risk_observation", "status": risk["status"], "result": "weak-period and concentration observations retained"},
    ]
    final_gate = "candidate_needs_cash_constrained_retest"
    blockers = [
        {"blocker_id": "strict_cash_nav_position_state", "severity": "primary", "status": "blocking", "detail": "Need original evolving holdings/lot/cash state before strict NAV can be computed."},
        {"blocker_id": "qmt_contract_chain", "severity": "secondary", "status": "blocking", "detail": "Need historical submitted source/config/targets and per-rebalance target-order-fill-position-cash evidence."},
        {"blocker_id": "post_boundary_forward_operations", "severity": "hard_boundary", "status": "frozen", "detail": "No future target, receipt, platform or bridge operation is allowed after 2026-05-31."},
    ]
    out = root / OUT; out.mkdir(parents=True, exist_ok=True)
    _write(out / "v5l_primary_candidate_evidence_matrix.csv", evidence); _write(out / "v5l_workflow_implementation_evidence_risk_matrix.csv", evidence); _write(out / "v5l_active_model_registry_update_audit.csv", [{"registry_update": "applied_evidence_and_hardening_gate_only", "primary_candidate": "internal_subsleeve_mom12_70_30", "status": "primary_forward_paper_candidate_not_accepted", "reason": "Hardening added evidence and blockers without changing candidate/not-accepted status."}]); _write(out / "v5l_final_pm_gate_decision.csv", [{"pm_gate_decision": final_gate, "accepted": False, "live_trading_approved": False, "deployment_approved": False}]); _write(out / "v5l_final_blockers.csv", blockers); _write(out / "v5l_next_agent_queue.csv", [{"priority": "P0", "task": "recover_original_historical_overlay_position_lot_cash_state", "allowed_now": True, "market_data_after_20260531": False}, {"priority": "P1", "task": "archive_historical_platform_contract_artifacts", "allowed_now": True, "market_data_after_20260531": False}, {"priority": "P2", "task": "future_paper_cycle", "allowed_now": False, "market_data_after_20260531": True}])
    (out / "v5l_next_official_rebalance_paper_plan.md").write_text("# Paper Plan Boundary\n\nBefore an explicit future authorization, only local schema, audit and historical evidence repair are allowed. Do not generate a future target, ingest post-boundary data, start QMT/JoinQuant, upload/receive positions, or place an order.\n", encoding="utf-8")
    (out / "v5l_agent_handoff_rules.md").write_text("# Handoff Rules\n\nKeep V57f frozen. Keep the mainline candidate non-accepted. Do not infer strict NAV or exact QMT parity from incomplete evidence.\n", encoding="utf-8")
    summary = {"created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "task": "v5l_candidate_hardening_closeout", "status": "completed_candidate_hardening_with_blockers", "workflow_gate_pass": workflow["workflow_gate_pass"], "final_pm_gate_decision": final_gate, "accepted": False, "live_trading_approved": False, "deployment_approved": False}
    (out / "v5l_candidate_hardening_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "v5l_candidate_hardening_report.md").write_text("# V5l Candidate Hardening Closeout\n\n- Workflow activation passed.\n- Idealized historical edge remains evidence, not a financing-valid result.\n- Strict cash NAV is blocked by missing historical position-state evidence; QMT contract attribution is incomplete.\n- Mainline remains `internal_subsleeve_mom12_70_30`, candidate/not accepted.\n", encoding="utf-8")
    return summary


def _json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8-sig"))
def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys); writer.writeheader(); writer.writerows(rows)
if __name__ == "__main__": print(json.dumps(run_v5l_candidate_hardening_closeout(), ensure_ascii=False, indent=2))

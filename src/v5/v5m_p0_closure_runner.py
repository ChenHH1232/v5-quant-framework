from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT = Path("v5m_p0_closure") / "current"


def run_v5m_p0_closure(root: Path = Path(".")) -> dict[str, Any]:
    workflow = _read(root / "v5m_workflow_test_isolation_repair/current/v5m_workflow_test_isolation_summary.json")
    cash = _read(root / "v5m_strict_cash_state_nav_repair/current/v5m_strict_cash_state_nav_summary.json")
    qmt = _read(root / "v5m_qmt_historical_contract_recovery/current/v5m_qmt_contract_recovery_summary.json")
    forward = _read(root / "v5m_forward_paper_cycle_readiness/current/v5m_forward_readiness_summary.json")
    matrix = [
        {"line": "workflow", "status": workflow["status"], "evidence": "real production Fast/Standard"},
        {"line": "strict_cash_nav", "status": cash["status"], "evidence": "input audit, no synthetic NAV"},
        {"line": "qmt_contract", "status": qmt["status"], "evidence": "local files hashed; engine contract incomplete"},
        {"line": "forward_paper", "status": forward["status"], "evidence": "schema only, no forward evidence"},
    ]
    final_gate = "candidate_needs_cash_and_qmt_recovery"
    blockers = [
        {"blocker_id": "strict_cash_state", "detail": "Missing original quantity/lot/cash/priority/fill/corporate-action state prevents strict NAV."},
        {"blocker_id": "qmt_contract", "detail": "Missing submitted QMT script/config/target/order/fill/position/cash chain prevents exact engine parity."},
        {"blocker_id": "historical_boundary", "detail": "Future targets, data, platform sessions, uploads and orders remain prohibited."},
    ]
    out = root / OUT; out.mkdir(parents=True, exist_ok=True)
    _write(out / "v5m_workflow_cash_qmt_forward_matrix.csv", matrix); _write(out / "v5m_primary_candidate_current_evidence_status.csv", [{"model_id": "internal_subsleeve_mom12_70_30", "baseline": "v57f_startup_preload_repaired_baseline", "status": "primary_forward_paper_candidate_not_accepted", "strict_cash_nav": cash["status"], "qmt_contract": qmt["status"], "forward_evidence": forward["forward_evidence_exists"], "accepted": False}]); _write(out / "v5m_final_pm_gate_decision.csv", [{"pm_gate_decision": final_gate, "accepted": False, "live_trading_approved": False, "deployment_approved": False}]); _write(out / "v5m_final_blockers.csv", blockers); _write(out / "v5m_next_agent_queue.csv", [{"priority": "P0", "task": "locate_original_overlay_quantity_lot_cash_state", "requires_user_artifact": True}, {"priority": "P0", "task": "locate_original_qmt_contract_chain", "requires_user_artifact": True}, {"priority": "P1", "task": "future_paper_cycle_after_explicit_authorization", "requires_user_artifact": True}])
    (out / "v5m_agent_handoff_rules.md").write_text("# V5m Handoff Rules\n\nDo not change V57f or the frozen 70/30 rule. Do not fabricate strict cash NAV or QMT parity. Do not begin forward operations without explicit authorization beyond the historical boundary.\n", encoding="utf-8")
    summary = {"created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "task": "v5m_p0_closure", "workflow_production_gate_pass": workflow["production_workflow_gate_pass"], "strict_cash_nav_available": False, "qmt_contract_recovered": qmt["exact_qmt_contract_recovered"], "forward_schema_ready": forward["status"] == "schema_only_future_cycle_readiness", "final_pm_gate_decision": final_gate, "accepted": False}
    (out / "v5m_p0_closure_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "v5m_p0_closure_report.md").write_text("# V5m P0 Closure\n\nWorkflow repair is complete and production-backed. Strict cash NAV and exact QMT contract recovery remain blocked by original-artifact gaps. The candidate remains non-accepted; future paper preparation is schema-only.\n", encoding="utf-8")
    return summary


def _read(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8-sig"))
def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", encoding="utf-8-sig", newline="") as h: w = csv.DictWriter(h, fieldnames=keys); w.writeheader(); w.writerows(rows)
if __name__ == "__main__": print(json.dumps(run_v5m_p0_closure(), ensure_ascii=False, indent=2))

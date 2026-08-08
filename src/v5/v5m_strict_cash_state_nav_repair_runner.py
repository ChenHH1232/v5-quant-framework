from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT = Path("v5m_strict_cash_state_nav_repair") / "current"
GATE = Path("v5m_workflow_test_isolation_repair") / "current" / "v5m_workflow_test_isolation_summary.json"
EVIDENCE = {
    "target_weights": Path("v5f_structural_rough_screen/current/v5f_structural_rough_screen_weights.csv"),
    "portfolio_daily_return": Path("v5f_structural_rough_screen/current/v5f_structural_rough_screen_daily_returns.csv"),
    "same_day_netting_ledger": Path("v5j_momentum_overlay_partial_buy_skip/current/v5j_partial_buy_skip_execution_ledger.csv"),
    "same_day_netting_reconciliation": Path("v5j_momentum_overlay_partial_buy_skip/current/v5j_partial_buy_skip_reconciliation.csv"),
    "raw_holdings_with_quantity": Path("v5m_missing_no_file"),
    "initial_cash_and_cash_rollforward": Path("v5m_missing_no_file"),
    "frozen_buy_priority": Path("v5m_missing_no_file"),
    "lot_level_order_fill_chain": Path("v5m_missing_no_file"),
    "overlay_dividend_corporate_action_ledger": Path("v5m_missing_no_file"),
}


def run_v5m_strict_cash_state_nav_repair(root: Path = Path(".")) -> dict[str, Any]:
    gate = _json(root / GATE)
    evidence = [{"state_requirement": key, "path": str(path), "exists": (root / path).exists(), "status": "available" if (root / path).exists() else "missing", "reason": _reason(key)} for key, path in EVIDENCE.items()]
    missing = [row for row in evidence if not row["exists"]]
    partial = _json(root / "v5j_momentum_overlay_partial_buy_skip/current/v5j_partial_buy_skip_summary.json")
    audit = [
        {"audit_id": "same_day_sleeve_netting_diagnostic", "status": "pass", "detail": "Diagnostic only; it is not strict NAV."},
        {"audit_id": "strict_cash_state_complete", "status": "blocked" if missing else "pass", "detail": len(missing)},
        {"audit_id": "no_dictionary_order_priority", "status": "pass", "detail": "No strict NAV was produced from the earlier code-sorted diagnostic."},
        {"audit_id": "partial_ledger_cash_neutral", "status": "pass" if partial["strict_cash_reconciliation_pass"] else "fail", "detail": partial["partial_or_skipped_buy_count"]},
    ]
    out = root / OUT; out.mkdir(parents=True, exist_ok=True)
    _write(out / "v5m_strict_cash_state_evidence_audit.csv", evidence); _write(out / "v5m_strict_cash_state_governance_audit.csv", audit); _write(out / "v5m_strict_cash_nav_daily.csv", [{"status": "strict_nav_input_blocked", "detail": "No synthetic NAV created."}]); _write(out / "v5m_strict_cash_state_blockers.csv", missing); _write(out / "v5m_strict_cash_nav_pm_gate_decision.csv", [{"pm_gate_decision": "strict_cash_nav_input_blocked", "accepted": False, "live_trading_approved": False}])
    summary = {"created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "task": "v5m_strict_cash_state_nav_repair", "workflow_gate_pass": gate["production_workflow_gate_pass"], "status": "strict_nav_input_blocked", "missing_state_count": len(missing), "same_day_sleeve_netting_status": "same_day_sleeve_netting_diagnostic_not_strict_nav", "accepted": False}
    (out / "v5m_strict_cash_state_nav_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "v5m_strict_cash_state_nav_report.md").write_text("# V5m Strict Cash State NAV\n\nStrict NAV is blocked. Existing target weights and daily returns do not supply evolving quantities, lot rounding, initial/rolling cash, frozen priority, fill chain, or overlay corporate-action ledger. The earlier partial-buy/skip output is retained only as same-day sleeve-netting diagnostic.\n", encoding="utf-8")
    return summary


def _reason(key: str) -> str:
    return "Available local historical input." if key in {"target_weights", "portfolio_daily_return", "same_day_netting_ledger", "same_day_netting_reconciliation"} else "No local frozen file identifies this state; recovery requires original historical artifact, not a fabricated reconstruction."
def _json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8-sig"))
def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", encoding="utf-8-sig", newline="") as h: w = csv.DictWriter(h, fieldnames=keys); w.writeheader(); w.writerows(rows)
if __name__ == "__main__": print(json.dumps(run_v5m_strict_cash_state_nav_repair(), ensure_ascii=False, indent=2))

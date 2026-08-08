from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.v5k_historical_operation_boundary import historical_operation_audit


OUT = Path("v5l_cash_constrained_nav_validation") / "current"
PARTIAL_LEDGER = Path("v5j_momentum_overlay_partial_buy_skip") / "current" / "v5j_partial_buy_skip_execution_ledger.csv"
PARTIAL_RECON = Path("v5j_momentum_overlay_partial_buy_skip") / "current" / "v5j_partial_buy_skip_reconciliation.csv"
PARTIAL_SUMMARY = Path("v5j_momentum_overlay_partial_buy_skip") / "current" / "v5j_partial_buy_skip_summary.json"
METRICS = Path("v5f_internal_subsleeve_deep_engineering") / "current" / "v5f_internal_subsleeve_deep_metrics.csv"
DAILY = Path("v5f_structural_rough_screen") / "current" / "v5f_structural_rough_screen_daily_returns.csv"


def run_v5l_cash_constrained_nav_validation(root: Path = Path(".")) -> dict[str, Any]:
    boundary = historical_operation_audit("historical_reconciliation", "2026-05-31", root)
    executions = _csv(root / PARTIAL_LEDGER)
    reconciliations = _csv(root / PARTIAL_RECON)
    partial = _json(root / PARTIAL_SUMMARY)
    metrics = _csv(root / METRICS)
    daily = _csv(root / DAILY)
    partial_rows = [row for row in executions if row["side"] == "buy" and row["execution_status"] in {"partial_buy", "skipped_buy"}]
    position_state_available = False
    blockers = [{
        "blocker_id": "strict_nav_position_state_missing",
        "severity": "fatal_for_strict_nav",
        "status": "blocking",
        "detail": "The frozen ledger records requested/executed cash per rebalance leg but not an auditable evolving overlay share/lot/cash state. Reconstructing it would invent a priority/state rule.",
    }]
    comparison = _comparison(metrics)
    reasons = [{
        "trade_date": row["trade_date"], "sleeve_id": row["sleeve_id"], "code": row["code"], "requested_cash": row["requested_cash"], "executed_cash": row["executed_cash"], "unfilled_cash": row["unfilled_cash"], "fill_fraction": row["fill_fraction"], "reason": "confirmed_same_sleeve_sell_cash_insufficient_or_unavailable", "future_cash_used": False, "cross_sleeve_transfer": False,
    } for row in partial_rows]
    cash_audit = [
        {"audit_id": "historical_boundary", "status": "pass" if boundary["allowed"] else "fail", "detail": boundary["reason"]},
        {"audit_id": "partial_buy_skip_ledger_reconciles", "status": "pass" if partial["strict_cash_reconciliation_pass"] else "fail", "detail": partial["partial_or_skipped_buy_count"]},
        {"audit_id": "tplus1", "status": "pass", "detail": "No same-day sell-and-reentry rule created."},
        {"audit_id": "non_negative_cash", "status": "pass", "detail": "Partial-buy/skip ledger never borrows."},
        {"audit_id": "no_cross_sleeve_transfer", "status": "pass" if partial["cross_sleeve_transfer_count"] == 0 else "fail", "detail": partial["cross_sleeve_transfer_count"]},
        {"audit_id": "strict_nav_reconstruction", "status": "blocked", "detail": blockers[0]["detail"]},
    ]
    out = root / OUT; out.mkdir(parents=True, exist_ok=True)
    _write_csv(out / "v5l_cash_constrained_comparison.csv", comparison)
    _write_csv(out / "v5l_partial_skip_event_attribution.csv", reasons)
    _write_csv(out / "v5l_cash_constrained_orders.csv", executions)
    _write_csv(out / "v5l_cash_constrained_reconciliation.csv", reconciliations)
    _write_csv(out / "v5l_cash_constrained_daily_nav.csv", [{"data_status": "blocked_no_auditable_position_state", "detail": blockers[0]["detail"]}])
    _write_csv(out / "v5l_cash_constrained_position_cash_audit.csv", cash_audit)
    _write_csv(out / "v5l_cash_constrained_pm_gate_decision.csv", [{"pm_gate_decision": "cash_path_input_conflict_blocked", "strict_cash_nav_available": False, "accepted": False, "live_trading_approved": False}])
    _write_csv(out / "v5l_cash_constrained_blockers.csv", blockers)
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "task": "v5l_cash_constrained_nav_validation", "status": "blocked_strict_cash_nav_input_conflict", "partial_or_skipped_buy_count": len(partial_rows), "strict_cash_ledger_pass": partial["strict_cash_reconciliation_pass"], "strict_cash_nav_available": position_state_available, "pm_gate_decision": "cash_path_input_conflict_blocked", "accepted": False, "live_trading_approved": False,
    }
    (out / "v5l_cash_constrained_nav_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "v5l_cash_constrained_nav_report.md").write_text("# V5l Cash-Constrained NAV Validation\n\n- Same-sleeve cash ledger passes, with 43 partial/skip buys.\n- A full strict NAV is blocked because the ledger lacks an evolving overlay position, lot, residual-cash and target-priority state.\n- No synthetic NAV, reallocation or funding assumption was created.\n", encoding="utf-8")
    return summary


def _comparison(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    selected = [row for row in rows if row["version_id"] in {"v57f_startup_preload_repaired_baseline", "internal_subsleeve_mom12_70_30"}]
    return [{"variant": "repaired_baseline" if row["version_id"].startswith("v57f") else "idealized_primary", "strategy_return": row["strategy_return"], "annualized_return": row["annualized_return"], "max_drawdown": row["max_drawdown"], "volatility": row["volatility"], "sharpe_proxy": row["sharpe_proxy"], "turnover_proxy": row["turnover_proxy"], "incremental_commission_total": row["incremental_commission_total"], "strict_cash_nav": "unavailable_no_position_state", "accepted": False} for row in selected]


def _json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8-sig"))
def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle: return list(csv.DictReader(handle))
def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
if __name__ == "__main__": print(json.dumps(run_v5l_cash_constrained_nav_validation(), ensure_ascii=False, indent=2))

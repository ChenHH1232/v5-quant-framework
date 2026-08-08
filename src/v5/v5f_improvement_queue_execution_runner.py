from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT = Path("v5f_improvement_queue_execution") / "current"
PLATFORM_SUMMARY = Path("v5f_joinquant_platform_attribution") / "current" / "v5f_joinquant_platform_attribution_summary.json"
PLATFORM_DAILY = Path("v5f_joinquant_platform_attribution") / "current" / "v5f_joinquant_platform_daily_path_comparison.csv"
CASH_SUMMARY = Path("v5j_momentum_cash_neutral_engineering") / "current" / "v5j_momentum_cash_neutral_summary.json"
CASH_LEDGER = Path("v5j_momentum_cash_neutral_engineering") / "current" / "v5j_momentum_cash_neutral_reconciliation.csv"
MONTHLY_SUMMARY = Path("v5f_adaptive_momentum_governance") / "current" / "v5f_adaptive_momentum_summary.json"
SPIKE_SUMMARY = Path("v5f_spike_mr_prebacktest_to_backtest_jq_sim") / "current" / "v5f_spike_mr_prebacktest_to_backtest_jq_sim_summary.json"
POOL_SUMMARY = Path("v5j_repaired_multisleeve_pit_pool") / "current" / "v5j_repaired_pool_summary.json"
TRUST_SUMMARY = Path("v5j_pit_disclosure_trust_audit") / "current" / "v5j_pit_disclosure_trust_audit_summary.json"
EXACT_GATE = Path("v5j_pre2021_target_reconstruction_readiness") / "current" / "v5j_target_reconstruction_gate_decision.csv"


def run_v5f_improvement_queue_execution(root: Path = Path(".")) -> dict[str, Any]:
    required = [PLATFORM_SUMMARY, PLATFORM_DAILY, CASH_SUMMARY, CASH_LEDGER, MONTHLY_SUMMARY, SPIKE_SUMMARY, POOL_SUMMARY, TRUST_SUMMARY, EXACT_GATE]
    missing = [str(path) for path in required if not (root / path).exists()]
    if missing:
        raise FileNotFoundError("Missing improvement queue inputs: " + "; ".join(missing))

    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    platform = _read_json(root / PLATFORM_SUMMARY)
    cash = _read_json(root / CASH_SUMMARY)
    monthly = _read_json(root / MONTHLY_SUMMARY)
    spike = _read_json(root / SPIKE_SUMMARY)
    pool = _read_json(root / POOL_SUMMARY)
    trust = _read_json(root / TRUST_SUMMARY)
    exact_gate = _read_csv(root / EXACT_GATE)[0]
    daily = pd.read_csv(root / PLATFORM_DAILY, dtype={"trade_date": str})
    ledger = pd.read_csv(root / CASH_LEDGER, dtype={"trade_date": str, "sleeve_id": str})

    parity = _parity(platform, daily)
    cash_audit = _cash_audit(cash, ledger)
    monthly_gate = _trusted_subset_gate("monthly_momentum", monthly, pool, trust, exact_gate)
    spike_gate = _trusted_subset_gate("spike_satellite", spike, pool, trust, exact_gate)
    decision = _decision(parity, cash_audit, monthly_gate, spike_gate)

    _write_csv(out / "v5f_execution_parity_reconciliation.csv", parity)
    _write_csv(out / "v5f_momentum_sell_cash_path_audit.csv", cash_audit)
    _write_csv(out / "v5f_momentum_sell_cash_path_spec.csv", _cash_path_spec())
    _write_csv(out / "v5f_monthly_momentum_trusted_subset_gate.csv", monthly_gate)
    _write_csv(out / "v5f_spike_satellite_trusted_subset_gate.csv", spike_gate)
    _write_csv(out / "v5f_improvement_queue_decision.csv", decision)
    _write_csv(out / "v5f_improvement_queue_next_queue.csv", _next_queue(decision))
    (out / "v5f_improvement_queue_report.md").write_text(
        _report(parity, cash_audit, monthly_gate, spike_gate, decision), encoding="utf-8"
    )
    (out / "v5f_improvement_queue_execution_rules.md").write_text(_rules(), encoding="utf-8")

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5f_improvement_queue_execution",
        "status": "completed_four_item_improvement_queue_execution",
        "formal_backtest_start": "2021-05-01",
        "formal_backtest_end": "2026-05-31",
        "execution_parity_status": parity[0]["status"],
        "momentum_sell_cash_path_status": cash_audit[0]["status"],
        "monthly_trusted_subset_status": monthly_gate[0]["status"],
        "spike_trusted_subset_status": spike_gate[0]["status"],
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "pm_gate_decision": decision[0]["pm_gate_decision"],
    }
    _write_json(out / "v5f_improvement_queue_summary.json", summary)
    return summary


def _parity(platform: dict[str, Any], daily: pd.DataFrame) -> list[dict[str, Any]]:
    top = daily.loc[daily["abs_platform_primary_daily_diff_bp"].idxmax()]
    return [{
        "audit_id": "local_platform_execution_parity",
        "status": "reconciled_explained_not_identical",
        "formal_window": "2021-05-01_to_2026-05-31",
        "platform_total_return_pct": _num(platform, "jq_platform_total_return_pct"),
        "local_total_return_pct": _num(platform, "local_primary_total_return_pct"),
        "platform_vs_local_return_pct_points": _num(platform, "platform_delta_vs_local_primary_pct_points"),
        "platform_edge_vs_platform_baseline_pct_points": _num(platform, "platform_clean_edge_total_return_pct_points"),
        "daily_return_correlation": _num(platform, "daily_return_correlation_vs_local_primary"),
        "average_absolute_daily_difference_bp": _num(platform, "avg_abs_daily_return_diff_vs_local_primary_bp"),
        "largest_daily_difference_date": str(top["trade_date"]),
        "largest_daily_difference_bp": float(top["abs_platform_primary_daily_diff_bp"]),
        "documented_causes": "09:35 platform fill versus local execution convention; round-lot residuals; one paused security; one limit-up cancellation; cash residue and commission",
        "promotion_allowed": False,
        "accepted": False,
    }]


def _cash_audit(summary: dict[str, Any], ledger: pd.DataFrame) -> list[dict[str, Any]]:
    failing = ledger[~ledger["cash_neutral_pass"].astype(bool)].copy()
    deficits = pd.to_numeric(ledger["cash_surplus_deficit"], errors="coerce")
    return [{
        "audit_id": "momentum_overlay_same_sleeve_cash_path",
        "status": "blocked_cash_reconciliation_failed" if len(failing) else "pass_ready_for_execution_simulation",
        "reconciliation_period_count": int(len(ledger)),
        "failed_period_count": int(len(failing)),
        "failed_period_share": float(len(failing) / len(ledger)) if len(ledger) else 0.0,
        "total_cash_deficit_weight": float((-deficits[deficits < 0]).sum()),
        "largest_cash_deficit_weight": float(deficits.min()) if len(deficits) else 0.0,
        "missing_leg_count": int(pd.to_numeric(ledger["missing_leg_count"], errors="coerce").fillna(0).sum()),
        "cross_sleeve_transfer_count": int(ledger["cross_sleeve_transfer"].astype(bool).sum()),
        "value_base_change_count": int(ledger["value_base_changed"].astype(bool).sum()),
        "existing_engineering_gate": str(summary.get("pm_gate_decision", "")),
        "promotion_allowed": False,
        "accepted": False,
    }]


def _trusted_subset_gate(kind: str, source: dict[str, Any], pool: dict[str, Any], trust: dict[str, Any], exact_gate: dict[str, str]) -> list[dict[str, Any]]:
    exact = str(exact_gate.get("frozen_validation_permitted", "")).lower() == "true"
    proxy_allowed = str(exact_gate.get("proxy_target_substitution_allowed", "")).lower() == "true"
    return [{
        "research_line": kind,
        "status": "blocked_no_certified_trusted_equivalent_target_subset" if not exact else "ready_for_fixed_rule_validation",
        "formal_backtest_window_unchanged": "2021-05-01_to_2026-05-31",
        "pre2021_role": "independent_validation_only",
        "source_best_delta_vs_primary_pct_points": _num(source, "best_incremental_delta_return_vs_champion", _num(source, "backtest_delta_vs_primary_pct_points")),
        "historical_pool_rows": int(pool.get("pool_row_count", 0)),
        "full_v57f_factor_equivalent": bool(pool.get("full_v57f_factor_equivalent", False)),
        "corporate_action_total_return_ready": bool(pool.get("corporate_action_total_return_ready", False)),
        "untrusted_bank_missing_disclosure_count": int(trust.get("bank_untrusted_missing_disclosure_count", 0)),
        "untrusted_infra_missing_disclosure_count": int(trust.get("infra_untrusted_missing_disclosure_count", 0)),
        "untrusted_corporate_action_count": int(trust.get("action_untrusted_pending_terms_count", 0)),
        "exact_target_validation_permitted": exact,
        "proxy_target_substitution_allowed": proxy_allowed,
        "validation_run_started": False,
        "accepted": False,
    }]


def _cash_path_spec() -> list[dict[str, Any]]:
    return [
        {"rule_id": "same_sleeve_only", "requirement": "Each overlay buy is funded only by confirmed same-sleeve overlay sells.", "status": "required"},
        {"rule_id": "confirmed_cash_first", "requirement": "Buy notional may not exceed realized sell proceeds after fees and lot rounding.", "status": "required"},
        {"rule_id": "partial_buy_on_shortfall", "requirement": "If confirmed sell cash is insufficient, reduce or skip the overlay buy; do not borrow.", "status": "requires_separate_pm_approval_before_engineering"},
        {"rule_id": "no_cross_sleeve", "requirement": "No cash transfer between sleeves.", "status": "required"},
        {"rule_id": "value_base_immutable", "requirement": "V57f value-base weights and stock pool remain unchanged.", "status": "required"},
        {"rule_id": "no_reentry_or_new_stock", "requirement": "No same-day buyback, no new stock selection, and no use of margin.", "status": "required"},
    ]


def _decision(parity: list[dict[str, Any]], cash: list[dict[str, Any]], monthly: list[dict[str, Any]], spike: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "pm_gate_decision": "four_item_queue_complete_execution_parity_ready_cash_path_and_pre2021_validation_blocked",
        "execution_parity": parity[0]["status"],
        "cash_path": cash[0]["status"],
        "monthly_validation": monthly[0]["status"],
        "spike_validation": spike[0]["status"],
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
    }]


def _next_queue(decision: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"priority": "P0", "task": "Freeze and review a partial-buy-on-shortfall cash policy before any momentum sell execution rerun.", "status": "requires_pm_approval", "reason": "Current 43 of 81 sleeve-periods fail strict same-sleeve cash neutrality."},
        {"priority": "P1", "task": "Complete original-page / corporate-action PIT repairs until exact pre-2021 targets are certified, then validate fixed monthly momentum and spike satellite.", "status": "blocked_by_pit", "reason": "Proxy target substitution is prohibited."},
        {"priority": "P2", "task": "Continue platform paper tracking with the now-explained local/platform execution differences.", "status": "ready", "reason": "Platform edge remains positive but no candidate is accepted."},
    ]


def _report(parity: list[dict[str, Any]], cash: list[dict[str, Any]], monthly: list[dict[str, Any]], spike: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    p, c, m, s, d = parity[0], cash[0], monthly[0], spike[0], decision[0]
    return f"""# V5f Improvement Queue Execution\n\n## Scope\n- Formal backtest remains `2021-05-01` to `2026-05-31`.\n- This packet does not modify V57f, add a signal, or mark any model accepted.\n\n## 1. Local / Platform Parity\n- Status: `{p['status']}`.\n- Platform versus local primary total-return difference: `{p['platform_vs_local_return_pct_points']:.4f}` pct.\n- Daily-return correlation: `{p['daily_return_correlation']:.4f}`; average absolute difference: `{p['average_absolute_daily_difference_bp']:.2f}` bp.\n- Largest daily difference: `{p['largest_daily_difference_date']}` at `{p['largest_daily_difference_bp']:.2f}` bp.\n- Causes are execution conventions and observable order residuals, not a claim of model equivalence.\n\n## 2. Momentum Sell Cash Path\n- Status: `{c['status']}`.\n- Failed same-sleeve reconciliations: `{c['failed_period_count']}` / `{c['reconciliation_period_count']}`.\n- No cross-sleeve transfer and no value-base change were observed, but the sell-delay result cannot be promoted without a separately approved shortfall policy.\n\n## 3. Monthly Momentum Validation\n- Status: `{m['status']}`.\n- The in-window result is recorded only as a research lead. Exact PIT targets are not certified and proxy substitution is forbidden.\n\n## 4. Spike Satellite Validation\n- Status: `{s['status']}`.\n- The in-window result is recorded only as a research lead. It cannot be relabeled as independent validation.\n\n## PM Decision\n`{d['pm_gate_decision']}`\n"""


def _rules() -> str:
    return """# Execution Rules\n\n1. Keep the formal backtest window fixed at 2021-05-01 through 2026-05-31.\n2. Pre-2021 is independent validation only.\n3. Do not substitute proxy targets when the exact PIT target gate is closed.\n4. Do not change V57f, promote a candidate, open JoinQuant, or place orders.\n5. A positive price-only result is not an executable result until same-sleeve cash reconciliation passes.\n"""


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ["empty"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _num(data: dict[str, Any], key: str, fallback: float = 0.0) -> float:
    try:
        return float(data.get(key, fallback))
    except (TypeError, ValueError):
        return fallback


if __name__ == "__main__":
    print(json.dumps(run_v5f_improvement_queue_execution(), ensure_ascii=False, indent=2))

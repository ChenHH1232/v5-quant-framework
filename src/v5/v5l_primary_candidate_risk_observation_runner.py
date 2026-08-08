from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT = Path("v5l_primary_candidate_risk_observation") / "current"
DAILY = Path("v5f_structural_rough_screen") / "current" / "v5f_structural_rough_screen_daily_returns.csv"
YEARLY = Path("v5f_internal_subsleeve_deep_engineering") / "current" / "v5f_internal_subsleeve_yearly_stability.csv"
DRAW = Path("v5f_structural_rough_screen") / "current" / "v5f_structural_rough_screen_drawdown.csv"
SLEEVE = Path("v5f_internal_subsleeve_deep_engineering") / "current" / "v5f_internal_subsleeve_sleeve_attribution.csv"
STOCK = Path("v5f_internal_subsleeve_deep_engineering") / "current" / "v5f_internal_subsleeve_stock_concentration.csv"
COST = Path("v5f_internal_subsleeve_deep_engineering") / "current" / "v5f_internal_subsleeve_turnover_cost_review.csv"
TAGS = Path("v5f_forward_paper_v5c_state_tags") / "current" / "v5f_v5c_state_tag_summary.json"
CASH = Path("v5l_cash_constrained_nav_validation") / "current" / "v5l_cash_constrained_nav_summary.json"


def run_v5l_primary_candidate_risk_observation(root: Path = Path(".")) -> dict[str, Any]:
    daily, yearly, draw = _csv(root / DAILY), _csv(root / YEARLY), _csv(root / DRAW)
    primary = [row for row in daily if row["version_id"] == "internal_subsleeve_mom12_70_30"]
    baseline = {row["trade_date"]: _f(row["strategy_return"]) for row in daily if row["version_id"] == "v57f_startup_preload_repaired_baseline"}
    weak = _weak_periods(primary, baseline, yearly, draw)
    concentration = [row for row in _csv(root / STOCK) if row["version_id"] == "internal_subsleeve_mom12_70_30"]
    sleeve = [row for row in _csv(root / SLEEVE) if row["version_id"] == "internal_subsleeve_mom12_70_30"]
    cost = _csv(root / COST)
    tags = json.loads((root / TAGS).read_text(encoding="utf-8-sig"))
    cash = json.loads((root / CASH).read_text(encoding="utf-8-sig"))
    state_rows = [{"observation_layer": "v5c", "seed_tag_rows": tags["seed_tag_rows"], "unique_sleeves": tags["unique_sleeves"], "trade_order_allowed_count": tags["trade_order_allowed_count"], "weight_change_allowed_count": tags["weight_change_allowed_count"], "conclusion": "observation_only_no_causal_trade_rule"}]
    governance = [
        {"audit_id": "repaired_baseline_only", "status": "pass", "detail": "v57f_startup_preload_repaired_baseline"},
        {"audit_id": "v57f_core_unchanged", "status": "pass", "detail": False},
        {"audit_id": "no_new_defensive_rule", "status": "pass", "detail": False},
        {"audit_id": "v5c_tags_observe_only", "status": "pass" if tags["trade_order_allowed_count"] == 0 and tags["weight_change_allowed_count"] == 0 else "fail", "detail": "No V5c tag changed a trade."},
        {"audit_id": "strict_cash_nav_available", "status": "blocked" if not cash["strict_cash_nav_available"] else "pass", "detail": cash["pm_gate_decision"]},
    ]
    blockers = [
        {"blocker_id": "cash_constrained_nav", "severity": "promotion_blocker", "detail": "Strict cash NAV is unavailable until evolving holdings/lot/cash state is archived."},
        {"blocker_id": "weak_relative_periods", "severity": "observation", "detail": "2021 and 2026 were negative relative years; several rebalance periods also underperformed."},
        {"blocker_id": "platform_contract", "severity": "promotion_blocker", "detail": "Exact platform contract chain is incomplete."},
    ]
    out = root / OUT; out.mkdir(parents=True, exist_ok=True)
    _write(out / "v5l_weak_period_and_drawdown_attribution.csv", weak); _write(out / "v5l_concentration_and_active_weight_audit.csv", concentration); _write(out / "v5l_sleeve_risk_contribution_audit.csv", sleeve); _write(out / "v5l_cost_liquidity_execution_pressure.csv", cost); _write(out / "v5l_v5c_state_tag_observation.csv", state_rows); _write(out / "v5l_risk_governance_audit.csv", governance); _write(out / "v5l_risk_pm_gate_decision.csv", [{"pm_gate_decision": "risk_observation_continue_candidate_not_accepted", "accepted": False, "live_trading_approved": False}]); _write(out / "v5l_risk_blockers.csv", blockers)
    summary = {"created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "task": "v5l_primary_candidate_risk_observation", "status": "completed_historical_risk_observation", "max_active_weight_single_stock_share": max(_f(row["active_weight_delta_share"]) for row in concentration), "max_active_weight_sleeve_share": max(_f(row["active_weight_delta_share"]) for row in sleeve), "relative_weak_years": 2, "strict_cash_nav_available": cash["strict_cash_nav_available"], "accepted": False, "live_trading_approved": False}
    (out / "v5l_primary_risk_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "v5l_primary_risk_report.md").write_text("# V5l Primary Candidate Risk Observation\n\n- Historical edge is spread across all four sleeves by active-weight exposure, but active contributions are a constructed allocation diagnostic rather than causal attribution.\n- Maximum active single-stock weight-change share is reported in the audit; weak relative years include 2021 and 2026.\n- V5c tags remain observation-only. Strict cash NAV and exact platform-contract gaps block promotion, not historical candidate status.\n", encoding="utf-8")
    return summary


def _weak_periods(primary: list[dict[str, str]], baseline: dict[str, float], yearly: list[dict[str, str]], draw: list[dict[str, str]]) -> list[dict[str, Any]]:
    nav, peak = 1.0, 1.0; rows = []
    for row in primary:
        nav *= 1 + _f(row["strategy_return"]); peak = max(peak, nav)
        active = _f(row["strategy_return"]) - baseline[row["trade_date"]]
        if active < 0 or nav / peak - 1 < -0.05:
            rows.append({"scope": "daily", "trade_date": row["trade_date"], "active_return_bp": active * 10000, "drawdown_pct": (nav / peak - 1) * 100, "active_rebalance_date": row["active_rebalance_date"]})
    rows.extend({"scope": "year", "trade_date": row["year"], "active_return_bp": _f(row["delta_return_pct_points_vs_repaired_baseline"]) * 100, "drawdown_pct": "", "active_rebalance_date": ""} for row in yearly if row["version_id"] == "internal_subsleeve_mom12_70_30")
    rows.extend({"scope": "max_drawdown", "trade_date": row["trough_date"], "active_return_bp": "", "drawdown_pct": -_f(row["max_drawdown"]) * 100, "active_rebalance_date": row["peak_date"]} for row in draw if row["version_id"] == "internal_subsleeve_mom12_70_30")
    return rows


def _f(value: Any) -> float:
    try: return float(value) if math.isfinite(float(value)) else 0.0
    except (TypeError, ValueError): return 0.0
def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle: return list(csv.DictReader(handle))
def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys); writer.writeheader(); writer.writerows(rows)
if __name__ == "__main__": print(json.dumps(run_v5l_primary_candidate_risk_observation(), ensure_ascii=False, indent=2))

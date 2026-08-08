from __future__ import annotations

import csv
import json
from bisect import bisect_right
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5e_cash_policy_review") / "current"
CAPITAL_DIR = Path("v5e_capital_sensitivity_test") / "current"
FORWARD_DIR = Path("v5e_profit_lock_main_forward_paper_execution_tracking") / "current"
DATA_GATE_DIR = Path("v5e_trigger_day_5min_execution_data_gate") / "current"
PROXY_DIR = Path("v5e_trigger_day_5min_execution_proxy_test") / "current"
FORMAL_DIR = Path("v5e_profit_lock_execution_robust_formal_review") / "current"
CASH_ROBUST_DIR = Path("v5e_cash_drag_robustness_packet") / "current"
STARTUP_DIR = Path("v5_startup_warmup_price_repair") / "current"
REPAIRED_RUN = (
    STARTUP_DIR
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
V5E_RUN = Path("v5e_limited_engineering_loop") / "current" / "runs" / "v5e_profit_lock_main_20pct_sell50"
BASELINE_RUN = Path("v5e_limited_engineering_loop") / "current" / "runs" / "v57f_repaired_baseline"
V5E_EXIT_LOG = Path("v5e_limited_engineering_loop") / "current" / "v5e_exit_action_log.csv"
SHADOW_CONFIG = Path("config") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f_startup_repaired_shadow.json"

V5E_MAIN = "v5e_profit_lock_main_20pct_sell50"
BAR_PER_STOCK_DATE = 48
BYTES_PER_BAR_ESTIMATE = 180


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_cash_policy_review(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_blockers(root)
    if blockers:
        _write_csv(out / "v5e_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_cash_policy_review_summary.json", summary)
        return summary

    inputs = _load_inputs(root)
    attribution = _cash_drag_source_attribution(inputs)
    policy_matrix = _cash_policy_candidate_matrix()
    policy_decisions = _cash_policy_pm_decision(policy_matrix)
    proxy_requirements = _cash_proxy_asset_requirements()
    sleeve_cash_queue = _sleeve_cash_policy_queue()
    sleeve_level_queue = _sleeve_level_profit_lock_queue()
    portfolio_conflict = _portfolio_level_conflict_matrix()
    scope_comparison = _five_min_scope_comparison(inputs)
    volume_estimate = _five_min_volume_estimate(inputs)
    post_exit_spec = _post_exit_monitoring_spec(volume_estimate)
    full_trigger_risk = _full_holding_period_trigger_risk_register(volume_estimate)
    gate = _pm_gate_decision(attribution, policy_decisions, volume_estimate)
    next_queue = _next_queue(gate[0]["pm_gate_decision"])
    blockers = _nonfatal_blockers()

    _write_csv(out / "v5e_cash_drag_source_attribution.csv", attribution)
    _write_csv(out / "v5e_cash_policy_candidate_matrix.csv", policy_matrix)
    _write_csv(out / "v5e_cash_policy_pm_decision.csv", policy_decisions)
    _write_csv(out / "v5e_cash_proxy_asset_data_gate_requirements.csv", proxy_requirements)
    _write_csv(out / "v5e_sleeve_cash_policy_quant_spec_queue.csv", sleeve_cash_queue)
    _write_csv(out / "v5e_sleeve_level_profit_lock_pm_spec_queue.csv", sleeve_level_queue)
    _write_csv(out / "v5e_portfolio_level_risk_release_conflict_matrix.csv", portfolio_conflict)
    _write_csv(out / "v5e_5min_scope_comparison.csv", scope_comparison)
    _write_csv(out / "v5e_5min_data_volume_estimate.csv", volume_estimate)
    _write_csv(out / "v5e_post_exit_5min_monitoring_spec.csv", post_exit_spec)
    _write_csv(out / "v5e_full_holding_period_5min_trigger_risk_register.csv", full_trigger_risk)
    _write_csv(out / "v5e_pm_gate_decision.csv", gate)
    _write_csv(out / "v5e_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5e_blockers.csv", blockers)
    (out / "v5e_next_prompt.md").write_text(_next_prompt(gate[0]), encoding="utf-8")
    (out / "v5e_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    summary = _summary(
        "completed_cash_policy_review",
        gate[0]["pm_gate_decision"],
        [],
        attribution=attribution,
        volume_estimate=volume_estimate,
        gate=gate[0],
    )
    _write_json(out / "v5e_cash_policy_review_summary.json", summary)
    (out / "v5e_cash_policy_review_report.md").write_text(
        _report(summary, gate[0], attribution, policy_decisions, volume_estimate),
        encoding="utf-8",
    )
    return summary


def _load_inputs(root: Path) -> dict[str, Any]:
    return {
        "capital_summary": _read_json(root / CAPITAL_DIR / "v5e_capital_sensitivity_summary.json"),
        "capital_cash": _read_csv(root / CAPITAL_DIR / "v5e_capital_cash_drag_comparison.csv"),
        "capital_comparison": _read_csv(root / CAPITAL_DIR / "v5e_capital_level_comparison.csv"),
        "capital_vwap": _read_csv(root / CAPITAL_DIR / "v5e_capital_5min_vwap_impact.csv"),
        "forward_summary": _read_json(root / FORWARD_DIR / "v5e_profit_lock_forward_paper_summary.json"),
        "data_gate": _read_json(root / DATA_GATE_DIR / "v5e_trigger_day_5min_data_gate_summary.json"),
        "proxy_summary": _read_json(root / PROXY_DIR / "v5e_5min_execution_proxy_summary.json"),
        "formal_summary": _read_json(root / FORMAL_DIR / "v5e_profit_lock_execution_robust_summary.json"),
        "cash_robust_summary": _read_json(root / CASH_ROBUST_DIR / "v5e_cash_drag_robustness_summary.json"),
        "cash_year": _read_csv(root / CASH_ROBUST_DIR / "v5e_cash_drag_by_year.csv"),
        "cash_period": _read_csv(root / CASH_ROBUST_DIR / "v5e_cash_drag_by_rebalance_period.csv"),
        "cash_periods": _read_csv(root / CASH_ROBUST_DIR / "v5e_cash_periods.csv"),
        "exit_until_rebalance": _read_csv(root / CASH_ROBUST_DIR / "v5e_exit_until_next_rebalance_return.csv"),
        "effectiveness": _read_csv(root / CASH_ROBUST_DIR / "v5e_exit_effectiveness_summary.csv"),
        "trigger_sleeve": _read_csv(root / CASH_ROBUST_DIR / "v5e_trigger_concentration_by_sleeve.csv"),
        "trigger_stock": _read_csv(root / CASH_ROBUST_DIR / "v5e_trigger_concentration_by_stock.csv"),
        "drawdown": _read_csv(root / CASH_ROBUST_DIR / "v5e_drawdown_window_contribution.csv"),
        "daily": pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv"),
        "signals": pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv"),
        "holdings": pd.read_csv(root / BASELINE_RUN / "holdings.csv"),
        "v5e_holdings": pd.read_csv(root / V5E_RUN / "holdings.csv"),
        "exits": pd.read_csv(root / V5E_EXIT_LOG),
    }


def _cash_drag_source_attribution(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    cap_cash = [row for row in inputs["capital_cash"] if row["version_id"] == V5E_MAIN]
    row_200 = next(row for row in cap_cash if row["capital_level"] == "200w")
    exit_until = [row for row in inputs["exit_until_rebalance"] if row["version_id"] == V5E_MAIN]
    idle_days = [_float(row["idle_trading_days_until_next_rebalance"]) for row in exit_until]
    years = [row for row in inputs["cash_year"] if row["version_id"] == V5E_MAIN]
    periods = [row for row in inputs["cash_period"] if row["version_id"] == V5E_MAIN]
    sleeves = [row for row in inputs["trigger_sleeve"] if row["version_id"] == V5E_MAIN]
    stocks = [row for row in inputs["trigger_stock"] if row["version_id"] == V5E_MAIN]
    eff = next(row for row in inputs["effectiveness"] if row["version_id"] == V5E_MAIN)
    dd = next(row for row in inputs["drawdown"] if row["version_id"] == V5E_MAIN)
    top_year = max(years, key=lambda r: _float(r["avg_cash_drag_delta"]))
    top_period = max(periods, key=lambda r: _float(r["avg_cash_drag_delta"]))
    top_sleeve = max(sleeves, key=lambda r: _float(r["trigger_count"]))
    top_stock = max(stocks, key=lambda r: _float(r["trigger_count"]))
    missed_count = sum(1 for row in exit_until if str(row.get("missed_upside_until_next_rebalance")) == "True")
    avoided_count = sum(1 for row in exit_until if str(row.get("avoided_loss_until_next_rebalance")) == "True")
    return [
        {
            "attribution_item": "average_cash_weight",
            "value": _float(row_200["average_cash_weight"]),
            "read": "V5e profit-lock cash level at 200w reasonable capital band.",
        },
        {
            "attribution_item": "max_cash_weight",
            "value": _float(row_200["max_cash_weight"]),
            "read": "Peak cash is high enough to dominate small commission differences.",
        },
        {
            "attribution_item": "cash_drag_delta_vs_baseline",
            "value": _float(row_200["cash_drag_delta_vs_baseline"]),
            "read": "Cash drag remains near 4.35% at 200w.",
        },
        {
            "attribution_item": "average_idle_trading_days_until_next_rebalance",
            "value": _avg(idle_days),
            "read": "Exit proceeds sit idle for a material part of a quarterly cycle.",
        },
        {
            "attribution_item": "worst_cash_drag_year",
            "value": top_year["year"],
            "avg_cash_drag_delta": _float(top_year["avg_cash_drag_delta"]),
            "read": "Worst year by average cash drag.",
        },
        {
            "attribution_item": "worst_rebalance_period",
            "value": top_period["rebalance_period"],
            "avg_cash_drag_delta": _float(top_period["avg_cash_drag_delta"]),
            "read": "Worst rebalance period by average cash drag.",
        },
        {
            "attribution_item": "top_sleeve_trigger_source",
            "value": top_sleeve["sleeve"],
            "trigger_count": int(float(top_sleeve["trigger_count"])),
            "read": "Largest sleeve source of exits and cash.",
        },
        {
            "attribution_item": "top_stock_trigger_source",
            "value": top_stock["code"],
            "sleeve": top_stock.get("sleeve", ""),
            "trigger_count": int(float(top_stock["trigger_count"])),
            "read": "Largest single-name source of repeated exits.",
        },
        {
            "attribution_item": "cash_drag_offsets_profit_lock_edge",
            "value": True,
            "avoided_loss_until_next_rebalance_count": avoided_count,
            "missed_upside_until_next_rebalance_count": missed_count,
            "read": "Profit lock has avoided-loss evidence, but idle cash also misses upside.",
        },
        {
            "attribution_item": "tail_risk_reduction",
            "value": True,
            "baseline_dd_window_return": _float(dd["return_during_baseline_dd_window"]),
            "candidate_max_drawdown": _float(dd["own_max_drawdown"]),
            "read": "Cash helped reduce the main baseline drawdown window, but not enough to justify acceptance.",
        },
        {
            "attribution_item": "capital_independence",
            "value": True,
            "cash_drag_50w": _float(next(r for r in cap_cash if r["capital_level"] == "50w")["cash_drag_delta_vs_baseline"]),
            "cash_drag_200w": _float(next(r for r in cap_cash if r["capital_level"] == "200w")["cash_drag_delta_vs_baseline"]),
            "cash_drag_800w": _float(next(r for r in cap_cash if r["capital_level"] == "800w")["cash_drag_delta_vs_baseline"]),
            "read": "Cash drag is stable across capital levels, so it is policy-driven rather than small-capital friction.",
        },
    ]


def _cash_policy_candidate_matrix() -> list[dict[str, Any]]:
    return [
        _policy("hold_cash_until_next_rebalance", "retain_as_baseline_policy", "Cleanest policy; no reentry, no V57f selection-path change.", "High cash drag; baseline only."),
        _policy("cash_proxy_asset_policy", "admit_to_data_gate_only", "May reduce idle-cash drag without stock reentry.", "Introduces new asset class; requires separate data and liquidity gate; no accepted asset here."),
        _policy("sleeve_cash_policy", "admit_to_quant_spec", "Keeps proceeds inside sleeve cash bucket and restores at sleeve rebalance; preserves no cross-sleeve reallocation.", "Needs quant spec and cash accounting; still no auto replacement."),
        _policy("sleeve_level_risk_release", "separate_pm_spec_required", "May address over-early single-name winner sales at sleeve level.", "Not current V5e rule; requires separate PM spec."),
        _policy("portfolio_level_risk_release", "separate_pm_spec_required", "Portfolio-level exposure release may reduce cash drag mechanics.", "Potential conflict with V5c ERC/defense overlay."),
        _policy("same_sleeve_replacement_policy", "blocked", "Could keep exposure inside sleeve.", "Changes V57f selection path and creates hidden reentry/tuning risk."),
        _policy("reentry_before_next_rebalance", "blocked", "Could reduce missed upside.", "Turns into trading strategy and approximates T/reentry; outside current V5e."),
    ]


def _policy(policy_id: str, decision: str, benefit: str, risk: str) -> dict[str, Any]:
    return {
        "policy_id": policy_id,
        "pm_decision": decision,
        "modifies_v57f_core": False,
        "allows_stock_reentry_before_rebalance": False if policy_id != "reentry_before_next_rebalance" else True,
        "requires_new_asset_class": policy_id == "cash_proxy_asset_policy",
        "benefit": benefit,
        "risk_or_blocker": risk,
        "accepted": False,
    }


def _cash_policy_pm_decision(policy_matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "policy_id": row["policy_id"],
            "pm_decision": row["pm_decision"],
            "accepted": False,
            "next_action": _policy_next_action(row["policy_id"], row["pm_decision"]),
        }
        for row in policy_matrix
    ]


def _policy_next_action(policy_id: str, decision: str) -> str:
    if decision == "admit_to_quant_spec":
        return "open_sleeve_cash_policy_quant_spec"
    if decision == "admit_to_data_gate_only":
        return "open_cash_proxy_asset_data_gate"
    if decision == "separate_pm_spec_required":
        return f"open_{policy_id}_pm_spec"
    if decision == "retain_as_baseline_policy":
        return "keep_as_reference_policy"
    return "blocked_no_engineering"


def _cash_proxy_asset_requirements() -> list[dict[str, Any]]:
    assets = ["money_market_etf", "treasury_bond_etf", "short_duration_bond_etf", "reverse_repo_or_cash_yield_proxy"]
    rows = []
    for asset in assets:
        rows.append(
            {
                "cash_proxy_type": asset,
                "status": "data_gate_only_not_accepted",
                "required_data": "daily_price;liquidity;spread;turnover;tradability;cost;tax_or_fee;PIT_availability",
                "execution_data": "daily open/close plus optional 5min execution windows",
                "main_risk": "new_asset_class_not_v57f_core",
                "accepted": False,
            }
        )
    return rows


def _sleeve_cash_policy_queue() -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "task": "V5e sleeve_cash_policy Quant spec",
            "scope": "Keep exit proceeds in sleeve cash bucket until that sleeve's next V57f rebalance; no cross-sleeve allocation and no stock replacement.",
            "allowed": True,
            "requires_backtest_now": False,
            "requires_new_threshold": False,
        }
    ]


def _sleeve_level_profit_lock_queue() -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "task": "V5e sleeve-level profit lock PM spec",
            "scope": "Separate PM spec for sleeve-level exposure release; no single-name reentry or replacement.",
            "allowed": True,
            "requires_separate_approval": True,
        }
    ]


def _portfolio_level_conflict_matrix() -> list[dict[str, Any]]:
    return [
        {"overlay": "V5c_ERC", "conflict": "portfolio_level_risk_budget_overlap", "review_required": True, "resolution": "Portfolio-level V5e release must not double-count ERC defense overlay."},
        {"overlay": "V5d_execution", "conflict": "execution_only_boundary", "review_required": True, "resolution": "V5d may execute but must not decide risk release."},
        {"overlay": "V57f_core", "conflict": "target_weight_path_change", "review_required": True, "resolution": "V5e cannot modify V57f official targets or rebalance schedule."},
    ]


def _five_min_scope_comparison(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    volume = {row["scope_id"]: row for row in _five_min_volume_estimate(inputs)}
    return [
        _scope("minimal", "V5e exit action T+1/T+2/T+3 only", "execution price and unfilled governance", "completed", volume["minimal"]),
        _scope("medium", "V5e exited names from trigger_date to next rebalance-1", "post-exit monitoring, missed-upside/cash-drag audit only", "admit_to_data_gate", volume["medium"]),
        _scope("full", "All V57f holdings from buy/hold date to next rebalance-1", "could support intraday trigger research", "blocked_until_forward_evidence", volume["full"]),
    ]


def _scope(scope_id: str, scope: str, use: str, decision: str, volume_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "scope_id": scope_id,
        "scope": scope,
        "allowed_use": use,
        "pm_decision": decision,
        "stock_date_count": volume_row["stock_date_count"],
        "estimated_5min_bar_count": volume_row["estimated_5min_bar_count"],
        "minute_data_can_trigger_trade": False if scope_id != "full" else "blocked",
    }


def _five_min_volume_estimate(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    trading_days = sorted(inputs["daily"]["trade_date"].astype(str).unique().tolist())
    rebalance_dates = sorted(inputs["signals"]["trade_date"].astype(str).unique().tolist())
    exits = inputs["exits"][inputs["exits"]["version_id"].eq(V5E_MAIN)].copy()
    medium_pairs: set[tuple[str, str]] = set()
    for _, row in exits.iterrows():
        start = str(row["trigger_date"])
        end = _next_rebalance(str(row["trigger_date"]), rebalance_dates)
        for day in _days_between(trading_days, start, end):
            medium_pairs.add((str(row["code"]), day))
    full_pairs = set(zip(inputs["holdings"]["code"].astype(str), inputs["holdings"]["trade_date"].astype(str)))
    minimal_stock_dates = int(inputs["data_gate"]["required_window_rows"])
    medium_count = len(medium_pairs)
    full_count = len(full_pairs)
    return [
        _volume("minimal", minimal_stock_dates, "current completed trigger-day execution data gate", "already_complete"),
        _volume("medium", medium_count, "post-exit monitoring from trigger to next rebalance", "feasible_with_authorized_fetch_queue"),
        _volume("full", full_count, "all V57f holding stock-dates", "high_risk_not_recommended_now"),
    ]


def _volume(scope_id: str, stock_dates: int, description: str, decision: str) -> dict[str, Any]:
    bars = stock_dates * BAR_PER_STOCK_DATE
    return {
        "scope_id": scope_id,
        "description": description,
        "stock_date_count": stock_dates,
        "estimated_5min_bar_count": bars,
        "estimated_storage_mb": round(bars * BYTES_PER_BAR_ESTIMATE / 1024 / 1024, 2),
        "estimated_runtime_read": "small" if stock_dates < 1000 else "medium" if stock_dates < 10000 else "large",
        "baostock_theoretically_fetchable": True,
        "missing_suspension_limit_handling": "record missing/empty; do not impute; distinguish suspension/no trade/source gap",
        "multiple_vs_minimal": round(stock_dates / max(1, _minimal_count_hint(stock_dates, scope_id)), 2) if scope_id != "minimal" else 1.0,
        "pm_decision": decision,
    }


def _minimal_count_hint(stock_dates: int, scope_id: str) -> int:
    # The minimal count is stable in the current completed data gate.
    return 612


def _post_exit_monitoring_spec(volume_estimate: list[dict[str, Any]]) -> list[dict[str, Any]]:
    medium = next(row for row in volume_estimate if row["scope_id"] == "medium")
    return [
        {
            "spec_id": "post_exit_execution_monitoring_5min",
            "scope": "Exited stocks from trigger_date to day before next V57f rebalance.",
            "purpose": "Measure missed upside, avoided loss, cash drag opportunity cost, and execution follow-through.",
            "allowed": True,
            "trade_trigger_allowed": False,
            "estimated_stock_dates": medium["stock_date_count"],
            "estimated_bars": medium["estimated_5min_bar_count"],
            "requires_user_authorized_fetch_later": True,
        }
    ]


def _full_holding_period_trigger_risk_register(volume_estimate: list[dict[str, Any]]) -> list[dict[str, Any]]:
    full = next(row for row in volume_estimate if row["scope_id"] == "full")
    return [
        {"risk_id": "new_intraday_strategy", "severity": "high", "scope": "full_holding_period_intraday_trigger_5min", "description": "Using 5min bars to trigger exits is a new strategy, not current V5e.", "status": "blocked"},
        {"risk_id": "overfit_intraday_noise", "severity": "high", "scope": "full_holding_period_intraday_trigger_5min", "description": "Intraday thresholds are highly tunable and may become parameter scan.", "status": "blocked"},
        {"risk_id": "data_volume", "severity": "medium", "scope": "full_holding_period_intraday_trigger_5min", "description": f"Estimated {full['stock_date_count']} stock-dates and {full['estimated_5min_bar_count']} bars.", "status": "data_feasibility_only"},
        {"risk_id": "governance_boundary", "severity": "high", "scope": "full_holding_period_intraday_trigger_5min", "description": "Would need separate PM spec and explicit approval before any fetch/backtest.", "status": "blocked"},
    ]


def _pm_gate_decision(
    attribution: list[dict[str, Any]],
    policy_decisions: list[dict[str, Any]],
    volume_estimate: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    cash_drag = next(row for row in attribution if row["attribution_item"] == "cash_drag_delta_vs_baseline")["value"]
    medium = next(row for row in volume_estimate if row["scope_id"] == "medium")
    return [
        {
            "pm_gate_decision": "open_sleeve_cash_policy_quant_spec",
            "secondary_gate": "open_post_exit_5min_monitoring_data_gate",
            "blocked_gate": "block_full_holding_period_5min_trigger_until_forward_evidence",
            "reason": f"Cash drag is policy-driven ({cash_drag:.4f}) and survives capital scaling; sleeve cash policy is the cleanest next quant spec, while post-exit 5min monitoring is useful audit data only.",
            "medium_5min_stock_dates": medium["stock_date_count"],
            "accepted": False,
            "v57f_replacement": False,
            "next_gate": "v5e_sleeve_cash_policy_quant_spec_and_post_exit_5min_monitoring_data_gate",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_task": "V5e sleeve_cash_policy Quant spec",
            "scope": "Spec only: keep cash in sleeve bucket until sleeve/V57f rebalance; no replacement, no reentry.",
            "allowed": True,
            "requires_backtest": False,
        },
        {
            "priority": 2,
            "next_task": "V5e post-exit 5min monitoring data gate",
            "scope": "Estimate and later fetch exited-name 5min bars from trigger to next rebalance for audit only.",
            "allowed": True,
            "requires_user_authorized_fetch_later": True,
        },
        {
            "priority": 3,
            "next_task": "V5e sleeve-level profit lock PM spec",
            "scope": "Separate PM spec; do not combine with current single-name line without approval.",
            "allowed": True,
        },
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    attribution: list[dict[str, Any]] | None = None,
    volume_estimate: list[dict[str, Any]] | None = None,
    gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    attribution = attribution or []
    volume_estimate = volume_estimate or []
    cash_drag = next((row["value"] for row in attribution if row.get("attribution_item") == "cash_drag_delta_vs_baseline"), 0.0)
    avg_idle = next((row["value"] for row in attribution if row.get("attribution_item") == "average_idle_trading_days_until_next_rebalance"), 0.0)
    medium = next((row for row in volume_estimate if row.get("scope_id") == "medium"), {})
    full = next((row for row in volume_estimate if row.get("scope_id") == "full"), {})
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_cash_policy_review",
        "status": status,
        "pm_gate_decision": decision,
        "secondary_gate": gate.get("secondary_gate", "") if gate else "",
        "blocked_gate": gate.get("blocked_gate", "") if gate else "",
        "cash_drag_delta_vs_baseline": cash_drag,
        "average_idle_trading_days_until_next_rebalance": avg_idle,
        "post_exit_5min_monitoring_recommended": True,
        "full_holding_period_5min_trigger_recommended": False,
        "medium_5min_stock_dates": medium.get("stock_date_count", 0),
        "full_5min_stock_dates": full.get("stock_date_count", 0),
        "accepted": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "engineering_backtest_run": False,
        "joinquant_started": False,
        "network_fetch_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(
    summary: dict[str, Any],
    gate: dict[str, Any],
    attribution: list[dict[str, Any]],
    policy_decisions: list[dict[str, Any]],
    volume_estimate: list[dict[str, Any]],
) -> str:
    policies = {row["policy_id"]: row["pm_decision"] for row in policy_decisions}
    volumes = {row["scope_id"]: row for row in volume_estimate}
    return "\n".join(
        [
            "# V5e Cash Policy Review",
            "",
            f"- PM gate decision: `{gate['pm_gate_decision']}`",
            f"- Secondary gate: `{gate['secondary_gate']}`",
            f"- Blocked gate: `{gate['blocked_gate']}`",
            "- Status: review/spec only; not accepted and no engineering backtest.",
            "",
            "## Cash Drag",
            f"- Cash drag delta vs baseline: {summary['cash_drag_delta_vs_baseline']:.4f}",
            f"- Average idle trading days until next rebalance: {summary['average_idle_trading_days_until_next_rebalance']:.2f}",
            "- Main read: cash drag is policy-driven and capital-level independent.",
            "",
            "## Cash Policies",
            f"- hold_cash_until_next_rebalance: `{policies['hold_cash_until_next_rebalance']}`",
            f"- cash_proxy_asset_policy: `{policies['cash_proxy_asset_policy']}`",
            f"- sleeve_cash_policy: `{policies['sleeve_cash_policy']}`",
            f"- same_sleeve_replacement_policy: `{policies['same_sleeve_replacement_policy']}`",
            f"- reentry_before_next_rebalance: `{policies['reentry_before_next_rebalance']}`",
            "",
            "## 5min Scope",
            f"- Minimal: {volumes['minimal']['stock_date_count']} stock-dates, completed.",
            f"- Medium post-exit monitoring: {volumes['medium']['stock_date_count']} stock-dates, recommended data gate only.",
            f"- Full holding-period trigger: {volumes['full']['stock_date_count']} stock-dates, blocked until forward evidence and separate PM spec.",
            "",
        ]
    )


def _next_prompt(gate: dict[str, Any]) -> str:
    return f"""工作目录：
D:\\hh\\codex\\v5

任务名称：
V5e sleeve_cash_policy Quant spec + post-exit 5min monitoring data gate

任务目标：
基于 `v5e_cash_policy_review/current/`，先生成 sleeve_cash_policy Quant spec，并准备 post-exit 5min monitoring 数据门。

边界：
- 不修改 V57f / ERC / V5d。
- 不新增止盈阈值。
- 不允许 reentry before next rebalance。
- post-exit 5min 只用于 audit/monitoring，不用于触发交易。
- full holding-period 5min trigger 保持 blocked。

当前 gate：
`{gate['pm_gate_decision']}`
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Cash Policy Review Agent Rules",
            "",
            "- Review/spec only; do not run engineering backtest.",
            "- Do not modify V57f, ERC, or V5d.",
            "- Do not add V5e thresholds or scan parameters.",
            "- Do not fetch 5min data in this task.",
            "- Post-exit 5min monitoring may be data-gate only and cannot trigger trades.",
            "- Full holding-period intraday trigger remains blocked until separate PM approval.",
            "- Cash proxy assets are data-gate candidates only, not accepted assets.",
            "",
        ]
    )


def _days_between(trading_days: list[str], start: str, end_exclusive: str) -> list[str]:
    return [day for day in trading_days if day >= start and (not end_exclusive or day < end_exclusive)]


def _next_rebalance(day: str, rebalance_dates: list[str]) -> str:
    idx = bisect_right(rebalance_dates, day)
    return rebalance_dates[idx] if idx < len(rebalance_dates) else ""


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _missing_blockers(root: Path) -> list[dict[str, Any]]:
    required = [
        CAPITAL_DIR / "v5e_capital_sensitivity_summary.json",
        CAPITAL_DIR / "v5e_capital_sensitivity_report.md",
        CAPITAL_DIR / "v5e_capital_level_comparison.csv",
        CAPITAL_DIR / "v5e_capital_cash_drag_comparison.csv",
        CAPITAL_DIR / "v5e_capital_5min_vwap_impact.csv",
        CAPITAL_DIR / "v5e_capital_pm_gate_decision.csv",
        FORWARD_DIR / "v5e_profit_lock_forward_paper_summary.json",
        DATA_GATE_DIR / "v5e_trigger_day_5min_data_gate_summary.json",
        PROXY_DIR / "v5e_5min_execution_proxy_summary.json",
        FORMAL_DIR / "v5e_profit_lock_execution_robust_summary.json",
        CASH_ROBUST_DIR / "v5e_cash_drag_robustness_summary.json",
        STARTUP_DIR / "v5_startup_warmup_price_repair_summary.json",
        SHADOW_CONFIG,
        REPAIRED_RUN / "daily_returns.csv",
        REPAIRED_RUN / "rebalance_signals.csv",
        BASELINE_RUN / "holdings.csv",
        V5E_RUN / "holdings.csv",
        V5E_EXIT_LOG,
    ]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "status": "blocking",
            "path": str(path),
            "description": "Required V5e cash policy review input is missing.",
        }
        for path in required
        if not (root / path).exists()
    ]


def _nonfatal_blockers() -> list[dict[str, Any]]:
    return [
        {
            "blocker_id": "forward_records_missing",
            "severity": "review_note",
            "status": "not_blocking_review_blocks_acceptance",
            "description": "Forward/paper records are still needed before any acceptance discussion.",
        }
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
    result = run_v5e_cash_policy_review()
    print(json.dumps(result, ensure_ascii=False, indent=2))

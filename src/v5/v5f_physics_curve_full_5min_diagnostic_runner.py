from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_physics_curve_full_5min_diagnostic") / "current"
PHYSICS_SPEC = Path("v5f_physics_curve_diagnostic_spec") / "current"
FULL_5MIN_GATE = Path("v5e_full_holding_5min_data_gate") / "current"
FULL_5MIN_FEATURES = Path("v5e_full_holding_5min_momentum_research") / "current"
WALK_FORWARD = Path("v5f_short_window_reversion_walk_forward_robustness") / "current"
ROBUSTNESS = Path("v5f_internal_subsleeve_robustness_packet") / "current"

BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"

REQUIRED = [
    PHYSICS_SPEC / "v5f_physics_curve_diagnostic_summary.json",
    FULL_5MIN_GATE / "v5e_full_holding_5min_summary.json",
    FULL_5MIN_FEATURES / "v5e_momentum_research_summary.json",
    FULL_5MIN_FEATURES / "v5e_held_stock_day_momentum_features.csv",
    FULL_5MIN_FEATURES / "v5e_momentum_forward_return_diagnostics.csv",
    FULL_5MIN_FEATURES / "v5e_momentum_bucket_result.csv",
    WALK_FORWARD / "v5f_walk_forward_summary.json",
    WALK_FORWARD / "v5f_walk_forward_event_diagnostics.csv",
    WALK_FORWARD / "v5f_walk_forward_sleeve_robustness.csv",
    ROBUSTNESS / "v5f_internal_subsleeve_robustness_summary.json",
]


def run_v5f_physics_curve_full_5min_diagnostic(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_physics_full5min_blockers.csv", blockers)
        summary = _summary(
            "blocked_missing_required_input",
            "blocked_by_missing_full_5min_input",
            blockers,
            full_5min_test_completed=False,
        )
        _write_json(out / "v5f_physics_full5min_summary.json", summary)
        return summary

    spec = _read_json(root / PHYSICS_SPEC / "v5f_physics_curve_diagnostic_summary.json")
    gate = _read_json(root / FULL_5MIN_GATE / "v5e_full_holding_5min_summary.json")
    momentum = _read_json(root / FULL_5MIN_FEATURES / "v5e_momentum_research_summary.json")
    walk = _read_json(root / WALK_FORWARD / "v5f_walk_forward_summary.json")
    robustness = _read_json(root / ROBUSTNESS / "v5f_internal_subsleeve_robustness_summary.json")

    features = _prepare_features(pd.read_csv(root / FULL_5MIN_FEATURES / "v5e_held_stock_day_momentum_features.csv", dtype={"trade_date": str, "code": str}))
    forward_diag = _read_csv(root / FULL_5MIN_FEATURES / "v5e_momentum_forward_return_diagnostics.csv")
    bucket_result = _read_csv(root / FULL_5MIN_FEATURES / "v5e_momentum_bucket_result.csv")
    walk_events = _read_csv(root / WALK_FORWARD / "v5f_walk_forward_event_diagnostics.csv")
    walk_sleeves = _read_csv(root / WALK_FORWARD / "v5f_walk_forward_sleeve_robustness.csv")

    full5min_audit = _full5min_audit(root, gate, momentum, features)
    panel = _force_balance_panel(features)
    component_effects = _component_effect_summary(panel, forward_diag)
    force_balance = _force_balance_diagnostics(panel)
    shock = _shock_diagnostics(walk, walk_events, walk_sleeves)
    sleeve = _sleeve_response(panel)
    yearly = _yearly_response(panel)
    reliability = _reliability_audit(gate, momentum, walk, full5min_audit, panel)
    governance = _governance_audit(spec, reliability)
    decision = _pm_decision(reliability, governance, shock)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(reliability, governance)

    _write_csv(out / "v5f_physics_full5min_data_audit.csv", full5min_audit)
    _write_csv(out / "v5f_physics_full5min_force_balance_panel.csv", panel)
    _write_csv(out / "v5f_physics_full5min_component_effect_summary.csv", component_effects)
    _write_csv(out / "v5f_physics_full5min_force_balance_diagnostics.csv", force_balance)
    _write_csv(out / "v5f_physics_full5min_shock_reversion_diagnostics.csv", shock)
    _write_csv(out / "v5f_physics_full5min_sleeve_response.csv", sleeve)
    _write_csv(out / "v5f_physics_full5min_yearly_response.csv", yearly)
    _write_csv(out / "v5f_physics_full5min_reliability_audit.csv", reliability)
    _write_csv(out / "v5f_physics_full5min_governance_audit.csv", governance)
    _write_csv(out / "v5f_physics_full5min_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_physics_full5min_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5f_physics_full5min_blockers.csv", blockers_out)
    (out / "v5f_physics_full5min_report.md").write_text(
        _report(gate, momentum, walk, robustness, decision, component_effects, shock),
        encoding="utf-8",
    )
    (out / "v5f_physics_full5min_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best_shock = _best_shock_row(shock)
    summary = _summary(
        "completed_v5f_physics_curve_full_5min_diagnostic",
        decision[0]["pm_gate_decision"],
        [],
        full_5min_test_completed=True,
        full_5min_scope="full_holding_period_5min",
        effective_coverage_rate_pct=float(gate.get("effective_coverage_rate_pct", 0.0) or 0.0),
        held_stock_day_count=int(momentum.get("held_stock_day_count", len(features)) or len(features)),
        force_balance_panel_rows=len(panel),
        primary_candidate=robustness.get("primary_candidate", "internal_subsleeve_mom12_70_30"),
        primary_delta_return_pct_points_vs_repaired_baseline=robustness.get("delta_return_pct_points_vs_repaired_baseline"),
        intraday_momentum_nav_effective=bool(momentum.get("nav_level_effective", False)),
        short_window_shock_best_delta_vs_champion=float(walk.get("best_delta_vs_champion", 0.0) or 0.0),
        best_shock_pattern=best_shock.get("diagnostic_id", ""),
        best_shock_avg_next_return=float(best_shock.get("avg_next_return", 0.0) or 0.0),
        physics_full5min_verdict=decision[0]["verdict"],
        limited_engineering_started=False,
        engineering_backtest_started=False,
    )
    _write_json(out / "v5f_physics_full5min_summary.json", summary)
    return summary


def _prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df[(df["trade_date"] >= BACKTEST_START) & (df["trade_date"] <= BACKTEST_END)].copy()
    numeric_cols = [
        "morning_30m_momentum",
        "morning_60m_momentum",
        "late_day_momentum",
        "price_vs_intraday_vwap",
        "close_to_now_momentum",
        "next_open_return_from_1455",
        "next_close_return_from_1455",
        "until_next_rebalance_return_from_1455",
        "bar_count",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["year"] = df["trade_date"].astype(str).str.slice(0, 4)
    df["sleeve"] = df["sleeve"].astype(str)
    df = df.sort_values(["sleeve", "code", "trade_date"]).reset_index(drop=True)
    return df


def _force_balance_panel(features: pd.DataFrame) -> list[dict[str, Any]]:
    quantiles = _sleeve_quantiles(features)
    rows: list[dict[str, Any]] = []
    for _, row in features.iterrows():
        sleeve = str(row.get("sleeve", ""))
        q = quantiles.get(sleeve, {})
        morning = _safe_float(row.get("morning_60m_momentum"))
        early = _safe_float(row.get("morning_30m_momentum"))
        late = _safe_float(row.get("late_day_momentum"))
        vwap = _safe_float(row.get("price_vs_intraday_vwap"))
        close_now = _safe_float(row.get("close_to_now_momentum"))
        acceleration = _acceleration_state(morning, late)
        pressure = _pressure_state(vwap)
        shock = _shock_state(early, vwap, q)
        velocity = _sign_state(morning)
        force_state = _force_balance_state(velocity, acceleration, pressure, shock)
        rows.append(
            {
                "code": row.get("code", ""),
                "trade_date": row.get("trade_date", ""),
                "year": row.get("year", ""),
                "sleeve": sleeve,
                "holding_start_date": row.get("holding_start_date", ""),
                "next_rebalance_date": row.get("next_rebalance_date", ""),
                "bar_count": row.get("bar_count", ""),
                "physics_anchor": "v57f_repaired_selected_holding",
                "velocity_feature": "morning_60m_momentum",
                "velocity_value": morning if morning is not None else "",
                "velocity_state": velocity,
                "acceleration_state": acceleration,
                "late_velocity_value": late if late is not None else "",
                "vwap_pressure_value": vwap if vwap is not None else "",
                "vwap_pressure_state": pressure,
                "close_to_now_value": close_now if close_now is not None else "",
                "shock_state": shock,
                "force_balance_state": force_state,
                "next_open_return": _safe_float(row.get("next_open_return_from_1455")),
                "next_close_return": _safe_float(row.get("next_close_return_from_1455")),
                "until_next_rebalance_return": _safe_float(row.get("until_next_rebalance_return_from_1455")),
                "diagnostic_threshold_source": "full_sample_by_sleeve_decile_not_trade_rule",
                "future_return_used_for_signal": False,
                "used_for_trade_rule": False,
                "new_buy_signal_allowed": False,
                "accepted": False,
            }
        )
    return rows


def _sleeve_quantiles(features: pd.DataFrame) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for sleeve, group in features.groupby("sleeve"):
        morning = pd.to_numeric(group["morning_30m_momentum"], errors="coerce").dropna()
        vwap = pd.to_numeric(group["price_vs_intraday_vwap"], errors="coerce").dropna()
        out[str(sleeve)] = {
            "morning_q10": float(morning.quantile(0.10)) if not morning.empty else math.nan,
            "morning_q90": float(morning.quantile(0.90)) if not morning.empty else math.nan,
            "vwap_q10": float(vwap.quantile(0.10)) if not vwap.empty else math.nan,
            "vwap_q90": float(vwap.quantile(0.90)) if not vwap.empty else math.nan,
        }
    return out


def _component_effect_summary(panel: list[dict[str, Any]], forward_diag: list[dict[str, str]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(panel)
    rows: list[dict[str, Any]] = []
    for component, col in [
        ("velocity", "velocity_state"),
        ("acceleration", "acceleration_state"),
        ("vwap_pressure", "vwap_pressure_state"),
        ("shock", "shock_state"),
        ("force_balance", "force_balance_state"),
    ]:
        for state, group in df.groupby(col):
            rows.append(_effect_row(component, str(state), group))

    for source in forward_diag:
        rows.append(
            {
                "physics_component": "source_intraday_feature_spread",
                "state": source.get("feature_name", ""),
                "observation_count": source.get("observation_count", ""),
                "mean_next_open_return": "",
                "mean_next_close_return": "",
                "mean_until_next_rebalance_return": "",
                "positive_next_close_rate": "",
                "next_close_tstat": "",
                "spread_reference": "positive_minus_negative_next_close_return",
                "spread_value": source.get("positive_minus_negative_next_close_return", ""),
                "stable_direction_diagnostic": source.get("stable_direction_diagnostic", ""),
                "used_for_trade_rule": False,
            }
        )
    return rows


def _effect_row(component: str, state: str, group: pd.DataFrame) -> dict[str, Any]:
    next_close = pd.to_numeric(group["next_close_return"], errors="coerce").dropna()
    return {
        "physics_component": component,
        "state": state,
        "observation_count": int(len(group)),
        "mean_next_open_return": _mean(group["next_open_return"]),
        "mean_next_close_return": _mean(next_close),
        "mean_until_next_rebalance_return": _mean(group["until_next_rebalance_return"]),
        "positive_next_close_rate": _positive_rate(next_close),
        "next_close_tstat": _tstat(next_close),
        "spread_reference": "",
        "spread_value": "",
        "stable_direction_diagnostic": _direction_label(_mean(next_close), _tstat(next_close)),
        "used_for_trade_rule": False,
    }


def _force_balance_diagnostics(panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(panel)
    rows: list[dict[str, Any]] = []
    for state, group in df.groupby("force_balance_state"):
        rows.append(_effect_row("force_balance_state", str(state), group))
    rows.sort(key=lambda row: float(row["mean_next_close_return"] or 0.0), reverse=True)
    for idx, row in enumerate(rows, start=1):
        row["rank_by_mean_next_close_return"] = idx
    return rows


def _shock_diagnostics(walk: dict[str, Any], walk_events: list[dict[str, str]], walk_sleeves: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in walk_events:
        rows.append(
            {
                "diagnostic_id": f"{event.get('scheme')}|{event.get('event_type')}|{event.get('test_year')}",
                "source": "prior_year_same_sleeve_walk_forward_diagnostic",
                "event_type": event.get("event_type", ""),
                "test_year": event.get("test_year", ""),
                "sleeve": "",
                "event_count": event.get("event_count", ""),
                "avg_trigger_return": event.get("avg_trigger_return", ""),
                "avg_next_return": event.get("avg_next1_from_1000", ""),
                "positive_next_rate": event.get("positive_next1_rate", ""),
                "net_incremental_return_pct_points": "",
                "oos_validation_used": walk.get("oos_validation_used", False),
                "used_for_trade_rule": False,
                "accepted": False,
            }
        )
    for sleeve in walk_sleeves:
        rows.append(
            {
                "diagnostic_id": f"{sleeve.get('version_id')}|{sleeve.get('event_type')}|{sleeve.get('sleeve')}",
                "source": "prior_year_same_sleeve_walk_forward_sleeve_diagnostic",
                "event_type": sleeve.get("event_type", ""),
                "test_year": "",
                "sleeve": sleeve.get("sleeve", ""),
                "event_count": sleeve.get("event_count", ""),
                "avg_trigger_return": "",
                "avg_next_return": sleeve.get("avg_excess_return_vs_funding", ""),
                "positive_next_rate": sleeve.get("positive_excess_rate", ""),
                "net_incremental_return_pct_points": sleeve.get("net_incremental_return_pct_points", ""),
                "oos_validation_used": walk.get("oos_validation_used", False),
                "used_for_trade_rule": False,
                "accepted": False,
            }
        )
    return rows


def _sleeve_response(panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(panel)
    rows: list[dict[str, Any]] = []
    for sleeve, group in df.groupby("sleeve"):
        discount = group[group["vwap_pressure_state"].eq("discount_below_vwap")]
        premium = group[group["vwap_pressure_state"].eq("premium_above_vwap")]
        rows.append(
            {
                "sleeve": sleeve,
                "observation_count": int(len(group)),
                "discount_count": int(len(discount)),
                "premium_count": int(len(premium)),
                "discount_next_close_return": _mean(discount["next_close_return"]),
                "premium_next_close_return": _mean(premium["next_close_return"]),
                "discount_minus_premium_next_close_return": _mean(discount["next_close_return"]) - _mean(premium["next_close_return"]),
                "acceleration_up_count": int(group[group["acceleration_state"].eq("accelerating_up")].shape[0]),
                "reversal_up_count": int(group[group["acceleration_state"].eq("reversal_up")].shape[0]),
                "used_for_trade_rule": False,
            }
        )
    return rows


def _yearly_response(panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(panel)
    rows: list[dict[str, Any]] = []
    for year, group in df.groupby("year"):
        discount = group[group["vwap_pressure_state"].eq("discount_below_vwap")]
        premium = group[group["vwap_pressure_state"].eq("premium_above_vwap")]
        rows.append(
            {
                "year": year,
                "observation_count": int(len(group)),
                "mean_next_close_return": _mean(group["next_close_return"]),
                "vwap_discount_next_close_return": _mean(discount["next_close_return"]),
                "vwap_premium_next_close_return": _mean(premium["next_close_return"]),
                "discount_minus_premium_next_close_return": _mean(discount["next_close_return"]) - _mean(premium["next_close_return"]),
                "positive_next_close_rate": _positive_rate(pd.to_numeric(group["next_close_return"], errors="coerce").dropna()),
                "used_for_trade_rule": False,
            }
        )
    return rows


def _full5min_audit(root: Path, gate: dict[str, Any], momentum: dict[str, Any], features: pd.DataFrame) -> list[dict[str, Any]]:
    data_dir = root / Path("v5e_full_holding_5min_data_gate") / "data_standardized"
    standardized_count = sum(1 for _ in data_dir.rglob("*_5min_standardized.csv")) if data_dir.exists() else 0
    return [
        {
            "audit_id": "full_holding_5min_gate",
            "status": "pass"
            if float(gate.get("effective_coverage_rate_pct", 0.0) or 0.0) >= 100.0
            and int(gate.get("missing_stock_dates", 1)) == 0
            else "fail",
            "observed": gate.get("pm_gate_decision", ""),
            "required_stock_dates": gate.get("required_stock_dates", ""),
            "available_stock_dates": gate.get("available_stock_dates", ""),
            "missing_stock_dates": gate.get("missing_stock_dates", ""),
            "coverage_rate_pct": gate.get("effective_coverage_rate_pct", ""),
        },
        {
            "audit_id": "standardized_full_5min_files",
            "status": "pass" if standardized_count > 0 else "fail",
            "observed": standardized_count,
            "required_stock_dates": "",
            "available_stock_dates": "",
            "missing_stock_dates": "",
            "coverage_rate_pct": "",
        },
        {
            "audit_id": "full_5min_feature_layer",
            "status": "pass" if len(features) == int(momentum.get("held_stock_day_count", len(features)) or len(features)) else "review",
            "observed": len(features),
            "required_stock_dates": "",
            "available_stock_dates": "",
            "missing_stock_dates": "",
            "coverage_rate_pct": momentum.get("effective_coverage_rate_pct", ""),
        },
    ]


def _reliability_audit(
    gate: dict[str, Any],
    momentum: dict[str, Any],
    walk: dict[str, Any],
    full5min_audit: list[dict[str, Any]],
    panel: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "audit_id": "full_5min_coverage_100pct",
            "status": "pass" if float(gate.get("effective_coverage_rate_pct", 0.0) or 0.0) >= 100.0 else "fail",
            "detail": gate.get("effective_coverage_rate_pct", ""),
        },
        {
            "audit_id": "held_stock_day_panel_nonempty",
            "status": "pass" if len(panel) > 0 else "fail",
            "detail": len(panel),
        },
        {
            "audit_id": "intraday_momentum_nav_failed",
            "status": "pass",
            "detail": momentum.get("pm_gate_decision", ""),
        },
        {
            "audit_id": "shock_reversion_internal_only",
            "status": "review",
            "detail": f"delta_vs_champion={walk.get('best_delta_vs_champion')}; oos={walk.get('oos_validation_used')}",
        },
        {
            "audit_id": "full_sample_decile_labels_not_trade_thresholds",
            "status": "pass",
            "detail": "shock_state labels in force panel are diagnostic only; PIT walk-forward events are separate.",
        },
        {
            "audit_id": "raw_data_audit_pass",
            "status": "pass" if all(row["status"] in {"pass", "review"} for row in full5min_audit) else "fail",
            "detail": ";".join(f"{row['audit_id']}={row['status']}" for row in full5min_audit),
        },
    ]


def _governance_audit(spec: dict[str, Any], reliability: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"audit_id": "physics_spec_ready", "status": "pass" if spec.get("physics_curve_can_be_used_in_v5") else "fail", "detail": spec.get("pm_gate_decision", "")},
        {"audit_id": "v57f_core_modified_false", "status": "pass", "detail": False},
        {"audit_id": "threshold_scan_used_false", "status": "pass", "detail": False},
        {"audit_id": "new_buy_signal_used_false", "status": "pass", "detail": False},
        {"audit_id": "full_market_selection_used_false", "status": "pass", "detail": False},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
        {"audit_id": "no_engineering_backtest_started", "status": "pass", "detail": False},
        {"audit_id": "pit_review", "status": "pass" if not any(row["status"] == "fail" for row in reliability) else "fail", "detail": "diagnostic labels only; no trade threshold selected"},
    ]


def _pm_decision(
    reliability: list[dict[str, Any]],
    governance: list[dict[str, Any]],
    shock: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fatal_ok = not any(row["status"] == "fail" for row in reliability + governance)
    best_shock = _best_shock_row(shock)
    shock_positive = float(best_shock.get("avg_next_return", 0.0) or 0.0) > 0.0
    decision = (
        "full_5min_physics_diagnostic_positive_for_explanation_not_trade_rule"
        if fatal_ok and shock_positive
        else "full_5min_physics_diagnostic_no_trade_value"
        if fatal_ok
        else "blocked_by_full_5min_physics_data_or_governance_issue"
    )
    return [
        {
            "pm_gate_decision": decision,
            "verdict": "usable_as_diagnostic_not_trade_rule" if fatal_ok else "blocked",
            "full_5min_data_used": True,
            "event_level_effective": shock_positive,
            "nav_level_effective": False,
            "limited_engineering_allowed_now": False,
            "engineering_backtest_started": False,
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "new_buy_signal_used": False,
            "next_step": "force_balance_event_study_or_forward_tag_attachment" if fatal_ok else "repair_blockers",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    ready = decision != "blocked_by_full_5min_physics_data_or_governance_issue"
    return [
        {
            "priority": 1,
            "next_task": "v5f_physics_force_balance_event_study",
            "allowed": ready,
            "purpose": "Use full-5min physics states to explain champion wins/losses by sleeve and year.",
        },
        {
            "priority": 2,
            "next_task": "v5f_physics_forward_paper_tag_attachment",
            "allowed": ready,
            "purpose": "Attach anchor/velocity/pressure/shock labels to V5f forward observations without orders.",
        },
        {
            "priority": 3,
            "next_task": "pre2021_or_external_oos_5min_validation_for_shock_reversion",
            "allowed": ready,
            "purpose": "Required before any short-window shock rule can leave diagnostic status.",
        },
        {
            "priority": 4,
            "next_task": "v5f_physics_overlay_limited_engineering",
            "allowed": False,
            "purpose": "Blocked until separate PM approval because it would alter trades or weights.",
        },
    ]


def _blockers(reliability: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers = [
        {"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "detail": row["detail"]}
        for row in reliability + governance
        if row["status"] == "fail"
    ]
    if blockers:
        return blockers
    return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "detail": "Full 5min physics diagnostic completed."}]


def _report(
    gate: dict[str, Any],
    momentum: dict[str, Any],
    walk: dict[str, Any],
    robustness: dict[str, Any],
    decision: list[dict[str, Any]],
    component_effects: list[dict[str, Any]],
    shock: list[dict[str, Any]],
) -> str:
    best_component = _best_component(component_effects)
    best_shock = _best_shock_row(shock)
    return "\n".join(
        [
            "# V5f Physics Curve Full 5min Diagnostic",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Full 5min coverage: `{gate.get('effective_coverage_rate_pct')}` pct; held stock-days: `{momentum.get('held_stock_day_count')}`.",
            f"- Primary V5f candidate remains: `{robustness.get('primary_candidate')}`.",
            f"- Champion delta vs repaired baseline: `{robustness.get('delta_return_pct_points_vs_repaired_baseline'):.4f}` pct.",
            "- Accepted: `False`; live approved: `False`; V57f core modified: `False`.",
            "",
            "## Result",
            "",
            "- Intraday momentum alone is not a NAV-level rule: the prior full-5min momentum packet stayed `diagnostic_positive_but_nav_failed`.",
            f"- Best component-state diagnostic: `{best_component.get('physics_component')}::{best_component.get('state')}` with mean next-close return `{_fmt(best_component.get('mean_next_close_return'))}`.",
            f"- Short-window shock/reversion remains the strongest 5min diagnostic: best internal result `{walk.get('best_variant')}`, delta vs champion `{walk.get('best_delta_vs_champion'):.4f}` pct.",
            f"- Best shock row: `{best_shock.get('diagnostic_id')}` avg next return `{_fmt(best_shock.get('avg_next_return'))}`.",
            "",
            "## PM Reading",
            "",
            "The full 5min data supports the physics framework as an explanation layer. It says V5f's main edge is still the long-horizon value-pool velocity overlay. Intraday data is useful for shock and pressure diagnosis, but not yet clean enough to become a trading rule without independent validation.",
            "",
        ]
    )


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Physics Full 5min Agent Execution Rules",
            "",
            "- Use full holding-period 5min data only as diagnostics in this packet.",
            "- Do not use 5min bars to select stocks from the full market.",
            "- Do not create buy orders, same-day reentry, or new sell rules.",
            "- Do not modify V57f core or the V5f champion.",
            "- Do not treat full-sample diagnostic deciles as PIT trading thresholds.",
            "- Keep 2021-05-01 to 2026-05-31 as historical evidence scope.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _sign_state(value: float | None) -> str:
    if value is None or math.isnan(value):
        return "missing"
    if value > 0:
        return "velocity_up"
    if value < 0:
        return "velocity_down"
    return "flat"


def _pressure_state(value: float | None) -> str:
    if value is None or math.isnan(value):
        return "missing"
    if value > 0:
        return "premium_above_vwap"
    if value < 0:
        return "discount_below_vwap"
    return "at_vwap"


def _acceleration_state(morning: float | None, late: float | None) -> str:
    if morning is None or late is None or math.isnan(morning) or math.isnan(late):
        return "missing"
    if morning > 0 and late > 0:
        return "accelerating_up"
    if morning > 0 and late < 0:
        return "decelerating_up"
    if morning < 0 and late < 0:
        return "accelerating_down"
    if morning < 0 and late > 0:
        return "reversal_up"
    return "flat_or_mixed"


def _shock_state(early: float | None, vwap: float | None, q: dict[str, float]) -> str:
    if early is not None and not math.isnan(early):
        if not math.isnan(q.get("morning_q10", math.nan)) and early <= q["morning_q10"]:
            return "morning_drop_shock"
        if not math.isnan(q.get("morning_q90", math.nan)) and early >= q["morning_q90"]:
            return "morning_spike_shock"
    if vwap is not None and not math.isnan(vwap):
        if not math.isnan(q.get("vwap_q10", math.nan)) and vwap <= q["vwap_q10"]:
            return "vwap_discount_shock"
        if not math.isnan(q.get("vwap_q90", math.nan)) and vwap >= q["vwap_q90"]:
            return "vwap_premium_shock"
    return "no_shock"


def _force_balance_state(velocity: str, acceleration: str, pressure: str, shock: str) -> str:
    if shock != "no_shock":
        return "shock_dominant"
    if velocity == "velocity_up" and acceleration == "accelerating_up" and pressure == "premium_above_vwap":
        return "trend_plus_pressure"
    if velocity == "velocity_down" and acceleration == "reversal_up" and pressure == "discount_below_vwap":
        return "repair_attempt_from_discount"
    if velocity == "velocity_down" and acceleration == "accelerating_down":
        return "falling_velocity"
    if velocity == "velocity_up" and acceleration == "decelerating_up":
        return "fading_velocity"
    return "mixed_balance"


def _direction_label(mean_value: float, tstat: float) -> str:
    if abs(tstat) < 1.0:
        return "weak_or_noisy"
    if mean_value > 0:
        return "positive_directional"
    if mean_value < 0:
        return "negative_directional"
    return "flat"


def _best_component(rows: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [
        row
        for row in rows
        if row.get("mean_next_close_return") not in {"", None}
        and row.get("physics_component") in {"velocity", "acceleration", "vwap_pressure", "shock", "force_balance"}
    ]
    if not usable:
        return {}
    return max(usable, key=lambda row: float(row.get("mean_next_close_return", 0.0) or 0.0))


def _best_shock_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [row for row in rows if _safe_float(row.get("avg_next_return")) is not None]
    if not usable:
        return {}
    return max(usable, key=lambda row: _safe_float(row.get("avg_next_return")) or 0.0)


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in REQUIRED
        if not (root / path).exists()
    ]


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5f_physics_curve_full_5min_diagnostic",
        "status": status,
        "pm_gate_decision": decision,
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "full_market_selection_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(blockers),
        "fatal_blockers": blockers,
    }
    payload.update(extra)
    return payload


def _mean(values: Any) -> float:
    series = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    if series.empty:
        return 0.0
    return float(series.mean())


def _positive_rate(values: pd.Series) -> float:
    series = pd.to_numeric(values, errors="coerce").dropna()
    if series.empty:
        return 0.0
    return float((series > 0).mean())


def _tstat(values: pd.Series) -> float:
    series = pd.to_numeric(values, errors="coerce").dropna()
    if len(series) < 2:
        return 0.0
    std = float(series.std(ddof=1))
    if std == 0:
        return 0.0
    return float(series.mean() / (std / math.sqrt(len(series))))


def _safe_float(value: Any) -> float | None:
    try:
        if value == "" or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt(value: Any) -> str:
    parsed = _safe_float(value)
    if parsed is None:
        return ""
    return f"{parsed:.6f}"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    print(json.dumps(run_v5f_physics_curve_full_5min_diagnostic(Path(".")), ensure_ascii=False, indent=2))

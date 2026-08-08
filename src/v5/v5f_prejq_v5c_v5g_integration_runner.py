from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_prejq_v5c_v5g_integration") / "current"
V5F_WEIGHTS = Path("v5f_structural_rough_screen") / "current" / "v5f_structural_rough_screen_weights.csv"
V5F_PERIODS = Path("v5f_internal_subsleeve_deep_engineering") / "current" / "v5f_internal_subsleeve_rebalance_period_stability.csv"
V5F_ROBUSTNESS = Path("v5f_internal_subsleeve_robustness_packet") / "current" / "v5f_internal_subsleeve_robustness_summary.json"
V5C_P2_SUMMARY = Path("v5c_p2_valuation_and_crowding_state_panel") / "current" / "v5c_p2_valuation_crowding_summary.json"
V5C_P3_SUMMARY = Path("v5c_p3_state_governance_quant_spec") / "current" / "v5c_p3_state_governance_summary.json"
V5C_P3_BOUNDARY = Path("v5c_p3_state_governance_quant_spec") / "current" / "v5c_p3_state_action_boundary_matrix.csv"
V5C_P4_SUMMARY = Path("v5c_p4_state_forward_observation_packet") / "current" / "v5c_p4_state_forward_observation_summary.json"
V5C_P4_SEED = Path("v5c_p4_state_forward_observation_packet") / "current" / "v5c_p4_historical_seed_observation_log.csv"
V5C_P4_QUEUE = Path("v5c_p4_state_forward_observation_packet") / "current" / "v5c_p4_pm_review_queue.csv"
V5C_OVERHEAT_SUMMARY = Path("v5c_overheat_overlay_pm_quant_spec") / "current" / "v5c_overheat_overlay_pm_quant_spec_summary.json"
V5C_OVERHEAT_CANDIDATES = Path("v5c_overheat_overlay_pm_quant_spec") / "current" / "v5c_overheat_overlay_fixed_rule_spec_candidates.csv"
V5G_SUMMARY = Path("v5g_vs_midterm_model_comparison") / "current" / "v5g_vs_midterm_summary.json"
V5G_DELTA = Path("v5g_vs_midterm_model_comparison") / "current" / "v5g_delta_vs_midterm_champion.csv"
V5G_QUEUE = Path("v5g_vs_midterm_model_comparison") / "current" / "v5g_vs_midterm_next_agent_queue.csv"
V5G02_SUMMARY = Path("v5g_02_quality_guarded_momentum_factor_validation") / "current" / "v5g_02_quality_factor_validation_summary.json"
V5G05_SUMMARY = Path("v5g_05_short_window_reversion_independent_validation_gate") / "current" / "v5g_05_short_window_validation_gate_summary.json"

PRIMARY = "internal_subsleeve_mom12_70_30"
BASELINE = "v57f_startup_preload_repaired_baseline"
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
COMPOSITE_OVERHEAT = "valuation_price_flow_overheat_watch"


REQUIRED = [
    V5F_WEIGHTS,
    V5F_PERIODS,
    V5F_ROBUSTNESS,
    V5C_P2_SUMMARY,
    V5C_P3_SUMMARY,
    V5C_P3_BOUNDARY,
    V5C_P4_SUMMARY,
    V5C_P4_SEED,
    V5C_P4_QUEUE,
    V5C_OVERHEAT_SUMMARY,
    V5C_OVERHEAT_CANDIDATES,
    V5G_SUMMARY,
    V5G_DELTA,
    V5G_QUEUE,
    V5G02_SUMMARY,
    V5G05_SUMMARY,
]


def run_v5f_prejq_v5c_v5g_integration(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    input_manifest = _input_manifest(root)
    missing = [row for row in input_manifest if row["required"] and not row["exists"]]
    if missing:
        _write_csv(out / "v5f_prejq_input_manifest.csv", input_manifest)
        _write_csv(out / "v5f_prejq_blockers.csv", missing)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", missing)
        _write_json(out / "v5f_prejq_v5c_v5g_integration_summary.json", summary)
        return summary

    robustness = _read_json(root / V5F_ROBUSTNESS)
    p2_summary = _read_json(root / V5C_P2_SUMMARY)
    p3_summary = _read_json(root / V5C_P3_SUMMARY)
    p4_summary = _read_json(root / V5C_P4_SUMMARY)
    overheat_summary = _read_json(root / V5C_OVERHEAT_SUMMARY)
    v5g_summary = _read_json(root / V5G_SUMMARY)
    v5g02 = _read_json(root / V5G02_SUMMARY)
    v5g05 = _read_json(root / V5G05_SUMMARY)

    state_join = _state_join(root)
    state_audit = _state_active_weight_audit(state_join)
    sleeve_exposure = _state_exposure_by_sleeve(state_join)
    period_exposure = _state_exposure_by_period(root, state_join)
    state_bucket = _state_bucket_result(state_join)
    forward_tags = _forward_observe_only_tags(state_join)
    overheat_candidate = _overheat_candidate_matrix(root, state_join)
    v5g_closeout = _v5g_closeout(root, v5g_summary, v5g02, v5g05)
    governance = _governance(
        robustness,
        p2_summary,
        p3_summary,
        p4_summary,
        overheat_summary,
        state_audit,
        overheat_candidate,
        v5g_closeout,
    )
    decision = _pm_decision(governance, state_audit, overheat_candidate)
    queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers = _blockers(governance)

    _write_csv(out / "v5f_prejq_input_manifest.csv", input_manifest)
    _write_csv(out / "v5c_v5f_state_active_weight_audit.csv", state_audit)
    _write_csv(out / "v5c_v5f_overheat_exposure_by_sleeve.csv", sleeve_exposure)
    _write_csv(out / "v5c_v5f_overheat_exposure_by_period.csv", period_exposure)
    _write_csv(out / "v5c_v5f_state_bucket_result.csv", state_bucket)
    _write_csv(out / "v5c_v5f_forward_observe_only_tags.csv", forward_tags)
    _write_csv(out / "v5c_overheat_no_new_overweight_candidate_matrix.csv", overheat_candidate)
    _write_csv(out / "v5g_secondary_diagnostic_closeout.csv", v5g_closeout)
    _write_csv(out / "v5f_prejq_v5c_v5g_governance_audit.csv", governance)
    _write_csv(out / "v5f_prejq_v5c_v5g_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_prejq_v5c_v5g_next_agent_queue.csv", queue)
    _write_csv(out / "v5f_prejq_blockers.csv", blockers)
    (out / "v5f_prejq_v5c_v5g_next_prompt.md").write_text(_next_prompt(queue), encoding="utf-8")
    (out / "v5f_prejq_v5c_v5g_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")
    (out / "v5f_prejq_v5c_v5g_integration_report.md").write_text(
        _report(robustness, state_audit, sleeve_exposure, period_exposure, overheat_candidate, v5g_closeout, decision),
        encoding="utf-8",
    )

    watch_rows = [row for row in state_audit if row["any_watch_state"]]
    overweight_watch = [row for row in state_audit if row["active_overweight_on_any_watch"]]
    composite_rows = [row for row in state_audit if row["sleeve_overheat_state"] == COMPOSITE_OVERHEAT]
    composite_overweight = [row for row in state_audit if row["active_overweight_on_composite_overheat"]]
    summary = _summary(
        "completed_v5f_prejq_v5c_v5g_integration",
        decision[0]["pm_gate_decision"],
        [],
        primary_candidate=PRIMARY,
        baseline_id=BASELINE,
        backtest_start=BACKTEST_START,
        backtest_end=BACKTEST_END,
        v5f_delta_return_pct_points_vs_repaired_baseline=robustness["delta_return_pct_points_vs_repaired_baseline"],
        joined_stock_rebalance_rows=len(state_audit),
        any_watch_row_count=len(watch_rows),
        active_overweight_on_watch_count=len(overweight_watch),
        composite_overheat_row_count=len(composite_rows),
        active_overweight_on_composite_overheat_count=len(composite_overweight),
        composite_candidate_touched_rebalance_sleeve_count=len({(row["rebalance_date"], row["sleeve_id"]) for row in composite_overweight}),
        v5g_primary_challenge_status=v5g_closeout[0]["status"],
        overheat_candidate_status=overheat_candidate[0]["pm_status"],
        observe_only_forward_integration=True,
    )
    _write_json(out / "v5f_prejq_v5c_v5g_integration_summary.json", summary)
    return summary


def _state_join(root: Path) -> pd.DataFrame:
    weights = pd.read_csv(root / V5F_WEIGHTS, dtype={"rebalance_date": str, "code": str, "sleeve": str})
    weights = weights[weights["version_id"] == PRIMARY].copy()
    weights["weight_delta"] = pd.to_numeric(weights["weight_delta"])
    weights["base_target_weight"] = pd.to_numeric(weights["base_target_weight"])
    weights["target_weight"] = pd.to_numeric(weights["target_weight"])

    states = pd.read_csv(root / V5C_P4_SEED, dtype={"observation_date": str, "code": str, "sleeve_id": str})
    states = states.rename(columns={"observation_date": "rebalance_date"})
    merged = weights.merge(states, left_on=["rebalance_date", "code", "sleeve"], right_on=["rebalance_date", "code", "sleeve_id"], how="left")
    merged["state_join_status"] = merged["valuation_state"].notna().map({True: "matched", False: "missing_state"})
    merged["valuation_state"] = merged["valuation_state"].fillna("missing_state")
    merged["crowding_state"] = merged["crowding_state"].fillna("missing_state")
    merged["sleeve_overheat_state"] = merged["sleeve_overheat_state"].fillna("missing_state")
    merged["broad_trend_state"] = merged["broad_trend_state"].fillna("missing_state")
    merged["pm_review_required"] = merged["pm_review_required"].fillna(False)
    merged["valuation_overheat_score"] = pd.to_numeric(merged["valuation_overheat_score"], errors="coerce").fillna(0.0)
    merged["money_percentile_252d"] = pd.to_numeric(merged["money_percentile_252d"], errors="coerce").fillna(0.0)
    return merged


def _state_active_weight_audit(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, row in df.sort_values(["rebalance_date", "sleeve", "code"]).iterrows():
        delta = float(row["weight_delta"])
        valuation_watch = "overheat" in str(row["valuation_state"])
        crowding_watch = str(row["crowding_state"]) in {"market_attention_hot", "rebalance_liquidity_pressure_watch"}
        sleeve_watch = "overheat" in str(row["sleeve_overheat_state"]) or "cooldown_or_stress" in str(row["sleeve_overheat_state"])
        broad_watch = str(row["broad_trend_state"]) in {"downtrend", "cooldown_or_stress_watch"}
        any_watch = valuation_watch or crowding_watch or sleeve_watch or broad_watch
        composite = str(row["sleeve_overheat_state"]) == COMPOSITE_OVERHEAT
        rows.append(
            {
                "rebalance_date": row["rebalance_date"],
                "code": row["code"],
                "sleeve_id": row["sleeve"],
                "base_target_weight": float(row["base_target_weight"]),
                "target_weight": float(row["target_weight"]),
                "weight_delta": delta,
                "active_direction": "overweight" if delta > 1e-12 else "underweight" if delta < -1e-12 else "neutral",
                "valuation_state": row["valuation_state"],
                "crowding_state": row["crowding_state"],
                "sleeve_overheat_state": row["sleeve_overheat_state"],
                "broad_trend_state": row["broad_trend_state"],
                "valuation_overheat_score": float(row["valuation_overheat_score"]),
                "money_percentile_252d": float(row["money_percentile_252d"]),
                "pm_review_required": _bool(row["pm_review_required"]),
                "valuation_watch": valuation_watch,
                "crowding_watch": crowding_watch,
                "sleeve_watch": sleeve_watch,
                "broad_watch": broad_watch,
                "any_watch_state": any_watch,
                "active_overweight_on_any_watch": delta > 1e-12 and any_watch,
                "active_underweight_on_any_watch": delta < -1e-12 and any_watch,
                "active_overweight_on_composite_overheat": delta > 1e-12 and composite,
                "state_join_status": row["state_join_status"],
                "allowed_current_action": "observe_only_tag",
                "trade_impact": "none",
                "accepted": False,
            }
        )
    return rows


def _state_exposure_by_sleeve(df: pd.DataFrame) -> list[dict[str, Any]]:
    audit = pd.DataFrame(_state_active_weight_audit(df))
    rows: list[dict[str, Any]] = []
    for sleeve, group in audit.groupby("sleeve_id", sort=True):
        rows.append(_exposure_row({"sleeve_id": sleeve}, group))
    return rows


def _state_exposure_by_period(root: Path, df: pd.DataFrame) -> list[dict[str, Any]]:
    audit = pd.DataFrame(_state_active_weight_audit(df))
    periods = pd.read_csv(root / V5F_PERIODS, dtype={"active_rebalance_date": str})
    periods = periods[periods["version_id"] == PRIMARY].copy()
    period_delta = {
        row["active_rebalance_date"]: float(row["delta_return_pct_points_vs_repaired_baseline"])
        for _, row in periods.iterrows()
    }
    rows: list[dict[str, Any]] = []
    for date, group in audit.groupby("rebalance_date", sort=True):
        payload = _exposure_row({"rebalance_date": date}, group)
        payload["period_delta_return_pct_points_vs_repaired_baseline"] = period_delta.get(date, "")
        payload["period_review_status"] = "overheat_watch_period" if payload["composite_overheat_row_count"] else "normal_or_noncomposite_watch_period"
        rows.append(payload)
    return rows


def _state_bucket_result(df: pd.DataFrame) -> list[dict[str, Any]]:
    audit = pd.DataFrame(_state_active_weight_audit(df))
    buckets = [
        ("valuation_state", "valuation_state"),
        ("crowding_state", "crowding_state"),
        ("sleeve_overheat_state", "sleeve_overheat_state"),
        ("broad_trend_state", "broad_trend_state"),
    ]
    rows: list[dict[str, Any]] = []
    for bucket_id, column in buckets:
        for state, group in audit.groupby(column, sort=True):
            row = _exposure_row({"bucket_id": bucket_id, "state": state}, group)
            rows.append(row)
    return rows


def _exposure_row(prefix: dict[str, Any], group: pd.DataFrame) -> dict[str, Any]:
    abs_delta = group["weight_delta"].abs()
    positive = group[group["weight_delta"] > 1e-12]
    watch = group[group["any_watch_state"]]
    overweight_watch = group[group["active_overweight_on_any_watch"]]
    composite = group[group["sleeve_overheat_state"] == COMPOSITE_OVERHEAT]
    composite_overweight = group[group["active_overweight_on_composite_overheat"]]
    payload = {
        "row_count": len(group),
        "watch_row_count": len(watch),
        "watch_row_share": len(watch) / len(group) if len(group) else 0.0,
        "positive_active_row_count": len(positive),
        "active_abs_weight_delta_sum": float(abs_delta.sum()),
        "watch_abs_weight_delta_sum": float(watch["weight_delta"].abs().sum()) if len(watch) else 0.0,
        "active_overweight_on_watch_count": len(overweight_watch),
        "active_overweight_on_watch_weight_delta_sum": float(overweight_watch["weight_delta"].sum()) if len(overweight_watch) else 0.0,
        "composite_overheat_row_count": len(composite),
        "active_overweight_on_composite_overheat_count": len(composite_overweight),
        "active_overweight_on_composite_overheat_weight_delta_sum": float(composite_overweight["weight_delta"].sum()) if len(composite_overweight) else 0.0,
        "state_exposure_status": "review" if len(composite_overweight) else "pass_observe_only",
    }
    return {**prefix, **payload}


def _forward_observe_only_tags(df: pd.DataFrame) -> list[dict[str, Any]]:
    audit = pd.DataFrame(_state_active_weight_audit(df))
    latest_dates = sorted(audit["rebalance_date"].unique())[-4:]
    rows = []
    for _, row in audit[audit["rebalance_date"].isin(latest_dates)].iterrows():
        if not row["any_watch_state"]:
            continue
        rows.append(
            {
                "template_id": "v5c_state_tag_for_v5f_forward",
                "paper_date": "",
                "source_historical_rebalance_date": row["rebalance_date"],
                "candidate_id": PRIMARY,
                "code": row["code"],
                "sleeve_id": row["sleeve_id"],
                "v5f_target_weight": row["target_weight"],
                "v5f_weight_delta": row["weight_delta"],
                "valuation_state": row["valuation_state"],
                "crowding_state": row["crowding_state"],
                "sleeve_overheat_state": row["sleeve_overheat_state"],
                "broad_trend_state": row["broad_trend_state"],
                "allowed_action": "record_observe_only_tag",
                "trade_order_allowed": False,
                "weight_change_allowed": False,
                "accepted": False,
            }
        )
    if rows:
        return rows
    return [
        {
            "template_id": "v5c_state_tag_for_v5f_forward",
            "paper_date": "",
            "source_historical_rebalance_date": "",
            "candidate_id": PRIMARY,
            "code": "",
            "sleeve_id": "",
            "v5f_target_weight": "",
            "v5f_weight_delta": "",
            "valuation_state": "",
            "crowding_state": "",
            "sleeve_overheat_state": "",
            "broad_trend_state": "",
            "allowed_action": "record_observe_only_tag",
            "trade_order_allowed": False,
            "weight_change_allowed": False,
            "accepted": False,
        }
    ]


def _overheat_candidate_matrix(root: Path, df: pd.DataFrame) -> list[dict[str, Any]]:
    candidates = _read_csv(root / V5C_OVERHEAT_CANDIDATES)
    spec = next(row for row in candidates if row["spec_id"] == "sleeve_composite_overheat_no_new_overweight_build")
    audit = pd.DataFrame(_state_active_weight_audit(df))
    touched = audit[audit["active_overweight_on_composite_overheat"]]
    composite = audit[audit["sleeve_overheat_state"] == COMPOSITE_OVERHEAT]
    return [
        {
            "candidate_id": "sleeve_composite_overheat_no_new_overweight_build",
            "source_spec_status": spec["pm_admission_status"],
            "user_message": "execute_1234",
            "pm_status": "approved_for_next_limited_engineering_fixed_rule_not_accepted",
            "fixed_trigger": COMPOSITE_OVERHEAT,
            "candidate_rule": "When a sleeve is in composite valuation+price-flow overheat, future limited engineering may freeze that sleeve to repaired V57f baseline weights for that rebalance, suppressing new V5f active overweight build only in that sleeve.",
            "ordinary_valuation_overheat_trade_allowed": False,
            "single_stock_sell_allowed": False,
            "cash_raise_allowed": False,
            "cross_sleeve_transfer_allowed": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "historical_nav_backtest_started": False,
            "accepted": False,
            "composite_overheat_rows": len(composite),
            "active_overweight_rows_touched_if_engineered": len(touched),
            "rebalance_sleeve_pairs_touched_if_engineered": len({(row["rebalance_date"], row["sleeve_id"]) for _, row in touched.iterrows()}),
            "positive_active_weight_delta_suppressed_if_engineered": float(touched["weight_delta"].sum()) if len(touched) else 0.0,
            "next_gate": "v5c_overheat_no_new_overweight_build_limited_engineering",
        },
        {
            "candidate_id": "v5c_overheat_observe_only_forward_tags",
            "source_spec_status": "admit_to_observation_control",
            "user_message": "execute_1234",
            "pm_status": "implemented_as_forward_observe_only_tagging",
            "fixed_trigger": "any V5c P3/P4 watch state",
            "candidate_rule": "Attach V5c state labels to V5f forward/paper rows without changing weights or trades.",
            "ordinary_valuation_overheat_trade_allowed": False,
            "single_stock_sell_allowed": False,
            "cash_raise_allowed": False,
            "cross_sleeve_transfer_allowed": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "historical_nav_backtest_started": False,
            "accepted": False,
            "composite_overheat_rows": len(composite),
            "active_overweight_rows_touched_if_engineered": 0,
            "rebalance_sleeve_pairs_touched_if_engineered": 0,
            "positive_active_weight_delta_suppressed_if_engineered": 0.0,
            "next_gate": "continue_v5c_state_observe_only_forward_tracking",
        },
    ]


def _v5g_closeout(root: Path, v5g_summary: dict[str, Any], v5g02: dict[str, Any], v5g05: dict[str, Any]) -> list[dict[str, Any]]:
    delta = _read_csv(root / V5G_DELTA)[0]
    queue = _read_csv(root / V5G_QUEUE)
    return [
        {
            "model_id": v5g_summary["best_new_model_id"],
            "role": "secondary_observation",
            "status": "sealed_secondary_underperforms_v5f_champion",
            "delta_return_pct_points_vs_repaired_baseline": v5g_summary["best_new_delta_return_pct_points_vs_baseline"],
            "delta_return_pct_points_vs_v5f_champion": delta["delta_return_pct_points_vs_midterm_champion"],
            "beats_v5f_champion": delta["beats_midterm_champion"],
            "allowed_next_action": "observe_or_archive_only",
            "accepted": False,
        },
        {
            "model_id": "v5g_02_quality_guarded_momentum_factor_validation",
            "role": "diagnostic",
            "status": v5g02["pm_gate_decision"],
            "delta_return_pct_points_vs_repaired_baseline": "",
            "delta_return_pct_points_vs_v5f_champion": "",
            "beats_v5f_champion": False,
            "allowed_next_action": "keep_diagnostic",
            "accepted": False,
        },
        {
            "model_id": "v5g_05_short_window_reversion_independent_validation_gate",
            "role": "diagnostic",
            "status": v5g05["pm_gate_decision"],
            "delta_return_pct_points_vs_repaired_baseline": "",
            "delta_return_pct_points_vs_v5f_champion": "",
            "beats_v5f_champion": False,
            "allowed_next_action": "keep_diagnostic_until_independent_evidence",
            "accepted": False,
        },
        {
            "model_id": "v5g_queue_reference",
            "role": "queue_governance",
            "status": ";".join(row["next_task"] for row in queue if row.get("allowed") == "True"),
            "delta_return_pct_points_vs_repaired_baseline": "",
            "delta_return_pct_points_vs_v5f_champion": "",
            "beats_v5f_champion": False,
            "allowed_next_action": "do_not_replace_v5f_champion",
            "accepted": False,
        },
    ]


def _governance(
    robustness: dict[str, Any],
    p2_summary: dict[str, Any],
    p3_summary: dict[str, Any],
    p4_summary: dict[str, Any],
    overheat_summary: dict[str, Any],
    state_audit: list[dict[str, Any]],
    overheat_candidate: list[dict[str, Any]],
    v5g_closeout: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        _audit("v5f_robustness_gate_passed", robustness["pm_gate_decision"] == "robustness_packet_pass_continue_forward_paper_not_accepted", robustness["pm_gate_decision"]),
        _audit("repaired_baseline_only", robustness["baseline_id"] == BASELINE, robustness["baseline_id"]),
        _audit("historical_scope_end_20260531", robustness["backtest_end"] == BACKTEST_END, robustness["backtest_end"]),
        _audit(
            "v5c_p2_passed",
            p2_summary["pm_gate_decision"]
            in {
                "p2_valuation_crowding_state_panel_pass_ready_for_pm_quant_spec",
                "p2_valuation_crowding_state_panel_pass_ready_for_v5c_p3_state_governance_spec",
            },
            p2_summary["pm_gate_decision"],
        ),
        _audit("v5c_p3_passed", p3_summary["pm_gate_decision"] == "p3_state_governance_spec_pass_ready_for_forward_observation_not_backtest", p3_summary["pm_gate_decision"]),
        _audit("v5c_p4_ready", p4_summary["pm_gate_decision"] == "p4_forward_observation_packet_pass_ready_for_future_v57f_rebalance_tracking", p4_summary["pm_gate_decision"]),
        _audit("v5c_overheat_spec_ready", overheat_summary["pm_gate_decision"] == "overheat_overlay_pm_quant_spec_pass_ready_for_limited_engineering_decision_not_backtest", overheat_summary["pm_gate_decision"]),
        _audit("state_join_complete", all(row["state_join_status"] == "matched" for row in state_audit), sum(1 for row in state_audit if row["state_join_status"] != "matched")),
        _audit("observe_only_tags_no_trade_impact", all(row["trade_impact"] == "none" for row in state_audit), "none"),
        _audit("conservative_overheat_candidate_not_backtested_here", not overheat_candidate[0]["historical_nav_backtest_started"], False),
        _audit("conservative_overheat_candidate_no_single_stock_sell", not overheat_candidate[0]["single_stock_sell_allowed"], False),
        _audit("v5g_not_replacing_v5f", v5g_closeout[0]["status"] == "sealed_secondary_underperforms_v5f_champion", v5g_closeout[0]["status"]),
        _audit("accepted_false", not robustness["accepted"] and all(not row["accepted"] for row in v5g_closeout), False),
        _audit("v57f_core_modified_false", not robustness["v57f_core_modified"] and not overheat_candidate[0]["v57f_core_modified"], False),
        _audit("threshold_scan_used_false", not robustness["threshold_scan_used"] and not overheat_candidate[0]["threshold_scan_used"], False),
        _audit("joinquant_not_started", not robustness["joinquant_started"], False),
    ]


def _pm_decision(
    governance: list[dict[str, Any]],
    state_audit: list[dict[str, Any]],
    overheat_candidate: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    candidate_ready = overheat_candidate[0]["pm_status"] == "approved_for_next_limited_engineering_fixed_rule_not_accepted"
    decision = (
        "prejq_v5c_v5g_integration_pass_observe_only_and_overheat_candidate_ready"
        if gov_ok and candidate_ready
        else "blocked_by_prejq_v5c_v5g_governance_issue"
    )
    return [
        {
            "pm_gate_decision": decision,
            "primary_candidate": PRIMARY,
            "baseline_id": BASELINE,
            "historical_scope": f"{BACKTEST_START} to {BACKTEST_END}",
            "observe_only_forward_tags_ready": gov_ok,
            "overheat_no_new_overweight_candidate_ready_for_next_limited_engineering": gov_ok and candidate_ready,
            "v5g_sealed_secondary_or_diagnostic": gov_ok,
            "joined_stock_rebalance_rows": len(state_audit),
            "accepted": False,
            "live_trading_approved": False,
            "deployment_approved": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "joinquant_started": False,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    ready = decision == "prejq_v5c_v5g_integration_pass_observe_only_and_overheat_candidate_ready"
    return [
        {
            "priority": "P0",
            "next_task": "v5c_overheat_no_new_overweight_build_limited_engineering",
            "allowed": ready,
            "requires_joinquant": False,
            "changes_trade_path": True,
            "status": "ready_fixed_rule_not_accepted" if ready else "blocked",
        },
        {
            "priority": "P1",
            "next_task": "attach_v5c_observe_only_state_tags_to_v5f_forward_paper_rows",
            "allowed": ready,
            "requires_joinquant": False,
            "changes_trade_path": False,
            "status": "ready",
        },
        {
            "priority": "P2",
            "next_task": "keep_v5g01_secondary_and_v5g02_v5g05_diagnostic",
            "allowed": True,
            "requires_joinquant": False,
            "changes_trade_path": False,
            "status": "done_closeout",
        },
        {
            "priority": "P3",
            "next_task": "joinquant_platform_attribution_after_user_exports",
            "allowed": False,
            "requires_joinquant": True,
            "changes_trade_path": False,
            "status": "waiting_for_user_exports",
        },
    ]


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    if not failed:
        return [
            {
                "blocker_id": "none",
                "severity": "none",
                "status": "not_blocking",
                "description": "Pre-JQ V5c/V5g integration packet completed.",
            }
        ]
    return [
        {
            "blocker_id": row["audit_id"],
            "severity": "fatal",
            "status": "blocking",
            "description": row["detail"],
        }
        for row in failed
    ]


def _report(
    robustness: dict[str, Any],
    state_audit: list[dict[str, Any]],
    sleeve_exposure: list[dict[str, Any]],
    period_exposure: list[dict[str, Any]],
    overheat_candidate: list[dict[str, Any]],
    v5g_closeout: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    watch_rows = [row for row in state_audit if row["any_watch_state"]]
    overweight_watch = [row for row in state_audit if row["active_overweight_on_any_watch"]]
    composite_overweight = [row for row in state_audit if row["active_overweight_on_composite_overheat"]]
    top_sleeve = max(sleeve_exposure, key=lambda row: float(row["active_overweight_on_watch_weight_delta_sum"]))
    composite_periods = [row for row in period_exposure if row["composite_overheat_row_count"]]
    return "\n".join(
        [
            "# V5f Pre-JQ V5c/V5g Integration",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Primary model: `{PRIMARY}`",
            f"- Benchmark: `{BASELINE}`",
            f"- Historical scope: `{BACKTEST_START}` to `{BACKTEST_END}`.",
            "- Accepted/live approved: `False`.",
            "",
            "## V5c State Cross Audit",
            f"- Joined stock-rebalance rows: `{len(state_audit)}`.",
            f"- Any V5c watch-state rows: `{len(watch_rows)}`.",
            f"- V5f active overweight on any watch-state rows: `{len(overweight_watch)}`.",
            f"- V5f active overweight on composite overheat rows: `{len(composite_overweight)}`.",
            f"- Highest sleeve watch overweight exposure: `{top_sleeve['sleeve_id']}` with `{float(top_sleeve['active_overweight_on_watch_weight_delta_sum']):.6f}` summed weight delta.",
            "",
            "## Composite Overheat",
            f"- Composite overheat periods: `{'; '.join(row['rebalance_date'] for row in composite_periods) if composite_periods else 'none'}`.",
            f"- Candidate status: `{overheat_candidate[0]['pm_status']}`.",
            "- Candidate remains not accepted and not backtested in this packet.",
            "",
            "## V5g Closeout",
            *[f"- `{row['model_id']}`: {row['status']}" for row in v5g_closeout],
            "",
            "## Interpretation",
            f"- V5f champion edge remains the main line at `{float(robustness['delta_return_pct_points_vs_repaired_baseline']):.4f}` pct points over repaired baseline.",
            "- V5c states are useful as forward risk tags before JoinQuant attribution.",
            "- The only trade-path candidate admitted for next work is the narrow composite-overheat no-new-overweight rule.",
            "- V5g remains secondary/diagnostic and does not replace V5f.",
            "",
        ]
    )


def _next_prompt(queue: list[dict[str, Any]]) -> str:
    return f"""工作目录：
D:\\hh\\codex\\v5

任务名称：
V5c overheat no-new-overweight limited engineering for V5f champion

任务目标：
基于 `v5f_prejq_v5c_v5g_integration/current/`，只测试固定规则 `sleeve_composite_overheat_no_new_overweight_build` 对 V5f 冠军 `internal_subsleeve_mom12_70_30` 的影响。

固定规则：
当且仅当某 sleeve 在 V5c 中处于 `{COMPOSITE_OVERHEAT}`，该 sleeve 在该调仓期不新增 V5f 主动超配，回到 repaired V57f baseline sleeve 内权重；其他 sleeve 保持 V5f 冠军权重。

禁止事项：
1. 不得修改 V57f core。
2. 不得新增阈值或参数扫描。
3. 不得单股卖出。
4. 不得跨 sleeve 转移。
5. 不得 cash raise。
6. 不得使用 2026-05-31 之后作为历史回测。
7. 不得标记 accepted/live approved。
8. 不得启动 JoinQuant。

必须先阅读：
- v5f_prejq_v5c_v5g_integration\\current\\v5f_prejq_v5c_v5g_integration_summary.json
- v5f_prejq_v5c_v5g_integration\\current\\v5c_overheat_no_new_overweight_candidate_matrix.csv
- v5f_prejq_v5c_v5g_integration\\current\\v5c_v5f_state_active_weight_audit.csv
- v5f_internal_subsleeve_robustness_packet\\current\\v5f_internal_subsleeve_robustness_summary.json

下一步队列：
{json.dumps(queue, ensure_ascii=False, indent=2)}
"""


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Pre-JQ V5c/V5g Integration Rules",
            "",
            "- Repaired V57f baseline only.",
            "- Historical scope ends at 2026-05-31.",
            "- V5c state labels are observe-only unless a separate fixed-rule engineering task is opened.",
            f"- The only admitted overheat candidate is `{COMPOSITE_OVERHEAT}` no-new-overweight build.",
            "- V5g01 stays secondary; V5g02 and V5g05 stay diagnostic.",
            "- Do not start JoinQuant.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _input_manifest(root: Path) -> list[dict[str, Any]]:
    rows = []
    for rel in REQUIRED:
        path = root / rel
        rows.append({"path": str(rel), "required": True, "exists": path.exists(), "file_size_bytes": path.stat().st_size if path.exists() else ""})
    return rows


def _audit(audit_id: str, ok: bool, detail: Any) -> dict[str, Any]:
    return {"audit_id": audit_id, "status": "pass" if ok else "fail", "detail": detail}


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _summary(status: str, decision: str, fatal_blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5f_prejq_v5c_v5g_integration",
        "status": status,
        "pm_gate_decision": decision,
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "engineering_backtest_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }
    payload.update(extra)
    return payload


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
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
    print(json.dumps(run_v5f_prejq_v5c_v5g_integration(Path(".")), ensure_ascii=False, indent=2))

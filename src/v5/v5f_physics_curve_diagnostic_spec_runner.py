from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5f_physics_curve_diagnostic_spec") / "current"
V4_ROOT = Path("D:/hh/codex/v4")

V4_REFERENCES = [
    V4_ROOT / "README.md",
    V4_ROOT / "PROJECT_CONTEXT.md",
    V4_ROOT / "phase_2_momentum" / "allocation_vs_selection_framework_note_v1.md",
    V4_ROOT / "phase_2_momentum" / "active_mainline_execution_prep_spec_v1.md",
    V4_ROOT / "phase_3_mean_reversion" / "README.md",
]

V5_REQUIRED = [
    Path("v5f_prejq_local_closeout") / "current" / "v5f_prejq_local_closeout_summary.json",
    Path("v5f_internal_subsleeve_robustness_packet") / "current" / "v5f_internal_subsleeve_robustness_summary.json",
    Path("v5f_forward_paper_v5c_state_tags") / "current" / "v5f_v5c_state_tag_summary.json",
    Path("v5c_p2_valuation_and_crowding_state_panel") / "current" / "v5c_p2_valuation_crowding_summary.json",
    Path("v5c_overheat_no_new_overweight_limited_engineering") / "current" / "v5c_overheat_no_new_overweight_summary.json",
    Path("v5f_structural_rough_screen") / "current" / "v5f_structural_rough_screen_metrics.csv",
    Path("v5f_adaptive_momentum_governance") / "current" / "v5f_adaptive_momentum_summary.json",
    Path("v5f_quality_value_mean_reversion") / "current" / "v5f_qv_mean_reversion_summary.json",
    Path("v5f_short_window_reversion_walk_forward_robustness") / "current" / "v5f_walk_forward_summary.json",
]


def run_v5f_physics_curve_diagnostic_spec(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_physics_blockers.csv", blockers)
        summary = _summary(
            "blocked_missing_required_input",
            "blocked_until_required_v4_or_v5_inputs_available",
            blockers,
            physics_curve_can_be_used_in_v5=False,
        )
        _write_json(out / "v5f_physics_curve_diagnostic_summary.json", summary)
        return summary

    prejq = _read_json(root / V5_REQUIRED[0])
    robustness = _read_json(root / V5_REQUIRED[1])
    v5c_tags = _read_json(root / V5_REQUIRED[2])
    v5c_p2 = _read_json(root / V5_REQUIRED[3])
    overheat = _read_json(root / V5_REQUIRED[4])
    adaptive = _read_json(root / V5_REQUIRED[6])
    qv_reversion = _read_json(root / V5_REQUIRED[7])
    short_reversion = _read_json(root / V5_REQUIRED[8])

    factor_mapping = _factor_mapping()
    v4_manifest = _v4_manifest()
    data_availability = _v5_data_availability(
        prejq=prejq,
        robustness=robustness,
        v5c_tags=v5c_tags,
        v5c_p2=v5c_p2,
        overheat=overheat,
        adaptive=adaptive,
        qv_reversion=qv_reversion,
        short_reversion=short_reversion,
    )
    allowed = _allowed_diagnostic_uses()
    blocked = _blocked_trading_uses()
    feature_schema = _candidate_feature_schema()
    hypothesis = _hypothesis_matrix(robustness, overheat, adaptive, qv_reversion, short_reversion)
    decision = _pm_gate_decision(data_availability, allowed, blocked)
    next_queue = _next_agent_queue(decision[0]["pm_gate_decision"])
    blockers_out = [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "detail": "Physics diagnostic spec generated without changing V57f or V5f rules."}]

    _write_csv(out / "v5f_physics_factor_mapping.csv", factor_mapping)
    _write_csv(out / "v5f_physics_v4_reference_manifest.csv", v4_manifest)
    _write_csv(out / "v5f_physics_v5_data_availability.csv", data_availability)
    _write_csv(out / "v5f_physics_allowed_diagnostic_uses.csv", allowed)
    _write_csv(out / "v5f_physics_blocked_trading_uses.csv", blocked)
    _write_csv(out / "v5f_physics_candidate_feature_schema.csv", feature_schema)
    _write_csv(out / "v5f_physics_model_hypothesis_matrix.csv", hypothesis)
    _write_csv(out / "v5f_physics_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_physics_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5f_physics_blockers.csv", blockers_out)
    (out / "v5f_physics_curve_diagnostic_report.md").write_text(
        _report(decision, robustness, overheat, adaptive, qv_reversion, short_reversion),
        encoding="utf-8",
    )
    (out / "v5f_physics_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    summary = _summary(
        "completed_v5f_physics_curve_diagnostic_spec",
        decision[0]["pm_gate_decision"],
        [],
        physics_curve_can_be_used_in_v5=True,
        recommended_use="diagnostic_explanation_and_feature_panel_spec",
        primary_candidate=robustness.get("primary_candidate", "internal_subsleeve_mom12_70_30"),
        baseline_id=robustness.get("baseline_id", "v57f_startup_preload_repaired_baseline"),
        backtest_start=robustness.get("backtest_start", "2021-05-01"),
        backtest_end=robustness.get("backtest_end", "2026-05-31"),
        primary_delta_return_pct_points_vs_repaired_baseline=robustness.get("delta_return_pct_points_vs_repaired_baseline"),
        primary_delta_drawdown_pct_points_vs_repaired_baseline=robustness.get("delta_max_drawdown_pct_points_vs_repaired_baseline"),
        limited_engineering_started=False,
        engineering_backtest_started=False,
        feature_panel_ready_for_next_gate=True,
    )
    _write_json(out / "v5f_physics_curve_diagnostic_summary.json", summary)
    return summary


def _factor_mapping() -> list[dict[str, Any]]:
    return [
        {
            "physics_component": "position",
            "v4_interpretation": "price location relative to a long-run terrain",
            "v5_translation": "fundamental/value anchor inside repaired V57f selected stock pool",
            "candidate_v5_inputs": "V57f sleeve membership; valuation state; dividend/OCF quality; low-vol state",
            "allowed_use": "anchor explanation and value-trap guard",
            "blocked_use": "do not add stocks outside repaired V57f pool",
        },
        {
            "physics_component": "velocity",
            "v4_interpretation": "momentum direction and speed",
            "v5_translation": "mom_12_1 internal sub-sleeve tilt",
            "candidate_v5_inputs": "V5f internal_subsleeve_mom12_70_30; mom_12_1 rank within same sleeve",
            "allowed_use": "current V5f champion interpretation",
            "blocked_use": "do not become full-market momentum selection",
        },
        {
            "physics_component": "acceleration",
            "v4_interpretation": "change in momentum, acceleration or deceleration",
            "v5_translation": "rank-change, mom_6_1 versus mom_12_1, monthly momentum update diagnostics",
            "candidate_v5_inputs": "adaptive momentum governance; fixed rank-change event logs",
            "allowed_use": "warning that velocity is improving or fading",
            "blocked_use": "do not trigger daily ungoverned rebalancing",
        },
        {
            "physics_component": "restoring_force",
            "v4_interpretation": "mean reversion pull toward value anchor",
            "v5_translation": "quality/value guarded mean-reversion and extreme value reversion diagnostics",
            "candidate_v5_inputs": "valuation percentile; quality pass; short-window reversion event diagnostics",
            "allowed_use": "diagnose tension between cheapness and price weakness",
            "blocked_use": "do not buy losers without fundamental guard",
        },
        {
            "physics_component": "shock",
            "v4_interpretation": "external impulse or temporary displacement",
            "v5_translation": "early-drop, VWAP-break and short-window reversal diagnostics",
            "candidate_v5_inputs": "full holding-period 5min data; 1-2 day repair diagnostics",
            "allowed_use": "event study and execution/risk note",
            "blocked_use": "do not promote in-sample shock rule without independent validation",
        },
        {
            "physics_component": "temperature_pressure",
            "v4_interpretation": "system instability, crowded kinetic state",
            "v5_translation": "V5c valuation, crowding, overheat and forward observation tags",
            "candidate_v5_inputs": "V5c P2/P4 state panels; overheat no-new-overweight diagnostic",
            "allowed_use": "PM watchlist and overheat attribution",
            "blocked_use": "do not replace V5f champion with overheat guard after underperformance",
        },
        {
            "physics_component": "friction",
            "v4_interpretation": "cost of moving the portfolio",
            "v5_translation": "turnover, commission, liquidity and execution cost health",
            "candidate_v5_inputs": "V5f robustness cost health; order health; JoinQuant export checklist",
            "allowed_use": "gate any later overlay before promotion",
            "blocked_use": "do not ignore costs when acceleration signals fire often",
        },
    ]


def _v4_manifest() -> list[dict[str, Any]]:
    return [
        {
            "source_id": "v4_readme_physics_explainer",
            "path": str(V4_ROOT / "README.md"),
            "reference_scope": "physics analogy: position, velocity, acceleration, driving force, shock",
            "v5_import_status": "import_as_explanatory_framework_only",
            "notable_boundary": "V4 did not promote the full physics analogy into formal execution.",
        },
        {
            "source_id": "v4_project_context",
            "path": str(V4_ROOT / "PROJECT_CONTEXT.md"),
            "reference_scope": "fundamental plus momentum plus mean-reversion research framework",
            "v5_import_status": "import_governance_language",
            "notable_boundary": "Momentum and mean reversion remain complements, not replacements for fundamentals.",
        },
        {
            "source_id": "v4_allocation_vs_selection",
            "path": str(V4_ROOT / "phase_2_momentum" / "allocation_vs_selection_framework_note_v1.md"),
            "reference_scope": "separate allocation-sleeve and stock-selection questions",
            "v5_import_status": "compatible_with_v5f_internal_subsleeve_reading",
            "notable_boundary": "Do not mix allocation conclusions with selection conclusions.",
        },
        {
            "source_id": "v4_active_mainline_execution_prep",
            "path": str(V4_ROOT / "phase_2_momentum" / "active_mainline_execution_prep_spec_v1.md"),
            "reference_scope": "state-routed momentum budget examples",
            "v5_import_status": "diagnostic_reference_only",
            "notable_boundary": "V5g state gate underperformed V5f champion, so routing is not promoted.",
        },
        {
            "source_id": "v4_mean_reversion_readme",
            "path": str(V4_ROOT / "phase_3_mean_reversion" / "README.md"),
            "reference_scope": "price and valuation mean-reversion features after momentum",
            "v5_import_status": "diagnostic_reference_only",
            "notable_boundary": "V5 mean reversion remains weaker than momentum champion.",
        },
    ]


def _v5_data_availability(
    *,
    prejq: dict[str, Any],
    robustness: dict[str, Any],
    v5c_tags: dict[str, Any],
    v5c_p2: dict[str, Any],
    overheat: dict[str, Any],
    adaptive: dict[str, Any],
    qv_reversion: dict[str, Any],
    short_reversion: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "data_or_result": "repaired_baseline_truth",
            "source": "v5f_prejq_local_closeout",
            "status": "available",
            "key_observation": prejq.get("baseline_id"),
            "historical_scope": f"{prejq.get('backtest_start')} to {prejq.get('backtest_end')}",
            "usable_for_physics": True,
        },
        {
            "data_or_result": "velocity_engine",
            "source": "v5f_internal_subsleeve_robustness_packet",
            "status": "available",
            "key_observation": f"{robustness.get('primary_candidate')} delta {robustness.get('delta_return_pct_points_vs_repaired_baseline'):.4f} pct",
            "historical_scope": f"{robustness.get('backtest_start')} to {robustness.get('backtest_end')}",
            "usable_for_physics": True,
        },
        {
            "data_or_result": "temperature_pressure_state",
            "source": "v5c_p2_valuation_and_crowding_state_panel",
            "status": "available",
            "key_observation": f"valuation_rows={v5c_p2.get('valuation_rows')}; crowding_rows={v5c_p2.get('crowding_rows')}; overheat_watch={v5c_p2.get('valuation_overheat_watch_count')}",
            "historical_scope": "PIT state panel",
            "usable_for_physics": True,
        },
        {
            "data_or_result": "forward_state_tags",
            "source": "v5f_forward_paper_v5c_state_tags",
            "status": "available_observe_only",
            "key_observation": f"seed_tag_rows={v5c_tags.get('seed_tag_rows')}; trade_orders={v5c_tags.get('trade_order_allowed_count')}",
            "historical_scope": "forward observation seed",
            "usable_for_physics": True,
        },
        {
            "data_or_result": "overheat_guard_engineering",
            "source": "v5c_overheat_no_new_overweight_limited_engineering",
            "status": "available_diagnostic_only",
            "key_observation": f"delta_vs_primary={overheat.get('candidate_delta_return_pct_points_vs_primary'):.4f} pct",
            "historical_scope": f"{overheat.get('backtest_start')} to {overheat.get('backtest_end')}",
            "usable_for_physics": True,
        },
        {
            "data_or_result": "acceleration_governance",
            "source": "v5f_adaptive_momentum_governance",
            "status": "available_not_promoted",
            "key_observation": f"best_incremental_vs_champion={adaptive.get('best_incremental_delta_return_vs_champion'):.4f} pct",
            "historical_scope": f"{adaptive.get('backtest_scope_start')} to {adaptive.get('backtest_scope_end')}",
            "usable_for_physics": True,
        },
        {
            "data_or_result": "restoring_force_guarded_reversion",
            "source": "v5f_quality_value_mean_reversion",
            "status": "available_diagnostic_only",
            "key_observation": f"best_incremental_vs_champion={qv_reversion.get('best_incremental_delta_return_vs_champion'):.4f} pct",
            "historical_scope": f"{qv_reversion.get('backtest_scope_start')} to {qv_reversion.get('backtest_scope_end')}",
            "usable_for_physics": True,
        },
        {
            "data_or_result": "shock_reversion_internal_rolling",
            "source": "v5f_short_window_reversion_walk_forward_robustness",
            "status": "available_in_sample_diagnostic_only",
            "key_observation": f"best_delta_vs_champion={short_reversion.get('best_delta_vs_champion'):.4f} pct; oos={short_reversion.get('oos_validation_used')}",
            "historical_scope": f"{short_reversion.get('backtest_scope_start')} to {short_reversion.get('backtest_scope_end')}",
            "usable_for_physics": True,
        },
    ]


def _allowed_diagnostic_uses() -> list[dict[str, Any]]:
    return [
        {"use_id": "pm_curve_explanation", "allowed": True, "description": "Explain each holding or sleeve as anchor, velocity, acceleration, restoring force and pressure."},
        {"use_id": "v5f_champion_attribution", "allowed": True, "description": "Describe why internal_subsleeve_mom12_70_30 works as a value-pool velocity overlay."},
        {"use_id": "v5c_state_interpretation", "allowed": True, "description": "Use V5c overheat/crowding tags as temperature/pressure labels for PM review."},
        {"use_id": "mean_reversion_failure_diagnosis", "allowed": True, "description": "Classify weak reversion results as broken anchor, weak restoring force or excessive friction."},
        {"use_id": "short_window_shock_review", "allowed": True, "description": "Treat early-drop/VWAP-break events as shock diagnostics requiring independent validation."},
        {"use_id": "feature_panel_spec", "allowed": True, "description": "Build a future PIT feature panel without changing trades."},
        {"use_id": "forward_paper_note", "allowed": True, "description": "Attach physics labels to future V5f paper observations without generating orders."},
    ]


def _blocked_trading_uses() -> list[dict[str, Any]]:
    return [
        {"blocked_use_id": "accepted_strategy_status", "blocked": True, "reason": "This packet is a diagnostic spec, not an acceptance gate."},
        {"blocked_use_id": "v57f_replacement", "blocked": True, "reason": "V57f repaired baseline remains the benchmark and core."},
        {"blocked_use_id": "full_market_stock_selection", "blocked": True, "reason": "Momentum and reversion can only operate inside V57f/V5f pools unless separately approved."},
        {"blocked_use_id": "daily_unbounded_rebalance", "blocked": True, "reason": "Daily re-optimization previously showed governance and turnover risk."},
        {"blocked_use_id": "parameter_scan", "blocked": True, "reason": "Physics labels cannot be used to choose historical best thresholds."},
        {"blocked_use_id": "post_20260531_historical_evidence", "blocked": True, "reason": "Backtest scope ends on 2026-05-31."},
        {"blocked_use_id": "new_buy_signal", "blocked": True, "reason": "No new buy signal is created by this spec."},
        {"blocked_use_id": "overheat_guard_replaces_champion", "blocked": True, "reason": "V5c no-new-overweight was diagnostic and lagged the champion."},
    ]


def _candidate_feature_schema() -> list[dict[str, Any]]:
    return [
        {
            "feature_name": "anchor_quality_state",
            "physics_role": "driving_force",
            "formula_hint": "PIT quality/dividend/OCF guard state from repaired V57f and V5c panels",
            "frequency": "rebalance_date_or_reporting_visibility",
            "pit_rule": "use only data visible before the signal date",
            "trade_effect_now": "none",
        },
        {
            "feature_name": "anchor_value_gap_state",
            "physics_role": "position_tension",
            "formula_hint": "within-sleeve valuation percentile or cheap/neutral/expensive state",
            "frequency": "rebalance_date",
            "pit_rule": "use only PIT valuation panel rows",
            "trade_effect_now": "none",
        },
        {
            "feature_name": "velocity_mom_12_1",
            "physics_role": "velocity",
            "formula_hint": "12 month return skipping latest 1 month, ranked within same sleeve",
            "frequency": "rebalance_date or approved monthly observation",
            "pit_rule": "price window must end before the decision timestamp",
            "trade_effect_now": "existing V5f champion only",
        },
        {
            "feature_name": "acceleration_momentum_change",
            "physics_role": "acceleration",
            "formula_hint": "fixed change in momentum rank or mom_6_1 minus mom_12_1 diagnostic",
            "frequency": "monthly_or_event_observation",
            "pit_rule": "no future returns in acceleration label",
            "trade_effect_now": "none",
        },
        {
            "feature_name": "restoring_force_score",
            "physics_role": "restoring_force",
            "formula_hint": "cheap valuation plus quality guard plus non-worsening momentum",
            "frequency": "rebalance_date_or_event_observation",
            "pit_rule": "fundamental guard must be visible before reversion label",
            "trade_effect_now": "none",
        },
        {
            "feature_name": "shock_impulse_state",
            "physics_role": "shock",
            "formula_hint": "fixed early-drop, VWAP-break or 1-2 day acute move event label",
            "frequency": "intraday_or_daily_diagnostic",
            "pit_rule": "event bar must be observed before forward return evaluation",
            "trade_effect_now": "none",
        },
        {
            "feature_name": "temperature_pressure_state",
            "physics_role": "system_pressure",
            "formula_hint": "V5c valuation overheat, sleeve overheat, crowding and broad trend state",
            "frequency": "rebalance_date_or_forward_observation",
            "pit_rule": "state tag only, not trade trigger",
            "trade_effect_now": "none",
        },
    ]


def _hypothesis_matrix(
    robustness: dict[str, Any],
    overheat: dict[str, Any],
    adaptive: dict[str, Any],
    qv_reversion: dict[str, Any],
    short_reversion: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "hypothesis_id": "H1_value_pool_velocity_overlay",
            "physics_pattern": "strong anchor plus positive velocity",
            "v5_reading": "V57f stock pool with internal same-sleeve mom_12_1 tilt",
            "current_evidence": f"champion delta {robustness.get('delta_return_pct_points_vs_repaired_baseline'):.4f} pct vs repaired baseline",
            "status": "supported_as_current_v5f_primary_candidate_not_accepted",
            "next_test": "continue forward/paper tracking",
        },
        {
            "hypothesis_id": "H2_acceleration_can_improve_timing",
            "physics_pattern": "velocity still positive but acceleration changes",
            "v5_reading": "monthly/rank-change adaptive momentum governance",
            "current_evidence": f"best adaptive incremental {adaptive.get('best_incremental_delta_return_vs_champion'):.4f} pct vs champion but not promoted",
            "status": "research_positive_but_insufficient_to_replace_champion",
            "next_test": "feature-panel event attribution only",
        },
        {
            "hypothesis_id": "H3_overheat_pressure_is_a_warning_not_a_brake",
            "physics_pattern": "high pressure with active velocity",
            "v5_reading": "V5c overheat no-new-overweight",
            "current_evidence": f"overheat guard delta {overheat.get('candidate_delta_return_pct_points_vs_primary'):.4f} pct vs primary",
            "status": "diagnostic_only",
            "next_test": "keep V5c tags as PM watch notes",
        },
        {
            "hypothesis_id": "H4_restoring_force_is_weak_in_red_dividend_pool",
            "physics_pattern": "cheap position but weak or broken anchor",
            "v5_reading": "quality/value mean reversion and extreme value reversion",
            "current_evidence": f"guarded reversion incremental {qv_reversion.get('best_incremental_delta_return_vs_champion'):.4f} pct vs champion",
            "status": "diagnostic_only_keep_momentum_primary",
            "next_test": "only retest after stronger PIT fundamental deterioration labels",
        },
        {
            "hypothesis_id": "H5_shock_reversion_needs_independent_validation",
            "physics_pattern": "temporary impulse away from anchor",
            "v5_reading": "short-window early-drop/VWAP-break repair events",
            "current_evidence": f"in-sample/internal diagnostic delta {short_reversion.get('best_delta_vs_champion'):.4f} pct; oos={short_reversion.get('oos_validation_used')}",
            "status": "not_validated_for_strategy",
            "next_test": "pre-2021 independent validation before any engineering promotion",
        },
    ]


def _pm_gate_decision(
    data_availability: list[dict[str, Any]],
    allowed: list[dict[str, Any]],
    blocked: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ok = all(row["usable_for_physics"] for row in data_availability) and all(row["allowed"] for row in allowed) and all(row["blocked"] for row in blocked)
    return [
        {
            "pm_gate_decision": "physics_curve_diagnostic_spec_ready_not_engineering" if ok else "blocked_by_physics_spec_governance_issue",
            "physics_curve_can_be_used_in_v5": ok,
            "allowed_scope": "diagnostic_explanation_feature_panel_and_forward_observation",
            "limited_engineering_allowed_now": False,
            "engineering_backtest_started": False,
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "new_buy_signal_used": False,
            "primary_candidate_remains": "internal_subsleeve_mom12_70_30",
            "rationale": "The framework explains existing V5 evidence coherently but does not add a governed trading rule by itself.",
        }
    ]


def _next_agent_queue(decision: str) -> list[dict[str, Any]]:
    ready = decision == "physics_curve_diagnostic_spec_ready_not_engineering"
    return [
        {
            "priority": 1,
            "next_task": "v5f_physics_curve_feature_panel_diagnostic",
            "allowed": ready,
            "purpose": "Build PIT feature panel with anchor, velocity, acceleration, restoring force, shock and pressure labels.",
        },
        {
            "priority": 2,
            "next_task": "v5f_physics_force_balance_event_study",
            "allowed": ready,
            "purpose": "Explain champion wins/losses and V5c watch events using the physics state labels.",
        },
        {
            "priority": 3,
            "next_task": "v5f_physics_overlay_limited_engineering",
            "allowed": False,
            "purpose": "Requires separate PM approval because it would change weights or trades.",
        },
        {
            "priority": 4,
            "next_task": "keep_v5f_internal_subsleeve_forward_paper_primary",
            "allowed": True,
            "purpose": "Do not interrupt current V5f champion forward/paper tracking.",
        },
    ]


def _report(
    decision: list[dict[str, Any]],
    robustness: dict[str, Any],
    overheat: dict[str, Any],
    adaptive: dict[str, Any],
    qv_reversion: dict[str, Any],
    short_reversion: dict[str, Any],
) -> str:
    return "\n".join(
        [
            "# V5f Physics Curve Diagnostic Spec",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            "- Verdict: the V4 physics idea can be used in V5 as a diagnostic and explanation framework, not as a direct trading rule.",
            "- Baseline: `v57f_startup_preload_repaired_baseline` only.",
            "- Backtest scope: `2021-05-01` to `2026-05-31`; do not treat later data as historical evidence.",
            "- Accepted: `False`; live approved: `False`; V57f core modified: `False`.",
            "",
            "## How The Physics Map Reads V5",
            "",
            "- Value/fundamental anchor = repaired V57f sleeve membership, quality/dividend/OCF and valuation state.",
            "- Velocity = V5f `internal_subsleeve_mom12_70_30`, currently the strongest governed overlay.",
            "- Acceleration = changes in momentum rank or monthly momentum update diagnostics.",
            "- Restoring force = value/quality guarded mean reversion, currently diagnostic only.",
            "- Shock = early-drop, VWAP-break and 1-2 day repair events, still requiring independent validation.",
            "- Temperature/pressure = V5c valuation, crowding and overheat state labels.",
            "",
            "## Current Evidence",
            "",
            f"- V5f velocity champion return: `{robustness.get('strategy_return_pct'):.4f}%`; delta vs repaired baseline: `{robustness.get('delta_return_pct_points_vs_repaired_baseline'):.4f}` pct.",
            f"- Adaptive acceleration-like momentum improved the champion by `{adaptive.get('best_incremental_delta_return_vs_champion'):.4f}` pct in the local test, but was not enough for replacement.",
            f"- V5c overheat brake lagged the champion by `{overheat.get('candidate_delta_return_pct_points_vs_primary'):.4f}` pct, so pressure is watchlist information, not a brake rule.",
            f"- Quality/value mean reversion added `{qv_reversion.get('best_incremental_delta_return_vs_champion'):.4f}` pct over the champion, so restoring-force alpha is weak in the current dividend/low-vol pool.",
            f"- Short-window shock reversion showed `{short_reversion.get('best_delta_vs_champion'):.4f}` pct internal diagnostic improvement, but it is not independently validated and remains diagnostic.",
            "",
            "## PM Reading",
            "",
            "The framework is useful because it makes the existing result easier to govern: V5f is a value-pool velocity overlay; V5c is pressure monitoring; mean reversion is restoring-force diagnosis; short-window repair is shock diagnosis. It does not by itself justify a new rule.",
            "",
        ]
    )


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Physics Curve Agent Execution Rules",
            "",
            "- Use repaired V57f baseline only.",
            "- Keep historical evidence within 2021-05-01 to 2026-05-31.",
            "- Do not modify V57f core, sleeves, target count, weights or rebalance frequency.",
            "- Do not use full-market stock selection.",
            "- Do not mark accepted, live approved or V57f replacement.",
            "- Do not use the physics framework to scan thresholds.",
            "- Do not generate buy orders or daily unbounded rebalancing from this spec.",
            "- Use physics labels only for diagnostics, PM review, feature-panel construction and forward paper notes unless separately approved.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for path in V4_REFERENCES:
        if not path.exists():
            blockers.append({"blocker_id": "missing_v4_reference", "severity": "fatal", "status": "blocking", "path": str(path)})
    for path in V5_REQUIRED:
        if not (root / path).exists():
            blockers.append({"blocker_id": "missing_v5_input", "severity": "fatal", "status": "blocking", "path": str(path)})
    return blockers


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5f_physics_curve_diagnostic_spec",
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


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
    print(json.dumps(run_v5f_physics_curve_diagnostic_spec(Path(".")), ensure_ascii=False, indent=2))

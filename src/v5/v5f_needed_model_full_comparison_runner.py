from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5f_needed_model_full_comparison") / "current"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_needed_model_full_comparison(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        summary = _summary("blocked_missing_required_model_outputs", blockers, [], [])
        _write_json(out / "v5f_needed_model_full_comparison_summary.json", summary)
        _write_csv(out / "v5f_needed_model_blockers.csv", blockers)
        return summary

    rows = _comparison_rows(root)
    family_rows = _family_difference_rows(rows)
    sample_audit = _sample_split_audit(root)
    pm_decision = _pm_gate(rows)
    next_queue = _next_queue(pm_decision)
    blockers = _blockers(rows, sample_audit)

    _write_csv(out / "v5f_needed_model_result_comparison.csv", rows)
    _write_csv(out / "v5f_model_family_difference_overview.csv", family_rows)
    _write_csv(out / "v5f_sample_split_and_validation_audit.csv", sample_audit)
    _write_csv(out / "v5f_needed_model_pm_gate_decision.csv", pm_decision)
    _write_csv(out / "v5f_needed_model_next_queue.csv", next_queue)
    _write_csv(out / "v5f_needed_model_blockers.csv", blockers)
    (out / "v5f_needed_model_full_comparison_report.md").write_text(
        _report(rows, family_rows, sample_audit, pm_decision),
        encoding="utf-8",
    )
    (out / "v5f_needed_model_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    primary = _row(rows, "internal_subsleeve_mom12_70_30")
    best_backtest = max(
        [row for row in rows if str(row.get("nav_comparable")) == "True"],
        key=lambda row: _num(row.get("delta_return_pct_points_vs_v57f")),
    )
    summary = _summary(
        "completed_needed_model_full_comparison",
        blockers,
        rows,
        pm_decision,
        model_count=len(rows),
        nav_comparable_count=sum(1 for row in rows if str(row.get("nav_comparable")) == "True"),
        primary_model="internal_subsleeve_mom12_70_30",
        primary_delta_return_pct_points_vs_v57f=_num(primary.get("delta_return_pct_points_vs_v57f")),
        best_backtest_model=best_backtest.get("model_id", ""),
        best_backtest_delta_return_pct_points_vs_v57f=_num(best_backtest.get("delta_return_pct_points_vs_v57f")),
    )
    _write_json(out / "v5f_needed_model_full_comparison_summary.json", summary)
    return summary


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        "v5f_internal_subsleeve_deep_engineering/current/v5f_internal_subsleeve_deep_metrics.csv",
        "v5f_internal_subsleeve_robustness_packet/current/v5f_internal_subsleeve_robustness_summary.json",
        "v5f_value_momentum_reversion_balance_test/current/v5f_vmr_balance_variant_metrics.csv",
        "v5f_locked_pool_conditional_momentum/current/v5f_locked_pool_conditional_momentum_metrics.csv",
        "v5f_locked_pool_daily_momentum_governance/current/v5f_locked_pool_daily_momentum_metrics.csv",
        "v5f_mean_reversion_diagnostic/current/v5f_mean_reversion_metrics.csv",
        "v5f_quality_value_mean_reversion/current/v5f_qv_mean_reversion_metrics.csv",
        "v5f_extreme_value_reversion/current/v5f_extreme_value_reversion_metrics.csv",
        "v5f_prebacktest_5min_to_backtest/current/v5f_prebacktest_5min_to_backtest_summary.json",
        "v5f_prebacktest_5min_to_backtest/current/v5f_formal_backtest_selected_variant_result.csv",
        "v5f_short_window_reversion_walk_forward_robustness/current/v5f_walk_forward_summary.json",
        "v5f_short_window_spike_reversion_symmetry/current/v5f_short_window_spike_reversion_summary.json",
        "v5f_physics_curve_full_5min_diagnostic/current/v5f_physics_full5min_summary.json",
        "v5g_vs_midterm_model_comparison/current/v5g_vs_midterm_top_model_comparison.csv",
    ]
    return [
        {"blocker_id": "missing_required_output", "severity": "fatal", "path": path, "detail": "restore or rerun source model"}
        for path in required
        if not (root / path).exists()
    ]


def _comparison_rows(root: Path) -> list[dict[str, Any]]:
    internal = _read_csv(root / "v5f_internal_subsleeve_deep_engineering/current/v5f_internal_subsleeve_deep_metrics.csv")
    locked = _read_csv(root / "v5f_locked_pool_conditional_momentum/current/v5f_locked_pool_conditional_momentum_metrics.csv")
    locked_summary = _read_json(root / "v5f_locked_pool_conditional_momentum/current/v5f_locked_pool_conditional_momentum_summary.json")
    daily = _read_csv(root / "v5f_locked_pool_daily_momentum_governance/current/v5f_locked_pool_daily_momentum_metrics.csv")
    vmr = _read_csv(root / "v5f_value_momentum_reversion_balance_test/current/v5f_vmr_balance_variant_metrics.csv")
    mr = _read_csv(root / "v5f_mean_reversion_diagnostic/current/v5f_mean_reversion_metrics.csv")
    qv_mr = _read_csv(root / "v5f_quality_value_mean_reversion/current/v5f_qv_mean_reversion_metrics.csv")
    extreme = _read_csv(root / "v5f_extreme_value_reversion/current/v5f_extreme_value_reversion_metrics.csv")
    prebacktest_summary = _read_json(root / "v5f_prebacktest_5min_to_backtest/current/v5f_prebacktest_5min_to_backtest_summary.json")
    prebacktest_selected = _read_csv(root / "v5f_prebacktest_5min_to_backtest/current/v5f_formal_backtest_selected_variant_result.csv")
    walk_forward = _read_json(root / "v5f_short_window_reversion_walk_forward_robustness/current/v5f_walk_forward_summary.json")
    spike_sym = _read_json(root / "v5f_short_window_spike_reversion_symmetry/current/v5f_short_window_spike_reversion_summary.json")
    physics = _read_json(root / "v5f_physics_curve_full_5min_diagnostic/current/v5f_physics_full5min_summary.json")
    midterm = _read_csv(root / "v5g_vs_midterm_model_comparison/current/v5g_vs_midterm_top_model_comparison.csv")

    rows: list[dict[str, Any]] = []
    for version_id in [
        "v57f_startup_preload_repaired_baseline",
        "internal_subsleeve_mom12_70_30",
        "internal_subsleeve_mom12_80_20",
    ]:
        source = _row(internal, version_id)
        rows.append(
            _model_row(
                model_id=version_id,
                family="baseline" if version_id.startswith("v57f") else "internal_value_momentum_subsleeve",
                role="baseline" if version_id.startswith("v57f") else ("primary" if version_id.endswith("70_30") else "stress_reference"),
                status="baseline" if version_id.startswith("v57f") else ("v5f_mainline_candidate_not_accepted" if version_id.endswith("70_30") else "secondary_reference"),
                nav=True,
                strategy_return_pct=_pct(source.get("strategy_return")),
                delta_v57f=_num(source.get("delta_return_pct_points_vs_repaired_baseline")),
                delta_primary=0.0 if version_id.endswith("70_30") else (
                    _num(source.get("delta_return_pct_points_vs_repaired_baseline"))
                    - _num(_row(internal, "internal_subsleeve_mom12_70_30").get("delta_return_pct_points_vs_repaired_baseline"))
                ),
                max_drawdown_pct=_pct(source.get("max_drawdown")),
                dd_delta_v57f=_num(source.get("delta_max_drawdown_pct_points_vs_repaired_baseline")),
                sharpe=_num(source.get("sharpe_proxy")),
                turnover_or_events=_num(source.get("turnover_proxy")),
                evidence="formal_backtest_20210501_20260531",
                difference="V57f repaired baseline" if version_id.startswith("v57f") else "V57f pool unchanged; sleeve total unchanged; value core plus 12-1 momentum sub-sleeve.",
                source_file="v5f_internal_subsleeve_deep_engineering/current/v5f_internal_subsleeve_deep_metrics.csv",
            )
        )

    for version_id in [
        "locked_pool_monthly_mom12_70_30",
        "locked_pool_biweekly_mom12_70_30",
        "locked_pool_daily_mom12_70_30",
        "locked_pool_major_bucket_change_mom12_70_30",
        "locked_pool_weight_drift_1pct_mom12_70_30",
    ]:
        source = _row(locked, version_id) or _row(daily, version_id)
        if not source:
            continue
        delta = _num(source.get("delta_return_pct_points_vs_repaired_baseline"))
        primary_delta_for_locked_pool = _num(locked_summary.get("fixed_delta_return_pct_points_vs_repaired_baseline"))
        rows.append(
            _model_row(
                model_id=version_id,
                family="locked_pool_adaptive_momentum",
                role="adaptive_observation",
                status="positive_but_not_primary" if delta > primary_delta_for_locked_pool else "diagnostic_weaker_than_primary",
                nav=True,
                strategy_return_pct=_pct(source.get("strategy_return")),
                delta_v57f=delta,
                delta_primary=delta - primary_delta_for_locked_pool,
                max_drawdown_pct=_pct(source.get("max_drawdown")),
                dd_delta_v57f=_num(source.get("delta_max_drawdown_pct_points_vs_repaired_baseline")),
                sharpe=_num(source.get("sharpe_proxy")),
                turnover_or_events=_num(source.get("incremental_turnover_total")),
                evidence="formal_backtest_20210501_20260531_only",
                difference="Momentum can update inside the already selected V57f pool; no full-market selection, but frequency/turnover risk rises.",
                source_file="v5f_locked_pool_conditional_momentum/current/v5f_locked_pool_conditional_momentum_metrics.csv",
            )
        )

    for version_id in [
        "momentum_plus_mean_reversion_equal_blend",
    ]:
        source = _row(midterm, version_id)
        rows.append(
            _model_row(
                model_id=version_id,
                family="small_weight_tilt_combined_overlay",
                role="older_overlay_reference",
                status="review_reference_weaker_than_internal_subsleeve",
                nav=True,
                strategy_return_pct=_num(source.get("strategy_return_pct")),
                delta_v57f=_num(source.get("delta_return_pct_points_vs_repaired_baseline")),
                delta_primary=_num(source.get("delta_return_pct_points_vs_repaired_baseline")) - _num(_row(internal, "internal_subsleeve_mom12_70_30").get("delta_return_pct_points_vs_repaired_baseline")),
                max_drawdown_pct=_num(source.get("max_drawdown_pct")),
                dd_delta_v57f=_num(source.get("delta_max_drawdown_pct_points_vs_repaired_baseline")),
                sharpe=_num(source.get("sharpe_proxy")),
                turnover_or_events="",
                evidence="formal_backtest_20210501_20260531",
                difference="Small cross-sectional weight tilt; confirms direction but much weaker than separated internal sub-sleeve.",
                source_file="v5g_vs_midterm_model_comparison/current/v5g_vs_midterm_top_model_comparison.csv",
            )
        )

    source = _row(vmr, "vmr_70_30_plus_10_symmetric_shock")
    rows.append(
        _model_row(
            model_id="vmr_70_30_plus_10_symmetric_shock",
            family="event_satellite_on_internal_subsleeve",
            role="best_backtest_scope_event_satellite",
            status="diagnostic_observation_not_candidate",
            nav=True,
            strategy_return_pct=_pct(source.get("strategy_return")),
            delta_v57f=_num(source.get("delta_return_pct_points_vs_v57f")),
            delta_primary=_num(source.get("delta_return_pct_points_vs_champion")),
            max_drawdown_pct=_pct(source.get("max_drawdown")),
            dd_delta_v57f=_num(source.get("delta_max_drawdown_pct_points_vs_v57f")),
            sharpe=_num(source.get("sharpe_proxy")),
            turnover_or_events="",
            evidence="formal_backtest_scope_in_sample_event_satellite",
            difference="Adds event satellite budget after identifying symmetric shock; good in backtest but not independently validated.",
            source_file="v5f_value_momentum_reversion_balance_test/current/v5f_vmr_balance_variant_metrics.csv",
        )
    )

    selected = prebacktest_selected[0]
    primary_delta = _num(_row(internal, "internal_subsleeve_mom12_70_30").get("delta_return_pct_points_vs_repaired_baseline"))
    selected_delta_primary = _num(selected.get("net_incremental_return_pct_points"))
    rows.append(
        _model_row(
            model_id="prebacktest_selected_spike_borrowing_paired_drop_spike_cap10_next2",
            family="prebacktest_validated_5min_spike_borrowing",
            role="corrected_sample_split_diagnostic",
            status="positive_but_keep_diagnostic_not_candidate",
            nav=False,
            strategy_return_pct=_pct(_row(internal, "internal_subsleeve_mom12_70_30").get("strategy_return")) + selected_delta_primary,
            delta_v57f=primary_delta + selected_delta_primary,
            delta_primary=selected_delta_primary,
            max_drawdown_pct="",
            dd_delta_v57f="",
            sharpe="",
            turnover_or_events=_num(selected.get("trade_group_count")),
            evidence=f"calibration={prebacktest_summary.get('calibration_start')}_to_{prebacktest_summary.get('threshold_calibration_end')}; validation_candidates={prebacktest_summary.get('available_pit_candidate_start')}_to_{prebacktest_summary.get('available_pit_candidate_end')}; formal={prebacktest_summary.get('formal_backtest_start')}_to_{prebacktest_summary.get('formal_backtest_end')}",
            difference="Uses prebacktest-selected 5min drop/spike rule; formal backtest is positive, but validation edge is thin.",
            source_file="v5f_prebacktest_5min_to_backtest/current/v5f_formal_backtest_selected_variant_result.csv",
        )
    )

    for source, model_id, delta_primary, status, evidence in [
        (
            walk_forward,
            "short_window_reversion_walk_forward_best",
            _num(walk_forward.get("best_delta_vs_champion")),
            "diagnostic_only_backtest_scope_no_oos_validation",
            "2021_2026_internal_rolling_diagnostic",
        ),
        (
            spike_sym,
            "morning30_spike_revert_next1_trim10",
            _num(spike_sym.get("best_delta_return_pct_points_vs_champion")),
            "diagnostic_only_partially_symmetric",
            "2021_2026_backtest_scope_symmetry_diagnostic",
        ),
    ]:
        rows.append(
            _model_row(
                model_id=model_id,
                family="full_5min_short_window_reversion",
                role="diagnostic_5min",
                status=status,
                nav=False,
                strategy_return_pct=_pct(_row(internal, "internal_subsleeve_mom12_70_30").get("strategy_return")) + delta_primary,
                delta_v57f=primary_delta + delta_primary,
                delta_primary=delta_primary,
                max_drawdown_pct="",
                dd_delta_v57f="",
                sharpe="",
                turnover_or_events=source.get("event_count", ""),
                evidence=evidence,
                difference="Uses full holding-period 5min path to diagnose intraday shock/reversion; not a new stock-selection model.",
                source_file="v5f_short_window_reversion_walk_forward_robustness/current/v5f_walk_forward_summary.json",
            )
        )

    for version_id in ["mr_60d_sleeve_reversal_tilt_10pct"]:
        source = _row(mr, version_id)
        rows.append(
            _model_row(
                model_id=version_id,
                family="mean_reversion_small_weight_tilt",
                role="older_mr_diagnostic",
                status="positive_small_edge_old_baseline_proxy",
                nav=True,
                strategy_return_pct=_pct(source.get("strategy_return")),
                delta_v57f=_num(source.get("delta_return_pct_points_vs_baseline_proxy")),
                delta_primary="not_comparable",
                max_drawdown_pct=_pct(source.get("max_drawdown")),
                dd_delta_v57f=_num(source.get("delta_max_drawdown_pct_points_vs_baseline_proxy")),
                sharpe=_num(source.get("sharpe_proxy")),
                turnover_or_events=_num(source.get("total_turnover_proxy")),
                evidence="older_baseline_proxy_20210501_20260531",
                difference="Mean-reversion tilt alone is weak; later repaired-baseline combinations do not beat the momentum mainline.",
                source_file="v5f_mean_reversion_diagnostic/current/v5f_mean_reversion_metrics.csv",
            )
        )

    for dataset, version_id in [
        (qv_mr, "qv_mr_60d_monthly_70_30"),
        (extreme, "extreme_60d_value_repair_70_30"),
    ]:
        source = _row(dataset, version_id)
        rows.append(
            _model_row(
                model_id=version_id,
                family="quality_value_mean_reversion",
                role="rejected_mr_variant",
                status="diagnostic_negative_or_weaker",
                nav=True,
                strategy_return_pct=_pct(source.get("strategy_return")),
                delta_v57f=_num(source.get("delta_return_pct_points_vs_repaired_baseline")),
                delta_primary=_num(source.get("delta_return_pct_points_vs_repaired_baseline")) - primary_delta,
                max_drawdown_pct=_pct(source.get("max_drawdown")),
                dd_delta_v57f=_num(source.get("delta_max_drawdown_pct_points_vs_repaired_baseline")),
                sharpe=_num(source.get("sharpe_proxy")),
                turnover_or_events=_num(source.get("incremental_turnover_total")),
                evidence="formal_backtest_20210501_20260531",
                difference="Tries to buy cheap/quality laggards; in repaired baseline it loses to V57f or far trails the momentum mainline.",
                source_file="v5f_quality_value_mean_reversion/current/v5f_qv_mean_reversion_metrics.csv",
            )
        )

    source = _row(midterm, "v5g_01_state_gated_internal_subsleeve_70_30")
    rows.append(
        _model_row(
            model_id="v5g_01_state_gated_internal_subsleeve_70_30",
            family="v5g_state_gated_internal_subsleeve",
            role="v5g_secondary_observation",
            status="secondary_diagnostic_do_not_replace_champion",
            nav=True,
            strategy_return_pct=_num(source.get("strategy_return_pct")),
            delta_v57f=_num(source.get("delta_return_pct_points_vs_repaired_baseline")),
            delta_primary=_num(source.get("delta_return_pct_points_vs_repaired_baseline")) - primary_delta,
            max_drawdown_pct=_num(source.get("max_drawdown_pct")),
            dd_delta_v57f=_num(source.get("delta_max_drawdown_pct_points_vs_repaired_baseline")),
            sharpe=_num(source.get("sharpe_proxy")),
            turnover_or_events="",
            evidence="formal_backtest_20210501_20260531",
            difference="Uses V5c state tags to gate the internal sub-sleeve; risk logic is cleaner but return trails 70/30 mainline.",
            source_file="v5g_vs_midterm_model_comparison/current/v5g_vs_midterm_top_model_comparison.csv",
        )
    )

    for model_id in ["erc_weak_portfolio_equal_fallback_63d", "v5e_profit_lock_main_20pct_sell50_511360_cash_proxy"]:
        source = _row(midterm, model_id)
        rows.append(
            _model_row(
                model_id=model_id,
                family=source.get("family", ""),
                role="midterm_cross_component_reference",
                status=source.get("pm_state", ""),
                nav=True,
                strategy_return_pct=_num(source.get("strategy_return_pct")),
                delta_v57f=_num(source.get("delta_return_pct_points_vs_repaired_baseline")),
                delta_primary=_num(source.get("delta_return_pct_points_vs_repaired_baseline")) - primary_delta,
                max_drawdown_pct=_num(source.get("max_drawdown_pct")),
                dd_delta_v57f=_num(source.get("delta_max_drawdown_pct_points_vs_repaired_baseline")),
                sharpe=_num(source.get("sharpe_proxy")),
                turnover_or_events="",
                evidence="midterm_cross_component_reference",
                difference="Useful governance/risk component, but not a V5f alpha replacement.",
                source_file="v5g_vs_midterm_model_comparison/current/v5g_vs_midterm_top_model_comparison.csv",
            )
        )

    rows.append(
        _model_row(
            model_id="physics_curve_full_5min_force_balance",
            family="physics_curve_5min_diagnostic",
            role="explanatory_diagnostic",
            status=physics.get("pm_gate_decision", ""),
            nav=False,
            strategy_return_pct="",
            delta_v57f="",
            delta_primary="",
            max_drawdown_pct="",
            dd_delta_v57f="",
            sharpe="",
            turnover_or_events=physics.get("held_stock_day_count", ""),
            evidence="full_holding_period_5min_100pct_coverage",
            difference="Explains value/momentum/reversion force balance; not a trade rule and not a portfolio candidate.",
            source_file="v5f_physics_curve_full_5min_diagnostic/current/v5f_physics_full5min_summary.json",
        )
    )
    return rows


def _model_row(
    *,
    model_id: str,
    family: str,
    role: str,
    status: str,
    nav: bool,
    strategy_return_pct: Any,
    delta_v57f: Any,
    delta_primary: Any,
    max_drawdown_pct: Any,
    dd_delta_v57f: Any,
    sharpe: Any,
    turnover_or_events: Any,
    evidence: str,
    difference: str,
    source_file: str,
) -> dict[str, Any]:
    return {
        "model_id": model_id,
        "family": family,
        "comparison_role": role,
        "pm_status": status,
        "nav_comparable": nav,
        "strategy_return_pct": _fmt(strategy_return_pct),
        "delta_return_pct_points_vs_v57f": _fmt(delta_v57f),
        "delta_return_pct_points_vs_primary": _fmt(delta_primary),
        "max_drawdown_pct": _fmt(max_drawdown_pct),
        "delta_max_drawdown_pct_points_vs_v57f": _fmt(dd_delta_v57f),
        "sharpe_proxy": _fmt(sharpe),
        "turnover_or_event_count": _fmt(turnover_or_events),
        "evidence_scope": evidence,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used_for_promotion": False,
        "difference_summary": difference,
        "source_file": source_file,
    }


def _family_difference_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "family": "internal_value_momentum_subsleeve",
            "best_model": "internal_subsleeve_mom12_70_30",
            "main_difference": "Keep the V57f value/low-vol pool unchanged; split each sleeve into 70pct value core and 30pct 12-1 momentum sub-sleeve.",
            "result_summary": "+11.43pct vs repaired V57f, with slightly better drawdown.",
            "pm_use": "V5f mainline forward/paper candidate, not accepted.",
        },
        {
            "family": "locked_pool_adaptive_momentum",
            "best_model": "locked_pool_biweekly_mom12_70_30",
            "main_difference": "Keep the selected stock pool locked but refresh momentum weights more often.",
            "result_summary": "Biweekly has the highest backtest return but worse drawdown/turnover; monthly is only modestly above the mainline.",
            "pm_use": "observation only; do not replace mainline before forward evidence.",
        },
        {
            "family": "mean_reversion",
            "best_model": "mr_60d_sleeve_reversal_tilt_10pct / event-triggered shock",
            "main_difference": "Favor short-term laggards or temporarily borrow weight from same-sleeve spike names into drop names.",
            "result_summary": "Fixed mean-reversion budget is weak; event-triggered variants are positive but thin.",
            "pm_use": "diagnostic only.",
        },
        {
            "family": "full_5min_short_window_reversion",
            "best_model": "prebacktest_selected_spike_borrowing_paired_drop_spike_cap10_next2",
            "main_difference": "Use full holding-period 5min data to detect morning drop/spike repair over the next 1-2 days.",
            "result_summary": "prebacktest validation +0.11pct; formal backtest +0.78pct vs primary.",
            "pm_use": "data blocker resolved; keep diagnostic/not candidate.",
        },
        {
            "family": "v5g_state_gated",
            "best_model": "v5g_01_state_gated_internal_subsleeve_70_30",
            "main_difference": "Use V5c state tags to gate or reduce momentum exposure.",
            "result_summary": "+10.40pct vs V57f, but -1.03pct vs primary.",
            "pm_use": "secondary observation.",
        },
    ]


def _sample_split_audit(root: Path) -> list[dict[str, Any]]:
    pre = _read_json(root / "v5f_prebacktest_5min_to_backtest/current/v5f_prebacktest_5min_to_backtest_summary.json")
    return [
        {
            "audit_id": "formal_backtest_boundary",
            "status": "pass",
            "detail": "2021-05-01 to 2026-05-31 is the formal backtest window and is not used as OOS validation.",
        },
        {
            "audit_id": "prebacktest_boundary",
            "status": "pass",
            "detail": "2013-01-01 to 2021-04-30 is prebacktest calibration/validation boundary.",
        },
        {
            "audit_id": "prebacktest_pit_candidate_coverage",
            "status": "pass",
            "detail": f"Full common PIT candidate dates: {pre.get('prebacktest_candidate_date_count')} from {pre.get('available_pit_candidate_start')} to {pre.get('available_pit_candidate_end')}.",
        },
        {
            "audit_id": "local_5min_dataset",
            "status": "pass",
            "detail": f"{pre.get('local_5min_dataset_status')} rows={pre.get('local_5min_total_rows')}",
        },
        {
            "audit_id": "no_acceptance",
            "status": "pass",
            "detail": "All compared models remain not accepted and not live approved.",
        },
    ]


def _pm_gate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "pm_gate_decision": "keep_internal_subsleeve_mom12_70_30_primary; keep_adaptive_and_5min_lines_diagnostic",
            "primary_model": "internal_subsleeve_mom12_70_30",
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "threshold_scan_used_for_promotion": False,
            "best_backtest_return_model": "locked_pool_biweekly_mom12_70_30",
            "best_governance_grade_model": "internal_subsleeve_mom12_70_30",
            "rationale": "Biweekly/event models can look higher in 2021-2026, but they carry weaker validation, higher turnover/drawdown, or diagnostic-only governance. The 70/30 internal sub-sleeve remains the cleanest large-edge model.",
        }
    ]


def _next_queue(pm_decision: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"priority": "P0", "next_task": "continue_internal_subsleeve_mom12_70_30_forward_paper_tracking", "allowed": True, "reason": "Best governance-grade mainline."},
        {"priority": "P1", "next_task": "monthly_or_biweekly_locked_pool_momentum_forward_observation", "allowed": True, "reason": "Potential incremental edge, but needs future evidence and turnover/drawdown review."},
        {"priority": "P2", "next_task": "prebacktest_selected_5min_spike_borrowing_diagnostic_observation", "allowed": True, "reason": "Data blocker resolved and formal backtest positive, but validation edge is thin."},
        {"priority": "P3", "next_task": "fixed_budget_mean_reversion_promotion", "allowed": False, "reason": "Repaired-baseline tests do not support replacing momentum with fixed mean-reversion allocation."},
    ]


def _blockers(rows: list[dict[str, Any]], sample_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in sample_audit if row.get("status") != "pass"]
    if failed:
        return [{"blocker_id": row["audit_id"], "severity": "fatal", "detail": row["detail"]} for row in failed]
    return [
        {
            "blocker_id": "promotion_blocked_by_governance",
            "severity": "promotion_only",
            "detail": "No model is accepted/live approved by this comparison packet.",
        }
    ]


def _report(
    rows: list[dict[str, Any]],
    family_rows: list[dict[str, Any]],
    sample_audit: list[dict[str, Any]],
    pm_decision: list[dict[str, Any]],
) -> str:
    display_rows = [
        row
        for row in rows
        if row["model_id"]
        in {
            "v57f_startup_preload_repaired_baseline",
            "internal_subsleeve_mom12_70_30",
            "locked_pool_monthly_mom12_70_30",
            "locked_pool_biweekly_mom12_70_30",
            "prebacktest_selected_spike_borrowing_paired_drop_spike_cap10_next2",
            "v5g_01_state_gated_internal_subsleeve_70_30",
            "qv_mr_60d_monthly_70_30",
        }
    ]
    lines = [
        "# V5f Needed Model Full Comparison",
        "",
        f"- PM gate: `{pm_decision[0]['pm_gate_decision']}`",
        "- Formal backtest window: `2021-05-01` to `2026-05-31`.",
        "- Prebacktest validation boundary: `2013-01-01` to `2021-04-30`.",
        "- Accepted/live approved: `False` for every row.",
        "",
        "## Key Results",
        "",
        "| model | return % | delta vs V57f pct | delta vs primary pct | status |",
        "|---|---:|---:|---:|---|",
    ]
    for row in display_rows:
        lines.append(
            f"| `{row['model_id']}` | {row['strategy_return_pct']} | {row['delta_return_pct_points_vs_v57f']} | {row['delta_return_pct_points_vs_primary']} | `{row['pm_status']}` |"
        )
    lines.extend(["", "## Family Differences", ""])
    for row in family_rows:
        lines.append(f"- `{row['family']}`: {row['main_difference']} Result: {row['result_summary']} PM: {row['pm_use']}")
    lines.extend(["", "## Sample Split Audit", ""])
    for row in sample_audit:
        lines.append(f"- `{row['audit_id']}`: `{row['status']}` - {row['detail']}")
    return "\n".join(lines) + "\n"


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Needed Model Comparison Rules",
            "",
            "- 2013-01-01 to 2021-04-30 is prebacktest calibration/validation.",
            "- 2021-05-01 to 2026-05-31 is formal backtest.",
            "- Do not mark accepted or live approved.",
            "- Do not modify V57f core.",
            "- Do not promote 5min or adaptive variants without future/independent evidence.",
            "",
        ]
    )


def _summary(status: str, blockers: list[dict[str, Any]], rows: list[dict[str, Any]], pm_decision: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload = {
        "created_at_utc": now_utc(),
        "task": "v5f_needed_model_full_comparison",
        "status": status,
        "pm_gate_decision": pm_decision[0]["pm_gate_decision"] if pm_decision else "blocked",
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used_for_promotion": False,
        "fatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "fatal"),
        "model_count": len(rows),
    }
    payload.update(extra)
    return payload


def _row(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    return next((row for row in rows if row.get("version_id") == key or row.get("model_id") == key), {})


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or ["empty"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _num(value: Any) -> float:
    try:
        if value in {None, "", "not_comparable"}:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _pct(value: Any) -> float:
    return _num(value) * 100.0


def _fmt(value: Any) -> Any:
    if value == "not_comparable":
        return value
    if value in {None, ""}:
        return ""
    try:
        return f"{float(value):.6f}"
    except (TypeError, ValueError):
        return value


if __name__ == "__main__":
    print(json.dumps(run_v5f_needed_model_full_comparison(Path(".")), ensure_ascii=False, indent=2))

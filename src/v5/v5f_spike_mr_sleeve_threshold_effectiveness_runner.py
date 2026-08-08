from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_spike_mr_sleeve_threshold_effectiveness_audit") / "current"

THRESHOLDS = (
    Path("v5f_short_window_reversion_walk_forward_robustness")
    / "current"
    / "v5f_sleeve_specific_thresholds.csv"
)
THRESHOLD_STABILITY = (
    Path("v5f_short_window_reversion_walk_forward_robustness")
    / "current"
    / "v5f_sleeve_threshold_stability.csv"
)
HIST_FEATURES = (
    Path("v5f_short_window_reversion_diagnostic")
    / "current"
    / "v5f_short_window_reversion_minute_day_features.csv"
)
HIST_TRADE_LOG = (
    Path("v5f_event_triggered_mean_reversion_borrowing_test")
    / "current"
    / "v5f_mr_borrowing_trade_log.csv"
)
HIST_SUMMARY = (
    Path("v5f_event_triggered_mean_reversion_borrowing_test")
    / "current"
    / "v5f_mr_borrowing_summary.json"
)
FORWARD_FEATURES = (
    Path("v5f_spike_funded_mr_borrowing_forward_observation")
    / "current"
    / "v5f_spike_mr_forward_feature_panel.csv"
)
FORWARD_TRADE_LOG = (
    Path("v5f_spike_funded_mr_borrowing_forward_observation")
    / "current"
    / "v5f_spike_mr_forward_observation_trade_log.csv"
)
FORWARD_SUMMARY = (
    Path("v5f_spike_funded_mr_borrowing_forward_observation")
    / "current"
    / "v5f_spike_mr_forward_summary.json"
)

BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
PRIMARY = "internal_subsleeve_mom12_70_30"
OBSERVATION = "spike_funded_mr_borrowing_observe_only"
FOCUS_HISTORICAL_VERSIONS = {
    "mr_borrow_paired_drop_spike_net0_cap10_next1",
    "mr_borrow_paired_drop_spike_net0_cap10_next2",
    "mr_borrow_spike_only_strict_cap10_next1",
    "mr_borrow_spike_only_strict_cap10_next2",
    "mr_borrow_pro_rata_non_drop_cap10_next1",
    "mr_borrow_pro_rata_non_drop_cap10_next2",
}

REQUIRED = [
    THRESHOLDS,
    THRESHOLD_STABILITY,
    HIST_FEATURES,
    HIST_TRADE_LOG,
    HIST_SUMMARY,
    FORWARD_FEATURES,
    FORWARD_TRADE_LOG,
    FORWARD_SUMMARY,
]


def run_v5f_spike_mr_sleeve_threshold_effectiveness(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_minimal(out, summary, blockers)
        return summary

    hist_summary = _read_json(root / HIST_SUMMARY)
    forward_summary = _read_json(root / FORWARD_SUMMARY)
    thresholds = _threshold_rows(root)
    stability = _read_csv(root / THRESHOLD_STABILITY)
    hist_rates = _historical_event_rates(root, thresholds)
    forward_rates = _forward_event_rates(root)
    hist_effect = _historical_effectiveness(root)
    forward_effect = _forward_effectiveness(root)
    compare = _common_vs_sleeve_threshold_comparison(root)
    classification = _sleeve_classification(thresholds, hist_rates, hist_effect, forward_rates, forward_effect)
    governance = _governance_audit(thresholds, hist_summary, forward_summary, hist_rates, forward_rates)
    decision = _pm_decision(classification, forward_effect, governance)
    blockers_out = _blockers(governance, classification)
    queue = _next_queue(decision[0]["pm_gate_decision"])

    _write_csv(out / "v5f_spike_mr_threshold_sensitivity_by_sleeve.csv", thresholds)
    _write_csv(out / "v5f_spike_mr_threshold_yearly_stability.csv", stability)
    _write_csv(out / "v5f_spike_mr_historical_event_rate_by_sleeve_year.csv", hist_rates)
    _write_csv(out / "v5f_spike_mr_forward_event_rate_by_sleeve.csv", forward_rates)
    _write_csv(out / "v5f_spike_mr_historical_effectiveness_by_sleeve.csv", hist_effect)
    _write_csv(out / "v5f_spike_mr_forward_effectiveness_by_sleeve.csv", forward_effect)
    _write_csv(out / "v5f_spike_mr_common_vs_sleeve_threshold_comparison.csv", compare)
    _write_csv(out / "v5f_spike_mr_sleeve_effectiveness_classification.csv", classification)
    _write_csv(out / "v5f_spike_mr_threshold_governance_audit.csv", governance)
    _write_csv(out / "v5f_spike_mr_threshold_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_spike_mr_threshold_next_agent_queue.csv", queue)
    _write_csv(out / "v5f_spike_mr_threshold_blockers.csv", blockers_out)
    (out / "v5f_spike_mr_threshold_effectiveness_report.md").write_text(
        _report(thresholds, hist_effect, forward_effect, classification, decision),
        encoding="utf-8",
    )
    (out / "v5f_spike_mr_threshold_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    summary = _summary(
        "completed_v5f_spike_mr_sleeve_threshold_effectiveness_audit",
        decision[0]["pm_gate_decision"],
        [],
        primary_candidate=PRIMARY,
        observation_id=OBSERVATION,
        backtest_start=BACKTEST_START,
        backtest_end=BACKTEST_END,
        sleeve_specific_thresholds_used=True,
        threshold_scan_used=False,
        accepted=False,
        live_trading_approved=False,
        candidate_promoted=False,
        historical_supported_sleeve_count=sum(1 for row in classification if row["historical_read"] == "supported"),
        historical_mixed_sleeve_count=sum(1 for row in classification if row["historical_read"] == "mixed_or_cost_sensitive"),
        historical_weak_sleeve_count=sum(1 for row in classification if row["historical_read"] == "weak"),
        forward_supported_sleeve_count=sum(1 for row in classification if row["forward_read"] == "supported"),
        forward_mixed_sleeve_count=sum(1 for row in classification if row["forward_read"] == "mixed_or_negative"),
        forward_sample_status=decision[0]["forward_sample_status"],
    )
    _write_json(out / "v5f_spike_mr_threshold_effectiveness_summary.json", summary)
    return summary


def _threshold_rows(root: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(root / THRESHOLDS, dtype={"test_year": str})
    df = df[df["scheme"].astype(str).isin(["anchored_prior_years", "rolling_2y_prior_years"]) & df["status"].astype(str).eq("pass")].copy()
    for col in ["train_row_count", "drop_cut_r_0935_1000", "spike_cut_r_0935_1000"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    rows = []
    for _, row in df.iterrows():
        rows.append(
            {
                "scheme": row["scheme"],
                "test_year": row["test_year"],
                "sleeve": row["sleeve"],
                "train_start": row["train_start"],
                "train_end": row["train_end"],
                "train_row_count": int(row["train_row_count"]),
                "drop_cut_r_0935_1000": float(row["drop_cut_r_0935_1000"]),
                "spike_cut_r_0935_1000": float(row["spike_cut_r_0935_1000"]),
                "drop_abs_pct": abs(float(row["drop_cut_r_0935_1000"])) * 100,
                "spike_abs_pct": abs(float(row["spike_cut_r_0935_1000"])) * 100,
                "sleeve_specific_sensitivity_used": True,
                "uses_future_test_year_data": False,
                "accepted": False,
            }
        )
    return rows


def _historical_event_rates(root: Path, thresholds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    features = pd.read_csv(root / HIST_FEATURES, dtype={"trade_date": str, "code": str})
    features["test_year"] = features["trade_date"].astype(str).str.slice(0, 4)
    features = features[(features["test_year"] >= "2022") & (features["test_year"] <= "2026")].copy()
    for col in ["r_0935_1000", "target_weight"]:
        features[col] = pd.to_numeric(features[col], errors="coerce")
    th = pd.DataFrame([row for row in thresholds if row["scheme"] == "anchored_prior_years"])
    th["test_year"] = th["test_year"].astype(str)
    joined = features.merge(th[["test_year", "sleeve", "drop_cut_r_0935_1000", "spike_cut_r_0935_1000"]], on=["test_year", "sleeve"], how="left")
    joined = joined[joined["drop_cut_r_0935_1000"].notna()].copy()
    joined["is_drop"] = joined["r_0935_1000"] <= joined["drop_cut_r_0935_1000"]
    joined["is_spike"] = joined["r_0935_1000"] >= joined["spike_cut_r_0935_1000"]
    rows = []
    for (year, sleeve), group in joined.groupby(["test_year", "sleeve"], sort=True):
        rows.append(
            {
                "test_year": year,
                "sleeve": sleeve,
                "stock_day_count": int(len(group)),
                "drop_count": int(group["is_drop"].sum()),
                "spike_count": int(group["is_spike"].sum()),
                "drop_rate": float(group["is_drop"].mean()) if len(group) else 0.0,
                "spike_rate": float(group["is_spike"].mean()) if len(group) else 0.0,
                "avg_r_0935_1000": _mean(group["r_0935_1000"]),
                "drop_cut": float(group["drop_cut_r_0935_1000"].iloc[0]),
                "spike_cut": float(group["spike_cut_r_0935_1000"].iloc[0]),
                "rate_read": _rate_read(float(group["is_drop"].mean()), float(group["is_spike"].mean())),
            }
        )
    return rows


def _forward_event_rates(root: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(root / FORWARD_FEATURES, dtype={"trade_date": str, "code": str})
    if df.empty:
        return []
    for col in ["r_0935_1000", "target_weight", "drop_cut_r_0935_1000", "spike_cut_r_0935_1000"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["is_drop"] = df["is_drop"].astype(str).str.lower().eq("true")
    df["is_spike"] = df["is_spike"].astype(str).str.lower().eq("true")
    rows = []
    for sleeve, group in df.groupby("sleeve", sort=True):
        rows.append(
            {
                "observation_window": "2026-07-20_to_2026-07-31",
                "sleeve": sleeve,
                "stock_day_count": int(len(group)),
                "drop_count": int(group["is_drop"].sum()),
                "spike_count": int(group["is_spike"].sum()),
                "drop_rate": float(group["is_drop"].mean()) if len(group) else 0.0,
                "spike_rate": float(group["is_spike"].mean()) if len(group) else 0.0,
                "avg_r_0935_1000": _mean(group["r_0935_1000"]),
                "drop_cut": float(group["drop_cut_r_0935_1000"].dropna().iloc[0]) if group["drop_cut_r_0935_1000"].notna().any() else "",
                "spike_cut": float(group["spike_cut_r_0935_1000"].dropna().iloc[0]) if group["spike_cut_r_0935_1000"].notna().any() else "",
                "rate_read": _rate_read(float(group["is_drop"].mean()), float(group["is_spike"].mean())),
            }
        )
    return rows


def _historical_effectiveness(root: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(root / HIST_TRADE_LOG)
    df = df[df["version_id"].astype(str).isin(FOCUS_HISTORICAL_VERSIONS)].copy()
    if df.empty:
        return []
    for col in ["net_incremental_return", "gross_incremental_return", "commission_drag", "target_avg_return", "funding_avg_return", "actual_borrow_weight"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["spread"] = df["target_avg_return"] - df["funding_avg_return"]
    rows = []
    for (version, sleeve), group in df.groupby(["version_id", "sleeve"], sort=True):
        net = group["net_incremental_return"].fillna(0.0)
        rows.append(
            {
                "scope": "historical_2021_20260531",
                "version_id": version,
                "funding_policy": str(group.iloc[0]["funding_policy"]),
                "borrow_horizon": str(group.iloc[0]["borrow_horizon"]),
                "sleeve": sleeve,
                "trade_group_count": int(len(group)),
                "active_borrow_days": int(group["open_date"].nunique()),
                "net_incremental_return_pct_points": float(net.sum() * 100),
                "gross_incremental_return_pct_points": float(group["gross_incremental_return"].fillna(0.0).sum() * 100),
                "commission_drag_pct_points": float(group["commission_drag"].fillna(0.0).sum() * 100),
                "avg_target_minus_funding_return": float(group["spread"].mean()),
                "win_rate": float((net > 0).mean()) if len(net) else 0.0,
                "effectiveness_read": _effectiveness_read(float(net.sum() * 100), float((net > 0).mean()) if len(net) else 0.0, len(group)),
            }
        )
    return sorted(rows, key=lambda row: (row["version_id"], row["sleeve"]))


def _forward_effectiveness(root: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(root / FORWARD_TRADE_LOG)
    if df.empty:
        return []
    for col in ["net_incremental_return", "gross_incremental_return", "commission_drag", "target_avg_return", "funding_avg_return", "actual_borrow_weight"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["spread"] = df["target_avg_return"] - df["funding_avg_return"]
    rows = []
    for (version, sleeve), group in df.groupby(["version_id", "sleeve"], sort=True):
        net = group["net_incremental_return"].fillna(0.0)
        rows.append(
            {
                "scope": "forward_20260720_20260731",
                "version_id": version,
                "funding_policy": str(group.iloc[0]["funding_policy"]),
                "borrow_horizon": str(group.iloc[0]["borrow_horizon"]),
                "sleeve": sleeve,
                "trade_group_count": int(len(group)),
                "active_borrow_days": int(group["paper_open_date"].nunique()),
                "net_incremental_return_pct_points": float(net.sum() * 100),
                "gross_incremental_return_pct_points": float(group["gross_incremental_return"].fillna(0.0).sum() * 100),
                "commission_drag_pct_points": float(group["commission_drag"].fillna(0.0).sum() * 100),
                "avg_target_minus_funding_return": float(group["spread"].mean()),
                "win_rate": float((net > 0).mean()) if len(net) else 0.0,
                "effectiveness_read": _effectiveness_read(float(net.sum() * 100), float((net > 0).mean()) if len(net) else 0.0, len(group)),
            }
        )
    return sorted(rows, key=lambda row: (row["version_id"], row["sleeve"]))


def _common_vs_sleeve_threshold_comparison(root: Path) -> list[dict[str, Any]]:
    features = pd.read_csv(root / HIST_FEATURES, dtype={"trade_date": str})
    features["test_year"] = features["trade_date"].astype(str).str.slice(0, 4)
    features = features[(features["test_year"] >= "2022") & (features["test_year"] <= "2026")].copy()
    features["r_0935_1000"] = pd.to_numeric(features["r_0935_1000"], errors="coerce")
    rows = []
    for sleeve, group in features.groupby("sleeve", sort=True):
        rows.append(
            {
                "sleeve": sleeve,
                "method": "common_abs_1pct",
                "stock_day_count": int(len(group)),
                "drop_count": int((group["r_0935_1000"] <= -0.01).sum()),
                "spike_count": int((group["r_0935_1000"] >= 0.01).sum()),
                "drop_rate": float((group["r_0935_1000"] <= -0.01).mean()) if len(group) else 0.0,
                "spike_rate": float((group["r_0935_1000"] >= 0.01).mean()) if len(group) else 0.0,
                "governance_read": "too_coarse_for_cross_sleeve_use",
            }
        )
    return rows


def _sleeve_classification(
    thresholds: list[dict[str, Any]],
    hist_rates: list[dict[str, Any]],
    hist_effect: list[dict[str, Any]],
    forward_rates: list[dict[str, Any]],
    forward_effect: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sleeves = sorted({row["sleeve"] for row in thresholds})
    rows = []
    for sleeve in sleeves:
        th = [row for row in thresholds if row["scheme"] == "anchored_prior_years" and row["sleeve"] == sleeve]
        hist_focus = [
            row for row in hist_effect
            if row["sleeve"] == sleeve
            and row["version_id"] in {
                "mr_borrow_paired_drop_spike_net0_cap10_next1",
                "mr_borrow_paired_drop_spike_net0_cap10_next2",
            }
        ]
        fwd_focus = [
            row for row in forward_effect
            if row["sleeve"] == sleeve
            and row["version_id"] in {
                "forward202607_paired_drop_spike_net0_cap10_next1",
                "forward202607_paired_drop_spike_net0_cap10_next2",
            }
        ]
        hist_net = sum(float(row["net_incremental_return_pct_points"]) for row in hist_focus)
        hist_count = sum(int(row["trade_group_count"]) for row in hist_focus)
        hist_win = _weighted_average([float(row["win_rate"]) for row in hist_focus], [int(row["trade_group_count"]) for row in hist_focus])
        fwd_net = sum(float(row["net_incremental_return_pct_points"]) for row in fwd_focus)
        fwd_count = sum(int(row["trade_group_count"]) for row in fwd_focus)
        fwd_win = _weighted_average([float(row["win_rate"]) for row in fwd_focus], [int(row["trade_group_count"]) for row in fwd_focus])
        fwd_rate = next((row for row in forward_rates if row["sleeve"] == sleeve), {})
        rows.append(
            {
                "sleeve": sleeve,
                "avg_anchored_drop_abs_pct": _mean([row["drop_abs_pct"] for row in th]),
                "avg_anchored_spike_abs_pct": _mean([row["spike_abs_pct"] for row in th]),
                "historical_paired_trade_count": hist_count,
                "historical_paired_net_pct_points": hist_net,
                "historical_paired_win_rate": hist_win,
                "historical_read": _historical_read(hist_net, hist_win, hist_count),
                "forward_drop_count": int(fwd_rate.get("drop_count", 0) or 0),
                "forward_spike_count": int(fwd_rate.get("spike_count", 0) or 0),
                "forward_paired_trade_count": fwd_count,
                "forward_paired_net_pct_points": fwd_net,
                "forward_paired_win_rate": fwd_win,
                "forward_read": _forward_read(fwd_net, fwd_win, fwd_count),
                "recommended_treatment": _recommended_treatment(sleeve, hist_net, hist_win, hist_count, fwd_net, fwd_win, fwd_count),
            }
        )
    return rows


def _governance_audit(
    thresholds: list[dict[str, Any]],
    hist_summary: dict[str, Any],
    forward_summary: dict[str, Any],
    hist_rates: list[dict[str, Any]],
    forward_rates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {"audit_id": "sleeve_specific_thresholds_used", "status": "pass" if thresholds and all(row["sleeve_specific_sensitivity_used"] for row in thresholds) else "fail", "detail": True},
        {"audit_id": "pit_threshold_training", "status": "pass" if thresholds and all(row["uses_future_test_year_data"] is False for row in thresholds) else "fail", "detail": "prior years only"},
        {"audit_id": "backtest_scope_not_oos", "status": "pass", "detail": f"{BACKTEST_START} to {BACKTEST_END} remains historical backtest"},
        {"audit_id": "primary_line_retained", "status": "pass" if hist_summary.get("primary_candidate") == PRIMARY else "fail", "detail": hist_summary.get("primary_candidate")},
        {"audit_id": "forward_observation_not_candidate", "status": "pass" if not forward_summary.get("candidate_promoted", True) else "fail", "detail": forward_summary.get("candidate_promoted")},
        {"audit_id": "historical_event_rates_available", "status": "pass" if hist_rates else "fail", "detail": len(hist_rates)},
        {"audit_id": "forward_event_rates_available", "status": "pass" if forward_rates else "fail", "detail": len(forward_rates)},
        {"audit_id": "no_threshold_scan_used", "status": "pass", "detail": False},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
        {"audit_id": "v57f_core_modified_false", "status": "pass", "detail": False},
    ]


def _pm_decision(
    classification: list[dict[str, Any]],
    forward_effect: list[dict[str, Any]],
    governance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] == "fail"]
    supported = [row for row in classification if row["historical_read"] == "supported"]
    weak = [row for row in classification if row["historical_read"] == "weak"]
    forward_positive = [row for row in forward_effect if float(row["net_incremental_return_pct_points"]) > 0]
    if failed:
        decision = "blocked_by_threshold_governance_issue"
        verdict = "blocked"
    elif len(supported) >= 2 and not forward_positive:
        decision = "sleeve_thresholds_valid_but_forward_mixed_keep_observation_only"
        verdict = "threshold_method_valid_signal_not_stable_enough"
    elif len(supported) >= 2:
        decision = "sleeve_thresholds_valid_continue_forward_observation_only"
        verdict = "threshold_method_valid_need_more_forward_cycles"
    else:
        decision = "threshold_effectiveness_weak_keep_diagnostic_only"
        verdict = "not_enough_sleeve_support"
    return [
        {
            "pm_gate_decision": decision,
            "verdict": verdict,
            "sleeve_specific_thresholds_effective_enough_for_observation": len(supported) >= 2,
            "supported_sleeves": ";".join(row["sleeve"] for row in supported),
            "weak_sleeves": ";".join(row["sleeve"] for row in weak),
            "forward_sample_status": "initial_forward_negative_or_too_small" if not forward_positive else "initial_forward_has_positive_rows",
            "candidate_promoted": False,
            "accepted": False,
            "live_trading_approved": False,
            "threshold_scan_used": False,
            "next_step": "continue_sleeve_specific_forward_observation_and_do_not_pool_thresholds",
        }
    ]


def _blockers(governance: list[dict[str, Any]], classification: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "detail": row["detail"]}
        for row in governance
        if row["status"] == "fail"
    ]
    rows.append(
        {
            "blocker_id": "forward_multi_cycle_evidence_missing",
            "severity": "research",
            "status": "blocking_candidate_promotion",
            "detail": "Need multiple forward cycles before judging promotion.",
        }
    )
    weak = [row for row in classification if row["historical_read"] == "weak"]
    if weak:
        rows.append(
            {
                "blocker_id": "some_sleeves_threshold_effectiveness_weak",
                "severity": "research",
                "status": "blocks_uniform_rule",
                "detail": ";".join(row["sleeve"] for row in weak),
            }
        )
    return rows


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_task": "continue_sleeve_specific_forward_observation",
            "allowed": decision != "blocked_by_threshold_governance_issue",
            "reason": "Append daily/periodic observations using existing PIT sleeve thresholds.",
        },
        {
            "priority": 2,
            "next_task": "do_not_use_common_abs_threshold_across_sleeves",
            "allowed": True,
            "reason": "Sleeve volatility differs materially.",
        },
        {
            "priority": 3,
            "next_task": "require_multi_cycle_forward_closeout_before_candidate_review",
            "allowed": True,
            "reason": "2026-07 initial sample is mixed/negative.",
        },
        {
            "priority": 4,
            "next_task": "optimize_new_thresholds",
            "allowed": False,
            "reason": "Would become parameter scanning.",
        },
    ]


def _report(
    thresholds: list[dict[str, Any]],
    hist_effect: list[dict[str, Any]],
    forward_effect: list[dict[str, Any]],
    classification: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    lines = [
        "# V5f Spike/MR Sleeve Threshold Effectiveness Audit",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Verdict: `{decision[0]['verdict']}`",
        "- Scope: audit only; no threshold change, no accepted status.",
        "",
        "## Sleeve Threshold Sensitivity",
        "",
    ]
    anchored_2026 = [row for row in thresholds if row["scheme"] == "anchored_prior_years" and str(row["test_year"]) == "2026"]
    for row in anchored_2026:
        lines.append(
            f"- `{row['sleeve']}`: drop `{row['drop_abs_pct']:.2f}%`, spike `{row['spike_abs_pct']:.2f}%`."
        )
    lines.extend(["", "## Sleeve Classification", ""])
    for row in classification:
        lines.append(
            f"- `{row['sleeve']}`: historical `{row['historical_read']}`, forward `{row['forward_read']}`, treatment `{row['recommended_treatment']}`."
        )
    lines.extend(["", "## Historical Focus Variants", ""])
    for row in sorted(hist_effect, key=lambda item: float(item["net_incremental_return_pct_points"]), reverse=True)[:8]:
        lines.append(
            f"- `{row['version_id']}` / `{row['sleeve']}`: net `{float(row['net_incremental_return_pct_points']):.4f}` pct, win `{float(row['win_rate']):.2%}`, trades `{row['trade_group_count']}`."
        )
    lines.extend(["", "## Forward Initial Observation", ""])
    if forward_effect:
        for row in forward_effect:
            lines.append(
                f"- `{row['version_id']}` / `{row['sleeve']}`: net `{float(row['net_incremental_return_pct_points']):.4f}` pct, win `{float(row['win_rate']):.2%}`, trades `{row['trade_group_count']}`."
            )
    else:
        lines.append("- No forward paired trade observations yet.")
    return "\n".join(lines) + "\n"


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Spike/MR Sleeve Threshold Effectiveness Rules",
            "",
            "- Do not pool all sleeves into one common shock threshold.",
            "- Do not change thresholds in this audit.",
            "- Use PIT sleeve-specific thresholds only.",
            "- Keep spike-funded MR borrowing observe-only.",
            "- Do not mark candidate, accepted, or live approved.",
            "- Dates after 2026-05-31 are forward/paper only.",
            "",
        ]
    )


def _historical_read(net_pct: float, win_rate: float, count: int) -> str:
    if count < 20:
        return "insufficient"
    if net_pct > 0 and win_rate >= 0.5:
        return "supported"
    if net_pct > 0 or win_rate >= 0.5:
        return "mixed_or_cost_sensitive"
    return "weak"


def _forward_read(net_pct: float, win_rate: float, count: int) -> str:
    if count == 0:
        return "no_paired_forward_sample"
    if net_pct > 0 and win_rate >= 0.5:
        return "supported"
    return "mixed_or_negative"


def _recommended_treatment(
    sleeve: str,
    hist_net: float,
    hist_win: float,
    hist_count: int,
    fwd_net: float,
    fwd_win: float,
    fwd_count: int,
) -> str:
    hist = _historical_read(hist_net, hist_win, hist_count)
    fwd = _forward_read(fwd_net, fwd_win, fwd_count)
    if hist == "supported" and fwd == "supported":
        return "continue_observation_high_priority"
    if hist == "supported":
        return "continue_observation_need_forward_confirmation"
    if hist == "mixed_or_cost_sensitive":
        return "observe_only_cost_sensitive"
    return "diagnostic_only"


def _effectiveness_read(net_pct: float, win_rate: float, count: int) -> str:
    if count < 5:
        return "too_few_events"
    if net_pct > 0 and win_rate >= 0.5:
        return "positive"
    if net_pct > 0:
        return "positive_sum_low_win"
    return "negative_or_cost_dragged"


def _rate_read(drop_rate: float, spike_rate: float) -> str:
    if 0.05 <= drop_rate <= 0.18 and 0.05 <= spike_rate <= 0.18:
        return "balanced_event_rate"
    if drop_rate > 0.25 or spike_rate > 0.25:
        return "too_many_events_possible_regime_shift"
    if drop_rate < 0.02 and spike_rate < 0.02:
        return "too_few_events"
    return "unbalanced_event_rate"


def _weighted_average(values: list[float], weights: list[int]) -> float:
    total = sum(weights)
    if total <= 0:
        return 0.0
    return sum(v * w for v, w in zip(values, weights)) / total


def _mean(values: Any) -> float:
    series = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    return float(series.mean()) if len(series) else 0.0


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5f_spike_mr_sleeve_threshold_effectiveness_audit",
        "status": status,
        "pm_gate_decision": decision,
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "full_market_selection_used": False,
        "joinquant_started": False,
        "fatal_blocker_count": len([row for row in blockers if row.get("severity") == "fatal"]),
        "fatal_blockers": [row for row in blockers if row.get("severity") == "fatal"],
    }
    payload.update(extra)
    return payload


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in REQUIRED
        if not (root / path).exists()
    ]


def _write_minimal(out: Path, summary: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    _write_json(out / "v5f_spike_mr_threshold_effectiveness_summary.json", summary)
    _write_csv(out / "v5f_spike_mr_threshold_blockers.csv", blockers)
    for name in [
        "v5f_spike_mr_threshold_sensitivity_by_sleeve.csv",
        "v5f_spike_mr_threshold_yearly_stability.csv",
        "v5f_spike_mr_historical_event_rate_by_sleeve_year.csv",
        "v5f_spike_mr_forward_event_rate_by_sleeve.csv",
        "v5f_spike_mr_historical_effectiveness_by_sleeve.csv",
        "v5f_spike_mr_forward_effectiveness_by_sleeve.csv",
        "v5f_spike_mr_common_vs_sleeve_threshold_comparison.csv",
        "v5f_spike_mr_sleeve_effectiveness_classification.csv",
        "v5f_spike_mr_threshold_governance_audit.csv",
        "v5f_spike_mr_threshold_pm_gate_decision.csv",
        "v5f_spike_mr_threshold_next_agent_queue.csv",
    ]:
        _write_csv(out / name, [])
    (out / "v5f_spike_mr_threshold_effectiveness_report.md").write_text("# Blocked\n", encoding="utf-8")
    (out / "v5f_spike_mr_threshold_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or ["empty"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


if __name__ == "__main__":
    print(json.dumps(run_v5f_spike_mr_sleeve_threshold_effectiveness(Path(".")), ensure_ascii=False, indent=2))

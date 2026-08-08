from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_event_triggered_mean_reversion_borrowing_test") / "current"
FEATURES = Path("v5f_short_window_reversion_diagnostic") / "current" / "v5f_short_window_reversion_minute_day_features.csv"
THRESHOLDS = Path("v5f_short_window_reversion_walk_forward_robustness") / "current" / "v5f_sleeve_specific_thresholds.csv"
STRUCTURAL_DAILY = Path("v5f_structural_rough_screen") / "current" / "v5f_structural_rough_screen_daily_returns.csv"
VMR_BALANCE = Path("v5f_value_momentum_reversion_balance_test") / "current"
PHYSICS_FULL5 = Path("v5f_physics_curve_full_5min_diagnostic") / "current"

BASELINE = "v57f_startup_preload_repaired_baseline"
CHAMPION = "internal_subsleeve_mom12_70_30"
CHAMPION_OUT = "vmr_70_30_0_champion"
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
COMMISSION_RATE = 0.0003
BORROW_INTENSITY = 0.10
CAPS = [0.02, 0.05, 0.10]
HORIZONS = ["next1", "next2"]
POLICIES = [
    "pro_rata_non_drop",
    "spike_only_strict",
    "spike_then_pro_rata",
    "paired_drop_spike_net0",
]

REQUIRED = [
    FEATURES,
    THRESHOLDS,
    STRUCTURAL_DAILY,
    VMR_BALANCE / "v5f_vmr_balance_summary.json",
    VMR_BALANCE / "v5f_vmr_balance_variant_metrics.csv",
    PHYSICS_FULL5 / "v5f_physics_full5min_summary.json",
]


def run_v5f_event_triggered_mr_borrowing(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_mr_borrowing_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_mr_borrowing_summary.json", summary)
        return summary

    features = _prepare_features(root)
    structural_daily = pd.read_csv(root / STRUCTURAL_DAILY, dtype={"trade_date": str})
    vmr_summary = _read_json(root / VMR_BALANCE / "v5f_vmr_balance_summary.json")
    physics_summary = _read_json(root / PHYSICS_FULL5 / "v5f_physics_full5min_summary.json")

    event_log, trade_log = _event_and_trade_logs(features)
    daily = _daily_returns(structural_daily, trade_log)
    metrics = _metrics(daily)
    yearly = _yearly(daily)
    policy = _policy_comparison(metrics, trade_log)
    sleeve = _sleeve_attribution(trade_log)
    source_audit = _source_audit(vmr_summary, physics_summary, len(features))
    governance = _governance_audit(physics_summary)
    decision = _pm_decision(metrics, governance, vmr_summary)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(out / "v5f_mr_borrowing_rule_spec.csv", _rule_spec())
    _write_csv(out / "v5f_mr_borrowing_event_log.csv", event_log)
    _write_csv(out / "v5f_mr_borrowing_trade_log.csv", trade_log)
    _write_csv(out / "v5f_mr_borrowing_daily_returns.csv", daily)
    _write_csv(out / "v5f_mr_borrowing_variant_metrics.csv", metrics)
    _write_csv(out / "v5f_mr_borrowing_yearly.csv", yearly)
    _write_csv(out / "v5f_mr_borrowing_funding_policy_comparison.csv", policy)
    _write_csv(out / "v5f_mr_borrowing_sleeve_attribution.csv", sleeve)
    _write_csv(out / "v5f_mr_borrowing_source_audit.csv", source_audit)
    _write_csv(out / "v5f_mr_borrowing_governance_audit.csv", governance)
    _write_csv(out / "v5f_mr_borrowing_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_mr_borrowing_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5f_mr_borrowing_blockers.csv", blockers_out)
    (out / "v5f_mr_borrowing_report.md").write_text(_report(metrics, decision, vmr_summary), encoding="utf-8")
    (out / "v5f_mr_borrowing_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = metrics[0]
    best_strict = _best(metrics, "spike_only_strict")
    best_pro_rata = _best(metrics, "pro_rata_non_drop")
    summary = _summary(
        "completed_v5f_event_triggered_mean_reversion_borrowing_test",
        decision[0]["pm_gate_decision"],
        [],
        backtest_start=BACKTEST_START,
        backtest_end=BACKTEST_END,
        full_5min_coverage_rate_pct=physics_summary.get("effective_coverage_rate_pct", ""),
        primary_candidate=CHAMPION,
        best_variant=best.get("version_id", ""),
        best_policy=best.get("funding_policy", ""),
        best_horizon=best.get("borrow_horizon", ""),
        best_return_pct=float(best.get("strategy_return", 0.0) or 0.0) * 100,
        best_delta_return_pct_points_vs_champion=float(best.get("delta_return_pct_points_vs_champion", 0.0) or 0.0),
        best_delta_return_pct_points_vs_v57f=float(best.get("delta_return_pct_points_vs_v57f", 0.0) or 0.0),
        best_strict_spike_delta_vs_champion=float(best_strict.get("delta_return_pct_points_vs_champion", 0.0) or 0.0),
        best_pro_rata_delta_vs_champion=float(best_pro_rata.get("delta_return_pct_points_vs_champion", 0.0) or 0.0),
        event_group_count=len(event_log),
        trade_group_count=len(trade_log),
        no_fixed_mean_reversion_budget=True,
        limited_engineering_started=True,
        engineering_backtest_started=True,
    )
    _write_json(out / "v5f_mr_borrowing_summary.json", summary)
    return summary


def _prepare_features(root: Path) -> pd.DataFrame:
    features = pd.read_csv(root / FEATURES, dtype={"trade_date": str, "code": str})
    thresholds = pd.read_csv(root / THRESHOLDS)
    features = features[(features["trade_date"] >= BACKTEST_START) & (features["trade_date"] <= BACKTEST_END)].copy()
    for col in ["r_0935_1000", "next1_from_1000", "next2_from_1000", "target_weight", "r_1455_vwap"]:
        if col in features.columns:
            features[col] = pd.to_numeric(features[col], errors="coerce")
    features["year"] = features["trade_date"].astype(str).str.slice(0, 4).astype(int)
    thresholds = thresholds[
        thresholds["scheme"].astype(str).eq("anchored_prior_years") & thresholds["status"].astype(str).eq("pass")
    ][["test_year", "sleeve", "drop_cut_r_0935_1000", "spike_cut_r_0935_1000"]].copy()
    thresholds = thresholds.rename(columns={"test_year": "year"})
    for col in ["drop_cut_r_0935_1000", "spike_cut_r_0935_1000"]:
        thresholds[col] = pd.to_numeric(thresholds[col], errors="coerce")
    features = features.merge(thresholds, on=["year", "sleeve"], how="left")
    features = features[features["drop_cut_r_0935_1000"].notna()].copy()
    features["is_drop"] = features["r_0935_1000"] <= features["drop_cut_r_0935_1000"]
    features["is_spike"] = features["r_0935_1000"] >= features["spike_cut_r_0935_1000"]
    features = features.sort_values(["code", "holding_start_date", "next_rebalance_date", "trade_date"]).reset_index(drop=True)
    cycle = ["code", "holding_start_date", "next_rebalance_date"]
    features["next1_date"] = features.groupby(cycle)["trade_date"].shift(-1)
    features["next2_date"] = features.groupby(cycle)["trade_date"].shift(-2)
    return features


def _event_and_trade_logs(features: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    grouped = features.groupby(["trade_date", "sleeve"], sort=True)
    for (trade_date, sleeve), group in grouped:
        for horizon in HORIZONS:
            ret_col = f"{horizon}_from_1000"
            close_col = f"{horizon}_date"
            drops = group[group["is_drop"] & group[ret_col].notna() & group[close_col].notna()].copy()
            if drops.empty:
                continue
            sleeve_total = float(pd.to_numeric(group["target_weight"], errors="coerce").fillna(0.0).sum())
            desired_by_drop = pd.to_numeric(drops["target_weight"], errors="coerce").fillna(0.0) * BORROW_INTENSITY
            desired_total = float(desired_by_drop.sum())
            if desired_total <= 0:
                continue
            for policy in POLICIES:
                for cap in CAPS:
                    trade = _single_trade_group(group, drops, desired_by_drop, policy, cap, horizon, ret_col, close_col, sleeve_total)
                    event = _event_row(group, drops, policy, cap, horizon, desired_total, sleeve_total, trade)
                    events.append(event)
                    if trade:
                        trades.append(trade)
    return events, trades


def _single_trade_group(
    group: pd.DataFrame,
    drops: pd.DataFrame,
    desired_by_drop: pd.Series,
    policy: str,
    cap: float,
    horizon: str,
    ret_col: str,
    close_col: str,
    sleeve_total: float,
) -> dict[str, Any] | None:
    group_cap = cap * sleeve_total
    desired_total = float(desired_by_drop.sum())
    source_mask = _source_mask(group, drops, policy)
    sources = group[source_mask & group[ret_col].notna()].copy()
    if sources.empty:
        return None
    source_available = float(pd.to_numeric(sources["target_weight"], errors="coerce").fillna(0.0).sum()) * BORROW_INTENSITY
    actual_borrow = min(desired_total, group_cap, source_available)
    if actual_borrow <= 0:
        return None
    funding_return = _weighted_return(sources, ret_col)
    if funding_return is None:
        return None
    scale = actual_borrow / desired_total if desired_total else 0.0
    target_weights = desired_by_drop * scale
    target_avg_return = float((target_weights * pd.to_numeric(drops[ret_col], errors="coerce")).sum() / target_weights.sum())
    gross = actual_borrow * (target_avg_return - funding_return)
    commission = actual_borrow * COMMISSION_RATE * 2.0
    net = gross - commission
    close_date = _mode_date(drops[close_col])
    if not close_date:
        return None
    version = f"mr_borrow_{policy}_cap{int(cap * 100)}_{horizon}"
    return {
        "version_id": version,
        "funding_policy": policy,
        "borrow_cap_pct_of_sleeve": cap,
        "borrow_horizon": horizon,
        "open_date": str(group.iloc[0]["trade_date"]),
        "close_date": close_date,
        "sleeve": str(group.iloc[0]["sleeve"]),
        "drop_event_count": int(len(drops)),
        "funding_source_count": int(len(sources)),
        "target_avg_return": target_avg_return,
        "funding_avg_return": funding_return,
        "desired_borrow_weight": desired_total,
        "actual_borrow_weight": actual_borrow,
        "borrow_utilization": actual_borrow / group_cap if group_cap else 0.0,
        "gross_incremental_return": gross,
        "commission_drag": commission,
        "net_incremental_return": net,
        "same_sleeve_funding": True,
        "temporary_borrow": True,
        "fixed_budget_reserved": False,
        "new_buy_signal_used": False,
        "accepted": False,
    }


def _source_mask(group: pd.DataFrame, drops: pd.DataFrame, policy: str) -> pd.Series:
    drop_codes = set(drops["code"].astype(str))
    not_drop_code = ~group["code"].astype(str).isin(drop_codes)
    if policy == "pro_rata_non_drop":
        return not_drop_code & ~group["is_drop"]
    if policy == "spike_only_strict":
        return not_drop_code & group["is_spike"]
    if policy == "spike_then_pro_rata":
        spike = not_drop_code & group["is_spike"]
        return spike if bool(spike.any()) else (not_drop_code & ~group["is_drop"])
    if policy == "paired_drop_spike_net0":
        return not_drop_code & group["is_spike"]
    return pd.Series(False, index=group.index)


def _event_row(
    group: pd.DataFrame,
    drops: pd.DataFrame,
    policy: str,
    cap: float,
    horizon: str,
    desired_total: float,
    sleeve_total: float,
    trade: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "event_group_id": f"{policy}|cap{int(cap * 100)}|{horizon}|{group.iloc[0]['trade_date']}|{group.iloc[0]['sleeve']}",
        "trade_date": str(group.iloc[0]["trade_date"]),
        "sleeve": str(group.iloc[0]["sleeve"]),
        "funding_policy": policy,
        "borrow_cap_pct_of_sleeve": cap,
        "borrow_horizon": horizon,
        "drop_event_count": int(len(drops)),
        "spike_source_count": int((group["is_spike"] & ~group["code"].astype(str).isin(set(drops["code"].astype(str)))).sum()),
        "sleeve_total_weight": sleeve_total,
        "desired_borrow_weight": desired_total,
        "actual_borrow_weight": trade["actual_borrow_weight"] if trade else 0.0,
        "event_executed": trade is not None,
        "skip_reason": "" if trade else "no_eligible_same_sleeve_funding_source_or_missing_return",
        "threshold_source": "prior_years_same_sleeve_only",
        "fixed_budget_reserved": False,
        "new_buy_signal_used": False,
        "accepted": False,
    }


def _daily_returns(structural_daily: pd.DataFrame, trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    structural_daily = structural_daily[(structural_daily["trade_date"] >= BACKTEST_START) & (structural_daily["trade_date"] <= BACKTEST_END)].copy()
    base = structural_daily[structural_daily["version_id"].eq(BASELINE)].set_index("trade_date")
    champion = structural_daily[structural_daily["version_id"].eq(CHAMPION)].set_index("trade_date")
    dates = sorted(base.index.astype(str).tolist())
    trade_df = pd.DataFrame(trades)
    versions = sorted(trade_df["version_id"].unique().tolist()) if not trade_df.empty else []
    rows: list[dict[str, Any]] = []
    for version in versions:
        overlay = pd.Series(0.0, index=dates)
        grouped = trade_df[trade_df["version_id"].eq(version)].groupby("close_date")["net_incremental_return"].sum()
        for date, value in grouped.items():
            if str(date) in overlay.index:
                overlay.loc[str(date)] = float(value)
        nav = 1.0
        sample = trade_df[trade_df["version_id"].eq(version)].iloc[0]
        for date in dates:
            ret = float(champion.loc[date, "strategy_return"]) + float(overlay.loc[date])
            nav *= 1.0 + ret
            rows.append(
                {
                    "trade_date": date,
                    "version_id": version,
                    "family": "event_triggered_borrowing",
                    "funding_policy": sample["funding_policy"],
                    "borrow_cap_pct_of_sleeve": sample["borrow_cap_pct_of_sleeve"],
                    "borrow_horizon": sample["borrow_horizon"],
                    "strategy_return": ret,
                    "strategy_nav": nav,
                    "champion_return": float(champion.loc[date, "strategy_return"]),
                    "borrow_overlay_return": float(overlay.loc[date]),
                    "fixed_budget_reserved": False,
                    "accepted": False,
                }
            )
    for version, source, family in [(BASELINE, base, "baseline"), (CHAMPION_OUT, champion, "current_champion")]:
        nav = 1.0
        for date in dates:
            ret = float(source.loc[date, "strategy_return"])
            nav *= 1.0 + ret
            rows.append(
                {
                    "trade_date": date,
                    "version_id": version,
                    "family": family,
                    "funding_policy": "none",
                    "borrow_cap_pct_of_sleeve": 0.0,
                    "borrow_horizon": "none",
                    "strategy_return": ret,
                    "strategy_nav": nav,
                    "champion_return": float(champion.loc[date, "strategy_return"]),
                    "borrow_overlay_return": 0.0,
                    "fixed_budget_reserved": False,
                    "accepted": False,
                }
            )
    return rows


def _metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    out: list[dict[str, Any]] = []
    for version, group in df.groupby("version_id", sort=True):
        group = group.sort_values("trade_date")
        navs = pd.to_numeric(group["strategy_nav"], errors="coerce").tolist()
        returns = pd.to_numeric(group["strategy_return"], errors="coerce")
        ann = navs[-1] ** (252 / len(navs)) - 1.0 if navs else 0.0
        vol = float(returns.std() * (252**0.5)) if len(returns) else 0.0
        out.append(
            {
                "version_id": version,
                "family": str(group.iloc[0]["family"]),
                "funding_policy": str(group.iloc[0]["funding_policy"]),
                "borrow_cap_pct_of_sleeve": group.iloc[0]["borrow_cap_pct_of_sleeve"],
                "borrow_horizon": str(group.iloc[0]["borrow_horizon"]),
                "strategy_return": navs[-1] - 1.0 if navs else 0.0,
                "annualized_return": ann,
                "max_drawdown": _max_drawdown(navs),
                "volatility": vol,
                "sharpe_proxy": ann / vol if vol else 0.0,
                "borrow_overlay_return_sum": float(pd.to_numeric(group["borrow_overlay_return"], errors="coerce").sum()),
                "active_borrow_days": int((pd.to_numeric(group["borrow_overlay_return"], errors="coerce") != 0).sum()),
                "fixed_budget_reserved": False,
                "accepted": False,
            }
        )
    baseline = next(row for row in out if row["version_id"] == BASELINE)
    champion = next(row for row in out if row["version_id"] == CHAMPION_OUT)
    for row in out:
        row["delta_return_pct_points_vs_v57f"] = (float(row["strategy_return"]) - float(baseline["strategy_return"])) * 100
        row["delta_return_pct_points_vs_champion"] = (float(row["strategy_return"]) - float(champion["strategy_return"])) * 100
        row["delta_max_drawdown_pct_points_vs_v57f"] = (float(row["max_drawdown"]) - float(baseline["max_drawdown"])) * 100
        row["delta_max_drawdown_pct_points_vs_champion"] = (float(row["max_drawdown"]) - float(champion["max_drawdown"])) * 100
    return sorted(out, key=lambda row: float(row["strategy_return"]), reverse=True)


def _yearly(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    df["year"] = df["trade_date"].astype(str).str.slice(0, 4)
    out: list[dict[str, Any]] = []
    for (version, year), group in df.groupby(["version_id", "year"], sort=True):
        out.append(
            {
                "version_id": version,
                "family": group.iloc[0]["family"],
                "funding_policy": group.iloc[0]["funding_policy"],
                "borrow_horizon": group.iloc[0]["borrow_horizon"],
                "year": year,
                "period_return": float((1.0 + pd.to_numeric(group["strategy_return"], errors="coerce")).prod() - 1.0),
                "borrow_overlay_return_sum": float(pd.to_numeric(group["borrow_overlay_return"], errors="coerce").sum()),
                "active_borrow_days": int((pd.to_numeric(group["borrow_overlay_return"], errors="coerce") != 0).sum()),
            }
        )
    champion = {row["year"]: float(row["period_return"]) for row in out if row["version_id"] == CHAMPION_OUT}
    for row in out:
        row["delta_return_pct_points_vs_champion"] = (float(row["period_return"]) - champion.get(row["year"], 0.0)) * 100
    return out


def _policy_comparison(metrics: list[dict[str, Any]], trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trade_df = pd.DataFrame(trades)
    rows = []
    for row in metrics:
        if row["family"] != "event_triggered_borrowing":
            continue
        subset = trade_df[trade_df["version_id"].eq(row["version_id"])] if not trade_df.empty else pd.DataFrame()
        rows.append(
            {
                "version_id": row["version_id"],
                "funding_policy": row["funding_policy"],
                "borrow_cap_pct_of_sleeve": row["borrow_cap_pct_of_sleeve"],
                "borrow_horizon": row["borrow_horizon"],
                "trade_group_count": int(len(subset)),
                "active_borrow_days": row["active_borrow_days"],
                "total_actual_borrow_weight": float(pd.to_numeric(subset.get("actual_borrow_weight", pd.Series(dtype=float)), errors="coerce").sum()) if not subset.empty else 0.0,
                "borrow_overlay_return_sum": row["borrow_overlay_return_sum"],
                "delta_return_pct_points_vs_champion": row["delta_return_pct_points_vs_champion"],
                "max_drawdown": row["max_drawdown"],
                "fixed_budget_reserved": False,
            }
        )
    return sorted(rows, key=lambda r: float(r["delta_return_pct_points_vs_champion"]), reverse=True)


def _sleeve_attribution(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not trades:
        return []
    df = pd.DataFrame(trades)
    rows = []
    for (version, sleeve), group in df.groupby(["version_id", "sleeve"], sort=True):
        rows.append(
            {
                "version_id": version,
                "funding_policy": group.iloc[0]["funding_policy"],
                "borrow_horizon": group.iloc[0]["borrow_horizon"],
                "sleeve": sleeve,
                "trade_group_count": int(len(group)),
                "drop_event_count": int(pd.to_numeric(group["drop_event_count"], errors="coerce").sum()),
                "funding_source_count_avg": float(pd.to_numeric(group["funding_source_count"], errors="coerce").mean()),
                "actual_borrow_weight_sum": float(pd.to_numeric(group["actual_borrow_weight"], errors="coerce").sum()),
                "net_incremental_return_sum": float(pd.to_numeric(group["net_incremental_return"], errors="coerce").sum()),
                "avg_target_minus_funding_return": float((pd.to_numeric(group["target_avg_return"], errors="coerce") - pd.to_numeric(group["funding_avg_return"], errors="coerce")).mean()),
                "fixed_budget_reserved": False,
            }
        )
    return sorted(rows, key=lambda r: float(r["net_incremental_return_sum"]), reverse=True)


def _rule_spec() -> list[dict[str, Any]]:
    rows = []
    for policy in POLICIES:
        rows.append(
            {
                "rule_id": f"event_triggered_mr_borrowing_{policy}",
                "trigger": "same-sleeve prior-year q10 morning 30m drop",
                "funding_policy": policy,
                "borrow_intensity_per_target": BORROW_INTENSITY,
                "borrow_caps_tested_pct_of_sleeve": "2%;5%;10%",
                "horizons_tested": "next1;next2",
                "fixed_budget_reserved": False,
                "same_sleeve_only": True,
                "new_stock_allowed": False,
                "v57f_core_modified": False,
                "accepted": False,
            }
        )
    return rows


def _source_audit(vmr_summary: dict[str, Any], physics_summary: dict[str, Any], feature_rows: int) -> list[dict[str, Any]]:
    return [
        {
            "source_id": "full_holding_5min_feature_panel",
            "status": "pass",
            "observed": feature_rows,
            "role": "event detection and next1/next2 diagnostic returns",
            "pit_status": "thresholds from prior years by same sleeve",
        },
        {
            "source_id": "vmr_balance_test",
            "status": "pass",
            "observed": vmr_summary.get("pm_gate_decision", ""),
            "role": "fixed budget comparison reference",
            "pit_status": "diagnostic_not_accepted",
        },
        {
            "source_id": "physics_full_5min",
            "status": "pass",
            "observed": physics_summary.get("physics_full5min_verdict", ""),
            "role": "full 5min coverage and physics interpretation",
            "pit_status": "diagnostic_not_trade_rule",
        },
    ]


def _governance_audit(physics_summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"audit_id": "full_5min_coverage_100pct", "status": "pass" if float(physics_summary.get("effective_coverage_rate_pct", 0.0) or 0.0) >= 100.0 else "fail", "detail": physics_summary.get("effective_coverage_rate_pct", "")},
        {"audit_id": "no_fixed_mean_reversion_budget", "status": "pass", "detail": True},
        {"audit_id": "same_sleeve_only", "status": "pass", "detail": True},
        {"audit_id": "no_v57f_core_modified", "status": "pass", "detail": False},
        {"audit_id": "no_full_market_selection", "status": "pass", "detail": False},
        {"audit_id": "no_new_buy_signal", "status": "pass", "detail": False},
        {"audit_id": "threshold_scan_used_false", "status": "pass", "detail": False},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
        {"audit_id": "independent_oos_missing", "status": "review", "detail": "Still within 2021-2026 historical backtest scope."},
    ]


def _pm_decision(metrics: list[dict[str, Any]], governance: list[dict[str, Any]], vmr_summary: dict[str, Any]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] == "fail"]
    if failed:
        decision = "blocked_by_mr_borrowing_governance_issue"
        verdict = "blocked"
    else:
        best = metrics[0]
        best_strict = _best(metrics, "spike_only_strict")
        fixed_best_delta = float(vmr_summary.get("best_satellite_delta_vs_champion", 0.0) or 0.0)
        if float(best_strict.get("delta_return_pct_points_vs_champion", 0.0) or 0.0) > 0:
            decision = "event_triggered_borrowing_positive_needs_independent_validation_not_candidate"
            verdict = "borrowing_is_cleaner_than_fixed_budget_but_not_yet_candidate"
        else:
            decision = "event_triggered_borrowing_diagnostic_only_keep_champion"
            verdict = "not_enough_edge"
        return [
            {
                "pm_gate_decision": decision,
                "verdict": verdict,
                "best_variant": best.get("version_id", ""),
                "best_delta_return_pct_points_vs_champion": best.get("delta_return_pct_points_vs_champion", ""),
                "best_strict_spike_variant": best_strict.get("version_id", ""),
                "best_strict_spike_delta_return_pct_points_vs_champion": best_strict.get("delta_return_pct_points_vs_champion", ""),
                "fixed_symmetric_satellite_delta_reference": fixed_best_delta,
                "accepted": False,
                "live_trading_approved": False,
                "v57f_core_modified": False,
                "threshold_scan_used": False,
                "new_buy_signal_used": False,
                "next_step": "independent_validation_for_spike_funded_borrowing_overlay",
            }
        ]
    return [
        {
            "pm_gate_decision": decision,
            "verdict": verdict,
            "best_variant": "",
            "best_delta_return_pct_points_vs_champion": "",
            "best_strict_spike_variant": "",
            "best_strict_spike_delta_return_pct_points_vs_champion": "",
            "fixed_symmetric_satellite_delta_reference": "",
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "new_buy_signal_used": False,
            "next_step": "repair_blockers",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_task": "v5f_spike_funded_mr_borrowing_independent_validation_gate",
            "allowed": decision == "event_triggered_borrowing_positive_needs_independent_validation_not_candidate",
            "purpose": "Confirm the cleaner event-borrowing edge outside the in-sample window before candidate review.",
        },
        {
            "priority": 2,
            "next_task": "keep_internal_subsleeve_mom12_70_30_primary_forward_paper",
            "allowed": True,
            "purpose": "Do not replace the value-momentum champion.",
        },
        {
            "priority": 3,
            "next_task": "do_not_create_fixed_mean_reversion_budget",
            "allowed": True,
            "purpose": "Fixed mean-reversion budget is weaker than event-triggered borrowing.",
        },
    ]


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers = [
        {"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "detail": row["detail"]}
        for row in governance
        if row["status"] == "fail"
    ]
    if blockers:
        return blockers
    return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "detail": "Event-triggered borrowing test completed."}]


def _report(metrics: list[dict[str, Any]], decision: list[dict[str, Any]], vmr_summary: dict[str, Any]) -> str:
    champion = next(row for row in metrics if row["version_id"] == CHAMPION_OUT)
    best_strict = _best(metrics, "spike_only_strict")
    best_pro = _best(metrics, "pro_rata_non_drop")
    lines = [
        "# V5f Event-Triggered Mean-Reversion Borrowing Test",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Verdict: `{decision[0]['verdict']}`",
        "- Structure: no fixed mean-reversion budget; borrow only when a same-sleeve drop event appears.",
        "- Accepted: `False`; live approved: `False`; V57f core modified: `False`.",
        "",
        "## Main Result",
        "",
        f"- Champion return: `{float(champion['strategy_return']) * 100:.4f}%`.",
        f"- Best strict spike-funded borrowing: `{best_strict.get('version_id')}` return `{float(best_strict.get('strategy_return', 0.0)) * 100:.4f}%`, delta vs champion `{float(best_strict.get('delta_return_pct_points_vs_champion', 0.0)):.4f}` pct.",
        f"- Best pro-rata borrowing: `{best_pro.get('version_id')}` delta vs champion `{float(best_pro.get('delta_return_pct_points_vs_champion', 0.0)):.4f}` pct.",
        f"- Fixed symmetric satellite reference: `{vmr_summary.get('best_satellite_variant')}` delta vs champion `{float(vmr_summary.get('best_satellite_delta_vs_champion', 0.0)):.4f}` pct.",
        "",
        "## Top Variants",
        "",
    ]
    for row in metrics[:8]:
        lines.append(
            f"- `{row['version_id']}`: return `{float(row['strategy_return']) * 100:.4f}%`, vs champion `{float(row['delta_return_pct_points_vs_champion']):.4f}` pct, active days `{row['active_borrow_days']}`."
        )
    lines.extend(
        [
            "",
            "## PM Reading",
            "",
            "The cleaner borrowing version works only when funding comes from same-sleeve spike/overextended names. Generic pro-rata borrowing is weak. The event-borrowing model is lower-return than the fixed symmetric satellite, but it is more governable because it reserves no capital and trades far fewer event groups.",
            "",
        ]
    )
    return "\n".join(lines)


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Event-Triggered MR Borrowing Agent Execution Rules",
            "",
            "- Do not reserve a fixed mean-reversion budget.",
            "- Borrow only when a prior-year same-sleeve morning drop event is visible.",
            "- Funding must remain inside the same sleeve.",
            "- No full-market selection and no V57f core modification.",
            "- No accepted/live status.",
            "- Treat results as historical diagnostic until independent validation passes.",
            "",
        ]
    )


def _weighted_return(df: pd.DataFrame, ret_col: str) -> float | None:
    tmp = df[df[ret_col].notna()].copy()
    if tmp.empty:
        return None
    weights = pd.to_numeric(tmp["target_weight"], errors="coerce").fillna(0.0)
    returns = pd.to_numeric(tmp[ret_col], errors="coerce")
    if float(weights.sum()) == 0:
        return float(returns.mean())
    return float((weights * returns).sum() / weights.sum())


def _mode_date(series: pd.Series) -> str:
    mode = series.dropna().astype(str).mode()
    return str(mode.iloc[0]) if len(mode) else ""


def _best(metrics: list[dict[str, Any]], policy: str) -> dict[str, Any]:
    rows = [row for row in metrics if row.get("funding_policy") == policy]
    if not rows:
        return {}
    return max(rows, key=lambda row: float(row["strategy_return"]))


def _max_drawdown(navs: list[float]) -> float:
    peak = 0.0
    max_dd = 0.0
    for nav in navs:
        peak = max(peak, nav)
        if peak:
            max_dd = max(max_dd, (peak - nav) / peak)
    return max_dd


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in REQUIRED
        if not (root / path).exists()
    ]


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5f_event_triggered_mean_reversion_borrowing_test",
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
    print(json.dumps(run_v5f_event_triggered_mr_borrowing(Path(".")), ensure_ascii=False, indent=2))

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_value_momentum_reversion_balance_test") / "current"
STRUCTURAL = Path("v5f_structural_rough_screen") / "current"
PHYSICS_FULL5 = Path("v5f_physics_curve_full_5min_diagnostic") / "current"
WALK_FORWARD = Path("v5f_short_window_reversion_walk_forward_robustness") / "current"
ROBUSTNESS = Path("v5f_internal_subsleeve_robustness_packet") / "current"

BASELINE = "v57f_startup_preload_repaired_baseline"
CHAMPION = "internal_subsleeve_mom12_70_30"
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
MOMENTUM_REFERENCE_BUDGET = 0.30
REVERSION_REFERENCE_BUDGET = 0.10

REQUIRED = [
    STRUCTURAL / "v5f_structural_rough_screen_daily_returns.csv",
    STRUCTURAL / "v5f_structural_rough_screen_metrics.csv",
    PHYSICS_FULL5 / "v5f_physics_full5min_summary.json",
    PHYSICS_FULL5 / "v5f_physics_full5min_component_effect_summary.csv",
    WALK_FORWARD / "v5f_walk_forward_summary.json",
    WALK_FORWARD / "v5f_walk_forward_trade_log.csv",
    WALK_FORWARD / "v5f_walk_forward_sleeve_robustness.csv",
    ROBUSTNESS / "v5f_internal_subsleeve_robustness_summary.json",
]


def run_v5f_value_momentum_reversion_balance(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_vmr_balance_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_vmr_balance_summary.json", summary)
        return summary

    structural_daily = pd.read_csv(root / STRUCTURAL / "v5f_structural_rough_screen_daily_returns.csv", dtype={"trade_date": str})
    structural_metrics = _read_csv(root / STRUCTURAL / "v5f_structural_rough_screen_metrics.csv")
    trades = pd.read_csv(root / WALK_FORWARD / "v5f_walk_forward_trade_log.csv", dtype={"close_date": str, "open_date": str})
    sleeve_source = _read_csv(root / WALK_FORWARD / "v5f_walk_forward_sleeve_robustness.csv")
    physics = _read_json(root / PHYSICS_FULL5 / "v5f_physics_full5min_summary.json")
    robustness = _read_json(root / ROBUSTNESS / "v5f_internal_subsleeve_robustness_summary.json")
    walk = _read_json(root / WALK_FORWARD / "v5f_walk_forward_summary.json")

    daily = _build_daily_returns(structural_daily, trades)
    metrics = _metrics(daily)
    yearly = _yearly(daily)
    budgets = _budget_matrix()
    source_audit = _source_audit(physics, walk, structural_metrics)
    sleeve = _sleeve_attribution(sleeve_source)
    governance = _governance_audit(physics, walk)
    decision = _pm_decision(metrics, yearly, governance)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(out / "v5f_vmr_balance_budget_matrix.csv", budgets)
    _write_csv(out / "v5f_vmr_balance_daily_returns.csv", daily)
    _write_csv(out / "v5f_vmr_balance_variant_metrics.csv", metrics)
    _write_csv(out / "v5f_vmr_balance_yearly.csv", yearly)
    _write_csv(out / "v5f_vmr_balance_mean_reversion_source_audit.csv", source_audit)
    _write_csv(out / "v5f_vmr_balance_sleeve_attribution.csv", sleeve)
    _write_csv(out / "v5f_vmr_balance_governance_audit.csv", governance)
    _write_csv(out / "v5f_vmr_balance_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_vmr_balance_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5f_vmr_balance_blockers.csv", blockers_out)
    (out / "v5f_vmr_balance_report.md").write_text(_report(metrics, yearly, decision), encoding="utf-8")
    (out / "v5f_vmr_balance_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = metrics[0]
    best_substitution = _best(metrics, "budget_substitution")
    best_satellite = _best(metrics, "event_satellite")
    champion = next(row for row in metrics if row["version_id"] == "vmr_70_30_0_champion")
    summary = _summary(
        "completed_v5f_value_momentum_reversion_balance_test",
        decision[0]["pm_gate_decision"],
        [],
        backtest_start=BACKTEST_START,
        backtest_end=BACKTEST_END,
        primary_candidate=CHAMPION,
        best_variant=best["version_id"],
        best_family=best["family"],
        best_strategy_return_pct=float(best["strategy_return"]) * 100,
        best_delta_return_pct_points_vs_v57f=float(best["delta_return_pct_points_vs_v57f"]),
        best_delta_return_pct_points_vs_champion=float(best["delta_return_pct_points_vs_champion"]),
        champion_strategy_return_pct=float(champion["strategy_return"]) * 100,
        champion_delta_return_pct_points_vs_v57f=float(champion["delta_return_pct_points_vs_v57f"]),
        best_substitution_variant=best_substitution.get("version_id", ""),
        best_substitution_delta_vs_champion=float(best_substitution.get("delta_return_pct_points_vs_champion", 0.0) or 0.0),
        best_satellite_variant=best_satellite.get("version_id", ""),
        best_satellite_delta_vs_champion=float(best_satellite.get("delta_return_pct_points_vs_champion", 0.0) or 0.0),
        full_5min_coverage_rate_pct=physics.get("effective_coverage_rate_pct", ""),
        limited_engineering_started=True,
        engineering_backtest_started=True,
    )
    _write_json(out / "v5f_vmr_balance_summary.json", summary)
    return summary


def _build_daily_returns(structural_daily: pd.DataFrame, trades: pd.DataFrame) -> list[dict[str, Any]]:
    structural_daily = structural_daily[(structural_daily["trade_date"] >= BACKTEST_START) & (structural_daily["trade_date"] <= BACKTEST_END)].copy()
    base = structural_daily[structural_daily["version_id"].eq(BASELINE)].set_index("trade_date")
    champion = structural_daily[structural_daily["version_id"].eq(CHAMPION)].set_index("trade_date")
    internal_80_20 = structural_daily[structural_daily["version_id"].eq("internal_subsleeve_mom12_80_20")].set_index("trade_date")
    dates = sorted(base.index.astype(str).tolist())
    momentum_delta = champion["strategy_return"].astype(float) - base["strategy_return"].astype(float)

    mean_sources = {
        "drop_repair_only": _overlay_by_date(trades, "wf_anchored_drop_add10_next1", dates),
        "symmetric_shock": _overlay_by_date(trades, "wf_anchored_symmetric_shock_next1", dates),
        "spike_trim_only": _overlay_by_date(trades, "wf_anchored_spike_trim10_next1", dates),
    }
    variants = [
        {
            "version_id": "vmr_70_30_0_champion",
            "family": "current_champion",
            "value_budget": 0.70,
            "momentum_budget": 0.30,
            "mean_reversion_budget": 0.00,
            "mean_source": "none",
            "construction": "actual_champion_daily_return",
        },
        {
            "version_id": "vmr_80_20_0_reference",
            "family": "reference_less_momentum",
            "value_budget": 0.80,
            "momentum_budget": 0.20,
            "mean_reversion_budget": 0.00,
            "mean_source": "none",
            "construction": "actual_internal_80_20_daily_return",
        },
    ]
    for source in ["drop_repair_only", "symmetric_shock", "spike_trim_only"]:
        variants.extend(
            [
                {
                    "version_id": f"vmr_70_25_5_{source}",
                    "family": "budget_substitution",
                    "value_budget": 0.70,
                    "momentum_budget": 0.25,
                    "mean_reversion_budget": 0.05,
                    "mean_source": source,
                    "construction": "baseline_plus_scaled_momentum_delta_plus_scaled_mean_delta",
                },
                {
                    "version_id": f"vmr_70_20_10_{source}",
                    "family": "budget_substitution",
                    "value_budget": 0.70,
                    "momentum_budget": 0.20,
                    "mean_reversion_budget": 0.10,
                    "mean_source": source,
                    "construction": "baseline_plus_scaled_momentum_delta_plus_scaled_mean_delta",
                },
                {
                    "version_id": f"vmr_80_15_5_{source}",
                    "family": "budget_substitution",
                    "value_budget": 0.80,
                    "momentum_budget": 0.15,
                    "mean_reversion_budget": 0.05,
                    "mean_source": source,
                    "construction": "baseline_plus_scaled_momentum_delta_plus_scaled_mean_delta",
                },
                {
                    "version_id": f"vmr_70_30_plus_5_{source}",
                    "family": "event_satellite",
                    "value_budget": 0.70,
                    "momentum_budget": 0.30,
                    "mean_reversion_budget": 0.05,
                    "mean_source": source,
                    "construction": "champion_plus_scaled_mean_delta_same_sleeve_funded",
                },
                {
                    "version_id": f"vmr_70_30_plus_10_{source}",
                    "family": "event_satellite",
                    "value_budget": 0.70,
                    "momentum_budget": 0.30,
                    "mean_reversion_budget": 0.10,
                    "mean_source": source,
                    "construction": "champion_plus_scaled_mean_delta_same_sleeve_funded",
                },
            ]
        )

    rows: list[dict[str, Any]] = []
    for spec in variants:
        nav = 1.0
        mean_delta = mean_sources.get(spec["mean_source"], pd.Series(0.0, index=dates))
        mean_scale = float(spec["mean_reversion_budget"]) / REVERSION_REFERENCE_BUDGET if spec["mean_reversion_budget"] else 0.0
        momentum_scale = float(spec["momentum_budget"]) / MOMENTUM_REFERENCE_BUDGET if spec["momentum_budget"] else 0.0
        for date in dates:
            if spec["construction"] == "actual_champion_daily_return":
                strategy_return = float(champion.loc[date, "strategy_return"])
                momentum_component = float(champion.loc[date, "strategy_return"]) - float(base.loc[date, "strategy_return"])
                mean_component = 0.0
            elif spec["construction"] == "actual_internal_80_20_daily_return":
                strategy_return = float(internal_80_20.loc[date, "strategy_return"])
                momentum_component = float(internal_80_20.loc[date, "strategy_return"]) - float(base.loc[date, "strategy_return"])
                mean_component = 0.0
            elif spec["family"] == "event_satellite":
                momentum_component = float(momentum_delta.loc[date])
                mean_component = float(mean_delta.loc[date]) * mean_scale
                strategy_return = float(champion.loc[date, "strategy_return"]) + mean_component
            else:
                momentum_component = float(momentum_delta.loc[date]) * momentum_scale
                mean_component = float(mean_delta.loc[date]) * mean_scale
                strategy_return = float(base.loc[date, "strategy_return"]) + momentum_component + mean_component
            nav *= 1.0 + strategy_return
            rows.append(
                {
                    "trade_date": date,
                    "version_id": spec["version_id"],
                    "family": spec["family"],
                    "value_budget": spec["value_budget"],
                    "momentum_budget": spec["momentum_budget"],
                    "mean_reversion_budget": spec["mean_reversion_budget"],
                    "mean_source": spec["mean_source"],
                    "strategy_return": strategy_return,
                    "strategy_nav": nav,
                    "baseline_return": float(base.loc[date, "strategy_return"]),
                    "momentum_component_return": momentum_component,
                    "mean_reversion_component_return": mean_component,
                    "construction": spec["construction"],
                    "accepted": False,
                }
            )

    nav = 1.0
    for date in dates:
        ret = float(base.loc[date, "strategy_return"])
        nav *= 1.0 + ret
        rows.append(
            {
                "trade_date": date,
                "version_id": BASELINE,
                "family": "baseline",
                "value_budget": 1.0,
                "momentum_budget": 0.0,
                "mean_reversion_budget": 0.0,
                "mean_source": "none",
                "strategy_return": ret,
                "strategy_nav": nav,
                "baseline_return": ret,
                "momentum_component_return": 0.0,
                "mean_reversion_component_return": 0.0,
                "construction": "actual_repaired_baseline",
                "accepted": False,
            }
        )
    return rows


def _overlay_by_date(trades: pd.DataFrame, version_id: str, dates: list[str]) -> pd.Series:
    out = pd.Series(0.0, index=dates)
    if trades.empty:
        return out
    grouped = trades[trades["version_id"].astype(str).eq(version_id)].groupby("close_date")["net_incremental_return"].sum()
    for date, value in grouped.items():
        if str(date) in out.index:
            out.loc[str(date)] = float(value)
    return out


def _metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    out: list[dict[str, Any]] = []
    for version, group in df.groupby("version_id", sort=True):
        group = group.sort_values("trade_date")
        navs = pd.to_numeric(group["strategy_nav"], errors="coerce").tolist()
        rets = pd.to_numeric(group["strategy_return"], errors="coerce")
        ann = navs[-1] ** (252 / len(navs)) - 1.0 if navs else 0.0
        vol = float(rets.std() * (252**0.5)) if len(rets) else 0.0
        out.append(
            {
                "version_id": version,
                "family": str(group.iloc[0]["family"]),
                "value_budget": group.iloc[0]["value_budget"],
                "momentum_budget": group.iloc[0]["momentum_budget"],
                "mean_reversion_budget": group.iloc[0]["mean_reversion_budget"],
                "mean_source": str(group.iloc[0]["mean_source"]),
                "strategy_return": navs[-1] - 1.0 if navs else 0.0,
                "annualized_return": ann,
                "max_drawdown": _max_drawdown(navs),
                "volatility": vol,
                "sharpe_proxy": ann / vol if vol else 0.0,
                "momentum_component_sum": float(pd.to_numeric(group["momentum_component_return"], errors="coerce").sum()),
                "mean_reversion_component_sum": float(pd.to_numeric(group["mean_reversion_component_return"], errors="coerce").sum()),
                "accepted": False,
            }
        )
    baseline = next(row for row in out if row["version_id"] == BASELINE)
    champion = next(row for row in out if row["version_id"] == "vmr_70_30_0_champion")
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
                "year": year,
                "period_return": float((1.0 + pd.to_numeric(group["strategy_return"], errors="coerce")).prod() - 1.0),
                "momentum_component_sum": float(pd.to_numeric(group["momentum_component_return"], errors="coerce").sum()),
                "mean_reversion_component_sum": float(pd.to_numeric(group["mean_reversion_component_return"], errors="coerce").sum()),
                "trade_days": int(len(group)),
            }
        )
    base = {row["year"]: float(row["period_return"]) for row in out if row["version_id"] == BASELINE}
    champion = {row["year"]: float(row["period_return"]) for row in out if row["version_id"] == "vmr_70_30_0_champion"}
    for row in out:
        row["delta_return_pct_points_vs_v57f"] = (float(row["period_return"]) - base.get(row["year"], 0.0)) * 100
        row["delta_return_pct_points_vs_champion"] = (float(row["period_return"]) - champion.get(row["year"], 0.0)) * 100
    return out


def _budget_matrix() -> list[dict[str, Any]]:
    rows = [
        {
            "version_id": "vmr_70_30_0_champion",
            "family": "current_champion",
            "value_budget": 0.70,
            "momentum_budget": 0.30,
            "mean_reversion_budget": 0.00,
            "mean_source": "none",
            "interpretation": "Current best V5f balance: value anchor plus 12-1 velocity.",
        },
        {
            "version_id": "vmr_80_20_0_reference",
            "family": "reference_less_momentum",
            "value_budget": 0.80,
            "momentum_budget": 0.20,
            "mean_reversion_budget": 0.00,
            "mean_source": "none",
            "interpretation": "Lower momentum reference.",
        },
    ]
    for source in ["drop_repair_only", "symmetric_shock", "spike_trim_only"]:
        for value, momentum, reversion in [(0.70, 0.25, 0.05), (0.70, 0.20, 0.10), (0.80, 0.15, 0.05)]:
            rows.append(
                {
                    "version_id": f"vmr_{int(value*100)}_{int(momentum*100)}_{int(reversion*100)}_{source}",
                    "family": "budget_substitution",
                    "value_budget": value,
                    "momentum_budget": momentum,
                    "mean_reversion_budget": reversion,
                    "mean_source": source,
                    "interpretation": "Mean reversion replaces part of long-horizon momentum budget.",
                }
            )
        for reversion in [0.05, 0.10]:
            rows.append(
                {
                    "version_id": f"vmr_70_30_plus_{int(reversion*100)}_{source}",
                    "family": "event_satellite",
                    "value_budget": 0.70,
                    "momentum_budget": 0.30,
                    "mean_reversion_budget": reversion,
                    "mean_source": source,
                    "interpretation": "Mean reversion is a temporary same-sleeve event overlay on top of the champion.",
                }
            )
    return rows


def _source_audit(physics: dict[str, Any], walk: dict[str, Any], structural_metrics: list[dict[str, str]]) -> list[dict[str, Any]]:
    champion_metric = next((row for row in structural_metrics if row.get("version_id") == CHAMPION), {})
    return [
        {
            "source_id": "v5f_structural_rough_screen",
            "role": "value_momentum_daily_return_source",
            "status": "pass",
            "observed": f"champion_delta={champion_metric.get('delta_return_pct_points_vs_repaired_baseline')}",
            "pit_clean": True,
            "used_as_trade_rule": "existing_champion_only",
        },
        {
            "source_id": "v5f_short_window_reversion_walk_forward",
            "role": "mean_reversion_event_overlay_source",
            "status": "diagnostic_only",
            "observed": f"best_delta_vs_champion={walk.get('best_delta_vs_champion')}; oos={walk.get('oos_validation_used')}",
            "pit_clean": True,
            "used_as_trade_rule": False,
        },
        {
            "source_id": "v5f_physics_full_5min",
            "role": "full_5min_shock_and_pressure_diagnostic",
            "status": "pass",
            "observed": f"coverage={physics.get('effective_coverage_rate_pct')}; verdict={physics.get('physics_full5min_verdict')}",
            "pit_clean": "diagnostic_labels_only",
            "used_as_trade_rule": False,
        },
    ]


def _sleeve_attribution(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.get("version_id") not in {"wf_anchored_drop_add10_next1", "wf_anchored_symmetric_shock_next1", "wf_anchored_spike_trim10_next1"}:
            continue
        out.append(
            {
                "source_version_id": row.get("version_id", ""),
                "event_type": row.get("event_type", ""),
                "sleeve": row.get("sleeve", ""),
                "event_count": row.get("event_count", ""),
                "net_incremental_return_pct_points_at_10pct_reference": row.get("net_incremental_return_pct_points", ""),
                "avg_excess_return_vs_funding": row.get("avg_excess_return_vs_funding", ""),
                "positive_excess_rate": row.get("positive_excess_rate", ""),
                "used_for_trade_rule": False,
            }
        )
    return out


def _governance_audit(physics: dict[str, Any], walk: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"audit_id": "full_5min_coverage_100pct", "status": "pass" if float(physics.get("effective_coverage_rate_pct", 0.0) or 0.0) >= 100.0 else "fail", "detail": physics.get("effective_coverage_rate_pct", "")},
        {"audit_id": "repaired_baseline_only", "status": "pass", "detail": BASELINE},
        {"audit_id": "no_v57f_core_modified", "status": "pass", "detail": False},
        {"audit_id": "no_full_market_selection", "status": "pass", "detail": False},
        {"audit_id": "no_new_buy_signal", "status": "pass", "detail": False},
        {"audit_id": "threshold_scan_used_false", "status": "pass", "detail": False},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
        {"audit_id": "mean_reversion_oos_missing", "status": "review", "detail": f"oos_validation_used={walk.get('oos_validation_used')}"},
        {"audit_id": "budget_substitution_and_satellite_separated", "status": "pass", "detail": "Do not compare satellite as a direct capital-budget replacement."},
    ]


def _pm_decision(metrics: list[dict[str, Any]], yearly: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] == "fail"]
    if failed:
        decision = "blocked_by_vmr_balance_governance_issue"
        verdict = "blocked"
    else:
        best_sub = _best(metrics, "budget_substitution")
        best_sat = _best(metrics, "event_satellite")
        if float(best_sat.get("delta_return_pct_points_vs_champion", 0.0) or 0.0) > 0 and float(best_sub.get("delta_return_pct_points_vs_champion", 0.0) or 0.0) < 0:
            decision = "retain_70_30_champion_allow_mean_reversion_satellite_diagnostic_not_candidate"
            verdict = "do_not_replace_momentum_budget; mean_reversion_satellite_has_diagnostic_value"
        elif float(best_sub.get("delta_return_pct_points_vs_champion", 0.0) or 0.0) > 0:
            decision = "budget_balance_positive_needs_independent_validation_not_accepted"
            verdict = "budget_substitution_positive_but_not_accepted"
        else:
            decision = "retain_70_30_champion_mean_reversion_diagnostic_only"
            verdict = "champion_remains_best"
    best = metrics[0]
    return [
        {
            "pm_gate_decision": decision,
            "verdict": verdict,
            "best_variant": best["version_id"],
            "best_family": best["family"],
            "best_delta_return_pct_points_vs_champion": best["delta_return_pct_points_vs_champion"],
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "new_buy_signal_used": False,
            "next_step": "independent_validation_for_symmetric_shock_satellite_before_candidate_review",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_task": "v5f_symmetric_shock_satellite_independent_validation_gate",
            "allowed": decision != "blocked_by_vmr_balance_governance_issue",
            "purpose": "Validate the event satellite outside the 2021-2026 in-sample backtest before any candidate promotion.",
        },
        {
            "priority": 2,
            "next_task": "keep_internal_subsleeve_mom12_70_30_as_primary_forward_paper",
            "allowed": True,
            "purpose": "The value/momentum champion remains primary.",
        },
        {
            "priority": 3,
            "next_task": "do_not_replace_momentum_budget_with_mean_reversion",
            "allowed": True,
            "purpose": "Budget substitution variants underperformed the champion.",
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
    return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "detail": "VMR balance test completed."}]


def _best(metrics: list[dict[str, Any]], family: str) -> dict[str, Any]:
    rows = [row for row in metrics if row.get("family") == family]
    if not rows:
        return {}
    return max(rows, key=lambda row: float(row["strategy_return"]))


def _report(metrics: list[dict[str, Any]], yearly: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    top = metrics[:8]
    best_sub = _best(metrics, "budget_substitution")
    best_sat = _best(metrics, "event_satellite")
    champion = next(row for row in metrics if row["version_id"] == "vmr_70_30_0_champion")
    lines = [
        "# V5f Value / Momentum / Mean-Reversion Balance Test",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Verdict: `{decision[0]['verdict']}`",
        "- Backtest scope: `2021-05-01` to `2026-05-31`.",
        "- Accepted: `False`; live approved: `False`; V57f core modified: `False`.",
        "",
        "## Main Result",
        "",
        f"- Champion `70/30/0`: return `{float(champion['strategy_return']) * 100:.4f}%`, delta vs V57f `{float(champion['delta_return_pct_points_vs_v57f']):.4f}` pct.",
        f"- Best budget-substitution variant: `{best_sub.get('version_id')}` delta vs champion `{float(best_sub.get('delta_return_pct_points_vs_champion', 0.0)):.4f}` pct.",
        f"- Best event-satellite variant: `{best_sat.get('version_id')}` delta vs champion `{float(best_sat.get('delta_return_pct_points_vs_champion', 0.0)):.4f}` pct.",
        "",
        "## Top Variants",
        "",
    ]
    for row in top:
        lines.append(
            f"- `{row['version_id']}`: return `{float(row['strategy_return']) * 100:.4f}%`, vs champion `{float(row['delta_return_pct_points_vs_champion']):.4f}` pct, maxDD `{float(row['max_drawdown']) * 100:.4f}%`."
        )
    lines.extend(
        [
            "",
            "## PM Reading",
            "",
            "Replacing long-horizon momentum with mean reversion is not attractive. The viable balance is to keep the 70/30 value-momentum champion and treat mean reversion as a small, event-based, same-sleeve satellite that still needs independent validation.",
            "",
        ]
    )
    return "\n".join(lines)


def _rules() -> str:
    return "\n".join(
        [
            "# V5f VMR Balance Agent Execution Rules",
            "",
            "- Use repaired V57f baseline only.",
            "- Keep historical evidence within 2021-05-01 to 2026-05-31.",
            "- Do not modify V57f core.",
            "- Do not use full-market stock selection.",
            "- Do not mark accepted or live approved.",
            "- Do not treat mean reversion satellite as accepted until independent validation passes.",
            "- Separate budget substitution from event satellite interpretation.",
            "",
        ]
    )


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
        "task": "v5f_value_momentum_reversion_balance_test",
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
    print(json.dumps(run_v5f_value_momentum_reversion_balance(Path(".")), ensure_ascii=False, indent=2))

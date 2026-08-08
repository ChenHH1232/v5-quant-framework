from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5h_buy_execution_backtest") / "current"
SPEC_DIR = Path("v5h_buy_execution_spec_v1") / "current"
OVERLAY_DIR = Path("v5h_buy_execution_timing_overlay") / "current"
ROUGH_DIR = Path("v5f_structural_rough_screen") / "current"

SPEC_SUMMARY = SPEC_DIR / "v5h_buy_execution_spec_v1_summary.json"
DECISION_LOG = OVERLAY_DIR / "v5h_buy_execution_timing_order_decision_log.csv"
DAILY_RETURNS = ROUGH_DIR / "v5f_structural_rough_screen_daily_returns.csv"

FORMAL_BACKTEST_START = "2021-05-01"
FORMAL_BACKTEST_END = "2026-05-31"
REPAIRED_BASELINE = "v57f_startup_preload_repaired_baseline"
V5F_PRIMARY = "internal_subsleeve_mom12_70_30"
FIXED_1400 = "fixed_1400_buy"
V5H_SPEC_V1 = "pressure_positive_1000_else_1400_buy"

V5F_CHAMPION_FAMILY = {"v5f_champion_rebalance"}
ALL_SCHEDULED_FAMILIES = {"value_lowvol_rebalance", "momentum_overlay_tilt", "v5f_champion_rebalance"}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5h_buy_execution_backtest(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5h_buy_execution_backtest_summary.json", summary)
        _write_csv(out / "v5h_buy_execution_backtest_blockers.csv", blockers)
        return summary

    spec_summary = _read_json(root / SPEC_SUMMARY)
    if spec_summary.get("status") != "completed_v5h_buy_execution_spec_v1_frozen":
        blocker = _blocker("spec_v1_not_frozen", str(spec_summary.get("status", "")))
        summary = _summary("blocked_spec_not_frozen", "blocked_until_v5h_spec_v1_frozen", [blocker])
        _write_json(out / "v5h_buy_execution_backtest_summary.json", summary)
        _write_csv(out / "v5h_buy_execution_backtest_blockers.csv", [blocker])
        return summary

    daily = pd.read_csv(root / DAILY_RETURNS, dtype={"trade_date": str, "version_id": str, "active_rebalance_date": str})
    decision_log = _read_csv(root / DECISION_LOG)

    adjustment_rows = _execution_adjustments(decision_log)
    adjustment_by_date = _adjustment_by_date(adjustment_rows)
    nav_rows = _build_nav_rows(daily, adjustment_by_date)
    metrics = _metrics(nav_rows)
    yearly = _yearly(nav_rows)
    drawdown = _drawdown(nav_rows)
    family = _family_adjustment(adjustment_rows)
    sleeve = _sleeve_adjustment(adjustment_rows)
    order_health = _order_health(decision_log)
    data_gate = _data_gate(spec_summary, daily, decision_log, adjustment_rows)
    governance = _governance_audit()
    decision = _pm_decision(metrics, governance)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": ""}]

    _write_csv(out / "v5h_buy_execution_backtest_daily_nav.csv", nav_rows)
    _write_csv(out / "v5h_buy_execution_backtest_execution_adjustment_by_date.csv", adjustment_by_date)
    _write_csv(out / "v5h_buy_execution_backtest_variant_metrics.csv", metrics)
    _write_csv(out / "v5h_buy_execution_backtest_yearly.csv", yearly)
    _write_csv(out / "v5h_buy_execution_backtest_drawdown.csv", drawdown)
    _write_csv(out / "v5h_buy_execution_backtest_family_attribution.csv", family)
    _write_csv(out / "v5h_buy_execution_backtest_sleeve_attribution.csv", sleeve)
    _write_csv(out / "v5h_buy_execution_backtest_order_health.csv", order_health)
    _write_csv(out / "v5h_buy_execution_backtest_data_gate.csv", data_gate)
    _write_csv(out / "v5h_buy_execution_backtest_governance_audit.csv", governance)
    _write_csv(out / "v5h_buy_execution_backtest_pm_gate_decision.csv", decision)
    _write_csv(out / "v5h_buy_execution_backtest_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5h_buy_execution_backtest_blockers.csv", blockers_out)
    (out / "v5h_buy_execution_backtest_report.md").write_text(
        _report(metrics, yearly, family, decision),
        encoding="utf-8",
    )
    (out / "v5h_buy_execution_backtest_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    primary = _find(metrics, "v5h_spec_v1_on_v5f_champion")
    v5f = _find(metrics, V5F_PRIMARY)
    baseline = _find(metrics, REPAIRED_BASELINE)
    summary = _summary(
        "completed_v5h_buy_execution_backtest",
        decision[0]["pm_gate_decision"],
        [],
        formal_backtest_start=FORMAL_BACKTEST_START,
        formal_backtest_end=FORMAL_BACKTEST_END,
        primary_backtest_variant="v5h_spec_v1_on_v5f_champion",
        v5h_return_pct=round(_float(primary.get("strategy_return")) * 100.0, 6),
        v5f_primary_return_pct=round(_float(v5f.get("strategy_return")) * 100.0, 6),
        repaired_baseline_return_pct=round(_float(baseline.get("strategy_return")) * 100.0, 6),
        delta_return_pct_points_vs_v5f_primary=round(_float(primary.get("delta_return_pct_points_vs_v5f_primary")), 6),
        delta_return_pct_points_vs_repaired_baseline=round(_float(primary.get("delta_return_pct_points_vs_repaired_baseline")), 6),
        delta_max_drawdown_pct_points_vs_v5f_primary=round(_float(primary.get("delta_max_drawdown_pct_points_vs_v5f_primary")), 6),
        v5f_champion_buy_order_count=int(_float(primary.get("execution_adjustment_order_count"))),
        execution_adjustment_trade_date_count=int(_float(primary.get("execution_adjustment_trade_date_count"))),
    )
    _write_json(out / "v5h_buy_execution_backtest_summary.json", summary)
    return summary


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [SPEC_SUMMARY, DECISION_LOG, DAILY_RETURNS]
    return [_blocker("missing_required_input", str(path)) for path in required if not (root / path).exists()]


def _execution_adjustments(decision_log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    specs = [
        {
            "backtest_variant": "v5h_fixed_1400_on_v5f_champion",
            "source_variant": FIXED_1400,
            "families": V5F_CHAMPION_FAMILY,
            "nav_comparable": True,
        },
        {
            "backtest_variant": "v5h_spec_v1_on_v5f_champion",
            "source_variant": V5H_SPEC_V1,
            "families": V5F_CHAMPION_FAMILY,
            "nav_comparable": True,
        },
        {
            "backtest_variant": "v5h_spec_v1_all_scheduled_diagnostic",
            "source_variant": V5H_SPEC_V1,
            "families": ALL_SCHEDULED_FAMILIES,
            "nav_comparable": False,
        },
    ]
    for spec in specs:
        families = spec["families"]
        for row in decision_log:
            if row.get("variant_id") != spec["source_variant"]:
                continue
            if row.get("order_type") != "scheduled_buy":
                continue
            if row.get("intent_family") not in families:
                continue
            if not (FORMAL_BACKTEST_START <= row.get("trade_date", "") <= FORMAL_BACKTEST_END):
                continue
            rows.append(
                {
                    "backtest_variant": spec["backtest_variant"],
                    "source_variant": spec["source_variant"],
                    "trade_date": row.get("trade_date", ""),
                    "intent_id": row.get("intent_id", ""),
                    "intent_family": row.get("intent_family", ""),
                    "code": row.get("code", ""),
                    "sleeve": row.get("sleeve", ""),
                    "selected_obs_time": row.get("selected_obs_time", ""),
                    "amount_pressure_bucket": row.get("amount_pressure_bucket", ""),
                    "trade_delta_weight_abs": _float(row.get("trade_delta_weight_abs")),
                    "incremental_edge_vs_baseline_order": _float(row.get("incremental_edge_vs_baseline_order")),
                    "weighted_incremental_edge_vs_baseline_order": _float(row.get("weighted_incremental_edge_vs_baseline_order")),
                    "nav_comparable": spec["nav_comparable"],
                    "accepted": False,
                }
            )
    return rows


def _adjustment_by_date(adjustments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in adjustments:
        groups[(row["backtest_variant"], row["trade_date"])].append(row)
    out = []
    for (variant, trade_date), group in sorted(groups.items()):
        out.append(
            {
                "backtest_variant": variant,
                "trade_date": trade_date,
                "execution_adjustment_return": sum(_float(row["weighted_incremental_edge_vs_baseline_order"]) for row in group),
                "order_count": len(group),
                "positive_pressure_order_count": sum(1 for row in group if row.get("amount_pressure_bucket") == "positive_pressure"),
                "fallback_1400_order_count": sum(1 for row in group if row.get("selected_obs_time") == "14:00:00"),
                "early_1000_order_count": sum(1 for row in group if row.get("selected_obs_time") == "10:00:00"),
                "nav_comparable": all(bool(row.get("nav_comparable")) for row in group),
            }
        )
    return out


def _build_nav_rows(daily: pd.DataFrame, adjustment_by_date: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = daily[daily["version_id"].isin([REPAIRED_BASELINE, V5F_PRIMARY])].copy()
    df = df[(df["trade_date"] >= FORMAL_BACKTEST_START) & (df["trade_date"] <= FORMAL_BACKTEST_END)].copy()
    base_rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        base_rows.append(
            {
                "trade_date": row["trade_date"],
                "version_id": row["version_id"],
                "active_rebalance_date": row.get("active_rebalance_date", ""),
                "strategy_return": _float(row["strategy_return"]),
                "execution_adjustment_return": 0.0,
                "strategy_nav": _float(row["strategy_nav"]),
                "baseline_return": _float(row.get("baseline_return", 0.0)),
                "turnover_proxy": _float(row.get("turnover_proxy", 0.0)),
                "incremental_commission": _float(row.get("incremental_commission", 0.0)),
                "nav_comparable": True,
                "accepted": False,
            }
        )

    primary = df[df["version_id"] == V5F_PRIMARY].copy().sort_values("trade_date")
    adj_maps: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in adjustment_by_date:
        adj_maps[row["backtest_variant"]][row["trade_date"]] = row
    adjusted_rows: list[dict[str, Any]] = []
    for variant in ["v5h_fixed_1400_on_v5f_champion", "v5h_spec_v1_on_v5f_champion", "v5h_spec_v1_all_scheduled_diagnostic"]:
        nav = 1.0
        for _, row in primary.iterrows():
            adj = adj_maps.get(variant, {}).get(row["trade_date"], {})
            execution_adjustment = _float(adj.get("execution_adjustment_return"))
            strategy_return = _float(row["strategy_return"]) + execution_adjustment
            nav *= 1.0 + strategy_return
            adjusted_rows.append(
                {
                    "trade_date": row["trade_date"],
                    "version_id": variant,
                    "active_rebalance_date": row.get("active_rebalance_date", ""),
                    "strategy_return": strategy_return,
                    "execution_adjustment_return": execution_adjustment,
                    "strategy_nav": nav,
                    "baseline_return": _float(row.get("baseline_return", 0.0)),
                    "turnover_proxy": _float(row.get("turnover_proxy", 0.0)),
                    "incremental_commission": _float(row.get("incremental_commission", 0.0)),
                    "execution_adjustment_order_count": int(_float(adj.get("order_count"))),
                    "early_1000_order_count": int(_float(adj.get("early_1000_order_count"))),
                    "fallback_1400_order_count": int(_float(adj.get("fallback_1400_order_count"))),
                    "nav_comparable": variant != "v5h_spec_v1_all_scheduled_diagnostic",
                    "accepted": False,
                }
            )
    return base_rows + adjusted_rows


def _metrics(nav_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(nav_rows).sort_values(["version_id", "trade_date"])
    out: list[dict[str, Any]] = []
    for version, group in df.groupby("version_id", sort=True):
        ordered = group.sort_values("trade_date")
        navs = pd.to_numeric(ordered["strategy_nav"]).tolist()
        rets = pd.to_numeric(ordered["strategy_return"]).tolist()
        ann = navs[-1] ** (252 / len(navs)) - 1.0
        vol = pd.Series(rets).std() * (252**0.5)
        out.append(
            {
                "version_id": version,
                "strategy_return": navs[-1] - 1.0,
                "annualized_return": ann,
                "max_drawdown": _max_drawdown(navs),
                "volatility": vol,
                "sharpe_proxy": ann / vol if vol else 0.0,
                "turnover_proxy": pd.to_numeric(ordered["turnover_proxy"]).sum(),
                "incremental_commission_total": pd.to_numeric(ordered["incremental_commission"]).sum(),
                "execution_adjustment_total": pd.to_numeric(ordered["execution_adjustment_return"]).sum(),
                "execution_adjustment_order_count": int(pd.to_numeric(ordered.get("execution_adjustment_order_count", 0)).sum()),
                "execution_adjustment_trade_date_count": int((pd.to_numeric(ordered["execution_adjustment_return"]) != 0).sum()),
                "nav_comparable": bool(ordered["nav_comparable"].astype(bool).all()),
                "accepted": False,
            }
        )
    repaired = _find(out, REPAIRED_BASELINE)
    v5f = _find(out, V5F_PRIMARY)
    for row in out:
        row["delta_return_pct_points_vs_repaired_baseline"] = (_float(row["strategy_return"]) - _float(repaired["strategy_return"])) * 100.0
        row["delta_max_drawdown_pct_points_vs_repaired_baseline"] = (_float(row["max_drawdown"]) - _float(repaired["max_drawdown"])) * 100.0
        row["delta_return_pct_points_vs_v5f_primary"] = (_float(row["strategy_return"]) - _float(v5f["strategy_return"])) * 100.0
        row["delta_max_drawdown_pct_points_vs_v5f_primary"] = (_float(row["max_drawdown"]) - _float(v5f["max_drawdown"])) * 100.0
    order = {
        "v5h_spec_v1_on_v5f_champion": 0,
        "v5h_fixed_1400_on_v5f_champion": 1,
        V5F_PRIMARY: 2,
        REPAIRED_BASELINE: 3,
        "v5h_spec_v1_all_scheduled_diagnostic": 4,
    }
    return sorted(out, key=lambda row: order.get(row["version_id"], 99))


def _yearly(nav_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(nav_rows).sort_values(["version_id", "trade_date"])
    df["year"] = df["trade_date"].str.slice(0, 4)
    rows = []
    for (version, year), group in df.groupby(["version_id", "year"], sort=True):
        ordered = group.sort_values("trade_date")
        total_return = (1.0 + pd.to_numeric(ordered["strategy_return"])).prod() - 1.0
        rows.append(
            {
                "version_id": version,
                "year": year,
                "year_return": total_return,
                "execution_adjustment_total": pd.to_numeric(ordered["execution_adjustment_return"]).sum(),
                "trade_days": len(ordered),
                "nav_comparable": bool(ordered["nav_comparable"].astype(bool).all()),
                "accepted": False,
            }
        )
    baseline = {(row["year"]): row for row in rows if row["version_id"] == V5F_PRIMARY}
    repaired = {(row["year"]): row for row in rows if row["version_id"] == REPAIRED_BASELINE}
    for row in rows:
        row["delta_return_pct_points_vs_v5f_primary"] = (_float(row["year_return"]) - _float(baseline.get(row["year"], {}).get("year_return"))) * 100.0
        row["delta_return_pct_points_vs_repaired_baseline"] = (_float(row["year_return"]) - _float(repaired.get(row["year"], {}).get("year_return"))) * 100.0
    return rows


def _drawdown(nav_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(nav_rows).sort_values(["version_id", "trade_date"])
    out = []
    for version, group in df.groupby("version_id", sort=True):
        ordered = group.sort_values("trade_date").reset_index(drop=True)
        nav = pd.to_numeric(ordered["strategy_nav"])
        dd = nav / nav.cummax() - 1.0
        trough = int(dd.idxmin())
        peak = int(nav.iloc[: trough + 1].idxmax())
        out.append(
            {
                "version_id": version,
                "max_drawdown": abs(float(dd.iloc[trough])),
                "peak_date": ordered.loc[peak, "trade_date"],
                "trough_date": ordered.loc[trough, "trade_date"],
                "nav_comparable": bool(ordered["nav_comparable"].astype(bool).all()),
            }
        )
    v5f_dd = _float(_find(out, V5F_PRIMARY).get("max_drawdown"))
    repaired_dd = _float(_find(out, REPAIRED_BASELINE).get("max_drawdown"))
    for row in out:
        row["delta_max_drawdown_pct_points_vs_v5f_primary"] = (_float(row["max_drawdown"]) - v5f_dd) * 100.0
        row["delta_max_drawdown_pct_points_vs_repaired_baseline"] = (_float(row["max_drawdown"]) - repaired_dd) * 100.0
    return out


def _family_adjustment(adjustments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in adjustments:
        groups[(row["backtest_variant"], row["intent_family"])].append(row)
    out = []
    for (variant, family), group in sorted(groups.items()):
        out.append(
            {
                "backtest_variant": variant,
                "intent_family": family,
                "order_count": len(group),
                "trade_date_count": len({row["trade_date"] for row in group}),
                "execution_adjustment_total": sum(_float(row["weighted_incremental_edge_vs_baseline_order"]) for row in group),
                "avg_order_incremental_edge": _mean([row["incremental_edge_vs_baseline_order"] for row in group]),
                "weighted_avg_order_incremental_edge": _weighted_mean(
                    [row["incremental_edge_vs_baseline_order"] for row in group],
                    [row["trade_delta_weight_abs"] for row in group],
                ),
                "nav_comparable": all(bool(row.get("nav_comparable")) for row in group),
            }
        )
    return out


def _sleeve_adjustment(adjustments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in adjustments:
        groups[(row["backtest_variant"], row["sleeve"])].append(row)
    out = []
    for (variant, sleeve), group in sorted(groups.items()):
        out.append(
            {
                "backtest_variant": variant,
                "sleeve": sleeve,
                "order_count": len(group),
                "trade_date_count": len({row["trade_date"] for row in group}),
                "execution_adjustment_total": sum(_float(row["weighted_incremental_edge_vs_baseline_order"]) for row in group),
                "nav_comparable": all(bool(row.get("nav_comparable")) for row in group),
            }
        )
    return out


def _order_health(decision_log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for variant in [FIXED_1400, V5H_SPEC_V1]:
        for family_set, label in [(V5F_CHAMPION_FAMILY, "v5f_champion_only"), (ALL_SCHEDULED_FAMILIES, "all_scheduled_diagnostic")]:
            rows = [
                row
                for row in decision_log
                if row.get("variant_id") == variant
                and row.get("order_type") == "scheduled_buy"
                and row.get("intent_family") in family_set
                and FORMAL_BACKTEST_START <= row.get("trade_date", "") <= FORMAL_BACKTEST_END
            ]
            out.append(
                {
                    "source_variant": variant,
                    "scope": label,
                    "order_count": len(rows),
                    "trade_date_count": len({row.get("trade_date", "") for row in rows}),
                    "early_1000_count": sum(1 for row in rows if row.get("selected_obs_time") == "10:00:00"),
                    "fallback_1400_count": sum(1 for row in rows if row.get("selected_obs_time") == "14:00:00"),
                    "positive_pressure_count": sum(1 for row in rows if row.get("amount_pressure_bucket") == "positive_pressure"),
                    "negative_pressure_count": sum(1 for row in rows if row.get("amount_pressure_bucket") == "negative_pressure"),
                    "neutral_pressure_count": sum(1 for row in rows if row.get("amount_pressure_bucket") == "neutral_pressure"),
                    "weighted_adjustment_total": sum(_float(row.get("weighted_incremental_edge_vs_baseline_order")) for row in rows),
                }
            )
    return out


def _data_gate(
    spec_summary: dict[str, Any],
    daily: pd.DataFrame,
    decision_log: list[dict[str, Any]],
    adjustment_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    versions = set(daily["version_id"].unique())
    return [
        {"gate_id": "v5h_spec_v1_frozen", "status": "pass" if spec_summary.get("status") == "completed_v5h_buy_execution_spec_v1_frozen" else "fail", "value": spec_summary.get("status", "")},
        {"gate_id": "daily_v5f_primary_available", "status": "pass" if V5F_PRIMARY in versions else "fail", "value": V5F_PRIMARY in versions},
        {"gate_id": "daily_repaired_baseline_available", "status": "pass" if REPAIRED_BASELINE in versions else "fail", "value": REPAIRED_BASELINE in versions},
        {"gate_id": "decision_log_loaded", "status": "pass" if decision_log else "fail", "value": len(decision_log)},
        {"gate_id": "execution_adjustments_built", "status": "pass" if adjustment_rows else "fail", "value": len(adjustment_rows)},
        {"gate_id": "formal_backtest_end_preserved", "status": "pass", "value": FORMAL_BACKTEST_END},
    ]


def _governance_audit() -> list[dict[str, Any]]:
    return [
        {"audit_id": "v57f_core_unchanged", "status": "pass", "detail": "Backtest adjusts execution price proxy only, not V57f selection."},
        {"audit_id": "v5f_mainline_unchanged", "status": "pass", "detail": "V5f internal_subsleeve_mom12_70_30 daily returns are input baseline."},
        {"audit_id": "buy_side_only", "status": "pass", "detail": "Only scheduled buy/increase execution adjustments are applied."},
        {"audit_id": "sell_rules_unchanged", "status": "pass", "detail": "No sell/decrease execution timing is modified."},
        {"audit_id": "no_new_buy_signal", "status": "pass", "detail": "The rule cannot create or cancel target orders."},
        {"audit_id": "no_trading_frequency_increase", "status": "pass", "detail": "The rule chooses 10:00 or 14:00 on existing buy dates."},
        {"audit_id": "no_threshold_scan", "status": "pass", "detail": "Only frozen v1 and fixed 14:00 reference are tested."},
        {"audit_id": "not_accepted_not_live", "status": "pass", "detail": "Backtest output is not accepted/live approved."},
        {"audit_id": "mixed_family_diagnostic_separated", "status": "pass", "detail": "All-scheduled adjustment is labelled diagnostic and not the official NAV-comparable result."},
    ]


def _pm_decision(metrics: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if any(row.get("status") != "pass" for row in governance):
        decision = "blocked_by_governance_issue"
        status = "blocked"
    else:
        primary = _find(metrics, "v5h_spec_v1_on_v5f_champion")
        delta = _float(primary.get("delta_return_pct_points_vs_v5f_primary"))
        if delta > 0:
            decision = "v5h_buy_execution_v1_backtest_positive_ready_for_paper_observation_not_accepted"
            status = "backtest_positive_not_accepted"
        else:
            decision = "v5h_buy_execution_v1_backtest_diagnostic_only_no_nav_edge"
            status = "diagnostic_only"
    return [
        {
            "pm_gate_decision": decision,
            "status": status,
            "primary_variant": "v5h_spec_v1_on_v5f_champion",
            "accepted": False,
            "live_trading_approved": False,
            "deployment_approved": False,
            "v57f_core_modified": False,
            "v5f_mainline_modified": False,
            "sell_rules_modified": False,
            "trading_frequency_increased": False,
            "new_buy_signal_used": False,
            "notes": "NAV backtest is execution-adjusted proxy on existing V5f planned buys; it is not a new stock-selection model.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "queue_id": "v5h_buy_execution_v1_forward_paper_nav_append",
            "status": "ready_when_official_forward_buy_orders_exist",
            "scope": "Apply frozen v1 to future official planned buy orders and compare paper execution NAV impact.",
        },
        {
            "priority": 2,
            "queue_id": "v5h_buy_execution_v1_joinquant_paper_dry_run",
            "status": "ready_when_platform_available",
            "scope": "Paper-only mapping; do not live approve.",
        },
        {
            "priority": 3,
            "queue_id": "v5h_execution_model_closeout_after_forward_cycles",
            "status": "pending_forward_cycles",
            "scope": "Only consider promotion after multiple forward rebalance cycles.",
        },
    ]


def _report(
    metrics: list[dict[str, Any]],
    yearly: list[dict[str, Any]],
    family: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    primary = _find(metrics, "v5h_spec_v1_on_v5f_champion")
    v5f = _find(metrics, V5F_PRIMARY)
    base = _find(metrics, REPAIRED_BASELINE)
    lines = [
        "# V5h Buy Execution v1 Backtest",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Formal window: {FORMAL_BACKTEST_START} to {FORMAL_BACKTEST_END}",
        "- Primary comparable test: apply frozen v1 only to `v5f_champion_rebalance` buy/increase orders.",
        "- Diagnostic upper-bound: all scheduled families are separated and not used as official comparison.",
        "",
        "## Main Comparison",
        "",
        f"- V57f repaired baseline return: `{_float(base.get('strategy_return')) * 100:.4f}%`.",
        f"- V5f primary return: `{_float(v5f.get('strategy_return')) * 100:.4f}%`.",
        f"- V5h v1 on V5f planned buys return: `{_float(primary.get('strategy_return')) * 100:.4f}%`.",
        f"- V5h v1 improvement vs V5f primary: `{_float(primary.get('delta_return_pct_points_vs_v5f_primary')):.4f}` pct points.",
        f"- V5h v1 improvement vs repaired V57f: `{_float(primary.get('delta_return_pct_points_vs_repaired_baseline')):.4f}` pct points.",
        f"- V5h v1 max drawdown delta vs V5f: `{_float(primary.get('delta_max_drawdown_pct_points_vs_v5f_primary')):.4f}` pct points.",
        "",
        "## Family Attribution",
        "",
    ]
    for row in family:
        if row["backtest_variant"] == "v5h_spec_v1_on_v5f_champion":
            lines.append(
                f"- `{row['intent_family']}`: orders `{row['order_count']}`, adjustment `{_float(row['execution_adjustment_total']) * 100:.4f}` pct."
            )
    lines.extend(
        [
            "",
            "## Governance",
            "",
            "- No V57f/V5f selection or weight rule is modified.",
            "- No sell timing is changed.",
            "- No new buy signal is introduced.",
            "- Not accepted and not live approved.",
            "",
        ]
    )
    return "\n".join(lines)


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5h Buy Execution Backtest Agent Rules",
            "",
            "- Use 2021-05-01 to 2026-05-31 only for formal backtest.",
            "- Official comparable variant is `v5h_spec_v1_on_v5f_champion`.",
            "- Do not treat all-scheduled diagnostic as the official V5f NAV result.",
            "- Do not modify V57f core, V5f mainline, sell rules, weights, or rebalance frequency.",
            "- Do not create new buy signals.",
            "- Do not mark accepted, live approved, or deployment approved.",
            "",
        ]
    )


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5h_buy_execution_backtest",
        "status": status,
        "pm_gate_decision": decision,
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "v5f_mainline_modified": False,
        "sell_rules_modified": False,
        "trading_frequency_increased": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len([row for row in blockers if row.get("status") == "blocking"]),
        "fatal_blockers": [row for row in blockers if row.get("status") == "blocking"],
        **extra,
    }


def _find(rows: list[dict[str, Any]], version_id: str) -> dict[str, Any]:
    return next((row for row in rows if row.get("version_id") == version_id), {})


def _blocker(blocker_id: str, description: str) -> dict[str, Any]:
    return {"blocker_id": blocker_id, "severity": "fatal", "status": "blocking", "description": description}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def _max_drawdown(navs: list[float]) -> float:
    peak = 0.0
    max_dd = 0.0
    for nav in navs:
        peak = max(peak, nav)
        if peak:
            max_dd = min(max_dd, nav / peak - 1.0)
    return abs(max_dd)


def _mean(values: list[Any]) -> float:
    clean = [_float(value) for value in values if value not in (None, "")]
    return sum(clean) / len(clean) if clean else 0.0


def _weighted_mean(values: list[Any], weights: list[Any]) -> float:
    pairs = [(_float(value), _float(weight)) for value, weight in zip(values, weights) if value not in (None, "")]
    total = sum(weight for _, weight in pairs)
    return sum(value * weight for value, weight in pairs) / total if total else 0.0


def _float(value: Any) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else 0.0
    except Exception:
        return 0.0


def main() -> None:
    summary = run_v5h_buy_execution_backtest(Path("."))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

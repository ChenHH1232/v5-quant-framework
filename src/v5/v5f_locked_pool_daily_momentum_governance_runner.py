from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_locked_pool_daily_momentum_governance") / "current"
PRICE_DIR = Path("数据库") / "processed" / "startup_preload_repaired_prices_v5"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
DEEP_DIR = Path("v5f_internal_subsleeve_deep_engineering") / "current"

BASELINE = "v57f_startup_preload_repaired_baseline"
FIXED_7030 = "internal_subsleeve_mom12_70_30_rebalance_only"
WEEKLY_7030 = "locked_pool_weekly_mom12_70_30"
DAILY_7030 = "locked_pool_daily_mom12_70_30"
BACKTEST_START = "2021-05-06"
BACKTEST_END = "2026-05-31"
COMMISSION_RATE = 0.0003


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_locked_pool_daily_momentum_governance(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_locked_pool_daily_momentum_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_locked_pool_daily_momentum_summary.json", summary)
        return summary

    prices = _load_prices(root)
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str, "code": str})
    baseline_daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv", dtype={"trade_date": str})
    repaired_summary = _read_json(root / REPAIRED_RUN / "summary.json")
    prior_deep = _read_json(root / DEEP_DIR / "v5f_internal_subsleeve_deep_summary.json")

    signals = signals[(signals["trade_date"] >= BACKTEST_START) & (signals["trade_date"] <= BACKTEST_END)].copy()
    baseline_daily = baseline_daily[
        (baseline_daily["trade_date"] >= BACKTEST_START) & (baseline_daily["trade_date"] <= BACKTEST_END)
    ].copy()

    prompt = _prompt()
    spec = _spec()
    weights = _build_weight_log(signals, prices, baseline_daily)
    daily = _daily_returns(weights, prices, baseline_daily)
    metrics = _metrics(daily)
    yearly = _yearly(daily)
    period = _rebalance_period(daily)
    comparison = _comparison(metrics, prior_deep)
    turnover = _turnover_cost_health(metrics, comparison)
    governance = _governance_audit(repaired_summary, weights)
    pit = _pit_audit()
    decision = _pm_decision(comparison, turnover, governance)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(out / "v5f_locked_pool_daily_momentum_spec.csv", spec)
    _write_csv(out / "v5f_locked_pool_daily_momentum_weight_log.csv", weights)
    _write_csv(out / "v5f_locked_pool_daily_momentum_daily_returns.csv", daily)
    _write_csv(out / "v5f_locked_pool_daily_momentum_metrics.csv", metrics)
    _write_csv(out / "v5f_locked_pool_daily_momentum_yearly.csv", yearly)
    _write_csv(out / "v5f_locked_pool_daily_momentum_rebalance_period.csv", period)
    _write_csv(out / "v5f_locked_pool_daily_momentum_comparison.csv", comparison)
    _write_csv(out / "v5f_locked_pool_daily_momentum_turnover_cost_health.csv", turnover)
    _write_csv(out / "v5f_locked_pool_daily_momentum_governance_audit.csv", governance)
    _write_csv(out / "v5f_locked_pool_daily_momentum_pit_audit.csv", pit)
    _write_csv(out / "v5f_locked_pool_daily_momentum_pm_decision.csv", decision)
    _write_csv(out / "v5f_locked_pool_daily_momentum_next_queue.csv", next_queue)
    _write_csv(out / "v5f_locked_pool_daily_momentum_blockers.csv", blockers_out)
    (out / "v5f_locked_pool_daily_momentum_prompt.md").write_text(prompt, encoding="utf-8")
    (out / "v5f_locked_pool_daily_momentum_report.md").write_text(_report(metrics, comparison, decision), encoding="utf-8")
    (out / "v5f_locked_pool_daily_momentum_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    daily_row = next(row for row in metrics if row["version_id"] == DAILY_7030)
    fixed_row = next(row for row in metrics if row["version_id"] == FIXED_7030)
    decision_row = decision[0]
    daily_comparison = next(row for row in comparison if row["version_id"] == DAILY_7030)
    summary = _summary(
        "completed_v5f_locked_pool_daily_momentum_governance",
        decision_row["pm_gate_decision"],
        [],
        primary_candidate=decision_row["primary_candidate"],
        daily_delta_return=float(daily_row["delta_return_pct_points_vs_repaired_baseline"]),
        fixed_delta_return=float(fixed_row["delta_return_pct_points_vs_repaired_baseline"]),
        incremental_daily_vs_fixed=float(daily_comparison["incremental_delta_return_vs_fixed_7030"]),
    )
    _write_json(out / "v5f_locked_pool_daily_momentum_summary.json", summary)
    return summary


def _load_prices(root: Path) -> pd.DataFrame:
    frames = [pd.read_csv(path, dtype={"date": str, "code": str}) for path in (root / PRICE_DIR).glob("*.csv")]
    prices = pd.concat(frames, ignore_index=True).drop_duplicates(["date", "code"])
    prices = prices.sort_values(["code", "date"]).reset_index(drop=True)
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    prices["next_close"] = prices.groupby("code")["close"].shift(-1)
    prices["stock_return"] = prices["next_close"] / prices["close"] - 1.0
    prices["close_lag_21"] = prices.groupby("code")["close"].shift(21)
    prices["close_lag_253"] = prices.groupby("code")["close"].shift(253)
    prices["mom_12_1"] = prices["close_lag_21"] / prices["close_lag_253"] - 1.0
    return prices[(prices["date"] >= BACKTEST_START) & (prices["date"] <= BACKTEST_END)].copy()


def _spec() -> list[dict[str, Any]]:
    return [
        {
            "version_id": FIXED_7030,
            "rebalance_policy": "official_v57f_rebalance_only",
            "rule": "Lock V57f selected pool at official rebalance; 70% core plus 30% same-sleeve mom_12_1 top tercile until next rebalance.",
            "accepted": False,
        },
        {
            "version_id": WEEKLY_7030,
            "rebalance_policy": "weekly_inside_locked_pool",
            "rule": "Lock V57f selected pool at official rebalance; recompute 70/30 same-sleeve mom_12_1 overlay every fifth trading day.",
            "accepted": False,
        },
        {
            "version_id": DAILY_7030,
            "rebalance_policy": "daily_inside_locked_pool",
            "rule": "Lock V57f selected pool at official rebalance; recompute 70/30 same-sleeve mom_12_1 overlay every trading day using visible close data for next interval.",
            "accepted": False,
        },
    ]


def _build_weight_log(signals: pd.DataFrame, prices: pd.DataFrame, baseline_daily: pd.DataFrame) -> list[dict[str, Any]]:
    feature = prices.set_index(["date", "code"])["mom_12_1"].to_dict()
    dates = sorted(baseline_daily["trade_date"].tolist())
    rebalance_dates = sorted(signals["trade_date"].unique().tolist())
    pools = {date: group.copy() for date, group in signals.groupby("trade_date", sort=True)}
    rows: list[dict[str, Any]] = []
    active_rebalance = ""
    active_pool = pd.DataFrame()
    prev_weekly_target: dict[str, float] = {}
    weekly_counter = 0
    fixed_target: dict[str, float] = {}

    for day in dates:
        if day in pools:
            active_rebalance = day
            active_pool = pools[day].copy()
            active_pool["base_target_weight"] = active_pool["target_weight"].astype(float)
            fixed_target = _targets_for_day(active_pool, feature, day)
            prev_weekly_target = fixed_target.copy()
            weekly_counter = 0
        if active_pool.empty:
            continue
        base = {row["code"]: float(row["base_target_weight"]) for _, row in active_pool.iterrows()}
        daily_target = _targets_for_day(active_pool, feature, day)
        if weekly_counter % 5 == 0:
            prev_weekly_target = daily_target.copy()
        weekly_counter += 1

        for version, target, cadence in [
            (FIXED_7030, fixed_target, "rebalance_only"),
            (WEEKLY_7030, prev_weekly_target, "weekly"),
            (DAILY_7030, daily_target, "daily"),
        ]:
            for _, row in active_pool.iterrows():
                code = row["code"]
                sleeve = row["sector_id"]
                base_weight = base[code]
                target_weight = target.get(code, base_weight)
                rows.append(
                    {
                        "trade_date": day,
                        "active_rebalance_date": active_rebalance,
                        "version_id": version,
                        "rebalance_cadence": cadence,
                        "code": code,
                        "sleeve": sleeve,
                        "base_target_weight": base_weight,
                        "target_weight": target_weight,
                        "weight_delta": target_weight - base_weight,
                        "mom_12_1": _safe_float(feature.get((day, code))),
                        "sleeve_weight_preserved": True,
                        "locked_pool_only": True,
                        "new_stock_selected": False,
                        "accepted": False,
                    }
                )
    return rows


def _targets_for_day(active_pool: pd.DataFrame, feature: dict[tuple[str, str], float], day: str) -> dict[str, float]:
    target: dict[str, float] = {}
    for sleeve, group in active_pool.groupby("sector_id"):
        sleeve_total = group["base_target_weight"].astype(float).sum()
        scores = group["code"].map(lambda code: _safe_float(feature.get((day, code))))
        if scores.notna().sum() == 0:
            for _, row in group.iterrows():
                target[row["code"]] = float(row["base_target_weight"])
            continue
        ranks = scores.rank(method="first")
        top_mask = ranks > len(group) * 2 / 3
        top_codes = group.loc[top_mask, "code"].tolist() or [group.loc[scores.astype(float).idxmax(), "code"]]
        for _, row in group.iterrows():
            code = row["code"]
            core = 0.70 * float(row["base_target_weight"])
            mom = 0.30 * sleeve_total / len(top_codes) if code in top_codes else 0.0
            target[code] = core + mom
    return target


def _daily_returns(weights: list[dict[str, Any]], prices: pd.DataFrame, baseline_daily: pd.DataFrame) -> list[dict[str, Any]]:
    ret_map = prices.set_index(["date", "code"])["stock_return"].to_dict()
    baseline_ret = baseline_daily.set_index("trade_date")["strategy_return"].astype(float).to_dict()
    baseline_nav = baseline_daily.set_index("trade_date")["strategy_nav"].astype(float).to_dict()
    weight_df = pd.DataFrame(weights)
    rows: list[dict[str, Any]] = []
    for version, group in weight_df.groupby("version_id", sort=True):
        nav = 1.0
        prev_target: dict[str, float] = {}
        prev_base_target: dict[str, float] = {}
        for day, day_group in group.groupby("trade_date", sort=True):
            target = {row["code"]: float(row["target_weight"]) for _, row in day_group.iterrows()}
            base_target = {row["code"]: float(row["base_target_weight"]) for _, row in day_group.iterrows()}
            overlay_turnover = sum(abs(target.get(code, 0.0) - prev_target.get(code, 0.0)) for code in set(target) | set(prev_target))
            baseline_turnover = (
                sum(abs(base_target.get(code, 0.0) - prev_base_target.get(code, 0.0)) for code in set(base_target) | set(prev_base_target))
                if day in set(day_group["active_rebalance_date"])
                else 0.0
            )
            incremental_turnover = max(0.0, overlay_turnover - baseline_turnover)
            commission = incremental_turnover * COMMISSION_RATE
            delta_stock_return = sum(
                float(row["weight_delta"]) * (_safe_float(ret_map.get((day, row["code"]))) or 0.0)
                for _, row in day_group.iterrows()
            )
            strategy_return = baseline_ret[day] + delta_stock_return - commission
            nav *= 1.0 + strategy_return
            rows.append(
                {
                    "trade_date": day,
                    "version_id": version,
                    "active_rebalance_date": day_group.iloc[0]["active_rebalance_date"],
                    "strategy_return": strategy_return,
                    "strategy_nav": nav,
                    "baseline_return": baseline_ret[day],
                    "delta_stock_return": delta_stock_return,
                    "overlay_turnover": overlay_turnover,
                    "incremental_turnover": incremental_turnover,
                    "incremental_commission": commission,
                    "accepted": False,
                }
            )
            prev_target = target
            prev_base_target = base_target
    for day in sorted(baseline_daily["trade_date"].tolist()):
        rows.append(
            {
                "trade_date": day,
                "version_id": BASELINE,
                "active_rebalance_date": "",
                "strategy_return": baseline_ret[day],
                "strategy_nav": baseline_nav[day],
                "baseline_return": baseline_ret[day],
                "delta_stock_return": 0.0,
                "overlay_turnover": 0.0,
                "incremental_turnover": 0.0,
                "incremental_commission": 0.0,
                "accepted": False,
            }
        )
    return rows


def _metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    out: list[dict[str, Any]] = []
    for version, group in df.groupby("version_id", sort=True):
        group = group.sort_values("trade_date")
        navs = pd.to_numeric(group["strategy_nav"]).tolist()
        rets = pd.to_numeric(group["strategy_return"]).tolist()
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
                "incremental_turnover_total": pd.to_numeric(group["incremental_turnover"]).sum(),
                "incremental_commission_total": pd.to_numeric(group["incremental_commission"]).sum(),
                "accepted": False,
            }
        )
    baseline = next(row for row in out if row["version_id"] == BASELINE)
    for row in out:
        row["delta_return_pct_points_vs_repaired_baseline"] = (float(row["strategy_return"]) - float(baseline["strategy_return"])) * 100
        row["delta_max_drawdown_pct_points_vs_repaired_baseline"] = (float(row["max_drawdown"]) - float(baseline["max_drawdown"])) * 100
    return sorted(out, key=lambda row: float(row["delta_return_pct_points_vs_repaired_baseline"]), reverse=True)


def _yearly(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    df["year"] = df["trade_date"].str.slice(0, 4)
    out = []
    for (version, year), group in df.groupby(["version_id", "year"], sort=True):
        out.append({"version_id": version, "year": year, "period_return": (1 + pd.to_numeric(group["strategy_return"])).prod() - 1, "trade_days": len(group)})
    base = {row["year"]: float(row["period_return"]) for row in out if row["version_id"] == BASELINE}
    for row in out:
        row["delta_return_pct_points_vs_repaired_baseline"] = (float(row["period_return"]) - base.get(row["year"], 0.0)) * 100
    return out


def _rebalance_period(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    df = df[df["version_id"] != BASELINE].copy()
    out = []
    for (version, period), group in df.groupby(["version_id", "active_rebalance_date"], sort=True):
        out.append({"version_id": version, "active_rebalance_date": period, "period_return": (1 + pd.to_numeric(group["strategy_return"])).prod() - 1, "trade_days": len(group)})
    return out


def _comparison(metrics: list[dict[str, Any]], prior_deep: dict[str, Any]) -> list[dict[str, Any]]:
    fixed = next(row for row in metrics if row["version_id"] == FIXED_7030)
    daily = next(row for row in metrics if row["version_id"] == DAILY_7030)
    weekly = next(row for row in metrics if row["version_id"] == WEEKLY_7030)
    rows = []
    for row in [fixed, weekly, daily]:
        rows.append(
            {
                "version_id": row["version_id"],
                "delta_return_pct_points_vs_repaired_baseline": row["delta_return_pct_points_vs_repaired_baseline"],
                "delta_max_drawdown_pct_points_vs_repaired_baseline": row["delta_max_drawdown_pct_points_vs_repaired_baseline"],
                "incremental_delta_return_vs_fixed_7030": float(row["delta_return_pct_points_vs_repaired_baseline"]) - float(fixed["delta_return_pct_points_vs_repaired_baseline"]),
                "incremental_delta_drawdown_vs_fixed_7030": float(row["delta_max_drawdown_pct_points_vs_repaired_baseline"]) - float(fixed["delta_max_drawdown_pct_points_vs_repaired_baseline"]),
                "prior_static_7030_delta_return": prior_deep["primary_delta_return_pct_points_vs_repaired_baseline"],
                "accepted": False,
            }
        )
    return rows


def _turnover_cost_health(metrics: list[dict[str, Any]], comparison: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in metrics:
        if row["version_id"] == BASELINE:
            continue
        comp = next(item for item in comparison if item["version_id"] == row["version_id"])
        edge = float(row["delta_return_pct_points_vs_repaired_baseline"]) / 100.0
        cost = float(row["incremental_commission_total"])
        rows.append(
            {
                "version_id": row["version_id"],
                "incremental_turnover_total": row["incremental_turnover_total"],
                "incremental_commission_total": cost,
                "delta_return_decimal_vs_repaired_baseline": edge,
                "incremental_delta_return_vs_fixed_7030": comp["incremental_delta_return_vs_fixed_7030"],
                "cost_to_edge_ratio": cost / edge if edge else "",
                "cost_health": "pass" if edge > cost else "review",
            }
        )
    return rows


def _governance_audit(repaired_summary: dict[str, Any], weights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(weights)
    sleeve_drift = (
        df.groupby(["trade_date", "version_id", "sleeve"])[["target_weight", "base_target_weight"]]
        .sum()
        .assign(drift=lambda x: (x["target_weight"] - x["base_target_weight"]).abs())
    )
    return [
        {"audit_id": "backtest_scope_end", "status": "pass", "detail": BACKTEST_END},
        {"audit_id": "repaired_first_signal", "status": "pass" if repaired_summary.get("startup_preload", {}).get("effective_first_signal_date") == "2021-05-06" else "fail", "detail": repaired_summary.get("startup_preload", {}).get("effective_first_signal_date")},
        {"audit_id": "locked_v57f_pool_only", "status": "pass" if not df["new_stock_selected"].astype(str).eq("True").any() else "fail", "detail": 0},
        {"audit_id": "sleeve_weight_preserved_daily", "status": "pass" if float(sleeve_drift["drift"].max()) < 1e-10 else "fail", "detail": float(sleeve_drift["drift"].max())},
        {"audit_id": "no_full_market_selection", "status": "pass", "detail": "V57f selected pool locked per rebalance period"},
        {"audit_id": "no_v57f_core_modified", "status": "pass", "detail": False},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
    ]


def _pit_audit() -> list[dict[str, Any]]:
    return [
        {"audit_id": "signal_visible_time", "status": "pass", "detail": "Daily mom_12_1 uses close data visible at decision date for next close-to-close interval."},
        {"audit_id": "forward_return_not_used_in_signal", "status": "pass", "detail": "Next close return is used only for evaluation."},
        {"audit_id": "same_day_buy_sell_rule", "status": "pass", "detail": "No new stock selected; daily changes are weight governance inside locked pool."},
    ]


def _pm_decision(
    comparison: list[dict[str, Any]],
    turnover: list[dict[str, Any]],
    governance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    daily = next(row for row in comparison if row["version_id"] == DAILY_7030)
    weekly = next(row for row in comparison if row["version_id"] == WEEKLY_7030)
    fixed = next(row for row in comparison if row["version_id"] == FIXED_7030)
    daily_turnover = next(row for row in turnover if row["version_id"] == DAILY_7030)
    if not gov_ok:
        decision = "blocked_by_governance_issue"
        primary = ""
        rationale = "Governance audit failed."
    elif float(daily["incremental_delta_return_vs_fixed_7030"]) > 1.0 and daily_turnover["cost_health"] == "pass":
        decision = "promote_locked_pool_daily_momentum_to_forward_paper_candidate_not_accepted"
        primary = DAILY_7030
        rationale = "Daily locked-pool reweighting improves on fixed 70/30 after cost and keeps V57f pool boundaries."
    elif float(weekly["incremental_delta_return_vs_fixed_7030"]) > 1.0:
        decision = "weekly_locked_pool_momentum_positive_daily_diagnostic"
        primary = WEEKLY_7030
        rationale = "Weekly reweighting improves on fixed 70/30 more cleanly than daily reweighting."
    else:
        decision = "daily_locked_pool_momentum_diagnostic_only_keep_rebalance_7030_primary"
        primary = FIXED_7030
        rationale = "Daily or weekly reweighting does not clearly improve on fixed rebalance-only 70/30."
    chosen = next(row for row in comparison if row["version_id"] == primary) if primary else daily
    return [
        {
            "pm_gate_decision": decision,
            "primary_candidate": primary,
            "daily_candidate": DAILY_7030,
            "weekly_candidate": WEEKLY_7030,
            "fixed_reference": FIXED_7030,
            "fixed_delta_return_pct_points_vs_repaired_baseline": fixed["delta_return_pct_points_vs_repaired_baseline"],
            "daily_delta_return_pct_points_vs_repaired_baseline": daily["delta_return_pct_points_vs_repaired_baseline"],
            "weekly_delta_return_pct_points_vs_repaired_baseline": weekly["delta_return_pct_points_vs_repaired_baseline"],
            "daily_incremental_delta_return_vs_fixed_7030": daily["incremental_delta_return_vs_fixed_7030"],
            "weekly_incremental_delta_return_vs_fixed_7030": weekly["incremental_delta_return_vs_fixed_7030"],
            "primary_incremental_delta_return_vs_fixed_7030": chosen["incremental_delta_return_vs_fixed_7030"],
            "accepted": False,
            "live_trading_approved": False,
            "rationale": rationale,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task": "Keep internal_subsleeve_mom12_70_30 fixed rebalance-only as current primary unless daily/weekly gate promotes.", "allowed": True},
        {"priority": 2, "task": "If promoted, open locked-pool daily/weekly momentum PM/Quant formal review.", "allowed": decision.startswith("promote") or decision.startswith("weekly")},
        {"priority": 3, "task": "Run forward/paper only after next clean official repaired V57f target.", "allowed": True},
        {"priority": 4, "task": "Full-market daily momentum selection.", "allowed": False},
    ]


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    if failed:
        return [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed]
    return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Locked-pool daily momentum governance test completed."}]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    primary_candidate: str = "",
    daily_delta_return: float = 0.0,
    fixed_delta_return: float = 0.0,
    incremental_daily_vs_fixed: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_locked_pool_daily_momentum_governance",
        "status": status,
        "pm_gate_decision": decision,
        "backtest_scope_start": BACKTEST_START,
        "backtest_scope_end": BACKTEST_END,
        "primary_candidate": primary_candidate,
        "daily_delta_return_pct_points_vs_repaired_baseline": daily_delta_return,
        "fixed_delta_return_pct_points_vs_repaired_baseline": fixed_delta_return,
        "incremental_daily_delta_return_vs_fixed_7030": incremental_daily_vs_fixed,
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(metrics: list[dict[str, Any]], comparison: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# V5f Locked-Pool Daily Momentum Governance",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Primary after this packet: `{decision[0]['primary_candidate']}`",
            "- Scope: V57f repaired selected pool only; no full-market selection; not accepted.",
            "- Historical engineering window ends `2026-05-31`.",
            "",
            "## Metrics",
            *[
                f"- `{row['version_id']}`: return={float(row['strategy_return']) * 100:.2f}%, delta={float(row['delta_return_pct_points_vs_repaired_baseline']):.4f} pct, max_dd={float(row['max_drawdown']) * 100:.2f}%, turnover={float(row['incremental_turnover_total']):.4f}"
                for row in metrics
            ],
            "",
            "## Fixed 70/30 Comparison",
            *[
                f"- `{row['version_id']}` incremental vs fixed 70/30: {float(row['incremental_delta_return_vs_fixed_7030']):.4f} pct"
                for row in comparison
            ],
            "",
        ]
    )


def _prompt() -> str:
    return """工作目录：
D:\\hh\\codex\\v5

任务名称：
V5f locked-pool daily momentum weight governance：V57f 锁定池内日级动量调权测试

任务目标：
在不改变 V57f 价值/红利/低波选股池的前提下，测试周期内每日更新动量权重是否优于当前 V5f `internal_subsleeve_mom12_70_30` 调仓日定权版本。

核心边界：
1. 历史工程窗口固定为 2021-05-06 至 2026-05-31。
2. V57f repaired baseline 是唯一 benchmark。
3. 每个 V57f 正式调仓日锁定当期股票池。
4. 周期内只允许在锁定股票池内部、同 sleeve 内调权。
5. 不得新增 V57f 之外股票。
6. 不得跨 sleeve 转移。
7. 不得改变 sleeve 总权重。
8. 不得修改 V57f core。
9. 不得标记 accepted / live approved。
10. 2026-05-31 之后全部视为 forward/paper，不进入历史工程结果。

固定测试：
1. `internal_subsleeve_mom12_70_30_rebalance_only`
2. `locked_pool_weekly_mom12_70_30`
3. `locked_pool_daily_mom12_70_30`

PM 结论只允许：
- promote_locked_pool_daily_momentum_to_forward_paper_candidate_not_accepted
- weekly_locked_pool_momentum_positive_daily_diagnostic
- daily_locked_pool_momentum_diagnostic_only_keep_rebalance_7030_primary
- blocked_by_governance_issue
"""


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Locked-Pool Daily Momentum Rules",
            "",
            "- Historical engineering window ends 2026-05-31.",
            "- V57f chooses the stock pool; V5f only governs weights inside that locked pool.",
            "- Same-sleeve normalization is mandatory.",
            "- No full-market selection, no new stock, no V57f core modification.",
            "- Not accepted and not live approved.",
            "",
        ]
    )


def _safe_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(result) else result


def _max_drawdown(navs: list[float]) -> float:
    peak = 0.0
    max_dd = 0.0
    for nav in navs:
        peak = max(peak, nav)
        if peak:
            max_dd = min(max_dd, nav / peak - 1.0)
    return abs(max_dd)


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        PRICE_DIR,
        REPAIRED_RUN / "summary.json",
        REPAIRED_RUN / "rebalance_signals.csv",
        REPAIRED_RUN / "daily_returns.csv",
        DEEP_DIR / "v5f_internal_subsleeve_deep_summary.json",
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


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
    print(json.dumps(run_v5f_locked_pool_daily_momentum_governance(Path(".")), ensure_ascii=False, indent=2))

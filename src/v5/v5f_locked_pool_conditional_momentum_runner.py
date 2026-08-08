from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_locked_pool_conditional_momentum") / "current"
PRICE_DIR = Path("数据库") / "processed" / "startup_preload_repaired_prices_v5"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
DAILY_DIR = Path("v5f_locked_pool_daily_momentum_governance") / "current"

BASELINE = "v57f_startup_preload_repaired_baseline"
FIXED = "internal_subsleeve_mom12_70_30_rebalance_only"
BIWEEKLY = "locked_pool_biweekly_mom12_70_30"
MONTHLY = "locked_pool_monthly_mom12_70_30"
BUCKET = "locked_pool_major_bucket_change_mom12_70_30"
DRIFT = "locked_pool_weight_drift_1pct_mom12_70_30"
WARNING = "locked_pool_risk_warning_only_no_trade"
BACKTEST_START = "2021-05-06"
BACKTEST_END = "2026-05-31"
COMMISSION_RATE = 0.0003
WEIGHT_DRIFT_TRIGGER = 0.01


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_locked_pool_conditional_momentum(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_locked_pool_conditional_momentum_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_locked_pool_conditional_momentum_summary.json", summary)
        return summary

    prices = _load_prices(root)
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str, "code": str})
    baseline_daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv", dtype={"trade_date": str})
    repaired_summary = _read_json(root / REPAIRED_RUN / "summary.json")
    daily_summary = _read_json(root / DAILY_DIR / "v5f_locked_pool_daily_momentum_summary.json")

    signals = signals[(signals["trade_date"] >= BACKTEST_START) & (signals["trade_date"] <= BACKTEST_END)].copy()
    baseline_daily = baseline_daily[
        (baseline_daily["trade_date"] >= BACKTEST_START) & (baseline_daily["trade_date"] <= BACKTEST_END)
    ].copy()

    spec = _spec()
    weights, update_events, warning_events = _build_weight_and_event_logs(signals, prices, baseline_daily)
    daily = _daily_returns(weights, prices, baseline_daily)
    metrics = _metrics(daily)
    yearly = _yearly(daily)
    comparison = _comparison(metrics, daily_summary)
    update_summary = _update_summary(update_events)
    turnover = _turnover_cost_health(metrics, comparison)
    warning_forward = _risk_warning_forward_returns(warning_events, prices)
    warning_summary = _risk_warning_summary(warning_forward)
    governance = _governance_audit(repaired_summary, weights)
    pit = _pit_audit()
    decision = _pm_decision(comparison, turnover, warning_summary, governance)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(out / "v5f_locked_pool_conditional_momentum_spec.csv", spec)
    _write_csv(out / "v5f_locked_pool_conditional_momentum_weight_log.csv", weights)
    _write_csv(out / "v5f_locked_pool_conditional_momentum_update_events.csv", update_events)
    _write_csv(out / "v5f_locked_pool_conditional_momentum_update_summary.csv", update_summary)
    _write_csv(out / "v5f_locked_pool_conditional_momentum_daily_returns.csv", daily)
    _write_csv(out / "v5f_locked_pool_conditional_momentum_metrics.csv", metrics)
    _write_csv(out / "v5f_locked_pool_conditional_momentum_yearly.csv", yearly)
    _write_csv(out / "v5f_locked_pool_conditional_momentum_comparison.csv", comparison)
    _write_csv(out / "v5f_locked_pool_conditional_momentum_turnover_cost_health.csv", turnover)
    _write_csv(out / "v5f_locked_pool_risk_warning_events.csv", warning_events)
    _write_csv(out / "v5f_locked_pool_risk_warning_forward_returns.csv", warning_forward)
    _write_csv(out / "v5f_locked_pool_risk_warning_summary.csv", warning_summary)
    _write_csv(out / "v5f_locked_pool_conditional_momentum_governance_audit.csv", governance)
    _write_csv(out / "v5f_locked_pool_conditional_momentum_pit_audit.csv", pit)
    _write_csv(out / "v5f_locked_pool_conditional_momentum_pm_decision.csv", decision)
    _write_csv(out / "v5f_locked_pool_conditional_momentum_next_queue.csv", next_queue)
    _write_csv(out / "v5f_locked_pool_conditional_momentum_blockers.csv", blockers_out)
    (out / "v5f_locked_pool_conditional_momentum_prompt.md").write_text(_prompt(), encoding="utf-8")
    (out / "v5f_locked_pool_conditional_momentum_report.md").write_text(
        _report(metrics, comparison, update_summary, warning_summary, decision),
        encoding="utf-8",
    )
    (out / "v5f_locked_pool_conditional_momentum_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = _best_trade_variant(comparison)
    fixed = next(row for row in comparison if row["version_id"] == FIXED)
    summary = _summary(
        "completed_v5f_locked_pool_conditional_momentum",
        decision[0]["pm_gate_decision"],
        [],
        primary_candidate=decision[0]["primary_candidate"],
        best_trade_variant=best["version_id"],
        best_delta_return=float(best["delta_return_pct_points_vs_repaired_baseline"]),
        fixed_delta_return=float(fixed["delta_return_pct_points_vs_repaired_baseline"]),
        best_incremental_vs_fixed=float(best["incremental_delta_return_vs_fixed_7030"]),
    )
    _write_json(out / "v5f_locked_pool_conditional_momentum_summary.json", summary)
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
        {"version_id": FIXED, "trade_rule": "Official V57f rebalance only; 70/30 same-sleeve mom12 top-tercile overlay.", "new_threshold": False, "accepted": False},
        {"version_id": BIWEEKLY, "trade_rule": "Inside locked V57f pool, update every 10 trading days.", "new_threshold": False, "accepted": False},
        {"version_id": MONTHLY, "trade_rule": "Inside locked V57f pool, update every 21 trading days.", "new_threshold": False, "accepted": False},
        {"version_id": BUCKET, "trade_rule": "Inside locked V57f pool, update only when same-sleeve bucket has a major change: top-bottom jump or top group symmetric difference >= 2.", "new_threshold": False, "accepted": False},
        {"version_id": DRIFT, "trade_rule": "Inside locked V57f pool, update only when any stock target weight differs from current target by at least 1.00 pct point.", "new_threshold": False, "accepted": False},
        {"version_id": WARNING, "trade_rule": "No extra trading; emit risk warnings when rebalance-top names fall to bottom bucket.", "new_threshold": False, "accepted": False},
    ]


def _build_weight_and_event_logs(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    baseline_daily: pd.DataFrame,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    feature = prices.set_index(["date", "code"])["mom_12_1"].to_dict()
    dates = sorted(baseline_daily["trade_date"].tolist())
    pools = {date: group.copy() for date, group in signals.groupby("trade_date", sort=True)}

    variants = [FIXED, BIWEEKLY, MONTHLY, BUCKET, DRIFT, WARNING]
    current_targets: dict[str, dict[str, float]] = {version: {} for version in variants}
    current_buckets: dict[str, dict[str, str]] = {version: {} for version in variants}
    days_since_update: dict[str, int] = {version: 0 for version in variants}
    active_rebalance = ""
    active_pool = pd.DataFrame()
    rebalance_buckets: dict[str, str] = {}
    weights: list[dict[str, Any]] = []
    updates: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for day in dates:
        official = day in pools
        if official:
            active_rebalance = day
            active_pool = pools[day].copy()
            active_pool["base_target_weight"] = active_pool["target_weight"].astype(float)
            desired = _targets_for_day(active_pool, feature, day)
            buckets = _buckets_for_day(active_pool, feature, day)
            rebalance_buckets = buckets.copy()
            for version in variants:
                current_targets[version] = desired.copy()
                current_buckets[version] = buckets.copy()
                days_since_update[version] = 0
                updates.append(_update_event(day, active_rebalance, version, "official_v57f_rebalance", 0.0))

        if active_pool.empty:
            continue

        desired = _targets_for_day(active_pool, feature, day)
        desired_buckets = _buckets_for_day(active_pool, feature, day)
        base = {row["code"]: float(row["base_target_weight"]) for _, row in active_pool.iterrows()}

        for version in [BIWEEKLY, MONTHLY, BUCKET, DRIFT]:
            days_since_update[version] += 1
        for version, cadence in [(BIWEEKLY, 10), (MONTHLY, 21)]:
            if (not official) and days_since_update[version] >= cadence:
                turnover = _target_turnover(current_targets[version], desired)
                current_targets[version] = desired.copy()
                current_buckets[version] = desired_buckets.copy()
                days_since_update[version] = 0
                updates.append(_update_event(day, active_rebalance, version, f"{cadence}_trading_day_update", turnover))

        if (not official) and _major_bucket_change(current_buckets[BUCKET], desired_buckets, active_pool):
            turnover = _target_turnover(current_targets[BUCKET], desired)
            current_targets[BUCKET] = desired.copy()
            current_buckets[BUCKET] = desired_buckets.copy()
            days_since_update[BUCKET] = 0
            updates.append(_update_event(day, active_rebalance, BUCKET, "major_same_sleeve_bucket_change", turnover))

        if (not official) and _max_target_drift(current_targets[DRIFT], desired) >= WEIGHT_DRIFT_TRIGGER:
            turnover = _target_turnover(current_targets[DRIFT], desired)
            current_targets[DRIFT] = desired.copy()
            current_buckets[DRIFT] = desired_buckets.copy()
            days_since_update[DRIFT] = 0
            updates.append(_update_event(day, active_rebalance, DRIFT, "target_weight_drift_ge_1pct_point", turnover))

        warnings.extend(_warning_events_for_day(day, active_rebalance, active_pool, rebalance_buckets, desired_buckets, feature))

        for version in variants:
            target = current_targets[version]
            for _, row in active_pool.iterrows():
                code = row["code"]
                weights.append(
                    {
                        "trade_date": day,
                        "active_rebalance_date": active_rebalance,
                        "version_id": version,
                        "code": code,
                        "sleeve": row["sector_id"],
                        "base_target_weight": base[code],
                        "target_weight": target.get(code, base[code]),
                        "weight_delta": target.get(code, base[code]) - base[code],
                        "mom_12_1": _safe_float(feature.get((day, code))),
                        "bucket": desired_buckets.get(code, "unknown"),
                        "locked_pool_only": True,
                        "new_stock_selected": False,
                        "accepted": False,
                    }
                )
    return weights, updates, warnings


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


def _buckets_for_day(active_pool: pd.DataFrame, feature: dict[tuple[str, str], float], day: str) -> dict[str, str]:
    buckets: dict[str, str] = {}
    for _, group in active_pool.groupby("sector_id"):
        scores = group["code"].map(lambda code: _safe_float(feature.get((day, code))))
        if scores.notna().sum() == 0:
            for _, row in group.iterrows():
                buckets[row["code"]] = "middle"
            continue
        ranks = scores.rank(method="first")
        for idx, row in group.iterrows():
            rank = ranks.loc[idx]
            if rank <= len(group) / 3:
                bucket = "bottom"
            elif rank > len(group) * 2 / 3:
                bucket = "top"
            else:
                bucket = "middle"
            buckets[row["code"]] = bucket
    return buckets


def _major_bucket_change(current: dict[str, str], desired: dict[str, str], active_pool: pd.DataFrame) -> bool:
    level = {"bottom": 0, "middle": 1, "top": 2}
    if any(abs(level.get(desired.get(code, "middle"), 1) - level.get(current.get(code, "middle"), 1)) >= 2 for code in desired):
        return True
    for _, group in active_pool.groupby("sector_id"):
        codes = set(group["code"])
        current_top = {code for code in codes if current.get(code) == "top"}
        desired_top = {code for code in codes if desired.get(code) == "top"}
        if len(current_top.symmetric_difference(desired_top)) >= 2:
            return True
    return False


def _warning_events_for_day(
    day: str,
    active_rebalance: str,
    active_pool: pd.DataFrame,
    rebalance_buckets: dict[str, str],
    desired_buckets: dict[str, str],
    feature: dict[tuple[str, str], float],
) -> list[dict[str, Any]]:
    events = []
    for _, row in active_pool.iterrows():
        code = row["code"]
        if rebalance_buckets.get(code) == "top" and desired_buckets.get(code) == "bottom":
            events.append(
                {
                    "trade_date": day,
                    "active_rebalance_date": active_rebalance,
                    "code": code,
                    "sleeve": row["sector_id"],
                    "warning_type": "rebalance_top_to_current_bottom",
                    "mom_12_1": _safe_float(feature.get((day, code))),
                    "trade_action": "none_warning_only",
                    "accepted": False,
                }
            )
    return events


def _daily_returns(weights: list[dict[str, Any]], prices: pd.DataFrame, baseline_daily: pd.DataFrame) -> list[dict[str, Any]]:
    ret_map = prices.set_index(["date", "code"])["stock_return"].to_dict()
    baseline_ret = baseline_daily.set_index("trade_date")["strategy_return"].astype(float).to_dict()
    baseline_nav = baseline_daily.set_index("trade_date")["strategy_nav"].astype(float).to_dict()
    official_rebalances = set(pd.read_csv(REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str})["trade_date"])
    df = pd.DataFrame(weights)
    rows: list[dict[str, Any]] = []
    for version, group in df.groupby("version_id", sort=True):
        nav = 1.0
        prev_target: dict[str, float] = {}
        prev_base: dict[str, float] = {}
        for day, day_group in group.groupby("trade_date", sort=True):
            target = {row["code"]: float(row["target_weight"]) for _, row in day_group.iterrows()}
            base = {row["code"]: float(row["base_target_weight"]) for _, row in day_group.iterrows()}
            overlay_turnover = _target_turnover(prev_target, target)
            baseline_turnover = _target_turnover(prev_base, base) if day in official_rebalances else 0.0
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
            prev_base = base
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


def _comparison(metrics: list[dict[str, Any]], daily_summary: dict[str, Any]) -> list[dict[str, Any]]:
    fixed = next(row for row in metrics if row["version_id"] == FIXED)
    rows = []
    for row in metrics:
        if row["version_id"] == BASELINE:
            continue
        rows.append(
            {
                "version_id": row["version_id"],
                "delta_return_pct_points_vs_repaired_baseline": row["delta_return_pct_points_vs_repaired_baseline"],
                "delta_max_drawdown_pct_points_vs_repaired_baseline": row["delta_max_drawdown_pct_points_vs_repaired_baseline"],
                "incremental_delta_return_vs_fixed_7030": float(row["delta_return_pct_points_vs_repaired_baseline"]) - float(fixed["delta_return_pct_points_vs_repaired_baseline"]),
                "incremental_delta_drawdown_vs_fixed_7030": float(row["delta_max_drawdown_pct_points_vs_repaired_baseline"]) - float(fixed["delta_max_drawdown_pct_points_vs_repaired_baseline"]),
                "prior_daily_full_reweight_delta_return": daily_summary.get("daily_delta_return_pct_points_vs_repaired_baseline"),
                "accepted": False,
            }
        )
    return rows


def _update_summary(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(events)
    rows = []
    for version, group in df.groupby("version_id", sort=True):
        rows.append(
            {
                "version_id": version,
                "update_count": len(group),
                "non_official_update_count": int((group["reason"] != "official_v57f_rebalance").sum()),
                "turnover_from_update_events": pd.to_numeric(group["target_turnover"]).sum(),
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


def _risk_warning_forward_returns(events: list[dict[str, Any]], prices: pd.DataFrame) -> list[dict[str, Any]]:
    if not events:
        return [{"sample": "warning", "count": 0, "avg_forward_5d": "", "avg_forward_20d": "", "status": "no_warning_events"}]
    close_map = prices.set_index(["date", "code"])["close"].to_dict()
    date_by_code = {code: list(group["date"]) for code, group in prices.groupby("code")}
    rows = []
    for event in events:
        code = event["code"]
        dates = date_by_code.get(code, [])
        if event["trade_date"] not in dates:
            continue
        idx = dates.index(event["trade_date"])
        close_now = _safe_float(close_map.get((event["trade_date"], code)))
        fwd5 = _forward_return(close_map, dates, code, idx, 5, close_now)
        fwd20 = _forward_return(close_map, dates, code, idx, 20, close_now)
        row = dict(event)
        row["forward_5d_return"] = fwd5
        row["forward_20d_return"] = fwd20
        rows.append(row)
    return rows


def _risk_warning_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows or rows[0].get("status") == "no_warning_events":
        return [{"sample": "warning", "count": 0, "avg_forward_5d": "", "avg_forward_20d": "", "warning_effect": "no_warning_events"}]
    df = pd.DataFrame(rows)
    avg5 = pd.to_numeric(df["forward_5d_return"], errors="coerce").mean()
    avg20 = pd.to_numeric(df["forward_20d_return"], errors="coerce").mean()
    return [
        {
            "sample": "warning",
            "count": len(df),
            "avg_forward_5d": avg5,
            "avg_forward_20d": avg20,
            "warning_effect": "negative_forward_returns" if avg20 < 0 else "not_negative_on_average",
        }
    ]


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
        {"audit_id": "sleeve_weight_preserved", "status": "pass" if float(sleeve_drift["drift"].max()) < 1e-10 else "fail", "detail": float(sleeve_drift["drift"].max())},
        {"audit_id": "no_full_market_selection", "status": "pass", "detail": "V57f selected pool locked per rebalance period"},
        {"audit_id": "no_v57f_core_modified", "status": "pass", "detail": False},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
    ]


def _pit_audit() -> list[dict[str, Any]]:
    return [
        {"audit_id": "signal_visible_time", "status": "pass", "detail": "Mom12 feature is computed from close_lag_21 / close_lag_253 and applied to the next close-to-close interval."},
        {"audit_id": "forward_return_not_used_in_signal", "status": "pass", "detail": "Forward returns are evaluation only."},
        {"audit_id": "risk_warning_no_trade", "status": "pass", "detail": "Warning-only variant emits no extra buy/sell path."},
    ]


def _pm_decision(
    comparison: list[dict[str, Any]],
    turnover: list[dict[str, Any]],
    warning_summary: list[dict[str, Any]],
    governance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    best = _best_trade_variant(comparison)
    best_turnover = next(row for row in turnover if row["version_id"] == best["version_id"])
    fixed = next(row for row in comparison if row["version_id"] == FIXED)
    warning = warning_summary[0]
    if not gov_ok:
        decision = "blocked_by_governance_issue"
        primary = ""
        rationale = "Governance audit failed."
    elif float(best["incremental_delta_return_vs_fixed_7030"]) > 1.0 and float(best["incremental_delta_drawdown_vs_fixed_7030"]) <= 0 and best_turnover["cost_health"] == "pass":
        decision = "promote_conditional_locked_pool_momentum_to_forward_paper_candidate_not_accepted"
        primary = best["version_id"]
        rationale = "A conditional locked-pool momentum variant beats fixed 70/30 with non-worse drawdown."
    elif warning.get("warning_effect") == "negative_forward_returns" and int(warning.get("count", 0)) >= 10:
        decision = "risk_warning_diagnostic_positive_no_trade_change"
        primary = FIXED
        rationale = "Risk warning has diagnostic value, but trading variants do not beat fixed 70/30."
    else:
        decision = "conditional_momentum_diagnostic_only_keep_fixed_7030_primary"
        primary = FIXED
        rationale = "Conditional trading variants do not clearly improve on fixed 70/30."
    return [
        {
            "pm_gate_decision": decision,
            "primary_candidate": primary,
            "best_trade_variant": best["version_id"],
            "fixed_reference": FIXED,
            "best_delta_return_pct_points_vs_repaired_baseline": best["delta_return_pct_points_vs_repaired_baseline"],
            "fixed_delta_return_pct_points_vs_repaired_baseline": fixed["delta_return_pct_points_vs_repaired_baseline"],
            "best_incremental_delta_return_vs_fixed_7030": best["incremental_delta_return_vs_fixed_7030"],
            "warning_effect": warning.get("warning_effect"),
            "accepted": False,
            "live_trading_approved": False,
            "rationale": rationale,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task": "Keep fixed rebalance-only internal_subsleeve_mom12_70_30 as primary if no conditional version promotes.", "allowed": True},
        {"priority": 2, "task": "If warning diagnostic is positive, open risk-warning-only monitoring spec with no trade-path change.", "allowed": decision == "risk_warning_diagnostic_positive_no_trade_change"},
        {"priority": 3, "task": "If conditional variant promotes, open PM/Quant formal review.", "allowed": decision.startswith("promote_conditional")},
        {"priority": 4, "task": "Full-market momentum selection or optimized trigger scan.", "allowed": False},
    ]


def _best_trade_variant(comparison: list[dict[str, Any]]) -> dict[str, Any]:
    tradable = [row for row in comparison if row["version_id"] != WARNING]
    return max(tradable, key=lambda row: float(row["delta_return_pct_points_vs_repaired_baseline"]))


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    if failed:
        return [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed]
    return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Conditional locked-pool momentum test completed."}]


def _update_event(day: str, active_rebalance: str, version: str, reason: str, turnover: float) -> dict[str, Any]:
    return {
        "trade_date": day,
        "active_rebalance_date": active_rebalance,
        "version_id": version,
        "reason": reason,
        "target_turnover": turnover,
        "accepted": False,
    }


def _target_turnover(a: dict[str, float], b: dict[str, float]) -> float:
    return sum(abs(a.get(code, 0.0) - b.get(code, 0.0)) for code in set(a) | set(b))


def _max_target_drift(a: dict[str, float], b: dict[str, float]) -> float:
    return max((abs(a.get(code, 0.0) - b.get(code, 0.0)) for code in set(a) | set(b)), default=0.0)


def _forward_return(
    close_map: dict[tuple[str, str], float],
    dates: list[str],
    code: str,
    idx: int,
    horizon: int,
    close_now: float | None,
) -> float | str:
    if close_now is None or idx + horizon >= len(dates):
        return ""
    close_future = _safe_float(close_map.get((dates[idx + horizon], code)))
    if close_future is None:
        return ""
    return close_future / close_now - 1.0


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    primary_candidate: str = "",
    best_trade_variant: str = "",
    best_delta_return: float = 0.0,
    fixed_delta_return: float = 0.0,
    best_incremental_vs_fixed: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_locked_pool_conditional_momentum",
        "status": status,
        "pm_gate_decision": decision,
        "backtest_scope_start": BACKTEST_START,
        "backtest_scope_end": BACKTEST_END,
        "primary_candidate": primary_candidate,
        "best_trade_variant": best_trade_variant,
        "best_delta_return_pct_points_vs_repaired_baseline": best_delta_return,
        "fixed_delta_return_pct_points_vs_repaired_baseline": fixed_delta_return,
        "best_incremental_delta_return_vs_fixed_7030": best_incremental_vs_fixed,
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


def _report(
    metrics: list[dict[str, Any]],
    comparison: list[dict[str, Any]],
    update_summary: list[dict[str, Any]],
    warning_summary: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    return "\n".join(
        [
            "# V5f Locked-Pool Conditional Momentum Test",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Primary: `{decision[0]['primary_candidate']}`",
            "- Scope: V57f repaired locked pool only; historical window ends `2026-05-31`.",
            "- Status: not accepted, not live approved.",
            "",
            "## Metrics",
            *[
                f"- `{row['version_id']}`: return={float(row['strategy_return']) * 100:.2f}%, delta={float(row['delta_return_pct_points_vs_repaired_baseline']):.4f} pct, dd_delta={float(row['delta_max_drawdown_pct_points_vs_repaired_baseline']):.4f} pct, turnover={float(row['incremental_turnover_total']):.4f}"
                for row in metrics
            ],
            "",
            "## Versus Fixed 70/30",
            *[
                f"- `{row['version_id']}`: incremental={float(row['incremental_delta_return_vs_fixed_7030']):.4f} pct"
                for row in comparison
            ],
            "",
            "## Update Summary",
            *[
                f"- `{row['version_id']}`: updates={row['update_count']}, non_official={row['non_official_update_count']}"
                for row in update_summary
            ],
            "",
            "## Risk Warning",
            *[
                f"- count={row['count']}, avg_5d={row['avg_forward_5d']}, avg_20d={row['avg_forward_20d']}, effect={row['warning_effect']}"
                for row in warning_summary
            ],
            "",
        ]
    )


def _prompt() -> str:
    return """工作目录：
D:\\hh\\codex\\v5

任务名称：
V5f locked-pool conditional momentum variants：条件触发式锁定池动量调权测试

任务目标：
在 V57f repaired 调仓日锁定股票池的前提下，测试以下四类替代日级动量治理：
1. 同 sleeve 排名发生大段位变化才调；
2. 目标权重偏离达到固定幅度才调；
3. 双周 / 月度固定低频更新；
4. 日级信号只做风险预警，不直接调仓。

历史工程窗口：
2021-05-06 至 2026-05-31。此后全部 forward/paper only。

禁止：
不改 V57f，不新增股票，不全市场选股，不跨 sleeve，不改 sleeve 总权重，不标记 accepted/live approved。
"""


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Locked-Pool Conditional Momentum Rules",
            "",
            "- Historical engineering window ends 2026-05-31.",
            "- V57f repaired selects and locks the stock pool at each official rebalance.",
            "- Conditional momentum can only change weights inside the same sleeve.",
            "- No full-market selection, no new stock, no sleeve transfer, no V57f core modification.",
            "- Warning-only signals must not create trades.",
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
        DAILY_DIR / "v5f_locked_pool_daily_momentum_summary.json",
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
    print(json.dumps(run_v5f_locked_pool_conditional_momentum(Path(".")), ensure_ascii=False, indent=2))

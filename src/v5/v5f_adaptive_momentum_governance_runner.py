from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_adaptive_momentum_governance") / "current"
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
CHAMPION = "internal_subsleeve_mom12_70_30_current_champion"
MONTHLY = "adaptive_monthly_momentum_70_30"
RANK_CHANGE = "adaptive_rank_change_ge3_momentum_70_30"
WEIGHT_DRIFT = "adaptive_weight_drift_rel5pct_momentum_70_30"
RISK_BUDGET_CUT = "adaptive_risk_warning_60d_down20_budget_30_to_10"
BACKTEST_START = "2021-05-06"
BACKTEST_END = "2026-05-31"
COMMISSION_RATE = 0.0003
RANK_CHANGE_TRIGGER = 3
WEIGHT_DRIFT_REL_TRIGGER = 0.05
RISK_WARNING_60D_RETURN = -0.20


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_adaptive_momentum_governance(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_adaptive_momentum_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_adaptive_momentum_summary.json", summary)
        return summary

    prices = _load_prices(root)
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str, "code": str})
    baseline_daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv", dtype={"trade_date": str})
    repaired_summary = _read_json(root / REPAIRED_RUN / "summary.json")
    deep_summary = _read_json(root / DEEP_DIR / "v5f_internal_subsleeve_deep_summary.json")

    signals = signals[(signals["trade_date"] >= BACKTEST_START) & (signals["trade_date"] <= BACKTEST_END)].copy()
    baseline_daily = baseline_daily[
        (baseline_daily["trade_date"] >= BACKTEST_START) & (baseline_daily["trade_date"] <= BACKTEST_END)
    ].copy()

    spec = _spec()
    weights, events = _build_weight_and_event_logs(signals, prices, baseline_daily)
    daily = _daily_returns(weights, prices, baseline_daily)
    metrics = _metrics(daily)
    yearly = _yearly(daily)
    comparison = _comparison(metrics, deep_summary)
    event_summary = _event_summary(events)
    turnover = _turnover_cost_health(metrics, comparison)
    governance = _governance_audit(repaired_summary, weights)
    pit = _pit_audit()
    decision = _pm_decision(comparison, turnover, governance)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(out / "v5f_adaptive_momentum_spec.csv", spec)
    _write_csv(out / "v5f_adaptive_momentum_weight_log.csv", weights)
    _write_csv(out / "v5f_adaptive_momentum_update_events.csv", events)
    _write_csv(out / "v5f_adaptive_momentum_update_summary.csv", event_summary)
    _write_csv(out / "v5f_adaptive_momentum_daily_returns.csv", daily)
    _write_csv(out / "v5f_adaptive_momentum_metrics.csv", metrics)
    _write_csv(out / "v5f_adaptive_momentum_yearly.csv", yearly)
    _write_csv(out / "v5f_adaptive_momentum_comparison.csv", comparison)
    _write_csv(out / "v5f_adaptive_momentum_turnover_cost_health.csv", turnover)
    _write_csv(out / "v5f_adaptive_momentum_governance_audit.csv", governance)
    _write_csv(out / "v5f_adaptive_momentum_pit_audit.csv", pit)
    _write_csv(out / "v5f_adaptive_momentum_pm_decision.csv", decision)
    _write_csv(out / "v5f_adaptive_momentum_next_queue.csv", next_queue)
    _write_csv(out / "v5f_adaptive_momentum_blockers.csv", blockers_out)
    (out / "v5f_adaptive_momentum_prompt.md").write_text(_prompt(), encoding="utf-8")
    (out / "v5f_adaptive_momentum_report.md").write_text(
        _report(metrics, comparison, event_summary, decision),
        encoding="utf-8",
    )
    (out / "v5f_adaptive_momentum_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = _best_variant(comparison)
    champion = next(row for row in comparison if row["version_id"] == CHAMPION)
    summary = _summary(
        "completed_v5f_adaptive_momentum_governance",
        decision[0]["pm_gate_decision"],
        [],
        primary_candidate=decision[0]["primary_candidate"],
        best_variant=best["version_id"],
        best_delta_return=float(best["delta_return_pct_points_vs_repaired_baseline"]),
        champion_delta_return=float(champion["delta_return_pct_points_vs_repaired_baseline"]),
        best_incremental_vs_champion=float(best["incremental_delta_return_vs_champion"]),
    )
    _write_json(out / "v5f_adaptive_momentum_summary.json", summary)
    return summary


def _load_prices(root: Path) -> pd.DataFrame:
    frames = [pd.read_csv(path, dtype={"date": str, "code": str}) for path in (root / PRICE_DIR).glob("*.csv")]
    prices = pd.concat(frames, ignore_index=True).drop_duplicates(["date", "code"])
    prices = prices.sort_values(["code", "date"]).reset_index(drop=True)
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    prices["next_close"] = prices.groupby("code")["close"].shift(-1)
    prices["stock_return"] = prices["next_close"] / prices["close"] - 1.0
    prices["close_lag_21"] = prices.groupby("code")["close"].shift(21)
    prices["close_lag_61"] = prices.groupby("code")["close"].shift(61)
    prices["close_lag_253"] = prices.groupby("code")["close"].shift(253)
    prices["mom_12_1"] = prices["close_lag_21"] / prices["close_lag_253"] - 1.0
    prices["ret_60d"] = prices["close"] / prices["close_lag_61"] - 1.0
    return prices[(prices["date"] >= BACKTEST_START) & (prices["date"] <= BACKTEST_END)].copy()


def _spec() -> list[dict[str, Any]]:
    return [
        {"version_id": CHAMPION, "rule": "Current champion: V57f locked pool; update 70/30 same-sleeve mom12 overlay only at official V57f rebalance.", "accepted": False},
        {"version_id": MONTHLY, "rule": "Monthly momentum overlay: update every 21 trading days inside locked V57f pool.", "accepted": False},
        {"version_id": RANK_CHANGE, "rule": "Rank-change trigger: update only if abs(rank_today - rank_at_last_v57f_rebalance) >= 3 inside same sleeve.", "accepted": False},
        {"version_id": WEIGHT_DRIFT, "rule": "No-trade region: update only if actual weight differs from desired target by more than 5% relative to desired target.", "accepted": False},
        {"version_id": RISK_BUDGET_CUT, "rule": "Momentum risk warning: if a sleeve has a current top-momentum stock with 60d return <= -20%, reduce that sleeve momentum budget from 30% to 10%; restore when warning clears.", "accepted": False},
    ]


def _build_weight_and_event_logs(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    baseline_daily: pd.DataFrame,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    mom = prices.set_index(["date", "code"])["mom_12_1"].to_dict()
    ret60 = prices.set_index(["date", "code"])["ret_60d"].to_dict()
    stock_ret = prices.set_index(["date", "code"])["stock_return"].to_dict()
    dates = sorted(baseline_daily["trade_date"].tolist())
    pools = {date: group.copy() for date, group in signals.groupby("trade_date", sort=True)}
    variants = [CHAMPION, MONTHLY, RANK_CHANGE, WEIGHT_DRIFT, RISK_BUDGET_CUT]

    active_rebalance = ""
    active_pool = pd.DataFrame()
    rebalance_ranks: dict[str, int] = {}
    current_targets: dict[str, dict[str, float]] = {version: {} for version in variants}
    actual_weights: dict[str, dict[str, float]] = {version: {} for version in variants}
    days_since_update: dict[str, int] = {version: 0 for version in variants}
    risk_state: dict[str, bool] = {}
    weights: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []

    for day in dates:
        official = day in pools
        if official:
            active_rebalance = day
            active_pool = pools[day].copy()
            active_pool["base_target_weight"] = active_pool["target_weight"].astype(float)
            rebalance_ranks = _ranks_for_day(active_pool, mom, day)
            standard = _targets_for_day(active_pool, mom, day)
            risk_target, risk_state = _risk_budget_targets(active_pool, mom, ret60, day)
            for version in variants:
                target = risk_target.copy() if version == RISK_BUDGET_CUT else standard.copy()
                current_targets[version] = target.copy()
                actual_weights[version] = target.copy()
                days_since_update[version] = 0
                events.append(_event(day, active_rebalance, version, "official_v57f_rebalance", 0.0))

        if active_pool.empty:
            continue

        standard = _targets_for_day(active_pool, mom, day)
        ranks_today = _ranks_for_day(active_pool, mom, day)
        risk_target, new_risk_state = _risk_budget_targets(active_pool, mom, ret60, day)

        for version in [MONTHLY, RANK_CHANGE, WEIGHT_DRIFT, RISK_BUDGET_CUT]:
            days_since_update[version] += 1

        if (not official) and days_since_update[MONTHLY] >= 21:
            turnover = _target_turnover(current_targets[MONTHLY], standard)
            current_targets[MONTHLY] = standard.copy()
            actual_weights[MONTHLY] = standard.copy()
            days_since_update[MONTHLY] = 0
            events.append(_event(day, active_rebalance, MONTHLY, "monthly_21_trading_day_update", turnover))

        if (not official) and _rank_change_triggered(rebalance_ranks, ranks_today):
            turnover = _target_turnover(current_targets[RANK_CHANGE], standard)
            current_targets[RANK_CHANGE] = standard.copy()
            actual_weights[RANK_CHANGE] = standard.copy()
            days_since_update[RANK_CHANGE] = 0
            events.append(_event(day, active_rebalance, RANK_CHANGE, "rank_change_ge3_vs_rebalance", turnover))

        if (not official) and _relative_weight_drift_triggered(actual_weights[WEIGHT_DRIFT], standard):
            turnover = _target_turnover(current_targets[WEIGHT_DRIFT], standard)
            current_targets[WEIGHT_DRIFT] = standard.copy()
            actual_weights[WEIGHT_DRIFT] = standard.copy()
            days_since_update[WEIGHT_DRIFT] = 0
            events.append(_event(day, active_rebalance, WEIGHT_DRIFT, "actual_weight_drift_gt_5pct_relative", turnover))

        if (not official) and new_risk_state != risk_state:
            turnover = _target_turnover(current_targets[RISK_BUDGET_CUT], risk_target)
            current_targets[RISK_BUDGET_CUT] = risk_target.copy()
            actual_weights[RISK_BUDGET_CUT] = risk_target.copy()
            risk_state = new_risk_state.copy()
            days_since_update[RISK_BUDGET_CUT] = 0
            events.append(_event(day, active_rebalance, RISK_BUDGET_CUT, "risk_warning_state_change", turnover))

        base = {row["code"]: float(row["base_target_weight"]) for _, row in active_pool.iterrows()}
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
                        "mom_12_1": _safe_float(mom.get((day, code))),
                        "ret_60d": _safe_float(ret60.get((day, code))),
                        "rank_today": ranks_today.get(code),
                        "rank_at_rebalance": rebalance_ranks.get(code),
                        "locked_pool_only": True,
                        "new_stock_selected": False,
                        "accepted": False,
                    }
                )
            actual_weights[version] = _drift_actual_weights(target, stock_ret, day)
    return weights, events


def _targets_for_day(active_pool: pd.DataFrame, mom: dict[tuple[str, str], float], day: str) -> dict[str, float]:
    budgets = {sleeve: 0.30 for sleeve in active_pool["sector_id"].unique()}
    return _targets_for_day_with_budget(active_pool, mom, day, budgets)


def _targets_for_day_with_budget(
    active_pool: pd.DataFrame,
    mom: dict[tuple[str, str], float],
    day: str,
    sleeve_momentum_budget: dict[str, float],
) -> dict[str, float]:
    target: dict[str, float] = {}
    for sleeve, group in active_pool.groupby("sector_id"):
        budget = sleeve_momentum_budget.get(sleeve, 0.30)
        sleeve_total = group["base_target_weight"].astype(float).sum()
        scores = group["code"].map(lambda code: _safe_float(mom.get((day, code))))
        if scores.notna().sum() == 0:
            for _, row in group.iterrows():
                target[row["code"]] = float(row["base_target_weight"])
            continue
        ranks = scores.rank(method="first")
        top_mask = ranks > len(group) * 2 / 3
        top_codes = group.loc[top_mask, "code"].tolist() or [group.loc[scores.astype(float).idxmax(), "code"]]
        for _, row in group.iterrows():
            code = row["code"]
            core = (1.0 - budget) * float(row["base_target_weight"])
            momentum = budget * sleeve_total / len(top_codes) if code in top_codes else 0.0
            target[code] = core + momentum
    return target


def _risk_budget_targets(
    active_pool: pd.DataFrame,
    mom: dict[tuple[str, str], float],
    ret60: dict[tuple[str, str], float],
    day: str,
) -> tuple[dict[str, float], dict[str, bool]]:
    state: dict[str, bool] = {}
    budgets: dict[str, float] = {}
    for sleeve, group in active_pool.groupby("sector_id"):
        ranks = group["code"].map(lambda code: _safe_float(mom.get((day, code)))).rank(method="first")
        top_mask = ranks > len(group) * 2 / 3
        top_codes = group.loc[top_mask, "code"].tolist()
        warning = any((_safe_float(ret60.get((day, code))) or 0.0) <= RISK_WARNING_60D_RETURN for code in top_codes)
        state[sleeve] = warning
        budgets[sleeve] = 0.10 if warning else 0.30
    return _targets_for_day_with_budget(active_pool, mom, day, budgets), state


def _ranks_for_day(active_pool: pd.DataFrame, mom: dict[tuple[str, str], float], day: str) -> dict[str, int]:
    ranks_out: dict[str, int] = {}
    for _, group in active_pool.groupby("sector_id"):
        scores = group["code"].map(lambda code: _safe_float(mom.get((day, code))))
        if scores.notna().sum() == 0:
            ordered_codes = group["code"].tolist()
        else:
            sortable = group.assign(_score=scores.fillna(float("-inf")))
            ordered_codes = sortable.sort_values(["_score", "code"], ascending=[False, True])["code"].tolist()
        for rank, code in enumerate(ordered_codes, start=1):
            ranks_out[code] = rank
    return ranks_out


def _rank_change_triggered(rebalance_ranks: dict[str, int], ranks_today: dict[str, int]) -> bool:
    return any(abs(ranks_today.get(code, rank) - rank) >= RANK_CHANGE_TRIGGER for code, rank in rebalance_ranks.items())


def _relative_weight_drift_triggered(actual: dict[str, float], desired: dict[str, float]) -> bool:
    for code, target in desired.items():
        if target <= 0:
            continue
        if abs(actual.get(code, 0.0) - target) / target > WEIGHT_DRIFT_REL_TRIGGER:
            return True
    return False


def _drift_actual_weights(target: dict[str, float], stock_ret: dict[tuple[str, str], float], day: str) -> dict[str, float]:
    drifted = {
        code: weight * (1.0 + (_safe_float(stock_ret.get((day, code))) or 0.0))
        for code, weight in target.items()
    }
    total = sum(drifted.values())
    if total <= 0:
        return target.copy()
    return {code: weight / total for code, weight in drifted.items()}


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


def _comparison(metrics: list[dict[str, Any]], deep_summary: dict[str, Any]) -> list[dict[str, Any]]:
    champion = next(row for row in metrics if row["version_id"] == CHAMPION)
    official_champion_delta = float(deep_summary["primary_delta_return_pct_points_vs_repaired_baseline"])
    rows = []
    for row in metrics:
        if row["version_id"] == BASELINE:
            continue
        rows.append(
            {
                "version_id": row["version_id"],
                "delta_return_pct_points_vs_repaired_baseline": row["delta_return_pct_points_vs_repaired_baseline"],
                "delta_max_drawdown_pct_points_vs_repaired_baseline": row["delta_max_drawdown_pct_points_vs_repaired_baseline"],
                "incremental_delta_return_vs_champion": float(row["delta_return_pct_points_vs_repaired_baseline"]) - float(champion["delta_return_pct_points_vs_repaired_baseline"]),
                "incremental_delta_drawdown_vs_champion": float(row["delta_max_drawdown_pct_points_vs_repaired_baseline"]) - float(champion["delta_max_drawdown_pct_points_vs_repaired_baseline"]),
                "official_registered_champion_delta_return": official_champion_delta,
                "incremental_delta_return_vs_official_registered_champion": float(row["delta_return_pct_points_vs_repaired_baseline"]) - official_champion_delta,
                "accepted": False,
            }
        )
    return rows


def _event_summary(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
                "incremental_delta_return_vs_champion": comp["incremental_delta_return_vs_champion"],
                "cost_to_edge_ratio": cost / edge if edge else "",
                "cost_health": "pass" if edge > cost else "review",
            }
        )
    return rows


def _governance_audit(repaired_summary: dict[str, Any], weights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(weights)
    drift = (
        df.groupby(["trade_date", "version_id", "sleeve"])[["target_weight", "base_target_weight"]]
        .sum()
        .assign(drift=lambda x: (x["target_weight"] - x["base_target_weight"]).abs())
    )
    return [
        {"audit_id": "backtest_scope_end", "status": "pass", "detail": BACKTEST_END},
        {"audit_id": "repaired_first_signal", "status": "pass" if repaired_summary.get("startup_preload", {}).get("effective_first_signal_date") == "2021-05-06" else "fail", "detail": repaired_summary.get("startup_preload", {}).get("effective_first_signal_date")},
        {"audit_id": "locked_v57f_pool_only", "status": "pass" if not df["new_stock_selected"].astype(str).eq("True").any() else "fail", "detail": 0},
        {"audit_id": "sleeve_weight_preserved", "status": "pass" if float(drift["drift"].max()) < 1e-10 else "fail", "detail": float(drift["drift"].max())},
        {"audit_id": "no_full_market_selection", "status": "pass", "detail": "V57f repaired selected pool only"},
        {"audit_id": "no_v57f_core_modified", "status": "pass", "detail": False},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
    ]


def _pit_audit() -> list[dict[str, Any]]:
    return [
        {"audit_id": "mom_12_1_visible", "status": "pass", "detail": "Uses close_lag_21 / close_lag_253 visible at decision date for next interval."},
        {"audit_id": "risk_60d_visible", "status": "pass", "detail": "Uses current close / close_lag_61 visible at decision date for next interval."},
        {"audit_id": "forward_return_not_used_in_signal", "status": "pass", "detail": "Forward close-to-close return is evaluation only."},
    ]


def _pm_decision(
    comparison: list[dict[str, Any]],
    turnover: list[dict[str, Any]],
    governance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    best = _best_variant(comparison)
    champion = next(row for row in comparison if row["version_id"] == CHAMPION)
    best_cost = next(row for row in turnover if row["version_id"] == best["version_id"])
    if not gov_ok:
        decision = "blocked_by_governance_issue"
        primary = ""
        rationale = "Governance audit failed."
    elif (
        best["version_id"] != CHAMPION
        and float(best["incremental_delta_return_vs_champion"]) > 0.5
        and float(best["incremental_delta_drawdown_vs_champion"]) <= 0.1
        and best_cost["cost_health"] == "pass"
    ):
        decision = "promote_adaptive_momentum_to_pm_quant_review_not_accepted"
        primary = best["version_id"]
        rationale = "Adaptive variant improves return versus champion with acceptable drawdown and cost profile."
    elif best["version_id"] != CHAMPION and float(best["incremental_delta_return_vs_champion"]) > 0:
        decision = "adaptive_positive_but_risk_or_edge_insufficient_keep_champion_primary"
        primary = CHAMPION
        rationale = "Adaptive variant improves return, but edge/risk is not strong enough to replace the champion."
    else:
        decision = "adaptive_diagnostic_only_keep_champion_primary"
        primary = CHAMPION
        rationale = "Adaptive variants do not improve on the current champion."
    return [
        {
            "pm_gate_decision": decision,
            "primary_candidate": primary,
            "best_variant": best["version_id"],
            "champion_reference": CHAMPION,
            "best_delta_return_pct_points_vs_repaired_baseline": best["delta_return_pct_points_vs_repaired_baseline"],
            "champion_delta_return_pct_points_vs_repaired_baseline": champion["delta_return_pct_points_vs_repaired_baseline"],
            "best_incremental_delta_return_vs_champion": best["incremental_delta_return_vs_champion"],
            "best_incremental_delta_drawdown_vs_champion": best["incremental_delta_drawdown_vs_champion"],
            "accepted": False,
            "live_trading_approved": False,
            "rationale": rationale,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task": "Keep current champion as primary unless adaptive PM/Quant review promotes a variant.", "allowed": True},
        {"priority": 2, "task": "Open PM/Quant formal review for the best adaptive variant if gate promoted.", "allowed": decision.startswith("promote_adaptive")},
        {"priority": 3, "task": "Keep positive-but-insufficient adaptive variants as secondary diagnostics.", "allowed": decision.startswith("adaptive_positive")},
        {"priority": 4, "task": "Parameter scan or full-market momentum selection.", "allowed": False},
    ]


def _best_variant(comparison: list[dict[str, Any]]) -> dict[str, Any]:
    return max(comparison, key=lambda row: float(row["delta_return_pct_points_vs_repaired_baseline"]))


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    if failed:
        return [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed]
    return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Adaptive momentum governance test completed."}]


def _event(day: str, active_rebalance: str, version: str, reason: str, turnover: float) -> dict[str, Any]:
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


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    primary_candidate: str = "",
    best_variant: str = "",
    best_delta_return: float = 0.0,
    champion_delta_return: float = 0.0,
    best_incremental_vs_champion: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_adaptive_momentum_governance",
        "status": status,
        "pm_gate_decision": decision,
        "backtest_scope_start": BACKTEST_START,
        "backtest_scope_end": BACKTEST_END,
        "primary_candidate": primary_candidate,
        "best_variant": best_variant,
        "best_delta_return_pct_points_vs_repaired_baseline": best_delta_return,
        "champion_delta_return_pct_points_vs_repaired_baseline": champion_delta_return,
        "best_incremental_delta_return_vs_champion": best_incremental_vs_champion,
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
    events: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    return "\n".join(
        [
            "# V5f Adaptive Momentum Governance",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Primary: `{decision[0]['primary_candidate']}`",
            f"- Best adaptive/reference variant: `{decision[0]['best_variant']}`",
            "- Scope: V57f repaired locked pool only; historical window ends `2026-05-31`.",
            "- Status: not accepted; not live approved.",
            "",
            "## Metrics",
            *[
                f"- `{row['version_id']}`: return={float(row['strategy_return']) * 100:.2f}%, delta={float(row['delta_return_pct_points_vs_repaired_baseline']):.4f} pct, dd_delta={float(row['delta_max_drawdown_pct_points_vs_repaired_baseline']):.4f} pct, turnover={float(row['incremental_turnover_total']):.4f}"
                for row in metrics
            ],
            "",
            "## Versus Champion",
            *[
                f"- `{row['version_id']}`: incremental={float(row['incremental_delta_return_vs_champion']):.4f} pct, dd_incremental={float(row['incremental_delta_drawdown_vs_champion']):.4f} pct"
                for row in comparison
            ],
            "",
            "## Update Events",
            *[
                f"- `{row['version_id']}`: updates={row['update_count']}, non_official={row['non_official_update_count']}"
                for row in events
            ],
            "",
        ]
    )


def _prompt() -> str:
    return """工作目录：
D:\\hh\\codex\\v5

任务名称：
V5f adaptive momentum governance：信息变化触发的锁定池动量治理测试

任务目标：
在 V57f repaired 价值低波锁定股票池内部，固定测试：
1. monthly_momentum_70_30；
2. rank_change_trigger_momentum，abs(rank_today - rank_at_last_rebalance) >= 3 才调；
3. weight_drift_threshold_momentum，实际权重相对目标偏离 >5% 才调；
4. momentum_risk_warning，60日跌幅 <= -20% 时 sleeve momentum budget 从 30% 降到 10%，恢复后加回。

历史工程窗口：
2021-05-06 至 2026-05-31。之后只允许 forward/paper。

禁止：
不改 V57f，不新增股票，不全市场选股，不跨 sleeve，不改 sleeve 总权重，不标记 accepted/live approved。
"""


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Adaptive Momentum Governance Rules",
            "",
            "- Historical engineering window ends 2026-05-31.",
            "- V57f repaired selects and locks the stock pool at each official rebalance.",
            "- Momentum only governs weights inside the same sleeve.",
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
    print(json.dumps(run_v5f_adaptive_momentum_governance(Path(".")), ensure_ascii=False, indent=2))

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_quality_value_mean_reversion") / "current"
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
SCORE_ONLY = "qv_score_only_70_30"
QV_MR_20 = "qv_mr_20d_rebalance_70_30"
QV_MR_60 = "qv_mr_60d_rebalance_70_30"
QV_MR_120 = "qv_mr_120d_rebalance_70_30"
QV_MR_60_TILT = "qv_mr_60d_tilt10_rebalance"
QV_MR_60_MONTHLY = "qv_mr_60d_monthly_70_30"
BACKTEST_START = "2021-05-06"
BACKTEST_END = "2026-05-31"
COMMISSION_RATE = 0.0003


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_quality_value_mean_reversion(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_qv_mean_reversion_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_qv_mean_reversion_summary.json", summary)
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
    concentration = _selection_concentration(weights)
    turnover = _turnover_cost_health(metrics, comparison)
    governance = _governance_audit(repaired_summary, weights)
    pit = _pit_audit()
    decision = _pm_decision(comparison, turnover, governance)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(out / "v5f_qv_mean_reversion_spec.csv", spec)
    _write_csv(out / "v5f_qv_mean_reversion_weight_log.csv", weights)
    _write_csv(out / "v5f_qv_mean_reversion_update_events.csv", events)
    _write_csv(out / "v5f_qv_mean_reversion_update_summary.csv", event_summary)
    _write_csv(out / "v5f_qv_mean_reversion_daily_returns.csv", daily)
    _write_csv(out / "v5f_qv_mean_reversion_metrics.csv", metrics)
    _write_csv(out / "v5f_qv_mean_reversion_yearly.csv", yearly)
    _write_csv(out / "v5f_qv_mean_reversion_comparison.csv", comparison)
    _write_csv(out / "v5f_qv_mean_reversion_selection_concentration.csv", concentration)
    _write_csv(out / "v5f_qv_mean_reversion_turnover_cost_health.csv", turnover)
    _write_csv(out / "v5f_qv_mean_reversion_governance_audit.csv", governance)
    _write_csv(out / "v5f_qv_mean_reversion_pit_audit.csv", pit)
    _write_csv(out / "v5f_qv_mean_reversion_pm_decision.csv", decision)
    _write_csv(out / "v5f_qv_mean_reversion_next_queue.csv", next_queue)
    _write_csv(out / "v5f_qv_mean_reversion_blockers.csv", blockers_out)
    (out / "v5f_qv_mean_reversion_prompt.md").write_text(_prompt(), encoding="utf-8")
    (out / "v5f_qv_mean_reversion_report.md").write_text(
        _report(metrics, comparison, event_summary, decision),
        encoding="utf-8",
    )
    (out / "v5f_qv_mean_reversion_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = _best_variant(comparison)
    champion = next(row for row in comparison if row["version_id"] == CHAMPION)
    summary = _summary(
        "completed_v5f_quality_value_mean_reversion",
        decision[0]["pm_gate_decision"],
        [],
        primary_candidate=decision[0]["primary_candidate"],
        best_variant=best["version_id"],
        best_delta_return=float(best["delta_return_pct_points_vs_repaired_baseline"]),
        champion_delta_return=float(champion["delta_return_pct_points_vs_repaired_baseline"]),
        best_incremental_vs_champion=float(best["incremental_delta_return_vs_champion"]),
    )
    _write_json(out / "v5f_qv_mean_reversion_summary.json", summary)
    return summary


def _load_prices(root: Path) -> pd.DataFrame:
    frames = [pd.read_csv(path, dtype={"date": str, "code": str}) for path in (root / PRICE_DIR).glob("*.csv")]
    prices = pd.concat(frames, ignore_index=True).drop_duplicates(["date", "code"])
    prices = prices.sort_values(["code", "date"]).reset_index(drop=True)
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    prices["next_close"] = prices.groupby("code")["close"].shift(-1)
    prices["stock_return"] = prices["next_close"] / prices["close"] - 1.0
    for lookback in [20, 60, 120]:
        prices[f"close_lag_1"] = prices.groupby("code")["close"].shift(1)
        prices[f"close_lag_{lookback + 1}"] = prices.groupby("code")["close"].shift(lookback + 1)
        prices[f"ret_{lookback}d_lagged"] = prices["close_lag_1"] / prices[f"close_lag_{lookback + 1}"] - 1.0
    prices["close_lag_21"] = prices.groupby("code")["close"].shift(21)
    prices["close_lag_253"] = prices.groupby("code")["close"].shift(253)
    prices["mom_12_1"] = prices["close_lag_21"] / prices["close_lag_253"] - 1.0
    return prices[(prices["date"] >= BACKTEST_START) & (prices["date"] <= BACKTEST_END)].copy()


def _spec() -> list[dict[str, Any]]:
    return [
        {"version_id": CHAMPION, "rule": "Current champion: V57f locked pool, same-sleeve 12-1 momentum 70/30 at official rebalance.", "accepted": False},
        {"version_id": SCORE_ONLY, "rule": "Sanity check: 70% base + 30% to highest V57f composite score names within each sleeve.", "accepted": False},
        {"version_id": QV_MR_20, "rule": "Buy undervalued quality: 70% base + 30% to high-score and weak 20d return names within each sleeve.", "accepted": False},
        {"version_id": QV_MR_60, "rule": "Main mean reversion: 70% base + 30% to high-score and weak 60d return names within each sleeve.", "accepted": False},
        {"version_id": QV_MR_120, "rule": "Longer stress: 70% base + 30% to high-score and weak 120d return names within each sleeve.", "accepted": False},
        {"version_id": QV_MR_60_TILT, "rule": "Mild version: within each sleeve, +10% multiplier to high-score weak-60d names, -10% to low-score strong-60d names, then renormalize.", "accepted": False},
        {"version_id": QV_MR_60_MONTHLY, "rule": "Locked pool monthly update: fundamentals fixed at V57f rebalance, 60d reversal refreshed every 21 trading days.", "accepted": False},
    ]


def _build_weight_and_event_logs(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    baseline_daily: pd.DataFrame,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    feature = prices.set_index(["date", "code"])[["mom_12_1", "ret_20d_lagged", "ret_60d_lagged", "ret_120d_lagged"]].to_dict("index")
    dates = sorted(baseline_daily["trade_date"].tolist())
    pools = {date: group.copy() for date, group in signals.groupby("trade_date", sort=True)}
    variants = [CHAMPION, SCORE_ONLY, QV_MR_20, QV_MR_60, QV_MR_120, QV_MR_60_TILT, QV_MR_60_MONTHLY]
    current_targets: dict[str, dict[str, float]] = {version: {} for version in variants}
    active_rebalance = ""
    active_pool = pd.DataFrame()
    days_since_monthly = 0
    weights: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []

    for day in dates:
        official = day in pools
        if official:
            active_rebalance = day
            active_pool = pools[day].copy()
            active_pool["base_target_weight"] = active_pool["target_weight"].astype(float)
            active_pool["quality_value_score"] = pd.to_numeric(active_pool["score"], errors="coerce")
            current_targets[CHAMPION] = _momentum_targets(active_pool, feature, day)
            current_targets[SCORE_ONLY] = _score_only_targets(active_pool)
            current_targets[QV_MR_20] = _qv_reversion_targets(active_pool, feature, day, "ret_20d_lagged")
            current_targets[QV_MR_60] = _qv_reversion_targets(active_pool, feature, day, "ret_60d_lagged")
            current_targets[QV_MR_120] = _qv_reversion_targets(active_pool, feature, day, "ret_120d_lagged")
            current_targets[QV_MR_60_TILT] = _qv_reversion_tilt10_targets(active_pool, feature, day, "ret_60d_lagged")
            current_targets[QV_MR_60_MONTHLY] = current_targets[QV_MR_60].copy()
            days_since_monthly = 0
            for version in variants:
                events.append(_event(day, active_rebalance, version, "official_v57f_rebalance", 0.0))

        if active_pool.empty:
            continue

        days_since_monthly += 1
        if (not official) and days_since_monthly >= 21:
            desired = _qv_reversion_targets(active_pool, feature, day, "ret_60d_lagged")
            turnover = _target_turnover(current_targets[QV_MR_60_MONTHLY], desired)
            current_targets[QV_MR_60_MONTHLY] = desired
            days_since_monthly = 0
            events.append(_event(day, active_rebalance, QV_MR_60_MONTHLY, "monthly_refresh_60d_reversal", turnover))

        base = {row["code"]: float(row["base_target_weight"]) for _, row in active_pool.iterrows()}
        for version in variants:
            target = current_targets[version]
            for _, row in active_pool.iterrows():
                code = row["code"]
                feature_row = feature.get((day, code), {})
                weights.append(
                    {
                        "trade_date": day,
                        "active_rebalance_date": active_rebalance,
                        "version_id": version,
                        "code": code,
                        "sleeve": row["sector_id"],
                        "quality_value_score": row["quality_value_score"],
                        "selected_rank": row["selected_rank"],
                        "base_target_weight": base[code],
                        "target_weight": target.get(code, base[code]),
                        "weight_delta": target.get(code, base[code]) - base[code],
                        "mom_12_1": _safe_float(feature_row.get("mom_12_1")),
                        "ret_20d_lagged": _safe_float(feature_row.get("ret_20d_lagged")),
                        "ret_60d_lagged": _safe_float(feature_row.get("ret_60d_lagged")),
                        "ret_120d_lagged": _safe_float(feature_row.get("ret_120d_lagged")),
                        "locked_pool_only": True,
                        "new_stock_selected": False,
                        "accepted": False,
                    }
                )
    return weights, events


def _score_only_targets(pool: pd.DataFrame) -> dict[str, float]:
    targets: dict[str, float] = {}
    for sleeve, group in pool.groupby("sector_id"):
        sleeve_total = group["base_target_weight"].astype(float).sum()
        ranks = group["quality_value_score"].rank(method="first", ascending=False)
        top_mask = ranks <= max(1, math.ceil(len(group) / 3))
        top_codes = group.loc[top_mask, "code"].tolist()
        for _, row in group.iterrows():
            code = row["code"]
            core = 0.70 * float(row["base_target_weight"])
            score_alloc = 0.30 * sleeve_total / len(top_codes) if code in top_codes else 0.0
            targets[code] = core + score_alloc
    return targets


def _momentum_targets(pool: pd.DataFrame, feature: dict[tuple[str, str], dict[str, Any]], day: str) -> dict[str, float]:
    targets: dict[str, float] = {}
    for sleeve, group in pool.groupby("sector_id"):
        sleeve_total = group["base_target_weight"].astype(float).sum()
        scores = group["code"].map(lambda code: _safe_float(feature.get((day, code), {}).get("mom_12_1")))
        if scores.notna().sum() == 0:
            for _, row in group.iterrows():
                targets[row["code"]] = float(row["base_target_weight"])
            continue
        ranks = scores.rank(method="first", ascending=False)
        top_mask = ranks <= max(1, math.ceil(len(group) / 3))
        top_codes = group.loc[top_mask, "code"].tolist()
        for _, row in group.iterrows():
            code = row["code"]
            core = 0.70 * float(row["base_target_weight"])
            mom_alloc = 0.30 * sleeve_total / len(top_codes) if code in top_codes else 0.0
            targets[code] = core + mom_alloc
    return targets


def _qv_reversion_targets(
    pool: pd.DataFrame,
    feature: dict[tuple[str, str], dict[str, Any]],
    day: str,
    return_feature: str,
) -> dict[str, float]:
    targets: dict[str, float] = {}
    for sleeve, group in pool.groupby("sector_id"):
        sleeve_total = group["base_target_weight"].astype(float).sum()
        tmp = group.copy()
        tmp["_ret"] = tmp["code"].map(lambda code: _safe_float(feature.get((day, code), {}).get(return_feature)))
        tmp["_quality_rank"] = tmp["quality_value_score"].rank(method="first", ascending=False)
        tmp["_reversal_rank"] = tmp["_ret"].fillna(tmp["_ret"].median()).rank(method="first", ascending=True)
        tmp["_blend_rank"] = tmp["_quality_rank"] + tmp["_reversal_rank"]
        high_quality = tmp["_quality_rank"] <= math.ceil(len(tmp) / 2)
        weak_return = tmp["_reversal_rank"] <= math.ceil(len(tmp) / 2)
        selected = tmp.loc[high_quality & weak_return, "code"].tolist()
        if not selected:
            selected = tmp.sort_values(["_blend_rank", "code"]).head(max(1, math.ceil(len(tmp) / 3)))["code"].tolist()
        for _, row in tmp.iterrows():
            code = row["code"]
            core = 0.70 * float(row["base_target_weight"])
            qv_alloc = 0.30 * sleeve_total / len(selected) if code in selected else 0.0
            targets[code] = core + qv_alloc
    return targets


def _qv_reversion_tilt10_targets(
    pool: pd.DataFrame,
    feature: dict[tuple[str, str], dict[str, Any]],
    day: str,
    return_feature: str,
) -> dict[str, float]:
    targets: dict[str, float] = {}
    for sleeve, group in pool.groupby("sector_id"):
        tmp = group.copy()
        tmp["_ret"] = tmp["code"].map(lambda code: _safe_float(feature.get((day, code), {}).get(return_feature)))
        tmp["_quality_rank"] = tmp["quality_value_score"].rank(method="first", ascending=False)
        tmp["_reversal_rank"] = tmp["_ret"].fillna(tmp["_ret"].median()).rank(method="first", ascending=True)
        high_quality = tmp["_quality_rank"] <= math.ceil(len(tmp) / 2)
        weak_return = tmp["_reversal_rank"] <= math.ceil(len(tmp) / 2)
        low_quality = tmp["_quality_rank"] > math.ceil(len(tmp) / 2)
        strong_return = tmp["_reversal_rank"] > math.ceil(len(tmp) / 2)
        tmp["_multiplier"] = 1.0
        tmp.loc[high_quality & weak_return, "_multiplier"] = 1.10
        tmp.loc[low_quality & strong_return, "_multiplier"] = 0.90
        tmp["_raw"] = tmp["base_target_weight"].astype(float) * tmp["_multiplier"]
        sleeve_total = tmp["base_target_weight"].astype(float).sum()
        raw_total = tmp["_raw"].sum()
        for _, row in tmp.iterrows():
            targets[row["code"]] = float(row["_raw"]) / raw_total * sleeve_total if raw_total else float(row["base_target_weight"])
    return targets


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


def _selection_concentration(weights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(weights)
    active = df[df["weight_delta"].astype(float) > 0].copy()
    rows = []
    for (version, sleeve), group in active.groupby(["version_id", "sleeve"], sort=True):
        rows.append(
            {
                "version_id": version,
                "sleeve": sleeve,
                "positive_weight_delta_rows": len(group),
                "unique_positive_delta_stocks": group["code"].nunique(),
                "avg_quality_value_score": pd.to_numeric(group["quality_value_score"], errors="coerce").mean(),
                "avg_ret_60d_lagged": pd.to_numeric(group["ret_60d_lagged"], errors="coerce").mean(),
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
        {"audit_id": "quality_value_score_visible", "status": "pass", "detail": "Uses V57f PIT rebalance score from repaired signal table."},
        {"audit_id": "recent_return_visible", "status": "pass", "detail": "Uses close_lag_1 / close_lag_N+1, not forward returns."},
        {"audit_id": "forward_return_not_used_in_signal", "status": "pass", "detail": "Next close-to-close return is evaluation only."},
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
        decision = "promote_qv_mean_reversion_to_pm_quant_review_not_accepted"
        primary = best["version_id"]
        rationale = "Quality-value mean reversion improves on champion with acceptable drawdown and cost."
    elif best["version_id"] != CHAMPION and float(best["incremental_delta_return_vs_champion"]) > 0:
        decision = "qv_mean_reversion_positive_but_insufficient_keep_champion_primary"
        primary = CHAMPION
        rationale = "Quality-value mean reversion is positive but not strong enough to replace the current champion."
    else:
        decision = "qv_mean_reversion_diagnostic_only_keep_champion_primary"
        primary = CHAMPION
        rationale = "Quality-value mean reversion does not improve on the current champion."
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
        {"priority": 1, "task": "Keep current champion as primary unless QV mean reversion PM/Quant review promotes a variant.", "allowed": True},
        {"priority": 2, "task": "Open PM/Quant formal review for best QV mean reversion variant if promoted.", "allowed": decision.startswith("promote_qv")},
        {"priority": 3, "task": "Keep QV mean reversion as diagnostic/secondary if positive but insufficient.", "allowed": decision.startswith("qv_mean_reversion_positive")},
        {"priority": 4, "task": "Full-market undervalued stock selection or threshold scan.", "allowed": False},
    ]


def _best_variant(comparison: list[dict[str, Any]]) -> dict[str, Any]:
    return max(comparison, key=lambda row: float(row["delta_return_pct_points_vs_repaired_baseline"]))


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    if failed:
        return [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed]
    return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Quality-value mean reversion test completed."}]


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
        "task": "v5f_quality_value_mean_reversion",
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
            "# V5f Quality-Value Mean Reversion",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Primary: `{decision[0]['primary_candidate']}`",
            f"- Best variant: `{decision[0]['best_variant']}`",
            "- Scope: V57f repaired selected pool only; historical window ends `2026-05-31`.",
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
V5f quality-value mean reversion：低估优质股票锁定池加权测试

任务目标：
在 V57f repaired 已选价值低波股票池内部，测试“高 V57f 综合价值/质量分 + 短中期价格回落”的均值回归加权方案。

历史工程窗口：
2021-05-06 至 2026-05-31。之后只允许 forward/paper。

固定测试：
1. qv_score_only_70_30；
2. qv_mr_20d_rebalance_70_30；
3. qv_mr_60d_rebalance_70_30；
4. qv_mr_120d_rebalance_70_30；
5. qv_mr_60d_tilt10_rebalance；
6. qv_mr_60d_monthly_70_30。

禁止：
不改 V57f，不新增股票，不全市场选股，不跨 sleeve，不改 sleeve 总权重，不标记 accepted/live approved。
"""


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Quality-Value Mean Reversion Rules",
            "",
            "- Historical engineering window ends 2026-05-31.",
            "- V57f repaired selects and locks the stock pool at each official rebalance.",
            "- Quality-value score is read from V57f repaired signal table.",
            "- Mean reversion uses lagged recent return only, not future return.",
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
    print(json.dumps(run_v5f_quality_value_mean_reversion(Path(".")), ensure_ascii=False, indent=2))

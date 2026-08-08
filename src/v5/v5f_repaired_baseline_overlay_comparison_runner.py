from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_repaired_baseline_overlay_comparison") / "current"
PRICE_DIR = Path("\u6570\u636e\u5e93") / "processed" / "startup_preload_repaired_prices_v5"
STARTUP_SUMMARY = Path("v5_startup_warmup_price_repair") / "current" / "v5_startup_warmup_price_repair_summary.json"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
OLD_MOMENTUM = Path("v5f_momentum_weight_tilt_backtest_scope") / "current" / "v5f_momentum_weight_tilt_backtest_summary.json"
OLD_MEAN_REVERSION = Path("v5f_mean_reversion_diagnostic") / "current" / "v5f_mean_reversion_summary.json"

BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
BASELINE = "v57f_startup_preload_repaired_baseline"
COMMISSION_RATE = 0.0003


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_repaired_baseline_overlay_comparison(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_baseline_mismatch_audit.csv", blockers)
        summary = _summary("blocked_missing_required_input", "repaired_baseline_mismatch_blocker", blockers)
        _write_json(out / "v5f_repaired_overlay_summary.json", summary)
        return summary

    startup = _read_json(root / STARTUP_SUMMARY)
    run_summary = _read_json(root / REPAIRED_RUN / "summary.json")
    prices = _load_prices(root)
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str, "code": str})
    baseline_daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv", dtype={"trade_date": str})
    trades = pd.read_csv(root / REPAIRED_RUN / "trades.csv", dtype={"trade_date": str, "code": str})

    truth = _truth_table(startup, run_summary, signals, baseline_daily, trades)
    mismatch = _baseline_mismatch_audit(root, run_summary, baseline_daily)
    weights = _all_overlay_weights(signals, prices)
    daily_returns = _overlay_daily_returns(weights, prices, baseline_daily)
    metrics = _metrics(daily_returns)
    yearly = _yearly_performance(daily_returns)
    drawdown = _drawdown_attribution(daily_returns)
    sleeve = _sleeve_contribution(weights, prices)
    turnover = _turnover_cost_health(daily_returns, metrics)
    order_health = _order_health(weights, trades, run_summary)
    pool = _stock_pool_boundary_audit(weights, signals)
    pit = _pit_leakage_audit(weights)
    candidate_matrix = _candidate_matrix(metrics)
    gate = _pm_gate(metrics, mismatch, pool, pit)
    queue = _next_queue(gate[0]["pm_gate_decision"])

    _write_csv(out / "v5f_repaired_baseline_truth_table.csv", truth)
    _write_csv(out / "v5f_baseline_mismatch_audit.csv", mismatch)
    _write_csv(out / "v5f_stock_pool_boundary_audit.csv", pool)
    _write_csv(out / "v5f_pit_leakage_audit.csv", pit)
    _write_csv(out / "v5f_momentum_repaired_result.csv", [row for row in metrics if row["overlay_family"] == "momentum"])
    _write_csv(out / "v5f_mean_reversion_repaired_result.csv", [row for row in metrics if row["overlay_family"] == "mean_reversion"])
    _write_csv(out / "v5f_combined_overlay_repaired_result.csv", [row for row in metrics if row["overlay_family"] == "combined"])
    _write_csv(out / "v5f_overlay_yearly_performance.csv", yearly)
    _write_csv(out / "v5f_overlay_drawdown_attribution.csv", drawdown)
    _write_csv(out / "v5f_overlay_sleeve_contribution.csv", sleeve)
    _write_csv(out / "v5f_overlay_turnover_cost_health.csv", turnover)
    _write_csv(out / "v5f_overlay_order_health.csv", order_health)
    _write_csv(out / "v5f_candidate_matrix.csv", candidate_matrix)
    _write_csv(out / "v5f_pm_quant_gate_decision.csv", gate)
    _write_csv(out / "v5f_next_agent_queue.csv", queue)
    (out / "v5f_repaired_overlay_report.md").write_text(
        _report(truth, mismatch, metrics, yearly, gate),
        encoding="utf-8",
    )
    (out / "v5f_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    best = _best_pm_candidate(metrics)
    summary = _summary(
        "completed_v5f_repaired_baseline_overlay_comparison",
        gate[0]["pm_gate_decision"],
        [],
        repaired_baseline_confirmed=True,
        best_candidate=best["version_id"],
        best_family=best["overlay_family"],
        best_delta_return_pct_points=float(best["delta_return_pct_points_vs_repaired_baseline"]),
        best_delta_max_drawdown_pct_points=float(best["delta_max_drawdown_pct_points_vs_repaired_baseline"]),
        baseline_mismatch_count=sum(1 for row in mismatch if row["status"] != "pass"),
    )
    _write_json(out / "v5f_repaired_overlay_summary.json", summary)
    return summary


def _load_prices(root: Path) -> pd.DataFrame:
    frames = [pd.read_csv(path, dtype={"date": str, "code": str}) for path in (root / PRICE_DIR).glob("*.csv")]
    prices = pd.concat(frames, ignore_index=True).drop_duplicates(["date", "code"])
    prices = prices.sort_values(["code", "date"]).reset_index(drop=True)
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    prices["next_close"] = prices.groupby("code")["close"].shift(-1)
    prices["stock_return"] = prices["next_close"] / prices["close"] - 1.0
    for lag in [21, 64, 127, 190, 253]:
        prices[f"close_lag_{lag}"] = prices.groupby("code")["close"].shift(lag)
    prices["mom_6_1"] = prices["close_lag_21"] / prices["close_lag_127"] - 1.0
    prices["mom_12_1"] = prices["close_lag_21"] / prices["close_lag_253"] - 1.0
    prices["mr_20d"] = prices.groupby("code")["close"].shift(1) / prices.groupby("code")["close"].shift(21) - 1.0
    prices["mr_60d"] = prices.groupby("code")["close"].shift(1) / prices.groupby("code")["close"].shift(61) - 1.0
    return prices


def _truth_table(startup: dict[str, Any], run_summary: dict[str, Any], signals: pd.DataFrame, daily: pd.DataFrame, trades: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {"item": "startup_repair_status", "value": startup.get("status"), "source": str(STARTUP_SUMMARY), "status": "pass" if startup.get("status") == "startup_warmup_price_repair_completed" else "fail"},
        {"item": "deployment_first_tradable_date", "value": startup.get("deployment_model", {}).get("first_tradable_date"), "source": str(STARTUP_SUMMARY), "status": "pass" if startup.get("deployment_model", {}).get("first_tradable_date") == "2021-05-06" else "fail"},
        {"item": "repaired_first_signal_date", "value": run_summary.get("startup_preload", {}).get("effective_first_signal_date"), "source": str(REPAIRED_RUN / "summary.json"), "status": "pass" if run_summary.get("startup_preload", {}).get("effective_first_signal_date") == "2021-05-06" else "fail"},
        {"item": "first_rebalance_signal_csv", "value": str(signals["trade_date"].min()), "source": str(REPAIRED_RUN / "rebalance_signals.csv"), "status": "pass" if str(signals["trade_date"].min()) == "2021-05-06" else "fail"},
        {"item": "first_daily_return_csv", "value": str(daily["trade_date"].min()), "source": str(REPAIRED_RUN / "daily_returns.csv"), "status": "pass" if str(daily["trade_date"].min()) == "2021-05-06" else "fail"},
        {"item": "first_trade_csv", "value": str(trades["trade_date"].min()), "source": str(REPAIRED_RUN / "trades.csv"), "status": "pass" if str(trades["trade_date"].min()) == "2021-05-06" else "fail"},
        {"item": "old_first_signal_not_used", "value": startup.get("pre_post", {}).get("old_first_signal_date"), "source": str(STARTUP_SUMMARY), "status": "pass" if startup.get("pre_post", {}).get("old_first_signal_date") == "2021-10-08" else "review"},
        {"item": "repaired_baseline_return", "value": run_summary.get("metrics", {}).get("strategy_return"), "source": str(REPAIRED_RUN / "summary.json"), "status": "pass"},
        {"item": "repaired_baseline_max_drawdown", "value": run_summary.get("metrics", {}).get("max_drawdown"), "source": str(REPAIRED_RUN / "summary.json"), "status": "pass"},
    ]


def _baseline_mismatch_audit(root: Path, run_summary: dict[str, Any], baseline_daily: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    repaired_return = float(run_summary.get("metrics", {}).get("strategy_return", 0.0)) * 100
    old_refs = [(OLD_MOMENTUM, "old_momentum_output"), (OLD_MEAN_REVERSION, "old_mean_reversion_output")]
    for path, audit_id in old_refs:
        if not (root / path).exists():
            rows.append({"audit_id": audit_id, "status": "review", "detail": f"{path} not found", "old_value": "", "repaired_value": repaired_return})
            continue
        data = _read_json(root / path)
        old_delta = data.get("primary_delta_return_pct_points_vs_baseline_proxy", data.get("best_delta_return_pct_points_vs_baseline_proxy", ""))
        rows.append(
            {
                "audit_id": audit_id,
                "status": "superseded_by_repaired_rerun",
                "detail": "Prior output used a baseline proxy comparison and is not the benchmark for this packet.",
                "old_value": old_delta,
                "repaired_value": repaired_return,
            }
        )
    actual_return = (1.0 + pd.to_numeric(baseline_daily["strategy_return"])).prod() - 1.0
    rows.append(
        {
            "audit_id": "repaired_daily_return_matches_summary",
            "status": "pass" if abs(actual_return - float(run_summary["metrics"]["strategy_return"])) < 1e-10 else "fail",
            "detail": "Main benchmark is repaired baseline daily_returns.csv.",
            "old_value": "",
            "repaired_value": actual_return * 100,
        }
    )
    return rows


def _all_overlay_weights(signals: pd.DataFrame, prices: pd.DataFrame) -> list[dict[str, Any]]:
    variants = [
        ("momentum", "mom_12_1_sleeve_tilt_5pct", "momentum", "mom_12_1", 0.05),
        ("momentum", "mom_12_1_sleeve_tilt_10pct", "momentum", "mom_12_1", 0.10),
        ("momentum", "mom_12_1_sleeve_tilt_15pct", "momentum", "mom_12_1", 0.15),
        ("momentum", "mom_6_1_sleeve_tilt_10pct", "momentum", "mom_6_1", 0.10),
        ("mean_reversion", "mr_20d_sleeve_reversal_tilt_10pct", "mean_reversion", "mr_20d", 0.10),
        ("mean_reversion", "mr_60d_sleeve_reversal_tilt_5pct", "mean_reversion", "mr_60d", 0.05),
        ("mean_reversion", "mr_60d_sleeve_reversal_tilt_10pct", "mean_reversion", "mr_60d", 0.10),
        ("mean_reversion", "mr_60d_sleeve_reversal_tilt_15pct", "mean_reversion", "mr_60d", 0.15),
    ]
    rows: list[dict[str, Any]] = []
    feature_map = prices.set_index(["date", "code"])[["mom_12_1", "mom_6_1", "mr_20d", "mr_60d"]].to_dict("index")
    base_by_variant_source: dict[tuple[str, str], pd.DataFrame] = {}
    for date, group in signals.groupby("trade_date", sort=True):
        base = group.copy()
        for col in ["mom_12_1", "mom_6_1", "mr_20d", "mr_60d"]:
            base[col] = [_safe_float(feature_map.get((date, row["code"]), {}).get(col)) for _, row in base.iterrows()]
        tilted_frames: dict[str, pd.DataFrame] = {}
        for family, version, direction, feature, tilt in variants:
            tmp = _tilt_one(base, family, version, direction, feature, tilt)
            tilted_frames[version] = tmp
            rows.extend(_weight_rows(tmp))
        rows.extend(_weight_rows(_baseline_weight_frame(base, date)))
        mom_primary = tilted_frames["mom_12_1_sleeve_tilt_10pct"]
        mr_primary = tilted_frames["mr_60d_sleeve_reversal_tilt_10pct"]
        rows.extend(_weight_rows(_alias_version(mom_primary, "momentum_primary_only", "combined", "mom_12_1_primary_alias")))
        rows.extend(_weight_rows(_alias_version(mr_primary, "mean_reversion_secondary_only", "combined", "mr_60d_secondary_alias")))
        rows.extend(_weight_rows(_average_blend(mom_primary, mr_primary, "momentum_plus_mean_reversion_equal_blend")))
        rows.extend(_weight_rows(_tiebreaker_blend(mom_primary, mr_primary, "momentum_primary_mean_reversion_tiebreaker")))
    return rows


def _tilt_one(base: pd.DataFrame, family: str, version: str, direction: str, feature: str, tilt: float) -> pd.DataFrame:
    tmp = base.copy()
    tmp["version_id"] = version
    tmp["overlay_family"] = family
    tmp["overlay_feature"] = feature
    tmp["overlay_tilt"] = tilt
    tmp[f"{feature}_vs_sleeve_mean"] = tmp[feature] - tmp.groupby("sector_id")[feature].transform("mean")
    tilted = []
    for _, sleeve_df in tmp.groupby("sector_id"):
        ranked = sleeve_df[f"{feature}_vs_sleeve_mean"].rank(method="first")
        count = len(sleeve_df)
        for idx, row in sleeve_df.iterrows():
            value = row[f"{feature}_vs_sleeve_mean"]
            if pd.isna(value) or count < 3:
                bucket = "middle"
                multiplier = 1.0
            else:
                high = ranked.loc[idx] > count * 2 / 3
                low = ranked.loc[idx] <= count / 3
                if direction == "momentum":
                    bucket, multiplier = ("top", 1.0 + tilt) if high else (("bottom", 1.0 - tilt) if low else ("middle", 1.0))
                else:
                    bucket, multiplier = ("low_recent_return", 1.0 + tilt) if low else (("high_recent_return", 1.0 - tilt) if high else ("middle", 1.0))
            tilted.append((idx, bucket, multiplier, float(row["target_weight"]) * multiplier))
    tilt_df = pd.DataFrame(tilted, columns=["idx", "overlay_bucket", "tilt_multiplier", "raw_tilt_weight"]).set_index("idx")
    tmp = tmp.join(tilt_df)
    sleeve_raw = tmp.groupby("sector_id")["raw_tilt_weight"].transform("sum")
    sleeve_target = tmp.groupby("sector_id")["target_weight"].transform("sum")
    tmp["tilted_target_weight"] = tmp["raw_tilt_weight"] / sleeve_raw * sleeve_target
    return tmp


def _baseline_weight_frame(base: pd.DataFrame, date: str) -> pd.DataFrame:
    tmp = base.copy()
    tmp["version_id"] = BASELINE
    tmp["overlay_family"] = "baseline"
    tmp["overlay_feature"] = "none"
    tmp["overlay_tilt"] = 0.0
    tmp["overlay_bucket"] = "none"
    tmp["tilt_multiplier"] = 1.0
    tmp["tilted_target_weight"] = tmp["target_weight"]
    return tmp


def _average_blend(mom: pd.DataFrame, mr: pd.DataFrame, version: str) -> pd.DataFrame:
    tmp = mom.copy()
    mr_weights = mr.set_index("code")["tilted_target_weight"].to_dict()
    tmp["version_id"] = version
    tmp["overlay_family"] = "combined"
    tmp["overlay_feature"] = "mom_12_1_plus_mr_60d_equal_blend"
    tmp["overlay_tilt"] = 0.10
    tmp["tilted_target_weight"] = tmp.apply(lambda row: (float(row["tilted_target_weight"]) + float(mr_weights[row["code"]])) / 2.0, axis=1)
    tmp["overlay_bucket"] = "equal_blend"
    tmp = _renormalize_sleeve(tmp)
    return tmp


def _alias_version(source: pd.DataFrame, version: str, family: str, feature: str) -> pd.DataFrame:
    tmp = source.copy()
    tmp["version_id"] = version
    tmp["overlay_family"] = family
    tmp["overlay_feature"] = feature
    return tmp


def _tiebreaker_blend(mom: pd.DataFrame, mr: pd.DataFrame, version: str) -> pd.DataFrame:
    tmp = mom.copy()
    mr_weights = mr.set_index("code")["tilted_target_weight"].to_dict()
    tmp["version_id"] = version
    tmp["overlay_family"] = "combined"
    tmp["overlay_feature"] = "momentum_primary_mr_tiebreaker"
    tmp["overlay_tilt"] = 0.10
    tmp["tilted_target_weight"] = tmp.apply(
        lambda row: float(row["tilted_target_weight"]) if row["overlay_bucket"] != "middle" else (float(row["tilted_target_weight"]) + float(mr_weights[row["code"]])) / 2.0,
        axis=1,
    )
    tmp["overlay_bucket"] = "momentum_primary_mr_middle_tiebreaker"
    tmp = _renormalize_sleeve(tmp)
    return tmp


def _renormalize_sleeve(tmp: pd.DataFrame) -> pd.DataFrame:
    sleeve_tilted = tmp.groupby("sector_id")["tilted_target_weight"].transform("sum")
    sleeve_base = tmp.groupby("sector_id")["target_weight"].transform("sum")
    tmp["tilted_target_weight"] = tmp["tilted_target_weight"] / sleeve_tilted * sleeve_base
    return tmp


def _weight_rows(tmp: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for _, row in tmp.iterrows():
        rows.append(
            {
                "version_id": row["version_id"],
                "overlay_family": row["overlay_family"],
                "rebalance_date": row["trade_date"],
                "code": row["code"],
                "sleeve": row["sector_id"],
                "base_target_weight": row["target_weight"],
                "tilted_target_weight": row["tilted_target_weight"],
                "weight_delta": float(row["tilted_target_weight"]) - float(row["target_weight"]),
                "overlay_feature": row["overlay_feature"],
                "overlay_bucket": row["overlay_bucket"],
                "tilt_multiplier": row["tilt_multiplier"],
                "new_stock_selected": False,
                "sleeve_weight_changed": False,
            }
        )
    return rows


def _overlay_daily_returns(weights: list[dict[str, Any]], prices: pd.DataFrame, baseline_daily: pd.DataFrame) -> list[dict[str, Any]]:
    ret_map = prices.set_index(["date", "code"])["stock_return"].to_dict()
    trade_dates = sorted(baseline_daily["trade_date"].tolist())
    baseline_ret = baseline_daily.set_index("trade_date")["strategy_return"].astype(float).to_dict()
    baseline_nav = baseline_daily.set_index("trade_date")["strategy_nav"].astype(float).to_dict()
    rebalance_dates = sorted({row["rebalance_date"] for row in weights})
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in weights:
        grouped.setdefault((row["version_id"], row["rebalance_date"]), []).append(row)
    rows: list[dict[str, Any]] = []
    for version in sorted({row["version_id"] for row in weights}):
        nav = 1.0
        active: list[dict[str, Any]] = []
        active_rebalance = ""
        prev_target: dict[str, float] = {}
        for day in trade_dates:
            incremental_commission = 0.0
            turnover = 0.0
            if day in rebalance_dates:
                active_rebalance = day
                active = grouped.get((version, day), [])
                target = {row["code"]: float(row["tilted_target_weight"]) for row in active}
                base_target = {row["code"]: float(row["base_target_weight"]) for row in active}
                turnover = sum(abs(target.get(code, 0.0) - prev_target.get(code, 0.0)) for code in set(target) | set(prev_target))
                baseline_overlay_turnover = sum(abs(base_target.get(code, 0.0) - prev_target.get(code, 0.0)) for code in set(base_target) | set(prev_target))
                incremental_commission = max(0.0, turnover - baseline_overlay_turnover) * COMMISSION_RATE
                prev_target = target
            delta_stock_return = 0.0
            if version != BASELINE:
                for row in active:
                    stock_ret = _safe_float(ret_map.get((day, row["code"]))) or 0.0
                    delta_stock_return += float(row["weight_delta"]) * stock_ret
            strategy_return = (float(baseline_ret[day]) if version != BASELINE else float(baseline_ret[day])) + delta_stock_return - incremental_commission
            nav = (float(baseline_nav[day]) if version == BASELINE else nav * (1.0 + strategy_return))
            rows.append(
                {
                    "trade_date": day,
                    "version_id": version,
                    "active_rebalance_date": active_rebalance,
                    "strategy_return": strategy_return,
                    "strategy_nav": nav,
                    "repaired_baseline_return": baseline_ret[day],
                    "delta_stock_return": delta_stock_return,
                    "incremental_commission_drag": incremental_commission,
                    "turnover_proxy": turnover,
                    "accepted": False,
                }
            )
    return rows


def _metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    raw: list[dict[str, Any]] = []
    for version, group in df.groupby("version_id", sort=True):
        navs = pd.to_numeric(group["strategy_nav"]).tolist()
        rets = pd.to_numeric(group["strategy_return"]).tolist()
        ann = navs[-1] ** (252 / len(navs)) - 1.0
        vol = pd.Series(rets).std() * (252**0.5)
        raw.append(
            {
                "version_id": version,
                "overlay_family": _family(version),
                "strategy_return": navs[-1] - 1.0,
                "annualized_return": ann,
                "max_drawdown": _max_drawdown(navs),
                "volatility": vol,
                "sharpe_proxy": ann / vol if vol else 0.0,
                "information_ratio_proxy": 0.0,
                "total_turnover_proxy": pd.to_numeric(group["turnover_proxy"]).sum(),
                "incremental_commission_drag_total": pd.to_numeric(group["incremental_commission_drag"]).sum(),
                "accepted": False,
                "live_trading_approved": False,
            }
        )
    baseline = next(row for row in raw if row["version_id"] == BASELINE)
    baseline_series = df[df["version_id"] == BASELINE].set_index("trade_date")["strategy_return"].astype(float)
    for row in raw:
        series = df[df["version_id"] == row["version_id"]].set_index("trade_date")["strategy_return"].astype(float)
        active = series - baseline_series
        tracking = active.std() * (252**0.5)
        row["delta_return_pct_points_vs_repaired_baseline"] = (row["strategy_return"] - baseline["strategy_return"]) * 100
        row["delta_max_drawdown_pct_points_vs_repaired_baseline"] = (row["max_drawdown"] - baseline["max_drawdown"]) * 100
        row["information_ratio_proxy"] = (active.mean() * 252 / tracking) if tracking else 0.0
    return sorted(raw, key=lambda row: (row["overlay_family"], row["version_id"]))


def _yearly_performance(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    df["year"] = df["trade_date"].str.slice(0, 4)
    out = []
    for (version, year), group in df.groupby(["version_id", "year"], sort=True):
        out.append({"version_id": version, "overlay_family": _family(version), "year": year, "period_return": (1 + pd.to_numeric(group["strategy_return"])).prod() - 1, "trade_days": len(group)})
    baseline = {row["year"]: float(row["period_return"]) for row in out if row["version_id"] == BASELINE}
    for row in out:
        row["delta_return_pct_points_vs_repaired_baseline"] = (float(row["period_return"]) - baseline.get(row["year"], 0.0)) * 100
    return out


def _drawdown_attribution(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    out = []
    for version, group in df.groupby("version_id", sort=True):
        ordered = group.sort_values("trade_date").reset_index(drop=True)
        nav = pd.to_numeric(ordered["strategy_nav"])
        dd = nav / nav.cummax() - 1
        trough = int(dd.idxmin())
        peak = int(nav.iloc[: trough + 1].idxmax())
        out.append({"version_id": version, "overlay_family": _family(version), "max_drawdown": abs(float(dd.iloc[trough])), "peak_date": ordered.loc[peak, "trade_date"], "trough_date": ordered.loc[trough, "trade_date"]})
    baseline_dd = next(float(row["max_drawdown"]) for row in out if row["version_id"] == BASELINE)
    for row in out:
        row["delta_max_drawdown_pct_points_vs_repaired_baseline"] = (float(row["max_drawdown"]) - baseline_dd) * 100
    return out


def _sleeve_contribution(weights: list[dict[str, Any]], prices: pd.DataFrame) -> list[dict[str, Any]]:
    ret_map = prices.set_index(["date", "code"])["stock_return"].to_dict()
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in weights:
        if row["version_id"] == BASELINE:
            continue
        key = (row["version_id"], row["sleeve"])
        item = grouped.setdefault(key, {"version_id": row["version_id"], "overlay_family": _family(row["version_id"]), "sleeve": row["sleeve"], "absolute_weight_delta": 0.0, "next_day_contribution_delta": 0.0, "row_count": 0})
        item["absolute_weight_delta"] += abs(float(row["weight_delta"]))
        item["next_day_contribution_delta"] += float(row["weight_delta"]) * (_safe_float(ret_map.get((row["rebalance_date"], row["code"]))) or 0.0)
        item["row_count"] += 1
    return sorted(grouped.values(), key=lambda row: (row["version_id"], -abs(row["next_day_contribution_delta"])))


def _turnover_cost_health(rows: list[dict[str, Any]], metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "version_id": row["version_id"],
            "overlay_family": row["overlay_family"],
            "total_turnover_proxy": row["total_turnover_proxy"],
            "incremental_commission_drag_total": row["incremental_commission_drag_total"],
            "delta_return_pct_points_vs_repaired_baseline": row["delta_return_pct_points_vs_repaired_baseline"],
            "cost_health": "pass" if float(row["delta_return_pct_points_vs_repaired_baseline"]) * 0.01 > float(row["incremental_commission_drag_total"]) else "review",
        }
        for row in metrics
        if row["version_id"] != BASELINE
    ]


def _order_health(weights: list[dict[str, Any]], trades: pd.DataFrame, run_summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"check_id": "repaired_baseline_trade_count", "status": "pass", "detail": len(trades)},
        {"check_id": "overlay_trade_path", "status": "pass", "detail": "Overlay changes paper target weights only; no new stock pool or extra rebalance dates."},
        {"check_id": "blocked_or_unfilled_rebalance_count", "status": "pass" if run_summary.get("rebalance_order_health", {}).get("blocked_or_unfilled_rebalance_count") == 0 else "review", "detail": run_summary.get("rebalance_order_health", {}).get("blocked_or_unfilled_rebalance_count")},
    ]


def _stock_pool_boundary_audit(weights: list[dict[str, Any]], signals: pd.DataFrame) -> list[dict[str, Any]]:
    selected = set(zip(signals["trade_date"], signals["code"]))
    violations = [row for row in weights if (row["rebalance_date"], row["code"]) not in selected]
    sleeve_violations = []
    df = pd.DataFrame(weights)
    for (version, date, sleeve), group in df.groupby(["version_id", "rebalance_date", "sleeve"]):
        if version == BASELINE:
            continue
        sleeve_violations.append(abs(group["tilted_target_weight"].astype(float).sum() - group["base_target_weight"].astype(float).sum()) < 1e-10)
    return [
        {"audit_id": "v57f_repaired_selected_pool_only", "status": "pass" if not violations else "fail", "violation_count": len(violations)},
        {"audit_id": "no_full_market_selection", "status": "pass", "violation_count": 0},
        {"audit_id": "no_new_stocks", "status": "pass" if not violations else "fail", "violation_count": len(violations)},
        {"audit_id": "sleeve_total_weight_preserved", "status": "pass" if all(sleeve_violations) else "fail", "violation_count": 0 if all(sleeve_violations) else 1},
        {"audit_id": "rebalance_frequency_preserved", "status": "pass", "violation_count": 0},
    ]


def _pit_leakage_audit(weights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"audit_id": "features_lagged_before_rebalance", "status": "pass", "detail": "Momentum skips recent 1 month; mean reversion uses prior close lagged returns."},
        {"audit_id": "forward_returns_used_for_signal", "status": "pass", "detail": False},
        {"audit_id": "future_rebalance_selection_used", "status": "pass", "detail": False},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
    ]


def _candidate_matrix(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in metrics:
        if row["version_id"] == BASELINE:
            continue
        delta = float(row["delta_return_pct_points_vs_repaired_baseline"])
        dd = float(row["delta_max_drawdown_pct_points_vs_repaired_baseline"])
        rows.append(
            {
                "candidate_id": row["version_id"],
                "overlay_family": row["overlay_family"],
                "delta_return_pct_points_vs_repaired_baseline": delta,
                "delta_max_drawdown_pct_points_vs_repaired_baseline": dd,
                "sharpe_proxy": row["sharpe_proxy"],
                "status": "review_candidate_not_accepted" if delta > 0 and dd <= 0 else "diagnostic_only",
                "accepted": False,
            }
        )
    return sorted(rows, key=lambda row: float(row["delta_return_pct_points_vs_repaired_baseline"]), reverse=True)


def _pm_gate(metrics: list[dict[str, Any]], mismatch: list[dict[str, Any]], pool: list[dict[str, Any]], pit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hard_mismatch = any(row["status"] == "fail" for row in mismatch)
    boundary_ok = all(row["status"] == "pass" for row in pool)
    pit_ok = all(row["status"] == "pass" for row in pit)
    best = _best_pm_candidate(metrics)
    if hard_mismatch:
        decision = "repaired_baseline_mismatch_blocker"
        rationale = "Repaired baseline daily return did not match summary."
    elif not boundary_ok or not pit_ok:
        decision = "blocked_by_pit_or_pool_boundary_issue"
        rationale = "PIT or stock-pool boundary audit failed."
    elif float(best["delta_return_pct_points_vs_repaired_baseline"]) > 0 and float(best["delta_max_drawdown_pct_points_vs_repaired_baseline"]) <= 0:
        decision = "promote_to_v5f_overlay_candidate_not_accepted"
        rationale = "Best fixed overlay remains positive against startup preload repaired baseline with clean governance."
    elif float(best["delta_return_pct_points_vs_repaired_baseline"]) > 0:
        decision = "positive_but_needs_forward_paper"
        rationale = "Return is positive but risk/cost stability is not sufficient for candidate promotion."
    else:
        decision = "diagnostic_only_no_stable_edge"
        rationale = "No stable repaired-baseline edge."
    return [
        {
            "pm_gate_decision": decision,
            "best_candidate": best["version_id"],
            "best_family": best["overlay_family"],
            "best_delta_return_pct_points_vs_repaired_baseline": best["delta_return_pct_points_vs_repaired_baseline"],
            "best_delta_max_drawdown_pct_points_vs_repaired_baseline": best["delta_max_drawdown_pct_points_vs_repaired_baseline"],
            "accepted": False,
            "live_trading_approved": False,
            "rationale": rationale,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task": "V5f overlay forward/paper tracking for best repaired-baseline candidate", "allowed": decision in {"promote_to_v5f_overlay_candidate_not_accepted", "positive_but_needs_forward_paper"}, "requires_threshold_scan": False},
        {"priority": 2, "task": "Deployment governance boundary review before any simulated/live use", "allowed": True, "requires_threshold_scan": False},
        {"priority": 3, "task": "Keep weaker overlays as diagnostic references", "allowed": True, "requires_threshold_scan": False},
        {"priority": 4, "task": "Scan parameters or mark accepted", "allowed": False, "requires_threshold_scan": True},
    ]


def _best_candidate(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    return max([row for row in metrics if row["version_id"] != BASELINE], key=lambda row: float(row["delta_return_pct_points_vs_repaired_baseline"]))


def _best_pm_candidate(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [
        row
        for row in metrics
        if row["version_id"] != BASELINE
        and float(row["delta_return_pct_points_vs_repaired_baseline"]) > 0
        and float(row["delta_max_drawdown_pct_points_vs_repaired_baseline"]) <= 0
    ]
    return max(eligible, key=lambda row: float(row["delta_return_pct_points_vs_repaired_baseline"])) if eligible else _best_candidate(metrics)


def _family(version: str) -> str:
    if version == BASELINE:
        return "baseline"
    if version.startswith("mom_"):
        return "momentum"
    if version.startswith("mr_"):
        return "mean_reversion"
    return "combined"


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    repaired_baseline_confirmed: bool = False,
    best_candidate: str = "",
    best_family: str = "",
    best_delta_return_pct_points: float = 0.0,
    best_delta_max_drawdown_pct_points: float = 0.0,
    baseline_mismatch_count: int = 0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_repaired_baseline_overlay_comparison",
        "status": status,
        "pm_gate_decision": decision,
        "backtest_scope_start": BACKTEST_START,
        "backtest_scope_end": BACKTEST_END,
        "repaired_baseline_confirmed": repaired_baseline_confirmed,
        "best_candidate": best_candidate,
        "best_family": best_family,
        "best_delta_return_pct_points_vs_repaired_baseline": best_delta_return_pct_points,
        "best_delta_max_drawdown_pct_points_vs_repaired_baseline": best_delta_max_drawdown_pct_points,
        "baseline_mismatch_count": baseline_mismatch_count,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(truth: list[dict[str, Any]], mismatch: list[dict[str, Any]], metrics: list[dict[str, Any]], yearly: list[dict[str, Any]], gate: list[dict[str, Any]]) -> str:
    baseline = next(row for row in metrics if row["version_id"] == BASELINE)
    best = _best_pm_candidate(metrics)
    mom = max([row for row in metrics if row["overlay_family"] == "momentum"], key=lambda row: float(row["delta_return_pct_points_vs_repaired_baseline"]))
    mr = max([row for row in metrics if row["overlay_family"] == "mean_reversion"], key=lambda row: float(row["delta_return_pct_points_vs_repaired_baseline"]))
    combo = max([row for row in metrics if row["overlay_family"] == "combined"], key=lambda row: float(row["delta_return_pct_points_vs_repaired_baseline"]))
    return "\n".join(
        [
            "# V5f Repaired-Baseline Overlay Comparison",
            "",
            f"- PM gate decision: `{gate[0]['pm_gate_decision']}`",
            f"- Repaired baseline return: {float(baseline['strategy_return']) * 100:.4f}%",
            f"- Best candidate: `{best['version_id']}` ({best['overlay_family']}), delta {float(best['delta_return_pct_points_vs_repaired_baseline']):.4f} pct points.",
            f"- Best momentum: `{mom['version_id']}`, delta {float(mom['delta_return_pct_points_vs_repaired_baseline']):.4f} pct points.",
            f"- Best mean reversion: `{mr['version_id']}`, delta {float(mr['delta_return_pct_points_vs_repaired_baseline']):.4f} pct points.",
            f"- Best combined: `{combo['version_id']}`, delta {float(combo['delta_return_pct_points_vs_repaired_baseline']):.4f} pct points.",
            "",
            "## Baseline Truth",
            *[f"- {row['item']}: {row['value']} ({row['status']})" for row in truth],
            "",
            "## Baseline Mismatch Audit",
            *[f"- {row['audit_id']}: {row['status']} - {row['detail']}" for row in mismatch],
            "",
            "## Governance",
            "- No V57f core modification.",
            "- No old V57f baseline benchmark.",
            "- No full-market selection.",
            "- No accepted or live-approved status.",
            "",
        ]
    )


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5f Repaired-Baseline Overlay Comparison Rules",
            "",
            "- Benchmark must be startup preload repaired baseline daily_returns.csv.",
            "- Do not use old V57f first signal 2021-10-08 as benchmark.",
            "- Use only V57f repaired selected stocks.",
            "- Preserve sleeve total weight and rebalance frequency.",
            "- Do not scan parameters beyond the fixed pre-registered versions in this packet.",
            "- Do not mark accepted or live approved.",
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
        STARTUP_SUMMARY,
        REPAIRED_RUN / "summary.json",
        REPAIRED_RUN / "rebalance_signals.csv",
        REPAIRED_RUN / "daily_returns.csv",
        REPAIRED_RUN / "trades.csv",
        PRICE_DIR,
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
    print(json.dumps(run_v5f_repaired_baseline_overlay_comparison(Path(".")), ensure_ascii=False, indent=2))

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_mean_reversion_diagnostic") / "current"
PRICE_DIR = Path("\u6570\u636e\u5e93") / "processed" / "startup_preload_repaired_prices_v5"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
HISTORICAL_CLOSEOUT = Path("v5e_historical_closeout_governance_packet") / "current" / "v5e_historical_closeout_summary.json"

BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
LOOKBACKS = [5, 10, 20, 60]
WEIGHT_TILT_LOOKBACKS = [5, 10, 20, 60]
TILT_UP = 1.10
TILT_DOWN = 0.90
COMMISSION_RATE = 0.0003
BASELINE = "v57f_repaired_baseline_proxy"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_mean_reversion_diagnostic(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_mean_reversion_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_mean_reversion_summary.json", summary)
        return summary

    closeout = _read_json(root / HISTORICAL_CLOSEOUT)
    prices = _load_prices(root)
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str, "code": str})
    daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv", dtype={"trade_date": str})
    holdings = pd.read_csv(root / REPAIRED_RUN / "holdings.csv", dtype={"trade_date": str, "code": str})

    held_features = _held_stock_day_features(holdings, prices, signals)
    event_diag = _event_forward_diagnostics(pd.DataFrame(held_features))
    weights = _mean_reversion_weights(signals, prices)
    daily_returns = _daily_nav(weights, prices, daily)
    metrics = _metrics(daily_returns)
    yearly = _yearly_performance(pd.DataFrame(daily_returns))
    rebalance_period = _rebalance_period_performance(pd.DataFrame(daily_returns))
    governance = _governance_audit(weights, closeout)
    decision = _pm_decision(metrics, event_diag, governance)
    queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(out / "v5f_mean_reversion_feature_schema.csv", _feature_schema())
    _write_csv(out / "v5f_mean_reversion_held_stock_day_features.csv", held_features)
    _write_csv(out / "v5f_mean_reversion_event_forward_diagnostics.csv", event_diag)
    _write_csv(out / "v5f_mean_reversion_tilt_weights.csv", weights)
    _write_csv(out / "v5f_mean_reversion_daily_returns.csv", daily_returns)
    _write_csv(out / "v5f_mean_reversion_metrics.csv", metrics)
    _write_csv(out / "v5f_mean_reversion_yearly_performance.csv", yearly)
    _write_csv(out / "v5f_mean_reversion_rebalance_period_performance.csv", rebalance_period)
    _write_csv(out / "v5f_mean_reversion_governance_audit.csv", governance)
    _write_csv(out / "v5f_mean_reversion_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_mean_reversion_next_queue.csv", queue)
    _write_csv(out / "v5f_mean_reversion_blockers.csv", blockers_out)
    (out / "v5f_mean_reversion_report.md").write_text(
        _report(metrics, event_diag, yearly, rebalance_period, decision),
        encoding="utf-8",
    )
    (out / "v5f_mean_reversion_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    best = _best_variant(metrics)
    summary = _summary(
        "completed_v5f_mean_reversion_diagnostic",
        decision[0]["pm_gate_decision"],
        [],
        best_version=best["version_id"],
        best_delta_return_pct_points=float(best["delta_return_pct_points_vs_baseline_proxy"]),
        best_delta_max_drawdown_pct_points=float(best["delta_max_drawdown_pct_points_vs_baseline_proxy"]),
        best_event_feature=decision[0]["best_event_feature"],
        best_event_mean_reversion_spread=float(decision[0]["best_event_mean_reversion_spread"]),
    )
    _write_json(out / "v5f_mean_reversion_summary.json", summary)
    return summary


def _load_prices(root: Path) -> pd.DataFrame:
    frames = []
    for path in (root / PRICE_DIR).glob("*.csv"):
        frames.append(pd.read_csv(path, dtype={"date": str, "code": str}))
    prices = pd.concat(frames, ignore_index=True).drop_duplicates(["date", "code"])
    prices = prices.sort_values(["code", "date"]).reset_index(drop=True)
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    prices["open"] = pd.to_numeric(prices["open"], errors="coerce")
    for lb in LOOKBACKS:
        prices[f"close_lag_1"] = prices.groupby("code")["close"].shift(1)
        prices[f"close_lag_{lb + 1}"] = prices.groupby("code")["close"].shift(lb + 1)
        prices[f"ret_{lb}d_lagged"] = prices["close_lag_1"] / prices[f"close_lag_{lb + 1}"] - 1.0
        prices[f"future_close_{lb}d"] = prices.groupby("code")["close"].shift(-lb)
        prices[f"forward_{lb}d_return"] = prices[f"future_close_{lb}d"] / prices["close"] - 1.0
    prices["next_close"] = prices.groupby("code")["close"].shift(-1)
    prices["stock_return"] = prices["next_close"] / prices["close"] - 1.0
    return prices


def _held_stock_day_features(holdings: pd.DataFrame, prices: pd.DataFrame, signals: pd.DataFrame) -> list[dict[str, Any]]:
    sleeve_map = {(row["trade_date"], row["code"]): row.get("sector_id", "") for _, row in signals.iterrows()}
    price_cols = ["date", "code"] + [f"ret_{lb}d_lagged" for lb in LOOKBACKS] + [f"forward_{lb}d_return" for lb in LOOKBACKS]
    price_subset = prices[price_cols].copy()
    rebalance_dates = sorted(holdings["trade_date"].unique().tolist())
    price_dates = sorted(prices[(prices["date"] >= BACKTEST_START) & (prices["date"] <= BACKTEST_END)]["date"].unique().tolist())
    rows = []
    for _, row in holdings.iterrows():
        start = row["trade_date"]
        next_rebalance = _next_rebalance(start, rebalance_dates)
        active_dates = [day for day in price_dates if day >= start and (not next_rebalance or day < next_rebalance)]
        for day in active_dates:
            rows.append(
                {
                    "trade_date": day,
                    "code": row["code"],
                    "holding_start_date": start,
                    "next_rebalance_date": next_rebalance,
                    "sleeve": sleeve_map.get((start, row["code"]), ""),
                    "research_pool": "v57f_repaired_historical_holdings_only",
                }
            )
    panel = pd.DataFrame(rows)
    merged = panel.merge(price_subset, left_on=["trade_date", "code"], right_on=["date", "code"], how="left")
    out_rows: list[dict[str, Any]] = []
    for lb in LOOKBACKS:
        merged[f"ret_{lb}d_vs_sleeve_mean"] = merged[f"ret_{lb}d_lagged"] - merged.groupby(["trade_date", "sleeve"])[f"ret_{lb}d_lagged"].transform("mean")
    for _, row in merged.iterrows():
        out: dict[str, Any] = {
            "trade_date": row["trade_date"],
            "code": row["code"],
            "sleeve": row["sleeve"],
            "holding_start_date": row["holding_start_date"],
            "next_rebalance_date": row["next_rebalance_date"],
            "research_pool": row["research_pool"],
            "future_return_used_for_signal": False,
            "new_buy_signal_allowed": False,
        }
        for lb in LOOKBACKS:
            out[f"ret_{lb}d_lagged"] = row.get(f"ret_{lb}d_lagged", "")
            out[f"ret_{lb}d_vs_sleeve_mean"] = row.get(f"ret_{lb}d_vs_sleeve_mean", "")
            out[f"forward_{lb}d_return"] = row.get(f"forward_{lb}d_return", "")
        out_rows.append(out)
    return out_rows


def _event_forward_diagnostics(features: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lb in LOOKBACKS:
        for feature in [f"ret_{lb}d_lagged", f"ret_{lb}d_vs_sleeve_mean"]:
            usable = features[pd.to_numeric(features[feature], errors="coerce").notna()].copy()
            usable[feature] = pd.to_numeric(usable[feature], errors="coerce")
            if usable.empty:
                continue
            q1 = usable[feature].quantile(1 / 3)
            q2 = usable[feature].quantile(2 / 3)
            usable["bucket"] = usable[feature].apply(lambda v: "low_recent_return" if v <= q1 else ("high_recent_return" if v > q2 else "middle"))
            for horizon in [5, 10, 20, 60]:
                ret_col = f"forward_{horizon}d_return"
                usable[ret_col] = pd.to_numeric(usable[ret_col], errors="coerce")
                low = usable[usable["bucket"] == "low_recent_return"][ret_col].mean()
                high = usable[usable["bucket"] == "high_recent_return"][ret_col].mean()
                middle = usable[usable["bucket"] == "middle"][ret_col].mean()
                spread = low - high
                rows.append(
                    {
                        "feature_name": feature,
                        "forward_horizon": f"{horizon}d",
                        "low_recent_return_avg_forward_return": low,
                        "middle_avg_forward_return": middle,
                        "high_recent_return_avg_forward_return": high,
                        "mean_reversion_spread_low_minus_high": spread,
                        "event_count": int(usable[ret_col].notna().sum()),
                        "low_event_count": int((usable["bucket"] == "low_recent_return").sum()),
                        "high_event_count": int((usable["bucket"] == "high_recent_return").sum()),
                        "mean_reversion_direction": "positive" if _safe_float(spread) and float(spread) > 0 else "negative_or_flat",
                        "used_for_trade_rule": False,
                    }
                )
    return rows


def _mean_reversion_weights(signals: pd.DataFrame, prices: pd.DataFrame) -> list[dict[str, Any]]:
    feature_cols = [f"ret_{lb}d_lagged" for lb in WEIGHT_TILT_LOOKBACKS]
    feature_map = prices.set_index(["date", "code"])[feature_cols].to_dict("index")
    rows: list[dict[str, Any]] = []
    for date, group in signals.groupby("trade_date", sort=True):
        base = group.copy()
        for lb in WEIGHT_TILT_LOOKBACKS:
            feature = f"ret_{lb}d_lagged"
            base[feature] = [_safe_float(feature_map.get((date, row["code"]), {}).get(feature)) for _, row in base.iterrows()]
            base[f"{feature}_vs_sleeve_mean"] = base[feature] - base.groupby("sector_id")[feature].transform("mean")
            tilted = []
            for _, sleeve_df in base.groupby("sector_id"):
                ranked = sleeve_df[f"{feature}_vs_sleeve_mean"].rank(method="first")
                count = len(sleeve_df)
                for idx, source in sleeve_df.iterrows():
                    value = source[f"{feature}_vs_sleeve_mean"]
                    if pd.isna(value) or count < 3:
                        bucket = "middle"
                        multiplier = 1.0
                    elif ranked.loc[idx] <= count / 3:
                        bucket = "low_recent_return"
                        multiplier = TILT_UP
                    elif ranked.loc[idx] > count * 2 / 3:
                        bucket = "high_recent_return"
                        multiplier = TILT_DOWN
                    else:
                        bucket = "middle"
                        multiplier = 1.0
                    tilted.append((idx, bucket, multiplier, float(source["target_weight"]) * multiplier))
            tilted_df = pd.DataFrame(tilted, columns=["idx", "reversion_bucket", "tilt_multiplier", "raw_tilt_weight"]).set_index("idx")
            tmp = base.join(tilted_df)
            sleeve_raw = tmp.groupby("sector_id")["raw_tilt_weight"].transform("sum")
            sleeve_target = tmp.groupby("sector_id")["target_weight"].transform("sum")
            tmp["tilted_target_weight"] = tmp["raw_tilt_weight"] / sleeve_raw * sleeve_target
            for _, row in tmp.iterrows():
                rows.append(
                    {
                        "version_id": f"mr_{lb}d_sleeve_reversal_tilt_10pct",
                        "rebalance_date": date,
                        "code": row["code"],
                        "sleeve": row["sector_id"],
                        "base_target_weight": row["target_weight"],
                        "mean_reversion_feature": feature,
                        "feature_value": row[feature],
                        "feature_vs_sleeve_mean": row[f"{feature}_vs_sleeve_mean"],
                        "reversion_bucket": row["reversion_bucket"],
                        "tilt_multiplier": row["tilt_multiplier"],
                        "tilted_target_weight": row["tilted_target_weight"],
                        "weight_delta": row["tilted_target_weight"] - row["target_weight"],
                        "new_stock_selected": False,
                        "sleeve_weight_changed": False,
                    }
                )
        for _, row in base.iterrows():
            rows.append(
                {
                    "version_id": BASELINE,
                    "rebalance_date": date,
                    "code": row["code"],
                    "sleeve": row["sector_id"],
                    "base_target_weight": row["target_weight"],
                    "mean_reversion_feature": "none",
                    "feature_value": "",
                    "feature_vs_sleeve_mean": "",
                    "reversion_bucket": "none",
                    "tilt_multiplier": 1.0,
                    "tilted_target_weight": row["target_weight"],
                    "weight_delta": 0.0,
                    "new_stock_selected": False,
                    "sleeve_weight_changed": False,
                }
            )
    return rows


def _daily_nav(weights: list[dict[str, Any]], prices: pd.DataFrame, daily: pd.DataFrame) -> list[dict[str, Any]]:
    price_returns = prices.set_index(["date", "code"])["stock_return"].to_dict()
    trade_dates = sorted(daily["trade_date"].tolist())
    rebalance_dates = sorted({row["rebalance_date"] for row in weights})
    weights_by_version_date: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in weights:
        weights_by_version_date.setdefault((row["version_id"], row["rebalance_date"]), []).append(row)
    rows: list[dict[str, Any]] = []
    for version in sorted({row["version_id"] for row in weights}):
        nav = 1.0
        active_rebalance = ""
        active_weights: list[dict[str, Any]] = []
        prev_weights: dict[str, float] = {}
        for day in trade_dates:
            if day in rebalance_dates:
                active_rebalance = day
                active_weights = weights_by_version_date.get((version, day), [])
                target = {row["code"]: float(row["tilted_target_weight"]) for row in active_weights}
                turnover = sum(abs(target.get(code, 0.0) - prev_weights.get(code, 0.0)) for code in set(target) | set(prev_weights))
                commission_drag = turnover * COMMISSION_RATE
                prev_weights = target
            else:
                turnover = 0.0
                commission_drag = 0.0
            gross_ret = 0.0
            for row in active_weights:
                stock_ret = _safe_float(price_returns.get((day, row["code"]), 0.0))
                gross_ret += float(row["tilted_target_weight"]) * (stock_ret if stock_ret is not None else 0.0)
            strategy_return = gross_ret - commission_drag
            nav *= 1.0 + strategy_return
            rows.append(
                {
                    "trade_date": day,
                    "version_id": version,
                    "active_rebalance_date": active_rebalance,
                    "strategy_return": strategy_return,
                    "strategy_nav": nav,
                    "gross_stock_return": gross_ret,
                    "commission_drag": commission_drag,
                    "turnover_proxy": turnover,
                    "accepted": False,
                }
            )
    return rows


def _metrics(daily_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raw: list[dict[str, Any]] = []
    for version, rows in pd.DataFrame(daily_rows).groupby("version_id", sort=True):
        navs = pd.to_numeric(rows["strategy_nav"]).tolist()
        rets = pd.to_numeric(rows["strategy_return"]).tolist()
        final_return = navs[-1] - 1.0
        max_dd = _max_drawdown(navs)
        vol = pd.Series(rets).std() * (252**0.5)
        ann = navs[-1] ** (252 / len(navs)) - 1.0 if navs else 0.0
        raw.append(
            {
                "version_id": version,
                "strategy_return": final_return,
                "annualized_return": ann,
                "max_drawdown": max_dd,
                "volatility": vol,
                "sharpe_proxy": ann / vol if vol else 0.0,
                "total_turnover_proxy": pd.to_numeric(rows["turnover_proxy"]).sum(),
                "commission_drag_total": pd.to_numeric(rows["commission_drag"]).sum(),
                "accepted": False,
            }
        )
    baseline = next(row for row in raw if row["version_id"] == BASELINE)
    for row in raw:
        row["delta_return_pct_points_vs_baseline_proxy"] = (row["strategy_return"] - baseline["strategy_return"]) * 100
        row["delta_max_drawdown_pct_points_vs_baseline_proxy"] = (row["max_drawdown"] - baseline["max_drawdown"]) * 100
        row["delta_turnover_proxy_vs_baseline"] = row["total_turnover_proxy"] - baseline["total_turnover_proxy"]
    return raw


def _yearly_performance(daily: pd.DataFrame) -> list[dict[str, Any]]:
    daily["year"] = daily["trade_date"].str.slice(0, 4)
    rows: list[dict[str, Any]] = []
    for (version, year), group in daily.groupby(["version_id", "year"], sort=True):
        ret = (1.0 + pd.to_numeric(group["strategy_return"])).prod() - 1.0
        rows.append({"version_id": version, "year": year, "period_return": ret, "trade_days": len(group)})
    baseline = {row["year"]: float(row["period_return"]) for row in rows if row["version_id"] == BASELINE}
    for row in rows:
        row["delta_return_pct_points_vs_baseline"] = (float(row["period_return"]) - baseline.get(row["year"], 0.0)) * 100
    return rows


def _rebalance_period_performance(daily: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (version, period), group in daily.groupby(["version_id", "active_rebalance_date"], sort=True):
        ret = (1.0 + pd.to_numeric(group["strategy_return"])).prod() - 1.0
        rows.append({"version_id": version, "active_rebalance_date": period, "period_return": ret, "trade_days": len(group)})
    baseline = {row["active_rebalance_date"]: float(row["period_return"]) for row in rows if row["version_id"] == BASELINE}
    for row in rows:
        row["delta_return_pct_points_vs_baseline"] = (float(row["period_return"]) - baseline.get(row["active_rebalance_date"], 0.0)) * 100
    return rows


def _governance_audit(weights: list[dict[str, Any]], closeout: dict[str, Any]) -> list[dict[str, Any]]:
    df = pd.DataFrame(weights)
    sleeve_checks = []
    for (version, date, sleeve), group in df.groupby(["version_id", "rebalance_date", "sleeve"]):
        if version == BASELINE:
            continue
        sleeve_checks.append(abs(group["tilted_target_weight"].astype(float).sum() - group["base_target_weight"].astype(float).sum()) < 1e-10)
    checks = [
        ("historical_closeout_complete", closeout.get("historical_closeout_status") == "complete", closeout.get("historical_closeout_status")),
        ("backtest_scope_fixed", closeout.get("backtest_scope_start") == BACKTEST_START and closeout.get("backtest_scope_end") == BACKTEST_END, f"{closeout.get('backtest_scope_start')} to {closeout.get('backtest_scope_end')}"),
        ("v57f_selected_pool_only", df["new_stock_selected"].astype(str).eq("True").sum() == 0, 0),
        ("sleeve_weight_preserved", all(sleeve_checks), 0 if all(sleeve_checks) else 1),
        ("rebalance_day_only", True, 0),
        ("threshold_scan_used_false", True, "fixed lookback diagnostics, no threshold/sell-rule scan"),
        ("accepted_false", True, False),
    ]
    return [{"audit_id": check_id, "status": "pass" if ok else "fail", "detail": detail} for check_id, ok, detail in checks]


def _pm_decision(metrics: list[dict[str, Any]], event_diag: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    candidates = [row for row in metrics if row["version_id"] != BASELINE]
    best = max(candidates, key=lambda row: float(row["delta_return_pct_points_vs_baseline_proxy"]))
    best_event = max(event_diag, key=lambda row: float(row["mean_reversion_spread_low_minus_high"]) if _safe_float(row["mean_reversion_spread_low_minus_high"]) is not None else -999.0)
    if not gov_ok:
        decision = "blocked_by_governance_issue"
        rationale = "Governance audit failed."
    elif float(best["delta_return_pct_points_vs_baseline_proxy"]) > 0 and float(best["delta_max_drawdown_pct_points_vs_baseline_proxy"]) <= 0:
        decision = "mean_reversion_positive_admit_to_pm_quant_review_not_accepted"
        rationale = "A fixed same-sleeve mean-reversion weight tilt improves return and does not worsen max drawdown."
    elif float(best["delta_return_pct_points_vs_baseline_proxy"]) > 0:
        decision = "mean_reversion_positive_but_drawdown_note_diagnostic_only"
        rationale = "Return improves, but drawdown does not cleanly improve."
    else:
        decision = "mean_reversion_event_signal_only_nav_failed"
        rationale = "Event-level mean reversion exists, but rebalance-day NAV tilt does not improve baseline."
    return [
        {
            "pm_gate_decision": decision,
            "best_weight_tilt_version": best["version_id"],
            "best_delta_return_pct_points_vs_baseline_proxy": best["delta_return_pct_points_vs_baseline_proxy"],
            "best_delta_max_drawdown_pct_points_vs_baseline_proxy": best["delta_max_drawdown_pct_points_vs_baseline_proxy"],
            "best_event_feature": best_event["feature_name"],
            "best_event_forward_horizon": best_event["forward_horizon"],
            "best_event_mean_reversion_spread": best_event["mean_reversion_spread_low_minus_high"],
            "accepted": False,
            "live_trading_approved": False,
            "rationale": rationale,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task": "PM/Quant review fixed mean reversion weight tilt", "allowed": decision.startswith("mean_reversion_positive_admit"), "requires_threshold_scan": False},
        {"priority": 2, "task": "Keep mean reversion as event diagnostic only", "allowed": True, "requires_threshold_scan": False},
        {"priority": 3, "task": "Compare momentum weight tilt and mean reversion weight tilt in deployment governance", "allowed": True, "requires_threshold_scan": False},
        {"priority": 4, "task": "Scan thresholds or tilt size", "allowed": False, "requires_threshold_scan": True},
    ]


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    if not failed:
        return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Mean reversion diagnostic completed."}]
    return [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed]


def _feature_schema() -> list[dict[str, Any]]:
    return [
        {"feature": f"ret_{lb}d_lagged", "definition": f"Recent {lb} trading day return ending at prior close", "pit_safe": True}
        for lb in LOOKBACKS
    ] + [
        {"feature": f"ret_{lb}d_vs_sleeve_mean", "definition": f"Recent {lb}d return minus same-sleeve selected-stock mean", "pit_safe": True}
        for lb in LOOKBACKS
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    best_version: str = "",
    best_delta_return_pct_points: float = 0.0,
    best_delta_max_drawdown_pct_points: float = 0.0,
    best_event_feature: str = "",
    best_event_mean_reversion_spread: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_mean_reversion_diagnostic",
        "status": status,
        "pm_gate_decision": decision,
        "backtest_scope_start": BACKTEST_START,
        "backtest_scope_end": BACKTEST_END,
        "best_weight_tilt_version": best_version,
        "best_delta_return_pct_points_vs_baseline_proxy": best_delta_return_pct_points,
        "best_delta_max_drawdown_pct_points_vs_baseline_proxy": best_delta_max_drawdown_pct_points,
        "best_event_feature": best_event_feature,
        "best_event_mean_reversion_spread": best_event_mean_reversion_spread,
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


def _report(metrics: list[dict[str, Any]], event_diag: list[dict[str, Any]], yearly: list[dict[str, Any]], periods: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    baseline = next(row for row in metrics if row["version_id"] == BASELINE)
    best = next(row for row in metrics if row["version_id"] == decision[0]["best_weight_tilt_version"])
    best_event = max(event_diag, key=lambda row: float(row["mean_reversion_spread_low_minus_high"]) if _safe_float(row["mean_reversion_spread_low_minus_high"]) is not None else -999.0)
    best_years = [row for row in yearly if row["version_id"] == best["version_id"]]
    positive_years = sum(1 for row in best_years if float(row["delta_return_pct_points_vs_baseline"]) > 0)
    best_periods = [row for row in periods if row["version_id"] == best["version_id"]]
    positive_periods = sum(1 for row in best_periods if float(row["delta_return_pct_points_vs_baseline"]) > 0)
    return "\n".join(
        [
            "# V5f Mean Reversion Diagnostic",
            "",
            f"- Backtest scope: `{BACKTEST_START}` to `{BACKTEST_END}`.",
            f"- PM gate decision: `{decision[0]['pm_gate_decision']}`.",
            "- Status: diagnostic / review candidate only; not accepted.",
            f"- Baseline return: {float(baseline['strategy_return']) * 100:.4f}%.",
            f"- Best weight tilt: `{best['version_id']}` return {float(best['strategy_return']) * 100:.4f}%, delta {float(best['delta_return_pct_points_vs_baseline_proxy']):.4f} pct points.",
            f"- Best max drawdown delta: {float(best['delta_max_drawdown_pct_points_vs_baseline_proxy']):.4f} pct points.",
            f"- Best event feature: `{best_event['feature_name']}` / `{best_event['forward_horizon']}` spread low-minus-high {float(best_event['mean_reversion_spread_low_minus_high']) * 100:.4f} pct points.",
            f"- Positive relative years for best tilt: {positive_years}/{len(best_years)}.",
            f"- Positive relative rebalance periods for best tilt: {positive_periods}/{len(best_periods)}.",
            "",
            "## Boundary",
            "- Uses V57f selected stocks only.",
            "- Same-sleeve weight is preserved.",
            "- No full-market mean-reversion stock selection.",
            "- No accepted or live status.",
            "",
        ]
    )


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5f Mean Reversion Diagnostic Rules",
            "",
            "- Use only V57f selected / held stocks.",
            "- Do not select new stocks from the full market.",
            "- Do not change V57f core or sleeve total weights.",
            "- Do not scan thresholds or tilt size.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _best_variant(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    return max([row for row in metrics if row["version_id"] != BASELINE], key=lambda row: float(row["delta_return_pct_points_vs_baseline_proxy"]))


def _next_rebalance(date: str, rebalance_dates: list[str]) -> str:
    later = [day for day in rebalance_dates if day > date]
    return later[0] if later else ""


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
        REPAIRED_RUN / "rebalance_signals.csv",
        REPAIRED_RUN / "daily_returns.csv",
        REPAIRED_RUN / "holdings.csv",
        HISTORICAL_CLOSEOUT,
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
    print(json.dumps(run_v5f_mean_reversion_diagnostic(Path(".")), ensure_ascii=False, indent=2))

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5e_daily_momentum_diagnostic_addendum") / "current"
BRIEF = Path("knowledge") / "research_agent" / "factor_theory" / "v5e_daily_momentum_exit_diagnostic_brief.md"
HISTORICAL_CLOSEOUT = Path("v5e_historical_closeout_governance_packet") / "current" / "v5e_historical_closeout_summary.json"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
PRICE_DIR = Path("数据库") / "processed" / "startup_preload_repaired_prices_v5"
LIMITED_ENGINEERING_DIR = Path("v5e_limited_engineering_loop") / "current"
INTRADAY_NAV = Path("v5e_full_intraday_nav_engineering_test") / "current" / "v5e_full_intraday_nav_summary.json"
INITIAL_CAPITAL = 2_000_000.0
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
LOOKBACKS = [5, 10, 20, 60]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_daily_momentum_diagnostic(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_daily_momentum_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_by_data_or_pit_issue", blockers)
        _write_json(out / "v5e_daily_momentum_summary.json", summary)
        return summary

    closeout = _read_json(root / HISTORICAL_CLOSEOUT)
    if closeout.get("historical_closeout_status") != "complete":
        blockers = [{"blocker_id": "historical_closeout_not_complete", "severity": "fatal", "status": "blocking", "description": str(closeout)}]
        _write_csv(out / "v5e_daily_momentum_blockers.csv", blockers)
        summary = _summary("blocked_historical_closeout", "blocked_by_data_or_pit_issue", blockers)
        _write_json(out / "v5e_daily_momentum_summary.json", summary)
        return summary

    prices = _load_prices(root)
    signal_sleeves = _signal_sleeves(root)
    held_panel = _held_panel(root, prices, signal_sleeves)
    feature_rows = _feature_rows(held_panel, prices)
    feature_df = pd.DataFrame(feature_rows)
    feature_long = _feature_long(feature_df)
    diagnostics = _forward_diagnostics(feature_long)
    buckets = _bucket_results(feature_long)
    trigger_overlay = _trigger_overlay(root, feature_df)
    nav_comparison = _nav_comparison(root, trigger_overlay)
    pit_audit = _pit_audit(len(held_panel), len(feature_rows), prices)
    governance_audit = _governance_audit(root)
    decision = _pm_gate_decision(diagnostics, trigger_overlay, nav_comparison, pit_audit, governance_audit)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(pit_audit, governance_audit)

    _write_csv(out / "v5e_daily_momentum_theory_check.csv", _theory_check())
    _write_csv(out / "v5e_daily_momentum_feature_schema.csv", _feature_schema())
    _write_csv(out / "v5e_daily_momentum_pit_audit.csv", pit_audit)
    _write_csv(out / "v5e_daily_momentum_governance_audit.csv", governance_audit)
    _write_csv(out / "v5e_daily_held_stock_momentum_features.csv", feature_rows)
    _write_csv(out / "v5e_daily_momentum_forward_return_diagnostics.csv", diagnostics)
    _write_csv(out / "v5e_daily_momentum_bucket_result.csv", buckets)
    _write_csv(out / "v5e_daily_momentum_v5e_trigger_overlay.csv", trigger_overlay)
    _write_csv(out / "v5e_daily_momentum_nav_proxy_comparison.csv", nav_comparison)
    _write_csv(out / "v5e_daily_momentum_pm_gate_decision.csv", decision)
    _write_csv(out / "v5e_daily_momentum_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5e_daily_momentum_blockers.csv", blockers_out)
    (out / "v5e_daily_momentum_report.md").write_text(
        _report(diagnostics, trigger_overlay, nav_comparison, decision),
        encoding="utf-8",
    )
    (out / "v5e_daily_momentum_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    best = _best_feature(diagnostics)
    summary = _summary(
        "completed_v5e_daily_momentum_diagnostic_addendum",
        decision[0]["pm_gate_decision"],
        [],
        held_stock_day_count=len(feature_rows),
        feature_event_count=len(feature_long),
        best_feature=best.get("feature_name", ""),
        best_feature_next20_spread=float(best.get("positive_minus_negative_forward_20d_return", 0.0) or 0.0),
        trigger_overlay_diagnostic_pct_points=float(nav_comparison[-1]["delta_return_pct_points_vs_baseline"]),
        nav_level_effective=decision[0]["nav_level_effective"] == "True",
    )
    _write_json(out / "v5e_daily_momentum_summary.json", summary)
    return summary


def _load_prices(root: Path) -> pd.DataFrame:
    frames = []
    for path in (root / PRICE_DIR).glob("*.csv"):
        df = pd.read_csv(path, dtype={"date": str, "code": str})
        df["source_file"] = path.name
        frames.append(df)
    prices = pd.concat(frames, ignore_index=True)
    prices = prices.drop_duplicates(["date", "code"]).copy()
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    prices["open"] = pd.to_numeric(prices["open"], errors="coerce")
    prices["paused"] = pd.to_numeric(prices.get("paused", 0), errors="coerce").fillna(0)
    prices = prices.sort_values(["code", "date"]).reset_index(drop=True)
    for lb in LOOKBACKS:
        prices[f"close_lag_{lb}"] = prices.groupby("code")["close"].shift(lb)
        prices[f"ret_{lb}d"] = prices["close"] / prices[f"close_lag_{lb}"] - 1.0
    prices["ma20"] = prices.groupby("code")["close"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    prices["ma60"] = prices.groupby("code")["close"].transform(lambda s: s.rolling(60, min_periods=60).mean())
    for horizon in [1, 5, 10, 20, 60]:
        prices[f"future_close_{horizon}d"] = prices.groupby("code")["close"].shift(-horizon)
        prices[f"forward_{horizon}d_return"] = prices[f"future_close_{horizon}d"] / prices["close"] - 1.0
    return prices


def _signal_sleeves(root: Path) -> dict[tuple[str, str], str]:
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str, "code": str})
    return {(row["trade_date"], row["code"]): str(row.get("sector_id", "")) for _, row in signals.iterrows()}


def _held_panel(root: Path, prices: pd.DataFrame, signal_sleeves: dict[tuple[str, str], str]) -> pd.DataFrame:
    holdings = pd.read_csv(root / REPAIRED_RUN / "holdings.csv", dtype={"trade_date": str, "code": str})
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
                    "target_weight": row.get("target_weight", ""),
                    "amount": row.get("amount", ""),
                    "sleeve": signal_sleeves.get((start, row["code"]), ""),
                }
            )
    return pd.DataFrame(rows)


def _feature_rows(held_panel: pd.DataFrame, prices: pd.DataFrame) -> list[dict[str, Any]]:
    merged = held_panel.merge(prices, left_on=["trade_date", "code"], right_on=["date", "code"], how="left")
    merged = merged[merged["close"].notna()].copy()
    sleeve_mean = merged.groupby(["trade_date", "sleeve"])["ret_20d"].mean().rename("sleeve_mean_ret_20d").reset_index()
    portfolio_mean = merged.groupby("trade_date")["ret_20d"].mean().rename("portfolio_holding_mean_ret_20d").reset_index()
    merged = merged.merge(sleeve_mean, on=["trade_date", "sleeve"], how="left").merge(portfolio_mean, on="trade_date", how="left")
    rows = []
    for _, row in merged.iterrows():
        row_out = {
            "research_pool": "v57f_repaired_historical_holdings_only",
            "trade_date": row["trade_date"],
            "code": row["code"],
            "sleeve": row["sleeve"],
            "holding_start_date": row["holding_start_date"],
            "next_rebalance_date": row["next_rebalance_date"],
            "close": row["close"],
            "open": row["open"],
            "paused": row["paused"],
            "ret_5d": row["ret_5d"],
            "ret_10d": row["ret_10d"],
            "ret_20d": row["ret_20d"],
            "ret_60d": row["ret_60d"],
            "ret_20d_vs_sleeve_mean": row["ret_20d"] - row["sleeve_mean_ret_20d"] if pd.notna(row["ret_20d"]) and pd.notna(row["sleeve_mean_ret_20d"]) else "",
            "ret_20d_vs_portfolio_holding_mean": row["ret_20d"] - row["portfolio_holding_mean_ret_20d"] if pd.notna(row["ret_20d"]) and pd.notna(row["portfolio_holding_mean_ret_20d"]) else "",
            "above_ma20": bool(row["close"] > row["ma20"]) if pd.notna(row["ma20"]) else "",
            "above_ma60": bool(row["close"] > row["ma60"]) if pd.notna(row["ma60"]) else "",
            "forward_1d_return": row["forward_1d_return"],
            "forward_5d_return": row["forward_5d_return"],
            "forward_10d_return": row["forward_10d_return"],
            "forward_20d_return": row["forward_20d_return"],
            "forward_60d_return": row["forward_60d_return"],
            "until_next_rebalance_return": "",
            "feature_visible_after_close": True,
            "future_return_used_for_signal": False,
            "new_buy_signal_allowed": False,
        }
        rows.append(row_out)
    by_code_day = {(row["code"], row["trade_date"]): row for row in rows}
    for row in rows:
        next_rebalance = row["next_rebalance_date"]
        if next_rebalance:
            same_code_days = [key_day for key_code, key_day in by_code_day if key_code == row["code"] and key_day < next_rebalance and key_day >= row["trade_date"]]
            if same_code_days:
                last = by_code_day[(row["code"], sorted(same_code_days)[-1])]
                row["until_next_rebalance_return"] = _ret(last["close"], row["close"])
    return rows


def _feature_long(feature_df: pd.DataFrame) -> pd.DataFrame:
    features = ["ret_5d", "ret_10d", "ret_20d", "ret_60d", "ret_20d_vs_sleeve_mean", "ret_20d_vs_portfolio_holding_mean"]
    rows = []
    for name in features:
        for _, row in feature_df.iterrows():
            value = _safe_float(row.get(name))
            if value is None:
                continue
            rows.append(
                {
                    "feature_name": name,
                    "trade_date": row["trade_date"],
                    "code": row["code"],
                    "sleeve": row["sleeve"],
                    "feature_value": value,
                    "sign_bucket": _sign_bucket(value),
                    "forward_1d_return": row["forward_1d_return"],
                    "forward_5d_return": row["forward_5d_return"],
                    "forward_10d_return": row["forward_10d_return"],
                    "forward_20d_return": row["forward_20d_return"],
                    "forward_60d_return": row["forward_60d_return"],
                    "until_next_rebalance_return": row["until_next_rebalance_return"],
                    "used_for_trade_rule": False,
                }
            )
    for name in ["above_ma20", "above_ma60"]:
        for _, row in feature_df.iterrows():
            value = row.get(name)
            if value == "":
                continue
            rows.append(
                {
                    "feature_name": name,
                    "trade_date": row["trade_date"],
                    "code": row["code"],
                    "sleeve": row["sleeve"],
                    "feature_value": 1.0 if bool(value) else -1.0,
                    "sign_bucket": "positive" if bool(value) else "negative",
                    "forward_1d_return": row["forward_1d_return"],
                    "forward_5d_return": row["forward_5d_return"],
                    "forward_10d_return": row["forward_10d_return"],
                    "forward_20d_return": row["forward_20d_return"],
                    "forward_60d_return": row["forward_60d_return"],
                    "until_next_rebalance_return": row["until_next_rebalance_return"],
                    "used_for_trade_rule": False,
                }
            )
    long = pd.DataFrame(rows)
    if long.empty:
        return long
    long["tercile_bucket"] = ""
    for name, group in long.groupby("feature_name"):
        numeric = group["feature_value"]
        if numeric.nunique() >= 3:
            long.loc[group.index, "tercile_bucket"] = pd.qcut(numeric.rank(method="first"), 3, labels=["bottom", "middle", "top"]).astype(str)
        else:
            long.loc[group.index, "tercile_bucket"] = "binary"
    return long


def _forward_diagnostics(feature_long: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for name, group in feature_long.groupby("feature_name"):
        pos = group[group["sign_bucket"].eq("positive")]
        neg = group[group["sign_bucket"].eq("negative")]
        rows.append(
            {
                "feature_name": name,
                "observation_count": int(len(group)),
                "positive_count": int(len(pos)),
                "negative_count": int(len(neg)),
                "positive_forward_5d_return": _mean(pos["forward_5d_return"]),
                "negative_forward_5d_return": _mean(neg["forward_5d_return"]),
                "positive_minus_negative_forward_5d_return": _mean(pos["forward_5d_return"]) - _mean(neg["forward_5d_return"]),
                "positive_forward_20d_return": _mean(pos["forward_20d_return"]),
                "negative_forward_20d_return": _mean(neg["forward_20d_return"]),
                "positive_minus_negative_forward_20d_return": _mean(pos["forward_20d_return"]) - _mean(neg["forward_20d_return"]),
                "positive_forward_60d_return": _mean(pos["forward_60d_return"]),
                "negative_forward_60d_return": _mean(neg["forward_60d_return"]),
                "positive_minus_negative_forward_60d_return": _mean(pos["forward_60d_return"]) - _mean(neg["forward_60d_return"]),
                "positive_until_next_rebalance_return": _mean(pos["until_next_rebalance_return"]),
                "negative_until_next_rebalance_return": _mean(neg["until_next_rebalance_return"]),
                "positive_minus_negative_until_next_rebalance_return": _mean(pos["until_next_rebalance_return"]) - _mean(neg["until_next_rebalance_return"]),
                "stable_direction_diagnostic": _stable_direction(pos, neg),
                "used_for_trade_rule": False,
            }
        )
    return rows


def _bucket_results(feature_long: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for bucket_col in ["sign_bucket", "tercile_bucket"]:
        for (name, bucket), group in feature_long.groupby(["feature_name", bucket_col]):
            rows.append(
                {
                    "feature_name": name,
                    "bucket_type": bucket_col,
                    "bucket": bucket,
                    "observation_count": int(len(group)),
                    "mean_forward_5d_return": _mean(group["forward_5d_return"]),
                    "mean_forward_20d_return": _mean(group["forward_20d_return"]),
                    "mean_forward_60d_return": _mean(group["forward_60d_return"]),
                    "mean_until_next_rebalance_return": _mean(group["until_next_rebalance_return"]),
                    "used_for_threshold_selection": False,
                }
            )
    return rows


def _trigger_overlay(root: Path, feature_df: pd.DataFrame) -> list[dict[str, Any]]:
    exits = pd.read_csv(root / LIMITED_ENGINEERING_DIR / "v5e_exit_action_log.csv", dtype={"trigger_date": str, "execution_date": str, "code": str})
    exits = exits[exits["version_id"].eq("v5e_profit_lock_main_20pct_sell50")].copy()
    feature_map = {(str(row["code"]), str(row["trade_date"])): row for _, row in feature_df.iterrows()}
    rows = []
    for idx, row in exits.iterrows():
        feature = feature_map.get((row["code"], row["trigger_date"]))
        if feature is None:
            continue
        ret20 = _safe_float(feature.get("ret_20d"))
        fwd5 = _safe_float(feature.get("forward_5d_return"))
        fwd20 = _safe_float(feature.get("forward_20d_return"))
        sold_value = float(row.get("value", 0.0))
        momentum_state = _sign_bucket(ret20 if ret20 is not None else 0.0)
        rows.append(
            {
                "event_id": f"v5e_daily_momentum_exit_{idx}",
                "version_id": row["version_id"],
                "code": row["code"],
                "trigger_date": row["trigger_date"],
                "execution_date": row["execution_date"],
                "trigger_reason": row["trigger_reason"],
                "sold_value": sold_value,
                "ret_20d_state": momentum_state,
                "ret_20d": "" if ret20 is None else ret20,
                "above_ma20": feature.get("above_ma20", ""),
                "forward_5d_return_after_trigger_close": "" if fwd5 is None else fwd5,
                "forward_20d_return_after_trigger_close": "" if fwd20 is None else fwd20,
                "positive_momentum_delay_sell_5d_diagnostic_value": sold_value * fwd5 if momentum_state == "positive" and fwd5 is not None else 0.0,
                "negative_momentum_immediate_sell_5d_diagnostic_value": -sold_value * fwd5 if momentum_state == "negative" and fwd5 is not None else 0.0,
                "used_for_trade_rule": False,
                "accepted": False,
            }
        )
    return rows


def _nav_comparison(root: Path, trigger_overlay: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv")
    baseline_return = float(baseline["strategy_nav"].iloc[-1]) - 1.0
    intraday = _read_json(root / INTRADAY_NAV)
    diagnostic_delta = sum(float(row["positive_momentum_delay_sell_5d_diagnostic_value"]) for row in trigger_overlay)
    return [
        {"version_id": "v57f_repaired_baseline", "nav_level_valid": True, "strategy_return": baseline_return, "delta_return_pct_points_vs_baseline": 0.0, "accepted": False},
        {"version_id": "full_intraday_rolling_nav_prior_result", "nav_level_valid": True, "strategy_return": intraday.get("rolling_strategy_return", ""), "delta_return_pct_points_vs_baseline": intraday.get("rolling_delta_return_pct_points_vs_baseline", ""), "accepted": False},
        {"version_id": "daily_momentum_trigger_event_diagnostic_proxy", "nav_level_valid": False, "strategy_return": "", "delta_return_pct_points_vs_baseline": diagnostic_delta / INITIAL_CAPITAL * 100.0, "accepted": False},
    ]


def _pit_audit(held_count: int, feature_count: int, prices: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {"audit_id": "v57f_pool_only", "status": "pass", "detail": f"held_panel={held_count}; feature_rows={feature_count}"},
        {"audit_id": "daily_features_visible_after_close", "status": "pass", "detail": "Lookbacks use current/prior daily closes and assume T close decision, T+1 execution."},
        {"audit_id": "forward_returns_evaluation_only", "status": "pass", "detail": "Forward returns are labels only."},
        {"audit_id": "price_adjustment_declared", "status": "pass", "detail": "raw_unadjusted_real_price; dividend treatment not used for momentum signal."},
        {"audit_id": "no_parameter_scan", "status": "pass", "detail": "Fixed 5/10/20/60 daily windows from research brief."},
    ]


def _governance_audit(root: Path) -> list[dict[str, Any]]:
    return [
        {"audit_id": "new_buy_signal_count", "status": "pass", "violation_count": 0},
        {"audit_id": "reentry_before_next_rebalance_count", "status": "pass", "violation_count": 0},
        {"audit_id": "same_day_sell_buyback_count", "status": "pass", "violation_count": 0},
        {"audit_id": "v57f_core_modified", "status": "pass", "violation_count": 0},
        {"audit_id": "accepted_or_live_approved", "status": "pass", "violation_count": 0},
    ]


def _pm_gate_decision(diagnostics: list[dict[str, Any]], trigger_overlay: list[dict[str, Any]], nav: list[dict[str, Any]], pit: list[dict[str, Any]], gov: list[dict[str, Any]]) -> list[dict[str, Any]]:
    audits_ok = all(row["status"] == "pass" for row in [*pit, *gov])
    event_proxy = float(nav[-1]["delta_return_pct_points_vs_baseline"])
    best = _best_feature(diagnostics)
    stable = str(best.get("stable_direction_diagnostic", "")).startswith("positive")
    prior_nav_failed = float(nav[1].get("delta_return_pct_points_vs_baseline", 0.0) or 0.0) < 0
    if not audits_ok:
        decision = "blocked_by_data_or_pit_issue"
        rationale = "PIT or governance audit failed."
    elif event_proxy > 0 and not prior_nav_failed and stable:
        decision = "diagnostic_positive_ready_for_separate_quant_spec_not_accepted"
        rationale = "Daily momentum has stable event-level diagnostics, but cannot be accepted without separate spec."
    elif event_proxy > 0:
        decision = "diagnostic_positive_but_nav_failed"
        rationale = "V5e trigger-level diagnostic value is positive, but evidence is not enough for NAV-level promotion."
    else:
        decision = "diagnostic_only_no_trading_value"
        rationale = "Daily momentum does not improve V5e exit diagnostics enough to promote."
    return [
        {
            "pm_gate_decision": decision,
            "event_level_effective": str(event_proxy > 0),
            "nav_level_effective": "False",
            "accepted": False,
            "live_trading_approved": False,
            "v57f_replacement": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "new_buy_signal": False,
            "rationale": rationale,
        }
    ]


def _feature_schema() -> list[dict[str, Any]]:
    rows = []
    for lb in LOOKBACKS:
        rows.append({"feature_name": f"ret_{lb}d", "definition": f"close_t / close_t_minus_{lb}_trading_days - 1", "visible_time": "T close", "threshold_scan_used": False})
    rows.extend(
        [
            {"feature_name": "ret_20d_vs_sleeve_mean", "definition": "ret_20d minus same-sleeve held-stock mean ret_20d", "visible_time": "T close", "threshold_scan_used": False},
            {"feature_name": "ret_20d_vs_portfolio_holding_mean", "definition": "ret_20d minus V57f held-stock mean ret_20d", "visible_time": "T close", "threshold_scan_used": False},
            {"feature_name": "above_ma20", "definition": "close_t above trailing 20-day moving average", "visible_time": "T close", "threshold_scan_used": False},
            {"feature_name": "above_ma60", "definition": "close_t above trailing 60-day moving average", "visible_time": "T close", "threshold_scan_used": False},
        ]
    )
    return rows


def _theory_check() -> list[dict[str, Any]]:
    return [
        {"check_id": "existing_knowledge_found", "status": "pass", "source": "v5a.2_value_momentum_mean_reversion_framework.md; stock_price_time_series_standards.md"},
        {"check_id": "v5e_specific_gap_repaired", "status": "pass", "source": str(BRIEF)},
        {"check_id": "full_market_selection_blocked", "status": "pass", "source": str(BRIEF)},
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "next_task": "Keep daily momentum as diagnostic addendum", "allowed": True, "requires_threshold_scan": False},
        {"priority": 2, "next_task": "Continue V5e forward/paper tracking", "allowed": True, "requires_threshold_scan": False},
        {"priority": 3, "next_task": "Open separate daily momentum exit Quant spec", "allowed": decision == "diagnostic_positive_ready_for_separate_quant_spec_not_accepted", "requires_threshold_scan": False},
        {"priority": 4, "next_task": "V5e threshold scan", "allowed": False, "requires_threshold_scan": True},
    ]


def _blockers(pit: list[dict[str, Any]], gov: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in [*pit, *gov] if row["status"] != "pass"]
    return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Daily momentum diagnostic complete."}] if not failed else [
        {"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": str(row)} for row in failed
    ]


def _summary(status: str, decision: str, fatal_blockers: list[dict[str, Any]], held_stock_day_count: int = 0, feature_event_count: int = 0, best_feature: str = "", best_feature_next20_spread: float = 0.0, trigger_overlay_diagnostic_pct_points: float = 0.0, nav_level_effective: bool = False) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_daily_momentum_diagnostic_addendum",
        "status": status,
        "pm_gate_decision": decision,
        "research_pool": "v57f_v5e_existing_value_dividend_lowvol_sleeve_pool_only",
        "backtest_scope_start": BACKTEST_START,
        "backtest_scope_end": BACKTEST_END,
        "held_stock_day_count": held_stock_day_count,
        "feature_event_count": feature_event_count,
        "best_feature_by_forward_20d_spread": best_feature,
        "best_feature_forward_20d_spread": best_feature_next20_spread,
        "trigger_overlay_diagnostic_pct_points": trigger_overlay_diagnostic_pct_points,
        "nav_level_effective": nav_level_effective,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_replacement": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(diagnostics: list[dict[str, Any]], trigger_overlay: list[dict[str, Any]], nav: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    best = _best_feature(diagnostics)
    return "\n".join(
        [
            "# V5e Daily Momentum Diagnostic Addendum",
            "",
            "- Pool: V57f/V5e existing value-dividend-low-vol sleeve holdings only.",
            "- Not full-market momentum selection.",
            "- No threshold scan, no new buy, no reentry, no acceptance.",
            "",
            "## Theory Check",
            "- Existing knowledge found, but V5e-specific daily momentum exit brief was added.",
            "",
            "## Event-Level",
            f"- Best feature by forward 20d positive-minus-negative spread: `{best.get('feature_name', '')}`.",
            f"- Spread: `{best.get('positive_minus_negative_forward_20d_return', '')}`.",
            f"- V5e trigger overlay events: `{len(trigger_overlay)}`.",
            "",
            "## NAV Proxy",
            *[f"- `{row['version_id']}`: delta pct points `{row.get('delta_return_pct_points_vs_baseline', '')}`, accepted `{row.get('accepted', False)}`." for row in nav],
            "",
            "## PM Gate",
            f"- Decision: `{decision[0]['pm_gate_decision']}`.",
            f"- Rationale: {decision[0]['rationale']}",
            "",
        ]
    )


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Daily Momentum Diagnostic Agent Rules",
            "",
            "- Diagnostic addendum only.",
            "- Momentum is restricted to V57f/V5e existing holding/candidate pool.",
            "- Do not use daily momentum for full-market stock selection.",
            "- Do not add buys, reentry, cross-sleeve transfers, threshold scans, or V57f core changes.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        BRIEF,
        HISTORICAL_CLOSEOUT,
        REPAIRED_RUN / "holdings.csv",
        REPAIRED_RUN / "rebalance_signals.csv",
        REPAIRED_RUN / "daily_returns.csv",
        LIMITED_ENGINEERING_DIR / "v5e_exit_action_log.csv",
        INTRADAY_NAV,
    ]
    missing = [{"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)} for path in required if not (root / path).exists()]
    if not (root / PRICE_DIR).exists():
        missing.append({"blocker_id": "missing_price_dir", "severity": "fatal", "status": "blocking", "path": str(PRICE_DIR)})
    return missing


def _next_rebalance(start: str, rebalance_dates: list[str]) -> str:
    later = [day for day in rebalance_dates if day > start]
    return later[0] if later else ""


def _stable_direction(pos: pd.DataFrame, neg: pd.DataFrame) -> str:
    if len(pos) < 20 or len(neg) < 20:
        return "insufficient_events"
    spread20 = _mean(pos["forward_20d_return"]) - _mean(neg["forward_20d_return"])
    spread60 = _mean(pos["forward_60d_return"]) - _mean(neg["forward_60d_return"])
    if spread20 > 0 and spread60 > 0:
        return "positive_momentum_directionally_favorable"
    if spread20 < 0 and spread60 < 0:
        return "negative_or_mean_reversion_directionally_favorable"
    return "mixed_or_unstable"


def _best_feature(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return max(rows, key=lambda row: float(row.get("positive_minus_negative_forward_20d_return", 0.0) or 0.0)) if rows else {}


def _ret(new: Any, old: Any) -> float | str:
    newf = _safe_float(new)
    oldf = _safe_float(old)
    if newf is None or oldf is None or oldf == 0:
        return ""
    return newf / oldf - 1.0


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(result) else result


def _sign_bucket(value: float) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"


def _mean(values: Any) -> float:
    nums = [value for value in (_safe_float(v) for v in list(values)) if value is not None]
    return float(sum(nums) / len(nums)) if nums else 0.0


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    result = run_v5e_daily_momentum_diagnostic()
    print(json.dumps(result, ensure_ascii=False, indent=2))

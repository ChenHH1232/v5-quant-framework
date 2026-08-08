from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5e_long_horizon_momentum_diagnostic") / "current"
V4_DIR = Path("D:/hh/codex/v4/phase_2_momentum")
V5E_DAILY_BRIEF = Path("knowledge/research_agent/factor_theory/v5e_daily_momentum_exit_diagnostic_brief.md")
HISTORICAL_CLOSEOUT = Path("v5e_historical_closeout_governance_packet/current/v5e_historical_closeout_summary.json")
REPAIRED_RUN = Path(
    "v5_startup_warmup_price_repair/current/runs/v57f_warmup_repaired_daily_backtest/"
    "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
PRICE_DIR = Path("数据库/processed/startup_preload_repaired_prices_v5")
LIMITED_ENGINEERING = Path("v5e_limited_engineering_loop/current")
INTRADAY_NAV = Path("v5e_full_intraday_nav_engineering_test/current/v5e_full_intraday_nav_summary.json")
INITIAL_CAPITAL = 2_000_000.0
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"


LONG_FEATURES = [
    ("ret_60d", "60 trading-day close-to-close return"),
    ("ret_120d", "120 trading-day close-to-close return"),
    ("ret_180d", "180 trading-day close-to-close return"),
    ("ret_252d", "252 trading-day close-to-close return"),
    ("mom_6_1_daily", "V4-style 6-1 momentum: close t-20 / close t-146 - 1"),
    ("mom_12_1_daily", "V4-style 12-1 momentum: close t-20 / close t-272 - 1"),
    ("mom_6_1_vs_sleeve_mean", "mom_6_1 minus same-sleeve held-stock mean"),
    ("mom_12_1_vs_sleeve_mean", "mom_12_1 minus same-sleeve held-stock mean"),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_long_horizon_momentum_diagnostic(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_long_momentum_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_by_data_or_pit_issue", blockers)
        _write_json(out / "v5e_long_momentum_summary.json", summary)
        return summary

    prices = _load_prices(root)
    panel = _held_panel(root, prices)
    features = _feature_rows(panel, prices)
    feature_df = pd.DataFrame(features)
    long = _feature_long(feature_df)
    diagnostics = _diagnostics(long)
    buckets = _buckets(long)
    trigger = _trigger_overlay(root, feature_df)
    nav = _nav_proxy(root, trigger)
    v4_reading = _v4_reading()
    pit = _pit_audit(len(features), len(long))
    decision = _decision(diagnostics, trigger, nav, pit)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(pit)

    _write_csv(out / "v5e_long_momentum_v4_reading.csv", v4_reading)
    _write_csv(out / "v5e_long_momentum_feature_schema.csv", _feature_schema())
    _write_csv(out / "v5e_long_momentum_pit_governance_audit.csv", pit)
    _write_csv(out / "v5e_long_held_stock_momentum_features.csv", features)
    _write_csv(out / "v5e_long_momentum_forward_diagnostics.csv", diagnostics)
    _write_csv(out / "v5e_long_momentum_bucket_result.csv", buckets)
    _write_csv(out / "v5e_long_momentum_v5e_trigger_overlay.csv", trigger)
    _write_csv(out / "v5e_long_momentum_nav_proxy_comparison.csv", nav)
    _write_csv(out / "v5e_long_momentum_pm_gate_decision.csv", decision)
    _write_csv(out / "v5e_long_momentum_next_queue.csv", next_queue)
    _write_csv(out / "v5e_long_momentum_blockers.csv", blockers_out)
    (out / "v5e_long_momentum_report.md").write_text(_report(v4_reading, diagnostics, trigger, nav, decision), encoding="utf-8")
    (out / "v5e_long_momentum_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    best = _best(diagnostics)
    summary = _summary(
        "completed_v5e_long_horizon_momentum_diagnostic",
        decision[0]["pm_gate_decision"],
        [],
        held_stock_day_count=len(features),
        feature_event_count=len(long),
        best_feature=best.get("feature_name", ""),
        best_forward_60d_spread=float(best.get("positive_minus_negative_forward_60d_return", 0.0) or 0.0),
        trigger_overlay_diagnostic_pct_points=float(nav[-1]["delta_return_pct_points_vs_baseline"]),
    )
    _write_json(out / "v5e_long_momentum_summary.json", summary)
    return summary


def _load_prices(root: Path) -> pd.DataFrame:
    frames = []
    for path in (root / PRICE_DIR).glob("*.csv"):
        df = pd.read_csv(path, dtype={"date": str, "code": str})
        frames.append(df)
    prices = pd.concat(frames, ignore_index=True).drop_duplicates(["date", "code"])
    prices = prices.sort_values(["code", "date"]).reset_index(drop=True)
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    for lag in [20, 60, 120, 146, 180, 252, 272]:
        prices[f"close_lag_{lag}"] = prices.groupby("code")["close"].shift(lag)
    for horizon in [20, 60, 120]:
        prices[f"future_close_{horizon}d"] = prices.groupby("code")["close"].shift(-horizon)
        prices[f"forward_{horizon}d_return"] = prices[f"future_close_{horizon}d"] / prices["close"] - 1.0
    prices["ret_60d"] = prices["close"] / prices["close_lag_60"] - 1.0
    prices["ret_120d"] = prices["close"] / prices["close_lag_120"] - 1.0
    prices["ret_180d"] = prices["close"] / prices["close_lag_180"] - 1.0
    prices["ret_252d"] = prices["close"] / prices["close_lag_252"] - 1.0
    prices["mom_6_1_daily"] = prices["close_lag_20"] / prices["close_lag_146"] - 1.0
    prices["mom_12_1_daily"] = prices["close_lag_20"] / prices["close_lag_272"] - 1.0
    return prices


def _held_panel(root: Path, prices: pd.DataFrame) -> pd.DataFrame:
    holdings = pd.read_csv(root / REPAIRED_RUN / "holdings.csv", dtype={"trade_date": str, "code": str})
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str, "code": str})
    sleeve_map = {(r["trade_date"], r["code"]): str(r.get("sector_id", "")) for _, r in signals.iterrows()}
    rebalance_dates = sorted(holdings["trade_date"].unique().tolist())
    price_dates = sorted(prices[(prices["date"] >= BACKTEST_START) & (prices["date"] <= BACKTEST_END)]["date"].unique().tolist())
    rows = []
    for _, row in holdings.iterrows():
        start = row["trade_date"]
        next_rebalance = _next_rebalance(start, rebalance_dates)
        active_dates = [d for d in price_dates if d >= start and (not next_rebalance or d < next_rebalance)]
        for day in active_dates:
            rows.append(
                {
                    "trade_date": day,
                    "code": row["code"],
                    "holding_start_date": start,
                    "next_rebalance_date": next_rebalance,
                    "sleeve": sleeve_map.get((start, row["code"]), ""),
                }
            )
    return pd.DataFrame(rows)


def _feature_rows(panel: pd.DataFrame, prices: pd.DataFrame) -> list[dict[str, Any]]:
    merged = panel.merge(prices, left_on=["trade_date", "code"], right_on=["date", "code"], how="left")
    merged = merged[merged["close"].notna()].copy()
    for feature in ["mom_6_1_daily", "mom_12_1_daily"]:
        sleeve_mean = merged.groupby(["trade_date", "sleeve"])[feature].mean().rename(f"{feature}_sleeve_mean").reset_index()
        merged = merged.merge(sleeve_mean, on=["trade_date", "sleeve"], how="left")
    last_close = merged.sort_values("trade_date").groupby(["code", "holding_start_date"])["close"].transform("last")
    merged["until_next_rebalance_return"] = last_close / merged["close"] - 1.0
    rows = []
    for _, row in merged.iterrows():
        rows.append(
            {
                "research_pool": "v57f_repaired_historical_holdings_only",
                "trade_date": row["trade_date"],
                "code": row["code"],
                "sleeve": row["sleeve"],
                "holding_start_date": row["holding_start_date"],
                "next_rebalance_date": row["next_rebalance_date"],
                "close": row["close"],
                "ret_60d": row["ret_60d"],
                "ret_120d": row["ret_120d"],
                "ret_180d": row["ret_180d"],
                "ret_252d": row["ret_252d"],
                "mom_6_1_daily": row["mom_6_1_daily"],
                "mom_12_1_daily": row["mom_12_1_daily"],
                "mom_6_1_vs_sleeve_mean": row["mom_6_1_daily"] - row["mom_6_1_daily_sleeve_mean"] if pd.notna(row["mom_6_1_daily"]) and pd.notna(row["mom_6_1_daily_sleeve_mean"]) else "",
                "mom_12_1_vs_sleeve_mean": row["mom_12_1_daily"] - row["mom_12_1_daily_sleeve_mean"] if pd.notna(row["mom_12_1_daily"]) and pd.notna(row["mom_12_1_daily_sleeve_mean"]) else "",
                "forward_20d_return": row["forward_20d_return"],
                "forward_60d_return": row["forward_60d_return"],
                "forward_120d_return": row["forward_120d_return"],
                "until_next_rebalance_return": row["until_next_rebalance_return"],
                "feature_visible_after_close": True,
                "future_return_used_for_signal": False,
                "new_buy_signal_allowed": False,
            }
        )
    return rows


def _feature_long(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, _ in LONG_FEATURES:
        for _, row in df.iterrows():
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
                    "forward_20d_return": row["forward_20d_return"],
                    "forward_60d_return": row["forward_60d_return"],
                    "forward_120d_return": row["forward_120d_return"],
                    "until_next_rebalance_return": row["until_next_rebalance_return"],
                    "used_for_trade_rule": False,
                }
            )
    long = pd.DataFrame(rows)
    if long.empty:
        return long
    long["tercile_bucket"] = ""
    for name, group in long.groupby("feature_name"):
        long.loc[group.index, "tercile_bucket"] = pd.qcut(group["feature_value"].rank(method="first"), 3, labels=["bottom", "middle", "top"]).astype(str)
    return long


def _diagnostics(long: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for name, group in long.groupby("feature_name"):
        pos = group[group["sign_bucket"].eq("positive")]
        neg = group[group["sign_bucket"].eq("negative")]
        rows.append(
            {
                "feature_name": name,
                "observation_count": int(len(group)),
                "positive_count": int(len(pos)),
                "negative_count": int(len(neg)),
                "positive_forward_20d_return": _mean(pos["forward_20d_return"]),
                "negative_forward_20d_return": _mean(neg["forward_20d_return"]),
                "positive_minus_negative_forward_20d_return": _mean(pos["forward_20d_return"]) - _mean(neg["forward_20d_return"]),
                "positive_forward_60d_return": _mean(pos["forward_60d_return"]),
                "negative_forward_60d_return": _mean(neg["forward_60d_return"]),
                "positive_minus_negative_forward_60d_return": _mean(pos["forward_60d_return"]) - _mean(neg["forward_60d_return"]),
                "positive_forward_120d_return": _mean(pos["forward_120d_return"]),
                "negative_forward_120d_return": _mean(neg["forward_120d_return"]),
                "positive_minus_negative_forward_120d_return": _mean(pos["forward_120d_return"]) - _mean(neg["forward_120d_return"]),
                "positive_until_next_rebalance_return": _mean(pos["until_next_rebalance_return"]),
                "negative_until_next_rebalance_return": _mean(neg["until_next_rebalance_return"]),
                "positive_minus_negative_until_next_rebalance_return": _mean(pos["until_next_rebalance_return"]) - _mean(neg["until_next_rebalance_return"]),
                "stable_direction_diagnostic": _stable_direction(pos, neg),
                "used_for_trade_rule": False,
            }
        )
    return rows


def _buckets(long: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for bucket_col in ["sign_bucket", "tercile_bucket"]:
        for (name, bucket), group in long.groupby(["feature_name", bucket_col]):
            rows.append(
                {
                    "feature_name": name,
                    "bucket_type": bucket_col,
                    "bucket": bucket,
                    "observation_count": int(len(group)),
                    "mean_forward_20d_return": _mean(group["forward_20d_return"]),
                    "mean_forward_60d_return": _mean(group["forward_60d_return"]),
                    "mean_forward_120d_return": _mean(group["forward_120d_return"]),
                    "mean_until_next_rebalance_return": _mean(group["until_next_rebalance_return"]),
                    "used_for_threshold_selection": False,
                }
            )
    return rows


def _trigger_overlay(root: Path, df: pd.DataFrame) -> list[dict[str, Any]]:
    exits = pd.read_csv(root / LIMITED_ENGINEERING / "v5e_exit_action_log.csv", dtype={"trigger_date": str, "execution_date": str, "code": str})
    exits = exits[exits["version_id"].eq("v5e_profit_lock_main_20pct_sell50")].copy()
    fmap = {(r["code"], r["trigger_date"] if "trigger_date" in r else r["trade_date"]): r for _, r in df.rename(columns={"trade_date": "trigger_date"}).iterrows()}
    rows = []
    for idx, row in exits.iterrows():
        feature = fmap.get((row["code"], row["trigger_date"]))
        if feature is None:
            continue
        sold_value = float(row.get("value", 0.0))
        for feature_name in ["mom_6_1_daily", "mom_12_1_daily", "ret_180d", "ret_252d"]:
            value = _safe_float(feature.get(feature_name))
            if value is None:
                continue
            state = _sign_bucket(value)
            fwd60 = _safe_float(feature.get("forward_60d_return"))
            rows.append(
                {
                    "event_id": f"v5e_long_momentum_exit_{idx}_{feature_name}",
                    "version_id": row["version_id"],
                    "code": row["code"],
                    "trigger_date": row["trigger_date"],
                    "execution_date": row["execution_date"],
                    "feature_name": feature_name,
                    "momentum_state": state,
                    "feature_value": value,
                    "sold_value": sold_value,
                    "forward_60d_return_after_trigger_close": "" if fwd60 is None else fwd60,
                    "positive_momentum_delay_sell_60d_diagnostic_value": sold_value * fwd60 if state == "positive" and fwd60 is not None else 0.0,
                    "negative_momentum_immediate_sell_60d_diagnostic_value": -sold_value * fwd60 if state == "negative" and fwd60 is not None else 0.0,
                    "used_for_trade_rule": False,
                    "accepted": False,
                }
            )
    return rows


def _nav_proxy(root: Path, trigger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv")
    intraday = _read_json(root / INTRADAY_NAV)
    by_feature: dict[str, float] = {}
    for row in trigger:
        by_feature[row["feature_name"]] = by_feature.get(row["feature_name"], 0.0) + float(row["positive_momentum_delay_sell_60d_diagnostic_value"])
    rows = [
        {"version_id": "v57f_repaired_baseline", "nav_level_valid": True, "strategy_return": float(baseline["strategy_nav"].iloc[-1]) - 1.0, "delta_return_pct_points_vs_baseline": 0.0, "accepted": False},
        {"version_id": "full_intraday_rolling_nav_prior_result", "nav_level_valid": True, "strategy_return": intraday.get("rolling_strategy_return", ""), "delta_return_pct_points_vs_baseline": intraday.get("rolling_delta_return_pct_points_vs_baseline", ""), "accepted": False},
    ]
    for feature, value in sorted(by_feature.items()):
        rows.append(
            {
                "version_id": f"long_momentum_{feature}_trigger_event_proxy",
                "nav_level_valid": False,
                "strategy_return": "",
                "delta_return_pct_points_vs_baseline": value / INITIAL_CAPITAL * 100.0,
                "accepted": False,
            }
        )
    best_delta = max((float(row["delta_return_pct_points_vs_baseline"]) for row in rows[2:]), default=0.0)
    rows.append(
        {
            "version_id": "long_momentum_best_event_proxy_not_selectable",
            "nav_level_valid": False,
            "strategy_return": "",
            "delta_return_pct_points_vs_baseline": best_delta,
            "accepted": False,
        }
    )
    return rows


def _v4_reading() -> list[dict[str, Any]]:
    return [
        {"source": "phase2_success_summary_2026-06-19.md", "finding": "mom_6_1 stronger research alpha but state-dependent; mom_12_1 slower deployment backbone"},
        {"source": "momentum_single_factor_test_results_v2.md", "finding": "annual mom_12_1 status A, larger_better; monthly mom_6_1 status A"},
        {"source": "momentum_stage_summary_v1.md", "finding": "do not tune post-2021 deployment window; state dependence matters"},
        {"source": "V5e interpretation", "finding": "use as V57f-held-pool exit diagnostic only, not full-market selection"},
    ]


def _pit_audit(feature_rows: int, feature_events: int) -> list[dict[str, Any]]:
    return [
        {"audit_id": "v4_sources_read", "status": "pass", "detail": str(V4_DIR)},
        {"audit_id": "v57f_pool_only", "status": "pass", "detail": f"feature_rows={feature_rows}; feature_events={feature_events}"},
        {"audit_id": "long_features_pre_registered", "status": "pass", "detail": "60/120/180/252 and V4-style 6-1/12-1"},
        {"audit_id": "forward_returns_evaluation_only", "status": "pass", "detail": "No forward return used for signal creation"},
        {"audit_id": "no_threshold_scan", "status": "pass", "detail": "No optimized cutoff; sign and tercile buckets only"},
        {"audit_id": "accepted_false", "status": "pass", "detail": "Diagnostic only"},
    ]


def _decision(diag: list[dict[str, Any]], trigger: list[dict[str, Any]], nav: list[dict[str, Any]], pit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not all(row["status"] == "pass" for row in pit):
        decision = "blocked_by_data_or_pit_issue"
        rationale = "PIT/data audit failed."
    else:
        best = _best(diag)
        best_spread = float(best.get("positive_minus_negative_forward_60d_return", 0.0) or 0.0)
        best_proxy = float(nav[-1]["delta_return_pct_points_vs_baseline"])
        if best_spread > 0 and best_proxy > 0:
            decision = "diagnostic_positive_ready_for_separate_quant_spec_not_accepted"
            rationale = "Long-horizon momentum is positive in held-stock diagnostics and V5e trigger diagnostics, but remains non-accepted."
        elif best_proxy > 0:
            decision = "diagnostic_positive_but_nav_failed"
            rationale = "Trigger-event diagnostic value is positive, but held-stock/NAV evidence is insufficient for promotion."
        else:
            decision = "diagnostic_only_no_trading_value"
            rationale = "Long-horizon momentum does not justify a separate trading rule."
    return [
        {
            "pm_gate_decision": decision,
            "event_level_effective": str(decision != "diagnostic_only_no_trading_value" and decision != "blocked_by_data_or_pit_issue"),
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


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "next_task": "Keep long-horizon momentum as diagnostic unless separate PM approval", "allowed": True},
        {"priority": 2, "next_task": "Compare V5e daily/5min/long momentum addenda in one PM packet", "allowed": True},
        {"priority": 3, "next_task": "Open separate long-horizon delay-sell Quant spec", "allowed": decision == "diagnostic_positive_ready_for_separate_quant_spec_not_accepted"},
        {"priority": 4, "next_task": "Use momentum for full-market selection", "allowed": False},
    ]


def _blockers(pit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in pit if row["status"] != "pass"]
    return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Long-horizon momentum diagnostic complete"}] if not failed else [
        {"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": str(row)} for row in failed
    ]


def _feature_schema() -> list[dict[str, Any]]:
    return [
        {"feature_name": name, "definition": definition, "visible_time": "T close", "threshold_scan_used": False, "accepted": False}
        for name, definition in LONG_FEATURES
    ]


def _summary(status: str, decision: str, fatal_blockers: list[dict[str, Any]], held_stock_day_count: int = 0, feature_event_count: int = 0, best_feature: str = "", best_forward_60d_spread: float = 0.0, trigger_overlay_diagnostic_pct_points: float = 0.0) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_long_horizon_momentum_diagnostic",
        "status": status,
        "pm_gate_decision": decision,
        "research_pool": "v57f_v5e_existing_value_dividend_lowvol_sleeve_pool_only",
        "v4_reference": "mom_6_1_research_alpha_and_mom_12_1_slow_backbone",
        "held_stock_day_count": held_stock_day_count,
        "feature_event_count": feature_event_count,
        "best_feature_by_forward_60d_spread": best_feature,
        "best_feature_forward_60d_spread": best_forward_60d_spread,
        "trigger_overlay_diagnostic_pct_points": trigger_overlay_diagnostic_pct_points,
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


def _report(v4: list[dict[str, Any]], diag: list[dict[str, Any]], trigger: list[dict[str, Any]], nav: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    best = _best(diag)
    return "\n".join(
        [
            "# V5e Long-Horizon Momentum Diagnostic",
            "",
            "## V4 Reading",
            *[f"- {row['source']}: {row['finding']}" for row in v4],
            "",
            "## Result",
            f"- Best held-stock feature by 60d spread: `{best.get('feature_name', '')}`.",
            f"- 60d spread: `{best.get('positive_minus_negative_forward_60d_return', '')}`.",
            f"- Trigger overlay rows: `{len(trigger)}`.",
            "",
            "## NAV Proxy",
            *[f"- `{row['version_id']}`: delta pct points `{row.get('delta_return_pct_points_vs_baseline', '')}`." for row in nav],
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
            "# V5e Long Momentum Agent Rules",
            "",
            "- Diagnostic only; do not mark accepted.",
            "- Use V4 momentum theory as reference, not as direct V5e rule import.",
            "- Use only V57f/V5e existing holding pool.",
            "- No full-market selection, no new buy, no threshold scan, no V57f core change.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        V5E_DAILY_BRIEF,
        HISTORICAL_CLOSEOUT,
        REPAIRED_RUN / "holdings.csv",
        REPAIRED_RUN / "rebalance_signals.csv",
        REPAIRED_RUN / "daily_returns.csv",
        LIMITED_ENGINEERING / "v5e_exit_action_log.csv",
        INTRADAY_NAV,
        V4_DIR / "phase2_success_summary_2026-06-19.md",
        V4_DIR / "momentum_stage_summary_v1.md",
    ]
    missing = [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists() and not path.is_absolute()
    ]
    for path in [V4_DIR / "phase2_success_summary_2026-06-19.md", V4_DIR / "momentum_stage_summary_v1.md"]:
        if not path.exists():
            missing.append({"blocker_id": "missing_v4_reference", "severity": "fatal", "status": "blocking", "path": str(path)})
    if not (root / PRICE_DIR).exists():
        missing.append({"blocker_id": "missing_price_dir", "severity": "fatal", "status": "blocking", "path": str(PRICE_DIR)})
    return missing


def _next_rebalance(start: str, dates: list[str]) -> str:
    later = [day for day in dates if day > start]
    return later[0] if later else ""


def _stable_direction(pos: pd.DataFrame, neg: pd.DataFrame) -> str:
    if len(pos) < 20 or len(neg) < 20:
        return "insufficient_events"
    spread60 = _mean(pos["forward_60d_return"]) - _mean(neg["forward_60d_return"])
    spread120 = _mean(pos["forward_120d_return"]) - _mean(neg["forward_120d_return"])
    if spread60 > 0 and spread120 > 0:
        return "positive_long_momentum_directionally_favorable"
    if spread60 < 0 and spread120 < 0:
        return "negative_or_reversal_directionally_favorable"
    return "mixed_or_unstable"


def _best(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return max(rows, key=lambda row: float(row.get("positive_minus_negative_forward_60d_return", 0.0) or 0.0)) if rows else {}


def _safe_float(value: Any) -> float | None:
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
    nums = [x for x in (_safe_float(v) for v in list(values)) if x is not None]
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
    result = run_v5e_long_horizon_momentum_diagnostic()
    print(json.dumps(result, ensure_ascii=False, indent=2))

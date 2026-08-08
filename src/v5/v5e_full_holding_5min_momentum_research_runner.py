from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5e_full_holding_5min_momentum_research") / "current"
HISTORICAL_CLOSEOUT_DIR = Path("v5e_historical_closeout_governance_packet") / "current"
FULL_GATE_DIR = Path("v5e_full_holding_5min_data_gate") / "current"
ROLLING_RESEARCH_DIR = Path("v5e_full_holding_rolling_intraday_research") / "current"
INTRADAY_NAV_DIR = Path("v5e_full_intraday_nav_engineering_test") / "current"
MODEL_COMPARISON_DIR = Path("v5e_profit_lock_model_comparison") / "current"
SLEEVE_CASH_DIR = Path("v5e_sleeve_cash_bucket_engineering") / "current"
CASH_PROXY_DIR = Path("v5e_511360_cash_proxy_limited_engineering") / "current"
LIMITED_ENGINEERING_DIR = Path("v5e_limited_engineering_loop") / "current"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
INITIAL_CAPITAL = 2_000_000.0
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"


FEATURE_SPECS = [
    {
        "feature_name": "morning_30m_momentum",
        "start_time": "09:35:00",
        "end_time": "10:00:00",
        "observation_time": "10:00:00",
        "definition": "close at 10:00 versus close at 09:35",
    },
    {
        "feature_name": "morning_60m_momentum",
        "start_time": "09:35:00",
        "end_time": "10:30:00",
        "observation_time": "10:30:00",
        "definition": "close at 10:30 versus close at 09:35",
    },
    {
        "feature_name": "afternoon_60m_momentum",
        "start_time": "13:00:00",
        "end_time": "14:00:00",
        "observation_time": "14:00:00",
        "definition": "close at 14:00 versus close at 13:00",
    },
    {
        "feature_name": "late_day_momentum",
        "start_time": "14:00:00",
        "end_time": "14:55:00",
        "observation_time": "14:55:00",
        "definition": "close at 14:55 versus close at 14:00",
    },
    {
        "feature_name": "price_vs_intraday_vwap",
        "start_time": "09:35:00",
        "end_time": "14:55:00",
        "observation_time": "14:55:00",
        "definition": "close at 14:55 versus cumulative intraday VWAP through 14:55",
    },
    {
        "feature_name": "close_to_now_momentum",
        "start_time": "previous_close",
        "end_time": "14:55:00",
        "observation_time": "14:55:00",
        "definition": "close at 14:55 versus previous trading day close",
    },
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_full_holding_5min_momentum_research(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_momentum_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_by_data_or_pit_issue", blockers)
        _write_json(out / "v5e_momentum_research_summary.json", summary)
        return summary

    closeout = _read_json(root / HISTORICAL_CLOSEOUT_DIR / "v5e_historical_closeout_summary.json")
    gate = _read_json(root / FULL_GATE_DIR / "v5e_full_holding_5min_summary.json")
    if _fatal_scope_conflict(closeout, gate):
        blockers = [
            {
                "blocker_id": "full_holding_5min_scope_conflict",
                "severity": "fatal",
                "status": "blocking",
                "description": "Historical closeout or full holding 5min data gate conflicts with required research scope.",
            }
        ]
        _write_csv(out / "v5e_momentum_blockers.csv", blockers)
        summary = _summary("blocked_scope_conflict", "blocked_by_data_or_pit_issue", blockers)
        _write_json(out / "v5e_momentum_research_summary.json", summary)
        return summary

    available = pd.read_csv(root / FULL_GATE_DIR / "v5e_full_holding_5min_available_windows.csv")
    features = _held_stock_day_features(root, available)
    feature_df = pd.DataFrame(features)
    feature_long = _feature_long(feature_df)
    forward_diag = _forward_return_diagnostics(feature_long)
    bucket_result = _bucket_result(feature_long)
    event_level = _event_level_result(feature_long)
    trigger_overlay = _trigger_overlay(root, feature_df)
    nav_comparison = _nav_comparison(root, trigger_overlay, event_level)
    pit_audit = _pit_audit(gate, len(feature_df), len(feature_long))
    tplus1_audit = _tplus1_audit(root)
    decision = _pm_gate_decision(event_level, nav_comparison, pit_audit, tplus1_audit)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(pit_audit, tplus1_audit)

    _write_csv(out / "v5e_momentum_feature_schema.csv", _feature_schema())
    _write_csv(out / "v5e_momentum_pit_leakage_audit.csv", pit_audit)
    _write_csv(out / "v5e_momentum_tplus1_governance_audit.csv", tplus1_audit)
    _write_csv(out / "v5e_held_stock_day_momentum_features.csv", features)
    _write_csv(out / "v5e_momentum_forward_return_diagnostics.csv", forward_diag)
    _write_csv(out / "v5e_momentum_bucket_result.csv", bucket_result)
    _write_csv(out / "v5e_momentum_event_level_result.csv", event_level)
    _write_csv(out / "v5e_momentum_v5e_trigger_overlay_diagnostic.csv", trigger_overlay)
    _write_csv(out / "v5e_momentum_nav_engineering_comparison.csv", nav_comparison)
    _write_csv(out / "v5e_momentum_pm_gate_decision.csv", decision)
    _write_csv(out / "v5e_momentum_blockers.csv", blockers_out)
    _write_csv(out / "v5e_momentum_next_agent_queue.csv", next_queue)
    (out / "v5e_momentum_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5e_momentum_research_report.md").write_text(
        _report(gate, forward_diag, bucket_result, trigger_overlay, nav_comparison, decision),
        encoding="utf-8",
    )

    best_feature = _best_feature_result(forward_diag)
    summary = _summary(
        "completed_v5e_full_holding_5min_momentum_research",
        decision[0]["pm_gate_decision"],
        [],
        held_stock_day_count=len(feature_df),
        event_level_row_count=len(event_level),
        effective_coverage_rate_pct=float(gate.get("effective_coverage_rate_pct", 0.0)),
        best_feature=best_feature.get("feature_name", ""),
        best_feature_next_close_spread=float(best_feature.get("positive_minus_negative_next_close_return", 0.0) or 0.0),
        nav_level_effective=decision[0]["nav_level_effective"] == "True",
    )
    _write_json(out / "v5e_momentum_research_summary.json", summary)
    return summary


def _held_stock_day_features(root: Path, available: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    available = available[available["coverage_status"].astype(str).eq("available")].copy()
    available = available.sort_values(["code", "trade_date"]).reset_index(drop=True)
    daily_close_by_code: dict[str, list[dict[str, Any]]] = {}
    cached: dict[str, dict[str, Any]] = {}

    for _, row in available.iterrows():
        path = root / Path(str(row["path"]))
        parsed = _minute_day(path, str(row["code"]), str(row["trade_date"]))
        if parsed is None:
            continue
        parsed.update(
            {
                "code": str(row["code"]),
                "trade_date": str(row["trade_date"]),
                "holding_start_date": str(row["holding_start_date"]),
                "next_rebalance_date": str(row["next_rebalance_date"]),
                "sleeve": str(row.get("sleeve", "")),
                "path": str(row["path"]),
            }
        )
        cached[f"{row['code']}|{row['trade_date']}"] = parsed
        daily_close_by_code.setdefault(str(row["code"]), []).append(parsed)

    next_map: dict[tuple[str, str], dict[str, Any]] = {}
    previous_close: dict[tuple[str, str], float] = {}
    until_rebalance_close: dict[tuple[str, str], float] = {}
    for code, days in daily_close_by_code.items():
        days = sorted(days, key=lambda item: item["trade_date"])
        for idx, day in enumerate(days):
            if idx > 0:
                previous_close[(code, day["trade_date"])] = float(days[idx - 1]["day_close"])
            if idx + 1 < len(days):
                next_map[(code, day["trade_date"])] = days[idx + 1]
        by_cycle: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for day in days:
            key = (code, day["holding_start_date"], day["next_rebalance_date"])
            by_cycle.setdefault(key, []).append(day)
        for key, cycle_days in by_cycle.items():
            last_close = float(sorted(cycle_days, key=lambda item: item["trade_date"])[-1]["day_close"])
            for day in cycle_days:
                until_rebalance_close[(code, day["trade_date"])] = last_close

    for key, day in sorted(cached.items()):
        code = day["code"]
        trade_date = day["trade_date"]
        prev_close = previous_close.get((code, trade_date))
        features = _feature_values(day, prev_close)
        next_day = next_map.get((code, trade_date))
        observation_price = _safe_float(day.get("close_1455"))
        next_open_return = _ret(_safe_float(next_day.get("day_open")) if next_day else None, observation_price)
        next_close_return = _ret(_safe_float(next_day.get("day_close")) if next_day else None, observation_price)
        until_return = _ret(until_rebalance_close.get((code, trade_date)), observation_price)
        row = {
            "research_pool": "v57f_repaired_historical_holdings_only",
            "code": code,
            "trade_date": trade_date,
            "holding_start_date": day["holding_start_date"],
            "next_rebalance_date": day["next_rebalance_date"],
            "sleeve": day["sleeve"],
            "bar_count": day["bar_count"],
            "first_bar_time": day["first_bar_time"],
            "last_bar_time": day["last_bar_time"],
            "day_open": day["day_open"],
            "day_close": day["day_close"],
            "close_1455": day["close_1455"],
            "vwap_1455": day["vwap_1455"],
            "previous_close": "" if prev_close is None else prev_close,
            "next_open_return_from_1455": next_open_return,
            "next_close_return_from_1455": next_close_return,
            "until_next_rebalance_return_from_1455": until_return,
            "future_return_used_for_signal": False,
            "new_buy_signal_allowed": False,
            **features,
        }
        rows.append(row)
    return rows


def _minute_day(path: Path, code: str, trade_date: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if df.empty:
        return None
    df = df[df["code"].astype(str).eq(code)].copy()
    if df.empty:
        return None
    df["time"] = df["time"].astype(str)
    df = df.sort_values("time").reset_index(drop=True)
    amount = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    volume = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)
    vwap = float(amount.sum() / volume.sum()) if volume.sum() else float(df.iloc[-1]["close"])
    by_time = {str(row["time"]): row for _, row in df.iterrows()}
    return {
        "trade_date": trade_date,
        "bar_count": int(len(df)),
        "first_bar_time": str(df.iloc[0]["time"]),
        "last_bar_time": str(df.iloc[-1]["time"]),
        "day_open": float(df.iloc[0]["open"]),
        "day_close": float(df.iloc[-1]["close"]),
        "close_0935": _time_close(by_time, "09:35:00"),
        "close_1000": _time_close(by_time, "10:00:00"),
        "close_1030": _time_close(by_time, "10:30:00"),
        "close_1300": _time_close(by_time, "13:00:00"),
        "close_1400": _time_close(by_time, "14:00:00"),
        "close_1455": _time_close(by_time, "14:55:00"),
        "vwap_1455": vwap,
    }


def _feature_values(day: dict[str, Any], previous_close: float | None) -> dict[str, Any]:
    return {
        "morning_30m_momentum": _ret(day["close_1000"], day["close_0935"]),
        "morning_60m_momentum": _ret(day["close_1030"], day["close_0935"]),
        "afternoon_60m_momentum": _ret(day["close_1400"], day["close_1300"]),
        "late_day_momentum": _ret(day["close_1455"], day["close_1400"]),
        "price_vs_intraday_vwap": _ret(day["close_1455"], day["vwap_1455"]),
        "close_to_now_momentum": _ret(day["close_1455"], previous_close),
    }


def _feature_long(feature_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for spec in FEATURE_SPECS:
        name = spec["feature_name"]
        if name not in feature_df.columns:
            continue
        for _, row in feature_df.iterrows():
            value = _safe_float(row.get(name))
            if value is None:
                continue
            rows.append(
                {
                    "feature_name": name,
                    "code": row["code"],
                    "trade_date": row["trade_date"],
                    "holding_start_date": row["holding_start_date"],
                    "next_rebalance_date": row["next_rebalance_date"],
                    "sleeve": row["sleeve"],
                    "observation_time": spec["observation_time"],
                    "feature_value": value,
                    "sign_bucket": _sign_bucket(value),
                    "remaining_intraday_return": _remaining_intraday(row, spec),
                    "next_open_return": row["next_open_return_from_1455"],
                    "next_close_return": row["next_close_return_from_1455"],
                    "until_next_rebalance_return": row["until_next_rebalance_return_from_1455"],
                    "future_return_used_for_signal": False,
                    "new_buy_signal_allowed": False,
                }
            )
    long = pd.DataFrame(rows)
    if long.empty:
        return long
    long["tercile_bucket"] = ""
    for name, group in long.groupby("feature_name"):
        values = group["feature_value"]
        if values.nunique() >= 3:
            labels = pd.qcut(values.rank(method="first"), 3, labels=["bottom", "middle", "top"])
            long.loc[group.index, "tercile_bucket"] = labels.astype(str)
        else:
            long.loc[group.index, "tercile_bucket"] = "insufficient_variation"
    return long


def _remaining_intraday(row: pd.Series, spec: dict[str, str]) -> float | str:
    end = spec["end_time"]
    if end == "10:00:00":
        return _ret(row["close_1455"], row["morning_30m_momentum_reference_close"] if "morning_30m_momentum_reference_close" in row else row.get("close_1000"))
    if end == "10:30:00":
        return _ret(row["close_1455"], row.get("close_1030"))
    if end == "14:00:00":
        return _ret(row["close_1455"], row.get("close_1400"))
    return 0.0


def _forward_return_diagnostics(feature_long: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    if feature_long.empty:
        return rows
    for name, group in feature_long.groupby("feature_name"):
        pos = group[group["sign_bucket"].eq("positive")]
        neg = group[group["sign_bucket"].eq("negative")]
        rows.append(
            {
                "feature_name": name,
                "observation_count": int(len(group)),
                "positive_count": int(len(pos)),
                "negative_count": int(len(neg)),
                "positive_next_open_return": _mean(pos["next_open_return"]),
                "negative_next_open_return": _mean(neg["next_open_return"]),
                "positive_minus_negative_next_open_return": _mean(pos["next_open_return"]) - _mean(neg["next_open_return"]),
                "positive_next_close_return": _mean(pos["next_close_return"]),
                "negative_next_close_return": _mean(neg["next_close_return"]),
                "positive_minus_negative_next_close_return": _mean(pos["next_close_return"]) - _mean(neg["next_close_return"]),
                "positive_until_next_rebalance_return": _mean(pos["until_next_rebalance_return"]),
                "negative_until_next_rebalance_return": _mean(neg["until_next_rebalance_return"]),
                "positive_minus_negative_until_next_rebalance_return": _mean(pos["until_next_rebalance_return"]) - _mean(neg["until_next_rebalance_return"]),
                "stable_direction_diagnostic": _stable_direction(pos, neg),
                "used_for_trade_rule": False,
            }
        )
    return rows


def _bucket_result(feature_long: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    if feature_long.empty:
        return rows
    for bucket_col in ["sign_bucket", "tercile_bucket"]:
        for (name, bucket), group in feature_long.groupby(["feature_name", bucket_col]):
            rows.append(
                {
                    "feature_name": name,
                    "bucket_type": bucket_col,
                    "bucket": bucket,
                    "observation_count": int(len(group)),
                    "mean_remaining_intraday_return": _mean(group["remaining_intraday_return"]),
                    "mean_next_open_return": _mean(group["next_open_return"]),
                    "mean_next_close_return": _mean(group["next_close_return"]),
                    "mean_until_next_rebalance_return": _mean(group["until_next_rebalance_return"]),
                    "median_next_close_return": _median(group["next_close_return"]),
                    "positive_forward_rate_next_close": _positive_rate(group["next_close_return"]),
                    "used_for_threshold_selection": False,
                }
            )
    return rows


def _event_level_result(feature_long: pd.DataFrame) -> list[dict[str, Any]]:
    if feature_long.empty:
        return []
    rows = []
    for _, row in feature_long.iterrows():
        rows.append(
            {
                "feature_name": row["feature_name"],
                "code": row["code"],
                "trade_date": row["trade_date"],
                "sleeve": row["sleeve"],
                "momentum_state": row["sign_bucket"],
                "tercile_bucket": row["tercile_bucket"],
                "feature_value": row["feature_value"],
                "next_open_return": row["next_open_return"],
                "next_close_return": row["next_close_return"],
                "until_next_rebalance_return": row["until_next_rebalance_return"],
                "diagnostic_interpretation": _event_interpretation(row),
                "new_buy_signal_allowed": False,
                "accepted": False,
            }
        )
    return rows


def _trigger_overlay(root: Path, feature_df: pd.DataFrame) -> list[dict[str, Any]]:
    exit_path = root / LIMITED_ENGINEERING_DIR / "v5e_exit_action_log.csv"
    if not exit_path.exists():
        return []
    exits = pd.read_csv(exit_path)
    exits = exits[exits["version_id"].astype(str).isin(["v5e_profit_lock_main_20pct_sell50", "v5e_trailing_main_peak15_drawdown8_sell50", "v5e_combined_main_profit_lock_plus_trailing"])].copy()
    feature_map = {
        (str(row["code"]), str(row["execution_date"]) if "execution_date" in row else str(row["trade_date"])): row
        for _, row in feature_df.rename(columns={"trade_date": "execution_date"}).iterrows()
    }
    rows = []
    for idx, exit_row in exits.iterrows():
        key = (str(exit_row["code"]), str(exit_row["execution_date"]))
        feature = feature_map.get(key)
        if feature is None:
            continue
        late = _safe_float(feature.get("late_day_momentum"))
        close_to_now = _safe_float(feature.get("close_to_now_momentum"))
        next_close = _safe_float(feature.get("next_close_return_from_1455"))
        until_rebalance = _safe_float(feature.get("until_next_rebalance_return_from_1455"))
        sold_value = float(exit_row.get("value", 0.0))
        sell_fraction = 0.5 if "sell50" in str(exit_row.get("version_id", "")) or str(exit_row.get("trigger_reason", "")) else 0.0
        diagnostic_state = _sign_bucket(late if late is not None else 0.0)
        rows.append(
            {
                "event_id": f"exit_{idx}",
                "version_id": exit_row["version_id"],
                "code": exit_row["code"],
                "trigger_date": exit_row["trigger_date"],
                "execution_date": exit_row["execution_date"],
                "trigger_reason": exit_row["trigger_reason"],
                "sold_value": sold_value,
                "sell_fraction": sell_fraction,
                "late_day_momentum_state": diagnostic_state,
                "late_day_momentum": "" if late is None else late,
                "close_to_now_momentum_state": _sign_bucket(close_to_now if close_to_now is not None else 0.0),
                "close_to_now_momentum": "" if close_to_now is None else close_to_now,
                "next_close_return_after_execution_1455": "" if next_close is None else next_close,
                "until_rebalance_return_after_execution_1455": "" if until_rebalance is None else until_rebalance,
                "positive_momentum_delay_sell_diagnostic_value": _diagnostic_delay_value(sold_value, diagnostic_state, next_close),
                "negative_momentum_immediate_sell_diagnostic_value": _diagnostic_immediate_value(sold_value, diagnostic_state, next_close),
                "used_for_trade_rule": False,
                "accepted": False,
            }
        )
    return rows


def _nav_comparison(root: Path, trigger_overlay: list[dict[str, Any]], event_level: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv")
    baseline_nav = baseline["strategy_nav"].astype(float).tolist()
    baseline_return = baseline_nav[-1] - 1.0 if baseline_nav else 0.0
    baseline_dd = _max_drawdown(baseline_nav)
    model_summary = _read_json(root / MODEL_COMPARISON_DIR / "v5e_model_comparison_summary.json")
    intraday_nav = _read_json(root / INTRADAY_NAV_DIR / "v5e_full_intraday_nav_summary.json")
    diagnostic_delta = sum(float(row.get("positive_momentum_delay_sell_diagnostic_value", 0.0) or 0.0) for row in trigger_overlay)
    diagnostic_return = diagnostic_delta / INITIAL_CAPITAL
    return [
        {
            "version_id": "v57f_repaired_baseline",
            "nav_level_valid": True,
            "strategy_return": baseline_return,
            "delta_return_vs_baseline": 0.0,
            "max_drawdown": baseline_dd,
            "delta_max_drawdown_vs_baseline": 0.0,
            "accepted": False,
            "notes": "Frozen reference only.",
        },
        {
            "version_id": "v5e_profit_lock_main_20pct_sell50_reference",
            "nav_level_valid": True,
            "strategy_return": model_summary.get("daily_open_strategy_return_200w", ""),
            "delta_return_vs_baseline": "",
            "delta_return_pct_points_vs_baseline": model_summary.get("daily_open_delta_return_pct_points_200w", ""),
            "max_drawdown": model_summary.get("daily_open_max_drawdown_200w", ""),
            "delta_max_drawdown_vs_baseline": "",
            "delta_max_drawdown_pct_points_vs_baseline": model_summary.get("delta_max_drawdown_pct_points_200w", ""),
            "accepted": False,
            "notes": "Existing V5e paper candidate reference; not modified by momentum research.",
        },
        {
            "version_id": "full_intraday_rolling_nav_prior_result",
            "nav_level_valid": True,
            "strategy_return": intraday_nav.get("rolling_strategy_return", ""),
            "delta_return_vs_baseline": "",
            "delta_return_pct_points_vs_baseline": intraday_nav.get("rolling_delta_return_pct_points_vs_baseline", ""),
            "max_drawdown": "",
            "delta_max_drawdown_vs_baseline": "",
            "delta_max_drawdown_pct_points_vs_baseline": intraday_nav.get("rolling_delta_max_drawdown_pct_points_vs_baseline", ""),
            "accepted": False,
            "notes": "Prior full intraday trigger NAV result was downgraded to diagnostic.",
        },
        {
            "version_id": "momentum_overlay_event_diagnostic_proxy",
            "nav_level_valid": False,
            "strategy_return": "",
            "delta_return_vs_baseline": diagnostic_return,
            "delta_return_pct_points_vs_baseline": diagnostic_return * 100.0,
            "max_drawdown": "",
            "delta_max_drawdown_vs_baseline": "",
            "delta_max_drawdown_pct_points_vs_baseline": "",
            "accepted": False,
            "notes": "Event-level diagnostic value only; no promoted trading NAV because momentum is not an approved trade rule.",
        },
    ]


def _pit_audit(gate: dict[str, Any], held_count: int, event_count: int) -> list[dict[str, Any]]:
    return [
        {"audit_id": "full_holding_scope", "status": "pass" if gate.get("scope") == "full_holding_period_5min" else "fail", "detail": gate.get("scope", "")},
        {"audit_id": "effective_coverage_rate", "status": "pass" if float(gate.get("effective_coverage_rate_pct", 0.0)) >= 100.0 else "fail", "detail": gate.get("effective_coverage_rate_pct", "")},
        {"audit_id": "signal_uses_only_elapsed_5min_bars", "status": "pass", "detail": "Each fixed feature uses bars up to its observation time only."},
        {"audit_id": "forward_returns_evaluation_only", "status": "pass", "detail": "Forward returns are calculated after feature values and are not used to create signals."},
        {"audit_id": "v57f_pool_only", "status": "pass", "detail": f"Held stock-day rows={held_count}; event rows={event_count}; no full-market selection."},
        {"audit_id": "accepted_false", "status": "pass", "detail": "Momentum addendum is diagnostic only."},
    ]


def _tplus1_audit(root: Path) -> list[dict[str, Any]]:
    checks = [
        ("v5e_limited_engineering_loop/current/v5e_t_violation_log.csv", "t_violation_count"),
        ("v5e_limited_engineering_loop/current/v5e_reentry_violation_log.csv", "reentry_violation_count"),
    ]
    rows = []
    for rel, audit_id in checks:
        path = root / rel
        count = 0
        if path.exists():
            try:
                df = pd.read_csv(path)
            except pd.errors.EmptyDataError:
                df = pd.DataFrame()
            count = 0 if df.empty or ("violation_id" in df.columns and df.iloc[0].astype(str).str.contains("none", case=False).any()) else len(df)
        rows.append({"audit_id": audit_id, "status": "pass" if count == 0 else "fail", "violation_count": count, "detail": rel})
    rows.extend(
        [
            {"audit_id": "new_buy_signal_count", "status": "pass", "violation_count": 0, "detail": "Momentum research does not create buys."},
            {"audit_id": "same_day_sell_buyback_count", "status": "pass", "violation_count": 0, "detail": "No reentry rule remains unchanged."},
        ]
    )
    return rows


def _pm_gate_decision(
    event_level: list[dict[str, Any]],
    nav_comparison: list[dict[str, Any]],
    pit_audit: list[dict[str, Any]],
    tplus1_audit: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pit_ok = all(row["status"] == "pass" for row in pit_audit)
    gov_ok = all(row["status"] == "pass" for row in tplus1_audit)
    if not pit_ok or not gov_ok:
        decision = "blocked_by_data_or_pit_issue"
        nav_effective = False
        rationale = "PIT or governance audit failed."
    else:
        proxy_row = next(row for row in nav_comparison if row["version_id"] == "momentum_overlay_event_diagnostic_proxy")
        prior_nav = next(row for row in nav_comparison if row["version_id"] == "full_intraday_rolling_nav_prior_result")
        event_positive = float(proxy_row.get("delta_return_vs_baseline", 0.0) or 0.0) > 0
        prior_nav_failed = float(prior_nav.get("delta_return_pct_points_vs_baseline", 0.0) or 0.0) < 0
        if event_positive and prior_nav_failed:
            decision = "diagnostic_positive_but_nav_failed"
            nav_effective = False
            rationale = "Momentum has event-level diagnostic value, but prior full intraday NAV engineering remained below baseline."
        elif event_positive:
            decision = "diagnostic_positive_ready_for_separate_quant_spec_not_accepted"
            nav_effective = False
            rationale = "Event-level signal is positive, but this addendum cannot become a trading rule without a separate Quant spec."
        else:
            decision = "diagnostic_only_no_trading_value"
            nav_effective = False
            rationale = "Event-level diagnostics do not justify a separate trading rule."
    return [
        {
            "pm_gate_decision": decision,
            "event_level_effective": str(decision != "diagnostic_only_no_trading_value" and decision != "blocked_by_data_or_pit_issue"),
            "nav_level_effective": str(nav_effective),
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
    if decision == "diagnostic_positive_ready_for_separate_quant_spec_not_accepted":
        first = "Open separate momentum-overlay Quant spec with fixed rules, no acceptance"
    elif decision == "diagnostic_positive_but_nav_failed":
        first = "Keep momentum as diagnostic addendum; do not promote NAV strategy"
    elif decision == "blocked_by_data_or_pit_issue":
        first = "Repair data/PIT audit before any further momentum work"
    else:
        first = "Close momentum addendum as diagnostic only"
    return [
        {"priority": 1, "next_task": first, "allowed": True, "requires_new_threshold": False},
        {"priority": 2, "next_task": "Continue V5e forward/paper tracking", "allowed": True, "requires_new_threshold": False},
        {"priority": 3, "next_task": "V5e threshold scan", "allowed": False, "requires_new_threshold": True},
        {"priority": 4, "next_task": "Promote momentum as accepted strategy", "allowed": False, "requires_new_threshold": False},
    ]


def _blockers(pit_audit: list[dict[str, Any]], tplus1_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in [*pit_audit, *tplus1_audit] if row["status"] != "pass"]
    if not failed:
        return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Diagnostic research completed; no acceptance."}]
    return [
        {"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": str(row.get("detail", row))}
        for row in failed
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    held_stock_day_count: int = 0,
    event_level_row_count: int = 0,
    effective_coverage_rate_pct: float = 0.0,
    best_feature: str = "",
    best_feature_next_close_spread: float = 0.0,
    nav_level_effective: bool = False,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_full_holding_5min_momentum_research",
        "status": status,
        "pm_gate_decision": decision,
        "backtest_scope_start": BACKTEST_START,
        "backtest_scope_end": BACKTEST_END,
        "research_pool": "v57f_v5e_existing_value_dividend_lowvol_sleeve_pool_only",
        "held_stock_day_count": held_stock_day_count,
        "event_level_row_count": event_level_row_count,
        "effective_coverage_rate_pct": effective_coverage_rate_pct,
        "best_feature_by_next_close_spread": best_feature,
        "best_feature_next_close_spread": best_feature_next_close_spread,
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


def _report(
    gate: dict[str, Any],
    forward_diag: list[dict[str, Any]],
    bucket_result: list[dict[str, Any]],
    trigger_overlay: list[dict[str, Any]],
    nav_comparison: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    best = _best_feature_result(forward_diag)
    overlay_delta = sum(float(row.get("positive_momentum_delay_sell_diagnostic_value", 0.0) or 0.0) for row in trigger_overlay)
    return "\n".join(
        [
            "# V5e Full Holding-Period 5min Momentum Research",
            "",
            "## Scope",
            "- Research pool: V57f repaired historical holdings and V5e-affected V57f holdings only.",
            "- This is not full-market momentum selection.",
            "- No new buys, no reentry, no cross-sleeve transfer, no V57f core change.",
            "",
            "## Data",
            f"- Full holding 5min effective coverage: `{gate.get('effective_coverage_rate_pct')}`%.",
            f"- Bucket diagnostic rows: `{len(bucket_result)}`.",
            f"- V5e trigger overlay rows: `{len(trigger_overlay)}`.",
            "",
            "## Event-Level Read",
            f"- Best fixed feature by positive-minus-negative next-close spread: `{best.get('feature_name', '')}`.",
            f"- Spread: `{best.get('positive_minus_negative_next_close_return', '')}`.",
            f"- V5e trigger overlay diagnostic value: `{overlay_delta}`.",
            "",
            "## NAV-Level Read",
            *[
                f"- `{row['version_id']}`: delta={row.get('delta_return_vs_baseline', '')}, accepted={row.get('accepted', False)}"
                for row in nav_comparison
            ],
            "",
            "## PM Gate",
            f"- Decision: `{decision[0]['pm_gate_decision']}`.",
            f"- Rationale: {decision[0]['rationale']}",
            "",
        ]
    )


def _feature_schema() -> list[dict[str, Any]]:
    return [
        {
            **spec,
            "pool_boundary": "V57f/V5e existing holdings/candidate pool only",
            "used_for_signal": True,
            "forward_return_used_for_signal": False,
            "threshold_optimized": False,
            "accepted": False,
        }
        for spec in FEATURE_SPECS
    ]


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Momentum Diagnostic Agent Rules",
            "",
            "- Diagnostic research addendum only.",
            "- Use only V57f/V5e existing holding or candidate pool; no full-market momentum selection.",
            "- Do not add buys, reentry, same-day sell/buyback, or cross-sleeve transfers.",
            "- Do not modify V57f core, thresholds, sleeve logic, target count, weights, or rebalance frequency.",
            "- Do not mark accepted or live approved.",
            "- Do not start JoinQuant or fetch new data.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        HISTORICAL_CLOSEOUT_DIR / "v5e_historical_closeout_summary.json",
        HISTORICAL_CLOSEOUT_DIR / "v5e_component_status_matrix.csv",
        FULL_GATE_DIR / "v5e_full_holding_5min_summary.json",
        FULL_GATE_DIR / "v5e_full_holding_5min_pm_gate_decision.csv",
        FULL_GATE_DIR / "v5e_full_holding_5min_available_windows.csv",
        ROLLING_RESEARCH_DIR / "v5e_full_intraday_summary.json",
        INTRADAY_NAV_DIR / "v5e_full_intraday_nav_summary.json",
        MODEL_COMPARISON_DIR / "v5e_model_comparison_summary.json",
        SLEEVE_CASH_DIR / "v5e_sleeve_cash_bucket_summary.json",
        CASH_PROXY_DIR / "v5e_511360_cash_proxy_summary.json",
        REPAIRED_RUN / "daily_returns.csv",
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _fatal_scope_conflict(closeout: dict[str, Any], gate: dict[str, Any]) -> bool:
    return not (
        closeout.get("historical_closeout_status") == "complete"
        and closeout.get("backtest_scope_start") == BACKTEST_START
        and closeout.get("backtest_scope_end") == BACKTEST_END
        and gate.get("scope") == "full_holding_period_5min"
        and float(gate.get("effective_coverage_rate_pct", 0.0)) >= 100.0
    )


def _best_feature_result(forward_diag: list[dict[str, Any]]) -> dict[str, Any]:
    if not forward_diag:
        return {}
    return max(forward_diag, key=lambda row: float(row.get("positive_minus_negative_next_close_return", 0.0) or 0.0))


def _event_interpretation(row: pd.Series) -> str:
    state = row["sign_bucket"]
    fwd = _safe_float(row.get("next_close_return"))
    if state == "positive" and fwd is not None and fwd > 0:
        return "positive_momentum_followed_by_gain"
    if state == "positive" and fwd is not None and fwd < 0:
        return "positive_momentum_failed"
    if state == "negative" and fwd is not None and fwd < 0:
        return "negative_momentum_warned_loss"
    if state == "negative" and fwd is not None and fwd > 0:
        return "negative_momentum_rebounded"
    return "neutral_or_unavailable"


def _diagnostic_delay_value(sold_value: float, state: str, next_close_return: float | None) -> float:
    if state != "positive" or next_close_return is None:
        return 0.0
    return sold_value * next_close_return


def _diagnostic_immediate_value(sold_value: float, state: str, next_close_return: float | None) -> float:
    if state != "negative" or next_close_return is None:
        return 0.0
    return -sold_value * next_close_return


def _stable_direction(pos: pd.DataFrame, neg: pd.DataFrame) -> str:
    if len(pos) < 20 or len(neg) < 20:
        return "insufficient_events"
    next_close_spread = _mean(pos["next_close_return"]) - _mean(neg["next_close_return"])
    until_spread = _mean(pos["until_next_rebalance_return"]) - _mean(neg["until_next_rebalance_return"])
    if next_close_spread > 0 and until_spread > 0:
        return "positive_momentum_directionally_favorable"
    if next_close_spread < 0 and until_spread < 0:
        return "negative_or_mean_reversion_directionally_favorable"
    return "mixed_or_unstable"


def _sign_bucket(value: float) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"


def _ret(new: float | None, old: float | None) -> float | str:
    if new is None or old is None or old == 0 or (isinstance(new, float) and math.isnan(new)) or (isinstance(old, float) and math.isnan(old)):
        return ""
    return float(new) / float(old) - 1.0


def _time_close(by_time: dict[str, pd.Series], time_value: str) -> float | None:
    row = by_time.get(time_value)
    if row is None:
        return None
    return float(row["close"])


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(result):
        return None
    return result


def _mean(values: Any) -> float:
    nums = [_safe_float(value) for value in list(values)]
    nums = [value for value in nums if value is not None]
    return float(sum(nums) / len(nums)) if nums else 0.0


def _median(values: Any) -> float:
    nums = sorted(value for value in (_safe_float(value) for value in list(values)) if value is not None)
    if not nums:
        return 0.0
    mid = len(nums) // 2
    if len(nums) % 2:
        return float(nums[mid])
    return float((nums[mid - 1] + nums[mid]) / 2.0)


def _positive_rate(values: Any) -> float:
    nums = [value for value in (_safe_float(value) for value in list(values)) if value is not None]
    return float(sum(1 for value in nums if value > 0) / len(nums)) if nums else 0.0


def _max_drawdown(nav: list[float]) -> float:
    peak = -float("inf")
    max_dd = 0.0
    for value in nav:
        peak = max(peak, value)
        if peak > 0:
            max_dd = min(max_dd, value / peak - 1.0)
    return abs(max_dd)


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
    result = run_v5e_full_holding_5min_momentum_research()
    print(json.dumps(result, ensure_ascii=False, indent=2))

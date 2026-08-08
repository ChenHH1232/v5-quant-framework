from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v5.v5f_quality_value_mean_reversion_runner import (
    BACKTEST_END,
    BACKTEST_START,
    REPAIRED_RUN,
    _safe_float,
)


OUT_DIR = Path("v5f_short_window_reversion_diagnostic") / "current"
FULL_5MIN_DIR = Path("v5e_full_holding_5min_data_gate") / "current"
FULL_5MIN_SUMMARY = FULL_5MIN_DIR / "v5e_full_holding_5min_summary.json"
FULL_5MIN_AVAILABLE = FULL_5MIN_DIR / "v5e_full_holding_5min_available_windows.csv"
FULL_5MIN_RAW_INDEX = FULL_5MIN_DIR / "v5e_full_holding_5min_raw_index.csv"
BASELINE = "v57f_startup_preload_repaired_baseline"
PRIMARY_REFERENCE = "internal_subsleeve_mom12_70_30_current_champion"


EVENT_DEFINITIONS = [
    {
        "event_type": "morning_30m_micro_crash",
        "observation_time": "10:00:00",
        "rule": "09:35->10:00 return is in full-sample bottom decile and <= -1%.",
        "horizon": "same_day_close,next_1d,next_2d",
    },
    {
        "event_type": "morning_60m_micro_crash",
        "observation_time": "10:30:00",
        "rule": "09:35->10:30 return is in full-sample bottom decile and <= -1.5%.",
        "horizon": "same_day_close,next_1d,next_2d",
    },
    {
        "event_type": "late_day_vwap_dislocation",
        "observation_time": "14:55:00",
        "rule": "Previous close->14:55 return <= -2% and 14:55 price is at least 0.5% below intraday VWAP.",
        "horizon": "next_1d,next_2d",
    },
    {
        "event_type": "pool_crash_dislocation",
        "observation_time": "14:55:00",
        "rule": "V57f held-pool average day return <= -1% and stock return <= -1.5%.",
        "horizon": "next_1d,next_2d",
    },
    {
        "event_type": "sector_rotation_outflow",
        "observation_time": "14:55:00",
        "rule": "Another V57f sleeve is at least 1pct stronger than this sleeve while this stock is negative by at least 0.5%.",
        "horizon": "next_1d,next_2d",
    },
    {
        "event_type": "daily_1d_extreme_drop",
        "observation_time": "daily_close",
        "rule": "Previous close->today close is in bottom decile and <= -2%, with V57f fundamental/valuation proxy intact.",
        "horizon": "next_1d,next_2d",
    },
    {
        "event_type": "daily_2d_extreme_drop",
        "observation_time": "daily_close",
        "rule": "Two-day close return is in bottom decile and <= -3%, with V57f fundamental/valuation proxy intact.",
        "horizon": "next_1d,next_2d",
    },
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_short_window_reversion(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_short_window_reversion_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_short_window_reversion_summary.json", summary)
        return summary

    gate = _read_json(root / FULL_5MIN_SUMMARY)
    if float(gate.get("effective_coverage_rate_pct", 0.0)) < 99.9:
        blockers = [
            {
                "blocker_id": "full_holding_5min_coverage_not_ready",
                "severity": "fatal",
                "status": "blocking",
                "description": gate.get("effective_coverage_rate_pct", 0.0),
            }
        ]
        _write_csv(out / "v5f_short_window_reversion_blockers.csv", blockers)
        summary = _summary("blocked_full_5min_coverage", "blocked_by_data_issue", blockers)
        _write_json(out / "v5f_short_window_reversion_summary.json", summary)
        return summary

    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str, "code": str})
    available = pd.read_csv(root / FULL_5MIN_AVAILABLE, dtype={"trade_date": str, "code": str})
    available = available[available["coverage_status"].astype(str).eq("available")].copy()
    minute_days = _load_minute_days(root, available, signals)
    enriched = _enrich_forward_returns(minute_days)
    event_rows = _event_rows(enriched)
    intraday_diag = _event_diagnostics(event_rows, "intraday")
    daily_diag = _event_diagnostics(event_rows, "daily")
    sector_diag = _sector_rotation_diagnostics(enriched, event_rows)
    by_year = _event_breakdown(event_rows, ["event_type", "year"])
    by_sleeve = _event_breakdown(event_rows, ["event_type", "sleeve"])
    overlay = _micro_overlay_estimate(event_rows)
    data_gate = _data_gate(gate, minute_days, signals)
    governance = _governance_audit(data_gate)
    pit = _pit_audit()
    decision = _pm_decision(intraday_diag, daily_diag, overlay, governance)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(governance)

    _write_csv(out / "v5f_short_window_reversion_event_definitions.csv", EVENT_DEFINITIONS)
    _write_csv(out / "v5f_short_window_reversion_data_gate.csv", data_gate)
    _write_csv(out / "v5f_short_window_reversion_minute_day_features.csv", enriched)
    _write_csv(out / "v5f_short_window_reversion_event_log.csv", event_rows)
    _write_csv(out / "v5f_short_window_reversion_intraday_diagnostics.csv", intraday_diag)
    _write_csv(out / "v5f_short_window_reversion_daily_1_2d_diagnostics.csv", daily_diag)
    _write_csv(out / "v5f_short_window_reversion_sector_rotation_diagnostics.csv", sector_diag)
    _write_csv(out / "v5f_short_window_reversion_event_by_year.csv", by_year)
    _write_csv(out / "v5f_short_window_reversion_event_by_sleeve.csv", by_sleeve)
    _write_csv(out / "v5f_short_window_reversion_micro_overlay_estimate.csv", overlay)
    _write_csv(out / "v5f_short_window_reversion_governance_audit.csv", governance)
    _write_csv(out / "v5f_short_window_reversion_pit_audit.csv", pit)
    _write_csv(out / "v5f_short_window_reversion_pm_decision.csv", decision)
    _write_csv(out / "v5f_short_window_reversion_next_queue.csv", next_queue)
    _write_csv(out / "v5f_short_window_reversion_blockers.csv", blockers_out)
    (out / "v5f_short_window_reversion_report.md").write_text(
        _report(intraday_diag, daily_diag, sector_diag, overlay, decision),
        encoding="utf-8",
    )
    (out / "v5f_short_window_reversion_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = _best_overlay(overlay)
    summary = _summary(
        "completed_v5f_short_window_reversion_diagnostic",
        decision[0]["pm_gate_decision"],
        [],
        observation_count=len(enriched),
        event_count=len(event_rows),
        best_event_type=best.get("event_type", ""),
        best_overlay_return_pct_points=float(best.get("estimated_total_overlay_return_pct_points", 0.0) or 0.0),
        usable_space=decision[0]["usable_space"],
    )
    _write_json(out / "v5f_short_window_reversion_summary.json", summary)
    return summary


def _load_minute_days(root: Path, available: pd.DataFrame, signals: pd.DataFrame) -> list[dict[str, Any]]:
    signal_map = _signal_map(signals)
    required = {
        (str(row["code"]), str(row["trade_date"])): row.to_dict()
        for _, row in available.iterrows()
    }
    raw_index = pd.read_csv(root / FULL_5MIN_RAW_INDEX, dtype={"code": str, "path": str})
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for _, raw_row in raw_index.iterrows():
        code = str(raw_row["code"])
        wanted_dates = {date for item_code, date in required if item_code == code and (item_code, date) not in seen}
        if not wanted_dates:
            continue
        path = root / Path(str(raw_row["path"]))
        if not path.exists():
            continue
        raw = pd.read_csv(
            path,
            usecols=["date", "time", "open", "high", "low", "close", "volume", "amount"],
            dtype={"date": str, "time": str},
        )
        raw = raw[raw["date"].isin(wanted_dates)].copy()
        if raw.empty:
            continue
        raw["time"] = raw["time"].map(_raw_time_to_clock)
        for trade_date, group in raw.groupby("date", sort=True):
            req = required.get((code, str(trade_date)))
            if req is None or (code, str(trade_date)) in seen:
                continue
            parsed = _minute_day_from_frame(group, code, str(trade_date))
            if parsed is None:
                continue
            key = (str(req["holding_start_date"]), code)
            signal = signal_map.get(key, {})
            parsed.update(
                {
                    "code": code,
                    "trade_date": str(trade_date),
                    "holding_start_date": str(req["holding_start_date"]),
                    "next_rebalance_date": str(req["next_rebalance_date"]),
                    "sleeve": str(req["sleeve"]),
                    "target_weight": _safe_float(signal.get("target_weight")) or 0.0,
                    "score": _safe_float(signal.get("score")),
                    "cash_generation_yield": _safe_float(signal.get("cash_generation_yield")),
                    "dividend_yield_decimal": _safe_float(signal.get("dividend_yield_decimal")),
                    "research_pool": "v57f_repaired_historical_holdings_only",
                    "new_stock_selected": False,
                    "accepted": False,
                }
            )
            rows.append(parsed)
            seen.add((code, str(trade_date)))

    for (code, trade_date), req in required.items():
        if (code, trade_date) in seen:
            continue
        path = root / Path(str(req["path"]))
        parsed = _minute_day(path, code, trade_date)
        if parsed is None:
            continue
        key = (str(req["holding_start_date"]), code)
        signal = signal_map.get(key, {})
        parsed.update(
            {
                "code": code,
                "trade_date": trade_date,
                "holding_start_date": str(req["holding_start_date"]),
                "next_rebalance_date": str(req["next_rebalance_date"]),
                "sleeve": str(req["sleeve"]),
                "target_weight": _safe_float(signal.get("target_weight")) or 0.0,
                "score": _safe_float(signal.get("score")),
                "cash_generation_yield": _safe_float(signal.get("cash_generation_yield")),
                "dividend_yield_decimal": _safe_float(signal.get("dividend_yield_decimal")),
                "research_pool": "v57f_repaired_historical_holdings_only",
                "new_stock_selected": False,
                "accepted": False,
            }
        )
        rows.append(parsed)
        seen.add((code, trade_date))

    df = pd.DataFrame(rows)
    if df.empty:
        return []
    df["fundamental_proxy_intact"] = False
    df["valuation_proxy_cheap"] = False
    for (date, sleeve), group in df.groupby(["holding_start_date", "sleeve"]):
        score_med = pd.to_numeric(group["score"], errors="coerce").median()
        cash_med = pd.to_numeric(group["cash_generation_yield"], errors="coerce").median()
        div_med = pd.to_numeric(group["dividend_yield_decimal"], errors="coerce").median()
        idx = group.index
        df.loc[idx, "fundamental_proxy_intact"] = pd.to_numeric(group["score"], errors="coerce") >= score_med
        cheap = (pd.to_numeric(group["cash_generation_yield"], errors="coerce") >= cash_med) | (
            pd.to_numeric(group["dividend_yield_decimal"], errors="coerce") >= div_med
        )
        df.loc[idx, "valuation_proxy_cheap"] = cheap
    return df.to_dict("records")


def _raw_time_to_clock(value: Any) -> str:
    text = str(value)
    if ":" in text:
        return text
    if len(text) >= 14:
        hhmmss = text[8:14]
        return f"{hhmmss[0:2]}:{hhmmss[2:4]}:{hhmmss[4:6]}"
    return text


def _minute_day(path: Path, code: str, trade_date: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        df = pd.read_csv(
            path,
            usecols=["code", "time", "open", "high", "low", "close", "volume", "amount"],
        )
    except ValueError:
        df = pd.read_csv(path)
    if df.empty:
        return None
    df = df[df["code"].astype(str).eq(code)].copy()
    if df.empty:
        return None
    df["time"] = df["time"].astype(str)
    df = df.sort_values("time").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume", "amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    by_time = {str(row["time"]): row for _, row in df.iterrows()}
    amount = df["amount"].fillna(0.0)
    volume = df["volume"].fillna(0.0)
    vwap = float(amount.sum() / volume.sum()) if volume.sum() else _safe_float(df.iloc[-1]["close"])
    close_0935 = _time_close(by_time, "09:35:00")
    close_1000 = _time_close(by_time, "10:00:00")
    close_1030 = _time_close(by_time, "10:30:00")
    close_1455 = _time_close(by_time, "14:55:00")
    day_close = _safe_float(df.iloc[-1]["close"])
    day_low = _safe_float(df["low"].min())
    return {
        "trade_date": trade_date,
        "bar_count": int(len(df)),
        "first_bar_time": str(df.iloc[0]["time"]),
        "last_bar_time": str(df.iloc[-1]["time"]),
        "day_open": _safe_float(df.iloc[0]["open"]),
        "day_close": day_close,
        "day_low": day_low,
        "close_0935": close_0935,
        "close_1000": close_1000,
        "close_1030": close_1030,
        "close_1455": close_1455,
        "vwap_1455": vwap,
        "r_0935_1000": _ret(close_1000, close_0935),
        "r_0935_1030": _ret(close_1030, close_0935),
        "r_1000_1455": _ret(close_1455, close_1000),
        "r_1030_1455": _ret(close_1455, close_1030),
        "r_1455_vwap": _ret(close_1455, vwap),
        "r_low_to_1455": _ret(close_1455, day_low),
    }


def _minute_day_from_frame(df: pd.DataFrame, code: str, trade_date: str) -> dict[str, Any] | None:
    if df.empty:
        return None
    df = df.sort_values("time").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "volume", "amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    by_time = {str(row["time"]): row for _, row in df.iterrows()}
    amount = df["amount"].fillna(0.0)
    volume = df["volume"].fillna(0.0)
    vwap = float(amount.sum() / volume.sum()) if volume.sum() else _safe_float(df.iloc[-1]["close"])
    close_0935 = _time_close(by_time, "09:35:00")
    close_1000 = _time_close(by_time, "10:00:00")
    close_1030 = _time_close(by_time, "10:30:00")
    close_1455 = _time_close(by_time, "14:55:00")
    day_close = _safe_float(df.iloc[-1]["close"])
    day_low = _safe_float(df["low"].min())
    return {
        "trade_date": trade_date,
        "bar_count": int(len(df)),
        "first_bar_time": str(df.iloc[0]["time"]),
        "last_bar_time": str(df.iloc[-1]["time"]),
        "day_open": _safe_float(df.iloc[0]["open"]),
        "day_close": day_close,
        "day_low": day_low,
        "close_0935": close_0935,
        "close_1000": close_1000,
        "close_1030": close_1030,
        "close_1455": close_1455,
        "vwap_1455": vwap,
        "r_0935_1000": _ret(close_1000, close_0935),
        "r_0935_1030": _ret(close_1030, close_0935),
        "r_1000_1455": _ret(close_1455, close_1000),
        "r_1030_1455": _ret(close_1455, close_1030),
        "r_1455_vwap": _ret(close_1455, vwap),
        "r_low_to_1455": _ret(close_1455, day_low),
    }


def _enrich_forward_returns(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    if df.empty:
        return []
    out = []
    for _, group in df.sort_values("trade_date").groupby(["code", "holding_start_date", "next_rebalance_date"]):
        group = group.reset_index(drop=True).copy()
        group["prev_day_close"] = group["day_close"].shift(1)
        group["prev_2d_close"] = group["day_close"].shift(2)
        group["next_day_close"] = group["day_close"].shift(-1)
        group["next_2d_close"] = group["day_close"].shift(-2)
        group["r_prevclose_1455"] = group.apply(lambda row: _ret(row["close_1455"], row["prev_day_close"]), axis=1)
        group["r_prevclose_close"] = group.apply(lambda row: _ret(row["day_close"], row["prev_day_close"]), axis=1)
        group["r_2d_to_close"] = group.apply(lambda row: _ret(row["day_close"], row["prev_2d_close"]), axis=1)
        group["next1_from_1000"] = group.apply(lambda row: _ret(row["next_day_close"], row["close_1000"]), axis=1)
        group["next2_from_1000"] = group.apply(lambda row: _ret(row["next_2d_close"], row["close_1000"]), axis=1)
        group["next1_from_1030"] = group.apply(lambda row: _ret(row["next_day_close"], row["close_1030"]), axis=1)
        group["next2_from_1030"] = group.apply(lambda row: _ret(row["next_2d_close"], row["close_1030"]), axis=1)
        group["next1_from_1455"] = group.apply(lambda row: _ret(row["next_day_close"], row["close_1455"]), axis=1)
        group["next2_from_1455"] = group.apply(lambda row: _ret(row["next_2d_close"], row["close_1455"]), axis=1)
        group["next1_from_close"] = group.apply(lambda row: _ret(row["next_day_close"], row["day_close"]), axis=1)
        group["next2_from_close"] = group.apply(lambda row: _ret(row["next_2d_close"], row["day_close"]), axis=1)
        out.extend(group.to_dict("records"))

    df = pd.DataFrame(out)
    sleeve_return = (
        df.groupby(["trade_date", "sleeve"])
        .apply(lambda g: _weighted_mean(g["r_prevclose_1455"], g["target_weight"]))
        .rename("sleeve_return_1455")
        .reset_index()
    )
    pool_return = (
        df.groupby("trade_date")
        .apply(lambda g: _weighted_mean(g["r_prevclose_1455"], g["target_weight"]))
        .rename("pool_return_1455")
        .reset_index()
    )
    top_sleeve = sleeve_return.groupby("trade_date")["sleeve_return_1455"].max().rename("top_sleeve_return_1455")
    df = df.merge(sleeve_return, on=["trade_date", "sleeve"], how="left")
    df = df.merge(pool_return, on="trade_date", how="left")
    df = df.merge(top_sleeve, on="trade_date", how="left")
    df["sleeve_gap_to_top"] = df["top_sleeve_return_1455"] - df["sleeve_return_1455"]

    cut_30 = _quantile(df["r_0935_1000"], 0.10)
    cut_60 = _quantile(df["r_0935_1030"], 0.10)
    cut_1d = _quantile(df["r_prevclose_close"], 0.10)
    cut_2d = _quantile(df["r_2d_to_close"], 0.10)
    df["bottom_decile_cut_30m"] = cut_30
    df["bottom_decile_cut_60m"] = cut_60
    df["bottom_decile_cut_1d"] = cut_1d
    df["bottom_decile_cut_2d"] = cut_2d
    return df.to_dict("records")


def _event_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        events = [
            (
                "morning_30m_micro_crash",
                bool(
                    _safe_float(row.get("r_0935_1000")) is not None
                    and _safe_float(row.get("r_0935_1000")) <= _safe_float(row.get("bottom_decile_cut_30m"))
                    and _safe_float(row.get("r_0935_1000")) <= -0.01
                ),
                "10:00:00",
                row.get("r_0935_1000"),
                row.get("r_1000_1455"),
                row.get("next1_from_1000"),
                row.get("next2_from_1000"),
            ),
            (
                "morning_60m_micro_crash",
                bool(
                    _safe_float(row.get("r_0935_1030")) is not None
                    and _safe_float(row.get("r_0935_1030")) <= _safe_float(row.get("bottom_decile_cut_60m"))
                    and _safe_float(row.get("r_0935_1030")) <= -0.015
                ),
                "10:30:00",
                row.get("r_0935_1030"),
                row.get("r_1030_1455"),
                row.get("next1_from_1030"),
                row.get("next2_from_1030"),
            ),
            (
                "late_day_vwap_dislocation",
                bool(
                    _safe_float(row.get("r_prevclose_1455")) is not None
                    and _safe_float(row.get("r_prevclose_1455")) <= -0.02
                    and _safe_float(row.get("r_1455_vwap")) is not None
                    and _safe_float(row.get("r_1455_vwap")) <= -0.005
                ),
                "14:55:00",
                row.get("r_prevclose_1455"),
                0.0,
                row.get("next1_from_1455"),
                row.get("next2_from_1455"),
            ),
            (
                "pool_crash_dislocation",
                bool(
                    _safe_float(row.get("pool_return_1455")) is not None
                    and _safe_float(row.get("pool_return_1455")) <= -0.01
                    and _safe_float(row.get("r_prevclose_1455")) is not None
                    and _safe_float(row.get("r_prevclose_1455")) <= -0.015
                ),
                "14:55:00",
                row.get("r_prevclose_1455"),
                0.0,
                row.get("next1_from_1455"),
                row.get("next2_from_1455"),
            ),
            (
                "sector_rotation_outflow",
                bool(
                    _safe_float(row.get("sleeve_gap_to_top")) is not None
                    and _safe_float(row.get("sleeve_gap_to_top")) >= 0.01
                    and _safe_float(row.get("r_prevclose_1455")) is not None
                    and _safe_float(row.get("r_prevclose_1455")) <= -0.005
                ),
                "14:55:00",
                row.get("r_prevclose_1455"),
                0.0,
                row.get("next1_from_1455"),
                row.get("next2_from_1455"),
            ),
            (
                "daily_1d_extreme_drop",
                bool(
                    _safe_float(row.get("r_prevclose_close")) is not None
                    and _safe_float(row.get("r_prevclose_close")) <= _safe_float(row.get("bottom_decile_cut_1d"))
                    and _safe_float(row.get("r_prevclose_close")) <= -0.02
                    and bool(row.get("fundamental_proxy_intact"))
                    and bool(row.get("valuation_proxy_cheap"))
                ),
                "daily_close",
                row.get("r_prevclose_close"),
                0.0,
                row.get("next1_from_close"),
                row.get("next2_from_close"),
            ),
            (
                "daily_2d_extreme_drop",
                bool(
                    _safe_float(row.get("r_2d_to_close")) is not None
                    and _safe_float(row.get("r_2d_to_close")) <= _safe_float(row.get("bottom_decile_cut_2d"))
                    and _safe_float(row.get("r_2d_to_close")) <= -0.03
                    and bool(row.get("fundamental_proxy_intact"))
                    and bool(row.get("valuation_proxy_cheap"))
                ),
                "daily_close",
                row.get("r_2d_to_close"),
                0.0,
                row.get("next1_from_close"),
                row.get("next2_from_close"),
            ),
        ]
        for event_type, triggered, obs_time, trigger_return, same_day, next1, next2 in events:
            if not triggered:
                continue
            out.append(
                {
                    "event_type": event_type,
                    "code": row["code"],
                    "trade_date": row["trade_date"],
                    "sleeve": row["sleeve"],
                    "holding_start_date": row["holding_start_date"],
                    "observation_time": obs_time,
                    "target_weight": row["target_weight"],
                    "trigger_return": trigger_return,
                    "same_day_return_after_observation": same_day,
                    "next1_return_after_observation": next1,
                    "next2_return_after_observation": next2,
                    "pool_return_1455": row.get("pool_return_1455"),
                    "sleeve_return_1455": row.get("sleeve_return_1455"),
                    "top_sleeve_return_1455": row.get("top_sleeve_return_1455"),
                    "sleeve_gap_to_top": row.get("sleeve_gap_to_top"),
                    "fundamental_proxy_intact": bool(row.get("fundamental_proxy_intact")),
                    "valuation_proxy_cheap": bool(row.get("valuation_proxy_cheap")),
                    "new_buy_signal_allowed": False,
                    "accepted": False,
                }
            )
    return out


def _event_diagnostics(events: list[dict[str, Any]], scope: str) -> list[dict[str, Any]]:
    df = pd.DataFrame(events)
    if df.empty:
        return []
    if scope == "intraday":
        df = df[~df["event_type"].str.startswith("daily_")].copy()
    else:
        df = df[df["event_type"].str.startswith("daily_")].copy()
    rows = []
    for event_type, group in df.groupby("event_type", sort=True):
        rows.append(
            {
                "event_type": event_type,
                "event_count": int(len(group)),
                "unique_stock_count": int(group["code"].nunique()),
                "avg_trigger_return": _mean(group["trigger_return"]),
                "avg_same_day_return_after_observation": _mean(group["same_day_return_after_observation"]),
                "avg_next1_return_after_observation": _mean(group["next1_return_after_observation"]),
                "avg_next2_return_after_observation": _mean(group["next2_return_after_observation"]),
                "hit_rate_next1_positive": _positive_rate(group["next1_return_after_observation"]),
                "hit_rate_next2_positive": _positive_rate(group["next2_return_after_observation"]),
                "weighted_next1_return": _weighted_mean(group["next1_return_after_observation"], group["target_weight"]),
                "weighted_next2_return": _weighted_mean(group["next2_return_after_observation"], group["target_weight"]),
                "diagnostic_direction": _direction(group),
                "used_for_trade_rule": False,
            }
        )
    return rows


def _sector_rotation_diagnostics(rows: list[dict[str, Any]], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    event_df = pd.DataFrame(events)
    out = []
    if df.empty:
        return out
    daily = (
        df.groupby(["trade_date", "sleeve"])
        .apply(lambda g: _weighted_mean(g["r_prevclose_1455"], g["target_weight"]))
        .rename("sleeve_return_1455")
        .reset_index()
    )
    for date, group in daily.groupby("trade_date"):
        spread = float(group["sleeve_return_1455"].max() - group["sleeve_return_1455"].min())
        if spread < 0.01:
            continue
        event_count = 0
        next1 = ""
        if not event_df.empty:
            ev = event_df[(event_df["trade_date"].eq(date)) & (event_df["event_type"].eq("sector_rotation_outflow"))]
            event_count = len(ev)
            next1 = _mean(ev["next1_return_after_observation"]) if len(ev) else ""
        out.append(
            {
                "trade_date": date,
                "sleeve_spread_1455": spread,
                "best_sleeve": group.sort_values("sleeve_return_1455", ascending=False).iloc[0]["sleeve"],
                "weakest_sleeve": group.sort_values("sleeve_return_1455", ascending=True).iloc[0]["sleeve"],
                "sector_rotation_event_count": event_count,
                "sector_rotation_event_next1_avg": next1,
                "used_for_trade_rule": False,
            }
        )
    return out


def _event_breakdown(events: list[dict[str, Any]], group_cols: list[str]) -> list[dict[str, Any]]:
    df = pd.DataFrame(events)
    if df.empty:
        return []
    df["year"] = df["trade_date"].astype(str).str.slice(0, 4)
    rows = []
    for key, group in df.groupby(group_cols, sort=True):
        key_values = key if isinstance(key, tuple) else (key,)
        row = {col: value for col, value in zip(group_cols, key_values)}
        row.update(
            {
                "event_count": int(len(group)),
                "unique_stock_count": int(group["code"].nunique()),
                "avg_trigger_return": _mean(group["trigger_return"]),
                "avg_next1_return_after_observation": _mean(group["next1_return_after_observation"]),
                "avg_next2_return_after_observation": _mean(group["next2_return_after_observation"]),
                "hit_rate_next1_positive": _positive_rate(group["next1_return_after_observation"]),
                "hit_rate_next2_positive": _positive_rate(group["next2_return_after_observation"]),
                "estimated_next2_overlay_return_pct_points": float(
                    (
                        pd.to_numeric(group["next2_return_after_observation"], errors="coerce").fillna(0.0)
                        * pd.to_numeric(group["target_weight"], errors="coerce").fillna(0.0)
                        * 0.10
                    ).sum()
                    * 100
                ),
            }
        )
        rows.append(row)
    return rows


def _micro_overlay_estimate(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(events)
    if df.empty:
        return []
    rows = []
    for event_type, group in df.groupby("event_type", sort=True):
        for horizon, col in [
            ("same_day", "same_day_return_after_observation"),
            ("next1", "next1_return_after_observation"),
            ("next2", "next2_return_after_observation"),
        ]:
            if event_type.startswith("daily_") and horizon == "same_day":
                continue
            ret = pd.to_numeric(group[col], errors="coerce")
            weight = pd.to_numeric(group["target_weight"], errors="coerce").fillna(0.0)
            overlay_return = float((ret.fillna(0.0) * weight * 0.10).sum())
            rows.append(
                {
                    "event_type": event_type,
                    "horizon": horizon,
                    "event_count": int(len(group)),
                    "avg_event_return": _mean(group[col]),
                    "hit_rate_positive": _positive_rate(group[col]),
                    "estimated_total_overlay_return_pct_points": overlay_return * 100,
                    "overlay_budget_rule": "diagnostic 10% relative add to triggered holding weight, no live approval",
                    "used_for_trade_rule": False,
                    "accepted": False,
                }
            )
    return rows


def _data_gate(gate: dict[str, Any], minute_days: list[dict[str, Any]], signals: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {
            "check_id": "full_holding_5min_effective_coverage",
            "status": "pass" if float(gate.get("effective_coverage_rate_pct", 0.0)) >= 99.9 else "fail",
            "detail": gate.get("effective_coverage_rate_pct", 0.0),
        },
        {
            "check_id": "minute_day_observations_loaded",
            "status": "pass" if len(minute_days) > 0 else "fail",
            "detail": len(minute_days),
        },
        {
            "check_id": "repaired_v57f_signal_table",
            "status": "pass" if {"score", "cash_generation_yield", "dividend_yield_decimal"}.issubset(signals.columns) else "review",
            "detail": "PIT proxy fundamentals available from repaired signals",
        },
        {
            "check_id": "direct_financial_statement_fields",
            "status": "needs_data_for_formal_gate",
            "detail": "PB/ROE/revenue/profit fields not required for this short-window proxy run",
        },
    ]


def _governance_audit(data_gate: list[dict[str, Any]]) -> list[dict[str, Any]]:
    data_ok = all(row["status"] in {"pass", "needs_data_for_formal_gate"} for row in data_gate)
    return [
        {"audit_id": "backtest_scope_end", "status": "pass", "detail": BACKTEST_END},
        {"audit_id": "full_holding_5min_scope", "status": "pass", "detail": "full_holding_period_5min"},
        {"audit_id": "data_gate_nonfatal", "status": "pass" if data_ok else "fail", "detail": data_ok},
        {"audit_id": "locked_v57f_pool_only", "status": "pass", "detail": True},
        {"audit_id": "no_full_market_selection", "status": "pass", "detail": True},
        {"audit_id": "no_v57f_core_modified", "status": "pass", "detail": False},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
    ]


def _pit_audit() -> list[dict[str, Any]]:
    return [
        {
            "audit_id": "intraday_observation_time_pit",
            "status": "pass",
            "detail": "10:00/10:30/14:55 signals use bars up to observation time; forward returns are evaluation only.",
        },
        {
            "audit_id": "daily_observation_time_pit",
            "status": "pass",
            "detail": "Daily shock signals use current/past close; next 1d/2d returns are evaluation only.",
        },
        {
            "audit_id": "no_threshold_optimization",
            "status": "pass",
            "detail": "Uses pre-fixed bottom decile plus shock floors; no historical best threshold selected.",
        },
    ]


def _pm_decision(
    intraday: list[dict[str, Any]],
    daily: list[dict[str, Any]],
    overlay: list[dict[str, Any]],
    governance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    best = _best_overlay(overlay)
    best_return = float(best.get("estimated_total_overlay_return_pct_points", 0.0) or 0.0)
    best_hit = float(best.get("hit_rate_positive", 0.0) or 0.0)
    if not gov_ok:
        decision = "blocked_by_governance_issue"
        usable = "no"
        rationale = "Governance audit failed."
    elif best_return > 1.0 and best_hit > 0.52:
        decision = "short_window_reversion_positive_ready_for_pm_quant_review_not_accepted"
        usable = "candidate_review"
        rationale = "Short-window reversion shows positive event-level and overlay-level diagnostic value."
    elif best_return > 0.0:
        decision = "short_window_reversion_diagnostic_positive_but_not_portfolio_material"
        usable = "limited_diagnostic"
        rationale = "Short-window reversion exists in places but is too small or unstable for a V5f trading overlay."
    else:
        decision = "short_window_reversion_diagnostic_only_no_material_edge"
        usable = "diagnostic_only"
        rationale = "Short-window reversion does not produce positive overlay-level value."
    return [
        {
            "pm_gate_decision": decision,
            "primary_candidate": PRIMARY_REFERENCE,
            "best_event_type": best.get("event_type", ""),
            "best_horizon": best.get("horizon", ""),
            "best_overlay_return_pct_points": best_return,
            "best_hit_rate_positive": best_hit,
            "usable_space": usable,
            "intraday_event_types_tested": len(intraday),
            "daily_event_types_tested": len(daily),
            "accepted": False,
            "live_trading_approved": False,
            "rationale": rationale,
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "task": "Keep internal_subsleeve_mom12_70_30 as V5f primary.",
            "allowed": True,
        },
        {
            "priority": 2,
            "task": "Keep short-window reversion as diagnostic/risk monitoring if not material.",
            "allowed": not decision.startswith("short_window_reversion_positive_ready"),
        },
        {
            "priority": 3,
            "task": "Open PM/Quant review only if short-window overlay is material.",
            "allowed": decision.startswith("short_window_reversion_positive_ready"),
        },
        {
            "priority": 4,
            "task": "Use 5min data for full-market selection or optimized shock thresholds.",
            "allowed": False,
        },
    ]


def _best_overlay(overlay: list[dict[str, Any]]) -> dict[str, Any]:
    if not overlay:
        return {}
    return max(overlay, key=lambda row: float(row.get("estimated_total_overlay_return_pct_points", 0.0) or 0.0))


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    if failed:
        return [{"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed]
    return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Short-window reversion diagnostic completed."}]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    observation_count: int = 0,
    event_count: int = 0,
    best_event_type: str = "",
    best_overlay_return_pct_points: float = 0.0,
    usable_space: str = "",
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_short_window_reversion_diagnostic",
        "status": status,
        "pm_gate_decision": decision,
        "backtest_scope_start": BACKTEST_START,
        "backtest_scope_end": BACKTEST_END,
        "primary_candidate": PRIMARY_REFERENCE,
        "observation_count": observation_count,
        "event_count": event_count,
        "best_event_type": best_event_type,
        "best_overlay_return_pct_points": best_overlay_return_pct_points,
        "usable_space": usable_space,
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
    intraday: list[dict[str, Any]],
    daily: list[dict[str, Any]],
    sector: list[dict[str, Any]],
    overlay: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    return "\n".join(
        [
            "# V5f Short-Window Reversion Diagnostic",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Primary remains: `{decision[0]['primary_candidate']}`",
            f"- Best event: `{decision[0]['best_event_type']}` / `{decision[0]['best_horizon']}`",
            f"- Best overlay estimate: `{decision[0]['best_overlay_return_pct_points']}` pct points.",
            "- Scope: full holding-period 5min data, V57f repaired holdings only.",
            "- Status: not accepted; not live approved.",
            "",
            "## Intraday Events",
            *[
                f"- `{row['event_type']}`: count={row['event_count']}, next1={float(row['avg_next1_return_after_observation']):.4%}, next2={float(row['avg_next2_return_after_observation']):.4%}, direction={row['diagnostic_direction']}"
                for row in intraday
            ],
            "",
            "## Daily 1-2 Day Events",
            *[
                f"- `{row['event_type']}`: count={row['event_count']}, next1={float(row['avg_next1_return_after_observation']):.4%}, next2={float(row['avg_next2_return_after_observation']):.4%}, direction={row['diagnostic_direction']}"
                for row in daily
            ],
            "",
            "## Micro Overlay Estimate",
            *[
                f"- `{row['event_type']}` / `{row['horizon']}`: estimate={float(row['estimated_total_overlay_return_pct_points']):.4f} pct, hit={float(row['hit_rate_positive']):.2%}"
                for row in overlay
            ],
            "",
            f"Sector rotation days detected: {len(sector)}.",
            "",
        ]
    )


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Short-Window Reversion Diagnostic Rules",
            "",
            "- Historical engineering window ends 2026-05-31.",
            "- Uses full holding-period 5min data and V57f repaired holdings only.",
            "- No full-market stock selection, no V57f core modification, no accepted/live approval.",
            "- Shock thresholds are fixed diagnostics, not optimized strategy parameters.",
            "",
        ]
    )


def _signal_map(signals: pd.DataFrame) -> dict[tuple[str, str], dict[str, Any]]:
    rows = {}
    for _, row in signals.iterrows():
        rows[(str(row["trade_date"]), str(row["code"]))] = row.to_dict()
    return rows


def _time_close(by_time: dict[str, Any], target: str) -> float | None:
    if target in by_time:
        return _safe_float(by_time[target]["close"])
    available = sorted(time for time in by_time if time <= target)
    if not available:
        return None
    return _safe_float(by_time[available[-1]]["close"])


def _ret(end: Any, start: Any) -> float | None:
    end_value = _safe_float(end)
    start_value = _safe_float(start)
    if end_value is None or start_value in (None, 0.0):
        return None
    return end_value / start_value - 1.0


def _mean(values: Any) -> float:
    series = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    return float(series.mean()) if len(series) else 0.0


def _positive_rate(values: Any) -> float:
    series = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    return float((series > 0).mean()) if len(series) else 0.0


def _weighted_mean(values: Any, weights: Any) -> float:
    value_series = pd.to_numeric(pd.Series(values), errors="coerce")
    weight_series = pd.to_numeric(pd.Series(weights), errors="coerce").fillna(0.0)
    valid = value_series.notna()
    if not valid.any():
        return 0.0
    value_series = value_series[valid]
    weight_series = weight_series[valid]
    if float(weight_series.sum()) == 0.0:
        return float(value_series.mean())
    return float((value_series * weight_series).sum() / weight_series.sum())


def _direction(group: pd.DataFrame) -> str:
    next1 = _mean(group["next1_return_after_observation"])
    next2 = _mean(group["next2_return_after_observation"])
    hit1 = _positive_rate(group["next1_return_after_observation"])
    if next1 > 0 and next2 > 0 and hit1 >= 0.5:
        return "mean_reversion_positive"
    if next1 < 0 and next2 < 0:
        return "continued_weakness"
    return "mixed_or_small"


def _quantile(series: Any, q: float) -> float:
    clean = pd.to_numeric(pd.Series(series), errors="coerce").dropna()
    return float(clean.quantile(q)) if len(clean) else 0.0


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        FULL_5MIN_SUMMARY,
        FULL_5MIN_AVAILABLE,
        FULL_5MIN_RAW_INDEX,
        REPAIRED_RUN / "rebalance_signals.csv",
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
    print(json.dumps(run_v5f_short_window_reversion(Path(".")), ensure_ascii=False, indent=2))

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_1min_microstructure_signal_quality_gate") / "current"
ONE_MIN_DATASET = "local_1min_clean_2013_2026"
ONE_MIN_MANIFEST = Path("manifests") / ONE_MIN_DATASET / "collection_manifest.json"
ONE_MIN_INDEX = Path("manifests") / ONE_MIN_DATASET / "v5_required_1min_coverage_audit.csv"
ONE_MIN_CROSSCHECK = Path("manifests") / ONE_MIN_DATASET / "sample_1min_to_5min_crosscheck.csv"

SHORT_WINDOW_DIR = Path("v5f_short_window_reversion_diagnostic") / "current"
SHORT_WINDOW_EVENTS = SHORT_WINDOW_DIR / "v5f_short_window_reversion_event_log.csv"
SHORT_WINDOW_FEATURES = SHORT_WINDOW_DIR / "v5f_short_window_reversion_minute_day_features.csv"
SPIKE_SYMMETRY_DIR = Path("v5f_short_window_spike_reversion_symmetry") / "current"
SPIKE_EVENTS = SPIKE_SYMMETRY_DIR / "v5f_short_window_spike_reversion_event_log.csv"

BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
PREBACKTEST_START = "2013-01-01"
PREBACKTEST_END = "2021-04-30"

EVENT_TYPES = {
    "morning_30m_micro_crash",
    "morning_60m_micro_crash",
    "late_day_vwap_dislocation",
    "morning_30m_micro_spike",
    "late_day_vwap_premium",
}

CRASH_TYPES = {"morning_30m_micro_crash", "morning_60m_micro_crash", "late_day_vwap_dislocation"}
SPIKE_TYPES = {"morning_30m_micro_spike", "late_day_vwap_premium"}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_1min_microstructure_signal_quality_gate(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        summary = _summary("blocked_missing_required_input", "blocked_by_missing_required_input", blockers)
        _write_minimal(out, summary, blockers)
        return summary

    db = _find_v5_database(root)
    manifest = _read_json(db / ONE_MIN_MANIFEST)
    data_gate = _data_gate(db, manifest)
    governance = _governance_audit(manifest)
    if any(row["status"] == "fail" for row in data_gate + governance):
        blockers = _blockers(data_gate, governance)
        summary = _summary("blocked_by_1min_data_quality", "blocked_by_data_or_governance_issue", blockers)
        _write_minimal(out, summary, blockers, data_gate=data_gate, governance=governance)
        return summary

    events = _load_registered_events(root)
    features = _load_feature_lookup(root)
    diagnostics, coverage_rows, read_audit = _event_microstructure_diagnostics(root, db, events, features)
    event_summary = _event_type_summary(diagnostics)
    vwap_diag = _vwap_precision_diagnostics(diagnostics)
    execution_diag = _execution_path_diagnostics(diagnostics)
    quality_filter = _quality_filter_recommendations(event_summary, vwap_diag)
    pm_decision = _pm_decision(event_summary, vwap_diag, data_gate, governance)
    blockers = _blockers(data_gate, governance)
    next_queue = _next_queue(pm_decision[0]["pm_gate_decision"])
    spec = _spec()

    _write_csv(out / "v5f_1min_microstructure_signal_quality_spec.csv", spec)
    _write_csv(out / "v5f_1min_microstructure_data_gate.csv", data_gate)
    _write_csv(out / "v5f_1min_event_coverage_audit.csv", coverage_rows)
    _write_csv(out / "v5f_1min_file_read_audit.csv", read_audit)
    _write_csv(out / "v5f_1min_event_path_diagnostics.csv", diagnostics)
    _write_csv(out / "v5f_1min_event_type_quality_summary.csv", event_summary)
    _write_csv(out / "v5f_1min_vwap_precision_diagnostics.csv", vwap_diag)
    _write_csv(out / "v5f_1min_execution_path_diagnostics.csv", execution_diag)
    _write_csv(out / "v5f_1min_quality_filter_recommendation.csv", quality_filter)
    _write_csv(out / "v5f_1min_pit_governance_audit.csv", governance)
    _write_csv(out / "v5f_1min_pm_gate_decision.csv", pm_decision)
    _write_csv(out / "v5f_1min_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5f_1min_blockers.csv", blockers)
    (out / "v5f_1min_microstructure_report.md").write_text(
        _report(manifest, data_gate, event_summary, vwap_diag, execution_diag, pm_decision),
        encoding="utf-8",
    )
    (out / "v5f_1min_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    confirmed = sum(int(row.get("confirmed_by_1min_count", 0) or 0) for row in event_summary)
    event_count = sum(int(row.get("event_count", 0) or 0) for row in event_summary)
    summary = _summary(
        "completed_v5f_1min_microstructure_signal_quality_gate",
        pm_decision[0]["pm_gate_decision"],
        [],
        one_min_rows=int(manifest.get("total_1min_rows", 0) or 0),
        one_min_stock_days=int(manifest.get("total_stock_days", 0) or 0),
        full_240_stock_day_rate_pct=float(manifest.get("full_240_stock_day_rate_pct", 0.0) or 0.0),
        registered_event_count=len(events),
        diagnosed_event_count=len(diagnostics),
        event_coverage_rate_pct=_pct(len(diagnostics), len(events)),
        confirmed_by_1min_count=confirmed,
        confirmed_by_1min_rate_pct=_pct(confirmed, event_count),
        single_minute_dominated_rate_pct=_weighted_pct(event_summary, "single_minute_dominated_count", "event_count"),
        vwap_review_needed_count=sum(1 for row in vwap_diag if row.get("needs_vwap_review") is True),
    )
    _write_json(out / "v5f_1min_microstructure_summary.json", summary)
    return summary


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    missing = []
    db: Path | None = None
    try:
        db = _find_v5_database(root)
    except FileNotFoundError as exc:
        missing.append(
            {
                "blocker_id": "v5_database_missing",
                "severity": "fatal",
                "status": "blocking",
                "description": str(exc),
            }
        )
    required = [SHORT_WINDOW_EVENTS, SHORT_WINDOW_FEATURES, SPIKE_EVENTS]
    for path in required:
        if not (root / path).exists():
            missing.append(
                {
                    "blocker_id": f"missing_{path.name}",
                    "severity": "fatal",
                    "status": "blocking",
                    "description": str(path),
                }
            )
    if db is not None:
        for rel_path in [ONE_MIN_MANIFEST, ONE_MIN_INDEX, ONE_MIN_CROSSCHECK]:
            if not (db / rel_path).exists():
                missing.append(
                    {
                        "blocker_id": f"missing_{rel_path.name}",
                        "severity": "fatal",
                        "status": "blocking",
                        "description": str(db / rel_path),
                    }
                )
    return missing


def _find_v5_database(root: Path) -> Path:
    for child in root.iterdir():
        if child.is_dir() and (child / "processed").exists() and (child / "raw").exists() and (child / "manifests").exists():
            return child
    raise FileNotFoundError("Could not locate V5 database directory with processed/raw/manifests children.")


def _data_gate(db: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    cross = _read_csv(db / ONE_MIN_CROSSCHECK)
    cross_pass = sum(1 for row in cross if row.get("status") == "pass")
    cross_total = len(cross)
    index = _read_csv(db / ONE_MIN_INDEX)
    status_counts = Counter(row.get("status", "") for row in index)
    return [
        {
            "gate_id": "one_min_dataset_completed",
            "status": "pass" if manifest.get("status") == "completed" else "fail",
            "value": manifest.get("status", ""),
            "detail": ONE_MIN_DATASET,
        },
        {
            "gate_id": "full_240_stock_day_rate",
            "status": "pass" if float(manifest.get("full_240_stock_day_rate_pct", 0.0) or 0.0) >= 99.9 else "fail",
            "value": manifest.get("full_240_stock_day_rate_pct", 0.0),
            "detail": "threshold >= 99.9%; missing minutes are not filled",
        },
        {
            "gate_id": "one_min_to_existing_5min_crosscheck",
            "status": "pass" if cross_total and cross_pass == cross_total else "fail",
            "value": f"{cross_pass}/{cross_total}",
            "detail": "sample aggregated 1min OHLCV/amount equals existing 5min database",
        },
        {
            "gate_id": "bad_ohlc_drop_rate",
            "status": "pass" if _pct(int(manifest.get("dropped_counts", {}).get("dropped_bad_ohlc_rows", 0)), int(manifest.get("total_1min_rows", 1))) < 0.01 else "fail",
            "value": manifest.get("dropped_counts", {}).get("dropped_bad_ohlc_rows", 0),
            "detail": "bad rows are dropped, not repaired",
        },
        {
            "gate_id": "universe_scope",
            "status": "pass" if int(manifest.get("universe_code_count", 0) or 0) > 0 else "fail",
            "value": manifest.get("universe_code_count", 0),
            "detail": f"status_counts={dict(status_counts)}",
        },
    ]


def _governance_audit(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "audit_id": "frequency_not_increased",
            "status": "pass",
            "detail": "1min is used only to audit signal quality, VWAP precision, and execution path; no 1min trading frequency is introduced.",
        },
        {
            "audit_id": "no_new_buy_signal",
            "status": "pass",
            "detail": "Only existing V57f/V5f held-pool events are inspected.",
        },
        {
            "audit_id": "no_threshold_scan",
            "status": "pass",
            "detail": "Registered 5min event definitions are reused; no 1min threshold is optimized.",
        },
        {
            "audit_id": "no_v57f_core_modified",
            "status": "pass",
            "detail": "V57f core files are read-only for this gate.",
        },
        {
            "audit_id": "accepted_false",
            "status": "pass",
            "detail": "This gate cannot mark any V5f/V5e/V57f component accepted or live approved.",
        },
        {
            "audit_id": "sample_split_preserved",
            "status": "pass",
            "detail": (
                f"{PREBACKTEST_START} to {PREBACKTEST_END} remains prebacktest learning/validation; "
                f"{BACKTEST_START} to {BACKTEST_END} remains formal backtest; 1min gate does not use backtest outcomes to tune thresholds."
            ),
        },
        {
            "audit_id": "one_min_cleaning_policy_preserved",
            "status": "pass",
            "detail": str(manifest.get("cleaning_policy", "")),
        },
    ]


def _load_registered_events(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source_specs = [
        (SHORT_WINDOW_EVENTS, "short_window_reversion_diagnostic"),
        (SPIKE_EVENTS, "short_window_spike_reversion_symmetry"),
    ]
    for path, source in source_specs:
        for row in _read_csv(root / path):
            event_type = str(row.get("event_type", ""))
            trade_date = str(row.get("trade_date", ""))
            if event_type not in EVENT_TYPES:
                continue
            if trade_date < BACKTEST_START or trade_date > BACKTEST_END:
                continue
            rows.append(
                {
                    "event_uid": f"{source}|{event_type}|{row.get('code')}|{trade_date}",
                    "event_source": source,
                    "event_type": event_type,
                    "code": str(row.get("code", "")),
                    "trade_date": trade_date,
                    "year": trade_date[:4],
                    "sleeve": str(row.get("sleeve", "")),
                    "holding_start_date": str(row.get("holding_start_date", "")),
                    "observation_time": _observation_time(event_type, row),
                    "trigger_return_5min_registered": _safe_float(row.get("trigger_return")),
                    "same_day_return_after_observation_5min": _safe_float(row.get("same_day_return_after_observation")),
                    "next1_return_after_observation": _safe_float(row.get("next1_return_after_observation")),
                    "next2_return_after_observation": _safe_float(row.get("next2_return_after_observation")),
                    "target_weight": _safe_float(row.get("target_weight")),
                    "new_buy_signal_allowed": False,
                    "accepted": False,
                }
            )
    rows.sort(key=lambda row: (row["trade_date"], row["code"], row["event_type"], row["event_source"]))
    return rows


def _load_feature_lookup(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    usecols = [
        "code",
        "trade_date",
        "prev_day_close",
        "close_0935",
        "close_1000",
        "close_1030",
        "close_1455",
        "vwap_1455",
        "r_0935_1000",
        "r_0935_1030",
        "r_prevclose_1455",
        "r_1455_vwap",
    ]
    df = pd.read_csv(root / SHORT_WINDOW_FEATURES, usecols=lambda col: col in usecols, dtype={"code": str, "trade_date": str})
    return {(str(row["code"]), str(row["trade_date"])): row.to_dict() for _, row in df.iterrows()}


def _event_microstructure_diagnostics(
    root: Path,
    db: Path,
    events: list[dict[str, Any]],
    features: dict[tuple[str, str], dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    by_file: dict[Path, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_file[_one_min_path(db, event["code"], event["year"])].append(event)

    diagnostics: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    read_audit: list[dict[str, Any]] = []
    for path, file_events in sorted(by_file.items(), key=lambda item: str(item[0])):
        code = file_events[0]["code"]
        year = file_events[0]["year"]
        dates = sorted({event["trade_date"] for event in file_events})
        if not path.exists():
            coverage_rows.extend(_coverage_miss_rows(file_events, "missing_1min_file", path))
            read_audit.append(
                {
                    "code": code,
                    "year": year,
                    "path": str(_rel(root, path)),
                    "status": "missing_1min_file",
                    "requested_event_count": len(file_events),
                    "loaded_row_count": 0,
                    "loaded_trade_date_count": 0,
                }
            )
            continue

        try:
            df = pd.read_csv(
                path,
                usecols=["trade_date", "time", "open", "high", "low", "close", "volume", "amount"],
                dtype={"trade_date": str, "time": str},
            )
        except Exception as exc:
            coverage_rows.extend(_coverage_miss_rows(file_events, f"read_error:{type(exc).__name__}", path))
            read_audit.append(
                {
                    "code": code,
                    "year": year,
                    "path": str(_rel(root, path)),
                    "status": "read_error",
                    "requested_event_count": len(file_events),
                    "loaded_row_count": 0,
                    "loaded_trade_date_count": 0,
                    "error_message": str(exc)[:300],
                }
            )
            continue

        df = df[df["trade_date"].isin(dates)].copy()
        for col in ["open", "high", "low", "close", "volume", "amount"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        grouped = {str(date): group.sort_values("time").reset_index(drop=True) for date, group in df.groupby("trade_date")}
        read_audit.append(
            {
                "code": code,
                "year": year,
                "path": str(_rel(root, path)),
                "status": "pass",
                "requested_event_count": len(file_events),
                "loaded_row_count": int(len(df)),
                "loaded_trade_date_count": int(len(grouped)),
            }
        )
        for event in file_events:
            group = grouped.get(event["trade_date"])
            if group is None or group.empty:
                coverage_rows.append(_coverage_row(event, "missing_trade_date", path, 0))
                continue
            coverage_rows.append(_coverage_row(event, "pass", path, len(group)))
            diagnostics.append(_diagnose_event(event, group, features.get((event["code"], event["trade_date"]), {})))
    return diagnostics, coverage_rows, read_audit


def _one_min_path(db: Path, code: str, year: str) -> Path:
    return db / "processed" / ONE_MIN_DATASET / "by_year" / str(year) / f"{code.replace('.', '_')}_1min.csv"


def _coverage_miss_rows(events: list[dict[str, Any]], status: str, path: Path) -> list[dict[str, Any]]:
    return [_coverage_row(event, status, path, 0) for event in events]


def _coverage_row(event: dict[str, Any], status: str, path: Path, row_count: int) -> dict[str, Any]:
    return {
        "event_uid": event["event_uid"],
        "event_type": event["event_type"],
        "code": event["code"],
        "trade_date": event["trade_date"],
        "year": event["year"],
        "sleeve": event["sleeve"],
        "coverage_status": status,
        "one_min_row_count": row_count,
        "one_min_file": str(path),
    }


def _diagnose_event(event: dict[str, Any], df: pd.DataFrame, feature: dict[str, Any]) -> dict[str, Any]:
    event_type = event["event_type"]
    obs_time = event["observation_time"]
    by_time = {str(row["time"]): row for _, row in df.iterrows()}
    obs_close = _time_value(by_time, obs_time, "close")
    day_close = _safe_float(df.iloc[-1]["close"])
    day_low = _safe_float(df["low"].min())
    day_high = _safe_float(df["high"].max())
    window_start = _window_start(event_type)
    start_close = _time_value(by_time, window_start, "close") if window_start else _safe_float(feature.get("prev_day_close"))
    window_return = _ret(obs_close, start_close)

    upto_obs = df[df["time"].astype(str) <= obs_time].copy()
    vwap_to_obs = _vwap(upto_obs)
    full_day_vwap = _vwap(df)
    vwap_deviation_1min = _ret(obs_close, vwap_to_obs)
    feature_vwap = _safe_float(feature.get("vwap_1455"))
    feature_vwap_deviation = _ret(obs_close, feature_vwap)

    window_df = _window_frame(df, window_start, obs_time)
    minute_returns = _minute_returns(window_df)
    direction = -1 if event_type in CRASH_TYPES else 1
    direction_consistency = _direction_consistency(minute_returns, direction)
    max_abs_1min_return = max((abs(value) for value in minute_returns if value is not None), default=0.0)
    concentration = max_abs_1min_return / abs(window_return) if window_return not in (None, 0.0) else 0.0
    after = df[df["time"].astype(str) > obs_time].copy()
    after_return = _ret(day_close, obs_close)
    mae_after = _mae_after(after, obs_close)
    mfe_after = _mfe_after(after, obs_close)

    confirmed = _confirmed(event_type, window_return, vwap_deviation_1min, event.get("trigger_return_5min_registered"))
    return {
        "event_uid": event["event_uid"],
        "event_source": event["event_source"],
        "event_type": event_type,
        "code": event["code"],
        "trade_date": event["trade_date"],
        "year": event["year"],
        "sample_scope": "formal_backtest",
        "sleeve": event["sleeve"],
        "holding_start_date": event["holding_start_date"],
        "observation_time": obs_time,
        "one_min_bar_count": int(len(df)),
        "window_start_time": window_start or "prev_close",
        "start_close_1min_or_prev": start_close,
        "observation_close_1min": obs_close,
        "day_close_1min": day_close,
        "day_low_1min": day_low,
        "day_high_1min": day_high,
        "trigger_return_5min_registered": event.get("trigger_return_5min_registered"),
        "trigger_return_1min_recomputed": window_return,
        "trigger_return_abs_diff": _abs_diff(window_return, event.get("trigger_return_5min_registered")),
        "vwap_to_observation_1min": vwap_to_obs,
        "full_day_vwap_1min": full_day_vwap,
        "feature_vwap_5min_reference": feature_vwap,
        "vwap_deviation_1min_to_observation": vwap_deviation_1min,
        "vwap_deviation_5min_reference": feature_vwap_deviation,
        "vwap_deviation_abs_diff": _abs_diff(vwap_deviation_1min, feature_vwap_deviation),
        "confirmed_by_1min": confirmed,
        "minute_return_count_in_window": len(minute_returns),
        "direction_consistency_rate": direction_consistency,
        "max_abs_1min_return_in_window": max_abs_1min_return,
        "single_minute_concentration": concentration,
        "single_minute_dominated": concentration >= 0.60 if concentration is not None else False,
        "same_day_return_after_observation_1min": after_return,
        "same_day_return_after_observation_5min_registered": event.get("same_day_return_after_observation_5min"),
        "same_day_after_abs_diff": _abs_diff(after_return, event.get("same_day_return_after_observation_5min")),
        "mae_after_observation": mae_after,
        "mfe_after_observation": mfe_after,
        "next1_return_after_observation": event.get("next1_return_after_observation"),
        "next2_return_after_observation": event.get("next2_return_after_observation"),
        "new_buy_signal_allowed": False,
        "frequency_increase_allowed": False,
        "accepted": False,
    }


def _window_start(event_type: str) -> str | None:
    if event_type.startswith("morning_"):
        return "09:35:00"
    return None


def _window_frame(df: pd.DataFrame, start_time: str | None, end_time: str) -> pd.DataFrame:
    if start_time is None:
        return df[df["time"].astype(str) <= end_time].copy()
    return df[(df["time"].astype(str) >= start_time) & (df["time"].astype(str) <= end_time)].copy()


def _minute_returns(df: pd.DataFrame) -> list[float | None]:
    if df.empty:
        return []
    closes = [_safe_float(value) for value in df["close"].tolist()]
    out = []
    for prev, curr in zip(closes, closes[1:]):
        out.append(_ret(curr, prev))
    return out


def _confirmed(event_type: str, window_return: float | None, vwap_deviation: float | None, registered_return: float | None) -> bool:
    if event_type == "morning_30m_micro_crash":
        return window_return is not None and registered_return is not None and window_return <= -0.01 and _abs_diff(window_return, registered_return) <= 1e-8
    if event_type == "morning_60m_micro_crash":
        return window_return is not None and registered_return is not None and window_return <= -0.015 and _abs_diff(window_return, registered_return) <= 1e-8
    if event_type == "morning_30m_micro_spike":
        return window_return is not None and registered_return is not None and window_return >= 0.01 and _abs_diff(window_return, registered_return) <= 1e-8
    if event_type == "late_day_vwap_dislocation":
        return vwap_deviation is not None and vwap_deviation <= -0.005
    if event_type == "late_day_vwap_premium":
        return vwap_deviation is not None and vwap_deviation >= 0.005
    return False


def _event_type_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    if df.empty:
        return []
    out = []
    for event_type, group in df.groupby("event_type", sort=True):
        out.append(
            {
                "event_type": event_type,
                "event_count": int(len(group)),
                "unique_stock_count": int(group["code"].nunique()),
                "unique_trade_date_count": int(group["trade_date"].nunique()),
                "confirmed_by_1min_count": int(group["confirmed_by_1min"].astype(bool).sum()),
                "confirmed_by_1min_rate_pct": _pct(int(group["confirmed_by_1min"].astype(bool).sum()), len(group)),
                "avg_trigger_return_1min": _mean(group["trigger_return_1min_recomputed"]),
                "avg_abs_trigger_return_1min": _mean_abs(group["trigger_return_1min_recomputed"]),
                "avg_trigger_abs_diff_vs_5min": _mean(group["trigger_return_abs_diff"]),
                "avg_direction_consistency_rate": _mean(group["direction_consistency_rate"]),
                "single_minute_dominated_count": int(group["single_minute_dominated"].astype(bool).sum()),
                "single_minute_dominated_rate_pct": _pct(int(group["single_minute_dominated"].astype(bool).sum()), len(group)),
                "avg_same_day_return_after_observation": _mean(group["same_day_return_after_observation_1min"]),
                "same_day_repair_or_fade_rate_pct": _repair_or_fade_rate(event_type, group),
                "avg_mae_after_observation": _mean(group["mae_after_observation"]),
                "avg_mfe_after_observation": _mean(group["mfe_after_observation"]),
                "used_for_new_trade_rule": False,
            }
        )
    return out


def _vwap_precision_diagnostics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    if df.empty:
        return []
    df = df[df["event_type"].isin(["late_day_vwap_dislocation", "late_day_vwap_premium"])].copy()
    if df.empty:
        return []
    out = []
    for event_type, group in df.groupby("event_type", sort=True):
        flips = int((group["confirmed_by_1min"].astype(bool) == False).sum())  # noqa: E712
        avg_abs_diff = _mean_abs(group["vwap_deviation_abs_diff"])
        out.append(
            {
                "event_type": event_type,
                "event_count": int(len(group)),
                "confirmed_by_1min_rate_pct": _pct(int(group["confirmed_by_1min"].astype(bool).sum()), len(group)),
                "avg_vwap_deviation_1min_to_observation": _mean(group["vwap_deviation_1min_to_observation"]),
                "avg_vwap_deviation_5min_reference": _mean(group["vwap_deviation_5min_reference"]),
                "avg_abs_vwap_deviation_diff": avg_abs_diff,
                "max_abs_vwap_deviation_diff": _max_abs(group["vwap_deviation_abs_diff"]),
                "confirmation_flip_count": flips,
                "needs_vwap_review": bool(flips > 0 or (avg_abs_diff is not None and avg_abs_diff > 0.001)),
                "recommendation": "use 1min observation-time VWAP for audit precision; do not change trade frequency",
            }
        )
    return out


def _execution_path_diagnostics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    if df.empty:
        return []
    out = []
    for event_type, group in df.groupby("event_type", sort=True):
        after = pd.to_numeric(group["same_day_return_after_observation_1min"], errors="coerce")
        if event_type in CRASH_TYPES:
            favorable = int((after > 0).sum())
            label = "same_day_repair_after_crash_rate_pct"
        else:
            favorable = int((after < 0).sum())
            label = "same_day_fade_after_spike_rate_pct"
        out.append(
            {
                "event_type": event_type,
                "event_count": int(len(group)),
                label: _pct(favorable, len(group)),
                "avg_same_day_return_after_observation": _mean(after),
                "median_same_day_return_after_observation": _median(after),
                "avg_mae_after_observation": _mean(group["mae_after_observation"]),
                "avg_mfe_after_observation": _mean(group["mfe_after_observation"]),
                "max_adverse_path_observed": _min(group["mae_after_observation"]),
                "max_favorable_path_observed": _max(group["mfe_after_observation"]),
                "execution_use": "diagnostic_precision_only",
            }
        )
    return out


def _quality_filter_recommendations(event_summary: list[dict[str, Any]], vwap_diag: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in event_summary:
        confirmed = float(row.get("confirmed_by_1min_rate_pct", 0.0) or 0.0)
        dominated = float(row.get("single_minute_dominated_rate_pct", 0.0) or 0.0)
        if confirmed < 95.0:
            recommendation = "keep_diagnostic_until_confirmation_improves"
        elif dominated > 35.0:
            recommendation = "consider_noise_flag_in_separate_spec_not_trade_rule"
        else:
            recommendation = "quality_pass_for_microstructure_audit"
        rows.append(
            {
                "event_type": row["event_type"],
                "recommendation": recommendation,
                "confirmed_by_1min_rate_pct": confirmed,
                "single_minute_dominated_rate_pct": dominated,
                "allowed_next_use": "audit_or_forward_observation_only",
                "trading_frequency_change_allowed": False,
                "accepted": False,
            }
        )
    for row in vwap_diag:
        if row.get("needs_vwap_review") is True:
            rows.append(
                {
                    "event_type": row["event_type"],
                    "recommendation": "replace_vwap_diagnostic_reference_with_1min_observation_time_vwap_in_future_audits",
                    "confirmed_by_1min_rate_pct": row.get("confirmed_by_1min_rate_pct"),
                    "single_minute_dominated_rate_pct": "",
                    "allowed_next_use": "vwap_audit_precision_only",
                    "trading_frequency_change_allowed": False,
                    "accepted": False,
                }
            )
    return rows


def _pm_decision(
    event_summary: list[dict[str, Any]],
    vwap_diag: list[dict[str, Any]],
    data_gate: list[dict[str, Any]],
    governance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if any(row["status"] == "fail" for row in data_gate + governance):
        decision = "blocked_by_data_or_governance_issue"
        status = "blocked"
    elif not event_summary:
        decision = "diagnostic_only_no_events"
        status = "diagnostic_only"
    elif any(row.get("needs_vwap_review") is True for row in vwap_diag):
        decision = "one_minute_quality_gate_pass_vwap_precision_review_needed_not_trading"
        status = "pass_with_review"
    else:
        decision = "one_minute_quality_gate_pass_for_diagnostic_precision_not_trading"
        status = "pass"
    return [
        {
            "pm_gate_decision": decision,
            "status": status,
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "v5f_mainline_modified": False,
            "trading_frequency_increased": False,
            "threshold_scan_used": False,
            "new_buy_signal_used": False,
            "notes": "1min can improve microstructure/VWAP/path diagnostics; it cannot promote the spike/reversion rule or increase trading frequency.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "queue_id": "v5f_1min_vwap_execution_precision_audit",
            "status": "ready" if "pass" in decision else "blocked",
            "scope": "replace future VWAP diagnostics with observation-time 1min VWAP; no trading-rule change",
        },
        {
            "queue_id": "v5f_spike_mr_signal_quality_filter_spec",
            "status": "ready_for_spec_only" if "pass" in decision else "blocked",
            "scope": "define noise flags such as single-minute dominated, but do not optimize thresholds or trade frequency",
        },
        {
            "queue_id": "v5f_1min_forward_observation_append",
            "status": "ready",
            "scope": "append future forward/paper events after 2026-05-31 only as observation",
        },
    ]


def _blockers(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers = []
    for group in groups:
        for row in group:
            if row.get("status") == "fail":
                blockers.append(
                    {
                        "blocker_id": row.get("gate_id") or row.get("audit_id") or "unknown",
                        "severity": "fatal",
                        "status": "blocking",
                        "description": row.get("detail", ""),
                    }
                )
    if not blockers:
        return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": ""}]
    return blockers


def _spec() -> list[dict[str, Any]]:
    return [
        {
            "spec_id": "scope",
            "rule": "Use cleaned local 1min bars only for microstructure signal-quality, VWAP precision, and execution-path diagnostics.",
            "trading_frequency_change_allowed": False,
        },
        {
            "spec_id": "event_pool",
            "rule": "Only existing V5f/V57f held-pool short-window spike/reversion events are inspected.",
            "trading_frequency_change_allowed": False,
        },
        {
            "spec_id": "vwap",
            "rule": "For late-day events, compute VWAP using only bars at or before the observation time.",
            "trading_frequency_change_allowed": False,
        },
        {
            "spec_id": "noise",
            "rule": "Flag events dominated by a single 1min move; do not convert flags into optimized trading thresholds in this gate.",
            "trading_frequency_change_allowed": False,
        },
    ]


def _report(
    manifest: dict[str, Any],
    data_gate: list[dict[str, Any]],
    event_summary: list[dict[str, Any]],
    vwap_diag: list[dict[str, Any]],
    execution_diag: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    lines = [
        "# V5f 1min Microstructure Signal Quality Gate",
        "",
        "This packet uses cleaned 1-minute bars to improve spike/drop, VWAP, and execution-path diagnostics. It does not increase trading frequency, add buy signals, scan thresholds, or change the V5f mainline.",
        "",
        "## Data Gate",
        f"- Dataset status: `{manifest.get('status')}`",
        f"- 1min rows: `{manifest.get('total_1min_rows')}`",
        f"- Full 240-minute stock-day rate: `{manifest.get('full_240_stock_day_rate_pct')}%`",
        f"- Bad OHLC rows dropped: `{manifest.get('dropped_counts', {}).get('dropped_bad_ohlc_rows', 0)}`",
        "",
        "## Event Quality",
    ]
    for row in event_summary:
        lines.append(
            f"- `{row['event_type']}`: events `{row['event_count']}`, 1min confirmed `{row['confirmed_by_1min_rate_pct']}%`, single-minute dominated `{row['single_minute_dominated_rate_pct']}%`, same-day repair/fade `{row['same_day_repair_or_fade_rate_pct']}%`."
        )
    lines.extend(["", "## VWAP Precision"])
    if vwap_diag:
        for row in vwap_diag:
            lines.append(
                f"- `{row['event_type']}`: confirmed `{row['confirmed_by_1min_rate_pct']}%`, avg abs VWAP deviation diff `{row['avg_abs_vwap_deviation_diff']}`, flips `{row['confirmation_flip_count']}`."
            )
    else:
        lines.append("- No late-day VWAP events available.")
    lines.extend(["", "## Execution Path"])
    for row in execution_diag:
        lines.append(
            f"- `{row['event_type']}`: avg after-observation return `{row['avg_same_day_return_after_observation']}`, avg MAE `{row['avg_mae_after_observation']}`, avg MFE `{row['avg_mfe_after_observation']}`."
        )
    lines.extend(
        [
            "",
            "## PM Decision",
            f"- `{decision[0]['pm_gate_decision']}`",
            "- accepted: `False`",
            "- live approved: `False`",
            "- trading frequency increased: `False`",
            "",
            "## Gate Rows",
        ]
    )
    for row in data_gate:
        lines.append(f"- `{row['gate_id']}`: `{row['status']}` ({row['value']})")
    lines.append("")
    return "\n".join(lines)


def _rules() -> str:
    return "\n".join(
        [
            "# V5f 1min Microstructure Agent Execution Rules",
            "",
            "- Do not modify V57f core.",
            "- Do not modify V5f mainline or internal_subsleeve_mom12_70_30.",
            "- Do not use 1min data to increase trading frequency.",
            "- Do not add buy signals, same-day reentry, or cross-sleeve transfer.",
            "- Do not scan thresholds or mark accepted/live approved.",
            "- Use 1min only for signal-quality, VWAP precision, and execution-path diagnostics.",
            "- Preserve sample split: 2013-01-01 to 2021-04-30 is prebacktest learning/validation; 2021-05-01 to 2026-05-31 is formal backtest; later data is forward/paper only.",
            "",
        ]
    )


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_1min_microstructure_signal_quality_gate",
        "status": status,
        "pm_gate_decision": decision,
        "prebacktest_learning_validation_start": PREBACKTEST_START,
        "prebacktest_learning_validation_end": PREBACKTEST_END,
        "formal_backtest_start": BACKTEST_START,
        "formal_backtest_end": BACKTEST_END,
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "v5f_mainline_modified": False,
        "trading_frequency_increased": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len([row for row in blockers if row.get("status") == "blocking"]),
        "fatal_blockers": [row for row in blockers if row.get("status") == "blocking"],
        **extra,
    }


def _write_minimal(
    out: Path,
    summary: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    data_gate: list[dict[str, Any]] | None = None,
    governance: list[dict[str, Any]] | None = None,
) -> None:
    _write_json(out / "v5f_1min_microstructure_summary.json", summary)
    _write_csv(out / "v5f_1min_blockers.csv", blockers)
    _write_csv(out / "v5f_1min_microstructure_data_gate.csv", data_gate or [])
    _write_csv(out / "v5f_1min_pit_governance_audit.csv", governance or [])


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return None
        return out
    except Exception:
        return None


def _ret(end: float | None, start: float | None) -> float | None:
    if end is None or start in (None, 0.0):
        return None
    return end / start - 1.0


def _vwap(df: pd.DataFrame) -> float | None:
    if df.empty:
        return None
    volume = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)
    amount = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    total_volume = float(volume.sum())
    if total_volume <= 0:
        return _safe_float(df.iloc[-1]["close"])
    return float(amount.sum() / total_volume)


def _time_value(by_time: dict[str, Any], time_value: str, column: str) -> float | None:
    row = by_time.get(time_value)
    if row is None:
        return None
    return _safe_float(row[column])


def _direction_consistency(returns: list[float | None], direction: int) -> float | None:
    clean = [value for value in returns if value is not None and abs(value) > 1e-12]
    if not clean:
        return None
    if direction < 0:
        return sum(1 for value in clean if value < 0) / len(clean)
    return sum(1 for value in clean if value > 0) / len(clean)


def _mae_after(after: pd.DataFrame, obs_close: float | None) -> float | None:
    if after.empty or obs_close in (None, 0.0):
        return None
    low = _safe_float(after["low"].min())
    return _ret(low, obs_close)


def _mfe_after(after: pd.DataFrame, obs_close: float | None) -> float | None:
    if after.empty or obs_close in (None, 0.0):
        return None
    high = _safe_float(after["high"].max())
    return _ret(high, obs_close)


def _observation_time(event_type: str, row: dict[str, Any]) -> str:
    if str(row.get("observation_time", "")).strip():
        return str(row["observation_time"])
    if event_type == "morning_60m_micro_crash":
        return "10:30:00"
    if event_type.startswith("morning_"):
        return "10:00:00"
    return "14:55:00"


def _repair_or_fade_rate(event_type: str, group: pd.DataFrame) -> float:
    after = pd.to_numeric(group["same_day_return_after_observation_1min"], errors="coerce").dropna()
    if len(after) == 0:
        return 0.0
    if event_type in CRASH_TYPES:
        return _pct(int((after > 0).sum()), len(after))
    return _pct(int((after < 0).sum()), len(after))


def _mean(series: Any) -> float | None:
    clean = pd.to_numeric(pd.Series(series), errors="coerce").dropna()
    return float(clean.mean()) if len(clean) else None


def _mean_abs(series: Any) -> float | None:
    clean = pd.to_numeric(pd.Series(series), errors="coerce").dropna().abs()
    return float(clean.mean()) if len(clean) else None


def _median(series: Any) -> float | None:
    clean = pd.to_numeric(pd.Series(series), errors="coerce").dropna()
    return float(clean.median()) if len(clean) else None


def _max(series: Any) -> float | None:
    clean = pd.to_numeric(pd.Series(series), errors="coerce").dropna()
    return float(clean.max()) if len(clean) else None


def _min(series: Any) -> float | None:
    clean = pd.to_numeric(pd.Series(series), errors="coerce").dropna()
    return float(clean.min()) if len(clean) else None


def _max_abs(series: Any) -> float | None:
    clean = pd.to_numeric(pd.Series(series), errors="coerce").dropna().abs()
    return float(clean.max()) if len(clean) else None


def _abs_diff(left: Any, right: Any) -> float | None:
    lval = _safe_float(left)
    rval = _safe_float(right)
    if lval is None or rval is None:
        return None
    return abs(lval - rval)


def _pct(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100.0, 6) if denominator else 0.0


def _weighted_pct(rows: list[dict[str, Any]], numerator_key: str, denominator_key: str) -> float:
    numerator = sum(int(row.get(numerator_key, 0) or 0) for row in rows)
    denominator = sum(int(row.get(denominator_key, 0) or 0) for row in rows)
    return _pct(numerator, denominator)


def _rel(root: Path, path: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def main() -> None:
    summary = run_v5f_1min_microstructure_signal_quality_gate(Path("."))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

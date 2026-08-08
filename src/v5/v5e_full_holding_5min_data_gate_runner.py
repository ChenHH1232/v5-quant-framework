from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v5.v5d_baostock_5min_data_gate import normalize_baostock_frame


OUT_DIR = Path("v5e_full_holding_5min_data_gate") / "current"
RAW_DIR = Path("v5e_full_holding_5min_data_gate") / "data_raw"
STD_DIR = Path("v5e_full_holding_5min_data_gate") / "data_standardized"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
PRICE_DIR = Path("数据库") / "processed" / "startup_preload_repaired_prices_v5"
V5D_STD_DIR = Path("v5d_baostock_5min_data_gate") / "data_standardized"
POST_EXIT_STD_DIR = Path("v5e_post_exit_5min_monitoring_data_gate") / "data_standardized"
TRIGGER_DAY_STD_DIR = Path("v5e_trigger_day_5min_execution_data_gate") / "data_standardized"
REQUIRED_TIMES = ["09:35", "09:40", "10:00", "14:55"]
REQUIRED_FIELDS = ["open", "high", "low", "close", "volume", "amount", "time"]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_full_holding_5min_data_gate(root: Path = Path("."), fetch: bool = True) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_full_holding_5min_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_full_holding_5min_summary.json", summary)
        return summary

    requirements, trading_days = _build_requirements(root)
    daily_status = _daily_status(root, requirements)
    index = _local_index(root)
    coverage, quality = _coverage_audit(root, requirements, index, daily_status)
    fetch_queue = _build_fetch_intervals([row for row in coverage if row["needs_fetch"]], trading_days)
    _write_base_outputs(out, requirements, coverage, quality, fetch_queue, daily_status)

    fetch_log: list[dict[str, Any]] = []
    raw_index: list[dict[str, Any]] = []
    std_index: list[dict[str, Any]] = []
    fetch_blockers: list[dict[str, Any]] = []
    if fetch and fetch_queue:
        fetch_log, raw_index, std_index, fetch_blockers = _fetch_baostock(root, fetch_queue)
        _write_csv(out / "v5e_full_holding_5min_fetch_log.csv", fetch_log)
        _write_csv(out / "v5e_full_holding_5min_raw_index.csv", raw_index)
        _write_csv(out / "v5e_full_holding_5min_standardized_index.csv", std_index)
        _write_csv(out / "v5e_full_holding_5min_fetch_blockers.csv", fetch_blockers)
        index = _local_index(root)
        coverage, quality = _coverage_audit(root, requirements, index, daily_status)
        fetch_queue = _build_fetch_intervals([row for row in coverage if row["needs_fetch"]], trading_days)
        _write_base_outputs(out, requirements, coverage, quality, fetch_queue, daily_status)
    else:
        _write_csv(out / "v5e_full_holding_5min_fetch_log.csv", fetch_log)
        _write_csv(out / "v5e_full_holding_5min_raw_index.csv", raw_index)
        _write_csv(out / "v5e_full_holding_5min_standardized_index.csv", std_index)
        _write_csv(out / "v5e_full_holding_5min_fetch_blockers.csv", fetch_blockers)

    std_scan = _scan_index(root, STD_DIR, "_5min_standardized.csv")
    raw_scan = _scan_index(root, RAW_DIR, "_5min_raw.csv")
    if std_scan:
        _write_csv(out / "v5e_full_holding_5min_standardized_index.csv", std_scan)
    if raw_scan:
        _write_csv(out / "v5e_full_holding_5min_raw_index.csv", raw_scan)

    missing = [row for row in coverage if row["coverage_status"] != "available"]
    paused_missing = [row for row in missing if row["coverage_status"] == "paused_no_intraday_expected"]
    unresolved_missing = [row for row in missing if row["coverage_status"] != "paused_no_intraday_expected"]
    gate = _pm_gate_decision(requirements, coverage, fetch_blockers)
    blockers = _data_blockers(unresolved_missing, paused_missing, fetch_blockers)
    next_queue = _next_queue(gate[0]["pm_gate_decision"])
    _write_csv(out / "v5e_full_holding_5min_missing_windows.csv", missing)
    _write_csv(out / "v5e_full_holding_5min_available_windows.csv", [row for row in coverage if row["coverage_status"] == "available"])
    _write_csv(out / "v5e_full_holding_5min_pm_gate_decision.csv", gate)
    _write_csv(out / "v5e_full_holding_5min_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5e_full_holding_5min_blockers.csv", blockers)
    (out / "v5e_full_holding_5min_report.md").write_text(_report(requirements, coverage, gate), encoding="utf-8")
    (out / "v5e_full_holding_5min_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    summary = _summary(
        "completed_full_holding_5min_data_gate",
        gate[0]["pm_gate_decision"],
        [],
        required_stock_dates=len(requirements),
        available_stock_dates=sum(1 for row in coverage if row["coverage_status"] == "available"),
        paused_stock_dates=len(paused_missing),
        missing_stock_dates=len(unresolved_missing),
        fetch_interval_count=len(fetch_log),
        fetch_pass_count=sum(1 for row in fetch_log if row["status"] == "pass"),
        fetch_empty_count=sum(1 for row in fetch_log if row["status"] == "empty"),
        fetch_failure_count=sum(1 for row in fetch_log if row["status"] not in {"pass", "empty"}),
        stored_raw_interval_count=len(raw_scan),
        stored_standardized_file_count=len(std_scan),
    )
    _write_json(out / "v5e_full_holding_5min_summary.json", summary)
    return summary


def _build_requirements(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv")
    trading_days = sorted(daily["trade_date"].astype(str).unique().tolist())
    rebalance_dates = sorted(pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv")["trade_date"].astype(str).unique().tolist())
    holdings = pd.read_csv(root / REPAIRED_RUN / "holdings.csv")
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv")
    sleeve_map = {
        (str(row["trade_date"]), str(row["code"])): str(row.get("sector_id", ""))
        for _, row in signals.iterrows()
        if pd.notna(row.get("code", ""))
    }
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for _, row in holdings.iterrows():
        start = str(row["trade_date"])
        code = str(row["code"])
        next_rebalance = _next_rebalance(start, rebalance_dates)
        for day in _days_between(trading_days, start, next_rebalance):
            key = (code, day)
            if key not in rows:
                rows[key] = {
                    "requirement_id": f"{code}|{day}",
                    "code": code,
                    "trade_date": day,
                    "holding_start_date": start,
                    "next_rebalance_date": next_rebalance,
                    "sleeve": sleeve_map.get((start, code), ""),
                    "scope": "full_holding_period_5min",
                    "purpose": "rolling_intraday_model_research_and_monitoring",
                    "trade_trigger_allowed": True,
                    "rolling_required": True,
                    "required_fields": ";".join(REQUIRED_FIELDS),
                    "required_bar_times": ";".join(REQUIRED_TIMES + ["last_bar"]),
                }
            else:
                rows[key]["holding_start_date"] = min(rows[key]["holding_start_date"], start)
    return sorted(rows.values(), key=lambda r: (r["trade_date"], r["code"])), trading_days


def _daily_status(root: Path, requirements: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    needed = {(row["code"], row["trade_date"]) for row in requirements}
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for path in (root / PRICE_DIR).glob("*.csv"):
        df = pd.read_csv(path, dtype={"date": str, "code": str})
        df = df[df.apply(lambda row: (str(row["code"]), str(row["date"])) in needed, axis=1)]
        for _, row in df.iterrows():
            result[(str(row["code"]), str(row["date"]))] = {
                "open": row.get("open", ""),
                "close": row.get("close", ""),
                "volume": row.get("volume", ""),
                "money": row.get("money", ""),
                "paused": row.get("paused", ""),
                "price_file": path.name,
            }
    return result


def _local_index(root: Path) -> dict[tuple[str, str], str]:
    result: dict[tuple[str, str], str] = {}
    for base in [V5D_STD_DIR, POST_EXIT_STD_DIR, TRIGGER_DAY_STD_DIR, STD_DIR]:
        for row in _scan_index(root, base, "_5min_standardized.csv"):
            result[(row["code"], row["trade_date"])] = row["path"]
    return result


def _scan_index(root: Path, base_dir: Path, suffix: str) -> list[dict[str, Any]]:
    base = root / base_dir
    if not base.exists():
        return []
    rows = []
    for path in sorted(base.rglob(f"*{suffix}")):
        trade_date = path.parent.name
        code_part = path.name[: -len(suffix)]
        if "_" not in code_part:
            continue
        ticker, exchange = code_part.split("_", 1)
        code = f"{ticker}.{exchange}"
        try:
            with path.open("r", encoding="utf-8-sig") as f:
                row_count = max(sum(1 for _ in f) - 1, 0)
        except OSError:
            row_count = 0
        rows.append({"code": code, "bs_code": _to_bs_code(code), "trade_date": trade_date, "path": _rel(root, path), "row_count": row_count})
    return rows


def _coverage_audit(
    root: Path,
    requirements: list[dict[str, Any]],
    index: dict[tuple[str, str], str],
    daily_status: dict[tuple[str, str], dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    coverage = []
    quality = []
    for req in requirements:
        key = (req["code"], req["trade_date"])
        daily = daily_status.get(key, {})
        paused = _is_paused(daily)
        path_text = index.get(key, "")
        if not path_text:
            status = "paused_no_intraday_expected" if paused else "missing_local_5min_file"
            coverage.append(_coverage_row(req, status, daily=daily))
            quality.append(_quality_row(req, status, daily=daily))
            continue
        path = root / Path(path_text)
        if not path.exists():
            status = "paused_no_intraday_expected" if paused else "indexed_file_not_found"
            coverage.append(_coverage_row(req, status, path=str(path), daily=daily))
            quality.append(_quality_row(req, status, path=str(path), daily=daily))
            continue
        q = _inspect_file(path)
        status = "available" if q["field_quality_status"] == "pass" else ("paused_no_intraday_expected" if paused else "field_quality_failed")
        coverage.append(_coverage_row(req, status, path=str(path), daily=daily, **q))
        quality.append({"requirement_id": req["requirement_id"], "code": req["code"], "trade_date": req["trade_date"], "path": str(path), **daily, **q})
    return coverage, quality


def _coverage_row(req: dict[str, Any], status: str, path: str = "", daily: dict[str, Any] | None = None, **q: Any) -> dict[str, Any]:
    daily = daily or {}
    return {
        "requirement_id": req["requirement_id"],
        "code": req["code"],
        "trade_date": req["trade_date"],
        "holding_start_date": req["holding_start_date"],
        "next_rebalance_date": req["next_rebalance_date"],
        "sleeve": req["sleeve"],
        "coverage_status": status,
        "path": path,
        "row_count": q.get("row_count", 0),
        "missing_fields": q.get("missing_fields", ""),
        "missing_bar_times": q.get("missing_bar_times", ";".join(REQUIRED_TIMES + ["last_bar"])),
        "paused": daily.get("paused", ""),
        "daily_volume": daily.get("volume", ""),
        "daily_money": daily.get("money", ""),
        "price_file": daily.get("price_file", ""),
        "needs_fetch": status in {"missing_local_5min_file", "indexed_file_not_found", "field_quality_failed"},
        "can_fabricate_from_daily": False,
        "trade_trigger_allowed_after_gate": status == "available",
    }


def _quality_row(req: dict[str, Any], status: str, path: str = "", daily: dict[str, Any] | None = None) -> dict[str, Any]:
    daily = daily or {}
    return {
        "requirement_id": req["requirement_id"],
        "code": req["code"],
        "trade_date": req["trade_date"],
        "path": path,
        "field_quality_status": status,
        "row_count": 0,
        "missing_fields": ";".join(REQUIRED_FIELDS),
        "missing_bar_times": ";".join(REQUIRED_TIMES + ["last_bar"]),
        "paused": daily.get("paused", ""),
        "daily_volume": daily.get("volume", ""),
        "daily_money": daily.get("money", ""),
    }


def _inspect_file(path: Path) -> dict[str, Any]:
    df = pd.read_csv(path)
    missing_fields = [field for field in REQUIRED_FIELDS if field not in df.columns]
    times = {str(value)[:5] for value in df.get("time", pd.Series(dtype=str)).dropna().tolist()}
    missing_times = [time for time in REQUIRED_TIMES if time not in times]
    if not times:
        missing_times.append("last_bar")
    vol_ok = all(col in df.columns and pd.to_numeric(df[col], errors="coerce").notna().all() for col in ["volume", "amount"])
    ohlc_ok = all(col in df.columns and (pd.to_numeric(df[col], errors="coerce") > 0).all() for col in ["open", "high", "low", "close"])
    status = "pass" if not missing_fields and not missing_times and vol_ok and ohlc_ok else "fail"
    return {
        "field_quality_status": status,
        "row_count": int(len(df)),
        "missing_fields": ";".join(missing_fields),
        "present_bar_times": ";".join(sorted(times)),
        "missing_bar_times": ";".join(missing_times),
        "volume_amount_nonempty": vol_ok,
        "ohlc_positive": ohlc_ok,
    }


def _build_fetch_intervals(missing_rows: list[dict[str, Any]], trading_days: list[str]) -> list[dict[str, Any]]:
    day_rank = {day: idx for idx, day in enumerate(trading_days)}
    by_code: dict[str, list[str]] = {}
    for row in missing_rows:
        by_code.setdefault(row["code"], []).append(row["trade_date"])
    intervals = []
    for code, dates in sorted(by_code.items()):
        dates = sorted(set(dates), key=lambda d: day_rank.get(d, 10**9))
        if not dates:
            continue
        start = prev = dates[0]
        for day in dates[1:]:
            if day_rank.get(day, -100) == day_rank.get(prev, -999) + 1:
                prev = day
                continue
            intervals.append(_fetch_interval(code, start, prev, len(intervals) + 1))
            start = prev = day
        intervals.append(_fetch_interval(code, start, prev, len(intervals) + 1))
    return intervals


def _fetch_interval(code: str, start: str, end: str, index: int) -> dict[str, Any]:
    return {
        "queue_id": f"full_holding_fetch_{index:05d}",
        "code": code,
        "bs_code": _to_bs_code(code),
        "fetch_start_date": start,
        "fetch_end_date": end,
        "frequency": "5min",
        "adjustflag": "3_unadjusted",
        "source": "BaoStock",
        "full_holding_period_fetch": True,
        "trade_trigger_allowed": False,
    }


def _fetch_baostock(root: Path, queue: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    import baostock as bs

    login = bs.login()
    if getattr(login, "error_code", "1") != "0":
        blocker = [{"blocker_id": "baostock_login_failed", "severity": "fatal", "status": "blocking", "description": getattr(login, "error_msg", "")}]
        return [], [], [], blocker
    fields = "date,time,code,open,high,low,close,volume,amount,adjustflag"
    fetch_log = []
    raw_index = []
    std_index = []
    try:
        for item in queue:
            started = time.perf_counter()
            code = item["code"]
            bs_code = item["bs_code"]
            start = item["fetch_start_date"]
            end = item["fetch_end_date"]
            raw_path = root / RAW_DIR / f"{start}_{end}" / f"{code.replace('.', '_')}_5min_raw.csv"
            status = "error"
            row_count = 0
            error_type = ""
            error_message = ""
            try:
                rs = bs.query_history_k_data_plus(bs_code, fields, start_date=start, end_date=end, frequency="5", adjustflag="3")
                rows = []
                while rs.error_code == "0" and rs.next():
                    rows.append(rs.get_row_data())
                if rs.error_code != "0":
                    status = "query_error"
                    error_type = str(rs.error_code)
                    error_message = str(rs.error_msg)
                else:
                    raw_path.parent.mkdir(parents=True, exist_ok=True)
                    raw_df = pd.DataFrame(rows, columns=rs.fields)
                    raw_df.to_csv(raw_path, index=False, encoding="utf-8-sig")
                    row_count = int(len(raw_df))
                    if row_count:
                        std_df = normalize_baostock_frame(raw_df, code, bs_code, start, end)
                        for trade_date, day_df in std_df.groupby("trade_date"):
                            if not trade_date:
                                continue
                            std_path = root / STD_DIR / str(trade_date) / f"{code.replace('.', '_')}_5min_standardized.csv"
                            std_path.parent.mkdir(parents=True, exist_ok=True)
                            day_df.to_csv(std_path, index=False, encoding="utf-8-sig")
                            std_index.append({"code": code, "bs_code": bs_code, "trade_date": str(trade_date), "path": _rel(root, std_path), "row_count": int(len(day_df))})
                        status = "pass"
                    else:
                        status = "empty"
                    raw_index.append({"code": code, "bs_code": bs_code, "fetch_start_date": start, "fetch_end_date": end, "path": _rel(root, raw_path), "row_count": row_count})
            except Exception as exc:  # pragma: no cover - external API defensive path
                error_type = type(exc).__name__
                error_message = str(exc)[:500]
            fetch_log.append({**item, "status": status, "row_count": row_count, "raw_path": _rel(root, raw_path) if raw_path.exists() else "", "elapsed_sec": round(time.perf_counter() - started, 3), "error_type": error_type, "error_message": error_message})
    finally:
        try:
            bs.logout()
        except Exception:
            pass
    return fetch_log, raw_index, std_index, _fetch_blockers(fetch_log)


def _write_base_outputs(
    out: Path,
    requirements: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    quality: list[dict[str, Any]],
    fetch_queue: list[dict[str, Any]],
    daily_status: dict[tuple[str, str], dict[str, Any]],
) -> None:
    _write_csv(out / "v5e_full_holding_5min_requirement.csv", requirements)
    _write_csv(out / "v5e_full_holding_5min_coverage_audit.csv", coverage)
    _write_csv(out / "v5e_full_holding_5min_field_quality_audit.csv", quality)
    _write_csv(out / "v5e_full_holding_5min_fetch_queue.csv", fetch_queue)
    status_rows = [{"code": code, "trade_date": day, **value} for (code, day), value in sorted(daily_status.items())]
    _write_csv(out / "v5e_full_holding_daily_status_crosscheck.csv", status_rows)


def _pm_gate_decision(requirements: list[dict[str, Any]], coverage: list[dict[str, Any]], fetch_blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    available = sum(1 for row in coverage if row["coverage_status"] == "available")
    paused = sum(1 for row in coverage if row["coverage_status"] == "paused_no_intraday_expected")
    total = len(requirements)
    effective = (available + paused) / total if total else 0.0
    if fetch_blockers:
        decision = "full_holding_5min_fetch_review_required"
    elif effective >= 0.995:
        decision = "full_holding_5min_ready_for_rolling_research"
    else:
        decision = "full_holding_5min_partial_coverage_review_required"
    return [
        {
            "pm_gate_decision": decision,
            "required_stock_dates": total,
            "available_stock_dates": available,
            "paused_no_intraday_stock_dates": paused,
            "effective_coverage_rate": effective,
            "trade_trigger_allowed": decision == "full_holding_5min_ready_for_rolling_research",
            "accepted": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
        }
    ]


def _data_blockers(unresolved: list[dict[str, Any]], paused: list[dict[str, Any]], fetch_blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = list(fetch_blockers)
    if unresolved:
        rows.append({"blocker_id": "unresolved_full_holding_5min_missing", "severity": "data_gate", "status": "review_required", "count": len(unresolved)})
    if paused:
        rows.append({"blocker_id": "paused_no_intraday_expected", "severity": "data_quality", "status": "not_fatal", "count": len(paused)})
    if not rows:
        rows.append({"blocker_id": "none", "severity": "none", "status": "not_blocking"})
    return rows


def _fetch_blockers(fetch_log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in fetch_log if row["status"] not in {"pass", "empty"}]
    empty = [row for row in fetch_log if row["status"] == "empty"]
    rows = []
    if failed:
        rows.append({"blocker_id": "baostock_fetch_failures", "severity": "data_gate", "status": "review_required", "count": len(failed)})
    if empty:
        rows.append({"blocker_id": "baostock_empty_intervals", "severity": "data_quality", "status": "review_required", "count": len(empty)})
    return rows


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_gate": "v5e_full_holding_rolling_intraday_research",
            "task": "Run rolling full holding-period 5min research models",
            "allowed": decision in {"full_holding_5min_ready_for_rolling_research", "full_holding_5min_fetch_review_required", "full_holding_5min_partial_coverage_review_required"},
        }
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    required_stock_dates: int = 0,
    available_stock_dates: int = 0,
    paused_stock_dates: int = 0,
    missing_stock_dates: int = 0,
    fetch_interval_count: int = 0,
    fetch_pass_count: int = 0,
    fetch_empty_count: int = 0,
    fetch_failure_count: int = 0,
    stored_raw_interval_count: int = 0,
    stored_standardized_file_count: int = 0,
) -> dict[str, Any]:
    effective = (available_stock_dates + paused_stock_dates) / required_stock_dates if required_stock_dates else 0.0
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_full_holding_5min_data_gate",
        "status": status,
        "pm_gate_decision": decision,
        "scope": "full_holding_period_5min",
        "required_stock_dates": required_stock_dates,
        "available_stock_dates": available_stock_dates,
        "paused_no_intraday_stock_dates": paused_stock_dates,
        "missing_stock_dates": missing_stock_dates,
        "effective_coverage_rate_pct": round(effective * 100.0, 4),
        "fetch_interval_count": fetch_interval_count,
        "fetch_pass_count": fetch_pass_count,
        "fetch_empty_count": fetch_empty_count,
        "fetch_failure_count": fetch_failure_count,
        "stored_raw_interval_count": stored_raw_interval_count,
        "stored_standardized_file_count": stored_standardized_file_count,
        "minute_data_used_for_trigger": False,
        "rolling_research_required": True,
        "accepted": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(requirements: list[dict[str, Any]], coverage: list[dict[str, Any]], gate: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# V5e Full Holding-Period 5min Data Gate",
            "",
            f"- PM decision: `{gate[0]['pm_gate_decision']}`",
            f"- Required stock-dates: {len(requirements)}",
            f"- Available stock-dates: {sum(1 for row in coverage if row['coverage_status'] == 'available')}",
            f"- Paused/no intraday stock-dates: {sum(1 for row in coverage if row['coverage_status'] == 'paused_no_intraday_expected')}",
            "- No 5min bars are fabricated from daily data.",
            "- V57f core remains unchanged.",
            "",
        ]
    )


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Full Holding 5min Data Gate Rules",
            "",
            "- Full V57f holding stock-date scope only.",
            "- Do not fabricate minute data for paused days.",
            "- Do rolling research before using 5min triggers.",
            "- Do not modify V57f or mark accepted.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [REPAIRED_RUN / "daily_returns.csv", REPAIRED_RUN / "holdings.csv", REPAIRED_RUN / "rebalance_signals.csv", PRICE_DIR]
    return [{"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)} for path in required if not (root / path).exists()]


def _days_between(trading_days: list[str], start: str, end_exclusive: str) -> list[str]:
    return [day for day in trading_days if day >= start and (not end_exclusive or day < end_exclusive)]


def _next_rebalance(day: str, rebalance_dates: list[str]) -> str:
    later = [d for d in rebalance_dates if d > day]
    return later[0] if later else ""


def _to_bs_code(code: str) -> str:
    ticker = code.split(".")[0]
    return f"sh.{ticker}" if code.endswith(".XSHG") else f"sz.{ticker}"


def _is_paused(daily: dict[str, Any]) -> bool:
    paused = str(daily.get("paused", ""))
    volume = pd.to_numeric(daily.get("volume", ""), errors="coerce")
    money = pd.to_numeric(daily.get("money", ""), errors="coerce")
    return paused in {"1", "1.0", "True", "true"} or (pd.notna(volume) and volume == 0 and pd.notna(money) and money == 0)


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


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
    result = run_v5e_full_holding_5min_data_gate()
    print(json.dumps(result, ensure_ascii=False, indent=2))

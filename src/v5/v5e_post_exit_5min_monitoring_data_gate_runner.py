from __future__ import annotations

import csv
import json
import time
from bisect import bisect_right
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v5.v5d_baostock_5min_data_gate import normalize_baostock_frame


OUT_DIR = Path("v5e_post_exit_5min_monitoring_data_gate") / "current"
RAW_DIR = Path("v5e_post_exit_5min_monitoring_data_gate") / "data_raw"
STD_DIR = Path("v5e_post_exit_5min_monitoring_data_gate") / "data_standardized"
CASH_POLICY_DIR = Path("v5e_cash_policy_review") / "current"
TRIGGER_DAY_DIR = Path("v5e_trigger_day_5min_execution_data_gate") / "current"
TRIGGER_DAY_STD_INDEX = TRIGGER_DAY_DIR / "v5e_exit_5min_standardized_index.csv"
V5D_STD_INDEX = Path("v5d_baostock_5min_data_gate") / "current" / "v5d_baostock_5min_standardized_index.csv"
V5E_EXIT_LOG = Path("v5e_limited_engineering_loop") / "current" / "v5e_exit_action_log.csv"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)

V5E_MAIN = "v5e_profit_lock_main_20pct_sell50"
REQUIRED_TIMES = ["09:35", "09:40", "10:00", "14:55"]
REQUIRED_FIELDS = ["open", "high", "low", "close", "volume", "amount", "time"]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_post_exit_5min_monitoring_data_gate(root: Path = Path("."), fetch: bool = True) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_blockers(root)
    if blockers:
        _write_csv(out / "v5e_post_exit_5min_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_post_exit_5min_monitoring_summary.json", summary)
        return summary

    requirements = _build_requirements(root)
    local_index = _local_index(root)
    coverage, quality = _coverage_audit(root, requirements, local_index)
    missing = [row for row in coverage if row["coverage_status"] != "available"]
    available = [row for row in coverage if row["coverage_status"] == "available"]
    fetch_queue = _fetch_queue(missing)
    _write_base_outputs(out, requirements, coverage, quality, missing, available, fetch_queue)

    fetch_log: list[dict[str, Any]] = []
    raw_index: list[dict[str, Any]] = []
    std_index: list[dict[str, Any]] = []
    fetch_blockers: list[dict[str, Any]] = []
    if fetch and fetch_queue:
        fetch_log, raw_index, std_index, fetch_blockers = _run_baostock_fetch(root, fetch_queue)
        _write_csv(out / "v5e_post_exit_5min_fetch_log.csv", fetch_log)
        _write_csv(out / "v5e_post_exit_5min_raw_index.csv", raw_index)
        _write_csv(out / "v5e_post_exit_5min_standardized_index.csv", std_index)
        _write_csv(out / "v5e_post_exit_5min_fetch_blockers.csv", fetch_blockers)
        local_index = _local_index(root)
        coverage, quality = _coverage_audit(root, requirements, local_index)
        missing = [row for row in coverage if row["coverage_status"] != "available"]
        available = [row for row in coverage if row["coverage_status"] == "available"]
        fetch_queue = _fetch_queue(missing)
        _write_base_outputs(out, requirements, coverage, quality, missing, available, fetch_queue)
    else:
        _write_csv(out / "v5e_post_exit_5min_fetch_log.csv", fetch_log)
        _write_csv(out / "v5e_post_exit_5min_raw_index.csv", raw_index)
        _write_csv(out / "v5e_post_exit_5min_standardized_index.csv", std_index)
        _write_csv(out / "v5e_post_exit_5min_fetch_blockers.csv", fetch_blockers)

    raw_scan_index = _scan_post_exit_index(root, RAW_DIR, "_5min_raw.csv")
    std_scan_index = _scan_post_exit_index(root, STD_DIR, "_5min_standardized.csv")
    if raw_scan_index:
        _write_csv(out / "v5e_post_exit_5min_raw_index.csv", raw_scan_index)
    if std_scan_index:
        _write_csv(out / "v5e_post_exit_5min_standardized_index.csv", std_scan_index)

    monitoring_metrics = _monitoring_metrics(root, requirements, coverage)
    gate = _pm_gate_decision(coverage, fetch, fetch_blockers)
    blockers = _data_blockers(missing, fetch_blockers)
    next_queue = _next_queue(gate[0]["pm_gate_decision"])

    _write_csv(out / "v5e_post_exit_5min_monitoring_metrics.csv", monitoring_metrics)
    _write_csv(out / "v5e_post_exit_5min_pm_gate_decision.csv", gate)
    _write_csv(out / "v5e_post_exit_5min_next_queue.csv", next_queue)
    _write_csv(out / "v5e_post_exit_5min_blockers.csv", blockers)
    (out / "v5e_post_exit_5min_prompt.md").write_text(_prompt_text(), encoding="utf-8")
    (out / "v5e_post_exit_5min_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    summary = _summary(
        "completed_post_exit_5min_monitoring_data_gate",
        gate[0]["pm_gate_decision"],
        [],
        requirement_count=len(requirements),
        available_count=len(available),
        missing_count=len(missing),
        fetch_queue_count=len(fetch_queue),
        fetch_log=fetch_log,
        metrics=monitoring_metrics,
    )
    _write_json(out / "v5e_post_exit_5min_monitoring_summary.json", summary)
    (out / "v5e_post_exit_5min_monitoring_report.md").write_text(
        _report(summary, gate, monitoring_metrics),
        encoding="utf-8",
    )
    return summary


def _build_requirements(root: Path) -> list[dict[str, Any]]:
    daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv")
    trading_days = sorted(daily["trade_date"].astype(str).unique().tolist())
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv")
    rebalance_dates = sorted(signals["trade_date"].astype(str).unique().tolist())
    exits = pd.read_csv(root / V5E_EXIT_LOG)
    exits = exits[exits["version_id"].eq(V5E_MAIN)].copy()
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for idx, row in exits.reset_index(drop=True).iterrows():
        code = str(row["code"])
        trigger_date = str(row["trigger_date"])
        execution_date = str(row["execution_date"])
        next_rebalance = _next_rebalance(trigger_date, rebalance_dates)
        source_id = f"{trigger_date}|{execution_date}|{code}|{idx + 1}"
        for day in _days_between(trading_days, trigger_date, next_rebalance):
            key = (code, day)
            if key not in rows:
                rows[key] = {
                    "monitoring_id": f"{code}|{day}",
                    "version_id": V5E_MAIN,
                    "code": code,
                    "trade_date": day,
                    "trigger_date_min": trigger_date,
                    "execution_date_min": execution_date,
                    "next_rebalance_date": next_rebalance,
                    "source_exit_action_ids": source_id,
                    "source_exit_count": 1,
                    "scope": "post_exit_to_next_rebalance_monitoring",
                    "purpose": "audit_missed_upside_avoided_loss_cash_drag_only",
                    "trade_trigger_allowed": False,
                    "required_fields": ";".join(REQUIRED_FIELDS),
                    "required_bar_times": ";".join(REQUIRED_TIMES + ["last_bar"]),
                }
            else:
                rows[key]["source_exit_action_ids"] += ";" + source_id
                rows[key]["source_exit_count"] += 1
    return sorted(rows.values(), key=lambda r: (r["trade_date"], r["code"]))


def _local_index(root: Path) -> dict[tuple[str, str], str]:
    result: dict[tuple[str, str], str] = {}
    for path, date_col in [
        (root / V5D_STD_INDEX, "rebalance_date"),
        (root / TRIGGER_DAY_STD_INDEX, "trade_date"),
        (root / OUT_DIR / "v5e_post_exit_5min_standardized_index.csv", "trade_date"),
    ]:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if date_col in row and row.get("path"):
                    result[(row["code"], row[date_col])] = row["path"]
    for row in _scan_post_exit_index(root, STD_DIR, "_5min_standardized.csv"):
        result[(row["code"], row["trade_date"])] = row["path"]
    return result


def _scan_post_exit_index(root: Path, base_dir: Path, suffix: str) -> list[dict[str, Any]]:
    base = root / base_dir
    if not base.exists():
        return []
    rows: list[dict[str, Any]] = []
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
        rows.append(
            {
                "code": code,
                "bs_code": _to_bs_code(code),
                "trade_date": trade_date,
                "path": _rel(root, path),
                "row_count": row_count,
                "index_source": "post_exit_data_directory_scan",
            }
        )
    return rows


def _coverage_audit(
    root: Path,
    requirements: list[dict[str, Any]],
    local_index: dict[tuple[str, str], str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    coverage: list[dict[str, Any]] = []
    quality: list[dict[str, Any]] = []
    for req in requirements:
        path_text = local_index.get((req["code"], req["trade_date"]), "")
        if not path_text:
            coverage.append(_coverage_row(req, "missing_local_5min_file"))
            quality.append(_quality_row(req, "missing_file"))
            continue
        path = root / Path(path_text)
        if not path.exists():
            coverage.append(_coverage_row(req, "missing_local_5min_file", path=str(path)))
            quality.append(_quality_row(req, "indexed_file_not_found", path=str(path)))
            continue
        q = _inspect_file(path)
        status = "available" if q["field_quality_status"] == "pass" else "field_quality_failed"
        coverage.append(_coverage_row(req, status, path=str(path), **q))
        quality.append({"monitoring_id": req["monitoring_id"], "code": req["code"], "trade_date": req["trade_date"], "path": str(path), **q})
    return coverage, quality


def _coverage_row(req: dict[str, Any], status: str, path: str = "", **quality: Any) -> dict[str, Any]:
    return {
        "monitoring_id": req["monitoring_id"],
        "version_id": req["version_id"],
        "code": req["code"],
        "trade_date": req["trade_date"],
        "next_rebalance_date": req["next_rebalance_date"],
        "coverage_status": status,
        "path": path,
        "row_count": quality.get("row_count", 0),
        "missing_fields": quality.get("missing_fields", ""),
        "missing_bar_times": quality.get("missing_bar_times", ";".join(REQUIRED_TIMES + ["last_bar"])),
        "volume_amount_nonempty": quality.get("volume_amount_nonempty", False),
        "can_use_for_monitoring": status == "available",
        "trade_trigger_allowed": False,
        "data_gate_blocker": status != "available",
    }


def _quality_row(req: dict[str, Any], status: str, path: str = "") -> dict[str, Any]:
    return {
        "monitoring_id": req["monitoring_id"],
        "code": req["code"],
        "trade_date": req["trade_date"],
        "path": path,
        "field_quality_status": status,
        "row_count": 0,
        "missing_fields": ";".join(REQUIRED_FIELDS),
        "missing_bar_times": ";".join(REQUIRED_TIMES + ["last_bar"]),
        "volume_amount_nonempty": False,
    }


def _inspect_file(path: Path) -> dict[str, Any]:
    df = pd.read_csv(path)
    missing_fields = [field for field in REQUIRED_FIELDS if field not in df.columns]
    times = {str(value)[:5] for value in df.get("time", pd.Series(dtype=str)).dropna().tolist()}
    missing_times = [time for time in REQUIRED_TIMES if time not in times]
    if not times:
        missing_times.append("last_bar")
    vol_ok = all(
        col in df.columns and pd.to_numeric(df[col], errors="coerce").notna().all()
        for col in ["volume", "amount"]
    )
    ohlc_ok = all(
        col in df.columns and (pd.to_numeric(df[col], errors="coerce") > 0).all()
        for col in ["open", "high", "low", "close"]
    )
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


def _fetch_queue(missing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in sorted(missing, key=lambda r: (r["trade_date"], r["code"])):
        rows.append(
            {
                "queue_id": f"post_exit_fetch_{len(rows) + 1:05d}",
                "code": row["code"],
                "bs_code": _to_bs_code(row["code"]),
                "fetch_start_date": row["trade_date"],
                "fetch_end_date": row["trade_date"],
                "frequency": "5min",
                "adjustflag": "3_unadjusted",
                "source": "BaoStock",
                "reason": "missing_post_exit_5min_monitoring_window",
                "full_holding_period_fetch": False,
                "trade_trigger_allowed": False,
            }
        )
    return rows


def _run_baostock_fetch(root: Path, queue: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    import baostock as bs

    login = bs.login()
    if getattr(login, "error_code", "1") != "0":
        blocker = [{"blocker_id": "baostock_login_failed", "severity": "fatal", "status": "blocking", "description": getattr(login, "error_msg", "")}]
        return [], [], [], blocker
    fields = "date,time,code,open,high,low,close,volume,amount,adjustflag"
    fetch_log: list[dict[str, Any]] = []
    raw_index: list[dict[str, Any]] = []
    std_index: list[dict[str, Any]] = []
    try:
        for item in queue:
            started = time.perf_counter()
            code = item["code"]
            bs_code = item["bs_code"]
            date = item["fetch_start_date"]
            raw_path = root / RAW_DIR / date / f"{code.replace('.', '_')}_5min_raw.csv"
            std_path = root / STD_DIR / date / f"{code.replace('.', '_')}_5min_standardized.csv"
            status = "error"
            row_count = 0
            error_type = ""
            error_message = ""
            try:
                rs = bs.query_history_k_data_plus(bs_code, fields, start_date=date, end_date=date, frequency="5", adjustflag="3")
                rows: list[list[str]] = []
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
                    std_df = normalize_baostock_frame(raw_df, code, bs_code, date, date)
                    std_path.parent.mkdir(parents=True, exist_ok=True)
                    std_df.to_csv(std_path, index=False, encoding="utf-8-sig")
                    row_count = int(len(std_df))
                    status = "pass" if row_count else "empty"
                    raw_index.append({"code": code, "bs_code": bs_code, "trade_date": date, "path": _rel(root, raw_path), "row_count": int(len(raw_df))})
                    std_index.append({"code": code, "bs_code": bs_code, "trade_date": date, "path": _rel(root, std_path), "row_count": row_count})
            except Exception as exc:  # pragma: no cover - external API defensive path
                error_type = type(exc).__name__
                error_message = str(exc)[:500]
            fetch_log.append(
                {
                    **item,
                    "status": status,
                    "row_count": row_count,
                    "raw_path": _rel(root, raw_path) if raw_path.exists() else "",
                    "standardized_path": _rel(root, std_path) if std_path.exists() else "",
                    "elapsed_sec": round(time.perf_counter() - started, 3),
                    "error_type": error_type,
                    "error_message": error_message,
                }
            )
    finally:
        try:
            bs.logout()
        except Exception:
            pass
    blockers = _fetch_blockers(fetch_log)
    return fetch_log, raw_index, std_index, blockers


def _monitoring_metrics(root: Path, requirements: list[dict[str, Any]], coverage: list[dict[str, Any]]) -> list[dict[str, Any]]:
    available = {row["monitoring_id"]: row for row in coverage if row["coverage_status"] == "available"}
    rows = []
    for req in requirements:
        cov = available.get(req["monitoring_id"])
        if not cov:
            continue
        df = pd.read_csv(Path(cov["path"]))
        close = pd.to_numeric(df["close"], errors="coerce").dropna()
        high = pd.to_numeric(df["high"], errors="coerce").dropna()
        low = pd.to_numeric(df["low"], errors="coerce").dropna()
        volume = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)
        amount = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        vwap = float(amount.sum() / volume.sum()) if float(volume.sum()) > 0 else 0.0
        rows.append(
            {
                "monitoring_id": req["monitoring_id"],
                "code": req["code"],
                "trade_date": req["trade_date"],
                "next_rebalance_date": req["next_rebalance_date"],
                "bar_count": int(len(df)),
                "first_close": float(close.iloc[0]) if len(close) else "",
                "last_close": float(close.iloc[-1]) if len(close) else "",
                "intraday_return_first_to_last": (float(close.iloc[-1]) / float(close.iloc[0]) - 1.0) if len(close) and float(close.iloc[0]) else "",
                "intraday_high": float(high.max()) if len(high) else "",
                "intraday_low": float(low.min()) if len(low) else "",
                "day_5min_vwap": vwap,
                "monitoring_only": True,
                "trade_trigger_allowed": False,
            }
        )
    return rows


def _pm_gate_decision(coverage: list[dict[str, Any]], fetch: bool, blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    available = sum(1 for row in coverage if row["coverage_status"] == "available")
    total = len(coverage)
    coverage_rate = available / total if total else 0.0
    if blockers:
        decision = "post_exit_5min_monitoring_partial_fetch_review_required"
    elif coverage_rate == 1.0:
        decision = "post_exit_5min_monitoring_ready_for_audit_not_trigger"
    elif fetch:
        decision = "post_exit_5min_monitoring_fetch_incomplete"
    else:
        decision = "post_exit_5min_monitoring_fetch_queue_ready"
    return [
        {
            "pm_gate_decision": decision,
            "coverage_rate": coverage_rate,
            "available_stock_dates": available,
            "required_stock_dates": total,
            "trade_trigger_allowed": False,
            "full_holding_period_trigger_allowed": False,
            "accepted": False,
            "reason": "Medium post-exit 5min data is monitoring/audit evidence only; it cannot trigger V5e trades.",
            "next_gate": "post_exit_5min_monitoring_audit_packet" if coverage_rate == 1.0 else "repair_post_exit_5min_missing_data",
        }
    ]


def _write_base_outputs(
    out: Path,
    requirements: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    quality: list[dict[str, Any]],
    missing: list[dict[str, Any]],
    available: list[dict[str, Any]],
    fetch_queue: list[dict[str, Any]],
) -> None:
    _write_csv(out / "v5e_post_exit_5min_requirement.csv", requirements)
    _write_csv(out / "v5e_post_exit_5min_coverage_audit.csv", coverage)
    _write_csv(out / "v5e_post_exit_5min_field_quality_audit.csv", quality)
    _write_csv(out / "v5e_post_exit_5min_missing_windows.csv", missing)
    _write_csv(out / "v5e_post_exit_5min_available_windows.csv", available)
    _write_csv(out / "v5e_post_exit_5min_fetch_queue.csv", fetch_queue)


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    requirement_count: int = 0,
    available_count: int = 0,
    missing_count: int = 0,
    fetch_queue_count: int = 0,
    fetch_log: list[dict[str, Any]] | None = None,
    metrics: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    fetch_log = fetch_log or []
    metrics = metrics or []
    coverage_rate = available_count / requirement_count if requirement_count else 0.0
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_post_exit_5min_monitoring_data_gate",
        "status": status,
        "pm_gate_decision": decision,
        "scope": "medium_post_exit_to_next_rebalance",
        "full_holding_period_fetch": False,
        "minute_data_used_for_trigger": False,
        "trade_trigger_allowed": False,
        "accepted": False,
        "v57f_core_modified": False,
        "joinquant_started": False,
        "network_fetch_started": bool(fetch_log),
        "required_stock_dates": requirement_count,
        "available_stock_dates": available_count,
        "missing_stock_dates": missing_count,
        "coverage_rate_pct": round(coverage_rate * 100.0, 4),
        "fetch_task_count": len(fetch_log),
        "fetch_pass_count": sum(1 for row in fetch_log if row.get("status") == "pass"),
        "fetch_empty_count": sum(1 for row in fetch_log if row.get("status") == "empty"),
        "fetch_failure_count": sum(1 for row in fetch_log if row.get("status") not in {"pass", "empty"}),
        "monitoring_metric_rows": len(metrics),
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(summary: dict[str, Any], gate: list[dict[str, Any]], metrics: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# V5e Post-Exit 5min Monitoring Data Gate",
            "",
            f"- PM decision: `{gate[0]['pm_gate_decision']}`",
            "- Scope: medium post-exit monitoring from trigger date to day before next V57f rebalance.",
            "- Use: audit missed upside, avoided loss, cash drag opportunity cost.",
            "- Not allowed: 5min-triggered trades, reentry, threshold changes, accepted marking.",
            "",
            "## Coverage",
            f"- Required stock-dates: {summary['required_stock_dates']}",
            f"- Available stock-dates: {summary['available_stock_dates']}",
            f"- Missing stock-dates: {summary['missing_stock_dates']}",
            f"- Coverage: {summary['coverage_rate_pct']}%",
            f"- Fetch tasks run: {summary['fetch_task_count']}",
            f"- Monitoring metric rows: {summary['monitoring_metric_rows']}",
            "",
        ]
    )


def _data_blockers(missing: list[dict[str, Any]], fetch_blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = list(fetch_blockers)
    if missing:
        rows.append(
            {
                "blocker_id": "missing_post_exit_5min_monitoring_windows",
                "severity": "data_gate",
                "status": "review_required",
                "missing_count": len(missing),
                "description": "Some medium post-exit monitoring stock-dates remain unavailable.",
            }
        )
    if not rows:
        rows.append({"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Post-exit monitoring data gate complete."})
    return rows


def _fetch_blockers(fetch_log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in fetch_log if row["status"] not in {"pass", "empty"}]
    empty = [row for row in fetch_log if row["status"] == "empty"]
    rows = []
    if failed:
        rows.append({"blocker_id": "baostock_fetch_failures", "severity": "data_gate", "status": "review_required", "count": len(failed)})
    if empty:
        rows.append({"blocker_id": "baostock_empty_responses", "severity": "data_quality", "status": "review_required", "count": len(empty)})
    return rows


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_gate": "post_exit_5min_monitoring_audit_packet",
            "task": "V5e post-exit 5min monitoring audit",
            "scope": "Use monitoring data to attribute missed upside and cash drag; no trade trigger.",
            "allowed": decision == "post_exit_5min_monitoring_ready_for_audit_not_trigger",
        },
        {
            "priority": 2,
            "next_gate": "v5e_sleeve_cash_policy_quant_spec",
            "task": "Continue sleeve cash policy spec",
            "scope": "Spec only; no reentry or replacement.",
            "allowed": True,
        },
    ]


def _prompt_text() -> str:
    return """工作目录：
D:\\hh\\codex\\v5

任务名称：
V5e post-exit 5min monitoring audit packet

任务目标：
使用 `v5e_post_exit_5min_monitoring_data_gate/current/` 下已覆盖的 medium post-exit 5分钟数据，分析 V5e 已退出股票从触发后到下一次 V57f 调仓前的 missed upside、avoided loss 和 cash drag opportunity cost。

边界：
- 5分钟数据只用于 monitoring/audit。
- 不得用 5分钟触发新交易。
- 不得允许 reentry before next rebalance。
- 不得修改 V57f / V5e 阈值。
- 不得标记 accepted。
"""


def _prompt_text() -> str:
    return """工作目录：
D:\\hh\\codex\\v5

任务名称：
V5e post-exit 5min monitoring audit packet

任务目标：
使用 `v5e_post_exit_5min_monitoring_data_gate/current/` 下已经生成的 medium post-exit 5分钟数据，分析 V5e 已退出股票从 trigger_date 后到下一次 V57f 调仓前的 missed upside、avoided loss 和 cash drag opportunity cost。

边界：
1. 5分钟数据只允许用于 monitoring / audit。
2. 不得用 5分钟走势触发新交易。
3. 不得允许 reentry before next rebalance。
4. 不得修改 V57f、V5e 阈值或 sell fraction。
5. 不得新增止盈阈值或参数扫描。
6. 不得标记 accepted。
7. 不得把 V5e 当作 V57f replacement。

必须先阅读：
- v5e_post_exit_5min_monitoring_data_gate\\current\\v5e_post_exit_5min_monitoring_summary.json
- v5e_post_exit_5min_monitoring_data_gate\\current\\v5e_post_exit_5min_requirement.csv
- v5e_post_exit_5min_monitoring_data_gate\\current\\v5e_post_exit_5min_coverage_audit.csv
- v5e_post_exit_5min_monitoring_data_gate\\current\\v5e_post_exit_5min_monitoring_metrics.csv
- v5e_post_exit_5min_monitoring_data_gate\\current\\v5e_post_exit_5min_missing_windows.csv
- v5e_cash_policy_review\\current\\v5e_cash_policy_review_summary.json
- v5e_limited_engineering_loop\\current\\v5e_exit_action_log.csv

输出要求：
生成 post-exit monitoring audit packet，至少包含退出后 5分钟表现、错失上涨/避免亏损归因、现金拖累机会成本、缺失 5分钟窗口影响评估、PM 下一门建议和 agent 队列。
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Post-Exit 5min Monitoring Data Gate Rules",
            "",
            "- Medium scope only: exited stocks from trigger date to before next V57f rebalance.",
            "- Do not fetch full holding-period data.",
            "- Do not use 5min data to trigger trades.",
            "- Do not allow reentry before next rebalance.",
            "- Do not modify V57f or V5e thresholds.",
            "- BaoStock data is unadjusted 5min execution/monitoring data.",
            "",
        ]
    )


def _missing_blockers(root: Path) -> list[dict[str, Any]]:
    required = [
        CASH_POLICY_DIR / "v5e_cash_policy_review_summary.json",
        CASH_POLICY_DIR / "v5e_post_exit_5min_monitoring_spec.csv",
        V5E_EXIT_LOG,
        REPAIRED_RUN / "daily_returns.csv",
        REPAIRED_RUN / "rebalance_signals.csv",
        TRIGGER_DAY_STD_INDEX,
    ]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "status": "blocking",
            "path": str(path),
            "description": "Required V5e post-exit monitoring input is missing.",
        }
        for path in required
        if not (root / path).exists()
    ]


def _days_between(trading_days: list[str], start: str, end_exclusive: str) -> list[str]:
    return [day for day in trading_days if day >= start and (not end_exclusive or day < end_exclusive)]


def _next_rebalance(day: str, rebalance_dates: list[str]) -> str:
    idx = bisect_right(rebalance_dates, day)
    return rebalance_dates[idx] if idx < len(rebalance_dates) else ""


def _to_bs_code(code: str) -> str:
    ticker = code.split(".")[0]
    if code.endswith(".XSHG"):
        return f"sh.{ticker}"
    if code.endswith(".XSHE"):
        return f"sz.{ticker}"
    return code


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
    result = run_v5e_post_exit_5min_monitoring_data_gate()
    print(json.dumps(result, ensure_ascii=False, indent=2))

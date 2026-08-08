from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v5.v5d_baostock_5min_data_gate import normalize_baostock_frame
from v5.v5e_trigger_day_5min_data_gate_runner import (
    OUT_DIR,
    run_v5e_trigger_day_5min_data_gate,
)


RAW_DIR = Path("v5e_trigger_day_5min_execution_data_gate") / "data_raw"
STD_DIR = Path("v5e_trigger_day_5min_execution_data_gate") / "data_standardized"
FETCH_QUEUE = OUT_DIR / "v5e_exit_5min_fetch_queue.csv"
FETCH_LOG = OUT_DIR / "v5e_exit_5min_baostock_fetch_log.csv"
RAW_INDEX = OUT_DIR / "v5e_exit_5min_raw_index.csv"
STD_INDEX = OUT_DIR / "v5e_exit_5min_standardized_index.csv"
FETCH_SUMMARY = OUT_DIR / "v5e_exit_5min_baostock_fetch_summary.json"
FETCH_BLOCKERS = OUT_DIR / "v5e_exit_5min_baostock_fetch_blockers.csv"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_trigger_day_5min_baostock_fetch(root: Path = Path("."), limit: int | None = None) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    queue_path = root / FETCH_QUEUE
    if not queue_path.exists():
        audit_summary = run_v5e_trigger_day_5min_data_gate(root)
        if audit_summary.get("fetch_queue_count", 0) == 0:
            summary = _summary("already_complete_no_fetch_needed", [], [], [], audit_summary)
            _write_json(root / FETCH_SUMMARY, summary)
            return summary
    queue = pd.read_csv(queue_path)
    if limit is not None:
        queue = queue.head(limit).copy()
    if queue.empty:
        audit_summary = run_v5e_trigger_day_5min_data_gate(root)
        summary = _summary("already_complete_no_fetch_needed", [], [], [], audit_summary)
        _write_json(root / FETCH_SUMMARY, summary)
        return summary

    try:
        import baostock as bs
    except Exception as exc:
        blockers = [_blocker("baostock_import_failed", str(exc))]
        _write_csv(root / FETCH_BLOCKERS, blockers)
        summary = _summary("blocked_baostock_import_failed", [], [], blockers, {})
        _write_json(root / FETCH_SUMMARY, summary)
        return summary

    try:
        login = bs.login()
    except Exception as exc:
        blockers = [_blocker("baostock_login_exception", str(exc))]
        _write_csv(root / FETCH_BLOCKERS, blockers)
        summary = _summary("blocked_baostock_login_failed", [], [], blockers, {})
        _write_json(root / FETCH_SUMMARY, summary)
        return summary

    if getattr(login, "error_code", "1") != "0":
        blockers = [_blocker("baostock_login_failed", getattr(login, "error_msg", ""))]
        _write_csv(root / FETCH_BLOCKERS, blockers)
        summary = _summary("blocked_baostock_login_failed", [], [], blockers, {})
        _write_json(root / FETCH_SUMMARY, summary)
        return summary

    fetch_rows: list[dict[str, Any]] = []
    raw_index: list[dict[str, Any]] = []
    std_index: list[dict[str, Any]] = []
    fields = "date,time,code,open,high,low,close,volume,amount,adjustflag"
    try:
        for _, item in queue.iterrows():
            started = time.perf_counter()
            code = str(item["code"])
            bs_code = str(item["bs_code"])
            start_date = str(item["fetch_start_date"])
            end_date = str(item["fetch_end_date"])
            raw_path = root / RAW_DIR / start_date / f"{code.replace('.', '_')}_5min_raw.csv"
            std_path = root / STD_DIR / start_date / f"{code.replace('.', '_')}_5min_standardized.csv"
            status = "error"
            row_count = 0
            error_type = ""
            error_message = ""
            try:
                rs = bs.query_history_k_data_plus(
                    bs_code,
                    fields,
                    start_date=start_date,
                    end_date=end_date,
                    frequency="5",
                    adjustflag="3",
                )
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
                    std_df = normalize_baostock_frame(raw_df, code, bs_code, start_date, end_date)
                    std_path.parent.mkdir(parents=True, exist_ok=True)
                    std_df.to_csv(std_path, index=False, encoding="utf-8-sig")
                    row_count = int(len(std_df))
                    status = "pass" if row_count else "empty"
                    raw_index.append(
                        {
                            "code": code,
                            "bs_code": bs_code,
                            "trade_date": start_date,
                            "path": _rel(root, raw_path),
                            "row_count": int(len(raw_df)),
                        }
                    )
                    std_index.append(
                        {
                            "code": code,
                            "bs_code": bs_code,
                            "trade_date": start_date,
                            "path": _rel(root, std_path),
                            "row_count": row_count,
                        }
                    )
            except Exception as exc:  # pragma: no cover - external API defensive path
                error_type = type(exc).__name__
                error_message = str(exc)[:500]
            fetch_rows.append(
                {
                    "queue_id": item.get("queue_id", ""),
                    "code": code,
                    "bs_code": bs_code,
                    "fetch_start_date": start_date,
                    "fetch_end_date": end_date,
                    "frequency": "5min",
                    "adjustflag": "3_unadjusted",
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

    _write_csv(root / FETCH_LOG, fetch_rows)
    _write_csv(root / RAW_INDEX, raw_index)
    _write_csv(root / STD_INDEX, std_index)
    blockers = _fetch_blockers(fetch_rows)
    _write_csv(root / FETCH_BLOCKERS, blockers)
    audit_summary = run_v5e_trigger_day_5min_data_gate(root)
    summary = _summary("completed_baostock_fetch_and_rerun_data_gate", fetch_rows, std_index, blockers, audit_summary)
    _write_json(root / FETCH_SUMMARY, summary)
    return summary


def _fetch_blockers(fetch_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in fetch_rows if row["status"] not in {"pass", "empty"}]
    empty = [row for row in fetch_rows if row["status"] == "empty"]
    blockers: list[dict[str, Any]] = []
    if failed:
        blockers.append(
            {
                "blocker_id": "baostock_fetch_failures",
                "severity": "data_gate",
                "status": "review_required",
                "count": len(failed),
                "description": "Some BaoStock code-date fetches failed and remain missing.",
            }
        )
    if empty:
        blockers.append(
            {
                "blocker_id": "baostock_empty_5min_responses",
                "severity": "data_quality",
                "status": "review_required",
                "count": len(empty),
                "description": "BaoStock returned no 5min bars for some code-date windows; these may be suspensions, non-trading, or source gaps.",
            }
        )
    return blockers


def _summary(
    status: str,
    fetch_rows: list[dict[str, Any]],
    std_index: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    audit_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_trigger_day_5min_baostock_fetch",
        "status": status,
        "fetch_started": bool(fetch_rows),
        "baostock_network_fetch_started": bool(fetch_rows),
        "full_holding_period_fetch": False,
        "minute_data_used_for_trigger": False,
        "accepted": False,
        "v57f_core_modified": False,
        "erc_modified": False,
        "v5d_modified": False,
        "fetch_task_count": len(fetch_rows),
        "fetch_pass_count": sum(1 for row in fetch_rows if row.get("status") == "pass"),
        "fetch_empty_count": sum(1 for row in fetch_rows if row.get("status") == "empty"),
        "fetch_failure_count": sum(1 for row in fetch_rows if row.get("status") not in {"pass", "empty"}),
        "standardized_file_count": len(std_index),
        "standardized_row_count": sum(int(row.get("row_count", 0)) for row in std_index),
        "post_fetch_pm_decision": audit_summary.get("pm_decision", ""),
        "post_fetch_coverage_rate_pct": audit_summary.get("coverage_rate_pct", 0.0),
        "post_fetch_missing_window_rows": audit_summary.get("missing_window_rows", 0),
        "post_fetch_fetch_queue_count": audit_summary.get("fetch_queue_count", 0),
        "blocker_count": len(blockers),
        "blockers": blockers,
    }


def _blocker(blocker_id: str, description: str) -> dict[str, Any]:
    return {
        "blocker_id": blocker_id,
        "severity": "fatal",
        "status": "blocking",
        "description": description,
    }


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
    result = run_v5e_trigger_day_5min_baostock_fetch()
    print(json.dumps(result, ensure_ascii=False, indent=2))

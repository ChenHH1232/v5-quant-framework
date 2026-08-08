from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v5.v5d_baostock_5min_data_gate import jq_to_bs, normalize_baostock_frame


WORKSPACE = Path(__file__).resolve().parents[2]
OUT_DIR = WORKSPACE / "v5d_l4_rebalance_neighborhood_order_completion" / "current"
RAW_DIR = WORKSPACE / "v5d_baostock_5min_data_gate" / "data_raw"
STD_DIR = WORKSPACE / "v5d_baostock_5min_data_gate" / "data_standardized"
DAILY_RETURNS = WORKSPACE / "local_daily_backtests_v57f_etf" / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f" / "daily_returns.csv"
TRADE_FILES = [
    WORKSPACE / "v5d_order_scheduling_engineering_test" / "current" / "runs" / "v57f_frozen" / "l2_size_aware" / "trades.csv",
    WORKSPACE / "v5d_order_scheduling_engineering_test" / "current" / "runs" / "erc_fixed_covariance_candidate" / "l2_size_aware" / "trades.csv",
]
REQUIRED_TIMES = ["09:35:00", "09:40:00", "10:00:00", "14:55:00"]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(WORKSPACE))
    except ValueError:
        return str(path)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def next_trading_day(trading_days: list[str], day: str, offset: int) -> str:
    idx = trading_days.index(day) + offset
    return trading_days[idx] if 0 <= idx < len(trading_days) else ""


def build_plan() -> pd.DataFrame:
    daily = pd.read_csv(DAILY_RETURNS)
    trading_days = [str(x) for x in daily["trade_date"].dropna().unique()]
    trade_frames = []
    for path in TRADE_FILES:
        df = pd.read_csv(path, usecols=["trade_date", "code"])
        trade_frames.append(df)
    trades = pd.concat(trade_frames, ignore_index=True).drop_duplicates()
    rows: list[dict[str, Any]] = []
    for trade_date, group in trades.groupby("trade_date"):
        d0 = str(trade_date)
        if d0 not in trading_days:
            continue
        d1 = next_trading_day(trading_days, d0, 1)
        d2 = next_trading_day(trading_days, d0, 2)
        if not d1 or not d2:
            continue
        for code in sorted(set(group["code"].astype(str))):
            rows.append(
                {
                    "rebalance_date": d0,
                    "code": code,
                    "bs_code": jq_to_bs(code),
                    "fetch_start_date": d1,
                    "fetch_end_date": d2,
                    "required_dates": f"{d1};{d2}",
                }
            )
    return pd.DataFrame(rows)


def existing_dates_with_required_times(rebalance_date: str, code: str) -> set[str]:
    path = STD_DIR / rebalance_date / f"{code.replace('.', '_')}_5min_standardized.csv"
    if not path.exists():
        return set()
    try:
        df = pd.read_csv(path, usecols=["trade_date", "time"])
    except Exception:
        return set()
    ok_dates: set[str] = set()
    for trade_date, day in df.groupby("trade_date"):
        times = set(str(t) for t in day["time"].dropna().unique())
        if all(t in times for t in REQUIRED_TIMES):
            ok_dates.add(str(trade_date))
    return ok_dates


def merge_standardized(path: Path, new_df: pd.DataFrame) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = []
    if path.exists():
        frames.append(pd.read_csv(path))
    frames.append(new_df)
    merged = pd.concat(frames, ignore_index=True)
    merged = merged.drop_duplicates(subset=["code", "trade_date", "datetime", "time"], keep="last")
    merged = merged.sort_values(["trade_date", "datetime", "time"])
    merged.to_csv(path, index=False, encoding="utf-8-sig")
    return int(len(merged))


def run() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    blockers = [{"blocker_id": "missing_required_input", "severity": "fatal", "path": str(path)} for path in [DAILY_RETURNS, *TRADE_FILES] if not path.exists()]
    if blockers:
        write_csv(OUT_DIR / "v5d_l4_d1d2_supplement_blockers.csv", blockers)
        return {"status": "blocked", "blocker_count": len(blockers), "created_at_utc": now_utc()}

    plan = build_plan()
    pending_rows = []
    for _, row in plan.iterrows():
        required = set(str(row["required_dates"]).split(";"))
        existing = existing_dates_with_required_times(str(row["rebalance_date"]), str(row["code"]))
        missing_dates = sorted(required - existing)
        if missing_dates:
            item = row.to_dict()
            item["missing_dates_before_fetch"] = ";".join(missing_dates)
            pending_rows.append(item)
    pending = pd.DataFrame(pending_rows)
    write_csv(OUT_DIR / "v5d_l4_d1d2_supplement_fetch_plan.csv", plan.to_dict("records"))
    if pending.empty:
        summary = {
            "schema_version": 1,
            "project": "v5d_l4_d1d2_supplement_fetch",
            "status": "already_complete",
            "created_at_utc": now_utc(),
            "planned_pairs": int(len(plan)),
            "pending_pairs_before_fetch": 0,
            "fetch_started": False,
        }
        (OUT_DIR / "v5d_l4_d1d2_supplement_fetch_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary

    try:
        import baostock as bs
    except Exception as exc:
        blocker = [{"blocker_id": "baostock_import_failed", "severity": "fatal", "description": str(exc)}]
        write_csv(OUT_DIR / "v5d_l4_d1d2_supplement_blockers.csv", blocker)
        return {"status": "blocked", "blocker_count": 1, "created_at_utc": now_utc()}

    login = bs.login()
    if getattr(login, "error_code", "1") != "0":
        blocker = [{"blocker_id": "baostock_login_failed", "severity": "fatal", "description": getattr(login, "error_msg", "")}]
        write_csv(OUT_DIR / "v5d_l4_d1d2_supplement_blockers.csv", blocker)
        return {"status": "blocked", "blocker_count": 1, "created_at_utc": now_utc()}

    fields = "date,time,code,open,high,low,close,volume,amount,adjustflag"
    fetch_rows: list[dict[str, Any]] = []
    raw_index: list[dict[str, Any]] = []
    std_index: list[dict[str, Any]] = []
    try:
        for _, item in pending.iterrows():
            started = time.perf_counter()
            code = str(item["code"])
            bs_code = str(item["bs_code"])
            rebalance_date = str(item["rebalance_date"])
            start_date = str(item["fetch_start_date"])
            end_date = str(item["fetch_end_date"])
            raw_path = RAW_DIR / rebalance_date / f"{code.replace('.', '_')}_5min_l4_d1d2_raw.csv"
            std_path = STD_DIR / rebalance_date / f"{code.replace('.', '_')}_5min_standardized.csv"
            status = "error"
            row_count = 0
            error_type = ""
            error_message = ""
            try:
                rs = bs.query_history_k_data_plus(bs_code, fields, start_date=start_date, end_date=end_date, frequency="5", adjustflag="3")
                rows: list[list[str]] = []
                while (rs.error_code == "0") and rs.next():
                    rows.append(rs.get_row_data())
                if rs.error_code != "0":
                    status = "query_error"
                    error_type = rs.error_code
                    error_message = rs.error_msg
                else:
                    raw_path.parent.mkdir(parents=True, exist_ok=True)
                    raw_df = pd.DataFrame(rows, columns=rs.fields)
                    raw_df.to_csv(raw_path, index=False, encoding="utf-8-sig")
                    std_df = normalize_baostock_frame(raw_df, code, bs_code, start_date, end_date)
                    merged_count = merge_standardized(std_path, std_df)
                    row_count = int(len(std_df))
                    status = "pass" if row_count else "empty"
                    raw_index.append({"code": code, "bs_code": bs_code, "rebalance_date": rebalance_date, "path": rel(raw_path), "row_count": int(len(raw_df))})
                    std_index.append({"code": code, "bs_code": bs_code, "rebalance_date": rebalance_date, "path": rel(std_path), "new_row_count": row_count, "merged_row_count": merged_count})
            except Exception as exc:
                error_type = type(exc).__name__
                error_message = str(exc)[:500]
            fetch_rows.append(
                {
                    "rebalance_date": rebalance_date,
                    "code": code,
                    "bs_code": bs_code,
                    "fetch_start_date": start_date,
                    "fetch_end_date": end_date,
                    "missing_dates_before_fetch": item.get("missing_dates_before_fetch", ""),
                    "status": status,
                    "row_count": row_count,
                    "raw_path": rel(raw_path) if raw_path.exists() else "",
                    "standardized_path": rel(std_path) if std_path.exists() else "",
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

    write_csv(OUT_DIR / "v5d_l4_d1d2_supplement_fetch_log.csv", fetch_rows)
    write_csv(OUT_DIR / "v5d_l4_d1d2_supplement_raw_index.csv", raw_index)
    write_csv(OUT_DIR / "v5d_l4_d1d2_supplement_standardized_index.csv", std_index)
    blockers = []
    fail_count = sum(1 for r in fetch_rows if r["status"] not in {"pass", "empty"})
    if fail_count:
        blockers.append({"blocker_id": "supplement_fetch_failures", "severity": "review", "description": f"{fail_count} supplemental fetches failed."})
    write_csv(OUT_DIR / "v5d_l4_d1d2_supplement_blockers.csv", blockers, ["blocker_id", "severity", "description"])
    summary = {
        "schema_version": 1,
        "project": "v5d_l4_d1d2_supplement_fetch",
        "status": "completed_with_review_notes" if blockers else "completed",
        "created_at_utc": now_utc(),
        "planned_pairs": int(len(plan)),
        "pending_pairs_before_fetch": int(len(pending)),
        "fetch_pass_count": sum(1 for r in fetch_rows if r["status"] == "pass"),
        "fetch_empty_count": sum(1 for r in fetch_rows if r["status"] == "empty"),
        "fetch_failure_count": fail_count,
        "new_standardized_rows": int(sum(int(r["row_count"]) for r in fetch_rows)),
        "blocker_count": len(blockers),
    }
    (OUT_DIR / "v5d_l4_d1d2_supplement_fetch_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))

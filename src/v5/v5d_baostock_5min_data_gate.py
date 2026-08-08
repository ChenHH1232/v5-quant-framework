from __future__ import annotations

import csv
import json
import multiprocessing as mp
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


WORKSPACE = Path(__file__).resolve().parents[2]
OUT_DIR = WORKSPACE / "v5d_baostock_5min_data_gate" / "current"
RAW_DIR = WORKSPACE / "v5d_baostock_5min_data_gate" / "data_raw"
STD_DIR = WORKSPACE / "v5d_baostock_5min_data_gate" / "data_standardized"

REQUIRED_FILES = {
    "config": WORKSPACE / "config" / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f.json",
    "summary": WORKSPACE / "local_daily_backtests_v57f_etf" / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f" / "summary.json",
    "signals": WORKSPACE / "local_daily_backtests_v57f_etf" / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f" / "rebalance_signals.csv",
    "trades": WORKSPACE / "local_daily_backtests_v57f_etf" / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f" / "trades.csv",
    "holdings": WORKSPACE / "local_daily_backtests_v57f_etf" / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f" / "holdings.csv",
    "sleeve_daily_returns": WORKSPACE / "v5c_sleeve_level_risk_attribution" / "current" / "v57f_core_sleeve_daily_returns.csv",
    "erc_validation": WORKSPACE / "v5c_erc_formal_validation" / "current" / "v5c_erc_formal_validation_summary.json",
    "erc_forward": WORKSPACE / "v5c_erc_forward_paper_tracking" / "current" / "v5c_erc_forward_paper_tracking_summary.json",
}

REQUIRED_PROXY_TIMES = ["09:35:00", "09:40:00", "10:00:00", "14:55:00"]
LOCAL_ENGINEERING_WINDOW_START = "2021-05-01"
LOCAL_ENGINEERING_WINDOW_END = "2026-05-31"


@dataclass
class FetchResult:
    code: str
    bs_code: str
    rebalance_date: str
    fetch_start_date: str
    fetch_end_date: str
    status: str
    row_count: int
    raw_path: str
    standardized_path: str
    elapsed_sec: float
    error_type: str = ""
    error_message: str = ""


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


def jq_to_bs(code: str) -> str:
    plain = code.split(".")[0]
    if code.endswith(".XSHG"):
        return f"sh.{plain}"
    if code.endswith(".XSHE"):
        return f"sz.{plain}"
    raise ValueError(f"Unsupported JQ code: {code}")


def parse_bs_time(value: Any) -> tuple[str, str]:
    text = str(value)
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 14:
        dt = datetime.strptime(digits[:14], "%Y%m%d%H%M%S")
        return dt.date().isoformat(), dt.strftime("%Y-%m-%d %H:%M:%S")
    return "", ""


def normalize_baostock_frame(df: pd.DataFrame, code: str, bs_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "code",
                "bs_code",
                "trade_date",
                "datetime",
                "time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "amount",
                "frequency",
                "adjustflag",
                "source",
                "fetch_start_date",
                "fetch_end_date",
                "created_at_utc",
            ]
        )
    rows = []
    created_at = now_utc()
    for _, row in df.iterrows():
        trade_date, dt_text = parse_bs_time(row.get("time", ""))
        if not trade_date:
            trade_date = str(row.get("date", ""))
        time_text = dt_text.split(" ")[1] if " " in dt_text else ""
        rows.append(
            {
                "code": code,
                "bs_code": bs_code,
                "trade_date": trade_date,
                "datetime": dt_text,
                "time": time_text,
                "open": pd.to_numeric(row.get("open"), errors="coerce"),
                "high": pd.to_numeric(row.get("high"), errors="coerce"),
                "low": pd.to_numeric(row.get("low"), errors="coerce"),
                "close": pd.to_numeric(row.get("close"), errors="coerce"),
                "volume": pd.to_numeric(row.get("volume"), errors="coerce"),
                "amount": pd.to_numeric(row.get("amount"), errors="coerce"),
                "frequency": "5min",
                "adjustflag": "3_unadjusted",
                "source": "baostock",
                "fetch_start_date": start_date,
                "fetch_end_date": end_date,
                "created_at_utc": created_at,
            }
        )
    return pd.DataFrame(rows)


def validate_required_files() -> list[dict[str, str]]:
    blockers = []
    for name, path in REQUIRED_FILES.items():
        if not path.exists():
            blockers.append(
                {
                    "blocker_id": f"missing_required_{name}",
                    "severity": "fatal",
                    "description": f"Required file not found: {rel(path)}",
                    "required_action": "Restore the required governance/backtest file before BaoStock data gate can run.",
                }
            )
    return blockers


def build_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict[str, str]], list[dict[str, str]]]:
    signals = pd.read_csv(REQUIRED_FILES["signals"])
    trades = pd.read_csv(REQUIRED_FILES["trades"])
    holdings = pd.read_csv(REQUIRED_FILES["holdings"])
    daily = pd.read_csv(REQUIRED_FILES["sleeve_daily_returns"])
    all_codes = sorted(set(signals["code"].dropna()) | set(trades["code"].dropna()) | set(holdings["code"].dropna()))
    sectors = signals.groupby("code")["sector_id"].agg(lambda x: ";".join(sorted(set(map(str, x.dropna()))))).to_dict()
    universe_rows = []
    for code in all_codes:
        universe_rows.append(
            {
                "code": code,
                "bs_code": jq_to_bs(code),
                "sector_ids": sectors.get(code, ""),
                "in_rebalance_signals": bool(code in set(signals["code"])),
                "in_trades": bool(code in set(trades["code"])),
                "in_holdings": bool(code in set(holdings["code"])),
            }
        )
    universe = pd.DataFrame(universe_rows)

    trading_dates = list(pd.to_datetime(daily["trade_date"]).dt.date.astype(str))
    trading_set = set(trading_dates)
    rebalance_dates = list(dict.fromkeys(signals["trade_date"].astype(str).tolist()))
    window_rows = []
    for d in rebalance_dates:
        if d in trading_set:
            idx = trading_dates.index(d)
            prev_d = trading_dates[idx - 1] if idx > 0 else ""
            next_d = trading_dates[idx + 1] if idx < len(trading_dates) - 1 else ""
            method = "daily_returns_trading_calendar"
        else:
            prev_d = ""
            next_d = ""
            method = "calendar_date_only_rebalance_not_in_daily_returns"
        start = prev_d or d
        end = next_d or d
        window_rows.append(
            {
                "rebalance_date": d,
                "prev_trading_date": prev_d,
                "rebalance_trading_date": d if d in trading_set else "",
                "next_trading_date": next_d,
                "fetch_start_date": start,
                "fetch_end_date": end,
                "calendar_method": method,
            }
        )
    windows = pd.DataFrame(window_rows)

    signal_cols = ["trade_date", "code", "sector_id", "selected_rank", "selected_count", "target_weight"]
    if "rebalance_event_type" in signals.columns:
        signal_cols.append("rebalance_event_type")
    plan = signals[signal_cols].merge(windows, left_on="trade_date", right_on="rebalance_date", how="left")
    plan["bs_code"] = plan["code"].map(jq_to_bs)
    plan = plan[
        [
            "rebalance_date",
            "prev_trading_date",
            "rebalance_trading_date",
            "next_trading_date",
            "fetch_start_date",
            "fetch_end_date",
            "code",
            "bs_code",
            "sector_id",
            "selected_rank",
            "selected_count",
            "target_weight",
            "calendar_method",
        ]
    ].drop_duplicates()

    code_mapping = universe[["code", "bs_code"]].to_dict("records")
    return universe, windows, plan, code_mapping, []


def baostock_fetch_worker(plan_records: list[dict[str, Any]], queue: mp.Queue) -> None:
    results: list[dict[str, Any]] = []
    raw_index: list[dict[str, Any]] = []
    std_index: list[dict[str, Any]] = []
    try:
        import baostock as bs
    except Exception as exc:
        queue.put({"fatal": True, "error_type": type(exc).__name__, "error_message": str(exc), "results": []})
        return

    try:
        login = bs.login()
    except Exception as exc:
        queue.put({"fatal": True, "error_type": type(exc).__name__, "error_message": str(exc), "results": []})
        return
    if getattr(login, "error_code", "1") != "0":
        queue.put({"fatal": True, "error_type": getattr(login, "error_code", "login_error"), "error_message": getattr(login, "error_msg", ""), "results": []})
        return

    fields = "date,time,code,open,high,low,close,volume,amount,adjustflag"
    for item in plan_records:
        started = time.perf_counter()
        code = str(item["code"])
        bs_code = str(item["bs_code"])
        rebalance_date = str(item["rebalance_date"])
        start_date = str(item["fetch_start_date"])
        end_date = str(item["fetch_end_date"])
        raw_path = RAW_DIR / rebalance_date / f"{code.replace('.', '_')}_5min_raw.csv"
        std_path = STD_DIR / rebalance_date / f"{code.replace('.', '_')}_5min_standardized.csv"
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
            while (rs.error_code == "0") and rs.next():
                rows.append(rs.get_row_data())
            if rs.error_code != "0":
                result = FetchResult(code, bs_code, rebalance_date, start_date, end_date, "query_error", 0, "", "", round(time.perf_counter() - started, 3), rs.error_code, rs.error_msg)
            else:
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                std_path.parent.mkdir(parents=True, exist_ok=True)
                raw_df = pd.DataFrame(rows, columns=rs.fields)
                raw_df.to_csv(raw_path, index=False, encoding="utf-8-sig")
                std_df = normalize_baostock_frame(raw_df, code, bs_code, start_date, end_date)
                std_df.to_csv(std_path, index=False, encoding="utf-8-sig")
                result = FetchResult(code, bs_code, rebalance_date, start_date, end_date, "pass" if len(std_df) else "empty", int(len(std_df)), rel(raw_path), rel(std_path), round(time.perf_counter() - started, 3))
                raw_index.append({"code": code, "bs_code": bs_code, "rebalance_date": rebalance_date, "path": rel(raw_path), "row_count": int(len(raw_df))})
                std_index.append({"code": code, "bs_code": bs_code, "rebalance_date": rebalance_date, "path": rel(std_path), "row_count": int(len(std_df))})
            results.append(result.__dict__)
        except Exception as exc:
            results.append(FetchResult(code, bs_code, rebalance_date, start_date, end_date, "error", 0, "", "", round(time.perf_counter() - started, 3), type(exc).__name__, str(exc)[:500]).__dict__)
    try:
        bs.logout()
    except Exception:
        pass
    queue.put({"fatal": False, "results": results, "raw_index": raw_index, "std_index": std_index})


def baostock_login_probe_worker(queue: mp.Queue) -> None:
    try:
        import baostock as bs

        login = bs.login()
        payload = {
            "ok": getattr(login, "error_code", "1") == "0",
            "error_type": getattr(login, "error_code", ""),
            "error_message": getattr(login, "error_msg", ""),
        }
        try:
            bs.logout()
        except Exception:
            pass
        queue.put(payload)
    except Exception as exc:
        queue.put({"ok": False, "error_type": type(exc).__name__, "error_message": str(exc)[:500]})


def run_baostock_login_probe(timeout_sec: int = 90) -> dict[str, Any]:
    queue: mp.Queue = mp.Queue()
    process = mp.Process(target=baostock_login_probe_worker, args=(queue,))
    process.start()
    process.join(timeout_sec)
    if process.is_alive():
        process.terminate()
        process.join()
        return {
            "ok": False,
            "error_type": "Timeout",
            "error_message": f"BaoStock login probe exceeded {timeout_sec} seconds.",
        }
    if not queue.empty():
        return queue.get()
    return {
        "ok": False,
        "error_type": "NoPayload",
        "error_message": f"BaoStock login probe exited without payload, exitcode={process.exitcode}.",
    }


def run_baostock_fetch_bounded(plan: pd.DataFrame, timeout_sec: int = 3600) -> dict[str, Any]:
    queue: mp.Queue = mp.Queue()
    process = mp.Process(target=baostock_fetch_worker, args=(plan.to_dict("records"), queue))
    process.start()
    process.join(timeout_sec)
    if process.is_alive():
        process.terminate()
        process.join()
        return {
            "fatal": True,
            "error_type": "Timeout",
            "error_message": f"BaoStock collection exceeded {timeout_sec} seconds.",
            "results": [],
            "raw_index": [],
            "std_index": [],
        }
    if not queue.empty():
        return queue.get()
    return {
        "fatal": True,
        "error_type": "NoPayload",
        "error_message": f"BaoStock subprocess exited without payload, exitcode={process.exitcode}.",
        "results": [],
        "raw_index": [],
        "std_index": [],
    }


def build_quality(fetch_log: pd.DataFrame, plan: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    stock_rows = []
    for code, group in fetch_log.groupby("code"):
        total = len(group)
        passes = int(group["status"].eq("pass").sum())
        rows = int(group["row_count"].sum())
        stock_rows.append(
            {
                "code": code,
                "bs_code": group["bs_code"].iloc[0],
                "planned_windows": total,
                "pass_windows": passes,
                "empty_windows": int(group["status"].eq("empty").sum()),
                "error_windows": int((~group["status"].isin(["pass", "empty"])).sum()),
                "coverage_ratio": passes / total if total else 0,
                "bar_rows": rows,
            }
        )
    coverage_by_stock = pd.DataFrame(stock_rows)

    window_rows = []
    for d, group in fetch_log.groupby("rebalance_date"):
        total = len(group)
        passes = int(group["status"].eq("pass").sum())
        window_rows.append(
            {
                "rebalance_date": d,
                "planned_codes": total,
                "pass_codes": passes,
                "empty_codes": int(group["status"].eq("empty").sum()),
                "error_codes": int((~group["status"].isin(["pass", "empty"])).sum()),
                "coverage_ratio": passes / total if total else 0,
                "bar_rows": int(group["row_count"].sum()),
            }
        )
    coverage_by_window = pd.DataFrame(window_rows)

    quality_rows = []
    proxy_counts = {time_key: {"available": 0, "total": 0} for time_key in REQUIRED_PROXY_TIMES}
    proxy_counts["last_bar"] = {"available": 0, "total": 0}
    for _, item in fetch_log[fetch_log["status"].eq("pass")].iterrows():
        path = WORKSPACE / str(item["standardized_path"])
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if df.empty:
            continue
        for trade_date, day in df.groupby("trade_date"):
            times = set(day["time"].astype(str))
            duplicate_count = int(day.duplicated(["datetime"]).sum())
            non_positive_price_rows = int(((day[["open", "high", "low", "close"]] <= 0).any(axis=1)).sum())
            non_trading_rows = int((~day["time"].astype(str).between("09:30:00", "15:00:00")).sum())
            row = {
                "code": item["code"],
                "bs_code": item["bs_code"],
                "rebalance_date": item["rebalance_date"],
                "trade_date": trade_date,
                "bar_count": int(len(day)),
                "has_0935": "09:35:00" in times,
                "has_0940": "09:40:00" in times,
                "has_1000": "10:00:00" in times,
                "has_1455": "14:55:00" in times,
                "last_bar_time": str(day["time"].iloc[-1]),
                "has_last_bar": bool(len(day) > 0),
                "duplicate_bar_count": duplicate_count,
                "non_positive_price_rows": non_positive_price_rows,
                "non_trading_time_rows": non_trading_rows,
                "quality_status": "pass" if duplicate_count == 0 and non_positive_price_rows == 0 and len(day) > 0 else "needs_review",
            }
            quality_rows.append(row)
            for time_key, col in [("09:35:00", "has_0935"), ("09:40:00", "has_0940"), ("10:00:00", "has_1000"), ("14:55:00", "has_1455")]:
                proxy_counts[time_key]["total"] += 1
                if row[col]:
                    proxy_counts[time_key]["available"] += 1
            proxy_counts["last_bar"]["total"] += 1
            proxy_counts["last_bar"]["available"] += 1
    quality = pd.DataFrame(quality_rows)
    readiness_rows = []
    for proxy, counts in proxy_counts.items():
        total = counts["total"]
        available = counts["available"]
        coverage = available / total if total else 0
        readiness_rows.append(
            {
                "execution_proxy": proxy,
                "available_rows": available,
                "total_checked_rows": total,
                "coverage_ratio": coverage,
                "allowed_for_next_spec": bool(total > 0 and coverage >= 0.95),
                "pm_read": "usable_for_5min_execution_proxy" if total > 0 and coverage >= 0.95 else "not_ready_or_insufficient_coverage",
            }
        )
    readiness = pd.DataFrame(readiness_rows)
    return coverage_by_stock, coverage_by_window, quality, readiness, fetch_log


def write_minimal_outputs(blockers: list[dict[str, str]], universe: pd.DataFrame | None = None, windows: pd.DataFrame | None = None, plan: pd.DataFrame | None = None) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    STD_DIR.mkdir(parents=True, exist_ok=True)
    if universe is not None:
        universe.to_csv(OUT_DIR / "v5d_baostock_stock_universe.csv", index=False, encoding="utf-8-sig")
        universe[["code", "bs_code"]].to_csv(OUT_DIR / "v5d_baostock_code_mapping.csv", index=False, encoding="utf-8-sig")
    else:
        write_csv(OUT_DIR / "v5d_baostock_stock_universe.csv", [])
        write_csv(OUT_DIR / "v5d_baostock_code_mapping.csv", [])
    if windows is not None:
        windows.to_csv(OUT_DIR / "v5d_baostock_rebalance_window_plan.csv", index=False, encoding="utf-8-sig")
    else:
        write_csv(OUT_DIR / "v5d_baostock_rebalance_window_plan.csv", [])
    empty_files = [
        "v5d_baostock_fetch_log.csv",
        "v5d_baostock_5min_raw_index.csv",
        "v5d_baostock_5min_standardized_index.csv",
        "v5d_baostock_coverage_by_stock.csv",
        "v5d_baostock_coverage_by_rebalance_window.csv",
        "v5d_baostock_bar_quality_checks.csv",
        "v5d_minute_execution_proxy_readiness.csv",
        "v5d_next_agent_queue.csv",
    ]
    for name in empty_files:
        write_csv(OUT_DIR / name, [])
    write_csv(OUT_DIR / "v5d_baostock_blockers.csv", blockers)
    (OUT_DIR / "v5d_agent_execution_rules.md").write_text(agent_rules_text(), encoding="utf-8")
    summary = {
        "schema_version": 1,
        "project": "v5d_baostock_5min_data_gate",
        "status": "blocked",
        "created_at_utc": now_utc(),
        "local_engineering_window": {
            "start_date": LOCAL_ENGINEERING_WINDOW_START,
            "end_date": LOCAL_ENGINEERING_WINDOW_END,
        },
        "first_v57f_rebalance_signal": str(windows["rebalance_date"].min()) if windows is not None and not windows.empty else None,
        "v57f_core_modified": False,
        "erc_modified": False,
        "joinquant_started": False,
        "minute_backtest_started": False,
        "stock_universe_count": int(len(universe)) if universe is not None else 0,
        "rebalance_window_count": int(len(windows)) if windows is not None else 0,
        "planned_fetch_count": int(len(plan)) if plan is not None else 0,
        "blocker_count": len(blockers),
        "primary_blocker": blockers[0]["blocker_id"] if blockers else None,
    }
    (OUT_DIR / "v5d_baostock_5min_data_gate_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "v5d_baostock_5min_data_gate_report.md").write_text(report_text(summary, blockers), encoding="utf-8")


def agent_rules_text() -> str:
    return """# V5d BaoStock 5min Agent Execution Rules

- Do not modify V57f or ERC.
- Do not start JoinQuant.
- Do not run minute strategy backtests in this data-gate task.
- Use BaoStock unadjusted prices only for execution proxies.
- Do not fill missing minute bars.
- Stop at blocker if BaoStock login/API is unavailable or coverage is insufficient.
"""


def report_text(summary: dict[str, Any], blockers: list[dict[str, str]], coverage: dict[str, Any] | None = None) -> str:
    lines = [
        "# V5d BaoStock 5min Data Gate",
        "",
        "## Status",
        f"- Status: `{summary.get('status')}`",
        f"- Local engineering window: {LOCAL_ENGINEERING_WINDOW_START} to {LOCAL_ENGINEERING_WINDOW_END}",
        f"- First V57f rebalance signal collected: {summary.get('first_v57f_rebalance_signal')}",
        f"- Stock universe count: {summary.get('stock_universe_count')}",
        f"- Rebalance windows: {summary.get('rebalance_window_count')}",
        f"- Planned fetches: {summary.get('planned_fetch_count')}",
        "- V57f modified: false",
        "- ERC modified: false",
        "- JoinQuant started: false",
        "- Minute backtest started: false",
        "",
    ]
    if coverage:
        lines.extend(
            [
                "## Coverage",
                f"- Fetch pass ratio: {coverage.get('fetch_pass_ratio'):.4f}",
                f"- Total standardized rows: {coverage.get('total_standardized_rows')}",
                f"- Execution proxy next spec allowed: {coverage.get('next_spec_allowed')}",
                "",
            ]
        )
    lines.append("## Blockers")
    if blockers:
        for b in blockers:
            lines.append(f"- {b['blocker_id']}: {b['description']} Required action: {b['required_action']}")
    else:
        lines.append("- None.")
    return "\n".join(lines) + "\n"


def finalize_existing_outputs() -> int:
    blockers = validate_required_files()
    if blockers:
        write_minimal_outputs(blockers)
        return 0
    universe, windows, plan, code_mapping, _ = build_inputs()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    universe.to_csv(OUT_DIR / "v5d_baostock_stock_universe.csv", index=False, encoding="utf-8-sig")
    windows.to_csv(OUT_DIR / "v5d_baostock_rebalance_window_plan.csv", index=False, encoding="utf-8-sig")
    write_csv(OUT_DIR / "v5d_baostock_code_mapping.csv", code_mapping)
    plan.to_csv(OUT_DIR / "v5d_baostock_fetch_plan_internal.csv", index=False, encoding="utf-8-sig")

    fetch_rows = []
    raw_rows = []
    std_rows = []
    for _, row in plan.iterrows():
        code = str(row["code"])
        rebalance_date = str(row["rebalance_date"])
        raw_path = RAW_DIR / rebalance_date / f"{code.replace('.', '_')}_5min_raw.csv"
        std_path = STD_DIR / rebalance_date / f"{code.replace('.', '_')}_5min_standardized.csv"
        raw_count = 0
        std_count = 0
        if raw_path.exists():
            try:
                raw_count = len(pd.read_csv(raw_path))
            except Exception:
                raw_count = 0
        if std_path.exists():
            try:
                std_count = len(pd.read_csv(std_path))
            except Exception:
                std_count = 0
        status = "pass" if std_count > 0 else "empty" if raw_path.exists() or std_path.exists() else "missing_file"
        fetch_rows.append(
            {
                "code": code,
                "bs_code": str(row["bs_code"]),
                "rebalance_date": rebalance_date,
                "fetch_start_date": str(row["fetch_start_date"]),
                "fetch_end_date": str(row["fetch_end_date"]),
                "status": status,
                "row_count": int(std_count),
                "raw_path": rel(raw_path) if raw_path.exists() else "",
                "standardized_path": rel(std_path) if std_path.exists() else "",
                "elapsed_sec": "",
                "error_type": "" if status == "pass" else status,
                "error_message": "" if status == "pass" else "Reconstructed from existing files after collection process timeout.",
            }
        )
        if raw_path.exists():
            raw_rows.append({"code": code, "bs_code": str(row["bs_code"]), "rebalance_date": rebalance_date, "path": rel(raw_path), "row_count": int(raw_count)})
        if std_path.exists():
            std_rows.append({"code": code, "bs_code": str(row["bs_code"]), "rebalance_date": rebalance_date, "path": rel(std_path), "row_count": int(std_count)})

    fetch_log = pd.DataFrame(fetch_rows)
    raw_index = pd.DataFrame(raw_rows)
    std_index = pd.DataFrame(std_rows)
    fetch_log.to_csv(OUT_DIR / "v5d_baostock_fetch_log.csv", index=False, encoding="utf-8-sig")
    raw_index.to_csv(OUT_DIR / "v5d_baostock_5min_raw_index.csv", index=False, encoding="utf-8-sig")
    std_index.to_csv(OUT_DIR / "v5d_baostock_5min_standardized_index.csv", index=False, encoding="utf-8-sig")

    coverage_by_stock, coverage_by_window, quality, readiness, _ = build_quality(fetch_log, plan)
    coverage_by_stock.to_csv(OUT_DIR / "v5d_baostock_coverage_by_stock.csv", index=False, encoding="utf-8-sig")
    coverage_by_window.to_csv(OUT_DIR / "v5d_baostock_coverage_by_rebalance_window.csv", index=False, encoding="utf-8-sig")
    quality.to_csv(OUT_DIR / "v5d_baostock_bar_quality_checks.csv", index=False, encoding="utf-8-sig")
    readiness.to_csv(OUT_DIR / "v5d_minute_execution_proxy_readiness.csv", index=False, encoding="utf-8-sig")

    total_fetches = int(len(fetch_log))
    pass_fetches = int(fetch_log["status"].eq("pass").sum()) if total_fetches else 0
    pass_ratio = pass_fetches / total_fetches if total_fetches else 0
    next_spec_allowed = bool(pass_ratio >= 0.95 and (not readiness.empty) and readiness["allowed_for_next_spec"].all())
    blockers: list[dict[str, str]] = []
    if pass_ratio < 0.8:
        blockers.append(
            {
                "blocker_id": "critical_rebalance_window_coverage_insufficient",
                "severity": "fatal",
                "description": f"BaoStock 5min fetch pass ratio is {pass_ratio:.4f}, below 0.80 stop threshold.",
                "required_action": "Repair BaoStock coverage before minute execution spec.",
            }
        )
    elif not next_spec_allowed:
        blockers.append(
            {
                "blocker_id": "execution_proxy_coverage_needs_review",
                "severity": "review",
                "description": "Fetch coverage is usable but one or more execution proxy timestamps has insufficient coverage.",
                "required_action": "Review proxy readiness table before engineering minute execution robustness spec.",
            }
        )
    write_csv(OUT_DIR / "v5d_baostock_blockers.csv", blockers)
    next_queue = [
        {
            "priority": "1",
            "agent": "V5d Engineering Agent",
            "task": "minute_execution_robustness_spec",
            "allowed_to_start": str(next_spec_allowed).lower(),
            "condition": "Use fixed 5min execution proxies only; no strategy parameter optimization.",
        }
    ]
    write_csv(OUT_DIR / "v5d_next_agent_queue.csv", next_queue)
    (OUT_DIR / "v5d_agent_execution_rules.md").write_text(agent_rules_text(), encoding="utf-8")
    coverage_info = {
        "fetch_pass_ratio": pass_ratio,
        "total_standardized_rows": int(std_index["row_count"].sum()) if not std_index.empty else 0,
        "next_spec_allowed": next_spec_allowed,
    }
    summary = {
        "schema_version": 1,
        "project": "v5d_baostock_5min_data_gate",
        "status": "pass" if not blockers else "pass_with_review_blocker" if blockers[0]["severity"] == "review" else "blocked",
        "created_at_utc": now_utc(),
        "local_engineering_window": {
            "start_date": LOCAL_ENGINEERING_WINDOW_START,
            "end_date": LOCAL_ENGINEERING_WINDOW_END,
        },
        "first_v57f_rebalance_signal": str(windows["rebalance_date"].min()) if not windows.empty else None,
        "last_v57f_rebalance_signal": str(windows["rebalance_date"].max()) if not windows.empty else None,
        "v57f_core_modified": False,
        "erc_modified": False,
        "joinquant_started": False,
        "minute_backtest_started": False,
        "stock_universe_count": int(len(universe)),
        "rebalance_window_count": int(len(windows)),
        "planned_fetch_count": int(len(plan)),
        "fetch_pass_count": pass_fetches,
        "fetch_pass_ratio": pass_ratio,
        "standardized_row_count": coverage_info["total_standardized_rows"],
        "next_spec_allowed": next_spec_allowed,
        "blocker_count": len(blockers),
        "primary_blocker": blockers[0]["blocker_id"] if blockers else None,
        "finalization_note": "Indexes and quality checks reconstructed from existing BaoStock files after the first collection process timed out at the shell layer.",
    }
    (OUT_DIR / "v5d_baostock_5min_data_gate_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "v5d_baostock_5min_data_gate_report.md").write_text(report_text(summary, blockers, coverage_info), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    STD_DIR.mkdir(parents=True, exist_ok=True)

    blockers = validate_required_files()
    if blockers:
        write_minimal_outputs(blockers)
        return 0

    universe, windows, plan, code_mapping, input_blockers = build_inputs()
    universe.to_csv(OUT_DIR / "v5d_baostock_stock_universe.csv", index=False, encoding="utf-8-sig")
    windows.to_csv(OUT_DIR / "v5d_baostock_rebalance_window_plan.csv", index=False, encoding="utf-8-sig")
    write_csv(OUT_DIR / "v5d_baostock_code_mapping.csv", code_mapping)
    plan.to_csv(OUT_DIR / "v5d_baostock_fetch_plan_internal.csv", index=False, encoding="utf-8-sig")

    try:
        import baostock  # noqa: F401
    except Exception as exc:
        blockers = [
            {
                "blocker_id": "baostock_not_installed",
                "severity": "fatal",
                "description": f"BaoStock package is unavailable: {type(exc).__name__}: {exc}",
                "required_action": "Install baostock package with user permission before rerunning.",
            }
        ]
        write_minimal_outputs(blockers, universe, windows, plan)
        return 0

    login_probe = run_baostock_login_probe()
    if not login_probe.get("ok"):
        blockers = [
            {
                "blocker_id": "baostock_login_unavailable",
                "severity": "fatal",
                "description": f"{login_probe.get('error_type')}: {login_probe.get('error_message')}",
                "required_action": "Retry BaoStock from a working network/API environment before 5min collection.",
            }
        ]
        write_minimal_outputs(blockers, universe, windows, plan)
        return 0

    fetch_payload = run_baostock_fetch_bounded(plan)
    if fetch_payload.get("fatal"):
        blockers = [
            {
                "blocker_id": "baostock_login_or_api_unavailable",
                "severity": "fatal",
                "description": f"{fetch_payload.get('error_type')}: {fetch_payload.get('error_message')}",
                "required_action": "Retry BaoStock from a working network/API environment, or provide another approved minute data export.",
            }
        ]
        write_minimal_outputs(blockers, universe, windows, plan)
        return 0

    fetch_log = pd.DataFrame(fetch_payload.get("results", []))
    raw_index = pd.DataFrame(fetch_payload.get("raw_index", []))
    std_index = pd.DataFrame(fetch_payload.get("std_index", []))
    fetch_log.to_csv(OUT_DIR / "v5d_baostock_fetch_log.csv", index=False, encoding="utf-8-sig")
    raw_index.to_csv(OUT_DIR / "v5d_baostock_5min_raw_index.csv", index=False, encoding="utf-8-sig")
    std_index.to_csv(OUT_DIR / "v5d_baostock_5min_standardized_index.csv", index=False, encoding="utf-8-sig")

    coverage_by_stock, coverage_by_window, quality, readiness, _ = build_quality(fetch_log, plan)
    coverage_by_stock.to_csv(OUT_DIR / "v5d_baostock_coverage_by_stock.csv", index=False, encoding="utf-8-sig")
    coverage_by_window.to_csv(OUT_DIR / "v5d_baostock_coverage_by_rebalance_window.csv", index=False, encoding="utf-8-sig")
    quality.to_csv(OUT_DIR / "v5d_baostock_bar_quality_checks.csv", index=False, encoding="utf-8-sig")
    readiness.to_csv(OUT_DIR / "v5d_minute_execution_proxy_readiness.csv", index=False, encoding="utf-8-sig")

    total_fetches = int(len(fetch_log))
    pass_fetches = int(fetch_log["status"].eq("pass").sum()) if total_fetches else 0
    pass_ratio = pass_fetches / total_fetches if total_fetches else 0
    next_spec_allowed = bool(pass_ratio >= 0.95 and (not readiness.empty) and readiness["allowed_for_next_spec"].all())
    blockers: list[dict[str, str]] = []
    if pass_ratio < 0.8:
        blockers.append(
            {
                "blocker_id": "critical_rebalance_window_coverage_insufficient",
                "severity": "fatal",
                "description": f"BaoStock 5min fetch pass ratio is {pass_ratio:.4f}, below 0.80 stop threshold.",
                "required_action": "Repair BaoStock connectivity/data coverage before minute execution spec.",
            }
        )
    elif not next_spec_allowed:
        blockers.append(
            {
                "blocker_id": "execution_proxy_coverage_needs_review",
                "severity": "review",
                "description": "Fetch coverage is usable but one or more execution proxy timestamps has insufficient coverage.",
                "required_action": "Review proxy readiness table before engineering minute execution robustness spec.",
            }
        )
    write_csv(OUT_DIR / "v5d_baostock_blockers.csv", blockers)

    next_queue = [
        {
            "priority": "1",
            "agent": "V5d Engineering Agent",
            "task": "minute_execution_robustness_spec",
            "allowed_to_start": str(next_spec_allowed).lower(),
            "condition": "Use only fixed 5min execution proxies; no strategy parameter optimization.",
        }
    ]
    write_csv(OUT_DIR / "v5d_next_agent_queue.csv", next_queue)
    (OUT_DIR / "v5d_agent_execution_rules.md").write_text(agent_rules_text(), encoding="utf-8")

    coverage_info = {
        "fetch_pass_ratio": pass_ratio,
        "total_standardized_rows": int(std_index["row_count"].sum()) if not std_index.empty else 0,
        "next_spec_allowed": next_spec_allowed,
    }
    summary = {
        "schema_version": 1,
        "project": "v5d_baostock_5min_data_gate",
        "status": "pass" if not blockers else "pass_with_review_blocker" if blockers[0]["severity"] == "review" else "blocked",
        "created_at_utc": now_utc(),
        "v57f_core_modified": False,
        "erc_modified": False,
        "joinquant_started": False,
        "minute_backtest_started": False,
        "stock_universe_count": int(len(universe)),
        "rebalance_window_count": int(len(windows)),
        "planned_fetch_count": int(len(plan)),
        "fetch_pass_count": pass_fetches,
        "fetch_pass_ratio": pass_ratio,
        "standardized_row_count": coverage_info["total_standardized_rows"],
        "next_spec_allowed": next_spec_allowed,
        "blocker_count": len(blockers),
        "primary_blocker": blockers[0]["blocker_id"] if blockers else None,
        "outputs": {
            "summary": "v5d_baostock_5min_data_gate/current/v5d_baostock_5min_data_gate_summary.json",
            "report": "v5d_baostock_5min_data_gate/current/v5d_baostock_5min_data_gate_report.md",
            "stock_universe": "v5d_baostock_5min_data_gate/current/v5d_baostock_stock_universe.csv",
            "rebalance_window_plan": "v5d_baostock_5min_data_gate/current/v5d_baostock_rebalance_window_plan.csv",
            "code_mapping": "v5d_baostock_5min_data_gate/current/v5d_baostock_code_mapping.csv",
            "fetch_log": "v5d_baostock_5min_data_gate/current/v5d_baostock_fetch_log.csv",
            "raw_index": "v5d_baostock_5min_data_gate/current/v5d_baostock_5min_raw_index.csv",
            "standardized_index": "v5d_baostock_5min_data_gate/current/v5d_baostock_5min_standardized_index.csv",
            "coverage_by_stock": "v5d_baostock_5min_data_gate/current/v5d_baostock_coverage_by_stock.csv",
            "coverage_by_window": "v5d_baostock_5min_data_gate/current/v5d_baostock_coverage_by_rebalance_window.csv",
            "quality_checks": "v5d_baostock_5min_data_gate/current/v5d_baostock_bar_quality_checks.csv",
            "proxy_readiness": "v5d_baostock_5min_data_gate/current/v5d_minute_execution_proxy_readiness.csv",
            "blockers": "v5d_baostock_5min_data_gate/current/v5d_baostock_blockers.csv",
            "next_queue": "v5d_baostock_5min_data_gate/current/v5d_next_agent_queue.csv",
            "rules": "v5d_baostock_5min_data_gate/current/v5d_agent_execution_rules.md",
        },
    }
    (OUT_DIR / "v5d_baostock_5min_data_gate_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "v5d_baostock_5min_data_gate_report.md").write_text(report_text(summary, blockers, coverage_info), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    if "--finalize-existing" in sys.argv:
        raise SystemExit(finalize_existing_outputs())
    raise SystemExit(main())

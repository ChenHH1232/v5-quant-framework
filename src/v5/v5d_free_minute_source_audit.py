from __future__ import annotations

import csv
import json
import math
import multiprocessing as mp
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


WORKSPACE = Path(__file__).resolve().parents[2]
INPUT_TARGETS = WORKSPACE / "v5d_minute_execution_audit" / "current" / "v5d_rebalance_target_universe.csv"
OUTPUT_DIR = WORKSPACE / "v5d_free_minute_source_audit" / "current"


@dataclass(frozen=True)
class SourceResult:
    source: str
    trade_date: str
    code: str
    sector_id: str
    selected_rank: int | None
    requested_frequency: str
    status: str
    row_count: int
    first_time: str
    last_time: str
    open_price: float | None
    close_price: float | None
    total_volume: float | None
    total_amount: float | None
    elapsed_sec: float
    error_type: str
    error_message: str


def jq_code_to_plain(code: str) -> str:
    return code.split(".")[0]


def jq_code_to_baostock(code: str) -> str:
    plain = jq_code_to_plain(code)
    if code.endswith(".XSHG"):
        return f"sh.{plain}"
    if code.endswith(".XSHE"):
        return f"sz.{plain}"
    raise ValueError(f"Unsupported code suffix: {code}")


def pick_probe_samples(targets: pd.DataFrame) -> pd.DataFrame:
    base = targets[targets["signal_source_id"].eq("v57f_frozen_baseline_200w_reference")].copy()
    base = base.sort_values(["trade_date", "sector_id", "selected_rank", "code"])
    dates = list(dict.fromkeys(base["trade_date"].astype(str).tolist()))
    desired_dates = []
    for idx in [0, len(dates) // 2, len(dates) - 1]:
        d = dates[idx]
        if d not in desired_dates:
            desired_dates.append(d)
    frames = []
    for d in desired_dates:
        day = base[base["trade_date"].eq(d)]
        frames.append(day.groupby("sector_id", as_index=False).head(1))
    samples = pd.concat(frames, ignore_index=True)
    return samples[["trade_date", "code", "sector_id", "selected_rank"]].drop_duplicates().head(12)


def summarize_ak_frame(df: pd.DataFrame) -> dict[str, Any]:
    if df is None or df.empty:
        return {
            "row_count": 0,
            "first_time": "",
            "last_time": "",
            "open_price": None,
            "close_price": None,
            "total_volume": None,
            "total_amount": None,
        }
    columns = {str(c): c for c in df.columns}
    time_col = columns.get("时间") or columns.get("日期") or df.columns[0]
    open_col = columns.get("开盘") or columns.get("open")
    close_col = columns.get("收盘") or columns.get("close")
    volume_col = columns.get("成交量") or columns.get("volume")
    amount_col = columns.get("成交额") or columns.get("amount")
    return {
        "row_count": int(len(df)),
        "first_time": str(df.iloc[0][time_col]),
        "last_time": str(df.iloc[-1][time_col]),
        "open_price": safe_float(df.iloc[0][open_col]) if open_col is not None else None,
        "close_price": safe_float(df.iloc[-1][close_col]) if close_col is not None else None,
        "total_volume": safe_float(pd.to_numeric(df[volume_col], errors="coerce").sum()) if volume_col is not None else None,
        "total_amount": safe_float(pd.to_numeric(df[amount_col], errors="coerce").sum()) if amount_col is not None else None,
    }


def safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except Exception:
        return None


def ak_worker(args: dict[str, Any], queue: mp.Queue) -> None:
    start = time.perf_counter()
    try:
        import akshare as ak

        trade_date = args["trade_date"]
        df = ak.stock_zh_a_hist_min_em(
            symbol=jq_code_to_plain(args["code"]),
            period="1",
            start_date=f"{trade_date} 09:30:00",
            end_date=f"{trade_date} 15:00:00",
            adjust="",
        )
        payload = summarize_ak_frame(df)
        payload.update({"status": "pass" if payload["row_count"] > 0 else "empty"})
        queue.put(payload)
    except Exception as exc:
        queue.put(
            {
                "status": "error",
                "row_count": 0,
                "first_time": "",
                "last_time": "",
                "open_price": None,
                "close_price": None,
                "total_volume": None,
                "total_amount": None,
                "error_type": type(exc).__name__,
                "error_message": str(exc)[:500],
            }
        )
    finally:
        elapsed = time.perf_counter() - start
        try:
            queue.put({"_elapsed_sec": elapsed})
        except Exception:
            pass


def run_ak_probe(row: pd.Series, timeout_sec: int = 45) -> SourceResult:
    queue: mp.Queue = mp.Queue()
    args = row.to_dict()
    process = mp.Process(target=ak_worker, args=(args, queue))
    started = time.perf_counter()
    process.start()
    process.join(timeout_sec)
    elapsed = time.perf_counter() - started
    if process.is_alive():
        process.terminate()
        process.join()
        payload = {
            "status": "timeout",
            "row_count": 0,
            "first_time": "",
            "last_time": "",
            "open_price": None,
            "close_price": None,
            "total_volume": None,
            "total_amount": None,
            "error_type": "Timeout",
            "error_message": f"AKShare request exceeded {timeout_sec} seconds",
        }
    else:
        payload = {}
        while not queue.empty():
            item = queue.get()
            if "_elapsed_sec" in item:
                elapsed = item["_elapsed_sec"]
            else:
                payload.update(item)
        if not payload:
            payload = {
                "status": f"process_exit_{process.exitcode}",
                "row_count": 0,
                "first_time": "",
                "last_time": "",
                "open_price": None,
                "close_price": None,
                "total_volume": None,
                "total_amount": None,
                "error_type": "NoPayload",
                "error_message": "AKShare subprocess exited without payload",
            }
    return make_result("akshare", row, "1m", payload, elapsed)


def run_ak_sina_recent_probe(row: pd.Series) -> SourceResult:
    started = time.perf_counter()
    try:
        import akshare as ak

        plain = jq_code_to_plain(str(row["code"]))
        prefix = "sh" if str(row["code"]).endswith(".XSHG") else "sz"
        df = ak.stock_zh_a_minute(symbol=f"{prefix}{plain}", period="1", adjust="")
        payload = summarize_sina_frame(df)
        requested_date = str(row["trade_date"])
        if payload["row_count"] > 0 and not (
            payload["first_time"].startswith(requested_date) or payload["last_time"].startswith(requested_date)
        ):
            payload.update(
                {
                    "status": "recent_only_not_requested_v5_date",
                    "error_type": "CoverageGap",
                    "error_message": "Sina minute endpoint returned recent rows, not the requested historical V5 rebalance date",
                }
            )
        else:
            payload.update({"status": "pass" if payload["row_count"] > 0 else "empty"})
    except Exception as exc:
        payload = {
            "status": "error",
            "row_count": 0,
            "first_time": "",
            "last_time": "",
            "open_price": None,
            "close_price": None,
            "total_volume": None,
            "total_amount": None,
            "error_type": type(exc).__name__,
            "error_message": str(exc)[:500],
        }
    return make_result("akshare_sina_recent", row, "1m", payload, time.perf_counter() - started)


def summarize_sina_frame(df: pd.DataFrame) -> dict[str, Any]:
    if df is None or df.empty:
        return {
            "row_count": 0,
            "first_time": "",
            "last_time": "",
            "open_price": None,
            "close_price": None,
            "total_volume": None,
            "total_amount": None,
        }
    return {
        "row_count": int(len(df)),
        "first_time": str(df.iloc[0]["day"]),
        "last_time": str(df.iloc[-1]["day"]),
        "open_price": safe_float(df.iloc[0]["open"]),
        "close_price": safe_float(df.iloc[-1]["close"]),
        "total_volume": safe_float(pd.to_numeric(df["volume"], errors="coerce").sum()),
        "total_amount": safe_float(pd.to_numeric(df["amount"], errors="coerce").sum()),
    }


def run_baostock_probe_rows(samples: pd.DataFrame) -> list[SourceResult]:
    results: list[SourceResult] = []
    start_login = time.perf_counter()
    try:
        import baostock as bs

        login = bs.login()
        login_elapsed = time.perf_counter() - start_login
        if login.error_code != "0":
            for _, row in samples.iterrows():
                results.append(
                    make_result(
                        "baostock",
                        row,
                        "5m",
                        {
                            "status": "login_error",
                            "row_count": 0,
                            "first_time": "",
                            "last_time": "",
                            "open_price": None,
                            "close_price": None,
                            "total_volume": None,
                            "total_amount": None,
                            "error_type": login.error_code,
                            "error_message": login.error_msg,
                        },
                        login_elapsed,
                    )
                )
            return results
        for _, row in samples.iterrows():
            started = time.perf_counter()
            try:
                rs = bs.query_history_k_data_plus(
                    jq_code_to_baostock(str(row["code"])),
                    "date,time,code,open,high,low,close,volume,amount",
                    start_date=str(row["trade_date"]),
                    end_date=str(row["trade_date"]),
                    frequency="5",
                    adjustflag="3",
                )
                records = []
                while (rs.error_code == "0") and rs.next():
                    records.append(rs.get_row_data())
                elapsed = time.perf_counter() - started
                if rs.error_code != "0":
                    payload = {
                        "status": "query_error",
                        "row_count": 0,
                        "first_time": "",
                        "last_time": "",
                        "open_price": None,
                        "close_price": None,
                        "total_volume": None,
                        "total_amount": None,
                        "error_type": rs.error_code,
                        "error_message": rs.error_msg,
                    }
                elif not records:
                    payload = {
                        "status": "empty",
                        "row_count": 0,
                        "first_time": "",
                        "last_time": "",
                        "open_price": None,
                        "close_price": None,
                        "total_volume": None,
                        "total_amount": None,
                    }
                else:
                    df = pd.DataFrame(records, columns=rs.fields)
                    payload = {
                        "status": "pass",
                        "row_count": int(len(df)),
                        "first_time": str(df.iloc[0]["time"]),
                        "last_time": str(df.iloc[-1]["time"]),
                        "open_price": safe_float(df.iloc[0]["open"]),
                        "close_price": safe_float(df.iloc[-1]["close"]),
                        "total_volume": safe_float(pd.to_numeric(df["volume"], errors="coerce").sum()),
                        "total_amount": safe_float(pd.to_numeric(df["amount"], errors="coerce").sum()),
                    }
                results.append(make_result("baostock", row, "5m", payload, elapsed))
            except Exception as exc:
                results.append(
                    make_result(
                        "baostock",
                        row,
                        "5m",
                        {
                            "status": "error",
                            "row_count": 0,
                            "first_time": "",
                            "last_time": "",
                            "open_price": None,
                            "close_price": None,
                            "total_volume": None,
                            "total_amount": None,
                            "error_type": type(exc).__name__,
                            "error_message": str(exc)[:500],
                        },
                        time.perf_counter() - started,
                    )
                )
        bs.logout()
        return results
    except Exception as exc:
        elapsed = time.perf_counter() - start_login
        for _, row in samples.iterrows():
            results.append(
                make_result(
                    "baostock",
                    row,
                    "5m",
                    {
                        "status": "error",
                        "row_count": 0,
                        "first_time": "",
                        "last_time": "",
                        "open_price": None,
                        "close_price": None,
                        "total_volume": None,
                        "total_amount": None,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc)[:500],
                    },
                    elapsed,
                )
            )
        return results


def baostock_worker(records: list[dict[str, Any]], queue: mp.Queue) -> None:
    samples = pd.DataFrame(records)
    rows = [r.__dict__ for r in run_baostock_probe_rows(samples)]
    queue.put(rows)


def run_baostock_probe_rows_bounded(samples: pd.DataFrame, timeout_sec: int = 60) -> list[SourceResult]:
    queue: mp.Queue = mp.Queue()
    process = mp.Process(target=baostock_worker, args=(samples.to_dict("records"), queue))
    started = time.perf_counter()
    process.start()
    process.join(timeout_sec)
    if process.is_alive():
        process.terminate()
        process.join()
        elapsed = time.perf_counter() - started
        results: list[SourceResult] = []
        for _, row in samples.iterrows():
            results.append(
                make_result(
                    "baostock",
                    row,
                    "5m",
                    {
                        "status": "timeout",
                        "row_count": 0,
                        "first_time": "",
                        "last_time": "",
                        "open_price": None,
                        "close_price": None,
                        "total_volume": None,
                        "total_amount": None,
                        "error_type": "Timeout",
                        "error_message": f"BaoStock probe exceeded {timeout_sec} seconds, likely login/query connectivity issue",
                    },
                    elapsed,
                )
            )
        return results
    if not queue.empty():
        rows = queue.get()
        return [SourceResult(**row) for row in rows]
    elapsed = time.perf_counter() - started
    return [
        make_result(
            "baostock",
            row,
            "5m",
            {
                "status": f"process_exit_{process.exitcode}",
                "row_count": 0,
                "first_time": "",
                "last_time": "",
                "open_price": None,
                "close_price": None,
                "total_volume": None,
                "total_amount": None,
                "error_type": "NoPayload",
                "error_message": "BaoStock subprocess exited without payload",
            },
            elapsed,
        )
        for _, row in samples.iterrows()
    ]


def make_result(source: str, row: pd.Series, frequency: str, payload: dict[str, Any], elapsed: float) -> SourceResult:
    return SourceResult(
        source=source,
        trade_date=str(row["trade_date"]),
        code=str(row["code"]),
        sector_id=str(row.get("sector_id", "")),
        selected_rank=int(row["selected_rank"]) if not pd.isna(row.get("selected_rank")) else None,
        requested_frequency=frequency,
        status=str(payload.get("status", "")),
        row_count=int(payload.get("row_count") or 0),
        first_time=str(payload.get("first_time") or ""),
        last_time=str(payload.get("last_time") or ""),
        open_price=safe_float(payload.get("open_price")),
        close_price=safe_float(payload.get("close_price")),
        total_volume=safe_float(payload.get("total_volume")),
        total_amount=safe_float(payload.get("total_amount")),
        elapsed_sec=round(float(elapsed), 3),
        error_type=str(payload.get("error_type") or ""),
        error_message=str(payload.get("error_message") or ""),
    )


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_recommendations(probe: pd.DataFrame) -> tuple[str, list[dict[str, str]]]:
    actions: list[dict[str, str]] = []
    ak = probe[probe["source"].eq("akshare")]
    bs = probe[probe["source"].eq("baostock")]
    sina = probe[probe["source"].eq("akshare_sina_recent")]
    ak_pass = int(ak["status"].eq("pass").sum()) if not ak.empty else 0
    bs_pass = int(bs["status"].eq("pass").sum()) if not bs.empty else 0
    sina_recent = int(sina["status"].eq("recent_only_not_requested_v5_date").sum()) if not sina.empty else 0
    early_ak_pass = int(ak[ak["trade_date"].astype(str).str.startswith("2021")]["status"].eq("pass").sum()) if not ak.empty else 0
    if ak_pass > 0 and early_ak_pass > 0:
        decision = "free_source_feasible_for_sample_continue_with_caution"
        actions.append({"priority": "1", "action": "expand_akshare_1m_to_all_v57f_rebalance_targets", "allowed": "yes", "condition": "continue to log missing rows and do not optimize timing"})
    elif ak_pass > 0:
        decision = "free_source_partial_recent_or_incomplete_not_full_v5"
        actions.append({"priority": "1", "action": "use_akshare_only_as_partial_probe", "allowed": "yes", "condition": "not formal full-window evidence"})
    else:
        decision = "free_source_not_feasible_for_full_v5_window"
        actions.append({"priority": "1", "action": "do_not_expand_free_source_bulk_pull", "allowed": "yes", "condition": "avoid wasting calls on failing endpoint"})
    if sina_recent > 0:
        actions.append({"priority": "2", "action": "do_not_use_akshare_sina_recent_as_v5_evidence", "allowed": "yes", "condition": "endpoint works only as recent capability probe"})
    if bs_pass > 0:
        actions.append({"priority": "3", "action": "use_baostock_5m_as_secondary_open_window_cross_check", "allowed": "yes", "condition": "5m proxy only, not 1m replacement"})
    else:
        actions.append({"priority": "3", "action": "fix_baostock_connectivity_or_use_local_tdx_for_cross_check", "allowed": "yes", "condition": "BaoStock currently unavailable in probe"})
    actions.append({"priority": "4", "action": "keep_v57f_frozen_and_do_not_run_minute_timing_optimization", "allowed": "yes", "condition": "governance hard rule"})
    return decision, actions


def build_failure_diagnosis(probe: pd.DataFrame) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not probe[probe["source"].eq("akshare")]["status"].eq("pass").any():
        rows.append(
            {
                "issue_id": "akshare_eastmoney_historical_minute_failed",
                "source": "akshare",
                "observed_result": "0 pass rows in V5 historical sample; errors are RemoteDisconnected/empty coverage",
                "root_cause": "Public Eastmoney minute endpoint is unstable in this environment; AKShare 1m Eastmoney path is also recent-limited through ndays=5 for 1m.",
                "v5d_impact": "Cannot complete V5 full-window 1m execution audit from AKShare online source.",
                "recommended_solution": "Use paid/full historical minute export, local TDX minute files, or another audited vendor for 2021-10-08 to 2026-05-31.",
            }
        )
    if not probe[probe["source"].eq("baostock")]["status"].eq("pass").any():
        rows.append(
            {
                "issue_id": "baostock_connectivity_or_service_timeout",
                "source": "baostock",
                "observed_result": "BaoStock login/query probe timed out.",
                "root_cause": "BaoStock service/network connectivity unavailable from current environment; it is also only a 5m/15m/30m/60m proxy for this task.",
                "v5d_impact": "Cannot use BaoStock as immediate cross-source check.",
                "recommended_solution": "Retry from local desktop network later; otherwise use TDX local data or RQData/Wind/iFinD/Tushare minute export.",
            }
        )
    if probe[probe["source"].eq("akshare_sina_recent")]["status"].eq("recent_only_not_requested_v5_date").any():
        rows.append(
            {
                "issue_id": "akshare_sina_recent_only",
                "source": "akshare_sina_recent",
                "observed_result": "Sina endpoint returns recent 1m rows but not requested V5 rebalance dates.",
                "root_cause": "Free public Sina minute endpoint has limited historical depth.",
                "v5d_impact": "Can prove API capability, but cannot serve as V5 historical evidence.",
                "recommended_solution": "Use only for live/recent smoke test outside V5 evidence; do not bulk-run for V5.",
            }
        )
    return rows


def build_solution_table() -> list[dict[str, str]]:
    return [
        {
            "priority": "1",
            "route": "local_tdx_minute_files",
            "coverage_potential": "high_if_local_history_downloaded",
            "cost": "free",
            "how_to_use": "Install/use TDX client to download 1m history for V57f target stocks, then read .lc1/.lc5 files locally.",
            "fit_for_v5d": "best_free_candidate",
            "caution": "Must audit missing days, corporate-action handling, and field definitions.",
        },
        {
            "priority": "2",
            "route": "jqdata_historical_export_or_renewal",
            "coverage_potential": "high_if_full_history_permission_enabled",
            "cost": "paid_or_export",
            "how_to_use": "Ask vendor for 2021-10-08 to 2026-05-31 1m OHLCV/amount export for V57f codes.",
            "fit_for_v5d": "best_low_engineering_cost",
            "caution": "Recent-15-month plan cannot cover full V5 window.",
        },
        {
            "priority": "3",
            "route": "rqdata_wind_ifind_tushare_export",
            "coverage_potential": "medium_to_high",
            "cost": "paid_or_points",
            "how_to_use": "Run a capability probe first, then export only rebalance-day target universe.",
            "fit_for_v5d": "vendor_fallback",
            "caution": "Need source metadata and reproducible extraction log.",
        },
        {
            "priority": "4",
            "route": "akshare_sina_recent_smoke_test",
            "coverage_potential": "recent_only",
            "cost": "free",
            "how_to_use": "Use only to validate parser and report template on recent rows.",
            "fit_for_v5d": "not_formal_v5_evidence",
            "caution": "Do not use post-2026-05-31 rows inside V5 results.",
        },
    ]


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = pd.read_csv(INPUT_TARGETS)
    samples = pick_probe_samples(targets)
    write_csv(OUTPUT_DIR / "v5d_free_source_probe_sample.csv", samples.to_dict("records"))

    results: list[SourceResult] = []
    for _, row in samples.iterrows():
        results.append(run_ak_probe(row))

    for _, row in samples.head(4).iterrows():
        results.append(run_ak_sina_recent_probe(row))

    # BaoStock is a secondary source. It can hang in some network environments, so call it only
    # after AKShare and keep the overall probe bounded by the caller's process timeout.
    results.extend(run_baostock_probe_rows_bounded(samples))

    result_rows = [r.__dict__ for r in results]
    write_csv(OUTPUT_DIR / "v5d_free_source_probe_results.csv", result_rows)

    probe_df = pd.DataFrame(result_rows)
    decision, actions = build_recommendations(probe_df)
    write_csv(OUTPUT_DIR / "v5d_free_source_next_actions.csv", actions)
    failure_diagnosis = build_failure_diagnosis(probe_df)
    write_csv(OUTPUT_DIR / "v5d_free_source_failure_diagnosis.csv", failure_diagnosis)
    solution_table = build_solution_table()
    write_csv(OUTPUT_DIR / "v5d_free_source_solution_table.csv", solution_table)

    source_summary = []
    for source, group in probe_df.groupby("source"):
        source_summary.append(
            {
                "source": source,
                "requested_frequency": ",".join(sorted(set(group["requested_frequency"].astype(str)))),
                "sample_rows": int(len(group)),
                "pass_rows": int(group["status"].eq("pass").sum()),
                "empty_rows": int(group["status"].eq("empty").sum()),
                "error_rows": int(group["status"].isin(["error", "query_error", "login_error", "timeout"]).sum()),
                "min_trade_date": str(group["trade_date"].min()),
                "max_trade_date": str(group["trade_date"].max()),
                "median_elapsed_sec": round(float(group["elapsed_sec"].median()), 3) if len(group) else None,
                "sample_status": "pass" if int(group["status"].eq("pass").sum()) > 0 else "not_pass",
            }
        )
    write_csv(OUTPUT_DIR / "v5d_free_source_capability_matrix.csv", source_summary)

    summary = {
        "schema_version": 1,
        "project": "v5d_free_minute_source_audit",
        "created_at_local": datetime.now().isoformat(timespec="seconds"),
        "status": decision,
        "v57f_core_modified": False,
        "joinquant_started": False,
        "minute_timing_optimization_started": False,
        "input_targets": str(INPUT_TARGETS.relative_to(WORKSPACE)),
        "sample_count": int(len(samples)),
        "source_summary": source_summary,
        "governance_read": "Free-source data can only support execution feasibility audit after coverage and cross-source quality checks; it cannot change V57f or V5c archived conclusions.",
        "outputs": {
            "summary": "v5d_free_minute_source_audit/current/v5d_free_source_audit_summary.json",
            "report": "v5d_free_minute_source_audit/current/v5d_free_source_audit_report.md",
            "sample": "v5d_free_minute_source_audit/current/v5d_free_source_probe_sample.csv",
            "probe_results": "v5d_free_minute_source_audit/current/v5d_free_source_probe_results.csv",
            "capability_matrix": "v5d_free_minute_source_audit/current/v5d_free_source_capability_matrix.csv",
            "next_actions": "v5d_free_minute_source_audit/current/v5d_free_source_next_actions.csv",
            "failure_diagnosis": "v5d_free_minute_source_audit/current/v5d_free_source_failure_diagnosis.csv",
            "solution_table": "v5d_free_minute_source_audit/current/v5d_free_source_solution_table.csv",
        },
    }
    (OUTPUT_DIR / "v5d_free_source_audit_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report = [
        "# V5d Free Minute Source Audit",
        "",
        "## PM Conclusion",
        f"- Status: `{decision}`",
        "- V57f frozen core was not modified.",
        "- This audit checks free-source execution feasibility only; it does not optimize minute timing.",
        "",
        "## Source Probe Summary",
    ]
    for item in source_summary:
        report.append(
            f"- {item['source']}: {item['pass_rows']}/{item['sample_rows']} pass, "
            f"frequency={item['requested_frequency']}, dates={item['min_trade_date']} to {item['max_trade_date']}, "
            f"median_elapsed_sec={item['median_elapsed_sec']}"
        )
    report.extend(
        [
            "",
            "## Failure Diagnosis",
        ]
    )
    for item in failure_diagnosis:
        report.append(f"- {item['issue_id']}: {item['v5d_impact']} Recommended: {item['recommended_solution']}")
    report.extend(
        [
            "",
            "## Solution Table",
        ]
    )
    for item in solution_table:
        report.append(f"- P{item['priority']} {item['route']}: {item['fit_for_v5d']} ({item['caution']})")
    report.extend(
        [
            "",
            "## Next Actions",
        ]
    )
    for action in actions:
        report.append(f"- P{action['priority']}: {action['action']} ({action['condition']})")
    report.extend(
        [
            "",
            "## Blocked / Caution",
            "- Free public endpoints may be rate-limited, schema-changing, or incomplete across the full V5 historical window.",
            "- BaoStock is a 5-minute cross-check source for this task; it is not a 1-minute replacement.",
            "- Any full formal minute evidence still requires complete coverage through 2026-05-31 and reproducible source metadata.",
        ]
    )
    (OUTPUT_DIR / "v5d_free_source_audit_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())

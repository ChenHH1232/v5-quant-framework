from __future__ import annotations

import csv
import json
import math
import multiprocessing as mp
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_pre2021_factor_panel_repair") / "current"
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
PRE2021_START = "2019-01-01"
PRE2021_END = "2020-12-31"
PANEL_START = "2019-04-01"
PANEL_END = "2020-10-31"
STRICT_REPAIR_ROOT = Path("processed") / "pre2021_repaired_factor_panels_v5"
SECTORS = {
    "highway_infrastructure": {
        "short_id": "highway_v54h",
        "price_file": "highway_v54h_startup_repaired_daily_prices.csv",
        "current_panel_parts": ["startup_preload_repaired_panels_v5", "highway_v54h", "panel_with_low_vol.csv"],
    },
    "port_rail_infrastructure": {
        "short_id": "port_rail_v55j",
        "price_file": "port_rail_v55j_startup_repaired_daily_prices.csv",
        "current_panel_parts": ["startup_preload_repaired_panels_v5", "port_rail_v55j", "panel_with_low_vol.csv"],
    },
}
PANEL_FIELDS = [
    "trade_date",
    "code",
    "sub_industry",
    "close",
    "price_adjustment",
    "next_trade_date",
    "price_return",
    "dividend_return",
    "total_return",
    "future_return",
    "return_source",
    "benchmark_return",
    "benchmark_source",
    "low_price_to_book",
    "pe_ratio",
    "market_cap",
    "dividend_yield",
    "revenue_growth_yoy",
    "total_revenue_growth_yoy",
    "ocf_to_revenue",
    "cash_collection_quality",
    "operating_cash_flow_yield",
    "free_cash_flow_yield",
    "return_on_equity_ttm",
    "operating_cash_flow_to_net_profit",
    "interest_coverage",
    "capex_burden",
    "asset_liability_ratio",
    "factor_visible_date",
    "factor_visibility_source",
    "universe_visible_date",
    "universe_source",
    "dividend_visible_policy",
    "volatility_60d",
    "volatility_120d",
    "volatility_252d",
    "downside_volatility_60d",
    "downside_volatility_120d",
    "downside_volatility_252d",
    "max_drawdown_60d",
    "max_drawdown_120d",
    "max_drawdown_252d",
    "low_vol_score",
    "low_vol_factor_visible_date",
    "low_vol_factor_source",
    "low_vol_observation_count_60d",
    "low_vol_observation_count_120d",
    "low_vol_observation_count_252d",
    "pre2021_repair_scope",
    "pre2021_repair_status",
    "pre2021_universe_pit_status",
    "pre2021_financial_factor_equivalence",
    "pre2021_repair_notes",
]


@dataclass(frozen=True)
class RepairPaths:
    output_dir: Path
    db_root: Path
    strict_root: Path


def run_v5f_pre2021_factor_panel_repair(
    root: Path = Path("."),
    *,
    fetch_baostock: bool = True,
    baostock_timeout_sec: int = 120,
    baostock_fetch_scope: str = "strict",
) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    db_root = _database_root(root)
    paths = RepairPaths(out, db_root, db_root / STRICT_REPAIR_ROOT)
    paths.strict_root.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    if db_root == Path(""):
        blockers.append(_blocker("missing_database_root", "fatal", "all", "No processed database root was found.", "restore local database/processed directory"))
        summary = _summary("blocked_missing_database_root", blockers, [], [], [], fetch_baostock, False)
        _write_outputs(paths, summary, {}, {}, [], [], [], blockers, [])
        return summary

    price_by_sector, price_audit = _load_prices(paths)
    strict_universe = _strict_universe_by_sector(paths)
    proxy_universe = {
        sector_id: {day: sorted(price_by_sector[sector_id]) for day in _panel_dates(price_by_sector[sector_id])}
        for sector_id in SECTORS
    }
    fetch_codes = _baostock_fetch_codes(price_by_sector, strict_universe, baostock_fetch_scope)
    baostock_payload = _fetch_baostock_payload(fetch_codes, fetch_baostock, baostock_timeout_sec)
    valuations = baostock_payload.get("valuations", {})
    dividends = baostock_payload.get("dividends", {})
    fetch_rows = baostock_payload.get("fetch_rows", [])

    strict_panels: dict[str, list[dict[str, Any]]] = {}
    proxy_panels: dict[str, list[dict[str, Any]]] = {}
    for sector_id in SECTORS:
        strict_panels[sector_id] = _panel_rows(
            sector_id,
            price_by_sector.get(sector_id, {}),
            valuations,
            dividends,
            strict_universe.get(sector_id, {}),
            scope="strict_pit_universe",
        )
        proxy_panels[sector_id] = _panel_rows(
            sector_id,
            price_by_sector.get(sector_id, {}),
            valuations,
            dividends,
            proxy_universe.get(sector_id, {}),
            scope="price_universe_proxy_not_validation",
        )

    panel_manifest = _write_panel_files(paths, strict_panels, proxy_panels)
    universe_audit = _universe_audit(strict_universe, proxy_universe)
    field_coverage = _field_coverage(strict_panels, proxy_panels)
    source_audit = _source_audit(fetch_rows, price_audit)
    blockers.extend(_repair_blockers(strict_panels, field_coverage, baostock_payload))
    next_queue = _next_queue(blockers)
    strict_ready = _strict_ready(strict_panels)
    status = "completed_pre2021_factor_panel_repair_partial" if not strict_ready else "completed_pre2021_factor_panel_repair_ready"
    summary = _summary(status, blockers, panel_manifest, universe_audit, field_coverage, fetch_baostock, baostock_payload.get("started", False))
    _write_outputs(paths, summary, strict_panels, proxy_panels, panel_manifest, universe_audit, field_coverage, blockers, next_queue, source_audit)
    return summary


def _database_root(root: Path) -> Path:
    candidates = [
        p
        for p in root.iterdir()
        if p.is_dir()
        and (p / "processed").is_dir()
        and (p / "processed" / "startup_preload_repaired_prices_v5").is_dir()
    ]
    if not candidates:
        return Path("")
    return sorted(candidates, key=lambda p: str(p))[0]


def _load_prices(paths: RepairPaths) -> tuple[dict[str, dict[str, list[dict[str, Any]]]], list[dict[str, Any]]]:
    result: dict[str, dict[str, list[dict[str, Any]]]] = {}
    audit: list[dict[str, Any]] = []
    for sector_id, cfg in SECTORS.items():
        path = paths.db_root / "processed" / "startup_preload_repaired_prices_v5" / str(cfg["price_file"])
        if not path.exists():
            result[sector_id] = {}
            audit.append({"sector_id": sector_id, "price_path": str(path), "status": "missing", "row_count": 0})
            continue
        df = pd.read_csv(path, dtype=str)
        date_col = "date" if "date" in df.columns else "trade_date"
        df[date_col] = df[date_col].astype(str).str.slice(0, 10)
        df = df[(df[date_col] >= PRE2021_START) & (df[date_col] <= PRE2021_END)].copy()
        by_code: dict[str, list[dict[str, Any]]] = {}
        for code, group in df.sort_values([date_col, "code"]).groupby("code"):
            rows = []
            for rec in group.to_dict("records"):
                close = _safe_float(rec.get("close"))
                if close is None or close <= 0:
                    continue
                rows.append(
                    {
                        "date": str(rec.get(date_col))[:10],
                        "code": str(code),
                        "open": _safe_float(rec.get("open")),
                        "high": _safe_float(rec.get("high")),
                        "low": _safe_float(rec.get("low")),
                        "close": close,
                        "volume": _safe_float(rec.get("volume")),
                        "amount": _safe_float(rec.get("money") or rec.get("amount")),
                    }
                )
            if rows:
                by_code[str(code)] = rows
        result[sector_id] = by_code
        all_dates = sorted({row["date"] for rows in by_code.values() for row in rows})
        audit.append(
            {
                "sector_id": sector_id,
                "price_path": str(path),
                "status": "pass",
                "row_count": sum(len(rows) for rows in by_code.values()),
                "code_count": len(by_code),
                "first_date": all_dates[0] if all_dates else "",
                "last_date": all_dates[-1] if all_dates else "",
            }
        )
    return result, audit


def _baostock_fetch_codes(
    price_by_sector: dict[str, dict[str, list[dict[str, Any]]]],
    strict_universe: dict[str, dict[str, list[dict[str, Any]]]],
    fetch_scope: str,
) -> list[str]:
    all_codes = sorted({code for sector_prices in price_by_sector.values() for code in sector_prices})
    strict_codes = sorted(
        {
            str(entry.get("code") or "")
            for sector_universe in strict_universe.values()
            for entries in sector_universe.values()
            for entry in entries
            if str(entry.get("code") or "").strip()
        }
    )
    if fetch_scope == "all":
        return all_codes
    return strict_codes


def _fetch_baostock_payload(codes: list[str], fetch: bool, timeout_sec: int) -> dict[str, Any]:
    if not fetch:
        return {
            "started": False,
            "fetch_code_count": len(codes),
            "valuations": {},
            "dividends": {},
            "fetch_rows": [{"source": "baostock", "status": "not_run", "detail": "fetch disabled", "code_count": len(codes)}],
        }
    started = time.perf_counter()
    if not codes:
        return {
            "started": True,
            "fetch_code_count": 0,
            "valuations": {},
            "dividends": {},
            "fetch_rows": [{"source": "baostock", "status": "not_run", "detail": "no strict PIT codes to fetch", "code_count": 0}],
        }
    valuations: dict[str, dict[str, dict[str, Any]]] = {}
    dividends: dict[str, list[dict[str, Any]]] = {}
    fetch_rows: list[dict[str, Any]] = []
    per_code_timeout = max(8.0, min(45.0, timeout_sec / max(len(codes), 1)))
    for code in codes:
        elapsed = time.perf_counter() - started
        remaining = timeout_sec - elapsed
        if remaining <= 0:
            fetch_rows.append(
                {
                    "source": "baostock",
                    "code": code,
                    "status": "timeout",
                    "elapsed_sec": round(elapsed, 3),
                    "detail": "BaoStock overall timeout reached before this code was fetched",
                    "code_count": 1,
                }
            )
            continue
        code_timeout = min(per_code_timeout, remaining)
        payload = _fetch_baostock_code_payload(code, code_timeout)
        valuations.update(payload.get("valuations", {}))
        dividends.update(payload.get("dividends", {}))
        fetch_rows.extend(payload.get("fetch_rows", []))
    fetch_rows.append(
        {
            "source": "baostock",
            "status": "completed_with_per_code_timeouts" if any(row.get("status") == "timeout" for row in fetch_rows) else "completed",
            "elapsed_sec": round(time.perf_counter() - started, 3),
            "detail": "per-code bounded BaoStock fetch",
            "code_count": len(codes),
        }
    )
    return {
        "started": True,
        "fetch_code_count": len(codes),
        "valuations": valuations,
        "dividends": dividends,
        "fetch_rows": fetch_rows,
    }


def _fetch_baostock_code_payload(code: str, timeout_sec: float) -> dict[str, Any]:
    parent_conn, child_conn = mp.Pipe(duplex=False)
    process = mp.Process(target=_baostock_worker, args=([code], child_conn))
    started = time.perf_counter()
    process.start()
    child_conn.close()
    payload: dict[str, Any] | None = None
    deadline = started + timeout_sec
    while time.perf_counter() < deadline:
        if parent_conn.poll(0.2):
            payload = parent_conn.recv()
            break
        if not process.is_alive():
            break
    if payload is not None:
        process.join(5)
        if process.is_alive():
            process.terminate()
            process.join()
        parent_conn.close()
        return payload
    if not process.is_alive():
        process.join()
        parent_conn.close()
        return {
            "valuations": {},
            "dividends": {},
            "fetch_rows": [
                {
                    "source": "baostock",
                    "code": code,
                    "status": f"process_exit_{process.exitcode}",
                    "elapsed_sec": round(time.perf_counter() - started, 3),
                    "detail": "BaoStock worker exited without payload",
                    "code_count": 1,
                }
            ],
        }
    process.terminate()
    process.join()
    parent_conn.close()
    return {
        "valuations": {},
        "dividends": {},
        "fetch_rows": [
            {
                "source": "baostock",
                "code": code,
                "status": "timeout",
                "elapsed_sec": round(time.perf_counter() - started, 3),
                "detail": f"BaoStock factor fetch exceeded per-code timeout {timeout_sec:.1f} seconds",
                "code_count": 1,
            }
        ],
    }


def _baostock_worker(codes: list[str], sink: Any) -> None:
    started = time.perf_counter()
    fetch_rows: list[dict[str, Any]] = []
    valuations: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    dividends: dict[str, list[dict[str, Any]]] = defaultdict(list)
    try:
        import baostock as bs

        login = bs.login()
        if login.error_code != "0":
            _send_worker_payload(
                sink,
                {
                    "valuations": {},
                    "dividends": {},
                    "fetch_rows": [
                        {
                            "source": "baostock",
                            "status": "login_error",
                            "detail": str(login.error_msg),
                            "elapsed_sec": round(time.perf_counter() - started, 3),
                        }
                    ],
                }
            )
            return
        try:
            for code in codes:
                dividends[code] = dividends[code]
                bs_code = _jq_to_baostock(code)
                k_started = time.perf_counter()
                rs = bs.query_history_k_data_plus(
                    bs_code,
                    "date,code,close,peTTM,pbMRQ,psTTM,pcfNcfTTM",
                    start_date=PRE2021_START,
                    end_date=PRE2021_END,
                    frequency="d",
                    adjustflag="3",
                )
                k_rows = []
                while rs.error_code == "0" and rs.next():
                    k_rows.append(rs.get_row_data())
                if rs.error_code == "0":
                    for row in k_rows:
                        rec = dict(zip(rs.fields, row))
                        day = str(rec.get("date") or "")[:10]
                        if day:
                            valuations[code][day] = {
                                "close": _safe_float(rec.get("close")),
                                "peTTM": _safe_float(rec.get("peTTM")),
                                "pbMRQ": _safe_float(rec.get("pbMRQ")),
                                "psTTM": _safe_float(rec.get("psTTM")),
                                "pcfNcfTTM": _safe_float(rec.get("pcfNcfTTM")),
                            }
                    fetch_rows.append(
                        {
                            "source": "baostock_history_k",
                            "code": code,
                            "status": "pass",
                            "row_count": len(k_rows),
                            "elapsed_sec": round(time.perf_counter() - k_started, 3),
                            "detail": "",
                        }
                    )
                else:
                    fetch_rows.append(
                        {
                            "source": "baostock_history_k",
                            "code": code,
                            "status": "query_error",
                            "row_count": 0,
                            "elapsed_sec": round(time.perf_counter() - k_started, 3),
                            "detail": str(rs.error_msg),
                        }
                    )
                for year in ["2018", "2019", "2020"]:
                    d_started = time.perf_counter()
                    div = bs.query_dividend_data(code=bs_code, year=year, yearType="report")
                    d_rows = []
                    while div.error_code == "0" and div.next():
                        d_rows.append(div.get_row_data())
                    if div.error_code == "0":
                        for row in d_rows:
                            rec = dict(zip(div.fields, row))
                            event = _dividend_event_from_baostock(code, year, rec)
                            if event:
                                dividends[code].append(event)
                        fetch_rows.append(
                            {
                                "source": "baostock_dividend",
                                "code": code,
                                "year": year,
                                "status": "pass",
                                "row_count": len(d_rows),
                                "elapsed_sec": round(time.perf_counter() - d_started, 3),
                                "detail": "",
                            }
                        )
                    else:
                        fetch_rows.append(
                            {
                                "source": "baostock_dividend",
                                "code": code,
                                "year": year,
                                "status": "query_error",
                                "row_count": 0,
                                "elapsed_sec": round(time.perf_counter() - d_started, 3),
                                "detail": str(div.error_msg),
                            }
                        )
        finally:
            bs.logout()
        _send_worker_payload(
            sink,
            {
                "valuations": {code: dict(rows) for code, rows in valuations.items()},
                "dividends": {code: rows for code, rows in dividends.items()},
                "fetch_rows": fetch_rows,
            }
        )
    except Exception as exc:
        _send_worker_payload(
            sink,
            {
                "valuations": {},
                "dividends": {},
                "fetch_rows": [
                    {
                        "source": "baostock",
                        "status": "error",
                        "elapsed_sec": round(time.perf_counter() - started, 3),
                        "detail": f"{type(exc).__name__}: {str(exc)[:500]}",
                    }
                ],
            }
        )


def _send_worker_payload(sink: Any, payload: dict[str, Any]) -> None:
    if hasattr(sink, "send"):
        sink.send(payload)
        sink.close()
    else:
        sink.put(payload)


def _strict_universe_by_sector(paths: RepairPaths) -> dict[str, dict[str, list[dict[str, Any]]]]:
    dates = _standard_panel_dates()
    return {
        "highway_infrastructure": _highway_strict_universe(paths, dates),
        "port_rail_infrastructure": _port_rail_strict_universe(paths, dates),
    }


def _highway_strict_universe(paths: RepairPaths, dates: list[str]) -> dict[str, list[dict[str, Any]]]:
    segment_paths = [
        paths.db_root
        / "processed"
        / "highway_operating_data"
        / "pre2021_supplement"
        / "highway_segment_business_evidence_eastmoney.csv",
        paths.db_root
        / "processed"
        / "highway_operating_data"
        / "annual_reports_2020_2025"
        / "highway_segment_business_evidence_eastmoney_2020_2025.csv",
    ]
    result = {day: [] for day in dates}
    path = next((candidate for candidate in segment_paths if candidate.exists()), None)
    if path is None:
        return _highway_reviewed_operating_strict_universe(paths, dates)
    df = pd.read_csv(path, dtype=str)
    if "visible_date" not in df.columns:
        return _highway_reviewed_operating_strict_universe(paths, dates)
    core_tags = {"core_toll_road_operator", "mixed_highway_operator"}
    df = df[df.get("pit_usable", "").astype(str).str.lower().eq("true")].copy()
    if "approved_highway_business_tag" in df.columns:
        df = df[df["approved_highway_business_tag"].isin(core_tags)].copy()
    for day in dates:
        visible = df[df["visible_date"].fillna("9999") <= day].copy()
        if visible.empty:
            continue
        latest = visible.sort_values(["code", "visible_date"]).groupby("code").tail(1)
        result[day] = [
            {
                "code": str(row["code"]),
                "sub_industry": str(row.get("approved_highway_business_tag") or "toll_road_operator"),
                "universe_visible_date": str(row.get("visible_date") or ""),
                "universe_source": "pre2021_highway_segment_business_evidence_eastmoney_tushare_disclosure",
                "business_tag": str(row.get("approved_highway_business_tag") or "reviewed_highway_operator"),
            }
            for row in latest.to_dict("records")
        ]
    return result


def _highway_reviewed_operating_strict_universe(paths: RepairPaths, dates: list[str]) -> dict[str, list[dict[str, Any]]]:
    path = (
        paths.db_root
        / "processed"
        / "highway_operating_data"
        / "annual_reports_2020_2025"
        / "highway_reviewed_operating_disclosure_data.csv"
    )
    result = {day: [] for day in dates}
    if not path.exists():
        return result
    df = pd.read_csv(path, dtype=str)
    if "visible_date" not in df.columns:
        return result
    df = df[df.get("pit_usable", "").astype(str).str.lower().eq("true")].copy()
    for day in dates:
        visible = df[df["visible_date"].fillna("9999") <= day].copy()
        if visible.empty:
            continue
        latest = visible.sort_values(["code", "visible_date"]).groupby("code").tail(1)
        result[day] = [
            {
                "code": str(row["code"]),
                "sub_industry": "toll_road_operator",
                "universe_visible_date": str(row.get("visible_date") or ""),
                "universe_source": "reviewed_highway_operating_disclosure_data",
                "business_tag": "reviewed_highway_operator",
            }
            for row in latest.to_dict("records")
        ]
    return result


def _port_rail_strict_universe(paths: RepairPaths, dates: list[str]) -> dict[str, list[dict[str, Any]]]:
    candidate_paths = [
        paths.db_root
        / "processed"
        / "port_rail_operating_evidence_v55h"
        / "pre2021_supplement"
        / "port_rail_segment_business_evidence_eastmoney.csv",
        paths.db_root
        / "processed"
        / "port_rail_operating_evidence_v55h"
        / "reviewed_evidence_v55j"
        / "port_rail_segment_business_evidence_reviewed_v55j.csv",
    ]
    path = next((candidate for candidate in candidate_paths if candidate.exists()), candidate_paths[-1])
    result = {day: [] for day in dates}
    if not path.exists():
        return result
    df = pd.read_csv(path, dtype=str)
    if "visible_date" not in df.columns:
        return result
    core_tags = {"core_port_operator", "core_rail_operator", "mixed_port_rail_operator"}
    df = df[df.get("pit_usable", "").astype(str).str.lower().eq("true")].copy()
    for day in dates:
        visible = df[df["visible_date"].fillna("9999") <= day].copy()
        if visible.empty:
            continue
        latest = visible.sort_values(["code", "visible_date"]).groupby("code").tail(1)
        latest = latest[latest["approved_port_rail_business_tag"].isin(core_tags)]
        result[day] = [
            {
                "code": str(row["code"]),
                "sub_industry": str(row.get("approved_port_rail_business_tag") or "port_rail_operator"),
                "universe_visible_date": str(row.get("visible_date") or ""),
                "universe_source": "reviewed_port_rail_business_evidence_v55j",
                "business_tag": str(row.get("approved_port_rail_business_tag") or ""),
            }
            for row in latest.to_dict("records")
        ]
    return result


def _standard_panel_dates() -> list[str]:
    return ["2019-04-01", "2019-07-01", "2019-10-08", "2020-01-02", "2020-04-01", "2020-07-01", "2020-10-09"]


def _panel_dates(price_by_code: dict[str, list[dict[str, Any]]]) -> list[str]:
    available = sorted({row["date"] for rows in price_by_code.values() for row in rows})
    result: list[str] = []
    for anchor in _standard_panel_dates():
        next_days = [day for day in available if day >= anchor]
        if next_days:
            result.append(next_days[0])
    return sorted(set(result))


def _panel_rows(
    sector_id: str,
    price_by_code: dict[str, list[dict[str, Any]]],
    valuations: dict[str, dict[str, dict[str, Any]]],
    dividends: dict[str, list[dict[str, Any]]],
    universe_by_date: dict[str, list[Any]],
    *,
    scope: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    dates = sorted(universe_by_date)
    all_price_dates = sorted({row["date"] for series in price_by_code.values() for row in series})
    for idx, day in enumerate(dates):
        next_day = dates[idx + 1] if idx + 1 < len(dates) else _next_available_date(all_price_dates, "2021-01-01")
        universe_entries = universe_by_date.get(day, [])
        for entry in universe_entries:
            if isinstance(entry, dict):
                code = str(entry.get("code") or "")
                sub_industry = str(entry.get("sub_industry") or sector_id)
                universe_visible_date = str(entry.get("universe_visible_date") or day)
                universe_source = str(entry.get("universe_source") or scope)
                pit_status = "pass"
            else:
                code = str(entry)
                sub_industry = sector_id
                universe_visible_date = ""
                universe_source = "price_file_code_universe_proxy"
                pit_status = "proxy_not_pit_clean"
            series = price_by_code.get(code, [])
            trade_price = _price_as_of(series, day)
            next_price = _price_as_of(series, next_day)
            if not trade_price:
                continue
            close = trade_price["close"]
            price_return = None
            if next_price and close:
                price_return = next_price["close"] / close - 1.0
            low_vol = _low_vol_metrics(series, day)
            valuation = _valuation_as_of(valuations.get(code, {}), day)
            dividend = _dividend_yield_as_of(dividends.get(code, []), close, day, dividend_query_known=code in dividends)
            pcf = _safe_float(valuation.get("pcfNcfTTM")) if valuation else None
            row = {
                "trade_date": day,
                "code": code,
                "sub_industry": sub_industry,
                "close": _fmt(close),
                "price_adjustment": "pre_adjusted_price",
                "next_trade_date": next_day or "",
                "price_return": _fmt(price_return),
                "dividend_return": "",
                "total_return": _fmt(price_return),
                "future_return": _fmt(price_return),
                "return_source": "local_startup_repaired_pre_adjusted_daily_price",
                "benchmark_return": "",
                "benchmark_source": "not_generated_in_pre2021_factor_repair",
                "low_price_to_book": _fmt(valuation.get("pbMRQ") if valuation else None),
                "pe_ratio": _fmt(valuation.get("peTTM") if valuation else None),
                "market_cap": "",
                "dividend_yield": _fmt(dividend.get("dividend_yield_pct")),
                "revenue_growth_yoy": "",
                "total_revenue_growth_yoy": "",
                "ocf_to_revenue": "",
                "cash_collection_quality": "",
                "operating_cash_flow_yield": "",
                "free_cash_flow_yield": "",
                "return_on_equity_ttm": "",
                "operating_cash_flow_to_net_profit": "",
                "interest_coverage": "",
                "capex_burden": "",
                "asset_liability_ratio": "",
                "factor_visible_date": day,
                "factor_visibility_source": "baostock_daily_pb_pe_pcf_as_of_trade_date;dividend_announced_cash_per_share;local_prior_daily_close_low_vol",
                "universe_visible_date": universe_visible_date,
                "universe_source": universe_source,
                "dividend_visible_policy": dividend.get("dividend_visible_policy", "no_visible_dividend_before_trade_date"),
                **low_vol,
                "pre2021_repair_scope": scope,
                "pre2021_repair_status": "generated",
                "pre2021_universe_pit_status": pit_status,
                "pre2021_financial_factor_equivalence": "partial_not_full_v57f_cashflow_equivalent",
                "pre2021_repair_notes": "OCF/capex fields were not fabricated; scoring can use PB + low-vol + drawdown only if PM approves predecessor validation.",
                "pcf_ncf_ttm": _fmt(pcf),
                "pcf_ncf_ttm_inverse_proxy": _fmt((1.0 / pcf) if pcf and pcf > 0 else None),
                "dividend_cash_per_share_used": _fmt(dividend.get("cash_per_share")),
                "dividend_visible_date_used": dividend.get("visible_date", ""),
            }
            rows.append(row)
    return rows


def _low_vol_metrics(series: list[dict[str, Any]], trade_date: str) -> dict[str, str]:
    visible = [row for row in series if row["date"] < trade_date and row.get("close")]
    returns: list[tuple[str, float]] = []
    prev = None
    for row in visible:
        close = row["close"]
        if prev and prev > 0:
            returns.append((row["date"], close / prev - 1.0))
        prev = close
    metrics: dict[str, str] = {
        "low_vol_factor_visible_date": visible[-1]["date"] if visible else "",
        "low_vol_factor_source": "local_daily_closes_strictly_before_trade_date",
    }
    parts: list[float] = []
    for window in [60, 120, 252]:
        window_returns = [value for _day, value in returns[-window:]]
        window_prices = [row["close"] for row in visible[-window:]]
        metrics[f"low_vol_observation_count_{window}d"] = str(len(window_returns))
        if len(window_returns) < min(40, window):
            for prefix in ["volatility", "downside_volatility", "max_drawdown"]:
                metrics[f"{prefix}_{window}d"] = ""
            continue
        vol = _annualized_std(window_returns)
        downside = _annualized_std([value for value in window_returns if value < 0])
        drawdown = _max_drawdown(window_prices)
        metrics[f"volatility_{window}d"] = _fmt(vol)
        metrics[f"downside_volatility_{window}d"] = _fmt(downside)
        metrics[f"max_drawdown_{window}d"] = _fmt(drawdown)
        for value in [vol, downside, drawdown]:
            if value is not None:
                parts.append(-value)
    metrics["low_vol_score"] = _fmt(mean(parts) if parts else None)
    return metrics


def _valuation_as_of(series: dict[str, dict[str, Any]], trade_date: str) -> dict[str, Any]:
    if not series:
        return {}
    dates = [day for day in series if day <= trade_date]
    return series[max(dates)] if dates else {}


def _dividend_yield_as_of(events: list[dict[str, Any]], close: float, trade_date: str, *, dividend_query_known: bool = False) -> dict[str, Any]:
    visible = [event for event in events if event.get("visible_date") and event["visible_date"] <= trade_date]
    if close <= 0:
        return {}
    if not visible:
        if dividend_query_known:
            return {
                "dividend_yield_pct": 0.0,
                "cash_per_share": 0.0,
                "visible_date": "",
                "dividend_visible_policy": "baostock_dividend_query_pass_no_visible_cash_event_lte_trade_date",
            }
        return {}
    recent = [
        event
        for event in visible
        if event.get("visible_date") >= f"{int(trade_date[:4]) - 1}{trade_date[4:]}"
    ]
    used = recent or visible[-1:]
    cash = sum(_safe_float(event.get("cash_per_share")) or 0.0 for event in used)
    return {
        "dividend_yield_pct": cash / close * 100.0 if cash > 0 else 0.0,
        "cash_per_share": cash,
        "visible_date": max(event["visible_date"] for event in used),
        "dividend_visible_policy": "baostock_dividend_cash_visible_date_lte_trade_date",
    }


def _dividend_event_from_baostock(code: str, year: str, rec: dict[str, Any]) -> dict[str, Any] | None:
    cash = _safe_float(rec.get("dividCashPsBeforeTax"))
    if cash is None:
        return None
    visible = _first_nonempty(
        rec,
        [
            "dividPlanAnnounceDate",
            "dividAgmPumDate",
            "dividPlanDate",
            "dividRegistDate",
            "dividOperateDate",
            "dividPayDate",
        ],
    )
    if not visible:
        return None
    return {
        "code": code,
        "report_year": year,
        "visible_date": str(visible)[:10],
        "cash_per_share": cash,
        "source": "baostock.query_dividend_data",
    }


def _write_panel_files(
    paths: RepairPaths,
    strict_panels: dict[str, list[dict[str, Any]]],
    proxy_panels: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for sector_id, cfg in SECTORS.items():
        out_dir = paths.strict_root / str(cfg["short_id"])
        out_dir.mkdir(parents=True, exist_ok=True)
        strict_path = out_dir / "strict_pit_panel_with_low_vol.csv"
        proxy_path = out_dir / "price_universe_proxy_panel_with_low_vol.csv"
        _write_csv(strict_path, _fields(strict_panels[sector_id]), strict_panels[sector_id])
        _write_csv(proxy_path, _fields(proxy_panels[sector_id]), proxy_panels[sector_id])
        _write_csv(paths.output_dir / f"v5f_pre2021_{cfg['short_id']}_strict_panel_with_low_vol.csv", _fields(strict_panels[sector_id]), strict_panels[sector_id])
        _write_csv(paths.output_dir / f"v5f_pre2021_{cfg['short_id']}_proxy_panel_with_low_vol.csv", _fields(proxy_panels[sector_id]), proxy_panels[sector_id])
        manifest.append(
            {
                "sector_id": sector_id,
                "strict_panel_path": str(strict_path),
                "proxy_panel_path": str(proxy_path),
                "strict_row_count": len(strict_panels[sector_id]),
                "proxy_row_count": len(proxy_panels[sector_id]),
                "strict_date_count": len({row["trade_date"] for row in strict_panels[sector_id]}),
                "proxy_date_count": len({row["trade_date"] for row in proxy_panels[sector_id]}),
                "strict_code_count": len({row["code"] for row in strict_panels[sector_id]}),
                "proxy_code_count": len({row["code"] for row in proxy_panels[sector_id]}),
                "status": "strict_generated" if strict_panels[sector_id] else "strict_empty_proxy_generated",
            }
        )
    return manifest


def _universe_audit(strict_universe: dict[str, dict[str, list[dict[str, Any]]]], proxy_universe: dict[str, dict[str, list[str]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sector_id in SECTORS:
        dates = sorted(set(strict_universe.get(sector_id, {})) | set(proxy_universe.get(sector_id, {})))
        for day in dates:
            strict_codes = [str(item.get("code")) for item in strict_universe.get(sector_id, {}).get(day, [])]
            proxy_codes = proxy_universe.get(sector_id, {}).get(day, [])
            rows.append(
                {
                    "sector_id": sector_id,
                    "trade_date": day,
                    "strict_pit_code_count": len(strict_codes),
                    "proxy_code_count": len(proxy_codes),
                    "strict_codes": ";".join(sorted(strict_codes)),
                    "proxy_only_code_count": len(set(proxy_codes) - set(strict_codes)),
                    "pit_status": "pass" if strict_codes else "missing_strict_pit_universe",
                    "governance_note": "Proxy universe is not valid for independent validation unless PIT universe evidence is repaired.",
                }
            )
    return rows


def _field_coverage(strict_panels: dict[str, list[dict[str, Any]]], proxy_panels: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fields = ["low_vol_score", "volatility_120d", "max_drawdown_120d", "low_price_to_book", "dividend_yield", "operating_cash_flow_yield", "capex_burden"]
    for sector_id in SECTORS:
        for scope, panel in [("strict_pit_universe", strict_panels[sector_id]), ("price_universe_proxy_not_validation", proxy_panels[sector_id])]:
            for field in fields:
                nonempty = sum(1 for row in panel if str(row.get(field) or "").strip() not in {"", "nan", "NaN"})
                rows.append(
                    {
                        "sector_id": sector_id,
                        "scope": scope,
                        "field": field,
                        "row_count": len(panel),
                        "nonempty_count": nonempty,
                        "coverage_ratio": _fmt(nonempty / len(panel) if panel else None),
                        "field_status": "pass" if panel and nonempty == len(panel) else ("partial" if nonempty else "missing"),
                    }
                )
    return rows


def _source_audit(fetch_rows: list[dict[str, Any]], price_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    rows.extend({"audit_type": "price_source", **row} for row in price_audit)
    rows.extend({"audit_type": "baostock_source", **row} for row in fetch_rows)
    return rows


def _repair_blockers(
    strict_panels: dict[str, list[dict[str, Any]]],
    field_coverage: list[dict[str, Any]],
    baostock_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not strict_panels.get("highway_infrastructure"):
        rows.append(
            _blocker(
                "highway_pre2021_strict_pit_universe_missing",
                "blocking_for_complete_pre2021_multisleeve_pool",
                "highway_infrastructure",
                "Local highway reviewed operating evidence becomes visible in 2021, so no strict PIT pre-2021 highway universe row can be generated.",
                "source or review 2019 annual / 2020 semiannual highway operating evidence with visible dates before target 2020 rebalance dates",
            )
        )
    port_dates = {row["trade_date"] for row in strict_panels.get("port_rail_infrastructure", [])}
    if len(port_dates) < len(_standard_panel_dates()):
        rows.append(
            _blocker(
                "port_rail_pre2021_strict_pit_universe_partial",
                "blocking_for_complete_pre2021_multisleeve_pool",
                "port_rail_infrastructure",
                f"Strict PIT port/rail rows exist only for dates: {';'.join(sorted(port_dates)) or 'none'}.",
                "source or review pre-2020 business-purity evidence and visible dates before 2019/early-2020 rebalance dates",
            )
        )
    fetch_statuses = {str(row.get("status") or "") for row in baostock_payload.get("fetch_rows", [])}
    if "timeout" in fetch_statuses or "login_error" in fetch_statuses or "error" in fetch_statuses:
        rows.append(
            _blocker(
                "baostock_factor_fetch_incomplete",
                "blocking_for_factor_completion",
                "baostock",
                ";".join(sorted(fetch_statuses)),
                "rerun BaoStock factor fetch or use another PIT-clean valuation/dividend source",
            )
        )
    for row in field_coverage:
        if row["scope"] == "strict_pit_universe" and row["field"] in {"operating_cash_flow_yield", "capex_burden"} and row["field_status"] == "missing":
            rows.append(
                _blocker(
                    f"{row['sector_id']}_{row['field']}_not_rebuilt",
                    "not_blocking_for_required_field_gate_but_blocks_full_v57f_factor_equivalence",
                    str(row["sector_id"]),
                    f"{row['field']} was not fabricated from non-equivalent sources.",
                    "fetch PIT fundamentals with announcement dates or approve predecessor scoring without this factor",
                )
            )
    return rows


def _strict_ready(strict_panels: dict[str, list[dict[str, Any]]]) -> bool:
    if any(not rows for rows in strict_panels.values()):
        return False
    dates = [set(row["trade_date"] for row in rows) for rows in strict_panels.values()]
    common = set.intersection(*dates) if dates else set()
    return bool(common)


def _next_queue(blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "queue_id": "source_highway_2019_2020_operating_evidence",
            "priority": "P0",
            "condition": any(row["blocker_id"] == "highway_pre2021_strict_pit_universe_missing" for row in blockers),
            "action": "Review or source 2019 annual and 2020 semiannual highway operating evidence with visible dates before 2020 rebalance dates.",
        },
        {
            "queue_id": "source_port_rail_pre2020_business_purity_evidence",
            "priority": "P0",
            "condition": any(row["blocker_id"] == "port_rail_pre2021_strict_pit_universe_partial" for row in blockers),
            "action": "Review older port/rail original annual reports so 2019 and early-2020 PIT universe rows can be used.",
        },
        {
            "queue_id": "decide_predecessor_factor_equivalence",
            "priority": "P1",
            "condition": True,
            "action": "PM/Quant must decide whether PB + low-vol + drawdown + dividend yield is sufficient for predecessor-only validation, since OCF/capex were not rebuilt.",
        },
    ]


def _summary(
    status: str,
    blockers: list[dict[str, Any]],
    panel_manifest: list[dict[str, Any]],
    universe_audit: list[dict[str, Any]],
    field_coverage: list[dict[str, Any]],
    fetch_requested: bool,
    fetch_started: bool,
) -> dict[str, Any]:
    strict_rows = sum(int(row.get("strict_row_count") or 0) for row in panel_manifest)
    proxy_rows = sum(int(row.get("proxy_row_count") or 0) for row in panel_manifest)
    blocking_blockers = [row for row in blockers if not str(row.get("severity", "")).startswith("not_blocking")]
    return {
        "schema_version": 1,
        "project": "v5f_pre2021_factor_panel_repair",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "backtest_scope": {"start_date": BACKTEST_START, "end_date": BACKTEST_END},
        "pre2021_repair_scope": {"start_date": PRE2021_START, "end_date": PRE2021_END},
        "baostock_fetch_requested": fetch_requested,
        "baostock_fetch_started": fetch_started,
        "joinquant_started": False,
        "v57f_core_modified": False,
        "accepted": False,
        "strict_pit_panel_total_rows": strict_rows,
        "proxy_panel_total_rows": proxy_rows,
        "strict_pit_common_date_count": _common_strict_date_count(panel_manifest, universe_audit),
        "highway_strict_rows": _manifest_value(panel_manifest, "highway_infrastructure", "strict_row_count"),
        "port_rail_strict_rows": _manifest_value(panel_manifest, "port_rail_infrastructure", "strict_row_count"),
        "pm_gate_decision": "pre2021_factor_panel_repair_partial_not_complete_multisleeve"
        if blocking_blockers
        else "pre2021_factor_panel_repair_required_fields_complete_not_full_v57f_equivalent",
        "blocker_count": len(blocking_blockers),
        "non_equivalence_warning": "OCF/capex fields were not fabricated; full V57f factor equivalence is not achieved.",
    }


def _common_strict_date_count(panel_manifest: list[dict[str, Any]], universe_audit: list[dict[str, Any]]) -> int:
    dates_by_sector: dict[str, set[str]] = defaultdict(set)
    for row in universe_audit:
        if int(row.get("strict_pit_code_count") or 0) > 0:
            dates_by_sector[str(row["sector_id"])].add(str(row["trade_date"]))
    if set(dates_by_sector) != set(SECTORS):
        return 0
    return len(set.intersection(*dates_by_sector.values()))


def _manifest_value(rows: list[dict[str, Any]], sector_id: str, field: str) -> int:
    for row in rows:
        if row.get("sector_id") == sector_id:
            return int(row.get(field) or 0)
    return 0


def _report(summary: dict[str, Any], blockers: list[dict[str, Any]]) -> str:
    lines = [
        "# V5f Pre-2021 Factor Panel Repair",
        "",
        f"Created at UTC: `{summary['created_at_utc']}`",
        "",
        "## Decision",
        "",
        f"- Status: `{summary['status']}`",
        f"- PM gate: `{summary['pm_gate_decision']}`",
        f"- Strict PIT rows: `{summary['strict_pit_panel_total_rows']}`",
        f"- Proxy rows: `{summary['proxy_panel_total_rows']}`",
        f"- JoinQuant started: `{summary['joinquant_started']}`",
        "",
        "## Interpretation",
        "",
        "Strict PIT repair uses pre-2021 visible business-inclusion evidence where available. If the PM gate is required-fields complete, the remaining OCF/capex rows are non-equivalence warnings rather than P0 data blockers.",
        "",
        "Proxy panels were generated only as reference. They must not be used as independent validation because their universe is the local price universe rather than a repaired PIT universe.",
        "",
        "## Blockers",
        "",
    ]
    for row in blockers:
        lines.append(f"- `{row['blocker_id']}` (`{row['severity']}`): {row['detail']} Next: {row['next_action']}")
    return "\n".join(lines) + "\n"


def _write_outputs(
    paths: RepairPaths,
    summary: dict[str, Any],
    strict_panels: dict[str, list[dict[str, Any]]],
    proxy_panels: dict[str, list[dict[str, Any]]],
    panel_manifest: list[dict[str, Any]],
    universe_audit: list[dict[str, Any]],
    field_coverage: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    next_queue: list[dict[str, Any]],
    source_audit: list[dict[str, Any]] | None = None,
) -> None:
    source_audit = source_audit or []
    _write_json(paths.output_dir / "v5f_pre2021_factor_panel_repair_summary.json", summary)
    (paths.output_dir / "v5f_pre2021_factor_panel_repair_report.md").write_text(_report(summary, blockers), encoding="utf-8")
    _write_csv(paths.output_dir / "v5f_pre2021_factor_panel_manifest.csv", _fields(panel_manifest), panel_manifest)
    _write_csv(paths.output_dir / "v5f_pre2021_universe_pit_audit.csv", _fields(universe_audit), universe_audit)
    _write_csv(paths.output_dir / "v5f_pre2021_field_coverage_after_repair.csv", _fields(field_coverage), field_coverage)
    _write_csv(paths.output_dir / "v5f_pre2021_factor_source_audit.csv", _fields(source_audit), source_audit)
    _write_csv(paths.output_dir / "v5f_pre2021_factor_panel_repair_blockers.csv", _fields(blockers), blockers)
    _write_csv(paths.output_dir / "v5f_pre2021_factor_panel_repair_next_queue.csv", _fields(next_queue), next_queue)
    (paths.output_dir / "v5f_pre2021_factor_panel_repair_agent_execution_rules.md").write_text(
        "\n".join(
            [
                "- Do not use proxy panels as independent validation.",
                "- Do not fabricate OCF/capex fields from non-equivalent sources.",
                "- Do not mark V5f or any pre-2021 repair accepted.",
                "- Do not modify V57f core or the 2021-05-01 to 2026-05-31 backtest boundary.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _blocker(blocker_id: str, severity: str, scope: str, detail: str, next_action: str) -> dict[str, Any]:
    return {
        "blocker_id": blocker_id,
        "severity": severity,
        "scope": scope,
        "detail": detail,
        "next_action": next_action,
    }


def _price_as_of(series: list[dict[str, Any]], day: str) -> dict[str, Any] | None:
    candidates = [row for row in series if row["date"] <= day]
    return candidates[-1] if candidates else None


def _next_available_date(dates: list[str], anchor: str) -> str:
    candidates = [day for day in dates if day >= anchor]
    return candidates[0] if candidates else ""


def _annualized_std(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    avg = mean(values)
    variance = sum((value - avg) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance) * math.sqrt(252)


def _max_drawdown(prices: list[float]) -> float | None:
    if len(prices) < 2:
        return None
    peak = prices[0]
    max_dd = 0.0
    for price in prices:
        peak = max(peak, price)
        if peak > 0:
            max_dd = max(max_dd, 1.0 - price / peak)
    return max_dd


def _jq_to_baostock(code: str) -> str:
    plain = code.split(".")[0]
    if code.endswith(".XSHG"):
        return f"sh.{plain}"
    if code.endswith(".XSHE"):
        return f"sz.{plain}"
    return code


def _safe_float(value: Any) -> float | None:
    if value in {None, "", "nan", "NaN", "None"}:
        return None
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        numeric = float(match.group(0))
    except ValueError:
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _fmt(value: Any) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return ""
    return f"{numeric:.10g}"


def _first_nonempty(row: dict[str, Any], fields: list[str]) -> str:
    for field in fields:
        value = str(row.get(field) or "").strip()
        if value:
            return value
    return ""


def _fields(rows: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    for preferred in PANEL_FIELDS:
        if any(preferred in row for row in rows):
            fields.append(preferred)
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    return fields or ["empty"]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--no-baostock", action="store_true")
    parser.add_argument("--baostock-timeout-sec", type=int, default=120)
    parser.add_argument("--baostock-fetch-scope", choices=["strict", "all"], default="strict")
    args = parser.parse_args()
    result = run_v5f_pre2021_factor_panel_repair(
        args.root,
        fetch_baostock=not args.no_baostock,
        baostock_timeout_sec=args.baostock_timeout_sec,
        baostock_fetch_scope=args.baostock_fetch_scope,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

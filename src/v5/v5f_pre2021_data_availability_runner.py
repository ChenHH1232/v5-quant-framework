from __future__ import annotations

import csv
import json
import math
import multiprocessing as mp
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v5.basket_field_utils import enrich_basket_panel_row
from v5.basket_scoring import score_basket_date_rows
from v5.math_utils import fmt_float, to_float


OUT_DIR = Path("v5f_pre2021_repaired_multisleeve_data_gate") / "current"
CONFIG = Path("config") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f_startup_repaired_shadow.json"
PRE2021_START = "2014-01-01"
PRE2021_END = "2020-12-31"
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
REQUIRED_FIELDS = ["low_vol_score", "volatility_120d", "dividend_yield"]
PRE2021_REPAIRED_STRICT_PANELS = {
    "highway_infrastructure": Path("processed") / "pre2021_repaired_factor_panels_v5" / "highway_v54h" / "strict_pit_panel_with_low_vol.csv",
    "port_rail_infrastructure": Path("processed") / "pre2021_repaired_factor_panels_v5" / "port_rail_v55j" / "strict_pit_panel_with_low_vol.csv",
}


@dataclass(frozen=True)
class BaoStockProbe:
    source: str
    window_scope: str
    trade_date: str
    code: str
    sleeve: str
    requested_frequency: str
    status: str
    row_count: int
    first_time: str
    last_time: str
    total_volume: float | None
    total_amount: float | None
    elapsed_sec: float
    error_type: str
    error_message: str
    research_window_usable: bool
    backtest_window_usable: bool
    api_capability_note: str


def run_v5f_pre2021_data_availability_gate(
    root: Path = Path("."),
    *,
    probe_baostock: bool = False,
    baostock_timeout_sec: int = 8,
) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    config_path = root / CONFIG
    blockers: list[dict[str, Any]] = []
    if not config_path.exists():
        blockers.append(
            {
                "blocker_id": "missing_v57f_repaired_shadow_config",
                "severity": "fatal",
                "scope": "pre2021_multisleeve_pool",
                "detail": str(CONFIG),
                "next_action": "restore repaired V57f startup shadow config before rerun",
            }
        )
        summary = _summary("blocked_missing_repaired_config", blockers, [], [], [], [], [])
        _write_all(out, summary, [], [], [], [], [], blockers, [], [], [])
        return summary

    config = _read_json(config_path)
    sectors = _sectors_with_resolved_paths(root, config)
    panel_coverage = _panel_coverage_rows(sectors)
    price_coverage = _price_coverage_rows(sectors)
    field_coverage = _field_coverage_rows(sectors)
    feasibility = _pool_feasibility_rows(sectors, panel_coverage, price_coverage, field_coverage)
    preview = _candidate_signal_preview(config, sectors)
    baostock_probe = _baostock_probe_rows(probe_baostock, baostock_timeout_sec)
    blockers = _blockers(feasibility, panel_coverage, baostock_probe)
    next_queue = _next_queue(feasibility, baostock_probe)
    rules = _rules()

    pre2021_status = _pre2021_status(feasibility)
    baostock_status = _baostock_status(baostock_probe, probe_baostock)
    blocking_blockers = [row for row in blockers if not str(row.get("severity", "")).startswith("not_a_blocker")]
    status = "completed_pre2021_data_gate_with_blockers" if blocking_blockers else "completed_pre2021_data_gate"
    summary = _summary(
        status,
        blockers,
        panel_coverage,
        field_coverage,
        feasibility,
        baostock_probe,
        preview,
        pre2021_multisleeve_pool_status=pre2021_status,
        baostock_2014_2020_status=baostock_status,
    )
    _write_all(
        out,
        summary,
        baostock_probe,
        panel_coverage,
        field_coverage,
        feasibility,
        preview,
        blockers,
        next_queue,
        price_coverage,
        rules,
    )
    return summary


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _database_roots(root: Path) -> list[Path]:
    result: list[Path] = []
    for child in root.iterdir():
        if child.is_dir() and (child / "processed").is_dir():
            result.append(child)
    result.sort(key=lambda p: 0 if (p / "processed" / "startup_preload_repaired_panels_v5").exists() else 1)
    return result


def _resolve_workspace_path(root: Path, raw: str) -> Path:
    direct = root / raw
    if direct.exists():
        return direct
    normalized = raw.replace("\\", "/")
    marker = "processed/"
    if marker in normalized:
        suffix = normalized.split(marker, 1)[1]
        for db_root in _database_roots(root):
            candidate = db_root / "processed" / Path(suffix)
            if candidate.exists():
                return candidate
        roots = _database_roots(root)
        if roots:
            return roots[0] / "processed" / Path(suffix)
    return direct


def _sectors_with_resolved_paths(root: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    sectors: list[dict[str, Any]] = []
    for sector in config.get("sectors", []):
        item = dict(sector)
        sector_id = str(sector.get("sector_id") or "")
        startup_panel_path = _resolve_workspace_path(root, str(sector.get("panel_csv") or ""))
        repaired_panel_path = _resolve_pre2021_repaired_panel_path(root, sector_id)
        item["startup_panel_path"] = startup_panel_path
        item["panel_path"] = repaired_panel_path or startup_panel_path
        item["panel_source_scope"] = "pre2021_repaired_strict_pit_panel" if repaired_panel_path else "startup_repaired_shadow_panel"
        item["price_path"] = _resolve_workspace_path(root, str(sector.get("price_csv") or ""))
        sectors.append(item)
    return sectors


def _resolve_pre2021_repaired_panel_path(root: Path, sector_id: str) -> Path | None:
    suffix = PRE2021_REPAIRED_STRICT_PANELS.get(sector_id)
    if not suffix:
        return None
    for db_root in _database_roots(root):
        candidate = db_root / suffix
        if candidate.exists():
            return candidate
    return None


def _read_header(path: Path) -> list[str]:
    if not path.exists():
        return []
    return pd.read_csv(path, nrows=0).columns.astype(str).tolist()


def _nonempty(series: pd.Series) -> pd.Series:
    return series.notna() & series.astype(str).str.strip().ne("")


def _date_col(columns: list[str]) -> str:
    if "trade_date" in columns:
        return "trade_date"
    if "date" in columns:
        return "date"
    return columns[0] if columns else "trade_date"


def _panel_coverage_rows(sectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sector in sectors:
        path = Path(sector["panel_path"])
        sector_id = str(sector.get("sector_id") or "")
        header = _read_header(path)
        if not path.exists() or not header:
            rows.append(
                {
                    "sector_id": sector_id,
                    "panel_path": str(path),
                    "panel_source_scope": str(sector.get("panel_source_scope") or ""),
                    "startup_panel_path": str(sector.get("startup_panel_path") or ""),
                    "exists": False,
                    "row_count": 0,
                    "min_trade_date": "",
                    "max_trade_date": "",
                    "pre2021_row_count": 0,
                    "pre2021_date_count": 0,
                    "pre2021_code_count": 0,
                    "pre_backtest_row_count": 0,
                    "candidate_date_count_pre2021": 0,
                    "first_candidate_date_pre2021": "",
                    "last_candidate_date_pre2021": "",
                    "coverage_status": "missing_panel_file",
                }
            )
            continue
        usecols = [_date_col(header)]
        if "code" in header:
            usecols.append("code")
        usecols.extend([f for f in REQUIRED_FIELDS if f in header])
        usecols = sorted(set(usecols))
        df = pd.read_csv(path, usecols=usecols, dtype=str)
        date_col = _date_col(df.columns.astype(str).tolist())
        dates = df[date_col].astype(str).str.slice(0, 10)
        pre2021 = (dates >= PRE2021_START) & (dates <= PRE2021_END)
        pre_backtest = dates < BACKTEST_START
        required_present = [field for field in REQUIRED_FIELDS if field in df.columns]
        required_mask = pre2021.copy()
        for field in REQUIRED_FIELDS:
            if field in df.columns:
                required_mask &= _nonempty(df[field])
            else:
                required_mask &= False
        candidate_dates = sorted(set(dates[required_mask].tolist()))
        rows.append(
            {
                "sector_id": sector_id,
                "panel_path": str(path),
                "panel_source_scope": str(sector.get("panel_source_scope") or ""),
                "startup_panel_path": str(sector.get("startup_panel_path") or ""),
                "exists": True,
                "row_count": int(len(df)),
                "min_trade_date": str(dates.min()) if len(dates) else "",
                "max_trade_date": str(dates.max()) if len(dates) else "",
                "pre2021_row_count": int(pre2021.sum()),
                "pre2021_date_count": int(dates[pre2021].nunique()),
                "pre2021_code_count": int(df.loc[pre2021, "code"].nunique()) if "code" in df.columns else 0,
                "pre_backtest_row_count": int(pre_backtest.sum()),
                "candidate_date_count_pre2021": len(candidate_dates),
                "first_candidate_date_pre2021": candidate_dates[0] if candidate_dates else "",
                "last_candidate_date_pre2021": candidate_dates[-1] if candidate_dates else "",
                "required_fields_present": ";".join(required_present),
                "coverage_status": "pass_pre2021_candidate_rows" if candidate_dates else "no_pre2021_required_field_candidate_rows",
            }
        )
    return rows


def _price_coverage_rows(sectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sector in sectors:
        path = Path(sector["price_path"])
        sector_id = str(sector.get("sector_id") or "")
        header = _read_header(path)
        if not path.exists() or not header:
            rows.append(
                {
                    "sector_id": sector_id,
                    "price_path": str(path),
                    "exists": False,
                    "row_count": 0,
                    "min_trade_date": "",
                    "max_trade_date": "",
                    "pre2021_row_count": 0,
                    "pre2021_date_count": 0,
                    "pre2021_code_count": 0,
                    "coverage_status": "missing_price_file",
                }
            )
            continue
        date_col = _date_col(header)
        code_col = "code" if "code" in header else None
        usecols = [date_col] + ([code_col] if code_col else [])
        df = pd.read_csv(path, usecols=usecols, dtype=str)
        dates = df[date_col].astype(str).str.slice(0, 10)
        pre2021 = (dates >= PRE2021_START) & (dates <= PRE2021_END)
        rows.append(
            {
                "sector_id": sector_id,
                "price_path": str(path),
                "exists": True,
                "row_count": int(len(df)),
                "min_trade_date": str(dates.min()) if len(dates) else "",
                "max_trade_date": str(dates.max()) if len(dates) else "",
                "pre2021_row_count": int(pre2021.sum()),
                "pre2021_date_count": int(dates[pre2021].nunique()),
                "pre2021_code_count": int(df.loc[pre2021, code_col].nunique()) if code_col else 0,
                "coverage_status": "pass_pre2021_prices" if int(pre2021.sum()) > 0 else "no_pre2021_prices",
            }
        )
    return rows


def _field_coverage_rows(sectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sector in sectors:
        sector_id = str(sector.get("sector_id") or "")
        path = Path(sector["panel_path"])
        header = _read_header(path)
        if not path.exists() or not header:
            for field in REQUIRED_FIELDS:
                rows.append(
                    {
                        "sector_id": sector_id,
                        "field": field,
                        "field_exists": False,
                        "total_nonempty_rows": 0,
                        "pre2021_nonempty_rows": 0,
                        "pre2021_nonempty_dates": 0,
                        "first_nonempty_date": "",
                        "first_pre2021_nonempty_date": "",
                        "field_status": "missing_panel_file",
                    }
                )
            continue
        date_col = _date_col(header)
        usecols = sorted(set([date_col, *[f for f in REQUIRED_FIELDS if f in header]]))
        df = pd.read_csv(path, usecols=usecols, dtype=str)
        dates = df[date_col].astype(str).str.slice(0, 10)
        pre2021 = (dates >= PRE2021_START) & (dates <= PRE2021_END)
        for field in REQUIRED_FIELDS:
            if field not in df.columns:
                rows.append(
                    {
                        "sector_id": sector_id,
                        "field": field,
                        "field_exists": False,
                        "total_nonempty_rows": 0,
                        "pre2021_nonempty_rows": 0,
                        "pre2021_nonempty_dates": 0,
                        "first_nonempty_date": "",
                        "first_pre2021_nonempty_date": "",
                        "field_status": "missing_field",
                    }
                )
                continue
            mask = _nonempty(df[field])
            pre_mask = mask & pre2021
            first_all = str(dates[mask].min()) if mask.any() else ""
            first_pre = str(dates[pre_mask].min()) if pre_mask.any() else ""
            rows.append(
                {
                    "sector_id": sector_id,
                    "field": field,
                    "field_exists": True,
                    "total_nonempty_rows": int(mask.sum()),
                    "pre2021_nonempty_rows": int(pre_mask.sum()),
                    "pre2021_nonempty_dates": int(dates[pre_mask].nunique()),
                    "first_nonempty_date": first_all,
                    "first_pre2021_nonempty_date": first_pre,
                    "field_status": "pass_pre2021" if pre_mask.any() else "no_pre2021_field_values",
                }
            )
    return rows


def _pool_feasibility_rows(
    sectors: list[dict[str, Any]],
    panel_coverage: list[dict[str, Any]],
    price_coverage: list[dict[str, Any]],
    field_coverage: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    panel_by_sector = {str(row["sector_id"]): row for row in panel_coverage}
    price_by_sector = {str(row["sector_id"]): row for row in price_coverage}
    field_by_sector: dict[str, list[dict[str, Any]]] = {}
    for row in field_coverage:
        field_by_sector.setdefault(str(row["sector_id"]), []).append(row)
    rows: list[dict[str, Any]] = []
    for sector in sectors:
        sector_id = str(sector.get("sector_id") or "")
        panel = panel_by_sector.get(sector_id, {})
        price = price_by_sector.get(sector_id, {})
        fields = field_by_sector.get(sector_id, [])
        missing_fields = [
            str(row["field"])
            for row in fields
            if str(row.get("field_status")) != "pass_pre2021"
        ]
        panel_ok = int(panel.get("candidate_date_count_pre2021") or 0) > 0
        price_ok = int(price.get("pre2021_row_count") or 0) > 0
        sector_status = "pass_pre2021_pool_input" if panel_ok and price_ok and not missing_fields else "blocked_pre2021_pool_input"
        reason_parts = []
        if not panel_ok:
            reason_parts.append("no pre-2021 panel date has all required fields")
        if not price_ok:
            reason_parts.append("no pre-2021 repaired daily prices")
        if missing_fields:
            reason_parts.append("missing pre-2021 required fields: " + ";".join(missing_fields))
        rows.append(
            {
                "scope": "sector",
                "sector_id": sector_id,
                "status": sector_status,
                "pre2021_candidate_dates": panel.get("candidate_date_count_pre2021", 0),
                "pre2021_price_dates": price.get("pre2021_date_count", 0),
                "missing_or_blocked_fields": ";".join(missing_fields),
                "reason": "; ".join(reason_parts),
            }
        )
    passed = [row for row in rows if row["status"] == "pass_pre2021_pool_input"]
    blocked = [row for row in rows if row["status"] != "pass_pre2021_pool_input"]
    all_candidate_date_sets = []
    for row in panel_coverage:
        sector_id = str(row["sector_id"])
        if int(row.get("candidate_date_count_pre2021") or 0) <= 0:
            all_candidate_date_sets.append(set())
            continue
        # Re-read only for exact common-date audit; small cost, keeps the output explicit.
        sector = next(item for item in sectors if str(item.get("sector_id") or "") == sector_id)
        all_candidate_date_sets.append(_candidate_dates_for_sector(Path(sector["panel_path"])))
    common_dates = set.intersection(*all_candidate_date_sets) if all_candidate_date_sets else set()
    rows.append(
        {
            "scope": "portfolio",
            "sector_id": "all_repaired_v57f_sleeves",
            "status": "pre2021_multisleeve_pool_ready" if not blocked and common_dates else "pre2021_pool_blocked_by_required_fields",
            "pre2021_candidate_dates": len(common_dates),
            "pre2021_price_dates": min([int(r.get("pre2021_date_count") or 0) for r in price_coverage] or [0]),
            "missing_or_blocked_fields": ";".join(str(row["sector_id"]) for row in blocked),
            "reason": "all four repaired V57f sleeves have common pre-2021 candidate dates"
            if not blocked and common_dates
            else "complete pre-2021 repaired V57f multi-sleeve pool is unavailable; do not substitute V4 bank/core predecessor pool",
            "partial_predecessor_sleeves_available": ";".join(str(row["sector_id"]) for row in passed),
            "v4_reference_only": True,
        }
    )
    return rows


def _candidate_dates_for_sector(panel_path: Path) -> set[str]:
    header = _read_header(panel_path)
    if not panel_path.exists() or not header:
        return set()
    date_col = _date_col(header)
    usecols = sorted(set([date_col, *[f for f in REQUIRED_FIELDS if f in header]]))
    df = pd.read_csv(panel_path, usecols=usecols, dtype=str)
    dates = df[date_col].astype(str).str.slice(0, 10)
    mask = (dates >= PRE2021_START) & (dates <= PRE2021_END)
    for field in REQUIRED_FIELDS:
        if field not in df.columns:
            return set()
        mask &= _nonempty(df[field])
    return set(dates[mask].tolist())


def _candidate_signal_preview(config: dict[str, Any], sectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidate_dates_by_sector = {
        str(sector.get("sector_id") or ""): _candidate_dates_for_sector(Path(sector["panel_path"]))
        for sector in sectors
    }
    union_dates = sorted(set().union(*candidate_dates_by_sector.values())) if candidate_dates_by_sector else []
    if not union_dates:
        return []
    preview_dates = sorted(set([union_dates[0], union_dates[-1]]))
    raw_spec = {"signals": config.get("signals", {})}
    rows: list[dict[str, Any]] = []
    for day in preview_dates:
        day_rows: list[dict[str, Any]] = []
        for sector in sectors:
            sector_id = str(sector.get("sector_id") or "")
            if day not in candidate_dates_by_sector.get(sector_id, set()):
                continue
            panel_path = Path(sector["panel_path"])
            header = _read_header(panel_path)
            if not header:
                continue
            date_col = _date_col(header)
            df = pd.read_csv(panel_path, dtype=str)
            day_df = df[df[date_col].astype(str).str.slice(0, 10).eq(day)]
            for record in day_df.to_dict("records"):
                enriched = enrich_basket_panel_row(record, sector_id)
                enriched["sector_id"] = sector_id
                enriched["source_strategy_id"] = str(sector.get("strategy_id") or "")
                day_rows.append(enriched)
        if not day_rows:
            continue
        scored, used_factors = score_basket_date_rows(raw_spec, day_rows)
        scored.sort(key=lambda item: to_float(item.get("score")) or -999999.0, reverse=True)
        for rank, item in enumerate(scored[:28], start=1):
            rows.append(
                {
                    "preview_date": day,
                    "code": item.get("code", ""),
                    "sector_id": item.get("sector_id", ""),
                    "selected_rank": rank,
                    "score": fmt_float(item.get("score")),
                    "used_factors": ";".join(used_factors),
                    "preview_status": "partial_predecessor_only_not_complete_v57f"
                    if len({r.get("sector_id") for r in scored}) < len(sectors)
                    else "complete_multisleeve_preview",
                    "governance_note": "V4 is reference only; this preview is not an accepted or validated strategy.",
                }
            )
    return rows


def _probe_samples() -> list[dict[str, str]]:
    samples = [
        ("pre2021_research", "2014-01-02", "600036.XSHG", "bank"),
        ("pre2021_research", "2015-01-05", "600036.XSHG", "bank"),
        ("pre2021_research", "2016-01-04", "600036.XSHG", "bank"),
        ("pre2021_research", "2017-01-03", "600036.XSHG", "bank"),
        ("pre2021_research", "2018-01-02", "600036.XSHG", "bank"),
        ("pre2021_research", "2019-01-02", "600036.XSHG", "bank"),
        ("pre2021_research", "2019-12-02", "600036.XSHG", "bank"),
        ("pre2021_research", "2020-01-02", "600036.XSHG", "bank"),
        ("pre2021_research", "2020-06-01", "600036.XSHG", "bank"),
        ("pre2021_research", "2020-12-01", "600036.XSHG", "bank"),
        ("pre2021_research", "2020-12-01", "600027.XSHG", "utilities_electricity"),
        ("pre2021_research", "2020-12-01", "600035.XSHG", "highway_infrastructure"),
        ("pre2021_research", "2020-12-01", "600018.XSHG", "port_rail_infrastructure"),
        ("backtest_scope_probe", "2021-05-06", "600036.XSHG", "bank"),
        ("backtest_scope_probe", "2026-05-29", "600000.XSHG", "bank"),
        ("api_capability_after_backtest", "2026-07-31", "600000.XSHG", "api_probe"),
    ]
    return [
        {"window_scope": scope, "trade_date": day, "code": code, "sleeve": sleeve, "requested_frequency": "5min"}
        for scope, day, code, sleeve in samples
    ]


def _jq_to_baostock(code: str) -> str:
    plain = code.split(".")[0]
    if code.endswith(".XSHG"):
        return f"sh.{plain}"
    if code.endswith(".XSHE"):
        return f"sz.{plain}"
    return code


def _baostock_worker(sample: dict[str, str], queue: mp.Queue) -> None:
    started = time.perf_counter()
    try:
        import baostock as bs

        login = bs.login()
        if login.error_code != "0":
            queue.put(
                {
                    "status": "login_error",
                    "row_count": 0,
                    "first_time": "",
                    "last_time": "",
                    "total_volume": None,
                    "total_amount": None,
                    "error_type": login.error_code,
                    "error_message": str(login.error_msg)[:500],
                    "elapsed_sec": time.perf_counter() - started,
                }
            )
            return
        try:
            rs = bs.query_history_k_data_plus(
                _jq_to_baostock(sample["code"]),
                "date,time,code,open,high,low,close,volume,amount",
                start_date=sample["trade_date"],
                end_date=sample["trade_date"],
                frequency="5",
                adjustflag="3",
            )
            records = []
            while rs.error_code == "0" and rs.next():
                records.append(rs.get_row_data())
            if rs.error_code != "0":
                payload = {
                    "status": "query_error",
                    "row_count": 0,
                    "first_time": "",
                    "last_time": "",
                    "total_volume": None,
                    "total_amount": None,
                    "error_type": str(rs.error_code),
                    "error_message": str(rs.error_msg)[:500],
                }
            elif not records:
                payload = {
                    "status": "empty",
                    "row_count": 0,
                    "first_time": "",
                    "last_time": "",
                    "total_volume": None,
                    "total_amount": None,
                    "error_type": "",
                    "error_message": "",
                }
            else:
                df = pd.DataFrame(records, columns=rs.fields)
                payload = {
                    "status": "pass",
                    "row_count": int(len(df)),
                    "first_time": str(df.iloc[0]["time"]),
                    "last_time": str(df.iloc[-1]["time"]),
                    "total_volume": _safe_float(pd.to_numeric(df["volume"], errors="coerce").sum()),
                    "total_amount": _safe_float(pd.to_numeric(df["amount"], errors="coerce").sum()),
                    "error_type": "",
                    "error_message": "",
                }
        finally:
            bs.logout()
        payload["elapsed_sec"] = time.perf_counter() - started
        queue.put(payload)
    except Exception as exc:
        queue.put(
            {
                "status": "error",
                "row_count": 0,
                "first_time": "",
                "last_time": "",
                "total_volume": None,
                "total_amount": None,
                "elapsed_sec": time.perf_counter() - started,
                "error_type": type(exc).__name__,
                "error_message": str(exc)[:500],
            }
        )


def _run_single_baostock_probe(sample: dict[str, str], timeout_sec: int) -> BaoStockProbe:
    queue: mp.Queue = mp.Queue()
    process = mp.Process(target=_baostock_worker, args=(sample, queue))
    started = time.perf_counter()
    process.start()
    process.join(timeout_sec)
    if process.is_alive():
        process.terminate()
        process.join()
        payload = {
            "status": "timeout",
            "row_count": 0,
            "first_time": "",
            "last_time": "",
            "total_volume": None,
            "total_amount": None,
            "elapsed_sec": time.perf_counter() - started,
            "error_type": "Timeout",
            "error_message": f"BaoStock 5min probe exceeded {timeout_sec} seconds",
        }
    elif not queue.empty():
        payload = queue.get()
    else:
        payload = {
            "status": f"process_exit_{process.exitcode}",
            "row_count": 0,
            "first_time": "",
            "last_time": "",
            "total_volume": None,
            "total_amount": None,
            "elapsed_sec": time.perf_counter() - started,
            "error_type": "NoPayload",
            "error_message": "BaoStock subprocess exited without payload",
        }
    return BaoStockProbe(
                source="baostock",
                window_scope=sample["window_scope"],
                trade_date=sample["trade_date"],
                code=sample["code"],
                sleeve=sample["sleeve"],
                requested_frequency=sample["requested_frequency"],
                status=str(payload.get("status") or ""),
                row_count=int(payload.get("row_count") or 0),
                first_time=str(payload.get("first_time") or ""),
        last_time=str(payload.get("last_time") or ""),
        total_volume=_safe_float(payload.get("total_volume")),
        total_amount=_safe_float(payload.get("total_amount")),
                elapsed_sec=round(float(payload.get("elapsed_sec") or 0.0), 3),
                error_type=str(payload.get("error_type") or ""),
                error_message=str(payload.get("error_message") or ""),
                research_window_usable=_is_research_window_usable(sample, payload),
                backtest_window_usable=_is_backtest_window_usable(sample, payload),
                api_capability_note=_api_capability_note(sample, payload),
            )


def _baostock_probe_rows(probe_baostock: bool, timeout_sec: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sample in _probe_samples():
        if not probe_baostock:
            probe = BaoStockProbe(
                source="baostock",
                window_scope=sample["window_scope"],
                trade_date=sample["trade_date"],
                code=sample["code"],
                sleeve=sample["sleeve"],
                requested_frequency=sample["requested_frequency"],
                status="not_run",
                row_count=0,
                first_time="",
                last_time="",
                total_volume=None,
                total_amount=None,
                elapsed_sec=0.0,
                error_type="ProbeDisabled",
                error_message="Set probe_baostock=True to run bounded BaoStock availability probes.",
                research_window_usable=False,
                backtest_window_usable=False,
                api_capability_note="probe_not_run",
            )
        else:
            probe = _run_single_baostock_probe(sample, timeout_sec)
        rows.append(probe.__dict__)
    return rows


def _is_research_window_usable(sample: dict[str, str], payload: dict[str, Any]) -> bool:
    return (
        sample.get("window_scope") == "pre2021_research"
        and str(payload.get("status") or "") == "pass"
        and int(payload.get("row_count") or 0) > 0
    )


def _is_backtest_window_usable(sample: dict[str, str], payload: dict[str, Any]) -> bool:
    return (
        sample.get("window_scope") == "backtest_scope_probe"
        and str(payload.get("status") or "") == "pass"
        and int(payload.get("row_count") or 0) > 0
    )


def _api_capability_note(sample: dict[str, str], payload: dict[str, Any]) -> str:
    status = str(payload.get("status") or "")
    row_count = int(payload.get("row_count") or 0)
    scope = sample.get("window_scope") or ""
    if status == "not_run":
        return "probe_not_run"
    if scope == "api_capability_after_backtest" and status == "pass" and row_count > 0:
        return "baostock_5min_api_available_after_20260531_not_used_for_backtest"
    if scope == "backtest_scope_probe" and status == "pass" and row_count > 0:
        return "baostock_5min_available_inside_20210501_20260531_backtest_window"
    if scope == "pre2021_research" and status == "pass" and row_count > 0:
        return "baostock_5min_available_for_this_pre2021_probe_date"
    if scope == "pre2021_research" and status == "empty":
        return "baostock_returned_empty_for_this_pre2020_probe_date_not_a_post2020_limit"
    return "probe_did_not_confirm_5min_availability"


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except Exception:
        return None


def _baostock_status(rows: list[dict[str, Any]], probe_started: bool) -> str:
    if not probe_started:
        return "not_run"
    research_rows = [row for row in rows if str(row.get("window_scope") or "") == "pre2021_research"]
    statuses = {str(row.get("status") or "") for row in research_rows}
    pass_years = {
        str(row.get("trade_date"))[:4]
        for row in research_rows
        if str(row.get("status") or "") == "pass"
    }
    empty_years = {
        str(row.get("trade_date"))[:4]
        for row in research_rows
        if str(row.get("status") or "") == "empty"
    }
    if len(pass_years) == 7:
        return "pre2021_2014_2020_5min_available_in_probe"
    if "2020" in pass_years and empty_years.intersection({"2014", "2015", "2016", "2017", "2018", "2019"}):
        return "pre2021_2020_5min_available_pre2020_not_confirmed"
    if "pass" in statuses:
        return "partial_pre2021_5min_available_in_probe"
    if "timeout" in statuses:
        return "pre2021_5min_unavailable_or_source_timeout"
    return "pre2021_5min_not_confirmed_by_probe"


def _baostock_api_capability_status(rows: list[dict[str, Any]], probe_started: bool) -> str:
    if not probe_started:
        return "not_run"
    backtest_rows = [row for row in rows if str(row.get("window_scope") or "") == "backtest_scope_probe"]
    api_rows = [row for row in rows if str(row.get("window_scope") or "") == "api_capability_after_backtest"]
    backtest_pass = any(str(row.get("status") or "") == "pass" and int(row.get("row_count") or 0) > 0 for row in backtest_rows)
    after_backtest_pass = any(str(row.get("status") or "") == "pass" and int(row.get("row_count") or 0) > 0 for row in api_rows)
    if backtest_pass and after_backtest_pass:
        return "baostock_5min_available_inside_backtest_and_after_20260531"
    if backtest_pass:
        return "baostock_5min_available_inside_backtest_only"
    if after_backtest_pass:
        return "baostock_5min_available_after_20260531_only"
    return "baostock_5min_api_capability_not_confirmed"


def _pre2021_status(feasibility: list[dict[str, Any]]) -> str:
    portfolio = next((row for row in feasibility if row.get("scope") == "portfolio"), {})
    return str(portfolio.get("status") or "pre2021_pool_blocked_by_required_fields")


def _blockers(
    feasibility: list[dict[str, Any]],
    panel_coverage: list[dict[str, Any]],
    baostock_probe: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    portfolio = next((row for row in feasibility if row.get("scope") == "portfolio"), {})
    if portfolio.get("status") != "pre2021_multisleeve_pool_ready":
        rows.append(
            {
                "blocker_id": "pre2021_complete_repaired_multisleeve_pool_unavailable",
                "severity": "blocking_for_independent_pre2021_validation",
                "scope": "pre2021_multisleeve_pool",
                "detail": str(portfolio.get("reason") or ""),
                "next_action": "repair or source PIT-clean pre-2021 factor panels for blocked repaired V57f sleeves",
            }
        )
    for row in panel_coverage:
        if str(row.get("coverage_status")) != "pass_pre2021_candidate_rows":
            rows.append(
                {
                    "blocker_id": f"missing_pre2021_required_panel_{row.get('sector_id')}",
                    "severity": "blocking_for_complete_multisleeve_pool",
                    "scope": "pre2021_multisleeve_pool",
                    "detail": "no pre-2021 panel date has all required fields",
                    "next_action": "source PIT-clean pre-2021 panel fields for this sleeve or keep as unavailable",
                }
            )
    statuses = {str(row.get("status") or "") for row in baostock_probe}
    baostock_status = _baostock_status(baostock_probe, statuses != {"not_run"})
    api_status = _baostock_api_capability_status(baostock_probe, statuses != {"not_run"})
    if statuses and statuses != {"not_run"} and baostock_status != "pre2021_2014_2020_5min_available_in_probe":
        rows.append(
            {
                "blocker_id": "baostock_pre2020_5min_not_confirmed",
                "severity": "blocks_short_window_independent_validation_only",
                "scope": "baostock_5min_availability",
                "detail": f"{baostock_status}; api_capability={api_status}; statuses={';'.join(sorted(statuses))}",
                "next_action": "do not treat BaoStock as capped at 2020; use BaoStock for 2020+ minute checks and source another PIT-clean provider if 2014-2019 5min validation is required",
            }
        )
    rows.append(
        {
            "blocker_id": "v4_5min_not_required",
            "severity": "not_a_blocker",
            "scope": "v4_reference",
            "detail": "V4 is reference only and already complete; no V4 5min repair is required.",
            "next_action": "do not use V4 as V57f repaired multi-sleeve substitute",
        }
    )
    rows.append(
        {
            "blocker_id": "post_20260531_not_required",
            "severity": "not_a_blocker",
            "scope": "backtest_boundary",
            "detail": "Current backtest scope ends at 2026-05-31.",
            "next_action": "do not require data after 2026-05-31 for this repair gate",
        }
    )
    return rows


def _next_queue(feasibility: list[dict[str, Any]], baostock_probe: list[dict[str, Any]]) -> list[dict[str, Any]]:
    portfolio = next((row for row in feasibility if row.get("scope") == "portfolio"), {})
    baostock_status = _baostock_status(baostock_probe, any(str(row.get("status")) != "not_run" for row in baostock_probe))
    api_status = _baostock_api_capability_status(baostock_probe, any(str(row.get("status")) != "not_run" for row in baostock_probe))
    rows = [
        {
            "queue_id": "repair_pre2021_highway_port_rail_factor_panels",
            "priority": "P0",
            "condition": portfolio.get("status") != "pre2021_multisleeve_pool_ready",
            "owner": "data_engineering",
            "action": "find or rebuild PIT-clean pre-2021 required factor panels for highway and port/rail sleeves; prices alone are insufficient",
        },
        {
            "queue_id": "resolve_pre2020_5min_source_if_short_window_validation_needed",
            "priority": "P1",
            "condition": baostock_status
            in {
                "partial_pre2021_5min_available_in_probe",
                "pre2021_5min_unavailable_or_source_timeout",
                "pre2021_5min_not_confirmed_by_probe",
                "pre2021_2020_5min_available_pre2020_not_confirmed",
                "not_run",
            },
            "owner": "data_engineering",
            "action": f"BaoStock API status is {api_status}; if pre-2020 short-window reversal must be independently validated, source PIT-clean 2014-2019 5min data from another provider instead of assuming BaoStock is capped at 2020",
        },
        {
            "queue_id": "keep_v5f_2021_20260531_as_backtest_only",
            "priority": "P1",
            "condition": True,
            "owner": "pm_quant",
            "action": "keep V5f momentum as historical backtest candidate not accepted; do not relabel 2021-2026 as OOS validation",
        },
    ]
    return rows


def _summary(
    status: str,
    blockers: list[dict[str, Any]],
    panel_coverage: list[dict[str, Any]],
    field_coverage: list[dict[str, Any]],
    feasibility: list[dict[str, Any]],
    baostock_probe: list[dict[str, Any]],
    preview: list[dict[str, Any]],
    *,
    pre2021_multisleeve_pool_status: str = "blocked_missing_inputs",
    baostock_2014_2020_status: str = "not_run",
) -> dict[str, Any]:
    portfolio = next((row for row in feasibility if row.get("scope") == "portfolio"), {})
    return {
        "schema_version": 1,
        "project": "v5f_pre2021_repaired_multisleeve_data_gate",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "backtest_scope": {"start_date": BACKTEST_START, "end_date": BACKTEST_END},
        "pre2021_research_scope": {"start_date": PRE2021_START, "end_date": PRE2021_END},
        "v4_reference_only": True,
        "v4_5min_required": False,
        "post_20260531_required": False,
        "accepted": False,
        "live_approved": False,
        "v57f_core_modified": False,
        "pre2021_multisleeve_pool_status": pre2021_multisleeve_pool_status,
        "complete_v57f_repaired_multisleeve_pool_available": pre2021_multisleeve_pool_status == "pre2021_multisleeve_pool_ready",
        "partial_predecessor_sleeves_available": portfolio.get("partial_predecessor_sleeves_available", ""),
        "baostock_probe_started": any(str(row.get("status") or "") != "not_run" for row in baostock_probe),
        "baostock_2014_2020_status": baostock_2014_2020_status,
        "baostock_5min_api_capability_status": _baostock_api_capability_status(
            baostock_probe,
            any(str(row.get("status") or "") != "not_run" for row in baostock_probe),
        ),
        "baostock_probe_pass_count": sum(1 for row in baostock_probe if str(row.get("status")) == "pass"),
        "baostock_probe_timeout_count": sum(1 for row in baostock_probe if str(row.get("status")) == "timeout"),
        "baostock_pre2020_empty_count": sum(
            1
            for row in baostock_probe
            if str(row.get("window_scope") or "") == "pre2021_research"
            and str(row.get("trade_date") or "")[:4] < "2020"
            and str(row.get("status") or "") == "empty"
        ),
        "baostock_2020_2026_pass_count": sum(
            1
            for row in baostock_probe
            if "2020" <= str(row.get("trade_date") or "")[:4] <= "2026"
            and str(row.get("status") or "") == "pass"
        ),
        "panel_sector_count": len(panel_coverage),
        "field_audit_count": len(field_coverage),
        "candidate_signal_preview_count": len(preview),
        "blocker_count": len([row for row in blockers if str(row.get("severity")) != "not_a_blocker"]),
        "pm_gate_decision": "pre2021_pool_blocked_by_required_fields"
        if pre2021_multisleeve_pool_status != "pre2021_multisleeve_pool_ready"
        else "pre2021_multisleeve_pool_ready",
    }


def _report(summary: dict[str, Any], feasibility: list[dict[str, Any]], blockers: list[dict[str, Any]]) -> str:
    lines = [
        "# V5f Pre-2021 Repaired Multi-Sleeve Data Gate",
        "",
        f"Created at UTC: `{summary['created_at_utc']}`",
        "",
        "## Scope",
        "",
        f"- Backtest window remains `{BACKTEST_START}` to `{BACKTEST_END}`.",
        f"- Pre-2021 research availability window is `{PRE2021_START}` to `{PRE2021_END}`.",
        "- V4 is reference only; V4 5min data is not required here.",
        "- Data after 2026-05-31 is outside this repair gate.",
        "",
        "## Conclusions",
        "",
        f"- BaoStock 2014-2020 5min status: `{summary['baostock_2014_2020_status']}`.",
        f"- BaoStock 2020+/current API capability status: `{summary.get('baostock_5min_api_capability_status', '')}`.",
        "- 2026-05-31 after-date probes are API capability checks only and are not mixed into historical validation.",
        f"- Complete pre-2021 repaired V57f multi-sleeve pool: `{summary['complete_v57f_repaired_multisleeve_pool_available']}`.",
        f"- Partial predecessor sleeves available: `{summary.get('partial_predecessor_sleeves_available', '')}`.",
        f"- PM gate decision: `{summary['pm_gate_decision']}`.",
        "",
        "## Feasibility",
        "",
    ]
    for row in feasibility:
        lines.append(
            f"- `{row.get('scope')}` / `{row.get('sector_id')}`: `{row.get('status')}` - {row.get('reason', '')}"
        )
    lines.extend(["", "## Blockers", ""])
    for row in blockers:
        lines.append(
            f"- `{row.get('blocker_id')}` (`{row.get('severity')}`): {row.get('detail')} Next: {row.get('next_action')}"
        )
    return "\n".join(lines) + "\n"


def _rules() -> list[dict[str, Any]]:
    return [
        {"rule_id": "v4_reference_only", "status": "active", "detail": "Do not require V4 5min data and do not substitute V4 bank/core predecessor pool for V57f repaired multi-sleeve pool."},
        {"rule_id": "backtest_boundary", "status": "active", "detail": "Current historical backtest window ends at 2026-05-31."},
        {"rule_id": "no_acceptance", "status": "active", "detail": "No V5f/V57f component is accepted or live approved by this data gate."},
        {"rule_id": "no_v57f_core_change", "status": "active", "detail": "This gate audits data availability only and does not modify V57f core."},
    ]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or ["empty"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_all(
    out: Path,
    summary: dict[str, Any],
    baostock_probe: list[dict[str, Any]],
    panel_coverage: list[dict[str, Any]],
    field_coverage: list[dict[str, Any]],
    feasibility: list[dict[str, Any]],
    preview: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    next_queue: list[dict[str, Any]],
    price_coverage: list[dict[str, Any]],
    rules: list[dict[str, Any]],
) -> None:
    _write_json(out / "v5f_pre2021_data_gate_summary.json", summary)
    _write_csv(out / "v5f_baostock_2014_2020_5min_probe.csv", baostock_probe)
    _write_csv(out / "v5f_baostock_5min_availability_probe.csv", baostock_probe)
    _write_csv(out / "v5f_pre2021_multisleeve_panel_coverage.csv", panel_coverage)
    _write_csv(out / "v5f_pre2021_required_field_coverage.csv", field_coverage)
    _write_csv(out / "v5f_pre2021_price_coverage.csv", price_coverage)
    _write_csv(out / "v5f_pre2021_repaired_pool_feasibility.csv", feasibility)
    _write_csv(out / "v5f_pre2021_candidate_signal_preview.csv", preview)
    _write_csv(out / "v5f_pre2021_missing_data_blockers.csv", blockers)
    _write_csv(out / "v5f_pre2021_next_queue.csv", next_queue)
    _write_csv(out / "v5f_pre2021_agent_execution_rules.csv", rules)
    (out / "v5f_pre2021_agent_execution_rules.md").write_text(
        "\n".join(f"- `{row['rule_id']}`: {row['detail']}" for row in rules) + "\n",
        encoding="utf-8",
    )
    (out / "v5f_pre2021_data_gate_report.md").write_text(_report(summary, feasibility, blockers), encoding="utf-8")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--probe-baostock", action="store_true")
    parser.add_argument("--baostock-timeout-sec", type=int, default=8)
    args = parser.parse_args()
    result = run_v5f_pre2021_data_availability_gate(
        args.root,
        probe_baostock=args.probe_baostock,
        baostock_timeout_sec=args.baostock_timeout_sec,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

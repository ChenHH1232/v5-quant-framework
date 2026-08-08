from __future__ import annotations

import csv
import json
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.basket_constructor_runner import construct_dividend_low_vol_fcf_basket
from v5.basket_daily_backtest_runner import run_basket_daily_backtest
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.low_volatility_factor_runner import add_low_volatility_factors
from v5.startup_preload import (
    build_startup_date_model,
    first_required_candidate_date,
    load_signal_dates,
    load_trading_days_from_price_files,
    startup_gap_days,
)


CONFIG_PATH = Path("config") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f.json"
SHADOW_CONFIG_PATH = Path("config") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f_startup_repaired_shadow.json"
OLD_SIGNALS = Path("validation_formal_v57f_etf_constructor") / "basket_rebalance_signals.csv"
OLD_BACKTEST_SUMMARY = (
    Path("local_daily_backtests_v57f_etf")
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
    / "summary.json"
)
PRELOAD_SUMMARY = Path("v5_startup_preload_repair") / "current" / "v5_startup_preload_repair_summary.json"
PRELOAD_REPORT = Path("v5_startup_preload_repair") / "current" / "v5_startup_preload_repair_report.md"
OUT_DIR = Path("v5_startup_warmup_price_repair") / "current"
RUN_DIR = OUT_DIR / "runs"
REPAIRED_PRICE_DIR = Path("\u6570\u636e\u5e93") / "processed" / "startup_preload_repaired_prices_v5"
REPAIRED_PANEL_DIR = Path("\u6570\u636e\u5e93") / "processed" / "startup_preload_repaired_panels_v5"

RECOMMENDED_WARMUP_START = "2019-01-01"
MINIMUM_WARMUP_START = "2020-04-01"
DEPLOYMENT_DATE = "2021-05-01"
END_DATE = "2026-05-31"
REQUIRED_LOOKBACK_DAYS = 252
WARMUP_BUFFER_DAYS = 20
PRICE_FIELDS = [
    "date",
    "code",
    "open",
    "close",
    "high",
    "low",
    "volume",
    "money",
    "high_limit",
    "low_limit",
    "paused",
    "price_adjustment",
    "source",
]
REPAIRED_PRICE_NAMES = {
    "bank": "bank_v3_startup_repaired_daily_prices.csv",
    "utilities_electricity": "utilities_v51f_startup_repaired_daily_prices.csv",
    "highway_infrastructure": "highway_v54h_startup_repaired_daily_prices.csv",
    "port_rail_infrastructure": "port_rail_v55j_startup_repaired_daily_prices.csv",
}
REPAIRED_PANEL_NAMES = {
    "bank": "bank_v3_repaired",
    "utilities_electricity": "utilities_v51f",
    "highway_infrastructure": "highway_v54h",
    "port_rail_infrastructure": "port_rail_v55j",
}


def run_v5_startup_warmup_price_repair(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    run_dir = root / RUN_DIR
    out.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    blockers: list[dict[str, Any]] = []
    missing_required = _missing_required_files(root)
    if missing_required:
        blockers.extend(
            {
                "blocker_id": "missing_required_file",
                "severity": "fatal",
                "path": str(path),
                "description": "Required startup warmup repair input file is missing.",
            }
            for path in missing_required
        )
        return _write_blocked_packet(root, blockers, {}, [], [], [], [], [], [])

    config = _read_json(root / CONFIG_PATH)
    old_summary = _read_json(root / OLD_BACKTEST_SUMMARY)
    deployment_date = str(config.get("portfolio", {}).get("start_date") or DEPLOYMENT_DATE)
    end_date = str(config.get("portfolio", {}).get("end_date") or END_DATE)
    required_fields = [str(item) for item in config.get("portfolio", {}).get("required_fields", [])]
    sectors = config.get("sectors", [])

    sector_universes, universe_rows = _candidate_universe_rows(root, sectors)
    price_files = [root / Path(str(sector.get("price_csv") or "")) for sector in sectors if sector.get("price_csv")]
    trading_days = load_trading_days_from_price_files(price_files)
    old_signal_dates = load_signal_dates(root / OLD_SIGNALS)
    startup_model = build_startup_date_model(
        deployment_date=deployment_date,
        trading_days=trading_days,
        regular_rebalance_dates=old_signal_dates,
    )

    requirement_rows = _warmup_requirement_rows(sectors, startup_model)
    existing_rows = _existing_price_rows(root, sectors, sector_universes, startup_model.first_tradable_date)
    source_rows, local_price_bank = _scan_local_warmup_sources(root, sector_universes, startup_model.first_tradable_date)
    existing_rows.extend(source_rows)

    usable_by_sector = _usable_local_sources(sectors, sector_universes, local_price_bank, startup_model.first_tradable_date)
    missing_sector_ids = [
        str(sector.get("sector_id") or "")
        for sector in sectors
        if str(sector.get("sector_id") or "") not in usable_by_sector
    ]
    if missing_sector_ids:
        blockers.extend(_warmup_missing_blockers(missing_sector_ids, sectors, sector_universes, local_price_bank))
        return _write_blocked_packet(
            root,
            blockers,
            config,
            requirement_rows,
            universe_rows,
            existing_rows,
            _not_generated_price_manifest(sectors),
            _not_run_low_vol_rows(sectors),
            _required_field_audit_rows(root, sectors, required_fields),
        )

    short_history_rows = _short_history_rows(sectors, sector_universes, local_price_bank, startup_model.first_tradable_date)
    repaired_price_rows = _write_repaired_prices(root, sectors, sector_universes, usable_by_sector, end_date)
    low_vol_rows = _write_repaired_low_vol_panels(
        root,
        sectors,
        repaired_price_rows,
        required_fields,
        deployment_date=deployment_date,
        first_tradable_date=startup_model.first_tradable_date,
    )
    config_manifest_rows = _write_shadow_config(root, config, repaired_price_rows, low_vol_rows)
    constructor_result = construct_dividend_low_vol_fcf_basket(
        root / SHADOW_CONFIG_PATH,
        root / RUN_DIR / "v57f_warmup_repaired_constructor",
    )
    repaired_signal_dates = load_signal_dates(constructor_result.signals_path)
    repaired_backtest_summary: dict[str, Any] = {}
    if repaired_signal_dates:
        backtest_result = run_basket_daily_backtest(
            config_path=root / SHADOW_CONFIG_PATH,
            signals_csv=constructor_result.signals_path,
            out_dir=root / RUN_DIR / "v57f_warmup_repaired_daily_backtest",
        )
        repaired_backtest_summary = _read_json(backtest_result.summary_path)

    repaired_first_signal = min(repaired_signal_dates) if repaired_signal_dates else ""
    if repaired_first_signal != startup_model.initial_rebalance_event:
        blockers.append(
            {
                "blocker_id": "repaired_initial_signal_not_generated",
                "severity": "fatal",
                "sector_id": "",
                "description": "Repaired prices existed, but the constructor did not generate the deployment first-tradable initial signal. This may require initial snapshot support or PIT field repair.",
            }
        )

    pre_post_rows = _signal_comparison_rows(
        deployment_date=deployment_date,
        old_signal_dates=old_signal_dates,
        repaired_signal_dates=repaired_signal_dates,
        old_summary=old_summary,
        repaired_summary=repaired_backtest_summary,
    )
    v57f_rows = _metric_rows(old_summary, repaired_backtest_summary)
    erc_rows = _erc_rows("ready_for_repaired_overlay_audit" if not blockers else "blocked_by_startup_signal")
    v5d_rows = _v5d_rows("ready_for_initial_minute_data_gate_check" if not blockers else "blocked_by_startup_signal")
    minute_rows = _minute_rows(startup_model.first_tradable_date, not blockers)
    test_rows = _test_placeholder_rows()
    next_rows = _next_queue_rows(blockers, repaired_first_signal)
    agent_rules = _agent_rules_text()
    summary = _summary_payload(
        root=root,
        status="startup_warmup_price_repair_completed" if not blockers else "startup_warmup_price_repair_blocked",
        config=config,
        startup_model=startup_model,
        old_signal_dates=old_signal_dates,
        repaired_signal_dates=repaired_signal_dates,
        old_summary=old_summary,
        repaired_summary=repaired_backtest_summary,
        blockers=blockers,
        repaired_price_rows=repaired_price_rows,
        local_warmup_found=True,
    )

    _write_common_outputs(
        root=root,
        summary=summary,
        report=_report(summary, blockers, requirement_rows, repaired_price_rows, low_vol_rows),
        requirement_rows=requirement_rows,
        universe_rows=universe_rows,
        existing_rows=existing_rows,
        price_manifest_rows=repaired_price_rows,
        blockers=blockers + short_history_rows,
        low_vol_rows=low_vol_rows,
        required_field_rows=_required_field_audit_rows(root, sectors, required_fields),
        config_manifest_rows=config_manifest_rows,
        pre_post_rows=pre_post_rows,
        v57f_rows=v57f_rows,
        erc_rows=erc_rows,
        v5d_rows=v5d_rows,
        minute_rows=minute_rows,
        test_rows=test_rows,
        next_rows=next_rows,
        agent_rules=agent_rules,
    )
    return summary


def _missing_required_files(root: Path) -> list[Path]:
    required = [
        root / PRELOAD_SUMMARY,
        root / PRELOAD_REPORT,
        root / "v5_startup_preload_repair" / "current" / "v5_startup_data_coverage_audit.csv",
        root / "v5_startup_preload_repair" / "current" / "v5_startup_required_field_audit.csv",
        root / "v5_startup_preload_repair" / "current" / "v5_startup_blockers.csv",
        root / CONFIG_PATH,
        root / "src" / "v5" / "startup_preload.py",
        root / "src" / "v5" / "low_volatility_factor_runner.py",
        root / "src" / "v5" / "basket_constructor_runner.py",
        root / "src" / "v5" / "basket_daily_backtest_runner.py",
        root / "src" / "v5" / "v5_startup_preload_repair_runner.py",
        root / OLD_SIGNALS,
        root / OLD_BACKTEST_SUMMARY,
    ]
    return [path for path in required if not path.exists()]


def _candidate_universe_rows(root: Path, sectors: list[dict[str, Any]]) -> tuple[dict[str, set[str]], list[dict[str, Any]]]:
    universes: dict[str, set[str]] = {}
    rows: list[dict[str, Any]] = []
    for sector in sectors:
        sector_id = str(sector.get("sector_id") or "")
        panel_path = root / Path(str(sector.get("panel_csv") or ""))
        panel_rows = read_csv_rows(panel_path)
        codes = {str(row.get("code") or "") for row in panel_rows if row.get("code")}
        dates = sorted({str(row.get("trade_date") or "")[:10] for row in panel_rows if row.get("trade_date")})
        first_tradable_candidate_count = sum(1 for row in panel_rows if str(row.get("trade_date") or "")[:10] == "2021-05-06")
        latest_predeployment = max((day for day in dates if day <= DEPLOYMENT_DATE), default="")
        universes[sector_id] = codes
        rows.append(
            {
                "sector_id": sector_id,
                "strategy_id": sector.get("strategy_id", ""),
                "panel_csv": str(panel_path),
                "price_csv": str(root / Path(str(sector.get("price_csv") or ""))),
                "dividend_csv": str(root / Path(str(sector.get("dividend_csv") or ""))),
                "candidate_code_count": len(codes),
                "panel_earliest_date": dates[0] if dates else "",
                "panel_latest_date": dates[-1] if dates else "",
                "candidate_rows_on_2021_05_06": first_tradable_candidate_count,
                "latest_panel_date_on_or_before_deployment": latest_predeployment,
                "universe_basis": "full_codes_from_panel_csv_not_final_holdings",
            }
        )
    return universes, rows


def _warmup_requirement_rows(sectors: list[dict[str, Any]], startup_model: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sector in sectors:
        rows.append(
            {
                "sector_id": sector.get("sector_id", ""),
                "deployment_date": startup_model.deployment_date,
                "first_tradable_date": startup_model.first_tradable_date,
                "recommended_warmup_start_date": RECOMMENDED_WARMUP_START,
                "minimum_allowed_warmup_start_date": MINIMUM_WARMUP_START,
                "required_lookback_trading_days": REQUIRED_LOOKBACK_DAYS,
                "warmup_buffer_trading_days": WARMUP_BUFFER_DAYS,
                "required_price_purpose": "low_volatility_and_max_drawdown_startup_warmup",
                "execution_price_requirement": "post_deployment_open_close_high_low_limit_paused_still_required_for_backtest_execution",
            }
        )
    return rows


def _existing_price_rows(
    root: Path,
    sectors: list[dict[str, Any]],
    sector_universes: dict[str, set[str]],
    first_tradable_date: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sector in sectors:
        sector_id = str(sector.get("sector_id") or "")
        path = root / Path(str(sector.get("price_csv") or ""))
        rows.append(
            {
                "record_type": "configured_price_csv",
                "sector_id": sector_id,
                "source_path": str(path),
                **_price_coverage_stats(path, sector_universes.get(sector_id, set()), first_tradable_date),
            }
        )
    return rows


def _scan_local_warmup_sources(
    root: Path,
    sector_universes: dict[str, set[str]],
    first_tradable_date: str,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, dict[str, dict[str, str]]]]]:
    all_codes: set[str] = set()
    for codes in sector_universes.values():
        all_codes |= codes
    source_rows: list[dict[str, Any]] = []
    price_bank: dict[str, dict[str, dict[str, dict[str, str]]]] = defaultdict(lambda: defaultdict(dict))
    for path in _candidate_csv_paths(root):
        try:
            fields = _csv_fieldnames(path)
        except Exception:
            continue
        date_field = _first_existing(fields, ["date", "trade_date"])
        if not date_field or "code" not in fields or "close" not in fields:
            continue
        source_type = "daily_price_schema" if {"open", "high", "low"}.issubset(set(fields)) else "panel_snapshot_or_close_only"
        code_hits: dict[str, int] = defaultdict(int)
        dates: list[str] = []
        overlap_by_sector = {sector_id: 0 for sector_id in sector_universes}
        local_rows = read_csv_rows(path)
        codes_in_file = {str(row.get("code") or "") for row in local_rows if row.get("code")}
        for sector_id, sector_codes in sector_universes.items():
            overlap_by_sector[sector_id] = len(codes_in_file & sector_codes)
        if not any(overlap_by_sector.values()):
            continue
        for row in local_rows:
            code = str(row.get("code") or "")
            day = str(row.get(date_field) or "")[:10]
            if not day:
                continue
            dates.append(day)
            if code not in all_codes or day < RECOMMENDED_WARMUP_START:
                continue
            if _positive(row.get("close")):
                if source_type == "daily_price_schema":
                    if day < first_tradable_date:
                        code_hits[code] += 1
                    price_bank[code][day] = _standard_price_row(row, path, date_field)
        if not dates or min(dates) >= first_tradable_date:
            continue
        row = {
            "record_type": "local_candidate_source",
            "sector_id": "multi_or_external",
            "source_path": str(path),
            "source_type": source_type,
            "earliest_date": min(dates),
            "latest_date": max(dates),
            "code_count": len(codes_in_file),
            "overlap_total_candidate_codes": len(codes_in_file & all_codes),
            "overlap_bank": overlap_by_sector.get("bank", 0),
            "overlap_utilities_electricity": overlap_by_sector.get("utilities_electricity", 0),
            "overlap_highway_infrastructure": overlap_by_sector.get("highway_infrastructure", 0),
            "overlap_port_rail_infrastructure": overlap_by_sector.get("port_rail_infrastructure", 0),
            "codes_with_252_predeployment_close_rows": sum(1 for count in code_hits.values() if count >= REQUIRED_LOOKBACK_DAYS),
            "usable_for_full_warmup_repair": "yes" if source_type == "daily_price_schema" and any(count >= REQUIRED_LOOKBACK_DAYS for count in code_hits.values()) else "no",
            "schema_fields": ";".join(fields),
        }
        source_rows.append(row)
    return source_rows, dict(price_bank)


def _candidate_csv_paths(root: Path) -> list[Path]:
    excluded = {
        ".git",
        ".pytest_cache",
        "__pycache__",
        "v5d_baostock_5min_data_gate",
        "data_raw",
        "data_standardized",
    }
    result: list[Path] = []
    for path in root.rglob("*.csv"):
        parts = set(path.parts)
        if parts & excluded:
            continue
        result.append(path)
    return result


def _csv_fieldnames(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or [])


def _usable_local_sources(
    sectors: list[dict[str, Any]],
    sector_universes: dict[str, set[str]],
    price_bank: dict[str, dict[str, dict[str, str]]],
    first_tradable_date: str,
) -> dict[str, dict[str, list[dict[str, str]]]]:
    usable: dict[str, dict[str, list[dict[str, str]]]] = {}
    for sector in sectors:
        sector_id = str(sector.get("sector_id") or "")
        sector_codes = sector_universes.get(sector_id, set())
        if not sector_codes:
            continue
        per_code_rows: dict[str, list[dict[str, str]]] = {}
        codes_with_required_predeployment_history = 0
        for code in sector_codes:
            pre_rows = [
                row
                for day, row in sorted(price_bank.get(code, {}).items())
                if RECOMMENDED_WARMUP_START <= day < first_tradable_date and _positive(row.get("close"))
            ]
            if len(pre_rows) >= REQUIRED_LOOKBACK_DAYS:
                codes_with_required_predeployment_history += 1
            rows = [
                row
                for day, row in sorted(price_bank.get(code, {}).items())
                if RECOMMENDED_WARMUP_START <= day <= END_DATE and _positive(row.get("close"))
            ]
            if rows:
                per_code_rows[code] = rows
        if set(per_code_rows) == sector_codes and codes_with_required_predeployment_history > 0:
            usable[sector_id] = per_code_rows
    return usable


def _short_history_rows(
    sectors: list[dict[str, Any]],
    sector_universes: dict[str, set[str]],
    price_bank: dict[str, dict[str, dict[str, str]]],
    first_tradable_date: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sector in sectors:
        sector_id = str(sector.get("sector_id") or "")
        for code in sorted(sector_universes.get(sector_id, set())):
            pre_days = [
                day
                for day, row in price_bank.get(code, {}).items()
                if RECOMMENDED_WARMUP_START <= day < first_tradable_date and _positive(row.get("close"))
            ]
            if len(pre_days) >= REQUIRED_LOOKBACK_DAYS:
                continue
            all_days = sorted(price_bank.get(code, {}))
            rows.append(
                {
                    "blocker_id": "short_predeployment_history_for_candidate_code",
                    "severity": "warning",
                    "sector_id": sector_id,
                    "candidate_code_count": "",
                    "codes_with_any_local_predeployment_daily_price": 1 if pre_days else 0,
                    "codes_with_252_local_predeployment_daily_price": 0,
                    "configured_price_csv": sector.get("price_csv", ""),
                    "code": code,
                    "predeployment_close_count": len(pre_days),
                    "first_local_price_date": all_days[0] if all_days else "",
                    "last_predeployment_price_date": max(pre_days) if pre_days else "",
                    "description": "Candidate has fewer than 252 pre-deployment close observations. It is not silently filled; low-vol required fields remain unavailable until enough PIT price history exists.",
                }
            )
    return rows


def _warmup_missing_blockers(
    missing_sector_ids: list[str],
    sectors: list[dict[str, Any]],
    sector_universes: dict[str, set[str]],
    price_bank: dict[str, dict[str, dict[str, str]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    sector_by_id = {str(sector.get("sector_id") or ""): sector for sector in sectors}
    for sector_id in missing_sector_ids:
        sector_codes = sector_universes.get(sector_id, set())
        codes_with_any = [code for code in sector_codes if price_bank.get(code)]
        codes_with_252 = [
            code
            for code in sector_codes
            if sum(1 for day, row in price_bank.get(code, {}).items() if RECOMMENDED_WARMUP_START <= day < "2021-05-06" and _positive(row.get("close"))) >= REQUIRED_LOOKBACK_DAYS
        ]
        rows.append(
            {
                "blocker_id": "local_predeployment_warmup_daily_prices_not_found",
                "severity": "fatal",
                "sector_id": sector_id,
                "candidate_code_count": len(sector_codes),
                "codes_with_any_local_predeployment_daily_price": len(codes_with_any),
                "codes_with_252_local_predeployment_daily_price": len(codes_with_252),
                "configured_price_csv": str(sector_by_id.get(sector_id, {}).get("price_csv", "")),
                "description": "No local daily price source covers the full sleeve candidate universe with at least 252 pre-deployment close observations. Network/API fetch authorization is required before repair can proceed.",
            }
        )
    rows.append(
        {
            "blocker_id": "external_data_authorization_required",
            "severity": "fatal",
            "sector_id": "all_core_sleeves",
            "candidate_code_count": sum(len(codes) for codes in sector_universes.values()),
            "codes_with_any_local_predeployment_daily_price": "",
            "codes_with_252_local_predeployment_daily_price": "",
            "configured_price_csv": "",
            "description": "JoinQuant/BaoStock/Tushare or a user-provided local daily price export is required. This runner did not call any external API.",
        }
    )
    return rows


def _write_repaired_prices(
    root: Path,
    sectors: list[dict[str, Any]],
    sector_universes: dict[str, set[str]],
    usable_by_sector: dict[str, dict[str, list[dict[str, str]]]],
    end_date: str,
) -> list[dict[str, Any]]:
    out_dir = root / REPAIRED_PRICE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict[str, Any]] = []
    for sector in sectors:
        sector_id = str(sector.get("sector_id") or "")
        original_path = root / Path(str(sector.get("price_csv") or ""))
        repaired_path = out_dir / REPAIRED_PRICE_NAMES.get(sector_id, f"{sector_id}_startup_repaired_daily_prices.csv")
        rows_by_key: dict[tuple[str, str], dict[str, str]] = {}
        for code_rows in usable_by_sector[sector_id].values():
            for row in code_rows:
                rows_by_key[(row["code"], row["date"])] = row
        for row in read_csv_rows(original_path):
            day = str(row.get("date") or row.get("trade_date") or "")[:10]
            code = str(row.get("code") or "")
            if code in sector_universes[sector_id] and day <= end_date:
                rows_by_key[(code, day)] = _standard_price_row(row, original_path, "date" if row.get("date") else "trade_date")
        repaired_rows = [rows_by_key[key] for key in sorted(rows_by_key, key=lambda item: (item[0], item[1]))]
        write_csv_rows(repaired_path, PRICE_FIELDS, repaired_rows)
        dates = sorted({row["date"] for row in repaired_rows if row.get("date")})
        codes = {row["code"] for row in repaired_rows if row.get("code")}
        manifest_rows.append(
            {
                "sector_id": sector_id,
                "status": "generated",
                "repaired_price_csv": str(repaired_path),
                "original_price_csv": str(original_path),
                "source": "local_predeployment_daily_prices_plus_original_configured_prices",
                "field_coverage": ";".join(PRICE_FIELDS),
                "missing_fields": "",
                "earliest_date": dates[0] if dates else "",
                "latest_date": dates[-1] if dates else "",
                "row_count": len(repaired_rows),
                "candidate_code_count": len(sector_universes[sector_id]),
                "covered_code_count": len(codes),
                "original_file_overwritten": "no",
            }
        )
    return manifest_rows


def _write_repaired_low_vol_panels(
    root: Path,
    sectors: list[dict[str, Any]],
    repaired_price_rows: list[dict[str, Any]],
    required_fields: list[str],
    *,
    deployment_date: str,
    first_tradable_date: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    price_by_sector = {str(row.get("sector_id") or ""): row for row in repaired_price_rows}
    for sector in sectors:
        sector_id = str(sector.get("sector_id") or "")
        original_panel_path = root / Path(str(sector.get("panel_csv") or ""))
        panel_path = _write_startup_snapshot_panel(
            root,
            sector,
            original_panel_path,
            deployment_date=deployment_date,
            first_tradable_date=first_tradable_date,
        )
        price_path = root / Path(str(price_by_sector[sector_id].get("repaired_price_csv") or ""))
        result = add_low_volatility_factors(
            panel_csv=panel_path,
            price_csv=price_path,
            out_dir=root / REPAIRED_PANEL_DIR,
            strategy_id=REPAIRED_PANEL_NAMES.get(sector_id, f"{sector_id}_repaired"),
        )
        panel_rows = read_csv_rows(result.panel_path)
        rows.append(
            {
                "sector_id": sector_id,
                "status": "generated",
                "original_panel_csv": str(original_panel_path),
                "startup_snapshot_panel_csv": str(panel_path),
                "repaired_panel_csv": str(result.panel_path),
                "repaired_price_csv": str(price_path),
                "windows": ";".join(str(item) for item in result.windows),
                "min_observations": 40,
                "pit_policy": "daily_closes_strictly_before_trade_date",
                "enriched_count": result.enriched_count,
                "required_fields_first_candidate_date": first_required_candidate_date(panel_rows, required_fields),
            }
        )
    return rows


def _write_startup_snapshot_panel(
    root: Path,
    sector: dict[str, Any],
    original_panel_path: Path,
    *,
    deployment_date: str,
    first_tradable_date: str,
) -> Path:
    panel_rows = read_csv_rows(original_panel_path)
    if any(str(row.get("trade_date") or "")[:10] == first_tradable_date for row in panel_rows):
        source_rows = [dict(row) for row in panel_rows]
        snapshot_source = "existing_first_tradable_panel_rows"
    else:
        latest_visible = max(
            (
                str(row.get("trade_date") or "")[:10]
                for row in panel_rows
                if str(row.get("trade_date") or "")[:10] and str(row.get("trade_date") or "")[:10] <= deployment_date
            ),
            default="",
        )
        snapshot_rows = [dict(row) for row in panel_rows if str(row.get("trade_date") or "")[:10] == latest_visible]
        source_rows = [dict(row) for row in panel_rows if str(row.get("trade_date") or "")[:10] != first_tradable_date]
        for row in snapshot_rows:
            item = dict(row)
            item["trade_date"] = first_tradable_date
            item["startup_initial_snapshot_source_trade_date"] = latest_visible
            item["startup_initial_snapshot_policy"] = "latest_pit_panel_snapshot_on_or_before_deployment_date"
            source_rows.append(item)
        snapshot_source = latest_visible
    out_dir = root / REPAIRED_PANEL_DIR / "_startup_snapshot_inputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{sector.get('sector_id', 'sector')}_startup_snapshot_panel.csv"
    fields = _merge_fields(source_rows)
    if "startup_initial_snapshot_source_trade_date" not in fields:
        fields.append("startup_initial_snapshot_source_trade_date")
    if "startup_initial_snapshot_policy" not in fields:
        fields.append("startup_initial_snapshot_policy")
    for row in source_rows:
        row.setdefault("startup_initial_snapshot_source_trade_date", snapshot_source if str(row.get("trade_date") or "")[:10] == first_tradable_date else "")
        row.setdefault("startup_initial_snapshot_policy", "existing_first_tradable_panel_rows" if str(row.get("trade_date") or "")[:10] == first_tradable_date else "")
    source_rows.sort(key=lambda row: (str(row.get("trade_date") or ""), str(row.get("code") or "")))
    write_csv_rows(out_path, fields, source_rows)
    return out_path


def _write_shadow_config(
    root: Path,
    config: dict[str, Any],
    repaired_price_rows: list[dict[str, Any]],
    low_vol_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    shadow = json.loads(json.dumps(config, ensure_ascii=False))
    price_by_sector = {str(row.get("sector_id") or ""): row for row in repaired_price_rows}
    panel_by_sector = {str(row.get("sector_id") or ""): row for row in low_vol_rows}
    manifest: list[dict[str, Any]] = []
    for sector in shadow.get("sectors", []):
        sector_id = str(sector.get("sector_id") or "")
        old_price = str(sector.get("price_csv") or "")
        old_panel = str(sector.get("panel_csv") or "")
        new_price = str(Path(price_by_sector[sector_id]["repaired_price_csv"]).as_posix())
        new_panel = str(Path(panel_by_sector[sector_id]["repaired_panel_csv"]).as_posix())
        sector["price_csv"] = new_price
        sector["panel_csv"] = new_panel
        manifest.append(
            {
                "sector_id": sector_id,
                "field": "price_csv;panel_csv",
                "old_value": f"{old_price};{old_panel}",
                "new_value": f"{new_price};{new_panel}",
                "core_logic_modified": "false",
                "original_config_overwritten": "false",
            }
        )
    governance = shadow.setdefault("governance", {})
    governance["status"] = "startup_repair_shadow_not_accepted"
    governance["not_status"] = sorted(set(governance.get("not_status", []) + ["accepted_strategy", "v57f_replacement", "live_trading_approved"]))
    governance["startup_warmup_price_repair"] = {
        "original_config": str(root / CONFIG_PATH),
        "shadow_config": str(root / SHADOW_CONFIG_PATH),
        "v57f_core_logic_modified": False,
        "purpose": "startup warmup data path repair only",
    }
    write_json_file(root / SHADOW_CONFIG_PATH, shadow)
    manifest.append(
        {
            "sector_id": "governance",
            "field": "governance.status",
            "old_value": str(config.get("governance", {}).get("status", "")),
            "new_value": "startup_repair_shadow_not_accepted",
            "core_logic_modified": "false",
            "original_config_overwritten": "false",
        }
    )
    return manifest


def _write_blocked_packet(
    root: Path,
    blockers: list[dict[str, Any]],
    config: dict[str, Any],
    requirement_rows: list[dict[str, Any]],
    universe_rows: list[dict[str, Any]],
    existing_rows: list[dict[str, Any]],
    price_manifest_rows: list[dict[str, Any]],
    low_vol_rows: list[dict[str, Any]],
    required_field_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    old_summary = _read_json(root / OLD_BACKTEST_SUMMARY) if (root / OLD_BACKTEST_SUMMARY).exists() else {}
    old_signal_dates = load_signal_dates(root / OLD_SIGNALS) if (root / OLD_SIGNALS).exists() else []
    price_files = []
    startup_model = None
    if config:
        price_files = [root / Path(str(sector.get("price_csv") or "")) for sector in config.get("sectors", []) if sector.get("price_csv")]
        startup_model = build_startup_date_model(
            deployment_date=str(config.get("portfolio", {}).get("start_date") or DEPLOYMENT_DATE),
            trading_days=load_trading_days_from_price_files(price_files),
            regular_rebalance_dates=old_signal_dates,
        )
    else:
        startup_model = build_startup_date_model(
            deployment_date=DEPLOYMENT_DATE,
            trading_days=[],
            regular_rebalance_dates=old_signal_dates,
        )
    pre_post_rows = _signal_comparison_rows(
        deployment_date=startup_model.deployment_date,
        old_signal_dates=old_signal_dates,
        repaired_signal_dates=[],
        old_summary=old_summary,
        repaired_summary={},
    )
    summary = _summary_payload(
        root=root,
        status="blocked_requires_user_authorized_warmup_daily_price_data",
        config=config,
        startup_model=startup_model,
        old_signal_dates=old_signal_dates,
        repaired_signal_dates=[],
        old_summary=old_summary,
        repaired_summary={},
        blockers=blockers,
        repaired_price_rows=[],
        local_warmup_found=False,
    )
    _write_common_outputs(
        root=root,
        summary=summary,
        report=_report(summary, blockers, requirement_rows, price_manifest_rows, low_vol_rows),
        requirement_rows=requirement_rows or _default_requirement_rows(config, startup_model),
        universe_rows=universe_rows,
        existing_rows=existing_rows,
        price_manifest_rows=price_manifest_rows,
        blockers=blockers,
        low_vol_rows=low_vol_rows,
        required_field_rows=required_field_rows,
        config_manifest_rows=_not_generated_config_manifest(),
        pre_post_rows=pre_post_rows,
        v57f_rows=_metric_rows(old_summary, {}),
        erc_rows=_erc_rows("not_rerun_blocked_by_missing_warmup_prices"),
        v5d_rows=_v5d_rows("not_rerun_blocked_by_missing_initial_signal"),
        minute_rows=_minute_rows(startup_model.first_tradable_date, False),
        test_rows=_test_placeholder_rows(),
        next_rows=_next_queue_rows(blockers, ""),
        agent_rules=_agent_rules_text(),
    )
    return summary


def _write_common_outputs(
    *,
    root: Path,
    summary: dict[str, Any],
    report: str,
    requirement_rows: list[dict[str, Any]],
    universe_rows: list[dict[str, Any]],
    existing_rows: list[dict[str, Any]],
    price_manifest_rows: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    low_vol_rows: list[dict[str, Any]],
    required_field_rows: list[dict[str, Any]],
    config_manifest_rows: list[dict[str, Any]],
    pre_post_rows: list[dict[str, Any]],
    v57f_rows: list[dict[str, Any]],
    erc_rows: list[dict[str, Any]],
    v5d_rows: list[dict[str, Any]],
    minute_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    next_rows: list[dict[str, Any]],
    agent_rules: str,
) -> None:
    out = root / OUT_DIR
    write_json_file(out / "v5_startup_warmup_price_repair_summary.json", summary)
    (out / "v5_startup_warmup_price_repair_report.md").write_text(report, encoding="utf-8")
    write_csv_rows(out / "v5_warmup_price_data_requirement.csv", _fieldnames(requirement_rows, ["sector_id"]), requirement_rows)
    write_csv_rows(out / "v5_warmup_candidate_universe_audit.csv", _fieldnames(universe_rows, ["sector_id"]), universe_rows)
    write_csv_rows(out / "v5_warmup_existing_price_coverage.csv", _fieldnames(existing_rows, ["record_type"]), existing_rows)
    write_csv_rows(out / "v5_warmup_repaired_price_manifest.csv", _fieldnames(price_manifest_rows, ["sector_id", "status"]), price_manifest_rows)
    write_csv_rows(out / "v5_warmup_missing_price_blockers.csv", _fieldnames(blockers, ["blocker_id", "severity"]), blockers)
    write_csv_rows(out / "v5_repaired_low_vol_factor_audit.csv", _fieldnames(low_vol_rows, ["sector_id", "status"]), low_vol_rows)
    write_csv_rows(out / "v5_repaired_required_field_audit.csv", _fieldnames(required_field_rows, ["sector_id"]), required_field_rows)
    write_csv_rows(out / "v5_repaired_config_change_manifest.csv", _fieldnames(config_manifest_rows, ["sector_id", "field"]), config_manifest_rows)
    write_csv_rows(out / "v5_repaired_startup_signal_comparison.csv", _fieldnames(pre_post_rows, ["strategy_or_component"]), pre_post_rows)
    write_csv_rows(out / "v5_repaired_v57f_metrics.csv", _fieldnames(v57f_rows, ["metric"]), v57f_rows)
    write_csv_rows(out / "v5_repaired_erc_metrics.csv", _fieldnames(erc_rows, ["component"]), erc_rows)
    write_csv_rows(out / "v5_repaired_v5d_execution_matrix.csv", _fieldnames(v5d_rows, ["component"]), v5d_rows)
    write_csv_rows(out / "v5_repaired_minute_data_blockers.csv", _fieldnames(minute_rows, ["required_window"]), minute_rows)
    write_csv_rows(out / "v5_startup_warmup_test_results.csv", _fieldnames(test_rows, ["test_command"]), test_rows)
    write_csv_rows(out / "v5_startup_warmup_next_agent_queue.csv", _fieldnames(next_rows, ["priority"]), next_rows)
    (out / "v5_startup_warmup_agent_execution_rules.md").write_text(agent_rules, encoding="utf-8")


def _price_coverage_stats(path: Path, candidate_codes: set[str], first_tradable_date: str) -> dict[str, Any]:
    if not path.exists():
        return {
            "exists": "no",
            "earliest_date": "",
            "latest_date": "",
            "row_count": 0,
            "code_count": 0,
            "candidate_code_count": len(candidate_codes),
            "covered_candidate_code_count": 0,
            "predeployment_row_count": 0,
            "candidate_codes_with_252_predeployment_closes": 0,
            "schema_fields": "",
        }
    rows = read_csv_rows(path)
    fields = _csv_fieldnames(path)
    dates: list[str] = []
    codes: set[str] = set()
    pre_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        day = str(row.get("date") or row.get("trade_date") or "")[:10]
        code = str(row.get("code") or "")
        if day:
            dates.append(day)
        if code:
            codes.add(code)
        if code in candidate_codes and day and RECOMMENDED_WARMUP_START <= day < first_tradable_date and _positive(row.get("close")):
            pre_counts[code] += 1
    return {
        "exists": "yes",
        "earliest_date": min(dates) if dates else "",
        "latest_date": max(dates) if dates else "",
        "row_count": len(rows),
        "code_count": len(codes),
        "candidate_code_count": len(candidate_codes),
        "covered_candidate_code_count": len(codes & candidate_codes),
        "predeployment_row_count": sum(pre_counts.values()),
        "candidate_codes_with_252_predeployment_closes": sum(1 for count in pre_counts.values() if count >= REQUIRED_LOOKBACK_DAYS),
        "schema_fields": ";".join(fields),
    }


def _standard_price_row(row: dict[str, Any], source_path: Path, date_field: str) -> dict[str, str]:
    result = {
        "date": str(row.get(date_field) or "")[:10],
        "code": str(row.get("code") or ""),
        "open": str(row.get("open") or ""),
        "close": str(row.get("close") or ""),
        "high": str(row.get("high") or ""),
        "low": str(row.get("low") or ""),
        "volume": str(row.get("volume") or ""),
        "money": str(row.get("money") or row.get("amount") or ""),
        "high_limit": str(row.get("high_limit") or ""),
        "low_limit": str(row.get("low_limit") or ""),
        "paused": str(row.get("paused") or ""),
        "price_adjustment": str(row.get("price_adjustment") or "raw_unadjusted_if_joinquant_real_price_source"),
        "source": str(row.get("source") or source_path),
    }
    return result


def _not_generated_price_manifest(sectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "sector_id": sector.get("sector_id", ""),
            "status": "not_generated_missing_local_warmup_daily_prices",
            "repaired_price_csv": "",
            "original_price_csv": sector.get("price_csv", ""),
            "source": "",
            "field_coverage": "",
            "missing_fields": "warmup_daily_ohlcv_limit_paused",
            "earliest_date": "",
            "latest_date": "",
            "row_count": 0,
            "candidate_code_count": "",
            "covered_code_count": 0,
            "original_file_overwritten": "no",
        }
        for sector in sectors
    ]


def _not_run_low_vol_rows(sectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "sector_id": sector.get("sector_id", ""),
            "status": "not_run_missing_repaired_price_file",
            "original_panel_csv": sector.get("panel_csv", ""),
            "repaired_panel_csv": "",
            "repaired_price_csv": "",
            "windows": "60;120;252",
            "min_observations": 40,
            "pit_policy": "daily_closes_strictly_before_trade_date",
            "enriched_count": 0,
            "required_fields_first_candidate_date": "",
        }
        for sector in sectors
    ]


def _required_field_audit_rows(root: Path, sectors: list[dict[str, Any]], required_fields: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sector in sectors:
        panel_path = root / Path(str(sector.get("panel_csv") or ""))
        panel_rows = read_csv_rows(panel_path) if panel_path.exists() else []
        dates = sorted({str(row.get("trade_date") or "")[:10] for row in panel_rows if row.get("trade_date")})
        first_date = first_required_candidate_date(panel_rows, required_fields) if panel_rows else ""
        for day in ["2021-05-06", "2021-07-01", "2021-10-08"]:
            day_rows = [row for row in panel_rows if str(row.get("trade_date") or "")[:10] == day]
            rows.append(
                {
                    "sector_id": sector.get("sector_id", ""),
                    "panel_csv": str(panel_path),
                    "audit_date": day,
                    "candidate_rows": len(day_rows),
                    "missing_low_vol_score": sum(1 for row in day_rows if row.get("low_vol_score") in (None, "")),
                    "missing_volatility_120d": sum(1 for row in day_rows if row.get("volatility_120d") in (None, "")),
                    "missing_max_drawdown_120d": sum(1 for row in day_rows if row.get("max_drawdown_120d") in (None, "")),
                    "missing_dividend_yield": sum(1 for row in day_rows if row.get("dividend_yield") in (None, "")),
                    "current_required_fields_first_candidate_date": first_date,
                    "panel_earliest_date": dates[0] if dates else "",
                    "panel_latest_date": dates[-1] if dates else "",
                }
            )
    return rows


def _not_generated_config_manifest() -> list[dict[str, Any]]:
    return [
        {
            "sector_id": "all_core_sleeves",
            "field": "price_csv;panel_csv",
            "old_value": "original_v57f_config_paths",
            "new_value": "",
            "core_logic_modified": "false",
            "original_config_overwritten": "false",
            "status": "shadow_config_not_generated_missing_warmup_prices",
        }
    ]


def _default_requirement_rows(config: dict[str, Any], startup_model: Any) -> list[dict[str, Any]]:
    return _warmup_requirement_rows(config.get("sectors", []), startup_model) if config else []


def _signal_comparison_rows(
    *,
    deployment_date: str,
    old_signal_dates: list[str],
    repaired_signal_dates: list[str],
    old_summary: dict[str, Any],
    repaired_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    old_health = old_summary.get("rebalance_order_health", {})
    repaired_health = repaired_summary.get("rebalance_order_health", {})
    old_first_signal = min(old_signal_dates) if old_signal_dates else ""
    repaired_first_signal = min(repaired_signal_dates) if repaired_signal_dates else old_first_signal
    return [
        {
            "strategy_or_component": "v57f_startup_warmup_price_repair_shadow",
            "old_first_signal_date": old_first_signal,
            "repaired_first_signal_date": repaired_first_signal,
            "old_first_trade_date": old_health.get("first_executed_order_date", ""),
            "repaired_first_trade_date": repaired_health.get("first_executed_order_date", old_health.get("first_executed_order_date", "")),
            "old_first_position_date": old_health.get("first_position_date", ""),
            "repaired_first_position_date": repaired_health.get("first_position_date", old_health.get("first_position_date", "")),
            "startup_gap_days_old": startup_gap_days(deployment_date, old_first_signal),
            "startup_gap_days_repaired": startup_gap_days(deployment_date, repaired_first_signal),
            "v57f_core_logic_modified": False,
            "note": "repaired startup signal generated from shadow config" if repaired_summary else "repaired values remain old values when warmup repair is blocked before constructor rerun",
        }
    ]


def _metric_rows(old_summary: dict[str, Any], repaired_summary: dict[str, Any]) -> list[dict[str, Any]]:
    old_metrics = old_summary.get("metrics", {})
    repaired_metrics = repaired_summary.get("metrics", {})
    rows = [
        {
            "metric": key,
            "old_value": old_metrics.get(key, ""),
            "repaired_value": repaired_metrics.get(key, ""),
            "status": "not_rerun" if not repaired_summary else "rerun",
        }
        for key in ["strategy_return", "annualized_return", "benchmark_return", "excess_return", "max_drawdown", "sharpe", "strategy_volatility", "information_ratio"]
    ]
    rows.append(
        {
            "metric": "trade_count",
            "old_value": old_summary.get("trade_count", ""),
            "repaired_value": repaired_summary.get("trade_count", ""),
            "status": "not_rerun" if not repaired_summary else "rerun",
        }
    )
    return rows


def _erc_rows(status: str) -> list[dict[str, Any]]:
    return [
        {
            "component": "erc_fixed_rule_risk_budget_overlay",
            "status": status,
            "rerun_result": "not_rerun_in_blocked_packet" if "blocked" in status else "pending_engineering_audit",
            "accepted": "no",
            "v57f_replacement": "no",
            "note": "ERC must derive from repaired V57f baseline and must not use future sleeve returns.",
        }
    ]


def _v5d_rows(status: str) -> list[dict[str, Any]]:
    return [
        {
            "component": component,
            "status": status,
            "rerun_result": "not_rerun_in_blocked_packet" if "blocked" in status else "pending_initial_minute_data_gate",
            "t_violation_count": 0,
            "accepted": "no",
            "note": "V5d candidates need repaired initial signal schedule before execution rerun.",
        }
        for component in ["l2_size_aware", "l3_default_exception", "l3_1_open_delay_price_band_fallback", "l4_exception_governed_completion"]
    ]


def _minute_rows(first_tradable_date: str, ready: bool) -> list[dict[str, Any]]:
    return [
        {
            "required_window": "initial_rebalance_D0_D1_D2",
            "first_tradable_date": first_tradable_date,
            "status": "needs_data_gate_check" if ready else "blocked_until_repaired_initial_signal_exists",
            "network_fetch_required": "unknown_until_signal_exists",
            "note": "No missing minute data is fabricated. BaoStock or other fetch requires user authorization when needed.",
        }
    ]


def _test_placeholder_rows() -> list[dict[str, Any]]:
    return [
        {"test_command": "python -m unittest tests.test_low_volatility_factor_runner", "status": "pending_run", "note": ""},
        {"test_command": "python -m unittest tests.test_basket_constructor_runner", "status": "pending_run", "note": ""},
        {"test_command": "python -m unittest tests.test_basket_daily_backtest_runner", "status": "pending_run", "note": ""},
        {"test_command": "python -m unittest tests.test_v57f_execution_robustness_runner", "status": "pending_run", "note": ""},
        {"test_command": "python -m unittest discover -s tests", "status": "pending_run", "note": ""},
    ]


def _next_queue_rows(blockers: list[dict[str, Any]], repaired_first_signal: str) -> list[dict[str, Any]]:
    if blockers:
        return [
            {
                "priority": 1,
                "next_action": "provide_or_authorize_predeployment_daily_warmup_price_data",
                "status": "blocked_requires_user_authorization",
                "scope": "V57f full core sleeve candidate universes, recommended 2019-01-01 to 2021-05-05, raw daily prices",
            },
            {
                "priority": 2,
                "next_action": "rerun_startup_warmup_price_repair",
                "status": "pending_data",
                "scope": "generate repaired price files, low-vol panels, shadow config, constructor and backtest",
            },
            {
                "priority": 3,
                "next_action": "start_v5e",
                "status": "not_allowed",
                "scope": "wait until startup warmup blocker is resolved",
            },
        ]
    return [
        {
            "priority": 1,
            "next_action": "pm_review_repaired_startup_signal",
            "status": "ready",
            "scope": f"repaired first signal {repaired_first_signal}",
        },
        {
            "priority": 2,
            "next_action": "rerun_erc_l2_l3_l4_on_repaired_schedule",
            "status": "ready",
            "scope": "candidates remain not accepted",
        },
        {
            "priority": 3,
            "next_action": "start_v5e",
            "status": "allowed_after_pm_gate",
            "scope": "only after startup repair package review",
        },
    ]


def _summary_payload(
    *,
    root: Path,
    status: str,
    config: dict[str, Any],
    startup_model: Any,
    old_signal_dates: list[str],
    repaired_signal_dates: list[str],
    old_summary: dict[str, Any],
    repaired_summary: dict[str, Any],
    blockers: list[dict[str, Any]],
    repaired_price_rows: list[dict[str, Any]],
    local_warmup_found: bool,
) -> dict[str, Any]:
    old_health = old_summary.get("rebalance_order_health", {})
    repaired_health = repaired_summary.get("rebalance_order_health", {})
    old_first_signal = min(old_signal_dates) if old_signal_dates else ""
    repaired_first_signal = min(repaired_signal_dates) if repaired_signal_dates else old_first_signal
    return {
        "schema_version": 1,
        "project": "v5_startup_warmup_price_repair",
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "deployment_model": {
            "deployment_date": startup_model.deployment_date,
            "first_tradable_date": startup_model.first_tradable_date,
            "warmup_start_date_recommended": RECOMMENDED_WARMUP_START,
            "warmup_start_date_minimum": MINIMUM_WARMUP_START,
            "trade_start_date": startup_model.trade_start_date,
            "initial_rebalance_event": startup_model.initial_rebalance_event,
        },
        "local_warmup_data_found": local_warmup_found,
        "repaired_price_files_generated": bool(repaired_price_rows),
        "original_v57f_config_modified": False,
        "v57f_core_logic_modified": False,
        "joinquant_started": _startup_warmup_joinquant_files_present(root),
        "baostock_started": False,
        "tushare_started": False,
        "v5e_started": False,
        "accepted_strategy_marked": False,
        "pre_post": {
            "old_first_signal_date": old_first_signal,
            "repaired_first_signal_date": repaired_first_signal,
            "old_first_trade_date": old_health.get("first_executed_order_date", ""),
            "repaired_first_trade_date": repaired_health.get("first_executed_order_date", old_health.get("first_executed_order_date", "")),
            "old_first_position_date": old_health.get("first_position_date", ""),
            "repaired_first_position_date": repaired_health.get("first_position_date", old_health.get("first_position_date", "")),
            "startup_gap_days_old": startup_gap_days(startup_model.deployment_date, old_first_signal),
            "startup_gap_days_repaired": startup_gap_days(startup_model.deployment_date, repaired_first_signal),
        },
        "blocker_count": len(blockers),
        "primary_blocker": blockers[0]["blocker_id"] if blockers else "",
        "erc_l2_l3_l4_rerun_status": "not_rerun_blocked_by_missing_warmup_prices" if blockers else "ready_or_completed",
        "next_gate": "provide_or_authorize_warmup_daily_price_data" if blockers else "pm_review_startup_repair_then_v5e_allowed",
        "outputs": {
            "summary": str(OUT_DIR / "v5_startup_warmup_price_repair_summary.json"),
            "report": str(OUT_DIR / "v5_startup_warmup_price_repair_report.md"),
            "blockers": str(OUT_DIR / "v5_warmup_missing_price_blockers.csv"),
            "repaired_price_manifest": str(OUT_DIR / "v5_warmup_repaired_price_manifest.csv"),
            "shadow_config": str(SHADOW_CONFIG_PATH),
        },
    }


def _report(
    summary: dict[str, Any],
    blockers: list[dict[str, Any]],
    requirement_rows: list[dict[str, Any]],
    price_manifest_rows: list[dict[str, Any]],
    low_vol_rows: list[dict[str, Any]],
) -> str:
    pp = summary.get("pre_post", {})
    lines = [
        "# V5 Startup Warmup Price Repair",
        "",
        f"- Status: `{summary.get('status')}`",
        f"- Local warmup data found: `{summary.get('local_warmup_data_found')}`",
        f"- Repaired price files generated: `{summary.get('repaired_price_files_generated')}`",
        f"- V57f core logic modified: `{summary.get('v57f_core_logic_modified')}`",
        f"- External warmup data source used: `JoinQuant={summary.get('joinquant_started')}`, `BaoStock={summary.get('baostock_started')}`, `Tushare={summary.get('tushare_started')}`",
        "",
        "## Startup Dates",
        "",
        f"- Deployment date: `{summary['deployment_model']['deployment_date']}`",
        f"- First tradable date: `{summary['deployment_model']['first_tradable_date']}`",
        f"- Recommended warmup start: `{summary['deployment_model']['warmup_start_date_recommended']}`",
        f"- Minimum allowed warmup start: `{summary['deployment_model']['warmup_start_date_minimum']}`",
        "",
        "## Pre/Post",
        "",
        "| Item | Old | Repaired |",
        "| --- | ---: | ---: |",
        f"| First signal | `{pp.get('old_first_signal_date')}` | `{pp.get('repaired_first_signal_date')}` |",
        f"| First trade | `{pp.get('old_first_trade_date')}` | `{pp.get('repaired_first_trade_date')}` |",
        f"| First position | `{pp.get('old_first_position_date')}` | `{pp.get('repaired_first_position_date')}` |",
        f"| Startup gap days | `{pp.get('startup_gap_days_old')}` | `{pp.get('startup_gap_days_repaired')}` |",
        "",
        "## Requirements",
        "",
    ]
    for row in requirement_rows:
        lines.append(
            f"- `{row.get('sector_id')}` needs raw daily warmup prices from `{row.get('recommended_warmup_start_date')}` through deployment eve, with at least `{row.get('required_lookback_trading_days')}` prior closes plus buffer."
        )
    lines.extend(["", "## Repaired Data", ""])
    for row in price_manifest_rows:
        lines.append(f"- `{row.get('sector_id')}`: `{row.get('status')}`, rows `{row.get('row_count')}`")
    lines.extend(["", "## Low-Vol Recalc", ""])
    for row in low_vol_rows:
        lines.append(f"- `{row.get('sector_id')}`: `{row.get('status')}`")
    lines.extend(["", "## Blockers", ""])
    if blockers:
        for blocker in blockers:
            lines.append(f"- `{blocker.get('blocker_id')}` / `{blocker.get('sector_id')}`: {blocker.get('description')}")
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Governance",
            "",
            "No original V57f core config or investment logic is modified. The repair is data-gate and startup deployment engineering only. ERC, L2, L3 and L4 remain candidates, not accepted strategies and not V57f replacements.",
            "",
        ]
    )
    return "\n".join(lines)


def _first_existing(fields: list[str], names: list[str]) -> str:
    for name in names:
        if name in fields:
            return name
    return ""


def _positive(value: Any) -> bool:
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _fieldnames(rows: list[dict[str, Any]], fallback: list[str]) -> list[str]:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    return fields or fallback


def _startup_warmup_joinquant_files_present(root: Path) -> bool:
    processed = root / Path("\u6570\u636e\u5e93") / "processed"
    return any(processed.glob("startup_warmup_*_joinquant_real_daily_prices.csv")) if processed.exists() else False


def _merge_fields(rows: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    return fields


def _agent_rules_text() -> str:
    return "\n".join(
        [
            "# V5 Startup Warmup Agent Execution Rules",
            "",
            "- Do not modify the original frozen V57f config.",
            "- Do not modify V57f sleeves, factors, weights, caps, target count, or rebalance frequency.",
            "- Use only pre-deployment PIT-visible warmup data for deployment-day factors.",
            "- Do not fabricate missing high_limit, low_limit, paused, or minute bars.",
            "- Do not start JoinQuant, BaoStock, Tushare, or other external data pulls without explicit user authorization.",
            "- Do not mark ERC, L2, L3, L4, or the startup shadow config as accepted.",
            "- Do not start V5e until the startup warmup blocker is resolved and reviewed.",
            "",
        ]
    )


if __name__ == "__main__":
    print(json.dumps(run_v5_startup_warmup_price_repair(Path(".")), ensure_ascii=False, indent=2))

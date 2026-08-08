from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd


OUT_DIR = Path("v5h_market_cap_pit_segmentation_gate") / "current"
SEGMENTED_DIR = Path("v5h_segmented_1min_execution_diagnostic") / "current"
ROUGH_DIR = Path("v5f_structural_rough_screen") / "current"

ORDER_PANEL = SEGMENTED_DIR / "v5h_segmented_execution_order_panel.csv"
SEGMENTED_SUMMARY = SEGMENTED_DIR / "v5h_segmented_execution_summary.json"
DAILY_RETURNS = ROUGH_DIR / "v5f_structural_rough_screen_daily_returns.csv"

FORMAL_BACKTEST_START = "2021-05-01"
FORMAL_BACKTEST_END = "2026-05-31"
REPAIRED_BASELINE = "v57f_startup_preload_repaired_baseline"
V5F_PRIMARY = "internal_subsleeve_mom12_70_30"
GLOBAL_V1 = "v5h_spec_v1_global_reference"

TOTAL_CAP_PANEL = "total_market_cap_pit_panel"
FREE_FLOAT_PANEL = "free_float_market_cap_pit_panel"

DIRECT_PANEL_SOURCES = {
    "highway_infrastructure": Path("processed") / "startup_preload_repaired_panels_v5" / "highway_v54h" / "panel_with_low_vol.csv",
    "port_rail_infrastructure": Path("processed") / "startup_preload_repaired_panels_v5" / "port_rail_v55j" / "panel_with_low_vol.csv",
    "utilities_electricity": Path("processed") / "startup_preload_repaired_panels_v5" / "utilities_v51f" / "panel_with_low_vol.csv",
}

BANK_PANEL = Path("processed") / "startup_preload_repaired_panels_v5" / "bank_v3_repaired" / "panel_with_low_vol.csv"
PRICE_SOURCES = {
    "bank": Path("processed") / "startup_preload_repaired_prices_v5" / "bank_v3_startup_repaired_daily_prices.csv",
    "highway_infrastructure": Path("processed") / "startup_preload_repaired_prices_v5" / "highway_v54h_startup_repaired_daily_prices.csv",
    "port_rail_infrastructure": Path("processed") / "startup_preload_repaired_prices_v5" / "port_rail_v55j_startup_repaired_daily_prices.csv",
    "utilities_electricity": Path("processed") / "startup_preload_repaired_prices_v5" / "utilities_v51f_startup_repaired_daily_prices.csv",
}
DIVIDEND_SOURCES = {
    "bank": Path("raw") / "dividends" / "bank_v3_joinquant_dividends_raw.csv",
    "highway_infrastructure": Path("raw") / "dividends" / "highway_v54h_joinquant_dividends_raw.csv",
    "port_rail_infrastructure": Path("raw") / "dividends" / "port_rail_v55c_joinquant_dividends_raw.csv",
    "utilities_electricity": Path("raw") / "dividends" / "utilities_joinquant_dividends_raw.csv",
}
V4_BANK_VALUATION_ROOT = Path("D:/hh/codex/v4/phase_1_fundamental/raw_downloads/all_banks")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5h_market_cap_pit_segmentation_gate(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        summary = _summary("blocked_missing_required_input", "market_cap_segmentation_blocked_by_missing_input", blockers)
        _write_json(out / "v5h_market_cap_pit_segmentation_summary.json", summary)
        _write_csv(out / "v5h_market_cap_pit_segmentation_blockers.csv", blockers)
        return summary

    db = _find_v5_database(root)
    segmented_summary = _read_json(root / SEGMENTED_SUMMARY)
    order_panel = _read_csv(root / ORDER_PANEL)
    daily = pd.read_csv(root / DAILY_RETURNS, dtype={"trade_date": str, "version_id": str, "active_rebalance_date": str})

    source_audit, direct_caps, price_lookup, capital_lookup = _load_market_cap_sources(root, db)
    cap_panel = _market_cap_panel(order_panel, direct_caps, price_lookup, capital_lookup)
    coverage = _coverage(cap_panel)
    enriched_orders = _enriched_order_panel(order_panel, cap_panel)
    size_segments = _size_segment_result(enriched_orders)
    adjustment_by_date = _adjustment_by_date(enriched_orders, _variant_specs())
    nav_rows = _build_nav_rows(daily, adjustment_by_date)
    metrics = _metrics(nav_rows)
    data_gate = _data_gate(segmented_summary, cap_panel, coverage)
    governance = _governance_audit()
    decision = _pm_decision(metrics, data_gate, governance, coverage)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(data_gate, governance)

    _write_csv(out / "v5h_market_cap_source_audit.csv", source_audit)
    _write_csv(out / "v5h_pit_market_cap_panel.csv", cap_panel)
    _write_csv(out / "v5h_market_cap_coverage_by_sleeve.csv", coverage)
    _write_csv(out / "v5h_market_cap_segmented_order_panel.csv", enriched_orders)
    _write_csv(out / "v5h_market_cap_segment_result.csv", size_segments)
    _write_csv(out / "v5h_market_cap_segmentation_adjustment_by_date.csv", adjustment_by_date)
    _write_csv(out / "v5h_market_cap_segmentation_daily_nav.csv", nav_rows)
    _write_csv(out / "v5h_market_cap_segmentation_variant_metrics.csv", metrics)
    _write_csv(out / "v5h_market_cap_segmentation_data_gate.csv", data_gate)
    _write_csv(out / "v5h_market_cap_segmentation_governance_audit.csv", governance)
    _write_csv(out / "v5h_market_cap_segmentation_pm_gate_decision.csv", decision)
    _write_csv(out / "v5h_market_cap_segmentation_next_queue.csv", next_queue)
    _write_csv(out / "v5h_market_cap_pit_segmentation_blockers.csv", blockers_out)
    (out / "v5h_market_cap_pit_segmentation_report.md").write_text(
        _report(metrics, coverage, size_segments, data_gate, decision),
        encoding="utf-8",
    )
    (out / "v5h_market_cap_pit_segmentation_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = _best_size_variant(metrics)
    global_v1 = _find(metrics, GLOBAL_V1)
    summary = _summary(
        "completed_market_cap_pit_segmentation_gate",
        decision[0]["pm_gate_decision"],
        [],
        formal_backtest_start=FORMAL_BACKTEST_START,
        formal_backtest_end=FORMAL_BACKTEST_END,
        order_count=len(order_panel),
        market_cap_panel_rows=len(cap_panel),
        market_cap_coverage_rate_pct=_coverage_rate(cap_panel, "market_cap_pit_status", "pass"),
        free_float_market_cap_coverage_rate_pct=_coverage_rate(cap_panel, "free_float_market_cap_pit_status", "pass"),
        total_market_cap_segmentation_status=decision[0]["total_market_cap_segmentation_status"],
        free_float_market_cap_segmentation_status=decision[0]["free_float_market_cap_segmentation_status"],
        best_size_variant=best.get("version_id", ""),
        best_size_variant_delta_return_pct_points_vs_v5f=round(_float(best.get("delta_return_pct_points_vs_v5f_primary")), 6),
        best_size_variant_delta_return_pct_points_vs_global_v1=round(
            (_float(best.get("strategy_return")) - _float(global_v1.get("strategy_return"))) * 100.0,
            6,
        )
        if best
        else 0.0,
    )
    _write_json(out / "v5h_market_cap_pit_segmentation_summary.json", summary)
    return summary


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    missing = []
    try:
        db = _find_v5_database(root)
    except FileNotFoundError as exc:
        missing.append(_blocker("v5_database_missing", str(exc)))
        db = None
    for path in [ORDER_PANEL, SEGMENTED_SUMMARY, DAILY_RETURNS]:
        if not (root / path).exists():
            missing.append(_blocker(f"missing_{path.name}", str(path)))
    if db is not None:
        for path in list(DIRECT_PANEL_SOURCES.values()) + [BANK_PANEL] + list(PRICE_SOURCES.values()) + list(DIVIDEND_SOURCES.values()):
            if not (db / path).exists():
                missing.append(_blocker(f"missing_{path.name}", str(db / path)))
    return missing


def _load_market_cap_sources(
    root: Path,
    db: Path,
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]], dict[tuple[str, str], dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    audit: list[dict[str, Any]] = []
    direct_caps: dict[tuple[str, str], dict[str, Any]] = {}
    price_lookup: dict[tuple[str, str], dict[str, Any]] = {}
    capital_lookup: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for sleeve, rel_path in DIRECT_PANEL_SOURCES.items():
        path = db / rel_path
        rows = _read_csv(path)
        usable = 0
        for row in rows:
            trade_date = str(row.get("trade_date", ""))
            code = str(row.get("code", ""))
            market_cap = _none_float(row.get("market_cap"))
            visible_date = str(row.get("factor_visible_date") or trade_date)
            if code and trade_date and market_cap is not None and visible_date <= trade_date:
                direct_caps[(trade_date, code)] = {
                    "market_cap_100m_cny": market_cap,
                    "market_cap_source": str(rel_path),
                    "market_cap_visible_date": visible_date,
                    "market_cap_pit_method": "direct_jq_valuation_market_cap_date_limited",
                    "market_cap_pit_status": "pass",
                }
                usable += 1
            close = _none_float(row.get("close"))
            if code and trade_date and close is not None:
                price_lookup[(trade_date, code)] = {
                    "close": close,
                    "price_source": str(rel_path),
                    "price_visible_date": trade_date,
                }
        audit.append(
            {
                "source_id": f"{sleeve}_direct_market_cap",
                "source_path": str(rel_path),
                "row_count": len(rows),
                "usable_market_cap_rows": usable,
                "pit_rule": "factor_visible_date <= trade_date and get_fundamentals(date=trade_date) source.",
                "status": "pass" if usable else "fail",
            }
        )

    valuation_root = _find_v4_bank_valuation_root(root)
    valuation_files = list(valuation_root.glob("*/daily_valuation.csv")) if valuation_root.exists() else []
    usable = 0
    for path in valuation_files:
        for row in _read_csv(path):
            trade_date = str(row.get("day", ""))
            code = str(row.get("code", ""))
            market_cap = _none_float(row.get("market_cap"))
            if code and trade_date and market_cap is not None:
                direct_caps[(trade_date, code)] = {
                    "market_cap_100m_cny": market_cap,
                    "market_cap_source": str(path),
                    "market_cap_visible_date": trade_date,
                    "market_cap_pit_method": "direct_v4_migrated_daily_valuation_market_cap",
                    "market_cap_pit_status": "pass",
                }
                usable += 1
    audit.append(
        {
            "source_id": "bank_v4_migrated_daily_valuation_market_cap",
            "source_path": str(valuation_root),
            "row_count": sum(len(_read_csv(path)) for path in valuation_files),
            "usable_market_cap_rows": usable,
            "pit_rule": "same-day daily valuation market_cap from V4 local migration; used before dividend share-capital proxy.",
            "status": "pass" if usable else "warn",
        }
    )

    bank_rows = _read_csv(db / BANK_PANEL)
    for row in bank_rows:
        trade_date = str(row.get("trade_date", ""))
        code = str(row.get("code", ""))
        close = _none_float(row.get("close"))
        if code and trade_date and close is not None:
            price_lookup[(trade_date, code)] = {
                "close": close,
                "price_source": str(BANK_PANEL),
                "price_visible_date": trade_date,
            }
    audit.append(
        {
            "source_id": "bank_repaired_close_for_cap_proxy",
            "source_path": str(BANK_PANEL),
            "row_count": len(bank_rows),
            "usable_market_cap_rows": 0,
            "pit_rule": "close is same-day repaired price input; used only with already visible share-capital records.",
            "status": "pass" if bank_rows else "fail",
        }
    )

    for sleeve, rel_path in PRICE_SOURCES.items():
        rows = _read_csv(db / rel_path)
        usable = 0
        for row in rows:
            trade_date = str(row.get("date") or row.get("trade_date") or "")
            code = str(row.get("code", ""))
            close = _none_float(row.get("close"))
            if code and trade_date and close is not None:
                price_lookup[(trade_date, code)] = {
                    "close": close,
                    "price_source": str(rel_path),
                    "price_visible_date": trade_date,
                }
                usable += 1
        audit.append(
            {
                "source_id": f"{sleeve}_startup_repaired_daily_price_for_cap_proxy",
                "source_path": str(rel_path),
                "row_count": len(rows),
                "usable_market_cap_rows": 0,
                "usable_price_rows": usable,
                "pit_rule": "same-day raw/unadjusted repaired daily close used only with already visible share-capital records.",
                "status": "pass" if usable else "fail",
            }
        )

    for sleeve, rel_path in DIVIDEND_SOURCES.items():
        rows = _read_csv(db / rel_path)
        usable_total = 0
        usable_float = 0
        for row in rows:
            code = str(row.get("code", ""))
            visible_date = _first_date(row, ["shareholders_plan_pub_date", "implementation_pub_date", "a_registration_date", "a_xr_date"])
            if not code or not visible_date:
                continue
            total_cap = _capital_for_trade_date(row, "total")
            float_cap = _capital_for_trade_date(row, "float")
            capital_lookup[code].append(
                {
                    "sleeve": sleeve,
                    "visible_date": visible_date,
                    "a_xr_date": str(row.get("a_xr_date") or ""),
                    "total_capital_10k_shares": total_cap,
                    "float_capital_10k_shares": float_cap,
                    "capital_source": str(rel_path),
                }
            )
            if total_cap is not None:
                usable_total += 1
            if float_cap is not None:
                usable_float += 1
        for code in capital_lookup:
            capital_lookup[code].sort(key=lambda item: item["visible_date"])
        audit.append(
            {
                "source_id": f"{sleeve}_share_capital_from_dividend_raw",
                "source_path": str(rel_path),
                "row_count": len(rows),
                "usable_total_capital_rows": usable_total,
                "usable_float_capital_rows": usable_float,
                "pit_rule": "latest visible dividend/share-capital row with visible_date <= trade_date.",
                "status": "pass" if usable_total else "warn",
            }
        )
    return audit, direct_caps, price_lookup, capital_lookup


def _find_v4_bank_valuation_root(root: Path) -> Path:
    candidates = [
        V4_BANK_VALUATION_ROOT,
        root.resolve().parent / "v4" / "phase_1_fundamental" / "raw_downloads" / "all_banks",
    ]
    return next((path for path in candidates if path.exists()), candidates[0])


def _market_cap_panel(
    order_panel: list[dict[str, Any]],
    direct_caps: dict[tuple[str, str], dict[str, Any]],
    price_lookup: dict[tuple[str, str], dict[str, Any]],
    capital_lookup: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows = []
    for order in order_panel:
        trade_date = str(order.get("trade_date", ""))
        code = str(order.get("code", ""))
        sleeve = str(order.get("sleeve", ""))
        key = (trade_date, code)
        direct = direct_caps.get(key)
        capital = _latest_visible_capital(capital_lookup.get(code, []), trade_date)
        price = price_lookup.get(key, {})
        close = _none_float(price.get("close"))

        market_cap = None
        cap_source = ""
        cap_visible = ""
        cap_method = ""
        cap_status = "missing"
        if direct is not None:
            market_cap = _none_float(direct.get("market_cap_100m_cny"))
            cap_source = str(direct.get("market_cap_source", ""))
            cap_visible = str(direct.get("market_cap_visible_date", ""))
            cap_method = str(direct.get("market_cap_pit_method", ""))
            cap_status = str(direct.get("market_cap_pit_status", ""))
        elif close is not None and capital and _none_float(capital.get("total_capital_10k_shares")) is not None:
            market_cap = close * _float(capital.get("total_capital_10k_shares")) / 10000.0
            cap_source = f"{price.get('price_source')} + {capital.get('capital_source')}"
            cap_visible = str(capital.get("visible_date", ""))
            cap_method = "derived_close_times_visible_total_capital_proxy"
            cap_status = "pass" if cap_visible <= trade_date else "fail"

        free_float_market_cap = None
        free_float_source = ""
        free_float_visible = ""
        free_float_method = ""
        free_float_status = "missing"
        if close is not None and capital and _none_float(capital.get("float_capital_10k_shares")) is not None:
            free_float_market_cap = close * _float(capital.get("float_capital_10k_shares")) / 10000.0
            free_float_source = f"{price.get('price_source')} + {capital.get('capital_source')}"
            free_float_visible = str(capital.get("visible_date", ""))
            free_float_method = "derived_close_times_visible_float_capital_proxy"
            free_float_status = "pass" if free_float_visible <= trade_date else "fail"

        rows.append(
            {
                "trade_date": trade_date,
                "code": code,
                "sleeve": sleeve,
                "market_cap_100m_cny": market_cap if market_cap is not None else "",
                "market_cap_source": cap_source,
                "market_cap_visible_date": cap_visible,
                "market_cap_pit_method": cap_method,
                "market_cap_pit_status": cap_status,
                "free_float_market_cap_100m_cny": free_float_market_cap if free_float_market_cap is not None else "",
                "free_float_market_cap_source": free_float_source,
                "free_float_market_cap_visible_date": free_float_visible,
                "free_float_market_cap_pit_method": free_float_method,
                "free_float_market_cap_pit_status": free_float_status,
                "price_source": price.get("price_source", ""),
                "capital_source": capital.get("capital_source", "") if capital else "",
                "diagnostic_only": True,
                "accepted": False,
            }
        )
    return rows


def _latest_visible_capital(rows: list[dict[str, Any]], trade_date: str) -> dict[str, Any]:
    visible = [row for row in rows if row.get("visible_date", "") <= trade_date]
    return visible[-1] if visible else {}


def _capital_for_trade_date(row: dict[str, Any], cap_type: str) -> float | None:
    before = _none_float(row.get(f"{cap_type}_capital_before_transfer"))
    after = _none_float(row.get(f"{cap_type}_capital_after_transfer"))
    if after is not None:
        return after
    return before


def _first_date(row: dict[str, Any], columns: list[str]) -> str:
    values = [str(row.get(col, "")).strip() for col in columns if str(row.get(col, "")).strip() not in {"", "nan", "None"}]
    return min(values) if values else ""


def _coverage(cap_panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in cap_panel:
        groups[str(row.get("sleeve", ""))].append(row)
    groups["ALL"].extend(cap_panel)
    out = []
    for sleeve, group in sorted(groups.items()):
        mcap_pass = sum(1 for row in group if row.get("market_cap_pit_status") == "pass")
        ff_pass = sum(1 for row in group if row.get("free_float_market_cap_pit_status") == "pass")
        out.append(
            {
                "sleeve": sleeve,
                "order_rows": len(group),
                "market_cap_pass_rows": mcap_pass,
                "market_cap_coverage_rate_pct": _pct(mcap_pass, len(group)),
                "free_float_market_cap_pass_rows": ff_pass,
                "free_float_market_cap_coverage_rate_pct": _pct(ff_pass, len(group)),
                "market_cap_status": "pass" if _pct(mcap_pass, len(group)) >= 95.0 else "blocked",
                "free_float_market_cap_status": "pass" if _pct(ff_pass, len(group)) >= 95.0 else "blocked",
                "accepted": False,
            }
        )
    return out


def _enriched_order_panel(order_panel: list[dict[str, Any]], cap_panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cap = {(row["trade_date"], row["code"]): row for row in cap_panel}
    rows = []
    for order in order_panel:
        item = {**order, **cap.get((order.get("trade_date", ""), order.get("code", "")), {})}
        rows.append(item)
    _assign_size_buckets(rows, "market_cap_100m_cny", "mcap_bucket_global_date", ["trade_date"])
    _assign_size_buckets(rows, "market_cap_100m_cny", "mcap_bucket_within_sleeve_date", ["trade_date", "sleeve"])
    _assign_size_buckets(rows, "free_float_market_cap_100m_cny", "free_float_mcap_bucket_within_sleeve_date", ["trade_date", "sleeve"])
    return rows


def _assign_size_buckets(rows: list[dict[str, Any]], value_col: str, bucket_col: str, group_cols: list[str]) -> None:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if _none_float(row.get(value_col)) is None:
            row[bucket_col] = "missing"
            continue
        groups[tuple(str(row.get(col, "")) for col in group_cols)].append(row)
    for group in groups.values():
        ordered = sorted(group, key=lambda row: _float(row.get(value_col)))
        n = len(ordered)
        for index, row in enumerate(ordered):
            if n < 3:
                row[bucket_col] = "insufficient_group_size"
                continue
            percentile = index / (n - 1) if n > 1 else 0.5
            if percentile < 1 / 3:
                row[bucket_col] = "small"
            elif percentile < 2 / 3:
                row[bucket_col] = "mid"
            else:
                row[bucket_col] = "large"


def _size_segment_result(enriched_orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for bucket_col in ["mcap_bucket_within_sleeve_date", "mcap_bucket_global_date", "free_float_mcap_bucket_within_sleeve_date"]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in enriched_orders:
            groups[str(row.get(bucket_col, "missing"))].append(row)
        for bucket, group in sorted(groups.items()):
            weight_sum = sum(_float(row.get("trade_delta_weight_abs")) for row in group)
            weighted = sum(_float(row.get("weighted_incremental_edge_vs_default_10am")) for row in group)
            rows.append(
                {
                    "bucket_type": bucket_col,
                    "bucket": bucket,
                    "order_count": len(group),
                    "trade_date_count": len({row.get("trade_date", "") for row in group}),
                    "execution_adjustment_total_pct_points": weighted * 100.0,
                    "weighted_avg_incremental_edge_bp": weighted / weight_sum * 10000.0 if weight_sum else 0.0,
                    "market_cap_pass_rate_pct": _pct(sum(1 for row in group if row.get("market_cap_pit_status") == "pass"), len(group)),
                    "free_float_pass_rate_pct": _pct(sum(1 for row in group if row.get("free_float_market_cap_pit_status") == "pass"), len(group)),
                    "diagnostic_only": True,
                    "accepted": False,
                }
            )
    return rows


def _variant_specs() -> list[dict[str, Any]]:
    return [
        {"version_id": GLOBAL_V1, "condition": lambda row: True, "bucket_source": "none"},
        {
            "version_id": "v5h_mcap_within_sleeve_small_only_diagnostic",
            "condition": lambda row: row.get("mcap_bucket_within_sleeve_date") == "small",
            "bucket_source": "market_cap",
        },
        {
            "version_id": "v5h_mcap_within_sleeve_mid_only_diagnostic",
            "condition": lambda row: row.get("mcap_bucket_within_sleeve_date") == "mid",
            "bucket_source": "market_cap",
        },
        {
            "version_id": "v5h_mcap_within_sleeve_large_only_diagnostic",
            "condition": lambda row: row.get("mcap_bucket_within_sleeve_date") == "large",
            "bucket_source": "market_cap",
        },
        {
            "version_id": "v5h_mcap_within_sleeve_small_or_large_diagnostic",
            "condition": lambda row: row.get("mcap_bucket_within_sleeve_date") in {"small", "large"},
            "bucket_source": "market_cap",
        },
        {
            "version_id": "v5h_free_float_mcap_within_sleeve_large_only_diagnostic",
            "condition": lambda row: row.get("free_float_mcap_bucket_within_sleeve_date") == "large",
            "bucket_source": "free_float_market_cap",
        },
    ]


def _adjustment_by_date(enriched_orders: list[dict[str, Any]], variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for spec in variants:
        condition: Callable[[dict[str, Any]], bool] = spec["condition"]
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in enriched_orders:
            if spec["bucket_source"] == "market_cap" and row.get("market_cap_pit_status") != "pass":
                continue
            if spec["bucket_source"] == "free_float_market_cap" and row.get("free_float_market_cap_pit_status") != "pass":
                continue
            if condition(row):
                groups[row["trade_date"]].append(row)
        for trade_date, group in sorted(groups.items()):
            out.append(
                {
                    "version_id": spec["version_id"],
                    "trade_date": trade_date,
                    "execution_adjustment_return": sum(_float(row.get("weighted_incremental_edge_vs_default_10am")) for row in group),
                    "order_count": len(group),
                    "bucket_source": spec["bucket_source"],
                    "accepted": False,
                }
            )
    return out


def _build_nav_rows(daily: pd.DataFrame, adjustment_by_date: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = daily[daily["version_id"].isin([REPAIRED_BASELINE, V5F_PRIMARY])].copy()
    df = df[(df["trade_date"] >= FORMAL_BACKTEST_START) & (df["trade_date"] <= FORMAL_BACKTEST_END)].copy()
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        rows.append(
            {
                "trade_date": row["trade_date"],
                "version_id": row["version_id"],
                "strategy_return": _float(row["strategy_return"]),
                "execution_adjustment_return": 0.0,
                "strategy_nav": _float(row["strategy_nav"]),
                "nav_comparable": True,
                "accepted": False,
            }
        )
    primary = df[df["version_id"].eq(V5F_PRIMARY)].copy().sort_values("trade_date")
    adj_map: dict[tuple[str, str], dict[str, Any]] = {(row["version_id"], row["trade_date"]): row for row in adjustment_by_date}
    for spec in _variant_specs():
        nav = 1.0
        for _, row in primary.iterrows():
            adj = _float(adj_map.get((spec["version_id"], row["trade_date"]), {}).get("execution_adjustment_return"))
            ret = _float(row["strategy_return"]) + adj
            nav *= 1.0 + ret
            rows.append(
                {
                    "trade_date": row["trade_date"],
                    "version_id": spec["version_id"],
                    "strategy_return": ret,
                    "execution_adjustment_return": adj,
                    "strategy_nav": nav,
                    "nav_comparable": True,
                    "accepted": False,
                }
            )
    return rows


def _metrics(nav_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(nav_rows).sort_values(["version_id", "trade_date"])
    out: list[dict[str, Any]] = []
    for version, group in df.groupby("version_id", sort=True):
        ordered = group.sort_values("trade_date")
        navs = pd.to_numeric(ordered["strategy_nav"], errors="coerce").tolist()
        rets = pd.to_numeric(ordered["strategy_return"], errors="coerce").tolist()
        ann = navs[-1] ** (252 / len(navs)) - 1.0 if navs and navs[-1] > 0 else 0.0
        vol = pd.Series(rets).std() * (252**0.5)
        out.append(
            {
                "version_id": version,
                "strategy_return": navs[-1] - 1.0 if navs else 0.0,
                "annualized_return": ann,
                "max_drawdown": _max_drawdown(navs),
                "volatility": vol,
                "sharpe_proxy": ann / vol if vol else 0.0,
                "execution_adjustment_total": pd.to_numeric(ordered["execution_adjustment_return"], errors="coerce").fillna(0.0).sum(),
                "execution_adjustment_trade_date_count": int((pd.to_numeric(ordered["execution_adjustment_return"], errors="coerce").fillna(0.0) != 0).sum()),
                "nav_comparable": bool(ordered["nav_comparable"].astype(bool).all()),
                "accepted": False,
            }
        )
    repaired = _find(out, REPAIRED_BASELINE)
    v5f = _find(out, V5F_PRIMARY)
    global_v1 = _find(out, GLOBAL_V1)
    for row in out:
        row["delta_return_pct_points_vs_repaired_baseline"] = (_float(row["strategy_return"]) - _float(repaired.get("strategy_return"))) * 100.0
        row["delta_return_pct_points_vs_v5f_primary"] = (_float(row["strategy_return"]) - _float(v5f.get("strategy_return"))) * 100.0
        row["delta_return_pct_points_vs_global_v1"] = (_float(row["strategy_return"]) - _float(global_v1.get("strategy_return"))) * 100.0
        row["delta_max_drawdown_pct_points_vs_v5f_primary"] = (_float(row["max_drawdown"]) - _float(v5f.get("max_drawdown"))) * 100.0
    order = {GLOBAL_V1: 0, V5F_PRIMARY: 98, REPAIRED_BASELINE: 99}
    return sorted(out, key=lambda row: order.get(row["version_id"], 10))


def _data_gate(segmented_summary: dict[str, Any], cap_panel: list[dict[str, Any]], coverage: list[dict[str, Any]]) -> list[dict[str, Any]]:
    all_row = next((row for row in coverage if row.get("sleeve") == "ALL"), {})
    sleeve_gaps = [
        row
        for row in coverage
        if row.get("sleeve") != "ALL" and row.get("market_cap_status") != "pass"
    ]
    return [
        {"gate_id": "segmented_source_completed", "status": "pass" if segmented_summary.get("status") == "completed_v5h_segmented_1min_execution_diagnostic" else "fail", "value": segmented_summary.get("status", "")},
        {"gate_id": "pit_market_cap_panel_built", "status": "pass" if cap_panel else "fail", "value": len(cap_panel)},
        {"gate_id": "total_market_cap_coverage", "status": "pass" if _float(all_row.get("market_cap_coverage_rate_pct")) >= 95.0 else "fail", "value": all_row.get("market_cap_coverage_rate_pct", 0)},
        {"gate_id": "total_market_cap_sleeve_completeness", "status": "warn" if sleeve_gaps else "pass", "value": ";".join(f"{row['sleeve']}={row['market_cap_coverage_rate_pct']}%" for row in sleeve_gaps)},
        {"gate_id": "free_float_market_cap_coverage", "status": "warn" if _float(all_row.get("free_float_market_cap_coverage_rate_pct")) < 95.0 else "pass", "value": all_row.get("free_float_market_cap_coverage_rate_pct", 0)},
        {"gate_id": "formal_backtest_end_preserved", "status": "pass", "value": FORMAL_BACKTEST_END},
        {"gate_id": "fixed_tercile_buckets_only", "status": "pass", "value": "small;mid;large"},
    ]


def _governance_audit() -> list[dict[str, Any]]:
    return [
        {"audit_id": "v57f_core_unchanged", "status": "pass", "detail": "Market-cap data gate and segmentation do not change V57f selection."},
        {"audit_id": "v5f_mainline_unchanged", "status": "pass", "detail": "V5f internal_subsleeve_mom12_70_30 remains unchanged."},
        {"audit_id": "buy_side_existing_orders_only", "status": "pass", "detail": "Segmentation is applied only to existing V5f champion planned buy/increase orders."},
        {"audit_id": "no_new_buy_signal", "status": "pass", "detail": "No stock can be added from market-cap buckets."},
        {"audit_id": "no_trading_frequency_increase", "status": "pass", "detail": "Only execution timing proxy on existing buy dates is compared."},
        {"audit_id": "no_threshold_scan", "status": "pass", "detail": "Only fixed within-date terciles are used."},
        {"audit_id": "free_float_not_forced", "status": "pass", "detail": "Free-float market cap is blocked where PIT source is unavailable."},
        {"audit_id": "not_accepted_not_live", "status": "pass", "detail": "No result is accepted or live approved."},
    ]


def _pm_decision(
    metrics: list[dict[str, Any]],
    data_gate: list[dict[str, Any]],
    governance: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    total_ok = next((row for row in data_gate if row["gate_id"] == "total_market_cap_coverage"), {}).get("status") == "pass"
    free_float_ok = next((row for row in data_gate if row["gate_id"] == "free_float_market_cap_coverage"), {}).get("status") == "pass"
    sleeve_complete = next((row for row in data_gate if row["gate_id"] == "total_market_cap_sleeve_completeness"), {}).get("status") == "pass"
    hard_fail = (
        any(
            row.get("status") == "fail"
            for row in data_gate + governance
            if row.get("gate_id", row.get("audit_id", "")) != "free_float_market_cap_coverage"
        )
        if data_gate
        else True
    )
    if hard_fail:
        decision = "market_cap_segmentation_blocked_by_pit_data"
        status = "blocked"
    else:
        best = _best_size_variant(metrics)
        delta_global = _float(best.get("delta_return_pct_points_vs_global_v1"))
        if total_ok and delta_global > 0:
            decision = "market_cap_segmentation_diagnostic_positive_needs_independent_validation"
            status = "diagnostic_positive"
        else:
            decision = "market_cap_segmentation_diagnostic_only_no_incremental_edge"
            status = "diagnostic_only"
    best = _best_size_variant(metrics)
    return [
        {
            "pm_gate_decision": decision,
            "status": status,
            "total_market_cap_segmentation_status": (
                "run_pit_clean_total_market_cap"
                if total_ok and sleeve_complete
                else "run_pit_clean_total_market_cap_with_sleeve_gap"
                if total_ok
                else "blocked_total_market_cap_pit_coverage"
            ),
            "free_float_market_cap_segmentation_status": "run_pit_clean_free_float_market_cap" if free_float_ok else "blocked_missing_free_float_pit_coverage",
            "best_size_variant": best.get("version_id", ""),
            "best_delta_return_pct_points_vs_global_v1": best.get("delta_return_pct_points_vs_global_v1", ""),
            "accepted": False,
            "live_trading_approved": False,
            "deployment_approved": False,
            "v57f_core_modified": False,
            "v5f_mainline_modified": False,
            "sell_rules_modified": False,
            "trading_frequency_increased": False,
            "new_buy_signal_used": False,
            "notes": "Total market-cap segmentation may run if PIT coverage passes; free-float is separately blocked when source coverage is insufficient.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "queue_id": "v5h_size_liquidity_interaction_independent_validation",
            "status": "ready_if_market_cap_positive",
            "scope": "Validate size/liquidity interaction outside the 2021-2026 discovery window before any spec.",
        },
        {
            "priority": 2,
            "queue_id": "v5h_free_float_market_cap_pit_source_repair",
            "status": "ready_if_free_float_blocked",
            "scope": "Locate PIT-clean free-float share capital source; do not infer from total market cap.",
        },
        {
            "priority": 3,
            "queue_id": "v5h_quiet_or_active_forward_observation",
            "status": "ready",
            "scope": "Continue forward observation; no mainline change.",
        },
    ]


def _report(
    metrics: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    data_gate: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    lines = [
        "# V5h PIT Market-Cap Segmentation Gate",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Total market-cap status: `{decision[0]['total_market_cap_segmentation_status']}`",
        f"- Free-float market-cap status: `{decision[0]['free_float_market_cap_segmentation_status']}`",
        "- Scope: existing V5f champion planned buy/increase order panel only.",
        "",
        "## Coverage",
    ]
    for row in coverage:
        lines.append(
            f"- `{row['sleeve']}`: market cap `{row['market_cap_coverage_rate_pct']}%`, free-float `{row['free_float_market_cap_coverage_rate_pct']}%`."
        )
    lines.extend(["", "## Variant Results"])
    for row in metrics:
        if row["version_id"] in {REPAIRED_BASELINE, V5F_PRIMARY}:
            continue
        lines.append(
            f"- `{row['version_id']}`: return `{_float(row['strategy_return']) * 100:.4f}%`, delta vs V5f `{_float(row['delta_return_pct_points_vs_v5f_primary']):+.4f}` pct, delta vs global v1 `{_float(row['delta_return_pct_points_vs_global_v1']):+.4f}` pct."
        )
    lines.extend(["", "## Segment Read"])
    for row in segments:
        if row["bucket_type"] == "mcap_bucket_within_sleeve_date":
            lines.append(
                f"- total mcap `{row['bucket']}`: n={row['order_count']}, adjustment `{_float(row['execution_adjustment_total_pct_points']):+.4f}` pct, avg `{_float(row['weighted_avg_incremental_edge_bp']):+.2f}` bp."
            )
    lines.extend(["", "## Data Gate"])
    for row in data_gate:
        lines.append(f"- `{row['gate_id']}`: `{row['status']}` ({row['value']})")
    lines.extend(["", "No V57f/V5f mainline rule is changed by this packet.", ""])
    return "\n".join(lines)


def _rules() -> str:
    return "\n".join(
        [
            "# V5h Market-Cap PIT Segmentation Rules",
            "",
            "- Build PIT-clean market-cap/free-float panel before any size segmentation.",
            "- Use total market cap only when coverage and visible-date checks pass.",
            "- Use free-float market cap only when PIT source coverage passes; do not fill from total market cap.",
            "- Do not modify V57f core or V5f mainline.",
            "- Do not create new buy signals, change sell rules, increase trading frequency, or scan thresholds.",
            "- Do not mark accepted, live approved, or deployment approved.",
            "",
        ]
    )


def _find_v5_database(root: Path) -> Path:
    for child in root.iterdir():
        if child.is_dir() and (child / "processed").exists() and (child / "raw").exists() and (child / "manifests").exists():
            return child
    raise FileNotFoundError("Could not locate V5 database directory with processed/raw/manifests children.")


def _best_size_variant(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in metrics if row.get("version_id", "").startswith("v5h_mcap_")]
    return max(eligible, key=lambda row: _float(row.get("delta_return_pct_points_vs_global_v1"))) if eligible else {}


def _coverage_rate(rows: list[dict[str, Any]], col: str, expected: str) -> float:
    return _pct(sum(1 for row in rows if row.get(col) == expected), len(rows))


def _blockers(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for group in groups:
        for row in group:
            if row.get("status") == "fail":
                rows.append(_blocker(row.get("gate_id") or row.get("audit_id") or "unknown", str(row.get("value", row.get("detail", "")))))
    return rows or [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": ""}]


def _blocker(blocker_id: str, description: str) -> dict[str, Any]:
    return {"blocker_id": blocker_id, "severity": "fatal", "status": "blocking", "description": description}


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5h_market_cap_pit_segmentation_gate",
        "status": status,
        "pm_gate_decision": decision,
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "v5f_mainline_modified": False,
        "sell_rules_modified": False,
        "trading_frequency_increased": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len([row for row in blockers if row.get("status") == "blocking"]),
        "fatal_blockers": [row for row in blockers if row.get("status") == "blocking"],
        **extra,
    }


def _max_drawdown(navs: list[float]) -> float:
    peak = 0.0
    max_dd = 0.0
    for nav in navs:
        peak = max(peak, nav)
        if peak:
            max_dd = min(max_dd, nav / peak - 1.0)
    return abs(max_dd)


def _find(rows: list[dict[str, Any]], version_id: str) -> dict[str, Any]:
    return next((row for row in rows if row.get("version_id") == version_id), {})


def _none_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        text = str(value).strip()
        if text == "" or text.lower() in {"nan", "none", "null"}:
            return None
        out = float(text)
        return out if math.isfinite(out) else None
    except Exception:
        return None


def _float(value: Any) -> float:
    parsed = _none_float(value)
    return parsed if parsed is not None else 0.0


def _pct(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100.0, 6) if denominator else 0.0


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def main() -> None:
    summary = run_v5h_market_cap_pit_segmentation_gate(Path("."))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

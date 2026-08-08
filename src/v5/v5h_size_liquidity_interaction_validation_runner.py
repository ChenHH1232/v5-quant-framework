from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd


OUT_DIR = Path("v5h_size_liquidity_interaction_independent_validation") / "current"
MCAP_DIR = Path("v5h_market_cap_pit_segmentation_gate") / "current"
QUIET_DIR = Path("v5h_quiet_or_active_independent_validation") / "current"
ROUGH_DIR = Path("v5f_structural_rough_screen") / "current"
PRE2021_DIR = Path("v5f_pre2021_multisleeve_mainline_validation") / "current"

FORMAL_ORDER_PANEL = MCAP_DIR / "v5h_market_cap_segmented_order_panel.csv"
FORMAL_MCAP_SUMMARY = MCAP_DIR / "v5h_market_cap_pit_segmentation_summary.json"
PRE2021_ORDER_PANEL = QUIET_DIR / "v5h_quiet_or_active_independent_order_panel.csv"
PRE2021_SUMMARY = QUIET_DIR / "v5h_quiet_or_active_independent_summary.json"
FORMAL_DAILY = ROUGH_DIR / "v5f_structural_rough_screen_daily_returns.csv"
PRE2021_DAILY = PRE2021_DIR / "v5f_pre2021_p1_daily_returns.csv"
PRE2021_MCAP_REPAIR_ROWS = (
    Path("v5h_pre2021_total_market_cap_source_repair")
    / "current"
    / "v5h_pre2021_total_market_cap_repaired_rows.csv"
)

V4_BANK_VALUATION_ROOT = Path("D:/hh/codex/v4/phase_1_fundamental/raw_downloads/all_banks")

FORMAL_BACKTEST_START = "2021-05-01"
FORMAL_BACKTEST_END = "2026-05-31"
AVAILABLE_PRE2021_START = "2019-04-01"
AVAILABLE_PRE2021_END = "2020-12-31"

REPAIRED_BASELINE = "v57f_startup_preload_repaired_baseline"
V5F_PRIMARY = "internal_subsleeve_mom12_70_30"
GLOBAL_V1_FORMAL = "v5h_spec_v1_global_reference"
PRE2021_BASELINE = "pre2021_repaired_multisleeve_equal_sleeve_baseline_proxy"
GLOBAL_V1_PRE2021 = "pre2021_global_pressure_positive_1000_else_1400"
PRE2021_PRIMARY_SCOPE = "pre2021_champion_increase_vs_previous"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5h_size_liquidity_interaction_validation(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        summary = _summary("blocked_missing_required_input", "blocked_missing_required_input", blockers)
        _write_json(out / "v5h_size_liquidity_interaction_summary.json", summary)
        _write_csv(out / "v5h_size_liquidity_interaction_blockers.csv", blockers)
        return summary

    formal_orders = _read_csv(root / FORMAL_ORDER_PANEL)
    formal_daily = pd.read_csv(root / FORMAL_DAILY, dtype={"trade_date": str, "version_id": str, "active_rebalance_date": str})
    formal_adjustments = _formal_adjustment_by_date(formal_orders, _formal_variants())
    formal_nav = _formal_nav(formal_daily, formal_adjustments)
    formal_metrics = _metrics(formal_nav, REPAIRED_BASELINE, V5F_PRIMARY, GLOBAL_V1_FORMAL, "formal")
    formal_segments = _interaction_segments(formal_orders, "formal_backtest")

    pre2021_orders_raw = _read_csv(root / PRE2021_ORDER_PANEL)
    pre2021_orders, pre2021_cap_audit = _attach_pre2021_market_cap(root, pre2021_orders_raw)
    pre2021_adjustments = _pre2021_adjustment_by_date(pre2021_orders, _pre2021_variants())
    pre2021_daily = pd.read_csv(root / PRE2021_DAILY, dtype={"trade_date": str, "version_id": str, "active_rebalance_date": str})
    pre2021_nav = _pre2021_nav(pre2021_daily, pre2021_adjustments)
    pre2021_metrics = _metrics(pre2021_nav, PRE2021_BASELINE, V5F_PRIMARY, GLOBAL_V1_PRE2021, "pre2021")
    pre2021_segments = _interaction_segments(
        [row for row in pre2021_orders if row.get("validation_scope") == PRE2021_PRIMARY_SCOPE],
        "pre2021_validation",
        edge_col="incremental_edge_global_v1_vs_default_10am",
        weighted_col="weighted_incremental_edge_global_v1_vs_default_10am",
    )

    data_gate = _data_gate(root, formal_orders, pre2021_orders, pre2021_cap_audit)
    governance = _governance_audit()
    decision = _pm_decision(formal_metrics, pre2021_metrics, data_gate, governance, pre2021_orders)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(data_gate, governance)

    _write_csv(out / "v5h_size_liquidity_formal_order_panel.csv", formal_orders)
    _write_csv(out / "v5h_size_liquidity_formal_interaction_segment_result.csv", formal_segments)
    _write_csv(out / "v5h_size_liquidity_formal_adjustment_by_date.csv", formal_adjustments)
    _write_csv(out / "v5h_size_liquidity_formal_daily_nav.csv", formal_nav)
    _write_csv(out / "v5h_size_liquidity_formal_variant_metrics.csv", formal_metrics)
    _write_csv(out / "v5h_size_liquidity_pre2021_order_panel.csv", pre2021_orders)
    _write_csv(out / "v5h_size_liquidity_pre2021_market_cap_source_audit.csv", pre2021_cap_audit)
    _write_csv(out / "v5h_size_liquidity_pre2021_interaction_segment_result.csv", pre2021_segments)
    _write_csv(out / "v5h_size_liquidity_pre2021_adjustment_by_date.csv", pre2021_adjustments)
    _write_csv(out / "v5h_size_liquidity_pre2021_daily_nav.csv", pre2021_nav)
    _write_csv(out / "v5h_size_liquidity_pre2021_variant_metrics.csv", pre2021_metrics)
    _write_csv(out / "v5h_size_liquidity_interaction_data_gate.csv", data_gate)
    _write_csv(out / "v5h_size_liquidity_interaction_governance_audit.csv", governance)
    _write_csv(out / "v5h_size_liquidity_interaction_pm_gate_decision.csv", decision)
    _write_csv(out / "v5h_size_liquidity_interaction_next_queue.csv", next_queue)
    _write_csv(out / "v5h_size_liquidity_interaction_blockers.csv", blockers_out)
    (out / "v5h_size_liquidity_interaction_report.md").write_text(
        _report(formal_metrics, pre2021_metrics, formal_segments, pre2021_segments, data_gate, decision),
        encoding="utf-8",
    )
    (out / "v5h_size_liquidity_interaction_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best_formal = _best_interaction(formal_metrics)
    best_pre = _best_interaction(pre2021_metrics)
    summary = _summary(
        "completed_size_liquidity_interaction_validation",
        decision[0]["pm_gate_decision"],
        [],
        formal_backtest_start=FORMAL_BACKTEST_START,
        formal_backtest_end=FORMAL_BACKTEST_END,
        pre2021_validation_start=AVAILABLE_PRE2021_START,
        pre2021_validation_end=AVAILABLE_PRE2021_END,
        formal_order_count=len(formal_orders),
        pre2021_order_count=len(pre2021_orders),
        pre2021_primary_order_count=sum(1 for row in pre2021_orders if row.get("validation_scope") == PRE2021_PRIMARY_SCOPE),
        formal_best_variant=best_formal.get("version_id", ""),
        formal_best_delta_return_pct_points_vs_v5f=round(_float(best_formal.get("delta_return_pct_points_vs_primary")), 6),
        formal_best_delta_return_pct_points_vs_global_v1=round(_float(best_formal.get("delta_return_pct_points_vs_global_v1")), 6),
        pre2021_best_variant=best_pre.get("version_id", ""),
        pre2021_best_delta_return_pct_points_vs_v5f=round(_float(best_pre.get("delta_return_pct_points_vs_primary")), 6),
        pre2021_best_delta_return_pct_points_vs_global_v1=round(_float(best_pre.get("delta_return_pct_points_vs_global_v1")), 6),
        pre2021_market_cap_coverage_rate_pct=_pre2021_mcap_coverage(pre2021_orders),
        sample_power=decision[0]["sample_power"],
    )
    _write_json(out / "v5h_size_liquidity_interaction_summary.json", summary)
    return summary


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [FORMAL_ORDER_PANEL, FORMAL_MCAP_SUMMARY, PRE2021_ORDER_PANEL, PRE2021_SUMMARY, FORMAL_DAILY, PRE2021_DAILY]
    return [_blocker("missing_required_input", str(path)) for path in required if not (root / path).exists()]


def _formal_variants() -> list[dict[str, Any]]:
    return [
        {"version_id": GLOBAL_V1_FORMAL, "condition": lambda row: True, "mode": "global_v1"},
        {
            "version_id": "v5h_size_liquidity_small_or_large_quiet_or_active_diagnostic",
            "condition": lambda row: row.get("mcap_bucket_within_sleeve_date") in {"small", "large"}
            and row.get("decision_10am_amount_intensity_bucket") in {"quiet", "active"},
            "mode": "gated_v1",
        },
        {
            "version_id": "v5h_size_liquidity_large_quiet_or_active_diagnostic",
            "condition": lambda row: row.get("mcap_bucket_within_sleeve_date") == "large"
            and row.get("decision_10am_amount_intensity_bucket") in {"quiet", "active"},
            "mode": "gated_v1",
        },
        {
            "version_id": "v5h_size_liquidity_small_quiet_or_active_diagnostic",
            "condition": lambda row: row.get("mcap_bucket_within_sleeve_date") == "small"
            and row.get("decision_10am_amount_intensity_bucket") in {"quiet", "active"},
            "mode": "gated_v1",
        },
        {
            "version_id": "v5h_size_liquidity_mid_normal_hold_default_diagnostic",
            "condition": lambda row: row.get("mcap_bucket_within_sleeve_date") != "mid"
            and row.get("decision_10am_amount_intensity_bucket") != "normal",
            "mode": "gated_v1",
        },
    ]


def _pre2021_variants() -> list[dict[str, Any]]:
    return [
        {"version_id": GLOBAL_V1_PRE2021, "condition": lambda row: True, "mode": "global_v1"},
        {
            "version_id": "pre2021_size_liquidity_small_or_large_quiet_or_active_diagnostic",
            "condition": lambda row: row.get("mcap_bucket_within_sleeve_date") in {"small", "large"}
            and row.get("decision_10am_amount_intensity_bucket") in {"quiet", "active"},
            "mode": "gated_v1",
        },
        {
            "version_id": "pre2021_size_liquidity_large_quiet_or_active_diagnostic",
            "condition": lambda row: row.get("mcap_bucket_within_sleeve_date") == "large"
            and row.get("decision_10am_amount_intensity_bucket") in {"quiet", "active"},
            "mode": "gated_v1",
        },
        {
            "version_id": "pre2021_size_liquidity_small_quiet_or_active_diagnostic",
            "condition": lambda row: row.get("mcap_bucket_within_sleeve_date") == "small"
            and row.get("decision_10am_amount_intensity_bucket") in {"quiet", "active"},
            "mode": "gated_v1",
        },
        {
            "version_id": "pre2021_size_liquidity_mid_normal_hold_default_diagnostic",
            "condition": lambda row: row.get("mcap_bucket_within_sleeve_date") != "mid"
            and row.get("decision_10am_amount_intensity_bucket") != "normal",
            "mode": "gated_v1",
        },
    ]


def _formal_adjustment_by_date(order_panel: list[dict[str, Any]], variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _adjustments(order_panel, variants, "trade_date", "incremental_edge_vs_default_10am", "trade_delta_weight_abs")


def _pre2021_adjustment_by_date(order_panel: list[dict[str, Any]], variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scoped = [row for row in order_panel if row.get("validation_scope") == PRE2021_PRIMARY_SCOPE]
    return _adjustments(scoped, variants, "trade_date", "incremental_edge_global_v1_vs_default_10am", "trade_delta_weight_abs")


def _adjustments(
    rows: list[dict[str, Any]],
    variants: list[dict[str, Any]],
    date_col: str,
    edge_col: str,
    weight_col: str,
) -> list[dict[str, Any]]:
    out = []
    for spec in variants:
        by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
        condition: Callable[[dict[str, Any]], bool] = spec["condition"]
        for row in rows:
            if spec["mode"] == "global_v1" or (
                row.get("market_cap_pit_status") == "pass" and condition(row)
            ):
                by_date[row[date_col]].append(row)
        for trade_date, group in sorted(by_date.items()):
            out.append(
                {
                    "version_id": spec["version_id"],
                    "trade_date": trade_date,
                    "execution_adjustment_return": sum(_float(row.get(edge_col)) * _float(row.get(weight_col)) for row in group),
                    "order_count": len(group),
                    "applied_order_count": len(group),
                    "accepted": False,
                }
            )
    return out


def _formal_nav(daily: pd.DataFrame, adjustment_by_date: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source = daily[daily["version_id"].isin([REPAIRED_BASELINE, V5F_PRIMARY])].copy()
    source = source[(source["trade_date"] >= FORMAL_BACKTEST_START) & (source["trade_date"] <= FORMAL_BACKTEST_END)].copy()
    rows = _base_nav_rows(source)
    primary = source[source["version_id"].eq(V5F_PRIMARY)].copy().sort_values("trade_date")
    return rows + _overlay_nav_rows(primary, adjustment_by_date, _formal_variants())


def _pre2021_nav(daily: pd.DataFrame, adjustment_by_date: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source = daily[daily["version_id"].isin([PRE2021_BASELINE, V5F_PRIMARY])].copy()
    source = source[(source["trade_date"] >= AVAILABLE_PRE2021_START) & (source["trade_date"] <= AVAILABLE_PRE2021_END)].copy()
    rows = _base_nav_rows(source)
    primary = source[source["version_id"].eq(V5F_PRIMARY)].copy().sort_values("trade_date")
    return rows + _overlay_nav_rows(primary, adjustment_by_date, _pre2021_variants())


def _base_nav_rows(source: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, row in source.iterrows():
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
    return rows


def _overlay_nav_rows(primary: pd.DataFrame, adjustment_by_date: list[dict[str, Any]], variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    adj_map = {(row["version_id"], row["trade_date"]): row for row in adjustment_by_date}
    rows: list[dict[str, Any]] = []
    for spec in variants:
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


def _metrics(
    nav_rows: list[dict[str, Any]],
    baseline_id: str,
    primary_id: str,
    global_id: str,
    window_id: str,
) -> list[dict[str, Any]]:
    if not nav_rows:
        return []
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
                "window_id": window_id,
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
    baseline = _find(out, baseline_id)
    primary = _find(out, primary_id)
    global_v1 = _find(out, global_id)
    for row in out:
        row["delta_return_pct_points_vs_baseline"] = (_float(row["strategy_return"]) - _float(baseline.get("strategy_return"))) * 100.0
        row["delta_return_pct_points_vs_primary"] = (_float(row["strategy_return"]) - _float(primary.get("strategy_return"))) * 100.0
        row["delta_return_pct_points_vs_global_v1"] = (_float(row["strategy_return"]) - _float(global_v1.get("strategy_return"))) * 100.0
        row["delta_max_drawdown_pct_points_vs_primary"] = (_float(row["max_drawdown"]) - _float(primary.get("max_drawdown"))) * 100.0
    return sorted(out, key=lambda row: (0 if "size_liquidity" in row["version_id"] else 1, row["version_id"]))


def _interaction_segments(
    order_panel: list[dict[str, Any]],
    window_id: str,
    edge_col: str = "incremental_edge_vs_default_10am",
    weighted_col: str = "weighted_incremental_edge_vs_default_10am",
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in order_panel:
        groups[
            (
                str(row.get("mcap_bucket_within_sleeve_date", "missing")),
                str(row.get("decision_10am_amount_intensity_bucket", "")),
                str(row.get("decision_10am_amount_pressure_bucket", "")),
            )
        ].append(row)
    out: list[dict[str, Any]] = []
    for (mcap_bucket, liquidity_bucket, pressure_bucket), group in sorted(groups.items()):
        total_weight = sum(_float(row.get("trade_delta_weight_abs")) for row in group)
        weighted = sum(_float(row.get(weighted_col)) for row in group)
        out.append(
            {
                "window_id": window_id,
                "mcap_bucket_within_sleeve_date": mcap_bucket,
                "decision_10am_amount_intensity_bucket": liquidity_bucket,
                "decision_10am_amount_pressure_bucket": pressure_bucket,
                "order_count": len(group),
                "trade_date_count": len({row.get("trade_date", "") for row in group}),
                "weighted_adjustment_pct_points": weighted * 100.0,
                "weighted_avg_incremental_edge_bp": weighted / total_weight * 10000.0 if total_weight else 0.0,
                "avg_incremental_edge_bp": _mean([row.get(edge_col) for row in group]) * 10000.0,
                "sample_power": _sample_power(len(group), len({row.get("trade_date", "") for row in group})),
                "diagnostic_only": True,
                "accepted": False,
            }
        )
    return out


def _attach_pre2021_market_cap(root: Path, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cap_lookup, audit = _pre2021_cap_lookup(root)
    out: list[dict[str, Any]] = []
    for row in rows:
        cap = cap_lookup.get((row.get("trade_date", ""), row.get("code", "")), {})
        item = dict(row)
        item.update(
            {
                "market_cap_100m_cny": cap.get("market_cap_100m_cny", ""),
                "market_cap_source": cap.get("market_cap_source", ""),
                "market_cap_visible_date": cap.get("market_cap_visible_date", ""),
                "market_cap_pit_method": cap.get("market_cap_pit_method", ""),
                "market_cap_pit_status": "pass" if cap else "missing",
            }
        )
        out.append(item)
    _assign_mcap_buckets(out)
    return out, audit


def _pre2021_cap_lookup(root: Path) -> tuple[dict[tuple[str, str], dict[str, Any]], list[dict[str, Any]]]:
    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    audit: list[dict[str, Any]] = []

    repaired_path = root / PRE2021_MCAP_REPAIR_ROWS
    repaired_rows = _read_csv(repaired_path)
    repaired_usable = 0
    for row in repaired_rows:
        trade_date = str(row.get("trade_date", ""))
        code = str(row.get("code", ""))
        market_cap = _none_float(row.get("market_cap_100m_cny"))
        visible = str(row.get("market_cap_visible_date") or trade_date)
        if trade_date and code and market_cap is not None and visible <= trade_date:
            lookup[(trade_date, code)] = {
                "market_cap_100m_cny": market_cap,
                "market_cap_source": str(repaired_path),
                "market_cap_visible_date": visible,
                "market_cap_pit_method": str(row.get("market_cap_pit_method") or "pre2021_repaired_total_market_cap"),
            }
            repaired_usable += 1
    audit.append(
        {
            "source_id": "pre2021_total_market_cap_repair_rows",
            "source_path": str(repaired_path),
            "row_count": len(repaired_rows),
            "usable_rows": repaired_usable,
            "status": "pass" if repaired_usable else "warn",
            "notes": "Priority source for repaired pre-2021 highway/port-rail total market cap.",
        }
    )

    bank_files = list(V4_BANK_VALUATION_ROOT.glob("*/daily_valuation.csv")) if V4_BANK_VALUATION_ROOT.exists() else []
    bank_rows = 0
    for path in bank_files:
        for row in _read_csv(path):
            date = str(row.get("day", ""))
            code = str(row.get("code", ""))
            market_cap = _none_float(row.get("market_cap"))
            if date and code and market_cap is not None:
                lookup[(date, code)] = {
                    "market_cap_100m_cny": market_cap,
                    "market_cap_source": str(path),
                    "market_cap_visible_date": date,
                    "market_cap_pit_method": "direct_v4_migrated_daily_valuation_market_cap",
                }
                bank_rows += 1
    audit.append(
        {
            "source_id": "bank_v4_daily_valuation",
            "source_path": str(V4_BANK_VALUATION_ROOT),
            "usable_rows": bank_rows,
            "status": "pass" if bank_rows else "missing",
            "notes": "Direct same-day daily valuation market_cap for bank sleeve.",
        }
    )

    db = _find_v5_database(root)
    panel_paths = [
        db / "processed" / "startup_preload_repaired_panels_v5" / "utilities_v51f" / "panel_with_low_vol.csv",
        root / "v5f_pre2021_factor_panel_repair" / "current" / "v5f_pre2021_highway_v54h_strict_panel_with_low_vol.csv",
        root / "v5f_pre2021_factor_panel_repair" / "current" / "v5f_pre2021_port_rail_v55j_strict_panel_with_low_vol.csv",
    ]
    for path in panel_paths:
        usable = 0
        rows = _read_csv(path)
        for row in rows:
            date = str(row.get("trade_date", ""))
            code = str(row.get("code", ""))
            visible = str(row.get("factor_visible_date") or date)
            market_cap = _none_float(row.get("market_cap"))
            if date and code and market_cap is not None and visible <= date:
                lookup[(date, code)] = {
                    "market_cap_100m_cny": market_cap,
                    "market_cap_source": str(path),
                    "market_cap_visible_date": visible,
                    "market_cap_pit_method": "direct_pre2021_or_repaired_panel_market_cap",
                }
                usable += 1
        audit.append(
            {
                "source_id": path.stem,
                "source_path": str(path),
                "row_count": len(rows),
                "usable_rows": usable,
                "status": "pass" if usable else "warn",
                "notes": "Used only when market_cap is present and factor_visible_date <= trade_date.",
            }
        )
    return lookup, audit


def _assign_mcap_buckets(rows: list[dict[str, Any]]) -> None:
    unique: dict[tuple[str, str, str], float] = {}
    for row in rows:
        market_cap = _none_float(row.get("market_cap_100m_cny"))
        if market_cap is not None:
            unique[(row.get("trade_date", ""), row.get("sleeve", ""), row.get("code", ""))] = market_cap
    groups: dict[tuple[str, str], list[tuple[str, float]]] = defaultdict(list)
    for (date, sleeve, code), market_cap in unique.items():
        groups[(date, sleeve)].append((code, market_cap))
    buckets: dict[tuple[str, str, str], str] = {}
    for (date, sleeve), items in groups.items():
        ordered = sorted(items, key=lambda item: item[1])
        n = len(ordered)
        for index, (code, _market_cap) in enumerate(ordered):
            if n < 3:
                bucket = "insufficient_group_size"
            else:
                pct = index / (n - 1)
                bucket = "small" if pct < 1 / 3 else "mid" if pct < 2 / 3 else "large"
            buckets[(date, sleeve, code)] = bucket
    for row in rows:
        row["mcap_bucket_within_sleeve_date"] = buckets.get((row.get("trade_date", ""), row.get("sleeve", ""), row.get("code", "")), "missing")


def _data_gate(
    root: Path,
    formal_orders: list[dict[str, Any]],
    pre2021_orders: list[dict[str, Any]],
    pre2021_cap_audit: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    formal_summary = _read_json(root / FORMAL_MCAP_SUMMARY)
    pre_summary = _read_json(root / PRE2021_SUMMARY)
    pre_primary = [row for row in pre2021_orders if row.get("validation_scope") == PRE2021_PRIMARY_SCOPE]
    pre_pass = sum(1 for row in pre_primary if row.get("market_cap_pit_status") == "pass")
    pre_dates = len({row.get("trade_date", "") for row in pre_primary})
    return [
        {"gate_id": "formal_total_market_cap_coverage", "status": "pass" if formal_summary.get("market_cap_coverage_rate_pct") == 100.0 else "fail", "value": formal_summary.get("market_cap_coverage_rate_pct")},
        {"gate_id": "formal_order_panel_available", "status": "pass" if formal_orders else "fail", "value": len(formal_orders)},
        {"gate_id": "pre2021_quiet_or_active_completed", "status": "pass" if pre_summary.get("status") == "completed_quiet_or_active_independent_validation" else "fail", "value": pre_summary.get("status", "")},
        {"gate_id": "pre2021_market_cap_primary_coverage", "status": "warn" if _pct(pre_pass, len(pre_primary)) < 95 else "pass", "value": _pct(pre_pass, len(pre_primary))},
        {"gate_id": "pre2021_sample_power", "status": "warn" if _sample_power(len(pre_primary), pre_dates) != "adequate" else "pass", "value": f"orders={len(pre_primary)};dates={pre_dates}"},
        {"gate_id": "pre2021_source_no_future_share_capital", "status": "pass", "value": "future dividend/share-capital rows not used"},
        {"gate_id": "network_fetch_started", "status": "pass", "value": False},
        {"gate_id": "joinquant_started", "status": "pass", "value": False},
    ]


def _governance_audit() -> list[dict[str, Any]]:
    return [
        {"audit_id": "v57f_core_unchanged", "status": "pass", "detail": "No V57f selection, weights, factor rules, or rebalance dates changed."},
        {"audit_id": "v5f_mainline_unchanged", "status": "pass", "detail": "internal_subsleeve_mom12_70_30 remains the V5f mainline."},
        {"audit_id": "existing_buy_orders_only", "status": "pass", "detail": "Interaction gate only reuses existing buy/increase order timing diagnostics."},
        {"audit_id": "no_new_buy_signal", "status": "pass", "detail": "No stock can be added by size or liquidity."},
        {"audit_id": "no_frequency_increase", "status": "pass", "detail": "Only 10:00 vs 14:00 proxy timing on existing buy dates is compared."},
        {"audit_id": "no_free_float_forced", "status": "pass", "detail": "Free-float is not used because PIT coverage remains insufficient."},
        {"audit_id": "not_accepted_not_live", "status": "pass", "detail": "No accepted/live/deployment status is granted."},
    ]


def _pm_decision(
    formal_metrics: list[dict[str, Any]],
    pre2021_metrics: list[dict[str, Any]],
    data_gate: list[dict[str, Any]],
    governance: list[dict[str, Any]],
    pre2021_orders: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    hard_fail = any(row.get("status") == "fail" for row in data_gate + governance)
    pre_primary = [row for row in pre2021_orders if row.get("validation_scope") == PRE2021_PRIMARY_SCOPE]
    sample_power = _sample_power(len(pre_primary), len({row.get("trade_date", "") for row in pre_primary}))
    pre_cov = _pre2021_mcap_coverage(pre_primary)
    formal_best = _best_interaction(formal_metrics)
    pre_best = _best_interaction(pre2021_metrics)
    formal_positive_vs_global = _float(formal_best.get("delta_return_pct_points_vs_global_v1")) > 0
    pre_positive_vs_global = _float(pre_best.get("delta_return_pct_points_vs_global_v1")) > 0
    if hard_fail:
        decision = "blocked_by_data_or_governance_issue"
        status = "blocked"
    elif formal_positive_vs_global and pre_positive_vs_global and sample_power == "adequate" and pre_cov >= 95.0:
        decision = "size_liquidity_interaction_positive_ready_for_forward_observation_not_accepted"
        status = "independent_positive"
    elif formal_positive_vs_global:
        decision = "size_liquidity_interaction_formal_positive_but_independent_unconfirmed"
        status = "diagnostic_only"
    else:
        decision = "size_liquidity_interaction_no_incremental_edge_over_global_v1"
        status = "diagnostic_only"
    return [
        {
            "pm_gate_decision": decision,
            "status": status,
            "sample_power": sample_power,
            "pre2021_market_cap_coverage_rate_pct": pre_cov,
            "formal_best_variant": formal_best.get("version_id", ""),
            "formal_best_delta_return_pct_points_vs_global_v1": formal_best.get("delta_return_pct_points_vs_global_v1", ""),
            "formal_best_delta_return_pct_points_vs_v5f": formal_best.get("delta_return_pct_points_vs_primary", ""),
            "pre2021_best_variant": pre_best.get("version_id", ""),
            "pre2021_best_delta_return_pct_points_vs_global_v1": pre_best.get("delta_return_pct_points_vs_global_v1", ""),
            "pre2021_best_delta_return_pct_points_vs_v5f": pre_best.get("delta_return_pct_points_vs_primary", ""),
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "v5f_mainline_modified": False,
            "notes": "Formal-period interaction is not enough for upgrade; require stronger pre-2021 or forward evidence.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "queue_id": "v5h_pre2021_total_market_cap_source_repair_for_highway_port_rail",
            "status": "ready_if_size_liquidity_research_continues",
            "scope": "Repair pre-2021 total market-cap sources for highway and port/rail before using size interaction as independent evidence.",
        },
        {
            "priority": 2,
            "queue_id": "v5h_buy_execution_v1_forward_observation_continuation",
            "status": "ready",
            "scope": "Keep pressure_positive_1000_else_1400_buy as the observation line.",
        },
        {
            "priority": 3,
            "queue_id": "v5h_size_liquidity_interaction_forward_paper_append",
            "status": "observation_only_if_pm_approves",
            "scope": "Append interaction diagnostics on future official buy orders; do not alter execution.",
        },
    ]


def _report(
    formal_metrics: list[dict[str, Any]],
    pre2021_metrics: list[dict[str, Any]],
    formal_segments: list[dict[str, Any]],
    pre2021_segments: list[dict[str, Any]],
    data_gate: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    lines = [
        "# V5h Size x Liquidity Interaction Validation",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Formal backtest window: `{FORMAL_BACKTEST_START}` to `{FORMAL_BACKTEST_END}`",
        f"- Pre-2021 validation window: `{AVAILABLE_PRE2021_START}` to `{AVAILABLE_PRE2021_END}`",
        "- Scope: existing V5f buy/increase orders only; no new buys, no sell changes.",
        "",
        "## Formal Variant Results",
    ]
    for row in formal_metrics:
        if row["version_id"] in {REPAIRED_BASELINE, V5F_PRIMARY}:
            continue
        lines.append(
            f"- `{row['version_id']}`: return `{_float(row['strategy_return']) * 100:.4f}%`, vs V5f `{_float(row['delta_return_pct_points_vs_primary']):+.4f}` pct, vs global v1 `{_float(row['delta_return_pct_points_vs_global_v1']):+.4f}` pct."
        )
    lines.extend(["", "## Pre-2021 Variant Results"])
    for row in pre2021_metrics:
        if row["version_id"] in {PRE2021_BASELINE, V5F_PRIMARY}:
            continue
        lines.append(
            f"- `{row['version_id']}`: return `{_float(row['strategy_return']) * 100:.4f}%`, vs V5f `{_float(row['delta_return_pct_points_vs_primary']):+.4f}` pct, vs global v1 `{_float(row['delta_return_pct_points_vs_global_v1']):+.4f}` pct."
        )
    lines.extend(["", "## Data Gate"])
    for row in data_gate:
        lines.append(f"- `{row['gate_id']}`: `{row['status']}` ({row['value']})")
    lines.extend(
        [
            "",
            "## Segment Notes",
            f"- Formal interaction cells: `{len(formal_segments)}`",
            f"- Pre-2021 interaction cells: `{len(pre2021_segments)}`",
            "- Pre-2021 sample is low power; do not upgrade from this packet alone.",
            "",
        ]
    )
    return "\n".join(lines)


def _rules() -> str:
    return "\n".join(
        [
            "# V5h Size x Liquidity Interaction Rules",
            "",
            "- Use only PIT-clean total market cap for size buckets.",
            "- Do not use free-float market cap until PIT coverage is repaired.",
            "- Do not modify V57f core or V5f mainline.",
            "- Do not create new buy signals, sell rules, or higher-frequency trading.",
            "- Treat 2021-05-01 to 2026-05-31 as formal backtest, not independent validation.",
            "- Treat pre-2021 as validation/training support only and mark low sample power when applicable.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _best_interaction(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in metrics if "size_liquidity" in row.get("version_id", "")]
    return max(eligible, key=lambda row: _float(row.get("delta_return_pct_points_vs_global_v1"))) if eligible else {}


def _pre2021_mcap_coverage(rows: list[dict[str, Any]]) -> float:
    return _pct(sum(1 for row in rows if row.get("market_cap_pit_status") == "pass"), len(rows))


def _find_v5_database(root: Path) -> Path:
    for child in root.iterdir():
        if child.is_dir() and (child / "processed").exists() and (child / "raw").exists() and (child / "manifests").exists():
            return child
    raise FileNotFoundError("Could not locate V5 database directory.")


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
        "task": "v5h_size_liquidity_interaction_independent_validation",
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
        "free_float_market_cap_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len([row for row in blockers if row.get("status") == "blocking"]),
        "fatal_blockers": [row for row in blockers if row.get("status") == "blocking"],
        **extra,
    }


def _sample_power(order_count: int, date_count: int) -> str:
    if order_count >= 80 and date_count >= 8:
        return "adequate"
    if order_count >= 30 and date_count >= 3:
        return "moderate"
    return "low_power"


def _max_drawdown(navs: list[float]) -> float:
    peak = 0.0
    max_dd = 0.0
    for nav in navs:
        peak = max(peak, nav)
        if peak:
            max_dd = min(max_dd, nav / peak - 1.0)
    return abs(max_dd)


def _mean(values: list[Any]) -> float:
    parsed = [_float(value) for value in values]
    return sum(parsed) / len(parsed) if parsed else 0.0


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
    summary = run_v5h_size_liquidity_interaction_validation(Path("."))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

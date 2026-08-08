from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd


OUT_DIR = Path("v5h_segmented_1min_execution_diagnostic") / "current"
SPEC_DIR = Path("v5h_buy_execution_spec_v1") / "current"
BACKTEST_DIR = Path("v5h_buy_execution_backtest") / "current"
OVERLAY_DIR = Path("v5h_buy_execution_timing_overlay") / "current"
ROUGH_DIR = Path("v5f_structural_rough_screen") / "current"
VALUATION_DIR = Path("v5c_p2_valuation_and_crowding_state_panel") / "current"

SPEC_SUMMARY = SPEC_DIR / "v5h_buy_execution_spec_v1_summary.json"
BACKTEST_SUMMARY = BACKTEST_DIR / "v5h_buy_execution_backtest_summary.json"
DECISION_LOG = OVERLAY_DIR / "v5h_buy_execution_timing_order_decision_log.csv"
DAILY_RETURNS = ROUGH_DIR / "v5f_structural_rough_screen_daily_returns.csv"
VALUATION_PANEL = VALUATION_DIR / "v5c_p2_valuation_state_panel.csv"

FORMAL_BACKTEST_START = "2021-05-01"
FORMAL_BACKTEST_END = "2026-05-31"
REPAIRED_BASELINE = "v57f_startup_preload_repaired_baseline"
V5F_PRIMARY = "internal_subsleeve_mom12_70_30"
V5H_SPEC_V1 = "pressure_positive_1000_else_1400_buy"
V5H_LINE_ID = "v5h_1min_microstructure_execution_research"
PRIMARY_SCOPE_FAMILY = "v5f_champion_rebalance"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5h_segmented_1min_execution_diagnostic(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        summary = _summary("blocked_missing_required_input", "blocked_until_required_inputs_available", blockers)
        _write_json(out / "v5h_segmented_execution_summary.json", summary)
        _write_csv(out / "v5h_segmented_execution_blockers.csv", blockers)
        return summary

    spec_summary = _read_json(root / SPEC_SUMMARY)
    backtest_summary = _read_json(root / BACKTEST_SUMMARY)
    daily = pd.read_csv(root / DAILY_RETURNS, dtype={"trade_date": str, "version_id": str, "active_rebalance_date": str})
    decision_log = _read_csv(root / DECISION_LOG)
    base_rows, v1_rows = _v5f_champion_rows(decision_log)
    order_panel = _segmented_order_panel(base_rows, v1_rows)
    segment_tables = _segment_tables(order_panel)
    variants = _segmented_variants()
    adjustment_by_date = _variant_adjustments(order_panel, variants)
    nav_rows = _build_nav_rows(daily, adjustment_by_date)
    metrics = _metrics(nav_rows)
    yearly = _yearly(nav_rows)
    candidate_matrix = _candidate_matrix(metrics)
    market_cap_gate = _market_cap_data_gate(root)
    data_gate = _data_gate(spec_summary, backtest_summary, daily, decision_log, order_panel, market_cap_gate)
    governance = _governance_audit()
    decision = _pm_decision(candidate_matrix, data_gate, governance)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": ""}]

    _write_csv(out / "v5h_segmented_execution_order_panel.csv", order_panel)
    _write_csv(out / "v5h_segmented_execution_by_sleeve.csv", segment_tables["sleeve"])
    _write_csv(out / "v5h_segmented_execution_by_10am_liquidity.csv", segment_tables["liquidity"])
    _write_csv(out / "v5h_segmented_execution_by_10am_zone.csv", segment_tables["zone"])
    _write_csv(out / "v5h_segmented_execution_by_sleeve_liquidity.csv", segment_tables["sleeve_liquidity"])
    _write_csv(out / "v5h_segmented_execution_variant_rule_spec.csv", _variant_rule_spec())
    _write_csv(out / "v5h_segmented_execution_adjustment_by_date.csv", adjustment_by_date)
    _write_csv(out / "v5h_segmented_execution_daily_nav.csv", nav_rows)
    _write_csv(out / "v5h_segmented_execution_variant_metrics.csv", metrics)
    _write_csv(out / "v5h_segmented_execution_yearly.csv", yearly)
    _write_csv(out / "v5h_segmented_execution_candidate_matrix.csv", candidate_matrix)
    _write_csv(out / "v5h_segmented_execution_market_cap_data_gate.csv", market_cap_gate)
    _write_csv(out / "v5h_segmented_execution_data_gate.csv", data_gate)
    _write_csv(out / "v5h_segmented_execution_governance_audit.csv", governance)
    _write_csv(out / "v5h_segmented_execution_pm_gate_decision.csv", decision)
    _write_csv(out / "v5h_segmented_execution_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5h_segmented_execution_blockers.csv", blockers_out)
    (out / "v5h_segmented_execution_report.md").write_text(
        _report(metrics, segment_tables, candidate_matrix, market_cap_gate, decision),
        encoding="utf-8",
    )
    (out / "v5h_segmented_execution_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    best = _best_segmented(metrics)
    global_v1 = _find(metrics, "v5h_spec_v1_global_reference")
    summary = _summary(
        "completed_v5h_segmented_1min_execution_diagnostic",
        decision[0]["pm_gate_decision"],
        [],
        formal_backtest_start=FORMAL_BACKTEST_START,
        formal_backtest_end=FORMAL_BACKTEST_END,
        order_count=len(order_panel),
        best_segmented_variant=best.get("version_id", ""),
        best_segmented_return_pct=round(_float(best.get("strategy_return")) * 100.0, 6),
        best_segmented_delta_return_pct_points_vs_v5f=round(_float(best.get("delta_return_pct_points_vs_v5f_primary")), 6),
        best_segmented_delta_return_pct_points_vs_global_v1=round(
            (_float(best.get("strategy_return")) - _float(global_v1.get("strategy_return"))) * 100.0,
            6,
        ),
        market_cap_segmentation_status=market_cap_gate[0]["status"],
        accepted=False,
    )
    _write_json(out / "v5h_segmented_execution_summary.json", summary)
    return summary


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [SPEC_SUMMARY, BACKTEST_SUMMARY, DECISION_LOG, DAILY_RETURNS]
    return [_blocker("missing_required_input", str(path)) for path in required if not (root / path).exists()]


def _v5f_champion_rows(decision_log: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    base = {}
    v1 = []
    for row in decision_log:
        if row.get("order_type") != "scheduled_buy" or row.get("intent_family") != PRIMARY_SCOPE_FAMILY:
            continue
        if not (FORMAL_BACKTEST_START <= row.get("trade_date", "") <= FORMAL_BACKTEST_END):
            continue
        if row.get("variant_id") == "baseline_default_1000_proxy":
            base[row["intent_id"]] = row
        elif row.get("variant_id") == V5H_SPEC_V1:
            v1.append(row)
    return base, v1


def _segmented_order_panel(base_rows: dict[str, dict[str, Any]], v1_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in v1_rows:
        base = base_rows.get(row["intent_id"], {})
        rows.append(
            {
                "intent_id": row.get("intent_id", ""),
                "trade_date": row.get("trade_date", ""),
                "code": row.get("code", ""),
                "sleeve": row.get("sleeve", ""),
                "intent_family": row.get("intent_family", ""),
                "v1_selected_obs_time": row.get("selected_obs_time", ""),
                "decision_10am_amount_pressure_bucket": base.get("amount_pressure_bucket", ""),
                "decision_10am_amount_intensity_bucket": base.get("amount_intensity_bucket", ""),
                "decision_10am_volume_intensity_bucket": base.get("volume_intensity_bucket", ""),
                "decision_10am_pit_zone_bucket": base.get("pit_zone_bucket", ""),
                "selected_obs_amount_pressure_bucket": row.get("amount_pressure_bucket", ""),
                "trade_delta_weight_abs": _float(row.get("trade_delta_weight_abs")),
                "incremental_edge_vs_default_10am": _float(row.get("incremental_edge_vs_baseline_order")),
                "weighted_incremental_edge_vs_default_10am": _float(row.get("weighted_incremental_edge_vs_baseline_order")),
                "used_10am_decision_features": bool(base),
                "accepted": False,
            }
        )
    return rows


def _segment_tables(order_panel: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        "sleeve": _group_segment(order_panel, ["sleeve"]),
        "liquidity": _group_segment(order_panel, ["decision_10am_amount_intensity_bucket"]),
        "zone": _group_segment(order_panel, ["decision_10am_pit_zone_bucket"]),
        "sleeve_liquidity": _group_segment(order_panel, ["sleeve", "decision_10am_amount_intensity_bucket"]),
    }


def _group_segment(rows: list[dict[str, Any]], columns: list[str]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(str(row.get(col, "")) for col in columns)].append(row)
    out = []
    for key, group in sorted(groups.items()):
        weight_sum = sum(_float(row["trade_delta_weight_abs"]) for row in group)
        total_adj = sum(_float(row["weighted_incremental_edge_vs_default_10am"]) for row in group)
        result = {columns[index]: key[index] for index in range(len(columns))}
        result.update(
            {
                "order_count": len(group),
                "trade_date_count": len({row["trade_date"] for row in group}),
                "early_1000_count": sum(1 for row in group if row["v1_selected_obs_time"] == "10:00:00"),
                "fallback_1400_count": sum(1 for row in group if row["v1_selected_obs_time"] == "14:00:00"),
                "execution_adjustment_total_pct_points": total_adj * 100.0,
                "avg_order_incremental_edge_bp": _mean([row["incremental_edge_vs_default_10am"] for row in group]) * 10000.0,
                "weighted_avg_order_incremental_edge_bp": total_adj / weight_sum * 10000.0 if weight_sum else 0.0,
                "diagnostic_status": _segment_status(len(group), total_adj),
            }
        )
        out.append(result)
    return out


def _segmented_variants() -> list[dict[str, Any]]:
    return [
        {
            "version_id": "v5h_spec_v1_global_reference",
            "rule": "Apply frozen V5h v1 to all V5f champion planned buy/increase orders.",
            "condition": lambda row: True,
            "promotion_status": "reference_backtest_not_accepted",
        },
        {
            "version_id": "v5h_segment_liquidity_quiet_only_diagnostic",
            "rule": "Apply v1 only when 10:00 amount-intensity bucket is quiet; otherwise keep default 10:00.",
            "condition": lambda row: row.get("decision_10am_amount_intensity_bucket") == "quiet",
            "promotion_status": "diagnostic_only_backtest_selected",
        },
        {
            "version_id": "v5h_segment_liquidity_quiet_or_active_diagnostic",
            "rule": "Apply v1 when 10:00 amount-intensity bucket is quiet or active; otherwise keep default 10:00.",
            "condition": lambda row: row.get("decision_10am_amount_intensity_bucket") in {"quiet", "active"},
            "promotion_status": "diagnostic_only_backtest_selected",
        },
        {
            "version_id": "v5h_segment_zone_low_mid_diagnostic",
            "rule": "Apply v1 only when 10:00 relative intraday zone is low or mid; otherwise keep default 10:00.",
            "condition": lambda row: row.get("decision_10am_pit_zone_bucket") in {"low_0_30", "mid_30_70"},
            "promotion_status": "diagnostic_only_backtest_selected",
        },
        {
            "version_id": "v5h_segment_sleeve_bank_utilities_diagnostic",
            "rule": "Apply v1 only in bank and utilities_electricity sleeves.",
            "condition": lambda row: row.get("sleeve") in {"bank", "utilities_electricity"},
            "promotion_status": "diagnostic_only_backtest_selected",
        },
        {
            "version_id": "v5h_segment_non_highway_diagnostic",
            "rule": "Apply v1 outside highway_infrastructure sleeve.",
            "condition": lambda row: row.get("sleeve") != "highway_infrastructure",
            "promotion_status": "diagnostic_only_backtest_selected",
        },
    ]


def _variant_rule_spec() -> list[dict[str, Any]]:
    return [
        {
            "version_id": spec["version_id"],
            "rule": spec["rule"],
            "promotion_status": spec["promotion_status"],
            "accepted": False,
            "live_trading_approved": False,
            "notes": "Segmented variants are diagnostic because segments are read from the backtest period and require independent validation.",
        }
        for spec in _segmented_variants()
    ]


def _variant_adjustments(order_panel: list[dict[str, Any]], variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for spec in variants:
        condition: Callable[[dict[str, Any]], bool] = spec["condition"]
        for row in order_panel:
            if condition(row):
                groups[(spec["version_id"], row["trade_date"])].append(row)
    out = []
    for (version, trade_date), group in sorted(groups.items()):
        out.append(
            {
                "version_id": version,
                "trade_date": trade_date,
                "execution_adjustment_return": sum(_float(row["weighted_incremental_edge_vs_default_10am"]) for row in group),
                "order_count": len(group),
                "early_1000_count": sum(1 for row in group if row["v1_selected_obs_time"] == "10:00:00"),
                "fallback_1400_count": sum(1 for row in group if row["v1_selected_obs_time"] == "14:00:00"),
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

    primary = df[df["version_id"] == V5F_PRIMARY].copy().sort_values("trade_date")
    adj_map: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in adjustment_by_date:
        adj_map[row["version_id"]][row["trade_date"]] = row
    for spec in _segmented_variants():
        version = spec["version_id"]
        nav = 1.0
        for _, row in primary.iterrows():
            adj = adj_map.get(version, {}).get(row["trade_date"], {})
            execution_adj = _float(adj.get("execution_adjustment_return"))
            ret = _float(row["strategy_return"]) + execution_adj
            nav *= 1.0 + ret
            rows.append(
                {
                    "trade_date": row["trade_date"],
                    "version_id": version,
                    "strategy_return": ret,
                    "execution_adjustment_return": execution_adj,
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
        navs = pd.to_numeric(ordered["strategy_nav"]).tolist()
        rets = pd.to_numeric(ordered["strategy_return"]).tolist()
        ann = navs[-1] ** (252 / len(navs)) - 1.0
        vol = pd.Series(rets).std() * (252**0.5)
        out.append(
            {
                "version_id": version,
                "strategy_return": navs[-1] - 1.0,
                "annualized_return": ann,
                "max_drawdown": _max_drawdown(navs),
                "volatility": vol,
                "sharpe_proxy": ann / vol if vol else 0.0,
                "execution_adjustment_total": pd.to_numeric(ordered["execution_adjustment_return"]).sum(),
                "execution_adjustment_trade_date_count": int((pd.to_numeric(ordered["execution_adjustment_return"]) != 0).sum()),
                "nav_comparable": bool(ordered["nav_comparable"].astype(bool).all()),
                "accepted": False,
            }
        )
    repaired = _find(out, REPAIRED_BASELINE)
    v5f = _find(out, V5F_PRIMARY)
    global_v1 = _find(out, "v5h_spec_v1_global_reference")
    for row in out:
        row["delta_return_pct_points_vs_repaired_baseline"] = (_float(row["strategy_return"]) - _float(repaired.get("strategy_return"))) * 100.0
        row["delta_return_pct_points_vs_v5f_primary"] = (_float(row["strategy_return"]) - _float(v5f.get("strategy_return"))) * 100.0
        row["delta_return_pct_points_vs_global_v1"] = (_float(row["strategy_return"]) - _float(global_v1.get("strategy_return"))) * 100.0
        row["delta_max_drawdown_pct_points_vs_v5f_primary"] = (_float(row["max_drawdown"]) - _float(v5f.get("max_drawdown"))) * 100.0
    order = {
        "v5h_segment_liquidity_quiet_or_active_diagnostic": 0,
        "v5h_segment_liquidity_quiet_only_diagnostic": 1,
        "v5h_spec_v1_global_reference": 2,
        "v5h_segment_zone_low_mid_diagnostic": 3,
        "v5h_segment_sleeve_bank_utilities_diagnostic": 4,
        "v5h_segment_non_highway_diagnostic": 5,
        V5F_PRIMARY: 6,
        REPAIRED_BASELINE: 7,
    }
    return sorted(out, key=lambda row: order.get(row["version_id"], 99))


def _yearly(nav_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(nav_rows).sort_values(["version_id", "trade_date"])
    df["year"] = df["trade_date"].str.slice(0, 4)
    rows = []
    for (version, year), group in df.groupby(["version_id", "year"], sort=True):
        ordered = group.sort_values("trade_date")
        year_return = (1.0 + pd.to_numeric(ordered["strategy_return"])).prod() - 1.0
        rows.append(
            {
                "version_id": version,
                "year": year,
                "year_return": year_return,
                "execution_adjustment_total": pd.to_numeric(ordered["execution_adjustment_return"]).sum(),
                "trade_days": len(ordered),
                "accepted": False,
            }
        )
    v5f = {(row["year"]): row for row in rows if row["version_id"] == V5F_PRIMARY}
    for row in rows:
        row["delta_return_pct_points_vs_v5f_primary"] = (_float(row["year_return"]) - _float(v5f.get(row["year"], {}).get("year_return"))) * 100.0
    return rows


def _candidate_matrix(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in metrics:
        version = row["version_id"]
        if version in {REPAIRED_BASELINE, V5F_PRIMARY}:
            continue
        selected_from_backtest = version != "v5h_spec_v1_global_reference"
        status = (
            "diagnostic_positive_needs_independent_validation"
            if _float(row["delta_return_pct_points_vs_v5f_primary"]) > 0
            else "diagnostic_only_no_edge"
        )
        rows.append(
            {
                "candidate_id": version,
                "strategy_return_pct": _float(row["strategy_return"]) * 100.0,
                "delta_return_pct_points_vs_v5f_primary": row["delta_return_pct_points_vs_v5f_primary"],
                "delta_return_pct_points_vs_global_v1": row["delta_return_pct_points_vs_global_v1"],
                "max_drawdown_pct": _float(row["max_drawdown"]) * 100.0,
                "delta_max_drawdown_pct_points_vs_v5f_primary": row["delta_max_drawdown_pct_points_vs_v5f_primary"],
                "sharpe_proxy": row["sharpe_proxy"],
                "selected_from_backtest_segments": selected_from_backtest,
                "pm_status": status,
                "accepted": False,
            }
        )
    return rows


def _market_cap_data_gate(root: Path) -> list[dict[str, Any]]:
    status = "missing_pit_clean_market_cap_panel"
    value = "market_cap/free_float_market_cap field not found in primary V5h/V5c PIT inputs"
    if (root / VALUATION_PANEL).exists():
        header = (root / VALUATION_PANEL).read_text(encoding="utf-8-sig").splitlines()[0].lower()
        if "market_cap" in header or "float_market_cap" in header or "total_mv" in header or "circ_mv" in header:
            status = "available_needs_join_audit"
            value = str(VALUATION_PANEL)
    return [
        {
            "gate_id": "pit_clean_market_cap_for_segmentation",
            "status": status,
            "value": value,
            "fatal": False,
            "notes": "Market-cap segmentation is not run until PIT-clean market cap/free-float cap is available.",
        }
    ]


def _data_gate(
    spec_summary: dict[str, Any],
    backtest_summary: dict[str, Any],
    daily: pd.DataFrame,
    decision_log: list[dict[str, Any]],
    order_panel: list[dict[str, Any]],
    market_cap_gate: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    versions = set(daily["version_id"].unique())
    return [
        {"gate_id": "v5h_spec_v1_frozen", "status": "pass" if spec_summary.get("status") == "completed_v5h_buy_execution_spec_v1_frozen" else "fail", "value": spec_summary.get("status", "")},
        {"gate_id": "v5h_backtest_completed", "status": "pass" if backtest_summary.get("status") == "completed_v5h_buy_execution_backtest" else "fail", "value": backtest_summary.get("status", "")},
        {"gate_id": "v5f_primary_daily_returns_available", "status": "pass" if V5F_PRIMARY in versions else "fail", "value": V5F_PRIMARY in versions},
        {"gate_id": "decision_log_loaded", "status": "pass" if decision_log else "fail", "value": len(decision_log)},
        {"gate_id": "v5f_champion_order_panel_built", "status": "pass" if order_panel else "fail", "value": len(order_panel)},
        {"gate_id": "market_cap_segmentation", "status": market_cap_gate[0]["status"], "value": market_cap_gate[0]["value"]},
    ]


def _governance_audit() -> list[dict[str, Any]]:
    return [
        {"audit_id": "v57f_core_unchanged", "status": "pass", "detail": "No V57f selection, weights, or rebalance frequency changed."},
        {"audit_id": "v5f_mainline_unchanged", "status": "pass", "detail": "V5f primary remains internal_subsleeve_mom12_70_30."},
        {"audit_id": "buy_side_only", "status": "pass", "detail": "Only existing V5f champion buy/increase orders are analyzed."},
        {"audit_id": "sell_rules_unchanged", "status": "pass", "detail": "No sell/decrease timing is touched."},
        {"audit_id": "no_new_buy_signal", "status": "pass", "detail": "Segment gates cannot create orders."},
        {"audit_id": "no_threshold_scan", "status": "pass", "detail": "Only fixed buckets already produced by V5h are used; no numeric threshold scan."},
        {"audit_id": "segmented_rules_diagnostic_only", "status": "pass", "detail": "Segmented variants are selected from backtest evidence and require independent validation."},
        {"audit_id": "not_accepted_not_live", "status": "pass", "detail": "No accepted/live/deployment status is granted."},
    ]


def _pm_decision(
    candidate_matrix: list[dict[str, Any]],
    data_gate: list[dict[str, Any]],
    governance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    hard_fail = any(row.get("status") == "fail" for row in data_gate) or any(row.get("status") != "pass" for row in governance)
    if hard_fail:
        decision = "blocked_by_data_or_governance_issue"
        status = "blocked"
    else:
        best = max(candidate_matrix, key=lambda row: _float(row.get("delta_return_pct_points_vs_v5f_primary")))
        if _float(best.get("delta_return_pct_points_vs_global_v1")) > 0:
            decision = "segmented_1min_execution_diagnostic_positive_needs_pre2021_or_forward_validation"
            status = "diagnostic_positive"
        else:
            decision = "segmented_1min_execution_no_improvement_over_global_v1"
            status = "diagnostic_only"
    best = max(candidate_matrix, key=lambda row: _float(row.get("delta_return_pct_points_vs_v5f_primary"))) if candidate_matrix else {}
    return [
        {
            "pm_gate_decision": decision,
            "status": status,
            "best_diagnostic_variant": best.get("candidate_id", ""),
            "best_delta_return_pct_points_vs_v5f": best.get("delta_return_pct_points_vs_v5f_primary", ""),
            "best_delta_return_pct_points_vs_global_v1": best.get("delta_return_pct_points_vs_global_v1", ""),
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "v5f_mainline_modified": False,
            "sell_rules_modified": False,
            "trading_frequency_increased": False,
            "new_buy_signal_used": False,
            "notes": "Use segmentation as research direction only; do not freeze until independent validation.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "queue_id": "v5h_segment_liquidity_quiet_or_active_independent_validation",
            "status": "ready",
            "scope": "Validate quiet-or-active liquidity gate on pre-2021 or future forward buy orders without retuning.",
        },
        {
            "priority": 2,
            "queue_id": "v5h_pit_market_cap_segmentation_data_gate",
            "status": "ready",
            "scope": "Add PIT-clean market cap/free-float cap panel before testing size segmentation.",
        },
        {
            "priority": 3,
            "queue_id": "v5h_sleeve_specific_execution_policy_spec",
            "status": "diagnostic_only",
            "scope": "Only open if independent validation confirms sleeve/liquidity heterogeneity.",
        },
    ]


def _report(
    metrics: list[dict[str, Any]],
    segment_tables: dict[str, list[dict[str, Any]]],
    candidate_matrix: list[dict[str, Any]],
    market_cap_gate: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    lines = [
        "# V5h Segmented 1min Execution Diagnostic",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        "- Scope: V5f champion planned buy/increase orders only.",
        "- Purpose: test whether 1min execution should be segmented by sleeve, intraday liquidity, or size.",
        "",
        "## Variant Results",
        "",
    ]
    for row in metrics:
        if row["version_id"] in {REPAIRED_BASELINE, V5F_PRIMARY}:
            continue
        lines.append(
            f"- `{row['version_id']}`: return `{_float(row['strategy_return']) * 100:.4f}%`, delta vs V5f `{_float(row['delta_return_pct_points_vs_v5f_primary']):.4f}` pct, delta vs global v1 `{_float(row['delta_return_pct_points_vs_global_v1']):.4f}` pct."
        )
    lines.extend(["", "## Key Segment Read", ""])
    for row in segment_tables["liquidity"]:
        lines.append(
            f"- 10:00 liquidity `{row['decision_10am_amount_intensity_bucket']}`: n={row['order_count']}, adjustment `{_float(row['execution_adjustment_total_pct_points']):.4f}` pct, status `{row['diagnostic_status']}`."
        )
    lines.extend(
        [
            "",
            "## Market Cap Gate",
            f"- `{market_cap_gate[0]['status']}`: {market_cap_gate[0]['value']}",
            "",
            "Segmented versions are diagnostic only because the segmentation itself is read from the backtest period. The clean next step is independent validation, especially for the liquidity quiet-or-active gate.",
            "",
        ]
    )
    return "\n".join(lines)


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5h Segmented 1min Execution Diagnostic Rules",
            "",
            "- Do not modify V57f core or V5f mainline.",
            "- Do not change sell/decrease timing.",
            "- Do not create new buy signals or increase trading frequency.",
            "- Do not promote segmented rules from the 2021-2026 backtest alone.",
            "- Market-cap segmentation requires PIT-clean market cap/free-float cap data first.",
            "- Keep all outputs diagnostic unless independently validated.",
            "",
        ]
    )


def _segment_status(order_count: int, total_adj: float) -> str:
    if order_count < 30:
        return "small_sample_diagnostic"
    if total_adj > 0:
        return "positive_segment"
    if total_adj < 0:
        return "negative_segment"
    return "flat_segment"


def _best_segmented(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [
        row
        for row in metrics
        if row["version_id"].startswith("v5h_segment_")
    ]
    return max(eligible, key=lambda row: _float(row.get("delta_return_pct_points_vs_v5f_primary"))) if eligible else {}


def _find(rows: list[dict[str, Any]], version_id: str) -> dict[str, Any]:
    return next((row for row in rows if row.get("version_id") == version_id), {})


def _blocker(blocker_id: str, description: str) -> dict[str, Any]:
    return {"blocker_id": blocker_id, "severity": "fatal", "status": "blocking", "description": description}


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5h_segmented_1min_execution_diagnostic",
        "v5h_line_id": V5H_LINE_ID,
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


def _max_drawdown(navs: list[float]) -> float:
    peak = 0.0
    max_dd = 0.0
    for nav in navs:
        peak = max(peak, nav)
        if peak:
            max_dd = min(max_dd, nav / peak - 1.0)
    return abs(max_dd)


def _mean(values: list[Any]) -> float:
    clean = [_float(value) for value in values if value not in (None, "")]
    return sum(clean) / len(clean) if clean else 0.0


def _float(value: Any) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else 0.0
    except Exception:
        return 0.0


def main() -> None:
    summary = run_v5h_segmented_1min_execution_diagnostic(Path("."))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

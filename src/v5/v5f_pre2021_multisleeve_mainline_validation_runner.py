from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5f_pre2021_multisleeve_mainline_validation") / "current"
DATA_GATE_DIR = Path("v5f_pre2021_repaired_multisleeve_data_gate") / "current"
SPIKE_DIR = Path("v5f_spike_funded_mr_borrowing_independent_validation_gate") / "current"
JQ_SIM_DIR = Path("v5f_spike_mr_prebacktest_to_backtest_jq_sim") / "current"
PRICE_ROOT = Path("数据库") / "processed" / "startup_preload_repaired_prices_v5"

BASELINE = "pre2021_repaired_multisleeve_equal_sleeve_baseline_proxy"
PRIMARY = "internal_subsleeve_mom12_70_30"
PRE2021_START = "2019-04-01"
PRE2021_END = "2020-12-31"
FORMAL_BACKTEST_START = "2021-05-01"
FORMAL_BACKTEST_END = "2026-05-31"
COMMISSION_RATE = 0.0003

PRICE_FILES = {
    "bank": "bank_v3_startup_repaired_daily_prices.csv",
    "utilities_electricity": "utilities_v51f_startup_repaired_daily_prices.csv",
    "highway_infrastructure": "highway_v54h_startup_repaired_daily_prices.csv",
    "port_rail_infrastructure": "port_rail_v55j_startup_repaired_daily_prices.csv",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_v5f_pre2021_multisleeve_mainline_validation(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        summary = _summary("blocked_missing_required_inputs", "blocked_missing_required_inputs", blockers)
        _write_json(out / "v5f_pre2021_validation_summary.json", summary)
        _write_csv(out / "v5f_pre2021_validation_blockers.csv", blockers)
        return summary

    data_gate_summary = _read_json(root / DATA_GATE_DIR / "v5f_pre2021_data_gate_summary.json")
    panel_coverage = _read_csv(root / DATA_GATE_DIR / "v5f_pre2021_multisleeve_panel_coverage.csv")
    required_fields = _read_csv(root / DATA_GATE_DIR / "v5f_pre2021_required_field_coverage.csv")
    price_coverage = _read_csv(root / DATA_GATE_DIR / "v5f_pre2021_price_coverage.csv")
    preview = pd.read_csv(root / DATA_GATE_DIR / "v5f_pre2021_candidate_signal_preview.csv", dtype={"preview_date": str, "code": str})
    spike_summary = _read_json(root / SPIKE_DIR / "v5f_spike_mr_validation_summary.json")
    spike_metrics = _read_csv(root / SPIKE_DIR / "v5f_spike_mr_validation_metrics.csv")
    jq_sim_summary = _read_json(root / JQ_SIM_DIR / "v5f_spike_mr_prebacktest_to_backtest_jq_sim_summary.json")

    prices = _load_prices(root)
    pool_truth = _pool_truth_table(data_gate_summary, panel_coverage, price_coverage, preview)
    field_audit = _field_audit(required_fields)
    weights = _build_weights(preview, prices)
    daily = _daily_returns(weights, prices)
    metrics = _metrics(daily)
    yearly = _yearly(daily)
    pool_audit = _pool_boundary_audit(preview, weights)
    pit_audit = _pit_governance_audit(data_gate_summary, field_audit)
    spike = _spike_reclassification(spike_summary, spike_metrics, jq_sim_summary)
    decision = _pm_gate_decision(metrics, pool_truth, pit_audit, spike)
    next_queue = _next_queue(decision)
    blockers_out = _blockers(pool_truth, pit_audit, spike)

    _write_csv(out / "v5f_pre2021_p0_pool_truth_table.csv", pool_truth)
    _write_csv(out / "v5f_pre2021_p0_required_field_audit.csv", field_audit)
    _write_csv(out / "v5f_pre2021_p0_stock_pool_boundary_audit.csv", pool_audit)
    _write_csv(out / "v5f_pre2021_p1_mainline_weights.csv", weights)
    _write_csv(out / "v5f_pre2021_p1_daily_returns.csv", daily)
    _write_csv(out / "v5f_pre2021_p1_metrics.csv", metrics)
    _write_csv(out / "v5f_pre2021_p1_yearly.csv", yearly)
    _write_csv(out / "v5f_pre2021_p1_pit_governance_audit.csv", pit_audit)
    _write_csv(out / "v5f_pre2021_p2_spike_reversion_reclassification.csv", spike)
    _write_csv(out / "v5f_pre2021_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_pre2021_next_queue.csv", next_queue)
    _write_csv(out / "v5f_pre2021_validation_blockers.csv", blockers_out)
    (out / "v5f_pre2021_validation_report.md").write_text(
        _report(pool_truth, metrics, yearly, spike, decision),
        encoding="utf-8",
    )
    (out / "v5f_pre2021_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    primary_row = next(row for row in metrics if row["version_id"] == PRIMARY)
    summary = _summary(
        "completed_pre2021_p0_p1_p2_validation",
        decision[0]["pm_gate_decision"],
        blockers_out,
        p0_sector_count=len(pool_truth),
        p1_delta_return_pct_points=float(primary_row["delta_return_pct_points_vs_pre2021_baseline"]),
        p1_delta_max_drawdown_pct_points=float(primary_row["delta_max_drawdown_pct_points_vs_pre2021_baseline"]),
        p2_best_net_incremental_return_pct_points=float(spike[0]["limited_2020q4_best_net_incremental_return_pct_points"]),
    )
    _write_json(out / "v5f_pre2021_validation_summary.json", summary)
    return summary


def _load_prices(root: Path) -> pd.DataFrame:
    frames = []
    for sector, file_name in PRICE_FILES.items():
        path = root / PRICE_ROOT / file_name
        frame = pd.read_csv(path, dtype={"date": str, "code": str})
        frame["sector_id"] = sector
        frames.append(frame)
    prices = pd.concat(frames, ignore_index=True).drop_duplicates(["date", "code"])
    prices = prices.sort_values(["code", "date"]).reset_index(drop=True)
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
    prices["next_close"] = prices.groupby("code")["close"].shift(-1)
    prices["stock_return"] = prices["next_close"] / prices["close"] - 1.0
    prices["close_lag_21"] = prices.groupby("code")["close"].shift(21)
    prices["close_lag_253"] = prices.groupby("code")["close"].shift(253)
    prices["mom_12_1"] = prices["close_lag_21"] / prices["close_lag_253"] - 1.0
    return prices


def _pool_truth_table(
    summary: dict[str, Any],
    panel_coverage: list[dict[str, str]],
    price_coverage: list[dict[str, str]],
    preview: pd.DataFrame,
) -> list[dict[str, Any]]:
    price_by_sector = {row["sector_id"]: row for row in price_coverage}
    rows = []
    for row in panel_coverage:
        sector = row["sector_id"]
        sector_preview = preview[preview["sector_id"] == sector]
        price_row = price_by_sector.get(sector, {})
        rows.append(
            {
                "sector_id": sector,
                "panel_source_scope": row.get("panel_source_scope", ""),
                "panel_exists": row.get("exists", ""),
                "panel_row_count": row.get("row_count", ""),
                "pre2021_row_count": row.get("pre2021_row_count", ""),
                "pre2021_date_count": row.get("pre2021_date_count", ""),
                "pre2021_code_count": row.get("pre2021_code_count", ""),
                "candidate_preview_rows": len(sector_preview),
                "candidate_preview_dates": sector_preview["preview_date"].nunique(),
                "candidate_preview_codes": sector_preview["code"].nunique(),
                "price_pre2021_row_count": price_row.get("pre2021_row_count", ""),
                "price_pre2021_date_count": price_row.get("pre2021_date_count", ""),
                "price_pre2021_code_count": price_row.get("pre2021_code_count", ""),
                "coverage_status": row.get("coverage_status", ""),
                "complete_v57f_equivalent": False,
                "pre2021_limited_validation_ready": row.get("coverage_status", "").startswith("pass") and len(sector_preview) > 0,
                "accepted": False,
            }
        )
    return rows


def _field_audit(required_fields: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in required_fields:
        rows.append(
            {
                "sector_id": row.get("sector_id", ""),
                "field": row.get("field", ""),
                "field_exists": row.get("field_exists", ""),
                "pre2021_nonempty_rows": row.get("pre2021_nonempty_rows", ""),
                "pre2021_nonempty_dates": row.get("pre2021_nonempty_dates", ""),
                "field_status": row.get("field_status", ""),
                "usable_for_p1_mainline": row.get("field", "") in {"low_vol_score", "volatility_120d", "dividend_yield"},
                "accepted": False,
            }
        )
    return rows


def _build_weights(preview: pd.DataFrame, prices: pd.DataFrame) -> list[dict[str, Any]]:
    feature_map = prices.set_index(["date", "code"])["mom_12_1"].to_dict()
    rows: list[dict[str, Any]] = []
    for date, group in preview.groupby("preview_date", sort=True):
        group = group.copy()
        group["mom_12_1"] = [_safe_float(feature_map.get((date, code))) for code in group["code"]]
        sectors = sorted(group["sector_id"].unique())
        sleeve_total = 1.0 / len(sectors) if sectors else 0.0
        base_weights = {}
        for sector, sector_df in group.groupby("sector_id", sort=True):
            base = sleeve_total / len(sector_df) if len(sector_df) else 0.0
            for _, item in sector_df.iterrows():
                base_weights[item["code"]] = base
                rows.append(
                    _weight_row(
                        BASELINE,
                        "pre2021_baseline_proxy",
                        date,
                        item,
                        base,
                        base,
                        "baseline",
                        momentum_valid=False,
                    )
                )
        primary_targets = _internal_subsleeve_targets(group, base_weights, sleeve_total)
        for _, item in group.iterrows():
            base = float(base_weights[item["code"]])
            target, bucket, valid = primary_targets[item["code"]]
            rows.append(
                _weight_row(
                    PRIMARY,
                    "pre2021_internal_subsleeve_momentum",
                    date,
                    item,
                    base,
                    target,
                    bucket,
                    momentum_valid=valid,
                )
            )
    return rows


def _internal_subsleeve_targets(group: pd.DataFrame, base_weights: dict[str, float], sleeve_total: float) -> dict[str, tuple[float, str, bool]]:
    targets: dict[str, tuple[float, str, bool]] = {}
    for _, sector_df in group.groupby("sector_id", sort=True):
        valid = sector_df.dropna(subset=["mom_12_1"])
        if valid.empty:
            for _, row in sector_df.iterrows():
                base = float(base_weights[row["code"]])
                targets[row["code"]] = (base, "momentum_unavailable_hold_baseline", False)
            continue
        top_count = max(1, math.ceil(len(valid) / 3))
        top_codes = set(valid.sort_values("mom_12_1", ascending=False).head(top_count)["code"].tolist())
        for _, row in sector_df.iterrows():
            base = float(base_weights[row["code"]])
            target = 0.70 * base
            bucket = "core_70pct"
            if row["code"] in top_codes:
                target += 0.30 * sleeve_total / len(top_codes)
                bucket = "momentum_subsleeve_30pct"
            targets[row["code"]] = (target, bucket, True)
    return targets


def _weight_row(
    version: str,
    family: str,
    date: str,
    item: pd.Series,
    base_weight: float,
    target_weight: float,
    bucket: str,
    momentum_valid: bool,
) -> dict[str, Any]:
    return {
        "version_id": version,
        "family": family,
        "rebalance_date": date,
        "code": item["code"],
        "sector_id": item["sector_id"],
        "selected_rank": item.get("selected_rank", ""),
        "base_target_weight": base_weight,
        "target_weight": target_weight,
        "weight_delta": target_weight - base_weight,
        "mom_12_1": item.get("mom_12_1", ""),
        "bucket": bucket,
        "momentum_feature_valid": momentum_valid,
        "new_stock_selected": False,
        "accepted": False,
    }


def _daily_returns(weights: list[dict[str, Any]], prices: pd.DataFrame) -> list[dict[str, Any]]:
    ret_map = prices.set_index(["date", "code"])["stock_return"].to_dict()
    date_min = min(row["rebalance_date"] for row in weights)
    dates = sorted(date for date in prices["date"].unique() if PRE2021_START <= date <= PRE2021_END and date >= date_min)
    rebalances = sorted({row["rebalance_date"] for row in weights})
    by_version_date: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in weights:
        by_version_date.setdefault((row["version_id"], row["rebalance_date"]), []).append(row)

    rows = []
    baseline_daily: dict[str, float] = {}
    baseline_nav = 1.0
    baseline_active: list[dict[str, Any]] = []
    baseline_rebalance = ""
    for day in dates:
        if day in rebalances:
            baseline_active = by_version_date.get((BASELINE, day), [])
            baseline_rebalance = day
        ret = sum(float(row["target_weight"]) * (_safe_float(ret_map.get((day, row["code"]))) or 0.0) for row in baseline_active)
        baseline_nav *= 1.0 + ret
        baseline_daily[day] = ret
        rows.append(
            {
                "trade_date": day,
                "version_id": BASELINE,
                "active_rebalance_date": baseline_rebalance,
                "strategy_return": ret,
                "strategy_nav": baseline_nav,
                "baseline_return": ret,
                "delta_stock_return": 0.0,
                "incremental_commission": 0.0,
                "turnover_proxy": 0.0,
                "accepted": False,
            }
        )

    primary_nav = 1.0
    primary_active: list[dict[str, Any]] = []
    previous_target: dict[str, float] = {}
    primary_rebalance = ""
    for day in dates:
        commission = 0.0
        turnover = 0.0
        if day in rebalances:
            primary_active = by_version_date.get((PRIMARY, day), [])
            primary_rebalance = day
            target = {row["code"]: float(row["target_weight"]) for row in primary_active}
            base = {row["code"]: float(row["base_target_weight"]) for row in primary_active}
            turnover = sum(abs(target.get(code, 0.0) - previous_target.get(code, 0.0)) for code in set(target) | set(previous_target))
            base_turnover = sum(abs(base.get(code, 0.0) - previous_target.get(code, 0.0)) for code in set(base) | set(previous_target))
            commission = max(0.0, turnover - base_turnover) * COMMISSION_RATE
            previous_target = target
        delta = sum(float(row["weight_delta"]) * (_safe_float(ret_map.get((day, row["code"]))) or 0.0) for row in primary_active)
        ret = baseline_daily[day] + delta - commission
        primary_nav *= 1.0 + ret
        rows.append(
            {
                "trade_date": day,
                "version_id": PRIMARY,
                "active_rebalance_date": primary_rebalance,
                "strategy_return": ret,
                "strategy_nav": primary_nav,
                "baseline_return": baseline_daily[day],
                "delta_stock_return": delta,
                "incremental_commission": commission,
                "turnover_proxy": turnover,
                "accepted": False,
            }
        )
    return rows


def _metrics(daily: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(daily)
    rows = []
    for version, group in df.groupby("version_id", sort=True):
        ordered = group.sort_values("trade_date")
        navs = pd.to_numeric(ordered["strategy_nav"]).tolist()
        rets = pd.to_numeric(ordered["strategy_return"]).tolist()
        ann = navs[-1] ** (252 / len(navs)) - 1.0
        vol = pd.Series(rets).std() * (252**0.5)
        rows.append(
            {
                "version_id": version,
                "strategy_return": navs[-1] - 1.0,
                "annualized_return": ann,
                "max_drawdown": _max_drawdown(navs),
                "volatility": vol,
                "sharpe_proxy": ann / vol if vol else 0.0,
                "incremental_commission_total": pd.to_numeric(ordered["incremental_commission"]).sum(),
                "turnover_proxy": pd.to_numeric(ordered["turnover_proxy"]).sum(),
                "accepted": False,
            }
        )
    baseline = next(row for row in rows if row["version_id"] == BASELINE)
    for row in rows:
        row["delta_return_pct_points_vs_pre2021_baseline"] = (float(row["strategy_return"]) - float(baseline["strategy_return"])) * 100
        row["delta_max_drawdown_pct_points_vs_pre2021_baseline"] = (float(row["max_drawdown"]) - float(baseline["max_drawdown"])) * 100
    return sorted(rows, key=lambda row: row["version_id"] != PRIMARY)


def _yearly(daily: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(daily)
    df["year"] = df["trade_date"].str.slice(0, 4)
    rows = []
    for (version, year), group in df.groupby(["version_id", "year"], sort=True):
        rows.append(
            {
                "version_id": version,
                "year": year,
                "period_return": (1.0 + pd.to_numeric(group["strategy_return"])).prod() - 1.0,
                "trade_days": len(group),
                "accepted": False,
            }
        )
    base = {row["year"]: row["period_return"] for row in rows if row["version_id"] == BASELINE}
    for row in rows:
        row["delta_return_pct_points_vs_pre2021_baseline"] = (float(row["period_return"]) - float(base.get(row["year"], 0.0))) * 100
    return rows


def _pool_boundary_audit(preview: pd.DataFrame, weights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    preview_keys = set(zip(preview["preview_date"], preview["code"]))
    weight_keys = {(row["rebalance_date"], row["code"]) for row in weights}
    primary = [row for row in weights if row["version_id"] == PRIMARY]
    return [
        {"audit_id": "v57f_repaired_pool_only", "status": "pass" if weight_keys == preview_keys else "fail", "detail": len(weight_keys - preview_keys)},
        {"audit_id": "no_full_market_selection", "status": "pass", "detail": True},
        {"audit_id": "no_new_stock_selected", "status": "pass" if not any(row["new_stock_selected"] for row in primary) else "fail", "detail": 0},
        {"audit_id": "sleeve_internal_only", "status": "pass", "detail": "internal_subsleeve weights only within existing sector_id"},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
    ]


def _pit_governance_audit(summary: dict[str, Any], field_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    missing_mainline = [row for row in field_audit if row["usable_for_p1_mainline"] and not str(row["field_status"]).startswith("pass")]
    return [
        {"audit_id": "pre2021_pool_ready", "status": "pass" if summary.get("pre2021_multisleeve_pool_status") == "pre2021_multisleeve_pool_ready" else "fail", "detail": summary.get("pre2021_multisleeve_pool_status")},
        {"audit_id": "formal_backtest_not_used_for_discovery", "status": "pass", "detail": f"{FORMAL_BACKTEST_START}_to_{FORMAL_BACKTEST_END}_excluded"},
        {"audit_id": "mainline_required_daily_fields", "status": "pass" if not missing_mainline else "fail", "detail": len(missing_mainline)},
        {"audit_id": "threshold_scan_used_false", "status": "pass", "detail": False},
        {"audit_id": "joinquant_started_false", "status": "pass", "detail": False},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
    ]


def _spike_reclassification(summary: dict[str, Any], metrics: list[dict[str, str]], jq_summary: dict[str, Any]) -> list[dict[str, Any]]:
    best = max(metrics, key=lambda row: _safe_float(row.get("net_incremental_return_pct_points")) or -999.0)
    return [
        {
            "component": "pre2021_5min_spike_reversion_independent_validation",
            "source_window": f"{summary.get('validation_window_start')}_to_{summary.get('validation_window_end')}",
            "source_classification": summary.get("validation_window_classification"),
            "limited_2020q4_directional_pass": summary.get("limited_2020q4_directional_pass", False),
            "formal_independent_pass": summary.get("independent_validation_pass", False),
            "formal_promotion_allowed": summary.get("formal_promotion_allowed", False),
            "limited_2020q4_best_variant": summary.get("best_variant", best.get("version_id", "")),
            "limited_2020q4_best_net_incremental_return_pct_points": summary.get("best_net_incremental_return_pct_points", best.get("net_incremental_return_pct_points", 0)),
            "limited_2020q4_best_win_rate": summary.get("best_win_rate", best.get("win_rate", 0)),
            "backtest_scope_positive_delta_pct_points": jq_summary.get("backtest_delta_vs_primary_pct_points", ""),
            "status": "observation_only_not_candidate",
            "accepted": False,
        }
    ]


def _pm_gate_decision(
    metrics: list[dict[str, Any]],
    pool_truth: list[dict[str, Any]],
    pit_audit: list[dict[str, Any]],
    spike: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    primary = next(row for row in metrics if row["version_id"] == PRIMARY)
    gov_ok = all(row["status"] == "pass" for row in pit_audit)
    pool_ready = all(row["pre2021_limited_validation_ready"] for row in pool_truth)
    delta = float(primary["delta_return_pct_points_vs_pre2021_baseline"])
    dd_delta = float(primary["delta_max_drawdown_pct_points_vs_pre2021_baseline"])
    if not gov_ok or not pool_ready:
        gate = "pre2021_validation_blocked_by_pool_or_pit"
        next_action = "repair pre2021 PIT pool before model interpretation"
    elif delta > 0 and dd_delta <= 0:
        gate = "pre2021_mainline_positive_supports_v5f_forward_tracking_not_accepted"
        next_action = "continue V5f forward/paper tracking; do not mark accepted"
    elif delta > 0:
        gate = "pre2021_mainline_positive_with_drawdown_cost_keep_forward_tracking_not_accepted"
        next_action = "continue observation; compare drawdown and execution before promotion"
    else:
        gate = "pre2021_mainline_no_independent_edge_keep_current_forward_only"
        next_action = "do not promote based on pre2021 proxy"
    return [
        {
            "pm_gate_decision": gate,
            "p0_pool_status": "limited_proxy_pool_ready" if pool_ready else "pool_needs_repair",
            "p1_mainline_delta_return_pct_points": delta,
            "p1_mainline_delta_max_drawdown_pct_points": dd_delta,
            "p2_spike_status": spike[0]["status"],
            "p2_formal_independent_pass": spike[0]["formal_independent_pass"],
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "next_action": next_action,
        }
    ]


def _next_queue(decision: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"priority": "P0", "task_id": "continue_internal_subsleeve_mom12_70_30_forward_paper_tracking", "status": "ready", "reason": decision[0]["pm_gate_decision"]},
        {"priority": "P1", "task_id": "extend_pre2021_repaired_pool_beyond_2019_if_source_equivalent", "status": "optional", "reason": "current P1 is limited proxy, not full V57f-equivalent"},
        {"priority": "P2", "task_id": "source_full_pre2021_5min_for_spike_only_if_needed", "status": "optional_blocked_by_data_value_tradeoff", "reason": "spike line is observation only"},
    ]


def _blockers(pool_truth: list[dict[str, Any]], pit_audit: list[dict[str, Any]], spike: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for row in pool_truth:
        if not row["pre2021_limited_validation_ready"]:
            blockers.append({"blocker_id": "pre2021_pool_not_ready", "severity": "fatal", "scope": row["sector_id"], "detail": row["coverage_status"]})
    for row in pit_audit:
        if row["status"] != "pass":
            blockers.append({"blocker_id": row["audit_id"], "severity": "fatal", "scope": "pit_governance", "detail": row["detail"]})
    if not spike[0]["formal_independent_pass"]:
        blockers.append({"blocker_id": "spike_reversion_not_formal_independent_pass", "severity": "nonfatal", "scope": "P2", "detail": spike[0]["source_classification"]})
    return blockers or [{"blocker_id": "none", "severity": "none", "scope": "", "detail": "validation packet completed"}]


def _summary(
    status: str,
    decision: str,
    blockers: list[dict[str, Any]],
    p0_sector_count: int = 0,
    p1_delta_return_pct_points: float = 0.0,
    p1_delta_max_drawdown_pct_points: float = 0.0,
    p2_best_net_incremental_return_pct_points: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_pre2021_multisleeve_mainline_validation",
        "status": status,
        "pre2021_validation_start": PRE2021_START,
        "pre2021_validation_end": PRE2021_END,
        "formal_backtest_scope_start": FORMAL_BACKTEST_START,
        "formal_backtest_scope_end": FORMAL_BACKTEST_END,
        "p0_sector_count": p0_sector_count,
        "p1_mainline": PRIMARY,
        "p1_delta_return_pct_points_vs_pre2021_baseline": p1_delta_return_pct_points,
        "p1_delta_max_drawdown_pct_points_vs_pre2021_baseline": p1_delta_max_drawdown_pct_points,
        "p2_best_net_incremental_return_pct_points": p2_best_net_incremental_return_pct_points,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "joinquant_started": False,
        "fatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "fatal"),
        "nonfatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "nonfatal"),
        "pm_gate_decision": decision,
    }


def _report(
    pool_truth: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
    yearly: list[dict[str, Any]],
    spike: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    primary = next(row for row in metrics if row["version_id"] == PRIMARY)
    baseline = next(row for row in metrics if row["version_id"] == BASELINE)
    return "\n".join(
        [
            "# V5f Pre-2021 Multisleeve Mainline Validation",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- P1 mainline: `{PRIMARY}`",
            "- Status: limited proxy validation only; not accepted.",
            "",
            "## P0 Pool",
            f"- Sectors: `{len(pool_truth)}`",
            f"- Ready sectors: `{sum(1 for row in pool_truth if row['pre2021_limited_validation_ready'])}`",
            "- Full V57f equivalence: `False`.",
            "",
            "## P1 Mainline",
            f"- Baseline return: `{float(baseline['strategy_return']) * 100:.4f}%`",
            f"- Mainline return: `{float(primary['strategy_return']) * 100:.4f}%`",
            f"- Delta return: `{float(primary['delta_return_pct_points_vs_pre2021_baseline']):+.4f}` pct points.",
            f"- Delta max drawdown: `{float(primary['delta_max_drawdown_pct_points_vs_pre2021_baseline']):+.4f}` pct points.",
            "",
            "## Yearly",
            *[
                f"- {row['year']} `{row['version_id']}`: return={float(row['period_return']) * 100:.4f}%, delta={float(row['delta_return_pct_points_vs_pre2021_baseline']):+.4f} pct"
                for row in yearly
            ],
            "",
            "## P2 Spike/Reversion",
            f"- Status: `{spike[0]['status']}`",
            f"- 2020Q4 directional pass: `{spike[0]['limited_2020q4_directional_pass']}`",
            f"- Formal independent pass: `{spike[0]['formal_independent_pass']}`",
            f"- Best limited net incremental return: `{float(spike[0]['limited_2020q4_best_net_incremental_return_pct_points']):+.4f}` pct points.",
            "",
        ]
    )


def _rules() -> str:
    return """# Agent Execution Rules

- P0: use only PIT-clean/repaired pre-2021 local pools.
- P1: test only `internal_subsleeve_mom12_70_30`; no variants and no threshold scan.
- P2: reclassify existing 2020Q4 5min spike/reversion validation; do not promote.
- Do not modify V57f, use full-market selection, start JoinQuant, or mark accepted.
"""


def _max_drawdown(navs: list[float]) -> float:
    peak = 0.0
    max_dd = 0.0
    for nav in navs:
        peak = max(peak, nav)
        if peak:
            max_dd = min(max_dd, nav / peak - 1.0)
    return abs(max_dd)


def _safe_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        DATA_GATE_DIR / "v5f_pre2021_data_gate_summary.json",
        DATA_GATE_DIR / "v5f_pre2021_multisleeve_panel_coverage.csv",
        DATA_GATE_DIR / "v5f_pre2021_required_field_coverage.csv",
        DATA_GATE_DIR / "v5f_pre2021_price_coverage.csv",
        DATA_GATE_DIR / "v5f_pre2021_candidate_signal_preview.csv",
        SPIKE_DIR / "v5f_spike_mr_validation_summary.json",
        SPIKE_DIR / "v5f_spike_mr_validation_metrics.csv",
        JQ_SIM_DIR / "v5f_spike_mr_prebacktest_to_backtest_jq_sim_summary.json",
    ] + [PRICE_ROOT / file_name for file_name in PRICE_FILES.values()]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "path": str(path), "required_action": "restore local pre2021 artifacts"}
        for path in required
        if not (root / path).exists()
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    summary = run_v5f_pre2021_multisleeve_mainline_validation(Path(args.root))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

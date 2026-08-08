from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd


OUT_DIR = Path("v5h_quiet_or_active_independent_validation") / "current"
SEGMENTED_DIR = Path("v5h_segmented_1min_execution_diagnostic") / "current"
PRE2021_DIR = Path("v5f_pre2021_multisleeve_mainline_validation") / "current"

SEGMENTED_SUMMARY = SEGMENTED_DIR / "v5h_segmented_execution_summary.json"
PRE2021_SUMMARY = PRE2021_DIR / "v5f_pre2021_validation_summary.json"
PRE2021_WEIGHTS = PRE2021_DIR / "v5f_pre2021_p1_mainline_weights.csv"
PRE2021_DAILY = PRE2021_DIR / "v5f_pre2021_p1_daily_returns.csv"

ONE_MIN_DATASET = "local_1min_clean_2013_2026"
ONE_MIN_MANIFEST = Path("manifests") / ONE_MIN_DATASET / "collection_manifest.json"

PRE2021_START = "2013-01-01"
PRE2021_END = "2021-04-30"
AVAILABLE_PRE2021_START = "2019-04-01"
AVAILABLE_PRE2021_END = "2020-12-31"
FORMAL_BACKTEST_START = "2021-05-01"
FORMAL_BACKTEST_END = "2026-05-31"

PRIMARY = "internal_subsleeve_mom12_70_30"
PRE2021_BASELINE = "pre2021_repaired_multisleeve_equal_sleeve_baseline_proxy"
GLOBAL_V1 = "pre2021_global_pressure_positive_1000_else_1400"
QUIET_OR_ACTIVE = "pre2021_liquidity_quiet_or_active_gate"
QUIET_ONLY = "pre2021_liquidity_quiet_only_gate"
ACTIVE_ONLY = "pre2021_liquidity_active_only_gate"
DEFAULT_1000 = "pre2021_default_1000_reference"

PRIMARY_SCOPE = "pre2021_champion_increase_vs_previous"
SUPPLEMENTAL_SCOPE = "pre2021_overlay_positive_delta"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5h_quiet_or_active_independent_validation(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        summary = _summary("blocked_missing_required_input", "blocked_until_required_inputs_available", blockers)
        _write_json(out / "v5h_quiet_or_active_independent_summary.json", summary)
        _write_csv(out / "v5h_quiet_or_active_independent_blockers.csv", blockers)
        return summary

    db = _find_v5_database(root)
    manifest = _read_json(db / ONE_MIN_MANIFEST)
    segmented_summary = _read_json(root / SEGMENTED_SUMMARY)
    pre2021_summary = _read_json(root / PRE2021_SUMMARY)
    weights = pd.read_csv(root / PRE2021_WEIGHTS, dtype={"rebalance_date": str, "code": str, "version_id": str})
    daily = pd.read_csv(root / PRE2021_DAILY, dtype={"trade_date": str, "version_id": str, "active_rebalance_date": str})

    source_orders = _source_orders(weights)
    day_cache = _load_days(db, [(row["code"], row["trade_date"]) for row in source_orders])
    order_panel, read_audit = _order_panel(source_orders, day_cache)
    segment_result = _segment_result(order_panel)
    adjustment_by_date = _adjustment_by_date(order_panel, _variants(), PRIMARY_SCOPE)
    nav_rows = _daily_nav(daily, adjustment_by_date)
    metrics = _metrics(nav_rows)
    scope_metrics = _scope_metrics(order_panel)
    data_gate = _data_gate(manifest, segmented_summary, pre2021_summary, source_orders, order_panel, read_audit)
    governance = _governance_audit()
    decision = _pm_decision(metrics, data_gate, governance, order_panel)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(data_gate, governance)

    _write_csv(out / "v5h_quiet_or_active_independent_order_panel.csv", order_panel)
    _write_csv(out / "v5h_quiet_or_active_independent_read_audit.csv", read_audit)
    _write_csv(out / "v5h_quiet_or_active_independent_segment_result.csv", segment_result)
    _write_csv(out / "v5h_quiet_or_active_independent_scope_metrics.csv", scope_metrics)
    _write_csv(out / "v5h_quiet_or_active_independent_adjustment_by_date.csv", adjustment_by_date)
    _write_csv(out / "v5h_quiet_or_active_independent_daily_nav.csv", nav_rows)
    _write_csv(out / "v5h_quiet_or_active_independent_variant_metrics.csv", metrics)
    _write_csv(out / "v5h_quiet_or_active_independent_data_gate.csv", data_gate)
    _write_csv(out / "v5h_quiet_or_active_independent_governance_audit.csv", governance)
    _write_csv(out / "v5h_quiet_or_active_independent_pm_gate_decision.csv", decision)
    _write_csv(out / "v5h_quiet_or_active_independent_next_queue.csv", next_queue)
    _write_csv(out / "v5h_quiet_or_active_independent_blockers.csv", blockers_out)
    (out / "v5h_quiet_or_active_independent_report.md").write_text(
        _report(metrics, segment_result, scope_metrics, data_gate, decision),
        encoding="utf-8",
    )
    (out / "v5h_quiet_or_active_independent_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    quiet = _find(metrics, QUIET_OR_ACTIVE)
    global_v1 = _find(metrics, GLOBAL_V1)
    primary = _find(metrics, PRIMARY)
    summary = _summary(
        "completed_quiet_or_active_independent_validation",
        decision[0]["pm_gate_decision"],
        [],
        validation_scope=PRIMARY_SCOPE,
        available_validation_start=AVAILABLE_PRE2021_START,
        available_validation_end=AVAILABLE_PRE2021_END,
        formal_backtest_start=FORMAL_BACKTEST_START,
        formal_backtest_end=FORMAL_BACKTEST_END,
        source_order_count=len(source_orders),
        primary_scope_order_count=sum(1 for row in order_panel if row["validation_scope"] == PRIMARY_SCOPE),
        diagnosed_order_count=len(order_panel),
        diagnosed_trade_date_count=len({row["trade_date"] for row in order_panel}),
        quiet_or_active_return_pct=round(_float(quiet.get("strategy_return")) * 100.0, 6),
        primary_return_pct=round(_float(primary.get("strategy_return")) * 100.0, 6),
        quiet_or_active_delta_return_pct_points_vs_pre2021_primary=round(_float(quiet.get("delta_return_pct_points_vs_pre2021_primary")), 6),
        quiet_or_active_delta_return_pct_points_vs_global_v1=round(
            (_float(quiet.get("strategy_return")) - _float(global_v1.get("strategy_return"))) * 100.0,
            6,
        ),
        quiet_or_active_execution_adjustment_pct_points=round(_float(quiet.get("execution_adjustment_total")) * 100.0, 6),
        independent_sample_power=decision[0]["sample_power"],
    )
    _write_json(out / "v5h_quiet_or_active_independent_summary.json", summary)
    return summary


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    missing = []
    try:
        db = _find_v5_database(root)
    except FileNotFoundError as exc:
        missing.append(_blocker("v5_database_missing", str(exc)))
        db = None
    for path in [SEGMENTED_SUMMARY, PRE2021_SUMMARY, PRE2021_WEIGHTS, PRE2021_DAILY]:
        if not (root / path).exists():
            missing.append(_blocker(f"missing_{path.name}", str(path)))
    if db is not None and not (db / ONE_MIN_MANIFEST).exists():
        missing.append(_blocker("missing_1min_manifest", str(db / ONE_MIN_MANIFEST)))
    return missing


def _source_orders(weights: pd.DataFrame) -> list[dict[str, Any]]:
    primary = weights[weights["version_id"].eq(PRIMARY)].copy()
    if primary.empty:
        return []
    for col in ["target_weight", "base_target_weight", "weight_delta", "mom_12_1"]:
        primary[col] = pd.to_numeric(primary[col], errors="coerce")
    rebalances = sorted(primary["rebalance_date"].dropna().unique())
    first_rebalance = rebalances[0] if rebalances else ""

    rows: list[dict[str, Any]] = []
    prev_target: dict[str, float] = {}
    for trade_date, group in primary.groupby("rebalance_date", sort=True):
        current_target = {str(row["code"]): _float(row["target_weight"]) for _, row in group.iterrows()}
        if trade_date != first_rebalance:
            for _, row in group.sort_values(["sector_id", "code"]).iterrows():
                code = str(row["code"])
                delta = _float(row["target_weight"]) - prev_target.get(code, 0.0)
                if delta > 1e-8:
                    rows.append(
                        _source_order_row(
                            row,
                            trade_date,
                            PRIMARY_SCOPE,
                            f"{PRIMARY_SCOPE}|{trade_date}|{code}",
                            delta,
                            "Full V5f champion target increase versus previous available pre-2021 rebalance.",
                        )
                    )
                overlay_delta = _float(row["weight_delta"])
                if overlay_delta > 1e-8:
                    rows.append(
                        _source_order_row(
                            row,
                            trade_date,
                            SUPPLEMENTAL_SCOPE,
                            f"{SUPPLEMENTAL_SCOPE}|{trade_date}|{code}",
                            overlay_delta,
                            "Supplemental momentum overweight relative to equal-sleeve baseline.",
                        )
                    )
        prev_target = current_target
    return rows


def _source_order_row(
    row: pd.Series,
    trade_date: str,
    validation_scope: str,
    intent_id: str,
    delta_weight: float,
    interpretation: str,
) -> dict[str, Any]:
    return {
        "intent_id": intent_id,
        "validation_scope": validation_scope,
        "trade_date": trade_date,
        "code": str(row["code"]),
        "sleeve": str(row["sector_id"]),
        "selected_rank": row.get("selected_rank", ""),
        "base_target_weight": _float(row.get("base_target_weight")),
        "target_weight": _float(row.get("target_weight")),
        "source_weight_delta": _float(row.get("weight_delta")),
        "trade_delta_weight_abs": abs(delta_weight),
        "mom_12_1": _float(row.get("mom_12_1")),
        "interpretation": interpretation,
        "accepted": False,
    }


def _load_days(db: Path, keys: list[tuple[str, str]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    wanted: dict[tuple[str, str], set[str]] = defaultdict(set)
    for code, trade_date in keys:
        if code and trade_date:
            wanted[(code, trade_date[:4])].add(trade_date)
    cache: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for (code, year), dates in sorted(wanted.items()):
        path = db / "processed" / ONE_MIN_DATASET / "by_year" / str(year) / f"{code.replace('.', '_')}_1min.csv"
        if not path.exists():
            continue
        by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                trade_date = str(row.get("trade_date", ""))
                if trade_date not in dates:
                    continue
                by_date[trade_date].append(
                    {
                        "time": str(row.get("time", "")),
                        "open": _float(row.get("open")),
                        "high": _float(row.get("high")),
                        "low": _float(row.get("low")),
                        "close": _float(row.get("close")),
                        "volume": _float(row.get("volume")),
                        "amount": _float(row.get("amount")),
                    }
                )
        for trade_date, rows in by_date.items():
            rows.sort(key=lambda item: item["time"])
            cache[(code, trade_date)] = rows
    return cache


def _order_panel(
    source_orders: list[dict[str, Any]],
    day_cache: dict[tuple[str, str], list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    read_audit: list[dict[str, Any]] = []
    for order in source_orders:
        day = day_cache.get((order["code"], order["trade_date"]))
        if not day:
            read_audit.append(
                {
                    "intent_id": order["intent_id"],
                    "code": order["code"],
                    "trade_date": order["trade_date"],
                    "status": "missing_1min_trade_date",
                    "one_min_bar_count": 0,
                }
            )
            continue
        obs_1000 = _features_at(day, "10:00:00")
        obs_1400 = _features_at(day, "14:00:00")
        if not obs_1000 or not obs_1400:
            read_audit.append(
                {
                    "intent_id": order["intent_id"],
                    "code": order["code"],
                    "trade_date": order["trade_date"],
                    "status": "missing_required_obs_time",
                    "one_min_bar_count": len(day),
                }
            )
            continue
        read_audit.append(
            {
                "intent_id": order["intent_id"],
                "code": order["code"],
                "trade_date": order["trade_date"],
                "status": "pass",
                "one_min_bar_count": len(day),
            }
        )
        day_close = day[-1]["close"]
        base_edge = _buy_edge(obs_1000["price_at_obs"], day_close)
        v1_selected = obs_1000 if obs_1000["amount_pressure_bucket"] == "positive_pressure" else obs_1400
        rows.append(
            {
                **order,
                "default_1000_price": obs_1000["price_at_obs"],
                "default_1000_action_edge_vs_close": base_edge,
                "fixed_1400_price": obs_1400["price_at_obs"],
                "fixed_1400_action_edge_vs_close": _buy_edge(obs_1400["price_at_obs"], day_close),
                "global_v1_selected_obs_time": v1_selected["obs_time"],
                "global_v1_action_edge_vs_close": _buy_edge(v1_selected["price_at_obs"], day_close),
                "decision_10am_amount_pressure_bucket": obs_1000["amount_pressure_bucket"],
                "decision_10am_amount_intensity_bucket": obs_1000["amount_intensity_bucket"],
                "decision_10am_volume_intensity_bucket": obs_1000["volume_intensity_bucket"],
                "decision_10am_amount_pressure_turn_bucket": obs_1000["amount_pressure_turn_bucket"],
                "decision_10am_price_vs_vwap_so_far": obs_1000["price_vs_vwap_so_far"],
                "day_close": day_close,
                "incremental_edge_global_v1_vs_default_10am": _buy_edge(v1_selected["price_at_obs"], day_close) - base_edge,
                "weighted_incremental_edge_global_v1_vs_default_10am": (
                    _buy_edge(v1_selected["price_at_obs"], day_close) - base_edge
                )
                * order["trade_delta_weight_abs"],
                "one_min_signal_is_pit": True,
                "diagnostic_only": True,
                "accepted": False,
            }
        )
    return rows, read_audit


def _features_at(day: list[dict[str, Any]], obs_time: str) -> dict[str, Any] | None:
    obs_index = next((index for index, row in enumerate(day) if row["time"] == obs_time), None)
    if obs_index is None:
        return None
    upto = day[: obs_index + 1]
    last15 = upto[-15:]
    prior = upto[:-15] if len(upto) > 15 else upto
    cum_amount = sum(row["amount"] for row in upto)
    cum_volume = sum(row["volume"] for row in upto)
    elapsed = max(len(upto), 1)
    avg_amount = cum_amount / elapsed
    avg_volume = cum_volume / elapsed
    price = upto[-1]["close"]
    vwap = cum_amount / cum_volume if cum_volume > 0 else price
    amount_pressure = _signed_pressure(upto, "amount")
    last15_pressure = _signed_pressure(last15, "amount")
    prior_pressure = _signed_pressure(prior, "amount")
    return {
        "obs_time": obs_time,
        "price_at_obs": price,
        "vwap_so_far": vwap,
        "price_vs_vwap_so_far": _ret(price, vwap),
        "last15_amount_intensity": _avg(last15, "amount") / avg_amount if avg_amount > 0 else 0.0,
        "last15_volume_intensity": _avg(last15, "volume") / avg_volume if avg_volume > 0 else 0.0,
        "amount_intensity_bucket": _intensity_bucket(_avg(last15, "amount") / avg_amount if avg_amount > 0 else 0.0),
        "volume_intensity_bucket": _intensity_bucket(_avg(last15, "volume") / avg_volume if avg_volume > 0 else 0.0),
        "amount_pressure_to_obs": amount_pressure,
        "amount_pressure_bucket": _pressure_bucket(amount_pressure),
        "amount_pressure_turn_bucket": _turn_bucket(last15_pressure - prior_pressure),
    }


def _variants() -> list[dict[str, Any]]:
    return [
        {"version_id": DEFAULT_1000, "condition": lambda row: False, "mode": "default"},
        {"version_id": GLOBAL_V1, "condition": lambda row: True, "mode": "global_v1"},
        {
            "version_id": QUIET_OR_ACTIVE,
            "condition": lambda row: row.get("decision_10am_amount_intensity_bucket") in {"quiet", "active"},
            "mode": "gated_v1",
        },
        {
            "version_id": QUIET_ONLY,
            "condition": lambda row: row.get("decision_10am_amount_intensity_bucket") == "quiet",
            "mode": "gated_v1",
        },
        {
            "version_id": ACTIVE_ONLY,
            "condition": lambda row: row.get("decision_10am_amount_intensity_bucket") == "active",
            "mode": "gated_v1",
        },
    ]


def _selected_adjustment(row: dict[str, Any], spec: dict[str, Any]) -> float:
    if spec["mode"] == "default":
        return 0.0
    if spec["mode"] == "global_v1":
        return _float(row.get("incremental_edge_global_v1_vs_default_10am"))
    condition: Callable[[dict[str, Any]], bool] = spec["condition"]
    if condition(row):
        return _float(row.get("incremental_edge_global_v1_vs_default_10am"))
    return 0.0


def _adjustment_by_date(
    order_panel: list[dict[str, Any]],
    variants: list[dict[str, Any]],
    validation_scope: str,
) -> list[dict[str, Any]]:
    scoped = [row for row in order_panel if row["validation_scope"] == validation_scope]
    out = []
    for spec in variants:
        by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in scoped:
            by_date[row["trade_date"]].append(row)
        for trade_date, group in sorted(by_date.items()):
            adjustments = [_selected_adjustment(row, spec) * _float(row["trade_delta_weight_abs"]) for row in group]
            out.append(
                {
                    "version_id": spec["version_id"],
                    "trade_date": trade_date,
                    "validation_scope": validation_scope,
                    "execution_adjustment_return": sum(adjustments),
                    "order_count": len(group),
                    "applied_order_count": sum(1 for row in group if abs(_selected_adjustment(row, spec)) > 1e-12),
                    "quiet_order_count": sum(1 for row in group if row["decision_10am_amount_intensity_bucket"] == "quiet"),
                    "normal_order_count": sum(1 for row in group if row["decision_10am_amount_intensity_bucket"] == "normal"),
                    "active_order_count": sum(1 for row in group if row["decision_10am_amount_intensity_bucket"] == "active"),
                    "extreme_order_count": sum(1 for row in group if row["decision_10am_amount_intensity_bucket"] == "extreme"),
                    "accepted": False,
                }
            )
    return out


def _daily_nav(daily: pd.DataFrame, adjustment_by_date: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source = daily[daily["version_id"].isin([PRE2021_BASELINE, PRIMARY])].copy()
    source = source[(source["trade_date"] >= AVAILABLE_PRE2021_START) & (source["trade_date"] <= AVAILABLE_PRE2021_END)].copy()
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
    primary = source[source["version_id"].eq(PRIMARY)].copy().sort_values("trade_date")
    adj_map = {(row["version_id"], row["trade_date"]): row for row in adjustment_by_date}
    for spec in _variants():
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
    baseline = _find(out, PRE2021_BASELINE)
    primary = _find(out, PRIMARY)
    global_v1 = _find(out, GLOBAL_V1)
    for row in out:
        row["delta_return_pct_points_vs_pre2021_baseline"] = (_float(row["strategy_return"]) - _float(baseline.get("strategy_return"))) * 100.0
        row["delta_return_pct_points_vs_pre2021_primary"] = (_float(row["strategy_return"]) - _float(primary.get("strategy_return"))) * 100.0
        row["delta_return_pct_points_vs_global_v1"] = (_float(row["strategy_return"]) - _float(global_v1.get("strategy_return"))) * 100.0
        row["delta_max_drawdown_pct_points_vs_pre2021_primary"] = (_float(row["max_drawdown"]) - _float(primary.get("max_drawdown"))) * 100.0
    order = {QUIET_OR_ACTIVE: 0, GLOBAL_V1: 1, QUIET_ONLY: 2, ACTIVE_ONLY: 3, DEFAULT_1000: 4, PRIMARY: 5, PRE2021_BASELINE: 6}
    return sorted(out, key=lambda row: order.get(row["version_id"], 99))


def _segment_result(order_panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [row for row in order_panel if row["validation_scope"] == PRIMARY_SCOPE]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["decision_10am_amount_intensity_bucket"]].append(row)
    out = []
    for bucket, group in sorted(groups.items()):
        weight_sum = sum(_float(row["trade_delta_weight_abs"]) for row in group)
        weighted = sum(_float(row["weighted_incremental_edge_global_v1_vs_default_10am"]) for row in group)
        out.append(
            {
                "validation_scope": PRIMARY_SCOPE,
                "decision_10am_amount_intensity_bucket": bucket,
                "order_count": len(group),
                "trade_date_count": len({row["trade_date"] for row in group}),
                "positive_pressure_count": sum(1 for row in group if row["decision_10am_amount_pressure_bucket"] == "positive_pressure"),
                "fallback_1400_count": sum(1 for row in group if row["global_v1_selected_obs_time"] == "14:00:00"),
                "execution_adjustment_total_pct_points": weighted * 100.0,
                "weighted_avg_incremental_edge_bp": weighted / weight_sum * 10000.0 if weight_sum else 0.0,
                "sample_power": _sample_power(len(group), len({row["trade_date"] for row in group})),
                "accepted": False,
            }
        )
    return out


def _scope_metrics(order_panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in order_panel:
        groups[row["validation_scope"]].append(row)
    out = []
    for scope, group in sorted(groups.items()):
        weighted = sum(_float(row["weighted_incremental_edge_global_v1_vs_default_10am"]) for row in group)
        weight = sum(_float(row["trade_delta_weight_abs"]) for row in group)
        out.append(
            {
                "validation_scope": scope,
                "order_count": len(group),
                "trade_date_count": len({row["trade_date"] for row in group}),
                "weighted_global_v1_adjustment_pct_points": weighted * 100.0,
                "weighted_avg_global_v1_adjustment_bp": weighted / weight * 10000.0 if weight else 0.0,
                "quiet_or_active_order_count": sum(1 for row in group if row["decision_10am_amount_intensity_bucket"] in {"quiet", "active"}),
                "sample_power": _sample_power(len(group), len({row["trade_date"] for row in group})),
                "accepted": False,
            }
        )
    return out


def _data_gate(
    manifest: dict[str, Any],
    segmented_summary: dict[str, Any],
    pre2021_summary: dict[str, Any],
    source_orders: list[dict[str, Any]],
    order_panel: list[dict[str, Any]],
    read_audit: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pass_reads = sum(1 for row in read_audit if row["status"] == "pass")
    primary_count = sum(1 for row in order_panel if row["validation_scope"] == PRIMARY_SCOPE)
    date_count = len({row["trade_date"] for row in order_panel if row["validation_scope"] == PRIMARY_SCOPE})
    return [
        {"gate_id": "segmented_source_completed", "status": "pass" if segmented_summary.get("status") == "completed_v5h_segmented_1min_execution_diagnostic" else "fail", "value": segmented_summary.get("status", "")},
        {"gate_id": "pre2021_validation_completed", "status": "pass" if pre2021_summary.get("status") == "completed_pre2021_p0_p1_p2_validation" else "fail", "value": pre2021_summary.get("status", "")},
        {"gate_id": "one_min_dataset_completed", "status": "pass" if manifest.get("status") == "completed" else "fail", "value": manifest.get("status")},
        {"gate_id": "source_orders_built", "status": "pass" if source_orders else "fail", "value": len(source_orders)},
        {"gate_id": "one_min_order_coverage_rate_pct", "status": "pass" if _pct(pass_reads, len(source_orders)) >= 95.0 else "fail", "value": _pct(pass_reads, len(source_orders))},
        {"gate_id": "primary_validation_sample_power", "status": "warn" if primary_count < 30 or date_count < 3 else "pass", "value": f"orders={primary_count};dates={date_count}"},
        {"gate_id": "formal_backtest_excluded_from_independent_validation", "status": "pass", "value": f"{FORMAL_BACKTEST_START}_to_{FORMAL_BACKTEST_END}_not_used"},
    ]


def _governance_audit() -> list[dict[str, Any]]:
    return [
        {"audit_id": "v57f_core_unchanged", "status": "pass", "detail": "Read-only independent validation; no V57f selection or core config changed."},
        {"audit_id": "v5f_mainline_unchanged", "status": "pass", "detail": "internal_subsleeve_mom12_70_30 remains the mainline input, not modified."},
        {"audit_id": "buy_side_only", "status": "pass", "detail": "Only existing pre-2021 buy/increase target changes are examined."},
        {"audit_id": "no_new_buy_signal", "status": "pass", "detail": "The gate cannot create orders or add stocks."},
        {"audit_id": "no_trading_frequency_increase", "status": "pass", "detail": "The rule only chooses 10:00 or 14:00 proxy on an existing buy day."},
        {"audit_id": "no_threshold_scan", "status": "pass", "detail": "The fixed quiet/active/normal/extreme buckets from V5h are reused."},
        {"audit_id": "not_accepted_not_live", "status": "pass", "detail": "No accepted/live/deployment status is granted."},
        {"audit_id": "formal_backtest_end_preserved", "status": "pass", "detail": f"Formal backtest remains capped at {FORMAL_BACKTEST_END}."},
    ]


def _pm_decision(
    metrics: list[dict[str, Any]],
    data_gate: list[dict[str, Any]],
    governance: list[dict[str, Any]],
    order_panel: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    hard_fail = any(row["status"] == "fail" for row in data_gate + governance)
    primary_count = sum(1 for row in order_panel if row["validation_scope"] == PRIMARY_SCOPE)
    date_count = len({row["trade_date"] for row in order_panel if row["validation_scope"] == PRIMARY_SCOPE})
    sample_power = _sample_power(primary_count, date_count)
    if hard_fail:
        decision = "blocked_by_data_or_governance_issue"
        status = "blocked"
    else:
        quiet = _find(metrics, QUIET_OR_ACTIVE)
        global_v1 = _find(metrics, GLOBAL_V1)
        delta_vs_global = (_float(quiet.get("strategy_return")) - _float(global_v1.get("strategy_return"))) * 100.0
        delta_vs_primary = _float(quiet.get("delta_return_pct_points_vs_pre2021_primary"))
        if sample_power != "adequate":
            if delta_vs_primary > 0:
                decision = "quiet_or_active_limited_independent_positive_low_power_not_accepted"
                status = "limited_support"
            else:
                decision = "quiet_or_active_independent_validation_low_power_no_confirmation"
                status = "low_power_diagnostic"
        elif delta_vs_global > 0 and delta_vs_primary > 0:
            decision = "quiet_or_active_independent_validation_positive_ready_for_forward_observation"
            status = "independent_positive"
        else:
            decision = "quiet_or_active_independent_validation_does_not_confirm"
            status = "diagnostic_only"
    quiet = _find(metrics, QUIET_OR_ACTIVE)
    global_v1 = _find(metrics, GLOBAL_V1)
    return [
        {
            "pm_gate_decision": decision,
            "status": status,
            "sample_power": sample_power,
            "primary_scope_order_count": primary_count,
            "primary_scope_trade_date_count": date_count,
            "quiet_or_active_delta_return_pct_points_vs_primary": quiet.get("delta_return_pct_points_vs_pre2021_primary", ""),
            "quiet_or_active_delta_return_pct_points_vs_global_v1": (
                (_float(quiet.get("strategy_return")) - _float(global_v1.get("strategy_return"))) * 100.0
                if quiet and global_v1
                else ""
            ),
            "accepted": False,
            "live_trading_approved": False,
            "deployment_approved": False,
            "v57f_core_modified": False,
            "v5f_mainline_modified": False,
            "sell_rules_modified": False,
            "trading_frequency_increased": False,
            "new_buy_signal_used": False,
            "notes": "Pre-2021 validation is independent from the formal backtest but currently has low sample power.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "queue_id": "v5h_quiet_or_active_forward_observation_append",
            "status": "ready",
            "scope": "Append future official buy/increase orders using the frozen quiet-or-active gate; do not promote.",
        },
        {
            "priority": 2,
            "queue_id": "v5h_market_cap_pit_segmentation_gate",
            "status": "ready",
            "scope": "Build PIT market-cap/free-float panel and test fixed size buckets without changing V5f mainline.",
        },
        {
            "priority": 3,
            "queue_id": "extend_pre2021_repaired_rebalance_events_for_execution_validation",
            "status": "optional",
            "scope": "Increase independent sample power only if PIT-clean pre-2021 repaired pool can be extended.",
        },
    ]


def _report(
    metrics: list[dict[str, Any]],
    segment_result: list[dict[str, Any]],
    scope_metrics: list[dict[str, Any]],
    data_gate: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    quiet = _find(metrics, QUIET_OR_ACTIVE)
    global_v1 = _find(metrics, GLOBAL_V1)
    primary = _find(metrics, PRIMARY)
    lines = [
        "# V5h Quiet-or-Active Independent Validation",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Sample power: `{decision[0]['sample_power']}`",
        f"- Independent validation window available locally: {AVAILABLE_PRE2021_START} to {AVAILABLE_PRE2021_END}.",
        f"- Formal backtest window {FORMAL_BACKTEST_START} to {FORMAL_BACKTEST_END} is not used for discovery here.",
        "",
        "## Main Result",
        "",
        f"- Pre-2021 V5f primary return: `{_float(primary.get('strategy_return')) * 100:.4f}%`.",
        f"- Global V5h v1 return: `{_float(global_v1.get('strategy_return')) * 100:.4f}%`.",
        f"- Quiet-or-active gate return: `{_float(quiet.get('strategy_return')) * 100:.4f}%`.",
        f"- Quiet-or-active delta vs primary: `{_float(quiet.get('delta_return_pct_points_vs_pre2021_primary')):+.4f}` pct points.",
        f"- Quiet-or-active delta vs global v1: `{(_float(quiet.get('strategy_return')) - _float(global_v1.get('strategy_return'))) * 100:+.4f}` pct points.",
        "",
        "## Liquidity Buckets",
    ]
    for row in segment_result:
        lines.append(
            f"- `{row['decision_10am_amount_intensity_bucket']}`: n={row['order_count']}, adjustment `{_float(row['execution_adjustment_total_pct_points']):+.4f}` pct, avg `{_float(row['weighted_avg_incremental_edge_bp']):+.2f}` bp."
        )
    lines.extend(["", "## Scope Health"])
    for row in scope_metrics:
        lines.append(
            f"- `{row['validation_scope']}`: orders `{row['order_count']}`, dates `{row['trade_date_count']}`, global v1 adjustment `{_float(row['weighted_global_v1_adjustment_pct_points']):+.4f}` pct."
        )
    lines.extend(["", "## Data Gate"])
    for row in data_gate:
        lines.append(f"- `{row['gate_id']}`: `{row['status']}` ({row['value']})")
    lines.extend(["", "This packet does not change V57f, V5f, sell rules, stock selection, or trading frequency.", ""])
    return "\n".join(lines)


def _rules() -> str:
    return "\n".join(
        [
            "# V5h Quiet-or-Active Independent Validation Rules",
            "",
            "- Use pre-2021 repaired V5f weights and cleaned 1min data only.",
            "- Do not use 2021-05-01 to 2026-05-31 to reselect the gate.",
            "- Do not modify V57f core or V5f mainline.",
            "- Do not change sell rules or create new buy signals.",
            "- Do not increase trading frequency; only 10:00 vs 14:00 execution proxy is compared.",
            "- Do not mark accepted, live approved, or deployment approved.",
            "",
        ]
    )


def _find_v5_database(root: Path) -> Path:
    for child in root.iterdir():
        if child.is_dir() and (child / "processed").exists() and (child / "raw").exists() and (child / "manifests").exists():
            return child
    raise FileNotFoundError("Could not locate V5 database directory with processed/raw/manifests children.")


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
        "task": "v5h_quiet_or_active_independent_validation",
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


def _sample_power(order_count: int, date_count: int) -> str:
    if order_count >= 80 and date_count >= 8:
        return "adequate"
    if order_count >= 30 and date_count >= 3:
        return "limited"
    return "low_power"


def _buy_edge(price: float, reference: float) -> float:
    if price == 0.0 or reference == 0.0:
        return 0.0
    return reference / price - 1.0


def _signed_pressure(rows: list[dict[str, Any]], weight_col: str) -> float:
    if len(rows) < 2:
        return 0.0
    total = 0.0
    signed = 0.0
    prev_close = rows[0]["close"]
    for row in rows[1:]:
        weight = max(_float(row.get(weight_col)), 0.0)
        total += weight
        delta = row["close"] - prev_close
        if delta > 1e-12:
            signed += weight
        elif delta < -1e-12:
            signed -= weight
        prev_close = row["close"]
    return signed / total if total > 0 else 0.0


def _intensity_bucket(value: float) -> str:
    if value < 0.80:
        return "quiet"
    if value < 1.20:
        return "normal"
    if value < 2.00:
        return "active"
    return "extreme"


def _pressure_bucket(value: float) -> str:
    if value <= -0.10:
        return "negative_pressure"
    if value >= 0.10:
        return "positive_pressure"
    return "neutral_pressure"


def _turn_bucket(value: float) -> str:
    if value <= -0.10:
        return "pressure_worsening"
    if value >= 0.10:
        return "pressure_improving"
    return "pressure_stable"


def _avg(rows: list[dict[str, Any]], col: str) -> float:
    return sum(_float(row.get(col)) for row in rows) / len(rows) if rows else 0.0


def _ret(end: float | None, start: float | None) -> float:
    if end is None or start in (None, 0.0):
        return 0.0
    return end / start - 1.0


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


def _float(value: Any) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else 0.0
    except Exception:
        return 0.0


def _pct(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100.0, 6) if denominator else 0.0


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
    summary = run_v5h_quiet_or_active_independent_validation(Path("."))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

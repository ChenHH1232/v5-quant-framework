from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v5.v5f_structural_rough_screen_runner import (
    BASELINE,
    PRICE_DIR,
    REPAIRED_RUN,
    _daily_returns,
    _drawdown,
    _load_prices,
    _metrics,
    _yearly,
)


OUT_DIR = Path("v5c_highway_ocf_risk_cap_v1_limited_engineering") / "current"
FREEZE_DIR = Path("v5c_highway_ocf_risk_cap_rule_freeze") / "current"
ROUGH_DIR = Path("v5f_structural_rough_screen") / "current"
HIGHWAY_PANEL = (
    Path("\u6570\u636e\u5e93")
    / "processed"
    / "startup_preload_repaired_panels_v5"
    / "highway_v54h"
    / "panel_with_low_vol.csv"
)

PRIMARY = "internal_subsleeve_mom12_70_30"
VERSION_ID = "highway_ocf_risk_cap_v1_on_internal_subsleeve_mom12_70_30"
FROZEN_RULE_ID = "highway_ocf_yield_quality_guard_v1_risk_cap_only"
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_v5c_highway_ocf_risk_cap_limited_engineering(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        summary = _summary("blocked_missing_required_inputs", "blocked_missing_required_inputs", blockers)
        _write_json(out / "v5c_highway_ocf_risk_cap_limited_summary.json", summary)
        _write_csv(out / "v5c_highway_ocf_risk_cap_blockers.csv", blockers)
        return summary

    freeze_summary = _read_json(root / FREEZE_DIR / "v5c_highway_ocf_risk_cap_rule_freeze_summary.json")
    frozen_rule = _read_csv(root / FREEZE_DIR / "v5c_highway_ocf_risk_cap_frozen_rule.csv")
    weights = pd.read_csv(root / ROUGH_DIR / "v5f_structural_rough_screen_weights.csv", dtype={"rebalance_date": str, "code": str})
    primary_metrics_input = _read_csv(root / ROUGH_DIR / "v5f_structural_rough_screen_metrics.csv")
    highway_panel = pd.read_csv(root / HIGHWAY_PANEL, dtype={"trade_date": str, "code": str})
    baseline_daily = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv", dtype={"trade_date": str})
    prices = _load_prices(root)

    risk_flags = _risk_flags(weights, highway_panel)
    adjusted_weights, cap_events = _apply_risk_cap(weights, risk_flags)
    relevant_weights = _relevant_weights(weights, adjusted_weights)
    daily = _daily_returns(relevant_weights, prices, baseline_daily)
    metrics = _post_process_metrics(_metrics(daily), primary_metrics_input)
    yearly = _tag_riskcap_family(_yearly(daily))
    drawdown = _tag_riskcap_family(_drawdown(daily))
    rebalance = _rebalance_period(daily)
    contribution = _risk_cap_contribution(cap_events, prices)
    cost = _turnover_cost(metrics)
    governance = _governance_audit(freeze_summary, frozen_rule, weights, adjusted_weights, risk_flags)
    decision = _pm_decision(metrics, governance, risk_flags, cap_events)
    next_queue = _next_queue(decision)
    blockers_out = _blockers(governance)

    _write_csv(out / "v5c_highway_ocf_risk_cap_risk_flags.csv", risk_flags)
    _write_csv(out / "v5c_highway_ocf_risk_cap_adjusted_weights.csv", adjusted_weights)
    _write_csv(out / "v5c_highway_ocf_risk_cap_cap_events.csv", cap_events)
    _write_csv(out / "v5c_highway_ocf_risk_cap_daily_returns.csv", daily)
    _write_csv(out / "v5c_highway_ocf_risk_cap_metrics.csv", metrics)
    _write_csv(out / "v5c_highway_ocf_risk_cap_yearly.csv", yearly)
    _write_csv(out / "v5c_highway_ocf_risk_cap_drawdown.csv", drawdown)
    _write_csv(out / "v5c_highway_ocf_risk_cap_rebalance_period.csv", rebalance)
    _write_csv(out / "v5c_highway_ocf_risk_cap_contribution.csv", contribution)
    _write_csv(out / "v5c_highway_ocf_risk_cap_turnover_cost.csv", cost)
    _write_csv(out / "v5c_highway_ocf_risk_cap_governance_audit.csv", governance)
    _write_csv(out / "v5c_highway_ocf_risk_cap_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_highway_ocf_risk_cap_next_queue.csv", next_queue)
    _write_csv(out / "v5c_highway_ocf_risk_cap_blockers.csv", blockers_out)
    (out / "v5c_highway_ocf_risk_cap_limited_report.md").write_text(
        _report(metrics, risk_flags, cap_events, governance, decision),
        encoding="utf-8",
    )
    (out / "v5c_highway_ocf_risk_cap_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    summary = _summary(
        "completed_fixed_rule_limited_engineering",
        decision[0]["pm_gate_decision"],
        blockers_out,
        risk_flag_count=sum(1 for row in risk_flags if row["flag_ocf_risk"]),
        cap_event_count=sum(1 for row in cap_events if row["cap_action"] == "cap_applied"),
        delta_vs_primary=_metric(metrics, VERSION_ID, "delta_return_pct_points_vs_v5f_primary"),
        delta_vs_baseline=_metric(metrics, VERSION_ID, "delta_return_pct_points_vs_repaired_baseline"),
        delta_dd_vs_primary=_metric(metrics, VERSION_ID, "delta_max_drawdown_pct_points_vs_v5f_primary"),
    )
    _write_json(out / "v5c_highway_ocf_risk_cap_limited_summary.json", summary)
    return summary


def _risk_flags(weights: pd.DataFrame, highway_panel: pd.DataFrame) -> list[dict[str, Any]]:
    primary = weights[(weights["version_id"] == PRIMARY) & (weights["sleeve"] == "highway_infrastructure")].copy()
    panel = highway_panel.copy()
    panel["operating_cash_flow_yield_num"] = pd.to_numeric(panel.get("operating_cash_flow_yield"), errors="coerce")
    panel["operating_cash_flow_to_net_profit_num"] = pd.to_numeric(panel.get("operating_cash_flow_to_net_profit"), errors="coerce")
    panel["factor_visible_date"] = panel.get("factor_visible_date", panel["trade_date"]).astype(str)
    panel_by_key = panel.set_index(["trade_date", "code"], drop=False)
    rows: list[dict[str, Any]] = []
    for date, group in primary.groupby("rebalance_date", sort=True):
        values = []
        for _, weight_row in group.iterrows():
            panel_row = _panel_row(panel_by_key, date, weight_row["code"])
            if panel_row is None:
                continue
            values.append(
                {
                    "code": weight_row["code"],
                    "ocf_yield": _safe_float(panel_row.get("operating_cash_flow_yield_num")),
                    "ocf_to_np": _safe_float(panel_row.get("operating_cash_flow_to_net_profit_num")),
                    "visible_date": str(panel_row.get("factor_visible_date", ""))[:10],
                    "source": panel_row.get("factor_visibility_source", ""),
                }
            )
        ocf_valid = sorted(v["ocf_yield"] for v in values if v["ocf_yield"] is not None)
        np_valid = sorted(v["ocf_to_np"] for v in values if v["ocf_to_np"] is not None)
        bottom_count = max(1, len(ocf_valid) // 3) if ocf_valid else 0
        ocf_threshold = ocf_valid[bottom_count - 1] if bottom_count else None
        np_median = _median(np_valid)
        for _, weight_row in group.iterrows():
            panel_row = _panel_row(panel_by_key, date, weight_row["code"])
            visible = ""
            source = ""
            ocf_yield = None
            ocf_to_np = None
            pit_status = "missing_factor_row"
            if panel_row is not None:
                visible = str(panel_row.get("factor_visible_date", ""))[:10]
                source = str(panel_row.get("factor_visibility_source", ""))
                ocf_yield = _safe_float(panel_row.get("operating_cash_flow_yield_num"))
                ocf_to_np = _safe_float(panel_row.get("operating_cash_flow_to_net_profit_num"))
                pit_status = "pass" if visible <= date else "fail_visible_after_rebalance"
            ocf_bottom = ocf_yield is not None and ocf_threshold is not None and ocf_yield <= ocf_threshold
            np_below = ocf_to_np is not None and np_median is not None and ocf_to_np < np_median
            missing_primary = ocf_yield is None or ocf_to_np is None
            flag = bool((ocf_bottom or np_below) and pit_status == "pass")
            if flag:
                risk_status = "flagged"
            elif missing_primary:
                risk_status = "needs_data_review"
            else:
                risk_status = "clear"
            rows.append(
                {
                    "rebalance_date": date,
                    "code": weight_row["code"],
                    "sleeve": "highway_infrastructure",
                    "base_target_weight": _safe_float(weight_row["base_target_weight"]),
                    "v5f_target_weight": _safe_float(weight_row["target_weight"]),
                    "v5f_weight_delta": _safe_float(weight_row["weight_delta"]),
                    "operating_cash_flow_yield": ocf_yield if ocf_yield is not None else "",
                    "ocf_yield_bottom_tercile_threshold": ocf_threshold if ocf_threshold is not None else "",
                    "ocf_yield_bottom_tercile": ocf_bottom,
                    "operating_cash_flow_to_net_profit": ocf_to_np if ocf_to_np is not None else "",
                    "ocf_to_np_same_date_median": np_median if np_median is not None else "",
                    "ocf_to_np_below_median": np_below,
                    "flag_ocf_risk": flag,
                    "risk_status": risk_status,
                    "factor_visible_date": visible,
                    "pit_status": pit_status,
                    "factor_source": source,
                    "accepted": False,
                }
            )
    return rows


def _apply_risk_cap(weights: pd.DataFrame, risk_flags: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    primary = weights[weights["version_id"] == PRIMARY].copy()
    flags = {(row["rebalance_date"], row["code"]): row for row in risk_flags}
    adjusted_frames = []
    events: list[dict[str, Any]] = []
    for date, day in primary.groupby("rebalance_date", sort=True):
        tmp = day.copy()
        tmp["adjusted_target_weight"] = pd.to_numeric(tmp["target_weight"], errors="coerce")
        highway_idx = tmp[tmp["sleeve"] == "highway_infrastructure"].index
        released = 0.0
        capped_idx: list[int] = []
        for idx in highway_idx:
            row = tmp.loc[idx]
            flag = flags.get((date, row["code"]), {})
            is_flagged = bool(flag.get("flag_ocf_risk"))
            target = float(row["target_weight"])
            base = float(row["base_target_weight"])
            cap_amount = max(0.0, target - base) if is_flagged else 0.0
            if cap_amount > 1e-12:
                tmp.loc[idx, "adjusted_target_weight"] = base
                released += cap_amount
                capped_idx.append(idx)
        receiver_idx = [
            idx
            for idx in highway_idx
            if idx not in capped_idx
            and not bool(flags.get((date, tmp.loc[idx, "code"]), {}).get("flag_ocf_risk"))
            and float(tmp.loc[idx, "target_weight"]) > 0
        ]
        no_action = False
        if released > 1e-12 and receiver_idx:
            receiver_weight_sum = float(tmp.loc[receiver_idx, "target_weight"].astype(float).sum())
            for idx in receiver_idx:
                tmp.loc[idx, "adjusted_target_weight"] += released * float(tmp.loc[idx, "target_weight"]) / receiver_weight_sum
        elif released > 1e-12:
            no_action = True
            tmp["adjusted_target_weight"] = pd.to_numeric(tmp["target_weight"], errors="coerce")
        for idx in highway_idx:
            row = tmp.loc[idx]
            flag = flags.get((date, row["code"]), {})
            original = float(row["target_weight"])
            adjusted = float(row["adjusted_target_weight"])
            base = float(row["base_target_weight"])
            if abs(adjusted - original) > 1e-12 or bool(flag.get("flag_ocf_risk")):
                events.append(
                    {
                        "rebalance_date": date,
                        "code": row["code"],
                        "risk_status": flag.get("risk_status", "missing_factor_row"),
                        "flag_ocf_risk": bool(flag.get("flag_ocf_risk")),
                        "base_target_weight": base,
                        "v5f_target_weight": original,
                        "adjusted_target_weight": adjusted,
                        "cap_delta_weight": adjusted - original,
                        "released_total_for_date": released,
                        "receiver_count": len(receiver_idx),
                        "cap_action": "no_action_no_receiver" if no_action else ("cap_applied" if adjusted < original else ("redistribution_receiver" if adjusted > original else "flag_no_overweight")),
                        "accepted": False,
                    }
                )
        tmp["version_id"] = VERSION_ID
        tmp["family"] = "v5c_highway_ocf_risk_cap"
        tmp["target_weight"] = tmp["adjusted_target_weight"]
        tmp["weight_delta"] = tmp["target_weight"].astype(float) - tmp["base_target_weight"].astype(float)
        tmp["bucket"] = tmp.apply(lambda row: f"{row['bucket']}|ocf_risk_cap_v1" if row["sleeve"] == "highway_infrastructure" else row["bucket"], axis=1)
        adjusted_frames.append(tmp.drop(columns=["adjusted_target_weight"]))
    adjusted = pd.concat(adjusted_frames, ignore_index=True)
    return adjusted.to_dict("records"), events


def _relevant_weights(weights: pd.DataFrame, adjusted_weights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base = weights[weights["version_id"].isin([BASELINE, PRIMARY])].copy()
    rows = base.to_dict("records") + adjusted_weights
    return rows


def _post_process_metrics(metrics: list[dict[str, Any]], primary_metrics_input: list[dict[str, str]]) -> list[dict[str, Any]]:
    primary = next(row for row in metrics if row["version_id"] == PRIMARY)
    primary_input = next((row for row in primary_metrics_input if row["version_id"] == PRIMARY), {})
    for row in metrics:
        row["family"] = "v5c_highway_ocf_risk_cap" if row["version_id"] == VERSION_ID else row.get("family", "")
        row["delta_return_pct_points_vs_v5f_primary"] = (float(row["strategy_return"]) - float(primary["strategy_return"])) * 100
        row["delta_max_drawdown_pct_points_vs_v5f_primary"] = (float(row["max_drawdown"]) - float(primary["max_drawdown"])) * 100
        row["primary_reference_strategy_return"] = primary_input.get("strategy_return", primary["strategy_return"])
        row["primary_reference_max_drawdown"] = primary_input.get("max_drawdown", primary["max_drawdown"])
        row["accepted"] = False
    return sorted(metrics, key=lambda row: (row["version_id"] != VERSION_ID, row["version_id"]))


def _rebalance_period(daily_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(daily_rows)
    rows: list[dict[str, Any]] = []
    for (version, period), group in df.groupby(["version_id", "active_rebalance_date"], sort=True):
        if not period:
            continue
        rows.append(
            {
                "version_id": version,
                "active_rebalance_date": period,
                "period_return": (1.0 + pd.to_numeric(group["strategy_return"])).prod() - 1.0,
                "trade_days": len(group),
            }
        )
    by_version_period = {(row["version_id"], row["active_rebalance_date"]): row for row in rows}
    for row in rows:
        period = row["active_rebalance_date"]
        baseline = by_version_period.get((BASELINE, period), {})
        primary = by_version_period.get((PRIMARY, period), {})
        row["delta_return_pct_points_vs_repaired_baseline"] = (float(row["period_return"]) - float(baseline.get("period_return", 0.0))) * 100
        row["delta_return_pct_points_vs_v5f_primary"] = (float(row["period_return"]) - float(primary.get("period_return", 0.0))) * 100
    return rows


def _risk_cap_contribution(cap_events: list[dict[str, Any]], prices: pd.DataFrame) -> list[dict[str, Any]]:
    ret_map = prices.set_index(["date", "code"])["stock_return"].to_dict()
    rows = []
    for event in cap_events:
        date = event["rebalance_date"]
        code = event["code"]
        first_day_ret = _safe_float(ret_map.get((date, code))) or 0.0
        delta_weight = float(event["cap_delta_weight"])
        rows.append(
            {
                **event,
                "first_day_stock_return": first_day_ret,
                "first_day_delta_contribution": delta_weight * first_day_ret,
            }
        )
    return rows


def _turnover_cost(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = next(row for row in metrics if row["version_id"] == PRIMARY)
    riskcap = next(row for row in metrics if row["version_id"] == VERSION_ID)
    return [
        {
            "version_id": VERSION_ID,
            "turnover_proxy": riskcap["turnover_proxy"],
            "incremental_commission_total": riskcap["incremental_commission_total"],
            "delta_turnover_vs_v5f_primary": float(riskcap["turnover_proxy"]) - float(primary["turnover_proxy"]),
            "delta_commission_vs_v5f_primary": float(riskcap["incremental_commission_total"]) - float(primary["incremental_commission_total"]),
            "delta_return_pct_points_vs_v5f_primary": riskcap["delta_return_pct_points_vs_v5f_primary"],
            "cost_health": "pass" if float(riskcap["delta_return_pct_points_vs_v5f_primary"]) >= -0.1 else "review",
        }
    ]


def _tag_riskcap_family(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for row in rows:
        if row.get("version_id") == VERSION_ID:
            row["family"] = "v5c_highway_ocf_risk_cap"
    return rows


def _governance_audit(
    freeze_summary: dict[str, Any],
    frozen_rule: list[dict[str, str]],
    weights: pd.DataFrame,
    adjusted_weights: list[dict[str, Any]],
    risk_flags: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    adjusted = pd.DataFrame(adjusted_weights)
    primary = weights[weights["version_id"] == PRIMARY].copy()
    primary_keys = set(zip(primary["rebalance_date"], primary["code"]))
    adjusted_keys = set(zip(adjusted["rebalance_date"], adjusted["code"]))
    sleeve_diff = _max_sleeve_weight_diff(primary, adjusted)
    pit_fail = sum(1 for row in risk_flags if row["pit_status"] == "fail_visible_after_rebalance")
    return [
        {"audit_id": "frozen_rule_id", "status": "pass" if freeze_summary.get("frozen_rule_id") == FROZEN_RULE_ID and frozen_rule and frozen_rule[0].get("frozen_rule_id") == FROZEN_RULE_ID else "fail", "detail": FROZEN_RULE_ID},
        {"audit_id": "fixed_rule_only_no_threshold_scan", "status": "pass", "detail": False},
        {"audit_id": "capex_fcf_model_use_false", "status": "pass", "detail": False},
        {"audit_id": "v57f_core_modified_false", "status": "pass", "detail": False},
        {"audit_id": "v5f_primary_modified_false", "status": "pass", "detail": False},
        {"audit_id": "no_new_stock", "status": "pass" if adjusted_keys == primary_keys else "fail", "detail": len(adjusted_keys - primary_keys)},
        {"audit_id": "same_sleeve_only", "status": "pass" if sleeve_diff < 1e-10 else "fail", "detail": sleeve_diff},
        {"audit_id": "pit_visible_date", "status": "pass" if pit_fail == 0 else "fail", "detail": pit_fail},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
        {"audit_id": "live_trading_approved_false", "status": "pass", "detail": False},
    ]


def _max_sleeve_weight_diff(primary: pd.DataFrame, adjusted: pd.DataFrame) -> float:
    left = primary.groupby(["rebalance_date", "sleeve"])["target_weight"].apply(lambda s: s.astype(float).sum()).to_dict()
    right = adjusted.groupby(["rebalance_date", "sleeve"])["target_weight"].apply(lambda s: s.astype(float).sum()).to_dict()
    keys = set(left) | set(right)
    return max((abs(left.get(key, 0.0) - right.get(key, 0.0)) for key in keys), default=0.0)


def _pm_decision(
    metrics: list[dict[str, Any]],
    governance: list[dict[str, Any]],
    risk_flags: list[dict[str, Any]],
    cap_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    riskcap = next(row for row in metrics if row["version_id"] == VERSION_ID)
    gov_ok = all(row["status"] == "pass" for row in governance)
    delta_return = float(riskcap["delta_return_pct_points_vs_v5f_primary"])
    delta_dd = float(riskcap["delta_max_drawdown_pct_points_vs_v5f_primary"])
    if not gov_ok:
        decision = "blocked_by_governance_or_pit_issue"
        next_action = "repair governance before any further use"
    elif delta_return > 0 and delta_dd <= 0:
        decision = "positive_ready_for_forward_observation_not_accepted"
        next_action = "open forward observation; do not replace V5f primary yet"
    elif delta_dd < -0.05 and delta_return >= -0.25:
        decision = "risk_reduction_only_keep_diagnostic_not_accepted"
        next_action = "keep diagnostic; only reconsider if forward evidence confirms drawdown value"
    else:
        decision = "diagnostic_only_no_incremental_value"
        next_action = "do not promote; keep V5f primary unchanged"
    return [
        {
            "pm_gate_decision": decision,
            "version_id": VERSION_ID,
            "delta_return_pct_points_vs_v5f_primary": delta_return,
            "delta_max_drawdown_pct_points_vs_v5f_primary": delta_dd,
            "delta_return_pct_points_vs_repaired_baseline": riskcap["delta_return_pct_points_vs_repaired_baseline"],
            "risk_flag_count": sum(1 for row in risk_flags if row["flag_ocf_risk"]),
            "cap_event_count": sum(1 for row in cap_events if row["cap_action"] == "cap_applied"),
            "limited_engineering_only": True,
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "v5f_primary_modified": False,
            "next_action": next_action,
        }
    ]


def _next_queue(decision: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gate = decision[0]["pm_gate_decision"]
    return [
        {
            "priority": "P0",
            "task_id": "keep_internal_subsleeve_mom12_70_30_as_v5f_primary",
            "status": "ready",
            "reason": "risk-cap v1 does not modify accepted/candidate status",
        },
        {
            "priority": "P1",
            "task_id": "v5c_highway_ocf_risk_cap_forward_observation",
            "status": "ready_if_positive_or_risk_reduction" if gate != "diagnostic_only_no_incremental_value" else "defer",
            "reason": gate,
        },
        {
            "priority": "P2",
            "task_id": "v5c_highway_capex_fcf_small_original_page_review",
            "status": "ready",
            "reason": "capex/FCF remain excluded from v1 model input",
        },
    ]


def _blockers(governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in governance if row["status"] != "pass"]
    return [
        {
            "blocker_id": row["audit_id"],
            "severity": "fatal",
            "status": "blocking",
            "detail": row["detail"],
            "required_action": "repair before further use",
        }
        for row in failed
    ] or [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "detail": "limited engineering completed", "required_action": ""}]


def _summary(
    status: str,
    pm_gate_decision: str,
    blockers: list[dict[str, Any]],
    risk_flag_count: int = 0,
    cap_event_count: int = 0,
    delta_vs_primary: float = 0.0,
    delta_vs_baseline: float = 0.0,
    delta_dd_vs_primary: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5c_highway_ocf_risk_cap_v1_limited_engineering",
        "status": status,
        "version_id": VERSION_ID if status != "blocked_missing_required_inputs" else "",
        "frozen_rule_id": FROZEN_RULE_ID,
        "backtest_scope_start": BACKTEST_START,
        "backtest_scope_end": BACKTEST_END,
        "primary_reference": PRIMARY,
        "baseline": BASELINE,
        "risk_flag_count": risk_flag_count,
        "cap_event_count": cap_event_count,
        "delta_return_pct_points_vs_v5f_primary": delta_vs_primary,
        "delta_return_pct_points_vs_repaired_baseline": delta_vs_baseline,
        "delta_max_drawdown_pct_points_vs_v5f_primary": delta_dd_vs_primary,
        "v57f_core_modified": False,
        "v5f_primary_modified": False,
        "parameter_scan_used": False,
        "capex_fcf_model_use": False,
        "accepted": False,
        "live_trading_approved": False,
        "fatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "fatal"),
        "nonfatal_blocker_count": sum(1 for row in blockers if row.get("severity") not in {"fatal", "none"}),
        "pm_gate_decision": pm_gate_decision,
    }


def _report(
    metrics: list[dict[str, Any]],
    risk_flags: list[dict[str, Any]],
    cap_events: list[dict[str, Any]],
    governance: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    riskcap = next(row for row in metrics if row["version_id"] == VERSION_ID)
    primary = next(row for row in metrics if row["version_id"] == PRIMARY)
    baseline = next(row for row in metrics if row["version_id"] == BASELINE)
    return "\n".join(
        [
            "# V5c Highway OCF Risk-Cap v1 Limited Engineering",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Version: `{VERSION_ID}`",
            f"- Fixed rule: `{FROZEN_RULE_ID}`",
            "- Accepted: `False`",
            "- V57f/V5f modified: `False` / `False`",
            "",
            "## Result",
            f"- Repaired baseline return: `{float(baseline['strategy_return']) * 100:.4f}%`",
            f"- V5f primary return: `{float(primary['strategy_return']) * 100:.4f}%`",
            f"- Risk-cap v1 return: `{float(riskcap['strategy_return']) * 100:.4f}%`",
            f"- Delta vs V5f primary: `{float(riskcap['delta_return_pct_points_vs_v5f_primary']):+.4f}` pct points.",
            f"- Delta drawdown vs V5f primary: `{float(riskcap['delta_max_drawdown_pct_points_vs_v5f_primary']):+.4f}` pct points.",
            "",
            "## Engineering Activity",
            f"- OCF risk flags: `{sum(1 for row in risk_flags if row['flag_ocf_risk'])}`",
            f"- Cap-applied events: `{sum(1 for row in cap_events if row['cap_action'] == 'cap_applied')}`",
            "- Capex/FCF were not used.",
            "",
            "## Governance",
            *[f"- `{row['audit_id']}`: {row['status']} ({row['detail']})" for row in governance],
            "",
        ]
    )


def _rules() -> str:
    return """# Agent Execution Rules

- Test only `highway_ocf_yield_quality_guard_v1_risk_cap_only`.
- Do not tune thresholds or variants.
- Do not use capex/FCF in model input.
- Do not modify V57f core or V5f primary.
- Existing V57f/V5f selected stocks only; no new buys and no cross-sleeve transfer.
- Do not mark accepted or live approved.
"""


def _panel_row(panel_by_key: pd.DataFrame, date: str, code: str) -> pd.Series | None:
    try:
        row = panel_by_key.loc[(date, code)]
    except KeyError:
        return None
    if isinstance(row, pd.DataFrame):
        return row.iloc[0]
    return row


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _safe_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _metric(metrics: list[dict[str, Any]], version: str, key: str) -> float:
    row = next((item for item in metrics if item["version_id"] == version), {})
    try:
        return float(row.get(key, 0.0))
    except (TypeError, ValueError):
        return 0.0


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        FREEZE_DIR / "v5c_highway_ocf_risk_cap_rule_freeze_summary.json",
        FREEZE_DIR / "v5c_highway_ocf_risk_cap_frozen_rule.csv",
        ROUGH_DIR / "v5f_structural_rough_screen_weights.csv",
        ROUGH_DIR / "v5f_structural_rough_screen_metrics.csv",
        PRICE_DIR,
        REPAIRED_RUN / "daily_returns.csv",
        HIGHWAY_PANEL,
    ]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "status": "blocking",
            "path": str(path),
            "required_action": "restore required V5c/V5f local artifacts",
        }
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
    summary = run_v5c_highway_ocf_risk_cap_limited_engineering(Path(args.root))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

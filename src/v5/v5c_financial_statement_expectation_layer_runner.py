from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5c_financial_statement_expectation_layer") / "current"

P1_DIR = Path("v5c_p1_financial_quality_pit_panel") / "current"
P2_DIR = Path("v5c_p2_valuation_and_crowding_state_panel") / "current"
KNOWLEDGE_DIR = Path("knowledge") / "research_agent" / "v5c_industry_bank_power_p0"
V5F_DIR = Path("v5f_structural_rough_screen") / "current"

P1_PANEL = P1_DIR / "v5c_p1_financial_quality_pit_panel.csv"
P1_SUMMARY = P1_DIR / "v5c_p1_financial_quality_summary.json"
P2_VALUATION = P2_DIR / "v5c_p2_valuation_state_panel.csv"
P2_CROWDING = P2_DIR / "v5c_p2_crowding_state_panel.csv"
P2_SLEEVE_OVERHEAT = P2_DIR / "v5c_p2_sleeve_overheat_state_panel.csv"
BANK_DRIVER_MAP = KNOWLEDGE_DIR / "v5c_bank_driver_metric_map.csv"
POWER_DRIVER_MAP = KNOWLEDGE_DIR / "v5c_power_driver_metric_map.csv"
V5F_METRICS = V5F_DIR / "v5f_structural_rough_screen_metrics.csv"

BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
PRIMARY_V5F = "internal_subsleeve_mom12_70_30"


EXPECTATION_GROUPS: tuple[dict[str, Any], ...] = (
    {
        "expectation_id": "bank_asset_quality_next_report",
        "sleeve_filter": ("bank",),
        "theory_driver": "asset_quality_cycle",
        "expected_report_state": "bank_next_asset_quality_direction",
        "metrics": (
            ("non_performing_loan_ratio", -1),
            ("provision_coverage_ratio", 1),
            ("core_tier_1_capital_adequacy_ratio", 1),
        ),
        "use_case": "credit_quality_watch",
    },
    {
        "expectation_id": "bank_dividend_capital_buffer_next_report",
        "sleeve_filter": ("bank",),
        "theory_driver": "dividend_sustainability",
        "expected_report_state": "bank_next_dividend_buffer_direction",
        "metrics": (
            ("return_on_equity_ttm", 1),
            ("core_tier_1_capital_adequacy_ratio", 1),
            ("provision_coverage_ratio", 1),
            ("non_performing_loan_ratio", -1),
        ),
        "use_case": "dividend_sustainability_watch",
    },
    {
        "expectation_id": "power_cashflow_pressure_next_report",
        "sleeve_filter": ("utilities_electricity",),
        "theory_driver": "capex_debt_cashflow",
        "expected_report_state": "power_next_cashflow_pressure_direction",
        "metrics": (
            ("operating_cash_flow_yield", 1),
            ("operating_cash_flow_to_net_profit", 1),
            ("capex_burden", -1),
            ("asset_liability_ratio", -1),
        ),
        "use_case": "cashflow_and_debt_watch",
    },
    {
        "expectation_id": "power_profitability_next_report",
        "sleeve_filter": ("utilities_electricity",),
        "theory_driver": "capex_debt_cashflow",
        "expected_report_state": "power_next_profitability_direction",
        "metrics": (
            ("return_on_equity_ttm", 1),
            ("net_profit_margin", 1),
            ("operating_cash_flow_yield", 1),
            ("asset_liability_ratio", -1),
        ),
        "use_case": "profitability_watch",
    },
    {
        "expectation_id": "infrastructure_cashflow_quality_next_report",
        "sleeve_filter": ("highway_infrastructure", "port_rail_infrastructure"),
        "theory_driver": "cashflow_dividend_infrastructure",
        "expected_report_state": "infrastructure_next_cashflow_quality_direction",
        "metrics": (
            ("operating_cash_flow_yield", 1),
            ("cash_collection_quality", 1),
            ("operating_cash_flow_to_net_profit", 1),
            ("capex_burden", -1),
            ("asset_liability_ratio", -1),
        ),
        "use_case": "infrastructure_cashflow_watch",
    },
)


def run_v5c_financial_statement_expectation_layer(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5c_financial_expectation_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_by_missing_required_input", blockers)
        _write_json(out / "v5c_financial_expectation_summary.json", summary)
        return summary

    p1 = pd.read_csv(root / P1_PANEL, dtype=str)
    valuation = pd.read_csv(root / P2_VALUATION, dtype=str)
    crowding = pd.read_csv(root / P2_CROWDING, dtype=str)
    sleeve_overheat = pd.read_csv(root / P2_SLEEVE_OVERHEAT, dtype=str)
    bank_map = _read_csv(root / BANK_DRIVER_MAP)
    power_map = _read_csv(root / POWER_DRIVER_MAP)
    v5f_metrics = _read_csv(root / V5F_METRICS)

    panel = _join_context(p1, valuation, crowding, sleeve_overheat)
    schema = _expectation_schema()
    knowledge = _knowledge_driver_usage(bank_map, power_map)
    expectation_panel, realized_panel = _build_expectation_panels(panel)
    accuracy = _accuracy_audit(expectation_panel)
    coverage = _coverage_audit(expectation_panel, schema)
    governance = _governance_audit(expectation_panel, v5f_metrics)
    decision = _pm_gate_decision(accuracy, coverage, governance)
    next_queue = _next_queue(decision[0], coverage, accuracy)
    blockers_out = _nonfatal_blockers(coverage, accuracy)

    _write_csv(out / "v5c_financial_expectation_schema.csv", schema)
    _write_csv(out / "v5c_financial_expectation_knowledge_driver_usage.csv", knowledge)
    _write_csv(out / "v5c_financial_expectation_historical_panel.csv", expectation_panel)
    _write_csv(out / "v5c_financial_expectation_realized_next_change_panel.csv", realized_panel)
    _write_csv(out / "v5c_financial_expectation_accuracy_audit.csv", accuracy)
    _write_csv(out / "v5c_financial_expectation_coverage_audit.csv", coverage)
    _write_csv(out / "v5c_financial_expectation_governance_audit.csv", governance)
    _write_csv(out / "v5c_financial_expectation_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_financial_expectation_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5c_financial_expectation_blockers.csv", blockers_out)
    (out / "v5c_financial_expectation_report.md").write_text(
        _report(accuracy, coverage, governance, decision, next_queue),
        encoding="utf-8",
    )
    (out / "v5c_financial_expectation_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    summary = _summary(
        "completed_financial_statement_expectation_layer",
        decision[0]["pm_gate_decision"],
        blockers_out,
        expectation_rows=len(expectation_panel),
        realized_rows=sum(1 for row in expectation_panel if row["realized_direction"] != "pending"),
        predicted_rows=sum(1 for row in expectation_panel if row["predicted_direction"] != "unknown"),
        overall_accuracy=_weighted_accuracy(accuracy, "all_hit_rate"),
        active_signal_accuracy=_weighted_accuracy(accuracy, "active_signal_hit_rate"),
        observation_ready=decision[0]["admit_forward_observation"] == "True",
    )
    _write_json(out / "v5c_financial_expectation_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def _join_context(
    p1: pd.DataFrame,
    valuation: pd.DataFrame,
    crowding: pd.DataFrame,
    sleeve_overheat: pd.DataFrame,
) -> pd.DataFrame:
    val_cols = [
        "trade_date",
        "code",
        "sleeve_id",
        "valuation_state",
        "valuation_cheapness_score",
        "valuation_overheat_score",
        "pit_status",
    ]
    crowd_cols = [
        "trade_date",
        "code",
        "sleeve_id",
        "money_percentile_252d",
        "price_return_20d",
        "price_return_60d",
        "crowding_state",
        "pit_status",
    ]
    sleeve_cols = [
        "trade_date",
        "sleeve_id",
        "avg_valuation_overheat_score",
        "avg_money_percentile_252d",
        "sleeve_benchmark_return_60d",
        "sleeve_overheat_state",
        "pit_status",
    ]
    panel = p1.copy()
    panel = panel.merge(
        valuation[[col for col in val_cols if col in valuation.columns]],
        on=["trade_date", "code", "sleeve_id"],
        how="left",
        suffixes=("", "_valuation"),
    )
    panel = panel.merge(
        crowding[[col for col in crowd_cols if col in crowding.columns]],
        on=["trade_date", "code", "sleeve_id"],
        how="left",
        suffixes=("", "_crowding"),
    )
    panel = panel.merge(
        sleeve_overheat[[col for col in sleeve_cols if col in sleeve_overheat.columns]],
        on=["trade_date", "sleeve_id"],
        how="left",
        suffixes=("", "_sleeve"),
    )
    panel = panel.sort_values(["code", "trade_date"]).reset_index(drop=True)
    return panel


def _expectation_schema() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in EXPECTATION_GROUPS:
        rows.append(
            {
                "expectation_id": group["expectation_id"],
                "sleeve_filter": ";".join(group["sleeve_filter"]),
                "theory_driver": group["theory_driver"],
                "expected_report_state": group["expected_report_state"],
                "metric_set": ";".join(f"{name}:{'higher_better' if direction > 0 else 'lower_better'}" for name, direction in group["metrics"]),
                "prediction_method": "fixed_prior_visible_report_direction_persistence",
                "prediction_values": "improve;stable;deteriorate;unknown",
                "realized_values": "improve;stable;deteriorate;pending",
                "allowed_use": "forward_observation_risk_or_confidence_tag_only",
                "can_change_weight": False,
                "can_trigger_trade": False,
                "can_mark_accepted": False,
            }
        )
    return rows


def _knowledge_driver_usage(bank_map: list[dict[str, str]], power_map: list[dict[str, str]]) -> list[dict[str, Any]]:
    used_drivers = {group["theory_driver"] for group in EXPECTATION_GROUPS}
    rows: list[dict[str, Any]] = []
    for source_name, source_rows in [("bank_driver_map", bank_map), ("power_driver_map", power_map)]:
        for row in source_rows:
            driver = row.get("driver", "")
            rows.append(
                {
                    "knowledge_source": source_name,
                    "industry": row.get("industry", ""),
                    "driver": driver,
                    "metric_or_observation": row.get("metric_or_observation", ""),
                    "proposed_state_tag": row.get("proposed_state_tag", ""),
                    "coverage_status": row.get("coverage_status", ""),
                    "used_in_expectation_layer": str(driver in used_drivers),
                    "used_as_trade_rule": False,
                    "used_as_weight_rule": False,
                }
            )
    rows.append(
        {
            "knowledge_source": "local_extension",
            "industry": "highway_infrastructure;port_rail_infrastructure",
            "driver": "cashflow_dividend_infrastructure",
            "metric_or_observation": "OCF yield, cash collection, OCF/net profit, capex burden, asset liability ratio",
            "proposed_state_tag": "infrastructure_cashflow_quality_watch",
            "coverage_status": "available_in_v5c_p1",
            "used_in_expectation_layer": True,
            "used_as_trade_rule": False,
            "used_as_weight_rule": False,
        }
    )
    return rows


def _build_expectation_panels(panel: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    realized_rows: list[dict[str, Any]] = []
    grouped = {code: group.sort_values("trade_date").reset_index(drop=True) for code, group in panel.groupby("code", sort=True)}
    for code, group in grouped.items():
        for pos, current in group.iterrows():
            prior = group.iloc[pos - 1] if pos > 0 else None
            next_row = group.iloc[pos + 1] if pos + 1 < len(group) else None
            for expectation in EXPECTATION_GROUPS:
                if str(current.get("sleeve_id", "")) not in expectation["sleeve_filter"]:
                    continue
                prediction, prediction_detail = _direction_from_prior(current, prior, expectation["metrics"])
                realized, realized_detail = _direction_to_next(current, next_row, expectation["metrics"])
                confidence = _confidence(prediction_detail, current)
                row = {
                    "expectation_event_id": f"finexp_{len(rows) + 1:06d}",
                    "trade_date": current.get("trade_date", ""),
                    "code": code,
                    "sleeve_id": current.get("sleeve_id", ""),
                    "financial_visible_date": current.get("financial_visible_date", ""),
                    "factor_visible_date": current.get("factor_visible_date", ""),
                    "next_observation_date": "" if next_row is None else next_row.get("trade_date", ""),
                    "expectation_id": expectation["expectation_id"],
                    "theory_driver": expectation["theory_driver"],
                    "predicted_direction": prediction,
                    "prediction_confidence": confidence,
                    "prediction_component_count": prediction_detail["available_count"],
                    "prediction_positive_count": prediction_detail["positive_count"],
                    "prediction_negative_count": prediction_detail["negative_count"],
                    "prediction_stable_count": prediction_detail["stable_count"],
                    "realized_direction": realized,
                    "realized_component_count": realized_detail["available_count"],
                    "realized_positive_count": realized_detail["positive_count"],
                    "realized_negative_count": realized_detail["negative_count"],
                    "realized_stable_count": realized_detail["stable_count"],
                    "direction_hit": _hit(prediction, realized),
                    "valuation_state": current.get("valuation_state", ""),
                    "crowding_state": current.get("crowding_state", ""),
                    "sleeve_overheat_state": current.get("sleeve_overheat_state", ""),
                    "quality_status": current.get("quality_status", ""),
                    "pit_status": _combined_pit_status(current),
                    "allowed_use": "observation_only",
                    "trade_impact": "none",
                    "weight_impact": "none",
                    "accepted": False,
                }
                rows.append(row)
                realized_rows.append(
                    {
                        "expectation_event_id": row["expectation_event_id"],
                        "trade_date": row["trade_date"],
                        "next_observation_date": row["next_observation_date"],
                        "code": code,
                        "sleeve_id": row["sleeve_id"],
                        "expectation_id": row["expectation_id"],
                        "realized_direction": realized,
                        "metric_change_detail": realized_detail["detail"],
                        "current_visible_date": row["financial_visible_date"],
                        "next_visible_date": "" if next_row is None else next_row.get("financial_visible_date", ""),
                        "realized_used_for_signal": False,
                    }
                )
    return rows, realized_rows


def _direction_from_prior(current: pd.Series, prior: pd.Series | None, metrics: tuple[tuple[str, int], ...]) -> tuple[str, dict[str, Any]]:
    if prior is None:
        return "unknown", _direction_detail([], "no_prior_visible_report")
    moves = _oriented_moves(prior, current, metrics)
    return _classify_moves(moves)


def _direction_to_next(current: pd.Series, next_row: pd.Series | None, metrics: tuple[tuple[str, int], ...]) -> tuple[str, dict[str, Any]]:
    if next_row is None:
        return "pending", _direction_detail([], "no_next_visible_report")
    moves = _oriented_moves(current, next_row, metrics)
    direction, detail = _classify_moves(moves)
    if direction == "unknown":
        return "pending", detail
    return direction, detail


def _oriented_moves(left: pd.Series, right: pd.Series, metrics: tuple[tuple[str, int], ...]) -> list[dict[str, Any]]:
    moves: list[dict[str, Any]] = []
    for field, orientation in metrics:
        old = _safe_float(left.get(field))
        new = _safe_float(right.get(field))
        if old is None or new is None:
            continue
        eps = _epsilon(field, old)
        raw_delta = new - old
        oriented_delta = raw_delta * orientation
        if abs(raw_delta) <= eps:
            state = "stable"
        elif oriented_delta > 0:
            state = "positive"
        else:
            state = "negative"
        moves.append(
            {
                "field": field,
                "old": old,
                "new": new,
                "raw_delta": raw_delta,
                "oriented_delta": oriented_delta,
                "state": state,
            }
        )
    return moves


def _classify_moves(moves: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    if not moves:
        return "unknown", _direction_detail(moves, "no_metric_coverage")
    pos = sum(1 for move in moves if move["state"] == "positive")
    neg = sum(1 for move in moves if move["state"] == "negative")
    stable = sum(1 for move in moves if move["state"] == "stable")
    if pos >= 2 and pos > neg:
        direction = "improve"
    elif neg >= 2 and neg > pos:
        direction = "deteriorate"
    elif len(moves) == 1:
        direction = {"positive": "improve", "negative": "deteriorate", "stable": "stable"}[moves[0]["state"]]
    elif stable >= max(pos, neg):
        direction = "stable"
    else:
        direction = "stable"
    return direction, _direction_detail(moves, "classified_from_fixed_metric_set")


def _direction_detail(moves: list[dict[str, Any]], reason: str) -> dict[str, Any]:
    return {
        "available_count": len(moves),
        "positive_count": sum(1 for move in moves if move["state"] == "positive"),
        "negative_count": sum(1 for move in moves if move["state"] == "negative"),
        "stable_count": sum(1 for move in moves if move["state"] == "stable"),
        "detail": ";".join(f"{move['field']}:{move['state']}:{move['raw_delta']:.6g}" for move in moves),
        "reason": reason,
    }


def _confidence(detail: dict[str, Any], current: pd.Series) -> str:
    if detail["available_count"] == 0:
        return "unknown"
    conflict = detail["positive_count"] > 0 and detail["negative_count"] > 0
    pit_ok = _combined_pit_status(current) == "pass"
    if detail["available_count"] >= 3 and not conflict and pit_ok:
        return "high"
    if detail["available_count"] >= 2 and pit_ok:
        return "medium"
    return "low"


def _hit(predicted: str, realized: str) -> str:
    if predicted == "unknown" or realized == "pending":
        return "not_scored"
    return "hit" if predicted == realized else "miss"


def _accuracy_audit(panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in panel:
        grouped[(row["sleeve_id"], row["expectation_id"])].append(row)
    rows: list[dict[str, Any]] = []
    for (sleeve, expectation_id), group in sorted(grouped.items()):
        scored = [row for row in group if row["direction_hit"] in {"hit", "miss"}]
        active = [row for row in scored if row["predicted_direction"] != "stable"]
        hits = sum(1 for row in scored if row["direction_hit"] == "hit")
        active_hits = sum(1 for row in active if row["direction_hit"] == "hit")
        rows.append(
            {
                "sleeve_id": sleeve,
                "expectation_id": expectation_id,
                "event_count": len(group),
                "scored_count": len(scored),
                "hit_count": hits,
                "miss_count": len(scored) - hits,
                "all_hit_rate": _ratio(hits, len(scored)),
                "active_signal_count": len(active),
                "active_signal_hit_count": active_hits,
                "active_signal_hit_rate": _ratio(active_hits, len(active)),
                "prediction_distribution": _counter(group, "predicted_direction"),
                "realized_distribution": _counter(group, "realized_direction"),
                "accuracy_role": "diagnostic_replay_not_validation",
            }
        )
    rows.append(_overall_accuracy_row(panel))
    return rows


def _overall_accuracy_row(panel: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [row for row in panel if row["direction_hit"] in {"hit", "miss"}]
    active = [row for row in scored if row["predicted_direction"] != "stable"]
    hits = sum(1 for row in scored if row["direction_hit"] == "hit")
    active_hits = sum(1 for row in active if row["direction_hit"] == "hit")
    return {
        "sleeve_id": "ALL",
        "expectation_id": "ALL",
        "event_count": len(panel),
        "scored_count": len(scored),
        "hit_count": hits,
        "miss_count": len(scored) - hits,
        "all_hit_rate": _ratio(hits, len(scored)),
        "active_signal_count": len(active),
        "active_signal_hit_count": active_hits,
        "active_signal_hit_rate": _ratio(active_hits, len(active)),
        "prediction_distribution": _counter(panel, "predicted_direction"),
        "realized_distribution": _counter(panel, "realized_direction"),
        "accuracy_role": "diagnostic_replay_not_validation",
    }


def _coverage_audit(panel: list[dict[str, Any]], schema: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    schema_by_id = {row["expectation_id"]: row for row in schema}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in panel:
        grouped[row["expectation_id"]].append(row)
    for expectation_id, group in sorted(grouped.items()):
        predicted = [row for row in group if row["predicted_direction"] != "unknown"]
        realized = [row for row in group if row["realized_direction"] != "pending"]
        high_medium = [row for row in group if row["prediction_confidence"] in {"high", "medium"}]
        rows.append(
            {
                "expectation_id": expectation_id,
                "sleeve_filter": schema_by_id.get(expectation_id, {}).get("sleeve_filter", ""),
                "event_count": len(group),
                "predicted_count": len(predicted),
                "prediction_coverage": _ratio(len(predicted), len(group)),
                "realized_count": len(realized),
                "realized_coverage": _ratio(len(realized), len(group)),
                "medium_or_high_confidence_count": len(high_medium),
                "medium_or_high_confidence_coverage": _ratio(len(high_medium), len(group)),
                "coverage_status": "pass" if len(predicted) and len(realized) else "review",
            }
        )
    return rows


def _governance_audit(panel: list[dict[str, Any]], v5f_metrics: list[dict[str, str]]) -> list[dict[str, Any]]:
    primary_present = any(row.get("version_id") == PRIMARY_V5F for row in v5f_metrics)
    backtest_rows = [row for row in panel if BACKTEST_START <= str(row["trade_date"]) <= BACKTEST_END]
    return [
        _audit("p1_p2_pit_status", all(row["pit_status"] == "pass" for row in panel), f"rows={len(panel)}"),
        _audit("v5f_primary_reference_present", primary_present, PRIMARY_V5F),
        _audit("no_trade_rule_added", True, "expectation layer outputs observation tags only"),
        _audit("no_weight_change_added", True, "no V57f or V5f target weights are modified"),
        _audit("no_threshold_scan_used", True, "fixed theory metric groups; no parameter search"),
        _audit("formal_backtest_scope_not_used_as_validation", True, f"diagnostic replay rows in {BACKTEST_START}..{BACKTEST_END}: {len(backtest_rows)}"),
        _audit("accepted_false", True, "not accepted and not live approved"),
    ]


def _pm_gate_decision(
    accuracy: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    governance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fatal = [row for row in governance if row["audit_status"] != "pass"]
    overall = next((row for row in accuracy if row["expectation_id"] == "ALL"), {})
    scored_count = int(overall.get("scored_count", 0) or 0)
    predicted_total = sum(int(row.get("predicted_count", 0) or 0) for row in coverage)
    event_total = sum(int(row.get("event_count", 0) or 0) for row in coverage)
    prediction_coverage = _ratio(predicted_total, event_total)
    if fatal:
        gate = "blocked_by_data_or_pit_issue"
        admit = False
    elif scored_count >= 50 and prediction_coverage > 0.5:
        gate = "expectation_layer_observation_ready_not_trading"
        admit = True
    else:
        gate = "expectation_layer_diagnostic_only"
        admit = True
    return [
        {
            "pm_gate_decision": gate,
            "admit_forward_observation": str(admit),
            "admit_weight_change": False,
            "admit_trading_rule": False,
            "admit_engineering_backtest": False,
            "accepted": False,
            "live_approved": False,
            "v57f_core_modified": False,
            "v5f_primary_modified": False,
            "threshold_scan_used": False,
            "formal_backtest_used_as_validation": False,
            "next_step": "open_forward_financial_statement_tracking" if admit else "repair_pit_or_panel_dependency",
            "review_notes": "Use theory and knowledge base as next-report observation tags; do not replace statistically validated V5f weights.",
        }
    ]


def _next_queue(
    decision: dict[str, Any],
    coverage: list[dict[str, Any]],
    accuracy: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    overall = next((row for row in accuracy if row["expectation_id"] == "ALL"), {})
    low_coverage = [row["expectation_id"] for row in coverage if row["coverage_status"] != "pass"]
    return [
        {
            "priority": 1,
            "next_gate": "v5c_forward_financial_statement_tracking",
            "allowed": decision["admit_forward_observation"],
            "scope": "Track future visible quarterly or annual report changes against pre-recorded expectation tags.",
            "requires_weight_change": False,
            "requires_trade_rule": False,
            "blocked_until": "",
        },
        {
            "priority": 2,
            "next_gate": "v5f_weight_confidence_tag_spec",
            "allowed": "True" if decision["pm_gate_decision"] == "expectation_layer_observation_ready_not_trading" else "False",
            "scope": "Design a separate spec for how expectation tags may annotate, but not resize, V5f primary weights.",
            "requires_weight_change": "separate_pm_approval_before_any_backtest",
            "requires_trade_rule": False,
            "blocked_until": "forward tracking or independent pre-2021 panel confirms usefulness",
        },
        {
            "priority": 3,
            "next_gate": "pre2021_financial_expectation_panel_extension",
            "allowed": "True",
            "scope": "Extend P1-style financial statement expectation replay to pre-2021 where PIT fields exist.",
            "requires_weight_change": False,
            "requires_trade_rule": False,
            "blocked_until": ";".join(low_coverage) if low_coverage else "",
        },
        {
            "priority": 4,
            "next_gate": "expectation_accuracy_recheck",
            "allowed": "True",
            "scope": f"Recheck after more reports; current overall active hit rate={overall.get('active_signal_hit_rate', '')}.",
            "requires_weight_change": False,
            "requires_trade_rule": False,
            "blocked_until": "additional forward financial statements",
        },
    ]


def _nonfatal_blockers(coverage: list[dict[str, Any]], accuracy: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for row in coverage:
        if row["coverage_status"] != "pass":
            blockers.append(
                {
                    "blocker_id": f"coverage_{row['expectation_id']}",
                    "severity": "nonfatal",
                    "status": "review",
                    "description": "Prediction or realized next-report coverage is incomplete.",
                    "next_action": "extend or repair the relevant PIT financial report panel",
                }
            )
    overall = next((row for row in accuracy if row["expectation_id"] == "ALL"), {})
    if float(overall.get("active_signal_hit_rate", 0.0) or 0.0) < 0.5:
        blockers.append(
            {
                "blocker_id": "active_signal_accuracy_below_observation_threshold",
                "severity": "nonfatal",
                "status": "diagnostic",
                "description": "Active improve/deteriorate tags are not yet reliable enough for any weight discussion.",
                "next_action": "keep as forward observation only",
            }
        )
    return blockers


def _report(
    accuracy: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    governance: list[dict[str, Any]],
    decision: list[dict[str, Any]],
    next_queue: list[dict[str, Any]],
) -> str:
    overall = next((row for row in accuracy if row["expectation_id"] == "ALL"), {})
    coverage_lines = "\n".join(
        f"- {row['expectation_id']}: prediction coverage {float(row['prediction_coverage']):.2%}, realized coverage {float(row['realized_coverage']):.2%}"
        for row in coverage
    )
    accuracy_lines = "\n".join(
        f"- {row['sleeve_id']} / {row['expectation_id']}: hit {float(row['all_hit_rate']):.2%}, active hit {float(row['active_signal_hit_rate']):.2%}, scored {row['scored_count']}"
        for row in accuracy
        if row["expectation_id"] != "ALL"
    )
    gov_lines = "\n".join(f"- {row['audit_id']}: {row['audit_status']}" for row in governance)
    queue_lines = "\n".join(f"- P{row['priority']} {row['next_gate']}: allowed={row['allowed']}" for row in next_queue)
    return f"""# V5c Financial Statement Expectation Layer

## Purpose
This packet uses the new bank/power knowledge base and local PIT financial panels to create a next-report expectation layer. It is an observation layer only. It does not alter V57f, V5f, target weights, trade rules, or accepted status.

## Historical Replay
- Replay window role: diagnostic replay, not validation or parameter selection.
- Overall scored rows: {overall.get('scored_count', 0)}
- Overall hit rate: {float(overall.get('all_hit_rate', 0.0) or 0.0):.2%}
- Active improve/deteriorate hit rate: {float(overall.get('active_signal_hit_rate', 0.0) or 0.0):.2%}

## Coverage
{coverage_lines}

## Accuracy By Expectation
{accuracy_lines}

## Governance
{gov_lines}

## PM Gate
- Decision: {decision[0]['pm_gate_decision']}
- Accepted: false
- V5f primary modified: false
- Weight or trade impact: none

## Next Queue
{queue_lines}
"""


def _agent_rules() -> str:
    return """# Agent Execution Rules

- Use repaired V57f / V5f primary context only.
- Treat the layer as next-report observation and attribution.
- Do not change V57f core.
- Do not change V5f primary weights.
- Do not create buy/sell signals.
- Do not use 2021-05-01 to 2026-05-31 as validation or parameter discovery.
- Do not mark accepted or live approved.
- Future use in weights requires a separate PM/Quant spec and independent evidence.
"""


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        P1_PANEL,
        P1_SUMMARY,
        P2_VALUATION,
        P2_CROWDING,
        P2_SLEEVE_OVERHEAT,
        BANK_DRIVER_MAP,
        POWER_DRIVER_MAP,
        V5F_METRICS,
    ]
    blockers = []
    for rel in required:
        if not (root / rel).exists():
            blockers.append(
                {
                    "blocker_id": str(rel).replace("\\", "/"),
                    "severity": "fatal",
                    "status": "missing_required_input",
                    "description": "Required local input was not found.",
                }
            )
    return blockers


def _combined_pit_status(row: pd.Series) -> str:
    statuses = [
        str(row.get("visible_date_status", "")),
        str(row.get("pit_status", "")),
        str(row.get("pit_status_crowding", "")),
        str(row.get("pit_status_sleeve", "")),
    ]
    statuses = [status for status in statuses if status and status != "nan"]
    return "pass" if all(status == "pass" for status in statuses) else "review"


def _epsilon(field: str, old: float) -> float:
    base = max(abs(old) * 0.02, 0.001)
    if field in {"non_performing_loan_ratio", "core_tier_1_capital_adequacy_ratio", "return_on_equity_ttm"}:
        return max(base, 0.02)
    if field in {"provision_coverage_ratio"}:
        return max(base, 1.0)
    return base


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(parsed):
        return None
    return parsed


def _audit(audit_id: str, passed: bool, observed: str) -> dict[str, Any]:
    return {
        "audit_id": audit_id,
        "audit_status": "pass" if passed else "fail",
        "observed": observed,
        "required": True,
    }


def _counter(rows: list[dict[str, Any]], field: str) -> str:
    counts = Counter(str(row.get(field, "")) for row in rows)
    return ";".join(f"{key}:{counts[key]}" for key in sorted(counts))


def _ratio(num: int | float, den: int | float) -> float:
    return float(num) / float(den) if den else 0.0


def _weighted_accuracy(rows: list[dict[str, Any]], field: str) -> float:
    overall = next((row for row in rows if row.get("expectation_id") == "ALL"), None)
    return float(overall.get(field, 0.0) or 0.0) if overall else 0.0


def _summary(status: str, gate: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "status": status,
        "pm_gate_decision": gate,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "accepted": False,
        "live_approved": False,
        "v57f_core_modified": False,
        "v5f_primary_modified": False,
        "new_strategy_rule_added": False,
        "trade_rule_added": False,
        "weight_change_added": False,
        "threshold_scan_used": False,
        "formal_backtest_used_as_validation": False,
        "fatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "fatal"),
        "blocker_count": len(blockers),
    }
    summary.update(extra)
    return summary


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    run_v5c_financial_statement_expectation_layer()

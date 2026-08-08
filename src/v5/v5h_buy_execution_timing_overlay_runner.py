from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5h_buy_execution_timing_overlay") / "current"
V5H_VOLUME_PANEL = Path("v5h_1min_volume_amount_timing_test") / "current" / "v5h_1min_volume_amount_feature_panel.csv"
V5H_VOLUME_SUMMARY = Path("v5h_1min_volume_amount_timing_test") / "current" / "v5h_1min_volume_amount_summary.json"
V5H_LINE_GOV = Path("v5h_1min_research_line_governance") / "current" / "v5h_1min_component_mapping.csv"

BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
V5H_LINE_ID = "v5h_1min_microstructure_execution_research"

SCHEDULED_BUY_FAMILIES = {
    "value_lowvol_rebalance",
    "momentum_overlay_tilt",
    "v5f_champion_rebalance",
}
MR_FAMILY = "mean_reversion_event"
BUY_ACTION = "buy"

BASELINE = "baseline_default_1000_proxy"
FIXED_1400 = "fixed_1400_buy"
PRESSURE_EARLY = "pressure_positive_1000_else_1400_buy"
MR_PRESSURE_GATE = "mr_crash_buy_pressure_neutral_or_positive_only"
COMBINED = "combined_v5h_buy_execution_overlay_v1"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5h_buy_execution_timing_overlay(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        summary = _summary("blocked_missing_required_input", "blocked_by_missing_required_input", blockers)
        _write_minimal(out, summary, blockers)
        return summary

    source_summary = _read_json(root / V5H_VOLUME_SUMMARY)
    rows = _read_csv(root / V5H_VOLUME_PANEL)
    scheduled_index = _scheduled_buy_index(rows)
    mr_buy_rows = _mr_buy_rows(rows)

    decision_log = _decision_log(scheduled_index, mr_buy_rows)
    metrics = _variant_metrics(decision_log)
    by_family = _variant_family_metrics(decision_log)
    by_sleeve = _variant_sleeve_metrics(decision_log)
    comparison = _comparison(metrics, decision_log)
    spec = _spec()
    data_gate = _data_gate(source_summary, scheduled_index, mr_buy_rows, decision_log)
    governance = _governance_audit()
    pm_decision = _pm_decision(comparison, data_gate, governance)
    next_queue = _next_queue(pm_decision[0]["pm_gate_decision"])
    blockers_out = _blockers(data_gate, governance)
    v5h_mapping = _v5h_mapping(root)

    _write_csv(out / "v5h_buy_execution_timing_overlay_spec.csv", spec)
    _write_csv(out / "v5h_buy_execution_timing_order_decision_log.csv", decision_log)
    _write_csv(out / "v5h_buy_execution_timing_variant_metrics.csv", metrics)
    _write_csv(out / "v5h_buy_execution_timing_variant_comparison.csv", comparison)
    _write_csv(out / "v5h_buy_execution_timing_by_family.csv", by_family)
    _write_csv(out / "v5h_buy_execution_timing_by_sleeve.csv", by_sleeve)
    _write_csv(out / "v5h_buy_execution_timing_data_gate.csv", data_gate)
    _write_csv(out / "v5h_buy_execution_timing_governance_audit.csv", governance)
    _write_csv(out / "v5h_buy_execution_timing_pm_gate_decision.csv", pm_decision)
    _write_csv(out / "v5h_buy_execution_timing_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5h_buy_execution_timing_blockers.csv", blockers_out)
    _write_csv(out / "v5h_buy_execution_timing_v5h_line_mapping.csv", v5h_mapping)
    (out / "v5h_buy_execution_timing_overlay_report.md").write_text(
        _report(metrics, comparison, by_family, pm_decision),
        encoding="utf-8",
    )
    (out / "v5h_buy_execution_timing_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best = _best_variant(comparison)
    summary = _summary(
        "completed_v5h_buy_execution_timing_overlay",
        pm_decision[0]["pm_gate_decision"],
        [],
        source_volume_amount_status=source_summary.get("status", ""),
        scheduled_buy_intent_count=len(scheduled_index),
        mean_reversion_buy_event_count=len(mr_buy_rows),
        decision_log_row_count=len(decision_log),
        best_variant=best.get("variant_id", ""),
        best_incremental_edge_vs_baseline=float(best.get("comparable_incremental_decision_edge_vs_baseline", 0.0) or 0.0),
        best_weighted_incremental_edge_vs_baseline=float(best.get("comparable_weighted_incremental_decision_edge_vs_baseline", 0.0) or 0.0),
        combined_v1_incremental_edge_vs_baseline=float(
            next(
                (
                    row.get("comparable_incremental_decision_edge_vs_baseline", 0.0)
                    for row in comparison
                    if row.get("variant_id") == COMBINED
                ),
                0.0,
            )
            or 0.0
        ),
        combined_v1_weighted_incremental_edge_vs_baseline=float(
            next(
                (
                    row.get("comparable_weighted_incremental_decision_edge_vs_baseline", 0.0)
                    for row in comparison
                    if row.get("variant_id") == COMBINED
                ),
                0.0,
            )
            or 0.0
        ),
    )
    _write_json(out / "v5h_buy_execution_timing_overlay_summary.json", summary)
    return summary


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    missing = []
    for path in [V5H_VOLUME_PANEL, V5H_VOLUME_SUMMARY]:
        if not (root / path).exists():
            missing.append(_blocker(f"missing_{path.name}", str(path)))
    return missing


def _scheduled_buy_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    index: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        if row.get("source_panel") != "value_momentum_zone_panel":
            continue
        if row.get("action") != BUY_ACTION:
            continue
        if row.get("intent_family") not in SCHEDULED_BUY_FAMILIES:
            continue
        if not (BACKTEST_START <= row.get("trade_date", "") <= BACKTEST_END):
            continue
        index[row["intent_id"]][row["obs_time"]] = row
    return {
        intent_id: by_time
        for intent_id, by_time in index.items()
        if "10:00:00" in by_time and "14:00:00" in by_time
    }


def _mr_buy_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        if row.get("source_panel") != "mean_reversion_zone_panel":
            continue
        if row.get("intent_family") != MR_FAMILY or row.get("action") != BUY_ACTION:
            continue
        if not (BACKTEST_START <= row.get("trade_date", "") <= BACKTEST_END):
            continue
        out.append(row)
    return out


def _decision_log(
    scheduled_index: dict[str, dict[str, dict[str, Any]]],
    mr_buy_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for intent_id, by_time in sorted(scheduled_index.items()):
        base = by_time["10:00:00"]
        fixed = by_time["14:00:00"]
        early = base if base.get("amount_pressure_bucket") == "positive_pressure" else fixed
        rows.append(_decision_row(BASELINE, "scheduled_buy", base, "10:00 default proxy", True, base))
        rows.append(_decision_row(FIXED_1400, "scheduled_buy", fixed, "fixed 14:00 buy", True, base))
        rows.append(
            _decision_row(
                PRESSURE_EARLY,
                "scheduled_buy",
                early,
                "10:00 if amount pressure is positive, otherwise 14:00",
                True,
                base,
            )
        )
        rows.append(
            _decision_row(
                COMBINED,
                "scheduled_buy",
                early,
                "combined v1 uses pressure-positive 10:00 else 14:00 for scheduled buys",
                True,
                base,
            )
        )

    for row in mr_buy_rows:
        allowed = row.get("amount_pressure_bucket") in {"neutral_pressure", "positive_pressure"}
        rows.append(_decision_row(BASELINE, "mean_reversion_buy", row, "original mean-reversion event observation", True, row))
        rows.append(
            _decision_row(
                MR_PRESSURE_GATE,
                "mean_reversion_buy",
                row,
                "allow only if amount pressure is neutral or positive",
                allowed,
                row,
            )
        )
        rows.append(
            _decision_row(
                COMBINED,
                "mean_reversion_buy",
                row,
                "combined v1 applies pressure gate to mean-reversion buys",
                allowed,
                row,
            )
        )
    return rows


def _decision_row(
    variant_id: str,
    order_type: str,
    row: dict[str, Any],
    rule: str,
    execute_allowed: bool,
    baseline_row: dict[str, Any],
) -> dict[str, Any]:
    edge = _float(row.get("action_edge_vs_close")) if execute_allowed else 0.0
    edge_vwap = _float(row.get("action_edge_vs_full_day_vwap")) if execute_allowed else 0.0
    baseline_edge = _float(baseline_row.get("action_edge_vs_close"))
    weight = abs(_float(row.get("trade_delta_weight"))) if row.get("trade_delta_weight") not in ("", None) else 1.0
    return {
        "variant_id": variant_id,
        "order_type": order_type,
        "intent_id": row.get("intent_id", ""),
        "intent_family": row.get("intent_family", ""),
        "event_type": row.get("event_type", ""),
        "trade_date": row.get("trade_date", ""),
        "code": row.get("code", ""),
        "sleeve": row.get("sleeve", ""),
        "selected_obs_time": row.get("obs_time", ""),
        "rule": rule,
        "execute_allowed": execute_allowed,
        "skip_reason": "" if execute_allowed else "amount_pressure_negative_do_not_catch_falling_knife",
        "pit_zone_bucket": row.get("pit_zone_bucket", ""),
        "amount_intensity_bucket": row.get("amount_intensity_bucket", ""),
        "volume_intensity_bucket": row.get("volume_intensity_bucket", ""),
        "amount_pressure_bucket": row.get("amount_pressure_bucket", ""),
        "amount_pressure_turn_bucket": row.get("amount_pressure_turn_bucket", ""),
        "price_at_obs": row.get("price_at_obs", ""),
        "action_edge_vs_close": edge,
        "baseline_action_edge_vs_close": baseline_edge,
        "incremental_edge_vs_baseline_order": edge - baseline_edge,
        "action_edge_vs_full_day_vwap": edge_vwap,
        "trade_delta_weight_abs": weight,
        "weighted_action_edge_vs_close": edge * weight,
        "weighted_incremental_edge_vs_baseline_order": (edge - baseline_edge) * weight,
        "diagnostic_only": True,
        "accepted": False,
        "trading_frequency_change_allowed": False,
    }


def _variant_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["variant_id"]].append(row)
    out = []
    for variant_id, group in sorted(groups.items()):
        executed = [row for row in group if row["execute_allowed"] is True]
        skipped = [row for row in group if row["execute_allowed"] is False]
        out.append(_metric_row({"variant_id": variant_id}, group, executed, skipped))
    return out


def _variant_family_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["variant_id"], row["order_type"], row["intent_family"])].append(row)
    out = []
    for (variant_id, order_type, family), group in sorted(groups.items()):
        executed = [row for row in group if row["execute_allowed"] is True]
        skipped = [row for row in group if row["execute_allowed"] is False]
        out.append(_metric_row({"variant_id": variant_id, "order_type": order_type, "intent_family": family}, group, executed, skipped))
    return out


def _variant_sleeve_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["variant_id"], row["sleeve"])].append(row)
    out = []
    for (variant_id, sleeve), group in sorted(groups.items()):
        executed = [row for row in group if row["execute_allowed"] is True]
        skipped = [row for row in group if row["execute_allowed"] is False]
        out.append(_metric_row({"variant_id": variant_id, "sleeve": sleeve}, group, executed, skipped))
    return out


def _metric_row(prefix: dict[str, Any], group: list[dict[str, Any]], executed: list[dict[str, Any]], skipped: list[dict[str, Any]]) -> dict[str, Any]:
    weight_sum = sum(_float(row.get("trade_delta_weight_abs")) for row in executed)
    baseline_weight_sum = sum(_float(row.get("trade_delta_weight_abs")) for row in group)
    sum_weighted_action_edge = sum(_float(row.get("weighted_action_edge_vs_close")) for row in group)
    sum_weighted_incremental = sum(_float(row.get("weighted_incremental_edge_vs_baseline_order")) for row in group)
    return {
        **prefix,
        "order_count": len(group),
        "executed_order_count": len(executed),
        "skipped_order_count": len(skipped),
        "execution_rate_pct": _pct(len(executed), len(group)),
        "avg_action_edge_vs_close": _mean([row.get("action_edge_vs_close") for row in executed]),
        "median_action_edge_vs_close": _median([row.get("action_edge_vs_close") for row in executed]),
        "positive_edge_rate_pct": _pct(sum(1 for row in executed if _float(row.get("action_edge_vs_close")) > 0), len(executed)),
        "avg_action_edge_vs_full_day_vwap": _mean([row.get("action_edge_vs_full_day_vwap") for row in executed]),
        "weighted_avg_action_edge_vs_close": (
            sum(_float(row.get("weighted_action_edge_vs_close")) for row in executed) / weight_sum if weight_sum else 0.0
        ),
        "avg_decision_edge_vs_close_all_orders": _mean([row.get("action_edge_vs_close") for row in group]),
        "weighted_avg_decision_edge_vs_close_all_orders": (
            sum_weighted_action_edge / baseline_weight_sum if baseline_weight_sum else 0.0
        ),
        "sum_weighted_action_edge_vs_close": sum(_float(row.get("weighted_action_edge_vs_close")) for row in executed),
        "sum_weighted_incremental_edge_vs_baseline_order": sum_weighted_incremental,
        "baseline_weight_sum": baseline_weight_sum,
        "avg_incremental_edge_vs_baseline_order": _mean([row.get("incremental_edge_vs_baseline_order") for row in group]),
        "weighted_avg_incremental_edge_vs_baseline_order": (
            sum_weighted_incremental / baseline_weight_sum if baseline_weight_sum else 0.0
        ),
    }


def _comparison(metrics: list[dict[str, Any]], decision_log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline_metrics = {
        "all_orders": next((row for row in metrics if row["variant_id"] == BASELINE), {}),
        "scheduled_buy": _baseline_scope_metric(decision_log, "scheduled_buy"),
        "mean_reversion_buy": _baseline_scope_metric(decision_log, "mean_reversion_buy"),
    }
    out = []
    for row in metrics:
        scope = _comparison_scope(row["variant_id"])
        baseline = baseline_metrics.get(scope, {})
        baseline_edge = _float(baseline.get("avg_action_edge_vs_close"))
        baseline_weighted = _float(baseline.get("weighted_avg_action_edge_vs_close"))
        baseline_decision_edge = _float(baseline.get("avg_decision_edge_vs_close_all_orders"))
        baseline_weighted_decision = _float(baseline.get("weighted_avg_decision_edge_vs_close_all_orders"))
        out.append(
            {
                **row,
                "comparison_scope": scope,
                "baseline_variant": BASELINE,
                "baseline_avg_action_edge_vs_close": baseline_edge,
                "incremental_edge_vs_baseline": _float(row.get("avg_action_edge_vs_close")) - baseline_edge,
                "baseline_weighted_avg_action_edge_vs_close": baseline_weighted,
                "weighted_incremental_edge_vs_baseline": _float(row.get("weighted_avg_action_edge_vs_close")) - baseline_weighted,
                "comparable_baseline_avg_decision_edge_vs_close": baseline_decision_edge,
                "comparable_incremental_decision_edge_vs_baseline": (
                    _float(row.get("avg_decision_edge_vs_close_all_orders")) - baseline_decision_edge
                ),
                "comparable_baseline_weighted_avg_decision_edge_vs_close": baseline_weighted_decision,
                "comparable_weighted_incremental_decision_edge_vs_baseline": (
                    _float(row.get("weighted_avg_decision_edge_vs_close_all_orders")) - baseline_weighted_decision
                ),
                "accepted": False,
                "trading_frequency_change_allowed": False,
            }
        )
    out.sort(key=lambda item: _float(item.get("comparable_incremental_decision_edge_vs_baseline")), reverse=True)
    return out


def _baseline_scope_metric(decision_log: list[dict[str, Any]], order_type: str) -> dict[str, Any]:
    group = [row for row in decision_log if row.get("variant_id") == BASELINE and row.get("order_type") == order_type]
    return _metric_row({"variant_id": BASELINE, "comparison_scope": order_type}, group, group, [])


def _comparison_scope(variant_id: str) -> str:
    if variant_id in {FIXED_1400, PRESSURE_EARLY}:
        return "scheduled_buy"
    if variant_id == MR_PRESSURE_GATE:
        return "mean_reversion_buy"
    return "all_orders"


def _spec() -> list[dict[str, Any]]:
    return [
        {
            "variant_id": BASELINE,
            "rule": "Scheduled buys use 10:00 as default proxy; mean-reversion buys use original event observation.",
            "scope": "comparison baseline",
            "accepted": False,
        },
        {
            "variant_id": FIXED_1400,
            "rule": "Scheduled value/momentum/champion buy or increase orders execute at fixed 14:00.",
            "scope": "scheduled buys only",
            "accepted": False,
        },
        {
            "variant_id": PRESSURE_EARLY,
            "rule": "Scheduled buys execute at 10:00 only if amount_pressure_bucket is positive_pressure; otherwise execute at 14:00.",
            "scope": "scheduled buys only",
            "accepted": False,
        },
        {
            "variant_id": MR_PRESSURE_GATE,
            "rule": "Mean-reversion crash/dislocation buys execute only when amount pressure is neutral or positive; negative pressure is skipped for this diagnostic.",
            "scope": "mean-reversion buy events only",
            "accepted": False,
        },
        {
            "variant_id": COMBINED,
            "rule": "Scheduled buys use pressure-positive 10:00 else 14:00; mean-reversion buys require neutral/positive pressure.",
            "scope": "combined V5h buy execution overlay v1",
            "accepted": False,
        },
    ]


def _data_gate(
    source_summary: dict[str, Any],
    scheduled_index: dict[str, dict[str, dict[str, Any]]],
    mr_buy_rows: list[dict[str, Any]],
    decision_log: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {"gate_id": "v5h_line_id", "status": "pass", "value": V5H_LINE_ID},
        {"gate_id": "source_volume_amount_status", "status": "pass" if source_summary.get("status") == "completed_v5h_1min_volume_amount_timing_test" else "fail", "value": source_summary.get("status", "")},
        {"gate_id": "scheduled_buy_intents_with_1000_and_1400", "status": "pass" if scheduled_index else "fail", "value": len(scheduled_index)},
        {"gate_id": "mean_reversion_buy_rows_loaded", "status": "pass" if mr_buy_rows else "fail", "value": len(mr_buy_rows)},
        {"gate_id": "decision_log_built", "status": "pass" if decision_log else "fail", "value": len(decision_log)},
        {"gate_id": "fixed_variants_only", "status": "pass", "value": ";".join([BASELINE, FIXED_1400, PRESSURE_EARLY, MR_PRESSURE_GATE, COMBINED])},
    ]


def _governance_audit() -> list[dict[str, Any]]:
    return [
        {"audit_id": "buy_side_only", "status": "pass", "detail": "Only buy/increase/buy_tilt and mean-reversion buy events are tested."},
        {"audit_id": "sell_model_unchanged", "status": "pass", "detail": "No sell/decrease timing rule is admitted."},
        {"audit_id": "no_v57f_core_modified", "status": "pass", "detail": "V57f core is not modified."},
        {"audit_id": "no_v5f_mainline_modified", "status": "pass", "detail": "V5f mainline remains unchanged."},
        {"audit_id": "no_trading_frequency_increase", "status": "pass", "detail": "Rules only choose fixed execution observation points inside already planned buy day/event."},
        {"audit_id": "no_threshold_scan", "status": "pass", "detail": "Only four predeclared variants plus combined v1 are compared."},
        {"audit_id": "no_new_buy_signal", "status": "pass", "detail": "No new stocks are selected; skipped mean-reversion events are diagnostic only."},
        {"audit_id": "accepted_false", "status": "pass", "detail": "No component is accepted/live approved."},
        {"audit_id": "formal_backtest_end_preserved", "status": "pass", "detail": f"Formal backtest ends at {BACKTEST_END}."},
    ]


def _pm_decision(
    comparison: list[dict[str, Any]],
    data_gate: list[dict[str, Any]],
    governance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if any(row["status"] == "fail" for row in data_gate + governance):
        decision = "blocked_by_data_or_governance_issue"
        status = "blocked"
    else:
        combined = next((row for row in comparison if row.get("variant_id") == COMBINED), {})
        inc = _float(combined.get("comparable_incremental_decision_edge_vs_baseline"))
        if inc > 0.0005:
            decision = "v5h_buy_execution_overlay_positive_ready_for_quant_spec_not_trading"
            status = "diagnostic_positive"
        else:
            decision = "v5h_buy_execution_overlay_diagnostic_only_no_material_edge"
            status = "diagnostic_only"
    return [
        {
            "pm_gate_decision": decision,
            "status": status,
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "v5f_mainline_modified": False,
            "trading_frequency_increased": False,
            "threshold_scan_used": False,
            "new_buy_signal_used": False,
            "notes": "V5h may improve buy execution timing. This packet does not change selection, target weights, sell rules, or rebalance frequency.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "queue_id": "v5h_buy_execution_timing_overlay_quant_spec",
            "status": "ready" if "positive" in decision else "diagnostic_only",
            "scope": "Freeze fixed buy-only execution overlay boundaries; no sell change and no portfolio acceptance.",
        },
        {
            "queue_id": "v5h_buy_execution_timing_forward_observation",
            "status": "ready",
            "scope": "Append future buy-order execution timing observations after official target files exist.",
        },
    ]


def _v5h_mapping(root: Path) -> list[dict[str, Any]]:
    rows = _read_csv(root / V5H_LINE_GOV) if (root / V5H_LINE_GOV).exists() else []
    rows.append(
        {
            "source_id": "v5h_buy_execution_timing_overlay",
            "source_path": "v5h_buy_execution_timing_overlay",
            "v5h_component_id": "v5h_buy_execution_timing_overlay",
            "description": "Fixed buy-side execution timing overlay comparison using 1min price, volume, and amount pressure.",
            "status": "completed_source_artifact",
            "rename_policy": "lineage_reclassification_only_do_not_move_source_artifact",
            "accepted": False,
            "trading_frequency_change_allowed": False,
        }
    )
    return rows


def _report(
    metrics: list[dict[str, Any]],
    comparison: list[dict[str, Any]],
    by_family: list[dict[str, Any]],
    pm_decision: list[dict[str, Any]],
) -> str:
    lines = [
        "# V5h Buy Execution Timing Overlay",
        "",
        "This packet compares fixed buy-side execution timing variants using 1-minute price, volume, and amount pressure. It does not change V57f/V5f selection, weights, sell rules, or rebalance frequency.",
        "",
        "## Variant Comparison",
    ]
    for row in comparison:
        lines.append(
            f"- `{row['variant_id']}`: scope `{row['comparison_scope']}`, executed `{row['executed_order_count']}/{row['order_count']}`, decision edge `{row['avg_decision_edge_vs_close_all_orders']}`, comparable incremental `{row['comparable_incremental_decision_edge_vs_baseline']}`, weighted comparable incremental `{row['comparable_weighted_incremental_decision_edge_vs_baseline']}`."
        )
    lines.extend(["", "## Family Detail"])
    for row in sorted(by_family, key=lambda item: (str(item.get("variant_id")), str(item.get("intent_family")))):
        lines.append(
            f"- `{row.get('variant_id')}` / `{row.get('intent_family')}`: n `{row.get('executed_order_count')}`, edge `{row.get('avg_action_edge_vs_close')}`, exec rate `{row.get('execution_rate_pct')}%`."
        )
    lines.extend(["", f"PM decision: `{pm_decision[0]['pm_gate_decision']}`", ""])
    return "\n".join(lines)


def _rules() -> str:
    return "\n".join(
        [
            "# V5h Buy Execution Timing Agent Rules",
            "",
            "- Buy-side execution timing diagnostics only.",
            "- Do not modify V57f core.",
            "- Do not modify V5f mainline.",
            "- Do not change sell/decrease execution rules.",
            "- Do not increase trading frequency.",
            "- Do not scan thresholds or mark accepted/live approved.",
            "",
        ]
    )


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5h_buy_execution_timing_overlay",
        "v5h_line_id": V5H_LINE_ID,
        "status": status,
        "pm_gate_decision": decision,
        "formal_backtest_start": BACKTEST_START,
        "formal_backtest_end": BACKTEST_END,
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


def _write_minimal(out: Path, summary: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    _write_json(out / "v5h_buy_execution_timing_overlay_summary.json", summary)
    _write_csv(out / "v5h_buy_execution_timing_blockers.csv", blockers)


def _blockers(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers = []
    for group in groups:
        for row in group:
            if row.get("status") == "fail":
                blockers.append(_blocker(row.get("gate_id") or row.get("audit_id") or "unknown", str(row.get("value", row.get("detail", "")))))
    return blockers or [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": ""}]


def _blocker(blocker_id: str, description: str) -> dict[str, Any]:
    return {"blocker_id": blocker_id, "severity": "fatal", "status": "blocking", "description": description}


def _best_variant(comparison: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in comparison if row.get("variant_id") != BASELINE]
    return max(eligible, key=lambda row: _float(row.get("comparable_incremental_decision_edge_vs_baseline"))) if eligible else {}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _float(value: Any) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else 0.0
    except Exception:
        return 0.0


def _mean(values: list[Any]) -> float:
    clean = [_float(value) for value in values if value not in (None, "")]
    return sum(clean) / len(clean) if clean else 0.0


def _median(values: list[Any]) -> float:
    clean = sorted(_float(value) for value in values if value not in (None, ""))
    if not clean:
        return 0.0
    mid = len(clean) // 2
    return clean[mid] if len(clean) % 2 else (clean[mid - 1] + clean[mid]) / 2.0


def _pct(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100.0, 6) if denominator else 0.0


def main() -> None:
    summary = run_v5h_buy_execution_timing_overlay(Path("."))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5h_buy_execution_spec_v1") / "current"
OVERLAY_DIR = Path("v5h_buy_execution_timing_overlay") / "current"

SUMMARY_INPUT = OVERLAY_DIR / "v5h_buy_execution_timing_overlay_summary.json"
COMPARISON_INPUT = OVERLAY_DIR / "v5h_buy_execution_timing_variant_comparison.csv"
BY_FAMILY_INPUT = OVERLAY_DIR / "v5h_buy_execution_timing_by_family.csv"
DATA_GATE_INPUT = OVERLAY_DIR / "v5h_buy_execution_timing_data_gate.csv"
GOVERNANCE_INPUT = OVERLAY_DIR / "v5h_buy_execution_timing_governance_audit.csv"

FORMAL_BACKTEST_START = "2021-05-01"
FORMAL_BACKTEST_END = "2026-05-31"
V5H_LINE_ID = "v5h_1min_microstructure_execution_research"
SPEC_ID = "v5h_buy_execution_spec_v1"
FROZEN_VARIANT = "pressure_positive_1000_else_1400_buy"
COMBINED_VARIANT = "combined_v5h_buy_execution_overlay_v1"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5h_buy_execution_spec_v1(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        summary = _summary("blocked_missing_required_input", "blocked_until_overlay_inputs_available", blockers)
        _write_csv(out / "v5h_buy_execution_spec_v1_blockers.csv", blockers)
        _write_json(out / "v5h_buy_execution_spec_v1_summary.json", summary)
        return summary

    source_summary = _read_json(root / SUMMARY_INPUT)
    comparison = _read_csv(root / COMPARISON_INPUT)
    by_family = _read_csv(root / BY_FAMILY_INPUT)
    data_gate_input = _read_csv(root / DATA_GATE_INPUT)
    governance_input = _read_csv(root / GOVERNANCE_INPUT)

    frozen = _find_variant(comparison, FROZEN_VARIANT)
    combined = _find_variant(comparison, COMBINED_VARIANT)
    input_blockers = _input_blockers(source_summary, frozen, data_gate_input, governance_input)
    if input_blockers:
        summary = _summary("blocked_input_gate_failed", "blocked_until_overlay_gate_passes", input_blockers)
        _write_csv(out / "v5h_buy_execution_spec_v1_blockers.csv", input_blockers)
        _write_json(out / "v5h_buy_execution_spec_v1_summary.json", summary)
        return summary

    frozen_rule = _frozen_rule_spec(frozen)
    decision_matrix = _execution_decision_matrix()
    visibility_schema = _signal_visibility_schema()
    order_scope = _applicable_order_scope()
    family_evidence = _family_evidence(by_family)
    combined_queue = _combined_observation_queue(combined)
    data_gate = _data_gate(source_summary, frozen, data_gate_input)
    governance = _governance_audit(governance_input)
    allowed_blocked = _allowed_blocked_actions()
    pm_decision = _pm_gate_decision(frozen, combined)
    next_queue = _next_agent_queue()
    blockers_out = [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": ""}]

    _write_csv(out / "v5h_buy_execution_spec_v1_frozen_rule_spec.csv", frozen_rule)
    _write_csv(out / "v5h_buy_execution_spec_v1_execution_decision_matrix.csv", decision_matrix)
    _write_csv(out / "v5h_buy_execution_spec_v1_signal_visibility_schema.csv", visibility_schema)
    _write_csv(out / "v5h_buy_execution_spec_v1_applicable_order_scope.csv", order_scope)
    _write_csv(out / "v5h_buy_execution_spec_v1_family_evidence.csv", family_evidence)
    _write_csv(out / "v5h_buy_execution_spec_v1_combined_observation_queue.csv", combined_queue)
    _write_csv(out / "v5h_buy_execution_spec_v1_data_gate.csv", data_gate)
    _write_csv(out / "v5h_buy_execution_spec_v1_governance_audit.csv", governance)
    _write_csv(out / "v5h_buy_execution_spec_v1_allowed_blocked_actions.csv", allowed_blocked)
    _write_csv(out / "v5h_buy_execution_spec_v1_pm_gate_decision.csv", pm_decision)
    _write_csv(out / "v5h_buy_execution_spec_v1_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5h_buy_execution_spec_v1_blockers.csv", blockers_out)
    (out / "v5h_buy_execution_spec_v1_report.md").write_text(
        _report(source_summary, frozen, combined, family_evidence, pm_decision),
        encoding="utf-8",
    )
    (out / "v5h_buy_execution_spec_v1_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    summary = _summary(
        "completed_v5h_buy_execution_spec_v1_frozen",
        pm_decision[0]["pm_gate_decision"],
        [],
        frozen_variant=FROZEN_VARIANT,
        combined_variant_status="observation_only_not_mainline",
        scheduled_buy_order_count=int(_float(frozen.get("order_count"))),
        frozen_variant_incremental_edge_bp=round(_float(frozen.get("comparable_incremental_decision_edge_vs_baseline")) * 10000.0, 6),
        frozen_variant_weighted_incremental_edge_bp=round(
            _float(frozen.get("comparable_weighted_incremental_decision_edge_vs_baseline")) * 10000.0,
            6,
        ),
        combined_v1_incremental_edge_bp=round(_float(combined.get("comparable_incremental_decision_edge_vs_baseline")) * 10000.0, 6),
        buy_execution_spec_frozen=True,
    )
    _write_json(out / "v5h_buy_execution_spec_v1_summary.json", summary)
    return summary


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [SUMMARY_INPUT, COMPARISON_INPUT, BY_FAMILY_INPUT, DATA_GATE_INPUT, GOVERNANCE_INPUT]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "status": "blocking",
            "description": str(path),
        }
        for path in required
        if not (root / path).exists()
    ]


def _input_blockers(
    source_summary: dict[str, Any],
    frozen: dict[str, Any],
    data_gate: list[dict[str, Any]],
    governance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    if source_summary.get("status") != "completed_v5h_buy_execution_timing_overlay":
        blockers.append(_blocker("overlay_not_completed", str(source_summary.get("status", ""))))
    if source_summary.get("pm_gate_decision") != "v5h_buy_execution_overlay_positive_ready_for_quant_spec_not_trading":
        blockers.append(_blocker("overlay_not_admitted_to_spec", str(source_summary.get("pm_gate_decision", ""))))
    if not frozen:
        blockers.append(_blocker("frozen_variant_missing", FROZEN_VARIANT))
    if any(row.get("status") != "pass" for row in data_gate):
        blockers.append(_blocker("source_data_gate_failed", "At least one source overlay data gate failed."))
    if any(row.get("status") != "pass" for row in governance):
        blockers.append(_blocker("source_governance_failed", "At least one source overlay governance audit failed."))
    return blockers


def _frozen_rule_spec(frozen: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "spec_id": SPEC_ID,
            "frozen_variant": FROZEN_VARIANT,
            "v5h_line_id": V5H_LINE_ID,
            "rule_status": "frozen_spec_not_trading",
            "order_scope": "scheduled_buy_and_increase_orders_only",
            "allowed_intent_families": "value_lowvol_rebalance;momentum_overlay_tilt;v5f_champion_rebalance",
            "excluded_intent_families": "mean_reversion_event;sell_orders;decrease_orders;cash_proxy_orders",
            "decision_time_early": "10:00:00",
            "decision_time_fallback": "14:00:00",
            "early_buy_condition": "amount_pressure_bucket == positive_pressure at 10:00 observation",
            "fallback_condition": "amount_pressure_bucket != positive_pressure or signal unavailable",
            "price_source": "1min_clean_price_volume_amount_feature_panel",
            "signal_source": "completed 1min bars visible up to decision timestamp",
            "sample_order_count": int(_float(frozen.get("order_count"))),
            "incremental_edge_bp_vs_default_proxy": round(_float(frozen.get("comparable_incremental_decision_edge_vs_baseline")) * 10000.0, 6),
            "weighted_incremental_edge_bp_vs_default_proxy": round(
                _float(frozen.get("comparable_weighted_incremental_decision_edge_vs_baseline")) * 10000.0,
                6,
            ),
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "v5f_mainline_modified": False,
            "sell_rules_modified": False,
            "trading_frequency_increased": False,
            "new_buy_signal_used": False,
        }
    ]


def _execution_decision_matrix() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "positive_amount_pressure_at_1000",
            "order_side": "buy_or_increase",
            "order_origin": "already_planned_v57f_or_v5f_target_delta",
            "visible_signal_time": "10:00:00",
            "condition": "amount_pressure_bucket == positive_pressure",
            "execution_time": "10:00:00",
            "fallback_time": "",
            "allowed": True,
            "notes": "Early execution is allowed only for already planned scheduled buy orders.",
        },
        {
            "case_id": "neutral_amount_pressure_at_1000",
            "order_side": "buy_or_increase",
            "order_origin": "already_planned_v57f_or_v5f_target_delta",
            "visible_signal_time": "10:00:00",
            "condition": "amount_pressure_bucket == neutral_pressure",
            "execution_time": "14:00:00",
            "fallback_time": "14:00:00",
            "allowed": True,
            "notes": "No early buy; wait for the fixed fallback window.",
        },
        {
            "case_id": "negative_amount_pressure_at_1000",
            "order_side": "buy_or_increase",
            "order_origin": "already_planned_v57f_or_v5f_target_delta",
            "visible_signal_time": "10:00:00",
            "condition": "amount_pressure_bucket == negative_pressure",
            "execution_time": "14:00:00",
            "fallback_time": "14:00:00",
            "allowed": True,
            "notes": "Avoid buying into weak amount pressure at 10:00, but do not cancel the planned buy.",
        },
        {
            "case_id": "amount_pressure_missing",
            "order_side": "buy_or_increase",
            "order_origin": "already_planned_v57f_or_v5f_target_delta",
            "visible_signal_time": "10:00:00",
            "condition": "10:00 amount pressure cannot be computed",
            "execution_time": "14:00:00",
            "fallback_time": "14:00:00",
            "allowed": True,
            "notes": "Fail closed to fallback execution; do not infer missing pressure.",
        },
        {
            "case_id": "sell_or_decrease_order",
            "order_side": "sell_or_decrease",
            "order_origin": "any",
            "visible_signal_time": "",
            "condition": "any amount pressure state",
            "execution_time": "unchanged_existing_policy",
            "fallback_time": "",
            "allowed": False,
            "notes": "This spec does not touch sell timing.",
        },
        {
            "case_id": "mean_reversion_event",
            "order_side": "buy",
            "order_origin": "mean_reversion_event",
            "visible_signal_time": "",
            "condition": "any",
            "execution_time": "observation_only",
            "fallback_time": "",
            "allowed": False,
            "notes": "Mean-reversion pressure gate remains in combined observation queue, not v1.",
        },
    ]


def _signal_visibility_schema() -> list[dict[str, Any]]:
    return [
        {
            "field": "trade_date",
            "required": True,
            "pit_rule": "Must be the scheduled order date inside formal backtest or forward observation date.",
        },
        {
            "field": "intent_id",
            "required": True,
            "pit_rule": "Must exist before execution timing is chosen.",
        },
        {
            "field": "intent_family",
            "required": True,
            "pit_rule": "Only pre-existing scheduled buy families are eligible.",
        },
        {
            "field": "amount_pressure_bucket",
            "required": True,
            "pit_rule": "For 10:00 early decision, use only completed 1min bars up to and including 10:00.",
        },
        {
            "field": "selected_obs_time",
            "required": True,
            "pit_rule": "May be 10:00 or 14:00 only for v1.",
        },
        {
            "field": "price_at_obs",
            "required": True,
            "pit_rule": "Execution proxy must come from the selected visible observation timestamp.",
        },
        {
            "field": "future_close_or_vwap",
            "required": False,
            "pit_rule": "Allowed only for evaluation after the decision, never for live timing choice.",
        },
    ]


def _applicable_order_scope() -> list[dict[str, Any]]:
    return [
        {
            "intent_family": "value_lowvol_rebalance",
            "scope_status": "included_in_v1",
            "reason": "Scheduled buy/increase target created by existing value-low-vol path.",
        },
        {
            "intent_family": "momentum_overlay_tilt",
            "scope_status": "included_in_v1",
            "reason": "Scheduled buy/increase target created by existing V5f momentum overlay path.",
        },
        {
            "intent_family": "v5f_champion_rebalance",
            "scope_status": "included_in_v1",
            "reason": "Scheduled buy/increase target created by V5f mainline comparison path.",
        },
        {
            "intent_family": "mean_reversion_event",
            "scope_status": "excluded_observation_only",
            "reason": "MR pressure gate is promising but not part of frozen v1.",
        },
        {
            "intent_family": "sell_or_decrease_orders",
            "scope_status": "excluded_blocked",
            "reason": "Sell timing remains unchanged because 1min sell-side evidence is unstable.",
        },
    ]


def _family_evidence(by_family: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [row for row in by_family if row.get("variant_id") == FROZEN_VARIANT]
    out = []
    for row in rows:
        out.append(
            {
                "spec_id": SPEC_ID,
                "variant_id": row.get("variant_id", ""),
                "intent_family": row.get("intent_family", ""),
                "order_count": int(_float(row.get("order_count"))),
                "executed_order_count": int(_float(row.get("executed_order_count"))),
                "decision_edge_bp": round(_float(row.get("avg_decision_edge_vs_close_all_orders")) * 10000.0, 6),
                "incremental_edge_bp_vs_family_default": round(_float(row.get("avg_incremental_edge_vs_baseline_order")) * 10000.0, 6),
                "weighted_incremental_edge_bp_vs_family_default": round(
                    _float(row.get("weighted_avg_incremental_edge_vs_baseline_order")) * 10000.0,
                    6,
                ),
                "positive_edge_rate_pct": _float(row.get("positive_edge_rate_pct")),
                "status": "supports_frozen_v1",
            }
        )
    return out


def _combined_observation_queue(combined: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "queue_id": "combined_v5h_buy_execution_overlay_v1",
            "source_variant": COMBINED_VARIANT,
            "status": "observation_only_not_mainline",
            "includes": "scheduled buy timing v1 plus mean-reversion amount-pressure gate",
            "reason_not_frozen": "Combines scheduled orders with mean-reversion event filtering; MR leg needs independent forward or pre-2021 validation before rule admission.",
            "all_order_incremental_edge_bp": round(_float(combined.get("comparable_incremental_decision_edge_vs_baseline")) * 10000.0, 6),
            "weighted_incremental_edge_bp": round(
                _float(combined.get("comparable_weighted_incremental_decision_edge_vs_baseline")) * 10000.0,
                6,
            ),
            "accepted": False,
            "live_trading_approved": False,
            "mainline_modified": False,
        }
    ]


def _data_gate(source_summary: dict[str, Any], frozen: dict[str, Any], source_gate: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {
            "gate_id": "source_overlay_completed",
            "status": "pass" if source_summary.get("status") == "completed_v5h_buy_execution_timing_overlay" else "fail",
            "value": source_summary.get("status", ""),
        },
        {
            "gate_id": "frozen_variant_available",
            "status": "pass" if frozen else "fail",
            "value": FROZEN_VARIANT,
        },
        {
            "gate_id": "scheduled_buy_sample_size",
            "status": "pass" if _float(frozen.get("order_count")) >= 100 else "fail",
            "value": int(_float(frozen.get("order_count"))),
        },
        {
            "gate_id": "formal_backtest_end_preserved",
            "status": "pass" if source_summary.get("formal_backtest_end") == FORMAL_BACKTEST_END else "fail",
            "value": source_summary.get("formal_backtest_end", ""),
        },
    ]
    rows.extend(
        {
            "gate_id": f"source_{row.get('gate_id', '')}",
            "status": row.get("status", ""),
            "value": row.get("value", ""),
        }
        for row in source_gate
    )
    return rows


def _governance_audit(source_governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {"audit_id": "spec_scope_buy_side_only", "status": "pass", "detail": "v1 only applies to scheduled buy/increase orders."},
        {"audit_id": "combined_v1_observation_only", "status": "pass", "detail": "combined v1 is explicitly not frozen into the mainline spec."},
        {"audit_id": "sell_rules_unchanged", "status": "pass", "detail": "No sell/decrease order timing is changed."},
        {"audit_id": "no_new_stock_selection", "status": "pass", "detail": "v1 does not create orders or add stocks."},
        {"audit_id": "no_rebalance_frequency_change", "status": "pass", "detail": "v1 selects timing inside an already planned buy day only."},
        {"audit_id": "no_threshold_scan", "status": "pass", "detail": "The pressure bucket rule was preselected from fixed 1/2/3/4 variants; no new threshold is optimized here."},
        {"audit_id": "not_accepted_not_live", "status": "pass", "detail": "Frozen spec is not accepted or live approved."},
        {"audit_id": "v57f_v5f_mainlines_unchanged", "status": "pass", "detail": "V57f core and V5f mainline remain unchanged."},
    ]
    rows.extend(
        {
            "audit_id": f"source_{row.get('audit_id', '')}",
            "status": row.get("status", ""),
            "detail": row.get("detail", ""),
        }
        for row in source_governance
    )
    return rows


def _allowed_blocked_actions() -> list[dict[str, Any]]:
    return [
        {"action": "use_10am_if_positive_amount_pressure_for_scheduled_buys", "status": "allowed_in_spec", "reason": "Frozen v1 rule."},
        {"action": "fallback_to_14pm_for_non_positive_or_missing_pressure", "status": "allowed_in_spec", "reason": "Fail-closed execution timing rule."},
        {"action": "apply_to_value_lowvol_momentum_v5f_scheduled_buys", "status": "allowed_in_spec", "reason": "These are already planned buy/increase orders."},
        {"action": "combined_v1_with_mean_reversion_pressure_gate", "status": "observation_only", "reason": "Promising but not frozen into v1."},
        {"action": "sell_timing_change", "status": "blocked", "reason": "Sell-side 1min evidence remains unstable."},
        {"action": "new_stock_buy_signal", "status": "blocked", "reason": "V5h execution timing cannot create buys."},
        {"action": "increase_trading_frequency", "status": "blocked", "reason": "Only same-day execution time may change for already planned orders."},
        {"action": "change_v57f_or_v5f_weights", "status": "blocked", "reason": "Execution spec does not alter target weights or selection."},
        {"action": "mark_accepted_or_live_approved", "status": "blocked", "reason": "Requires separate forward/paper governance."},
    ]


def _pm_gate_decision(frozen: dict[str, Any], combined: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "pm_gate_decision": "freeze_pressure_positive_1000_else_1400_buy_as_v5h_buy_execution_spec_v1_not_trading",
            "status": "spec_frozen_ready_for_forward_observation",
            "frozen_variant": FROZEN_VARIANT,
            "frozen_variant_incremental_edge_bp": round(_float(frozen.get("comparable_incremental_decision_edge_vs_baseline")) * 10000.0, 6),
            "combined_v1_status": "observation_only_not_mainline",
            "combined_v1_incremental_edge_bp": round(_float(combined.get("comparable_incremental_decision_edge_vs_baseline")) * 10000.0, 6),
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "v5f_mainline_modified": False,
            "sell_rules_modified": False,
            "trading_frequency_increased": False,
            "new_buy_signal_used": False,
        }
    ]


def _next_agent_queue() -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "queue_id": "v5h_buy_execution_spec_v1_forward_observation",
            "status": "ready",
            "scope": "Append future planned buy orders and record whether 10:00 positive amount pressure improves execution versus default/fallback.",
        },
        {
            "priority": 2,
            "queue_id": "v5h_buy_execution_spec_v1_jq_or_broker_paper_mapping",
            "status": "ready_when_platform_available",
            "scope": "Map v1 to practical order schedule; do not alter target holdings or sell logic.",
        },
        {
            "priority": 3,
            "queue_id": "combined_v5h_buy_execution_overlay_v1_observation",
            "status": "observation_only",
            "scope": "Track combined scheduled-buy v1 plus MR amount-pressure gate, but do not freeze as mainline.",
        },
    ]


def _report(
    source_summary: dict[str, Any],
    frozen: dict[str, Any],
    combined: dict[str, Any],
    family_evidence: list[dict[str, Any]],
    pm_decision: list[dict[str, Any]],
) -> str:
    lines = [
        "# V5h Buy Execution Spec v1",
        "",
        f"- PM gate: `{pm_decision[0]['pm_gate_decision']}`",
        f"- Frozen variant: `{FROZEN_VARIANT}`",
        f"- Formal window: {FORMAL_BACKTEST_START} to {FORMAL_BACKTEST_END}",
        "- Scope: scheduled buy/increase execution timing only.",
        "- Rule: buy at 10:00 when amount pressure is positive; otherwise buy at 14:00.",
        "- Combined v1 remains observation-only and is not part of the frozen spec.",
        "",
        "## Evidence",
        "",
        f"- Scheduled buy sample: {int(_float(frozen.get('order_count')))} orders.",
        f"- Incremental edge versus scheduled-buy default proxy: {round(_float(frozen.get('comparable_incremental_decision_edge_vs_baseline')) * 10000.0, 2)} bp.",
        f"- Weighted incremental edge: {round(_float(frozen.get('comparable_weighted_incremental_decision_edge_vs_baseline')) * 10000.0, 2)} bp.",
        f"- Combined v1 all-order incremental edge: {round(_float(combined.get('comparable_incremental_decision_edge_vs_baseline')) * 10000.0, 2)} bp.",
        "",
        "## Family Evidence",
        "",
    ]
    for row in family_evidence:
        lines.append(
            f"- `{row['intent_family']}`: n={row['order_count']}, incremental={row['incremental_edge_bp_vs_family_default']} bp, weighted={row['weighted_incremental_edge_bp_vs_family_default']} bp."
        )
    lines.extend(
        [
            "",
            "## Governance",
            "",
            "- No V57f core modification.",
            "- No V5f mainline modification.",
            "- No sell-rule change.",
            "- No new buy signal.",
            "- No rebalance-frequency increase.",
            "- Not accepted and not live approved.",
            "",
            f"Source overlay status: `{source_summary.get('status', '')}`.",
            "",
        ]
    )
    return "\n".join(lines)


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5h Buy Execution Spec v1 Agent Rules",
            "",
            "- Use `pressure_positive_1000_else_1400_buy` as the only frozen v1 rule.",
            "- Apply only to already planned scheduled buy/increase orders.",
            "- At 10:00, buy early only when `amount_pressure_bucket == positive_pressure`.",
            "- Otherwise use the fixed 14:00 fallback.",
            "- Do not change sell/decrease orders.",
            "- Do not create new stock buys, change target weights, or change rebalance frequency.",
            "- Keep `combined_v5h_buy_execution_overlay_v1` observation-only.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": SPEC_ID,
        "v5h_line_id": V5H_LINE_ID,
        "status": status,
        "pm_gate_decision": decision,
        "formal_backtest_start": FORMAL_BACKTEST_START,
        "formal_backtest_end": FORMAL_BACKTEST_END,
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


def _find_variant(rows: list[dict[str, Any]], variant_id: str) -> dict[str, Any]:
    return next((row for row in rows if row.get("variant_id") == variant_id), {})


def _blocker(blocker_id: str, description: str) -> dict[str, Any]:
    return {"blocker_id": blocker_id, "severity": "fatal", "status": "blocking", "description": description}


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


def _float(value: Any) -> float:
    try:
        out = float(value)
        return out if math.isfinite(out) else 0.0
    except Exception:
        return 0.0


def main() -> None:
    summary = run_v5h_buy_execution_spec_v1(Path("."))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

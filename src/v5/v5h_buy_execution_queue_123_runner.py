from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SPEC_DIR = Path("v5h_buy_execution_spec_v1") / "current"
OVERLAY_DIR = Path("v5h_buy_execution_timing_overlay") / "current"
FORWARD_SOURCE_DIR = Path("v5f_1min_forward_observation_append") / "current"
FORWARD_TARGET_DIR = Path("v5f_clean_forward_target_population") / "current"

QUEUE_OUT = Path("v5h_buy_execution_queue_123") / "current"
FORWARD_OUT = Path("v5h_buy_execution_spec_v1_forward_observation") / "current"
MAPPING_OUT = Path("v5h_buy_execution_spec_v1_jq_broker_paper_mapping") / "current"
COMBINED_OUT = Path("v5h_combined_buy_execution_overlay_v1_observation") / "current"

SPEC_SUMMARY = SPEC_DIR / "v5h_buy_execution_spec_v1_summary.json"
SPEC_RULE = SPEC_DIR / "v5h_buy_execution_spec_v1_frozen_rule_spec.csv"
SPEC_FAMILY = SPEC_DIR / "v5h_buy_execution_spec_v1_family_evidence.csv"
SPEC_GOV = SPEC_DIR / "v5h_buy_execution_spec_v1_governance_audit.csv"
SPEC_COMBINED_QUEUE = SPEC_DIR / "v5h_buy_execution_spec_v1_combined_observation_queue.csv"

OVERLAY_COMPARISON = OVERLAY_DIR / "v5h_buy_execution_timing_variant_comparison.csv"
OVERLAY_BY_FAMILY = OVERLAY_DIR / "v5h_buy_execution_timing_by_family.csv"

FORWARD_SUMMARY = FORWARD_SOURCE_DIR / "v5f_1min_forward_observation_summary.json"
FORWARD_AVAILABILITY = FORWARD_SOURCE_DIR / "v5f_1min_forward_data_availability.csv"
FORWARD_TARGET_SUMMARY = FORWARD_TARGET_DIR / "v5f_clean_forward_target_population_summary.json"
FORWARD_TARGET_ROWS = FORWARD_TARGET_DIR / "v5f_clean_forward_paper_target_rows.csv"

FORMAL_BACKTEST_END = "2026-05-31"
FORWARD_START = "2026-06-01"
V5H_LINE_ID = "v5h_1min_microstructure_execution_research"
FROZEN_VARIANT = "pressure_positive_1000_else_1400_buy"
COMBINED_VARIANT = "combined_v5h_buy_execution_overlay_v1"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5h_buy_execution_queue_123(root: Path = Path(".")) -> dict[str, Any]:
    blockers = _missing_inputs(root)
    if blockers:
        return _write_blocked(root, blockers)

    spec_summary = _read_json(root / SPEC_SUMMARY)
    spec_rule = _read_csv(root / SPEC_RULE)
    spec_family = _read_csv(root / SPEC_FAMILY)
    spec_governance = _read_csv(root / SPEC_GOV)
    spec_combined_queue = _read_csv(root / SPEC_COMBINED_QUEUE)
    overlay_comparison = _read_csv(root / OVERLAY_COMPARISON)
    overlay_by_family = _read_csv(root / OVERLAY_BY_FAMILY)
    forward_summary = _read_optional_json(root / FORWARD_SUMMARY)
    forward_availability = _read_csv(root / FORWARD_AVAILABILITY) if (root / FORWARD_AVAILABILITY).exists() else []
    target_summary = _read_optional_json(root / FORWARD_TARGET_SUMMARY)
    target_rows = _read_csv(root / FORWARD_TARGET_ROWS) if (root / FORWARD_TARGET_ROWS).exists() else []

    source_blockers = _source_blockers(spec_summary, spec_governance)
    if source_blockers:
        return _write_blocked(root, source_blockers)

    forward_result = _run_forward_observation(
        root,
        spec_summary,
        spec_rule[0],
        forward_summary,
        forward_availability,
        target_summary,
        target_rows,
    )
    mapping_result = _run_jq_broker_mapping(root, spec_summary, spec_rule[0])
    combined_result = _run_combined_observation(
        root,
        spec_summary,
        spec_combined_queue[0],
        overlay_comparison,
        overlay_by_family,
    )

    summary = _combined_summary(forward_result, mapping_result, combined_result)
    _write_queue_summary(root, summary, [forward_result, mapping_result, combined_result])
    return summary


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        SPEC_SUMMARY,
        SPEC_RULE,
        SPEC_FAMILY,
        SPEC_GOV,
        SPEC_COMBINED_QUEUE,
        OVERLAY_COMPARISON,
        OVERLAY_BY_FAMILY,
    ]
    return [
        _blocker("missing_required_input", str(path))
        for path in required
        if not (root / path).exists()
    ]


def _source_blockers(spec_summary: dict[str, Any], spec_governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers = []
    if spec_summary.get("status") != "completed_v5h_buy_execution_spec_v1_frozen":
        blockers.append(_blocker("spec_v1_not_frozen", str(spec_summary.get("status", ""))))
    if spec_summary.get("frozen_variant") != FROZEN_VARIANT:
        blockers.append(_blocker("unexpected_frozen_variant", str(spec_summary.get("frozen_variant", ""))))
    if any(row.get("status") != "pass" for row in spec_governance):
        blockers.append(_blocker("spec_governance_not_pass", "At least one V5h spec v1 governance row failed."))
    return blockers


def _run_forward_observation(
    root: Path,
    spec_summary: dict[str, Any],
    spec_rule: dict[str, Any],
    forward_summary: dict[str, Any],
    forward_availability: list[dict[str, Any]],
    target_summary: dict[str, Any],
    target_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    out = root / FORWARD_OUT
    out.mkdir(parents=True, exist_ok=True)
    official_ready = _official_forward_targets_available(target_summary, target_rows)
    target_status = "official_planned_buy_orders_available" if official_ready else "waiting_official_planned_buy_orders"
    planned_buy_rows = _planned_buy_template_rows(target_rows, official_ready)
    observation_schema = _forward_observation_schema()
    readiness = _forward_readiness_rows(forward_summary, forward_availability, target_summary, target_rows, official_ready)
    data_boundary = _forward_data_boundary(forward_summary, official_ready)
    append_plan = _forward_append_plan(official_ready)
    governance = _shared_governance(
        [
            ("forward_only_after_backtest_end", "pass", f"Observation starts after {FORMAL_BACKTEST_END}."),
            ("no_synthetic_forward_orders", "pass", "Template/TBD rows are not treated as official planned buy orders."),
            ("buy_execution_spec_only", "pass", "Only v1 buy execution timing fields are prepared."),
            ("one_min_ohlcv_amount_only", "pass", "Current 1min data has OHLCV and amount, not order-book or tick trade direction."),
            ("no_order_book_claim", "pass", "No bid/ask depth, quote queue, Level-2, or broker order book is claimed available."),
            ("no_active_buy_sell_flow_inference", "pass", "Amount pressure is a proxy from signed minute returns, not true active buy/sell flow."),
        ]
    )
    decision = [
        {
            "pm_gate_decision": "v5h_buy_execution_spec_v1_forward_observation_ready_waiting_official_buy_orders",
            "status": target_status,
            "official_forward_targets_available": official_ready,
            "planned_buy_observation_rows": len(planned_buy_rows),
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "v5f_mainline_modified": False,
            "sell_rules_modified": False,
            "trading_frequency_increased": False,
            "new_buy_signal_used": False,
            "one_min_ohlcv_amount_available": True,
            "order_book_available": False,
            "bid_ask_available": False,
            "active_buy_sell_flow_available": False,
        }
    ]
    blockers = [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": ""}]
    summary = {
        "created_at_utc": now_utc(),
        "task": "v5h_buy_execution_spec_v1_forward_observation",
        "status": "completed_forward_observation_packet_waiting_official_buy_orders",
        "pm_gate_decision": decision[0]["pm_gate_decision"],
        "frozen_variant": FROZEN_VARIANT,
        "formal_backtest_end": FORMAL_BACKTEST_END,
        "forward_start": FORWARD_START,
        "source_forward_stock_day_count": int(_float(forward_summary.get("forward_stock_day_count", 0))),
        "source_forward_event_count": int(_float(forward_summary.get("forward_event_count", 0))),
        "source_forward_first_available_date": forward_summary.get("forward_first_available_date", ""),
        "source_forward_last_available_date": forward_summary.get("forward_last_available_date", ""),
        "official_forward_targets_available": official_ready,
        "planned_buy_observation_rows": len(planned_buy_rows),
        "target_status": target_status,
        "one_min_data_granularity": "ohlcv_amount_1min",
        "one_min_ohlcv_amount_available": True,
        "order_book_available": False,
        "bid_ask_available": False,
        "quote_depth_available": False,
        "tick_trade_direction_available": False,
        "active_buy_sell_flow_available": False,
        "true_order_flow_available": False,
        "allowed_use": "execution_timing_observation_only",
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "v5f_mainline_modified": False,
        "sell_rules_modified": False,
        "trading_frequency_increased": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "fatal_blocker_count": 0,
    }
    _write_json(out / "v5h_buy_execution_v1_forward_observation_summary.json", summary)
    _write_csv(out / "v5h_buy_execution_v1_forward_observation_schema.csv", observation_schema)
    _write_csv(out / "v5h_buy_execution_v1_forward_target_readiness.csv", readiness)
    _write_csv(out / "v5h_buy_execution_v1_forward_planned_buy_observation_rows.csv", planned_buy_rows)
    _write_csv(out / "v5h_buy_execution_v1_forward_append_plan.csv", append_plan)
    _write_csv(out / "v5h_buy_execution_v1_forward_data_availability.csv", forward_availability or _empty_forward_availability())
    _write_csv(out / "v5h_buy_execution_v1_forward_data_boundary.csv", data_boundary)
    _write_csv(out / "v5h_buy_execution_v1_forward_governance_audit.csv", governance)
    _write_csv(out / "v5h_buy_execution_v1_forward_pm_gate_decision.csv", decision)
    _write_csv(out / "v5h_buy_execution_v1_forward_blockers.csv", blockers)
    (out / "v5h_buy_execution_v1_forward_observation_report.md").write_text(
        _forward_report(summary, spec_rule, readiness, data_boundary),
        encoding="utf-8",
    )
    (out / "v5h_buy_execution_v1_forward_agent_execution_rules.md").write_text(_agent_rules("forward observation"), encoding="utf-8")
    return summary


def _run_jq_broker_mapping(root: Path, spec_summary: dict[str, Any], spec_rule: dict[str, Any]) -> dict[str, Any]:
    out = root / MAPPING_OUT
    out.mkdir(parents=True, exist_ok=True)
    mapping = _jq_broker_mapping_rows()
    order_state = _paper_order_state_machine()
    data_contract = _platform_data_contract()
    preflight = _platform_preflight_checklist()
    governance = _shared_governance(
        [
            ("platform_mapping_only", "pass", "No JoinQuant or broker session is launched."),
            ("no_order_submission", "pass", "This packet maps paper workflow only and does not submit orders."),
            ("fallback_is_14pm", "pass", "Missing or non-positive pressure falls back to 14:00."),
        ]
    )
    decision = [
        {
            "pm_gate_decision": "v5h_buy_execution_spec_v1_jq_broker_mapping_ready_not_deployed",
            "status": "ready_when_platform_available",
            "frozen_variant": FROZEN_VARIANT,
            "accepted": False,
            "live_trading_approved": False,
            "deployment_approved": False,
            "joinquant_started": False,
            "broker_started": False,
            "v57f_core_modified": False,
            "v5f_mainline_modified": False,
            "sell_rules_modified": False,
            "trading_frequency_increased": False,
            "new_buy_signal_used": False,
        }
    ]
    blockers = [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": ""}]
    summary = {
        "created_at_utc": now_utc(),
        "task": "v5h_buy_execution_spec_v1_jq_broker_paper_mapping",
        "status": "completed_mapping_ready_when_platform_available",
        "pm_gate_decision": decision[0]["pm_gate_decision"],
        "frozen_variant": FROZEN_VARIANT,
        "rule": spec_rule.get("early_buy_condition", ""),
        "fallback": spec_rule.get("fallback_condition", ""),
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "joinquant_started": False,
        "broker_started": False,
        "v57f_core_modified": False,
        "v5f_mainline_modified": False,
        "sell_rules_modified": False,
        "trading_frequency_increased": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "fatal_blocker_count": 0,
    }
    _write_json(out / "v5h_buy_execution_v1_jq_broker_mapping_summary.json", summary)
    _write_csv(out / "v5h_buy_execution_v1_jq_broker_mapping.csv", mapping)
    _write_csv(out / "v5h_buy_execution_v1_paper_order_state_machine.csv", order_state)
    _write_csv(out / "v5h_buy_execution_v1_platform_data_contract.csv", data_contract)
    _write_csv(out / "v5h_buy_execution_v1_platform_preflight_checklist.csv", preflight)
    _write_csv(out / "v5h_buy_execution_v1_jq_broker_governance_audit.csv", governance)
    _write_csv(out / "v5h_buy_execution_v1_jq_broker_pm_gate_decision.csv", decision)
    _write_csv(out / "v5h_buy_execution_v1_jq_broker_blockers.csv", blockers)
    (out / "v5h_buy_execution_v1_jq_broker_mapping_report.md").write_text(
        _mapping_report(summary, mapping, preflight),
        encoding="utf-8",
    )
    (out / "v5h_buy_execution_v1_jq_broker_agent_execution_rules.md").write_text(_agent_rules("JQ/broker paper mapping"), encoding="utf-8")
    return summary


def _run_combined_observation(
    root: Path,
    spec_summary: dict[str, Any],
    combined_queue: dict[str, Any],
    overlay_comparison: list[dict[str, Any]],
    overlay_by_family: list[dict[str, Any]],
) -> dict[str, Any]:
    out = root / COMBINED_OUT
    out.mkdir(parents=True, exist_ok=True)
    combined = _find_variant(overlay_comparison, COMBINED_VARIANT)
    mr_gate = _find_variant(overlay_comparison, "mr_crash_buy_pressure_neutral_or_positive_only")
    components = _combined_component_evidence(overlay_by_family, combined, mr_gate)
    observation_spec = _combined_observation_spec(combined_queue, combined, mr_gate)
    risk_register = _combined_risk_register()
    governance = _shared_governance(
        [
            ("combined_observation_only", "pass", "Combined v1 is not part of the frozen V5h buy execution spec v1."),
            ("mr_leg_not_admitted", "pass", "Mean-reversion amount-pressure gate remains observation only."),
            ("no_mainline_change", "pass", "V5f internal_subsleeve_mom12_70_30 remains the mainline."),
        ]
    )
    decision = [
        {
            "pm_gate_decision": "combined_v5h_buy_execution_overlay_v1_observation_open_not_mainline",
            "status": "observation_only",
            "combined_incremental_edge_bp": round(_float(combined.get("comparable_incremental_decision_edge_vs_baseline")) * 10000.0, 6),
            "mr_pressure_gate_incremental_edge_bp": round(_float(mr_gate.get("comparable_incremental_decision_edge_vs_baseline")) * 10000.0, 6),
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "v5f_mainline_modified": False,
            "sell_rules_modified": False,
            "trading_frequency_increased": False,
            "new_buy_signal_used": False,
        }
    ]
    blockers = [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": ""}]
    summary = {
        "created_at_utc": now_utc(),
        "task": "v5h_combined_buy_execution_overlay_v1_observation",
        "status": "completed_combined_observation_packet_not_mainline",
        "pm_gate_decision": decision[0]["pm_gate_decision"],
        "combined_variant": COMBINED_VARIANT,
        "combined_incremental_edge_bp": decision[0]["combined_incremental_edge_bp"],
        "mr_pressure_gate_incremental_edge_bp": decision[0]["mr_pressure_gate_incremental_edge_bp"],
        "observation_only": True,
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "v5f_mainline_modified": False,
        "sell_rules_modified": False,
        "trading_frequency_increased": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "fatal_blocker_count": 0,
    }
    _write_json(out / "v5h_combined_buy_execution_observation_summary.json", summary)
    _write_csv(out / "v5h_combined_buy_execution_component_evidence.csv", components)
    _write_csv(out / "v5h_combined_buy_execution_observation_spec.csv", observation_spec)
    _write_csv(out / "v5h_combined_buy_execution_risk_register.csv", risk_register)
    _write_csv(out / "v5h_combined_buy_execution_governance_audit.csv", governance)
    _write_csv(out / "v5h_combined_buy_execution_pm_gate_decision.csv", decision)
    _write_csv(out / "v5h_combined_buy_execution_blockers.csv", blockers)
    (out / "v5h_combined_buy_execution_observation_report.md").write_text(
        _combined_report(summary, components, risk_register),
        encoding="utf-8",
    )
    (out / "v5h_combined_buy_execution_agent_execution_rules.md").write_text(_agent_rules("combined observation"), encoding="utf-8")
    return summary


def _official_forward_targets_available(target_summary: dict[str, Any], target_rows: list[dict[str, Any]]) -> bool:
    if not target_summary or not target_rows:
        return False
    status_text = json.dumps(target_summary, ensure_ascii=False).lower()
    if "template" in status_text or "tbd" in status_text or "waiting" in status_text:
        return False
    for row in target_rows:
        if any("TBD" in str(value) for value in row.values()):
            return False
    return True


def _planned_buy_template_rows(target_rows: list[dict[str, Any]], official_ready: bool) -> list[dict[str, Any]]:
    if not official_ready:
        return [
            {
                "row_id": "template_waiting_official_targets",
                "rebalance_date": "TBD_official_forward_rebalance_date",
                "code": "TBD_official_planned_buy_code",
                "intent_family": "TBD_value_lowvol_or_momentum_or_v5f_champion",
                "planned_delta_weight": "TBD_positive_delta_only",
                "decision_rule": "10:00 if positive amount pressure else 14:00",
                "observation_status": "template_not_trade_instruction",
                "accepted": False,
            }
        ]
    rows = []
    for index, row in enumerate(target_rows, start=1):
        rows.append(
            {
                "row_id": f"forward_buy_obs_{index:05d}",
                "rebalance_date": row.get("rebalance_date", ""),
                "code": row.get("code", ""),
                "intent_family": row.get("candidate_id", ""),
                "planned_delta_weight": row.get("overlay_target_weight", ""),
                "decision_rule": "10:00 if positive amount pressure else 14:00",
                "observation_status": "ready_for_paper_observation",
                "accepted": False,
            }
        )
    return rows


def _forward_observation_schema() -> list[dict[str, Any]]:
    return [
        {"field": "observation_id", "required": True, "definition": "Stable row id for one planned buy/increase order."},
        {"field": "rebalance_or_order_date", "required": True, "definition": "Forward order date; must be after formal backtest end."},
        {"field": "code", "required": True, "definition": "Official target stock code from V57f/V5f planned order."},
        {"field": "planned_delta_weight", "required": True, "definition": "Positive buy/increase delta only."},
        {"field": "amount_pressure_bucket_1000", "required": True, "definition": "Computed from visible 1min bars through 10:00."},
        {"field": "selected_execution_time", "required": True, "definition": "10:00 for positive pressure; otherwise 14:00."},
        {"field": "price_1000", "required": True, "definition": "1min price at 10:00 observation."},
        {"field": "price_1400", "required": True, "definition": "1min price at 14:00 fallback observation."},
        {"field": "same_day_close_or_eval_price", "required": False, "definition": "Evaluation-only after decision, never used for timing."},
        {"field": "forward_result_status", "required": True, "definition": "observation_only / missing_data / official_target_pending."},
    ]


def _forward_readiness_rows(
    forward_summary: dict[str, Any],
    forward_availability: list[dict[str, Any]],
    target_summary: dict[str, Any],
    target_rows: list[dict[str, Any]],
    official_ready: bool,
) -> list[dict[str, Any]]:
    target_status = target_summary.get("status", "") or target_summary.get("pm_gate_decision", "")
    return [
        {
            "readiness_id": "post_backtest_1min_observation_data",
            "status": "pass" if forward_summary else "missing",
            "value": f"{forward_summary.get('forward_first_available_date', '')}..{forward_summary.get('forward_last_available_date', '')}",
        },
        {
            "readiness_id": "forward_stock_days_available",
            "status": "pass" if _float(forward_summary.get("forward_stock_day_count")) > 0 else "missing",
            "value": int(_float(forward_summary.get("forward_stock_day_count", 0))),
        },
        {
            "readiness_id": "official_forward_targets",
            "status": "pass" if official_ready else "pending",
            "value": target_status or "not_available",
        },
        {
            "readiness_id": "target_rows",
            "status": "pass" if official_ready else "template_or_empty",
            "value": len(target_rows),
        },
        {
            "readiness_id": "source_availability_rows",
            "status": "pass" if forward_availability else "missing",
            "value": len(forward_availability),
        },
    ]


def _forward_data_boundary(forward_summary: dict[str, Any], official_ready: bool) -> list[dict[str, Any]]:
    date_range = f"{forward_summary.get('forward_first_available_date', '')}..{forward_summary.get('forward_last_available_date', '')}"
    return [
        {
            "boundary_id": "one_min_ohlcv_amount",
            "available": True,
            "scope": "1min open/high/low/close/volume/amount",
            "use_in_v5h_v1": "Compute VWAP proxies, amount pressure, and timing diagnostics.",
            "limitation": "Minute bars aggregate trades and cannot identify the initiating side of each trade.",
        },
        {
            "boundary_id": "forward_date_range",
            "available": bool(forward_summary),
            "scope": date_range,
            "use_in_v5h_v1": "Forward observation data after the formal backtest end.",
            "limitation": f"Formal backtest still ends at {FORMAL_BACKTEST_END}; forward data is paper observation only.",
        },
        {
            "boundary_id": "official_forward_targets",
            "available": official_ready,
            "scope": "official repaired V57f/V5f planned buy/increase orders",
            "use_in_v5h_v1": "Required before appending real forward buy observation rows.",
            "limitation": "Template rows are not orders and must not be treated as trades.",
        },
        {
            "boundary_id": "bid_ask_quote",
            "available": False,
            "scope": "best bid/ask quotes and spread",
            "use_in_v5h_v1": "Not used.",
            "limitation": "Current local 1min dataset does not include bid/ask snapshots.",
        },
        {
            "boundary_id": "order_book_depth",
            "available": False,
            "scope": "Level-2 depth, queue, and order book imbalance",
            "use_in_v5h_v1": "Not used.",
            "limitation": "Current local 1min dataset does not include order book or queue data.",
        },
        {
            "boundary_id": "tick_active_buy_sell_flow",
            "available": False,
            "scope": "tick-level active buy/sell direction",
            "use_in_v5h_v1": "Not used; amount pressure remains a bar-level proxy.",
            "limitation": "Signed minute return pressure is not true active order flow.",
        },
    ]


def _forward_append_plan(official_ready: bool) -> list[dict[str, Any]]:
    status = "ready" if official_ready else "ready_after_official_targets"
    return [
        {
            "step": 1,
            "status": status,
            "action": "Load official planned buy/increase orders after 2026-05-31.",
            "blocked_action": "Do not use TBD template rows as orders.",
        },
        {
            "step": 2,
            "status": status,
            "action": "For each buy order, compute 10:00 amount pressure using visible 1min volume and amount only.",
            "blocked_action": "Do not use same-day close, future VWAP, or later bars for timing.",
        },
        {
            "step": 3,
            "status": status,
            "action": "Select 10:00 if pressure is positive, otherwise 14:00.",
            "blocked_action": "Do not cancel or create orders from pressure.",
        },
        {
            "step": 4,
            "status": "ready",
            "action": "Append observation-only evaluation after prices become known.",
            "blocked_action": "Do not mark accepted from one forward batch.",
        },
    ]


def _jq_broker_mapping_rows() -> list[dict[str, Any]]:
    return [
        {
            "mapping_id": "pre_market_order_import",
            "platform_stage": "pre_market",
            "time": "before 09:30",
            "input": "official planned buy/increase orders only",
            "action": "Build buy candidate ledger for v1 timing decision.",
            "output": "pending_buy_order_ledger",
            "order_submission_allowed": False,
        },
        {
            "mapping_id": "ten_am_pressure_snapshot",
            "platform_stage": "intraday_observation",
            "time": "10:00",
            "input": "1min bars through 10:00 with price, volume, amount",
            "action": "Compute amount pressure bucket.",
            "output": "amount_pressure_bucket_1000",
            "order_submission_allowed": False,
        },
        {
            "mapping_id": "ten_am_early_buy",
            "platform_stage": "paper_execution",
            "time": "10:00",
            "input": "amount_pressure_bucket_1000 == positive_pressure",
            "action": "Paper-buy the already planned buy/increase order at 10:00 proxy.",
            "output": "paper_fill_1000",
            "order_submission_allowed": False,
        },
        {
            "mapping_id": "fourteen_fallback_buy",
            "platform_stage": "paper_execution",
            "time": "14:00",
            "input": "amount_pressure_bucket_1000 != positive_pressure or missing",
            "action": "Paper-buy the already planned buy/increase order at 14:00 proxy.",
            "output": "paper_fill_1400",
            "order_submission_allowed": False,
        },
        {
            "mapping_id": "evaluation_closeout",
            "platform_stage": "post_market",
            "time": "after close",
            "input": "same-day close / VWAP / actual paper fill audit",
            "action": "Evaluate execution edge only after timing decision is fixed.",
            "output": "forward_observation_result",
            "order_submission_allowed": False,
        },
    ]


def _paper_order_state_machine() -> list[dict[str, Any]]:
    return [
        {"state": "pending_official_order", "next_state": "await_1000_pressure", "condition": "official buy/increase order exists"},
        {"state": "await_1000_pressure", "next_state": "paper_filled_1000", "condition": "positive amount pressure at 10:00"},
        {"state": "await_1000_pressure", "next_state": "await_1400_fallback", "condition": "neutral/negative/missing pressure at 10:00"},
        {"state": "await_1400_fallback", "next_state": "paper_filled_1400", "condition": "14:00 price available"},
        {"state": "await_1400_fallback", "next_state": "missing_data_review", "condition": "14:00 price missing"},
        {"state": "paper_filled_1000", "next_state": "post_market_evaluate", "condition": "market close/evaluation price available"},
        {"state": "paper_filled_1400", "next_state": "post_market_evaluate", "condition": "market close/evaluation price available"},
    ]


def _platform_data_contract() -> list[dict[str, Any]]:
    return [
        {"field": "code", "jq_name": "security", "broker_name": "symbol", "required": True},
        {"field": "order_date", "jq_name": "context.current_dt.date()", "broker_name": "trade_date", "required": True},
        {"field": "planned_delta_weight", "jq_name": "target_delta_weight", "broker_name": "target_delta_weight", "required": True},
        {"field": "price_1000", "jq_name": "current_data/security minute price at 10:00", "broker_name": "quote_1000.last", "required": True},
        {"field": "volume_1000_window", "jq_name": "minute volume through 10:00", "broker_name": "bar_1m.volume", "required": True},
        {"field": "amount_1000_window", "jq_name": "minute money through 10:00", "broker_name": "bar_1m.amount", "required": True},
        {"field": "amount_pressure_bucket_1000", "jq_name": "computed locally", "broker_name": "computed locally", "required": True},
        {"field": "price_1400", "jq_name": "minute price at 14:00", "broker_name": "quote_1400.last", "required": True},
    ]


def _platform_preflight_checklist() -> list[dict[str, Any]]:
    return [
        {"check_id": "official_target_file_loaded", "status": "required_before_run", "reason": "v1 cannot create orders."},
        {"check_id": "one_min_price_volume_amount_available", "status": "required_before_run", "reason": "amount pressure needs volume and amount."},
        {"check_id": "clock_trigger_1000_available", "status": "required_before_run", "reason": "early buy decision is time-bound."},
        {"check_id": "clock_trigger_1400_available", "status": "required_before_run", "reason": "fallback buy decision is time-bound."},
        {"check_id": "sell_orders_routed_to_existing_policy", "status": "required_before_run", "reason": "v1 does not alter sells."},
        {"check_id": "paper_mode_only", "status": "required_before_run", "reason": "not accepted/live approved."},
    ]


def _combined_component_evidence(
    overlay_by_family: list[dict[str, Any]],
    combined: dict[str, Any],
    mr_gate: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = []
    for row in overlay_by_family:
        if row.get("variant_id") != COMBINED_VARIANT:
            continue
        rows.append(
            {
                "component": row.get("intent_family", ""),
                "order_type": row.get("order_type", ""),
                "order_count": int(_float(row.get("order_count"))),
                "executed_order_count": int(_float(row.get("executed_order_count"))),
                "decision_edge_bp": round(_float(row.get("avg_decision_edge_vs_close_all_orders")) * 10000.0, 6),
                "incremental_edge_bp": round(_float(row.get("avg_incremental_edge_vs_baseline_order")) * 10000.0, 6),
                "weighted_incremental_edge_bp": round(_float(row.get("weighted_avg_incremental_edge_vs_baseline_order")) * 10000.0, 6),
                "observation_status": "observation_only",
            }
        )
    rows.append(
        {
            "component": "combined_total",
            "order_type": "all_orders",
            "order_count": int(_float(combined.get("order_count"))),
            "executed_order_count": int(_float(combined.get("executed_order_count"))),
            "decision_edge_bp": round(_float(combined.get("avg_decision_edge_vs_close_all_orders")) * 10000.0, 6),
            "incremental_edge_bp": round(_float(combined.get("comparable_incremental_decision_edge_vs_baseline")) * 10000.0, 6),
            "weighted_incremental_edge_bp": round(_float(combined.get("comparable_weighted_incremental_decision_edge_vs_baseline")) * 10000.0, 6),
            "observation_status": "observation_only_not_mainline",
        }
    )
    rows.append(
        {
            "component": "mr_pressure_gate_standalone",
            "order_type": "mean_reversion_buy",
            "order_count": int(_float(mr_gate.get("order_count"))),
            "executed_order_count": int(_float(mr_gate.get("executed_order_count"))),
            "decision_edge_bp": round(_float(mr_gate.get("avg_decision_edge_vs_close_all_orders")) * 10000.0, 6),
            "incremental_edge_bp": round(_float(mr_gate.get("comparable_incremental_decision_edge_vs_baseline")) * 10000.0, 6),
            "weighted_incremental_edge_bp": round(_float(mr_gate.get("comparable_weighted_incremental_decision_edge_vs_baseline")) * 10000.0, 6),
            "observation_status": "observation_only_needs_independent_validation",
        }
    )
    return rows


def _combined_observation_spec(combined_queue: dict[str, Any], combined: dict[str, Any], mr_gate: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "observation_id": "scheduled_buy_v1_leg",
            "status": "frozen_in_v1_for_scheduled_buys",
            "rule": "10:00 if positive amount pressure else 14:00",
            "allowed_to_change_mainline": False,
            "notes": "This leg is the only frozen v1 part.",
        },
        {
            "observation_id": "mr_pressure_gate_leg",
            "status": "observation_only",
            "rule": "Mean-reversion buys only observed when amount pressure is neutral or positive.",
            "allowed_to_change_mainline": False,
            "notes": "Needs pre-2021 or future independent validation.",
        },
        {
            "observation_id": "combined_v1_total",
            "status": combined_queue.get("status", "observation_only_not_mainline"),
            "rule": combined_queue.get("includes", "scheduled v1 plus MR pressure gate"),
            "all_order_incremental_edge_bp": round(_float(combined.get("comparable_incremental_decision_edge_vs_baseline")) * 10000.0, 6),
            "mr_incremental_edge_bp": round(_float(mr_gate.get("comparable_incremental_decision_edge_vs_baseline")) * 10000.0, 6),
            "allowed_to_change_mainline": False,
            "notes": combined_queue.get("reason_not_frozen", ""),
        },
    ]


def _combined_risk_register() -> list[dict[str, Any]]:
    return [
        {"risk_id": "mixed_sample_pool", "severity": "medium", "mitigation": "Evaluate scheduled-buy leg and MR leg separately before any promotion."},
        {"risk_id": "mr_event_overfit", "severity": "high", "mitigation": "Require pre-2021 or forward independent samples; no acceptance from 2021-2026."},
        {"risk_id": "implicit_order_cancellation", "severity": "medium", "mitigation": "MR gate is observation-only; v1 scheduled buys must not be cancelled by pressure."},
        {"risk_id": "mainline_confusion", "severity": "medium", "mitigation": "Keep internal_subsleeve_mom12_70_30 as V5f mainline and V5h as execution diagnostics."},
    ]


def _shared_governance(extra: list[tuple[str, str, str]]) -> list[dict[str, Any]]:
    base = [
        ("no_v57f_core_modified", "pass", "V57f core is not modified."),
        ("no_v5f_mainline_modified", "pass", "V5f mainline is not modified."),
        ("no_sell_rule_change", "pass", "Sell/decrease orders remain on existing policy."),
        ("no_trading_frequency_increase", "pass", "V5h chooses timing inside already planned execution dates only."),
        ("no_new_buy_signal", "pass", "No new stocks or orders are created."),
        ("no_threshold_scan", "pass", "No thresholds are scanned in this queue execution."),
        ("not_accepted_not_live", "pass", "No component is accepted or live approved."),
        ("formal_backtest_end_preserved", "pass", f"Formal backtest ends at {FORMAL_BACKTEST_END}."),
    ]
    base.extend(extra)
    return [{"audit_id": key, "status": status, "detail": detail} for key, status, detail in base]


def _combined_summary(forward: dict[str, Any], mapping: dict[str, Any], combined: dict[str, Any]) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5h_buy_execution_queue_123",
        "status": "completed_v5h_buy_execution_queue_123",
        "queue_1_status": forward.get("status"),
        "queue_1_pm_gate_decision": forward.get("pm_gate_decision"),
        "queue_2_status": mapping.get("status"),
        "queue_2_pm_gate_decision": mapping.get("pm_gate_decision"),
        "queue_3_status": combined.get("status"),
        "queue_3_pm_gate_decision": combined.get("pm_gate_decision"),
        "frozen_variant": FROZEN_VARIANT,
        "forward_official_targets_available": forward.get("official_forward_targets_available", False),
        "forward_planned_buy_observation_rows": forward.get("planned_buy_observation_rows", 0),
        "source_forward_stock_day_count": forward.get("source_forward_stock_day_count", 0),
        "combined_v1_incremental_edge_bp": combined.get("combined_incremental_edge_bp", 0.0),
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "v5f_mainline_modified": False,
        "sell_rules_modified": False,
        "trading_frequency_increased": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "joinquant_started": False,
        "broker_started": False,
        "fatal_blocker_count": 0,
    }


def _write_queue_summary(root: Path, summary: dict[str, Any], child_summaries: list[dict[str, Any]]) -> None:
    out = root / QUEUE_OUT
    out.mkdir(parents=True, exist_ok=True)
    _write_json(out / "v5h_buy_execution_queue_123_summary.json", summary)
    _write_csv(
        out / "v5h_buy_execution_queue_123_child_summary.csv",
        [
            {
                "task": child.get("task"),
                "status": child.get("status"),
                "pm_gate_decision": child.get("pm_gate_decision"),
                "accepted": child.get("accepted"),
                "live_trading_approved": child.get("live_trading_approved"),
                "v57f_core_modified": child.get("v57f_core_modified"),
                "v5f_mainline_modified": child.get("v5f_mainline_modified"),
                "sell_rules_modified": child.get("sell_rules_modified"),
                "trading_frequency_increased": child.get("trading_frequency_increased"),
            }
            for child in child_summaries
        ],
    )
    _write_csv(
        out / "v5h_buy_execution_queue_123_pm_gate_decision.csv",
        [
            {
                "pm_gate_decision": "queue_123_completed_v1_forward_mapping_combined_observation_no_trading_change",
                "status": "completed",
                "accepted": False,
                "live_trading_approved": False,
                "deployment_approved": False,
                "v57f_core_modified": False,
                "v5f_mainline_modified": False,
                "sell_rules_modified": False,
                "trading_frequency_increased": False,
                "new_buy_signal_used": False,
            }
        ],
    )
    _write_csv(
        out / "v5h_buy_execution_queue_123_next_agent_queue.csv",
        [
            {
                "priority": 1,
                "queue_id": "wait_for_official_forward_buy_orders_then_append_v5h_v1",
                "status": "pending_official_targets",
                "scope": "Use frozen v1 on real planned buy orders only.",
            },
            {
                "priority": 2,
                "queue_id": "paper_platform_dry_run_when_jq_or_broker_available",
                "status": "ready_when_platform_available",
                "scope": "Paper mapping only; no live approval.",
            },
            {
                "priority": 3,
                "queue_id": "combined_v1_independent_validation_before_any_promotion",
                "status": "observation_only",
                "scope": "MR pressure gate must stay separate until independent evidence exists.",
            },
        ],
    )
    (out / "v5h_buy_execution_queue_123_report.md").write_text(_queue_report(summary, child_summaries), encoding="utf-8")
    (out / "v5h_buy_execution_queue_123_agent_execution_rules.md").write_text(_agent_rules("queue 123"), encoding="utf-8")


def _write_blocked(root: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    out = root / QUEUE_OUT
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "created_at_utc": now_utc(),
        "task": "v5h_buy_execution_queue_123",
        "status": "blocked_missing_or_invalid_required_input",
        "pm_gate_decision": "blocked_by_missing_or_invalid_required_input",
        "accepted": False,
        "live_trading_approved": False,
        "fatal_blocker_count": len(blockers),
        "fatal_blockers": blockers,
    }
    _write_json(out / "v5h_buy_execution_queue_123_summary.json", summary)
    _write_csv(out / "v5h_buy_execution_queue_123_blockers.csv", blockers)
    return summary


def _empty_forward_availability() -> list[dict[str, Any]]:
    return [{"availability_id": "forward_source_missing", "status": "missing", "value": ""}]


def _forward_report(
    summary: dict[str, Any],
    spec_rule: dict[str, Any],
    readiness: list[dict[str, Any]],
    data_boundary: list[dict[str, Any]],
) -> str:
    lines = [
        "# V5h Buy Execution Spec v1 Forward Observation",
        "",
        f"- Status: `{summary['status']}`",
        f"- Source forward stock-days: `{summary['source_forward_stock_day_count']}`",
        f"- Source forward date range: `{summary['source_forward_first_available_date']}` to `{summary['source_forward_last_available_date']}`",
        f"- Official forward targets available: `{summary['official_forward_targets_available']}`",
        f"- Planned buy observation rows: `{summary['planned_buy_observation_rows']}`",
        f"- Rule: `{spec_rule.get('early_buy_condition', '')}`; fallback `{spec_rule.get('fallback_condition', '')}`.",
        "",
        "## Readiness",
    ]
    for row in readiness:
        lines.append(f"- `{row['readiness_id']}`: `{row['status']}` / `{row['value']}`")
    lines.extend(["", "## Data Boundary"])
    for row in data_boundary:
        lines.append(f"- `{row['boundary_id']}`: available `{row['available']}`; {row['limitation']}")
    lines.extend(
        [
            "",
            "Current 1min data supports price/volume/amount timing observation only. It does not provide bid/ask, order-book depth, quote queue, or true active buy/sell order flow.",
            "",
            "No synthetic future order is created in this packet.",
            "",
        ]
    )
    return "\n".join(lines)


def _mapping_report(summary: dict[str, Any], mapping: list[dict[str, Any]], preflight: list[dict[str, Any]]) -> str:
    lines = [
        "# V5h Buy Execution Spec v1 JQ/Broker Paper Mapping",
        "",
        f"- Status: `{summary['status']}`",
        "- This is a paper mapping only. JoinQuant/broker was not started.",
        "",
        "## Mapping",
    ]
    for row in mapping:
        lines.append(f"- `{row['time']}` / `{row['mapping_id']}`: {row['action']}")
    lines.extend(["", "## Preflight"])
    for row in preflight:
        lines.append(f"- `{row['check_id']}`: `{row['status']}`")
    lines.append("")
    return "\n".join(lines)


def _combined_report(summary: dict[str, Any], components: list[dict[str, Any]], risks: list[dict[str, Any]]) -> str:
    lines = [
        "# V5h Combined Buy Execution Overlay v1 Observation",
        "",
        f"- Status: `{summary['status']}`",
        f"- Combined incremental edge: `{summary['combined_incremental_edge_bp']}` bp",
        f"- MR pressure gate incremental edge: `{summary['mr_pressure_gate_incremental_edge_bp']}` bp",
        "- Combined v1 remains observation-only and not mainline.",
        "",
        "## Components",
    ]
    for row in components:
        lines.append(
            f"- `{row['component']}` / `{row['order_type']}`: n={row['order_count']}, incremental={row['incremental_edge_bp']} bp, status `{row['observation_status']}`."
        )
    lines.extend(["", "## Risks"])
    for row in risks:
        lines.append(f"- `{row['risk_id']}`: `{row['severity']}`; {row['mitigation']}")
    lines.append("")
    return "\n".join(lines)


def _queue_report(summary: dict[str, Any], child_summaries: list[dict[str, Any]]) -> str:
    lines = [
        "# V5h Buy Execution Queue 123",
        "",
        f"- Status: `{summary['status']}`",
        f"- Frozen variant: `{summary['frozen_variant']}`",
        f"- Forward official targets available: `{summary['forward_official_targets_available']}`",
        f"- Combined v1 incremental edge: `{summary['combined_v1_incremental_edge_bp']}` bp",
        "",
        "## Child Queues",
    ]
    for child in child_summaries:
        lines.append(f"- `{child.get('task')}`: `{child.get('status')}` / `{child.get('pm_gate_decision')}`")
    lines.extend(["", "No accepted/live/deployment status is granted.", ""])
    return "\n".join(lines)


def _agent_rules(title: str) -> str:
    return "\n".join(
        [
            f"# V5h Buy Execution {title} Rules",
            "",
            "- Do not modify V57f core.",
            "- Do not modify V5f mainline.",
            "- Do not change sell/decrease rules.",
            "- Do not increase trading frequency.",
            "- Do not create new buy signals.",
            "- Do not treat TBD/template forward rows as official orders.",
            "- Do not start JoinQuant or broker sessions in this packet.",
            "- Do not mark accepted, live approved, or deployment approved.",
            "",
        ]
    )


def _find_variant(rows: list[dict[str, Any]], variant_id: str) -> dict[str, Any]:
    return next((row for row in rows if row.get("variant_id") == variant_id), {})


def _blocker(blocker_id: str, description: str) -> dict[str, Any]:
    return {"blocker_id": blocker_id, "severity": "fatal", "status": "blocking", "description": description}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_optional_json(path: Path) -> dict[str, Any]:
    return _read_json(path) if path.exists() else {}


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
    summary = run_v5h_buy_execution_queue_123(Path("."))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

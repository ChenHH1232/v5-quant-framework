from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5e_sleeve_cash_policy_quant_spec") / "current"
CASH_REVIEW = Path("v5e_cash_policy_review") / "current"
MODEL_COMPARISON = Path("v5e_profit_lock_model_comparison") / "current"
FORWARD_TRACKING = Path("v5e_profit_lock_main_forward_paper_execution_tracking") / "current"
CAPITAL_TEST = Path("v5e_capital_sensitivity_test") / "current"
FULL_INTRADAY_NAV = Path("v5e_full_intraday_nav_engineering_test") / "current"
STARTUP_REPAIR = Path("v5_startup_warmup_price_repair") / "current"
SHADOW_CONFIG = Path("config") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f_startup_repaired_shadow.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_sleeve_cash_policy_spec(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_sleeve_cash_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_sleeve_cash_policy_summary.json", summary)
        return summary

    cash_review = _read_json(root / CASH_REVIEW / "v5e_cash_policy_review_summary.json")
    model_summary = _read_json(root / MODEL_COMPARISON / "v5e_model_comparison_summary.json")
    forward_summary = _read_json(root / FORWARD_TRACKING / "v5e_profit_lock_forward_paper_summary.json")
    full_intraday_summary = _read_json(root / FULL_INTRADAY_NAV / "v5e_full_intraday_nav_summary.json")

    rule_spec = _rule_spec()
    schema = _bucket_schema()
    restore = _restore_rules()
    lifecycle = _event_lifecycle()
    comparison = _policy_comparison(cash_review, model_summary)
    proxy_gate = _cash_proxy_asset_data_gate()
    erc_boundary = _v5c_erc_boundary()
    v5d_boundary = _v5d_boundary()
    blocked = _blocked_actions()
    decision = _pm_decision()
    next_queue = _next_engineering_queue(decision[0]["pm_admission_decision"])
    nonfatal = [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Sleeve cash policy spec complete."}]

    _write_csv(out / "v5e_sleeve_cash_policy_rule_spec.csv", rule_spec)
    _write_csv(out / "v5e_sleeve_cash_bucket_schema.csv", schema)
    _write_csv(out / "v5e_sleeve_cash_restore_rule_matrix.csv", restore)
    _write_csv(out / "v5e_sleeve_cash_event_lifecycle.csv", lifecycle)
    _write_csv(out / "v5e_sleeve_cash_policy_comparison.csv", comparison)
    _write_csv(out / "v5e_cash_proxy_asset_data_gate.csv", proxy_gate)
    _write_csv(out / "v5e_sleeve_cash_v5c_erc_boundary.csv", erc_boundary)
    _write_csv(out / "v5e_sleeve_cash_v5d_execution_boundary.csv", v5d_boundary)
    _write_csv(out / "v5e_sleeve_cash_blocked_actions.csv", blocked)
    _write_csv(out / "v5e_sleeve_cash_pm_admission_decision.csv", decision)
    _write_csv(out / "v5e_sleeve_cash_next_engineering_queue.csv", next_queue)
    _write_csv(out / "v5e_sleeve_cash_blockers.csv", nonfatal)
    (out / "v5e_sleeve_cash_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5e_sleeve_cash_policy_report.md").write_text(_report(cash_review, model_summary, forward_summary, full_intraday_summary, decision), encoding="utf-8")

    summary = _summary(
        "completed_sleeve_cash_policy_quant_spec",
        decision[0]["pm_admission_decision"],
        [],
        cash_drag_delta_vs_baseline=float(cash_review.get("cash_drag_delta_vs_baseline", 0.0)),
        admitted_policy_count=sum(1 for row in decision if row["pm_admission_decision"].startswith("admit")),
        data_gate_policy_count=sum(1 for row in decision if row["pm_admission_decision"] == "data_gate_only_for_sleeve_cash_proxy_asset"),
    )
    _write_json(out / "v5e_sleeve_cash_policy_summary.json", summary)
    return summary


def _rule_spec() -> list[dict[str, Any]]:
    return [
        {
            "rule_id": "sleeve_cash_bucket_accounting",
            "rule_type": "cash_governance_accounting",
            "trigger_source": "v5e_profit_lock_main_20pct_sell50_exit_action",
            "cash_destination": "original_sleeve_cash_bucket",
            "trades_cash": False,
            "changes_v57f_selection": False,
            "changes_v57f_weights": False,
            "reentry_allowed": False,
            "cross_sleeve_transfer_allowed": False,
            "proxy_asset_allowed": False,
            "restore_timing": "next_v57f_regular_rebalance_only",
            "threshold_status": "no_new_threshold",
            "accepted": False,
        }
    ]


def _bucket_schema() -> list[dict[str, Any]]:
    fields = [
        ("event_id", "string", "Stable V5e exit event id."),
        ("trigger_date", "date", "Daily signal date; visible after close."),
        ("execution_date", "date", "T+1 execution date from V5e profit-lock."),
        ("code", "string", "Sold stock code."),
        ("sleeve_id", "string", "Original V57f sleeve id."),
        ("sold_value", "float", "Gross value sold by V5e exit."),
        ("sold_weight", "float", "Sold value divided by portfolio value."),
        ("sleeve_cash_bucket_id", "string", "sleeve_id plus rebalance cycle id."),
        ("sleeve_cash_balance", "float", "Cash balance attributed to original sleeve."),
        ("portfolio_cash_balance", "float", "Total portfolio cash including sleeve buckets."),
        ("sleeve_cash_weight", "float", "Sleeve cash divided by portfolio value."),
        ("portfolio_cash_weight", "float", "Portfolio cash divided by portfolio value."),
        ("frozen_until_rebalance_date", "date", "Next V57f regular rebalance."),
        ("restore_rule", "string", "Restore by next V57f target portfolio only."),
        ("reentry_allowed", "bool", "Must be false before next rebalance."),
        ("cross_sleeve_transfer_allowed", "bool", "Must be false."),
        ("proxy_asset_allowed", "bool", "Default false; separate approval only."),
        ("audit_status", "string", "open/frozen/restored/expired/review_required."),
    ]
    return [{"field_name": name, "field_type": typ, "description": desc, "required": True} for name, typ, desc in fields]


def _restore_rules() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "original_stock_reselected",
            "condition": "Next V57f rebalance selects same code.",
            "restore_rule": "Cash bucket is released into official rebalance cash and target weight is restored by V57f order set.",
            "v5e_may_buy": False,
        },
        {
            "case_id": "original_stock_not_reselected",
            "condition": "Next V57f rebalance does not select same code.",
            "restore_rule": "No stock-specific restore; cash joins regular rebalance cash and follows V57f selected targets.",
            "v5e_may_buy": False,
        },
        {
            "case_id": "same_sleeve_other_stock_selected",
            "condition": "Next V57f selects another stock in same sleeve.",
            "restore_rule": "Only regular V57f rebalance may allocate cash to the new target; sleeve cash policy does not choose replacement.",
            "v5e_may_buy": False,
        },
        {
            "case_id": "sleeve_weight_changes",
            "condition": "Next V57f / approved overlays change sleeve target exposure.",
            "restore_rule": "Sleeve cash bucket is released, then official target weights determine final exposure.",
            "v5e_may_buy": False,
        },
        {
            "case_id": "multiple_exits_same_sleeve",
            "condition": "Multiple V5e exits occur inside one sleeve in one cycle.",
            "restore_rule": "Aggregate balances by sleeve_cash_bucket_id; restore only at regular rebalance.",
            "v5e_may_buy": False,
        },
        {
            "case_id": "pre_rebalance_suspension",
            "condition": "Sold stock or target stock suspended before rebalance.",
            "restore_rule": "Do not force trade; V5d/L4 execution governance handles unfilled regular rebalance orders.",
            "v5e_may_buy": False,
        },
        {
            "case_id": "dividend_received",
            "condition": "Dividend arrives after partial sale.",
            "restore_rule": "Dividend from remaining shares goes to same sleeve cash bucket for attribution; portfolio cash accounting reconciles total.",
            "v5e_may_buy": False,
        },
        {
            "case_id": "corporate_action",
            "condition": "Split/bonus/rights action occurs after V5e exit.",
            "restore_rule": "Attribute action impact to residual holding and same sleeve bucket; no V5e discretionary trade.",
            "v5e_may_buy": False,
        },
        {
            "case_id": "erc_interaction",
            "condition": "V5c/ERC risk budget overlay exists.",
            "restore_rule": "Sleeve cash bucket is not ERC risk asset exposure by default; ERC interaction requires separate approval.",
            "v5e_may_buy": False,
        },
    ]


def _event_lifecycle() -> list[dict[str, Any]]:
    return [
        {"step": 1, "state": "triggered", "event": "V5e profit-lock signal visible after T close.", "trade_allowed": False},
        {"step": 2, "state": "executed", "event": "T+1 sell action executes under V5d execution governance if available.", "trade_allowed": True},
        {"step": 3, "state": "bucket_created", "event": "Sold proceeds enter original sleeve cash bucket.", "trade_allowed": False},
        {"step": 4, "state": "frozen", "event": "Bucket remains frozen until next regular V57f rebalance.", "trade_allowed": False},
        {"step": 5, "state": "audited", "event": "Report sleeve cash weight and portfolio cash weight daily.", "trade_allowed": False},
        {"step": 6, "state": "restored", "event": "At next V57f rebalance, official target portfolio controls recovery.", "trade_allowed": True},
    ]


def _policy_comparison(cash_review: dict[str, Any], model_summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "policy_id": "portfolio_cash_baseline",
            "description": "Current policy: V5e exit proceeds enter portfolio cash until next rebalance.",
            "changes_trade_path": False,
            "expected_return_change_from_accounting_only": 0.0,
            "cash_drag_delta_vs_baseline": cash_review.get("cash_drag_delta_vs_baseline", ""),
            "pm_status": "retain_as_baseline_policy",
        },
        {
            "policy_id": "sleeve_cash_bucket_accounting",
            "description": "Proceeds are attributed to original sleeve bucket but remain untraded.",
            "changes_trade_path": False,
            "expected_return_change_from_accounting_only": 0.0,
            "cash_drag_delta_vs_baseline": cash_review.get("cash_drag_delta_vs_baseline", ""),
            "pm_status": "admit_to_limited_engineering",
        },
        {
            "policy_id": "sleeve_cash_proxy_asset",
            "description": "Sleeve bucket may use a low-risk cash proxy asset after separate approval.",
            "changes_trade_path": True,
            "expected_return_change_from_accounting_only": "not_applicable",
            "current_vwap_adjusted_delta_vs_v57f": model_summary.get("vwap_adjusted_delta_return_pct_points_200w", ""),
            "pm_status": "data_gate_only",
        },
    ]


def _cash_proxy_asset_data_gate() -> list[dict[str, Any]]:
    rows = []
    for asset_type in ["money_market_etf", "short_term_treasury_etf", "short_duration_bond_etf", "reverse_repo_or_cash_yield_proxy"]:
        rows.append(
            {
                "asset_type": asset_type,
                "historical_daily_price_required": True,
                "minute_liquidity_required_if_execution_test": True,
                "fee_slippage_cost_required": True,
                "tradability_required": True,
                "income_accrual_required": True,
                "joinquant_or_account_tradability_required": True,
                "bond_or_rate_risk_introduced": asset_type != "money_market_etf",
                "equity_strategy_boundary_conflict_review": True,
                "specific_asset_user_approval_required": True,
                "current_status": "data_gate_only_not_engineering",
                "accepted": False,
            }
        )
    return rows


def _v5c_erc_boundary() -> list[dict[str, Any]]:
    return [
        {"system": "V5c_ERC", "boundary": "ERC sets sleeve risk budget at rebalance; sleeve cash policy attributes post-exit cash during holding period.", "cash_bucket_participates_in_erc": False, "separate_approval_required": True},
        {"system": "V57f", "boundary": "V57f target weights, sleeve definitions, selection and rebalance frequency are unchanged.", "cash_bucket_participates_in_erc": False, "separate_approval_required": False},
        {"system": "V5e_full_intraday", "boundary": "Full holding-period 5min trigger is diagnostic and excluded from sleeve cash spec.", "cash_bucket_participates_in_erc": False, "separate_approval_required": False},
    ]


def _v5d_boundary() -> list[dict[str, Any]]:
    return [
        {"system": "V5d", "responsibility": "Execute approved sell or rebalance orders.", "not_responsible_for": "Deciding cash policy or selecting replacement assets.", "new_approval_required_for_cash_proxy_execution": True},
        {"system": "V5e_sleeve_cash_policy", "responsibility": "Record, freeze, restore and audit sleeve cash bucket.", "not_responsible_for": "Execution scheduling or intraday trigger prediction.", "new_approval_required_for_cash_proxy_execution": True},
    ]


def _blocked_actions() -> list[dict[str, Any]]:
    actions = [
        "reentry_before_next_rebalance",
        "same_sleeve_replacement_stock_buy",
        "cross_sleeve_cash_transfer",
        "portfolio_cash_reallocation_to_other_stocks",
        "cash_proxy_asset_without_data_gate_and_user_approval",
        "new_profit_lock_threshold",
        "parameter_scan",
        "modify_v57f_core",
        "use_5min_trend_to_trigger_trade",
        "mark_v5e_or_sleeve_cash_policy_accepted",
    ]
    return [{"action": action, "status": "blocked", "reason": "Outside current sleeve cash accounting spec."} for action in actions]


def _pm_decision() -> list[dict[str, Any]]:
    return [
        {
            "policy_id": "sleeve_cash_bucket_accounting",
            "pm_admission_decision": "admit_sleeve_cash_bucket_accounting_to_limited_engineering",
            "reason": "Accounting/governance only; no new stock trade path, no reentry, no V57f change.",
            "accepted": False,
        },
        {
            "policy_id": "sleeve_cash_proxy_asset",
            "pm_admission_decision": "data_gate_only_for_sleeve_cash_proxy_asset",
            "reason": "Introduces a new asset class and requires data, liquidity, cost, and user approval gates.",
            "accepted": False,
        },
    ]


def _next_engineering_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "task": "V5e sleeve cash bucket accounting limited engineering",
            "scope": "Generate event-level sleeve cash ledger from V5e profit-lock exits; no trade path change.",
            "allowed": decision == "admit_sleeve_cash_bucket_accounting_to_limited_engineering",
            "requires_backtest": False,
            "requires_v57f_change": False,
        },
        {
            "priority": 2,
            "task": "Cash proxy asset data gate",
            "scope": "Prepare requirements only; do not select or trade asset.",
            "allowed": True,
            "requires_user_asset_approval": True,
            "requires_backtest": False,
        },
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    cash_drag_delta_vs_baseline: float = 0.0,
    admitted_policy_count: int = 0,
    data_gate_policy_count: int = 0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_sleeve_cash_policy_quant_spec",
        "status": status,
        "pm_admission_decision": decision,
        "cash_drag_delta_vs_baseline": cash_drag_delta_vs_baseline,
        "admitted_policy_count": admitted_policy_count,
        "data_gate_policy_count": data_gate_policy_count,
        "engineering_backtest_run": False,
        "joinquant_started": False,
        "network_fetch_started": False,
        "v57f_core_modified": False,
        "new_profit_lock_threshold_added": False,
        "reentry_allowed": False,
        "cross_sleeve_transfer_allowed": False,
        "cash_proxy_asset_selected": False,
        "accepted": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(
    cash_review: dict[str, Any],
    model_summary: dict[str, Any],
    forward_summary: dict[str, Any],
    full_intraday_summary: dict[str, Any],
    decision: list[dict[str, Any]],
) -> str:
    return "\n".join(
        [
            "# V5e Sleeve Cash Policy Quant Spec",
            "",
            f"- PM admission: `{decision[0]['pm_admission_decision']}`",
            "- Definition: V5e profit-lock sale proceeds are recorded in the original sleeve cash bucket, frozen, audited, and released only at the next regular V57f rebalance.",
            "- It is not reentry, replacement, cross-sleeve allocation, or a new asset trade.",
            "",
            "## Context",
            f"- Cash drag delta vs baseline: {cash_review.get('cash_drag_delta_vs_baseline')}",
            f"- Profit-lock VWAP adjusted delta vs V57f: {model_summary.get('vwap_adjusted_delta_return_pct_points_200w')} pct points",
            f"- Forward status: {forward_summary.get('tracking_status')}",
            f"- Full intraday PM gate: {full_intraday_summary.get('pm_gate_decision')}",
            "",
            "## Decision",
            "- Sleeve cash bucket accounting may enter limited engineering because it changes accounting/governance only.",
            "- Sleeve cash proxy assets remain data gate only and require user approval of a concrete asset before engineering.",
            "",
        ]
    )


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Sleeve Cash Policy Agent Execution Rules",
            "",
            "- Do not modify V57f.",
            "- Do not change V5e profit-lock threshold or sell fraction.",
            "- Do not run backtest in this spec task.",
            "- Do not allow reentry before next rebalance.",
            "- Do not transfer sleeve cash across sleeves.",
            "- Do not select or trade cash proxy assets without separate approval.",
            "- Do not use 5min data to trigger trades.",
            "- Do not mark accepted.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        CASH_REVIEW / "v5e_cash_policy_review_summary.json",
        CASH_REVIEW / "v5e_pm_gate_decision.csv",
        CASH_REVIEW / "v5e_cash_policy_candidate_matrix.csv",
        CASH_REVIEW / "v5e_sleeve_cash_policy_quant_spec_queue.csv",
        CASH_REVIEW / "v5e_portfolio_level_risk_release_conflict_matrix.csv",
        CASH_REVIEW / "v5e_5min_scope_comparison.csv",
        CASH_REVIEW / "v5e_full_holding_period_5min_trigger_risk_register.csv",
        MODEL_COMPARISON / "v5e_model_comparison_summary.json",
        MODEL_COMPARISON / "v5e_model_comparison_pm_gate_decision.csv",
        FORWARD_TRACKING / "v5e_profit_lock_forward_paper_summary.json",
        CAPITAL_TEST / "v5e_capital_sensitivity_summary.json",
        FULL_INTRADAY_NAV / "v5e_full_intraday_nav_summary.json",
        STARTUP_REPAIR / "v5_startup_warmup_price_repair_summary.json",
        SHADOW_CONFIG,
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    result = run_v5e_sleeve_cash_policy_spec()
    print(json.dumps(result, ensure_ascii=False, indent=2))

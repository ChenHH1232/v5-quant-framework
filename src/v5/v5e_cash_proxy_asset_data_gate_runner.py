from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5e_cash_proxy_asset_data_gate") / "current"
BUCKET_DIR = Path("v5e_sleeve_cash_bucket_engineering") / "current"
POLICY_SPEC_DIR = Path("v5e_sleeve_cash_policy_quant_spec") / "current"
CASH_POLICY_DIR = Path("v5e_cash_policy_review") / "current"
MODEL_DIR = Path("v5e_profit_lock_model_comparison") / "current"
CAPITAL_DIR = Path("v5e_capital_sensitivity_test") / "current"
STARTUP_DIR = Path("v5_startup_warmup_price_repair") / "current"
SHADOW_CONFIG = Path("config") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f_startup_repaired_shadow.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_cash_proxy_asset_data_gate(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_cash_proxy_asset_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_cash_proxy_asset_data_gate_summary.json", summary)
        return summary

    bucket_summary = _read_json(root / BUCKET_DIR / "v5e_sleeve_cash_bucket_summary.json")
    model_summary = _read_json(root / MODEL_DIR / "v5e_model_comparison_summary.json")
    capital_summary = _read_json(root / CAPITAL_DIR / "v5e_capital_sensitivity_summary.json")
    source_gate = _read_csv(root / POLICY_SPEC_DIR / "v5e_cash_proxy_asset_data_gate.csv")
    drag_by_sleeve = _read_csv(root / BUCKET_DIR / "v5e_sleeve_cash_drag_by_sleeve.csv")
    top_periods = _read_csv(root / BUCKET_DIR / "v5e_top_cash_bucket_periods.csv")

    candidates = _candidate_type_matrix(source_gate)
    data_req = _data_requirements(candidates)
    tradability = _tradability_gate(candidates)
    risk = _risk_register(candidates)
    cost = _cost_liquidity_gate(candidates)
    income = _income_accounting_spec(candidates)
    v57f_boundary = _v57f_boundary()
    v5d_boundary = _v5d_boundary()
    blocked = _blocked_actions()
    decision = _pm_gate_decision(candidates)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    nonfatal = _nonfatal_blockers()

    _write_csv(out / "v5e_cash_proxy_asset_candidate_type_matrix.csv", candidates)
    _write_csv(out / "v5e_cash_proxy_asset_data_requirement.csv", data_req)
    _write_csv(out / "v5e_cash_proxy_asset_tradability_gate.csv", tradability)
    _write_csv(out / "v5e_cash_proxy_asset_risk_register.csv", risk)
    _write_csv(out / "v5e_cash_proxy_asset_cost_liquidity_gate.csv", cost)
    _write_csv(out / "v5e_cash_proxy_asset_income_accounting_spec.csv", income)
    _write_csv(out / "v5e_cash_proxy_asset_v57f_boundary.csv", v57f_boundary)
    _write_csv(out / "v5e_cash_proxy_asset_v5d_execution_boundary.csv", v5d_boundary)
    _write_csv(out / "v5e_cash_proxy_asset_blocked_actions.csv", blocked)
    _write_csv(out / "v5e_cash_proxy_asset_pm_gate_decision.csv", decision)
    _write_csv(out / "v5e_cash_proxy_asset_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5e_cash_proxy_asset_blockers.csv", nonfatal)
    (out / "v5e_cash_proxy_asset_next_prompt.md").write_text(_next_prompt(decision[0]), encoding="utf-8")
    (out / "v5e_cash_proxy_asset_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5e_cash_proxy_asset_data_gate_report.md").write_text(
        _report(bucket_summary, model_summary, capital_summary, drag_by_sleeve, top_periods, decision),
        encoding="utf-8",
    )

    summary = _summary(
        "completed_cash_proxy_asset_data_gate",
        decision[0]["pm_gate_decision"],
        [],
        candidate_type_count=len(candidates),
        asset_selected=False,
        primary_cash_drag_sleeve=bucket_summary.get("primary_cash_drag_sleeve", ""),
        cash_reconciliation_error=bucket_summary.get("cash_reconciliation_max_abs_error", 0.0),
    )
    _write_json(out / "v5e_cash_proxy_asset_data_gate_summary.json", summary)
    return summary


def _candidate_type_matrix(source_gate: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in source_gate:
        asset_type = row["asset_type"]
        rows.append(
            {
                "asset_type": asset_type,
                "role": "cash_proxy_candidate_type_only",
                "allowed_current_task": True,
                "specific_asset_selected": False,
                "trade_allowed": False,
                "engineering_backtest_allowed": False,
                "requires_user_asset_approval": True,
                "requires_daily_price_gate": row.get("historical_daily_price_required", "True"),
                "requires_liquidity_gate": row.get("minute_liquidity_required_if_execution_test", "True"),
                "requires_cost_gate": row.get("fee_slippage_cost_required", "True"),
                "requires_account_tradability_gate": row.get("joinquant_or_account_tradability_required", "True"),
                "introduces_rate_or_bond_risk": row.get("bond_or_rate_risk_introduced", "True"),
                "equity_strategy_boundary_review_required": True,
                "current_status": "data_gate_only_not_selected_not_accepted",
                "accepted": False,
            }
        )
    return rows


def _data_requirements(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    fields = [
        ("historical_daily_price", "daily open/high/low/close, volume, amount, adjustment policy", "PIT required", "valuation and carry proxy"),
        ("corporate_actions", "dividend, split, fund distribution, redemption or conversion events", "PIT required", "income and total-return accounting"),
        ("minute_liquidity", "5min bars around planned execution days if later approved", "execution only", "execution price governance"),
        ("tradability", "paused, limit status, subscription/redemption restrictions if applicable", "PIT required", "order feasibility"),
        ("cost_fee_tax", "commission, fund fees, taxes, spread, slippage assumptions", "pre-registered", "cost gate"),
        ("account_eligibility", "whether the asset can be traded in JoinQuant and intended account", "current-state gate", "deployment feasibility"),
    ]
    for candidate in candidates:
        for field_id, requirement, pit_status, usage in fields:
            rows.append(
                {
                    "asset_type": candidate["asset_type"],
                    "data_gate_id": field_id,
                    "requirement": requirement,
                    "pit_status_required": pit_status,
                    "allowed_usage": usage,
                    "available_in_current_task": "not_audited_no_network_fetch",
                    "blocker_if_missing_for_engineering": True,
                }
            )
    return rows


def _tradability_gate(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks = [
        ("listed_and_active", "Asset is listed and active for the whole intended history."),
        ("account_tradeable", "Asset can be traded in the target account or platform."),
        ("open_sell_buy_feasible", "Daily open or approved execution window has sufficient prints."),
        ("paused_limit_safe", "Paused and limit-day behavior can be handled without forced fills."),
        ("minimum_order_safe", "Minimum lot and minimum commission do not dominate order value."),
    ]
    return [
        {
            "asset_type": c["asset_type"],
            "check_id": check_id,
            "description": description,
            "current_status": "requires_specific_asset_selection",
            "passed": False,
            "fatal_for_current_data_gate": False,
        }
        for c in candidates
        for check_id, description in checks
    ]


def _risk_register(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base = [
        ("equity_boundary_drift", "Cash proxy creates a non-equity sleeve component and cannot be treated as V57f core."),
        ("interest_rate_risk", "Treasury or bond proxy can lose value when rates move."),
        ("liquidity_gap", "Low turnover proxy can distort execution benefit."),
        ("income_accounting_error", "Distribution/carry treatment can overstate or understate cash drag relief."),
        ("implicit_market_timing", "Choosing proxy after observing history would create selection bias."),
        ("erc_conflict", "Proxy asset exposure may conflict with V5c/ERC if treated as risk asset."),
    ]
    rows = []
    for c in candidates:
        for risk_id, description in base:
            severity = "high" if risk_id in {"equity_boundary_drift", "implicit_market_timing"} else "medium"
            rows.append(
                {
                    "asset_type": c["asset_type"],
                    "risk_id": risk_id,
                    "severity": severity,
                    "description": description,
                    "mitigation": "Specific asset approval, PIT data gate, fixed cost policy, and separate engineering approval.",
                    "blocks_acceptance": True,
                }
            )
    return rows


def _cost_liquidity_gate(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metrics = [
        "daily_turnover",
        "bid_ask_spread_or_proxy",
        "5min_vwap_availability",
        "commission_and_min_fee",
        "tax_or_fund_fee",
        "slippage_policy",
        "capacity_at_50w_200w_800w",
    ]
    return [
        {
            "asset_type": c["asset_type"],
            "metric": metric,
            "required_before_engineering": True,
            "current_status": "pending_specific_asset",
            "threshold_status": "not_parameterized_in_this_task",
        }
        for c in candidates
        for metric in metrics
    ]


def _income_accounting_spec(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for c in candidates:
        rows.append(
            {
                "asset_type": c["asset_type"],
                "income_source": "distribution_or_cash_yield",
                "accounting_rule": "Income belongs to the original sleeve cash bucket until next V57f rebalance.",
                "total_return_required": True,
                "cash_bucket_transfer_allowed": False,
                "reentry_allowed": False,
                "accepted": False,
            }
        )
    return rows


def _v57f_boundary() -> list[dict[str, Any]]:
    return [
        {"boundary": "v57f_selection", "rule": "Cash proxy data gate cannot alter V57f stock universe or selection.", "allowed": False},
        {"boundary": "v57f_weighting", "rule": "Cash proxy cannot alter frozen V57f target weights without separate approval.", "allowed": False},
        {"boundary": "v57f_rebalance_frequency", "rule": "Cash proxy does not change regular rebalance dates.", "allowed": False},
        {"boundary": "strategy_status", "rule": "V5e remains overlay candidate, not V57f replacement and not accepted.", "allowed": False},
    ]


def _v5d_boundary() -> list[dict[str, Any]]:
    return [
        {"component": "V5e", "responsibility": "Decides profit-lock exit and records sleeve cash.", "uses_5min_trigger": False},
        {"component": "cash_proxy_data_gate", "responsibility": "Defines data and approval requirements only.", "uses_5min_trigger": False},
        {"component": "V5d", "responsibility": "May execute approved proxy trades later, only after separate engineering approval.", "uses_5min_trigger": False},
    ]


def _blocked_actions() -> list[dict[str, Any]]:
    actions = [
        "select_specific_cash_proxy_asset_without_user_approval",
        "buy_cash_proxy_asset_in_current_task",
        "run_engineering_backtest_in_current_task",
        "modify_v57f_core",
        "change_v5e_profit_lock_threshold",
        "parameter_scan_cash_proxy",
        "reentry_before_next_rebalance",
        "cross_sleeve_cash_transfer",
        "use_5min_data_as_profit_lock_trigger",
        "mark_v5e_or_proxy_asset_accepted",
    ]
    return [{"action": action, "blocked": True, "reason": "Outside current data-gate boundary."} for action in actions]


def _pm_gate_decision(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "pm_gate_decision": "cash_proxy_asset_data_gate_complete_requires_user_asset_selection",
            "candidate_type_count": len(candidates),
            "data_gate_complete_for_types": True,
            "specific_asset_selected": False,
            "engineering_test_allowed_now": False,
            "accepted": False,
            "reason": "Candidate asset classes are scoped, but a concrete tradable asset must be approved and audited before engineering.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "task": "User-approved cash proxy asset selection gate",
            "scope": "Choose at most one concrete proxy candidate type/asset for PIT data audit; no acceptance.",
            "allowed": decision == "cash_proxy_asset_data_gate_complete_requires_user_asset_selection",
            "requires_user_asset_approval": True,
            "requires_backtest": False,
        },
        {
            "priority": 2,
            "task": "Cash proxy PIT data audit after asset selection",
            "scope": "Audit daily price, distribution, cost, liquidity, and tradability for the selected asset.",
            "allowed": False,
            "requires_user_asset_approval": True,
            "requires_backtest": False,
        },
    ]


def _nonfatal_blockers() -> list[dict[str, Any]]:
    return [
        {
            "blocker_id": "specific_asset_not_selected",
            "severity": "next_gate",
            "status": "not_blocking_data_gate_blocks_engineering",
            "description": "A concrete cash proxy asset requires user approval before data fetch or engineering.",
        }
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    candidate_type_count: int = 0,
    asset_selected: bool = False,
    primary_cash_drag_sleeve: str = "",
    cash_reconciliation_error: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_cash_proxy_asset_data_gate",
        "status": status,
        "pm_gate_decision": decision,
        "candidate_type_count": candidate_type_count,
        "specific_asset_selected": asset_selected,
        "cash_proxy_asset_trade_allowed": False,
        "engineering_backtest_run": False,
        "joinquant_started": False,
        "network_fetch_started": False,
        "v57f_core_modified": False,
        "v5e_threshold_modified": False,
        "reentry_allowed": False,
        "cross_sleeve_transfer_allowed": False,
        "accepted": False,
        "primary_cash_drag_sleeve": primary_cash_drag_sleeve,
        "cash_reconciliation_error": cash_reconciliation_error,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(
    bucket_summary: dict[str, Any],
    model_summary: dict[str, Any],
    capital_summary: dict[str, Any],
    drag_by_sleeve: list[dict[str, str]],
    top_periods: list[dict[str, str]],
    decision: list[dict[str, Any]],
) -> str:
    sleeve = drag_by_sleeve[0]["sleeve_id"] if drag_by_sleeve else ""
    period = top_periods[0].get("rebalance_period", top_periods[0].get("sleeve_cash_bucket_id", "")) if top_periods else ""
    return "\n".join(
        [
            "# V5e Cash Proxy Asset Data Gate",
            "",
            f"- PM gate decision: `{decision[0]['pm_gate_decision']}`",
            "- Status: data gate only; no concrete proxy asset selected, no trades, no backtest.",
            f"- Primary cash drag sleeve from sleeve cash ledger: `{bucket_summary.get('primary_cash_drag_sleeve', sleeve)}`",
            f"- Largest bucket period reference: `{period}`",
            "",
            "## Context",
            f"- V5e profit-lock VWAP adjusted delta vs V57f at 200w: {model_summary.get('vwap_adjusted_delta_return_pct_points_200w')} pct points.",
            f"- Capital sensitivity PM gate: {capital_summary.get('pm_gate_decision')}",
            "- Cash drag is policy-driven; this packet only asks whether a low-risk proxy asset data gate is feasible.",
            "",
            "## Decision",
            "- Money-market ETF, treasury ETF, short-duration bond ETF, and reverse repo/cash-yield proxy are candidate types only.",
            "- A specific tradable asset must be approved before PIT data fetch, liquidity audit, or engineering test.",
            "- The proxy cannot be treated as accepted, cannot modify V57f, and cannot create reentry before next rebalance.",
            "",
        ]
    )


def _next_prompt(decision: dict[str, Any]) -> str:
    return f"""工作目录：
D:\\hh\\codex\\v5

任务名称：
V5e cash proxy asset selection + PIT data audit

任务目标：
基于 `v5e_cash_proxy_asset_data_gate/current/`，仅在用户明确批准一个具体现金替代标的后，审计该标的的 PIT 日线、分红/收益、流动性、成本和可交易性。不得回测，不得买入，不得标记 accepted。

当前 gate：
`{decision["pm_gate_decision"]}`

硬边界：
- 不修改 V57f / ERC / V5d。
- 不改变 V5e +20% / sell50 规则。
- 不允许 reentry before next rebalance。
- 不允许跨 sleeve 转移现金。
- 不使用 5分钟走势触发交易。
- 未经用户批准不得选择具体 cash proxy asset。
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Cash Proxy Asset Data Gate Agent Rules",
            "",
            "- Data gate only; do not run an engineering backtest.",
            "- Do not select a concrete cash proxy asset without user approval.",
            "- Do not buy cash proxy assets or any stock in this task.",
            "- Do not modify V57f, ERC, V5d, or V5e thresholds.",
            "- Do not use 5min data as a stop-profit trigger.",
            "- Do not allow reentry or cross-sleeve transfer before next rebalance.",
            "- Do not mark accepted.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        BUCKET_DIR / "v5e_sleeve_cash_bucket_summary.json",
        BUCKET_DIR / "v5e_sleeve_cash_next_agent_queue.csv",
        BUCKET_DIR / "v5e_sleeve_cash_drag_by_sleeve.csv",
        BUCKET_DIR / "v5e_top_cash_bucket_periods.csv",
        POLICY_SPEC_DIR / "v5e_cash_proxy_asset_data_gate.csv",
        CASH_POLICY_DIR / "v5e_cash_policy_review_summary.json",
        MODEL_DIR / "v5e_model_comparison_summary.json",
        CAPITAL_DIR / "v5e_capital_sensitivity_summary.json",
        STARTUP_DIR / "v5_startup_warmup_price_repair_summary.json",
        SHADOW_CONFIG,
    ]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "status": "blocking",
            "path": str(path),
            "description": "Required cash proxy data-gate input is missing.",
        }
        for path in required
        if not (root / path).exists()
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


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
    result = run_v5e_cash_proxy_asset_data_gate()
    print(json.dumps(result, ensure_ascii=False, indent=2))

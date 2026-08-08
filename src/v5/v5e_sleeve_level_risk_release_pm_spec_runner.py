from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5e_sleeve_level_risk_release_pm_spec") / "current"
BUCKET_DIR = Path("v5e_sleeve_cash_bucket_engineering") / "current"
CASH_POLICY_DIR = Path("v5e_cash_policy_review") / "current"
MODEL_DIR = Path("v5e_profit_lock_model_comparison") / "current"
FULL_INTRADAY_DIR = Path("v5e_full_intraday_nav_engineering_test") / "current"
CAPITAL_DIR = Path("v5e_capital_sensitivity_test") / "current"
V5C_DIR = Path("v5c_closeout") / "current"
V5D_DIR = Path("v5d_closeout") / "current"
STARTUP_DIR = Path("v5_startup_warmup_price_repair") / "current"
SHADOW_CONFIG = Path("config") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f_startup_repaired_shadow.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_sleeve_level_risk_release_pm_spec(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_sleeve_level_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_sleeve_level_risk_release_summary.json", summary)
        return summary

    bucket_summary = _read_json(root / BUCKET_DIR / "v5e_sleeve_cash_bucket_summary.json")
    model_summary = _read_json(root / MODEL_DIR / "v5e_model_comparison_summary.json")
    full_intraday_summary = _read_json(root / FULL_INTRADAY_DIR / "v5e_full_intraday_nav_summary.json")
    capital_summary = _read_json(root / CAPITAL_DIR / "v5e_capital_sensitivity_summary.json")
    drag_by_sleeve = _read_csv(root / BUCKET_DIR / "v5e_sleeve_cash_drag_by_sleeve.csv")
    drag_by_period = _read_csv(root / BUCKET_DIR / "v5e_sleeve_cash_drag_by_rebalance_period.csv")

    boundary = _rule_boundary()
    directions = _candidate_direction_matrix(drag_by_sleeve)
    visibility = _trigger_visibility()
    cash_interaction = _cash_policy_interaction()
    v57f_boundary = _v57f_boundary()
    erc_conflict = _v5c_erc_conflict_matrix()
    v5d_boundary = _v5d_boundary()
    data_gate = _data_gate(directions)
    blocked = _blocked_actions()
    decision = _pm_admission_decision()
    next_queue = _next_quant_spec_queue(decision[0]["pm_admission_decision"])
    blockers_out = _nonfatal_blockers()

    _write_csv(out / "v5e_sleeve_level_rule_boundary.csv", boundary)
    _write_csv(out / "v5e_sleeve_level_candidate_direction_matrix.csv", directions)
    _write_csv(out / "v5e_sleeve_level_trigger_visibility.csv", visibility)
    _write_csv(out / "v5e_sleeve_level_cash_policy_interaction.csv", cash_interaction)
    _write_csv(out / "v5e_sleeve_level_v57f_boundary.csv", v57f_boundary)
    _write_csv(out / "v5e_sleeve_level_v5c_erc_conflict_matrix.csv", erc_conflict)
    _write_csv(out / "v5e_sleeve_level_v5d_boundary.csv", v5d_boundary)
    _write_csv(out / "v5e_sleeve_level_data_gate.csv", data_gate)
    _write_csv(out / "v5e_sleeve_level_blocked_actions.csv", blocked)
    _write_csv(out / "v5e_sleeve_level_pm_admission_decision.csv", decision)
    _write_csv(out / "v5e_sleeve_level_next_quant_spec_queue.csv", next_queue)
    _write_csv(out / "v5e_sleeve_level_blockers.csv", blockers_out)
    (out / "v5e_sleeve_level_next_prompt.md").write_text(_next_prompt(decision[0]), encoding="utf-8")
    (out / "v5e_sleeve_level_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5e_sleeve_level_risk_release_report.md").write_text(
        _report(bucket_summary, model_summary, full_intraday_summary, capital_summary, drag_by_sleeve, drag_by_period, decision),
        encoding="utf-8",
    )

    summary = _summary(
        "completed_sleeve_level_risk_release_pm_spec",
        decision[0]["pm_admission_decision"],
        [],
        candidate_direction_count=len(directions),
        primary_cash_drag_sleeve=bucket_summary.get("primary_cash_drag_sleeve", ""),
        quant_spec_allowed_count=sum(1 for row in directions if row["pm_status"] == "admit_to_quant_spec_boundary"),
    )
    _write_json(out / "v5e_sleeve_level_risk_release_summary.json", summary)
    return summary


def _rule_boundary() -> list[dict[str, Any]]:
    return [
        {
            "boundary_id": "definition",
            "rule": "Sleeve-level risk release is a V5e research direction that may reduce original sleeve exposure after a pre-registered daily sleeve-level condition.",
            "allowed_in_current_task": True,
            "engineering_trade_allowed": False,
        },
        {
            "boundary_id": "not_single_name_reentry",
            "rule": "It must not buy back a V5e-sold stock before the next V57f rebalance.",
            "allowed_in_current_task": False,
            "engineering_trade_allowed": False,
        },
        {
            "boundary_id": "not_same_sleeve_replacement",
            "rule": "It must not replace a sold stock with another stock in the same sleeve outside regular V57f rebalance.",
            "allowed_in_current_task": False,
            "engineering_trade_allowed": False,
        },
        {
            "boundary_id": "not_erc_replacement",
            "rule": "It must not replace V5c/ERC, which remains a separate overlay candidate.",
            "allowed_in_current_task": False,
            "engineering_trade_allowed": False,
        },
        {
            "boundary_id": "not_intraday_trigger",
            "rule": "Full holding-period 5min trigger remains diagnostic and cannot be mixed into this PM spec.",
            "allowed_in_current_task": False,
            "engineering_trade_allowed": False,
        },
    ]


def _candidate_direction_matrix(drag_by_sleeve: list[dict[str, str]]) -> list[dict[str, Any]]:
    primary = drag_by_sleeve[0]["sleeve_id"] if drag_by_sleeve else "unknown"
    return [
        {
            "direction_id": "sleeve_level_daily_profit_lock",
            "description": "Daily sleeve-level profit state releases part of sleeve exposure after a pre-registered threshold.",
            "why_considered": "Single-name exits create cash drag and may sell winners too early; sleeve-level state may be more stable.",
            "threshold_status": "not_selected_in_pm_spec_requires_next_quant_spec",
            "uses_intraday_trigger": False,
            "changes_v57f_selection": False,
            "reentry_allowed": False,
            "pm_status": "admit_to_quant_spec_boundary",
        },
        {
            "direction_id": "sleeve_level_trailing_risk_release",
            "description": "Daily sleeve peak and drawdown state releases risk after sleeve-level gains.",
            "why_considered": "Trailing behavior is more explainable as risk release than repeated single-name profit locks.",
            "threshold_status": "not_selected_in_pm_spec_requires_next_quant_spec",
            "uses_intraday_trigger": False,
            "changes_v57f_selection": False,
            "reentry_allowed": False,
            "pm_status": "admit_to_quant_spec_boundary",
        },
        {
            "direction_id": "primary_cash_drag_sleeve_focus",
            "description": f"Start diagnostics with sleeve `{primary}` because it is the largest sleeve cash drag source.",
            "why_considered": "Focuses attribution, but must not choose thresholds by historical sleeve performance.",
            "threshold_status": "diagnostic_only_no_threshold",
            "uses_intraday_trigger": False,
            "changes_v57f_selection": False,
            "reentry_allowed": False,
            "pm_status": "diagnostic_only",
        },
        {
            "direction_id": "portfolio_level_risk_release",
            "description": "Reduce total portfolio exposure after portfolio-level profit/risk condition.",
            "why_considered": "Could address cash drag at portfolio level, but overlaps with V5c/ERC defense ideas.",
            "threshold_status": "separate_pm_spec_required",
            "uses_intraday_trigger": False,
            "changes_v57f_selection": False,
            "reentry_allowed": False,
            "pm_status": "separate_pm_spec_required",
        },
    ]


def _trigger_visibility() -> list[dict[str, Any]]:
    return [
        {
            "signal_component": "sleeve_daily_return",
            "visible_time": "T close plus data publication",
            "can_trigger_same_day_trade": False,
            "earliest_execution": "T+1",
            "future_bar_required": False,
        },
        {
            "signal_component": "sleeve_peak_close_anchor",
            "visible_time": "after each completed daily close",
            "can_trigger_same_day_trade": False,
            "earliest_execution": "T+1",
            "future_bar_required": False,
        },
        {
            "signal_component": "next_v57f_rebalance_result",
            "visible_time": "only on official rebalance decision date",
            "can_be_used_before_rebalance": False,
            "earliest_execution": "regular_rebalance_only",
            "future_bar_required": True,
        },
    ]


def _cash_policy_interaction() -> list[dict[str, Any]]:
    return [
        {
            "cash_policy": "portfolio_cash_baseline",
            "interaction": "Sleeve release creates portfolio cash until next rebalance.",
            "allowed": True,
            "expected_accounting_change": "none",
        },
        {
            "cash_policy": "sleeve_cash_bucket_accounting",
            "interaction": "Released exposure is attributed to original sleeve bucket for audit.",
            "allowed": True,
            "expected_accounting_change": "clearer sleeve-level cash attribution",
        },
        {
            "cash_policy": "cash_proxy_asset",
            "interaction": "Released sleeve cash may use a proxy only after separate asset approval and engineering.",
            "allowed": False,
            "expected_accounting_change": "separate_data_gate_only",
        },
    ]


def _v57f_boundary() -> list[dict[str, Any]]:
    return [
        {"boundary": "core_sleeve", "rule": "Do not change V57f sleeves.", "allowed": False},
        {"boundary": "stock_selection", "rule": "Do not add replacement stocks or change selected names.", "allowed": False},
        {"boundary": "target_weight", "rule": "Do not change regular target weights; overlay only changes interim exposure if later approved.", "allowed": False},
        {"boundary": "rebalance_frequency", "rule": "Do not change official rebalance schedule.", "allowed": False},
        {"boundary": "status", "rule": "V5e remains candidate only, not accepted and not V57f replacement.", "allowed": False},
    ]


def _v5c_erc_conflict_matrix() -> list[dict[str, Any]]:
    return [
        {
            "topic": "scope",
            "v5c_erc_role": "Rebalance-time sleeve weight overlay candidate.",
            "sleeve_level_risk_release_role": "Holding-period exposure release candidate.",
            "conflict_status": "manageable_with_boundary",
        },
        {
            "topic": "risk_budget",
            "v5c_erc_role": "May alter sleeve target risk weights at rebalance.",
            "sleeve_level_risk_release_role": "Must not alter ERC history or budget without separate approval.",
            "conflict_status": "requires_formal_conflict_review_before_engineering",
        },
        {
            "topic": "cash_bucket",
            "v5c_erc_role": "Does not own V5e cash bucket accounting.",
            "sleeve_level_risk_release_role": "Uses sleeve cash bucket attribution after approved release.",
            "conflict_status": "no_direct_conflict_current_spec",
        },
    ]


def _v5d_boundary() -> list[dict[str, Any]]:
    return [
        {"component": "V5e sleeve-level PM spec", "responsibility": "Define if and when a sleeve exposure release could be considered.", "trade_execution": False},
        {"component": "V5d", "responsibility": "If later approved, execute sell orders and unfilled remediation.", "trade_execution": True},
        {"component": "5min data", "responsibility": "Execution governance only; not trigger generation.", "trade_execution": False},
    ]


def _data_gate(directions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    requirements = [
        ("repaired_v57f_daily_holdings", "daily holdings with sleeve_id and weights", "trigger_and_attribution"),
        ("repaired_v57f_daily_returns", "portfolio and sleeve-level daily returns", "trigger"),
        ("repaired_v57f_rebalance_calendar", "official next rebalance date", "restore_governance"),
        ("daily_stock_ohlc", "open/high/low/close for held stocks", "valuation"),
        ("sleeve_cash_ledger", "V5e sleeve cash bucket balances", "cash_attribution"),
        ("corporate_actions_dividends", "dividend and action attribution by sleeve", "accounting"),
        ("t_plus_one_tradability", "paused and limit fields", "execution_gate"),
    ]
    rows = []
    for direction in directions:
        if direction["pm_status"] not in {"admit_to_quant_spec_boundary", "diagnostic_only"}:
            continue
        for req_id, description, usage in requirements:
            rows.append(
                {
                    "direction_id": direction["direction_id"],
                    "data_requirement": req_id,
                    "description": description,
                    "pit_required": True,
                    "allowed_usage": usage,
                    "current_status": "required_for_next_quant_spec",
                    "blocker_if_missing_for_engineering": True,
                }
            )
    return rows


def _blocked_actions() -> list[dict[str, Any]]:
    actions = [
        "single_name_reentry_before_next_rebalance",
        "same_sleeve_replacement_stock_buy",
        "cash_reallocation_to_other_stocks",
        "cross_sleeve_cash_transfer",
        "modify_v57f_selection_or_weights",
        "parameter_scan_or_threshold_grid",
        "use_5min_intraday_trigger",
        "merge_with_erc_without_conflict_review",
        "mark_accepted",
        "run_engineering_backtest_from_pm_spec",
    ]
    return [{"action": action, "blocked": True, "reason": "Outside sleeve-level PM spec boundary."} for action in actions]


def _pm_admission_decision() -> list[dict[str, Any]]:
    return [
        {
            "pm_admission_decision": "admit_sleeve_level_risk_release_to_quant_spec_not_engineering",
            "quant_spec_allowed": True,
            "engineering_test_allowed_now": False,
            "requires_pre_registered_thresholds": True,
            "requires_erc_conflict_review": True,
            "accepted": False,
            "reason": "The direction is plausible after single-name cash drag attribution, but rules and thresholds must be fixed in a separate Quant spec before engineering.",
        }
    ]


def _next_quant_spec_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "task": "V5e sleeve-level risk release Quant spec",
            "scope": "Pre-register one sleeve-level profit/risk release rule and one conservative pressure rule; no parameter grid.",
            "allowed": decision == "admit_sleeve_level_risk_release_to_quant_spec_not_engineering",
            "requires_backtest": False,
            "requires_erc_conflict_review": True,
        },
        {
            "priority": 2,
            "task": "V5e cash proxy asset selection gate",
            "scope": "Optional parallel data gate; requires concrete user-approved asset before fetch.",
            "allowed": True,
            "requires_user_asset_approval": True,
            "requires_backtest": False,
        },
    ]


def _nonfatal_blockers() -> list[dict[str, Any]]:
    return [
        {
            "blocker_id": "quant_thresholds_not_pre_registered",
            "severity": "next_gate",
            "status": "not_blocking_pm_spec_blocks_engineering",
            "description": "Sleeve-level engineering cannot start until the next Quant spec fixes non-optimized thresholds and actions.",
        },
        {
            "blocker_id": "erc_conflict_review_required",
            "severity": "next_gate",
            "status": "not_blocking_pm_spec_blocks_engineering",
            "description": "Formal boundary with V5c/ERC must be reviewed before any portfolio-level or sleeve-weight overlay engineering.",
        },
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    candidate_direction_count: int = 0,
    primary_cash_drag_sleeve: str = "",
    quant_spec_allowed_count: int = 0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_sleeve_level_risk_release_pm_spec",
        "status": status,
        "pm_admission_decision": decision,
        "candidate_direction_count": candidate_direction_count,
        "quant_spec_allowed_count": quant_spec_allowed_count,
        "primary_cash_drag_sleeve": primary_cash_drag_sleeve,
        "engineering_backtest_run": False,
        "joinquant_started": False,
        "network_fetch_started": False,
        "v57f_core_modified": False,
        "v5e_threshold_modified": False,
        "new_threshold_added": False,
        "reentry_allowed": False,
        "cross_sleeve_transfer_allowed": False,
        "accepted": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(
    bucket_summary: dict[str, Any],
    model_summary: dict[str, Any],
    full_intraday_summary: dict[str, Any],
    capital_summary: dict[str, Any],
    drag_by_sleeve: list[dict[str, str]],
    drag_by_period: list[dict[str, str]],
    decision: list[dict[str, Any]],
) -> str:
    primary = drag_by_sleeve[0]["sleeve_id"] if drag_by_sleeve else bucket_summary.get("primary_cash_drag_sleeve", "")
    period = drag_by_period[0].get("rebalance_period", drag_by_period[0].get("sleeve_cash_bucket_id", "")) if drag_by_period else ""
    return "\n".join(
        [
            "# V5e Sleeve-Level Risk Release PM Spec",
            "",
            f"- PM admission: `{decision[0]['pm_admission_decision']}`",
            "- Status: PM/spec only; not an engineering test and not accepted.",
            f"- Primary cash drag sleeve: `{primary}`",
            f"- Top cash drag period reference: `{period}`",
            "",
            "## Context",
            f"- Profit-lock VWAP adjusted delta vs V57f at 200w: {model_summary.get('vwap_adjusted_delta_return_pct_points_200w')} pct points.",
            f"- Capital sensitivity gate: {capital_summary.get('pm_gate_decision')}",
            f"- Full intraday NAV gate: {full_intraday_summary.get('pm_gate_decision')}",
            "",
            "## Boundary",
            "- Sleeve-level risk release is not same-sleeve stock replacement and not reentry.",
            "- It may enter a future Quant spec only after thresholds, visibility, action size, cash handling, and ERC conflict boundaries are pre-registered.",
            "- 5min data remains execution/audit only and cannot become the trigger source.",
            "",
        ]
    )


def _next_prompt(decision: dict[str, Any]) -> str:
    return f"""工作目录：
D:\\hh\\codex\\v5

任务名称：
V5e sleeve-level risk release Quant spec

任务目标：
基于 `v5e_sleeve_level_risk_release_pm_spec/current/`，生成 sleeve-level risk release 的 Quant spec。只允许预注册固定规则、数据门、T+1 可见性、现金桶恢复、V5c/ERC 冲突边界和后续工程队列；不得回测、不得扫阈值。

当前 admission：
`{decision["pm_admission_decision"]}`

硬边界：
- 不修改 V57f core sleeve、选股、权重、调仓频率。
- 不允许 single-name reentry before next rebalance。
- 不允许 same-sleeve replacement buy。
- 不使用 5分钟走势触发交易。
- 不与 V5c/ERC 合并，先做冲突审查。
- 不标记 accepted。
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Sleeve-Level Risk Release Agent Rules",
            "",
            "- PM/spec only; do not run engineering backtest.",
            "- Do not modify V57f, ERC, or V5d.",
            "- Do not add unapproved thresholds or scan parameters.",
            "- Do not allow stock reentry or same-sleeve replacement before next rebalance.",
            "- Do not move cash across sleeves.",
            "- Do not use 5min data as a trigger.",
            "- Do not mark accepted.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        BUCKET_DIR / "v5e_sleeve_cash_bucket_summary.json",
        BUCKET_DIR / "v5e_sleeve_cash_drag_by_sleeve.csv",
        BUCKET_DIR / "v5e_sleeve_cash_drag_by_rebalance_period.csv",
        BUCKET_DIR / "v5e_sleeve_cash_next_agent_queue.csv",
        CASH_POLICY_DIR / "v5e_cash_policy_review_summary.json",
        CASH_POLICY_DIR / "v5e_sleeve_level_profit_lock_pm_spec_queue.csv",
        MODEL_DIR / "v5e_model_comparison_summary.json",
        FULL_INTRADAY_DIR / "v5e_full_intraday_nav_summary.json",
        CAPITAL_DIR / "v5e_capital_sensitivity_summary.json",
        V5C_DIR / "v5c_closeout_summary.json",
        V5D_DIR / "v5d_closeout_summary.json",
        STARTUP_DIR / "v5_startup_warmup_price_repair_summary.json",
        SHADOW_CONFIG,
    ]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "status": "blocking",
            "path": str(path),
            "description": "Required sleeve-level risk release PM-spec input is missing.",
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
    result = run_v5e_sleeve_level_risk_release_pm_spec()
    print(json.dumps(result, ensure_ascii=False, indent=2))

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5e_sleeve_level_risk_release_quant_spec") / "current"
PM_SPEC_DIR = Path("v5e_sleeve_level_risk_release_pm_spec") / "current"
CASH_PROXY_ENG_DIR = Path("v5e_511360_cash_proxy_limited_engineering") / "current"
BUCKET_DIR = Path("v5e_sleeve_cash_bucket_engineering") / "current"
STARTUP_DIR = Path("v5_startup_warmup_price_repair") / "current"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_sleeve_level_risk_release_quant_spec(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_sleeve_level_quant_spec_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_sleeve_level_quant_spec_summary.json", summary)
        return summary

    pm_summary = _read_json(root / PM_SPEC_DIR / "v5e_sleeve_level_risk_release_summary.json")
    if pm_summary.get("pm_admission_decision") != "admit_sleeve_level_risk_release_to_quant_spec_not_engineering":
        blocker = {"blocker_id": "pm_not_admitted", "severity": "fatal", "status": "blocking", "description": "PM spec did not admit sleeve-level risk release to Quant spec."}
        _write_csv(out / "v5e_sleeve_level_quant_spec_blockers.csv", [blocker])
        summary = _summary("blocked_pm_not_admitted", "blocked_until_pm_admission", [blocker])
        _write_json(out / "v5e_sleeve_level_quant_spec_summary.json", summary)
        return summary

    rule_spec = _rule_spec()
    thresholds = _threshold_policy()
    trade_action = _trade_action_policy()
    cash_interaction = _cash_policy_interaction()
    trigger_visibility = _trigger_visibility()
    erc_boundary = _erc_boundary()
    data_gate = _data_gate()
    blocked = _blocked_actions()
    decision = _pm_gate_decision()
    queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Quant spec complete; not engineered and not accepted."}]

    _write_csv(out / "v5e_sleeve_level_rule_spec.csv", rule_spec)
    _write_csv(out / "v5e_sleeve_level_pre_registered_threshold_policy.csv", thresholds)
    _write_csv(out / "v5e_sleeve_level_trade_action_policy.csv", trade_action)
    _write_csv(out / "v5e_sleeve_level_cash_policy_interaction.csv", cash_interaction)
    _write_csv(out / "v5e_sleeve_level_trigger_visibility_matrix.csv", trigger_visibility)
    _write_csv(out / "v5e_sleeve_level_v5c_erc_boundary.csv", erc_boundary)
    _write_csv(out / "v5e_sleeve_level_data_gate.csv", data_gate)
    _write_csv(out / "v5e_sleeve_level_blocked_actions.csv", blocked)
    _write_csv(out / "v5e_sleeve_level_quant_pm_gate_decision.csv", decision)
    _write_csv(out / "v5e_sleeve_level_next_engineering_queue.csv", queue)
    _write_csv(out / "v5e_sleeve_level_quant_spec_blockers.csv", blockers_out)
    (out / "v5e_sleeve_level_next_prompt.md").write_text(_next_prompt(decision[0]), encoding="utf-8")
    (out / "v5e_sleeve_level_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5e_sleeve_level_quant_spec_report.md").write_text(_report(decision), encoding="utf-8")

    summary = _summary(
        "completed_sleeve_level_risk_release_quant_spec",
        decision[0]["pm_gate_decision"],
        [],
        rule_count=len(rule_spec),
        engineering_test_allowed=True,
    )
    _write_json(out / "v5e_sleeve_level_quant_spec_summary.json", summary)
    return summary


def _rule_spec() -> list[dict[str, Any]]:
    return [
        {
            "rule_id": "sleeve_level_daily_profit_release_main",
            "scope": "sleeve",
            "trigger": "sleeve holding-period return reaches +12pct based on T close",
            "action": "T+1 reduce sleeve exposure by 25pct of active sleeve market value into sleeve cash bucket",
            "threshold_status": "pre_registered_not_optimized",
            "sell_fraction": 0.25,
            "reentry_allowed": False,
            "uses_5min_trigger": False,
            "accepted": False,
        },
        {
            "rule_id": "sleeve_level_trailing_release_conservative",
            "scope": "sleeve",
            "trigger": "sleeve peak return at least +15pct and drawdown from known peak close reaches -6pct",
            "action": "T+1 reduce sleeve exposure by 20pct of active sleeve market value into sleeve cash bucket",
            "threshold_status": "pre_registered_not_optimized",
            "sell_fraction": 0.20,
            "reentry_allowed": False,
            "uses_5min_trigger": False,
            "accepted": False,
        },
    ]


def _threshold_policy() -> list[dict[str, Any]]:
    return [
        {"rule_id": "sleeve_level_daily_profit_release_main", "threshold": "+12pct sleeve holding-period return", "source": "PM/Quant pre-registration", "scan_allowed": False, "historical_optimization_used": False},
        {"rule_id": "sleeve_level_trailing_release_conservative", "threshold": "+15pct peak and -6pct drawdown", "source": "PM/Quant pre-registration", "scan_allowed": False, "historical_optimization_used": False},
    ]


def _trade_action_policy() -> list[dict[str, Any]]:
    return [
        {"field": "trigger_date", "policy": "T daily close visible after close"},
        {"field": "execution_date", "policy": "T+1 open daily proxy"},
        {"field": "cash_destination", "policy": "original sleeve cash bucket"},
        {"field": "reentry_policy", "policy": "no reentry before next V57f rebalance"},
        {"field": "restore_policy", "policy": "next V57f regular rebalance only"},
        {"field": "unfilled_policy", "policy": "record unfilled; do not force trade"},
    ]


def _cash_policy_interaction() -> list[dict[str, Any]]:
    return [
        {"policy": "hold_cash", "interaction": "released sleeve exposure stays as sleeve cash", "allowed": True},
        {"policy": "511360_cash_proxy", "interaction": "can be tested separately after cash proxy PM/Quant review", "allowed": False},
        {"policy": "same_sleeve_replacement", "interaction": "not allowed", "allowed": False},
    ]


def _trigger_visibility() -> list[dict[str, Any]]:
    return [
        {"input": "sleeve daily close value", "visible": "after T close", "future_data_required": False},
        {"input": "sleeve peak close anchor", "visible": "after each historical close", "future_data_required": False},
        {"input": "next rebalance selected stocks", "visible": "not before rebalance", "future_data_required": True},
    ]


def _erc_boundary() -> list[dict[str, Any]]:
    return [
        {"topic": "V5c/ERC", "boundary": "ERC remains separate rebalance-time candidate; sleeve-level V5e is holding-period exit overlay.", "conflict_review_required": True},
        {"topic": "risk_budget", "boundary": "Sleeve-level release cannot alter ERC weights or history.", "conflict_review_required": True},
    ]


def _data_gate() -> list[dict[str, Any]]:
    requirements = [
        "repaired_v57f_daily_holdings_by_sleeve",
        "repaired_v57f_daily_returns",
        "sleeve_daily_market_value",
        "repaired_rebalance_calendar",
        "daily_stock_open_high_low_close",
        "t_plus_one_tradability",
        "sleeve_cash_bucket_ledger",
    ]
    return [{"requirement": req, "pit_required": True, "status": "required_for_limited_engineering"} for req in requirements]


def _blocked_actions() -> list[dict[str, Any]]:
    actions = [
        "modify_v57f",
        "scan_thresholds",
        "use_5min_trigger",
        "same_sleeve_replacement_buy",
        "single_name_reentry_before_next_rebalance",
        "cross_sleeve_cash_transfer",
        "mark_accepted",
        "merge_with_erc_without_review",
    ]
    return [{"action": action, "blocked": True} for action in actions]


def _pm_gate_decision() -> list[dict[str, Any]]:
    return [
        {
            "pm_gate_decision": "admit_sleeve_level_risk_release_to_limited_engineering_test_not_accepted",
            "engineering_test_allowed": True,
            "threshold_scan_used": False,
            "accepted": False,
            "reason": "Two pre-registered sleeve-level rules are fixed; limited engineering may compare them without parameter scan.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "task": "V5e sleeve-level risk release limited engineering test",
            "allowed": decision == "admit_sleeve_level_risk_release_to_limited_engineering_test_not_accepted",
            "requires_backtest": True,
        }
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    rule_count: int = 0,
    engineering_test_allowed: bool = False,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_sleeve_level_risk_release_quant_spec",
        "status": status,
        "pm_gate_decision": decision,
        "rule_count": rule_count,
        "engineering_test_allowed": engineering_test_allowed,
        "accepted": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "new_unapproved_threshold_added": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(decision: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# V5e Sleeve-Level Risk Release Quant Spec",
            "",
            f"- PM gate decision: `{decision[0]['pm_gate_decision']}`",
            "- Status: Quant spec only; not accepted.",
            "- Main rule: +12pct sleeve holding-period return, T+1 release 25pct exposure.",
            "- Conservative trailing rule: +15pct peak and -6pct drawdown, T+1 release 20pct exposure.",
            "- No parameter scan and no 5min trigger.",
            "",
        ]
    )


def _next_prompt(decision: dict[str, Any]) -> str:
    return f"""工作目录：
D:\\hh\\codex\\v5

任务名称：
V5e sleeve-level risk release limited engineering test

任务目标：
基于 `v5e_sleeve_level_risk_release_quant_spec/current/`，测试已预注册的 sleeve-level 风险释放规则。不得新增阈值、不得参数扫描、不得修改 V57f、不得标记 accepted。

当前 gate：
`{decision["pm_gate_decision"]}`
"""


def _agent_rules() -> str:
    return "\n".join(["# V5e Sleeve-Level Risk Release Quant Spec Rules", "", "- Do not modify V57f.", "- Do not scan thresholds.", "- Do not use 5min trigger.", "- Do not mark accepted.", ""])


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        PM_SPEC_DIR / "v5e_sleeve_level_risk_release_summary.json",
        BUCKET_DIR / "v5e_sleeve_cash_event_ledger.csv",
        STARTUP_DIR / "v5_startup_warmup_price_repair_summary.json",
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
    result = run_v5e_sleeve_level_risk_release_quant_spec()
    print(json.dumps(result, ensure_ascii=False, indent=2))

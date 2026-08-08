from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5e_511360_cash_proxy_limited_engineering_spec") / "current"
PIT_DIR = Path("v5e_511360_pit_data_audit") / "current"
SELECTION_DIR = Path("v5e_short_financing_etf_cash_proxy_selection_gate") / "current"
BUCKET_DIR = Path("v5e_sleeve_cash_bucket_engineering") / "current"
SLEEVE_LEVEL_PM_DIR = Path("v5e_sleeve_level_risk_release_pm_spec") / "current"
STARTUP_DIR = Path("v5_startup_warmup_price_repair") / "current"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_511360_cash_proxy_limited_engineering_spec(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_511360_cash_proxy_spec_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_511360_cash_proxy_spec_summary.json", summary)
        return summary

    pit_summary = _read_json(root / PIT_DIR / "v5e_511360_pit_data_audit_summary.json")
    if pit_summary.get("pm_gate_decision") != "ready_for_511360_cash_proxy_limited_engineering_spec":
        blocker = {
            "blocker_id": "pit_gate_not_ready",
            "severity": "fatal",
            "status": "blocking",
            "description": "511360 PIT data audit has not admitted the candidate to limited engineering spec.",
        }
        _write_csv(out / "v5e_511360_cash_proxy_spec_blockers.csv", [blocker])
        summary = _summary("blocked_pit_gate_not_ready", "blocked_until_pit_gate_ready", [blocker])
        _write_json(out / "v5e_511360_cash_proxy_spec_summary.json", summary)
        return summary

    rule_spec = _rule_spec()
    trade_path = _trade_path_spec()
    accounting = _accounting_policy()
    cost_policy = _cost_policy()
    conflict = _conflict_resolution()
    data_gate = _data_gate()
    blocked = _blocked_actions()
    decision = _pm_gate_decision()
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Spec complete; not accepted."}]

    _write_csv(out / "v5e_511360_cash_proxy_rule_spec.csv", rule_spec)
    _write_csv(out / "v5e_511360_cash_proxy_trade_path_spec.csv", trade_path)
    _write_csv(out / "v5e_511360_cash_proxy_accounting_policy.csv", accounting)
    _write_csv(out / "v5e_511360_cash_proxy_cost_policy.csv", cost_policy)
    _write_csv(out / "v5e_511360_cash_proxy_conflict_resolution.csv", conflict)
    _write_csv(out / "v5e_511360_cash_proxy_data_gate.csv", data_gate)
    _write_csv(out / "v5e_511360_cash_proxy_blocked_actions.csv", blocked)
    _write_csv(out / "v5e_511360_cash_proxy_pm_gate_decision.csv", decision)
    _write_csv(out / "v5e_511360_cash_proxy_next_engineering_queue.csv", next_queue)
    _write_csv(out / "v5e_511360_cash_proxy_spec_blockers.csv", blockers_out)
    (out / "v5e_511360_cash_proxy_next_prompt.md").write_text(_next_prompt(decision[0]), encoding="utf-8")
    (out / "v5e_511360_cash_proxy_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5e_511360_cash_proxy_spec_report.md").write_text(_report(pit_summary, decision), encoding="utf-8")

    summary = _summary(
        "completed_511360_cash_proxy_limited_engineering_spec",
        decision[0]["pm_gate_decision"],
        [],
        candidate_asset_code="511360.SH",
        engineering_test_allowed=True,
    )
    _write_json(out / "v5e_511360_cash_proxy_spec_summary.json", summary)
    return summary


def _rule_spec() -> list[dict[str, Any]]:
    return [
        {
            "rule_id": "v5e_511360_sleeve_cash_proxy",
            "base_v5e_rule": "v5e_profit_lock_main_20pct_sell50",
            "proxy_asset_code": "511360.SH",
            "proxy_asset_role": "cash_proxy_for_sleeve_cash_bucket",
            "trigger_source": "existing_v5e_exit_action_only",
            "buy_proxy_date": "exit_execution_date",
            "buy_proxy_price_policy": "511360 same-day open after cash is created by V5e exit proxy",
            "sell_proxy_date": "next_v57f_regular_rebalance_date",
            "sell_proxy_price_policy": "511360 restore-date open before official V57f rebalance restore",
            "daily_mark_policy": "511360 close for daily NAV proxy",
            "cash_bucket_owner": "original_sleeve_id",
            "reentry_allowed": False,
            "cross_sleeve_transfer_allowed": False,
            "changes_v57f_core": False,
            "accepted": False,
        }
    ]


def _trade_path_spec() -> list[dict[str, Any]]:
    return [
        {"step": 1, "event": "V5e profit-lock sell executes", "timing": "T+1 open", "trade_asset": "original_stock", "changes_existing_v5e": False},
        {"step": 2, "event": "Proxy buy uses freed sleeve cash", "timing": "same execution date open proxy", "trade_asset": "511360.SH", "changes_existing_v5e": True},
        {"step": 3, "event": "Proxy is marked to market", "timing": "daily close until restore", "trade_asset": "511360.SH", "changes_existing_v5e": True},
        {"step": 4, "event": "Proxy is sold and cash released", "timing": "next V57f rebalance date open", "trade_asset": "511360.SH", "changes_existing_v5e": True},
        {"step": 5, "event": "V57f official rebalance restores target portfolio", "timing": "regular rebalance", "trade_asset": "V57f targets", "changes_existing_v5e": False},
    ]


def _accounting_policy() -> list[dict[str, Any]]:
    return [
        {"topic": "income", "policy": "511360 distributions/NAV effects remain attributed to original sleeve cash bucket until restore.", "required": True},
        {"topic": "daily_nav", "policy": "Add realized plus unrealized proxy PnL to V5e hold-cash portfolio value.", "required": True},
        {"topic": "open_forward_restore", "policy": "If next rebalance is outside sample, mark active proxy to last available close and keep restore open.", "required": True},
        {"topic": "total_return", "policy": "Use adjusted daily price and NAV audit; raw close-only comparison is diagnostic only.", "required": True},
    ]


def _cost_policy() -> list[dict[str, Any]]:
    return [
        {"cost_id": "commission", "value": 0.00003, "unit": "notional", "pre_registered": True, "scan_allowed": False},
        {"cost_id": "min_commission", "value": 5.0, "unit": "CNY per order", "pre_registered": True, "scan_allowed": False},
        {"cost_id": "slippage_proxy", "value": "open_price_daily_proxy; VWAP optional later", "unit": "policy", "pre_registered": True, "scan_allowed": False},
        {"cost_id": "fund_fee", "value": "embedded in ETF NAV/price, separately disclosed in report", "unit": "policy", "pre_registered": True, "scan_allowed": False},
    ]


def _conflict_resolution() -> list[dict[str, Any]]:
    return [
        {"case_id": "v57f_rebalance_same_day", "rule": "Regular V57f rebalance has priority; proxy is released before rebalance accounting.", "allowed": True},
        {"case_id": "missing_proxy_price", "rule": "Do not force fill; record unfilled and keep cash for that window.", "allowed": True},
        {"case_id": "stock_reentry", "rule": "Proxy trade is not stock reentry; sold stock cannot be bought before next rebalance.", "allowed": False},
        {"case_id": "cross_sleeve", "rule": "Proxy PnL remains inside original sleeve cash bucket.", "allowed": False},
        {"case_id": "erc_overlap", "rule": "Do not count 511360 as ERC sleeve risk asset without separate approval.", "allowed": False},
    ]


def _data_gate() -> list[dict[str, Any]]:
    return [
        {"data_id": "511360_daily_price", "source": "v5e_511360_pit_data_audit", "status": "passed"},
        {"data_id": "511360_nav_history", "source": "v5e_511360_pit_data_audit", "status": "passed"},
        {"data_id": "execution_liquidity", "source": "v5e_511360_pit_data_audit", "status": "passed"},
        {"data_id": "v5e_sleeve_cash_ledger", "source": "v5e_sleeve_cash_bucket_engineering", "status": "passed"},
        {"data_id": "v5e_profit_lock_hold_cash_run", "source": "v5e_limited_engineering_loop", "status": "required_for_engineering"},
    ]


def _blocked_actions() -> list[dict[str, Any]]:
    actions = [
        "modify_v57f_core",
        "change_profit_lock_threshold",
        "parameter_scan_proxy_asset",
        "mark_511360_accepted",
        "use_5min_trigger",
        "single_name_reentry_before_next_rebalance",
        "cross_sleeve_cash_transfer",
        "buy_other_stocks_with_proxy_cash",
    ]
    return [{"action": action, "blocked": True, "reason": "Outside 511360 cash proxy limited engineering boundary."} for action in actions]


def _pm_gate_decision() -> list[dict[str, Any]]:
    return [
        {
            "pm_gate_decision": "admit_511360_cash_proxy_to_limited_engineering_test_not_accepted",
            "engineering_test_allowed": True,
            "requires_backtest": True,
            "accepted": False,
            "reason": "PIT data passed and fixed trade/accounting path is specified; limited engineering test may compare hold-cash vs 511360 proxy.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "task": "V5e 511360 cash proxy limited engineering test",
            "scope": "Compare V57f baseline, V5e hold cash, and V5e with 511360 proxy; no threshold changes.",
            "allowed": decision == "admit_511360_cash_proxy_to_limited_engineering_test_not_accepted",
            "requires_backtest": True,
        }
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    candidate_asset_code: str = "",
    engineering_test_allowed: bool = False,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_511360_cash_proxy_limited_engineering_spec",
        "status": status,
        "pm_gate_decision": decision,
        "candidate_asset_code": candidate_asset_code,
        "engineering_test_allowed": engineering_test_allowed,
        "accepted": False,
        "v57f_core_modified": False,
        "v5e_threshold_modified": False,
        "threshold_scan_used": False,
        "joinquant_started": False,
        "network_fetch_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(pit_summary: dict[str, Any], decision: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# V5e 511360 Cash Proxy Limited Engineering Spec",
            "",
            f"- PM gate decision: `{decision[0]['pm_gate_decision']}`",
            "- Status: engineering spec only; not accepted.",
            f"- PIT price rows: {pit_summary.get('price_rows')}",
            f"- PIT NAV rows: {pit_summary.get('nav_rows')}",
            "",
            "## Fixed Path",
            "- Use only existing V5e profit-lock exit actions.",
            "- Buy 511360 with sleeve cash on the exit execution date open.",
            "- Sell 511360 on the next regular V57f rebalance date open.",
            "- Keep PnL attributed to the original sleeve cash bucket.",
            "",
        ]
    )


def _next_prompt(decision: dict[str, Any]) -> str:
    return f"""工作目录：
D:\\hh\\codex\\v5

任务名称：
V5e 511360 cash proxy limited engineering test

任务目标：
基于 `v5e_511360_cash_proxy_limited_engineering_spec/current/`，比较 V57f baseline、V5e hold cash、V5e + 511360 cash proxy。不得修改 V57f，不得修改 V5e 阈值，不得参数扫描，不得标记 accepted。

当前 gate：
`{decision["pm_gate_decision"]}`
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e 511360 Cash Proxy Spec Agent Rules",
            "",
            "- Do not modify V57f or V5e thresholds.",
            "- Do not scan proxy assets or parameters.",
            "- Do not allow stock reentry before next rebalance.",
            "- 511360 is a candidate proxy only; do not mark accepted.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        PIT_DIR / "v5e_511360_pit_data_audit_summary.json",
        SELECTION_DIR / "v5e_short_financing_etf_selection_summary.json",
        BUCKET_DIR / "v5e_sleeve_cash_event_ledger.csv",
        SLEEVE_LEVEL_PM_DIR / "v5e_sleeve_level_risk_release_summary.json",
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
    result = run_v5e_511360_cash_proxy_limited_engineering_spec()
    print(json.dumps(result, ensure_ascii=False, indent=2))

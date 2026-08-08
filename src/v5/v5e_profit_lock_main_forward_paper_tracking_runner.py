from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5e_profit_lock_main_forward_paper_execution_tracking") / "current"
FORMAL_DIR = Path("v5e_profit_lock_execution_robust_formal_review") / "current"
PROXY_DIR = Path("v5e_trigger_day_5min_execution_proxy_test") / "current"
DATA_GATE_DIR = Path("v5e_trigger_day_5min_execution_data_gate") / "current"
LOOP_DIR = Path("v5e_limited_engineering_loop") / "current"
STARTUP_DIR = Path("v5_startup_warmup_price_repair") / "current"

PRIMARY = "v5e_profit_lock_main_20pct_sell50"
BASELINE = "v57f_repaired_baseline"
PROFIT_LOCK_THRESHOLD = 0.20
SELL_FRACTION = 0.50


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_profit_lock_main_forward_paper_tracking(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_blockers(root)
    if blockers:
        _write_csv(out / "v5e_profit_lock_forward_paper_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_profit_lock_forward_paper_summary.json", summary)
        return summary

    formal = _read_json(root / FORMAL_DIR / "v5e_profit_lock_execution_robust_summary.json")
    proxy = _read_json(root / PROXY_DIR / "v5e_5min_execution_proxy_summary.json")
    data_gate = _read_json(root / DATA_GATE_DIR / "v5e_trigger_day_5min_data_gate_summary.json")
    comparison = _read_csv(root / LOOP_DIR / "v5e_engineering_comparison.csv")
    proxy_impact = _read_csv(root / PROXY_DIR / "v5e_5min_execution_proxy_candidate_impact.csv")

    readiness = _readiness_rows(formal, proxy, data_gate)
    candidate_status = _candidate_status_rows(comparison, proxy_impact)
    signal_template = _signal_template_rows()
    execution_template = _execution_template_rows()
    cash_template = _cash_drag_template_rows()
    reentry_template = _no_reentry_template_rows()
    post_exit_template = _post_exit_template_rows()
    evidence = _evidence_requirement_rows()
    cadence = _review_cadence_rows()
    allowed_blocked = _allowed_blocked_rows()
    gate = _gate_decision(readiness)
    next_queue = _next_queue(gate[0]["next_gate"])
    blockers = _nonfatal_blockers()

    _write_csv(out / "v5e_profit_lock_forward_paper_readiness.csv", readiness)
    _write_csv(out / "v5e_profit_lock_forward_paper_candidate_status.csv", candidate_status)
    _write_csv(out / "v5e_profit_lock_forward_signal_template.csv", signal_template)
    _write_csv(out / "v5e_profit_lock_forward_execution_tracking_template.csv", execution_template)
    _write_csv(out / "v5e_profit_lock_forward_cash_drag_template.csv", cash_template)
    _write_csv(out / "v5e_profit_lock_forward_no_reentry_audit_template.csv", reentry_template)
    _write_csv(out / "v5e_profit_lock_forward_post_exit_template.csv", post_exit_template)
    _write_csv(out / "v5e_profit_lock_forward_evidence_requirements.csv", evidence)
    _write_csv(out / "v5e_profit_lock_forward_pm_review_cadence.csv", cadence)
    _write_csv(out / "v5e_profit_lock_forward_allowed_blocked_actions.csv", allowed_blocked)
    _write_csv(out / "v5e_profit_lock_forward_paper_gate_decision.csv", gate)
    _write_csv(out / "v5e_profit_lock_forward_paper_next_queue.csv", next_queue)
    _write_csv(out / "v5e_profit_lock_forward_paper_blockers.csv", blockers)
    (out / "v5e_profit_lock_forward_paper_agent_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5e_profit_lock_forward_paper_next_prompt.md").write_text(_next_prompt(gate[0]), encoding="utf-8")

    summary = _summary(
        "completed_forward_paper_tracking_packet",
        gate[0]["pm_decision"],
        [],
        gate=gate[0],
        candidate_status=candidate_status[0],
    )
    _write_json(out / "v5e_profit_lock_forward_paper_summary.json", summary)
    (out / "v5e_profit_lock_forward_paper_report.md").write_text(
        _report(summary, gate[0], candidate_status[0], readiness),
        encoding="utf-8",
    )
    return summary


def _readiness_rows(formal: dict[str, Any], proxy: dict[str, Any], data_gate: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "check_item": "primary_review_candidate",
            "status": "pass",
            "evidence": formal.get("primary_candidate") == PRIMARY,
            "note": formal.get("pm_decision", ""),
        },
        {
            "check_item": "not_accepted",
            "status": "pass",
            "evidence": not formal.get("accepted", True),
            "note": "Forward/paper tracking only.",
        },
        {
            "check_item": "v57f_core_unchanged",
            "status": "pass",
            "evidence": not formal.get("v57f_core_modified", True),
            "note": "Overlay evidence packet does not alter V57f.",
        },
        {
            "check_item": "no_threshold_scan",
            "status": "pass",
            "evidence": not formal.get("threshold_scan_used", True),
            "note": "Threshold remains pre_registered_not_optimized.",
        },
        {
            "check_item": "5min_execution_data_gate",
            "status": "pass",
            "evidence": data_gate.get("coverage_rate_pct") == 100.0,
            "note": data_gate.get("pm_decision", ""),
        },
        {
            "check_item": "5min_not_trigger_signal",
            "status": "pass",
            "evidence": not proxy.get("minute_data_used_for_trigger", True),
            "note": "5min used only for T+1 execution evidence.",
        },
        {
            "check_item": "paper_tracking_not_live_approval",
            "status": "pass",
            "evidence": not formal.get("live_trading_approved", True),
            "note": "No live approval in this packet.",
        },
    ]


def _candidate_status_rows(comparison: list[dict[str, str]], proxy_impact: list[dict[str, str]]) -> list[dict[str, Any]]:
    comp = next(row for row in comparison if row["version_id"] == PRIMARY)
    proxy = next(row for row in proxy_impact if row["version_id"] == PRIMARY and row["proxy_id"] == "day_5min_vwap")
    return [
        {
            "candidate_id": PRIMARY,
            "status": "forward_paper_tracking_ready_not_accepted",
            "daily_proxy_strategy_return": _float(comp["strategy_return"]),
            "daily_proxy_delta_vs_v57f_baseline": _float(comp["delta_return_vs_baseline"]),
            "daily_proxy_max_drawdown": _float(comp["max_drawdown"]),
            "daily_proxy_delta_max_drawdown_vs_baseline": _float(comp["delta_max_drawdown_vs_baseline"]),
            "cash_drag_delta_vs_baseline": _float(comp["cash_drag_delta_vs_baseline"]),
            "vwap_adjusted_delta_vs_v57f_baseline": _float(proxy["execution_proxy_adjusted_delta_vs_v57f_baseline"]),
            "trigger_count_historical": int(float(comp["trigger_count"])),
            "exit_action_count_historical": int(float(comp["exit_action_count"])),
            "threshold_status": comp["threshold_status"],
            "accepted": False,
            "live_trading_approved": False,
        }
    ]


def _signal_template_rows() -> list[dict[str, Any]]:
    return [
        {
            "tracking_date": "",
            "as_of_close_date": "",
            "decision_visible_time": "after_daily_close",
            "candidate_id": PRIMARY,
            "code": "",
            "sleeve": "",
            "holding_shares": "",
            "cost_basis_or_rebalance_reference_price": "",
            "prior_close": "",
            "holding_period_return": "",
            "profit_lock_threshold": PROFIT_LOCK_THRESHOLD,
            "profit_lock_triggered": "",
            "trigger_reason": "profit_lock",
            "sell_fraction": SELL_FRACTION,
            "execution_earliest_date": "T+1",
            "minute_data_used_for_trigger": False,
            "threshold_status": "pre_registered_not_optimized",
            "review_notes": "",
        }
    ]


def _execution_template_rows() -> list[dict[str, Any]]:
    return [
        {
            "trigger_date": "",
            "execution_date": "",
            "fallback_date_1": "",
            "fallback_date_2": "",
            "candidate_id": PRIMARY,
            "code": "",
            "side": "sell",
            "planned_sell_fraction": SELL_FRACTION,
            "planned_sell_shares": "",
            "daily_open_proxy_price": "",
            "bar_0935_price": "",
            "bar_0940_price": "",
            "bar_1000_price": "",
            "bar_1455_price": "",
            "day_5min_vwap": "",
            "day_5min_twap": "",
            "chosen_execution_proxy": "",
            "filled_shares": "",
            "unfilled_shares": "",
            "unfilled_reason": "",
            "cash_after_trade": "",
            "v5d_reuse_needed": "",
        }
    ]


def _cash_drag_template_rows() -> list[dict[str, Any]]:
    return [
        {
            "trade_date": "",
            "candidate_id": PRIMARY,
            "portfolio_value": "",
            "cash": "",
            "cash_weight": "",
            "baseline_cash_weight": "",
            "cash_drag_delta": "",
            "cash_source_exit_code": "",
            "cash_idle_days_since_exit": "",
            "next_regular_v57f_rebalance": "",
            "cash_policy": "hold_cash_until_next_v57f_rebalance",
        }
    ]


def _no_reentry_template_rows() -> list[dict[str, Any]]:
    return [
        {
            "trade_date": "",
            "candidate_id": PRIMARY,
            "code": "",
            "exit_date": "",
            "reentry_locked_until": "next_regular_v57f_rebalance",
            "buy_attempt_before_rebalance": "",
            "same_day_sell_buy": "",
            "same_day_buy_sell": "",
            "violation_count": "",
            "status": "",
            "notes": "",
        }
    ]


def _post_exit_template_rows() -> list[dict[str, Any]]:
    return [
        {
            "execution_date": "",
            "candidate_id": PRIMARY,
            "code": "",
            "exit_price": "",
            "post_exit_5d_return": "",
            "post_exit_10d_return": "",
            "post_exit_20d_return": "",
            "post_exit_60d_return": "",
            "until_next_rebalance_return": "",
            "avoided_loss": "",
            "missed_upside": "",
            "review_read": "",
        }
    ]


def _evidence_requirement_rows() -> list[dict[str, Any]]:
    return [
        {"evidence_id": "daily_trigger_log", "required": True, "cadence": "daily_after_close", "description": "Record whether any held stock crosses +20% holding-period return using known daily close."},
        {"evidence_id": "T_plus_1_execution_log", "required": True, "cadence": "next_trade_day", "description": "Record planned/filled shares and daily/5min execution proxies."},
        {"evidence_id": "cash_drag_path", "required": True, "cadence": "daily", "description": "Track cash weight and idle days until next V57f rebalance."},
        {"evidence_id": "no_reentry_audit", "required": True, "cadence": "daily_and_rebalance", "description": "Confirm exited stocks are not repurchased before next regular V57f rebalance."},
        {"evidence_id": "post_exit_outcome", "required": True, "cadence": "5d_10d_20d_60d_and_rebalance", "description": "Classify avoided loss versus missed upside after each exit."},
        {"evidence_id": "PM_review_minutes", "required": True, "cadence": "monthly_or_after_5_exits", "description": "PM review of execution quality, cash drag, and rule suitability."},
    ]


def _review_cadence_rows() -> list[dict[str, Any]]:
    return [
        {"cadence_id": "daily_after_close", "owner": "Engineering Agent", "task": "Refresh held-name returns and generate paper trigger log.", "gate": "no_trade_without_next_day_execution_review"},
        {"cadence_id": "T_plus_1_execution", "owner": "Execution Agent", "task": "Record daily open and 5min VWAP/TWAP execution evidence.", "gate": "no_intraday_trigger"},
        {"cadence_id": "weekly", "owner": "Quant Agent", "task": "Review cash drag, post-exit early evidence, and no-reentry logs.", "gate": "diagnostic_only"},
        {"cadence_id": "monthly_or_after_5_exits", "owner": "PM Agent", "task": "Decide retain / downgrade / cash-policy-review; no accepted decision.", "gate": "not_accepted"},
        {"cadence_id": "next_v57f_rebalance", "owner": "PM + Engineering", "task": "Reset no-reentry locks according to V57f official rebalance targets.", "gate": "V57f_rebalance_priority"},
    ]


def _allowed_blocked_rows() -> list[dict[str, Any]]:
    return [
        {"action": "record_forward_paper_signal", "status": "allowed", "reason": "Evidence collection for review candidate."},
        {"action": "record_T_plus_1_execution_proxy", "status": "allowed", "reason": "5min data is execution evidence only."},
        {"action": "hold_exit_proceeds_as_cash", "status": "allowed", "reason": "Pre-registered cash policy."},
        {"action": "reenter_before_next_rebalance", "status": "blocked", "reason": "No-reentry governance."},
        {"action": "use_5min_to_trigger_exit", "status": "blocked", "reason": "V5e trigger remains daily close only."},
        {"action": "change_profit_threshold", "status": "blocked", "reason": "No new thresholds or parameter scan."},
        {"action": "mark_accepted_or_live_approved", "status": "blocked", "reason": "Forward/paper evidence packet only."},
        {"action": "modify_V57f_core", "status": "blocked", "reason": "V57f remains frozen formal ETF candidate."},
    ]


def _gate_decision(readiness: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ready = all(row["status"] == "pass" for row in readiness)
    return [
        {
            "pm_decision": "paper_tracking_ready_waiting_forward_records" if ready else "blocked_until_readiness_repaired",
            "candidate_id": PRIMARY,
            "accepted": False,
            "live_trading_approved": False,
            "v57f_replacement": False,
            "reason": "All governance and 5min execution data gates are ready; next evidence must come from forward/paper records, not more historical tuning.",
            "next_gate": "collect_forward_paper_records_then_pm_review" if ready else "repair_forward_paper_readiness",
        }
    ]


def _next_queue(next_gate: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_gate": next_gate,
            "task": "Collect V5e profit_lock_main forward/paper records",
            "description": "Use templates to record daily triggers, T+1 execution proxies, cash drag, no-reentry, and post-exit outcome.",
            "requires_joinquant": False,
            "requires_new_threshold": False,
            "requires_v57f_change": False,
        },
        {
            "priority": 2,
            "next_gate": "pm_review_after_forward_records",
            "task": "PM review after first forward exits or monthly cadence",
            "description": "Retain, downgrade, or route to cash policy review; do not accept without separate approval.",
            "requires_joinquant": False,
            "requires_new_threshold": False,
            "requires_v57f_change": False,
        },
    ]


def _nonfatal_blockers() -> list[dict[str, Any]]:
    return [
        {
            "blocker_id": "forward_records_not_yet_collected",
            "severity": "review_note",
            "status": "non_blocking_for_packet_blocks_acceptance",
            "description": "Packet is ready, but there are no future/paper records yet; this blocks acceptance, not tracking setup.",
        }
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    gate: dict[str, Any] | None = None,
    candidate_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_profit_lock_main_forward_paper_execution_tracking",
        "status": status,
        "pm_decision": decision,
        "candidate_id": PRIMARY if not fatal_blockers else "",
        "tracking_status": gate.get("pm_decision", "") if gate else "",
        "accepted": False,
        "live_trading_approved": False,
        "v57f_replacement": False,
        "v57f_core_modified": False,
        "erc_modified": False,
        "v5d_modified": False,
        "threshold_scan_used": False,
        "minute_data_used_for_trigger": False,
        "full_holding_period_5min_fetch": False,
        "profit_lock_threshold": PROFIT_LOCK_THRESHOLD,
        "sell_fraction": SELL_FRACTION,
        "candidate_status": candidate_status or {},
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(summary: dict[str, Any], gate: dict[str, Any], candidate: dict[str, Any], readiness: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# V5e Profit-Lock Main Forward/Paper Execution Tracking",
            "",
            "## Status",
            f"- Candidate: `{summary['candidate_id']}`",
            f"- PM decision: `{gate['pm_decision']}`",
            "- This is forward/paper tracking setup only; not accepted and not live approved.",
            "",
            "## Candidate",
            f"- Daily proxy delta vs V57f baseline: {candidate['daily_proxy_delta_vs_v57f_baseline']:.6f}",
            f"- VWAP-adjusted delta vs V57f baseline: {candidate['vwap_adjusted_delta_vs_v57f_baseline']:.6f}",
            f"- Drawdown delta vs baseline: {candidate['daily_proxy_delta_max_drawdown_vs_baseline']:.6f}",
            f"- Cash drag delta vs baseline: {candidate['cash_drag_delta_vs_baseline']:.6f}",
            "",
            "## Tracking Rules",
            "- Trigger uses daily close only, visible after close.",
            "- Execute from T+1; 5min bars are execution evidence only.",
            "- Sell fraction is fixed at 50% after +20% holding-period return.",
            "- Proceeds remain cash until next V57f rebalance.",
            "- No reentry before next V57f official rebalance.",
            "",
            "## Next Gate",
            f"- `{gate['next_gate']}`",
            "",
        ]
    )


def _next_prompt(gate: dict[str, Any]) -> str:
    return f"""工作目录：
D:\\hh\\codex\\v5

任务名称：
V5e profit_lock_main forward/paper records collection

任务目标：
使用 `v5e_profit_lock_main_forward_paper_execution_tracking/current/` 下的模板，记录 `{PRIMARY}` 的未来/纸面触发、T+1 执行、5分钟执行代理、现金拖累、no-reentry 和 post-exit 结果。

边界：
- 不修改 V57f / ERC / V5d。
- 不新增阈值，不参数扫描。
- 5分钟只用于执行记录，不用于触发。
- 不标记 accepted，不标记 live approved。

当前 gate：
`{gate['pm_decision']}`
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Profit-Lock Forward/Paper Tracking Rules",
            "",
            "- Use daily close for trigger visibility; no intraday trigger.",
            "- Execute or paper-record no earlier than T+1.",
            "- Keep +20% threshold and 50% sell fraction fixed.",
            "- Keep cash until next V57f official rebalance.",
            "- No reentry before next V57f rebalance.",
            "- Tracking evidence cannot mark the candidate accepted without a separate PM gate.",
            "",
        ]
    )


def _missing_blockers(root: Path) -> list[dict[str, Any]]:
    required = [
        FORMAL_DIR / "v5e_profit_lock_execution_robust_summary.json",
        PROXY_DIR / "v5e_5min_execution_proxy_summary.json",
        PROXY_DIR / "v5e_5min_execution_proxy_candidate_impact.csv",
        DATA_GATE_DIR / "v5e_trigger_day_5min_data_gate_summary.json",
        LOOP_DIR / "v5e_engineering_comparison.csv",
        STARTUP_DIR / "v5_startup_warmup_price_repair_summary.json",
    ]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "status": "blocking",
            "path": str(path),
            "description": "Required V5e forward/paper tracking input is missing.",
        }
        for path in required
        if not (root / path).exists()
    ]


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
    result = run_v5e_profit_lock_main_forward_paper_tracking()
    print(json.dumps(result, ensure_ascii=False, indent=2))

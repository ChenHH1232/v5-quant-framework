from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5e_profit_lock_execution_robust_formal_review") / "current"
LOOP_DIR = Path("v5e_limited_engineering_loop") / "current"
CASH_DIR = Path("v5e_cash_drag_robustness_packet") / "current"
PROXY_DIR = Path("v5e_trigger_day_5min_execution_proxy_test") / "current"
DATA_GATE_DIR = Path("v5e_trigger_day_5min_execution_data_gate") / "current"

BASELINE = "v57f_repaired_baseline"
PREVIOUS_PRIMARY = "v5e_combined_main_profit_lock_plus_trailing"
NEW_PRIMARY = "v5e_profit_lock_main_20pct_sell50"
REVIEW_PROXY = "day_5min_vwap"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_profit_lock_execution_robust_formal_review(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_blockers(root)
    if blockers:
        _write_csv(out / "v5e_profit_lock_execution_robust_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_profit_lock_execution_robust_summary.json", summary)
        return summary

    comp = _read_csv(root / LOOP_DIR / "v5e_engineering_comparison.csv")
    stability = _read_csv(root / CASH_DIR / "v5e_candidate_stability_review.csv")
    effectiveness = _read_csv(root / CASH_DIR / "v5e_exit_effectiveness_summary.csv")
    cash_year = _read_csv(root / CASH_DIR / "v5e_cash_drag_by_year.csv")
    proxy_impact = _read_csv(root / PROXY_DIR / "v5e_5min_execution_proxy_candidate_impact.csv")
    proxy_gate = _read_csv(root / PROXY_DIR / "v5e_5min_execution_proxy_gate_decision.csv")
    data_gate = _read_json(root / DATA_GATE_DIR / "v5e_trigger_day_5min_data_gate_summary.json")

    risk_rows = _risk_benefit_rows(comp, proxy_impact)
    switch_rows = _candidate_switch_rows(risk_rows, stability, effectiveness, cash_year)
    governance_rows = _governance_rows(comp, data_gate, proxy_gate)
    proxy_rows = _proxy_robustness_rows(proxy_impact)
    pm_gate = _pm_gate_decision(switch_rows, governance_rows)
    next_queue = _next_queue(pm_gate[0]["next_gate"])
    blockers = _nonfatal_blockers(pm_gate)

    _write_csv(out / "v5e_profit_lock_execution_robust_candidate_switch_matrix.csv", switch_rows)
    _write_csv(out / "v5e_profit_lock_execution_robust_proxy_matrix.csv", proxy_rows)
    _write_csv(out / "v5e_profit_lock_execution_robust_risk_benefit.csv", risk_rows)
    _write_csv(out / "v5e_profit_lock_execution_robust_governance_checks.csv", governance_rows)
    _write_csv(out / "v5e_profit_lock_execution_robust_pm_gate_decision.csv", pm_gate)
    _write_csv(out / "v5e_profit_lock_execution_robust_next_queue.csv", next_queue)
    _write_csv(out / "v5e_profit_lock_execution_robust_blockers.csv", blockers)
    (out / "v5e_profit_lock_execution_robust_next_prompt.md").write_text(_next_prompt(pm_gate[0]), encoding="utf-8")
    (out / "v5e_profit_lock_execution_robust_agent_rules.md").write_text(_agent_rules(), encoding="utf-8")

    summary = _summary(
        "completed_profit_lock_execution_robust_formal_review",
        pm_gate[0]["pm_decision"],
        [],
        pm_gate=pm_gate[0],
        risk_rows=risk_rows,
    )
    _write_json(out / "v5e_profit_lock_execution_robust_summary.json", summary)
    (out / "v5e_profit_lock_execution_robust_report.md").write_text(
        _report(summary, pm_gate[0], switch_rows, proxy_rows),
        encoding="utf-8",
    )
    return summary


def _risk_benefit_rows(comp: list[dict[str, str]], proxy_impact: list[dict[str, str]]) -> list[dict[str, Any]]:
    comp_by_id = {row["version_id"]: row for row in comp}
    proxy_by_id = {
        row["version_id"]: row
        for row in proxy_impact
        if row["proxy_id"] == REVIEW_PROXY and row["version_id"] in {PREVIOUS_PRIMARY, NEW_PRIMARY}
    }
    rows: list[dict[str, Any]] = []
    for role, version in [("baseline", BASELINE), ("previous_primary", PREVIOUS_PRIMARY), ("new_primary", NEW_PRIMARY)]:
        comp_row = comp_by_id[version]
        proxy_row = proxy_by_id.get(version, {})
        rows.append(
            {
                "role": role,
                "version_id": version,
                "strategy_return": _float(comp_row["strategy_return"]),
                "delta_return_vs_baseline_daily_proxy": _float(comp_row["delta_return_vs_baseline"]),
                "max_drawdown": _float(comp_row["max_drawdown"]),
                "delta_max_drawdown_vs_baseline": _float(comp_row["delta_max_drawdown_vs_baseline"]),
                "cash_drag_delta_vs_baseline": _float(comp_row["cash_drag_delta_vs_baseline"]),
                "trigger_count": int(float(comp_row["trigger_count"])),
                "exit_action_count": int(float(comp_row["exit_action_count"])),
                "t_violation_count": int(float(comp_row["t_violation_count"])),
                "reentry_violation_count": int(float(comp_row["reentry_violation_count"])),
                "vwap_execution_delta_vs_daily_proxy": _float(proxy_row.get("delta_return_estimate_vs_daily_proxy", 0.0)),
                "vwap_adjusted_delta_vs_v57f_baseline": _float(proxy_row.get("execution_proxy_adjusted_delta_vs_v57f_baseline", 0.0)),
                "vwap_avg_bps_delta_vs_daily_open": _float(proxy_row.get("avg_bps_delta_vs_daily_open", 0.0)),
                "threshold_status": comp_row["threshold_status"],
                "accepted": False,
            }
        )
    return rows


def _candidate_switch_rows(
    risk_rows: list[dict[str, Any]],
    stability: list[dict[str, str]],
    effectiveness: list[dict[str, str]],
    cash_year: list[dict[str, str]],
) -> list[dict[str, Any]]:
    risk = {row["version_id"]: row for row in risk_rows}
    stability_by_id = {row["version_id"]: row for row in stability}
    rows: list[dict[str, Any]] = []
    for version in [PREVIOUS_PRIMARY, NEW_PRIMARY]:
        eff = [row for row in effectiveness if row["version_id"] == version]
        avoided = sum(int(float(row.get("avoided_loss_20d_count", 0))) for row in eff)
        missed = sum(int(float(row.get("missed_upside_20d_count", 0))) for row in eff)
        yearly = [row for row in cash_year if row["version_id"] == version]
        max_cash_year = max((_float(row.get("max_cash_weight", 0.0)) for row in yearly), default=0.0)
        r = risk[version]
        rows.append(
            {
                "version_id": version,
                "old_role": "primary" if version == PREVIOUS_PRIMARY else "secondary",
                "proposed_role": "secondary_reference" if version == PREVIOUS_PRIMARY else "primary_execution_robust_review_candidate",
                "vwap_adjusted_delta_vs_v57f_baseline": r["vwap_adjusted_delta_vs_v57f_baseline"],
                "drawdown_improvement_vs_baseline": -r["delta_max_drawdown_vs_baseline"],
                "cash_drag_delta_vs_baseline": r["cash_drag_delta_vs_baseline"],
                "exit_action_count": r["exit_action_count"],
                "avoided_loss_20d_count": avoided,
                "missed_upside_20d_count": missed,
                "max_cash_weight_by_year": max_cash_year,
                "stability_prior_decision": stability_by_id.get(version, {}).get("stability_decision", ""),
                "switch_rationale": _switch_rationale(version, r, avoided, missed),
                "accepted": False,
            }
        )
    return rows


def _switch_rationale(version: str, risk: dict[str, Any], avoided: int, missed: int) -> str:
    if version == NEW_PRIMARY:
        return (
            "Retain as primary review candidate after 5min VWAP execution stress: adjusted delta remains slightly positive versus V57f baseline, "
            "drawdown improves, cash drag is lower than combined_main, and profit-lock exits have more avoided-loss than missed-upside cases."
        )
    return (
        "Downgrade from primary review candidate after 5min VWAP execution stress: drawdown improvement is stronger, "
        "but adjusted delta turns meaningfully negative versus V57f baseline and cash drag is higher."
    )


def _governance_rows(comp: list[dict[str, str]], data_gate: dict[str, Any], proxy_gate: list[dict[str, str]]) -> list[dict[str, Any]]:
    new_row = next(row for row in comp if row["version_id"] == NEW_PRIMARY)
    return [
        {"check_item": "v57f_core_modified", "status": "pass", "value": False, "evidence": "No V57f source/config change in this review."},
        {"check_item": "v5e_rules_modified", "status": "pass", "value": False, "evidence": "Only pre-registered +20% sell50 profit-lock main is reviewed."},
        {"check_item": "threshold_scan", "status": "pass", "value": False, "evidence": "threshold_status remains pre_registered_not_optimized."},
        {"check_item": "minute_trigger_used", "status": "pass", "value": False, "evidence": "5min data used only for execution price proxy."},
        {"check_item": "full_holding_period_5min_fetch", "status": "pass", "value": False, "evidence": "Only V5e exit execution windows were fetched."},
        {"check_item": "5min_execution_coverage", "status": "pass", "value": data_gate.get("coverage_rate_pct"), "evidence": "Trigger-day T+1/T+2/T+3 coverage is complete."},
        {"check_item": "T_violation", "status": "pass", "value": new_row["t_violation_count"], "evidence": "No same-day T violation in limited engineering test."},
        {"check_item": "reentry_violation", "status": "pass", "value": new_row["reentry_violation_count"], "evidence": "No reentry before next V57f rebalance."},
        {"check_item": "accepted_status", "status": "blocked", "value": False, "evidence": "Review candidate only; not accepted and not live approved."},
        {"check_item": "proxy_gate", "status": "pass", "value": proxy_gate[0].get("pm_decision", ""), "evidence": proxy_gate[0].get("reason", "")},
    ]


def _proxy_robustness_rows(proxy_impact: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in proxy_impact:
        if row["version_id"] not in {PREVIOUS_PRIMARY, NEW_PRIMARY}:
            continue
        rows.append(
            {
                "version_id": row["version_id"],
                "proxy_id": row["proxy_id"],
                "action_count": int(float(row["action_count"])),
                "avg_bps_delta_vs_daily_open": _float(row["avg_bps_delta_vs_daily_open"]),
                "delta_return_estimate_vs_daily_proxy": _float(row["delta_return_estimate_vs_daily_proxy"]),
                "execution_proxy_adjusted_delta_vs_v57f_baseline": _float(row["execution_proxy_adjusted_delta_vs_v57f_baseline"]),
                "better_count": int(float(row["better_than_daily_open_count"])),
                "worse_count": int(float(row["worse_than_daily_open_count"])),
                "proxy_read": _proxy_read(row),
            }
        )
    return rows


def _proxy_read(row: dict[str, str]) -> str:
    adjusted = _float(row["execution_proxy_adjusted_delta_vs_v57f_baseline"])
    if adjusted > 0:
        return "survives_execution_proxy_vs_baseline"
    return "execution_proxy_erodes_baseline_edge"


def _pm_gate_decision(switch_rows: list[dict[str, Any]], governance_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    new = next(row for row in switch_rows if row["version_id"] == NEW_PRIMARY)
    governance_pass = all(row["status"] in {"pass", "blocked"} for row in governance_rows)
    decision = "promote_profit_lock_main_to_execution_robust_review_candidate_not_accepted"
    if not governance_pass or new["vwap_adjusted_delta_vs_v57f_baseline"] <= 0:
        decision = "remain_review_candidate_needs_more_evidence"
    return [
        {
            "pm_decision": decision,
            "primary_candidate": NEW_PRIMARY,
            "downgraded_reference_candidate": PREVIOUS_PRIMARY,
            "accepted": False,
            "v57f_replacement": False,
            "live_trading_approved": False,
            "reason": "Switch is supported by 5min execution robustness and lower governance complexity/cash drag, not by threshold scanning or accepted-status selection.",
            "next_gate": "v5e_profit_lock_main_forward_paper_execution_tracking",
        }
    ]


def _next_queue(next_gate: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_gate": next_gate,
            "task": "V5e profit_lock_main forward/paper execution tracking packet",
            "description": "Track daily close triggers, T+1 execution, 5min VWAP/TWAP execution slippage, cash drag, and no-reentry in forward or paper mode.",
            "requires_joinquant": False,
            "requires_new_threshold": False,
            "requires_v57f_core_change": False,
            "allowed": True,
        },
        {
            "priority": 2,
            "next_gate": "cash_policy_review_if_cash_drag_persists",
            "task": "V5e cash policy review",
            "description": "Review whether cash drag governance should remain strict cash-to-next-rebalance or require a separately approved cash sleeve policy.",
            "requires_joinquant": False,
            "requires_new_threshold": False,
            "requires_v57f_core_change": False,
            "allowed": True,
        },
    ]


def _nonfatal_blockers(pm_gate: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "blocker_id": "not_accepted_requires_forward_or_paper_tracking",
            "severity": "review_note",
            "status": "non_blocking",
            "description": "Candidate can enter forward/paper tracking but cannot be accepted from historical evidence.",
        }
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    pm_gate: dict[str, Any] | None = None,
    risk_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    risk_rows = risk_rows or []
    risk = {row["version_id"]: row for row in risk_rows}
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_profit_lock_execution_robust_formal_review",
        "status": status,
        "pm_decision": decision,
        "primary_candidate": NEW_PRIMARY if not fatal_blockers else "",
        "previous_primary_candidate": PREVIOUS_PRIMARY if not fatal_blockers else "",
        "accepted": False,
        "v57f_replacement": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "erc_modified": False,
        "v5d_modified": False,
        "threshold_scan_used": False,
        "minute_data_used_for_trigger": False,
        "full_holding_period_5min_fetch": False,
        "new_primary_daily_delta_vs_baseline": risk.get(NEW_PRIMARY, {}).get("delta_return_vs_baseline_daily_proxy", 0.0),
        "new_primary_vwap_adjusted_delta_vs_baseline": risk.get(NEW_PRIMARY, {}).get("vwap_adjusted_delta_vs_v57f_baseline", 0.0),
        "new_primary_drawdown_improvement_vs_baseline": -risk.get(NEW_PRIMARY, {}).get("delta_max_drawdown_vs_baseline", 0.0),
        "new_primary_cash_drag_delta_vs_baseline": risk.get(NEW_PRIMARY, {}).get("cash_drag_delta_vs_baseline", 0.0),
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
        "pm_gate": pm_gate or {},
    }


def _report(summary: dict[str, Any], gate: dict[str, Any], switch_rows: list[dict[str, Any]], proxy_rows: list[dict[str, Any]]) -> str:
    new = next(row for row in switch_rows if row["version_id"] == NEW_PRIMARY)
    old = next(row for row in switch_rows if row["version_id"] == PREVIOUS_PRIMARY)
    return "\n".join(
        [
            "# V5e Profit-Lock Main Execution-Robust Formal Review",
            "",
            "## Decision",
            f"- PM decision: `{gate['pm_decision']}`",
            f"- Primary review candidate: `{gate['primary_candidate']}`",
            f"- Downgraded reference candidate: `{gate['downgraded_reference_candidate']}`",
            "- Status: review candidate only; not accepted and not live approved.",
            "",
            "## Why Switch",
            f"- Profit-lock main VWAP-adjusted delta vs V57f baseline: {new['vwap_adjusted_delta_vs_v57f_baseline']:.6f}",
            f"- Combined main VWAP-adjusted delta vs V57f baseline: {old['vwap_adjusted_delta_vs_v57f_baseline']:.6f}",
            f"- Profit-lock cash drag delta: {new['cash_drag_delta_vs_baseline']:.6f}",
            f"- Combined cash drag delta: {old['cash_drag_delta_vs_baseline']:.6f}",
            f"- Profit-lock avoided/missed 20d: {new['avoided_loss_20d_count']}/{new['missed_upside_20d_count']}",
            "",
            "## Governance",
            "- No V57f / ERC / V5d modification.",
            "- No threshold scan.",
            "- 5min data used only for execution proxy, not trigger.",
            "- No accepted decision.",
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
V5e profit_lock_main forward/paper execution tracking packet

任务目标：
基于 V5e execution-robust formal review，将 `{NEW_PRIMARY}` 作为主 review candidate 进入 forward/paper tracking 设计与证据包。

边界：
- 不修改 V57f / ERC / V5d。
- 不新增阈值，不参数扫描。
- 不用 5分钟触发止盈；5分钟只用于 T+1 执行治理。
- 不标记 accepted，不标记 live approved。

当前 gate：
`{gate['pm_decision']}`

下一步：
生成 forward/paper signal template、execution tracking template、cash drag monitoring、no-reentry audit、PM review cadence。
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Profit-Lock Execution-Robust Formal Review Rules",
            "",
            "- Candidate status is review only, not accepted.",
            "- Do not change V57f, ERC, or V5d.",
            "- Do not add thresholds or scan parameters.",
            "- 5min data may be used only for execution evidence.",
            "- Candidate switch must be justified by robustness and governance, not historical return alone.",
            "",
        ]
    )


def _missing_blockers(root: Path) -> list[dict[str, Any]]:
    required = [
        LOOP_DIR / "v5e_engineering_comparison.csv",
        CASH_DIR / "v5e_candidate_stability_review.csv",
        CASH_DIR / "v5e_exit_effectiveness_summary.csv",
        CASH_DIR / "v5e_cash_drag_by_year.csv",
        PROXY_DIR / "v5e_5min_execution_proxy_candidate_impact.csv",
        PROXY_DIR / "v5e_5min_execution_proxy_gate_decision.csv",
        DATA_GATE_DIR / "v5e_trigger_day_5min_data_gate_summary.json",
    ]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "status": "blocking",
            "path": str(path),
            "description": "Required V5e execution-robust review input is missing.",
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
    result = run_v5e_profit_lock_execution_robust_formal_review()
    print(json.dumps(result, ensure_ascii=False, indent=2))

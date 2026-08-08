from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5c_p4_state_forward_observation_packet") / "current"
P2_DIR = Path("v5c_p2_valuation_and_crowding_state_panel") / "current"
P3_DIR = Path("v5c_p3_state_governance_quant_spec") / "current"

P2_VALUATION = P2_DIR / "v5c_p2_valuation_state_panel.csv"
P2_CROWDING = P2_DIR / "v5c_p2_crowding_state_panel.csv"
P2_SLEEVE_OVERHEAT = P2_DIR / "v5c_p2_sleeve_overheat_state_panel.csv"
P2_BROAD_TREND = P2_DIR / "v5c_p2_broad_index_trend_state_panel.csv"
P3_SUMMARY = P3_DIR / "v5c_p3_state_governance_summary.json"
P3_PM_DECISION = P3_DIR / "v5c_p3_pm_gate_decision.csv"
P3_SCHEMA = P3_DIR / "v5c_p3_forward_observation_schema.csv"
P3_BLOCKED = P3_DIR / "v5c_p3_blocked_actions.csv"
P3_BOUNDARY = P3_DIR / "v5c_p3_state_action_boundary_matrix.csv"


def run_v5c_p4_state_forward_observation_packet(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5c_p4_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "p4_blocked_missing_required_input", blockers)
        _write_json(out / "v5c_p4_state_forward_observation_summary.json", summary)
        return summary

    p3_summary = _read_json(root / P3_SUMMARY)
    p3_decision = _read_csv(root / P3_PM_DECISION)[0]
    p3_schema = _read_csv(root / P3_SCHEMA)
    p3_blocked = _read_csv(root / P3_BLOCKED)
    p3_boundary = _read_csv(root / P3_BOUNDARY)
    valuation = _read_csv(root / P2_VALUATION)
    crowding = _read_csv(root / P2_CROWDING)
    sleeve = _read_csv(root / P2_SLEEVE_OVERHEAT)
    broad = _read_csv(root / P2_BROAD_TREND)

    dependency = _dependency_audit(p3_summary, p3_decision, p3_boundary)
    seed_log = _historical_seed_observation_log(valuation, crowding, sleeve, broad)
    watchlist = [row for row in seed_log if row["pm_review_required"] == "True"]
    pm_queue = _pm_review_queue(watchlist)
    template = _forward_observation_template(p3_schema)
    governance = _observation_governance_rules()
    blockers_out = _p4_blockers(dependency, p3_decision)
    decision = _pm_decision(blockers_out)
    next_queue = _next_queue(decision[0])

    _write_csv(out / "v5c_p4_input_dependency_audit.csv", dependency)
    _write_csv(out / "v5c_p4_forward_observation_template.csv", template)
    _write_csv(out / "v5c_p4_historical_seed_observation_log.csv", seed_log)
    _write_csv(out / "v5c_p4_watchlist_seed.csv", watchlist)
    _write_csv(out / "v5c_p4_pm_review_queue.csv", pm_queue)
    _write_csv(out / "v5c_p4_observation_governance_rules.csv", governance)
    _write_csv(out / "v5c_p4_blocked_actions.csv", p3_blocked)
    _write_csv(out / "v5c_p4_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_p4_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5c_p4_blockers.csv", blockers_out)
    (out / "v5c_p4_state_forward_observation_report.md").write_text(
        _report(seed_log, watchlist, decision, next_queue), encoding="utf-8"
    )
    (out / "v5c_p4_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    summary = _summary(
        "completed_p4_state_forward_observation_packet",
        decision[0]["pm_gate_decision"],
        blockers_out,
        p3_dependency_pass=decision[0]["p4_pass"] == "True",
        seed_observation_rows=len(seed_log),
        watchlist_seed_rows=len(watchlist),
        pm_review_queue_rows=len(pm_queue),
        blocked_action_count=len(p3_blocked),
    )
    _write_json(out / "v5c_p4_state_forward_observation_summary.json", summary)
    return summary


def _dependency_audit(
    p3_summary: dict[str, Any],
    p3_decision: dict[str, str],
    p3_boundary: list[dict[str, str]],
) -> list[dict[str, Any]]:
    return [
        {
            "dependency_id": "p3_summary",
            "status": "pass" if p3_summary.get("fatal_blocker_count") == 0 else "fail",
            "observed": f"fatal_blocker_count={p3_summary.get('fatal_blocker_count')}",
            "required_for_p4": True,
        },
        {
            "dependency_id": "p3_pm_gate",
            "status": "pass" if p3_decision.get("admit_forward_observation") == "True" else "fail",
            "observed": p3_decision.get("pm_gate_decision", ""),
            "required_for_p4": True,
        },
        {
            "dependency_id": "p3_boundary_no_trade",
            "status": "pass"
            if all(row.get("trade_order_allowed") == "False" and row.get("weight_change_allowed") == "False" for row in p3_boundary)
            else "fail",
            "observed": f"boundary_rows={len(p3_boundary)}",
            "required_for_p4": True,
        },
    ]


def _historical_seed_observation_log(
    valuation: list[dict[str, str]],
    crowding: list[dict[str, str]],
    sleeve: list[dict[str, str]],
    broad: list[dict[str, str]],
) -> list[dict[str, Any]]:
    crowding_by_key = {(row["trade_date"], row["code"]): row for row in crowding}
    sleeve_by_key = {(row["trade_date"], row["sleeve_id"]): row for row in sleeve}
    broad_by_date = {row["rebalance_date"]: row for row in broad}
    out = []
    for idx, row in enumerate(valuation, start=1):
        key = (row["trade_date"], row["code"])
        sleeve_key = (row["trade_date"], row["sleeve_id"])
        c = crowding_by_key.get(key, {})
        s = sleeve_by_key.get(sleeve_key, {})
        b = broad_by_date.get(row["trade_date"], {})
        states = [row.get("valuation_state", ""), c.get("crowding_state", ""), s.get("sleeve_overheat_state", ""), b.get("broad_trend_state", "")]
        review_required = _review_required(states)
        out.append(
            {
                "observation_id": f"p4_seed_{idx:05d}",
                "observation_date": row["trade_date"],
                "code": row["code"],
                "sleeve_id": row["sleeve_id"],
                "valuation_state": row.get("valuation_state", ""),
                "crowding_state": c.get("crowding_state", ""),
                "sleeve_overheat_state": s.get("sleeve_overheat_state", ""),
                "broad_trend_state": b.get("broad_trend_state", ""),
                "valuation_overheat_score": row.get("valuation_overheat_score", ""),
                "money_percentile_252d": c.get("money_percentile_252d", ""),
                "sleeve_benchmark_return_60d": s.get("sleeve_benchmark_return_60d", ""),
                "state_visible_time": "after_prior_visible_data_loaded_before_pm_review",
                "pm_review_required": str(review_required),
                "pm_review_reason": _review_reason(states),
                "action_taken": "observe_only",
                "trade_impact": "none",
                "accepted": False,
            }
        )
    return out


def _pm_review_queue(watchlist: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in watchlist:
        grouped[(row["observation_date"], row["sleeve_id"], row["sleeve_overheat_state"])].append(row)
    out = []
    for idx, (key, rows) in enumerate(sorted(grouped.items()), start=1):
        date, sleeve, sleeve_state = key
        out.append(
            {
                "review_id": f"p4_review_{idx:04d}",
                "observation_date": date,
                "sleeve_id": sleeve,
                "sleeve_overheat_state": sleeve_state,
                "watch_item_count": len(rows),
                "codes": ";".join(sorted({row["code"] for row in rows})),
                "primary_review_reason": ";".join(sorted({row["pm_review_reason"] for row in rows})),
                "allowed_pm_action": "record_review_note_only",
                "blocked_pm_action": "no_trade_no_reweight_no_cash_action",
                "status": "seed_template_for_future_forward_tracking",
            }
        )
    return out


def _forward_observation_template(schema: list[dict[str, str]]) -> list[dict[str, Any]]:
    template = []
    for row in schema:
        template.append(
            {
                "field_name": row["field_name"],
                "field_type": row["field_type"],
                "required": row["required"],
                "future_tracking_value": "",
                "description": row["description"],
            }
        )
    return template


def _observation_governance_rules() -> list[dict[str, Any]]:
    rules = [
        ("observe_only", "All P4 state observations are tags/review notes only."),
        ("no_trade_impact", "P4 cannot create, suppress, delay, or resize any order."),
        ("no_v57f_change", "V57f universe, sleeve weights, target_count, caps, and cadence remain frozen."),
        ("no_threshold_scan", "P4 cannot tune state thresholds using historical outcomes."),
        ("forward_tracking_only", "Future official V57f/paper rebalance states may be logged after visible data is available."),
    ]
    return [{"rule_id": rule, "required": True, "description": desc} for rule, desc in rules]


def _p4_blockers(dependency: list[dict[str, Any]], p3_decision: dict[str, str]) -> list[dict[str, Any]]:
    blockers = []
    for row in dependency:
        if row["required_for_p4"] == "True" and row["status"] != "pass":
            blockers.append(
                {
                    "blocker_id": row["dependency_id"],
                    "severity": "fatal",
                    "status": "blocking",
                    "observed": row["observed"],
                    "description": "P4 dependency failed.",
                }
            )
    if p3_decision.get("admit_engineering_backtest") != "False" or p3_decision.get("admit_trading_rule") != "False":
        blockers.append(
            {
                "blocker_id": "p3_boundary_not_observe_only",
                "severity": "fatal",
                "status": "blocking",
                "observed": "P3 admitted backtest or trading rule.",
                "description": "P4 requires observe-only governance.",
            }
        )
    return blockers


def _pm_decision(blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    passed = not blockers
    return [
        {
            "pm_gate_decision": "p4_forward_observation_packet_pass_ready_for_future_v57f_rebalance_tracking" if passed else "p4_forward_observation_packet_blocked",
            "p4_pass": str(passed),
            "admit_forward_tracking": str(passed),
            "admit_engineering_backtest": False,
            "admit_trading_rule": False,
            "accepted": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "network_fetch_started": False,
            "joinquant_started": False,
            "next_step": "future_v57f_rebalance_state_tracking" if passed else "repair_p4_dependency",
            "review_notes": "P4 creates an observe-only forward tracking packet; no trading or engineering backtest is admitted.",
        }
    ]


def _next_queue(decision: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_gate": "future_v57f_rebalance_state_tracking",
            "allowed": decision["p4_pass"],
            "scope": "When a future official V57f rebalance signal exists, log P3 state tags and PM notes.",
            "requires_network": "maybe_if_future_data_missing",
            "requires_v57f_change": False,
            "status": "ready_when_future_rebalance_signal_available" if decision["p4_pass"] == "True" else "blocked_until_p4_repair",
        },
        {
            "priority": 2,
            "next_gate": "v5c_overheat_overlay_pm_quant_spec",
            "allowed": "True",
            "scope": "User approved opening the fixed-rule PM/Quant spec; still no backtest until separately admitted.",
            "requires_network": False,
            "requires_v57f_change": False,
            "status": "approved_for_spec_only",
        },
    ]


def _summary(
    status: str,
    decision: str,
    blockers: list[dict[str, Any]],
    p3_dependency_pass: bool = False,
    seed_observation_rows: int = 0,
    watchlist_seed_rows: int = 0,
    pm_review_queue_rows: int = 0,
    blocked_action_count: int = 0,
) -> dict[str, Any]:
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5c_p4_state_forward_observation_packet",
        "status": status,
        "pm_gate_decision": decision,
        "p3_dependency_pass": p3_dependency_pass,
        "seed_observation_rows": seed_observation_rows,
        "watchlist_seed_rows": watchlist_seed_rows,
        "pm_review_queue_rows": pm_review_queue_rows,
        "blocked_action_count": blocked_action_count,
        "accepted": False,
        "v57f_core_modified": False,
        "new_strategy_rule_added": False,
        "threshold_scan_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "engineering_backtest_started": False,
        "fatal_blocker_count": len(blockers),
        "fatal_blockers": blockers,
        "outputs": {
            "summary": str(OUT_DIR / "v5c_p4_state_forward_observation_summary.json"),
            "report": str(OUT_DIR / "v5c_p4_state_forward_observation_report.md"),
            "forward_observation_template": str(OUT_DIR / "v5c_p4_forward_observation_template.csv"),
            "watchlist_seed": str(OUT_DIR / "v5c_p4_watchlist_seed.csv"),
            "pm_review_queue": str(OUT_DIR / "v5c_p4_pm_review_queue.csv"),
            "next_queue": str(OUT_DIR / "v5c_p4_next_agent_queue.csv"),
        },
    }


def _report(seed_log: list[dict[str, Any]], watchlist: list[dict[str, Any]], decision: list[dict[str, Any]], next_queue: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# V5c P4 State Forward Observation Packet",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Historical seed observation rows: `{len(seed_log)}`",
            f"- Watchlist seed rows: `{len(watchlist)}`",
            "- Engineering backtest admitted: `False`",
            "- Trading rule admitted: `False`",
            "- Accepted: `False`",
            "",
            "P4 is a forward observation packet. It validates the observation workflow using historical P2 state rows, but it does not run or imply a strategy backtest.",
            "",
            "## Next",
            *[f"- P{row['priority']} `{row['next_gate']}`: {row['status']}" for row in next_queue],
            "",
        ]
    )


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5c P4 State Forward Observation Agent Rules",
            "",
            "1. Use P3 observe-only governance and P2 state panels.",
            "2. Generate forward tracking templates and PM review queues only.",
            "3. Do not run engineering backtests, trigger trades, change weights, scan thresholds, or mark accepted.",
            "4. Future tracking may be filled only when official V57f/paper rebalance data is available and visible.",
            "",
        ]
    )


def _review_required(states: list[str]) -> bool:
    return any(state in {"valuation_overheat_watch", "valuation_price_flow_overheat_watch", "cooldown_or_stress_watch"} for state in states)


def _review_reason(states: list[str]) -> str:
    reasons = []
    if "valuation_overheat_watch" in states:
        reasons.append("valuation_overheat_watch")
    if "valuation_price_flow_overheat_watch" in states:
        reasons.append("sleeve_valuation_price_flow_overheat_watch")
    if "cooldown_or_stress_watch" in states:
        reasons.append("sleeve_cooldown_or_stress_watch")
    return ";".join(reasons) if reasons else "no_review_required"


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [P2_VALUATION, P2_CROWDING, P2_SLEEVE_OVERHEAT, P2_BROAD_TREND, P3_SUMMARY, P3_PM_DECISION, P3_SCHEMA, P3_BLOCKED, P3_BOUNDARY]
    blockers = []
    for rel in required:
        if not (root / rel).exists():
            blockers.append(
                {
                    "blocker_id": f"missing_{rel.name}",
                    "severity": "fatal",
                    "status": "blocking",
                    "path": str(rel),
                    "description": "Required P4 local input is missing.",
                }
            )
    return blockers


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    run_v5c_p4_state_forward_observation_packet()

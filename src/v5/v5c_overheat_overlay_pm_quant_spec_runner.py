from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5c_overheat_overlay_pm_quant_spec") / "current"
P2_DIR = Path("v5c_p2_valuation_and_crowding_state_panel") / "current"
P3_DIR = Path("v5c_p3_state_governance_quant_spec") / "current"
P4_DIR = Path("v5c_p4_state_forward_observation_packet") / "current"

P2_SUMMARY = P2_DIR / "v5c_p2_valuation_crowding_summary.json"
P2_SLEEVE_OVERHEAT = P2_DIR / "v5c_p2_sleeve_overheat_state_panel.csv"
P2_VALUATION = P2_DIR / "v5c_p2_valuation_state_panel.csv"
P2_CROWDING = P2_DIR / "v5c_p2_crowding_state_panel.csv"
P3_SUMMARY = P3_DIR / "v5c_p3_state_governance_summary.json"
P3_BLOCKED = P3_DIR / "v5c_p3_blocked_actions.csv"
P3_BOUNDARY = P3_DIR / "v5c_p3_state_action_boundary_matrix.csv"
P4_SUMMARY = P4_DIR / "v5c_p4_state_forward_observation_summary.json"
P4_WATCHLIST = P4_DIR / "v5c_p4_watchlist_seed.csv"


def run_v5c_overheat_overlay_pm_quant_spec(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5c_overheat_overlay_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "overheat_overlay_spec_blocked_missing_input", blockers)
        _write_json(out / "v5c_overheat_overlay_pm_quant_spec_summary.json", summary)
        return summary

    p2_summary = _read_json(root / P2_SUMMARY)
    p3_summary = _read_json(root / P3_SUMMARY)
    p4_summary = _read_json(root / P4_SUMMARY)
    sleeve = _read_csv(root / P2_SLEEVE_OVERHEAT)
    valuation = _read_csv(root / P2_VALUATION)
    crowding = _read_csv(root / P2_CROWDING)
    p3_blocked = _read_csv(root / P3_BLOCKED)
    p3_boundary = _read_csv(root / P3_BOUNDARY)
    p4_watchlist = _read_csv(root / P4_WATCHLIST)

    dependency = _dependency_audit(p2_summary, p3_summary, p4_summary)
    approval = _approval_scope()
    state_evidence = _state_evidence_summary(sleeve, valuation, crowding, p4_watchlist)
    trigger_mapping = _trigger_state_mapping()
    candidates = _fixed_rule_spec_candidates()
    action_matrix = _allowed_blocked_actions(candidates, p3_blocked)
    pit_contract = _pit_contract_requirements()
    boundary = _v5c_erc_v5e_boundary_matrix()
    readiness = _engineering_readiness_checklist()
    blockers_out = _spec_blockers(dependency, p3_boundary)
    decision = _pm_decision(blockers_out)
    next_queue = _next_queue(decision[0])

    _write_csv(out / "v5c_overheat_overlay_input_dependency_audit.csv", dependency)
    _write_csv(out / "v5c_overheat_overlay_user_approval_scope.csv", approval)
    _write_csv(out / "v5c_overheat_overlay_state_evidence_summary.csv", state_evidence)
    _write_csv(out / "v5c_overheat_overlay_trigger_state_mapping.csv", trigger_mapping)
    _write_csv(out / "v5c_overheat_overlay_fixed_rule_spec_candidates.csv", candidates)
    _write_csv(out / "v5c_overheat_overlay_allowed_blocked_actions.csv", action_matrix)
    _write_csv(out / "v5c_overheat_overlay_pit_contract_requirements.csv", pit_contract)
    _write_csv(out / "v5c_overheat_overlay_v5c_erc_v5e_boundary_matrix.csv", boundary)
    _write_csv(out / "v5c_overheat_overlay_engineering_readiness_checklist.csv", readiness)
    _write_csv(out / "v5c_overheat_overlay_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_overheat_overlay_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5c_overheat_overlay_blockers.csv", blockers_out)
    (out / "v5c_overheat_overlay_pm_quant_spec_report.md").write_text(
        _report(state_evidence, candidates, decision, next_queue), encoding="utf-8"
    )
    (out / "v5c_overheat_overlay_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    summary = _summary(
        "completed_overheat_overlay_pm_quant_spec",
        decision[0]["pm_gate_decision"],
        blockers_out,
        spec_opening_user_approved=True,
        engineering_backtest_started=False,
        candidate_spec_count=len(candidates),
        admitted_spec_only_count=sum(1 for row in candidates if row["pm_admission_status"] in {"admit_to_spec_only", "admit_to_observation_control"}),
        blocked_action_count=sum(1 for row in action_matrix if row["blocked_now"] == "True"),
    )
    _write_json(out / "v5c_overheat_overlay_pm_quant_spec_summary.json", summary)
    return summary


def _dependency_audit(p2_summary: dict[str, Any], p3_summary: dict[str, Any], p4_summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "dependency_id": "p2_state_panel",
            "status": "pass" if p2_summary.get("fatal_blocker_count") == 0 else "fail",
            "observed": f"fatal_blocker_count={p2_summary.get('fatal_blocker_count')}",
            "required_for_spec": True,
        },
        {
            "dependency_id": "p3_state_governance",
            "status": "pass" if p3_summary.get("fatal_blocker_count") == 0 else "fail",
            "observed": p3_summary.get("pm_gate_decision", ""),
            "required_for_spec": True,
        },
        {
            "dependency_id": "p4_forward_observation_packet",
            "status": "pass" if p4_summary.get("fatal_blocker_count") == 0 else "fail",
            "observed": p4_summary.get("pm_gate_decision", ""),
            "required_for_spec": True,
        },
        {
            "dependency_id": "user_approval_to_open_spec",
            "status": "pass",
            "observed": "User approved v5c_overheat_overlay_pm_quant_spec opening in current queue message.",
            "required_for_spec": True,
        },
    ]


def _approval_scope() -> list[dict[str, Any]]:
    return [
        {
            "approval_id": "user_approved_spec_opening",
            "approved": True,
            "approved_scope": "write_fixed_rule_pm_quant_spec",
            "not_approved_scope": "engineering_backtest; live_trading; accepted_status; V57f_core_change; threshold_scan",
            "approval_interpretation": "Approval opens the spec gate only. Limited engineering needs a separate explicit approval.",
        }
    ]


def _state_evidence_summary(
    sleeve: list[dict[str, str]],
    valuation: list[dict[str, str]],
    crowding: list[dict[str, str]],
    p4_watchlist: list[dict[str, str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(_count_rows("sleeve_overheat_state", sleeve, "sleeve_overheat_state"))
    rows.extend(_count_rows("valuation_state", valuation, "valuation_state"))
    rows.extend(_count_rows("crowding_state", crowding, "crowding_state"))
    rows.append(
        {
            "evidence_scope": "p4_watchlist",
            "state_id": "pm_review_required",
            "count": len(p4_watchlist),
            "share": "",
            "interpretation": "Historical seed queue validates observation workflow only; not a backtest result.",
        }
    )
    return rows


def _trigger_state_mapping() -> list[dict[str, Any]]:
    return [
        {
            "trigger_state_id": "valuation_price_flow_overheat_watch",
            "source_panel": "v5c_p2_sleeve_overheat_state_panel",
            "trigger_family": "composite_sleeve_overheat",
            "allowed_spec_use": "primary fixed trigger candidate for future limited engineering decision",
            "numeric_threshold_scan_allowed": False,
            "trade_allowed_now": False,
        },
        {
            "trigger_state_id": "valuation_overheat_watch",
            "source_panel": "v5c_p2_valuation_state_panel / sleeve panel",
            "trigger_family": "valuation_only_watch",
            "allowed_spec_use": "secondary review trigger; insufficient alone for trading",
            "numeric_threshold_scan_allowed": False,
            "trade_allowed_now": False,
        },
        {
            "trigger_state_id": "market_attention_hot",
            "source_panel": "v5c_p2_crowding_state_panel",
            "trigger_family": "flow_attention_context",
            "allowed_spec_use": "confirmation/context only, not standalone trigger",
            "numeric_threshold_scan_allowed": False,
            "trade_allowed_now": False,
        },
        {
            "trigger_state_id": "downtrend",
            "source_panel": "v5c_p2_broad_index_trend_state_panel",
            "trigger_family": "broad_context",
            "allowed_spec_use": "context only; avoid mixing with ERC without conflict review",
            "numeric_threshold_scan_allowed": False,
            "trade_allowed_now": False,
        },
    ]


def _fixed_rule_spec_candidates() -> list[dict[str, Any]]:
    return [
        {
            "spec_id": "overheat_observe_only_control",
            "trigger_source": "any P3 watch state",
            "candidate_action": "record_pm_watch_note_only",
            "changes_trade_path": False,
            "changes_v57f_core": False,
            "conflicts_with_erc": False,
            "pm_admission_status": "admit_to_observation_control",
            "engineering_backtest_allowed_now": False,
            "notes": "Control line for forward observation.",
        },
        {
            "spec_id": "sleeve_composite_overheat_no_new_overweight_build",
            "trigger_source": "valuation_price_flow_overheat_watch",
            "candidate_action": "future spec may restrict new overweight build in already-hot sleeve",
            "changes_trade_path": True,
            "changes_v57f_core": False,
            "conflicts_with_erc": "review_required",
            "pm_admission_status": "admit_to_spec_only",
            "engineering_backtest_allowed_now": False,
            "notes": "Most conservative future engineering candidate; requires separate limited-engineering approval.",
        },
        {
            "spec_id": "sleeve_composite_overheat_trim_overweight_to_target",
            "trigger_source": "valuation_price_flow_overheat_watch",
            "candidate_action": "future spec may trim only overweight drift back to existing V57f target",
            "changes_trade_path": True,
            "changes_v57f_core": False,
            "conflicts_with_erc": "review_required",
            "pm_admission_status": "separate_limited_engineering_approval_required",
            "engineering_backtest_allowed_now": False,
            "notes": "More intrusive because it can create sells between regular review states.",
        },
        {
            "spec_id": "sleeve_overheat_risk_budget_cut",
            "trigger_source": "valuation_price_flow_overheat_watch plus broad downtrend",
            "candidate_action": "future spec may lower sleeve exposure or raise cash",
            "changes_trade_path": True,
            "changes_v57f_core": "boundary_conflict_review_required",
            "conflicts_with_erc": True,
            "pm_admission_status": "blocked_until_erc_conflict_review",
            "engineering_backtest_allowed_now": False,
            "notes": "Potentially conflicts with V5c ERC/defense overlay and is not admitted now.",
        },
        {
            "spec_id": "stock_level_valuation_overheat_sell",
            "trigger_source": "valuation_overheat_watch",
            "candidate_action": "sell or trim individual stock",
            "changes_trade_path": True,
            "changes_v57f_core": False,
            "conflicts_with_erc": False,
            "pm_admission_status": "reject_for_current_line",
            "engineering_backtest_allowed_now": False,
            "notes": "Too close to V5e single-name exit and vulnerable to threshold overfit.",
        },
    ]


def _allowed_blocked_actions(candidates: list[dict[str, Any]], p3_blocked: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for candidate in candidates:
        rows.append(
            {
                "item_id": candidate["spec_id"],
                "allowed_now": str(candidate["pm_admission_status"] in {"admit_to_observation_control", "admit_to_spec_only"}),
                "blocked_now": str(candidate["engineering_backtest_allowed_now"] == "False" or candidate["engineering_backtest_allowed_now"] is False),
                "reason": candidate["notes"],
                "unblock_condition": "separate_limited_engineering_approval" if candidate["pm_admission_status"] == "admit_to_spec_only" else candidate["pm_admission_status"],
            }
        )
    for row in p3_blocked:
        rows.append(
            {
                "item_id": row["blocked_action"],
                "allowed_now": "False",
                "blocked_now": "True",
                "reason": row["reason"],
                "unblock_condition": row["unblock_condition"],
            }
        )
    return rows


def _pit_contract_requirements() -> list[dict[str, Any]]:
    requirements = [
        ("p2_state_panels", "PIT valuation/crowding/sleeve/broad states must be generated before the decision time."),
        ("no_future_return_in_trigger", "Future returns may only evaluate later engineering, never form triggers."),
        ("fixed_state_trigger", "Use named P2/P3 states only; do not rescan numeric thresholds."),
        ("execution_cost_model", "Any later engineering must include V5d-compatible cost/slippage and order-health audit."),
        ("forward_observation", "P4 observation evidence should continue before candidate promotion."),
    ]
    return [{"requirement_id": req, "required": True, "description": desc} for req, desc in requirements]


def _v5c_erc_v5e_boundary_matrix() -> list[dict[str, Any]]:
    return [
        {
            "component": "V57f",
            "boundary": "core universe, sleeve logic, target_count, caps and cadence remain unchanged",
            "conflict_status": "must_not_modify",
        },
        {
            "component": "V5c ERC/defense",
            "boundary": "sleeve risk budget cuts or cash raising can conflict with ERC/defense overlays",
            "conflict_status": "conflict_review_required_before_engineering",
        },
        {
            "component": "V5e profit lock",
            "boundary": "single-name sell/trim rules belong to V5e and are not reopened here",
            "conflict_status": "stock_level_exit_rejected_for_current_line",
        },
        {
            "component": "V5d execution",
            "boundary": "execution review may consume crowding states but does not set strategy policy",
            "conflict_status": "execution_only",
        },
    ]


def _engineering_readiness_checklist() -> list[dict[str, Any]]:
    checks = [
        ("pm_approval_for_limited_engineering", False, "User approved spec opening, not engineering backtest."),
        ("fixed_rule_spec_selected", False, "A single fixed candidate must be selected before engineering."),
        ("erc_conflict_review_complete", False, "Required for any sleeve exposure cut."),
        ("cost_and_turnover_constraints_defined", False, "Required before engineering."),
        ("p4_forward_observation_active", True, "P4 packet is ready for future official rebalance tracking."),
    ]
    return [{"check_id": check, "pass": str(passed), "notes": notes} for check, passed, notes in checks]


def _spec_blockers(dependency: list[dict[str, Any]], p3_boundary: list[dict[str, str]]) -> list[dict[str, Any]]:
    blockers = []
    for row in dependency:
        if row["required_for_spec"] == "True" and row["status"] != "pass":
            blockers.append(_blocker(row["dependency_id"], row["observed"]))
    if not all(row.get("trade_order_allowed") == "False" for row in p3_boundary):
        blockers.append(_blocker("p3_trade_boundary_not_clean", "P3 boundary contains trade allowance."))
    return blockers


def _pm_decision(blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    passed = not blockers
    return [
        {
            "pm_gate_decision": "overheat_overlay_pm_quant_spec_pass_ready_for_limited_engineering_decision_not_backtest" if passed else "overheat_overlay_pm_quant_spec_blocked",
            "spec_pass": str(passed),
            "user_approved_spec_opening": True,
            "admit_limited_engineering_now": False,
            "admit_trading_rule": False,
            "accepted": False,
            "v57f_core_modified": False,
            "threshold_scan_used": False,
            "engineering_backtest_started": False,
            "network_fetch_started": False,
            "joinquant_started": False,
            "next_step": "request_explicit_limited_engineering_approval_for_one_fixed_candidate" if passed else "repair_spec_dependency",
            "review_notes": "Spec is open and completed. Limited engineering/backtest remains blocked until the user explicitly approves one fixed candidate.",
        }
    ]


def _next_queue(decision: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_gate": "v5c_overheat_overlay_limited_engineering_approval_request",
            "allowed": "False",
            "scope": "Choose exactly one fixed candidate and explicitly approve limited engineering/backtest.",
            "requires_network": False,
            "requires_v57f_change": False,
            "status": "blocked_until_user_explicitly_approves_limited_engineering",
        },
        {
            "priority": 2,
            "next_gate": "v5c_p4_state_forward_observation_packet",
            "allowed": "True",
            "scope": "Continue observe-only state tracking on future official V57f rebalances.",
            "requires_network": "maybe_if_future_data_missing",
            "requires_v57f_change": False,
            "status": "ready",
        },
        {
            "priority": 3,
            "next_gate": "v5c_p2_market_crowding_deepening_optional",
            "allowed": "True",
            "scope": "Optional local enrichment for free-float turnover/shareholder-flow if needed.",
            "requires_network": "maybe_if_local_fields_missing",
            "requires_v57f_change": False,
            "status": "optional",
        },
    ]


def _summary(
    status: str,
    decision: str,
    blockers: list[dict[str, Any]],
    spec_opening_user_approved: bool = False,
    engineering_backtest_started: bool = False,
    candidate_spec_count: int = 0,
    admitted_spec_only_count: int = 0,
    blocked_action_count: int = 0,
) -> dict[str, Any]:
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5c_overheat_overlay_pm_quant_spec",
        "status": status,
        "pm_gate_decision": decision,
        "spec_opening_user_approved": spec_opening_user_approved,
        "candidate_spec_count": candidate_spec_count,
        "admitted_spec_only_count": admitted_spec_only_count,
        "blocked_action_count": blocked_action_count,
        "accepted": False,
        "v57f_core_modified": False,
        "new_strategy_rule_added": False,
        "threshold_scan_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "engineering_backtest_started": engineering_backtest_started,
        "fatal_blocker_count": len(blockers),
        "fatal_blockers": blockers,
        "outputs": {
            "summary": str(OUT_DIR / "v5c_overheat_overlay_pm_quant_spec_summary.json"),
            "report": str(OUT_DIR / "v5c_overheat_overlay_pm_quant_spec_report.md"),
            "fixed_rule_spec_candidates": str(OUT_DIR / "v5c_overheat_overlay_fixed_rule_spec_candidates.csv"),
            "pm_gate_decision": str(OUT_DIR / "v5c_overheat_overlay_pm_gate_decision.csv"),
            "next_queue": str(OUT_DIR / "v5c_overheat_overlay_next_agent_queue.csv"),
        },
    }


def _report(state_evidence: list[dict[str, Any]], candidates: list[dict[str, Any]], decision: list[dict[str, Any]], next_queue: list[dict[str, Any]]) -> str:
    evidence_lines = [f"- `{row['evidence_scope']}` / `{row['state_id']}`: `{row['count']}`" for row in state_evidence]
    candidate_lines = [f"- `{row['spec_id']}`: {row['pm_admission_status']}" for row in candidates]
    return "\n".join(
        [
            "# V5c Overheat Overlay PM/Quant Spec",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            "- User approval scope: spec opening only.",
            "- Engineering backtest started: `False`",
            "- Trading rule admitted: `False`",
            "- Accepted: `False`",
            "",
            "## Evidence",
            *evidence_lines,
            "",
            "## Candidate Spec Status",
            *candidate_lines,
            "",
            "## Next",
            *[f"- P{row['priority']} `{row['next_gate']}`: {row['status']}" for row in next_queue],
            "",
        ]
    )


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5c Overheat Overlay PM/Quant Spec Agent Rules",
            "",
            "1. This packet is a fixed-rule PM/Quant spec only.",
            "2. Do not run engineering backtests unless the user explicitly approves one fixed candidate.",
            "3. Do not modify V57f, V5c ERC, V5d, or V5e rules.",
            "4. Do not scan thresholds or select a rule by historical return.",
            "5. Do not mark accepted, live approved, or V57f replacement.",
            "",
        ]
    )


def _count_rows(scope: str, rows: list[dict[str, str]], field: str) -> list[dict[str, Any]]:
    counts = Counter(row.get(field, "") for row in rows)
    total = len(rows)
    return [
        {
            "evidence_scope": scope,
            "state_id": state,
            "count": count,
            "share": f"{count / total:.12g}" if total else "",
            "interpretation": "Observed P2/P4 state evidence, not return evidence.",
        }
        for state, count in sorted(counts.items())
    ]


def _blocker(blocker_id: str, observed: str) -> dict[str, Any]:
    return {
        "blocker_id": blocker_id,
        "severity": "fatal",
        "status": "blocking",
        "observed": observed,
        "description": "Required overheat overlay spec dependency failed.",
    }


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [P2_SUMMARY, P2_SLEEVE_OVERHEAT, P2_VALUATION, P2_CROWDING, P3_SUMMARY, P3_BLOCKED, P3_BOUNDARY, P4_SUMMARY, P4_WATCHLIST]
    blockers = []
    for rel in required:
        if not (root / rel).exists():
            blockers.append(
                {
                    "blocker_id": f"missing_{rel.name}",
                    "severity": "fatal",
                    "status": "blocking",
                    "path": str(rel),
                    "description": "Required overheat overlay spec input is missing.",
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
    run_v5c_overheat_overlay_pm_quant_spec()

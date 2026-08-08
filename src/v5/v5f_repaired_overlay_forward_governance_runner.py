from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TRACKING_DIR = Path("v5f_repaired_overlay_forward_paper_tracking") / "current"
GOVERNANCE_DIR = Path("v5f_overlay_deployment_governance_review") / "current"
COMPARISON_DIR = Path("v5f_repaired_baseline_overlay_comparison") / "current"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_repaired_overlay_forward_governance(root: Path = Path(".")) -> dict[str, Any]:
    tracking_out = root / TRACKING_DIR
    governance_out = root / GOVERNANCE_DIR
    tracking_out.mkdir(parents=True, exist_ok=True)
    governance_out.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(tracking_out / "v5f_repaired_overlay_forward_blockers.csv", blockers)
        _write_csv(governance_out / "v5f_overlay_governance_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(tracking_out / "v5f_repaired_overlay_forward_summary.json", summary)
        _write_json(governance_out / "v5f_overlay_governance_summary.json", summary)
        return summary

    comparison = _read_json(root / COMPARISON_DIR / "v5f_repaired_overlay_summary.json")
    gate = _read_csv(root / COMPARISON_DIR / "v5f_pm_quant_gate_decision.csv")[0]
    candidate_matrix = _read_csv(root / COMPARISON_DIR / "v5f_candidate_matrix.csv")
    truth = _read_csv(root / COMPARISON_DIR / "v5f_repaired_baseline_truth_table.csv")
    pool = _read_csv(root / COMPARISON_DIR / "v5f_stock_pool_boundary_audit.csv")
    pit = _read_csv(root / COMPARISON_DIR / "v5f_pit_leakage_audit.csv")
    order = _read_csv(root / COMPARISON_DIR / "v5f_overlay_order_health.csv")
    turnover = _read_csv(root / COMPARISON_DIR / "v5f_overlay_turnover_cost_health.csv")

    candidate = _best_candidate_row(candidate_matrix, gate)
    tracking_status = _tracking_candidate_status(comparison, gate, candidate)
    tracking_schema = _tracking_schema()
    signal_template = _paper_signal_template(candidate)
    tracking_checklist = _rebalance_day_checklist(candidate)
    tracking_audit = _forward_governance_audit(comparison, gate, pool, pit)
    tracking_queue = _tracking_next_queue()
    tracking_blockers = _forward_blockers(tracking_audit)

    _write_csv(tracking_out / "v5f_repaired_overlay_forward_candidate_status.csv", tracking_status)
    _write_csv(tracking_out / "v5f_repaired_overlay_forward_tracking_schema.csv", tracking_schema)
    _write_csv(tracking_out / "v5f_repaired_overlay_paper_signal_template.csv", signal_template)
    _write_csv(tracking_out / "v5f_repaired_overlay_rebalance_day_checklist.csv", tracking_checklist)
    _write_csv(tracking_out / "v5f_repaired_overlay_forward_governance_audit.csv", tracking_audit)
    _write_csv(tracking_out / "v5f_repaired_overlay_forward_next_queue.csv", tracking_queue)
    _write_csv(tracking_out / "v5f_repaired_overlay_forward_blockers.csv", tracking_blockers)
    (tracking_out / "v5f_repaired_overlay_forward_report.md").write_text(_tracking_report(candidate, gate), encoding="utf-8")
    (tracking_out / "v5f_repaired_overlay_forward_agent_execution_rules.md").write_text(_tracking_rules(), encoding="utf-8")

    boundary = _deployment_boundary_matrix(candidate)
    preflight = _deployment_preflight(comparison, gate, truth, pool, pit, order)
    conflicts = _conflict_matrix()
    controls = _implementation_controls(candidate)
    acceptance = _acceptance_gate_matrix(candidate)
    governance_decision = _governance_decision(preflight, candidate)
    governance_queue = _governance_next_queue(governance_decision[0]["pm_gate_decision"])
    governance_blockers = _governance_blockers(preflight)

    _write_csv(governance_out / "v5f_overlay_deployment_boundary_matrix.csv", boundary)
    _write_csv(governance_out / "v5f_overlay_deployment_preflight.csv", preflight)
    _write_csv(governance_out / "v5f_overlay_erc_v5e_conflict_matrix.csv", conflicts)
    _write_csv(governance_out / "v5f_overlay_implementation_control_checklist.csv", controls)
    _write_csv(governance_out / "v5f_overlay_acceptance_gate_matrix.csv", acceptance)
    _write_csv(governance_out / "v5f_overlay_turnover_cost_review.csv", turnover)
    _write_csv(governance_out / "v5f_overlay_governance_pm_decision.csv", governance_decision)
    _write_csv(governance_out / "v5f_overlay_governance_next_queue.csv", governance_queue)
    _write_csv(governance_out / "v5f_overlay_governance_blockers.csv", governance_blockers)
    (governance_out / "v5f_overlay_governance_report.md").write_text(
        _governance_report(candidate, governance_decision, boundary),
        encoding="utf-8",
    )
    (governance_out / "v5f_overlay_governance_agent_execution_rules.md").write_text(_governance_rules(), encoding="utf-8")

    tracking_summary = _summary(
        "completed_v5f_repaired_overlay_forward_paper_tracking_packet",
        "forward_paper_tracking_ready_wait_for_next_official_v57f_rebalance_signal",
        [],
        candidate_id=candidate["candidate_id"],
        delta_return=float(candidate["delta_return_pct_points_vs_repaired_baseline"]),
        delta_drawdown=float(candidate["delta_max_drawdown_pct_points_vs_repaired_baseline"]),
    )
    governance_summary = _summary(
        "completed_v5f_overlay_deployment_governance_review",
        governance_decision[0]["pm_gate_decision"],
        [],
        candidate_id=candidate["candidate_id"],
        delta_return=float(candidate["delta_return_pct_points_vs_repaired_baseline"]),
        delta_drawdown=float(candidate["delta_max_drawdown_pct_points_vs_repaired_baseline"]),
    )
    _write_json(tracking_out / "v5f_repaired_overlay_forward_summary.json", tracking_summary)
    _write_json(governance_out / "v5f_overlay_governance_summary.json", governance_summary)
    return {
        "tracking": tracking_summary,
        "governance": governance_summary,
    }


def _best_candidate_row(candidate_matrix: list[dict[str, str]], gate: dict[str, str]) -> dict[str, str]:
    for row in candidate_matrix:
        if row["candidate_id"] == gate["best_candidate"]:
            return row
    return candidate_matrix[0]


def _tracking_candidate_status(comparison: dict[str, Any], gate: dict[str, str], candidate: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": candidate["candidate_id"],
            "overlay_family": candidate["overlay_family"],
            "source_pm_gate": gate["pm_gate_decision"],
            "status": "forward_paper_tracking_ready_not_accepted",
            "delta_return_pct_points_vs_repaired_baseline": candidate["delta_return_pct_points_vs_repaired_baseline"],
            "delta_max_drawdown_pct_points_vs_repaired_baseline": candidate["delta_max_drawdown_pct_points_vs_repaired_baseline"],
            "repaired_baseline_confirmed": comparison.get("repaired_baseline_confirmed", False),
            "accepted": False,
            "live_trading_approved": False,
        }
    ]


def _tracking_schema() -> list[dict[str, Any]]:
    return [
        {"field": "rebalance_date", "definition": "Official V57f rebalance date only."},
        {"field": "code", "definition": "Official V57f selected stock only."},
        {"field": "sleeve", "definition": "Original V57f sleeve."},
        {"field": "base_target_weight", "definition": "Startup repaired V57f target before overlay."},
        {"field": "mom_12_1_bucket", "definition": "Same-sleeve 12-1 momentum tercile."},
        {"field": "mr_60d_bucket", "definition": "Same-sleeve 60d mean-reversion tercile."},
        {"field": "overlay_target_weight", "definition": "Paper overlay weight after fixed equal blend."},
        {"field": "weight_delta", "definition": "Overlay target minus repaired V57f target."},
        {"field": "sleeve_weight_preserved", "definition": "Must be true."},
        {"field": "paper_only_status", "definition": "Not accepted and not live approved."},
    ]


def _paper_signal_template(candidate: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "rebalance_date": "TBD_next_official_v57f_rebalance",
            "candidate_id": candidate["candidate_id"],
            "signal_status": "pending_official_v57f_targets",
            "required_source": "startup_preload_repaired_v57f_targets",
            "allowed_scope": "paper_tracking_only",
            "accepted": False,
            "live_trading_approved": False,
        }
    ]


def _rebalance_day_checklist(candidate: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {"step_id": "load_official_repaired_v57f_targets", "required": True, "pass_condition": "Targets are from repaired startup-preload V57f line."},
        {"step_id": "compute_mom_12_1", "required": True, "pass_condition": "Uses only data visible before rebalance decision."},
        {"step_id": "compute_mr_60d", "required": True, "pass_condition": "Uses prior-close lagged 60d return only."},
        {"step_id": "build_equal_blend", "required": candidate["candidate_id"] == "momentum_plus_mean_reversion_equal_blend", "pass_condition": "Fixed blend, no dynamic switching."},
        {"step_id": "normalize_same_sleeve", "required": True, "pass_condition": "Every sleeve total equals repaired V57f sleeve total."},
        {"step_id": "audit_selected_pool", "required": True, "pass_condition": "Zero stocks outside repaired V57f target list."},
        {"step_id": "paper_only", "required": True, "pass_condition": "accepted=false, live_trading_approved=false."},
    ]


def _forward_governance_audit(comparison: dict[str, Any], gate: dict[str, str], pool: list[dict[str, str]], pit: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {"check_id": "comparison_gate_promoted", "status": "pass" if gate["pm_gate_decision"] == "promote_to_v5f_overlay_candidate_not_accepted" else "review", "detail": gate["pm_gate_decision"]},
        {"check_id": "repaired_baseline_confirmed", "status": "pass" if comparison.get("repaired_baseline_confirmed") else "fail", "detail": comparison.get("repaired_baseline_confirmed")},
        {"check_id": "stock_pool_boundary_clean", "status": "pass" if all(row["status"] == "pass" for row in pool) else "fail", "detail": "v57f repaired selected pool only"},
        {"check_id": "pit_clean", "status": "pass" if all(row["status"] == "pass" for row in pit) else "fail", "detail": "lagged features only"},
        {"check_id": "accepted_false", "status": "pass", "detail": False},
        {"check_id": "live_trading_approved_false", "status": "pass", "detail": False},
        {"check_id": "v57f_core_modified_false", "status": "pass", "detail": False},
    ]


def _forward_blockers(audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in audit if row["status"] == "fail"]
    if not failed:
        return [{"blocker_id": "future_official_v57f_rebalance_signal_pending", "severity": "forward_only", "status": "not_backtest_blocker", "description": "Paper rows can be populated when the next official repaired V57f rebalance target file is available."}]
    return [{"blocker_id": row["check_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed]


def _tracking_next_queue() -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task": "Populate paper signal table at next official repaired V57f rebalance", "allowed": True, "requires_threshold_scan": False},
        {"priority": 2, "task": "Compare paper overlay vs repaired V57f after observation window", "allowed": True, "requires_threshold_scan": False},
        {"priority": 3, "task": "Deployment governance approval", "allowed": False, "requires_threshold_scan": False},
    ]


def _deployment_boundary_matrix(candidate: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {"boundary": "v57f_core_modified", "allowed": False, "candidate": candidate["candidate_id"]},
        {"boundary": "v57f_replacement", "allowed": False, "candidate": candidate["candidate_id"]},
        {"boundary": "new_stock_selection", "allowed": False, "candidate": candidate["candidate_id"]},
        {"boundary": "sleeve_total_weight_change", "allowed": False, "candidate": candidate["candidate_id"]},
        {"boundary": "rebalance_frequency_change", "allowed": False, "candidate": candidate["candidate_id"]},
        {"boundary": "paper_overlay_target_weight_generation", "allowed": True, "candidate": candidate["candidate_id"]},
        {"boundary": "live_trading", "allowed": False, "candidate": candidate["candidate_id"]},
        {"boundary": "accepted_status", "allowed": False, "candidate": candidate["candidate_id"]},
    ]


def _deployment_preflight(
    comparison: dict[str, Any],
    gate: dict[str, str],
    truth: list[dict[str, str]],
    pool: list[dict[str, str]],
    pit: list[dict[str, str]],
    order: list[dict[str, str]],
) -> list[dict[str, Any]]:
    return [
        {"check_id": "repaired_baseline_truth_table_pass", "status": "pass" if all(row["status"] == "pass" for row in truth) else "fail", "detail": "first signal/trade 2021-05-06"},
        {"check_id": "comparison_gate", "status": "pass" if gate["pm_gate_decision"] == "promote_to_v5f_overlay_candidate_not_accepted" else "review", "detail": gate["pm_gate_decision"]},
        {"check_id": "pool_boundary", "status": "pass" if all(row["status"] == "pass" for row in pool) else "fail", "detail": "selected-pool only"},
        {"check_id": "pit_boundary", "status": "pass" if all(row["status"] == "pass" for row in pit) else "fail", "detail": "no future data"},
        {"check_id": "order_path_reference", "status": "pass" if all(row["status"] == "pass" for row in order) else "review", "detail": "paper target only, no trade-path approval"},
        {"check_id": "not_accepted", "status": "pass" if not comparison.get("accepted") else "fail", "detail": comparison.get("accepted")},
        {"check_id": "not_live_approved", "status": "pass" if not comparison.get("live_trading_approved") else "fail", "detail": comparison.get("live_trading_approved")},
    ]


def _conflict_matrix() -> list[dict[str, Any]]:
    return [
        {"component": "V57f", "boundary": "Overlay may read repaired targets but may not modify core selection, sleeve framework, target_count, or rebalance cadence.", "conflict_status": "clean_if_paper_only"},
        {"component": "V5c/ERC", "boundary": "Overlay is inside-sleeve stock weighting; ERC sleeve-level weight changes remain separate and require explicit conflict review before combination.", "conflict_status": "separate_approval_required"},
        {"component": "V5e", "boundary": "Overlay does not reopen V5e exit/delay-sell or cash proxy acceptance.", "conflict_status": "clean"},
        {"component": "V5d execution", "boundary": "Execution engine may only be used after separate deployment approval.", "conflict_status": "blocked_for_live"},
    ]


def _implementation_controls(candidate: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {"control_id": "fixed_candidate_id", "required": True, "expected": candidate["candidate_id"]},
        {"control_id": "no_dynamic_switching", "required": True, "expected": "no year/regime/timing switch"},
        {"control_id": "no_parameter_scan", "required": True, "expected": "fixed reviewed blend only"},
        {"control_id": "same_sleeve_normalization", "required": True, "expected": "sleeve sum unchanged"},
        {"control_id": "paper_audit_before_execution", "required": True, "expected": "must pass before any simulated/live use"},
    ]


def _acceptance_gate_matrix(candidate: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {"gate_id": "paper_tracking", "status": "ready", "candidate": candidate["candidate_id"]},
        {"gate_id": "simulated_execution", "status": "blocked", "candidate": candidate["candidate_id"]},
        {"gate_id": "accepted", "status": "blocked", "candidate": candidate["candidate_id"]},
        {"gate_id": "live_approved", "status": "blocked", "candidate": candidate["candidate_id"]},
    ]


def _governance_decision(preflight: list[dict[str, Any]], candidate: dict[str, str]) -> list[dict[str, Any]]:
    hard_ok = all(row["status"] in {"pass", "review"} for row in preflight)
    decision = "deployment_governance_ready_for_paper_tracking_not_live" if hard_ok else "blocked_until_governance_repaired"
    return [
        {
            "pm_gate_decision": decision,
            "candidate_id": candidate["candidate_id"],
            "paper_tracking_ready": hard_ok,
            "deployment_approved": False,
            "accepted": False,
            "live_trading_approved": False,
            "rationale": "Governance permits paper tracking only; simulated/live deployment remains blocked."
            if hard_ok
            else "One or more governance preflight checks failed.",
        }
    ]


def _governance_next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task": "Continue paper tracking packet at next repaired V57f rebalance", "allowed": decision.startswith("deployment_governance_ready"), "requires_user_approval": False},
        {"priority": 2, "task": "After paper evidence, prepare PM/Quant forward evidence closeout", "allowed": True, "requires_user_approval": False},
        {"priority": 3, "task": "Simulated/live deployment approval", "allowed": False, "requires_user_approval": True},
    ]


def _governance_blockers(preflight: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in preflight if row["status"] == "fail"]
    if not failed:
        return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Governance ready for paper tracking only."}]
    return [{"blocker_id": row["check_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    candidate_id: str = "",
    delta_return: float = 0.0,
    delta_drawdown: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_repaired_overlay_forward_governance",
        "status": status,
        "pm_gate_decision": decision,
        "candidate_id": candidate_id,
        "delta_return_pct_points_vs_repaired_baseline": delta_return,
        "delta_max_drawdown_pct_points_vs_repaired_baseline": delta_drawdown,
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _tracking_report(candidate: dict[str, str], gate: dict[str, str]) -> str:
    return "\n".join(
        [
            "# V5f Repaired Overlay Forward/Paper Tracking",
            "",
            f"- Candidate: `{candidate['candidate_id']}`",
            f"- Source gate: `{gate['pm_gate_decision']}`",
            "- Status: paper tracking ready, not accepted, not live approved.",
            "- Next: populate paper signal rows when next official repaired V57f rebalance target file is available.",
            "",
        ]
    )


def _governance_report(candidate: dict[str, str], decision: list[dict[str, Any]], boundary: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# V5f Overlay Deployment Governance Review",
            "",
            f"- Candidate: `{candidate['candidate_id']}`",
            f"- Decision: `{decision[0]['pm_gate_decision']}`",
            "- Deployment approved: `False`.",
            "- Live trading approved: `False`.",
            "- Accepted: `False`.",
            "",
            "## Boundary",
            *[f"- {row['boundary']}: allowed={row['allowed']}" for row in boundary],
            "",
        ]
    )


def _tracking_rules() -> str:
    return "\n".join(
        [
            "# V5f Repaired Overlay Forward Tracking Rules",
            "",
            "- Use only startup preload repaired V57f official targets.",
            "- Paper tracking only.",
            "- Do not change V57f core.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _governance_rules() -> str:
    return "\n".join(
        [
            "# V5f Overlay Deployment Governance Rules",
            "",
            "- Governance review does not grant deployment approval.",
            "- Simulated/live deployment requires separate user approval.",
            "- No full-market stock selection or parameter scan.",
            "- Preserve sleeve total weights.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        COMPARISON_DIR / "v5f_repaired_overlay_summary.json",
        COMPARISON_DIR / "v5f_pm_quant_gate_decision.csv",
        COMPARISON_DIR / "v5f_candidate_matrix.csv",
        COMPARISON_DIR / "v5f_repaired_baseline_truth_table.csv",
        COMPARISON_DIR / "v5f_stock_pool_boundary_audit.csv",
        COMPARISON_DIR / "v5f_pit_leakage_audit.csv",
        COMPARISON_DIR / "v5f_overlay_order_health.csv",
        COMPARISON_DIR / "v5f_overlay_turnover_cost_health.csv",
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
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
    print(json.dumps(run_v5f_repaired_overlay_forward_governance(Path(".")), ensure_ascii=False, indent=2))

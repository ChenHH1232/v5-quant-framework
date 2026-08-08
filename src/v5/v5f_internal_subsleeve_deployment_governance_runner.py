from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GOVERNANCE_DIR = Path("v5f_internal_subsleeve_deployment_governance") / "current"
REPLACEMENT_DIR = Path("v5f_internal_subsleeve_candidate_replacement_packet") / "current"
REVIEW_DIR = Path("v5f_internal_subsleeve_pm_quant_review") / "current"
FORWARD_DIR = Path("v5f_internal_subsleeve_forward_paper_tracking") / "current"
DEEP_DIR = Path("v5f_internal_subsleeve_deep_engineering") / "current"
REPAIRED_OVERLAY_DIR = Path("v5f_repaired_baseline_overlay_comparison") / "current"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_internal_subsleeve_deployment_governance(root: Path = Path(".")) -> dict[str, Any]:
    governance_out = root / GOVERNANCE_DIR
    replacement_out = root / REPLACEMENT_DIR
    governance_out.mkdir(parents=True, exist_ok=True)
    replacement_out.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(governance_out / "v5f_internal_subsleeve_deployment_blockers.csv", blockers)
        _write_csv(replacement_out / "v5f_candidate_replacement_blockers.csv", blockers)
        summary = _summary(
            task="v5f_internal_subsleeve_deployment_governance",
            status="blocked_missing_required_input",
            decision="blocked_until_inputs_available",
            fatal_blockers=blockers,
        )
        _write_json(governance_out / "v5f_internal_subsleeve_deployment_summary.json", summary)
        _write_json(replacement_out / "v5f_candidate_replacement_summary.json", summary)
        return {"governance": summary, "replacement": summary}

    review_summary = _read_json(root / REVIEW_DIR / "v5f_internal_subsleeve_review_summary.json")
    forward_summary = _read_json(root / FORWARD_DIR / "v5f_internal_subsleeve_forward_summary.json")
    deep_summary = _read_json(root / DEEP_DIR / "v5f_internal_subsleeve_deep_summary.json")
    deep_metrics = _read_csv(root / DEEP_DIR / "v5f_internal_subsleeve_deep_metrics.csv")
    deep_comparison = _read_csv(root / DEEP_DIR / "v5f_internal_subsleeve_vs_current_overlay.csv")
    governance_audit = _read_csv(root / DEEP_DIR / "v5f_internal_subsleeve_governance_audit.csv")
    yearly = _read_csv(root / DEEP_DIR / "v5f_internal_subsleeve_yearly_stability.csv")
    old_candidate_matrix = _read_csv(root / REPAIRED_OVERLAY_DIR / "v5f_candidate_matrix.csv")

    primary = _row(deep_metrics, "version_id", "internal_subsleeve_mom12_70_30")
    old_equal_blend = _row(old_candidate_matrix, "candidate_id", "momentum_plus_mean_reversion_equal_blend")
    replacement_compare = _row(deep_comparison, "version_id", "internal_subsleeve_mom12_70_30")

    preflight = _deployment_preflight(review_summary, forward_summary, deep_summary, governance_audit)
    boundary = _deployment_boundary_matrix(primary)
    controls = _implementation_controls(primary)
    gates = _acceptance_gate_matrix(primary)
    conflicts = _component_conflict_matrix()
    decision = _deployment_decision(preflight, primary)
    queue = _deployment_next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _soft_blockers(preflight)

    replacement_matrix = _candidate_replacement_matrix(primary, old_equal_blend, replacement_compare)
    demotion = _prior_candidate_demotion(old_equal_blend, primary)
    replacement_decision = _replacement_decision(primary, old_equal_blend, replacement_compare)
    replacement_queue = _replacement_next_queue(replacement_decision[0]["pm_gate_decision"])

    _write_csv(governance_out / "v5f_internal_subsleeve_deployment_preflight.csv", preflight)
    _write_csv(governance_out / "v5f_internal_subsleeve_deployment_boundary_matrix.csv", boundary)
    _write_csv(governance_out / "v5f_internal_subsleeve_implementation_control_checklist.csv", controls)
    _write_csv(governance_out / "v5f_internal_subsleeve_acceptance_gate_matrix.csv", gates)
    _write_csv(governance_out / "v5f_internal_subsleeve_component_conflict_matrix.csv", conflicts)
    _write_csv(governance_out / "v5f_internal_subsleeve_yearly_stability_review.csv", yearly)
    _write_csv(governance_out / "v5f_internal_subsleeve_deployment_pm_decision.csv", decision)
    _write_csv(governance_out / "v5f_internal_subsleeve_deployment_next_queue.csv", queue)
    _write_csv(governance_out / "v5f_internal_subsleeve_deployment_blockers.csv", blockers_out)
    (governance_out / "v5f_internal_subsleeve_deployment_report.md").write_text(
        _governance_report(primary, decision, preflight),
        encoding="utf-8",
    )
    (governance_out / "v5f_internal_subsleeve_deployment_agent_execution_rules.md").write_text(
        _rules(),
        encoding="utf-8",
    )

    _write_csv(replacement_out / "v5f_candidate_replacement_matrix.csv", replacement_matrix)
    _write_csv(replacement_out / "v5f_prior_candidate_demotion.csv", demotion)
    _write_csv(replacement_out / "v5f_candidate_replacement_pm_decision.csv", replacement_decision)
    _write_csv(replacement_out / "v5f_candidate_replacement_next_queue.csv", replacement_queue)
    _write_csv(replacement_out / "v5f_candidate_replacement_blockers.csv", blockers_out)
    (replacement_out / "v5f_candidate_replacement_report.md").write_text(
        _replacement_report(primary, old_equal_blend, replacement_decision),
        encoding="utf-8",
    )
    (replacement_out / "v5f_candidate_replacement_agent_execution_rules.md").write_text(
        _rules(),
        encoding="utf-8",
    )

    governance_summary = _summary(
        task="v5f_internal_subsleeve_deployment_governance",
        status="completed_v5f_internal_subsleeve_deployment_governance",
        decision=decision[0]["pm_gate_decision"],
        fatal_blockers=[],
        primary_candidate=primary["version_id"],
        delta_return=float(primary["delta_return_pct_points_vs_repaired_baseline"]),
        delta_drawdown=float(primary["delta_max_drawdown_pct_points_vs_repaired_baseline"]),
        incremental_delta_return=float(replacement_compare["incremental_delta_return_vs_current_equal_blend"]),
    )
    replacement_summary = _summary(
        task="v5f_internal_subsleeve_candidate_replacement_packet",
        status="completed_v5f_internal_subsleeve_candidate_replacement_packet",
        decision=replacement_decision[0]["pm_gate_decision"],
        fatal_blockers=[],
        primary_candidate=primary["version_id"],
        delta_return=float(primary["delta_return_pct_points_vs_repaired_baseline"]),
        delta_drawdown=float(primary["delta_max_drawdown_pct_points_vs_repaired_baseline"]),
        incremental_delta_return=float(replacement_compare["incremental_delta_return_vs_current_equal_blend"]),
    )
    _write_json(governance_out / "v5f_internal_subsleeve_deployment_summary.json", governance_summary)
    _write_json(replacement_out / "v5f_candidate_replacement_summary.json", replacement_summary)
    return {"governance": governance_summary, "replacement": replacement_summary}


def _deployment_preflight(
    review_summary: dict[str, Any],
    forward_summary: dict[str, Any],
    deep_summary: dict[str, Any],
    governance_audit: list[dict[str, str]],
) -> list[dict[str, Any]]:
    return [
        {
            "check_id": "formal_review_promoted_to_forward_paper",
            "status": "pass"
            if review_summary["pm_gate_decision"] == "promote_internal_subsleeve_70_30_to_forward_paper_candidate_not_accepted"
            else "fail",
            "detail": review_summary["pm_gate_decision"],
        },
        {
            "check_id": "forward_packet_ready",
            "status": "pass"
            if forward_summary["pm_gate_decision"] == "forward_paper_tracking_ready_wait_for_next_official_v57f_rebalance_signal"
            else "fail",
            "detail": forward_summary["pm_gate_decision"],
        },
        {
            "check_id": "large_repaired_baseline_edge",
            "status": "pass" if float(deep_summary["primary_delta_return_pct_points_vs_repaired_baseline"]) > 10.0 else "review",
            "detail": deep_summary["primary_delta_return_pct_points_vs_repaired_baseline"],
        },
        {
            "check_id": "drawdown_non_worse",
            "status": "pass" if float(deep_summary["primary_delta_max_drawdown_pct_points_vs_repaired_baseline"]) <= 0.0 else "review",
            "detail": deep_summary["primary_delta_max_drawdown_pct_points_vs_repaired_baseline"],
        },
        {
            "check_id": "governance_clean",
            "status": "pass" if all(row["status"] == "pass" for row in governance_audit) else "fail",
            "detail": "selected-pool only, sleeve totals preserved, no scan",
        },
        {"check_id": "accepted_false", "status": "pass" if not review_summary["accepted"] else "fail", "detail": review_summary["accepted"]},
        {
            "check_id": "live_trading_approved_false",
            "status": "pass" if not review_summary["live_trading_approved"] else "fail",
            "detail": review_summary["live_trading_approved"],
        },
        {
            "check_id": "deployment_approved_false",
            "status": "pass" if not review_summary["deployment_approved"] else "fail",
            "detail": review_summary["deployment_approved"],
        },
    ]


def _deployment_boundary_matrix(primary: dict[str, str]) -> list[dict[str, Any]]:
    candidate = primary["version_id"]
    return [
        {"boundary": "startup_preload_repaired_baseline_required", "allowed": True, "candidate": candidate},
        {"boundary": "v57f_core_modified", "allowed": False, "candidate": candidate},
        {"boundary": "v57f_replacement", "allowed": False, "candidate": candidate},
        {"boundary": "full_market_stock_selection", "allowed": False, "candidate": candidate},
        {"boundary": "selected_pool_only_weight_overlay", "allowed": True, "candidate": candidate},
        {"boundary": "same_sleeve_normalization", "allowed": True, "candidate": candidate},
        {"boundary": "sleeve_total_weight_change", "allowed": False, "candidate": candidate},
        {"boundary": "budget_or_parameter_scan", "allowed": False, "candidate": candidate},
        {"boundary": "paper_tracking", "allowed": True, "candidate": candidate},
        {"boundary": "accepted_or_live_approved", "allowed": False, "candidate": candidate},
    ]


def _implementation_controls(primary: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {"control_id": "fixed_candidate_id", "required": True, "expected": primary["version_id"]},
        {"control_id": "fixed_internal_split", "required": True, "expected": "70pct repaired V57f core + 30pct same-sleeve mom_12_1 top tercile"},
        {"control_id": "same_sleeve_pool_only", "required": True, "expected": "no stocks outside repaired V57f official target list"},
        {"control_id": "sleeve_weight_preserved", "required": True, "expected": "zero sleeve total drift"},
        {"control_id": "paper_before_deployment", "required": True, "expected": "forward/paper evidence before any further approval"},
        {"control_id": "no_accepted_flag", "required": True, "expected": False},
    ]


def _acceptance_gate_matrix(primary: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {"gate_id": "historical_candidate_replacement", "status": "passed_for_paper", "candidate": primary["version_id"]},
        {"gate_id": "forward_paper_tracking", "status": "ready_pending_next_official_rebalance", "candidate": primary["version_id"]},
        {"gate_id": "simulated_execution", "status": "blocked_until_separate_approval", "candidate": primary["version_id"]},
        {"gate_id": "accepted", "status": "blocked", "candidate": primary["version_id"]},
        {"gate_id": "live_approved", "status": "blocked", "candidate": primary["version_id"]},
    ]


def _component_conflict_matrix() -> list[dict[str, Any]]:
    return [
        {"component": "V57f", "conflict_status": "clean_if_overlay_only", "boundary": "Read official repaired targets; do not change core selection or sleeve framework."},
        {"component": "V5c/ERC", "conflict_status": "separate_review_required", "boundary": "ERC changes sleeve weights; internal sub-sleeve only changes weights inside sleeve."},
        {"component": "V5e", "conflict_status": "separate_review_required", "boundary": "Do not combine with profit-lock exits or 511360 cash proxy without a new combined packet."},
        {"component": "V5d execution", "conflict_status": "not_approved_for_live", "boundary": "Execution review can be reused only after deployment approval."},
    ]


def _deployment_decision(preflight: list[dict[str, Any]], primary: dict[str, str]) -> list[dict[str, Any]]:
    hard_ok = all(row["status"] in {"pass", "review"} for row in preflight)
    return [
        {
            "pm_gate_decision": "deployment_governance_ready_for_forward_paper_not_live" if hard_ok else "blocked_until_preflight_repaired",
            "primary_candidate": primary["version_id"],
            "forward_paper_ready": hard_ok,
            "accepted": False,
            "live_trading_approved": False,
            "deployment_approved": False,
            "rationale": "Large repaired-baseline edge is admitted only to forward/paper; acceptance and live deployment remain blocked."
            if hard_ok
            else "One or more hard governance checks failed.",
        }
    ]


def _deployment_next_queue(decision: str) -> list[dict[str, Any]]:
    ready = decision == "deployment_governance_ready_for_forward_paper_not_live"
    return [
        {"priority": 1, "task": "Populate internal_subsleeve_mom12_70_30 paper targets at next official repaired V57f rebalance", "allowed": ready, "requires_user_approval": False},
        {"priority": 2, "task": "Open forward evidence closeout after paper observation window", "allowed": ready, "requires_user_approval": False},
        {"priority": 3, "task": "Combined conflict review with V5c/ERC and V5e cash proxy", "allowed": True, "requires_user_approval": False},
        {"priority": 4, "task": "Accepted/live deployment approval", "allowed": False, "requires_user_approval": True},
    ]


def _candidate_replacement_matrix(
    primary: dict[str, str],
    old_equal_blend: dict[str, str],
    replacement_compare: dict[str, str],
) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": old_equal_blend["candidate_id"],
            "role_before": "primary_review_candidate",
            "role_after": "secondary_reference_archived_from_primary",
            "delta_return_pct_points_vs_repaired_baseline": old_equal_blend["delta_return_pct_points_vs_repaired_baseline"],
            "delta_max_drawdown_pct_points_vs_repaired_baseline": old_equal_blend["delta_max_drawdown_pct_points_vs_repaired_baseline"],
            "accepted": False,
            "reason": "Superseded by internal_subsleeve_mom12_70_30 on repaired-baseline return edge.",
        },
        {
            "candidate_id": primary["version_id"],
            "role_before": "new_deep_engineering_candidate",
            "role_after": "primary_forward_paper_candidate_not_accepted",
            "delta_return_pct_points_vs_repaired_baseline": primary["delta_return_pct_points_vs_repaired_baseline"],
            "delta_max_drawdown_pct_points_vs_repaired_baseline": primary["delta_max_drawdown_pct_points_vs_repaired_baseline"],
            "incremental_delta_return_vs_prior_primary": replacement_compare["incremental_delta_return_vs_current_equal_blend"],
            "accepted": False,
            "reason": "Clear repaired-baseline improvement with non-worse drawdown and clean governance.",
        },
    ]


def _prior_candidate_demotion(old_equal_blend: dict[str, str], primary: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "prior_candidate": old_equal_blend["candidate_id"],
            "new_primary_candidate": primary["version_id"],
            "prior_status": old_equal_blend["status"],
            "new_status": "secondary_reference_not_primary",
            "accepted": False,
            "live_trading_approved": False,
            "rationale": "Prior equal-blend remains useful as a conservative reference, but no longer leads the V5f queue.",
        }
    ]


def _replacement_decision(
    primary: dict[str, str],
    old_equal_blend: dict[str, str],
    replacement_compare: dict[str, str],
) -> list[dict[str, Any]]:
    improvement = float(replacement_compare["incremental_delta_return_vs_current_equal_blend"])
    return [
        {
            "pm_gate_decision": "replace_equal_blend_with_internal_subsleeve_70_30_as_primary_forward_candidate_not_accepted"
            if improvement > 5.0
            else "retain_equal_blend_primary_pending_more_evidence",
            "new_primary_candidate": primary["version_id"],
            "prior_primary_candidate": old_equal_blend["candidate_id"],
            "incremental_delta_return_vs_prior_primary": improvement,
            "accepted": False,
            "live_trading_approved": False,
            "rationale": "The new internal sub-sleeve candidate is the only current model with obvious repaired-baseline improvement."
            if improvement > 5.0
            else "The improvement was not large enough to replace the prior candidate.",
        }
    ]


def _replacement_next_queue(decision: str) -> list[dict[str, Any]]:
    replaced = decision.startswith("replace_equal_blend")
    return [
        {"priority": 1, "task": "Use internal_subsleeve_mom12_70_30 as the V5f primary forward/paper candidate", "allowed": replaced},
        {"priority": 2, "task": "Keep momentum_plus_mean_reversion_equal_blend as secondary reference only", "allowed": replaced},
        {"priority": 3, "task": "Prepare next official rebalance paper target population", "allowed": replaced},
        {"priority": 4, "task": "Do further parameter-budget scan", "allowed": False},
    ]


def _soft_blockers(preflight: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in preflight if row["status"] == "fail"]
    if failed:
        return [{"blocker_id": row["check_id"], "severity": "fatal", "status": "blocking", "description": row["detail"]} for row in failed]
    return [
        {
            "blocker_id": "next_official_repaired_v57f_rebalance_signal_pending",
            "severity": "forward_only",
            "status": "not_backtest_blocker",
            "description": "Forward/paper rows require the next official startup-preload repaired V57f target file.",
        }
    ]


def _summary(
    task: str,
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    primary_candidate: str = "",
    delta_return: float = 0.0,
    delta_drawdown: float = 0.0,
    incremental_delta_return: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": task,
        "status": status,
        "pm_gate_decision": decision,
        "primary_candidate": primary_candidate,
        "delta_return_pct_points_vs_repaired_baseline": delta_return,
        "delta_max_drawdown_pct_points_vs_repaired_baseline": delta_drawdown,
        "incremental_delta_return_vs_prior_primary": incremental_delta_return,
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


def _governance_report(primary: dict[str, str], decision: list[dict[str, Any]], preflight: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# V5f Internal Sub-Sleeve Deployment Governance",
            "",
            f"- Candidate: `{primary['version_id']}`",
            f"- Decision: `{decision[0]['pm_gate_decision']}`",
            f"- Repaired-baseline return delta: {float(primary['delta_return_pct_points_vs_repaired_baseline']):.4f} pct points.",
            f"- Repaired-baseline drawdown delta: {float(primary['delta_max_drawdown_pct_points_vs_repaired_baseline']):.4f} pct points.",
            "- Status: forward/paper only, not accepted, not live approved.",
            "",
            "## Preflight",
            *[f"- {row['check_id']}: {row['status']} ({row['detail']})" for row in preflight],
            "",
        ]
    )


def _replacement_report(
    primary: dict[str, str],
    old_equal_blend: dict[str, str],
    decision: list[dict[str, Any]],
) -> str:
    return "\n".join(
        [
            "# V5f Candidate Replacement Packet",
            "",
            f"- Decision: `{decision[0]['pm_gate_decision']}`",
            f"- New primary: `{primary['version_id']}`",
            f"- Prior primary/reference: `{old_equal_blend['candidate_id']}`",
            f"- New primary return delta: {float(primary['delta_return_pct_points_vs_repaired_baseline']):.4f} pct points vs repaired baseline.",
            f"- Prior candidate return delta: {float(old_equal_blend['delta_return_pct_points_vs_repaired_baseline']):.4f} pct points vs repaired baseline.",
            f"- Incremental improvement: {float(decision[0]['incremental_delta_return_vs_prior_primary']):.4f} pct points.",
            "- Replacement is for forward/paper candidate ordering only; not accepted.",
            "",
        ]
    )


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Internal Sub-Sleeve Deployment Rules",
            "",
            "- Use startup preload repaired V57f baseline only.",
            "- Candidate is `internal_subsleeve_mom12_70_30` only.",
            "- Do not modify V57f core or sleeve totals.",
            "- Do not use full-market stock selection.",
            "- Do not scan budgets or parameters.",
            "- Do not mark accepted, deployment approved, or live approved.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        REVIEW_DIR / "v5f_internal_subsleeve_review_summary.json",
        FORWARD_DIR / "v5f_internal_subsleeve_forward_summary.json",
        DEEP_DIR / "v5f_internal_subsleeve_deep_summary.json",
        DEEP_DIR / "v5f_internal_subsleeve_deep_metrics.csv",
        DEEP_DIR / "v5f_internal_subsleeve_vs_current_overlay.csv",
        DEEP_DIR / "v5f_internal_subsleeve_governance_audit.csv",
        DEEP_DIR / "v5f_internal_subsleeve_yearly_stability.csv",
        REPAIRED_OVERLAY_DIR / "v5f_candidate_matrix.csv",
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _row(rows: list[dict[str, str]], key: str, value: str) -> dict[str, str]:
    for row in rows:
        if row[key] == value:
            return row
    raise ValueError(f"missing row {key}={value}")


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
    print(json.dumps(run_v5f_internal_subsleeve_deployment_governance(Path(".")), ensure_ascii=False, indent=2))

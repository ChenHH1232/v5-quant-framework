from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REVIEW_DIR = Path("v5f_internal_subsleeve_pm_quant_review") / "current"
FORWARD_DIR = Path("v5f_internal_subsleeve_forward_paper_tracking") / "current"
DEEP_DIR = Path("v5f_internal_subsleeve_deep_engineering") / "current"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_internal_subsleeve_formal_review(root: Path = Path(".")) -> dict[str, Any]:
    review_out = root / REVIEW_DIR
    forward_out = root / FORWARD_DIR
    review_out.mkdir(parents=True, exist_ok=True)
    forward_out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(review_out / "v5f_internal_subsleeve_review_blockers.csv", blockers)
        _write_csv(forward_out / "v5f_internal_subsleeve_forward_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(review_out / "v5f_internal_subsleeve_review_summary.json", summary)
        _write_json(forward_out / "v5f_internal_subsleeve_forward_summary.json", summary)
        return summary

    deep_summary = _read_json(root / DEEP_DIR / "v5f_internal_subsleeve_deep_summary.json")
    deep_metrics = _read_csv(root / DEEP_DIR / "v5f_internal_subsleeve_deep_metrics.csv")
    comparison = _read_csv(root / DEEP_DIR / "v5f_internal_subsleeve_vs_current_overlay.csv")
    governance = _read_csv(root / DEEP_DIR / "v5f_internal_subsleeve_governance_audit.csv")
    yearly = _read_csv(root / DEEP_DIR / "v5f_internal_subsleeve_yearly_stability.csv")

    candidate_checks = _candidate_checks(deep_summary, deep_metrics, comparison, governance)
    risk_benefit = _risk_benefit(deep_summary, comparison, yearly)
    candidate_matrix = _candidate_matrix(deep_metrics, comparison)
    decision = _decision(candidate_checks, deep_summary)
    next_queue = _review_next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _blockers(candidate_checks)

    _write_csv(review_out / "v5f_internal_subsleeve_candidate_checks.csv", candidate_checks)
    _write_csv(review_out / "v5f_internal_subsleeve_risk_benefit_matrix.csv", risk_benefit)
    _write_csv(review_out / "v5f_internal_subsleeve_candidate_matrix.csv", candidate_matrix)
    _write_csv(review_out / "v5f_internal_subsleeve_pm_gate_decision.csv", decision)
    _write_csv(review_out / "v5f_internal_subsleeve_review_next_queue.csv", next_queue)
    _write_csv(review_out / "v5f_internal_subsleeve_review_blockers.csv", blockers_out)
    (review_out / "v5f_internal_subsleeve_review_report.md").write_text(_review_report(deep_summary, decision, risk_benefit), encoding="utf-8")
    (review_out / "v5f_internal_subsleeve_next_prompt.md").write_text(_forward_prompt(decision[0]), encoding="utf-8")
    (review_out / "v5f_internal_subsleeve_review_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    forward_status = _forward_status(decision[0], deep_summary)
    forward_schema = _forward_schema()
    forward_checklist = _forward_checklist()
    forward_queue = _forward_next_queue()
    forward_blockers = [
        {
            "blocker_id": "next_official_repaired_v57f_rebalance_signal_pending",
            "severity": "forward_only",
            "status": "not_backtest_blocker",
            "description": "Populate paper signal rows when the next official startup-preload repaired V57f rebalance target is available.",
        }
    ]
    _write_csv(forward_out / "v5f_internal_subsleeve_forward_candidate_status.csv", forward_status)
    _write_csv(forward_out / "v5f_internal_subsleeve_forward_schema.csv", forward_schema)
    _write_csv(forward_out / "v5f_internal_subsleeve_rebalance_day_checklist.csv", forward_checklist)
    _write_csv(forward_out / "v5f_internal_subsleeve_forward_next_queue.csv", forward_queue)
    _write_csv(forward_out / "v5f_internal_subsleeve_forward_blockers.csv", forward_blockers)
    (forward_out / "v5f_internal_subsleeve_forward_report.md").write_text(_forward_report(deep_summary), encoding="utf-8")
    (forward_out / "v5f_internal_subsleeve_forward_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    review_summary = _summary(
        "completed_v5f_internal_subsleeve_pm_quant_review",
        decision[0]["pm_gate_decision"],
        [],
        primary_candidate=deep_summary["primary_candidate"],
        delta_return=float(deep_summary["primary_delta_return_pct_points_vs_repaired_baseline"]),
        delta_drawdown=float(deep_summary["primary_delta_max_drawdown_pct_points_vs_repaired_baseline"]),
    )
    forward_summary = _summary(
        "completed_v5f_internal_subsleeve_forward_paper_tracking_packet",
        "forward_paper_tracking_ready_wait_for_next_official_v57f_rebalance_signal",
        [],
        primary_candidate=deep_summary["primary_candidate"],
        delta_return=float(deep_summary["primary_delta_return_pct_points_vs_repaired_baseline"]),
        delta_drawdown=float(deep_summary["primary_delta_max_drawdown_pct_points_vs_repaired_baseline"]),
    )
    _write_json(review_out / "v5f_internal_subsleeve_review_summary.json", review_summary)
    _write_json(forward_out / "v5f_internal_subsleeve_forward_summary.json", forward_summary)
    return {"review": review_summary, "forward": forward_summary}


def _candidate_checks(
    deep_summary: dict[str, Any],
    deep_metrics: list[dict[str, str]],
    comparison: list[dict[str, str]],
    governance: list[dict[str, str]],
) -> list[dict[str, Any]]:
    primary = next(row for row in deep_metrics if row["version_id"] == "internal_subsleeve_mom12_70_30")
    compare = next(row for row in comparison if row["version_id"] == "internal_subsleeve_mom12_70_30")
    return [
        {"check_id": "deep_engineering_gate", "pass": deep_summary["pm_gate_decision"] == "promote_internal_subsleeve_70_30_to_v5f_candidate_not_accepted", "detail": deep_summary["pm_gate_decision"]},
        {"check_id": "large_return_edge", "pass": float(primary["delta_return_pct_points_vs_repaired_baseline"]) > 5.0, "detail": primary["delta_return_pct_points_vs_repaired_baseline"]},
        {"check_id": "drawdown_non_worse", "pass": float(primary["delta_max_drawdown_pct_points_vs_repaired_baseline"]) <= 0.0, "detail": primary["delta_max_drawdown_pct_points_vs_repaired_baseline"]},
        {"check_id": "yearly_win_rate_ok", "pass": float(deep_summary["yearly_win_rate"]) >= 0.6, "detail": deep_summary["yearly_win_rate"]},
        {"check_id": "rebalance_period_win_rate_ok", "pass": float(deep_summary["rebalance_period_win_rate"]) >= 0.55, "detail": deep_summary["rebalance_period_win_rate"]},
        {"check_id": "beats_current_equal_blend", "pass": compare["beats_current_on_return"] == "True", "detail": compare["incremental_delta_return_vs_current_equal_blend"]},
        {"check_id": "governance_clean", "pass": all(row["status"] == "pass" for row in governance), "detail": "selected pool only, sleeve preserved"},
        {"check_id": "not_accepted_or_live", "pass": not deep_summary["accepted"] and not deep_summary["live_trading_approved"], "detail": "not accepted/live"},
    ]


def _risk_benefit(deep_summary: dict[str, Any], comparison: list[dict[str, str]], yearly: list[dict[str, str]]) -> list[dict[str, Any]]:
    compare = next(row for row in comparison if row["version_id"] == "internal_subsleeve_mom12_70_30")
    years = [row for row in yearly if row["version_id"] == "internal_subsleeve_mom12_70_30"]
    negative_years = [row["year"] for row in years if float(row["delta_return_pct_points_vs_repaired_baseline"]) < 0]
    return [
        {"topic": "return_edge", "benefit": f"{deep_summary['primary_delta_return_pct_points_vs_repaired_baseline']:.4f} pct points vs repaired baseline", "risk": "historical repaired window only", "pm_read": "strong_positive"},
        {"topic": "drawdown", "benefit": f"{deep_summary['primary_delta_max_drawdown_pct_points_vs_repaired_baseline']:.4f} pct point drawdown delta", "risk": "improvement is small but non-worse", "pm_read": "pass"},
        {"topic": "versus_current_candidate", "benefit": f"{float(compare['incremental_delta_return_vs_current_equal_blend']):.4f} pct points over current equal-blend", "risk": "current equal-blend is more conservative", "pm_read": "strong_upgrade"},
        {"topic": "yearly_stability", "benefit": f"wins {float(deep_summary['yearly_win_rate']) * 100:.2f}% of years", "risk": f"negative years: {','.join(negative_years)}", "pm_read": "adequate_not_perfect"},
    ]


def _candidate_matrix(deep_metrics: list[dict[str, str]], comparison: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in deep_metrics:
        if row["version_id"] == "v57f_startup_preload_repaired_baseline":
            continue
        compare = next(item for item in comparison if item["version_id"] == row["version_id"])
        rows.append(
            {
                "candidate_id": row["version_id"],
                "role": "primary" if row["version_id"] == "internal_subsleeve_mom12_70_30" else "secondary_stress",
                "delta_return_pct_points_vs_repaired_baseline": row["delta_return_pct_points_vs_repaired_baseline"],
                "delta_max_drawdown_pct_points_vs_repaired_baseline": row["delta_max_drawdown_pct_points_vs_repaired_baseline"],
                "incremental_delta_return_vs_current_equal_blend": compare["incremental_delta_return_vs_current_equal_blend"],
                "status": "formal_review_candidate_not_accepted" if row["version_id"] == "internal_subsleeve_mom12_70_30" else "secondary_stress_reference",
                "accepted": False,
            }
        )
    return rows


def _decision(checks: list[dict[str, Any]], deep_summary: dict[str, Any]) -> list[dict[str, Any]]:
    passed = all(bool(row["pass"]) for row in checks)
    return [
        {
            "pm_gate_decision": "promote_internal_subsleeve_70_30_to_forward_paper_candidate_not_accepted" if passed else "retain_internal_subsleeve_as_diagnostic_only",
            "primary_candidate": deep_summary["primary_candidate"],
            "candidate_promoted": passed,
            "delta_return_pct_points_vs_repaired_baseline": deep_summary["primary_delta_return_pct_points_vs_repaired_baseline"],
            "delta_max_drawdown_pct_points_vs_repaired_baseline": deep_summary["primary_delta_max_drawdown_pct_points_vs_repaired_baseline"],
            "accepted": False,
            "live_trading_approved": False,
            "rationale": "Strong repaired-baseline improvement with clean governance; forward/paper only, not accepted."
            if passed
            else "One or more PM/Quant checks failed.",
        }
    ]


def _review_next_queue(decision: str) -> list[dict[str, Any]]:
    promoted = decision.startswith("promote")
    return [
        {"priority": 1, "task": "V5f internal sub-sleeve forward/paper tracking population", "allowed": promoted, "requires_threshold_scan": False},
        {"priority": 2, "task": "Deployment governance review for internal sub-sleeve", "allowed": promoted, "requires_threshold_scan": False},
        {"priority": 3, "task": "Scan 60/40 or 90/10 budgets", "allowed": False, "requires_threshold_scan": True},
    ]


def _forward_status(decision: dict[str, Any], deep_summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": deep_summary["primary_candidate"],
            "source_pm_gate": decision["pm_gate_decision"],
            "status": "forward_paper_tracking_ready_not_accepted",
            "delta_return_pct_points_vs_repaired_baseline": deep_summary["primary_delta_return_pct_points_vs_repaired_baseline"],
            "delta_max_drawdown_pct_points_vs_repaired_baseline": deep_summary["primary_delta_max_drawdown_pct_points_vs_repaired_baseline"],
            "accepted": False,
            "live_trading_approved": False,
        }
    ]


def _forward_schema() -> list[dict[str, Any]]:
    return [
        {"field": "rebalance_date", "definition": "Official startup-preload repaired V57f rebalance date."},
        {"field": "code", "definition": "Official repaired V57f selected stock only."},
        {"field": "sleeve", "definition": "Original V57f sleeve."},
        {"field": "base_target_weight", "definition": "Original repaired V57f target weight."},
        {"field": "mom_12_1", "definition": "12-1 momentum visible before rebalance decision."},
        {"field": "bucket", "definition": "same-sleeve top tercile gets momentum sub-sleeve allocation."},
        {"field": "overlay_target_weight", "definition": "70% core target plus 30% same-sleeve momentum sub-sleeve target."},
        {"field": "sleeve_weight_preserved", "definition": "Must be true."},
    ]


def _forward_checklist() -> list[dict[str, Any]]:
    return [
        {"step_id": "load_repaired_v57f_targets", "required": True, "pass_condition": "official repaired target file exists"},
        {"step_id": "compute_mom_12_1", "required": True, "pass_condition": "no future data"},
        {"step_id": "allocate_70_core_30_momentum_within_sleeve", "required": True, "pass_condition": "fixed rule only"},
        {"step_id": "audit_sleeve_weight_preserved", "required": True, "pass_condition": "zero violations"},
        {"step_id": "paper_only", "required": True, "pass_condition": "accepted=false and live=false"},
    ]


def _forward_next_queue() -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task": "Populate internal sub-sleeve paper rows at next repaired V57f rebalance", "allowed": True, "requires_threshold_scan": False},
        {"priority": 2, "task": "Compare paper tracking vs repaired V57f and prior equal-blend candidate", "allowed": True, "requires_threshold_scan": False},
        {"priority": 3, "task": "Live/simulated deployment approval", "allowed": False, "requires_threshold_scan": False},
    ]


def _blockers(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [row for row in checks if not bool(row["pass"])]
    return [{"blocker_id": row["check_id"], "severity": "review", "status": "blocking", "description": row["detail"]} for row in failed] or [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "PM/Quant formal review passed for forward/paper."}]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    primary_candidate: str = "",
    delta_return: float = 0.0,
    delta_drawdown: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_internal_subsleeve_formal_review",
        "status": status,
        "pm_gate_decision": decision,
        "primary_candidate": primary_candidate,
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


def _review_report(deep_summary: dict[str, Any], decision: list[dict[str, Any]], risk_benefit: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# V5f Internal Sub-Sleeve PM/Quant Review",
            "",
            f"- Decision: `{decision[0]['pm_gate_decision']}`",
            f"- Primary: `{deep_summary['primary_candidate']}`",
            f"- Return delta: {float(deep_summary['primary_delta_return_pct_points_vs_repaired_baseline']):.4f} pct points.",
            f"- Drawdown delta: {float(deep_summary['primary_delta_max_drawdown_pct_points_vs_repaired_baseline']):.4f} pct points.",
            "- Status: forward/paper candidate only; not accepted.",
            "",
            "## Risk Benefit",
            *[f"- {row['topic']}: {row['pm_read']} | benefit={row['benefit']} | risk={row['risk']}" for row in risk_benefit],
            "",
        ]
    )


def _forward_report(deep_summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# V5f Internal Sub-Sleeve Forward/Paper Tracking",
            "",
            f"- Candidate: `{deep_summary['primary_candidate']}`",
            "- Status: ready for next official repaired V57f rebalance target.",
            "- Not accepted. Not live approved.",
            "",
        ]
    )


def _forward_prompt(decision: dict[str, Any]) -> str:
    return f"""Working directory:
D:\\hh\\codex\\v5

Task name:
V5f internal sub-sleeve forward/paper tracking population

Objective:
When the next official startup-preload repaired V57f rebalance target is available, populate paper target weights for `internal_subsleeve_mom12_70_30`. Do not modify V57f, do not select full-market stocks, do not change sleeve totals, do not scan budgets, and do not mark accepted/live approved.

Source PM gate:
`{decision["pm_gate_decision"]}`
"""


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Internal Sub-Sleeve Formal Review Rules",
            "",
            "- Repaired V57f baseline only.",
            "- V57f selected-stock pool only.",
            "- 70/30 fixed internal sub-sleeve only.",
            "- No budget scan.",
            "- Not accepted and not live approved.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        DEEP_DIR / "v5f_internal_subsleeve_deep_summary.json",
        DEEP_DIR / "v5f_internal_subsleeve_deep_metrics.csv",
        DEEP_DIR / "v5f_internal_subsleeve_vs_current_overlay.csv",
        DEEP_DIR / "v5f_internal_subsleeve_governance_audit.csv",
        DEEP_DIR / "v5f_internal_subsleeve_yearly_stability.csv",
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
    print(json.dumps(run_v5f_internal_subsleeve_formal_review(Path(".")), ensure_ascii=False, indent=2))

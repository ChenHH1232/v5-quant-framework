from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5f_progress_checkpoint") / "current"
COMPARISON_DIR = Path("v5f_repaired_baseline_overlay_comparison") / "current"
TRACKING_DIR = Path("v5f_repaired_overlay_forward_paper_tracking") / "current"
GOVERNANCE_DIR = Path("v5f_overlay_deployment_governance_review") / "current"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_progress_checkpoint(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_progress_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_progress_summary.json", summary)
        return summary

    comparison = _read_json(root / COMPARISON_DIR / "v5f_repaired_overlay_summary.json")
    tracking = _read_json(root / TRACKING_DIR / "v5f_repaired_overlay_forward_summary.json")
    governance = _read_json(root / GOVERNANCE_DIR / "v5f_overlay_governance_summary.json")
    gate = _read_csv(root / COMPARISON_DIR / "v5f_pm_quant_gate_decision.csv")[0]
    candidates = _read_csv(root / COMPARISON_DIR / "v5f_candidate_matrix.csv")
    governance_queue = _read_csv(root / GOVERNANCE_DIR / "v5f_overlay_governance_next_queue.csv")

    status_matrix = _status_matrix(comparison, tracking, governance, gate)
    next_actions = _next_action_matrix(governance_queue)
    decision = _pm_decision(comparison, tracking, governance)
    blockers_out = _blockers(decision)

    _write_csv(out / "v5f_progress_status_matrix.csv", status_matrix)
    _write_csv(out / "v5f_progress_candidate_matrix.csv", candidates)
    _write_csv(out / "v5f_progress_next_action_matrix.csv", next_actions)
    _write_csv(out / "v5f_progress_pm_decision.csv", decision)
    _write_csv(out / "v5f_progress_blockers.csv", blockers_out)
    (out / "v5f_progress_next_prompt.md").write_text(_next_prompt(decision[0]), encoding="utf-8")
    (out / "v5f_progress_report.md").write_text(_report(status_matrix, next_actions, decision), encoding="utf-8")
    (out / "v5f_progress_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    summary = _summary(
        "completed_v5f_progress_checkpoint",
        decision[0]["pm_gate_decision"],
        [],
        candidate_id=comparison["best_candidate"],
        next_task=decision[0]["next_task"],
        requires_future_rebalance_signal=decision[0]["requires_future_rebalance_signal"] == "True",
    )
    _write_json(out / "v5f_progress_summary.json", summary)
    return summary


def _status_matrix(comparison: dict[str, Any], tracking: dict[str, Any], governance: dict[str, Any], gate: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "component": "repaired_baseline_overlay_comparison",
            "status": comparison["status"],
            "pm_gate": comparison["pm_gate_decision"],
            "candidate_id": comparison["best_candidate"],
            "delta_return_pct_points_vs_repaired_baseline": comparison["best_delta_return_pct_points_vs_repaired_baseline"],
            "delta_max_drawdown_pct_points_vs_repaired_baseline": comparison["best_delta_max_drawdown_pct_points_vs_repaired_baseline"],
            "accepted": comparison["accepted"],
            "live_trading_approved": comparison["live_trading_approved"],
            "ready_state": "complete",
        },
        {
            "component": "forward_paper_tracking_packet",
            "status": tracking["status"],
            "pm_gate": tracking["pm_gate_decision"],
            "candidate_id": tracking["candidate_id"],
            "delta_return_pct_points_vs_repaired_baseline": tracking["delta_return_pct_points_vs_repaired_baseline"],
            "delta_max_drawdown_pct_points_vs_repaired_baseline": tracking["delta_max_drawdown_pct_points_vs_repaired_baseline"],
            "accepted": tracking["accepted"],
            "live_trading_approved": tracking["live_trading_approved"],
            "ready_state": "ready_waiting_next_official_rebalance_signal",
        },
        {
            "component": "deployment_governance_review",
            "status": governance["status"],
            "pm_gate": governance["pm_gate_decision"],
            "candidate_id": governance["candidate_id"],
            "delta_return_pct_points_vs_repaired_baseline": governance["delta_return_pct_points_vs_repaired_baseline"],
            "delta_max_drawdown_pct_points_vs_repaired_baseline": governance["delta_max_drawdown_pct_points_vs_repaired_baseline"],
            "accepted": governance["accepted"],
            "live_trading_approved": governance["live_trading_approved"],
            "ready_state": "paper_tracking_only_not_live",
        },
        {
            "component": "pm_quant_candidate_gate",
            "status": "complete",
            "pm_gate": gate["pm_gate_decision"],
            "candidate_id": gate["best_candidate"],
            "delta_return_pct_points_vs_repaired_baseline": gate["best_delta_return_pct_points_vs_repaired_baseline"],
            "delta_max_drawdown_pct_points_vs_repaired_baseline": gate["best_delta_max_drawdown_pct_points_vs_repaired_baseline"],
            "accepted": gate["accepted"],
            "live_trading_approved": gate["live_trading_approved"],
            "ready_state": "candidate_not_accepted",
        },
    ]


def _next_action_matrix(governance_queue: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in governance_queue:
        task = row["task"]
        rows.append(
            {
                "priority": row["priority"],
                "task": task,
                "allowed": row["allowed"],
                "requires_user_approval": row["requires_user_approval"],
                "requires_future_rebalance_signal": "True" if "next repaired V57f rebalance" in task else "False",
                "action_status": "forward_pending" if "next repaired V57f rebalance" in task else ("blocked_requires_user_approval" if row["requires_user_approval"] == "True" else "ready_after_forward_evidence"),
            }
        )
    return rows


def _pm_decision(comparison: dict[str, Any], tracking: dict[str, Any], governance: dict[str, Any]) -> list[dict[str, Any]]:
    paper_ready = (
        comparison["pm_gate_decision"] == "promote_to_v5f_overlay_candidate_not_accepted"
        and tracking["pm_gate_decision"] == "forward_paper_tracking_ready_wait_for_next_official_v57f_rebalance_signal"
        and governance["pm_gate_decision"] == "deployment_governance_ready_for_paper_tracking_not_live"
    )
    return [
        {
            "pm_gate_decision": "v5f_wait_for_next_repaired_v57f_rebalance_paper_tracking" if paper_ready else "v5f_progress_needs_repair",
            "candidate_id": comparison["best_candidate"],
            "next_task": "populate_forward_paper_signal_when_next_official_repaired_v57f_rebalance_available" if paper_ready else "repair_v5f_progress_inputs",
            "requires_future_rebalance_signal": str(paper_ready),
            "accepted": False,
            "live_trading_approved": False,
            "deployment_approved": False,
            "rationale": "V5f candidate and governance packets are complete; execution of the next step waits for future official repaired V57f rebalance targets."
            if paper_ready
            else "One or more V5f progress components is not ready.",
        }
    ]


def _blockers(decision: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if decision[0]["pm_gate_decision"] == "v5f_wait_for_next_repaired_v57f_rebalance_paper_tracking":
        return [
            {
                "blocker_id": "next_official_repaired_v57f_rebalance_signal_pending",
                "severity": "forward_only",
                "status": "not_backtest_blocker",
                "description": "Paper tracking rows can be populated after the next official repaired V57f rebalance target file exists.",
            }
        ]
    return [{"blocker_id": "progress_component_not_ready", "severity": "fatal", "status": "blocking", "description": decision[0]["rationale"]}]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    candidate_id: str = "",
    next_task: str = "",
    requires_future_rebalance_signal: bool = False,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_progress_checkpoint",
        "status": status,
        "pm_gate_decision": decision,
        "candidate_id": candidate_id,
        "next_task": next_task,
        "requires_future_rebalance_signal": requires_future_rebalance_signal,
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


def _report(status_matrix: list[dict[str, Any]], next_actions: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# V5f Progress Checkpoint",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Candidate: `{decision[0]['candidate_id']}`",
            "- Accepted: `False`.",
            "- Live approved: `False`.",
            "- Deployment approved: `False`.",
            "",
            "## Status",
            *[f"- `{row['component']}`: {row['ready_state']} / {row['pm_gate']}" for row in status_matrix],
            "",
            "## Next Actions",
            *[f"- P{row['priority']} `{row['task']}`: {row['action_status']}" for row in next_actions],
            "",
        ]
    )


def _next_prompt(decision: dict[str, Any]) -> str:
    return f"""Working directory:
D:\\hh\\codex\\v5

Task name:
V5f repaired overlay paper tracking population after next official V57f rebalance

Objective:
When the next official startup-preload repaired V57f rebalance target file is available, populate the paper tracking signal table for `momentum_plus_mean_reversion_equal_blend` and compare it against the repaired V57f baseline. Do not modify V57f, do not add stocks, do not change sleeve total weights, do not scan parameters, and do not mark accepted / live approved / deployment approved.

Current status:
- PM gate: `{decision["pm_gate_decision"]}`
- candidate: `{decision["candidate_id"]}`
- next task: `{decision["next_task"]}`

Read first:
- v5f_progress_checkpoint\\current\\v5f_progress_summary.json
- v5f_repaired_baseline_overlay_comparison\\current\\v5f_repaired_overlay_summary.json
- v5f_repaired_overlay_forward_paper_tracking\\current\\v5f_repaired_overlay_forward_candidate_status.csv
- v5f_repaired_overlay_forward_paper_tracking\\current\\v5f_repaired_overlay_paper_signal_template.csv
- v5f_overlay_deployment_governance_review\\current\\v5f_overlay_governance_summary.json

Execution boundaries:
1. Use only the next official repaired V57f target file.
2. Apply overlay target weights only inside the official V57f selected stock list.
3. Normalize within each sleeve; sleeve total weight must remain unchanged.
4. No full-market stock selection.
5. No V57f core modification.
6. No accepted / live approved / deployment approved status.

If the next official repaired V57f rebalance target is still unavailable:
- Do not treat it as a historical backtest blocker.
- Output forward_only_pending.
- Keep the next queue open.
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5f Progress Checkpoint Rules",
            "",
            "- Repaired baseline remains the only benchmark.",
            "- Current V5f overlay is paper tracking only.",
            "- Do not mark accepted, live approved, or deployment approved.",
            "- Next actionable trading-cycle step requires future official repaired V57f rebalance targets.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        COMPARISON_DIR / "v5f_repaired_overlay_summary.json",
        COMPARISON_DIR / "v5f_pm_quant_gate_decision.csv",
        COMPARISON_DIR / "v5f_candidate_matrix.csv",
        TRACKING_DIR / "v5f_repaired_overlay_forward_summary.json",
        GOVERNANCE_DIR / "v5f_overlay_governance_summary.json",
        GOVERNANCE_DIR / "v5f_overlay_governance_next_queue.csv",
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
    print(json.dumps(run_v5f_progress_checkpoint(Path(".")), ensure_ascii=False, indent=2))

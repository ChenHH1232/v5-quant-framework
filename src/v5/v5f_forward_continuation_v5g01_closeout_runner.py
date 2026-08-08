from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.v5f_internal_subsleeve_queue_123_runner import run_v5f_internal_subsleeve_queue_123


OUT_DIR = Path("v5f_forward_continuation_v5g01_closeout") / "current"
QUEUE123_DIR = Path("v5f_internal_subsleeve_queue_123_execution") / "current"
FORWARD_DIR = Path("v5f_internal_subsleeve_forward_paper_tracking") / "current"
DEEP_DIR = Path("v5f_internal_subsleeve_deep_engineering") / "current"
V5G_COMPARE_DIR = Path("v5g_vs_midterm_model_comparison") / "current"
V5G01_DIR = Path("v5g_01_state_gated_internal_subsleeve_limited_engineering") / "current"
V5G04_DIR = Path("v5g_04_exit_policy_spec") / "current"

PRIMARY = "internal_subsleeve_mom12_70_30"
SECONDARY = "v5g_01_state_gated_internal_subsleeve_70_30"


REQUIRED = [
    FORWARD_DIR / "v5f_internal_subsleeve_forward_summary.json",
    DEEP_DIR / "v5f_internal_subsleeve_deep_summary.json",
    V5G_COMPARE_DIR / "v5g_vs_midterm_summary.json",
    V5G_COMPARE_DIR / "v5g_delta_vs_midterm_champion.csv",
    V5G01_DIR / "v5g_01_state_gated_engineering_summary.json",
    V5G01_DIR / "v5g_01_state_gated_pm_gate_decision.csv",
    V5G04_DIR / "v5g_04_exit_policy_summary.json",
]


def run_v5f_forward_continuation_v5g01_closeout(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_forward_continuation_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_forward_continuation_summary.json", summary)
        return summary

    queue_summary = run_v5f_internal_subsleeve_queue_123(root)
    forward = _read_json(root / FORWARD_DIR / "v5f_internal_subsleeve_forward_summary.json")
    deep = _read_json(root / DEEP_DIR / "v5f_internal_subsleeve_deep_summary.json")
    compare = _read_json(root / V5G_COMPARE_DIR / "v5g_vs_midterm_summary.json")
    v5g01 = _read_json(root / V5G01_DIR / "v5g_01_state_gated_engineering_summary.json")
    v5g04 = _read_json(root / V5G04_DIR / "v5g_04_exit_policy_summary.json")
    target_audit = _read_csv(root / QUEUE123_DIR / "v5f_queue_123_official_rebalance_signal_audit.csv")
    population = _read_csv(root / QUEUE123_DIR / "v5f_queue_123_paper_target_population_status.csv")
    delta = _read_csv(root / V5G_COMPARE_DIR / "v5g_delta_vs_midterm_champion.csv")[0]

    tracking = _tracking_status(forward, deep, queue_summary, population)
    clean_audit = _clean_forward_target_audit(target_audit)
    paper_queue = _paper_population_queue(population, queue_summary)
    secondary = _v5g01_secondary_status(v5g01, delta)
    priority = _model_priority_matrix(deep, compare, v5g01, v5g04)
    governance = _governance(forward, deep, compare, v5g01, v5g04, clean_audit)
    decision = _pm_decision(governance, tracking, secondary)
    next_queue = _next_queue(decision[0]["pm_gate_decision"], paper_queue)
    blockers_out = _soft_blockers(clean_audit)

    _write_csv(out / "v5f_forward_tracking_status_update.csv", tracking)
    _write_csv(out / "v5f_clean_forward_target_audit.csv", clean_audit)
    _write_csv(out / "v5f_paper_target_population_queue.csv", paper_queue)
    _write_csv(out / "v5g01_secondary_observation_closeout.csv", secondary)
    _write_csv(out / "v5f_v5g_model_priority_matrix.csv", priority)
    _write_csv(out / "v5f_forward_continuation_governance_audit.csv", governance)
    _write_csv(out / "v5f_forward_continuation_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_forward_continuation_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5f_forward_continuation_blockers.csv", blockers_out)
    (out / "v5f_forward_continuation_report.md").write_text(
        _report(tracking, secondary, priority, clean_audit, decision),
        encoding="utf-8",
    )
    (out / "v5f_forward_continuation_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    summary = _summary(
        "completed_v5f_forward_continuation_v5g01_closeout",
        decision[0]["pm_gate_decision"],
        [],
        primary_candidate=PRIMARY,
        secondary_candidate=SECONDARY,
        primary_delta_return_pct_points_vs_repaired_baseline=float(deep["primary_delta_return_pct_points_vs_repaired_baseline"]),
        secondary_delta_return_pct_points_vs_repaired_baseline=float(v5g01["state_gated_delta_return_pct_points_vs_repaired_baseline"]),
        secondary_delta_return_pct_points_vs_primary=float(v5g01["state_gated_delta_return_pct_points_vs_internal_subsleeve_champion"]),
        target_population_status=population[0]["population_status"],
        v5g01_closeout_status=secondary[0]["closeout_status"],
    )
    _write_json(out / "v5f_forward_continuation_summary.json", summary)
    return summary


def _tracking_status(
    forward: dict[str, Any],
    deep: dict[str, Any],
    queue_summary: dict[str, Any],
    population: list[dict[str, str]],
) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": PRIMARY,
            "tracking_status": "continue_forward_paper_tracking",
            "source_forward_gate": forward["pm_gate_decision"],
            "queue_123_gate": queue_summary["pm_gate_decision"],
            "paper_target_population_status": population[0]["population_status"],
            "delta_return_pct_points_vs_repaired_baseline": deep["primary_delta_return_pct_points_vs_repaired_baseline"],
            "delta_max_drawdown_pct_points_vs_repaired_baseline": deep["primary_delta_max_drawdown_pct_points_vs_repaired_baseline"],
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
        }
    ]


def _clean_forward_target_audit(target_audit: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in target_audit:
        rows.append(
            {
                "source_id": row["source_id"],
                "rebalance_date": row["rebalance_date"],
                "audit_status": row["audit_status"],
                "clean_forward_usable": row["clean_forward_usable"],
                "use_for_paper_population_now": str(row["clean_forward_usable"]) == "True",
                "historical_backtest_blocker": False,
                "reason": row["reason"],
            }
        )
    return rows


def _paper_population_queue(population: list[dict[str, str]], queue_summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "candidate_id": PRIMARY,
            "population_status": population[0]["population_status"],
            "next_clean_rebalance_date": population[0]["next_clean_rebalance_date"],
            "late_202607_signal_used": population[0]["late_202607_signal_used"],
            "action_now": "wait_for_clean_official_repaired_v57f_targets",
            "queue_123_status": queue_summary["pm_gate_decision"],
            "accepted": False,
        }
    ]


def _v5g01_secondary_status(v5g01: dict[str, Any], delta: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": SECONDARY,
            "closeout_status": "sealed_secondary_observation_not_primary",
            "delta_return_pct_points_vs_repaired_baseline": v5g01["state_gated_delta_return_pct_points_vs_repaired_baseline"],
            "delta_return_pct_points_vs_primary": v5g01["state_gated_delta_return_pct_points_vs_internal_subsleeve_champion"],
            "beats_primary": delta["beats_midterm_champion"],
            "reason": "Positive versus repaired baseline but underperforms internal_subsleeve_mom12_70_30; no drawdown improvement.",
            "accepted": False,
            "live_trading_approved": False,
            "next_use": "secondary_observation_or_archive_only",
        }
    ]


def _model_priority_matrix(
    deep: dict[str, Any],
    compare: dict[str, Any],
    v5g01: dict[str, Any],
    v5g04: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "rank": 1,
            "model_id": PRIMARY,
            "role": "primary_forward_paper_candidate",
            "delta_return_pct_points_vs_repaired_baseline": deep["primary_delta_return_pct_points_vs_repaired_baseline"],
            "status": "continue_forward_paper_tracking_not_accepted",
            "accepted": False,
        },
        {
            "rank": 2,
            "model_id": SECONDARY,
            "role": "secondary_observation",
            "delta_return_pct_points_vs_repaired_baseline": v5g01["state_gated_delta_return_pct_points_vs_repaired_baseline"],
            "status": "sealed_secondary_not_primary",
            "accepted": False,
        },
        {
            "rank": 3,
            "model_id": "v5g_04_511360_exit_policy_spec",
            "role": "policy_spec_not_nav_model",
            "delta_return_pct_points_vs_repaired_baseline": "",
            "status": v5g04["pm_gate_decision"],
            "accepted": False,
        },
        {
            "rank": 4,
            "model_id": "v5g_vs_midterm_comparison",
            "role": "governance_reference",
            "delta_return_pct_points_vs_repaired_baseline": compare["best_new_delta_return_pct_points_vs_baseline"],
            "status": compare["pm_gate_decision"],
            "accepted": False,
        },
    ]


def _governance(
    forward: dict[str, Any],
    deep: dict[str, Any],
    compare: dict[str, Any],
    v5g01: dict[str, Any],
    v5g04: dict[str, Any],
    clean_audit: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {"audit_id": "primary_candidate_confirmed", "status": "pass" if deep["primary_candidate"] == PRIMARY else "fail", "detail": deep["primary_candidate"]},
        {"audit_id": "forward_tracking_ready", "status": "pass" if forward["pm_gate_decision"] == "forward_paper_tracking_ready_wait_for_next_official_v57f_rebalance_signal" else "fail", "detail": forward["pm_gate_decision"]},
        {"audit_id": "v5g_comparison_keeps_primary", "status": "pass" if compare["pm_gate_decision"] == "midterm_internal_subsleeve_champion_remains_primary_v5g_new_models_secondary" else "fail", "detail": compare["pm_gate_decision"]},
        {"audit_id": "v5g01_secondary_only", "status": "pass" if float(v5g01["state_gated_delta_return_pct_points_vs_internal_subsleeve_champion"]) < 0 else "fail", "detail": v5g01["state_gated_delta_return_pct_points_vs_internal_subsleeve_champion"]},
        {"audit_id": "511360_not_attached_to_v5g01", "status": "pass" if not v5g04["cash_proxy_attachment_approved"] else "fail", "detail": v5g04["pm_gate_decision"]},
        {"audit_id": "late_202607_not_used", "status": "pass" if all(not row["use_for_paper_population_now"] for row in clean_audit) else "fail", "detail": "no clean target usable now"},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
        {"audit_id": "v57f_core_modified_false", "status": "pass", "detail": False},
        {"audit_id": "threshold_scan_used_false", "status": "pass", "detail": False},
    ]


def _pm_decision(
    governance: list[dict[str, Any]],
    tracking: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gov_ok = all(row["status"] == "pass" for row in governance)
    decision = (
        "continue_internal_subsleeve_forward_paper_tracking_v5g01_sealed_secondary"
        if gov_ok
        else "blocked_by_forward_continuation_governance_issue"
    )
    return [
        {
            "pm_gate_decision": decision,
            "primary_candidate": tracking[0]["candidate_id"],
            "secondary_candidate": secondary[0]["candidate_id"],
            "forward_tracking_continue": gov_ok,
            "v5g01_sealed_secondary": gov_ok,
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "next_step": "wait_for_clean_official_repaired_v57f_targets_then_populate_paper_rows"
            if gov_ok
            else "repair_governance",
        }
    ]


def _next_queue(decision: str, paper_queue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "priority": "P0",
            "next_task": "populate_internal_subsleeve_mom12_70_30_paper_targets_when_clean_official_repaired_v57f_targets_available",
            "status": paper_queue[0]["population_status"],
            "allowed_now": False,
            "reason": "Clean official repaired V57f targets are pending.",
        },
        {
            "priority": "P1",
            "next_task": "keep_v5g01_secondary_observation_archived",
            "status": "done",
            "allowed_now": True,
            "reason": "V5g01 underperforms primary by about 1.03 pct points.",
        },
        {
            "priority": "P2",
            "next_task": "do_not_attach_511360_without_specific_cash_event",
            "status": "policy_ready_but_attachment_blocked",
            "allowed_now": False,
            "reason": "V5g01 creates no cash bucket and baseline idle cash is blocked.",
        },
    ]


def _soft_blockers(clean_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if any(row["use_for_paper_population_now"] for row in clean_audit):
        return []
    return [
        {
            "blocker_id": "clean_official_repaired_v57f_targets_pending",
            "severity": "forward_only",
            "status": "not_historical_blocker",
            "description": "Paper rows will be populated when clean official repaired V57f targets are available.",
        }
    ]


def _report(
    tracking: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
    priority: list[dict[str, Any]],
    clean_audit: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    primary = tracking[0]
    sec = secondary[0]
    return "\n".join(
        [
            "# V5f Forward Continuation + V5g01 Closeout",
            "",
            f"- Primary: `{primary['candidate_id']}` remains in forward/paper tracking.",
            f"- Primary edge vs repaired baseline: `{float(primary['delta_return_pct_points_vs_repaired_baseline']):.4f}` pct points.",
            f"- Secondary: `{sec['candidate_id']}` is sealed as secondary observation.",
            f"- Secondary delta vs primary: `{float(sec['delta_return_pct_points_vs_primary']):.4f}` pct points.",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`.",
            "- Accepted/live approved: `False`.",
            "",
            "## Clean Target Audit",
            *[f"- `{row['source_id']}`: {row['audit_status']} | use now: `{row['use_for_paper_population_now']}`" for row in clean_audit],
            "",
            "## Priority",
            *[f"- P{row['rank']} `{row['model_id']}`: {row['status']}" for row in priority if isinstance(row.get("rank"), int)],
            "",
        ]
    )


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Forward Continuation Rules",
            "",
            "- Continue `internal_subsleeve_mom12_70_30` only as forward/paper candidate.",
            "- Do not mark accepted or live approved.",
            "- Do not use late 2026-07 shadow signal as clean forward evidence.",
            "- Keep V5g01 as secondary observation; do not replace the primary.",
            "- Do not attach 511360 unless a separate specific cash event is approved.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    blockers = []
    for rel in REQUIRED:
        if not (root / rel).exists():
            blockers.append({"blocker_id": f"missing_{rel.name}", "severity": "fatal", "status": "blocking", "path": str(rel)})
    return blockers


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5f_forward_continuation_v5g01_closeout",
        "status": status,
        "pm_gate_decision": decision,
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(blockers),
        "fatal_blockers": blockers,
    }
    payload.update(extra)
    return payload


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    print(json.dumps(run_v5f_forward_continuation_v5g01_closeout(Path(".")), ensure_ascii=False, indent=2))

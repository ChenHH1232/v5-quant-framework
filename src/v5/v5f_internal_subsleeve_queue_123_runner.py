from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5f_internal_subsleeve_queue_123_execution") / "current"
DEPLOY_DIR = Path("v5f_internal_subsleeve_deployment_governance") / "current"
REPLACEMENT_DIR = Path("v5f_internal_subsleeve_candidate_replacement_packet") / "current"
FORWARD_DIR = Path("v5f_internal_subsleeve_forward_paper_tracking") / "current"
PREFLIGHT_DIR = Path("paper_input_preflight_checks_v57f") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
V57F_PAPER_SIGNAL_DIR = Path("paper_trading_signals") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f" / "2026-07-19"
V5C_DIR = Path("v5c_erc_forward_paper_tracking") / "current"
V5E_511360_DIR = Path("v5e_511360_forward_paper_tracking") / "current"
V5E_511360_REVIEW_DIR = Path("v5e_511360_cash_proxy_pm_quant_review") / "current"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_internal_subsleeve_queue_123(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_queue_123_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_queue_123_summary.json", summary)
        return summary

    deployment = _read_json(root / DEPLOY_DIR / "v5f_internal_subsleeve_deployment_summary.json")
    replacement = _read_json(root / REPLACEMENT_DIR / "v5f_candidate_replacement_summary.json")
    forward = _read_json(root / FORWARD_DIR / "v5f_internal_subsleeve_forward_summary.json")
    preflight = _read_json(root / PREFLIGHT_DIR / "paper_input_preflight_summary.json")
    paper_signal = _read_json(root / V57F_PAPER_SIGNAL_DIR / "basket_construction_summary.json")
    v5c = _read_json(root / V5C_DIR / "v5c_erc_forward_paper_tracking_summary.json")
    v5e_forward = _read_json(root / V5E_511360_DIR / "v5e_511360_forward_tracking_summary.json")
    v5e_review = _read_json(root / V5E_511360_REVIEW_DIR / "v5e_511360_pm_quant_review_summary.json")

    target_audit = _official_target_audit(preflight, paper_signal)
    paper_target_status = _paper_target_population_status(deployment, target_audit)
    input_queue = _required_input_queue(preflight)
    signal_template = _paper_target_template(deployment, preflight)
    closeout_framework = _forward_closeout_framework(deployment, forward)
    closeout_status = _forward_closeout_status(target_audit)
    conflict_matrix = _combined_conflict_matrix(v5c, v5e_forward, v5e_review)
    component_sequence = _component_sequence()
    pm_decision = _pm_decision(target_audit, conflict_matrix, deployment, replacement)
    next_queue = _next_queue(pm_decision[0]["pm_gate_decision"])
    blockers_out = _blockers(target_audit, conflict_matrix)

    _write_csv(out / "v5f_queue_123_official_rebalance_signal_audit.csv", target_audit)
    _write_csv(out / "v5f_queue_123_paper_target_population_status.csv", paper_target_status)
    _write_csv(out / "v5f_queue_123_required_input_queue.csv", input_queue)
    _write_csv(out / "v5f_queue_123_paper_target_template.csv", signal_template)
    _write_csv(out / "v5f_queue_123_forward_evidence_closeout_framework.csv", closeout_framework)
    _write_csv(out / "v5f_queue_123_forward_closeout_status.csv", closeout_status)
    _write_csv(out / "v5f_queue_123_v5c_v5e_conflict_matrix.csv", conflict_matrix)
    _write_csv(out / "v5f_queue_123_component_sequence.csv", component_sequence)
    _write_csv(out / "v5f_queue_123_pm_decision.csv", pm_decision)
    _write_csv(out / "v5f_queue_123_next_queue.csv", next_queue)
    _write_csv(out / "v5f_queue_123_blockers.csv", blockers_out)
    (out / "v5f_queue_123_report.md").write_text(
        _report(deployment, replacement, target_audit, pm_decision),
        encoding="utf-8",
    )
    (out / "v5f_queue_123_next_prompt.md").write_text(_next_prompt(preflight), encoding="utf-8")
    (out / "v5f_queue_123_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    summary = _summary(
        status="completed_v5f_internal_subsleeve_queue_123_execution",
        decision=pm_decision[0]["pm_gate_decision"],
        fatal_blockers=[],
        primary_candidate=deployment["primary_candidate"],
        delta_return=float(deployment["delta_return_pct_points_vs_repaired_baseline"]),
        incremental_delta_return=float(deployment["incremental_delta_return_vs_prior_primary"]),
        target_population_status=paper_target_status[0]["population_status"],
    )
    _write_json(out / "v5f_queue_123_summary.json", summary)
    return summary


def _official_target_audit(preflight: dict[str, Any], paper_signal: dict[str, Any]) -> list[dict[str, Any]]:
    target_date = preflight["target_rebalance_date"]
    late_signal_date = "2026-07-01"
    late_signal_created = paper_signal["created_at_utc"][:10]
    late_is_clean = late_signal_created <= late_signal_date
    return [
        {
            "source_id": "paper_input_preflight_20261008",
            "source_path": str(PREFLIGHT_DIR / "paper_input_preflight_summary.json"),
            "rebalance_date": target_date,
            "source_status": preflight["status"],
            "target_date_is_future": preflight["target_date_is_future"],
            "target_panel_rows_available": False,
            "official_repaired_targets_available": False,
            "clean_forward_usable": False,
            "audit_status": "forward_only_pending",
            "reason": "Target date is still in the future and target rows are not available yet.",
        },
        {
            "source_id": "late_shadow_signal_20260701",
            "source_path": str(V57F_PAPER_SIGNAL_DIR / "basket_rebalance_signals.csv"),
            "rebalance_date": late_signal_date,
            "source_status": paper_signal["pm_rule"],
            "target_date_is_future": False,
            "target_panel_rows_available": True,
            "official_repaired_targets_available": True,
            "clean_forward_usable": late_is_clean,
            "audit_status": "reference_only_not_clean_forward" if not late_is_clean else "clean_forward_usable",
            "reason": "Signal was generated after the 2026-07-01 rebalance date, so it cannot be used as clean forward evidence.",
        },
    ]


def _paper_target_population_status(deployment: dict[str, Any], audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clean_available = any(row["clean_forward_usable"] is True for row in audit)
    return [
        {
            "candidate_id": deployment["primary_candidate"],
            "requested_queue_item": "1_populate_paper_targets",
            "population_status": "not_populated_waiting_next_clean_official_repaired_v57f_targets"
            if not clean_available
            else "ready_to_populate",
            "next_clean_rebalance_date": "2026-10-08",
            "late_202607_signal_used": False,
            "accepted": False,
            "live_trading_approved": False,
            "reason": "No clean official repaired target table is available for population yet."
            if not clean_available
            else "Clean target table exists.",
        }
    ]


def _required_input_queue(preflight: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for sector in preflight["sector_checks"]:
        rows.append(
            {
                "priority": len(rows) + 1,
                "target_rebalance_date": preflight["target_rebalance_date"],
                "sector_id": sector["sector_id"],
                "required_input": "fresh PIT panel rows and prices through prior trading date",
                "latest_panel_trade_date": sector["latest_panel_trade_date"],
                "latest_price_date": sector["latest_price_date"],
                "target_panel_rows": sector["target_panel_rows"],
                "price_reaches_prior_trading_date": sector["price_reaches_prior_trading_date"],
                "status": sector["status"],
            }
        )
    return rows


def _paper_target_template(deployment: dict[str, Any], preflight: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "rebalance_date": preflight["target_rebalance_date"],
            "candidate_id": deployment["primary_candidate"],
            "code": "TBD_official_repaired_v57f_target",
            "sleeve_id": "TBD",
            "base_target_weight": "TBD",
            "mom_12_1_rank_within_sleeve": "TBD",
            "mom_12_1_bucket": "TBD_top_middle_bottom",
            "overlay_target_weight": "TBD_70pct_core_plus_30pct_same_sleeve_momentum",
            "sleeve_weight_preserved": "must_be_true",
            "paper_only": True,
            "accepted": False,
        }
    ]


def _forward_closeout_framework(deployment: dict[str, Any], forward: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "closeout_step": "load_paper_targets",
            "candidate_id": deployment["primary_candidate"],
            "status_now": "pending_targets",
            "pass_condition": "official repaired V57f target table exists and overlay target rows are populated",
        },
        {
            "closeout_step": "observe_forward_window",
            "candidate_id": deployment["primary_candidate"],
            "status_now": "not_started",
            "pass_condition": "forward daily NAV/holding comparison exists after observation window",
        },
        {
            "closeout_step": "compare_vs_repaired_v57f",
            "candidate_id": deployment["primary_candidate"],
            "status_now": forward["pm_gate_decision"],
            "pass_condition": "paper overlay edge persists without governance violations",
        },
        {
            "closeout_step": "pm_quant_closeout",
            "candidate_id": deployment["primary_candidate"],
            "status_now": "framework_ready",
            "pass_condition": "PM/Quant review keeps accepted=false unless separately approved",
        },
    ]


def _forward_closeout_status(audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clean_available = any(row["clean_forward_usable"] is True for row in audit)
    return [
        {
            "queue_item": "2_forward_evidence_closeout",
            "status": "framework_created_waiting_forward_evidence"
            if not clean_available
            else "ready_after_target_population",
            "evidence_available_now": False,
            "blocks_historical_candidate": False,
            "accepted": False,
        }
    ]


def _combined_conflict_matrix(v5c: dict[str, Any], v5e_forward: dict[str, Any], v5e_review: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "component": "V5f_internal_subsleeve_mom12_70_30",
            "scope": "inside-sleeve stock weighting",
            "interaction": "primary candidate for paper only",
            "conflict_status": "clean_standalone",
            "requires_separate_combined_backtest": False,
            "accepted": False,
        },
        {
            "component": "V5c_ERC",
            "scope": "sleeve-level risk weight overlay",
            "interaction": v5c.get("pm_gate_decision") or v5c.get("current_tracking_status") or v5c.get("status"),
            "conflict_status": "separate_review_required_before_combination",
            "requires_separate_combined_backtest": True,
            "accepted": False,
        },
        {
            "component": "V5e_511360_cash_proxy",
            "scope": "cash proxy after V5e profit-lock exit",
            "interaction": v5e_forward["pm_gate_decision"],
            "conflict_status": "separate_review_required_before_combination",
            "requires_separate_combined_backtest": True,
            "accepted": v5e_review["accepted"],
        },
        {
            "component": "V5e_profit_lock",
            "scope": "holding-period exit overlay",
            "interaction": "separate line; should not be bundled into V5f target generation",
            "conflict_status": "keep_separate_until_forward_evidence",
            "requires_separate_combined_backtest": True,
            "accepted": False,
        },
    ]


def _component_sequence() -> list[dict[str, Any]]:
    return [
        {"sequence": 1, "component": "V57f repaired baseline", "action": "load official target list", "allowed_now": False, "reason": "next clean target is future/pending"},
        {"sequence": 2, "component": "V5f internal sub-sleeve", "action": "compute paper overlay weights", "allowed_now": False, "reason": "requires step 1"},
        {"sequence": 3, "component": "V5c/ERC", "action": "combined review only", "allowed_now": True, "reason": "do not combine into live/paper target without separate packet"},
        {"sequence": 4, "component": "V5e 511360 cash proxy", "action": "combined review only", "allowed_now": True, "reason": "official restore still unavailable"},
    ]


def _pm_decision(
    audit: list[dict[str, Any]],
    conflict_matrix: list[dict[str, Any]],
    deployment: dict[str, Any],
    replacement: dict[str, Any],
) -> list[dict[str, Any]]:
    clean_available = any(row["clean_forward_usable"] is True for row in audit)
    hard_conflict = any(row["conflict_status"] == "blocked" for row in conflict_matrix)
    if hard_conflict:
        decision = "blocked_by_combined_conflict"
    elif clean_available:
        decision = "paper_target_population_ready_then_forward_closeout"
    else:
        decision = "queue_123_completed_forward_targets_pending_combined_review_ready"
    return [
        {
            "pm_gate_decision": decision,
            "primary_candidate": deployment["primary_candidate"],
            "candidate_replacement_decision": replacement["pm_gate_decision"],
            "target_population_ready_now": clean_available,
            "combined_conflict_review_completed": True,
            "accepted": False,
            "live_trading_approved": False,
            "rationale": "Queue 1 is pending the next clean official repaired V57f target; queues 2 and 3 are prepared/completed at governance level.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "task": "Wait until 2026-10-08 clean V57f paper input refresh window, then populate internal_subsleeve_mom12_70_30 paper targets",
            "allowed": True,
            "requires_user_approval": False,
        },
        {
            "priority": 2,
            "task": "After target population, run forward evidence closeout framework",
            "allowed": True,
            "requires_user_approval": False,
        },
        {
            "priority": 3,
            "task": "Open separate combined packet only if PM wants V5f + V5c/ERC or V5f + V5e/511360 interaction tested",
            "allowed": decision != "blocked_by_combined_conflict",
            "requires_user_approval": False,
        },
        {
            "priority": 4,
            "task": "Accepted/live approval",
            "allowed": False,
            "requires_user_approval": True,
        },
    ]


def _blockers(audit: list[dict[str, Any]], conflict_matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {
            "blocker_id": "next_clean_official_repaired_v57f_target_pending",
            "severity": "forward_only",
            "status": "not_historical_blocker",
            "description": "No clean official repaired target rows are available now; 2026-10-08 remains the next clean paper window.",
        }
    ]
    for row in conflict_matrix:
        if row["conflict_status"] == "blocked":
            rows.append(
                {
                    "blocker_id": f"{row['component']}_conflict",
                    "severity": "fatal",
                    "status": "blocking",
                    "description": row["interaction"],
                }
            )
    return rows


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    primary_candidate: str = "",
    delta_return: float = 0.0,
    incremental_delta_return: float = 0.0,
    target_population_status: str = "",
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_internal_subsleeve_queue_123_execution",
        "status": status,
        "pm_gate_decision": decision,
        "primary_candidate": primary_candidate,
        "delta_return_pct_points_vs_repaired_baseline": delta_return,
        "incremental_delta_return_vs_prior_primary": incremental_delta_return,
        "target_population_status": target_population_status,
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


def _report(
    deployment: dict[str, Any],
    replacement: dict[str, Any],
    audit: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    return "\n".join(
        [
            "# V5f Internal Sub-Sleeve Queue 1/2/3 Execution",
            "",
            f"- Primary candidate: `{deployment['primary_candidate']}`",
            f"- Candidate replacement: `{replacement['pm_gate_decision']}`",
            f"- Return edge vs repaired V57f: {float(deployment['delta_return_pct_points_vs_repaired_baseline']):.4f} pct points.",
            f"- Incremental edge vs prior equal-blend: {float(deployment['incremental_delta_return_vs_prior_primary']):.4f} pct points.",
            f"- PM decision: `{decision[0]['pm_gate_decision']}`",
            "- Accepted: `False`; live approved: `False`.",
            "",
            "## Target Audit",
            *[f"- {row['source_id']}: {row['audit_status']} | {row['reason']}" for row in audit],
            "",
        ]
    )


def _next_prompt(preflight: dict[str, Any]) -> str:
    return f"""Working directory:
D:\\hh\\codex\\v5

Task name:
V5f internal_subsleeve_mom12_70_30 clean paper target population

Objective:
When the clean official startup-preload repaired V57f target table for `{preflight["target_rebalance_date"]}` is available, populate V5f `internal_subsleeve_mom12_70_30` paper target weights. Do not use late 2026-07 shadow signals as clean forward evidence. Do not modify V57f, do not scan parameters, do not mark accepted/live approved.
"""


def _rules() -> str:
    return "\n".join(
        [
            "# V5f Queue 1/2/3 Execution Rules",
            "",
            "- Use startup preload repaired V57f targets only.",
            "- 2026-07 late/shadow signal may be reference only, not clean forward evidence.",
            "- No V57f modification, no parameter scan, no full-market selection.",
            "- V5c/ERC and V5e/511360 require separate combined review before any merged use.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        DEPLOY_DIR / "v5f_internal_subsleeve_deployment_summary.json",
        REPLACEMENT_DIR / "v5f_candidate_replacement_summary.json",
        FORWARD_DIR / "v5f_internal_subsleeve_forward_summary.json",
        PREFLIGHT_DIR / "paper_input_preflight_summary.json",
        V57F_PAPER_SIGNAL_DIR / "basket_construction_summary.json",
        V57F_PAPER_SIGNAL_DIR / "basket_rebalance_signals.csv",
        V5C_DIR / "v5c_erc_forward_paper_tracking_summary.json",
        V5E_511360_DIR / "v5e_511360_forward_tracking_summary.json",
        V5E_511360_REVIEW_DIR / "v5e_511360_pm_quant_review_summary.json",
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
    print(json.dumps(run_v5f_internal_subsleeve_queue_123(Path(".")), ensure_ascii=False, indent=2))

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5f_momentum_weight_tilt_forward_paper_tracking") / "current"
REVIEW_DIR = Path("v5f_momentum_weight_tilt_pm_quant_review") / "current"
ENG_DIR = Path("v5f_momentum_weight_tilt_limited_engineering") / "current"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_momentum_weight_tilt_forward_tracking(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5f_momentum_weight_tilt_forward_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5f_momentum_weight_tilt_forward_summary.json", summary)
        return summary

    review_summary = _read_json(root / REVIEW_DIR / "v5f_momentum_weight_tilt_pm_quant_summary.json")
    review_decision = _read_csv(root / REVIEW_DIR / "v5f_momentum_weight_tilt_pm_gate_decision.csv")[0]
    metrics = _read_csv(root / ENG_DIR / "v5f_momentum_weight_tilt_metrics.csv")

    candidate_status = _candidate_status(review_summary, review_decision)
    tracking_schema = _tracking_schema()
    checklist = _rebalance_day_checklist()
    signal_template = _paper_signal_template()
    governance = _governance_audit(review_summary, review_decision)
    queue = _next_queue()
    blockers_out = [{"blocker_id": "future_official_rebalance_signal_pending", "severity": "forward_only", "status": "not_backtest_blocker", "description": "Forward/paper signal can be evaluated when the next official V57f rebalance target file is available."}]

    _write_csv(out / "v5f_momentum_weight_tilt_forward_candidate_status.csv", candidate_status)
    _write_csv(out / "v5f_momentum_weight_tilt_forward_tracking_schema.csv", tracking_schema)
    _write_csv(out / "v5f_momentum_weight_tilt_rebalance_day_checklist.csv", checklist)
    _write_csv(out / "v5f_momentum_weight_tilt_paper_signal_template.csv", signal_template)
    _write_csv(out / "v5f_momentum_weight_tilt_forward_governance_audit.csv", governance)
    _write_csv(out / "v5f_momentum_weight_tilt_forward_next_queue.csv", queue)
    _write_csv(out / "v5f_momentum_weight_tilt_forward_blockers.csv", blockers_out)
    (out / "v5f_momentum_weight_tilt_forward_report.md").write_text(_report(review_summary, metrics), encoding="utf-8")
    (out / "v5f_momentum_weight_tilt_forward_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    summary = _summary(
        "completed_v5f_momentum_weight_tilt_forward_paper_tracking_packet",
        "forward_paper_tracking_ready_wait_for_next_official_v57f_rebalance_signal",
        [],
        primary_delta_return_pct_points=float(review_summary["primary_delta_return_pct_points_vs_baseline_proxy"]),
        primary_delta_max_drawdown_pct_points=float(review_summary["primary_delta_max_drawdown_pct_points_vs_baseline_proxy"]),
    )
    _write_json(out / "v5f_momentum_weight_tilt_forward_summary.json", summary)
    return summary


def _candidate_status(review_summary: dict[str, Any], review_decision: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": "mom_12_1_sleeve_tilt_10pct",
            "source_pm_gate": review_decision["pm_gate_decision"],
            "status": "forward_paper_tracking_ready_not_accepted",
            "primary_delta_return_pct_points_vs_baseline_proxy": review_summary["primary_delta_return_pct_points_vs_baseline_proxy"],
            "primary_delta_max_drawdown_pct_points_vs_baseline_proxy": review_summary["primary_delta_max_drawdown_pct_points_vs_baseline_proxy"],
            "accepted": False,
            "live_trading_approved": False,
        }
    ]


def _tracking_schema() -> list[dict[str, Any]]:
    fields = [
        ("rebalance_date", "official V57f rebalance date"),
        ("code", "V57f selected stock only"),
        ("sleeve", "original V57f sleeve"),
        ("base_target_weight", "V57f target before tilt"),
        ("mom_12_1", "12 month momentum skipping recent 1 month / 20 trading days"),
        ("sleeve_mean_momentum", "same sleeve selected-stock mean"),
        ("momentum_bucket", "top / middle / bottom tercile"),
        ("tilt_multiplier", "fixed 1.10 / 1.00 / 0.90"),
        ("tilted_target_weight", "normalized within same sleeve"),
        ("sleeve_weight_preserved", "must be true"),
        ("new_stock_selected", "must be false"),
        ("paper_only_status", "not live approved"),
    ]
    return [{"field": field, "definition": definition} for field, definition in fields]


def _rebalance_day_checklist() -> list[dict[str, Any]]:
    return [
        {"step_id": "load_official_v57f_targets", "required": True, "pass_condition": "official target file exists and is inside forward/paper workflow"},
        {"step_id": "compute_mom_12_1", "required": True, "pass_condition": "uses only prices visible before rebalance decision"},
        {"step_id": "rank_within_sleeve", "required": True, "pass_condition": "no cross-sleeve comparison for tilt"},
        {"step_id": "apply_fixed_multiplier", "required": True, "pass_condition": "top=1.10 middle=1.00 bottom=0.90"},
        {"step_id": "normalize_same_sleeve", "required": True, "pass_condition": "sleeve total target weight unchanged"},
        {"step_id": "audit_new_stocks", "required": True, "pass_condition": "zero stocks outside official V57f selected set"},
        {"step_id": "paper_tracking_only", "required": True, "pass_condition": "accepted=false and live_trading_approved=false"},
    ]


def _paper_signal_template() -> list[dict[str, Any]]:
    return [
        {
            "rebalance_date": "TBD_next_official_v57f_rebalance",
            "candidate_id": "mom_12_1_sleeve_tilt_10pct",
            "signal_status": "pending_official_v57f_targets",
            "action_scope": "paper_tracking_only",
            "allowed_trade_path_change": False,
            "notes": "Populate one row per V57f selected stock when the next official rebalance target file is available.",
        }
    ]


def _governance_audit(review_summary: dict[str, Any], review_decision: dict[str, str]) -> list[dict[str, Any]]:
    checks = [
        ("review_gate_promoted", review_decision["pm_gate_decision"] == "promote_momentum_weight_tilt_to_forward_paper_candidate_not_accepted", review_decision["pm_gate_decision"]),
        ("accepted_false", not review_summary.get("accepted"), review_summary.get("accepted")),
        ("live_trading_approved_false", not review_summary.get("live_trading_approved"), review_summary.get("live_trading_approved")),
        ("v57f_core_modified_false", not review_summary.get("v57f_core_modified"), review_summary.get("v57f_core_modified")),
        ("threshold_scan_false", not review_summary.get("threshold_scan_used"), review_summary.get("threshold_scan_used")),
        ("new_buy_signal_false", not review_summary.get("new_buy_signal_used"), review_summary.get("new_buy_signal_used")),
    ]
    return [{"check_id": check_id, "status": "pass" if ok else "fail", "detail": detail} for check_id, ok, detail in checks]


def _next_queue() -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task": "Wait for next official V57f rebalance target file, then populate paper signal table", "allowed": True, "requires_external_data": False},
        {"priority": 2, "task": "Run deployment governance review before any simulated/live use", "allowed": True, "requires_external_data": False},
        {"priority": 3, "task": "Compare paper tilt vs un-tilted V57f after next rebalance observation window", "allowed": True, "requires_external_data": False},
        {"priority": 4, "task": "Change momentum window or tilt size", "allowed": False, "requires_external_data": False},
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    primary_delta_return_pct_points: float = 0.0,
    primary_delta_max_drawdown_pct_points: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5f_momentum_weight_tilt_forward_paper_tracking",
        "status": status,
        "pm_gate_decision": decision,
        "candidate_id": "mom_12_1_sleeve_tilt_10pct",
        "primary_delta_return_pct_points_vs_baseline_proxy": primary_delta_return_pct_points,
        "primary_delta_max_drawdown_pct_points_vs_baseline_proxy": primary_delta_max_drawdown_pct_points,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "new_buy_signal_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(review_summary: dict[str, Any], metrics: list[dict[str, str]]) -> str:
    primary = next(row for row in metrics if row["version_id"] == "mom_12_1_sleeve_tilt_10pct")
    return "\n".join(
        [
            "# V5f Momentum Weight Tilt Forward/Paper Tracking",
            "",
            "- Candidate: `mom_12_1_sleeve_tilt_10pct`",
            "- Status: forward/paper tracking ready; not accepted; not live approved.",
            f"- Historical proxy delta return: {float(primary['delta_return_pct_points_vs_baseline_proxy']):.4f} pct points vs V57f baseline proxy.",
            f"- Historical proxy max drawdown delta: {float(primary['delta_max_drawdown_pct_points_vs_baseline_proxy']):.4f} pct points.",
            "- Next action: wait for the next official V57f rebalance target file, then populate paper signal rows.",
            "",
            "## Boundary",
            "- Do not add stocks.",
            "- Do not change sleeve total weights.",
            "- Do not scan windows or tilt size.",
            "- Do not reopen V5e exit/delay-sell acceptance.",
            "",
            f"Source review gate: `{review_summary['pm_gate_decision']}`.",
            "",
        ]
    )


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5f Momentum Weight Tilt Forward Rules",
            "",
            "- Paper tracking only.",
            "- Use only official V57f rebalance targets.",
            "- Fixed 12-1 momentum, fixed 10% top/bottom tilt.",
            "- Preserve sleeve total weights.",
            "- No accepted or live status.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        REVIEW_DIR / "v5f_momentum_weight_tilt_pm_quant_summary.json",
        REVIEW_DIR / "v5f_momentum_weight_tilt_pm_gate_decision.csv",
        ENG_DIR / "v5f_momentum_weight_tilt_metrics.csv",
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
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    print(json.dumps(run_v5f_momentum_weight_tilt_forward_tracking(Path(".")), ensure_ascii=False, indent=2))

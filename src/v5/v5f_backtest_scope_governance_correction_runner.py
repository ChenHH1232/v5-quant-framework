from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5f_backtest_scope_governance_correction") / "current"
BACKTEST_SCOPE_START = "2021-05-01"
REPAIRED_FIRST_TRADE = "2021-05-06"
BACKTEST_SCOPE_END = "2026-05-31"
PRE2021_CUTOFF = "2021-05-01"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5f_backtest_scope_governance_correction(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    rulebook = _rulebook()
    v5f = _v5f_component_reclassification(root)
    v4 = _v4_component_reclassification()
    violations = _violation_audit(v5f, v4)
    decision = _decision(v5f, v4, violations)
    next_queue = _next_queue()

    _write_csv(out / "v5f_evidence_scope_rulebook.csv", rulebook)
    _write_csv(out / "v5f_component_scope_reclassification.csv", v5f)
    _write_csv(out / "v4_component_scope_reclassification.csv", v4)
    _write_csv(out / "v4_v5_scope_violation_audit.csv", violations)
    _write_csv(out / "v5f_corrected_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_backtest_scope_next_queue.csv", next_queue)
    _write_csv(out / "v5f_backtest_scope_blockers.csv", [])
    (out / "v5f_backtest_scope_governance_correction_report.md").write_text(
        _report(v5f, v4, violations, decision),
        encoding="utf-8",
    )
    (out / "v5f_backtest_scope_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    summary = {
        "created_at_utc": now_utc(),
        "task": "v5f_backtest_scope_governance_correction",
        "status": "completed_backtest_scope_governance_correction",
        "backtest_scope_start": BACKTEST_SCOPE_START,
        "repaired_first_trade": REPAIRED_FIRST_TRADE,
        "backtest_scope_end": BACKTEST_SCOPE_END,
        "global_rule": "2021-05-01_to_2026-05-31_is_historical_backtest_not_oos_validation",
        "prior_momentum_scope_violation": "label_and_evidence_grade_violation_where_2021_2026_was_called_validation_or_oos",
        "prior_mean_reversion_scope_violation": "label_and_evidence_grade_violation_where_2021_2026_was_called_validation_or_oos",
        "v5f_momentum_corrected_status": "historical_backtest_candidate_not_accepted_requires_forward_paper",
        "v5f_mean_reversion_corrected_status": "historical_backtest_diagnostic_only",
        "v5f_short_window_corrected_status": "historical_backtest_internal_diagnostic_only_not_walk_forward_validation",
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "fatal_blocker_count": 0,
    }
    _write_json(out / "v5f_backtest_scope_correction_summary.json", summary)
    return summary


def _rulebook() -> list[dict[str, Any]]:
    return [
        {
            "scope_id": "pre2021_research_reserve",
            "date_range": f"before_{PRE2021_CUTOFF}",
            "allowed_label": "research_train_validation_or_predecessor_proxy_if_pit_clean",
            "forbidden_label": "V57f_repaired_direct_oos_unless_exact_repaired_pool_exists",
            "use_policy": "Can select rules or explain mechanisms before entering 2021-2026 backtest.",
        },
        {
            "scope_id": "v57f_repaired_historical_backtest",
            "date_range": f"{BACKTEST_SCOPE_START}_to_{BACKTEST_SCOPE_END}",
            "allowed_label": "historical_backtest_engineering_diagnostic",
            "forbidden_label": "out_of_sample_or_formal_rolling_validation",
            "use_policy": "Can compare models, cannot be used repeatedly as validation after rule search.",
        },
        {
            "scope_id": "post_backtest_forward_paper",
            "date_range": f"after_{BACKTEST_SCOPE_END}",
            "allowed_label": "forward_paper_or_live_shadow_tracking",
            "forbidden_label": "historical_backtest",
            "use_policy": "Only this future window can provide clean forward evidence after rules are frozen.",
        },
    ]


def _v5f_component_reclassification(root: Path) -> list[dict[str, Any]]:
    components = [
        (
            "v5f_internal_subsleeve_mom12_70_30",
            "v5f_internal_subsleeve_deep_engineering/current/v5f_internal_subsleeve_deep_summary.json",
            "momentum",
            "promote_internal_subsleeve_70_30_to_v5f_candidate_not_accepted",
            "historical_backtest_candidate_not_accepted_requires_forward_paper",
            "Backtest result is useful, but not OOS validation.",
        ),
        (
            "v5f_quality_value_mean_reversion",
            "v5f_quality_value_mean_reversion/current/v5f_qv_mean_reversion_summary.json",
            "mean_reversion",
            "qv_mean_reversion_diagnostic_only_keep_champion_primary",
            "historical_backtest_diagnostic_only",
            "Mean reversion failed against momentum champion in the backtest window; no acceptance issue.",
        ),
        (
            "v5f_v57f_qv_mr_combination",
            "v5f_v57f_qv_mr_combination/current/v5f_v57f_qv_mr_combination_summary.json",
            "momentum_plus_mean_reversion",
            "combo_diagnostic_only_keep_momentum_primary",
            "historical_backtest_diagnostic_only",
            "Combination did not beat momentum champion; only backtest diagnostic evidence.",
        ),
        (
            "v5f_short_window_reversion_nav",
            "v5f_short_window_reversion_nav_engineering/current/v5f_short_window_reversion_nav_summary.json",
            "short_window_mean_reversion",
            "promote_short_window_reversion_to_pm_quant_review_not_accepted",
            "historical_backtest_diagnostic_only_not_candidate",
            "Positive result came from 2021-2026 backtest internals; cannot be promoted without pre-2021 or future evidence.",
        ),
        (
            "v5f_short_window_spike_reversion",
            "v5f_short_window_spike_reversion_symmetry/current/v5f_short_window_spike_reversion_summary.json",
            "short_window_spike_reversion",
            "diagnostic_positive_ready_for_pm_quant_review_not_accepted",
            "historical_backtest_diagnostic_only_not_candidate",
            "Symmetry result remains an in-sample backtest diagnostic.",
        ),
        (
            "v5f_short_window_reversion_walk_forward_robustness",
            "v5f_short_window_reversion_walk_forward_robustness/current/v5f_walk_forward_summary.json",
            "short_window_internal_rolling",
            "diagnostic_only_backtest_scope_no_oos_validation",
            "historical_backtest_internal_rolling_diagnostic_only",
            "The word walk-forward is retained only in the folder name for compatibility; evidence is not OOS validation.",
        ),
    ]
    rows: list[dict[str, Any]] = []
    for component_id, path_text, family, corrected_gate, corrected_status, note in components:
        path = root / path_text
        summary = _read_json(path) if path.exists() else {}
        original_gate = summary.get("pm_gate_decision", "")
        rows.append(
            {
                "component_id": component_id,
                "family": family,
                "source_path": str(path),
                "source_exists": path.exists(),
                "original_pm_gate_decision": original_gate,
                "corrected_pm_gate_decision": corrected_gate,
                "corrected_evidence_status": corrected_status,
                "backtest_scope_start": summary.get("backtest_scope_start", REPAIRED_FIRST_TRADE),
                "backtest_scope_end": summary.get("backtest_scope_end", BACKTEST_SCOPE_END),
                "oos_validation_claim_allowed": False,
                "accepted": False,
                "requires_forward_paper": component_id == "v5f_internal_subsleeve_mom12_70_30",
                "scope_violation_type": _scope_violation_type(component_id, original_gate),
                "correction_note": note,
            }
        )
    return rows


def _v4_component_reclassification() -> list[dict[str, Any]]:
    v4 = Path("D:/hh/codex/v4")
    components = [
        (
            "v4_pre2021_momentum_rolling",
            v4 / "phase_2_momentum/momentum_rolling_validation_v1.md",
            "pre2021_research_reserve",
            "compliant_if_all_folds_before_2021_05_01",
            "Pre-2021 rolling validation can remain research/validation reserve.",
        ),
        (
            "v4_pre2021_mean_reversion_tests",
            v4 / "phase_2_momentum/mean_reversion_composite_test_results_v1.md",
            "pre2021_research_reserve",
            "compliant_if_all_folds_before_2021_05_01",
            "Pre-2021 mean-reversion research can remain research reserve.",
        ),
        (
            "v4_post2021_active_mainline_final_validation_packet",
            v4 / "phase_2_momentum/active_mainline_final_validation_packet_v1.md",
            "post2021_backtest_scope",
            "reclassify_as_backtest_execution_confirmation_not_validation",
            "The 2021-05-31 to 2026-05-31 window is backtest/executable confirmation, not OOS validation.",
        ),
        (
            "v4_post2021_mean_reversion_overlay_tests",
            v4 / "phase_2_momentum/mean_reversion_overlay_on_annual_pool_v1.md",
            "post2021_backtest_scope",
            "reclassify_as_backtest_observation_not_acceptance",
            "Post-2021 mean-reversion observations cannot be used for parameter tuning or acceptance.",
        ),
    ]
    rows: list[dict[str, Any]] = []
    for component_id, path, scope, corrected_status, note in components:
        rows.append(
            {
                "component_id": component_id,
                "source_path": str(path),
                "source_exists": path.exists(),
                "scope": scope,
                "corrected_evidence_status": corrected_status,
                "oos_validation_claim_allowed": scope == "pre2021_research_reserve",
                "accepted": False,
                "scope_violation_type": "none" if scope == "pre2021_research_reserve" else "post2021_validation_or_acceptance_label_must_be_corrected",
                "correction_note": note,
            }
        )
    return rows


def _violation_audit(v5f: list[dict[str, Any]], v4: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in [*v5f, *v4]:
        violation = row.get("scope_violation_type", "none")
        rows.append(
            {
                "component_id": row["component_id"],
                "scope_violation_type": violation,
                "severity": "governance_correction" if violation != "none" else "none",
                "status": "corrected_in_this_packet" if violation != "none" else "pass",
                "corrected_evidence_status": row["corrected_evidence_status"],
            }
        )
    return rows


def _decision(v5f: list[dict[str, Any]], v4: list[dict[str, Any]], violations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "pm_gate_decision": "apply_backtest_scope_correction_keep_v5f_momentum_backtest_candidate_not_accepted",
            "v5f_momentum_status": "historical_backtest_candidate_not_accepted_requires_forward_paper",
            "v5f_mean_reversion_status": "historical_backtest_diagnostic_only",
            "v5f_short_window_status": "historical_backtest_internal_diagnostic_only",
            "v4_pre2021_status": "research_reserve_allowed",
            "v4_post2021_status": "backtest_observation_not_oos_acceptance",
            "scope_correction_count": sum(1 for row in violations if row["status"] == "corrected_in_this_packet"),
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
        }
    ]


def _next_queue() -> list[dict[str, Any]]:
    return [
        {
            "queue_id": "next_001",
            "task": "Use pre-2021 only for rule discovery or validation reserve; do not retune on 2021-2026.",
            "priority": "high",
            "status": "rule",
        },
        {
            "queue_id": "next_002",
            "task": "Keep V5f internal subsleeve momentum as historical backtest candidate and continue only forward/paper after 2026-05-31.",
            "priority": "high",
            "status": "queued",
        },
        {
            "queue_id": "next_003",
            "task": "Archive V5f mean-reversion and short-window reversion as diagnostics unless independent pre-2021 or future evidence is added.",
            "priority": "medium",
            "status": "queued",
        },
    ]


def _report(
    v5f: list[dict[str, Any]],
    v4: list[dict[str, Any]],
    violations: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    lines = [
        "# V5f Backtest-Scope Governance Correction",
        "",
        "Correction rule: 2021-05-01 to 2026-05-31 is the historical backtest window. It is not OOS, not formal rolling validation, and not acceptance evidence.",
        "",
        "Answer to the PM question:",
        "- Prior momentum work is not numerically invalid, but any promotion language based only on 2021-2026 must be downgraded to historical backtest candidate, not accepted.",
        "- Prior mean-reversion work is not a live violation because it mostly failed/diagnostic, but any post-2021 validation or acceptance wording is downgraded to backtest diagnostic.",
        "- Short-window reversion had the clearest labeling problem: it was named walk-forward robustness while using only the repaired backtest window. It is now reclassified as internal rolling diagnostic.",
        "",
        f"PM decision: `{decision[0]['pm_gate_decision']}`",
        "",
        "V5f component corrections:",
    ]
    for row in v5f:
        lines.append(
            f"- `{row['component_id']}` -> `{row['corrected_evidence_status']}`; violation `{row['scope_violation_type']}`"
        )
    lines += ["", "V4 component corrections:"]
    for row in v4:
        lines.append(
            f"- `{row['component_id']}` -> `{row['corrected_evidence_status']}`; violation `{row['scope_violation_type']}`"
        )
    lines += ["", "Permanent rule:"]
    lines.append("- Future V4/V5/V5f reports must separate pre-2021 research reserve, 2021-2026 historical backtest, and post-2026-05-31 forward/paper evidence.")
    return "\n".join(lines) + "\n"


def _rules() -> str:
    return "\n".join(
        [
            "# Agent Execution Rules",
            "",
            "- 2021-05-01 to 2026-05-31 is historical backtest scope.",
            "- Repaired V57f first legal trade may be 2021-05-06; this does not change the scope classification.",
            "- Do not call any 2021-2026 result OOS, formal rolling validation, or acceptance evidence.",
            "- Pre-2021 can be research/validation reserve only if PIT-clean and not reusing post-2021 outcomes.",
            "- Post-2026-05-31 is forward/paper evidence.",
            "- Do not mark accepted or live approved.",
        ]
    ) + "\n"


def _scope_violation_type(component_id: str, gate: str) -> str:
    if "short_window_reversion_walk_forward" in component_id:
        return "walk_forward_label_inside_backtest_window"
    if gate.startswith("promote_short_window"):
        return "promotion_language_from_backtest_only"
    if gate.startswith("promote_internal_subsleeve"):
        return "candidate_language_from_backtest_only_requires_forward_paper"
    return "none"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


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
        if not keys:
            f.write("")
            return
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    print(json.dumps(run_v5f_backtest_scope_governance_correction(Path(".")), ensure_ascii=False, indent=2))

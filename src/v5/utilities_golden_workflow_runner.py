from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import write_json_file


DEFAULT_OUT_DIR = Path("docs") / "governance"
DB = "\u6570\u636e\u5e93"


def run_utilities_golden_workflow_audit(
    out_dir: Path = DEFAULT_OUT_DIR,
    *,
    repo_root: Path | None = None,
) -> Path:
    root = repo_root or Path.cwd()
    out_dir = out_dir if out_dir.is_absolute() else root / out_dir
    steps = [_check_step(root, step) for step in _build_steps()]
    summary = _summary(steps)
    payload = {
        "strategy_id": "utilities_demand_state_v51f",
        "sector": "utilities_electricity",
        "audit_id": "v51f_utilities_golden_workflow_execution_v1",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": summary["status"],
        "not_status": ["accepted_strategy", "live_trading_approved"],
        "summary": summary,
        "steps": steps,
        "pm_decision": _pm_decision(summary),
    }
    json_path = out_dir / "v51f_utilities_golden_workflow_execution_v1.json"
    md_path = out_dir / "v51f_utilities_golden_workflow_execution_v1.md"
    write_json_file(json_path, payload)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_render_markdown(payload), encoding="utf-8")
    return md_path


def _build_steps() -> list[dict[str, Any]]:
    return [
        _step(
            1,
            "data_availability_gate",
            "Project Manager",
            "utilities_data_gate",
            [
                f"{DB}/processed/utilities_pit_panel/panel.csv",
                f"{DB}/processed/utilities_cashflow_value_v51b_panel/panel.csv",
                f"{DB}/processed/utilities_external_state/utilities_external_state.csv",
                f"{DB}/processed/utilities_joinquant_real_daily_prices.csv",
                f"{DB}/processed/utilities_joinquant_real_benchmark_prices.csv",
            ],
            [f"{DB}/processed/utilities_joinquant_cash_dividends.csv"],
        ),
        _step(
            2,
            "research_knowledge_gate",
            "Research Agent",
            "sector_knowledge_packet",
            [
                "knowledge/research_agent/references/utilities_universe_definition.md",
                "knowledge/research_agent/references/utilities_data_field_map.md",
                "knowledge/research_agent/factor_theory/utilities_value_investing_framework.md",
                "knowledge/research_agent/factor_theory/utilities_core_factor_hypotheses.md",
                "knowledge/research_agent/references/utilities_validation_handoff.md",
            ],
            [
                "knowledge/research_agent/references/utilities_source_collection_plan.md",
                "knowledge/research_agent/references/utilities_special_information_sources.md",
            ],
        ),
        _step(
            3,
            "research_hypothesis_design",
            "Research Agent",
            "testable_hypotheses",
            [
                "examples/utilities_demand_state_v51f_strategy.json",
                "knowledge/research_agent/strategy_cases/utilities_v51f_quant_ready_candidate.md",
            ],
            ["docs/governance/v51f_utilities_pm_formal_candidate_decision_v1.md"],
        ),
        _step(
            4,
            "pit_universe_build",
            "Quant Validation Agent",
            "pit_universe",
            [
                f"{DB}/processed/utilities_pit_panel/panel.csv",
                f"{DB}/processed/utilities_pit_panel/collection_manifest.json",
            ],
        ),
        _step(
            5,
            "pit_panel_build",
            "Quant Validation Agent",
            "pit_factor_and_state_panel",
            [
                f"{DB}/processed/utilities_cashflow_value_v51b_panel/panel.csv",
                f"{DB}/processed/utilities_cashflow_value_v51b_panel/collection_manifest.json",
                f"{DB}/processed/utilities_external_state/utilities_external_state.csv",
                f"{DB}/processed/utilities_external_state/collection_manifest.json",
            ],
        ),
        _step(
            6,
            "formal_validation",
            "Quant Validation Agent",
            "formal_validation_packet",
            [
                "validation_formal_v51e/utilities_demand_state_v51e/demand_state_validation_summary.json",
                "validation_formal_v51e/utilities_demand_state_v51e/demand_state_validation_report.md",
                "validation_formal_v51e/utilities_demand_state_v51e/rolling_state_model_tests.csv",
                "validation_formal_v51e/utilities_demand_state_v51e/state_conditioned_factor_ic.csv",
                "validation_formal_v51e/utilities_demand_state_v51e/selection_count_robustness.csv",
                "validation_formal_v51e/utilities_demand_state_v51e/failure_year_analysis.csv",
            ],
            ["validation_formal_v51e/utilities_demand_state_v51e/yearly_comparison.csv"],
        ),
        _step(
            7,
            "pm_formal_candidate_decision",
            "Project Manager",
            "formal_candidate_decision",
            ["docs/governance/v51f_utilities_pm_formal_candidate_decision_v1.md"],
        ),
        _step(
            8,
            "engineering_smoke_test",
            "Engineering Agent",
            "engineering_smoke_test",
            [
                "docs/governance/v51f_utilities_local_simulation_ready_v1.md",
                "local_daily_backtests_utilities_v51f/utilities_demand_state_v51f/summary.json",
            ],
        ),
        _step(
            9,
            "local_daily_simulation",
            "Engineering Agent",
            "local_daily_simulation_packet",
            [
                "local_daily_backtests_utilities_v51f/utilities_demand_state_v51f/daily_returns.csv",
                "local_daily_backtests_utilities_v51f/utilities_demand_state_v51f/holdings.csv",
                "local_daily_backtests_utilities_v51f/utilities_demand_state_v51f/trades.csv",
                "local_daily_backtests_utilities_v51f/utilities_demand_state_v51f/rebalance_signals.csv",
                "local_daily_backtests_utilities_v51f/utilities_demand_state_v51f/dividends.csv",
            ],
        ),
        _step(
            10,
            "overfit_audit",
            "Engineering Agent + Quant Validation Agent",
            "overfit_audit_packet",
            [
                "validation_overfit/utilities_demand_state_v51f/overfit_audit_summary.json",
                "validation_overfit/utilities_demand_state_v51f/overfit_audit_report.md",
                "validation_overfit/utilities_demand_state_v51f/overfit_audit_checks.csv",
                "docs/governance/v51f_utilities_overfit_audit_v1.md",
            ],
        ),
        _step(
            11,
            "platform_replication_gate",
            "Project Manager",
            "platform_gate",
            [
                "docs/governance/v51f_utilities_frozen_signal_platform_test_v1.md",
                "exports/joinquant/utilities_demand_state_v51f_joinquant_live_recompute.py",
            ],
            ["docs/governance/v51f_utilities_live_joinquant_recompute_v1.md"],
        ),
        _step(
            12,
            "platform_replication",
            "Engineering Agent",
            "platform_replication_packet",
            [],
            status_override="pending_user_platform_export",
            notes="Platform smoke test is prepared, but external JoinQuant result export is not yet recorded as a passed replication packet.",
        ),
        _step(
            13,
            "paper_trading_setup",
            "Project Manager + Engineering Agent",
            "paper_trading_signal",
            [
                "docs/governance/v51f_utilities_forward_paper_trading_log.md",
                "docs/governance/v51f_utilities_paper_signal_20260716.md",
                "paper_trading_signals/utilities_demand_state_v51f/2026-07-16/signal_summary.json",
                "paper_trading_signals/utilities_demand_state_v51f/2026-07-16/selected_signal.csv",
            ],
            [
                "paper_trading_signals/utilities_demand_state_v51f/2026-07-16/candidate_scores.csv",
                "paper_trading_signals/utilities_demand_state_v51f/2026-07-16/q1_quality_check.csv",
            ],
        ),
        _step(
            14,
            "paper_trading_review",
            "Project Manager + Quant Validation Agent",
            "forward_review",
            [],
            status_override="pending_forward_evidence",
            notes="Paper trading started on 2026-07-16. Forward review requires future realized data and must not be backfilled.",
        ),
    ]


def _step(
    step: int,
    layer: str,
    owner: str,
    gate: str,
    required: list[str],
    optional: list[str] | None = None,
    *,
    status_override: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "step": step,
        "layer": layer,
        "owner": owner,
        "gate": gate,
        "required": required,
        "optional": optional or [],
    }
    if status_override:
        result["status_override"] = status_override
    if notes:
        result["notes"] = notes
    return result


def _check_step(root: Path, step: dict[str, Any]) -> dict[str, Any]:
    required = step.get("required", [])
    optional = step.get("optional", [])
    missing_required = [path for path in required if not (root / path).exists()]
    present_required = [path for path in required if (root / path).exists()]
    present_optional = [path for path in optional if (root / path).exists()]
    missing_optional = [path for path in optional if not (root / path).exists()]
    if step.get("status_override"):
        status = step["status_override"]
    elif missing_required:
        status = "blocked"
    else:
        status = "passed"
    result = dict(step)
    result.update(
        {
            "status": status,
            "present_required": present_required,
            "missing_required": missing_required,
            "present_optional": present_optional,
            "missing_optional": missing_optional,
        }
    )
    return result


def _summary(steps: list[dict[str, Any]]) -> dict[str, Any]:
    passed = sum(1 for step in steps if step["status"] == "passed")
    blocked = [step for step in steps if step["status"] == "blocked"]
    pending = [step for step in steps if step["status"].startswith("pending")]
    required_total = sum(len(step.get("required", [])) for step in steps)
    required_present = sum(len(step.get("present_required", [])) for step in steps)
    return {
        "status": "golden_template_productized_with_pending_forward_and_platform_review"
        if not blocked
        else "golden_template_needs_repair",
        "passed_steps": passed,
        "blocked_steps": len(blocked),
        "pending_steps": len(pending),
        "total_steps": len(steps),
        "required_artifacts_present": required_present,
        "required_artifacts_total": required_total,
        "blocked_gates": [step["gate"] for step in blocked],
        "pending_gates": [step["gate"] for step in pending],
    }


def _pm_decision(summary: dict[str, Any]) -> dict[str, Any]:
    if summary["blocked_steps"]:
        return {
            "decision": "Do not use as golden template until blocked gates are repaired.",
            "current_status": ["golden_template_needs_repair"],
            "not_status": ["accepted_strategy", "live_trading_approved"],
            "next_gate": "repair_missing_golden_template_artifacts",
        }
    return {
        "decision": "V5.1f is productized as the utilities golden workflow template. It remains not accepted and not live-trading approved.",
        "current_status": [
            "formal_strategy_candidate",
            "engineering_smoke_test_passed",
            "paper_trading_started",
            "utilities_golden_workflow_template",
        ],
        "not_status": ["accepted_strategy", "live_trading_approved"],
        "next_gate": "paper_trading_forward_review_and_optional_platform_export_attribution",
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# V5.1f Utilities Golden Workflow Execution V1",
        "",
        f"Date: {payload['created_at_utc'][:10]}",
        "",
        "Status:",
        "",
        "```text",
        str(payload["status"]),
        "```",
        "",
        "Not status:",
        "",
        "```text",
        "accepted_strategy",
        "live_trading_approved",
        "```",
        "",
        "## Summary",
        "",
        f"- Passed steps: {summary['passed_steps']} / {summary['total_steps']}",
        f"- Pending steps: {summary['pending_steps']}",
        f"- Blocked steps: {summary['blocked_steps']}",
        f"- Required artifacts present: {summary['required_artifacts_present']} / {summary['required_artifacts_total']}",
        f"- Pending gates: {', '.join(summary['pending_gates']) if summary['pending_gates'] else 'none'}",
        f"- Blocked gates: {', '.join(summary['blocked_gates']) if summary['blocked_gates'] else 'none'}",
        "",
        "## PM Decision",
        "",
        payload["pm_decision"]["decision"],
        "",
        f"Next gate: `{payload['pm_decision']['next_gate']}`",
        "",
        "## Step Results",
        "",
        "| Step | Layer | Owner | Gate | Status | Missing Required |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for step in payload["steps"]:
        missing = ", ".join(step["missing_required"]) if step["missing_required"] else ""
        lines.append(f"| {step['step']} | {step['layer']} | {step['owner']} | {step['gate']} | {step['status']} | {missing} |")
    lines.extend(
        [
            "",
            "## Operating Rule",
            "",
            "V5.1f is the reusable utilities / electricity workflow template. It remains a formal candidate and paper-trading case, not an accepted or live-trading strategy.",
            "",
        ]
    )
    return "\n".join(lines)

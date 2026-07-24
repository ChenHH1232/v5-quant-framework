from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows_if_exists, write_csv_rows, write_json_file
from v5.math_utils import to_float


DEFAULT_OBSERVATION_REGISTRY = Path("enhanced_etf_governance_v5") / "current" / "observation_sleeve_registry.csv"
DEFAULT_CORE_DASHBOARD = Path("enhanced_etf_governance_v5") / "current" / "v57f_core_dashboard.csv"
DEFAULT_OUT_DIR = Path("enhanced_etf_governance_v5") / "current" / "promotion_policy"

POLICY_FIELDS = ["rule_id", "category", "rule", "threshold_or_condition", "failure_effect"]
AUDIT_FIELDS = [
    "sector_id",
    "strategy_id",
    "observation_class",
    "latest_stage",
    "strategy_return",
    "max_drawdown",
    "information_ratio",
    "order_health_status",
    "paper_tracking_status",
    "promotion_decision",
    "can_promote_to_core_candidate",
    "can_remain_observation",
    "required_next_evidence",
    "failed_rules",
    "allowed_next_action",
    "blocked_action",
    "next_gate",
]
QUEUE_FIELDS = ["queue_rank", "sector_id", "owner", "task", "input_artifacts", "output_artifacts", "gate", "blocked_actions"]


@dataclass(frozen=True)
class SleevePromotionPolicyResult:
    output_dir: Path
    policy_json: Path
    policy_md: Path
    audit_csv: Path
    audit_summary_json: Path
    report_md: Path
    next_agent_queue_csv: Path
    status: str


def run_sleeve_promotion_policy_audit(
    *,
    observation_registry: Path = DEFAULT_OBSERVATION_REGISTRY,
    core_dashboard: Path = DEFAULT_CORE_DASHBOARD,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> SleevePromotionPolicyResult:
    observation_rows = read_csv_rows_if_exists(observation_registry)
    core_rows = read_csv_rows_if_exists(core_dashboard)
    v57f = _mainline_row(core_rows)
    policy_rows = _policy_rows()
    audit_rows = [_audit_row(row, v57f) for row in observation_rows]
    queue_rows = _queue_rows(audit_rows)
    status = "promotion_policy_audit_completed_no_core_promotions"
    if any(row["can_promote_to_core_candidate"] == "yes" for row in audit_rows):
        status = "promotion_policy_audit_completed_core_candidate_found_needs_pm_stage_gate"

    out_dir.mkdir(parents=True, exist_ok=True)
    policy_json = out_dir / "sleeve_promotion_policy_v1.json"
    policy_md = out_dir / "sleeve_promotion_policy_v1.md"
    audit_csv = out_dir / "sleeve_promotion_eligibility_audit.csv"
    audit_summary_json = out_dir / "sleeve_promotion_eligibility_summary.json"
    report_md = out_dir / "sleeve_promotion_eligibility_report.md"
    next_agent_queue_csv = out_dir / "sleeve_promotion_next_agent_queue.csv"

    policy = {
        "schema_version": 1,
        "policy_id": "sleeve_promotion_policy_v1",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "active_governance_policy",
        "purpose": "Define when an observation sleeve can be promoted to a V57f core candidate.",
        "mainline_reference": {
            "strategy_id": v57f.get("strategy_id", ""),
            "strategy_return": v57f.get("strategy_return", ""),
            "max_drawdown": v57f.get("max_drawdown", ""),
            "information_ratio": v57f.get("information_ratio", ""),
        },
        "rules": policy_rows,
        "hard_blocks": [
            "Historical return alone cannot promote a sleeve.",
            "Small-sample sleeves cannot become ordinary core sleeves without a separate PM-approved capped policy.",
            "Order-health needs_review blocks paper tracking and core promotion.",
            "Archived/data-gate-failed sleeves cannot be reopened by high backtest return.",
            "This policy does not modify V57f or generate a 2026-10 paper runner.",
        ],
    }
    write_json_file(policy_json, policy)
    policy_md.write_text(_policy_report(policy), encoding="utf-8")
    write_csv_rows(audit_csv, AUDIT_FIELDS, audit_rows, encoding="utf-8-sig")
    write_csv_rows(next_agent_queue_csv, QUEUE_FIELDS, queue_rows, encoding="utf-8-sig")

    summary = {
        "schema_version": 1,
        "project": "v5_sleeve_promotion_policy_audit",
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "candidate_count": len(audit_rows),
        "promotion_decision_counts": _count(audit_rows, "promotion_decision"),
        "core_candidate_count": sum(1 for row in audit_rows if row["can_promote_to_core_candidate"] == "yes"),
        "observation_count": sum(1 for row in audit_rows if row["can_remain_observation"] == "yes"),
        "outputs": {
            "policy_json": str(policy_json),
            "policy_md": str(policy_md),
            "audit_csv": str(audit_csv),
            "report_md": str(report_md),
            "next_agent_queue_csv": str(next_agent_queue_csv),
        },
        "source_paths": {
            "observation_registry": str(observation_registry),
            "core_dashboard": str(core_dashboard),
        },
    }
    write_json_file(audit_summary_json, summary)
    report_md.write_text(_audit_report(summary, audit_rows, queue_rows), encoding="utf-8")

    return SleevePromotionPolicyResult(
        output_dir=out_dir,
        policy_json=policy_json,
        policy_md=policy_md,
        audit_csv=audit_csv,
        audit_summary_json=audit_summary_json,
        report_md=report_md,
        next_agent_queue_csv=next_agent_queue_csv,
        status=status,
    )


def _policy_rows() -> list[dict[str, str]]:
    return [
        _rule("P1", "governance", "V57f is frozen during promotion audit.", "No sleeve/factor/weight/timing change", "block_core_promotion"),
        _rule("P2", "evidence", "Local daily simulation must exist and use real dividends where applicable.", "summary_path exists and dividend/order outputs are reviewed", "remain_observation_or_repair"),
        _rule("P3", "execution", "Rebalance order health must pass.", "order_health_status == passed", "block_paper_and_core"),
        _rule("P4", "forward", "Paper tracking or clean forward evidence is required before core candidacy.", "paper_tracking_status == paper_artifact_exists and future window is not retroactive", "remain_observation"),
        _rule("P5", "risk", "Drawdown cannot materially worsen versus V57f.", "max_drawdown <= V57f max_drawdown * 1.10", "remain_observation_or_repair"),
        _rule("P6", "quality", "Information ratio cannot be materially worse than V57f.", "information_ratio >= V57f IR * 0.90", "remain_observation"),
        _rule("P7", "sample", "Small-sample/specialist sleeves need separate capped policy.", "no small_sample/specialist class unless PM approves capped sleeve", "capped_observation_only"),
        _rule("P8", "data", "Research/data-gate/archived stages cannot promote.", "latest_stage not in research_or_data_repair, archived_or_failed", "block_core_promotion"),
        _rule("P9", "mandate", "Cycle-state or specialist-data gaps must be closed ex ante.", "required industry data gate is passed", "remain_observation_or_archive"),
    ]


def _audit_row(row: dict[str, str], v57f: dict[str, str]) -> dict[str, str]:
    sector_id = row.get("sector_id", "")
    obs_class = row.get("observation_class", "")
    stage = row.get("latest_stage", "")
    order = row.get("order_health_status", "")
    paper = row.get("paper_tracking_status", "")
    max_dd = to_float(row.get("max_drawdown"))
    ir = to_float(row.get("information_ratio"))
    v57f_dd = to_float(v57f.get("max_drawdown")) or 0.0
    v57f_ir = to_float(v57f.get("information_ratio")) or 0.0
    failed: list[str] = []
    evidence: list[str] = []

    if order != "passed":
        failed.append("P3_order_health_not_passed")
        evidence.append("repair or explain rebalance_order_health")
    if paper != "paper_artifact_exists":
        failed.append("P4_no_paper_tracking_artifact")
        evidence.append("create paper tracking packet after engineering blockers are closed")
    if max_dd is None or (v57f_dd > 0 and max_dd > v57f_dd * 1.10):
        failed.append("P5_drawdown_worse_than_threshold")
        evidence.append("show drawdown does not worsen V57f materially in sidecar / forward evidence")
    if ir is None or (v57f_ir > 0 and ir < v57f_ir * 0.90):
        failed.append("P6_information_ratio_below_threshold")
        evidence.append("show IR contribution is not materially worse than V57f")
    if "small_sample" in obs_class or "specialist" in obs_class:
        failed.append("P7_small_sample_or_specialist_policy_required")
        evidence.append("PM-approved capped/specialist sleeve policy")
    if stage in {"research_or_data_repair", "archived_or_failed"}:
        failed.append("P8_stage_blocks_promotion")
        evidence.append("complete research/data-gate repair before any promotion audit")
    if obs_class in {"cycle_state_observation", "archived_data_gate_failed", "specialist_small_sample_observation"}:
        failed.append("P9_industry_specific_data_gate_required")
        evidence.append("close specialist/cycle-state industry data gate ex ante")

    decision = _decision(sector_id, obs_class, stage, failed)
    can_core = "yes" if decision == "can_promote_to_core_candidate_needs_pm_stage_gate" else "no"
    can_observe = "yes" if decision in {
        "remain_observation_needs_forward_or_sidecar_evidence",
        "capped_observation_only",
        "specialist_observation_only",
    } else "no"

    return {
        "sector_id": sector_id,
        "strategy_id": row.get("strategy_id", ""),
        "observation_class": obs_class,
        "latest_stage": stage,
        "strategy_return": row.get("strategy_return", ""),
        "max_drawdown": row.get("max_drawdown", ""),
        "information_ratio": row.get("information_ratio", ""),
        "order_health_status": order,
        "paper_tracking_status": paper,
        "promotion_decision": decision,
        "can_promote_to_core_candidate": can_core,
        "can_remain_observation": can_observe,
        "required_next_evidence": ";".join(_dedupe(evidence)) or "PM stage gate approval",
        "failed_rules": ";".join(failed) or "none",
        "allowed_next_action": row.get("allowed_next_action", ""),
        "blocked_action": row.get("blocked_action", ""),
        "next_gate": row.get("next_gate", ""),
    }


def _decision(sector_id: str, obs_class: str, stage: str, failed: list[str]) -> str:
    if stage == "archived_or_failed" or obs_class == "archived_data_gate_failed":
        return "archived_or_data_gate_failed"
    if "P3_order_health_not_passed" in failed:
        return "engineering_repair_required"
    if "P8_stage_blocks_promotion" in failed:
        return "research_data_repair_required"
    if "small_sample" in obs_class:
        return "capped_observation_only"
    if "specialist" in obs_class:
        return "specialist_observation_only"
    if not failed:
        return "can_promote_to_core_candidate_needs_pm_stage_gate"
    if sector_id in {"gas_water_operators", "home_appliances"}:
        return "remain_observation_needs_forward_or_sidecar_evidence"
    return "blocked_or_observation_only"


def _queue_rows(audit_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    queue: list[dict[str, str]] = []
    rank = 1
    for row in audit_rows:
        decision = row["promotion_decision"]
        if decision in {"engineering_repair_required", "research_data_repair_required", "remain_observation_needs_forward_or_sidecar_evidence"}:
            queue.append(
                {
                    "queue_rank": str(rank),
                    "sector_id": row["sector_id"],
                    "owner": _owner_for_decision(decision),
                    "task": _task_for_decision(row),
                    "input_artifacts": row["source_summary_path"] if "source_summary_path" in row else row["strategy_id"],
                    "output_artifacts": "updated evidence packet; no V57f change",
                    "gate": decision,
                    "blocked_actions": "do_not_modify_V57f;do_not_tune;do_not_promote_by_return",
                }
            )
            rank += 1
    if not queue:
        queue.append(
            {
                "queue_rank": "1",
                "sector_id": "all",
                "owner": "Project Manager Agent",
                "task": "No promotion candidate found; keep all observation sleeves under current restrictions.",
                "input_artifacts": "sleeve_promotion_eligibility_audit.csv",
                "output_artifacts": "none",
                "gate": "governance_reference_only",
                "blocked_actions": "do_not_modify_V57f;do_not_start_new_sector;do_not_tune",
            }
        )
    return queue


def _owner_for_decision(decision: str) -> str:
    if decision == "engineering_repair_required":
        return "Engineering Agent"
    if decision == "research_data_repair_required":
        return "Research Agent"
    return "Project Manager Agent"


def _task_for_decision(row: dict[str, str]) -> str:
    decision = row["promotion_decision"]
    if decision == "engineering_repair_required":
        return f"Repair engineering blockers for {row['sector_id']} before any paper tracking or promotion audit."
    if decision == "research_data_repair_required":
        return f"Repair research/data-gate blockers for {row['sector_id']} before Engineering handoff."
    return f"Keep {row['sector_id']} as observation and require forward/sidecar evidence before another promotion audit."


def _mainline_row(rows: list[dict[str, str]]) -> dict[str, str]:
    for row in rows:
        if row.get("row_type") == "mainline_basket":
            return row
    return {}


def _rule(rule_id: str, category: str, rule: str, threshold: str, effect: str) -> dict[str, str]:
    return {
        "rule_id": rule_id,
        "category": category,
        "rule": rule,
        "threshold_or_condition": threshold,
        "failure_effect": effect,
    }


def _policy_report(policy: dict[str, Any]) -> str:
    lines = [
        "# Sleeve Promotion Policy V1",
        "",
        "Purpose: define when an observation sleeve can become a V57f core candidate.",
        "",
        "## Rules",
        "",
        "| Rule | Category | Condition | Failure effect |",
        "| --- | --- | --- | --- |",
    ]
    for row in policy["rules"]:
        lines.append(f"| `{row['rule_id']}` | {row['category']} | {row['threshold_or_condition']} | `{row['failure_effect']}` |")
    lines.extend(["", "## Hard Blocks", ""])
    for item in policy["hard_blocks"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def _audit_report(summary: dict[str, Any], audit_rows: list[dict[str, str]], queue_rows: list[dict[str, str]]) -> str:
    lines = [
        "# Sleeve Promotion Eligibility Audit",
        "",
        f"Status: `{summary['status']}`",
        "",
        "## Decisions",
        "",
        "| Sector | Decision | Core candidate | Required next evidence |",
        "| --- | --- | --- | --- |",
    ]
    for row in audit_rows:
        lines.append(f"| `{row['sector_id']}` | `{row['promotion_decision']}` | `{row['can_promote_to_core_candidate']}` | {row['required_next_evidence']} |")
    lines.extend(["", "## Next Queue", "", "| Rank | Sector | Owner | Task |", "| ---: | --- | --- | --- |"])
    for row in queue_rows:
        lines.append(f"| {row['queue_rank']} | `{row['sector_id']}` | {row['owner']} | {row['task']} |")
    lines.append("")
    return "\n".join(lines)


def _count(rows: list[dict[str, str]], field: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        value = str(row.get(field) or "")
        result[value] = result.get(value, 0) + 1
    return result


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result

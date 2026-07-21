from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows_if_exists, write_csv_rows, write_json_file


DEFAULT_CONFIG = Path("config/dividend_low_vol_cashflow_sector_coverage_v58.json")
DEFAULT_OUT_DIR = Path("roadmaps_v58_sector_replication")

ROADMAP_FIELDS = [
    "priority_rank",
    "sector_id",
    "display_name",
    "sector_type",
    "pm_lane",
    "next_agent",
    "loop_type",
    "timebox_minutes",
    "required_packet",
    "required_inputs",
    "allowed_next_action",
    "forbidden_action",
    "graduation_gate",
    "stop_condition",
    "screening_decision",
    "data_gate",
    "pit_universe_gate",
    "business_purity_gate",
    "dividend_gate",
    "fcf_gate",
    "low_vol_gate",
    "external_state_burden",
    "sample_size_risk",
    "notes",
]


@dataclass(frozen=True)
class SectorReplicationRoadmapResult:
    output_dir: Path
    csv_path: Path
    json_path: Path
    report_path: Path
    queue_dir: Path
    sector_count: int
    lane_counts: dict[str, int]


def build_sector_replication_roadmap(
    config_path: Path = DEFAULT_CONFIG,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> SectorReplicationRoadmapResult:
    config = _read_json(config_path)
    source_config = _read_json(Path(str(config["source_sector_config"])))
    screening_rows = _read_screening_rows(config)
    screening_by_sector = {row.get("sector_id", ""): row for row in screening_rows}

    rows = [
        _build_roadmap_row(candidate, screening_by_sector.get(str(candidate.get("sector_id")), {}), config)
        for candidate in source_config.get("candidate_sectors", [])
    ]
    rows.sort(key=lambda row: (int(row["priority_rank"]), row["sector_id"]))

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "sector_replication_roadmap.csv"
    json_path = out_dir / "sector_replication_roadmap_summary.json"
    report_path = out_dir / "sector_replication_roadmap_pm_report.md"
    queue_dir = out_dir / "agent_queues"

    write_csv_rows(csv_path, ROADMAP_FIELDS, rows)
    queue_paths = _write_agent_queues(queue_dir, rows)
    summary = _build_summary(config, rows, csv_path, report_path, queue_paths)
    write_json_file(json_path, summary)
    report_path.write_text(_build_report(summary, rows, config), encoding="utf-8")

    return SectorReplicationRoadmapResult(
        output_dir=out_dir,
        csv_path=csv_path,
        json_path=json_path,
        report_path=report_path,
        queue_dir=queue_dir,
        sector_count=len(rows),
        lane_counts=summary["lane_counts"],
    )


def _read_screening_rows(config: dict[str, Any]) -> list[dict[str, str]]:
    rows = read_csv_rows_if_exists(Path(str(config.get("source_screening_results", ""))))
    if rows:
        return rows
    summary_path = Path(str(config.get("source_screening_summary", "")))
    if summary_path.exists():
        return []
    return []


def _build_roadmap_row(candidate: dict[str, Any], screening: dict[str, str], config: dict[str, Any]) -> dict[str, Any]:
    decision = screening.get("pm_screening_decision") or _infer_screening_decision(candidate)
    lane = _lane_from_decision(decision)
    lane_policy = config.get("lane_policy", {}).get(lane, {})
    priority = _priority(candidate, decision, lane)
    required_inputs = _required_inputs(candidate, lane)
    graduation_gate = _graduation_gate(candidate, lane)
    stop_condition = _stop_condition(lane, config)

    return {
        "priority_rank": priority,
        "sector_id": candidate.get("sector_id", ""),
        "display_name": candidate.get("display_name", ""),
        "sector_type": candidate.get("sector_type", ""),
        "pm_lane": lane,
        "next_agent": lane_policy.get("next_agent", "Project Manager Agent"),
        "loop_type": lane_policy.get("loop_type", ""),
        "timebox_minutes": lane_policy.get("timebox_minutes", config.get("timebox_policy", {}).get("default_minutes", 30)),
        "required_packet": lane_policy.get("required_packet", "checkpoint_packet"),
        "required_inputs": ";".join(required_inputs),
        "allowed_next_action": lane_policy.get("allowed_next_action", ""),
        "forbidden_action": lane_policy.get("forbidden_action", ""),
        "graduation_gate": graduation_gate,
        "stop_condition": stop_condition,
        "screening_decision": decision,
        "data_gate": candidate.get("data_gate", ""),
        "pit_universe_gate": candidate.get("pit_universe_gate", ""),
        "business_purity_gate": candidate.get("business_purity_gate", ""),
        "dividend_gate": candidate.get("dividend_gate", ""),
        "fcf_gate": candidate.get("fcf_gate", ""),
        "low_vol_gate": candidate.get("low_vol_gate", ""),
        "external_state_burden": candidate.get("external_state_burden", ""),
        "sample_size_risk": candidate.get("sample_size_risk", ""),
        "notes": candidate.get("notes", ""),
    }


def _infer_screening_decision(candidate: dict[str, Any]) -> str:
    data_gate = str(candidate.get("data_gate", ""))
    sector_type = str(candidate.get("sector_type", ""))
    sample_size_risk = str(candidate.get("sample_size_risk", ""))
    basket_role = str(candidate.get("basket_role", ""))
    if data_gate == "blocked" and sector_type == "cyclical":
        return "blocked_by_cycle_data_gate"
    if data_gate == "blocked":
        return "blocked_by_data_gate"
    if data_gate == "strategy_candidate_failed":
        return "archived_strategy_candidate_failed"
    if data_gate == "excluded_by_business_model":
        return "excluded_by_business_model"
    if data_gate == "low_priority_watchlist":
        return "low_priority_watchlist"
    if data_gate == "platform_replication_pending_exports":
        return "platform_replication_pending_before_basket"
    if data_gate in {"needs_manual_research", "specialist_data_partial"}:
        if sample_size_risk == "high" or "specialist" in sector_type:
            return "basket_observation_only"
        return "needs_manual_research_before_formal"
    if basket_role in {"core_candidate", "candidate_after_platform_replication"}:
        return "ready_for_basket_shadow_pool"
    if sample_size_risk == "high":
        return "basket_observation_only"
    return "ready_for_batch_initial_validation"


def _lane_from_decision(decision: str) -> str:
    if decision == "ready_for_basket_shadow_pool":
        return "basket_core_shadow_pool"
    if decision == "needs_manual_research_before_formal":
        return "manual_research_before_formal"
    if decision == "ready_for_batch_initial_validation":
        return "batch_initial_validation"
    if decision == "basket_observation_only":
        return "observation_only"
    if decision == "platform_replication_pending_before_basket":
        return "observation_only"
    if decision == "low_priority_watchlist":
        return "observation_only"
    if decision == "excluded_by_business_model":
        return "blocked_data_repair"
    if decision == "archived_strategy_candidate_failed":
        return "blocked_data_repair"
    if decision.startswith("blocked"):
        return "blocked_data_repair"
    return "manual_research_before_formal"


def _priority(candidate: dict[str, Any], decision: str, lane: str) -> int:
    sector_id = str(candidate.get("sector_id", ""))
    preferred_order = {
        "bank": 10,
        "utilities_electricity": 11,
        "highway_infrastructure": 12,
        "port_rail_infrastructure": 13,
        "gas_water_operators": 20,
        "telecom_operators": 30,
        "airport_transport_operators": 31,
        "insurance": 40,
        "oil_gas_pipeline_integrated": 50,
        "consumer_staples_cashflow": 60,
        "pharma_medical_services": 70,
        "environmental_project_operators": 90,
        "coal": 91,
    }
    if sector_id in preferred_order:
        return preferred_order[sector_id]
    lane_base = {
        "basket_core_shadow_pool": 10,
        "manual_research_before_formal": 20,
        "batch_initial_validation": 25,
        "observation_only": 40,
        "blocked_data_repair": 90,
    }
    return lane_base.get(lane, 80) + (5 if "blocked" in decision else 0)


def _required_inputs(candidate: dict[str, Any], lane: str) -> list[str]:
    common = ["PIT universe", "real daily open/close prices", "cash dividends with visible dates"]
    sector_id = str(candidate.get("sector_id", ""))
    sector_type = str(candidate.get("sector_type", ""))
    if lane == "basket_core_shadow_pool":
        return common + ["fresh low-vol factors", "frozen sleeve signals", "daily attribution inputs"]
    if lane == "observation_only":
        if candidate.get("data_gate") == "low_priority_watchlist":
            return ["coarse data availability note", "reason to revisit", "PM-approved priority upgrade"]
        if sector_id == "insurance":
            return ["multi-year PIT EV/NBV or P/EV", "solvency disclosures", "interest-rate state", "equity-market state"]
        if sector_id == "telecom_operators":
            return common + ["capex cycle review", "operator purity evidence", "small-sample sleeve policy"]
        return common + ["small-sample or specialist sleeve policy"]
    if lane == "blocked_data_repair":
        if candidate.get("data_gate") == "excluded_by_business_model":
            return ["PM-approved new strategy family", "fresh industry thesis", "data availability note"]
        if "cyclical" in sector_type:
            return ["commodity price state", "output/inventory state", "spread/profit state", "PIT business exposure"]
        return ["business-purity split", "receivables/project cash-flow review", "original-report evidence"]
    if lane == "manual_research_before_formal":
        return common + ["industry knowledge packet", "business-purity evidence", "FCF/capex-quality gate", "external state map"]
    return common + ["Research proposal", "formal validation packet"]


def _graduation_gate(candidate: dict[str, Any], lane: str) -> str:
    if lane == "basket_core_shadow_pool":
        return "paper_trading_record_or_platform_attribution_packet_completed"
    if lane == "manual_research_before_formal":
        return "industry_knowledge_and_data_availability_gate_passed"
    if lane == "batch_initial_validation":
        return "baseline_ic_rankic_rolling_ablation_robustness_passed"
    if lane == "observation_only":
        if candidate.get("data_gate") == "low_priority_watchlist":
            return "PM_priority_upgrade_before_research_or_validation"
        return "PM_approves_specialist_or_small_sample_policy"
    if str(candidate.get("data_gate")) == "excluded_by_business_model":
        return "new_strategy_family_required_before_modeling"
    if str(candidate.get("sector_type")) == "cyclical":
        return "cycle_data_gate_passed_before_modeling"
    return "hard_data_gate_repaired_before_modeling"


def _stop_condition(lane: str, config: dict[str, Any]) -> str:
    no_evidence_loops = config.get("timebox_policy", {}).get("stop_after_no_new_evidence_loops", 2)
    if lane == "basket_core_shadow_pool":
        return "stop if frozen logic change is required or platform exports remain unavailable"
    if lane == "blocked_data_repair":
        return f"stop after {no_evidence_loops} loops without new source evidence; archive blocker packet"
    if lane == "observation_only":
        return "stop if sample policy or specialist data is not approved"
    return f"stop after {no_evidence_loops} loops without new evidence or if the next stage gate needs PM approval"


def _write_agent_queues(queue_dir: Path, rows: list[dict[str, Any]]) -> dict[str, str]:
    queue_dir.mkdir(parents=True, exist_ok=True)
    queue_paths: dict[str, str] = {}
    agents = {
        "Project Manager Agent": "project_manager_queue.csv",
        "Research Agent": "research_agent_queue.csv",
        "Quant Validation Agent": "quant_validation_agent_queue.csv",
        "Engineering Agent": "engineering_agent_queue.csv",
    }
    for agent, filename in agents.items():
        path = queue_dir / filename
        agent_rows = [row for row in rows if row["next_agent"] == agent]
        write_csv_rows(path, ROADMAP_FIELDS, agent_rows)
        queue_paths[agent] = str(path)
    return queue_paths


def _build_summary(
    config: dict[str, Any],
    rows: list[dict[str, Any]],
    csv_path: Path,
    report_path: Path,
    queue_paths: dict[str, str],
) -> dict[str, Any]:
    lane_counts: dict[str, int] = {}
    next_agent_counts: dict[str, int] = {}
    for row in rows:
        lane_counts[row["pm_lane"]] = lane_counts.get(row["pm_lane"], 0) + 1
        next_agent_counts[row["next_agent"]] = next_agent_counts.get(row["next_agent"], 0) + 1
    return {
        "schema_version": 1,
        "project": config.get("project"),
        "experiment_layer": config.get("experiment_layer"),
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "objective": config.get("objective"),
        "sector_count": len(rows),
        "lane_counts": lane_counts,
        "next_agent_counts": next_agent_counts,
        "factor_policy": config.get("factor_policy", {}),
        "csv_path": str(csv_path),
        "report_path": str(report_path),
        "agent_queue_paths": queue_paths,
        "pm_decision": "Broad replication roadmap is active, but no new sector is promoted to formal modeling or acceptance by this packet.",
    }


def _build_report(summary: dict[str, Any], rows: list[dict[str, Any]], config: dict[str, Any]) -> str:
    lines = [
        "# V5.8 Dividend Low-Vol Cash-Flow Sector Replication Roadmap",
        "",
        f"Created at UTC: `{summary['created_at_utc']}`",
        "",
        "## PM Decision",
        "",
        str(summary["pm_decision"]),
        "",
        "## Core Factor Policy",
        "",
        f"- Primary: `{', '.join(config.get('factor_policy', {}).get('primary_cross_sector_factors', []))}`",
        f"- Supporting: `{', '.join(config.get('factor_policy', {}).get('supporting_factors', []))}`",
        f"- Enhancement only after sector approval: `{', '.join(config.get('factor_policy', {}).get('sector_approved_enhancements', []))}`",
        f"- Not current mainline: `{', '.join(config.get('factor_policy', {}).get('not_current_mainline', []))}`",
        "",
        "## Lane Counts",
        "",
        "| Lane | Count |",
        "| --- | ---: |",
    ]
    for lane, count in sorted(summary["lane_counts"].items()):
        lines.append(f"| `{lane}` | {count} |")
    lines.extend(
        [
            "",
            "## Agent Work Queue",
            "",
            "| Priority | Sector | Lane | Next Agent | Timebox | Graduation Gate |",
            "| ---: | --- | --- | --- | ---: | --- |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['priority_rank']} | {row['display_name']} | `{row['pm_lane']}` | `{row['next_agent']}` | {row['timebox_minutes']} | `{row['graduation_gate']}` |"
        )
    lines.extend(
        [
            "",
            "## Agent Queue Files",
            "",
            "| Agent | Queue file |",
            "| --- | --- |",
        ]
    )
    for agent, path in summary.get("agent_queue_paths", {}).items():
        lines.append(f"| `{agent}` | `{path}` |")
    lines.extend(
        [
            "",
            "## PM Operating Rules",
            "",
            "- Keep V5.7f frozen; do not tune the current ETF basket while expanding coverage.",
            "- Research Agent learns the industry first, then writes hypotheses; Quant Agent rejects or validates them with PIT evidence.",
            "- Engineering Agent receives only frozen candidates or data-pipeline tasks; it does not create investment theory.",
            "- Failed sectors are useful evidence when their blocker packet explains what is missing and when to restart.",
            "- Historical performance alone is never sufficient evidence for accepting a strategy.",
            "",
        ]
    )
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload

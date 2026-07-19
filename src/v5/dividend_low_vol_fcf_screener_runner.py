from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import write_csv_rows, write_json_file


DEFAULT_CONFIG = Path("config/dividend_low_vol_fcf_sector_candidates_v56.json")
DEFAULT_STATUS_REGISTRY = Path("docs/governance/status_registry.json")
DEFAULT_OUT_DIR = Path("validation_formal_v56_batch_screening")


@dataclass(frozen=True)
class BatchScreeningResult:
    output_dir: Path
    csv_path: Path
    json_path: Path
    report_path: Path
    sector_count: int
    core_candidate_count: int
    manual_research_count: int
    blocked_count: int


CSV_FIELDS = [
    "sector_id",
    "display_name",
    "sector_type",
    "basket_role",
    "pm_screening_decision",
    "allowed_next_action",
    "registry_status",
    "next_gate",
    "data_gate",
    "pit_universe_gate",
    "business_purity_gate",
    "dividend_gate",
    "fcf_gate",
    "low_vol_gate",
    "external_state_burden",
    "sample_size_risk",
    "knowledge_artifacts_existing",
    "knowledge_artifacts_total",
    "missing_knowledge_artifacts",
    "blockers",
    "notes",
]


def run_dividend_low_vol_fcf_batch_screening(
    config_path: Path = DEFAULT_CONFIG,
    status_registry_path: Path = DEFAULT_STATUS_REGISTRY,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> BatchScreeningResult:
    config = _read_json(config_path)
    registry = _read_json(status_registry_path)
    strategies = registry.get("strategies", [])
    strategy_by_id = {str(item.get("strategy_id")): item for item in strategies}

    rows: list[dict[str, Any]] = []
    for candidate in config.get("candidate_sectors", []):
        rows.append(_screen_candidate(candidate, strategy_by_id))

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "sector_screening_results.csv"
    json_path = out_dir / "sector_screening_summary.json"
    report_path = out_dir / "sector_screening_pm_report.md"

    write_csv_rows(csv_path, CSV_FIELDS, rows)
    summary = _build_summary(config, rows, csv_path, report_path)
    write_json_file(json_path, summary)
    report_path.write_text(_build_report(summary, rows), encoding="utf-8")

    return BatchScreeningResult(
        output_dir=out_dir,
        csv_path=csv_path,
        json_path=json_path,
        report_path=report_path,
        sector_count=len(rows),
        core_candidate_count=sum(1 for row in rows if row["pm_screening_decision"] == "ready_for_basket_shadow_pool"),
        manual_research_count=sum(1 for row in rows if row["pm_screening_decision"] == "needs_manual_research_before_formal"),
        blocked_count=sum(1 for row in rows if row["pm_screening_decision"].startswith("blocked")),
    )


def _screen_candidate(candidate: dict[str, Any], strategy_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    strategy_ids = [str(item) for item in candidate.get("strategy_ids", [])]
    registry_items = [strategy_by_id[item] for item in strategy_ids if item in strategy_by_id]
    registry_statuses = sorted({status for item in registry_items for status in item.get("current_status", [])})
    blockers = sorted({blocker for item in registry_items for blocker in item.get("blockers", [])})
    next_gates = sorted({str(item.get("next_gate")) for item in registry_items if item.get("next_gate")})

    artifacts = [Path(str(item)) for item in candidate.get("knowledge_artifacts", [])]
    existing_artifacts = [str(path) for path in artifacts if path.exists()]
    missing_artifacts = [str(path) for path in artifacts if not path.exists()]

    decision, action = _decide(candidate, registry_statuses)

    return {
        "sector_id": candidate.get("sector_id", ""),
        "display_name": candidate.get("display_name", ""),
        "sector_type": candidate.get("sector_type", ""),
        "basket_role": candidate.get("basket_role", ""),
        "pm_screening_decision": decision,
        "allowed_next_action": action,
        "registry_status": ";".join(registry_statuses),
        "next_gate": ";".join(next_gates),
        "data_gate": candidate.get("data_gate", ""),
        "pit_universe_gate": candidate.get("pit_universe_gate", ""),
        "business_purity_gate": candidate.get("business_purity_gate", ""),
        "dividend_gate": candidate.get("dividend_gate", ""),
        "fcf_gate": candidate.get("fcf_gate", ""),
        "low_vol_gate": candidate.get("low_vol_gate", ""),
        "external_state_burden": candidate.get("external_state_burden", ""),
        "sample_size_risk": candidate.get("sample_size_risk", ""),
        "knowledge_artifacts_existing": len(existing_artifacts),
        "knowledge_artifacts_total": len(artifacts),
        "missing_knowledge_artifacts": ";".join(missing_artifacts),
        "blockers": " | ".join(blockers),
        "notes": candidate.get("notes", ""),
    }


def _decide(candidate: dict[str, Any], registry_statuses: list[str]) -> tuple[str, str]:
    data_gate = str(candidate.get("data_gate", ""))
    sector_type = str(candidate.get("sector_type", ""))
    sample_size_risk = str(candidate.get("sample_size_risk", ""))
    basket_role = str(candidate.get("basket_role", ""))

    if data_gate == "blocked" and sector_type == "cyclical":
        return "blocked_by_cycle_data_gate", "repair cycle-state and PIT business-exposure data only"
    if data_gate == "blocked":
        return "blocked_by_data_gate", "repair data before any modeling"
    if data_gate in {"needs_manual_research", "specialist_data_partial"}:
        if sample_size_risk == "high" or "specialist" in sector_type:
            return "basket_observation_only", "track as specialist or concentrated sleeve; do not run broad IC acceptance"
        return "needs_manual_research_before_formal", "Research Agent repairs operating-purity and field evidence"
    if "platform_replication_passed" in registry_statuses or "paper_trading_started" in registry_statuses:
        return "ready_for_basket_shadow_pool", "include in basket shadow pool after basket rules and low-vol module exist"
    if "formal_strategy_candidate" in registry_statuses and basket_role in {"core_candidate", "candidate_after_platform_replication"}:
        return "ready_for_basket_shadow_pool", "include in basket shadow pool after pending replication notes are resolved"
    if sample_size_risk == "high":
        return "basket_observation_only", "track as concentrated sleeve; sample is too small for formal cross-sectional inference"
    return "ready_for_batch_initial_validation", "run batch baseline, IC, RankIC, rolling, ablation and robustness"


def _build_summary(config: dict[str, Any], rows: list[dict[str, Any]], csv_path: Path, report_path: Path) -> dict[str, Any]:
    decisions: dict[str, int] = {}
    for row in rows:
        decisions[row["pm_screening_decision"]] = decisions.get(row["pm_screening_decision"], 0) + 1
    return {
        "schema_version": 1,
        "project": config.get("project"),
        "experiment_layer": config.get("experiment_layer"),
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "sector_count": len(rows),
        "decision_counts": decisions,
        "global_missing_modules": config.get("global_missing_modules", []),
        "csv_path": str(csv_path),
        "report_path": str(report_path),
        "pm_rule": "Batch screening is allowed; formal candidacy and acceptance remain blocked until all gates pass.",
    }


def _build_report(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    project = str(summary.get("project") or "dividend_low_vol_sector_screening")
    lines = [
        f"# {project} Batch Screening PM Report",
        "",
        f"Created at UTC: `{summary['created_at_utc']}`",
        "",
        "## PM Decision",
        "",
        "Stage 1 batch screening is completed. This report classifies sectors for the dividend low-volatility, OCF and sector-approved FCF basket path. It is not strategy acceptance.",
        "",
        "## Decision Counts",
        "",
        "| Decision | Count |",
        "| --- | ---: |",
    ]
    for decision, count in sorted(summary["decision_counts"].items()):
        lines.append(f"| `{decision}` | {count} |")
    lines.extend(
        [
            "",
            "## Sector Results",
            "",
            "| Sector | Decision | Allowed next action | Key note |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['display_name']} | `{row['pm_screening_decision']}` | {row['allowed_next_action']} | {row['notes']} |"
        )
    lines.extend(
        [
            "",
            "## Global Missing Modules",
            "",
        ]
    )
    for item in summary.get("global_missing_modules", []):
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## PM Next Steps",
            "",
            "1. Keep ready sectors in the shadow basket only after their PIT panels and low-vol factors are fresh.",
            "2. Send manual-research sectors to Research Agent for business purity, industry knowledge and FCF/capex-quality gates.",
            "3. Keep observation-only sectors out of broad IC acceptance unless PM approves a small-sample sleeve policy.",
            "4. Keep blocked sectors out of modeling until their data gates are repaired.",
            "5. Keep 2021-2026 as platform-confirmation context, not accepted-strategy evidence.",
            "",
            "## Hard Rule",
            "",
            "Historical performance alone is never sufficient evidence for accepting a strategy.",
            "",
        ]
    )
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload

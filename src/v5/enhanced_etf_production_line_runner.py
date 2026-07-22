from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows_if_exists, write_csv_rows, write_json_file


DEFAULT_MASTER_TABLE = Path("docs/governance/v5a_broad_sector_coverage_master_table.csv")
DEFAULT_BASKET_CONFIG = Path("config/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f.json")
DEFAULT_STATUS_REGISTRY = Path("docs/governance/status_registry.json")
DEFAULT_OUT_DIR = Path("enhanced_etf_production_lines_v5") / "current"

SLEEVE_FIELDS = [
    "sector_id",
    "display_name",
    "production_lane",
    "is_active_v57f_sleeve",
    "basket_role",
    "pm_bucket",
    "basket_eligibility",
    "next_agent",
    "allowed_next_action",
    "blocked_action",
    "data_gate",
    "external_state_burden",
    "sample_size_risk",
    "panel_csv",
    "price_csv",
    "dividend_csv",
    "panel_exists",
    "price_exists",
    "dividend_exists",
    "required_before_engineering",
    "engineering_gate",
    "pm_note",
]

PLAN_FIELDS = [
    "priority",
    "stage",
    "owner",
    "action",
    "input",
    "output",
    "gate",
    "status",
]


@dataclass(frozen=True)
class EnhancedEtfProductionLineResult:
    output_dir: Path
    sleeve_registry_csv: Path
    sleeve_registry_json: Path
    refresh_plan_csv: Path
    summary_json: Path
    report_path: Path
    active_sleeve_count: int
    engineering_ready: bool


def build_enhanced_etf_production_line(
    master_table: Path = DEFAULT_MASTER_TABLE,
    basket_config: Path = DEFAULT_BASKET_CONFIG,
    status_registry: Path = DEFAULT_STATUS_REGISTRY,
    out_dir: Path = DEFAULT_OUT_DIR,
    *,
    strategy_id: str | None = None,
    next_clean_rebalance_date: str = "2026-10-08",
) -> EnhancedEtfProductionLineResult:
    master_rows = read_csv_rows_if_exists(master_table)
    if not master_rows:
        raise FileNotFoundError(f"master sector table not found or empty: {master_table}")
    config = _read_json(basket_config)
    registry = _read_json(status_registry) if status_registry.exists() else {}
    project = strategy_id or str(config.get("project") or "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f")

    active_by_sector = {str(item.get("sector_id")): item for item in config.get("sectors", [])}
    status_item = _find_strategy(registry, project)
    sleeve_rows = [_build_sleeve_row(row, active_by_sector) for row in master_rows]
    sleeve_rows.sort(key=lambda row: (_lane_priority(row["production_lane"]), row["sector_id"]))

    plan_rows = _build_refresh_plan(project, basket_config, next_clean_rebalance_date)
    evidence = _collect_evidence(project)
    engineering_ready = _engineering_ready(sleeve_rows, evidence)

    out_dir.mkdir(parents=True, exist_ok=True)
    sleeve_registry_csv = out_dir / "sleeve_registry.csv"
    sleeve_registry_json = out_dir / "sleeve_registry_summary.json"
    refresh_plan_csv = out_dir / "refresh_plan.csv"
    summary_json = out_dir / "production_line_summary.json"
    report_path = out_dir / "production_line_report.md"

    write_csv_rows(sleeve_registry_csv, SLEEVE_FIELDS, sleeve_rows)
    write_csv_rows(refresh_plan_csv, PLAN_FIELDS, plan_rows)
    sleeve_summary = _build_sleeve_summary(sleeve_rows)
    write_json_file(sleeve_registry_json, sleeve_summary)
    summary = _build_summary(
        project=project,
        master_table=master_table,
        basket_config=basket_config,
        status_registry=status_registry,
        sleeve_rows=sleeve_rows,
        plan_rows=plan_rows,
        evidence=evidence,
        status_item=status_item,
        next_clean_rebalance_date=next_clean_rebalance_date,
        engineering_ready=engineering_ready,
        sleeve_registry_csv=sleeve_registry_csv,
        refresh_plan_csv=refresh_plan_csv,
        report_path=report_path,
    )
    write_json_file(summary_json, summary)
    report_path.write_text(_build_report(summary, sleeve_rows, plan_rows), encoding="utf-8")

    return EnhancedEtfProductionLineResult(
        output_dir=out_dir,
        sleeve_registry_csv=sleeve_registry_csv,
        sleeve_registry_json=sleeve_registry_json,
        refresh_plan_csv=refresh_plan_csv,
        summary_json=summary_json,
        report_path=report_path,
        active_sleeve_count=sum(1 for row in sleeve_rows if row["is_active_v57f_sleeve"] == "yes"),
        engineering_ready=engineering_ready,
    )


def _build_sleeve_row(master: dict[str, str], active_by_sector: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sector_id = str(master.get("sector_id") or "")
    active = active_by_sector.get(sector_id)
    lane = _production_lane(master, active is not None)
    panel = str(active.get("panel_csv") or "") if active else ""
    price = str(active.get("price_csv") or "") if active else ""
    dividend = str(active.get("dividend_csv") or "") if active else ""
    exists = {name: _path_exists(value) for name, value in {"panel": panel, "price": price, "dividend": dividend}.items()}
    engineering_gate, required = _engineering_gate(master, lane, exists)
    return {
        "sector_id": sector_id,
        "display_name": master.get("display_name", ""),
        "production_lane": lane,
        "is_active_v57f_sleeve": "yes" if active else "no",
        "basket_role": active.get("role", "") if active else "",
        "pm_bucket": master.get("pm_bucket", ""),
        "basket_eligibility": master.get("basket_eligibility", ""),
        "next_agent": master.get("next_agent", ""),
        "allowed_next_action": master.get("allowed_next_action", ""),
        "blocked_action": master.get("blocked_action", ""),
        "data_gate": master.get("data_gate", ""),
        "external_state_burden": master.get("external_state_burden", ""),
        "sample_size_risk": master.get("sample_size_risk", ""),
        "panel_csv": panel,
        "price_csv": price,
        "dividend_csv": dividend,
        "panel_exists": _yes_no(exists["panel"]),
        "price_exists": _yes_no(exists["price"]),
        "dividend_exists": _yes_no(exists["dividend"]),
        "required_before_engineering": required,
        "engineering_gate": engineering_gate,
        "pm_note": _pm_note(master, lane),
    }


def _production_lane(master: dict[str, str], active: bool) -> str:
    bucket = str(master.get("pm_bucket") or "")
    eligibility = str(master.get("basket_eligibility") or "")
    sector_id = str(master.get("sector_id") or "")
    if active:
        return "core_frozen_refresh"
    if bucket == "core_or_observation_refresh_no_tuning" and eligibility == "eligible_or_existing_sleeve_refresh_only":
        return "observation_refresh_only"
    if "repair" in eligibility or bucket == "research_repair_only":
        return "research_repair_queue"
    if bucket.startswith("blocked"):
        return "data_gate_blocked"
    if bucket == "archived_or_rejected":
        return "archived_or_rejected"
    if bucket == "excluded_from_current_mandate":
        return "excluded_from_current_mandate"
    if sector_id:
        return "pm_review"
    return "unknown"


def _engineering_gate(master: dict[str, str], lane: str, exists: dict[str, bool]) -> tuple[str, str]:
    if lane == "core_frozen_refresh":
        missing = [name for name, ok in exists.items() if not ok]
        if missing:
            return "blocked_missing_active_sleeve_files", ";".join(f"repair_{name}_csv" for name in missing)
        return "ready_for_local_refresh", "run_local_daily_simulation_and_rebalance_order_health"
    if lane == "observation_refresh_only":
        return "not_core_engineering_observation_only", "PM_approval_required_before_basket_inclusion"
    if lane == "research_repair_queue":
        return "not_engineering_handoff", "Research_repairs_knowledge_data_or_specialist_gate"
    if lane == "data_gate_blocked":
        return "blocked_before_modeling", "repair_hard_data_gate_before_validation"
    if lane == "archived_or_rejected":
        return "archived_not_engineering", "new_research_hypothesis_required_before_restart"
    if lane == "excluded_from_current_mandate":
        return "excluded_not_engineering", "new_strategy_family_required"
    return "pm_review_required", "PM_decision_required"


def _pm_note(master: dict[str, str], lane: str) -> str:
    sector_id = str(master.get("sector_id") or "")
    if lane == "core_frozen_refresh":
        return "Existing V57f sleeve; refresh only, no tuning."
    if lane == "observation_refresh_only":
        return f"{sector_id} can be tracked, but cannot be silently added to frozen V57f."
    if lane == "research_repair_queue":
        return "Research/Quant loop may continue, but Engineering cannot receive it yet."
    if lane == "data_gate_blocked":
        return "Do not model until PIT and source data gate is repaired."
    if lane == "archived_or_rejected":
        return "Archive unless a new ex-ante hypothesis and source data appear."
    if lane == "excluded_from_current_mandate":
        return "Outside the current dividend low-volatility OCF/FCF mandate."
    return "Needs PM review."


def _build_refresh_plan(project: str, basket_config: Path, next_clean_rebalance_date: str) -> list[dict[str, str]]:
    signals = Path("validation_formal_v57f_etf_constructor") / "basket_rebalance_signals.csv"
    daily_dir = Path("local_daily_backtests_v57f_etf") / project
    daily_returns = daily_dir / "daily_returns.csv"
    formal = Path("validation_formal_v57f_etf") / project / "basket_formal_validation_summary.json"
    daily_summary = daily_dir / "summary.json"
    overfit = Path("validation_overfit_v57f_etf") / project / "overfit_audit_summary.json"
    ablation = Path("validation_ablation_v57f_etf") / project / "basket_ablation_summary.json"
    pm_gate = Path("pm_gate_packets_v57f") / project / "basket_pm_gate_summary.json"
    paper_gate = Path("basket_forward_paper_gates_v57f") / project / "forward_paper_gate_summary.json"
    dashboard = Path("basket_governance_dashboards_v57f") / project / "basket_governance_dashboard_summary.json"
    route = Path("basket_pm_action_routes_v57f") / project / "basket_pm_action_route_summary.json"
    return [
        _plan(1, "freeze_check", "Project Manager Agent", "Confirm active sleeves are unchanged", str(basket_config), "sleeve_registry.csv", "no_new_sleeves", "completed_by_runner"),
        _plan(2, "signal_refresh", "Engineering Agent", "Rebuild frozen basket signals", str(basket_config), str(signals), "quarterly_signal_file_exists", _exists_status(signals)),
        _plan(3, "local_daily_refresh", "Engineering Agent", "Run local JoinQuant-like daily simulation", str(signals), str(daily_summary), "rebalance_order_health_passed", _exists_status(daily_summary)),
        _plan(4, "formal_validation_refresh", "Quant Validation Agent", "Refresh rolling, baseline, IC/RankIC and robustness", str(daily_returns), str(formal), "formal_validation_completed", _exists_status(formal)),
        _plan(5, "failure_attribution", "Quant Validation Agent", "Refresh weak-year and detractor attribution", str(daily_dir), "validation_attribution_v57f_etf", "diagnosis_not_tuning", _exists_status(Path("validation_attribution_v57f_etf") / project / "failure_attribution_summary.json")),
        _plan(6, "ablation_refresh", "Quant Validation Agent", "Refresh basket ablation cases", str(basket_config), str(ablation), "no_blocked_cases", _exists_status(ablation)),
        _plan(7, "overfit_audit", "Engineering Agent", "Run anti-overfit and leakage audit", str(daily_returns), str(overfit), "blocker_count_zero", _exists_status(overfit)),
        _plan(8, "pm_gate", "Project Manager Agent", "Combine formal, daily, ablation and overfit evidence", str(formal), str(pm_gate), "blocker_count_zero", _exists_status(pm_gate)),
        _plan(9, "forward_paper_gate", "Project Manager Agent", f"Prepare clean paper window {next_clean_rebalance_date}", str(pm_gate), str(paper_gate), "pending_clean_future_rebalance", _exists_status(paper_gate)),
        _plan(10, "dashboard", "Project Manager Agent", "Build governance dashboard and action route", str(paper_gate), str(dashboard), "blocked_actions_visible", _exists_status(dashboard)),
        _plan(11, "action_route", "Project Manager Agent", "Route next owner and stop/continue state", str(dashboard), str(route), "no_tuning_no_platform_claim", _exists_status(route)),
    ]


def _plan(priority: int, stage: str, owner: str, action: str, input_path: str, output: str, gate: str, status: str) -> dict[str, str]:
    return {
        "priority": str(priority),
        "stage": stage,
        "owner": owner,
        "action": action,
        "input": input_path,
        "output": output,
        "gate": gate,
        "status": status,
    }


def _collect_evidence(project: str) -> dict[str, Any]:
    paths = {
        "construction_summary": Path("validation_formal_v57f_etf_constructor") / "basket_construction_summary.json",
        "daily_summary": Path("local_daily_backtests_v57f_etf") / project / "summary.json",
        "formal_summary": Path("validation_formal_v57f_etf") / project / "basket_formal_validation_summary.json",
        "ablation_summary": Path("validation_ablation_v57f_etf") / project / "basket_ablation_summary.json",
        "overfit_summary": Path("validation_overfit_v57f_etf") / project / "overfit_audit_summary.json",
        "pm_gate_summary": Path("pm_gate_packets_v57f") / project / "basket_pm_gate_summary.json",
        "forward_paper_gate_summary": Path("basket_forward_paper_gates_v57f") / project / "forward_paper_gate_summary.json",
        "dashboard_summary": Path("basket_governance_dashboards_v57f") / project / "basket_governance_dashboard_summary.json",
        "action_route_summary": Path("basket_pm_action_routes_v57f") / project / "basket_pm_action_route_summary.json",
    }
    evidence: dict[str, Any] = {}
    for key, path in paths.items():
        evidence[key] = {"path": str(path), "exists": path.exists()}
        if path.exists() and path.suffix == ".json":
            try:
                payload = _read_json(path)
            except (OSError, json.JSONDecodeError):
                payload = {}
            evidence[key]["status"] = payload.get("status") or payload.get("route_status") or payload.get("pm_decision")
            evidence[key]["blocker_count"] = payload.get("blocker_count")
            evidence[key]["needs_review_count"] = payload.get("needs_review_count")
            if key == "daily_summary":
                evidence[key]["rebalance_order_health"] = payload.get("rebalance_order_health", {})
                evidence[key]["metrics"] = payload.get("metrics", {})
            if key == "forward_paper_gate_summary":
                evidence[key]["next_rebalance_date"] = payload.get("next_rebalance_date")
    return evidence


def _engineering_ready(sleeve_rows: list[dict[str, Any]], evidence: dict[str, Any]) -> bool:
    active_ok = all(
        row["engineering_gate"] == "ready_for_local_refresh"
        for row in sleeve_rows
        if row["is_active_v57f_sleeve"] == "yes"
    )
    daily = evidence.get("daily_summary", {})
    order_health = daily.get("rebalance_order_health", {}) if isinstance(daily, dict) else {}
    order_ok = bool(order_health) and not bool(order_health.get("needs_review"))
    pm_gate = evidence.get("pm_gate_summary", {})
    pm_ok = pm_gate.get("exists") and int(pm_gate.get("blocker_count") or 0) == 0
    overfit = evidence.get("overfit_summary", {})
    overfit_ok = overfit.get("exists") and int(overfit.get("blocker_count") or 0) == 0
    return active_ok and order_ok and pm_ok and overfit_ok


def _build_sleeve_summary(sleeve_rows: list[dict[str, Any]]) -> dict[str, Any]:
    lane_counts: dict[str, int] = {}
    gate_counts: dict[str, int] = {}
    for row in sleeve_rows:
        lane_counts[row["production_lane"]] = lane_counts.get(row["production_lane"], 0) + 1
        gate_counts[row["engineering_gate"]] = gate_counts.get(row["engineering_gate"], 0) + 1
    return {
        "schema_version": 1,
        "created_at_utc": _now(),
        "sleeve_count": len(sleeve_rows),
        "active_v57f_sleeve_count": sum(1 for row in sleeve_rows if row["is_active_v57f_sleeve"] == "yes"),
        "lane_counts": lane_counts,
        "engineering_gate_counts": gate_counts,
        "pm_rule": "This registry routes sleeves; it does not promote or tune any strategy.",
    }


def _build_summary(
    *,
    project: str,
    master_table: Path,
    basket_config: Path,
    status_registry: Path,
    sleeve_rows: list[dict[str, Any]],
    plan_rows: list[dict[str, str]],
    evidence: dict[str, Any],
    status_item: dict[str, Any],
    next_clean_rebalance_date: str,
    engineering_ready: bool,
    sleeve_registry_csv: Path,
    refresh_plan_csv: Path,
    report_path: Path,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "project": "v5_enhanced_etf_production_line",
        "strategy_id": project,
        "experiment_layer": "pm_decision_gate",
        "created_at_utc": _now(),
        "status": "engineering_local_refresh_ready_not_platform_replication" if engineering_ready else "needs_review_before_engineering_refresh",
        "engineering_ready": engineering_ready,
        "active_sleeves": [row["sector_id"] for row in sleeve_rows if row["is_active_v57f_sleeve"] == "yes"],
        "observation_sleeves": [row["sector_id"] for row in sleeve_rows if row["production_lane"] == "observation_refresh_only"],
        "blocked_or_repair_sleeves": [
            row["sector_id"]
            for row in sleeve_rows
            if row["production_lane"] in {"research_repair_queue", "data_gate_blocked", "archived_or_rejected"}
        ],
        "next_clean_rebalance_date": next_clean_rebalance_date,
        "source_paths": {
            "master_table": str(master_table),
            "basket_config": str(basket_config),
            "status_registry": str(status_registry),
        },
        "outputs": {
            "sleeve_registry_csv": str(sleeve_registry_csv),
            "refresh_plan_csv": str(refresh_plan_csv),
            "report_path": str(report_path),
        },
        "plan_status_counts": _count_values(plan_rows, "status"),
        "evidence": evidence,
        "registry_status": status_item.get("current_status", []),
        "registry_next_gate": status_item.get("next_gate", ""),
        "pm_rules": [
            "V57f remains frozen; this runner does not tune weights, factors or sleeve membership.",
            "Observation sleeves cannot enter the core basket without a separate PM stage gate.",
            "Platform replication remains blocked until JoinQuant exports are supplied and attributed.",
            "Historical performance alone is never sufficient evidence for accepting a strategy.",
        ],
    }


def _build_report(summary: dict[str, Any], sleeve_rows: list[dict[str, Any]], plan_rows: list[dict[str, str]]) -> str:
    lines = [
        "# V5 Enhanced ETF Production Line",
        "",
        f"Created at UTC: `{summary['created_at_utc']}`",
        "",
        "## PM Decision",
        "",
        f"Status: `{summary['status']}`",
        "",
        "V57f remains frozen. This production line refreshes and routes sleeves; it does not change the strategy.",
        "",
        "## Active Core Sleeves",
        "",
        "| Sleeve | Engineering gate | Data files |",
        "| --- | --- | --- |",
    ]
    for row in sleeve_rows:
        if row["is_active_v57f_sleeve"] == "yes":
            files = f"panel={row['panel_exists']}, price={row['price_exists']}, dividend={row['dividend_exists']}"
            lines.append(f"| `{row['sector_id']}` | `{row['engineering_gate']}` | {files} |")
    lines.extend(
        [
            "",
            "## Observation / Repair Routing",
            "",
            "| Sector | Lane | Next agent | Gate |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in sleeve_rows:
        if row["is_active_v57f_sleeve"] != "yes":
            lines.append(f"| `{row['sector_id']}` | `{row['production_lane']}` | `{row['next_agent']}` | `{row['engineering_gate']}` |")
    lines.extend(
        [
            "",
            "## Refresh Plan",
            "",
            "| # | Stage | Owner | Status | Gate |",
            "| ---: | --- | --- | --- | --- |",
        ]
    )
    for row in plan_rows:
        lines.append(f"| {row['priority']} | `{row['stage']}` | `{row['owner']}` | `{row['status']}` | `{row['gate']}` |")
    lines.extend(
        [
            "",
            "## Engineering Boundary",
            "",
            "- Engineering may rerun local daily simulation, real dividend accounting, holdings, trades, cash logs and `rebalance_order_health`.",
            "- Engineering must not tune returns, change factors, add sleeves, or mark platform replication passed.",
            "- Next clean paper signal remains gated by the future rebalance window.",
            "",
            "## Hard Rule",
            "",
            "Historical performance alone is never sufficient evidence for accepting a strategy.",
            "",
        ]
    )
    return "\n".join(lines)


def _find_strategy(registry: dict[str, Any], strategy_id: str) -> dict[str, Any]:
    for item in registry.get("strategies", []):
        if str(item.get("strategy_id")) == strategy_id:
            return item
    return {}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _path_exists(value: str) -> bool:
    return bool(value) and Path(value).exists()


def _exists_status(path: Path) -> str:
    return "completed_existing_output" if path.exists() else "pending"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _lane_priority(lane: str) -> int:
    order = {
        "core_frozen_refresh": 10,
        "observation_refresh_only": 20,
        "research_repair_queue": 30,
        "data_gate_blocked": 70,
        "archived_or_rejected": 80,
        "excluded_from_current_mandate": 90,
    }
    return order.get(lane, 60)


def _count_values(rows: list[dict[str, str]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(field) or "")
        counts[value] = counts.get(value, 0) + 1
    return counts


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

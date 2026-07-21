from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import write_csv_rows, write_json_file


DEFAULT_CONFIG = Path("config/v5a.3_theory_gated_sector_prevalidation.json")
DEFAULT_STATUS_REGISTRY = Path("docs/governance/status_registry.json")
DEFAULT_OUT_DIR = Path("sector_replication_batches_v5a3") / "theory_gated_prevalidation_current"


CSV_FIELDS = [
    "sector_id",
    "display_name",
    "sector_type",
    "theory_family",
    "primary_theory",
    "primary_factor_priority",
    "value_role",
    "fcf_role",
    "momentum_role",
    "mean_reversion_role",
    "low_vol_role",
    "dividend_role",
    "prevalidation_decision",
    "next_agent",
    "allowed_next_action",
    "blocked_action",
    "data_gate",
    "pit_universe_gate",
    "business_purity_gate",
    "dividend_gate",
    "fcf_gate",
    "low_vol_gate",
    "external_state_burden",
    "sample_size_risk",
    "required_evidence_before_quant",
    "required_quant_tests",
    "notes",
]


@dataclass(frozen=True)
class TheoryGatedPrevalidationResult:
    output_dir: Path
    csv_path: Path
    json_path: Path
    report_path: Path
    sector_count: int
    decision_counts: dict[str, int]


def run_theory_gated_sector_prevalidation(
    config_path: Path = DEFAULT_CONFIG,
    status_registry_path: Path = DEFAULT_STATUS_REGISTRY,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> TheoryGatedPrevalidationResult:
    config = _read_json(config_path)
    status_registry = _read_json(status_registry_path)
    candidates = list(config.get("candidate_sectors") or [])
    if not candidates and config.get("source_sector_config"):
        source_config = _read_json(Path(str(config["source_sector_config"])))
        candidates = list(source_config.get("candidate_sectors") or [])
    rows = [_prevalidate_sector(candidate, status_registry, config) for candidate in candidates]
    decision_counts: dict[str, int] = {}
    for row in rows:
        decision = str(row["prevalidation_decision"])
        decision_counts[decision] = decision_counts.get(decision, 0) + 1

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "theory_gated_sector_prevalidation.csv"
    json_path = out_dir / "theory_gated_sector_prevalidation_summary.json"
    report_path = out_dir / "theory_gated_sector_prevalidation_pm_report.md"
    write_csv_rows(csv_path, CSV_FIELDS, rows)
    summary = _build_summary(config, status_registry_path, csv_path, report_path, rows, decision_counts)
    write_json_file(json_path, summary)
    report_path.write_text(_build_report(summary, rows), encoding="utf-8")
    return TheoryGatedPrevalidationResult(
        output_dir=out_dir,
        csv_path=csv_path,
        json_path=json_path,
        report_path=report_path,
        sector_count=len(rows),
        decision_counts=decision_counts,
    )


def _prevalidate_sector(candidate: dict[str, Any], status_registry: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    sector_id = str(candidate.get("sector_id") or "")
    sector_type = str(candidate.get("sector_type") or "")
    data_gate = str(candidate.get("data_gate") or "")
    sample_size_risk = str(candidate.get("sample_size_risk") or "")
    external_state_burden = str(candidate.get("external_state_burden") or "")
    strategy_statuses = _strategy_statuses(candidate, status_registry)
    theory = _theory_profile(candidate, config)
    decision, next_agent, action, blocked = _decision(candidate, strategy_statuses)

    return {
        "sector_id": sector_id,
        "display_name": candidate.get("display_name", ""),
        "sector_type": sector_type,
        "theory_family": theory["theory_family"],
        "primary_theory": theory["primary_theory"],
        "primary_factor_priority": theory["primary_factor_priority"],
        "value_role": theory["value_role"],
        "fcf_role": theory["fcf_role"],
        "momentum_role": theory["momentum_role"],
        "mean_reversion_role": theory["mean_reversion_role"],
        "low_vol_role": theory["low_vol_role"],
        "dividend_role": theory["dividend_role"],
        "prevalidation_decision": decision,
        "next_agent": next_agent,
        "allowed_next_action": action,
        "blocked_action": blocked,
        "data_gate": data_gate,
        "pit_universe_gate": candidate.get("pit_universe_gate", ""),
        "business_purity_gate": candidate.get("business_purity_gate", ""),
        "dividend_gate": candidate.get("dividend_gate", ""),
        "fcf_gate": candidate.get("fcf_gate", ""),
        "low_vol_gate": candidate.get("low_vol_gate", ""),
        "external_state_burden": external_state_burden,
        "sample_size_risk": sample_size_risk,
        "required_evidence_before_quant": ";".join(_required_evidence(candidate, theory)),
        "required_quant_tests": ";".join(_required_quant_tests(candidate, theory)),
        "notes": _notes(candidate, theory, strategy_statuses),
    }


def _strategy_statuses(candidate: dict[str, Any], status_registry: dict[str, Any]) -> list[str]:
    sector_id = str(candidate.get("sector_id") or "")
    strategies = {
        str(item.get("strategy_id")): item
        for item in status_registry.get("strategies", [])
        if isinstance(item, dict)
    }
    statuses: set[str] = set()
    for strategy_id in candidate.get("strategy_ids", []):
        item = strategies.get(str(strategy_id))
        if not item:
            continue
        statuses.update(str(status) for status in item.get("current_status", []))
    for item in strategies.values():
        if str(item.get("sector") or "") == sector_id:
            statuses.update(str(status) for status in item.get("current_status", []))
    return sorted(statuses)


def _theory_profile(candidate: dict[str, Any], config: dict[str, Any]) -> dict[str, str]:
    sector_id = str(candidate.get("sector_id") or "")
    sector_type = str(candidate.get("sector_type") or "")
    data_gate = str(candidate.get("data_gate") or "")
    fcf_gate = str(candidate.get("fcf_gate") or "")
    low_vol_gate = str(candidate.get("low_vol_gate") or "")
    dividend_gate = str(candidate.get("dividend_gate") or "")

    if data_gate == "excluded_by_business_model":
        primary = "outside_current_dividend_low_vol_cashflow_mandate"
        fcf_role = "not_current_mandate"
        value_role = "not_current_mandate"
    elif "financial" in sector_type:
        primary = "sector_specific_value_and_balance_sheet_quality"
        fcf_role = "not_comparable"
        value_role = "sector_specific_primary_or_support"
    elif "cyclical" in sector_type or sector_id in {"oil_gas_pipeline_integrated", "coal", "steel", "nonferrous_metals", "shipping"}:
        primary = "cycle_aware_ocf_value_with_external_state"
        fcf_role = "blocked_until_cycle_and_capex_state_pass"
        value_role = "state_conditioned_support"
    elif "project_cash_flow_trap" in sector_type:
        primary = "cash_conversion_and_receivables_trap_detection"
        fcf_role = "high_trap_risk"
        value_role = "guarded_support_only"
    elif "consumer" in sector_type or sector_id in {"food_beverage", "home_appliances", "consumer_staples_cashflow"}:
        primary = "cash_flow_quality_and_defensive_demand"
        fcf_role = "potential_enhancement_after_working_capital_review"
        value_role = "valuation_support_after_quality"
    elif "growth" in sector_type or sector_id in {"computer_software", "electronics_semiconductor", "power_equipment_new_energy"}:
        primary = "outside_current_dividend_low_vol_cashflow_mandate"
        fcf_role = "not_current_mandate"
        value_role = "not_current_mandate"
    else:
        primary = "ocf_low_vol_dividend_sustainability"
        fcf_role = "conditional_enhancement" if "usable" in fcf_gate or "enhancement" in fcf_gate else "diagnostic_or_repair_required"
        value_role = "support_after_cashflow_quality"

    momentum_role = "support_state_only_after_turnover_audit"
    mean_reversion_role = "support_only_with_value_trap_guard"
    if sector_id in {"telecom_operators", "insurance"}:
        momentum_role = "observation_only_due_sample_or_specialist_model"
    if "cyclical" in sector_type:
        mean_reversion_role = "blocked_until_ex_ante_cycle_state_exists"

    return {
        "theory_family": "dividend_low_volatility_ocf_fcf_value_momentum_mean_reversion",
        "primary_theory": primary,
        "primary_factor_priority": _factor_priority(primary, fcf_role),
        "value_role": value_role,
        "fcf_role": fcf_role,
        "momentum_role": momentum_role,
        "mean_reversion_role": mean_reversion_role,
        "low_vol_role": "primary_or_required_gate" if low_vol_gate in {"passed", "can_build_from_daily_prices"} else "repair_required",
        "dividend_role": "required_sustainability_gate" if dividend_gate not in {"weak", "unstable"} else "weak_or_blocked",
    }


def _factor_priority(primary: str, fcf_role: str) -> str:
    factors = ["operating_cash_flow_yield", "low_volatility", "dividend_sustainability"]
    if "enhancement" in fcf_role or "potential" in fcf_role:
        factors.append("sector_approved_free_cash_flow_yield")
    if "sector_specific_value" in primary:
        factors = ["sector_specific_value", "dividend_sustainability", "low_volatility"]
    if "cycle_aware" in primary:
        factors = ["operating_cash_flow_yield", "external_cycle_state", "low_volatility", "dividend_sustainability"]
    if "outside_current" in primary:
        factors = ["not_in_current_mandate"]
    return ">".join(factors)


def _decision(candidate: dict[str, Any], strategy_statuses: list[str]) -> tuple[str, str, str, str]:
    data_gate = str(candidate.get("data_gate") or "")
    sector_type = str(candidate.get("sector_type") or "")
    sample_size_risk = str(candidate.get("sample_size_risk") or "")

    if any(
        status in strategy_statuses
        for status in {"strategy_candidate_failed", "archived_not_formal_candidate", "initial_composite_rejected"}
    ):
        return (
            "archived_after_failed_initial_validation",
            "Project Manager Agent",
            "keep archived unless new source data or a new research hypothesis is approved",
            "do not reroute failed sector into ordinary research queue",
        )
    if any(
        status in strategy_statuses
        for status in {
            "platform_replication_passed",
            "paper_trading_started",
            "formal_strategy_candidate",
            "engineering_smoke_test_passed",
            "engineering_local_daily_simulation_passed",
            "local_daily_smoke_test_completed",
        }
    ):
        return (
            "passed_prevalidation_shadow_basket_refresh",
            "Engineering Agent",
            "refresh PIT panel, dividends, low-vol factors and paper-trading inputs without tuning",
            "do not change frozen strategy logic",
        )
    if "research_pit_validation_completed" in strategy_statuses and "not_engineering_handoff" in strategy_statuses:
        return (
            "research_loop_after_initial_validation",
            "Research Agent",
            "repair the documented source, state or business-purity blocker before any new Quant attempt",
            "do not rerun ordinary initial validation or hand off to Engineering",
        )
    if "pharma_specialist_data_gate_blocked" in strategy_statuses:
        return (
            "blocked_by_specialist_data_gate_before_initial_validation",
            "Research Agent",
            "repair PIT R&D, procurement or policy-state fields only",
            "do not run generic pharma OCF/low-vol formal validation",
        )
    if data_gate == "excluded_by_business_model":
        return (
            "excluded_before_initial_validation",
            "Project Manager Agent",
            "archive unless PM opens a separate strategy family",
            "do not run dividend low-vol OCF/FCF validation",
        )
    if data_gate == "blocked" and "cyclical" in sector_type:
        return (
            "blocked_by_cycle_data_gate_before_initial_validation",
            "Research Agent",
            "repair commodity/output/inventory/spread/PIT exposure data only",
            "do not model or backtest",
        )
    if data_gate == "blocked":
        return (
            "blocked_by_data_gate_before_initial_validation",
            "Research Agent",
            "repair PIT, business purity, receivables or original-source data",
            "do not model or backtest",
        )
    if data_gate == "low_priority_watchlist":
        return (
            "low_priority_observation_before_initial_validation",
            "Project Manager Agent",
            "keep in watchlist until higher-priority sectors are exhausted",
            "do not spend Quant/Engineering time yet",
        )
    if data_gate == "platform_replication_pending_exports":
        return (
            "observation_waiting_platform_or_local_attribution",
            "Project Manager Agent",
            "keep as observation sleeve and wait for attribution inputs",
            "do not add to core basket yet",
        )
    if sample_size_risk == "high" or data_gate == "specialist_data_partial":
        return (
            "specialist_or_small_sample_observation_before_initial_validation",
            "Project Manager Agent",
            "define specialist/small-sample policy before Quant validation",
            "do not apply broad IC acceptance standards",
        )
    if data_gate in {"needs_manual_research", "passed_with_review_notes"}:
        return (
            "research_gate_before_quant_initial_validation",
            "Research Agent",
            "complete knowledge, source, business-purity and capex-quality gates",
            "do not run formal validation until source gates pass",
        )
    if data_gate == "passed":
        return (
            "passed_prevalidation_ready_for_quant_initial_validation",
            "Quant Validation Agent",
            "run baseline, IC/RankIC, rolling, ablation, robustness and failure-year analysis",
            "do not tune parameters by return",
        )
    return (
        "needs_pm_review_before_initial_validation",
        "Project Manager Agent",
        "review sector gate because status is not recognized",
        "do not model until routing is clarified",
    )


def _required_evidence(candidate: dict[str, Any], theory: dict[str, str]) -> list[str]:
    evidence = [
        "industry_knowledge_packet",
        "PIT_universe",
        "PIT_financial_visibility",
        "real_daily_open_close_prices",
        "cash_dividend_visibility",
        "low_volatility_factors_60_120_252d",
    ]
    sector_type = str(candidate.get("sector_type") or "")
    if "cycle" in sector_type or "cycle" in theory["primary_theory"]:
        evidence.extend(["external_price_state", "output_or_inventory_state", "spread_or_margin_state", "PIT_business_exposure"])
    if "project_cash_flow_trap" in sector_type:
        evidence.extend(["receivables_quality", "project_revenue_split", "cash_collection_evidence"])
    if "consumer" in sector_type:
        evidence.extend(["working_capital_quality", "inventory_cycle_state", "brand_or_channel_quality_map"])
    if "financial" in sector_type:
        evidence.extend(["sector_specific_balance_sheet_fields", "solvency_or_asset_quality_fields"])
    if "enhancement" in theory["fcf_role"] or "potential" in theory["fcf_role"]:
        evidence.append("capex_quality_gate")
    return evidence


def _required_quant_tests(candidate: dict[str, Any], theory: dict[str, str]) -> list[str]:
    tests = ["baseline", "IC", "RankIC", "rolling_validation", "ablation", "robustness", "failure_year_analysis"]
    tests.extend(["low_volatility_perturbation", "buy_sell_timing_perturbation"])
    if "momentum" in theory["momentum_role"]:
        tests.extend(["momentum_horizon_grid", "turnover_audit"])
    if "mean_reversion" in theory["mean_reversion_role"] or "reversion" in theory["mean_reversion_role"]:
        tests.append("value_trap_guard_ablation")
    if "cycle" in str(candidate.get("sector_type") or ""):
        tests.append("state_bucket_validation")
    return tests


def _notes(candidate: dict[str, Any], theory: dict[str, str], strategy_statuses: list[str]) -> str:
    base = str(candidate.get("notes") or "")
    status = ";".join(strategy_statuses)
    return (
        f"{base} Theory read: {theory['primary_theory']}; FCF role: {theory['fcf_role']}; "
        f"momentum role: {theory['momentum_role']}; mean-reversion role: {theory['mean_reversion_role']}. "
        f"Registry statuses: {status or 'none'}."
    )


def _build_summary(
    config: dict[str, Any],
    status_registry_path: Path,
    csv_path: Path,
    report_path: Path,
    rows: list[dict[str, Any]],
    decision_counts: dict[str, int],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "project": config.get("project"),
        "experiment_layer": config.get("experiment_layer"),
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "theory_gated_prevalidation_completed_not_strategy_acceptance",
        "theory_inputs": config.get("theory_inputs", []),
        "source_sector_config": config.get("source_sector_config"),
        "status_registry": str(status_registry_path),
        "sector_count": len(rows),
        "decision_counts": decision_counts,
        "csv_path": str(csv_path),
        "report_path": str(report_path),
        "pm_rule": "This is initial theory/data prevalidation only. Quant and Engineering gates remain separate.",
    }


def _build_report(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# V5a.3 Theory-Gated Sector Prevalidation PM Report",
        "",
        f"Created at UTC: `{summary['created_at_utc']}`",
        "",
        "## Decision",
        "",
        "All configured sectors were routed through the V5a.2 theory gate. This is not strategy acceptance and not platform replication.",
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
            "## Full Sector Table",
            "",
            "| Sector | Primary theory | Factor priority | Decision | Next agent |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['display_name']} | `{row['primary_theory']}` | `{row['primary_factor_priority']}` | `{row['prevalidation_decision']}` | `{row['next_agent']}` |"
        )
    lines.extend(
        [
            "",
            "## Theory Rules Applied",
            "",
            "- OCF / cash-flow quality and low volatility are the cross-sector core.",
            "- FCF is an enhancement only after sector capex and accounting comparability pass.",
            "- Low PB is sector-specific valuation support, not the global basket mainline.",
            "- Momentum is a support/state hypothesis and requires horizon plus turnover audit.",
            "- Mean reversion requires an ex-ante value-trap guard.",
            "- Cyclical sectors cannot enter validation without price, output/inventory, spread and business-exposure state.",
            "",
            "## Output Paths",
            "",
            f"- CSV: `{summary['csv_path']}`",
            f"- Summary: `{Path(summary['csv_path']).with_name('theory_gated_sector_prevalidation_summary.json')}`",
            f"- Report: `{summary['report_path']}`",
        ]
    )
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload

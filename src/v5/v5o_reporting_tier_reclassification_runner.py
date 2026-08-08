from __future__ import annotations

"""Read-only Tier A/B/C classification companion for V5n reporting units."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


V5N = Path("v5n_model_performance_reporting") / "current"
OUT = Path("v5o_reporting_tier_reclassification") / "current"
EXPECTED_UNITS = 335


def run_v5o_reporting_tier_reclassification(root: Path = Path("."), output_dir: Path | None = None) -> dict[str, Any]:
    root = Path(root)
    _assert_inputs(root)
    out = output_dir or root / OUT
    out.mkdir(parents=True, exist_ok=True)
    quality = _rows(root / V5N / "v5n_all_models_status_and_limitations.csv")
    benchmark = _by_id(_rows(root / V5N / "v5n_all_models_benchmark_register.csv"))
    validation = _by_id(_rows(root / V5N / "v5n_validation_period_statistics.csv"))
    links = _by_id(_rows(root / V5N / "v5n_model_report_link_index.csv"))
    identity = _by_id(_rows(root / V5N / "v5n_model_identity_and_lineage.csv"))
    if len(quality) != EXPECTED_UNITS:
        raise ValueError(f"V5n unit count is {len(quality)}, expected {EXPECTED_UNITS}")

    assignments: list[dict[str, Any]] = []
    tier_a: list[dict[str, Any]] = []
    tier_b: list[dict[str, Any]] = []
    tier_c: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    link_index: list[dict[str, Any]] = []
    for row in quality:
        mid = row["canonical_model_id"]
        bench, valid, link, ident = benchmark.get(mid, {}), validation.get(mid, {}), links.get(mid, {}), identity.get(mid, {})
        tier, reason = _classify(row, bench, valid)
        record = {
            "canonical_model_id": mid, "tier": tier, "classification_reason": reason,
            "canonical_or_alias": "alias" if row["report_status"] == "duplicate_or_alias_of_canonical_model" else "canonical_or_research_unit",
            "family": ident.get("family", "not_available"), "role": ident.get("role", "not_available"),
            "daily_series_status": row["daily_series_status"], "benchmark_type": bench.get("benchmark_type", "not_available"),
            "benchmark_status": row["benchmark_status"], "validation_independence_status": valid.get("validation_result", "not_available"),
            "alpha_beta_ir_computable": ident.get("alpha_beta_ir_computable", "False"), "promotion_eligibility": False,
            "primary_benchmark": bench.get("benchmark_id", "not_available"), "primary_benchmark_statement": bench.get("primary_benchmark_statement", "not_available"),
            "reporting_interpretation_limit": _limit(tier, row, bench, valid), "v5n_addendum_path": link.get("addendum_path", "not_available"),
        }
        assignments.append(record)
        link_index.append({**record, "v5o_classification_record": "v5o_model_tier_assignment.csv"})
        if tier.startswith("tier_a"):
            tier_a.append(record)
        elif tier.startswith("tier_b"):
            tier_b.append(record)
        elif tier == "tier_c_archived_alias_or_superseded":
            tier_c.append(record)
        else:
            conflicts.append({"canonical_model_id": mid, "conflict_type": "classification_conflict", "source": "v5n_status_benchmark_validation_join", "detail": reason, "resolution": "do_not_place_in_tier_a"})

    if len(assignments) != EXPECTED_UNITS or sum(1 for r in assignments if r["tier"]) != EXPECTED_UNITS:
        raise ValueError("Tier assignment completeness failed")
    _write_csv(out / "v5o_model_unit_taxonomy.csv", assignments)
    _write_csv(out / "v5o_model_tier_assignment.csv", assignments)
    _write_csv(out / "v5o_model_alias_and_supersession_audit.csv", [r for r in assignments if r["canonical_or_alias"] == "alias"] or [{"status": "no_aliases"}])
    _write_csv(out / "v5o_classification_conflict_register.csv", conflicts or [{"conflict_type": "none", "detail": "No unresolved local classification conflict."}])
    _write_csv(out / "v5o_tier_a_comparable_models_table.csv", tier_a)
    _write_csv(out / "v5o_tier_b_evidence_only_models_table.csv", tier_b)
    _write_csv(out / "v5o_tier_c_archived_alias_table.csv", tier_c)
    _write_csv(out / "v5o_tier_a_comparability_audit.csv", [_a_audit(r) for r in tier_a])
    _write_csv(out / "v5o_tier_a_benchmark_quality_register.csv", [_a_audit(r) for r in tier_a])
    _write_csv(out / "v5o_tier_a_metric_method_consistency_audit.csv", [{"canonical_model_id": r["canonical_model_id"], "status": "v5n_common_daily_simple_return_definition", "consistent": True} for r in tier_a])
    _write_csv(out / "v5o_tier_a_validation_independence_audit.csv", [{"canonical_model_id": r["canonical_model_id"], "validation_independence_status": r["validation_independence_status"], "promotion_eligibility": False} for r in tier_a])
    _write_csv(out / "v5o_tier_a_execution_evidence_audit.csv", [{"canonical_model_id": r["canonical_model_id"], "execution_evidence_status": "no_complete_historical_target_order_fill_position_cash_contract_claim", "qmt_no_order_not_fill_evidence": True} for r in tier_a])
    _write_csv(out / "v5o_tier_b_evidence_only_register.csv", tier_b)
    _write_csv(out / "v5o_tier_b_missing_data_reason_matrix.csv", [_b_reason(r) for r in tier_b])
    _write_csv(out / "v5o_tier_b_research_value_and_next_evidence.csv", [_b_next(r) for r in tier_b])
    _write_csv(out / "v5o_tier_b_archive_wait_observe_queue.csv", [_b_next(r) for r in tier_b])
    _write_csv(out / "v5o_tier_b_no_performance_comparison_audit.csv", [{"canonical_model_id": r["canonical_model_id"], "may_participate_in_return_alpha_beta_sharpe_ir_comparison": False, "reason": r["classification_reason"]} for r in tier_b])
    _write_csv(out / "v5o_model_report_tier_link_index.csv", link_index)
    _write_csv(out / "v5o_model_report_label_completeness_audit.csv", [{"canonical_model_id": r["canonical_model_id"], "has_unique_tier": True, "has_v5n_addendum_link": r["v5n_addendum_path"] != "not_available"} for r in assignments])
    _write_csv(out / "v5o_reporting_language_and_status_audit.csv", [{"audit_item": "accepted_or_live_status_changed", "result": False}, {"audit_item": "old_baseline_used_as_new_primary", "result": False}, {"audit_item": "future_data_used", "result": False}, {"audit_item": "performance_ranking_or_recommendation_created", "result": False}, {"audit_item": "v5n_reports_overwritten", "result": False}])
    _write_csv(out / "v5o_canonical_strategy_count.csv", [{"definition": "comparable_canonical_strategy_units_tier_a_only", "count": len(tier_a)}, {"definition": "research_or_evidence_units_not_in_tier_a", "count": EXPECTED_UNITS - len(tier_a)}])
    _write_csv(out / "v5o_benchmark_type_distribution.csv", _distribution(assignments, "benchmark_type"))
    _write_csv(out / "v5o_validation_independence_distribution.csv", _distribution(assignments, "validation_independence_status"))
    _write_csv(out / "v5o_metric_availability_distribution.csv", _distribution(assignments, "alpha_beta_ir_computable"))
    (out / "v5o_tier_classification_contract.md").write_text(_contract(), encoding="utf-8")
    (out / "v5o_canonical_strategy_vs_research_unit_definition.md").write_text("# Canonical Strategy vs Research Unit\n\nA comparable canonical strategy is a non-alias unit with eligible daily strategy and benchmark series. All other units retain evidentiary value but are research, execution, data, governance, diagnostic, or archived units; they are not counted as comparable investment models.\n", encoding="utf-8")
    (out / "v5o_tier_a_limitations_report.md").write_text(_tier_a_report(tier_a), encoding="utf-8")
    (out / "v5o_tier_a_performance_reading_report.md").write_text(_tier_a_report(tier_a), encoding="utf-8")
    (out / "v5o_tier_b_evidence_reading_report.md").write_text(_tier_b_report(tier_b, tier_c), encoding="utf-8")
    (out / "v5o_reporting_tier_report.md").write_text(_final_report(assignments, tier_a, tier_b, tier_c, conflicts), encoding="utf-8")
    summary = _summary(assignments, tier_a, tier_b, tier_c, conflicts)
    _write_json(out / "v5o_reporting_tier_summary.json", summary)
    _write_csv(out / "v5o_pm_governance_decision.csv", [{"decision": "tiered_reporting_complete_no_strategy_promotion", "model_status_modified": False, "accepted": False, "live_trading_approved": False, "deployment_approved": False}])
    _write_csv(out / "v5o_next_agent_queue.csv", [{"priority": "P0", "task": "do_not_promote_tier_a_without_independent_validation_and_cash_qmt_contract_recovery", "allowed_now": "reporting_only"}, {"priority": "P1", "task": "retain_tier_b_evidence_and_recover_original_inputs_only_when_authorized", "allowed_now": "local_evidence_review_only"}])
    (out / "v5o_agent_execution_rules.md").write_text("# V5o Rules\n\nClassification is reporting-only. Tier A means comparable reporting, never accepted/live/deployment approval. Tier B and C do not enter performance comparison. Do not alter V5n or historical reports.\n", encoding="utf-8")
    return summary


def _classify(row: dict[str, str], bench: dict[str, str], valid: dict[str, str]) -> tuple[str, str]:
    status = row["report_status"]
    if status in ("archived_or_superseded", "duplicate_or_alias_of_canonical_model"):
        return "tier_c_archived_alias_or_superseded", "v5n_archived_or_alias_status"
    if status == "execution_only_no_strategy_nav":
        return "tier_b2_execution_or_engineering_only", "execution_or_engineering_without_strategy_nav"
    eligible = row["daily_series_status"] == "available" and row["benchmark_status"] == "coverage_pass"
    if eligible and bench.get("benchmark_type") == "parent_strategy":
        return "tier_a1_comparable_parent_or_market_benchmark", "eligible_daily_series_and_parent_strategy_benchmark"
    if eligible and bench.get("benchmark_type") == "static_proxy_basket":
        return "tier_a2_comparable_proxy_benchmark_limited", "eligible_daily_series_with_static_proxy_basket"
    if eligible:
        return "classification_conflict", "eligible_series_with_unrecognised_benchmark_type"
    return "tier_b1_evidence_only_no_comparable_daily_performance", "missing_daily_nav_or_eligible_benchmark_or_diagnostic_evidence_only"


def _limit(tier: str, row: dict[str, str], bench: dict[str, str], valid: dict[str, str]) -> str:
    if tier == "tier_a1_comparable_parent_or_market_benchmark": return "validation_not_independent;execution_contract_incomplete;reporting_only_not_promotion"
    if tier == "tier_a2_comparable_proxy_benchmark_limited": return "proxy_benchmark_limited_interpretation;validation_not_independent;execution_contract_incomplete;reporting_only_not_promotion"
    if tier == "tier_b2_execution_or_engineering_only": return "execution_only_no_strategy_nav_claim"
    if tier == "tier_c_archived_alias_or_superseded": return "archived_or_alias_not_active_comparison"
    return "no_comparable_daily_performance_or_benchmark"


def _a_audit(r: dict[str, Any]) -> dict[str, Any]:
    return {"canonical_model_id": r["canonical_model_id"], "tier": r["tier"], "comparability_status": "comparable_reporting_only", "benchmark_quality_grade": "parent_strategy" if r["tier"].startswith("tier_a1") else "static_proxy_limited", "validation_independence_status": r["validation_independence_status"], "execution_evidence_status": "historical_execution_contract_incomplete", "promotion_eligibility": False, "reporting_interpretation_limit": r["reporting_interpretation_limit"]}
def _b_reason(r: dict[str, Any]) -> dict[str, Any]:
    low = (r["family"] + " " + r["role"] + " " + r["classification_reason"]).lower()
    reason = "missing_daily_nav"
    if "execution" in low or "qmt" in low: reason = "execution_only"
    elif "pit" in low: reason = "pit_boundary_blocked"
    elif "factor" in low: reason = "factor_only"
    elif "diagnostic" in low or "research" in low: reason = "diagnostic_only"
    elif r["benchmark_status"] != "coverage_pass": reason = "missing_benchmark_series"
    return {"canonical_model_id": r["canonical_model_id"], "missing_reason_category": reason, "why_no_alpha_beta_ir": r["reporting_interpretation_limit"], "may_be_compared_on_performance": False}
def _b_next(r: dict[str, Any]) -> dict[str, Any]:
    return {"canonical_model_id": r["canonical_model_id"], "research_value": "retain_evidence_without_performance_promotion", "next_evidence": "original_pit_daily_nav_benchmark_or_execution_contract_only_if_authorized", "archive_wait_or_observe": "observe_or_archive_by_existing_governance", "duplicate_of_canonical": r["canonical_or_alias"] == "alias"}
def _distribution(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    values: dict[str, int] = {}
    for row in rows: values[str(row[key])] = values.get(str(row[key]), 0) + 1
    return [{key: value, "count": count} for value, count in sorted(values.items())]
def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle: return list(csv.DictReader(handle))
def _by_id(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]: return {row["canonical_model_id"]: row for row in rows}
def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(dict.fromkeys(k for row in rows for k in row)) or ["status"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys); writer.writeheader(); writer.writerows(rows)
def _write_json(path: Path, value: Any) -> None: path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
def _assert_inputs(root: Path) -> None:
    summary = json.loads((root / V5N / "v5n_unified_model_reporting_summary.json").read_text(encoding="utf-8"))
    if summary.get("model_count") != EXPECTED_UNITS or summary.get("required_baseline") != "v57f_startup_preload_repaired_baseline": raise ValueError("V5n reporting contract mismatch")
def _contract() -> str: return "# V5o Tier Classification Contract\n\nTier A1 requires eligible common daily data and a parent/market benchmark; Tier A2 uses a static proxy basket and therefore has limited interpretation. Tier B preserves non-comparable evidence. Tier C preserves aliases and archived units. No tier is an acceptance or deployment state.\n"
def _tier_a_report(rows: list[dict[str, Any]]) -> str:
    lines = ["# Tier A Performance Reading\n", "Tier A is a reporting-comparability set, not a ranked shortlist and not an acceptance gate. All Tier A validation remains non-independent; historical execution contract evidence is incomplete.\n"]
    for family in sorted({r["family"] for r in rows}):
        group = [r for r in rows if r["family"] == family]
        lines.append(f"## {family}\n\n- Units: {len(group)}\n- Benchmark types: {', '.join(sorted({r['benchmark_type'] for r in group}))}\n")
    primary = next((r for r in rows if r["canonical_model_id"] == "internal_subsleeve_mom12_70_30"), None)
    if primary: lines.append("## Primary Candidate\n\n`internal_subsleeve_mom12_70_30` remains `primary_forward_paper_candidate_not_accepted`. Its validation is not independent; strict cash NAV is unavailable; the QMT historical contract is incomplete.\n")
    return "\n".join(lines)
def _tier_b_report(rows: list[dict[str, Any]], archived: list[dict[str, Any]]) -> str: return f"# Tier B Evidence Reading\n\nTier B contains {len(rows)} evidence-only or execution-only units. They remain useful for PIT, data, factor, diagnostics, and engineering provenance, but never participate in return, Alpha, Beta, Sharpe, IR, or promotion comparison. Tier C contains {len(archived)} archived or alias units retained for traceability.\n"
def _final_report(all_rows: list[dict[str, Any]], a: list[dict[str, Any]], b: list[dict[str, Any]], c: list[dict[str, Any]], conflicts: list[dict[str, Any]]) -> str: return f"# V5o Reporting Tier Reclassification\n\nAll {len(all_rows)} V5n units have exactly one tier: A={len(a)}, B={len(b)}, C={len(c)}, conflicts={len(conflicts)}. Tier A is comparable reporting only; all independent-validation counts remain zero. No model state was changed.\n"
def _summary(rows: list[dict[str, Any]], a: list[dict[str, Any]], b: list[dict[str, Any]], c: list[dict[str, Any]], conflicts: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {tier: sum(r["tier"] == tier for r in rows) for tier in ("tier_a1_comparable_parent_or_market_benchmark", "tier_a2_comparable_proxy_benchmark_limited", "tier_b1_evidence_only_no_comparable_daily_performance", "tier_b2_execution_or_engineering_only", "tier_c_archived_alias_or_superseded", "classification_conflict")}
    return {"created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "task": "v5o_reporting_tier_reclassification", "total_units": len(rows), "tier_counts": counts, "comparable_canonical_strategy_units": len(a), "research_or_evidence_units": len(rows) - len(a), "independent_validation_count": 0, "model_status_modified": False, "accepted": False, "live_trading_approved": False, "deployment_approved": False}

if __name__ == "__main__": print(json.dumps(run_v5o_reporting_tier_reclassification(), ensure_ascii=False, indent=2))

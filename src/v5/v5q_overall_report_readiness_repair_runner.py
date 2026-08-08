from __future__ import annotations

"""V5q/V5r: reporting-contract repair and a non-final governance report draft."""

import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


V5N = Path("v5n_model_performance_reporting") / "current"
V5O = Path("v5o_reporting_tier_reclassification") / "current"
V5P = Path("v5p_benchmark_discovery_and_research_sequence") / "current"
QOUT = Path("v5q_overall_report_readiness_repair") / "current"
ROUT = Path("v5r_overall_research_governance_report_draft") / "current"
BASELINE = "v57f_startup_preload_repaired_baseline"
PRIMARY = "internal_subsleeve_mom12_70_30"


def run_v5q_v5r_overall_report_readiness(root: Path = Path("."), q_output: Path | None = None, r_output: Path | None = None, test_statuses: dict[str, str] | None = None) -> dict[str, Any]:
    root = Path(root); _assert_contract(root)
    qout = q_output or root / QOUT; rout = r_output or root / ROUT
    qout.mkdir(parents=True, exist_ok=True); rout.mkdir(parents=True, exist_ok=True)
    tiers = _rows(root / V5O / "v5o_model_tier_assignment.csv")
    metrics = _by_id(_rows(root / V5N / "v5n_formal_backtest_performance_statistics.csv"))
    return_contracts = _rows(root / V5P / "v5p_benchmark_return_contract_audit.csv")
    tier_a = [r for r in tiers if r["tier"].startswith("tier_a")]
    canonical = {r["canonical_model_id"] for r in tiers}
    diagnostic = _diagnostic_audit(root, tiers)
    matrix = _canonical_comparison_matrix(tier_a, canonical, diagnostic)
    evidence = _evidence_manifest(root)
    citations = _citations()
    contract_decision = [{"contract_scope": "direct_etf_economic_exposure_context", "return_contract": r["return_contract"], "formal_alpha_beta_ir_allowed": False, "decision": "price_return_only_no_total_return_chain"} for r in return_contracts]
    readiness = "pass_with_required_disclosures"

    _write_csv(qout / "v5q_benchmark_return_contract_decision.csv", contract_decision)
    _write_csv(qout / "v5q_canonical_comparison_matrix.csv", matrix)
    _write_csv(qout / "v5q_diagnostic_unit_audit.csv", diagnostic)
    _write_csv(qout / "v5q_required_evidence_manifest.csv", evidence)
    _write_csv(qout / "v5q_chapter_citation_map.csv", citations)
    _write_csv(qout / "v5q_reproducibility_freeze_manifest.csv", _freeze_manifest(root, evidence))
    test_statuses = test_statuses or {"v5p_and_v5q_targeted": "not_run_by_runner", "fast": "not_run_by_runner", "standard": "not_run_by_runner", "extended": "not_run"}
    _write_csv(qout / "v5q_test_coverage_and_results.csv", [{"test_scope": scope, "status": status} for scope, status in test_statuses.items()])
    blockers = _blockers()
    _write_csv(qout / "v5q_blockers.csv", blockers)
    _write_csv(qout / "v5q_readiness_gate.csv", [{"readiness_gate": readiness, "p0_downgraded_or_disclosed": True, "strict_cash_nav_available": False, "qmt_contract_complete": False, "independent_forward_paper_exists": False, "allows_draft_only": True, "accepted": False}])
    (qout / "v5q_report.md").write_text(_q_report(matrix, diagnostic, blockers), encoding="utf-8")
    qsummary = {"created_at_utc": _now(), "task": "v5q_overall_report_readiness_repair", "status": readiness, "tier_registry_count": len(tiers), "canonical_comparison_pair_count": sum(r["comparison_allowed"] is True for r in matrix), "etf_total_return_contract_available": False, "v5c_sleeve_weighting_diagnostic_downgraded": True, "model_status_modified": False, "accepted": False}
    _write_json(qout / "v5q_overall_report_readiness_summary.json", qsummary)

    performance = _performance_table(metrics, matrix)
    _write_csv(rout / "v5r_performance_comparison_table.csv", performance)
    _write_csv(rout / "v5r_benchmark_and_return_contract_table.csv", contract_decision)
    _write_csv(rout / "v5r_model_tier_and_status_table.csv", tiers)
    _write_csv(rout / "v5r_execution_and_evidence_appendix.csv", [r for r in tiers if r["tier"].startswith("tier_b2") or r["canonical_model_id"].startswith(("v5d_", "v5e_", "v5h_", "v5i_", "v5j_", "v5m_"))])
    _write_csv(rout / "v5r_unresolved_limitations.csv", blockers)
    _write_csv(rout / "v5r_claim_to_evidence_map.csv", citations)
    (rout / "v5r_executive_summary.md").write_text(_executive_summary(), encoding="utf-8")
    (rout / "v5r_overall_research_governance_report_draft.md").write_text(_draft_report(performance, blockers), encoding="utf-8")
    rsummary = {"created_at_utc": _now(), "task": "v5r_overall_research_governance_report_draft", "status": "draft_only_not_final", "primary_candidate": PRIMARY, "primary_candidate_status": "primary_forward_paper_candidate_not_accepted", "comparable_performance_rows": len(performance), "model_status_modified": False, "accepted": False, "live_trading_approved": False, "deployment_approved": False}
    _write_json(rout / "v5r_report_summary.json", rsummary)
    _write_csv(rout / "v5r_pm_draft_release_decision.csv", [{"decision": "draft_ready_with_required_disclosures_not_final", "accepted": False, "live_trading_approved": False, "deployment_approved": False, "model_status_modified": False}])
    return {"q": qsummary, "r": rsummary}


def _canonical_comparison_matrix(tier_a: list[dict[str, str]], canonical: set[str], diagnostic: list[dict[str, Any]]) -> list[dict[str, Any]]:
    downgraded = {r["canonical_model_id"] for r in diagnostic if r["draft_performance_comparison_allowed"] is False}
    rows = []
    for row in tier_a:
        mid = row["canonical_model_id"]
        allowed = mid in (BASELINE, PRIMARY) and mid not in downgraded
        rows.append({"canonical_model_id": mid, "comparison_group_id": "repaired_baseline_primary_candidate_pair" if allowed else "context_only_not_global_comparison", "comparison_allowed": allowed, "parent_baseline": row["primary_benchmark"], "formal_window": "2021-05-01_to_2026-05-31", "model_layer": row["family"], "return_contract": "local_daily_series_embedded_or_parent_contract", "reason": "same_parent_same_window_canonical_pair" if allowed else "no_global_cross_model_comparison; proxy/sector/execution/diagnostic boundary"})
    return rows


def _diagnostic_audit(root: Path, tiers: list[dict[str, str]]) -> list[dict[str, Any]]:
    path = root / "v5c_sleeve_weighting_diagnostic/current/v5c_sleeve_weighting_daily_nav.csv"
    rows = _rows(path)
    schemes = sorted({r.get("scheme_id", "") for r in rows})
    return [{"canonical_model_id": "v5c_sleeve_weighting_diagnostic", "source_path": str(path.relative_to(root)), "daily_nav_exists": bool(rows), "scheme_count_in_single_file": len(schemes), "first_date": rows[0].get("trade_date", "not_available") if rows else "not_available", "last_date": rows[-1].get("trade_date", "not_available") if rows else "not_available", "start_matches_repaired_signal": bool(rows and rows[0].get("trade_date") == "2021-05-06"), "return_definition_reconstructable_as_single_canonical_strategy": False, "draft_performance_comparison_allowed": False, "decision": "diagnostic_only_no_comparable_performance", "reason": "mixed_scheme_file_and_old_startup_window_prevent_single_canonical_return_contract"}]


def _performance_table(metrics: dict[str, dict[str, str]], matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cols = ("total_return_pct", "annualized_return_pct", "max_drawdown_pct", "annualized_volatility_pct", "sharpe_ratio", "alpha_zero_rf_annualized_pct", "beta_zero_rf", "information_ratio", "excess_return_pct_points", "max_drawdown_delta_pct_points", "observations", "start_date", "end_date")
    return [{"canonical_model_id": r["canonical_model_id"], "comparison_group_id": r["comparison_group_id"], "benchmark_contract_disclosure": "local_daily_parent_strategy_contract; validation_not_independent", **{c: metrics.get(r["canonical_model_id"], {}).get(c, "not_available") for c in cols}} for r in matrix if r["comparison_allowed"]]


def _evidence_manifest(root: Path) -> list[dict[str, Any]]:
    paths = [
        "v5m_p0_closure/current/v5m_p0_closure_summary.json", "v5n_model_performance_reporting/current/v5n_unified_model_reporting_summary.json", "v5o_reporting_tier_reclassification/current/v5o_model_tier_assignment.csv", "v5p_benchmark_discovery_and_research_sequence/current/v5p_benchmark_return_contract_audit.csv", "v5p_benchmark_discovery_and_research_sequence/current/v5p_model_comparison_pairing_matrix.csv", "v5p_benchmark_discovery_and_research_sequence/current/v5p_overall_report_input_manifest.csv", "config/v5_test_tiers.json", "docs/governance/status_registry.json",
    ]
    return [{"source_path": path, "sha256": hashlib.sha256((root / path).read_bytes()).hexdigest() if (root / path).exists() else "not_available", "exists": (root / path).exists(), "required_for_draft": True} for path in paths]


def _citations() -> list[dict[str, str]]:
    return [
        {"chapter": "Research boundary and method", "claim": "repaired baseline and historical boundary", "evidence": "config/v5_active_model_registry.json; config/v5_historical_operation_boundary.json"},
        {"chapter": "Comparable performance", "claim": "only canonical repaired-baseline/primary-candidate pair in draft table", "evidence": "v5q_canonical_comparison_matrix.csv; v5n_formal_backtest_performance_statistics.csv"},
        {"chapter": "Execution and evidence", "claim": "strict cash NAV and QMT contract remain incomplete", "evidence": "v5m_p0_closure/current/v5m_p0_closure_summary.json"},
        {"chapter": "Benchmark limitation", "claim": "direct ETF series are adjusted price return only", "evidence": "v5q_benchmark_return_contract_decision.csv"},
    ]


def _blockers() -> list[dict[str, str]]:
    return [
        {"blocker": "validation_not_independent", "status": "required_disclosure", "effect": "no promotion from historical report"},
        {"blocker": "strict_cash_nav_unavailable", "status": "unresolved", "effect": "no financing-valid historical NAV claim"},
        {"blocker": "qmt_contract_incomplete", "status": "unresolved", "effect": "no exact platform target-order-fill-position-cash attribution"},
        {"blocker": "etf_total_return_contract_unavailable", "status": "required_disclosure", "effect": "ETF is economic context only; no formal ETF alpha beta IR"},
        {"blocker": "future_paper_cycle_not_formed", "status": "unresolved", "effect": "no independent forward evidence"},
    ]


def _q_report(matrix: list[dict[str, Any]], diagnostic: list[dict[str, Any]], blockers: list[dict[str, str]]) -> str:
    return "# V5q Overall Report Readiness Repair\n\n## Repairs\n\n- Direct ETF series are adjusted price-return economic-context references only; no ETF Alpha/Beta/IR is admitted without a local total-return contract.\n- Mini-report generic labels are excluded from the canonical comparison matrix.\n- `v5c_sleeve_weighting_diagnostic` is diagnostic-only because its mixed-scheme daily file starts on the old chain and cannot be reconstructed as one canonical strategy.\n\n## Allowed Draft Comparison\n\nOnly the repaired baseline and `internal_subsleeve_mom12_70_30` share the required canonical parent/window contract for the draft performance table.\n\n## Required Disclosures\n\n" + "\n".join(f"- `{r['blocker']}`: {r['effect']}" for r in blockers) + "\n"
def _executive_summary() -> str: return "# V5r Executive Summary\n\nV57f repaired baseline remains the frozen reference. `internal_subsleeve_mom12_70_30` remains the sole primary forward/paper candidate, not accepted. This draft reports research and governance evidence, not an investment recommendation or a performance ranking. Its historical comparison is non-independent; strict cash NAV, exact QMT contract attribution, ETF total-return comparison, and forward paper evidence remain incomplete.\n"
def _draft_report(performance: list[dict[str, Any]], blockers: list[dict[str, str]]) -> str:
    table = "\n".join("| " + " | ".join(str(r.get(k, "")) for k in ("canonical_model_id", "total_return_pct", "max_drawdown_pct", "sharpe_ratio", "alpha_zero_rf_annualized_pct", "beta_zero_rf", "information_ratio")) + " |" for r in performance)
    return "# V5 Overall Research and Governance Report Draft\n\n**Status: draft only. Not final; not accepted; not live approved.**\n\n## 1. Research Boundary and Method\n\nFormal window is 2021-05-01 to 2026-05-31, with effective repaired first signal 2021-05-06. V57f core is frozen. No model rule, sleeve, factor, weighting, frequency, target, or historical result was modified for this report.\n\n## 2. Repaired Baseline and Core Sleeves\n\nThe repaired baseline is the only new-mainline reference and retains bank, highway infrastructure, port/rail infrastructure, and utilities/electricity sleeve roles. Single-sleeve evidence is not substituted for the multi-sleeve portfolio.\n\n## 3. Research Sequence\n\nSector exploration remained bounded by PIT evidence; V5c defense/state work is retained as research or diagnostics; V5d is execution governance; V5e exit/cash work closed historically without promotion; V5f produced the present candidate; V5k-M established workflow, cash, and QMT evidence boundaries.\n\n## 4. Comparable Performance\n\nOnly the canonical pair below is admitted. Validation is not independent and the comparison is not a promotion claim.\n\n| Model | Total return % | Max drawdown % | Sharpe | Alpha % | Beta | IR |\n|---|---:|---:|---:|---:|---:|---:|\n" + table + "\n\n## 5. Benchmark Contract\n\nDirect ETF discovery provides economic-exposure context only: locally cached ETF records are adjusted price return, not verified ETF NAV-plus-dividend total-return chains. ETF Alpha/Beta/IR are therefore excluded.\n\n## 6. Execution and Reality Friction\n\nCommission, slippage, whole-lot, partial-buy/skip, halted securities, cash roll-forward, and order sequencing remain execution constraints. Strict cash NAV is unavailable and QMT historical target-order-fill-position-cash contract evidence is incomplete.\n\n## 7. Primary Candidate\n\n`internal_subsleeve_mom12_70_30` remains `primary_forward_paper_candidate_not_accepted`. Its historical evidence is not independent, it lacks strict cash reconstruction and exact QMT contract recovery, and it cannot be upgraded here.\n\n## 8. Model Tiers\n\nTier A is reporting comparability only; Tier B is evidence/engineering/diagnostic material; Tier C is archive/alias provenance. No research unit is repackaged as an investable model.\n\n## 9. Forward Evidence\n\nA future authorised paper cycle must record target -> order -> fill -> position -> cash from the first paper order. This report does not generate a target, start a platform, or claim forward evidence.\n\n## 10. Limitations\n\n" + "\n".join(f"- `{r['blocker']}`: {r['effect']}" for r in blockers) + "\n"
def _freeze_manifest(root: Path, evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try: head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True).stdout.strip()
    except Exception: head = "not_available"
    return [{"git_head": head, "generated_at_utc": _now(), "market_data_boundary": "2026-05-31", "source_manifest_count": len(evidence), "git_action": "status_record_only_no_add_commit_reset_clean"}]
def _assert_contract(root: Path) -> None:
    tiers = _rows(root / V5O / "v5o_model_tier_assignment.csv")
    if len(tiers) != 335: raise ValueError("V5o tier registry mismatch")
def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))
def _by_id(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]: return {r["canonical_model_id"]: r for r in rows}
def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(dict.fromkeys(k for r in rows for k in r)) or ["status"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
def _write_json(path: Path, value: Any) -> None: path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
def _now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")

if __name__ == "__main__": print(json.dumps(run_v5q_v5r_overall_report_readiness(), ensure_ascii=False, indent=2))

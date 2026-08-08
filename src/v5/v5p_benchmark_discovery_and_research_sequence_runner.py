from __future__ import annotations

"""V5p public-benchmark discovery and reporting-only research sequence packet."""

import csv
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


V5N = Path("v5n_model_performance_reporting") / "current"
V5O = Path("v5o_reporting_tier_reclassification") / "current"
OUT = Path("v5p_benchmark_discovery_and_research_sequence") / "current"
BOUNDARY = "2026-05-31"
PRIMARY = "internal_subsleeve_mom12_70_30"
BASELINE = "v57f_startup_preload_repaired_baseline"

# These are pre-declared exposure proxies, never selected by model returns.
CANDIDATES = {
    "512800.SH": {"secid": "1.512800", "name": "银行ETF华宝", "exposure": "bank", "decision": "candidate_direct"},
    "515220.SH": {"secid": "1.515220", "name": "煤炭ETF", "exposure": "coal", "decision": "candidate_direct"},
    "159930.SZ": {"secid": "0.159930", "name": "能源ETF", "exposure": "oil_gas_energy", "decision": "candidate_direct"},
    "159996.SZ": {"secid": "0.159996", "name": "家电ETF", "exposure": "home_appliances", "decision": "candidate_direct"},
    "512070.SH": {"secid": "1.512070", "name": "非银ETF", "exposure": "nonbank_financial", "decision": "rejection_control"},
    "516970.SH": {"secid": "1.516970", "name": "基建50ETF", "exposure": "infrastructure", "decision": "rejection_control"},
    "159611.SZ": {"secid": "0.159611", "name": "电力ETF", "exposure": "electricity", "decision": "rejection_control"},
    "561700.SH": {"secid": "1.561700", "name": "电力ETF", "exposure": "electricity", "decision": "rejection_control"},
    "516950.SH": {"secid": "1.516950", "name": "基建ETF", "exposure": "infrastructure", "decision": "rejection_control"},
    "515180.SH": {"secid": "1.515180", "name": "红利ETF", "exposure": "broad_dividend", "decision": "rejection_control"},
}


def run_v5p_benchmark_discovery_and_research_sequence(root: Path = Path("."), output_dir: Path | None = None, fetch_public_data: bool = True) -> dict[str, Any]:
    root = Path(root); _assert_contract(root)
    out = output_dir or root / OUT; out.mkdir(parents=True, exist_ok=True)
    raw = out / "benchmark_data"; raw.mkdir(exist_ok=True)
    tier_a = _rows(root / V5O / "v5o_tier_a_comparable_models_table.csv")
    tier_b = _rows(root / V5O / "v5o_tier_b_evidence_only_models_table.csv")
    tier_c = _rows(root / V5O / "v5o_tier_c_archived_alias_table.csv")
    metrics = _by_id(_rows(root / V5N / "v5n_formal_backtest_performance_statistics.csv"))
    links = _by_id(_rows(root / V5N / "v5n_model_report_link_index.csv"))
    required_dates = _baseline_dates(root)
    candidate_evidence, manifest = _collect_candidates(raw, required_dates, fetch_public_data)
    evidence_by_id = {r["candidate_id"]: r for r in candidate_evidence}
    exposure_map, decisions, rejection = _map_models(tier_a, evidence_by_id)

    _write_csv(out / "v5p_tier_a_model_exposure_map.csv", exposure_map)
    _write_csv(out / "v5p_benchmark_candidate_universe.csv", candidate_evidence)
    _write_csv(out / "v5p_benchmark_candidate_evidence.csv", candidate_evidence)
    _write_csv(out / "v5p_benchmark_rejection_reason_register.csv", rejection)
    _write_csv(out / "v5p_benchmark_selection_decisions.csv", decisions)
    _write_csv(out / "v5p_primary_vs_economic_benchmark_map.csv", decisions)
    _write_csv(out / "v5p_benchmark_inception_and_pit_audit.csv", candidate_evidence)
    _write_csv(out / "v5p_benchmark_daily_price_coverage_audit.csv", candidate_evidence)
    _write_csv(out / "v5p_benchmark_return_contract_audit.csv", [{"candidate_id": r["candidate_id"], "adjusted": r["adjusted"], "return_contract": r["return_contract"], "status": r["qualification_status"]} for r in candidate_evidence])
    _write_csv(out / "v5p_new_public_benchmark_data_manifest.csv", manifest or [{"status": "no_public_data_fetched"}])
    _write_csv(out / "v5p_benchmark_selection_rulebook.csv", _rulebook())
    _write_csv(out / "v5p_benchmark_blockers.csv", [r for r in candidate_evidence if r["qualification_status"] != "qualified"] or [{"blocker": "none_for_selected_direct_etfs"}])
    (out / "v5p_benchmark_discovery_contract.md").write_text(_contract(), encoding="utf-8")
    (out / "v5p_benchmark_data_quality_report.md").write_text(_benchmark_report(candidate_evidence, decisions), encoding="utf-8")

    sequence = _sequence_rows(tier_a, tier_b, tier_c)
    exclusions = [{"canonical_model_id": r["canonical_model_id"], "tier": r["tier"], "reason": r["classification_reason"], "may_enter_performance_comparison": False} for r in [*tier_b, *tier_c]]
    pairing = [{"report_id": s["report_id"], "canonical_model_id": mid, "comparison_eligible": mid in {r["canonical_model_id"] for r in tier_a}} for s in sequence for mid in s["model_ids"].split(";")]
    _write_csv(out / "v5p_research_sequence_comparison_matrix.csv", sequence)
    _write_csv(out / "v5p_mini_report_index.csv", [{"report_id": r["report_id"], "path": f"reports/{r['file_name']}", "research_question": r["research_question"], "comparison_objects": r["model_ids"]} for r in sequence])
    _write_csv(out / "v5p_model_comparison_pairing_matrix.csv", pairing)
    _write_csv(out / "v5p_noncomparable_model_exclusion_register.csv", exclusions)
    reports = out / "reports"; reports.mkdir(exist_ok=True)
    for item in sequence:
        (reports / item["file_name"]).write_text(_mini_report(item, tier_a, tier_b, tier_c, metrics, links, decisions), encoding="utf-8")

    _write_csv(out / "v5p_canonical_model_and_benchmark_register.csv", [{**r, "v5n_addendum_path": links.get(r["canonical_model_id"], {}).get("addendum_path", "not_available")} for r in decisions])
    _write_csv(out / "v5p_comparable_model_statistics_table.csv", [{**r, **{k: metrics.get(r["canonical_model_id"], {}).get(k, "not_available") for k in ("total_return_pct", "annualized_return_pct", "max_drawdown_pct", "annualized_volatility_pct", "sharpe_ratio", "alpha_zero_rf_annualized_pct", "beta_zero_rf", "information_ratio")}} for r in decisions])
    _write_csv(out / "v5p_evidence_only_model_summary.csv", exclusions)
    _write_csv(out / "v5p_overall_report_input_manifest.csv", _input_manifest(out, sequence))
    _write_csv(out / "v5p_overall_report_citation_index.csv", [{"topic": "model_addendum", "path": v.get("addendum_path", "not_available")} for v in links.values()])
    _write_csv(out / "v5p_future_refresh_requirements.csv", _future_refresh())
    (out / "v5p_research_dependency_map.md").write_text(_dependency_map(), encoding="utf-8")
    (out / "v5p_overall_report_outline.md").write_text(_outline(), encoding="utf-8")
    (out / "v5p_handoff_to_overall_report.md").write_text(_handoff(), encoding="utf-8")
    (out / "v5p_report.md").write_text(_final_report(tier_a, tier_b, tier_c, candidate_evidence, decisions), encoding="utf-8")
    summary = _summary(tier_a, tier_b, tier_c, candidate_evidence, decisions)
    _write_json(out / "v5p_summary.json", summary)
    _write_csv(out / "v5p_benchmark_type_distribution.csv", _distribution(decisions, "economic_benchmark_quality_grade"))
    _write_csv(out / "v5p_pm_gate_decision.csv", [{"decision": "benchmark_reporting_material_ready_no_model_promotion", "model_status_modified": False, "accepted": False, "live_trading_approved": False, "deployment_approved": False}])
    _write_csv(out / "v5p_next_agent_queue.csv", [{"priority": "P0", "task": "refresh_benchmark_reporting_only_if_new_local_or_authorized_pre_boundary_series_is_archived", "status": "reporting_only"}, {"priority": "P1", "task": "recover_strict_cash_and_qmt_historical_contract", "status": "still_required_before_execution_claim"}])
    (out / "v5p_agent_execution_rules.md").write_text("# V5p Rules\n\nPublic benchmark data is cached solely for reporting and truncated at 2026-05-31. No model, benchmark in V5n/V5o, target, platform, or order is changed. Direct ETF discovery is never an investment recommendation or strategy promotion.\n", encoding="utf-8")
    return summary


def _collect_candidates(raw: Path, required: set[str], fetch: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    evidence, manifest = [], []
    for cid, meta in CANDIDATES.items():
        path = raw / f"{cid.replace('.', '_')}_daily.csv"
        source_url = _url(meta["secid"])
        download_error = ""
        if path.exists():
            with path.open(encoding="utf-8-sig", newline="") as handle:
                cached = list(csv.DictReader(handle))
            dates = {r["trade_date"] for r in cached if r["trade_date"] <= BOUNDARY}
            common = len(dates & required); coverage = common / len(required) * 100 if required else 0.0
            first = min(dates) if dates else "not_available"; last = max(dates) if dates else "not_available"
            qualified = first <= "2021-05-06" and coverage >= 95.0
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest.append({"candidate_id": cid, "source_url": source_url, "downloaded_at_utc": "cached_prior_v5p_run", "file_path": str(path), "sha256": digest, "start_date": first, "end_date": last, "fields": "trade_date,open,close,high,low,volume,amount", "adjusted": "eastmoney_fqt_1", "return_contract": "adjusted_price_return_not_total_return", "use_scope": "benchmark_reporting_only"})
        elif fetch:
            try:
                request = urllib.request.Request(source_url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json, text/plain, */*", "Referer": "https://quote.eastmoney.com/"})
                payload = urllib.request.urlopen(request, timeout=35).read()
                data = json.loads(payload.decode("utf-8")); klines = data.get("data", {}).get("klines", [])
                rows = [line.split(",") for line in klines if line[:10] <= BOUNDARY]
                _write_csv(path, [{"trade_date": r[0], "open": r[1], "close": r[2], "high": r[3], "low": r[4], "volume": r[5], "amount": r[6]} for r in rows])
                dates = {r[0] for r in rows}; common = len(dates & required); coverage = common / len(required) * 100 if required else 0.0
                first = min(dates) if dates else "not_available"; last = max(dates) if dates else "not_available"
                qualified = first <= "2021-05-06" and coverage >= 95.0
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                manifest.append({"candidate_id": cid, "source_url": source_url, "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "file_path": str(path), "sha256": digest, "start_date": first, "end_date": last, "fields": "trade_date,open,close,high,low,volume,amount", "adjusted": "eastmoney_fqt_1", "return_contract": "adjusted_price_return_not_total_return", "use_scope": "benchmark_reporting_only"})
            except Exception as exc:
                dates = set(); common = 0; coverage = 0.0; first = last = "not_available"; qualified = False; digest = "not_available"
                download_error = repr(exc)
                manifest.append({"candidate_id": cid, "source_url": source_url, "download_error": download_error, "use_scope": "benchmark_reporting_only"})
        else:
            dates = set(); common = 0; coverage = 0.0; first = last = "not_fetched"; qualified = False; digest = "not_fetched"
        evidence.append({"candidate_id": cid, "candidate_name": meta["name"], "candidate_type": "ETF", "exposure": meta["exposure"], "source_url": source_url, "inception_or_first_available_date": first, "data_end_date": last, "common_trading_days": common, "coverage_pct": round(coverage, 4), "adjusted": "eastmoney_fqt_1", "return_contract": "adjusted_price_return_not_total_return", "tradable": True, "qualification_status": "qualified" if qualified else ("data_unavailable" if download_error else "rejected"), "qualification_reason": "predeclared_exposure_candidate_with_95pct_coverage" if qualified else ("public_source_fetch_failed_not_treated_as_inception_evidence" if download_error else "inception_or_coverage_gate_failed"), "file_sha256": digest, "use_scope": "benchmark_reporting_only"})
    return evidence, manifest


def _map_models(tier_a: list[dict[str, str]], evidence: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    exposure, decisions, rejected = [], [], []
    for row in tier_a:
        mid = row["canonical_model_id"]; sector, selected, rejected_id = _sector_candidate(mid)
        candidate = evidence.get(selected) if selected else None
        direct = bool(candidate and candidate["qualification_status"] == "qualified")
        primary = row["primary_benchmark"] if "overlay" in row["family"] or mid == PRIMARY else (selected if direct else row["primary_benchmark"])
        grade = "A_direct_tradable_etf" if direct else ("C_static_proxy_basket" if row["benchmark_type"] == "static_proxy_basket" else "D_parent_strategy_only")
        economic = selected if direct else ("frozen_static_proxy_basket" if row["benchmark_type"] == "static_proxy_basket" else row["primary_benchmark"])
        rationale = "predeclared_sector_exposure_candidate; no return-based selection" if direct else "existing_parent_or_static_proxy_retained; direct candidate did not meet sector/inception gate"
        exposure.append({"canonical_model_id": mid, "model_type": _model_type(mid), "exposure_bucket": sector, "parent_baseline": row["primary_benchmark"], "average_major_exposure": sector, "primary_comparison_benchmark": primary, "economic_exposure_benchmark": economic})
        decisions.append({"canonical_model_id": mid, "primary_comparison_benchmark": primary, "economic_exposure_benchmark": economic, "economic_benchmark_quality_grade": grade, "direct_benchmark_added_for_reporting": direct, "proxy_only": not direct, "alpha_beta_ir_allowed_under_new_view": False, "selection_rationale": rationale, "model_status_modified": False})
        if rejected_id:
            r = evidence[rejected_id]; rejected.append({"canonical_model_id": mid, "candidate_id": rejected_id, "candidate_name": r["candidate_name"], "rejection_reason": _rejection_reason(rejected_id), "not_return_selected": True})
    return exposure, decisions, rejected


def _sector_candidate(mid: str) -> tuple[str, str | None, str | None]:
    low = mid.lower()
    if "bank" in low: return "bank", "512800.SH", "512070.SH"
    if "coal" in low: return "coal", "515220.SH", "159930.SZ"
    if "home_appliances" in low: return "home_appliances", "159996.SZ", "515180.SH"
    if "oil_gas" in low: return "oil_gas_energy", "159930.SZ", "515180.SH"
    if "insurance" in low: return "insurance", None, "512070.SH"
    if "utilities" in low: return "electricity", None, "159611.SZ"
    if "gas_water" in low: return "gas_water", None, "561700.SH"
    if "highway" in low or "port_rail" in low: return "infrastructure_transport", None, "516970.SH"
    return "multi_sleeve_or_overlay", None, "515180.SH"


def _rejection_reason(candidate_id: str) -> str:
    if candidate_id in ("159611.SZ", "561700.SH", "516970.SH", "516950.SH"): return "first_available_after_formal_comparison_start"
    if candidate_id in ("512070.SH", "159930.SZ", "515180.SH"): return "exposure_not_specific_enough_for_this_model"
    return "not_eligible_under_predeclared_contract"


def _baseline_dates(root: Path) -> set[str]:
    path = root / "v5f_structural_rough_screen/current/v5f_structural_rough_screen_daily_returns.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {r["trade_date"] for r in csv.DictReader(handle) if r.get("version_id") == BASELINE and r["trade_date"] <= BOUNDARY}


def _url(secid: str) -> str:
    params = {"secid": secid, "klt": "101", "fqt": "1", "beg": "19900101", "end": "20260531", "lmt": "10000", "fields1": "f1,f2", "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"}
    return "https://push2his.eastmoney.com/api/qt/stock/kline/get?" + urllib.parse.urlencode(params)


def _sequence_rows(a: list[dict[str, str]], b: list[dict[str, str]], c: list[dict[str, str]]) -> list[dict[str, str]]:
    all_ids = ";".join(r["canonical_model_id"] for r in a)
    return [
        _seq("01", "01_repaired_baseline_and_core_sleeves.md", "repaired baseline and core sleeves", "v57f_startup_preload_repaired_baseline;bank;utilities;highway;port_rail"),
        _seq("02", "02_enhanced_etf_assembly_and_noncore_boundary.md", "enhanced ETF assembly and non-core boundary", "v57f;gas_water;telecom;home_appliances;oil_gas"),
        _seq("03", "03_defense_risk_budget_and_state_observation.md", "defense, risk budget, and state observation", "v57f;erc;risk_budget;state"),
        _seq("04", "04_execution_governance_and_realistic_cost_boundary.md", "execution governance and realistic cost boundary", "v57f;v5d;execution;order"),
        _seq("05", "05_exit_cash_policy_and_profit_lock_closeout.md", "exit, cash policy, and profit-lock closeout", "v57f;v5e;cash_proxy;profit_lock"),
        _seq("06", "06_weight_governance_momentum_mean_reversion_to_primary_candidate.md", "weight governance from momentum and mean reversion to primary candidate", f"{BASELINE};{PRIMARY};momentum;mean_reversion"),
        _seq("07", "07_execution_buy_sell_technical_research_closeout.md", "buy/sell technical execution research closeout", "v5h;v5i;v5j;technical"),
        _seq("08", "08_evidence_quality_pit_qmt_cash_and_forward_boundary.md", "PIT, QMT, cash, and forward evidence boundary", "v5m;strict_cash;qmt_contract;forward"),
        _seq("09", "09_overall_report_readiness_and_open_questions.md", "overall report readiness and open questions", all_ids),
    ]
def _seq(number: str, file_name: str, question: str, ids: str) -> dict[str, str]: return {"report_id": number, "file_name": file_name, "research_question": question, "model_ids": ids, "formal_window": "2021-05-01_to_2026-05-31", "comparison_rule": "same_parent_or_same_research_question_only_no_performance_ranking"}
def _mini_report(item: dict[str, str], a: list[dict[str, str]], b: list[dict[str, str]], c: list[dict[str, str]], metrics: dict[str, dict[str, str]], links: dict[str, dict[str, str]], decisions: list[dict[str, Any]]) -> str:
    tokens = [x.lower() for x in item["model_ids"].split(";")]
    included = [r for r in a if any(t in r["canonical_model_id"].lower() for t in tokens)]
    excluded = [r for r in [*b, *c] if any(t in r["canonical_model_id"].lower() for t in tokens)]
    lines = [f"# {item['report_id']} {item['research_question'].title()}\n", f"## Research Question\n\n{item['research_question']}. This is a research-order report, never a performance ranking.\n", "## Eligible Comparison Units\n"]
    for r in included:
        m = metrics.get(r["canonical_model_id"], {})
        lines.append(f"- `{r['canonical_model_id']}`: tier `{r['tier']}`, primary `{r['primary_benchmark']}`, total-return field `{m.get('total_return_pct', 'not_available')}`, addendum `{links.get(r['canonical_model_id'], {}).get('addendum_path', 'not_available')}`.\n")
    lines.append("\n## Excluded Evidence Units\n\n" + ("\n".join(f"- `{r['canonical_model_id']}`: `{r['tier']}`; not a comparable daily-performance unit." for r in excluded[:30]) or "- None matched this report's research scope.") + "\n")
    lines.append("\n## Benchmark and Evidence Boundary\n\nPrimary comparisons retain the repaired parent baseline where applicable. Direct ETF discoveries are a `new_benchmark_reporting_view_not_model_retest`; no model NAV or state is changed. Static proxy baskets retain limited interpretation.\n")
    lines.append("## Governance Conclusion\n\nNo accepted/live/deployment conclusion. Next research question is the next numbered report in this sequence.\n")
    return "\n".join(lines)


def _rulebook() -> list[dict[str, str]]: return [{"rule": "inception", "requirement": "first available date no later than 2021-05-06"}, {"rule": "coverage", "requirement": "at least 95 percent of repaired baseline daily dates"}, {"rule": "selection", "requirement": "predeclared exposure match; never return-selected"}, {"rule": "return_contract", "requirement": "adjusted price return or total-return contract disclosed"}]
def _model_type(mid: str) -> str:
    if mid == PRIMARY: return "weight_overlay"
    if any(x in mid for x in ("execution", "v5d_", "minute")): return "execution_overlay_or_engineering"
    if any(x in mid for x in ("v57", "v5c_")): return "core_or_multi_sleeve"
    return "single_sector_strategy"
def _distribution(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    d: dict[str, int] = {}
    for r in rows: d[str(r[key])] = d.get(str(r[key]), 0) + 1
    return [{key: k, "count": v} for k, v in sorted(d.items())]
def _input_manifest(out: Path, sequence: list[dict[str, str]]) -> list[dict[str, str]]: return [{"component": "tiered_model_registry", "path": "v5o_reporting_tier_reclassification/current/v5o_model_tier_assignment.csv", "use": "model_scope"}, {"component": "benchmark_discovery", "path": "v5p_benchmark_selection_decisions.csv", "use": "benchmark_contract"}, {"component": "sequence_reports", "path": "reports/", "use": "research_order"}]
def _future_refresh() -> list[dict[str, str]]: return [{"requirement": "strict_cash_state", "why": "needed for strict cash NAV"}, {"requirement": "qmt_historical_contract", "why": "needed for target-order-fill-position-cash attribution"}, {"requirement": "future_authorized_paper_cycle", "why": "only future source of independent paper evidence"}]
def _contract() -> str: return "# V5p Benchmark Discovery Contract\n\nCandidates are identified before examining relative model results, must start by the formal comparison start and cover at least 95% of repaired-baseline dates. They are reporting references, not trading recommendations. Parent benchmarks remain primary for overlays. Public data is adjusted price return unless stated otherwise and is capped at 2026-05-31.\n"
def _benchmark_report(evidence: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> str: return f"# Benchmark Data Quality\n\nCandidate records: {len(evidence)}. Qualified direct ETFs: {sum(r['qualification_status'] == 'qualified' for r in evidence)}. They are exposure references only; no V5n/V5o historical statistic or model status has been replaced.\n"
def _dependency_map() -> str: return "# Research Dependency Map\n\nRepaired baseline -> core sleeves -> non-core boundary -> defense/state -> execution/cost -> exit/cash -> V5f weight governance -> technical closeout -> evidence quality -> overall readiness.\n"
def _outline() -> str: return "# Overall Report Outline\n\n1. Governance boundary\n2. Repaired baseline and core sleeves\n3. Industry extensions\n4. Defense/state observation\n5. Execution, cost, cash and orders\n6. V5f primary-candidate formation\n7. Comparable performance and benchmark interpretation\n8. Evidence gaps\n9. Future paper plan\n10. Why no acceptance conclusion\n"
def _handoff() -> str: return "# Handoff\n\nUse V5p model/benchmark registers and the nine sequence reports. Refresh only benchmark reporting if new permitted historical evidence is archived. Strict cash NAV, QMT contract attribution and independent forward paper evidence require separate authorised work.\n"
def _final_report(a: list[dict[str, str]], b: list[dict[str, str]], c: list[dict[str, str]], evidence: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> str: return f"# V5p Materials\n\nTier A={len(a)}, Tier B={len(b)}, Tier C={len(c)}. Qualified direct ETF candidates={sum(r['qualification_status'] == 'qualified' for r in evidence)}. Models with direct economic benchmark reporting views={sum(bool(r['direct_benchmark_added_for_reporting']) for r in decisions)}. No model result or status changed.\n"
def _summary(a: list[dict[str, str]], b: list[dict[str, str]], c: list[dict[str, str]], evidence: list[dict[str, Any]], decisions: list[dict[str, Any]]) -> dict[str, Any]: return {"created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "task": "v5p_benchmark_discovery_and_research_sequence", "formal_scope_end": BOUNDARY, "qualified_direct_etf_count": sum(r["qualification_status"] == "qualified" for r in evidence), "qualified_industry_index_count": 0, "confirmed_static_proxy_basket_model_count": sum(r["economic_benchmark_quality_grade"] == "C_static_proxy_basket" for r in decisions), "tier_a_models_with_direct_economic_benchmark": sum(bool(r["direct_benchmark_added_for_reporting"]) for r in decisions), "tier_a_count": len(a), "tier_b_count": len(b), "tier_c_count": len(c), "model_status_modified": False, "accepted": False, "live_trading_approved": False, "deployment_approved": False}
def _assert_contract(root: Path) -> None:
    data = json.loads((root / V5O / "v5o_reporting_tier_summary.json").read_text(encoding="utf-8"))
    if data.get("total_units") != 335 or data.get("model_status_modified") is not False: raise ValueError("V5o contract mismatch")
def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))
def _by_id(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]: return {r["canonical_model_id"]: r for r in rows}
def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(dict.fromkeys(k for r in rows for k in r)) or ["status"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
def _write_json(path: Path, value: Any) -> None: path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__": print(json.dumps(run_v5p_benchmark_discovery_and_research_sequence(), ensure_ascii=False, indent=2))

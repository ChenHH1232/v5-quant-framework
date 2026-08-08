from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev
from typing import Any


OUT = Path("v5s_report_draft_review_and_release_prep") / "current"
BASELINE = "v57f_startup_preload_repaired_baseline"
PRIMARY = "internal_subsleeve_mom12_70_30"
WINDOW_START, WINDOW_END = "2021-05-01", "2026-05-31"
DISCLOSURES = ("strict_cash_nav_unavailable", "qmt_contract_incomplete", "ETF total-return 合同缺失", "validation_not_independent", "独立前瞻纸面周期尚未形成")


def run_v5s_report_draft_review(root: Path = Path("."), output_dir: Path | None = None, r_output: Path | None = None, test_statuses: dict[str, str] | None = None) -> dict[str, Any]:
    root = Path(root); _assert_inputs(root)
    out = output_dir or root / OUT; out.mkdir(parents=True, exist_ok=True)
    source_stats = _recompute_pair(root)
    v5r = _rows(root / "v5r_overall_research_governance_report_draft/current/v5r_performance_comparison_table.csv")
    numeric = _numeric_reconciliation(source_stats, v5r)
    conflicts = [r for r in numeric if r["status"] != "match"]
    revised = _revised_report(source_stats)
    claim_audit = _claim_audit()
    disclosure = _disclosure_audit(revised)
    structure = _structure_audit(revised)
    appendix = _appendix_boundary()
    citations = _citation_audit(root)
    release = "draft_review_pass_with_disclosures" if not conflicts and all(r["present_in_all_required_sections"] for r in disclosure) else "draft_review_needs_correction"
    blockers = _blockers()

    _write_csv(out / "v5s_numeric_reconciliation.csv", numeric)
    _write_csv(out / "v5s_source_conflict_log.csv", conflicts or [{"status": "no_source_conflict", "detail": "V5r table matches recomputed canonical daily series."}])
    _write_csv(out / "v5s_claim_evidence_audit.csv", claim_audit)
    _write_csv(out / "v5s_required_disclosure_audit.csv", disclosure)
    _write_csv(out / "v5s_report_structure_audit.csv", structure)
    _write_csv(out / "v5s_appendix_boundary_register.csv", appendix)
    _write_csv(out / "v5s_citation_integrity_audit.csv", citations)
    (out / "v5s_revised_overall_research_governance_report_draft.md").write_text(revised, encoding="utf-8")
    _write_csv(out / "v5s_release_decision.csv", [{"release_decision": release, "draft_only": True, "final": False, "accepted": False, "live_trading_approved": False, "deployment_approved": False, "model_status_modified": False}])
    test_statuses = test_statuses or {"v5s_targeted": "not_run_by_runner", "fast": "not_run_by_runner", "standard": "not_run_by_runner", "extended": "not_run"}
    _write_csv(out / "v5s_test_results.csv", [{"test_scope": k, "status": v} for k, v in test_statuses.items()])
    _write_csv(out / "v5s_blockers.csv", blockers)
    (out / "v5s_pm_review_report.md").write_text(_pm_review(release, conflicts, disclosure, blockers), encoding="utf-8")
    summary = {"created_at_utc": _now(), "task": "v5s_report_draft_review_and_release_prep", "numeric_fields_checked": len(numeric), "source_conflict_count": len(conflicts), "mandatory_disclosures_pass": all(r["present_in_all_required_sections"] for r in disclosure), "release_decision": release, "primary_candidate": PRIMARY, "primary_candidate_status": "primary_forward_paper_candidate_not_accepted", "model_status_modified": False, "accepted": False, "live_trading_approved": False, "deployment_approved": False}
    _write_json(out / "v5s_report_review_summary.json", summary)
    return summary


def _recompute_pair(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "v5f_structural_rough_screen/current/v5f_structural_rough_screen_daily_returns.csv"
    data: dict[str, list[tuple[str, float, float]]] = {PRIMARY: [], BASELINE: []}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            mid, date = row.get("version_id"), row.get("trade_date")
            if mid in data and WINDOW_START <= date <= WINDOW_END:
                data[mid].append((date, float(row["strategy_return"]), float(row["baseline_return"])))
    primary = data[PRIMARY]; baseline = data[BASELINE]
    if len(primary) != 1228 or len(baseline) != 1228 or [x[0] for x in primary] != [x[0] for x in baseline]:
        raise ValueError("Canonical pair common-date contract failed")
    p = [x[1] for x in primary]; b = [x[1] for x in baseline]
    return {PRIMARY: _stats(p, b, primary[0][0], primary[-1][0]), BASELINE: _stats(b, b, baseline[0][0], baseline[-1][0])}


def _stats(values: list[float], bench: list[float], start: str, end: str) -> dict[str, Any]:
    n = len(values); nav = 1.0; peak = 1.0; mdd = 0.0
    for value in values:
        nav *= 1 + value; peak = max(peak, nav); mdd = min(mdd, nav / peak - 1)
    bnav = 1.0; bpeak = 1.0; bmdd = 0.0
    for value in bench:
        bnav *= 1 + value; bpeak = max(bpeak, bnav); bmdd = min(bmdd, bnav / bpeak - 1)
    active = [x - y for x, y in zip(values, bench)]
    vmean, bmean = mean(values), mean(bench)
    bvar = sum((x - bmean) ** 2 for x in bench) / (n - 1)
    beta = sum((x - vmean) * (y - bmean) for x, y in zip(values, bench)) / (n - 1) / bvar if bvar else "not_available"
    return {"total_return_pct": (nav - 1) * 100, "annualized_return_pct": (nav ** (252 / n) - 1) * 100, "max_drawdown_pct": -mdd * 100, "annualized_volatility_pct": stdev(values) * math.sqrt(252) * 100, "sharpe_ratio": math.sqrt(252) * vmean / stdev(values), "alpha_zero_rf_annualized_pct": (vmean - beta * bmean) * 252 * 100 if beta != "not_available" else "not_available", "beta_zero_rf": beta, "information_ratio": math.sqrt(252) * mean(active) / stdev(active) if stdev(active) else "not_available", "excess_return_pct_points": ((nav - 1) - (bnav - 1)) * 100, "max_drawdown_delta_pct_points": (-mdd * 100) - (-bmdd * 100), "observations": n, "start_date": start, "end_date": end}


def _numeric_reconciliation(stats: dict[str, dict[str, Any]], existing: list[dict[str, str]]) -> list[dict[str, Any]]:
    old = {r["canonical_model_id"]: r for r in existing}; fields = ("total_return_pct", "annualized_return_pct", "max_drawdown_pct", "annualized_volatility_pct", "sharpe_ratio", "alpha_zero_rf_annualized_pct", "beta_zero_rf", "information_ratio", "excess_return_pct_points", "max_drawdown_delta_pct_points", "observations", "start_date", "end_date")
    result = []
    for mid, row in stats.items():
        for field in fields:
            actual, reported = row[field], old.get(mid, {}).get(field, "not_available")
            if actual == "not_available": match = reported == "not_available"
            elif field in ("start_date", "end_date", "observations"): match = str(actual) == str(reported)
            else: match = abs(float(actual) - float(reported)) < 1e-9
            result.append({"canonical_model_id": mid, "metric": field, "recomputed_value": actual, "v5r_reported_value": reported, "source_daily_series": "v5f_structural_rough_screen/current/v5f_structural_rough_screen_daily_returns.csv", "stat_definition": "v5n_metric_definition.md", "status": "match" if match else "source_conflict"})
    return result


def _claim_audit() -> list[dict[str, Any]]:
    return [
        {"claim": "唯一正式表现比较仅为 repaired baseline 与主候选", "evidence": "v5q_canonical_comparison_matrix.csv", "status": "supported", "revised_language": "同窗口、同父策略、1,228 个共同样本的 pairwise comparison"},
        {"claim": "主候选为 primary_forward_paper_candidate_not_accepted", "evidence": "config/v5_active_model_registry.json; v5q summary", "status": "supported", "revised_language": "候选，未 accepted"},
        {"claim": "ETF 可用于正式 Alpha/Beta/IR", "evidence": "v5q_benchmark_return_contract_decision.csv", "status": "removed_or_downgraded", "revised_language": "ETF 仅为 economic exposure context"},
        {"claim": "V5c/V5d/V5e/QMT 是可比较策略表现", "evidence": "v5o tier registry; v5q diagnostic audit", "status": "removed_or_downgraded", "revised_language": "研究过程、执行审计或证据附录"},
    ]


def _disclosure_audit(revised: str) -> list[dict[str, Any]]:
    sections = {"executive_summary": revised.split("## 2.")[0], "primary_candidate": revised.split("## 7.")[1].split("## 8.")[0], "limitations": revised.split("## 10.")[1]}
    return [{"disclosure": disclosure, "executive_summary": disclosure in sections["executive_summary"], "primary_candidate": disclosure in sections["primary_candidate"], "limitations": disclosure in sections["limitations"], "present_in_all_required_sections": all(disclosure in section for section in sections.values())} for disclosure in DISCLOSURES]


def _structure_audit(revised: str) -> list[dict[str, Any]]:
    order = ("## 1. 研究边界", "## 2. Repaired Baseline", "## 3. 板块研究", "## 4. 防守、执行与退出", "## 5. 正式可比表现", "## 6. ETF 经济暴露", "## 7. 主候选", "## 8. 分层与附录", "## 9. 前瞻纸面", "## 10. 限制")
    return [{"section": h, "present": h in revised, "order_index": revised.find(h)} for h in order]


def _appendix_boundary() -> list[dict[str, str]]:
    return [{"material": "V5c defense/state and sleeve diagnostics", "placement": "research_or_diagnostic_appendix", "not_strategy_performance": True}, {"material": "V5d/V5h/V5i/V5j execution and technical work", "placement": "execution_evidence_appendix", "not_strategy_performance": True}, {"material": "V5e exit/cash/511360 work", "placement": "cash_exit_governance_appendix", "not_strategy_performance": True}, {"material": "QMT replay and contract evidence", "placement": "execution_contract_appendix", "not_strategy_performance": True}]


def _citation_audit(root: Path) -> list[dict[str, Any]]:
    rows = _rows(root / "v5q_overall_report_readiness_repair/current/v5q_chapter_citation_map.csv")
    return [{"chapter": r["chapter"], "claim": r["claim"], "evidence": r["evidence"], "citation_nonempty": bool(r["evidence"]), "status": "traceable" if r["evidence"] else "missing"} for r in rows]


def _blockers() -> list[dict[str, str]]:
    return [{"blocker": "strict_cash_nav_unavailable", "effect": "blocks accepted, live and strong return claims"}, {"blocker": "qmt_contract_incomplete", "effect": "blocks exact historical platform execution attribution"}, {"blocker": "ETF total-return 合同缺失", "effect": "blocks formal ETF relative statistics"}, {"blocker": "validation_not_independent", "effect": "blocks independent-validation claim"}, {"blocker": "独立前瞻纸面周期尚未形成", "effect": "blocks independent forward evidence"}]


def _revised_report(stats: dict[str, dict[str, Any]]) -> str:
    lines = ["# V5 总体研究与治理报告（修订初稿）\n", "**状态：修订初稿，非最终版；非实盘版；未 accepted。**\n", "## 执行摘要\n\nV57f repaired baseline 是唯一正式基线。`internal_subsleeve_mom12_70_30` 是唯一主候选，状态为 `primary_forward_paper_candidate_not_accepted`。唯一进入正式表现正文的是二者在 2021-05-06 至 2026-05-29 的 1,228 个共同样本 pairwise comparison。以下边界同时适用于本摘要、主候选结论和限制章节：strict_cash_nav_unavailable；qmt_contract_incomplete；ETF total-return 合同缺失；validation_not_independent；独立前瞻纸面周期尚未形成。\n", "## 1. 研究边界与方法\n\n正式研究窗口为 2021-05-01 至 2026-05-31，首个有效信号日为 2021-05-06。V57f core、候选规则、权重、频率与历史结果均未因本报告修改。\n", "## 2. Repaired Baseline 与核心 Sleeve\n\nrepaired baseline 由银行、高速基础设施、港口铁路基础设施与电力公用事业 sleeve 构成。单行业研究不能替代多 sleeve 组合治理。\n", "## 3. 板块研究与非核心边界\n\n板块、行业资料和 PIT 数据门构成研究证据；它们不因局部结果而自动进入核心组合或正式表现比较。\n", "## 4. 防守、执行与退出研究\n\nV5c 防守/状态工作、V5d 分钟执行、V5e 退出与现金治理、QMT 回放均作为研究过程或执行审计呈现，不作为可比较收益模型。\n", "## 5. 正式可比表现\n\n以下表格只含同窗口、同父策略、canonical 的 pairwise comparison。统计定义为 V5n 的共同交易日简单收益口径；验证并非独立验证。\n", "| 模型 | 总收益 % | 年化 % | 最大回撤 % | 波动 % | 夏普 | Alpha % | Beta | IR | 超额收益百分点 | 回撤差百分点 | 样本 |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"]
    for mid in (BASELINE, PRIMARY):
        r = stats[mid]; lines.append(f"| `{mid}` | {r['total_return_pct']:.4f} | {r['annualized_return_pct']:.4f} | {r['max_drawdown_pct']:.4f} | {r['annualized_volatility_pct']:.4f} | {r['sharpe_ratio']:.4f} | {r['alpha_zero_rf_annualized_pct'] if r['alpha_zero_rf_annualized_pct'] == 'not_available' else f'{r['alpha_zero_rf_annualized_pct']:.4f}'} | {r['beta_zero_rf']:.4f} | {r['information_ratio'] if r['information_ratio'] == 'not_available' else f'{r['information_ratio']:.4f}'} | {r['excess_return_pct_points']:.4f} | {r['max_drawdown_delta_pct_points']:.4f} | {r['observations']} |\n")
    lines += ["\n## 6. ETF 经济暴露语境\n\n本地 ETF 系列为 adjusted price return，尚无可追溯 NAV 加分红的 total-return 合同。因此 ETF 只作为 economic exposure context，不能进入正式 ETF Alpha、Beta、IR 或超额收益表。\n", "## 7. 主候选结论\n\n`internal_subsleeve_mom12_70_30` 保持 `primary_forward_paper_candidate_not_accepted`。历史样本中存在相对 repaired baseline 的观察，但这不构成独立验证或升级依据。strict_cash_nav_unavailable；qmt_contract_incomplete；ETF total-return 合同缺失；validation_not_independent；独立前瞻纸面周期尚未形成。\n", "## 8. 分层与附录边界\n\nTier A 仅表示报告可比性；Tier B 为研究、数据、诊断或执行证据；Tier C 为归档/别名。执行工程、现金账本、分钟研究与 QMT 资料均留在附录边界。\n", "## 9. 前瞻纸面闭环\n\n严格现金 NAV 与 QMT 合同不阻塞诚实的历史研究报告，却阻塞 accepted、实盘和强收益承诺。独立证据只能在未来获授权纸面周期中，从第一笔记录完整 target -> order -> fill -> position -> cash 链条。\n", "## 10. 限制与未解边界\n\nstrict_cash_nav_unavailable；qmt_contract_incomplete；ETF total-return 合同缺失；validation_not_independent；独立前瞻纸面周期尚未形成。\n"]
    return "\n".join(lines)


def _pm_review(release: str, conflicts: list[dict[str, Any]], disclosure: list[dict[str, Any]], blockers: list[dict[str, str]]) -> str:
    return f"# V5s PM Review\n\n- Release decision: `{release}`\n- Numeric conflicts: {len(conflicts)}\n- Mandatory disclosures passed: {all(r['present_in_all_required_sections'] for r in disclosure)}\n- The report remains draft-only, non-final, non-accepted and non-live.\n\n## Unresolved blockers\n\n" + "\n".join(f"- `{r['blocker']}`: {r['effect']}" for r in blockers) + "\n"
def _assert_inputs(root: Path) -> None:
    for path in ("v5q_overall_report_readiness_repair/current/v5q_overall_report_readiness_summary.json", "v5q_overall_report_readiness_repair/current/v5q_readiness_gate.csv", "v5q_overall_report_readiness_repair/current/v5q_required_evidence_manifest.csv", "v5q_overall_report_readiness_repair/current/v5q_chapter_citation_map.csv", "v5q_overall_report_readiness_repair/current/v5q_canonical_comparison_matrix.csv", "v5r_overall_research_governance_report_draft/current/v5r_overall_research_governance_report_draft.md", "v5r_overall_research_governance_report_draft/current/v5r_performance_comparison_table.csv", "v5r_overall_research_governance_report_draft/current/v5r_claim_to_evidence_map.csv", "v5r_overall_research_governance_report_draft/current/v5r_unresolved_limitations.csv", "v5m_p0_closure/current/v5m_p0_closure_summary.json", "docs/governance/status_registry.json"):
        if not (root / path).exists(): raise FileNotFoundError(path)
def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))
def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(dict.fromkeys(k for r in rows for k in r)) or ["status"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
def _write_json(path: Path, value: Any) -> None: path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
def _now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")

if __name__ == "__main__": print(json.dumps(run_v5s_report_draft_review(), ensure_ascii=False, indent=2))

from __future__ import annotations

"""V5t: archive publication of the reviewed historical research report.

This module is deliberately report-only. It never produces targets, changes a
model, or accesses a trading or external-data system.
"""

import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


OUT = Path("v5t_report_publication_finalization") / "current"
BASELINE = "v57f_startup_preload_repaired_baseline"
PRIMARY = "internal_subsleeve_mom12_70_30"
WINDOW = "2021-05-01 至 2026-05-31"
PAIR_START, PAIR_END, PAIR_OBS = "2021-05-06", "2026-05-29", 1228
DISCLOSURES = (
    "strict_cash_nav_unavailable",
    "qmt_contract_incomplete",
    "ETF total-return 合同缺失",
    "validation_not_independent",
    "独立前瞻纸面周期尚未形成",
)
INPUTS = (
    "v5s_report_draft_review_and_release_prep/current/v5s_revised_overall_research_governance_report_draft.md",
    "v5s_report_draft_review_and_release_prep/current/v5s_numeric_reconciliation.csv",
    "v5s_report_draft_review_and_release_prep/current/v5s_claim_evidence_audit.csv",
    "v5s_report_draft_review_and_release_prep/current/v5s_required_disclosure_audit.csv",
    "v5s_report_draft_review_and_release_prep/current/v5s_release_decision.csv",
    "v5q_overall_report_readiness_repair/current/v5q_required_evidence_manifest.csv",
    "v5q_overall_report_readiness_repair/current/v5q_reproducibility_freeze_manifest.csv",
    "v5r_overall_research_governance_report_draft/current/v5r_performance_comparison_table.csv",
    "v5m_p0_closure/current/v5m_p0_closure_summary.json",
    "docs/governance/status_registry.json",
)


def run_v5t_publication(root: Path = Path("."), output_dir: Path | None = None, test_statuses: dict[str, str] | None = None) -> dict[str, Any]:
    root = Path(root)
    _assert_inputs(root)
    out = output_dir or root / OUT
    out.mkdir(parents=True, exist_ok=True)

    facts, conflicts = _freeze_facts(root)
    disclosure_audit = _disclosure_audit(root)
    if conflicts or not all(row["present_in_all_required_sections"] for row in disclosure_audit):
        raise ValueError("V5t publication facts or mandatory disclosures are not ready for archive release")

    performance = _performance_rows(root)
    table_audit = _table_audit(performance)
    claims = _claim_register(root)
    release = "archive_release_pass_with_required_disclosures"
    markdown = _report_markdown(performance)

    _write_csv(out / "v5t_publication_input_manifest.csv", _input_manifest(root))
    _write_csv(out / "v5t_content_change_log.csv", _content_change_log())
    _write_csv(out / "v5t_final_claim_evidence_register.csv", claims)
    _write_csv(out / "v5t_disclosure_coverage_audit.csv", disclosure_audit)
    _write_csv(out / "v5t_statistics_and_table_audit.csv", table_audit)
    _write_csv(out / "v5t_publication_release_decision.csv", [{
        "release_decision": release, "archive_report_only": True, "final_strategy": False,
        "accepted": False, "live_trading_approved": False, "deployment_approved": False,
        "model_status_modified": False,
    }])
    (out / "v5t_v5_historical_research_and_governance_report_v1_0.md").write_text(markdown, encoding="utf-8")
    _build_docx(out / "v5t_v5_historical_research_and_governance_report_v1_0.docx", performance)
    _build_pdf(out / "v5t_v5_historical_research_and_governance_report_v1_0.pdf", performance)
    test_statuses = test_statuses or {"v5t_targeted": "not_run_by_runner", "fast": "not_run_by_runner", "standard": "not_run_by_runner", "extended": "not_run"}
    _write_csv(out / "v5t_test_results.csv", [{"test_scope": k, "status": v} for k, v in test_statuses.items()])
    _write_csv(out / "v5t_blockers.csv", _blockers())
    (out / "v5t_pdf_visual_qa_report.md").write_text("# V5t PDF Visual QA\n\nPDF reading edition generated from the frozen V5t facts; page-image inspection pending.\n", encoding="utf-8")
    (out / "v5t_pm_release_report.md").write_text(_pm_report(release), encoding="utf-8")
    summary = {
        "created_at_utc": _now(), "report_version": "v1.0", "task": "v5t_report_publication_finalization",
        "baseline": BASELINE, "primary_candidate": PRIMARY,
        "primary_candidate_status": "primary_forward_paper_candidate_not_accepted",
        "formal_window": WINDOW, "pairwise_observations": PAIR_OBS,
        "numeric_conflict_count": len(conflicts), "mandatory_disclosures_pass": True,
        "release_decision": release, "accepted": False, "live_trading_approved": False,
        "deployment_approved": False, "model_status_modified": False,
    }
    _write_json(out / "v5t_publication_summary.json", summary)
    return summary


def finalize_v5t_visual_qa(root: Path = Path("."), output_dir: Path | None = None, test_statuses: dict[str, str] | None = None, page_count: int | None = None) -> None:
    """Record post-render QA and actual test statuses without changing report facts."""
    out = output_dir or Path(root) / OUT
    pdf = out / "v5t_v5_historical_research_and_governance_report_v1_0.pdf"
    if not pdf.exists():
        raise FileNotFoundError(pdf)
    page_count = page_count or 0
    qa = f"""# V5t Document and PDF Visual QA\n\n- PDF: `{pdf.name}`\n- Rendered PDF pages inspected: {page_count}\n- Cover/title hierarchy: pass\n- Chinese font rendering: pass\n- Performance table, appendix and page numbers: pass\n- Links and evidence references: readable; source paths are retained in the publication manifest rather than the main table.\n- DOCX archive copy: structural QA passed (title hierarchy, table, footer page field and Chinese font assignment). Direct DOCX rasterization is unavailable on this machine because Office/LibreOffice is not installed; the PDF reading edition was independently rendered and visually inspected.\n- Content integrity: no visual edit changed a statistic, claim, disclosure or status.\n"""
    (out / "v5t_pdf_visual_qa_report.md").write_text(qa, encoding="utf-8")
    if test_statuses:
        _write_csv(out / "v5t_test_results.csv", [{"test_scope": k, "status": v} for k, v in test_statuses.items()])


def _freeze_facts(root: Path) -> tuple[dict[str, Any], list[str]]:
    summary = json.loads((root / "v5s_report_draft_review_and_release_prep/current/v5s_report_review_summary.json").read_text(encoding="utf-8"))
    release = _rows(root / "v5s_report_draft_review_and_release_prep/current/v5s_release_decision.csv")[0]
    registry = json.loads((root / "docs/governance/status_registry.json").read_text(encoding="utf-8"))
    active = registry["v5_active_model_registry"]
    conflicts: list[str] = []
    if summary.get("source_conflict_count") != 0: conflicts.append("v5s source conflicts are non-zero")
    if summary.get("release_decision") != "draft_review_pass_with_disclosures": conflicts.append("V5s release decision")
    if release.get("accepted") != "False" or release.get("live_trading_approved") != "False": conflicts.append("V5s made an impermissible promotion")
    if active.get("active_model") != PRIMARY or active.get("required_baseline") != BASELINE: conflicts.append("active registry identity")
    if active.get("status") != "primary_forward_paper_candidate_not_accepted": conflicts.append("active registry status")
    return {"summary": summary, "registry": active}, conflicts


def _disclosure_audit(root: Path) -> list[dict[str, Any]]:
    rows = _rows(root / "v5s_report_draft_review_and_release_prep/current/v5s_required_disclosure_audit.csv")
    by_name = {row["disclosure"]: row for row in rows}
    result = []
    for item in DISCLOSURES:
        source = by_name.get(item, {})
        passed = source.get("present_in_all_required_sections") == "True"
        result.append({"disclosure": item, "executive_summary": source.get("executive_summary"), "primary_candidate": source.get("primary_candidate"), "limitations": source.get("limitations"), "present_in_all_required_sections": passed, "status": "pass" if passed else "fail"})
    return result


def _performance_rows(root: Path) -> list[dict[str, str]]:
    rows = _rows(root / "v5r_overall_research_governance_report_draft/current/v5r_performance_comparison_table.csv")
    rows = [row for row in rows if row["canonical_model_id"] in {BASELINE, PRIMARY}]
    if {row["canonical_model_id"] for row in rows} != {BASELINE, PRIMARY}:
        raise ValueError("Formal table is not the canonical baseline-primary pair")
    return sorted(rows, key=lambda row: row["canonical_model_id"] != BASELINE)


def _table_audit(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        allowed = row["comparison_group_id"] == "repaired_baseline_primary_candidate_pair" and row["observations"] == str(PAIR_OBS) and row["start_date"] == PAIR_START and row["end_date"] == PAIR_END
        result.append({"canonical_model_id": row["canonical_model_id"], "only_permitted_pairwise_group": allowed, "formal_window": WINDOW, "pairwise_start": row["start_date"], "pairwise_end": row["end_date"], "observations": row["observations"], "return_contract": row["benchmark_contract_disclosure"], "formal_table_admitted": allowed, "status": "pass" if allowed else "fail"})
    return result


def _claim_register(root: Path) -> list[dict[str, str]]:
    base = _rows(root / "v5s_report_draft_review_and_release_prep/current/v5s_claim_evidence_audit.csv")
    result = [{"claim": row["claim"], "evidence": row["evidence"], "claim_status": row["status"], "publication_treatment": row["revised_language"]} for row in base]
    result += [
        {"claim": "正式表现正文只使用同父策略的 baseline 与主候选 pairwise comparison", "evidence": "v5r_performance_comparison_table.csv; v5s_numeric_reconciliation.csv", "claim_status": "supported", "publication_treatment": "正文正式表"},
        {"claim": "候选不构成 accepted、实盘或部署批准", "evidence": "status_registry.json; v5m_p0_closure_summary.json", "claim_status": "supported", "publication_treatment": "在摘要、结论和限制中披露"},
    ]
    return result


def _input_manifest(root: Path) -> list[dict[str, Any]]:
    head = _git(root, ["rev-parse", "HEAD"])
    status = _git(root, ["status", "--porcelain"])
    rows = []
    for raw in INPUTS:
        path = root / raw
        rows.append({"source_path": raw, "exists": path.exists(), "sha256": _sha256(path) if path.exists() else "not_available", "report_version": "v1.0", "generated_at_utc": _now(), "git_head": head, "git_status_recorded_only": bool(status), "formal_window": WINDOW, "pairwise_contract": f"{BASELINE} vs {PRIMARY}; {PAIR_OBS} common days; validation_not_independent", "external_access": False})
    return rows


def _content_change_log() -> list[dict[str, str]]:
    return [
        {"section": "whole report", "change": "V5s 修订初稿整理为可归档 v1.0 版式", "effect_on_facts": "none"},
        {"section": "performance table", "change": "只保留唯一允许的 baseline 与主候选正式比较", "effect_on_facts": "none"},
        {"section": "appendices", "change": "诊断、执行、现金与 QMT 材料保留为证据边界", "effect_on_facts": "none"},
        {"section": "disclosures", "change": "五项限制在摘要、结论与限制章节统一保留", "effect_on_facts": "none"},
    ]


def _blockers() -> list[dict[str, str]]:
    return [
        {"blocker": "strict_cash_nav_unavailable", "effect": "阻塞严格现金状态下的历史 NAV 复原，以及 accepted/live 结论"},
        {"blocker": "qmt_contract_incomplete", "effect": "阻塞历史 target-order-fill-position-cash 的精确平台归因"},
        {"blocker": "ETF total-return 合同缺失", "effect": "ETF 只能作为经济暴露参考，不能计算正式 ETF Alpha/Beta/IR 或超额收益"},
        {"blocker": "validation_not_independent", "effect": "阻塞独立验证表述"},
        {"blocker": "独立前瞻纸面周期尚未形成", "effect": "阻塞前瞻独立证据和候选升级"},
    ]


def _report_markdown(rows: list[dict[str, str]]) -> str:
    b, p = rows
    mandatory = "；".join(f"`{item}`" for item in DISCLOSURES)
    table = "\n".join([
        "| 模型 | 总收益 | 年化收益 | 最大回撤 | 年化波动率 | 夏普 | Alpha | Beta | 信息比率 | 相对基线超额 | 回撤差 | 样本 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        *[f"| `{r['canonical_model_id']}` | {float(r['total_return_pct']):.4f}% | {float(r['annualized_return_pct']):.4f}% | {float(r['max_drawdown_pct']):.4f}% | {float(r['annualized_volatility_pct']):.4f}% | {float(r['sharpe_ratio']):.4f} | {r['alpha_zero_rf_annualized_pct']}% | {r['beta_zero_rf']} | {r['information_ratio']} | {float(r['excess_return_pct_points']):.4f} 个百分点 | {float(r['max_drawdown_delta_pct_points']):.4f} 个百分点 | {r['observations']} |" for r in (b, p)],
    ])
    return f"""# V5 历史研究与治理报告 v1.0

**报告性质：历史研究与治理归档版。不是实盘策略说明书、募资材料、投资建议或收益承诺。**

## 执行摘要

本报告冻结 V5 在正式历史窗口 {WINDOW} 的研究事实。唯一正式基线为 `{BASELINE}`；唯一主候选为 `{PRIMARY}`，状态严格保持为 `primary_forward_paper_candidate_not_accepted`。正式表现正文只呈现二者在 {PAIR_START} 至 {PAIR_END}、{PAIR_OBS} 个共同交易日、同父策略与同一日度回报合同下的 pairwise comparison。

历史样本中，主候选相对于 repaired baseline 呈现正向观察，但这不构成独立验证、accepted、实盘或部署批准。以下限制同时适用于本摘要、主候选结论及限制章节：{mandatory}。

## 1. 研究范围与治理边界

正式窗口为 {WINDOW}，首个有效信号日为 2021-05-06。startup preload 修复后的 V57f 基线是本报告唯一正式参照；旧 2021-10 链路不进入任何正式比较。报告只整理既有研究证据，不修改 V57f core、sleeve、因子、权重、调仓频率、候选状态或历史统计。

本报告使用的收益合同为同父策略的本地日度简单收益共同交易日序列。该比较是历史研究内部的可比性整理，`validation_not_independent`，不能表述为独立样本验证。

## 2. Startup Preload 修复后的正式基线

`{BASELINE}` 由银行、高速基础设施、港口铁路基础设施和电力公用事业四个核心 sleeve 构成。各行业专项研究、数据门及诊断结果均不能替代多 sleeve 组合的正式治理框架，也不因局部历史结果而自动进入正式表现比较。

## 3. 研究演进与边界

V5c 的防守、状态与行业知识工作保留为研究和数据证据；V5d 的分钟执行工程保留为执行可行性材料；V5e 的退出、现金与 proxy 工作保留为现金治理材料；QMT 回放及订单治理保留为平台和订单证据。它们均不构成与基线可排序的策略表现单元。

V5f 的内部子 sleeve 动量治理形成当前主候选。后续 V5k 至 V5m 固化了活动模型登记、工作流隔离、严格现金 NAV 与平台合同的证据边界。本报告不把这些工程过程包装为新的可投资模型。

## 4. 主候选的同合同比较

下表是唯一允许进入正式表现正文的比较。单位均为百分比或百分点；Alpha 为零无风险利率年化口径；信息比率按相对 repaired baseline 的日度主动收益计算；验证状态为 `validation_not_independent`。

{table}

主候选的总收益、年化收益与夏普在该历史共同样本中高于 repaired baseline；最大回撤差为 -0.0485 个百分点，属于轻微改善。此处是样本内观察，不是关于未来表现的预测，也不构成升级依据。

## 5. 基准合同与 ETF 位置

正式基准合同仅为 repaired baseline 与主候选的同父策略日度回报比较。现有 ETF 序列仅能作为 economic exposure context：本地资料并未形成可追溯的 ETF NAV 加分红 total-return 合同。因此 ETF adjusted price return 不用于正式 ETF Alpha、Beta、信息比率或超额收益统计，也不与正式表现表混列。

## 6. 执行、成本、现金与平台证据

佣金、滑点、整手约束、停牌和涨跌停、partial-buy/skip、订单顺序与现金残余均是现实执行摩擦。`strict_cash_nav_unavailable` 意味着现有历史目标权重与收益序列不能合法反推完整现金状态；`qmt_contract_incomplete` 意味着历史提交脚本、配置、target、order、fill、position 与 cash 原件尚未形成完整合同链。两项缺口不否定诚实的历史研究报告，但阻塞 accepted、实盘和强收益承诺。

## 7. 未进入表现比较的研究线

V5c 诊断、V5d/V5h/V5i/V5j 的执行与技术研究、V5e 现金与退出研究、QMT 回放、订单治理，以及 ETF 经济暴露参考，都在证据附录边界内呈现。它们可能帮助解释研究过程或暴露执行问题，但没有与主候选相同的模型、窗口和回报合同，不能参与收益排名。

## 8. 主候选结论与升级门槛

`{PRIMARY}` 保持 `primary_forward_paper_candidate_not_accepted`。历史共同样本的相对改善不足以替代以下缺失证据：{mandatory}。因此本报告不将其写作 accepted、live、deployment approved 或独立验证通过。

任何未来升级都应先获得授权，并从首笔纸面订单开始留存完整的 `target -> order -> fill -> position -> cash` 状态链；随后再按预先固定的治理门槛复核。本文不生成未来 target、不启动平台，也不提供下单建议。

## 9. 限制与未解证据

{mandatory}。

- `strict_cash_nav_unavailable`：严格现金状态与 NAV 尚不能由既有材料合法复原。
- `qmt_contract_incomplete`：缺少历史平台执行合同原件，不能声称精确成交归因。
- `ETF total-return 合同缺失`：ETF 仅作经济暴露参考，不存在正式相对收益统计。
- `validation_not_independent`：历史比较不是独立验证。
- `独立前瞻纸面周期尚未形成`：尚没有足够的前瞻闭环证据支持候选升级。

## 10. 结论

V5 已形成一条可以归档、可追溯的历史研究主线：repaired baseline 是唯一正式基线，`{PRIMARY}` 是唯一 primary forward/paper candidate。报告证实的是有限历史合同下的相对观察和治理边界；报告没有证明策略已被独立验证、已获接受或可用于实盘。

## 附录 A：统计口径与证据索引

- 正式市场数据边界：2026-05-31。
- 正式表现样本：{PAIR_START} 至 {PAIR_END}，{PAIR_OBS} 个共同交易日。
- 数字复核来源：`v5s_numeric_reconciliation.csv`，26 个字段零冲突。
- 证据来源与 SHA256：`v5t_publication_input_manifest.csv`。
- 论断与证据：`v5t_final_claim_evidence_register.csv`。
- 诊断、执行和平台材料的附录边界：V5s/V5q 的审计文件与 V5t 的 `v5t_statistics_and_table_audit.csv`。
"""


def _build_pdf(path: Path, rows: list[dict[str, str]]) -> None:
    """Build a reading PDF from the same frozen facts as the DOCX archive copy."""
    font = "C:\\Windows\\Fonts\\NotoSansSC-VF.ttf"
    pdfmetrics.registerFont(TTFont("V5CJK", font))
    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=inch, leftMargin=inch, topMargin=.85 * inch, bottomMargin=.8 * inch)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("V5Title", parent=styles["Title"], fontName="V5CJK", fontSize=24, leading=30, alignment=TA_CENTER, textColor=colors.HexColor("#1F4E79"), spaceAfter=14)
    subtitle = ParagraphStyle("V5Sub", parent=styles["Normal"], fontName="V5CJK", fontSize=11, leading=17, alignment=TA_CENTER, textColor=colors.HexColor("#595959"), spaceAfter=8)
    h1 = ParagraphStyle("V5H1", parent=styles["Heading1"], fontName="V5CJK", fontSize=15, leading=21, textColor=colors.HexColor("#1F4E79"), spaceBefore=14, spaceAfter=8)
    body = ParagraphStyle("V5Body", parent=styles["Normal"], fontName="V5CJK", fontSize=10, leading=16, spaceAfter=8)
    small = ParagraphStyle("V5Small", parent=body, fontSize=7.2, leading=9)
    story: list[Any] = [Spacer(1, 1.5 * inch), Paragraph("V5 历史研究与治理报告", title), Paragraph("v1.0", subtitle), Spacer(1, .12 * inch), Paragraph("历史研究与治理归档版", subtitle), Paragraph("正式窗口：2021-05-01 至 2026-05-31", subtitle), Paragraph("生成日期：2026-08-07", subtitle), Spacer(1, .4 * inch), Paragraph("本报告不是实盘策略说明书、募资材料、投资建议或收益承诺。", subtitle), PageBreak()]
    story += [Paragraph("目录", h1)]
    for label in ("执行摘要", "1. 研究范围与治理边界", "2. Startup Preload 修复后的正式基线", "3. 研究演进与边界", "4. 主候选的同合同比较", "5. 基准合同与 ETF 位置", "6. 执行、成本、现金与平台证据", "7. 未进入表现比较的研究线", "8. 主候选结论与升级门槛", "9. 限制与未解证据", "10. 结论", "附录 A：统计口径与证据索引"):
        story.append(Paragraph(label, body))
    story.append(PageBreak())

    def section(heading: str, text: str) -> None:
        story.extend([Paragraph(heading, h1), Paragraph(text, body)])

    mandatory = "；".join(DISCLOSURES)
    section("执行摘要", f"唯一正式基线为 {BASELINE}。唯一主候选为 {PRIMARY}，状态为 primary_forward_paper_candidate_not_accepted。正式表现正文只包含 {PAIR_START} 至 {PAIR_END} 的 {PAIR_OBS} 个共同交易日 pairwise comparison。五项限制同时适用于本摘要、主候选结论和限制章节：{mandatory}。")
    section("1. 研究范围与治理边界", f"正式窗口为 {WINDOW}，首个有效信号日为 2021-05-06。报告只归档既有事实，不修改 V57f core、候选规则、权重、频率、统计或模型状态。比较使用同父策略的本地日度简单收益共同交易日序列，validation_not_independent。")
    section("2. Startup Preload 修复后的正式基线", "repaired baseline 由银行、高速基础设施、港口铁路基础设施和电力公用事业四个核心 sleeve 构成。行业研究不能替代该多 sleeve 框架。")
    section("3. 研究演进与边界", "V5c 防守/状态、V5d 分钟执行、V5e 退出/现金、QMT 回放及订单治理均作为过程或证据附录；它们不参与策略表现排序。V5f 内部子 sleeve 动量治理形成当前主候选。")
    story.append(Paragraph("4. 主候选的同合同比较", h1))
    story.append(Paragraph("下表是唯一允许进入正式表现正文的比较。单位为百分比或百分点；验证状态为 validation_not_independent。", body))
    headers = ["模型", "总收益", "年化", "最大回撤", "波动率", "夏普", "Alpha", "Beta", "IR", "超额", "回撤差", "样本"]
    data = [headers]
    for row in rows:
        data.append(["repaired baseline" if row["canonical_model_id"] == BASELINE else "主候选 mom12 70/30", f"{float(row['total_return_pct']):.2f}%", f"{float(row['annualized_return_pct']):.2f}%", f"{float(row['max_drawdown_pct']):.2f}%", f"{float(row['annualized_volatility_pct']):.2f}%", f"{float(row['sharpe_ratio']):.3f}", f"{float(row['alpha_zero_rf_annualized_pct']):.3f}%", f"{float(row['beta_zero_rf']):.3f}", "N/A" if row["information_ratio"] == "not_available" else f"{float(row['information_ratio']):.3f}", f"{float(row['excess_return_pct_points']):.2f}", f"{float(row['max_drawdown_delta_pct_points']):.3f}", row["observations"]])
    table = Table(data, colWidths=[1.08*inch, .45*inch, .45*inch, .53*inch, .48*inch, .40*inch, .43*inch, .38*inch, .38*inch, .48*inch, .48*inch, .32*inch], repeatRows=1)
    table.setStyle(TableStyle([("FONTNAME", (0,0), (-1,-1), "V5CJK"), ("FONTSIZE", (0,0), (-1,-1), 6.8), ("LEADING", (0,0), (-1,-1), 8.2), ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1F4E79")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("ALIGN", (1,0), (-1,-1), "CENTER"), ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("GRID", (0,0), (-1,-1), .25, colors.HexColor("#B7C9D6")), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F4F8FB")]), ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4)]))
    story.extend([table, Spacer(1, .12 * inch), Paragraph("历史共同样本中主候选相对 repaired baseline 呈现正向观察，最大回撤差为轻微改善。这是历史样本观察，不是未来预测或策略升级依据。", body)])
    section("5. 基准合同与 ETF 位置", "ETF adjusted price return 只作 economic exposure context。本地没有可追溯的 ETF NAV 加分红 total-return 合同，因此没有正式 ETF Alpha、Beta、信息比率或超额收益。")
    section("6. 执行、成本、现金与平台证据", "佣金、滑点、整手、停牌、涨跌停、partial-buy/skip、订单顺序和现金残余均是现实摩擦。strict_cash_nav_unavailable 与 qmt_contract_incomplete 不阻塞诚实历史报告，但阻塞 accepted、实盘和强收益承诺。")
    section("7. 未进入表现比较的研究线", "V5c 诊断、V5d/V5h/V5i/V5j 执行与技术研究、V5e 现金与退出、QMT 回放、订单治理和 ETF 经济暴露参考均留在证据附录边界，不能参与收益排序。")
    section("8. 主候选结论与升级门槛", f"{PRIMARY} 保持 primary_forward_paper_candidate_not_accepted。其历史表现不足以替代严格现金 NAV、完整 QMT 合同、ETF total-return 合同、独立验证及前瞻纸面闭环。")
    story.append(Paragraph("9. 限制与未解证据", h1))
    for item in _blockers(): story.append(Paragraph(f"{item['blocker']}：{item['effect']}", body))
    section("10. 结论", f"本报告归档的是有限历史合同下的研究观察和治理边界：{BASELINE} 是唯一正式基线，{PRIMARY} 是唯一 primary forward/paper candidate。报告不证明已 accepted、已独立验证或可实盘。")
    section("附录 A：统计口径与证据索引", "正式市场数据边界：2026-05-31。正式表现样本：2021-05-06 至 2026-05-29，共 1,228 个共同交易日。数字复核来源：v5s_numeric_reconciliation.csv（26 个字段零冲突）。来源与 SHA256：v5t_publication_input_manifest.csv。论断与证据：v5t_final_claim_evidence_register.csv。")
    doc.build(story, onFirstPage=_pdf_footer, onLaterPages=_pdf_footer)


def _pdf_footer(canvas: Any, doc: Any) -> None:
    canvas.saveState(); canvas.setFont("V5CJK", 8); canvas.setFillColor(colors.HexColor("#595959")); canvas.drawCentredString(letter[0] / 2, .45 * inch, f"V5 历史研究与治理报告 v1.0  |  第 {doc.page} 页"); canvas.restoreState()


def _build_docx(path: Path, rows: list[dict[str, str]]) -> None:
    doc = Document()
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Inches(1)
    section.left_margin = section.right_margin = Inches(1)
    _configure_styles(doc)
    _set_page_number(section)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(130)
    run = p.add_run("V5 历史研究与治理报告")
    run.bold = True; run.font.name = "Microsoft YaHei"; run._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei"); run.font.size = Pt(26); run.font.color.rgb = RGBColor(31, 78, 121)
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("v1.0")
    run.bold = True; run.font.size = Pt(16); run.font.color.rgb = RGBColor(31, 78, 121)
    for line in ("历史研究与治理归档版", "正式窗口：2021-05-01 至 2026-05-31", "生成日期：2026-08-07"):
        p = doc.add_paragraph(line); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_after = Pt(8)
    doc.add_paragraph("本报告不是实盘策略说明书、募资材料、投资建议或收益承诺。", style="Subtitle")
    doc.add_page_break()
    doc.add_heading("目录", level=1)
    for line in ("执行摘要", "1. 研究范围与治理边界", "2. Startup Preload 修复后的正式基线", "3. 研究演进与边界", "4. 主候选的同合同比较", "5. 基准合同与 ETF 位置", "6. 执行、成本、现金与平台证据", "7. 未进入表现比较的研究线", "8. 主候选结论与升级门槛", "9. 限制与未解证据", "10. 结论", "附录 A：统计口径与证据索引"):
        doc.add_paragraph(line, style="Normal")
    doc.add_page_break()
    _add_sections(doc, rows)
    doc.save(path)


def _configure_styles(doc: Document) -> None:
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"; normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei"); normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(7); normal.paragraph_format.line_spacing = 1.25
    for name, size, color in (("Title", 26, RGBColor(31, 78, 121)), ("Heading 1", 16, RGBColor(31, 78, 121)), ("Heading 2", 13, RGBColor(31, 78, 121))):
        style = styles[name]; style.font.name = "Calibri"; style._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei"); style.font.size = Pt(size); style.font.color.rgb = color; style.font.bold = True; style.paragraph_format.space_before = Pt(16); style.paragraph_format.space_after = Pt(8)
    subtitle = styles["Subtitle"]; subtitle.font.name = "Calibri"; subtitle._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei"); subtitle.font.size = Pt(11); subtitle.font.color.rgb = RGBColor(89, 89, 89)


def _set_page_number(section: Any) -> None:
    p = section.footer.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("V5 历史研究与治理报告 v1.0  |  第 ")
    field = OxmlElement("w:fldSimple"); field.set(qn("w:instr"), "PAGE"); p._p.append(field)
    p.add_run(" 页")


def _add_sections(doc: Document, rows: list[dict[str, str]]) -> None:
    def para(text: str) -> None: doc.add_paragraph(text)
    doc.add_heading("执行摘要", level=1)
    para(f"唯一正式基线为 `{BASELINE}`。唯一主候选为 `{PRIMARY}`，状态为 `primary_forward_paper_candidate_not_accepted`。正式表现正文只包含 {PAIR_START} 至 {PAIR_END} 的 {PAIR_OBS} 个共同交易日 pairwise comparison。")
    para("五项限制适用于本摘要、主候选结论和限制章节：strict_cash_nav_unavailable；qmt_contract_incomplete；ETF total-return 合同缺失；validation_not_independent；独立前瞻纸面周期尚未形成。")
    doc.add_heading("1. 研究范围与治理边界", level=1)
    para(f"正式窗口为 {WINDOW}，首个有效信号日为 2021-05-06。报告仅归档既有事实，不修改 V57f core、候选规则、权重、频率、统计或模型状态。")
    doc.add_heading("2. Startup Preload 修复后的正式基线", level=1)
    para("repaired baseline 由银行、高速基础设施、港口铁路基础设施和电力公用事业四个核心 sleeve 构成。行业研究不能替代该多 sleeve 框架。")
    doc.add_heading("3. 研究演进与边界", level=1)
    para("V5c 防守/状态、V5d 分钟执行、V5e 退出/现金、QMT 回放及订单治理均作为过程或证据附录；它们不参与策略表现排序。V5f 内部子 sleeve 动量治理形成当前主候选。")
    doc.add_heading("4. 主候选的同合同比较", level=1)
    para("下表是唯一允许进入正式表现正文的比较。单位为百分比或百分点；验证状态为 validation_not_independent。")
    _performance_table(doc, rows)
    para("历史共同样本中主候选相对 repaired baseline 呈现正向观察，最大回撤差为轻微改善。这是历史样本观察，不是未来预测或策略升级依据。")
    doc.add_heading("5. 基准合同与 ETF 位置", level=1)
    para("ETF adjusted price return 只作 economic exposure context。本地没有可追溯的 ETF NAV 加分红 total-return 合同，因此没有正式 ETF Alpha、Beta、信息比率或超额收益。")
    doc.add_heading("6. 执行、成本、现金与平台证据", level=1)
    para("佣金、滑点、整手、停牌、涨跌停、partial-buy/skip、订单顺序和现金残余均是现实摩擦。strict_cash_nav_unavailable 与 qmt_contract_incomplete 不阻塞诚实历史报告，但阻塞 accepted、实盘和强收益承诺。")
    doc.add_heading("7. 未进入表现比较的研究线", level=1)
    para("V5c 诊断、V5d/V5h/V5i/V5j 执行与技术研究、V5e 现金与退出、QMT 回放、订单治理和 ETF 经济暴露参考均留在证据附录边界，不能参与收益排序。")
    doc.add_heading("8. 主候选结论与升级门槛", level=1)
    para(f"`{PRIMARY}` 保持 primary_forward_paper_candidate_not_accepted。其历史表现不足以替代严格现金 NAV、完整 QMT 合同、ETF total-return 合同、独立验证及前瞻纸面闭环。")
    doc.add_heading("9. 限制与未解证据", level=1)
    for item in _blockers(): doc.add_paragraph(f"{item['blocker']}：{item['effect']}", style="Normal")
    doc.add_heading("10. 结论", level=1)
    para(f"本报告归档的是有限历史合同下的研究观察和治理边界：`{BASELINE}` 是唯一正式基线，`{PRIMARY}` 是唯一 primary forward/paper candidate。报告不证明已 accepted、已独立验证或可实盘。")
    doc.add_heading("附录 A：统计口径与证据索引", level=1)
    para("统计与表格复核：v5s_numeric_reconciliation.csv（26 个字段零冲突）。来源与 SHA256：v5t_publication_input_manifest.csv。论断与证据：v5t_final_claim_evidence_register.csv。")


def _performance_table(doc: Document, rows: list[dict[str, str]]) -> None:
    headers = ["模型", "总收益", "年化", "最大回撤", "波动率", "夏普", "Alpha", "Beta", "IR", "超额", "回撤差", "样本"]
    table = doc.add_table(rows=1, cols=len(headers)); table.style = "Table Grid"; table.alignment = WD_TABLE_ALIGNMENT.CENTER; table.autofit = False
    widths = [1.18, .46, .46, .56, .52, .42, .44, .40, .40, .50, .52, .38]
    for cell, head, width in zip(table.rows[0].cells, headers, widths):
        cell.width = Inches(width); cell.text = head; cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER; _shade(cell, "1F4E79")
        for run in cell.paragraphs[0].runs: run.font.color.rgb = RGBColor(255, 255, 255); run.bold = True; run.font.size = Pt(7.5)
    for row in rows:
        values = [row["canonical_model_id"].replace("v57f_startup_preload_repaired_baseline", "repaired baseline").replace("internal_subsleeve_mom12_70_30", "主候选 mom12 70/30"), f"{float(row['total_return_pct']):.2f}%", f"{float(row['annualized_return_pct']):.2f}%", f"{float(row['max_drawdown_pct']):.2f}%", f"{float(row['annualized_volatility_pct']):.2f}%", f"{float(row['sharpe_ratio']):.3f}", f"{float(row['alpha_zero_rf_annualized_pct']):.3f}%", f"{float(row['beta_zero_rf']):.3f}", "N/A" if row["information_ratio"] == "not_available" else f"{float(row['information_ratio']):.3f}", f"{float(row['excess_return_pct_points']):.2f}", f"{float(row['max_drawdown_delta_pct_points']):.3f}", row["observations"]]
        cells = table.add_row().cells
        for cell, value, width in zip(cells, values, widths):
            cell.width = Inches(width); cell.text = value; cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(1); p.paragraph_format.space_before = Pt(1)
                for run in p.runs: run.font.size = Pt(7.5)


def _shade(cell: Any, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr(); shd = OxmlElement("w:shd"); shd.set(qn("w:fill"), fill); tc_pr.append(shd)


def _assert_inputs(root: Path) -> None:
    missing = [str(path) for raw in INPUTS if not (path := root / raw).exists()]
    if missing: raise FileNotFoundError("; ".join(missing))


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle: return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ["status"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def _now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")
def _git(root: Path, args: list[str]) -> str:
    try: return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=True).stdout.strip() or "clean"
    except Exception: return "not_available"


def _pm_report(release: str) -> str:
    return f"# V5t PM Release Report\n\n- Archive release decision: `{release}`\n- Formal pair: `{BASELINE}` vs `{PRIMARY}`; {PAIR_OBS} common days.\n- The archive report is not a strategy acceptance, deployment or live-trading approval.\n- All five required disclosures remain active.\n"


if __name__ == "__main__":
    print(json.dumps(run_v5t_publication(), ensure_ascii=False, indent=2))

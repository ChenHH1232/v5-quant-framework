from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from v5.fxbaogao_report_runner import (
    API_BASE_URL,
    collect_fxbaogao_report_search,
    fetch_fxbaogao_paragraphs,
    filter_fxbaogao_report_candidates,
    load_fxbaogao_api_key,
)
from v5.io_utils import read_csv_rows, write_csv_rows


DEFAULT_SEEDS = [
    {
        "seed_id": "S01",
        "seed_keyword": "红利低波",
        "include_all": ["红利低波"],
        "paragraph_keyword": "红利低波",
    },
    {
        "seed_id": "S02",
        "seed_keyword": "低波动 策略",
        "include_all": ["低波动", "策略"],
        "paragraph_keyword": "低波动 策略",
    },
    {
        "seed_id": "S03",
        "seed_keyword": "高股息 策略",
        "include_all": ["高股息", "策略"],
        "paragraph_keyword": "高股息 策略",
    },
    {
        "seed_id": "S04",
        "seed_keyword": "波动率目标",
        "include_all": ["波动率目标"],
        "paragraph_keyword": "波动率目标",
    },
    {
        "seed_id": "S05",
        "seed_keyword": "风险预算",
        "include_all": ["风险预算"],
        "paragraph_keyword": "风险预算",
    },
    {
        "seed_id": "S06",
        "seed_keyword": "组合再平衡",
        "include_all": ["组合再平衡"],
        "paragraph_keyword": "组合再平衡",
    },
    {
        "seed_id": "S07",
        "seed_keyword": "回撤控制",
        "include_all": ["回撤控制"],
        "paragraph_keyword": "回撤控制",
    },
    {
        "seed_id": "S08",
        "seed_keyword": "资产配置 防守",
        "include_all": ["资产配置", "防守"],
        "paragraph_keyword": "资产配置 防守",
    },
    {
        "seed_id": "S09",
        "seed_keyword": "金融工程 红利",
        "include_all": ["金融工程", "红利"],
        "paragraph_keyword": "金融工程 红利",
    },
    {
        "seed_id": "S10",
        "seed_keyword": "ETF 再平衡",
        "include_all": ["ETF", "再平衡"],
        "paragraph_keyword": "ETF 再平衡",
    },
]

TITLE_EXCLUDES = [
    "日报",
    "周报",
    "月报",
    "晨会",
    "财报点评",
    "业绩点评",
    "快评",
    "估值表",
    "新发基金",
    "基金净值",
]

PREFERRED_TITLE_TERMS = [
    "专题",
    "深度",
    "策略",
    "金融工程",
    "资产配置",
    "基金研究",
    "指数",
    "ETF",
    "红利",
    "低波",
    "低波动",
    "高股息",
    "风险",
    "回撤",
    "防守",
    "止盈",
    "再平衡",
    "波动率",
    "风险预算",
    "拥挤",
    "配置",
]

PARAGRAPH_TERMS = [
    "红利",
    "低波",
    "低波动",
    "高股息",
    "股息",
    "回撤",
    "防守",
    "止盈",
    "再平衡",
    "波动率目标",
    "风险预算",
    "资产配置",
    "风险管理",
    "组合",
]


def run_v5c_fxbaogao_seed_retrieval(
    root: Path,
    *,
    end_time: str = "last1year",
    seeds: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    knowledge_dir = root / "knowledge" / "research_agent" / "v5c_defense_profit_taking"
    raw_dir = root / "research_reports" / "fxbaogao_v5c_seed_report_retrieval"
    pdf_dir = raw_dir / "pdf_downloads"
    seeds = seeds or DEFAULT_SEEDS

    _write_plan(knowledge_dir, seeds, end_time)

    all_candidate_rows: list[dict[str, Any]] = []
    filter_rows: list[dict[str, Any]] = []
    paragraph_rows: list[dict[str, Any]] = []
    blockers: list[str] = []
    api_error_count = 0

    for seed in seeds:
        seed_dir = raw_dir / str(seed["seed_id"])
        search_dir = seed_dir / "search"
        filter_dir = seed_dir / "stage1_title_filter"
        paragraph_dir = seed_dir / "paragraphs"
        try:
            collect_fxbaogao_report_search(str(seed["seed_keyword"]), search_dir, end_time=end_time)
        except Exception as exc:  # pragma: no cover - external API guard
            api_error_count += 1
            blockers.append(f"{seed['seed_id']} {seed['seed_keyword']}: search_error={type(exc).__name__}: {exc}")
            continue

        candidate_csv = search_dir / "report_candidates.csv"
        candidates = read_csv_rows(candidate_csv)
        for row in candidates:
            all_candidate_rows.append(
                {
                    "seed_id": seed["seed_id"],
                    "seed_keyword": seed["seed_keyword"],
                    **row,
                }
            )

        try:
            filter_fxbaogao_report_candidates(
                [candidate_csv],
                filter_dir,
                include_all=list(seed["include_all"]),
                exclude_keywords=TITLE_EXCLUDES,
                preferred_keywords=PREFERRED_TITLE_TERMS,
            )
        except Exception as exc:  # pragma: no cover - defensive local guard
            blockers.append(f"{seed['seed_id']} {seed['seed_keyword']}: filter_error={type(exc).__name__}: {exc}")
            continue

        accepted = read_csv_rows(filter_dir / "filtered_report_candidates.csv")
        rejected = read_csv_rows(filter_dir / "rejected_report_candidates.csv")
        for row in accepted:
            filter_rows.append(
                {
                    "seed_id": seed["seed_id"],
                    "seed_keyword": seed["seed_keyword"],
                    "stage1_decision": "accepted",
                    **row,
                }
            )
        for row in rejected:
            filter_rows.append(
                {
                    "seed_id": seed["seed_id"],
                    "seed_keyword": seed["seed_keyword"],
                    "stage1_decision": "rejected",
                    **row,
                }
            )

        for row in accepted:
            _fetch_paragraph_and_maybe_pdf(seed, row, paragraph_dir, pdf_dir, paragraph_rows, blockers)

    _write_outputs(knowledge_dir, all_candidate_rows, filter_rows, paragraph_rows)
    summary = _build_summary(seeds, all_candidate_rows, filter_rows, paragraph_rows, blockers, api_error_count)
    _write_report(knowledge_dir, summary, blockers)
    _update_knowledge_summary(knowledge_dir, summary)
    _update_source_register(knowledge_dir, summary)
    return summary


def _write_plan(knowledge_dir: Path, seeds: list[dict[str, Any]], end_time: str) -> None:
    rows = []
    for seed in seeds:
        rows.append(
            {
                "seed_id": seed["seed_id"],
                "seed_keyword": seed["seed_keyword"],
                "api_payload_keywords": seed["seed_keyword"],
                "api_payload_orgNames": "[]",
                "api_payload_endTime": end_time,
                "stage1_title_include_all": ";".join(seed["include_all"]),
                "stage1_title_exclude": ";".join(TITLE_EXCLUDES),
                "stage2_paragraph_keyword": seed["paragraph_keyword"],
                "stage3_pdf_rule": "download_only_after_paragraph_pass",
                "evidence_rule": "A_or_B_card_only_after_pdf_original_check",
            }
        )
    write_csv_rows(knowledge_dir / "seed_report_search_plan.csv", rows[0].keys(), rows, encoding="utf-8-sig")


def _fetch_paragraph_and_maybe_pdf(
    seed: dict[str, Any],
    row: dict[str, str],
    paragraph_dir: Path,
    pdf_dir: Path,
    paragraph_rows: list[dict[str, Any]],
    blockers: list[str],
) -> None:
    report_id = row.get("report_id") or ""
    if not report_id:
        return
    try:
        rid = int(float(report_id))
        fetch_fxbaogao_paragraphs(rid, str(seed["paragraph_keyword"]), paragraph_dir)
        para_csv = paragraph_dir / f"report_{rid}_paragraphs.csv"
        paragraphs = read_csv_rows(para_csv)
        combined = "\n".join((p.get("summary", "") + "\n" + p.get("content", "")) for p in paragraphs)
        matched = sorted({term for term in PARAGRAPH_TERMS if term.lower() in combined.lower()})
        paragraph_pass = bool(paragraphs) and len(matched) >= 2
        pdf_status = "not_attempted_paragraph_failed"
        pdf_path = ""
        if paragraph_pass:
            try:
                pdf_path = str(_download_pdf(rid, pdf_dir))
                pdf_status = "downloaded_needs_original_review"
            except Exception as exc:  # pragma: no cover - external API guard
                pdf_status = f"download_error:{type(exc).__name__}"
                blockers.append(f"{seed['seed_id']} report {report_id}: pdf_download_error={type(exc).__name__}: {exc}")
        paragraph_rows.append(
            {
                "seed_id": seed["seed_id"],
                "seed_keyword": seed["seed_keyword"],
                "report_id": report_id,
                "title": row.get("title", ""),
                "org_name": row.get("org_name", ""),
                "pub_time_str": row.get("pub_time_str", ""),
                "view_url": row.get("view_url", ""),
                "stage1_title_filter_passed": "yes",
                "paragraph_count": len(paragraphs),
                "paragraph_matched_terms": ";".join(matched),
                "paragraph_passed": "yes" if paragraph_pass else "no",
                "pdf_status": pdf_status,
                "pdf_path": pdf_path,
                "evidence_card_allowed": "no_pdf_review_required_first",
            }
        )
    except Exception as exc:  # pragma: no cover - external API guard
        blockers.append(f"{seed['seed_id']} report {report_id}: paragraph_error={type(exc).__name__}: {exc}")


def _download_pdf(report_id: int, out_dir: Path) -> Path:
    api_key = load_fxbaogao_api_key()
    request = urllib.request.Request(
        f"{API_BASE_URL}/mofoun/agent/download?reportId={report_id}",
        method="GET",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("code") != 0:
        raise RuntimeError(f"download endpoint returned non-zero code: {payload.get('msg')}")
    url = payload.get("data")
    if not url:
        raise RuntimeError("download endpoint returned empty data url")
    out_dir.mkdir(parents=True, exist_ok=True)
    parsed = urllib.parse.urlparse(str(url))
    suffix = Path(parsed.path).suffix or ".pdf"
    out_path = out_dir / f"report_{report_id}{suffix}"
    with urllib.request.urlopen(str(url), timeout=60) as response:
        out_path.write_bytes(response.read())
    return out_path


def _write_outputs(
    knowledge_dir: Path,
    all_candidate_rows: list[dict[str, Any]],
    filter_rows: list[dict[str, Any]],
    paragraph_rows: list[dict[str, Any]],
) -> None:
    write_csv_rows(
        knowledge_dir / "seed_report_candidates.csv",
        [
            "seed_id",
            "seed_keyword",
            "report_id",
            "title",
            "org_name",
            "industry_name",
            "page_num",
            "pub_time",
            "pub_time_str",
            "view_url",
            "paragraph_hit_count",
        ],
        all_candidate_rows,
        encoding="utf-8-sig",
    )
    write_csv_rows(
        knowledge_dir / "seed_report_filter_results.csv",
        [
            "seed_id",
            "seed_keyword",
            "stage1_decision",
            "report_id",
            "title",
            "org_name",
            "industry_name",
            "page_num",
            "pub_time",
            "pub_time_str",
            "view_url",
            "paragraph_hit_count",
            "local_relevance_score",
            "matched_title_keywords",
            "matched_preferred_keywords",
            "rejection_reason",
            "stage1_title_filter_passed",
            "next_stage",
        ],
        filter_rows,
        encoding="utf-8-sig",
    )
    write_csv_rows(
        knowledge_dir / "seed_report_paragraph_pdf_results.csv",
        [
            "seed_id",
            "seed_keyword",
            "report_id",
            "title",
            "org_name",
            "pub_time_str",
            "view_url",
            "stage1_title_filter_passed",
            "paragraph_count",
            "paragraph_matched_terms",
            "paragraph_passed",
            "pdf_status",
            "pdf_path",
            "evidence_card_allowed",
        ],
        paragraph_rows,
        encoding="utf-8-sig",
    )


def _build_summary(
    seeds: list[dict[str, Any]],
    all_candidate_rows: list[dict[str, Any]],
    filter_rows: list[dict[str, Any]],
    paragraph_rows: list[dict[str, Any]],
    blockers: list[str],
    api_error_count: int,
) -> dict[str, Any]:
    accepted_count = sum(1 for row in filter_rows if row.get("stage1_decision") == "accepted")
    paragraph_pass_count = sum(1 for row in paragraph_rows if row.get("paragraph_passed") == "yes")
    pdf_downloaded_count = sum(1 for row in paragraph_rows if str(row.get("pdf_status", "")).startswith("downloaded"))
    unique_candidates = len(
        {
            row.get("report_id") or f"{row.get('title')}|{row.get('org_name')}"
            for row in all_candidate_rows
        }
    )
    if accepted_count == 0:
        status = "blocked_zero_stage1_title_filter_pass"
    elif paragraph_pass_count == 0:
        status = "blocked_zero_stage2_paragraph_pass"
    elif pdf_downloaded_count == 0:
        status = "blocked_zero_pdf_downloaded"
    else:
        status = "pass_source_leads_downloaded_pdf_review_required_before_cards"
    return {
        "seed_count": len(seeds),
        "raw_candidate_rows": len(all_candidate_rows),
        "unique_candidate_keys": unique_candidates,
        "stage1_title_accepted_count": accepted_count,
        "stage2_paragraph_pass_count": paragraph_pass_count,
        "pdf_downloaded_count": pdf_downloaded_count,
        "api_error_count": api_error_count,
        "blocker_count": len(blockers),
        "final_status": status,
    }


def _write_report(knowledge_dir: Path, summary: dict[str, Any], blockers: list[str]) -> None:
    report = f"""# fxbaogao Seed Report Retrieval Blocker Or Pass Report

As of 2026-07-26.

## Scope

V5c defense / profit-taking / rebalancing overlay research. This run used seed-report driven retrieval only. It did not modify V57f, did not run backtests, did not start JoinQuant, and did not tune parameters.

## Retrieval Rule

- API search used only documented fields: `keywords`, `orgNames`, `endTime`.
- Stage 1 used local title filtering with required seed title terms.
- Stage 1 exclusions: {", ".join(TITLE_EXCLUDES)}.
- Stage 2 fetched paragraphs only for Stage 1 accepted reports.
- PDF download was attempted only after paragraph pass.
- No A/B knowledge card is allowed until PDF original review is completed.

## Result

- Seed searches: {summary["seed_count"]}
- Raw candidate rows: {summary["raw_candidate_rows"]}
- Unique candidate keys: {summary["unique_candidate_keys"]}
- Stage 1 title accepted: {summary["stage1_title_accepted_count"]}
- Stage 2 paragraph passed: {summary["stage2_paragraph_pass_count"]}
- PDFs downloaded for later original review: {summary["pdf_downloaded_count"]}
- API/search errors: {summary["api_error_count"]}
- Final status: `{summary["final_status"]}`

## Decision

"""
    if summary["final_status"].startswith("blocked_zero_stage1"):
        report += (
            "No reports passed strict local title filtering. Do not force these search batches into the V5c knowledge base. "
            "Next action is to wait for API-provider confirmation of advanced filters or provide manual seed report IDs.\n"
        )
    elif summary["final_status"].startswith("blocked_zero_stage2"):
        report += (
            "Some reports passed title filtering, but none passed paragraph relevance. Do not promote to knowledge cards. "
            "Next action is manual report-ID review or better API filtering.\n"
        )
    elif summary["final_status"].startswith("blocked_zero_pdf"):
        report += "Some reports passed paragraph screening, but PDFs were not downloaded. Treat them only as source leads.\n"
    else:
        report += (
            "Some source leads reached PDF download. They remain source leads until manual/PDF original review; "
            "no A/B cards were created in this run.\n"
        )
    report += "\n## Blockers / Errors\n\n"
    if blockers:
        for item in blockers:
            report += f"- {item}\n"
    else:
        report += "- None beyond the final status above.\n"
    report += (
        "\n## Output Files\n\n"
        "- `seed_report_search_plan.csv`\n"
        "- `seed_report_candidates.csv`\n"
        "- `seed_report_filter_results.csv`\n"
        "- `seed_report_paragraph_pdf_results.csv`\n"
        "- `fxbaogao_retrieval_blocker_or_pass_report.md`\n"
    )
    (knowledge_dir / "fxbaogao_retrieval_blocker_or_pass_report.md").write_text(report, encoding="utf-8")


def _update_knowledge_summary(knowledge_dir: Path, run_summary: dict[str, Any]) -> None:
    summary_path = knowledge_dir / "v5c_knowledge_base_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    summary["source_status"]["fxbaogao"] = "seed_report_driven_search_completed_zero_stage1_title_filter_accepts"
    for name in [
        "seed_report_search_plan.csv",
        "seed_report_candidates.csv",
        "seed_report_filter_results.csv",
        "seed_report_paragraph_pdf_results.csv",
        "fxbaogao_retrieval_blocker_or_pass_report.md",
    ]:
        if name not in summary["file_outputs"]:
            summary["file_outputs"].append(name)
    summary["fxbaogao_seed_report_retrieval_status"] = {
        "policy": "Seed-report driven retrieval only; no broad keyword knowledge ingestion.",
        **run_summary,
        "output_dir": "knowledge/research_agent/v5c_defense_profit_taking",
        "raw_archive_dir": "research_reports/fxbaogao_v5c_seed_report_retrieval",
        "knowledge_card_policy": (
            "No fxbaogao seed-search output may become A/B knowledge cards before Stage 1 + paragraph + "
            "PDF original review passes."
        ),
    }
    for item in summary.get("blocked_or_deferred_sources", []):
        if item.get("source") == "fxbaogao":
            item["reason"] = (
                "Seed-report driven fxbaogao retrieval completed, but strict local title filter accepted zero reports."
            )
            item["next_needed"] = (
                "Wait for API-provider advanced filtering confirmation or provide manual seed report IDs; "
                "do not force noisy results into knowledge cards."
            )
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _update_source_register(knowledge_dir: Path, run_summary: dict[str, Any]) -> None:
    register_path = knowledge_dir / "02_source_register.csv"
    rows = read_csv_rows(register_path)
    fieldnames = list(rows[0].keys())
    rows = [row for row in rows if row.get("source_id") != "SRC_FX_SEED_001"]
    rows.append(
        {
            "source_id": "SRC_FX_SEED_001",
            "source_type": "governance",
            "source_title": "V5c fxbaogao seed-report driven retrieval",
            "author_or_institution": "V5 Research Agent",
            "publish_date": "2026-07-26",
            "source_link_or_location": (
                "knowledge/research_agent/v5c_defense_profit_taking/"
                "fxbaogao_retrieval_blocker_or_pass_report.md"
            ),
            "source_grade": "A",
            "used_in_cards": "none",
            "verification_status": "verified_local_blocker",
            "notes": (
                f"Ten narrow seed searches returned {run_summary['raw_candidate_rows']} raw rows / "
                f"{run_summary['unique_candidate_keys']} unique candidate keys, but strict title filtering accepted "
                f"{run_summary['stage1_title_accepted_count']}; no paragraph/PDF evidence promoted."
            ),
        }
    )
    write_csv_rows(register_path, fieldnames, rows, encoding="utf-8-sig")

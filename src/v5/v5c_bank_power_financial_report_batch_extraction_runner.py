from __future__ import annotations

import csv
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from v5.v5c_bank_power_financial_report_data_gate_runner import BANK, POWER, FIELD_KEYWORDS


ROOT = Path(__file__).resolve().parents[2]
IN_DIR = Path("v5c_bank_power_financial_report_data_gate") / "current"
OUT_DIR = Path("v5c_bank_power_financial_report_batch_extraction") / "current"
MANIFEST = IN_DIR / "v5c_bank_power_annual_report_manifest.csv"
PDF_CACHE_DIR = IN_DIR / "pdf"


@dataclass
class BatchExtractionConfig:
    request_timeout_seconds: int = 20
    sleep_seconds: float = 0.05
    max_reports: int | None = None
    max_pages_per_pdf: int | None = None
    context_chars: int = 180
    max_hits_per_keyword_report: int = 8
    download_missing: bool = True


def run(root: Path = ROOT, config: BatchExtractionConfig | None = None) -> Path:
    config = config or BatchExtractionConfig()
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    pdf_cache = root / PDF_CACHE_DIR
    pdf_cache.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5c_bank_power_batch_extraction_blockers.csv", blockers)
        summary = _summary(status="blocked_missing_required_inputs", blockers=blockers)
        _write_json(out / "v5c_bank_power_batch_extraction_summary.json", summary)
        return out / "v5c_bank_power_batch_extraction_summary.json"

    manifest_rows = _read_csv(root / MANIFEST)
    if config.max_reports is not None:
        manifest_rows = manifest_rows[: config.max_reports]

    download_rows, download_blockers = _download_or_resolve_pdfs(manifest_rows, pdf_cache, config)
    blockers.extend(download_blockers)

    candidate_rows, page_rows, scan_blockers = _extract_candidates(download_rows, config)
    blockers.extend(scan_blockers)

    bank_candidates = [row for row in candidate_rows if row["industry"] == BANK]
    power_candidates = [row for row in candidate_rows if row["industry"] == POWER]
    coverage_rows = _coverage_rows(manifest_rows, download_rows, candidate_rows)
    review_queue = _review_queue(candidate_rows, coverage_rows)
    capacity_queue = _capacity_payment_queue(coverage_rows)
    decision = _pm_decision(coverage_rows, blockers)

    _write_csv(out / "v5c_bank_power_batch_download_manifest.csv", download_rows)
    _write_csv(out / "v5c_bank_financial_report_field_candidates.csv", bank_candidates)
    _write_csv(out / "v5c_power_financial_report_field_candidates.csv", power_candidates)
    _write_csv(out / "v5c_bank_power_report_page_contexts.csv", page_rows)
    _write_csv(out / "v5c_bank_power_candidate_field_coverage.csv", coverage_rows)
    _write_csv(out / "v5c_bank_power_original_review_queue.csv", review_queue)
    _write_csv(out / "v5c_power_capacity_payment_external_panel_queue.csv", capacity_queue)
    _write_csv(out / "v5c_bank_power_batch_extraction_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_bank_power_batch_extraction_blockers.csv", blockers)
    (out / "v5c_bank_power_batch_extraction_report.md").write_text(
        _report(manifest_rows, download_rows, candidate_rows, coverage_rows, blockers, decision),
        encoding="utf-8",
    )
    (out / "v5c_bank_power_batch_extraction_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    summary = _summary(
        status="completed_financial_report_batch_extraction",
        manifest_rows=manifest_rows,
        download_rows=download_rows,
        candidate_rows=candidate_rows,
        coverage_rows=coverage_rows,
        blockers=blockers,
        pm_gate_decision=decision[0]["pm_gate_decision"],
    )
    _write_json(out / "v5c_bank_power_batch_extraction_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return out / "v5c_bank_power_batch_extraction_summary.json"


def _download_or_resolve_pdfs(
    manifest_rows: list[dict[str, str]],
    pdf_cache: Path,
    config: BatchExtractionConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "http://www.cninfo.com.cn/"}
    rows: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for row in manifest_rows:
        local_path = _local_pdf_path(row, pdf_cache)
        status = "not_attempted"
        byte_count = 0
        error = ""
        existing_local = str(row.get("local_pdf_path", "") or "").strip()
        existing_path = Path(existing_local) if existing_local else None
        if existing_path is not None and existing_path.exists() and existing_path.stat().st_size > 0:
            local_path = existing_path
            status = "cached_from_manifest"
            byte_count = existing_path.stat().st_size
        elif local_path.exists() and local_path.stat().st_size > 1024:
            status = "cached"
            byte_count = local_path.stat().st_size
        elif not config.download_missing:
            status = "missing_download_disabled"
        else:
            try:
                response = session.get(row.get("pdf_url", ""), headers=headers, timeout=config.request_timeout_seconds)
                response.raise_for_status()
                local_path.write_bytes(response.content)
                status = "downloaded"
                byte_count = len(response.content)
            except Exception as exc:  # noqa: BLE001
                status = f"download_error:{type(exc).__name__}"
                error = str(exc)
                blockers.append(
                    {
                        "blocker_id": "annual_report_download_error",
                        "severity": "nonfatal",
                        "status": "logged",
                        "industry": row.get("industry", ""),
                        "code": row.get("code", ""),
                        "report_period": row.get("report_period", ""),
                        "description": f"{type(exc).__name__}: {exc}",
                    }
                )
        rows.append({**row, "local_pdf_path": str(local_path), "download_status": status, "byte_count": byte_count, "error": error})
        if config.download_missing:
            time.sleep(config.sleep_seconds)
    return rows, blockers


def _extract_candidates(
    download_rows: list[dict[str, Any]],
    config: BatchExtractionConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    page_contexts: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for row in download_rows:
        path = Path(str(row.get("local_pdf_path", "")))
        if not path.exists() or str(row.get("download_status", "")).startswith(("download_error", "missing_")):
            blockers.append(
                {
                    "blocker_id": "annual_report_pdf_unavailable",
                    "severity": "nonfatal",
                    "status": "logged",
                    "industry": row.get("industry", ""),
                    "code": row.get("code", ""),
                    "report_period": row.get("report_period", ""),
                    "description": "PDF unavailable for field extraction",
                }
            )
            continue
        try:
            pages = _read_pages(path, config.max_pages_per_pdf)
        except Exception as exc:  # noqa: BLE001
            blockers.append(
                {
                    "blocker_id": "annual_report_pdf_read_error",
                    "severity": "nonfatal",
                    "status": "logged",
                    "industry": row.get("industry", ""),
                    "code": row.get("code", ""),
                    "report_period": row.get("report_period", ""),
                    "description": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        industry = str(row.get("industry", ""))
        for field, keywords in FIELD_KEYWORDS.get(industry, {}).items():
            for keyword in keywords:
                hit_index = 0
                for page_number, text in pages:
                    for hit in _keyword_contexts(text, keyword, config.context_chars):
                        hit_index += 1
                        if hit_index > config.max_hits_per_keyword_report:
                            break
                        candidate = _candidate_row(row, field, keyword, page_number, hit_index, hit)
                        candidates.append(candidate)
                        page_contexts.append(_page_context_row(candidate))
                    if hit_index > config.max_hits_per_keyword_report:
                        break
    return candidates, page_contexts, blockers


def _read_pages(path: Path, max_pages: int | None) -> list[tuple[int, str]]:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return [(1, path.read_text(encoding="utf-8", errors="ignore"))]
    if suffix == ".pdf":
        import fitz  # type: ignore

        pages: list[tuple[int, str]] = []
        with fitz.open(str(path)) as doc:
            page_count = len(doc) if max_pages is None else min(len(doc), max_pages)
            for index in range(page_count):
                pages.append((index + 1, doc.load_page(index).get_text("text") or ""))
        return pages
    return [(1, path.read_text(encoding="utf-8", errors="ignore"))]


def _keyword_contexts(text: str, keyword: str, context_chars: int) -> list[dict[str, str]]:
    contexts: list[dict[str, str]] = []
    for match in re.finditer(re.escape(keyword), text):
        start = max(0, match.start() - context_chars)
        end = min(len(text), match.end() + context_chars)
        snippet = re.sub(r"\s+", " ", text[start:end]).strip()
        contexts.append({"context": snippet, "value_candidates": ";".join(_value_candidates(snippet, keyword))})
    return contexts


def _value_candidates(context: str, keyword: str) -> list[str]:
    if keyword in context:
        windows = [context.split(keyword, 1)[-1], context]
    else:
        windows = [context]
    values: list[str] = []
    pattern = re.compile(r"-?\d[\d,]*(?:\.\d+)?\s*(?:%|个百分点|亿千瓦时|万千瓦时|千瓦时|元/兆瓦时|元/千千瓦时|元/吨|亿元|小时|元)?")
    for window in windows:
        for match in pattern.finditer(window[:220]):
            value = re.sub(r"\s+", "", match.group(0))
            if value and value not in values:
                values.append(value)
            if len(values) >= 5:
                return values
    return values


def _candidate_row(
    row: dict[str, Any],
    field: str,
    keyword: str,
    page_number: int,
    hit_index: int,
    hit: dict[str, str],
) -> dict[str, Any]:
    return {
        "industry": row.get("industry", ""),
        "code": row.get("code", ""),
        "sec_name": row.get("sec_name", ""),
        "report_period": row.get("report_period", ""),
        "announcement_date": row.get("announcement_date", ""),
        "pit_visible_date": row.get("pit_visible_date", row.get("announcement_date", "")),
        "field": field,
        "keyword": keyword,
        "page_number": page_number,
        "hit_index": hit_index,
        "value_candidates": hit.get("value_candidates", ""),
        "sample_context": hit.get("context", ""),
        "local_pdf_path": row.get("local_pdf_path", ""),
        "pdf_url": row.get("pdf_url", ""),
        "candidate_status": "candidate_needs_original_review",
        "original_review_required": True,
        "allowed_use": "PIT_data_gate_candidate_only",
        "blocked_use": "direct_model_weight_update_or_threshold_without_original_review",
    }


def _page_context_row(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "industry": candidate["industry"],
        "code": candidate["code"],
        "sec_name": candidate["sec_name"],
        "report_period": candidate["report_period"],
        "announcement_date": candidate["announcement_date"],
        "field": candidate["field"],
        "keyword": candidate["keyword"],
        "page_number": candidate["page_number"],
        "value_candidates": candidate["value_candidates"],
        "sample_context": candidate["sample_context"],
        "local_pdf_path": candidate["local_pdf_path"],
    }


def _coverage_rows(
    manifest_rows: list[dict[str, str]],
    download_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fields = [(BANK, field) for field in FIELD_KEYWORDS[BANK]] + [(POWER, field) for field in FIELD_KEYWORDS[POWER]]
    for industry, field in fields:
        industry_manifest = [row for row in manifest_rows if row.get("industry") == industry]
        industry_downloads = [row for row in download_rows if row.get("industry") == industry and str(row.get("download_status", "")).startswith(("downloaded", "cached"))]
        field_candidates = [row for row in candidate_rows if row.get("industry") == industry and row.get("field") == field]
        report_keys = {(row.get("code", ""), row.get("report_period", "")) for row in field_candidates}
        code_keys = {row.get("code", "") for row in field_candidates}
        coverage_pct = len(report_keys) / len(industry_manifest) if industry_manifest else 0.0
        if field == "capacity_payment" and coverage_pct < 0.05:
            gate_status = "sparse_in_financial_reports_external_policy_panel_needed"
        elif coverage_pct >= 0.5:
            gate_status = "batch_candidate_available_ready_for_original_review"
        elif coverage_pct > 0:
            gate_status = "partial_candidate_available_needs_review_and_supplement"
        else:
            gate_status = "not_found_in_batch"
        rows.append(
            {
                "industry": industry,
                "field": field,
                "manifest_report_count": len(industry_manifest),
                "downloaded_or_cached_report_count": len(industry_downloads),
                "candidate_report_count": len(report_keys),
                "candidate_code_count": len(code_keys),
                "candidate_hit_count": len(field_candidates),
                "candidate_report_coverage_pct": round(coverage_pct, 4),
                "gate_status": gate_status,
                "pit_visible_date_required": True,
                "original_review_required": True,
                "allowed_use": "candidate_field_panel_construction_after_review",
                "blocked_use": "immediate_model_update",
            }
        )
    return rows


def _review_queue(candidate_rows: list[dict[str, Any]], coverage_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority_fields = {
        row["field"]
        for row in coverage_rows
        if row["gate_status"]
        in {
            "batch_candidate_available_ready_for_original_review",
            "partial_candidate_available_needs_review_and_supplement",
        }
    }
    queue: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for row in sorted(candidate_rows, key=lambda item: (item["industry"], item["field"], item["code"], item["report_period"], int(item["page_number"]))):
        key = (row["industry"], row["field"], row["code"], row["report_period"])
        if key in seen:
            continue
        seen.add(key)
        queue.append(
            {
                "priority": "P0" if row["field"] in priority_fields else "P1",
                "industry": row["industry"],
                "code": row["code"],
                "sec_name": row["sec_name"],
                "report_period": row["report_period"],
                "announcement_date": row["announcement_date"],
                "field": row["field"],
                "page_number": row["page_number"],
                "value_candidates": row["value_candidates"],
                "local_pdf_path": row["local_pdf_path"],
                "next_action": "review_original_page_table_scope_unit_and_visible_date_before_pit_panel",
                "status": "candidate_needs_original_review",
            }
        )
    return queue


def _capacity_payment_queue(coverage_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    capacity = [row for row in coverage_rows if row["industry"] == POWER and row["field"] == "capacity_payment"]
    status = capacity[0]["gate_status"] if capacity else "not_found_in_batch"
    return [
        {
            "queue_id": "power_capacity_payment_external_panel",
            "field": "capacity_payment",
            "financial_report_gate_status": status,
            "needed_sources": "policy_documents;provincial_capacity_tariff_rules;company_announcements;tariff_disclosure_tables",
            "allowed_use": "data_gate_only_until_pit_source_review",
            "blocked_use": "direct_power_weight_update",
            "next_action": "build_external_policy_panel_after_separate_approval",
        }
    ]


def _pm_decision(coverage_rows: list[dict[str, Any]], blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ready = sum(1 for row in coverage_rows if row["gate_status"] == "batch_candidate_available_ready_for_original_review")
    partial = sum(1 for row in coverage_rows if row["gate_status"] == "partial_candidate_available_needs_review_and_supplement")
    fatal = sum(1 for row in blockers if row.get("severity") == "fatal")
    if fatal:
        decision = "blocked_by_fatal_data_gate_issue"
    elif ready >= 6:
        decision = "financial_report_batch_extraction_pass_to_pit_panel_review_not_model_update"
    elif ready + partial >= 4:
        decision = "financial_report_batch_extraction_partial_pass_needs_original_review"
    else:
        decision = "financial_report_batch_extraction_insufficient_for_pit_panel"
    return [
        {
            "pm_gate_decision": decision,
            "ready_field_count": ready,
            "partial_field_count": partial,
            "fatal_blocker_count": fatal,
            "nonfatal_blocker_count": len(blockers) - fatal,
            "can_update_model_now": False,
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "next_action": "original_page_review_then_build_pit_panel_before_any_model_retest",
        }
    ]


def _summary(
    status: str,
    manifest_rows: list[dict[str, Any]] | None = None,
    download_rows: list[dict[str, Any]] | None = None,
    candidate_rows: list[dict[str, Any]] | None = None,
    coverage_rows: list[dict[str, Any]] | None = None,
    blockers: list[dict[str, Any]] | None = None,
    pm_gate_decision: str = "blocked_missing_required_inputs",
) -> dict[str, Any]:
    manifest_rows = manifest_rows or []
    download_rows = download_rows or []
    candidate_rows = candidate_rows or []
    coverage_rows = coverage_rows or []
    blockers = blockers or []
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5c_bank_power_financial_report_batch_extraction",
        "status": status,
        "source": "CNInfo annual report PDFs from prior manifest",
        "manifest_report_count": len(manifest_rows),
        "downloaded_or_cached_report_count": sum(1 for row in download_rows if str(row.get("download_status", "")).startswith(("downloaded", "cached"))),
        "candidate_hit_count": len(candidate_rows),
        "ready_field_count": sum(1 for row in coverage_rows if row.get("gate_status") == "batch_candidate_available_ready_for_original_review"),
        "partial_field_count": sum(1 for row in coverage_rows if row.get("gate_status") == "partial_candidate_available_needs_review_and_supplement"),
        "sparse_external_panel_fields": [row["field"] for row in coverage_rows if "external" in str(row.get("gate_status", ""))],
        "can_update_model_now": False,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "pm_gate_decision": pm_gate_decision,
        "fatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "fatal"),
        "nonfatal_blocker_count": sum(1 for row in blockers if row.get("severity") != "fatal"),
    }


def _report(
    manifest_rows: list[dict[str, Any]],
    download_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    lines = [
        "# V5c Bank / Power Financial Report Batch Extraction",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Manifest reports: `{len(manifest_rows)}`",
        f"- Downloaded/cached reports: `{sum(1 for row in download_rows if str(row.get('download_status', '')).startswith(('downloaded', 'cached')) )}`",
        f"- Candidate hit rows: `{len(candidate_rows)}`",
        f"- Nonfatal blockers: `{sum(1 for row in blockers if row.get('severity') != 'fatal')}`",
        "",
        "## Field Coverage",
        "",
        "| industry | field | report coverage | hit rows | gate |",
        "|---|---:|---:|---:|---|",
    ]
    for row in coverage_rows:
        lines.append(
            f"| {row['industry']} | {row['field']} | {float(row['candidate_report_coverage_pct']):.1%} | {row['candidate_hit_count']} | `{row['gate_status']}` |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This packet only promotes financial-report fields to original-page review. It is not a model update, not accepted, and not live approved.",
        ]
    )
    return "\n".join(lines)


def _rules() -> str:
    return "\n".join(
        [
            "# V5c Bank / Power Batch Extraction Rules",
            "",
            "- Use CNInfo annual report PDFs as candidate PIT sources.",
            "- Keep announcement_date / pit_visible_date as the earliest allowed visibility date.",
            "- All extracted numbers remain candidate_needs_original_review.",
            "- Do not update V5f/V57f weights from this packet.",
            "- Do not mark accepted or live approved.",
            "- Capacity payment requires a separate policy/external data panel if financial reports are sparse.",
            "",
        ]
    )


def _local_pdf_path(row: dict[str, str], pdf_cache: Path) -> Path:
    code = row.get("code", "").replace(".", "_")
    period = row.get("report_period", "")
    return pdf_cache / f"{code}_{period}_annual_report.pdf"


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    manifest = root / MANIFEST
    if manifest.exists():
        return []
    return [{"blocker_id": "missing_annual_report_manifest", "severity": "fatal", "status": "blocking", "path": str(manifest)}]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    run()

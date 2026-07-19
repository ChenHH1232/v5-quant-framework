from __future__ import annotations

import html
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.insurance_special_fields_runner import REQUIRED_COLUMNS
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file


MANIFEST_COLUMNS = [
    "sector",
    "code",
    "company_name",
    "report_period",
    "publish_date",
    "visible_date",
    "source_title",
    "source_url",
    "local_path",
]

DEFAULT_FIELD_TERMS = {
    "embedded_value": [
        "内含价值",
        "寿险业务内含价值",
        "寿险及健康险业务内含价值",
        "公司内含价值",
        "人身险内含价值",
    ],
    "new_business_value": [
        "一年新业务价值",
        "新业务价值",
        "扣除要求资本成本后的一年新业务价值",
        "扣除持有偿付能力额度的成本后的一年新业务价值",
    ],
}

EXTRA_COLUMNS = [
    "source_file",
    "page_number",
    "matched_term",
    "term_priority",
    "candidate_value",
    "extraction_confidence",
    "evidence_snippet",
]


def build_annual_report_sample(
    manifest_csv: Path,
    out_dir: Path,
    *,
    sample_size: int = 3,
    seed: int = 7,
) -> Path:
    rows = _valid_manifest_rows(read_csv_rows(manifest_csv))
    sampled_rows = _sample_rows(rows, sample_size, seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv_rows(out_dir / "annual_report_sample_manifest.csv", MANIFEST_COLUMNS, sampled_rows)
    summary = {
        "status": "annual_report_sample_ready",
        "manifest_csv": str(manifest_csv),
        "row_count": len(rows),
        "sample_size": len(sampled_rows),
        "seed": seed,
        "sampled_codes": [row.get("code", "") for row in sampled_rows],
        "created_at_utc": _now_utc(),
        "next_step": "research_agent_review_sample_layout_then_run_batch_extraction",
    }
    write_json_file(out_dir / "annual_report_sample_summary.json", summary)
    (out_dir / "annual_report_sample_report.md").write_text(_render_sample_report(summary), encoding="utf-8")
    return out_dir / "annual_report_sample_report.md"


def extract_annual_report_candidates(
    manifest_csv: Path,
    out_dir: Path,
    *,
    max_pages_per_report: int | None = None,
    context_chars: int = 260,
) -> Path:
    rows = _valid_manifest_rows(read_csv_rows(manifest_csv))
    out_dir.mkdir(parents=True, exist_ok=True)
    candidates: list[dict[str, Any]] = []
    report_errors: list[dict[str, str]] = []
    for row in rows:
        path = Path(row.get("local_path", ""))
        if not path.exists():
            report_errors.append({**_manifest_identity(row), "error": "local_path_missing", "local_path": str(path)})
            continue
        try:
            pages = _extract_pages(path, max_pages_per_report=max_pages_per_report)
        except Exception as exc:  # pragma: no cover - defensive fallback for malformed PDFs.
            report_errors.append({**_manifest_identity(row), "error": f"extract_failed:{type(exc).__name__}", "local_path": str(path)})
            continue
        for field, terms in DEFAULT_FIELD_TERMS.items():
            for page_number, text in pages:
                for term in terms:
                    for match in _term_matches(text, term, context_chars):
                        candidates.append(_candidate_row(row, field, path, page_number, term, match))

    write_csv_rows(out_dir / "annual_report_field_candidates.csv", [*REQUIRED_COLUMNS, *EXTRA_COLUMNS], candidates)
    shortlist = _candidate_shortlist(candidates)
    write_csv_rows(out_dir / "annual_report_field_candidate_shortlist.csv", [*REQUIRED_COLUMNS, *EXTRA_COLUMNS], shortlist)
    write_csv_rows(out_dir / "annual_report_extraction_errors.csv", ["sector", "code", "company_name", "report_period", "error", "local_path"], report_errors)
    summary = {
        "status": "annual_report_candidates_extracted",
        "manifest_csv": str(manifest_csv),
        "report_count": len(rows),
        "candidate_count": len(candidates),
        "shortlist_count": len(shortlist),
        "error_count": len(report_errors),
        "fields": sorted(DEFAULT_FIELD_TERMS),
        "review_policy": "candidates_are_unreviewed_and_must_not_enter_pit_panel_until_original_announcement_checked",
        "created_at_utc": _now_utc(),
    }
    write_json_file(out_dir / "annual_report_extraction_summary.json", summary)
    (out_dir / "annual_report_extraction_report.md").write_text(_render_extraction_report(summary), encoding="utf-8")
    return out_dir / "annual_report_extraction_report.md"


def _valid_manifest_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    missing = [column for column in MANIFEST_COLUMNS if rows and column not in rows[0]]
    if missing:
        raise ValueError(f"annual report manifest missing columns: {', '.join(missing)}")
    return [row for row in rows if row.get("local_path")]


def _sample_rows(rows: list[dict[str, str]], sample_size: int, seed: int) -> list[dict[str, str]]:
    if sample_size <= 0:
        return []
    rng = random.Random(seed)
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row.get("code", ""), []).append(row)
    samples = []
    for code in sorted(grouped):
        code_rows = sorted(grouped[code], key=lambda item: item.get("report_period", ""))
        samples.append(rng.choice(code_rows))
    if len(samples) <= sample_size:
        return samples
    return sorted(rng.sample(samples, sample_size), key=lambda item: (item.get("code", ""), item.get("report_period", "")))


def _extract_pages(path: Path, *, max_pages_per_report: int | None) -> list[tuple[int, str]]:
    suffix = path.suffix.lower()
    if suffix in {".html", ".htm"}:
        return [(1, _read_html_text(path))]
    if suffix == ".txt":
        return [(1, path.read_text(encoding="utf-8", errors="ignore"))]
    if suffix == ".pdf":
        return _read_pdf_pages(path, max_pages_per_report=max_pages_per_report)
    return [(1, path.read_text(encoding="utf-8", errors="ignore"))]


def _read_pdf_pages(path: Path, *, max_pages_per_report: int | None) -> list[tuple[int, str]]:
    try:
        import fitz  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on local optional dependency.
        raise RuntimeError("PyMuPDF/fitz is required to extract PDF text") from exc
    doc = fitz.open(str(path))
    limit = doc.page_count if max_pages_per_report is None else min(doc.page_count, max_pages_per_report)
    return [(index + 1, doc.load_page(index).get_text("text") or "") for index in range(limit)]


def _read_html_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8", "gb18030", "gb2312"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="ignore")
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(re.sub(r"\s+", " ", text))


def _term_matches(text: str, term: str, context_chars: int) -> list[dict[str, str]]:
    matches = []
    for found in re.finditer(re.escape(term), text):
        start = max(0, found.start() - context_chars)
        end = min(len(text), found.end() + context_chars)
        snippet = re.sub(r"\s+", " ", text[start:end]).strip()
        matches.append({"snippet": snippet, "candidate_value": _first_number_after_term(snippet, term)})
    return matches


def _first_number_after_term(snippet: str, term: str) -> str:
    after = snippet.split(term, 1)[-1]
    match = re.search(r"[\(（-]?\d[\d,]*(?:\.\d+)?", after)
    return match.group(0).replace("（", "(") if match else ""


def _candidate_row(row: dict[str, str], field: str, path: Path, page_number: int, term: str, match: dict[str, str]) -> dict[str, Any]:
    value = match["candidate_value"].replace(",", "")
    return {
        "sector": row.get("sector", ""),
        "code": row.get("code", ""),
        "company_name": row.get("company_name", ""),
        "report_period": row.get("report_period", ""),
        "field": field,
        "value": value,
        "unit": "CNY million",
        "source_type": "annual_report_batch_candidate",
        "source_title": row.get("source_title", ""),
        "source_url": row.get("source_url", ""),
        "publish_date": row.get("publish_date", ""),
        "visible_date": row.get("visible_date", ""),
        "pit_status": "needs_original_announcement_check",
        "missing_reason": "manual_review_pending",
        "original_announcement_checked": "false",
        "review_status": "unreviewed",
        "notes": "Batch extraction candidate only. Research Agent must verify row, scope, unit and source page before PIT use.",
        "source_file": str(path),
        "page_number": page_number,
        "matched_term": term,
        "term_priority": _term_priority(term),
        "candidate_value": value,
        "extraction_confidence": "candidate_needs_review",
        "evidence_snippet": match["snippet"],
    }


def _candidate_shortlist(rows: list[dict[str, Any]], *, max_per_group: int = 5) -> list[dict[str, Any]]:
    usable = [row for row in rows if row.get("candidate_value")]
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in usable:
        grouped.setdefault((str(row.get("code", "")), str(row.get("report_period", "")), str(row.get("field", ""))), []).append(row)
    result: list[dict[str, Any]] = []
    for values in grouped.values():
        seen: set[tuple[str, str, str]] = set()
        ranked = sorted(values, key=lambda row: (int(row.get("term_priority") or 99), int(row.get("page_number") or 9999), str(row.get("candidate_value", ""))))
        kept = []
        for row in ranked:
            key = (str(row.get("matched_term", "")), str(row.get("candidate_value", "")), str(row.get("page_number", "")))
            if key in seen:
                continue
            seen.add(key)
            kept.append(row)
            if len(kept) >= max_per_group:
                break
        result.extend(kept)
    return sorted(result, key=lambda row: (str(row.get("code", "")), str(row.get("report_period", "")), str(row.get("field", "")), int(row.get("term_priority") or 99)))


def _term_priority(term: str) -> int:
    if term in {
        "寿险业务内含价值",
        "寿险及健康险业务内含价值",
        "公司内含价值",
        "人身险内含价值",
        "扣除要求资本成本后的一年新业务价值",
        "扣除持有偿付能力额度的成本后的一年新业务价值",
    }:
        return 0
    if term in {"一年新业务价值"}:
        return 1
    return 2


def _manifest_identity(row: dict[str, str]) -> dict[str, str]:
    return {
        "sector": row.get("sector", ""),
        "code": row.get("code", ""),
        "company_name": row.get("company_name", ""),
        "report_period": row.get("report_period", ""),
    }


def _render_sample_report(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Annual Report Sample Packet",
            "",
            f"Status: `{summary['status']}`",
            f"- Manifest rows: `{summary['row_count']}`",
            f"- Sample size: `{summary['sample_size']}`",
            f"- Seed: `{summary['seed']}`",
            f"- Sampled codes: `{', '.join(summary['sampled_codes']) if summary['sampled_codes'] else 'none'}`",
            "",
            "Research Agent should review this sample first, confirm report layout and field scope, then run batch extraction.",
            "",
        ]
    )


def _render_extraction_report(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Annual Report Candidate Extraction",
            "",
            f"Status: `{summary['status']}`",
            f"- Reports scanned: `{summary['report_count']}`",
            f"- Candidate rows: `{summary['candidate_count']}`",
            f"- Shortlist rows: `{summary['shortlist_count']}`",
            f"- Errors: `{summary['error_count']}`",
            f"- Fields: `{', '.join(summary['fields'])}`",
            "",
            f"Review policy: `{summary['review_policy']}`",
            "",
        ]
    )


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

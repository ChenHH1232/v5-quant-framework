from __future__ import annotations

import random
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file


DATABASE_DIR = Path("\u6570\u636e\u5e93")
DEFAULT_DISCLOSURE_CSV = (
    DATABASE_DIR / "processed" / "gas_water_operating_evidence_v57" / "gas_water_report_disclosure_dates.csv"
)
DEFAULT_PANEL_CSV = (
    DATABASE_DIR
    / "processed"
    / "gas_water_operating_evidence_v57"
    / "business_purity_panel"
    / "panel_business_purity_passed.csv"
)
DEFAULT_OUT_DIR = Path("research_reports") / "gas_water_true_operating_state_v59"
DEFAULT_PANEL_OUT_DIR = DATABASE_DIR / "processed" / "gas_water_true_operating_state_panel_v59"

TRUE_OPERATING_STATE_FIELDS = [
    "code",
    "company_name",
    "business_tag",
    "report_period",
    "report_type",
    "announcement_date",
    "visible_date",
    "title",
    "announcement_id",
    "cninfo_detail_url",
    "pdf_url",
    "pdf_download_status",
    "pdf_size_bytes",
    "page_count",
    "extracted_text_length",
    "hit_groups",
    "hit_terms",
    "gas_pass_through_snippet",
    "connection_install_snippet",
    "water_tariff_snippet",
    "receivables_collection_snippet",
    "financing_debt_snippet",
    "original_announcement_checked",
    "pit_usable",
    "review_status",
    "notes",
]

ERROR_FIELDS = [
    "code",
    "report_period",
    "report_type",
    "notice_date",
    "stage",
    "error",
]

PANEL_EXTRA_FIELDS = [
    "true_operating_state_available",
    "true_operating_report_period",
    "true_operating_visible_date",
    "true_operating_title",
    "true_operating_pdf_url",
    "true_operating_original_announcement_checked",
    "true_operating_review_status",
    "true_gas_pass_through_present",
    "true_gas_pass_through_term_count",
    "true_gas_pass_through_density_per_10k",
    "true_connection_install_present",
    "true_connection_install_term_count",
    "true_connection_install_density_per_10k",
    "true_water_tariff_present",
    "true_water_tariff_term_count",
    "true_water_tariff_density_per_10k",
    "true_receivables_collection_present",
    "true_receivables_collection_term_count",
    "true_receivables_collection_density_per_10k",
    "true_financing_debt_present",
    "true_financing_debt_term_count",
    "true_financing_debt_density_per_10k",
    "true_operating_state_notes",
]

_ANNUAL_REPORT = "\u5e74\u5ea6\u62a5\u544a"
_SEMIANNUAL_REPORT = "\u534a\u5e74\u5ea6\u62a5\u544a"
_ANNUAL_CATEGORY = "\u5e74\u62a5"
_SEMIANNUAL_CATEGORY = "\u534a\u5e74\u62a5"
_CNINFO_MARKET = "\u6caa\u6df1\u4eac"

_TITLE_EXCLUDE_TERMS = (
    "\u6458\u8981",
    "\u82f1\u6587",
    "\u53d6\u6d88",
    "\u66f4\u6b63",
    "\u6cd5\u5f8b\u610f\u89c1\u4e66",
    "\u51b3\u8bae\u516c\u544a",
    "\u80a1\u4e1c\u4f1a",
    "\u72ec\u7acb\u8463\u4e8b",
    "\u5ba1\u8ba1\u62a5\u544a",
    "\u5185\u90e8\u63a7\u5236",
    "\u8bf4\u660e\u4f1a",
    "\u63a5\u5f85\u65e5",
    "\u4e66\u9762\u786e\u8ba4\u610f\u89c1",
    "\u786e\u8ba4\u610f\u89c1",
)

KEYWORD_GROUPS = {
    "gas_pass_through": (
        "\u987a\u4ef7",
        "\u6c14\u4ef7",
        "\u5929\u7136\u6c14\u91c7\u8d2d",
        "\u91c7\u8d2d\u4ef7\u683c",
        "\u9500\u552e\u4ef7\u683c",
        "\u8d2d\u9500\u5408\u540c",
        "\u6bdb\u5dee",
        "\u8d2d\u9500\u5dee\u4ef7",
    ),
    "connection_install": (
        "\u63a5\u9a73",
        "\u5b89\u88c5",
        "\u5de5\u7a0b\u5b89\u88c5",
        "\u5165\u6237\u5b89\u88c5",
        "\u71c3\u6c14\u5de5\u7a0b",
        "\u914d\u5957\u5b89\u88c5",
    ),
    "water_tariff": (
        "\u6c34\u4ef7",
        "\u6c61\u6c34\u5904\u7406\u8d39",
        "\u8c03\u4ef7",
        "\u4ef7\u683c\u8c03\u6574",
        "\u6c34\u4ef7\u6539\u9769",
        "\u4f9b\u6c34\u4ef7\u683c",
    ),
    "receivables_collection": (
        "\u5e94\u6536",
        "\u56de\u6b3e",
        "\u8d26\u9f84",
        "\u5730\u65b9\u8d22\u653f",
        "\u653f\u5e9c\u652f\u4ed8",
        "\u6c61\u6c34\u5904\u7406\u670d\u52a1\u8d39",
        "\u6536\u6b3e",
    ),
    "financing_debt": (
        "\u516c\u53f8\u503a",
        "\u53ef\u7eed\u671f",
        "\u878d\u8d44",
        "\u6388\u4fe1",
        "\u62c5\u4fdd",
        "\u5229\u7387",
        "\u8d22\u52a1\u8d39\u7528",
        "\u6709\u606f\u8d1f\u503a",
    ),
}


def collect_gas_water_true_operating_state_evidence(
    disclosure_csv: Path = DEFAULT_DISCLOSURE_CSV,
    panel_csv: Path = DEFAULT_PANEL_CSV,
    out_dir: Path = DEFAULT_OUT_DIR,
    *,
    sample_size: int | None = None,
    seed: int = 59,
    start_period: str | None = None,
    end_period: str | None = None,
    include_pdf_text: bool = True,
    cache_pdf: bool = False,
    max_pages: int = 120,
    request_timeout_seconds: float = 30.0,
    sleep_seconds: float = 0.2,
    searcher: Callable[..., list[dict[str, Any]]] | None = None,
    detail_fetcher: Callable[..., dict[str, Any]] | None = None,
    pdf_downloader: Callable[..., bytes] | None = None,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    text_cache_dir = out_dir / "text_cache"
    pdf_cache_dir = out_dir / "pdf_cache"
    text_cache_dir.mkdir(parents=True, exist_ok=True)
    if cache_pdf:
        pdf_cache_dir.mkdir(parents=True, exist_ok=True)

    code_tags = _business_tags(panel_csv)
    selected_codes = _select_codes(code_tags, sample_size=sample_size, seed=seed)
    disclosure_rows = _filter_disclosures(
        disclosure_csv,
        selected_codes=selected_codes,
        start_period=start_period,
        end_period=end_period,
    )
    searcher = searcher or _search_cninfo_reports
    detail_fetcher = detail_fetcher or _fetch_cninfo_bulletin_detail
    pdf_downloader = pdf_downloader or _download_pdf

    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for disclosure in disclosure_rows:
        code = disclosure.get("code", "")
        report_period = disclosure.get("report_period", "")
        report_type = disclosure.get("report_type", "")
        notice_date = disclosure.get("notice_date", "")
        try:
            candidates = searcher(
                code=code,
                report_type=report_type,
                notice_date=notice_date,
                timeout_seconds=request_timeout_seconds,
            )
            candidate = _select_report_candidate(candidates, report_type)
            if candidate is None:
                errors.append(_error_row(disclosure, "cninfo_search", "no strict annual/semiannual report matched"))
                continue
            detail = detail_fetcher(candidate, timeout_seconds=request_timeout_seconds)
            pdf_url = str(detail.get("fileUrl") or "")
            row = _base_output_row(disclosure, candidate, detail, code_tags.get(code, ""))
            text = ""
            pdf_bytes = b""
            if include_pdf_text and pdf_url:
                try:
                    pdf_bytes = pdf_downloader(pdf_url, timeout_seconds=request_timeout_seconds)
                    row["pdf_download_status"] = "downloaded"
                    row["pdf_size_bytes"] = len(pdf_bytes)
                    if cache_pdf:
                        _pdf_cache_path(pdf_cache_dir, code, report_period, candidate).write_bytes(pdf_bytes)
                    text, page_count = _extract_pdf_text(pdf_bytes, max_pages=max_pages)
                    row["page_count"] = page_count
                    row["extracted_text_length"] = len(text)
                    _text_cache_path(text_cache_dir, code, report_period, candidate).write_text(text, encoding="utf-8")
                    _apply_keyword_hits(row, text)
                    row["original_announcement_checked"] = "true"
                    row["pit_usable"] = "true"
                    row["review_status"] = "cninfo_pdf_keyword_candidate_manual_value_review_required"
                except Exception as exc:
                    row["pdf_download_status"] = "failed"
                    row["notes"] = f"PDF/text extraction failed: {type(exc).__name__}: {exc}"
                    row["review_status"] = "cninfo_index_only_pdf_extraction_failed"
                    errors.append(_error_row(disclosure, "pdf_extract", f"{type(exc).__name__}: {exc}"))
            rows.append(row)
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
        except Exception as exc:
            errors.append(_error_row(disclosure, "runner", f"{type(exc).__name__}: {exc}"))

    out_path = out_dir / "gas_water_true_operating_state_candidates.csv"
    error_path = out_dir / "gas_water_true_operating_state_errors.csv"
    write_csv_rows(out_path, TRUE_OPERATING_STATE_FIELDS, rows)
    write_csv_rows(error_path, ERROR_FIELDS, errors)
    hit_rows = [row for row in rows if row.get("hit_groups")]
    write_json_file(
        out_dir / "gas_water_true_operating_state_manifest.json",
        {
            "dataset": "gas_water_true_operating_state_candidates",
            "disclosure_csv": str(disclosure_csv),
            "panel_csv": str(panel_csv),
            "output": str(out_path),
            "error_output": str(error_path),
            "sample_size": sample_size,
            "seed": seed,
            "selected_code_count": len(selected_codes),
            "selected_codes": selected_codes,
            "requested_report_count": len(disclosure_rows),
            "row_count": len(rows),
            "hit_row_count": len(hit_rows),
            "error_count": len(errors),
            "include_pdf_text": include_pdf_text,
            "cache_pdf": cache_pdf,
            "max_pages": max_pages,
            "source_policy": "CNINFO/AkShare is used to locate public annual and semiannual report PDFs. Eastmoney remains a first-layer cross-check source only.",
            "pit_policy": "visible_date is the original announcement date from the disclosure calendar/CNINFO report row.",
            "review_policy": "Keyword snippets are research candidates only. Numeric values must be reviewed against original PDF text before entering Quant validation.",
            "created_at_utc": _now_utc(),
        },
    )
    return out_path


def build_gas_water_true_operating_state_panel(
    panel_csv: Path,
    evidence_csv: Path,
    out_dir: Path = DEFAULT_PANEL_OUT_DIR,
) -> Path:
    panel_rows = read_csv_rows(panel_csv)
    evidence_rows = read_csv_rows(evidence_csv)
    evidence_by_code: dict[str, list[dict[str, str]]] = {}
    for row in evidence_rows:
        if row.get("code") and row.get("visible_date") and row.get("original_announcement_checked") == "true":
            evidence_by_code.setdefault(row["code"], []).append(row)
    for rows in evidence_by_code.values():
        rows.sort(key=lambda item: (item.get("visible_date", ""), item.get("report_period", "")))

    enriched_rows: list[dict[str, Any]] = []
    covered_rows = 0
    covered_by_date: dict[str, int] = {}
    total_by_date: dict[str, int] = {}
    for row in panel_rows:
        item = dict(row)
        trade_date = str(row.get("trade_date") or "")[:10]
        code = str(row.get("code") or "")
        total_by_date[trade_date] = total_by_date.get(trade_date, 0) + 1
        latest = _latest_visible_evidence(evidence_by_code.get(code, []), trade_date)
        if latest:
            covered_rows += 1
            covered_by_date[trade_date] = covered_by_date.get(trade_date, 0) + 1
            item.update(_panel_evidence_fields(latest))
        else:
            item.update(_empty_panel_evidence_fields())
        enriched_rows.append(item)

    fieldnames = _merge_panel_fieldnames(panel_rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    panel_path = out_dir / "panel_with_true_operating_state.csv"
    write_csv_rows(panel_path, fieldnames, enriched_rows)
    coverage_by_date = {
        trade_date: {
            "row_count": total,
            "covered_rows": covered_by_date.get(trade_date, 0),
            "coverage_ratio": covered_by_date.get(trade_date, 0) / total if total else 0.0,
        }
        for trade_date, total in sorted(total_by_date.items())
    }
    min_date_coverage = min((item["coverage_ratio"] for item in coverage_by_date.values()), default=0.0)
    write_json_file(
        out_dir / "true_operating_state_panel_manifest.json",
        {
            "dataset": "gas_water_true_operating_state_panel_v59",
            "panel_csv": str(panel_csv),
            "evidence_csv": str(evidence_csv),
            "output": str(panel_path),
            "row_count": len(enriched_rows),
            "covered_rows": covered_rows,
            "coverage_ratio": covered_rows / len(enriched_rows) if enriched_rows else 0.0,
            "trade_date_count": len(coverage_by_date),
            "minimum_trade_date_coverage": min_date_coverage,
            "coverage_by_date": coverage_by_date,
            "status": "quant_validation_input_ready" if min_date_coverage >= 0.8 else "needs_more_report_history",
            "pit_policy": "For each stock and rebalance date, use only the latest CNINFO annual/semiannual report with visible_date <= trade_date.",
            "factor_policy": "Text-hit variables are diagnostic PIT candidates, not accepted operating metrics. Manual numeric extraction remains required before Engineering handoff.",
            "created_at_utc": _now_utc(),
        },
    )
    return panel_path


def _business_tags(panel_csv: Path) -> dict[str, str]:
    tags: dict[str, str] = {}
    for row in read_csv_rows(panel_csv):
        code = row.get("code", "")
        if code and code not in tags:
            tags[code] = row.get("approved_gas_water_business_tag", "")
    return tags


def _select_codes(tags: dict[str, str], *, sample_size: int | None, seed: int) -> list[str]:
    codes = sorted(tags)
    if sample_size is None or sample_size >= len(codes):
        return codes
    selected: list[str] = []
    by_tag: dict[str, list[str]] = {}
    for code, tag in tags.items():
        by_tag.setdefault(tag, []).append(code)
    for tag in ["core_gas_operator", "core_water_operator", "mixed_gas_water_operator"]:
        if by_tag.get(tag):
            selected.append(sorted(by_tag[tag])[0])
    remaining = [code for code in codes if code not in selected]
    random.Random(seed).shuffle(remaining)
    selected.extend(remaining[: max(0, sample_size - len(selected))])
    return sorted(selected[:sample_size])


def _filter_disclosures(
    disclosure_csv: Path,
    *,
    selected_codes: list[str],
    start_period: str | None,
    end_period: str | None,
) -> list[dict[str, str]]:
    selected = set(selected_codes)
    rows: list[dict[str, str]] = []
    for row in read_csv_rows(disclosure_csv):
        if row.get("code") not in selected:
            continue
        if row.get("report_type") not in {"annual", "semiannual"}:
            continue
        period = row.get("report_period", "")
        if start_period and period < start_period:
            continue
        if end_period and period > end_period:
            continue
        rows.append(row)
    return sorted(rows, key=lambda item: (item.get("code", ""), item.get("report_period", "")))


def _search_cninfo_reports(
    *,
    code: str,
    report_type: str,
    notice_date: str,
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    import akshare as ak

    notice = datetime.strptime(notice_date, "%Y-%m-%d")
    start_date = (notice - timedelta(days=25)).strftime("%Y%m%d")
    end_date = (notice + timedelta(days=25)).strftime("%Y%m%d")
    keyword = _ANNUAL_REPORT if report_type == "annual" else _SEMIANNUAL_REPORT
    category = _ANNUAL_CATEGORY if report_type == "annual" else _SEMIANNUAL_CATEGORY
    try:
        frame = ak.stock_zh_a_disclosure_report_cninfo(
            symbol=code[:6],
            market=_CNINFO_MARKET,
            keyword=keyword,
            category=category,
            start_date=start_date,
            end_date=end_date,
        )
    except KeyError:
        try:
            frame = ak.stock_zh_a_disclosure_report_cninfo(
                symbol=code[:6],
                market=_CNINFO_MARKET,
                keyword=keyword,
                category="",
                start_date=start_date,
                end_date=end_date,
            )
        except KeyError:
            return []
    rows = frame.to_dict("records") if hasattr(frame, "to_dict") else []
    return [dict(row) for row in rows]


def _select_report_candidate(candidates: list[dict[str, Any]], report_type: str) -> dict[str, Any] | None:
    target = _ANNUAL_REPORT if report_type == "annual" else _SEMIANNUAL_REPORT
    good = []
    for row in candidates:
        title = _clean_title(str(row.get("\u516c\u544a\u6807\u9898") or row.get("title") or ""))
        if target not in title:
            continue
        if any(term in title for term in _TITLE_EXCLUDE_TERMS):
            continue
        good.append((title, row))
    if not good:
        return None
    good.sort(key=lambda item: (len(item[0]), item[0]))
    return good[0][1]


def _fetch_cninfo_bulletin_detail(candidate: dict[str, Any], *, timeout_seconds: float) -> dict[str, Any]:
    import requests

    detail_url = str(candidate.get("\u516c\u544a\u94fe\u63a5") or candidate.get("url") or "")
    announcement_id = _announcement_id_from_url(detail_url)
    announcement_time = str(candidate.get("\u516c\u544a\u65f6\u95f4") or "")
    stock_code = str(candidate.get("\u4ee3\u7801") or "")
    flag = "true" if stock_code and stock_code[0] in {"0", "2", "3"} else "false"
    response = requests.post(
        "http://www.cninfo.com.cn/new/announcement/bulletin_detail",
        params={"announceId": announcement_id, "flag": flag, "announceTime": announcement_time},
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": detail_url or "http://www.cninfo.com.cn/",
            "X-Requested-With": "XMLHttpRequest",
        },
        timeout=(5, timeout_seconds),
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("fileUrl"):
        raise ValueError("CNINFO bulletin detail missing fileUrl")
    return payload


def _download_pdf(pdf_url: str, *, timeout_seconds: float) -> bytes:
    import requests

    response = requests.get(
        pdf_url,
        headers={"User-Agent": "Mozilla/5.0", "Referer": "http://www.cninfo.com.cn/"},
        timeout=(5, timeout_seconds),
    )
    response.raise_for_status()
    content = response.content
    if not content.startswith(b"%PDF"):
        raise ValueError("downloaded content is not a PDF")
    return content


def _extract_pdf_text(pdf_bytes: bytes, *, max_pages: int) -> tuple[str, int]:
    import fitz

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = len(doc)
    limit = min(page_count, max_pages)
    text = "\n".join(doc[page].get_text("text") for page in range(limit))
    return _normalize_text(text), page_count


def _base_output_row(
    disclosure: dict[str, str],
    candidate: dict[str, Any],
    detail: dict[str, Any],
    business_tag: str,
) -> dict[str, Any]:
    announcement = detail.get("announcement") or {}
    pdf_url = str(detail.get("fileUrl") or "")
    title = _clean_title(str(candidate.get("\u516c\u544a\u6807\u9898") or announcement.get("announcementTitle") or ""))
    announcement_date = str(candidate.get("\u516c\u544a\u65f6\u95f4") or disclosure.get("notice_date") or "")
    detail_url = str(candidate.get("\u516c\u544a\u94fe\u63a5") or "")
    return {
        "code": disclosure.get("code", ""),
        "company_name": str(candidate.get("\u7b80\u79f0") or announcement.get("secName") or ""),
        "business_tag": business_tag,
        "report_period": disclosure.get("report_period", ""),
        "report_type": disclosure.get("report_type", ""),
        "announcement_date": announcement_date,
        "visible_date": announcement_date,
        "title": title,
        "announcement_id": str(announcement.get("announcementId") or _announcement_id_from_url(detail_url)),
        "cninfo_detail_url": detail_url,
        "pdf_url": pdf_url,
        "pdf_download_status": "not_requested",
        "pdf_size_bytes": "",
        "page_count": "",
        "extracted_text_length": "",
        "hit_groups": "",
        "hit_terms": "",
        "gas_pass_through_snippet": "",
        "connection_install_snippet": "",
        "water_tariff_snippet": "",
        "receivables_collection_snippet": "",
        "financing_debt_snippet": "",
        "original_announcement_checked": "false",
        "pit_usable": "false",
        "review_status": "cninfo_index_only_pdf_text_not_extracted",
        "notes": "",
    }


def _apply_keyword_hits(row: dict[str, Any], text: str) -> None:
    hit_groups: list[str] = []
    hit_terms: list[str] = []
    for group, terms in KEYWORD_GROUPS.items():
        snippets: list[str] = []
        for term in terms:
            if term in text:
                hit_terms.append(f"{group}:{term}")
                snippets.append(_snippet(text, term))
        if snippets:
            hit_groups.append(group)
            row[f"{group}_snippet"] = " || ".join(snippets[:3])
    row["hit_groups"] = "|".join(hit_groups)
    row["hit_terms"] = "|".join(hit_terms)


def _latest_visible_evidence(rows: list[dict[str, str]], trade_date: str) -> dict[str, str] | None:
    latest = None
    for row in rows:
        if str(row.get("visible_date", ""))[:10] <= trade_date:
            latest = row
        else:
            break
    return latest


def _panel_evidence_fields(evidence: dict[str, str]) -> dict[str, Any]:
    text_length = _to_float(evidence.get("extracted_text_length")) or 0.0
    hit_terms = [item for item in str(evidence.get("hit_terms") or "").split("|") if item]
    result: dict[str, Any] = {
        "true_operating_state_available": 1,
        "true_operating_report_period": evidence.get("report_period", ""),
        "true_operating_visible_date": evidence.get("visible_date", ""),
        "true_operating_title": evidence.get("title", ""),
        "true_operating_pdf_url": evidence.get("pdf_url", ""),
        "true_operating_original_announcement_checked": evidence.get("original_announcement_checked", ""),
        "true_operating_review_status": evidence.get("review_status", ""),
        "true_operating_state_notes": "latest_visible_cninfo_pdf_keyword_candidate",
    }
    for group in KEYWORD_GROUPS:
        count = sum(1 for term in hit_terms if term.startswith(f"{group}:"))
        result[f"true_{group}_present"] = 1 if count else 0
        result[f"true_{group}_term_count"] = count
        result[f"true_{group}_density_per_10k"] = (count / text_length * 10000.0) if text_length > 0 else ""
    return result


def _empty_panel_evidence_fields() -> dict[str, Any]:
    result: dict[str, Any] = {
        "true_operating_state_available": 0,
        "true_operating_report_period": "",
        "true_operating_visible_date": "",
        "true_operating_title": "",
        "true_operating_pdf_url": "",
        "true_operating_original_announcement_checked": "false",
        "true_operating_review_status": "missing_latest_visible_cninfo_report",
        "true_operating_state_notes": "",
    }
    for group in KEYWORD_GROUPS:
        result[f"true_{group}_present"] = ""
        result[f"true_{group}_term_count"] = ""
        result[f"true_{group}_density_per_10k"] = ""
    return result


def _merge_panel_fieldnames(panel_rows: list[dict[str, str]]) -> list[str]:
    names: list[str] = []
    for row in panel_rows:
        for key in row:
            if key not in names:
                names.append(key)
    for key in PANEL_EXTRA_FIELDS:
        if key not in names:
            names.append(key)
    return names


def _to_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _announcement_id_from_url(url: str) -> str:
    query = parse_qs(urlparse(url).query)
    return (query.get("announcementId") or [""])[0]


def _clean_title(title: str) -> str:
    return re.sub(r"<[^>]+>", "", title).strip()


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _snippet(text: str, term: str, radius: int = 140) -> str:
    index = text.find(term)
    if index < 0:
        return ""
    return text[max(0, index - radius) : index + len(term) + radius]


def _text_cache_path(cache_dir: Path, code: str, report_period: str, candidate: dict[str, Any]) -> Path:
    announcement_id = _announcement_id_from_url(str(candidate.get("\u516c\u544a\u94fe\u63a5") or "")) or "unknown"
    return cache_dir / f"{code.replace('.', '_')}_{report_period}_{announcement_id}.txt"


def _pdf_cache_path(cache_dir: Path, code: str, report_period: str, candidate: dict[str, Any]) -> Path:
    announcement_id = _announcement_id_from_url(str(candidate.get("\u516c\u544a\u94fe\u63a5") or "")) or "unknown"
    return cache_dir / f"{code.replace('.', '_')}_{report_period}_{announcement_id}.pdf"


def _error_row(disclosure: dict[str, str], stage: str, error: str) -> dict[str, str]:
    return {
        "code": disclosure.get("code", ""),
        "report_period": disclosure.get("report_period", ""),
        "report_type": disclosure.get("report_type", ""),
        "notice_date": disclosure.get("notice_date", ""),
        "stage": stage,
        "error": error,
    }


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

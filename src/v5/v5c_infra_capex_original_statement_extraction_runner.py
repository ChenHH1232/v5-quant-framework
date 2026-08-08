from __future__ import annotations

import argparse
import csv
import json
import math
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path("v5c_infra_capex_original_statement_extraction") / "current"
SPEC_DIR = Path("v5c_infra_ocf_quality_fixed_rule_quant_spec") / "current"
SIDECAR_DIR = Path("v5c_sidecar_observation_enhancement") / "current"
CYCLE_DIR = Path("v5c_cycle_sector_data_gate_queue") / "current"

INPUT_DIR = Path("v5c_core_infra_cashflow_field_repair") / "current"
STRICT_INPUT = INPUT_DIR / "v5c_core_infra_cashflow_enriched_strict_panel.csv"
PROXY_INPUT = INPUT_DIR / "v5c_core_infra_cashflow_enriched_proxy_panel.csv"
FACTOR_PREVIEW_INPUT = INPUT_DIR / "v5c_core_infra_cashflow_factor_preview.csv"

DATABASE_DIR = Path("\u6570\u636e\u5e93")
CNINFO_SEARCH_URL = "http://www.cninfo.com.cn/new/information/topSearch/query"
CNINFO_ANNOUNCE_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_STATIC_BASE = "http://static.cninfo.com.cn/"

TRAIN_START = "2013-01-01"
TRAIN_END = "2021-04-30"
FORMAL_START = "2021-05-01"
FORMAL_END = "2026-05-31"

CFO_TERM = "\u7ecf\u8425\u6d3b\u52a8\u4ea7\u751f\u7684\u73b0\u91d1\u6d41\u91cf\u51c0\u989d"
CAPEX_TERM = "\u8d2d\u5efa\u56fa\u5b9a\u8d44\u4ea7\u3001\u65e0\u5f62\u8d44\u4ea7\u548c\u5176\u4ed6\u957f\u671f\u8d44\u4ea7\u652f\u4ed8\u7684\u73b0\u91d1"
CAPEX_TERM_ALT = "\u8d2d\u5efa\u56fa\u5b9a\u8d44\u4ea7\u3001\u65e0\u5f62\u8d44\u4ea7\u548c\u5176\u4ed6\u957f\u671f\u8d44\u4ea7\u6240\u652f\u4ed8\u7684\u73b0\u91d1"
CAPEX_TERM_SHORT = "\u8d2d\u5efa\u56fa\u5b9a\u8d44\u4ea7"
CASHFLOW_TABLE_TERMS = [
    "\u5408\u5e76\u73b0\u91d1\u6d41\u91cf\u8868",
    "\u73b0\u91d1\u6d41\u91cf\u8868",
    "\u73b0\u91d1\u6d41\u91cf",
]


@dataclass(frozen=True)
class InfraCapexConfig:
    request_timeout_seconds: int = 20
    sleep_seconds: float = 0.08
    max_codes: int | None = None
    max_reports: int | None = None
    download_missing: bool = True
    reuse_cached_manifest: bool = True
    reuse_cached_downloads: bool = True
    reuse_cached_extraction: bool = False


def run_v5c_infra_capex_original_statement_extraction(
    root: Path = ROOT,
    config: InfraCapexConfig | None = None,
) -> dict[str, Any]:
    config = config or InfraCapexConfig()
    out = root / OUT_DIR
    spec_out = root / SPEC_DIR
    sidecar_out = root / SIDECAR_DIR
    cycle_out = root / CYCLE_DIR
    for path in [out, spec_out, sidecar_out, cycle_out]:
        path.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        summary = _summary(
            status="blocked_missing_required_inputs",
            strict_rows=0,
            strict_capex_coverage=0.0,
            strict_fcf_coverage=0.0,
            manifest_rows=0,
            extracted_reports=0,
            blockers=blockers,
        )
        _write_blocked_outputs(out, summary, blockers)
        return summary

    strict_rows = _read_csv(root / STRICT_INPUT)
    proxy_rows = _read_csv(root / PROXY_INPUT)
    all_rows = [dict(row, scope="strict_pit_universe") for row in strict_rows] + [
        dict(row, scope="price_universe_proxy_not_validation") for row in proxy_rows
    ]
    requirements = _report_requirements(all_rows)
    codes = sorted({row["code"] for row in requirements})
    if config.max_codes is not None:
        keep = set(codes[: config.max_codes])
        requirements = [row for row in requirements if row["code"] in keep]
        codes = sorted(keep)

    manifest_path = out / "v5c_infra_capex_cninfo_manifest.csv"
    if config.reuse_cached_manifest and manifest_path.exists():
        cninfo_manifest = _read_csv(manifest_path)
        manifest_blockers: list[dict[str, Any]] = []
    else:
        cninfo_manifest, manifest_blockers = _build_cninfo_manifest(codes, config)
        _write_csv(manifest_path, cninfo_manifest)
    blockers.extend(manifest_blockers)

    local_inventory = _local_pdf_inventory(root, requirements)
    source_plan = _resolve_report_sources(requirements, local_inventory, cninfo_manifest)
    if config.max_reports is not None:
        source_plan = source_plan[: config.max_reports]

    download_path = out / "v5c_infra_capex_download_audit.csv"
    if config.reuse_cached_downloads and download_path.exists():
        download_audit = _read_csv(download_path)
        download_blockers = []
    else:
        download_audit, download_blockers = _download_or_resolve(source_plan, out / "pdf", config)
        _write_csv(download_path, download_audit)
    blockers.extend(download_blockers)

    extraction_path = out / "v5c_infra_capex_extraction_candidates.csv"
    if config.reuse_cached_extraction and extraction_path.exists():
        extraction_rows = _read_csv(extraction_path)
        extraction_blockers = []
    else:
        extraction_rows, extraction_blockers = _extract_capex_reports(download_audit)
        _write_csv(extraction_path, extraction_rows)
    blockers.extend(extraction_blockers)

    strict_panel = _apply_capex_panel(strict_rows, extraction_rows, "strict_pit_universe")
    proxy_panel = _apply_capex_panel(proxy_rows, extraction_rows, "price_universe_proxy_not_validation")
    coverage = _field_coverage(strict_panel + proxy_panel)
    pit_audit = _pit_audit(strict_panel + proxy_panel)
    factor_preview = _capex_factor_preview(strict_panel)
    blockers_out = _blockers(blockers, coverage, pit_audit, source_plan, extraction_rows)
    next_queue = _next_queue(coverage, blockers_out)

    strict_capex_coverage = _coverage_ratio(coverage, "strict_pit_universe", "capex_burden")
    strict_fcf_coverage = _coverage_ratio(coverage, "strict_pit_universe", "free_cash_flow_yield")
    status = (
        "completed_original_statement_capex_fcf_pass"
        if strict_capex_coverage >= 0.95 and strict_fcf_coverage >= 0.95
        else "completed_original_statement_capex_fcf_partial"
        if strict_capex_coverage > 0
        else "blocked_original_statement_capex_fcf_unavailable"
    )
    summary = _summary(
        status=status,
        strict_rows=len(strict_panel),
        strict_capex_coverage=strict_capex_coverage,
        strict_fcf_coverage=strict_fcf_coverage,
        manifest_rows=len(cninfo_manifest),
        extracted_reports=sum(1 for row in extraction_rows if row.get("extraction_status") == "pass_original_statement_extracted"),
        blockers=blockers_out,
    )

    _write_json(out / "v5c_infra_capex_original_statement_summary.json", summary)
    _write_csv(out / "v5c_infra_capex_source_pdf_inventory.csv", local_inventory)
    _write_csv(out / "v5c_infra_capex_source_plan.csv", source_plan)
    _write_csv(out / "v5c_infra_capex_strict_panel.csv", strict_panel)
    _write_csv(out / "v5c_infra_capex_proxy_panel.csv", proxy_panel)
    _write_csv(out / "v5c_infra_capex_field_coverage.csv", coverage)
    _write_csv(out / "v5c_infra_capex_pit_coverage_audit.csv", pit_audit)
    _write_csv(out / "v5c_infra_capex_factor_preview.csv", factor_preview)
    _write_csv(out / "v5c_infra_capex_blockers.csv", blockers_out)
    _write_csv(out / "v5c_infra_capex_next_queue.csv", next_queue)
    (out / "v5c_infra_capex_original_statement_report.md").write_text(
        _capex_report(summary, coverage, factor_preview, blockers_out, next_queue),
        encoding="utf-8",
    )
    (out / "v5c_infra_capex_agent_execution_rules.md").write_text(_capex_rules(), encoding="utf-8")

    _write_ocf_quality_spec(root, spec_out, factor_preview, coverage)
    _write_sidecar_packet(sidecar_out)
    _write_cycle_packet(cycle_out)
    return summary


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [STRICT_INPUT, PROXY_INPUT, FACTOR_PREVIEW_INPUT]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "scope": "infra_capex_original_statement_extraction",
            "path": str(path),
            "required_action": "restore v5c_core_infra_cashflow_field_repair/current outputs",
        }
        for path in required
        if not (root / path).exists()
    ]


def _report_requirements(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        code = str(row.get("code", "")).strip()
        report_period = str(row.get("cashflow_report_period", "")).strip()[:10]
        if not code or not report_period:
            continue
        key = (code, report_period)
        item = grouped.setdefault(
            key,
            {
                "code": code,
                "cn_code": code.split(".")[0],
                "exchange": code.split(".")[1] if "." in code else "",
                "report_period": report_period,
                "sector_ids": set(),
                "scopes": set(),
                "trade_dates": set(),
                "panel_visible_dates": set(),
            },
        )
        item["sector_ids"].add(row.get("sector_id", ""))
        item["scopes"].add(row.get("scope", ""))
        item["trade_dates"].add(str(row.get("trade_date", ""))[:10])
        if row.get("cashflow_factor_visible_date"):
            item["panel_visible_dates"].add(str(row.get("cashflow_factor_visible_date", ""))[:10])
    out = []
    for item in grouped.values():
        out.append(
            {
                "code": item["code"],
                "cn_code": item["cn_code"],
                "exchange": item["exchange"],
                "report_period": item["report_period"],
                "sector_ids": ";".join(sorted(x for x in item["sector_ids"] if x)),
                "scopes": ";".join(sorted(x for x in item["scopes"] if x)),
                "trade_dates": ";".join(sorted(x for x in item["trade_dates"] if x)),
                "panel_visible_dates": ";".join(sorted(x for x in item["panel_visible_dates"] if x)),
            }
        )
    return sorted(out, key=lambda row: (row["code"], row["report_period"]))


def _local_pdf_inventory(root: Path, requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base = root / DATABASE_DIR / "processed"
    if not base.exists():
        return []
    wanted = {(row["code"].replace(".", "_"), row["report_period"]) for row in requirements}
    inventory = []
    for path in base.rglob("*.pdf"):
        name = path.name
        for code_token, report_period in wanted:
            if code_token in name and report_period in name:
                inventory.append(
                    {
                        "code": code_token.replace("_XSHG", ".XSHG").replace("_XSHE", ".XSHE"),
                        "report_period": report_period,
                        "local_pdf_path": str(path),
                        "local_pdf_size": path.stat().st_size,
                        "inventory_source": "local_database_processed_recursive",
                    }
                )
                break
    return sorted(inventory, key=lambda row: (row["code"], row["report_period"], row["local_pdf_path"]))


def _build_cninfo_manifest(codes: list[str], config: InfraCapexConfig) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search",
    }
    rows: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for code in codes:
        cn_code = code.split(".")[0]
        exchange = code.split(".")[1] if "." in code else ""
        try:
            org = _query_org_id(session, headers, cn_code, config.request_timeout_seconds)
            if not org.get("org_id"):
                blockers.append(_nonfatal("cninfo_org_id_missing", code, "", "No CNInfo org_id returned."))
            else:
                rows.extend(_query_reports(session, headers, code, cn_code, exchange, org, config.request_timeout_seconds))
        except Exception as exc:  # noqa: BLE001
            blockers.append(_nonfatal("cninfo_manifest_query_error", code, "", f"{type(exc).__name__}: {exc}"))
        time.sleep(config.sleep_seconds)
    return _dedup_manifest(rows), blockers


def _query_org_id(session: requests.Session, headers: dict[str, str], cn_code: str, timeout: int) -> dict[str, str]:
    response = session.post(CNINFO_SEARCH_URL, headers=headers, data={"keyWord": cn_code, "maxNum": 10}, timeout=timeout)
    response.raise_for_status()
    for item in response.json():
        if str(item.get("code")) == cn_code and item.get("orgId"):
            return {
                "org_id": str(item.get("orgId") or ""),
                "sec_name": str(item.get("zwjc") or ""),
                "market_type": str(item.get("type") or ""),
            }
    return {"org_id": "", "sec_name": "", "market_type": ""}


def _query_reports(
    session: requests.Session,
    headers: dict[str, str],
    code: str,
    cn_code: str,
    exchange: str,
    org: dict[str, str],
    timeout: int,
) -> list[dict[str, Any]]:
    column = "szse" if exchange == "XSHE" else "sse"
    response = session.post(
        CNINFO_ANNOUNCE_URL,
        headers=headers,
        data={
            "pageNum": 1,
            "pageSize": 50,
            "column": column,
            "tabName": "fulltext",
            "plate": "",
            "stock": f"{cn_code},{org['org_id']}",
            "searchkey": "",
            "secid": "",
            "category": "category_ndbg_szsh;category_bndbg_szsh;category_yjdbg_szsh;category_sjdbg_szsh;",
            "trade": "",
            "seDate": "2018-01-01~2021-04-30",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    rows: list[dict[str, Any]] = []
    for announcement in response.json().get("announcements") or []:
        title = _clean_html(str(announcement.get("announcementTitle") or ""))
        if not _is_usable_financial_report_title(title):
            continue
        report_period = _infer_report_period(title)
        if not report_period or report_period < "2018-01-01" or report_period > "2020-12-31":
            continue
        adjunct = str(announcement.get("adjunctUrl") or "")
        rows.append(
            {
                "code": code,
                "cn_code": cn_code,
                "exchange": exchange,
                "sec_name": org.get("sec_name", ""),
                "org_id": org.get("org_id", ""),
                "announcement_title": title,
                "announcement_date_utc": _ms_to_date(announcement.get("announcementTime")),
                "pit_visible_date": _visible_date_from_adjunct(adjunct) or _ms_to_date(announcement.get("announcementTime")),
                "report_period": report_period,
                "report_type": _report_type(report_period),
                "adjunct_url": adjunct,
                "pdf_url": CNINFO_STATIC_BASE + adjunct if adjunct else "",
                "source": "cninfo_hisAnnouncement_financial_report",
                "accepted": False,
            }
        )
    return rows


def _dedup_manifest(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    preferred: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["code"], row["report_period"])
        current = preferred.get(key)
        if current is None or _manifest_preference(row) > _manifest_preference(current):
            preferred[key] = row
    return sorted(preferred.values(), key=lambda row: (row["code"], row["report_period"], row["pit_visible_date"]))


def _manifest_preference(row: dict[str, Any]) -> tuple[int, str]:
    title = str(row.get("announcement_title", ""))
    score = 0
    if "\u5168\u6587" in title:
        score += 3
    if "\u5e74\u5ea6\u62a5\u544a" in title or "\u534a\u5e74\u5ea6\u62a5\u544a" in title:
        score += 2
    if "\u66f4\u65b0\u540e" in title:
        score += 1
    return score, str(row.get("pit_visible_date", ""))


def _resolve_report_sources(
    requirements: list[dict[str, Any]],
    local_inventory: list[dict[str, Any]],
    manifest: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    local_by_key = defaultdict(list)
    for row in local_inventory:
        local_by_key[(row["code"], row["report_period"])].append(row)
    manifest_by_key = {(row["code"], row["report_period"]): row for row in manifest}
    sources = []
    for req in requirements:
        key = (req["code"], req["report_period"])
        cn = manifest_by_key.get(key, {})
        local = local_by_key.get(key, [])
        local_path = local[0]["local_pdf_path"] if local else ""
        pit_visible_date = str(cn.get("pit_visible_date") or _first_date(req.get("panel_visible_dates", "")) or "")
        sources.append(
            {
                **req,
                "sec_name": cn.get("sec_name", ""),
                "announcement_title": cn.get("announcement_title", ""),
                "pit_visible_date": pit_visible_date,
                "pdf_url": cn.get("pdf_url", ""),
                "local_pdf_path": local_path,
                "source_resolution_status": "local_pdf_available" if local_path else ("cninfo_pdf_available" if cn.get("pdf_url") else "missing_pdf_source"),
                "source": "local_pdf_plus_cninfo_manifest" if local_path and cn else ("local_pdf_panel_visible_date" if local_path else ("cninfo_manifest" if cn else "")),
            }
        )
    return sources


def _download_or_resolve(
    source_plan: list[dict[str, Any]],
    pdf_dir: Path,
    config: InfraCapexConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pdf_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "http://www.cninfo.com.cn/"}
    rows: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for row in source_plan:
        local_text = str(row.get("local_pdf_path") or "").strip()
        local_path = Path(local_text) if local_text else Path()
        status = "not_attempted"
        byte_count = 0
        error = ""
        if local_text and local_path.is_file() and local_path.stat().st_size > 1024:
            status = "local"
            byte_count = local_path.stat().st_size
        else:
            local_path = pdf_dir / f"{row['code'].replace('.', '_')}_{row['report_period']}_financial_report.pdf"
            if local_path.is_file() and local_path.stat().st_size > 1024:
                status = "cached_download"
                byte_count = local_path.stat().st_size
            elif not config.download_missing:
                status = "missing_download_disabled"
            elif row.get("pdf_url"):
                try:
                    response = session.get(str(row["pdf_url"]), headers=headers, timeout=config.request_timeout_seconds)
                    response.raise_for_status()
                    local_path.write_bytes(response.content)
                    status = "downloaded"
                    byte_count = len(response.content)
                except Exception as exc:  # noqa: BLE001
                    status = f"download_error:{type(exc).__name__}"
                    error = str(exc)
                    blockers.append(_nonfatal("financial_report_download_error", row.get("code", ""), row.get("report_period", ""), f"{type(exc).__name__}: {exc}"))
            else:
                status = "missing_pdf_url"
        rows.append({**row, "resolved_pdf_path": str(local_path), "download_status": status, "byte_count": byte_count, "error": error})
        time.sleep(config.sleep_seconds)
    return rows, blockers


def _extract_capex_reports(download_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = []
    blockers = []
    cache: dict[str, dict[str, Any]] = {}
    for row in download_rows:
        path_text = str(row.get("resolved_pdf_path", "")).strip()
        path = Path(path_text) if path_text else Path()
        if not path_text or not path.is_file() or not str(row.get("download_status", "")).startswith(("local", "cached", "downloaded")):
            rows.append(_extraction_row(row, {}, "pdf_unavailable"))
            blockers.append(_nonfatal("financial_report_pdf_unavailable", row.get("code", ""), row.get("report_period", ""), str(row.get("download_status", ""))))
            continue
        try:
            extracted = cache.get(str(path))
            if extracted is None:
                extracted = _extract_cashflow_values_from_pdf(path)
                cache[str(path)] = extracted
        except Exception as exc:  # noqa: BLE001
            rows.append(_extraction_row(row, {}, f"pdf_read_error:{type(exc).__name__}"))
            blockers.append(_nonfatal("financial_report_pdf_read_error", row.get("code", ""), row.get("report_period", ""), f"{type(exc).__name__}: {exc}"))
            continue
        status = "pass_original_statement_extracted" if extracted.get("capex_cash_paid") is not None and extracted.get("operating_cash_flow_net") is not None else "needs_original_review"
        rows.append(_extraction_row(row, extracted, status))
    return rows, blockers


def _extract_cashflow_values_from_pdf(path: Path) -> dict[str, Any]:
    try:
        import fitz  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"PyMuPDF unavailable: {exc}") from exc

    best: dict[str, Any] | None = None
    with fitz.open(str(path)) as doc:
        for page_index in range(len(doc)):
            text = doc.load_page(page_index).get_text("text") or ""
            if CAPEX_TERM_SHORT not in text and not _fuzzy_find(text, CAPEX_TERM_SHORT):
                continue
            capex = _parse_value_after_term(text, CAPEX_TERM) or _parse_value_after_term(text, CAPEX_TERM_ALT) or _parse_value_after_term(text, CAPEX_TERM_SHORT)
            cfo = _parse_value_after_term(text, CFO_TERM)
            if cfo is None:
                for near in [page_index - 1, page_index + 1]:
                    if 0 <= near < len(doc):
                        cfo = _parse_value_after_term(doc.load_page(near).get_text("text") or "", CFO_TERM)
                        if cfo is not None:
                            break
            if cfo is None:
                # Quarterly cash-flow tables can split the two rows across pages.
                for near in range(len(doc)):
                    cfo = _parse_value_after_term(doc.load_page(near).get_text("text") or "", CFO_TERM)
                    if cfo is not None:
                        break
            unit, multiplier = _unit_multiplier(text)
            candidate = {
                "operating_cash_flow_net": cfo * multiplier if cfo is not None else None,
                "capex_cash_paid": abs(capex * multiplier) if capex is not None else None,
                "unit": unit,
                "unit_multiplier": multiplier,
                "page_number": page_index + 1,
                "parse_rule": "cash_flow_statement_preferred_page_first_numeric_value_after_term",
                "sample_context": _sample_context(text, CAPEX_TERM_SHORT),
                "_score": _cashflow_page_score(text, cfo, capex),
            }
            if best is None or float(candidate["_score"]) > float(best["_score"]):
                best = candidate
        if best and best.get("capex_cash_paid") is not None and best.get("operating_cash_flow_net") is not None:
            best.pop("_score", None)
            return best
    return {
        "operating_cash_flow_net": None,
        "capex_cash_paid": None,
        "unit": "",
        "unit_multiplier": "",
        "page_number": "",
        "parse_rule": "not_found",
        "sample_context": "",
    }


def _cashflow_page_score(text: str, cfo: float | None, capex: float | None) -> float:
    score = 0.0
    if capex is not None:
        score += 2.0
    if cfo is not None:
        score += 6.0
    if "\u5408\u5e76\u73b0\u91d1\u6d41\u91cf\u8868" in text:
        score += 5.0
    if "\u6bcd\u516c\u53f8\u73b0\u91d1\u6d41\u91cf\u8868" in text:
        score += 2.0
    if "\u9879\u76ee" in text and ("\u672c\u671f\u53d1\u751f\u989d" in text or "\u672c\u671f\u91d1\u989d" in text):
        score += 3.0
    if "\u73b0\u91d1\u6d41\u91cf\u8868\u4e3b\u8981\u9879\u76ee\u8bf4\u660e" in text or "\u540c\u6bd4\u589e\u52a0" in text or "\u589e\u5e45" in text:
        score -= 6.0
    return score


def _parse_value_after_term(text: str, term: str) -> float | None:
    match = _fuzzy_find(text, term)
    if not match:
        return None
    tail = text[match.end() : match.end() + 700]
    numbers = re.findall(r"[\(\uff08-]?\d[\d,]*(?:\.\d+)?[\)\uff09]?", tail)
    for token in numbers:
        value = _number_value(token)
        if value is not None:
            return value
    return None


def _fuzzy_find(text: str, term: str) -> re.Match[str] | None:
    pattern = r"\s*".join(re.escape(ch) for ch in term)
    return re.search(pattern, text)


def _unit_multiplier(text: str) -> tuple[str, float]:
    head = text[:1200]
    if "\u5355\u4f4d\uff1a\u767e\u4e07\u5143" in head or "\u5355\u4f4d:\u767e\u4e07\u5143" in head:
        return "million_cny", 1_000_000.0
    if "\u5355\u4f4d\uff1a\u4e07\u5143" in head or "\u5355\u4f4d:\u4e07\u5143" in head:
        return "ten_thousand_cny", 10_000.0
    if "\u5355\u4f4d\uff1a\u5343\u5143" in head or "\u5355\u4f4d:\u5343\u5143" in head:
        return "thousand_cny", 1_000.0
    return "cny", 1.0


def _sample_context(text: str, term: str, window: int = 360) -> str:
    match = _fuzzy_find(text, term)
    if not match:
        return ""
    start = max(0, match.start() - window)
    end = min(len(text), match.end() + window)
    return re.sub(r"\s+", " ", text[start:end]).strip()[:900]


def _extraction_row(row: dict[str, Any], extracted: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "code": row.get("code", ""),
        "sector_ids": row.get("sector_ids", ""),
        "report_period": row.get("report_period", ""),
        "pit_visible_date": row.get("pit_visible_date", ""),
        "announcement_title": row.get("announcement_title", ""),
        "operating_cash_flow_net_original": _fmt(extracted.get("operating_cash_flow_net")),
        "capex_cash_paid_original": _fmt(extracted.get("capex_cash_paid")),
        "unit": extracted.get("unit", ""),
        "unit_multiplier": extracted.get("unit_multiplier", ""),
        "source_page_number": extracted.get("page_number", ""),
        "parse_rule": extracted.get("parse_rule", ""),
        "sample_context": extracted.get("sample_context", ""),
        "local_pdf_path": row.get("resolved_pdf_path", ""),
        "download_status": row.get("download_status", ""),
        "extraction_status": status,
        "pit_source": "cninfo_or_local_original_financial_report_pdf",
        "accepted": False,
    }


def _apply_capex_panel(panel_rows: list[dict[str, Any]], extraction_rows: list[dict[str, Any]], scope: str) -> list[dict[str, Any]]:
    by_key = defaultdict(list)
    for item in extraction_rows:
        by_key[(item.get("code", ""), item.get("report_period", ""))].append(item)
    out = []
    for row in panel_rows:
        item = dict(row)
        item["scope"] = scope
        code = item.get("code", "")
        report_period = str(item.get("cashflow_report_period", ""))[:10]
        trade_date = str(item.get("trade_date", ""))[:10]
        candidates = [
            cand
            for cand in by_key.get((code, report_period), [])
            if cand.get("extraction_status") == "pass_original_statement_extracted"
            and str(cand.get("pit_visible_date", ""))[:10] <= trade_date
        ]
        candidates.sort(key=lambda cand: str(cand.get("pit_visible_date", "")))
        if candidates:
            match = candidates[-1]
            cfo = _to_float(match.get("operating_cash_flow_net_original"))
            capex = _to_float(match.get("capex_cash_paid_original"))
            ocf_yield = _to_float(item.get("operating_cash_flow_yield"))
            capex_burden = abs(capex) / cfo if cfo and cfo > 0 and capex is not None else None
            fcf_yield = ocf_yield * ((cfo - abs(capex or 0.0)) / cfo) if ocf_yield is not None and cfo and cfo > 0 and capex is not None else None
            item.update(
                {
                    "operating_cash_flow_net_original": _fmt(cfo),
                    "capex_cash_paid_original": _fmt(capex),
                    "capex_burden": _fmt(capex_burden),
                    "free_cash_flow_yield": _fmt(fcf_yield),
                    "free_cash_flow_yield_source": "original_cfo_and_capex_scaled_by_existing_pit_ocf_yield" if fcf_yield is not None else "source_blocked_missing_ocf_yield_or_nonpositive_cfo",
                    "capex_original_visible_date": match.get("pit_visible_date", ""),
                    "capex_original_report_period": match.get("report_period", ""),
                    "capex_source_page_number": match.get("source_page_number", ""),
                    "capex_source_unit": match.get("unit", ""),
                    "capex_source_pdf": match.get("local_pdf_path", ""),
                    "capex_fcf_status": "pass_pit_original_statement_extracted" if capex_burden is not None or fcf_yield is not None else "partial_original_extracted_ratio_unavailable",
                }
            )
        else:
            item.update(
                {
                    "operating_cash_flow_net_original": "",
                    "capex_cash_paid_original": "",
                    "capex_burden": "",
                    "free_cash_flow_yield": "",
                    "free_cash_flow_yield_source": "",
                    "capex_original_visible_date": "",
                    "capex_original_report_period": report_period,
                    "capex_source_page_number": "",
                    "capex_source_unit": "",
                    "capex_source_pdf": "",
                    "capex_fcf_status": "missing_pit_original_statement_extraction",
                }
            )
        out.append(item)
    return out


def _field_coverage(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = ["capex_cash_paid_original", "operating_cash_flow_net_original", "capex_burden", "free_cash_flow_yield"]
    out = []
    for (sector_id, scope), group in _groupby(rows, lambda row: (row.get("sector_id", ""), row.get("scope", ""))).items():
        for field in fields:
            count = len(group)
            nonempty = sum(1 for row in group if _to_float(row.get(field)) is not None)
            ratio = nonempty / count if count else 0.0
            out.append(
                {
                    "sector_id": sector_id,
                    "scope": scope,
                    "field": field,
                    "row_count": count,
                    "nonempty_count": nonempty,
                    "coverage_ratio": _fmt(ratio),
                    "field_status": "pass" if ratio >= 0.95 else ("partial" if ratio > 0 else "missing"),
                    "source_status": "original_statement_pdf_extracted" if ratio > 0 else "source_blocked_or_needs_review",
                }
            )
    return out


def _pit_audit(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        trade_date = str(row.get("trade_date", ""))[:10]
        visible = str(row.get("capex_original_visible_date", ""))[:10]
        status = "missing_original_statement_match"
        if visible:
            status = "pass" if visible <= trade_date else "fail_visible_after_trade_date"
        out.append(
            {
                "scope": row.get("scope", ""),
                "sector_id": row.get("sector_id", ""),
                "trade_date": trade_date,
                "code": row.get("code", ""),
                "cashflow_report_period": row.get("cashflow_report_period", ""),
                "capex_original_visible_date": visible,
                "pit_status": status,
                "capex_fcf_status": row.get("capex_fcf_status", ""),
            }
        )
    return out


def _capex_factor_preview(strict_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    specs = [
        ("free_cash_flow_yield", "higher_better", "fcf_yield"),
        ("capex_burden", "lower_better", "capex_burden"),
    ]
    out = []
    for sector_id, sector_rows in _groupby(strict_rows, lambda row: row.get("sector_id", "")).items():
        for field, direction, family in specs:
            spreads = []
            for trade_date, day_rows in _groupby(sector_rows, lambda row: row.get("trade_date", "")).items():
                valid = [row for row in day_rows if _to_float(row.get(field)) is not None and _to_float(row.get("future_return")) is not None]
                if len(valid) < 4:
                    continue
                reverse = direction == "higher_better"
                valid.sort(key=lambda row: _to_float(row.get(field)) or 0.0, reverse=reverse)
                bucket = max(1, len(valid) // 3)
                top = valid[:bucket]
                bottom = valid[-bucket:]
                top_ret = _mean(_to_float(row.get("future_return")) for row in top)
                bottom_ret = _mean(_to_float(row.get("future_return")) for row in bottom)
                if top_ret is not None and bottom_ret is not None:
                    spreads.append(top_ret - bottom_ret)
            out.append(
                {
                    "sector_id": sector_id,
                    "factor_id": field,
                    "family": family,
                    "direction": direction,
                    "scope": "pre2021_train_test_only",
                    "period_count": len(spreads),
                    "avg_top_minus_bottom_return": _fmt(_mean(spreads)),
                    "positive_spread_rate": _fmt(sum(1 for value in spreads if value > 0) / len(spreads) if spreads else None),
                    "preview_status": _preview_status(spreads),
                    "formal_backtest_used_as_validation": False,
                    "accepted": False,
                }
            )
    return out


def _blockers(
    blockers: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    pit_audit: list[dict[str, Any]],
    source_plan: list[dict[str, Any]],
    extraction_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out = list(blockers)
    pit_fail = [row for row in pit_audit if row.get("pit_status") == "fail_visible_after_trade_date"]
    if pit_fail:
        out.append(
            {
                "blocker_id": "capex_pit_visible_date_failure",
                "severity": "fatal",
                "scope": "capex_original_statement",
                "detail": len(pit_fail),
                "required_action": "review CNInfo visible dates before using capex/FCF fields",
            }
        )
    for row in coverage:
        if row["scope"] == "strict_pit_universe" and row["field"] in {"capex_burden", "free_cash_flow_yield"} and row["field_status"] != "pass":
            out.append(
                {
                    "blocker_id": f"{row['sector_id']}_{row['field']}_coverage_partial",
                    "severity": "nonfatal",
                    "scope": row["sector_id"],
                    "detail": f"coverage={row['coverage_ratio']}",
                    "required_action": "manual original table review for missing or nonpositive-CFO rows before formal use",
                }
            )
    missing_sources = [row for row in source_plan if row.get("source_resolution_status") == "missing_pdf_source"]
    if missing_sources:
        out.append(
            {
                "blocker_id": "capex_pdf_source_missing",
                "severity": "nonfatal",
                "scope": "infra_capex",
                "detail": len(missing_sources),
                "required_action": "retry CNInfo manifest or provide original reports",
            }
        )
    needs_review = [row for row in extraction_rows if row.get("extraction_status") == "needs_original_review"]
    if needs_review:
        out.append(
            {
                "blocker_id": "capex_pdf_extraction_needs_original_review",
                "severity": "nonfatal",
                "scope": "infra_capex",
                "detail": len(needs_review),
                "required_action": "review page/table/unit for unmatched capex rows",
            }
        )
    return out or [{"blocker_id": "none", "severity": "none", "scope": "infra_capex", "detail": "completed", "required_action": ""}]


def _next_queue(coverage: list[dict[str, Any]], blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fatal = any(row.get("severity") == "fatal" for row in blockers)
    capex_ok = _coverage_ratio(coverage, "strict_pit_universe", "capex_burden") >= 0.75
    return [
        {
            "priority": "P1",
            "task_id": "v5c_infra_ocf_quality_fixed_rule_quant_spec",
            "status": "ready",
            "action": "use pre-2021 OCF quality evidence to define fixed highway rules; no formal backtest or acceptance",
            "allowed": "quant_spec_only",
        },
        {
            "priority": "P2",
            "task_id": "v5c_cross_sector_screen_rerun_after_capex",
            "status": "ready_for_spec_review" if capex_ok and not fatal else "waiting_manual_original_review",
            "action": "only after fixed rules are frozen, rerun pre-2021 screen; do not use 2021-2026 as discovery",
            "allowed": "pre2021_research_only",
        },
        {
            "priority": "S1",
            "task_id": "v5c_sidecar_observation_enhancement",
            "status": "generated",
            "action": "gas/water and telecom observation enhancement only",
            "allowed": "sidecar_observation_only",
        },
        {
            "priority": "C1",
            "task_id": "v5c_cycle_sector_data_gate_queue",
            "status": "generated",
            "action": "cycle sectors remain data-gate-only until state data are PIT-clean",
            "allowed": "data_gate_only_no_backtest",
        },
    ]


def _write_ocf_quality_spec(root: Path, out: Path, capex_preview: list[dict[str, Any]], capex_coverage: list[dict[str, Any]]) -> None:
    existing_preview = _read_csv(root / FACTOR_PREVIEW_INPUT)
    rule_spec = [
        {
            "rule_id": "highway_ocf_yield_quality_guard",
            "sector_id": "highway_infrastructure",
            "rule_type": "risk_cap_only",
            "allowed_use": "limit weak cash-flow names inside existing V57f/V5f highway sleeve",
            "fixed_fields": "operating_cash_flow_yield;operating_cash_flow_to_net_profit;ocf_to_revenue",
            "positive_support": "none",
            "risk_condition": "bottom_tercile_ocf_yield_or_ocf_to_net_profit_below_sector_median",
            "weight_action_spec": "cap relative overweight; do not create new buys; do not cross sleeve",
            "status": "admit_to_fixed_rule_quant_spec_not_engineering_backtest",
        },
        {
            "rule_id": "highway_fcf_capex_guard",
            "sector_id": "highway_infrastructure",
            "rule_type": "risk_cap_only_with_capex_data_gate",
            "allowed_use": "flag high capex burden and weak free cash flow once original-statement coverage is reviewed",
            "fixed_fields": "free_cash_flow_yield;capex_burden",
            "positive_support": "none_by_default",
            "risk_condition": "negative_fcf_yield_or_top_tercile_capex_burden",
            "weight_action_spec": "risk cap only until forward/PIT evidence improves",
            "status": "data_gate_dependent",
        },
        {
            "rule_id": "highway_cash_collection_support_tilt_5pct_spec",
            "sector_id": "highway_infrastructure",
            "rule_type": "support_tilt_small_fixed",
            "allowed_use": "optional later test only after risk_cap_only passes",
            "fixed_fields": "ocf_to_revenue;cash_collection_quality;operating_cash_flow_yield",
            "positive_support": "top_tercile_all_or_two_of_three_fields",
            "risk_condition": "bottom_tercile_two_or_more_fields",
            "weight_action_spec": "+5pct/-5pct relative tilt inside highway sleeve only",
            "status": "second_stage_spec_only",
        },
    ]
    field_mapping = [
        {"field": "operating_cash_flow_yield", "direction": "higher_better", "source": "BaoStock finance PIT row", "status": "available"},
        {"field": "operating_cash_flow_to_net_profit", "direction": "higher_better", "source": "BaoStock finance PIT row", "status": "available"},
        {"field": "ocf_to_revenue", "direction": "higher_better", "source": "BaoStock finance PIT row", "status": "available"},
        {"field": "cash_collection_quality", "direction": "higher_better", "source": "BaoStock finance PIT row", "status": "available"},
        {"field": "free_cash_flow_yield", "direction": "higher_better", "source": "original statement capex/CFO plus PIT OCF yield scale", "status": "data_gate_review"},
        {"field": "capex_burden", "direction": "lower_better", "source": "original statement capex/CFO", "status": "data_gate_review"},
    ]
    governance = [
        {"audit_id": "sample_split", "status": "pass", "detail": f"{TRAIN_START}_to_{TRAIN_END}_only_for_rule_discovery"},
        {"audit_id": "formal_backtest_not_used_for_discovery", "status": "pass", "detail": f"{FORMAL_START}_to_{FORMAL_END}_reserved"},
        {"audit_id": "v57f_core_modified", "status": "pass", "detail": False},
        {"audit_id": "v5f_primary_modified", "status": "pass", "detail": False},
        {"audit_id": "accepted", "status": "pass", "detail": False},
        {"audit_id": "parameter_scan_used", "status": "pass", "detail": False},
    ]
    decision = [
        {
            "pm_gate_decision": "admit_highway_ocf_quality_risk_cap_to_quant_spec_not_accepted",
            "cashflow_support_tilt_status": "second_stage_spec_only",
            "capex_fcf_status": "data_gate_review_required",
            "engineering_backtest_allowed_now": False,
            "accepted": False,
            "v57f_core_modified": False,
            "next_action": "freeze one fixed risk-cap rule before any limited engineering",
        }
    ]
    queue = [
        {"priority": "P1A", "task_id": "highway_ocf_yield_quality_guard_limited_engineering_spec_approval", "status": "ready_for_pm_review", "allowed": "spec_review_only"},
        {"priority": "P1B", "task_id": "highway_fcf_capex_guard_manual_review", "status": "ready_if_capex_coverage_partial", "allowed": "data_gate_review_only"},
        {"priority": "P1C", "task_id": "port_rail_interest_coverage_diagnostic", "status": "diagnostic_only", "allowed": "do_not_promote_without_stronger_pre2021_evidence"},
    ]
    blockers = [
        {
            "blocker_id": "no_engineering_backtest_approval",
            "severity": "governance",
            "detail": "This packet is a Quant spec boundary only.",
            "required_action": "separate approval for limited engineering",
        }
    ]
    summary = {
        "created_at_utc": now_utc(),
        "task": "v5c_infra_ocf_quality_fixed_rule_quant_spec",
        "status": "completed_quant_spec_only",
        "target_sector": "highway_infrastructure",
        "primary_rule": "highway_ocf_yield_quality_guard",
        "formal_backtest_used_as_validation": False,
        "v57f_core_modified": False,
        "v5f_primary_modified": False,
        "accepted": False,
        "live_trading_approved": False,
        "pm_gate_decision": decision[0]["pm_gate_decision"],
    }
    _write_json(out / "v5c_infra_ocf_quality_fixed_rule_spec_summary.json", summary)
    _write_csv(out / "v5c_infra_ocf_quality_rule_spec.csv", rule_spec)
    _write_csv(out / "v5c_infra_ocf_quality_field_mapping.csv", field_mapping)
    _write_csv(out / "v5c_infra_ocf_quality_pre2021_evidence_snapshot.csv", existing_preview + capex_preview)
    _write_csv(out / "v5c_infra_ocf_quality_capex_coverage_snapshot.csv", capex_coverage)
    _write_csv(out / "v5c_infra_ocf_quality_governance_audit.csv", governance)
    _write_csv(out / "v5c_infra_ocf_quality_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_infra_ocf_quality_next_queue.csv", queue)
    _write_csv(out / "v5c_infra_ocf_quality_blockers.csv", blockers)
    (out / "v5c_infra_ocf_quality_fixed_rule_spec_report.md").write_text(_ocf_spec_report(summary, rule_spec, decision), encoding="utf-8")
    (out / "v5c_infra_ocf_quality_agent_execution_rules.md").write_text(_spec_rules(), encoding="utf-8")


def _write_sidecar_packet(out: Path) -> None:
    rows = [
        {
            "sidecar_id": "gas_water_observation_enhancement",
            "sector_id": "gas_water_operators",
            "status": "sidecar_observation_only",
            "allowed_fields": "regulated_tariff_state;volume_growth;receivables_quality;ocf_quality;capex_burden",
            "allowed_action": "refresh observation cards and paper contribution attribution",
            "blocked_action": "V57f_core_entry;accepted;return_tuning_without_PIT_state_gate",
        },
        {
            "sidecar_id": "telecom_observation_enhancement",
            "sector_id": "telecom_operators",
            "status": "capped_specialist_sidecar_observation_only",
            "allowed_fields": "capex_cycle;mobile_arpu;cloud_growth;dividend_sustainability;ocf_quality",
            "allowed_action": "specialist observation and capped policy review only",
            "blocked_action": "ordinary_cross_section_core_promotion;accepted",
        },
    ]
    summary = {
        "created_at_utc": now_utc(),
        "task": "v5c_sidecar_observation_enhancement",
        "status": "completed_sidecar_queue_only",
        "sectors": ["gas_water_operators", "telecom_operators"],
        "v57f_core_modified": False,
        "accepted": False,
    }
    _write_json(out / "v5c_sidecar_observation_summary.json", summary)
    _write_csv(out / "v5c_sidecar_observation_enhancement_queue.csv", rows)
    _write_csv(
        out / "v5c_sidecar_observation_pm_gate_decision.csv",
        [
            {
                "pm_gate_decision": "sidecar_observation_only_not_core",
                "gas_water_status": "observation_enhancement_ready",
                "telecom_status": "capped_specialist_observation_ready",
                "accepted": False,
                "v57f_core_modified": False,
            }
        ],
    )
    (out / "v5c_sidecar_observation_report.md").write_text(
        "# V5c Sidecar Observation Enhancement\n\nGas/water and telecom remain sidecar observation only. No V57f core entry, no accepted status, and no return tuning is authorized by this packet.\n",
        encoding="utf-8",
    )


def _write_cycle_packet(out: Path) -> None:
    rows = [
        {
            "sector_id": "oil_gas",
            "status": "cycle_data_gate_only",
            "required_state_data": "oil_price;gas_price;refining_spread;reserve_or_production;capex_cycle;inventory",
            "blocked_action": "backtest_before_PIT_state_gate",
        },
        {
            "sector_id": "chemical_materials",
            "status": "cycle_data_gate_only",
            "required_state_data": "product_spread;inventory;capacity_utilization;capex_cycle;demand_proxy",
            "blocked_action": "backtest_before_PIT_state_gate",
        },
        {
            "sector_id": "nonferrous_metals",
            "status": "cycle_data_gate_only",
            "required_state_data": "metal_price;inventory;smelting_margin;capex_cycle;demand_proxy",
            "blocked_action": "backtest_before_PIT_state_gate",
        },
        {
            "sector_id": "cement",
            "status": "cycle_data_gate_only",
            "required_state_data": "regional_price;inventory;capacity_utilization;coal_cost;construction_demand_proxy",
            "blocked_action": "backtest_before_PIT_state_gate",
        },
    ]
    summary = {
        "created_at_utc": now_utc(),
        "task": "v5c_cycle_sector_data_gate_queue",
        "status": "completed_data_gate_queue_only",
        "backtest_allowed": False,
        "accepted": False,
        "v57f_core_modified": False,
    }
    _write_json(out / "v5c_cycle_sector_data_gate_summary.json", summary)
    _write_csv(out / "v5c_cycle_sector_data_gate_queue.csv", rows)
    _write_csv(
        out / "v5c_cycle_sector_pm_gate_decision.csv",
        [{"pm_gate_decision": "cycle_industries_data_gate_only_no_backtest", "accepted": False, "v57f_core_modified": False}],
    )
    (out / "v5c_cycle_sector_data_gate_report.md").write_text(
        "# V5c Cycle Sector Data Gate Queue\n\nCycle sectors remain data-gate-only. No model backtest is authorized until PIT-clean state variables are repaired and reviewed.\n",
        encoding="utf-8",
    )


def _summary(
    *,
    status: str,
    strict_rows: int,
    strict_capex_coverage: float,
    strict_fcf_coverage: float,
    manifest_rows: int,
    extracted_reports: int,
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    fatal = [row for row in blockers if row.get("severity") == "fatal"]
    return {
        "created_at_utc": now_utc(),
        "task": "v5c_infra_capex_original_statement_extraction",
        "status": status,
        "train_test_scope_start": TRAIN_START,
        "train_test_scope_end": TRAIN_END,
        "formal_backtest_scope_start": FORMAL_START,
        "formal_backtest_scope_end": FORMAL_END,
        "target_sleeves": ["highway_infrastructure", "port_rail_infrastructure"],
        "strict_panel_rows": strict_rows,
        "strict_capex_burden_coverage": strict_capex_coverage,
        "strict_free_cash_flow_yield_coverage": strict_fcf_coverage,
        "cninfo_manifest_rows": manifest_rows,
        "extracted_report_count": extracted_reports,
        "formal_backtest_used_as_validation": False,
        "v57f_core_modified": False,
        "v5f_primary_modified": False,
        "accepted": False,
        "live_trading_approved": False,
        "fatal_blocker_count": len(fatal),
        "nonfatal_blocker_count": sum(1 for row in blockers if row.get("severity") not in {"fatal", "none"}),
        "pm_gate_decision": "capex_fcf_data_gate_ready_for_fixed_rule_review" if not fatal and strict_capex_coverage >= 0.75 else ("blocked_by_pit_or_source_issue" if fatal else "capex_fcf_partial_manual_review_required"),
    }


def _write_blocked_outputs(out: Path, summary: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    _write_json(out / "v5c_infra_capex_original_statement_summary.json", summary)
    _write_csv(out / "v5c_infra_capex_blockers.csv", blockers)
    (out / "v5c_infra_capex_original_statement_report.md").write_text("# V5c Infra Capex Original Statement Extraction\n\nBlocked by missing required inputs.\n", encoding="utf-8")


def _capex_report(
    summary: dict[str, Any],
    coverage: list[dict[str, Any]],
    factor_preview: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    next_queue: list[dict[str, Any]],
) -> str:
    lines = [
        "# V5c Infra Capex / FCF Original Statement Extraction",
        "",
        f"- Status: `{summary['status']}`",
        f"- PM gate: `{summary['pm_gate_decision']}`",
        f"- Train/test scope: `{TRAIN_START}` to `{TRAIN_END}`",
        f"- Formal backtest used as validation: `{summary['formal_backtest_used_as_validation']}`",
        f"- V57f/V5f modified: `{summary['v57f_core_modified']}` / `{summary['v5f_primary_modified']}`",
        "",
        "## Coverage",
        "",
        "| sector | scope | field | coverage | status |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in coverage:
        if row["scope"] == "strict_pit_universe":
            lines.append(f"| {row['sector_id']} | {row['scope']} | {row['field']} | {row['coverage_ratio']} | {row['field_status']} |")
    lines.extend(["", "## Factor Preview", "", "| sector | factor | periods | avg spread | positive rate | status |", "| --- | --- | ---: | ---: | ---: | --- |"])
    for row in factor_preview:
        lines.append(f"| {row['sector_id']} | {row['factor_id']} | {row['period_count']} | {row['avg_top_minus_bottom_return']} | {row['positive_spread_rate']} | {row['preview_status']} |")
    lines.extend(["", "## Blockers"])
    for row in blockers:
        lines.append(f"- `{row['blocker_id']}` ({row['severity']}): {row.get('detail', '')}")
    lines.extend(["", "## Next Queue"])
    for row in next_queue:
        lines.append(f"- {row['priority']} `{row['task_id']}`: {row['status']}")
    return "\n".join(lines) + "\n"


def _ocf_spec_report(summary: dict[str, Any], rule_spec: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    lines = [
        "# V5c Highway OCF Quality Fixed Rule Quant Spec",
        "",
        f"- Status: `{summary['status']}`",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        "- This is a spec boundary only; no engineering backtest, no acceptance.",
        "",
        "## Fixed Rules",
    ]
    for row in rule_spec:
        lines.append(f"- `{row['rule_id']}`: {row['rule_type']}; status=`{row['status']}`")
    return "\n".join(lines) + "\n"


def _capex_rules() -> str:
    return "\n".join(
        [
            "# Agent Execution Rules",
            "",
            "- Use 2013-01-01 to 2021-04-30 as train/test research only.",
            "- Do not use 2021-05-01 to 2026-05-31 as factor discovery or OOS validation.",
            "- Only fill capex/FCF from original financial report pages with PIT visible dates.",
            "- Do not modify V57f core or V5f primary.",
            "- Do not mark accepted or live approved.",
            "- Cycle sectors remain data-gate-only; no backtest.",
            "",
        ]
    )


def _spec_rules() -> str:
    return "\n".join(
        [
            "# Agent Execution Rules",
            "",
            "- This packet is Quant spec only.",
            "- Do not run engineering backtests from this spec without separate approval.",
            "- Risk-cap rules may limit weak cash-flow names but may not add new stocks or cross sleeves.",
            "- No accepted or live-approved status.",
            "",
        ]
    )


def _is_usable_financial_report_title(title: str) -> bool:
    if not any(token in title for token in ["\u5e74\u5ea6\u62a5\u544a", "\u534a\u5e74\u5ea6\u62a5\u544a", "\u7b2c\u4e00\u5b63\u5ea6\u62a5\u544a", "\u7b2c\u4e09\u5b63\u5ea6\u62a5\u544a"]):
        return False
    blocked = ["\u6458\u8981", "\u6b63\u6587", "\u5df2\u53d6\u6d88", "\u53d6\u6d88", "\u82f1\u6587", "\u516c\u544a"]
    return not any(token in title for token in blocked)


def _infer_report_period(title: str) -> str:
    year_match = re.search(r"(20\d{2})\s*\u5e74", title)
    if not year_match:
        return ""
    year = year_match.group(1)
    if "\u7b2c\u4e00\u5b63\u5ea6" in title:
        return f"{year}-03-31"
    if "\u534a\u5e74\u5ea6" in title:
        return f"{year}-06-30"
    if "\u7b2c\u4e09\u5b63\u5ea6" in title:
        return f"{year}-09-30"
    if "\u5e74\u5ea6\u62a5\u544a" in title:
        return f"{year}-12-31"
    return ""


def _report_type(report_period: str) -> str:
    suffix = report_period[5:]
    return {"03-31": "q1", "06-30": "semiannual", "09-30": "q3", "12-31": "annual"}.get(suffix, "")


def _visible_date_from_adjunct(adjunct: str) -> str:
    match = re.search(r"finalpage/(\d{4}-\d{2}-\d{2})/", adjunct)
    return match.group(1) if match else ""


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def _ms_to_date(value: Any) -> str:
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return ""


def _preview_status(spreads: list[float]) -> str:
    if len(spreads) < 4:
        return "insufficient_periods_diagnostic"
    positive_rate = sum(1 for value in spreads if value > 0) / len(spreads)
    avg = _mean(spreads)
    if avg is not None and avg > 0 and positive_rate >= 0.6:
        return "pre2021_positive_needs_fixed_rule_review_not_accepted"
    return "diagnostic_only_no_stable_pre2021_spread"


def _coverage_ratio(coverage: list[dict[str, Any]], scope: str, field: str) -> float:
    vals = [float(row["coverage_ratio"]) for row in coverage if row.get("scope") == scope and row.get("field") == field]
    return sum(vals) / len(vals) if vals else 0.0


def _first_date(text: str) -> str:
    dates = [item for item in str(text).split(";") if item]
    return sorted(dates)[0] if dates else ""


def _number_value(text: str) -> float | None:
    token = text.strip().replace(",", "")
    negative = token.startswith("-") or token.startswith("(") or token.startswith("\uff08")
    token = token.strip("-()\uff08\uff09")
    try:
        value = float(token)
    except ValueError:
        return None
    return -value if negative else value


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        result = float(text)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def _fmt(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return ""
    return f"{number:.10g}"


def _mean(values: Any) -> float | None:
    vals = [value for value in values if value is not None and math.isfinite(value)]
    return sum(vals) / len(vals) if vals else None


def _groupby(rows: list[dict[str, Any]], key_func: Any) -> dict[Any, list[dict[str, Any]]]:
    out: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        out[key_func(row)].append(row)
    return dict(out)


def _nonfatal(blocker_id: str, code: str, report_period: str, description: str) -> dict[str, Any]:
    return {
        "blocker_id": blocker_id,
        "severity": "nonfatal",
        "scope": "infra_capex",
        "code": code,
        "report_period": report_period,
        "detail": description,
        "required_action": "review source or retry",
    }


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--max-codes", type=int, default=None)
    parser.add_argument("--max-reports", type=int, default=None)
    args = parser.parse_args()
    config = InfraCapexConfig(
        download_missing=not args.no_download,
        reuse_cached_manifest=not args.no_cache,
        reuse_cached_downloads=not args.no_cache,
        reuse_cached_extraction=False,
        max_codes=args.max_codes,
        max_reports=args.max_reports,
    )
    summary = run_v5c_infra_capex_original_statement_extraction(Path(args.root), config)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

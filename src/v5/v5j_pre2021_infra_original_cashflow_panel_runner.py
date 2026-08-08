from __future__ import annotations

import csv
import json
import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from v5.v5c_infra_capex_original_statement_extraction_runner import _extract_cashflow_values_from_pdf


OUT = Path("v5j_pre2021_infra_original_cashflow_panel") / "current"
POOL = Path("processed") / "pre2021_repaired_multisleeve_pit_pool_v5" / "repaired_multisleeve_pit_pool.csv"
QUALITY = Path("processed") / "pre2021_repaired_multisleeve_pit_pool_v5" / "pit_financial_quality_panel.csv"
SLEEVES = {"highway_infrastructure", "port_rail_infrastructure", "utilities_electricity"}
SEARCH = "http://www.cninfo.com.cn/new/information/topSearch/query"
ANNOUNCEMENTS = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
STATIC = "http://static.cninfo.com.cn/"


def run_v5j_pre2021_infra_original_cashflow_panel(root: Path = Path("."), *, download_missing: bool = True, max_reports: int | None = None) -> dict[str, Any]:
    out = root / OUT
    pdf = out / "pdf"
    out.mkdir(parents=True, exist_ok=True)
    pdf.mkdir(exist_ok=True)
    db = _database(root)
    pool_path, quality_path = db / POOL, db / QUALITY
    if not pool_path.exists() or not quality_path.exists():
        raise FileNotFoundError("Missing repaired pre-2021 pool or PIT financial-quality panel")
    pool = [r for r in _read(pool_path) if r.get("sleeve_id") in SLEEVES and r.get("pool_eligibility") == "eligible_for_predecessor_pool"]
    quality = _read(quality_path)
    requirements = _requirements(pool, quality)
    manifest, query_audit = _manifest(sorted({r["code"] for r in requirements}))
    source_plan = _source_plan(requirements, manifest)
    if max_reports is not None:
        source_plan = source_plan[:max_reports]
    downloaded = _download(source_plan, pdf, download_missing)
    extracted = _extract(downloaded, out / "v5j_infra_cashflow_original_statement_candidates.csv")
    panel = _apply(pool, quality, extracted)
    coverage = _coverage(panel)
    blockers = _blockers(coverage, downloaded, query_audit)
    summary = {
        "created_at_utc": _now(), "task": "v5j_pre2021_infra_original_cashflow_panel",
        "sleeves": sorted(SLEEVES), "pool_row_count": len(pool), "report_requirement_count": len(requirements),
        "report_manifest_count": len(manifest), "source_plan_count": len(source_plan),
        "downloaded_or_cached_pdf_count": sum(r["download_status"] in {"downloaded", "cached"} for r in downloaded),
        "original_statement_extraction_pass_count": sum(r["extraction_status"] == "pass_original_statement_extracted" for r in extracted),
        "strict_capex_coverage_min": min((float(r["coverage_ratio"]) for r in coverage if r["field"] == "capex_burden"), default=0.0),
        "strict_fcf_coverage_min": min((float(r["coverage_ratio"]) for r in coverage if r["field"] == "free_cash_flow_yield"), default=0.0),
        "status": "original_statement_panel_partial_needs_page_review", "accepted": False,
        "v57f_core_modified": False, "strategy_backtest_started": False,
    }
    _write(out / "v5j_infra_cashflow_report_requirements.csv", requirements)
    _write(out / "v5j_infra_cashflow_cninfo_manifest.csv", manifest)
    _write(out / "v5j_infra_cashflow_source_plan.csv", source_plan)
    _write(out / "v5j_infra_cashflow_download_audit.csv", downloaded)
    _write(out / "v5j_infra_cashflow_original_statement_candidates.csv", extracted)
    _write(out / "v5j_infra_cashflow_pit_panel.csv", panel)
    _write(out / "v5j_infra_cashflow_field_coverage.csv", coverage)
    _write(out / "v5j_infra_cashflow_query_audit.csv", query_audit)
    _write(out / "v5j_infra_cashflow_blockers.csv", blockers)
    (out / "v5j_infra_cashflow_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "v5j_infra_cashflow_report.md").write_text(_report(summary, blockers), encoding="utf-8")
    return summary


def _database(root: Path) -> Path:
    direct = root / "数据库"
    if direct.exists():
        return direct
    matches = list(root.glob("*"))
    return next((p for p in matches if p.name.encode("utf-8", "ignore").decode("utf-8", "ignore") == "数据库"), direct)


def _requirements(pool: list[dict[str, str]], quality: list[dict[str, str]]) -> list[dict[str, Any]]:
    eligible = {(r["rebalance_date"], r["code"], r["sleeve_id"]) for r in pool}
    needed: dict[tuple[str, str], dict[str, Any]] = {}
    for row in quality:
        key = (row.get("rebalance_date", ""), row.get("code", ""), row.get("sleeve_id", ""))
        period = row.get("statement_period", "")[:10]
        visible = row.get("statement_pub_date", "")[:10]
        if key not in eligible or not period or not visible:
            continue
        group = needed.setdefault((row["code"], period), {"code": row["code"], "report_period": period, "sleeve_ids": set(), "rebalance_dates": set(), "required_visible_dates": set()})
        group["sleeve_ids"].add(row["sleeve_id"]); group["rebalance_dates"].add(row["rebalance_date"]); group["required_visible_dates"].add(visible)
    return sorted(({**r, "sleeve_ids": ";".join(sorted(r["sleeve_ids"])), "rebalance_dates": ";".join(sorted(r["rebalance_dates"])), "required_visible_dates": ";".join(sorted(r["required_visible_dates"]))} for r in needed.values()), key=lambda r: (r["code"], r["report_period"]))


def _manifest(codes: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    session = requests.Session(); headers = {"User-Agent": "Mozilla/5.0", "Referer": "http://www.cninfo.com.cn/"}
    result: list[dict[str, Any]] = []; audit: list[dict[str, Any]] = []
    for code in codes:
        plain = code.split(".")[0]
        try:
            orgs = session.post(SEARCH, headers=headers, data={"keyWord": plain, "maxNum": 10}, timeout=25).json()
            org = next((r.get("orgId") for r in orgs if str(r.get("code")) == plain and r.get("orgId")), "")
            if not org:
                audit.append({"code": code, "status": "org_id_missing"}); continue
            count = 0
            # CNInfo's broad historical query can repeatedly return only the newest
            # page. Query by announcement year instead, retaining all early filings.
            notices: list[dict[str, Any]] = []
            for year in range(2011, 2022):
                end = "2021-04-30" if year == 2021 else f"{year}-12-31"
                response = session.post(ANNOUNCEMENTS, headers=headers, data={"pageNum": 1, "pageSize": 30, "column": "sse" if code.endswith("XSHG") else "szse", "tabName": "fulltext", "plate": "", "stock": f"{plain},{org}", "searchkey": "", "secid": "", "category": "category_ndbg_szsh;category_bndbg_szsh;category_yjdbg_szsh;category_sjdbg_szsh;", "trade": "", "seDate": f"{year}-01-01~{end}", "sortName": "", "sortType": "", "isHLtitle": "true"}, timeout=25).json()
                page_rows = response.get("announcements") or []
                notices.extend(page_rows)
            for item in notices:
                title = re.sub(r"<[^>]+>", "", str(item.get("announcementTitle") or ""))
                visible = _date_ms(item.get("announcementTime"))
                period = _period(title) or _period_from_undated_title(title, visible)
                if not period or "摘要" in title or "英文" in title:
                    continue
                adjunct = str(item.get("adjunctUrl") or "")
                result.append({"code": code, "report_period": period, "announcement_title": title, "pit_visible_date": visible, "pdf_url": STATIC + adjunct if adjunct else "", "source": "cninfo_original_financial_statement", "accepted": False}); count += 1
            audit.append({"code": code, "status": "pass", "financial_report_count": count})
        except Exception as exc:  # noqa: BLE001
            audit.append({"code": code, "status": f"query_error:{type(exc).__name__}", "detail": str(exc)})
        time.sleep(0.1)
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for row in result:
        key = (row["code"], row["report_period"])
        # The initial formal filing is PIT-safe; later correction/republication is
        # not allowed to replace it for an earlier rebalance.
        current = unique.get(key)
        score = (0 if "全文" in row["announcement_title"] else 1, row["pit_visible_date"])
        current_score = (0 if "全文" in current["announcement_title"] else 1, current["pit_visible_date"]) if current else None
        if current is None or score < current_score:
            unique[key] = row
    return sorted(unique.values(), key=lambda r: (r["code"], r["report_period"])), audit


def _period(title: str) -> str:
    match = re.search(r"(20\d{2})\s*年", title)
    if not match: return ""
    year = match.group(1)
    if "第一季度" in title: return f"{year}-03-31"
    if "半年度" in title: return f"{year}-06-30"
    if "第三季度" in title or "三季度" in title: return f"{year}-09-30"
    if "年度报告" in title: return f"{year}-12-31"
    return ""


def _period_from_undated_title(title: str, visible_date: str) -> str:
    if len(visible_date) < 4:
        return ""
    year = visible_date[:4]
    if "第一季度" in title:
        return f"{year}-03-31"
    if "第三季度" in title or "三季度" in title:
        return f"{year}-09-30"
    if "半年度" in title:
        return f"{year}-06-30"
    return f"{int(year) - 1}-12-31" if "年度报告" in title else ""


def _source_plan(requirements: list[dict[str, Any]], manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    known = {(r["code"], r["report_period"]): r for r in manifest}
    return [{**r, **{k: known.get((r["code"], r["report_period"]), {}).get(k, "") for k in ("announcement_title", "pit_visible_date", "pdf_url")}, "source_status": "cninfo_pdf_available" if known.get((r["code"], r["report_period"]), {}).get("pdf_url") else "missing_cninfo_pdf"} for r in requirements]


def _download(rows: list[dict[str, Any]], pdf_dir: Path, enabled: bool) -> list[dict[str, Any]]:
    session = requests.Session(); headers = {"User-Agent": "Mozilla/5.0", "Referer": "http://www.cninfo.com.cn/"}; out = []
    for row in rows:
        path = pdf_dir / f"{row['code'].replace('.', '_')}_{row['report_period']}.pdf"
        status = "cached" if path.exists() and path.stat().st_size > 1024 else ""
        error = ""
        if not status and enabled and row.get("pdf_url"):
            try:
                response = session.get(row["pdf_url"], headers=headers, timeout=35); response.raise_for_status(); path.write_bytes(response.content); status = "downloaded"
            except Exception as exc:  # noqa: BLE001
                status, error = f"download_error:{type(exc).__name__}", str(exc)
        if not status: status = "not_downloaded_or_source_missing"
        out.append({**row, "resolved_pdf_path": str(path), "download_status": status, "pdf_bytes": path.stat().st_size if path.exists() else 0, "error": error})
        time.sleep(0.08)
    return out


def _extract(rows: list[dict[str, Any]], existing_path: Path) -> list[dict[str, Any]]:
    # PDFs are independent. A small bounded pool makes the repair restartable
    # within the agent time window without changing extraction semantics.
    previous: dict[tuple[str, str], dict[str, Any]] = {}
    if existing_path.exists():
        # Reuse confirmed extraction rows while a parser repair reprocesses only
        # the remaining failures.
        previous = {(row.get("code", ""), row.get("report_period", "")): row for row in _read(existing_path) if row.get("extraction_status") == "pass_original_statement_extracted"}
    prior_rows = [previous.get((row.get("code", ""), row.get("report_period", ""))) for row in rows]
    pending = [row for row, prior in zip(rows, prior_rows) if prior is None]
    with ThreadPoolExecutor(max_workers=4) as executor:
        repaired = {(row["code"], row["report_period"]): row for row in executor.map(_extract_one, pending)}
    return [prior if prior is not None else repaired[(row["code"], row["report_period"])] for row, prior in zip(rows, prior_rows)]


def _extract_one(row: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    if row["download_status"] in {"downloaded", "cached"}:
        try: values = _extract_cashflow_values_from_pdf(Path(row["resolved_pdf_path"]))
        except Exception as exc: values = {"error": f"extract_error:{type(exc).__name__}"}
    status = "pass_original_statement_extracted" if values.get("operating_cash_flow_net") is not None and values.get("capex_cash_paid") is not None else "needs_original_page_review_or_missing_term"
    return {**row, "operating_cash_flow_net_original": values.get("operating_cash_flow_net", ""), "capex_cash_paid_original": values.get("capex_cash_paid", ""), "unit": values.get("unit", ""), "unit_multiplier": values.get("unit_multiplier", ""), "source_page_number": values.get("page_number", ""), "sample_context": values.get("sample_context", ""), "parse_rule": values.get("parse_rule", values.get("error", "")), "extraction_status": status, "accepted": False}


def _apply(pool: list[dict[str, str]], quality: list[dict[str, str]], extracted: list[dict[str, Any]]) -> list[dict[str, Any]]:
    qmap = {(r["rebalance_date"], r["code"], r["sleeve_id"]): r for r in quality}
    emap = {(r["code"], r["report_period"]): r for r in extracted if r["extraction_status"] == "pass_original_statement_extracted"}
    result=[]
    for item in pool:
        q = qmap.get((item["rebalance_date"], item["code"], item["sleeve_id"]), {}); period = q.get("statement_period", "")[:10]; e = emap.get((item["code"], period), {})
        cfo, capex = _num(e.get("operating_cash_flow_net_original")), _num(e.get("capex_cash_paid_original")); ocf_yield = _num(q.get("fcf_yield"))
        # The existing fcf_yield may be unavailable; it is never silently backfilled by a price proxy here.
        capex_burden = capex / cfo if cfo and cfo > 0 and capex is not None else None
        result.append({"rebalance_date": item["rebalance_date"], "code": item["code"], "sleeve_id": item["sleeve_id"], "statement_period": period, "statement_visible_date": q.get("statement_pub_date", ""), "ocf_original": cfo if cfo is not None else "", "capex_original": capex if capex is not None else "", "capex_burden": capex_burden if capex_burden is not None else "", "free_cash_flow_yield": "", "free_cash_flow_status": "blocked_no_pit_market_value_denominator_in_this_repair", "source_page_number": e.get("source_page_number", ""), "source_pdf": e.get("resolved_pdf_path", ""), "pit_visible": bool(e) and str(e.get("pit_visible_date", "")) <= item["rebalance_date"], "status": "pass_original_ocf_capex" if capex_burden is not None else "missing_or_unreviewed_original_statement", "accepted": False})
    return result


def _coverage(panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out=[]
    for sleeve in sorted(SLEEVES):
        group=[r for r in panel if r["sleeve_id"]==sleeve]
        for field in ("ocf_original", "capex_original", "capex_burden", "free_cash_flow_yield"):
            passed=sum(str(r.get(field,"")) != "" for r in group); ratio=passed/len(group) if group else 0.0
            out.append({"sleeve_id": sleeve, "field": field, "row_count": len(group), "pass_row_count": passed, "coverage_ratio": f"{ratio:.6f}", "status": "pass" if ratio >= .95 else ("partial" if ratio else "missing")})
    return out


def _blockers(coverage: list[dict[str, Any]], downloads: list[dict[str, Any]], audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers=[]
    if any(r["status"] != "pass" for r in coverage): blockers.append({"blocker_id":"infra_original_cashflow_panel_incomplete","severity":"blocking_for_exact_target_reconstruction","detail":"One or more sleeve/field coverage ratios remain below 95%; source values stay sidecar-only."})
    if any(str(r.get("status","")).startswith("query_error") for r in audit): blockers.append({"blocker_id":"cninfo_financial_report_query_error","severity":"review","detail":"Retry only failed codes; do not substitute later statements."})
    if any(str(r.get("download_status","")).startswith("download_error") for r in downloads): blockers.append({"blocker_id":"cninfo_financial_report_download_error","severity":"review","detail":"Retry failed original report downloads."})
    return blockers


def _num(value: Any) -> float | None:
    try: return float(value)
    except (TypeError, ValueError): return None
def _date_ms(value: Any) -> str:
    try: return datetime.fromtimestamp(int(value)/1000, tz=timezone.utc).date().isoformat()
    except (TypeError, ValueError, OSError): return ""
def _read(path: Path) -> list[dict[str,str]]:
    with path.open(encoding="utf-8-sig", newline="") as h: return list(csv.DictReader(h))
def _write(path: Path, rows: list[dict[str,Any]]) -> None:
    fields=list(dict.fromkeys(k for r in rows for k in r)) or ["empty"]
    with path.open("w",encoding="utf-8-sig",newline="") as h: w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(rows)
def _now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")
def _report(summary:dict[str,Any], blockers:list[dict[str,Any]])->str:
    lines=["# Pre-2021 infrastructure original cashflow panel", "", f"- PIT pool rows: `{summary['pool_row_count']}`; report requirements: `{summary['report_requirement_count']}`.", "- Values are extracted candidates with source page and unit. They remain page-review sidecar data, not a V57f core replacement.", ""]
    lines.extend(f"- `{b['blocker_id']}`: {b['detail']}" for b in blockers); return "\n".join(lines)+"\n"


if __name__ == "__main__": print(json.dumps(run_v5j_pre2021_infra_original_cashflow_panel(), ensure_ascii=False, indent=2))

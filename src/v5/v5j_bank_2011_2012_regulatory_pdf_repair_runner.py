from __future__ import annotations

import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from v5.local_1min_clean_ingest_runner import find_v5_database


OUT = Path("v5j_bank_2011_2012_regulatory_pdf_repair") / "current"
POOL = Path("processed") / "pre2021_repaired_multisleeve_pit_pool_v5" / "repaired_multisleeve_pit_pool.csv"
SEARCH = "http://www.cninfo.com.cn/new/information/topSearch/query"
ANNOUNCEMENTS = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
STATIC = "http://static.cninfo.com.cn/"
FIELDS = ("nonperforming_loan_rate", "provision_coverage", "core_tier_1_capital_adequacy_ratio")
TERMS = {
    "nonperforming_loan_rate": ("不良贷款率",),
    "provision_coverage": ("拨备覆盖率",),
    "core_tier_1_capital_adequacy_ratio": ("核心一级资本充足率",),
}


def run_v5j_bank_2011_2012_regulatory_pdf_repair(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT
    pdf_dir = out / "pdf"
    out.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(exist_ok=True)
    db = find_v5_database(root)
    pool = [
        row for row in _read_csv(db / POOL)
        if row.get("sleeve_id") == "bank" and row.get("rebalance_date", "") <= "2014-01-02"
        and row.get("pool_eligibility") == "eligible_for_predecessor_pool"
    ]
    codes = sorted({row["code"] for row in pool})
    manifest, query_audit = _manifest(codes)
    download = _download(manifest, pdf_dir)
    candidates, extract_audit = _extract(download)
    coverage = _coverage(pool, manifest, candidates)
    blockers = _blockers(coverage, query_audit, download)
    summary = {
        "created_at_utc": _now(),
        "task": "v5j_bank_2011_2012_regulatory_pdf_repair",
        "early_bank_code_count": len(codes),
        "report_manifest_count": len(manifest),
        "downloaded_or_cached_pdf_count": sum(row["download_status"] in {"downloaded", "cached"} for row in download),
        "term_candidate_count": len(candidates),
        "rebalance_rows_with_all_three_term_candidates": sum(row["all_three_candidate_terms"] for row in coverage),
        "rebalance_pool_row_count": len(coverage),
        "status": "candidate_extraction_ready_for_original_page_review",
        "accepted": False,
        "v57f_core_modified": False,
        "strategy_backtest_started": False,
    }
    _write_csv(out / "v5j_bank_2011_2012_report_manifest.csv", manifest)
    _write_csv(out / "v5j_bank_2011_2012_query_audit.csv", query_audit)
    _write_csv(out / "v5j_bank_2011_2012_download_audit.csv", download)
    _write_csv(out / "v5j_bank_2011_2012_term_candidates.csv", candidates)
    _write_csv(out / "v5j_bank_2011_2012_pit_coverage.csv", coverage)
    _write_csv(out / "v5j_bank_2011_2012_blockers.csv", blockers)
    _write_json(out / "v5j_bank_2011_2012_summary.json", summary)
    (out / "v5j_bank_2011_2012_report.md").write_text(_report(summary, blockers), encoding="utf-8")
    return summary


def _manifest(codes: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "http://www.cninfo.com.cn/"}
    rows: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    for code in codes:
        plain = code.split(".")[0]
        exchange = "sse" if code.endswith("XSHG") else "szse"
        try:
            org = session.post(SEARCH, headers=headers, data={"keyWord": plain, "maxNum": 10}, timeout=20).json()
            item = next((x for x in org if str(x.get("code")) == plain and x.get("orgId")), None)
            if not item:
                audit.append({"code": code, "status": "org_id_missing"})
                continue
            payload = {
                "pageNum": 1, "pageSize": 60, "column": exchange, "tabName": "fulltext", "plate": "",
                "stock": f"{plain},{item['orgId']}", "searchkey": "", "secid": "",
                "category": "category_ndbg_szsh;category_bndbg_szsh;category_yjdbg_szsh;category_sjdbg_szsh;",
                "trade": "", "seDate": "2011-01-01~2014-01-02", "sortName": "", "sortType": "", "isHLtitle": "true",
            }
            data = session.post(ANNOUNCEMENTS, headers=headers, data=payload, timeout=20).json()
            count = 0
            for announcement in data.get("announcements") or []:
                title = re.sub(r"<[^>]+>", "", str(announcement.get("announcementTitle") or ""))
                match = re.search(r"(2011|2012|2013)年年度报告", title)
                if not match or "摘要" in title or "英文" in title:
                    continue
                adjunct = str(announcement.get("adjunctUrl") or "")
                if not adjunct:
                    continue
                year = match.group(1)
                published = _date_ms(announcement.get("announcementTime"))
                rows.append({"code": code, "report_year": year, "report_period": f"{year}-12-31", "announcement_title": title, "pit_visible_date": published, "pdf_url": STATIC + adjunct, "source": "cninfo_original_annual_report", "accepted": False})
                count += 1
            audit.append({"code": code, "status": "pass", "annual_report_count": count})
        except Exception as exc:  # noqa: BLE001
            audit.append({"code": code, "status": f"query_error:{type(exc).__name__}", "detail": str(exc)})
        time.sleep(0.1)
    # Retain the latest filing per code/report-year. Revised annual reports are preferred.
    chosen: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["code"], row["report_year"])
        if key not in chosen or row["pit_visible_date"] >= chosen[key]["pit_visible_date"]:
            chosen[key] = row
    return sorted(chosen.values(), key=lambda row: (row["code"], row["report_year"])), audit


def _download(rows: list[dict[str, Any]], pdf_dir: Path) -> list[dict[str, Any]]:
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "http://www.cninfo.com.cn/"}
    out = []
    for row in rows:
        path = pdf_dir / f"{row['code'].replace('.', '_')}_{row['report_year']}_annual_report.pdf"
        status = "cached" if path.exists() and path.stat().st_size > 1024 else ""
        error = ""
        if not status:
            try:
                response = session.get(row["pdf_url"], headers=headers, timeout=30)
                response.raise_for_status()
                path.write_bytes(response.content)
                status = "downloaded"
            except Exception as exc:  # noqa: BLE001
                status, error = f"download_error:{type(exc).__name__}", str(exc)
        out.append({**row, "pdf_path": str(path), "download_status": status, "pdf_bytes": path.stat().st_size if path.exists() else 0, "error": error})
        time.sleep(0.1)
    return out


def _extract(download: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    import fitz  # type: ignore

    candidates: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    for row in download:
        path = Path(row["pdf_path"])
        if row["download_status"] not in {"downloaded", "cached"} or not path.exists():
            audit.append({"code": row["code"], "report_year": row["report_year"], "status": "pdf_unavailable"})
            continue
        try:
            doc = fitz.open(path)
            hit_count = 0
            for page_idx in range(len(doc)):
                text = doc.load_page(page_idx).get_text("text") or ""
                normal = re.sub(r"\s+", " ", text)
                for field, terms in TERMS.items():
                    for term in terms:
                        for match in re.finditer(re.escape(term), normal):
                            start, end = max(0, match.start() - 120), min(len(normal), match.end() + 180)
                            context = normal[start:end]
                            values = re.findall(r"(?<!\d)(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*%", context)
                            candidates.append({**row, "field": field, "term": term, "page_number": page_idx + 1, "value_candidates_pct": ";".join(values[:8]), "context": context, "candidate_status": "needs_original_page_review", "accepted": False})
                            hit_count += 1
            doc.close()
            audit.append({"code": row["code"], "report_year": row["report_year"], "status": "pass", "term_hit_count": hit_count})
        except Exception as exc:  # noqa: BLE001
            audit.append({"code": row["code"], "report_year": row["report_year"], "status": f"extract_error:{type(exc).__name__}", "detail": str(exc)})
    return candidates, audit


def _coverage(pool: list[dict[str, str]], manifest: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    available = {(row["code"], row["report_year"]): row for row in manifest}
    fields_by_key: dict[tuple[str, str], set[str]] = {}
    for row in candidates:
        fields_by_key.setdefault((row["code"], row["report_year"]), set()).add(row["field"])
    output = []
    for item in pool:
        visible = [row for row in manifest if row["code"] == item["code"] and row["pit_visible_date"] <= item["rebalance_date"]]
        source = visible[-1] if visible else None
        fields = fields_by_key.get((source["code"], source["report_year"]), set()) if source else set()
        output.append({"rebalance_date": item["rebalance_date"], "code": item["code"], "selected_report_year": source["report_year"] if source else "", "selected_report_visible_date": source["pit_visible_date"] if source else "", "all_three_candidate_terms": set(FIELDS).issubset(fields), "candidate_fields": ";".join(sorted(fields)), "future_report_used": False, "pit_status": "candidate_terms_found" if set(FIELDS).issubset(fields) else "missing_source_or_term", "accepted": False})
    return output


def _blockers(coverage: list[dict[str, Any]], query: list[dict[str, Any]], download: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    if any(str(row.get("status", "")).startswith("query_error") for row in query):
        result.append({"blocker_id": "cninfo_query_error", "severity": "review", "detail": "At least one CNInfo report query failed."})
    if any(str(row.get("download_status", "")).startswith("download_error") for row in download):
        result.append({"blocker_id": "annual_report_download_error", "severity": "review", "detail": "At least one annual report did not download."})
    missing = sum(not row["all_three_candidate_terms"] for row in coverage)
    if missing:
        result.append({"blocker_id": "bank_original_page_review_or_disclosure_gap", "severity": "blocking_for_target_reconstruction", "detail": f"{missing} early bank observations do not yet have all three machine-extracted candidate terms."})
    return result


def _date_ms(value: Any) -> str:
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).date().isoformat()
    except (TypeError, ValueError, OSError):
        return ""


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ["empty"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _report(summary: dict[str, Any], blockers: list[dict[str, Any]]) -> str:
    lines = ["# Bank 2011/2012 Original Regulatory Report Repair", "", f"- Codes: `{summary['early_bank_code_count']}`.", f"- Candidate reports: `{summary['report_manifest_count']}`.", f"- Candidate term rows: `{summary['term_candidate_count']}`.", "- Every number remains page-review required; no model target or strategy test was run.", ""]
    lines.extend(f"- `{row['blocker_id']}`: {row['detail']}" for row in blockers)
    return "\n".join(lines) + "\n"


def _report_period(title: str) -> str:
    match = re.search(r"(2011|2012|2013)\s*\u5e74", title)
    if not match:
        return ""
    year = match.group(1)
    if "\u7b2c\u4e00\u5b63\u5ea6" in title:
        return f"{year}-03-31"
    if "\u7b2c\u4e09\u5b63\u5ea6" in title:
        return f"{year}-09-30"
    if "\u5e74\u5ea6\u62a5\u544a" in title:
        return f"{year}-12-31"
    return ""


def _manifest(codes: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Override the annual-only collector with PIT-safe annual/quarterly slices."""
    session = requests.Session(); headers = {"User-Agent": "Mozilla/5.0", "Referer": "http://www.cninfo.com.cn/"}
    rows: list[dict[str, Any]] = []; audit: list[dict[str, Any]] = []
    for code in codes:
        plain = code.split(".")[0]; exchange = "sse" if code.endswith("XSHG") else "szse"
        try:
            org = session.post(SEARCH, headers=headers, data={"keyWord": plain, "maxNum": 10}, timeout=20).json()
            item = next((x for x in org if str(x.get("code")) == plain and x.get("orgId")), None)
            if not item:
                audit.append({"code": code, "status": "org_id_missing"}); continue
            count = 0
            for year in range(2011, 2014):
                payload = {"pageNum": 1, "pageSize": 30, "column": exchange, "tabName": "fulltext", "plate": "", "stock": f"{plain},{item['orgId']}", "searchkey": "", "secid": "", "category": "category_ndbg_szsh;category_bndbg_szsh;category_yjdbg_szsh;category_sjdbg_szsh;", "trade": "", "seDate": f"{year}-01-01~{year}-12-31", "sortName": "", "sortType": "", "isHLtitle": "true"}
                for notice in session.post(ANNOUNCEMENTS, headers=headers, data=payload, timeout=20).json().get("announcements") or []:
                    title = re.sub(r"<[^>]+>", "", str(notice.get("announcementTitle") or "")); period = _report_period(title)
                    adjunct = str(notice.get("adjunctUrl") or "")
                    if period and adjunct and "\u6458\u8981" not in title and "\u82f1\u6587" not in title:
                        rows.append({"code": code, "report_year": period[:4], "report_period": period, "announcement_title": title, "pit_visible_date": _date_ms(notice.get("announcementTime")), "pdf_url": STATIC + adjunct, "source": "cninfo_original_regulatory_report", "accepted": False}); count += 1
            audit.append({"code": code, "status": "pass", "regulatory_report_count": count})
        except Exception as exc:  # noqa: BLE001
            audit.append({"code": code, "status": f"query_error:{type(exc).__name__}", "detail": str(exc)})
        time.sleep(0.1)
    selected: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key=(row["code"],row["report_period"])
        if key not in selected or row["pit_visible_date"] < selected[key]["pit_visible_date"]: selected[key]=row
    return sorted(selected.values(), key=lambda r:(r["code"],r["pit_visible_date"],r["report_period"])), audit


def _download(rows: list[dict[str, Any]], pdf_dir: Path) -> list[dict[str, Any]]:
    session = requests.Session(); headers = {"User-Agent": "Mozilla/5.0", "Referer": "http://www.cninfo.com.cn/"}; out=[]
    for row in rows:
        path = pdf_dir / f"{row['code'].replace('.', '_')}_{row.get('report_period', row['report_year'])}_regulatory_report.pdf"; status="cached" if path.exists() and path.stat().st_size>1024 else ""; error=""
        if not status:
            try: response=session.get(row["pdf_url"],headers=headers,timeout=30);response.raise_for_status();path.write_bytes(response.content);status="downloaded"
            except Exception as exc: status,error=f"download_error:{type(exc).__name__}",str(exc)
        out.append({**row,"pdf_path":str(path),"download_status":status,"pdf_bytes":path.stat().st_size if path.exists() else 0,"error":error});time.sleep(.1)
    return out


def _coverage(pool: list[dict[str, str]], manifest: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields_by_key: dict[tuple[str, str], set[str]] = {}
    for row in candidates: fields_by_key.setdefault((row["code"], row.get("report_period", f"{row.get('report_year','')}-12-31")), set()).add(row["field"])
    output=[]
    for item in pool:
        visible=sorted((row for row in manifest if row["code"]==item["code"] and row["pit_visible_date"]<=item["rebalance_date"]),key=lambda r:r["pit_visible_date"])
        source=visible[-1] if visible else None; period=source.get("report_period",f"{source.get('report_year','')}-12-31") if source else ""; fields=fields_by_key.get((item["code"],period),set())
        output.append({"rebalance_date":item["rebalance_date"],"code":item["code"],"selected_report_year":source.get("report_year","") if source else "","selected_report_period":period,"selected_report_visible_date":source.get("pit_visible_date","") if source else "","all_three_candidate_terms":set(FIELDS).issubset(fields),"candidate_fields":";".join(sorted(fields)),"future_report_used":False,"pit_status":"candidate_terms_found" if set(FIELDS).issubset(fields) else "missing_source_or_term","accepted":False})
    return output


TERMS["core_tier_1_capital_adequacy_ratio"] = (*TERMS["core_tier_1_capital_adequacy_ratio"], "\u6838\u5fc3\u8d44\u672c\u5145\u8db3\u7387")


if __name__ == "__main__":
    print(json.dumps(run_v5j_bank_2011_2012_regulatory_pdf_repair(), ensure_ascii=False, indent=2))

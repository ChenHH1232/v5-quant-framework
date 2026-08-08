from __future__ import annotations

import csv
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path("v5c_bank_power_financial_report_data_gate") / "current"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
CNINFO_SEARCH_URL = "http://www.cninfo.com.cn/new/information/topSearch/query"
CNINFO_ANNOUNCE_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_STATIC_BASE = "http://static.cninfo.com.cn/"
BACKTEST_END = "2026-05-31"
BANK = "bank"
POWER = "utilities_electricity"


BANK_PRIORITY_CODES = ["000001.XSHE", "600000.XSHG", "601166.XSHG", "601288.XSHG", "601398.XSHG", "601939.XSHG"]
POWER_PRIORITY_CODES = ["600011.XSHG", "600027.XSHG", "600795.XSHG", "600886.XSHG", "601985.XSHG", "002039.XSHE"]


FIELD_KEYWORDS: dict[str, dict[str, list[str]]] = {
    BANK: {
        "net_interest_margin": ["净息差", "净利差"],
        "deposit_cost": ["存款成本率", "客户存款成本", "平均付息率", "吸收存款平均成本"],
        "interest_earning_assets": ["生息资产", "付息负债"],
        "asset_quality": ["不良贷款率", "关注类贷款", "拨备覆盖率"],
        "capital_buffer": ["核心一级资本充足率", "一级资本充足率", "资本充足率"],
    },
    POWER: {
        "fuel_cost": ["燃料成本", "燃煤成本", "煤价", "标煤单价", "入炉标煤单价"],
        "tariff": ["上网电价", "平均上网电价", "市场化交易电价", "电价"],
        "capacity_payment": ["容量电价", "容量电费", "容量补偿", "容量电价机制"],
        "utilization_hours": ["利用小时", "发电设备平均利用小时"],
        "hydro_water": ["来水", "径流", "蓄水", "水库", "水电"],
        "generation_volume": ["发电量", "上网电量", "售电量"],
    },
}


@dataclass
class ProbeConfig:
    download_limit_per_industry: int = 6
    request_timeout_seconds: int = 12
    sleep_seconds: float = 0.08
    max_pages_per_pdf: int | None = None


def run(root: Path = ROOT, config: ProbeConfig | None = None) -> Path:
    config = config or ProbeConfig()
    out = root / OUT_DIR
    pdf_dir = out / "pdf"
    out.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5c_bank_power_financial_report_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_inputs", blockers=blockers)
        _write_json(out / "v5c_bank_power_financial_report_summary.json", summary)
        return out / "v5c_bank_power_financial_report_summary.json"

    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv", dtype={"trade_date": str, "code": str})
    universe = _universe(signals)
    org_rows, annual_rows, query_blockers = _probe_cninfo(universe, config)
    sample_rows = _select_download_samples(annual_rows, config.download_limit_per_industry)
    download_rows = _download_samples(sample_rows, pdf_dir, config)
    keyword_rows = _extract_keyword_hits(download_rows, config)
    bank_gate = _field_gate(BANK, keyword_rows, annual_rows)
    power_gate = _field_gate(POWER, keyword_rows, annual_rows)
    fetch_queue = _fetch_queue(annual_rows, keyword_rows)
    blockers_out = query_blockers
    decision = _pm_decision(bank_gate, power_gate, blockers_out)

    _write_csv(out / "v5c_bank_power_cninfo_orgid_probe.csv", org_rows)
    _write_csv(out / "v5c_bank_power_annual_report_manifest.csv", annual_rows)
    _write_csv(out / "v5c_bank_power_financial_report_download_manifest.csv", download_rows)
    _write_csv(out / "v5c_bank_power_financial_report_keyword_hits.csv", keyword_rows)
    _write_csv(out / "v5c_bank_financial_report_field_gate.csv", bank_gate)
    _write_csv(out / "v5c_power_financial_report_field_gate.csv", power_gate)
    _write_csv(out / "v5c_bank_power_financial_report_fetch_queue.csv", fetch_queue)
    _write_csv(out / "v5c_bank_power_financial_report_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_bank_power_financial_report_blockers.csv", blockers_out)
    (out / "v5c_bank_power_financial_report_report.md").write_text(
        _report(bank_gate, power_gate, annual_rows, download_rows, keyword_rows, decision),
        encoding="utf-8",
    )
    (out / "v5c_bank_power_financial_report_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    summary = _summary(
        "completed_financial_report_data_gate_probe",
        annual_rows=annual_rows,
        download_rows=download_rows,
        keyword_rows=keyword_rows,
        bank_gate=bank_gate,
        power_gate=power_gate,
        pm_gate_decision=decision[0]["pm_gate_decision"],
        blockers=blockers_out,
    )
    _write_json(out / "v5c_bank_power_financial_report_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return out / "v5c_bank_power_financial_report_summary.json"


def _universe(signals: pd.DataFrame) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for sleeve in [BANK, POWER]:
        codes = sorted(signals[signals["sector_id"].eq(sleeve)]["code"].unique())
        for code in codes:
            rows.append({"industry": sleeve, "code": code, "cn_code": code.split(".")[0], "exchange": code.split(".")[1]})
    return rows


def _probe_cninfo(universe: list[dict[str, str]], config: ProbeConfig) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search",
    }
    org_rows: list[dict[str, Any]] = []
    annual_rows: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for item in universe:
        code = item["cn_code"]
        try:
            org = _query_org_id(session, headers, code, config.request_timeout_seconds)
            org_rows.append({**item, **org, "probe_status": "pass" if org.get("org_id") else "missing_org_id"})
            if org.get("org_id"):
                reports = _query_annual_reports(session, headers, item, org, config.request_timeout_seconds)
                annual_rows.extend(reports)
        except Exception as exc:  # noqa: BLE001
            blockers.append({"blocker_id": "cninfo_probe_error", "severity": "nonfatal", "status": "logged", "code": item["code"], "description": f"{type(exc).__name__}: {exc}"})
            org_rows.append({**item, "org_id": "", "sec_name": "", "market_type": "", "probe_status": f"error:{type(exc).__name__}"})
        time.sleep(config.sleep_seconds)
    return org_rows, annual_rows, blockers


def _query_org_id(session: requests.Session, headers: dict[str, str], code: str, timeout: int) -> dict[str, str]:
    response = session.post(CNINFO_SEARCH_URL, headers=headers, data={"keyWord": code, "maxNum": 10}, timeout=timeout)
    response.raise_for_status()
    candidates = response.json()
    for item in candidates:
        if str(item.get("code")) == code and item.get("orgId"):
            return {
                "org_id": str(item.get("orgId") or ""),
                "sec_name": str(item.get("zwjc") or ""),
                "market_type": str(item.get("type") or ""),
            }
    return {"org_id": "", "sec_name": "", "market_type": ""}


def _query_annual_reports(
    session: requests.Session,
    headers: dict[str, str],
    universe_row: dict[str, str],
    org: dict[str, str],
    timeout: int,
) -> list[dict[str, Any]]:
    cn_code = universe_row["cn_code"]
    column = "szse" if universe_row["exchange"] == "XSHE" else "sse"
    stock = f"{cn_code},{org['org_id']}"
    response = session.post(
        CNINFO_ANNOUNCE_URL,
        headers=headers,
        data={
            "pageNum": 1,
            "pageSize": 30,
            "column": column,
            "tabName": "fulltext",
            "plate": "",
            "stock": stock,
            "searchkey": "",
            "secid": "",
            "category": "category_ndbg_szsh;",
            "trade": "",
            "seDate": f"2021-01-01~{BACKTEST_END}",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    rows: list[dict[str, Any]] = []
    for announcement in payload.get("announcements") or []:
        title = _clean_html(str(announcement.get("announcementTitle") or ""))
        if not _is_full_annual_report_title(title):
            continue
        adjunct = str(announcement.get("adjunctUrl") or "")
        announcement_date = _ms_to_date(announcement.get("announcementTime"))
        report_period = _infer_report_period(title, announcement_date)
        rows.append(
            {
                "industry": universe_row["industry"],
                "code": universe_row["code"],
                "cn_code": cn_code,
                "sec_name": org.get("sec_name", ""),
                "org_id": org.get("org_id", ""),
                "announcement_title": title,
                "announcement_date": announcement_date,
                "report_period": report_period,
                "adjunct_url": adjunct,
                "pdf_url": CNINFO_STATIC_BASE + adjunct if adjunct else "",
                "source": "cninfo_hisAnnouncement",
                "pit_visible_date": announcement_date,
                "download_status": "queued",
            }
        )
    return rows


def _is_full_annual_report_title(title: str) -> bool:
    if "年度报告" not in title:
        return False
    blocked = ["摘要", "英文", "已取消", "取消", "关于", "公告"]
    return not any(token in title for token in blocked)


def _select_download_samples(annual_rows: list[dict[str, Any]], limit_per_industry: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    priority = {BANK: BANK_PRIORITY_CODES, POWER: POWER_PRIORITY_CODES}
    by_key = {(row["industry"], row["code"]): row for row in sorted(annual_rows, key=lambda r: r.get("announcement_date", ""), reverse=True)}
    for industry in [BANK, POWER]:
        count = 0
        for code in priority[industry]:
            row = by_key.get((industry, code))
            if row:
                selected.append(row)
                count += 1
            if count >= limit_per_industry:
                break
        if count < limit_per_industry:
            for row in sorted([r for r in annual_rows if r["industry"] == industry], key=lambda r: (r.get("announcement_date", ""), r.get("code", "")), reverse=True):
                if row not in selected:
                    selected.append(row)
                    count += 1
                if count >= limit_per_industry:
                    break
    return selected


def _download_samples(sample_rows: list[dict[str, Any]], pdf_dir: Path, config: ProbeConfig) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "http://www.cninfo.com.cn/"}
    for row in sample_rows:
        filename = f"{row['code'].replace('.', '_')}_{row['report_period']}_annual_report.pdf"
        local_path = pdf_dir / filename
        status = "not_attempted"
        byte_count = 0
        error = ""
        try:
            if local_path.exists() and local_path.stat().st_size > 1024:
                status = "cached"
                byte_count = local_path.stat().st_size
            else:
                response = session.get(row["pdf_url"], headers=headers, timeout=config.request_timeout_seconds)
                response.raise_for_status()
                local_path.write_bytes(response.content)
                status = "downloaded"
                byte_count = len(response.content)
        except Exception as exc:  # noqa: BLE001
            status = f"download_error:{type(exc).__name__}"
            error = str(exc)
        rows.append({**row, "local_pdf_path": str(local_path), "download_status": status, "byte_count": byte_count, "error": error})
        time.sleep(config.sleep_seconds)
    return rows


def _extract_keyword_hits(download_rows: list[dict[str, Any]], config: ProbeConfig) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in download_rows:
        path = Path(str(row.get("local_pdf_path", "")))
        if not path.exists() or not str(row.get("download_status", "")).startswith(("downloaded", "cached")):
            rows.append({**_hit_identity(row), "field": "pdf_read", "keyword": "", "hit_count": 0, "pages": "", "sample_context": "", "extraction_status": "pdf_unavailable"})
            continue
        try:
            pages = _read_pdf_pages(path, max_pages=config.max_pages_per_pdf)
        except Exception as exc:  # noqa: BLE001
            rows.append({**_hit_identity(row), "field": "pdf_read", "keyword": "", "hit_count": 0, "pages": "", "sample_context": "", "extraction_status": f"pdf_read_error:{type(exc).__name__}"})
            continue
        industry = str(row["industry"])
        for field, keywords in FIELD_KEYWORDS[industry].items():
            for keyword in keywords:
                hits = _keyword_hits_from_pages(pages, keyword)
                rows.append(
                    {
                        **_hit_identity(row),
                        "field": field,
                        "keyword": keyword,
                        "hit_count": len(hits),
                        "pages": ";".join(str(item["page"]) for item in hits[:8]),
                        "sample_context": hits[0]["context"] if hits else "",
                        "extraction_status": "candidate_hit" if hits else "no_hit",
                    }
                )
    return rows


def _read_pdf_pages(path: Path, max_pages: int | None) -> list[tuple[int, str]]:
    import fitz  # type: ignore

    pages: list[tuple[int, str]] = []
    with fitz.open(path) as doc:
        page_count = len(doc) if max_pages is None else min(len(doc), max_pages)
        for index in range(page_count):
            pages.append((index + 1, doc.load_page(index).get_text("text")))
    return pages


def _keyword_hits_from_pages(pages: list[tuple[int, str]], keyword: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for page_no, text in pages:
        for match in re.finditer(re.escape(keyword), text):
            start = max(0, match.start() - 80)
            end = min(len(text), match.end() + 120)
            context = " ".join(text[start:end].split())
            hits.append({"page": page_no, "context": context})
    return hits


def _field_gate(industry: str, keyword_rows: list[dict[str, Any]], annual_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field in FIELD_KEYWORDS[industry]:
        field_rows = [row for row in keyword_rows if row.get("field") == field and row.get("industry") == industry]
        report_count = len({row["code"] for row in field_rows if int(row.get("hit_count") or 0) > 0})
        hit_count = sum(int(row.get("hit_count") or 0) for row in field_rows)
        if hit_count:
            status = "financial_report_candidate_available_needs_original_review"
        elif field in {"capacity_payment", "hydro_water", "deposit_cost"}:
            status = "partial_or_sparse_report_disclosure_external_panel_needed"
        else:
            status = "not_confirmed_in_sample_expand_fetch"
        rows.append(
            {
                "industry": industry,
                "field": field,
                "keyword_set": ";".join(FIELD_KEYWORDS[industry][field]),
                "sample_report_code_hit_count": report_count,
                "sample_keyword_hit_count": hit_count,
                "annual_report_manifest_count": len([row for row in annual_rows if row["industry"] == industry]),
                "gate_status": status,
                "pit_visible_date_required": True,
                "allowed_use": "data_gate_and_candidate_extraction_only",
                "blocked_use": "direct_weight_update_without_review_or_forward_validation",
            }
        )
    return rows


def _fetch_queue(annual_rows: list[dict[str, Any]], keyword_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    downloaded = {row["code"] for row in keyword_rows if row.get("extraction_status") in {"candidate_hit", "no_hit"}}
    queue: list[dict[str, Any]] = []
    for row in annual_rows:
        status = "sample_done" if row["code"] in downloaded else "queued_for_full_batch"
        queue.append(
            {
                "priority": "P1" if row["industry"] in {BANK, POWER} else "P2",
                "industry": row["industry"],
                "code": row["code"],
                "sec_name": row["sec_name"],
                "report_period": row["report_period"],
                "announcement_date": row["announcement_date"],
                "pdf_url": row["pdf_url"],
                "status": status,
                "next_action": "download_pdf_extract_keywords_manual_spot_check" if status != "sample_done" else "review_keyword_candidate_pages",
            }
        )
    return queue


def _pm_decision(bank_gate: list[dict[str, Any]], power_gate: list[dict[str, Any]], blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bank_ready = sum(1 for row in bank_gate if str(row["gate_status"]).startswith("financial_report_candidate_available"))
    power_ready = sum(1 for row in power_gate if str(row["gate_status"]).startswith("financial_report_candidate_available"))
    if bank_ready and power_ready:
        decision = "financial_report_data_gate_pass_to_batch_extraction_not_model_update"
    elif bank_ready or power_ready:
        decision = "financial_report_data_gate_partial_pass_expand_batch_extraction"
    else:
        decision = "financial_report_data_gate_needs_more_sources"
    return [
        {
            "pm_gate_decision": decision,
            "bank_candidate_field_count": bank_ready,
            "power_candidate_field_count": power_ready,
            "nonfatal_blocker_count": len(blockers),
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "next_action": "batch_download_extract_annual_reports_then_manual_spot_check_before_quant_panel",
        }
    ]


def _summary(
    status: str,
    annual_rows: list[dict[str, Any]] | None = None,
    download_rows: list[dict[str, Any]] | None = None,
    keyword_rows: list[dict[str, Any]] | None = None,
    bank_gate: list[dict[str, Any]] | None = None,
    power_gate: list[dict[str, Any]] | None = None,
    pm_gate_decision: str = "blocked_missing_required_inputs",
    blockers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    annual_rows = annual_rows or []
    download_rows = download_rows or []
    keyword_rows = keyword_rows or []
    bank_gate = bank_gate or []
    power_gate = power_gate or []
    blockers = blockers or []
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5c_bank_power_financial_report_data_gate",
        "status": status,
        "source": "CNInfo annual report announcements plus downloaded PDF keyword scan",
        "backtest_end": BACKTEST_END,
        "annual_report_manifest_count": len(annual_rows),
        "sample_pdf_download_count": sum(1 for row in download_rows if str(row.get("download_status", "")).startswith(("downloaded", "cached"))),
        "keyword_candidate_hit_rows": sum(1 for row in keyword_rows if row.get("extraction_status") == "candidate_hit"),
        "bank_candidate_fields": [row["field"] for row in bank_gate if str(row["gate_status"]).startswith("financial_report_candidate_available")],
        "power_candidate_fields": [row["field"] for row in power_gate if str(row["gate_status"]).startswith("financial_report_candidate_available")],
        "can_update_model_now": False,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "pm_gate_decision": pm_gate_decision,
        "fatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "fatal"),
        "blockers": blockers,
    }


def _report(
    bank_gate: list[dict[str, Any]],
    power_gate: list[dict[str, Any]],
    annual_rows: list[dict[str, Any]],
    download_rows: list[dict[str, Any]],
    keyword_rows: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    lines = [
        "# V5c Bank / Power Financial Report Data Gate",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Annual report manifest rows: {len(annual_rows)}",
        f"- Sample PDFs downloaded/cached: {sum(1 for row in download_rows if str(row.get('download_status', '')).startswith(('downloaded', 'cached')))}",
        f"- Keyword candidate hit rows: {sum(1 for row in keyword_rows if row.get('extraction_status') == 'candidate_hit')}",
        "",
        "## Bank Fields",
    ]
    lines.extend([f"- `{row['field']}`: {row['gate_status']} ({row['sample_keyword_hit_count']} hits)" for row in bank_gate])
    lines.append("")
    lines.append("## Power Fields")
    lines.extend([f"- `{row['field']}`: {row['gate_status']} ({row['sample_keyword_hit_count']} hits)" for row in power_gate])
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This packet confirms financial-report availability and candidate pages only. It is not a model update, not accepted, and not live approved.",
        ]
    )
    return "\n".join(lines)


def _rules() -> str:
    return "\n".join(
        [
            "# V5c Bank / Power Financial Report Data Gate Rules",
            "",
            "- Use annual reports as PIT source candidates only.",
            "- Keep announcement_date as visible date.",
            "- Keyword hits require original-page review before becoming a Quant panel field.",
            "- Do not update weights from this packet.",
            "- Do not mark accepted or live approved.",
            "- Do not modify V57f core or V5f primary.",
            "",
        ]
    )


def _hit_identity(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "industry": row.get("industry", ""),
        "code": row.get("code", ""),
        "sec_name": row.get("sec_name", ""),
        "report_period": row.get("report_period", ""),
        "announcement_date": row.get("announcement_date", ""),
        "local_pdf_path": row.get("local_pdf_path", ""),
        "pdf_url": row.get("pdf_url", ""),
    }


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def _infer_report_period(title: str, announcement_date: str) -> str:
    match = re.search(r"(20\d{2})年年度报告", title)
    if match:
        return f"{match.group(1)}-12-31"
    if announcement_date:
        year = int(announcement_date[:4]) - 1
        return f"{year}-12-31"
    return ""


def _ms_to_date(value: Any) -> str:
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return ""


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [root / REPAIRED_RUN / "rebalance_signals.csv"]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not path.exists()
    ]


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    run()

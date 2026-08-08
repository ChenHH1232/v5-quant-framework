from __future__ import annotations

import csv
import json
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


OUT = Path("v5j_material_corporate_action_notice_repair") / "current"
SOURCE = Path("v5j_local_adjust_factor_corporate_action") / "current" / "v5j_adjust_factor_corporate_action_reconciliation.csv"
SEARCH = "http://www.cninfo.com.cn/new/information/topSearch/query"
ANNOUNCEMENTS = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
STATIC = "http://static.cninfo.com.cn/"
MATERIAL_THRESHOLD = 0.01

KEYWORDS = {
    "cash_dividend_or_ex_right": ("分红", "派息", "除权", "除息", "权益分派", "利润分配"),
    "stock_dividend_or_conversion": ("送股", "转增", "转股", "资本公积"),
    "rights_issue": ("配股", "供股", "优先股"),
    "restructuring_or_merger": ("重组", "合并", "吸收合并", "资产置换", "重大资产"),
    "listing_or_terminal": ("停牌", "复牌", "终止上市", "退市", "恢复上市"),
    "share_capital_change": ("股份变动", "股本", "增发", "定向发行"),
}


def run_v5j_material_corporate_action_notice_repair(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    source = root / SOURCE
    if not source.exists():
        raise FileNotFoundError(f"Missing adjustment-factor reconciliation: {source}")

    events = [
        row for row in _read_csv(source)
        if row.get("reconciliation_status") == "effective_factor_event_recorded_no_dividend_match"
        and abs(_number(row.get("factor_change_ratio"))) >= MATERIAL_THRESHOLD
    ]
    manifest, query_audit = _build_manifest(events)
    candidates = _classify_candidates(manifest)
    review = _review_matrix(events, candidates)
    blockers = _blockers(review, query_audit)
    summary = {
        "created_at_utc": _now(),
        "task": "v5j_material_corporate_action_notice_repair",
        "material_factor_event_count": len(events),
        "notice_candidate_count": len(candidates),
        "events_with_notice_candidates": sum(row["notice_candidate_count"] > 0 for row in review),
        "events_ready_for_original_terms_review": sum(row["review_status"] == "needs_original_notice_terms_review" for row in review),
        "events_without_candidate_notice": sum(row["review_status"] == "no_candidate_notice_found" for row in review),
        "status": "original_notice_candidates_ready_for_review",
        "accepted": False,
        "v57f_core_modified": False,
        "strategy_backtest_started": False,
    }
    _write_csv(out / "v5j_material_factor_event_scope.csv", events)
    _write_csv(out / "v5j_material_action_notice_manifest.csv", manifest)
    _write_csv(out / "v5j_material_action_notice_candidates.csv", candidates)
    _write_csv(out / "v5j_material_action_original_terms_review_matrix.csv", review)
    _write_csv(out / "v5j_material_action_query_audit.csv", query_audit)
    _write_csv(out / "v5j_material_action_blockers.csv", blockers)
    (out / "v5j_material_action_notice_repair_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "v5j_material_action_notice_repair_report.md").write_text(_report(summary, blockers), encoding="utf-8")
    return summary


def _build_manifest(events: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "http://www.cninfo.com.cn/"}
    records: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    org_cache: dict[str, str] = {}
    for event in events:
        code = event["code"]
        plain = code.split(".")[0]
        try:
            org_id = org_cache.get(code) or _org_id(session, headers, plain)
            org_cache[code] = org_id
            if not org_id:
                audit.append({"code": code, "effective_factor_date": event["effective_factor_date"], "status": "org_id_missing"})
                continue
            day = date.fromisoformat(event["effective_factor_date"])
            start, end = day - timedelta(days=100), day + timedelta(days=10)
            data = session.post(
                ANNOUNCEMENTS,
                headers=headers,
                data={
                    "pageNum": 1, "pageSize": 100, "column": "sse" if code.endswith("XSHG") else "szse",
                    "tabName": "fulltext", "plate": "", "stock": f"{plain},{org_id}", "searchkey": "", "secid": "",
                    "category": "", "trade": "", "seDate": f"{start.isoformat()}~{end.isoformat()}",
                    "sortName": "", "sortType": "", "isHLtitle": "true",
                },
                timeout=25,
            ).json()
            count = 0
            for notice in data.get("announcements") or []:
                title = re.sub(r"<[^>]+>", "", str(notice.get("announcementTitle") or ""))
                if not _keyword_types(title):
                    continue
                adjunct = str(notice.get("adjunctUrl") or "")
                records.append({
                    "event_id": f"{code}|{event['effective_factor_date']}", "code": code,
                    "effective_factor_date": event["effective_factor_date"], "factor_change_ratio": event["factor_change_ratio"],
                    "announcement_title": title, "announcement_visible_date": _date_ms(notice.get("announcementTime")),
                    "announcement_url": STATIC + adjunct if adjunct else "", "adjunct_url": adjunct,
                    "candidate_types": ";".join(_keyword_types(title)), "source": "cninfo_original_notice_manifest",
                    "original_terms_review_status": "needs_original_notice_terms_review", "accepted": False,
                })
                count += 1
            audit.append({"code": code, "effective_factor_date": event["effective_factor_date"], "status": "pass", "candidate_notice_count": count})
        except Exception as exc:  # noqa: BLE001
            audit.append({"code": code, "effective_factor_date": event["effective_factor_date"], "status": f"query_error:{type(exc).__name__}", "detail": str(exc)})
        time.sleep(0.12)
    return records, audit


def _org_id(session: requests.Session, headers: dict[str, str], plain: str) -> str:
    rows = session.post(SEARCH, headers=headers, data={"keyWord": plain, "maxNum": 10}, timeout=25).json()
    return next((str(row.get("orgId")) for row in rows if str(row.get("code")) == plain and row.get("orgId")), "")


def _keyword_types(title: str) -> list[str]:
    return [kind for kind, words in KEYWORDS.items() if any(word in title for word in words)]


def _classify_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (row["code"], row["effective_factor_date"], row["announcement_visible_date"], row["announcement_title"]))


def _review_matrix(events: list[dict[str, str]], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_event: dict[str, list[dict[str, Any]]] = {}
    for row in candidates:
        by_event.setdefault(row["event_id"], []).append(row)
    result = []
    for event in events:
        event_id = f"{event['code']}|{event['effective_factor_date']}"
        notices = by_event.get(event_id, [])
        result.append({
            "event_id": event_id, "code": event["code"], "effective_factor_date": event["effective_factor_date"],
            "factor_change_ratio": event["factor_change_ratio"], "notice_candidate_count": len(notices),
            "candidate_types": ";".join(sorted({item["candidate_types"] for item in notices if item["candidate_types"]})),
            "earliest_notice_visible_date": min((item["announcement_visible_date"] for item in notices), default=""),
            "review_status": "needs_original_notice_terms_review" if notices else "no_candidate_notice_found",
            "terms_inferred_from_factor": False, "usable_for_total_return": False, "accepted": False,
        })
    return result


def _blockers(review: list[dict[str, Any]], audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers = []
    no_notice = sum(row["review_status"] == "no_candidate_notice_found" for row in review)
    pending = sum(row["review_status"] == "needs_original_notice_terms_review" for row in review)
    if no_notice:
        blockers.append({"blocker_id": "material_action_notice_not_found", "severity": "blocking_for_total_return_reconciliation", "detail": f"{no_notice} material events have no title-level candidate notice."})
    if pending:
        blockers.append({"blocker_id": "material_action_original_terms_unreviewed", "severity": "blocking_for_total_return_reconciliation", "detail": f"{pending} material events require original-notice term, date, and treatment review."})
    if any(str(row.get("status", "")).startswith("query_error") for row in audit):
        blockers.append({"blocker_id": "cninfo_notice_query_error", "severity": "review", "detail": "At least one notice query failed; retry only those event IDs."})
    return blockers


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


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


def _report(summary: dict[str, Any], blockers: list[dict[str, Any]]) -> str:
    rows = ["# Material corporate-action original-notice repair", "", f"- Material unmatched factor events: `{summary['material_factor_event_count']}`.", f"- Events with title-level notice candidates: `{summary['events_with_notice_candidates']}`.", "- Adjustment-factor changes never supply inferred action terms; each candidate remains original-notice review only.", ""]
    rows.extend(f"- `{item['blocker_id']}`: {item['detail']}" for item in blockers)
    return "\n".join(rows) + "\n"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    print(json.dumps(run_v5j_material_corporate_action_notice_repair(), ensure_ascii=False, indent=2))

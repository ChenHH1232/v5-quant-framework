from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file


API_BASE_URL = "https://api.fxbaogao.com"
DEFAULT_VAULT_PATH = Path(r"D:\hh\保险箱\重要凭据.txt")


HttpPost = Callable[[str, dict[str, Any], str], dict[str, Any]]

FALLBACK_VAULT_PATHS = [
    Path(r"D:\hh\保险箱\重要凭据.txt"),
]

DEFAULT_REPORT_EXCLUDE_KEYWORDS = [
    "日报",
    "周报",
    "月报",
    "晨会",
    "快评",
    "简评",
    "点评",
    "业绩点评",
    "财报点评",
    "半年度报告",
    "年度报告",
    "季报",
    "估值表",
    "基金净值",
    "新发基金",
    "周观点",
    "每日",
    "双周报",
]

DEFAULT_REPORT_PREFERRED_KEYWORDS = [
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


def collect_fxbaogao_report_search(
    keywords: str,
    out_dir: Path,
    *,
    org_names: list[str] | None = None,
    start_time: str | None = None,
    end_time: str | None = "last1year",
    vault_path: Path = DEFAULT_VAULT_PATH,
    http_post: HttpPost | None = None,
) -> Path:
    api_key = load_fxbaogao_api_key(vault_path)
    payload: dict[str, Any] = {
        "keywords": keywords,
        "orgNames": org_names or [],
    }
    if start_time:
        payload["startTime"] = start_time
    if end_time:
        payload["endTime"] = end_time

    post = http_post or _post_json
    response = post("/mofoun/agent/search", payload, api_key)
    reports = _normalize_search_response(response)

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json_file(out_dir / "raw_search_response.json", response, encoding="utf-8-sig")
    write_csv_rows(
        out_dir / "report_candidates.csv",
        [
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
        reports,
        encoding="utf-8-sig",
    )
    write_json_file(
        out_dir / "collection_manifest.json",
        {
            "source": "fxbaogao",
            "api_base_url": API_BASE_URL,
            "keywords": keywords,
            "org_names": org_names or [],
            "start_time": start_time,
            "end_time": end_time,
            "status": "completed",
            "report_count": len(reports),
            "outputs": [
                "raw_search_response.json",
                "report_candidates.csv",
                "collection_manifest.json",
            ],
            "credential_policy": "api key loaded from environment or vault; never written to output files",
            "pit_policy": "research reports are knowledge sources only; any financial field still requires original announcement date before PIT validation",
        },
        encoding="utf-8-sig",
    )
    return out_dir / "collection_manifest.json"


def fetch_fxbaogao_paragraphs(
    report_id: int,
    keyword: str,
    out_dir: Path,
    *,
    vault_path: Path = DEFAULT_VAULT_PATH,
    http_post: HttpPost | None = None,
) -> Path:
    api_key = load_fxbaogao_api_key(vault_path)
    post = http_post or _post_json
    response = post("/mofoun/agent/paragraph", {"reportId": report_id, "keyword": keyword}, api_key)
    data = response.get("data") or {}
    paragraphs = data.get("paragraphs") or []
    rows = []
    for item in paragraphs:
        rows.append(
            {
                "report_id": report_id,
                "keyword": keyword,
                "title": data.get("title", ""),
                "summary": data.get("summary", ""),
                "page_num": item.get("pageNum", ""),
                "content": item.get("content", ""),
                "view_url": f"https://www.fxbaogao.com/view?id={report_id}",
            }
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json_file(out_dir / f"report_{report_id}_paragraph_raw.json", response, encoding="utf-8-sig")
    write_csv_rows(
        out_dir / f"report_{report_id}_paragraphs.csv",
        ["report_id", "keyword", "title", "summary", "page_num", "content", "view_url"],
        rows,
        encoding="utf-8-sig",
    )
    return out_dir / f"report_{report_id}_paragraphs.csv"


def filter_fxbaogao_report_candidates(
    candidate_csvs: list[Path],
    out_dir: Path,
    *,
    include_any: list[str] | None = None,
    include_all: list[str] | None = None,
    exclude_keywords: list[str] | None = None,
    preferred_keywords: list[str] | None = None,
    top_k: int | None = None,
) -> Path:
    include_any = _clean_keywords(include_any)
    include_all = _clean_keywords(include_all)
    exclude_keywords = _clean_keywords(exclude_keywords) or DEFAULT_REPORT_EXCLUDE_KEYWORDS
    preferred_keywords = _clean_keywords(preferred_keywords) or DEFAULT_REPORT_PREFERRED_KEYWORDS

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen_report_ids: set[str] = set()

    for csv_path in candidate_csvs:
        for row in read_csv_rows(csv_path):
            report_id = str(row.get("report_id") or "")
            dedupe_key = report_id or f"{row.get('title', '')}|{row.get('org_name', '')}|{row.get('pub_time_str', '')}"
            if dedupe_key in seen_report_ids:
                continue
            seen_report_ids.add(dedupe_key)
            decision = _score_candidate(row, include_any, include_all, exclude_keywords, preferred_keywords)
            output_row = {
                **row,
                "source_candidate_csv": str(csv_path),
                "local_relevance_score": decision["score"],
                "matched_title_keywords": ";".join(decision["matched_title_keywords"]),
                "matched_preferred_keywords": ";".join(decision["matched_preferred_keywords"]),
                "rejection_reason": decision["rejection_reason"],
                "stage1_title_filter_passed": "yes" if decision["accepted"] else "no",
                "next_stage": "fetch_paragraph_or_pdf_then_local_rerank"
                if decision["accepted"]
                else "do_not_use_for_knowledge_cards",
            }
            if decision["accepted"]:
                accepted.append(output_row)
            else:
                rejected.append(output_row)

    accepted.sort(
        key=lambda row: (
            -float(row["local_relevance_score"]),
            str(row.get("pub_time_str") or ""),
            str(row.get("report_id") or ""),
        )
    )
    if top_k is not None:
        accepted = accepted[:top_k]

    out_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "report_id",
        "title",
        "org_name",
        "industry_name",
        "page_num",
        "pub_time",
        "pub_time_str",
        "view_url",
        "paragraph_hit_count",
        "source_candidate_csv",
        "local_relevance_score",
        "matched_title_keywords",
        "matched_preferred_keywords",
        "rejection_reason",
        "stage1_title_filter_passed",
        "next_stage",
    ]
    write_csv_rows(out_dir / "filtered_report_candidates.csv", fieldnames, accepted, encoding="utf-8-sig")
    write_csv_rows(out_dir / "rejected_report_candidates.csv", fieldnames, rejected, encoding="utf-8-sig")
    write_json_file(
        out_dir / "filter_manifest.json",
        {
            "source": "fxbaogao_local_stage1_filter",
            "candidate_csvs": [str(path) for path in candidate_csvs],
            "include_any": include_any,
            "include_all": include_all,
            "exclude_keywords": exclude_keywords,
            "preferred_keywords": preferred_keywords,
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "top_k": top_k,
            "policy": (
                "Stage 1 only: narrow keywords plus title filtering. Accepted rows are source leads, "
                "not evidence cards, until paragraph/PDF review."
            ),
            "outputs": [
                "filtered_report_candidates.csv",
                "rejected_report_candidates.csv",
                "filter_manifest.json",
            ],
        },
        encoding="utf-8-sig",
    )
    return out_dir / "filter_manifest.json"


def load_fxbaogao_api_key(vault_path: Path = DEFAULT_VAULT_PATH) -> str:
    env_key = os.environ.get("FXBAOGAO_API_KEY", "").strip()
    if env_key:
        return env_key
    if not vault_path.exists():
        for fallback_path in FALLBACK_VAULT_PATHS:
            if fallback_path.exists():
                vault_path = fallback_path
                break
    if not vault_path.exists():
        raise RuntimeError("missing FXBAOGAO_API_KEY and vault credential file")
    current_section = ""
    for raw_line in vault_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if line.startswith("[") and line.endswith("]"):
            current_section = line.strip("[]").lower()
            continue
        if current_section == "fxbaogao" and line.lower().startswith("api_key"):
            _name, _sep, value = line.partition("=")
            key = value.strip()
            if key:
                return key
    raise RuntimeError("missing fxbaogao api_key in vault credential file")


def _clean_keywords(values: list[str] | None) -> list[str]:
    if not values:
        return []
    output: list[str] = []
    for value in values:
        for part in str(value).replace(",", ";").split(";"):
            term = part.strip()
            if term:
                output.append(term)
    return output


def _score_candidate(
    row: dict[str, str],
    include_any: list[str],
    include_all: list[str],
    exclude_keywords: list[str],
    preferred_keywords: list[str],
) -> dict[str, Any]:
    title = str(row.get("title") or "")
    title_lower = title.lower()
    excluded = [term for term in exclude_keywords if term and term.lower() in title_lower]
    if excluded:
        return {
            "accepted": False,
            "score": 0,
            "matched_title_keywords": [],
            "matched_preferred_keywords": [],
            "rejection_reason": f"title_excluded:{';'.join(excluded)}",
        }

    all_missing = [term for term in include_all if term and term.lower() not in title_lower]
    if all_missing:
        return {
            "accepted": False,
            "score": 0,
            "matched_title_keywords": [],
            "matched_preferred_keywords": [],
            "rejection_reason": f"title_missing_required:{';'.join(all_missing)}",
        }

    matched_any = [term for term in include_any if term and term.lower() in title_lower]
    if include_any and not matched_any:
        return {
            "accepted": False,
            "score": 0,
            "matched_title_keywords": [],
            "matched_preferred_keywords": [],
            "rejection_reason": "title_missing_any_include_keyword",
        }

    matched_preferred = [term for term in preferred_keywords if term and term.lower() in title_lower]
    paragraph_hits = _to_int(row.get("paragraph_hit_count"))
    page_num = _to_int(row.get("page_num"))
    score = len(matched_any) * 3 + len(include_all) * 4 + len(matched_preferred) * 2
    if paragraph_hits > 0:
        score += 1
    if page_num >= 15:
        score += 1
    if not include_any and not include_all and not matched_preferred:
        return {
            "accepted": False,
            "score": 0,
            "matched_title_keywords": [],
            "matched_preferred_keywords": [],
            "rejection_reason": "no_positive_title_signal",
        }
    return {
        "accepted": True,
        "score": score,
        "matched_title_keywords": matched_any + include_all,
        "matched_preferred_keywords": matched_preferred,
        "rejection_reason": "",
    }


def _to_int(value: Any) -> int:
    try:
        return int(float(str(value or "0")))
    except ValueError:
        return 0


def _post_json(path: str, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
    url = urllib.parse.urljoin(API_BASE_URL, path)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"fxbaogao API HTTP error: {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"fxbaogao API network error: {exc.reason}") from exc


def _normalize_search_response(response: dict[str, Any]) -> list[dict[str, Any]]:
    if response.get("code") != 0:
        raise RuntimeError(f"fxbaogao API returned non-zero code: {response.get('msg')}")
    rows = []
    for item in response.get("data") or []:
        report_id = item.get("reportId")
        rows.append(
            {
                "report_id": report_id,
                "title": _strip_html(str(item.get("title") or "")),
                "org_name": _strip_html(str(item.get("orgName") or "")),
                "industry_name": item.get("industryName") or "",
                "page_num": item.get("pageNum") or "",
                "pub_time": item.get("pubTime") or "",
                "pub_time_str": item.get("pubTimeStr") or "",
                "view_url": f"https://www.fxbaogao.com/view?id={report_id}" if report_id else "",
                "paragraph_hit_count": len(item.get("paragraphs") or []),
            }
        )
    return rows


def _strip_html(value: str) -> str:
    return value.replace("<em>", "").replace("</em>", "")

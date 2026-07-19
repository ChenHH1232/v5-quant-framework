from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from v5.io_utils import write_csv_rows, write_json_file


API_BASE_URL = "https://api.fxbaogao.com"
DEFAULT_VAULT_PATH = Path(r"D:\hh\保险箱\重要凭据.txt")


HttpPost = Callable[[str, dict[str, Any], str], dict[str, Any]]


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


def load_fxbaogao_api_key(vault_path: Path = DEFAULT_VAULT_PATH) -> str:
    env_key = os.environ.get("FXBAOGAO_API_KEY", "").strip()
    if env_key:
        return env_key
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

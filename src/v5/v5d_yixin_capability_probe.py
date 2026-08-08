from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parents[2]
OUTPUT_DIR = WORKSPACE / "v5d_yixin_api_capability_probe" / "current"


def call_yixin(path: str, payload: dict[str, Any], timeout: int = 120) -> dict[str, Any]:
    api_key = os.environ.get("YIXIN_API_KEY")
    if not api_key:
        return {
            "status": "missing_key",
            "http_status": None,
            "elapsed_sec": 0,
            "body_preview": "",
            "error_type": "MissingEnvironmentVariable",
            "error_message": "YIXIN_API_KEY is not set",
        }
    url = f"https://openapi.billionsintelligence.com{path}"
    started = time.perf_counter()
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-KEY": api_key,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return {
                "status": "http_ok",
                "http_status": response.status,
                "elapsed_sec": round(time.perf_counter() - started, 3),
                "body_preview": raw[:4000],
                "error_type": "",
                "error_message": "",
            }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        message = "额度已用完，请联系销售升级：https://www.billionsintelligence.com" if exc.code == 429 else body[:1000]
        return {
            "status": "http_error",
            "http_status": exc.code,
            "elapsed_sec": round(time.perf_counter() - started, 3),
            "body_preview": body[:4000],
            "error_type": "HTTPError",
            "error_message": message,
        }
    except Exception as exc:
        return {
            "status": "request_error",
            "http_status": None,
            "elapsed_sec": round(time.perf_counter() - started, 3),
            "body_preview": "",
            "error_type": type(exc).__name__,
            "error_message": str(exc)[:1000],
        }


def safe_parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return None


def classify_minute_capability(result: dict[str, Any]) -> str:
    parsed = safe_parse_json(result.get("body_preview", ""))
    text = json.dumps(parsed, ensure_ascii=False) if parsed is not None else str(result.get("body_preview", ""))
    if result["status"] != "http_ok":
        return "blocked_api_call_failed"
    positive_terms = ["分钟", "1分钟", "minute", "OHLC", "成交量", "成交额", "A股"]
    if any(term in text for term in positive_terms):
        return "needs_manual_schema_review"
    return "no_direct_minute_capability_confirmed"


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    probes = [
        {
            "probe_id": "search_report_smoke",
            "api": "search",
            "path": "/api/v2/search",
            "purpose": "Confirm key and report/internet search gateway availability",
            "payload": {
                "query": "A股 分钟线 历史行情 数据源",
                "source": "web",
                "search_mode": "fast",
                "count": 3,
                "timeout": 30,
            },
        },
        {
            "probe_id": "fin_db_minute_capability",
            "api": "fin_db",
            "path": "/api/v1/fin_db",
            "purpose": "Ask whether the database service can provide historical A-share 1-minute OHLCV data for a fixed code/date",
            "payload": {
                "query": "请检查数据库是否可以提供A股股票600795在2024-10-08的1分钟历史行情数据，字段至少包括时间、开盘、最高、最低、收盘、成交量、成交额。只回答是否可直接返回数据以及可用字段。",
                "data_sources": ["auto"],
            },
        },
        {
            "probe_id": "fin_db_daily_smoke",
            "api": "fin_db",
            "path": "/api/v1/fin_db",
            "purpose": "Check whether fin_db can answer a simpler A-share daily data query",
            "payload": {
                "query": "查询600795.SH在2024-10-08的A股日线收盘价和成交额。",
                "data_sources": ["auto"],
            },
        },
        {
            "probe_id": "fin_db_minute_short_query",
            "api": "fin_db",
            "path": "/api/v1/fin_db",
            "purpose": "Check whether a shorter minute query can be planned",
            "payload": {
                "query": "600795.SH 2024-10-08 1分钟行情",
                "data_sources": ["auto"],
            },
        },
    ]
    result_rows = []
    raw_results: dict[str, Any] = {}
    for probe in probes:
        result = call_yixin(probe["path"], probe["payload"])
        raw_results[probe["probe_id"]] = {
            "api": probe["api"],
            "purpose": probe["purpose"],
            "payload_without_key": probe["payload"],
            "result": result,
        }
        result_rows.append(
            {
                "probe_id": probe["probe_id"],
                "api": probe["api"],
                "purpose": probe["purpose"],
                "status": result["status"],
                "http_status": result["http_status"],
                "elapsed_sec": result["elapsed_sec"],
                "minute_capability_read": classify_minute_capability(result) if probe["api"] == "fin_db" else "not_applicable",
                "error_type": result["error_type"],
                "error_message": result["error_message"],
            }
        )
    write_csv(OUTPUT_DIR / "v5d_yixin_api_probe_results.csv", result_rows)
    (OUTPUT_DIR / "v5d_yixin_api_raw_response_redacted.json").write_text(
        json.dumps(raw_results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fin_rows = [row for row in result_rows if row["api"] == "fin_db"]
    minute_rows = [row for row in fin_rows if "minute" in row["probe_id"]]
    any_fin_ok = any(row["status"] == "http_ok" for row in fin_rows)
    any_minute_ok = any(row["status"] == "http_ok" for row in minute_rows)
    fin_row = minute_rows[0]
    if not any_fin_ok:
        status = "blocked_yixin_api_call_failed"
    elif any_minute_ok:
        status = "yixin_api_connected_minute_capability_needs_schema_review"
    else:
        status = "yixin_fin_db_connected_but_minute_query_not_confirmed"
    capability_matrix = [
        {
            "route": "yixin_search",
            "fit_for_v5d": "source_discovery_only",
            "status": next(row for row in result_rows if row["probe_id"] == "search_report_smoke")["status"],
            "can_replace_minute_vendor": "no",
            "notes": "Search can help locate data vendors or documents, but does not itself provide audited 1m OHLCV.",
        },
        {
            "route": "yixin_fin_db",
            "fit_for_v5d": "unknown_until_schema_confirmed",
            "status": "some_fin_db_ok" if any_fin_ok else "fin_db_not_ok",
            "can_replace_minute_vendor": "unknown",
            "notes": "Requires schema-level confirmation that A-share historical 1m OHLCV is available for 2021-10-08 to 2026-05-31.",
        },
    ]
    write_csv(OUTPUT_DIR / "v5d_yixin_minute_capability_matrix.csv", capability_matrix)
    next_actions = [
        {
            "priority": "1",
            "action": "review_fin_db_response_schema",
            "condition": "Only proceed if the response exposes a real minute OHLCV dataset or a documented table/API path.",
            "blocked_if": "The response is narrative only or lacks historical minute fields.",
        },
        {
            "priority": "2",
            "action": "request_exact_yixin_database_schema_if_needed",
            "condition": "Ask for database/table names, date/code filters, row limits, and export method.",
            "blocked_if": "No schema/documented endpoint for historical A-share 1m data.",
        },
        {
            "priority": "3",
            "action": "keep_akshare_baostock_result_as_free_source_failed_probe",
            "condition": "Do not rerun broad free-source pulls without a new data path.",
            "blocked_if": "N/A",
        },
    ]
    write_csv(OUTPUT_DIR / "v5d_yixin_next_actions.csv", next_actions)
    summary = {
        "schema_version": 1,
        "project": "v5d_yixin_api_capability_probe",
        "created_at_local": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "api_key_policy": "API key was read only from process environment and was not written to outputs.",
        "v57f_core_modified": False,
        "joinquant_started": False,
        "minute_timing_optimization_started": False,
        "outputs": {
            "summary": "v5d_yixin_api_capability_probe/current/v5d_yixin_api_capability_summary.json",
            "report": "v5d_yixin_api_capability_probe/current/v5d_yixin_api_capability_report.md",
            "probe_results": "v5d_yixin_api_capability_probe/current/v5d_yixin_api_probe_results.csv",
            "redacted_raw_response": "v5d_yixin_api_capability_probe/current/v5d_yixin_api_raw_response_redacted.json",
            "minute_capability_matrix": "v5d_yixin_api_capability_probe/current/v5d_yixin_minute_capability_matrix.csv",
            "next_actions": "v5d_yixin_api_capability_probe/current/v5d_yixin_next_actions.csv",
        },
    }
    (OUTPUT_DIR / "v5d_yixin_api_capability_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report = [
        "# V5d Yixin API Capability Probe",
        "",
        "## Conclusion",
        f"- Status: `{status}`",
        "- The API key is not written to any output.",
        "- V57f is unchanged; no JoinQuant or minute timing optimization was started.",
        "",
        "## Probe Results",
    ]
    for row in result_rows:
        report.append(
            f"- {row['probe_id']}: status={row['status']}, http={row['http_status']}, "
            f"minute_read={row['minute_capability_read']}, error={row['error_type']}"
        )
    report.extend(["", "## Next Actions"])
    for row in next_actions:
        report.append(f"- P{row['priority']}: {row['action']} ({row['condition']})")
    (OUTPUT_DIR / "v5d_yixin_api_capability_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import csv
import json
import math
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path("v5c_bank_special_mention_pre2021_train_test") / "current"
SPLIT_DIR = Path("v5_sample_split_governance_correction") / "current"
PREVIEW_DIR = Path("v5f_pre2021_repaired_multisleeve_data_gate") / "current"
BACKTEST_RESULT_DIR = Path("v5c_bank_power_single_factor_cross_section_test") / "current"
BANK_PANEL = Path("\u6570\u636e\u5e93") / "processed" / "startup_preload_repaired_panels_v5" / "bank_v3_repaired" / "panel_with_low_vol.csv"

CNINFO_SEARCH_URL = "http://www.cninfo.com.cn/new/information/topSearch/query"
CNINFO_ANNOUNCE_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_STATIC_BASE = "http://static.cninfo.com.cn/"

TRAIN_START = "2013-01-01"
TRAIN_END = "2021-04-30"
FORMAL_BACKTEST_START = "2021-05-01"
FORMAL_BACKTEST_END = "2026-05-31"
FACTOR_ID = "bank_special_mention_loan"
VERSION_ID = "pre2021_bank_special_mention_loan_equal_10pct_overlay"
BACKTEST_POSITIVE_VERSION_ID = "single_factor_bank_special_mention_loan_overlay_10pct"
BASELINE = "v57f_startup_preload_repaired_baseline"
PRIMARY = "internal_subsleeve_mom12_70_30"


@dataclass(frozen=True)
class Pre2021Config:
    request_timeout_seconds: int = 20
    sleep_seconds: float = 0.05
    max_codes: int | None = None
    max_reports: int | None = None
    download_missing: bool = True
    reuse_cached_manifest: bool = True
    reuse_cached_extraction: bool = True


def run(root: Path = ROOT, config: Pre2021Config | None = None) -> Path:
    config = config or Pre2021Config()
    out = root / OUT_DIR
    pdf_dir = out / "pdf"
    out.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5c_bank_special_mention_pre2021_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_inputs", blockers=blockers)
        _write_json(out / "v5c_bank_special_mention_pre2021_summary.json", summary)
        return out / "v5c_bank_special_mention_pre2021_summary.json"

    bank_panel = _load_bank_panel(root)
    preview = pd.read_csv(root / PREVIEW_DIR / "v5f_pre2021_candidate_signal_preview.csv", dtype=str)
    backtest_summary = _read_json(root / BACKTEST_RESULT_DIR / "v5c_bank_power_single_factor_summary.json")
    bank_codes = sorted(bank_panel["code"].dropna().unique().tolist())
    if config.max_codes is not None:
        bank_codes = bank_codes[: config.max_codes]

    manifest_path = out / "v5c_bank_special_mention_pre2021_cninfo_manifest.csv"
    if config.reuse_cached_manifest and manifest_path.exists():
        manifest_rows = _read_csv(manifest_path)
    else:
        manifest_rows, manifest_blockers = _build_cninfo_manifest(bank_codes, config)
        blockers.extend(manifest_blockers)
        _write_csv(manifest_path, manifest_rows)

    if config.max_reports is not None:
        manifest_for_extraction = manifest_rows[: config.max_reports]
    else:
        manifest_for_extraction = manifest_rows

    extraction_path = out / "v5c_bank_special_mention_pre2021_extraction_panel.csv"
    if config.reuse_cached_extraction and extraction_path.exists():
        extraction_rows = _read_csv(extraction_path)
        download_rows = _read_csv(out / "v5c_bank_special_mention_pre2021_download_manifest.csv") if (out / "v5c_bank_special_mention_pre2021_download_manifest.csv").exists() else []
    else:
        download_rows, download_blockers = _download_or_resolve(manifest_for_extraction, pdf_dir, config)
        blockers.extend(download_blockers)
        extraction_rows, extraction_blockers = _extract_special_mention_panel(download_rows)
        blockers.extend(extraction_blockers)
        _write_csv(out / "v5c_bank_special_mention_pre2021_download_manifest.csv", download_rows)
        _write_csv(extraction_path, extraction_rows)

    pit_panel = _build_pit_panel(bank_panel, extraction_rows)
    bucket_rows = _bucket_results(pit_panel, "bank_sleeve_train_test")
    overlay_rows = _overlay_results(pit_panel, "bank_sleeve_train_test")
    strict_panel = _strict_preview_panel(preview, pit_panel)
    strict_bucket = _bucket_results(strict_panel, "strict_multisleeve_preview_bank_subset")
    strict_overlay = _overlay_results(strict_panel, "strict_multisleeve_preview_bank_subset")
    coverage = _coverage_rows(bank_panel, pit_panel, strict_panel, extraction_rows, manifest_rows)
    governance = _governance_audit(bank_panel, preview, pit_panel, strict_panel, blockers)
    reconciliation = _backtest_reconciliation(backtest_summary, overlay_rows, strict_overlay)
    decision = _pm_decision(coverage, governance, bucket_rows, overlay_rows, strict_bucket, strict_overlay)
    queue = _next_queue(decision, coverage, reconciliation)
    blockers_out = _blockers(blockers, governance, coverage)

    _write_csv(out / "v5c_bank_special_mention_pre2021_pit_panel.csv", pit_panel)
    _write_csv(out / "v5c_bank_special_mention_pre2021_bucket_result.csv", bucket_rows)
    _write_csv(out / "v5c_bank_special_mention_pre2021_overlay_result.csv", overlay_rows)
    _write_csv(out / "v5c_bank_special_mention_pre2021_strict_preview_panel.csv", strict_panel)
    _write_csv(out / "v5c_bank_special_mention_pre2021_strict_preview_result.csv", strict_bucket + strict_overlay)
    _write_csv(out / "v5c_bank_special_mention_pre2021_coverage_audit.csv", coverage)
    _write_csv(out / "v5c_bank_special_mention_pre2021_governance_audit.csv", governance)
    _write_csv(out / "v5c_bank_special_mention_pre2021_backtest_scope_reconciliation.csv", reconciliation)
    _write_csv(out / "v5c_bank_special_mention_pre2021_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_bank_special_mention_pre2021_next_queue.csv", queue)
    _write_csv(out / "v5c_bank_special_mention_pre2021_blockers.csv", blockers_out)
    (out / "v5c_bank_special_mention_pre2021_report.md").write_text(
        _report(coverage, bucket_rows, overlay_rows, strict_bucket, strict_overlay, reconciliation, decision),
        encoding="utf-8",
    )
    (out / "v5c_bank_special_mention_pre2021_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    best_overlay = overlay_rows[0] if overlay_rows else {}
    strict = strict_overlay[0] if strict_overlay else {}
    summary = _summary(
        "completed_pre2021_train_test_packet",
        train_observation_count=int(best_overlay.get("period_count", 0) or 0),
        strict_observation_count=int(strict.get("period_count", 0) or 0),
        train_delta_pct_points=float(best_overlay.get("delta_cumulative_return_pct_points_vs_equal_weight", 0.0) or 0.0),
        strict_delta_pct_points=float(strict.get("delta_cumulative_return_pct_points_vs_equal_weight", 0.0) or 0.0),
        pm_gate_decision=decision[0]["pm_gate_decision"],
        blockers=blockers_out,
    )
    _write_json(out / "v5c_bank_special_mention_pre2021_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return out / "v5c_bank_special_mention_pre2021_summary.json"


def _load_bank_panel(root: Path) -> pd.DataFrame:
    panel = pd.read_csv(root / BANK_PANEL, dtype={"trade_date": str, "code": str})
    panel = panel[(panel["trade_date"] >= TRAIN_START) & (panel["trade_date"] <= TRAIN_END)].copy()
    panel["future_return"] = pd.to_numeric(panel["future_return"], errors="coerce")
    return panel


def _build_cninfo_manifest(codes: list[str], config: Pre2021Config) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search",
    }
    rows: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for code in codes:
        cn_code = code.split(".")[0]
        exchange = code.split(".")[1]
        try:
            org = _query_org_id(session, headers, cn_code, config.request_timeout_seconds)
            if not org.get("org_id"):
                blockers.append(_nonfatal("cninfo_org_id_missing", code, "", "No CNInfo org_id returned."))
            else:
                rows.extend(_query_annual_reports(session, headers, code, cn_code, exchange, org, config.request_timeout_seconds))
        except Exception as exc:  # noqa: BLE001
            blockers.append(_nonfatal("cninfo_manifest_query_error", code, "", f"{type(exc).__name__}: {exc}"))
        time.sleep(config.sleep_seconds)
    dedup: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        dedup[(row["code"], row["report_period"], row["announcement_title"])] = row
    return sorted(dedup.values(), key=lambda item: (item["code"], item["report_period"], item["announcement_date"])), blockers


def _query_org_id(session: requests.Session, headers: dict[str, str], cn_code: str, timeout: int) -> dict[str, str]:
    response = session.post(CNINFO_SEARCH_URL, headers=headers, data={"keyWord": cn_code, "maxNum": 10}, timeout=timeout)
    response.raise_for_status()
    for item in response.json():
        if str(item.get("code")) == cn_code and item.get("orgId"):
            return {"org_id": str(item.get("orgId") or ""), "sec_name": str(item.get("zwjc") or ""), "market_type": str(item.get("type") or "")}
    return {"org_id": "", "sec_name": "", "market_type": ""}


def _query_annual_reports(
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
            "category": "category_ndbg_szsh;",
            "trade": "",
            "seDate": f"{TRAIN_START}~{TRAIN_END}",
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
        announcement_date = _ms_to_date(announcement.get("announcementTime"))
        report_period = _infer_report_period(title, announcement_date)
        if not report_period or report_period > "2020-12-31":
            continue
        adjunct = str(announcement.get("adjunctUrl") or "")
        rows.append(
            {
                "industry": "bank",
                "code": code,
                "cn_code": cn_code,
                "exchange": exchange,
                "sec_name": org.get("sec_name", ""),
                "org_id": org.get("org_id", ""),
                "announcement_title": title,
                "announcement_date": announcement_date,
                "report_period": report_period,
                "pit_visible_date": announcement_date,
                "adjunct_url": adjunct,
                "pdf_url": CNINFO_STATIC_BASE + adjunct if adjunct else "",
                "source": "cninfo_hisAnnouncement_pre2021",
                "accepted": False,
            }
        )
    return rows


def _download_or_resolve(
    manifest_rows: list[dict[str, Any]],
    pdf_dir: Path,
    config: Pre2021Config,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "http://www.cninfo.com.cn/"}
    rows: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for row in manifest_rows:
        local_path = pdf_dir / f"{row['code'].replace('.', '_')}_{row['report_period']}_annual_report.pdf"
        status = "not_attempted"
        byte_count = 0
        error = ""
        if local_path.exists() and local_path.stat().st_size > 1024:
            status = "cached"
            byte_count = local_path.stat().st_size
        elif not config.download_missing:
            status = "missing_download_disabled"
        else:
            try:
                response = session.get(str(row.get("pdf_url", "")), headers=headers, timeout=config.request_timeout_seconds)
                response.raise_for_status()
                local_path.write_bytes(response.content)
                status = "downloaded"
                byte_count = len(response.content)
            except Exception as exc:  # noqa: BLE001
                status = f"download_error:{type(exc).__name__}"
                error = str(exc)
                blockers.append(_nonfatal("annual_report_download_error", row.get("code", ""), row.get("report_period", ""), f"{type(exc).__name__}: {exc}"))
        rows.append({**row, "local_pdf_path": str(local_path), "download_status": status, "byte_count": byte_count, "error": error})
        time.sleep(config.sleep_seconds)
    return rows, blockers


def _extract_special_mention_panel(download_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for row in download_rows:
        path = Path(str(row.get("local_pdf_path", "")))
        if not path.exists() or not str(row.get("download_status", "")).startswith(("downloaded", "cached")):
            blockers.append(_nonfatal("annual_report_pdf_unavailable", row.get("code", ""), row.get("report_period", ""), "PDF unavailable."))
            rows.append(_extraction_row(row, "", "", "", "", "pdf_unavailable"))
            continue
        try:
            extracted = _extract_ratio_from_pdf(path)
        except Exception as exc:  # noqa: BLE001
            blockers.append(_nonfatal("annual_report_pdf_read_error", row.get("code", ""), row.get("report_period", ""), f"{type(exc).__name__}: {exc}"))
            rows.append(_extraction_row(row, "", "", "", "", f"pdf_read_error:{type(exc).__name__}"))
            continue
        if extracted:
            rows.append(
                _extraction_row(
                    row,
                    extracted["special_mention_loan_ratio_pct"],
                    extracted.get("special_mention_loan_amount", ""),
                    extracted.get("page_number", ""),
                    extracted.get("context", ""),
                    "pass_extracted_from_original_pdf_text",
                )
            )
        else:
            rows.append(_extraction_row(row, "", "", "", "", "not_found_needs_original_review_or_manual_table_extraction"))
    return rows, blockers


def _extract_ratio_from_pdf(path: Path) -> dict[str, Any] | None:
    import fitz  # type: ignore

    focus_terms = [
        "\u4e94\u7ea7\u5206\u7c7b",
        "\u8d37\u6b3e\u8d28\u91cf",
        "\u5173\u6ce8\u7c7b",
        "\u5173\u6ce8\u7c7b\u8d37\u6b3e",
    ]
    with fitz.open(str(path)) as doc:
        for page_index in range(len(doc)):
            text = doc.load_page(page_index).get_text("text") or ""
            if "\u5173\u6ce8\u7c7b" not in text:
                continue
            page_has_quality_table = any(term in text for term in focus_terms[:2])
            for raw_line in text.splitlines():
                line = re.sub(r"\s+", " ", raw_line).strip()
                if "\u5173\u6ce8\u7c7b" not in line:
                    continue
                if "\u8fc1\u5f99\u7387" in line:
                    continue
                parsed = _parse_special_mention_line(line)
                if parsed:
                    return {**parsed, "page_number": page_index + 1, "context": _context(text, "\u5173\u6ce8\u7c7b")}
            if page_has_quality_table:
                parsed = _parse_special_mention_line(re.sub(r"\s+", " ", text))
                if parsed:
                    return {**parsed, "page_number": page_index + 1, "context": _context(text, "\u5173\u6ce8\u7c7b")}
    return None


def _parse_special_mention_line(line: str) -> dict[str, Any] | None:
    if "\u5173\u6ce8\u7c7b" not in line:
        return None
    tail = line.split("\u5173\u6ce8\u7c7b", 1)[-1]
    nums = re.findall(r"-?\d[\d,]*(?:\.\d+)?%?", tail[:160])
    values = [_number_value(item) for item in nums]
    values = [value for value in values if value is not None]
    if len(values) >= 2 and values[0] > 100 and 0 <= values[1] <= 20:
        return {"special_mention_loan_amount": values[0], "special_mention_loan_ratio_pct": values[1], "parse_rule": "amount_then_ratio_after_special_mention_class"}
    if values and 0 <= values[0] <= 20 and "%" in nums[0]:
        return {"special_mention_loan_amount": "", "special_mention_loan_ratio_pct": values[0], "parse_rule": "percent_after_special_mention_class"}
    return None


def _number_value(text: str) -> float | None:
    try:
        return float(text.replace(",", "").replace("%", ""))
    except ValueError:
        return None


def _context(text: str, term: str, window: int = 260) -> str:
    idx = text.find(term)
    if idx < 0:
        return ""
    return re.sub(r"\s+", " ", text[max(0, idx - window) : idx + window]).strip()


def _extraction_row(row: dict[str, Any], ratio: Any, amount: Any, page_number: Any, context: str, status: str) -> dict[str, Any]:
    return {
        "code": row.get("code", ""),
        "sec_name": row.get("sec_name", ""),
        "report_period": row.get("report_period", ""),
        "announcement_date": row.get("announcement_date", ""),
        "pit_visible_date": row.get("pit_visible_date", row.get("announcement_date", "")),
        "special_mention_loan_ratio_pct": ratio,
        "special_mention_loan_amount": amount,
        "page_number": page_number,
        "sample_context": context,
        "local_pdf_path": row.get("local_pdf_path", ""),
        "extraction_status": status,
        "pit_source": "cninfo_annual_report_pdf_text",
        "accepted": False,
    }


def _build_pit_panel(bank_panel: pd.DataFrame, extraction_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    extract = pd.DataFrame(extraction_rows)
    if extract.empty:
        return []
    extract["special_mention_loan_ratio_pct"] = pd.to_numeric(extract.get("special_mention_loan_ratio_pct"), errors="coerce")
    extract = extract[extract["special_mention_loan_ratio_pct"].notna()].copy()
    extract = extract.sort_values(["code", "pit_visible_date", "report_period"])
    by_code = {code: group for code, group in extract.groupby("code", sort=True)}
    rows: list[dict[str, Any]] = []
    for _, item in bank_panel.sort_values(["trade_date", "code"]).iterrows():
        code = str(item["code"])
        trade_date = str(item["trade_date"])
        match = _latest_visible_report(by_code.get(code), trade_date)
        future_return = _safe_float(item.get("future_return"))
        row = {
            "scope": "bank_sleeve_train_test",
            "trade_date": trade_date,
            "code": code,
            "next_trade_date": item.get("next_trade_date", ""),
            "future_return": future_return if future_return is not None else "",
            "special_mention_loan_ratio_pct": "",
            "matched_report_period": "",
            "matched_visible_date": "",
            "pit_status": "missing_special_mention_before_trade_date",
            "source_status": "",
            "sample_split_role": "train_test_pre2021",
            "formal_backtest_window": False,
            "accepted": False,
        }
        if match is not None:
            row.update(
                {
                    "special_mention_loan_ratio_pct": float(match["special_mention_loan_ratio_pct"]),
                    "matched_report_period": match.get("report_period", ""),
                    "matched_visible_date": match.get("pit_visible_date", ""),
                    "pit_status": "pass",
                    "source_status": match.get("extraction_status", ""),
                }
            )
        rows.append(row)
    return rows


def _latest_visible_report(group: pd.DataFrame | None, trade_date: str) -> dict[str, Any] | None:
    if group is None or group.empty:
        return None
    eligible = group[group["pit_visible_date"].astype(str) <= trade_date]
    if eligible.empty:
        return None
    return eligible.iloc[-1].to_dict()


def _strict_preview_panel(preview: pd.DataFrame, pit_panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pit = pd.DataFrame(pit_panel)
    if pit.empty:
        return []
    preview_bank = preview[preview["sector_id"].eq("bank")].rename(columns={"preview_date": "trade_date"}).copy()
    merged = preview_bank.merge(pit, on=["trade_date", "code"], how="left", suffixes=("_preview", ""))
    rows: list[dict[str, Any]] = []
    for _, row in merged.iterrows():
        rows.append(
            {
                "scope": "strict_multisleeve_preview_bank_subset",
                "trade_date": row.get("trade_date", ""),
                "code": row.get("code", ""),
                "selected_rank": row.get("selected_rank", ""),
                "future_return": row.get("future_return", ""),
                "special_mention_loan_ratio_pct": row.get("special_mention_loan_ratio_pct", ""),
                "matched_report_period": row.get("matched_report_period", ""),
                "matched_visible_date": row.get("matched_visible_date", ""),
                "pit_status": row.get("pit_status", "missing_special_mention_before_trade_date"),
                "sample_split_role": "strict_pre2021_preview",
                "accepted": False,
            }
        )
    return rows


def _bucket_results(panel_rows: list[dict[str, Any]], scope: str) -> list[dict[str, Any]]:
    df = pd.DataFrame(panel_rows)
    if df.empty:
        return []
    df["factor"] = pd.to_numeric(df.get("special_mention_loan_ratio_pct"), errors="coerce")
    df["future_return_num"] = pd.to_numeric(df.get("future_return"), errors="coerce")
    rows: list[dict[str, Any]] = []
    for date, group in df.groupby("trade_date", sort=True):
        valid = group[group["factor"].notna() & group["future_return_num"].notna()].copy()
        if len(valid) < 3:
            continue
        valid["score"] = -valid["factor"]
        valid["rank"] = valid["score"].rank(method="first")
        valid["bucket"] = "middle"
        valid.loc[valid["rank"] > len(valid) * 2 / 3, "bucket"] = "top_low_special_mention"
        valid.loc[valid["rank"] <= len(valid) / 3, "bucket"] = "bottom_high_special_mention"
        for bucket, bucket_df in valid.groupby("bucket", sort=True):
            rows.append(
                {
                    "scope": scope,
                    "factor_id": FACTOR_ID,
                    "trade_date": date,
                    "bucket": bucket,
                    "stock_count": len(bucket_df),
                    "avg_special_mention_loan_ratio_pct": bucket_df["factor"].mean(),
                    "avg_forward_period_return": bucket_df["future_return_num"].mean(),
                    "sample_split_role": "train_test_pre2021",
                    "accepted": False,
                }
            )
        top = valid[valid["bucket"].eq("top_low_special_mention")]
        bottom = valid[valid["bucket"].eq("bottom_high_special_mention")]
        if len(top) and len(bottom):
            rows.append(
                {
                    "scope": scope,
                    "factor_id": FACTOR_ID,
                    "trade_date": date,
                    "bucket": "top_minus_bottom",
                    "stock_count": len(top) + len(bottom),
                    "avg_special_mention_loan_ratio_pct": top["factor"].mean() - bottom["factor"].mean(),
                    "avg_forward_period_return": top["future_return_num"].mean() - bottom["future_return_num"].mean(),
                    "sample_split_role": "train_test_pre2021",
                    "accepted": False,
                }
            )
    return rows


def _overlay_results(panel_rows: list[dict[str, Any]], scope: str) -> list[dict[str, Any]]:
    df = pd.DataFrame(panel_rows)
    if df.empty:
        return []
    df["factor"] = pd.to_numeric(df.get("special_mention_loan_ratio_pct"), errors="coerce")
    df["future_return_num"] = pd.to_numeric(df.get("future_return"), errors="coerce")
    period_rows: list[dict[str, Any]] = []
    for date, group in df.groupby("trade_date", sort=True):
        valid = group[group["factor"].notna() & group["future_return_num"].notna()].copy()
        if len(valid) < 3:
            continue
        rank = (-valid["factor"]).rank(method="first")
        top = valid[rank > len(valid) * 2 / 3]
        if top.empty:
            continue
        equal_return = valid["future_return_num"].mean()
        top_return = top["future_return_num"].mean()
        overlay_return = 0.90 * equal_return + 0.10 * top_return
        period_rows.append(
            {
                "scope": scope,
                "trade_date": date,
                "valid_stock_count": len(valid),
                "top_stock_count": len(top),
                "equal_weight_period_return": equal_return,
                "overlay_period_return": overlay_return,
                "delta_period_return": overlay_return - equal_return,
            }
        )
    if not period_rows:
        return []
    equal_nav = _compound(row["equal_weight_period_return"] for row in period_rows)
    overlay_nav = _compound(row["overlay_period_return"] for row in period_rows)
    deltas = [row["delta_period_return"] for row in period_rows]
    return [
        {
            "scope": scope,
            "version_id": VERSION_ID,
            "factor_id": FACTOR_ID,
            "period_count": len(period_rows),
            "avg_valid_stock_count": sum(row["valid_stock_count"] for row in period_rows) / len(period_rows),
            "equal_weight_cumulative_return": equal_nav - 1.0,
            "overlay_cumulative_return": overlay_nav - 1.0,
            "delta_cumulative_return_pct_points_vs_equal_weight": (overlay_nav - equal_nav) * 100,
            "avg_period_delta_return": sum(deltas) / len(deltas),
            "positive_delta_period_rate": sum(1 for value in deltas if value > 0) / len(deltas),
            "test_scope": "fixed_10pct_equal_weight_bank_sleeve_diagnostic_not_portfolio_nav",
            "sample_split_role": "train_test_pre2021",
            "accepted": False,
            "live_trading_approved": False,
        }
    ]


def _compound(values: Any) -> float:
    nav = 1.0
    for value in values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            continue
        nav *= 1.0 + float(value)
    return nav


def _coverage_rows(
    bank_panel: pd.DataFrame,
    pit_panel: list[dict[str, Any]],
    strict_panel: list[dict[str, Any]],
    extraction_rows: list[dict[str, Any]],
    manifest_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pit = pd.DataFrame(pit_panel)
    strict = pd.DataFrame(strict_panel)
    extracted = pd.DataFrame(extraction_rows)
    rows = [
        {
            "audit_id": "cninfo_pre2021_manifest",
            "scope": "annual_report_source",
            "row_count": len(manifest_rows),
            "code_count": len({row.get("code", "") for row in manifest_rows}),
            "coverage": "",
            "status": "pass" if manifest_rows else "fail",
            "detail": f"{TRAIN_START}_to_{TRAIN_END}",
        },
        {
            "audit_id": "special_mention_extraction",
            "scope": "annual_report_field",
            "row_count": int(pd.to_numeric(extracted.get("special_mention_loan_ratio_pct"), errors="coerce").notna().sum()) if not extracted.empty else 0,
            "code_count": int(extracted[pd.to_numeric(extracted.get("special_mention_loan_ratio_pct"), errors="coerce").notna()]["code"].nunique()) if not extracted.empty else 0,
            "coverage": "",
            "status": "pass" if not extracted.empty and pd.to_numeric(extracted.get("special_mention_loan_ratio_pct"), errors="coerce").notna().any() else "fail",
            "detail": "CNInfo annual report PDF text extraction.",
        },
        {
            "audit_id": "bank_sleeve_train_test_pit_rows",
            "scope": "bank_sleeve_train_test",
            "row_count": len(pit),
            "code_count": int(pit["code"].nunique()) if not pit.empty else 0,
            "coverage": float(pit["pit_status"].eq("pass").mean()) if not pit.empty else 0.0,
            "status": "pass" if not pit.empty and pit["pit_status"].eq("pass").mean() >= 0.25 else "partial",
            "detail": "Coverage is PIT-visible before each pre-2021 panel date.",
        },
        {
            "audit_id": "strict_preview_dates",
            "scope": "strict_multisleeve_preview_bank_subset",
            "row_count": len(strict),
            "code_count": int(strict["code"].nunique()) if not strict.empty else 0,
            "coverage": float(strict["pit_status"].eq("pass").mean()) if not strict.empty else 0.0,
            "status": "small_sample" if len(strict) else "missing",
            "detail": "Strict repaired multi-sleeve preview currently has bank subset only on 2019-04-01 and 2020-10-09.",
        },
    ]
    return rows


def _governance_audit(
    bank_panel: pd.DataFrame,
    preview: pd.DataFrame,
    pit_panel: list[dict[str, Any]],
    strict_panel: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pit = pd.DataFrame(pit_panel)
    strict = pd.DataFrame(strict_panel)
    pit_leak = 0
    if not pit.empty:
        passed = pit[pit["pit_status"].eq("pass")]
        pit_leak = int((passed["matched_visible_date"].astype(str) > passed["trade_date"].astype(str)).sum())
    return [
        {"audit_id": "sample_split_train_test_window", "status": "pass", "detail": f"{TRAIN_START}_to_{TRAIN_END}"},
        {"audit_id": "formal_backtest_window_not_used_for_training", "status": "pass", "detail": f"{FORMAL_BACKTEST_START}_to_{FORMAL_BACKTEST_END}_reclassified_as_formal_backtest_only"},
        {"audit_id": "pit_visible_date_audit", "status": "pass" if pit_leak == 0 else "fail", "detail": pit_leak},
        {"audit_id": "bank_sleeve_only_diagnostic_boundary", "status": "pass", "detail": "No full-market stock selection; bank panel only."},
        {"audit_id": "strict_multisleeve_preview_boundary", "status": "pass" if not strict.empty else "partial", "detail": len(strict)},
        {"audit_id": "v57f_core_modified_false", "status": "pass", "detail": False},
        {"audit_id": "accepted_false", "status": "pass", "detail": False},
        {"audit_id": "live_trading_approved_false", "status": "pass", "detail": False},
        {"audit_id": "threshold_scan_used_false", "status": "pass", "detail": "fixed 10pct overlay diagnostic only"},
        {"audit_id": "nonfatal_data_issue_count", "status": "pass", "detail": sum(1 for row in blockers if row.get("severity") != "fatal")},
    ]


def _backtest_reconciliation(
    backtest_summary: dict[str, Any],
    overlay_rows: list[dict[str, Any]],
    strict_overlay: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    train_delta = float(overlay_rows[0].get("delta_cumulative_return_pct_points_vs_equal_weight", 0.0)) if overlay_rows else 0.0
    strict_delta = float(strict_overlay[0].get("delta_cumulative_return_pct_points_vs_equal_weight", 0.0)) if strict_overlay else 0.0
    return [
        {
            "result_id": "v5c_bank_power_single_factor_cross_section_test",
            "window": f"{FORMAL_BACKTEST_START}_to_{FORMAL_BACKTEST_END}",
            "factor": backtest_summary.get("best_factor", FACTOR_ID),
            "version_id": backtest_summary.get("best_version", BACKTEST_POSITIVE_VERSION_ID),
            "reported_delta_vs_v5f_primary_pct_points": backtest_summary.get("best_delta_return_pct_points_vs_v5f_primary", ""),
            "corrected_scope_label": "formal_backtest_positive_only_not_training_or_validation",
            "may_promote_from_this_window": False,
        },
        {
            "result_id": "v5c_bank_special_mention_pre2021_train_test",
            "window": f"{TRAIN_START}_to_{TRAIN_END}",
            "factor": FACTOR_ID,
            "version_id": VERSION_ID,
            "reported_delta_vs_equal_weight_bank_sleeve_pct_points": train_delta,
            "strict_preview_delta_pct_points": strict_delta,
            "corrected_scope_label": "pre2021_train_test_diagnostic",
            "may_promote_from_this_window": train_delta > 0 and strict_delta > 0,
        },
    ]


def _pm_decision(
    coverage: list[dict[str, Any]],
    governance: list[dict[str, Any]],
    bucket_rows: list[dict[str, Any]],
    overlay_rows: list[dict[str, Any]],
    strict_bucket: list[dict[str, Any]],
    strict_overlay: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gov_fail = [row for row in governance if row["status"] == "fail"]
    coverage_fail = [row for row in coverage if row["status"] == "fail"]
    train_delta = float(overlay_rows[0].get("delta_cumulative_return_pct_points_vs_equal_weight", 0.0)) if overlay_rows else 0.0
    train_rate = float(overlay_rows[0].get("positive_delta_period_rate", 0.0)) if overlay_rows else 0.0
    strict_delta = float(strict_overlay[0].get("delta_cumulative_return_pct_points_vs_equal_weight", 0.0)) if strict_overlay else 0.0
    strict_periods = int(strict_overlay[0].get("period_count", 0)) if strict_overlay else 0
    if gov_fail:
        decision = "blocked_by_pit_or_sample_split_issue"
        next_action = "repair_governance_before_any_factor_use"
    elif coverage_fail:
        decision = "blocked_by_pre2021_special_mention_data_gap"
        next_action = "manual_original_table_review_or_more_cninfo_extraction"
    elif train_delta > 0 and train_rate >= 0.55 and strict_delta > 0 and strict_periods >= 3:
        decision = "pre2021_supports_deep_research_not_accepted"
        next_action = "open_deep_research_candidate_review_without_acceptance"
    elif train_delta > 0 and train_rate >= 0.5 and strict_delta > 0:
        decision = "bank_sleeve_only_positive_strict_preview_insufficient"
        next_action = "keep_as_diagnostic_until_more_strict_multisleeve_or_forward_confirms"
    elif train_delta > 0 and train_rate >= 0.5:
        decision = "bank_sleeve_only_positive_strict_preview_not_confirmed"
        next_action = "keep_as_diagnostic; do_not_promote_without_strict_or_forward_confirmation"
    else:
        decision = "diagnostic_only_pre2021_no_stable_confirmation"
        next_action = "do_not_promote_bank_special_mention_factor"
    return [
        {
            "pm_gate_decision": decision,
            "train_delta_pct_points_vs_equal_weight_bank_sleeve": train_delta,
            "train_positive_delta_period_rate": train_rate,
            "strict_preview_delta_pct_points": strict_delta,
            "strict_preview_period_count": strict_periods,
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "next_action": next_action,
        }
    ]


def _next_queue(
    decision: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    reconciliation: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gate = decision[0]["pm_gate_decision"]
    return [
        {
            "priority": 1,
            "next_task": "keep_internal_subsleeve_mom12_70_30_as_v5f_primary",
            "status": "ready",
            "reason": "No pre2021 packet may override V5f primary without stronger evidence.",
        },
        {
            "priority": 2,
            "next_task": "manual_original_review_for_missing_pre2021_special_mention_reports",
            "status": "ready_if_needed",
            "reason": f"gate={gate}",
        },
        {
            "priority": 3,
            "next_task": "do_not_use_2021_2026_as_training_validation_for_bank_special_mention",
            "status": "ready",
            "reason": reconciliation[0]["corrected_scope_label"],
        },
    ]


def _blockers(blockers: list[dict[str, Any]], governance: list[dict[str, Any]], coverage: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = list(blockers)
    rows.extend({"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": str(row["detail"])} for row in governance if row["status"] == "fail")
    rows.extend({"blocker_id": row["audit_id"], "severity": "fatal", "status": "blocking", "description": str(row["detail"])} for row in coverage if row["status"] == "fail")
    return rows or [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Pre-2021 packet completed."}]


def _summary(
    status: str,
    train_observation_count: int = 0,
    strict_observation_count: int = 0,
    train_delta_pct_points: float = 0.0,
    strict_delta_pct_points: float = 0.0,
    pm_gate_decision: str = "blocked_missing_required_inputs",
    blockers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    blockers = blockers or []
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5c_bank_special_mention_pre2021_train_test",
        "status": status,
        "factor_id": FACTOR_ID,
        "train_test_scope_start": TRAIN_START,
        "train_test_scope_end": TRAIN_END,
        "formal_backtest_scope_start": FORMAL_BACKTEST_START,
        "formal_backtest_scope_end": FORMAL_BACKTEST_END,
        "benchmark": BASELINE,
        "primary_reference": PRIMARY,
        "train_observation_count": train_observation_count,
        "strict_preview_observation_count": strict_observation_count,
        "train_delta_pct_points_vs_equal_weight_bank_sleeve": train_delta_pct_points,
        "strict_preview_delta_pct_points": strict_delta_pct_points,
        "pm_gate_decision": pm_gate_decision,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "formal_backtest_used_as_validation": False,
        "fatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "fatal"),
        "nonfatal_blocker_count": sum(1 for row in blockers if row.get("severity") not in {"fatal", "none"}),
    }


def _report(
    coverage: list[dict[str, Any]],
    bucket_rows: list[dict[str, Any]],
    overlay_rows: list[dict[str, Any]],
    strict_bucket: list[dict[str, Any]],
    strict_overlay: list[dict[str, Any]],
    reconciliation: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    train = overlay_rows[0] if overlay_rows else {}
    strict = strict_overlay[0] if strict_overlay else {}
    lines = [
        "# V5c Bank Special Mention Loan Pre-2021 Train/Test Packet",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Train/test window: `{TRAIN_START}` to `{TRAIN_END}`",
        f"- Formal backtest window: `{FORMAL_BACKTEST_START}` to `{FORMAL_BACKTEST_END}`",
        "- Formal backtest results are not treated as training, validation, rolling, or OOS evidence.",
        "- Accepted: `False`",
        "- V57f core modified: `False`",
        "",
        "## Result",
        f"- Bank sleeve-only fixed 10% diagnostic delta: `{float(train.get('delta_cumulative_return_pct_points_vs_equal_weight', 0.0) or 0.0):+.4f}` pct points vs equal-weight bank sleeve.",
        f"- Bank sleeve-only positive period rate: `{float(train.get('positive_delta_period_rate', 0.0) or 0.0):.2%}`.",
        f"- Strict repaired multi-sleeve preview bank-subset delta: `{float(strict.get('delta_cumulative_return_pct_points_vs_equal_weight', 0.0) or 0.0):+.4f}` pct points.",
        "",
        "## Coverage",
    ]
    for row in coverage:
        lines.append(f"- `{row['audit_id']}`: status=`{row['status']}`, rows=`{row['row_count']}`, detail={row['detail']}")
    lines.extend(
        [
            "",
            "## Scope Reconciliation",
        ]
    )
    for row in reconciliation:
        lines.append(f"- `{row['result_id']}`: window `{row['window']}`, label `{row['corrected_scope_label']}`, promote_now=`{row['may_promote_from_this_window']}`")
    lines.extend(
        [
            "",
            "This packet is a PIT and sample-split correction. It does not accept a new model, does not change V5f primary, and does not use the 2021-2026 formal backtest period as validation.",
        ]
    )
    return "\n".join(lines)


def _rules() -> str:
    return "\n".join(
        [
            "# V5c Bank Special Mention Pre-2021 Rules",
            "",
            "- 2013-01-01 to 2021-04-30 is train/test research only.",
            "- 2021-05-01 to 2026-05-31 is formal backtest only.",
            "- Do not treat 2021-2026 as validation, rolling, or OOS evidence.",
            "- Use PIT-visible annual-report fields only; visible date must be before the panel date.",
            "- Bank sleeve-only diagnostics cannot be promoted as full V57f/V5f portfolio evidence.",
            "- Strict repaired multi-sleeve pre-2021 preview is small sample unless more dates are rebuilt.",
            "- Do not mark accepted or live approved.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        SPLIT_DIR / "v5_sample_split_rules.md",
        PREVIEW_DIR / "v5f_pre2021_candidate_signal_preview.csv",
        BACKTEST_RESULT_DIR / "v5c_bank_power_single_factor_summary.json",
        BANK_PANEL,
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _is_full_annual_report_title(title: str) -> bool:
    if "\u5e74\u5ea6\u62a5\u544a" not in title:
        return False
    blocked = ["\u6458\u8981", "\u82f1\u6587", "\u53d6\u6d88", "\u5173\u4e8e", "\u516c\u544a"]
    return not any(token in title for token in blocked)


def _infer_report_period(title: str, announcement_date: str) -> str:
    match = re.search(r"(20\d{2})\s*\u5e74", title)
    if match:
        return f"{match.group(1)}-12-31"
    if announcement_date:
        return f"{int(announcement_date[:4]) - 1}-12-31"
    return ""


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def _ms_to_date(value: Any) -> str:
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return ""


def _safe_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(result) else result


def _nonfatal(blocker_id: str, code: str, report_period: str, description: str) -> dict[str, Any]:
    return {"blocker_id": blocker_id, "severity": "nonfatal", "status": "logged", "code": code, "report_period": report_period, "description": description}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    run()

from __future__ import annotations

import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.credential_loader import DEFAULT_CREDENTIAL_FILE, load_tushare_token
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import fmt_float, ratio, to_float


DEFAULT_OUT_DIR = Path("\u6570\u636e\u5e93") / "processed" / "gas_water_operating_evidence_v57"

REPORT_DISCLOSURE_FIELDS = [
    "code",
    "ts_code",
    "report_period",
    "report_type",
    "notice_date",
    "notice_date_source",
    "ann_date",
    "pre_date",
    "actual_date",
    "modify_date",
    "source_name",
    "review_status",
    "notes",
]

SEGMENT_RAW_FIELDS = [
    "code",
    "eastmoney_code",
    "report_period",
    "mainop_type",
    "item_name",
    "main_business_income",
    "income_ratio",
    "main_business_cost",
    "cost_ratio",
    "main_business_profit",
    "profit_ratio",
    "gross_profit_ratio",
    "source_name",
    "source_url",
]

SEGMENT_EVIDENCE_FIELDS = [
    "code",
    "ts_code",
    "report_period",
    "report_type",
    "notice_date",
    "visible_date",
    "selected_mainop_type",
    "gas_revenue_share",
    "water_revenue_share",
    "operator_revenue_share",
    "project_engineering_revenue_share",
    "non_operator_revenue_share",
    "largest_non_operator_item",
    "largest_non_operator_revenue_ratio",
    "approved_gas_water_business_tag",
    "source_name",
    "source_url",
    "pit_usable",
    "review_status",
    "notes",
]

PANEL_EXTRA_FIELDS = [
    "gas_water_report_period",
    "gas_water_visible_date",
    "gas_revenue_share",
    "water_revenue_share",
    "operator_revenue_share",
    "project_engineering_revenue_share",
    "non_operator_revenue_share",
    "approved_gas_water_business_tag",
    "business_purity_gate",
    "business_purity_review_status",
]

GAS_TERMS = (
    "\u71c3\u6c14",
    "\u5929\u7136\u6c14",
    "\u57ce\u5e02\u71c3\u6c14",
    "\u7ba1\u9053\u71c3\u6c14",
    "\u7ba1\u8f93",
    "\u4f9b\u6c14",
    "lng",
)
WATER_TERMS = (
    "\u81ea\u6765\u6c34",
    "\u4f9b\u6c34",
    "\u6c34\u52a1",
    "\u6c61\u6c34",
    "\u6392\u6c34",
    "\u6c34\u5904\u7406",
    "\u518d\u751f\u6c34",
)
PROJECT_TERMS = (
    "\u5de5\u7a0b",
    "\u65bd\u5de5",
    "\u5efa\u8bbe",
    "\u5b89\u88c5",
    "\u8bbe\u5907",
    "\u8bbe\u8ba1",
    "\u6280\u672f\u670d\u52a1",
    "\u9879\u76ee",
    "epc",
)
NON_OPERATOR_TERMS = (
    "\u623f\u5730\u4ea7",
    "\u7269\u4e1a",
    "\u8d38\u6613",
    "\u5546\u54c1",
    "\u6750\u6599",
    "\u5efa\u6750",
    "\u91d1\u878d",
    "\u6295\u8d44",
)


def collect_gas_water_report_disclosure_dates(
    panel_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
    credential_file: Path = DEFAULT_CREDENTIAL_FILE,
    token_env: str = "TUSHARE_TOKEN",
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    panel_rows = read_csv_rows(panel_csv)
    codes = sorted({row["code"] for row in panel_rows if row.get("code")})
    target_years = _target_report_years(panel_rows)
    warnings: list[str] = []
    rows: list[dict[str, Any]] = []
    token = load_tushare_token(token_env, credential_file)
    if not token:
        warnings.append(f"Tushare token not found in {token_env} or credential file.")
    else:
        try:
            import tushare as ts

            pro = ts.pro_api(token)
            rows = _fetch_disclosure_rows(pro, codes, target_years, warnings)
        except Exception as exc:
            warnings.append(f"tushare disclosure_date collection failed: {type(exc).__name__}: {exc}")

    out_path = out_dir / "gas_water_report_disclosure_dates.csv"
    write_csv_rows(out_path, REPORT_DISCLOSURE_FIELDS, rows)
    write_json_file(
        out_dir / "gas_water_report_disclosure_dates_manifest.json",
        {
            "dataset": "gas_water_report_disclosure_dates",
            "panel": str(panel_csv),
            "output": str(out_path),
            "code_count": len(codes),
            "target_years": sorted(target_years),
            "row_count": len(rows),
            "warning_count": len(warnings),
            "warnings": warnings,
            "source_policy": "Tushare disclosure_date supplies report timing only. It does not prove gas/water operating exposure.",
            "created_at_utc": _now_utc(),
        },
    )
    return out_path


def collect_eastmoney_gas_water_segment_evidence(
    panel_csv: Path,
    disclosure_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
    *,
    request_timeout_seconds: float = 15.0,
    sleep_seconds: float = 0.25,
    limit: int | None = None,
) -> Path:
    panel_rows = read_csv_rows(panel_csv)
    codes = sorted({row.get("code", "") for row in panel_rows if row.get("code")})
    if limit is not None:
        codes = codes[:limit]
    disclosures = _disclosures_by_code_period(disclosure_csv)
    raw_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for code in codes:
        try:
            records = _fetch_eastmoney_segment_records(code, request_timeout_seconds)
        except Exception as exc:
            warnings.append(f"{code}: Eastmoney segment fetch failed: {type(exc).__name__}: {exc}")
            continue
        if not records:
            warnings.append(f"{code}: Eastmoney segment fetch returned no zygcfx rows")
        raw_rows.extend(_normalize_eastmoney_segment_records(code, records))
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    evidence_rows = _build_segment_evidence_from_raw(raw_rows, disclosures)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "eastmoney_gas_water_segment_raw.csv"
    evidence_path = out_dir / "gas_water_segment_business_evidence_eastmoney.csv"
    write_csv_rows(raw_path, SEGMENT_RAW_FIELDS, raw_rows)
    write_csv_rows(evidence_path, SEGMENT_EVIDENCE_FIELDS, evidence_rows)
    usable = [row for row in evidence_rows if str(row.get("pit_usable", "")).lower() == "true"]
    tag_counts = Counter(row.get("approved_gas_water_business_tag", "") for row in evidence_rows)
    write_json_file(
        out_dir / "eastmoney_gas_water_segment_evidence_manifest.json",
        {
            "dataset": "eastmoney_gas_water_segment_evidence",
            "panel": str(panel_csv),
            "disclosure_csv": str(disclosure_csv),
            "raw_output": str(raw_path),
            "evidence_output": str(evidence_path),
            "requested_company_count": len(codes),
            "raw_row_count": len(raw_rows),
            "evidence_row_count": len(evidence_rows),
            "pit_usable_rows": len(usable),
            "covered_company_count": len({row["code"] for row in usable if row.get("code")}),
            "tag_counts": dict(sorted(tag_counts.items())),
            "warning_count": len(warnings),
            "warnings": warnings,
            "source_policy": "Eastmoney public F10 BusinessAnalysis/PageAjax via normal HTTP request with timeout and no anti-crawler bypass.",
            "pit_policy": "visible_date is joined from Tushare disclosure_date for the same report period when available.",
            "limitations": [
                "Eastmoney segment evidence is first-layer structured evidence only.",
                "Annual/interim report spot checks are still required before Engineering handoff.",
                "Receivables, tariff reform and gas procurement pass-through are not certified by this file.",
            ],
            "created_at_utc": _now_utc(),
        },
    )
    return evidence_path


def build_gas_water_business_purity_panel(
    panel_csv: Path,
    evidence_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR / "business_purity_panel",
    *,
    min_operator_share: float = 0.5,
) -> Path:
    panel_rows = read_csv_rows(panel_csv)
    evidence_rows = read_csv_rows(evidence_csv)
    evidence_by_code: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in evidence_rows:
        if row.get("code") and row.get("visible_date") and str(row.get("pit_usable", "")).lower() == "true":
            evidence_by_code[row["code"]].append(row)
    for rows in evidence_by_code.values():
        rows.sort(key=lambda item: (item.get("visible_date", ""), item.get("report_period", "")))

    enriched_rows: list[dict[str, Any]] = []
    removed_rows: list[dict[str, Any]] = []
    for row in panel_rows:
        visible = _latest_visible_evidence(evidence_by_code.get(row.get("code", ""), []), row.get("trade_date", ""))
        enriched = dict(row)
        gate = "missing_visible_business_evidence"
        if visible:
            for field in [
                "report_period",
                "visible_date",
                "gas_revenue_share",
                "water_revenue_share",
                "operator_revenue_share",
                "project_engineering_revenue_share",
                "non_operator_revenue_share",
                "approved_gas_water_business_tag",
                "review_status",
            ]:
                target = f"gas_water_{field}" if field in {"report_period", "visible_date"} else field
                enriched[target] = visible.get(field, "")
            operator_share = to_float(visible.get("operator_revenue_share")) or 0.0
            tag = visible.get("approved_gas_water_business_tag", "")
            if operator_share >= min_operator_share and tag in {
                "core_gas_operator",
                "core_water_operator",
                "mixed_gas_water_operator",
                "mixed_utility_operator",
            }:
                gate = "passed"
            else:
                gate = "failed_non_operator_contamination"
        for field in PANEL_EXTRA_FIELDS:
            enriched.setdefault(field, "")
        enriched["business_purity_gate"] = gate
        enriched["business_purity_review_status"] = "eastmoney_first_layer_needs_spot_check" if gate == "passed" else gate
        if gate == "passed":
            enriched_rows.append(enriched)
        else:
            removed_rows.append(enriched)

    out_dir.mkdir(parents=True, exist_ok=True)
    panel_path = out_dir / "panel_business_purity_passed.csv"
    removed_path = out_dir / "removed_by_business_purity_gate.csv"
    fieldnames = list(panel_rows[0].keys()) + [field for field in PANEL_EXTRA_FIELDS if field not in panel_rows[0]]
    write_csv_rows(panel_path, fieldnames, enriched_rows)
    write_csv_rows(removed_path, fieldnames, removed_rows)
    coverage_by_date = _coverage_rows(panel_rows, enriched_rows, removed_rows)
    write_csv_rows(out_dir / "business_purity_coverage_by_rebalance.csv", ["trade_date", "total_rows", "passed_rows", "removed_rows", "coverage_ratio"], coverage_by_date)
    write_json_file(
        out_dir / "business_purity_gate_manifest.json",
        {
            "dataset": "gas_water_business_purity_gate_v57",
            "source_panel": str(panel_csv),
            "evidence_csv": str(evidence_csv),
            "passed_panel": str(panel_path),
            "removed_rows": str(removed_path),
            "source_panel_rows": len(panel_rows),
            "passed_rows": len(enriched_rows),
            "removed_rows_count": len(removed_rows),
            "passed_code_count": len({row["code"] for row in enriched_rows if row.get("code")}),
            "min_operator_share": min_operator_share,
            "coverage_by_rebalance": "business_purity_coverage_by_rebalance.csv",
            "source_policy": "Eastmoney segment evidence is first-layer only; annual/interim report spot checks are still required.",
            "created_at_utc": _now_utc(),
        },
    )
    return panel_path


def _build_segment_evidence_from_raw(
    raw_rows: list[dict[str, Any]],
    disclosures: dict[tuple[str, str], dict[str, str]],
) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        code = str(row.get("code") or "")
        report_period = str(row.get("report_period") or "")
        if code and report_period:
            by_key[(code, report_period)].append(row)

    evidence_rows: list[dict[str, Any]] = []
    for (code, report_period), rows in sorted(by_key.items()):
        selected_type, selected = _select_segment_layer(rows)
        ratios = _gas_water_segment_ratios(selected)
        disclosure = disclosures.get((code, report_period), {})
        visible_date = disclosure.get("notice_date", "")
        tag = _approved_gas_water_business_tag(ratios)
        pit_usable = bool(visible_date and tag != "non_operator_or_needs_review")
        evidence_rows.append(
            {
                "code": code,
                "ts_code": _to_ts_code(code),
                "report_period": report_period,
                "report_type": "semiannual" if report_period.endswith("-06-30") else "annual" if report_period.endswith("-12-31") else "other",
                "notice_date": visible_date,
                "visible_date": visible_date,
                "selected_mainop_type": selected_type,
                "gas_revenue_share": fmt_float(ratios["gas_revenue_share"]),
                "water_revenue_share": fmt_float(ratios["water_revenue_share"]),
                "operator_revenue_share": fmt_float(ratios["operator_revenue_share"]),
                "project_engineering_revenue_share": fmt_float(ratios["project_engineering_revenue_share"]),
                "non_operator_revenue_share": fmt_float(ratios["non_operator_revenue_share"]),
                "largest_non_operator_item": ratios["largest_non_operator_item"],
                "largest_non_operator_revenue_ratio": fmt_float(ratios["largest_non_operator_revenue_ratio"]),
                "approved_gas_water_business_tag": tag,
                "source_name": "Eastmoney F10 BusinessAnalysis/PageAjax + Tushare disclosure_date",
                "source_url": f"https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/Index?type=web&code={_to_eastmoney_code(code)}",
                "pit_usable": "true" if pit_usable else "false",
                "review_status": "eastmoney_segment_needs_spot_check" if pit_usable else "needs_review_or_not_core",
                "notes": _segment_notes(selected, ratios),
            }
        )
    return evidence_rows


def _select_segment_layer(rows: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    for mainop_type in ("product", "industry"):
        selected = [row for row in rows if row.get("mainop_type") == mainop_type and not _is_segment_subitem(str(row.get("item_name") or ""))]
        if selected:
            return mainop_type, selected
    selected = [row for row in rows if not _is_segment_subitem(str(row.get("item_name") or ""))]
    return "all_non_region" if selected else "all", selected or rows


def _gas_water_segment_ratios(rows: list[dict[str, Any]]) -> dict[str, Any]:
    weights = [_segment_weight(row) for row in rows]
    total = sum(weight for weight in weights if weight > 0)
    gas_total = 0.0
    water_total = 0.0
    project_total = 0.0
    non_operator: list[tuple[str, float]] = []
    for row, amount in zip(rows, weights):
        name = str(row.get("item_name") or "")
        bucket = _segment_bucket(name)
        if bucket == "gas":
            gas_total += amount
        elif bucket == "water":
            water_total += amount
        elif bucket == "project_engineering":
            project_total += amount
            non_operator.append((name, amount))
        else:
            non_operator.append((name, amount))
    operator_total = gas_total + water_total
    largest_non_name, largest_non_amount = ("", 0.0)
    if non_operator:
        largest_non_name, largest_non_amount = max(non_operator, key=lambda item: item[1])
    return {
        "gas_revenue_share": ratio(gas_total, total),
        "water_revenue_share": ratio(water_total, total),
        "operator_revenue_share": ratio(operator_total, total),
        "project_engineering_revenue_share": ratio(project_total, total),
        "non_operator_revenue_share": ratio(max(0.0, total - operator_total), total),
        "largest_non_operator_item": largest_non_name,
        "largest_non_operator_revenue_ratio": ratio(largest_non_amount, total),
    }


def _segment_bucket(name: str) -> str:
    text = name.lower()
    if any(term in name for term in PROJECT_TERMS) or any(term in text for term in ("epc",)):
        return "project_engineering"
    if any(term in name for term in GAS_TERMS) or "lng" in text:
        return "gas"
    if any(term in name for term in WATER_TERMS):
        return "water"
    if any(term in name for term in NON_OPERATOR_TERMS):
        return "non_operator"
    return "non_operator"


def _approved_gas_water_business_tag(ratios: dict[str, Any]) -> str:
    gas_share = to_float(ratios.get("gas_revenue_share")) or 0.0
    water_share = to_float(ratios.get("water_revenue_share")) or 0.0
    operator_share = to_float(ratios.get("operator_revenue_share")) or 0.0
    project_share = to_float(ratios.get("project_engineering_revenue_share")) or 0.0
    if gas_share >= 0.5:
        return "core_gas_operator"
    if water_share >= 0.5:
        return "core_water_operator"
    if operator_share >= 0.6:
        return "mixed_gas_water_operator"
    if operator_share >= 0.5 and project_share <= 0.35:
        return "mixed_utility_operator"
    return "non_operator_or_needs_review"


def _fetch_disclosure_rows(pro: Any, codes: list[str], target_years: set[str], warnings: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for code in codes:
        ts_code = _to_ts_code(code)
        try:
            df = pro.disclosure_date(ts_code=ts_code)
        except Exception as exc:
            warnings.append(f"{code}: tushare disclosure_date failed: {type(exc).__name__}: {exc}")
            continue
        if df is None or getattr(df, "empty", True):
            warnings.append(f"{code}: tushare disclosure_date returned empty")
            continue
        for raw in df.to_dict("records"):
            end_date = _date_text(raw.get("end_date"))
            if not end_date or end_date[:4] not in target_years:
                continue
            if not (end_date.endswith("1231") or end_date.endswith("0630")):
                continue
            ann_date = _date_text(raw.get("ann_date"))
            pre_date = _date_text(raw.get("pre_date"))
            actual_date = _date_text(raw.get("actual_date"))
            modify_date = _date_text(raw.get("modify_date"))
            notice_date, source = _choose_notice_date(actual_date, ann_date, pre_date)
            if not notice_date:
                warnings.append(f"{code} {end_date}: missing report disclosure date")
                continue
            rows.append(
                {
                    "code": code,
                    "ts_code": ts_code,
                    "report_period": _format_date(end_date),
                    "report_type": "semiannual" if end_date.endswith("0630") else "annual",
                    "notice_date": _format_date(notice_date),
                    "notice_date_source": source,
                    "ann_date": _format_date(ann_date),
                    "pre_date": _format_date(pre_date),
                    "actual_date": _format_date(actual_date),
                    "modify_date": _format_date(modify_date),
                    "source_name": "tushare.disclosure_date",
                    "review_status": "report_date_only_operating_evidence_required",
                    "notes": "Use this as report timing evidence only; operating fields still require original report review.",
                }
            )
    return sorted(rows, key=lambda row: (row["code"], row["report_period"], row["report_type"]))


def _fetch_eastmoney_segment_records(code: str, timeout_seconds: float) -> list[dict[str, Any]]:
    import requests

    eastmoney_code = _to_eastmoney_code(code)
    url = "https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/PageAjax"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": f"https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/Index?type=web&code={eastmoney_code}",
    }
    response = requests.get(url, params={"code": eastmoney_code}, headers=headers, timeout=(5, timeout_seconds))
    response.raise_for_status()
    payload = response.json()
    records = payload.get("zygcfx") or []
    return records if isinstance(records, list) else []


def _normalize_eastmoney_segment_records(code: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        report_period = _format_date(_date_text(record.get("REPORT_DATE")))
        if not report_period:
            continue
        rows.append(
            {
                "code": code,
                "eastmoney_code": _to_eastmoney_code(code),
                "report_period": report_period,
                "mainop_type": _mainop_type_name(record.get("MAINOP_TYPE")),
                "item_name": str(record.get("ITEM_NAME") or "").strip(),
                "main_business_income": fmt_float(record.get("MAIN_BUSINESS_INCOME")),
                "income_ratio": fmt_float(record.get("MBI_RATIO")),
                "main_business_cost": fmt_float(record.get("MAIN_BUSINESS_COST")),
                "cost_ratio": fmt_float(record.get("MBC_RATIO")),
                "main_business_profit": fmt_float(record.get("MAIN_BUSINESS_RPOFIT")),
                "profit_ratio": fmt_float(record.get("MBR_RATIO")),
                "gross_profit_ratio": fmt_float(record.get("GROSS_RPOFIT_RATIO")),
                "source_name": "Eastmoney F10 BusinessAnalysis",
                "source_url": f"https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/Index?type=web&code={_to_eastmoney_code(code)}",
            }
        )
    return rows


def _segment_weight(row: dict[str, Any]) -> float:
    amount = to_float(row.get("main_business_income"))
    if amount is not None and amount > 0:
        return amount
    income_ratio = to_float(row.get("income_ratio"))
    if income_ratio is None:
        return 0.0
    return income_ratio * 100.0 if income_ratio <= 1.5 else income_ratio


def _latest_visible_evidence(rows: list[dict[str, str]], trade_date: str) -> dict[str, str] | None:
    visible = None
    trade_key = str(trade_date)[:10]
    for row in rows:
        if str(row.get("visible_date", ""))[:10] <= trade_key:
            visible = row
        else:
            break
    return visible


def _coverage_rows(panel_rows: list[dict[str, str]], passed_rows: list[dict[str, Any]], removed_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total_by_date = Counter(row.get("trade_date", "") for row in panel_rows)
    passed_by_date = Counter(row.get("trade_date", "") for row in passed_rows)
    removed_by_date = Counter(row.get("trade_date", "") for row in removed_rows)
    rows = []
    for trade_date in sorted(total_by_date):
        total = total_by_date[trade_date]
        passed = passed_by_date[trade_date]
        rows.append(
            {
                "trade_date": trade_date,
                "total_rows": total,
                "passed_rows": passed,
                "removed_rows": removed_by_date[trade_date],
                "coverage_ratio": fmt_float(ratio(passed, total)),
            }
        )
    return rows


def _target_report_years(rows: list[dict[str, str]]) -> set[str]:
    years = set()
    for row in rows:
        text = str(row.get("trade_date", ""))[:4]
        if not text.isdigit():
            continue
        year = int(text)
        years.add(str(year))
        years.add(str(year - 1))
    return {year for year in years if "2013" <= year <= "2026"}


def _disclosures_by_code_period(disclosure_csv: Path) -> dict[tuple[str, str], dict[str, str]]:
    result = {}
    if not disclosure_csv.exists():
        return result
    for row in read_csv_rows(disclosure_csv):
        code = row.get("code", "")
        report_period = row.get("report_period", "")
        if code and report_period:
            result[(code, report_period)] = row
    return result


def _choose_notice_date(actual_date: str, ann_date: str, pre_date: str) -> tuple[str, str]:
    if actual_date:
        return actual_date, "actual_date"
    if ann_date:
        return ann_date, "ann_date"
    if pre_date:
        return pre_date, "pre_date"
    return "", ""


def _segment_notes(rows: list[dict[str, Any]], ratios: dict[str, Any]) -> str:
    items = [str(row.get("item_name") or "") for row in rows if row.get("item_name")]
    return (
        f"selected_items={'|'.join(items[:12])}; "
        f"largest_non_operator={ratios.get('largest_non_operator_item')}; "
        "Eastmoney structured segment evidence requires original annual/interim report spot check before final PIT promotion."
    )


def _is_segment_subitem(name: str) -> bool:
    return name.startswith("\u5176\u4e2d") or name.startswith("\u5176\u4e2d\uff1a") or name.startswith("\u5176\u4e2d:")


def _mainop_type_name(value: Any) -> str:
    text = str(value or "").strip()
    return {"1": "industry", "2": "product", "3": "region"}.get(text, text)


def _to_ts_code(code: str) -> str:
    if code.endswith(".XSHE"):
        return code[:6] + ".SZ"
    if code.endswith(".XSHG"):
        return code[:6] + ".SH"
    return code


def _to_eastmoney_code(code: str) -> str:
    if code.endswith(".XSHE"):
        return "SZ" + code[:6]
    if code.endswith(".XSHG"):
        return "SH" + code[:6]
    return code


def _date_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text.lower() == "nan":
        return ""
    return "".join(ch for ch in text[:10] if ch.isdigit())


def _format_date(value: str) -> str:
    text = _date_text(value)
    if len(text) != 8:
        return ""
    return f"{text[:4]}-{text[4:6]}-{text[6:8]}"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

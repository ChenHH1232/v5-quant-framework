from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_OUT_DIR = Path("数据库") / "processed" / "coal_external_state"

STATE_FIELDS = [
    "visible_date",
    "state_date",
    "state_scope",
    "sub_industry",
    "metric",
    "value",
    "unit",
    "source_name",
    "source_url",
    "source_publication_date",
    "pit_usable",
    "review_status",
    "notes",
]

DEFAULT_TEMPLATE_ROWS = [
    {
        "visible_date": "",
        "state_date": "",
        "state_scope": "national",
        "sub_industry": "thermal_coal",
        "metric": "thermal_coal_price_state",
        "value": "",
        "unit": "cny_per_ton_or_index",
        "source_name": "",
        "source_url": "",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "template",
        "notes": "Prefer official spot or long-contract thermal coal source. Futures proxy alone is not formal PIT evidence.",
    },
    {
        "visible_date": "",
        "state_date": "",
        "state_scope": "national",
        "sub_industry": "coking_coal",
        "metric": "coking_coal_price_state",
        "value": "",
        "unit": "cny_per_ton_or_index",
        "source_name": "",
        "source_url": "",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "template",
        "notes": "Coking coal spot or auditable futures proxy with conservative visible date.",
    },
    {
        "visible_date": "",
        "state_date": "",
        "state_scope": "national_or_port",
        "sub_industry": "all_coal",
        "metric": "coal_inventory_or_output_state",
        "value": "",
        "unit": "ton_or_index_or_yoy",
        "source_name": "",
        "source_url": "",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "template",
        "notes": "Use NBS raw coal output, CCTD port inventory, NDRC inventory, or manually reviewed official source.",
    },
    {
        "visible_date": "",
        "state_date": "",
        "state_scope": "national",
        "sub_industry": "coal_power",
        "metric": "coal_power_spread_state",
        "value": "",
        "unit": "spread_index",
        "source_name": "",
        "source_url": "",
        "source_publication_date": "",
        "pit_usable": "false",
        "review_status": "template",
        "notes": "Derived proxy must document coal-price and electricity-price/tariff sources separately.",
    },
]


def write_coal_external_state_template(out_dir: Path = DEFAULT_OUT_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    template_path = out_dir / "coal_external_state_template.csv"
    _write_csv(template_path, STATE_FIELDS, DEFAULT_TEMPLATE_ROWS)
    _write_json(
        out_dir / "collection_manifest.json",
        {
            "dataset": "coal_external_state_template",
            "template": str(template_path),
            "fields": STATE_FIELDS,
            "row_count": len(DEFAULT_TEMPLATE_ROWS),
            "required_pit_rule": "visible_date must be on or before the rebalance date. Rows without visible_date or source_publication_date are not PIT usable.",
            "governance": "This template is data-engineering preparation only. It must not be used for formal strategy scoring until populated and PIT audited.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return template_path


def collect_coal_external_state(
    out_dir: Path = DEFAULT_OUT_DIR,
    start_date: str = "2013-01-01",
    end_date: str = "2026-05-31",
) -> Path:
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    rows.extend(_collect_futures_state_rows(start_date, end_date, warnings))
    rows.extend(_collect_coal_oil_power_index_rows(start_date, end_date, warnings))
    rows.extend(_unavailable_required_state_rows(end_date))
    rows = sorted(rows, key=lambda item: (item["visible_date"], item["metric"], item["sub_industry"]))

    out_dir.mkdir(parents=True, exist_ok=True)
    panel_path = out_dir / "coal_external_state.csv"
    _write_csv(panel_path, STATE_FIELDS, rows)
    validation = validate_coal_external_state(panel_path)
    _write_json(
        out_dir / "collection_manifest.json",
        {
            "dataset": "coal_external_state",
            "panel": str(panel_path),
            "row_count": len(rows),
            "validation": validation,
            "sources": [
                "akshare.futures_main_sina ZC0 thermal-coal proxy",
                "akshare.futures_main_sina JM0 coking-coal proxy",
                "akshare.futures_main_sina J0 coke proxy for coal-power spread proxy review",
                "akshare.macro_china_qyspjg coal-oil-power price index proxy",
            ],
            "warnings": warnings,
            "pit_policy": "Daily futures rows are reduced to month-end state rows and assigned visible_date = next calendar day. This is usable only as preliminary proxy evidence, not final accepted spot-state evidence.",
            "limitations": [
                "Thermal coal futures proxy ZC0 ends in 2022 and cannot cover 2023-2026 formal PIT state.",
                "Inventory/output and coal-power spread rows are templates until official or licensed sources are collected.",
                "Coal-oil-power price index is a broad macro proxy, not a direct coal-power spread.",
                "Futures prices are market proxies and must not be confused with physical spot or long-contract coal prices.",
            ],
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return panel_path


def validate_coal_external_state(path: Path) -> dict[str, Any]:
    rows = _read_csv(path)
    missing_required = []
    future_or_invalid = 0
    pit_usable = 0
    metric_counts: dict[str, int] = defaultdict(int)
    usable_metric_counts: dict[str, int] = defaultdict(int)
    for index, row in enumerate(rows, start=2):
        metric = row.get("metric", "")
        if metric:
            metric_counts[metric] += 1
        required_fields = ["visible_date", "state_date", "metric", "source_publication_date"]
        for field in required_fields:
            if not row.get(field):
                missing_required.append(f"line {index}: missing {field}")
        if row.get("visible_date") and row.get("source_publication_date"):
            if str(row["visible_date"])[:10] < str(row["source_publication_date"])[:10]:
                future_or_invalid += 1
        if str(row.get("pit_usable", "")).lower() == "true":
            pit_usable += 1
            if metric:
                usable_metric_counts[metric] += 1
    required_metrics = [
        "thermal_coal_price_state",
        "coking_coal_price_state",
        "coal_inventory_or_output_state",
        "coal_power_spread_state",
        "coal_oil_power_price_index_state",
    ]
    missing_usable_required_metrics = [metric for metric in required_metrics if usable_metric_counts.get(metric, 0) == 0]
    status = "pass" if not missing_required and future_or_invalid == 0 and not missing_usable_required_metrics else "needs_review"
    return {
        "row_count": len(rows),
        "pit_usable_count": pit_usable,
        "metric_counts": dict(metric_counts),
        "usable_metric_counts": dict(usable_metric_counts),
        "missing_required": missing_required,
        "future_or_invalid_visible_dates": future_or_invalid,
        "missing_usable_required_metrics": missing_usable_required_metrics,
        "status": status,
    }


def latest_visible_state_values(panel_path: Path, trade_dates: Iterable[str]) -> dict[str, dict[str, str]]:
    rows = [row for row in _read_csv(panel_path) if str(row.get("pit_usable", "")).lower() == "true"]
    by_metric: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("metric") and row.get("visible_date") and row.get("value"):
            by_metric[row["metric"]].append(row)
    for metric_rows in by_metric.values():
        metric_rows.sort(key=lambda row: row["visible_date"])

    result: dict[str, dict[str, str]] = {}
    for trade_date in sorted(set(trade_dates)):
        values: dict[str, str] = {}
        for metric, metric_rows in by_metric.items():
            visible = [row for row in metric_rows if row["visible_date"] <= trade_date]
            if visible:
                row = visible[-1]
                values[metric] = row["value"]
                values[f"{metric}_visible_date"] = row["visible_date"]
                values[f"{metric}_state_date"] = row.get("state_date", "")
                values[f"{metric}_source"] = row.get("source_name", "")
        result[trade_date] = values
    return result


def _collect_futures_state_rows(start_date: str, end_date: str, warnings: list[str]) -> list[dict[str, Any]]:
    try:
        import akshare as ak
    except Exception as exc:  # pragma: no cover - optional dependency.
        raise RuntimeError("collecting coal external state requires akshare") from exc

    futures_specs = [
        ("ZC0", "thermal_coal_price_state", "thermal_coal", "thermal coal main-continuous futures proxy"),
        ("JM0", "coking_coal_price_state", "coking_coal", "coking coal main-continuous futures proxy"),
        ("J0", "coke_price_state", "coke", "coke main-continuous futures proxy for spread review"),
    ]
    rows: list[dict[str, Any]] = []
    for symbol, metric, sub_industry, notes in futures_specs:
        try:
            df = ak.futures_main_sina(symbol=symbol, start_date=start_date.replace("-", ""), end_date=end_date.replace("-", ""))
        except Exception as exc:
            warnings.append(f"{symbol}: futures collection failed: {repr(exc)}")
            continue
        rows.extend(_month_end_futures_rows(df, symbol, metric, sub_industry, notes))
    rows.extend(_derived_spread_rows(rows))
    return rows


def _collect_coal_oil_power_index_rows(start_date: str, end_date: str, warnings: list[str]) -> list[dict[str, Any]]:
    try:
        import akshare as ak
    except Exception as exc:  # pragma: no cover - optional dependency.
        raise RuntimeError("collecting coal external state requires akshare") from exc

    try:
        df = ak.macro_china_qyspjg()
    except Exception as exc:
        warnings.append(f"macro_china_qyspjg: collection failed: {repr(exc)}")
        return []

    start = _parse_date(start_date) or date.min
    end = _parse_date(end_date) or date.max
    rows = []
    for record in df.to_dict("records"):
        state_day = _parse_chinese_month(record.get("月份"))
        value = _to_float(record.get("煤油电-指数值"))
        yoy = _to_float(record.get("煤油电-同比增长"))
        if state_day is None or state_day < start or state_day > end:
            continue
        visible = _next_month_25(state_day)
        if value is not None:
            rows.append(
                _state_row(
                    visible,
                    state_day,
                    "china_macro",
                    "coal_oil_power",
                    "coal_oil_power_price_index_state",
                    value,
                    "index",
                    "AkShare macro_china_qyspjg / Eastmoney macro data",
                    "https://data.eastmoney.com/cjsj/qyspjg.html",
                    visible,
                    "macro_proxy",
                    "Broad coal-oil-power enterprise commodity price index. Use as exploratory state proxy only.",
                    pit_usable=True,
                )
            )
        if yoy is not None:
            rows.append(
                _state_row(
                    visible,
                    state_day,
                    "china_macro",
                    "coal_oil_power",
                    "coal_oil_power_price_yoy_state",
                    yoy,
                    "percent",
                    "AkShare macro_china_qyspjg / Eastmoney macro data",
                    "https://data.eastmoney.com/cjsj/qyspjg.html",
                    visible,
                    "macro_proxy",
                    "Broad coal-oil-power enterprise commodity price YoY. Use as exploratory state proxy only.",
                    pit_usable=True,
                )
            )
    return rows


def _month_end_futures_rows(df: Any, symbol: str, metric: str, sub_industry: str, notes: str) -> list[dict[str, Any]]:
    if df is None or getattr(df, "empty", True):
        return []
    latest_by_month: dict[str, dict[str, Any]] = {}
    for record in df.to_dict("records"):
        state_day = _parse_date(record.get("日期"))
        value = _to_float(record.get("收盘价"))
        if state_day is None or value is None or value <= 0:
            continue
        key = state_day.strftime("%Y-%m")
        if key not in latest_by_month or state_day > latest_by_month[key]["state_day"]:
            latest_by_month[key] = {"state_day": state_day, "value": value}
    rows = []
    for item in latest_by_month.values():
        state_day = item["state_day"]
        visible = state_day + timedelta(days=1)
        rows.append(
            _state_row(
                visible,
                state_day,
                "china_futures_market",
                sub_industry,
                metric,
                item["value"],
                "cny_per_ton_proxy",
                f"AkShare futures_main_sina {symbol}",
                "https://vip.stock.finance.sina.com.cn/quotes_service/view/qihuohangqing.html",
                visible,
                "preliminary_proxy",
                notes,
                pit_usable=True,
            )
        )
    return rows


def _derived_spread_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    thermal = _rows_by_state_date(rows, "thermal_coal_price_state")
    coke = _rows_by_state_date(rows, "coke_price_state")
    result = []
    for state_day, thermal_row in thermal.items():
        coke_row = coke.get(state_day)
        if not coke_row:
            continue
        thermal_value = _to_float(thermal_row.get("value"))
        coke_value = _to_float(coke_row.get("value"))
        if thermal_value is None or coke_value is None:
            continue
        visible = max(_parse_date(thermal_row["visible_date"]) or state_day, _parse_date(coke_row["visible_date"]) or state_day)
        result.append(
            _state_row(
                visible,
                state_day,
                "china_futures_market",
                "coal_power",
                "coal_power_spread_state",
                coke_value - thermal_value,
                "proxy_spread",
                "Derived from AkShare futures_main_sina J0 minus ZC0",
                "https://vip.stock.finance.sina.com.cn/quotes_service/view/qihuohangqing.html",
                visible,
                "preliminary_proxy",
                "Proxy only. This is not a physical coal-power spread and must be replaced before formal acceptance.",
                pit_usable=True,
            )
        )
    return result


def _rows_by_state_date(rows: list[dict[str, Any]], metric: str) -> dict[date, dict[str, Any]]:
    result = {}
    for row in rows:
        if row.get("metric") != metric:
            continue
        state_day = _parse_date(row.get("state_date"))
        if state_day is not None:
            result[state_day] = row
    return result


def _unavailable_required_state_rows(end_date: str) -> list[dict[str, Any]]:
    day = _parse_date(end_date) or date.today()
    return [
        _state_row(
            day,
            day,
            "national_or_port",
            "all_coal",
            "coal_inventory_or_output_state",
            "",
            "ton_or_yoy",
            "not_collected_yet",
            "",
            day,
            "missing_required_source",
            "Official raw coal output or inventory source is required before formal candidate promotion.",
            pit_usable=False,
        )
    ]


def _state_row(
    visible_date: date,
    state_date: date,
    state_scope: str,
    sub_industry: str,
    metric: str,
    value: Any,
    unit: str,
    source_name: str,
    source_url: str,
    source_publication_date: date,
    review_status: str,
    notes: str,
    pit_usable: bool,
) -> dict[str, str]:
    return {
        "visible_date": visible_date.isoformat(),
        "state_date": state_date.isoformat(),
        "state_scope": state_scope,
        "sub_industry": sub_industry,
        "metric": metric,
        "value": _fmt(value),
        "unit": unit,
        "source_name": source_name,
        "source_url": source_url,
        "source_publication_date": source_publication_date.isoformat(),
        "pit_usable": str(pit_usable).lower(),
        "review_status": review_status,
        "notes": notes,
    }


def _parse_date(value: Any) -> date | None:
    if value in {None, ""}:
        return None
    if isinstance(value, date):
        return value
    if hasattr(value, "date"):
        return value.date()
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def _parse_chinese_month(value: Any) -> date | None:
    if value in {None, ""}:
        return None
    text = str(value).strip().replace("月份", "")
    try:
        year_text, month_text = text.split("年", 1)
        year = int(year_text)
        month = int(month_text)
    except (ValueError, TypeError):
        return None
    if month < 1 or month > 12:
        return None
    if month == 12:
        return date(year, month, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def _next_month_25(day: date) -> date:
    year = day.year
    month = day.month + 1
    if month == 13:
        year += 1
        month = 1
    return date(year, month, 25)


def _to_float(value: Any) -> float | None:
    if value in {None, "", "nan", "NaN", "None"}:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _fmt(value: Any) -> str:
    numeric = _to_float(value)
    if numeric is None:
        return "" if value in {None, ""} else str(value)
    return f"{numeric:.10g}"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-coal-external-state")
    subparsers = parser.add_subparsers(dest="command", required=True)
    template_parser = subparsers.add_parser("template")
    template_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    collect_parser = subparsers.add_parser("collect")
    collect_parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    collect_parser.add_argument("--start-date", default="2013-01-01")
    collect_parser.add_argument("--end-date", default="2026-05-31")
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("csv_path", type=Path)
    args = parser.parse_args(argv)
    if args.command == "template":
        print(write_coal_external_state_template(args.out_dir))
        return 0
    if args.command == "collect":
        print(collect_coal_external_state(args.out_dir, args.start_date, args.end_date))
        return 0
    if args.command == "validate":
        print(json.dumps(validate_coal_external_state(args.csv_path), ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

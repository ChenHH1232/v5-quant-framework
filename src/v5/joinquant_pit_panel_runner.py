from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from v5.credential_loader import load_joinquant_credentials


DEFAULT_DATABASE_DIR = Path("数据库")


@dataclass(frozen=True)
class JoinQuantPitPanelResult:
    panel_path: Path
    manifest_path: Path
    row_count: int
    date_count: int
    code_count: int
    warning_count: int


PIT_PANEL_FIELDS = [
    "trade_date",
    "code",
    "close",
    "price_adjustment",
    "next_trade_date",
    "price_return",
    "dividend_return",
    "total_return",
    "future_return",
    "return_source",
    "benchmark_return",
    "benchmark_source",
    "low_price_to_book",
    "dividend_yield",
    "return_on_equity_ttm",
    "non_performing_loan_ratio",
    "provision_coverage_ratio",
    "core_tier_1_capital_adequacy_ratio",
    "factor_visible_date",
    "factor_visibility_source",
    "bank_quality_notice_date",
    "bank_quality_review_status",
    "dividend_visible_policy",
]


def collect_joinquant_basic_pit_panel(
    scaffold_panel: Path,
    out_dir: Path,
    database_dir: Path = DEFAULT_DATABASE_DIR,
    start_date: str = "2014-01-01",
    end_date: str = "2026-05-31",
    benchmark: str = "512800.XSHG",
    benchmark_fq: str = "pre",
    dividend_csv: Path | None = None,
    dividend_tax_rate: float = 0.2,
    bank_quality_csv: Path | None = None,
    bank_quality_min_review_status: str = "needs_check",
    username_env: str = "JQDATA_USERNAME",
    password_env: str = "JQDATA_PASSWORD",
) -> JoinQuantPitPanelResult:
    jq = _load_authenticated_jqdata(username_env, password_env)
    scaffold_rows = _load_scaffold(scaffold_panel, start_date, end_date)
    if not scaffold_rows:
        raise RuntimeError(f"no scaffold rows in window: {start_date} to {end_date}")
    dates = sorted({row["trade_date"] for row in scaffold_rows})
    codes = sorted({row["code"] for row in scaffold_rows})
    dividends = _load_dividend_events(dividend_csv or database_dir / "processed" / "bank_cash_dividends.csv")
    bank_quality = _load_bank_quality_snapshots(
        bank_quality_csv or database_dir / "processed" / "eastmoney_bank_quality_manual_csv.csv",
        bank_quality_min_review_status,
    )
    warnings: list[str] = []

    fundamentals_by_date: dict[str, dict[str, dict[str, Any]]] = {}
    for trade_day in dates:
        try:
            fundamentals_by_date[trade_day.isoformat()] = _fetch_fundamentals(jq, codes, trade_day)
        except Exception as exc:
            warnings.append(f"{trade_day}: fundamentals failed: {repr(exc)}")
            fundamentals_by_date[trade_day.isoformat()] = {}

    price_by_code: dict[str, dict[str, float]] = {}
    min_day = min(dates).isoformat()
    max_next_day = max(row["next_trade_date"] for row in scaffold_rows if row.get("next_trade_date"))
    for code in codes:
        try:
            price_by_code[code] = _fetch_close_series(jq, code, min_day, max_next_day, fq="pre")
        except Exception as exc:
            warnings.append(f"{code}: price failed: {repr(exc)}")
            price_by_code[code] = {}

    try:
        benchmark_closes = _fetch_close_series(jq, benchmark, min_day, max_next_day, fq=benchmark_fq)
    except Exception as exc:
        warnings.append(f"{benchmark}: benchmark failed: {repr(exc)}")
        benchmark_closes = {}

    rows: list[dict[str, Any]] = []
    for item in scaffold_rows:
        trade_day = item["trade_date"]
        next_day = item["next_trade_date"]
        code = item["code"]
        close = _value_as_of(price_by_code.get(code, {}), trade_day)
        next_close = _value_as_of(price_by_code.get(code, {}), next_day)
        if close is None or next_close is None or close <= 0:
            continue
        price_return = next_close / close - 1.0
        dividend_return = _holding_period_dividend_return(
            dividends.get(code, []),
            trade_day,
            next_day,
            close,
            dividend_tax_rate,
        )
        total_return = price_return
        benchmark_return = _period_return(benchmark_closes, trade_day, next_day)
        fundamentals = fundamentals_by_date.get(trade_day.isoformat(), {}).get(code, {})
        quality = _latest_visible_bank_quality(bank_quality.get(code, []), trade_day)
        rows.append(
            {
                "trade_date": trade_day.isoformat(),
                "code": code,
                "close": _fmt_float(close),
                "price_adjustment": "pre_adjusted_price",
                "next_trade_date": next_day.isoformat(),
                "price_return": _fmt_float(price_return),
                "dividend_return": _fmt_float(dividend_return),
                "total_return": _fmt_float(total_return),
                "future_return": _fmt_float(total_return),
                "return_source": "jqdata_pre_adjusted_total_return_with_dividend_attribution",
                "benchmark_return": _fmt_float(benchmark_return),
                "benchmark_source": benchmark if benchmark_return is not None else "",
                "low_price_to_book": _fmt_float(fundamentals.get("pb_ratio")),
                "dividend_yield": _fmt_float(_trailing_dividend_yield(dividends.get(code, []), trade_day, close)),
                "return_on_equity_ttm": _fmt_float(fundamentals.get("roe")),
                "non_performing_loan_ratio": _fmt_float(quality.get("npl_ratio") if quality else None),
                "provision_coverage_ratio": _fmt_float(quality.get("provision_coverage_ratio") if quality else None),
                "core_tier_1_capital_adequacy_ratio": _fmt_float(quality.get("core_tier_1_capital_adequacy_ratio") if quality else None),
                "factor_visible_date": trade_day.isoformat(),
                "factor_visibility_source": "jqdatasdk.get_fundamentals(date=trade_date)",
                "bank_quality_notice_date": quality.get("notice_date", "") if quality else "",
                "bank_quality_review_status": quality.get("review_status", "") if quality else "",
                "dividend_visible_policy": "announce_date_or_ex_date_must_be_on_or_before_trade_date",
            }
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    panel_path = out_dir / "panel.csv"
    manifest_path = out_dir / "collection_manifest.json"
    _write_csv(panel_path, PIT_PANEL_FIELDS, rows)
    manifest = {
        "dataset": "joinquant_basic_pit_panel",
        "panel": str(panel_path),
        "scaffold_panel": str(scaffold_panel),
        "database_dir": str(database_dir),
        "start_date": start_date,
        "end_date": end_date,
        "benchmark": benchmark,
        "benchmark_fq": benchmark_fq,
        "dividend_csv": str(dividend_csv or database_dir / "processed" / "bank_cash_dividends.csv"),
        "dividend_tax_rate": dividend_tax_rate,
        "bank_quality_csv": str(bank_quality_csv or database_dir / "processed" / "eastmoney_bank_quality_manual_csv.csv"),
        "bank_quality_min_review_status": bank_quality_min_review_status,
        "row_count": len(rows),
        "date_count": len({row["trade_date"] for row in rows}),
        "code_count": len({row["code"] for row in rows}),
        "warnings": warnings,
        "fields": PIT_PANEL_FIELDS,
        "limitations": [
            "Uses JoinQuant get_fundamentals(date=trade_date) as point-in-time visibility, but does not expose the original announcement date per field.",
            "Bank-specialized quality fields are sourced from the local Eastmoney annual-report extraction when a visible notice_date is available. Rows marked needs_check are not final acceptance evidence.",
            "Pre-adjusted stock prices are used for research total return; cash dividends are retained as attribution only to avoid double counting.",
        ],
        "credential_policy": f"Credentials loaded from {username_env}/{password_env} or existing authenticated jqdatasdk session. Credentials are never written.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    _write_json(manifest_path, manifest)
    return JoinQuantPitPanelResult(
        panel_path=panel_path,
        manifest_path=manifest_path,
        row_count=len(rows),
        date_count=len({row["trade_date"] for row in rows}),
        code_count=len({row["code"] for row in rows}),
        warning_count=len(warnings),
    )


def _fetch_fundamentals(jq: Any, codes: list[str], trade_day: date) -> dict[str, dict[str, Any]]:
    df = jq.get_fundamentals(
        jq.query(
            jq.valuation.code,
            jq.valuation.pb_ratio,
            jq.indicator.roe,
        ).filter(jq.valuation.code.in_(codes)),
        date=trade_day,
    )
    if df is None or getattr(df, "empty", True):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in df.to_dict("records"):
        code = str(row.get("code") or "")
        if code:
            result[code] = row
    return result


def _fetch_close_series(jq: Any, code: str, start_date: str, end_date: str, fq: str | None) -> dict[str, float]:
    df = jq.get_price(
        code,
        start_date=start_date,
        end_date=end_date,
        frequency="daily",
        fields=["close"],
        fq=fq,
        skip_paused=False,
        fill_paused=True,
        panel=False,
    )
    if df is None or getattr(df, "empty", True):
        return {}
    result: dict[str, float] = {}
    for index, row in df.iterrows():
        value = _to_float(row.get("close"))
        if value is not None:
            result[str(index)[:10]] = value
    return result


def _load_scaffold(path: Path, start_date: str, end_date: str) -> list[dict[str, Any]]:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if not row.get("trade_date") or not row.get("code") or not row.get("next_trade_date"):
                continue
            trade_day = _parse_date(row["trade_date"])
            next_day = _parse_date(row["next_trade_date"])
            if start <= trade_day <= end:
                rows.append({"trade_date": trade_day, "next_trade_date": next_day, "code": row["code"]})
    return sorted(rows, key=lambda item: (item["trade_date"], item["code"]))


@dataclass(frozen=True)
class DividendEvent:
    ex_date: date
    visible_date: date
    cash_per_share: float


def _load_dividend_events(path: Path) -> dict[str, list[DividendEvent]]:
    if not path.exists():
        return {}
    events: dict[str, list[DividendEvent]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            code = _normalize_code(row.get("code") or row.get("security") or row.get("ts_code") or "")
            ex_date = _first_date(row, ["ex_date", "ex_dividend_date", "xd_date", "pay_date"])
            visible_date = _first_date(row, ["announce_date", "ann_date", "pubDate", "pub_date", "ex_date", "pay_date"])
            cash = _first_float(row, ["cash_per_share", "cash_dividend_per_share", "dividend_per_share", "cash"])
            if not code or ex_date is None or visible_date is None or cash is None or cash <= 0:
                continue
            events.setdefault(code, []).append(DividendEvent(ex_date=ex_date, visible_date=visible_date, cash_per_share=cash))
    for code_events in events.values():
        code_events.sort(key=lambda item: item.ex_date)
    return events


def _load_bank_quality_snapshots(path: Path, min_review_status: str) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        return {}
    allowed = _allowed_review_statuses(min_review_status)
    snapshots: dict[str, list[dict[str, Any]]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            code = _normalize_code(row.get("code") or "")
            notice_date = row.get("notice_date") or ""
            if not code or not notice_date:
                continue
            if str(row.get("review_status") or "") not in allowed:
                continue
            item = dict(row)
            item["code"] = code
            item["notice_day"] = _parse_date(notice_date)
            snapshots.setdefault(code, []).append(item)
    for code_snapshots in snapshots.values():
        code_snapshots.sort(key=lambda item: (item["notice_day"], int(float(item.get("source_year") or 0))))
    return snapshots


def _latest_visible_bank_quality(snapshots: list[dict[str, Any]], trade_day: date) -> dict[str, Any] | None:
    visible = None
    for snapshot in snapshots:
        if snapshot["notice_day"] <= trade_day:
            visible = snapshot
        else:
            break
    return visible


def _allowed_review_statuses(min_review_status: str) -> set[str]:
    if min_review_status == "reviewed":
        return {"reviewed"}
    if min_review_status == "needs_check":
        return {"reviewed", "needs_check"}
    if min_review_status == "unreviewed":
        return {"reviewed", "needs_check", "unreviewed"}
    raise ValueError("min_review_status must be reviewed, needs_check, or unreviewed")


def _trailing_dividend_yield(events: list[DividendEvent], trade_day: date, close: float) -> float:
    if close <= 0:
        return 0.0
    start = date(trade_day.year - 1, trade_day.month, trade_day.day)
    cash = sum(event.cash_per_share for event in events if start < event.ex_date <= trade_day and event.visible_date <= trade_day)
    return cash / close


def _holding_period_dividend_return(events: list[DividendEvent], start: date, end: date, close: float, tax_rate: float) -> float:
    if close <= 0:
        return 0.0
    net_multiplier = max(0.0, 1.0 - tax_rate)
    cash = sum(event.cash_per_share * net_multiplier for event in events if start < event.ex_date <= end and event.visible_date <= end)
    return cash / close


def _period_return(closes: dict[str, float], start: date, end: date) -> float | None:
    start_close = _value_as_of(closes, start)
    end_close = _value_as_of(closes, end)
    if start_close is None or end_close is None or start_close <= 0:
        return None
    return end_close / start_close - 1.0


def _value_as_of(values: dict[str, float], day: date) -> float | None:
    key = day.isoformat()
    if key in values:
        return values[key]
    candidates = [item for item in values if item <= key]
    if not candidates:
        return None
    return values[max(candidates)]


def _load_authenticated_jqdata(username_env: str, password_env: str):
    try:
        import jqdatasdk as jq
    except Exception as exc:
        raise RuntimeError("jqdatasdk is required for JoinQuant PIT panel collection") from exc
    username, password = load_joinquant_credentials(username_env, password_env)
    if username and password:
        jq.auth(username, password)
    if not jq.is_auth():
        raise RuntimeError(
            f"JoinQuant credentials are not available. Set {username_env} and {password_env}, "
            "or authenticate jqdatasdk in the current environment before running this collector."
        )
    return jq


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _parse_date(value: str) -> date:
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def _first_date(row: dict[str, str], names: list[str]) -> date | None:
    for name in names:
        value = row.get(name)
        if value:
            try:
                return _parse_date(value)
            except ValueError:
                continue
    return None


def _first_float(row: dict[str, str], names: list[str]) -> float | None:
    for name in names:
        value = _to_float(row.get(name))
        if value is not None:
            return value
    return None


def _normalize_code(value: str) -> str:
    code = str(value).strip()
    if not code:
        return ""
    if "." in code:
        left, right = code.split(".", 1)
        if right.upper() in {"SZ", "XSHE"}:
            return f"{left}.XSHE"
        if right.upper() in {"SH", "XSHG", "SSE"}:
            return f"{left}.XSHG"
    return code


def _to_float(value: Any) -> float | None:
    if value in {None, "", "nan", "NaN", "None"}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt_float(value: Any) -> str:
    numeric = _to_float(value)
    if numeric is None:
        return ""
    return f"{numeric:.10g}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-joinquant-basic-pit-panel")
    parser.add_argument("scaffold_panel", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("数据库/processed/joinquant_basic_pit_panel"))
    parser.add_argument("--database-dir", type=Path, default=DEFAULT_DATABASE_DIR)
    parser.add_argument("--start-date", default="2014-01-01")
    parser.add_argument("--end-date", default="2026-05-31")
    parser.add_argument("--benchmark", default="512800.XSHG")
    parser.add_argument("--benchmark-fq", default="pre", choices=["pre", "post", "none"])
    parser.add_argument("--dividend-csv", type=Path)
    parser.add_argument("--dividend-tax-rate", type=float, default=0.2)
    parser.add_argument("--bank-quality-csv", type=Path)
    parser.add_argument("--bank-quality-min-review-status", choices=["reviewed", "needs_check", "unreviewed"], default="needs_check")
    args = parser.parse_args(argv)
    result = collect_joinquant_basic_pit_panel(
        args.scaffold_panel,
        args.out_dir,
        database_dir=args.database_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        benchmark=args.benchmark,
        benchmark_fq=None if args.benchmark_fq == "none" else args.benchmark_fq,
        dividend_csv=args.dividend_csv,
        dividend_tax_rate=args.dividend_tax_rate,
        bank_quality_csv=args.bank_quality_csv,
        bank_quality_min_review_status=args.bank_quality_min_review_status,
    )
    print(result.panel_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import json
from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

from v5.engine import load_spec


PANEL_FIELDS = [
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
]


@dataclass(frozen=True)
class Snapshot:
    visible_date: date
    values: dict[str, float]


@dataclass(frozen=True)
class DividendEvent:
    code: str
    ex_date: date
    announce_date: date | None
    cash_per_share: float


@dataclass(frozen=True)
class BenchmarkPoint:
    day: date
    close: float
    benchmark_id: str
    name: str


def collect_panel_from_v4_raw(
    spec_path: Path,
    v4_raw_dir: Path,
    out_dir: Path,
    price_adjustment: str = "unconfirmed_v4_raw",
    dividend_csv: Path | None = None,
    benchmark_csv: Path | None = None,
    benchmark_id: str = "bank_etf_512800_qfq",
    total_return_mode: str = "adjusted_total_return",
    dividend_tax_rate: float = 0.2,
) -> Path:
    spec = load_spec(spec_path)
    window = spec.raw.get("data", {}).get("window", {})
    start = _parse_date(window.get("start", "2011-01-01"))
    end = _parse_date(window.get("end", date.today().isoformat()))
    dividend_events = _load_dividend_events(dividend_csv)
    benchmark_points = _load_benchmark_points(benchmark_csv, benchmark_id)

    panel_dir = out_dir / spec.strategy_id
    panel_dir.mkdir(parents=True, exist_ok=True)
    panel_path = panel_dir / "panel.csv"
    manifest_path = panel_dir / "collection_manifest.json"
    report_path = panel_dir / "collection_report.md"

    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    bank_dirs = sorted(path for path in v4_raw_dir.iterdir() if path.is_dir())

    for bank_dir in bank_dirs:
        try:
            rows.extend(
                _collect_bank_rows(
                    bank_dir,
                    start,
                    end,
                    price_adjustment,
                    dividend_events,
                    benchmark_points,
                    benchmark_id,
                    total_return_mode,
                    dividend_tax_rate,
                )
            )
        except Exception as exc:
            warnings.append(f"{bank_dir.name}: {exc}")

    rows.sort(key=lambda item: (item["trade_date"], item["code"]))
    _write_csv(panel_path, PANEL_FIELDS, rows)

    manifest = {
        "strategy_id": spec.strategy_id,
        "source": "v4_raw_downloads",
        "source_dir": str(v4_raw_dir),
        "panel": str(panel_path),
        "row_count": len(rows),
        "bank_count": len({row["code"] for row in rows}),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "price_adjustment": price_adjustment,
        "dividend_source": str(dividend_csv) if dividend_csv else None,
        "dividend_event_count": sum(len(events) for events in dividend_events.values()),
        "benchmark_source": str(benchmark_csv) if benchmark_csv else None,
        "benchmark_id": benchmark_id if benchmark_points else None,
        "benchmark_point_count": len(benchmark_points),
        "total_return_mode": total_return_mode,
        "dividend_tax_rate": dividend_tax_rate,
        "fields": PANEL_FIELDS,
        "warnings": warnings,
        "data_quality_notes": [
            "daily_price.csv in the V4 raw folder does not include a date column; this collector aligns it to daily_valuation.csv by row order.",
            "price_adjustment is recorded explicitly in every panel row and in this manifest.",
            "Default total_return_mode is adjusted_total_return: use the migrated/adjusted price return and keep dividend_return as attribution only.",
            "When an unadjusted price source is confirmed, price_plus_net_cash_dividend computes total_return as price_return plus cash dividend after dividend_tax_rate.",
            "If price_adjustment is pre-adjusted or otherwise already total-return adjusted, adding cash dividends can double-count dividends.",
            "benchmark_return is mapped from the configured real benchmark series when benchmark_csv is supplied.",
            "When dividend_csv is not supplied, dividend_return is zero and return_source records dividend_missing.",
        ],
        "bank_indicator_policy": "V5 collector does not call JoinQuant bank_indicator. V4 raw files are treated as historical migration inputs; new production collection must use replacement or annual-report routes.",
    }
    _write_json(manifest_path, manifest)
    _write_collection_report(report_path, manifest)
    return panel_path


def write_collection_manifest(spec_path: Path, out_dir: Path) -> Path:
    spec = load_spec(spec_path)
    panel_dir = out_dir / spec.strategy_id
    panel_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = panel_dir / "collection_plan.json"
    required = [factor.name for factor in spec.factors]
    manifest = {
        "strategy_id": spec.strategy_id,
        "mode": "plan_only",
        "required_panel_fields": PANEL_FIELDS,
        "required_factors": required,
        "preferred_sources": [
            "JoinQuant for market, valuation, industry membership, and standard statements",
            "Tushare when approved and useful as fallback",
            "Annual reports for bank-specific indicators that ordinary APIs do not reliably expose",
        ],
        "blocked_sources": [
            "Direct JoinQuant bank_indicator for new V5 collection work"
        ],
        "credential_policy": "Load credentials only through the approved local secret mechanism. Do not write tokens, passwords, or raw credentials into manifests, logs, reports, or git-tracked files.",
        "return_policy": {
            "price_adjustment_field": "Required. Examples: pre_adjusted, post_adjusted, raw_unadjusted, unconfirmed_v4_raw.",
            "preferred_total_return": "Default to an explicitly documented adjusted total-return series. Use net cash dividends only when raw unadjusted prices are confirmed.",
            "dividend_tax_rate_default": 0.2,
            "dividend_csv_columns": {
                "required": "code, cash_per_share, and one date column such as ex_date, ex_dividend_date, record_date, or announce_date",
                "optional": "announce_date for point-in-time trailing dividend yield",
            },
            "benchmark_csv_columns": {
                "required": "benchmark_id, date, close",
                "default_benchmark_id": "bank_etf_512800_qfq",
            },
        },
    }
    _write_json(manifest_path, manifest)
    return manifest_path


def _collect_bank_rows(
    bank_dir: Path,
    start: date,
    end: date,
    price_adjustment: str,
    dividend_events: dict[str, list[DividendEvent]],
    benchmark_points: list[BenchmarkPoint],
    benchmark_id: str,
    total_return_mode: str,
    dividend_tax_rate: float,
) -> list[dict[str, Any]]:
    valuation_rows = _read_csv(bank_dir / "daily_valuation.csv")
    price_rows = _read_csv(bank_dir / "daily_price.csv")
    if not valuation_rows or not price_rows:
        return []

    usable_count = min(len(valuation_rows), len(price_rows))
    daily: list[dict[str, Any]] = []
    for index in range(usable_count):
        valuation = valuation_rows[index]
        price = price_rows[index]
        day = _parse_date(valuation["day"])
        if day < start or day > end:
            continue
        close = _to_float(price.get("close"))
        if close is None:
            continue
        daily.append(
            {
                "trade_date": day,
                "code": valuation.get("code", bank_dir.name.replace("_", ".")),
                "close": close,
                "pb_ratio": _to_float(valuation.get("pb_ratio")),
            }
        )

    if len(daily) < 2:
        return []

    indicator_snapshots = _load_indicator_snapshots(bank_dir / "indicator.csv")
    bank_indicator_snapshots = _load_bank_indicator_snapshots(bank_dir / "bank_indicator.csv")
    rebalance_indices = _quarterly_rebalance_indices(daily)

    rows: list[dict[str, Any]] = []
    for current_idx, next_idx in zip(rebalance_indices, rebalance_indices[1:]):
        current = daily[current_idx]
        future = daily[next_idx]
        code = current["code"]
        ind = _snapshot_as_of(indicator_snapshots, current["trade_date"])
        bank = _snapshot_as_of(bank_indicator_snapshots, current["trade_date"])
        price_return = (future["close"] / current["close"]) - 1.0
        dividends = dividend_events.get(code, [])
        dividend_return = _holding_period_dividend_return(
            dividends,
            current["trade_date"],
            future["trade_date"],
            current["close"],
            dividend_tax_rate,
        )
        if total_return_mode == "adjusted_total_return":
            total_return = price_return
            return_source = f"{price_adjustment}_adjusted_total_return"
        elif total_return_mode == "price_plus_gross_cash_dividend":
            gross_dividend_return = _holding_period_dividend_return(
                dividends,
                current["trade_date"],
                future["trade_date"],
                current["close"],
                0.0,
            )
            total_return = price_return + gross_dividend_return
            return_source = "price_plus_gross_cash_dividend" if dividends else "price_only_dividend_missing"
        else:
            total_return = price_return + dividend_return
            return_source = "price_plus_net_cash_dividend" if dividends else "price_only_dividend_missing"
        trailing_yield = _trailing_dividend_yield(dividends, current["trade_date"], current["close"])
        benchmark_return = _period_benchmark_return(benchmark_points, current["trade_date"], future["trade_date"])
        rows.append(
            {
                "trade_date": current["trade_date"].isoformat(),
                "code": code,
                "close": _fmt_float(current["close"]),
                "price_adjustment": price_adjustment,
                "next_trade_date": future["trade_date"].isoformat(),
                "price_return": _fmt_float(price_return),
                "dividend_return": _fmt_float(dividend_return),
                "total_return": _fmt_float(total_return),
                "future_return": _fmt_float(total_return),
                "return_source": return_source,
                "benchmark_return": _fmt_float(benchmark_return),
                "benchmark_source": benchmark_id if benchmark_return is not None else "",
                "low_price_to_book": _fmt_float(current["pb_ratio"]),
                "dividend_yield": _fmt_float(trailing_yield),
                "return_on_equity_ttm": _fmt_float(ind.get("return_on_equity_ttm")),
                "non_performing_loan_ratio": _fmt_float(bank.get("non_performing_loan_ratio")),
                "provision_coverage_ratio": _fmt_float(bank.get("provision_coverage_ratio")),
                "core_tier_1_capital_adequacy_ratio": _fmt_float(bank.get("core_tier_1_capital_adequacy_ratio")),
            }
        )
    return rows


def _load_benchmark_points(path: Path | None, benchmark_id: str) -> list[BenchmarkPoint]:
    if path is None or not path.exists():
        return []
    points: list[BenchmarkPoint] = []
    for row in _read_csv(path):
        if str(row.get("benchmark_id") or "") != benchmark_id:
            continue
        day = _optional_date(row.get("date"))
        close = _to_float(row.get("close"))
        if day is None or close is None:
            continue
        points.append(
            BenchmarkPoint(
                day=day,
                close=close,
                benchmark_id=benchmark_id,
                name=str(row.get("name") or benchmark_id),
            )
        )
    return sorted(points, key=lambda item: item.day)


def _period_benchmark_return(points: list[BenchmarkPoint], start: date, end: date) -> float | None:
    if not points:
        return None
    dates = [point.day for point in points]
    start_idx = bisect_right(dates, start) - 1
    end_idx = bisect_right(dates, end) - 1
    if start_idx < 0 or end_idx < 0:
        return None
    start_close = points[start_idx].close
    end_close = points[end_idx].close
    if start_close <= 0:
        return None
    return (end_close / start_close) - 1.0


def _load_dividend_events(path: Path | None) -> dict[str, list[DividendEvent]]:
    if path is None or not path.exists():
        return {}
    events: dict[str, list[DividendEvent]] = {}
    for row in _read_csv(path):
        code = _normalize_code(row.get("code") or row.get("ts_code") or row.get("security_code") or "")
        cash = _first_float(row, ["cash_per_share", "cash_dividend_per_share", "dividend_per_share", "cash_div", "cash"])
        event_date = _first_date(row, ["ex_date", "ex_dividend_date", "xd_date", "record_date", "pay_date", "announce_date"])
        announce_date = _first_date(row, ["announce_date", "ann_date", "pubDate", "pub_date"])
        if not code or cash is None or event_date is None:
            continue
        events.setdefault(code, []).append(
            DividendEvent(
                code=code,
                ex_date=event_date,
                announce_date=announce_date,
                cash_per_share=cash,
            )
        )
    for code_events in events.values():
        code_events.sort(key=lambda item: item.ex_date)
    return events


def _holding_period_dividend_return(
    events: list[DividendEvent],
    start: date,
    end: date,
    close: float,
    dividend_tax_rate: float = 0.2,
) -> float:
    if close <= 0:
        return 0.0
    net_multiplier = max(0.0, 1.0 - dividend_tax_rate)
    cash = sum(event.cash_per_share * net_multiplier for event in events if start < event.ex_date <= end)
    return cash / close


def _trailing_dividend_yield(events: list[DividendEvent], trade_date: date, close: float) -> float:
    if close <= 0:
        return 0.0
    start = date(trade_date.year - 1, trade_date.month, trade_date.day)
    cash = 0.0
    for event in events:
        visible_date = event.announce_date or event.ex_date
        if start < event.ex_date <= trade_date and visible_date <= trade_date:
            cash += event.cash_per_share
    return cash / close


def _load_indicator_snapshots(path: Path) -> list[Snapshot]:
    rows = _read_csv(path)
    snapshots: list[Snapshot] = []
    for row in rows:
        pub_date = _optional_date(row.get("pubDate"))
        if pub_date is None:
            continue
        snapshots.append(
            Snapshot(
                visible_date=pub_date,
                values={"return_on_equity_ttm": _to_float(row.get("roe"))},
            )
        )
    return sorted(snapshots, key=lambda item: item.visible_date)


def _load_bank_indicator_snapshots(path: Path) -> list[Snapshot]:
    rows = _read_csv(path)
    snapshots: list[Snapshot] = []
    for row in rows:
        pub_date = _optional_date(row.get("pubDate"))
        if pub_date is None:
            continue
        snapshots.append(
            Snapshot(
                visible_date=pub_date,
                values={
                    "non_performing_loan_ratio": _to_float(row.get("Nonperforming_loan_rate")),
                    "provision_coverage_ratio": _to_float(row.get("non_performing_loan_provision_coverage")),
                    "core_tier_1_capital_adequacy_ratio": _to_float(row.get("core_level_capital_adequacy_ratio")),
                },
            )
        )
    return sorted(snapshots, key=lambda item: item.visible_date)


def _snapshot_as_of(snapshots: list[Snapshot], trade_date: date) -> dict[str, float | None]:
    dates = [snapshot.visible_date for snapshot in snapshots]
    idx = bisect_right(dates, trade_date) - 1
    if idx < 0:
        return {}
    return snapshots[idx].values


def _quarterly_rebalance_indices(daily: list[dict[str, Any]]) -> list[int]:
    indices: list[int] = []
    seen: set[tuple[int, int]] = set()
    quarter_start_months = {1, 4, 7, 10}
    for index, row in enumerate(daily):
        day: date = row["trade_date"]
        key = (day.year, day.month)
        if day.month in quarter_start_months and key not in seen:
            seen.add(key)
            indices.append(index)
    return indices


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _write_collection_report(path: Path, manifest: dict[str, Any]) -> None:
    lines = [
        f"# Data Collection Report: {manifest['strategy_id']}",
        "",
        f"- Source: `{manifest['source']}`",
        f"- Source directory: `{manifest['source_dir']}`",
        f"- Panel: `{manifest['panel']}`",
        f"- Rows: `{manifest['row_count']}`",
        f"- Banks: `{manifest['bank_count']}`",
        f"- Window: `{manifest['start']}` to `{manifest['end']}`",
        "",
        "## Policy",
        "",
        manifest["bank_indicator_policy"],
        "",
        "## Data Quality Notes",
        "",
        *[f"- {item}" for item in manifest.get("data_quality_notes", [])],
        "",
        "## Warnings",
        "",
    ]
    warnings = manifest.get("warnings", [])
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- No collection warnings.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_date(value: str) -> date:
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def _optional_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return _parse_date(value)
    except ValueError:
        return None


def _first_date(row: dict[str, str], names: list[str]) -> date | None:
    for name in names:
        value = row.get(name)
        if value:
            return _optional_date(value)
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


def _fmt_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.10g}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-data")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path, default=Path("data/processed"))
    parser.add_argument("--mode", choices=["plan", "v4-raw"], default="plan")
    parser.add_argument("--v4-raw-dir", type=Path, default=Path(r"D:\hh\codex\v4\phase_1_fundamental\raw_downloads\all_banks"))
    parser.add_argument("--price-adjustment", default="unconfirmed_v4_raw")
    parser.add_argument("--dividend-csv", type=Path)
    parser.add_argument("--benchmark-csv", type=Path)
    parser.add_argument("--benchmark-id", default="bank_etf_512800_qfq")
    parser.add_argument(
        "--total-return-mode",
        choices=["adjusted_total_return", "price_plus_net_cash_dividend", "price_plus_gross_cash_dividend"],
        default="adjusted_total_return",
    )
    parser.add_argument("--dividend-tax-rate", type=float, default=0.2)
    args = parser.parse_args(argv)

    if args.mode == "plan":
        print(write_collection_manifest(args.spec, args.out))
        return 0
    if args.mode == "v4-raw":
        print(
            collect_panel_from_v4_raw(
                args.spec,
                args.v4_raw_dir,
                args.out,
                price_adjustment=args.price_adjustment,
                dividend_csv=args.dividend_csv,
                benchmark_csv=args.benchmark_csv,
                benchmark_id=args.benchmark_id,
                total_return_mode=args.total_return_mode,
                dividend_tax_rate=args.dividend_tax_rate,
            )
        )
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

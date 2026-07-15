from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_DATABASE_DIR = Path("数据库")
DEFAULT_REAL_PRICE_PROCESSED = DEFAULT_DATABASE_DIR / "processed" / "joinquant_real_daily_prices.csv"
DEFAULT_REAL_BENCHMARK_PROCESSED = DEFAULT_DATABASE_DIR / "processed" / "joinquant_real_benchmark_prices.csv"
DEFAULT_REAL_DIVIDEND_PROCESSED = DEFAULT_DATABASE_DIR / "processed" / "joinquant_cash_dividends.csv"


@dataclass(frozen=True)
class JoinQuantRealDataResult:
    price_path: Path
    benchmark_path: Path
    dividend_path: Path
    manifest_path: Path
    code_count: int
    price_row_count: int
    benchmark_row_count: int
    dividend_row_count: int
    warning_count: int


def collect_joinquant_real_data(
    panel_path: Path,
    database_dir: Path = DEFAULT_DATABASE_DIR,
    start_date: str = "2021-05-01",
    end_date: str = "2026-05-31",
    benchmark: str = "512800.XSHG",
    benchmark_fq: str = "pre",
    dividend_csv: Path | None = None,
    dividend_tax_rate: float = 0.2,
    username_env: str = "JQDATA_USERNAME",
    password_env: str = "JQDATA_PASSWORD",
) -> JoinQuantRealDataResult:
    jq = _load_authenticated_jqdata(username_env, password_env)
    codes = _load_codes_from_panel(panel_path)
    processed_dir = database_dir / "processed"
    raw_dir = database_dir / "raw" / "joinquant_real"
    manifest_dir = database_dir / "manifests"
    processed_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    price_rows: list[dict[str, Any]] = []
    for code in codes:
        try:
            price_rows.extend(_fetch_jq_price_rows(jq, code, start_date, end_date, "stock"))
        except Exception as exc:
            warnings.append(f"{code}: price collection failed: {repr(exc)}")

    benchmark_rows: list[dict[str, Any]] = []
    try:
        benchmark_rows = _fetch_jq_price_rows(jq, benchmark, start_date, end_date, "benchmark", fq=benchmark_fq)
    except Exception as exc:
        warnings.append(f"{benchmark}: benchmark collection failed: {repr(exc)}")

    if dividend_csv is None:
        candidate = database_dir / "processed" / "bank_cash_dividends.csv"
        dividend_csv = candidate if candidate.exists() else None
    dividend_rows = _load_dividend_rows(dividend_csv, start_date, end_date, dividend_tax_rate)
    if dividend_csv is None:
        warnings.append("dividend_csv missing; joinquant_cash_dividends.csv will contain headers only")

    price_path = processed_dir / "joinquant_real_daily_prices.csv"
    benchmark_path = processed_dir / "joinquant_real_benchmark_prices.csv"
    dividend_path = processed_dir / "joinquant_cash_dividends.csv"
    _write_csv(
        price_path,
        [
            "date",
            "code",
            "open",
            "close",
            "high",
            "low",
            "volume",
            "money",
            "high_limit",
            "low_limit",
            "paused",
            "price_adjustment",
            "source",
        ],
        price_rows,
    )
    _write_csv(
        benchmark_path,
        [
            "date",
            "code",
            "open",
            "close",
            "high",
            "low",
            "volume",
            "money",
            "price_adjustment",
            "source",
        ],
        benchmark_rows,
    )
    _write_csv(
        dividend_path,
        [
            "code",
            "report_period",
            "announce_date",
            "record_date",
            "ex_date",
            "pay_date",
            "cash_per_share",
            "dividend_tax_rate",
            "net_cash_per_share",
            "source",
        ],
        dividend_rows,
    )

    manifest = {
        "dataset": "joinquant_real_execution_data",
        "panel": str(panel_path),
        "database_dir": str(database_dir),
        "price_path": str(price_path),
        "benchmark_path": str(benchmark_path),
        "dividend_path": str(dividend_path),
        "benchmark": benchmark,
        "benchmark_fq": benchmark_fq,
        "start_date": start_date,
        "end_date": end_date,
        "price_policy": "Stock execution prices use JoinQuant get_price fq=None. Benchmark prices default to get_price fq=pre to match JoinQuant benchmark performance display.",
        "dividend_policy": "Cash dividends are represented as cash events. net_cash_per_share = cash_per_share * (1 - dividend_tax_rate). pay_date falls back to ex_date when no payment date is available.",
        "dividend_source": str(dividend_csv) if dividend_csv else None,
        "dividend_tax_rate": dividend_tax_rate,
        "credential_policy": f"Credentials loaded from {username_env}/{password_env} or an existing jqdatasdk authenticated session. Credentials are never written.",
        "code_count": len(codes),
        "price_row_count": len(price_rows),
        "benchmark_row_count": len(benchmark_rows),
        "dividend_row_count": len(dividend_rows),
        "warnings": warnings,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "agent_access": ["Quant Validation Agent", "Engineering Agent"],
    }
    manifest_path = manifest_dir / "joinquant_real_execution_data_manifest.json"
    _write_json(manifest_path, manifest)
    return JoinQuantRealDataResult(
        price_path=price_path,
        benchmark_path=benchmark_path,
        dividend_path=dividend_path,
        manifest_path=manifest_path,
        code_count=len(codes),
        price_row_count=len(price_rows),
        benchmark_row_count=len(benchmark_rows),
        dividend_row_count=len(dividend_rows),
        warning_count=len(warnings),
    )


def _load_authenticated_jqdata(username_env: str, password_env: str):
    try:
        import jqdatasdk as jq
    except Exception as exc:
        raise RuntimeError("jqdatasdk is required for JoinQuant real data collection") from exc

    username = os.environ.get(username_env)
    password = os.environ.get(password_env)
    if username and password:
        jq.auth(username, password)
    if not jq.is_auth():
        raise RuntimeError(
            f"JoinQuant credentials are not available. Set {username_env} and {password_env}, "
            "or authenticate jqdatasdk in the current environment before running this collector."
        )
    return jq


def _fetch_jq_price_rows(
    jq: Any,
    code: str,
    start_date: str,
    end_date: str,
    asset_type: str,
    fq: str | None = None,
) -> list[dict[str, Any]]:
    fields = ["open", "close", "high", "low", "volume", "money", "high_limit", "low_limit", "paused"]
    if asset_type == "benchmark":
        fields = ["open", "close", "high", "low", "volume", "money"]
    df = jq.get_price(
        code,
        start_date=start_date,
        end_date=end_date,
        frequency="daily",
        fields=fields,
        skip_paused=False,
        fq=fq,
        panel=False,
        fill_paused=True,
    )
    if df is None or getattr(df, "empty", True):
        return []
    rows: list[dict[str, Any]] = []
    for index, row in df.iterrows():
        rows.append(
            {
                "date": str(index)[:10],
                "code": code,
                "open": _fmt_float(row.get("open")),
                "close": _fmt_float(row.get("close")),
                "high": _fmt_float(row.get("high")),
                "low": _fmt_float(row.get("low")),
                "volume": _fmt_float(row.get("volume")),
                "money": _fmt_float(row.get("money")),
                "high_limit": _fmt_float(row.get("high_limit")),
                "low_limit": _fmt_float(row.get("low_limit")),
                "paused": _fmt_float(row.get("paused")),
                "price_adjustment": "raw_unadjusted_real_price" if fq is None else f"{fq}_adjusted_price",
                "source": f"jqdatasdk.get_price(fq={fq})",
            }
        )
    return rows


def _load_dividend_rows(path: Path | None, start_date: str, end_date: str, dividend_tax_rate: float) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    rows: list[dict[str, Any]] = []
    for row in _read_csv(path):
        code = row.get("code") or row.get("security") or row.get("security_code")
        ex_date = row.get("ex_date") or row.get("ex_dividend_date") or row.get("xd_date")
        if not code or not ex_date:
            continue
        ex_day = _parse_date(ex_date)
        if ex_day < start or ex_day > end:
            continue
        cash = _to_float(row.get("cash_per_share") or row.get("dividend_per_share") or row.get("cash"))
        if cash is None or cash <= 0:
            continue
        pay_date = row.get("pay_date") or row.get("payment_date") or row.get("dividend_payment_date") or ex_date
        rows.append(
            {
                "code": code,
                "report_period": row.get("report_period", ""),
                "announce_date": row.get("announce_date", ""),
                "record_date": row.get("record_date", ""),
                "ex_date": ex_date,
                "pay_date": pay_date,
                "cash_per_share": _fmt_float(cash),
                "dividend_tax_rate": _fmt_float(dividend_tax_rate),
                "net_cash_per_share": _fmt_float(cash * max(0.0, 1.0 - dividend_tax_rate)),
                "source": row.get("source") or f"normalized:{path}",
            }
        )
    return sorted(rows, key=lambda item: (item["pay_date"], item["code"]))


def _load_codes_from_panel(panel_path: Path) -> list[str]:
    with panel_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sorted({row["code"] for row in csv.DictReader(handle) if row.get("code")})


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


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


def _parse_date(value: str):
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


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
    parser = argparse.ArgumentParser(prog="v5-joinquant-real-data")
    parser.add_argument("panel", type=Path)
    parser.add_argument("--database-dir", type=Path, default=DEFAULT_DATABASE_DIR)
    parser.add_argument("--start-date", default="2021-05-01")
    parser.add_argument("--end-date", default="2026-05-31")
    parser.add_argument("--benchmark", default="512800.XSHG")
    parser.add_argument("--benchmark-fq", default="pre", choices=["pre", "post", "none"])
    parser.add_argument("--dividend-csv", type=Path)
    parser.add_argument("--dividend-tax-rate", type=float, default=0.2)
    args = parser.parse_args(argv)
    result = collect_joinquant_real_data(
        args.panel,
        database_dir=args.database_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        benchmark=args.benchmark,
        benchmark_fq=None if args.benchmark_fq == "none" else args.benchmark_fq,
        dividend_csv=args.dividend_csv,
        dividend_tax_rate=args.dividend_tax_rate,
    )
    print(result.price_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

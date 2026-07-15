from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DATABASE_DIR = Path("数据库")
DEFAULT_BENCHMARK_PROCESSED = DEFAULT_DATABASE_DIR / "processed" / "bank_benchmarks.csv"
DEFAULT_BENCHMARK_ID = "bank_etf_512800_qfq"


@dataclass(frozen=True)
class BenchmarkCollectionResult:
    processed_path: Path
    raw_dir: Path
    manifest_path: Path
    benchmark_count: int
    row_count: int
    warning_count: int


def collect_bank_benchmarks(
    database_dir: Path = DEFAULT_DATABASE_DIR,
    start_date: str = "2011-01-01",
    end_date: str = "2026-07-14",
) -> BenchmarkCollectionResult:
    try:
        import akshare as ak
    except Exception as exc:  # pragma: no cover - optional dependency guard.
        raise RuntimeError("collect-bank-benchmarks requires akshare in the local Python environment") from exc

    raw_dir = database_dir / "raw" / "benchmarks"
    processed_dir = database_dir / "processed"
    manifest_dir = database_dir / "manifests"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    processed_rows: list[dict[str, Any]] = []
    warnings: list[str] = []

    benchmark_specs = [
        {
            "benchmark_id": "bank_etf_512800_qfq",
            "name": "银行ETF 512800 前复权",
            "asset_type": "tradable_etf",
            "source": "akshare.fund_etf_hist_em",
            "adjustment": "qfq",
            "collector": "etf",
            "symbol": "512800",
        },
        {
            "benchmark_id": "csi_bank_399986",
            "name": "中证银行指数 399986",
            "asset_type": "index",
            "source": "akshare.stock_zh_index_hist_csindex",
            "adjustment": "index_price",
            "collector": "csindex",
            "symbol": "399986",
        },
        {
            "benchmark_id": "csi_300_bank_000951",
            "name": "沪深300银行指数 000951",
            "asset_type": "index",
            "source": "akshare.stock_zh_index_hist_csindex",
            "adjustment": "index_price",
            "collector": "csindex",
            "symbol": "000951",
        },
    ]

    for spec in benchmark_specs:
        try:
            if spec["collector"] == "etf":
                df = ak.fund_etf_hist_em(
                    symbol=spec["symbol"],
                    period="daily",
                    start_date=start_date.replace("-", ""),
                    end_date=end_date.replace("-", ""),
                    adjust="qfq",
                )
            else:
                df = ak.stock_zh_index_hist_csindex(
                    symbol=spec["symbol"],
                    start_date=start_date.replace("-", ""),
                    end_date=end_date.replace("-", ""),
                )
        except Exception as exc:
            warnings.append(f"{spec['benchmark_id']}: {repr(exc)}")
            continue
        if df is None or df.empty:
            warnings.append(f"{spec['benchmark_id']}: no rows returned")
            continue

        raw_path = raw_dir / f"{spec['benchmark_id']}.csv"
        df.to_csv(raw_path, index=False, encoding="utf-8-sig")

        for row in df.to_dict(orient="records"):
            normalized = _normalize_benchmark_row(spec, row)
            if normalized:
                processed_rows.append(normalized)

    processed_rows.sort(key=lambda item: (item["benchmark_id"], item["date"]))
    processed_path = processed_dir / "bank_benchmarks.csv"
    _write_csv(
        processed_path,
        [
            "benchmark_id",
            "name",
            "asset_type",
            "symbol",
            "date",
            "open",
            "close",
            "volume",
            "amount",
            "source",
            "adjustment",
        ],
        processed_rows,
    )

    manifest = {
        "dataset": "bank_benchmarks",
        "database_dir": str(database_dir),
        "processed_path": str(processed_path),
        "raw_dir": str(raw_dir),
        "start_date": start_date,
        "end_date": end_date,
        "default_benchmark_id": DEFAULT_BENCHMARK_ID,
        "benchmarks": benchmark_specs,
        "row_count": len(processed_rows),
        "warnings": warnings,
        "schema": {
            "benchmark_id": "Stable identifier used by data_runner to map period benchmark returns.",
            "date": "Trading date.",
            "close": "Close level after the stated adjustment policy.",
            "adjustment": "qfq for ETF front-adjusted prices; index_price for index levels.",
        },
        "agent_access": ["Quant Validation Agent", "Engineering Agent"],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    manifest_path = manifest_dir / "bank_benchmarks_manifest.json"
    _write_json(manifest_path, manifest)

    return BenchmarkCollectionResult(
        processed_path=processed_path,
        raw_dir=raw_dir,
        manifest_path=manifest_path,
        benchmark_count=len({row["benchmark_id"] for row in processed_rows}),
        row_count=len(processed_rows),
        warning_count=len(warnings),
    )


def _normalize_benchmark_row(spec: dict[str, Any], row: dict[str, Any]) -> dict[str, str] | None:
    day = _date_text(row.get("日期"))
    close = _to_float(row.get("收盘"))
    if not day or close is None:
        return None
    return {
        "benchmark_id": spec["benchmark_id"],
        "name": spec["name"],
        "asset_type": spec["asset_type"],
        "symbol": spec["symbol"],
        "date": day,
        "open": _fmt_float(_to_float(row.get("开盘"))),
        "close": _fmt_float(close),
        "volume": _fmt_float(_to_float(row.get("成交量"))),
        "amount": _fmt_float(_to_float(row.get("成交额") or row.get("成交金额"))),
        "source": spec["source"],
        "adjustment": spec["adjustment"],
    }


def _date_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if not text or text == "NaT" or text.lower() == "nan":
        return ""
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date().isoformat()
    except ValueError:
        return ""


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


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-benchmarks")
    parser.add_argument("--database-dir", type=Path, default=DEFAULT_DATABASE_DIR)
    parser.add_argument("--start-date", default="2011-01-01")
    parser.add_argument("--end-date", default="2026-07-14")
    args = parser.parse_args(argv)

    result = collect_bank_benchmarks(args.database_dir, args.start_date, args.end_date)
    print(result.processed_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.daily_backtest import run_daily_joinquant_like_backtest
from v5.local_backtest import BacktestOptions, _parse_date, _to_float, _write_csv, _write_json


DEFAULT_OUT_DIR = Path("local_daily_backtests_insurance_v53c")
DEFAULT_BENCHMARK_ID = "insurance_core_equal_weight"


def check_insurance_daily_backtest_ready(
    panel_path: Path,
    execution_price_csv: Path,
    start_date: str = "2021-05-01",
    end_date: str = "2026-05-31",
    dividend_cash_csv: Path | None = None,
) -> dict[str, Any]:
    required = {
        "panel_path": panel_path,
        "execution_price_csv": execution_price_csv,
    }
    missing = [name for name, path in required.items() if not path.exists()]
    panel_dates = _panel_dates(panel_path, start_date, end_date) if panel_path.exists() else []
    price_dates = _price_dates(execution_price_csv, start_date, end_date) if execution_price_csv.exists() else []
    price_codes = _price_codes(execution_price_csv, start_date, end_date) if execution_price_csv.exists() else []
    dividend_exists = dividend_cash_csv.exists() if dividend_cash_csv else False
    blockers = list(missing)
    if execution_price_csv.exists() and not price_dates:
        blockers.append("execution_price_csv_has_no_window_rows")
    if panel_dates and price_dates:
        missing_rebalance_dates = [day for day in panel_dates if day not in price_dates]
        if missing_rebalance_dates:
            blockers.append("execution_price_csv_missing_rebalance_dates")
    return {
        "status": "ready" if not blockers else "blocked",
        "blockers": blockers,
        "window": {"start_date": start_date, "end_date": end_date},
        "panel_rebalance_dates": len(panel_dates),
        "execution_price_dates": len(price_dates),
        "execution_price_codes": len(price_codes),
        "dividend_cash_csv": str(dividend_cash_csv) if dividend_cash_csv else None,
        "dividend_cash_csv_exists": dividend_exists,
        "benchmark_policy": "Build an internal equal-weight benchmark from the same PIT core insurance universe daily close prices.",
        "notes": [
            "This is an engineering smoke test, not platform replication.",
            "The internal equal-weight insurance benchmark avoids using the bank ETF as a proxy.",
            "Dividend cash CSV is optional for a first smoke run, but required before platform replication.",
        ],
    }


def build_insurance_equal_weight_benchmark(
    execution_price_csv: Path,
    out_path: Path,
    benchmark_id: str = DEFAULT_BENCHMARK_ID,
    start_date: str = "2021-05-01",
    end_date: str = "2026-05-31",
    base_close: float = 1000.0,
) -> Path:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    by_date: dict[str, dict[str, float]] = defaultdict(dict)
    for row in _read_csv(execution_price_csv):
        day_text = row.get("date") or row.get("trade_date") or row.get("day")
        code = row.get("code") or row.get("security")
        close = _to_float(row.get("close"))
        if not day_text or not code or close is None or close <= 0:
            continue
        day = _parse_date(day_text)
        if start <= day <= end:
            by_date[day.isoformat()][code] = close

    benchmark_close = base_close
    previous_close_by_code: dict[str, float] = {}
    rows: list[dict[str, Any]] = []
    for day in sorted(by_date):
        current = by_date[day]
        daily_returns = []
        for code, close in current.items():
            previous = previous_close_by_code.get(code)
            if previous is not None and previous > 0:
                daily_returns.append((close / previous) - 1.0)
        if daily_returns:
            benchmark_close *= 1.0 + (sum(daily_returns) / len(daily_returns))
        rows.append(
            {
                "date": day,
                "code": benchmark_id,
                "close": f"{benchmark_close:.10g}",
                "member_count": len(current),
                "return_member_count": len(daily_returns),
                "source": "internal_equal_weight_core_insurance_from_joinquant_real_close",
            }
        )
        previous_close_by_code.update(current)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(out_path, ["date", "code", "close", "member_count", "return_member_count", "source"], rows)
    return out_path


def run_insurance_daily_joinquant_like_backtest(
    spec_path: Path,
    panel_path: Path,
    execution_price_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
    benchmark_csv: Path | None = None,
    benchmark_id: str = DEFAULT_BENCHMARK_ID,
    dividend_cash_csv: Path | None = None,
    options: BacktestOptions | None = None,
) -> Path:
    options = options or BacktestOptions(execution_mode="joinquant_like", value_trap_guard_mode="disabled")
    if options.value_trap_guard_mode == "apply":
        options = replace(options, value_trap_guard_mode="disabled")
    readiness = check_insurance_daily_backtest_ready(
        panel_path,
        execution_price_csv,
        options.start_date,
        options.end_date,
        dividend_cash_csv,
    )
    if readiness["status"] != "ready":
        raise RuntimeError("insurance daily backtest is not ready: " + ";".join(readiness["blockers"]))
    out_dir.mkdir(parents=True, exist_ok=True)
    built_internal_benchmark = benchmark_csv is None
    if benchmark_csv is None:
        benchmark_csv = out_dir / f"{benchmark_id}.csv"
        build_insurance_equal_weight_benchmark(
            execution_price_csv,
            benchmark_csv,
            benchmark_id=benchmark_id,
            start_date=options.start_date,
            end_date=options.end_date,
        )
    summary_path = run_daily_joinquant_like_backtest(
        spec_path,
        panel_path,
        v4_raw_dir=Path("."),
        benchmark_csv=benchmark_csv,
        out_dir=out_dir,
        options=options,
        benchmark_id=benchmark_id,
        execution_price_csv=execution_price_csv,
        dividend_cash_csv=dividend_cash_csv,
        experiment_layer="engineering_smoke_test",
    )
    _append_engineering_context(summary_path, readiness, benchmark_csv, benchmark_id, dividend_cash_csv, built_internal_benchmark)
    _ensure_empty_dividend_log(summary_path.parent / "dividends.csv")
    return summary_path


def _append_engineering_context(
    summary_path: Path,
    readiness: dict[str, Any],
    benchmark_csv: Path,
    benchmark_id: str,
    dividend_cash_csv: Path | None,
    built_internal_benchmark: bool,
) -> None:
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    payload["mode"] = "insurance_daily_joinquant_like_smoke_test"
    payload["readiness"] = readiness
    payload["benchmark_policy"] = {
        "benchmark_id": benchmark_id,
        "benchmark_csv": str(benchmark_csv),
        "type": "internal_equal_weight_core_insurance" if built_internal_benchmark else "external_joinquant_benchmark",
        "reason": (
            "No external benchmark was supplied, so the runner built an internal equal-weight benchmark from core insurance closes."
            if built_internal_benchmark
            else "External benchmark CSV was supplied by Engineering Agent; verify that it is insurance-appropriate before platform replication."
        ),
    }
    payload["dividend_status"] = {
        "dividend_cash_csv": str(dividend_cash_csv) if dividend_cash_csv else None,
        "status": "provided" if dividend_cash_csv and dividend_cash_csv.exists() else "missing_for_smoke_test",
        "required_before": "platform_replication",
    }
    payload["engineering_gate"] = "local_daily_simulation_completed_not_platform_replication"
    payload["created_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    notes = list(payload.get("notes", []))
    notes.append("Insurance benchmark is internal equal-weight core insurance, not bank ETF.")
    if not dividend_cash_csv or not dividend_cash_csv.exists():
        notes.append("Cash-dividend events are missing; dividend reconciliation is incomplete before platform replication.")
    payload["notes"] = notes
    _write_json(summary_path, payload)


def _ensure_empty_dividend_log(path: Path) -> None:
    if path.exists():
        return
    _write_csv(path, ["trade_date", "code", "amount", "net_cash_per_share", "dividend_cash"], [])


def _panel_dates(path: Path, start_date: str, end_date: str) -> list[str]:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    dates = set()
    for row in _read_csv(path):
        day_text = row.get("trade_date")
        if not day_text:
            continue
        day = _parse_date(day_text)
        if start <= day <= end:
            dates.add(day.isoformat())
    return sorted(dates)


def _price_dates(path: Path, start_date: str, end_date: str) -> list[str]:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    dates = set()
    for row in _read_csv(path):
        day_text = row.get("date") or row.get("trade_date") or row.get("day")
        close = _to_float(row.get("close"))
        if not day_text or close is None or close <= 0:
            continue
        day = _parse_date(day_text)
        if start <= day <= end:
            dates.add(day.isoformat())
    return sorted(dates)


def _price_codes(path: Path, start_date: str, end_date: str) -> list[str]:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    codes = set()
    for row in _read_csv(path):
        day_text = row.get("date") or row.get("trade_date") or row.get("day")
        code = row.get("code") or row.get("security")
        if not day_text or not code:
            continue
        day = _parse_date(day_text)
        if start <= day <= end:
            codes.add(code)
    return sorted(codes)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-insurance-daily-backtest")
    subparsers = parser.add_subparsers(dest="command", required=True)
    ready = subparsers.add_parser("ready")
    ready.add_argument("--panel", type=Path, required=True)
    ready.add_argument("--execution-price-csv", type=Path, required=True)
    ready.add_argument("--dividend-cash-csv", type=Path)
    ready.add_argument("--start-date", default="2021-05-01")
    ready.add_argument("--end-date", default="2026-05-31")
    benchmark = subparsers.add_parser("build-benchmark")
    benchmark.add_argument("--execution-price-csv", type=Path, required=True)
    benchmark.add_argument("--out", type=Path, required=True)
    benchmark.add_argument("--benchmark-id", default=DEFAULT_BENCHMARK_ID)
    benchmark.add_argument("--start-date", default="2021-05-01")
    benchmark.add_argument("--end-date", default="2026-05-31")
    run = subparsers.add_parser("run")
    run.add_argument("spec", type=Path)
    run.add_argument("--panel", type=Path, required=True)
    run.add_argument("--execution-price-csv", type=Path, required=True)
    run.add_argument("--benchmark-csv", type=Path)
    run.add_argument("--benchmark-id", default=DEFAULT_BENCHMARK_ID)
    run.add_argument("--dividend-cash-csv", type=Path)
    run.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    run.add_argument("--start-date", default="2021-05-01")
    run.add_argument("--end-date", default="2026-05-31")
    run.add_argument("--initial-cash", type=float, default=2_000_000.0)
    args = parser.parse_args(argv)
    if args.command == "ready":
        print(
            json.dumps(
                check_insurance_daily_backtest_ready(
                    args.panel,
                    args.execution_price_csv,
                    args.start_date,
                    args.end_date,
                    args.dividend_cash_csv,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "build-benchmark":
        print(build_insurance_equal_weight_benchmark(args.execution_price_csv, args.out, args.benchmark_id, args.start_date, args.end_date))
        return 0
    print(
        run_insurance_daily_joinquant_like_backtest(
            args.spec,
            args.panel,
            args.execution_price_csv,
            args.out,
            args.benchmark_csv,
            args.benchmark_id,
            args.dividend_cash_csv,
            options=BacktestOptions(
                execution_mode="joinquant_like",
                start_date=args.start_date,
                end_date=args.end_date,
                initial_cash=args.initial_cash,
            ),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

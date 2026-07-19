from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from v5.local_backtest import _parse_date, _to_float, _write_csv


def build_equal_weight_benchmark(
    execution_price_csv: Path,
    out_path: Path,
    *,
    benchmark_id: str,
    source_label: str,
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
                "source": source_label,
            }
        )
        previous_close_by_code.update(current)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(out_path, ["date", "code", "close", "member_count", "return_member_count", "source"], rows)
    return out_path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-equal-weight-benchmark")
    parser.add_argument("execution_price_csv", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--benchmark-id", required=True)
    parser.add_argument("--source-label", default="internal_equal_weight_benchmark_from_joinquant_real_close")
    parser.add_argument("--start-date", default="2021-05-01")
    parser.add_argument("--end-date", default="2026-05-31")
    parser.add_argument("--base-close", type=float, default=1000.0)
    args = parser.parse_args(argv)
    print(
        build_equal_weight_benchmark(
            args.execution_price_csv,
            args.out,
            benchmark_id=args.benchmark_id,
            source_label=args.source_label,
            start_date=args.start_date,
            end_date=args.end_date,
            base_close=args.base_close,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

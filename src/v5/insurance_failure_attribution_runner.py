from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from v5.local_backtest import _to_float, _write_csv, _write_json


def run_insurance_failure_year_attribution(
    daily_returns_csv: Path,
    rebalance_signals_csv: Path,
    trades_csv: Path,
    dividends_csv: Path,
    out_dir: Path,
    strategy_id: str = "insurance_low_pb_only_v53c",
    years: list[str] | None = None,
) -> Path:
    years = years or ["2021", "2026"]
    daily_rows = _read_csv(daily_returns_csv)
    signal_rows = _read_csv(rebalance_signals_csv)
    trade_rows = _read_csv(trades_csv)
    dividend_rows = _read_csv(dividends_csv)
    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    worst_day_rows = []
    signal_year_rows = []
    for year in years:
        daily = [row for row in daily_rows if str(row.get("trade_date", "")).startswith(year)]
        trades = [row for row in trade_rows if str(row.get("trade_date", "")).startswith(year)]
        dividends = [row for row in dividend_rows if str(row.get("trade_date", "")).startswith(year)]
        signals = [row for row in signal_rows if str(row.get("trade_date", "")).startswith(year)]
        strategy_returns = [_to_float(row.get("strategy_return")) or 0.0 for row in daily]
        benchmark_returns = [_to_float(row.get("benchmark_return")) or 0.0 for row in daily]
        summary_rows.append(
            {
                "year": year,
                "daily_count": len(daily),
                "strategy_return": _compound(strategy_returns),
                "benchmark_return": _compound(benchmark_returns),
                "excess_return": _compound(strategy_returns) - _compound(benchmark_returns),
                "max_drawdown": _max_drawdown(strategy_returns),
                "dividend_cash": sum(_to_float(row.get("dividend_cash")) or 0.0 for row in dividends),
                "dividend_event_count": len(dividends),
                "trade_count": len([row for row in trades if str(row.get("side", "")).endswith("skipped") is False]),
                "buy_turnover": sum(_to_float(row.get("value")) or 0.0 for row in trades if row.get("side") == "buy"),
                "sell_turnover": sum(_to_float(row.get("value")) or 0.0 for row in trades if row.get("side") == "sell"),
                "signal_count": len(signals),
                "selected_codes_by_rebalance": " | ".join(f"{row.get('trade_date')}:{row.get('selected_codes')}" for row in signals),
                "interpretation": _interpret_year(year, strategy_returns, benchmark_returns, dividends, signals),
            }
        )
        for row in sorted(daily, key=lambda item: _to_float(item.get("strategy_return")) or 0.0)[:10]:
            worst_day_rows.append(
                {
                    "year": year,
                    "trade_date": row.get("trade_date"),
                    "strategy_return": row.get("strategy_return"),
                    "benchmark_return": row.get("benchmark_return"),
                    "excess_return": row.get("excess_return"),
                    "strategy_nav": row.get("strategy_nav"),
                    "benchmark_nav": row.get("benchmark_nav"),
                    "cash_weight": row.get("cash_weight"),
                    "selected_codes": row.get("selected_codes"),
                    "dividend_cash": row.get("dividend_cash"),
                }
            )
        for row in signals:
            signal_year_rows.append(
                {
                    "year": year,
                    "trade_date": row.get("trade_date"),
                    "factor_visible_date": row.get("factor_visible_date"),
                    "external_state_visible_date": row.get("external_state_visible_date"),
                    "candidate_count": row.get("candidate_count"),
                    "guarded_count": row.get("guarded_count"),
                    "selected_count": row.get("selected_count"),
                    "used_factors": row.get("used_factors"),
                    "selected_codes": row.get("selected_codes"),
                }
            )

    _write_csv(out / "failure_year_summary.csv", list(summary_rows[0].keys()) if summary_rows else [], summary_rows)
    _write_csv(out / "failure_year_worst_days.csv", list(worst_day_rows[0].keys()) if worst_day_rows else [], worst_day_rows)
    _write_csv(out / "failure_year_rebalance_signals.csv", list(signal_year_rows[0].keys()) if signal_year_rows else [], signal_year_rows)
    payload = {
        "strategy_id": strategy_id,
        "years": years,
        "daily_returns_csv": str(daily_returns_csv),
        "rebalance_signals_csv": str(rebalance_signals_csv),
        "trades_csv": str(trades_csv),
        "dividends_csv": str(dividends_csv),
        "summary": summary_rows,
        "outputs": {
            "summary": "failure_year_summary.csv",
            "worst_days": "failure_year_worst_days.csv",
            "rebalance_signals": "failure_year_rebalance_signals.csv",
            "report": "failure_year_attribution_report.md",
        },
        "status": "completed_not_acceptance",
    }
    _write_json(out / "failure_year_attribution_summary.json", payload)
    _write_report(out / "failure_year_attribution_report.md", payload)
    return out / "failure_year_attribution_report.md"


def _compound(values: list[float]) -> float:
    nav = 1.0
    for value in values:
        nav *= 1.0 + value
    return nav - 1.0


def _max_drawdown(values: list[float]) -> float:
    nav = 1.0
    peak = 1.0
    max_dd = 0.0
    for value in values:
        nav *= 1.0 + value
        peak = max(peak, nav)
        if peak > 0:
            max_dd = max(max_dd, 1.0 - nav / peak)
    return max_dd


def _interpret_year(year: str, strategy_returns: list[float], benchmark_returns: list[float], dividends: list[dict[str, str]], signals: list[dict[str, str]]) -> str:
    strategy = _compound(strategy_returns)
    benchmark = _compound(benchmark_returns)
    dividend_cash = sum(_to_float(row.get("dividend_cash")) or 0.0 for row in dividends)
    notes = []
    notes.append("underperformed_benchmark" if strategy < benchmark else "outperformed_benchmark")
    if strategy < 0:
        notes.append("negative_absolute_return")
    if dividend_cash > 0:
        notes.append("dividends_cushioned_drawdown")
    if len(signals) <= 2:
        notes.append("few_rebalance_observations")
    if year == "2026":
        notes.append("partial_year_tail_risk")
    return ",".join(notes)


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [f"# Failure Year Attribution: {payload['strategy_id']}", "", f"- Status: `{payload['status']}`", ""]
    lines.extend(["## Summary", ""])
    for row in payload["summary"]:
        lines.extend(
            [
                f"### {row['year']}",
                "",
                f"- Strategy return: `{row['strategy_return']}`",
                f"- Benchmark return: `{row['benchmark_return']}`",
                f"- Excess return: `{row['excess_return']}`",
                f"- Max drawdown: `{row['max_drawdown']}`",
                f"- Dividend cash: `{row['dividend_cash']}`",
                f"- Dividend events: `{row['dividend_event_count']}`",
                f"- Signals: `{row['signal_count']}`",
                f"- Selected codes: `{row['selected_codes_by_rebalance']}`",
                f"- Interpretation: `{row['interpretation']}`",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-insurance-failure-attribution")
    parser.add_argument("--daily-returns-csv", type=Path, required=True)
    parser.add_argument("--rebalance-signals-csv", type=Path, required=True)
    parser.add_argument("--trades-csv", type=Path, required=True)
    parser.add_argument("--dividends-csv", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("failure_attribution_insurance_v53c"))
    parser.add_argument("--strategy-id", default="insurance_low_pb_only_v53c")
    parser.add_argument("--years", nargs="+", default=["2021", "2026"])
    args = parser.parse_args(argv)
    print(
        run_insurance_failure_year_attribution(
            args.daily_returns_csv,
            args.rebalance_signals_csv,
            args.trades_csv,
            args.dividends_csv,
            args.out,
            args.strategy_id,
            args.years,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

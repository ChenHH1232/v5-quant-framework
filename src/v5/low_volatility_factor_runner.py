from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import fmt_float, pearson, to_float


DEFAULT_OUT_DIR = Path("数据库") / "processed" / "low_volatility_factors_v56"
DEFAULT_WINDOWS = [60, 120, 252]
STATIC_LOW_VOL_FIELDS = [
    "low_vol_score",
    "low_vol_factor_visible_date",
    "low_vol_factor_source",
]


@dataclass(frozen=True)
class LowVolatilityFactorResult:
    panel_path: Path
    factor_path: Path
    manifest_path: Path
    row_count: int
    enriched_count: int
    windows: list[int]


def add_low_volatility_factors(
    panel_csv: Path,
    price_csv: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
    *,
    benchmark_csv: Path | None = None,
    strategy_id: str | None = None,
    windows: list[int] | None = None,
    min_observations: int = 40,
) -> LowVolatilityFactorResult:
    windows = windows or list(DEFAULT_WINDOWS)
    low_vol_fields = _low_vol_fields(windows)
    panel_rows = read_csv_rows(panel_csv)
    price_by_code = _load_price_series(price_csv)
    benchmark_returns = _load_benchmark_returns(benchmark_csv) if benchmark_csv else {}
    enriched_rows: list[dict[str, Any]] = []
    factor_rows: list[dict[str, Any]] = []

    for row in panel_rows:
        enriched = dict(row)
        trade_date = str(row.get("trade_date") or "")[:10]
        code = str(row.get("code") or "")
        series = price_by_code.get(code, [])
        metrics = _compute_metrics_for_date(series, trade_date, windows, min_observations, benchmark_returns)
        for key in low_vol_fields:
            enriched[key] = metrics.get(key, "")
        enriched_rows.append(enriched)
        factor_rows.append(
            {
                "trade_date": trade_date,
                "code": code,
                **{key: metrics.get(key, "") for key in low_vol_fields},
            }
        )

    out_name = strategy_id or panel_csv.stem
    out_path = out_dir / out_name
    out_path.mkdir(parents=True, exist_ok=True)
    panel_out = out_path / "panel_with_low_vol.csv"
    factor_out = out_path / "low_volatility_factors.csv"
    manifest_out = out_path / "low_volatility_factor_manifest.json"

    fieldnames = _merge_fieldnames(panel_rows, low_vol_fields)
    write_csv_rows(panel_out, fieldnames, enriched_rows)
    write_csv_rows(factor_out, ["trade_date", "code", *low_vol_fields], factor_rows)
    enriched_count = sum(1 for row in factor_rows if row.get("low_vol_score") not in (None, ""))
    write_json_file(
        manifest_out,
        {
            "dataset": "low_volatility_factors_v56",
            "strategy_id": strategy_id,
            "panel_csv": str(panel_csv),
            "price_csv": str(price_csv),
            "benchmark_csv": str(benchmark_csv) if benchmark_csv else None,
            "panel_with_low_vol": str(panel_out),
            "factor_csv": str(factor_out),
            "row_count": len(panel_rows),
            "enriched_count": enriched_count,
            "windows": windows,
            "min_observations": min_observations,
            "pit_policy": "For each trade_date, only daily closes strictly before trade_date are used. The trade_date close and all future prices are excluded.",
            "beta_policy": "Beta is computed only when a benchmark close-return series is supplied and aligned with stock returns.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return LowVolatilityFactorResult(panel_out, factor_out, manifest_out, len(panel_rows), enriched_count, windows)


def _load_price_series(path: Path) -> dict[str, list[tuple[str, float]]]:
    result: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in read_csv_rows(path):
        code = str(row.get("code") or "")
        day = str(row.get("date") or row.get("trade_date") or "")[:10]
        close = to_float(row.get("close"))
        if code and day and close is not None and close > 0:
            result[code].append((day, close))
    for rows in result.values():
        rows.sort(key=lambda item: item[0])
    return dict(result)


def _low_vol_fields(windows: list[int]) -> list[str]:
    fields: list[str] = []
    for prefix in ["volatility", "downside_volatility", "max_drawdown", "beta"]:
        for window in windows:
            fields.append(f"{prefix}_{window}d")
    fields.extend(STATIC_LOW_VOL_FIELDS)
    for window in windows:
        fields.append(f"low_vol_observation_count_{window}d")
    return fields


def _load_benchmark_returns(path: Path | None) -> dict[str, float]:
    if path is None or not path.exists():
        return {}
    rows_by_code = _load_price_series(path)
    if not rows_by_code:
        return {}
    longest = max(rows_by_code.values(), key=len)
    return _returns_by_date(longest)


def _compute_metrics_for_date(
    series: list[tuple[str, float]],
    trade_date: str,
    windows: list[int],
    min_observations: int,
    benchmark_returns: dict[str, float],
) -> dict[str, str]:
    visible = [(day, close) for day, close in series if day < trade_date]
    returns_by_date = _returns_by_date(visible)
    sorted_returns = sorted(returns_by_date.items(), key=lambda item: item[0])
    metrics: dict[str, str] = {
        "low_vol_factor_visible_date": _last_visible_date(visible),
        "low_vol_factor_source": "daily_close_returns_strictly_before_trade_date",
    }
    low_vol_parts: list[float] = []
    for window in windows:
        window_returns = sorted_returns[-window:]
        returns = [value for _day, value in window_returns]
        prices = [close for _day, close in visible[-window:]]
        obs_key = f"low_vol_observation_count_{window}d"
        metrics[obs_key] = str(len(returns))
        if len(returns) < min(min_observations, window):
            for prefix in ["volatility", "downside_volatility", "max_drawdown", "beta"]:
                metrics[f"{prefix}_{window}d"] = ""
            continue
        vol = _annualized_std(returns)
        downside = _annualized_std([ret for ret in returns if ret < 0])
        drawdown = _max_drawdown(prices)
        beta = _beta(window_returns, benchmark_returns)
        metrics[f"volatility_{window}d"] = fmt_float(vol)
        metrics[f"downside_volatility_{window}d"] = fmt_float(downside)
        metrics[f"max_drawdown_{window}d"] = fmt_float(drawdown)
        metrics[f"beta_{window}d"] = fmt_float(beta)
        if vol is not None:
            low_vol_parts.append(-vol)
        if downside is not None:
            low_vol_parts.append(-downside)
        if drawdown is not None:
            low_vol_parts.append(-drawdown)
    metrics["low_vol_score"] = fmt_float(mean(low_vol_parts) if low_vol_parts else None)
    return metrics


def _returns_by_date(series: list[tuple[str, float]]) -> dict[str, float]:
    result: dict[str, float] = {}
    previous: float | None = None
    for day, close in sorted(series, key=lambda item: item[0]):
        if previous is not None and previous > 0:
            result[day] = close / previous - 1.0
        previous = close
    return result


def _annualized_std(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    avg = mean(values)
    variance = sum((value - avg) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance) * math.sqrt(252)


def _max_drawdown(prices: list[float]) -> float | None:
    if len(prices) < 2:
        return None
    peak = prices[0]
    max_dd = 0.0
    for price in prices:
        if price > peak:
            peak = price
        if peak > 0:
            max_dd = max(max_dd, 1.0 - price / peak)
    return max_dd


def _beta(window_returns: list[tuple[str, float]], benchmark_returns: dict[str, float]) -> float | None:
    if not benchmark_returns:
        return None
    stock: list[float] = []
    benchmark: list[float] = []
    for day, stock_return in window_returns:
        benchmark_return = benchmark_returns.get(day)
        if benchmark_return is None:
            continue
        stock.append(stock_return)
        benchmark.append(benchmark_return)
    corr = pearson(stock, benchmark)
    if corr is None or len(benchmark) < 2:
        return None
    benchmark_avg = mean(benchmark)
    variance = sum((value - benchmark_avg) ** 2 for value in benchmark) / (len(benchmark) - 1)
    if variance <= 0:
        return None
    covariance = sum((s - mean(stock)) * (b - benchmark_avg) for s, b in zip(stock, benchmark)) / (len(benchmark) - 1)
    return covariance / variance


def _last_visible_date(series: list[tuple[str, float]]) -> str:
    return series[-1][0] if series else ""


def _merge_fieldnames(rows: list[dict[str, Any]], extra_fields: list[str]) -> list[str]:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    for key in extra_fields:
        if key not in fieldnames:
            fieldnames.append(key)
    return fieldnames

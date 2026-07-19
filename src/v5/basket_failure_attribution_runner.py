from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import compound, fmt_float, to_float


DEFAULT_CONFIG = Path("config/dividend_low_vol_fcf_basket_v56.json")
DEFAULT_DAILY_DIR = Path("local_daily_backtests_v56_basket") / "v56_dividend_low_vol_fcf_shadow_basket"
DEFAULT_SIGNALS = Path("validation_formal_v56_basket_constructor") / "basket_rebalance_signals.csv"
DEFAULT_OUT_DIR = Path("validation_attribution_v56_basket")


@dataclass(frozen=True)
class BasketFailureAttributionResult:
    output_dir: Path
    summary_path: Path
    report_path: Path
    yearly_count: int
    detractor_count: int
    missed_winner_count: int


def run_basket_failure_attribution(
    config_path: Path = DEFAULT_CONFIG,
    daily_dir: Path = DEFAULT_DAILY_DIR,
    signals_csv: Path = DEFAULT_SIGNALS,
    out_dir: Path = DEFAULT_OUT_DIR,
    *,
    focus_years: tuple[int, ...] = (2025, 2026),
) -> BasketFailureAttributionResult:
    config = _read_json(config_path)
    project = str(config.get("project") or "v56_dividend_low_vol_fcf_shadow_basket")
    out = out_dir / project
    out.mkdir(parents=True, exist_ok=True)

    sector_price_files = _sector_price_files(config)
    sector_dividend_files = _sector_dividend_files(config)
    prices = _load_prices(sector_price_files)
    actions = _load_actions(sector_dividend_files)
    signals = _load_signal_rows(signals_csv)
    active_targets = _daily_active_targets(sorted(prices), signals)
    daily_rows = read_csv_rows(daily_dir / "daily_returns.csv")

    yearly_rows = _yearly_summary(daily_rows)
    sector_rows, code_rows = _selected_attribution(prices, actions, active_targets)
    top_detractors = _top_detractors(code_rows, focus_years)
    missed_winners = _missed_winners(prices, actions, active_targets, focus_years)
    worst_days = _worst_excess_days(daily_rows, focus_years)
    cash_rows = _cash_drag_rows(daily_rows, focus_years)

    yearly_path = out / "yearly_performance.csv"
    sector_path = out / "yearly_sector_attribution.csv"
    code_path = out / "yearly_code_attribution.csv"
    detractors_path = out / "top_detractors_2025_2026.csv"
    missed_path = out / "missed_winners_2025_2026.csv"
    worst_days_path = out / "daily_excess_worst_days.csv"
    cash_path = out / "cash_drag_2025_2026.csv"
    summary_path = out / "failure_attribution_summary.json"
    report_path = out / "failure_attribution_report.md"

    write_csv_rows(yearly_path, _fieldnames(yearly_rows), yearly_rows)
    write_csv_rows(sector_path, _fieldnames(sector_rows), sector_rows)
    write_csv_rows(code_path, _fieldnames(code_rows), code_rows)
    write_csv_rows(detractors_path, _fieldnames(top_detractors), top_detractors)
    write_csv_rows(missed_path, _fieldnames(missed_winners), missed_winners)
    write_csv_rows(worst_days_path, _fieldnames(worst_days), worst_days)
    write_csv_rows(cash_path, _fieldnames(cash_rows), cash_rows)

    summary = {
        "schema_version": 1,
        "strategy_id": project,
        "experiment_layer": "engineering_smoke_test",
        "status": "local_failure_attribution_completed_not_acceptance",
        "config": str(config_path),
        "daily_dir": str(daily_dir),
        "signals_csv": str(signals_csv),
        "focus_years": list(focus_years),
        "yearly_performance_csv": str(yearly_path),
        "yearly_sector_attribution_csv": str(sector_path),
        "yearly_code_attribution_csv": str(code_path),
        "top_detractors_csv": str(detractors_path),
        "missed_winners_csv": str(missed_path),
        "daily_excess_worst_days_csv": str(worst_days_path),
        "cash_drag_csv": str(cash_path),
        "diagnosis": _diagnosis(yearly_rows, sector_rows, top_detractors, missed_winners, cash_rows, focus_years),
        "pm_note": "Attribution is signal-weight based and uses local daily prices plus net cash dividends and stock actions. It is for diagnosis, not factor acceptance.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_json_file(summary_path, summary)
    report_path.write_text(_report(summary), encoding="utf-8")
    return BasketFailureAttributionResult(out, summary_path, report_path, len(yearly_rows), len(top_detractors), len(missed_winners))


def _sector_price_files(config: dict[str, Any]) -> dict[str, Path]:
    return {
        str(sector.get("sector_id") or ""): Path(str(sector.get("price_csv") or ""))
        for sector in config.get("sectors", [])
        if sector.get("price_csv")
    }


def _sector_dividend_files(config: dict[str, Any]) -> dict[str, Path]:
    return {
        str(sector.get("sector_id") or ""): Path(str(sector.get("dividend_csv") or ""))
        for sector in config.get("sectors", [])
        if sector.get("dividend_csv")
    }


def _load_prices(sector_files: dict[str, Path]) -> dict[str, dict[str, dict[str, Any]]]:
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for sector_id, path in sector_files.items():
        for row in read_csv_rows(path):
            day = str(row.get("date") or row.get("trade_date") or "")[:10]
            code = str(row.get("code") or "")
            close = to_float(row.get("close"))
            if not day or not code or close is None or close <= 0:
                continue
            result.setdefault(day, {})[code] = {"close": close, "sector_id": sector_id}
    return dict(sorted(result.items()))


def _load_actions(sector_files: dict[str, Path]) -> dict[str, dict[str, dict[str, float]]]:
    result: dict[str, dict[str, dict[str, float]]] = {}
    for _sector_id, path in sector_files.items():
        if not path.exists():
            continue
        for row in read_csv_rows(path):
            day = str(row.get("ex_date") or row.get("pay_date") or "")[:10]
            code = str(row.get("code") or "")
            cash = to_float(row.get("net_cash_per_share") or row.get("cash_per_share")) or 0.0
            stock_ratio = to_float(row.get("stock_dividend_ratio"))
            if stock_ratio is None:
                bonus = to_float(row.get("bonus_share_per_10_shares")) or 0.0
                transfer = to_float(row.get("transfer_share_per_10_shares")) or 0.0
                stock_ratio = (bonus + transfer) / 10.0
            if not day or not code or (cash <= 0 and stock_ratio <= 0):
                continue
            bucket = result.setdefault(day, {}).setdefault(code, {"net_cash_per_share": 0.0, "stock_dividend_ratio": 0.0})
            bucket["net_cash_per_share"] += cash
            bucket["stock_dividend_ratio"] += stock_ratio
    return result


def _load_signal_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv_rows(path):
        weight = to_float(row.get("target_weight"))
        if weight is None or weight <= 0:
            continue
        rows.append(
            {
                "trade_date": str(row.get("trade_date") or "")[:10],
                "code": str(row.get("code") or ""),
                "sector_id": str(row.get("sector_id") or ""),
                "target_weight": weight,
                "score": to_float(row.get("score")),
            }
        )
    return sorted(rows, key=lambda item: (item["trade_date"], item["code"]))


def _daily_active_targets(price_dates: list[str], signals: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    by_signal_date: dict[str, list[dict[str, Any]]] = {}
    for row in signals:
        by_signal_date.setdefault(str(row["trade_date"]), []).append(row)
    active: dict[str, dict[str, Any]] = {}
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for day in price_dates:
        if day in by_signal_date:
            active = {str(row["code"]): row for row in by_signal_date[day]}
        if active:
            result[day] = active
    return result


def _yearly_summary(daily_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, str]]] = {}
    for row in daily_rows:
        year = str(row.get("trade_date") or "")[:4]
        if year:
            buckets.setdefault(year, []).append(row)
    result = []
    for year, rows in sorted(buckets.items()):
        strategy_returns = [to_float(row.get("strategy_return")) or 0.0 for row in rows]
        benchmark_returns = [to_float(row.get("benchmark_return")) or 0.0 for row in rows]
        excess_returns = [to_float(row.get("excess_return")) or 0.0 for row in rows]
        result.append(
            {
                "year": year,
                "daily_count": len(rows),
                "strategy_return": fmt_float(compound(strategy_returns)),
                "benchmark_return": fmt_float(compound(benchmark_returns)),
                "excess_return": fmt_float(compound(strategy_returns) - compound(benchmark_returns)),
                "mean_cash_weight": fmt_float(_mean([to_float(row.get("cash_weight")) for row in rows])),
                "rebalance_count": sum(1 for row in rows if str(row.get("rebalance")) == "1"),
                "worst_excess_day": min(rows, key=lambda row: to_float(row.get("excess_return")) or 0.0).get("trade_date", ""),
                "worst_excess_return": fmt_float(min(excess_returns) if excess_returns else None),
            }
        )
    return result


def _selected_attribution(
    prices: dict[str, dict[str, dict[str, Any]]],
    actions: dict[str, dict[str, dict[str, float]]],
    active_targets: dict[str, dict[str, dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    last_close: dict[str, float] = {}
    sector_bucket: dict[tuple[str, str], dict[str, Any]] = {}
    code_bucket: dict[tuple[str, str], dict[str, Any]] = {}
    for day, price_rows in sorted(prices.items()):
        targets = active_targets.get(day, {})
        for code, target in targets.items():
            price = price_rows.get(code)
            previous = last_close.get(code)
            if not price or previous is None or previous <= 0:
                continue
            close = to_float(price.get("close"))
            if close is None or close <= 0:
                continue
            action = actions.get(day, {}).get(code, {})
            stock_return = (action.get("stock_dividend_ratio", 0.0) or 0.0) * close / previous
            cash_return = (action.get("net_cash_per_share", 0.0) or 0.0) / previous
            total_return = close / previous - 1.0 + cash_return + stock_return
            contribution = total_return * (to_float(target.get("target_weight")) or 0.0)
            year = day[:4]
            sector_id = str(target.get("sector_id") or price.get("sector_id") or "")
            _add_contribution(sector_bucket, (year, sector_id), contribution, target.get("target_weight"), total_return)
            _add_contribution(code_bucket, (year, code), contribution, target.get("target_weight"), total_return, sector_id=sector_id)
        for code, price in price_rows.items():
            close = to_float(price.get("close"))
            if close is not None and close > 0:
                last_close[code] = close
    sector_rows = [_contribution_row("sector_id", key, value) for key, value in sector_bucket.items()]
    code_rows = [_contribution_row("code", key, value) for key, value in code_bucket.items()]
    return sorted(sector_rows, key=lambda row: (row["year"], row["sector_id"])), sorted(code_rows, key=lambda row: (row["year"], row["code"]))


def _add_contribution(
    bucket: dict[tuple[str, str], dict[str, Any]],
    key: tuple[str, str],
    contribution: float,
    target_weight: Any,
    total_return: float,
    *,
    sector_id: str = "",
) -> None:
    row = bucket.setdefault(key, {"contribution": 0.0, "weighted_return": 0.0, "weight_sum": 0.0, "day_count": 0, "sector_id": sector_id})
    weight = to_float(target_weight) or 0.0
    row["contribution"] += contribution
    row["weighted_return"] += total_return * weight
    row["weight_sum"] += weight
    row["day_count"] += 1
    if sector_id:
        row["sector_id"] = sector_id


def _contribution_row(label: str, key: tuple[str, str], value: dict[str, Any]) -> dict[str, Any]:
    year, name = key
    row = {
        "year": year,
        label: name,
        "signal_weighted_contribution_sum": fmt_float(value.get("contribution")),
        "average_daily_target_weight": fmt_float((value.get("weight_sum") or 0.0) / (value.get("day_count") or 1)),
        "selected_day_count": value.get("day_count", 0),
    }
    if label == "code":
        row["sector_id"] = value.get("sector_id", "")
    return row


def _top_detractors(code_rows: list[dict[str, Any]], focus_years: tuple[int, ...]) -> list[dict[str, Any]]:
    rows = [row for row in code_rows if int(row.get("year") or 0) in focus_years]
    rows.sort(key=lambda row: to_float(row.get("signal_weighted_contribution_sum")) or 0.0)
    return rows[:25]


def _missed_winners(
    prices: dict[str, dict[str, dict[str, Any]]],
    actions: dict[str, dict[str, dict[str, float]]],
    active_targets: dict[str, dict[str, dict[str, Any]]],
    focus_years: tuple[int, ...],
) -> list[dict[str, Any]]:
    selected_by_year = {
        str(year): {code for day, targets in active_targets.items() if day[:4] == str(year) for code in targets}
        for year in focus_years
    }
    code_returns: dict[tuple[str, str], dict[str, Any]] = {}
    last_close: dict[str, float] = {}
    for day, price_rows in sorted(prices.items()):
        year = day[:4]
        if int(year) not in focus_years:
            for code, price in price_rows.items():
                close = to_float(price.get("close"))
                if close is not None and close > 0:
                    last_close[code] = close
            continue
        for code, price in price_rows.items():
            previous = last_close.get(code)
            close = to_float(price.get("close"))
            if previous is not None and previous > 0 and close is not None and close > 0:
                action = actions.get(day, {}).get(code, {})
                stock_return = (action.get("stock_dividend_ratio", 0.0) or 0.0) * close / previous
                cash_return = (action.get("net_cash_per_share", 0.0) or 0.0) / previous
                bucket = code_returns.setdefault((year, code), {"returns": [], "sector_id": price.get("sector_id", "")})
                bucket["returns"].append(close / previous - 1.0 + cash_return + stock_return)
            if close is not None and close > 0:
                last_close[code] = close
    rows = []
    for (year, code), value in code_returns.items():
        if code in selected_by_year.get(year, set()):
            continue
        returns = value.get("returns", [])
        if len(returns) < 40:
            continue
        rows.append(
            {
                "year": year,
                "code": code,
                "sector_id": value.get("sector_id", ""),
                "same_pool_total_return": fmt_float(compound(returns)),
                "daily_count": len(returns),
                "reason": "not_selected_by_basket_signals",
            }
        )
    rows.sort(key=lambda row: to_float(row.get("same_pool_total_return")) or -999, reverse=True)
    return rows[:30]


def _worst_excess_days(daily_rows: list[dict[str, str]], focus_years: tuple[int, ...]) -> list[dict[str, Any]]:
    rows = [dict(row) for row in daily_rows if int(str(row.get("trade_date") or "0")[:4] or 0) in focus_years]
    rows.sort(key=lambda row: to_float(row.get("excess_return")) or 0.0)
    return rows[:25]


def _cash_drag_rows(daily_rows: list[dict[str, str]], focus_years: tuple[int, ...]) -> list[dict[str, Any]]:
    result = []
    for year in focus_years:
        rows = [row for row in daily_rows if str(row.get("trade_date") or "").startswith(str(year))]
        result.append(
            {
                "year": year,
                "daily_count": len(rows),
                "mean_cash_weight": fmt_float(_mean([to_float(row.get("cash_weight")) for row in rows])),
                "max_cash_weight": fmt_float(max([to_float(row.get("cash_weight")) or 0.0 for row in rows], default=0.0)),
                "cash_weight_over_10pct_days": sum(1 for row in rows if (to_float(row.get("cash_weight")) or 0.0) > 0.10),
            }
        )
    return result


def _diagnosis(
    yearly_rows: list[dict[str, Any]],
    sector_rows: list[dict[str, Any]],
    detractors: list[dict[str, Any]],
    missed_winners: list[dict[str, Any]],
    cash_rows: list[dict[str, Any]],
    focus_years: tuple[int, ...],
) -> list[str]:
    notes = []
    for year in focus_years:
        year_row = next((row for row in yearly_rows if str(row.get("year")) == str(year)), None)
        if year_row:
            notes.append(
                f"{year}: strategy_return={year_row.get('strategy_return')}, "
                f"benchmark_return={year_row.get('benchmark_return')}, excess={year_row.get('excess_return')}."
            )
        sector_for_year = [row for row in sector_rows if str(row.get("year")) == str(year)]
        if sector_for_year:
            weakest = min(sector_for_year, key=lambda row: to_float(row.get("signal_weighted_contribution_sum")) or 0.0)
            notes.append(f"{year}: weakest selected sector by signal-weight contribution is {weakest.get('sector_id')}.")
        cash = next((row for row in cash_rows if str(row.get("year")) == str(year)), None)
        if cash and (to_float(cash.get("max_cash_weight")) or 0.0) > 0.10:
            notes.append(f"{year}: cash drag needs review, max_cash_weight={cash.get('max_cash_weight')}.")
    if detractors:
        notes.append(f"Top detractor sample: {detractors[0].get('code')} in {detractors[0].get('year')}.")
    if missed_winners:
        notes.append(f"Missed winner sample: {missed_winners[0].get('code')} in {missed_winners[0].get('year')}.")
    return notes


def _report(summary: dict[str, Any]) -> str:
    lines = [
        "# Basket Failure Attribution Report",
        "",
        f"- Status: `{summary['status']}`",
        f"- Focus years: `{', '.join(str(year) for year in summary['focus_years'])}`",
        "",
        "## Diagnosis",
        "",
    ]
    for note in summary.get("diagnosis", []):
        lines.append(f"- {note}")
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- Yearly performance: `{summary['yearly_performance_csv']}`",
            f"- Sector attribution: `{summary['yearly_sector_attribution_csv']}`",
            f"- Code attribution: `{summary['yearly_code_attribution_csv']}`",
            f"- Top detractors: `{summary['top_detractors_csv']}`",
            f"- Missed winners: `{summary['missed_winners_csv']}`",
            f"- Worst excess days: `{summary['daily_excess_worst_days_csv']}`",
            "",
            "## Governance",
            "",
            str(summary["pm_note"]),
            "",
        ]
    )
    return "\n".join(lines)


def _mean(values: list[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    return sum(clean) / len(clean) if clean else None


def _fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    return names or ["empty"]


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload

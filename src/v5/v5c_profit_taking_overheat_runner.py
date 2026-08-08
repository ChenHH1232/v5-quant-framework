from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


BASELINE_DIR = (
    Path("local_daily_backtests_v57f_etf")
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
CONFIG_PATH = Path("config") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f.json"
ADMISSION_DIR = Path("v5c_overlay_hypothesis_admission") / "current"
DEFENSE_ENGINEERING_DIR = Path("v5c_overlay_engineering_comparison") / "current"
OUT_DIR = Path("v5c_profit_taking_overheat_overlay") / "current"


@dataclass(frozen=True)
class VariantSpec:
    variant_id: str
    overlay_type: str
    rule_description: str
    trigger_type: str
    governance_status: str


@dataclass
class Position:
    amount: int
    target_weight: float
    sector_id: str


def run_v5c_profit_taking_overheat(root: Path) -> dict[str, Any]:
    baseline_dir = root / BASELINE_DIR
    out_dir = root / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    config = _read_json(root / CONFIG_PATH)
    baseline_summary = _read_json(baseline_dir / "summary.json")
    admission_summary = _read_json(root / ADMISSION_DIR / "v5c_overlay_hypothesis_admission_summary.json")
    defense_summary = _read_json(root / DEFENSE_ENGINEERING_DIR / "v5c_overlay_engineering_summary.json")
    daily_rows = _read_csv(baseline_dir / "daily_returns.csv")
    holding_rows = _read_csv(baseline_dir / "holdings.csv")
    signal_rows = _read_csv(baseline_dir / "rebalance_signals.csv")

    price_rows = _read_price_rows(root, config)
    dates = [row["trade_date"] for row in daily_rows]
    codes = sorted({row["code"] for row in holding_rows})
    sector_by_date_code = {
        (row["trade_date"], row["code"]): row.get("sector_id", "") for row in signal_rows
    }
    close_by_code = _build_close_matrix(dates, codes, price_rows)
    benchmark_returns = [_to_float(row.get("benchmark_return")) for row in daily_rows]
    official_returns = [_to_float(row.get("strategy_return")) for row in daily_rows]
    official_baseline_metrics = _compute_metrics(official_returns, benchmark_returns, [1.0] * len(dates), dates)

    rebalances = _build_rebalance_targets(holding_rows, sector_by_date_code)
    sector_reference_returns = _build_sector_reference_returns(dates, rebalances, close_by_code)
    variants = _variant_specs()

    _write_prompt(out_dir)
    _write_csv(out_dir / "v5c_profit_taking_overheat_flow_table.csv", _flow_rows())
    _write_csv(out_dir / "v5c_profit_taking_overheat_spec.csv", [spec.__dict__ for spec in variants])

    comparison_rows: list[dict[str, Any]] = [
        {
            "variant_id": "v57f_official_frozen_baseline",
            "overlay_type": "none",
            "rule_description": "Official frozen V57f local daily backtest output; reference only.",
            **official_baseline_metrics,
            "trim_event_count": 0,
            "trim_trade_count": 0,
            "trim_value": 0.0,
            "delta_return_vs_official_baseline": 0.0,
            "delta_max_drawdown_vs_official_baseline": 0.0,
            "delta_return_vs_reconstructed_baseline": "",
            "delta_max_drawdown_vs_reconstructed_baseline": "",
            "pm_conclusion": "frozen_reference_not_replaced",
        }
    ]
    all_daily_rows: list[dict[str, Any]] = []
    all_trim_rows: list[dict[str, Any]] = []

    for idx, ret in enumerate(official_returns):
        all_daily_rows.append(
            {
                "trade_date": dates[idx],
                "variant_id": "v57f_official_frozen_baseline",
                "overlay_nav": _nav_series(official_returns)[idx],
                "overlay_return": ret,
                "benchmark_return": benchmark_returns[idx],
                "portfolio_value": _to_float(daily_rows[idx].get("portfolio_value")),
                "cash": _to_float(daily_rows[idx].get("cash")),
                "trim_event_count": 0,
            }
        )

    reconstructed_spec = VariantSpec(
        variant_id="v57f_reconstructed_close_proxy_no_overlay",
        overlay_type="none",
        rule_description="Close-to-close reconstruction from frozen V57f rebalance targets and local close prices; used only as the apples-to-apples baseline for trim overlays.",
        trigger_type="none",
        governance_status="diagnostic_reference",
    )
    reconstructed = _simulate_variant(
        spec=reconstructed_spec,
        dates=dates,
        daily_rows=daily_rows,
        rebalances=rebalances,
        close_by_code=close_by_code,
        sector_reference_returns=sector_reference_returns,
        benchmark_returns=benchmark_returns,
    )
    reconstructed_metrics = reconstructed["metrics"]
    all_daily_rows.extend(reconstructed["daily_rows"])
    comparison_rows.append(
        {
            "variant_id": reconstructed_spec.variant_id,
            "overlay_type": reconstructed_spec.overlay_type,
            "rule_description": reconstructed_spec.rule_description,
            **reconstructed_metrics,
            "trim_event_count": 0,
            "trim_trade_count": 0,
            "trim_value": 0.0,
            "delta_return_vs_official_baseline": reconstructed_metrics["strategy_return"] - official_baseline_metrics["strategy_return"],
            "delta_max_drawdown_vs_official_baseline": reconstructed_metrics["max_drawdown"] - official_baseline_metrics["max_drawdown"],
            "delta_return_vs_reconstructed_baseline": 0.0,
            "delta_max_drawdown_vs_reconstructed_baseline": 0.0,
            "pm_conclusion": "diagnostic_execution_proxy_reference_not_strategy_candidate",
        }
    )

    for spec in variants:
        sim = _simulate_variant(
            spec=spec,
            dates=dates,
            daily_rows=daily_rows,
            rebalances=rebalances,
            close_by_code=close_by_code,
            sector_reference_returns=sector_reference_returns,
            benchmark_returns=benchmark_returns,
        )
        all_daily_rows.extend(sim["daily_rows"])
        all_trim_rows.extend(sim["trim_rows"])
        metrics = sim["metrics"]
        comparison_rows.append(
            {
                "variant_id": spec.variant_id,
                "overlay_type": spec.overlay_type,
                "rule_description": spec.rule_description,
                **metrics,
                "trim_event_count": sim["trim_event_count"],
                "trim_trade_count": sim["trim_trade_count"],
                "trim_value": sim["trim_value"],
                "delta_return_vs_official_baseline": metrics["strategy_return"] - official_baseline_metrics["strategy_return"],
                "delta_max_drawdown_vs_official_baseline": metrics["max_drawdown"] - official_baseline_metrics["max_drawdown"],
                "delta_return_vs_reconstructed_baseline": metrics["strategy_return"] - reconstructed_metrics["strategy_return"],
                "delta_max_drawdown_vs_reconstructed_baseline": metrics["max_drawdown"] - reconstructed_metrics["max_drawdown"],
                "pm_conclusion": _pm_conclusion(spec, metrics, reconstructed_metrics, sim["trim_event_count"]),
            }
        )

    blocker_rows = _blocker_rows()
    _write_csv(out_dir / "v5c_profit_taking_overheat_engineering_comparison.csv", comparison_rows)
    _write_csv(out_dir / "v5c_profit_taking_overheat_daily_nav.csv", all_daily_rows)
    _write_csv(out_dir / "v5c_profit_taking_overheat_trim_log.csv", all_trim_rows)
    _write_csv(out_dir / "v5c_profit_taking_overheat_blockers.csv", blocker_rows)
    _write_report(out_dir, baseline_summary, admission_summary, defense_summary, comparison_rows, blocker_rows)

    summary = {
        "schema_version": 1,
        "project": "v5c_profit_taking_overheat_overlay",
        "status": "engineering_diagnostic_completed_no_v57f_core_change",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_strategy_id": baseline_summary.get("strategy_id"),
        "window": baseline_summary.get("window"),
        "v57f_core_modified": False,
        "joinquant_started": False,
        "backtest_type": "close_to_close_diagnostic_reconstruction_from_frozen_v57f_signals_and_holdings",
        "official_baseline": {
            "strategy_return": official_baseline_metrics["strategy_return"],
            "max_drawdown": official_baseline_metrics["max_drawdown"],
            "strategy_volatility": official_baseline_metrics["strategy_volatility"],
        },
        "reconstructed_close_proxy_baseline": {
            "strategy_return": reconstructed_metrics["strategy_return"],
            "max_drawdown": reconstructed_metrics["max_drawdown"],
            "strategy_volatility": reconstructed_metrics["strategy_volatility"],
            "purpose": "apples-to-apples comparison baseline for profit-taking overlays only",
        },
        "tested_overlay_count": len(variants),
        "tested_overlays": [spec.variant_id for spec in variants],
        "blocked_items": len(blocker_rows),
        "pm_decision": "diagnostic_only; no profit-taking or overheat rule is admitted as accepted strategy; V57f remains frozen",
        "outputs": {
            "execution_prompt": str(out_dir / "00_v5c_profit_taking_overheat_prompt.md"),
            "flow_table": str(out_dir / "v5c_profit_taking_overheat_flow_table.csv"),
            "spec": str(out_dir / "v5c_profit_taking_overheat_spec.csv"),
            "comparison": str(out_dir / "v5c_profit_taking_overheat_engineering_comparison.csv"),
            "daily_nav": str(out_dir / "v5c_profit_taking_overheat_daily_nav.csv"),
            "trim_log": str(out_dir / "v5c_profit_taking_overheat_trim_log.csv"),
            "blockers": str(out_dir / "v5c_profit_taking_overheat_blockers.csv"),
            "report": str(out_dir / "v5c_profit_taking_overheat_report.md"),
            "summary": str(out_dir / "v5c_profit_taking_overheat_summary.json"),
        },
    }
    _write_json(out_dir / "v5c_profit_taking_overheat_summary.json", summary)
    return summary


def _variant_specs() -> list[VariantSpec]:
    return [
        VariantSpec(
            variant_id="stock_weight_drift_trim_target_plus_150bp",
            overlay_type="individual_stock_profit_taking",
            rule_description="If a holding weight drifts above max(target weight + 1.50pp, 5.00%), trim back toward the frozen target weight and hold proceeds as cash until the next scheduled rebalance.",
            trigger_type="weight_drift_only",
            governance_status="engineering_diagnostic_allowed",
        ),
        VariantSpec(
            variant_id="stock_20d_overheat_trim_to_target",
            overlay_type="individual_stock_overheat",
            rule_description="If a holding's prior 20 trading-day close return is above 25% and weight is above target + 0.50pp, trim back toward frozen target weight.",
            trigger_type="prior_return_overheat",
            governance_status="diagnostic_high_overfit_risk_not_admitted",
        ),
        VariantSpec(
            variant_id="sleeve_weight_drift_trim_target_plus_300bp",
            overlay_type="sector_sleeve_profit_taking",
            rule_description="If a core sleeve weight drifts above its frozen target weight + 3.00pp, trim sleeve holdings pro-rata back toward target sleeve weight.",
            trigger_type="sleeve_weight_drift_only",
            governance_status="engineering_diagnostic_allowed",
        ),
        VariantSpec(
            variant_id="sleeve_20d_overheat_cut_15pct",
            overlay_type="sector_sleeve_overheat",
            rule_description="If a sleeve's prior 20 trading-day reference return is above 18% or prior 60 trading-day return is above 35%, cut 15% of that sleeve exposure and hold proceeds as cash until next scheduled rebalance.",
            trigger_type="prior_sleeve_return_overheat",
            governance_status="diagnostic_high_overfit_risk_not_admitted",
        ),
    ]


def _simulate_variant(
    *,
    spec: VariantSpec,
    dates: list[str],
    daily_rows: list[dict[str, str]],
    rebalances: dict[str, list[dict[str, Any]]],
    close_by_code: dict[str, list[float | None]],
    sector_reference_returns: dict[str, list[float]],
    benchmark_returns: list[float],
) -> dict[str, Any]:
    positions: dict[str, Position] = {}
    cash = _to_float(daily_rows[0].get("portfolio_value"))
    previous_value: float | None = None
    returns: list[float] = []
    exposures: list[float] = []
    daily_out: list[dict[str, Any]] = []
    trim_rows: list[dict[str, Any]] = []
    trim_event_count = 0
    trim_trade_count = 0
    trim_value = 0.0

    for date_idx, date in enumerate(dates):
        prices = {code: series[date_idx] for code, series in close_by_code.items() if series[date_idx] is not None}
        if date in rebalances:
            current_value = previous_value if previous_value is not None else _to_float(daily_rows[date_idx].get("portfolio_value"))
            positions, cash = _reset_to_frozen_targets(current_value, rebalances[date], prices)

        cash += _scaled_dividend_cash(daily_rows[date_idx], positions, prices)
        pre_trim_value = _portfolio_value(positions, cash, prices)
        if pre_trim_value <= 0:
            returns.append(0.0)
            exposures.append(0.0)
            daily_out.append(_daily_row(date, spec.variant_id, 1.0, 0.0, benchmark_returns[date_idx], 0.0, cash, 0))
            previous_value = pre_trim_value
            continue

        trim_events = _apply_variant_rule(
            spec,
            date_idx,
            date,
            positions,
            cash,
            pre_trim_value,
            prices,
            dates,
            close_by_code,
            sector_reference_returns,
        )
        if trim_events:
            event_value = sum(row["trim_value"] for row in trim_events)
            commission = sum(row["commission"] for row in trim_events)
            cash += event_value - commission
            trim_value += event_value
            trim_event_count += 1
            trim_trade_count += len(trim_events)
            trim_rows.extend(trim_events)

        value = _portfolio_value(positions, cash, prices)
        ret = 0.0 if previous_value is None or previous_value == 0 else value / previous_value - 1
        returns.append(ret)
        invested_value = sum(pos.amount * prices.get(code, 0.0) for code, pos in positions.items())
        exposures.append(invested_value / value if value else 0.0)
        previous_value = value
        nav = _nav_series(returns)[-1]
        daily_out.append(
            _daily_row(date, spec.variant_id, nav, ret, benchmark_returns[date_idx], value, cash, len(trim_events))
        )

    metrics = _compute_metrics(returns, benchmark_returns, exposures, dates)
    return {
        "metrics": metrics,
        "daily_rows": daily_out,
        "trim_rows": trim_rows,
        "trim_event_count": trim_event_count,
        "trim_trade_count": trim_trade_count,
        "trim_value": trim_value,
    }


def _apply_variant_rule(
    spec: VariantSpec,
    date_idx: int,
    date: str,
    positions: dict[str, Position],
    cash: float,
    portfolio_value: float,
    prices: dict[str, float],
    dates: list[str],
    close_by_code: dict[str, list[float | None]],
    sector_reference_returns: dict[str, list[float]],
) -> list[dict[str, Any]]:
    if spec.variant_id == "stock_weight_drift_trim_target_plus_150bp":
        return _trim_overweight_stocks(spec, date, positions, portfolio_value, prices, 0.015, require_overheat=False, date_idx=date_idx, close_by_code=close_by_code)
    if spec.variant_id == "stock_20d_overheat_trim_to_target":
        return _trim_overweight_stocks(spec, date, positions, portfolio_value, prices, 0.005, require_overheat=True, date_idx=date_idx, close_by_code=close_by_code)
    if spec.variant_id == "sleeve_weight_drift_trim_target_plus_300bp":
        return _trim_overweight_sleeves(spec, date, positions, portfolio_value, prices, 0.03, sector_reference_returns, date_idx, require_overheat=False)
    if spec.variant_id == "sleeve_20d_overheat_cut_15pct":
        return _trim_overweight_sleeves(spec, date, positions, portfolio_value, prices, 0.01, sector_reference_returns, date_idx, require_overheat=True)
    return []


def _trim_overweight_stocks(
    spec: VariantSpec,
    date: str,
    positions: dict[str, Position],
    portfolio_value: float,
    prices: dict[str, float],
    band: float,
    *,
    require_overheat: bool,
    date_idx: int,
    close_by_code: dict[str, list[float | None]],
) -> list[dict[str, Any]]:
    rows = []
    for code, pos in list(positions.items()):
        price = prices.get(code)
        if not price or pos.amount <= 0:
            continue
        current_value = pos.amount * price
        current_weight = current_value / portfolio_value
        trigger_weight = max(pos.target_weight + band, 0.05 if not require_overheat else pos.target_weight + band)
        if current_weight <= trigger_weight:
            continue
        prior_20d_return = _prior_code_return(code, date_idx, close_by_code, 20)
        if require_overheat and (prior_20d_return is None or prior_20d_return <= 0.25):
            continue
        target_value = pos.target_weight * portfolio_value
        sell_value = max(0.0, current_value - target_value)
        sell_amount = int((sell_value / price) // 100 * 100)
        sell_amount = min(sell_amount, pos.amount)
        if sell_amount <= 0:
            continue
        pos.amount -= sell_amount
        value = sell_amount * price
        rows.append(
            _trim_row(
                spec=spec,
                date=date,
                code=code,
                sector_id=pos.sector_id,
                trigger_metric="prior_20d_return" if require_overheat else "weight_drift",
                trigger_value=prior_20d_return if require_overheat and prior_20d_return is not None else current_weight - pos.target_weight,
                before_weight=current_weight,
                target_weight=pos.target_weight,
                trim_amount=sell_amount,
                trim_price=price,
                trim_value=value,
            )
        )
    return rows


def _trim_overweight_sleeves(
    spec: VariantSpec,
    date: str,
    positions: dict[str, Position],
    portfolio_value: float,
    prices: dict[str, float],
    band: float,
    sector_reference_returns: dict[str, list[float]],
    date_idx: int,
    *,
    require_overheat: bool,
) -> list[dict[str, Any]]:
    by_sector: dict[str, list[tuple[str, Position, float]]] = defaultdict(list)
    target_by_sector: dict[str, float] = defaultdict(float)
    for code, pos in positions.items():
        price = prices.get(code)
        if not price or pos.amount <= 0:
            continue
        by_sector[pos.sector_id].append((code, pos, pos.amount * price))
        target_by_sector[pos.sector_id] += pos.target_weight

    rows = []
    for sector_id, items in by_sector.items():
        current_value = sum(value for _, _, value in items)
        current_weight = current_value / portfolio_value
        target_weight = target_by_sector[sector_id]
        if require_overheat:
            prior20 = _prior_series_return(sector_reference_returns.get(sector_id, []), date_idx, 20)
            prior60 = _prior_series_return(sector_reference_returns.get(sector_id, []), date_idx, 60)
            overheated = (prior20 is not None and prior20 > 0.18) or (prior60 is not None and prior60 > 0.35)
            if not overheated or current_weight <= target_weight + band:
                continue
            desired_trim_value = current_value * 0.15
            trigger_value = prior20 if prior20 is not None else prior60
            trigger_metric = "prior_sleeve_return"
        else:
            if current_weight <= target_weight + band:
                continue
            desired_trim_value = max(0.0, current_value - target_weight * portfolio_value)
            trigger_value = current_weight - target_weight
            trigger_metric = "sleeve_weight_drift"
        for code, pos, value in items:
            price = prices[code]
            sell_value = desired_trim_value * value / current_value if current_value else 0.0
            sell_amount = int((sell_value / price) // 100 * 100)
            sell_amount = min(sell_amount, pos.amount)
            if sell_amount <= 0:
                continue
            pos.amount -= sell_amount
            trim_value = sell_amount * price
            rows.append(
                _trim_row(
                    spec=spec,
                    date=date,
                    code=code,
                    sector_id=sector_id,
                    trigger_metric=trigger_metric,
                    trigger_value=trigger_value if trigger_value is not None else 0.0,
                    before_weight=current_weight,
                    target_weight=target_weight,
                    trim_amount=sell_amount,
                    trim_price=price,
                    trim_value=trim_value,
                )
            )
    return rows


def _reset_to_frozen_targets(
    portfolio_value: float,
    target_rows: list[dict[str, Any]],
    prices: dict[str, float],
) -> tuple[dict[str, Position], float]:
    positions: dict[str, Position] = {}
    invested = 0.0
    for row in target_rows:
        code = row["code"]
        price = prices.get(code)
        if not price or price <= 0:
            continue
        target_weight = _to_float(row.get("target_weight"))
        amount = int((portfolio_value * target_weight / price) // 100 * 100)
        positions[code] = Position(amount=amount, target_weight=target_weight, sector_id=row["sector_id"])
        invested += amount * price
    cash = max(0.0, portfolio_value - invested)
    return positions, cash


def _build_rebalance_targets(
    holding_rows: list[dict[str, str]],
    sector_by_date_code: dict[tuple[str, str], str],
) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in holding_rows:
        date = row["trade_date"]
        code = row["code"]
        output[date].append(
            {
                "trade_date": date,
                "code": code,
                "target_weight": _to_float(row.get("target_weight")),
                "sector_id": sector_by_date_code.get((date, code), "unknown"),
            }
        )
    return dict(output)


def _build_close_matrix(
    dates: list[str],
    codes: list[str],
    price_rows: list[dict[str, str]],
) -> dict[str, list[float | None]]:
    raw: dict[str, dict[str, float]] = defaultdict(dict)
    for row in price_rows:
        code = row.get("code", "")
        if code in codes:
            raw[code][row.get("date", "")] = _to_float(row.get("close"))
    matrix: dict[str, list[float | None]] = {}
    for code in codes:
        series: list[float | None] = []
        last: float | None = None
        for date in dates:
            close = raw.get(code, {}).get(date)
            if close and close > 0:
                last = close
            series.append(last)
        matrix[code] = series
    return matrix


def _build_sector_reference_returns(
    dates: list[str],
    rebalances: dict[str, list[dict[str, Any]]],
    close_by_code: dict[str, list[float | None]],
) -> dict[str, list[float]]:
    active: dict[str, str] = {}
    output: dict[str, list[float]] = defaultdict(list)
    known_sectors = sorted({row["sector_id"] for rows in rebalances.values() for row in rows})
    for sector in known_sectors:
        output[sector] = []
    for idx, date in enumerate(dates):
        if date in rebalances:
            active = {row["code"]: row["sector_id"] for row in rebalances[date]}
        sector_returns: dict[str, list[float]] = defaultdict(list)
        if idx > 0:
            for code, sector in active.items():
                series = close_by_code.get(code)
                if not series:
                    continue
                prev_close = series[idx - 1]
                close = series[idx]
                if prev_close and close:
                    sector_returns[sector].append(close / prev_close - 1)
        for sector in known_sectors:
            output[sector].append(mean(sector_returns[sector]) if sector_returns.get(sector) else 0.0)
    return dict(output)


def _read_price_rows(root: Path, config: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for sector in config.get("sectors", []):
        path = root / Path(str(sector["price_csv"]))
        rows.extend(_read_csv(path))
    return rows


def _portfolio_value(positions: dict[str, Position], cash: float, prices: dict[str, float]) -> float:
    return cash + sum(pos.amount * prices.get(code, 0.0) for code, pos in positions.items())


def _scaled_dividend_cash(row: dict[str, str], positions: dict[str, Position], prices: dict[str, float]) -> float:
    dividend_cash = _to_float(row.get("dividend_cash"))
    if dividend_cash <= 0:
        return 0.0
    baseline_invested = _to_float(row.get("invested_value"))
    if baseline_invested <= 0:
        return dividend_cash
    current_invested = sum(pos.amount * prices.get(code, 0.0) for code, pos in positions.items())
    return dividend_cash * max(0.0, min(1.2, current_invested / baseline_invested))


def _trim_row(
    *,
    spec: VariantSpec,
    date: str,
    code: str,
    sector_id: str,
    trigger_metric: str,
    trigger_value: float,
    before_weight: float,
    target_weight: float,
    trim_amount: int,
    trim_price: float,
    trim_value: float,
) -> dict[str, Any]:
    commission = max(5.0, trim_value * 0.0003) if trim_value > 0 else 0.0
    return {
        "trade_date": date,
        "variant_id": spec.variant_id,
        "overlay_type": spec.overlay_type,
        "code": code,
        "sector_id": sector_id,
        "trigger_metric": trigger_metric,
        "trigger_value": trigger_value,
        "before_weight": before_weight,
        "target_weight": target_weight,
        "trim_amount": trim_amount,
        "trim_price": trim_price,
        "trim_value": trim_value,
        "commission": commission,
        "cash_policy": "hold_trim_proceeds_as_cash_until_next_scheduled_v57f_rebalance",
    }


def _daily_row(
    date: str,
    variant_id: str,
    nav: float,
    ret: float,
    benchmark_return: float,
    value: float,
    cash: float,
    trim_events: int,
) -> dict[str, Any]:
    return {
        "trade_date": date,
        "variant_id": variant_id,
        "overlay_nav": nav,
        "overlay_return": ret,
        "benchmark_return": benchmark_return,
        "portfolio_value": value,
        "cash": cash,
        "cash_weight": cash / value if value else 0.0,
        "trim_event_count": trim_events,
    }


def _prior_code_return(
    code: str,
    date_idx: int,
    close_by_code: dict[str, list[float | None]],
    window: int,
) -> float | None:
    if date_idx <= window:
        return None
    series = close_by_code.get(code)
    if not series:
        return None
    start = series[date_idx - window]
    end = series[date_idx - 1]
    if not start or not end:
        return None
    return end / start - 1


def _prior_series_return(values: list[float], date_idx: int, window: int) -> float | None:
    if date_idx <= window:
        return None
    nav = 1.0
    for ret in values[date_idx - window:date_idx]:
        nav *= 1 + ret
    return nav - 1


def _compute_metrics(
    returns: list[float],
    benchmark_returns: list[float],
    exposures: list[float],
    dates: list[str],
) -> dict[str, Any]:
    navs = _nav_series(returns)
    benchmark_navs = _nav_series(benchmark_returns)
    total_return = navs[-1] - 1 if navs else 0.0
    benchmark_return = benchmark_navs[-1] - 1 if benchmark_navs else 0.0
    periods = len(returns)
    annualized_return = (1 + total_return) ** (252 / periods) - 1 if periods and total_return > -1 else None
    vol = _annualized_vol(returns)
    sharpe = annualized_return / vol if annualized_return is not None and vol else None
    max_dd, dd_start_idx, dd_end_idx = _max_drawdown(navs)
    excess_returns = [ret - benchmark_returns[idx] for idx, ret in enumerate(returns)]
    information_ratio = _safe_mean(excess_returns) / pstdev(excess_returns) * math.sqrt(252) if len(excess_returns) > 1 and pstdev(excess_returns) else None
    risk_off_days = sum(1 for value in exposures if value < 0.98)
    return {
        "strategy_return": total_return,
        "annualized_return": annualized_return,
        "benchmark_return": benchmark_return,
        "excess_return": total_return - benchmark_return,
        "max_drawdown": max_dd,
        "max_drawdown_interval": _drawdown_interval(dates, navs),
        "strategy_volatility": vol,
        "sharpe": sharpe,
        "information_ratio": information_ratio,
        "average_exposure": mean(exposures) if exposures else 1.0,
        "risk_off_days": risk_off_days,
        "risk_off_ratio": risk_off_days / len(exposures) if exposures else 0.0,
    }


def _pm_conclusion(
    spec: VariantSpec,
    metrics: dict[str, Any],
    baseline: dict[str, Any],
    trim_event_count: int,
) -> str:
    if trim_event_count == 0:
        return "no_trigger_in_window_diagnostic_only"
    if "overheat" in spec.overlay_type:
        return "overheat_rule_triggered_but_high_overfit_risk_quant_pm_review_only"
    if metrics["max_drawdown"] < baseline["max_drawdown"] and metrics["strategy_return"] < baseline["strategy_return"]:
        return "risk_reduced_with_return_cost_not_accepted"
    if metrics["max_drawdown"] < baseline["max_drawdown"]:
        return "risk_reduced_diagnostic_promising_not_accepted"
    return "no_risk_improvement_not_accepted"


def _nav_series(returns: list[float]) -> list[float]:
    nav = 1.0
    output = []
    for ret in returns:
        nav *= 1 + ret
        output.append(nav)
    return output


def _drawdown_interval(dates: list[str], navs: list[float]) -> str:
    _, start_idx, end_idx = _max_drawdown(navs)
    if 0 <= start_idx < len(dates) and 0 <= end_idx < len(dates):
        return f"{dates[start_idx]},{dates[end_idx]}"
    return ""


def _max_drawdown(navs: list[float]) -> tuple[float, int, int]:
    peak = -float("inf")
    peak_idx = 0
    max_dd = 0.0
    start_idx = 0
    end_idx = 0
    for idx, nav in enumerate(navs):
        if nav > peak:
            peak = nav
            peak_idx = idx
        if peak > 0:
            dd = 1 - nav / peak
            if dd > max_dd:
                max_dd = dd
                start_idx = peak_idx
                end_idx = idx
    return max_dd, start_idx, end_idx


def _annualized_vol(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return pstdev(values) * math.sqrt(252)


def _safe_mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _flow_rows() -> list[dict[str, str]]:
    return [
        {
            "step": "1",
            "stage": "freeze_guard",
            "action": "Read V57f summary, governance admission, existing V5c defense engineering outputs.",
            "output": "scope confirmation",
            "allowed": "evidence refresh only",
            "blocked": "modify V57f core or tune historical thresholds",
        },
        {
            "step": "2",
            "stage": "data_reconstruction",
            "action": "Reconstruct daily holdings weights from frozen rebalance holdings, frozen signals, and local daily close prices.",
            "output": "close-to-close diagnostic engine",
            "allowed": "local diagnostic only",
            "blocked": "claim platform replication",
        },
        {
            "step": "3",
            "stage": "individual_profit_taking",
            "action": "Test stock weight drift trim and prior-return overheat trim.",
            "output": "engineering comparison and trim log",
            "allowed": "diagnostic review",
            "blocked": "use result to accept strategy directly",
        },
        {
            "step": "4",
            "stage": "sleeve_profit_taking",
            "action": "Test sleeve weight drift trim and sleeve prior-return overheat trim.",
            "output": "engineering comparison and trim log",
            "allowed": "diagnostic review",
            "blocked": "change V57f sleeve weights",
        },
        {
            "step": "5",
            "stage": "data_gate",
            "action": "Park valuation overheat and crowding overheat until PIT valuation/flow data exists.",
            "output": "blocker list",
            "allowed": "data requirement packet",
            "blocked": "current valuation backfill or ETF holding lookback",
        },
    ]


def _blocker_rows() -> list[dict[str, str]]:
    return [
        {
            "blocked_item": "valuation_overheat_profit_taking",
            "reason": "No audited PIT daily/periodic valuation series for each holding and sleeve is available in this overlay scope.",
            "needed_input": "PIT PB/PE/dividend-yield/FCF-yield or valuation percentile with announcement/source date contract.",
            "allowed_next_action": "build PIT valuation data gate; no engineering return test yet",
        },
        {
            "blocked_item": "crowding_overheat_profit_taking",
            "reason": "No PIT fund-flow, ETF holding crowding, northbound, margin, or ownership concentration dataset is admitted.",
            "needed_input": "PIT crowding proxy with publication date and historical availability contract.",
            "allowed_next_action": "research/data gate only",
        },
        {
            "blocked_item": "optimized_take_profit_thresholds",
            "reason": "Optimizing thresholds on 2021-2026 would violate V5c PM admission rules.",
            "needed_input": "pre-registered thresholds and forward/paper evidence outside frozen V5 evidence.",
            "allowed_next_action": "coarse diagnostic thresholds only; do not rank by historical return",
        },
    ]


def _write_prompt(out_dir: Path) -> None:
    prompt = """# V5c Profit-Taking / Overheat Overlay Execution Prompt

Workspace: `D:\\hh\\codex\\v5`

Task: Generate and execute a V5c diagnostic for profit-taking, stock overheating, sleeve overheating, and blocked valuation/crowding overheating gates.

Core rules:

1. Do not modify V57f core sleeves, weights, factors, rebalance calendar, or execution timing.
2. Do not start JoinQuant.
3. Do not use 2026-10 future paper signals inside V5.
4. Do not tune thresholds by historical return.
5. Historical return cannot be the reason to accept an overlay.
6. Only use frozen V57f local outputs through 2026-05-31.
7. Only admit close-to-close local diagnostics; do not claim platform replication.

Execution:

1. Read frozen V57f `summary.json`, `daily_returns.csv`, `holdings.csv`, `rebalance_signals.csv`, and V57f config price files.
2. Reconstruct daily position weights from frozen rebalance targets and local close prices.
3. Test pre-registered coarse variants:
   - stock weight drift trim;
   - stock prior-20d return overheat trim;
   - sleeve weight drift trim;
   - sleeve prior-20d / prior-60d return overheat trim.
4. Write comparison, daily NAV, trim log, blockers, and PM report.
5. Keep valuation overheat and crowding overheat in data gate until PIT data exists.

Stop only if a required local governance or V57f evidence file is missing, or if execution would require external data or a V57f core change.
"""
    (out_dir / "00_v5c_profit_taking_overheat_prompt.md").write_text(prompt, encoding="utf-8")


def _write_report(
    out_dir: Path,
    baseline_summary: dict[str, Any],
    admission_summary: dict[str, Any],
    defense_summary: dict[str, Any],
    comparison_rows: list[dict[str, Any]],
    blocker_rows: list[dict[str, str]],
) -> None:
    lines = [
        "# V5c Profit-Taking / Overheat Overlay Diagnostic",
        "",
        "This packet answers whether V5c has tested profit-taking, including individual stock and sleeve overheating. It remains diagnostic only.",
        "",
        "## Scope",
        "",
        f"- Baseline: `{baseline_summary.get('strategy_id')}`",
        f"- Window: `{baseline_summary.get('window', {}).get('start_date')}` to `{baseline_summary.get('window', {}).get('end_date')}`",
        f"- PM admission status: `{admission_summary.get('status')}`",
        f"- Prior V5c defense engineering status: `{defense_summary.get('status')}`",
        "- V57f core modified: `false`",
        "- JoinQuant started: `false`",
        "",
        "## Engineering Comparison",
        "",
        "| Variant | Return | Max Drawdown | Volatility | Avg Exposure | Trim Events | Delta Return vs Recon | Delta DD vs Recon | PM Conclusion |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in comparison_rows:
        delta_ret = row.get("delta_return_vs_reconstructed_baseline")
        delta_dd = row.get("delta_max_drawdown_vs_reconstructed_baseline")
        delta_ret_text = "" if delta_ret == "" else f"{delta_ret:.2%}"
        delta_dd_text = "" if delta_dd == "" else f"{delta_dd:.2%}"
        lines.append(
            "| {variant_id} | {ret:.2%} | {dd:.2%} | {vol:.2%} | {exp:.2%} | {events} | {delta_ret} | {delta_dd} | {conclusion} |".format(
                variant_id=row["variant_id"],
                ret=row["strategy_return"],
                dd=row["max_drawdown"],
                vol=row["strategy_volatility"],
                exp=row["average_exposure"],
                events=row["trim_event_count"],
                delta_ret=delta_ret_text,
                delta_dd=delta_dd_text,
                conclusion=row["pm_conclusion"],
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Stock and sleeve profit-taking were tested as mechanical trim diagnostics, not as accepted trading rules.",
            "- The reconstructed close-to-close baseline is included only to compare overlays under the same execution proxy; official V57f remains the frozen reference.",
            "- Return-based overheat rules are especially vulnerable to threshold overfit, so they require Quant/PM review and future paper evidence before any promotion.",
            "- Valuation and crowding overheating are not tested because current PIT data contracts are missing.",
            "- V57f remains frozen; none of these overlays can rewrite the V5 final conclusion.",
            "",
            "## Blockers",
            "",
        ]
    )
    for row in blocker_rows:
        lines.append(f"- `{row['blocked_item']}`: {row['reason']}")
    (out_dir / "v5c_profit_taking_overheat_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["empty"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    result = run_v5c_profit_taking_overheat(Path.cwd())
    print(json.dumps(result, ensure_ascii=False, indent=2))

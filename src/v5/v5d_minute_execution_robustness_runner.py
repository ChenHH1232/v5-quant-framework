from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

import pandas as pd

from v5.io_utils import read_csv_rows, write_csv_rows
from v5.math_utils import to_float
from v5.rebalance_order_health import build_rebalance_order_health
from v5.v57f_execution_robustness_runner import (
    _build_equal_weight_benchmark,
    _compute_metrics,
    _execute_buys,
    _execute_sells,
    _fieldnames,
    _load_corporate_actions,
    _load_prices,
    _load_signals,
    _portfolio_value,
)


ROOT = Path(".")
OUT_DIR = Path("v5d_minute_execution_robustness") / "current"
BASELINE_DIR = Path("local_daily_backtests_v57f_etf") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
CONFIG_PATH = Path("config") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f.json"
DATA_GATE_DIR = Path("v5d_baostock_5min_data_gate") / "current"
STD_INDEX = DATA_GATE_DIR / "v5d_baostock_5min_standardized_index.csv"
STD_DATA_DIR = Path("v5d_baostock_5min_data_gate") / "data_standardized"
V57F_SIGNALS = BASELINE_DIR / "rebalance_signals.csv"
ERC_SIGNALS = Path("v5c_risk_budget_overlay_engineering_comparison") / "current" / "v5c_erc_fixed_covariance_signals.csv"
ENGINEERING_WINDOW_START = "2021-05-01"
ENGINEERING_WINDOW_END = "2026-05-31"


@dataclass(frozen=True)
class ExecutionProxy:
    proxy_id: str
    strategy_family: str
    description: str
    price_source: str
    bar_time: str = ""
    delay_days: int = 0


PROXIES = [
    ExecutionProxy("daily_open", "baseline", "Original local daily open execution baseline", "daily_open"),
    ExecutionProxy("bar_0935", "baostock_5min", "BaoStock 09:35 5min bar close proxy", "bar_time", "09:35:00"),
    ExecutionProxy("bar_0940", "baostock_5min", "BaoStock 09:40 approximate 5min bar close proxy", "bar_time", "09:40:00"),
    ExecutionProxy("bar_1000", "baostock_5min", "BaoStock 10:00 5min bar close proxy", "bar_time", "10:00:00"),
    ExecutionProxy("bar_1455", "baostock_5min", "BaoStock 14:55 5min bar close proxy", "bar_time", "14:55:00"),
    ExecutionProxy("day_5min_vwap", "baostock_5min", "Same-day BaoStock 5min amount/volume VWAP proxy", "vwap"),
    ExecutionProxy("day_5min_twap", "baostock_5min", "Same-day BaoStock 5min close TWAP proxy", "twap"),
    ExecutionProxy("next_day_open", "daily_next_open", "Next trading day daily open proxy", "daily_open", delay_days=1),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_minute_prices(index_path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    if STD_DATA_DIR.exists():
        paths = sorted(STD_DATA_DIR.rglob("*_5min_standardized.csv"))
        index = pd.DataFrame({"path": [str(p) for p in paths]})
    else:
        index = pd.read_csv(index_path)
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for _, item in index.iterrows():
        path = Path(str(item["path"]))
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if df.empty:
            continue
        for trade_date, day in df.groupby("trade_date"):
            code = str(day["code"].iloc[0]) if "code" in day.columns else str(item.get("code", ""))
            day = day.copy()
            day["volume"] = pd.to_numeric(day["volume"], errors="coerce").fillna(0)
            day["amount"] = pd.to_numeric(day["amount"], errors="coerce").fillna(0)
            day["close"] = pd.to_numeric(day["close"], errors="coerce")
            by_time = {str(row["time"]): float(row["close"]) for _, row in day.iterrows() if pd.notna(row["close"]) and float(row["close"]) > 0}
            total_volume = float(day["volume"].sum())
            total_amount = float(day["amount"].sum())
            closes = [float(x) for x in day["close"].dropna().tolist() if float(x) > 0]
            result[(code, str(trade_date))] = {
                "by_time": by_time,
                "vwap": total_amount / total_volume if total_volume > 0 else None,
                "twap": sum(closes) / len(closes) if closes else None,
                "last_bar": closes[-1] if closes else None,
                "bar_count": int(len(day)),
            }
    return result


def proxy_price_for(
    proxy: ExecutionProxy,
    day: str,
    code: str,
    daily_price_row: dict[str, float],
    minute_prices: dict[tuple[str, str], dict[str, Any]],
) -> tuple[float | None, str]:
    if proxy.price_source == "daily_open":
        price = daily_price_row.get("open")
        return (price if price and price > 0 else None), "" if price and price > 0 else "missing_daily_open"
    minute = minute_prices.get((code, day))
    if not minute:
        return None, "missing_baostock_5min_day"
    if proxy.price_source == "bar_time":
        price = minute["by_time"].get(proxy.bar_time)
        return (price if price and price > 0 else None), "" if price and price > 0 else f"missing_bar_{proxy.bar_time}"
    if proxy.price_source in {"vwap", "twap"}:
        price = minute.get(proxy.price_source)
        return (price if price and price > 0 else None), "" if price and price > 0 else f"missing_{proxy.price_source}"
    return None, "unsupported_proxy"


def schedule_signals(signals: dict[str, dict[str, float]], trading_days: list[str], delay_days: int) -> dict[str, dict[str, float]]:
    if delay_days <= 0:
        return dict(signals)
    idx = {day: i for i, day in enumerate(trading_days)}
    scheduled: dict[str, dict[str, float]] = {}
    for day, targets in signals.items():
        if day not in idx:
            continue
        target_i = min(idx[day] + delay_days, len(trading_days) - 1)
        scheduled[trading_days[target_i]] = targets
    return scheduled


def simulate_proxy(
    *,
    proxy: ExecutionProxy,
    strategy_id: str,
    signals: dict[str, dict[str, float]],
    prices_by_date: dict[str, dict[str, dict[str, float]]],
    corporate_actions_by_date: dict[str, dict[str, dict[str, float]]],
    benchmark_rows: list[dict[str, Any]],
    minute_prices: dict[tuple[str, str], dict[str, Any]],
    trading_days: list[str],
    initial_cash: float = 2_000_000.0,
    target_exposure: float = 0.995,
    lot_size: int = 100,
    open_commission: float = 0.0003,
    close_commission: float = 0.0003,
    min_commission: float = 5.0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    signal_schedule = schedule_signals(signals, trading_days, proxy.delay_days)
    benchmark_by_date = {row["trade_date"]: row for row in benchmark_rows}
    cash = initial_cash
    positions: dict[str, int] = {}
    last_close: dict[str, float] = {}
    previous_value = cash
    strategy_nav = 1.0
    excess_nav = 1.0
    current_targets: dict[str, float] = {}
    daily_rows: list[dict[str, Any]] = []
    holding_rows: list[dict[str, Any]] = []
    trade_rows: list[dict[str, Any]] = []
    dividend_rows: list[dict[str, Any]] = []
    corporate_action_rows: list[dict[str, Any]] = []
    missing_rows: list[dict[str, Any]] = []

    for day in trading_days:
        price_rows = prices_by_date.get(day, {})
        action_share_value = 0.0
        for code, action in corporate_actions_by_date.get(day, {}).items():
            current_amount = positions.get(code, 0)
            share_ratio = action.get("stock_dividend_ratio", 0.0) or 0.0
            if current_amount <= 0 or share_ratio <= 0:
                continue
            new_amount = int(round(current_amount * (1.0 + share_ratio)))
            added_amount = new_amount - current_amount
            if added_amount <= 0:
                continue
            positions[code] = new_amount
            close_for_value = price_rows.get(code, {}).get("close") or last_close.get(code, 0.0)
            action_value = added_amount * close_for_value
            action_share_value += action_value
            corporate_action_rows.append(
                {
                    "trade_date": day,
                    "code": code,
                    "action": "stock_dividend_or_transfer",
                    "old_amount": current_amount,
                    "added_amount": added_amount,
                    "new_amount": new_amount,
                    "stock_dividend_ratio": share_ratio,
                    "valuation_price": close_for_value,
                    "estimated_share_value": action_value,
                }
            )

        close_prices = {code: item["close"] for code, item in price_rows.items()}
        trade_prices = dict(last_close)
        scheduled_targets = signal_schedule.get(day)
        rebalance = scheduled_targets is not None
        if rebalance:
            current_targets = {code: weight * target_exposure for code, weight in scheduled_targets.items()}
            for code in set(positions) | set(current_targets):
                daily_row = price_rows.get(code, {})
                price, reason = proxy_price_for(proxy, day, code, daily_row, minute_prices)
                if price is None:
                    fallback = daily_row.get("open") or last_close.get(code)
                    if fallback and fallback > 0:
                        trade_prices[code] = fallback
                    missing_rows.append(
                        {
                            "strategy_id": strategy_id,
                            "execution_proxy": proxy.proxy_id,
                            "trade_date": day,
                            "code": code,
                            "missing_reason": reason,
                            "daily_paused": daily_row.get("paused", ""),
                            "daily_high_limit": daily_row.get("high_limit", ""),
                            "daily_low_limit": daily_row.get("low_limit", ""),
                            "fallback_policy": "daily_open_or_last_close_for_continuity",
                        }
                    )
                else:
                    trade_prices[code] = price
        else:
            trade_prices.update({code: item["open"] for code, item in price_rows.items()})

        buy_turnover = sell_turnover = commission_total = 0.0
        if rebalance:
            cash, sell_commission, sell_turnover, sells, _ = _execute_sells(
                day,
                cash,
                positions,
                trade_prices,
                price_rows,
                current_targets,
                lot_size,
                close_commission,
                min_commission,
                carry_blocked_orders=False,
                pending_targets={},
            )
            total_after_sells = _portfolio_value(cash, positions, trade_prices)
            cash, buy_commission, buy_turnover, buys, _ = _execute_buys(
                day,
                cash,
                positions,
                trade_prices,
                price_rows,
                current_targets,
                total_after_sells,
                lot_size,
                open_commission,
                min_commission,
                carry_blocked_orders=False,
                pending_targets={},
            )
            commission_total = sell_commission + buy_commission
            for row in sells + buys:
                row["execution_proxy"] = proxy.proxy_id
                row["strategy_id"] = strategy_id
            trade_rows.extend(sells)
            trade_rows.extend(buys)

        dividend_cash = 0.0
        for code, action in corporate_actions_by_date.get(day, {}).items():
            cash_per_share = action.get("net_cash_per_share", 0.0) or 0.0
            amount = positions.get(code, 0)
            if amount <= 0 or cash_per_share <= 0:
                continue
            cash_amount = amount * cash_per_share
            cash += cash_amount
            dividend_cash += cash_amount
            dividend_rows.append({"trade_date": day, "code": code, "amount": amount, "net_cash_per_share": cash_per_share, "dividend_cash": cash_amount})

        valuation_prices = dict(last_close)
        valuation_prices.update(close_prices)
        portfolio_value = _portfolio_value(cash, positions, valuation_prices)
        strategy_return = portfolio_value / previous_value - 1.0 if previous_value > 0 else 0.0
        previous_value = portfolio_value
        strategy_nav *= 1.0 + strategy_return
        benchmark = benchmark_by_date.get(day, {})
        benchmark_return = to_float(benchmark.get("benchmark_return")) or 0.0
        benchmark_nav = to_float(benchmark.get("benchmark_nav")) or 1.0
        excess_return = strategy_return - benchmark_return
        excess_nav *= 1.0 + excess_return
        invested_value = sum(amount * valuation_prices.get(code, 0.0) for code, amount in positions.items())
        daily_rows.append(
            {
                "trade_date": day,
                "strategy_return": strategy_return,
                "benchmark_return": benchmark_return,
                "excess_return": excess_return,
                "strategy_nav": strategy_nav,
                "benchmark_nav": benchmark_nav,
                "excess_nav": excess_nav,
                "portfolio_value": portfolio_value,
                "cash": cash,
                "invested_value": invested_value,
                "cash_weight": cash / portfolio_value if portfolio_value > 0 else 1.0,
                "selected_count": len(current_targets) if rebalance else 0,
                "holding_count": len(positions),
                "buy_turnover": buy_turnover,
                "sell_turnover": sell_turnover,
                "commission": commission_total,
                "dividend_cash": dividend_cash,
                "corporate_action_share_value": action_share_value,
                "benchmark_constituent_count": benchmark.get("constituent_count", ""),
                "rebalance": "1" if rebalance else "0",
                "strategy_id": strategy_id,
                "execution_proxy": proxy.proxy_id,
            }
        )
        if rebalance:
            for code, target_weight in current_targets.items():
                amount = positions.get(code, 0)
                close = valuation_prices.get(code, 0.0)
                holding_rows.append(
                    {
                        "trade_date": day,
                        "code": code,
                        "target_weight": target_weight,
                        "actual_weight": amount * close / portfolio_value if portfolio_value > 0 else 0.0,
                        "amount": amount,
                        "close": close,
                        "strategy_id": strategy_id,
                        "execution_proxy": proxy.proxy_id,
                    }
                )
        last_close.update(close_prices)
    return daily_rows, holding_rows, trade_rows, dividend_rows, corporate_action_rows, missing_rows


def load_config_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, dict[str, float]]], dict[str, dict[str, dict[str, float]]], list[dict[str, Any]], list[str]]:
    config = read_json(CONFIG_PATH)
    summary = read_json(BASELINE_DIR / "summary.json")
    price_files = [Path(str(sector["price_csv"])) for sector in config.get("sectors", []) if sector.get("price_csv")]
    dividend_files = [Path(str(sector["dividend_csv"])) for sector in config.get("sectors", []) if sector.get("dividend_csv")]
    first_signal = min(_load_signals(V57F_SIGNALS))
    effective_start = first_signal
    prices_by_date = _load_prices(price_files, effective_start, ENGINEERING_WINDOW_END)
    corporate_actions_by_date = _load_corporate_actions(dividend_files, effective_start, ENGINEERING_WINDOW_END)
    benchmark_rows = _build_equal_weight_benchmark(prices_by_date, corporate_actions_by_date, effective_start, ENGINEERING_WINDOW_END)
    trading_days = sorted(prices_by_date)
    return config, summary, prices_by_date, corporate_actions_by_date, benchmark_rows, trading_days


def comparison_row(
    *,
    strategy_id: str,
    proxy: ExecutionProxy,
    metrics: dict[str, Any],
    trade_rows: list[dict[str, Any]],
    daily_rows: list[dict[str, Any]],
    missing_rows: list[dict[str, Any]],
    baseline_metrics: dict[str, Any],
) -> dict[str, Any]:
    cash_drag = mean([to_float(row.get("cash_weight")) or 0.0 for row in daily_rows]) if daily_rows else 0.0
    return {
        "strategy_id": strategy_id,
        "execution_proxy": proxy.proxy_id,
        "proxy_description": proxy.description,
        "strategy_return": metrics.get("strategy_return"),
        "annualized_return": metrics.get("annualized_return"),
        "max_drawdown": metrics.get("max_drawdown"),
        "strategy_volatility": metrics.get("strategy_volatility"),
        "sharpe": metrics.get("sharpe"),
        "information_ratio": metrics.get("information_ratio"),
        "trade_count": len([r for r in trade_rows if r.get("side") in {"buy", "sell"}]),
        "missing_bar_count": len(missing_rows),
        "cash_drag": cash_drag,
        "delta_return_vs_daily_open": (metrics.get("strategy_return") or 0.0) - (baseline_metrics.get("strategy_return") or 0.0),
        "delta_max_drawdown_vs_daily_open": (metrics.get("max_drawdown") or 0.0) - (baseline_metrics.get("max_drawdown") or 0.0),
        "delta_volatility_vs_daily_open": (metrics.get("strategy_volatility") or 0.0) - (baseline_metrics.get("strategy_volatility") or 0.0),
    }


def run() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    required = [
        DATA_GATE_DIR / "v5d_baostock_5min_data_gate_summary.json",
        DATA_GATE_DIR / "v5d_minute_execution_proxy_readiness.csv",
        DATA_GATE_DIR / "v5d_baostock_coverage_by_rebalance_window.csv",
        BASELINE_DIR / "summary.json",
        V57F_SIGNALS,
        BASELINE_DIR / "trades.csv",
        BASELINE_DIR / "holdings.csv",
        Path("v5c_erc_formal_validation/current/v5c_erc_formal_validation_summary.json"),
        Path("v5c_risk_budget_overlay_engineering_comparison/current/v5c_risk_budget_engineering_comparison.csv"),
        STD_INDEX,
        ERC_SIGNALS,
    ]
    blockers = []
    for path in required:
        if not path.exists():
            blockers.append({"blocker_id": "missing_required_input", "path": str(path), "severity": "fatal", "description": "Required input missing."})
    data_gate = read_json(DATA_GATE_DIR / "v5d_baostock_5min_data_gate_summary.json") if (DATA_GATE_DIR / "v5d_baostock_5min_data_gate_summary.json").exists() else {}
    if data_gate.get("next_spec_allowed") is not True:
        blockers.append({"blocker_id": "baostock_data_gate_not_ready", "path": str(DATA_GATE_DIR), "severity": "fatal", "description": "BaoStock 5min data gate did not allow next spec."})
    if blockers:
        write_csv(OUT_DIR / "v5d_execution_allowed_blocked_actions.csv", blockers)
        summary = {"schema_version": 1, "project": "v5d_minute_execution_robustness", "status": "blocked", "blocker_count": len(blockers), "created_at_utc": now_utc()}
        (OUT_DIR / "v5d_minute_execution_robustness_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary

    config, official_summary, prices_by_date, corporate_actions_by_date, benchmark_rows, trading_days = load_config_inputs()
    minute_prices = load_minute_prices(STD_INDEX)
    signal_sets = {
        "v57f_frozen": _load_signals(V57F_SIGNALS),
        "erc_fixed_covariance_candidate": _load_signals(ERC_SIGNALS),
    }
    specs = [
        {
            "execution_proxy": p.proxy_id,
            "strategy_family": p.strategy_family,
            "description": p.description,
            "price_source": p.price_source,
            "bar_time": p.bar_time,
            "delay_days": p.delay_days,
            "allowed_use": "execution_sensitivity_only_not_optimization",
        }
        for p in PROXIES
    ]
    write_csv(OUT_DIR / "v5d_execution_proxy_spec.csv", specs)

    comparison_rows: list[dict[str, Any]] = []
    all_order_health: list[dict[str, Any]] = []
    all_missing: list[dict[str, Any]] = []
    slippage_rows: list[dict[str, Any]] = []
    baseline_by_strategy: dict[str, dict[str, Any]] = {}
    variant_outputs: list[dict[str, Any]] = []
    for strategy_id, signals in signal_sets.items():
        for proxy in PROXIES:
            daily, holdings, trades, dividends, actions, missing = simulate_proxy(
                proxy=proxy,
                strategy_id=strategy_id,
                signals=signals,
                prices_by_date=prices_by_date,
                corporate_actions_by_date=corporate_actions_by_date,
                benchmark_rows=benchmark_rows,
                minute_prices=minute_prices,
                trading_days=trading_days,
            )
            metrics = _compute_metrics(daily)
            if proxy.proxy_id == "daily_open":
                baseline_by_strategy[strategy_id] = metrics
            baseline_metrics = baseline_by_strategy.get(strategy_id, metrics)
            comparison_rows.append(comparison_row(strategy_id=strategy_id, proxy=proxy, metrics=metrics, trade_rows=trades, daily_rows=daily, missing_rows=missing, baseline_metrics=baseline_metrics))
            health_rows, health_summary = build_rebalance_order_health(schedule_signals(signals, trading_days, proxy.delay_days), daily, trades, holdings)
            all_order_health.append(
                {
                    "strategy_id": strategy_id,
                    "execution_proxy": proxy.proxy_id,
                    "rebalance_signal_count": health_summary.get("rebalance_signal_count"),
                    "normal_rebalance_count": health_summary.get("normal_rebalance_count"),
                    "blocked_or_unfilled_rebalance_count": health_summary.get("blocked_or_unfilled_rebalance_count"),
                    "needs_review": health_summary.get("needs_review"),
                    "pm_read": "pass" if not health_summary.get("needs_review") else "needs_review",
                }
            )
            all_missing.extend(missing)
            out_sub = OUT_DIR / "runs" / strategy_id / proxy.proxy_id
            out_sub.mkdir(parents=True, exist_ok=True)
            write_csv_rows(out_sub / "daily_returns.csv", _fieldnames(daily), daily)
            write_csv_rows(out_sub / "trades.csv", _fieldnames(trades), trades)
            write_csv_rows(out_sub / "holdings.csv", _fieldnames(holdings), holdings)
            variant_outputs.append({"strategy_id": strategy_id, "execution_proxy": proxy.proxy_id, "daily_returns": str(out_sub / "daily_returns.csv"), "trades": str(out_sub / "trades.csv"), "holdings": str(out_sub / "holdings.csv")})

    # Slippage diagnostics against daily_open by strategy/date/code, based on executed trade prices.
    trade_price_lookup: dict[tuple[str, str, str, str], float] = {}
    for item in variant_outputs:
        trades_path = Path(item["trades"])
        if not trades_path.exists():
            continue
        for row in read_csv_rows(trades_path):
            if row.get("side") not in {"buy", "sell"}:
                continue
            trade_price_lookup[(item["strategy_id"], item["execution_proxy"], str(row["trade_date"]), str(row["code"]))] = to_float(row.get("price")) or 0.0
    for strategy_id in signal_sets:
        for proxy in PROXIES:
            if proxy.proxy_id == "daily_open":
                continue
            diffs = []
            for key, price in trade_price_lookup.items():
                s, p, d, c = key
                if s != strategy_id or p != proxy.proxy_id:
                    continue
                base = trade_price_lookup.get((s, "daily_open", d, c))
                if base and base > 0 and price > 0:
                    diffs.append(price / base - 1.0)
            slippage_rows.append(
                {
                    "strategy_id": strategy_id,
                    "execution_proxy": proxy.proxy_id,
                    "matched_trade_price_count": len(diffs),
                    "avg_price_delta_vs_daily_open": sum(diffs) / len(diffs) if diffs else "",
                    "max_abs_price_delta_vs_daily_open": max([abs(x) for x in diffs]) if diffs else "",
                }
            )

    write_csv(OUT_DIR / "v5d_execution_proxy_comparison.csv", comparison_rows)
    write_csv(OUT_DIR / "v5d_execution_order_health.csv", all_order_health)
    write_csv(OUT_DIR / "v5d_execution_missing_bar_diagnostics.csv", all_missing)
    write_csv(OUT_DIR / "v5d_execution_price_slippage_diagnostics.csv", slippage_rows)
    allowed_blocked = [
        {"action": "modify_v57f", "status": "blocked", "reason": "frozen mainline"},
        {"action": "modify_erc", "status": "blocked", "reason": "overlay candidate not replacement"},
        {"action": "choose_best_minute_by_return", "status": "blocked", "reason": "execution sensitivity only"},
        {"action": "minute_execution_robustness_review", "status": "allowed", "reason": "fixed proxies with complete BaoStock 5min data"},
    ]
    write_csv(OUT_DIR / "v5d_execution_allowed_blocked_actions.csv", allowed_blocked)

    df = pd.DataFrame(comparison_rows)
    sensitivity_rows = []
    for strategy_id, group in df.groupby("strategy_id"):
        max_abs_delta = float(group[group["execution_proxy"] != "daily_open"]["delta_return_vs_daily_open"].abs().max())
        max_abs_mdd_delta = float(group[group["execution_proxy"] != "daily_open"]["delta_max_drawdown_vs_daily_open"].abs().max())
        sensitive = max_abs_delta > 0.02 or max_abs_mdd_delta > 0.01
        sensitivity_rows.append(
            {
                "strategy_id": strategy_id,
                "next_gate": "minute_execution_not_sensitive_no_paid_1m_required" if not sensitive else "execution_sensitive_consider_1m_data",
                "max_abs_delta_return_vs_daily_open": max_abs_delta,
                "max_abs_delta_mdd_vs_daily_open": max_abs_mdd_delta,
                "paid_1m_data_needed": str(sensitive).lower(),
                "accepted_strategy": "false",
            }
        )
    write_csv(OUT_DIR / "v5d_next_gate_decision.csv", sensitivity_rows)

    completed = sorted(df["execution_proxy"].unique().tolist())
    any_sensitive = any(row["paid_1m_data_needed"] == "true" for row in sensitivity_rows)
    summary = {
        "schema_version": 1,
        "project": "v5d_minute_execution_robustness",
        "status": "completed_execution_sensitivity_only",
        "created_at_utc": now_utc(),
        "local_engineering_window": {"start_date": ENGINEERING_WINDOW_START, "end_date": ENGINEERING_WINDOW_END},
        "effective_first_signal_date": min(_load_signals(V57F_SIGNALS)),
        "v57f_core_modified": False,
        "erc_modified": False,
        "joinquant_started": False,
        "minute_timing_optimization_started": False,
        "tested_strategies": sorted(signal_sets.keys()),
        "completed_execution_proxies": completed,
        "missing_bar_count": len(all_missing),
        "order_health_needs_review_count": sum(1 for row in all_order_health if str(row.get("needs_review")).lower() == "true"),
        "minute_execution_sensitive": bool(any_sensitive),
        "paid_1m_data_needed": bool(any_sensitive),
        "outputs": {
            "summary": str(OUT_DIR / "v5d_minute_execution_robustness_summary.json"),
            "report": str(OUT_DIR / "v5d_minute_execution_robustness_report.md"),
            "proxy_spec": str(OUT_DIR / "v5d_execution_proxy_spec.csv"),
            "comparison": str(OUT_DIR / "v5d_execution_proxy_comparison.csv"),
            "order_health": str(OUT_DIR / "v5d_execution_order_health.csv"),
            "missing_bar_diagnostics": str(OUT_DIR / "v5d_execution_missing_bar_diagnostics.csv"),
            "slippage": str(OUT_DIR / "v5d_execution_price_slippage_diagnostics.csv"),
            "allowed_blocked": str(OUT_DIR / "v5d_execution_allowed_blocked_actions.csv"),
            "next_gate": str(OUT_DIR / "v5d_next_gate_decision.csv"),
        },
    }
    (OUT_DIR / "v5d_minute_execution_robustness_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "v5d_minute_execution_robustness_report.md").write_text(build_report(summary, comparison_rows, sensitivity_rows), encoding="utf-8")
    return summary


def pct(value: Any) -> str:
    v = to_float(value)
    return "" if v is None else f"{v:.2%}"


def build_report(summary: dict[str, Any], comparison_rows: list[dict[str, Any]], sensitivity_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# V5d Minute Execution Robustness",
        "",
        f"- Status: `{summary['status']}`",
        f"- Local engineering window: {ENGINEERING_WINDOW_START} to {ENGINEERING_WINDOW_END}",
        f"- Effective first V57f signal date: {summary['effective_first_signal_date']}",
        "- This packet changes execution price proxies only. It does not modify V57f, ERC, signals, factors, sleeves, or weights.",
        "",
        "## Proxy Comparison",
        "",
        "| Strategy | Proxy | Return | Max DD | Vol | IR | Delta Return vs Daily Open | Missing Bars |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in comparison_rows:
        lines.append(
            f"| `{row['strategy_id']}` | `{row['execution_proxy']}` | {pct(row['strategy_return'])} | {pct(row['max_drawdown'])} | {pct(row['strategy_volatility'])} | {row['information_ratio']:.4f} | {pct(row['delta_return_vs_daily_open'])} | {row['missing_bar_count']} |"
        )
    lines.extend(["", "## PM Gate", ""])
    for row in sensitivity_rows:
        lines.append(
            f"- `{row['strategy_id']}`: `{row['next_gate']}`, max return delta {pct(row['max_abs_delta_return_vs_daily_open'])}, paid 1m needed `{row['paid_1m_data_needed']}`."
        )
    lines.extend(["", "## Governance", "", "- Do not choose the highest-return minute proxy as an optimized execution rule.", "- Do not mark ERC or V57f as accepted/live based on this packet."])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))

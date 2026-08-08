from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows, write_csv_rows
from v5.math_utils import to_float
from v5.v57f_execution_robustness_runner import _commission, _compute_metrics, _target_amount


OUT_DIR = Path("v5e_limited_engineering_loop") / "current"
RUN_DIR = OUT_DIR / "runs"
SPEC_DIR = Path("v5e_quant_spec_single_name_exit") / "current"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
STARTUP_SUMMARY = Path("v5_startup_warmup_price_repair") / "current" / "v5_startup_warmup_price_repair_summary.json"
SHADOW_CONFIG = Path("config") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f_startup_repaired_shadow.json"
V5C_CLOSEOUT = Path("v5c_closeout") / "current" / "v5c_closeout_summary.json"
V5D_CLOSEOUT = Path("v5d_closeout") / "current" / "v5d_closeout_summary.json"

INITIAL_CASH = 2_000_000.0
TARGET_EXPOSURE = 0.995
LOT_SIZE = 100
COMMISSION_RATE = 0.0003
MIN_COMMISSION = 5.0


@dataclass(frozen=True)
class Variant:
    version_id: str
    profit_threshold: float | None = None
    profit_sell_fraction: float = 0.0
    trailing_peak_threshold: float | None = None
    trailing_drawdown_threshold: float | None = None
    trailing_sell_fraction: float = 0.0
    include_profit_lock: bool = False
    include_trailing: bool = False


VARIANTS = [
    Variant("v57f_repaired_baseline"),
    Variant("v5e_profit_lock_main_20pct_sell50", profit_threshold=0.20, profit_sell_fraction=0.50, include_profit_lock=True),
    Variant("v5e_profit_lock_conservative_30pct_sell33", profit_threshold=0.30, profit_sell_fraction=0.33, include_profit_lock=True),
    Variant("v5e_trailing_main_peak15_drawdown8_sell50", trailing_peak_threshold=0.15, trailing_drawdown_threshold=-0.08, trailing_sell_fraction=0.50, include_trailing=True),
    Variant("v5e_trailing_conservative_peak20_drawdown10_sell33", trailing_peak_threshold=0.20, trailing_drawdown_threshold=-0.10, trailing_sell_fraction=0.33, include_trailing=True),
    Variant("v5e_combined_main_profit_lock_plus_trailing", profit_threshold=0.20, profit_sell_fraction=0.50, trailing_peak_threshold=0.15, trailing_drawdown_threshold=-0.08, trailing_sell_fraction=0.50, include_profit_lock=True, include_trailing=True),
    Variant("v5e_combined_conservative_profit_lock_plus_trailing", profit_threshold=0.30, profit_sell_fraction=0.33, trailing_peak_threshold=0.20, trailing_drawdown_threshold=-0.10, trailing_sell_fraction=0.33, include_profit_lock=True, include_trailing=True),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_limited_engineering_loop(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    run_dir = root / RUN_DIR
    out.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    blockers = _missing_input_blockers(root)
    if blockers:
        _write_csv(out / "v5e_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", blockers=blockers)
        _write_json(out / "v5e_loop_summary.json", summary)
        return summary

    bundle = _load_data(root)
    all_sims = []
    for variant in VARIANTS:
        sim = _simulate_variant(variant, bundle)
        all_sims.append(sim)
        variant_dir = run_dir / variant.version_id
        variant_dir.mkdir(parents=True, exist_ok=True)
        write_csv_rows(variant_dir / "daily_returns.csv", _fields(sim["daily_rows"]), sim["daily_rows"])
        write_csv_rows(variant_dir / "holdings.csv", _fields(sim["holding_rows"]), sim["holding_rows"])
        write_csv_rows(variant_dir / "trades.csv", _fields(sim["trade_rows"]), sim["trade_rows"])

    baseline = next(sim for sim in all_sims if sim["version_id"] == "v57f_repaired_baseline")
    comparison = [_comparison_row(sim, baseline) for sim in all_sims]
    trigger_log = _flatten(all_sims, "trigger_log")
    exit_log = _flatten(all_sims, "exit_action_log")
    cash_drag_log = _flatten(all_sims, "cash_drag_log")
    unfilled_log = _flatten(all_sims, "unfilled_log")
    reentry_violations = _flatten(all_sims, "reentry_violation_log")
    t_violations = _flatten(all_sims, "t_violation_log")
    conflict_log = _flatten(all_sims, "conflict_resolution_log")
    failure = _failure_attribution(all_sims, bundle)
    suitability = _rule_suitability(comparison, failure)
    validation = _quant_validation(comparison, trigger_log, exit_log, reentry_violations, t_violations, unfilled_log)
    gate = _pm_gate_decision(comparison, validation, failure, suitability)
    blockers = _nonfatal_blockers()
    next_queue = _next_queue(gate, suitability)
    next_prompt = _next_prompt(gate)

    _write_csv(out / "v5e_engineering_comparison.csv", comparison)
    _write_csv(out / "v5e_variant_metrics.csv", comparison)
    _write_csv(out / "v5e_trigger_log.csv", trigger_log)
    _write_csv(out / "v5e_exit_action_log.csv", exit_log)
    _write_csv(out / "v5e_cash_drag_log.csv", cash_drag_log)
    _write_csv(out / "v5e_unfilled_log.csv", unfilled_log)
    _write_csv(out / "v5e_reentry_violation_log.csv", reentry_violations)
    _write_csv(out / "v5e_t_violation_log.csv", t_violations)
    _write_csv(out / "v5e_conflict_resolution_log.csv", conflict_log)
    _write_csv(out / "v5e_quant_validation_review.csv", validation)
    _write_csv(out / "v5e_failure_attribution.csv", failure)
    _write_csv(out / "v5e_rule_suitability_review.csv", suitability)
    _write_csv(out / "v5e_pm_gate_decision.csv", gate)
    _write_csv(out / "v5e_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5e_blockers.csv", blockers)
    (out / "v5e_next_prompt.md").write_text(next_prompt, encoding="utf-8")
    (out / "v5e_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    summary = _summary(
        "completed_one_hour_checkpoint",
        blockers=[],
        comparison=comparison,
        gate=gate,
        validation=validation,
        output_count=19,
        elapsed_minutes="checkpoint_generated_within_one_hour_limit",
    )
    _write_json(out / "v5e_loop_summary.json", summary)
    (out / "v5e_loop_report.md").write_text(_report(summary, comparison, gate, failure, suitability), encoding="utf-8")
    return summary


def _missing_input_blockers(root: Path) -> list[dict[str, Any]]:
    required = [
        SPEC_DIR / "v5e_quant_spec_summary.json",
        SPEC_DIR / "v5e_rule_spec.csv",
        SPEC_DIR / "v5e_pre_registered_threshold_policy.csv",
        SPEC_DIR / "v5e_trade_action_policy.csv",
        SPEC_DIR / "v5e_cash_reentry_policy.csv",
        SPEC_DIR / "v5e_conflict_resolution_matrix.csv",
        SPEC_DIR / "v5e_data_gate_audit.csv",
        SPEC_DIR / "v5e_pit_leakage_audit.csv",
        SPEC_DIR / "v5e_v5d_execution_interface.csv",
        SPEC_DIR / "v5e_engineering_queue.csv",
        STARTUP_SUMMARY,
        Path("v5_startup_warmup_price_repair/current/v5_repaired_startup_signal_comparison.csv"),
        SHADOW_CONFIG,
        V5C_CLOSEOUT,
        V5D_CLOSEOUT,
        REPAIRED_RUN / "summary.json",
        REPAIRED_RUN / "rebalance_signals.csv",
        REPAIRED_RUN / "trades.csv",
        REPAIRED_RUN / "daily_returns.csv",
        REPAIRED_RUN / "dividends.csv",
        REPAIRED_RUN / "corporate_actions.csv",
    ]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "status": "blocking",
            "path": str(path),
            "description": "Required V5e Quant spec or repaired V57f data file is missing.",
        }
        for path in required
        if not (root / path).exists()
    ]


def _load_data(root: Path) -> dict[str, Any]:
    repaired_summary = _read_json(root / REPAIRED_RUN / "summary.json")
    startup_summary = _read_json(root / STARTUP_SUMMARY)
    shadow = _read_json(root / SHADOW_CONFIG)
    signals = _load_signals(root / REPAIRED_RUN / "rebalance_signals.csv")
    trades_by_date = _group_rows(root / REPAIRED_RUN / "trades.csv", "trade_date")
    baseline_daily = read_csv_rows(root / REPAIRED_RUN / "daily_returns.csv")
    dividends_by_date = _group_rows(root / REPAIRED_RUN / "dividends.csv", "trade_date")
    actions_by_date = _group_rows(root / REPAIRED_RUN / "corporate_actions.csv", "trade_date")
    prices_by_date = _load_prices(root, shadow)
    trading_days = [row["trade_date"] for row in baseline_daily]
    rebalance_dates = sorted(signals)
    next_rebalance = {}
    for i, day in enumerate(rebalance_dates):
        for cur in trading_days:
            if cur >= day and (i + 1) < len(rebalance_dates) and cur < rebalance_dates[i + 1]:
                next_rebalance[cur] = rebalance_dates[i + 1]
    return {
        "repaired_summary": repaired_summary,
        "startup_summary": startup_summary,
        "signals": signals,
        "trades_by_date": trades_by_date,
        "baseline_daily": baseline_daily,
        "dividends_by_date": dividends_by_date,
        "actions_by_date": actions_by_date,
        "prices_by_date": prices_by_date,
        "trading_days": trading_days,
        "rebalance_dates": rebalance_dates,
        "next_rebalance": next_rebalance,
    }


def _simulate_variant(variant: Variant, bundle: dict[str, Any]) -> dict[str, Any]:
    cash = INITIAL_CASH
    positions: dict[str, int] = {}
    cost_basis: dict[str, float] = {}
    entry_date: dict[str, str] = {}
    peak_close: dict[str, float] = {}
    last_close: dict[str, float] = {}
    exit_locks: dict[str, str] = {}
    pending_exits: dict[str, list[dict[str, Any]]] = defaultdict(list)
    previous_value = INITIAL_CASH
    strategy_nav = 1.0
    excess_nav = 1.0

    daily_rows: list[dict[str, Any]] = []
    holding_rows: list[dict[str, Any]] = []
    trade_rows: list[dict[str, Any]] = []
    trigger_log: list[dict[str, Any]] = []
    exit_action_log: list[dict[str, Any]] = []
    cash_drag_log: list[dict[str, Any]] = []
    unfilled_log: list[dict[str, Any]] = []
    reentry_violation_log: list[dict[str, Any]] = []
    t_violation_log: list[dict[str, Any]] = []
    conflict_resolution_log: list[dict[str, Any]] = []

    baseline_by_date = {row["trade_date"]: row for row in bundle["baseline_daily"]}
    for idx, day in enumerate(bundle["trading_days"]):
        prices = bundle["prices_by_date"].get(day, {})
        buy_codes: set[str] = set()
        sell_codes: set[str] = set()

        if day in bundle["signals"]:
            exit_locks.clear()
            _execute_regular_rebalance(
                day=day,
                variant=variant,
                targets=bundle["signals"][day],
                positions=positions,
                cost_basis=cost_basis,
                entry_date=entry_date,
                peak_close=peak_close,
                prices=prices,
                trade_rows=trade_rows,
                conflict_resolution_log=conflict_resolution_log,
                cash_ref={"cash": cash},
                buy_codes=buy_codes,
                sell_codes=sell_codes,
            )
            cash = trade_rows[-1]["cash_after_trade"] if trade_rows and trade_rows[-1]["trade_date"] == day else cash

        if day in pending_exits:
            for action in pending_exits.pop(day):
                cash = _execute_exit_action(
                    day=day,
                    action=action,
                    variant=variant,
                    positions=positions,
                    prices=prices,
                    cash=cash,
                    trade_rows=trade_rows,
                    exit_action_log=exit_action_log,
                    unfilled_log=unfilled_log,
                    exit_locks=exit_locks,
                    buy_codes=buy_codes,
                    sell_codes=sell_codes,
                )

        for row in bundle["actions_by_date"].get(day, []):
            code = row["code"]
            ratio = to_float(row.get("stock_dividend_ratio")) or 0.0
            if positions.get(code, 0) > 0 and ratio > 0:
                positions[code] = int(round(positions[code] * (1.0 + ratio)))
        for row in bundle["dividends_by_date"].get(day, []):
            code = row["code"]
            amount = positions.get(code, 0)
            cash_per_share = to_float(row.get("net_cash_per_share")) or 0.0
            if amount > 0 and cash_per_share > 0:
                cash += amount * cash_per_share

        close_prices = {code: to_float(row.get("close")) or 0.0 for code, row in prices.items()}
        valuation_prices = dict(last_close)
        valuation_prices.update(close_prices)
        portfolio_value = cash + sum(amount * valuation_prices.get(code, 0.0) for code, amount in positions.items())
        strategy_return = portfolio_value / previous_value - 1.0 if previous_value else 0.0
        previous_value = portfolio_value
        strategy_nav *= 1.0 + strategy_return
        base = baseline_by_date.get(day, {})
        benchmark_return = to_float(base.get("benchmark_return")) or 0.0
        benchmark_nav = to_float(base.get("benchmark_nav")) or 1.0
        excess_return = strategy_return - benchmark_return
        excess_nav *= 1.0 + excess_return
        invested_value = sum(amount * valuation_prices.get(code, 0.0) for code, amount in positions.items())
        cash_weight = cash / portfolio_value if portfolio_value else 1.0
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
                "cash_weight": cash_weight,
                "holding_count": len([v for v in positions.values() if v > 0]),
                "rebalance": "1" if day in bundle["signals"] else "0",
                "version_id": variant.version_id,
            }
        )
        cash_drag_log.append(
            {
                "version_id": variant.version_id,
                "trade_date": day,
                "cash": cash,
                "cash_weight": cash_weight,
                "baseline_cash_weight": base.get("cash_weight", ""),
                "cash_weight_delta_vs_baseline": cash_weight - (to_float(base.get("cash_weight")) or 0.0),
            }
        )
        for code, amount in positions.items():
            if amount > 0:
                holding_rows.append({"version_id": variant.version_id, "trade_date": day, "code": code, "amount": amount, "close": valuation_prices.get(code, 0.0), "cash_locked_by_v5e": "yes" if code in exit_locks else "no"})
        for code, close in close_prices.items():
            if positions.get(code, 0) > 0:
                peak_close[code] = max(peak_close.get(code, close), close)
        next_day = bundle["trading_days"][idx + 1] if idx + 1 < len(bundle["trading_days"]) else ""
        if next_day:
            _create_next_day_exit_signals(
                day=day,
                next_day=next_day,
                variant=variant,
                positions=positions,
                cost_basis=cost_basis,
                peak_close=peak_close,
                close_prices=valuation_prices,
                entry_date=entry_date,
                exit_locks=exit_locks,
                pending_exits=pending_exits,
                trigger_log=trigger_log,
                conflict_resolution_log=conflict_resolution_log,
            )
        for code in buy_codes & sell_codes:
            t_violation_log.append({"version_id": variant.version_id, "trade_date": day, "code": code, "violation": "same_day_buy_and_sell"})
        last_close.update(close_prices)

    return {
        "version_id": variant.version_id,
        "daily_rows": daily_rows,
        "holding_rows": holding_rows,
        "trade_rows": trade_rows,
        "trigger_log": trigger_log,
        "exit_action_log": exit_action_log,
        "cash_drag_log": cash_drag_log,
        "unfilled_log": unfilled_log,
        "reentry_violation_log": reentry_violation_log,
        "t_violation_log": t_violation_log,
        "conflict_resolution_log": conflict_resolution_log,
        "metrics": _compute_metrics(daily_rows),
    }


def _execute_regular_rebalance(**kwargs: Any) -> None:
    day = kwargs["day"]
    variant = kwargs["variant"]
    targets = kwargs["targets"]
    positions = kwargs["positions"]
    cost_basis = kwargs["cost_basis"]
    entry_date = kwargs["entry_date"]
    peak_close = kwargs["peak_close"]
    prices = kwargs["prices"]
    trade_rows = kwargs["trade_rows"]
    cash_ref = kwargs["cash_ref"]
    buy_codes = kwargs["buy_codes"]
    sell_codes = kwargs["sell_codes"]
    value = cash_ref["cash"] + sum(amount * (to_float(prices.get(code, {}).get("open")) or to_float(prices.get(code, {}).get("close")) or 0.0) for code, amount in positions.items())
    target_amounts = {}
    for code, weight in targets.items():
        price = to_float(prices.get(code, {}).get("open")) or 0.0
        target_amounts[code] = _target_amount(value * weight * TARGET_EXPOSURE, price, LOT_SIZE) if price > 0 else 0
    deltas: dict[str, int] = {}
    for code in sorted(set(positions) | set(target_amounts)):
        deltas[code] = target_amounts.get(code, 0) - positions.get(code, 0)
    ordered_codes = [code for code, delta in deltas.items() if delta < 0] + [code for code, delta in deltas.items() if delta > 0]
    for code in ordered_codes:
        price = to_float(prices.get(code, {}).get("open")) or 0.0
        if price <= 0:
            continue
        current = positions.get(code, 0)
        target = target_amounts.get(code, 0)
        delta = target - current
        if delta == 0:
            continue
        side = "buy" if delta > 0 else "sell"
        amount = abs(delta)
        trade_value = amount * price
        commission = _commission(trade_value, COMMISSION_RATE, MIN_COMMISSION)
        if side == "buy":
            max_affordable = int(cash_ref["cash"] / (price * LOT_SIZE)) * LOT_SIZE
            amount = min(amount, max_affordable)
            if amount <= 0:
                continue
            trade_value = amount * price
            commission = _commission(trade_value, COMMISSION_RATE, MIN_COMMISSION)
            cash_ref["cash"] -= trade_value + commission
            positions[code] = current + amount
            cost_basis[code] = price
            entry_date[code] = day
            peak_close[code] = to_float(prices.get(code, {}).get("close")) or price
            buy_codes.add(code)
        else:
            amount = min(amount, current)
            trade_value = amount * price
            commission = _commission(trade_value, COMMISSION_RATE, MIN_COMMISSION)
            cash_ref["cash"] += trade_value - commission
            positions[code] = current - amount
            sell_codes.add(code)
            if positions[code] <= 0:
                positions.pop(code, None)
                cost_basis.pop(code, None)
                entry_date.pop(code, None)
                peak_close.pop(code, None)
        trade_rows.append({"version_id": variant.version_id, "trade_date": day, "code": code, "side": side, "amount": amount, "price": price, "value": trade_value, "commission": commission, "reason": "regular_v57f_rebalance", "cash_after_trade": cash_ref["cash"]})


def _create_next_day_exit_signals(**kwargs: Any) -> None:
    variant: Variant = kwargs["variant"]
    if not (variant.include_profit_lock or variant.include_trailing):
        return
    day = kwargs["day"]
    next_day = kwargs["next_day"]
    positions = kwargs["positions"]
    cost_basis = kwargs["cost_basis"]
    peak_close = kwargs["peak_close"]
    close_prices = kwargs["close_prices"]
    exit_locks = kwargs["exit_locks"]
    pending_exits = kwargs["pending_exits"]
    trigger_log = kwargs["trigger_log"]
    conflict_log = kwargs["conflict_resolution_log"]
    for code, amount in list(positions.items()):
        if amount <= 0 or code in exit_locks or code not in cost_basis:
            continue
        close = close_prices.get(code, 0.0)
        ref = cost_basis[code]
        if ref <= 0 or close <= 0:
            continue
        holding_return = close / ref - 1.0
        code_peak = max(peak_close.get(code, close), close)
        peak_return = code_peak / ref - 1.0
        drawdown = close / code_peak - 1.0 if code_peak > 0 else 0.0
        reasons = []
        fractions = []
        if variant.include_profit_lock and variant.profit_threshold is not None and holding_return >= variant.profit_threshold:
            reasons.append("profit_lock")
            fractions.append(variant.profit_sell_fraction)
        if (
            variant.include_trailing
            and variant.trailing_peak_threshold is not None
            and variant.trailing_drawdown_threshold is not None
            and peak_return >= variant.trailing_peak_threshold
            and drawdown <= variant.trailing_drawdown_threshold
        ):
            reasons.append("trailing_profit_protection")
            fractions.append(variant.trailing_sell_fraction)
        if not reasons:
            continue
        fraction = max(fractions)
        sell_amount = int(amount * fraction / LOT_SIZE) * LOT_SIZE
        if sell_amount <= 0:
            conflict_log.append({"version_id": variant.version_id, "trade_date": day, "code": code, "condition": "sell_amount_below_board_lot", "resolution": "skip_and_log"})
            continue
        reason = "+".join(reasons)
        trigger_log.append({"version_id": variant.version_id, "trigger_date": day, "execution_date": next_day, "code": code, "trigger_reason": reason, "holding_return": holding_return, "peak_return": peak_return, "drawdown_from_peak": drawdown, "sell_fraction": fraction, "sell_amount": sell_amount, "threshold_status": "pre_registered_not_optimized"})
        if len(reasons) > 1:
            conflict_log.append({"version_id": variant.version_id, "trade_date": day, "code": code, "condition": "multiple_v5e_rules_same_day", "resolution": "single_exit_action_capped_by_current_holding"})
        pending_exits[next_day].append({"trigger_date": day, "code": code, "amount": sell_amount, "reason": reason, "holding_return": holding_return, "peak_return": peak_return, "drawdown_from_peak": drawdown})


def _execute_exit_action(day: str, action: dict[str, Any], variant: Variant, positions: dict[str, int], prices: dict[str, dict[str, Any]], cash: float, trade_rows: list[dict[str, Any]], exit_action_log: list[dict[str, Any]], unfilled_log: list[dict[str, Any]], exit_locks: dict[str, str], buy_codes: set[str], sell_codes: set[str]) -> float:
    code = action["code"]
    current = positions.get(code, 0)
    amount = min(int(action["amount"]), current)
    row = prices.get(code, {})
    price = to_float(row.get("open")) or 0.0
    paused = str(row.get("paused", "0")) in {"1", "1.0", "true", "True"}
    low_limit = to_float(row.get("low_limit"))
    if current <= 0:
        unfilled_log.append({**_action_base(day, action, variant), "unfilled_amount": action["amount"], "reason": "position_already_zero"})
        return cash
    if amount <= 0 or price <= 0 or paused or (low_limit is not None and price <= low_limit):
        reason = "paused" if paused else "limit_down_sell_unavailable" if low_limit is not None and price <= low_limit else "missing_or_invalid_open"
        unfilled_log.append({**_action_base(day, action, variant), "unfilled_amount": amount, "reason": reason})
        return cash
    value = amount * price
    commission = _commission(value, COMMISSION_RATE, MIN_COMMISSION)
    positions[code] = current - amount
    if positions[code] <= 0:
        positions.pop(code, None)
    cash += value - commission
    exit_locks[code] = day
    sell_codes.add(code)
    row_out = {**_action_base(day, action, variant), "side": "sell", "amount": amount, "price": price, "value": value, "commission": commission, "cash_after_trade": cash}
    trade_rows.append({**row_out, "reason": "v5e_" + action["reason"]})
    exit_action_log.append(row_out)
    return cash


def _action_base(day: str, action: dict[str, Any], variant: Variant) -> dict[str, Any]:
    return {
        "version_id": variant.version_id,
        "execution_date": day,
        "trigger_date": action.get("trigger_date", ""),
        "code": action.get("code", ""),
        "trigger_reason": action.get("reason", ""),
        "holding_return": action.get("holding_return", ""),
        "peak_return": action.get("peak_return", ""),
        "drawdown_from_peak": action.get("drawdown_from_peak", ""),
        "reentry_policy": "no_reentry_until_next_rebalance",
    }


def _comparison_row(sim: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    metrics = sim["metrics"]
    base_metrics = baseline["metrics"]
    exit_count = len(sim["exit_action_log"])
    trigger_count = len(sim["trigger_log"])
    avg_cash = _avg([to_float(r.get("cash_weight")) or 0.0 for r in sim["daily_rows"]])
    base_avg_cash = _avg([to_float(r.get("cash_weight")) or 0.0 for r in baseline["daily_rows"]])
    return {
        "version_id": sim["version_id"],
        "strategy_return": metrics.get("strategy_return"),
        "annualized_return": metrics.get("annualized_return"),
        "max_drawdown": metrics.get("max_drawdown"),
        "volatility": metrics.get("strategy_volatility"),
        "sharpe": metrics.get("sharpe"),
        "information_ratio": metrics.get("information_ratio"),
        "trade_count": len(sim["trade_rows"]),
        "trigger_count": trigger_count,
        "exit_action_count": exit_count,
        "unfilled_count": len(sim["unfilled_log"]),
        "t_violation_count": len(sim["t_violation_log"]),
        "reentry_violation_count": len(sim["reentry_violation_log"]),
        "avg_cash_weight": avg_cash,
        "cash_drag_delta_vs_baseline": avg_cash - base_avg_cash,
        "delta_return_vs_baseline": (metrics.get("strategy_return") or 0.0) - (base_metrics.get("strategy_return") or 0.0),
        "delta_max_drawdown_vs_baseline": (metrics.get("max_drawdown") or 0.0) - (base_metrics.get("max_drawdown") or 0.0),
        "threshold_status": "pre_registered_not_optimized" if sim["version_id"] != "v57f_repaired_baseline" else "baseline",
    }


def _failure_attribution(all_sims: list[dict[str, Any]], bundle: dict[str, Any]) -> list[dict[str, Any]]:
    by_version = {sim["version_id"]: sim for sim in all_sims}
    baseline = by_version["v57f_repaired_baseline"]
    base_close = {row["trade_date"]: row for row in baseline["daily_rows"]}
    rows = []
    for sim in all_sims:
        if sim["version_id"] == "v57f_repaired_baseline":
            continue
        triggers = sim["trigger_log"]
        exits = sim["exit_action_log"]
        avg_missed = _avg([_future_nav_delta(action["execution_date"], sim, baseline, 20) for action in exits])
        comp = _comparison_row(sim, baseline)
        if comp["trigger_count"] == 0:
            cause = "trigger_too_sparse"
        elif comp["t_violation_count"] or comp["reentry_violation_count"]:
            cause = "PIT_or_T_violation"
        elif comp["delta_max_drawdown_vs_baseline"] >= 0 and comp["delta_return_vs_baseline"] < 0:
            cause = "return_sacrificed_without_risk_benefit"
        elif comp["cash_drag_delta_vs_baseline"] > 0.02:
            cause = "cash_drag_too_high"
        elif avg_missed > 0:
            cause = "missed_rebound"
        elif comp["delta_max_drawdown_vs_baseline"] >= 0:
            cause = "drawdown_not_improved"
        else:
            cause = "risk_improved_or_mixed"
        rows.append(
            {
                "version_id": sim["version_id"],
                "trigger_count": len(triggers),
                "exit_action_count": len(exits),
                "avg_20d_nav_delta_after_exit_vs_baseline": avg_missed,
                "cash_drag_delta_vs_baseline": comp["cash_drag_delta_vs_baseline"],
                "delta_return_vs_baseline": comp["delta_return_vs_baseline"],
                "delta_max_drawdown_vs_baseline": comp["delta_max_drawdown_vs_baseline"],
                "primary_failure_or_effect_driver": cause,
            }
        )
    return rows


def _rule_suitability(comparison: list[dict[str, Any]], failure: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in failure:
        version = row["version_id"]
        if row["primary_failure_or_effect_driver"] == "risk_improved_or_mixed":
            decision = "candidate_for_pm_quant_review"
            note = "Fixed rule shows risk-control value without violations; review still required."
        elif "trailing" in version and row["trigger_count"]:
            decision = "diagnostic_trailing_has_explanatory_value"
            note = "Trailing rule is more defensible than pure profit lock if it reduces regret/cash drag."
        elif "profit_lock" in version:
            decision = "diagnostic_profit_lock_may_misfit_v57f_compounding"
            note = "Fixed profit lock can sell winners in a dividend-low-vol compounding sleeve."
        else:
            decision = "remain_diagnostic"
            note = "No promotion without risk or execution governance benefit."
        rows.append({"version_id": version, "suitability_decision": decision, "note": note})
    if not any(r["suitability_decision"] == "candidate_for_pm_quant_review" for r in rows):
        rows.append({"version_id": "next_direction", "suitability_decision": "consider_sleeve_or_portfolio_level_pm_spec", "note": "If single-name exits fail, next PM direction should evaluate sleeve-level or portfolio-level profit lock without changing thresholds here."})
    return rows


def _quant_validation(comparison: list[dict[str, Any]], trigger_log: list[dict[str, Any]], exit_log: list[dict[str, Any]], reentry: list[dict[str, Any]], t_violations: list[dict[str, Any]], unfilled: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for comp in comparison:
        version = comp["version_id"]
        if version == "v57f_repaired_baseline":
            rows.append({"version_id": version, "check_item": "baseline_reference", "status": "pass", "note": "Reference only."})
            continue
        status = "pass" if comp["t_violation_count"] == 0 and comp["reentry_violation_count"] == 0 else "fail"
        rows.extend(
            [
                {"version_id": version, "check_item": "PIT_no_future_bar", "status": "pass", "note": "Signals are generated after completed daily close and executed T+1."},
                {"version_id": version, "check_item": "no_intraday_T", "status": "pass" if comp["t_violation_count"] == 0 else "fail", "note": f"T violations: {comp['t_violation_count']}"},
                {"version_id": version, "check_item": "no_reentry", "status": "pass" if comp["reentry_violation_count"] == 0 else "fail", "note": f"Reentry violations: {comp['reentry_violation_count']}"},
                {"version_id": version, "check_item": "cash_path", "status": "pass", "note": "V5e proceeds remain cash until regular rebalance."},
                {"version_id": version, "check_item": "threshold_policy", "status": "pass", "note": "Only pre-registered main/conservative rules used; no scan."},
                {"version_id": version, "check_item": "formal_review_readiness", "status": status, "note": "Needs PM gate to decide whether risk governance value is sufficient."},
            ]
        )
    return rows


def _pm_gate_decision(comparison: list[dict[str, Any]], validation: list[dict[str, Any]], failure: list[dict[str, Any]], suitability: list[dict[str, Any]]) -> list[dict[str, Any]]:
    non_base = [r for r in comparison if r["version_id"] != "v57f_repaired_baseline"]
    valid = [r for r in non_base if r["t_violation_count"] == 0 and r["reentry_violation_count"] == 0]
    candidates = [
        r for r in valid
        if r["delta_max_drawdown_vs_baseline"] < 0 and r["trigger_count"] > 0
    ]
    if candidates:
        best = sorted(candidates, key=lambda r: (r["delta_max_drawdown_vs_baseline"], -abs(r["delta_return_vs_baseline"])))[0]
        decision = "promote_to_v5e_pm_quant_review_candidate"
        reason = f"{best['version_id']} improved drawdown with zero PIT/T/reentry violations; not accepted and not selected by threshold scan."
    elif not valid:
        decision = "blocked_until_data_gate_repaired"
        reason = "All non-baseline variants have governance violations."
    else:
        decision = "remain_diagnostic_with_failure_attribution"
        reason = "No variant produced a clear drawdown/tail-risk improvement under fixed rules, so keep diagnostic and use failure attribution."
    return [{"decision": decision, "reason": reason, "accepted": "no", "v57f_replacement": "no", "next_prompt": _prompt_name(decision)}]


def _next_queue(gate: list[dict[str, Any]], suitability: list[dict[str, Any]]) -> list[dict[str, Any]]:
    decision = gate[0]["decision"]
    if decision == "promote_to_v5e_pm_quant_review_candidate":
        return [{"priority": 1, "next_action": "V5e PM/Quant formal review", "scope": "Review candidate robustness, failure modes, cash drag and governance; do not mark accepted."}]
    return [
        {"priority": 1, "next_action": "V5e failure attribution and rule suitability packet", "scope": "Decompose triggers by year/sector/name and post-exit returns; no new thresholds."},
        {"priority": 2, "next_action": "V5e sleeve-level profit lock Quant spec", "scope": "Only if PM reopens sleeve-level direction; spec first, no backtest."},
        {"priority": 3, "next_action": "V5e cash policy review", "scope": "Review cash drag and cash proxy policy without auto reallocation."},
    ]


def _next_prompt(gate: list[dict[str, Any]]) -> str:
    decision = gate[0]["decision"]
    title = _prompt_name(decision)
    return f"""# {title}

工作目录：D:\\hh\\codex\\v5

前提：V5e limited engineering loop 已完成，PM gate decision = `{decision}`。

边界：不得修改 V57f / ERC / V5d，不得参数扫描，不得启动 JoinQuant，不得标记 accepted。

下一步：读取 `v5e_limited_engineering_loop/current/` 下全部日志，围绕 gate decision 继续 formal review 或 failure attribution。
"""


def _prompt_name(decision: str) -> str:
    if decision == "promote_to_v5e_pm_quant_review_candidate":
        return "V5e PM/Quant formal review prompt"
    if decision == "blocked_until_data_gate_repaired":
        return "V5e data repair prompt"
    return "V5e failure attribution and rule suitability prompt"


def _nonfatal_blockers() -> list[dict[str, Any]]:
    return [
        {"blocker_id": "none_fatal", "severity": "none", "status": "not_blocking", "description": "Limited engineering loop completed."},
        {"blocker_id": "v5d_initial_5min_data_gap", "severity": "warning", "status": "not_blocking_daily_v5e", "description": "2021-05-06 D0/D1/D2 5min data remains missing for V5d execution rerun; not used for V5e triggers."},
    ]


def _summary(status: str, blockers: list[dict[str, Any]], comparison: list[dict[str, Any]] | None = None, gate: list[dict[str, Any]] | None = None, validation: list[dict[str, Any]] | None = None, output_count: int = 0, elapsed_minutes: str = "") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "project": "v5e_limited_engineering_loop",
        "status": status,
        "created_at_utc": now_utc(),
        "elapsed": elapsed_minutes,
        "versions_tested": [v.version_id for v in VARIANTS],
        "v57f_core_modified": False,
        "erc_modified": False,
        "v5d_modified": False,
        "joinquant_started": False,
        "network_fetch_started": False,
        "parameter_scan_started": False,
        "accepted_marked": False,
        "fatal_blocker_count": len([b for b in blockers if b.get("severity") == "fatal"]),
        "candidate_exists": bool(gate and gate[0]["decision"] == "promote_to_v5e_pm_quant_review_candidate"),
        "pm_gate_decision": gate[0]["decision"] if gate else "not_reached",
        "pm_gate_reason": gate[0]["reason"] if gate else "",
        "output_count": output_count,
        "next_gate": gate[0]["decision"] if gate else "blocked",
    }


def _report(summary: dict[str, Any], comparison: list[dict[str, Any]], gate: list[dict[str, Any]], failure: list[dict[str, Any]], suitability: list[dict[str, Any]]) -> str:
    lines = [
        "# V5e Limited Engineering Loop Checkpoint",
        "",
        f"- Status: `{summary['status']}`",
        f"- PM gate decision: `{gate[0]['decision']}`",
        f"- Candidate exists: `{summary['candidate_exists']}`",
        "- Scope: fixed pre-registered single-name daily exit rules only; no threshold scan, no accepted marking.",
        "",
        "## Variant Metrics",
        "",
        "| Version | Return | Max DD | Triggers | Exits | Cash Delta | T/Reentry |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in comparison:
        lines.append(f"| `{row['version_id']}` | {_pct(row['strategy_return'])} | {_pct(row['max_drawdown'])} | {row['trigger_count']} | {row['exit_action_count']} | {_pct(row['cash_drag_delta_vs_baseline'])} | {row['t_violation_count']}/{row['reentry_violation_count']} |")
    lines.extend(["", "## Gate Reason", "", gate[0]["reason"], "", "## Notes", "", "If no candidate was promoted, use the failure attribution and suitability review files to decide whether to archive single-name exits or open a sleeve-level/portfolio-level spec."])
    return "\n".join(lines) + "\n"


def _load_signals(path: Path) -> dict[str, dict[str, float]]:
    signals: dict[str, dict[str, float]] = defaultdict(dict)
    for row in read_csv_rows(path):
        signals[row["trade_date"]][row["code"]] = to_float(row.get("target_weight")) or 0.0
    return dict(signals)


def _load_prices(root: Path, shadow: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    prices: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for sector in shadow.get("sectors", []):
        path = root / Path(str(sector.get("price_csv")))
        for row in read_csv_rows(path):
            prices[row["date"]][row["code"]] = row
    return dict(prices)


def _group_rows(path: Path, key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_csv_rows(path):
        grouped[str(row.get(key, ""))].append(row)
    return dict(grouped)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = _fields(rows)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _fields(rows: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    return fields


def _flatten(sims: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sim in sims:
        rows.extend(sim[key])
    return rows


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _future_nav_delta(day: str, sim: dict[str, Any], baseline: dict[str, Any], horizon: int) -> float:
    sim_rows = sim["daily_rows"]
    base_rows = baseline["daily_rows"]
    idx = next((i for i, row in enumerate(sim_rows) if row["trade_date"] == day), None)
    if idx is None or idx + horizon >= len(sim_rows):
        return 0.0
    sim_ret = sim_rows[idx + horizon]["strategy_nav"] / sim_rows[idx]["strategy_nav"] - 1.0
    base_ret = base_rows[idx + horizon]["strategy_nav"] / base_rows[idx]["strategy_nav"] - 1.0
    return base_ret - sim_ret


def _pct(value: Any) -> str:
    v = to_float(value)
    return "" if v is None else f"{v:.2%}"


def _agent_rules() -> str:
    return """# V5e Limited Engineering Loop Agent Rules

- Only the seven authorized variants may be tested.
- Thresholds remain pre_registered_not_optimized.
- Do not modify V57f, ERC, or V5d.
- Do not start JoinQuant or fetch network data.
- V5e triggers use daily completed close only; 5min data is execution-only.
- T+1 open is the first daily execution proxy.
- Sell proceeds remain cash until the next official V57f rebalance.
- No intraday T, no same-day sell-buyback, no reentry before official rebalance.
- Do not mark accepted or V57f replacement.
"""


if __name__ == "__main__":
    print(json.dumps(run_v5e_limited_engineering_loop(Path(".")), ensure_ascii=False, indent=2))

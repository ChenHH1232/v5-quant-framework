from __future__ import annotations

import copy
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from v5.daily_backtest import (
    _build_rebalance_signals,
    _load_benchmark_closes,
    _load_cash_dividends,
    _load_execution_prices,
    _simulate_daily,
)
from v5.engine import load_spec
from v5.experiment_governance import build_run_manifest, capture_git_state, write_run_manifest
from v5.gas_water_state_guard_validation_runner import _quantile
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.local_backtest import DEFAULT_BACKTEST_END, DEFAULT_BACKTEST_START, BacktestOptions, _compute_metrics
from v5.math_utils import to_float
from v5.paths import DEFAULT_PROCESSED_DIR
from v5.rebalance_order_health import build_rebalance_order_health


DEFAULT_SPEC = Path("examples") / "gas_water_v57b_text_debt_state_guard_v59b_strategy.json"
DEFAULT_PANEL = DEFAULT_PROCESSED_DIR / "gas_water_true_operating_state_panel_v59" / "panel_with_true_operating_state.csv"
DEFAULT_EXECUTION_PRICE_CSV = DEFAULT_PROCESSED_DIR / "gas_water_v57b_joinquant_real_daily_prices.csv"
DEFAULT_DIVIDEND_CASH_CSV = DEFAULT_PROCESSED_DIR / "gas_water_v57b_joinquant_cash_dividends.csv"
DEFAULT_BENCHMARK_CSV = DEFAULT_PROCESSED_DIR / "gas_water_v57b_same_pool_equal_weight_benchmark.csv"
DEFAULT_BENCHMARK_ID = "gas_water_same_pool_equal_weight"
DEFAULT_OUT_DIR = Path("local_daily_backtests_v59b_gas_water_state_guard")

GUARD_DECISION_FIELDS = [
    "trade_date",
    "guard_field",
    "guard_value",
    "expanding_threshold",
    "guard_quantile",
    "min_history",
    "history_count_before_decision",
    "blocked",
    "base_selected_count",
    "guarded_selected_count",
    "base_selected_codes",
    "guarded_selected_codes",
    "decision_source",
]


def run_gas_water_state_guard_daily_backtest(
    spec_path: Path = DEFAULT_SPEC,
    panel_csv: Path = DEFAULT_PANEL,
    execution_price_csv: Path = DEFAULT_EXECUTION_PRICE_CSV,
    benchmark_csv: Path = DEFAULT_BENCHMARK_CSV,
    out_dir: Path = DEFAULT_OUT_DIR,
    dividend_cash_csv: Path | None = DEFAULT_DIVIDEND_CASH_CSV,
    *,
    benchmark_id: str = DEFAULT_BENCHMARK_ID,
    start_date: str = DEFAULT_BACKTEST_START,
    end_date: str = DEFAULT_BACKTEST_END,
    initial_cash: float = 2_000_000.0,
    target_exposure: float = 0.995,
    lot_size: int = 100,
    open_commission: float = 0.0003,
    close_commission: float = 0.0003,
    min_commission: float = 5.0,
) -> Path:
    pre_run_git = capture_git_state()
    spec = load_spec(spec_path)
    options = BacktestOptions(
        execution_mode="joinquant_like",
        start_date=start_date,
        end_date=end_date,
        initial_cash=initial_cash,
        target_exposure=target_exposure,
        lot_size=lot_size,
        open_commission=open_commission,
        close_commission=close_commission,
        min_commission=min_commission,
    )
    guard_config = _extract_guard_config(spec.raw)
    base_signals, base_signal_rows = _build_rebalance_signals(
        panel_csv,
        spec.raw,
        options,
        signal_dividend_yield_mode="panel",
        execution_price_csv=execution_price_csv,
        dividend_cash_csv=dividend_cash_csv,
    )
    panel_by_date = _load_panel_by_date(panel_csv, start_date, end_date)
    coverage_audit_rows = _build_rebalance_coverage_audit(panel_by_date, spec.raw, options)
    guarded_signals, guard_decisions = apply_state_guard_to_signals(
        base_signals,
        panel_by_date,
        guard_field=guard_config["field"],
        guard_quantile=guard_config["quantile"],
        min_history=guard_config["min_history"],
    )
    signal_rows = _merge_signal_guard_rows(base_signal_rows, guard_decisions)

    prices_by_date = _load_execution_prices(execution_price_csv, start_date, end_date)
    benchmarks = _load_benchmark_closes(benchmark_csv, benchmark_id, start_date, end_date)
    cash_dividends = _load_cash_dividends(dividend_cash_csv, start_date, end_date)

    out = out_dir / spec.strategy_id
    out.mkdir(parents=True, exist_ok=True)
    daily_rows, holding_rows, trade_rows, dividend_rows = _simulate_daily(
        prices_by_date,
        benchmarks,
        cash_dividends,
        guarded_signals,
        spec.raw,
        options,
    )
    for row in daily_rows:
        row["experiment_layer"] = "engineering_smoke_test"
        row["benchmark_source"] = benchmark_id

    order_health_rows, raw_order_health_summary = build_rebalance_order_health(guarded_signals, daily_rows, trade_rows, holding_rows)
    order_health_rows, order_health_summary = _annotate_guard_order_health(order_health_rows, guard_decisions, raw_order_health_summary)
    metrics = _compute_metrics(daily_rows)
    summary = _build_summary(
        spec.raw,
        panel_csv,
        execution_price_csv,
        benchmark_csv,
        dividend_cash_csv,
        benchmark_id,
        options,
        guard_config,
        guard_decisions,
        coverage_audit_rows,
        order_health_summary,
        metrics,
        len(daily_rows),
    )

    write_json_file(out / "summary.json", summary)
    write_csv_rows(out / "daily_returns.csv", list(daily_rows[0].keys()) if daily_rows else [], daily_rows)
    write_csv_rows(out / "holdings.csv", list(holding_rows[0].keys()) if holding_rows else [], holding_rows)
    write_csv_rows(out / "trades.csv", list(trade_rows[0].keys()) if trade_rows else [], trade_rows)
    write_csv_rows(out / "dividends.csv", list(dividend_rows[0].keys()) if dividend_rows else [], dividend_rows)
    write_csv_rows(out / "rebalance_signals.csv", list(signal_rows[0].keys()) if signal_rows else [], signal_rows)
    write_csv_rows(out / "rebalance_coverage_audit.csv", list(coverage_audit_rows[0].keys()) if coverage_audit_rows else [], coverage_audit_rows)
    write_csv_rows(out / "guard_decisions.csv", GUARD_DECISION_FIELDS, guard_decisions)
    write_csv_rows(out / "rebalance_order_health.csv", list(order_health_rows[0].keys()) if order_health_rows else [], order_health_rows)
    _write_report(out / "engineering_local_daily_simulation_report.md", summary)
    manifest = build_run_manifest(
        strategy_id=spec.strategy_id,
        experiment_layer="engineering_smoke_test",
        command_profile={
            "runner": "gas_water_state_guard_daily_backtest_runner",
            "spec": str(spec_path),
            "panel": str(panel_csv),
            "execution_price_csv": str(execution_price_csv),
            "benchmark_csv": str(benchmark_csv),
            "benchmark_id": benchmark_id,
            "dividend_cash_csv": str(dividend_cash_csv) if dividend_cash_csv else None,
            "start_date": start_date,
            "end_date": end_date,
            "initial_cash": initial_cash,
            "target_exposure": target_exposure,
            "lot_size": lot_size,
        },
        outputs=summary["outputs"] | {"run_manifest": "RUN_MANIFEST.json"},
        warnings=[],
        pre_run_git=pre_run_git,
    )
    write_run_manifest(out / "RUN_MANIFEST.json", manifest)
    return out / "summary.json"


def apply_state_guard_to_signals(
    base_signals: dict[str, list[str]],
    panel_by_date: dict[str, list[dict[str, Any]]],
    *,
    guard_field: str,
    guard_quantile: float,
    min_history: int,
) -> tuple[dict[str, list[str]], list[dict[str, Any]]]:
    guarded: dict[str, list[str]] = {}
    decisions: list[dict[str, Any]] = []
    history: list[float] = []
    for trade_date in sorted(base_signals):
        date_rows = panel_by_date.get(trade_date, [])
        guard_value = _state_value(date_rows, guard_field)
        threshold = _quantile(history, guard_quantile) if len(history) >= min_history else None
        blocked = bool(threshold is not None and guard_value is not None and guard_value > threshold)
        base_codes = list(base_signals[trade_date])
        guarded_codes: list[str] = [] if blocked else base_codes
        guarded[trade_date] = guarded_codes
        decisions.append(
            {
                "trade_date": trade_date,
                "guard_field": guard_field,
                "guard_value": "" if guard_value is None else guard_value,
                "expanding_threshold": "" if threshold is None else threshold,
                "guard_quantile": guard_quantile,
                "min_history": min_history,
                "history_count_before_decision": len(history),
                "blocked": int(blocked),
                "base_selected_count": len(base_codes),
                "guarded_selected_count": len(guarded_codes),
                "base_selected_codes": ";".join(base_codes),
                "guarded_selected_codes": ";".join(guarded_codes),
                "decision_source": "expanding_prior_rebalance_history_only",
            }
        )
        if guard_value is not None:
            history.append(guard_value)
    return guarded, decisions


def _extract_guard_config(raw_spec: dict[str, Any]) -> dict[str, Any]:
    rule = raw_spec.get("risk", {}).get("defensive_rule", {})
    if not rule.get("enabled") or rule.get("type") != "state_guard_cash_block":
        raise ValueError("V59b daily runner requires risk.defensive_rule.type=state_guard_cash_block")
    field = str(rule.get("field") or "")
    if not field:
        raise ValueError("state guard field is required")
    return {
        "field": field,
        "quantile": float(rule.get("quantile", 0.75)),
        "min_history": int(rule.get("min_history", 8)),
        "action": str(rule.get("action") or "block_new_equity_exposure_hold_cash"),
    }


def _load_panel_by_date(path: Path, start_date: str, end_date: str) -> dict[str, list[dict[str, Any]]]:
    start = start_date[:10]
    end = end_date[:10]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_csv_rows(path):
        day = str(row.get("trade_date") or "")[:10]
        if start <= day <= end and row.get("code"):
            grouped[day].append(row)
    return dict(grouped)


def _build_rebalance_coverage_audit(
    panel_by_date: dict[str, list[dict[str, Any]]],
    raw_spec: dict[str, Any],
    options: BacktestOptions,
) -> list[dict[str, Any]]:
    max_date_coverage = max((len(rows) for rows in panel_by_date.values()), default=0)
    min_required = int(max_date_coverage * options.min_coverage_ratio)
    if max_date_coverage and min_required < max_date_coverage * options.min_coverage_ratio:
        min_required += 1
    rebalance_months = set(raw_spec.get("schedule", {}).get("rebalance_months", [1, 4, 7, 10]))
    seen_keys: set[str] = set()
    rows: list[dict[str, Any]] = []
    for trade_date, date_rows in sorted(panel_by_date.items()):
        day_key = trade_date[:7]
        month = int(trade_date[5:7])
        if month not in rebalance_months or day_key in seen_keys:
            continue
        seen_keys.add(day_key)
        security_count = len(date_rows)
        rows.append(
            {
                "trade_date": trade_date,
                "security_count": security_count,
                "max_date_coverage": max_date_coverage,
                "min_coverage_ratio": options.min_coverage_ratio,
                "required_security_count": min_required,
                "coverage_passed": int(security_count >= min_required),
                "reason": "" if security_count >= min_required else "coverage_below_frozen_threshold",
            }
        )
    return rows


def _state_value(date_rows: list[dict[str, Any]], field: str) -> float | None:
    values = [to_float(row.get(field)) for row in date_rows]
    values = [value for value in values if value is not None]
    return mean(values) if values else None


def _merge_signal_guard_rows(signal_rows: list[dict[str, Any]], guard_decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_date = {row["trade_date"]: row for row in guard_decisions}
    merged: list[dict[str, Any]] = []
    for row in signal_rows:
        decision = by_date.get(str(row.get("trade_date") or "")[:10], {})
        item = copy.deepcopy(row)
        item["state_guard_blocked"] = decision.get("blocked", "")
        item["state_guard_field"] = decision.get("guard_field", "")
        item["state_guard_value"] = decision.get("guard_value", "")
        item["state_guard_threshold"] = decision.get("expanding_threshold", "")
        item["base_selected_codes"] = decision.get("base_selected_codes", "")
        item["selected_count"] = decision.get("guarded_selected_count", item.get("selected_count", ""))
        item["selected_codes"] = decision.get("guarded_selected_codes", item.get("selected_codes", ""))
        merged.append(item)
    return merged


def _annotate_guard_order_health(
    order_health_rows: list[dict[str, Any]],
    guard_decisions: list[dict[str, Any]],
    raw_summary: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    decisions = {row["trade_date"]: row for row in guard_decisions}
    rows: list[dict[str, Any]] = []
    intentional_guard_count = 0
    unexpected_needs_review = 0
    for row in order_health_rows:
        item = dict(row)
        decision = decisions.get(str(row.get("trade_date") or "")[:10], {})
        blocked = int(decision.get("blocked") or 0) == 1
        item["state_guard_blocked"] = int(blocked)
        item["base_selected_count"] = decision.get("base_selected_count", "")
        item["guard_decision_source"] = decision.get("decision_source", "")
        original_status = str(item.get("order_health_status") or "")
        item["raw_order_health_status"] = original_status
        if blocked:
            intentional_guard_count += 1
            if int(item.get("executed_order_count") or 0) > 0:
                item["order_health_status"] = "intentional_guard_cash_block_sell_executed"
                item["diagnosis"] = "State guard intentionally blocked equity exposure and local simulation executed cash transition trades."
            else:
                item["order_health_status"] = "intentional_guard_cash_block_no_order_needed"
                item["diagnosis"] = "State guard intentionally blocked equity exposure; no order was needed because the portfolio was already cash or unchanged."
        elif original_status in {"missing_daily_row", "no_order_no_position", "order_blocked_or_unfilled", "ordered_but_no_position", "no_selected_stocks"}:
            unexpected_needs_review += 1
        rows.append(item)

    summary = dict(raw_summary)
    summary["intentional_guard_cash_block_count"] = intentional_guard_count
    summary["unexpected_rebalance_issue_count"] = unexpected_needs_review
    summary["needs_review"] = unexpected_needs_review > 0 or int(summary.get("missing_daily_rebalance_count") or 0) > 0
    summary["pm_rule"] = (
        "Guard-blocked empty selections are intentional cash defense. Non-guard missing orders, blocked orders, or no-position rebalance dates still require review."
    )
    return rows, summary


def _build_summary(
    raw_spec: dict[str, Any],
    panel_csv: Path,
    execution_price_csv: Path,
    benchmark_csv: Path,
    dividend_cash_csv: Path | None,
    benchmark_id: str,
    options: BacktestOptions,
    guard_config: dict[str, Any],
    guard_decisions: list[dict[str, Any]],
    coverage_audit_rows: list[dict[str, Any]],
    order_health_summary: dict[str, Any],
    metrics: dict[str, Any],
    daily_count: int,
) -> dict[str, Any]:
    blocked_dates = [row["trade_date"] for row in guard_decisions if int(row.get("blocked") or 0) == 1]
    missing_signal_dates = [row["trade_date"] for row in coverage_audit_rows if int(row.get("coverage_passed") or 0) == 0]
    has_coverage_gap = bool(missing_signal_dates)
    status = (
        "engineering_local_daily_simulation_passed_ready_for_platform_preparation"
        if not order_health_summary.get("needs_review") and not has_coverage_gap
        else "engineering_local_daily_simulation_needs_review"
    )
    return {
        "strategy_id": raw_spec["meta"]["strategy_id"],
        "mode": "daily_joinquant_like_with_state_guard",
        "experiment_layer": "engineering_smoke_test",
        "status": status,
        "pm_decision": (
            "Local daily engineering simulation passed. Do not enter JoinQuant replication until PM explicitly opens the platform gate."
            if status.endswith("platform_preparation")
            else "Local daily engineering simulation needs review before any platform work."
        ),
        "panel": str(panel_csv),
        "price_source": str(execution_price_csv),
        "benchmark_csv": str(benchmark_csv),
        "benchmark_id": benchmark_id,
        "dividend_cash_csv": str(dividend_cash_csv) if dividend_cash_csv else None,
        "window": {"start_date": options.start_date, "end_date": options.end_date},
        "execution": {
            "initial_cash": options.initial_cash,
            "target_exposure": options.target_exposure,
            "lot_size": options.lot_size,
            "open_commission": options.open_commission,
            "close_commission": options.close_commission,
            "min_commission": options.min_commission,
            "trade_price": "daily_open",
            "valuation_price": "daily_close",
            "cash_dividend_policy": "Use net_cash_per_share on pay_date. Current gas/water dividend file is already 20% tax-adjusted.",
            "state_guard_policy": "If blocked, set current rebalance target to cash via empty selected list.",
        },
        "state_guard": {
            **guard_config,
            "history_policy": "expanding prior rebalance dates only",
            "blocked_count": len(blocked_dates),
            "blocked_dates": blocked_dates,
        },
        "rebalance_coverage_audit": {
            "expected_rebalance_count": len(coverage_audit_rows),
            "executed_signal_count": len(guard_decisions),
            "coverage_skipped_count": len(missing_signal_dates),
            "coverage_skipped_dates": missing_signal_dates,
            "policy": "Frozen minimum_rebalance_coverage_ratio is enforced before signal generation.",
            "needs_review": has_coverage_gap,
        },
        "signal_count": len(guard_decisions),
        "daily_count": daily_count,
        "rebalance_order_health": order_health_summary,
        "metrics": metrics,
        "outputs": {
            "summary": "summary.json",
            "daily_returns": "daily_returns.csv",
            "holdings": "holdings.csv",
            "trades": "trades.csv",
            "dividends": "dividends.csv",
            "rebalance_signals": "rebalance_signals.csv",
            "rebalance_coverage_audit": "rebalance_coverage_audit.csv",
            "guard_decisions": "guard_decisions.csv",
            "rebalance_order_health": "rebalance_order_health.csv",
            "engineering_report": "engineering_local_daily_simulation_report.md",
        },
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    metrics = summary["metrics"]
    health = summary["rebalance_order_health"]
    guard = summary["state_guard"]
    coverage = summary["rebalance_coverage_audit"]
    lines = [
        f"# {summary['strategy_id']} Local Daily Simulation",
        "",
        f"- Status: `{summary['status']}`",
        f"- Window: {summary['window']['start_date']} to {summary['window']['end_date']}",
        f"- Strategy return: {_fmt_pct(metrics.get('strategy_return'))}",
        f"- Benchmark return: {_fmt_pct(metrics.get('benchmark_return'))}",
        f"- Excess return: {_fmt_pct(metrics.get('excess_return'))}",
        f"- Max drawdown: {_fmt_pct(metrics.get('max_drawdown'))}",
        f"- Guard blocked dates: {guard['blocked_count']} ({', '.join(guard['blocked_dates'])})",
        f"- Coverage skipped dates: {coverage['coverage_skipped_count']} ({', '.join(coverage['coverage_skipped_dates'])})",
        f"- Rebalance signals: {health.get('rebalance_signal_count')}",
        f"- Intentional guard cash blocks: {health.get('intentional_guard_cash_block_count')}",
        f"- Unexpected rebalance issues: {health.get('unexpected_rebalance_issue_count')}",
        "",
        "Engineering boundary: this packet only checks local daily execution, real cash dividends, trade/cash/holding logs, and rebalance order health. It does not tune parameters and does not start JoinQuant replication.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fmt_pct(value: Any) -> str:
    parsed = to_float(value)
    return "" if parsed is None else f"{parsed:.2%}"

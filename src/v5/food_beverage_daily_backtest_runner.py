from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.daily_backtest import run_daily_joinquant_like_backtest
from v5.io_utils import read_csv_rows_if_exists, write_csv_rows, write_json_file
from v5.local_backtest import BacktestOptions
from v5.paths import DEFAULT_PROCESSED_DIR


DEFAULT_STRATEGY_ID = "food_beverage_packaged_food_ocf_quality_v5a9a"
DEFAULT_SPEC = Path("validation_formal_v5a9_food_beverage_research_repair") / "specs" / f"{DEFAULT_STRATEGY_ID}.json"
DEFAULT_PANEL = Path("validation_formal_v5a9_food_beverage_research_repair") / "panels" / f"{DEFAULT_STRATEGY_ID}.csv"
DEFAULT_RESEARCH_GATE = Path("validation_formal_v5a9_food_beverage_research_repair") / "food_beverage_research_repair_summary.json"
DEFAULT_EXECUTION_PRICE_CSV = DEFAULT_PROCESSED_DIR / "food_beverage_v5a5_joinquant_real_daily_prices.csv"
DEFAULT_DIVIDEND_CASH_CSV = DEFAULT_PROCESSED_DIR / "food_beverage_v5a5_joinquant_cash_dividends.csv"
DEFAULT_BENCHMARK_CSV = DEFAULT_PROCESSED_DIR / "food_beverage_v5a5_joinquant_real_benchmark_prices.csv"
DEFAULT_BENCHMARK_ID = "000300.XSHG"
DEFAULT_OUT_DIR = Path("local_daily_backtests_food_beverage_v5a9")


@dataclass(frozen=True)
class FoodBeverageDailyBacktestResult:
    summary_path: Path
    status: str
    next_gate: str


def run_food_beverage_daily_backtest(
    *,
    spec_path: Path = DEFAULT_SPEC,
    panel_csv: Path = DEFAULT_PANEL,
    research_gate_summary: Path = DEFAULT_RESEARCH_GATE,
    execution_price_csv: Path = DEFAULT_EXECUTION_PRICE_CSV,
    dividend_cash_csv: Path = DEFAULT_DIVIDEND_CASH_CSV,
    benchmark_csv: Path = DEFAULT_BENCHMARK_CSV,
    out_dir: Path = DEFAULT_OUT_DIR,
    benchmark_id: str = DEFAULT_BENCHMARK_ID,
    start_date: str = "2021-05-01",
    end_date: str = "2026-05-31",
    initial_cash: float = 2_000_000.0,
    target_exposure: float = 0.995,
    lot_size: int = 100,
    open_commission: float = 0.0003,
    close_commission: float = 0.0003,
    min_commission: float = 5.0,
    min_coverage_ratio: float = 0.0,
) -> FoodBeverageDailyBacktestResult:
    gate = _read_research_gate(research_gate_summary)
    _assert_gate_open(gate)
    readiness = _readiness(panel_csv, execution_price_csv, dividend_cash_csv, benchmark_csv, start_date, end_date)
    if readiness["status"] != "ready":
        raise RuntimeError("food/beverage daily backtest is not ready: " + ";".join(readiness["blockers"]))

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
        min_coverage_ratio=min_coverage_ratio,
        value_trap_guard_mode="disabled",
    )
    summary_path = run_daily_joinquant_like_backtest(
        spec_path,
        panel_csv,
        v4_raw_dir=Path("."),
        benchmark_csv=benchmark_csv,
        out_dir=out_dir,
        options=options,
        benchmark_id=benchmark_id,
        execution_price_csv=execution_price_csv,
        dividend_cash_csv=dividend_cash_csv,
        experiment_layer="engineering_smoke_test",
    )
    _ensure_dividend_output(summary_path.parent / "dividends.csv")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    signal_rows = read_csv_rows_if_exists(summary_path.parent / "rebalance_signals.csv")
    order_health_rows = read_csv_rows_if_exists(summary_path.parent / "rebalance_order_health.csv")
    signal_coverage = _signal_coverage(panel_csv, signal_rows, start_date, end_date)
    startup_gap = _startup_gap(start_date, signal_coverage)
    partial_skipped = _partial_skipped_orders(order_health_rows)
    order = payload.get("rebalance_order_health", {})
    raw_needs_review = bool(order.get("needs_review"))
    order.update(partial_skipped)
    order["raw_needs_review_before_partial_skipped_policy"] = raw_needs_review
    order["needs_review"] = raw_needs_review or partial_skipped["partial_skipped_order_rebalance_count"] > 0
    unexpected = int(order.get("unexpected_rebalance_issue_count") or 0) if "unexpected_rebalance_issue_count" in order else _legacy_unexpected(order)
    status = (
        "engineering_local_daily_simulation_passed"
        if not order.get("needs_review") and unexpected == 0 and signal_coverage["missing_signal_count"] == 0 and partial_skipped["partial_skipped_order_rebalance_count"] == 0
        else "engineering_local_daily_simulation_needs_review"
    )
    next_gate = (
        "pm_review_for_observation_sleeve_or_paper_tracking"
        if status.endswith("passed")
        else "repair_signal_coverage_or_rebalance_order_health_before_any_promotion"
    )
    payload["mode"] = "food_beverage_daily_joinquant_like_no_tuning"
    payload["research_gate_summary"] = str(research_gate_summary)
    payload["readiness"] = readiness
    payload["signal_coverage"] = signal_coverage
    payload["startup_signal_gap"] = startup_gap
    payload["engineering_gate"] = status
    payload["next_gate"] = next_gate
    payload["pm_rules"] = [
        "This is a local Engineering smoke test, not JoinQuant platform replication.",
        "Only food_beverage_packaged_food_ocf_quality_v5a9a is allowed into this runner.",
        "Do not tune factor weights, selection count, timing or packaged-food subindustry membership.",
        "No V57f inclusion can be made from this run.",
        "2021-2026 remains a platform-confirmation and engineering window, not clean out-of-sample acceptance evidence.",
        "If a rebalance signal exists but no order or no holding appears, stop before any platform replication.",
        "Partial skipped orders from price-limit, suspension or lot/cash constraints must be explained before any promotion.",
    ]
    payload["created_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    write_json_file(summary_path, payload)
    _write_report(summary_path.parent / "engineering_local_daily_simulation_report.md", payload)
    return FoodBeverageDailyBacktestResult(summary_path, status, next_gate)


def _read_research_gate(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"research gate summary not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _assert_gate_open(payload: dict[str, Any]) -> None:
    if payload.get("status") != "food_beverage_engineering_handoff_ready":
        raise RuntimeError("food/beverage Research gate is not open for Engineering")
    allowed = [
        row
        for row in payload.get("candidate_results", [])
        if row.get("strategy_id") == DEFAULT_STRATEGY_ID and row.get("pm_decision") == "can_start_engineering_local_daily_only"
    ]
    if not allowed:
        raise RuntimeError(f"{DEFAULT_STRATEGY_ID} is not approved for Engineering local daily simulation")


def _readiness(
    panel_csv: Path,
    execution_price_csv: Path,
    dividend_cash_csv: Path,
    benchmark_csv: Path,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    panel_rows = read_csv_rows_if_exists(panel_csv)
    price_rows = read_csv_rows_if_exists(execution_price_csv)
    dividend_rows = read_csv_rows_if_exists(dividend_cash_csv)
    benchmark_rows = read_csv_rows_if_exists(benchmark_csv)
    blockers = []
    if not panel_csv.exists():
        blockers.append("panel_missing")
    if not execution_price_csv.exists():
        blockers.append("execution_price_missing")
    if not dividend_cash_csv.exists():
        blockers.append("dividend_cash_missing")
    if not benchmark_csv.exists():
        blockers.append("benchmark_missing")
    panel_dates = _dates(panel_rows, "trade_date", start_date, end_date)
    price_dates = _dates(price_rows, "date", start_date, end_date)
    benchmark_dates = _dates(benchmark_rows, "date", start_date, end_date)
    if panel_csv.exists() and not panel_dates:
        blockers.append("panel_has_no_window_rows")
    if execution_price_csv.exists() and not price_dates:
        blockers.append("execution_price_has_no_window_rows")
    if benchmark_csv.exists() and not benchmark_dates:
        blockers.append("benchmark_has_no_window_rows")
    return {
        "status": "ready" if not blockers else "blocked",
        "blockers": blockers,
        "window": {"start_date": start_date, "end_date": end_date},
        "panel_rebalance_dates": len(panel_dates),
        "execution_price_dates": len(price_dates),
        "dividend_event_count": len(dividend_rows),
        "benchmark_dates": len(benchmark_dates),
        "first_panel_trade_date": panel_dates[0] if panel_dates else "",
        "latest_panel_trade_date": panel_dates[-1] if panel_dates else "",
        "first_price_date": price_dates[0] if price_dates else "",
        "latest_price_date": price_dates[-1] if price_dates else "",
        "latest_benchmark_date": benchmark_dates[-1] if benchmark_dates else "",
    }


def _dates(rows: list[dict[str, str]], field: str, start_date: str, end_date: str) -> list[str]:
    return sorted({str(row.get(field) or "")[:10] for row in rows if start_date <= str(row.get(field) or "")[:10] <= end_date})


def _signal_coverage(panel_csv: Path, signal_rows: list[dict[str, str]], start_date: str, end_date: str) -> dict[str, Any]:
    expected = _dates(read_csv_rows_if_exists(panel_csv), "trade_date", start_date, end_date)
    actual = _dates(signal_rows, "trade_date", start_date, end_date)
    missing = [day for day in expected if day not in actual]
    extra = [day for day in actual if day not in expected]
    return {
        "expected_rebalance_count": len(expected),
        "actual_signal_count": len(actual),
        "missing_signal_count": len(missing),
        "extra_signal_count": len(extra),
        "expected_rebalance_dates": expected,
        "actual_signal_dates": actual,
        "missing_signal_dates": missing,
        "extra_signal_dates": extra,
        "status": "passed" if not missing else "missing_rebalance_signals",
    }


def _startup_gap(start_date: str, signal_coverage: dict[str, Any]) -> dict[str, Any]:
    first_signal = ""
    actual = signal_coverage.get("actual_signal_dates", [])
    if actual:
        first_signal = str(actual[0])
    return {
        "requested_start_date": start_date,
        "first_signal_date": first_signal,
        "has_startup_gap": bool(first_signal and first_signal > start_date[:10]),
        "classification": "panel_has_no_pit_rebalance_rows_before_first_signal" if first_signal and first_signal > start_date[:10] else "no_startup_gap",
        "pm_note": (
            "A startup gap before the first PIT panel rebalance date is a Research data-window limitation, not an order-health failure. "
            "If PM requires 2021 exposure, return to Research to repair PIT coverage rather than changing Engineering execution."
        ),
    }


def _legacy_unexpected(order: dict[str, Any]) -> int:
    return int(order.get("blocked_or_unfilled_rebalance_count") or 0) + int(order.get("no_order_no_position_count") or 0)


def _ensure_dividend_output(path: Path) -> None:
    if not path.exists():
        write_csv_rows(path, ["trade_date", "code", "amount", "net_cash_per_share", "dividend_cash"], [])


def _partial_skipped_orders(order_health_rows: list[dict[str, str]]) -> dict[str, Any]:
    affected = []
    skipped_total = 0
    for row in order_health_rows:
        skipped = _int(row.get("skipped_order_count"))
        if skipped > 0:
            affected.append(str(row.get("trade_date") or "")[:10])
            skipped_total += skipped
    return {
        "partial_skipped_order_rebalance_count": len(affected),
        "partial_skipped_order_count": skipped_total,
        "partial_skipped_order_dates": affected,
        "partial_skipped_order_policy": (
            "Any partially skipped rebalance is treated as Engineering needs_review. "
            "This is usually a tradability or lot/cash constraint, not factor tuning evidence."
        ),
    }


def _int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    metrics = payload.get("metrics", {})
    order = payload.get("rebalance_order_health", {})
    startup = payload.get("startup_signal_gap", {})
    lines = [
        "# V5a.9 Food/Beverage Local Daily Engineering Simulation",
        "",
        "## Decision",
        "",
        f"Engineering gate: `{payload.get('engineering_gate')}`",
        "",
        f"Next gate: `{payload.get('next_gate')}`",
        "",
        "This is a local daily Engineering smoke test only. It does not promote the strategy into V57f, platform replication, or accepted strategy status.",
        "",
        "## Execution Health",
        "",
        f"- Rebalance signals: {order.get('rebalance_signal_count')}",
        f"- Normal rebalance count: {order.get('normal_rebalance_count')}",
        f"- Needs review: {order.get('needs_review')}",
        f"- First executed order date: {order.get('first_executed_order_date')}",
        f"- First position date: {order.get('first_position_date')}",
        f"- Partial skipped-order rebalance count: {order.get('partial_skipped_order_rebalance_count')}",
        f"- Partial skipped-order dates: {', '.join(order.get('partial_skipped_order_dates') or [])}",
        f"- Startup gap classification: `{startup.get('classification')}`",
        "",
        "## Local Metrics",
        "",
        f"- Strategy return: {_pct(metrics.get('strategy_return'))}",
        f"- Benchmark return: {_pct(metrics.get('benchmark_return'))}",
        f"- Excess return: {_pct(metrics.get('excess_return'))}",
        f"- Max drawdown: {_pct(metrics.get('max_drawdown'))}",
        f"- Sharpe: {_num(metrics.get('sharpe'))}",
        "",
        "## PM Rules",
        "",
    ]
    lines.extend(f"- {rule}" for rule in payload.get("pm_rules", []))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return ""


def _num(value: Any) -> str:
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return ""

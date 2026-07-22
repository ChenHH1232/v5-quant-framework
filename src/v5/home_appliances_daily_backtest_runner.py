from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.daily_backtest import run_daily_joinquant_like_backtest
from v5.io_utils import read_csv_rows_if_exists, write_json_file
from v5.local_backtest import BacktestOptions
from v5.paths import DEFAULT_PROCESSED_DIR


DEFAULT_SPEC = Path("examples") / "home_appliances_ocf_quality_v5a5c_strategy.json"
DEFAULT_PANEL = DEFAULT_PROCESSED_DIR / "home_appliances_state_gate_v5a5d" / "panel_with_home_appliances_state_gate.csv"
DEFAULT_EXECUTION_PRICE_CSV = DEFAULT_PROCESSED_DIR / "home_appliances_v5a5_joinquant_real_daily_prices.csv"
DEFAULT_DIVIDEND_CASH_CSV = DEFAULT_PROCESSED_DIR / "home_appliances_v5a5_joinquant_cash_dividends.csv"
DEFAULT_BENCHMARK_CSV = DEFAULT_PROCESSED_DIR / "home_appliances_v5a5_joinquant_real_benchmark_prices.csv"
DEFAULT_ENGINEERING_GATE = (
    Path("home_appliances_engineering_gates_v5a5e")
    / "home_appliances_ocf_quality_v5a5c"
    / "home_appliances_engineering_gate_summary.json"
)
DEFAULT_OUT_DIR = Path("local_daily_backtests_home_appliances_v5a5e")
DEFAULT_BENCHMARK_ID = "000300.XSHG"


@dataclass(frozen=True)
class HomeAppliancesDailyBacktestResult:
    summary_path: Path
    status: str
    next_gate: str


def run_home_appliances_daily_backtest(
    *,
    spec_path: Path = DEFAULT_SPEC,
    panel_csv: Path = DEFAULT_PANEL,
    execution_price_csv: Path = DEFAULT_EXECUTION_PRICE_CSV,
    dividend_cash_csv: Path = DEFAULT_DIVIDEND_CASH_CSV,
    benchmark_csv: Path = DEFAULT_BENCHMARK_CSV,
    engineering_gate_summary: Path = DEFAULT_ENGINEERING_GATE,
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
) -> HomeAppliancesDailyBacktestResult:
    gate = _read_json(engineering_gate_summary)
    if gate.get("status") != "engineering_handoff_ready_local_daily_only":
        raise RuntimeError("home appliances Engineering gate is not open")
    readiness = _readiness(panel_csv, execution_price_csv, dividend_cash_csv, benchmark_csv, start_date, end_date)
    if readiness["status"] != "ready":
        raise RuntimeError("home appliances daily backtest is not ready: " + ";".join(readiness["blockers"]))

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
    payload = _read_json(summary_path)
    signal_rows = read_csv_rows_if_exists(summary_path.parent / "rebalance_signals.csv")
    signal_coverage = _signal_coverage(panel_csv, signal_rows, start_date, end_date)
    order = payload.get("rebalance_order_health", {})
    unexpected = int(order.get("unexpected_rebalance_issue_count") or 0) if "unexpected_rebalance_issue_count" in order else _legacy_unexpected(order)
    missing_signal_count = int(signal_coverage["missing_signal_count"])
    status = (
        "engineering_local_daily_simulation_passed"
        if not order.get("needs_review") and unexpected == 0 and missing_signal_count == 0
        else "engineering_local_daily_simulation_needs_review"
    )
    next_gate = (
        "pm_review_for_observation_sleeve_or_paper_tracking"
        if status.endswith("passed")
        else "repair_signal_coverage_or_rebalance_order_health_before_any_promotion"
    )
    payload["mode"] = "home_appliances_daily_joinquant_like_no_state_policy"
    payload["engineering_gate_summary"] = str(engineering_gate_summary)
    payload["readiness"] = readiness
    payload["signal_coverage"] = signal_coverage
    payload["state_policy"] = gate.get("state_policy", {})
    payload["signal_coverage_policy"] = {
        "min_coverage_ratio": min_coverage_ratio,
        "reason": (
            "Home appliances uses formal-validation rebalance dates for local Engineering. "
            "The generic global-max 80% coverage filter incorrectly drops 2021 startup PIT universes "
            "because later listed securities raise the maximum cross-section."
        ),
        "minimum_requirement": "rebalance date must have enough PIT-visible scored candidates to fill the frozen selection_count",
    }
    payload["engineering_gate"] = status
    payload["next_gate"] = next_gate
    payload["pm_rules"] = [
        "This is a local Engineering smoke test, not platform replication.",
        "The frozen scoring uses OCF yield and OCF-to-net-profit only.",
        "External macro state fields are diagnostic only and are not used as score, guard, timing or tuning variables.",
        "Every formal rebalance date must generate a local signal or receive an explicit coverage blocker.",
        "Do not add home appliances to V57f from this run.",
        "Do not accept the strategy based on 2021-2026 performance.",
    ]
    payload["created_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    write_json_file(summary_path, payload)
    return HomeAppliancesDailyBacktestResult(summary_path, status, next_gate)


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
        "latest_panel_trade_date": panel_dates[-1] if panel_dates else "",
        "latest_price_date": price_dates[-1] if price_dates else "",
        "latest_benchmark_date": benchmark_dates[-1] if benchmark_dates else "",
    }


def _dates(rows: list[dict[str, str]], field: str, start_date: str, end_date: str) -> list[str]:
    return sorted({str(row.get(field) or "")[:10] for row in rows if start_date <= str(row.get(field) or "")[:10] <= end_date})


def _signal_coverage(panel_csv: Path, signal_rows: list[dict[str, str]], start_date: str, end_date: str) -> dict[str, Any]:
    panel_rows = read_csv_rows_if_exists(panel_csv)
    panel_dates = _dates(panel_rows, "trade_date", start_date, end_date)
    expected = []
    seen_keys = set()
    for day in panel_dates:
        month = day[5:7]
        if month not in {"01", "04", "07", "10"}:
            continue
        key = day[:7]
        if key in seen_keys:
            continue
        expected.append(day)
        seen_keys.add(key)
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


def _legacy_unexpected(order: dict[str, Any]) -> int:
    return int(order.get("blocked_or_unfilled_rebalance_count") or 0) + int(order.get("no_order_no_position_count") or 0)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload

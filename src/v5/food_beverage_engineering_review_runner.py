from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.food_beverage_daily_backtest_runner import (
    DEFAULT_DIVIDEND_CASH_CSV,
    DEFAULT_EXECUTION_PRICE_CSV,
    DEFAULT_OUT_DIR as DEFAULT_FOOD_BEVERAGE_DAILY_OUT,
    DEFAULT_STRATEGY_ID,
)
from v5.io_utils import read_csv_rows_if_exists, write_csv_rows, write_json_file


DEFAULT_LOCAL_DAILY_DIR = DEFAULT_FOOD_BEVERAGE_DAILY_OUT / DEFAULT_STRATEGY_ID
DEFAULT_OUT_DIR = Path("food_beverage_engineering_reviews_v5") / "current"


@dataclass(frozen=True)
class FoodBeverageEngineeringReviewResult:
    summary_json: Path
    report_md: Path
    status: str
    next_gate: str


def run_food_beverage_engineering_review(
    *,
    local_daily_dir: Path = DEFAULT_LOCAL_DAILY_DIR,
    price_csv: Path = DEFAULT_EXECUTION_PRICE_CSV,
    dividend_cash_csv: Path = DEFAULT_DIVIDEND_CASH_CSV,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> FoodBeverageEngineeringReviewResult:
    summary_path = local_daily_dir / "summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"food/beverage local daily summary not found: {summary_path}")

    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    order_health_rows = read_csv_rows_if_exists(local_daily_dir / "rebalance_order_health.csv")
    trade_rows = read_csv_rows_if_exists(local_daily_dir / "trades.csv")
    signal_rows = read_csv_rows_if_exists(local_daily_dir / "rebalance_signals.csv")
    holding_rows = read_csv_rows_if_exists(local_daily_dir / "holdings.csv")
    output_dividend_rows = read_csv_rows_if_exists(local_daily_dir / "dividends.csv")
    source_dividend_rows = read_csv_rows_if_exists(dividend_cash_csv)

    skipped_rows, partial_fill_rows = _diagnose_trade_execution(trade_rows, holding_rows, price_csv)
    startup_gap = _diagnose_startup_gap(summary, signal_rows)
    dividend_gap = _diagnose_dividend_gap(dividend_cash_csv, source_dividend_rows, output_dividend_rows)
    order_health = _diagnose_order_health(summary, order_health_rows, skipped_rows, partial_fill_rows)
    flow_rows = _flow_rows()
    decision = _pm_decision(order_health, dividend_gap, startup_gap)

    out_dir.mkdir(parents=True, exist_ok=True)
    flow_path = out_dir / "food_beverage_engineering_review_flow_table.csv"
    skip_path = out_dir / "food_beverage_order_skip_diagnosis.csv"
    partial_path = out_dir / "food_beverage_partial_fill_diagnosis.csv"
    dividend_path = out_dir / "food_beverage_dividend_gap_diagnosis.csv"
    startup_path = out_dir / "food_beverage_startup_gap_diagnosis.csv"
    queue_path = out_dir / "food_beverage_next_agent_queue.csv"
    summary_out = out_dir / "food_beverage_engineering_review_summary.json"
    report_path = out_dir / "food_beverage_engineering_review_report.md"

    write_csv_rows(flow_path, _FLOW_FIELDS, flow_rows)
    write_csv_rows(skip_path, _SKIP_FIELDS, skipped_rows)
    write_csv_rows(partial_path, _PARTIAL_FIELDS, partial_fill_rows)
    write_csv_rows(dividend_path, _DIVIDEND_FIELDS, [dividend_gap])
    write_csv_rows(startup_path, _STARTUP_FIELDS, [startup_gap])
    write_csv_rows(queue_path, _QUEUE_FIELDS, [_queue_row(decision, dividend_gap, order_health, startup_gap)])

    payload = {
        "strategy_id": summary.get("strategy_id") or DEFAULT_STRATEGY_ID,
        "review_type": "food_beverage_engineering_blocker_review",
        "experiment_layer": "engineering_smoke_test",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": {
            "local_daily_dir": str(local_daily_dir),
            "summary_json": str(summary_path),
            "price_csv": str(price_csv),
            "dividend_cash_csv": str(dividend_cash_csv),
        },
        "local_metrics": summary.get("metrics", {}),
        "order_health": order_health,
        "dividend_gap": dividend_gap,
        "startup_gap": startup_gap,
        "pm_decision": decision,
        "outputs": {
            "flow_table": str(flow_path),
            "order_skip_diagnosis": str(skip_path),
            "partial_fill_diagnosis": str(partial_path),
            "dividend_gap_diagnosis": str(dividend_path),
            "startup_gap_diagnosis": str(startup_path),
            "next_agent_queue": str(queue_path),
            "report": str(report_path),
        },
        "pm_rules": [
            "Do not modify V57f core sleeves, factors, weights, or rebalance rules.",
            "Do not tune food/beverage returns from this engineering review.",
            "Explained skipped orders are still an Engineering review item when they cause high cash drag.",
            "Missing real cash dividends remains a data/engineering blocker until repaired.",
            "Do not claim platform_replication_passed, accepted_strategy, or live_trading_approved.",
        ],
    }
    write_json_file(summary_out, payload)
    report_path.write_text(_report(payload), encoding="utf-8")
    return FoodBeverageEngineeringReviewResult(
        summary_json=summary_out,
        report_md=report_path,
        status=decision["status"],
        next_gate=decision["next_gate"],
    )


_FLOW_FIELDS = ["step", "owner", "input", "action", "output", "pass_standard", "forbidden_action"]
_SKIP_FIELDS = [
    "trade_date",
    "code",
    "side",
    "reason",
    "target_amount",
    "attempted_amount",
    "trade_price",
    "price_open",
    "price_high_limit",
    "price_low_limit",
    "paused",
    "tradability_check",
    "engineering_interpretation",
]
_PARTIAL_FIELDS = [
    "trade_date",
    "code",
    "side",
    "target_amount",
    "current_amount_before_rebalance",
    "expected_buy_delta",
    "filled_amount",
    "unfilled_amount",
    "fill_ratio",
    "trade_price",
    "reason",
    "engineering_interpretation",
]
_DIVIDEND_FIELDS = [
    "status",
    "source_path",
    "source_exists",
    "source_dividend_event_count",
    "output_dividend_event_count",
    "diagnosis",
    "required_repair",
]
_STARTUP_FIELDS = [
    "status",
    "requested_start_date",
    "first_signal_date",
    "has_startup_gap",
    "classification",
    "diagnosis",
    "required_repair",
]
_QUEUE_FIELDS = ["owner", "priority", "task", "input", "output", "blocked_actions", "stop_condition"]


def _flow_rows() -> list[dict[str, str]]:
    return [
        {
            "step": "1",
            "owner": "PM Agent",
            "input": "V57f freeze state + food_beverage route",
            "action": "confirm this review cannot change V57f or promote the sleeve",
            "output": "scope lock",
            "pass_standard": "V57f core unchanged; food_beverage remains observation/engineering review",
            "forbidden_action": "add food_beverage to V57f; tune factors; claim accepted",
        },
        {
            "step": "2",
            "owner": "Engineering Agent",
            "input": "local daily summary, rebalance_order_health, trades",
            "action": "separate no-order bugs from genuine tradability skips",
            "output": "order skip diagnosis",
            "pass_standard": "every skipped order has date, code, reason, and price-limit/suspension evidence",
            "forbidden_action": "ignore skipped orders because total return is low or high",
        },
        {
            "step": "3",
            "owner": "Engineering Agent",
            "input": "trades",
            "action": "surface buy orders whose filled amount is below the true rebalance delta",
            "output": "partial fill diagnosis",
            "pass_standard": "cash/lot-limited buy gaps are visible to PM gate",
            "forbidden_action": "treat target_amount as the same thing as this-order amount",
        },
        {
            "step": "4",
            "owner": "Engineering Agent",
            "input": "dividend source csv + local dividends output",
            "action": "verify whether real cash dividends entered the local simulation",
            "output": "dividend gap diagnosis",
            "pass_standard": "real tax-adjusted cash dividend rows exist or blocker is explicit",
            "forbidden_action": "promote a dividend sleeve with an empty dividend source",
        },
        {
            "step": "5",
            "owner": "Research Agent",
            "input": "PIT panel date coverage + first signal",
            "action": "classify pre-first-signal empty period",
            "output": "startup gap diagnosis",
            "pass_standard": "2021 gap is classified as PIT window issue, not order execution bug",
            "forbidden_action": "fill missing 2021 signal by using future-visible data",
        },
        {
            "step": "6",
            "owner": "PM Agent",
            "input": "all diagnostics",
            "action": "route next agent queue",
            "output": "repair/explain decision packet",
            "pass_standard": "one clear next action; no platform replication until blockers are closed",
            "forbidden_action": "continue to JoinQuant replication or V57f inclusion",
        },
    ]


def _diagnose_trade_execution(
    trade_rows: list[dict[str, str]],
    holding_rows: list[dict[str, str]],
    price_csv: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    skipped_trades = [row for row in trade_rows if str(row.get("side") or "").endswith("_skipped")]
    price_lookup = _price_lookup(price_csv, {(str(row.get("trade_date") or "")[:10], str(row.get("code") or "")) for row in skipped_trades})
    skipped_rows = []
    for row in skipped_trades:
        key = (str(row.get("trade_date") or "")[:10], str(row.get("code") or ""))
        price = price_lookup.get(key, {})
        check = _tradability_check(row, price)
        skipped_rows.append(
            {
                "trade_date": key[0],
                "code": key[1],
                "side": row.get("side", ""),
                "reason": row.get("reason", ""),
                "target_amount": _int(row.get("target_amount")),
                "attempted_amount": _int(row.get("amount")),
                "trade_price": row.get("price", ""),
                "price_open": price.get("open", ""),
                "price_high_limit": price.get("high_limit", ""),
                "price_low_limit": price.get("low_limit", ""),
                "paused": price.get("paused", ""),
                "tradability_check": check,
                "engineering_interpretation": _skip_interpretation(check),
            }
        )

    prior_holdings = _prior_holding_lookup(holding_rows)
    partial_rows = []
    for row in trade_rows:
        side = str(row.get("side") or "")
        if side != "buy":
            continue
        target = _int(row.get("target_amount"))
        filled = _int(row.get("amount"))
        trade_date = str(row.get("trade_date") or "")[:10]
        code = str(row.get("code") or "")
        current_before = prior_holdings.get((trade_date, code), 0)
        expected_delta = max(target - current_before, 0)
        if expected_delta <= 0 or filled >= expected_delta:
            continue
        unfilled = max(expected_delta - filled, 0)
        partial_rows.append(
            {
                "trade_date": trade_date,
                "code": code,
                "side": side,
                "target_amount": target,
                "current_amount_before_rebalance": current_before,
                "expected_buy_delta": expected_delta,
                "filled_amount": filled,
                "unfilled_amount": unfilled,
                "fill_ratio": f"{(filled / expected_delta):.6f}" if expected_delta else "",
                "trade_price": row.get("price", ""),
                "reason": row.get("reason", ""),
                "engineering_interpretation": "cash_or_lot_limited_buy_delta_visible_to_pm_gate",
            }
        )
    return skipped_rows, partial_rows


def _prior_holding_lookup(holding_rows: list[dict[str, str]]) -> dict[tuple[str, str], int]:
    by_code: dict[str, list[tuple[str, int]]] = {}
    for row in holding_rows:
        day = str(row.get("trade_date") or "")[:10]
        code = str(row.get("code") or "")
        if not day or not code:
            continue
        by_code.setdefault(code, []).append((day, _int(row.get("amount"))))
    for values in by_code.values():
        values.sort(key=lambda item: item[0])
    lookup: dict[tuple[str, str], int] = {}
    all_dates = sorted({day for values in by_code.values() for day, _amount in values})
    for code, values in by_code.items():
        idx = 0
        last_amount = 0
        for day in all_dates:
            while idx < len(values) and values[idx][0] < day:
                last_amount = values[idx][1]
                idx += 1
            lookup[(day, code)] = last_amount
    return lookup


def _price_lookup(price_csv: Path, keys: set[tuple[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    if not keys:
        return {}
    rows = read_csv_rows_if_exists(price_csv)
    lookup = {}
    for row in rows:
        key = (str(row.get("date") or "")[:10], str(row.get("code") or ""))
        if key in keys:
            lookup[key] = row
    return lookup


def _tradability_check(trade_row: dict[str, str], price_row: dict[str, str]) -> str:
    reason = str(trade_row.get("reason") or "")
    side = str(trade_row.get("side") or "")
    open_price = _float(price_row.get("open"))
    high_limit = _float(price_row.get("high_limit"))
    low_limit = _float(price_row.get("low_limit"))
    paused = str(price_row.get("paused") or "")
    if paused in {"1", "1.0", "true", "True"}:
        return "confirmed_paused"
    if reason == "high_limit" and side.startswith("buy") and open_price is not None and high_limit is not None and abs(open_price - high_limit) < 1e-9:
        return "confirmed_buy_open_at_high_limit"
    if reason == "low_limit" and side.startswith("sell") and open_price is not None and low_limit is not None and abs(open_price - low_limit) < 1e-9:
        return "confirmed_sell_open_at_low_limit"
    if reason:
        return f"reason_recorded_unconfirmed_by_price:{reason}"
    return "skipped_without_reason"


def _skip_interpretation(check: str) -> str:
    if check.startswith("confirmed_"):
        return "explained_tradability_skip_not_code_no_order_bug"
    if check.startswith("reason_recorded"):
        return "needs_price_source_spot_check"
    return "needs_engineering_repair"


def _diagnose_startup_gap(summary: dict[str, Any], signal_rows: list[dict[str, str]]) -> dict[str, Any]:
    window = summary.get("window", {})
    start = str(window.get("start_date") or "")
    first_signal = ""
    signal_dates = sorted({str(row.get("trade_date") or "")[:10] for row in signal_rows if row.get("trade_date")})
    if signal_dates:
        first_signal = signal_dates[0]
    has_gap = bool(start and first_signal and first_signal > start)
    return {
        "status": "research_pit_window_gap" if has_gap else "passed",
        "requested_start_date": start,
        "first_signal_date": first_signal,
        "has_startup_gap": str(has_gap).lower(),
        "classification": "panel_has_no_pit_rebalance_rows_before_first_signal" if has_gap else "no_startup_gap",
        "diagnosis": "pre-first-signal cash period is caused by missing PIT rebalance rows, not by failed local order execution" if has_gap else "no startup gap detected",
        "required_repair": "Research Agent repairs 2021 PIT panel only if PM requires pre-2022 food/beverage exposure" if has_gap else "none",
    }


def _diagnose_dividend_gap(source_path: Path, source_rows: list[dict[str, str]], output_rows: list[dict[str, str]]) -> dict[str, Any]:
    source_exists = source_path.exists()
    source_count = len(source_rows)
    output_count = len(output_rows)
    if not source_exists:
        status = "dividend_source_missing"
        diagnosis = "cash dividend source file is missing"
        repair = "build/import a PIT-safe tax-adjusted cash dividend source before promotion"
    elif source_count == 0:
        status = "dividend_source_empty"
        diagnosis = "cash dividend source exists but contains no dividend events"
        repair = "repair JoinQuant/DataJQ/Tushare/manual dividend import and rerun local daily simulation"
    elif output_count == 0:
        status = "dividend_output_empty"
        diagnosis = "source has events but local simulation did not emit dividend cash rows"
        repair = "debug dividend date/code mapping and rerun local daily simulation"
    else:
        status = "passed"
        diagnosis = "cash dividend source and local dividend output are non-empty"
        repair = "none"
    return {
        "status": status,
        "source_path": str(source_path),
        "source_exists": str(source_exists).lower(),
        "source_dividend_event_count": source_count,
        "output_dividend_event_count": output_count,
        "diagnosis": diagnosis,
        "required_repair": repair,
    }


def _diagnose_order_health(
    summary: dict[str, Any],
    order_health_rows: list[dict[str, str]],
    skipped_rows: list[dict[str, Any]],
    partial_fill_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    order = dict(summary.get("rebalance_order_health") or {})
    high_cash_rows = []
    for row in order_health_rows:
        cash_weight = _float(row.get("cash_weight_after_rebalance"))
        if cash_weight is not None and cash_weight >= 0.25:
            high_cash_rows.append(
                {
                    "trade_date": str(row.get("trade_date") or "")[:10],
                    "cash_weight_after_rebalance": cash_weight,
                    "holding_count_after_rebalance": _int(row.get("holding_count_after_rebalance")),
                    "selected_count": _int(row.get("selected_count")),
                }
            )
    no_order = _int(order.get("no_order_rebalance_count")) + _int(order.get("no_order_no_position_count"))
    status = "passed"
    if no_order:
        status = "failed_no_order_bug_or_no_position"
    elif skipped_rows or partial_fill_rows or high_cash_rows:
        status = "explained_needs_review"
    return {
        "status": status,
        "rebalance_signal_count": _int(order.get("rebalance_signal_count")),
        "normal_rebalance_count": _int(order.get("normal_rebalance_count")),
        "no_order_rebalance_count": _int(order.get("no_order_rebalance_count")),
        "no_order_no_position_count": _int(order.get("no_order_no_position_count")),
        "blocked_or_unfilled_rebalance_count": _int(order.get("blocked_or_unfilled_rebalance_count")),
        "partial_skipped_order_count": len(skipped_rows),
        "partial_fill_count": len(partial_fill_rows),
        "high_cash_rebalance_count": len(high_cash_rows),
        "high_cash_rebalance_dates": [row["trade_date"] for row in high_cash_rows],
        "diagnosis": _order_health_diagnosis(status, skipped_rows, partial_fill_rows, high_cash_rows),
    }


def _order_health_diagnosis(
    status: str,
    skipped_rows: list[dict[str, Any]],
    partial_fill_rows: list[dict[str, Any]],
    high_cash_rows: list[dict[str, Any]],
) -> str:
    if status == "failed_no_order_bug_or_no_position":
        return "local simulation has an actual no-order or no-position failure; stop before any promotion"
    if status == "explained_needs_review":
        parts = []
        if skipped_rows:
            parts.append(f"{len(skipped_rows)} skipped orders")
        if partial_fill_rows:
            parts.append(f"{len(partial_fill_rows)} partial fills")
        if high_cash_rows:
            dates = ",".join(row["trade_date"] for row in high_cash_rows)
            parts.append(f"high cash after rebalance on {dates}")
        return "; ".join(parts) + "; execution is explainable but not promotion-ready"
    return "all rebalance orders look healthy"


def _pm_decision(order_health: dict[str, Any], dividend_gap: dict[str, Any], startup_gap: dict[str, Any]) -> dict[str, Any]:
    blockers = []
    review_items = []
    if dividend_gap["status"] != "passed":
        blockers.append(dividend_gap["status"])
    if order_health["status"] != "passed":
        review_items.append(order_health["status"])
    if startup_gap["status"] != "passed":
        review_items.append(startup_gap["status"])
    status = "engineering_needs_repair"
    next_gate = "repair_real_cash_dividends_then_rerun_local_daily_simulation"
    if blockers:
        status = "engineering_data_blocker_confirmed"
    elif review_items:
        status = "engineering_needs_review_explained"
        next_gate = "pm_review_tradability_and_cash_drag_before_observation_paper_tracking"
    else:
        status = "engineering_review_passed"
        next_gate = "pm_review_for_observation_paper_tracking_only"
    return {
        "status": status,
        "next_gate": next_gate,
        "blockers": blockers,
        "review_items": review_items,
        "allowed_next_action": "repair_food_beverage_dividend_source_and_rerun_local_daily_only" if blockers else "pm_review_only",
        "blocked_action": "modify_V57f_or_start_platform_replication_or_tune_food_beverage_returns",
        "can_enter_engineering_next_layer": False,
        "can_enter_platform_replication": False,
        "can_join_v57f_core": False,
    }


def _queue_row(
    decision: dict[str, Any],
    dividend_gap: dict[str, Any],
    order_health: dict[str, Any],
    startup_gap: dict[str, Any],
) -> dict[str, str]:
    if dividend_gap["status"] != "passed":
        owner = "Engineering Agent"
        task = "repair/import PIT-safe real cash dividends for food_beverage, then rerun local daily simulation and this engineering review"
        inputs = dividend_gap["source_path"]
        output = "non-empty cash dividend source + local dividends.csv + refreshed order health"
        stop = "dividend source has real events and no critical no-order/no-position failures remain"
    elif order_health["status"] != "passed":
        owner = "PM Agent"
        task = "review explained price-limit skips, partial fill, and high cash drag before any observation paper tracking"
        inputs = "order_skip_diagnosis.csv; partial_fill_diagnosis.csv; rebalance_order_health.csv"
        output = "PM tradability/cash-drag decision"
        stop = "PM either accepts observation-only tracking or returns execution policy repair"
    elif startup_gap["status"] != "passed":
        owner = "Research Agent"
        task = "repair 2021 PIT panel coverage only if pre-2022 exposure is required"
        inputs = "startup_gap_diagnosis.csv"
        output = "repaired PIT panel or explicit no-repair PM waiver"
        stop = "PIT startup gap is repaired or waived"
    else:
        owner = "PM Agent"
        task = "consider observation paper tracking only"
        inputs = "engineering_review_summary.json"
        output = "observation tracking decision"
        stop = "food_beverage remains outside V57f core"
    return {
        "owner": owner,
        "priority": "P0" if dividend_gap["status"] != "passed" else "P1",
        "task": task,
        "input": inputs,
        "output": output,
        "blocked_actions": str(decision["blocked_action"]),
        "stop_condition": stop,
    }


def _report(payload: dict[str, Any]) -> str:
    metrics = payload.get("local_metrics", {})
    order = payload.get("order_health", {})
    dividend = payload.get("dividend_gap", {})
    startup = payload.get("startup_gap", {})
    decision = payload.get("pm_decision", {})
    lines = [
        "# Food/Beverage Engineering Blocker Review",
        "",
        "## Decision",
        "",
        f"- Status: `{decision.get('status')}`",
        f"- Next gate: `{decision.get('next_gate')}`",
        f"- Can enter platform replication: `{decision.get('can_enter_platform_replication')}`",
        f"- Can join V57f core: `{decision.get('can_join_v57f_core')}`",
        "",
        "This packet only repairs or explains Engineering blockers. It does not tune food/beverage and does not change frozen V57f.",
        "",
        "## Flow Table",
        "",
        "| Step | Owner | Action | Pass Standard | Forbidden Action |",
        "|---:|---|---|---|---|",
    ]
    for row in _flow_rows():
        lines.append(
            f"| {row['step']} | {row['owner']} | {row['action']} | {row['pass_standard']} | {row['forbidden_action']} |"
        )
    lines.extend(
        [
            "",
            "## Order Health",
            "",
            f"- Rebalance signals: {order.get('rebalance_signal_count')}",
            f"- Normal rebalance count: {order.get('normal_rebalance_count')}",
            f"- No-order rebalance count: {order.get('no_order_rebalance_count')}",
            f"- No-order/no-position count: {order.get('no_order_no_position_count')}",
            f"- Skipped orders: {order.get('partial_skipped_order_count')}",
            f"- Partial fills: {order.get('partial_fill_count')}",
            f"- High-cash rebalance dates: {', '.join(order.get('high_cash_rebalance_dates') or [])}",
            f"- Diagnosis: {order.get('diagnosis')}",
            "",
            "## Dividend Gap",
            "",
            f"- Status: `{dividend.get('status')}`",
            f"- Source event count: {dividend.get('source_dividend_event_count')}",
            f"- Local output event count: {dividend.get('output_dividend_event_count')}",
            f"- Required repair: {dividend.get('required_repair')}",
            "",
            "## Startup Gap",
            "",
            f"- Status: `{startup.get('status')}`",
            f"- Requested start: {startup.get('requested_start_date')}",
            f"- First signal: {startup.get('first_signal_date')}",
            f"- Diagnosis: {startup.get('diagnosis')}",
            "",
            "## Local Metrics Context",
            "",
            f"- Strategy return: {_pct(metrics.get('strategy_return'))}",
            f"- Benchmark return: {_pct(metrics.get('benchmark_return'))}",
            f"- Excess return: {_pct(metrics.get('excess_return'))}",
            f"- Max drawdown: {_pct(metrics.get('max_drawdown'))}",
            f"- Sharpe: {_num(metrics.get('sharpe'))}",
            "",
            "## Next Queue",
            "",
            f"- Owner: `{_queue_row(decision, dividend, order, startup)['owner']}`",
            f"- Task: {_queue_row(decision, dividend, order, startup)['task']}",
            f"- Stop condition: {_queue_row(decision, dividend, order, startup)['stop_condition']}",
            "",
        ]
    )
    return "\n".join(lines)


def _int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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

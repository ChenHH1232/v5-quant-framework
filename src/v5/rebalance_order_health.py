from __future__ import annotations

from collections import defaultdict
from typing import Any

from v5.math_utils import to_float


def build_rebalance_order_health(
    signals_by_date: dict[str, Any],
    daily_rows: list[dict[str, Any]],
    trade_rows: list[dict[str, Any]],
    holding_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    daily_by_date = {str(row.get("trade_date") or "")[:10]: row for row in daily_rows if row.get("trade_date")}
    trades_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in trade_rows:
        day = str(row.get("trade_date") or "")[:10]
        if day:
            trades_by_date[day].append(row)
    holdings_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in holding_rows:
        day = str(row.get("trade_date") or "")[:10]
        if day:
            holdings_by_date[day].append(row)

    rows: list[dict[str, Any]] = []
    leading_empty = 0
    still_leading = True
    first_executed_order_date = ""
    first_position_date = ""

    for day in sorted(str(date)[:10] for date in signals_by_date):
        selected_codes = _selected_codes(signals_by_date.get(day))
        daily = daily_by_date.get(day, {})
        trades = trades_by_date.get(day, [])
        holdings = holdings_by_date.get(day, [])
        buy_count = _side_count(trades, "buy")
        sell_count = _side_count(trades, "sell")
        buy_skipped_count = _side_count(trades, "buy_skipped")
        sell_skipped_count = _side_count(trades, "sell_skipped")
        executed_count = buy_count + sell_count
        skipped_count = buy_skipped_count + sell_skipped_count
        held_count = sum(1 for row in holdings if (to_float(row.get("amount")) or 0.0) > 0)
        selected_count = len(selected_codes)

        if executed_count > 0 and not first_executed_order_date:
            first_executed_order_date = day
        if held_count > 0 and not first_position_date:
            first_position_date = day
        if still_leading and executed_count == 0 and held_count == 0:
            leading_empty += 1
        else:
            still_leading = False

        status = _status(
            daily_available=bool(daily),
            selected_count=selected_count,
            executed_count=executed_count,
            skipped_count=skipped_count,
            held_count=held_count,
        )
        rows.append(
            {
                "trade_date": day,
                "order_health_status": status,
                "selected_count": selected_count,
                "selected_codes": ";".join(selected_codes),
                "executed_order_count": executed_count,
                "buy_order_count": buy_count,
                "sell_order_count": sell_count,
                "skipped_order_count": skipped_count,
                "buy_skipped_count": buy_skipped_count,
                "sell_skipped_count": sell_skipped_count,
                "buy_turnover": _sum_value(trades, "buy"),
                "sell_turnover": _sum_value(trades, "sell"),
                "holding_count_after_rebalance": held_count,
                "cash_weight_after_rebalance": daily.get("cash_weight", ""),
                "portfolio_value_after_rebalance": daily.get("portfolio_value", ""),
                "diagnosis": _diagnosis(status),
            }
        )

    missing_daily_count = sum(1 for row in rows if row["order_health_status"] == "missing_daily_row")
    no_order_count = sum(1 for row in rows if int(row["executed_order_count"]) == 0)
    no_order_no_position_count = sum(1 for row in rows if row["order_health_status"] == "no_order_no_position")
    blocked_count = sum(1 for row in rows if row["order_health_status"] == "order_blocked_or_unfilled")
    normal_count = sum(1 for row in rows if row["order_health_status"] in {"normal_ordered", "held_no_order_needed"})
    summary = {
        "rebalance_signal_count": len(rows),
        "normal_rebalance_count": normal_count,
        "no_order_rebalance_count": no_order_count,
        "no_order_no_position_count": no_order_no_position_count,
        "blocked_or_unfilled_rebalance_count": blocked_count,
        "missing_daily_rebalance_count": missing_daily_count,
        "leading_no_order_no_position_count": leading_empty,
        "first_executed_order_date": first_executed_order_date or None,
        "first_position_date": first_position_date or None,
        "needs_review": bool(missing_daily_count or no_order_no_position_count or blocked_count),
        "pm_rule": "Every rebalance signal must be checked for actual local orders and post-rebalance holdings before comparing with JoinQuant.",
    }
    return rows, summary


def _selected_codes(value: Any) -> list[str]:
    if isinstance(value, dict):
        return sorted(str(code) for code, weight in value.items() if (to_float(weight) or 0.0) > 0)
    if isinstance(value, list):
        return sorted(str(code) for code in value if code)
    return []


def _side_count(rows: list[dict[str, Any]], side: str) -> int:
    return sum(1 for row in rows if str(row.get("side") or "") == side)


def _sum_value(rows: list[dict[str, Any]], side: str) -> float:
    return sum(to_float(row.get("value")) or 0.0 for row in rows if str(row.get("side") or "") == side)


def _status(
    *,
    daily_available: bool,
    selected_count: int,
    executed_count: int,
    skipped_count: int,
    held_count: int,
) -> str:
    if not daily_available:
        return "missing_daily_row"
    if selected_count <= 0:
        return "no_selected_stocks"
    if executed_count > 0 and held_count > 0:
        return "normal_ordered"
    if executed_count > 0:
        return "ordered_but_no_position"
    if skipped_count > 0:
        return "order_blocked_or_unfilled"
    if held_count > 0:
        return "held_no_order_needed"
    return "no_order_no_position"


def _diagnosis(status: str) -> str:
    return {
        "missing_daily_row": "Signal date is not present in local daily return rows; check price calendar coverage.",
        "no_selected_stocks": "Signal exists but selected universe is empty.",
        "normal_ordered": "At least one order executed and holdings exist after rebalance.",
        "ordered_but_no_position": "Orders executed but no selected holding remains; inspect sell/buy sequence and lot constraints.",
        "order_blocked_or_unfilled": "Orders were attempted but skipped by tradability or lot/cash constraints.",
        "held_no_order_needed": "No new order was needed because the existing holding already matched the target closely enough.",
        "no_order_no_position": "Signal exists but no order executed and no selected holding exists after rebalance.",
    }.get(status, "")

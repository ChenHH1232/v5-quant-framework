from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows
from v5.math_utils import to_float


DEFAULT_LOOKBACK_TRADING_DAYS = 252
DEFAULT_WARMUP_BUFFER_TRADING_DAYS = 20


@dataclass(frozen=True)
class StartupDateModel:
    deployment_date: str
    first_tradable_date: str
    warmup_start_date: str
    trade_start_date: str
    required_lookback_days: int
    warmup_buffer_days: int
    regular_rebalance_dates: list[str]
    initial_rebalance_event: str
    warmup_available: bool
    startup_ready: bool
    blocker_reason: str


def build_startup_date_model(
    *,
    deployment_date: str,
    trading_days: list[str],
    regular_rebalance_dates: list[str] | None = None,
    required_lookback_days: int = DEFAULT_LOOKBACK_TRADING_DAYS,
    warmup_buffer_days: int = DEFAULT_WARMUP_BUFFER_TRADING_DAYS,
    initial_rebalance_policy: str = "deployment_first_tradable",
) -> StartupDateModel:
    days = sorted({day[:10] for day in trading_days if day})
    regular = sorted({day[:10] for day in (regular_rebalance_dates or []) if day})
    first_tradable = next((day for day in days if day >= deployment_date), "")
    if not first_tradable:
        return StartupDateModel(
            deployment_date=deployment_date,
            first_tradable_date="",
            warmup_start_date=_calendar_warmup_start(deployment_date, required_lookback_days + warmup_buffer_days),
            trade_start_date="",
            required_lookback_days=required_lookback_days,
            warmup_buffer_days=warmup_buffer_days,
            regular_rebalance_dates=regular,
            initial_rebalance_event="",
            warmup_available=False,
            startup_ready=False,
            blocker_reason="no_trading_day_on_or_after_deployment_date",
        )
    required_total = required_lookback_days + warmup_buffer_days
    first_idx = days.index(first_tradable)
    warmup_available = first_idx >= required_lookback_days
    warmup_start_date = days[max(0, first_idx - required_total)] if days else _calendar_warmup_start(deployment_date, required_total)
    blocker = "" if warmup_available else "insufficient_pre_deployment_price_history_for_required_lookback"
    return StartupDateModel(
        deployment_date=deployment_date,
        first_tradable_date=first_tradable,
        warmup_start_date=warmup_start_date,
        trade_start_date=first_tradable,
        required_lookback_days=required_lookback_days,
        warmup_buffer_days=warmup_buffer_days,
        regular_rebalance_dates=regular,
        initial_rebalance_event=first_tradable if initial_rebalance_policy == "deployment_first_tradable" else "",
        warmup_available=warmup_available,
        startup_ready=warmup_available,
        blocker_reason=blocker,
    )


def load_trading_days_from_price_files(price_files: list[Path]) -> list[str]:
    days: set[str] = set()
    for path in price_files:
        if not path.exists():
            continue
        for row in read_csv_rows(path):
            day = str(row.get("date") or row.get("trade_date") or "")[:10]
            open_price = to_float(row.get("open"))
            close_price = to_float(row.get("close"))
            if day and open_price is not None and close_price is not None and open_price > 0 and close_price > 0:
                days.add(day)
    return sorted(days)


def load_signal_dates(signals_csv: Path) -> list[str]:
    if not signals_csv.exists():
        return []
    return sorted({str(row.get("trade_date") or "")[:10] for row in read_csv_rows(signals_csv) if row.get("trade_date")})


def startup_gap_days(deployment_date: str, first_signal_date: str | None) -> int | None:
    if not deployment_date or not first_signal_date:
        return None
    return (_parse_date(first_signal_date) - _parse_date(deployment_date)).days


def inject_initial_rebalance_signal(
    signal_rows: list[dict[str, Any]],
    initial_rows: list[dict[str, Any]],
    *,
    initial_rebalance_date: str,
    event_id: str = "initial_rebalance_event",
) -> list[dict[str, Any]]:
    copied = [dict(row) for row in signal_rows if str(row.get("trade_date") or "")[:10] != initial_rebalance_date]
    for row in initial_rows:
        item = dict(row)
        item["trade_date"] = initial_rebalance_date
        item["rebalance_event_type"] = event_id
        copied.append(item)
    for row in copied:
        row.setdefault("rebalance_event_type", "regular_rebalance")
    return sorted(copied, key=lambda row: (str(row.get("trade_date") or ""), str(row.get("sector_id") or ""), int(float(row.get("selected_rank") or 0))))


def first_required_field_pass_date(panel_rows: list[dict[str, Any]], required_fields: list[str]) -> str:
    for day in sorted({str(row.get("trade_date") or "")[:10] for row in panel_rows if row.get("trade_date")}):
        day_rows = [row for row in panel_rows if str(row.get("trade_date") or "")[:10] == day]
        if day_rows and all(all(row.get(field) not in (None, "") for field in required_fields) for row in day_rows):
            return day
    return ""


def first_required_candidate_date(panel_rows: list[dict[str, Any]], required_fields: list[str]) -> str:
    for day in sorted({str(row.get("trade_date") or "")[:10] for row in panel_rows if row.get("trade_date")}):
        day_rows = [row for row in panel_rows if str(row.get("trade_date") or "")[:10] == day]
        if any(all(row.get(field) not in (None, "") for field in required_fields) for row in day_rows):
            return day
    return ""


def first_field_available_dates(panel_rows: list[dict[str, Any]], fields: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in sorted(panel_rows, key=lambda item: str(item.get("trade_date") or "")):
        day = str(row.get("trade_date") or "")[:10]
        for field in fields:
            if field not in result and row.get(field) not in (None, ""):
                result[field] = day
    return result


def _calendar_warmup_start(deployment_date: str, trading_days: int) -> str:
    return (_parse_date(deployment_date) - timedelta(days=int(trading_days * 1.6))).date().isoformat()


def _parse_date(value: str) -> datetime:
    return datetime.strptime(value[:10], "%Y-%m-%d")

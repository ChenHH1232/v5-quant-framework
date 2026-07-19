from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.io_utils import read_csv_rows
from v5.math_utils import to_float


DEFAULT_SIGNALS = Path("validation_formal_v56_basket_constructor") / "basket_rebalance_signals.csv"
DEFAULT_OUT = Path("exports/joinquant/v56_dividend_low_vol_fcf_basket_frozen_signals_near5y.py")


@dataclass(frozen=True)
class BasketJoinQuantExportResult:
    script_path: Path
    strategy_id: str
    signal_date_count: int
    holding_count: int


def export_basket_frozen_signals_to_joinquant(
    signals_csv: Path = DEFAULT_SIGNALS,
    out_file: Path = DEFAULT_OUT,
    *,
    strategy_id: str = "v56_dividend_low_vol_fcf_shadow_basket",
    script_version: str | None = None,
    benchmark: str = "000300.XSHG",
    target_exposure: float = 0.995,
    lot_size: int = 100,
) -> BasketJoinQuantExportResult:
    signals = _load_signals(signals_csv)
    if not signals:
        raise ValueError(f"no basket signals found: {signals_csv}")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    script_version = script_version or f"{strategy_id}_frozen_signals_{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    content = _build_script(
        signals,
        strategy_id=strategy_id,
        script_version=script_version,
        benchmark=benchmark,
        target_exposure=target_exposure,
        lot_size=lot_size,
    )
    out_file.write_text(content, encoding="utf-8")
    return BasketJoinQuantExportResult(
        script_path=out_file,
        strategy_id=strategy_id,
        signal_date_count=len(signals),
        holding_count=sum(len(items) for items in signals.values()),
    )


def _load_signals(path: Path) -> dict[str, list[tuple[str, float, str]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in read_csv_rows(path):
        day = str(row.get("trade_date") or "")[:10]
        code = str(row.get("code") or "")
        weight = to_float(row.get("target_weight"))
        sector = str(row.get("sector_id") or "")
        rank = int(to_float(row.get("selected_rank")) or 999999)
        if not day or not code or weight is None or weight <= 0:
            continue
        grouped.setdefault(day, []).append({"code": code, "weight": weight, "sector": sector, "rank": rank})
    result: dict[str, list[tuple[str, float, str]]] = {}
    for day in sorted(grouped):
        rows = sorted(grouped[day], key=lambda item: (item["rank"], item["code"]))
        result[day] = [(str(item["code"]), float(item["weight"]), str(item["sector"])) for item in rows]
    return result


def _signals_literal(signals: dict[str, list[tuple[str, float, str]]]) -> str:
    lines = ["{"]
    for day, rows in signals.items():
        item_text = ", ".join(f"({code!r}, {weight:.12f}, {sector!r})" for code, weight, sector in rows)
        lines.append(f"    {day!r}: [{item_text}],")
    lines.append("}")
    return "\n".join(lines)


def _build_script(
    signals: dict[str, list[tuple[str, float, str]]],
    *,
    strategy_id: str,
    script_version: str,
    benchmark: str,
    target_exposure: float,
    lot_size: int,
) -> str:
    first_signal_date = min(signals)
    selection_count = max(len(rows) for rows in signals.values())
    return f'''from jqdata import *


"""
Bank Quant V5 - Dividend Low-Vol Cash-Flow enhanced ETF frozen-signal JoinQuant script.

Purpose:
- Platform replication preparation for a frozen cross-sector basket.
- This is not an accepted strategy and must not be tuned after seeing JoinQuant results.

Frozen rule:
- Use local basket_rebalance_signals.csv exactly.
- Rebalance only on exact frozen signal dates.
- Use order_target_value, not order_target_percent, for compatibility with JoinQuant runtimes.
- No timing overlay, no stop loss, no take profit, no return tuning.

Comparison contract:
- Local runner executes at daily open and values at daily close.
- JoinQuant scheduled execution is 09:40, so small execution differences are expected.
- JoinQuant display benchmark is only a platform reference.
- Formal relative judgment should use local same-pool total-return benchmark and attribution packet.
"""


FROZEN_SIGNALS = {_signals_literal(signals)}

FIRST_SIGNAL_DATE = {first_signal_date!r}


def initialize(context):
    set_benchmark({benchmark!r})
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    set_order_cost(
        OrderCost(open_commission=0.0003, close_commission=0.0003, min_commission=5),
        type='stock',
    )

    g.strategy_id = {strategy_id!r}
    g.script_version = {script_version!r}
    g.target_exposure = {target_exposure:.12f}
    g.selection_count = {selection_count}
    g.lot_size = {lot_size}
    g.executed_dates = set()
    g.debug = True

    log.info('basket script=%s strategy=%s frozen_signal_dates=%d first_signal=%s benchmark=%s' % (
        g.script_version,
        g.strategy_id,
        len(FROZEN_SIGNALS),
        FIRST_SIGNAL_DATE,
        {benchmark!r},
    ))
    log.info('frozen rule: exact local basket signals; no recompute, no tuning, no accepted-strategy claim.')
    log.info('benchmark note: platform benchmark is display-only; formal comparison uses local same-pool total-return benchmark.')

    run_daily(maybe_rebalance, time='09:40')
    run_daily(after_close_log, time='after_close')


def maybe_rebalance(context):
    today = context.current_dt.date().isoformat()
    if today not in FROZEN_SIGNALS:
        return
    if today in g.executed_dates:
        return

    rows = FROZEN_SIGNALS[today]
    tradable_rows = []
    for code, weight, sector_id in rows:
        if is_tradable(code):
            tradable_rows.append((code, weight, sector_id))
        else:
            log.info('skip untradable date=%s code=%s sector=%s' % (today, code, sector_id))

    if not tradable_rows:
        log.info('BLOCKED no tradable selected stocks date=%s' % today)
        g.executed_dates.add(today)
        return

    total_value = context.portfolio.total_value
    log.info(
        'rebalance date=%s raw_selected=%d tradable_selected=%d target_exposure=%.4f selected=%s'
        % (today, len(rows), len(tradable_rows), g.target_exposure, ','.join([item[0] for item in tradable_rows]))
    )
    execute_target_weights(context, tradable_rows, total_value)
    g.executed_dates.add(today)


def execute_target_weights(context, target_rows, total_value):
    selected = set([code for code, _weight, _sector in target_rows])
    current_positions = list(context.portfolio.positions.keys())
    current_data = get_current_data()

    for code in current_positions:
        if code not in selected:
            try:
                order_target_value(code, 0)
            except Exception as exc:
                log.info('sell failed code=%s error=%s' % (code, str(exc)))

    for code, weight, sector_id in target_rows:
        target_value = total_value * float(weight) * g.target_exposure
        estimated_price = get_estimated_trade_price(current_data, code)
        if estimated_price is not None:
            min_lot_value = estimated_price * g.lot_size
            if target_value < min_lot_value:
                log.info(
                    'capital warning code=%s target_value=%.2f one_lot_value=%.2f price=%.3f lot_size=%d; order may be rejected by lot-size rule.'
                    % (code, target_value, min_lot_value, estimated_price, g.lot_size)
                )
        try:
            order_target_value(code, target_value)
        except Exception as exc:
            log.info('buy/adjust failed code=%s sector=%s target_value=%.2f error=%s' % (code, sector_id, target_value, str(exc)))


def get_estimated_trade_price(current_data, code):
    try:
        item = current_data[code]
    except Exception:
        return None
    for attr in ('last_price', 'day_open', 'high_limit', 'low_limit'):
        try:
            value = getattr(item, attr, None)
        except Exception:
            value = None
        if value is not None and value > 0:
            return float(value)
    return None


def is_tradable(code):
    current_data = get_current_data()
    try:
        item = current_data[code]
    except Exception:
        return False
    if getattr(item, 'paused', False):
        return False
    if getattr(item, 'is_st', False):
        return False
    return True


def after_close_log(context):
    today = context.current_dt.date().isoformat()
    if today not in FROZEN_SIGNALS:
        return
    positions = []
    for code, pos in context.portfolio.positions.items():
        if pos.total_amount > 0:
            positions.append('%s:%s' % (code, int(pos.total_amount)))
    log.info(
        'after_close date=%s total_value=%.2f cash=%.2f positions=%s'
        % (today, context.portfolio.total_value, context.portfolio.cash, ';'.join(positions))
    )
'''

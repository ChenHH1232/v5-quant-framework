from jqdata import *
from datetime import datetime

"""
Bank Quant V5 - Frozen-signal JoinQuant execution check.

Purpose:
- Reproduce V5 local validated rebalance signals on JoinQuant.
- This file does not recompute factors on JoinQuant.
- Use it to isolate execution/platform differences from data/factor-source differences.

Backtest window in JoinQuant UI: 2021-05-01 to 2026-05-31.
Benchmark: 512800.XSHG bank ETF.
"""

FROZEN_SIGNALS = {
    '2021-07-01': [
        ('601077.XSHG', 0.1250000000),
        ('601128.XSHG', 0.1250000000),
        ('601009.XSHG', 0.1250000000),
        ('601288.XSHG', 0.1250000000),
        ('601658.XSHG', 0.1250000000),
        ('600036.XSHG', 0.1250000000),
        ('601229.XSHG', 0.1250000000),
        ('601997.XSHG', 0.1250000000),
    ],
    '2021-10-08': [
        ('601009.XSHG', 0.1250000000),
        ('601229.XSHG', 0.1250000000),
        ('601077.XSHG', 0.1250000000),
        ('603323.XSHG', 0.1250000000),
        ('601658.XSHG', 0.1250000000),
        ('601128.XSHG', 0.1250000000),
        ('601577.XSHG', 0.1250000000),
        ('601288.XSHG', 0.1250000000),
    ],
    '2022-01-04': [
        ('601077.XSHG', 0.1250000000),
        ('601128.XSHG', 0.1250000000),
        ('601009.XSHG', 0.1250000000),
        ('601658.XSHG', 0.1250000000),
        ('601288.XSHG', 0.1250000000),
        ('601229.XSHG', 0.1250000000),
        ('600036.XSHG', 0.1250000000),
        ('601577.XSHG', 0.1250000000),
    ],
    '2022-04-01': [
        ('002807.XSHE', 0.1250000000),
        ('601229.XSHG', 0.1250000000),
        ('601288.XSHG', 0.1250000000),
        ('601128.XSHG', 0.1250000000),
        ('601009.XSHG', 0.1250000000),
        ('601187.XSHG', 0.1250000000),
        ('601077.XSHG', 0.1250000000),
        ('601577.XSHG', 0.1250000000),
    ],
    '2022-07-01': [
        ('601825.XSHG', 0.1250000000),
        ('601077.XSHG', 0.1250000000),
        ('601009.XSHG', 0.1250000000),
        ('601658.XSHG', 0.1250000000),
        ('002966.XSHE', 0.1250000000),
        ('601187.XSHG', 0.1250000000),
        ('600036.XSHG', 0.1250000000),
        ('601128.XSHG', 0.1250000000),
    ],
    '2022-10-10': [
        ('601825.XSHG', 0.1250000000),
        ('601077.XSHG', 0.1250000000),
        ('603323.XSHG', 0.1250000000),
        ('601229.XSHG', 0.1250000000),
        ('601658.XSHG', 0.1250000000),
        ('600036.XSHG', 0.1250000000),
        ('601009.XSHG', 0.1250000000),
        ('600908.XSHG', 0.1250000000),
    ],
    '2023-01-03': [
        ('601825.XSHG', 0.1250000000),
        ('601077.XSHG', 0.1250000000),
        ('601658.XSHG', 0.1250000000),
        ('601128.XSHG', 0.1250000000),
        ('601288.XSHG', 0.1250000000),
        ('600036.XSHG', 0.1250000000),
        ('603323.XSHG', 0.1250000000),
        ('600919.XSHG', 0.1250000000),
    ],
    '2023-04-03': [
        ('002807.XSHE', 0.1250000000),
        ('601825.XSHG', 0.1250000000),
        ('601077.XSHG', 0.1250000000),
        ('600908.XSHG', 0.1250000000),
        ('601009.XSHG', 0.1250000000),
        ('603323.XSHG', 0.1250000000),
        ('600919.XSHG', 0.1250000000),
        ('601288.XSHG', 0.1250000000),
    ],
    '2023-07-03': [
        ('601077.XSHG', 0.1250000000),
        ('601825.XSHG', 0.1250000000),
        ('601229.XSHG', 0.1250000000),
        ('601009.XSHG', 0.1250000000),
        ('002966.XSHE', 0.1250000000),
        ('002839.XSHE', 0.1250000000),
        ('600926.XSHG', 0.1250000000),
        ('601187.XSHG', 0.1250000000),
    ],
    '2023-10-09': [
        ('601825.XSHG', 0.1250000000),
        ('603323.XSHG', 0.1250000000),
        ('601077.XSHG', 0.1250000000),
        ('600908.XSHG', 0.1250000000),
        ('601009.XSHG', 0.1250000000),
        ('600919.XSHG', 0.1250000000),
        ('601838.XSHG', 0.1250000000),
        ('002807.XSHE', 0.1250000000),
    ],
    '2024-01-02': [
        ('601825.XSHG', 0.1250000000),
        ('601077.XSHG', 0.1250000000),
        ('002807.XSHE', 0.1250000000),
        ('601128.XSHG', 0.1250000000),
        ('600919.XSHG', 0.1250000000),
        ('603323.XSHG', 0.1250000000),
        ('601838.XSHG', 0.1250000000),
        ('002839.XSHE', 0.1250000000),
    ],
    '2024-04-01': [
        ('002807.XSHE', 0.1250000000),
        ('601825.XSHG', 0.1250000000),
        ('601187.XSHG', 0.1250000000),
        ('002839.XSHE', 0.1250000000),
        ('603323.XSHG', 0.1250000000),
        ('600908.XSHG', 0.1250000000),
        ('601077.XSHG', 0.1250000000),
        ('600919.XSHG', 0.1250000000),
    ],
    '2024-07-01': [
        ('600919.XSHG', 0.1250000000),
        ('601825.XSHG', 0.1250000000),
        ('601077.XSHG', 0.1250000000),
        ('600926.XSHG', 0.1250000000),
        ('600908.XSHG', 0.1250000000),
        ('000001.XSHE', 0.1250000000),
        ('002839.XSHE', 0.1250000000),
        ('002966.XSHE', 0.1250000000),
    ],
    '2024-10-08': [
        ('601825.XSHG', 0.1250000000),
        ('601077.XSHG', 0.1250000000),
        ('603323.XSHG', 0.1250000000),
        ('601838.XSHG', 0.1250000000),
        ('600908.XSHG', 0.1250000000),
        ('600919.XSHG', 0.1250000000),
        ('002966.XSHE', 0.1250000000),
        ('002807.XSHE', 0.1250000000),
    ],
    '2025-01-02': [
        ('601128.XSHG', 0.1250000000),
        ('601825.XSHG', 0.1250000000),
        ('601187.XSHG', 0.1250000000),
        ('000001.XSHE', 0.1250000000),
        ('603323.XSHG', 0.1250000000),
        ('002966.XSHE', 0.1250000000),
        ('601528.XSHG', 0.1250000000),
        ('002807.XSHE', 0.1250000000),
    ],
    '2025-04-01': [
        ('002807.XSHE', 0.1250000000),
        ('601187.XSHG', 0.1250000000),
        ('601825.XSHG', 0.1250000000),
        ('002966.XSHE', 0.1250000000),
        ('603323.XSHG', 0.1250000000),
        ('600908.XSHG', 0.1250000000),
        ('600919.XSHG', 0.1250000000),
        ('601128.XSHG', 0.1250000000),
    ],
    '2025-07-01': [
        ('601128.XSHG', 0.1250000000),
        ('600908.XSHG', 0.1250000000),
        ('600926.XSHG', 0.1250000000),
        ('002839.XSHE', 0.1250000000),
        ('601577.XSHG', 0.1250000000),
        ('601825.XSHG', 0.1250000000),
        ('601077.XSHG', 0.1250000000),
        ('601658.XSHG', 0.1250000000),
    ],
    '2025-10-09': [
        ('603323.XSHG', 0.1250000000),
        ('600908.XSHG', 0.1250000000),
        ('601128.XSHG', 0.1250000000),
        ('601825.XSHG', 0.1250000000),
        ('002807.XSHE', 0.1250000000),
        ('601077.XSHG', 0.1250000000),
        ('601577.XSHG', 0.1250000000),
        ('601838.XSHG', 0.1250000000),
    ],
    '2026-01-05': [
        ('601128.XSHG', 0.1250000000),
        ('002807.XSHE', 0.1250000000),
        ('002839.XSHE', 0.1250000000),
        ('603323.XSHG', 0.1250000000),
        ('600908.XSHG', 0.1250000000),
        ('601528.XSHG', 0.1250000000),
        ('601577.XSHG', 0.1250000000),
        ('601825.XSHG', 0.1250000000),
    ],
}

TARGET_EXPOSURE = 0.995
LOT_SIZE = 100
DEFENSIVE_MODE = 'benchmark_ma'
DEFENSIVE_BENCHMARK = '512800.XSHG'
DEFENSIVE_MA_DAYS = 252
DEFENSIVE_RISK_EXPOSURE = 0.5

def initialize(context):
    set_benchmark('512800.XSHG')
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    set_order_cost(OrderCost(open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    g.current_target = {}
    g.last_effective_exposure = None
    g.debug = True
    run_daily(rebalance_frozen_targets_if_signal_day, time='09:40')

def rebalance_frozen_targets_if_signal_day(context):
    current_date = context.current_dt.date().isoformat()
    is_signal_day = current_date in FROZEN_SIGNALS
    if is_signal_day:
        signal = FROZEN_SIGNALS[current_date]
        g.current_target = {code: weight for code, weight in signal}
        log.info('frozen rebalance date=%s selected=%s' % (current_date, ','.join(g.current_target.keys())))
    if not g.current_target:
        return
    defensive_state = get_defensive_state(context)
    effective_exposure = TARGET_EXPOSURE
    if defensive_state == 'risk_off':
        effective_exposure = TARGET_EXPOSURE * DEFENSIVE_RISK_EXPOSURE
    exposure_changed = (g.last_effective_exposure is None or abs(effective_exposure - g.last_effective_exposure) > 1e-12)
    if not is_signal_day and not exposure_changed:
        return
    log.info('defensive state=%s effective_exposure=%.4f signal_day=%s' % (defensive_state, effective_exposure, is_signal_day))
    execute_frozen_sells(context, g.current_target, effective_exposure)
    execute_frozen_buys(context, g.current_target, effective_exposure)
    g.last_effective_exposure = effective_exposure

def get_defensive_state(context):
    if DEFENSIVE_MODE != 'benchmark_ma':
        return 'risk_on'
    try:
        closes = get_price(
            DEFENSIVE_BENCHMARK,
            end_date=context.previous_date,
            count=DEFENSIVE_MA_DAYS,
            frequency='daily',
            fields=['close'],
            fq='pre',
            panel=False,
        )
        if closes is None or len(closes) < DEFENSIVE_MA_DAYS:
            return 'risk_on'
        last_close = float(closes['close'].iloc[-1])
        ma = float(closes['close'].mean())
        if ma <= 0:
            return 'risk_on'
        return 'risk_off' if last_close < ma else 'risk_on'
    except Exception as exc:
        log.info('defensive check failed %s' % str(exc))
        return 'risk_on'

def execute_frozen_sells(context, target_weights, effective_exposure):
    current_data = get_current_data()
    total_value = context.portfolio.total_value * effective_exposure
    target_codes = set(target_weights.keys())
    for stock in list(context.portfolio.positions.keys()):
        position = context.portfolio.positions[stock]
        if stock not in target_codes:
            order_lot_aware(context, current_data, stock, 0, 'sell_clear')
            continue
        target_value = total_value * float(target_weights[stock])
        current_value = position.value
        if current_value > target_value:
            order_lot_aware(context, current_data, stock, target_value, 'sell_trim')

def execute_frozen_buys(context, target_weights, effective_exposure):
    current_data = get_current_data()
    total_value = context.portfolio.total_value * effective_exposure
    for stock, weight in target_weights.items():
        target_value = total_value * float(weight)
        order_lot_aware(context, current_data, stock, target_value, 'buy_fill', weight, effective_exposure)

def order_lot_aware(context, current_data, stock, target_value, reason, weight=None, effective_exposure=None):
    try:
        data = current_data[stock]
        if data.paused:
            log.info('skip paused %s reason=%s' % (stock, reason))
            return
        if data.last_price >= data.high_limit or data.last_price <= data.low_limit:
            log.info('skip limit %s reason=%s last=%.4f high=%.4f low=%.4f' % (stock, reason, data.last_price, data.high_limit, data.low_limit))
            return
        price = float(data.last_price)
        if price <= 0:
            log.info('skip bad price %s reason=%s price=%.4f' % (stock, reason, price))
            return
        position = context.portfolio.positions[stock] if stock in context.portfolio.positions else None
        current_amount = int(position.total_amount) if position is not None else 0
        if target_value <= 0:
            target_amount = 0
        else:
            target_amount = int(target_value / price / LOT_SIZE) * LOT_SIZE
        delta = target_amount - current_amount
        if target_amount != 0 and abs(delta) < LOT_SIZE:
            log.info('skip lot delta %s reason=%s current=%d target=%d delta=%d' % (stock, reason, current_amount, target_amount, delta))
            return
        if target_amount == current_amount:
            log.info('skip unchanged %s reason=%s amount=%d' % (stock, reason, current_amount))
            return
        order_target(stock, target_amount)
        if g.debug:
            value = target_amount * price
            if weight is None:
                log.info('frozen order target %s amount=%d value=%.2f reason=%s' % (stock, target_amount, value, reason))
            else:
                exposure = TARGET_EXPOSURE if effective_exposure is None else effective_exposure
                log.info('frozen order target %s amount=%d value=%.2f weight=%.4f reason=%s exposure=%.4f' % (stock, target_amount, value, weight, reason, exposure))
    except Exception as exc:
        log.info('order failed %s reason=%s %s' % (stock, reason, str(exc)))

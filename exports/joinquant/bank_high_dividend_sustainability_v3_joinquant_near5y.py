from jqdata import *
from datetime import datetime, timedelta
from io import StringIO
import math

import numpy as np
import pandas as pd


"""
Bank Quant V5 - Bank High Dividend Sustainability V3 JoinQuant near-5-year file.

Purpose:
- Platform replication / engineering test for 2021-05-01 to 2026-05-31.
- This is not final research acceptance evidence.
- Do not tune after seeing JoinQuant results.
- Formal candidate guard is required. If bank-quality guard data is missing,
  the script must stop trading instead of silently degrading to no-guard.

Data policy:
- PB and ROE: JoinQuant get_fundamentals(date=factor_date).
- Dividend yield: embedded visible cash dividend table / pre-adjusted close.
- Bank quality: embedded V4 legacy bank_indicator bridge, using latest notice_date <= factor_date.
- The quality table is needs_check and requires source-date review before formal acceptance.
"""


def initialize(context):
    set_benchmark('512800.XSHG')
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    set_order_cost(
        OrderCost(open_commission=0.0003, close_commission=0.0003, min_commission=5),
        type='stock',
    )

    g.strategy_id = 'bank_high_dividend_sustainability_v3'
    g.script_version = 'v3_formal_candidate_guard_required_20260716'
    g.selection_count = 8
    g.max_position_weight = 0.15
    g.min_coverage_ratio = 0.80
    g.rebalance_months = [1, 4, 7, 10]
    g.executed_rebalance_keys = set()
    g.debug = True
    g.require_value_trap_guard = True

    g.bank_stocks = build_bank_stock_universe()
    g.quality_data = build_quality_data()
    g.dividend_events = build_dividend_events()
    g.last_used_factors = []
    quality_snapshot_count = sum(len(items) for items in g.quality_data.values())

    log.info('V3 formal candidate script=%s bank_universe=%d quality_codes=%d quality_snapshots=%d guard_required=%s' % (
        g.script_version,
        len(g.bank_stocks),
        len(g.quality_data),
        quality_snapshot_count,
        str(g.require_value_trap_guard),
    ))

    run_daily(maybe_rebalance, time='09:40')
    run_daily(after_trading_end_log, time='after_close')


def maybe_rebalance(context):
    current_date = context.current_dt.date()
    if current_date.month not in g.rebalance_months:
        return
    key = '%04d-%02d' % (current_date.year, current_date.month)
    if key in g.executed_rebalance_keys:
        return

    factor_date = get_previous_trade_date(context)
    stocks = get_tradable_bank_stocks(context, factor_date)
    reference_count = get_coverage_reference_count(factor_date)
    min_required = int(math.ceil(reference_count * g.min_coverage_ratio)) if reference_count > 0 else 0
    if reference_count > 0 and len(stocks) < min_required:
        log.info('skip rebalance coverage too low date=%s factor_date=%s tradable=%d required=%d reference=%d' % (
            str(current_date), str(factor_date), len(stocks), min_required, reference_count))
        return

    score_df = build_score_frame(stocks, factor_date)
    if score_df is None or len(score_df) == 0:
        log.info('empty score frame on %s factor_date=%s' % (str(current_date), str(factor_date)))
        clear_positions(context)
        g.executed_rebalance_keys.add(key)
        return

    guarded = apply_value_trap_guard(score_df)
    if len(guarded) == 0:
        log.info('no selected stocks after V3 value trap guard on %s' % str(current_date))
        clear_positions(context)
        g.executed_rebalance_keys.add(key)
        return

    selected = guarded.sort_values('final_score', ascending=False).head(g.selection_count)
    selected_codes = selected['code'].tolist()
    target_weight = min(g.max_position_weight, 0.995 / float(g.selection_count))

    log.info('V3 rebalance date=%s factor_date=%s candidates=%d guarded=%d selected=%s target_weight=%.4f' % (
        str(current_date), str(factor_date), len(score_df), len(guarded), ','.join(selected_codes), target_weight))
    if g.debug:
        log.info('V3 used factors on %s: %s' % (str(factor_date), ','.join(g.last_used_factors)))
        log.info('V3 score preview: %s' % build_score_preview(selected))

    execute_target_weights(context, selected_codes, target_weight)
    g.executed_rebalance_keys.add(key)


def build_score_frame(stocks, factor_date):
    valuation_df = fetch_valuation_snapshot(stocks, factor_date)
    indicator_df = fetch_indicator_snapshot(stocks, factor_date)
    quality_df = fetch_quality_snapshot(stocks, factor_date)
    dividend_df = fetch_dividend_yield_snapshot(stocks, factor_date)

    df = pd.DataFrame(index=stocks)
    df['code'] = df.index
    for source in [valuation_df, indicator_df, quality_df, dividend_df]:
        if source is None or len(source) == 0:
            continue
        for col in source.columns:
            if col == 'code':
                continue
            df[col] = pd.to_numeric(source[col], errors='coerce')

    if 'pb_ratio' in df.columns:
        df['low_price_to_book'] = df['pb_ratio']
    if 'roe' in df.columns:
        df['return_on_equity_ttm'] = df['roe']

    parts = []
    used = []
    add_score_part(df, parts, used, 'dividend_yield', 0.35, 1)
    add_score_part(df, parts, used, 'return_on_equity_ttm', 0.20, 1)
    add_score_part(df, parts, used, 'low_price_to_book', 0.20, -1)
    add_score_part(df, parts, used, 'provision_coverage_ratio', 0.15, 1)
    add_score_part(df, parts, used, 'core_tier_1_capital_adequacy_ratio', 0.10, 1)

    if not parts:
        return pd.DataFrame()

    df['final_score'] = weighted_average_parts(parts)
    df['factor_count'] = df[['adj__' + name for name in used]].notna().sum(axis=1)
    df = df.dropna(subset=['final_score']).copy()
    df = df[df['factor_count'] >= 3].copy()
    g.last_used_factors = used

    missing = [name for name in ['dividend_yield', 'return_on_equity_ttm', 'low_price_to_book', 'provision_coverage_ratio', 'core_tier_1_capital_adequacy_ratio'] if name not in used]
    if missing:
        log.info('V3 missing factors: %s' % ','.join(missing))
    return df


def add_score_part(df, parts, used, factor_name, weight, direction):
    if factor_name not in df.columns:
        return
    raw = pd.to_numeric(df[factor_name], errors='coerce')
    if raw.notna().sum() < 3:
        return
    z = zscore_series(winsorize_series(raw))
    adjusted = z * float(direction)
    if adjusted.notna().sum() < 3:
        return
    df['z__' + factor_name] = z
    df['adj__' + factor_name] = adjusted
    parts.append((factor_name, adjusted, float(weight)))
    used.append(factor_name)


def weighted_average_parts(parts):
    total_weight = sum(weight for _, _, weight in parts)
    if total_weight <= 0:
        return pd.Series(dtype=float)
    result = None
    for _, series, weight in parts:
        weighted = series * weight
        result = weighted if result is None else result + weighted
    return result / total_weight


def apply_value_trap_guard(score_df):
    required = ['non_performing_loan_ratio', 'provision_coverage_ratio', 'core_tier_1_capital_adequacy_ratio']
    if any(name not in score_df.columns for name in required):
        missing = [name for name in required if name not in score_df.columns]
        log.info('V3 FORMAL GUARD BLOCKED: missing quality fields=%s; no no-guard fallback allowed.' % ','.join(missing))
        return score_df.iloc[0:0].copy()
    quality = (-pd.to_numeric(score_df['non_performing_loan_ratio'], errors='coerce')
               + pd.to_numeric(score_df['provision_coverage_ratio'], errors='coerce')
               + pd.to_numeric(score_df['core_tier_1_capital_adequacy_ratio'], errors='coerce'))
    if quality.notna().sum() < 3:
        log.info('V3 FORMAL GUARD BLOCKED: insufficient quality values=%d; no no-guard fallback allowed.' % int(quality.notna().sum()))
        return score_df.iloc[0:0].copy()
    guarded = score_df.copy()
    guarded['quality_guard_score'] = quality
    threshold = guarded['quality_guard_score'].median()
    result = guarded[guarded['quality_guard_score'] >= threshold].copy()
    log.info('V3 formal value trap guard applied: candidates=%d guarded=%d threshold=%.4f' % (
        len(score_df),
        len(result),
        float(threshold),
    ))
    return result


def fetch_valuation_snapshot(stocks, factor_date):
    try:
        df = get_fundamentals(
            query(valuation.code, valuation.pb_ratio).filter(valuation.code.in_(stocks)),
            date=factor_date,
        )
        if df is None or len(df) == 0:
            return pd.DataFrame(index=stocks)
        return df.set_index('code')
    except Exception as exc:
        log.info('valuation fetch failed: %s' % str(exc))
        return pd.DataFrame(index=stocks)


def fetch_indicator_snapshot(stocks, factor_date):
    try:
        df = get_fundamentals(
            query(indicator.code, indicator.roe).filter(indicator.code.in_(stocks)),
            date=factor_date,
        )
        if df is None or len(df) == 0:
            return pd.DataFrame(index=stocks)
        return df.set_index('code')
    except Exception as exc:
        log.info('indicator fetch failed: %s' % str(exc))
        return pd.DataFrame(index=stocks)


def fetch_quality_snapshot(stocks, factor_date):
    result = pd.DataFrame(index=stocks)
    result['code'] = result.index
    date_value = to_date(factor_date)
    for stock in stocks:
        snapshots = g.quality_data.get(stock, [])
        selected = None
        for item in snapshots:
            if item.get('notice_date') is not None and item['notice_date'] <= date_value:
                selected = item
            else:
                break
        if selected is None:
            continue
        result.loc[stock, 'non_performing_loan_ratio'] = selected.get('npl_ratio')
        result.loc[stock, 'provision_coverage_ratio'] = selected.get('provision_coverage_ratio')
        result.loc[stock, 'core_tier_1_capital_adequacy_ratio'] = selected.get('core_tier_1_capital_adequacy_ratio')
    return result


def fetch_dividend_yield_snapshot(stocks, factor_date):
    result = pd.DataFrame(index=stocks)
    result['code'] = result.index
    date_value = to_date(factor_date)
    close_map = fetch_pre_adjusted_close(stocks, factor_date)
    start_date = date_value - timedelta(days=365)
    for stock in stocks:
        close = close_map.get(stock)
        if close is None or close <= 0:
            continue
        cash = 0.0
        for event in g.dividend_events.get(stock, []):
            if event['visible_date'] <= date_value and start_date < event['ex_date'] <= date_value:
                cash += event['cash_per_share']
        result.loc[stock, 'dividend_yield'] = cash / close
    return result


def fetch_pre_adjusted_close(stocks, factor_date):
    result = {}
    try:
        df = get_price(stocks, end_date=factor_date, count=1, frequency='daily', fields=['close'], fq='pre', panel=False)
        if df is None or len(df) == 0:
            return result
        if 'code' in df.columns:
            for _, row in df.iterrows():
                result[str(row['code'])] = safe_float(row['close'])
        elif len(stocks) == 1 and 'close' in df.columns:
            result[stocks[0]] = safe_float(df['close'].iloc[-1])
    except Exception as exc:
        log.info('pre-adjusted close fetch failed: %s' % str(exc))
    return result


def execute_target_weights(context, selected_codes, target_weight):
    selected_set = set(selected_codes)
    target_value = context.portfolio.total_value * float(target_weight)
    current_data = get_current_data()
    for stock in list(context.portfolio.positions.keys()):
        if stock not in selected_set:
            order_lot_aware(context, current_data, stock, 0, 'sell_clear')
    for stock in selected_codes:
        order_lot_aware(context, current_data, stock, target_value, 'buy_or_adjust', target_weight)


def order_lot_aware(context, current_data, stock, target_value, reason, target_weight=None):
    try:
        data = current_data[stock]
        if data.paused:
            log.info('skip paused %s reason=%s' % (stock, reason))
            return
        if data.is_st or 'ST' in data.name or '*' in data.name:
            log.info('skip ST %s reason=%s' % (stock, reason))
            return
        if data.last_price >= data.high_limit or data.last_price <= data.low_limit:
            log.info('skip limit %s reason=%s last=%.4f high=%.4f low=%.4f' % (stock, reason, data.last_price, data.high_limit, data.low_limit))
            return
        price = float(data.last_price)
        if price <= 0:
            return
        position = context.portfolio.positions[stock] if stock in context.portfolio.positions else None
        current_amount = int(position.total_amount) if position is not None else 0
        target_amount = 0 if target_value <= 0 else int(target_value / price / 100) * 100
        delta = target_amount - current_amount
        if target_amount != 0 and abs(delta) < 100:
            log.info('skip lot delta %s reason=%s current=%d target=%d delta=%d' % (stock, reason, current_amount, target_amount, delta))
            return
        if target_amount == current_amount:
            return
        order_target(stock, target_amount)
        if g.debug:
            value = target_amount * price
            if target_weight is None:
                log.info('V3 order target %s amount=%d value=%.2f reason=%s' % (stock, target_amount, value, reason))
            else:
                log.info('V3 order target %s amount=%d value=%.2f weight=%.4f reason=%s' % (stock, target_amount, value, target_weight, reason))
    except Exception as exc:
        log.info('order failed %s reason=%s %s' % (stock, reason, str(exc)))


def clear_positions(context):
    current_data = get_current_data()
    for stock in list(context.portfolio.positions.keys()):
        order_lot_aware(context, current_data, stock, 0, 'clear')


def get_tradable_bank_stocks(context, factor_date):
    all_securities = get_all_securities(['stock'], date=factor_date)
    current_data = get_current_data()
    result = []
    for stock in g.bank_stocks:
        if stock not in all_securities.index:
            continue
        try:
            start_date = all_securities.loc[stock, 'start_date']
            if (to_date(factor_date) - to_date(start_date)).days < 180:
                continue
            data = current_data[stock]
            if data.paused or data.is_st:
                continue
            if 'ST' in data.name or '*' in data.name:
                continue
            result.append(stock)
        except Exception:
            continue
    return result


def get_coverage_reference_count(factor_date):
    all_securities = get_all_securities(['stock'], date=factor_date)
    count = 0
    for stock in g.bank_stocks:
        if stock not in all_securities.index:
            continue
        try:
            start_date = all_securities.loc[stock, 'start_date']
            if (to_date(factor_date) - to_date(start_date)).days < 180:
                continue
            count += 1
        except Exception:
            continue
    return count


def get_previous_trade_date(context):
    try:
        return to_date(context.previous_date)
    except Exception:
        trade_days = get_trade_days(end_date=context.current_dt.date(), count=2)
        if trade_days is None or len(trade_days) == 0:
            return context.current_dt.date()
        return to_date(trade_days[0])


def build_bank_stock_universe():
    return [
        '000001.XSHE',
        '001227.XSHE',
        '002142.XSHE',
        '002807.XSHE',
        '002839.XSHE',
        '002936.XSHE',
        '002948.XSHE',
        '002958.XSHE',
        '002966.XSHE',
        '600000.XSHG',
        '600015.XSHG',
        '600016.XSHG',
        '600036.XSHG',
        '600908.XSHG',
        '600919.XSHG',
        '600926.XSHG',
        '600928.XSHG',
        '601009.XSHG',
        '601077.XSHG',
        '601128.XSHG',
        '601166.XSHG',
        '601169.XSHG',
        '601187.XSHG',
        '601229.XSHG',
        '601288.XSHG',
        '601328.XSHG',
        '601398.XSHG',
        '601528.XSHG',
        '601577.XSHG',
        '601658.XSHG',
        '601665.XSHG',
        '601818.XSHG',
        '601825.XSHG',
        '601838.XSHG',
        '601860.XSHG',
        '601916.XSHG',
        '601939.XSHG',
        '601963.XSHG',
        '601988.XSHG',
        '601997.XSHG',
        '601998.XSHG',
        '603323.XSHG'
    ]


QUALITY_CSV = """
code,source_year,notice_date,asset_quality_trend,provision_buffer,capital_resilience,npl_ratio,provision_coverage_ratio,core_tier_1_capital_adequacy_ratio
000001.XSHE,2019,2020-11-02,-1.65,183.12,9.11,1.65,183.12,9.11
000001.XSHE,2020,2021-05-06,0.47,201.4,8.69,1.18,201.4,8.69
000001.XSHE,2021,2022-05-05,0.15999999999999992,288.42,8.6,1.02,288.42,8.6
000001.XSHE,2022,2023-05-04,-0.030000000000000027,290.28,8.64,1.05,290.28,8.64
000001.XSHE,2023,2024-05-06,-0.010000000000000009,277.63,9.22,1.06,277.63,9.22
001227.XSHE,2022,2023-05-04,-1.71,194.99,8.47,1.71,194.99,8.47
001227.XSHE,2023,2024-05-06,-0.020000000000000018,197.51,8.41,1.73,197.51,8.41
002142.XSHE,2014,2015-05-04,-0.89,285.17,10.07,0.89,285.17,10.07
002142.XSHE,2015,2016-05-03,-0.030000000000000027,308.67,9.03,0.92,308.67,9.03
002142.XSHE,2016,2017-05-02,0.010000000000000009,351.42,8.55,0.91,351.42,8.55
002142.XSHE,2017,2018-05-02,0.09000000000000008,493.26,8.61,0.82,493.26,8.61
002142.XSHE,2018,2019-05-06,0.039999999999999925,521.83,9.16,0.78,521.83,9.16
002142.XSHE,2019,2020-05-06,0.0,524.08,9.62,0.78,524.08,9.62
002142.XSHE,2020,2021-05-06,-0.010000000000000009,505.59,9.52,0.79,505.59,9.52
002142.XSHE,2021,2022-05-05,0.020000000000000018,525.52,10.16,0.77,525.52,10.16
002142.XSHE,2022,2023-05-04,0.020000000000000018,504.9,9.75,0.75,504.9,9.75
002142.XSHE,2023,2024-05-06,-0.010000000000000009,461.04,9.64,0.76,461.04,9.64
002807.XSHE,2016,2017-05-02,-2.41,170.14,12.8,2.41,170.14,12.8
002807.XSHE,2017,2018-05-02,0.020000000000000018,192.13,12.94,2.39,192.13,12.94
002807.XSHE,2018,2019-05-06,0.2400000000000002,233.71,14.02,2.15,233.71,14.02
002807.XSHE,2019,2020-05-06,0.31999999999999984,259.13,14.16,1.83,259.13,14.16
002807.XSHE,2020,2021-05-06,0.040000000000000036,224.27,13.34,1.79,224.27,13.34
002807.XSHE,2021,2022-05-05,0.47,330.62,12.96,1.32,330.62,12.96
002807.XSHE,2022,2023-05-04,0.3400000000000001,469.62,12.77,0.98,469.62,12.77
002807.XSHE,2023,2024-05-06,0.0,409.46,13.1,0.98,409.46,13.1
002839.XSHE,2017,2018-05-02,-1.78,185.6,11.82,1.78,185.6,11.82
002839.XSHE,2018,2019-05-06,0.31000000000000005,223.85,11.94,1.47,223.85,11.94
002839.XSHE,2019,2020-05-06,0.09000000000000008,252.14,11.02,1.38,252.14,11.02
002839.XSHE,2020,2021-05-06,0.20999999999999996,307.83,10.35,1.17,307.83,10.35
002839.XSHE,2021,2022-05-05,0.21999999999999997,475.35,9.82,0.95,475.35,9.82
002839.XSHE,2022,2023-05-04,0.05999999999999994,521.09,9.36,0.89,521.09,9.36
002839.XSHE,2023,2024-05-06,-0.04999999999999993,424.23,9.76,0.94,424.23,9.76
002936.XSHE,2018,2019-05-06,-2.47,154.84,8.22,2.47,154.84,8.22
002936.XSHE,2019,2020-05-06,0.10000000000000009,159.85,7.98,2.37,159.85,7.98
002936.XSHE,2020,2021-05-06,0.29000000000000004,160.44,8.92,2.08,160.44,8.92
002936.XSHE,2021,2022-05-05,0.22999999999999998,156.58,9.49,1.85,156.58,9.49
002936.XSHE,2022,2023-05-04,-0.029999999999999805,165.73,9.29,1.88,165.73,9.29
002936.XSHE,2023,2024-05-06,0.009999999999999787,174.87,8.9,1.87,174.87,8.9
002948.XSHE,2019,2020-05-06,-1.65,155.09,8.36,1.65,155.09,8.36
002948.XSHE,2020,2021-05-06,0.1399999999999999,169.62,8.35,1.51,169.62,8.35
002948.XSHE,2021,2022-05-05,0.16999999999999993,197.42,8.38,1.34,197.42,8.38
002948.XSHE,2022,2023-05-04,0.13000000000000012,219.77,8.75,1.21,219.77,8.75
002948.XSHE,2023,2024-05-06,0.030000000000000027,225.96,8.42,1.18,225.96,8.42
002958.XSHE,2019,2020-05-06,-1.46,310.23,10.48,1.46,310.23,10.48
002958.XSHE,2020,2021-05-06,0.020000000000000018,278.73,9.73,1.44,278.73,9.73
002958.XSHE,2021,2022-05-05,-0.30000000000000004,231.77,9.62,1.74,231.77,9.62
002958.XSHE,2022,2023-05-04,-0.44999999999999996,207.63,9.77,2.19,207.63,9.77
002958.XSHE,2023,2024-05-06,0.3799999999999999,237.96,9.91,1.81,237.96,9.91
002966.XSHE,2019,2020-05-06,-1.53,224.07,11.3,1.53,224.07,11.3
002966.XSHE,2020,2021-05-06,0.15000000000000013,291.74,11.26,1.38,291.74,11.26
002966.XSHE,2021,2022-05-05,0.2699999999999998,422.91,10.37,1.11,422.91,10.37
002966.XSHE,2022,2023-05-04,0.2300000000000001,530.81,9.63,0.88,530.81,9.63
002966.XSHE,2023,2024-05-06,0.040000000000000036,522.77,9.38,0.84,522.77,9.38
600000.XSHG,2013,2014-05-05,-0.74,319.65,8.58,0.74,319.65,8.58
600000.XSHG,2014,2015-04-29,-0.32000000000000006,249.09,8.61,1.06,249.09,8.61
600000.XSHG,2015,2016-04-29,-0.5,211.4,8.56,1.56,211.4,8.56
600000.XSHG,2016,2017-05-02,-0.32999999999999985,169.13,8.53,1.89,169.13,8.53
600000.XSHG,2017,2018-05-02,-0.2500000000000002,132.44,9.5,2.14,132.44,9.5
600000.XSHG,2018,2019-05-06,0.2400000000000002,156.08,10.09,1.9,156.08,10.09
600000.XSHG,2019,2020-05-06,-0.1299999999999999,134.94,10.26,2.03,134.94,10.26
600000.XSHG,2020,2021-05-06,0.2999999999999998,152.77,9.51,1.73,152.77,9.51
600000.XSHG,2021,2022-05-05,0.11999999999999988,143.96,9.4,1.61,143.96,9.4
600000.XSHG,2022,2023-05-04,0.09000000000000008,159.04,9.19,1.52,159.04,9.19
600000.XSHG,2023,2024-05-06,0.040000000000000036,173.51,8.97,1.48,173.51,8.97
600015.XSHG,2013,2014-05-05,-0.9,301.53,8.03,0.9,301.53,8.03
600015.XSHG,2014,2015-04-29,-0.19000000000000006,233.13,8.49,1.09,233.13,8.49
600015.XSHG,2015,2016-04-29,-0.42999999999999994,167.12,8.89,1.52,167.12,8.89
600015.XSHG,2016,2017-05-02,-0.1499999999999999,158.73,8.43,1.67,158.73,8.43
600015.XSHG,2017,2018-05-02,-0.09000000000000008,156.51,8.26,1.76,156.51,8.26
600015.XSHG,2018,2019-05-06,-0.09000000000000008,158.59,9.47,1.85,158.59,9.47
600015.XSHG,2019,2020-05-06,0.020000000000000018,141.92,9.25,1.83,141.92,9.25
600015.XSHG,2020,2021-05-06,0.030000000000000027,147.22,8.79,1.8,147.22,8.79
600015.XSHG,2021,2022-05-05,0.030000000000000027,150.99,8.78,1.77,150.99,8.78
600015.XSHG,2022,2023-05-04,0.020000000000000018,159.88,9.24,1.75,159.88,9.24
600015.XSHG,2023,2024-05-06,0.08000000000000007,160.06,9.16,1.67,160.06,9.16
600016.XSHG,2013,2014-05-05,-0.85,259.74,8.72,0.85,259.74,8.72
600016.XSHG,2014,2015-05-04,-0.31999999999999995,182.2,8.58,1.17,182.2,8.58
600016.XSHG,2015,2016-04-29,-0.43000000000000016,153.63,9.17,1.6,153.63,9.17
600016.XSHG,2016,2017-05-02,-0.07999999999999985,155.41,8.95,1.68,155.41,8.95
600016.XSHG,2017,2018-05-02,-0.030000000000000027,155.61,8.63,1.71,155.61,8.63
600016.XSHG,2018,2019-05-06,-0.050000000000000044,134.05,8.93,1.76,134.05,8.93
600016.XSHG,2019,2020-05-06,0.19999999999999996,155.5,8.89,1.56,155.5,8.89
600016.XSHG,2020,2021-05-06,-0.26,139.38,8.51,1.82,139.38,8.51
600016.XSHG,2021,2022-05-05,0.030000000000000027,145.3,9.04,1.79,145.3,9.04
600016.XSHG,2022,2023-05-04,0.1100000000000001,142.49,9.17,1.68,142.49,9.17
600016.XSHG,2023,2024-05-06,0.19999999999999996,149.69,9.28,1.48,149.69,9.28
600036.XSHG,2013,2014-05-05,-0.83,266.0,9.27,0.83,266.0,9.27
600036.XSHG,2014,2015-04-29,-0.28000000000000014,233.42,10.44,1.11,233.42,10.44
600036.XSHG,2015,2016-04-29,-0.5699999999999998,178.95,10.83,1.68,178.95,10.83
600036.XSHG,2016,2017-05-02,-0.19000000000000017,180.02,11.54,1.87,180.02,11.54
600036.XSHG,2017,2018-05-02,0.26,262.11,12.06,1.61,262.11,12.06
600036.XSHG,2018,2019-05-06,0.25,358.18,11.78,1.36,358.18,11.78
600036.XSHG,2019,2020-05-06,0.20000000000000018,426.78,11.95,1.16,426.78,11.95
600036.XSHG,2020,2021-05-06,0.08999999999999986,437.68,12.29,1.07,437.68,12.29
600036.XSHG,2021,2022-05-05,0.16000000000000003,483.87,12.66,0.91,483.87,12.66
600036.XSHG,2022,2023-05-04,-0.04999999999999993,450.79,13.68,0.96,450.79,13.68
600036.XSHG,2023,2024-05-06,0.010000000000000009,437.7,13.73,0.95,437.7,13.73
600908.XSHG,2016,2017-05-02,-1.39,200.77,10.28,1.39,200.77,10.28
600908.XSHG,2017,2018-05-02,0.010000000000000009,193.77,9.93,1.38,193.77,9.93
600908.XSHG,2018,2019-05-06,0.1399999999999999,234.76,10.44,1.24,234.76,10.44
600908.XSHG,2019,2020-05-06,0.030000000000000027,288.18,10.2,1.21,288.18,10.2
600908.XSHG,2020,2021-05-06,0.10999999999999988,355.88,9.03,1.1,355.88,9.03
600908.XSHG,2021,2022-05-05,0.17000000000000004,477.19,8.74,0.93,477.19,8.74
600908.XSHG,2022,2023-05-04,0.12,552.74,10.97,0.81,552.74,10.97
600908.XSHG,2023,2024-05-06,0.020000000000000018,522.57,11.27,0.79,522.57,11.27
600919.XSHG,2016,2017-05-02,-1.43,180.56,9.01,1.43,180.56,9.01
600919.XSHG,2017,2018-05-02,0.020000000000000018,184.25,8.54,1.41,184.25,8.54
600919.XSHG,2018,2019-05-06,0.020000000000000018,203.84,8.61,1.39,203.84,8.61
600919.XSHG,2019,2020-05-06,0.010000000000000009,232.79,8.59,1.38,232.79,8.59
600919.XSHG,2020,2021-05-06,0.05999999999999983,256.4,9.25,1.32,256.4,9.25
600919.XSHG,2021,2022-05-05,0.24,318.93,8.78,1.08,318.93,8.78
600919.XSHG,2022,2023-05-04,0.14000000000000012,371.66,8.79,0.94,371.66,8.79
600919.XSHG,2023,2024-05-06,0.04999999999999993,389.53,9.46,0.89,389.53,9.46
600926.XSHG,2016,2017-05-02,-1.62,186.76,9.95,1.62,186.76,9.95
600926.XSHG,2017,2018-05-02,0.030000000000000027,211.03,8.69,1.59,211.03,8.69
600926.XSHG,2019,2020-05-06,-1.34,316.71,8.08,1.34,316.71,8.08
600926.XSHG,2020,2021-05-06,0.27,469.54,8.53,1.07,469.54,8.53
600926.XSHG,2021,2022-05-05,0.21000000000000008,567.71,8.43,0.86,567.71,8.43
600926.XSHG,2022,2023-05-04,0.08999999999999997,565.1,8.08,0.77,565.1,8.08
600926.XSHG,2023,2024-05-06,0.010000000000000009,561.42,8.16,0.76,561.42,8.16
600928.XSHG,2019,2020-05-06,-1.18,262.41,12.62,1.18,262.41,12.62
600928.XSHG,2020,2021-05-06,0.0,269.39,12.37,1.18,269.39,12.37
600928.XSHG,2021,2022-05-05,-0.14000000000000012,224.21,12.09,1.32,224.21,12.09
600928.XSHG,2022,2023-05-04,0.07000000000000006,201.63,10.48,1.25,201.63,10.48
600928.XSHG,2023,2024-05-06,-0.10000000000000009,197.07,10.73,1.35,197.07,10.73
601009.XSHG,2013,2014-05-05,-0.89,298.51,10.1,0.89,298.51,10.1
601009.XSHG,2014,2015-05-04,-0.04999999999999993,325.72,8.59,0.94,325.72,8.59
601009.XSHG,2015,2016-05-03,0.10999999999999999,430.95,9.38,0.83,430.95,9.38
601009.XSHG,2016,2017-05-02,-0.040000000000000036,457.32,8.21,0.87,457.32,8.21
601009.XSHG,2017,2018-05-02,0.010000000000000009,462.54,7.99,0.86,462.54,7.99
601009.XSHG,2018,2019-05-06,-0.030000000000000027,462.68,8.51,0.89,462.68,8.51
601009.XSHG,2019,2020-05-06,0.0,417.73,8.87,0.89,417.73,8.87
601009.XSHG,2020,2021-05-06,-0.020000000000000018,391.76,9.97,0.91,391.76,9.97
601009.XSHG,2021,2022-05-05,0.0,397.34,10.16,0.91,397.34,10.16
601009.XSHG,2022,2023-05-04,0.010000000000000009,397.2,9.73,0.9,397.2,9.73
601009.XSHG,2023,2024-05-06,0.0,360.58,9.39,0.9,360.58,9.39
601077.XSHG,2019,2020-05-06,-1.25,380.31,12.42,1.25,380.31,12.42
601077.XSHG,2020,2021-05-06,-0.06000000000000005,314.95,11.96,1.31,314.95,11.96
601077.XSHG,2021,2022-05-05,0.06000000000000005,340.25,12.47,1.25,340.25,12.47
601077.XSHG,2022,2023-05-04,0.030000000000000027,357.74,13.1,1.22,357.74,13.1
601077.XSHG,2023,2024-05-06,0.030000000000000027,366.7,13.53,1.19,366.7,13.53
601128.XSHG,2016,2017-05-02,-1.4,234.83,10.9,1.4,234.83,10.9
601128.XSHG,2017,2018-05-02,0.26,325.93,9.88,1.14,325.93,9.88
601128.XSHG,2018,2019-05-06,0.1499999999999999,445.02,10.49,0.99,445.02,10.49
601128.XSHG,2019,2020-05-06,0.030000000000000027,481.28,12.44,0.96,481.28,12.44
601128.XSHG,2020,2021-05-06,0.0,485.33,11.08,0.96,485.33,11.08
601128.XSHG,2021,2022-05-05,0.1499999999999999,531.82,10.21,0.81,531.82,10.21
601128.XSHG,2022,2023-05-04,0.0,536.77,10.21,0.81,536.77,10.21
601128.XSHG,2023,2024-05-06,0.06000000000000005,537.88,10.42,0.75,537.88,10.42
601166.XSHG,2013,2014-05-05,-0.76,352.1,8.68,0.76,352.1,8.68
601166.XSHG,2014,2015-05-04,-0.3400000000000001,250.21,8.45,1.1,250.21,8.45
601166.XSHG,2015,2016-05-03,-0.3599999999999999,210.08,8.43,1.46,210.08,8.43
601166.XSHG,2016,2017-05-02,-0.18999999999999995,210.51,8.55,1.65,210.51,8.55
601166.XSHG,2017,2018-05-02,0.05999999999999983,211.78,9.07,1.59,211.78,9.07
601166.XSHG,2018,2019-05-06,0.020000000000000018,207.28,9.3,1.57,207.28,9.3
601166.XSHG,2019,2020-05-06,0.030000000000000027,199.13,9.47,1.54,199.13,9.47
601166.XSHG,2020,2021-05-06,0.29000000000000004,218.83,9.33,1.25,218.83,9.33
601166.XSHG,2021,2022-05-05,0.1499999999999999,268.73,9.81,1.1,268.73,9.81
601166.XSHG,2022,2023-05-04,0.010000000000000009,236.44,9.81,1.09,236.44,9.81
601166.XSHG,2023,2024-05-06,0.020000000000000018,245.21,9.76,1.07,245.21,9.76
601169.XSHG,2013,2014-05-05,-0.65,385.91,8.81,0.65,385.91,8.81
601169.XSHG,2014,2015-05-04,-0.20999999999999996,324.22,9.16,0.86,324.22,9.16
601169.XSHG,2015,2016-04-29,-0.2600000000000001,278.39,8.76,1.12,278.39,8.76
601169.XSHG,2016,2017-05-02,-0.1499999999999999,256.06,8.26,1.27,256.06,8.26
601169.XSHG,2017,2018-05-02,0.030000000000000027,265.57,8.92,1.24,265.57,8.92
601169.XSHG,2018,2019-05-06,-0.21999999999999997,217.51,8.93,1.46,217.51,8.93
601169.XSHG,2019,2020-05-06,0.06000000000000005,224.69,9.22,1.4,224.69,9.22
601169.XSHG,2020,2021-05-06,-0.17000000000000015,215.95,9.42,1.57,215.95,9.42
601169.XSHG,2021,2022-05-05,0.13000000000000012,210.22,9.86,1.44,210.22,9.86
601169.XSHG,2022,2023-05-04,0.010000000000000009,210.04,9.54,1.43,210.04,9.54
601169.XSHG,2023,2024-05-06,0.10999999999999988,216.78,9.21,1.32,216.78,9.21
601187.XSHG,2020,2021-05-06,-0.98,368.03,11.34,0.98,368.03,11.34
601187.XSHG,2021,2022-05-05,0.06999999999999995,370.64,10.47,0.91,370.64,10.47
601187.XSHG,2022,2023-05-04,0.050000000000000044,387.93,9.5,0.86,387.93,9.5
601187.XSHG,2023,2024-05-06,0.09999999999999998,412.89,9.86,0.76,412.89,9.86
601229.XSHG,2016,2017-05-02,-1.17,255.5,11.13,1.17,255.5,11.13
601229.XSHG,2017,2018-05-02,0.020000000000000018,272.52,10.69,1.15,272.52,10.69
601229.XSHG,2018,2019-05-06,0.010000000000000009,332.95,9.83,1.14,332.95,9.83
601229.XSHG,2019,2020-05-06,-0.020000000000000018,337.15,9.66,1.16,337.15,9.66
601229.XSHG,2020,2021-05-06,-0.06000000000000005,321.38,9.34,1.22,321.38,9.34
601229.XSHG,2021,2022-05-05,-0.030000000000000027,301.13,8.95,1.25,301.13,8.95
601229.XSHG,2022,2023-05-04,0.0,291.61,9.14,1.25,291.61,9.14
601229.XSHG,2023,2024-05-06,0.040000000000000036,272.66,9.53,1.21,272.66,9.53
601288.XSHG,2013,2014-05-05,-1.22,367.04,9.25,1.22,367.04,9.25
601288.XSHG,2014,2015-04-29,-0.32000000000000006,286.53,9.09,1.54,286.53,9.09
601288.XSHG,2015,2016-04-29,-0.8500000000000001,189.43,10.24,2.39,189.43,10.24
601288.XSHG,2016,2017-05-02,0.020000000000000018,173.4,10.38,2.37,173.4,10.38
601288.XSHG,2017,2018-05-02,0.56,208.37,10.63,1.81,208.37,10.63
601288.XSHG,2018,2019-05-06,0.21999999999999997,252.18,11.55,1.59,252.18,11.55
601288.XSHG,2019,2020-05-06,0.19000000000000017,295.45,11.24,1.4,295.45,11.24
601288.XSHG,2020,2021-05-06,-0.17000000000000015,266.2,11.04,1.57,266.2,11.04
601288.XSHG,2021,2022-05-05,0.14000000000000012,299.73,11.44,1.43,299.73,11.44
601288.XSHG,2022,2023-05-04,0.05999999999999983,302.6,11.15,1.37,302.6,11.15
601288.XSHG,2023,2024-05-06,0.040000000000000036,303.87,10.72,1.33,303.87,10.72
601328.XSHG,2013,2014-05-05,-1.05,213.65,9.76,1.05,213.65,9.76
601328.XSHG,2014,2015-04-29,-0.19999999999999996,178.88,11.3,1.25,178.88,11.3
601328.XSHG,2015,2016-04-29,-0.26,155.57,11.14,1.51,155.57,11.14
601328.XSHG,2016,2017-05-02,0.010000000000000009,153.61,11.0,1.5,153.61,11.0
601328.XSHG,2017,2018-05-02,0.0,154.73,10.79,1.5,154.73,10.79
601328.XSHG,2018,2019-05-06,0.010000000000000009,173.13,11.16,1.49,173.13,11.16
601328.XSHG,2019,2020-05-06,0.020000000000000018,171.77,11.22,1.47,171.77,11.22
601328.XSHG,2020,2021-05-06,-0.19999999999999996,143.87,10.87,1.67,143.87,10.87
601328.XSHG,2021,2022-05-05,0.18999999999999995,166.5,10.62,1.48,166.5,10.62
601328.XSHG,2022,2023-05-04,0.1299999999999999,180.68,10.06,1.35,180.68,10.06
601328.XSHG,2023,2024-05-06,0.020000000000000018,195.21,10.23,1.33,195.21,10.23
601398.XSHG,2013,2014-05-05,-0.94,257.19,10.57,0.94,257.19,10.57
601398.XSHG,2014,2015-04-29,-0.18999999999999995,206.9,11.92,1.13,206.9,11.92
601398.XSHG,2015,2016-04-29,-0.3700000000000001,156.34,12.87,1.5,156.34,12.87
601398.XSHG,2016,2017-05-02,-0.1200000000000001,136.69,12.87,1.62,136.69,12.87
601398.XSHG,2017,2018-05-02,0.07000000000000006,154.07,12.77,1.55,154.07,12.77
601398.XSHG,2018,2019-05-06,0.030000000000000027,175.76,12.98,1.52,175.76,12.98
601398.XSHG,2019,2020-05-06,0.09000000000000008,199.32,13.2,1.43,199.32,13.2
601398.XSHG,2020,2021-05-06,-0.15000000000000013,180.68,13.18,1.58,180.68,13.18
601398.XSHG,2021,2022-05-05,0.16000000000000014,205.84,13.31,1.42,205.84,13.31
601398.XSHG,2022,2023-05-04,0.040000000000000036,209.47,14.04,1.38,209.47,14.04
601398.XSHG,2023,2024-05-06,0.019999999999999796,213.97,13.72,1.36,213.97,13.72
601528.XSHG,2021,2022-05-05,-1.25,252.9,15.41,1.25,252.9,15.41
601528.XSHG,2022,2023-05-04,0.16999999999999993,280.5,14.42,1.08,280.5,14.42
601528.XSHG,2023,2024-05-06,0.1100000000000001,304.12,12.68,0.97,304.12,12.68
601577.XSHG,2018,2019-05-06,-1.29,275.4,9.53,1.29,275.4,9.53
601577.XSHG,2019,2020-05-06,0.07000000000000006,279.98,9.16,1.22,279.98,9.16
601577.XSHG,2020,2021-05-06,0.010000000000000009,292.68,8.61,1.21,292.68,8.61
601577.XSHG,2021,2022-05-05,0.010000000000000009,297.87,9.69,1.2,297.87,9.69
601577.XSHG,2022,2023-05-04,0.040000000000000036,311.09,9.7,1.16,311.09,9.7
601577.XSHG,2023,2024-05-06,0.010000000000000009,314.21,9.59,1.15,314.21,9.59
601658.XSHG,2019,2020-05-06,-0.86,389.45,9.9,0.86,389.45,9.9
601658.XSHG,2020,2021-05-06,-0.020000000000000018,408.06,9.6,0.88,408.06,9.6
601658.XSHG,2021,2022-05-05,0.06000000000000005,418.61,9.92,0.82,418.61,9.92
601658.XSHG,2022,2023-05-04,-0.020000000000000018,385.51,9.36,0.84,385.51,9.36
601658.XSHG,2023,2024-05-06,0.010000000000000009,347.57,9.53,0.83,347.57,9.53
601665.XSHG,2021,2022-05-05,-1.35,253.95,9.65,1.35,253.95,9.65
601665.XSHG,2022,2023-05-04,0.06000000000000005,281.06,9.56,1.29,281.06,9.56
601665.XSHG,2023,2024-05-06,0.030000000000000027,303.58,10.16,1.26,303.58,10.16
601818.XSHG,2013,2014-05-05,-0.86,241.02,9.11,0.86,241.02,9.11
601818.XSHG,2014,2015-04-29,-0.32999999999999996,180.52,9.34,1.19,180.52,9.34
601818.XSHG,2015,2016-04-29,-0.42000000000000015,156.39,9.24,1.61,156.39,9.24
601818.XSHG,2016,2017-05-02,0.010000000000000009,152.02,8.21,1.6,152.02,8.21
601818.XSHG,2017,2018-05-02,0.010000000000000009,158.18,9.56,1.59,158.18,9.56
601818.XSHG,2018,2019-05-06,0.0,176.16,9.15,1.59,176.16,9.15
601818.XSHG,2019,2020-05-06,0.030000000000000027,181.62,9.2,1.56,181.62,9.2
601818.XSHG,2020,2021-05-06,0.18000000000000016,182.71,9.02,1.38,182.71,9.02
601818.XSHG,2021,2022-05-05,0.1299999999999999,187.02,8.91,1.25,187.02,8.91
601818.XSHG,2022,2023-05-04,0.0,187.93,8.72,1.25,187.93,8.72
601818.XSHG,2023,2024-05-06,0.0,181.27,9.18,1.25,181.27,9.18
601825.XSHG,2021,2022-05-05,-0.95,442.5,13.06,0.95,442.5,13.06
601825.XSHG,2022,2023-05-04,0.010000000000000009,445.32,12.96,0.94,445.32,12.96
601825.XSHG,2023,2024-05-06,-0.030000000000000027,404.98,13.32,0.97,404.98,13.32
601838.XSHG,2018,2019-05-06,-1.54,237.01,11.14,1.54,237.01,11.14
601838.XSHG,2019,2020-05-06,0.1100000000000001,253.88,10.13,1.43,253.88,10.13
601838.XSHG,2020,2021-05-06,0.05999999999999983,293.43,9.26,1.37,293.43,9.26
601838.XSHG,2021,2022-05-05,0.3900000000000001,402.88,8.7,0.98,402.88,8.7
601838.XSHG,2022,2023-05-04,0.19999999999999996,501.57,8.47,0.78,501.57,8.47
601838.XSHG,2023,2024-05-06,0.09999999999999998,504.29,8.22,0.68,504.29,8.22
601916.XSHG,2019,2020-05-06,-1.37,220.8,9.64,1.37,220.8,9.64
601916.XSHG,2020,2021-05-06,-0.04999999999999982,191.01,8.75,1.42,191.01,8.75
601916.XSHG,2021,2022-05-05,-0.1100000000000001,174.61,8.13,1.53,174.61,8.13
601916.XSHG,2022,2023-05-04,0.06000000000000005,182.19,8.05,1.47,182.19,8.05
601916.XSHG,2023,2024-05-06,0.030000000000000027,182.6,8.22,1.44,182.6,8.22
601939.XSHG,2013,2014-05-05,-0.99,268.22,10.75,0.99,268.22,10.75
601939.XSHG,2014,2015-04-29,-0.19999999999999996,222.33,12.11,1.19,222.33,12.11
601939.XSHG,2015,2016-04-29,-0.3900000000000001,150.99,13.13,1.58,150.99,13.13
601939.XSHG,2016,2017-05-02,0.06000000000000005,150.36,12.98,1.52,150.36,12.98
601939.XSHG,2017,2018-05-02,0.030000000000000027,171.08,13.09,1.49,171.08,13.09
601939.XSHG,2018,2019-05-06,0.030000000000000027,208.37,13.83,1.46,208.37,13.83
601939.XSHG,2019,2020-05-06,0.040000000000000036,227.69,13.88,1.42,227.69,13.88
601939.XSHG,2020,2021-05-06,-0.14000000000000012,213.59,13.62,1.56,213.59,13.62
601939.XSHG,2021,2022-05-05,0.14000000000000012,239.96,13.59,1.42,239.96,13.59
601939.XSHG,2022,2023-05-04,0.040000000000000036,241.53,13.69,1.38,241.53,13.69
601939.XSHG,2023,2024-05-06,0.009999999999999787,239.85,13.15,1.37,239.85,13.15
601963.XSHG,2021,2022-05-05,-1.3,274.01,9.36,1.3,274.01,9.36
601963.XSHG,2022,2023-05-04,-0.07999999999999985,211.19,9.52,1.38,211.19,9.52
601963.XSHG,2023,2024-05-06,0.039999999999999813,234.18,9.78,1.34,234.18,9.78
601988.XSHG,2013,2014-05-05,-0.96,229.35,9.69,0.96,229.35,9.69
601988.XSHG,2014,2015-04-29,-0.21999999999999997,187.6,10.61,1.18,187.6,10.61
601988.XSHG,2015,2016-05-03,-0.25,153.3,11.1,1.43,153.3,11.1
601988.XSHG,2016,2017-05-02,-0.030000000000000027,162.82,11.37,1.46,162.82,11.37
601988.XSHG,2017,2018-05-02,0.010000000000000009,159.18,11.15,1.45,159.18,11.15
601988.XSHG,2018,2019-05-06,0.030000000000000027,181.97,11.41,1.42,181.97,11.41
601988.XSHG,2019,2020-05-06,0.04999999999999982,182.86,11.3,1.37,182.86,11.3
601988.XSHG,2020,2021-05-06,-0.08999999999999986,177.84,11.28,1.46,177.84,11.28
601988.XSHG,2021,2022-05-05,0.1299999999999999,187.05,11.3,1.33,187.05,11.3
601988.XSHG,2022,2023-05-04,0.010000000000000009,188.73,11.84,1.32,188.73,11.84
601988.XSHG,2023,2024-05-06,0.050000000000000044,191.66,11.63,1.27,191.66,11.63
601997.XSHG,2016,2017-05-02,-1.42,235.19,11.51,1.42,235.19,11.51
601997.XSHG,2017,2018-05-02,0.07999999999999985,269.72,9.54,1.34,269.72,9.54
601997.XSHG,2018,2019-05-06,-0.010000000000000009,266.05,9.61,1.35,266.05,9.61
601997.XSHG,2019,2020-05-06,-0.09999999999999987,291.86,9.39,1.45,291.86,9.39
601997.XSHG,2020,2021-05-06,-0.08000000000000007,277.3,9.3,1.53,277.3,9.3
601997.XSHG,2021,2022-05-05,0.08000000000000007,271.03,10.62,1.45,271.03,10.62
601997.XSHG,2022,2023-05-04,0.0,260.86,10.95,1.45,260.86,10.95
601997.XSHG,2023,2024-05-06,-0.14000000000000012,244.5,11.84,1.59,244.5,11.84
601998.XSHG,2013,2014-05-05,-1.03,206.62,8.78,1.03,206.62,8.78
601998.XSHG,2014,2015-05-04,-0.27,181.26,8.93,1.3,181.26,8.93
601998.XSHG,2015,2016-05-03,-0.1299999999999999,167.81,9.12,1.43,167.81,9.12
601998.XSHG,2016,2017-05-02,-0.26,155.5,8.64,1.69,155.5,8.64
601998.XSHG,2017,2018-05-02,0.010000000000000009,169.44,8.49,1.68,169.44,8.49
601998.XSHG,2018,2019-05-06,-0.09000000000000008,157.98,8.62,1.77,157.98,8.62
601998.XSHG,2019,2020-05-06,0.1200000000000001,175.25,8.69,1.65,175.25,8.69
601998.XSHG,2020,2021-05-06,0.010000000000000009,171.68,8.74,1.64,171.68,8.74
601998.XSHG,2021,2022-05-05,0.25,180.07,8.85,1.39,180.07,8.85
601998.XSHG,2022,2023-05-04,0.11999999999999988,201.19,8.74,1.27,201.19,8.74
601998.XSHG,2023,2024-05-06,0.09000000000000008,207.59,8.99,1.18,207.59,8.99
603323.XSHG,2016,2017-05-02,-1.78,187.46,13.04,1.78,187.46,13.04
603323.XSHG,2017,2018-05-02,0.14000000000000012,201.5,12.27,1.64,201.5,12.27
603323.XSHG,2018,2019-05-06,0.32999999999999985,248.18,10.99,1.31,248.18,10.99
603323.XSHG,2019,2020-05-06,-0.020000000000000018,249.32,12.17,1.33,249.32,12.17
603323.XSHG,2020,2021-05-06,0.050000000000000044,305.31,11.38,1.28,305.31,11.38
603323.XSHG,2021,2022-05-05,0.28,412.22,10.72,1.0,412.22,10.72
603323.XSHG,2022,2023-05-04,0.050000000000000044,442.83,10.17,0.95,442.83,10.17
603323.XSHG,2023,2024-05-06,0.039999999999999925,452.85,10.19,0.91,452.85,10.19
"""


DIVIDEND_CSV = """
code,announce_date,ex_date,cash_per_share
002807.XSHE,2021-05-07,2021-05-13,0.18
000001.XSHE,2021-05-07,2021-05-14,0.18
601128.XSHG,2021-05-19,2021-05-26,0.2
002966.XSHE,2021-05-21,2021-05-27,0.24
002948.XSHE,2021-05-21,2021-05-28,0.18
601009.XSHG,2021-05-29,2021-06-04,0.393
601988.XSHG,2021-05-28,2021-06-04,0.197
603323.XSHG,2021-06-01,2021-06-08,0.15
601860.XSHG,2021-06-07,2021-06-15,0.1
601288.XSHG,2021-06-08,2021-06-17,0.1851
600919.XSHG,2021-06-10,2021-06-18,0.316
600928.XSHG,2021-06-10,2021-06-18,0.19
601997.XSHG,2021-06-16,2021-06-23,0.3
600016.XSHG,2021-06-18,2021-06-24,0.213
600926.XSHG,2021-06-18,2021-06-25,0.35
601838.XSHG,2021-06-22,2021-06-28,0.46
601077.XSHG,2021-06-21,2021-06-29,0.222
601166.XSHG,2021-06-23,2021-06-29,0.802
600908.XSHG,2021-06-29,2021-07-06,0.18
601229.XSHG,2021-06-30,2021-07-06,0.4
601398.XSHG,2021-06-29,2021-07-06,0.266
002958.XSHE,2021-06-30,2021-07-07,0.15
002839.XSHE,2021-07-02,2021-07-08,0.16
002142.XSHE,2021-07-01,2021-07-09,0.5
600015.XSHG,2021-07-05,2021-07-09,0.301
601963.XSHG,2021-07-05,2021-07-09,0.373
601577.XSHG,2021-07-06,2021-07-12,0.32
600036.XSHG,2021-07-06,2021-07-13,1.253
601328.XSHG,2021-07-07,2021-07-13,0.317
601939.XSHG,2021-07-07,2021-07-15,0.326
601169.XSHG,2021-07-08,2021-07-16,0.3
600000.XSHG,2021-07-13,2021-07-21,0.48
601818.XSHG,2021-07-13,2021-07-21,0.21
601187.XSHG,2021-07-16,2021-07-22,0.18
601658.XSHG,2021-07-14,2021-07-22,0.2085
601998.XSHG,2021-07-22,2021-07-29,0.254
601916.XSHG,2021-07-24,2021-07-30,0.161
601665.XSHG,2021-08-16,2021-08-20,0.18
601825.XSHG,2021-11-27,2021-12-03,0.26
002839.XSHE,2022-04-26,2022-05-05,0.16
601528.XSHG,2022-04-29,2022-05-10,0.18
002966.XSHE,2022-04-30,2022-05-11,0.28
002807.XSHE,2022-05-07,2022-05-13,0.18
600919.XSHG,2022-05-20,2022-05-26,0.4
002948.XSHE,2022-05-24,2022-05-31,0.16
600015.XSHG,2022-05-30,2022-06-08,0.338
601128.XSHG,2022-05-31,2022-06-08,0.2
601997.XSHG,2022-06-01,2022-06-09,0.3
601860.XSHG,2022-06-07,2022-06-13,0.1
601166.XSHG,2022-06-09,2022-06-16,1.035
603323.XSHG,2022-06-08,2022-06-16,0.16
601009.XSHG,2022-06-09,2022-06-17,0.46162
600928.XSHG,2022-06-13,2022-06-20,0.19
601187.XSHG,2022-06-14,2022-06-21,0.25
600016.XSHG,2022-06-18,2022-06-24,0.213
601077.XSHG,2022-06-21,2022-06-29,0.2525
601818.XSHG,2022-06-21,2022-06-29,0.201
601838.XSHG,2022-06-22,2022-06-29,0.63
601825.XSHG,2022-06-23,2022-06-30,0.3
600908.XSHG,2022-06-29,2022-07-06,0.18
601665.XSHG,2022-06-30,2022-07-06,0.184
002958.XSHE,2022-07-02,2022-07-08,0.1
601229.XSHG,2022-07-02,2022-07-08,0.4
601939.XSHG,2022-07-01,2022-07-08,0.364
002142.XSHE,2022-07-05,2022-07-12,0.5
601328.XSHG,2022-07-06,2022-07-12,0.355
601398.XSHG,2022-07-05,2022-07-12,0.2933
601658.XSHG,2022-07-06,2022-07-12,0.2474
600926.XSHG,2022-07-06,2022-07-13,0.35
600036.XSHG,2022-07-08,2022-07-15,1.522
601169.XSHG,2022-07-11,2022-07-15,0.305
601288.XSHG,2022-07-08,2022-07-15,0.2068
601988.XSHG,2022-07-08,2022-07-15,0.221
001227.XSHE,2022-07-15,2022-07-21,0.1
600000.XSHG,2022-07-13,2022-07-21,0.41
000001.XSHE,2022-07-15,2022-07-22,0.228
601963.XSHG,2022-07-20,2022-07-28,0.39
601998.XSHG,2022-07-21,2022-07-28,0.302
601577.XSHG,2022-07-27,2022-08-02,0.35
601528.XSHG,2023-04-28,2023-05-10,0.15
601916.XSHG,2023-05-12,2023-05-19,0.21
002966.XSHE,2023-05-24,2023-05-31,0.33
002839.XSHE,2023-05-26,2023-06-01,0.2
601128.XSHG,2023-05-26,2023-06-05,0.25
002807.XSHE,2023-06-01,2023-06-07,0.18
601187.XSHG,2023-05-31,2023-06-08,0.29
601997.XSHG,2023-06-01,2023-06-08,0.3
000001.XSHE,2023-06-07,2023-06-14,0.285
601860.XSHG,2023-06-09,2023-06-16,0.1
601166.XSHG,2023-06-13,2023-06-19,1.188
600928.XSHG,2023-06-13,2023-06-20,0.165
002948.XSHE,2023-06-16,2023-06-21,0.16
600015.XSHG,2023-06-13,2023-06-21,0.383
601009.XSHG,2023-06-15,2023-06-21,0.5339
600016.XSHG,2023-06-16,2023-06-26,0.214
601229.XSHG,2023-06-20,2023-06-28,0.4
601825.XSHG,2023-06-20,2023-06-28,0.342
603323.XSHG,2023-06-20,2023-06-28,0.17
601077.XSHG,2023-06-20,2023-06-29,0.2714
001227.XSHE,2023-06-28,2023-07-05,0.12
600908.XSHG,2023-06-29,2023-07-06,0.2
601169.XSHG,2023-06-28,2023-07-06,0.31
601665.XSHG,2023-07-04,2023-07-10,0.186
002142.XSHE,2023-07-05,2023-07-12,0.5
601328.XSHG,2023-07-06,2023-07-12,0.373
600036.XSHG,2023-07-06,2023-07-13,1.738
600926.XSHG,2023-07-06,2023-07-13,0.4
601658.XSHG,2023-07-07,2023-07-13,0.2579
601939.XSHG,2023-07-08,2023-07-14,0.389
600919.XSHG,2023-07-11,2023-07-17,0.4907
601398.XSHG,2023-07-11,2023-07-17,0.3035
601988.XSHG,2023-07-08,2023-07-17,0.232
601288.XSHG,2023-07-10,2023-07-18,0.2222
601818.XSHG,2023-07-11,2023-07-19,0.19
601963.XSHG,2023-07-13,2023-07-20,0.395
601998.XSHG,2023-07-13,2023-07-20,0.329
600000.XSHG,2023-07-13,2023-07-21,0.32
601577.XSHG,2023-07-15,2023-07-21,0.35
601838.XSHG,2023-07-19,2023-07-26,0.76793
601528.XSHG,2024-04-26,2024-05-09,0.18
002807.XSHE,2024-04-30,2024-05-10,0.19
601128.XSHG,2024-05-22,2024-05-29,0.25
002839.XSHE,2024-05-30,2024-06-06,0.2
002966.XSHE,2024-05-29,2024-06-06,0.39
601860.XSHG,2024-05-30,2024-06-06,0.1
601288.XSHG,2024-05-30,2024-06-07,0.2309
603323.XSHG,2024-05-31,2024-06-07,0.18
601997.XSHG,2024-06-04,2024-06-12,0.29
000001.XSHE,2024-06-06,2024-06-14,0.719
600919.XSHG,2024-06-07,2024-06-14,0.47
601009.XSHG,2024-06-07,2024-06-14,0.5367
601187.XSHG,2024-06-06,2024-06-14,0.31
002948.XSHE,2024-06-15,2024-06-20,0.16
600015.XSHG,2024-06-14,2024-06-21,0.384
601825.XSHG,2024-06-20,2024-06-26,0.379
601916.XSHG,2024-06-20,2024-06-26,0.164
601229.XSHG,2024-06-20,2024-06-27,0.46
601077.XSHG,2024-06-20,2024-06-28,0.2885
600908.XSHG,2024-06-28,2024-07-05,0.2
601665.XSHG,2024-06-28,2024-07-05,0.22
601838.XSHG,2024-06-27,2024-07-05,0.8968
002958.XSHE,2024-07-01,2024-07-09,0.1
601166.XSHG,2024-07-03,2024-07-09,1.04
002142.XSHE,2024-07-03,2024-07-10,0.6
601169.XSHG,2024-07-03,2024-07-10,0.32
601328.XSHG,2024-07-04,2024-07-10,0.375
601998.XSHG,2024-07-03,2024-07-10,0.3261
001227.XSHE,2024-07-05,2024-07-11,0.1
600036.XSHG,2024-07-04,2024-07-11,1.972
600926.XSHG,2024-07-05,2024-07-11,0.52
601658.XSHG,2024-07-05,2024-07-11,0.261
600016.XSHG,2024-07-04,2024-07-12,0.216
601939.XSHG,2024-07-06,2024-07-12,0.4
601398.XSHG,2024-07-09,2024-07-16,0.3064
601577.XSHG,2024-07-10,2024-07-16,0.38
601988.XSHG,2024-07-10,2024-07-17,0.2364
600000.XSHG,2024-07-11,2024-07-18,0.321
601963.XSHG,2024-07-13,2024-07-19,0.408
601818.XSHG,2024-07-16,2024-07-24,0.173
600928.XSHG,2024-07-25,2024-08-01,0.056
601825.XSHG,2024-09-19,2024-09-25,0.239
000001.XSHE,2024-09-26,2024-10-10,0.246
601009.XSHG,2024-10-25,2024-11-01,0.34626
600926.XSHG,2024-10-31,2024-11-06,0.37
600016.XSHG,2024-11-05,2024-11-13,0.13
002966.XSHE,2024-11-08,2024-11-18,0.2
601229.XSHG,2024-11-22,2024-11-28,0.28
601998.XSHG,2024-12-04,2024-12-11,0.1825
601187.XSHG,2024-12-04,2024-12-12,0.15
601398.XSHG,2024-12-31,2025-01-07,0.1434
601288.XSHG,2024-12-30,2025-01-08,0.1164
601658.XSHG,2024-12-31,2025-01-08,0.1477
600919.XSHG,2025-01-02,2025-01-10,0.3062
601939.XSHG,2025-01-03,2025-01-10,0.197
601169.XSHG,2025-01-14,2025-01-20,0.12
600015.XSHG,2025-01-16,2025-01-22,0.1
601818.XSHG,2025-01-16,2025-01-22,0.104
601860.XSHG,2025-01-15,2025-01-22,0.05
601077.XSHG,2025-01-15,2025-01-23,0.1944
601665.XSHG,2025-01-17,2025-01-23,0.127
601988.XSHG,2025-01-15,2025-01-23,0.1208
001227.XSHE,2025-01-18,2025-01-24,0.05
601328.XSHG,2025-01-16,2025-01-24,0.182
601963.XSHG,2025-01-18,2025-01-24,0.166
601328.XSHG,2025-04-14,2025-04-18,0.197
601988.XSHG,2025-04-21,2025-04-25,0.1216
002807.XSHE,2025-04-23,2025-04-30,0.2
601658.XSHG,2025-04-24,2025-04-30,0.1139
601528.XSHG,2025-04-29,2025-05-09,0.2
601939.XSHG,2025-04-30,2025-05-09,0.206
002839.XSHE,2025-05-10,2025-05-16,0.2
002966.XSHE,2025-05-28,2025-06-05,0.2
601128.XSHG,2025-05-28,2025-06-05,0.25
601860.XSHG,2025-05-29,2025-06-06,0.05
601997.XSHG,2025-05-30,2025-06-06,0.29
601963.XSHG,2025-06-04,2025-06-10,0.248
000001.XSHE,2025-06-05,2025-06-12,0.362
601229.XSHG,2025-06-06,2025-06-12,0.22
601665.XSHG,2025-06-06,2025-06-12,0.139
603323.XSHG,2025-06-06,2025-06-12,0.18
601577.XSHG,2025-06-07,2025-06-13,0.42
601166.XSHG,2025-06-16,2025-06-20,1.06
601009.XSHG,2025-06-17,2025-06-23,0.19931
002948.XSHE,2025-06-19,2025-06-26,0.16
600015.XSHG,2025-06-20,2025-06-26,0.305
601187.XSHG,2025-06-18,2025-06-26,0.16
601077.XSHG,2025-06-20,2025-06-27,0.1102
601825.XSHG,2025-06-23,2025-06-27,0.193
601916.XSHG,2025-06-21,2025-06-27,0.156
600908.XSHG,2025-06-27,2025-07-04,0.22
002958.XSHE,2025-07-02,2025-07-09,0.12
002936.XSHE,2025-07-03,2025-07-10,0.02
600919.XSHG,2025-07-03,2025-07-10,0.2144
601169.XSHG,2025-07-03,2025-07-10,0.2
601998.XSHG,2025-07-03,2025-07-10,0.1722
600036.XSHG,2025-07-04,2025-07-11,2
600928.XSHG,2025-07-04,2025-07-11,0.1
600016.XSHG,2025-07-04,2025-07-14,0.062
601398.XSHG,2025-07-08,2025-07-14,0.1646
002142.XSHE,2025-07-09,2025-07-16,0.9
600000.XSHG,2025-07-10,2025-07-16,0.41
601288.XSHG,2025-07-09,2025-07-17,0.1255
600926.XSHG,2025-07-15,2025-07-21,0.28
001227.XSHE,2025-07-16,2025-07-22,0.051
601818.XSHG,2025-07-18,2025-07-24,0.085
601838.XSHG,2025-07-22,2025-07-28,0.891
601128.XSHG,2025-09-02,2025-09-08,0.15
600016.XSHG,2025-09-10,2025-09-16,0.136
603323.XSHG,2025-09-12,2025-09-19,0.09
601577.XSHG,2025-09-19,2025-09-26,0.2
601825.XSHG,2025-09-20,2025-09-26,0.241
000001.XSHE,2025-09-30,2025-10-15,0.236
002839.XSHE,2025-10-09,2025-10-15,0.1
601229.XSHG,2025-10-10,2025-10-16,0.3
002966.XSHE,2025-11-08,2025-11-17,0.21
600926.XSHG,2025-11-12,2025-11-18,0.38
601009.XSHG,2025-11-14,2025-11-20,0.3062
601998.XSHG,2025-11-14,2025-11-21,0.188
600908.XSHG,2025-11-18,2025-11-25,0.11
002807.XSHE,2025-11-27,2025-12-03,0.1
601187.XSHG,2025-11-27,2025-12-05,0.14
601939.XSHG,2025-12-05,2025-12-11,0.1858
601988.XSHG,2025-12-05,2025-12-11,0.1094
601288.XSHG,2025-12-09,2025-12-15,0.1195
601398.XSHG,2025-12-09,2025-12-15,0.1414
002142.XSHE,2025-12-10,2025-12-17,0.3
601328.XSHG,2025-12-19,2025-12-25,0.1563
601963.XSHG,2025-12-27,2026-01-07,0.1684
601658.XSHG,2026-01-06,2026-01-12,0.123
600919.XSHG,2026-01-08,2026-01-14,0.3309
600036.XSHG,2026-01-10,2026-01-16,1.013
600015.XSHG,2026-01-17,2026-01-23,0.1
601077.XSHG,2026-01-15,2026-01-23,0.20336
601818.XSHG,2026-01-30,2026-02-05,0.105
601860.XSHG,2026-01-29,2026-02-05,0.05
601166.XSHG,2026-02-02,2026-02-06,0.565
001227.XSHE,2026-02-03,2026-02-09,0.05
601665.XSHG,2026-02-05,2026-02-11,0.121
601528.XSHG,2026-04-30,2026-05-12,0.21
601288.XSHG,2026-05-07,2026-05-13,0.13
601398.XSHG,2026-05-07,2026-05-13,0.1689
002839.XSHE,2026-05-15,2026-05-21,0.12
002807.XSHE,2026-05-23,2026-05-29,0.12
"""


def build_quality_data():
    data = {}
    try:
        df = pd.read_csv(StringIO(QUALITY_CSV.strip()))
    except Exception as exc:
        log.info('quality csv parse failed: %s' % str(exc))
        return data
    for _, row in df.iterrows():
        code = str(row.get('code', '')).strip()
        if not code:
            continue
        notice_date = to_date(row.get('notice_date'))
        item = {
            'source_year': safe_int(row.get('source_year')),
            'notice_date': notice_date,
            'npl_ratio': safe_float(row.get('npl_ratio')),
            'provision_coverage_ratio': safe_float(row.get('provision_coverage_ratio')),
            'core_tier_1_capital_adequacy_ratio': safe_float(row.get('core_tier_1_capital_adequacy_ratio')),
        }
        data.setdefault(code, []).append(item)
    for snapshots in data.values():
        snapshots.sort(key=lambda x: (x['notice_date'], x.get('source_year') or 0))
    return data


def build_dividend_events():
    data = {}
    try:
        df = pd.read_csv(StringIO(DIVIDEND_CSV.strip()))
    except Exception as exc:
        log.info('dividend csv parse failed: %s' % str(exc))
        return data
    for _, row in df.iterrows():
        code = str(row.get('code', '')).strip()
        if not code:
            continue
        ex_date = to_date(row.get('ex_date'))
        visible_date = to_date(row.get('announce_date')) or ex_date
        cash = safe_float(row.get('cash_per_share'))
        if ex_date is None or visible_date is None or cash is None or cash <= 0:
            continue
        data.setdefault(code, []).append({'ex_date': ex_date, 'visible_date': visible_date, 'cash_per_share': cash})
    for events in data.values():
        events.sort(key=lambda x: x['ex_date'])
    return data


def winsorize_series(series, lower=0.05, upper=0.95):
    series = pd.to_numeric(series, errors='coerce')
    if series.notna().sum() < 5:
        return series
    return series.clip(lower=series.quantile(lower), upper=series.quantile(upper))


def zscore_series(series):
    series = pd.to_numeric(series, errors='coerce')
    if series.notna().sum() < 3:
        return pd.Series(index=series.index, data=np.nan)
    std = series.std()
    avg = series.mean()
    if std is None or pd.isna(std) or abs(std) < 1e-12:
        return pd.Series(index=series.index, data=np.nan)
    return (series - avg) / std


def safe_float(value):
    try:
        if value is None or pd.isna(value):
            return None
        value = float(value)
        if np.isinf(value):
            return None
        return value
    except Exception:
        return None


def safe_int(value):
    value = safe_float(value)
    return int(value) if value is not None else None


def to_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if hasattr(value, 'date'):
        return value.date()
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        return pd.Timestamp(value).date()
    except Exception:
        return None


def build_score_preview(df):
    preview = []
    for _, row in df.iterrows():
        preview.append('%s:score=%.4f,div=%s,pb=%s,roe=%s,prov=%s,cap=%s,qguard=%s' % (
            row['code'],
            float(row['final_score']) if pd.notna(row['final_score']) else float('nan'),
            fmt_num(row.get('dividend_yield')),
            fmt_num(row.get('low_price_to_book')),
            fmt_num(row.get('return_on_equity_ttm')),
            fmt_num(row.get('provision_coverage_ratio')),
            fmt_num(row.get('core_tier_1_capital_adequacy_ratio')),
            fmt_num(row.get('quality_guard_score')),
        ))
    return '[' + ' ; '.join(preview) + ']'


def fmt_num(value):
    try:
        if value is None or pd.isna(value):
            return 'na'
        return '%.4f' % float(value)
    except Exception:
        return 'na'


def after_trading_end_log(context):
    return

from jqdata import *
from datetime import datetime
import math

import numpy as np
import pandas as pd


"""
Bank Quant V5.1f - Utilities Demand-State JoinQuant near-5-year test.

Purpose:
- Engineering/platform test for 2021-05-01 to 2026-05-31.
- This is not an accepted strategy.
- Do not tune parameters after seeing JoinQuant results.

Rule:
- warmup: operating cash-flow yield top 10
- weak electricity demand: dividend yield top 10
- mid electricity demand: operating cash-flow yield top 10
- strong electricity demand: low PB top 10

Important:
- This version uses frozen V5 local rebalance signals for platform execution alignment.
- It does not recompute dividend_yield on JoinQuant because valuation.dividend_ratio is not
  available in the tested JoinQuant runtime.
- Cash dividends are not explicitly credited here; JoinQuant platform handles portfolio accounting.
"""


UTILITY_INDUSTRIES = {
    'HY10001': 'thermal_power',
    'HY10002': 'hydropower',
    'HY10003': 'nuclear_power',
    'HY10005': 'gas',
    'HY10006': 'heating_or_other_utility',
    'HY10007': 'water',
    'HY10008': 'grid',
    'HY10101': 'thermal_power',
    'HY10102': 'hydropower',
    'HY10103': 'nuclear_power',
    'HY10107': 'grid',
    'HY10108': 'gas',
    'HY10109': 'water',
    'HY10111': 'heating_or_other_utility',
}


FALLBACK_UTILITY_CODES = [
    '000027.XSHE', '000037.XSHE', '000301.XSHE', '000407.XSHE', '000421.XSHE',
    '000531.XSHE', '000539.XSHE', '000543.XSHE', '000593.XSHE', '000598.XSHE',
    '000600.XSHE', '000601.XSHE', '000605.XSHE', '000669.XSHE', '000685.XSHE',
    '000690.XSHE', '000692.XSHE', '000695.XSHE', '000720.XSHE', '000722.XSHE',
    '000767.XSHE', '000791.XSHE', '000875.XSHE', '000883.XSHE', '000899.XSHE',
    '000958.XSHE', '000966.XSHE', '000993.XSHE', '001210.XSHE', '001286.XSHE',
    '001299.XSHE', '001376.XSHE', '001896.XSHE', '002015.XSHE', '002039.XSHE',
    '002259.XSHE', '002267.XSHE', '002479.XSHE', '002524.XSHE', '002608.XSHE',
    '002700.XSHE', '002893.XSHE', '002911.XSHE', '003039.XSHE', '003816.XSHE',
    '300332.XSHE', '300335.XSHE', '300435.XSHE', '600008.XSHG', '600011.XSHG',
    '600021.XSHG', '600023.XSHG', '600025.XSHG', '600027.XSHG', '600051.XSHG',
    '600052.XSHG', '600098.XSHG', '600101.XSHG', '600116.XSHG', '600131.XSHG',
    '600149.XSHG', '600157.XSHG', '600167.XSHG', '600168.XSHG', '600187.XSHG',
    '600212.XSHG', '600226.XSHG', '600236.XSHG', '600283.XSHG', '600292.XSHG',
    '600310.XSHG', '600333.XSHG', '600396.XSHG', '600452.XSHG', '600461.XSHG',
    '600475.XSHG', '600483.XSHG', '600505.XSHG', '600509.XSHG', '600575.XSHG',
    '600578.XSHG', '600617.XSHG', '600635.XSHG', '600642.XSHG', '600644.XSHG',
    '600674.XSHG', '600681.XSHG', '600719.XSHG', '600726.XSHG', '600744.XSHG',
    '600769.XSHG', '600780.XSHG', '600795.XSHG', '600803.XSHG', '600863.XSHG',
    '600864.XSHG', '600868.XSHG', '600886.XSHG', '600900.XSHG', '600903.XSHG',
    '600917.XSHG', '600956.XSHG', '600969.XSHG', '600979.XSHG', '600982.XSHG',
    '600995.XSHG', '601139.XSHG', '601158.XSHG', '601199.XSHG', '601368.XSHG',
    '601985.XSHG', '601991.XSHG', '603053.XSHG', '603080.XSHG', '603291.XSHG',
    '603318.XSHG', '603393.XSHG', '603689.XSHG', '603706.XSHG', '603759.XSHG',
    '603817.XSHG', '605011.XSHG', '605028.XSHG', '605090.XSHG', '605162.XSHG',
    '605169.XSHG', '605368.XSHG', '605580.XSHG'
]


ELECTRICITY_STATE_ROWS = [
    ('2021-06-25', '2021-05-31', 17.7),
    ('2021-09-25', '2021-08-31', 13.8),
    ('2021-12-25', '2021-11-30', 11.4),
    ('2022-03-25', '2022-02-28', 5.8),
    ('2022-06-25', '2022-05-31', 2.5),
    ('2022-09-25', '2022-08-31', 4.4),
    ('2022-12-25', '2022-11-30', 3.5),
    ('2023-03-25', '2023-02-28', 2.3),
    ('2023-06-25', '2023-05-31', 5.2),
    ('2023-09-25', '2023-08-31', 5.0),
    ('2023-12-25', '2023-11-30', 6.3),
    ('2024-03-25', '2024-02-29', 11.0),
    ('2024-06-25', '2024-05-31', 8.6),
    ('2024-09-25', '2024-08-31', 7.9),
    ('2024-12-25', '2024-11-30', 7.1),
    ('2025-03-25', '2025-02-28', 1.3),
    ('2025-06-25', '2025-05-31', 3.4),
    ('2025-09-25', '2025-08-31', 4.6),
    ('2025-12-25', '2025-11-30', 5.2),
    ('2026-03-25', '2026-02-28', 6.1),
]


FROZEN_REBALANCE_SIGNALS = {
    '2021-07': ['600011.XSHG', '600795.XSHG', '600396.XSHG', '600027.XSHG', '601991.XSHG', '000669.XSHE', '600021.XSHG', '000543.XSHE', '001896.XSHE', '600617.XSHG'],
    '2021-10': ['600969.XSHG', '000421.XSHE', '000539.XSHE', '601991.XSHG', '600803.XSHG', '600617.XSHG', '601985.XSHG', '000543.XSHE', '600795.XSHG', '600011.XSHG'],
    '2022-01': ['000421.XSHE', '600795.XSHG', '600310.XSHG', '002893.XSHE', '601991.XSHG', '600617.XSHG', '002267.XSHE', '002039.XSHE', '601985.XSHG', '003816.XSHE'],
    '2022-04': ['000421.XSHE', '600795.XSHG', '002893.XSHE', '600803.XSHG', '600681.XSHG', '002267.XSHE', '600617.XSHG', '600310.XSHG', '000407.XSHE', '600886.XSHG'],
    '2022-07': ['601991.XSHG', '600795.XSHG', '000543.XSHE', '600027.XSHG', '002608.XSHE', '000669.XSHE', '000883.XSHE', '601985.XSHG', '600011.XSHG', '600744.XSHG'],
    '2022-10': ['600719.XSHG', '600617.XSHG', '000421.XSHE', '600021.XSHG', '600795.XSHG', '000600.XSHE', '600803.XSHG', '600310.XSHG', '002039.XSHE', '600969.XSHG'],
    '2023-01': ['600795.XSHG', '000600.XSHE', '600310.XSHG', '600283.XSHG', '002039.XSHE', '002893.XSHE', '600098.XSHG', '600617.XSHG', '601991.XSHG', '601985.XSHG'],
    '2023-04': ['600795.XSHG', '000600.XSHE', '002893.XSHE', '600021.XSHG', '600283.XSHG', '600617.XSHG', '600956.XSHG', '600098.XSHG', '600168.XSHG', '601985.XSHG'],
    '2023-07': ['000421.XSHE', '600795.XSHG', '600617.XSHG', '000669.XSHE', '600642.XSHG', '000883.XSHE', '002039.XSHE', '601985.XSHG', '000027.XSHE', '601991.XSHG'],
    '2023-10': ['000421.XSHE', '600969.XSHG', '600795.XSHG', '600617.XSHG', '601985.XSHG', '600396.XSHG', '601991.XSHG', '000539.XSHE', '600982.XSHG', '003816.XSHE'],
    '2024-01': ['000692.XSHE', '000685.XSHE', '600969.XSHG', '600098.XSHG', '000690.XSHE', '002608.XSHE', '000883.XSHE', '600168.XSHG', '000600.XSHE', '600578.XSHG'],
    '2024-04': ['000692.XSHE', '600969.XSHG', '000685.XSHE', '600168.XSHG', '601368.XSHG', '000601.XSHE', '000605.XSHE', '600098.XSHG', '600021.XSHG', '000690.XSHE'],
    '2024-07': ['001896.XSHE', '000601.XSHE', '601991.XSHG', '000669.XSHE', '600744.XSHG', '000539.XSHE', '600011.XSHG', '000966.XSHE', '600982.XSHG', '600795.XSHG'],
    '2024-10': ['600969.XSHG', '000421.XSHE', '600795.XSHG', '000539.XSHE', '600617.XSHG', '000027.XSHE', '600011.XSHG', '600021.XSHG', '601991.XSHG', '002479.XSHE'],
    '2025-01': ['600969.XSHG', '601991.XSHG', '000539.XSHE', '600744.XSHG', '600795.XSHG', '600011.XSHG', '000543.XSHE', '600021.XSHG', '000600.XSHE', '000692.XSHE'],
    '2025-04': ['605368.XSHG', '000690.XSHE', '605028.XSHG', '600681.XSHG', '002911.XSHE', '000685.XSHE', '600167.XSHG', '603706.XSHG', '002267.XSHE', '600803.XSHG'],
    '2025-07': ['605368.XSHG', '600681.XSHG', '000685.XSHE', '002267.XSHE', '600008.XSHG', '600167.XSHG', '001299.XSHE', '600803.XSHG', '001286.XSHE', '605090.XSHG'],
    '2025-10': ['000421.XSHE', '600969.XSHG', '600795.XSHG', '600011.XSHG', '600051.XSHG', '600578.XSHG', '600027.XSHG', '000539.XSHE', '601991.XSHG', '600803.XSHG'],
    '2026-01': ['601991.XSHG', '001896.XSHE', '600011.XSHG', '600795.XSHG', '000027.XSHE', '000543.XSHE', '600027.XSHG', '000600.XSHE', '002039.XSHE', '600617.XSHG'],
    '2026-04': ['600795.XSHG', '000543.XSHE', '000027.XSHE', '600011.XSHG', '002039.XSHE', '001210.XSHE', '600021.XSHG', '000600.XSHE', '600969.XSHG', '600803.XSHG'],
}


FROZEN_SIGNAL_META = {
    '2021-07': ('warmup', 'raw_cashflow_yield_utilities_top10', 'operating_cash_flow_yield'),
    '2021-10': ('warmup', 'raw_cashflow_yield_utilities_top10', 'operating_cash_flow_yield'),
    '2022-01': ('warmup', 'raw_cashflow_yield_utilities_top10', 'operating_cash_flow_yield'),
    '2022-04': ('warmup', 'raw_cashflow_yield_utilities_top10', 'operating_cash_flow_yield'),
    '2022-07': ('warmup', 'raw_cashflow_yield_utilities_top10', 'operating_cash_flow_yield'),
    '2022-10': ('warmup', 'raw_cashflow_yield_utilities_top10', 'operating_cash_flow_yield'),
    '2023-01': ('warmup', 'raw_cashflow_yield_utilities_top10', 'operating_cash_flow_yield'),
    '2023-04': ('warmup', 'raw_cashflow_yield_utilities_top10', 'operating_cash_flow_yield'),
    '2023-07': ('mid', 'raw_cashflow_yield_utilities_top10', 'operating_cash_flow_yield'),
    '2023-10': ('mid', 'raw_cashflow_yield_utilities_top10', 'operating_cash_flow_yield'),
    '2024-01': ('strong', 'raw_low_pb_utilities_top10', 'low_price_to_book'),
    '2024-04': ('strong', 'raw_low_pb_utilities_top10', 'low_price_to_book'),
    '2024-07': ('mid', 'raw_cashflow_yield_utilities_top10', 'operating_cash_flow_yield'),
    '2024-10': ('mid', 'raw_cashflow_yield_utilities_top10', 'operating_cash_flow_yield'),
    '2025-01': ('mid', 'raw_cashflow_yield_utilities_top10', 'operating_cash_flow_yield'),
    '2025-04': ('weak', 'raw_high_dividend_utilities_top10', 'dividend_yield'),
    '2025-07': ('weak', 'raw_high_dividend_utilities_top10', 'dividend_yield'),
    '2025-10': ('mid', 'raw_cashflow_yield_utilities_top10', 'operating_cash_flow_yield'),
    '2026-01': ('mid', 'raw_cashflow_yield_utilities_top10', 'operating_cash_flow_yield'),
    '2026-04': ('mid', 'raw_cashflow_yield_utilities_top10', 'operating_cash_flow_yield'),
}


def initialize(context):
    set_benchmark('000007.XSHG')
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    set_order_cost(
        OrderCost(open_commission=0.0003, close_commission=0.0003, min_commission=5),
        type='stock',
    )

    g.strategy_id = 'utilities_demand_state_v51f'
    g.script_version = 'v51f_utilities_frozen_signals_near5y_20260716_fix_no_dividend_ratio'
    g.selection_count = 10
    g.target_exposure = 0.995
    g.max_position_weight = 0.12
    g.min_coverage_ratio = 0.80
    g.min_listing_age_days = 180
    g.min_state_history = 8
    g.rebalance_months = [1, 4, 7, 10]
    g.executed_rebalance_keys = set()
    g.state_history = []
    g.debug = True

    log.info('V5.1f utilities frozen-signal script=%s benchmark=000007.XSHG selection_count=%d signal_months=%d' % (
        g.script_version, g.selection_count, len(FROZEN_REBALANCE_SIGNALS)))

    if '512800' in str(g.script_version):
        log.info('V5.1f WARNING: unexpected bank ETF marker in utilities script')
    log.info('V5.1f benchmark note: 000007.XSHG is used for utilities; 512800.XSHG bank ETF is not used here.')
    run_daily(maybe_rebalance, time='09:40')
    run_daily(after_trading_end_log, time='after_close')


def maybe_rebalance(context):
    current_date = context.current_dt.date()
    if current_date.month not in g.rebalance_months:
        return

    key = '%04d-%02d' % (current_date.year, current_date.month)
    if key in g.executed_rebalance_keys:
        return

    selected_codes = FROZEN_REBALANCE_SIGNALS.get(key, [])
    if not selected_codes:
        log.info('V5.1f no frozen signal for date=%s key=%s; no trade' % (str(current_date), key))
        return

    factor_date = get_previous_trade_date(context)
    bucket, case_name, factor_name = FROZEN_SIGNAL_META.get(key, ('unknown', 'unknown', 'unknown'))
    target_weight = min(g.max_position_weight, g.target_exposure / float(g.selection_count))

    log.info('V5.1f frozen rebalance date=%s factor_date=%s bucket=%s case=%s factor=%s selected=%s target_weight=%.4f' % (
        str(current_date),
        str(factor_date),
        bucket,
        case_name,
        factor_name,
        ','.join(selected_codes),
        target_weight,
    ))

    execute_target_weights(context, selected_codes, target_weight)
    g.executed_rebalance_keys.add(key)


def build_score_frame(stocks, factor_date):
    fundamentals = fetch_fundamentals(stocks, factor_date)
    if fundamentals is None or len(fundamentals) == 0:
        return pd.DataFrame()

    df = fundamentals.copy()
    df['low_price_to_book'] = pd.to_numeric(df.get('pb_ratio'), errors='coerce')
    df['dividend_yield'] = pd.Series(index=df.index, data=np.nan)
    market_cap_cny = pd.to_numeric(df.get('market_cap'), errors='coerce') * 100000000.0
    operating_cash_flow = pd.to_numeric(df.get('net_operate_cash_flow'), errors='coerce')
    df['operating_cash_flow_yield'] = operating_cash_flow / market_cap_cny
    df = df.replace([np.inf, -np.inf], np.nan)
    return df


def fetch_fundamentals(stocks, factor_date):
    if not stocks:
        return pd.DataFrame()
    try:
        df = get_fundamentals(
            query(
                valuation.code,
                valuation.pb_ratio,
                valuation.pe_ratio,
                valuation.market_cap,
                cash_flow.net_operate_cash_flow,
            ).filter(valuation.code.in_(stocks)),
            date=factor_date,
        )
        if df is None or len(df) == 0:
            return pd.DataFrame()
        return df
    except Exception as exc:
        log.info('V5.1f fundamentals fetch failed factor_date=%s error=%s' % (str(factor_date), str(exc)))
        return pd.DataFrame()


def get_utilities_universe(factor_date):
    securities = get_all_securities(['stock'], date=factor_date)
    result = set()
    for industry_code in sorted(UTILITY_INDUSTRIES):
        try:
            codes = get_industry_stocks(industry_code, date=factor_date)
        except Exception as exc:
            if g.debug:
                log.info('V5.1f industry fetch failed code=%s date=%s error=%s' % (
                    industry_code, str(factor_date), str(exc)))
            codes = []
        for code in codes:
            if is_listed_and_mature(securities, code, factor_date):
                result.add(code)

    if not result:
        log.info('V5.1f industry universe empty on %s; using embedded fallback code union' % str(factor_date))
        for code in FALLBACK_UTILITY_CODES:
            if is_listed_and_mature(securities, code, factor_date):
                result.add(code)

    return sorted(result)


def get_tradable_stocks(stocks, context, factor_date):
    current_data = get_current_data()
    result = []
    for stock in stocks:
        try:
            data = current_data[stock]
            if data.paused or data.is_st:
                continue
            if 'ST' in data.name or '*' in data.name:
                continue
            result.append(stock)
        except Exception:
            continue
    return result


def is_listed_and_mature(securities, stock, factor_date):
    if stock not in securities.index:
        return False
    try:
        start_date = to_date(securities.loc[stock, 'start_date'])
        end_date = to_date(securities.loc[stock, 'end_date'])
        day = to_date(factor_date)
        if start_date is None or day is None:
            return False
        if (day - start_date).days < g.min_listing_age_days:
            return False
        if end_date is not None and end_date < day:
            return False
        return True
    except Exception:
        return False


def latest_visible_state(factor_date):
    day = to_date(factor_date)
    selected = None
    for visible_text, state_text, value in ELECTRICITY_STATE_ROWS:
        visible_date = to_date(visible_text)
        if visible_date is not None and visible_date <= day:
            selected = {'visible_date': visible_date, 'state_date': to_date(state_text), 'value': float(value)}
        else:
            break
    return selected


def expanding_bucket(history, value, min_history):
    if len(history) < min_history:
        return 'warmup'
    values = sorted([float(item) for item in history])
    q33 = values[len(values) // 3]
    q67 = values[(2 * len(values)) // 3]
    if value <= q33:
        return 'weak'
    if value >= q67:
        return 'strong'
    return 'mid'


def case_for_bucket(bucket):
    if bucket == 'strong':
        return 'raw_low_pb_utilities_top10', 'low_price_to_book', True
    if bucket == 'weak':
        return 'raw_high_dividend_utilities_top10', 'dividend_yield', False
    return 'raw_cashflow_yield_utilities_top10', 'operating_cash_flow_yield', False


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
            log.info('V5.1f skip paused %s reason=%s' % (stock, reason))
            return
        if data.is_st or 'ST' in data.name or '*' in data.name:
            log.info('V5.1f skip ST %s reason=%s' % (stock, reason))
            return
        if data.last_price >= data.high_limit or data.last_price <= data.low_limit:
            log.info('V5.1f skip limit %s reason=%s last=%.4f high=%.4f low=%.4f' % (
                stock, reason, data.last_price, data.high_limit, data.low_limit))
            return
        price = float(data.last_price)
        if price <= 0:
            return
        position = context.portfolio.positions[stock] if stock in context.portfolio.positions else None
        current_amount = int(position.total_amount) if position is not None else 0
        target_amount = 0 if target_value <= 0 else int(target_value / price / 100) * 100
        delta = target_amount - current_amount
        if target_amount != 0 and abs(delta) < 100:
            if g.debug:
                log.info('V5.1f skip lot delta %s reason=%s current=%d target=%d delta=%d' % (
                    stock, reason, current_amount, target_amount, delta))
            return
        if target_amount == current_amount:
            return
        order_target(stock, target_amount)
        if g.debug:
            if target_weight is None:
                log.info('V5.1f order target %s amount=%d value=%.2f reason=%s' % (
                    stock, target_amount, target_amount * price, reason))
            else:
                log.info('V5.1f order target %s amount=%d value=%.2f weight=%.4f reason=%s' % (
                    stock, target_amount, target_amount * price, target_weight, reason))
    except Exception as exc:
        log.info('V5.1f order failed %s reason=%s error=%s' % (stock, reason, str(exc)))


def clear_positions(context):
    current_data = get_current_data()
    for stock in list(context.portfolio.positions.keys()):
        order_lot_aware(context, current_data, stock, 0, 'clear')


def get_previous_trade_date(context):
    try:
        return to_date(context.previous_date)
    except Exception:
        trade_days = get_trade_days(end_date=context.current_dt.date(), count=2)
        if trade_days is None or len(trade_days) == 0:
            return context.current_dt.date()
        return to_date(trade_days[0])


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


def build_score_preview(df, factor_name):
    preview = []
    for _, row in df.iterrows():
        preview.append('%s:%s=%s,div=%s,ocfy=%s,pb=%s' % (
            row['code'],
            factor_name,
            fmt_num(row.get(factor_name)),
            fmt_num(row.get('dividend_yield')),
            fmt_num(row.get('operating_cash_flow_yield')),
            fmt_num(row.get('low_price_to_book')),
        ))
    return '[' + ' ; '.join(preview) + ']'


def fmt_num(value):
    try:
        if value is None or pd.isna(value):
            return 'na'
        return '%.6f' % float(value)
    except Exception:
        return 'na'


def after_trading_end_log(context):
    return

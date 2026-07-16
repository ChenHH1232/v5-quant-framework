from jqdata import *
from datetime import datetime, timedelta
import math

import numpy as np
import pandas as pd

try:
    from jqdata import finance
except Exception:
    finance = None


"""
Bank Quant V5.1f - Utilities Demand-State JoinQuant live recompute test.

Purpose:
- Engineering live-factor recompute test.
- This is not an accepted strategy.
- Do not tune parameters after seeing JoinQuant results.

Rule:
- warmup: operating cash-flow yield top 10
- weak electricity demand: dividend yield top 10
- mid electricity demand: operating cash-flow yield top 10
- strong electricity demand: low PB top 10

Important:
- This version recomputes the universe, external state bucket, and stock-level factor ranking on JoinQuant.
- It does not use valuation.dividend_ratio. Dividend yield is reconstructed from visible cash
  dividends where JoinQuant finance.STK_XR_XD is available.
- If the weak-demand branch needs dividend_yield and the dividend source is unavailable, the
  rebalance is blocked instead of trading on blank data.
- Warm-up history is preloaded from dates before the backtest start when needed. This is not
  performance-window leakage because every state observation still requires visible_date <= factor_date.
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


def initialize(context):
    set_benchmark('000007.XSHG')
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    set_order_cost(
        OrderCost(open_commission=0.0003, close_commission=0.0003, min_commission=5),
        type='stock',
    )

    g.strategy_id = 'utilities_demand_state_v51f'
    g.script_version = 'v51f_utilities_live_recompute_20260716_warmup_dividend_repair'
    g.selection_count = 10
    g.target_exposure = 0.995
    g.max_position_weight = 0.12
    g.min_coverage_ratio = 0.80
    g.min_listing_age_days = 180
    g.min_state_history = 8
    g.data_warmup_start_date = to_date('2017-01-01')
    g.dividend_lookback_days = 365
    g.rebalance_months = [1, 4, 7, 10]
    g.executed_rebalance_keys = set()
    g.state_history = preload_state_history(g.data_warmup_start_date)
    g.dividend_source_attempted = False
    g.dividend_source_available = None
    g.debug = True

    log.info('V5.1f utilities live-recompute script=%s benchmark=000007.XSHG selection_count=%d warmup_start=%s preloaded_state_history=%d' % (
        g.script_version, g.selection_count, str(g.data_warmup_start_date), len(g.state_history)))

    if '512800' in str(g.script_version):
        log.info('V5.1f WARNING: unexpected bank ETF marker in utilities script')
    log.info('V5.1f benchmark note: 000007.XSHG is used for utilities; 512800.XSHG bank ETF is not used here.')
    log.info('V5.1f warm-up rule: backtest start is the performance window; state/dividend history may be read before it only when visible_date <= factor_date.')
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
    state = latest_visible_state(factor_date)
    if state is None:
        log.info('V5.1f LIVE BLOCKED: no visible electricity state on date=%s factor_date=%s' % (
            str(current_date), str(factor_date)))
        return

    history = visible_state_history(factor_date, exclude_state_date=state['state_date'])
    bucket = expanding_bucket(history, state['value'], g.min_state_history)
    case_name, factor_name, ascending = case_for_bucket(bucket)

    stocks = get_utilities_universe(factor_date)
    stocks = get_tradable_stocks(stocks, context, factor_date)
    if not stocks:
        log.info('V5.1f LIVE BLOCKED: empty tradable universe on date=%s factor_date=%s' % (
            str(current_date), str(factor_date)))
        return

    score_df = build_score_frame(stocks, factor_date)
    required = [factor_name, 'low_price_to_book', 'operating_cash_flow_yield']
    if factor_name == 'dividend_yield' and not dividend_source_is_usable(score_df):
        log.info('V5.1f LIVE BLOCKED: weak-demand branch needs dividend_yield but cash-dividend source is unavailable or blank on date=%s factor_date=%s' % (
            str(current_date), str(factor_date)))
        return

    score_df = score_df.dropna(subset=[factor_name]).copy()
    if len(score_df) == 0:
        log.info('V5.1f LIVE BLOCKED: no non-null factor rows factor=%s date=%s factor_date=%s' % (
            factor_name, str(current_date), str(factor_date)))
        return

    candidate_count = len(score_df)
    selected = score_df.sort_values([factor_name, 'code'], ascending=[ascending, True]).head(g.selection_count)
    selected_codes = selected['code'].tolist()
    coverage = float(len(selected_codes)) / float(g.selection_count)
    if coverage < g.min_coverage_ratio:
        log.info('V5.1f LIVE BLOCKED: selected coverage %.4f below minimum %.4f date=%s factor=%s candidates=%d selected=%d' % (
            coverage, g.min_coverage_ratio, str(current_date), factor_name, candidate_count, len(selected_codes)))
        return

    target_weight = min(g.max_position_weight, g.target_exposure / float(g.selection_count))

    log.info('V5.1f LIVE rebalance date=%s factor_date=%s state_visible=%s state_date=%s state_value=%.4f history=%d bucket=%s case=%s factor=%s candidates=%d selected=%s target_weight=%.4f preview=%s' % (
        str(current_date),
        str(factor_date),
        str(state['visible_date']),
        str(state['state_date']),
        float(state['value']),
        len(history),
        bucket,
        case_name,
        factor_name,
        candidate_count,
        ','.join(selected_codes),
        target_weight,
        build_score_preview(selected, factor_name),
    ))

    execute_target_weights(context, selected_codes, target_weight)
    g.executed_rebalance_keys.add(key)


def build_score_frame(stocks, factor_date):
    fundamentals = fetch_fundamentals(stocks, factor_date)
    if fundamentals is None or len(fundamentals) == 0:
        return pd.DataFrame()

    df = fundamentals.copy()
    df['low_price_to_book'] = pd.to_numeric(df.get('pb_ratio'), errors='coerce')
    dividend_df = fetch_dividend_yield_snapshot(stocks, factor_date)
    if dividend_df is not None and len(dividend_df) > 0:
        if 'dividend_yield' in dividend_df.columns:
            df['dividend_yield'] = pd.to_numeric(dividend_df['dividend_yield'], errors='coerce')
        else:
            df['dividend_yield'] = pd.Series(index=df.index, data=np.nan)
    else:
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


def fetch_dividend_yield_snapshot(stocks, factor_date):
    result = pd.DataFrame(index=stocks)
    result['code'] = result.index
    date_value = to_date(factor_date)
    if date_value is None:
        return result
    close_map = fetch_pre_adjusted_close(stocks, factor_date)
    event_map = fetch_visible_cash_dividends_from_joinquant(stocks, date_value)
    start_date = date_value - timedelta(days=int(g.dividend_lookback_days))
    non_null = 0
    for stock in stocks:
        close = close_map.get(stock)
        if close is None or close <= 0:
            continue
        cash = 0.0
        for event in event_map.get(stock, []):
            if event['visible_date'] <= date_value and start_date < event['ex_date'] <= date_value:
                cash += event['cash_per_share']
        if cash > 0:
            non_null += 1
        result.loc[stock, 'dividend_yield'] = cash / close
    if g.debug:
        log.info('V5.1f dividend snapshot date=%s source_available=%s non_null_cash_codes=%d stocks=%d' % (
            str(factor_date), str(g.dividend_source_available), non_null, len(stocks)))
    return result


def fetch_visible_cash_dividends_from_joinquant(stocks, factor_date):
    if finance is None:
        g.dividend_source_available = False
        log.info('V5.1f dividend source unavailable: jqdata.finance import failed')
        return {}
    if not stocks:
        return {}
    table = getattr(finance, 'STK_XR_XD', None)
    if table is None:
        g.dividend_source_available = False
        log.info('V5.1f dividend source unavailable: finance.STK_XR_XD missing')
        return {}

    start_date = factor_date - timedelta(days=int(g.dividend_lookback_days) + 45)
    field_sets = [
        ('code', 'implementation_pub_date', 'a_xr_date', 'bonus_ratio_rmb'),
        ('code', 'implementation_pub_date', 'a_xr_date', 'at_bonus_ratio_rmb'),
        ('code', 'shareholders_plan_pub_date', 'a_xr_date', 'bonus_ratio_rmb'),
        ('code', 'shareholders_plan_pub_date', 'a_xr_date', 'at_bonus_ratio_rmb'),
        ('code', 'notice_date', 'ex_date', 'cash_dividend_ratio'),
        ('code', 'announce_date', 'ex_date', 'cash_per_share'),
        ('code', 'pub_date', 'ex_dividend_date', 'dividend_cash_before_tax'),
    ]
    for code_field, visible_field, ex_field, cash_field in field_sets:
        try:
            fields = [
                getattr(table, code_field),
                getattr(table, visible_field),
                getattr(table, ex_field),
                getattr(table, cash_field),
            ]
            df = finance.run_query(
                query(*fields).filter(
                    getattr(table, code_field).in_(stocks),
                    getattr(table, ex_field) >= start_date,
                    getattr(table, ex_field) <= factor_date,
                )
            )
            events = normalize_dividend_events(df, code_field, visible_field, ex_field, cash_field)
            if events:
                g.dividend_source_available = True
                if g.debug:
                    log.info('V5.1f dividend source OK table=finance.STK_XR_XD fields=%s,%s,%s,%s event_codes=%d' % (
                        code_field, visible_field, ex_field, cash_field, len(events)))
                return events
        except Exception as exc:
            if g.debug:
                log.info('V5.1f dividend field-set failed fields=%s,%s,%s,%s error=%s' % (
                    code_field, visible_field, ex_field, cash_field, str(exc)))
            continue
    g.dividend_source_available = False
    return {}


def normalize_dividend_events(df, code_field, visible_field, ex_field, cash_field):
    result = {}
    if df is None or len(df) == 0:
        return result
    for _, row in df.iterrows():
        code = str(row.get(code_field, '')).strip()
        if not code:
            continue
        visible_date = to_date(row.get(visible_field))
        ex_date = to_date(row.get(ex_field))
        cash = normalize_cash_dividend(row.get(cash_field), cash_field)
        if visible_date is None:
            visible_date = ex_date
        if ex_date is None or visible_date is None or cash is None or cash <= 0:
            continue
        result.setdefault(code, []).append({
            'visible_date': visible_date,
            'ex_date': ex_date,
            'cash_per_share': cash,
        })
    for events in result.values():
        events.sort(key=lambda item: item['ex_date'])
    return result


def normalize_cash_dividend(value, field_name):
    cash = safe_float(value)
    if cash is None:
        return None
    # Some JoinQuant dividend tables express cash dividend per 10 shares.
    if field_name in {'bonus_ratio_rmb', 'at_bonus_ratio_rmb', 'cash_dividend_ratio', 'dividend_cash_before_tax'} and cash > 1.0:
        return cash / 10.0
    return cash


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
        log.info('V5.1f pre-adjusted close fetch failed: %s' % str(exc))
    return result


def dividend_source_is_usable(score_df):
    if score_df is None or len(score_df) == 0 or 'dividend_yield' not in score_df.columns:
        return False
    usable = pd.to_numeric(score_df['dividend_yield'], errors='coerce').notna().sum()
    return bool(g.dividend_source_available) and usable >= g.selection_count


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


def preload_state_history(warmup_start_date):
    start = to_date(warmup_start_date)
    history = []
    for visible_text, state_text, value in ELECTRICITY_STATE_ROWS:
        visible_date = to_date(visible_text)
        if start is not None and visible_date is not None and visible_date >= start:
            history.append(float(value))
    return history


def visible_state_history(factor_date, exclude_state_date=None):
    day = to_date(factor_date)
    excluded = to_date(exclude_state_date)
    history = []
    for visible_text, state_text, value in ELECTRICITY_STATE_ROWS:
        visible_date = to_date(visible_text)
        state_date = to_date(state_text)
        if visible_date is None or day is None or visible_date > day:
            continue
        if excluded is not None and state_date == excluded:
            continue
        history.append(float(value))
    return history


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


def after_trading_end_log(context):
    return

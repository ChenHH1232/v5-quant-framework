from jqdata import *
from datetime import datetime
from io import StringIO
import math

import numpy as np
import pandas as pd


"""
Bank Quant V5 - Bank Value 15Y JoinQuant near-5-year confirmation file.

Purpose:
- Confirm platform execution for the frozen `bank_value_15y` candidate.
- Do not tune this file after seeing the backtest result.

Important:
- This file does not call JoinQuant `bank_indicator`.
- Bank-specific indicators must be supplied through MANUAL_BANK_INDICATOR_CSV.
- If the manual table is empty, the code degrades to available valuation/ROE factors
  and logs a warning. That degraded run is not the full Bank Value 15Y strategy.
- Rebalance-day coverage filter is enabled. If too few bank stocks are tradable,
  the day is skipped and the strategy retries later in the same rebalance month.
"""


def initialize(context):
    set_benchmark('512800.XSHG')
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    set_order_cost(
        OrderCost(
            open_commission=0.0003,
            close_commission=0.0003,
            min_commission=5,
        ),
        type='stock',
    )

    g.strategy_id = 'bank_value_15y'
    g.selection_count = 8
    g.max_position_weight = 0.15
    g.min_coverage_ratio = 0.80
    g.rebalance_months = [1, 4, 7, 10]
    g.executed_rebalance_keys = set()
    g.debug = True

    g.factor_weights = {
        'low_price_to_book': 0.25,
        'dividend_yield': 0.15,
        'return_on_equity_ttm': 0.20,
        'non_performing_loan_ratio': 0.15,
        'provision_coverage_ratio': 0.15,
        'core_tier_1_capital_adequacy_ratio': 0.10,
    }
    g.factor_directions = {
        'low_price_to_book': -1,
        'dividend_yield': 1,
        'return_on_equity_ttm': 1,
        'non_performing_loan_ratio': -1,
        'provision_coverage_ratio': 1,
        'core_tier_1_capital_adequacy_ratio': 1,
    }
    g.bank_stocks = build_bank_stock_universe()
    g.manual_bank_indicator_data = build_manual_bank_indicator_data()

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
        log.info(
            'skip rebalance coverage too low date=%s factor_date=%s tradable=%d required=%d reference=%d ratio=%.2f'
            % (
                str(current_date),
                str(factor_date),
                len(stocks),
                min_required,
                reference_count,
                g.min_coverage_ratio,
            )
        )
        return

    if len(stocks) == 0:
        log.info('no tradable bank stocks on %s' % str(current_date))
        clear_positions(context)
        g.executed_rebalance_keys.add(key)
        return

    score_df = build_score_frame(stocks, factor_date)
    if score_df is None or len(score_df) == 0:
        log.info('empty score frame on %s factor_date=%s' % (str(current_date), str(factor_date)))
        clear_positions(context)
        g.executed_rebalance_keys.add(key)
        return

    guarded = apply_value_trap_guard(score_df)
    selected = guarded.sort_values('final_score', ascending=False).head(g.selection_count)

    exposure = get_target_exposure(context, factor_date, score_df, guarded)
    if len(selected) == 0:
        log.info('no selected stocks after value trap guard on %s' % str(current_date))
        clear_positions(context)
        g.executed_rebalance_keys.add(key)
        return

    target_weight = min(g.max_position_weight, exposure / float(g.selection_count))
    selected_codes = selected['code'].tolist()

    log.info(
        'rebalance date=%s factor_date=%s candidates=%d guarded=%d selected=%s exposure=%.2f target_weight=%.4f'
        % (
            str(current_date),
            str(factor_date),
            len(score_df),
            len(guarded),
            ','.join(selected_codes),
            exposure,
            target_weight,
        )
    )
    if g.debug:
        log.info('score preview: %s' % build_score_preview(selected))

    execute_target_weights(context, selected_codes, target_weight)
    g.executed_rebalance_keys.add(key)


def build_score_frame(stocks, factor_date):
    valuation_df = fetch_valuation_snapshot(stocks, factor_date)
    indicator_df = fetch_indicator_snapshot(stocks, factor_date)
    bank_df = fetch_manual_bank_indicator_snapshot(stocks, factor_date)

    df = pd.DataFrame(index=stocks)
    df['code'] = df.index
    for source in [valuation_df, indicator_df, bank_df]:
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

    # Dividend source is intentionally disabled until a reliable point-in-time
    # source is attached. Constant or missing factors are skipped in scoring.
    df['dividend_yield'] = np.nan

    score_parts = []
    used_factors = []
    for factor_name, weight in g.factor_weights.items():
        if factor_name not in df.columns:
            continue
        raw = pd.to_numeric(df[factor_name], errors='coerce')
        if raw.notna().sum() < 3:
            continue
        z = zscore_series(winsorize_series(raw))
        direction = g.factor_directions[factor_name]
        adjusted = z * float(direction)
        if adjusted.notna().sum() < 3:
            continue
        score_parts.append(adjusted * float(weight))
        used_factors.append(factor_name)
        df['z__' + factor_name] = z
        df['adj__' + factor_name] = adjusted

    if not score_parts:
        return pd.DataFrame()

    total_weight = sum(float(g.factor_weights[name]) for name in used_factors)
    df['final_score'] = sum(score_parts) / total_weight
    df['factor_count'] = df[['adj__' + name for name in used_factors]].notna().sum(axis=1)
    df = df.dropna(subset=['final_score']).copy()

    min_required = min(2, len(used_factors))
    df = df[df['factor_count'] >= min_required].copy()

    if g.debug:
        log.info('used factors on %s: %s' % (str(factor_date), ','.join(used_factors)))
        missing_bank = len(g.manual_bank_indicator_data) == 0
        if missing_bank:
            log.info('WARNING manual bank indicator table is empty; this is a degraded proxy run.')
    return df


def apply_value_trap_guard(score_df):
    quality_cols = [
        'adj__non_performing_loan_ratio',
        'adj__provision_coverage_ratio',
        'adj__core_tier_1_capital_adequacy_ratio',
    ]
    available = [col for col in quality_cols if col in score_df.columns]
    if len(available) < 2:
        log.info('value trap guard degraded: insufficient bank-quality factors')
        return score_df
    guarded = score_df.copy()
    guarded['quality_guard_score'] = guarded[available].mean(axis=1)
    threshold = guarded['quality_guard_score'].median()
    return guarded[guarded['quality_guard_score'] >= threshold].copy()


def get_target_exposure(context, factor_date, score_df, guarded_df):
    exposure = 1.0
    if len(score_df) > 0:
        failed_ratio = 1.0 - (float(len(guarded_df)) / float(len(score_df)))
        if failed_ratio > 0.5:
            exposure = min(exposure, 0.5)

    if is_bank_proxy_below_ma(factor_date):
        exposure = min(exposure, 0.5)
    return exposure


def is_bank_proxy_below_ma(factor_date):
    try:
        prices = get_price(
            '512800.XSHG',
            end_date=factor_date,
            count=244,
            frequency='daily',
            fields=['close'],
            panel=False,
        )
        if prices is None or len(prices) < 120:
            return False
        close = pd.to_numeric(prices['close'], errors='coerce').dropna()
        if len(close) < 120:
            return False
        return float(close.iloc[-1]) < float(close.mean())
    except Exception as exc:
        log.info('bank proxy MA check skipped: %s' % str(exc))
        return False


def fetch_valuation_snapshot(stocks, factor_date):
    try:
        df = get_fundamentals(
            query(
                valuation.code,
                valuation.pb_ratio,
            ).filter(valuation.code.in_(stocks)),
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
            query(
                indicator.code,
                indicator.roe,
            ).filter(indicator.code.in_(stocks)),
            date=factor_date,
        )
        if df is None or len(df) == 0:
            return pd.DataFrame(index=stocks)
        return df.set_index('code')
    except Exception as exc:
        log.info('indicator fetch failed: %s' % str(exc))
        return pd.DataFrame(index=stocks)


def fetch_manual_bank_indicator_snapshot(stocks, factor_date):
    source_year = get_bank_indicator_source_year(factor_date)
    result = pd.DataFrame(index=stocks)
    result['code'] = result.index
    if source_year is None:
        return result

    records = []
    for stock in stocks:
        stock_data = g.manual_bank_indicator_data.get(stock, {})
        yearly = stock_data.get(source_year, None)
        if yearly is None:
            continue
        records.append({
            'code': stock,
            'non_performing_loan_ratio': yearly.get('non_performing_loan_ratio', np.nan),
            'provision_coverage_ratio': yearly.get('provision_coverage_ratio', np.nan),
            'core_tier_1_capital_adequacy_ratio': yearly.get('core_tier_1_capital_adequacy_ratio', np.nan),
        })
    if not records:
        return result
    df = pd.DataFrame(records).set_index('code')
    for col in df.columns:
        result[col] = pd.to_numeric(df[col], errors='coerce')
    return result


def get_bank_indicator_source_year(factor_date):
    date_value = to_date(factor_date)
    if date_value is None:
        return None
    # Conservative annual-report visibility rule:
    # use year-1 only after May 1; otherwise use year-2.
    if date_value.month >= 5:
        return date_value.year - 1
    return date_value.year - 2


def execute_target_weights(context, selected_codes, target_weight):
    selected_set = set(selected_codes)
    target_value = context.portfolio.total_value * float(target_weight)
    current_positions = list(context.portfolio.positions.keys())
    for stock in current_positions:
        if stock not in selected_set:
            try:
                order_target_value(stock, 0)
            except Exception as exc:
                log.info('sell failed %s %s' % (stock, str(exc)))

    current_data = get_current_data()
    for stock in selected_codes:
        try:
            data = current_data[stock]
            if data.paused:
                continue
            if data.last_price >= data.high_limit or data.last_price <= data.low_limit:
                continue
            order_target_value(stock, target_value)
            if g.debug:
                log.info('order target %s value=%.2f weight=%.4f' % (stock, target_value, target_weight))
        except Exception as exc:
            log.info('buy failed %s %s' % (stock, str(exc)))


def clear_positions(context):
    for stock in list(context.portfolio.positions.keys()):
        try:
            order_target_value(stock, 0)
        except Exception as exc:
            log.info('clear failed %s %s' % (stock, str(exc)))


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


def get_previous_trade_date(context):
    try:
        return to_date(context.previous_date)
    except Exception:
        trade_days = get_trade_days(end_date=context.current_dt.date(), count=2)
        if trade_days is None or len(trade_days) == 0:
            return context.current_dt.date()
        return to_date(trade_days[0])


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


def build_bank_stock_universe():
    return [
        '000001.XSHE', '001227.XSHE', '002142.XSHE', '002807.XSHE',
        '002839.XSHE', '002936.XSHE', '002948.XSHE', '002958.XSHE',
        '002966.XSHE', '600000.XSHG', '600015.XSHG', '600016.XSHG',
        '600036.XSHG', '600908.XSHG', '600919.XSHG', '600926.XSHG',
        '600928.XSHG', '601009.XSHG', '601077.XSHG', '601128.XSHG',
        '601166.XSHG', '601169.XSHG', '601187.XSHG', '601229.XSHG',
        '601288.XSHG', '601328.XSHG', '601398.XSHG', '601528.XSHG',
        '601577.XSHG', '601658.XSHG', '601665.XSHG', '601818.XSHG',
        '601825.XSHG', '601838.XSHG', '601860.XSHG', '601916.XSHG', '601939.XSHG',
        '601963.XSHG', '601988.XSHG', '601997.XSHG', '601998.XSHG',
        '603323.XSHG'
    ]


MANUAL_BANK_INDICATOR_CSV = """
code,source_year,non_performing_loan_ratio,provision_coverage_ratio,core_tier_1_capital_adequacy_ratio
"""


def build_manual_bank_indicator_data():
    data = {}
    try:
        df = pd.read_csv(StringIO(MANUAL_BANK_INDICATOR_CSV.strip()))
    except Exception:
        return data
    required = [
        'code',
        'source_year',
        'non_performing_loan_ratio',
        'provision_coverage_ratio',
        'core_tier_1_capital_adequacy_ratio',
    ]
    for col in required:
        if col not in df.columns:
            return data
    for _, row in df.iterrows():
        code = str(row['code']).strip()
        if not code:
            continue
        try:
            year = int(row['source_year'])
        except Exception:
            continue
        data.setdefault(code, {})[year] = {
            'non_performing_loan_ratio': safe_float(row['non_performing_loan_ratio']),
            'provision_coverage_ratio': safe_float(row['provision_coverage_ratio']),
            'core_tier_1_capital_adequacy_ratio': safe_float(row['core_tier_1_capital_adequacy_ratio']),
        }
    return data


def winsorize_series(series, lower=0.05, upper=0.95):
    series = pd.to_numeric(series, errors='coerce')
    if series.notna().sum() < 5:
        return series
    low = series.quantile(lower)
    high = series.quantile(upper)
    return series.clip(lower=low, upper=high)


def zscore_series(series):
    series = pd.to_numeric(series, errors='coerce')
    if series.notna().sum() < 3:
        return pd.Series(index=series.index, data=np.nan)
    std = series.std()
    mean = series.mean()
    if std is None or pd.isna(std) or abs(std) < 1e-12:
        return pd.Series(index=series.index, data=np.nan)
    return (series - mean) / std


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


def to_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if hasattr(value, 'date'):
        return value.date()
    return pd.Timestamp(value).date()


def build_score_preview(df):
    preview = []
    for _, row in df.iterrows():
        preview.append('%s:score=%.4f,count=%s' % (
            row['code'],
            float(row['final_score']) if pd.notna(row['final_score']) else float('nan'),
            str(int(row['factor_count'])) if 'factor_count' in row and pd.notna(row['factor_count']) else 'na',
        ))
    return '[' + ' ; '.join(preview) + ']'


def after_trading_end_log(context):
    return

from jqdata import *
from datetime import datetime
from io import StringIO
import math

import numpy as np
import pandas as pd


"""
Bank Quant V5 - Bank Value Quality V2 JoinQuant near-5-year simulation file.

Purpose:
- Test the engineering feasibility of `bank_value_quality_v2` on JoinQuant.
- Use the 2021-05-01 to 2026-05-31 window only for platform confirmation.
- Do not tune this file after seeing the backtest result.

Important:
- This file does not call deprecated JoinQuant `bank_indicator`.
- Bank-specific quality fields are supplied through MANUAL_BANK_QUALITY_CSV.
- The embedded table is generated from V4 Eastmoney annual-report extraction.
- The embedded table is `needs_check`, so this is an engineering proxy run,
  not a formal V2 factor-validation result.
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

    g.strategy_id = 'bank_value_quality_v2'
    g.selection_count = 6
    g.max_position_weight = 0.18
    g.min_coverage_ratio = 0.80
    g.rebalance_months = [1, 4, 7, 10]
    g.executed_rebalance_keys = set()
    g.debug = True

    # Base V2 alpha strategy has no active defensive overlay. Keep this disabled
    # unless testing a separate risk-control candidate.
    g.defensive_overlay_enabled = False
    g.defensive_benchmark = '512800.XSHG'
    g.defensive_ma_days = 252
    g.risk_off_exposure_multiplier = 0.5

    g.bank_stocks = build_bank_stock_universe()
    g.manual_quality_data = build_manual_quality_data()
    g.quality_data_label = 'eastmoney_v4_needs_check_proxy'
    g.last_used_factors = []

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
            % (str(current_date), str(factor_date), len(stocks), min_required, reference_count, g.min_coverage_ratio)
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
    if len(guarded) == 0:
        log.info('no selected stocks after V2 value trap guard on %s' % str(current_date))
        clear_positions(context)
        g.executed_rebalance_keys.add(key)
        return

    selected = guarded.sort_values('final_score', ascending=False).head(g.selection_count)
    exposure = get_target_exposure(factor_date)
    target_weight = min(g.max_position_weight, exposure / float(g.selection_count))
    selected_codes = selected['code'].tolist()

    log.info(
        'V2 rebalance date=%s factor_date=%s candidates=%d guarded=%d selected=%s exposure=%.2f target_weight=%.4f'
        % (str(current_date), str(factor_date), len(score_df), len(guarded), ','.join(selected_codes), exposure, target_weight)
    )
    if g.debug:
        log.info('V2 used factors on %s: %s' % (str(factor_date), ','.join(g.last_used_factors)))
        log.info('V2 score preview: %s' % build_score_preview(selected))

    execute_target_weights(context, selected_codes, target_weight)
    g.executed_rebalance_keys.add(key)


def build_score_frame(stocks, factor_date):
    valuation_df = fetch_valuation_snapshot(stocks, factor_date)
    indicator_df = fetch_indicator_snapshot(stocks, factor_date)
    quality_df = fetch_manual_quality_snapshot(stocks, factor_date)

    df = pd.DataFrame(index=stocks)
    df['code'] = df.index
    for source in [valuation_df, indicator_df, quality_df]:
        if source is None or len(source) == 0:
            continue
        for col in source.columns:
            if col == 'code':
                continue
            df[col] = pd.to_numeric(source[col], errors='coerce')

    if 'pb_ratio' in df.columns:
        df['low_price_to_book'] = df['pb_ratio']
    if 'roe' in df.columns:
        df['roe_quality'] = df['roe']

    # Disabled until a reliable point-in-time dividend source is attached.
    df['sustainable_dividend_yield'] = np.nan

    value_parts = []
    value_used = []
    add_score_part(df, value_parts, value_used, 'low_price_to_book', 0.60, -1)
    add_score_part(df, value_parts, value_used, 'sustainable_dividend_yield', 0.40, 1)

    quality_parts = []
    quality_used = []
    add_score_part(df, quality_parts, quality_used, 'roe_quality', 0.35, 1)
    add_score_part(df, quality_parts, quality_used, 'asset_quality_trend', 0.25, 1)
    add_score_part(df, quality_parts, quality_used, 'provision_buffer', 0.20, 1)
    add_score_part(df, quality_parts, quality_used, 'capital_resilience', 0.20, 1)

    if not value_parts:
        return pd.DataFrame()

    df['value_score'] = weighted_average_parts(value_parts, value_used)
    if quality_parts:
        df['quality_score'] = weighted_average_parts(quality_parts, quality_used)
        df['final_score'] = 0.55 * df['value_score'] + 0.45 * df['quality_score']
    else:
        df['quality_score'] = np.nan
        df['final_score'] = df['value_score']

    used_factors = value_used + quality_used
    df['factor_count'] = df[['adj__' + name for name in used_factors]].notna().sum(axis=1)
    df = df.dropna(subset=['final_score']).copy()
    min_required = 2 if len(used_factors) >= 2 else 1
    df = df[df['factor_count'] >= min_required].copy()
    g.last_used_factors = used_factors

    if len(g.manual_quality_data) == 0:
        log.info('WARNING manual bank quality table is empty; V2 is degraded to available PB/ROE proxy factors.')
    else:
        log.info('WARNING V2 manual quality table loaded from %s; engineering proxy only, not formal validation.' % g.quality_data_label)
    missing_quality = [name for name in ['asset_quality_trend', 'provision_buffer', 'capital_resilience'] if name not in used_factors]
    if missing_quality:
        log.info('V2 missing quality factors: %s' % ','.join(missing_quality))
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


def weighted_average_parts(parts, used):
    total_weight = sum(weight for _, _, weight in parts)
    if total_weight <= 0:
        return pd.Series(dtype=float)
    result = None
    for _, series, weight in parts:
        weighted = series * weight
        result = weighted if result is None else result + weighted
    return result / total_weight


def apply_value_trap_guard(score_df):
    guarded = score_df.copy()
    if 'quality_score' not in guarded.columns or guarded['quality_score'].notna().sum() < 3:
        log.info('V2 value trap guard degraded: insufficient quality_score; no guard applied.')
        return guarded

    quality_threshold = guarded['quality_score'].median()
    result = guarded[guarded['quality_score'] >= quality_threshold].copy()

    if 'adj__asset_quality_trend' in result.columns and result['adj__asset_quality_trend'].notna().sum() >= 4:
        bottom_quartile = result['adj__asset_quality_trend'].quantile(0.25)
        result = result[result['adj__asset_quality_trend'] > bottom_quartile].copy()
    return result


def get_target_exposure(factor_date):
    if not g.defensive_overlay_enabled:
        return 1.0
    if is_bank_proxy_below_ma(factor_date):
        return g.risk_off_exposure_multiplier
    return 1.0


def is_bank_proxy_below_ma(factor_date):
    try:
        prices = get_price(
            g.defensive_benchmark,
            end_date=factor_date,
            count=g.defensive_ma_days,
            frequency='daily',
            fields=['close'],
            fq='pre',
            panel=False,
        )
        if prices is None or len(prices) < g.defensive_ma_days:
            return False
        close = pd.to_numeric(prices['close'], errors='coerce').dropna()
        if len(close) < g.defensive_ma_days:
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


def fetch_manual_quality_snapshot(stocks, factor_date):
    source_year = get_bank_indicator_source_year(factor_date)
    result = pd.DataFrame(index=stocks)
    result['code'] = result.index
    if source_year is None:
        return result

    records = []
    for stock in stocks:
        stock_data = g.manual_quality_data.get(stock, {})
        yearly = stock_data.get(source_year, None)
        if yearly is None:
            continue
        records.append({
            'code': stock,
            'asset_quality_trend': yearly.get('asset_quality_trend', np.nan),
            'provision_buffer': yearly.get('provision_buffer', np.nan),
            'capital_resilience': yearly.get('capital_resilience', np.nan),
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
    if date_value.month >= 5:
        return date_value.year - 1
    return date_value.year - 2


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
        if target_value <= 0:
            target_amount = 0
        else:
            target_amount = int(target_value / price / 100) * 100
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
                log.info('V2 order target %s amount=%d value=%.2f reason=%s' % (stock, target_amount, value, reason))
            else:
                log.info('V2 order target %s amount=%d value=%.2f weight=%.4f reason=%s' % (stock, target_amount, value, target_weight, reason))
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
        '000001.XSHE', '001227.XSHE', '002142.XSHE', '002807.XSHE',
        '002839.XSHE', '002936.XSHE', '002948.XSHE', '002958.XSHE',
        '002966.XSHE', '600000.XSHG', '600015.XSHG', '600016.XSHG',
        '600036.XSHG', '600908.XSHG', '600919.XSHG', '600926.XSHG',
        '600928.XSHG', '601009.XSHG', '601077.XSHG', '601128.XSHG',
        '601166.XSHG', '601169.XSHG', '601187.XSHG', '601229.XSHG',
        '601288.XSHG', '601328.XSHG', '601398.XSHG', '601528.XSHG',
        '601577.XSHG', '601658.XSHG', '601665.XSHG', '601818.XSHG',
        '601825.XSHG', '601838.XSHG', '601860.XSHG', '601916.XSHG',
        '601939.XSHG', '601963.XSHG', '601988.XSHG', '601997.XSHG',
        '601998.XSHG', '603323.XSHG'
    ]


MANUAL_BANK_QUALITY_CSV = """
"code","source_year","asset_quality_trend","provision_buffer","capital_resilience"
"000001.XSHE","2024","-1.06","315.02","9.12"
"000001.XSHE","2025","0.010000000000000009","330.03","9.36"
"001227.XSHE","2024","-1.83","201.6","8.73"
"001227.XSHE","2025","0.010000000000000009","198.38","8.21"
"002142.XSHE","2024","-0.76","389.35","9.84"
"002142.XSHE","2025","0.0","373.16","9.34"
"002807.XSHE","2024","-0.86","369.32","14.09"
"002807.XSHE","2025","0.040000000000000036","329.98","13.63"
"002839.XSHE","2024","-0.94","376.03","11.08"
"002839.XSHE","2025","0.0","328.87","10.93"
"002936.XSHE","2024","-2.05","182.99","8.76"
"002936.XSHE","2025","0.21999999999999975","185.81","8.45"
"002948.XSHE","2024","","241.32","9.11"
"002948.XSHE","2025","-0.17","72.53","8.67"
"002958.XSHE","2024","-1.79","250.53","10.7"
"002958.XSHE","2025","","261.01","10.07"
"002966.XSHE","2024","-0.83","483.5","9.77"
"002966.XSHE","2025","0.010000000000000009","418.6","9.53"
"600000.XSHG","2024","-1.36","","8.92"
"600000.XSHG","2025","0.10000000000000009","","8.99"
"600015.XSHG","2024","-1.59","","9.77"
"600015.XSHG","2025","0.66","","9.38"
"600016.XSHG","2024","-0.96","","9.36"
"600016.XSHG","2025","-0.96","","9.38"
"600036.XSHG","2024","","411.0","12.0"
"600036.XSHG","2025","","391.0","11.0"
"600908.XSHG","2024","-0.78","457.6","11.79"
"600908.XSHG","2025","0.010000000000000009","414.91","11.84"
"600919.XSHG","2024","-0.89","350.1","9.12"
"600919.XSHG","2025","0.050000000000000044","322.98","8.93"
"600926.XSHG","2024","-0.75","541.45","8.85"
"600926.XSHG","2025","0.17000000000000004","502.24","9.59"
"600928.XSHG","2024","-1.72","184.06","10.07"
"600928.XSHG","2025","0.07000000000000006","214.62","9.15"
"601009.XSHG","2024","","","5.0"
"601009.XSHG","2025","","","5.0"
"601077.XSHG","2024","","363.44","14.24"
"601077.XSHG","2025","","367.26","12.67"
"601128.XSHG","2024","","317.34","11.18"
"601128.XSHG","2025","-0.76","353.6","11.6"
"601166.XSHG","2024","-1.07","237.78","5.125"
"601166.XSHG","2025","-0.010000000000000009","228.41","9.7"
"601169.XSHG","2024","-1.31","247.16","8.95"
"601169.XSHG","2025","0.020000000000000018","200.21","8.37"
"601187.XSHG","2024","-0.74","","9.91"
"601187.XSHG","2025","-0.76","312.71","8.58"
"601229.XSHG","2024","-1.37","269.81","10.35"
"601229.XSHG","2025","0.19000000000000017","244.94","10.65"
"601288.XSHG","2024","-1.3","338.33","11.42"
"601288.XSHG","2025","0.030000000000000027","336.21","11.08"
"601328.XSHG","2024","-1.0","201.0",""
"601328.XSHG","2025","0.0","",""
"601398.XSHG","2024","","","14.1"
"601398.XSHG","2025","","35.0",""
"601528.XSHG","2024","-0.97","320.87","12.0"
"601528.XSHG","2025","-0.020000000000000018","159.29","12.65"
"601577.XSHG","2025","-2.43","280.86","10.05"
"601658.XSHG","2024","-0.9","286.15","9.56"
"601658.XSHG","2025","-0.04999999999999993","227.94","10.53"
"601665.XSHG","2024","","322.38","10.75"
"601665.XSHG","2025","-1.05","355.91","11.61"
"601818.XSHG","2024","-1.25","180.59","9.82"
"601818.XSHG","2025","-0.020000000000000018","174.14","9.69"
"601825.XSHG","2024","-1.32","352.35","7.5"
"601825.XSHG","2025","","328.87","7.5"
"601838.XSHG","2024","-0.66","479.29","9.06"
"601838.XSHG","2025","-0.020000000000000018","426.17","8.91"
"601860.XSHG","2024","-1.24","201.44","10.78"
"601860.XSHG","2025","-0.1100000000000001","","10.62"
"601916.XSHG","2024","","","12.0"
"601939.XSHG","2024","","","14.48"
"601963.XSHG","2024","","","12.0"
"601963.XSHG","2025","","","12.0"
"601988.XSHG","2025","-1.18","200.37","12.53"
"601997.XSHG","2024","-1.76","188.08","12.94"
"601997.XSHG","2025","-0.06000000000000005","173.38","13.11"
"601998.XSHG","2024","-1.19","","8.99"
"601998.XSHG","2025","0.040000000000000036","","9.48"
"603323.XSHG","2024","","428.96","10.91"
"603323.XSHG","2025","","370.17","10.65"
"""


def build_manual_quality_data():
    data = {}
    try:
        df = pd.read_csv(StringIO(MANUAL_BANK_QUALITY_CSV.strip()))
    except Exception:
        return data
    required = ['code', 'source_year', 'asset_quality_trend', 'provision_buffer', 'capital_resilience']
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
            'asset_quality_trend': safe_float(row['asset_quality_trend']),
            'provision_buffer': safe_float(row['provision_buffer']),
            'capital_resilience': safe_float(row['capital_resilience']),
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
        preview.append('%s:final=%.4f,value=%.4f,quality=%s,count=%s' % (
            row['code'],
            float(row['final_score']) if pd.notna(row['final_score']) else float('nan'),
            float(row['value_score']) if pd.notna(row['value_score']) else float('nan'),
            ('%.4f' % float(row['quality_score'])) if 'quality_score' in row and pd.notna(row['quality_score']) else 'na',
            str(int(row['factor_count'])) if 'factor_count' in row and pd.notna(row['factor_count']) else 'na',
        ))
    return '[' + ' ; '.join(preview) + ']'


def after_trading_end_log(context):
    return

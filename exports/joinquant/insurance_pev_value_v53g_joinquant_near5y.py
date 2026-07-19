from jqdata import *
from datetime import datetime
import math

import numpy as np
import pandas as pd


"""
Bank Quant V5.3g - Insurance Low P/EV JoinQuant near-5-year replication file.

Purpose:
- Platform replication preparation for the frozen `insurance_pev_value_v53g` candidate.
- This is not an accepted strategy and must not be tuned after seeing JoinQuant results.

Frozen rule:
- Core A-share insurers only.
- Quarterly rebalance in Jan/Apr/Jul/Oct.
- Select the 3 lowest PIT-visible P/EV names.
- Equal target weight, 99.5% target exposure.
- No NBV growth score, no solvency guard, no dividend/PB/PE/ROE score, no timing overlay.

PIT rule:
- Embedded value is embedded below from reviewed annual reports.
- A row is usable only when visible_date <= factor_date.
- P/EV = market_cap(CNY 100m) * 100 / embedded_value(CNY million).

Known local comparison contract:
- Local runner used daily open for trade price and daily close for valuation.
- JoinQuant scheduled execution is at 09:40, so small execution differences are expected.
"""


CORE_INSURANCE_CODES = [
    '601318.XSHG',  # Ping An
    '601319.XSHG',  # PICC
    '601336.XSHG',  # New China Life
    '601601.XSHG',  # CPIC
    '601628.XSHG',  # China Life
]


EMBEDDED_VALUE_ROWS = [
    ('601318.XSHG', '2020-12-31', 824574.0, '2021-02-04'),
    ('601318.XSHG', '2021-12-31', 876490.0, '2022-03-18'),
    ('601318.XSHG', '2022-12-31', 874786.0, '2023-03-16'),
    ('601318.XSHG', '2023-12-31', 830974.0, '2024-03-22'),
    ('601318.XSHG', '2024-12-31', 835093.0, '2025-03-20'),
    ('601318.XSHG', '2025-12-31', 928630.0, '2026-03-27'),
    ('601319.XSHG', '2020-12-31', 117244.0, '2021-03-24'),
    ('601319.XSHG', '2021-12-31', 127607.0, '2022-03-26'),
    ('601319.XSHG', '2022-12-31', 122011.0, '2023-03-25'),
    ('601319.XSHG', '2023-12-31', 123965.0, '2024-03-27'),
    ('601319.XSHG', '2024-12-31', 149848.0, '2025-03-28'),
    ('601319.XSHG', '2025-12-31', 159518.0, '2026-03-27'),
    ('601336.XSHG', '2020-12-31', 240604.0, '2021-03-24'),
    ('601336.XSHG', '2021-12-31', 258824.0, '2022-03-30'),
    ('601336.XSHG', '2022-12-31', 255582.0, '2023-03-30'),
    ('601336.XSHG', '2023-12-31', 250510.0, '2024-03-28'),
    ('601336.XSHG', '2024-12-31', 258448.0, '2025-03-28'),
    ('601336.XSHG', '2025-12-31', 287840.0, '2026-03-28'),
    ('601601.XSHG', '2020-12-31', 341348.0, '2021-03-29'),
    ('601601.XSHG', '2021-12-31', 376643.0, '2022-03-28'),
    ('601601.XSHG', '2022-12-31', 398191.0, '2023-03-27'),
    ('601601.XSHG', '2023-12-31', 402027.0, '2024-03-29'),
    ('601601.XSHG', '2024-12-31', 421837.0, '2025-03-27'),
    ('601601.XSHG', '2025-12-31', 465479.0, '2026-03-27'),
    ('601628.XSHG', '2020-12-31', 1072140.0, '2021-03-25'),
    ('601628.XSHG', '2021-12-31', 1203008.0, '2022-03-25'),
    ('601628.XSHG', '2022-12-31', 1230519.0, '2023-03-30'),
    ('601628.XSHG', '2023-12-31', 1260567.0, '2024-03-28'),
    ('601628.XSHG', '2024-12-31', 1401146.0, '2025-03-27'),
    ('601628.XSHG', '2025-12-31', 1467876.0, '2026-03-26'),
]


def initialize(context):
    set_benchmark('399809.XSHE')
    set_option('use_real_price', True)
    set_option('avoid_future_data', True)
    set_order_cost(
        OrderCost(open_commission=0.0003, close_commission=0.0003, min_commission=5),
        type='stock',
    )

    g.strategy_id = 'insurance_pev_value_v53g'
    g.script_version = 'v53g_insurance_pev_value_frozen_20260717'
    g.selection_count = 3
    g.target_exposure = 0.995
    g.max_position_weight = 0.34
    g.min_coverage_ratio = 0.80
    g.rebalance_months = [1, 4, 7, 10]
    g.executed_rebalance_keys = set()
    g.ev_rows = build_ev_rows()
    g.debug = True

    log.info(
        'V5.3g insurance script=%s benchmark=399809.XSHE universe=%d selection_count=%d target_exposure=%.4f'
        % (g.script_version, len(CORE_INSURANCE_CODES), g.selection_count, g.target_exposure)
    )
    log.info('V5.3g frozen rule: lowest PIT P/EV top3 only; no NBV growth, solvency, PB, PE, ROE, dividend or timing overlay.')
    log.info('V5.3g PIT rule: EV row usable only when visible_date <= factor_date; do not tune this file after platform result.')

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
    stocks = get_tradable_core_insurance(context)
    reference_count = len(CORE_INSURANCE_CODES)
    min_required = int(math.ceil(reference_count * g.min_coverage_ratio))
    if len(stocks) < min_required:
        log.info(
            'V5.3g BLOCKED coverage too low date=%s factor_date=%s tradable=%d required=%d reference=%d'
            % (str(current_date), str(factor_date), len(stocks), min_required, reference_count)
        )
        return

    score_df = build_score_frame(stocks, factor_date)
    if score_df is None or len(score_df) == 0:
        log.info('V5.3g BLOCKED empty P/EV score frame date=%s factor_date=%s' % (str(current_date), str(factor_date)))
        return

    selected = score_df.sort_values(['price_to_embedded_value', 'code'], ascending=[True, True]).head(g.selection_count)
    selected_codes = selected['code'].tolist()
    if len(selected_codes) < g.selection_count:
        log.info(
            'V5.3g BLOCKED selected_count below target date=%s factor_date=%s selected=%d target=%d'
            % (str(current_date), str(factor_date), len(selected_codes), g.selection_count)
        )
        return

    target_weight = min(g.max_position_weight, g.target_exposure / float(g.selection_count))
    log.info(
        'V5.3g rebalance date=%s factor_date=%s candidates=%d selected=%s target_weight=%.4f preview=%s'
        % (
            str(current_date),
            str(factor_date),
            len(score_df),
            ','.join(selected_codes),
            target_weight,
            build_score_preview(selected),
        )
    )

    execute_target_weights(context, selected_codes, target_weight)
    g.executed_rebalance_keys.add(key)


def build_score_frame(stocks, factor_date):
    valuation_df = fetch_market_caps(stocks, factor_date)
    if valuation_df is None or len(valuation_df) == 0:
        return pd.DataFrame()

    rows = []
    for _, row in valuation_df.iterrows():
        code = row['code']
        market_cap = safe_float(row.get('market_cap'))
        ev = latest_visible_ev(code, factor_date)
        if ev is None or market_cap is None or market_cap <= 0:
            continue
        pev = market_cap * 100.0 / float(ev['embedded_value'])
        rows.append(
            {
                'code': code,
                'market_cap_100m': market_cap,
                'embedded_value_million': float(ev['embedded_value']),
                'ev_report_period': ev['report_period'],
                'ev_visible_date': str(ev['visible_date']),
                'price_to_embedded_value': pev,
            }
        )
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df = df.dropna(subset=['price_to_embedded_value']).copy()
    return df


def fetch_market_caps(stocks, factor_date):
    q = query(valuation.code, valuation.market_cap).filter(valuation.code.in_(stocks))
    try:
        df = get_fundamentals(q, date=factor_date)
    except Exception as exc:
        log.info('V5.3g fetch_market_caps failed factor_date=%s error=%s' % (str(factor_date), str(exc)))
        return pd.DataFrame()
    if df is None or len(df) == 0:
        return pd.DataFrame()
    return df


def latest_visible_ev(code, factor_date):
    factor_date = to_date(factor_date)
    candidates = []
    for row in g.ev_rows.get(code, []):
        if row['visible_date'] <= factor_date:
            candidates.append(row)
    if not candidates:
        return None
    candidates = sorted(candidates, key=lambda item: (item['visible_date'], item['report_period']))
    return candidates[-1]


def build_ev_rows():
    data = {}
    for code, report_period, embedded_value, visible_date in EMBEDDED_VALUE_ROWS:
        data.setdefault(code, []).append(
            {
                'code': code,
                'report_period': report_period,
                'embedded_value': float(embedded_value),
                'visible_date': to_date(visible_date),
            }
        )
    for code in data:
        data[code] = sorted(data[code], key=lambda item: (item['visible_date'], item['report_period']))
    return data


def get_tradable_core_insurance(context):
    current_data = get_current_data()
    tradable = []
    for code in CORE_INSURANCE_CODES:
        try:
            item = current_data[code]
        except Exception:
            continue
        if getattr(item, 'paused', False):
            continue
        if getattr(item, 'is_st', False):
            continue
        tradable.append(code)
    return tradable


def execute_target_weights(context, selected_codes, target_weight):
    selected_set = set(selected_codes)
    for code in list(context.portfolio.positions.keys()):
        if code not in selected_set:
            log.info('V5.3g sell target zero code=%s' % code)
            order_target_value(code, 0)

    target_value = context.portfolio.total_value * float(target_weight)
    for code in selected_codes:
        log.info('V5.3g buy/hold target code=%s weight=%.4f target_value=%.2f' % (code, target_weight, target_value))
        order_target_value(code, target_value)


def get_previous_trade_date(context):
    current_date = context.current_dt.date()
    days = get_trade_days(end_date=current_date, count=2)
    if days is None or len(days) == 0:
        return current_date
    if len(days) == 1:
        return to_date(days[0])
    return to_date(days[-2])


def after_trading_end_log(context):
    current_date = context.current_dt.date()
    value = context.portfolio.total_value
    cash = context.portfolio.cash
    positions = []
    for code, pos in context.portfolio.positions.items():
        if pos.total_amount > 0:
            positions.append('%s:%d' % (code, pos.total_amount))
    log.info(
        'V5.3g EOD date=%s total_value=%.2f cash=%.2f positions=%s'
        % (str(current_date), value, cash, ';'.join(positions))
    )


def build_score_preview(df):
    parts = []
    for _, row in df.iterrows():
        parts.append(
            '%s pev=%.4f mcap=%.2f ev=%.1f report=%s visible=%s'
            % (
                row['code'],
                float(row['price_to_embedded_value']),
                float(row['market_cap_100m']),
                float(row['embedded_value_million']),
                str(row['ev_report_period']),
                str(row['ev_visible_date']),
            )
        )
    return ' | '.join(parts)


def safe_float(value):
    if value is None:
        return None
    try:
        result = float(value)
    except Exception:
        return None
    if np.isnan(result) or np.isinf(result):
        return None
    return result


def to_date(value):
    if hasattr(value, 'date'):
        return value.date()
    if isinstance(value, str):
        return datetime.strptime(value[:10], '%Y-%m-%d').date()
    return value

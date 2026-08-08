from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.v5j_frozen_buy_timing_full_pit_validation_runner import _load_event_days
from v5.v5j_pit_pool_1min_pairing_runner import _paired
from v5.v5j_v5e_profit_lock_sell_timing_proxy_runner import _daily_ohlc_archive

OUT = Path('v5j_1min_technical_pattern_diagnostic') / 'current'
DB = Path('\u6570\u636e\u5e93') / 'processed' / 'pre2021_repaired_multisleeve_pit_pool_v5'
POOL = DB / 'repaired_multisleeve_pit_pool.csv'
MANIFEST = Path('v5j_pit_pool_1min_pairing') / 'current' / 'v5j_pit_pool_1min_event_manifest.csv'
GATE = Path('v5j_cross_period_technical_validation_gate') / 'current' / 'v5j_cross_period_data_gate_summary.json'
OBSERVATION_TIME = '10:00:00'
FILL_TIME = '10:01:00'
FEATURES = ('price_vs_vwap', 'ema_5_20', 'rsi_14', 'opening_range_30m')


def run_v5j_1min_technical_pattern_diagnostic(root: Path = Path('.')) -> dict[str, Any]:
    gate = json.loads((root / GATE).read_text(encoding='utf-8'))
    if not gate.get('technical_rule_validation_allowed'):
        raise RuntimeError('PIT data gate has not allowed 1-minute technical diagnostics.')
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    pool = [row for row in _csv(root / POOL) if row.get('pool_eligibility') == 'eligible_for_predecessor_pool']
    manifest = {row['event_id']: row for row in _csv(root / MANIFEST)}
    events = [
        row for row in pool
        if _paired(manifest.get(f"{row['rebalance_date']}|{row['code']}|{row['sleeve_id']}", {}))
    ]
    daily = _daily_ohlc_archive(root, {row['code'] for row in events})
    next_close = _next_close_map(daily)
    day_bars = _load_event_days(root, events)
    rows = [_evaluate(event, day_bars.get(_event_id(event), []), next_close) for event in events]
    condition_results = _condition_results(rows)
    sleeve_year = _sleeve_year_results(rows)
    audits = _audits(events, rows)
    decision = _decision(condition_results, sleeve_year, audits)
    _write(out / 'v5j_1min_technical_feature_schema.csv', _schema())
    _write(out / 'v5j_1min_technical_pattern_events.csv', rows)
    _write(out / 'v5j_1min_technical_pattern_condition_results.csv', condition_results)
    _write(out / 'v5j_1min_technical_pattern_sleeve_year.csv', sleeve_year)
    _write(out / 'v5j_1min_technical_pattern_pit_governance_audit.csv', audits)
    _write(out / 'v5j_1min_technical_pattern_pm_gate.csv', [decision])
    _write(out / 'v5j_1min_technical_pattern_blockers.csv', _blockers(audits, decision))
    _write(out / 'v5j_1min_technical_pattern_next_queue.csv', _next_queue(decision))
    summary = {
        'created_at_utc': _now(),
        'task': 'v5j_1min_technical_pattern_diagnostic',
        'validation_window': '2013-01-01_to_2021-04-30',
        'observation_time': OBSERVATION_TIME,
        'fill_time': FILL_TIME,
        'pit_candidate_event_count': len(events),
        'executable_event_count': sum(row['pit_status'] == 'pass' for row in rows),
        'fixed_standard_indicator_count': len(FEATURES),
        'stock_selection_rebuilt': False,
        'weight_change_used': False,
        'parameter_scan_used': False,
        'accepted': False,
        'pm_gate_decision': decision['pm_gate_decision'],
    }
    (out / 'v5j_1min_technical_pattern_summary.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    (out / 'v5j_1min_technical_pattern_report.md').write_text(_report(summary, condition_results, decision), encoding='utf-8')
    return summary


def _event_id(row: dict[str, str]) -> str:
    return f"{row['rebalance_date']}|{row['code']}|{row['sleeve_id']}"


def _next_close_map(daily: dict[str, list[dict[str, Any]]]) -> dict[tuple[str, str], float]:
    result = {}
    for code, series in daily.items():
        for index, row in enumerate(series[:-1]):
            result[(code, row['date'])] = _f(series[index + 1].get('close'))
    return result


def _evaluate(event: dict[str, str], bars: list[dict[str, str]], next_close: dict[tuple[str, str], float]) -> dict[str, Any]:
    visible = [row for row in bars if row.get('time', '') <= OBSERVATION_TIME]
    index = {row['time']: row for row in bars}
    observation, fill = index.get(OBSERVATION_TIME), index.get(FILL_TIME)
    close = _f(observation.get('close')) if observation else 0.0
    fill_price = _f(fill.get('open')) if fill else 0.0
    volume = sum(_f(row.get('volume')) for row in visible)
    amount = sum(_f(row.get('amount')) for row in visible)
    vwap = amount / volume if volume else 0.0
    closes = [_f(row.get('close')) for row in visible]
    ema_5, ema_20 = _ema(closes, 5), _ema(closes, 20)
    rsi = _rsi(closes, 14)
    prior = [row for row in visible if row.get('time') < OBSERVATION_TIME]
    prior_high = max((_f(row.get('high')) for row in prior), default=0.0)
    prior_low = min((_f(row.get('low')) for row in prior if _f(row.get('low')) > 0), default=0.0)
    day_close = _f(bars[-1].get('close')) if bars else 0.0
    following_close = next_close.get((event['code'], event['rebalance_date']), 0.0)
    return {
        'event_id': _event_id(event), 'rebalance_date': event['rebalance_date'], 'year': event['rebalance_date'][:4],
        'code': event['code'], 'sleeve_id': event['sleeve_id'], 'minute_row_count': len(bars),
        'vwap_to_1000': vwap, 'close_1000': close, 'price_vs_vwap_bps': (close / vwap - 1.0) * 10000 if close and vwap else '',
        'price_vs_vwap_state': 'above' if close > vwap else 'below_or_equal' if close and vwap else 'missing',
        'ema_5': ema_5, 'ema_20': ema_20, 'ema_spread_bps': (ema_5 / ema_20 - 1.0) * 10000 if ema_5 and ema_20 else '',
        'ema_5_20_state': 'bullish' if ema_5 > ema_20 else 'bearish_or_equal' if ema_5 and ema_20 else 'missing',
        'rsi_14': rsi, 'rsi_14_state': 'oversold' if rsi < 30 else 'overbought' if rsi > 70 else 'neutral' if rsi else 'missing',
        'prior_30m_high': prior_high, 'prior_30m_low': prior_low,
        'opening_range_30m_state': 'breakout_up' if close > prior_high > 0 else 'breakout_down' if prior_low > 0 and close < prior_low else 'inside_range' if close else 'missing',
        'entry_price_1001': fill_price, 'same_day_close': day_close, 'next_trading_day_close': following_close,
        'same_day_forward_return_bps': (day_close / fill_price - 1.0) * 10000 if day_close and fill_price else '',
        'next_day_forward_return_bps': (following_close / fill_price - 1.0) * 10000 if following_close and fill_price else '',
        'future_return_used_for_evaluation_only': True,
        'pit_status': 'pass' if close and fill_price and vwap and following_close else 'missing_required_bar_or_next_close',
        'accepted': False,
    }


def _ema(values: list[float], period: int) -> float:
    if not values:
        return 0.0
    alpha = 2.0 / (period + 1.0)
    value = values[0]
    for item in values[1:]:
        value = alpha * item + (1.0 - alpha) * value
    return value


def _rsi(values: list[float], period: int) -> float:
    if len(values) <= period:
        return 0.0
    changes = [values[index] - values[index - 1] for index in range(1, len(values))][-period:]
    gains = sum(max(change, 0.0) for change in changes) / period
    losses = sum(max(-change, 0.0) for change in changes) / period
    if losses == 0.0:
        return 100.0 if gains > 0.0 else 50.0
    return 100.0 - 100.0 / (1.0 + gains / losses)


def _condition_results(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row['pit_status'] != 'pass':
            continue
        for feature in FEATURES:
            grouped[(feature, row[f'{feature}_state'])].append(row)
    result = []
    for (feature, state), values in sorted(grouped.items()):
        same_day = [_f(row['same_day_forward_return_bps']) for row in values]
        next_day = [_f(row['next_day_forward_return_bps']) for row in values]
        result.append({
            'feature_id': feature, 'state': state, 'event_count': len(values),
            'mean_same_day_forward_return_bps': sum(same_day) / len(same_day),
            'mean_next_day_forward_return_bps': sum(next_day) / len(next_day),
            'median_next_day_forward_return_bps': _median(next_day),
            'positive_next_day_ratio': sum(value > 0 for value in next_day) / len(next_day),
            'diagnostic_only': True, 'accepted': False,
        })
    return result


def _sleeve_year_results(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for feature in FEATURES:
        groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            if row['pit_status'] == 'pass':
                groups[(row['year'], row['sleeve_id'], row[f'{feature}_state'])].append(row)
        for (year, sleeve, state), values in sorted(groups.items()):
            outcomes = [_f(row['next_day_forward_return_bps']) for row in values]
            result.append({'feature_id': feature, 'year': year, 'sleeve_id': sleeve, 'state': state, 'event_count': len(values), 'mean_next_day_forward_return_bps': sum(outcomes) / len(outcomes)})
    return result


def _audits(events: list[dict[str, str]], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {'audit_id': 'pit_candidate_pool_only', 'status': 'pass', 'detail': len(events)},
        {'audit_id': 'completed_bars_only', 'status': 'pass', 'detail': f'signals through {OBSERVATION_TIME}; reference fill at {FILL_TIME}'},
        {'audit_id': 'future_outcomes_not_signals', 'status': 'pass', 'detail': True},
        {'audit_id': 'no_stock_selection_or_weight_change', 'status': 'pass', 'detail': True},
        {'audit_id': 'no_parameter_scan', 'status': 'pass', 'detail': False},
        {'audit_id': 'minute_and_next_close_coverage', 'status': 'pass' if all(row['pit_status'] == 'pass' for row in rows) else 'review', 'detail': sum(row['pit_status'] != 'pass' for row in rows)},
    ]


def _decision(results: list[dict[str, Any]], sleeve_year: list[dict[str, Any]], audits: list[dict[str, Any]]) -> dict[str, Any]:
    coverage_ok = next(row for row in audits if row['audit_id'] == 'minute_and_next_close_coverage')['status'] == 'pass'
    comparisons = []
    for feature, up, down in (
        ('price_vs_vwap', 'above', 'below_or_equal'),
        ('ema_5_20', 'bullish', 'bearish_or_equal'),
        ('rsi_14', 'oversold', 'overbought'),
        ('opening_range_30m', 'breakout_up', 'breakout_down'),
    ):
        left = next((row for row in results if row['feature_id'] == feature and row['state'] == up), None)
        right = next((row for row in results if row['feature_id'] == feature and row['state'] == down), None)
        if left and right:
            cells: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
            for row in sleeve_year:
                if row['feature_id'] == feature and row['state'] in {up, down}:
                    cells[(row['year'], row['sleeve_id'])][row['state']] = _f(row['mean_next_day_forward_return_bps'])
            deltas = [state[up] - state[down] for state in cells.values() if up in state and down in state]
            edge = _f(left['mean_next_day_forward_return_bps']) - _f(right['mean_next_day_forward_return_bps'])
            comparisons.append({
                'feature': feature, 'edge': edge, 'comparable_cell_count': len(deltas),
                'positive_cell_ratio': sum(delta > 0 for delta in deltas) / len(deltas) if deltas else 0.0,
                'minimum_state_event_count': min(int(left['event_count']), int(right['event_count'])),
            })
    strongest = max(comparisons, key=lambda item: abs(item['edge'])) if comparisons else {'feature': '', 'edge': 0.0, 'comparable_cell_count': 0, 'positive_cell_ratio': 0.0, 'minimum_state_event_count': 0}
    stable = [item for item in comparisons if item['edge'] >= 10.0 and item['positive_cell_ratio'] >= 0.60 and item['comparable_cell_count'] >= 24 and item['minimum_state_event_count'] >= 200]
    gate = 'diagnostic_only_no_stable_technical_edge'
    if coverage_ok and stable:
        gate = 'diagnostic_signal_requires_separate_cross_period_spec_not_accepted'
    return {
        'pm_gate_decision': gate, 'largest_pre_registered_state_spread_feature': strongest['feature'],
        'largest_next_day_state_spread_bps': strongest['edge'], 'largest_spread_positive_sleeve_year_ratio': strongest['positive_cell_ratio'],
        'largest_spread_comparable_sleeve_year_count': strongest['comparable_cell_count'],
        'stable_expected_direction_feature_count': len(stable), 'accepted': False,
        'reason': 'Promotion needs the pre-registered expected direction, at least 60% same-direction sleeve-year cells, 24 comparable cells, and 200 events per compared state; no threshold is chosen from returns.',
    }


def _schema() -> list[dict[str, str]]:
    return [
        {'feature_id': 'price_vs_vwap', 'formula': '10:00 close relative to cumulative session VWAP', 'states': 'above; below_or_equal'},
        {'feature_id': 'ema_5_20', 'formula': '1-minute EMA(5) relative to EMA(20), calculated through 10:00', 'states': 'bullish; bearish_or_equal'},
        {'feature_id': 'rsi_14', 'formula': 'standard RSI(14) on 1-minute closes through 10:00', 'states': 'oversold; neutral; overbought'},
        {'feature_id': 'opening_range_30m', 'formula': '10:00 close relative to 09:31-09:59 high/low range', 'states': 'breakout_up; breakout_down; inside_range'},
    ]


def _blockers(audits: list[dict[str, Any]], decision: dict[str, Any]) -> list[dict[str, Any]]:
    return [{'blocker_id': row['audit_id'], 'status': row['status'], 'detail': row['detail']} for row in audits if row['status'] != 'pass'] + [{'blocker_id': 'promotion', 'status': 'blocked', 'detail': decision['pm_gate_decision']}]


def _next_queue(decision: dict[str, Any]) -> list[dict[str, str]]:
    return [{'priority': 'P0', 'next_task': 'keep_v5i_technical_analysis_diagnostic_only', 'status': 'ready', 'reason': decision['pm_gate_decision']}]


def _median(values: list[float]) -> float:
    values = sorted(values)
    return 0.0 if not values else values[len(values) // 2] if len(values) % 2 else (values[len(values) // 2 - 1] + values[len(values) // 2]) / 2.0


def _f(value: Any) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ['empty']
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(rows)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _report(summary: dict[str, Any], results: list[dict[str, Any]], decision: dict[str, Any]) -> str:
    lines = ['# V5j 1-minute technical pattern diagnostic', '', f"- PIT events: `{summary['executable_event_count']}/{summary['pit_candidate_event_count']}`.", f"- PM gate: `{decision['pm_gate_decision']}`.", '- Fixed classic indicators only; no technical state was converted into a trade rule.', '', '## State Results', '']
    for row in results:
        lines.append(f"- `{row['feature_id']}:{row['state']}`: n={row['event_count']}, next-day mean={float(row['mean_next_day_forward_return_bps']):.2f} bps.")
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    print(json.dumps(run_v5j_1min_technical_pattern_diagnostic(), ensure_ascii=False, indent=2))

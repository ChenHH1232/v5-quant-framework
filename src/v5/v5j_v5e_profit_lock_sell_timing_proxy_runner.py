from __future__ import annotations

import csv
import io
import json
import math
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUT = Path('v5j_v5e_profit_lock_sell_timing_proxy') / 'current'
DB = Path('\u6570\u636e\u5e93') / 'processed' / 'pre2021_repaired_multisleeve_pit_pool_v5'
POOL = DB / 'repaired_multisleeve_pit_pool.csv'
FACTORS = Path('v5j_local_adjust_factor_corporate_action') / 'current' / 'v5j_local_adjust_factor_panel.csv'
GATE = Path('v5j_cross_period_technical_validation_gate') / 'current' / 'v5j_cross_period_data_gate_summary.json'
MINUTE = Path('\u6570\u636e\u5e93') / 'processed' / 'local_1min_clean_2013_2026' / 'by_year'
ARCHIVE_PARTS = ('\u4e00\u5206\u949f\u884c\u60c5\u6570\u636e 2000\u81f32026', '\u80a1\u7968\u5168\u5468\u671fK\u7ebf\u5305', '\u5386\u53f2\u6570\u636e', 'a\u80a1\u65e5\u7ebf.zip')
THRESHOLD = 0.20
RULES = (
    'open_control',
    'vwap_1000_protect_else_1400',
    'two_5m_vwap_break_1000_else_1400',
    'vwap_1400_hold_to_1445',
)


def run_v5j_v5e_profit_lock_sell_timing_proxy(root: Path = Path('.')) -> dict[str, Any]:
    gate = json.loads((root / GATE).read_text(encoding='utf-8'))
    if not gate.get('technical_rule_validation_allowed'):
        raise RuntimeError('PIT data gate has not allowed frozen technical validation.')
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    pool = [row for row in _csv(root / POOL) if row.get('pool_eligibility') == 'eligible_for_predecessor_pool']
    daily = _daily_ohlc_archive(root, {row['code'] for row in pool})
    factors = _factors(_csv(root / FACTORS))
    triggers = _triggers(pool, daily, factors)
    bars = _load_days(root, triggers)
    events = [event for trigger in triggers for event in _evaluate(trigger, bars.get(trigger['event_id'], []))]
    results = _results(events)
    yearly = _yearly(events)
    audits = _audits(triggers, events)
    decision = _decision(results, yearly, audits)
    _write(out / 'v5j_v5e_profit_lock_proxy_trigger_ledger.csv', triggers)
    _write(out / 'v5j_v5e_profit_lock_proxy_sell_events.csv', events)
    _write(out / 'v5j_v5e_profit_lock_proxy_results.csv', results)
    _write(out / 'v5j_v5e_profit_lock_proxy_yearly_sleeve.csv', yearly)
    _write(out / 'v5j_v5e_profit_lock_proxy_governance_audit.csv', audits)
    _write(out / 'v5j_v5e_profit_lock_proxy_pm_gate.csv', [decision])
    summary = {
        'created_at_utc': _now(),
        'task': 'v5j_v5e_profit_lock_sell_timing_proxy',
        'validation_window': '2013-01-01_to_2021-04-30',
        'profit_lock_threshold': THRESHOLD,
        'sell_fraction': 0.5,
        'entry_cost_basis': 'local_daily_ohlc_rebalance_day_open_adjusted_by_local_factor',
        'candidate_holding_period_count': len(pool),
        'trigger_count': len(triggers),
        'fillable_trigger_count': len({row['event_id'] for row in events if row['pit_status'] == 'pass'}),
        'fixed_sell_rule_count': len(RULES),
        'technical_rule_validation_started': True,
        'scope': 'pre2021_v5e_profit_lock_single_stock_proxy_on_pit_candidates_not_rebuilt_portfolio',
        'threshold_scan_used': False,
        'accepted': False,
        'pm_gate_decision': decision['pm_gate_decision'],
    }
    (out / 'v5j_v5e_profit_lock_proxy_summary.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    (out / 'v5j_v5e_profit_lock_proxy_report.md').write_text(_report(summary, results, decision), encoding='utf-8')
    return summary


def _daily_ohlc_archive(root: Path, codes: set[str]) -> dict[str, list[dict[str, Any]]]:
    """The local archive is the authoritative entry-day OHLC source for this proxy."""
    archive = root.resolve().parent.parent.joinpath(*ARCHIVE_PARTS)
    if not archive.exists():
        raise FileNotFoundError(f'Local daily OHLC archive is required: {archive}')
    local_to_code = {_local_code(code): code for code in codes}
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with zipfile.ZipFile(archive) as handle:
        names = {Path(name).name.upper(): name for name in handle.namelist() if name.lower().endswith('.csv')}
        missing = []
        for local, code in local_to_code.items():
            name = names.get(f'{local}.CSV')
            if not name:
                missing.append(local)
                continue
            for row in csv.reader(io.StringIO(_decode_archive_csv(handle.read(name)))):
                if len(row) < 6 or not row[1:2] or not row[1].isdigit():
                    continue
                trade_date = f'{row[1][:4]}-{row[1][4:6]}-{row[1][6:8]}'
                opening, closing = _f(row[2]), _f(row[5])
                if opening > 0 and closing > 0:
                    result[code].append({'date': trade_date, 'open': opening, 'close': closing, 'price_source': 'local_daily_ohlc_archive'})
    for local in missing:
        code = local_to_code[local]
        result[code] = _daily_ohlc_from_minute(root, code)
        if not result[code]:
            raise RuntimeError(f'Neither the daily archive nor local 1-minute source has usable OHLC for {local}.')
    for series in result.values():
        series.sort(key=lambda item: item['date'])
    return result


def _daily_ohlc_from_minute(root: Path, code: str) -> list[dict[str, Any]]:
    """Narrow corporate-action fallback for archive-absent securities; no substitute is used."""
    by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for year in range(2013, 2022):
        path = root / MINUTE / str(year) / f"{code.replace('.', '_')}_1min.csv"
        if not path.exists():
            continue
        for row in _csv(path):
            if row.get('trade_date'):
                by_date[row['trade_date']].append(row)
    rebuilt = []
    for trade_date, bars in by_date.items():
        bars.sort(key=lambda row: row.get('time', ''))
        opening, closing = _f(bars[0].get('open')), _f(bars[-1].get('close'))
        if opening > 0 and closing > 0:
            rebuilt.append({'date': trade_date, 'open': opening, 'close': closing, 'price_source': 'local_1min_daily_ohlc_rebuild'})
    return rebuilt


def _local_code(code: str) -> str:
    return f"{code[:6]}.{'SH' if code.endswith('XSHG') else 'SZ'}"


def _decode_archive_csv(raw: bytes) -> str:
    for encoding in ('utf-8-sig', 'gb18030', 'gbk'):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError('Could not decode local daily OHLC archive CSV.')


def _factors(rows: list[dict[str, str]]) -> dict[tuple[str, str], float]:
    return {(row['code'], row['trade_date']): _f(row.get('adjust_factor')) for row in rows if _f(row.get('adjust_factor')) > 0}


def _triggers(pool: list[dict[str, str]], daily: dict[str, list[dict[str, Any]]], factors: dict[tuple[str, str], float]) -> list[dict[str, Any]]:
    dates = sorted({row['rebalance_date'] for row in pool})
    next_rebalance = {date: dates[index + 1] for index, date in enumerate(dates[:-1])}
    result = []
    for candidate in pool:
        period_start = candidate['rebalance_date']
        period_end = next_rebalance.get(period_start, '')
        if not period_end:
            continue
        series = [row for row in daily.get(candidate['code'], []) if period_start <= row['date'] < period_end]
        if len(series) < 2:
            continue
        entry = series[0]
        entry_factor = factors.get((candidate['code'], entry['date']))
        if entry['open'] <= 0 or not entry_factor:
            continue
        for index, row in enumerate(series[:-1]):
            factor = factors.get((candidate['code'], row['date']))
            if not factor:
                continue
            holding_return = row['close'] * factor / (entry['open'] * entry_factor) - 1.0
            if holding_return >= THRESHOLD:
                result.append({
                    'event_id': f"{period_start}|{candidate['code']}|{candidate['sleeve_id']}|{row['date']}",
                    'code': candidate['code'], 'sleeve_id': candidate['sleeve_id'],
                    'entry_date': entry['date'], 'entry_price_open': entry['open'],
                    'entry_price_source': entry.get('price_source', 'unknown'), 'entry_adjust_factor': entry_factor,
                    'trigger_date': row['date'], 'trigger_adjusted_close': row['close'] * factor,
                    'holding_return_adjusted': holding_return, 'execution_date': series[index + 1]['date'],
                    'scheduled_period_end': period_end, 'profit_threshold': THRESHOLD, 'sell_fraction': 0.5,
                    'trigger_source': 'frozen_v5e_profit_lock_20pct_sell50_single_stock_proxy',
                    'future_return_used_for_trigger': False, 'accepted': False,
                })
                break
    return result


def _load_days(root: Path, events: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[(event['code'], event['execution_date'][:4])].append(event)
    result: dict[str, list[dict[str, str]]] = {}
    for (code, year), members in grouped.items():
        path = root / MINUTE / year / f"{code.replace('.', '_')}_1min.csv"
        wanted = {event['execution_date'] for event in members}
        by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
        if path.exists():
            for row in _csv(path):
                if row.get('trade_date') in wanted:
                    by_date[row['trade_date']].append(row)
        for event in members:
            result[event['event_id']] = by_date.get(event['execution_date'], [])
    return result


def _evaluate(event: dict[str, Any], bars: list[dict[str, str]]) -> list[dict[str, Any]]:
    index = {row['time']: row for row in bars}
    feature_0955, feature_1000, feature_1400 = _feature(bars, '09:55:00'), _feature(bars, '10:00:00'), _feature(bars, '14:00:00')
    two_break = feature_0955['below'] and feature_1000['below']
    variants = [
        ('open_control', '09:31:00', True),
        ('vwap_1000_protect_else_1400', '10:01:00' if feature_1000['below'] else '14:01:00', feature_1000['available']),
        ('two_5m_vwap_break_1000_else_1400', '10:01:00' if two_break else '14:01:00', feature_1000['available']),
        ('vwap_1400_hold_to_1445', '14:01:00' if feature_1400['below'] else '14:46:00', feature_1400['available']),
    ]
    control = _fill(index, '09:31:00')
    control_price = _f(control.get('open')) if control else 0.0
    result = []
    for candidate_id, selected_time, available in variants:
        fill = control if candidate_id == 'open_control' else _fill(index, selected_time)
        fallback = False
        if not available or not fill:
            fill, fallback = control, True
        selected_price = _f(fill.get('open')) if fill else 0.0
        result.append({
            **event, 'year': event['execution_date'][:4], 'candidate_id': candidate_id,
            'selected_execution_time': selected_time, 'fallback_used': fallback, 'minute_row_count': len(bars),
            'control_open': control_price, 'selected_open': selected_price,
            'sell_proceeds_delta_bps': (selected_price / control_price - 1.0) * 10000 if selected_price and control_price else '',
            'close_1000_lte_vwap': feature_1000['below'], 'two_5m_vwap_break': two_break,
            'close_1400_lte_vwap': feature_1400['below'],
            'pit_status': 'pass' if control_price and selected_price else 'missing_required_bar',
            'completed_bar_only': True, 'accepted': False,
        })
    return result


def _feature(bars: list[dict[str, str]], until: str) -> dict[str, Any]:
    visible = [row for row in bars if row['time'] <= until]
    volume, amount = sum(_f(row.get('volume')) for row in visible), sum(_f(row.get('amount')) for row in visible)
    at_time = next((row for row in visible if row['time'] == until), None)
    vwap = amount / volume if volume else 0.0
    close = _f(at_time.get('close')) if at_time else 0.0
    return {'available': bool(at_time and volume > 0), 'below': bool(close and vwap and close <= vwap)}


def _fill(index: dict[str, dict[str, str]], moment: str) -> dict[str, str] | None:
    row = index.get(moment)
    return row if row and _f(row.get('volume')) > 0 else None


def _results(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for candidate_id, values in sorted(_group(rows, lambda item: item['candidate_id']).items()):
        good = [item for item in values if item['pit_status'] == 'pass']
        deltas = [_f(item['sell_proceeds_delta_bps']) for item in good]
        result.append({
            'candidate_id': candidate_id, 'event_count': len(values), 'fillable_event_count': len(good),
            'fallback_count': sum(item['fallback_used'] for item in values),
            'mean_sell_proceeds_delta_bps': sum(deltas) / len(deltas) if deltas else 0.0,
            'median_sell_proceeds_delta_bps': _median(deltas),
            'positive_event_ratio': sum(delta > 0 for delta in deltas) / len(deltas) if deltas else 0.0,
            'accepted': False,
        })
    return result


def _yearly(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for (candidate_id, year, sleeve_id), values in sorted(_group(rows, lambda item: (item['candidate_id'], item['year'], item['sleeve_id'])).items()):
        good = [item for item in values if item['pit_status'] == 'pass']
        deltas = [_f(item['sell_proceeds_delta_bps']) for item in good]
        result.append({
            'candidate_id': candidate_id, 'year': year, 'sleeve_id': sleeve_id, 'event_count': len(good),
            'mean_sell_proceeds_delta_bps': sum(deltas) / len(deltas) if deltas else 0.0,
            'positive_event_ratio': sum(delta > 0 for delta in deltas) / len(deltas) if deltas else 0.0,
        })
    return result


def _audits(triggers: list[dict[str, Any]], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    missing = sum(row['pit_status'] != 'pass' for row in events if row['candidate_id'] == 'open_control')
    return [
        {'audit_id': 'frozen_20pct_sell50_only', 'status': 'pass', 'detail': THRESHOLD},
        {'audit_id': 'entry_cost_basis', 'status': 'pass', 'detail': 'local daily archive entry-day open with local adjustment factor; archive-absent corporate-action codes rebuild from their own 1-minute bars'},
        {'audit_id': 'entry_and_trigger_pit', 'status': 'pass', 'detail': 'entry open and same-date close only'},
        {'audit_id': 'tplus1_execution', 'status': 'pass', 'detail': 'execution is next observed trading date'},
        {'audit_id': 'candidate_pool_only', 'status': 'pass', 'detail': len(triggers)},
        {'audit_id': 'no_parameter_scan', 'status': 'pass', 'detail': False},
        {'audit_id': 'minute_fill_coverage', 'status': 'pass' if missing == 0 else 'review', 'detail': missing},
    ]


def _decision(results: list[dict[str, Any]], yearly: list[dict[str, Any]], audits: list[dict[str, Any]]) -> dict[str, Any]:
    technical = [row for row in results if row['candidate_id'] != 'open_control']
    if not technical:
        return {'pm_gate_decision': 'blocked_by_missing_proxy_events', 'accepted': False, 'reason': 'No fillable V5e-like profit-lock proxy events.'}
    best = max(technical, key=lambda row: _f(row['mean_sell_proceeds_delta_bps']))
    units = [row for row in yearly if row['candidate_id'] == best['candidate_id'] and row['event_count'] > 0]
    positive = sum(_f(row['mean_sell_proceeds_delta_bps']) > 0 for row in units)
    stable = bool(units) and positive / len(units) >= 0.60
    decision = 'v5e_profit_lock_proxy_sell_timing_positive_ready_for_separate_v5i_spec_not_accepted' if _f(best['mean_sell_proceeds_delta_bps']) > 0 and _f(best['positive_event_ratio']) >= 0.5 and stable else 'v5e_profit_lock_proxy_sell_timing_not_stable_keep_diagnostic_only'
    return {
        'pm_gate_decision': decision, 'best_fixed_candidate': best['candidate_id'],
        'best_mean_sell_proceeds_delta_bps': best['mean_sell_proceeds_delta_bps'],
        'best_positive_event_ratio': best['positive_event_ratio'],
        'positive_year_sleeve_ratio': positive / len(units) if units else 0.0, 'accepted': False,
        'reason': 'Pre-2021 proxy uses frozen profit-lock economics but PIT candidate holdings, not formal V5e portfolio history.',
    }


def _group(rows: list[dict[str, Any]], key: Any) -> dict[Any, list[dict[str, Any]]]:
    result: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        result[key(row)].append(row)
    return result


def _median(values: list[float]) -> float:
    values = sorted(values)
    if not values:
        return 0.0
    return values[len(values) // 2] if len(values) % 2 else (values[len(values) // 2 - 1] + values[len(values) // 2]) / 2


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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(rows)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _report(summary: dict[str, Any], results: list[dict[str, Any]], decision: dict[str, Any]) -> str:
    lines = [
        '# V5e profit-lock proxy sell timing',
        '',
        f"- Frozen `+20% sell50` triggers: `{summary['trigger_count']}`.",
        '- Entry cost basis is the local daily-archive rebalance-day open, adjusted by the local factor panel.',
        f"- PM gate: `{decision['pm_gate_decision']}`.",
        '- This is a single-stock PIT candidate proxy, not an accepted V5e portfolio result.',
        '',
        '## Fixed Window Results',
        '',
    ]
    for row in results:
        lines.append(f"- `{row['candidate_id']}`: mean `{row['mean_sell_proceeds_delta_bps']:.2f}` bps; positive-event ratio `{row['positive_event_ratio']:.2%}`.")
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    print(json.dumps(run_v5j_v5e_profit_lock_sell_timing_proxy(), ensure_ascii=False, indent=2))

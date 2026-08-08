from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.v5j_v5e_profit_lock_sell_timing_proxy_runner import _daily_ohlc_archive, _factors

OUT = Path('v5j_family_specific_sell_timing_diagnostic') / 'current'
DB = Path('\u6570\u636e\u5e93') / 'processed' / 'pre2021_repaired_multisleeve_pit_pool_v5'
POOL = DB / 'repaired_multisleeve_pit_pool.csv'
FACTORS = Path('v5j_local_adjust_factor_corporate_action') / 'current' / 'v5j_local_adjust_factor_panel.csv'
GATE = Path('v5j_cross_period_technical_validation_gate') / 'current' / 'v5j_cross_period_data_gate_summary.json'
EXIT_EVENTS = Path('v5j_frozen_sell_timing_full_pit_validation') / 'current' / 'v5j_frozen_sell_timing_full_pit_events.csv'
FAMILIES = ('value_core', 'momentum_12_1_top_tercile', 'mean_reversion_20d_bottom_tercile')


def run_v5j_family_specific_sell_timing_diagnostic(root: Path = Path('.')) -> dict[str, Any]:
    gate = json.loads((root / GATE).read_text(encoding='utf-8'))
    if not gate.get('technical_rule_validation_allowed'):
        raise RuntimeError('PIT data gate has not allowed family-specific exit diagnostics.')
    if not (root / EXIT_EVENTS).exists():
        raise FileNotFoundError(f'Frozen sell-window event source is required: {root / EXIT_EVENTS}')
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    pool = [row for row in _csv(root / POOL) if row.get('pool_eligibility') == 'eligible_for_predecessor_pool']
    daily = _daily_ohlc_archive(root, {row['code'] for row in pool})
    factors = _factors(_csv(root / FACTORS))
    cohorts, signals = _cohorts(pool, daily, factors)
    selected_events = _attach_cohorts(_csv(root / EXIT_EVENTS), cohorts)
    results = _results(selected_events)
    yearly = _yearly(selected_events)
    audits = _audits(pool, selected_events)
    decision = _decision(results, yearly, audits)
    _write(out / 'v5j_family_sell_signal_cohort.csv', signals)
    _write(out / 'v5j_family_sell_timing_events.csv', selected_events)
    _write(out / 'v5j_family_sell_timing_results.csv', results)
    _write(out / 'v5j_family_sell_timing_sleeve_year.csv', yearly)
    _write(out / 'v5j_family_sell_timing_governance_audit.csv', audits)
    _write(out / 'v5j_family_sell_timing_pm_gate.csv', [decision])
    _write(out / 'v5j_family_sell_timing_next_queue.csv', _next_queue(decision))
    summary = {
        'created_at_utc': _now(), 'task': 'v5j_family_specific_sell_timing_diagnostic',
        'validation_window': '2013-01-01_to_2021-04-30',
        'value_family': 'all original PIT value/low-volatility pool holdings',
        'momentum_family': 'top within-sleeve pre-entry 12-1 adjusted-close return cohort',
        'mean_reversion_family': 'bottom within-sleeve pre-entry 20-trading-day adjusted-close return cohort',
        'family_count': len(FAMILIES), 'pool_event_count': len(pool),
        'value_core_intent_count': len(cohorts['value_core']),
        'momentum_cohort_intent_count': len(cohorts['momentum_12_1_top_tercile']),
        'mean_reversion_cohort_intent_count': len(cohorts['mean_reversion_20d_bottom_tercile']),
        'signal_cohort_union_intent_count': len(cohorts['momentum_12_1_top_tercile'] | cohorts['mean_reversion_20d_bottom_tercile']),
        'family_event_count': len(selected_events),
        'frozen_sell_window_source': str(EXIT_EVENTS), 'parameter_scan_used': False,
        'stock_selection_rebuilt': False, 'accepted': False, 'pm_gate_decision': decision['pm_gate_decision'],
    }
    (out / 'v5j_family_sell_timing_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (out / 'v5j_family_sell_timing_report.md').write_text(_report(summary, results, decision), encoding='utf-8')
    return summary


def _cohorts(pool: list[dict[str, str]], daily: dict[str, list[dict[str, Any]]], factors: dict[tuple[str, str], float]) -> tuple[dict[str, set[str]], list[dict[str, Any]]]:
    by_period: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    signals = []
    for row in pool:
        momentum, reversion = _signals_before_entry(row['code'], row['rebalance_date'], daily, factors)
        intent_id = f"{row['rebalance_date']}|{row['code']}|{row['sleeve_id']}"
        record = {**row, 'intent_id': intent_id, 'momentum_12_1': momentum if momentum is not None else '', 'mean_reversion_20d': reversion if reversion is not None else ''}
        by_period[(row['rebalance_date'], row['sleeve_id'])].append(record)
    families: dict[str, set[str]] = {family: set() for family in FAMILIES}
    for (_, _), values in by_period.items():
        for row in values:
            families['value_core'].add(row['intent_id'])
        usable = [row for row in values if row['momentum_12_1'] != '' and row['mean_reversion_20d'] != '']
        count = max(1, round(len(usable) / 3)) if usable else 0
        for row in sorted(usable, key=lambda item: float(item['momentum_12_1']), reverse=True)[:count]:
            families['momentum_12_1_top_tercile'].add(row['intent_id'])
        for row in sorted(usable, key=lambda item: float(item['mean_reversion_20d']))[:count]:
            families['mean_reversion_20d_bottom_tercile'].add(row['intent_id'])
        for row in values:
            signals.append({
                'intent_id': row['intent_id'], 'rebalance_date': row['rebalance_date'], 'code': row['code'], 'sleeve_id': row['sleeve_id'],
                'momentum_12_1': row['momentum_12_1'], 'mean_reversion_20d': row['mean_reversion_20d'],
                'value_core_member': row['intent_id'] in families['value_core'],
                'momentum_12_1_top_tercile_member': row['intent_id'] in families['momentum_12_1_top_tercile'],
                'mean_reversion_20d_bottom_tercile_member': row['intent_id'] in families['mean_reversion_20d_bottom_tercile'],
                'signal_uses_pre_entry_information_only': True,
            })
    return families, signals


def _signals_before_entry(code: str, entry_date: str, daily: dict[str, list[dict[str, Any]]], factors: dict[tuple[str, str], float]) -> tuple[float | None, float | None]:
    history = []
    for row in daily.get(code, []):
        if row['date'] >= entry_date:
            break
        factor = factors.get((code, row['date']))
        if factor and _f(row.get('close')) > 0:
            history.append(_f(row['close']) * factor)
    if len(history) < 253:
        return None, None
    momentum = history[-22] / history[-253] - 1.0
    reversion = history[-1] / history[-21] - 1.0
    return momentum, reversion


def _attach_cohorts(events: list[dict[str, str]], cohorts: dict[str, set[str]]) -> list[dict[str, Any]]:
    result = []
    for event in events:
        for family, members in cohorts.items():
            if event['intent_id'] in members:
                result.append({**event, 'strategy_family_proxy': family, 'cohort_proxy_only_not_rebuilt_strategy': True})
    return result


def _results(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for (family, candidate), values in sorted(_group(events, lambda row: (row['strategy_family_proxy'], row['candidate_id'])).items()):
        valid = [row for row in values if row['pit_status'] == 'pass']
        deltas = [_f(row['sell_proceeds_delta_bps']) for row in valid]
        result.append({
            'strategy_family_proxy': family, 'candidate_id': candidate, 'event_count': len(values), 'fillable_event_count': len(valid),
            'fallback_count': sum(_bool(row['fallback_used']) for row in values),
            'mean_sell_proceeds_delta_bps': sum(deltas) / len(deltas) if deltas else 0.0,
            'median_sell_proceeds_delta_bps': _median(deltas),
            'positive_event_ratio': sum(delta > 0 for delta in deltas) / len(deltas) if deltas else 0.0,
            'accepted': False,
        })
    return result


def _yearly(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    key = lambda row: (row['strategy_family_proxy'], row['candidate_id'], row['year'], row['sleeve_id'])
    for (family, candidate, year, sleeve), values in sorted(_group(events, key).items()):
        valid = [row for row in values if row['pit_status'] == 'pass']
        deltas = [_f(row['sell_proceeds_delta_bps']) for row in valid]
        result.append({'strategy_family_proxy': family, 'candidate_id': candidate, 'year': year, 'sleeve_id': sleeve, 'event_count': len(valid), 'mean_sell_proceeds_delta_bps': sum(deltas) / len(deltas) if deltas else 0.0})
    return result


def _audits(pool: list[dict[str, str]], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {'audit_id': 'value_pool_only', 'status': 'pass', 'detail': len(pool)},
        {'audit_id': 'signal_precedes_entry', 'status': 'pass', 'detail': '12-1 and 20-day signals end on the prior trading close'},
        {'audit_id': 'frozen_exit_window_only', 'status': 'pass', 'detail': 'uses existing V5j full PIT sell-window events without new windows'},
        {'audit_id': 'no_strategy_rebuild', 'status': 'pass', 'detail': True},
        {'audit_id': 'no_parameter_scan', 'status': 'pass', 'detail': False},
        {'audit_id': 'event_coverage', 'status': 'pass' if events else 'fail', 'detail': len(events)},
    ]


def _decision(results: list[dict[str, Any]], yearly: list[dict[str, Any]], audits: list[dict[str, Any]]) -> dict[str, Any]:
    non_control = [row for row in results if row['candidate_id'] != 'open_control']
    best_by_family = {}
    for family in FAMILIES:
        options = [row for row in non_control if row['strategy_family_proxy'] == family]
        if options:
            best_by_family[family] = max(options, key=lambda row: _f(row['mean_sell_proceeds_delta_bps']))
    positive = {family: row for family, row in best_by_family.items() if _f(row['mean_sell_proceeds_delta_bps']) > 0 and _f(row['positive_event_ratio']) >= 0.50}
    return {
        'pm_gate_decision': 'family_specific_exit_proxy_differences_observed_keep_diagnostic_only' if positive else 'family_specific_exit_proxy_no_economic_edge_keep_diagnostic_only',
        'best_fixed_candidate_by_family': json.dumps({family: row['candidate_id'] for family, row in best_by_family.items()}, ensure_ascii=False),
        'positive_family_count': len(positive), 'accepted': False,
        'reason': 'Cohorts are derived from the existing PIT value pool and frozen planned-exit proxy. They cannot establish a separate V5f strategy or change V5e exits.',
    }


def _next_queue(decision: dict[str, Any]) -> list[dict[str, str]]:
    return [{'priority': 'P0', 'next_task': 'retain_family_exit_results_as_v5i_diagnostic', 'status': 'ready', 'reason': decision['pm_gate_decision']}]


def _group(rows: list[dict[str, Any]], key: Any) -> dict[Any, list[dict[str, Any]]]:
    result: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        result[key(row)].append(row)
    return result


def _median(values: list[float]) -> float:
    values = sorted(values)
    return 0.0 if not values else values[len(values) // 2] if len(values) % 2 else (values[len(values) // 2 - 1] + values[len(values) // 2]) / 2.0


def _f(value: Any) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _bool(value: Any) -> bool:
    return str(value).lower() == 'true'


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
    lines = ['# V5j family-specific sell-timing diagnostic', '', '- All cohorts are derived inside the existing PIT value/low-volatility pool.', '- Momentum and mean-reversion labels are pre-entry signal cohorts, not rebuilt V5f portfolios.', f"- PM gate: `{decision['pm_gate_decision']}`.", '', '## Fixed Window Results', '']
    for row in results:
        lines.append(f"- `{row['strategy_family_proxy']} | {row['candidate_id']}`: n={row['fillable_event_count']}, mean={float(row['mean_sell_proceeds_delta_bps']):.2f} bps, positive={float(row['positive_event_ratio']):.2%}.")
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    print(json.dumps(run_v5j_family_specific_sell_timing_diagnostic(), ensure_ascii=False, indent=2))

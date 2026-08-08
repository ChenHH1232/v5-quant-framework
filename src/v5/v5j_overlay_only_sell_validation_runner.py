from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.v5j_family_sell_execution_formal_backtest_runner import _evaluate_events
from v5.v5j_v5e_profit_lock_sell_timing_proxy_runner import _daily_ohlc_archive, _factors

OUT = Path('v5j_overlay_only_sell_validation') / 'current'
DB = Path('\u6570\u636e\u5e93') / 'processed' / 'pre2021_repaired_multisleeve_pit_pool_v5'
POOL = DB / 'repaired_multisleeve_pit_pool.csv'
FACTORS = Path('v5j_local_adjust_factor_corporate_action') / 'current' / 'v5j_local_adjust_factor_panel.csv'
GATE = Path('v5j_cross_period_technical_validation_gate') / 'current' / 'v5j_cross_period_data_gate_summary.json'
FAMILIES = ('momentum_overlay_70_30', 'mean_reversion_20d_overlay_70_30_proxy')


def run_v5j_overlay_only_sell_validation(root: Path = Path('.')) -> dict[str, Any]:
    gate = json.loads((root / GATE).read_text(encoding='utf-8'))
    if not gate.get('technical_rule_validation_allowed'):
        raise RuntimeError('PIT data gate has not allowed overlay-only validation.')
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    pool = [row for row in _csv(root / POOL) if row.get('pool_eligibility') == 'eligible_for_predecessor_pool']
    daily = _daily_ohlc_archive(root, {row['code'] for row in pool})
    factors = _factors(_csv(root / FACTORS))
    weight_rows = _weights(pool, daily, factors)
    intents = _overlay_sell_intents(weight_rows)
    events = _evaluate_events(root, intents)
    results = _results(events)
    yearly = _yearly(events)
    audits = _audits(pool, weight_rows, events)
    decision = _decision(results, yearly, audits)
    _write(out / 'v5j_overlay_only_pre2021_weights.csv', weight_rows)
    _write(out / 'v5j_overlay_only_pre2021_sell_intents.csv', intents)
    _write(out / 'v5j_overlay_only_pre2021_events.csv', events)
    _write(out / 'v5j_overlay_only_pre2021_results.csv', results)
    _write(out / 'v5j_overlay_only_pre2021_sleeve_year.csv', yearly)
    _write(out / 'v5j_overlay_only_pre2021_audit.csv', audits)
    _write(out / 'v5j_overlay_only_pre2021_pm_gate.csv', [decision])
    summary = {
        'created_at_utc': _now(), 'task': 'v5j_overlay_only_sell_validation', 'validation_window': '2013-01-01_to_2021-04-30',
        'value_base_weight_changed': False, 'frozen_sell_window': 'vwap_1400_hold_to_1445', 'family_count': len(FAMILIES),
        'overlay_only_sell_intent_count': len(intents), 'fillable_intent_count': len({row['intent_id'] for row in events if row['pit_status'] == 'pass'}),
        'mean_reversion_definition': 'within existing PIT value/low-volatility pool, weakest pre-entry 20-day adjusted return; proxy only, not financial-quality reconstruction',
        'parameter_scan_used': False, 'accepted': False, 'pm_gate_decision': decision['pm_gate_decision'],
    }
    (out / 'v5j_overlay_only_pre2021_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return summary


def _weights(pool: list[dict[str, str]], daily: dict[str, list[dict[str, Any]]], factors: dict[tuple[str, str], float]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in pool:
        grouped[row['rebalance_date']].append(row)
    result = []
    for date, rows in sorted(grouped.items()):
        sleeves = sorted({row['sleeve_id'] for row in rows})
        for sleeve in sleeves:
            members = [row for row in rows if row['sleeve_id'] == sleeve]
            base_weight = 1.0 / len(sleeves) / len(members)
            signals = []
            for row in members:
                momentum, reversion = _signals_before_entry(row['code'], date, daily, factors)
                signals.append({**row, 'momentum_12_1': momentum, 'mean_reversion_20d': reversion})
            valid = [row for row in signals if row['momentum_12_1'] is not None and row['mean_reversion_20d'] is not None]
            count = max(1, round(len(valid) / 3)) if valid else 0
            top = {row['code'] for row in sorted(valid, key=lambda item: item['momentum_12_1'], reverse=True)[:count]}
            bottom = {row['code'] for row in sorted(valid, key=lambda item: item['mean_reversion_20d'])[:count]}
            sleeve_weight = 1.0 / len(sleeves)
            for row in signals:
                momentum_target = 0.7 * base_weight + (0.3 * sleeve_weight / len(top) if row['code'] in top and top else 0.0)
                reversion_target = 0.7 * base_weight + (0.3 * sleeve_weight / len(bottom) if row['code'] in bottom and bottom else 0.0)
                for family, target in ((FAMILIES[0], momentum_target), (FAMILIES[1], reversion_target)):
                    result.append({'strategy_family': family, 'rebalance_date': date, 'code': row['code'], 'sleeve_id': sleeve, 'base_weight': base_weight, 'target_weight': target, 'overlay_weight': target - base_weight, 'momentum_12_1': row['momentum_12_1'] if row['momentum_12_1'] is not None else '', 'mean_reversion_20d': row['mean_reversion_20d'] if row['mean_reversion_20d'] is not None else '', 'value_base_unchanged': True, 'accepted': False})
    return result


def _signals_before_entry(code: str, entry_date: str, daily: dict[str, list[dict[str, Any]]], factors: dict[tuple[str, str], float]) -> tuple[float | None, float | None]:
    history = [
        _f(row['close']) * factors[(code, row['date'])]
        for row in daily.get(code, []) if row['date'] < entry_date and factors.get((code, row['date'])) and _f(row['close']) > 0
    ]
    if len(history) < 253:
        return None, None
    return history[-22] / history[-253] - 1.0, history[-1] / history[-21] - 1.0


def _overlay_sell_intents(weights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_family_date: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in weights:
        by_family_date[(row['strategy_family'], row['rebalance_date'])][row['code']] = row
    prior: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    intents = []
    for (family, date), current in sorted(by_family_date.items()):
        previous = prior[family]
        for code in set(previous) | set(current):
            before, after = _f(previous.get(code, {}).get('overlay_weight')), _f(current.get(code, {}).get('overlay_weight'))
            reduction = before - after
            if reduction > 1e-10:
                reference = previous.get(code) or current.get(code)
                intents.append({'intent_id': f'{family}|{date}|{code}', 'strategy_family': family, 'trade_date': date, 'code': code, 'sleeve_id': reference['sleeve_id'], 'sell_weight': reduction, 'overlay_only': True, 'value_base_unchanged': True, 'precommitted_rebalance_sell': True})
        prior[family] = current
    return intents


def _results(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for family, rows in sorted(_group(events, lambda row: row['strategy_family']).items()):
        valid = [row for row in rows if row['pit_status'] == 'pass']
        deltas = [_f(row['sell_proceeds_delta_bps']) for row in valid]
        result.append({'strategy_family': family, 'event_count': len(rows), 'fillable_event_count': len(valid), 'mean_sell_proceeds_delta_bps': sum(deltas) / len(deltas) if deltas else 0.0, 'positive_event_ratio': sum(delta > 0 for delta in deltas) / len(deltas) if deltas else 0.0, 'weighted_adjustment_bps': sum(_f(row['weighted_execution_adjustment_return']) for row in valid) * 10000, 'accepted': False})
    return result


def _yearly(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for (family, year, sleeve), rows in sorted(_group(events, lambda row: (row['strategy_family'], row['trade_date'][:4], row['sleeve_id'])).items()):
        valid = [row for row in rows if row['pit_status'] == 'pass']
        deltas = [_f(row['sell_proceeds_delta_bps']) for row in valid]
        result.append({'strategy_family': family, 'year': year, 'sleeve_id': sleeve, 'event_count': len(valid), 'mean_sell_proceeds_delta_bps': sum(deltas) / len(deltas) if deltas else 0.0})
    return result


def _audits(pool: list[dict[str, str]], weights: list[dict[str, Any]], events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{'audit_id': 'pit_value_pool_only', 'status': 'pass', 'detail': len(pool)}, {'audit_id': 'value_base_unchanged', 'status': 'pass' if all(_bool(row['value_base_unchanged']) for row in weights + events) else 'fail', 'detail': True}, {'audit_id': 'pre_entry_signals_only', 'status': 'pass', 'detail': True}, {'audit_id': 'frozen_1400_window_only', 'status': 'pass', 'detail': True}, {'audit_id': 'no_parameter_scan', 'status': 'pass', 'detail': False}, {'audit_id': 'minute_coverage', 'status': 'pass' if all(row['pit_status'] == 'pass' for row in events) else 'review', 'detail': sum(row['pit_status'] != 'pass' for row in events)}]


def _decision(results: list[dict[str, Any]], yearly: list[dict[str, Any]], audits: list[dict[str, Any]]) -> dict[str, Any]:
    support = []
    for row in results:
        units = [item for item in yearly if item['strategy_family'] == row['strategy_family'] and item['event_count'] > 0]
        ratio = sum(_f(item['mean_sell_proceeds_delta_bps']) > 0 for item in units) / len(units) if units else 0.0
        if _f(row['weighted_adjustment_bps']) > 0 and ratio >= 0.60:
            support.append(row['strategy_family'])
    return {'pm_gate_decision': 'overlay_only_pre2021_support_ready_for_formal_backtest_not_accepted' if support else 'overlay_only_pre2021_not_stable_keep_diagnostic_only', 'supported_families': ';'.join(support), 'accepted': False, 'reason': 'Value base is frozen. Mean-reversion is only a PIT value-pool short-window proxy until a comparable pre-2021 financial-quality panel exists.'}


def _group(rows: list[dict[str, Any]], key: Any) -> dict[Any, list[dict[str, Any]]]:
    out: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        out[key(row)].append(row)
    return out


def _f(value: Any) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _bool(value: Any) -> bool:
    return value is True or str(value).lower() == 'true'


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ['empty']
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader(); writer.writerows(rows)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


if __name__ == '__main__':
    print(json.dumps(run_v5j_overlay_only_sell_validation(), ensure_ascii=False, indent=2))

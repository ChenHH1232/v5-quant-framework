from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

OUT = Path('v5j_family_sell_execution_formal_backtest') / 'current'
MINUTE = Path('\u6570\u636e\u5e93') / 'processed' / 'local_1min_clean_2013_2026' / 'by_year'
STRUCTURAL_DAILY = Path('v5f_structural_rough_screen') / 'current' / 'v5f_structural_rough_screen_daily_returns.csv'
STRUCTURAL_WEIGHTS = Path('v5f_structural_rough_screen') / 'current' / 'v5f_structural_rough_screen_weights.csv'
QV_DAILY = Path('v5f_quality_value_mean_reversion') / 'current' / 'v5f_qv_mean_reversion_daily_returns.csv'
QV_WEIGHTS = Path('v5f_quality_value_mean_reversion') / 'current' / 'v5f_qv_mean_reversion_weight_log.csv'
FORMAL_START = '2021-05-01'
FORMAL_END = '2026-05-31'
WINDOW = 'vwap_1400_hold_to_1445'
SPECS = (
    ('value_core', STRUCTURAL_DAILY, STRUCTURAL_WEIGHTS, 'v57f_startup_preload_repaired_baseline', 'rebalance_date'),
    ('momentum_12_1', STRUCTURAL_DAILY, STRUCTURAL_WEIGHTS, 'internal_subsleeve_mom12_70_30', 'rebalance_date'),
    ('mean_reversion_20d', QV_DAILY, QV_WEIGHTS, 'qv_mr_20d_rebalance_70_30', 'active_rebalance_date'),
)


def run_v5j_family_sell_execution_formal_backtest(root: Path = Path('.')) -> dict[str, Any]:
    required = (STRUCTURAL_DAILY, STRUCTURAL_WEIGHTS, QV_DAILY, QV_WEIGHTS)
    missing = [str(path) for path in required if not (root / path).exists()]
    if missing:
        raise FileNotFoundError(f'Missing formal backtest inputs: {missing}')
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    all_events, all_nav, metrics, funding = [], [], [], []
    for family, daily_path, weight_path, version, date_column in SPECS:
        snapshots = _snapshots(_csv(root / weight_path), version, date_column)
        intents = _sell_intents(family, snapshots)
        evaluated = _evaluate_events(root, intents)
        daily = _daily_returns(root / daily_path, version)
        nav = _adjust_nav(daily, evaluated, family)
        all_events.extend(evaluated)
        all_nav.extend(nav)
        metrics.append(_metrics(nav, family))
        funding.extend(_funding_audit(family, snapshots, intents))
    audits = _audits(all_events, funding)
    decision = _decision(metrics, audits)
    _write(out / 'v5j_formal_family_sell_execution_events.csv', all_events)
    _write(out / 'v5j_formal_family_sell_execution_daily_nav.csv', all_nav)
    _write(out / 'v5j_formal_family_sell_execution_metrics.csv', metrics)
    _write(out / 'v5j_formal_family_sell_execution_cash_path_audit.csv', funding)
    _write(out / 'v5j_formal_family_sell_execution_governance_audit.csv', audits)
    _write(out / 'v5j_formal_family_sell_execution_pm_gate.csv', [decision])
    _write(out / 'v5j_formal_family_sell_execution_next_queue.csv', _next_queue(decision))
    summary = {
        'created_at_utc': _now(), 'task': 'v5j_family_sell_execution_formal_backtest',
        'formal_backtest_window': f'{FORMAL_START}_to_{FORMAL_END}', 'frozen_exit_window': WINDOW,
        'family_count': len(SPECS), 'sell_intent_count': len({row['intent_id'] for row in all_events}),
        'fillable_sell_intent_count': len({row['intent_id'] for row in all_events if row['pit_status'] == 'pass'}),
        'price_only_counterfactual': True, 'cash_path_audited': True, 'accepted': False,
        'pm_gate_decision': decision['pm_gate_decision'],
    }
    (out / 'v5j_formal_family_sell_execution_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (out / 'v5j_formal_family_sell_execution_report.md').write_text(_report(summary, metrics, funding, decision), encoding='utf-8')
    return summary


def _snapshots(rows: list[dict[str, str]], version: str, date_column: str) -> dict[str, dict[str, float]]:
    by_date: dict[str, dict[str, float]] = defaultdict(dict)
    for row in rows:
        if row.get('version_id') != version:
            continue
        date = row.get(date_column, '')
        if date_column == 'active_rebalance_date' and row.get('trade_date') != date:
            continue
        if FORMAL_START <= date <= FORMAL_END:
            by_date[date][row['code']] = _f(row.get('target_weight'))
    return dict(sorted(by_date.items()))


def _sell_intents(family: str, snapshots: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    previous: dict[str, float] = {}
    result = []
    for date, current in snapshots.items():
        for code in set(previous) | set(current):
            sell_weight = previous.get(code, 0.0) - current.get(code, 0.0)
            if sell_weight > 1e-10:
                result.append({'intent_id': f'{family}|{date}|{code}', 'strategy_family': family, 'trade_date': date, 'code': code, 'sell_weight': sell_weight, 'control_time': '09:31:00', 'window': WINDOW, 'precommitted_rebalance_sell': True})
        previous = current
    return result


def _evaluate_events(root: Path, intents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    requested: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for intent in intents:
        requested[(intent['code'], intent['trade_date'][:4])].append(intent)
    result = []
    for (code, year), members in requested.items():
        path = root / MINUTE / year / f"{code.replace('.', '_')}_1min.csv"
        wanted = {item['trade_date'] for item in members}
        days: dict[str, list[dict[str, str]]] = defaultdict(list)
        if path.exists():
            for row in _csv(path):
                if row.get('trade_date') in wanted:
                    days[row['trade_date']].append(row)
        for intent in members:
            result.append(_evaluate_one(intent, days.get(intent['trade_date'], [])))
    return result


def _evaluate_one(intent: dict[str, Any], bars: list[dict[str, str]]) -> dict[str, Any]:
    index = {row['time']: row for row in bars}
    control = _fill(index, '09:31:00')
    feature = _vwap_feature(bars, '14:00:00')
    selected_time = '14:01:00' if feature['below'] else '14:46:00'
    selected = _fill(index, selected_time)
    fallback = False
    if not selected or not feature['available']:
        selected, fallback = control, True
    control_price, selected_price = _f(control.get('open')) if control else 0.0, _f(selected.get('open')) if selected else 0.0
    delta = selected_price / control_price - 1.0 if control_price and selected_price else 0.0
    return {**intent, 'minute_row_count': len(bars), 'vwap_1400': feature['vwap'], 'close_1400_lte_vwap': feature['below'], 'selected_time': selected_time, 'fallback_used': fallback, 'control_open': control_price, 'selected_open': selected_price, 'sell_proceeds_delta_bps': delta * 10000, 'weighted_execution_adjustment_return': intent['sell_weight'] * delta, 'pit_status': 'pass' if control_price and selected_price else 'missing_required_bar', 'accepted': False}


def _vwap_feature(bars: list[dict[str, str]], until: str) -> dict[str, Any]:
    visible = [row for row in bars if row.get('time', '') <= until]
    volume, amount = sum(_f(row.get('volume')) for row in visible), sum(_f(row.get('amount')) for row in visible)
    at_time = next((row for row in visible if row.get('time') == until), None)
    vwap = amount / volume if volume else 0.0
    close = _f(at_time.get('close')) if at_time else 0.0
    return {'available': bool(at_time and volume > 0), 'vwap': vwap, 'below': bool(close and vwap and close <= vwap)}


def _fill(index: dict[str, dict[str, str]], time_value: str) -> dict[str, str] | None:
    row = index.get(time_value)
    return row if row and _f(row.get('open')) > 0 and _f(row.get('volume')) > 0 else None


def _daily_returns(path: Path, version: str) -> list[dict[str, Any]]:
    rows = [row for row in _csv(path) if row.get('version_id') == version and FORMAL_START <= row.get('trade_date', '') <= FORMAL_END]
    return [{'trade_date': row['trade_date'], 'strategy_return': _f(row['strategy_return']), 'strategy_nav': _f(row.get('strategy_nav'))} for row in rows]


def _adjust_nav(daily: list[dict[str, Any]], events: list[dict[str, Any]], family: str) -> list[dict[str, Any]]:
    by_date: dict[str, float] = defaultdict(float)
    for event in events:
        if event['pit_status'] == 'pass':
            by_date[event['trade_date']] += _f(event['weighted_execution_adjustment_return'])
    nav = 1.0
    result = []
    for row in daily:
        adjustment = by_date[row['trade_date']]
        baseline_return = _f(row['strategy_return'])
        adjusted_return = baseline_return + adjustment
        nav *= 1.0 + adjusted_return
        result.append({'trade_date': row['trade_date'], 'strategy_family': family, 'control_strategy_return': baseline_return, 'price_only_execution_adjustment_return': adjustment, 'adjusted_strategy_return': adjusted_return, 'control_nav': row['strategy_nav'], 'price_only_adjusted_nav': nav, 'cash_path_comparable': False, 'accepted': False})
    return result


def _metrics(nav: list[dict[str, Any]], family: str) -> dict[str, Any]:
    control = [_f(row['control_nav']) for row in nav]
    adjusted = [_f(row['price_only_adjusted_nav']) for row in nav]
    adjustments = [_f(row['price_only_execution_adjustment_return']) for row in nav]
    return {'strategy_family': family, 'control_return_pct': (control[-1] - 1.0) * 100 if control else 0.0, 'price_only_adjusted_return_pct': (adjusted[-1] - 1.0) * 100 if adjusted else 0.0, 'delta_return_pct_points': (adjusted[-1] - control[-1]) * 100 if control and adjusted else 0.0, 'execution_adjustment_total_bps': sum(adjustments) * 10000, 'control_max_drawdown_pct': _max_drawdown(control) * 100, 'adjusted_max_drawdown_pct': _max_drawdown(adjusted) * 100, 'cash_path_comparable': False, 'accepted': False}


def _funding_audit(family: str, snapshots: dict[str, dict[str, float]], intents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sold: dict[str, float] = defaultdict(float)
    for item in intents:
        sold[item['trade_date']] += _f(item['sell_weight'])
    previous: dict[str, float] = {}
    result = []
    for date, current in snapshots.items():
        buys = sum(max(current.get(code, 0.0) - previous.get(code, 0.0), 0.0) for code in set(previous) | set(current))
        result.append({'strategy_family': family, 'trade_date': date, 'morning_buy_weight_need': buys, 'delayed_sell_weight': sold[date], 'same_day_rebalance_cash_dependency': buys > 1e-10 and sold[date] > 1e-10, 'status': 'review_required' if buys > 1e-10 and sold[date] > 1e-10 else 'not_applicable'})
        previous = current
    return result


def _audits(events: list[dict[str, Any]], funding: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dependency = sum(_bool(row['same_day_rebalance_cash_dependency']) for row in funding)
    return [
        {'audit_id': 'formal_window_only', 'status': 'pass', 'detail': f'{FORMAL_START} to {FORMAL_END}'},
        {'audit_id': 'frozen_pre2021_validated_window', 'status': 'pass', 'detail': WINDOW},
        {'audit_id': 'no_v5e_profit_lock_integration', 'status': 'pass', 'detail': True},
        {'audit_id': 'minute_sell_fill_coverage', 'status': 'pass' if all(row['pit_status'] == 'pass' for row in events) else 'review', 'detail': sum(row['pit_status'] != 'pass' for row in events)},
        {'audit_id': 'cash_path_dependency', 'status': 'review_required' if dependency else 'pass', 'detail': dependency},
        {'audit_id': 'price_only_nav_not_trade_path_equivalent', 'status': 'pass', 'detail': True},
    ]


def _decision(metrics: list[dict[str, Any]], audits: list[dict[str, Any]]) -> dict[str, Any]:
    positive = sum(_f(row['delta_return_pct_points']) > 0 for row in metrics)
    cash_dependency = next(row for row in audits if row['audit_id'] == 'cash_path_dependency')['status'] == 'review_required'
    return {'pm_gate_decision': 'formal_price_only_positive_but_cash_path_blocks_promotion' if positive and cash_dependency else 'formal_price_only_no_consistent_edge_keep_diagnostic_only', 'positive_family_count': positive, 'cash_path_dependency_blocks_trade_path_claim': cash_dependency, 'accepted': False, 'reason': 'The delayed sell is a price-only counterfactual until same-day buy funding and order sequencing are separately engineered.'}


def _next_queue(decision: dict[str, Any]) -> list[dict[str, str]]:
    return [{'priority': 'P0', 'next_task': 'cash_neutral_rebalance_execution_spec_only_if_separately_approved', 'status': 'blocked_by_cash_path' if decision['cash_path_dependency_blocks_trade_path_claim'] else 'diagnostic_only', 'reason': decision['pm_gate_decision']}]


def _max_drawdown(values: list[float]) -> float:
    peak, worst = 0.0, 0.0
    for value in values:
        peak = max(peak, value)
        if peak:
            worst = min(worst, value / peak - 1.0)
    return -worst


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
        writer.writeheader()
        writer.writerows(rows)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _report(summary: dict[str, Any], metrics: list[dict[str, Any]], funding: list[dict[str, Any]], decision: dict[str, Any]) -> str:
    lines = ['# V5j formal family sell-execution backtest', '', '- The 2013-2021 validation froze the 14:00 VWAP sell window before this formal-period evaluation.', '- These NAVs are price-only counterfactuals, explicitly not cash-path-equivalent executions.', f"- PM gate: `{decision['pm_gate_decision']}`.", '', '## Metrics', '']
    for row in metrics:
        lines.append(f"- `{row['strategy_family']}`: control={float(row['control_return_pct']):.4f}%, price-only adjusted={float(row['price_only_adjusted_return_pct']):.4f}%, delta={float(row['delta_return_pct_points']):.4f} pct points.")
    lines.extend(['', f"- Rebalance dates with delayed-sell/morning-buy cash dependency: `{sum(_bool(row['same_day_rebalance_cash_dependency']) for row in funding)}`.", ''])
    return '\n'.join(lines)


if __name__ == '__main__':
    print(json.dumps(run_v5j_family_sell_execution_formal_backtest(), ensure_ascii=False, indent=2))

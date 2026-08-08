from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.v5j_family_sell_execution_formal_backtest_runner import _adjust_nav, _daily_returns, _evaluate_events, _metrics

OUT = Path('v5j_overlay_only_sell_formal_backtest') / 'current'
STRUCTURAL_DAILY = Path('v5f_structural_rough_screen') / 'current' / 'v5f_structural_rough_screen_daily_returns.csv'
STRUCTURAL_WEIGHTS = Path('v5f_structural_rough_screen') / 'current' / 'v5f_structural_rough_screen_weights.csv'
QV_DAILY = Path('v5f_quality_value_mean_reversion') / 'current' / 'v5f_qv_mean_reversion_daily_returns.csv'
QV_WEIGHTS = Path('v5f_quality_value_mean_reversion') / 'current' / 'v5f_qv_mean_reversion_weight_log.csv'
FORMAL_START = '2021-05-01'
FORMAL_END = '2026-05-31'
BASELINE = 'v57f_startup_preload_repaired_baseline'
SPECS = (
    ('momentum_overlay_70_30', STRUCTURAL_DAILY, STRUCTURAL_WEIGHTS, 'internal_subsleeve_mom12_70_30', 'rebalance_date'),
    ('mean_reversion_20d_overlay_70_30', QV_DAILY, QV_WEIGHTS, 'qv_mr_20d_rebalance_70_30', 'active_rebalance_date'),
)


def run_v5j_overlay_only_sell_formal_backtest(root: Path = Path('.')) -> dict[str, Any]:
    required = (STRUCTURAL_DAILY, STRUCTURAL_WEIGHTS, QV_DAILY, QV_WEIGHTS)
    missing = [str(path) for path in required if not (root / path).exists()]
    if missing:
        raise FileNotFoundError(f'Missing required formal sources: {missing}')
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    base = _snapshots(_csv(root / STRUCTURAL_WEIGHTS), BASELINE, 'rebalance_date')
    events, nav_rows, metrics, funding = [], [], [], []
    for family, daily_path, weight_path, version, date_column in SPECS:
        target = _snapshots(_csv(root / weight_path), version, date_column)
        overlays = _overlay_snapshots(base, target)
        intents = _overlay_sell_intents(family, overlays)
        evaluated = _evaluate_events(root, intents)
        nav = _adjust_nav(_daily_returns(root / daily_path, version), evaluated, family)
        events.extend(evaluated); nav_rows.extend(nav); metrics.append(_metrics(nav, family)); funding.extend(_funding(family, overlays))
    audits = _audits(events, funding)
    decision = _decision(metrics, audits)
    _write(out / 'v5j_overlay_only_formal_sell_events.csv', events)
    _write(out / 'v5j_overlay_only_formal_daily_nav.csv', nav_rows)
    _write(out / 'v5j_overlay_only_formal_metrics.csv', metrics)
    _write(out / 'v5j_overlay_only_formal_cash_path_audit.csv', funding)
    _write(out / 'v5j_overlay_only_formal_governance_audit.csv', audits)
    _write(out / 'v5j_overlay_only_formal_pm_gate.csv', [decision])
    summary = {
        'created_at_utc': _now(), 'task': 'v5j_overlay_only_sell_formal_backtest', 'formal_backtest_window': f'{FORMAL_START}_to_{FORMAL_END}',
        'frozen_exit_window': 'vwap_1400_hold_to_1445', 'value_base_weight_changed': False, 'family_count': len(SPECS),
        'overlay_only_sell_intent_count': len({row['intent_id'] for row in events}), 'fillable_intent_count': len({row['intent_id'] for row in events if row['pit_status'] == 'pass'}),
        'price_only_counterfactual': True, 'accepted': False, 'pm_gate_decision': decision['pm_gate_decision'],
    }
    (out / 'v5j_overlay_only_formal_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (out / 'v5j_overlay_only_formal_report.md').write_text(_report(summary, metrics, funding, decision), encoding='utf-8')
    return summary


def _snapshots(rows: list[dict[str, str]], version: str, date_column: str) -> dict[str, dict[str, float]]:
    output: dict[str, dict[str, float]] = defaultdict(dict)
    for row in rows:
        if row.get('version_id') != version:
            continue
        date = row.get(date_column, '')
        if date_column == 'active_rebalance_date' and row.get('trade_date') != date:
            continue
        if FORMAL_START <= date <= FORMAL_END:
            output[date][row['code']] = _f(row.get('target_weight'))
    return dict(sorted(output.items()))


def _overlay_snapshots(base: dict[str, dict[str, float]], target: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    output = {}
    for date, target_map in target.items():
        base_map = base.get(date, {})
        output[date] = {code: target_map.get(code, 0.0) - base_map.get(code, 0.0) for code in set(base_map) | set(target_map)}
    return output


def _overlay_sell_intents(family: str, overlays: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    prior: dict[str, float] = {}
    result = []
    for date, current in sorted(overlays.items()):
        for code in set(prior) | set(current):
            reduction = prior.get(code, 0.0) - current.get(code, 0.0)
            if reduction > 1e-10:
                result.append({'intent_id': f'{family}|{date}|{code}', 'strategy_family': family, 'trade_date': date, 'code': code, 'sell_weight': reduction, 'overlay_only': True, 'value_base_unchanged': True, 'precommitted_rebalance_sell': True})
        prior = current
    return result


def _funding(family: str, overlays: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    prior: dict[str, float] = {}
    result = []
    for date, current in sorted(overlays.items()):
        sell = sum(max(prior.get(code, 0.0) - current.get(code, 0.0), 0.0) for code in set(prior) | set(current))
        buy = sum(max(current.get(code, 0.0) - prior.get(code, 0.0), 0.0) for code in set(prior) | set(current))
        result.append({'strategy_family': family, 'trade_date': date, 'overlay_buy_weight': buy, 'delayed_overlay_sell_weight': sell, 'same_day_overlay_cash_dependency': buy > 1e-10 and sell > 1e-10, 'value_base_unchanged': True, 'status': 'review_required' if buy > 1e-10 and sell > 1e-10 else 'not_applicable'})
        prior = current
    return result


def _audits(events: list[dict[str, Any]], funding: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dependency = sum(_bool(row['same_day_overlay_cash_dependency']) for row in funding)
    return [{'audit_id': 'formal_window_only', 'status': 'pass', 'detail': f'{FORMAL_START} to {FORMAL_END}'}, {'audit_id': 'value_base_unchanged', 'status': 'pass' if all(_bool(row['value_base_unchanged']) for row in events + funding) else 'fail', 'detail': True}, {'audit_id': 'frozen_window_only', 'status': 'pass', 'detail': 'vwap_1400_hold_to_1445'}, {'audit_id': 'minute_fill_coverage', 'status': 'pass' if all(row['pit_status'] == 'pass' for row in events) else 'review', 'detail': sum(row['pit_status'] != 'pass' for row in events)}, {'audit_id': 'overlay_cash_path_dependency', 'status': 'review_required' if dependency else 'pass', 'detail': dependency}, {'audit_id': 'price_only_not_trade_path_equivalent', 'status': 'pass', 'detail': True}]


def _decision(metrics: list[dict[str, Any]], audits: list[dict[str, Any]]) -> dict[str, Any]:
    positive = [row['strategy_family'] for row in metrics if _f(row['delta_return_pct_points']) > 0]
    cash_review = next(row for row in audits if row['audit_id'] == 'overlay_cash_path_dependency')['status'] == 'review_required'
    return {'pm_gate_decision': 'overlay_only_formal_positive_but_cash_path_blocks_promotion' if positive and cash_review else 'overlay_only_formal_no_consistent_edge_keep_diagnostic_only', 'positive_families': ';'.join(positive), 'value_base_weight_changed': False, 'accepted': False, 'reason': 'Only overlay reductions were delayed. Any positive price-only result still needs a separately approved same-day overlay cash-funding specification.'}


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
        writer = csv.DictWriter(handle, fields); writer.writeheader(); writer.writerows(rows)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _report(summary: dict[str, Any], metrics: list[dict[str, Any]], funding: list[dict[str, Any]], decision: dict[str, Any]) -> str:
    lines = ['# Overlay-only formal sell execution backtest', '', '- Value base target weights are unchanged; only internal momentum or mean-reversion overlay reductions use the frozen sell window.', '- NAV is price-only and not cash-path-equivalent.', f"- PM gate: `{decision['pm_gate_decision']}`.", '']
    for row in metrics:
        lines.append(f"- `{row['strategy_family']}`: delta `{float(row['delta_return_pct_points']):.4f}` pct points.")
    lines.append(f"- Overlay cash-dependency rebalance dates: `{sum(_bool(row['same_day_overlay_cash_dependency']) for row in funding)}`.")
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    print(json.dumps(run_v5j_overlay_only_sell_formal_backtest(), ensure_ascii=False, indent=2))

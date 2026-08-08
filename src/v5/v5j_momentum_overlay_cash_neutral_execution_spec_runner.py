from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUT = Path('v5j_momentum_overlay_cash_neutral_execution_spec') / 'current'
VALIDATION = Path('v5j_overlay_only_sell_validation') / 'current'
FORMAL = Path('v5j_overlay_only_sell_formal_backtest') / 'current'


def run_v5j_momentum_overlay_cash_neutral_execution_spec(root: Path = Path('.')) -> dict[str, Any]:
    validation = _json(root / VALIDATION / 'v5j_overlay_only_pre2021_summary.json')
    formal = _json(root / FORMAL / 'v5j_overlay_only_formal_summary.json')
    validation_results = _csv(root / VALIDATION / 'v5j_overlay_only_pre2021_results.csv')
    metrics = _csv(root / FORMAL / 'v5j_overlay_only_formal_metrics.csv')
    validation_momentum = next((row for row in validation_results if row.get('strategy_family') == 'momentum_overlay_70_30'), None)
    momentum = next((row for row in metrics if row.get('strategy_family') == 'momentum_overlay_70_30'), None)
    if not validation_momentum or not momentum:
        raise RuntimeError('Momentum overlay formal metric is required for cash-neutral execution spec.')
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    rules = _rules()
    schema = _ledger_schema()
    gates = _cash_neutrality_gates()
    boundaries = _boundaries()
    fallback = _failure_fallbacks()
    decision = _decision(validation, formal, momentum)
    _write(out / 'v5j_momentum_cash_neutral_rule_spec.csv', rules)
    _write(out / 'v5j_momentum_cash_neutral_ledger_schema.csv', schema)
    _write(out / 'v5j_momentum_cash_neutral_gate_matrix.csv', gates)
    _write(out / 'v5j_momentum_cash_neutral_boundary_matrix.csv', boundaries)
    _write(out / 'v5j_momentum_cash_neutral_failure_fallback.csv', fallback)
    _write(out / 'v5j_momentum_cash_neutral_pm_admission.csv', [decision])
    _write(out / 'v5j_momentum_cash_neutral_next_agent_queue.csv', _next_queue(decision))
    _write(out / 'v5j_momentum_cash_neutral_blocked_actions.csv', _blocked())
    summary = {
        'created_at_utc': _now(), 'task': 'v5j_momentum_overlay_cash_neutral_execution_spec',
        'scope': 'V5f internal_subsleeve_mom12_70_30 overlay reductions only',
        'value_base_weight_changed': False, 'mean_reversion_included': False, 'v5e_profit_lock_included': False,
        'frozen_sell_window': 'vwap_1400_hold_to_1445', 'pre2021_validation_weighted_adjustment_bps': _f(validation_momentum.get('weighted_adjustment_bps')),
        'formal_price_only_delta_return_pct_points': _f(momentum.get('delta_return_pct_points')),
        'formal_cash_path_comparable': False, 'accepted': False, 'live_trading_approved': False,
        'pm_gate_decision': decision['pm_gate_decision'],
    }
    (out / 'v5j_momentum_cash_neutral_execution_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (out / 'v5j_momentum_cash_neutral_execution_report.md').write_text(_report(summary, decision), encoding='utf-8')
    (out / 'v5j_momentum_cash_neutral_agent_execution_rules.md').write_text(_agent_rules(), encoding='utf-8')
    return summary


def _rules() -> list[dict[str, Any]]:
    return [
        {'rule_id': 'scope', 'rule': 'Apply only to negative changes in the V5f 70/30 momentum overlay weight.', 'required': True},
        {'rule_id': 'value_base', 'rule': 'V57f repaired value-base holdings and base rebalance orders retain original timing and quantity.', 'required': True},
        {'rule_id': 'signal', 'rule': 'At 14:00 use completed 1-minute bars only: if close <= session VWAP, sell at 14:01; otherwise sell at 14:46.', 'required': True},
        {'rule_id': 'sell_first', 'rule': 'Overlay sell orders must reach confirmed-fill state before any dependent overlay buy order is released.', 'required': True},
        {'rule_id': 'buy_time', 'rule': 'All dependent overlay buys wait until the first full minute after the final planned overlay sell confirmation; baseline buys are untouched.', 'required': True},
        {'rule_id': 'cash_neutral', 'rule': 'Within each sleeve, confirmed net overlay sell proceeds less fees must cover released overlay buy notional and fees. No borrowing, margin, proxy asset, or cross-sleeve cash is permitted.', 'required': True},
        {'rule_id': 'fallback', 'rule': 'Before order release, an infeasible cash-neutral ledger means no delayed overlay path is admitted; limited engineering records the failure and emits no order.', 'required': True},
        {'rule_id': 'post_trade', 'rule': 'Reconcile per sleeve confirmed cash, fills, target residual, and no-reentry state after the close.', 'required': True},
    ]


def _ledger_schema() -> list[dict[str, str]]:
    fields = [('rebalance_date', 'official V57f rebalance date'), ('sleeve_id', 'original sleeve only'), ('code', 'existing locked-pool code'), ('overlay_delta_weight', 'target minus existing overlay only'), ('side', 'sell or buy overlay leg'), ('planned_sell_time', '14:01 or 14:46 from frozen signal'), ('confirmed_fill_time', 'broker fill timestamp'), ('confirmed_gross_cash', 'confirmed proceeds or cost'), ('fees', 'actual fee'), ('available_sleeve_cash', 'confirmed sleeve cash before leg'), ('cash_neutral_pass', 'true only when confirmed cash covers dependent buy'), ('base_order_changed', 'must remain false'), ('cross_sleeve_transfer', 'must remain false'), ('proxy_asset_used', 'must remain false'), ('audit_status', 'pass, fail, or review')]
    return [{'field_name': name, 'definition': definition} for name, definition in fields]


def _cash_neutrality_gates() -> list[dict[str, str]]:
    return [
        {'gate_id': 'pit_target_snapshot', 'pass_condition': 'Official repaired V57f target and V5f 70/30 overlay target are frozen before the trading day.', 'failure_action': 'no delayed overlay path'},
        {'gate_id': 'minute_signal', 'pass_condition': '14:00 and selected next-bar minute data are present and completed.', 'failure_action': 'no delayed overlay path'},
        {'gate_id': 'same_sleeve_netting', 'pass_condition': 'Every delayed sell and dependent buy is assigned to the same sleeve.', 'failure_action': 'block'},
        {'gate_id': 'confirmed_cash', 'pass_condition': 'Confirmed overlay sell proceeds minus fees cover each released overlay buy plus fees.', 'failure_action': 'do not release dependent buy; record cash deficit'},
        {'gate_id': 'base_invariance', 'pass_condition': 'All value-base order quantities and times equal the original V57f/V5f schedule.', 'failure_action': 'block'},
        {'gate_id': 'close_reconciliation', 'pass_condition': 'Per-sleeve ledger cash and executed overlay weights reconcile to broker fills.', 'failure_action': 'review; no promotion'},
    ]


def _boundaries() -> list[dict[str, Any]]:
    return [
        {'component': 'V57f repaired value base', 'allowed_change': 'none', 'status': 'immutable'},
        {'component': 'V5f internal_subsleeve_mom12_70_30', 'allowed_change': 'execution timing of overlay reduction only, pending engineering', 'status': 'spec_only'},
        {'component': 'V5e profit lock', 'allowed_change': 'none; its independent sell-timing proxy was negative', 'status': 'blocked'},
        {'component': 'mean reversion overlay', 'allowed_change': 'none; 2021-2026 overlay-only result was negative', 'status': 'closed'},
        {'component': 'cash proxy asset', 'allowed_change': 'none', 'status': 'blocked'},
        {'component': 'cross-sleeve netting', 'allowed_change': 'none', 'status': 'blocked'},
    ]


def _failure_fallbacks() -> list[dict[str, str]]:
    return [
        {'failure_case': 'missing target or minute bar', 'limited_engineering_action': 'record failure; emit no delayed overlay order'},
        {'failure_case': 'overlay sell partial fill', 'limited_engineering_action': 'use confirmed proceeds only; do not release dependent buy beyond available sleeve cash'},
        {'failure_case': 'insufficient confirmed sleeve cash', 'limited_engineering_action': 'record residual target; do not borrow, transfer cash, or buy proxy'},
        {'failure_case': 'suspension or limit prevents fill', 'limited_engineering_action': 'record needs_review; do not fabricate a fill'},
        {'failure_case': 'base order would change', 'limited_engineering_action': 'block entire delayed-overlay experiment'},
    ]


def _decision(validation: dict[str, Any], formal: dict[str, Any], momentum: dict[str, str]) -> dict[str, Any]:
    supported = validation.get('pm_gate_decision') == 'overlay_only_pre2021_support_ready_for_formal_backtest_not_accepted'
    formal_positive = _f(momentum.get('delta_return_pct_points')) > 0
    return {'pm_gate_decision': 'admit_momentum_overlay_cash_neutral_ledger_to_limited_engineering_not_accepted' if supported and formal_positive else 'remain_spec_only', 'pre2021_validation_gate': validation.get('pm_gate_decision', ''), 'formal_gate': formal.get('pm_gate_decision', ''), 'momentum_price_only_delta_return_pct_points': _f(momentum.get('delta_return_pct_points')), 'accepted': False, 'reason': 'The prior test is price-only and has cash-path dependencies. Limited engineering is ledger and reconciliation only; no broker order path is approved.'}


def _next_queue(decision: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {'priority': 'P0', 'next_task': 'v5j_momentum_overlay_cash_neutral_ledger_limited_engineering', 'status': 'ready' if decision['pm_gate_decision'].startswith('admit_') else 'blocked', 'scope': 'dry-run ledger, cash-neutrality checks, and reconciliation only; no orders'},
        {'priority': 'P1', 'next_task': 'mean_reversion_overlay_sell_execution', 'status': 'closed', 'scope': '2021-2026 overlay-only result negative'},
    ]


def _blocked() -> list[dict[str, str]]:
    return [{'action': action, 'status': 'blocked'} for action in ('change V57f base target or order timing', 'change V5e profit-lock execution', 'apply to mean reversion', 'borrow or use margin', 'transfer cash across sleeves', 'use cash proxy asset', 'reenter a sold stock', 'live order submission', 'accepted or live-approved status')]


def _json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f'Required prior result is missing: {path}')
    return json.loads(path.read_text(encoding='utf-8'))


def _csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f'Required prior result is missing: {path}')
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ['empty']
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fields); writer.writeheader(); writer.writerows(rows)


def _f(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _report(summary: dict[str, Any], decision: dict[str, Any]) -> str:
    return '\n'.join(['# V5j Momentum Overlay Cash-Neutral Execution Spec', '', '- Scope: only V5f momentum-overlay reductions; the V57f value base stays unchanged.', '- The frozen sell window is `vwap_1400_hold_to_1445`.', '- Any realised price edge is price-only until this cash-neutral ledger has passed limited engineering.', f"- PM gate: `{decision['pm_gate_decision']}`.", '- Mean reversion is closed after its negative formal result; V5e is explicitly excluded.', ''])


def _agent_rules() -> str:
    return '# Execution Rules\n\n1. Produce a dry-run ledger only.\n2. Do not emit broker, QMT, JoinQuant, or simulated orders.\n3. Preserve all value-base orders exactly.\n4. Require confirmed same-sleeve cash before dependent overlay buys.\n5. Record every failure without inventing fills or residual allocations.\n'


if __name__ == '__main__':
    print(json.dumps(run_v5j_momentum_overlay_cash_neutral_execution_spec(), ensure_ascii=False, indent=2))

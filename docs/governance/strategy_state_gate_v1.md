# Strategy State Gate V1

## Purpose

`strategy-state-gate` is the PM read-only gate for strategy state promotion.

It prevents accidental status upgrades such as:

- `formal_strategy_candidate`
- `platform_replication_passed`
- `paper_trading_started`
- `accepted_strategy`
- `live_trading_approved`

## Rule

Passing this gate never changes `status_registry.json` automatically.

If evidence is sufficient, the result is `ready_for_user_stage_gate`, because strategy promotion is a stage-gate decision. If evidence is insufficient, the result is `blocked`.

## Current V5.7f Check

Command target:

- Strategy: `dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f`
- Target status: `accepted_strategy`

Result:

- Status: `blocked`
- Blockers: `2`

Blocking reasons:

- Missing required `platform_replication_passed` status.
- Strategy still lists open blockers.

This confirms V5.7f must remain a frozen formal ETF candidate and cannot be accepted until platform attribution and clean forward evidence mature.

## Evidence

- Runner: `src/v5/strategy_state_gate_runner.py`
- Tests: `tests/test_strategy_state_gate_runner.py`
- V5.7f accepted gate summary: `strategy_state_gates_v58/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/accepted_strategy/strategy_state_gate_summary.json`
- V5.7f accepted gate report: `strategy_state_gates_v58/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/accepted_strategy/strategy_state_gate_report.md`

## PM Use

Run this gate before manually changing a strategy's status in the registry.

The gate is especially important before:

- platform replication passed marking
- paper-trading start marking
- accepted strategy marking
- live trading approval

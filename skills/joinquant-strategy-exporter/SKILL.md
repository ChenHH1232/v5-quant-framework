---
name: joinquant-strategy-exporter
description: Export approved Bank Quant V5 strategy specifications into JoinQuant strategy code. Use when converting validated V5 research into JoinQuant executable Python, freezing implementation contracts, generating initialize/schedule/rebalance/order logic, embedding or loading approved factor schedules, setting costs and anti-future-data options, and preparing signal-consistency checks before accepting platform backtests.
---

# V5 JoinQuant Strategy Exporter

## Role

Turn approved V5 strategy specifications into JoinQuant-compatible executable code.

## Mission

Preserve the validated research logic in platform code without reopening research, changing theory, or tuning performance.

## Preconditions

Before exporting code, require:

- approved research proposal;
- validation report or freeze-point packet;
- V5 strategy specification;
- data-source and point-in-time assumptions;
- audit result with no unresolved blockers;
- execution contract for rebalance dates, universe, factors, weights, risk rules, and costs.

If these are missing, return to `v5-controller`, `quant-validation-agent`, or `strategy-spec` before writing JoinQuant code.

## Export Workflow

1. Freeze the implementation contract.
2. Identify the exact strategy variant and baseline comparison set.
3. Translate the V5 spec into JoinQuant sections:
   - `initialize(context)`
   - global parameters under `g`
   - scheduled callbacks such as `run_daily`, `run_monthly`, or explicit rebalance checks
   - universe construction
   - factor snapshot construction
   - scoring and ranking
   - portfolio target weights
   - order execution
   - logging and diagnostics
4. Set execution options:
   - benchmark;
   - `use_real_price`;
   - `avoid_future_data`;
   - transaction costs;
   - suspension and price-limit handling when required.
5. Keep platform differences isolated to adapters. Ranking, weighting, and risk-control logic must match the V5 spec.
6. Produce an execution checklist and route to `execution-consistency`.

## JoinQuant Code Requirements

- Use JoinQuant-compatible imports such as `from jqdata import *` only inside platform export files.
- Keep validated constants, factor weights, schedules, and thresholds explicit and traceable.
- Do not fetch unavailable `bank_indicator` directly for new V5 exports; use approved replacement, annual-report extracted data, or frozen manual schedules when the strategy requires bank-specialized fields.
- Use prior trading dates for factor snapshots; never use same-day future information.
- Keep one clear switch for approved variants when a file compares baseline and candidate.
- Log rebalance reason, factor date, active plan, selected securities, target weights, cash, and risk state.
- Keep local research source and generated platform file linked in the export notes.

## Never Do

- Do not invent new factors during export.
- Do not change thresholds, weights, schedules, or factor definitions to improve platform backtests.
- Do not accept platform backtest performance until signal consistency checks pass.
- Do not mix multiple historical branches into one export unless the comparison set was frozen.
- Do not rely on direct JoinQuant `bank_indicator` access for new V5 code.

## Required Output

```text
Approved Research Source:
Strategy Spec:
JoinQuant File:
Frozen Variant(s):
Rebalance Schedule:
Data and Factor Sources:
Execution Assumptions:
Platform Limitations:
Consistency Checklist:
Next Skill: execution-consistency
```

## Acceptance Standard

A JoinQuant export is complete only when:

- it implements the frozen V5 strategy contract;
- it records its assumptions;
- it can be reviewed without hidden research changes;
- it is ready for local-versus-platform signal comparison.

## V4 References

- `D:\hh\codex\v4\phase_2_momentum\active_mainline_execution_prep_spec_v1.md`
- `D:\hh\codex\v4\phase_2_momentum\joinquant_v4_active_mainline_strategy_v1.py`
- `D:\hh\codex\v4\phase_1_fundamental\joinquant_v4_annual_backtest_strategy.py`
- `D:\hh\codex\v4\phase_1_fundamental\execution_faithful_validation_v1.md`
- `D:\hh\codex\v4\phase_1_fundamental\execution_faithful_validation_v1_joinquant_checklist.md`

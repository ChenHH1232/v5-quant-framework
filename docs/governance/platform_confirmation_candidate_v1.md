# Platform Confirmation Candidate V1

Date: 2026-07-15

Strategy: `bank_value_15y`

## Status

`platform_confirmation_candidate_v1`

This version is frozen for JoinQuant/platform-confirmation comparison. It is not a final accepted production strategy.

## Frozen Contract

- Strategy spec: `examples/bank_value_15y_strategy.json`
- Selection count: `8`
- Factor weights:
  - low_price_to_book: `0.25`
  - dividend_yield: `0.15`
  - return_on_equity_ttm: `0.20`
  - non_performing_loan_ratio: `0.15`
  - provision_coverage_ratio: `0.15`
  - core_tier_1_capital_adequacy_ratio: `0.10`
- Value trap guard: enabled.
- Rebalance: quarterly.
- Execution comparison:
  - stock prices: JoinQuant `fq=None`
  - benchmark: `512800.XSHG`, `fq=pre`
  - cash dividend events: explicit net cash events
  - lot size: `100`
  - commission: `0.03%`, min `5`
- Defensive overlay:
  - status: `risk_control_candidate`
  - mode: `benchmark_ma`
  - benchmark: `512800.XSHG`
  - MA days: `252`
  - risk-off exposure multiplier: `0.5`

## Governance Rule

The `2021-05-01` to `2026-05-31` window is no longer a tuning window.

Allowed uses:

- JoinQuant/platform execution simulation.
- Local-vs-platform attribution.
- Comparing different model families as reference.
- Debugging data, dividend, benchmark, and execution alignment.

Not allowed:

- Tuning factor weights.
- Changing selection count.
- Adding or removing factors.
- Selecting defensive parameters by performance.
- Claiming clean out-of-sample acceptance.

Single-model statistical validation must use rolling validation and formal common-sample tests.

## Required Next Evidence

- Formal factor ablation.
- Common-sample baseline comparison.
- Robustness checks.
- Point-in-time bank universe.
- Local-vs-JoinQuant daily attribution.
- Forward / paper-trading log.

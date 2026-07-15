# Governance Record: bank_high_dividend_sustainability_v3_jq_signal_alignment_v1

Date: 2026-07-15

Experiment layer:

`platform_replication`

Status:

`usable_for_routine_local_development`

Not status:

`formal_strategy_acceptance`

## Frozen Local Configuration

```text
strategy_id = bank_high_dividend_sustainability_v3
eastmoney_visibility_mode = joinquant_source_year
value_trap_guard_mode = disabled
signal_dividend_yield_mode = cash_dividend_trailing
execution_price = daily open approximation
valuation_price = daily close
benchmark = 512800.XSHG
window = 2021-05-01 to 2026-05-31
```

## Decision

This version may be used for routine local engineering development and platform pre-checks.

It must not be used as investment evidence or formal acceptance evidence.

## Evidence Summary

- first-day selected stocks matched 8 / 8;
- signal set-match reached 17 / 19 local rebalance dates;
- transaction matched keys improved to 215;
- final local strategy return exceeded JoinQuant by 5.88 pct points;
- final local benchmark return was 1.35 pct points below JoinQuant;
- exact platform replication remains incomplete.

## Required Next Gate

Before strategy promotion:

1. Quant Validation Agent must complete formal rolling / baseline / ablation / robustness validation.
2. Research Agent must finish V4 legacy quality source-date audit or replace it with stronger PIT quality data.
3. Project Manager Agent must prevent platform replication results from being treated as research evidence.


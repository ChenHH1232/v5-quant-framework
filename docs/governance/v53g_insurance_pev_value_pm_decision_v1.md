# V5.3g Insurance P/EV Value PM Decision

Date: 2026-07-17

Status:

```text
formal_strategy_candidate + engineering_smoke_test_completed_needs_review
```

Not status:

```text
accepted_strategy
paper_trading_ready
joinquant_code_ready
```

## PM Decision

V5.3g is the first insurance model in this line that clears the main research data gate and produces an insurance-specific value signal.

The accepted research hypothesis is:

```text
For core listed A-share insurers, low price-to-embedded-value is a cleaner value anchor than generic low PB. NBV growth is useful for interpretation, but it is not approved as an incremental score factor.
```

## Evidence

Source repair:

- Evidence file: `knowledge/research_agent/references/insurance_ev_nbv_reviewed_2020_2025_core5.csv`
- Rows: `60`
- Core codes: `5`
- Fields: `embedded_value`, `new_business_value`
- Covered years after PIT panel join: `2021, 2022, 2023, 2024, 2025, 2026`
- First covered rebalance date: `2021-04-01`
- Last covered rebalance date: `2026-04-01`
- Source audit status: `insurance_special_fields_source_repair_passed`

Formal validation:

- Output: `validation_formal_v53g_insurance_pev_value/insurance_pev_value_v53g`
- PIT leakage audit: `pass`
- Observations: `105`
- Dates: `21`
- Mean IC: `0.0513`
- Mean RankIC: `0.1095`
- Positive IC ratio: `71.43%`
- Equal-weight covered insurance cumulative return: `23.40%`
- Low P/EV top3 cumulative return: `32.14%`

Rolling validation:

| Year | Cumulative return | Positive ratio | Read |
| --- | ---: | ---: | --- |
| 2023 | -4.58% | 75% | weak but not structurally broken |
| 2024 | 48.75% | 75% | strong |
| 2025 | 44.08% | 100% | strong |
| 2026 | -21.98% | 0% | unresolved absolute drawdown |

Robustness:

- Top2 cumulative return: `62.41%`
- Top3 cumulative return: `32.14%`
- Top4 cumulative return: `18.16%`

This is not parameter-fragile in the sense that all tested selection counts remain positive, but it is concentration-sensitive because the core insurance universe has only five names.

Engineering smoke test:

- Output: `local_daily_backtests_insurance_v53g/insurance_pev_value_v53g`
- Window: `2021-05-01` to `2026-05-31`
- Strategy return: `29.89%`
- Annualized return: `5.51%`
- Benchmark: `399809.XSHE`
- Benchmark return: `-3.02%`
- Excess return: `32.91%`
- Max drawdown: `34.20%`
- Strategy volatility: `30.15%`
- Dividend events captured while held: `18`
- Dividend policy: cash dividend taxed at `20%`

Failure-year attribution:

| Year | Strategy return | Benchmark return | Excess | PM read |
| --- | ---: | ---: | ---: | --- |
| 2021 | -9.92% | -16.72% | 6.80% | absolute loss, but industry drawdown was worse |
| 2022 | -0.71% | -8.27% | 7.56% | absolute near-flat, relative protection worked |
| 2026 | -20.88% | -19.59% | -1.29% | unresolved partial-year tail risk |

Overfit audit:

- Output: `validation_overfit_v53g_insurance/insurance_pev_value_v53g`
- Blockers: `0`
- Needs review: `3`
- Passed checks: `11`

Remaining review items:

- Core insurance universe is very small, so first-date constituent smell test must be manually accepted.
- The 2021-05 to 2026-05 daily window is platform-confirmation context, not clean out-of-sample acceptance evidence.
- Formal validation includes rolling tests, but the spec method is labeled `formal_research_pit_validation`, so PM must not confuse it with accepted out-of-sample proof.

## Agent Read

Research Agent:

- Low P/EV has insurance-specific economic meaning because embedded value approximates the present value of in-force life insurance business plus adjusted net worth.
- Generic low PB worked partly because it proxied low P/EV, but P/EV is a cleaner insurance-domain expression.
- NBV growth remains a franchise-quality diagnostic, not an approved alpha score.

Quant Validation Agent:

- Statistical evidence is positive but not strong enough for accepted strategy status.
- P/EV passes PIT leakage and rolling validation checks.
- 2026 remains the key unresolved stress period.

Engineering Agent:

- Local daily simulation can run with true daily open/close, cash dividends after 20% tax, lot rounding, commissions, and `399809.XSHE` benchmark.
- No JoinQuant code should be written until PM explicitly opens platform replication.

Project Manager:

- Promote V5.3g to `formal_strategy_candidate`.
- Do not promote to accepted strategy.
- Do not tune around 2026.
- Next gate is either platform replication preparation or paper-trading record, not further research weight tweaking.

## Next Gate

```text
platform_replication_or_paper_trading_preparation
```

Required before platform replication:

1. Manual PM acceptance of the small-universe concentration risk.
2. Decide whether `399809.XSHE` remains the official benchmark.
3. Freeze V5.3g signals and forbid additional return tuning.
4. Prepare JoinQuant script only after the above three points are explicitly approved.

# V5.8h Oil / Gas Engineering Smoke Test PM Decision

Date: 2026-07-20

## Stage

Experiment layer: `engineering_smoke_test`

Decision: `engineering_smoke_test_completed_not_platform_replication`

V5.8h moves the frozen V5.8g oil / gas candidate into Engineering Agent smoke testing. This is not a JoinQuant platform test, not paper trading, and not basket inclusion.

## Why Engineering Was Allowed

The previous blocker was the core source gate. V5.8g repaired the core source gate:

| Core State Metric | Coverage |
| --- | ---: |
| `crude_oil_price_state` | 18 / 18 |
| `bitumen_price_state` | 18 / 18 |
| `gas_liquid_price_state` | 18 / 18 |
| `refining_spread_proxy_state` | 18 / 18 |

Formal validation was completed with PIT leakage audit passing. This is enough for an Engineering smoke test that checks execution, cash, lots, trades, holdings, dividends and logs.

## Engineering Inputs

| Input | Path |
| --- | --- |
| Strategy spec | `examples/oil_gas_state_conditioned_ocf_v58g_strategy.json` |
| PIT panel | `数据库/processed/oil_gas_state_conditioned_panel_v58g/oil_gas_state_conditioned_ocf_v58g/panel.csv` |
| Real daily prices | `数据库/processed/oil_gas_v58a_joinquant_real_daily_prices.csv` |
| Benchmark prices | `数据库/processed/oil_gas_v58a_joinquant_real_benchmark_prices.csv` |
| Cash dividends | `数据库/processed/oil_gas_v58g_joinquant_cash_dividends.csv` |

Dividend policy:

- source: JoinQuant `finance.STK_XR_XD`
- tax treatment: 20% tax withheld
- cash arrival proxy: ex-dividend date, because the validated JoinQuant field set does not expose a separate cash arrival date

## Engineering Smoke Test Result

Output:

```text
validation_daily_v58g_oil_gas/oil_gas_state_conditioned_ocf_v58g/summary.json
```

Summary:

| Item | Result |
| --- | ---: |
| Rebalance signals | 18 |
| Daily rows | 1228 |
| Trades | 197 |
| Holding snapshots | 144 |
| Dividend cash rows | 29 |
| Strategy return | 99.79% |
| Annualized return | 15.26% |
| Benchmark return | -4.52% |
| Max drawdown | 21.78% |
| Sharpe | 0.714 |

The first executed rebalance is `2022-01-04`. The earlier 2021 period is cash because the repaired PIT panel starts effective coverage from 2022, not because the order engine failed.

## Overfit Audit

Output:

```text
overfit_audits_v58g_oil_gas/oil_gas_state_conditioned_ocf_v58g/overfit_audit_summary.json
```

Result:

| Item | Result |
| --- | ---: |
| Status | `needs_review` |
| Blockers | 0 |
| Needs review | 2 |
| Pass | 12 |

Needs-review items:

- 2021-05 to 2026-05 remains a platform-confirmation / engineering smoke-test window, not clean out-of-sample acceptance evidence.
- Full parameter perturbation contract still needs to be formalized before PM promotion.

## PM Interpretation

The oil / gas line has reached Engineering smoke test stage.

This means the Engineering Agent has proven that the candidate can run through local daily execution mechanics:

- signal generation
- real daily open execution
- close valuation
- 100-share lot rounding
- cash accounting
- commissions
- net cash dividends
- trades / holdings / daily return logs

This does not mean the strategy is deployable.

## Remaining Blockers

V5.8h still cannot enter platform replication, paper trading, accepted strategy, or V5.7f basket inclusion because:

- inventory / demand state is still missing
- pipeline tariff / policy state is still missing
- refining spread remains a licensed futures proxy, not a reviewed operating margin
- business exposure remains JoinQuant industry proxy rather than reviewed annual-report segment evidence
- the benchmark is still HS300 in the current daily smoke test; a proper oil / gas or energy-sector benchmark is required before platform comparison
- 2021-2026 evidence cannot be used as clean out-of-sample acceptance

## PM Decision

Current status:

```text
engineering_smoke_test_completed_needs_review
```

Allowed next actions:

1. Build an oil / gas sector benchmark.
2. Repair inventory / demand state and pipeline tariff / policy state.
3. Review business exposure from annual reports.
4. Add a parameter perturbation contract for V5.8g.
5. Rerun engineering smoke test with the sector benchmark.

Blocked next actions:

- JoinQuant code generation
- platform replication
- paper trading
- V5.7f basket inclusion
- accepted strategy

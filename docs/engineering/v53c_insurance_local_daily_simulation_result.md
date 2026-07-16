# V5.3c Insurance Local Daily Simulation Result

Date: 2026-07-17

Status:

```text
engineering_smoke_test_with_dividends_completed_needs_review_before_platform_replication
```

## Scope

This run moved V5.3c from research PIT validation into Engineering Agent local daily simulation.

It did not generate JoinQuant strategy code.

## Inputs

Spec:

```text
examples / insurance_low_pb_only_v53c_strategy.json
```

Research PIT panel:

```text
database / processed / insurance_pit_panel_v53b / panel.csv
```

Real JoinQuant execution prices:

```text
database / processed / insurance_v53c_joinquant_real_daily_prices.csv
```

Real JoinQuant cash dividends:

```text
database / processed / insurance_v53c_joinquant_cash_dividends.csv
```

Local daily output:

```text
local_daily_backtests_insurance_v53c / insurance_low_pb_only_v53c
```

## Benchmark Policy

The local engineering benchmark is:

```text
399809.XSHE
```

JoinQuant name:

```text
中证方正富邦保险主题指数
```

Reason:

```text
This is a priceable insurance-theme index in JoinQuant. It is more appropriate than the bank ETF and more external than the internal equal-weight core-insurance fallback.
```

## Execution Model

| Item | Value |
| --- | ---: |
| Start | 2021-05-01 |
| End | 2026-05-31 |
| Daily rows | 1228 |
| Rebalance signals | 20 |
| Initial cash | 2,000,000 |
| Target exposure | 99.50% |
| Lot size | 100 shares |
| Trade price | daily open |
| Valuation price | daily close |
| Open commission | 0.03% |
| Close commission | 0.03% |
| Minimum commission | 5 |
| Value-trap guard | disabled |
| Dividend tax rate | 20% |
| Dividend cash events | 37 source events / 20 held-position cash events |

Value-trap guard is disabled because V5.3c froze the rule as low PB only. No insurance-specific quality guard has been approved yet.

## Outputs

- `summary.json`
- `daily_returns.csv`
- `holdings.csv`
- `trades.csv`
- `dividends.csv`
- `rebalance_signals.csv`
- `RUN_MANIFEST.json`

The dividend log is present and populated from JoinQuant `finance.STK_XR_XD`.

Dividend policy:

```text
net_cash_per_share = bonus_ratio_rmb / 10 * (1 - 20%)
```

`pay_date` currently uses `a_xr_date`, because the validated JoinQuant field set does not expose a separate cash arrival date.

## Local Daily Metrics

| Metric | Value |
| --- | ---: |
| Strategy return | 42.03% |
| Annualized return | 7.47% |
| Benchmark return | -3.02% |
| Excess return | 45.05% |
| Alpha | 0.0811 |
| Beta | 1.0242 |
| Sharpe | 0.4034 |
| Max drawdown | 33.02% |
| Max drawdown interval | 2021-07-06 to 2022-10-28 |
| Strategy volatility | 26.45% |
| Benchmark volatility | 24.48% |
| Total local dividend cash | 271,513.36 |

PM read:

```text
Adding real net cash dividends materially improves the local daily result, but the daily path still exposes a large 2021-2022 drawdown.
```

## Failure-Year Attribution

Output:

```text
failure_attribution_insurance_v53c / insurance_low_pb_only_v53c
```

| Year | Strategy return | Benchmark return | Excess return | Max drawdown | Dividend cash | Read |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 2021 | -12.00% | -16.72% | 4.73% | 14.52% | 36,618.72 | loses money but beats insurance-theme index |
| 2026 | -22.56% | -19.59% | -2.98% | 30.99% | 0.00 | loses money and lags insurance-theme index |

PM read:

```text
2021 is an industry drawdown year where low PB still adds relative value. 2026 is the unresolved failure year because low PB underperforms the insurance-theme index and receives no dividend cushion in the partial-year sample.
```

## Engineering Audit

Overfit audit:

```text
validation_overfit_v53c_insurance / insurance_low_pb_only_v53c
```

Audit summary:

| Item | Value |
| --- | ---: |
| Blockers | 0 |
| Needs review | 1 |
| Passed checks | 13 |

The only needs-review item:

```text
2021-05 to 2026-05 is a platform-confirmation / engineering window, not clean out-of-sample acceptance evidence.
```

## Current Blockers Before Platform Replication

No hard engineering blocker was found for local daily simulation.

Platform replication remains blocked by:

- 2026 failure-year risk needs PM review;
- no JoinQuant code should be written until PM accepts the benchmark/dividend policy and 2026 risk.

## Next Gate

```text
engineering_daily_simulation_with_dividends_passed_platform_replication_pending_pm_review
```

Recommended next Engineering Agent tasks:

1. approve `399809.XSHE` as the platform comparison benchmark;
2. decide whether the 2026 partial-year low-PB failure is acceptable for platform replication preparation;
3. only after PM approval, prepare platform replication inputs.

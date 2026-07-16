# Insurance V5.3c Local Daily Simulation Result

Date: 2026-07-17

Status:

```text
engineering_daily_simulation_with_dividends_passed_platform_replication_pending_pm_review
```

## Memory

Engineering Agent ran V5.3c low-PB-only through local JoinQuant-like daily simulation.

This is not research acceptance and not platform replication.

## Main Result

| Item | Value |
| --- | ---: |
| Strategy return | 42.03% |
| Annualized return | 7.47% |
| Benchmark return | -3.02% |
| Excess return | 45.05% |
| Max drawdown | 33.02% |
| Signals | 20 |
| Daily rows | 1228 |
| Held-position dividend cash | 271,513.36 |

Benchmark:

```text
399809.XSHE / 中证方正富邦保险主题指数
```

Reason:

```text
The bank ETF is not appropriate for insurance. JoinQuant can price 399809.XSHE, which is an insurance-theme index.
```

## Dividend Update

Real JoinQuant cash-dividend events were added from `finance.STK_XR_XD`.

Policy:

```text
net_cash_per_share = bonus_ratio_rmb / 10 * 80%
```

## Failure-Year Memory

- 2021: strategy return `-12.00%`, benchmark return `-16.72%`; low PB loses money but beats the insurance-theme benchmark, with dividends cushioning drawdown.
- 2026: strategy return `-22.56%`, benchmark return `-19.59%`; low PB underperforms, has no dividend cushion, and remains the unresolved tail-risk year.

Before platform replication:

- PM must approve `399809.XSHE` as the platform comparison benchmark;
- PM must decide whether 2026 partial-year failure blocks platform replication preparation.

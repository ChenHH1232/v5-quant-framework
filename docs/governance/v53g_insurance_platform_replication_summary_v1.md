# V5.3g Insurance Platform Replication Summary V1

Date: 2026-07-17

Status:

```text
platform_replication_summary_matched_pending_daily_attribution
```

Not status:

```text
accepted_strategy
live_trading_approved
full_platform_replication_passed
```

## Purpose

Record the first JoinQuant platform run for frozen V5.3g.

This is a platform-replication summary check only. It must not be used to tune the strategy.

## Frozen Strategy

```text
insurance_pev_value_v53g
```

Frozen rule:

```text
Core A-share insurers, quarterly rebalance, select the 3 lowest PIT-visible P/EV names.
```

## Local Vs JoinQuant Summary

| Metric | Local daily simulation | JoinQuant run | Difference |
| --- | ---: | ---: | ---: |
| Strategy return | 29.89% | 28.86% | -1.03 pp |
| Annualized return | 5.51% | 5.30% | -0.21 pp |
| Benchmark return | -3.02% | -3.51% | -0.49 pp |
| Excess return | 32.91% | 33.55% | +0.64 pp |
| Beta | 1.178 | 1.176 | -0.002 |
| Strategy volatility | 30.15% | 30.00% | -0.15 pp |
| Benchmark volatility | 24.48% | 24.40% | -0.08 pp |
| Max drawdown | 34.20% | 34.25% | +0.05 pp |
| Max drawdown interval | 2023-05-08 to 2024-01-23 | 2023-05-08 to 2024-01-23 | matched |
| Information ratio | 0.765 | 0.616 | -0.149 |

## PM Read

The JoinQuant summary is close enough to the local simulation to confirm that the frozen V5.3g strategy contract is being replicated at the summary level.

The small residual difference is consistent with known execution and platform mechanics:

- local daily-open approximation versus JoinQuant scheduled `09:40` execution;
- benchmark price / adjustment convention differences;
- cash residual and order-value rounding;
- dividend cash timing and tax treatment;
- JoinQuant transaction and commission handling.

## Remaining Requirement

To upgrade from summary-level match to full platform replication passed, export:

- daily returns CSV;
- transaction / trade detail CSV;
- position CSV;
- full log TXT.

Then run local-vs-JoinQuant daily attribution.

## PM Decision

V5.3g remains:

```text
frozen_formal_strategy_candidate
```

It may be tracked in paper trading and platform attribution, but it is still not:

```text
accepted_strategy
```

No tuning is allowed based on this JoinQuant result.

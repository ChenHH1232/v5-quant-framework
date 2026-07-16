# Governance Record: v51f_utilities_frozen_signal_platform_test_v1

Date: 2026-07-16

Strategy:

```text
utilities_demand_state_v51f
```

Layer:

```text
platform_replication_precheck
```

Status:

```text
frozen_signal_platform_test_passed
```

Not status:

```text
accepted_strategy
live_joinquant_factor_recompute_passed
paper_trading_passed
```

## Test Type

This JoinQuant run used frozen V5.1f local rebalance signals.

It did not recompute the full signal on JoinQuant because the first live-factor script showed:

```text
valuation.dividend_ratio is not available in the tested JoinQuant runtime
```

Therefore this test answers:

```text
Can JoinQuant execute the V5.1f frozen signal contract and produce a return path close to the local JoinQuant-like runner?
```

It does not yet answer:

```text
Can JoinQuant independently rebuild every V5.1f factor from live platform fields?
```

## Benchmark

Benchmark used:

```text
000007.XSHG
```

This is the utilities benchmark used for V5.1f platform testing.

Bank ETF:

```text
512800.XSHG
```

is not appropriate for this utilities test and is not used by the V5.1f frozen-signal JoinQuant script.

## Local Versus JoinQuant Summary

| Metric | Local JoinQuant-like | JoinQuant frozen signal | Difference |
|---|---:|---:|---:|
| strategy return | 200.92% | 200.58% | -0.34 pct points |
| annualized return | 25.37% | 25.11% | -0.26 pct points |
| benchmark return | 15.86% | 15.89% | +0.03 pct points |
| alpha | 0.220 | 0.221 | +0.001 |
| beta | 1.084 | 1.079 | -0.005 |
| strategy volatility | 0.243 | 0.239 | -0.004 |
| benchmark volatility | 0.166 | 0.165 | -0.001 |
| max drawdown | 27.53% | 24.04% | -3.49 pct points |
| max drawdown interval | 2024-05-29,2024-09-11 | 2024-05-29,2024-09-11 | aligned |
| information ratio | 1.294 | 1.388 | +0.094 |

## PM Interpretation

The frozen-signal platform test passes.

Evidence:

```text
1. Strategy final return differs by only 0.34 percentage points.
2. Benchmark final return differs by only 0.03 percentage points.
3. Beta and volatility are nearly identical.
4. Maximum drawdown interval is identical.
```

The residual differences are consistent with:

```text
JoinQuant 09:40 execution versus local daily-open approximation;
order fill details;
hundred-share rounding;
cash timing;
platform accounting conventions.
```

## Remaining Blockers

V5.1f is still not an accepted strategy.

Before acceptance:

```text
1. Export JoinQuant daily result, transaction, and position CSV files.
2. Run daily NAV, trade, and position attribution against local outputs.
3. Fix or replace the live JoinQuant dividend-yield source.
4. Decide whether live-factor JoinQuant recomputation is required, or frozen-signal execution is sufficient for paper trading.
5. Start forward / paper-trading records.
```


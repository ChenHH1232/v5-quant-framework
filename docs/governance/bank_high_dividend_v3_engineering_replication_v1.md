# Governance Record: bank_high_dividend_sustainability_v3_engineering_replication_v1

Date: 2026-07-16

Experiment layer:

`platform_replication`

## Decision

Engineering local daily simulation for V3 formal candidate is complete.

Fresh JoinQuant execution for the guard-applied V3 formal candidate is now complete by user-reported platform summary, and fresh daily-result attribution is complete.

Strict JoinQuant replication is not complete yet because fresh position, transaction, and log exports still need attribution against local simulation.

## Evidence

- Formal candidate local daily simulation produced:
  - strategy return: 61.76%
  - benchmark return: 25.16%
  - max drawdown: 17.24%
  - trade count: 192
- Existing JoinQuant export versus formal candidate:
  - first-day selected stocks match only 5 / 8;
  - matched transaction keys: 103;
  - JoinQuant-only transaction keys: 129;
  - local-only transaction keys: 88.
- Existing JoinQuant export versus no-guard local replication:
  - first-day selected stocks match 8 / 8;
  - matched transaction keys: 215;
  - JoinQuant-only transaction keys: 17;
  - local-only transaction keys: 5.
- Fresh guard-applied JoinQuant formal-candidate summary reported by user:
  - strategy return: 57.35%
  - annualized return: 9.67%
  - benchmark return: 26.51%
  - max drawdown: 17.06%
  - beta: 0.864
  - strategy volatility: 0.163
  - max drawdown interval: 2021/07/07,2022/10/31
- Local formal-candidate comparison:
  - strategy return: 61.76%
  - annualized return: 10.37%
  - benchmark return: 25.16%
  - max drawdown: 17.24%
  - beta: 0.863
  - strategy volatility: 0.163
  - max drawdown interval: 2021-07-07,2022-10-31
- Fresh daily-result attribution using `result_1 (16).csv`:
  - matched days: 1228
  - final strategy diff: +4.41 percentage points
  - final benchmark diff: -1.35 percentage points
  - max absolute strategy diff: 7.19 percentage points
  - max absolute benchmark diff: 1.62 percentage points
  - largest divergence period: 2026-04 to 2026-05

## PM Interpretation

The previous JoinQuant export should be treated as an older no-guard platform replication run.

It should not be used to accept or reject the guard-applied V3 formal candidate.

The fresh guard-applied JoinQuant platform summary is close enough to local simulation to move to order-level attribution. Daily NAV attribution shows material alignment, with the remaining strategy-return gap concentrated late in the window. Risk path alignment is strong, while return difference still requires position, transaction, dividend, and cash decomposition.

## Required Next Gate

Engineering Agent must attribute fresh JoinQuant position, transaction, and log exports before Project Manager Agent can mark platform replication as passed.

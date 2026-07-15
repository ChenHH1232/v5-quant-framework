# Governance Record: bank_high_dividend_sustainability_v3_engineering_replication_v1

Date: 2026-07-16

Experiment layer:

`platform_replication`

## Decision

Engineering local daily simulation for V3 formal candidate is complete.

Fresh JoinQuant execution for the guard-applied V3 formal candidate is now complete by user-reported platform summary. Fresh daily-result attribution and transaction attribution are complete.

Strict JoinQuant replication is not complete yet because the current local PIT panel ends at the 2026-01 rebalance and misses the 2026-04 rebalance that JoinQuant executed.

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
- Fresh transaction attribution using `transaction (1).csv`:
  - JoinQuant transaction rows: 206
  - local transaction rows: 191
  - matched transaction keys: 189
  - JoinQuant-only keys: 17
  - local-only keys: 2
  - first-day selected stocks match: 8 / 8
  - first-day absolute value difference: 3,441
  - key issue: JoinQuant has 10 transactions on 2026-04-01 while local has no 2026-04 rebalance signal.
- Local data coverage issue:
  - `joinquant_basic_pit_panel_v4_legacy_quality/panel.csv` ends at `2026-01-05`
  - local `rebalance_signals.csv` ends at `2026-01-05`
  - JoinQuant executed the expected 2026-04 rebalance.

## PM Interpretation

The previous JoinQuant export should be treated as an older no-guard platform replication run.

It should not be used to accept or reject the guard-applied V3 formal candidate.

The fresh guard-applied JoinQuant platform summary is close enough to local simulation to move forward, and transaction attribution confirms the first rebalance signal contract is aligned. The remaining late-window return gap is now primarily a local data-coverage problem, not evidence that the strategy failed or that JoinQuant ran the wrong contract.

## Required Next Gate

Engineering Agent must extend the local PIT panel through the 2026-04 rebalance, rerun local daily simulation, rerun daily and transaction attribution, and then attribute fresh position/log exports before Project Manager Agent can mark platform replication as passed.

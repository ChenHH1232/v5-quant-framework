# Governance Record: bank_high_dividend_sustainability_v3_engineering_replication_v1

Date: 2026-07-16

Experiment layer:

`platform_replication`

## Decision

Engineering local daily simulation for V3 formal candidate is complete.

Strict JoinQuant replication is not complete yet because the available JoinQuant export corresponds to a no-guard contract, while the formal candidate uses the value-trap guard.

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

## PM Interpretation

The previous JoinQuant export should be treated as an older no-guard platform replication run.

It should not be used to accept or reject the guard-applied V3 formal candidate.

## Required Next Gate

Engineering Agent must provide a fresh JoinQuant run for the guard-applied formal candidate before Project Manager Agent can mark engineering replication as passed.


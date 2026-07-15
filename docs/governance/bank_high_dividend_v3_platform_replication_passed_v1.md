# Governance Record: bank_high_dividend_sustainability_v3_platform_replication_passed_v1

Date: 2026-07-16

Experiment layer:

`platform_replication`

## Decision

Bank High Dividend Sustainability V3 is marked:

```text
formal_strategy_candidate + platform_replication_passed
```

It is still not:

```text
accepted_strategy
```

## Evidence

- Fresh JoinQuant formal-candidate result:
  - strategy return: 57.35%
  - annualized return: 9.67%
  - benchmark return: 26.51%
  - max drawdown: 17.06%
  - beta: 0.864
  - strategy volatility: 0.163
- Extended local platform-replication result after adding the missing `2026-04-01` PIT date:
  - strategy return: 57.94%
  - annualized return: 9.83%
  - benchmark return: 25.16%
  - max drawdown: 17.24%
  - beta: 0.864
  - strategy volatility: 0.163
- Daily attribution after extension:
  - matched days: 1228
  - final strategy diff: +0.59 percentage points
  - max absolute strategy diff: 2.52 percentage points
- Transaction attribution after extension:
  - matched transaction keys: 198
  - JoinQuant-only keys: 8
  - local-only keys: 2
- Position attribution after extension:
  - local rebalance dates checked: 20
  - code mismatches on rebalance dates: 0
  - first-day selected stocks match: 8 / 8
  - `2026-04-01` selected stocks match: 8 / 8

## PM Interpretation

The platform replication gap is small and explained by expected residuals:

- JoinQuant executes at `09:40`, while the local runner approximates with daily open.
- A-share hundred-share rounding creates small position-size differences.
- Cash, dividend timing, and platform accounting can drift slightly.
- Local and JoinQuant benchmark conventions differ by about 1.35 percentage points in the confirmation window.

The previous large gap was caused by a local PIT data-coverage issue: the local panel originally ended at `2026-01-05` and missed the `2026-04-01` rebalance. After extending the panel, the gap narrowed materially.

## Constraints

- The 2021-2026 window remains `platform_replication` only.
- It must not be used for tuning, factor acceptance, or strategy acceptance.
- V3 remains a formal candidate, not an accepted strategy.

## Next Gate

Move to `paper_trading`.

Forward observations must be recorded without changing:

- factor weights;
- selection count;
- value-trap guard;
- rebalance schedule;
- paper-trading interpretation rules.

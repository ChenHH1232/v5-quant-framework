# Utilities V5.1f Quant-Ready Candidate

Date: 2026-07-16

Status:

```text
formal_strategy_candidate + engineering_contract_audit_passed
```

Not status:

```text
accepted_strategy
platform_replication
```

## Rule

```text
weak demand -> high dividend
mid demand -> operating cash-flow yield
strong demand -> low PB
```

## Why It Makes Sense

Weak demand favors defensive shareholder return.

Mid demand favors cash-flow resilience.

Strong demand favors valuation recovery in asset-heavy utilities.

## Quant Evidence

```text
candidate cumulative return = 2.6761
low PB baseline = 1.9444
cash-flow baseline = 1.9209
```

Selection-count robustness passed for:

```text
8, 10, 12
```

State-conditioned RankIC is positive for all three state-factor pairs.

## Research Warning

The candidate still has failure years:

```text
2017, 2020
```

Research Agent should continue tracking these failure modes before strategy acceptance.

## Engineering Update

The strategy contract passed engineering audit. This does not mean the strategy is accepted or ready for JoinQuant code.

Engineering smoke test also passed. This means the local validation runner can reproduce the Quant result from local PIT and external-state panels.

Next possible PM gate:

```text
platform_replication_preparation
```

Accepted strategy status remains blocked.

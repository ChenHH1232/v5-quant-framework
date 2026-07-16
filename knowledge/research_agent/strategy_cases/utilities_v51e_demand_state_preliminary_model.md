# Utilities V5.1e Demand-State Preliminary Model

Date: 2026-07-16

Status:

```text
preliminary_model_candidate
```

## Core Idea

Static factor composites failed in V5.1a-d. V5.1e adds an external demand state:

```text
electricity_consumption_yoy
```

The initial model is:

```text
strong demand -> low PB
otherwise -> operating cash-flow yield
```

## Financial Interpretation

For utilities, value is state dependent.

When electricity demand is not strong, cash-flow yield better captures resilience and shareholder-return capacity.

When electricity demand is strong, low PB may better capture asset re-rating and valuation recovery.

## Evidence Snapshot

Rolling PIT cumulative return:

```text
demand-state model = 2.6883
raw low PB = 1.9444
raw cash-flow yield = 1.9209
```

Alternative state check:

```text
secondary_industry_electricity_yoy
```

also supports the direction, but suggests that mid-demand periods may prefer subindustry cash-flow. Treat this as a research lead, not as an approved complexity increase.

Coverage:

```text
38 / 38 rebalance dates have visible external state
```

## Research Warning

This is not an accepted factor model.

The model failed to beat both main baselines in several years, especially:

```text
2017, 2019, 2020, 2021
```

Research Agent should not expand the model by adding many factors. The next useful work is explaining failure states and identifying whether coal, tariff or hydrology data can improve the state definition.

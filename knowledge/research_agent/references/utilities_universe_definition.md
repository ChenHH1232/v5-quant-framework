# Utilities Universe Definition

Date: 2026-07-16

Owner:

Research Agent

Project:

```text
V5.1 Utilities Sector Process-Portability Test
```

Status:

```text
research_preparation
```

## Universe Purpose

The V5.1 universe should represent A-share utilities operating companies. The first priority is electric power operators because their business model is easier to compare than a broad public-utilities basket.

This is an industry-operating-company universe, not a high-dividend style universe.

## Initial Inclusion Rules

A company may enter the first-pass universe when:

- it is A-share listed;
- it belongs to utilities, electric power, gas, water, or related regulated public-service operation;
- its main business is operating utility assets or selling utility services;
- it has enough listing history and financial-statement coverage for PIT validation;
- it has tradable daily price and volume history;
- it is not suspended or ST at the rebalance date under the selected validation rule.

## Priority Subgroups

1. Thermal power operators.
2. Hydropower operators.
3. Nuclear power operators.
4. Integrated power operators where power generation / operation is core.
5. Gas, water, and grid operators if their economics are comparable and data coverage is adequate.

## Initial Exclusion Rules

Exclude:

- new-energy equipment manufacturers;
- wind / solar equipment suppliers;
- environmental equipment manufacturers;
- EPC / construction contractors;
- power engineering design companies;
- diversified conglomerates where utility operation is not the core business;
- broad high-dividend SOE baskets;
- companies whose main return driver is commodity trading, real estate, finance, or unrelated industrial assets.

## Mixed-Business Treatment

Mixed-business companies require a separate core-business check. A company should be included only when utility operation is the dominant source of revenue, profit, cash flow, or asset base.

If a company cannot be clearly classified, it should be tagged:

```text
universe_review_required
```

and excluded from the first formal validation sample unless PM approves a documented treatment.

## PIT Universe Rule

The formal universe must be point-in-time. A company can only be included on a rebalance date if it was listed, tradable, and identifiable as a utilities operating company using information visible at that time.

Future industry reclassification must not be used to reconstruct the past unless the runner records a conservative visible date.

## Baseline Universe

The initial baseline should be:

```text
equal-weight utilities operating universe
```

Optional baselines:

- equal-weight electric power operators only;
- low-PB utilities baseline;
- high-dividend utilities baseline.

## Acceptance Check

This universe definition passes preparation only if high-dividend SOE and utilities are not mixed.

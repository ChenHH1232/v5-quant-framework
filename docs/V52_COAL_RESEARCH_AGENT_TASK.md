# V5.2 Coal Research Agent Task Sheet

Date: 2026-07-16

Owner:

Research Agent

Project:

```text
V5.2 Coal High-Dividend / Cycle-Value Process-Portability Test
```

## Mission

Prepare a financially explainable, data-collectible, PIT-validatable research packet for A-share coal mining and coal operating companies.

The goal is not to produce a backtest result. The goal is to define a coal-sector hypothesis that can survive later Quant Validation Agent testing.

## Step 1: Define Universe Boundary

Deliverable:

```text
coal_universe_definition.md
```

Required content:

- industry definition;
- inclusion rules;
- exclusion rules;
- treatment of mixed-business companies;
- initial subgroups:
  - thermal coal;
  - coking coal;
  - integrated coal operators;
  - mixed coal-power;
  - mixed coal-chemical;
- explicit exclusion of:
  - pure coal chemical;
  - coal machinery and equipment;
  - non-coal mining;
  - broad high-dividend SOE style basket.

Acceptance check:

The universe must be an industry-operating-company universe, not a style universe.

## Step 2: Build Data Field Availability Map

Deliverable:

```text
coal_data_field_map.md
```

Required field groups:

- market data:
  - open;
  - close;
  - volume;
  - market cap;
  - tradability / suspension / ST status;
- valuation:
  - PB;
  - PE;
  - EV / EBITDA if available;
  - operating cash-flow yield;
  - free-cash-flow yield;
- dividend:
  - cash dividend;
  - dividend yield;
  - payout ratio;
  - dividend continuity;
  - dividend coverage;
- cycle profitability:
  - revenue YoY;
  - net profit YoY;
  - gross margin;
  - ROE / ROA;
  - profit volatility;
- cash flow and capex:
  - operating cash flow;
  - free cash flow;
  - capex;
  - operating cash flow / net profit;
  - dividend / free cash flow;
- leverage:
  - asset-liability ratio;
  - interest expense;
  - interest coverage;
  - debt / operating cash flow;
- external state:
  - thermal coal price;
  - coking coal price;
  - coal inventory or port inventory;
  - raw coal output;
  - coal-power spread proxy.

For each field record:

- source candidate;
- PIT visibility route;
- reporting lag;
- missing-data risk;
- required / optional / exploratory status.

## Step 3: Write Coal Value-Investing Framework

Deliverable:

```text
coal_value_investing_framework.md
```

Required sections:

- why coal can support high-dividend / value investing;
- why coal is not the same as stable utilities;
- why high dividend can be a cycle-peak trap;
- why coal price state must be separated from stock-level factors;
- why cash-flow coverage and capex matter;
- expected failure modes:
  - coal price collapse;
  - policy price controls;
  - safety / environmental production restrictions;
  - reserve depletion or capex cliff;
  - dividend cuts after peak profit;
  - coal chemical contamination;
  - parent-company restructuring or asset injection.

Core statement:

```text
The key coal question is whether current dividend and valuation signals are supported by cycle-adjusted cash generation rather than peak-cycle accounting profit.
```

## Step 4: Build Initial Factor Hypothesis List

Deliverable:

```text
coal_core_factor_hypotheses.md
```

Group hypotheses into six modules:

1. shareholder return;
2. valuation;
3. cycle profitability;
4. cash flow and capex;
5. leverage and solvency;
6. external coal-cycle state.

For each hypothesis include:

- financial intuition;
- candidate formula;
- expected direction;
- expected failure mode;
- required data;
- whether it is alpha, support, filter, state variable, or risk-control candidate.

Do not include:

- momentum-only strategies;
- complex timing before state variables are validated;
- cross-industry high-dividend SOE baskets;
- bank-specific thresholds;
- performance-based factor weights.

## Step 5: Build External State Source Register

Deliverable:

```text
coal_source_collection_plan.md
```

Required source candidates:

- JoinQuant / DataJQ industry, price, valuation, finance, dividend fields;
- National Bureau of Statistics raw coal output and production-material price releases;
- Ministry of Commerce commodity price monitoring / business forecast data;
- coal-industry association or market-index sources such as CCTD;
- exchange futures settlement prices for proxy review only;
- China Electricity Council or NDRC data for electricity tariff, coal inventory, or coal-power spread proxies;
- company annual and interim reports for coal business exposure classification.

Each source must be tagged:

```text
official
industry_association
vendor
exchange_market_proxy
manual_review
not_pit_usable_until_audited
```

## Step 6: Hand Off Validation Plan To Quant Agent

Deliverable:

```text
coal_validation_handoff.md
```

Required tests:

- PIT leakage audit;
- baseline comparison:
  - equal-weight coal;
  - high-dividend coal top N;
  - low-PB coal top N;
  - high cash-flow-yield coal top N;
  - state-conditioned baseline;
- IC / RankIC;
- rolling validation;
- ablation by factor module;
- robustness:
  - selection count;
  - state threshold perturbation;
  - mixed-company exclusion;
  - thermal / coking split;
  - rebalance date perturbation;
  - random window stress.

## Research Agent Rules

- Do not write strategy code.
- Do not run platform backtests.
- Do not tune based on 2021-2026 results.
- Do not treat external state as PIT-usable without visible-date evidence.
- Do not treat broad high-dividend SOE as a coal-sector strategy.

## Completion Signal

Research Agent finishes preparation by reporting:

```text
V5.2 coal preparation packet complete
```

Project Manager Agent then decides whether to approve:

```text
research_pit_validation
```

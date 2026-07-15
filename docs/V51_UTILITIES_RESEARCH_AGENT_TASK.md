# V5.1 Utilities Research Agent Task Sheet

Date: 2026-07-16

Owner:

Research Agent

Project:

```text
V5.1 Utilities Sector Process-Portability Test
```

## Mission

Prepare the first non-bank V5 research packet for A-share utilities operating companies, with priority on electric power operators.

The goal is not to produce a backtest result. The goal is to prepare a financially explainable, data-collectible, PIT-validatable research hypothesis.

## Step 1: Define Universe Boundary

Deliverable:

```text
utilities_universe_definition.md
```

Required content:

- industry definition;
- inclusion rules;
- exclusion rules;
- treatment of mixed-business companies;
- initial subgroups:
  - thermal power;
  - hydropower;
  - nuclear power;
  - gas / water / grid operators if appropriate;
- explicit exclusion of:
  - new-energy equipment;
  - environmental equipment;
  - EPC / construction;
  - high-dividend SOE cross-industry basket.

Acceptance check:

The universe must be an industry-operating-company universe, not a style universe.

## Step 2: Build Data Field Availability Map

Deliverable:

```text
utilities_data_field_map.md
```

Required field groups:

- market data:
  - price;
  - volume;
  - market cap;
  - tradability / suspension / ST status;
- valuation:
  - PB;
  - PE;
  - EV / EBITDA if available;
  - operating cash-flow yield;
- dividend:
  - cash dividend;
  - dividend yield;
  - payout ratio;
  - dividend continuity;
- profitability:
  - ROE;
  - gross margin;
  - operating margin;
  - ROIC if available;
- cash flow:
  - operating cash flow;
  - free cash flow;
  - capex;
  - operating cash flow / net profit;
- debt-service capacity:
  - asset-liability ratio;
  - interest expense;
  - interest coverage;
  - debt / operating cash flow.

For each field record:

- source candidate;
- PIT visibility route;
- reporting lag;
- missing-data risk;
- whether the field is required, optional, or exploratory.

## Step 3: Write Economic Logic Memorandum

Deliverable:

```text
utilities_value_investing_framework.md
```

Required sections:

- why utilities may support value / dividend investing;
- why high capex and high debt are normal;
- why low debt alone is not automatically superior;
- why cash-flow coverage matters;
- expected failure modes:
  - tariff / policy shocks;
  - fuel cost cycle;
  - capex pressure;
  - dividend cut risk;
  - parent-company asset injections or restructuring;
  - accounting profit without free cash flow.

Core statement:

```text
The key utilities question is whether stable cash flow can cover interest, capital expenditure, and dividends.
```

## Step 4: Build Initial Factor Hypothesis List

Deliverable:

```text
utilities_core_factor_hypotheses.md
```

Group hypotheses into five modules:

1. valuation;
2. dividend;
3. profitability quality;
4. cash flow;
5. debt-service capacity.

For each hypothesis include:

- financial intuition;
- candidate formula;
- expected direction;
- expected failure mode;
- required data;
- whether it is alpha, support, filter, or risk-control candidate.

Do not include:

- momentum;
- complex timing;
- industry rotation;
- bank-specific thresholds;
- performance-based factor weights.

## Step 5: Hand Off Validation Plan To Quant Agent

Deliverable:

```text
utilities_validation_handoff.md
```

Required tests:

- PIT leakage audit;
- single-factor IC / RankIC;
- baseline comparison:
  - equal-utility baseline;
  - low-PB baseline;
  - high-dividend baseline;
- ablation:
  - remove one factor module at a time;
- rolling validation;
- robustness:
  - selection count;
  - factor weight perturbation;
  - sub-industry split;
  - common-sample comparison.

## Research Agent Rules

- Do not write strategy code.
- Do not run platform backtests.
- Do not tune based on 2021-2026 results.
- Do not copy bank indicators into utilities.
- Do not treat broad high-dividend SOE as the first V5.1 test universe.

## Completion Signal

Research Agent finishes preparation by reporting:

```text
V5.1 utilities preparation packet complete
```

Project Manager Agent then decides whether to approve:

```text
research_pit_validation
```

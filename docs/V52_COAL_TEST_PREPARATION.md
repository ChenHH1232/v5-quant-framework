# V5.2 Coal High-Dividend / Cycle-Value Test Preparation

Date: 2026-07-16

Owner:

Project Manager Agent

Experiment layer:

```text
pre_research_intake
```

## Purpose

V5.2 is the second cross-industry process-portability test after the bank V3 candidate and utilities V5.1f candidate.

The goal is not to immediately produce a stronger backtest than V5.1f. The goal is to test whether V5 can handle a stronger cyclical value industry where the same high-dividend signal may mean either:

```text
shareholder-return discipline
```

or:

```text
late-cycle value trap
```

## Sector Boundary

First V5.2 test sector:

```text
A-share coal mining and coal operating companies
```

Include initially:

- coal mining;
- coal washing;
- integrated coal operators where coal mining is the dominant economic exposure;
- thermal coal producers;
- coking coal producers.

Exclude initially:

- pure coal chemical companies;
- coal machinery and mining equipment;
- non-coal mining;
- broad high-dividend SOE baskets;
- diversified companies where coal is not the core profit driver.

Mixed companies must be tagged as:

```text
core_coal
mixed_coal_chemical
mixed_power_coal
exclude_non_core
```

and must be tested with an exclusion robustness run.

## Required External State

V5.2 cannot promote a formal strategy candidate without PIT-usable external coal-cycle state variables:

- thermal coal price;
- coking coal price;
- coal inventory or port inventory;
- raw coal output / production;
- coal-power spread or coal-electricity margin proxy.

Each state row must carry:

- `state_date`;
- `visible_date`;
- `source_publication_date`;
- `source_name`;
- `source_url`;
- `pit_usable`.

## Core Questions

V5.2 should answer four questions:

1. Can the V5 research workflow run on a commodity-cycle industry?
2. Can dividend and valuation factors remain useful after controlling for cycle state?
3. Can external coal-cycle state be collected with auditable visible dates?
4. Does the process reject overfit cycle timing rules when evidence is unstable?

## Initial Research Boundary

| Item | Initial Setting |
| --- | --- |
| Stock universe | A-share coal mining and coal operating companies |
| Sample requirements | listing age, liquidity, PIT industry membership, financial-statement coverage, dividend coverage |
| Candidate logic | dividend yield, PB / PE, coal-price state, profit cycle, cash flow, capex, leverage |
| Required external state | thermal coal, coking coal, inventory/output, coal-power spread |
| Excluded in Test-1 | momentum-only strategies, cross-industry SOE high-dividend baskets, non-coal mining, coal machinery |
| Validation method | PIT -> baseline -> IC / RankIC -> rolling -> ablation -> robustness |
| Platform backtest | only after research candidate is frozen |
| Success standard | stable process, clear coal economics, no overfitting; not required to beat V5.1f |

## Candidate Factor Modules

### 1. Shareholder Return

Candidate fields:

- dividend yield;
- payout ratio;
- dividend continuity;
- dividend coverage by operating cash flow and free cash flow.

Interpretation:

High dividend can be attractive when cash generation is durable. In coal, high yield can also appear near a profit-cycle peak, so dividend must be tested with cycle-state controls.

### 2. Valuation

Candidate fields:

- PB;
- PE;
- EV / EBITDA if available;
- operating cash-flow yield;
- free-cash-flow yield.

Interpretation:

Coal assets can look cheap when the market discounts future coal-price weakness. Low valuation is not sufficient unless current profitability and cash flow can survive a weaker coal-price state.

### 3. Cycle Profitability

Candidate fields:

- revenue / net profit YoY;
- gross margin;
- ROE / ROA;
- profit volatility;
- coal-price sensitivity.

Interpretation:

Profitability should be interpreted as cyclical state evidence, not as a simple higher-is-better quality score.

### 4. Cash Flow And Capex

Candidate fields:

- operating cash flow;
- free cash flow;
- capex intensity;
- operating cash flow / net profit;
- dividend / free cash flow.

Interpretation:

The key question is whether current cash flow can cover maintenance capex, safety/environmental spending, debt service, and dividends across the coal cycle.

### 5. Leverage And Solvency

Candidate fields:

- asset-liability ratio;
- interest coverage;
- debt / operating cash flow;
- short-term debt pressure.

Interpretation:

Coal companies may carry different debt levels depending on mine assets and parent-company structure. Leverage is initially a risk-control or value-trap guard candidate, not an approved alpha factor.

### 6. External Cycle State

Candidate fields:

- thermal coal price state;
- coking coal price state;
- coal inventory or port inventory;
- raw coal output;
- coal-power spread proxy.

Interpretation:

External state is used to avoid treating all high dividend and low valuation signals as identical across cycle regimes.

## Test-1 Gate

Project Manager Agent may approve formal V5.2 Test-1 only after these preparation outputs exist:

- coal universe definition;
- data field availability map;
- coal value-investing framework;
- initial factor hypothesis list;
- external state source register;
- validation handoff plan;
- explicit statement that 2021-2026 platform windows are not used for tuning.

## PM Decision

V5.2 preparation may start now.

Formal Test-1 is not approved yet.

The next step is Research Agent preparation and Quant Validation Agent data-contract review, not Engineering Agent strategy code.

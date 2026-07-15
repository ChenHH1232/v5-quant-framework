# V5.1 Utilities Sector Test Preparation

Date: 2026-07-16

Owner:

Project Manager Agent

Experiment layer:

```text
pre_research_intake
```

## Purpose

V5.1 is the first cross-industry process portability test after the bank-sector V3 candidate reached:

```text
formal_strategy_candidate + platform_replication_passed
```

The goal is not to immediately create a second profitable strategy. The goal is to test whether the V5 research process can leave bank-specific indicators and still run through:

```text
Research -> PIT data -> Quant validation -> Candidate governance -> Engineering replication
```

## Sector Boundary

First V5.1 test sector:

```text
A-share utilities operating companies, with priority on electric power operators.
```

Include initially:

- thermal power operators;
- hydropower operators;
- nuclear power operators;
- grid / gas / water operators if they share regulated-utility economics and data coverage.

Exclude initially:

- new-energy equipment manufacturers;
- environmental equipment manufacturers;
- engineering / EPC contractors;
- diversified conglomerates where utility operation is not the core business;
- broad "high-dividend SOE" baskets.

Reason:

Utilities is an industry boundary with relatively coherent business economics. High-dividend SOE is a cross-industry style basket and would mix utilities, coal, energy, telecom, transportation, and other cyclicals. That would make it harder to know whether V5 is testing industry logic or style exposure.

## Core Questions

V5.1 should answer three questions:

1. Can the V5 research workflow run without bank-specific indicators?
2. Can PIT data, rolling validation, ablation, baseline comparison, and platform replication standards be reused?
3. Do any retained factors have utilities-sector economic logic rather than accidental historical significance?

## Initial Research Boundary

| Item | Initial Setting |
| --- | --- |
| Stock universe | Utilities operating companies, priority electric power |
| Sample requirements | listing age, liquidity, financial-statement coverage, dividend-data coverage |
| Candidate logic | valuation, dividend, cash flow, earnings stability, debt-service pressure |
| Excluded in Test-1 | momentum, complex timing, sector rotation, bank defensive thresholds |
| Validation method | PIT -> single factor -> baseline -> ablation -> rolling |
| Platform backtest | only after research candidate is frozen |
| Success standard | workflow portability and stable conclusion, not beating the bank strategy |

## Candidate Factor Modules

### 1. Valuation

Candidate fields:

- PB;
- PE;
- EV / EBITDA;
- operating cash-flow yield;
- free-cash-flow yield where capex data is reliable.

Economic interpretation:

Utilities often have regulated or quasi-regulated assets. Valuation factors should test whether the market over-discounts stable assets or future cash flows.

### 2. Dividend

Candidate fields:

- dividend yield;
- payout ratio;
- consecutive dividend record;
- dividend volatility;
- dividend coverage by operating cash flow.

Economic interpretation:

Dividend yield is meaningful only when cash generation can support it. High yield without cash-flow support may indicate a value trap.

### 3. Profitability Quality

Candidate fields:

- ROE;
- gross margin;
- operating margin;
- earnings volatility;
- return on invested capital when available.

Economic interpretation:

Stable profitability is more important than short-term profit spikes. For regulated utilities, extreme profitability can also be temporary or policy-sensitive.

### 4. Cash Flow

Candidate fields:

- operating cash flow;
- free cash flow;
- operating cash flow / net profit;
- operating cash flow / revenue;
- capex intensity.

Economic interpretation:

Utilities are capital-intensive. A useful factor must distinguish stable cash-flow generation from accounting earnings that cannot fund capex, debt service, and dividends.

### 5. Debt-Service Capacity

Candidate fields:

- asset-liability ratio;
- interest coverage ratio;
- debt / operating cash flow;
- cash flow after interest and capex;
- short-term debt pressure.

Economic interpretation:

Utilities naturally carry high debt because assets are capital-intensive and cash flows are relatively stable. Low debt should not be treated as automatically superior. The more relevant question is:

```text
Can stable cash flow cover interest, capital expenditure, and dividends?
```

## Test-1 Gate

Project Manager Agent may approve formal V5.1 Test-1 only after these preparation outputs exist:

- utilities universe definition;
- data field availability map;
- utilities economic logic memorandum;
- initial factor hypothesis list;
- validation plan with baseline, ablation, rolling, and robustness checks;
- explicit statement that 2021-2026 platform windows are not used for tuning.

## PM Decision

V5.1 preparation may start now.

Formal Test-1 is not approved yet.

The next step is Research Agent preparation, not Engineering Agent platform backtest.

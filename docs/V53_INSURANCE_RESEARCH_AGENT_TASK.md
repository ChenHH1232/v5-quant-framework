# V5.3 Insurance Research Agent Task Sheet

Date: 2026-07-16

Owner:

Research Agent

Project:

```text
V5.3 Insurance Value / Quality Process-Portability Test
```

## Mission

Prepare a financially explainable and PIT-validatable research packet for A-share listed insurance companies.

The goal is to define insurance-sector hypotheses that Quant Validation Agent can test. The goal is not to write strategy code or produce a backtest.

## Step 1: Define Universe Boundary

Deliverable:

```text
insurance_universe_definition.md
```

Required content:

- industry definition;
- inclusion rules;
- exclusion rules;
- life insurance vs P&C insurance vs insurance group treatment;
- treatment of insurance-led holdings;
- explicit exclusion of banks, brokers, asset managers and non-insurance financial holdings.

Acceptance check:

The universe must be an insurance operating-company universe, not a generic financial-sector basket.

## Step 2: Build Data Field Availability Map

Deliverable:

```text
insurance_data_field_map.md
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
  - P/EV if embedded value is available;
  - market cap / net assets;
  - dividend yield;
- insurance operating quality:
  - premium income growth;
  - new business value growth if available;
  - embedded value growth if available;
  - combined ratio for P&C insurers;
  - claim ratio and expense ratio if available;
  - surrender rate / persistency if available;
- investment quality:
  - investment yield;
  - total investment income;
  - equity-market sensitivity;
  - bond-yield sensitivity;
- solvency and balance sheet:
  - comprehensive solvency adequacy ratio;
  - core solvency adequacy ratio;
  - leverage / liability reserve quality;
  - asset impairment or credit-risk exposure;
- shareholder return:
  - cash dividend;
  - payout ratio;
  - dividend continuity;
- external state:
  - 10Y government bond yield;
  - yield-curve slope;
  - equity index state;
  - credit spread or bond-market risk proxy;
  - insurance premium industry growth if available.

For each field record:

- source candidate;
- PIT visibility route;
- reporting lag;
- missing-data risk;
- required / optional / exploratory status.

## Step 3: Write Insurance Value / Quality Framework

Deliverable:

```text
insurance_value_quality_framework.md
```

Required sections:

- why insurance can support value investing;
- why insurance is different from banks;
- life insurance economics:
  - embedded value;
  - new business value;
  - liability duration;
  - interest-rate sensitivity;
- P&C insurance economics:
  - combined ratio;
  - underwriting cycle;
  - catastrophe / claim risk;
- why low PB / low PE can be a value trap;
- why solvency and investment income must be separated from operating quality;
- expected failure modes:
  - falling long-term rates;
  - weak new business value;
  - equity-market drawdown;
  - claim-ratio deterioration;
  - solvency pressure;
  - accounting profit inflated by investment gains.

Core statement:

```text
The key insurance question is whether low valuation is supported by durable insurance franchise quality, solvency strength and rate-state-adjusted investment returns.
```

## Step 4: Build Initial Factor Hypothesis List

Deliverable:

```text
insurance_core_factor_hypotheses.md
```

Group hypotheses into six modules:

1. valuation;
2. insurance franchise growth;
3. underwriting / operating quality;
4. investment quality and rate sensitivity;
5. solvency and balance-sheet strength;
6. shareholder return.

For each hypothesis include:

- financial intuition;
- candidate formula;
- expected direction;
- expected failure mode;
- required data;
- whether it is alpha, support, filter, state variable, or risk-control candidate.

Do not include:

- bank-specific factor thresholds;
- broker-style trading-volume factors;
- performance-based factor weights;
- platform-window tuning.

## Step 5: Build Source Collection Plan

Deliverable:

```text
insurance_source_collection_plan.md
```

Required source candidates:

- JoinQuant / DataJQ price, valuation, dividend and finance fields;
- company annual and interim reports;
- company solvency reports;
- National Financial Regulatory Administration / former CBIRC statistics where available;
- exchange announcements;
- Eastmoney F10 / company pages as first-pass structured source only;
- Tushare announcement links for report-date cross-checking;
- bond-yield and equity-index data for external state.

Each source must be tagged:

```text
official
company_disclosure
vendor
market_proxy
manual_review
not_pit_usable_until_audited
```

## Step 6: Hand Off Validation Plan To Quant Agent

Deliverable:

```text
insurance_validation_handoff.md
```

Required tests:

- PIT leakage audit;
- baseline comparison:
  - equal-weight insurance;
  - low-PB insurance top N;
  - high-dividend insurance top N;
  - high-solvency-quality top N if data exists;
  - embedded-value discount top N if data exists;
- IC / RankIC;
- rolling validation;
- ablation by factor module;
- robustness:
  - selection count;
  - report-date lag;
  - life vs P&C split;
  - rate-state buckets;
  - equity-market state buckets;
  - rebalance date perturbation;
  - random window stress.

## Research Agent Rules

- Do not write strategy code.
- Do not run platform backtests.
- Do not tune based on 2021-2026 results.
- Do not treat Eastmoney or vendor fields as PIT-usable until report-date visibility is audited.
- Do not mix insurance with banks or brokers unless a separate financial-sector strategy is approved.

## Completion Signal

Research Agent finishes preparation by reporting:

```text
V5.3 insurance preparation packet complete
```

Project Manager Agent then decides whether to approve:

```text
research_pit_validation
```


# Bank Stock Core Factor Hypothesis List

## Type

Hypothesis List

## Summary

This card converts bank value-investing logic into testable factor hypotheses. Each hypothesis must be validated separately before being used in a composite strategy.

## Hypotheses

### 1. Low P/B With Quality Support

Hypothesis:

Banks with low price-to-book outperform only when asset quality and capital adequacy are not deteriorating.

Candidate factors:

- low `pb_ratio`;
- low `pb_ratio` interacted with acceptable NPL/provision/capital scores;
- valuation discount relative to bank universe median.

Expected evidence:

- positive RankIC for valuation after excluding weak quality names;
- top-minus-bottom spread improves after value-trap guard.

Failure mode:

- low P/B selects structurally impaired banks.

### 2. Sustainable Dividend Yield

Hypothesis:

High dividend yield predicts better future returns when dividends are supported by profitability and capital adequacy.

Candidate factors:

- trailing announced dividend yield;
- dividend payout stability;
- dividend yield adjusted by capital adequacy;
- dividend yield adjusted by ROE stability.

Expected evidence:

- positive RankIC for dividend yield;
- high-yield group does not show worsening capital ratio or ROE collapse.

Failure mode:

- high yield is caused by price decline before dividend cuts.

### 3. ROE Quality

Hypothesis:

Banks with stronger and more stable ROE deserve higher valuation and may generate better shareholder returns.

Candidate factors:

- ROE TTM;
- ROE stability over 3 to 5 years;
- ROE minus estimated cost of equity;
- ROE adjusted by leverage or risk-weighted asset growth.

Expected evidence:

- positive IC for ROE or ROE stability;
- ROE helps distinguish cheap good banks from cheap impaired banks.

Failure mode:

- high ROE comes from excessive leverage, under-provisioning, or short-term credit expansion.

### 4. Asset Quality Improvement

Hypothesis:

Improving asset quality is more informative than absolute low NPL because markets may reward inflection points.

Candidate factors:

- NPL ratio change;
- special mention loan ratio change;
- overdue loan ratio change;
- credit cost change;
- provision coverage change.

Expected evidence:

- deterioration-speed factors predict underperformance;
- improvement factors work especially after sector stress.

Failure mode:

- reported asset quality lags true credit risk.

### 5. Provision Buffer

Hypothesis:

Higher provision coverage protects book value during credit stress and reduces value-trap risk.

Candidate factors:

- provision coverage ratio;
- provision-to-loan ratio;
- provision coverage relative to NPL trend;
- credit cost buffer.

Expected evidence:

- provision strength improves drawdown behavior;
- value strategy performs better when low-PB names with weak provisions are excluded.

Failure mode:

- high provision coverage reflects backward-looking accounting rather than future resilience.

### 6. Capital Adequacy

Hypothesis:

Banks with stronger core tier 1 capital adequacy can absorb losses and sustain dividends better.

Candidate factors:

- core tier 1 capital adequacy ratio;
- capital adequacy trend;
- capital surplus over regulatory minimum;
- risk-weighted asset growth versus capital growth.

Expected evidence:

- capital factor reduces downside or value-trap exposure;
- stronger capital supports dividend and ROE sustainability.

Failure mode:

- capital factor has weak standalone IC because market prices it slowly or only during stress.

### 7. Funding Advantage

Hypothesis:

Banks with stable low-cost deposits have more resilient net interest margins and franchise value.

Candidate factors:

- demand deposit ratio;
- deposit growth;
- deposit cost;
- loan-to-deposit ratio;
- interbank funding reliance.

Expected evidence:

- funding-quality factors help during rate and liquidity stress;
- funding advantage explains valuation premium.

Failure mode:

- data availability is poor or disclosure frequency is too low.

## Required Validation

- factor IC and RankIC;
- top-minus-bottom group spread;
- rolling fold stability;
- common-sample comparison;
- leave-one-factor-out for composite strategy;
- stress periods such as credit tightening, real estate downturn, and rate-cycle shifts.

## Last Updated

2026-07-15

# Bank Stock Core Factor Hypothesis List

## Type

Citation-Backed Hypothesis List

## Summary

This card converts bank value-investing logic into testable factor hypotheses. Each hypothesis must be validated separately before being used in a composite strategy.

Evidence level: mostly `hypothesis_only`. Supporting references explain financial plausibility and variable definitions; they do not accept any V5 factor. See [Bank Sector Research References](../references/bank_sector_references.md).

## Hypotheses

### 1. Low P/B With Quality Support

Hypothesis:

Banks with low price-to-book outperform only when asset quality and capital adequacy are not deteriorating.

Evidence trail:

- `academic_evidence`: book-to-market/value-factor literature supports valuation as a general equity factor.
- `academic_evidence`: financial-services valuation literature supports book equity and ROE as central bank valuation inputs.
- `regulatory_definition`: NPL, provision and capital variables define balance-sheet quality.
- `hypothesis_only`: the interaction between low P/B and bank quality must be validated in V5.

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

Evidence trail:

- `industry_disclosure`: listed-bank profit distribution plans and annual reports define cash dividends and payout ratio.
- `regulatory_definition`: capital adequacy constrains dividend capacity.
- `hypothesis_only`: high dividend yield conditioned on profitability and capital adequacy may outperform.

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

Evidence trail:

- `academic_evidence`: profitability literature supports profitability as distinct from valuation in equity returns.
- `academic_evidence`: bank valuation links P/B, ROE and cost of equity.
- `hypothesis_only`: ROE stability, ROE minus cost of equity, and leverage-adjusted ROE require V5 validation.

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

Evidence trail:

- `regulatory_definition`: NPL, special mention loans, overdue loans, provisions and credit cost are bank risk indicators.
- `industry_disclosure`: listed banks disclose these indicators at annual/interim frequency.
- `hypothesis_only`: deterioration speed or improvement inflection may predict returns.

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

Evidence trail:

- `regulatory_definition`: provision coverage and loan-loss reserve ratios are supervisory/accounting resilience indicators.
- `hypothesis_only`: higher provision buffer improves future stock returns or drawdown control.

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

Evidence trail:

- `regulatory_definition`: Basel and NFRA define capital adequacy and risk-weighted asset concepts.
- `hypothesis_only`: capital strength reduces downside or improves value-factor quality in V5.

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

Evidence trail:

- `academic_evidence`: deposit-franchise research supports the economic value of stable, low-beta deposits.
- `industry_disclosure`: listed banks disclose deposit structure and funding-cost indicators, but frequency and consistency vary.
- `hypothesis_only`: deposit and funding variables improve China bank-stock selection.

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

Do not use 2021-05 to 2026-05 as a tuning or acceptance sample. It is only for platform-confirmation and local-vs-JoinQuant comparison.

## Claims Downgraded To `hypothesis_only`

- Low P/B works only with quality support.
- Dividend yield predicts returns after capital/profitability conditioning.
- ROE stability improves shareholder returns.
- Asset-quality improvement is more predictive than level.
- Provision buffer reduces value-trap risk.
- Capital adequacy improves downside control.
- Funding advantage improves NIM resilience and valuation premium.

## Research Agent Usage Notes

- Use this card to propose factor families and experiment designs.
- Every candidate factor must specify point-in-time availability, disclosure lag, missing-data treatment and expected economic mechanism.
- Research Agent must not tune weights, thresholds or signs based on backtest performance.
- Quant Validation Agent must run rolling IC/RankIC, baseline, ablation, robustness and common-sample checks before Engineering Agent implements production logic.

## References

- [Bank Sector Research References](../references/bank_sector_references.md)

## Last Updated

2026-07-15

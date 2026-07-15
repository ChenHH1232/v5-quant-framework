# Bank Stock Value Investing Framework

## Type

Citation-Backed Research Framework

## Summary

Bank stock value investing should be built around valuation discipline, balance-sheet quality, sustainable profitability, capital adequacy, dividend capacity, and funding quality. Low valuation alone is not enough because banks can look cheap when the market is pricing credit losses, capital pressure, weak franchise quality, or future book-value impairment.

Evidence level: mixed `academic_evidence`, `regulatory_definition`, `industry_disclosure`, `V5_internal_finding`, and `hypothesis_only`. See [Bank Sector Research References](../references/bank_sector_references.md).

## Core Economic Logic

Banks are leveraged balance-sheet businesses. Their equity value is shaped by:

- asset quality;
- net interest margin;
- loan growth quality;
- deposit stability and funding cost;
- fee and non-interest income resilience;
- provision and credit-cost cycle;
- regulatory capital adequacy;
- dividend capacity;
- valuation relative to book equity.

For banks and other financial firms, book equity, ROE, and cost of equity are often more central to valuation than industrial-company operating-asset metrics. This is supported by financial-services valuation literature and by the balance-sheet nature of banking. Evidence level: `academic_evidence`.

However, book value can still be overstated if asset quality deteriorates faster than provisions recognize losses, if risk-weighted assets grow faster than capital, or if reported asset quality lags the credit cycle. Evidence level: `regulatory_definition` for the ratio definitions; `hypothesis_only` for predictive use in V5.

## Value Investing Question

Is the bank cheap because the market is too pessimistic, or cheap because future book value and profitability are impaired?

## Key Research Dimensions

### Valuation

- price-to-book;
- price-to-earnings;
- dividend yield;
- market implied cost of equity.

Evidence level: `academic_evidence` for general value/profitability framing; `hypothesis_only` for bank-sector predictive ranking in V5 until rolling validation confirms it.

### Profitability

- ROE;
- ROA;
- net interest margin;
- fee income ratio;
- cost-income ratio.

Evidence level: `industry_disclosure` for definitions from listed-bank reports; `hypothesis_only` for return prediction.

### Asset Quality

- non-performing loan ratio;
- special mention loan ratio;
- overdue loan ratio;
- credit cost;
- provision coverage ratio;
- loan loss reserve ratio.

Evidence level: `regulatory_definition` for ratio meaning; `hypothesis_only` for whether level, change, or acceleration predicts bank-stock returns.

### Capital Strength

- core tier 1 capital adequacy ratio;
- tier 1 capital adequacy ratio;
- total capital adequacy ratio;
- risk-weighted asset growth.

Evidence level: `regulatory_definition`. Capital strength is a balance-sheet resilience condition; its standalone return-predictive value requires Quant Validation.

### Funding Quality

- deposit growth;
- demand deposit ratio;
- loan-to-deposit ratio;
- interbank liability reliance;
- funding cost.

Evidence level: `academic_evidence` for deposit-franchise logic; `industry_disclosure` for reported variables; `hypothesis_only` for China A-share factor use.

## Candidate Strategy Logic

A bank value strategy should prefer banks that are:

- cheap on P/B or dividend yield;
- not showing rapid credit deterioration;
- profitable enough to sustain ROE above cost of equity;
- sufficiently capitalized;
- able to maintain dividends without consuming regulatory capital.

Evidence level: `hypothesis_only` until tested through common-sample IC, rolling validation, ablation, baseline comparison and robustness checks.

## Data Requirements

- point-in-time daily market and valuation data;
- announcement-date aligned financial statements;
- bank-specific indicators from annual/interim reports or reconstructed sources;
- dividend records with announcement, ex-date, and payment date;
- bank-sector benchmark for market state.

Evidence level: `V5_internal_finding` for point-in-time and platform-alignment requirements.

## Rejection Criteria

Reject a bank value factor or strategy if:

- low valuation mainly selects banks with worsening asset quality;
- returns disappear after controlling for asset quality;
- performance is concentrated in one credit or policy cycle;
- dividend yield is high only because price collapsed before dividend cuts;
- factor evidence fails rolling or common-sample tests.

## Implications For V5

Research Agent should not propose bank value strategies as low-PB screens only. Every valuation signal needs a balance-sheet quality check and a capital/dividend sustainability interpretation.

Historical performance alone is never sufficient evidence for accepting a strategy. The 2021-05 to 2026-05 window is platform-confirmation only and must not be used as a tuning or acceptance sample. Evidence level: `V5_internal_finding`.

## Research Agent Usage Notes

- Use this card to frame bank-sector investment hypotheses before coding.
- Do not convert the framework directly into a portfolio rule.
- Treat all stock-selection claims as `hypothesis_only` until Quant Validation Agent verifies them.
- Use regulatory and disclosure sources to define variables, not to claim alpha.

## References

- [Bank Sector Research References](../references/bank_sector_references.md)
- Basel Committee / BIS capital framework.
- NFRA Commercial Bank Capital Management Measures.
- Fama-French value-factor literature.
- Damodaran financial-services valuation materials.
- Listed Chinese bank annual/interim reports and dividend announcements.
- V5 leakage audit and platform-confirmation governance documents.

## Last Updated

2026-07-15

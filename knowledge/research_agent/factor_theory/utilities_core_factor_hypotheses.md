# Utilities Core Factor Hypotheses

Date: 2026-07-16

Owner:

Research Agent

Project:

```text
V5.1 Utilities Sector Process-Portability Test
```

Status:

```text
hypothesis_list_not_validated
```

## Rules

These hypotheses are candidates only. They are not accepted factors.

Do not tune factor weights with 2021-2026 platform replication results.

## Module 1: Valuation

### H1: Low PB Within Utilities

- Financial intuition: stable infrastructure assets may be mispriced when the market over-discounts regulated returns.
- Candidate formula: negative rank of PB.
- Expected direction: lower PB may predict higher future relative return.
- Failure mode: low PB may reflect stranded assets, tariff pressure, poor asset quality, or weak governance.
- Required data: daily PB with PIT book-value visibility.
- Role: alpha candidate.

### H2: Operating Cash-Flow Yield

- Financial intuition: operating cash generation relative to market value may be more relevant than accounting earnings.
- Candidate formula: trailing visible OCF / market cap.
- Expected direction: higher OCF yield may predict higher future relative return.
- Failure mode: temporary working-capital inflows can inflate OCF.
- Required data: OCF, market cap, statement pubDate.
- Role: alpha / support candidate.

### H3: Free-Cash-Flow Yield

- Financial intuition: cash left after capex is closer to distributable value.
- Candidate formula: visible FCF / market cap.
- Expected direction: higher FCF yield may be positive.
- Failure mode: expansion-heavy utilities may have negative FCF while creating long-term value.
- Required data: OCF, capex, market cap.
- Role: support candidate.

## Module 2: Dividend

### H4: Sustainable Dividend Yield

- Financial intuition: dividend yield matters only when dividend cash outflow is covered by operating cash flow.
- Candidate formula: dividend yield adjusted by OCF dividend coverage.
- Expected direction: higher covered yield may be positive.
- Failure mode: future dividend cuts, one-off dividends, or delayed payment-date treatment.
- Required data: visible dividend record, price, OCF.
- Role: alpha / filter candidate.

### H5: Dividend Continuity

- Financial intuition: stable dividends may identify companies with predictable cash generation and shareholder-return discipline.
- Candidate formula: count or ratio of visible dividend-paying years in a trailing window.
- Expected direction: higher continuity may be positive.
- Failure mode: mature low-growth firms may underperform if valuation is too high.
- Required data: historical dividend records with visible dates.
- Role: support candidate.

## Module 3: Profitability Quality

### H6: Stable ROE

- Financial intuition: stable profitability may be more useful than one-year profit spikes.
- Candidate formula: trailing visible ROE minus ROE volatility penalty.
- Expected direction: higher stable ROE may be positive.
- Failure mode: ROE may be inflated by leverage.
- Required data: ROE with statement pubDate, rolling history.
- Role: support candidate.

### H7: Operating Margin Stability

- Financial intuition: operating margin stability may distinguish regulated or resilient operators from fuel-cost-sensitive operators.
- Candidate formula: operating margin rank minus volatility rank.
- Expected direction: higher and more stable margin may be positive.
- Failure mode: different sub-industries have structurally different margins.
- Required data: operating revenue, operating profit.
- Role: support / subgroup candidate.

## Module 4: Cash Flow

### H8: OCF / Net Profit Quality

- Financial intuition: earnings backed by cash flow are less likely to be accounting-only profits.
- Candidate formula: OCF / net profit with clipping for negative or extreme values.
- Expected direction: higher ratio may be positive when net profit is positive.
- Failure mode: seasonal cash-flow patterns and working-capital swings.
- Required data: OCF, net profit.
- Role: filter / support candidate.

### H9: Capex Burden

- Financial intuition: excessive capex burden can pressure dividends and free cash flow.
- Candidate formula: capex / OCF or capex / revenue.
- Expected direction: moderate burden may be better than extreme burden.
- Failure mode: high capex may be investment phase rather than deterioration.
- Required data: capex, OCF, revenue.
- Role: risk-control candidate.

## Module 5: Debt-Service Capacity

### H10: Interest Coverage

- Financial intuition: stable cash flow should cover interest expense.
- Candidate formula: EBIT / interest expense or OCF / interest expense.
- Expected direction: higher coverage may reduce downside risk.
- Failure mode: missing or low interest expense can distort ratios.
- Required data: EBIT, OCF, interest expense.
- Role: filter / risk-control candidate.

### H11: Debt / OCF Pressure

- Financial intuition: debt load should be evaluated against cash-generation capacity.
- Candidate formula: interest-bearing debt / OCF.
- Expected direction: lower pressure may be better, but not necessarily linearly.
- Failure mode: naturally levered operators may be wrongly penalized.
- Required data: debt, OCF.
- Role: risk-control candidate.

## Initial Composite Concept

The first composite should remain simple:

```text
utilities_value_quality_score = valuation_score + dividend_sustainability_score + cash_flow_support_score - debt_service_pressure_penalty
```

The exact weights must not be finalized until Quant Validation Agent completes PIT validation, baseline comparison, ablation, rolling validation, and robustness checks.

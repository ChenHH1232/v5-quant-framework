# Insurance Core Factor Hypotheses

Date: 2026-07-16

Project:

```text
V5.3 Insurance Value / Quality Process-Portability Test
```

Status:

```text
research_hypothesis_only
```

## Module 1: Valuation

| Hypothesis | Candidate formula | Direction | Role |
| --- | --- | --- | --- |
| Low PB may capture undervalued insurance balance-sheet franchise | price_to_book | lower is better | alpha candidate |
| Low PE may capture underpriced earnings, but can be distorted by investment gains | price_to_earnings | lower is better after quality filter | support |
| Low P/EV may capture embedded-value discount if EV is PIT-audited | market_cap / embedded_value | lower is better | alpha candidate |

## Module 2: Franchise Growth

| Hypothesis | Candidate formula | Direction | Role |
| --- | --- | --- | --- |
| Premium growth indicates franchise momentum | premium_income_yoy | higher is better | support |
| Embedded value growth indicates durable life-insurance value creation | embedded_value_yoy | higher is better | alpha candidate |
| New business value growth indicates future franchise quality | new_business_value_yoy | higher is better | alpha candidate |

## Module 3: Underwriting / Operating Quality

| Hypothesis | Candidate formula | Direction | Role |
| --- | --- | --- | --- |
| P&C combined ratio discipline supports durable profit | combined_ratio | lower is better | alpha / filter |
| Claim ratio deterioration signals underwriting weakness | claim_ratio_yoy or claim_ratio | lower is better | risk filter |
| Expense control supports operating efficiency | expense_ratio | lower is better | support |

## Module 4: Investment Quality And Rate Sensitivity

| Hypothesis | Candidate formula | Direction | Role |
| --- | --- | --- | --- |
| Investment yield supports insurance earnings | investment_yield | higher is better if not risk-seeking | support |
| Long-rate state changes valuation reliability | 10Y government bond yield / change | state dependent | state variable |
| Equity-market state affects investment income and capital | index trend / drawdown | state dependent | state variable |

## Module 5: Solvency And Balance-Sheet Strength

| Hypothesis | Candidate formula | Direction | Role |
| --- | --- | --- | --- |
| Comprehensive solvency adequacy supports dividend and growth | comprehensive_solvency_ratio | higher is better | filter |
| Core solvency adequacy is a stricter capital-quality measure | core_solvency_ratio | higher is better | filter |
| Asset impairment risk weakens reported value | impairment / assets | lower is better | risk filter |

## Module 6: Shareholder Return

| Hypothesis | Candidate formula | Direction | Role |
| --- | --- | --- | --- |
| Dividend yield may support value if solvency and operating quality are sound | dividend_yield | higher is better after filters | support |
| Stable payout indicates shareholder-return discipline | consecutive_dividend_years / payout stability | higher is better | support |
| Excessive payout under weak solvency is a value trap | payout_ratio with solvency state | moderate is better | risk filter |

## Validation Notes

Quant Validation Agent must test factors separately for:

- life insurers;
- P&C insurers;
- insurance groups;
- all-insurance combined universe.

Rate-state and equity-market-state buckets are required before any promotion.


# Oil / Gas OCF-Led Value Hypothesis V5.8b

Date: 2026-07-20

Owner:

```text
Research Agent
```

Status:

```text
research_hypothesis_ready_for_quant_validation
```

## Why V5.8a Returned To Research

V5.8a repaired the oil / gas data gate and completed Test-1. The important finding was not that the first composite worked. It did not.

Observed Test-1 evidence:

```text
OCF-only baseline > composite > equal-weight pool
dividend-only baseline was weak
FCF had only diagnostic evidence
low-vol had useful RankIC but weak return spread
2026 remained unresolved
```

Research interpretation:

```text
For oil / gas, the first durable economic signal is operating cash generation, not headline dividend or raw FCF.
```

## V5.8b Core Hypothesis

Hypothesis:

```text
In oil / gas and related distribution/refining candidates, operating cash-flow yield identifies companies whose current market value is supported by real cash generation. Low-volatility should improve deployability by avoiding unstable cyclicality, while valuation factors provide discipline. Dividend yield and FCF remain support / diagnostic variables until dividend cash events and capex-cycle meaning are reviewed.
```

## Factor Roles

| Factor | V5.8b Role | Reason |
| --- | --- | --- |
| `operating_cash_flow_yield` | primary | strongest V5.8a signal and economically interpretable |
| `low_vol_score` | support / risk control | helps align with dividend-low-vol basket objective |
| `low_price_to_book` | valuation discipline | mild evidence, but not primary |
| `pe_ratio` | valuation discipline | useful but cyclical earnings must be reviewed |
| `dividend_yield` | diagnostic / shareholder-return support | weak standalone evidence in V5.8a |
| `free_cash_flow_yield` | diagnostic only | capex can be reserve replacement, expansion or policy-driven investment |
| `capex_burden` | diagnostic only | not stable as a positive guard in V5.8a |

## What Quant Should Test

Quant Agent should test:

1. OCF-only baseline.
2. Low-vol-only baseline.
3. OCF after low-vol top-half filter.
4. OCF plus valuation discipline.
5. OCF-led composite with low-vol support.
6. Robustness across selection counts.
7. 2022, 2024 and 2026 failure modes.

## What Quant Must Not Do

Do not:

```text
optimize weights from 2021-2026 returns
promote the strongest historical line directly
turn FCF into a primary factor
use dividend yield as the main line before cash dividend events are reviewed
send to Engineering Agent before PM approval
```

## Quant Handoff Condition

V5.8b can enter research PIT validation because:

```text
PIT universe exists
preliminary cycle-state proxy exists
business-exposure PIT proxy exists
low-vol panel exists
V5.8b hypothesis is defined before running validation
```

Promotion after validation still requires:

```text
official / reviewed oil, gas, spread and tariff state data
annual-report business-exposure source repair
cash dividend event repair
2026 failure explanation
```

Historical performance alone is never sufficient evidence for accepting a strategy.

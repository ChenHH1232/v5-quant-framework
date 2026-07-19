# Gas / Water V5.7b Initial Model Result

Date: 2026-07-18

Status:

```text
initial_model_validation_passed
research_signal_candidate
not_formal_strategy_candidate
```

## Research Loop Result

Research Agent first proposed an OCF + dividend + value-trap-guard hypothesis for gas / water operators.

Quant Agent rejected the pure OCF mainline:

```text
V5.7a OCF/dividend/guard composite returned 40.31%,
below high-dividend top10 at 48.08% and equal-weight at 42.54%.
```

Research Agent then revised the hypothesis:

```text
Gas / water operators may behave more like regulated-asset value stocks than pure OCF stocks.
```

The revised model V5.7b passed the initial research validation gate.

## Accepted Preliminary Hypothesis

```text
Low PB + serviceability + dividend support is a better first model for gas / water operators than raw OCF or raw FCF.
```

Factor roles:

| Factor | Role |
| --- | --- |
| `low_price_to_book_safe` | regulated-asset valuation discipline |
| `interest_coverage_safe` | debt serviceability |
| `dividend_yield` | shareholder-return support |
| `debt_pressure_safe` | risk context / guard |
| `capex_burden_safe` | capex-quality guard candidate |

## Evidence

Formal validation:

```text
validation_formal_v57_gas_water_v57b/gas_water_value_serviceability_v57b/formal_validation_summary.json
```

Headline comparison:

| Case | Cum Return | Positive Ratio |
| --- | ---: | ---: |
| equal_weight_gas_water | 42.54% | 55.00% |
| high_dividend_top10 | 48.08% | 50.00% |
| low_pb_safe_top10 | 83.23% | 65.00% |
| v57b_value_serviceability_top10 | 87.08% | 75.00% |

Rolling:

| Year | Cum Return |
| --- | ---: |
| 2023 | 14.27% |
| 2024 | 15.13% |
| 2025 | 24.15% |
| 2026 | -8.58% |

## Rejected Hypotheses

| Hypothesis | Decision |
| --- | --- |
| OCF is the main standalone alpha signal | rejected in V5.7a |
| Cash-collection/debt/capex guard alone can define selection | rejected in V5.7c |
| Old V5.5a dividend + OCF + low PB + capex model is sufficient | rejected as inferior to revised V5.7b |

## Required Next Research

Before Engineering:

```text
operator_purity PIT panel
receivables_to_revenue
receivables_growth_minus_revenue_growth
direct gas/water revenue share
project_or_engineering_revenue_share
2026 failure analysis
```

## PM Note

V5.7b is only an initial model. It is not accepted and not ready for platform replication.

The important process result is:

```text
The Research -> Quant loop worked: first hypothesis failed, revised hypothesis passed initial validation.
```

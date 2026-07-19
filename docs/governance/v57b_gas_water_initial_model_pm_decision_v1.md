# V5.7b Gas / Water Initial Model PM Decision V1

Date: 2026-07-18

Owner:

```text
Project Manager Agent, Research Agent, Quant Validation Agent
```

Strategy:

```text
gas_water_value_serviceability_v57b
```

Status:

```text
initial_model_validation_passed
research_pit_validation_completed
not_formal_strategy_candidate
not_engineering_handoff
not_accepted_strategy
```

## PM Decision

V5.7 gas / water workflow has produced one preliminary model that passes the initial research validation gate:

```text
Gas / Water Value + Serviceability V5.7b
```

The model should be kept as:

```text
research_signal_candidate
```

It should not yet be promoted to:

```text
formal_strategy_candidate
platform_replication
paper_trading
accepted_strategy
```

## What Was Tested

Input PIT panel:

```text
数据库/processed/similar_sector_pit_panel_v57/gas_water_operators/panel.csv
```

Enriched panel:

```text
数据库/processed/gas_water_v57_enriched_panel/panel_enriched.csv
```

Formal validation outputs:

```text
validation_formal_v57_gas_water_v57b/gas_water_value_serviceability_v57b/
```

Compared candidates:

| Model | Decision | Reason |
| --- | --- | --- |
| `gas_water_cashflow_dividend_v55a` | rejected as old baseline | Composite did not beat high-dividend baseline |
| `gas_water_ocf_dividend_guard_v57a` | rejected | OCF mainline failed; composite underperformed high-dividend and equal-weight |
| `gas_water_value_serviceability_v57b` | preliminary pass | Beat equal-weight, high-dividend and low-PB baseline; rolling behavior acceptable except 2026 |
| `gas_water_collection_debt_guard_v57c` | rejected | Collection/debt/capex guard composite underperformed sharply |

## V5.7b Hypothesis

Research conclusion:

```text
Gas / water operators currently look less like a pure OCF basket sleeve and more like regulated-asset value stocks.
```

Model logic:

```text
low PB for regulated-asset valuation discipline
dividend yield for shareholder-return support
interest coverage for debt serviceability
asset-liability ratio for debt pressure
capex burden with negative-OCF penalty for capex quality
```

This does not overturn the V5.6c basket rule:

```text
Low PB is still not restored as a basket-wide mainline.
```

It is only a sector-specific gas / water hypothesis.

## Key Metrics

| Check | Result |
| --- | ---: |
| PIT leakage audit | pass |
| Row count | 830 |
| Rebalance dates | 20 |
| Securities | 45 |
| Equal-weight same-pool return | 42.54% |
| High-dividend top10 return | 48.08% |
| Low-PB safe top10 return | 83.23% |
| V5.7b composite return | 87.08% |
| V5.7b positive period ratio | 75.00% |
| Mean selected count | 10 |

Rolling validation:

| Year | Cum Return | Positive Ratio |
| --- | ---: | ---: |
| 2023 | 14.27% | 100.00% |
| 2024 | 15.13% | 75.00% |
| 2025 | 24.15% | 100.00% |
| 2026 | -8.58% | 50.00% |

Robustness:

| Case | Cum Return | Positive Ratio |
| --- | ---: | ---: |
| selection_count_8 | 90.75% | 75.00% |
| selection_count_10 | 87.08% | 75.00% |
| selection_count_12 | 73.73% | 65.00% |
| weight_scale_0.8 | 82.64% | 70.00% |
| weight_scale_1.0 | 87.08% | 75.00% |
| weight_scale_1.2 | 75.00% | 75.00% |

## Factor Evidence

| Factor | Mean IC | Mean RankIC | Positive IC Ratio | Interpretation |
| --- | ---: | ---: | ---: | --- |
| `low_price_to_book_safe` | -0.0570 | 0.0931 | 40.00% | Rank evidence is positive; IC sign is mixed |
| `dividend_yield` | 0.0193 | 0.0897 | 50.00% | Useful support, not enough alone |
| `interest_coverage_safe` | 0.0513 | 0.0491 | 55.00% | Best clean statistical support among model fields |
| `debt_pressure_safe` | -0.0174 | -0.0015 | 50.00% | Weak as standalone factor; kept as risk context |
| `capex_burden_safe` | -0.0496 | -0.0540 | 45.00% | Standalone signal is weak; kept as accounting-quality guard candidate |

## Ablation

V5.7b composite:

```text
87.08%
```

Drop-factor results:

| Drop Factor | Cum Return |
| --- | ---: |
| drop_low_price_to_book_safe | 65.74% |
| drop_dividend_yield | 78.34% |
| drop_interest_coverage_safe | 66.63% |
| drop_debt_pressure_safe | 73.06% |
| drop_capex_burden_safe | 76.37% |

PM interpretation:

```text
No single included factor removal improves the model in this sample, but dividend, debt and capex are still support/guard variables rather than standalone alpha proof.
```

## Failure Mode

2026 remains the main unresolved weakness:

```text
V5.7b returned -8.58% in the 2026 partial window,
underperforming both equal-weight and low-PB baselines.
```

This is not a blocker for initial research pass, but it blocks Engineering handoff until explained.

Possible causes to test later:

- gas / water sector style reversal;
- tariff reform and receivables pressure not captured directly;
- operator-purity contamination;
- small-cap / liquidity exposure;
- market regime not handled by current risk layer.

## Blockers Before Engineering

V5.7b cannot be handed to Engineering until these are repaired:

1. Build PIT operator-purity panel from Eastmoney/F10 plus annual/interim report review.
2. Add direct receivables fields, not only `cash_collection_quality_safe`.
3. Confirm gas / water industry benchmark or use same-pool benchmark with clear policy.
4. Collect real JoinQuant daily open/close and true cash dividends.
5. Run daily local simulation and failure attribution.
6. Analyze 2026 failure before any platform replication.

## PM Next Gate

```text
gas_water_operator_purity_and_receivables_data_repair
```

Only after that gate passes may V5.7b become:

```text
formal_strategy_candidate
```

Hard rule:

```text
Historical performance alone is never sufficient evidence for accepting a strategy.
```

# V5.7b Gas / Water Business-Purity And Financial-Evidence Repair PM Decision V1

Date: 2026-07-19

Owner:

```text
Project Manager Agent, Research Agent, Quant Validation Agent
```

Strategy:

```text
gas_water_value_serviceability_v57b
```

## PM Decision

V5.7b passed the first repair gate:

```text
business_purity_repair_passed
direct_financial_evidence_repair_passed
research_signal_candidate_repaired
```

It is still not promoted to:

```text
formal_strategy_candidate
engineering_handoff
platform_replication
paper_trading
accepted_strategy
```

Reason:

```text
The operator-purity and direct receivables/debt data blockers were repaired, but 2026 remains unresolved at daily/state level.
```

## What Was Repaired

Business-purity input:

```text
数据库/processed/gas_water_operating_evidence_v57/gas_water_segment_business_evidence_eastmoney.csv
```

Business-purity panel:

```text
数据库/processed/gas_water_operating_evidence_v57/business_purity_panel/panel_business_purity_passed.csv
```

Direct financial-evidence panel:

```text
数据库/processed/gas_water_financial_evidence_v57/panel_with_direct_financial_evidence.csv
```

Validation packet:

```text
validation_formal_v57_gas_water_v57b_direct_financial/gas_water_value_serviceability_v57b/
```

## Business-Purity Gate

| Check | Result |
| --- | ---: |
| Source panel rows | 830 |
| Passed rows | 746 |
| Removed rows | 84 |
| Passed code count | 40 |
| Minimum operator revenue share | 50% |
| Lowest rebalance coverage | 71.79% |

PM readout:

```text
The model did not depend on broad contamination from non-operator companies. After business-purity filtering, the signal remained stable.
```

Source warning:

```text
Eastmoney segment evidence is first-layer structured evidence only. Annual/interim report spot checks are still required before Engineering handoff.
```

## Direct Receivables / Debt Repair

JQData PIT fields were joined for:

```text
account_receivable
bill_receivable
receivable_fin
contract_assets
longterm_receivable_account
goods_sale_and_service_render_cash
shortterm_loan
longterm_loan
bonds_payable
non_current_liability_in_one_year
cash_equivalents
net_operate_cash_flow
```

Coverage:

| Field group | Coverage |
| --- | ---: |
| Direct receivables | 100% |
| Direct collection cash / revenue | 100% |
| Direct interest-bearing debt / assets | 100% |

PM readout:

```text
The previous blocker "direct receivables fields are not joined" is repaired. Remaining 2026 weakness is not a simple data-coverage issue.
```

## Validation After Repair

Business-purity validation:

| Case | Cum Return | Positive Ratio |
| --- | ---: | ---: |
| Equal-weight gas/water | 42.59% | 55.00% |
| High-dividend top10 | 51.35% | 50.00% |
| Low-PB safe top10 | 72.96% | 65.00% |
| V5.7b composite | 90.09% | 75.00% |

Rolling validation:

| Year | Cum Return | Positive Ratio |
| --- | ---: | ---: |
| 2023 | 16.55% | 100.00% |
| 2024 | 12.61% | 75.00% |
| 2025 | 25.95% | 100.00% |
| 2026 | -9.60% | 50.00% |

## 2026 Attribution

Direct-factor attribution:

```text
validation_formal_v57_gas_water_v57b_direct_financial/gas_water_value_serviceability_v57b/gas_water_v57b_2026_direct_factor_attribution.md
```

PM readout:

```text
2026-01 is the main unresolved window.
The selected group had better collection and lower debt, but higher receivables/revenue than the broad universe.
2026-04 was a broad sector drawdown; the selected group was still negative but slightly better than all-universe and low-PB top10.
```

Interpretation:

```text
Direct receivables can become a future Research Agent guard hypothesis, but adding it now would be 2026-aware tuning.
```

## Current Status

```text
research_signal_candidate_repaired
not_formal_strategy_candidate
not_engineering_handoff
```

## Remaining Blockers

1. Annual/interim report spot checks for business-purity evidence.
2. Daily-level 2026 attribution using real daily open/close and dividends.
3. External state evidence for tariff reform, gas procurement cost, water price reform or regulated-utility style regime.
4. Benchmark policy for gas/water operators.

## Next Gate

```text
gas_water_daily_attribution_and_external_state_repair
```

Hard rule:

```text
Historical performance alone is never sufficient evidence for accepting a strategy.
```

# V5a.3 Theory-Gated Sector Prevalidation PM Report

Created at UTC: `2026-07-21T12:24:29+00:00`

## Decision

All configured sectors were routed through the V5a.2 theory gate. This is not strategy acceptance and not platform replication.

## Decision Counts

| Decision | Count |
| --- | ---: |
| `archived_after_failed_initial_validation` | 6 |
| `blocked_by_cycle_data_gate_before_initial_validation` | 3 |
| `blocked_by_data_gate_before_initial_validation` | 2 |
| `blocked_by_specialist_data_gate_before_initial_validation` | 1 |
| `excluded_before_initial_validation` | 7 |
| `passed_prevalidation_shadow_basket_refresh` | 6 |
| `research_loop_after_initial_validation` | 8 |

## Full Sector Table

| Sector | Primary theory | Factor priority | Decision | Next agent |
| --- | --- | --- | --- | --- |
| Bank | `sector_specific_value_and_balance_sheet_quality` | `sector_specific_value>dividend_sustainability>low_volatility` | `passed_prevalidation_shadow_basket_refresh` | `Engineering Agent` |
| Utilities / Electricity | `ocf_low_vol_dividend_sustainability` | `operating_cash_flow_yield>low_volatility>dividend_sustainability>sector_approved_free_cash_flow_yield` | `passed_prevalidation_shadow_basket_refresh` | `Engineering Agent` |
| Highway Infrastructure | `ocf_low_vol_dividend_sustainability` | `operating_cash_flow_yield>low_volatility>dividend_sustainability` | `passed_prevalidation_shadow_basket_refresh` | `Engineering Agent` |
| Port / Rail Infrastructure | `ocf_low_vol_dividend_sustainability` | `operating_cash_flow_yield>low_volatility>dividend_sustainability>sector_approved_free_cash_flow_yield` | `passed_prevalidation_shadow_basket_refresh` | `Engineering Agent` |
| Gas / Water Operators | `ocf_low_vol_dividend_sustainability` | `operating_cash_flow_yield>low_volatility>dividend_sustainability` | `passed_prevalidation_shadow_basket_refresh` | `Engineering Agent` |
| Telecom Operators | `ocf_low_vol_dividend_sustainability` | `operating_cash_flow_yield>low_volatility>dividend_sustainability` | `research_loop_after_initial_validation` | `Research Agent` |
| Insurance | `sector_specific_value_and_balance_sheet_quality` | `sector_specific_value>dividend_sustainability>low_volatility` | `passed_prevalidation_shadow_basket_refresh` | `Engineering Agent` |
| Securities / Brokerage | `sector_specific_value_and_balance_sheet_quality` | `sector_specific_value>dividend_sustainability>low_volatility` | `research_loop_after_initial_validation` | `Research Agent` |
| Oil / Gas Pipeline and Integrated Energy | `cycle_aware_ocf_value_with_external_state` | `operating_cash_flow_yield>external_cycle_state>low_volatility>dividend_sustainability` | `research_loop_after_initial_validation` | `Research Agent` |
| Coal | `cycle_aware_ocf_value_with_external_state` | `operating_cash_flow_yield>external_cycle_state>low_volatility>dividend_sustainability` | `archived_after_failed_initial_validation` | `Project Manager Agent` |
| Steel | `cycle_aware_ocf_value_with_external_state` | `operating_cash_flow_yield>external_cycle_state>low_volatility>dividend_sustainability` | `blocked_by_cycle_data_gate_before_initial_validation` | `Research Agent` |
| Nonferrous Metals | `cycle_aware_ocf_value_with_external_state` | `operating_cash_flow_yield>external_cycle_state>low_volatility>dividend_sustainability` | `blocked_by_cycle_data_gate_before_initial_validation` | `Research Agent` |
| Basic Chemicals | `cycle_aware_ocf_value_with_external_state` | `operating_cash_flow_yield>external_cycle_state>low_volatility>dividend_sustainability` | `archived_after_failed_initial_validation` | `Project Manager Agent` |
| Building Materials / Cement | `cycle_aware_ocf_value_with_external_state` | `operating_cash_flow_yield>external_cycle_state>low_volatility>dividend_sustainability` | `archived_after_failed_initial_validation` | `Project Manager Agent` |
| Construction Engineering | `cash_conversion_and_receivables_trap_detection` | `operating_cash_flow_yield>low_volatility>dividend_sustainability` | `blocked_by_data_gate_before_initial_validation` | `Research Agent` |
| Environmental / Project Operators | `cash_conversion_and_receivables_trap_detection` | `operating_cash_flow_yield>low_volatility>dividend_sustainability` | `blocked_by_data_gate_before_initial_validation` | `Research Agent` |
| Real Estate | `outside_current_dividend_low_vol_cashflow_mandate` | `not_in_current_mandate` | `excluded_before_initial_validation` | `Project Manager Agent` |
| Consumer Staples Cash-Flow Leaders | `cash_flow_quality_and_defensive_demand` | `operating_cash_flow_yield>low_volatility>dividend_sustainability>sector_approved_free_cash_flow_yield` | `research_loop_after_initial_validation` | `Research Agent` |
| Food / Beverage | `cash_flow_quality_and_defensive_demand` | `operating_cash_flow_yield>low_volatility>dividend_sustainability>sector_approved_free_cash_flow_yield` | `research_loop_after_initial_validation` | `Research Agent` |
| Home Appliances | `cash_flow_quality_and_defensive_demand` | `operating_cash_flow_yield>low_volatility>dividend_sustainability>sector_approved_free_cash_flow_yield` | `research_loop_after_initial_validation` | `Research Agent` |
| Textile / Apparel | `cash_flow_quality_and_defensive_demand` | `operating_cash_flow_yield>low_volatility>dividend_sustainability>sector_approved_free_cash_flow_yield` | `research_loop_after_initial_validation` | `Research Agent` |
| Pharma / Medical Services | `ocf_low_vol_dividend_sustainability` | `operating_cash_flow_yield>low_volatility>dividend_sustainability` | `blocked_by_specialist_data_gate_before_initial_validation` | `Research Agent` |
| Agriculture / Forestry / Fishery | `outside_current_dividend_low_vol_cashflow_mandate` | `not_in_current_mandate` | `excluded_before_initial_validation` | `Project Manager Agent` |
| Logistics / Express Delivery | `ocf_low_vol_dividend_sustainability` | `operating_cash_flow_yield>low_volatility>dividend_sustainability` | `research_loop_after_initial_validation` | `Research Agent` |
| Shipping | `cycle_aware_ocf_value_with_external_state` | `operating_cash_flow_yield>external_cycle_state>low_volatility>dividend_sustainability` | `blocked_by_cycle_data_gate_before_initial_validation` | `Research Agent` |
| Retail / Commerce | `cash_flow_quality_and_defensive_demand` | `operating_cash_flow_yield>low_volatility>dividend_sustainability>sector_approved_free_cash_flow_yield` | `archived_after_failed_initial_validation` | `Project Manager Agent` |
| Media / Entertainment | `outside_current_dividend_low_vol_cashflow_mandate` | `not_in_current_mandate` | `excluded_before_initial_validation` | `Project Manager Agent` |
| Computer / Software | `outside_current_dividend_low_vol_cashflow_mandate` | `not_in_current_mandate` | `excluded_before_initial_validation` | `Project Manager Agent` |
| Electronics / Semiconductor | `outside_current_dividend_low_vol_cashflow_mandate` | `not_in_current_mandate` | `excluded_before_initial_validation` | `Project Manager Agent` |
| Auto and Parts | `ocf_low_vol_dividend_sustainability` | `operating_cash_flow_yield>low_volatility>dividend_sustainability` | `archived_after_failed_initial_validation` | `Project Manager Agent` |
| Machinery / Equipment | `ocf_low_vol_dividend_sustainability` | `operating_cash_flow_yield>low_volatility>dividend_sustainability` | `archived_after_failed_initial_validation` | `Project Manager Agent` |
| Power Equipment / New Energy | `outside_current_dividend_low_vol_cashflow_mandate` | `not_in_current_mandate` | `excluded_before_initial_validation` | `Project Manager Agent` |
| Military / Defense | `outside_current_dividend_low_vol_cashflow_mandate` | `not_in_current_mandate` | `excluded_before_initial_validation` | `Project Manager Agent` |

## Theory Rules Applied

- OCF / cash-flow quality and low volatility are the cross-sector core.
- FCF is an enhancement only after sector capex and accounting comparability pass.
- Low PB is sector-specific valuation support, not the global basket mainline.
- Momentum is a support/state hypothesis and requires horizon plus turnover audit.
- Mean reversion requires an ex-ante value-trap guard.
- Cyclical sectors cannot enter validation without price, output/inventory, spread and business-exposure state.

## Output Paths

- CSV: `sector_replication_batches_v5a3\theory_gated_prevalidation_current\theory_gated_sector_prevalidation.csv`
- Summary: `sector_replication_batches_v5a3\theory_gated_prevalidation_current\theory_gated_sector_prevalidation_summary.json`
- Report: `sector_replication_batches_v5a3\theory_gated_prevalidation_current\theory_gated_sector_prevalidation_pm_report.md`
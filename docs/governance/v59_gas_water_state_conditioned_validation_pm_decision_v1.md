# V5.9 Gas / Water State-Conditioned Validation PM Decision

Date: 2026-07-21

Strategy: `gas_water_value_serviceability_v57b`

Diagnostic strategy id: `gas_water_value_serviceability_state_diagnostic_v59`

Decision: `do_not_handoff_engineering`

## PM Conclusion

Gas / water V57b should not enter Engineering.

Quant state-conditioned validation has started and completed its first diagnostic pass. The current ex-ante proxy state variables are useful for research triage, but they do not stably explain the 2026 failure enough to justify local simulation / basket candidate promotion.

## Evidence

Validation packet:

`validation_state_v59_gas_water/gas_water_value_serviceability_state_diagnostic_v59/state_conditioned_quant_validation_packet/state_conditioned_quant_validation_summary.json`

Explainability table:

`validation_state_v59_gas_water/gas_water_value_serviceability_state_diagnostic_v59/state_conditioned_quant_validation_packet/state_metric_explainability.csv`

Factor IC table:

`validation_state_v59_gas_water/gas_water_value_serviceability_state_diagnostic_v59/state_conditioned_quant_validation_packet/state_conditioned_factor_ic_all_metrics.csv`

Combined state dates:

`validation_state_v59_gas_water/gas_water_value_serviceability_state_diagnostic_v59/state_conditioned_quant_validation_packet/combined_state_bucket_dates.csv`

## What The Validation Found

The tested state metrics were:

- `sector_receivables_to_revenue_median`
- `sector_collection_cash_to_revenue_median`
- `sector_net_debt_to_assets_median`
- `same_pool_trailing_60d_return`
- `same_pool_trailing_60d_volatility`
- `same_pool_trailing_60d_drawdown`

2026 underperformed equal-weight under every tested state view.

However, the historical buckets matching 2026 do not show stable V57b weakness versus equal-weight. In several high-state buckets, V57b still historically outperformed equal-weight.

Therefore, using these state variables as a 2026 explanation would be too close to post-hoc interpretation.

## Important Nuance

2026 falls into a combined state key:

`high;high;high`

for:

- receivables pressure
- net-debt pressure
- prior same-pool return

This state appears in history, but it is not sufficient evidence for promotion because:

- the state combination is sparse,
- it is still a proxy built from current financial and market panels,
- it does not include true gas procurement / tariff pass-through or water tariff / local-fiscal payment data,
- it does not consistently prove V57b underperformance across baselines.

## PM Decision

Current status:

`state_conditioned_validation_failed_to_explain_2026_for_engineering`

Engineering handoff:

`blocked`

Next gate:

`research_agent_collect_true_operating_state_or_archive_research_signal_candidate`

## Required Research Repair

Before another Quant pass, Research Agent should collect true operating state data:

1. Gas procurement cost and terminal sales price / pass-through state.
2. Water tariff adjustment progress and tariff lag.
3. Water receivables collection pressure and local fiscal payment proxy.
4. Financing pressure proxy, such as sector bond spread, issuance cost, or credit-event state.

These must be structured as PIT rows with `visible_date` and `source_publication_date`.

## Guardrails

- Do not tune V57b weights using 2021-2026.
- Do not use research reports as direct factor data.
- Do not enter Engineering from this packet.
- Keep gas/water as `research_signal_candidate` unless true operating-state data repairs the 2026 explanation.


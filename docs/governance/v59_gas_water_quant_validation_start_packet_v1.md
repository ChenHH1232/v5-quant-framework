# V5.9 Gas / Water Quant Validation Start Packet

Date: 2026-07-21

Strategy: `gas_water_value_serviceability_v57b`

Diagnostic strategy id: `gas_water_value_serviceability_state_diagnostic_v59`

Decision: `quant_validation_can_start`

## PM Conclusion

Gas / water is now ready for Quant Agent state-conditioned validation.

This does not promote the strategy, and it does not hand the work to Engineering. It only means the external-state blocker has been repaired enough for Quant Agent to run a formal diagnostic review.

## Validation Inputs

State-enriched panel:

`数据库/processed/gas_water_state_enriched_panel_v59/panel_with_external_state.csv`

Formal compatibility packet:

`validation_formal_v59_gas_water_state_enriched/gas_water_value_serviceability_v57b/formal_validation_summary.json`

State bucket packet root:

`validation_state_v59_gas_water/gas_water_value_serviceability_state_diagnostic_v59/`

Quant start packet:

`validation_state_v59_gas_water/gas_water_value_serviceability_state_diagnostic_v59/quant_state_validation_start_packet/quant_state_validation_start_packet.json`

## Readiness Result

- state metric count: `6`
- ready metric count: `6`
- minimum coverage: `100%`
- status: `quant_validation_can_start`

All required state metrics produced state-bucket validation outputs:

- `sector_receivables_to_revenue_median`
- `sector_collection_cash_to_revenue_median`
- `sector_net_debt_to_assets_median`
- `same_pool_trailing_60d_return`
- `same_pool_trailing_60d_volatility`
- `same_pool_trailing_60d_drawdown`

## Initial 2026 State Observation

2026 falls into high-pressure / elevated-state buckets for:

- `sector_receivables_to_revenue_median`
- `sector_net_debt_to_assets_median`
- `sector_collection_cash_to_revenue_median`
- `same_pool_trailing_60d_return`

The working hypothesis is:

> Gas / water value + dividend selection may underperform when sector receivables pressure and net-debt pressure are elevated, especially after a strong same-pool price run.

This hypothesis is now testable. It is not yet proven.

## Quant Agent Task

Run full state-conditioned validation:

1. State-conditioned IC / RankIC for all current V57b factors.
2. Baseline comparison inside high-pressure versus normal states.
3. 2026 failure attribution under each state metric.
4. Check whether state-aware explanation is ex-ante and stable.
5. PM decision:
   - return to Research Agent,
   - keep as research_signal_candidate,
   - or approve Engineering to evaluate a state-aware candidate.

## Guardrails

- Do not tune V57b weights using 2021-2026.
- Do not use research reports as factor data unless converted into PIT rows.
- Do not enter Engineering until Quant Agent explains 2026 with ex-ante evidence.
- This packet opens validation; it is not acceptance.


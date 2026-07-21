# V5.9 Gas / Water External State Validation Ready Packet

Date: 2026-07-21

Strategy: `gas_water_value_serviceability_v57b`

Diagnostic strategy id: `gas_water_value_serviceability_state_diagnostic_v59`

Layer: `research_pit_validation`

## PM Decision

Gas / water can now start Quant state-variable validation.

This is not an Engineering handoff and not a strategy promotion. It only means the prior blocker, "no structured ex-ante state panel", has been repaired enough to begin validation.

## What Changed

Added a reusable gas / water state runner:

`src/v5/gas_water_external_state_runner.py`

Added CLI entries:

- `build-gas-water-external-state`
- `validate-gas-water-external-state`
- `build-gas-water-state-enriched-panel`
- `validate-gas-water-state-bucket`

Added regression test:

`tests/test_gas_water_external_state_runner.py`

## Generated Inputs

External state panel:

`数据库/processed/gas_water_external_state_v59/gas_water_external_state.csv`

Manifest:

`数据库/processed/gas_water_external_state_v59/collection_manifest.json`

State-enriched research panel:

`数据库/processed/gas_water_state_enriched_panel_v59/panel_with_external_state.csv`

Manifest:

`数据库/processed/gas_water_state_enriched_panel_v59/collection_manifest.json`

## State Metrics Opened For Validation

The initial state panel uses only ex-ante, structured proxies:

- `sector_receivables_to_revenue_median`
- `sector_collection_cash_to_revenue_median`
- `sector_net_debt_to_assets_median`
- `same_pool_trailing_60d_return`
- `same_pool_trailing_60d_volatility`
- `same_pool_trailing_60d_drawdown`

Financial-state rows are cross-sectional aggregates from the existing PIT gas/water financial evidence panel.

Market-state rows use same-pool benchmark prices strictly before the rebalance date.

## Readiness Results

External state panel:

- rows: `200`
- PIT usable rows: `200`
- status: `state_validation_ready`

State-enriched panel:

- rows: `746`
- state-enriched rows: `746`
- status: `state_validation_ready`

Validation smoke run:

- all 6 required state metrics produced state bucket validation packets
- status: `state_bucket_validation_completed_not_acceptance`

Output root:

`validation_state_v59_gas_water/gas_water_value_serviceability_state_diagnostic_v59/`

## Initial 2026 Diagnostic Observation

2026 appears in the high bucket for:

- `sector_receivables_to_revenue_median`
- `sector_net_debt_to_assets_median`
- `same_pool_trailing_60d_return`

This supports a testable research direction:

> Gas / water value + dividend selection may weaken when sector receivables pressure and net-debt pressure are high, especially after a strong same-pool price run.

This is a hypothesis for Quant validation, not a conclusion.

## Quant Agent Next Step

Run state validation as a formal diagnostic packet:

1. state bucket validation across all required state metrics
2. 2026 failure attribution under state buckets
3. factor IC / RankIC by state bucket
4. baseline comparison in high-pressure vs normal-pressure states
5. PM decision on whether to:
   - return to Research Agent for a new hypothesis,
   - keep gas/water as research_signal_candidate only,
   - or allow Engineering to evaluate a state-aware candidate.

## Guardrails

- Do not tune weights using 2021-2026.
- Do not promote to `formal_strategy_candidate` from this packet alone.
- Do not hand off to Engineering until Quant state validation explains 2026 with ex-ante evidence.
- Research reports remain hypothesis evidence only unless converted into structured PIT source rows.


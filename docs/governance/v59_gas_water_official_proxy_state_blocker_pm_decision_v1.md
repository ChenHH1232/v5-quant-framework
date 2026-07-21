# V5.9 Gas / Water Official Proxy State Blocker PM Decision

Date: 2026-07-21

Strategy: `gas_water_value_serviceability_v57b`

Decision: `engineering_handoff_blocked`

## PM Conclusion

Gas / water still cannot enter Engineering.

We repaired the previous blocker by adding machine-readable official proxy state data, but Quant validation still failed to produce a stable ex-ante explanation for the 2026 weakness.

The PM decision is:

`archive_gas_water_or_collect_company_level_true_operating_state`

## What Was Tried

Added official proxy state collection to:

`src/v5/gas_water_external_state_runner.py`

New CLI option:

`build-gas-water-external-state --include-official-proxies`

Official / market proxy sources:

- AkShare `macro_china_qyspjg`
  - NBS production-material total price YoY
  - NBS mineral product price YoY
  - NBS coal / oil / power price YoY
- AkShare `macro_china_shibor_all`
  - 3M Shibor
  - 1Y Shibor
  - 3M Shibor 60-observation change
- AkShare `macro_china_lpr`
  - 1Y LPR
  - 5Y LPR

Generated panel:

`数据库/processed/gas_water_external_state_v59_official_proxy/gas_water_external_state.csv`

State-enriched panel:

`数据库/processed/gas_water_state_enriched_panel_v59_official_proxy/panel_with_external_state.csv`

Validation root:

`validation_state_v59_gas_water_official_proxy/gas_water_value_serviceability_official_state_diagnostic_v59/`

Summary:

`validation_state_v59_gas_water_official_proxy/gas_water_value_serviceability_official_state_diagnostic_v59/official_proxy_state_quant_validation_packet/official_proxy_state_quant_validation_summary.json`

## Result

Official proxy state validation status:

`official_proxy_state_validation_failed_to_open_engineering`

Supporting metrics:

`[]`

Meaning:

- Official proxy rows were collected with PIT-visible dates.
- All official proxy metrics produced state-bucket validation outputs.
- No official proxy metric gave a stable enough historical explanation to justify Engineering handoff.

## Why This Blocks Engineering

Engineering Agent should only receive frozen candidates whose research evidence is stable enough to implement.

For gas / water:

- V57b 2026 failure remains unresolved.
- V57c collection / debt guard was worse, not better.
- Proxy state variables do not explain 2026 robustly.
- Research reports provide useful hypotheses but no structured PIT state series.
- True operating variables are still missing:
  - city-gas procurement cost and terminal sales-price pass-through,
  - gas connection / installation income decline,
  - water tariff adjustment by region / company,
  - water receivable collection and local fiscal payment state,
  - company-level financing pressure.

## PM Decision

Do not hand off gas / water to Engineering.

Allowed next actions:

1. Archive gas / water as `research_signal_candidate_blocked_by_true_operating_state`.
2. Or start a heavier Research Agent task to collect company-level true operating-state data from announcements, annual reports and credit reports.

Not allowed:

- No local daily simulation as an Engineering candidate.
- No basket inclusion as a live candidate.
- No tuning V57b weights on 2021-2026.


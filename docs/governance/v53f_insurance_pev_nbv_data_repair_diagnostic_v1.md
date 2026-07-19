# Governance Record: v53f_insurance_pev_nbv_data_repair_diagnostic_v1

Date: 2026-07-17

Project:

```text
V5.3f Insurance P/EV, EV and NBV PIT Repair Probe
```

PM decision:

```text
insurance_pev_nbv_research_data_repair_partial_not_engineering_handoff
```

## Work Completed

- Added Research Agent knowledge: `insurance_pev_ev_nbv_research_framework.md`.
- Added reviewed EV/NBV source table: `insurance_ev_nbv_reviewed_2024_2025_core5.csv`.
- Added reusable runner: `insurance-ev-nbv-panel`.
- Added diagnostic spec: `insurance_pev_nbv_v53f_diagnostic_strategy.json`.
- Ran EV/NBV source audit.
- Ran PIT P/EV panel coverage gate.
- Ran Quant diagnostic on covered rows only.

## Evidence Paths

- `knowledge/research_agent/factor_theory/insurance_pev_ev_nbv_research_framework.md`
- `knowledge/research_agent/references/insurance_ev_nbv_reviewed_2024_2025_core5.csv`
- `insurance_ev_nbv_source_audit_v53f/insurance_pev_nbv_v53f_source/insurance_special_fields_audit_summary.json`
- `insurance_ev_nbv_panel_v53f/insurance_pev_nbv_v53f/ev_nbv_panel_summary.json`
- `validation_diagnostic_v53f_insurance_pev_nbv/insurance_pev_nbv_v53f_diagnostic/formal_validation_summary.json`

## Gate Results

EV/NBV source audit:

```text
passed for EV/NBV-specific source fields
```

P/EV PIT panel:

```text
blocked by insufficient history
```

Diagnostic validation:

```text
completed_not_acceptance
```

## Blocking Reasons

- P/EV coverage spans only 2025-2026.
- Rolling validation is skipped.
- NBV growth has only one usable date.
- 2024 New China Life exact EV/NBV values remain unconfirmed.
- CPIC EV口径 differs between the 2024 life-only row and the 2025 group seed.

## PM Ruling

Insurance remains:

```text
research_signal_exists_but_not_deployable
blocked_until_multi_year_ev_nbv_pit_repair
```

Insurance is not:

```text
formal_strategy_candidate
platform_replication_ready
paper_trading_ready
joinquant_code_ready
```

## Next Approved Work

Repair 2021-2023 EV/NBV from original annual reports or official announcement links, then rebuild the panel and rerun:

- coverage gate;
- IC / RankIC;
- rolling validation;
- baseline;
- ablation;
- robustness;
- 2021 / 2022 / 2026 failure analysis.

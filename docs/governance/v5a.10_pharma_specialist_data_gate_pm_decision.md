# V5a.10 Pharma Specialist Data Gate PM Decision

Date: 2026-07-21

## Decision

V5a.10 blocks Pharma / Medical Services from ordinary enhanced-ETF Quant validation.

The sector has enough PIT panel coverage for a generic OCF / low-volatility diagnostic, but it does not have the specialist fields required by the Research Agent framework:

- R&D expense / revenue;
- capitalized R&D ratio;
- procurement pressure state;
- policy / reimbursement state.

Therefore pharma cannot be promoted as a normal dividend low-volatility and OCF/FCF sleeve. It remains a specialist research/data-repair lane.

## Evidence

Data gate output:

```text
数据库/processed/pharma_specialist_data_gate_v5a10/pharma_specialist_data_gate_summary.json
数据库/processed/pharma_specialist_data_gate_v5a10/pharma_specialist_field_coverage.csv
数据库/processed/pharma_specialist_data_gate_v5a10/pharma_specialist_subsector_coverage.csv
```

Observed coverage:

| Gate | Result |
| --- | --- |
| PIT panel | Passed |
| Core cash-flow fields | Passed |
| Daily price rows | Passed |
| Research-report seed | Passed |
| Cash dividend events | Failed / not repaired |
| R&D / policy specialist fields | Failed |

Subsector sample size is not the blocker: biologics, chemical pharma, medical devices, medical services, pharma distribution and traditional Chinese medicine all have enough PIT rows for diagnostics.

## PM Interpretation

The previous V5a.6 finding remains valid:

```text
Some pharma subsectors show research signals, but generic OCF quality is not enough.
```

The new conclusion is stricter:

```text
Do not rerun formal pharma model variants until specialist PIT fields are repaired.
```

## Next Gate

Research Agent may continue only on data repair:

1. Map R&D expense, capitalized R&D and R&D intensity from JQData/DataJQ, Tushare, annual reports or audited statement tables.
2. Build PIT procurement / policy pressure state from official policy dates, procurement rounds and reimbursement/catalog events.
3. Repair real cash-dividend events before Engineering daily simulation.
4. Only after those pass should Quant Agent run specialist validation for mature pharma, biologics or other approved subsectors.

This packet is a data-availability decision, not a strategy acceptance decision.

# V5.1 Engineering Data Pipeline Update

Date: 2026-07-16

Owner:

Engineering Agent

Scope:

```text
data_pipeline_and_reusable_tools_only
```

Not scope:

```text
strategy_code
platform_replication
JoinQuant_generation
```

## Completed

Engineering Agent prepared two reusable components.

### 1. Generic Sector Rank Panel Runner

File:

```text
src/v5/sector_rank_panel_runner.py
```

CLI:

```powershell
python -m v5.cli build-sector-rank-panel <source_panel.csv> <factor_config.json> --out-dir <out_dir>
```

Purpose:

Build within-date and within-sector or within-subindustry percentile scores for any sector panel.

This makes V5.1's sub-industry scoring reusable for future sectors:

- utilities;
- coal;
- insurance;
- brokerage;
- high-dividend SOE style baskets, if later approved.

### 2. Utilities External State Template

File:

```text
src/v5/utilities_external_state_runner.py
```

CLI:

```powershell
python -m v5.cli utilities-external-state template --out-dir 数据库\processed\utilities_external_state
python -m v5.cli utilities-external-state validate 数据库\processed\utilities_external_state\utilities_external_state_template.csv
```

Purpose:

Prepare a PIT-auditable data container for external utilities variables:

- coal price / fuel-cost index;
- thermal utilization hours;
- hydropower utilization or water-condition proxy;
- gas tariff / margin proxy;
- electricity tariff / marketized power price proxy.

## Guardrails

- Every external-state row must have `visible_date`.
- Rows without `source_publication_date` are not PIT usable.
- External variables must not be joined by future publication information.
- These tools do not generate strategy code.

## Current Engineering Status

```text
engineering_data_pipeline_prepared
```

Engineering Agent remains blocked from platform replication until Project Manager Agent promotes a formal strategy candidate.

# Governance Record: v52b_coal_data_audit_blockers_v1

Date: 2026-07-16

Project:

```text
V5.2b Coal Cash-Flow Value / Cycle-Aware Value
```

Current status:

```text
research_pit_validation_data_audit_loop
```

## PM Decision

Project Manager Agent keeps V5.2b blocked from formal strategy candidacy.

The blocker-repair runner improved process control, but did not yet clear the required data conditions.

## What Was Completed

- Added formal manual-import template for raw coal output / inventory and coal price state.
- Added source-governance rule against forced scraping or bypassing restricted sources.
- Added business-tag PIT audit.
- Added FCF / capex stability audit.
- Reran V5.2b formal validation, state-bucket validation, and overfit audit.
- Added unit tests for the new audit gates.

## Current Evidence

- Research evidence remains positive for OCF yield, FCF yield, low PB, and low PE.
- OCF yield remains the cleanest core factor.
- FCF yield remains conditional on capex audit.
- 2018 remains an unresolved down-cycle failure year.
- Business classification is not yet PIT-audited.
- Official raw coal output / inventory and formal 2023+ thermal coal price data are not yet imported.

## Blocking Conditions Still Active

```text
raw_coal_output_or_inventory_missing
formal_thermal_coal_price_missing_after_2023
coal_business_tag_visible_date_missing
capex_fcf_outlier_review_required
daily_backtest_inputs_missing_for_platform_overfit_checks
```

## Agent Instructions

Research Agent:

- Continue source review for official or licensed coal output, inventory, and coal price data.
- Do not reinterpret strong historical return as acceptance.

Quant Validation Agent:

- After formal state data is imported, rerun V5.2b with common-sample IC / RankIC, rolling, ablation, robustness, state buckets, and 2018 repair analysis.
- Treat FCF as provisional until capex outlier rules are explicit.

Engineering Agent:

- Maintain import and audit runners.
- Do not write JoinQuant strategy code.
- Do not run platform replication until PM promotes V5.2b to `formal_strategy_candidate`.

## Next Decision Gate

V5.2b can be reconsidered only after:

1. A formal external state panel includes PIT-usable output/inventory and 2023+ thermal coal price rows.
2. Coal business tags have conservative visible dates.
3. FCF/capex outlier policy is documented and tested.
4. V5.2b passes formal validation again under the repaired data panel.

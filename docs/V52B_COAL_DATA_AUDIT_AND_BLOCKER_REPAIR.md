# V5.2b Coal Data Audit And Blocker Repair

Date: 2026-07-16

Owner:

```text
Project Manager Agent / Quant Validation Agent / Engineering Agent
```

Experiment layer:

```text
research_pit_validation
```

Status:

```text
research_pit_validation_strong_but_blockers_not_cleared
```

Not status:

```text
formal_strategy_candidate
platform_replication_candidate
accepted_strategy
```

## Purpose

This repair loop handles the hard blockers found after V5.2b:

- raw coal output / inventory data;
- formal thermal coal price data;
- point-in-time coal business tag visibility;
- FCF / capex definition stability;
- V5.2b rerun after blocker audit.

## Source Policy

Formal sources are prioritized in this order:

1. National Bureau of Statistics monthly raw coal output and production-material circulation price releases.
2. Licensed or manually downloaded CCTD / Qinhuangdao coal market / national coal trading center data.
3. Exchange-traded futures or macro commodity index proxies only for preliminary research interpretation.

No runner may bypass login, paywall, robots policy, anti-crawler controls, or license restrictions.

## Engineering Work Added

New runner:

```text
src/v5/coal_data_audit_runner.py
```

New CLI entry:

```text
python -m v5.cli coal-data-audit manual-state-template
python -m v5.cli coal-data-audit merge-manual-state
python -m v5.cli coal-data-audit audit-business-tags
python -m v5.cli coal-data-audit audit-capex-fcf
```

Generated local files:

```text
数据库/processed/coal_external_state/coal_manual_state_import_template.csv
数据库/processed/coal_external_state/coal_manual_state_import_manifest.json
数据库/manifests/coal_business_tag_audit/
数据库/manifests/coal_capex_fcf_audit/
```

The manual state template covers:

- `coal_inventory_or_output_state`;
- `thermal_coal_price_state`;
- `coking_coal_price_state`;
- licensed/manual market price candidates;
- licensed/manual inventory candidates.

Rows are not PIT usable until `visible_date`, `source_publication_date`, `value`, and source review are filled.

## Data Source Probe Result

The National Bureau of Statistics data path is the correct priority source, but the online NBS tree/API was unstable during this run. It returned non-JSON content through the automated route, so the system must not depend on automatic NBS scraping as the only formal path.

AkShare `macro_china_daily_energy` can provide a historical coastal six-power-plant coal inventory series, but the available local pull stopped at 2019-06-21. It is therefore only a candidate/historical reference and does not solve the 2021-2026 or 2023+ blocker.

PM interpretation:

```text
The raw coal output / inventory blocker is not cleared. A manual or licensed import is still required.
```

## Business Tag Audit

Output:

```text
数据库/manifests/coal_business_tag_audit/coal_business_tag_audit_summary.json
```

Result:

| Item | Value |
| --- | ---: |
| Companies audited | 37 |
| PIT usable tags | 0 |
| Blocked tags | 37 |

Reason:

```text
Current coal_business_tag values are manual classifications without company-report visible-date audit.
```

Required repair:

- verify annual/interim report publication dates;
- record segment revenue / segment profit evidence;
- assign conservative `business_tag_visible_date`;
- allow historical tag changes if a company changed business mix over time.

## FCF / Capex Audit

Output:

```text
数据库/manifests/coal_capex_fcf_audit/coal_capex_fcf_audit_summary.json
```

Result:

| Item | Value |
| --- | ---: |
| Panel rows | 1206 |
| Flagged rows | 405 |
| Flagged ratio | 33.58% |
| Median OCF yield | 3.95% |
| Median FCF yield | 1.96% |
| Median capex burden | 24.73% |
| P90 capex burden | 150.64% |
| Negative FCF rows | 405 |
| Capex exceeds OCF rows | 201 |

Interpretation:

```text
FCF yield is a useful research signal, but it cannot be accepted without capex outlier review.
```

Current capex field:

```text
fix_intan_other_asset_acqui_cash
```

Required repair:

- confirm this field is consistently available for coal companies;
- review whether expansion-year capex should be penalized or treated as cycle investment;
- test OCF-only, FCF-only, and capex-burden-filter variants on a common PIT sample.

## V5.2b Rerun

Formal validation rerun:

```text
validation_formal_v52b_blocker_repair/coal_cashflow_cycle_value_v52b/
```

State bucket rerun:

```text
validation_formal_v52b_blocker_repair/coal_cashflow_cycle_value_v52b/cycle_state_coking_coal_price_state/
```

Overfit audit rerun:

```text
validation_overfit_v52b_blocker_repair/coal_cashflow_cycle_value_v52b/
```

Key findings:

- V5.2b PIT evidence remains strong.
- OCF yield remains the cleanest factor.
- FCF yield remains positive but is not clean enough until capex audit is repaired.
- 2018 remains a failure year.
- 2024 remains improved but weak.
- Overfit audit has no hard blocker, but remains `needs_review` because no daily returns / rebalance signals exist yet for platform-style checks.

## PM Decision

V5.2b is not promoted.

Approved working status:

```text
research_pit_validation_data_audit_loop
```

Engineering Agent may continue:

- source import runners;
- business tag PIT audit tooling;
- capex / FCF audit tooling;
- validation packet automation.

Engineering Agent must not generate JoinQuant strategy code until these blockers are cleared and PM promotes the model to:

```text
formal_strategy_candidate
```

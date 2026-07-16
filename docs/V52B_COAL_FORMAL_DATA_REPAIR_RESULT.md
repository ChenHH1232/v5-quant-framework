# V5.2b Coal Formal Data Repair Result

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
research_pit_validation_improved_but_not_formal_candidate
```

Not status:

```text
formal_strategy_candidate
platform_replication_candidate
accepted_strategy
```

## Scope

This loop followed the required order:

1. supplement formal external state data;
2. supplement coal-business PIT visible-date infrastructure;
3. repair FCF / capex factor policy;
4. rerun V5.2b formal validation.

## External State Data

Generated:

```text
数据库/processed/coal_external_state/coal_official_state_seed.csv
数据库/processed/coal_external_state/coal_external_state_enriched.csv
```

Official NBS seed rows added:

| Metric | State date | Visible date | Value | Unit | Source |
| --- | --- | --- | ---: | --- | --- |
| `coal_inventory_or_output_state` | 2026-05-31 | 2026-06-16 | -1.7 | raw-coal output YoY % | NBS energy production release |
| `thermal_coal_price_state` | 2026-06-20 | 2026-06-24 | 862.0 | CNY / ton | NBS production-material circulation price release |
| `coking_coal_price_state` | 2026-06-20 | 2026-06-24 | 1912.5 | CNY / ton | NBS production-material circulation price release |

Enriched state validation:

| Item | Value |
| --- | ---: |
| Rows | 825 |
| PIT usable rows | 824 |
| `coal_inventory_or_output_state` usable rows | 1 |
| `thermal_coal_price_state` usable rows | 92 |
| `coking_coal_price_state` usable rows | 160 |
| Status | pass at field level |

PM interpretation:

```text
The import path is repaired, but formal historical coverage is not repaired.
```

The NBS official rows are reviewed seed rows only. They do not provide enough 2015-2026 history to approve a formal candidate.

Source notes:

- NBS monthly energy production release is the preferred official raw-coal output source.
- NBS production-material circulation price release is the preferred official coal price source.
- NBS changed coal price item specifications in 2026, so long-history stitching must document item changes.

## Business Tag PIT Visible Dates

Generated:

```text
数据库/processed/coal_business_tags/coal_business_tag_visible_date_template.csv
数据库/processed/coal_business_tags/coal_report_disclosure_dates.csv
```

Tushare disclosure collection result:

| Item | Value |
| --- | ---: |
| Coal companies | 37 |
| Target reporting years | 2014-2026 |
| Annual / semiannual disclosure rows | 859 |
| Warnings | 0 |

This solves the report-timing layer:

```text
When was an annual or semiannual report visible?
```

It does not solve the segment-evidence layer:

```text
Did the report prove core_coal / mixed_power_coal / mixed_coal_chemical at that historical date?
```

Business tags remain blocked until segment revenue / profit evidence is filled.

## FCF / Capex Policy

Generated:

```text
数据库/processed/coal_pit_panel_capex_policy/panel_capex_policy.csv
examples/coal_cashflow_cycle_value_v52b_capex_policy_strategy.json
```

Capex policy result:

| Item | Value |
| --- | ---: |
| Panel rows | 1206 |
| Capex-policy flagged rows | 464 |
| Flagged ratio | 38.47% |

Policy decision:

```text
OCF yield remains the primary cash-flow factor.
FCF yield is downgraded to auxiliary status until capex outliers are reviewed.
```

The capex-policy strategy weights are:

| Factor | Weight |
| --- | ---: |
| `operating_cash_flow_yield` | 0.45 |
| `free_cash_flow_yield` | 0.10 |
| `low_price_to_book` | 0.30 |
| `low_price_to_earnings` | 0.15 |

## Formal Validation Rerun

Outputs:

```text
validation_formal_v52b_enriched/
validation_formal_v52b_capex_policy/
validation_overfit_v52b_capex_policy/
```

### Original V5.2b On Enriched Panel

Result remained unchanged because official rows are mostly after the research panel’s last full rebalance period:

| Item | Result |
| --- | ---: |
| Composite cumulative return | 646.02% |
| 2018 rolling return | -35.23% |
| 2024 rolling return | 4.59% |
| 2025 rolling return | 6.38% |

### V5.2b Capex-Policy Variant

| Item | Result |
| --- | ---: |
| Composite cumulative return | 689.75% |
| Positive period ratio | 59.09% |
| 2018 rolling return | -35.07% |
| 2024 rolling return | 7.44% |
| 2025 rolling return | 8.61% |
| 2026 partial rolling return | 12.03% |

Interpretation:

- FCF downweighting improved stability in weak recent years.
- OCF-primary construction is better aligned with the capex audit.
- 2018 remains unresolved and cannot be ignored.
- Top-5 concentration remains too strong to treat as acceptance evidence.

Overfit audit:

```text
status = needs_review
blocker_count = 0
```

Reason:

No daily returns or rebalance signals exist yet for platform-style checks. This is expected because the model has not been promoted to a platform replication candidate.

## PM Decision

V5.2b capex-policy is a better research variant than original V5.2b, but it is not yet a formal strategy candidate.

Current approved status:

```text
research_pit_validation_improved_but_business_tag_and_state_history_blocked
```

Remaining blockers:

- official raw-coal output / inventory history is not complete for 2015-2026;
- official thermal coal price history is not complete for 2015-2026;
- coal business tags still lack segment evidence;
- 2018 failure remains unresolved;
- platform-style overfit checks require daily returns and rebalance signals after PM approval.

Next allowed work:

1. fill historical NBS / licensed coal state rows;
2. fill segment evidence for 37 company business tags;
3. rerun capex-policy formal validation;
4. only then decide whether to promote to `formal_strategy_candidate`.

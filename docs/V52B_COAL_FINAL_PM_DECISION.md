# V5.2b Coal Final PM Decision

Date: 2026-07-16

Project:

```text
V5.2b Coal Cash-Flow Cycle Value / Capex Policy
```

Final status:

```text
workflow_replication_passed_strategy_candidate_failed
```

Not status:

```text
formal_strategy_candidate
platform_replication_candidate
accepted_strategy
```

## Work Completed

This loop followed the approved order:

1. supplement NBS historical coal-state data;
2. supplement coal-company segment business evidence;
3. rerun the capex-policy branch;
4. make a PM decision.

## NBS Historical Coal-State Data

Generated:

```text
数据库/processed/coal_external_state/coal_nbs_historical_state_import_template.csv
数据库/processed/coal_external_state/coal_external_state_formal_candidate.csv
```

The NBS historical import template covers 2015-2026:

| Metric | Frequency template | Status |
| --- | --- | --- |
| Raw coal output / YoY | monthly | manual official import required |
| Thermal coal price | early / middle / late month | manual official import required |
| Coking coal price | early / middle / late month | manual official import required |

Template rows:

```text
966
```

Formal state candidate coverage:

| Metric | PIT usable months |
| --- | ---: |
| `coal_inventory_or_output_state` | 1 |
| `thermal_coal_price_state` | 92 |
| `coking_coal_price_state` | 160 |

Decision:

```text
NBS data path is prepared, but formal history is not complete.
```

Primary official sources:

- NBS energy production release: https://www.stats.gov.cn/sj/zxfb/202606/t20260616_1963948.html
- NBS production-material circulation price release: https://www.stats.gov.cn/sj/zxfb/202606/t20260623_1963989.html

## Coal Segment Business Evidence

Generated:

```text
数据库/processed/coal_business_tags/coal_segment_business_evidence_template.csv
数据库/manifests/coal_segment_evidence_audit/
```

Evidence audit:

| Item | Value |
| --- | ---: |
| Report disclosure rows | 859 |
| Segment evidence rows | 859 |
| PIT usable rows | 0 |
| Complete rows | 0 |
| Covered company count | 0 |
| Status | blocked |

Decision:

```text
The disclosure-date layer is complete enough for workflow use, but business segment evidence is still absent.
```

Business tags such as:

```text
core_coal
mixed_power_coal
mixed_coal_chemical
integrated_coal_power_transport
```

must not be treated as formal PIT tags until segment revenue / profit evidence is filled.

## Capex-Policy Branch Rerun

Strategy:

```text
coal_cashflow_cycle_value_v52b_capex_policy
```

Panel:

```text
数据库/processed/coal_pit_panel_formal_candidate_state/panel.csv
```

Formal validation:

```text
validation_formal_v52b_capex_policy_formal_state/
```

Key result:

| Item | Result |
| --- | ---: |
| Composite cumulative return | 689.75% |
| Positive period ratio | 59.09% |
| 2018 rolling return | -35.07% |
| 2024 rolling return | 7.44% |
| 2025 rolling return | 8.61% |

Factor evidence:

| Factor | Mean IC | Mean RankIC | Positive IC ratio |
| --- | ---: | ---: | ---: |
| OCF yield | 0.1718 | 0.1458 | 68.18% |
| FCF yield | 0.1388 | 0.1075 | 65.91% |
| Low PB | 0.0661 | 0.1033 | 59.09% |
| Low PE | 0.0752 | 0.0725 | 52.27% |

Overfit audit:

```text
status = needs_review
blocker_count = 0
```

Reason:

Daily returns and rebalance signals are not present because PM did not approve platform replication.

## PM Decision

V5.2b Coal is not promoted.

Final decision:

```text
workflow_replication_passed_strategy_candidate_failed
```

Reason:

- V5 workflow successfully replicated to coal;
- Research / Quant / Engineering gates worked;
- Capex-policy branch improved stability;
- But required formal evidence is still incomplete;
- 2018 remains a material failure year;
- Historical return alone is not enough.

## What This Means

Coal is archived as:

```text
process-portability success, strategy-candidate failure
```

Engineering Agent must not produce JoinQuant strategy code for V5.2b.

Recommended next project:

```text
Start V5.3 on another nearby sector, or improve data-collection tooling before another cyclical sector.
```

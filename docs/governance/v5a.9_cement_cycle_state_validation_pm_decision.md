# V5a.9 Cement Cycle-State Validation PM Decision

Date: 2026-07-21  
Layer: research_pit_validation  
Owner: Project Manager Agent  
Status: workflow_replication_passed_strategy_candidate_failed

## Decision

V5a.9 tested the next queued broad-sector candidate: A-share cement manufacturing companies.

PM decision:

```text
cement_cycle_aware_ocf_low_vol_v5a9 is not an Engineering handoff.
```

The V5 workflow did replicate successfully:

- PIT cement universe was collected;
- low-volatility factors and real daily price inputs already existed;
- fxbaogao research search and paragraph screening produced a usable industry-state hypothesis;
- public cement-state proxy data was collected and joined to the panel;
- formal validation and state-bucket validation both completed.

But the model hypothesis did not pass.

## Evidence Summary

Formal validation:

| Test | Result |
| --- | ---: |
| Equal-weight cement universe | `-5.70%` |
| High OCF top 8 | `-29.85%` |
| Low-vol top 8 | `-18.14%` |
| High-dividend diagnostic top 8 | `-10.38%` |
| Low-PB diagnostic top 8 | `-13.18%` |
| OCF + low-vol composite top 8 | `-34.07%` |

Factor evidence:

| Factor | Mean IC | Mean RankIC | Positive IC Ratio |
| --- | ---: | ---: | ---: |
| `operating_cash_flow_yield` | `-0.1130` | `-0.1188` | `20.00%` |
| `low_vol_score` | `0.0404` | `0.0287` | `57.89%` |

Rolling validation:

| Window | Composite Return |
| --- | ---: |
| 2023 | `-6.21%` |
| 2024 | `-4.96%` |
| 2025 | `26.25%` |
| 2026 | `-22.65%` |

State-bucket diagnostic:

| Bucket | Periods | Composite Return |
| --- | ---: | ---: |
| All | 20 | `-34.07%` |
| Cycle guard pass | 9 | `-3.43%` |
| Cycle guard fail | 11 | `-31.73%` |

## Research Interpretation

Cement is not behaving like a clean dividend low-volatility / OCF sleeve in the 2021-2026 platform-reference window.

The result is useful because it separates two claims:

1. The cement cycle state matters.
2. The current stock-selection model does not work.

The state guard sharply reduces damage, but the model still does not create enough positive evidence. OCF yield has negative IC and RankIC, so the Research Agent must not reinterpret the weak model as a hidden success.

## Data Gate Review

New V5a.9 state inputs:

- cement price proxy: `akshare.macro_china_construction_price_index`;
- real-estate demand proxy: `akshare.macro_china_real_estate`;
- fixed-asset investment proxy: `akshare.macro_china_gdzctz`;
- energy / mineral cost proxy: `akshare.macro_china_qyspjg`;
- fxbaogao report search and selected paragraph records.

These inputs are acceptable for research diagnostics, but not enough for Engineering handoff.

Required before any future cement restart:

- reviewed cement spot price or cement price index history;
- cement output / clinker capacity utilization;
- regional cement price and demand split;
- coal / energy cost pressure;
- company-level regional exposure and cement revenue share;
- capex policy review distinguishing maintenance capex, environmental capex and underinvestment.

## PM Routing

Current status:

```text
workflow_replication_passed_strategy_candidate_failed
```

Next gate:

```text
archive_until_official_cement_cycle_state_and_business_exposure_repair
```

Allowed future work:

- data-source repair only;
- no Engineering handoff;
- no JoinQuant script;
- no return-driven tuning;
- no basket inclusion.

## Evidence Paths

- Spec: `examples/cement_cycle_aware_ocf_low_vol_v5a9_strategy.json`
- PIT panel: `数据库/processed/similar_sector_pit_panel_v55/building_materials_cement/panel.csv`
- State panel: `数据库/processed/cement_state_enriched_panel_v5a9/panel_with_cement_state.csv`
- Formal validation: `validation_formal_v5a9_cement_cycle_state/cement_cycle_aware_ocf_low_vol_v5a9/formal_validation_summary.json`
- State bucket validation: `validation_state_v5a9_cement/cement_cycle_aware_ocf_low_vol_v5a9/cement_state_bucket_validation_summary.json`
- Research report search: `research_reports/fxbaogao_v5a9_cement_state/`


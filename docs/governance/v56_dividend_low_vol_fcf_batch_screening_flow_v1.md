# V5.6 Dividend Low-Vol FCF Batch Screening Flow V1

Date: 2026-07-18

Owner:

```text
Project Manager Agent
```

Experiment layer:

```text
data_availability_gate
```

Status:

```text
first_stage_batch_screening_started
```

## Purpose

V5.6 is the first step toward a dividend low-volatility and free-cash-flow enhanced ETF-style basket.

This stage does not accept any strategy and does not tune returns. It only answers:

```text
Which sectors can enter the enhanced-basket candidate pool?
Which sectors need manual research?
Which sectors are blocked by data gates?
Which global modules must be built before formal basket construction?
```

## Flow Table

| Step | Owner | Input | Action | Output | PM Gate |
| --- | --- | --- | --- | --- | --- |
| 1 | Project Manager | Existing status registry | Build candidate sector list from prior sector tests | `config/dividend_low_vol_fcf_sector_candidates_v56.json` | Candidate list approved |
| 2 | Research Agent | Knowledge base and sector reports | Check industry knowledge, value trap logic, and sector-specific fields | Knowledge gate status per sector | Missing knowledge routed to Research |
| 3 | Project Manager | Candidate config and known evidence | Check PIT universe, business purity, dividend, FCF, benchmark, external-state burden | Data gate status per sector | Pass / manual research / blocked |
| 4 | Quant Validation Agent | Existing validation summaries | Read baseline, rolling, IC / RankIC, overfit status where available | Evidence summary | No return tuning allowed |
| 5 | Engineering Agent | Existing runner inventory | Check whether local daily, dividends, benchmark, and platform attribution can be reused | Engineering readiness status | Engineering only for frozen candidates |
| 6 | Project Manager | All sector rows | Classify sectors into core pool, observation pool, manual research pool, blocked pool | Batch screening report | V5.6 Stage-1 decision |
| 7 | Project Manager | Global missing modules | Decide next build tasks | Low-vol runner, basket constructor, weight caps, paper log | Move to V5.6 Stage-2 only after modules exist |

## Sector Classification Rules

| Result | Meaning | Allowed next action |
| --- | --- | --- |
| `ready_for_basket_shadow_pool` | Sector has strong prior evidence and can enter paper/basket observation once basket rules exist | Build basket module, no acceptance |
| `ready_for_batch_initial_validation` | Sector has enough data for first-pass validation but is not a formal candidate | Run batch validation |
| `basket_observation_only` | Sector has economic fit but sample size or specialist metrics limit formal IC use | Paper/basket observation only |
| `needs_manual_research_before_formal` | Sector needs operating-purity, tariff, field, or source repair | Research Agent repair |
| `blocked_by_cycle_data_gate` | Cyclical sector lacks commodity/output/inventory/spread PIT data | Do not model until data repaired |
| `blocked_by_data_gate` | Key PIT data or visibility is missing | Stop and repair data |

## First Candidate Set

| Sector | Initial PM Role |
| --- | --- |
| Bank | Core candidate |
| Utilities / electricity | Golden-template core candidate |
| Highway infrastructure | Core candidate |
| Port / rail infrastructure | Candidate after platform replication |
| Telecom operators | Observation candidate due to small sample |
| Gas / water operators | Manual research candidate |
| Insurance | Specialist observation candidate |
| Coal | Blocked observation pool |

## Global Missing Modules

V5.6 cannot become a true enhanced ETF workflow until these are implemented:

| Module | Why it matters |
| --- | --- |
| Low-volatility factor runner | Low-vol must be a selectable, PIT-safe factor, not only a performance metric |
| Cross-sector basket constructor | Current V5 is sector-by-sector; ETF-style basket needs cross-sector allocation |
| Sector and single-stock weight caps | Prevent overconcentration in small sectors such as telecom and insurance |
| Basket-level benchmark | Need dividend-low-vol / same-pool benchmark comparison |
| Basket paper-trading log | Future signals must be tracked at basket level |

## PM Rule

The first V5.6 stage permits broad traversal only at the screening layer.

Formal strategy candidacy still requires:

```text
Industry Knowledge Gate
Data Availability Gate
Formal Validation Gate
Engineering Replication Gate
PM Decision Gate
```

No sector is accepted because its 2021-2026 return is high.

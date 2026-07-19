# V5.7 Dividend Low-Vol OCF / FCF Coverage Workflow V1

Date: 2026-07-18

Owner:

```text
Project Manager Agent, Research Agent, Quant Validation Agent, Engineering Agent
```

Status:

```text
workflow_defined
stage1_batch_screening_ready
not_formal_modeling
not_accepted_strategy
```

## Objective

Build a repeatable industry-coverage process for a future ETF-like basket:

```text
Dividend + low volatility + operating cash-flow strength, with free cash-flow as an enhancement only when sector data quality is good.
```

V5.6c changed the core narrative:

```text
OCF is the current primary cross-sector factor.
Low-volatility is a risk / coverage guard.
Dividend yield is shareholder-return support.
FCF is a future enhancement, not a required core factor yet.
Low PB is not a basket-wide mainline.
```

## Flow Table

| Step | Stage | Owner | Input | Work | Output | PM Gate |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | Coverage universe map | Project Manager | Existing V5.1-V5.6 results, status registry | List candidate sectors by business model, cash-flow stability, dividend habit and data burden | Candidate sector coverage config | No modeling before sector is classified |
| 2 | Industry knowledge gate | Research Agent | Candidate sector list | Write business model, profit driver, risk variables, value-trap patterns and required fields | Knowledge artifacts | Missing knowledge blocks formal validation |
| 3 | Data availability gate | Project Manager + Engineering | Local database, JQData/DataJQ, manual source register | Check PIT universe, financial fields, dividend data, low-vol price history, sector-specific fields | Sector screening packet | Failed data gate blocks modeling |
| 4 | Initial PIT panel | Engineering Agent | Passed or repairable sectors | Build PIT panel and real daily price/dividend inputs | Panel, price, dividend files | No today-universe backfill |
| 5 | Research hypothesis | Research Agent | Knowledge + data coverage | Define sector-specific hypothesis and decide whether FCF is core, support, or rejected | Research proposal | No factor chosen by return alone |
| 6 | Quant validation | Quant Agent | PIT panel + hypothesis | Run baseline, IC/RankIC, rolling, ablation, robustness and weak-year analysis | Formal validation packet | Must pass statistical and economic logic checks |
| 7 | Basket eligibility | Project Manager | Validation packet + sector status | Mark sector as core sleeve, observation sleeve, manual-research sleeve, or blocked | Basket eligibility decision | No accepted strategy status |
| 8 | Basket construction | Engineering Agent | Eligible sleeves | Build capped basket signals with sector caps, stock caps, cash remainder, no renormalization breach | Rebalance signals | Sector cap must pass |
| 9 | Local daily simulation | Engineering Agent | Signals, real open/close, dividends, stock actions | Generate daily NAV, holdings, cash, trades, dividend and action logs | Local daily packet | Not platform replication |
| 10 | Basket formal validation | Quant Agent | Basket signals + combined PIT panel | Run IC/RankIC, rolling, true ablation, failure attribution and overfit audit | Basket validation packet | 2021-2026 remains confirmation context |
| 11 | PM decision | Project Manager | All packets | Promote to paper trading, return to Research, keep observation, or block | Status registry update | Historical performance alone is insufficient |
| 12 | Forward / paper trading | Project Manager + Engineering | Fresh PIT data after confirmation window | Record future signals, selected stocks, factor values and risk notes | Paper trading log | Required before acceptance |

## Candidate Sector Tiers

### Tier A: Current Basket Mainline

| Sector | Role | Reason |
| --- | --- | --- |
| Bank | Core financial dividend sleeve | V3 platform replication passed; dividend and OCF logic usable |
| Utilities / electricity | Golden template | V5.1f is the strongest workflow template |
| Highway infrastructure | Stable cash-flow sleeve | V5.4h passed reviewed operating-data workflow |
| Port / rail infrastructure | Stable cash-flow candidate | V5.5j passed reviewed business-source repair |

### Tier B: Next Expansion Candidates

| Sector | Role | First Gate |
| --- | --- | --- |
| Telecom operators | Observation sleeve | Sample too small; use basket evidence, not broad IC |
| Gas / water operators | Manual research candidate | Separate true operators from engineering / project companies |
| Airport / toll-like transportation operators | Observation candidate | Traffic recovery and concession/policy data required |
| Oil / gas pipeline and integrated energy operators | Cycle-aware candidate | Commodity and price-spread state required |

### Tier C: Watchlist Only

| Sector | Reason |
| --- | --- |
| Coal | Cycle data gate remains incomplete |
| Insurance | Requires EV/NBV/P/EV specialist data; not generic FCF basket |
| Consumer staples | Cash flow can be strong, but dividend-low-vol profile must be screened first |
| Pharma / medical services | Policy and pipeline risk require specialist knowledge gate |
| Environmental project companies | Receivables and project revenue can create cash-flow traps |

## Stage 1 Execution Rule

Stage 1 may only classify sectors:

```text
ready_for_basket_shadow_pool
ready_for_batch_initial_validation
needs_manual_research_before_formal
basket_observation_only
blocked_by_data_gate
blocked_by_cycle_data_gate
```

Stage 1 must not produce:

```text
accepted_strategy
live_trading_approved
platform_replication_passed
```

## PM Hard Rules

- FCF cannot be a basket-wide core factor until coverage and capex accounting are proven by sector.
- Low PB cannot return to basket-wide scoring unless new formal validation overturns V5.6 evidence.
- Cyclical sectors require commodity price, output/inventory, spread and PIT business-exposure data before modeling.
- Small-sample sectors can be observation sleeves, not IC-proven standalone strategies.
- The basket must keep unallocated weight as cash if cap-constrained selection cannot fill target count.

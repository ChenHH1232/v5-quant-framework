# V5a.9 Food/Beverage Research Repair PM Decision

Date: 2026-07-22

Layer: `research_pit_validation`

Owner: Project Manager Agent

## Decision

V5a.9 completed the food/beverage Research repair loop and found one candidate that can enter Engineering local daily simulation:

`food_beverage_packaged_food_ocf_quality_v5a9a`

This is not an accepted strategy, not a platform replication candidate, and not a V57f sleeve. It may only enter:

`engineering_local_daily_simulation_only_no_tuning`

## Detailed Flow Table

| Stage | Owner | Input | Action | Output | Gate | Status |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | Project Manager Agent | V5a.6 / V5a.7 / V5a.8 evidence | Confirm broad food/beverage is too mixed | Repair scope | `subsector_only` | completed |
| 2 | Research Agent | Business model map | Define packaged-food candidate: condiments + snack food, excluding liquor/dairy/processing | Fixed hypothesis | `no_return_tuning` | completed |
| 3 | Research Agent | V5a.6 working-capital PIT panel | Build unguarded and fixed-guard candidate panels | Candidate panels | `PIT_visible_fields_only` | completed |
| 4 | Quant Validation Agent | Candidate panels + specs | Run formal validation, rolling, IC/RankIC, ablation and robustness | Formal packets | `research_pit_validation` | completed |
| 5 | Project Manager Agent | Formal packets | Apply sample-width, stability and matched-baseline engineering gate | PM decision | `no_engineering_without_gate` | completed |
| 6 | Project Manager Agent | `food_beverage_engineering_handoff_ready` | Route to Engineering | Local daily simulation only | `no_tuning_no_joinquant` | ready |

## Candidate Results

| Candidate | PM Gate | Rows | Securities | Selection | Equal Weight | Candidate | RankIC | Decision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `food_beverage_packaged_food_ocf_quality_v5a9a` | `engineering_handoff_candidate` | 634 | 38 | 8 | -17.20% | 9.40% | 0.0293 | Engineering local daily only |
| `food_beverage_packaged_food_high_ocf_wc_guard_v5a9b` | `research_repair_blocked` | 346 | 25 | 6 | -9.40% | -6.40% | 0.0525 | Diagnostic only; cumulative return is still negative |

## PM Interpretation

The repair worked because Research Agent stopped treating food/beverage as one sector and also stopped forcing the small condiments-only specialist sleeve.

The current best hypothesis is:

`branded packaged food = condiments + snack food`

with:

- OCF yield as the main factor;
- OCF-to-net-profit as a cash-conversion support factor;
- working-capital pressure kept as diagnostic, not a required guard for Engineering.

## Engineering Scope

Engineering Agent may now run local daily simulation for `food_beverage_packaged_food_ocf_quality_v5a9a` only.

Required outputs:

- daily returns;
- holdings;
- trades;
- real cash dividends;
- cash log;
- rebalance signals;
- `rebalance_order_health`;
- signal coverage check for every formal rebalance date.

## Blocked Actions

- Do not add food/beverage to V57f.
- Do not tune factor weights, selection count, timing, or subindustry membership.
- Do not start JoinQuant platform replication.
- Do not accept the strategy based on 2021-2026 results.
- Do not promote the guarded V5a.9b variant unless Research supplies a new forward-looking state rationale.

## Next Gate

`engineering_local_daily_simulation_only_no_tuning`

# V5a.9 Food/Beverage Research Repair

- Status: `food_beverage_engineering_handoff_ready`
- Next gate: `engineering_local_daily_simulation_only_no_tuning`

## Detailed Flow Table

| Stage | Owner | Input | Action | Output | Gate | Status |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | Project Manager Agent | `V5a.6 / V5a.7 / V5a.8 evidence` | Confirm parent food/beverage cannot be modeled as one pool | `repair scope` | `subsector_only` | `completed` |
| 2 | Research Agent | `business model map` | Define packaged-food candidate: condiments + snack food, excluding liquor/dairy/processing | `fixed hypothesis` | `no_return_tuning` | `completed` |
| 3 | Research Agent | `working-capital state panel` | Build unguarded and fixed-guard PIT panels | `candidate panels` | `PIT_visible_fields_only` | `completed` |
| 4 | Quant Validation Agent | `candidate panels + specs` | Run formal validation, rolling, IC/RankIC, ablation and robustness | `formal packets` | `research_pit_validation` | `completed` |
| 5 | Project Manager Agent | `formal packets` | Apply sample-width, stability and matched-baseline engineering gate | `PM decision` | `no_engineering_without_gate` | `completed` |
| 6 | Project Manager Agent | `food_beverage_engineering_handoff_ready` | Route next owner | `engineering_local_daily_simulation_only_no_tuning` | `stage_gate` | `completed` |

## Candidate Results

| Strategy | Rows | Securities | Selection | Equal | Candidate | RankIC | Gate | Blocker |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `food_beverage_packaged_food_ocf_quality_v5a9a` | 634 | 38 | 8 | -0.17201532190673452 | 0.09395689264963503 | 0.029299183033703158 | `engineering_handoff_candidate` |  |
| `food_beverage_packaged_food_high_ocf_wc_guard_v5a9b` | 346 | 25 | 6 | -0.09395068150695496 | -0.06398707700738815 | 0.052479022027413474 | `research_repair_blocked` | Candidate cumulative return is not positive; keep as diagnostic rather than Engineering handoff. |

## PM Rules

- This is Research/Quant repair only; it cannot accept a strategy.
- Food/beverage may enter Engineering only if a subsector/business-state hypothesis has enough PIT sample width and stable evidence.
- Do not tune factor weights, selection count, timing or subindustry membership based on 2021-2026 returns.
- Do not send small-sample specialist watchlists to Engineering without a separate PM approval gate.

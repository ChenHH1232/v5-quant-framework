# V5a.6 Consumer Subsector Working-Capital PM Decision

Date: 2026-07-21

## Decision

V5a.6 completed the next queue item after the home-appliance repair: consumer-sector working-capital repair and subsector PIT validation.

The result is useful but not Engineering-ready:

- Food / beverage should not be modeled as one broad sector.
- Condiments and snack food show early OCF-quality research signals.
- Broad consumer staples also shows an OCF-quality signal, but the parent pool is too mixed to become a basket sleeve without a stricter business-quality screen.
- Pharma / medical services can produce OCF signals in biologics and selected pharma subsectors, but it requires R&D, procurement and policy-state gates before any ETF-sleeve candidacy.

No V5a.6 consumer strategy is a formal strategy candidate, platform replication candidate, paper-trading candidate or accepted strategy.

## New Runners

- `src/v5/consumer_working_capital_state_runner.py`
- `src/v5/consumer_subsector_validation_runner.py`

These runners make the consumer queue reusable:

1. Enrich a PIT sector panel with statement-derived inventory, receivables, gross margin, current ratio and working-capital pressure.
2. Split the sector by `sub_industry`.
3. Run the same OCF-quality research validation per subsector.
4. Route each subsector by evidence instead of manually picking winners.

## Data Gate

| Sector | Rows | Dates | Codes | Working-Capital Coverage | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| Food / beverage | `2290` | `20` | `135` | `~100%` | enriched |
| Consumer staples parent pool | `5132` | `20` | `295` | `~100%` | enriched |
| Pharma / medical services | `8704` | `20` | `490` | `~99%+` | enriched |

## Quant Routing

### Food / Beverage

| Subsector | PM Decision | Equal-Weight | OCF-Quality | Read |
| --- | --- | ---: | ---: | --- |
| Condiments | `research_signal_candidate_needs_state_review` | `-11.86%` | `15.97%` | Needs channel/inventory and valuation state |
| Snack food | `research_signal_candidate_needs_state_review` | `-21.80%` | `3.66%` | Weak but better than parent pool |
| Beverage / dairy | `rejected_subsector_ocf_quality_not_superior` | `-19.38%` | `-18.25%` | Not enough |
| Food processing | `rejected_subsector_ocf_quality_not_superior` | `-23.83%` | `-33.23%` | Reject current hypothesis |
| Liquor | `rejected_subsector_ocf_quality_not_superior` | `-63.87%` | `-64.49%` | OCF-quality does not solve valuation cycle |
| Non-liquor alcohol | `rejected_subsector_ocf_quality_not_superior` | `-14.04%` | `-5.92%` | Not enough |

### Consumer Staples Parent Pool

| Pool | PM Decision | Equal-Weight | OCF-Quality | Read |
| --- | --- | ---: | ---: | --- |
| JoinQuant primary consumption | `research_signal_candidate_needs_state_review` | `-16.61%` | `39.64%` | Signal exists, but the pool is too mixed for direct ETF sleeve construction |

### Pharma / Medical Services

| Subsector | PM Decision | Equal-Weight | OCF-Quality | Read |
| --- | --- | ---: | ---: | --- |
| Biologics | `research_signal_candidate_needs_state_review` | `-32.41%` | `31.99%` | Needs R&D and policy gate |
| Chemical pharma | `research_signal_only_unstable_rolling` | `35.50%` | `57.75%` | Signal exists but rolling instability blocks handoff |
| Traditional Chinese medicine | `research_signal_only_unstable_rolling` | `7.59%` | `29.04%` | Signal exists but rolling instability blocks handoff |
| Medical devices | `rejected_subsector_ocf_quality_not_superior` | `-25.24%` | `-50.41%` | Reject current hypothesis |
| Medical services | `rejected_subsector_ocf_quality_not_superior` | `-36.73%` | `-47.59%` | Reject current hypothesis |
| Pharma distribution | `rejected_subsector_ocf_quality_not_superior` | `-2.06%` | `-5.94%` | Reject current hypothesis |

## PM Read

V5a.6 confirms the value of the new batch process: the parent sectors looked weak or messy, but subsector routing extracted specific places where OCF-quality may matter.

The best next research candidates are:

1. Condiments.
2. Snack food.
3. Consumer staples strict quality subset.
4. Biologics, but only under a pharma-specific R&D / policy-state model.

The next step is not Engineering. The next step is a state-review loop for the candidate subsectors:

- channel inventory / receivables pressure;
- gross margin and price power;
- brand or product concentration;
- capex and reinvestment policy;
- valuation-state guard;
- for pharma, R&D capitalization / procurement / policy-risk state.

Only after one candidate passes those gates should Quant rerun formal validation and PM consider Engineering local daily simulation.


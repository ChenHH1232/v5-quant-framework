# v5a.1_broad_sector_coarse_screening_for_dividend_low_vol_ocf_fcf Batch Screening PM Report

Created at UTC: `2026-07-21T05:15:54+00:00`

## PM Decision

Stage 1 batch screening is completed. This report classifies sectors for the dividend low-volatility, OCF and sector-approved FCF basket path. It is not strategy acceptance.

## Decision Counts

| Decision | Count |
| --- | ---: |
| `basket_observation_only` | 2 |
| `blocked_by_cycle_data_gate` | 4 |
| `blocked_by_data_gate` | 2 |
| `excluded_by_business_model` | 7 |
| `low_priority_watchlist` | 7 |
| `needs_manual_research_before_formal` | 6 |
| `platform_replication_pending_before_basket` | 1 |
| `ready_for_basket_shadow_pool` | 4 |

## Sector Results

| Sector | Decision | Allowed next action | Key note |
| --- | --- | --- | --- |
| Bank | `ready_for_basket_shadow_pool` | include in basket shadow pool after basket rules and low-vol module exist | Core financial dividend sleeve; bank quality stays sector-specific. |
| Utilities / Electricity | `ready_for_basket_shadow_pool` | include in basket shadow pool after basket rules and low-vol module exist | Golden template; OCF and demand state dominate raw FCF. |
| Highway Infrastructure | `ready_for_basket_shadow_pool` | include in basket shadow pool after basket rules and low-vol module exist | Strong cash-flow sleeve; concession life stays value-trap context. |
| Port / Rail Infrastructure | `ready_for_basket_shadow_pool` | include in basket shadow pool after pending replication notes are resolved | Eligible for shadow basket but platform attribution remains pending. |
| Gas / Water Operators | `needs_manual_research_before_formal` | Research Agent repairs operating-purity and field evidence | Observation sleeve exists; deeper company-level tariff/pass-through data may be costly. |
| Telecom Operators | `basket_observation_only` | track as specialist or concentrated sleeve; do not run broad IC acceptance | Good fit but too few core names for broad IC standards. |
| Insurance | `basket_observation_only` | track as specialist or concentrated sleeve; do not run broad IC acceptance | Needs EV/NBV/P/EV and specialist state model; not generic FCF. |
| Securities / Brokerage | `low_priority_watchlist` | keep in broad watchlist; do not spend Quant/Engineering time before higher-priority lanes are exhausted | More market-beta/capital-market cycle than stable dividend low-vol cash flow. |
| Oil / Gas Pipeline and Integrated Energy | `platform_replication_pending_before_basket` | wait for platform exports and attribution; do not add to basket yet | Potential sleeve but cycle data and platform exports still gate inclusion. |
| Coal | `blocked_by_cycle_data_gate` | repair cycle-state and PIT business-exposure data only | Do not model until commodity output/inventory/price state gates pass. |
| Steel | `blocked_by_cycle_data_gate` | repair cycle-state and PIT business-exposure data only | Requires steel price, margin, output/inventory and product exposure state. |
| Nonferrous Metals | `blocked_by_cycle_data_gate` | repair cycle-state and PIT business-exposure data only | Needs metal price and business exposure PIT; high research cost. |
| Basic Chemicals | `low_priority_watchlist` | keep in broad watchlist; do not spend Quant/Engineering time before higher-priority lanes are exhausted | Too heterogeneous for first-pass generic basket without subsector split. |
| Building Materials / Cement | `needs_manual_research_before_formal` | Research Agent repairs operating-purity and field evidence | Could have cash-flow names but real-estate cycle exposure must be isolated. |
| Construction Engineering | `blocked_by_data_gate` | repair data before any modeling | Receivables and project cash-flow risk can create value traps. |
| Environmental / Project Operators | `blocked_by_data_gate` | repair data before any modeling | Potential value-trap cluster; data repair only. |
| Real Estate | `excluded_by_business_model` | exclude from this dividend low-volatility OCF/FCF path unless PM opens a new strategy family | Not suitable for current dividend low-vol OCF/FCF path. |
| Consumer Staples Cash-Flow Leaders | `needs_manual_research_before_formal` | Research Agent repairs operating-purity and field evidence | Likely useful second-wave candidate; needs brand/channel/working-capital review. |
| Food / Beverage | `needs_manual_research_before_formal` | Research Agent repairs operating-purity and field evidence | Could fit cash-flow quality, but valuation and channel cycles matter. |
| Home Appliances | `needs_manual_research_before_formal` | Research Agent repairs operating-purity and field evidence | Potential dividend/FCF sleeve; needs real-estate and export cycle context. |
| Textile / Apparel | `low_priority_watchlist` | keep in broad watchlist; do not spend Quant/Engineering time before higher-priority lanes are exhausted | Possible individual names, but sector quality is uneven. |
| Pharma / Medical Services | `needs_manual_research_before_formal` | Research Agent repairs operating-purity and field evidence | Needs specialist split; not first-wave basket sleeve. |
| Agriculture / Forestry / Fishery | `excluded_by_business_model` | exclude from this dividend low-volatility OCF/FCF path unless PM opens a new strategy family | Poor fit for stable dividend low-vol OCF/FCF basket. |
| Logistics / Express Delivery | `low_priority_watchlist` | keep in broad watchlist; do not spend Quant/Engineering time before higher-priority lanes are exhausted | More competitive/capex intensive than toll-road style infrastructure. |
| Shipping | `blocked_by_cycle_data_gate` | repair cycle-state and PIT business-exposure data only | Needs freight-rate state and fleet/capex cycle. |
| Retail / Commerce | `low_priority_watchlist` | keep in broad watchlist; do not spend Quant/Engineering time before higher-priority lanes are exhausted | Too mixed for first-wave generic cash-flow basket. |
| Media / Entertainment | `excluded_by_business_model` | exclude from this dividend low-volatility OCF/FCF path unless PM opens a new strategy family | Weak fit for dividend low-vol cash-flow ETF path. |
| Computer / Software | `excluded_by_business_model` | exclude from this dividend low-volatility OCF/FCF path unless PM opens a new strategy family | Not aligned with current dividend low-vol OCF/FCF mandate. |
| Electronics / Semiconductor | `excluded_by_business_model` | exclude from this dividend low-volatility OCF/FCF path unless PM opens a new strategy family | May need a growth/cycle framework, not this ETF mandate. |
| Auto and Parts | `low_priority_watchlist` | keep in broad watchlist; do not spend Quant/Engineering time before higher-priority lanes are exhausted | Some cash-flow names exist, but sector is too cycle/competition heavy for first wave. |
| Machinery / Equipment | `low_priority_watchlist` | keep in broad watchlist; do not spend Quant/Engineering time before higher-priority lanes are exhausted | Could be explored later with order-cycle variables. |
| Power Equipment / New Energy | `excluded_by_business_model` | exclude from this dividend low-volatility OCF/FCF path unless PM opens a new strategy family | Not first-pass fit for dividend low-vol cash-flow mandate. |
| Military / Defense | `excluded_by_business_model` | exclude from this dividend low-volatility OCF/FCF path unless PM opens a new strategy family | Requires a separate policy/project framework. |

## Global Missing Modules

- `automatic_industry_constituent_refresh`
- `uniform_pit_financial_panel_for_all_sectors`
- `uniform_real_daily_price_and_dividend_collection`
- `sector_specific_business_purity_templates`
- `sector_specific_fcf_capex_quality_templates`
- `batch_formal_validation_runner_for_approved_panels`

## PM Next Steps

1. Keep ready sectors in the shadow basket only after their PIT panels and low-vol factors are fresh.
2. Send manual-research sectors to Research Agent for business purity, industry knowledge and FCF/capex-quality gates.
3. Keep observation-only sectors out of broad IC acceptance unless PM approves a small-sample sleeve policy.
4. Keep blocked sectors out of modeling until their data gates are repaired.
5. Keep 2021-2026 as platform-confirmation context, not accepted-strategy evidence.

## Hard Rule

Historical performance alone is never sufficient evidence for accepting a strategy.

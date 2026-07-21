# V5 Sector Replication Batch PM Report

Created at UTC: `2026-07-21T05:15:54+00:00`

## Decision

The nearby-sector replication process is now routed as one batch. This is a PM routing packet, not model acceptance.

## Lane Counts

| Lane | Count |
| --- | ---: |
| `basket_core_shadow_pool` | 4 |
| `blocked_data_repair` | 13 |
| `manual_research_before_formal` | 6 |
| `observation_only` | 10 |

## Execution Queue

| Rank | Sector | Lane | Agent | Timebox | Next action | Stop condition |
| ---: | --- | --- | --- | ---: | --- | --- |
| 10 | Bank | `basket_core_shadow_pool` | Engineering Agent | 30 | Refresh PIT panels, low-vol factors, dividends, daily logs and platform-attribution inputs while keeping frozen strategy logic unchanged. | stop if frozen logic change is required or platform exports remain unavailable |
| 11 | Utilities / Electricity | `basket_core_shadow_pool` | Engineering Agent | 30 | Refresh PIT panels, low-vol factors, dividends, daily logs and platform-attribution inputs while keeping frozen strategy logic unchanged. | stop if frozen logic change is required or platform exports remain unavailable |
| 12 | Highway Infrastructure | `basket_core_shadow_pool` | Engineering Agent | 30 | Refresh PIT panels, low-vol factors, dividends, daily logs and platform-attribution inputs while keeping frozen strategy logic unchanged. | stop if frozen logic change is required or platform exports remain unavailable |
| 13 | Port / Rail Infrastructure | `basket_core_shadow_pool` | Engineering Agent | 30 | Refresh PIT panels, low-vol factors, dividends, daily logs and platform-attribution inputs while keeping frozen strategy logic unchanged. | stop if frozen logic change is required or platform exports remain unavailable |
| 20 | Building Materials / Cement | `manual_research_before_formal` | Research Agent | 60 | Build industry knowledge, business-purity evidence, PIT field map, FCF/capex-quality gate and source register before Quant validation. | stop after 2 loops without new evidence or if the next stage gate needs PM approval |
| 20 | Food / Beverage | `manual_research_before_formal` | Research Agent | 60 | Build industry knowledge, business-purity evidence, PIT field map, FCF/capex-quality gate and source register before Quant validation. | stop after 2 loops without new evidence or if the next stage gate needs PM approval |
| 20 | Gas / Water Operators | `manual_research_before_formal` | Research Agent | 60 | Build industry knowledge, business-purity evidence, PIT field map, FCF/capex-quality gate and source register before Quant validation. | stop after 2 loops without new evidence or if the next stage gate needs PM approval |
| 20 | Home Appliances | `manual_research_before_formal` | Research Agent | 60 | Build industry knowledge, business-purity evidence, PIT field map, FCF/capex-quality gate and source register before Quant validation. | stop after 2 loops without new evidence or if the next stage gate needs PM approval |
| 30 | Telecom Operators | `observation_only` | Project Manager Agent | 30 | Keep as observation sleeve, specialist sleeve, or paper-only tracker until PM approves a special sample policy. | stop if sample policy or specialist data is not approved |
| 40 | Auto and Parts | `observation_only` | Project Manager Agent | 30 | Keep as observation sleeve, specialist sleeve, or paper-only tracker until PM approves a special sample policy. | stop if sample policy or specialist data is not approved |
| 40 | Basic Chemicals | `observation_only` | Project Manager Agent | 30 | Keep as observation sleeve, specialist sleeve, or paper-only tracker until PM approves a special sample policy. | stop if sample policy or specialist data is not approved |
| 40 | Insurance | `observation_only` | Project Manager Agent | 30 | Keep as observation sleeve, specialist sleeve, or paper-only tracker until PM approves a special sample policy. | stop if sample policy or specialist data is not approved |
| 40 | Logistics / Express Delivery | `observation_only` | Project Manager Agent | 30 | Keep as observation sleeve, specialist sleeve, or paper-only tracker until PM approves a special sample policy. | stop if sample policy or specialist data is not approved |
| 40 | Machinery / Equipment | `observation_only` | Project Manager Agent | 30 | Keep as observation sleeve, specialist sleeve, or paper-only tracker until PM approves a special sample policy. | stop if sample policy or specialist data is not approved |
| 40 | Retail / Commerce | `observation_only` | Project Manager Agent | 30 | Keep as observation sleeve, specialist sleeve, or paper-only tracker until PM approves a special sample policy. | stop if sample policy or specialist data is not approved |
| 40 | Securities / Brokerage | `observation_only` | Project Manager Agent | 30 | Keep as observation sleeve, specialist sleeve, or paper-only tracker until PM approves a special sample policy. | stop if sample policy or specialist data is not approved |
| 40 | Textile / Apparel | `observation_only` | Project Manager Agent | 30 | Keep as observation sleeve, specialist sleeve, or paper-only tracker until PM approves a special sample policy. | stop if sample policy or specialist data is not approved |
| 50 | Oil / Gas Pipeline and Integrated Energy | `observation_only` | Project Manager Agent | 30 | Keep as observation sleeve, specialist sleeve, or paper-only tracker until PM approves a special sample policy. | stop if sample policy or specialist data is not approved |
| 60 | Consumer Staples Cash-Flow Leaders | `manual_research_before_formal` | Research Agent | 60 | Build industry knowledge, business-purity evidence, PIT field map, FCF/capex-quality gate and source register before Quant validation. | stop after 2 loops without new evidence or if the next stage gate needs PM approval |
| 70 | Pharma / Medical Services | `manual_research_before_formal` | Research Agent | 60 | Build industry knowledge, business-purity evidence, PIT field map, FCF/capex-quality gate and source register before Quant validation. | stop after 2 loops without new evidence or if the next stage gate needs PM approval |
| 90 | Agriculture / Forestry / Fishery | `blocked_data_repair` | Research Agent | 60 | Repair missing PIT data, external state data, business-exposure evidence or original-report review. | stop after 2 loops without new source evidence; archive blocker packet |
| 90 | Computer / Software | `blocked_data_repair` | Research Agent | 60 | Repair missing PIT data, external state data, business-exposure evidence or original-report review. | stop after 2 loops without new source evidence; archive blocker packet |
| 90 | Electronics / Semiconductor | `blocked_data_repair` | Research Agent | 60 | Repair missing PIT data, external state data, business-exposure evidence or original-report review. | stop after 2 loops without new source evidence; archive blocker packet |
| 90 | Environmental / Project Operators | `blocked_data_repair` | Research Agent | 60 | Repair missing PIT data, external state data, business-exposure evidence or original-report review. | stop after 2 loops without new source evidence; archive blocker packet |
| 90 | Media / Entertainment | `blocked_data_repair` | Research Agent | 60 | Repair missing PIT data, external state data, business-exposure evidence or original-report review. | stop after 2 loops without new source evidence; archive blocker packet |
| 90 | Military / Defense | `blocked_data_repair` | Research Agent | 60 | Repair missing PIT data, external state data, business-exposure evidence or original-report review. | stop after 2 loops without new source evidence; archive blocker packet |
| 90 | Power Equipment / New Energy | `blocked_data_repair` | Research Agent | 60 | Repair missing PIT data, external state data, business-exposure evidence or original-report review. | stop after 2 loops without new source evidence; archive blocker packet |
| 90 | Real Estate | `blocked_data_repair` | Research Agent | 60 | Repair missing PIT data, external state data, business-exposure evidence or original-report review. | stop after 2 loops without new source evidence; archive blocker packet |
| 91 | Coal | `blocked_data_repair` | Research Agent | 60 | Repair missing PIT data, external state data, business-exposure evidence or original-report review. | stop after 2 loops without new source evidence; archive blocker packet |
| 95 | Construction Engineering | `blocked_data_repair` | Research Agent | 60 | Repair missing PIT data, external state data, business-exposure evidence or original-report review. | stop after 2 loops without new source evidence; archive blocker packet |
| 95 | Nonferrous Metals | `blocked_data_repair` | Research Agent | 60 | Repair missing PIT data, external state data, business-exposure evidence or original-report review. | stop after 2 loops without new source evidence; archive blocker packet |
| 95 | Shipping | `blocked_data_repair` | Research Agent | 60 | Repair missing PIT data, external state data, business-exposure evidence or original-report review. | stop after 2 loops without new source evidence; archive blocker packet |
| 95 | Steel | `blocked_data_repair` | Research Agent | 60 | Repair missing PIT data, external state data, business-exposure evidence or original-report review. | stop after 2 loops without new source evidence; archive blocker packet |

## Hard Rules

- Batch traversal is allowed; strategy acceptance is not.
- Research Agent must pass industry knowledge and data availability gates before Quant validation.
- Quant Validation Agent must run baseline, IC/RankIC, rolling, ablation and robustness before Engineering handoff.
- Engineering Agent only handles frozen candidates and must output local daily simulation, dividends, trades, cash, holdings and rebalance_order_health.
- No sector may be promoted because historical return looks good.
- Two consecutive loops without new evidence produce a blocker or failure-return packet.

## Output Paths

- Screening summary: `sector_replication_batches_v5a1\broad_coarse_current\screening\sector_screening_summary.json`
- Roadmap summary: `sector_replication_batches_v5a1\broad_coarse_current\roadmap\sector_replication_roadmap_summary.json`
- Agent queue dir: `sector_replication_batches_v5a1\broad_coarse_current\roadmap\agent_queues`

# V5.8 Dividend Low-Vol Cash-Flow Sector Replication Roadmap

Created at UTC: `2026-07-21T05:15:54+00:00`

## PM Decision

Broad replication roadmap is active, but no new sector is promoted to formal modeling or acceptance by this packet.

## Core Factor Policy

- Primary: `operating_cash_flow_yield, low_volatility`
- Supporting: `dividend_yield, dividend_stability, cash_flow_coverage`
- Enhancement only after sector approval: `free_cash_flow_yield, capex_quality, sector_operating_state`
- Not current mainline: `low_pb_as_basket_wide_primary_factor, raw_free_cash_flow_without_capex_review, historical_return_selected_factors`

## Lane Counts

| Lane | Count |
| --- | ---: |
| `basket_core_shadow_pool` | 4 |
| `blocked_data_repair` | 13 |
| `manual_research_before_formal` | 6 |
| `observation_only` | 10 |

## Agent Work Queue

| Priority | Sector | Lane | Next Agent | Timebox | Graduation Gate |
| ---: | --- | --- | --- | ---: | --- |
| 10 | Bank | `basket_core_shadow_pool` | `Engineering Agent` | 30 | `paper_trading_record_or_platform_attribution_packet_completed` |
| 11 | Utilities / Electricity | `basket_core_shadow_pool` | `Engineering Agent` | 30 | `paper_trading_record_or_platform_attribution_packet_completed` |
| 12 | Highway Infrastructure | `basket_core_shadow_pool` | `Engineering Agent` | 30 | `paper_trading_record_or_platform_attribution_packet_completed` |
| 13 | Port / Rail Infrastructure | `basket_core_shadow_pool` | `Engineering Agent` | 30 | `paper_trading_record_or_platform_attribution_packet_completed` |
| 20 | Building Materials / Cement | `manual_research_before_formal` | `Research Agent` | 60 | `industry_knowledge_and_data_availability_gate_passed` |
| 20 | Food / Beverage | `manual_research_before_formal` | `Research Agent` | 60 | `industry_knowledge_and_data_availability_gate_passed` |
| 20 | Gas / Water Operators | `manual_research_before_formal` | `Research Agent` | 60 | `industry_knowledge_and_data_availability_gate_passed` |
| 20 | Home Appliances | `manual_research_before_formal` | `Research Agent` | 60 | `industry_knowledge_and_data_availability_gate_passed` |
| 30 | Telecom Operators | `observation_only` | `Project Manager Agent` | 30 | `PM_approves_specialist_or_small_sample_policy` |
| 40 | Auto and Parts | `observation_only` | `Project Manager Agent` | 30 | `PM_priority_upgrade_before_research_or_validation` |
| 40 | Basic Chemicals | `observation_only` | `Project Manager Agent` | 30 | `PM_priority_upgrade_before_research_or_validation` |
| 40 | Insurance | `observation_only` | `Project Manager Agent` | 30 | `PM_approves_specialist_or_small_sample_policy` |
| 40 | Logistics / Express Delivery | `observation_only` | `Project Manager Agent` | 30 | `PM_priority_upgrade_before_research_or_validation` |
| 40 | Machinery / Equipment | `observation_only` | `Project Manager Agent` | 30 | `PM_priority_upgrade_before_research_or_validation` |
| 40 | Retail / Commerce | `observation_only` | `Project Manager Agent` | 30 | `PM_priority_upgrade_before_research_or_validation` |
| 40 | Securities / Brokerage | `observation_only` | `Project Manager Agent` | 30 | `PM_priority_upgrade_before_research_or_validation` |
| 40 | Textile / Apparel | `observation_only` | `Project Manager Agent` | 30 | `PM_priority_upgrade_before_research_or_validation` |
| 50 | Oil / Gas Pipeline and Integrated Energy | `observation_only` | `Project Manager Agent` | 30 | `PM_approves_specialist_or_small_sample_policy` |
| 60 | Consumer Staples Cash-Flow Leaders | `manual_research_before_formal` | `Research Agent` | 60 | `industry_knowledge_and_data_availability_gate_passed` |
| 70 | Pharma / Medical Services | `manual_research_before_formal` | `Research Agent` | 60 | `industry_knowledge_and_data_availability_gate_passed` |
| 90 | Agriculture / Forestry / Fishery | `blocked_data_repair` | `Research Agent` | 60 | `new_strategy_family_required_before_modeling` |
| 90 | Computer / Software | `blocked_data_repair` | `Research Agent` | 60 | `new_strategy_family_required_before_modeling` |
| 90 | Electronics / Semiconductor | `blocked_data_repair` | `Research Agent` | 60 | `new_strategy_family_required_before_modeling` |
| 90 | Environmental / Project Operators | `blocked_data_repair` | `Research Agent` | 60 | `hard_data_gate_repaired_before_modeling` |
| 90 | Media / Entertainment | `blocked_data_repair` | `Research Agent` | 60 | `new_strategy_family_required_before_modeling` |
| 90 | Military / Defense | `blocked_data_repair` | `Research Agent` | 60 | `new_strategy_family_required_before_modeling` |
| 90 | Power Equipment / New Energy | `blocked_data_repair` | `Research Agent` | 60 | `new_strategy_family_required_before_modeling` |
| 90 | Real Estate | `blocked_data_repair` | `Research Agent` | 60 | `new_strategy_family_required_before_modeling` |
| 91 | Coal | `blocked_data_repair` | `Research Agent` | 60 | `cycle_data_gate_passed_before_modeling` |
| 95 | Construction Engineering | `blocked_data_repair` | `Research Agent` | 60 | `hard_data_gate_repaired_before_modeling` |
| 95 | Nonferrous Metals | `blocked_data_repair` | `Research Agent` | 60 | `cycle_data_gate_passed_before_modeling` |
| 95 | Shipping | `blocked_data_repair` | `Research Agent` | 60 | `cycle_data_gate_passed_before_modeling` |
| 95 | Steel | `blocked_data_repair` | `Research Agent` | 60 | `cycle_data_gate_passed_before_modeling` |

## Agent Queue Files

| Agent | Queue file |
| --- | --- |
| `Project Manager Agent` | `sector_replication_batches_v5a1\broad_coarse_current\roadmap\agent_queues\project_manager_queue.csv` |
| `Research Agent` | `sector_replication_batches_v5a1\broad_coarse_current\roadmap\agent_queues\research_agent_queue.csv` |
| `Quant Validation Agent` | `sector_replication_batches_v5a1\broad_coarse_current\roadmap\agent_queues\quant_validation_agent_queue.csv` |
| `Engineering Agent` | `sector_replication_batches_v5a1\broad_coarse_current\roadmap\agent_queues\engineering_agent_queue.csv` |

## PM Operating Rules

- Keep V5.7f frozen; do not tune the current ETF basket while expanding coverage.
- Research Agent learns the industry first, then writes hypotheses; Quant Agent rejects or validates them with PIT evidence.
- Engineering Agent receives only frozen candidates or data-pipeline tasks; it does not create investment theory.
- Failed sectors are useful evidence when their blocker packet explains what is missing and when to restart.
- Historical performance alone is never sufficient evidence for accepting a strategy.

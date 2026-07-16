# Governance Record: v5_cyclical_sector_data_gate_v1

Date: 2026-07-16

Scope:

```text
coal, steel, non-ferrous metals, chemicals, energy and other commodity-cycle sectors
```

## Rule

PM must block formal strategy-candidate promotion for cyclical sectors unless four PIT-ready data layers exist.

Required layers:

1. commodity price state;
2. production / inventory / supply-demand state;
3. spread / margin state;
4. company business-exposure PIT tags.

## Required Metadata

Each state or exposure record must include:

```text
state_date
source_publication_date
visible_date
source_name
source_url_or_file
pit_usable
review_status
```

## Governance Effect

If any required layer is missing:

```text
data_probe_allowed
workflow_replication_allowed
formal_strategy_candidate_blocked
platform_replication_blocked
paper_trading_blocked
```

## Lesson From V5.2b

High historical return in a commodity cycle is not enough.

Without inventory / output or supply-demand evidence, a price-cycle explanation can become post-hoc storytelling.


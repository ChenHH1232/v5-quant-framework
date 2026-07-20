# Oil / Gas External-State Field Map V5.8a

Date: 2026-07-20

Owner:

```text
Research Agent
```

Status:

```text
required_before_quant
```

## Purpose

Oil / gas cannot use a simple dividend or FCF story without cycle-state evidence. The same factor can mean different things when crude oil is rising, refining spreads are compressed, gas pricing is regulated, or pipeline tariffs change.

This field map defines the minimum external-state panel required before V5.8a can move to Quant validation.

## Required State Fields

| Field | Meaning | Preferred PIT Source | Quant Use |
| --- | --- | --- | --- |
| `brent_price_state` | global crude oil price level / trend | Wind / Choice / public exchange data / reviewed manual import | state bucket, upstream exposure |
| `wti_price_state` | secondary crude oil price state | Wind / Choice / public exchange data / reviewed manual import | cross-check crude state |
| `domestic_gas_price_state` | domestic natural-gas price / city-gate or LNG state | NDRC, NBS, industry source, reviewed manual import | pipeline / gas operator state |
| `refining_spread_state` | downstream refining margin proxy | crude price plus product price proxy, reviewed source | refining / integrated names |
| `inventory_or_demand_state` | inventory, apparent consumption or demand pressure | NBS, industry association, reviewed manual import | weak-year explanation |
| `pipeline_tariff_policy_state` | regulated tariff or policy regime change | NDRC / company announcement / annual report | risk guard, exposure filter |
| `capex_cycle_state` | capex expansion / reserve replacement pressure | annual report, cash-flow statement, segment capex notes | FCF promotion audit |

## PIT Rules

Each row must carry:

```text
state_date
visible_date
source_publication_date
source_name
source_url
pit_usable
review_status
```

Rules:

1. `visible_date` must be no earlier than the source publication date.
2. Quant may only use state values where `visible_date <= trade_date`.
3. Backfilled vendor data must be marked `pit_usable=false` until publication timing is checked.
4. If only monthly data is available, use the first trading day after `visible_date`.
5. If a state field is unavailable, PM must decide whether to waive it or keep V5.8a blocked.

## Promotion Policy

`operating_cash_flow_yield` may enter the first baseline only after external state exists.

`free_cash_flow_yield` remains diagnostic until `capex_cycle_state` explains whether capex is maintenance, reserve replacement, policy-driven expansion or one-off project investment.

## Candidate Sources

Use these in priority order:

1. Licensed data terminal or API available to the project.
2. Official source such as NBS, NDRC or exchange-published commodity data.
3. Company annual reports and announcements.
4. Research reports as interpretation evidence, not as a raw market-data substitute.
5. Manual import template with reviewed source links.

Historical performance alone is never sufficient evidence for accepting a strategy.

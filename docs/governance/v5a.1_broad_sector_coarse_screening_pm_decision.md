# V5a.1 Broad Sector Coarse Screening PM Decision

Date: 2026-07-21

## Decision

V5a.1 broad-sector coarse screening is completed.

This is not model validation, not platform replication and not strategy acceptance. It is a first-pass PM routing layer designed to avoid getting stuck in one difficult sector before seeing the full opportunity map.

## Why This Exists

Single-sector exploration is useful after a candidate is promising, but it is a poor default search method. A single industry can consume a lot of time because of unknown data gaps, specialist accounting issues, external state variables or business-purity problems.

V5a.1 changes the default:

1. Screen many sectors first.
2. Estimate evidence availability and research cost.
3. Route sectors into lanes.
4. Only spend deep Research / Quant / Engineering time on the best second-pass candidates.

## Current Coverage

The current coarse screen covers 33 broad A-share sectors or sector clusters.

Lane counts:

- Core shadow basket: 4
- Manual research before formal validation: 6
- Observation only: 10
- Blocked / data repair: 13

## Best Second-Pass Candidates

These are worth Research Agent review before Quant validation:

- Building Materials / Cement
- Food / Beverage
- Gas / Water Operators
- Home Appliances
- Consumer Staples Cash-Flow Leaders
- Pharma / Medical Services

The goal is not to prove all six. The goal is to find which have enough PIT data and financial logic to justify formal validation.

## Current Core Shadow Basket

These remain the existing strongest sleeves:

- Bank
- Utilities / Electricity
- Highway Infrastructure
- Port / Rail Infrastructure

They should stay in the main enhanced ETF shadow basket unless a later clean forward or platform attribution result changes the PM decision.

## Observation Only

These may be useful but should not use broad cross-sectional acceptance standards yet:

- Telecom Operators
- Insurance
- Oil / Gas Pipeline and Integrated Energy
- Securities / Brokerage
- Auto and Parts
- Basic Chemicals
- Logistics / Express Delivery
- Machinery / Equipment
- Retail / Commerce
- Textile / Apparel

## Blocked Or Excluded

These are not ready for modeling under the current dividend low-volatility / OCF / FCF mandate:

- Coal
- Steel
- Nonferrous Metals
- Shipping
- Construction Engineering
- Environmental / Project Operators
- Real Estate
- Agriculture / Forestry / Fishery
- Computer / Software
- Electronics / Semiconductor
- Media / Entertainment
- Power Equipment / New Energy
- Military / Defense

Some of them may be valid under another strategy family, but not this one without a new PM-approved thesis.

## Naming Rule

This module is `V5a.1`. `V5` remains the project name. Do not create new main-version labels for workflow branches.

## Evidence

- Config: `config/v5a.1_broad_sector_coarse_screening.json`
- Batch packet: `sector_replication_batches_v5a1/broad_coarse_current/sector_replication_batch_packet.json`
- PM report: `sector_replication_batches_v5a1/broad_coarse_current/sector_replication_batch_pm_report.md`
- Roadmap: `sector_replication_batches_v5a1/broad_coarse_current/roadmap/sector_replication_roadmap.csv`
- Agent queues: `sector_replication_batches_v5a1/broad_coarse_current/roadmap/agent_queues/`
- Naming policy: `docs/governance/v5_naming_policy.md`

## Next Gate

Run Research Agent on the six second-pass candidates using a timebox. Stop after two loops without new evidence. Only candidates that pass the industry knowledge and data availability gates may enter Quant validation.

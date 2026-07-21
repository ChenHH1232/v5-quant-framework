# V5a.4 Research Queue Execution PM Decision

Date: 2026-07-21  
Layer: research_gate_execution  
Status: completed_first_research_queue_pass_not_quant_validation  
Owner: Project Manager Agent

## Decision

The V5a.3 Research Agent queue was executed for the seven `research_gate_before_quant_initial_validation` sectors.

No new sector is approved for Quant formal validation yet. The reason is not lack of theory; it is that the Research Agent queue exposed missing PIT data contracts, subsector splits, capex/FCF gates or external state variables.

This is still progress: the queue now has explicit blockers and restart conditions instead of open-ended "try a sector" work.

## Queue Result

| Sector | Research status | Quant permission | Next action |
| --- | --- | --- | --- |
| Port / Rail Infrastructure | Prior research / validation exists | No new Quant tuning | Refresh attribution and frozen inputs |
| Gas / Water Operators | Prior research / engineering exists, observation sleeve | No new Quant tuning | Keep observation / paper lane |
| Building Materials / Cement | New research framework added | No | Build cement PIT universe and cycle-state panel |
| Consumer Staples Cash-Flow Leaders | Existing framework, data gate blocked | No | Build subsector and working-capital data gate |
| Food / Beverage | New research framework added | No | Build subsector split and channel/inventory gate |
| Home Appliances | New research framework added | No | Build property/export/inventory state gate |
| Pharma / Medical Services | Existing framework, specialist data blocked | No | Build subsector, policy and R&D state gate |

## New Knowledge Added

- `knowledge/research_agent/factor_theory/building_materials_cement_cashflow_cycle_framework_v5a4.md`
- `knowledge/research_agent/factor_theory/food_beverage_cashflow_quality_framework_v5a4.md`
- `knowledge/research_agent/factor_theory/home_appliances_cashflow_dividend_framework_v5a4.md`
- `knowledge/research_agent/references/v5a4_research_queue_source_register.csv`

## PM Read

The best next data-building targets are:

1. Home appliances: likely best fit for OCF + low-vol + dividend + sector-approved FCF after inventory/property/export gates.
2. Food / beverage: strong candidate, but must split liquor and channel/inventory effects.
3. Consumer staples: overlaps with food/beverage, should be handled as either a broad defensive-consumer parent or a stricter quality subset.
4. Building materials / cement: only after cement cycle-state data exists.
5. Pharma: specialist route, not broad ETF core route yet.

Port/rail and gas/water are not "new research" work now; they are refresh, observation or attribution work.

## Required Before Quant

For any of the new second-pass consumer / cement / pharma sectors, Quant Agent cannot start until the following exist:

- PIT universe and subsector split.
- PIT financial panel with visible-date policy.
- Real daily open/close prices.
- Cash dividend events with visible dates.
- Low-volatility factors.
- Sector-specific capex / FCF quality gate.
- Sector-specific value-trap guard.

## Next Gate

Start V5a.5 data-gate build for:

```text
home_appliances
food_beverage
consumer_staples_cashflow
```

The goal is to see whether any of these can reach `ready_for_quant_initial_validation`.


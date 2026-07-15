# Bank High Dividend Sustainability V3 Test Plan

Date: 2026-07-15

## Experiment Layer

`research_pit_validation`

This is not a platform replication test and not a strategy acceptance decision.

## Research Question

Do high-dividend A-share banks produce more robust forward returns only when the dividend is supported by profitability, capital resilience, and provision strength?

## Background

Research Agent collected market-view hypotheses from Snowball and related public discussions. The views suggest:

- high dividend yield may be attractive when supported by stable ROE;
- high dividend yield may be a trap when caused by price decline or deteriorating fundamentals;
- PB should be interpreted together with ROE, dividend yield, and required return;
- bank ranking should avoid double-counting similar metrics;
- regional banks need additional quality controls.

All market-view evidence is `market_views` only. It cannot prove a strategy.

## Hypotheses

### H1: Raw High Dividend

Banks with higher trailing dividend yield have higher forward returns.

Expected risk:

- high yield may be caused by price collapse;
- dividend may be unsustainable;
- high yield may overlap with low PB.

### H2: Sustainable High Dividend

Dividend yield is more useful when combined with:

- visible ROE;
- core tier 1 capital adequacy;
- provision coverage;
- low PB as valuation support.

### H3: Value Trap Guard

High yield should be penalized when capital or provision support is weak.

## Data

Panel:

- `data/processed/bank_value_15y/panel.csv`

Available fields:

- `dividend_yield`
- `return_on_equity_ttm`
- `low_price_to_book`
- `provision_coverage_ratio`
- `core_tier_1_capital_adequacy_ratio`
- `total_return` / `future_return`

Known limitations:

- panel source is inherited from V4 migration and must remain `data_limited`;
- formal acceptance requires stronger point-in-time source labels;
- this test is evidence exploration, not final strategy promotion.

## Test Sequence

1. Create V3 strategy spec.
2. Validate spec contract.
3. Run factor validation:
   - IC;
   - RankIC;
   - positive IC ratio;
   - top-minus-bottom spread;
   - rolling fold behavior.
4. Run formal validation:
   - notice-date leakage audit;
   - rolling validation;
   - equal-weight all-bank baseline;
   - low-PB baseline;
   - composite candidate;
   - leave-one-factor-out ablation;
   - selection-count robustness;
   - value-weight perturbation robustness.
5. Produce decision memo:
   - research evidence;
   - data limitations;
   - whether to continue, revise, or reject.

## Acceptance Gate

V3 cannot be accepted from this test alone.

It may only be promoted to an engineering candidate if:

- dividend factor has positive rolling evidence;
- sustainable composite beats raw low-PB baseline on common sample;
- ablation shows dividend or quality layer contributes meaningfully;
- results are not driven by one year or one configuration;
- Quant Validation Agent confirms no blocker in price/dividend treatment.

## Output Directories

Expected generated outputs:

- `validation/bank_high_dividend_sustainability_v3/`
- `validation_formal/bank_high_dividend_sustainability_v3/`


# V5.1 Utilities Test-1 Initial Result

Date: 2026-07-16

Owner:

Project Manager Agent

Experiment layer:

```text
research_pit_validation
```

Strategy spec:

```text
examples/utilities_value_quality_v51_strategy.json
```

Panel:

```text
数据库/processed/utilities_pit_panel/panel.csv
```

Validation output:

```text
validation_formal_v51/utilities_value_quality_v51/
```

## Current Status

```text
research_pit_validation_completed_initial
```

Not status:

```text
formal_strategy_candidate
platform_replication_candidate
platform_replication_passed
accepted_strategy
```

## Data Scope

V5.1 Test-1 built a JoinQuant PIT utilities panel:

- sample window: 2017-01-01 to 2026-05-31;
- rebalance dates: 38 quarterly dates;
- rows: 3739;
- securities: 128;
- industry scope: thermal power, hydropower, nuclear power, grid, gas, water, heating / other utilities;
- excluded: wind, solar, other new-energy generation, municipal sanitation.

## Validation Summary

The formal validation runner completed:

- PIT visible-date audit;
- IC / RankIC;
- equal-utilities baseline;
- low-PB baseline;
- high-dividend baseline;
- ablation;
- rolling validation;
- robustness tests;
- weak-year review for 2018, 2021 and 2022.

## Factor Evidence

| Factor | Mean IC | Mean RankIC | Positive IC Ratio | Initial read |
| --- | ---: | ---: | ---: | --- |
| operating_cash_flow_yield | 0.0751 | 0.0884 | 0.7895 | strongest single-factor evidence |
| dividend_yield | 0.0478 | 0.0881 | 0.5789 | useful but weaker than cash-flow yield |
| low_price_to_book | 0.0138 | 0.1048 | 0.5263 | strong rank behavior and strong baseline performance |
| return_on_equity_ttm | 0.0090 | 0.0469 | 0.5263 | weak support factor |
| capex_burden | -0.0138 | 0.0181 | 0.5526 | weak and directionally mixed |
| operating_cash_flow_to_net_profit | -0.0167 | 0.0027 | 0.5000 | not useful in current form |
| interest_coverage | -0.0862 | -0.0005 | 0.4815 | sparse coverage; not usable as core factor |

## Baseline Evidence

| Case | Cumulative Return | Mean Period Return | Positive Ratio |
| --- | ---: | ---: | ---: |
| equal_weight_utilities | 0.4099 | 0.0137 | 0.5526 |
| low_pb_utilities_top10 | 1.9448 | 0.0354 | 0.5526 |
| high_dividend_utilities_top10 | 1.3529 | 0.0267 | 0.5789 |
| composite_current | 1.1816 | 0.0257 | 0.5789 |

## Rolling Evidence

The composite is not stable enough to promote:

- 2019: -3.13%;
- 2020: -2.02%;
- 2021: +59.13%;
- 2022: +4.89%;
- 2023: +12.12%;
- 2024: +19.67%;
- 2025: +33.95%;
- 2026 partial: +0.95%.

The result improves after 2021, but the early weak windows and benchmark failure against low-PB baseline prevent candidate promotion.

## Ablation Evidence

Current composite:

```text
cum_return = 1.1816
```

Dropping low PB improves the result:

```text
drop_low_price_to_book = 1.4276
```

Dropping dividend also improves the result:

```text
drop_dividend_yield = 1.3921
```

Dropping operating cash-flow yield hurts the result:

```text
drop_operating_cash_flow_yield = 0.8402
```

Interpretation:

The current weighting is not well specified. Operating cash-flow yield appears more valuable than the composite gives it credit for, while low PB and dividend should be tested as baselines or simpler factor combinations rather than assumed support factors.

## PM Decision

V5.1 Test-1 successfully proves that the V5 workflow can move outside bank-specific indicators:

```text
process_portability = passed_initial
```

But V5.1 Test-1 does not produce a formal strategy candidate:

```text
strategy_candidate_promotion = rejected_for_now
```

Reasons:

- current composite does not beat low-PB utilities baseline;
- current composite does not beat high-dividend utilities baseline;
- interest coverage has only 125 observations and is not reliable;
- common-sample tests shrink to 14 securities because of sparse interest coverage;
- cash-flow yield is promising, but the composite needs redesign before candidate review;
- field-level original announcement dates are not yet exported, only JoinQuant `get_fundamentals(date=trade_date)` PIT visibility.

## Next Quant Instruction

Do not proceed to Engineering Agent platform replication.

Quant Validation Agent should open V5.1 Test-2 with a narrower hypothesis:

```text
utilities_cashflow_value_v51b
```

Candidate redesign:

- keep low-PB and high-dividend as baselines;
- promote operating cash-flow yield to the main research factor;
- test dividend only when covered by operating cash flow;
- remove interest coverage from the core composite unless coverage can be repaired;
- move capex burden to risk-control / failure-mode analysis;
- add sub-industry split for thermal, hydro, gas and water.

## Governance Note

This result is research evidence only. It must not be used as platform replication evidence and must not trigger JoinQuant code generation.

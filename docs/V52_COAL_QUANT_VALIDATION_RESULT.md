# V5.2 Coal Quant Validation Result

Date: 2026-07-16

Owner:

Quant Validation Agent

Experiment layer:

```text
research_pit_validation
```

Status:

```text
research_pit_validation_completed_data_gap_not_formal_candidate
```

Not status:

```text
formal_strategy_candidate
platform_replication_candidate
platform_replication_passed
accepted_strategy
```

## Execution Scope

This step executed the V5.2 coal research validation preparation requested by PM:

- PIT coal stock universe;
- coal external state panel;
- baseline comparison;
- IC / RankIC;
- rolling validation;
- ablation;
- robustness;
- coal price state bucket validation.

No JoinQuant strategy code was generated.

## Data Built

### PIT Coal Panel

Local generated panel:

```text
数据库/processed/coal_pit_panel/panel.csv
```

Summary:

| Item | Value |
| --- | ---: |
| Rows | 1206 |
| Rebalance dates | 44 |
| Securities | 37 |
| Window | 2015-07-01 to 2026-05-31 |
| Return mode | pre-adjusted close-to-close total-return proxy |

The panel includes:

- JoinQuant/DataJQ PIT industry membership;
- stock-level valuation, dividend, cash-flow, capex, leverage fields;
- manual initial coal-business tags;
- external coal-state columns.

Important limitation:

```text
coal_business_tag still requires company-report visible-date audit before formal candidate promotion.
```

### External Coal State Panel

Local generated panel:

```text
数据库/processed/coal_external_state/coal_external_state.csv
```

Validation result:

| Metric | Usable rows | Status |
| --- | ---: | --- |
| `thermal_coal_price_state` | 91 | preliminary futures proxy; ends in 2022 |
| `coking_coal_price_state` | 159 | preliminary futures proxy |
| `coal_power_spread_state` | 88 | preliminary derived proxy |
| `coal_inventory_or_output_state` | 0 | missing required source |

PM interpretation:

```text
External state is sufficient for exploratory research validation, not sufficient for formal candidate promotion.
```

## Baseline Results

Validation output:

```text
validation_formal_v52/coal_high_dividend_cycle_value_v52/
```

| Baseline | Cumulative return | Positive period ratio | Interpretation |
| --- | ---: | ---: | --- |
| Equal-weight coal | 83.94% | 54.55% | sector beta baseline |
| High dividend top 8 | 54.35% | 52.27% | weak as standalone alpha |
| Low PB top 8 | 214.26% | 59.09% | meaningful value evidence |
| Low PE top 8 | 202.60% | 54.55% | useful but cycle-peak risk remains |
| High OCF yield top 8 | 461.79% | 54.55% | strongest baseline |
| High FCF yield top 8 | 440.41% | 56.82% | strong but capex definition must be audited |

First conclusion:

```text
V5.2 is not a simple high-dividend coal strategy. The first evidence points more toward cash-flow value plus valuation.
```

## IC / RankIC

| Factor | Mean IC | Mean RankIC | Positive IC ratio | Top-bottom spread |
| --- | ---: | ---: | ---: | ---: |
| Dividend yield | 0.0387 | 0.0308 | 63.64% | -0.28% |
| Low PB | 0.0661 | 0.1033 | 59.09% | 3.14% |
| Low PE | 0.0752 | 0.0725 | 52.27% | 2.41% |
| OCF yield | 0.1718 | 0.1458 | 68.18% | 5.59% |
| FCF yield | 0.1388 | 0.1075 | 65.91% | 4.68% |
| OCF / net profit | -0.0512 | 0.0282 | 38.64% | -0.63% |
| Asset-liability ratio | -0.0200 | 0.0396 | 47.73% | -1.59% |

Interpretation:

- Operating cash-flow yield is the strongest stock-level signal.
- Free cash-flow yield is promising but depends on capex field reliability.
- Dividend yield alone is not enough; spread is slightly negative.
- Leverage is not yet a clean alpha factor and should remain risk-control / filter candidate.

## Rolling Validation

The composite research candidate had:

- strong years: 2017, 2019, 2020, 2021, 2022, 2023;
- weak years: 2018, 2024;
- flat / mixed year: 2025;
- partial 2026 positive but not a decision basis.

Weak-year notes:

| Year | Result | Interpretation |
| --- | --- | --- |
| 2018 | composite -32.41% | sector down-cycle; model failed to avoid drawdown |
| 2024 | composite -5.09% | underperformed equal coal and low PB; high dividend/cash-flow selection may lag regime change |

## Ablation

Key ablation finding:

- Dropping `operating_cash_flow_yield` reduced cumulative return from 376.18% to 189.92%.
- Dropping `asset_liability_ratio` increased result to 581.49%.
- Dropping dividend yield increased result to 563.84%.

Interpretation:

```text
The current composite is not optimal and should not be accepted. Dividend and leverage weights may be hurting evidence.
```

## Robustness

Selection-count robustness:

| Selection count | Cumulative return |
| ---: | ---: |
| 5 | 843.64% |
| 8 | 376.18% |
| 10 | 387.02% |
| 12 | 338.20% |

Weight scaling for dividend / PB / OCF was stable around the current region:

- 0.8 scale: 386.46%;
- 1.0 scale: 376.18%;
- 1.2 scale: 402.45%.

Interpretation:

- Evidence is directionally robust for 8-12 names.
- Top-5 result is much higher and may indicate concentration risk or hidden overfit, so it cannot be used as acceptance evidence.

## External State Bucket Validation

### Coking Coal State

State coverage:

```text
44 / 44 rebalance dates
```

Best cases:

| Bucket | Best case | Cumulative return |
| --- | --- | ---: |
| All | High OCF yield top 8 | 461.79% |
| Weak coking coal state | Low PE top 8 | 83.39% |
| Strong coking coal state | High OCF yield top 8 | 250.44% |

State-conditioned IC highlights:

- In strong coking-coal state, OCF yield RankIC was 0.1730 and top-bottom spread was 9.29%.
- In weak coking-coal state, low PE had positive RankIC 0.2073.
- Dividend yield was negative in weak and mid states and only positive in strong state.

Interpretation:

```text
Coal price state helps explain when factor families behave differently, but it is not yet a validated timing rule.
```

### Thermal Coal State

State coverage shows values for 44 dates, but source quality is weaker because the futures proxy ends in 2022 and becomes stale afterward.

Interpretation:

```text
Thermal coal state cannot be used for formal validation until real spot / long-contract thermal coal data is collected for 2023-2026.
```

## PM Decision

V5.2 has enough evidence to continue research, but not enough to promote a formal strategy candidate.

Decision:

```text
revise_research_and_data_before_formal_candidate
```

Reasons:

1. Required inventory/output data is missing.
2. Thermal coal state proxy is incomplete after 2022.
3. Dividend yield, the original high-dividend hypothesis, is weak as a standalone factor.
4. Current composite is too dependent on cash-flow yield and may be improved by reducing dividend and leverage weights.
5. Manual coal-business tags require report-date audit before formal PIT acceptance.
6. 2018 and 2024 failure modes must be explained before candidate promotion.

## Next Quant Tasks

Approved next actions:

1. Collect official or licensed `coal_inventory_or_output_state`.
2. Replace thermal coal futures proxy with spot or long-contract thermal coal price series.
3. Run a revised V5.2b hypothesis centered on:
   - OCF yield;
   - FCF yield after capex audit;
   - low PB / low PE;
   - dividend as support or filter, not primary alpha.
4. Add mixed-business exclusion robustness as a first-class output.
5. Run weak-year failure analysis for 2018 and 2024 before any PM upgrade.

Blocked actions:

- no JoinQuant strategy code;
- no platform replication;
- no paper trading;
- no formal candidate promotion.

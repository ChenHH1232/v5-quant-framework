# V5.2b Coal Cash-Flow Cycle Value Result

Date: 2026-07-16

Owner:

Quant Validation Agent

Experiment layer:

```text
research_pit_validation
```

Status:

```text
research_pit_validation_strong_but_data_audit_blocked
```

Not status:

```text
formal_strategy_candidate
platform_replication_candidate
platform_replication_passed
accepted_strategy
```

## Purpose

V5.2b revises the first coal test from:

```text
Coal High-Dividend / Cycle Value
```

to:

```text
Coal Cash-Flow Value / Cycle-Aware Value
```

The high-dividend signal is downgraded to support/filter candidate. The core model now tests:

- operating cash-flow yield;
- free cash-flow yield;
- low PB;
- low PE.

## Data Update

External state panel was expanded with:

- `coal_oil_power_price_index_state`;
- `coal_oil_power_price_yoy_state`.

These come from AkShare / Eastmoney enterprise commodity price index and are treated as macro proxies only.

External state validation now has:

| Metric | Usable rows | Status |
| --- | ---: | --- |
| `coking_coal_price_state` | 159 | preliminary futures proxy |
| `thermal_coal_price_state` | 91 | preliminary futures proxy, weak after 2022 |
| `coal_power_spread_state` | 88 | derived proxy |
| `coal_oil_power_price_index_state` | 161 | macro proxy |
| `coal_inventory_or_output_state` | 0 | still missing |

PM interpretation:

```text
The data gap is reduced but not solved. Inventory/output remains a hard blocker.
```

## Baseline Results

Output:

```text
validation_formal_v52b/coal_cashflow_cycle_value_v52b/
```

| Case | Cumulative return | Positive period ratio |
| --- | ---: | ---: |
| Equal-weight coal | 83.94% | 54.55% |
| High dividend support reference | 54.35% | 52.27% |
| Low PB | 214.26% | 59.09% |
| Low PE | 202.60% | 54.55% |
| High OCF yield | 461.79% | 54.55% |
| High FCF yield | 440.41% | 56.82% |
| Core-coal OCF yield | 433.46% | 52.27% |
| V5.2b composite | 646.02% | 56.82% |

Interpretation:

```text
V5.2b improves the research composite by removing dividend and leverage from the main score.
```

## IC / RankIC

| Factor | Mean IC | Mean RankIC | Positive IC ratio | Top-bottom spread |
| --- | ---: | ---: | ---: | ---: |
| OCF yield | 0.1718 | 0.1458 | 68.18% | 5.59% |
| FCF yield | 0.1388 | 0.1075 | 65.91% | 4.68% |
| Low PB | 0.0661 | 0.1033 | 59.09% | 3.14% |
| Low PE | 0.0752 | 0.0725 | 52.27% | 2.41% |

Interpretation:

- OCF yield remains the strongest and cleanest factor.
- FCF yield is strong but still depends on capex definition quality.
- PB and PE provide supporting value evidence.

## Rolling Validation

| Year | V5.2b composite return | Interpretation |
| --- | ---: | --- |
| 2017 | 46.07% | strong |
| 2018 | -35.23% | failure year |
| 2019 | 19.78% | positive but weaker |
| 2020 | 57.45% | strong |
| 2021 | 89.01% | strong |
| 2022 | 47.46% | strong |
| 2023 | 41.74% | strong |
| 2024 | 4.59% | improved from V5.2 but still weak |
| 2025 | 6.38% | weak / mixed |
| 2026 partial | 9.44% | not decision evidence |

Compared with V5.2:

- 2024 improved from negative to positive.
- 2018 remains unresolved.
- 2025 remains weak.

## Ablation

| Case | Cumulative return |
| --- | ---: |
| V5.2b composite | 646.02% |
| Drop OCF yield | 592.87% |
| Drop FCF yield | 735.43% |
| Drop low PB | 613.54% |
| Drop low PE | 482.58% |

Interpretation:

- The result is not one-factor only.
- Low PE adds useful support to the composite.
- FCF yield may overlap with OCF yield or add capex noise; capex audit is required before formal candidate promotion.

## Robustness

| Selection count | Cumulative return |
| ---: | ---: |
| 5 | 1136.71% |
| 8 | 646.02% |
| 10 | 362.27% |
| 12 | 339.89% |

Interpretation:

The result survives 8-12 names, but top-5 concentration is much stronger and must be treated as concentration / overfit risk, not acceptance evidence.

Weight scale robustness:

- 0.8: 578.75%;
- 1.0: 646.02%;
- 1.2: 511.44%.

This is acceptable for research evidence, but not yet sufficient for final acceptance.

## State Bucket Results

### Coal-Oil-Power Price Index State

State coverage:

```text
44 / 44 rebalance dates
```

| Bucket | Best case | Cumulative return |
| --- | --- | ---: |
| Weak | Low PE | 120.01% |
| Mid | Low PB | 77.97% |
| Strong | OCF yield | 65.17% |
| All | OCF yield | 461.79% |

State-conditioned IC highlights:

- Weak state: OCF yield RankIC 0.1631, FCF yield RankIC 0.0921, low PE RankIC 0.1303.
- Mid state: OCF yield RankIC 0.1283, FCF yield RankIC 0.1008.
- Strong state: low PB RankIC 0.1954, OCF yield RankIC 0.1150.

Interpretation:

```text
Cycle state helps explain which value factor works better, but it is not yet an approved timing rule.
```

## Failure-Year Analysis

### 2018

V5.2b return:

```text
-35.23%
```

Observed:

- positive period ratio was 0%;
- model slightly beat equal-weight coal but underperformed low PB;
- selected names still had high OCF/FCF, meaning the cash-flow signal lagged the sector drawdown;
- failure likely reflects broad coal-sector beta / cycle downshift rather than only stock selection error.

Conclusion:

```text
2018 requires external cycle-risk control or state-aware exposure reduction before formal candidate promotion.
```

### 2024

V5.2b return:

```text
4.59%
```

Observed:

- improved from V5.2's negative result;
- beat equal-weight coal but still underperformed low PB;
- selected names had strong OCF/FCF and lower PB, but low PB alone captured the year better.

Conclusion:

```text
2024 is no longer a hard failure, but it shows the composite may dilute low-PB exposure in certain states.
```

## PM Decision

V5.2b shows stronger and cleaner evidence than V5.2.

However, PM does not approve formal strategy candidacy yet.

Decision:

```text
continue_research_pit_validation_not_formal_candidate
```

Reasons:

1. `coal_inventory_or_output_state` is still missing.
2. Thermal coal price still lacks a formal 2023-2026 spot / long-contract source.
3. Coal-power spread remains a proxy, not a real spread.
4. Coal-business tags still need visible-date audit from company disclosures.
5. 2018 failure is unresolved.
6. Top-5 concentration result suggests overfit / concentration risk.

## Approved Next Step

Continue V5.2b with a narrower task:

```text
V5.2b data-audit and failure-year repair
```

Required before formal candidate:

- official / licensed inventory or raw coal output state;
- formal thermal coal price series;
- business-tag visible-date audit;
- 2018 down-cycle risk explanation;
- capex field audit for FCF yield.

Blocked:

- no JoinQuant strategy code;
- no platform replication;
- no paper trading.

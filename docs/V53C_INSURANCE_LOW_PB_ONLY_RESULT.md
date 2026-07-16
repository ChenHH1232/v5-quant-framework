# V5.3c Insurance Low-PB-only Result

Date: 2026-07-17

Project:

```text
V5.3c Insurance Low-PB-only Formal Review
```

Strategy:

```text
insurance_low_pb_only_v53c
```

PM status:

```text
research_pit_validation_passed_engineering_handoff_allowed
```

Not status:

```text
accepted_strategy
paper_trading_ready
joinquant_code_ready
```

## Agent Collaboration

Research Agent approved a narrow V5.3c hypothesis:

```text
In A-share core insurance companies, low PB may capture excessive pessimism toward the balance sheet, long-rate sensitivity, investment returns and insurance franchise recovery.
```

Research constraints:

- use only `low_price_to_book` as score factor;
- do not use profit growth;
- do not use ROE as a positive quality factor;
- do not use dividend in the composite score;
- keep real 10Y government yield and equity state as review variables only;
- keep EV / NBV and solvency fields as future data-repair work.

Quant Validation Agent then ran formal PIT validation and approved engineering handoff preparation.

## Validation Inputs

Spec:

```text
examples / insurance_low_pb_only_v53c_strategy.json
```

Panel:

```text
database / processed / insurance_pit_panel_v53b / panel.csv
```

Output:

```text
validation_formal_v53c_insurance_low_pb_only / insurance_low_pb_only_v53c
```

## Formal Validation

| Item | Value |
| --- | ---: |
| Rows | 206 |
| Rebalance dates | 44 |
| PIT leakage violations | 0 |
| Checked rows | 205 |

Factor evidence:

| Factor | Mean IC | Mean RankIC | Positive IC ratio |
| --- | ---: | ---: | ---: |
| Low PB | 0.2004 | 0.2023 | 70.45% |

## Baseline Comparison

| Case | Cumulative return |
| --- | ---: |
| Equal-weight core insurance | 79.01% |
| High dividend top 3 reference | 86.56% |
| Low PB-only top 3 | 137.12% |
| V5.3b low PB + dividend | 114.17% |

PM read:

```text
Low PB-only is stronger than equal weight, dividend reference and V5.3b composite.
```

## Rolling Validation

| Year | Low PB-only return | Positive ratio |
| --- | ---: | ---: |
| 2017 | 60.15% | 75.00% |
| 2018 | -28.28% | 25.00% |
| 2019 | 58.23% | 75.00% |
| 2020 | 8.63% | 75.00% |
| 2021 | -24.28% | 0.00% |
| 2022 | -1.99% | 25.00% |
| 2023 | 1.48% | 50.00% |
| 2024 | 51.82% | 75.00% |
| 2025 | 42.97% | 50.00% |
| 2026 | -28.43% | 0.00% |

Failure-year read:

- 2021: low PB still loses money, but is slightly better than the full insurance universe.
- 2022: low PB nearly flat but underperforms the full insurance universe.
- 2026: low PB materially underperforms the full insurance universe and remains the main unresolved risk.

## Robustness

| Selection count | Cumulative return |
| ---: | ---: |
| 2 | 180.94% |
| 3 | 137.12% |
| 4 | 56.42% |
| 5 | 67.16% |

PM read:

```text
The low-PB signal is real enough to hand to Engineering, but the edge is concentrated. Engineering must test execution, concentration, turnover, benchmark choice and daily drawdown before platform replication.
```

## PM Decision

V5.3c passes the research PIT validation gate and may be handed to Engineering Agent for:

- local daily simulation preparation;
- insurance benchmark selection;
- rebalance signals / daily returns / holdings generation;
- platform replication readiness checks.

Blocked:

- accepted-strategy label;
- paper trading;
- JoinQuant strategy code;
- final platform replication.

Next gate:

```text
engineering_local_daily_simulation_preparation
```


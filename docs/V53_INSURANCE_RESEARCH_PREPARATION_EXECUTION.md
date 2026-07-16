# V5.3 Insurance Research Preparation Execution

Date: 2026-07-16

Project:

```text
V5.3 Insurance Value / Quality Process-Portability Test
```

Execution status:

```text
research_preparation_executed_data_probe_completed
```

Not status:

```text
research_pit_validation_started
formal_strategy_candidate
platform_replication_candidate
accepted_strategy
```

## What Was Executed

PM executed the approved preparation scope:

1. generated the V5.3 flow table;
2. confirmed Research Agent packet exists;
3. probed JoinQuant/DataJQ insurance industry membership;
4. probed `insurance_indicator` coverage;
5. probed generic valuation / finance field availability;
6. made a PM Gate-1 readiness decision.

Data probe output:

```text
数据库/processed/insurance_data_probe/
```

Files:

- `insurance_universe_snapshots.csv`
- `insurance_universe_codes.csv`
- `insurance_indicator_rows.csv`
- `insurance_indicator_year_coverage.csv`
- `insurance_indicator_field_coverage.csv`
- `insurance_generic_field_availability.csv`
- `insurance_data_probe_manifest.json`

## Universe Probe

Initial JoinQuant/DataJQ industry sources:

| Code | Source |
| --- | --- |
| `HY07110` | life and health insurance |
| `HY07111` | diversified insurance |
| `HY07112` | property and casualty insurance |
| `801194` | SW insurance II |
| `851941` | SW insurance III |
| `J68` | CSRC insurance |

Excluded financial industries:

| Code | Source |
| --- | --- |
| `HY07107` | securities company |
| `801193` | SW securities II |
| `J67` | CSRC capital market service |

Probe result:

| Item | Value |
| --- | ---: |
| Rebalance dates | 44 |
| Universe codes | 8 |
| Universe snapshot rows | 278 |
| Warnings | 0 |

Initial code list:

| Code | Initial subgroup | PM note |
| --- | --- | --- |
| `601318.XSHG` | insurance group | core review candidate |
| `601628.XSHG` | life insurance | core review candidate |
| `601601.XSHG` | insurance group | core review candidate |
| `601336.XSHG` | life insurance | core review candidate |
| `601319.XSHG` | P&C insurance group | core review candidate |
| `000627.XSHE` | insurance-led holding needs review | possible exclusion / special case |
| `600291.XSHG` | P&C insurance needs review | delisted / historical special case |
| `002423.XSHE` | manual review required | likely financial holding contamination |

PM interpretation:

```text
Universe is collectible, but formal universe is not approved until company-report business-exposure PIT review is complete.
```

## Insurance Indicator Probe

Detected JoinQuant table:

```text
insurance_indicator
```

Useful fields:

- `earned_premium`
- `earned_premium_growth_rate`
- `compensation_rate`
- `comprehensive_compensation_rate`
- `comprehensive_cost_ratio`
- `solvency_adequacy_ratio`
- `net_investment_rate_of_return`
- `total_investment_rate_of_return`
- `actual_capital`
- `minimum_capital`
- `investment_assets`
- `payoff_cost`
- `not_expired_duty_reserve`
- `outstanding_claims_reserve`
- `pubDate`
- `statDate`

Annual coverage:

| Source year | Covered codes | Universe codes | Coverage |
| --- | ---: | ---: | ---: |
| 2015 | 6 | 8 | 75.00% |
| 2016 | 6 | 8 | 75.00% |
| 2017 | 6 | 8 | 75.00% |
| 2018 | 7 | 8 | 87.50% |
| 2019 | 7 | 8 | 87.50% |
| 2020 | 7 | 8 | 87.50% |
| 2021 | 6 | 8 | 75.00% |
| 2022 | 6 | 8 | 75.00% |
| 2023 | 6 | 8 | 75.00% |
| 2024 | 0 | 8 | 0.00% |
| 2025 | 0 | 8 | 0.00% |

PM interpretation:

```text
insurance_indicator is useful but not sufficient for formal V5.3 without repairing 2024-2025 coverage or confirming API/statDate behavior.
```

## Field Coverage Finding

High-coverage insurance fields across returned rows:

| Field | Coverage |
| --- | ---: |
| `solvency_adequacy_ratio` | 89.47% |
| `total_investment_rate_of_return` | 89.47% |
| `investment_assets` | 91.23% |
| `payoff_cost` | 84.21% |
| `actual_capital` | 82.46% |
| `minimum_capital` | 82.46% |
| `earned_premium` | 82.46% |

Lower-coverage fields:

| Field | Coverage |
| --- | ---: |
| `earned_premium_growth_rate` | 35.09% |
| `comprehensive_cost_ratio` | 47.37% |
| `comprehensive_compensation_rate` | 47.37% |
| `not_expired_duty_reserve` | 42.11% |
| `outstanding_claims_reserve` | 42.11% |

Missing from `insurance_indicator`:

- embedded value;
- new business value;
- P/EV;
- surrender / persistency;
- detailed life-insurance channel quality.

These must come from annual reports, manual templates, Eastmoney/F10 first-pass extraction, or another reviewed data source.

## Generic Field Probe

Generic JoinQuant valuation and finance fields are available for baseline use.

Fields checked:

- `pb_ratio`
- `pe_ratio`
- `market_cap`
- `dividend_ratio`
- `roe`
- `inc_net_profit_year_on_year`
- `net_profit`
- `net_operate_cash_flow`
- `total_assets`
- `total_liability`

Coverage:

- 2020 and 2021: `8 / 8`
- 2024 and 2025: `7 / 8`

PM interpretation:

```text
Generic valuation baselines can be built, but insurance-quality validation cannot rely only on generic fields.
```

## PM Gate-1 Decision

Current decision:

```text
research_preparation_partially_passed_quant_validation_blocked_until_data_repairs
```

Approved next work:

- review the 8-code universe and decide formal insurance-led membership;
- repair or replace 2024-2025 `insurance_indicator` coverage;
- add report/manual extraction route for embedded value and new business value;
- build external rate/equity state panel;
- only then build a V5.3 PIT panel.

Blocked:

- formal validation;
- local strategy simulation;
- JoinQuant strategy code;
- paper trading.


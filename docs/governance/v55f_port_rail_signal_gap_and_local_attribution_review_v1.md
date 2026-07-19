# V5.5f Port / Rail 2021 Signal Gap And Local Attribution Review V1

Date: 2026-07-18

Owner:

```text
Project Manager Agent
Quant Validation Agent
Engineering Agent
```

Experiment layer:

```text
engineering_smoke_test_local_attribution
```

Strategy:

```text
port_rail_cashflow_value_operating_diagnostic_v55c
```

## PM Conclusion

The 2021 no-signal gap is explained.

It was caused by JoinQuant PIT industry membership coverage:

| Date | HY03155 railway transport | HY03159 port |
| --- | ---: | ---: |
| 2021-07-01 | 0 | 0 |
| 2021-10-08 | 0 | 0 |
| 2021-12-31 | 6 | 18 |
| 2022-01-04 | 6 | 18 |

Daily prices were available for the later 23-name port / rail pool on both 2021-07-01 and 2021-10-08.

Therefore the 2021 no-buy issue is not:

```text
order sizing;
100-share lot rounding;
cash shortage;
daily price absence;
strategy defensive timing;
trade execution failure.
```

It is a PIT universe coverage gap in the industry-classification source.

## Local Daily Attribution Result

Output directory:

```text
local_attribution_port_rail_v55f/port_rail_cashflow_value_operating_diagnostic_v55c
```

Generated files:

| File | Purpose |
| --- | --- |
| `local_daily_attribution_summary.json` | PM summary |
| `local_daily_attribution_report.md` | readable attribution report |
| `annual_attribution.csv` | calendar-year return / cash / dividend / turnover view |
| `rebalance_period_attribution.csv` | per-rebalance-period attribution |
| `top_loss_days.csv` | largest local daily losses |
| `top_gain_days.csv` | largest local daily gains |

Core numbers:

| Segment | Strategy | Benchmark proxy | Interpretation |
| --- | ---: | ---: | --- |
| 2021 pre-signal period | 0.00% | 22.55% | cash-only because PIT universe returned no members |
| 2022-01-04 to 2026-05-29 active period | 63.86% | -3.96% | local strategy mechanically active |
| Full local window | 63.86% | 17.69% | full-window excess is reduced by 2021 cash gap |

Active-period risk:

| Metric | Value |
| --- | ---: |
| Active invested days | 1064 |
| Average active cash weight | 0.85% |
| Active max drawdown | 20.20% |
| Drawdown interval | 2023-05-08 to 2024-01-22 |

Annual view:

| Year | Strategy | Benchmark | Dividend cash | PM note |
| --- | ---: | ---: | ---: | --- |
| 2021 | 0.00% | 22.55% | 0.00 | no signal due to PIT industry coverage |
| 2022 | 5.88% | -11.96% | 55,675.36 | active |
| 2023 | 10.17% | -7.69% | 58,109.83 | active |
| 2024 | 21.71% | 13.30% | 48,162.01 | active |
| 2025 | 10.70% | 6.27% | 53,749.88 | active |
| 2026 | 4.25% | -1.85% | 0.00 | partial year |

## PM Decision

V5.5c local daily engineering smoke test and local attribution review are complete.

The model may proceed to:

```text
local engineering review
2021 universe repair decision
operating evidence original-source review
```

The model may not proceed to:

```text
JoinQuant strategy code generation
platform replication
paper trading
accepted strategy
```

until the PM chooses one of the following 2021 policies:

| Policy | Meaning |
| --- | --- |
| repair PIT universe | Rebuild 2021 port / rail universe using original PIT evidence, similar to the highway V5.4h repair |
| disclose 2022-start limitation | Keep the formal local engineering window active from 2022-01-04 and disclose the 2021 source limitation |
| reject platform handoff | Stop V5.5c before platform replication if 2021 coverage cannot be justified |

## Next Gate

```text
V5.5g 2021 PIT universe repair decision + operating evidence review
```

Recommended PM path:

```text
repair PIT universe if original historical industry / segment evidence is easy to obtain;
otherwise disclose 2022-start limitation and keep V5.5c as a port-dominant local candidate, not a platform-ready strategy.
```

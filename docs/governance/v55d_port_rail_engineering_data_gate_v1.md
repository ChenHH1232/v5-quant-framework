# V5.5d Port / Rail Engineering Data Gate V1

Date: 2026-07-18

Owner:

```text
Project Manager Agent
```

Experiment layer:

```text
engineering_data_gate
```

Status:

```text
engineering_data_partially_passed
operating_evidence_review_blocked
no_engineering_handoff
```

## Scope

This gate checks whether `port_rail_cashflow_value_operating_diagnostic_v55c` can move from Research / Quant into Engineering.

PM answer:

```text
Not yet.
```

The model is a formal strategy candidate, but Engineering remains blocked until original operating evidence is reviewed.

## Automated Engineering Data

The automated data layer is ready for later Engineering work.

| Data item | Status | Evidence |
| --- | --- | --- |
| PIT research panel | pass | `数据库/processed/port_rail_operating_state_v55b/panel_operating_state.csv` |
| Real daily stock open / close | pass | `数据库/processed/port_rail_v55c_joinquant_real_daily_prices.csv` |
| Real cash dividends | pass | `数据库/processed/port_rail_v55c_joinquant_cash_dividends.csv` |
| Dividend tax treatment | pass | 20% tax, net cash per share generated |
| Benchmark daily price | partial_pass | `数据库/processed/port_rail_v55c_joinquant_real_benchmark_prices.csv` |
| Benchmark code | partial_pass | `516970.XSHG` infrastructure ETF |

Collection summary:

| Item | Count |
| --- | ---: |
| Stock codes | 23 |
| Daily price rows | 28244 |
| Cash dividend events | 130 |
| Benchmark rows | 1228 |

Warnings:

```text
none
```

## Benchmark Decision

Candidate benchmarks:

| Benchmark | Status | PM interpretation |
| --- | --- | --- |
| Same-pool equal-weight benchmark | research_primary | Best for PIT research comparison. |
| `516970.XSHG` 基建50 ETF | engineering_proxy | Tradable and covers the V5.5c window, but not pure port / rail. |
| `159666.XSHE` 交通运输 ETF | coverage_blocked | Listed 2023-02-13, too late for full 2022-2026 comparison. |
| Old transport indices such as `000945.XSHG` / `000957.XSHG` | blocked | Ended in 2020 in current JQData metadata. |

PM benchmark rule:

```text
Use same-pool equal-weight for research validation.
Use 516970.XSHG only as a tradable engineering proxy until a better pure transport benchmark is confirmed.
Do not claim 516970.XSHG is a pure port / rail benchmark.
```

## Operating Evidence Gate

Operating evidence is not ready.

Template generated:

```text
数据库/processed/port_rail_operating_evidence_v55d/port_rail_operating_evidence_manual_template.csv
```

Required fields:

| Field group | Required before Engineering? |
| --- | --- |
| port revenue share | yes |
| rail revenue share | yes |
| cargo throughput | yes for port names when disclosed |
| container throughput | yes for container port names when disclosed |
| rail freight volume | yes for rail names when disclosed |
| rail passenger volume | optional / subgroup dependent |
| tariff or pricing-policy evidence | yes where available |
| capex project commitments | yes |
| source title / source URL | yes |
| publish date / visible date | yes |
| original_announcement_checked | must be true |
| review_status | must be reviewed |
| pit_status | must be pit_usable or explicitly excluded |

Current state:

```text
23 rows generated.
0 rows reviewed.
23 rows need original announcement check.
```

## PM Decision

V5.5c status remains:

```text
formal_strategy_candidate
research_pit_validation_passed
engineering_blocked_until_operating_evidence_review
```

Engineering may not:

```text
run local daily simulation;
write JoinQuant strategy code;
start platform replication;
start paper trading.
```

Engineering may:

```text
maintain data collection tools;
validate daily price / dividend / benchmark files;
prepare operating evidence import checks.
```

## Next Action

Start:

```text
V5.5e Port / Rail Operating Evidence Review
```

Research Agent must review original annual reports / interim reports / official company disclosures for the 23 companies and promote rows to:

```text
pit_usable
original_announcement_checked=true
review_status=reviewed
```

Only after coverage is sufficient can PM approve Engineering handoff.


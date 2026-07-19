# V5.5a Similar-Sector Initial Model PM Decision V1

Date: 2026-07-18

Owner:

```text
Project Manager Agent
```

Experiment layer:

```text
research_pit_validation
```

Status:

```text
initial_model_screening_completed
no_strategy_accepted
no_engineering_replication_started
```

## Purpose

This run tests whether the V5 similar-sector replication workflow can build and validate first-pass models across three candidates:

```text
telecom_operators
gas_water_operators
port_rail_infrastructure
```

The goal is process evidence and hypothesis triage, not strategy acceptance.

## Data Collection

| Sector | Panel path | Rows | Dates | Codes | Data status |
| --- | --- | ---: | ---: | ---: | --- |
| Telecom operators | `数据库/processed/similar_sector_pit_panel_v55/telecom_operators/panel.csv` | 52 | 20 | 3 | collected |
| Gas / water operators | `数据库/processed/similar_sector_pit_panel_v55/gas_water_operators/panel.csv` | 830 | 20 | 45 | collected |
| Port / rail infrastructure | `数据库/processed/similar_sector_pit_panel_v55/port_rail_infrastructure/panel.csv` | 409 | 18 | 23 | collected |

Collection note:

```text
JQData allows only one concurrent connection for the current account. Similar-sector data collection must run serially.
```

## Formal Validation Outputs

| Sector | Strategy ID | Validation packet |
| --- | --- | --- |
| Telecom operators | `telecom_operators_cashflow_dividend_v55a` | `validation_formal_v55a_similar_sectors/telecom_operators_cashflow_dividend_v55a/formal_validation_summary.json` |
| Gas / water operators | `gas_water_cashflow_dividend_v55a` | `validation_formal_v55a_similar_sectors/gas_water_cashflow_dividend_v55a/formal_validation_summary.json` |
| Port / rail infrastructure | `port_rail_cashflow_dividend_v55a` | `validation_formal_v55a_similar_sectors/port_rail_cashflow_dividend_v55a/formal_validation_summary.json` |

All three passed the current PIT visible-date audit:

```text
future_notice_violations = 0
```

Important limitation:

```text
The panel uses JoinQuant get_fundamentals(date=trade_date) as PIT visibility. Field-level original announcement dates are not exported yet.
```

## Telecom Operators

Initial model:

```text
Dividend yield + operating cash-flow yield + low PB + lower capex burden
```

Evidence snapshot:

| Check | Result |
| --- | --- |
| Rows / codes | 52 rows / 3 codes |
| Composite cumulative return | 48.93% |
| Equal-weight baseline | 25.24% |
| High-dividend baseline | 26.07% |
| Rolling 2023 | 8.00% |
| Rolling 2024 | 30.86% |
| Rolling 2025 | -1.86% |
| Rolling 2026 | -17.73% |
| Strongest IC signal | dividend_yield, mean RankIC 0.3333 |
| Main weakness | sample size and 2026 failure |

PM decision:

```text
research_signal_only
not_formal_strategy_candidate
```

Interpretation:

Telecom fits the dividend / cash-flow direction, but the A-share core universe has only three operators. The model is closer to a concentrated basket hypothesis than a statistically robust cross-sectional factor strategy.

Next Research Agent tasks:

```text
Add ARPU, mobile / broadband subscriber count, capex cycle, EBITDA margin and enterprise-service revenue share.
Decide whether telecom should be evaluated as a basket strategy rather than IC-driven stock selection.
Explain 2026 weakness before any Engineering handoff.
```

## Gas / Water Operators

Initial model:

```text
Dividend yield + operating cash-flow yield + low PB + interest coverage + lower capex burden
```

Evidence snapshot:

| Check | Result |
| --- | --- |
| Rows / codes | 830 rows / 45 codes |
| Composite cumulative return | 47.95% |
| Equal-weight baseline | 42.54% |
| High-dividend baseline | 48.08% |
| Rolling 2023 | 20.61% |
| Rolling 2024 | 15.19% |
| Rolling 2025 | 5.00% |
| Rolling 2026 | -12.86% |
| IC quality | weak and mixed |
| Main weakness | composite does not beat high-dividend baseline; 2026 failure |

PM decision:

```text
hypothesis_needs_research_revision
not_formal_strategy_candidate
```

Interpretation:

The workflow replicated cleanly, but the first hypothesis is not strong enough. The composite behaves like a high-dividend variant rather than a clearly improved sector model.

Next Research Agent tasks:

```text
Build operating-purity evidence to separate gas / water operators from engineering and project-contracting firms.
Add tariff / spread, receivables pressure, gas procurement cost pass-through and recurring-operation revenue share.
Analyze why 2026 failed.
```

## Port / Rail Infrastructure

Initial model:

```text
Dividend yield + operating cash-flow yield + free-cash-flow yield + low PB + lower capex burden
```

Evidence snapshot:

| Check | Result |
| --- | --- |
| Rows / codes | 409 rows / 23 codes |
| Composite cumulative return | 54.31% |
| Equal-weight baseline | 13.19% |
| High-dividend baseline | 22.85% |
| Rolling 2024 | 22.22% |
| Rolling 2025 | 11.05% |
| Rolling 2026 | -3.92% |
| Strongest IC signal | low PB, operating cash-flow yield, free-cash-flow yield all positive |
| Main weakness | missing cargo / freight / trade-state fields |

PM decision:

```text
research_signal_only
promote_to_next_research_cycle
not_formal_strategy_candidate_yet
```

Interpretation:

Port / rail is the strongest initial model. It beat both equal-weight and high-dividend baselines, and factor IC evidence is more coherent than telecom or gas / water. However, it remains externally state-sensitive and cannot enter Engineering until operating-state evidence is joined.

Next Research Agent tasks:

```text
Add cargo throughput, container throughput, rail freight volume, regional trade state and tariff / pricing policy evidence.
Split port and rail submodels if factor behavior differs.
Explain whether 2026 resilience is real or caused by benchmark / sample effects.
```

## Cross-Sector PM Conclusion

The similar-sector replication workflow is effective.

It surfaced three different outcomes without jumping to Engineering:

| Sector | Workflow result | Meaning |
| --- | --- | --- |
| Telecom operators | research signal only, sample-size blocked | Good basket idea, weak cross-sectional validation base. |
| Gas / water operators | workflow passed, hypothesis needs revision | Need sector-specific purity and operating-state data. |
| Port / rail infrastructure | strongest initial signal, next research cycle approved | Candidate for deeper V5.5 research after operating-state data is added. |

## PM Ranking After Initial Models

| Rank | Sector | Decision |
| --- | --- | --- |
| 1 | port_rail_infrastructure | Continue Research -> Quant loop with operating-state data. |
| 2 | telecom_operators | Keep as concentrated basket / paper-observation candidate; do not rely on IC. |
| 3 | gas_water_operators | Return to Research Agent for operating-purity and tariff / receivables hypothesis repair. |

## Governance Decision

No sector is approved for Engineering Agent.

No JoinQuant strategy code should be written.

Allowed next work:

```text
Research Agent: add sector-specific operating knowledge and data maps.
Quant Agent: rerun formal validation only after Research Agent changes the hypothesis or data.
Engineering Agent: only maintain generic data probe tools; no strategy implementation.
```

## Next PM Action

Start V5.5b as:

```text
Port / Rail Infrastructure Operating-State Repair
```

Keep telecom and gas / water in the research backlog.


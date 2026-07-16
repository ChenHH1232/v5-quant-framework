# Governance Record: v52_coal_quant_validation_start_v1

Date: 2026-07-16

Project:

```text
V5.2 Coal High-Dividend / Cycle-Value Process-Portability Test
```

Current status:

```text
research_pit_validation_preparation_ready
```

Not status:

```text
formal_strategy_candidate
platform_replication_candidate
platform_replication_passed
accepted_strategy
```

## PM Decision

Project Manager Agent approves the start of limited V5.2 Quant Validation preparation.

The approved scope is limited to:

- frozen pre-research spec audit;
- PIT panel contract;
- coal external state panel contract;
- data coverage checks;
- validation runner compatibility.

Engineering platform replication and JoinQuant strategy generation remain blocked until Quant Validation Agent produces a formal evidence packet and PM explicitly freezes a formal candidate.

## Executed Work

- Created `examples/coal_high_dividend_cycle_value_v52_strategy.json`.
- Documented V5.2 Quant Validation flow.
- Documented coal external-state source candidates and PIT date requirements.
- Initialized coal Research Agent knowledge packet.

## Next Required Work

Quant Validation Agent must build or collect a PIT coal panel and run:

```text
python -m v5.cli validate-formal examples\coal_high_dividend_cycle_value_v52_strategy.json 数据库\processed\coal_pit_panel\panel.csv --out validation_formal_v52 --experiment-layer research_pit_validation
```

Required before the run:

- PIT universe membership;
- visible-date audited external coal state;
- stock-level financial and dividend coverage check;
- mixed-business classification;
- baseline definitions.

## PM Guardrail

The next run must not use 2021-2026 platform replication output as tuning evidence.

The panel can include those dates for rolling research validation, but the result must be interpreted as `research_pit_validation`, not platform confirmation.

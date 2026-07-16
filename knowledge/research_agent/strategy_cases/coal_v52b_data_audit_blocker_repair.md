# Coal V5.2b Data Audit Blocker Repair

Date: 2026-07-16

Status:

```text
research_memory_not_accepted_strategy
```

## Core Lesson

Coal V5.2b has stronger research evidence than V5.2, but the strategy cannot be accepted before data blockers are cleared.

The main danger is mistaking a strong cash-flow value backtest for a fully verified coal cycle strategy.

## What Worked

- Operating cash-flow yield remains the cleanest coal value factor.
- Free cash-flow yield is positive, but depends on capex definition quality.
- PB and PE remain useful support factors.
- The revised model improved 2024, but did not solve all weak-year behavior.

## What Is Still Blocked

- Raw coal output / inventory state is missing as formal PIT data.
- Thermal coal futures proxy does not solve 2023+ formal price-state coverage.
- Coal business tags are current manual classifications, not company-report visible-date classifications.
- FCF/capex audit flagged roughly one-third of panel rows.
- 2018 remains a down-cycle failure year.

## Reusable Rule

For cyclical resource sectors:

```text
Cash-flow value is not enough. It must be conditioned on a visible, auditable cycle-state panel.
```

Do not allow Engineering Agent to write platform strategy code until:

- external state is PIT usable;
- business classification is PIT audited;
- capex policy is explicit;
- rolling and robustness evidence remain stable after repairs.

## Next Research Tasks

1. Import official or licensed raw coal output / inventory data.
2. Import official or licensed thermal coal price data after 2023.
3. Build historical coal business tag visible-date evidence from company reports.
4. Decide whether expansion capex should be a penalty, a neutral investment signal, or a separate regime variable.
5. Rerun V5.2b formal validation before PM promotion.

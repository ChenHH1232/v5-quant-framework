# Insurance V5.3c Low-PB-only Result

Date: 2026-07-17

Status:

```text
research_pit_validation_passed_engineering_handoff_allowed
```

## Research Memory

V5.3c narrowed the insurance strategy to the simplest valid hypothesis:

```text
low PB only
```

It deliberately removed profit growth, ROE-as-quality and dividend composite scoring.

Real 10Y government yield and equity market state are review variables only.

## Key Evidence

| Case | Cumulative return |
| --- | ---: |
| Equal-weight core insurance | 79.01% |
| High-dividend reference | 86.56% |
| V5.3b low PB + dividend | 114.17% |
| V5.3c low PB-only | 137.12% |

Factor evidence:

- mean IC: `0.2004`;
- mean RankIC: `0.2023`;
- positive IC ratio: `70.45%`.

## Remaining Problems

- 2021 loses money.
- 2026 loses money and underperforms the full insurance universe.
- Top2 and Top3 are much stronger than Top4 and Top5, so the signal is concentrated.
- EV / NBV and solvency quality data remain unrepaired.

## PM Lesson

For the current 5-stock A-share insurance universe, a single clean valuation signal is stronger than a weak composite.

V5.3c can move to Engineering preparation, but not to JoinQuant code or paper trading yet.


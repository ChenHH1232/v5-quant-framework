# Utilities V5.1 Test-1 Initial Result

Date: 2026-07-16

Layer:

```text
research_pit_validation
```

Status:

```text
initial_result_not_formal_candidate
```

## Reusable Lesson

The V5 workflow can be ported from banks to utilities: universe definition, PIT panel construction, IC / RankIC, baseline, ablation, rolling validation, and PM gating all ran end-to-end.

The current V5.1 utilities composite should not be promoted to formal candidate.

## Key Evidence

- PIT panel: 3739 rows, 38 quarterly dates, 128 securities.
- Operating cash-flow yield had the strongest single-factor evidence.
- Low-PB utilities baseline beat the current composite.
- High-dividend utilities baseline also beat the current composite.
- Interest coverage coverage was too sparse to use as a core factor.
- Common-sample tests collapsed to a small universe when sparse fields were required.

## Research Implication

The next utilities test should not keep the current composite weights.

Candidate Test-2 direction:

```text
utilities_cashflow_value_v51b
```

Suggested changes:

- make operating cash-flow yield the main candidate factor;
- keep low PB and high dividend as baselines;
- test dividend only with cash-flow coverage;
- demote interest coverage from alpha to data-quality repair / risk-control candidate;
- use sub-industry split for thermal, hydro, gas and water.

## Governance

This is research evidence only. It is not platform replication evidence and not strategy acceptance.

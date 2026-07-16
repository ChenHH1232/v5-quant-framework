# Governance Record: v53_insurance_test1_pm_decision_v1

Date: 2026-07-16

Project:

```text
V5.3 Insurance Value / Quality Process-Portability Test
```

PM decision:

```text
current_composite_rejected_continue_to_v53b
```

## Decision

Project Manager Agent rejects the current V5.3 Test-1 composite as a formal strategy candidate.

## Why

The process worked:

- formal insurance universe was narrowed;
- 2024-2025 insurance-specific data gap was handled without silent filling;
- EV / NBV were explicitly deferred;
- rate / equity state panel was built;
- Quant Validation ran baseline, IC / RankIC, rolling, ablation, robustness and state review.

The model did not pass:

- composite did not beat simple low-PB baseline;
- profit-growth factor had negative IC / RankIC;
- ROE added little and hurt ablation;
- weak years 2021, 2022 and 2026 remain problematic;
- rate state still uses a bond ETF proxy, not true 10Y yield;
- insurance-specific quality data is not repaired for 2024-2025.

## Frozen Status

```text
V5.3 Test-1 = research_pit_validation_completed_not_candidate
```

## Approved Next Step

Start:

```text
V5.3b Insurance Low-PB + Dividend With Real Rate State
```

Engineering may work on:

- real PIT 10Y government bond yield ingestion;
- report/manual extraction template for EV / NBV;
- repaired insurance-specific indicator coverage.

Quant may test:

- low PB;
- dividend yield;
- low PB + dividend;
- state buckets;
- weak-year repair.

Engineering must not write JoinQuant strategy code until PM freezes a formal candidate.


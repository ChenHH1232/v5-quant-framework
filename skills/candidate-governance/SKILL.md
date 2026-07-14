---
name: candidate-governance
description: Govern Bank Quant V5 strategy candidates using V4-style ranking discipline. Use when comparing candidate strategies, deciding promote/archive/reject/pending status, closing a research branch, maintaining active baselines, or producing a decision log after common-sample rolling comparison.
---

# Candidate Governance

## Mission

Keep strategy promotion decisions evidence-driven, comparable, and reversible.

## Core Rule

A candidate is not promoted because it looks good in isolation. It must be compared against the active baseline under the same sample, fold structure, data assumptions, and execution constraints whenever possible.

## Workflow

1. Name each candidate with a stable id and role.
2. Identify the active baseline and the formal challenger set.
3. Use common-sample comparison when candidates share dates.
4. Preserve original fold ids, validation windows, and out-of-sample boundaries.
5. Report return, drawdown, positive periods, exposure, cash, turnover, and execution assumptions.
6. Explain the structural reason for each candidate's result.
7. Assign one final status: `promote`, `keep_as_alternative`, `archive`, `reject`, or `pending`.
8. Record the decision in a freeze packet or decision log.

## Status Definitions

- `promote`: replaces or upgrades the active mainline.
- `keep_as_alternative`: useful structural alternative, not the default.
- `archive`: coherent research branch, weaker than baseline or not deployable now.
- `reject`: invalid, unsupported, or broken by validation/audit.
- `pending`: incomplete evidence; no production claim.

## Never Do

- Do not compare candidates on different samples and call it a ranking.
- Do not reopen a closed candidate because a later metric looks attractive.
- Do not mix research alpha, allocation change, and execution change without attribution.
- Do not promote a candidate without a named baseline.
- Do not leave decision status implicit.

## Required Output

```text
Candidate Set:
Active Baseline:
Common Sample:
Fold Alignment:
Metrics:
Structural Interpretation:
Execution Assumptions:
Ranking:
Decision Per Candidate:
Reason:
Next Action:
```

## V4 References

- `D:\hh\codex\v4\phase_2_momentum\formal_candidate_rolling_comparison_v1.md`
- `D:\hh\codex\v4\phase_2_momentum\active_mainline_final_validation_packet_v1.md`
- `D:\hh\codex\v4\safebox_2026-06-24_v4_finalization_v1\v4_final_candidate_ranking_2026-06-23.md`

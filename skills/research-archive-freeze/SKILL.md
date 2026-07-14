---
name: research-archive-freeze
description: Freeze or archive Bank Quant V5 research branches using V4 safebox discipline. Use when closing a phase, preserving a final candidate ranking, locking an out-of-sample window, preventing further tuning, writing a final validation packet, or moving rejected and archived branches into historical evidence.
---

# Research Archive Freeze

## Mission

Preserve research conclusions so V5 can learn from both success and failure without endless retuning.

## Freeze Points

Create a freeze point when:

- a candidate is promoted;
- a branch is archived or rejected;
- an out-of-sample window has been used for acceptance;
- a strategy is exported to a platform;
- a phase is closed and its evidence should become historical context.

## Workflow

1. Name the freeze point, date, branch, baseline, and candidate set.
2. Record source data versions, code paths, configs, and output artifacts.
3. Record validation windows and out-of-sample windows.
4. Record final candidate ranking and status labels.
5. Record unresolved risks and allowed future revisit conditions.
6. Store archived branches as evidence, not as active defaults.
7. Forbid tuning against a frozen acceptance window unless a new hypothesis is explicitly opened.

## Revisit Rules

A frozen branch may be revisited only when at least one condition holds:

- new data source;
- new financial hypothesis;
- new execution constraint;
- material market-structure change;
- bug or leakage correction;
- user explicitly reopens the branch with a new objective.

## Never Do

- Do not delete failed branches just because they failed.
- Do not retune after final out-of-sample failure and call it validation.
- Do not leave the active baseline ambiguous.
- Do not promote from an archive without rerunning current validation.

## Required Output

```text
Freeze Point:
Branch:
Active Baseline:
Candidate Ranking:
Final Status:
Validation Windows:
Out-of-Sample Windows:
Artifacts:
Risks:
Allowed Revisit Conditions:
Next Action:
```

## V4 References

- `D:\hh\codex\v4\safebox_2026-06-24_v4_finalization_v1\v4_final_candidate_ranking_2026-06-23.md`
- `D:\hh\codex\v4\phase_2_momentum\active_mainline_final_validation_packet_v1.md`
- `D:\hh\codex\v4\phase_2_momentum\mean_reversion_final_archive_conclusion_v1.md`

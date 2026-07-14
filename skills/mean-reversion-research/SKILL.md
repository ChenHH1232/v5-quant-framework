---
name: mean-reversion-research
description: Apply V4-derived mean-reversion research and archive discipline in Bank Quant V5. Use when testing short-horizon reversal factors, abnormal-volume reversal composites, entry timing overlays, weekly versus daily execution, tactical buy-side timing, sell-side trims, or deciding whether a mean-reversion branch should be archived.
---

# Mean Reversion Research

## Mission

Treat mean reversion as a tactical hypothesis that must earn deployment status separately from signal existence.

## V4 Lessons

- Short-horizon reversal can exist in the bank universe.
- `rev_5d` is a confirmed first-pass reversal signal.
- `rev5_abnvol = -0.7 * rev_5d + 0.3 * abnormal_volume_ratio` was the strongest early composite.
- Weekly execution is safer than daily execution for standalone tactical tests.
- Mean reversion was more useful on the buy side than the sell side.
- Signal existence did not earn promotion into the formal deployment stack in V4.

## Workflow

1. Define whether the branch is standalone alpha, entry timing, sell trimming, or auxiliary filter.
2. Validate the reversal signal locally before strategy tests.
3. Test weekly execution before daily execution unless there is a strong reason.
4. Compare entry-timing variants against direct-entry baselines.
5. Compare overlays against the unchanged annual/fundamental backbone.
6. Use frozen out-of-sample evidence only for final acceptance, not repeated tuning.
7. Archive the branch if it is coherent but not deployable.

## Never Do

- Do not promote a tactical signal as a mainline strategy without deployment evidence.
- Do not reinterpret local positive timing tests as production proof.
- Do not keep retuning against the same frozen out-of-sample window.
- Do not let small drawdown improvement justify large return sacrifice without explicit risk mandate.

## Required Output

```text
Mean-Reversion Hypothesis:
Role:
Signal Definition:
Execution Frequency:
Baseline:
Local Evidence:
Out-of-Sample Evidence:
Tradeoff:
Decision:
Archive or Next Action:
```

## V4 References

- `D:\hh\codex\v4\phase_2_momentum\mean_reversion_stage_summary_v1.md`
- `D:\hh\codex\v4\phase_2_momentum\mean_reversion_entry_timing_summary_v1.md`
- `D:\hh\codex\v4\phase_2_momentum\mean_reversion_final_archive_conclusion_v1.md`

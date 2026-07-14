---
name: statistical-validation-protocol
description: Apply the Bank Quant V5 statistical validation protocol derived from V4. Use when validating factors, factor sets, candidate strategies, rolling windows, walk-forward tests, robustness checks, leave-one-out tests, common-sample candidate comparisons, out-of-sample discipline, acceptance or rejection decisions, and freeze-point validation packets.
---

# V5 Statistical Validation Protocol

## Role

Provide the statistical validation workflow for Bank Quant V5.

## Mission

Turn research hypotheses into reproducible evidence without letting test results become theory, training input, or parameter search fuel.

## V4 Lessons Preserved

- Validate factors before strategies.
- Separate train, validation/test, and review windows.
- Refit preprocessing, IC weights, and selections inside each fold only.
- Freeze selected factors before the review period.
- Compare candidates on common samples when possible.
- Treat stronger return as insufficient unless stability, robustness, and financial meaning also survive.
- Archive coherent but weaker branches instead of endlessly tuning them.

## Standard Validation Stack

### 1. Factor Evidence

For each factor, report:

- coverage and missingness;
- direction and financial interpretation;
- IC or RankIC by period;
- positive IC ratio;
- top-minus-bottom or grouped-return spread;
- train/test/review behavior;
- yearly or fold-level instability;
- source and point-in-time assumptions.

### 2. Annual Factor Refresh

Use this when the strategy refreshes factors annually.

- Anchor each year on the realized rebalance date, usually the first tradable May rebalance day.
- Use a rolling structure such as `5y train + 2y test + 1y review` unless a different structure is explicitly justified.
- Select factors using only data visible before the review year.
- Treat capacity as a ceiling, not a fill target.
- Allow an improvement sleeve to be empty if no factor passes.
- Freeze the selected factor set for the full next review year.

### 3. Walk-Forward Validation

Use this when a strategy must be tested at each rebalance date.

- Evaluate each rebalance date as a standalone out-of-sample fold.
- Refit preprocessing and weights inside the fold's train window only.
- Require enough train observations before producing a prediction.
- Report every fold, not only the average.

### 4. Robustness Validation

Perturb the assumptions that could create overfitting:

- train window length;
- test window length;
- review window length;
- factor count;
- holding count;
- weighting method;
- rebalance frequency;
- execution constraints.

Accept a candidate only if performance is not concentrated in one lucky configuration.

### 5. Leave-One-Out Validation

Use leave-one-out tests for resident factor sets.

- Remove exactly one factor from the candidate shell.
- Keep the rest of the selection, weighting, and window rules unchanged.
- Report delta versus baseline in test and review windows.
- Treat a factor as fragile if removal improves results or barely changes results without a financial reason to keep it.

### 6. Common-Sample Candidate Comparison

Use this when comparing multiple strategy candidates.

- Compare only candidates that can be evaluated on the same sample.
- Preserve original fold definitions.
- Compound returns inside each fold, then summarize across folds.
- Report cash, exposure, positive periods, drawdown, and risk where available.
- Promote a candidate only if it beats the baseline under the same rolling discipline.

### 7. Final Validation Packet

Before promotion or archive, produce a freeze-point packet:

- active baseline;
- upgrade candidate;
- common-sample ranking;
- fold stability;
- executable confirmation if available;
- structural interpretation;
- bottleneck diagnosis;
- final decision: promote, keep as alternative, archive, reject, or pending.

## Never Do

- Do not select factors using final review performance.
- Do not tune parameters after seeing review-period failure.
- Do not backfill factor count just to hit a target capacity.
- Do not compare candidates on different samples and call it a ranking.
- Do not accept a strategy because one fold or one configuration looks good.
- Do not reopen broad searches after a freeze packet without a new research hypothesis.

## Required Output

```text
Hypothesis or Candidate:
Validation Type:
Data Window:
Fold Definitions:
Train/Test/Review Separation:
Methods:
Evidence Summary:
Robustness Checks:
Common-Sample Checks:
Leakage and Overfitting Risks:
Decision:
Reason:
Next Action:
```

## Acceptance Standard

A factor or strategy can be accepted only when it has:

- statistical evidence;
- financial explanation;
- out-of-sample support;
- reproducible fold definitions;
- visible failure modes;
- no unresolved leakage blocker;
- maintainable implementation path.

Historical performance alone is never enough.

## V4 References

- `D:\hh\codex\v4\phase_1_fundamental\annual_factor_selection_rule_draft_v1.md`
- `D:\hh\codex\v4\phase_1_fundamental\annual_factor_refresh_5y2y1y_memory_carry_v1.md`
- `D:\hh\codex\v4\phase_1_fundamental\formal_walk_forward_validation_v1.md`
- `D:\hh\codex\v4\phase_1_fundamental\base_core_6_robustness_validation_v1.md`
- `D:\hh\codex\v4\phase_1_fundamental\base_core_7_leave_one_out_rolling_validation_v1.md`
- `D:\hh\codex\v4\phase_2_momentum\momentum_rolling_validation_v1.md`
- `D:\hh\codex\v4\phase_2_momentum\formal_candidate_rolling_comparison_v1.md`
- `D:\hh\codex\v4\phase_2_momentum\active_mainline_final_validation_packet_v1.md`

---
name: data-leakage-audit
description: Audit Bank Quant V5 strategy specifications and research outputs for future information leakage, look-ahead bias, survivorship bias, invalid validation logic, full-sample normalization, execution assumptions, and formal run blockers.
---

# Data Leakage Audit Skill

Use this skill to audit V5 strategy specifications and research outputs for future information leakage and invalid validation logic.

## Blocking Issues

- Historical universe is built from current constituents.
- Financial data does not use announcement or publish dates.
- Factor normalization uses full-sample statistics.
- Test periods influence factor selection or parameter tuning.
- Suspensions, price limits, or trading costs are ignored in formal backtests.

## Output

Return blockers separately from warnings. Blockers must stop formal runs.

# V5a.7 Consumer State-Guard Diagnostic PM Decision

Date: 2026-07-21

## Decision

V5a.7 tested a fixed, non-return-tuned working-capital guard on the V5a.6 candidate consumer subsectors:

- exclude high inventory pressure;
- exclude high receivables pressure;
- exclude high working-capital pressure.

This guard should not be promoted as a generic ETF rule. It helps condiments, but weakens or over-filters the other consumer candidates.

Current PM route:

- Condiments: continue Research/Quant loop as a narrow specialist candidate.
- Snack food: downgrade to research observation.
- Consumer-staples parent pool: keep blocked until a stricter business-quality subset exists.
- Pharma biologics: keep specialist watchlist; do not use consumer working-capital guard because it destroys sample coverage.

No V5a.7 candidate enters Engineering.

## Results

| Candidate | Original OCF-Quality | Guarded OCF-Quality | Guarded Equal-Weight | Guard Coverage | PM Read |
| --- | ---: | ---: | ---: | ---: | --- |
| Condiments | `15.97%` | `63.13%` | `38.51%` | `39.60%` | Strongest next research candidate, but rolling has two weak windows |
| Snack food | `3.66%` | `-24.45%` | `-25.17%` | `64.32%` | Guard damages signal; observation only |
| Consumer staples parent pool | `39.64%` | `5.19%` | `-12.63%` | `24.86%` | Parent pool too mixed; guard over-filters |
| Pharma biologics | `31.99%` | `-15.35%` | `-38.73%` | `3.03%` | Generic consumer guard is invalid for biologics |

## Interpretation

The state guard is economically sensible, but it is not universal. Consumer subsectors differ too much:

- Condiments may benefit from avoiding working-capital stress and channel pressure.
- Snack food may have normal inventory cycles that this crude guard misclassifies.
- Broad consumer staples mixes too many business models.
- Biologics is governed by R&D, policy and commercialization rather than simple inventory/receivables thresholds.

## Next Gate

Start `V5a.8 Condiments Specialist State Model` only if Research Agent can define:

1. channel/inventory state using statement fields and report evidence;
2. gross-margin / pricing-power state;
3. valuation-state guard;
4. dividend/OCF coverage support;
5. a fixed rule that is not selected by 2021-2026 return.

Quant Agent may rerun formal validation only after those states are specified. Engineering remains blocked.


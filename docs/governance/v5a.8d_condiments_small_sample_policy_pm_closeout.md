# V5a.8d Condiments Small-Sample Specialist Policy Closeout

Date: 2026-07-22

Layer: `pm_decision_gate`

Owner: Project Manager Agent

## Decision

`condiments_high_ocf_wc_guard_v5a8c` remains a research signal only.

It is not promoted to Engineering, not added to V57f, not used as a basket sleeve, and not accepted as a strategy.

The conservative PM decision is:

`small_sample_specialist_sleeve_policy_not_approved_by_default`

This is because the filtered universe is too concentrated for the current dividend / low-volatility / operating-cash-flow enhanced ETF mandate.

## Detailed Flow Table

| Stage | Owner | Input | Action | Output | Gate | Status |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | Project Manager Agent | V5a.7 consumer state-guard diagnostic | Identify strongest consumer candidate after broad food/beverage rejection | `sw_condiments` candidate | candidate must be subsector-specific | completed |
| 2 | Research Agent | Working-capital, OCF, gross-margin and channel/inventory hypothesis | Define specialist condiments state model | V5a.8 hypothesis variants | no return-selected rule | completed |
| 3 | Quant Validation Agent | V5a.8 fixed variants | Run PIT validation, rolling, ablation, robustness and IC/RankIC | `condiments_high_ocf_wc_guard_v5a8c` evidence | research layer only | completed |
| 4 | Project Manager Agent | V5a.8 summary | Check concentration and sleeve suitability | small-sample policy check | no broad ETF sleeve if universe too narrow | completed |
| 5 | Project Manager Agent | small-sample policy check | Apply conservative default: no specialist sleeve without explicit PM approval | watchlist closeout | do not enter Engineering | completed |
| 6 | Research Agent | watchlist closeout | Preserve hypothesis for future specialist portfolio or manual watchlist | restart condition | only restart with PM-approved small-sample sleeve policy | waiting |

## Evidence

| Check | Result |
| --- | --- |
| Strategy | `condiments_high_ocf_wc_guard_v5a8c` |
| Panel rows after guard | `99` |
| Rebalance dates | `18` |
| Common sample securities | `8` |
| Mean selected count | `4` |
| Guarded equal-weight return | `38.51%` |
| High OCF guarded return | `78.31%` |
| Mean IC / RankIC | `0.0769` / `0.1357` |
| Rolling weak window | 2025: `-1.48%` |

## PM Read

The research result is useful: it confirms that food/beverage must be routed by subsector and that condiments respond better to OCF yield plus working-capital stress control than to broad valuation or gross-margin composites.

The result is not enough for the enhanced ETF sleeve system. A 4-stock selected portfolio from an 8-stock common sample is too concentrated and too vulnerable to single-name effects.

## Blocked Actions

- Do not hand off to Engineering local daily simulation.
- Do not write JoinQuant code.
- Do not add condiments to frozen V57f.
- Do not treat 2021-2026 performance as acceptance evidence.
- Do not create a small-sample specialist sleeve without a separate PM approval gate.

## Restart Condition

Restart only if one of the following happens:

1. PM explicitly approves a small capped specialist sleeve policy.
2. The PIT universe expands enough to support normal sleeve construction.
3. Research Agent provides independent channel/inventory evidence that supports a forward paper watchlist, not merely historical returns.

## Next Gate

`archive_as_research_signal_only_small_sample_specialist_watchlist`

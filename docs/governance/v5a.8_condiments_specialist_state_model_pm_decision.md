# V5a.8 Condiments Specialist State Model PM Decision

Date: 2026-07-21

## Decision

V5a.8 tested the narrow condiments candidate after the V5a.7 state-guard diagnostic.

PM decision:

`condiments_high_ocf_wc_guard_v5a8c` is a specialist research signal, not an Engineering handoff and not an ETF sleeve candidate yet.

The signal is economically cleaner than the broad food / beverage pool, but the filtered universe becomes too concentrated for the current enhanced ETF mandate.

## Tested Hypotheses

| Variant | Logic | Result | PM Read |
| --- | --- | ---: | --- |
| V5a.8a OCF + gross margin | OCF quality plus pricing-power proxy | `-5.50%` | Reject: gross margin does not map cleanly to forward returns |
| V5a.8b OCF + gross margin + working-capital guard | Add fixed working-capital guard | `19.31%` | Not superior to guarded equal-weight |
| V5a.8c high OCF + working-capital guard | Keep only OCF after fixed guard | `78.31%` | Best result, but too concentrated |

## V5a.8c Evidence

| Check | Result |
| --- | --- |
| Panel rows after guard | `99` |
| Rebalance dates | `18` |
| Guarded equal-weight return | `38.51%` |
| High OCF guarded return | `78.31%` |
| Mean IC / RankIC | `0.0769` / `0.1357` |
| Rolling 2024 | `7.94%` |
| Rolling 2025 | `-1.48%` |
| Rolling 2026 | `21.53%` |

## PM Interpretation

The core lesson is not "add condiments to the ETF." The lesson is:

1. Food / beverage must be routed by subsector.
2. For condiments, OCF yield matters more than gross margin as a scoring variable.
3. Working-capital pressure is a useful guard candidate.
4. The resulting universe is too narrow after filtering, so it is better treated as a specialist watchlist or a small capped observation sleeve.

## Next Gate

Do not send condiments to Engineering yet.

Only continue if PM explicitly allows a small-sample specialist sleeve policy. Otherwise, keep V5a.8c as:

`research_signal_only_small_sample_specialist_watchlist`

The enhanced ETF core should keep relying on broader, cleaner sleeves such as utilities/electricity, highway, bank, port/rail and approved gas/water observation sleeves.


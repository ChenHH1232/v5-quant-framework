# V5c Quant Handoff Packet

## Status

Knowledge base scaffold completed. This is not Quant validation approval.

## Eligible For Next Stage

The following hypotheses can enter a Quant design specification after PM approval and PIT source confirmation:

- `V5C_H01`: portfolio drawdown defense.
- `V5C_H02`: broad-market trend defense.
- `V5C_H03`: portfolio volatility target.
- `V5C_H04`: sleeve overweight peak trimming.
- `V5C_H06`: dividend safety defense.
- `V5C_H07`: valuation heat peak trimming.
- `V5C_H08`: cash restoration rule.
- `V5C_H09`: threshold rebalancing.

## Not Yet Eligible

- Any hypothesis requiring fxbaogao report evidence, because broad-query report recall is noisy and Stage 1 title filtering produced no accepted V5c source leads from the initial batch.
- Any hypothesis relying on WeChat Reading notes, because user-provided book notes are not available.
- Any hypothesis relying on Xueqiu/blog material, because links and dates are not available and D-level material cannot be evidence.

## Quant Design Requirements

Before validation, Quant Agent must receive:

1. Frozen V57f daily NAV / returns.
2. Overlay decision calendar.
3. Execution calendar and next-day/open/close policy.
4. Cash treatment policy.
5. PIT-safe broad index data, if using trend defense.
6. PIT-safe dividend and financial fields, if using dividend safety defense.
7. Pre-registered threshold families, not optimized thresholds.
8. Overfit audit plan.
9. Ablation plan separating defense, profit taking, rebalancing and cash restoration.

## Hard Blocks

- Do not modify V57f.
- Do not change V57f core sleeves, weights, factors, rebalance schedule or execution timing.
- Do not run JoinQuant.
- Do not backtest until PM opens the V5c Quant stage.
- Do not optimize thresholds on 2021-2026.
- Do not use future data.
- Do not use blog/book opinions as parameters.

## Recommended First Quant Design

Start with the simplest three candidates:

1. Portfolio drawdown defense.
2. Broad-market long-term trend defense.
3. Sleeve drift rebalancing.

These are transparent and easier to audit than complex multi-signal macro timing.

# V5.6c OCF Value + Volatility Guard Basket Research Reset

Date: 2026-07-18

## PM Instruction

The prior low PB / FCF enhanced dividend-basket narrative is rejected for the current V5.6 basket layer.

Research and Quant should use the following mainline instead:

```text
Operating cash-flow yield is the primary cross-sector value signal.
Low-volatility and drawdown are risk / coverage guards.
Dividend yield supports shareholder-return discipline.
Low PB and FCF are not core factors unless future evidence repairs them.
```

## Why Low PB / FCF Was Rejected

- `low_price_to_book` had weak or negative basket-level evidence.
- Removing low PB improved the earlier V5.6 common-window result.
- `free_cash_flow_yield` had low coverage and weak incremental impact.
- The FCF story may still be useful at sector level, but it is not yet robust enough for cross-sector basket scoring.

## New Hypothesis

Stable cash-flow sectors can be combined through a disciplined cash-flow quality/value lens:

- prefer high operating cash-flow yield;
- require PIT-safe low-volatility data coverage;
- penalize high realized volatility and drawdown;
- keep dividend yield as shareholder-return support, not the only reason to buy;
- use capex burden only as a small risk modifier.

## Validation Summary

V5.6c local result:

| Metric | Value |
| --- | ---: |
| Strategy return | 86.38% |
| Annualized return | 14.97% |
| Excess return vs same-pool benchmark | 35.37% |
| Max drawdown | 13.43% |
| Sharpe | 0.935 |
| Information ratio | 0.542 |

Formal validation:

| Evidence | Value |
| --- | ---: |
| Composite mean RankIC | 0.1574 |
| Composite positive IC ratio | 73.68% |
| OCF yield mean RankIC | 0.0856 |
| Volatility 120d mean RankIC | 0.1358 |
| Max drawdown 120d mean RankIC | 0.0995 |
| Dividend yield mean RankIC | 0.0803 |

## Known Boundaries

- 2021-2026 is still a platform-confirmation window, not clean accepted-strategy evidence.
- 2025 and 2026 still underperform the same-pool benchmark.
- The basket misses high-elasticity utilities winners that do not fit OCF / dividend / volatility-guard style.
- Selected count varies between 24 and 30 because the OCF + low-vol coverage gate is stricter.

## Next Research Questions

1. Is OCF yield stable across additional PIT data beyond 2026-04?
2. Should FCF be reintroduced only inside sectors where capex accounting is clean?
3. Should low PB remain sector-specific rather than basket-wide?
4. Should the basket have a separate high-elasticity sleeve, or is missing those winners an acceptable style boundary?

## Governance

V5.6c is a research-reset success and current basket mainline, but it is not an accepted strategy.

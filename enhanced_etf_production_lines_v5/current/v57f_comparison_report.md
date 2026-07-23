# V57f Governed Comparison Packet

Created at UTC: `2026-07-23T04:37:05+00:00`

## PM Conclusion

V57f remains the frozen mainline enhanced ETF candidate. It is not accepted, not live-trading approved, and not platform-replication passed.

Next gate: `wait_until_2026_10_08_or_joinquant_exports_for_daily_attribution`.

## Best Version Snapshot

| Strategy | Return | Benchmark | Excess | Max drawdown | Sharpe | Order health |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f` | 81.42% | 51.01% | 30.40% | 11.75% | 0.932 | `pass` |

## Core Sleeve View

These rows support sleeve monitoring. They are not direct replacements for the full V57f basket.

| Sector | Return | Benchmark | Window | Directly comparable | Order health | Next gate |
| --- | ---: | ---: | --- | --- | --- | --- |
| `enhanced_etf_basket` | 81.42% | 51.01% | 2021-10-08 to 2026-05-31 | yes | `pass` | `wait_until_2026_10_08_or_joinquant_exports_for_daily_attribution` |
| `bank` | 57.94% | 25.16% | 2021-05-01 to 2026-05-31 | no | `unknown` | `core_sleeve_refresh_only` |
| `utilities_electricity` | 230.70% | 15.86% | 2021-05-06 to 2026-05-29 | no | `pass` | `golden_template_refresh_only` |
| `highway_infrastructure` | 106.61% | 58.10% | 2021-05-06 to 2026-05-29 | no | `unknown` | `core_sleeve_refresh_only` |
| `port_rail_infrastructure` | 71.23% | 17.69% | 2021-05-01 to 2026-05-31 | no | `unknown` | `core_sleeve_refresh_only` |

## Observation / Blocked View

High historical return in this table is explicitly not a promotion signal.

| Sector | Return | Governance group | Core eligible | Order health | Exclusion reason |
| --- | ---: | --- | --- | --- | --- |
| `gas_water_operators` | 76.49% | `observation` | no | `pass` | Rank 1 observation sleeve, but core inclusion still requires separate PM gate and clean paper evidence. |
| `insurance` | 29.89% | `observation` | no | `unknown` | Insurance needs specialist EV/NBV/P/EV and has small-sample concentration risk. |
| `telecom_operators` | 80.12% | `observation` | no | `unknown` | Telecom sample is small and overlay construction is not the same contract as V57f. |
| `home_appliances` | 106.37% | `observation` | no | `pass` | Observation candidate; promotion queue does not allow core inclusion yet. |
| `oil_gas_pipeline_integrated` | 99.79% | `observation` | no | `pass` | External state and platform/paper event are pending; high return is not core evidence. |
| `food_beverage` | 4.65% | `blocked_or_failed` | no | `needs_review` | Order-health/dividend issues still need PM review before any sleeve decision. |
| `coal` | 133.69% | `blocked_or_failed` | no | `unknown` | Failed candidate despite high return; official cycle state and PIT business exposure data gates remain incomplete. |

## Guardrails

- Do not sort all rows by return and treat the top sector as a replacement for V57f.
- `unknown` order health is not a pass.
- Observation sleeves require a separate PM promotion gate before any basket inclusion.
- Coal remains a failed high-return example unless its cyclical data gate is reopened and repaired.

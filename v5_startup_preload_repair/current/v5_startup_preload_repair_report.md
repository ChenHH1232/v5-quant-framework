# V5 Startup Preload / Initial Rebalance Repair

- Status: `blocked_requires_warmup_price_data`
- Deployment date: `2021-05-01`
- First tradable date: `2021-05-06`
- Warmup start date: `2021-05-06`

## Pre/Post

| Item | Old | Repaired |
| --- | ---: | ---: |
| First signal | `2021-10-08` | `2021-10-08` |
| First trade | `2021-10-08` | `2021-10-08` |
| First position | `2021-10-08` | `2021-10-08` |
| Startup gap days | `160` | `160` |

## PM Read

The code path now exposes the startup gap instead of hiding it by lifting the start date to the first signal. Current local files still cannot legally generate a deployment-day initial rebalance because pre-deployment warmup prices are missing.

## Blockers

- `deployment_day_initial_signal_blocked`: Initial rebalance cannot be generated from current local files because required startup fields are unavailable on the first tradable date.
- `missing_pre_deployment_warmup_prices`: Current local price files start at or after deployment first tradable date, so 120/252-day low-volatility factors cannot be computed for deployment day.

## Governance

No V57f sleeve/factor/weight/rebalance-frequency change was made. ERC/L2/L3/L4 remain candidates only. V5e remains blocked until startup warmup data is repaired.

# V5 Startup Warmup Price Repair

- Status: `startup_warmup_price_repair_completed`
- Local warmup data found: `True`
- Repaired price files generated: `True`
- V57f core logic modified: `False`
- External warmup data source used: `JoinQuant=True`, `BaoStock=False`, `Tushare=False`

## Startup Dates

- Deployment date: `2021-05-01`
- First tradable date: `2021-05-06`
- Recommended warmup start: `2019-01-01`
- Minimum allowed warmup start: `2020-04-01`

## Pre/Post

| Item | Old | Repaired |
| --- | ---: | ---: |
| First signal | `2021-10-08` | `2021-05-06` |
| First trade | `2021-10-08` | `2021-05-06` |
| First position | `2021-10-08` | `2021-05-06` |
| Startup gap days | `160` | `5` |

## Requirements

- `bank` needs raw daily warmup prices from `2019-01-01` through deployment eve, with at least `252` prior closes plus buffer.
- `utilities_electricity` needs raw daily warmup prices from `2019-01-01` through deployment eve, with at least `252` prior closes plus buffer.
- `highway_infrastructure` needs raw daily warmup prices from `2019-01-01` through deployment eve, with at least `252` prior closes plus buffer.
- `port_rail_infrastructure` needs raw daily warmup prices from `2019-01-01` through deployment eve, with at least `252` prior closes plus buffer.

## Repaired Data

- `bank`: `generated`, rows `71246`
- `utilities_electricity`: `generated`, rows `221206`
- `highway_infrastructure`: `generated`, rows `23322`
- `port_rail_infrastructure`: `generated`, rows `36841`

## Low-Vol Recalc

- `bank`: `generated`
- `utilities_electricity`: `generated`
- `highway_infrastructure`: `generated`
- `port_rail_infrastructure`: `generated`

## Blockers

- None

## Governance

No original V57f core config or investment logic is modified. The repair is data-gate and startup deployment engineering only. ERC, L2, L3 and L4 remain candidates, not accepted strategies and not V57f replacements.

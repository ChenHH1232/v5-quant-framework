# V57f Execution Robustness Freeze And Result

Created: 2026-07-23

## PM Decision

V57f remains frozen. This packet only tests execution timing and non-rebalance risk-control mechanics. It does not recompute factors, change sleeves, tune weights, or approve platform replication / live trading.

Decision: `execution_timing_not_fragile_no_strategy_change`

Next gate: `prepare_clean_2026_10_08_paper_signal_or_joinquant_export_attribution`

## Frozen Baseline

Core sleeves remain unchanged:

- `bank`
- `utilities_electricity`
- `highway_infrastructure`
- `port_rail_infrastructure`

Locked local baseline:

| Metric | Value |
| --- | ---: |
| Strategy return | 81.42% |
| Annualized return | 14.27% |
| Benchmark return | 51.01% |
| Excess return | 30.40% |
| Max drawdown | 11.75% |
| Sharpe | 0.932 |
| Trade rows | 709 |
| Dividend events | 128 |
| Rebalance signals | 19 |
| First executed order | 2021-10-08 |

## Execution Matrix

| Variant | Return | Benchmark | Excess | Max drawdown | Sharpe | Order health | Conclusion |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `rebalance_day_open` | 81.42% | 51.01% | 30.40% | 11.75% | 0.932 | pass | pass |
| `rebalance_day_0940_proxy` | 81.35% | 51.01% | 30.33% | 11.75% | 0.931 | pass | pass |
| `rebalance_day_1000_proxy` | 81.28% | 51.01% | 30.26% | 11.74% | 0.931 | pass | pass |
| `rebalance_day_close_proxy` | 81.06% | 51.01% | 30.04% | 11.72% | 0.930 | pass | pass |
| `t_plus_1_open` | 77.95% | 51.01% | 26.94% | 11.71% | 0.904 | pass | pass |
| `sliced_2d_open` | 78.60% | 51.01% | 27.59% | 11.72% | 0.911 | pass | pass |
| `sliced_3d_open` | 79.40% | 51.01% | 28.39% | 11.71% | 0.920 | pass | pass |
| `delayed_limit_fill_3d` | 80.63% | 51.01% | 29.62% | 11.75% | 0.924 | pass | pass |

## Risk-Control Boundary

Non-rebalance days are no-action by default. The only permitted non-rebalance actions are:

- delayed fill attempts from blocked rebalance orders;
- sell-delay repair when a rebalance sell is blocked;
- drift / risk logging;
- cash-drag measurement.

Observed risk-event counts:

| Event | Count |
| --- | ---: |
| `non_rebalance_no_action` | 8780 |
| `blocked_or_unfilled_order` | 37 |
| `cash_drag_high` | 40 |

## PM Rules

- This result supports execution robustness only.
- Do not choose an execution variant because it has the highest historical return.
- Do not add observation sleeves to V57f from this packet.
- Do not mark `platform_replication_passed`, `accepted_strategy`, or `live_trading_approved`.
- 2021-2026 remains platform-confirmation context, not clean acceptance evidence.


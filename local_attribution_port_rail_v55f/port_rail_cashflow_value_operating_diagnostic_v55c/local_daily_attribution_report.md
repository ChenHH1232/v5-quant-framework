# V5.5f Port / Rail Local Daily Attribution Review

Date: 2026-07-18

Experiment layer: `engineering_smoke_test_local_attribution`

## PM Conclusion

The 2021 no-signal gap is a PIT universe coverage issue. JoinQuant returned zero members for `HY03155` and `HY03159` on 2021-07-01 and 2021-10-08, while daily prices for the later 23-name port/rail pool existed on both dates. It is not an order-size, cash, defensive-rule, or daily-price problem.

Local daily attribution is complete enough for engineering review, but not enough for platform replication or paper trading.

## Core Attribution

- First signal date: `2022-01-04`
- Pre-signal period: `2021-05-06` to `2021-12-31`, invested days `0`, strategy `0.00%`, benchmark `22.55%`
- Active period: `2022-01-04` to `2026-05-29`, invested days `1064`, strategy `63.86%`, benchmark `-3.96%`, excess `51.75%`
- Full period: strategy `63.86%`, benchmark `17.69%`, excess `20.07%`
- Active max drawdown: `20.20%` from `2023-05-08` to `2024-01-22`

## Yearly View

| Year | Strategy | Benchmark | Excess | Invested Days | Dividend Cash | Commission |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2021 | 0.00% | 22.55% | -20.87% | 0 | 0.00 | 0.00 |
| 2022 | 5.88% | -11.96% | 16.48% | 242 | 55675.36 | 2193.22 |
| 2023 | 10.17% | -7.69% | 16.54% | 242 | 58109.83 | 1842.95 |
| 2024 | 21.71% | 13.30% | 3.81% | 242 | 48162.01 | 2721.33 |
| 2025 | 10.70% | 6.27% | 2.45% | 243 | 53749.88 | 2685.91 |
| 2026 | 4.25% | -1.85% | 5.12% | 95 | 0.00 | 1290.18 |

## Generated Files

- `annual_attribution.csv`
- `rebalance_period_attribution.csv`
- `top_loss_days.csv`
- `top_gain_days.csv`
- `local_daily_attribution_summary.json`

## Remaining Blockers

- Decide whether to repair the 2021 universe with original PIT evidence, as was done for highway V5.4h, or disclose the 2022-start limitation.
- Review original operating evidence for port / rail revenue share, cargo throughput, rail freight volume and tariff policy.
- Keep `516970.XSHG` as an engineering proxy only until a pure port / rail benchmark is confirmed.

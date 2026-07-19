# V5.4g Highway Multi-Year Reviewed Operating Data PM Decision V1

Date: 2026-07-18

Strategy ID:

```text
highway_dividend_reviewed_operating_v54g
```

Status:

```text
research_pit_validation_passed
engineering_smoke_test_passed_with_pm_review
not_accepted_strategy
```

## What Changed From V5.4f

V5.4f was blocked because reviewed operating evidence covered only a small 2024 annual-report sample.

V5.4g expanded the reviewed annual-report operating evidence to 2021-2025.

Data repair result:

| Item | Count |
| --- | ---: |
| Target annual reports | 100 |
| Downloaded CNINFO reports | 80 |
| Candidate operating snippets | 4,575 |
| Shortlisted candidate snippets | 1,278 |
| Reviewed disclosure rows | 80 |
| PIT usable reviewed disclosure rows | 58 |
| PIT usable companies | 14 |
| Formal reviewed-operating panel rows | 149 |
| Formal rebalance dates | 17 |
| Formal covered companies | 12 |

Still missing from CNINFO query:

```text
001965.XSHE
601107.XSHG
601188.XSHG
601518.XSHG
```

## Formal Validation

Panel:

```text
数据库/processed/highway_operating_data/annual_reports_2021_2025/highway_reviewed_operating_formal_panel.csv
```

PIT leakage audit:

```text
pass
```

Baseline:

| Case | Periods | Cumulative Return | Positive Ratio | Mean Selected Count |
| --- | ---: | ---: | ---: | ---: |
| equal_weight_reviewed_operating_formal | 17 | 66.40% | 70.59% | 8.76 |
| high_dividend_reviewed_operating_top8 | 17 | 76.86% | 82.35% | 7.35 |
| reviewed_operating_segment_purity_composite | 17 | 74.09% | 82.35% | 7.35 |

Rolling:

| Year | Return | Positive Ratio |
| --- | ---: | ---: |
| 2024 | 30.84% | 100.00% |
| 2025 | 1.74% | 75.00% |
| 2026 | -2.67% | 50.00% |

Factor IC / RankIC:

| Factor | Mean IC | Mean RankIC | Positive IC Ratio |
| --- | ---: | ---: | ---: |
| dividend_yield | 0.2336 | 0.2875 | 70.59% |
| highway_revenue_ratio | -0.0528 | -0.0731 | 52.94% |
| non_highway_revenue_ratio | -0.0528 | -0.0731 | 52.94% |
| capex_burden | -0.1364 | -0.1222 | 29.41% |
| reviewed_operating_disclosure_score | 0.0883 | 0.0557 | 58.82% |

Interpretation:

- Dividend yield remains the core validated signal.
- Reviewed operating evidence is useful as a data-quality gate.
- Segment purity and capex burden are not independently strong alpha factors.
- The composite is slightly below high-dividend-only, so the strategy should not be described as a superior multi-factor alpha model.

## Engineering Smoke Test

Inputs:

| Input | Path / Policy |
| --- | --- |
| Real daily prices | `数据库/processed/highway_v54g_joinquant_real_daily_prices.csv` |
| Real cash dividends | `数据库/processed/highway_v54g_joinquant_cash_dividends.csv` |
| Dividend tax | 20% tax, net cash paid on ex-date proxy |
| Benchmark | internal same-pool highway equal-weight |
| Benchmark path | `数据库/processed/highway_v54g_equal_weight_benchmark.csv` |
| Execution price | daily open |
| Valuation price | daily close |
| Lot size | 100 shares |

Local daily result:

```text
local_daily_backtests_highway_v54g_full_coverage/highway_dividend_reviewed_operating_v54g/summary.json
```

Metrics:

| Metric | Value |
| --- | ---: |
| Strategy return | 67.18% |
| Annualized return | 13.43% |
| Benchmark return | 33.46% |
| Excess return | 33.72% |
| Max drawdown | 14.91% |
| Sharpe | 0.824 |
| Information ratio | 0.635 |
| Beta | 0.822 |
| Signal count | 17 |
| Trade count | 133 |
| Dividend cash events | 30 |

Important engineering correction:

The first smoke run generated only 8 signals because the daily runner had a hidden 80% max-coverage filter. The CLI now exposes `--min-coverage-ratio`, and the full-coverage smoke run uses `0.33` to match the formal reviewed-operating panel coverage.

## Overfit / Leakage Audit

Audit status:

```text
needs_review
```

Blockers:

```text
0
```

Needs review:

1. The 2022-2026 local daily window overlaps the platform-confirmation period and is not clean forward evidence.
2. The spec should document parameter perturbation requirements more explicitly.
3. Selected counts vary from 4 to 8 because early reviewed-operating coverage is smaller.

Passes:

- PIT universe visibility;
- no visible-date future leakage;
- cross-sectional normalization;
- rolling validation requirement;
- random window stability;
- execution timing shift proxy.

## PM Decision

V5.4g can proceed to platform-replication preparation.

It is not an accepted strategy.

Current PM status:

```text
formal_strategy_candidate
engineering_smoke_test_passed_with_pm_review
platform_replication_ready
not_accepted_strategy
```

## Next Gate

Engineering Agent should prepare platform replication:

1. Generate frozen JoinQuant script for V5.4g.
2. Use the same signal rules:
   - PIT highway reviewed-operating panel;
   - high dividend main signal;
   - segment purity / capex as support diagnostics;
   - no timing overlay;
   - no return tuning.
3. In JoinQuant, use `000027.XSHG` (180 transport) as the display benchmark unless a cleaner highway-specific platform benchmark is confirmed.
4. Export:
   - daily returns;
   - transactions;
   - positions;
   - logs.
5. Run local vs JoinQuant attribution.

Generated script:

```text
exports/joinquant/highway_dividend_reviewed_operating_v54g_joinquant_frozen_signals.py
```

Script notes:

- uses frozen local rebalance signals;
- uses `order_target_value`, not `order_target_percent`;
- keeps residual cash when early-year selected count is below 8;
- uses `000027.XSHG` (180 transport) as the JoinQuant display benchmark.
- `000027.XSHG` is not a pure highway benchmark; formal sector-relative attribution still uses the internal same-pool highway equal-weight benchmark.

Do not accept or trade the strategy before platform replication and forward / paper trading.

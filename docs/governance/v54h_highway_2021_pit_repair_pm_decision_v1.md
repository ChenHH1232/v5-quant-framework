# V5.4h Highway 2021 PIT Repair PM Decision V1

Date: 2026-07-18

Strategy ID:

```text
highway_dividend_reviewed_operating_v54h_repaired_2021
```

Status:

```text
research_pit_validation_repaired
engineering_smoke_test_completed
platform_replication_ready
not_accepted_strategy
```

## Why V5.4h Exists

V5.4g had no trades before 2022-04-01 because its reviewed operating evidence started from 2021 annual reports, which only became visible in March/April 2022.

The missing pre-2022 signal was not a trading-code failure. It was a data coverage issue.

The repair confirms that 2020 annual reports existed and were visible before the 2021-05 backtest window.

## Repair Actions

1. Added Tushare disclosure dates for 2020 annual and semiannual reports.
2. Downloaded CNINFO 2020-2025 annual reports for highway candidates.
3. Extracted operating evidence from original annual reports.
4. Rebuilt Eastmoney segment evidence with repaired 2020-2025 disclosure dates.
5. Built a repaired 2021 PIT highway universe using 2020 annual-report reviewed operating evidence because JoinQuant `HY03160` returns empty before 2021-12-13.
6. Rebuilt formal panel, validation packet, real daily data, dividends, equal-weight benchmark, and frozen JoinQuant script.

## Data Outputs

```text
数据库/processed/highway_operating_data/annual_reports_2020_2025/highway_report_disclosure_dates_2020_2025.csv
数据库/processed/highway_operating_data/annual_reports_2020_2025/highway_reviewed_operating_disclosure_data.csv
数据库/processed/highway_operating_data/annual_reports_2020_2025/highway_segment_business_evidence_eastmoney_2020_2025.csv
数据库/processed/highway_operating_data/annual_reports_2020_2025/v54h_repaired_2021/highway_reviewed_operating_formal_panel_v54h_repaired_2021_segment_filled.csv
数据库/processed/highway_v54h_joinquant_real_daily_prices.csv
数据库/processed/highway_v54h_joinquant_cash_dividends.csv
数据库/processed/highway_v54h_equal_weight_benchmark.csv
```

## Data Repair Result

| Item | Result |
| --- | ---: |
| 2020 disclosure rows added | 40 |
| CNINFO annual reports requested | 120 |
| CNINFO annual reports downloaded | 96 |
| Operating candidate snippets | 5,563 |
| Operating shortlist rows | 1,553 |
| PIT usable reviewed operating rows | 69 |
| 2020 annual PIT usable reviewed operating rows | 11 |
| 2020 annual PIT usable segment evidence rows | 14 |
| V5.4h formal panel rows | 193 |
| V5.4h formal rebalance dates | 21 |

Still missing CNINFO reports:

```text
001965.XSHE
601107.XSHG
601188.XSHG
601518.XSHG
```

## Formal Validation

Output:

```text
validation_formal_v54h_highway_repaired_2021_final/highway_dividend_reviewed_operating_v54h_repaired_2021/formal_validation_summary.json
```

Key result:

| Test | Result |
| --- | ---: |
| PIT leakage audit | pass |
| Date count | 21 |
| Equal-weight reviewed formal | 93.27% |
| High-dividend reviewed top8 | 91.94% |
| Composite current | 102.34% |
| Common-sample composite | 113.64% |
| Dividend yield mean IC | 0.1686 |
| Dividend yield mean RankIC | 0.1999 |

PM interpretation:

- The 2021 no-trade gap is repaired.
- Dividend yield remains the most financially explainable main signal.
- Highway revenue ratio and non-highway ratio still do not show strong independent alpha; they are better treated as gates or diagnostics.
- This is still not an accepted strategy because the 2021-2026 window is platform-confirmation and not clean forward evidence.

## Engineering Smoke Test

Output:

```text
local_daily_backtests_highway_v54h_repaired_2021_final/highway_dividend_reviewed_operating_v54h_repaired_2021/summary.json
```

Metrics:

| Metric | Value |
| --- | ---: |
| Signal count | 21 |
| First signal date | 2021-05-06 |
| Strategy return | 106.61% |
| Annualized return | 16.06% |
| Same-pool benchmark return | 58.10% |
| Excess return | 48.51% |
| Max drawdown | 14.91% |
| Sharpe | 0.936 |
| Information ratio | 0.654 |

The local daily runner now buys on 2021-05-06.

## JoinQuant Script

```text
exports/joinquant/highway_dividend_reviewed_operating_v54h_repaired_2021_joinquant_frozen_signals.py
```

Script contract:

- first frozen signal date is 2021-05-06;
- display benchmark is `000027.XSHG`;
- no defensive overlay;
- no stop loss or take profit;
- no return tuning;
- logs capital warnings when target value is below one lot.

## JoinQuant Platform Smoke Result

Source files reviewed:

```text
C:\Users\Administrator\Downloads\result_1 (18).csv
C:\Users\Administrator\AppData\Local\Temp\log (1).txt
```

Summary:

| Item | Result |
| --- | ---: |
| JoinQuant result strategy return | 104.26% |
| JoinQuant annualized return | 15.65% |
| JoinQuant display benchmark return | -16.31% |
| JoinQuant max drawdown | 14.98% |
| Local daily simulation strategy return | 106.61% |
| Local vs JoinQuant strategy-return gap | -2.35 pct pts |
| Rebalance logs | 21 |
| After-close position logs | 21 |
| First signal date | 2021-05-06 |
| First-day buy amount in result CSV | 1,989,525 |
| Capital warnings | 0 |
| ERROR lines | 9 |

PM interpretation:

- JoinQuant did buy on 2021-05-06. The repaired 2021 no-signal gap is fixed on platform.
- The displayed benchmark `000027.XSHG` is a transport index, not a pure highway benchmark. JoinQuant excess return is therefore not the formal sector-relative evidence.
- Most order messages are normal 100-share lot adjustments.
- The 9 true ERROR lines are execution-friction items, not a no-trade failure:
  - 1 paused-security close failure: `600012.XSHG` on 2023-04-03.
  - 7 sub-100-share open/close delta failures: tiny rebalance differences that JoinQuant rejected.
  - 1 cash-left sub-100-share failure: `000429.XSHE` on 2025-04-01, where remaining cash only allowed 6 shares.
- This smoke result is close to the local daily simulation and is good enough to proceed to full platform replication attribution.

Open replication work:

1. Export JoinQuant daily returns, transaction details, positions, and logs for V5.4h.
2. Run local-vs-JoinQuant daily attribution on net value, trades, holdings, cash, and dividends.
3. Only after the attribution gap is explained can this move from `platform_replication_ready` to `platform_replication_passed`.

## JoinQuant Platform Replication Attribution

Source files reviewed:

```text
C:\Users\Administrator\Downloads\result_1 (19).csv
C:\Users\Administrator\AppData\Local\Temp\transaction.csv
C:\Users\Administrator\AppData\Local\Temp\position.csv
```

Output:

```text
platform_replication_packets_highway_v54h/highway_dividend_reviewed_operating_v54h_repaired_2021/platform_replication_packet.json
```

Result:

| Item | Result |
| --- | ---: |
| Platform replication packet status | platform_replication_passed |
| Matched daily NAV days | 1,228 |
| Final local strategy return | 106.61% |
| Final JoinQuant strategy return | 104.26% |
| Final strategy-return gap | 2.35 pct pts |
| Max absolute strategy-return gap | 2.38 pct pts |
| Rebalance dates checked | 21 |
| Rebalance-date code mismatch count | 0 |
| JoinQuant transaction rows | 162 |
| Local transaction rows | 169 |
| Matched transaction keys | 157 |

Attribution interpretation:

- The local-vs-JoinQuant strategy NAV gap is within the configured platform replication threshold.
- The benchmark gap is intentionally large because local formal attribution uses the highway same-pool equal-weight benchmark, while JoinQuant display uses `000027.XSHG`.
- Remaining transaction quantity and value differences are mainly caused by local daily-open execution versus JoinQuant 09:40 market fills.
- `000828.XSHE` on 2024-10-08 was selected but not bought because it was limit-up. JoinQuant cancelled the buy order; the local runner also recorded `buy_skipped: high_limit`. The attribution tool was repaired so 0-share skipped holdings and cancelled 0-share orders are not counted as real positions or trades.

PM decision:

```text
platform_replication_passed
not_accepted_strategy
next_gate = forward / paper trading
```

## PM Decision

V5.4h passed JoinQuant platform replication attribution.

It supersedes V5.4g for the specific purpose of fixing the 2021 no-signal gap, but V5.4g should remain archived as the original reviewed-operating candidate.

Do not mark V5.4h as accepted. The next gate is forward / paper trading.

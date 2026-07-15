# JoinQuant Execution Matching Requires Real-Price Data

## Type

Caveat / Procedure

## Summary

Local execution backtests must use the same price and cash-flow mechanics as the execution platform. For JoinQuant comparison, stock execution should use unadjusted real prices, while benchmark display may require an adjusted benchmark series. Using V4 adjusted prices for execution can create large return gaps even when signals and order logic are correct.

## Context

This was discovered while comparing the Bank Value 15Y frozen-signal strategy between V5 local backtests and JoinQuant platform backtests.

## Evidence

- V5 ideal quarterly backtest showed materially higher returns than JoinQuant.
- Adding lot rounding, commissions, cash handling, and JoinQuant-like order logic only reduced a small part of the gap.
- Switching local daily execution from V4 adjusted prices to JoinQuant `get_price(fq=None)` real stock prices moved local strategy return close to JoinQuant.
- Example observed mismatch before correction:
  - JoinQuant execution price for `601077.XSHG` on 2021-07-01 was about `3.98`.
  - V4 adjusted local price for the same stock/date was about `2.97`.
- After collecting JoinQuant real data:
  - Local real-price daily strategy return: about `33.89%`.
  - JoinQuant platform strategy return: about `35.77%`.
  - Max drawdown interval matched: `2022-02-11` to `2022-11-03`.

## Implications

- Research panels may use adjusted total-return data for factor validation.
- Execution-matching backtests must use platform-consistent execution data:
  - stock open/close: JoinQuant `get_price(fq=None)`;
  - benchmark display series: JoinQuant adjusted benchmark series, currently `512800.XSHG` with `fq=pre`;
  - cash dividends: explicit cash events, net of the configured dividend tax assumption;
  - ex-dividend and payment dates: stored separately from price returns.
- Do not interpret local-vs-platform return gaps as strategy failure until price adjustment, benchmark, dividend, and execution semantics are aligned.

## Limits

This finding was based on one bank-sector value strategy. It should be retested across other strategy families, especially high-turnover or price-sensitive strategies.

## Related Files

- `src/v5/joinquant_real_data_runner.py`
- `src/v5/daily_backtest.py`
- `数据库/processed/joinquant_real_daily_prices.csv`
- `数据库/processed/joinquant_real_benchmark_prices.csv`
- `数据库/processed/joinquant_cash_dividends.csv`
- `local_daily_backtests_real_jq/bank_value_15y/summary.json`

## Last Updated

2026-07-15

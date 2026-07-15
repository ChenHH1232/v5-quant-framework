# Bank Value 15Y Defensive Overlay Research

## Research Question

Does Bank Value 15Y lack stop-loss, take-profit, and defensive-risk controls?

## Finding

Yes. The strategy specification included a defensive rule, but the executable local daily runner and JoinQuant frozen-signal export did not enforce it. There was no individual stock stop-loss or take-profit rule.

## Research Decision

Do not add individual fixed stop-loss or take-profit as the first risk layer.

Reason: Bank Value 15Y is a value-investing strategy. Fixed price stops can force selling precisely when valuation is becoming more attractive, and fixed take-profit can prematurely exit value re-rating. These rules may be useful later, but they need separate evidence and should not be added just because a backtest drawdown is uncomfortable.

Add a portfolio-level defensive overlay instead:

- Keep stock selection fixed.
- Use `512800.XSHG` bank ETF as the bank-sector state proxy.
- If the previous close of `512800.XSHG` is below its 252-trading-day moving average, reduce target stock exposure by 50%.
- Otherwise keep normal target exposure.
- Route the reduced exposure to cash.

## Validation Setup

- Window: `2021-05-01` to `2026-05-31`.
- Stock execution prices: JoinQuant `fq=None` real open/close.
- Benchmark: `512800.XSHG`, JoinQuant `fq=pre`.
- Cash dividends: explicit net cash events after 20% tax assumption.
- Selection model: unchanged frozen Bank Value 15Y signal.
- Target exposure baseline: `99.5%`.
- Defensive risk-off exposure: `49.75%`.

## Results

| Case | Return | Annualized | Excess | Max DD | Sharpe | Sortino | Vol | Beta | Risk-Off Days | Avg Cash |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 33.89% | 6.17% | 8.73% | 17.69% | 0.438 | 0.632 | 0.169 | 0.883 | 0.0% | 4.1% |
| MA126 | 28.42% | 5.27% | 3.26% | 13.09% | 0.421 | 0.607 | 0.148 | 0.741 | 38.1% | 23.1% |
| MA189 | 30.28% | 5.58% | 5.12% | 12.95% | 0.435 | 0.627 | 0.151 | 0.762 | 31.8% | 20.0% |
| MA252 | 31.29% | 5.75% | 6.13% | 13.03% | 0.438 | 0.632 | 0.155 | 0.789 | 28.7% | 18.4% |
| MA378 | 22.82% | 4.31% | -2.34% | 17.69% | 0.341 | 0.486 | 0.163 | 0.832 | 17.1% | 12.6% |

## Interpretation

The MA252 overlay reduces max drawdown from `17.69%` to `13.03%`, lowers volatility and beta, and preserves a positive excess return. It sacrifices about `2.60%` total return over the test window.

MA126 and MA189 reduce drawdown similarly, but they trigger more often and increase turnover. MA252 is preferred because it matches the original 12-month defensive rule in the strategy specification and avoids choosing a parameter only because it performed better in this sample.

## Decision

Status: accepted as a risk-control layer, not as new alpha evidence.

The Bank Value 15Y executable path now supports:

- `defensive_mode = benchmark_ma`
- `defensive_ma_days = 252`
- `defensive_risk_exposure = 0.5`

The JoinQuant frozen-signal export also implements the same defensive overlay.

## Remaining Risks

- This is not a clean untouched out-of-sample decision because it was researched after seeing the first platform runs.
- Defensive overlays can create hidden market-timing exposure.
- Daily risk-state changes may increase turnover around the moving average.
- Future tests should compare cash versus short-duration bond fund as the defensive asset.

## Related Files

- `src/v5/daily_backtest.py`
- `exports/joinquant/bank_value_15y_joinquant_frozen_signals_near5y.py`
- `local_daily_backtests_real_jq_baseline/bank_value_15y/summary.json`
- `local_daily_backtests_real_jq_defensive_ma252/bank_value_15y/summary.json`

# Bank Value Quality V2 Engineering Test Note

Date: 2026-07-15

## Status

`engineering_test_candidate_eastmoney_quality_proxy`

Bank Value Quality V2 is better structured than Bank Value 15Y as a research design, but it has not been statistically proven. The JoinQuant file is for platform simulation and execution checking only.

The current JoinQuant file embeds V4 Eastmoney annual-report extraction output for 2024 and 2025 bank quality indicators. These rows are marked `needs_check`, so they improve the engineering proxy but do not make V2 formally validated.

## Comparison With Bank Value 15Y

### Improvements

- Separates value alpha from value-trap controls.
- Makes dividend yield conditional on sustainability instead of treating high yield as automatically positive.
- Keeps defensive overlay outside alpha evidence.
- Requires rolling common-sample validation, ablation, baseline and robustness tests.
- Explicitly labels unvalidated claims as `hypothesis_only`.
- Uses a smaller and more concentrated portfolio design: 6 stocks, max 18 percent per position.

### Engineering Risks

- V2 depends more heavily on bank-specific indicators than V1.
- JoinQuant can directly provide `valuation.pb_ratio` and `indicator.roe`, but not stable point-in-time NPL trend, provision buffer, capital resilience or sustainable dividend yield.
- With the embedded Eastmoney quality CSV, the JoinQuant simulation can test V2 quality-layer mechanics after the relevant annual reports become visible.
- The embedded table covers 2024 and 2025 reports only. Earlier rebalances remain closer to the PB/ROE proxy unless older reviewed bank-specific indicators are added.
- Dividend sustainability is still not fully implemented because point-in-time dividend-yield support has not been attached to the JoinQuant file.
- Current `v5.spec` validates JSON structure but does not yet enforce V2 scoring semantics.

## JoinQuant Simulation File

Use:

- `exports/joinquant/bank_value_quality_v2_joinquant_near5y.py`

JoinQuant UI settings:

- Start date: `2021-05-01`
- End date: `2026-05-31`
- Benchmark: `512800.XSHG`
- Frequency: daily
- Use real price: enabled in code

## Degraded Proxy Rule

The current file includes `MANUAL_BANK_QUALITY_CSV` generated from:

`数据库/processed/eastmoney_bank_quality_manual_csv.csv`

The table is generated from V4 Eastmoney annual-report extraction and includes only rows that passed V5 sanity filters. If the table is empty, the strategy logs:

`WARNING manual bank quality table is empty; V2 is degraded to available PB/ROE proxy factors.`

The current Eastmoney proxy result can be used to test:

- whether the code runs on JoinQuant;
- whether orders are placed normally;
- whether 100-share lot rounding behaves reasonably;
- whether benchmark and real-price settings are compatible;
- whether the V2 value/quality two-layer score works mechanically;
- whether quality indicators change selected banks after 2024 reports become visible;
- whether local and platform execution paths are comparable.

It cannot be used to claim:

- V2 is statistically better than V1;
- bank quality factors are effective;
- value-trap guard is validated;
- dividend sustainability adds alpha.

## Required Next Validation

Before V2 can be considered better than V1, Quant Validation Agent must run:

- low-PB-only baseline;
- Bank Value 15Y baseline;
- equal-weight bank basket baseline;
- common-sample IC and RankIC;
- leave-one-factor-out ablation;
- weight perturbation robustness;
- rebalance-day robustness;
- dividend treatment sensitivity;
- rolling validation outside the 2021-05 to 2026-05 platform-confirmation window.

## Platform Test Result

JoinQuant simulation result reported by user on 2026-07-15:

- strategy return: 35.43 percent;
- annualized return: 6.37 percent;
- excess return: 7.05 percent;
- benchmark return: 26.51 percent;
- alpha: 0.016;
- beta: 0.837;
- Sharpe ratio: 0.145;
- win rate: 0.547;
- profit/loss ratio: 2.457;
- max drawdown: 18.08 percent;
- Sortino ratio: 0.203;
- excess max drawdown: 10.66 percent;
- excess Sharpe ratio: -0.296;
- daily win rate: 0.503;
- information ratio: 0.166;
- strategy volatility: 0.164;
- benchmark volatility: 0.168;
- max drawdown interval: 2021-07-06 to 2022-11-03.

Interpretation:

- The V2 Eastmoney quality proxy ran successfully on JoinQuant.
- Return is close to the previous near-5-year JoinQuant platform result for Bank Value 15Y, but slightly lower than the last reported 35.77 percent.
- Risk profile is slightly improved on beta, volatility and max drawdown versus the last reported 35.77 percent Bank Value 15Y platform result.
- This is still platform confirmation, not statistical acceptance.

## JoinQuant Compatibility Note

Do not use `DataFrame.attrs` in JoinQuant strategy files.

Reason:

- JoinQuant may run an older pandas version where `DataFrame.attrs` does not exist.
- The V2 proxy initially failed with `AttributeError: 'DataFrame' object has no attribute 'attrs'`.

Required pattern:

- Store debug metadata in `g.*`, for example `g.last_used_factors`.
- Or return `(dataframe, metadata)` from helper functions.
- Keep JoinQuant strategy code conservative and compatible with older pandas APIs.

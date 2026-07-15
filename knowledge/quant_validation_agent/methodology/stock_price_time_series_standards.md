# Stock Price Time-Series Statistical Standards

## Type

Methodology Card

## Purpose

This card defines the mandatory standards for Quant Validation Agent when analyzing stock prices, ETF prices, benchmark prices, factor-portfolio returns, and strategy daily net value series.

It is stricter than the general time-series card because stock price data has special problems: non-stationary levels, corporate actions, dividends, suspensions, limit moves, stale prices, microstructure noise, overlapping returns, and benchmark exposure.

## Evidence Level

Mixed `econometric_method`, `market_microstructure_awareness`, `asset_pricing_method`, and `V5_internal_rule`.

## Core Principle

Do not treat price levels as ordinary stationary observations.

In most V5 validation work, Quant Validation Agent should analyze:

- simple returns;
- log returns;
- excess returns;
- active returns;
- drawdowns;
- rolling beta;
- factor portfolio returns;
- non-overlapping forward returns;
- price-derived signals with explicit lookback windows.

Price levels may be analyzed only when the hypothesis explicitly concerns:

- valuation ratios;
- trend or moving-average state;
- cointegration;
- relative price spreads;
- drawdown from prior peak;
- distance from rolling high or low.

## Price And Return Definitions

Every validation report must declare which return definition is used:

- `raw_price_return`: unadjusted close-to-close price return.
- `pre_adjusted_return`: return from pre-adjusted prices.
- `post_adjusted_return`: return from post-adjusted prices.
- `cash_dividend_return`: explicit cash dividend divided by prior value.
- `total_return`: price return plus dividend return, or a verified total-return series.
- `excess_return`: strategy return minus benchmark return.
- `active_return`: portfolio return minus selected benchmark return.

Do not mix these definitions inside one evidence table unless the comparison is explicitly labeled as a dividend or adjustment sensitivity test.

## Price Adjustment And Dividend Rules

For stock-price validation:

- State whether prices are raw, pre-adjusted, post-adjusted, or total-return.
- If using raw prices, cash dividends must be represented explicitly when relevant.
- If using adjusted prices, do not add the same dividend cash again.
- Separate research total-return treatment from platform execution treatment.
- For local-vs-platform comparison, use the platform-compatible price and dividend treatment.
- For formal factor validation, prefer point-in-time total-return treatment or raw price plus explicit dividend data, with the treatment stated.

Failure to state price adjustment is a blocker.

## Stationarity Rules

Prices and index levels are usually non-stationary. Therefore:

- Do not regress one price level on another price level unless testing a cointegration hypothesis.
- Do not infer predictive power from trending price-level correlation.
- Prefer returns, changes, spreads, growth rates, valuation ratios, or rolling standardized deviations.
- If using rolling z-scores, compute mean and standard deviation using only past data inside the decision window.
- If using moving averages or momentum, define lookback and rebalance timing before testing.

## Overlapping Forward Returns

Overlapping forward returns create serial correlation.

Examples:

- using 20-day forward return for every daily observation;
- using quarterly holding-period returns on monthly dates;
- daily evaluating a strategy that rebalances monthly.

Required handling:

- mark the result as overlapping;
- use non-overlapping samples where feasible;
- use HAC/Newey-West style standard errors for mean or regression tests;
- report fold-level behavior, not only full-sample t-statistics;
- do not overstate significance.

## Autocorrelation And Stale Price Checks

Autocorrelation can come from:

- suspended stocks;
- stale last prices;
- low liquidity;
- daily limit-up or limit-down constraints;
- slow-moving fundamental variables;
- overlapping returns;
- smoothed net value series;
- repeated unchanged holdings.

Required checks:

- percentage of zero returns;
- suspension and paused-day count;
- limit-up/limit-down blocked days;
- ACF or Ljung-Box style diagnostic for return series;
- comparison of daily and lower-frequency returns;
- turnover and holding-period overlap.

If stale prices are material, report the evidence as `data_limited` or use a liquidity/tradability filter.

## Volatility And Tail Risk

Stock returns are heteroskedastic and fat-tailed.

Required outputs for strategy or factor portfolio returns:

- annualized volatility;
- rolling volatility;
- max drawdown and drawdown interval;
- downside deviation or Sortino;
- skewness and tail-loss periods when sample size permits;
- stress windows;
- volatility regime performance.

Do not rely on a single full-sample Sharpe ratio.

## Benchmark And Beta Standards

Bank-sector strategies must separate:

- absolute return;
- bank-sector beta;
- benchmark-relative active return;
- stock-selection contribution;
- cash or exposure effect.

Required benchmark checks:

- benchmark identity and price adjustment;
- benchmark start-date anchor;
- benchmark return path;
- rolling beta;
- correlation with benchmark;
- active return stability;
- benchmark mismatch risk.

For bank strategies, 512800.XSHG or another explicit bank-sector proxy should be tested when platform-compatible data exists.

## Factor Price-Signal Standards

For price-derived factors such as momentum, reversal, volatility, drawdown, moving average, or trend state:

- define lookback before validation;
- use only information available before the trade decision;
- exclude current-day close if orders execute before close;
- account for suspensions and limit days;
- test lookback robustness;
- test non-overlapping future returns;
- separate price signal from valuation or quality signals;
- compare against a simple baseline.

## Statistical Tests And Reporting

Recommended diagnostics:

- return summary by year and fold;
- rolling mean return;
- rolling volatility;
- rolling Sharpe or information ratio;
- drawdown path;
- ACF / Ljung-Box style autocorrelation check;
- HAC/Newey-West adjusted mean or regression inference when serial correlation is likely;
- beta and alpha versus benchmark;
- non-overlapping return spread when forward returns overlap;
- robustness across frequency: daily, weekly, monthly where appropriate.

The report must state whether each statistic is:

- descriptive only;
- in-sample evidence;
- out-of-sample evidence;
- platform-replication diagnostic.

## Decision Rules

Quant Validation Agent must not approve a price-related factor or strategy if:

- price adjustment is unclear;
- dividends are double-counted or omitted without label;
- price-level regression is used without stationarity or cointegration justification;
- overlapping returns are treated as independent;
- results are driven by one stress window or one rebound period;
- benchmark exposure explains most of the return but is reported as alpha;
- local-vs-platform price treatment is unresolved;
- the 2021-05 to 2026-05 platform-confirmation window is used for tuning.

## Handoff To Engineering Agent

When a candidate passes statistical review, hand off:

- required price adjustment;
- dividend treatment;
- execution price assumption;
- benchmark identity;
- rebalance timing;
- current-day data exclusion rule;
- suspension and limit-day handling;
- metrics that must be reproduced locally and on JoinQuant.


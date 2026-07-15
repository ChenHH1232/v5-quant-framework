# Time-Series Validation Methods

## Type

Methodology Card

## Purpose

This card defines how Quant Validation Agent should analyze time-series behavior in stock strategies, factor returns, macro variables, and defensive overlays.

## Evidence Level

Mixed `econometric_method`, `backtest_governance`, and `V5_internal_rule`. See [Statistical Methods References](../references/statistical_methods_references.md).

## Time-Series Questions

Quant Validation Agent should ask:

- Is the return series stable across time?
- Is alpha persistent after accounting for benchmark exposure?
- Are returns autocorrelated because of stale prices, smoothing, or overlapping holding periods?
- Does volatility cluster?
- Does the signal work only in one regime?
- Are macro or defensive variables known before the trading decision?

## Return Series Diagnostics

For any strategy, factor portfolio, or defensive overlay:

- daily, weekly, and monthly return summary;
- cumulative return;
- rolling return;
- rolling volatility;
- rolling Sharpe;
- drawdown path;
- turnover and exposure path;
- benchmark beta path;
- correlation with benchmark and sector ETF;
- tail loss periods.

## Stationarity And Transformation

Prices and many macro levels are often non-stationary. Returns, changes, spreads, growth rates, or z-scores may be more appropriate.

Rules:

- Do not regress one price level on another price level unless there is a cointegration hypothesis.
- For macro variables, distinguish level, change, acceleration, and surprise.
- For valuation ratios, test cross-sectional ranks and time-series deviations separately.
- If using rolling z-scores, define lookback length before validation.

## Autocorrelation

Autocorrelation can inflate significance.

Common causes:

- overlapping forward returns;
- slow-moving fundamental data;
- stale or suspended prices;
- monthly rebalancing measured with daily returns;
- defensive exposure changes that persist for long periods.

Required checks:

- autocorrelation function or Ljung-Box style diagnostic;
- HAC/Newey-West standard errors for serially correlated factor premia;
- non-overlapping return tests when feasible;
- rolling-window stability rather than one full-sample statistic.

## Volatility Clustering

Stock returns often have clustered volatility. A high average return in calm periods may not survive stress.

Required checks:

- rolling volatility;
- downside volatility;
- max drawdown and drawdown duration;
- stress-window performance;
- return distribution skewness and kurtosis;
- exposure during high-volatility states.

## Rolling Validation

Use rolling validation for single-model statistical evidence.

Suggested structure:

- choose a training window;
- choose a validation window;
- advance the window without looking ahead;
- keep preprocessing rules inside each training or decision window;
- report fold-by-fold results;
- aggregate without hiding failed folds.

For V5, rolling validation is the default evidence path. The 2021-05 to 2026-05 period is platform confirmation only.

## Walk-Forward Testing

Walk-forward testing should simulate the actual research-to-trading process:

1. Train or estimate using past data only.
2. Select parameters if the method requires them.
3. Trade the next validation period.
4. Roll forward.
5. Record every fold, including losing folds.

Failure modes:

- reusing full-sample winsorization thresholds;
- choosing lookback length after seeing all folds;
- changing rules after reviewing validation periods;
- ignoring failed folds.

## Defensive Overlay Tests

Defensive overlays are time-series exposure rules. They must be tested separately from stock-selection alpha.

Required outputs:

- exposure path;
- number and duration of risk-off periods;
- return impact;
- drawdown impact;
- turnover impact;
- missed rebound cost;
- parameter sensitivity;
- out-of-sample or rolling evidence.

Decision label:

- If it reduces drawdown but sacrifices return, label as `risk_control_candidate`.
- Do not relabel it as alpha unless it independently passes predictive tests.


# Factor Validation Methods

## Type

Methodology Card

## Purpose

This card defines how Quant Validation Agent should test stock-selection factors.

## Evidence Level

Mixed `asset_pricing_method`, `econometric_method`, and `V5_internal_rule`. See [Statistical Methods References](../references/statistical_methods_references.md).

## 1. Factor Preparation

Before testing:

- align factor timestamp to decision date;
- winsorize or cap extreme values using only training or current cross-section information;
- standardize within the investable universe if needed;
- decide whether to neutralize by industry, size, beta, liquidity, or other controls;
- record all preprocessing choices in the validation report.

For a single-sector bank universe, industry neutralization is usually not useful, but size, liquidity, listing age, and beta controls may still matter.

## 2. IC And RankIC

Use IC to test linear association between factor values and future returns.

Use RankIC to test monotonic rank association. RankIC is often more robust when factor values are nonlinear, skewed, or affected by outliers.

Required outputs:

- mean IC and RankIC;
- standard deviation;
- t-stat or HAC-adjusted t-stat when serial correlation is likely;
- positive-period ratio;
- rolling mean;
- date-level distribution;
- IC decay across holding horizons.

Interpretation rules:

- Sign must match the financial hypothesis.
- Stability matters more than one high average.
- IC must be tested on common samples when comparing factors.
- A small bank universe can make IC noisy; breadth must be reported.

## 3. Quantile Spread

Sort stocks into quantiles or groups by factor score and compare future returns.

For a small bank universe, terciles or top/bottom groups may be more realistic than deciles.

Required outputs:

- group count by date;
- average forward return by group;
- top-minus-bottom spread;
- long-only top group return;
- turnover;
- transaction-cost sensitivity;
- rolling spread stability.

Failure modes:

- the spread is driven by one stock;
- top group has too few names;
- bottom group is not investable or includes suspended names;
- turnover makes the signal uneconomic.

## 4. Fama-MacBeth Regression

Use Fama-MacBeth when testing whether factor exposure explains cross-sectional returns after controls.

Basic process:

1. Run cross-sectional regression each period:
   `future_return_i,t = a_t + b_t * factor_i,t + controls_i,t + error_i,t`
2. Average coefficients over time.
3. Test whether average coefficient differs from zero.
4. Use robust or HAC-aware inference when serial correlation exists.

Usage rules:

- Do not over-control away the intended economic mechanism.
- Report sample size per period.
- Avoid too many controls when the universe is small.
- Prefer simple controls first: size, beta, liquidity, valuation baseline.

## 5. Baseline Tests

Every new factor must beat or improve a relevant baseline.

Examples:

- equal-weight bank basket;
- low-PB only;
- dividend-yield only;
- current composite without the new factor;
- sector ETF or bank index for strategy-level attribution.

Acceptance standard:

- improvement must be visible on common samples;
- improvement cannot rely only on one recent platform-confirmation window;
- improvement must be explainable by the factor's financial mechanism.

## 6. Ablation Tests

For composite strategies, remove one component at a time:

- valuation-only;
- valuation plus quality;
- valuation plus dividend;
- valuation plus capital;
- current full composite;
- composite without each factor.

The goal is to identify whether a component adds evidence or only adds complexity.

Do not accept a component because it improves one cumulative return chart. Require rolling and common-sample evidence.

## 7. Multiple-Horizon Testing

Test horizons should match the strategy design:

- short horizon: 1 to 5 trading days for execution and reversal checks;
- medium horizon: 20 to 60 trading days for monthly or quarterly rebalance;
- long horizon: 120 to 252 trading days for slow fundamental factors.

Report IC decay. A fundamental factor that only works at one hand-picked horizon needs extra skepticism.

## Required Decision Labels

- `reject`: sign is wrong, unstable, or explained by leakage/noise.
- `needs_more_data`: plausible but insufficient coverage or history.
- `research_candidate`: financially plausible and statistically promising.
- `risk_control_candidate`: useful for exposure or drawdown control, not alpha evidence.
- `approved_for_engineering`: passes statistical, governance, and reproducibility checks.


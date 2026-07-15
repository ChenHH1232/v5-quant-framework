# Robustness And Overfitting Controls

## Type

Governance / Methodology Card

## Purpose

This card defines how Quant Validation Agent should detect fragile results, multiple-testing risk, and backtest overfitting.

## Evidence Level

Mixed `backtest_governance`, `econometric_method`, and `V5_internal_rule`. See [Statistical Methods References](../references/statistical_methods_references.md).

## Overfitting Warning Signs

Treat a result as high risk if:

- the best result uses a very specific date range;
- parameter changes slightly destroy performance;
- many factors were tried but only winners are reported;
- only cumulative return is shown;
- transaction costs are ignored;
- rebalancing day is hand-picked;
- benchmark or dividend treatment changes the conclusion;
- performance is concentrated in one regime;
- the strategy cannot be explained financially.

## Robustness Matrix

A formal validation report should include a robustness matrix:

- rebalance frequency: monthly, quarterly, semiannual if relevant;
- rebalance day: first, middle, last available trading day;
- holding period: one period and multiple-period decay;
- winsorization: none, 1 percent, 2.5 percent, 5 percent;
- standardization: raw, rank, z-score;
- universe filter: full, coverage-filtered, liquidity-filtered;
- benchmark: bank ETF, bank index, equal-weight bank basket;
- transaction cost: base, high-cost, no-cost diagnostic;
- dividend treatment: price return, cash dividend, total return where appropriate.

Acceptance standard:

- the sign and broad conclusion should survive reasonable choices;
- the exact performance number does not need to match across all choices;
- if one choice drives the result, the report must flag `fragile`.

## Common-Sample Rule

When comparing factors, use the same dates and stocks.

Report both:

- factor's own available sample;
- common sample shared by all compared factors.

If the conclusion reverses in common sample, do not promote the factor.

## Multiple Testing

Every tested variant consumes research degrees of freedom.

Quant Validation Agent should record:

- number of factors tested;
- number of parameter variants;
- number of windows or horizons;
- number of benchmark alternatives;
- number of rejected ideas.

Do not present the best surviving variant as if it was the only idea tested.

## Purging And Embargo

For machine-learning or overlapping-label validation:

- purge training observations whose labels overlap the validation window;
- embargo a short period after validation labels when leakage could occur;
- choose embargo length based on label horizon and data-release lag;
- document the rule before testing.

This is especially important when predicting future returns over 20, 60, 120, or 252 trading days.

## Placebo And Negative Controls

Use placebo checks to detect accidental leakage:

- shuffled factor values;
- delayed signal beyond plausible usefulness;
- future-shifted signal as a leakage detector;
- random rebalance dates;
- irrelevant factor with no financial mechanism.

If placebo tests perform similarly to the proposed factor, mark the evidence as unreliable.

## Stress And Regime Robustness

Split results by:

- bull, bear, and range-bound market;
- high and low volatility;
- rising and falling rate periods;
- credit stress and credit calm periods;
- real estate stress periods for bank strategies;
- pre- and post-major regulation or accounting changes.

Regime splits are diagnostic. They should not become new tuned rules without a separate validation plan.

## Final Overfitting Verdict

Use one of:

- `low_overfitting_risk`: simple rule, pre-specified, stable across windows and variants.
- `medium_overfitting_risk`: plausible but needs more rolling evidence.
- `high_overfitting_risk`: narrow window, many tries, unstable, or insufficient documentation.
- `invalid`: leakage, future data, survivorship bias, or unreproducible data.


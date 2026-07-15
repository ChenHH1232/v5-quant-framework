# Stock Statistical Analysis Framework

## Type

Validation Framework

## Purpose

This card defines the default validation sequence for stock and factor research. It is designed for Quant Validation Agent use after Research Agent has produced a financial hypothesis and factor specification.

## Evidence Level

Mixed `asset_pricing_method`, `econometric_method`, `backtest_governance`, and `V5_internal_rule`. See [Statistical Methods References](../references/statistical_methods_references.md).

## Default Validation Order

1. Data integrity check.
2. Point-in-time alignment check.
3. Universe and sample coverage check.
4. Factor distribution and outlier check.
5. Cross-sectional predictive test.
6. Time-series stability test.
7. Baseline and ablation test.
8. Robustness test.
9. Overfitting and data-snooping review.
10. Performance attribution.
11. Decision report.

## Data Integrity Checks

Quant Validation Agent must check:

- missing values by date and stock;
- duplicate observations;
- impossible prices or returns;
- stock suspension and limit-up/limit-down handling;
- reporting date versus announcement date;
- survivorship bias in the universe;
- delisted, newly listed, ST, and suspended securities;
- dividend, split, ex-right, and price-adjustment consistency.

## Point-In-Time Rule

Every observation must be available before the decision date. If a factor uses financial statements, use announcement-date alignment, not period-end alignment.

If true point-in-time data is unavailable, the report must label the result as `data_limited` and not as accepted evidence.

## Universe Rule

Use the same investable universe for all factors in a common-sample test. If one factor has weaker coverage, report:

- full-sample result;
- common-sample result;
- coverage ratio by rebalancing date;
- dates rejected by the sample coverage filter.

## Statistical Evidence Hierarchy

Strong evidence usually requires:

- economically meaningful sign;
- stable IC or RankIC direction;
- rolling-window consistency;
- top-minus-bottom spread that survives realistic trading assumptions;
- improvement over a simple baseline;
- no obvious concentration in one stock, one year, or one regime;
- robustness to rebalance day, holding period, winsorization, and neutralization choices.

Weak evidence includes:

- one impressive cumulative return curve;
- one lucky test window;
- high return with low breadth;
- signal only visible after parameter search;
- performance driven by dividend or benchmark treatment mismatch;
- unexplained result that conflicts with financial logic.

## Required Outputs

For each validation task, produce:

- data window and sample definition;
- factor definition and lag rule;
- universe construction rule;
- missing-data and coverage report;
- IC, RankIC, and spread table if cross-sectional;
- rolling stability chart or table;
- baseline comparison;
- robustness matrix;
- overfitting review;
- final status: `reject`, `needs_more_data`, `risk_control_candidate`, `research_candidate`, or `approved_for_engineering`.

## V5 Usage Notes

For Bank Value 15Y, the 2021-05 to 2026-05 window must be treated as platform-confirmation context only. It can compare local execution to JoinQuant, but it must not be used to choose factors, tune thresholds, accept defensive overlays, or declare alpha.


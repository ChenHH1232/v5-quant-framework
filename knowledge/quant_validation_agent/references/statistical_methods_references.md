# Statistical Methods References

## Purpose

This file is the citation map for Quant Validation Agent methodology cards. The references support statistical testing design. They do not validate any V5 factor or strategy by themselves.

## Evidence Labels

- `econometric_method`: statistical method, estimator, or inference framework.
- `asset_pricing_method`: asset-pricing or factor-testing method.
- `backtest_governance`: source about data snooping, overfitting, or validation design.
- `V5_internal_rule`: project-specific governance rule.
- `implementation_reference`: software or data-platform behavior reference.

## Cross-Sectional Asset Pricing And Factor Testing

1. Fama, E. F. and MacBeth, J. D. (1973), "Risk, Return, and Equilibrium: Empirical Tests", Journal of Political Economy. DOI: [10.1086/260061](https://doi.org/10.1086/260061). Evidence label: `asset_pricing_method`. Use for two-pass cross-sectional regressions and time-series averaging of risk premia.
2. Fama, E. F. and French, K. R. (1992), "The Cross-Section of Expected Stock Returns", Journal of Finance. DOI: [10.1111/j.1540-6261.1992.tb04398.x](https://doi.org/10.1111/j.1540-6261.1992.tb04398.x). Evidence label: `asset_pricing_method`. Use for value, size, beta, and cross-sectional return framing.
3. Fama, E. F. and French, K. R. (1993), "Common Risk Factors in the Returns on Stocks and Bonds", Journal of Financial Economics. DOI: [10.1016/0304-405X(93)90023-5](https://doi.org/10.1016/0304-405X(93)90023-5). Evidence label: `asset_pricing_method`. Use for factor-model attribution and alpha estimation.

## Econometric Inference

1. Newey, W. K. and West, K. D. (1987), "A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix", Econometrica. DOI: [10.2307/1913610](https://doi.org/10.2307/1913610). Evidence label: `econometric_method`. Use for HAC standard errors when returns or factor premia are serially correlated.
2. White, H. (1980), "A Heteroskedasticity-Consistent Covariance Matrix Estimator and a Direct Test for Heteroskedasticity", Econometrica. DOI: [10.2307/1912934](https://doi.org/10.2307/1912934). Evidence label: `econometric_method`. Use for heteroskedasticity-robust inference.
3. Ljung, G. M. and Box, G. E. P. (1978), "On a Measure of Lack of Fit in Time Series Models", Biometrika. DOI: [10.1093/biomet/65.2.297](https://doi.org/10.1093/biomet/65.2.297). Evidence label: `econometric_method`. Use for autocorrelation diagnostics.
4. Dickey, D. A. and Fuller, W. A. (1979), "Distribution of the Estimators for Autoregressive Time Series With a Unit Root", Journal of the American Statistical Association. DOI: [10.2307/2286348](https://doi.org/10.2307/2286348). Evidence label: `econometric_method`. Use for unit-root and stationarity checks.
5. Engle, R. F. (1982), "Autoregressive Conditional Heteroscedasticity with Estimates of the Variance of United Kingdom Inflation", Econometrica. DOI: [10.2307/1912773](https://doi.org/10.2307/1912773). Evidence label: `econometric_method`. Use for volatility clustering awareness.
6. Johansen, S. (1988), "Statistical Analysis of Cointegration Vectors", Journal of Economic Dynamics and Control. DOI: [10.1016/0165-1889(88)90041-3](https://doi.org/10.1016/0165-1889(88)90041-3). Evidence label: `econometric_method`. Use for cointegration analysis only when the hypothesis requires long-run equilibrium testing.

## Backtest Governance And Overfitting

1. White, H. (2000), "A Reality Check for Data Snooping", Econometrica. DOI: [10.1111/1468-0262.00152](https://doi.org/10.1111/1468-0262.00152). Evidence label: `backtest_governance`. Use for multiple-testing and data-snooping caution.
2. Bailey, D. H., Borwein, J. M., Lopez de Prado, M. and Zhu, Q. J. (2014), "The Probability of Backtest Overfitting". [SSRN](https://ssrn.com/abstract=2326253). Evidence label: `backtest_governance`. Use for strategy-selection overfitting awareness.
3. Bailey, D. H. and Lopez de Prado, M. (2014), "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality". [SSRN](https://ssrn.com/abstract=2460551). Evidence label: `backtest_governance`. Use for Sharpe ratio interpretation under multiple trials.
4. Lopez de Prado, M. (2018), "Advances in Financial Machine Learning", Wiley. Evidence label: `backtest_governance`. Use for purging, embargo, and time-series cross-validation concepts.

## V5 Internal Rules

1. `docs/governance/platform_confirmation_candidate_v1.md`. Evidence label: `V5_internal_rule`. Use for the rule that 2021-05 to 2026-05 is platform confirmation only, not tuning or model acceptance.
2. `docs/BANK_VALUE_15Y_LEAKAGE_AUDIT.md`. Evidence label: `V5_internal_rule`. Use for leakage and sample-pollution constraints.
3. `docs/BANK_VALUE_15Y_PROCESS_REVIEW.md`. Evidence label: `V5_internal_rule`. Use for workflow weaknesses found in the first Bank Value 15Y test.

## Source Limitations

- General asset-pricing methods do not automatically transfer to small single-sector universes.
- Econometric significance can be fragile when the bank universe has few stocks.
- Robust standard errors reduce inference risk but do not fix bad data, look-ahead bias, or overfitting.
- Machine-learning validation methods require careful label definition and embargo length; they are not a substitute for financial reasoning.


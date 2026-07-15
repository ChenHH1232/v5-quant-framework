# Performance Attribution And Risk Metrics

## Type

Methodology Card

## Purpose

This card defines the minimum risk and attribution report expected from Quant Validation Agent for stock strategies and factor portfolios.

## Evidence Level

Mixed `asset_pricing_method`, `econometric_method`, and `V5_internal_rule`. See [Statistical Methods References](../references/statistical_methods_references.md).

## Core Performance Metrics

Report:

- total return;
- annualized return;
- benchmark return;
- excess return;
- annualized volatility;
- benchmark volatility;
- Sharpe ratio;
- Sortino ratio;
- max drawdown;
- max drawdown interval;
- Calmar ratio if useful;
- win rate;
- profit/loss ratio;
- daily win rate;
- information ratio;
- beta;
- alpha;
- turnover;
- average exposure;
- cash ratio.

For platform comparisons, match the platform's metric definitions where possible and document any mismatch.

## Drawdown Analysis

Drawdown report should include:

- start date;
- valley date;
- recovery date if recovered;
- max drawdown depth;
- drawdown duration;
- portfolio holdings during drawdown;
- benchmark drawdown over the same interval;
- whether loss came from sector beta, stock selection, execution, dividend treatment, or defensive overlay.

## Attribution Layers

For V5 bank strategies, separate:

1. Benchmark return.
2. Sector beta exposure.
3. Stock-selection return.
4. Rebalancing effect.
5. Dividend cashflow effect.
6. Transaction-cost effect.
7. Cash or defensive exposure effect.
8. Execution-price difference.

This layer is required before comparing local results with JoinQuant results.

## Alpha And Beta

Estimate beta and alpha against a relevant benchmark:

- bank ETF or bank index for bank-sector strategies;
- broad market benchmark only as secondary context;
- equal-weight bank basket when checking stock-selection skill.

Rules:

- Do not claim alpha if the benchmark is wrong.
- Use robust inference if daily residuals are autocorrelated or heteroskedastic.
- Report rolling beta when exposure changes materially.

## Information Ratio

Information ratio should use active return versus the chosen benchmark.

Check:

- active return mean;
- active return volatility;
- active drawdown;
- rolling information ratio;
- correlation of active return with benchmark return.

If active return is unstable or concentrated in a few periods, do not rely on the full-sample information ratio.

## Turnover And Trading Feasibility

Report:

- one-way turnover;
- two-way turnover if available;
- number of trades;
- average position size;
- minimum lot constraint;
- cash drag from lot rounding;
- suspension and limit-up/limit-down failed trades;
- transaction-cost sensitivity.

For China A-shares, account for board-lot constraints, stamp duty if selling, commission assumptions, slippage, and platform-specific execution rules.

## Dividend And Corporate Action Attribution

Separate:

- price return;
- cash dividend return;
- tax or withholding assumptions;
- ex-right date price adjustment;
- payment date cash arrival;
- total-return series when available.

For local-vs-platform comparison, record whether the platform uses raw price, pre-adjusted price, post-adjusted price, or explicit cash dividend accounting.

## Decision Use

Performance attribution can explain a strategy result, but it cannot replace factor validation.

If a strategy has strong return but weak factor evidence, mark it as `needs_more_data` or `research_candidate`, not `approved_for_engineering`.


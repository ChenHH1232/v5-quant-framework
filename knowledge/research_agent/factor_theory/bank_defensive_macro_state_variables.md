# Bank Defensive And Macro State Variables

## Type

Research Framework / Defensive Overlay

## Summary

Bank stocks are sensitive to credit cycles, interest-rate cycles, liquidity conditions, and policy expectations. Defensive overlays should control portfolio exposure to unfavorable states without changing the stock-selection thesis.

## Core Principle

Defensive state variables are risk-control tools. They should not be used to claim that the stock-selection model has better alpha.

## Candidate State Variables

### Bank Sector Trend

Proxy:

- `512800.XSHG` bank ETF;
- CSI bank index;
- bank sector relative strength versus broad market.

Hypothesis:

When the bank sector trades below its 12-month moving average, sector-level downside risk is elevated.

Implementation candidate:

- risk-on: target exposure near normal level;
- risk-off: reduce exposure by 50%;
- decision uses previous close to avoid look-ahead.

### Credit Cycle Stress

Proxy:

- NPL ratio deterioration;
- special mention loan ratio;
- credit cost;
- real estate loan stress;
- bond credit spread if available.

Hypothesis:

Credit deterioration reduces bank book-value credibility and should reduce value exposure.

### Interest Rate And NIM State

Proxy:

- net interest margin trend;
- policy rate;
- yield-curve slope;
- deposit repricing pressure.

Hypothesis:

Banks with stronger deposit franchises benefit more from favorable rate/NIM states.

### Liquidity And Funding State

Proxy:

- interbank funding rate;
- repo rate;
- deposit growth;
- loan-to-deposit ratio.

Hypothesis:

Liquidity stress hurts banks with weaker funding structures and higher wholesale funding reliance.

### Macro Growth And Real Estate State

Proxy:

- credit impulse;
- social financing growth;
- property sales/investment indicators;
- local government financing stress proxies.

Hypothesis:

Bank equity risk rises when macro growth slows and credit-risk-sensitive assets deteriorate.

## Defensive Overlay Governance

Before activating a defensive variable:

- define the economic mechanism before testing;
- keep stock selection fixed;
- report exposure and turnover;
- compare against no-overlay baseline;
- test across multiple windows;
- avoid choosing parameters only because they worked in the latest period.

## Current Bank Value 15Y Status

The current defensive overlay is a risk-control candidate:

- trigger: bank ETF previous close below 252-day moving average;
- action: reduce target exposure by 50%;
- defensive asset: cash;
- status: not accepted as alpha evidence.

## Future Research

- Compare cash versus short-duration bond fund as defensive asset.
- Test whether credit-cycle variables improve drawdown control beyond bank ETF trend.
- Separate sector timing value from stock-selection alpha.

## Last Updated

2026-07-15

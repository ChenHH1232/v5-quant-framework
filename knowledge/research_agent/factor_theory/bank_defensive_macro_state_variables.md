# Bank Defensive And Macro State Variables

## Type

Citation-Backed Research Framework / Defensive Overlay

## Summary

Bank stocks are sensitive to credit cycles, interest-rate cycles, liquidity conditions, and policy expectations. Defensive overlays should control portfolio exposure to unfavorable states without changing the stock-selection thesis.

Evidence level: mixed `regulatory_definition`, `academic_evidence`, `industry_disclosure`, `V5_internal_finding`, and `hypothesis_only`. Defensive overlays are risk-control candidates, not alpha evidence. See [Bank Sector Research References](../references/bank_sector_references.md).

## Core Principle

Defensive state variables are risk-control tools. They should not be used to claim that the stock-selection model has better alpha.

## Candidate State Variables

### Bank Sector Trend

Proxy:

- `512800.XSHG` bank ETF;
- CSI bank index;
- bank sector relative strength versus broad market.

Evidence trail:

- `industry_disclosure`: 512800 tracks the CSI Bank Index according to Huabao Fund disclosures.
- `regulatory_definition`: CSI methodology defines index construction and corporate-action handling.
- `hypothesis_only`: trend state predicts sector downside risk.

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

Evidence trail:

- `regulatory_definition`: bank asset-quality indicators are defined in regulatory and disclosure frameworks.
- `academic_evidence`: BIS credit-gap research supports credit excess as an early-warning macroprudential indicator.
- `hypothesis_only`: these variables improve V5 exposure control for bank equities.

Hypothesis:

Credit deterioration reduces bank book-value credibility and should reduce value exposure.

### Interest Rate And NIM State

Proxy:

- net interest margin trend;
- policy rate;
- yield-curve slope;
- deposit repricing pressure.

Evidence trail:

- `regulatory_definition`: PBOC and China Money publish LPR and rate-market information.
- `academic_evidence`: deposit-franchise research links deposit pricing power to bank interest-rate sensitivity.
- `hypothesis_only`: rate/NIM state improves bank-stock selection or defensive allocation.

Hypothesis:

Banks with stronger deposit franchises benefit more from favorable rate/NIM states.

### Liquidity And Funding State

Proxy:

- interbank funding rate;
- repo rate;
- deposit growth;
- loan-to-deposit ratio.

Evidence trail:

- `industry_disclosure`: listed banks disclose deposit and funding structure at low frequency.
- `hypothesis_only`: liquidity stress has cross-sectional or exposure-control value for V5.

Hypothesis:

Liquidity stress hurts banks with weaker funding structures and higher wholesale funding reliance.

### Macro Growth And Real Estate State

Proxy:

- credit impulse;
- social financing growth;
- property sales/investment indicators;
- local government financing stress proxies.

Evidence trail:

- `regulatory_definition`: PBOC social financing and NBS real estate releases provide macro state inputs.
- `academic_evidence`: credit-cycle literature supports macroprudential warning variables.
- `hypothesis_only`: China bank equity response must be tested by V5.

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

Evidence level: `V5_internal_finding`. The 2021-05 to 2026-05 result is platform-confirmation context only, not tuning evidence.

## Future Research

- Compare cash versus short-duration bond fund as defensive asset.
- Test whether credit-cycle variables improve drawdown control beyond bank ETF trend.
- Separate sector timing value from stock-selection alpha.

## Claims Downgraded To `hypothesis_only`

- Bank ETF trend below a 12-month moving average predicts elevated downside risk.
- Credit-cycle stress variables improve exposure control.
- Rate/NIM state improves cross-sectional or allocation decisions.
- Liquidity and funding stress variables improve downside control.
- Real estate and macro growth variables improve bank-sector risk management.

## Research Agent Usage Notes

- Use this card only for defensive and macro-state research design.
- Keep stock-selection alpha and exposure-control effects separated.
- Any defensive rule must use previous available observations and point-in-time macro release dates.
- Quant Validation Agent must compare no-overlay baseline, fixed-threshold overlay, rolling-trained overlay, turnover, cash drag and stress-period behavior.

## References

- [Bank Sector Research References](../references/bank_sector_references.md)
- Huabao CSI Bank ETF 512800 disclosures.
- China Securities Index methodology.
- PBOC LPR and social-financing data.
- NBS real estate statistical releases.
- BIS credit-gap and macroprudential research.

## Last Updated

2026-07-15

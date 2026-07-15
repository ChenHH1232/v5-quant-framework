# Bank Value Quality V2 Research Proposal

Date: 2026-07-15

## Status

`engineering_test_candidate_eastmoney_quality_proxy_pending_quant_validation`

This is a new bank-sector value-investing strategy proposal. It is not an accepted strategy and must not be treated as proven by Bank Value 15Y historical results.

Current engineering proxy note:

- V4 Eastmoney annual-report extraction has been migrated into V5 for 2024 and 2025 bank quality indicators.
- The migrated values are `needs_check`, so they can support engineering simulation but not formal factor acceptance.
- Earlier rebalances still need older reviewed bank-specific indicators before the full V2 quality layer can be tested across the full 15-year research window.

## Purpose

Bank Value Quality V2 turns the current V5 knowledge base into a cleaner research design:

- use valuation as the primary return hypothesis;
- use profitability, asset quality, provision buffer and capital strength to avoid value traps;
- treat dividend yield as a shareholder-return signal only when sustainability is visible;
- keep defensive overlays separate as risk-control candidates;
- validate by rolling common-sample tests instead of tuning on 2021-05 to 2026-05.

## Research Thesis

Bank stocks may be mispriced when low valuation reflects excessive pessimism rather than impaired book value. However, low P/B can also signal a rational value trap. The strategy therefore ranks banks by value and dividend attractiveness only after checking whether profitability, asset quality, provisioning and capital adequacy support the book value and future dividend capacity.

## Factor Families

### Primary Value Layer

- `low_price_to_book`
- `sustainable_dividend_yield`

Purpose:

Identify banks that are cheap relative to visible book equity and shareholder cash-return capacity.

Evidence status:

`hypothesis_only`. General value and bank-valuation literature supports plausibility, but V5 must validate predictive power on point-in-time A-share bank data.

### Quality And Value-Trap Layer

- `roe_quality`
- `asset_quality_trend`
- `provision_buffer`
- `capital_resilience`

Purpose:

Avoid cheap banks where reported book value, dividend capacity or future profitability may be impaired.

Evidence status:

`hypothesis_only`. Regulatory and disclosure sources define these variables, but their return-predictive value requires rolling validation.

## Portfolio Design

- Universe: point-in-time A-share listed banks.
- Rebalance: quarterly, after financial disclosure visibility checks.
- Selection count: 6.
- Weighting: equal weight after value-trap guard.
- Max position weight: 18 percent.
- Stop-loss/take-profit: disabled by default.
- Defensive overlay: bank ETF MA252 only as a separately tested risk-control candidate.

## What Changed Versus Bank Value 15Y

- The strategy explicitly separates value alpha from value-trap control.
- The value-trap guard is no longer a vague quality filter; it is a defined research hypothesis.
- The 2021-05 to 2026-05 period is not an acceptance or tuning window.
- Defensive overlay is kept out of alpha evidence.
- Required validation now includes common-sample rolling tests, ablation, baseline comparison and dividend-treatment sensitivity.

## Required Quant Validation

Quant Validation Agent must test:

- IC and RankIC for each factor;
- top-minus-bottom or top-group spread;
- rolling fold stability;
- low-PB-only baseline;
- equal-weight bank basket baseline;
- common-sample factor comparison;
- leave-one-factor-out ablation;
- weight perturbation robustness;
- rebalance-day robustness;
- transaction-cost and lot-rounding sensitivity;
- dividend treatment sensitivity;
- local-vs-JoinQuant daily attribution.

## Required Decision Rule

Project Manager Agent may move this strategy to `approved_for_engineering` only if:

- factor signs match the financial thesis;
- rolling results are not concentrated in one regime;
- the value-trap layer improves common-sample evidence versus low-PB-only;
- data lineage is point-in-time and reproducible;
- local execution attribution is close enough to platform behavior;
- no acceptance conclusion relies on the 2021-05 to 2026-05 platform-confirmation window.

## References

- [Bank Sector Research References](../knowledge/research_agent/references/bank_sector_references.md)
- [Quant Validation Statistical Methods References](../knowledge/quant_validation_agent/references/statistical_methods_references.md)
- [Strategy Spec](../examples/bank_value_quality_v2_strategy.json)

# Bank Knowledge Collection Report

Status: in progress.

## Sources Collected

- Official and regulatory source register completed in `source_register_bank_sector.md`.
- First-pass regulatory definitions completed in `bank_regulatory_definitions.md`.
- First-pass academic theory sources completed in `bank_academic_theory_sources.md`.
- First-pass Snowball high-dividend bank-stock market-view notes completed in `bank_market_view_hypotheses.md`.

## Strongest Theory-Backed Hypotheses

- Low PB may represent value only when book value is credible and profitability/asset quality/capital support it.
- ROE and profitability quality may improve valuation interpretation, but must be adjusted for leverage, provisioning and cyclicality.
- Asset-quality deterioration and capital weakness are plausible bank value-trap indicators.
- Credit-cycle and rate-state variables are plausible defensive state variables, not accepted alpha signals.

## Market-View-Only Hypotheses

- High dividend yield should be filtered by ROE stability, capital adequacy and dividend sustainability.
- Bank PB can be interpreted through ROE, payout ratio, growth and required return, rather than a universal PB threshold.
- Dividend yield relative to bond or wealth-management yields may explain income-oriented demand for bank stocks.
- Multi-factor bank rankings should avoid duplicated indicators and should include asset-quality metrics such as overdue/NPL and loan provision ratio where available.
- Regional banks may require bank-type, size, liquidity, regional economy and asset-quality controls.

## Data Gaps

- Point-in-time dividend announcement, ex-dividend and payment-date data.
- Bank-specific fields from annual/interim reports: NPL, special mention loans, overdue loans, provision coverage, loan provision ratio, NIM, CET1 and capital adequacy.
- Release-date-aware macro variables and rate/yield alternatives.
- Ownership/crowding data if testing market-view claims about fund crowding.

## Crawler / Access Limitations

- CNINFO and annual-report PDFs remain `manual_download_required` for safe, selective collection.
- Snowball high-dividend bank-stock pages are mixed: selected discussion pages are `public_access_partial`, but profile pages, stock hot pages and many article pages require `manual_review_required`.
- WeChat links inside Snowball discussions are `manual_review_required`.
- Paywalled academic and broker research sources remain `paid_or_restricted`.

## Ready For Quant Validation

- Raw high dividend yield versus sustainable high dividend yield.
- PB/ROE/payout-implied valuation gap versus raw PB.
- Dividend-yield spread over risk-free or low-risk income proxies.
- High-yield value-trap interaction with ROE, capital, NPL trend and provision buffer.
- Deduplicated bank quality score versus equal-weighted multi-factor ranking.
- Regional-bank stability filter by bank type and liquidity.

## Rejected Or Downgraded Hypotheses

- Single-stock conviction posts are excluded from factor evidence.
- Big-V identity, popularity and comment volume are excluded.
- Fixed PB/dividend-yield thresholds are downgraded unless conditioned on ROE, payout, capital, asset quality and rate regime.
- Hong Kong-only high-dividend discussions are excluded from the A-share strategy unless separately scoped.
- Short-term tactical/T+0 comments are excluded from long-horizon value strategy design.

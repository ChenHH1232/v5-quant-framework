# V5.7f Dividend Low-Vol Cash-Flow Enhanced ETF PM Decision

Date: 2026-07-19

## PM Decision

V5.7f is promoted to the current `formal_etf_candidate_not_accepted` line for the dividend low-volatility cash-flow enhanced ETF project.

It is not an accepted strategy and not live-trading approved. The next gates are platform replication preparation and forward / paper-trading records.

## Why V5.7f Becomes The Main Line

V5.7 exposed an important problem: a pure cross-sector OCF score produced strong local results, but bank stocks disappeared from the selected basket because banks do not have a comparable non-financial OCF-yield field.

V5.7b fixed bank inclusion but still mixed sector-specific evidence in one global score, which diluted the signal and left weak excess performance.

V5.7c introduced sector-adaptive scoring: rank each approved sleeve internally, then combine sleeves with caps. This restored a financially explainable ETF-like structure.

V5.7d removed dividend yield from alpha scoring after ablation showed it was better treated as a product-support and diagnostic variable.

V5.7e moved to an equal-sleeve structure, but 2026-04 had only 21 names because the bank sleeve had a local data gap.

V5.7f repaired that data gap using same-code, previously visible stale fallback fields in a separate bank panel. The repair is marked and auditable.

## Current Model

- Approved sleeves: `bank`, `utilities_electricity`, `highway_infrastructure`, `port_rail_infrastructure`
- Target names: `28`
- Sector cap: `25%`
- Single-stock cap: `5%`
- Rebalance: quarterly
- Execution simulation: daily open execution, daily close valuation, 100-share lot, 3 bps commission, true cash dividends after 20% tax where available

Core evidence:

- Non-financial sleeves: OCF yield, low volatility, drawdown control, capex burden, low PB diagnostic
- Bank sleeve: low PB, low volatility, drawdown control, NPL ratio, provision coverage, core tier 1 capital adequacy
- Dividend yield: product-support / diagnostic variable, not positive alpha score in V5.7f
- FCF: still disabled until capex-quality and PIT coverage gates pass

## Local Simulation Result

Source: `local_daily_backtests_v57f_etf/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/summary.json`

- Strategy return: `81.42%`
- Annualized return: `14.27%`
- Same-pool benchmark return: `51.01%`
- Excess return: `30.40%`
- Max drawdown: `11.75%`
- Sharpe: `0.932`
- Information ratio: `0.444`
- Strategy volatility: `15.64%`
- Benchmark volatility: `17.63%`

## Rolling Result

Source: `validation_formal_v57f_etf/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/rolling_validation.csv`

- 2021: strategy `1.63%`, excess `2.37%`
- 2022: strategy `7.80%`, excess `10.69%`
- 2023: strategy `11.50%`, excess `6.96%`
- 2024: strategy `28.76%`, excess `11.10%`
- 2025: strategy `11.65%`, excess `-1.26%`
- 2026: strategy `3.31%`, excess `-9.50%`

PM interpretation: absolute returns are positive in all measured years, but 2025 and especially 2026 underperform the same-pool benchmark. This must be tracked in paper trading and platform attribution.

## Formal Evidence

Source: `validation_formal_v57f_etf/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/factor_ic_rankic.csv`

- Composite score mean RankIC: `0.1247`
- OCF yield mean RankIC: `0.0856`
- 120d volatility mean RankIC: `0.1435`
- 120d max drawdown mean RankIC: `0.1137`
- Low PB mean RankIC: `0.1353`
- Dividend yield decimal mean RankIC: `0.0358`, positive IC ratio only `26.32%`

PM interpretation: current evidence supports OCF, low volatility / drawdown control and low PB more than raw dividend yield. Dividend remains in the product narrative as shareholder-return support, not as a primary alpha factor.

## Engineering Audit

Source: `validation_overfit_v57f_etf/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/overfit_audit_summary.json`

- Blockers: `0`
- Needs review: `1`
- Status: `needs_review`

The remaining needs-review item is expected: 2021-05 to 2026-05 is still a platform-confirmation window, not clean out-of-sample acceptance evidence.

## Known Gaps

- No platform replication yet.
- No forward / paper-trading history yet.
- Same-pool equal-weight benchmark is still a local proxy.
- 2026 underperformance requires daily attribution and future monitoring.
- FCF is not yet validated as a cross-sector core factor.
- The 2026-04 bank repair uses stale visible fallback fields and should be replaced by refreshed PIT bank fundamentals from JoinQuant/DataJQ when available.

## Next Gate

Engineering Agent should prepare a platform replication packet for V5.7f, but PM should not call it accepted.

Forward / paper trading should start with the next real rebalance signal. The paper log must record selected stocks, sector sleeve weights, factor values, stale fallback usage and benchmark comparison.

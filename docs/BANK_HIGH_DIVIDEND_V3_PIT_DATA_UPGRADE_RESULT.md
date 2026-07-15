# Bank High Dividend V3 PIT Data Upgrade Result

Date: 2026-07-15

## Purpose

Continue the third test by rebuilding a cleaner point-in-time panel with DataJQ/JQData basic A-share interfaces.

## JQData Capability Probe

The local DataJQ/JQData account successfully accessed:

- `get_all_securities(["stock"])`
- `get_price` raw stock daily prices
- `get_price` pre-adjusted stock daily prices
- `get_price` pre-adjusted 512800 ETF prices
- `get_fundamentals` with `valuation.pb_ratio`, `valuation.market_cap`, and `indicator.roe`

Probe output:

- `数据库/manifests/joinquant_capability_probe.json`

Credentials were loaded temporarily from the local vault into environment variables and were not written to output files.

## New PIT Panel

Runner:

- `src/v5/joinquant_pit_panel_runner.py`

Generated local data:

- `数据库/processed/joinquant_basic_pit_panel/panel.csv`
- `数据库/processed/joinquant_basic_pit_panel/collection_manifest.json`

The generated data is ignored by git and should remain local.

## Panel Coverage

From the collection manifest:

- Rows: 1547
- Dates: 57
- Codes: 42
- Warnings: 0

The panel uses:

- pre-adjusted stock prices for research total return;
- cash dividends as attribution only, to avoid double counting;
- `get_fundamentals(date=trade_date)` for point-in-time valuation and ROE visibility;
- `factor_visible_date = trade_date`;
- `factor_visibility_source = jqdatasdk.get_fundamentals(date=trade_date)`.

## Formal Validation Change

Before PIT upgrade:

```text
notice_date_leakage_audit.status = needs_review
missing_notice_date_rows = 1547
```

After PIT upgrade:

```text
notice_date_leakage_audit.status = pass
missing_notice_date_rows = 0
future_notice_violations = 0
```

This fixes the biggest blocker from the first V3 run for PB, ROE, and dividend-yield visibility.

## Updated Factor Evidence

Using `数据库/processed/joinquant_basic_pit_panel/panel.csv`:

| Factor | Mean IC | Mean RankIC | Positive IC Ratio | Top-Bottom Mean Return |
| --- | ---: | ---: | ---: | ---: |
| dividend_yield | 0.1731 | 0.1735 | 77.55% | 2.55% |
| low_price_to_book | 0.1109 | 0.1168 | 61.22% | 1.82% |
| return_on_equity_ttm | 0.0567 | 0.0412 | 57.14% | 1.01% |
| provision_coverage_ratio | n/a | n/a | n/a | n/a |
| core_tier_1_capital_adequacy_ratio | n/a | n/a | n/a | n/a |

Interpretation:

- High dividend yield remains the strongest single factor under the JQData PIT basic panel.
- Low PB remains positive but weaker than in the migrated V4 panel.
- ROE remains directionally positive but weaker.
- Provision and capital fields are not validated in this panel because JQData basic interfaces do not provide reviewed bank-specialized fields here.

## Updated Formal Validation

| Case | Cumulative Return | Positive Ratio | Mean Selected Count |
| --- | ---: | ---: | ---: |
| equal_weight_all_banks | 35.17 | 61.40% | 27.14 |
| low_pb_top8 | 4.52 | 52.63% | 6.91 |
| composite_current | 60.88 | 66.67% | 7.02 |

Ablation:

| Case | Cumulative Return | Interpretation |
| --- | ---: | --- |
| composite_current | 60.88 | current V3 basic PIT composite |
| drop_dividend_yield | 5.26 | dividend yield is the dominant contributor |
| drop_return_on_equity_ttm | 56.29 | ROE contributes modestly |
| drop_low_price_to_book | 59.64 | low PB contributes little in this PIT basic run |
| drop_provision_coverage_ratio | 60.88 | no effect because field is unavailable |
| drop_core_tier_1_capital_adequacy_ratio | 60.88 | no effect because field is unavailable |

Robustness:

- selection count 6: 66.66
- selection count 8: 60.88
- selection count 10: 58.81
- value weight scale 0.8: 61.72
- value weight scale 1.0: 60.88
- value weight scale 1.2: 61.53

## Decision

Project Manager decision:

`continue_research_with_bank_quality_data_upgrade`

Reason:

The JQData PIT upgrade confirms that high dividend yield deserves further research. The visibility blocker is resolved for PB, ROE, and dividend-yield fields. However, the original research question was not merely "raw high dividend"; it was "sustainable high dividend." Sustainability still requires bank-specific asset-quality and capital fields, which remain unavailable in this basic panel.

## Next Step

Do not tune weights yet.

Next work should be:

1. Build or import reviewed annual-report bank quality fields with `notice_date`.
2. Merge provision coverage and core tier 1 capital into the JQData basic PIT panel.
3. Rerun V3 formal validation.
4. Add interaction tests:
   - high dividend only;
   - high dividend + ROE;
   - high dividend + capital;
   - high dividend + provision;
   - high dividend + low PB;
   - high dividend trap filter.

# Bank High Dividend V3 PIT Data Upgrade Plan

Date: 2026-07-15

## Purpose

Upgrade the V3 high-dividend validation from a migrated V4 panel to a clearer point-in-time local panel using DataJQ/JQData basic A-share interfaces.

## Why This Is Needed

The third V3 test found useful high-dividend evidence, but formal validation returned:

```text
status: needs_review
missing_notice_date_rows: 1547
```

The next step is data lineage repair, not parameter tuning.

## New Runner

Runner:

- `src/v5/joinquant_pit_panel_runner.py`

CLI:

```powershell
$env:PYTHONPATH='src'
python -m v5.cli collect-joinquant-basic-pit-panel `
  data\processed\bank_value_15y\panel.csv `
  --out-dir 数据库\processed\joinquant_basic_pit_panel `
  --database-dir 数据库 `
  --start-date 2014-01-01 `
  --end-date 2026-05-31 `
  --benchmark 512800.XSHG `
  --benchmark-fq pre `
  --dividend-csv 数据库\processed\bank_cash_dividends.csv
```

## Expected Output

- `数据库/processed/joinquant_basic_pit_panel/panel.csv`
- `数据库/processed/joinquant_basic_pit_panel/collection_manifest.json`

These files are local generated data and should not be committed.

## Data Fields

The runner builds:

- `low_price_to_book`: from `get_fundamentals(..., date=trade_date)` / `valuation.pb_ratio`
- `return_on_equity_ttm`: from `get_fundamentals(..., date=trade_date)` / `indicator.roe`
- `dividend_yield`: from dividend events visible by `announce_date` or ex-date fallback
- `factor_visible_date`: set to the rebalance date used for the PIT fundamentals query
- `factor_visibility_source`: `jqdatasdk.get_fundamentals(date=trade_date)`
- pre-adjusted stock returns for research total return
- pre-adjusted 512800 benchmark returns

## Known Limitation

The basic PIT panel intentionally leaves these blank:

- `non_performing_loan_ratio`
- `provision_coverage_ratio`
- `core_tier_1_capital_adequacy_ratio`

Reason:

These are specialized bank indicators and should come from annual-report extraction, reviewed Eastmoney extraction, or another approved replacement source, not direct `bank_indicator`.

## Validation After Collection

After the panel is generated, rerun:

```powershell
$env:PYTHONPATH='src'
python -m v5.cli validate-research examples\bank_high_dividend_sustainability_v3_strategy.json 数据库\processed\joinquant_basic_pit_panel\panel.csv --out validation
python -m v5.cli validate-formal examples\bank_high_dividend_sustainability_v3_strategy.json 数据库\processed\joinquant_basic_pit_panel\panel.csv --out validation_formal --experiment-layer research_pit_validation
```

Expected interpretation:

- This can validate high-dividend, PB, and ROE visibility more cleanly.
- It cannot fully validate provision/capital sustainability until specialized bank fields are connected.

---
name: joinquant-a-share-collector
description: Collect standard Shanghai/Shenzhen A-share daily market, valuation, universe, industry, index, and ordinary financial statement data for Bank Quant V5 using JoinQuant-style workflows. Use for daily prices, daily valuation, bank universe discovery, quarterly balance/income/cash-flow/indicator data, finance statement tables, and resumable collection plans that must not depend on bank_indicator.
---

# V5 JoinQuant A-Share Collector

## Role

Collect standard A-share research data through JoinQuant-compatible workflows.

## Mission

Build reproducible raw data layers for market data and standard financial statements.

## Collectable Data

- Bank universe and stock metadata.
- Daily price data.
- Daily valuation and market-cap data.
- Ordinary quarterly `balance`, `income`, `cash_flow`, and `indicator` tables.
- Dedicated finance tables such as financial-company income statement, cash-flow statement, and parent balance sheet when available.
- Index and industry membership data when explicitly required.

## Do Not Collect

- Do not use JoinQuant `bank_indicator` for new V5 collection work.
- Do not assume minute data is available.
- Do not assume futures, options, Hong Kong, U.S., or convertible bond data is available.
- Do not overwrite raw source files.

## Workflow

1. Route the request through `data-source-router`.
2. Confirm account credentials are provided through environment variables or a secure vault, never hard-coded.
3. Enumerate the universe with an explicit industry code and date window.
4. Download each raw dataset into a per-security raw folder.
5. Save a per-security `summary.json`.
6. Maintain resumable state and failure logs.
7. Record quota, retry, and permission failures separately from true missing data.

## Output

```text
Collection Scope:
Universe Definition:
Date Window:
Raw Tables:
Saved Artifacts:
Missing Data:
Quota or Permission Issues:
Next Skill:
```

## V4 References

- `D:\hh\codex\v4\phase_1_fundamental\download_all_banks_joinquant.py`
- `D:\hh\codex\v4\phase_1_fundamental\raw_downloads\all_banks`
- `D:\hh\codex\v4\phase_1_fundamental\statement_standardization_rules.md`

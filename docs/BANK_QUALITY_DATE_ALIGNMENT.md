# Bank Quality Date Alignment

Date: 2026-07-16

## Purpose

Bank-specialized quality factors must not enter formal research validation unless their visibility date is conservative and auditable.

For each bank-quality snapshot, V5 now aligns three dates:

| Date Type | Meaning | Current Source |
| --- | --- | --- |
| `eastmoney_notice_date` | original report / announcement evidence from Eastmoney, Tushare, or exchange filings | `<database_dir>/processed/eastmoney_bank_quality_manual_csv.csv` plus optional external notice CSV |
| `joinquant_available_date` | the date when JoinQuant could actually expose the same bank-quality item | optional JoinQuant availability CSV |
| `local_first_use_date` | the first date the local V4/V5 panel used the item | `<database_dir>/processed/v4_legacy_bank_quality.csv` |

The formal PIT rule is:

```text
conservative_visible_date = max(eastmoney_notice_date, joinquant_available_date, local_first_use_date)
```

Rows are formal PIT usable only when all three dates are known.

## Flow

```mermaid
flowchart TD
    PM["Project Manager Agent<br/>requires PIT date alignment"] --> E["Engineering Agent<br/>run align-bank-quality-dates"]
    E --> S1["Load Eastmoney notice dates"]
    E --> S2["Load JoinQuant availability dates"]
    E --> S3["Load local first-use dates"]
    S1 --> A["Align by code + source_year"]
    S2 --> A
    S3 --> A
    A --> C["conservative_visible_date = max(all known dates)"]
    C --> G{"All three dates present?"}
    G -- "Yes" --> Q["Quant Validation Agent<br/>formal PIT validation allowed"]
    G -- "No" --> B["PM gate blocks formal acceptance<br/>row remains research/data-lineage work"]
```

## Command

```text
python -m v5.cli align-bank-quality-dates
```

Collect Tushare annual report disclosure dates:

```text
python -m v5.cli collect-tushare-disclosure-dates
```

Build a low-confidence JoinQuant availability proxy from V4 first-visible dates:

```text
python -m v5.cli build-joinquant-availability-proxy
```

Collect real JoinQuant `bank_indicator.pubDate` availability dates through DataJQ/JQData:

```text
python -m v5.cli collect-joinquant-bank-indicator-pubdates
```

Optional JoinQuant availability evidence can be provided with:

```text
python -m v5.cli align-bank-quality-dates --joinquant-availability-csv path/to/joinquant_bank_quality_availability.csv
```

Optional external announcement evidence can be provided with:

```text
python -m v5.cli align-bank-quality-dates --external-notice-csv path/to/tushare_bank_annual_disclosure_dates.csv
```

Expected JoinQuant availability columns:

```text
code,source_year,joinquant_available_date,review_status,confidence,source_note
```

Aliases accepted by the runner:

- `report_year` for `source_year`;
- `jq_available_date`, `available_date`, or `notice_date` for `joinquant_available_date`.

## Current Result

Generated outputs:

```text
<database_dir>/processed/bank_quality_date_alignment/bank_quality_date_alignment.csv
<database_dir>/processed/bank_quality_date_alignment/bank_quality_date_alignment_manifest.json
<database_dir>/processed/bank_quality_date_alignment/bank_quality_date_alignment_report.md
```

Current summary:

| Item | Count |
| --- | ---: |
| aligned rows | 390 |
| formal PIT usable rows | 0 |
| blocked rows | 390 |

Blocked status:

| Status | Count | Meaning |
| --- | ---: | --- |
| `aligned_with_joinquant_proxy_not_formal` | 310 | long-history V4 rows now have Tushare annual-report disclosure dates and V4 first-visible JoinQuant proxy dates, but JoinQuant availability is still not API-verified |
| `blocked_missing_joinquant_available_date_and_local_first_use_date` | 80 | recent Eastmoney rows have original notice dates, but no JoinQuant availability date and no local first-use bridge date |

Tushare collection result:

| Item | Count |
| --- | ---: |
| requested annual disclosure rows | 310 |
| collected annual disclosure rows | 310 |
| warnings | 0 |

DataJQ/JQData finding:

| Probe | Result |
| --- | --- |
| authentication | passed |
| `jqdatasdk.bank_indicator` object | exists |
| `get_fundamentals(..., date=trade_date)` for `bank_indicator` | returns empty frames |
| `get_fundamentals(..., statDate=year)` for `bank_indicator` | returns data and `pubDate` |
| collected JoinQuant `pubDate` rows | 310 / 310 |

Interpretation:

The issue was not missing JoinQuant bank-indicator data. The issue was query mode. Current DataJQ/JQData does not return bank-indicator rows through the usual PIT `date=trade_date` call, but it does return annual rows through `statDate`, including `pubDate`. Therefore `pubDate` should be treated as the JoinQuant availability date for the migrated V4 long-history bank-quality fields.

Example:

| Code | Source Year | Tushare Disclosure Date | V4 First-Visible Date | Conservative Date | Status |
| --- | ---: | --- | --- | --- | --- |
| `000001.XSHE` | 2019 | `2020-02-14` | `2020-02-14` | `2020-11-02` | `aligned_formal_pit_ready` |

## PM Decision

This closes the ambiguity:

- the missing evidence is local evidence-chain completeness, not proof that JoinQuant or Eastmoney is wrong;
- JoinQuant and Eastmoney may have different collection dates;
- formal research should use the most conservative date only after all three date types are present;
- V4 first-visible dates are useful diagnostics, but JoinQuant `pubDate` from `statDate` query is the stronger availability evidence for the migrated long-history bank-quality fields;
- until then, V3 can remain `conditional_research_candidate`, but cannot become `formal_strategy_candidate` because bank-quality PIT lineage is not closed.

## Next Work

1. Engineering Agent builds or imports a JoinQuant bank-quality availability table.
2. Research Agent decides which quality fields are essential enough to justify historical Eastmoney / exchange source-date collection.
3. Quant Validation Agent reruns formal validation using `conservative_visible_date`.
4. Project Manager Agent only reopens candidate acceptance after `formal_pit_usable=true` covers the rows used by the strategy.

# V5.2b Coal Eastmoney Segment Evidence

Date: 2026-07-16

Owner:

```text
Engineering Agent / Quant Validation Agent
```

Status:

```text
segment_evidence_partially_repaired_still_blocked
```

## Purpose

User asked whether the financial reports mention segment business composition. They usually do. The missing part in V5.2b was not the existence of report content, but the structured extraction of segment evidence into PIT data.

This runner prioritizes Eastmoney F10 business composition data and joins report visibility dates from Tushare disclosure dates.

## Runner

New command:

```text
python -m v5.cli coal-data-audit collect-eastmoney-segments
```

Outputs:

```text
数据库/processed/coal_business_tags/eastmoney_coal_segment_raw.csv
数据库/processed/coal_business_tags/coal_segment_business_evidence_eastmoney.csv
数据库/processed/coal_business_tags/eastmoney_coal_segment_evidence_manifest.json
数据库/manifests/coal_segment_evidence_audit_eastmoney/
```

Source:

```text
Eastmoney F10 BusinessAnalysis/PageAjax
```

Access policy:

```text
Normal HTTP request with timeout and no anti-crawler bypass.
```

## Method

For each coal company:

1. request Eastmoney F10 `BusinessAnalysis/PageAjax`;
2. save raw segment rows;
3. prefer product classification rows;
4. fall back to industry classification if product rows are absent;
5. filter `其中` sub-items to avoid double counting;
6. classify segment rows into coal, power, coal chemical or other;
7. join Tushare disclosure `notice_date` as PIT `visible_date`;
8. assign preliminary business tag.

The generated business tag is not final acceptance. It is marked:

```text
eastmoney_segment_needs_spot_check
```

## Result

| Item | Value |
| --- | ---: |
| Requested companies | 37 |
| Raw Eastmoney rows | 6541 |
| Aggregated evidence rows | 642 |
| PIT usable rows | 561 |
| Covered companies | 33 |
| Warning count | 4 |

Missing companies:

```text
000611.XSHE
000780.XSHE
600532.XSHG
600652.XSHG
```

Warnings:

```text
Eastmoney segment fetch returned no zygcfx rows
```

## PM Interpretation

This materially improves V5.2b data quality:

```text
segment evidence coverage improved from 0 / 37 to 33 / 37 companies
```

But it does not clear the formal candidate gate:

```text
business tag evidence remains blocked until all required companies are covered or excluded by a PIT-valid universe rule
```

## Next Options

1. For the four missing companies, use manual report/PDF extraction from annual reports or exchange announcements.
2. If they are delisted, shell-transformed, non-core, or outside current coal universe historically, document PIT exclusion rules.
3. Rebuild the coal PIT panel with Eastmoney evidence only after PM approves the business-tag evidence policy.

V5.2b remains:

```text
workflow_replication_passed_strategy_candidate_failed
```

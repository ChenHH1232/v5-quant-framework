# V5.3c Insurance Data Availability Matrix V1

Date: 2026-07-17

Status:

```text
insurance_specific_data_gate_reviewed_passed_after_field_decision
```

Not status:

```text
platform_replication_approved
paper_trading_ready
accepted_strategy
```

## Purpose

This matrix answers whether V5.3c can be upgraded from a simple low-PB diagnostic case into an insurance-specific V5.3d model.

The answer after source repair and Research Agent field decision is:

```text
data gate passed; V5.3d may enter research hypothesis design
```

Low PB remains a valid research signal, but insurance-specific variables are not sufficiently PIT-complete for a formal model redesign.

## Source Evidence

Existing local evidence:

```text
数据库/processed/insurance_data_probe/insurance_data_probe_manifest.json
数据库/processed/insurance_data_probe/insurance_indicator_field_coverage.csv
数据库/processed/insurance_data_probe/insurance_indicator_year_coverage.csv
数据库/processed/insurance_pit_panel_v53b/panel.csv
数据库/processed/insurance_external_state_v53b/insurance_real_rate_equity_state.csv
```

Key source read:

- Generic valuation fields are usable for baseline research.
- JQData `insurance_indicator` exists and includes some insurance-specific fields with `pubDate` / `statDate`.
- `insurance_indicator` probe coverage is 2015-2023 partial and 2024-2025 absent.
- EV / NBV fields were not found in `insurance_indicator`.
- 10Y government bond yield and equity state are available as review state variables.

## Data Availability Matrix

| Module | Field / Variable | Primary Source Candidate | Observed Coverage | PIT Visible Date Route | V5.3c Status | V5.3d Decision |
| --- | --- | --- | --- | --- | --- | --- |
| Market | open / close / volume | JoinQuant / DataJQ daily price | available for local daily simulation | trade date | usable | usable |
| Market | suspension / limit status | JoinQuant / DataJQ price execution fields | available through local execution simulation | trade date | usable | usable |
| Market | market cap | JoinQuant valuation | generic probe coverage 87.5%-100% on sampled dates | trade date | usable | usable |
| Valuation | PB | JoinQuant valuation | generic probe coverage 87.5%-100%; PIT panel populated | trade date | score input | usable as baseline factor |
| Valuation | PE | JoinQuant valuation | generic probe coverage 87.5%-100%; PIT panel populated | trade date | diagnostic only | usable as diagnostic / baseline |
| Shareholder return | cash dividend | JoinQuant dividend records / exchange announcements | real net cash dividends connected in local daily simulation | announcement / ex-date / pay-date, currently cash on ex-date proxy | usable for engineering simulation | usable after pay-date policy review |
| External state | 10Y government bond yield | ChinaBond / AkShare cached output | available | state date / visible date | review state only | usable as diagnostic state |
| External state | real 10Y yield | 10Y yield minus inflation proxy | available in V53b external panel | visible date | review state only | usable as diagnostic state |
| External state | equity-market state | CSI300 / insurance index / JoinQuant index data | available | trade date | review state only | usable as diagnostic state |
| Insurance operation | earned premium | JQData `insurance_indicator` | 47 / 57 rows, 82.46% field coverage | `pubDate <= trade_date` | present but not scoring | candidate after year coverage repair |
| Insurance operation | earned premium growth | JQData `insurance_indicator` | 20 / 57 rows, 35.09% field coverage | `pubDate <= trade_date` | weak coverage | not ready |
| P&C quality | compensation / claim ratio | JQData `insurance_indicator` | 44 / 57 rows, 77.19% field coverage | `pubDate <= trade_date` | present but not scoring | subgroup-only candidate after repair |
| P&C quality | comprehensive cost ratio | JQData `insurance_indicator` | 27 / 57 rows, 47.37% field coverage | `pubDate <= trade_date` | weak coverage | not ready |
| Investment quality | net investment return | JQData `insurance_indicator` / annual reports | reviewed 2025 core5 coverage 3 / 5 | original announcement date | optional enhancement only | not required for V5.3d core |
| Investment quality | total investment return | JQData `insurance_indicator` / annual reports | reviewed 2025 core5 coverage 5 / 5 | original announcement date | required investment-quality field | V5.3d core field |
| Solvency | solvency adequacy ratio | JQData `insurance_indicator` / insurer solvency report | 51 / 57 rows, 89.47% field coverage, but 2024-2025 absent in probe | `pubDate <= trade_date` | present but not scoring | required repair before V5.3d |
| Solvency | core solvency ratio | insurer solvency report / annual report / vendor | not found in current panel | report publication date | missing | manual/vendor extraction required |
| Solvency | comprehensive solvency ratio | insurer solvency report / annual report / vendor | not found as separate audited field in current panel | report publication date | missing | manual/vendor extraction required |
| Life franchise | embedded value | annual report / interim report / company disclosure / vendor | not found in JQData probe | report publication date | missing | required for insurance-specific value model |
| Life franchise | new business value | annual report / interim report / company disclosure / vendor | not found in JQData probe | report publication date | missing | required for insurance-specific value model |
| Liability pressure | surrender / persistency / reserve pressure | annual report / solvency report / insurer disclosure | not present in current panel | report publication date | missing | optional but important for failure explanation |
| Business type | life / P&C / group tag | PM-reviewed universe + company disclosure | available as current research classification | conservative visible date needed | usable with caution | PIT audit still required |

## Year Coverage Gate

`insurance_indicator` year coverage from the local probe:

| Source year | Coverage |
| ---: | ---: |
| 2015 | 75.00% |
| 2016 | 75.00% |
| 2017 | 75.00% |
| 2018 | 87.50% |
| 2019 | 87.50% |
| 2020 | 87.50% |
| 2021 | 75.00% |
| 2022 | 75.00% |
| 2023 | 75.00% |
| 2024 | 0.00% |
| 2025 | 0.00% |

PM read:

```text
JQData insurance_indicator is useful, but recent-year coverage is not good enough for a formal V5.3d model without repair.
```

## Data Gate Decision

```text
passed_for_v53d_research_hypothesis_design
```

Research Agent field decision:

```text
docs/governance/v53d_insurance_investment_quality_field_decision_v1.md
```

`net_investment_yield` is not a required V5.3d core field. It remains an optional enhancement / robustness field because only three of five core insurers disclose a reviewed annual field. `total_investment_yield` becomes the required investment-quality field because it has five-code reviewed PIT coverage.

## Required Repairs Before V5.3d

1. Build V5.3d hypotheses using low PB, EV / NBV, solvency and total investment yield.
2. Keep `net_investment_yield` as an optional enhancement only where directly disclosed.
3. Separate life, P&C and insurance group logic before using combined ratios or NBV.
4. Keep `pubDate`, `report_period`, `source_url`, `source_type`, and `review_status` for every manually imported field.
5. Re-run failure-year attribution after V5.3d research validation, especially for 2026.

Additional PIT repair fields are mandatory:

```text
pit_status
missing_reason
original_announcement_checked
```

If Eastmoney/F10 or any vendor database contains a historical value but the original announcement date has not been checked, the row must remain:

```text
needs_original_announcement_check
```

Preferred source priority for announcement-date repair:

1. original annual report / interim report PDF;
2. solvency report PDF;
3. exchange or company announcement page;
4. Eastmoney/F10 announcement date if it links to the original disclosure;
5. Tushare announcement link as source discovery;
6. research report as cross-check only, not PIT evidence.

Delayed disclosure, non-disclosure, source gaps and poor disclosure quality must be recorded as potential risk information rather than silently imputed.

## Allowed Work

- Data repair.
- Research report and annual-report source review.
- Manual import template creation.
- Data coverage audit runner.
- V5.3d hypothesis drafting only after source coverage is known.

## Blocked Work

- No JoinQuant strategy code.
- No platform replication.
- No selection-count tuning on V5.3c.
- No defensive overlay from 2021-2026 results.

## Next Gate

```text
v53d_research_hypothesis_design
```

First source audit:

```text
docs/governance/v53c_insurance_special_fields_source_audit_v1.md
```

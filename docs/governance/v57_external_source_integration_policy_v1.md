# V5.7 External Source Integration Policy V1

Date: 2026-07-18

Owner:

```text
Project Manager Agent, Research Agent, Quant Validation Agent, Engineering Agent
```

Status:

```text
active_governance_policy
applies_to_v57_and_later_sector_coverage
not_strategy_evidence_by_itself
```

## Purpose

V5.7 is expanding from single-sector experiments into a future ETF-like basket:

```text
dividend + low volatility + operating cash-flow strength,
with free-cash-flow only as a sector-approved enhancement.
```

This policy defines how external sources are used, so Research Agent, Quant Validation Agent and Engineering Agent do not mix:

```text
industry knowledge
PIT factor data
execution/platform data
manual reviewed evidence
```

## Source Roles

| Source | Primary Role | May Be Used For | Must Not Be Used For |
| --- | --- | --- | --- |
| FxBaogao / research reports | Research knowledge and source discovery | Industry business model, cash-flow logic, value traps, factor hypothesis design, field discovery | Direct PIT factor values, acceptance evidence, backtest tuning |
| JoinQuant / DataJQ | PIT market and financial data | Daily open/close, fundamentals, dividends, industry classification, tradable universe, benchmark data | Untested theory or business-model claims |
| Tushare / TCER-style sources | Disclosure-date cross-check and supplemental structured data | Announcement dates, financial statement cross-check, official-source triangulation | Replacing original visibility audit when dates are missing |
| Eastmoney / F10 | First-layer structured business evidence | Segment/business-composition clues, company field discovery, manual review queue | Final PIT business tag without original report or disclosure-date review |
| Annual reports / interim reports / solvency reports | Original reviewed evidence | Segment data, insurance EV/NBV, operating statistics, special industry fields, visible-date proof | Fast bulk extraction without source row and announcement date |
| Official statistics and exchanges | External state and policy evidence | Commodity state, production/inventory, traffic/state data, policy changes, index/benchmark definitions | Unversioned today-only state assumptions |

## PIT Evidence Rules

Every row that enters formal validation must carry enough visibility evidence:

```text
report_period
original_announcement_date or source_publication_date
visible_date
source_type
source_name
source_url or source_file
review_status
```

For formal factors:

- `visible_date` must be no later than the rebalance date.
- If only `report_period` exists, the row is not PIT usable.
- If a vendor field has no original or cross-checked announcement date, it is `research_only`.
- If Eastmoney supplies a business segment row, it is `first_layer_structured_evidence` until original report review upgrades it.
- If a company does not disclose a key field, Research Agent may classify it as a quality or governance risk, but Quant Agent must test the exclusion rule separately.

## Research Report Rules

Research reports are important, but they are not backtest data.

Research Agent may use FxBaogao reports to:

- learn sector economics;
- identify dividend and cash-flow mechanisms;
- discover industry-specific value traps;
- propose field maps and hypotheses;
- locate original company report or official-statistics sources.

Research Agent must not use reports to:

- accept a strategy because an analyst likes the industry;
- copy a stock list directly into a model;
- treat reported historical returns as factor proof;
- turn an ex-post narrative into a timing rule without PIT validation.

When a report supplies a key claim, the knowledge entry must include:

```text
report_id
title
institution
publication_date
view_url
claim_summary
which hypothesis it supports
whether PDF/original source check is required
```

## Data Source Priority By Stage

| Stage | Preferred Source Order | Gate |
| --- | --- | --- |
| Industry knowledge gate | FxBaogao reports, official industry sources, annual reports | Research Agent writes knowledge packet before modeling |
| Universe PIT gate | JoinQuant/DataJQ, exchange industry data, annual report business evidence, Eastmoney first-pass | PM blocks today-universe backfill |
| Financial factor gate | JoinQuant/DataJQ first, Tushare/TCER cross-check, annual report/manual reviewed rows | Quant Agent blocks missing visible dates |
| Special field gate | Annual reports, solvency reports, industry operating disclosures, reviewed vendor rows | Research Agent must provide original visibility evidence |
| External state gate | Official statistics, exchange data, verified industry source, manual template | Cyclical sectors blocked without state data |
| Engineering replication | JoinQuant real open/close, dividends, stock actions, benchmark prices | Engineering Agent does not alter research conclusion |

## PM Blocking Conditions

Project Manager Agent must block formal validation or promotion when:

- research reports are the only evidence for a factor value;
- PIT visible dates are missing for formal factors;
- a sector needs external state data but only has price returns;
- a business-purity tag is based on current company structure only;
- a small-sample sector is evaluated as if it had broad IC breadth;
- the 2021-2026 platform-confirmation window is used as acceptance evidence;
- a factor is promoted because of historical return alone.

## Current V5.7 Decision

FxBaogao is approved as a Research Agent knowledge source for:

```text
gas_water_operators
telecom_operators
transport_infrastructure
cross_industry_fcf_low_vol_framework
```

JoinQuant/DataJQ remains the preferred source for:

```text
daily real open/close
cash dividends
PIT financial statement fields
tradable universe
benchmarks
```

Tushare / TCER-style sources are approved for:

```text
announcement-date cross-check
supplemental disclosure data
source triangulation
```

Final rule:

```text
Reports create hypotheses. PIT data tests hypotheses. Engineering replicates frozen hypotheses.
```

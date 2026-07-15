# Governance Record: bank_high_dividend_sustainability_v3_formal_candidate_v1

Date: 2026-07-16

Experiment layer:

`research_pit_validation`

Previous status:

`conditional_research_candidate`

Updated status:

`formal_strategy_candidate`

Not status:

`accepted_strategy`

## Decision

Bank High Dividend Sustainability V3 is promoted to formal strategy candidate.

It is not accepted as a production or paper-trading strategy yet.

## Evidence

- V4 long-history bank-quality bridge has 310 rows with aligned Tushare disclosure date, JoinQuant `bank_indicator.pubDate`, and local first-use date.
- `bank_indicator` was not missing in DataJQ. The previous problem was query mode: `date=trade_date` returns empty, while `statDate=year` returns data and `pubDate`.
- Formal notice-date leakage audit passed:
  - checked rows: 1547
  - missing notice-date rows: 0
  - future notice violations: 0
- Dividend yield is the dominant signal:
  - Mean IC: 0.1731
  - Mean RankIC: 0.1735
  - Positive IC ratio: 77.55%
- Low PB is the strongest support signal:
  - Mean IC: 0.1109
  - Mean RankIC: 0.1168
- Provision coverage is directionally positive but modest.
- Core tier 1 capital adequacy is not alpha evidence; use it as quality / risk context.
- Current composite beats equal-bank and low-PB baselines in formal validation.
- Weak years 2018 and 2021 are weak in absolute path stability but still outperform all-bank and low-PB comparators on mean return.

## PM Constraint

V3's accepted research story is:

```text
high visible dividend yield + valuation support, filtered/supported by bank quality evidence
```

V3's rejected research story is:

```text
bank quality factors alone are strong alpha
```

## Required Next Gate

Engineering Agent:

- run local daily simulation for the formal candidate;
- export a frozen JoinQuant version if needed;
- run local-vs-JoinQuant attribution;
- keep 2021-2026 as platform replication only.

Quant Validation Agent:

- keep monitoring quality-factor contribution;
- do not allow quality factors to be accepted as standalone alpha without stronger incremental evidence.

Project Manager Agent:

- block near-sector testing until V3 formal candidate engineering replication is complete.


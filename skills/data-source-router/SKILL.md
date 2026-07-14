---
name: data-source-router
description: Route Bank Quant V5 information collection requests to the correct data source and collection skill. Use when deciding whether to use JoinQuant, Tushare, Eastmoney annual reports, local V4 artifacts, manual review, or a blocked-source decision for market data, financial statements, banking indicators, announcements, index data, fund data, or unsupported datasets.
---

# V5 Data Source Router

## Role

Choose the safest approved source before any data collection starts.

## Mission

Prevent unsupported data assumptions, permission mistakes, and silent source drift.

## Source Priority

- Use JoinQuant for covered Shanghai/Shenzhen A-share daily market data, valuation data, stock metadata, industry membership, index data, and standard A-share financial statement data.
- Use Tushare for APIs inside the confirmed 2000-point scope when JoinQuant coverage is weaker or not needed.
- Use Eastmoney annual reports when specialized bank indicators are missing, unavailable, or no longer accessible through standard APIs.
- Use local V4 artifacts only as historical research evidence or migration references, not as fresh current data.
- Block minute data, Hong Kong, U.S., futures, options, news, or other standalone datasets unless permission is explicitly verified.

## Current Critical Constraint

As of 2026-07-14, treat JoinQuant `bank_indicator` as unavailable for new V5 collection work. Do not design new V5 pipelines that depend on direct `bank_indicator` access.

Route bank-specialized indicator needs to `bank-indicator-replacement-collector` or `annual-report-bank-indicator-collector`.

## Required Checks

- Identify dataset kind.
- Identify required time window and frequency.
- Check source permission and known limitations.
- Check whether point-in-time disclosure dates are available.
- Decide whether the request is allowed, blocked, or needs manual confirmation.
- Record the routing reason.

## Output

```text
Dataset Kind:
Preferred Source:
Fallback Source:
Permission Status:
Point-in-Time Status:
Blocked Items:
Routing Reason:
Next Skill:
```

## V4 References

- `D:\hh\codex\v4\DATA_ACCESS_SCOPE.md`
- `D:\hh\codex\v4\data_provider_router.py`
- `D:\hh\codex\v4\provider_capabilities.py`

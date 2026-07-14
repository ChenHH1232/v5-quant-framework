---
name: tushare-data-collector
description: Collect Bank Quant V5 data from Tushare within the confirmed 2000-point permission scope. Use for allowed A-share daily, daily_basic, financial statement, fina_indicator, disclosure_date, fund, moneyflow, margin, dividend, and other supported Tushare APIs when JoinQuant is not the preferred source or a cross-source check is needed.
---

# V5 Tushare Data Collector

## Role

Collect approved Tushare data without exceeding the confirmed permission scope.

## Mission

Use Tushare as a controlled source for standard market, financial, disclosure, and cross-check data.

## Allowed Scope

Use only APIs confirmed inside the 2000-point scope, including:

- `daily`, `weekly`, `monthly`, `pro_bar`
- `daily_basic`
- `income`, `balancesheet`, `cashflow`
- `fina_indicator`, `fina_audit`, `fina_mainbz`
- `disclosure_date`
- `dividend`, `forecast`, `express`
- supported fund and trading-statistics APIs inside the confirmed scope

## Blocked By Default

- APIs requiring more than 2000 points.
- Minute data.
- Standalone news, announcement, policy, or research-report products.
- Hong Kong, U.S., or other separately licensed market products.

## Workflow

1. Route the request through `data-source-router`.
2. Verify the API is in the allowed list before writing collection code.
3. Require token access through environment variables or a secure vault.
4. Save raw responses separately from cleaned outputs.
5. Preserve disclosure dates for point-in-time research.
6. Record the Tushare API name, parameters, request date, and permission assumption.

## Output

```text
API:
Permission Status:
Request Parameters:
Raw Artifact:
Disclosure-Date Availability:
Missing Data:
Limitations:
Next Skill:
```

## V4 References

- `D:\hh\codex\v4\DATA_ACCESS_SCOPE.md`
- `D:\hh\codex\v4\provider_capabilities.py`

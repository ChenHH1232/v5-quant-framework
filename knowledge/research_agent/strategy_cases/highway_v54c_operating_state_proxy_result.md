# Highway V5.4c Operating-State Proxy Result

Date: 2026-07-18

## Result

V5.4c tested whether PIT financial operating-state proxies can improve the toll-road high-dividend signal.

Conclusion:

```text
Not enough for a formal strategy candidate.
```

## What Improved

The operating-state composite reduced the 2026 weakness compared with some earlier V5.4 variants:

- 2026 composite return: -7.13%;
- 2026 selected portfolio outperformed the all-universe average and low-PB benchmark on a relative basis.

This suggests operating-state information may help explain stress periods.

## What Failed

The new operating proxy fields did not work as alpha factors:

- revenue_growth_yoy Mean IC: -0.0348;
- cash_collection_quality Mean IC: -0.0410;
- ocf_to_revenue Mean IC: -0.0807;
- operating-state composite return: 74.00%;
- high-dividend-only baseline return: 78.84%.

## Research Interpretation

The current JQData financial proxies are too broad. For highway operators, real domain knowledge should focus on:

- actual traffic volume;
- toll revenue;
- remaining concession years;
- tariff policy;
- road asset acquisition / expansion cycle;
- non-highway business contamination.

## PM Instruction

Do not send to Engineering Agent.

Research Agent should either repair highway-specific operating data or let Project Manager archive V5.4 as:

```text
workflow_replication_passed_strategy_candidate_failed
```

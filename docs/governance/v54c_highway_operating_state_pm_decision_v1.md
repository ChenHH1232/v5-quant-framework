# V5.4c Highway Operating-State Proxy PM Decision V1

Date: 2026-07-18

Status:

```text
research_pit_validation_completed_not_engineering_handoff
```

Strategy ID:

```text
highway_dividend_operating_state_v54c
```

## Purpose

V5.4b showed that high dividend is the strongest toll-road signal, while FCF and leverage fields were only weak diagnostics.

V5.4c therefore added PIT operating-state proxy fields from JQData:

- revenue_growth_yoy;
- total_revenue_growth_yoy;
- ocf_to_revenue;
- cash_collection_quality.

Important limitation:

```text
These are PIT financial-statement proxies. They are not direct toll-road traffic volume, toll revenue, concession maturity or toll policy data.
```

## Data Gate

Panel:

```text
数据库/processed/highway_pit_panel_v54c/panel.csv
```

Coverage:

| Item | Value |
| --- | ---: |
| Rows | 344 |
| Rebalance dates | 18 |
| Codes | 20 |
| revenue_growth_yoy coverage | 100% |
| cash_collection_quality coverage | 100% |
| ocf_to_revenue coverage | 100% |

PIT leakage audit:

```text
pass
```

## Quant Result

Single-factor evidence:

| Factor | Mean IC | Mean RankIC | Positive IC Ratio | PM Read |
| --- | ---: | ---: | ---: | --- |
| dividend_yield | 0.2225 | 0.2298 | 72.22% | strongest |
| revenue_growth_yoy | -0.0348 | -0.0512 | 44.44% | weak / negative |
| cash_collection_quality | -0.0410 | -0.0897 | 50.00% | weak / negative |
| ocf_to_revenue | -0.0807 | -0.0756 | 27.78% | negative |
| capex_burden | 0.0210 | -0.0429 | 44.44% | unstable |
| asset_liability_ratio | 0.0216 | 0.0214 | 50.00% | weak |

Baseline tests:

| Case | Cumulative Return | Positive Ratio | PM Read |
| --- | ---: | ---: | --- |
| equal_weight_highway | 42.56% | 72.22% | sector beta exists |
| high_dividend_highway_top8 | 78.84% | 66.67% | best baseline |
| revenue_growth_top8 | 28.35% | 66.67% | weak |
| cash_collection_top8 | 26.00% | 61.11% | weak |
| high_dividend_after_revenue_growth_top70pct | 59.45% | 66.67% | weaker than dividend |
| high_dividend_after_cash_collection_top70pct | 55.09% | 55.56% | weaker |
| operating_state_composite_current | 74.00% | 66.67% | close, but below dividend |

Rolling result:

| Year | Composite Return | Read |
| --- | ---: | --- |
| 2024 | 38.10% | strong |
| 2025 | -2.54% | weak |
| 2026 | -7.13% | still negative, but relatively better than prior simple variants |

## PM Decision

V5.4c is not promoted to Engineering Agent.

Reasons:

- operating-state composite still underperforms high-dividend-only baseline;
- revenue growth and cash-collection fields have negative IC / RankIC;
- 2026 is still an absolute loss year;
- current operating-state fields are proxies, not direct highway operating data;
- common-sample interaction rows with fewer factors are affected by the known min_factor_count runner limitation and should not be used for acceptance.

Current status:

```text
workflow_replication_passed
operating_state_proxy_validation_completed
high_dividend_signal_promising
operating_state_proxy_rejected_as_alpha
not_engineering_handoff
```

## Research Conclusion

Highway remains useful for the long-term dividend / cash-flow basket path, but not as an independent formal candidate yet.

The next V5.4 step should not be weight tuning. It should be source repair:

- direct toll-road traffic volume;
- toll revenue trend;
- remaining concession years;
- toll policy / tariff changes;
- non-highway revenue contamination;
- asset expansion or road acquisition events.

## Stop Rule

No JoinQuant strategy code should be written for V5.4c.

The next gate is:

```text
highway_operating_data_repair_or_archive_as_workflow_replication_passed_strategy_candidate_failed
```

# V5.4b Highway High Dividend With Cash-Flow Diagnostics Decision V1

Date: 2026-07-18

Status:

```text
research_pit_validation_completed_not_engineering_handoff
```

Strategy ID:

```text
highway_high_dividend_cashflow_diagnostics_v54b
```

## Research Question

After V5.4 Test-1 rejected the cash-flow-dividend composite, V5.4b tested a cleaner hypothesis:

```text
Use dividend yield as the main toll-road signal, and treat FCF support, capex burden and leverage as diagnostics or filters.
```

This follows the V5.1 / V5.2 / V5.3 lessons:

- do not promote a strategy only because the return is attractive;
- do not force weak accounting factors into a composite;
- return failed hypotheses to Research Agent instead of letting Engineering Agent write code;
- keep PIT validation separate from platform replication.

## Data Gate

Input panel:

```text
数据库/processed/highway_pit_panel_v54/panel.csv
```

Data limitation:

```text
JoinQuant HY03160 starts on 2021-12-13, so V5.4b only validates 2022-2026.
```

PIT leakage audit:

```text
pass
```

## Quant Result

Single-factor result:

| Factor | Mean IC | Mean RankIC | Positive IC Ratio | Read |
| --- | ---: | ---: | ---: | --- |
| dividend_yield | 0.2225 | 0.2298 | 72.22% | strongest signal |
| free_cash_flow_yield | -0.0143 | -0.0026 | 50.00% | weak |
| fcf_dividend_support | -0.0229 | -0.0350 | 38.89% | weak / negative |
| capex_burden | 0.0210 | -0.0429 | 44.44% | unstable |
| asset_liability_ratio | 0.0216 | 0.0214 | 50.00% | weak |

Baseline / filter tests:

| Case | Cumulative Return | Positive Ratio | PM Read |
| --- | ---: | ---: | --- |
| equal_weight_highway | 42.56% | 72.22% | sector beta exists |
| high_dividend_highway_top8 | 78.84% | 66.67% | best return evidence |
| high_dividend_after_fcf_yield_top70pct | 61.84% | 72.22% | smoother but weaker |
| high_dividend_after_fcf_support_top70pct | 56.94% | 72.22% | weaker |
| high_dividend_after_capex_burden_low70pct | 65.66% | 77.78% | better hit rate, lower return |
| high_dividend_after_leverage_low70pct | 66.97% | 61.11% | weaker hit rate |

Rolling result for the dividend-only V5.4b mainline:

| Year | Return | Positive Ratio | Read |
| --- | ---: | ---: | --- |
| 2024 | 24.00% | 100.00% | strong |
| 2025 | -0.95% | 50.00% | weak |
| 2026 | -9.65% | 50.00% | unresolved |

## PM Decision

V5.4b is not promoted to Engineering Agent.

Reason:

- high dividend is clearly the strongest signal, but the sample is short;
- FCF support, FCF yield, capex burden and leverage do not yet prove incremental alpha;
- capex filtering improves positive-period ratio, but does not beat pure high dividend;
- 2026 remains unresolved;
- traffic volume, toll revenue trend, concession maturity and toll policy are still missing.

Current status:

```text
workflow_replication_passed
research_pit_validation_completed
high_dividend_signal_promising
cashflow_diagnostics_not_promoted
not_engineering_handoff
returned_to_research_agent
```

## Next Research Tasks

Research Agent should add highway-specific knowledge before another model attempt:

- concession maturity and remaining toll years;
- toll road tariff / toll policy changes;
- traffic volume or toll revenue trend;
- capex cycle and road expansion burden;
- non-highway business contamination;
- whether high dividend is backed by recurring toll cash flow or asset monetization.

## Stop Rule

No JoinQuant strategy code should be written for V5.4b yet.

The next acceptable path is V5.4c only after highway-specific external fields are added or explicitly marked unavailable.

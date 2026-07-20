# V5.8i Oil / Gas Sector-Benchmark Validation-Ready PM Decision

Date: 2026-07-21

## Stage

Experiment layer: `engineering_smoke_test`

Decision: `sector_benchmark_smoke_test_completed_validation_ready_not_platform_replication`

V5.8i repairs the main benchmark mismatch that remained after V5.8h. It does not change the frozen V5.8g model, factors, weights, selection count or rebalance logic.

## What Was Added

Oil / gas sector benchmark:

| Field | Value |
| --- | --- |
| Code | `399439.XSHE` |
| Name | 国证石油天然气行业指数 |
| Source | JoinQuant `get_price` |
| Adjustment | `fq=pre` |
| Window | 2021-05-01 to 2026-05-31 |
| Rows | 1228 |

## Engineering Rerun

Output:

```text
validation_daily_v58h_oil_gas_sector_benchmark/oil_gas_state_conditioned_ocf_v58g/summary.json
```

Result:

| Item | Result |
| --- | ---: |
| Strategy return | 99.79% |
| Annualized return | 15.26% |
| Sector benchmark return | 86.21% |
| Excess return | 13.58% |
| Max drawdown | 21.78% |
| Sharpe | 0.714 |
| Information ratio | 0.071 |
| Rebalance signals | 18 |
| Trades | 197 |
| Dividend rows | 29 |
| Daily rows | 1228 |

Compared with the earlier HS300 benchmark smoke test, the sector benchmark result is more conservative and more relevant for oil / gas.

## Overfit Audit

Output:

```text
overfit_audits_v58h_oil_gas_sector_benchmark/oil_gas_state_conditioned_ocf_v58g/overfit_audit_summary.json
```

Result:

| Item | Result |
| --- | ---: |
| Status | `needs_review` |
| Blockers | 0 |
| Needs review | 1 |
| Pass | 13 |

The remaining needs-review item is expected:

- 2021-05 to 2026-05 is still a research / platform-confirmation window, not clean out-of-sample acceptance evidence.

The parameter perturbation contract is now explicit in the V5.8g spec:

- `selection_count_robustness_6_8_10`
- `weight_scale_parameter_perturbation_0.8_1.0_1.2`
- `rolling_validation`
- `weak_year_failure_analysis`

## PM Interpretation

V5.8i is now ready to open the next validation gate.

Allowed:

- platform-replication preparation
- platform export intake checklist
- local-vs-platform attribution framework
- paper-trading preparation checklist after platform evidence exists

Still blocked:

- writing JoinQuant strategy code without explicit user request
- running actual JoinQuant tests automatically
- paper trading
- accepted strategy
- V5.7f basket inclusion

## Remaining Research Data Gaps

These gaps do not block opening platform-replication preparation, but they block strategy acceptance and basket inclusion:

- inventory / demand state remains missing
- pipeline tariff / policy state remains missing
- business exposure still needs annual-report segment review
- refining spread remains a licensed futures proxy rather than a reviewed operating margin

## PM Decision

Current status:

```text
validation_ready_for_platform_replication_preparation
```

Next owner:

```text
Engineering Agent
```

Next allowed action:

Prepare platform-replication intake and local-vs-platform attribution files for V5.8g/V5.8i. Do not generate JoinQuant code or request a platform run unless the user explicitly asks.

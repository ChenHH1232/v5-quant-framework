# V5a.5e Home Appliances Engineering Handoff PM Decision

Date: 2026-07-22

## Decision

`home_appliances_ocf_quality_v5a5c` has passed the V5a.5e Research / Quant / PM gate and may enter Engineering local daily simulation only.

It is not accepted, not a V57f sleeve, not platform-replication passed, and not approved for JoinQuant testing.

## Flow Result

| Stage | Owner | Result |
| --- | --- | --- |
| Promotion queue | Project Manager Agent | `home_appliances` is rank 2 after gas/water |
| Research state policy | Research Agent / PM | no-state scoring or guard policy accepted for Engineering smoke test |
| Formal validation review | Quant Validation Agent | PIT validation, rolling, IC/RankIC and robustness evidence exist |
| Engineering input gate | Project Manager Agent | PIT panel, real daily prices, cash dividends and benchmark files exist |
| Local daily simulation | Engineering Agent | completed after repairing startup signal coverage |

## State Policy

External macro and sector state variables remain diagnostic only:

- real-estate demand proxy;
- export proxy;
- commodity / raw-material proxy;
- inventory, receivables and working-capital pressure;
- capex burden;
- dividend and low-volatility diagnostics.

They cannot be used as:

- positive scoring factors;
- defensive guards;
- timing rules;
- selection-count or weight tuning inputs.

The frozen Engineering smoke-test scoring remains:

```text
0.7 * operating_cash_flow_yield
+ 0.3 * operating_cash_flow_to_net_profit
```

## Engineering Finding

The first local daily run exposed a platform-contract issue:

```text
2021-07-01 and 2021-10-08 were skipped by the generic global-max 80% coverage filter.
```

Reason:

```text
The maximum later cross-section is 95 names, so the generic 80% threshold requires 76 names.
The true PIT startup universe has 65 names on 2021-07-01 and 67 names on 2021-10-08.
Both dates have enough scored candidates and complete factor fields, so dropping them is an Engineering coverage-policy error.
```

Repair:

```text
The home-appliances daily runner now follows formal-validation rebalance dates and requires enough PIT-visible scored candidates to fill the frozen selection_count.
It no longer uses the global-max 80% filter for this sector.
```

## Local Daily Result

| Check | Result |
| --- | --- |
| Engineering gate | `engineering_local_daily_simulation_passed` |
| Signal coverage | `20 / 20` |
| Missing rebalance signals | `0` |
| First executed order date | `2021-07-01` |
| First position date | `2021-07-01` |
| Rebalance order health | passed |
| Unexpected rebalance issues | `0` |
| Strategy return | `106.37%` |
| Annualized return | `16.03%` |
| Benchmark return | `-3.34%` |
| Max drawdown | `30.18%` |

These performance numbers are Engineering smoke-test context only. They are not acceptance evidence.

## Artifacts

- Engineering gate summary: `home_appliances_engineering_gates_v5a5e/home_appliances_ocf_quality_v5a5c/home_appliances_engineering_gate_summary.json`
- Engineering gate report: `home_appliances_engineering_gates_v5a5e/home_appliances_ocf_quality_v5a5c/home_appliances_engineering_gate_report.md`
- Local daily summary: `local_daily_backtests_home_appliances_v5a5e/home_appliances_ocf_quality_v5a5c/summary.json`
- Rebalance order health: `local_daily_backtests_home_appliances_v5a5e/home_appliances_ocf_quality_v5a5c/rebalance_order_health.csv`
- Rebalance signals: `local_daily_backtests_home_appliances_v5a5e/home_appliances_ocf_quality_v5a5c/rebalance_signals.csv`

## PM Status

Current status:

```text
engineering_local_daily_simulation_passed_observation_candidate
```

Next gate:

```text
pm_review_for_observation_sleeve_or_paper_tracking
```

## Hard Rules

- Do not add home appliances to frozen V57f from this run.
- Do not tune factor weights, selection count, state rules or timing.
- Do not start JoinQuant platform replication without a separate PM gate.
- Do not treat 2021-2026 results as clean out-of-sample acceptance evidence.
- Historical performance alone is never sufficient evidence for accepting a strategy.


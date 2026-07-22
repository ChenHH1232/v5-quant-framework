# Home Appliances Engineering Gate: home_appliances_ocf_quality_v5a5c

- Status: `engineering_handoff_ready_local_daily_only`
- Next gate: `engineering_run_local_daily_simulation_with_order_health`
- State policy: `no_state_scoring_or_guard_policy_accepted_for_engineering_smoke_test`

## Detailed Flow Table

| Stage | Owner | Input | Action | Output | Gate | Status |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | Project Manager Agent | `sleeve_promotion_queue.csv` | Confirm home_appliances is rank-2 repair candidate, not V57f sleeve | `PM scoped task` | `no_core_inclusion` | `completed` |
| 2 | Research Agent | `V5a.5d PM decision + state diagnostics` | Decide whether external state is hard gate or diagnostic only | `no-state policy` | `no_return_tuning` | `completed` |
| 3 | Quant Validation Agent | `home_appliances_ocf_quality_v5a5c` | Review formal validation, PIT leakage, rolling, IC/RankIC, ablation and robustness evidence | `validation evidence contract` | `research_pit_validation` | `completed` |
| 4 | Project Manager Agent | `panel / real prices / dividends / benchmark` | Check engineering input files exist | `engineering data contract` | `files_exist` | `completed` |
| 5 | Project Manager Agent | `policy + validation + data checks` | Open or block Engineering handoff | `engineering queue` | `local_daily_only` | `completed` |
| 6 | Engineering Agent | `engineering queue` | Run local daily simulation with real dividends, trades, cash, holdings and rebalance_order_health | `local daily packet` | `no_tuning` | `pending` |

## Gate Checks

| Check | Status | Detail |
| --- | --- | --- |
| `formal_validation_completed` | `passed` | formal_validation_completed_not_acceptance |
| `notice_date_leakage_audit_passed` | `passed` | checks=1 |
| `rolling_validation_completed` | `passed` | completed_windows=4 |
| `factor_ic_rankic_available` | `passed` | factor_rows=2 |
| `state_diagnostic_completed` | `passed` | state_diagnostic_completed_not_engineering_handoff |
| `no_state_policy_documented` | `passed` | no_state_scoring_or_guard_policy_accepted_for_engineering_smoke_test |
| `panel_exists` | `passed` | rows=1687 latest=2026-04-01 |
| `real_daily_prices_exist` | `passed` | rows=124028 latest=2026-05-29 |
| `real_dividends_exist` | `passed` | rows=440 latest=2026-05-29 |
| `benchmark_prices_exist` | `passed` | rows=1228 latest=2026-05-29 |

## Engineering Queue

| Rank | Sector | Owner | Task | Gate |
| ---: | --- | --- | --- | --- |
| 1 | home_appliances | Engineering Agent | Run local daily simulation only for frozen home_appliances_ocf_quality_v5a5c; include real dividends, trades, cash, holdings and rebalance_order_health. | `engineering_local_daily_simulation_only` |

## PM Rules

- This gate resolves Research/Quant state policy; it does not tune V5a.5c.
- External macro state variables are diagnostic only and cannot be positive scoring factors or guards in this handoff.
- Engineering may run local daily simulation only with frozen OCF yield + OCF-to-net-profit scoring.
- Engineering must output real dividends, trades, cash, holdings and rebalance_order_health.
- No V57f sleeve inclusion, JoinQuant platform claim or accepted-strategy status is allowed here.

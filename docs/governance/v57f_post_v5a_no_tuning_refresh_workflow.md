# V57f Post-V5a No-Tuning Refresh Workflow

Date: 2026-07-21

Owner: Project Manager Agent

## Objective

Return to the frozen V57f dividend low-volatility cash-flow enhanced ETF candidate after the V5a broad-sector traversal. The goal is to refresh evidence for the already approved sleeves without tuning the model, changing weights, or adding new sectors.

This is a workflow refresh and Engineering handoff gate. It is not strategy acceptance and not JoinQuant platform replication.

## Core Rule

V57f remains frozen. The V5a traversal may inform observation and repair queues, but it must not change V57f factors, weights, selection count, sleeve count, sector caps, execution settings, or benchmark policy.

## Sleeve Routing From V5a

| Sleeve / sector | V5a bucket | V57f action | PM decision |
| --- | --- | --- | --- |
| `bank` | `core_or_observation_refresh_no_tuning` | Refresh existing V57f sleeve inputs | Keep in V57f |
| `utilities_electricity` | `core_or_observation_refresh_no_tuning` | Refresh existing V57f sleeve inputs | Keep in V57f |
| `highway_infrastructure` | `core_or_observation_refresh_no_tuning` | Refresh existing V57f sleeve inputs | Keep in V57f |
| `port_rail_infrastructure` | `core_or_observation_refresh_no_tuning` | Refresh existing V57f sleeve inputs | Keep in V57f |
| `gas_water_operators` | `core_or_observation_refresh_no_tuning` | Observation sleeve only | Do not add to V57f |
| `insurance` | `core_or_observation_refresh_no_tuning` | Specialist observation sleeve only | Do not add to V57f |
| `telecom_operators` | `research_repair_only` | Research repair / small-sample observation | Do not add to V57f |
| `oil_gas_pipeline_integrated` | `research_repair_only` | Platform-export / specialist observation | Do not add to V57f |
| `coal`, `cement`, `steel`, `nonferrous`, `chemicals`, `retail`, `auto`, `machinery` | rejected / blocked / repair-only | Archive or repair data gates | Do not add to V57f |

## Optimized Refresh Flow

| Stage | Owner | Input | Action | Output | Gate |
| --- | --- | --- | --- | --- | --- |
| 1. PM freeze check | Project Manager | V57f config + V5a master table | Confirm only the 4 frozen sleeves are active | Frozen-sleeve decision | Block if a new sleeve is silently added |
| 2. Signal reconstruction | Quant / Engineering | Frozen V57f config | Rebuild basket rebalance signals | `basket_rebalance_signals.csv` | Must match quarterly frozen process |
| 3. Local daily simulation | Engineering | Signals + real daily open/close + cash dividends | Run JoinQuant-like daily simulation | Daily returns, trades, holdings, cash, dividends | Must output `rebalance_order_health` |
| 4. Order-health gate | Engineering / PM | `rebalance_order_health.csv` | Check every rebalance signal actually generated orders and holdings | Order-health pass/fail | Block if any signal has no order, no holding, blocked/unfilled orders, or leading no-position dates |
| 5. Formal validation refresh | Quant | PIT panel + local daily returns | Recompute rolling, baseline, IC/RankIC, robustness | Formal validation summary | Not acceptance evidence |
| 6. Ablation refresh | Quant | Frozen config | Rerun drop-factor and policy cases | Ablation summary | Used for fragility diagnosis only |
| 7. Failure attribution | Quant / Engineering | Daily simulation + signals | Attribute weak years, detractors, missed winners, cash drag | Attribution packet | Diagnose; do not tune |
| 8. Overfit audit | Engineering | Spec, panel, daily returns, signals | Run leakage, random-window and robustness audit | Overfit summary | Block if blocker count > 0 |
| 9. PM Gate | Project Manager | Formal + daily + overfit + ablation + paper signal | Decide Engineering handoff readiness | PM gate summary | Pass to Engineering local refresh if blocker count = 0 |
| 10. Paper gate | Project Manager | Current signal + PM gate | Prepare next clean future rebalance window | Forward paper gate | No late-recorded signal can be called clean forward evidence |
| 11. Governance dashboard | Project Manager | PM gate + paper queue + platform intake | Show current state and blocked actions | Dashboard + action route | Platform replication remains blocked without exports |

## Engineering Handoff Contract

Engineering may continue with:

- local daily simulation refresh;
- real cash dividend accounting using tax-adjusted net cash per share;
- cash, holdings, trades, dividends, and same-pool benchmark logs;
- `rebalance_order_health` review;
- local monitoring for the next clean paper signal.

Engineering must not:

- tune weights or factors;
- add `gas_water`, `insurance`, `telecom`, `oil_gas`, or any other observation sleeve into frozen V57f;
- call this platform replication without JoinQuant daily return, transaction, position, and log exports;
- promote V57f to accepted strategy.

## Next Clean Forward Gate

The next clean forward / paper trading window is 2026-10-08. Before that date, the refresh queue must complete updated PIT panels, daily open/close prices, cash dividends, stale fallback audit, and trading calendar confirmation.


# V5.1f PM 30-Minute Workflow Run V1

Date: 2026-07-16

Owner: Project Manager Agent

Workflow source:

```text
docs/V5_AGENT_WORKFLOW_OPTIMIZATION_TABLE.md
```

Task:

```text
Run V5.1f next-step workflow under the 30-minute PM review rule.
```

## PM Gate

Opened gate:

```text
live_joinquant_recompute_smoke_test_preparation
```

Timebox:

```text
30 minutes
```

Stop rule:

- stop if live script fails local syntax/static checks;
- stop if dividend source cannot be identified;
- stop if frozen-signal and live-recompute paths are mixed;
- stop if paper-trading evidence would require retrospective backfill.

## Agent Handoff Checklist

| Field | Result |
|---|---|
| Current status | `ready_for_user_platform_smoke_test` |
| Evidence path | `exports/joinquant/utilities_demand_state_v51f_joinquant_live_recompute.py` |
| Supporting evidence | `docs/governance/v51f_utilities_live_joinquant_recompute_v1.md` |
| Blocking issue | Actual JoinQuant platform backtest runtime still must run the script |
| Next owner | User + Engineering Agent |
| Stop rule | If JoinQuant platform logs `LIVE BLOCKED` because dividend source is unavailable, return to Engineering source repair |
| Timebox | 30 minutes for the next platform attempt before PM review |

## Work Performed

Engineering Agent completed:

- local Python syntax compilation for the live-recompute JoinQuant script;
- cleanup of frozen-signal constants from the live-recompute script;
- local JoinQuant/DataJQ capability probe;
- dividend table field discovery;
- correction of dividend yield reconstruction from total dividend amount to per-10-share cash dividend field;
- source status classification.

## Local Checks

Syntax:

```text
python -m py_compile src/v5/joinquant_capability_probe.py exports/joinquant/utilities_demand_state_v51f_joinquant_live_recompute.py
```

Result:

```text
pass
```

Capability probe:

```text
python -m v5.cli probe-joinquant-capabilities --out-dir joinquant_capability_manifests
```

Result summary:

| Check | Status |
|---|---|
| stock universe | pass |
| raw daily stock price | pass |
| pre-adjusted daily stock price | pass |
| ETF daily price | pass |
| valuation / indicator fundamentals | pass |
| `finance.STK_XR_XD` cash dividend source | pass |

Working dividend fields:

```text
code
implementation_pub_date
a_xr_date
bonus_ratio_rmb
```

Interpretation:

```text
bonus_ratio_rmb is cash dividend per 10 shares.
cash_per_share = bonus_ratio_rmb / 10
```

Rejected field:

```text
bonus_amount_rmb
```

Reason:

```text
It is total dividend amount, not per-share cash dividend.
```

## Paper Trading Status

Paper trading remains open but no signal was generated in this workflow run.

Reason:

```text
The paper-trading log starts from 2026-07-16 and must not backfill 2021-2026 signals.
The next actionable paper-trading entry requires the next valid forward rebalance signal packet.
```

Paper-trading log:

```text
docs/governance/v51f_utilities_forward_paper_trading_log.md
```

## PM Decision

Decision:

```text
continue_same_loop only for one JoinQuant platform smoke test
```

Allowed next action:

```text
Run exports/joinquant/utilities_demand_state_v51f_joinquant_live_recompute.py on JoinQuant as a live-recompute smoke test.
```

Not allowed:

```text
accepted_strategy
live_trading_approved
historical retuning from the platform result
paper-trading backfill
```

Required platform artifacts after the next run:

- JoinQuant log;
- daily result CSV if available;
- transaction CSV if trades occur;
- position CSV if trades occur.

If the next platform attempt does not produce a usable artifact within 30 minutes, PM must request a blocker report using the 30-minute template.

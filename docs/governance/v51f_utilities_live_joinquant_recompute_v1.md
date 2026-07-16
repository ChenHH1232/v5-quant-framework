# V5.1f Utilities Live JoinQuant Recompute Repair V1

Date: 2026-07-16

Owner: Engineering Agent

Status: `live_recompute_script_ready_for_platform_smoke_test`

Not status:

```text
platform_replication_passed
accepted_strategy
paper_trading_passed
```

## Problem

The previous V5.1f JoinQuant platform test used frozen local rebalance signals. It passed platform execution alignment, but it did not prove that JoinQuant can recompute the full V5.1f factor signal live.

Known issue:

```text
valuation.dividend_ratio is not available in the tested JoinQuant runtime
```

This matters because the weak electricity-demand branch requires:

```text
dividend_yield top 10
```

## Repair

Added a separate script:

```text
exports/joinquant/utilities_demand_state_v51f_joinquant_live_recompute.py
```

The original frozen-signal script remains unchanged as the platform-replication baseline:

```text
exports/joinquant/utilities_demand_state_v51f_joinquant_near5y.py
```

The live-recompute script now:

- recomputes the utilities universe on JoinQuant;
- recomputes electricity-demand state bucket from visible state rows;
- recomputes PB and operating cash-flow yield from JoinQuant fundamentals;
- replaces unavailable `valuation.dividend_ratio` with a cash-dividend reconstruction attempt from `finance.STK_XR_XD`;
- tries multiple JoinQuant dividend field-name conventions;
- blocks weak-demand trading if dividend source is unavailable or blank;
- preloads state warm-up history before the backtest start date;
- logs warm-up coverage, factor source status, state bucket, candidate count, selected codes, and score preview.

## Warm-Up Rule

The script separates:

```text
performance window start
data warm-up start
```

Warm-up state history starts from:

```text
2017-01-01
```

This is allowed only because each state row still requires:

```text
visible_date <= factor_date
```

If future data is needed, the script must block rather than trade.

## Remaining Platform Check

The new script has passed local Python syntax compilation only:

```text
python -m py_compile exports/joinquant/utilities_demand_state_v51f_joinquant_live_recompute.py
```

It still requires a JoinQuant platform smoke test to confirm:

- whether `finance.STK_XR_XD` exists in the user's runtime;
- which cash-dividend field set works;
- whether the weak-demand branch can compute enough non-null dividend-yield rows;
- whether live-selected securities match or reasonably differ from frozen local signals.

## PM Interpretation

This repair improves operational readiness but does not upgrade V5.1f to accepted strategy.

If JoinQuant dividend source fails again, Engineering Agent should either:

- add a real local PIT dividend export embedded into the script, or
- downgrade the weak-demand high-dividend branch to blocked until a reliable source exists.

# V5.5e Port / Rail Local Daily Smoke Test Approval V1

Date: 2026-07-18

Owner:

```text
Project Manager Agent
```

Experiment layer:

```text
engineering_smoke_test
```

Status:

```text
local_daily_smoke_test_approved
platform_replication_still_blocked
paper_trading_still_blocked
```

## PM Scope Adjustment

V5.5c remains a formal strategy candidate with research PIT validation passed, but the original operating evidence review is still incomplete.

The PM now allows a narrow local daily smoke test because V5.5c uses:

```text
operating_state_score weight = 0
operating_state_score role = diagnostic only
```

This means the local smoke test can verify execution mechanics without accepting the unreviewed operating evidence as an alpha signal.

## Allowed

Engineering Agent may run a local daily simulation to verify:

| Check | Purpose |
| --- | --- |
| daily open execution | confirm real execution-price file can drive trades |
| daily close valuation | confirm portfolio NAV calculation |
| 100-share lot rounding | confirm A-share order constraint handling |
| commission / slippage | confirm transaction-cost plumbing |
| true cash dividends | confirm 20% tax-adjusted dividend cash treatment |
| benchmark proxy NAV | confirm engineering benchmark comparison |
| holdings / trades / cash logs | confirm audit artifacts are generated |
| rebalance signals | confirm frozen research signals connect to execution |

## Still Blocked

Engineering Agent may not:

```text
write JoinQuant strategy code;
start platform replication;
start paper trading;
mark platform_replication_passed;
mark accepted_strategy;
use operating_state_score as a positive scoring factor.
```

## Evidence Boundary

The local smoke test answers:

```text
Can the frozen V5.5c candidate be mechanically simulated with local daily prices, dividends, cash and benchmark logs?
```

It does not answer:

```text
Are cargo throughput, container throughput, rail freight volume, tariff policy or segment revenue fields fully reviewed?
Can V5.5c be deployed?
Is 516970.XSHG a pure port / rail benchmark?
```

## Required Inputs

| Input | Path | Status |
| --- | --- | --- |
| frozen strategy spec | `examples/port_rail_cashflow_value_operating_diagnostic_v55c_strategy.json` | ready |
| PIT signal panel | `数据库/processed/port_rail_operating_state_v55b/panel_operating_state.csv` | ready |
| real daily open / close | `数据库/processed/port_rail_v55c_joinquant_real_daily_prices.csv` | ready |
| real cash dividends | `数据库/processed/port_rail_v55c_joinquant_cash_dividends.csv` | ready |
| benchmark proxy | `数据库/processed/port_rail_v55c_joinquant_real_benchmark_prices.csv` | partial, engineering proxy only |

## Next Action

Run:

```text
V5.5c local daily engineering smoke test
```

Then PM must classify the result as:

```text
engineering_smoke_test_completed
engineering_smoke_test_failed
needs_data_repair
```

Regardless of the result, platform replication remains blocked until operating evidence review is completed or explicitly waived by a separate PM decision.

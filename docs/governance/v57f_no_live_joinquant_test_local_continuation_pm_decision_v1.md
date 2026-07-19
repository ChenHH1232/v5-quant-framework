# V5.7f No Live JoinQuant Test Local Continuation PM Decision V1

Date: 2026-07-19

Owner:

```text
Project Manager Agent
```

User instruction:

```text
Do not run actual JoinQuant platform testing now; continue.
```

## PM Decision

V5.7f remains the frozen enhanced ETF candidate, but the external JoinQuant platform test is deferred.

Current status:

```text
formal_etf_candidate
platform_test_deferred_by_user
local_paper_preflight_continues
not_platform_replication_passed
not_accepted_strategy
```

## What Changed

This is a workflow-state change only.

No changes were made to:

```text
factor weights
sleeve weights
target count
stock selection logic
rebalance rules
V5.7f frozen JoinQuant script
```

## New Local Tool

Engineering Agent added a platform export intake checker:

```text
python -m v5.cli check-platform-export-intake platform_exports_v57f/expected_exports_manifest.json --out platform_export_intake_checks_v57f --user-deferred
```

Output:

```text
platform_export_intake_checks_v57f/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/platform_export_intake_summary.json
```

Current check result:

| Check | Result |
| --- | ---: |
| Ready exports | 0 |
| Missing exports | 4 |
| Empty exports | 0 |
| User deferred | true |

Missing exports:

```text
platform_exports_v57f/pending/result.csv
platform_exports_v57f/pending/transaction.csv
platform_exports_v57f/pending/position.csv
platform_exports_v57f/pending/log.txt
```

## Allowed Continuation

Allowed:

```text
continue local paper preflight
prepare 2026-10-08 clean signal inputs
refresh PIT panels before the signal date
refresh daily open / close prices
refresh cash dividends
audit bank stale fallback usage
keep platform export intake check available
```

Blocked:

```text
platform_replication_passed
accepted_strategy
live_trading_approved
return tuning from platform or paper result
adding telecom overlay to V5.7f mainline
```

## PM Interpretation

Deferring live JoinQuant testing does not invalidate V5.7f. It simply means V5.7f cannot advance from `platform_replication_prepared` to `platform_replication_passed`.

The correct next work is to keep the model frozen and prepare the next clean forward / paper-trading record. The first clean future gate remains:

```text
2026-10-08
```

## Next Owner

```text
Engineering Agent
```

Next task:

```text
Build or run local preflight checks for 2026-10 PIT inputs when the signal window approaches.
```

## 2026-10 Paper Input Preflight Update

New artifact:

```text
docs/governance/v57f_2026_10_clean_paper_input_preflight_v1.md
```

New checker:

```text
src/v5/basket_paper_input_preflight_runner.py
```

Current result:

```text
paper_input_preflight_checks_v57f/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/paper_input_preflight_summary.json
```

Status:

```text
pending_future_data_window
```

PM interpretation:

```text
The 2026-10-08 target date is still in the future. Missing target-date rows are pending refresh work, not a model failure.
The key review item is bank stale fallback usage in the latest available panel.
```

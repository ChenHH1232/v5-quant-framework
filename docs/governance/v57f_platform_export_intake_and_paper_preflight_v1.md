# V5.7f Platform Export Intake And Paper Preflight V1

Date: 2026-07-19

Owner:

```text
Project Manager Agent
```

Status:

```text
platform_export_intake_ready
paper_preflight_ready
not_platform_replication_passed
not_accepted_strategy
```

## Purpose

This packet closes the operational gap between V5.7f being frozen and the next two gates:

```text
JoinQuant platform replication attribution
clean future paper-trading signal
```

No factor, weight, sleeve, stock-pool or rebalance parameter is changed by this packet.

## Platform Export Intake

Dedicated intake folder:

```text
platform_exports_v57f/pending
```

Manifest:

```text
platform_exports_v57f/expected_exports_manifest.json
```

Required files:

| Required export | Target path |
| --- | --- |
| Daily result | `platform_exports_v57f/pending/result.csv` |
| Transaction detail | `platform_exports_v57f/pending/transaction.csv` |
| Position detail | `platform_exports_v57f/pending/position.csv` |
| Full log | `platform_exports_v57f/pending/log.txt` |

PM rule:

```text
Do not infer platform pass from the JoinQuant summary page.
Daily NAV, transaction and position attribution must all pass.
```

## Attribution Command

After the four exports are placed in the intake folder:

```text
python -m v5.cli platform-replication-packet local_daily_backtests_v57f_etf/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f --out platform_replication_packets_v57f_etf --strategy-id dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f --panel-csv validation_formal_v57f_etf/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/combined_basket_panel_for_validation.csv --joinquant-daily-csv platform_exports_v57f/pending/result.csv --joinquant-transaction-csv platform_exports_v57f/pending/transaction.csv --joinquant-position-csv platform_exports_v57f/pending/position.csv
```

Expected local reference:

```text
local_daily_backtests_v57f_etf/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f
```

## Clean Paper Preflight

Current forward gate:

```text
paper_trading_gates_v57f/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/forward_paper_gate_summary.json
```

Current status:

```text
pending_clean_future_rebalance
```

Next clean rebalance:

```text
2026-10-08
```

Before 2026-10-08, Engineering Agent must refresh:

1. PIT sector panels for bank, utilities/electricity, highway infrastructure and port/rail infrastructure.
2. Unadjusted daily open/close prices through the prior trading day.
3. Cash dividend files with 20% tax-adjusted net cash per share.
4. Bank quality data, preferably without stale fallback.
5. Trading calendar confirmation.

## PM Decision

V5.7f remains the frozen main ETF candidate.

Allowed:

```text
platform export intake
platform attribution after exports arrive
clean paper preflight for 2026-10-08
```

Blocked:

```text
return tuning
adding telecom overlay to the frozen mainline
strategy acceptance
live trading approval
```

## Next Owner

```text
Engineering Agent
```

Task:

```text
Wait for JoinQuant exports or refresh the 2026-10 PIT input pipeline before the next clean paper signal.
```

## 2026-07-19 No Live JoinQuant Test Update

User instruction:

```text
Do not run actual JoinQuant testing now; continue locally.
```

PM update:

```text
platform_test_deferred_by_user
local_paper_preflight_continues
```

New checker:

```text
python -m v5.cli check-platform-export-intake platform_exports_v57f/expected_exports_manifest.json --out platform_export_intake_checks_v57f --user-deferred
```

Current result:

```text
platform_export_intake_checks_v57f/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/platform_export_intake_summary.json
```

The checker confirms:

| Check | Result |
| --- | ---: |
| Ready exports | 0 |
| Missing exports | 4 |
| User deferred | true |

V5.7f remains frozen. Platform replication cannot be marked passed while this gate is deferred.

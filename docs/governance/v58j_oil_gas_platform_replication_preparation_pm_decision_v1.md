# V5.8j Oil / Gas Platform-Replication Preparation PM Decision

Date: 2026-07-21

## Stage

Experiment layer: `platform_replication`

Decision: `platform_replication_preparation_completed_waiting_for_exports`

V5.8j prepares the platform-replication intake for the frozen V5.8g oil / gas model after the V5.8i sector-benchmark repair. It does not generate JoinQuant strategy code, does not run JoinQuant, and does not change the frozen model.

## Frozen Reference

| Item | Value |
| --- | --- |
| Strategy id | `oil_gas_state_conditioned_ocf_v58g` |
| Sector benchmark | `399439.XSHE` |
| Benchmark name | 国证石油天然气行业指数 |
| Local run | `validation_daily_v58h_oil_gas_sector_benchmark/oil_gas_state_conditioned_ocf_v58g` |
| PIT panel | `数据库/processed/oil_gas_state_conditioned_panel_v58g/oil_gas_state_conditioned_ocf_v58g/panel.csv` |
| Cash dividends | `数据库/processed/oil_gas_v58g_joinquant_cash_dividends.csv` |

Local smoke-test reference:

| Item | Result |
| --- | ---: |
| Strategy return | 99.79% |
| Sector benchmark return | 86.21% |
| Excess return | 13.58% |
| Max drawdown | 21.78% |
| Rebalance signals | 18 |
| Latest local signal | 2026-04-01 |

## Artifacts Created

| Artifact | Purpose |
| --- | --- |
| `platform_exports_v58i_oil_gas/expected_exports_manifest.json` | Defines the required JoinQuant exports and the local reference files. |
| `platform_export_intake_checks_v58i_oil_gas/oil_gas_state_conditioned_ocf_v58g/platform_export_intake_summary.json` | Confirms platform testing is deferred and four required exports are missing. |
| `platform_export_intake_checks_v58i_oil_gas/oil_gas_state_conditioned_ocf_v58g/platform_export_intake_report.md` | Human-readable export checklist. |
| `platform_replication_packets_v58i_oil_gas/oil_gas_state_conditioned_ocf_v58g/platform_replication_packet.json` | Prepared local-vs-platform packet in `pending_attribution` state. |
| `platform_replication_packets_v58i_oil_gas/oil_gas_state_conditioned_ocf_v58g/platform_replication_packet.md` | Human-readable packet report. |

## Required Platform Exports

The platform attribution gate requires all four exports:

| Export | Target path | Required for |
| --- | --- | --- |
| Daily result | `platform_exports_v58i_oil_gas/pending/result.csv` | Daily NAV attribution |
| Transaction detail | `platform_exports_v58i_oil_gas/pending/transaction.csv` | Transaction attribution |
| Position detail | `platform_exports_v58i_oil_gas/pending/position.csv` | Position attribution |
| Full log | `platform_exports_v58i_oil_gas/pending/log.txt` | Manual execution diagnostics |

Current intake status:

```text
platform_test_deferred_by_user_waiting_for_exports
```

Current packet status:

```text
pending_attribution
```

## Known Alignment Items

- Local simulation uses daily open execution and close valuation; JoinQuant scheduled `09:40` execution may differ.
- Local first selected rebalance signal is `2022-01-04`; the 2021 empty-position period must be explained during platform attribution.
- Real cash dividends are included locally with 20% tax net cash treatment.
- The sector benchmark uses JoinQuant pre-adjusted `399439.XSHE` prices.

## Blocked Actions

- `platform_replication_passed`
- `accepted_strategy`
- `paper_trading`
- `live_trading_approved`
- oil / gas inclusion in V5.7f or any enhanced ETF basket
- return tuning from future platform results

## PM Decision

V5.8j is a preparation gate only.

Allowed next action:

```text
wait_for_user_supplied_joinquant_exports_then_run_platform_attribution_without_tuning
```

No user decision is required now because the user has already said not to do actual JoinQuant testing. The next real gate opens only if platform exports are provided or the user explicitly asks for JoinQuant code.

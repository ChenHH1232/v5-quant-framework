# V5.5h Port / Rail Operating Evidence Review V1

Date: 2026-07-18

Strategy ID:

```text
port_rail_cashflow_value_operating_diagnostic_v55g_repaired_2021
```

## PM Decision

V5.5h fixes the first-layer Eastmoney segment classifier and confirms that V5.5g has broad structured business-evidence coverage.

Status:

```text
formal_strategy_candidate
2021_pit_universe_repaired
local_daily_smoke_test_completed
eastmoney_segment_classifier_repaired
first_layer_business_evidence_partially_passed
platform_replication_still_blocked
not_accepted_strategy
```

The candidate remains blocked from JoinQuant platform replication until the selected-stock evidence gaps are either manually reviewed from original reports or removed by a frozen business-purity gate and rerun.

## What Was Fixed

The previous V5.5h classifier produced:

```text
pit_usable_rows=0
covered_company_count=0
```

Root cause:

```text
Chinese segment keywords were corrupted when passed through the Windows command line.
```

The repaired runner stores the classifier keywords as Unicode escapes in source code:

```text
src/v5/port_rail_operating_evidence_runner.py
```

CLI entry:

```text
python -m v5.cli classify-port-rail-eastmoney-segments
```

Regression test:

```text
tests/test_port_rail_operating_evidence_runner.py
```

## Evidence Outputs

| Output | Path |
| --- | --- |
| raw Eastmoney segment data | `数据库/processed/port_rail_operating_evidence_v55h/eastmoney_port_rail_segment_raw.csv` |
| Tushare report disclosure dates | `数据库/processed/port_rail_operating_evidence_v55h/port_rail_report_disclosure_dates.csv` |
| repaired segment evidence | `数据库/processed/port_rail_operating_evidence_v55h/port_rail_segment_business_evidence_eastmoney.csv` |
| segment evidence manifest | `数据库/processed/port_rail_operating_evidence_v55h/port_rail_segment_business_evidence_manifest.json` |
| candidate coverage by rebalance date | `数据库/processed/port_rail_operating_evidence_v55h/port_rail_segment_evidence_coverage_by_rebalance.csv` |
| selected-signal coverage by rebalance date | `数据库/processed/port_rail_operating_evidence_v55h/port_rail_segment_evidence_selected_signal_coverage.csv` |
| coverage summary | `数据库/processed/port_rail_operating_evidence_v55h/port_rail_segment_evidence_coverage_summary.json` |

## Repaired Classifier Result

| Item | Value |
| --- | ---: |
| raw Eastmoney rows | 4,226 |
| evidence rows | 476 |
| PIT usable evidence rows | 213 |
| covered companies | 22 / 23 |

Tag counts:

| Tag | Rows |
| --- | ---: |
| core_port_operator | 226 |
| core_rail_operator | 115 |
| mixed_transport_infrastructure_operator | 26 |
| non_core_or_needs_review | 109 |

Usable tag counts:

| Tag | Rows |
| --- | ---: |
| core_port_operator | 141 |
| core_rail_operator | 61 |
| mixed_transport_infrastructure_operator | 11 |

## Coverage Audit

Candidate-pool evidence coverage:

| Date range | Minimum coverage |
| --- | ---: |
| all V5.5g rebalance dates | 72.73% |
| after 2022-07-01 | above 90% |

Selected-stock evidence coverage:

| Date | Selected coverage | Missing selected codes |
| --- | ---: | --- |
| 2021-05-06 | 75.00% | `601326.XSHG`, `600125.XSHG` |
| 2021-07-01 | 75.00% | `601326.XSHG`, `600125.XSHG` |
| 2022-01-04 | 75.00% | `000905.XSHE`, `600125.XSHG` |
| 2022-04-01 | 75.00% | `600125.XSHG`, `000507.XSHE` |

Interpretation:

```text
V5.5g can trade locally, but its early selected portfolio is not fully supported by PIT-visible segment evidence.
```

## Research Notes

The evidence gap is not the same as missing price or order data.

Examples:

| Code | Issue |
| --- | --- |
| `600125.XSHG` | Eastmoney segment table shows large supply-chain-management revenue and only about 20% railway-related revenue in 2020-2021. It should not be automatically treated as a core railway operator without original-report review. |
| `601326.XSHG` | 2021 semiannual report shows near-pure port service exposure, but that disclosure was visible after the 2021-05 and 2021-07 rebalance dates. Earlier annual segment labels are cargo-type labels, not direct port-service labels. |
| `000905.XSHE`, `600279.XSHG` | Trade / logistics revenue dominates in some periods, so they need business-purity review before being allowed through a hard gate. |

## PM Gate

Do not approve:

```text
platform_replication
paper_trading
accepted_strategy
joinquant_code_ready
```

until one of the following is completed:

1. Research Agent manually spot-checks the missing selected-stock years against original annual or interim reports and upgrades them to reviewed PIT evidence.
2. Quant Agent freezes a business-purity gate using only PIT-visible evidence, reruns formal validation, local daily simulation and overfit audit, and PM re-approves.

Recommended next step:

```text
V5.5i selected-stock operating evidence spot check, focused on 600125.XSHG, 601326.XSHG, 000905.XSHE, 000507.XSHE and 600279.XSHG.
```


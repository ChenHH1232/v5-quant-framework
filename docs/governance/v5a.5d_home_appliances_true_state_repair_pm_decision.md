# V5a.5d Home Appliances True State Repair PM Decision

Date: 2026-07-21

## Decision

`home_appliances_ocf_quality_v5a5d` remains a promising research signal candidate, but it is not yet an Engineering handoff.

V5a.5d repaired the main "are these fields absent from statements?" question. The standard PIT finance snapshot already supports inventory, receivables and working-capital pressure, and Tushare area-segment disclosure can supply export exposure with conservative visible dates.

The candidate is still kept at the research / Quant loop because property-demand and raw-material-cost states are still proxy-based. PM should not let this move into local daily Engineering simulation until either those states are reviewed or a documented no-state policy is accepted.

## Evidence

- True financial state panel: `数据库/processed/home_appliances_true_state_v5a5d/panel_with_true_home_appliances_state.csv`
- Export exposure panel: `数据库/processed/home_appliances_export_exposure_v5a5d/panel_with_export_exposure.csv`
- State gate packet: `数据库/processed/home_appliances_state_gate_v5a5d/home_appliances_state_gate_summary.json`
- Formal validation packet: `validation_formal_v5a5d_home_appliances_true_state/home_appliances_ocf_quality_v5a5c/formal_validation_summary.json`
- State diagnostic packet: `validation_state_v5a5d_home_appliances/home_appliances_ocf_quality_v5a5d/state_diagnostic_summary.json`

## Data Gate

| Check | Result |
| --- | --- |
| PIT panel rows | `1687` |
| Rebalance dates | `20` |
| JoinQuant cash dividend events | `440` |
| Inventory / receivables / working-capital coverage | `100%` |
| Export exposure panel coverage | `100%` |
| Tushare export segment evidence rows | `1094` |
| External proxy state rows | `120` |

## Quant Evidence

| Test | Result |
| --- | --- |
| PIT leakage audit | pass |
| Equal-weight home appliances baseline | `49.62%` |
| High OCF top 10 | `86.43%` |
| OCF-to-net-profit top 10 | `105.03%` |
| V5a.5d OCF-quality top 10 | `128.09%` |
| OCF yield mean IC / RankIC | `0.0430` / `0.0197` |
| OCF-to-net-profit mean IC / RankIC | `0.0180` / `0.0222` |
| Rolling 2023 | `25.23%` |
| Rolling 2024 | `35.27%` |
| Rolling 2025 | `10.18%` |
| Rolling 2026 | `-1.83%` |

## State Diagnostic

The new export-exposure diagnostics were added to the state bucket packet.

- `sector_high_export_exposure_ratio` high bucket underperformed the universe on average, so export exposure should not be a positive scoring factor.
- `sector_overseas_revenue_share_median` does not explain the full signal; it is better treated as an ex-ante state diagnostic.
- Inventory, receivables and working-capital pressure are now PIT-available enough for diagnostics, but they are not approved as positive factors.

## PM Gate

Current status:

`research_signal_candidate_true_state_repaired_not_engineering_handoff`

Next gate:

1. Either review real estate demand and raw-material cost states, or approve a documented no-state policy for V5a.5d.
2. Do not tune weights or selection count using 2021-2026 results.
3. Keep home appliances as an observation sleeve for the enhanced dividend / low-volatility / OCF ETF queue.
4. Only after the state policy is resolved may Engineering run local daily simulation with real dividends, trades, cash, holdings and `rebalance_order_health`.


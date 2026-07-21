# V5.9 Gas / Water 2026 Failure Attribution and Ex-Ante State Review

Date: 2026-07-21

Strategy: `gas_water_value_serviceability_v57b`

Layer: `research_pit_validation`

Decision: `not_engineering_handoff`

## PM Conclusion

Gas / water V57b should not move to the Engineering Agent yet.

The 2026 failure is not an order-execution failure. Both 2026 rebalance dates produced real orders and post-rebalance holdings. The unresolved issue is research evidence: the model does not yet have validated, point-in-time external state variables for gas procurement cost pass-through, water tariff / receivables stress, financing pressure, or regulated-utility risk appetite.

The correct next gate is:

`research_agent_build_structured_pit_external_state_panel_then_quant_revalidate`

## Evidence Packet

Output folder:

`failure_attribution_v59_gas_water_2026/gas_water_value_serviceability_v57b/`

Key files:

- `failure_attribution_packet.json`
- `gas_water_2026_period_summary.csv`
- `gas_water_2026_selected_factor_detail.csv`
- `gas_water_2026_selected_stock_path_returns.csv`
- `gas_water_2026_monthly_returns.csv`
- `gas_water_2026_worst_daily_returns.csv`
- `gas_water_2026_ex_ante_state_review.csv`
- `gas_water_2026_rebalance_order_health.csv`

## Formal 2026 Attribution

Formal validation result:

- 2026 selected cumulative return: `-9.60%`
- selected mean quarterly return: `-4.64%`
- all-universe mean quarterly return: `-3.42%`
- low-PB mean quarterly return: `-2.75%`
- interpretation: `underperformed_all_universe`, `underperformed_low_pb`

The selected stocks looked stronger than the universe on the current financial factors:

- lower PB
- higher dividend yield
- higher interest coverage
- lower debt pressure
- lower capex burden

Therefore the failure is not explained by the current value / dividend / serviceability factor set. It likely requires sector state variables that were not present in the formal PIT panel.

## Local Daily Check

2026 local daily simulation result:

- strategy return: `-0.63%`
- same-pool benchmark return: `+1.94%`
- excess return: `-2.57%`

Rebalance health:

- `2026-01-05`: selected 10, trade count 13, post-rebalance holdings 10, status `passed`
- `2026-04-01`: selected 10, trade count 11, post-rebalance holdings 10, status `passed`

This rules out the main engineering failure modes:

- no orders
- first rebalances not building positions
- no post-rebalance holdings
- 100-share lot constraint causing cash-only behavior

## 2026 Window Notes

Local daily path:

- January: strategy `+2.23%`, benchmark `+7.94%`, excess `-5.34%`
- February: strategy `+2.28%`, benchmark `+2.33%`, roughly flat relative
- March: strategy `-1.63%`, benchmark `-2.57%`, relative positive
- April: strategy `-3.80%`, benchmark `+0.34%`, excess `-4.15%`
- May: strategy `+0.43%`, benchmark `-5.60%`, relative positive

The largest relative weakness is January and April. That pattern supports a missing state-variable explanation rather than a simple no-trade or one-stock accident.

## Ex-Ante State Review

Candidate state variables:

| Theme | 2026-01 usable | 2026-04 usable | Status | Policy |
|---|---:|---:|---|---|
| gas procurement cost / pass-through | no | not yet structured | needs PIT series | research hypothesis only |
| water tariff / receivables collection | no | no | post-event research only | cannot score 2026 signals |
| water credit / financing pressure | no | possible only if structured before 2026-04 | needs PIT series | future test only |
| regulated utility risk appetite / bond-yield sensitivity | no current evidence | no current evidence | missing data | collect PIT state first |

Research reports used as hypothesis evidence:

- [5306422 - gas procurement / contract policy](https://www.fxbaogao.com/view?id=5306422), published 2026-03-18
- [5307690 - gas operator profit stability](https://www.fxbaogao.com/view?id=5307690), published 2026-03-19
- [5462617 - water tariff / receivables / debt pressure](https://www.fxbaogao.com/view?id=5462617), published 2026-06-04
- [5271953 - water credit risk / financing outlook](https://www.fxbaogao.com/view?id=5271953), published 2026-02-23

These reports are not approved PIT factor data. They can guide Research Agent hypothesis design only.

## Data Governance Note

`knowledge/research_agent/references/gas_water_v57_external_state_source_register.csv` contains titles with commas but does not quote fields consistently. It should be repaired before becoming machine-read by runners. This is a data-governance issue, not a strategy result.

## PM Decision

Status added:

- `2026_failure_attribution_completed`
- `ex_ante_state_review_completed`
- `not_engineering_handoff`

Blocked because:

- No validated PIT external state panel exists for 2026 gas/water operating state.
- Existing research reports are mostly post-rebalance or unstructured.
- 2026 failure remains unresolved at formal ex-ante state-variable level.

Required before Engineering handoff:

1. Build structured PIT external state panel:
   - gas procurement cost / sales-price pass-through
   - water tariff reform / receivables collection pressure
   - financing pressure / local fiscal payment proxy
   - 10Y CGB yield or regulated-utility risk-appetite proxy
2. Re-run formal validation with state buckets and 2026 failure analysis.
3. Only if the state explanation is ex-ante and stable, re-open Engineering for daily simulation or basket candidate evaluation.


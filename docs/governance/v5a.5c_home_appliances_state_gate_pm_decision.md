# V5a.5c Home Appliances State Gate PM Decision

Date: 2026-07-21  
Layer: research_pit_validation + research_state_diagnostic  
Status: research_signal_candidate_proxy_state_repaired_not_engineering_handoff  
Owner: Project Manager Agent

## Decision

`home_appliances_ocf_quality_v5a5c` is retained as a promising research signal for the enhanced dividend / low-volatility / OCF ETF roadmap.

It is not approved for Engineering handoff yet.

The reason is not the core factor evidence. The core factor evidence improved after removing capex as a positive scoring factor. The remaining blocker is the sector state contract: real appliance inventory, export exposure and property-cycle state are still proxies, not reviewed sector-specific PIT fields.

## What Changed

V5a.5c made three changes after V5a.5b:

1. Removed `capex_burden` from positive scoring.
2. Kept `operating_cash_flow_yield` as the primary factor.
3. Kept `operating_cash_flow_to_net_profit` as the cash-conversion support factor.

The new local tools are:

- `src/v5/home_appliances_state_gate_runner.py`
- `src/v5/home_appliances_state_diagnostic_runner.py`

CLI commands:

- `build-home-appliances-state-gate`
- `collect-home-appliances-external-proxy-state`
- `diagnose-home-appliances-state`

## Data Gate Result

| Check | Status | Detail |
| --- | --- | --- |
| PIT panel | pass | 1687 rows, 20 rebalance dates |
| JoinQuant cash dividends | pass | 440 tax-adjusted cash-dividend events |
| State enrichment | pass | Enriched panel rebuilt with sector / subsector financial states |
| Official proxy external state | needs review | 120 rows, 6 proxy metrics |
| True appliance-specific state | blocker | Inventory, appliance export exposure and property-demand state still need reviewed PIT import |

Official / public proxy metrics collected:

- `real_estate_climate_index`
- `china_exports_yoy`
- `commodity_price_index`
- `producer_goods_total_yoy`
- `mineral_goods_yoy`
- `energy_goods_yoy`

These proxies are useful for diagnostics, but they are not a substitute for company-level or appliance-specific exposure data.

## Formal Validation Result

V5a.5c formal validation used the latest state-enriched panel.

| Test | Result |
| --- | ---: |
| Equal-weight home-appliance pool | `49.62%` |
| High OCF top 10 | `86.43%` |
| OCF-to-net-profit top 10 | `105.03%` |
| Low-volatility diagnostic top 10 | `51.92%` |
| High-dividend diagnostic top 10 | `60.25%` |
| V5a.5c OCF-quality top 10 | `128.09%` |

Rolling validation:

| Window | Cumulative return |
| --- | ---: |
| 2023 | `25.23%` |
| 2024 | `35.27%` |
| 2025 | `10.18%` |
| 2026 | `-1.83%` |

Ablation:

| Case | Cumulative return |
| --- | ---: |
| Composite | `128.09%` |
| Drop OCF yield | `105.03%` |
| Drop OCF-to-net-profit | `86.43%` |

Factor IC / RankIC:

| Factor | Mean IC | Mean RankIC | Positive IC ratio |
| --- | ---: | ---: | ---: |
| `operating_cash_flow_yield` | `0.0430` | `0.0197` | `60.00%` |
| `operating_cash_flow_to_net_profit` | `0.0180` | `0.0222` | `65.00%` |

PM read: both factors have incremental contribution. OCF yield remains the primary economic line; OCF-to-net-profit is supportive but weaker.

## State Diagnostic Result

The proxy-state bucket diagnostic completed, but it remains explanatory, not deployable.

Key reads:

- Weak real-estate climate periods did not destroy the OCF-quality signal in this sample.
- Export proxy buckets did not show a clean failure pattern.
- Commodity / material-cost proxies are mixed.
- Sector internal stress measures are more informative than broad macro proxies: high negative-OCF ratio buckets showed weaker excess return.

PM read: the current proxy state does not reject the model, but it is too coarse to approve Engineering. The next Research step should focus on company / subsector inventory and export exposure, not another return-tuned factor revision.

## Agent Routing

| Agent | Decision |
| --- | --- |
| Research Agent | Continue. Build true appliance state data or write a documented no-state policy. |
| Quant Validation Agent | Do not tune weights. Only rerun after true state data or no-state policy is available. |
| Engineering Agent | Blocked. No local daily simulation yet. |
| PM Agent | Keep as `research_signal_candidate`, not `formal_strategy_candidate`. |

## Next Gate

The next queue item is:

```text
V5a.5d Home Appliances True State Repair
```

Required:

1. Appliance inventory / channel pressure PIT data.
2. Appliance export exposure or export-demand PIT proxy.
3. Property completion / sales state with conservative visible dates.
4. Capex policy memo deciding whether capex is risk, normal reinvestment or expansion signal.
5. If true state data remains unavailable, Research Agent must produce a no-state policy memo explaining why the model can remain research-only or observation-only.

Only after V5a.5d should PM decide whether the candidate can move to Engineering local daily simulation.


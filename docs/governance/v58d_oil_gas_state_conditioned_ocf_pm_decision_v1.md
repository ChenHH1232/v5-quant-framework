# V5.8d Oil / Gas State-Conditioned OCF PM Decision

Date: 2026-07-20

## Stage

Experiment layer: `research_pit_validation`

Strategy id: `oil_gas_state_conditioned_ocf_v58d`

Decision: `validation_opened_and_completed_return_to_research_source_repair`

V5.8d opened formal validation successfully. It is not an Engineering handoff and not a platform replication candidate.

## What Changed From V5.8c

V5.8c showed that raw OCF is cycle-conditioned.

V5.8d converted that diagnostic into a PIT-safe research factor panel:

- state buckets use expanding history strictly before each trade date
- OCF is active only when cycle policy supports OCF interpretation
- low-volatility is the fallback under warmup or strong commodity states
- low PE remains diagnostic only

## Formal Validation Evidence

Formal validation completed on 351 rows and 18 rebalance dates.

Key results:

- PIT leakage audit: passed, 0 future visible-date violations
- Equal-weight oil / gas pool cumulative return: about `39.3%`
- Raw OCF top 8 cumulative return: about `80.4%`
- Raw low-vol top 8 cumulative return: about `47.4%`
- State-conditioned OCF top 8 cumulative return: about `127.0%`
- State-conditioned OCF + defensive low-vol composite cumulative return: about `120.9%`

IC / RankIC:

- `state_conditioned_ocf_score`: mean IC about `0.191`, RankIC about `0.215`
- raw `operating_cash_flow_yield`: mean IC about `0.092`, RankIC about `0.111`
- raw `low_vol_score`: mean IC about `0.055`, RankIC about `0.119`

Rolling windows:

- 2024: positive but weak
- 2025: strong
- 2026: positive but only two periods

## PM Interpretation

V5.8d materially improves the research hypothesis versus V5.8b.

The evidence supports:

- OCF should not be used as a static oil / gas factor.
- OCF is more interpretable when conditioned on cycle state.
- The state-conditioned OCF factor has stronger IC and RankIC than raw OCF.
- The defensive low-vol fallback improves positive-period ratio for the composite.

The evidence does not support:

- immediate Engineering handoff
- local daily simulation
- JoinQuant code
- adding oil / gas to the V5.7f basket
- accepting 2021-2026 return as strategy proof

## Remaining Blockers

- External state metrics are still V5.8a futures proxies.
- Official / reviewed spot price, refining spread, gas/liquid state, pipeline tariff and inventory evidence are not repaired.
- Business exposure is still JoinQuant industry proxy, not reviewed annual-report segment evidence.
- Cash dividend events are not repaired.
- The low-PE diagnostic was inactive in this panel and still needs cyclical earnings review.
- 2026 has only two periods and cannot prove forward stability.

## PM Decision

V5.8d is marked as:

```text
research_pit_validation_completed
state_conditioned_ocf_signal_strengthened
not_engineering_handoff
source_repair_required
```

Next owner: Research Agent.

Next allowed work:

1. Repair official / reviewed oil and gas state sources.
2. Repair business-exposure segment evidence.
3. Repair cash dividend events.
4. Then rerun V5.8d or V5.8e formal validation.

Engineering Agent remains blocked.

# V5.8c Oil / Gas Cycle-State Diagnostic PM Decision

Date: 2026-07-20

## Stage

Experiment layer: `research_pit_validation`

Strategy id: `oil_gas_ocf_state_diagnostic_v58c`

Decision: `return_to_research`

V5.8c is a diagnostic validation, not a formal strategy candidate and not an Engineering handoff.

## What Was Tested

Quant Validation added an oil / gas cycle-state diagnostic runner and tested OCF, low-vol, low-PB, low-PE, dividend yield and FCF yield across expanding state buckets.

The diagnostic was run on four V5.8a proxy state metrics:

- `crude_oil_price_state`
- `refining_spread_proxy_state`
- `gas_liquid_price_state`
- `bitumen_price_state`

Each state metric covered all 18 rebalance dates in the current oil / gas research panel.

## Main Evidence

OCF remains stronger than equal-weight in the all-state diagnostic:

- OCF all-bucket cumulative return: about `80.4%`
- Equal-weight oil / gas pool cumulative return: about `39.3%`
- Low-vol all-bucket cumulative return: about `47.4%`

However, the OCF signal is clearly cycle-conditioned rather than universally stable.

Key pattern:

- Under weak crude-oil and weak bitumen proxy states, OCF is strong and has positive IC / RankIC.
- Under strong crude-oil proxy states, OCF weakens or turns negative.
- Under refining-spread proxy states, OCF works better in mid / strong spread buckets than in weak spread buckets.
- Low-PE often produces strong returns, but PM treats that as a cyclical earnings artifact risk until Research explains it financially.

## PM Interpretation

The result supports the existence of an OCF signal, but does not support a static OCF-only model or the previous static composite model.

The current evidence says:

- OCF is likely useful in oil / gas only when conditioned on cycle state.
- Low-vol is useful as a support or risk variable, but did not dominate OCF.
- Low-PE needs special caution because cyclical earnings can make low PE appear attractive near peak profitability.
- The state data are still proxy-based, so this cannot be promoted to platform replication.

## Blockers

- External state metrics are still futures proxies, not official or reviewed spot price, spread, tariff or inventory evidence.
- Business-exposure tags are still not reviewed annual-report segment evidence.
- Cash dividend events have not been repaired for local daily simulation.
- 2026 failure mode is not sufficiently explained ex ante.
- Low-PE strength may be a cyclical earnings illusion and needs Research review.

## Next Gate

Return to Research Agent.

Research Agent should either:

1. Repair official / reviewed oil, gas, refining-spread, pipeline tariff and inventory state sources before formal validation, or
2. Propose a new state-conditioned OCF hypothesis that explicitly explains when OCF should be selected and when it should be de-emphasized.

Engineering Agent remains blocked.

No JoinQuant code should be written from V5.8c.

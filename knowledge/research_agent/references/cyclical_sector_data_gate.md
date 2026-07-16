# Cyclical Sector Data Gate

Date: 2026-07-16

Status:

```text
research_governance_rule
```

## Rule

For commodity-cycle sectors, Research Agent must not hand off a formal strategy hypothesis unless four PIT-ready data layers are available:

- commodity price state;
- production / inventory / supply-demand state;
- spread / margin state;
- company business-exposure PIT tags.

## Why This Exists

V5.2b Coal produced attractive cash-flow value results, but the strategy remained blocked because raw-coal output / inventory history was incomplete and 2018 could not be explained with enough ex-ante cycle-state evidence.

For cyclical industries, historical factor performance can be dominated by commodity cycle timing. A price-only explanation is too weak because it may describe what happened after the fact without proving that the model could have known the state at the signal date.

## PM Interpretation

If one required layer is missing:

```text
data_probe_allowed
workflow_replication_allowed
formal_strategy_candidate_blocked
platform_replication_blocked
paper_trading_blocked
```

## Applies To

- coal;
- steel;
- non-ferrous metals;
- chemicals;
- energy;
- other sectors where company profit is dominated by commodity-cycle state.


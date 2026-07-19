# Airport Transport Franchise + State Framework V5.8b

Date: 2026-07-19

Owner: Research Agent

Status:

```text
research_hypothesis_redesign
not_strategy_candidate
```

## Why V5.8 Was Rejected

The first airport model treated operating recovery as a linear positive factor:

```text
higher passenger / cargo / aircraft movement YoY = better
```

Quant rejected that assumption:

```text
airport_operating_state_score mean IC = -0.1264
operating_state_top3 cumulative return = -21.10%
```

This does not mean the airport operating data is useless. It means raw YoY recovery is not a clean positive alpha factor.

## Revised Economic View

Airport operators are not pure throughput growers. Their equity value mixes:

- regulated aviation-service traffic;
- commercial rent / concession / duty-free exposure;
- fixed-cost operating leverage;
- travel recovery state;
- policy and contract repricing risk.

In a dividend low-volatility cash-flow basket, the preferred airport operator is not necessarily the airport with the highest current traffic rebound. A more suitable hypothesis is:

```text
Stable visible traffic, reasonable valuation, cash-flow support and limited commercial-exposure shock risk may be better than chasing the strongest YoY rebound.
```

## V5.8b Hypothesis

Test airport operators as a defensive franchise sleeve:

```text
prefer shareholder return + valuation discipline + cash-flow support
penalize unstable operating-state swings
penalize high commercial/rental/concession exposure until contract and policy evidence is reviewed
```

Candidate factors:

| Factor | Role | Direction |
| --- | --- | --- |
| dividend_yield | shareholder return | higher is better |
| low_price_to_book | valuation discipline | lower is better |
| operating_cash_flow_yield | cash support | higher is better |
| capex_burden | capital intensity risk | lower is better |
| airport_operating_state_instability | traffic/recovery instability | lower is better |
| airport_commercial_revenue_share | concession / rental / duty-free exposure risk | lower is better |

## Data Gate

Allowed inputs:

- V5.8 PIT airport panel;
- monthly operating values with visible_date;
- 12-row CNINFO original PDF spot-check passed.

Remaining blocker before strategy-candidate promotion:

```text
Annual-report business-purity spot-check is still needed because airport commercial and non-airport segment evidence currently comes from Eastmoney first-layer data.
```

## Acceptance Rule

V5.8b can only proceed if it improves evidence stability, not merely cumulative return. Required:

- no PIT leakage blocker;
- IC / RankIC not dependent on one factor;
- rolling years not dominated by 2026 failure;
- ablation must show the new state-risk logic contributes evidence;
- still no Engineering handoff until business-purity original-report review is complete.

Historical performance alone is never sufficient evidence for accepting a strategy.

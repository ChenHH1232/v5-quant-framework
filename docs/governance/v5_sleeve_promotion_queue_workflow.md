# V5 Sleeve Promotion Queue Workflow

Date: 2026-07-22

Owner: Project Manager Agent

## Objective

Build a repeatable promotion queue for expansion sleeves in the dividend low-volatility operating-cash-flow enhanced ETF line.

This workflow answers one narrow PM question:

Which single candidate should receive the next Research / Quant / Engineering task, based on minimum completion cost and strongest cash-flow dividend fit?

It does not tune V57f, does not add sleeves to V57f, and does not rank candidates by historical return.

## Candidate Scope

Current first-pass candidates:

- `gas_water_operators`
- `insurance`
- `telecom_operators`
- `oil_gas_pipeline_integrated`
- `home_appliances`
- `consumer_staples_cashflow`
- `food_beverage`

## Flow Table

| Stage | Owner | Input | Action | Output | Gate |
| --- | --- | --- | --- | --- | --- |
| 1. Load sleeve registry | PM Agent | `enhanced_etf_production_lines_v5/current/sleeve_registry.csv` | Read observation, repair and blocked sleeve lanes | Candidate rows | Stop if registry missing |
| 2. Load governance evidence | PM Agent | `docs/governance/status_registry.json` | Collect evidence paths, statuses, blockers and next gates by sector | Evidence corpus | Do not use returns for ranking |
| 3. Build gap checklist | PM Agent | Candidate rows + evidence corpus | Check PIT data, real dividends, low-vol factors, external state, local daily simulation, order health and sample size | `sleeve_promotion_queue.csv` | Missing evidence becomes a gate, not a tuning instruction |
| 4. Score candidates | PM Agent | Gap checklist | Score dividend / low-vol / OCF fit minus completion cost and risk penalty | Ranked queue | Highest return cannot promote a sleeve |
| 5. Select first candidate only | PM Agent | Ranked queue | Route only rank 1 into next agent queue | `promotion_agent_queues/selected_candidate_agent_queue.csv` | Other candidates remain parked |
| 6. Agent handoff | PM Agent | Selected task | Give the next owner a bounded task | Agent queue packet | PM does not modify strategy logic |
| 7. Stop condition | PM Agent | Queue output | Record selected candidate and blocked actions | PM checkpoint | No V57f inclusion without a separate stage gate |

## Gap Checklist

Each candidate must show:

- whether PIT data is missing;
- whether real cash dividend events are missing;
- whether low-volatility factors are missing;
- whether industry-specific state variables are missing;
- whether local daily simulation is missing;
- whether `rebalance_order_health` is missing;
- whether sample size is too small;
- whether platform exports are missing;
- whether specialist data is required.

## Ranking Rule

Promotion score:

```text
promotion_score = cashflow_dividend_fit - completion_cost - risk_penalty
```

The score intentionally ignores historical return.

Fit is higher for sectors that naturally match dividend, low-volatility and operating-cash-flow logic. Completion cost rises when PIT, dividends, low-vol factors, state variables, local daily simulation or order-health evidence is missing. Risk penalty rises when sample size is too small, specialist data is required, external state burden is high, or the sector remains cycle-data dependent.

## Handoff Rules

| Candidate condition | Next owner | Allowed task |
| --- | --- | --- |
| Observation sleeve already has local daily and order health | Engineering Agent | Refresh paper-trading inputs and wait for clean forward signal |
| PIT / state / specialist data missing | Research Agent | Repair source evidence and hypothesis packet |
| Research validation exists but local daily missing | Engineering Agent | Run local daily simulation only |
| Validation evidence needs rerun after repair | Quant Validation Agent | Run baseline, IC/RankIC, rolling, ablation and robustness |
| No clear route | Project Manager Agent | Keep parked until new evidence appears |

## Hard Rules

- Only the first-ranked candidate enters the next agent queue.
- Do not modify frozen V57f.
- Do not add observation sleeves into V57f without a separate PM stage gate.
- Do not tune returns, factor weights, target count, sector caps or execution rules.
- Do not claim platform replication without JoinQuant daily, transaction, position and log attribution.
- Historical performance alone is never sufficient evidence for accepting a strategy.

## Runner

```text
python -m v5.cli build-sleeve-promotion-queue \
  --sleeve-registry enhanced_etf_production_lines_v5/current/sleeve_registry.csv \
  --status-registry docs/governance/status_registry.json \
  --out enhanced_etf_production_lines_v5/current
```

## Outputs

| Artifact | Purpose |
| --- | --- |
| `enhanced_etf_production_lines_v5/current/sleeve_promotion_queue.csv` | Full ranked candidate queue and gap checklist |
| `enhanced_etf_production_lines_v5/current/sleeve_promotion_summary.json` | Machine-readable PM decision packet |
| `enhanced_etf_production_lines_v5/current/sleeve_promotion_report.md` | Human-readable PM report |
| `enhanced_etf_production_lines_v5/current/promotion_agent_queues/selected_candidate_agent_queue.csv` | Only rank-1 candidate handoff queue |


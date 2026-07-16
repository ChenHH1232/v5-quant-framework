# Sector Data Availability Gate Template

Use this template before opening a new sector workflow.

Experiment layer:

```text
data_availability_gate
```

## Sector

```text
sector_name:
sector_boundary:
excluded_business_models:
candidate_strategy_family:
```

## PIT Universe

| Check | Status | Evidence Path | Notes |
| --- | --- | --- | --- |
| Listed companies identified | pending |  |  |
| Business model boundary defined | pending |  |  |
| Historical membership visible date available | pending |  |  |
| Current-business-structure pollution avoided | pending |  |  |
| Delisted / transformed companies handled | pending |  |  |

## Research Knowledge Gate

Research Agent must finish this before Quant Agent runs formal validation.

| Check | Status | Evidence Path | Notes |
| --- | --- | --- | --- |
| Sector value investing framework completed | pending | `knowledge/research_agent/factor_theory/{sector}_value_investing_framework.md` |  |
| Core factor hypotheses completed | pending | `knowledge/research_agent/factor_theory/{sector}_core_factor_hypotheses.md` |  |
| Universe definition completed | pending | `knowledge/research_agent/references/{sector}_universe_definition.md` |  |
| Data field map completed | pending | `knowledge/research_agent/references/{sector}_data_field_map.md` |  |
| Source collection plan completed | pending | `knowledge/research_agent/references/{sector}_source_collection_plan.md` |  |
| Quant validation handoff completed | pending | `knowledge/research_agent/references/{sector}_validation_handoff.md` |  |
| Source citations recorded | pending |  | Official / filings / reports / papers / articles separated by confidence. |
| Financial falsification conditions defined | pending |  | What evidence would reject the hypothesis? |

## Required Economic Data

| Data Type | Required? | PIT Visible Date? | Source Candidate | Status |
| --- | --- | --- | --- | --- |
| Valuation | yes | pending | JoinQuant / DataJQ / Tushare | pending |
| Dividend | yes | pending | JoinQuant / Akshare / exchange announcement | pending |
| Cash flow | case dependent | pending | JoinQuant / DataJQ / statements | pending |
| Debt / interest coverage | case dependent | pending | JoinQuant / DataJQ / statements | pending |
| Sector external state | case dependent | pending | official source preferred | pending |
| Sector benchmark | yes | pending | JoinQuant index / ETF / equal-weight fallback | pending |

## Engineering Data

| Check | Status | Evidence Path | Notes |
| --- | --- | --- | --- |
| Daily open / close available | pending |  |  |
| Benchmark daily series available | pending |  |  |
| Cash dividend events available | pending |  |  |
| Corporate action treatment defined | pending |  |  |
| Local runner can generate daily returns | pending |  |  |

## Legal / Source Access Review

| Check | Status | Notes |
| --- | --- | --- |
| No forced crawling required | pending |  |
| Manual import route exists if source blocks automation | pending |  |
| Paid data permission understood | pending |  |
| Source citation retained | pending |  |

## PM Decision

Allowed statuses:

```text
sector_knowledge_gate_passed
sector_knowledge_gate_needs_more_sources
data_gate_passed
data_gate_needs_manual_research
data_gate_blocked
```

Decision:

```text
pending
```

Next gate if passed:

```text
research_pit_validation
```

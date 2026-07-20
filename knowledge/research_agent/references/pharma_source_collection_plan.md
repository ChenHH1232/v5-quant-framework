# Pharma / Medical Services Source Collection Plan V5.9

Date: 2026-07-21

Owner:

```text
Research Agent
```

Status:

```text
research_knowledge_gate_seed
not_quant_ready
```

## Research Boundary

Pharma and medical services are not a first-choice dividend low-volatility FCF sleeve. The sector has policy, R&D, pipeline and reimbursement risks that can overwhelm generic cash-flow factors.

Initial split required:

```text
mature pharma manufacturers
medical services
testing / CRO / CXO services
medical devices
innovative drug / pipeline-heavy companies
```

Do not mix all subsectors in one factor test.

## Source Priority

1. JoinQuant / DataJQ PIT financial fields, dividends and daily prices.
2. Annual reports for R&D capitalization, product concentration and reimbursement exposure.
3. Policy and procurement announcements for visible-date state variables.
4. Eastmoney/F10 as first-layer business clues.
5. Research reports for industry logic and policy vocabulary only.

## FxBaogao Search Seed

Local search output:

```text
research_reports_v59_expansion/pharma_medical/report_candidates.csv
```

Useful first-pass candidates:

| Report ID | Title | Link | Use |
| --- | --- | --- | --- |
| 5435994 | Testing service 2025 and 2026Q1 summary: margin and cash-flow repair | https://www.fxbaogao.com/view?id=5435994 | Testing-service cash-flow repair vocabulary |
| 5345366 | Pharma industry quick report on hierarchical medical system | https://www.fxbaogao.com/view?id=5345366 | Policy-state context |
| 5405909 | 2026Q1 pharma fund holding analysis | https://www.fxbaogao.com/view?id=5405909 | Market preference context only |

## Required Data Before Quant Validation

```text
PIT subsector classification
visible_date
operating_cash_flow_yield
free_cash_flow_yield
dividend_yield
R&D expense / revenue
capitalized R&D ratio if available
gross_margin_stability
inventory_turnover
receivables_to_revenue
policy_state
procurement_pressure_state
real daily open / close prices
cash dividends
```

## PM Gate

Pharma / medical services remains `needs_manual_research_before_formal` until:

```text
subsector split is PIT-safe
R&D and policy-risk fields are mapped
FCF interpretation is approved per subsector
dividend sustainability is not only historical payout
```

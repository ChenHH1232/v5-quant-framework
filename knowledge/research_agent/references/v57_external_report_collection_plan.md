# V5.7 Research Agent External Report Collection Plan

Date: 2026-07-18

Owner:

```text
Research Agent
```

Status:

```text
active_task_plan
feeds_v57_sector_coverage
```

## Research Boundary

Theme:

```text
Build the industry knowledge layer for a future dividend low-volatility OCF basket, and decide where FCF can be safely upgraded from diagnostic/enhancement to formal sector factor.
```

Current first-pass sectors:

```text
gas_water_operators
telecom_operators
transport_infrastructure
cross_industry_fcf_low_vol_framework
```

Excluded from immediate modeling:

```text
coal
environmental_project_operators
generic insurance FCF basket
```

## MECE Questions And Search Matrix

| Order | Sub-question | Judgment To Validate | Search Keywords | Evidence Needed | Output |
| ---: | --- | --- | --- | --- | --- |
| 1 | Business model | Is the sector a stable operator business rather than project, equipment or trade revenue? | 行业名 运营商 收入结构 分部业务 商业模式 | Reports, annual reports, segment tables | Sector business model card |
| 2 | Cash-flow quality | Does OCF represent durable earning power, or is it distorted by working capital, subsidies or receivables? | 行业名 经营现金流 应收账款 回款 现金流质量 | Reports, cash-flow statements, receivable notes | OCF quality rule |
| 3 | FCF interpretation | Is capex maintenance, growth, policy-mandated, or cycle-driven? | 行业名 自由现金流 资本开支 维护性资本开支 | Reports, capex notes, annual reports | FCF approval or downgrade decision |
| 4 | Dividend sustainability | Is dividend supported by cash generation and balance sheet, not one-off payout? | 行业名 分红 股息率 派息率 现金流覆盖 | Dividend data, reports, annual reports | Dividend sustainability rule |
| 5 | Low-volatility rationale | Why should low volatility be economically meaningful in this sector? | 行业名 红利低波 防御 资产属性 现金流稳定 | Reports, market stress periods, beta data | Low-vol guard explanation |
| 6 | Value-trap risks | What makes a high-dividend stock unsafe? | 行业名 价值陷阱 债务 政策风险 非主业 应收 | Reports, company reports, credit reports | Exclusion / guard hypotheses |
| 7 | PIT data route | Can every field be collected with visible dates? | 行业名 数据 财报 公告日 指标 | JoinQuant/DataJQ, Tushare/TCER, reports | Data availability gate |

## Sector-Specific Instructions

### Gas / Water Operators

Research focus:

- separate real operators from engineering, project, construction and equipment companies;
- identify water-price / gas-price pass-through mechanisms;
- track receivables, government payment and debt expansion as value traps;
- decide whether FCF is usable, or whether OCF plus receivables guard is safer.

Required fields before formal validation:

```text
operator_purity
water_or_gas_revenue_share
ocf_quality
receivables_to_revenue
net_debt_pressure
capex_burden
dividend_yield
dividend_payout_ratio
```

### Telecom Operators

Research focus:

- treat as small-sample observation sleeve, not standalone broad IC sector;
- study capex cycle, depreciation burden, cloud/AI business mix and dividend commitment;
- decide whether basket-level evidence can justify an observation sleeve.

Required fields before formal promotion:

```text
ocf_yield
capex_to_ocf
free_cash_flow_yield
dividend_yield
depreciation_amortization_burden
mobile_arpu_or_service_revenue_trend_if_available
```

### Transport Infrastructure

Research focus:

- preserve V5.4 and V5.5 lessons: operating-purity review matters;
- use reports to improve port / railway / highway value-trap definitions;
- avoid mixing logistics trade and infrastructure operation.

Required fields:

```text
business_purity
toll_or_throughput_or_rail_freight_state
ocf_yield
dividend_yield
capex_burden
debt_pressure
policy_or_concession_risk
```

### Cross-Industry FCF Framework

Research focus:

- compare OCF, FCFF/EV, FCF yield and dividend yield;
- distinguish cash-flow strength from capex-cycle exposure;
- define when FCF is alpha, when it is a guard, and when it is a trap.

Required output:

```text
sector_fcf_capex_quality_gate_v1
```

## Execution Steps

1. Use FxBaogao to collect 5-10 candidate reports per sub-question.
2. Register every useful report in `v57_fxbaogao_source_register.md`.
3. Fetch paragraphs for first screening only.
4. Download and inspect PDF/original source when a claim becomes a formal hypothesis.
5. Produce one knowledge card per sector.
6. Produce a cross-industry FCF/capex-quality gate.
7. Hand only hypothesis specifications to Quant Agent.
8. Quant Agent runs baseline, IC/RankIC, rolling, ablation, robustness and failure-year analysis.
9. Failed validation returns to Research Agent for new hypothesis or archival.

## Research Agent Completion Report Must Include

```text
sector
knowledge_sources
candidate_hypotheses
rejected_hypotheses
PIT data route
missing fields
recommended Quant validation spec
PM gate recommendation
```

## Hard Rules

- Research reports are not accepted as factor data.
- No stock list copied directly from a report can enter a strategy.
- Every sector-specific field must have source and visible-date path before formal validation.
- If a source cannot be accessed without aggressive crawling, mark it as manual or vendor-required.
- Historical performance alone is never sufficient evidence for accepting a strategy.

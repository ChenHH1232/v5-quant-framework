# Environmental / Project Operator Cash-Flow Trap Framework V5.9

Date: 2026-07-21

Owner:

```text
Research Agent
```

Status:

```text
blocked_framework
data_gate_not_passed
not_quant_ready
```

## PM Starting View

Environmental operators look superficially similar to utilities, but the sector can hide project cash-flow traps. V5 must not treat high dividend or low valuation as evidence until receivables and project exposure are audited.

## Economic Logic

Potential fit:

- concession-like waste or sewage operation;
- recurring treatment volume;
- long-term service contract;
- stable operating cash flow;
- dividend backed by cash collection.

Value-trap risks:

- EPC / construction revenue inflates earnings but weakens cash quality;
- PPP projects create long receivable cycles;
- subsidy arrears or local-government payment delay distort OCF;
- capex is lumpy and policy-driven;
- high dividend may be one-off or balance-sheet funded.

## Research Hypotheses

### H1: OCF Is Not Enough Without Receivable Audit

Hypothesis:

```text
High OCF yield is only meaningful when receivables and government payment risk are controlled.
```

Candidate guards:

```text
receivables_to_revenue
receivables_ageing
operating_cash_flow_to_net_income
government_receivable_share
net_debt_to_ocf
```

### H2: FCF Is Usually Diagnostic Before Project Split

Hypothesis:

```text
Raw FCF is unreliable when project capex and concession investment dominate cash flow.
```

### H3: Business Purity Is The First Gate

Hypothesis:

```text
True operators and EPC/project companies must be separated before any factor can be interpreted.
```

Required tags:

```text
operator_revenue_share
EPC_or_construction_revenue_share
equipment_revenue_share
PPP_project_exposure
```

## Factor Role Decision

| Factor | Initial role | Promotion rule |
| --- | --- | --- |
| `operating_cash_flow_yield` | candidate after receivable guard | Blocked until receivable audit |
| `free_cash_flow_yield` | diagnostic only | Blocked until project/capex split |
| `dividend_yield` | support only | Requires cash collection coverage |
| `low_volatility_score` | possible guard | Does not override data gate |
| `receivable_trap_guard` | mandatory filter candidate | Required before modeling |

## Quant Handoff Conditions

Do not hand to Quant Agent until:

1. PIT business-purity panel exists.
2. Receivable and cash-conversion fields are visible-date safe.
3. Project/EPC exposure is excluded or tagged.
4. Dividend cash coverage is confirmed.

Historical performance alone is never sufficient evidence for accepting a strategy.

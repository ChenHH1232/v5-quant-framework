# Oil / Gas Cash-Flow Dividend Framework V5.8a

Date: 2026-07-20

Owner:

```text
Research Agent
```

Status:

```text
research_framework
data_gate_not_passed
not_quant_ready
```

## PM Starting View

Oil / gas may contain high-dividend and strong cash-flow companies, but it is not a clean stable-operator sector like toll roads or electricity.

The sector mixes at least four different economic engines:

| Business Type | Main Driver | Risk For V5 Basket |
| --- | --- | --- |
| Upstream oil / gas | Brent / WTI, production, reserve replacement | commodity cycle dominates returns |
| Integrated oil | upstream price plus refining / chemicals / retail | exposure is mixed and changes over time |
| Pipeline / storage / LNG infrastructure | regulated tariffs, utilization, gas demand | closer to stable cash-flow, but policy data needed |
| Oilfield services | oil-company capex and offshore drilling activity | capex-cycle beta, not dividend low-vol core |

## Research Hypotheses

### H1: OCF Is Safer Than Raw FCF As The First Cash-Flow Lens

Hypothesis:

```text
Operating cash-flow yield is more interpretable than raw FCF yield for oil/gas because capex can represent reserve replacement, offshore development or policy / energy-security investment.
```

Factor implication:

```text
OCF yield can be tested first.
FCF yield must be downgraded to support / diagnostic until capex quality and cycle state pass.
```

### H2: Dividend Yield Needs Cash-Flow And Cycle-State Coverage

Hypothesis:

```text
High dividend is attractive only when payout is covered by recurring cash generation across commodity states.
```

Candidate fields:

```text
dividend_yield
dividend_payout_ratio
cash_dividend_coverage_by_ocf
net_debt_pressure
oil_price_state
gas_price_state
```

### H3: Business Exposure Must Be PIT Tagged

Hypothesis:

```text
The same valuation factor can mean different things for upstream, pipeline and refining companies.
```

Required tags:

```text
upstream_exposure_share
pipeline_or_storage_exposure_share
refining_chemical_exposure_share
retail_or_sales_exposure_share
oilfield_service_exposure_share
```

### H4: External State Is Mandatory

Hypothesis:

```text
Oil/gas cannot enter formal modeling without ex-ante commodity and spread states.
```

Minimum external-state panel:

```text
brent_price_state
wti_price_state
domestic_gas_price_state
refining_spread_state
inventory_or_demand_state
pipeline_tariff_policy_state
```

## Factor Policy

| Factor | Initial Role | Promotion Rule |
| --- | --- | --- |
| `operating_cash_flow_yield` | primary candidate | May enter baseline if PIT cash-flow fields pass |
| `dividend_yield` | support candidate | Must be paired with cash-flow coverage |
| `free_cash_flow_yield` | diagnostic / support only | Needs capex-cycle classification before scoring |
| `low_vol_score` | risk guard | Can be built from daily prices |
| `low_price_to_book` | sector-specific diagnostic | Not basket-wide mainline |
| `net_debt_pressure` | value-trap guard | Required before dividend promotion |
| `oil_price_state` | external state | Required before formal promotion |
| `refining_spread_state` | external state | Required for downstream / integrated names |

## Candidate Universe Boundary

Start with a broad watchlist, then filter by PIT business tags:

```text
core upstream / integrated oil and gas
pipeline / LNG / storage operators
high-dividend large integrated energy companies
```

Exclude or downgrade:

```text
pure oilfield services
pure petrochemical processors without stable dividend policy
trading-heavy companies
companies whose historical business exposure cannot be dated
```

## Quant Handoff Conditions

Only hand to Quant Validation Agent after:

1. PIT universe exists.
2. PIT business-exposure tags exist.
3. Oil / gas / spread state panel exists.
4. Capex-to-OCF and FCF coverage fields are joined.
5. Dividends and real daily prices are available.

Required Quant tests:

```text
baseline
IC / RankIC
rolling validation
ablation
robustness
state bucket validation
mixed-business exclusion
capex-cycle sensitivity
weak-year analysis
```

## PM Decision For V5.8a

Current status:

```text
industry_knowledge_gate_started
blocked_before_quant_by_cycle_state_and_business_exposure_pit
```

Oil / gas should not become the next formal model until its data gate passes.

Historical performance alone is never sufficient evidence for accepting a strategy.

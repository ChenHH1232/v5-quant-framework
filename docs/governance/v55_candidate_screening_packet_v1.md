# V5.5 Candidate Sector Screening Packet V1

Date: 2026-07-18

Owner:

```text
Project Manager Agent
```

Experiment layer:

```text
data_availability_gate
```

Status:

```text
candidate_screening_completed
new_sector_formal_modeling_not_started
```

## Purpose

V5.5 should not start with direct factor modeling.

This packet screens the next similar-sector candidates using the V5.5 sector replication framework:

```text
Industry Knowledge Gate
Data Availability Gate
```

Only a candidate that passes these two gates can move into formal V5.5 research.

## Inputs From Previous Sector Lines

| Sector line | PM lesson reused in this screening |
| --- | --- |
| Bank | PIT visibility, platform replication, and paper-trading separation must remain hard rules. |
| Utilities / electricity | Sector knowledge and external state improved the model. This is the golden template. |
| Coal | Cyclical sectors must pass commodity / output / inventory / spread data gates before modeling. |
| Insurance | Superficially similar valuation factors are not enough when the sector needs specialist metrics. |
| Transportation / highway | Stable cash-flow sectors with reviewed operating evidence are strong replication candidates. |

## Candidate Set

Initial V5.5 candidates:

```text
1. telecom_operators
2. gas_water_operators
3. port_rail_infrastructure
```

Rejected at this pre-screening stage:

```text
oil_gas_high_dividend
```

Reason:

```text
Too cycle-sensitive for the next test. It belongs closer to the coal data-gate family.
```

## Screening Criteria

| Criterion | Meaning |
| --- | --- |
| Business model clarity | Can Research Agent explain how the sector makes money? |
| Cash-flow / dividend fit | Does the sector fit the dividend and free-cash-flow enhancement ETF direction? |
| PIT universe feasibility | Can we avoid using today's business structure to classify historical stocks? |
| Sector-specific data availability | Are operating fields available from filings, JQData / DataJQ, Eastmoney F10, annual reports, or manual import? |
| External-state burden | Does the sector require hard-to-get macro / commodity / traffic / freight state data? |
| Benchmark feasibility | Is there a reasonable sector index / ETF / equal-weight benchmark fallback? |
| Sample-size risk | Is the stock pool large enough for IC / RankIC and rolling validation? |

## Candidate 1: Telecom Operators

Sector boundary:

```text
A-share telecom network operators and telecom service operators.
Exclude equipment makers, software vendors, optical modules, communication devices, and satellite / defense communication themes.
```

Likely core stocks:

```text
600050.XSHG China Unicom
600941.XSHG China Mobile
601728.XSHG China Telecom
```

Industry knowledge pre-screen:

| Area | Preliminary view |
| --- | --- |
| Business model | Subscription and traffic-based communication service revenue, enterprise / cloud / digital services, infrastructure monetization. |
| Profit drivers | Mobile users, ARPU, broadband users, enterprise services, capex cycle, depreciation, network utilization, cost control. |
| Dividend logic | High cash generation and state-owned shareholder return policy may support dividend strategy. |
| Value trap risk | Heavy capex, declining ARPU, regulatory pressure, price competition, slow enterprise-service monetization. |
| External state | Moderate. Interest-rate state and capex / 5G investment cycle matter more than commodity state. |

Potential factor modules:

| Module | Candidate fields |
| --- | --- |
| Valuation | PB, PE, EV / EBITDA if available, free-cash-flow yield. |
| Dividend | Dividend yield, payout ratio, dividend continuity, cash dividend coverage. |
| Cash flow | Operating cash flow, capex, free cash flow, capex / operating cash flow. |
| Operating quality | ARPU, mobile users, broadband users, enterprise-service revenue share, EBITDA margin. |
| Risk control | Capex pressure, debt pressure, regulatory / price-war signals. |

Data availability pre-screen:

| Data requirement | Preliminary status | Notes |
| --- | --- | --- |
| PIT universe | likely_pass_with_review | Small and explicit universe, but listing-date and A-share availability must be handled. |
| Financial PIT fields | likely_pass | JQData / DataJQ should cover statements, valuation, dividends, daily prices. |
| Operating fields | needs_manual_research | ARPU, user counts, capex cycle, enterprise-service mix usually come from annual reports. |
| External state | likely_pass | Interest-rate proxy and capex-cycle fields are feasible. |
| Benchmark | needs_check | Prefer telecom / communication services index if available; otherwise equal-weight core universe benchmark. |
| Statistical sample | high_risk | Only three A-share core operators. IC / RankIC may be weak due to small N. |

Gate status:

```text
sector_knowledge_gate_needs_more_sources
data_gate_needs_manual_research
```

PM view:

```text
Best V5.5 first candidate if the goal is high-dividend cash-flow replication, but sample-size risk must be disclosed.
It may be better as a concentrated basket / paper-trading candidate than a broad cross-sectional IC strategy.
```

## Candidate 2: Gas / Water Operators

Sector boundary:

```text
A-share gas distribution, water supply, water treatment, and utility operation companies.
Exclude equipment makers, pure environmental engineering contractors, waste-to-energy equipment, and project-based construction firms unless recurring operating revenue dominates.
```

Industry knowledge pre-screen:

| Area | Preliminary view |
| --- | --- |
| Business model | Regulated or semi-regulated local utility operation with recurring demand. |
| Profit drivers | Gas / water sales volume, tariff policy, connection fees, purchase cost pass-through, operating region growth. |
| Dividend logic | Stable operating cash flow may support dividend and low-volatility strategy. |
| Value trap risk | Price controls, receivable stress, local fiscal pressure, construction / engineering revenue masking weak operation quality. |
| External state | Low to moderate. Natural gas cost spread, tariff adjustment, interest-rate state, and local demand matter. |

Potential factor modules:

| Module | Candidate fields |
| --- | --- |
| Valuation | PB, PE, dividend yield, cash-flow yield. |
| Dividend | Dividend continuity, payout ratio, dividend coverage. |
| Cash flow | Operating cash flow, free cash flow, receivables pressure. |
| Operating purity | Utility-operation revenue share, gas / water volume, tariff / spread where available. |
| Risk control | Construction revenue share, receivables growth, debt / interest burden. |

Data availability pre-screen:

| Data requirement | Preliminary status | Notes |
| --- | --- | --- |
| PIT universe | needs_review | Need to separate real operators from engineering / equipment / environmental project companies. |
| Financial PIT fields | likely_pass | Standard financial, valuation, dividend, daily price fields should be available. |
| Operating fields | needs_manual_research | Volumes, tariffs, utility-operation revenue share likely require filings / F10 / manual panel. |
| External state | likely_pass_with_proxy | Gas price spread can be proxied; water tariff is more local and harder. |
| Benchmark | needs_check | Equal-weight same-pool benchmark is likely needed if no pure sector benchmark is available. |
| Statistical sample | medium | Larger than telecom, but business-model impurity risk is higher. |

Gate status:

```text
sector_knowledge_gate_needs_more_sources
data_gate_needs_manual_research
```

PM view:

```text
Good second candidate. It is closest to the utilities golden template, but requires careful operating-purity and receivables-risk gates.
```

## Candidate 3: Port / Rail Infrastructure

Sector boundary:

```text
A-share port operators, railway operators, and transport infrastructure operation companies.
Exclude airlines, shipping carriers, logistics asset-light companies, highway names already covered by V5.4, and equipment makers.
```

Industry knowledge pre-screen:

| Area | Preliminary view |
| --- | --- |
| Business model | Infrastructure assets earning throughput, freight, passenger, port handling, and related service revenue. |
| Profit drivers | Cargo throughput, freight volume, tariff / pricing policy, regional trade, operating leverage, capex and debt. |
| Dividend logic | Mature infrastructure assets can produce distributable cash flow. |
| Value trap risk | Trade-cycle exposure, tariff controls, asset-heavy capex, regional overcapacity, related-party transactions. |
| External state | Moderate to high. Trade, freight, commodity throughput, and regional demand can dominate results. |

Potential factor modules:

| Module | Candidate fields |
| --- | --- |
| Valuation | PB, PE, dividend yield, cash-flow yield. |
| Dividend | Dividend continuity, payout ratio, dividend coverage. |
| Cash flow | Operating cash flow, capex, free cash flow. |
| Operating state | Cargo throughput, container throughput, freight volume, utilization. |
| Risk control | Debt pressure, capex expansion, cyclical throughput decline. |

Data availability pre-screen:

| Data requirement | Preliminary status | Notes |
| --- | --- | --- |
| PIT universe | needs_review | Need to split port, rail, logistics, shipping, airport, and highway exposures. |
| Financial PIT fields | likely_pass | Standard fields should be available. |
| Operating fields | needs_manual_research | Throughput / freight volume should exist but must be reviewed from filings or official sources. |
| External state | needs_manual_research | Trade / freight-cycle state is required for ports and rail. |
| Benchmark | needs_check | Transport / infrastructure index may exist; otherwise equal-weight same-pool benchmark. |
| Statistical sample | medium | Better than telecom, but mixed business models increase noise. |

Gate status:

```text
sector_knowledge_gate_needs_more_sources
data_gate_needs_manual_research
```

PM view:

```text
Promising, but more state-dependent than telecom or gas / water. It should not be first unless operating-state data is easy to build.
```

## PM Candidate Ranking

| Rank | Candidate | PM status | Reason |
| --- | --- | --- | --- |
| 1 | telecom_operators | prelaunch_preferred_candidate | Best fit with high-dividend / cash-flow route, simple boundary, but small-sample risk. |
| 2 | gas_water_operators | backup_candidate | Closest to V5.1 utilities golden template, but needs operating-purity review. |
| 3 | port_rail_infrastructure | watchlist_candidate | Cash-flow logic is good, but external trade / freight state burden is higher. |

## Decision

PM decision:

```text
Do not start V5.5 formal modeling yet.
Start V5.5 prelaunch Gate 1 + Gate 2 on telecom_operators first.
Prepare gas_water_operators as backup if telecom sample size blocks formal validation.
Keep port_rail_infrastructure on watchlist until operating-state data sources are clearer.
```

## Next Required Artifacts For Telecom Operators

Research Agent must create:

| Artifact | Required path |
| --- | --- |
| Telecom value investing framework | `knowledge/research_agent/factor_theory/telecom_operators_value_investing_framework.md` |
| Telecom core factor hypotheses | `knowledge/research_agent/factor_theory/telecom_operators_core_factor_hypotheses.md` |
| Telecom value trap framework | `knowledge/research_agent/factor_theory/telecom_operators_value_trap_framework.md` |
| Telecom universe definition | `knowledge/research_agent/references/telecom_operators_universe_definition.md` |
| Telecom data field map | `knowledge/research_agent/references/telecom_operators_data_field_map.md` |
| Telecom source collection plan | `knowledge/research_agent/references/telecom_operators_source_collection_plan.md` |
| Telecom validation handoff | `knowledge/research_agent/references/telecom_operators_validation_handoff.md` |

PM must then decide:

```text
sector_knowledge_gate_passed / sector_knowledge_gate_needs_more_sources / sector_knowledge_gate_blocked
data_gate_passed / data_gate_needs_manual_research / data_gate_blocked
```

## Engineering Block

Engineering Agent must not write a telecom strategy or JoinQuant script at this stage.

Allowed engineering work only:

```text
data probe scripts
manual import templates
PIT universe builder prototype
benchmark availability probe
```

## Hard Rule

V5.5 cannot enter formal validation until the chosen sector has:

```text
sector_knowledge_gate_passed
data_gate_passed
```


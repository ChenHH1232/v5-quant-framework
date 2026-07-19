# Airport / Transport External State Field Map V5.8

Date: 2026-07-19

Owner:

```text
Research Agent
```

Status:

```text
external_state_field_map
supports_airport_transport_operators_v58
not_quant_validation_ready
```

## Boundary

This file covers airport operators only. Highway and port / rail already have separate operating-state evidence lines.

Current first-layer PIT business-purity universe:

```text
600009.XSHG Shanghai Airport
600004.XSHG Baiyun Airport
000089.XSHE Shenzhen Airport
600897.XSHG Xiamen Airport
```

Excluded from airport operator universe for now:

```text
600515.XSHG Hainan Airport
reason=visible Eastmoney segment evidence shows airport operator revenue share below 50% on every 2021-2026 rebalance date.
```

## MECE State Questions

| State question | Why it matters | Candidate PIT field |
| --- | --- | --- |
| Passenger recovery | Aeronautical fee, commercial rent and advertising demand depend on passenger flow. | airport_passenger_throughput_yoy |
| International route recovery | International passenger mix and duty-free / concession economics can differ from domestic recovery. | airport_international_passenger_recovery |
| Cargo resilience | Cargo can support Shanghai / gateway airports even when passenger traffic is weak. | airport_cargo_throughput_yoy |
| Aircraft movements | Takeoff / landing and ground service revenue are linked to aircraft movements. | airport_aircraft_movement_yoy |
| Commercial exposure | Rent, concession and duty-free exposure can amplify recovery but also add policy / contract risk. | airport_commercial_revenue_share |
| Capex pressure | Expansion and terminal renewal can distort FCF and dividend capacity. | airport_capex_to_ocf |
| Policy / fee state | Airport fee and concession policy changes can break historical cash-flow relationships. | airport_policy_state_flag |

## Source Priority

| Source | Fields | PIT treatment | Status |
| --- | --- | --- | --- |
| Listed-company monthly operating briefings | airport-level passenger throughput, cargo throughput, aircraft movements, YoY | Use announcement date as visible_date. Prefer SSE/SZSE/CNINFO original announcements. | required before Quant |
| Annual / interim reports | business segment shares, commercial / rental / duty-free exposure, capex plans | Use report announcement date. Eastmoney only gives first-layer clues until original report spot check. | required before Engineering |
| CAAC monthly main production indicators | national / route-level passenger and cargo state | Use CAAC publish date as visible_date. Can explain macro state but not company-specific selection alone. | useful state proxy |
| CAAC annual airport statistical bulletin | airport ranking, passenger/cargo/aircraft movement totals, recovery levels | Use CAAC publish date. Annual only, too slow for high-frequency timing. | background / annual state |
| Research reports | operating framework, state variable selection, risk themes | Knowledge only. Not scoring data unless source data is separately PIT-verified. | optional knowledge |

## Initial Official Source Leads

- CAAC 2025 airport statistical bulletin: `https://www.caac.gov.cn/XWZX/MHYW/202602/t20260227_230131.html`
- CAAC 2025 civil aviation development statistical bulletin: `https://www.caac.gov.cn/XWZX/MHYW/202604/t20260417_230603.html`
- CAAC 2025 monthly production indicator example: `https://www.caac.gov.cn/XXGK/XXGK/TJSJ/202601/t20260120_229807.html`
- CAAC 2022 airport statistical bulletin: `https://www.caac.gov.cn/XXGK/XXGK/TJSJ/202303/t20230317_217609.html`
- Shanghai Airport monthly operating briefing example: `https://www.sse.com.cn/disclosure/listedinfo/announcement/c/new/2025-01-15/600009_20250115_KF2P.pdf`
- Shanghai Airport 2025 annual report example: `https://star.sse.com.cn/disclosure/listedinfo/announcement/c/new/2026-04-30/600009_20260430_BK10.pdf`
- Baiyun Airport 2025 annual report summary example: `https://big5.sse.com.cn/disclosure/listedinfo/announcement/c/new/2026-04-30/600004_20260430_U3M8.pdf`

## Candidate Field Schema

```text
code
report_period_or_month
visible_date
source_name
source_url
passenger_throughput
passenger_throughput_yoy
cargo_throughput
cargo_throughput_yoy
aircraft_movements
aircraft_movements_yoy
international_passenger_throughput
international_passenger_recovery_vs_2019
airport_commercial_revenue_share
airport_operator_revenue_share
capex_to_ocf
policy_state_flag
review_status
notes
```

## Research Hypothesis Implication

Airport operators should not simply inherit the highway dividend model. The first testable hypothesis should be:

```text
Among business-pure airport operators, OCF yield plus dividend support may work only when passenger / cargo state is not deteriorating. Operating state should start as a guard or failure-explanation variable, not as a positive alpha score.
```

## Next Step

Research Agent should build:

```text
airport_transport_operating_state_manual_template.csv
airport_transport_annual_report_spot_check_template.csv
```

Quant Validation Agent must wait until at least the company-level monthly operating state panel or a documented annual proxy is available with visible_date.

Historical performance alone is never sufficient evidence for accepting a strategy.

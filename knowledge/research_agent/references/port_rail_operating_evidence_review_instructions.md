# Port / Rail Operating Evidence Review Instructions

Date: 2026-07-18

Owner:

```text
Research Agent
```

## Input Template

```text
数据库/processed/port_rail_operating_evidence_v55d/port_rail_operating_evidence_manual_template.csv
```

## Review Rule

A row is usable only when:

```text
original_announcement_checked=true
review_status=reviewed
pit_status=pit_usable
visible_date <= rebalance_date where the data is used
```

## Preferred Sources

1. Annual reports and interim reports.
2. Exchange or company announcements.
3. Company operating data announcements.
4. Official transport / port / railway statistics.
5. Eastmoney F10 only as a first-layer structured hint, not final proof.

## Required Evidence

For each code, try to fill:

```text
port_revenue_share
rail_revenue_share
cargo_throughput
container_throughput
rail_freight_volume
rail_passenger_volume
tariff_policy_evidence
capex_project_commitment
source_title
source_url
publish_date
visible_date
```

If a company does not disclose a field, record:

```text
pit_status=not_disclosed
missing_reason=company_not_disclosed
```

Do not invent or infer numeric values without source support.


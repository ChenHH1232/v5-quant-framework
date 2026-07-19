# V5.3c Insurance Special Fields Source Repair Execution V1

Date: 2026-07-17

Status:

```text
insurance_special_fields_source_repair_passed
```

Not status:

```text
platform_replication_approved
accepted_strategy
```

## Purpose

Repair the insurance-specific PIT field packet before any V5.3d hypothesis or validation work starts.

The rule is strict:

```text
Every imported row must carry the original announcement publication date and original_announcement_checked=true.
```

## Reviewed Source Packet

Reviewed CSV:

```text
knowledge/research_agent/references/insurance_special_fields_reviewed_2025_core5.csv
```

Audit output:

```text
insurance_special_fields_audit_reviewed_2025_core5/insurance_low_pb_only_v53c/
```

Command:

```text
python -m v5.cli insurance-special-fields-audit knowledge\research_agent\references\insurance_special_fields_reviewed_2025_core5.csv --out insurance_special_fields_audit_reviewed_2025_core5
```

## Source Scope

Core codes reviewed:

| Code | Company | Primary source date |
| --- | --- | --- |
| 601318.XSHG | Ping An Insurance | 2026-03-27 |
| 601628.XSHG | China Life Insurance | 2026-03-26 |
| 601601.XSHG | CPIC | 2026-03-27 |
| 601336.XSHG | New China Life Insurance | 2026-03-28 |
| 601319.XSHG | PICC Group | 2026-03-27 |

Source priority used:

1. Eastmoney original announcement PDFs.
2. Company official solvency summary PDF where Eastmoney did not expose the same group-level solvency detail.
3. HK annual results announcement for PICC because the A-share annual report text extraction dropped key numeric values.

## Audit Result

| Item | Value |
| --- | ---: |
| Rows | 30 |
| PIT usable rows | 28 |
| Field count | 6 |
| PIT blocked rows | 2 |
| Blockers | 0 |
| Minimum core code count | 5 |

Usable core fields:

```text
embedded_value
new_business_value
core_solvency_ratio
comprehensive_solvency_ratio
total_investment_yield
```

Optional enhancement field:

```text
net_investment_yield
```

## Why Still Blocked

`net_investment_yield` is PIT usable for only three of five core insurance codes:

```text
601601.XSHG
601336.XSHG
601319.XSHG
```

For:

```text
601318.XSHG
601628.XSHG
```

the original annual / results PDFs were checked, but no annual net investment yield was found. Ping An discloses a 10-year average net investment return, and China Life discloses net investment income amount but not annual net investment yield. These were recorded as:

```text
pit_status = not_disclosed
missing_reason = not_disclosed
original_announcement_checked = true
review_status = reviewed
```

This means the issue is a real disclosure / field-definition limitation, not a missing announcement-date issue.

## PM Decision

Research Agent decision:

```text
net_investment_yield is downgraded to optional enhancement.
total_investment_yield is the V5.3d required investment-quality field.
```

Decision memo:

```text
docs/governance/v53d_insurance_investment_quality_field_decision_v1.md
```

After this decision, the source-repair gate passes and V5.3 moves to:

```text
v53d_research_hypothesis_design
```

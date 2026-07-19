# V5.3d Insurance Investment Quality Field Decision V1

Date: 2026-07-17

Agent:

```text
Research Agent
```

Status:

```text
research_field_decision_passed
```

## Decision

`net_investment_yield` is downgraded from a required V5.3d core field to an optional enhancement field.

The V5.3d core investment-quality field is:

```text
total_investment_yield
```

Company-specific investment-yield aliases may be retained as audit metadata, but they must not be silently mapped into a unified core field.

## Why

Insurance investment quality matters because low-PB insurance stocks can be value traps when the asset side deteriorates. However, a deployable V5 field must be:

- PIT visible;
- disclosed from original announcements;
- annual, not multi-year average;
- comparable across core companies.

`net_investment_yield` fails the current coverage and comparability test:

| Code | Company | Finding |
| --- | --- | --- |
| 601318.XSHG | Ping An Insurance | Original annual / results PDFs checked; annual net investment yield not found. The report discloses a 10-year average net investment return, which is not an annual PIT field. |
| 601628.XSHG | China Life Insurance | Original annual PDF checked; net investment income amount is disclosed, but annual net investment yield was not found. |

Self-computing a net yield from amount and an inferred asset base would introduce an outside formula and break the source-consistency rule.

`total_investment_yield` is less pure economically because it includes broader market and fair-value effects, but it has five-code reviewed PIT coverage and is directly disclosed. For V5.3d, auditability beats theoretical neatness.

## Audit Consequence

The insurance special-fields gate now treats the following as V5.3d core fields:

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

Re-run result:

```text
insurance_special_fields_source_repair_passed
```

Next gate:

```text
v53d_research_hypothesis_design
```

## Quant Validation Instructions

Quant Validation Agent should test V5.3d using:

1. Low PB as the baseline value signal.
2. EV / NBV level or improvement as life-franchise quality evidence.
3. Core and comprehensive solvency ratios as balance-sheet and dividend-safety evidence.
4. `total_investment_yield` as the required investment-quality field.
5. `net_investment_yield` only as a robustness or subgroup enhancement where directly disclosed.

The validation packet must include:

- baseline;
- IC / RankIC;
- rolling validation;
- ablation;
- robustness;
- failure-year analysis for 2021, 2022 and 2026;
- comparison against V5.3c low-PB-only.

## Do Not

- Do not treat Ping An's 10-year average net investment return as annual `net_investment_yield`.
- Do not convert China Life's net investment income amount into annual yield unless the original announcement provides the formula and denominator.
- Do not accept a vendor-filled value without original announcement publication date.
- Do not tune 2021-2026 returns to improve the model.
- Do not write JoinQuant strategy code before V5.3d formal validation.


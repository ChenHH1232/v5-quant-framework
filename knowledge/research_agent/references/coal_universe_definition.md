# Coal Universe Definition

Date: 2026-07-16

Project:

```text
V5.2 Coal High-Dividend / Cycle-Value Process-Portability Test
```

Status:

```text
research_preparation
```

## Universe Definition

The V5.2 universe is:

```text
A-share coal mining and coal operating companies
```

The universe is an industry universe, not a high-dividend style basket.

## Include

- coal mining;
- coal washing;
- integrated coal operators where coal is the dominant profit driver;
- thermal coal producers;
- coking coal producers.

## Exclude

- pure coal chemical companies;
- coal machinery and mining equipment;
- non-coal mining;
- broad high-dividend SOE baskets;
- diversified companies where coal is not the core profit driver.

## Mixed-Business Tags

Every candidate company must receive one of these tags:

| Tag | Meaning | Default treatment |
| --- | --- | --- |
| `core_coal` | coal mining / washing is core profit driver | include |
| `integrated_coal_power_transport` | coal plus power, rail, port, or logistics integration | include with subgroup tag |
| `mixed_power_coal` | coal and power both material | include in broad run, test exclusion |
| `mixed_coal_chemical` | coal chemical material to economics | include only after manual review |
| `mixed_energy` | coal exposure exists but other energy exposure is material | manual review |
| `exclude_non_core` | coal is not core or company is equipment / non-coal mining | exclude |

## Candidate Industry Construction

Initial candidate construction should use a union of:

- JoinQuant coal industry;
- Shenwan coal mining industry;
- CSRC coal mining and washing industry.

Then apply manual business-line review using company disclosures.

## Point-In-Time Requirement

The formal universe must not use only a current industry list. It must store:

- `code`;
- `company_name`;
- `industry_source`;
- `industry_code`;
- `industry_name`;
- `membership_start_date`;
- `membership_end_date`;
- `membership_visible_date`;
- `coal_business_tag`;
- `tag_source`;
- `tag_visible_date`.

## Research Rule

If PIT industry membership is incomplete, Quant Validation Agent may run an exploratory sensitivity check, but PM must label the result as:

```text
data_gap_exploratory_only
```

It cannot promote a formal strategy candidate.

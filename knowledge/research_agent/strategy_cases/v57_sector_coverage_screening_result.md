# V5.7 Sector Coverage Screening Result

Date: 2026-07-18

## Research Context

V5.7 starts the industry-coverage path for a future:

```text
Dividend Low-Vol OCF Basket with sector-approved FCF enhancement
```

The current basket evidence supports:

- operating cash-flow yield as the primary cross-sector signal;
- volatility and drawdown as risk / coverage guards;
- dividend yield as shareholder-return support;
- FCF only as a sector-approved enhancement;
- no basket-wide low PB mainline.

## Stage 1 Result

Output:

```text
validation_formal_v57_sector_coverage
```

Decision counts:

| Decision | Count |
| --- | ---: |
| ready_for_basket_shadow_pool | 4 |
| needs_manual_research_before_formal | 5 |
| basket_observation_only | 2 |
| blocked_by_data_gate | 1 |
| blocked_by_cycle_data_gate | 1 |

## Research Priorities

1. `gas_water_operators`
   - Most similar to utilities / electricity.
   - Research must separate true operators from engineering/project companies.
   - FCF must be checked against receivables, project revenue and capex burden.

2. `telecom_operators`
   - Strong business fit for dividend / OCF / low-vol.
   - Sample is too small for broad cross-sectional IC.
   - Treat as observation sleeve unless PM approves a small-sample policy.

3. `airport_transport_operators`
   - Needs traffic volume, recovery cycle, concession and policy state.

4. `oil_gas_pipeline_integrated`
   - Needs commodity state, spread state and PIT business-exposure tags.

## Blocked

- `coal`: cycle-state data gate remains incomplete.
- `environmental_project_operators`: receivables and project revenue create high cash-flow-trap risk.

## PM Rule

Research Agent should not propose new sector factors until the sector passes the knowledge and data availability gates.

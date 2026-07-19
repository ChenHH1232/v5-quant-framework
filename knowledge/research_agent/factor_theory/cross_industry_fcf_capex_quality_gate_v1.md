# Cross-Industry FCF / Capex Quality Gate V1

Date: 2026-07-18

Owner:

```text
Research Agent
```

Status:

```text
research_framework
requires_quant_validation_before_factor_promotion
```

## Purpose

V5.6c rejected the simple basket narrative that raw low PB and raw FCF should be universal core factors.

This gate defines when free cash flow can be used in a dividend low-volatility OCF basket:

```text
FCF is allowed only when the sector's capex pattern is financially interpretable and PIT measurable.
```

## Starting View

Current V5 evidence supports:

```text
primary factor: operating_cash_flow_yield
risk guard: low volatility / drawdown / beta
support factor: dividend yield and dividend coverage
conditional enhancement: free_cash_flow_yield
rejected basket-wide mainline: low PB + raw FCF
```

## FCF Approval Classes

| Class | Meaning | FCF Use | Example Sector Logic |
| --- | --- | --- | --- |
| `fcf_core_candidate` | Capex is stable, maintenance-like, and not masking future growth collapse | May enter scoring after validation | Mature toll roads, mature ports, some stable utilities |
| `fcf_support_candidate` | FCF is useful but sensitive to investment cycle or policy timing | Use as guard or tie-breaker | Electricity, gas/water, telecom operators |
| `fcf_diagnostic_only` | FCF helps explain risk but should not score positively | Diagnostics and failure attribution only | Insurance, banks, sectors with accounting mismatch |
| `fcf_blocked` | FCF is too distorted by cycle, project revenue, working capital, subsidy or missing data | Do not use in formal scoring | Coal until cycle data is repaired, environmental project operators |

## Required Evidence Before FCF Promotion

Every sector must pass these checks before FCF becomes a scoring factor:

| Gate | Required Evidence | Fail Action |
| --- | --- | --- |
| PIT availability | FCF components have report date and visible date | Downgrade to diagnostic |
| Capex meaning | Maintenance capex can be separated from growth/policy capex or at least interpreted | Use OCF instead |
| Accounting stability | `fix_intan_other_asset_acqui_cash` or equivalent capex field is stable for the sector | Mark capex noisy |
| Cash conversion | OCF is not dominated by working-capital timing or receivable reversal | Add receivables guard |
| Dividend coverage | Dividends are covered by cash generation over rolling periods | Dividend support only |
| Debt pressure | FCF is not created by underinvestment while leverage rises | Add leverage/debt guard |
| External state | Cyclical or policy sectors have ex-ante external state data | Block formal promotion |

## Sector Application

### Bank

FCF is not a natural bank factor.

Use:

```text
dividend sustainability
asset quality
capital adequacy
deposit/franchise indicators
```

FCF status:

```text
fcf_diagnostic_only
```

### Utilities / Electricity

OCF is usually more interpretable than FCF because capex is affected by generation mix, policy, grid projects and capacity buildout.

FCF status:

```text
fcf_support_candidate
```

### Highway

FCF can be useful if concession maturity, toll-policy risk and maintenance capex are reviewed.

FCF status:

```text
fcf_core_candidate_after_operating_review
```

### Port / Rail

FCF can be useful but must avoid logistics/trade business contamination.

FCF status:

```text
fcf_support_to_core_candidate_after_business_purity_review
```

### Gas / Water

OCF may be distorted by receivables, government payment and tariff reform timing. FCF can be distorted by network expansion and project investment.

FCF status:

```text
fcf_support_candidate_after_receivables_and_operator_purity_gate
```

### Telecom Operators

FCF is economically important, but capex cycle, depreciation burden and network/AI/cloud investment cycle dominate interpretation.

FCF status:

```text
fcf_support_candidate_small_sample_observation
```

### Coal

FCF depends on coal price cycle, production, inventory, safety capex and expansion capex.

FCF status:

```text
fcf_blocked_until_cycle_state_repaired
```

### Insurance

FCF is not the right main accounting lens.

Use:

```text
EV
NBV
P/EV
solvency
investment income quality
liability-cost and rate state
```

FCF status:

```text
fcf_diagnostic_only
```

## Quant Validation Requirement

Before promotion, Quant Validation Agent must run:

```text
baseline: OCF only, dividend only, low-vol guard only
IC / RankIC: FCF and OCF separately
rolling validation
ablation: with and without FCF
robustness: rebalance date, selection count, sector cap, single-stock cap
failure-year analysis
common-sample coverage check
```

FCF is promoted only if it improves evidence without creating:

```text
coverage collapse
single-sector concentration
one-period dependence
capex-cycle hindsight
```

## PM Rule

```text
OCF is the default cross-sector cash-flow factor.
FCF is a sector-specific enhancement that must earn its place.
```

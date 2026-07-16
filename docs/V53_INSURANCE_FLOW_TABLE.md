# V5.3 Insurance Flow Table

Date: 2026-07-16

Project:

```text
V5.3 Insurance Value / Quality Process-Portability Test
```

Current PM status:

```text
research_preparation_execution_started
```

## Flow Table

| Order | Stage | Owner | Action | Required input | Output | Gate |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | PM intake | Project Manager Agent | Confirm sector boundary and experiment layer | V5.2b closeout, V5.3 selection | `v53_insurance_pm_intake_v1.md` | Approved for preparation only |
| 2 | Research universe | Research Agent | Define insurance operating-company universe | A-share listings, industry classification, company disclosures | `insurance_universe_definition.md` | Must exclude banks, brokers and non-insurance holdings |
| 3 | Research field map | Research Agent | Map valuation, EV/NBV, solvency, underwriting, investment and state fields | JoinQuant/DataJQ, reports, solvency reports, vendor pages | `insurance_data_field_map.md` | Must mark PIT route and missing-data risk |
| 4 | Research theory | Research Agent | Write insurance value / quality framework | Insurance economics and failure modes | `insurance_value_quality_framework.md` | Must separate life, P&C and group economics |
| 5 | Research hypotheses | Research Agent | Build candidate factor list | Universe + field map + theory | `insurance_core_factor_hypotheses.md` | Hypotheses only, no performance tuning |
| 6 | Research source plan | Research Agent | Define source order and access guardrails | Company disclosures, regulator, JoinQuant/DataJQ, Tushare, Eastmoney | `insurance_source_collection_plan.md` | Vendor data not PIT-usable until audited |
| 7 | Engineering data probe | Engineering Agent | Probe industry membership and field availability | JoinQuant/DataJQ credentials and local database | `insurance_data_probe` packet | No strategy code; only availability evidence |
| 8 | PM Gate 1 | Project Manager Agent | Decide whether research packet is complete | Research docs + data probe | PM preparation decision | Approve or block `research_pit_validation` |
| 9 | Quant PIT panel | Quant Validation Agent | Build formal PIT panel if Gate 1 passes | Universe, factor fields, visible dates, returns | insurance PIT panel | Must include leakage audit metadata |
| 10 | Formal validation | Quant Validation Agent | Run baseline, IC / RankIC, rolling, ablation, robustness | PIT panel + spec | formal validation packet | No 2021-2026 tuning |
| 11 | PM Gate 2 | Project Manager Agent | Decide whether model becomes formal candidate | Quant packet | candidate / reject decision | Must be evidence-driven |
| 12 | Engineering simulation | Engineering Agent | Build local daily simulation only after freeze | Frozen candidate + real execution data | daily NAV, holdings, trades, cash, dividends, signals | Not research evidence |
| 13 | Platform replication | Engineering Agent + PM | Compare local vs JoinQuant | JoinQuant exports and local logs | attribution packet | Pass / data gap / contract mismatch |
| 14 | Paper trading | PM + Engineering Agent | Record future signals without retroactive tuning | Frozen model | forward signal log | Needed before accepted strategy |

## Immediate Execution Scope

Approved now:

```text
steps 2 to 8
```

Blocked now:

```text
strategy code
local daily strategy simulation
JoinQuant strategy generation
paper trading
accepted-strategy labeling
```

## PM Rule

V5.3 may enter Quant Validation only after PM confirms:

- insurance universe is genuinely insurance-led;
- life and P&C economics are separated;
- `insurance_indicator` or equivalent report-derived fields have PIT visibility;
- rate and equity-market states are collectible;
- field gaps are explicit rather than silently filled.


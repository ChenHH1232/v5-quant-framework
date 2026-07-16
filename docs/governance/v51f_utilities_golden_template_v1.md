# Governance Record: v51f_utilities_golden_template_v1

Date: 2026-07-17

Status:

```text
utilities_golden_workflow_template
```

Not status:

```text
accepted_strategy
live_trading_approved
```

## PM Decision

V5.1f Utilities / Electricity becomes the first V5 golden workflow template.

This means the workflow is valuable as a repeatable operating model, not that the strategy is accepted.

## Why Utilities Is The Template

Utilities / electricity passed the most important process checks:

- sector economics are explainable;
- external state data can be defined;
- factor logic can be separated by state;
- formal validation can be run;
- engineering smoke tests can be run;
- overfit audit exists;
- paper-trading log exists;
- PM can distinguish research evidence from platform and paper-trading evidence.

## Required Golden Packet

Every future sector candidate should be compared against this packet:

| Packet Item | Required |
| --- | --- |
| Sector research knowledge packet | yes |
| Research memo | yes |
| PIT universe definition | yes |
| Data availability gate | yes |
| External state panel, if economically required | yes |
| Formal validation packet | yes |
| Baseline / IC / RankIC / rolling / ablation / robustness | yes |
| Engineering smoke test | yes |
| Local daily simulation | yes, after research gate |
| Platform replication | only after PM approval |
| Overfit audit | yes |
| Paper-trading log | yes, after candidate freeze |
| Machine-readable status registry entry | yes |

## Productization Work

Engineering and PM should now make the utilities path reusable by:

- making the Research Agent knowledge packet the first required gate for any new sector;
- keeping a stable output folder convention;
- preserving one-command validation and smoke-test runners where possible;
- recording benchmark and dividend policies explicitly;
- using the same scoring function in formal validation and backtests;
- keeping paper-trading signals immutable once recorded.

Detailed workflow table:

```text
docs/governance/v51f_utilities_golden_workflow_table_v1.md
```

Latest executable audit:

```text
docs/governance/v51f_utilities_golden_workflow_execution_v1.md
```

## Next Gate

```text
golden_template_productization_in_progress
```

No broad new-sector testing should outrank this work.

# Coal V5.2b Final Inputs Audit Result

Date: 2026-07-16

Status:

```text
engineering_inputs_repaired_but_external_state_still_blocked
```

## Research Memory

V5.2b Coal repaired the Engineering audit-input gap, but not the Research / Quant external-state gap.

Daily returns and rebalance signals now exist, so overfit audit can run. The remaining problem is not engineering execution. It is that the coal cycle state is still incomplete without PIT-ready raw-coal output or inventory history.

## Current Evidence

Formal validation shows positive factor evidence:

- OCF yield: mean IC `0.1370`, mean RankIC `0.1359`;
- FCF yield: mean IC `0.1167`, mean RankIC `0.1152`;
- low PB: mean IC `0.0886`, mean RankIC `0.1080`;
- low PE: mean IC `0.0714`, mean RankIC `0.0836`.

But 2018 remains a severe failure year:

```text
2018 selected cumulative return = -35.94%
2018 positive period ratio = 0.00%
```

The selected basket only slightly outperformed the broad coal universe, so this looks like a sector-cycle drawdown, not a solved factor failure.

## External State Lesson

Coking-coal and thermal-coal price states are useful, but they are not enough for formal acceptance.

For coal, Research Agent should require at least one PIT-ready supply / inventory series:

- raw-coal output;
- coal inventory;
- port inventory;
- production utilization;
- coal-power spread or equivalent demand-pressure proxy.

Without this layer, cycle-state validation can only explain history after the fact.

## PM Outcome

Do not promote V5.2b to formal strategy candidate.

Use it as:

- a workflow-replication success;
- a negative-control strategy case;
- a reminder that high cyclical returns need external-state evidence.

Do not use it as:

- JoinQuant production code;
- paper trading;
- accepted strategy evidence.


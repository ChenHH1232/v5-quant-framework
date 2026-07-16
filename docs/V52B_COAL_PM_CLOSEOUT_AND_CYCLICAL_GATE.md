# V5.2b Coal PM Closeout And Cyclical Gate

Date: 2026-07-16

Owner:

Project Manager Agent

## PM Closeout

V5.2b Coal is paused as a strategy track.

Final operating status:

```text
workflow_replication_passed_strategy_candidate_failed
```

Reason:

- V5 workflow successfully replicated to a cyclical commodity industry.
- Research, Quant Validation and Engineering gates worked.
- Engineering audit inputs were repaired.
- The strategy itself did not pass formal promotion.
- The hard blocker is not engineering; it is incomplete PIT-ready external cycle-state data.
- Raw coal output / inventory history is still not complete enough.
- 2018 remains a severe weak year without enough ex-ante explanation.

V5.2b Coal moves to:

```text
data_completion_watchlist
```

Allowed future work:

- official raw-coal output / inventory import;
- verified port inventory / industry inventory source registration;
- coal-power spread source audit;
- use as negative-control process memory.

Disallowed work:

- JoinQuant production strategy code;
- paper trading;
- accepted-strategy labeling;
- further factor tuning on 2021-2026 platform window.

## Cyclical Industry Data Gate

For coal, steel, non-ferrous metals, chemicals and similar cyclical commodity sectors, PM must block formal modeling unless all four data layers are available with PIT visible dates.

| Layer | Required evidence | Why it matters |
| --- | --- | --- |
| Commodity price state | spot or officially reviewed price series | identifies price-cycle regime |
| Production / inventory / supply-demand state | output, inventory, utilization or equivalent | avoids pure price-only post-hoc explanation |
| Spread / margin state | commodity-product spread, electricity spread, refining spread, or profit proxy | links price to company economics |
| Company business-exposure PIT tags | segment revenue / profit with report publication dates | avoids using today's business structure in historical validation |

Required fields:

```text
state_date
source_publication_date
visible_date
source_name
source_url_or_file
pit_usable
review_status
```

PM rule:

```text
If any required cyclical layer is missing, the project may run data probes and workflow tests, but it cannot enter formal strategy-candidate promotion.
```

## V5.3 Selection

Next main project:

```text
V5.3 Insurance Value / Quality Process-Portability Test
```

Reason for selecting insurance:

- It is closer to banks than coal and utilities, so V5 can test financial-sector transfer.
- It has different economics from banks: liability duration, embedded value, new business value, solvency, investment spread and claim risk.
- It should expose whether V5 can reuse governance while changing domain-specific factor logic.
- It avoids immediately entering another hard-cycle commodity sector with unresolved external-state data requirements.

Coal remains a data-engineering side track, not the main strategy path.


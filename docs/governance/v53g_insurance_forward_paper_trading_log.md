# V5.3g Insurance Forward / Paper Trading Log

Date opened: 2026-07-17

Strategy:

```text
insurance_pev_value_v53g
```

Status:

```text
paper_trading_started
```

Not status:

```text
accepted_strategy
live_trading_approved
post_2026_forward_evidence_passed
```

## Purpose

Record future V5.3g insurance P/EV signals after the model has been frozen as a formal strategy candidate.

This log is forward evidence only. It must not be used to rewrite historical validation, tune the 2021-2026 confirmation window, or change the frozen research hypothesis.

## Frozen Candidate Rule

```text
At each quarterly rebalance, select the 3 core listed A-share insurers with the lowest PIT-visible P/EV.
```

Core constraints:

- use only PIT-visible embedded value;
- use current market capitalization only on the signal date;
- do not add NBV growth into scoring;
- do not add solvency, ROE, dividend, PB, PE, or investment yield into scoring;
- do not change selection count;
- do not add defensive timing or stop rules;
- record failed data collection as a failure instead of manually replacing the signal.

## Required Signal Packet

Each future paper-trading signal must record:

- signal date;
- rebalance date;
- latest visible EV report period;
- latest EV visible date;
- candidate count;
- selected count;
- selected securities;
- P/EV values;
- target weights;
- blocked or missing securities and reasons;
- whether the signal came from local runner, JoinQuant live recompute, or frozen-signal fallback;
- PM decision.

## Entries

| Entry Date | Signal Date | Layer | Candidate Count | Selected Count | Selected Codes | Data Coverage | Execution Status | Notes | PM Decision |
| --- | --- | --- | ---: | ---: | --- | --- | --- | --- | --- |
| 2026-07-17 | pending next valid rebalance | paper_trading_setup |  |  |  | n/a | not started | Paper-trading log opened after V5.3g freeze. No historical refill is allowed. Next signal requires post-freeze market data and latest PIT EV visibility check. | monitor only |

## PM Review Rule

PM reviews this log after each new signal and after each forward result update.

If no valid signal packet can be produced within 30 minutes during a scheduled paper-trading update, PM must receive a blocker report with:

- missing data;
- failed source or API;
- affected Agent;
- whether fallback is allowed;
- whether the runner or skill should be disabled, limited, or revised.

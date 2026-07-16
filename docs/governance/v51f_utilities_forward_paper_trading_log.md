# V5.1f Utilities Forward / Paper Trading Log

Date opened: 2026-07-16

Strategy: `utilities_demand_state_v51f`

Sector boundary: electricity-heavy public utility operators

Status: `paper_trading_started`

Not status:

```text
accepted_strategy
live_trading_approved
post_2026_forward_evidence_passed
```

## Purpose

Record future V5.1f signals after the platform-replication and engineering-audit phase.

This log must not be used to rewrite 2021-2026 evidence. It is a forward observation record for model discipline, operational reliability, and PM review.

## Frozen Candidate Rule

Current candidate rule:

```text
warmup -> operating_cash_flow_yield top 10
weak electricity demand -> dividend_yield top 10
mid electricity demand -> operating_cash_flow_yield top 10
strong electricity demand -> low_price_to_book top 10
```

Core constraints:

- Do not tune factor rules based on forward outcomes.
- Do not change rebalance months without PM approval.
- Use point-in-time universe and visible state data only.
- Keep live JoinQuant factor recomputation tests separate from paper-trading evidence.
- If live recomputation fails, record the failure instead of replacing the signal by hand.

## Required Signal Packet

Each paper-trading signal must record:

- signal date;
- factor date;
- electricity-state visible date;
- electricity-state value;
- state bucket;
- selected factor;
- selected securities;
- blocked securities and reasons;
- expected target weights;
- data coverage;
- whether the signal came from local runner, JoinQuant live recompute, or frozen-signal fallback;
- PM decision.

## Entries

| Entry Date | Signal Date | Layer | State | Factor | Selected Holdings | Data Coverage | Execution Status | Notes | PM Decision |
|---|---|---|---|---|---|---:|---|---|---|
| 2026-07-16 | pending next valid rebalance | paper_trading_setup | pending | pending | pending | n/a | not started | Paper-trading log opened. First actionable signal requires latest visible electricity-demand state, PIT utilities universe, factor panel, and live/frozen signal source label. No retrospective refill from 2021-2026 is allowed. | monitor only |
| 2026-07-16 | no forward signal generated | workflow_pm30_review | n/a | n/a | n/a | n/a | no trade | PM 30-minute workflow run prepared live JoinQuant recompute smoke test. This is not a paper-trading signal and does not backfill historical holdings. | continue platform smoke test only |
| 2026-07-16 | 2026-07-16 | paper_trading_signal | weak | dividend_yield | `paper_trading_signals/utilities_demand_state_v51f/2026-07-16/selected_signal.csv` | 117 candidates / 10 selected | paper signal only | Latest visible electricity-demand state: 2026-06 value 3.7%, visible 2026-07-15. Bucket = weak, selected high-dividend branch. This is a forward paper-trading signal, not accepted-strategy advice. | monitor only |

## PM Review Rule

PM reviews this log after each new signal and after each monthly result update.

If no valid signal packet can be produced within 30 minutes during a scheduled paper-trading update, PM must receive a blocker report with:

- missing data;
- failed source or API;
- affected Agent;
- whether fallback is allowed;
- whether the skill or runner should be disabled, limited, or revised.

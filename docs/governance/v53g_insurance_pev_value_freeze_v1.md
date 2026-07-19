# V5.3g Insurance P/EV Value Freeze V1

Date frozen: 2026-07-17

Strategy:

```text
insurance_pev_value_v53g
```

Freeze status:

```text
frozen_formal_strategy_candidate
```

Not status:

```text
accepted_strategy
live_trading_approved
return_tuning_allowed
```

## Frozen Contract

The V5.3g model is frozen as:

```text
Core A-share insurers, quarterly rebalance, select the 3 lowest P/EV names using only PIT-visible embedded value and trade-date market capitalization.
```

Frozen signal:

- factor: `price_to_embedded_value`
- direction: `lower_is_better`
- selection count: `3`
- weighting: equal weight
- rebalance: quarterly
- value-trap guard: disabled
- defensive timing: disabled
- individual stop-loss / take-profit: disabled
- benchmark for engineering comparison: `399809.XSHE`
- dividend policy: cash dividends added after 20% tax

## Frozen Inputs

| Artifact | SHA256 |
| --- | --- |
| `examples/insurance_pev_value_v53g_strategy.json` | `5AF8F2412482186FDB42F238A4AD3F6E0C44E95809932E249F69D5CC21BE42B0` |
| `knowledge/research_agent/references/insurance_ev_nbv_reviewed_2020_2025_core5.csv` | `3766BB07A7A7E8C5825FB3273911C4007A74E98026DA849B24104A506360F6C6` |
| `validation_formal_v53g_insurance_pev_value/insurance_pev_value_v53g/formal_validation_summary.json` | `A6B5A429D3CD7BD45F074CC8D7F88165E7DDC86A3F877532BE7EA2B38DF678A5` |
| `local_daily_backtests_insurance_v53g/insurance_pev_value_v53g/summary.json` | `FB94B412966AA3DE9372CBBA5527C1DD3F0C3B602C98E0CF82E43A11A4DF5B00` |
| `validation_overfit_v53g_insurance/insurance_pev_value_v53g/overfit_audit_summary.json` | `C0601CFD32D18D1A60C437A094B08438B51A47283B3BCB74EA0698358BA46E05` |

## Evidence Snapshot

Formal validation:

- PIT leakage audit: `pass`
- Mean IC: `0.0513`
- Mean RankIC: `0.1095`
- Positive IC ratio: `71.43%`
- Low P/EV top3 cumulative return: `32.14%`
- Equal-weight covered insurance cumulative return: `23.40%`

Engineering smoke test:

- Strategy return: `29.89%`
- Annualized return: `5.51%`
- Benchmark: `399809.XSHE`
- Benchmark return: `-3.02%`
- Excess return: `32.91%`
- Max drawdown: `34.20%`

Overfit audit:

- Blockers: `0`
- Needs review: `3`

## Change Control

Forbidden without a new research cycle:

- changing factor weights;
- adding NBV growth into score;
- adding solvency, ROE, investment yield, dividend, PB or PE into score;
- changing selection count;
- adding stop-loss, take-profit, timing, or defensive overlay;
- changing rebalance frequency;
- using 2021-2026 platform results to tune the model.

Allowed without opening a new strategy:

- platform replication attribution;
- paper-trading signal recording;
- fixing data ingestion bugs that do not change frozen historical signals;
- documenting benchmark, dividend, fee, or execution differences;
- adding future signal rows using the same frozen contract.

## PM Rule

Any future improvement proposal must open a new candidate ID, for example:

```text
insurance_pev_value_v53h
```

V5.3g itself is now read-only except for evidence logs and attribution.

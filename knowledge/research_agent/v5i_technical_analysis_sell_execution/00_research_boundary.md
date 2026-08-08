# V5i Technical Analysis Sell-Execution Research Boundary

Status: research knowledge only
Date: 2026-08-06
Owner: Research Agent A

## Topic And Decision Boundary

V5i studies whether technical features can improve the execution timing or execution-quality assessment of a sell that was already scheduled by an existing V57f, V5f, or V5e process. It does not study whether a stock should be sold, what quantity should be sold, or what stock should be held.

The formal V5 historical backtest range is 2021-05-01 to 2026-05-31. Any work using data before 2021 is independent learning or validation only. It must not be merged with the formal backtest or used to select a rule from the formal backtest.

V5i may use the cleaned 1-minute OHLCV and amount data as an execution-observation source. It may aggregate that data to 5-minute or 15-minute feature bars. It may not use L2, order-book, trade-direction, bid/ask, or fill-quality claims unless those data are separately available and PIT-audited.

## In Scope

- Execution timing and quality of an already-scheduled sell.
- Technical feature definitions that use only bars observed at the decision timestamp.
- The distinction between execution alpha and predictive alpha.
- Evidence grading, data gates, falsifiable hypotheses, and a next-step queue.
- Diagnostics by existing sleeve, liquidity, and event family after a separate Quant specification is approved.

## Out Of Scope

- A standalone technical sell signal, stop loss, profit-lock, or stock-selection rule.
- Changes to V57f/V5f/V5e selection, weights, sell quantity, rebalance date, or target universe.
- New buys, re-entry, cross-sleeve transfer, cash-proxy action, or intraday trading-frequency increase.
- Parameter search, threshold optimization, historical backtest, JoinQuant, QMT, or live approval.
- Claims that a local high, close, final-day VWAP, or final-day volume was knowable before it occurred.

## Five MECE Research Questions

| id | question | judgement to validate later | evidence needed |
| --- | --- | --- | --- |
| Q1 | Execution objective | Can a fixed scheduled sell be compared to a technically conditioned execution time without changing its economic decision? | Existing V5 sell schedule, fixed benchmark time, fill-assumption contract |
| Q2 | Feature validity | Which technical constructs are observable at a timestamp and have a coherent execution mechanism? | Academic and practitioner literature, explicit feature schema, local 1-minute data audit |
| Q3 | Microstructure limits | What can OHLCV and amount establish, and what cannot be inferred without L2 or trade-direction data? | V5h field inventory, market-microstructure references, missing-data register |
| Q4 | Evaluation design | How should a sell-execution hypothesis be judged without future-bar leakage or hidden timing alpha? | PIT protocol, next-bar rule, benchmark-price and cost definitions, pre-2021 versus formal-window separation |
| Q5 | Governance | What evidence would permit a separate limited-engineering test, and what remains blocked? | V57f/V5f/V5e boundary documents, V5h governance, PM approval record |

## Source Search Matrix

| question | narrow search terms | preferred source classes | current local leads | exclusion rule |
| --- | --- | --- | --- | --- |
| Q1 | execution benchmark VWAP implementation shortfall sell order | execution research, academic market microstructure, broker methodology | V5h buy-execution spec, V5c rebalancing cards | Do not infer alpha from a benchmark-only definition |
| Q2 | intraday VWAP reversal volume confirmation RSI technical analysis evidence | peer-reviewed technical-analysis studies, execution texts | V5h 1-minute feature schema and signal-quality report | Do not elevate a chart pattern solely because it is popular |
| Q3 | OHLCV order flow trade sign bid ask limitation | market-microstructure studies, data-vendor documentation | V5h volume/amount data gate | Do not call amount pressure signed order flow |
| Q4 | intraday timing look-ahead bias next bar execution | backtest methodology, V5 PIT governance | V5h governance audit, V5c anti-overfit cards | Do not use final daily high, low, volume, or close in a live feature |
| Q5 | turnover cost sell execution governance profit taking overfit | portfolio-management texts, local governance material | V5c rejected ideas, V5a.2 framework | Do not turn books or blogs into numeric parameters |

## Evidence Policy

Evidence A is a traceable academic or official source, or a local V5 data/governance artifact with a reproducible location. Evidence B is a reputable practitioner or execution reference. Evidence C is a book or practitioner framework. Evidence D is an anecdote or unverified market commentary.

Evidence supports a research hypothesis only. It does not establish an A-share sell edge, set a numeric threshold, or justify accepted/live status.

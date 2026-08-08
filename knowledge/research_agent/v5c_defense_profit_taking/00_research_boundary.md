# V5c Defense / Profit Taking / Rebalancing Overlay Research Boundary

As of 2026-07-25.

## Research Topic

Build a Research Agent knowledge base for portfolio-level defense, profit taking, peak trimming, rebalancing, cash management and drawdown control overlays suitable for V57f-style dividend, low-volatility, cash-flow, multi-sleeve ETF candidates.

## Scope

V5c is an overlay research line. It may study when to lower risk exposure, when to trim sleeve-level peaks, and when to restore target exposure. It must not alter V57f stock selection, core sleeves, sector weights, factor definitions, rebalance calendar or execution timing.

## Out Of Scope

- High-frequency trading.
- Minute-level timing.
- Single-stock short-term stop loss.
- Complex macro forecasting.
- Leverage.
- Options.
- Live trading system design.
- V57f core stock-selection changes.
- New sector expansion.
- Historical threshold tuning on 2021-2026 results.

## MECE Sub-Questions

| id | sub_question | judgement_to_validate | search_keywords | evidence_needed |
|---|---|---|---|---|
| Q1 | Portfolio defense | Whether a portfolio-level risk state can reduce drawdown without destroying dividend/FCF compounding. | portfolio drawdown control; volatility targeting equity strategy; trend following defensive overlay; 红利低波 回撤 控制 | Academic / official / report evidence plus PIT market-state data. |
| Q2 | Profit taking / peak trimming | Whether sleeve-level over-weight trimming is safer than stock-level profit taking. | rebalancing premium; sleeve rebalancing; value strategy profit taking; 高股息 策略 止盈 | Rebalancing theory, fund/ETF practice, local sleeve weight history. |
| Q3 | Rebalancing mechanism | Whether calendar, threshold, volatility or risk-budget rebalancing best fits a low-turnover ETF candidate. | threshold rebalancing; risk budget rebalancing; risk parity rebalancing drawdown | Academic / institutional framework, turnover/cost evidence. |
| Q4 | Cash management | How defensive cash should be governed and restored without creating cash drag. | cash management portfolio drawdown; tactical asset allocation cash | Cash drag studies, local execution logs, exposure restoration rules. |
| Q5 | Dividend/low-vol special risks | How interest rates, dividend traps, crowding, valuation heat and payout sustainability affect defensive overlays. | dividend low volatility risk management; 股息策略 利率上行 风险; 红利策略 拥挤交易 | Reports, index methodology, PIT dividend/valuation/rate data. |
| Q6 | Behavior and discipline | Which profit-taking and stop-loss intuitions are behavioral traps. | behavioral finance disposition effect; loss aversion; market timing mistakes | Books, academic studies, practitioner notes. |
| Q7 | Quant hypothesis conversion | Which ideas can become PIT-safe overlay hypotheses and which must remain qualitative controls. | PIT data requirement; tactical asset allocation drawdown control | Source-date requirements, anti-overfit policy, PM gate rules. |

## Evidence Hierarchy

- A: official materials, fund periodic reports, index rules, verifiable academic papers, PDF-original reports.
- B: institutional report summaries, fund company strategy material, sell-side thematic reports.
- C: books and long-horizon investment frameworks.
- D: blogs, Xueqiu posts, interviews and practitioner anecdotes.

D-level material can only generate hypotheses. It cannot become evidence, thresholds or model parameters.

## Current Source Limitation

The fxbaogao credential is available from the local vault and API search can run. However, V5c broad-query recall is too noisy. Until the API provider confirms advanced filtering or we implement a stricter local pipeline, Research Agent must not use broad keyword results directly as knowledge evidence.

Mandatory policy:

1. Stage 1: narrow keywords plus local title filter, excluding daily/weekly/monthly/company-result noise.
2. Stage 2: fetch paragraph or PDF, then locally rerank and keep only thematic, financial-engineering, strategy, fund-research or asset-allocation materials.
3. Only PDF-original-checked reports can become A/B evidence cards.

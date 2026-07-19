# V5.3c Insurance Diagnostic Workflow Table

Date: 2026-07-17

Status:

```text
failure_attribution_only_no_return_tuning
```

Not status:

```text
accepted_strategy
paper_trading_ready
joinquant_code_ready
platform_replication_approved
```

## Purpose

V5.3c Insurance Low-PB-only passed research PIT validation, but it is not deployable. The next task is diagnosis, not return improvement.

This workflow answers whether insurance can remain a simple low-PB value model, or whether it requires an insurance-specific data model with EV / NBV, solvency, liability-side pressure, interest-rate state, and equity-market state.

## Diagnostic Workflow Table

| Step | Layer | Owner Agent | Goal | Required Inputs | Core Actions | Required Outputs | Pass Standard | Fail / Return Rule |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | PM diagnostic gate | Project Manager | Freeze V5.3c as diagnosis-only | V5.3c result, PM decision, status registry | Confirm no weight tuning, no selection-count tuning, no JoinQuant code | Diagnostic gate record | Status remains `failure_attribution_only_no_return_tuning` | If anyone proposes return tuning, block and return to Research |
| 2 | Research knowledge repair | Research Agent | Confirm what insurance-specific knowledge is missing | Insurance knowledge packet, reports, annual reports, regulatory materials | Review EV / NBV, embedded value, new business value, solvency, liability duration, investment yield, surrender pressure, accounting changes | Insurance knowledge repair memo | Each missing variable has financial meaning and candidate source | If knowledge is too shallow, continue Research before Quant |
| 3 | Data source inventory | Research Agent + Engineering Agent | Decide which insurance-specific fields are realistically available | JQData/DataJQ, Tushare, annual reports, insurer disclosures, Wind/Choice/third-party notes if available | List source, history, visible date, frequency, coverage, manual workload | Insurance data availability matrix | Fields are classified as usable / manual / unavailable / deferred | If core fields are unavailable, do not rebuild model yet |
| 4 | PIT universe audit | Quant Validation Agent | Check whether the 8-code insurance universe is stable and historically valid | Listing dates, industry labels, company transformations, ST/delist info | Verify insurer membership at each rebalance date and exclude non-core or unavailable names by PIT rule | PIT insurance universe audit | No survivor-only contamination; universe size risk is explicit | If historical membership is weak, strategy remains diagnostic only |
| 5 | Baseline restatement | Quant Validation Agent | Restate V5.3c evidence without changing model | V5.3c panel, formal validation output | Reconfirm equal-weight, high-dividend reference, low-PB-only, V5.3b composite comparison | Baseline restatement table | Evidence matches frozen V5.3c; no new tuned case appears | If results drift, investigate data/version mismatch |
| 6 | Failure-year attribution | Quant Validation Agent | Explain 2021, 2022, 2026 before any model change | Quarterly returns, daily returns, rebalance signals, holdings, benchmark, market states | Attribute by selected stocks, universe returns, PB rank, equity market, 10Y rate, drawdown timing | Failure-year attribution packet | Losses are explained by ex-ante observable states or known model limits | If explanation is only after-the-fact, do not promote |
| 7 | Interest-rate state diagnosis | Research Agent + Quant Validation Agent | Test whether real 10Y yield state explains low-PB success/failure | 10Y treasury yield, CPI/inflation proxy, real-rate panel | Bucket periods by rate level/change; compare factor IC and returns by state | Rate-state diagnostic report | Rate state improves explanation without tuning trading rules | If state is unstable, keep it as risk note only |
| 8 | Equity-market state diagnosis | Quant Validation Agent | Test whether broad equity beta dominates insurance returns | CSI 300 / financial index / insurance benchmark, daily and quarterly returns | Compare factor returns under equity bull/bear, volatility, drawdown states | Equity-state diagnostic report | State explains failures such as 2021/2026 or rules out equity-only explanation | If insurance is just equity beta, research thesis weakens |
| 9 | EV / NBV availability decision | Research Agent + Engineering Agent | Decide whether EV / NBV is required for Test-2 | Annual reports, insurer disclosures, research reports, possible paid sources | Check embedded value, NBV, PEV, NBV growth, visible dates, coverage | EV/NBV source decision | Either field is available PIT, or explicitly deferred with reason | If EV/NBV is required but unavailable, insurance pauses as data-blocked |
| 10 | Solvency and liability-side decision | Research Agent + Quant Validation Agent | Decide whether solvency / liability pressure must enter the model | Solvency reports, annual reports, regulatory disclosures | Review core solvency ratio, comprehensive solvency ratio, surrender rate, reserve pressure, investment yield | Solvency/liability data decision | Variables are sourced or rejected with clear reason | If unavailable and economically required, insurance remains diagnostic |
| 11 | Concentration and small-universe audit | Quant Validation Agent | Determine whether V5.3c is too concentrated to trust | Selection-count robustness, holdings, daily returns | Compare top2/top3/top4/top5, turnover, name contribution, single-name drawdown | Small-universe robustness report | Edge is not driven by one or two names only | If concentrated edge dominates, do not proceed to platform replication |
| 12 | Local daily simulation review | Engineering Agent | Check whether execution changes the research conclusion | Local daily summary, holdings, trades, dividends, benchmark | Review daily NAV, turnover, cash, benchmark, dividend tax, price source, rebalance timing | Engineering daily simulation diagnostic | Daily result is mechanically consistent with frozen V5.3c | If mechanics alter thesis, return to PM and Quant |
| 13 | Data-model PM decision | Project Manager | Decide the next insurance branch | Steps 2-12 outputs | Classify insurance as simple-model-continues, needs-insurance-specific-model, data-blocked, or failed-candidate | PM data-model decision | Decision is evidence-driven and not based only on return | If unresolved, keep diagnosis open and block JoinQuant code |
| 14 | Optional Test-2 design | Research Agent | Only if PM approves a new data model | PM decision, available PIT fields | Propose Insurance EV/Rate/Solvency V5.3d hypotheses | Test-2 research proposal | New hypothesis uses insurance-specific logic and PIT-available fields | Quant starts only after PM approves Test-2 |

## Required Diagnostic Artifacts

| Artifact | Owner | Required Before |
| --- | --- | --- |
| Insurance data availability matrix | Research + Engineering | Any V5.3d proposal |
| 2021 / 2022 / 2026 failure attribution packet | Quant | PM data-model decision |
| Rate-state diagnostic report | Quant | Model redesign |
| Equity-state diagnostic report | Quant | Model redesign |
| EV / NBV source decision | Research + Engineering | Model redesign |
| Solvency / liability data decision | Research + Quant | Model redesign |
| Small-universe robustness report | Quant | Platform replication |
| Local daily simulation diagnostic | Engineering | Platform replication approval |
| PM insurance data-model decision | Project Manager | Any new insurance test |

## Forbidden During Diagnosis

- Do not tune selection count to maximize 2021-2026 return.
- Do not tune factor weights after seeing failure years.
- Do not add defensive timing only because it improves the backtest.
- Do not generate JoinQuant strategy code before PM approves platform replication.
- Do not call V5.3c `accepted_strategy`.
- Do not treat research reports as validation evidence; reports are only hypothesis sources.

## PM Decision States

After the workflow, Project Manager must assign one of:

| Decision State | Meaning | Next Action |
| --- | --- | --- |
| `simple_low_pb_model_continues_diagnostic` | Low PB remains interesting but not deployable | Continue paperless diagnosis |
| `needs_insurance_specific_data_model` | EV/NBV, solvency, rate/equity state are required | Research Agent designs V5.3d |
| `blocked_by_insurance_data_availability` | Required fields are unavailable or not PIT | Pause strategy, keep data work only |
| `strategy_candidate_failed` | Failure modes are not explainable or edge is unstable | Archive insurance candidate |
| `engineering_platform_gate_ready` | Rare case: diagnosis resolves risks and daily sim is stable | PM may approve platform replication |

## Current PM Bias

Current evidence suggests:

```text
needs_insurance_specific_data_model
```

But this is not final until failure-year attribution and data availability are complete.

## Next Gate

```text
insurance_data_model_decision
```

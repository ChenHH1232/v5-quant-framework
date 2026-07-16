# V5.1f Utilities / Electricity Golden Workflow Table

Date: 2026-07-17

Status:

```text
golden_template_productization_in_progress
```

Not status:

```text
accepted_strategy
live_trading_approved
```

## Purpose

V5.1f Utilities / Electricity is the current V5 golden workflow template. Its purpose is to define a repeatable sector research and validation process, not to declare the strategy accepted.

Every future sector test should be compared against this table before entering platform replication or paper trading.

## Golden Workflow Table

| Step | Experiment Layer | Owner Agent | Goal | Required Inputs | Core Actions | Required Outputs | Pass Standard | Fail / Return Rule |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | data_availability_gate | Project Manager | Decide whether the sector is allowed to enter research validation | Sector name, candidate universe, known data sources | Check whether public / licensed sources can support PIT universe, PIT financials, dividends, benchmark, external state data, and failure-year diagnosis | Data availability gate record | Data fields are available, auditable, and not dependent on future-known classifications | If key data is missing, stop modeling and return to Research / Data Engineering |
| 2 | research_knowledge_gate | Research Agent | Learn sector economics before proposing factors | Industry reports, annual reports, regulatory documents, high-quality articles, prior knowledge base | Summarize business model, profit drivers, valuation logic, risk variables, and external state variables | Sector knowledge packet, research memo, citation index | The sector logic is financially explainable and cites sources | If knowledge is shallow, continue research; Quant Agent must not start validation |
| 3 | research_hypothesis_design | Research Agent | Convert sector knowledge into testable hypotheses | Research memo, factor clues, risk variables | Define value, quality, dividend, cash-flow, debt, and external-state hypotheses | Hypothesis list, factor specification, expected direction, rejection criteria | Each hypothesis has economic reasoning and can be tested with PIT data | If a hypothesis cannot be tested, mark as deferred or data-blocked |
| 4 | pit_universe_build | Quant Validation Agent | Build investable historical universe | Securities master, listing dates, delisting dates, industry classifications, manual exclusions | Construct point-in-time universe and coverage report | PIT universe file, universe audit report | No survivorship-only universe; coverage is high on rebalance dates | If PIT universe is weak, return to PM and Data Engineering |
| 5 | pit_panel_build | Quant Validation Agent | Build factor and external-state panel | PIT financial data, market data, dividends, benchmark, external state data | Align visible dates, factor dates, rebalance dates, and state variables | PIT factor panel, external state panel, coverage report | No look-ahead fields; missingness is documented | If visible dates are uncertain, downgrade factor or block formal validation |
| 6 | formal_validation | Quant Validation Agent | Test whether hypotheses have statistical support | PIT universe, PIT factor panel, returns, benchmark, state panel | Run baseline, IC, RankIC, rolling validation, ablation, robustness, state bucket tests | Formal validation packet | Evidence is stable enough to justify an engineering smoke test | If evidence fails, return to Research Agent; no weight tuning after seeing returns |
| 7 | pm_formal_candidate_decision | Project Manager | Decide whether research evidence can enter engineering | Research memo, validation packet, failure analysis | Classify result as formal_strategy_candidate, needs_more_research, or failed_candidate | PM decision record | Statistical evidence and financial explanation are both acceptable | If only backtest return is strong, reject or hold for more validation |
| 8 | engineering_smoke_test | Engineering Agent | Confirm implementation feasibility without platform overfitting | Frozen strategy spec, PIT panel, validation outputs | Run local execution checks, order constraints, dividend policy, benchmark policy, lot-size rules, logs | Engineering smoke-test report | Strategy can be executed reproducibly and logs are auditable | If implementation changes research logic, return to PM |
| 9 | local_daily_simulation | Engineering Agent | Simulate daily portfolio mechanics locally | Frozen strategy spec, real daily prices, dividends, benchmark, rebalance signals | Generate daily NAV, holdings, cash, orders, trades, dividends, and benchmark returns | Local simulation packet | Daily accounting is reproducible and matches declared assumptions | If data gaps or accounting mismatch exist, mark needs_review |
| 10 | overfit_audit | Engineering Agent + Quant Validation Agent | Check whether results are fragile or contaminated | Daily returns, rebalance signals, factor panel, config | Test survivorship, look-ahead, sample contamination, random date windows, parameter perturbations, execution-time shifts | Overfit audit report | No major leak or unacceptable parameter fragility | If fragile, return to Research / Quant; do not proceed to platform replication |
| 11 | platform_replication_gate | Project Manager | Decide whether to spend platform-testing effort | Local simulation packet, overfit audit, candidate freeze record | Confirm the strategy is frozen and the platform objective is replication, not tuning | Platform replication approval record | Clear expected metrics, benchmark, rebalance logic, and attribution plan | If unfrozen or still being tuned, block platform test |
| 12 | platform_replication | Engineering Agent | Compare local model with JoinQuant / external platform | Frozen platform code, exported platform result, trades, positions, logs | Run local-vs-platform attribution on returns, holdings, trades, cash, dividends, benchmark | Platform replication packet | Differences are explained by known execution/data rules | If unexplained gap remains, mark platform_replication_needs_attribution |
| 13 | paper_trading_setup | Project Manager + Engineering Agent | Start forward record without using future data | Frozen candidate, current PIT data, paper log template | Record next live signal, selected stocks, factor values, guard state, expected risks | Paper-trading log entry | Signal is generated before observing future returns and cannot be edited afterward | If signal was generated late or revised, mark invalid |
| 14 | paper_trading_review | Project Manager + Quant Validation Agent | Accumulate forward evidence | Paper signals, realized returns, market state, attribution | Review signal quality, risk exposure, turnover, failure modes, and thesis drift | Paper-trading review report | Forward evidence is consistent enough for later acceptance review | If thesis fails, archive or return to Research |

## Agent Handoff Rules

| From | To | Handoff Artifact | PM Check |
| --- | --- | --- | --- |
| Research Agent | Quant Validation Agent | Research memo, hypothesis list, factor specification, citation index | Hypotheses are testable and source-backed |
| Quant Validation Agent | Project Manager | Formal validation packet, factor ranking, failure-year analysis | Evidence is not only return-based |
| Project Manager | Engineering Agent | Frozen strategy spec, PM candidate decision | Research logic is frozen before engineering starts |
| Engineering Agent | Project Manager | Local daily simulation, overfit audit, platform attribution | Implementation matches the frozen spec |
| Project Manager | Paper Trading Log | Frozen paper signal | No use of future returns or revised factor values |

## Required Output Folder Convention

```text
docs/governance/
docs/engineering/
knowledge/research_agent/
reports/
database/processed/
examples/
```

Each sector should preserve a clear chain:

```text
knowledge packet -> hypothesis -> PIT panel -> validation packet -> PM decision -> engineering packet -> platform packet -> paper log
```

## PM Stop Rules

The Project Manager must stop the workflow when any of these occur:

- Research Agent has no credible sector knowledge source.
- Quant Agent uses non-PIT data or future-known classifications.
- Formal validation and actual scoring logic diverge.
- Engineering modifies factor theory to improve returns.
- Platform replication is used for tuning instead of attribution.
- Paper-trading signals are revised after the fact.
- A strategy is described as accepted before forward evidence exists.

## V5.1f Specific Baseline

V5.1f should remain the reference template for:

- sector knowledge before modeling;
- external state awareness;
- formal validation before platform testing;
- local daily simulation before JoinQuant code;
- overfit audit before paper trading;
- immutable paper signal records;
- machine-readable status tracking.

The strategy remains:

```text
formal_strategy_candidate + golden_workflow_template
```

It is not:

```text
accepted_strategy
```

# Bank Quant V5 Manifesto

## From Strategy Development to Research System

Bank Quant V5 is not a new trading strategy.

It is a research and development framework for systematic quantitative investing.

The objective of V5 is no longer to discover a single profitable strategy, but to establish a complete, reproducible, and explainable research pipeline that transforms investment hypotheses into deployable quantitative strategies.

Every component of the framework should be independently verifiable, extensible, and maintainable.

## Research Philosophy

Quantitative investing is often misunderstood as a purely statistical optimization problem.

V5 takes a different view.

Statistical methods identify relationships. Financial theory explains why those relationships exist. Artificial Intelligence accelerates the process of discovering, validating, and implementing them.

A successful quantitative strategy should not be viewed as the output of a single algorithm, but as the result of a complete research methodology integrating finance, statistics, software engineering, and AI.

## Core Question

V5 should answer three questions:

- What works?
- Why does it work?
- How can we systematically discover the next strategy that works?

The first question identifies effective strategies. The second explains those strategies through finance and statistics. The third turns the research process itself into a reusable system.

## Project Evolution

- V1: Can fundamental factors outperform?
- V2: Are these factors statistically significant?
- V3: Can they become a deployable strategy?
- V4: Is the strategy robust under rolling validation?
- V5: Can the entire research process itself become systematic?

## Core Principles

### Research Before Strategy

Research is more valuable than a single strategy.

Strategies may become obsolete. A sound research methodology should continue to generate new strategies.

### Explainability Before Performance

Higher returns alone are not considered progress.

Every accepted factor should have statistical evidence, financial interpretation, and implementation feasibility.

### Evidence Before Optimization

Optimization without evidence leads to overfitting.

Every improvement must be supported by experiments rather than historical performance alone.

### Reproducibility Before Convenience

Every conclusion should be reproducible from source data, experiment configuration, code version, and generated reports.

Nothing should depend on undocumented manual operations.

### AI Augments Researchers

AI accelerates engineering and experimentation, but it does not replace research judgment.

Human researchers remain responsible for defining investment hypotheses, interpreting financial meaning, and making final research decisions.

## Agent Architecture

V5 should be organized around four core agents. This keeps the system close to a real quantitative research team and avoids unnecessary agent complexity.

### Project Manager Agent

Role: orchestrator.

Mission: plan, coordinate, and manage the V5 project.

The Project Manager Agent reads the V5 Manifesto, maintains the roadmap, breaks development into stages, assigns tasks to other agents, summarizes research results, manages experiment flow, updates TODOs, and records final decisions.

It produces task lists, development plans, decision logs, and sprint reports.

It should not directly design factors, write strategy code, or perform statistical validation.

Core question: what should happen next?

### Research Agent

Role: financial researcher.

Mission: convert investment ideas into testable research hypotheses.

The Research Agent proposes research directions, designs factors and strategy frameworks, explains financial logic, reviews literature, judges economic meaning, and creates experiment plans.

It produces research proposals, hypotheses, experiment designs, and factor specifications.

It should not write code, tune parameters, or accept a strategy based on returns alone.

Core question: why is this worth researching?

### Quant Validation Agent

Role: statistical analyst.

Mission: validate research hypotheses with statistical evidence.

The Quant Validation Agent performs IC analysis, RankIC, Fama-MacBeth regression, correlation analysis, feature selection, rolling validation, walk-forward testing, robustness testing, and overfitting checks.

It produces validation reports, statistical evidence, factor rankings, and robustness reports.

It should not create financial theory, modify strategy ideas, or write trading logic.

Core question: is there evidence to support this?

### Engineering Agent

Role: quantitative engineer.

Mission: turn validated research into reliable running systems.

The Engineering Agent implements Python modules, JoinQuant strategies, strategy engines, portfolio construction, risk control, unit tests, integration tests, audits, and documentation.

It produces strategy code, backtests, tests, audit reports, and technical documentation.

It should not invent investment views, change research conclusions, or adjust theory to fit historical performance.

Core question: how can this be implemented reliably?

## Shared Agent Rule

Every agent must obey the same system rule:

> Every decision must be evidence-driven, financially explainable, statistically validated, reproducible and maintainable. Historical performance alone is never sufficient evidence for accepting a strategy.

In Chinese:

> 所有决策必须基于证据、具有金融解释、经过统计验证、能够复现，并具备长期维护性。任何策略都不能仅因为历史收益较高而被接受。

## Long-Term Vision

## Dynamic Skill Lifecycle

V5 skills are not static documentation.

They are living operating rules. When data sources, APIs, permissions, research methods, or implementation paths change, the skills must be updated as part of the research process.

If a skill becomes unavailable, unsafe, or no longer reproducible, it should be marked as limited, deprecated, or disabled for new work. The reason and replacement route must be recorded.

If a task succeeds without an existing skill, and the workflow is repeatable, V5 should summarize the experience and turn it into a new candidate skill. This is how the framework learns from practice.

The Project Manager Agent is responsible for monitoring this lifecycle and using the Skill Lifecycle Manager when a skill must be changed.

## Statistical Validation Discipline

V5 inherits the statistical discipline developed in V4.

The central rule is simple: no factor or strategy is accepted because one backtest looks good.

Validation must move through separated evidence layers: factor evidence, annual refresh behavior, walk-forward performance, robustness perturbation, leave-one-out checks, common-sample candidate comparison, and a final freeze-point decision.

Every validation must preserve train, test, and review separation. Preprocessing, weights, factor selection, and parameter choices must be refit inside each fold using only information available at that time.

Candidate comparisons should use common samples whenever possible. If a branch is coherent but weaker than the baseline, it should be archived as evidence rather than tuned indefinitely.

This discipline is captured in the `statistical-validation-protocol` skill.

## V4 Method Inheritance

V5 preserves the reusable research methods that V4 discovered while building, testing, rejecting, and freezing bank-sector strategies. These include candidate governance, allocation versus selection separation, momentum research, mean-reversion archive discipline, defensive overlays, state routing, strategy attribution, execution stress testing, and final archive freeze packets.

The purpose is not to copy V4's final strategy mechanically. The purpose is to convert V4's hard-earned research process into reusable operating skills for future hypotheses.

## Platform Export Discipline

Platform code is an implementation artifact, not a research workspace.

When V5 exports a strategy to JoinQuant, the strategy contract must already be frozen. The export step may adapt APIs, scheduling, logging, order placement, and platform-specific mechanics, but it must not change factor definitions, thresholds, weights, rebalance rules, or research conclusions.

JoinQuant backtest results should not be accepted until execution consistency checks confirm that signal dates, factor values, ranks, selected securities, target weights, and risk states match the approved V5 logic.

This discipline is captured in the `joinquant-strategy-exporter` and `execution-consistency` skills.

The current implementation focuses on the Chinese banking sector.

The objective is not to build only the best banking strategy. The objective is to develop a reusable quantitative research framework that can eventually support multiple industries, multiple asset classes, and different investment methodologies.

The banking strategy is the first application of this framework.

## Success Criteria

V5 is successful if it can consistently transform an investment idea into a reproducible quantitative strategy through a standardized research pipeline.

Success is not measured solely by annualized return or Sharpe ratio. It is evaluated by whether the framework can:

- Preserve research evidence.
- Automate repetitive research tasks.
- Reduce implementation errors.
- Improve reproducibility.
- Accelerate future strategy development.

## Motto

A strategy can generate returns.

A research framework can generate strategies.

Bank Quant V5 is designed to build the latter.

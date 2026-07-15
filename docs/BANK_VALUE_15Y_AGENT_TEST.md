# Bank Value 15Y Agent Test

## Objective

Generate a bank-sector quantitative strategy based on value-investing principles and use it to test whether V5 agents and skills can work together.

This is a strategy research package, not a completed performance claim. The current V5 engine validates the strategy contract and audit rules; it does not yet compute real 15-year factor returns.

## Requested Strategy

- Domain: A-share listed banks.
- Data window: 2011-07-14 to 2026-07-14.
- Philosophy: value investing for banks.
- Strategy id: `bank_value_15y`.
- Spec file: `examples/bank_value_15y_strategy.json`.

## Project Manager Agent

Question: what should happen next?

Skill chain used:

- `v5-controller`
- `research-agent`
- `factor-research`
- `data-source-router`
- `bank-indicator-replacement-collector`
- `annual-report-bank-indicator-collector`
- `statistical-validation-protocol`
- `strategy-spec`
- `data-leakage-audit`

Decision:

Create a formal research candidate and keep its status as `pending_validation` until real data collection, factor computation, rolling validation, and execution stress testing are completed.

## Research Agent

Question: why is this worth researching?

Research question:

Can a bank-specific value strategy outperform by buying banks that are cheap relative to book value and dividends while avoiding value traps through asset quality, provision coverage, capital adequacy, and profitability filters?

Hypothesis:

Banks with low price-to-book ratios and high dividend yields should offer a value premium only when their balance-sheet quality remains acceptable. In banking, low valuation without asset-quality support can indicate credit deterioration rather than mispricing.

Financial rationale:

- P/B is central for banks because book equity is closer to the operating balance sheet than for many non-financial firms.
- Dividend yield captures shareholder return discipline and capital distribution.
- ROE captures profitability of equity capital.
- Non-performing loan ratio and provision coverage control for credit-cycle value traps.
- Core tier 1 capital adequacy controls for solvency and regulatory resilience.

Candidate factors:

- `low_price_to_book`: lower is better.
- `dividend_yield`: higher is better.
- `return_on_equity_ttm`: higher is better.
- `non_performing_loan_ratio`: lower is better.
- `provision_coverage_ratio`: higher is better.
- `core_tier_1_capital_adequacy_ratio`: higher is better.

Experiment design:

- Use point-in-time A-share bank universe.
- Rebalance quarterly after financial disclosure visibility checks.
- Rank banks by weighted composite score.
- Apply value-trap guard before final selection.
- Select up to 8 banks.
- Equal weight selected names with 15% max single-name weight.
- Hold residual cash when fewer than 8 banks pass filters.

Rejection criteria:

- Factor IC is unstable or negative after proper time separation.
- Low-PB winners are concentrated in deteriorating credit-quality names.
- Return advantage disappears after asset-quality filters are applied.
- Rolling folds show one-period concentration rather than durable behavior.
- Execution stress erases the candidate's edge.

## Data Source Router

Dataset kind:

- Daily market data.
- Valuation data.
- Standard financial statements.
- Bank-specific balance-sheet quality and capital indicators.

Preferred source:

- JoinQuant for A-share daily market, valuation, industry membership, and standard statements.

Fallback source:

- Tushare for supported market or financial fields when JoinQuant coverage is insufficient.
- Annual reports for bank-specific indicators unavailable through ordinary APIs.

Blocked or limited item:

- Direct JoinQuant `bank_indicator` must not be used for new V5 workflows.

Next skills:

- `bank-indicator-replacement-collector`
- `annual-report-bank-indicator-collector`
- `financial-statement-standardizer`

Credential note:

Credentials may be stored in the user's secure vault, but this test package does not expose or persist credentials. A future collection run should load credentials through the approved local secret mechanism and write only source labels and collection status into artifacts.

## Bank Indicator Replacement Plan

| Field | Replacement class | Proposed route |
| --- | --- | --- |
| non-performing loan ratio | annual-report extraction or reconstructed indicator | Extract from bank annual/interim reports and align by announcement date. |
| provision coverage ratio | annual-report extraction or reconstructed indicator | Extract from reports; do not infer without explicit source. |
| core tier 1 capital adequacy ratio | annual-report extraction | Extract from capital adequacy disclosure tables. |
| dividend yield | direct/reconstructed | Use announced dividends and lagged market price. |
| ROE | ordinary statement/indicator | Use financial statements visible by announcement date. |
| price-to-book | valuation | Use lagged market cap and latest visible net assets. |

Every bank-specific field must keep `source_type`, `source_table`, `source_field`, `mapping_method`, `confidence`, `review_status`, and `is_original_bank_indicator`.

## Quant Validation Agent

Question: is there evidence to support this?

Required validation stack:

1. Factor coverage and missingness by rebalance date.
2. IC and RankIC for every factor.
3. Positive IC ratio.
4. Grouped return spread from top value-quality group versus bottom group.
5. Rolling validation with `5y train + 2y test + 1y review`.
6. Leave-one-out tests for each resident factor.
7. Robustness tests on factor weights, selection count, rebalance frequency, and value-trap guard.
8. Common-sample comparison versus:
   - equal-weight listed bank basket;
   - low-PB-only strategy;
   - V4 fundamental baseline where comparable.

Current decision:

`pending_validation`. The strategy is financially coherent and structurally auditable, but not accepted until real data validation is complete.

## Engineering Agent

Question: how can this be implemented reliably?

Implementation contract:

- The JSON spec is the source of truth.
- Platform code must not change factor definitions, weights, schedules, or risk rules.
- Financial data must be aligned by announcement date.
- Cross-sectional normalization must occur only at each rebalance date.
- Suspensions and price limits must be handled.
- Execution stress scenarios must be run before acceptance.

Audit expectation:

The local scaffold audit should pass because the strategy uses point-in-time universe construction, announcement-date financial visibility, rebalance-date normalization, rolling validation, and nonzero execution costs.

## Final Status

Status: `pending_validation`

Reason:

The agent and skill workflow can produce a coherent strategy contract and research plan. However, V5 must not claim a 15-year validated strategy until data collection, factor computation, rolling validation, and execution stress tests are actually run.

Next action:

Build the data collection runner for this spec, then run the Quant Validation Agent workflow on the collected 15-year bank panel.

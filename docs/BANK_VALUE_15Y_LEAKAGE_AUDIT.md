# Bank Value 15Y Leakage Audit

Date: 2026-07-14

Strategy: `bank_value_15y`

## Audit Scope

This audit checks whether the current Bank Value 15Y candidate can be used for a near-5-year JoinQuant backtest without sample-out contamination or future leakage.

Inputs reviewed:

- `examples/bank_value_15y_strategy.json`
- `validation/bank_value_15y/validation_summary.json`
- V5 data-leakage audit rules
- V5 JoinQuant export rules

## Verdict

Status: `platform_confirmation_only`

The strategy specification itself passes the current V5 structural audit, but the near-5-year JoinQuant backtest should not be treated as a clean untouched out-of-sample acceptance test.

Reason:

- The local V5 validation already included dates from 2021 to 2026.
- The user and agents have already seen factor evidence and a portfolio path covering the same recent period.
- Any decision made after seeing that evidence can contaminate the near-5-year window if it changes factors, weights, filters, schedule, or risk rules.

Therefore, the near-5-year JoinQuant run is useful as an execution confirmation, not as final clean OOS proof.

## Blockers

None for generating a JoinQuant test file, if the code is used as a frozen execution confirmation.

## Warnings

### 1. Near-5-Year Window Is No Longer Pristine OOS

The 2021-2026 segment has already appeared in local V5 validation artifacts.

Allowed use:

- confirm platform execution;
- compare signal dates, selected stocks, factor values, and weights;
- detect local-versus-JoinQuant mismatch.

Not allowed:

- tune weights after seeing the JoinQuant result;
- drop weak factors because the near-5-year result looks better;
- claim the near-5-year result is a fresh OOS acceptance test.

### 2. V4 Raw Migration Price Adjustment Is Not Fully Confirmed

The local validation used V4 raw daily price files. Their adjustment policy must be confirmed before accepting long-window return statistics.

The JoinQuant run should use its platform price settings consistently and should be treated as the more execution-faithful result.

### 3. Dividend Yield Is Not Yet a Real Tested Factor

In the V4 raw migration panel, `dividend_yield` was set to zero because no dedicated dividend source had been connected.

The JoinQuant export keeps the factor slot but will skip it unless a reliable dividend source is added.

### 4. Bank-Specific Indicators Must Not Use Direct `bank_indicator`

JoinQuant `bank_indicator` is unavailable for new V5 workflows.

The JoinQuant export must use:

- frozen manual annual-report data;
- reconstructed ratios;
- or an approved external source loaded into the code before backtest.

The generated platform file uses a manual table hook and does not call direct `bank_indicator`.

### 5. Universe Construction Is Approximate

The export uses a fixed bank-stock candidate list plus listing, ST, suspension, and tradability filters.

This is safer than using today's active holdings blindly, but it is not a perfect historical point-in-time industry membership reconstruction.

## Clean Use Protocol For JoinQuant

Before running the near-5-year backtest:

1. Do not change factor weights.
2. Do not change selection count.
3. Do not change rebalance months.
4. Do not add or remove factors based on the near-5-year result.
5. Fill the manual bank-indicator table only from annual reports or a frozen pre-run data file.
6. Record the first JoinQuant result as execution confirmation.
7. Compare selected stocks and weights against local signals where possible.

## Current Fixed Contract

- Factors:
  - low price-to-book;
  - dividend yield, currently skipped unless source is available;
  - ROE;
  - non-performing loan ratio;
  - provision coverage ratio;
  - core tier 1 capital adequacy ratio.
- Selection count: 8.
- Max position weight: 15%.
- Rebalance: quarterly.
- Execution: skip untradeable, ST, suspended, and limit-blocked names.
- Risk overlay: reduce exposure by 50% when the bank ETF proxy is below its 12-month moving average.

## Final Decision

Use the generated JoinQuant code for near-5-year platform confirmation.

Do not use the near-5-year result as final clean OOS acceptance unless no research or parameter decision is changed after this audit and the result is clearly labeled as previously observed-period confirmation.

## Engineering Correction Log

Correction owner: Engineering Agent.

Issue:

- JoinQuant selected stocks correctly, but no orders were placed.
- Log message: `name 'order_target_percent' is not defined`.
- This was a platform adapter issue, not a research, factor, or validation issue.

Fix:

- Replace `order_target_percent(stock, target_weight)` with `order_target_value(stock, context.portfolio.total_value * target_weight)`.
- Keep selected stocks, factor weights, rebalance schedule, exposure rule, and research logic unchanged.
- Add order-target logging so platform execution can be confirmed from JoinQuant logs.

Expected confirmation log:

- `order target <code> value=<amount> weight=<target_weight>`

Responsible skills:

- `engineering-agent`
- `joinquant-strategy-exporter`
- `execution-consistency`

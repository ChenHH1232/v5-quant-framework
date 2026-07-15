# Bank Value 15Y Process Review

Date: 2026-07-15

## Scope

This review covers the Bank Value 15Y workflow across research design, data collection, validation, local backtesting, JoinQuant comparison, defensive overlay testing, and knowledge capture.

## Findings

### 1. Near-5-Year Window Was Used For Too Many Purposes

Severity: High

The 2021-05 to 2026-05 window was used for local validation, JoinQuant execution confirmation, data debugging, benchmark alignment, dividend treatment, and defensive overlay research. This makes the window unsuitable as a clean out-of-sample acceptance test.

Impact:

- Any rule added after seeing this window, including the defensive overlay implementation, is contaminated for acceptance purposes.
- The window remains useful for platform consistency checks, but not for final strategy approval.

Improvement:

- Label this window as `platform_confirmation_only`.
- Create a separate acceptance protocol:
  - historical development window;
  - frozen validation window;
  - future paper-trading window.
- Do not change factors, weights, selection count, or risk overlays based on the platform-confirmation window.

### 2. Research Validation Is Still Too Thin For Strategy Acceptance

Severity: High

The current validation runner computes IC, RankIC, grouped spreads, and simple rolling summaries, but it does not yet fully implement the stated validation stack: walk-forward train/test separation, leave-one-factor-out, weight robustness, common-sample baselines, and statistical confidence reporting.

Impact:

- The strategy is financially coherent but not yet statistically accepted.
- Some weak factors may remain in the composite because no formal ablation decision has been completed.

Evidence:

- `core_tier_1_capital_adequacy_ratio` showed weak evidence in the current validation summary.
- `provision_coverage_ratio` had low top-minus-bottom spread in the current validation summary.

Improvement:

- Add formal validation reports for:
  - leave-one-factor-out;
  - low-PB-only baseline;
  - equal-weight bank basket baseline;
  - V4 comparable baseline;
  - weight perturbation robustness;
  - rolling fold stability.
- Require a Project Manager decision before removing or reweighting factors.

### 3. Data Lineage Was Fixed During The Test, But Earlier Results Became Obsolete

Severity: High

The workflow initially used V4 adjusted prices for execution-like testing, which caused large divergence from JoinQuant. Later, JoinQuant `fq=None` stock prices and `fq=pre` benchmark prices were collected and used. This corrected the execution comparison, but all earlier local execution results are obsolete for platform comparison.

Impact:

- Old results such as V4 adjusted local daily returns should not be compared against JoinQuant.
- Reports must clearly distinguish research adjusted-return panels from execution real-price panels.

Improvement:

- Split datasets by purpose:
  - `research_panel`: adjusted total-return or factor validation panel;
  - `execution_panel`: raw stock open/close, cash dividends, benchmark display series;
  - `platform_confirmation`: JoinQuant-aligned local daily simulation.
- Add manifest fields for `intended_use`.

### 4. Defensive Overlay Was Added After Seeing Platform Results

Severity: Medium-High

The MA252 defensive overlay is economically reasonable and reduced drawdown, but it was implemented after observing platform and local results. It should be treated as an improvement hypothesis, not as accepted out-of-sample evidence.

Impact:

- The defensive overlay can be used for risk-control experiments.
- It should not be presented as already validated alpha or clean OOS improvement.

Improvement:

- Mark the overlay status as `risk_control_candidate`.
- Freeze the MA252 rule before the next untouched/paper-trading window.
- Compare cash versus short-duration bond fund as defensive assets in a future test.
- Add turnover and tax impact diagnostics around MA threshold crossings.

### 5. Stop-Loss And Take-Profit Were Not Added, But Need Explicit Governance

Severity: Medium

The decision not to add fixed individual stop-loss/take-profit is consistent with value investing, but the framework needs a formal policy so future agents do not add price stops opportunistically.

Impact:

- Without governance, future tests may add stops after drawdowns, causing overfit market-timing behavior.

Improvement:

- Keep individual stop-loss/take-profit disabled by default.
- Only test them under a separate research hypothesis:
  - thesis: credit deterioration proxy or liquidity risk control;
  - trigger: not pure price loss alone unless economically justified;
  - decision: separate from factor alpha.

### 6. Platform Consistency Improved, But Residual Gap Still Needs Attribution

Severity: Medium

After switching to JoinQuant real stock prices and adjusted benchmark prices, local strategy return moved close to JoinQuant. Residual differences remain and should be attributed before treating local daily simulation as fully platform-equivalent.

Observed:

- Local real-price daily return: about `33.89%`.
- JoinQuant platform return: about `35.77%`.
- Local benchmark: about `25.16%`.
- JoinQuant benchmark: about `26.51%`.
- Max drawdown interval matched.

Improvement:

- Add an attribution runner comparing:
  - local daily holdings;
  - JoinQuant daily curve CSV;
  - rebalance-date holdings;
  - dividend cash events;
  - benchmark daily returns.
- Require a residual threshold, for example less than 2 percentage points strategy-return difference and matched drawdown interval.

### 7. Universe Construction Is Still Approximate

Severity: Medium

The strategy uses a bank universe derived from migrated/local data and frozen signal lists. It is not yet a fully point-in-time historical industry membership system.

Impact:

- Long-window validation may contain survivorship or membership approximation bias.

Improvement:

- Build a point-in-time bank universe runner:
  - listing dates;
  - delisting dates;
  - ST status;
  - industry classification by date;
  - newly listed exclusion.
- Store universe snapshots in the local database with manifests.

### 8. Bank-Specific Indicator Replacement Needs Stronger Source Labels

Severity: Medium

The spec correctly avoids JoinQuant `bank_indicator`, but the replacement pipeline still needs stronger source labels and review status for NPL, provision coverage, and capital adequacy fields.

Impact:

- The strategy may appear more reproducible than it actually is if reconstructed or extracted indicators are not fully traceable.

Improvement:

- For every bank-specific field, store:
  - source document/table;
  - announcement date;
  - extraction method;
  - confidence;
  - manual review status;
  - original versus reconstructed flag.

### 9. Metrics From Quarterly And Daily Backtests Were Mixed During Interpretation

Severity: Medium

Quarterly-period metrics and daily-path metrics were both used during the discussion. They have different volatility, drawdown, win-rate, and Sharpe meanings.

Impact:

- Quarterly max drawdown understated daily drawdown.
- Daily and quarterly Sharpe/win-rate are not directly comparable.

Improvement:

- Use quarterly backtests for factor/research sanity checks.
- Use daily JoinQuant-like backtests for execution and risk metrics.
- Label report frequency explicitly in every summary.

### 10. Knowledge Capture Started, But Decision Governance Is Not Yet Formal Enough

Severity: Low-Medium

Knowledge cards were created, but candidate decisions still need a structured decision log: pending, accepted, rejected, archived, platform-confirmation-only, risk-control-candidate.

Improvement:

- Add `decisions/` or `governance/` records for:
  - factor inclusion;
  - data source acceptance;
  - execution alignment acceptance;
  - defensive overlay status.

## Recommended Next Steps

1. Freeze the current Bank Value 15Y as `platform_confirmation_candidate_v1`.
2. Do not tune it further on 2021-05 to 2026-05.
3. Build a formal validation runner for ablation, baselines, and robustness.
4. Build a point-in-time bank universe dataset.
5. Add local-vs-JoinQuant daily attribution.
6. Promote the defensive overlay only as `risk_control_candidate`.
7. Start a paper-trading or future-forward confirmation log.

## Current Status

Bank Value 15Y is not a final accepted strategy.

It is a useful V5 system test and a promising research candidate with improved execution alignment. The correct status is:

`pending_validation + platform_confirmation_completed + defensive_overlay_candidate`

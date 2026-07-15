# Local JoinQuant Simulation Gap Plan

Date: 2026-07-15

## Objective

Make V5 local daily backtesting close enough to JoinQuant platform simulation that local results can be used for rapid debugging before spending JoinQuant credits.

Target case:

- Strategy: `bank_value_quality_v2`
- Platform window: `2021-05-01` to `2026-05-31`
- Benchmark: `512800.XSHG`
- Platform result to match first: JoinQuant strategy return `35.43%`, benchmark return `26.51%`, max drawdown `18.08%`, max drawdown interval `2021-07-06` to `2022-11-03`.

## Current Blocking Gap

Current local daily runner is not yet a true V2 platform simulator.

Reason:

- `bank_value_quality_v2` uses `two_layer_score`: `value_score`, `quality_score`, and a V2-specific value-trap guard.
- Existing `src/v5/daily_backtest.py` and `src/v5/local_backtest.py` call the generic single-layer `_score_date_rows` from `src/v5/validation_runner.py`.
- The generic guard still expects old V1-style fields: `non_performing_loan_ratio`, `provision_coverage_ratio`, `core_tier_1_capital_adequacy_ratio`.
- V2 uses Eastmoney proxy fields: `asset_quality_trend`, `provision_buffer`, `capital_resilience`.

Until this is fixed, any local V2 result is not comparable to the JoinQuant V2 platform result.

## External JoinQuant Rules To Mirror

Use these as local simulator requirements:

- `get_price` supports `fq='pre'`, `fq='post'`, and `fq=None` / `fq='none'`; unadjusted real price is required for execution comparison.
- `set_option('use_real_price', True)` changes how real-price/back-adjusted behavior is interpreted.
- `set_option('avoid_future_data', True)` should be mirrored by strict point-in-time factor visibility.
- `get_current_data()` is the platform path for current paused, ST, high-limit and low-limit state.
- A-share stock orders must respect 100-share board lots; clearing to zero can sell remaining odd lots.
- Typical A-share stock cost settings include sell-side stamp duty, buy/sell commission and minimum commission.
- JoinQuant strategy code may run on older pandas versions, so do not use `DataFrame.attrs`.

## Implementation Steps

### Step 1: Add V2 Scoring Engine

Add a strategy-aware scoring module, for example:

- `src/v5/scoring.py`

Required functions:

- `score_rows(raw_spec, date_rows)`
- `score_weighted_composite(...)`
- `score_two_layer(...)`
- `apply_value_trap_guard(raw_spec, scored_rows)`

V2 scoring must match the JoinQuant file:

- value layer:
  - `low_price_to_book`: weight `0.60`, lower is better;
  - `sustainable_dividend_yield`: weight `0.40`, higher is better, currently missing unless dividend factor is attached.
- quality layer:
  - `roe_quality`: weight `0.35`;
  - `asset_quality_trend`: weight `0.25`;
  - `provision_buffer`: weight `0.20`;
  - `capital_resilience`: weight `0.20`.
- final score:
  - `0.55 * value_score + 0.45 * quality_score` when quality exists;
  - fallback to value score only when quality is unavailable.

### Step 2: Add Eastmoney Quality Merge Into Local Panel

Input:

- `数据库/processed/eastmoney_bank_quality_manual_csv.csv`

Join rules:

- key by `code`;
- use `source_year`;
- visibility determined by `notice_date`;
- only use rows where `notice_date < rebalance_date`;
- if multiple reports are visible, use the latest visible one.

Fields to merge:

- `asset_quality_trend`;
- `provision_buffer`;
- `capital_resilience`;
- optional diagnostics: `review_status`, `confidence`, `source_note`.

Important:

- `needs_check` may be used for platform proxy debugging.
- `reviewed` only should be used for formal Quant Validation.

### Step 3: Reproduce JoinQuant Rebalance Calendar

Current JoinQuant V2 code:

- runs daily at `09:40`;
- rebalances only in months `[1, 4, 7, 10]`;
- uses `context.previous_date` as `factor_date`;
- executes only once per rebalance month;
- skips month until a date passes coverage/tradability checks.

Local runner must record:

- actual local signal date;
- factor date;
- selected stocks;
- used factors;
- candidate count;
- guarded count;
- coverage ratio.

### Step 4: Execution Price Matching

Use local JoinQuant real data:

- `数据库/processed/joinquant_real_daily_prices.csv`

Required fields:

- unadjusted real open;
- unadjusted real close;
- paused/tradability if available;
- high-limit/low-limit if available or approximated.

Execution rule:

- rebalance at `09:40`;
- approximate execution price with same-day open unless a better JoinQuant-like intraday price proxy is collected;
- value positions at same-day close.

Known limitation:

- true 09:40 intraday price is not currently available in the local database.

### Step 5: Trading Constraint Matching

Mirror the JoinQuant code:

- skip paused stocks;
- skip ST stocks;
- skip buy/sell when current price is at high-limit or low-limit;
- new listing exclusion: 180 days;
- board lot: round target amount down to 100 shares;
- if target is zero, clear position;
- if delta is less than 100 shares and target is nonzero, skip the tiny adjustment;
- preserve residual cash.

### Step 6: Cost And Tax Matching

Current JoinQuant V2 code sets:

- open commission: `0.0003`;
- close commission: `0.0003`;
- minimum commission: `5`;
- no explicit sell-side stamp duty in the current file.

Local runner should support both:

- `platform_code_mode`: match the current JoinQuant file exactly;
- `realistic_a_share_mode`: include sell-side stamp duty such as `0.001`.

Do not mix these two modes when comparing with JoinQuant.

### Step 7: Dividend And Corporate Action Matching

For platform confirmation:

- do not manually add dividends inside the JoinQuant strategy code;
- local runner should use explicit cash dividend events only if matching platform cash-flow timing;
- otherwise use platform daily total value CSV for attribution.

Required local diagnostics:

- price return;
- cash dividend received;
- dividend tax assumption;
- ex-date;
- payment date if available;
- whether a difference is caused by dividend timing.

### Step 8: Benchmark Matching

Use `512800.XSHG`.

Local benchmark source:

- `数据库/processed/joinquant_real_benchmark_prices.csv`

Required:

- match `fq='pre'` benchmark behavior used in previous JoinQuant alignment;
- report benchmark return and benchmark volatility;
- compare local benchmark `26.51%` target over the same window.

If benchmark return differs materially, strategy comparison is not valid yet.

### Step 9: Daily Attribution Report

Add or extend attribution output:

- local daily return;
- JoinQuant daily return from exported CSV;
- return difference;
- cumulative difference;
- benchmark difference;
- holding difference;
- cash difference;
- dividend difference;
- trade-day difference;
- selected-stock difference.

Acceptance threshold for platform equivalence:

- benchmark cumulative return within `0.5` percentage points;
- strategy cumulative return within `1.0` to `2.0` percentage points;
- max drawdown interval should match or be explainably close;
- every rebalance date selected-stock difference must be explainable.

### Step 10: Tests

Add unit tests for:

- V2 two-layer scoring;
- V2 fallback when dividend is missing;
- V2 value-trap guard;
- Eastmoney quality point-in-time visibility;
- 100-share lot rounding;
- odd-lot clearing;
- commission and optional stamp-duty modes;
- pandas compatibility rule: no JoinQuant export uses `DataFrame.attrs`.

## Priority Order

1. Implement V2 scoring locally.
2. Merge Eastmoney quality fields point-in-time.
3. Re-run local daily JoinQuant-like V2 simulation.
4. Export local daily curve and holdings.
5. Ask user to provide JoinQuant daily result CSV for the 35.43 percent run.
6. Run local-vs-JoinQuant daily attribution.
7. Only then decide whether the local simulator is accurate enough.

## Current Decision

Do not yet compare the 35.43 percent JoinQuant V2 result against existing local runner output.

Reason:

Existing local output is not guaranteed to use V2 two-layer scoring, Eastmoney quality proxy, and the exact JoinQuant execution logic.


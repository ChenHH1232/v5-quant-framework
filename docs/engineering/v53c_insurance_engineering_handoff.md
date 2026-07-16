# Engineering Handoff: V5.3c Insurance Low-PB-only

Date: 2026-07-17

Status:

```text
approved_for_engineering_preparation
```

## Scope

Prepare V5.3c for local daily simulation and platform replication readiness.

Do not write JoinQuant strategy code yet.

## Frozen Research Rule

Universe:

```text
PIT-confirmed A-share core insurance operating companies and insurance groups
```

Score:

```text
low_price_to_book only
```

Direction:

```text
lower PB is better
```

Portfolio:

```text
top 3, equal weight, quarterly rebalance
```

Do not include:

- profit growth;
- ROE positive quality score;
- dividend composite score;
- EV / NBV;
- solvency guard;
- market-timing rule.

## Required Engineering Outputs

- local daily rebalance signals;
- local daily returns;
- holdings log;
- trade log;
- cash log;
- benchmark return series;
- concentration and turnover diagnostics;
- execution-price and dividend-treatment notes.

## Benchmark Policy Required

Before daily simulation, choose an insurance-appropriate benchmark.

Do not use the bank ETF as benchmark.

Candidate benchmark types:

- insurance industry index if available from JoinQuant / DataJQ;
- CSI / SW insurance industry index if available;
- equal-weight core insurance universe as fallback benchmark, clearly labeled as internal benchmark.

## Audit Focus

- PIT universe coverage on every rebalance date;
- daily open / close execution convention;
- dividend cash handling;
- suspension / limit-up / limit-down handling;
- 100-share lot constraint;
- 2021, 2022 and 2026 failure-year daily attribution;
- top2 / top3 / top4 concentration sensitivity.

## Exit Criteria

Engineering preparation passes only if:

- all required logs are generated;
- benchmark policy is explicit;
- local daily result is explainable from quarterly research signals;
- no platform contract mismatch is detected.

## First Local Daily Simulation

Completed:

```text
docs / engineering / v53c_insurance_local_daily_simulation_result.md
```

Current gate:

```text
engineering_daily_simulation_with_dividends_passed_platform_replication_pending_pm_review
```

Real insurance cash-dividend events have been added with 20% tax treatment.

Platform replication still requires PM approval of `399809.XSHE` as benchmark and PM review of the 2026 partial-year failure.

# V5.8 Telecom Overlay Basket Contribution PM Decision V1

Date: 2026-07-19

Owner:

```text
Project Manager Agent
```

Experiment layer:

```text
research_pit_validation + engineering_smoke_test
```

## Decision

PM decision:

```text
telecom_overlay_diagnostic_completed_observation_only_not_v57f_replacement
```

Telecom remains an observation sleeve. It is not promoted into the V5.7f frozen main basket.

## What Was Done

Engineering Agent repaired the data inputs required for a fair basket diagnostic:

```text
real daily open / close prices
cash dividend events with 20% tax treatment
PIT-safe low-volatility factor panel
```

Then PM ran a sidecar diagnostic overlay:

```text
dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay
```

This overlay adds telecom operators to the V5.7f basket family without modifying the V5.7f candidate.

## Artifacts

Config:

```text
config/dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay.json
```

Basket construction:

```text
validation_formal_v58_telecom_overlay_basket_constructor/basket_construction_summary.json
validation_formal_v58_telecom_overlay_basket_constructor/basket_rebalance_signals.csv
```

Matched local daily simulation:

```text
local_daily_backtests_v58_telecom_overlay_matched/dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay/dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay/summary.json
```

Formal validation:

```text
validation_formal_v58_telecom_overlay_matched_basket/dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay/basket_formal_validation_summary.json
```

## Comparison With V5.7f

Both rows use the same near-five-year local daily simulation style and the same 200万 / 99.5% exposure comparison setting.

| Metric | V5.7f main basket | V5.8 telecom overlay | PM read |
| --- | ---: | ---: | --- |
| Strategy return | 81.42% | 80.12% | worse |
| Annualized return | 14.27% | 14.09% | slightly worse |
| Excess return | 30.40% | 28.67% | worse |
| Benchmark return | 51.01% | 51.45% | benchmark changed with same-pool telecom inclusion |
| Max drawdown | 11.75% | 11.11% | slightly better |
| Sharpe | 0.932 | 0.950 | slightly better |
| Information ratio | 0.444 | 0.400 | worse |
| Volatility | 15.64% | 15.08% | better |

Telecom overlay exposure:

| Check | Result |
| --- | ---: |
| Telecom holding signals | 45 |
| Telecom average weight per rebalance | 7.64% |
| Telecom average names per rebalance | 2.37 |
| Each core telecom code selected | 15 times |

## Interpretation

Telecom slightly reduces volatility and drawdown, but it does not improve total return, excess return or information ratio versus the V5.7f main basket. This is consistent with its business profile: stable cash-flow and dividend support may help defensive characteristics, but the three-name universe is too concentrated to become a standalone alpha sleeve.

## PM Outcome

Current status:

```text
observation_sleeve_data_repaired
basket_contribution_diagnostic_completed
not_mainline_replacement
not_platform_replication
not_accepted_strategy
```

Allowed next work:

```text
Keep telecom in paper observation or future basket diagnostics with a capped weight.
```

Blocked next work:

```text
Do not replace V5.7f with the telecom overlay.
Do not generate JoinQuant strategy code for the overlay.
Do not promote telecom to formal_strategy_candidate.
```

## Next PM Action

Keep V5.7f as the current enhanced ETF candidate. Telecom can remain in the observation queue and may be reconsidered only if future paper records or specialist operating data show a stronger basket contribution.


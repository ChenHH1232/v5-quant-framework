# V5.6 Low-Vol Factor And Basket Constructor Stage 2 V1

Date: 2026-07-18

Owner:

```text
Project Manager Agent
```

Experiment layer:

```text
research_pit_validation
```

Status:

```text
low_vol_factor_runner_completed
shadow_basket_constructor_completed
not_backtest
not_accepted_strategy
```

## Purpose

V5.6 Stage 2 converts the Stage 1 screening result into two reusable tools:

1. A PIT-safe low-volatility factor runner.
2. A first cross-sector shadow basket constructor.

This is still not a deployable strategy. It only prepares the infrastructure needed for a dividend low-volatility and free-cash-flow enhanced ETF-style path.

## Low-Volatility Factor Runner

Runner:

```text
src/v5/low_volatility_factor_runner.py
```

CLI:

```text
python -m v5.cli add-low-volatility-factors PANEL_CSV PRICE_CSV --benchmark-csv BENCHMARK_CSV --strategy-id STRATEGY_ID
```

PIT rule:

```text
For each trade_date, only daily closes strictly before trade_date are used.
The trade_date close and all future prices are excluded.
```

Generated fields:

| Field group | Fields |
| --- | --- |
| Realized volatility | `volatility_60d`, `volatility_120d`, `volatility_252d` |
| Downside volatility | `downside_volatility_60d`, `downside_volatility_120d`, `downside_volatility_252d` |
| Drawdown | `max_drawdown_60d`, `max_drawdown_120d`, `max_drawdown_252d` |
| Beta | `beta_60d`, `beta_120d`, `beta_252d` |
| Composite support | `low_vol_score` |
| Audit | `low_vol_factor_visible_date`, `low_vol_factor_source`, observation counts |

## Generated Low-Vol Panels

| Sector | Output | Status |
| --- | --- | --- |
| Utilities / electricity | `数据库/processed/low_volatility_factors_v56/utilities_v51f/panel_with_low_vol.csv` | completed |
| Highway infrastructure | `数据库/processed/low_volatility_factors_v56/highway_v54h/panel_with_low_vol.csv` | completed |
| Port / rail infrastructure | `数据库/processed/low_volatility_factors_v56/port_rail_v55j/panel_with_low_vol.csv` | completed |

Bank is not yet included in the first generated low-vol panel because the current local database does not contain a bank real daily price file matching the V3 panel.

## Basket Constructor

Runner:

```text
src/v5/basket_constructor_runner.py
```

Config:

```text
config/dividend_low_vol_fcf_basket_v56.json
```

CLI:

```text
python -m v5.cli construct-dividend-low-vol-fcf-basket --config config/dividend_low_vol_fcf_basket_v56.json
```

First included sectors:

| Sector | Reason |
| --- | --- |
| Utilities / electricity | Golden-template sector |
| Highway infrastructure | Stable cash-flow and dividend candidate |
| Port / rail infrastructure | Reviewed business-purity candidate, pending platform replication |

Basket signal guard:

```text
start_date = 2021-05-01
end_date = 2026-05-31
required_fields = low_vol_score + volatility_120d
```

Rows before the platform-confirmation window, or rows without real low-volatility factors, are excluded from basket signal construction.

First excluded or pending sectors:

| Sector | Reason |
| --- | --- |
| Bank | Waiting for local real daily price file and low-vol factor generation |
| Telecom operators | Observation only because A-share sample is too small |
| Insurance | Specialist observation sleeve; not generic FCF basket |
| Gas / water | Needs operating-purity and tariff / project-revenue research |
| Coal | Blocked by cyclical data gate |

## PM Decision

V5.6 Stage 2 is approved as infrastructure progress:

```text
low_volatility_factor_runner_completed
shadow_basket_constructor_completed
```

But it is not:

```text
accepted_strategy
platform_replication_passed
paper_trading_ready
live_trading_approved
```

## Next Gate

The next gate is:

```text
v56_basket_daily_backtest_and_benchmark_design
```

Required before that gate:

1. Add bank low-vol factors after bank real daily price data is collected or located.
2. Build a basket-level daily simulator.
3. Build a basket benchmark, preferably same-pool equal weight plus dividend-low-vol baseline.
4. Run formal validation and overfit audit on the basket signal itself.

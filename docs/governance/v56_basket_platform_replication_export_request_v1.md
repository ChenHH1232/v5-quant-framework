# V5.6 Basket Platform Replication Export Request V1

Date: 2026-07-18

Owner:

```text
Engineering Agent, supervised by Project Manager Agent
```

Status:

```text
platform_replication_prepared
pending_joinquant_exports
not_platform_replication_passed
not_accepted_strategy
```

## Purpose

This packet prepares V5.6 for JoinQuant platform replication.

The JoinQuant script is frozen-signal only:

```text
exports/joinquant/v56_dividend_low_vol_fcf_basket_frozen_signals_near5y.py
```

It must not recompute factors, tune weights, change selected stocks, add defense, or alter rebalance dates after seeing platform results.

## Local Reference

Local run directory:

```text
local_daily_backtests_v56_basket/v56_dividend_low_vol_fcf_shadow_basket
```

Local files:

| File | Purpose |
| --- | --- |
| `daily_returns.csv` | local daily NAV and benchmark |
| `trades.csv` | local open-price trades |
| `holdings.csv` | local rebalance-date holdings |
| `dividends.csv` | local tax-adjusted cash dividends |
| `rebalance_signals.csv` | frozen V5.6 basket signals |

Platform packet:

```text
platform_replication_packets_v56_basket/v56_dividend_low_vol_fcf_shadow_basket/platform_replication_packet.json
```

Current packet status:

```text
pending_attribution
```

Reason:

```text
JoinQuant daily result, transaction and position CSV exports are not attached yet.
```

## JoinQuant Backtest Setup

Use:

```text
exports/joinquant/v56_dividend_low_vol_fcf_basket_frozen_signals_near5y.py
```

Recommended settings:

| Item | Value |
| --- | --- |
| Start date | 2021-05-01 |
| End date | 2026-05-31 |
| Initial cash | 2,000,000 |
| Frequency | Daily |
| Benchmark shown in script | 000300.XSHG |

Important:

```text
000300.XSHG is only a JoinQuant display benchmark.
Formal comparison should use the local same-pool total-return benchmark.
```

## Required Exports

After the JoinQuant run, export:

| Export | Required file |
| --- | --- |
| Daily return / result CSV | `result_*.csv` |
| Transaction detail CSV | `transaction.csv` |
| Position CSV | `position.csv` |
| Full log | `log.txt` |

## Attribution Commands

After exports are available, run:

```text
python -m v5.cli platform-replication-packet \
  local_daily_backtests_v56_basket/v56_dividend_low_vol_fcf_shadow_basket \
  --out platform_replication_packets_v56_basket \
  --strategy-id v56_dividend_low_vol_fcf_shadow_basket \
  --panel-csv validation_formal_v56_basket/v56_dividend_low_vol_fcf_shadow_basket/combined_basket_panel_for_validation.csv \
  --joinquant-daily-csv <result_csv> \
  --joinquant-transaction-csv <transaction_csv> \
  --joinquant-position-csv <position_csv>
```

PM pass rule:

```text
Only if daily NAV residual, transaction attribution and position attribution all pass can V5.6 be promoted to platform_replication_passed.
```

Not enough:

```text
A good JoinQuant return summary alone is not enough.
```

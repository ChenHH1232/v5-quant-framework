# V5.7f Dividend Low-Vol Cash-Flow Enhanced ETF Platform Replication Preparation V1

Date: 2026-07-19

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

This packet prepares V5.7f for JoinQuant platform replication.

V5.7f is a frozen ETF-like basket candidate:

- Sleeves: bank, utilities/electricity, highway infrastructure, port/rail infrastructure.
- Target names: 28.
- Sector cap: 25%.
- Single-stock cap: 5%.
- Rebalance: quarterly frozen local signals.
- Execution comparison: local daily-open approximation versus JoinQuant 09:40 scheduled execution.

This step is only for platform alignment and attribution. It must not be used to tune factors, rebalance dates, sector caps or selected stocks.

## Frozen JoinQuant Script

Generated script:

```text
exports/joinquant/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f_joinquant_frozen_signals_near5y.py
```

Generator:

```text
python -m v5.cli export-basket-frozen-signals-joinquant \
  --signals validation_formal_v57f_etf_constructor/basket_rebalance_signals.csv \
  --out-file exports/joinquant/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f_joinquant_frozen_signals_near5y.py \
  --strategy-id dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f \
  --script-version v57f_etf_frozen_signals_20260719 \
  --benchmark 000300.XSHG \
  --target-exposure 0.995 \
  --lot-size 100
```

The script uses `order_target_value`, not `order_target_percent`, to avoid the JoinQuant runtime compatibility issue previously seen in V5.3.

## Local Reference

Local run directory:

```text
local_daily_backtests_v57f_etf/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f
```

Reference files:

| File | Purpose |
| --- | --- |
| `daily_returns.csv` | local daily NAV and same-pool benchmark |
| `trades.csv` | local open-price trade approximation |
| `holdings.csv` | local rebalance-date holdings |
| `dividends.csv` | local tax-adjusted cash dividends |
| `rebalance_signals.csv` | frozen V5.7f basket signals |

Platform packet:

```text
platform_replication_packets_v57f_etf/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/platform_replication_packet.json
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

Recommended settings:

| Item | Value |
| --- | --- |
| Start date | 2021-05-01 |
| End date | 2026-05-31 |
| Initial cash | 2,000,000 |
| Frequency | Daily |
| Scheduled rebalance | 09:40 |
| Display benchmark | 000300.XSHG |

Important:

```text
000300.XSHG is only a JoinQuant display benchmark.
Formal comparison should use the local same-pool total-return benchmark and attribution packet.
```

## Required Platform Exports

After the JoinQuant run, export:

| Export | Required file |
| --- | --- |
| Daily return / result CSV | `result_*.csv` |
| Transaction detail CSV | `transaction.csv` |
| Position CSV | `position.csv` |
| Full log | `log.txt` |

## Attribution Command

After exports are available:

```text
python -m v5.cli platform-replication-packet \
  local_daily_backtests_v57f_etf/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f \
  --out platform_replication_packets_v57f_etf \
  --strategy-id dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f \
  --panel-csv validation_formal_v57f_etf/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f/combined_basket_panel_for_validation.csv \
  --joinquant-daily-csv <result_csv> \
  --joinquant-transaction-csv <transaction_csv> \
  --joinquant-position-csv <position_csv>
```

PM pass rule:

```text
Only if daily NAV residual, transaction attribution and position attribution all pass can V5.7f be promoted to platform_replication_passed.
```

Not enough:

```text
A good JoinQuant return summary alone is not enough.
```

## Current PM Decision

V5.7f remains:

```text
formal_etf_candidate
platform_replication_prepared_pending_joinquant_exports
paper_trading_process_started_pending_fresh_pit_panel
not_accepted_strategy
```

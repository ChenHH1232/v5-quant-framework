# V5.1f Utilities Paper Signal 2026-07-16

Date: 2026-07-16

Layer: `paper_trading_signal`

Status: `monitor_only`

Not status:

```text
accepted_strategy
live_trading_approved
personal_investment_advice
```

## Signal Context

As of 2026-07-16, the latest visible electricity-demand state used by V5.1f is:

```text
state_date = 2026-06-30
visible_date = 2026-07-15
electricity_consumption_yoy = 3.7%
```

Historical state thresholds from the visible PIT state panel:

```text
history_count = 22
q33 = 5.0
q67 = 6.9
```

State bucket:

```text
weak
```

V5.1f branch:

```text
weak electricity demand -> dividend_yield top 10
```

Factor date:

```text
2026-07-15
```

Candidate count:

```text
117
```

## Paper Signal Holdings

Target portfolio construction:

```text
equal-weight top 10
target_weight = 9.95% each
cash buffer = 0.5%
```

| Rank | Code | Name | Dividend Yield | Cash/Share | Pre-Adjusted Close | PB | Operating Cash-Flow Yield | Target Weight |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 1 | 600803.XSHG | 新奥股份 | 13.3047% | 2.170 | 16.31 | 2.0868 | 0.0187% | 9.95% |
| 2 | 001299.XSHE | 美能能源 | 6.3725% | 0.650 | 10.20 | 2.5808 | 0.4479% | 9.95% |
| 3 | 600575.XSHG | 淮河能源 | 5.9748% | 0.190 | 3.18 | 1.0214 | 3.5872% | 9.95% |
| 4 | 605368.XSHG | 蓝天燃气 | 5.9435% | 0.400 | 6.73 | 1.4484 | 2.3340% | 9.95% |
| 5 | 600011.XSHG | 华能国际 | 5.7971% | 0.400 | 6.90 | 1.5461 | 11.4818% | 9.95% |
| 6 | 000899.XSHE | 赣能股份 | 5.7681% | 0.567 | 9.83 | 1.4412 | 11.2701% | 9.95% |
| 7 | 600098.XSHG | 广州发展 | 5.5821% | 0.350 | 6.27 | 0.7912 | 2.7432% | 9.95% |
| 8 | 600642.XSHG | 申能股份 | 5.5422% | 0.460 | 8.30 | 1.0659 | 5.8625% | 9.95% |
| 9 | 000690.XSHE | 宝新能源 | 5.3533% | 0.250 | 4.67 | 0.7763 | 7.8109% | 9.95% |
| 10 | 600475.XSHG | 华光环能 | 5.2671% | 0.700 | 13.29 | 1.4671 | -1.5475% | 9.95% |

## Files

```text
paper_trading_signals/utilities_demand_state_v51f/2026-07-16/signal_summary.json
paper_trading_signals/utilities_demand_state_v51f/2026-07-16/selected_signal.csv
paper_trading_signals/utilities_demand_state_v51f/2026-07-16/candidate_scores.csv
```

## PM Interpretation

This is a V5.1f forward paper-trading signal.

It should be monitored, not treated as an accepted strategy or personal trading instruction.

The signal is concentrated in high-dividend electricity/gas/public-utility operators because the latest electricity-demand state is weak.

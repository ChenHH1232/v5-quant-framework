# V5.3c Insurance Benchmark Probe

Date: 2026-07-17

Status:

```text
verified_joinquant_insurance_benchmark_found
```

## Probe Output

Raw probe:

```text
docs / engineering / insurance_v53c_benchmark_probe.json
```

## Result

Approved engineering benchmark candidate:

```text
399809.XSHE
```

JoinQuant name:

```text
中证方正富邦保险主题指数
```

Reason:

```text
It is priceable through JoinQuant get_price and is insurance-theme specific.
```

## Rejected / Not Preferred

| Code | Name / Issue | Decision |
| --- | --- | --- |
| 512070.XSHG | 证券保险 ETF | mixed securities + insurance, not pure insurance |
| 515630.XSHG | 保险证券 ETF | mixed securities + insurance, not pure insurance |
| 167301.XSHE | 保险主题 LOF | fund benchmark possible, but index 399809 is cleaner |
| 000849.XSHG | 沪深300非银行金融指数 | non-bank financials includes brokers and other financials |
| 000300.XSHG | 沪深300 | broad-market reference only |
| 801194 / 851941 | SW insurance industry codes | not priceable through tested JoinQuant get_price calls |

## Policy

Use `399809.XSHE` for V5.3c local daily simulation and any later platform comparison unless PM explicitly chooses a different verified insurance benchmark.


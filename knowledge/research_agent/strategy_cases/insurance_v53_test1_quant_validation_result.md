# Insurance V5.3 Test-1 Quant Validation Result

Date: 2026-07-16

Status:

```text
research_pit_validation_completed_current_composite_rejected
```

## Research Memory

V5.3 Test-1 showed that the insurance process can run, but the first composite model is not good enough.

The useful structure is:

```text
low PB + dividend yield
```

The weak structure is:

```text
ROE + profit growth as generic insurance quality proxies
```

## Key Evidence

Factor IC / RankIC:

| Factor | Mean IC | Mean RankIC | Read |
| --- | ---: | ---: | --- |
| Low PB | 0.2004 | 0.2023 | strongest |
| Dividend yield | 0.1606 | 0.1614 | positive |
| ROE TTM | 0.0594 | 0.0452 | weak |
| Profit growth YoY | -0.0888 | -0.0955 | reject |

Baseline:

- low PB top 3: 137.12%;
- current composite: 114.09%;
- equal-weight core insurance: 79.01%.

The composite failed because it did not beat the simple low-PB baseline and because generic growth / quality proxies weakened the signal.

## Data Lessons

`insurance_indicator` is useful but not enough yet:

- 2024 and 2025 coverage returned zero in the first probe;
- EV / NBV were not available in the detected fields;
- solvency and investment-return fields should be repaired before being used as formal quality factors.

Rate state currently uses:

```text
511010.XSHG bond ETF proxy
```

This is acceptable for Test-1 review only. Formal candidate promotion requires true PIT 10Y government bond yield.

## PM Outcome

Do not promote V5.3 Test-1.

Recommended next hypothesis:

```text
V5.3b Insurance Low-PB + Dividend With Real Rate State
```

Keep weak years visible:

- 2021;
- 2022;
- 2026.


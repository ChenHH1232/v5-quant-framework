# Highway V5.4d Segment Purity Result

Date: 2026-07-18

## Result

Adding real segment evidence materially improved the highway line.

The useful repaired field is:

```text
highway business purity / non-highway revenue contamination
```

## Evidence

- Segment-purity composite return: 99.57%.
- High-dividend formal highway baseline: 92.36%.
- Dividend yield Mean IC improved to 0.2577 after removing non-highway-contaminated rows.
- 2026 loss narrowed to -3.29%.

## Interpretation

The earlier highway failures were partly a data-definition problem:

```text
HY03160 industry membership alone is too broad.
```

Some rows were not clean toll-road operators at the time. Once visible segment evidence is used, the high-dividend signal becomes stronger.

## Remaining Research Gap

The model still lacks direct highway operating information:

- traffic volume;
- toll revenue;
- remaining concession years;
- toll policy changes.

These must come from original annual/interim reports or a verified structured provider.

## PM Instruction

V5.4d is promising but not ready for Engineering Agent.

Next step:

```text
annual_report_spot_check_and_operating_data_repair
```

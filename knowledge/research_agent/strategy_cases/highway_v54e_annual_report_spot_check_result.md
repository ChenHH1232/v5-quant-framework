# Highway V5.4e Annual-Report Spot-Check Result

Date: 2026-07-18

## Conclusion

V5.4e strengthens the highway line but does not yet clear the engineering gate.

The Eastmoney segment evidence is broadly supported by sampled annual reports:

- 7 reports checked;
- 30 segment rows checked;
- 28 pass rows;
- 7 reports had at least one passing segment check.

## What This Means

The key research insight from V5.4d remains valid:

```text
HY03160 industry membership alone is too broad. High-dividend signals improve after filtering non-highway business contamination.
```

## What Is Still Missing

Direct highway operating fields are not yet usable as formal factors:

- traffic volume;
- toll revenue;
- remaining concession years;
- toll policy changes.

The extractor found candidate text snippets, but they require manual or rule-based review because:

- values may be road-level rather than company-level;
- units differ;
- some snippets are risk-disclosure text rather than numeric operating data;
- some candidate numbers are false positives.

## PM Instruction

Do not hand V5.4e to Engineering Agent.

Next step:

```text
review_candidate_operating_fields_then_run_v54f
```

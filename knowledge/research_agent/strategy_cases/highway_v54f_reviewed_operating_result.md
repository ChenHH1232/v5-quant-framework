# Highway V5.4f Reviewed Operating Data Result

Date: 2026-07-18

## Conclusion

V5.4f completed the Research / Quant loop but did not pass the Engineering gate.

The important result is not return performance. The important result is that highway operating disclosure can now be joined as PIT evidence, but current reviewed coverage is too narrow to support a deployable model.

## Evidence

Reviewed operating disclosure:

- 7 annual-report rows reviewed;
- 5 rows PIT usable;
- 5 companies covered at the disclosure level.

After joining back to the formal panel:

- 18 formal rows;
- 5 rebalance dates;
- 4 companies covered;
- rolling validation skipped due to insufficient history.

Formal validation:

- PIT leakage audit passed;
- composite cumulative return was -2.20%;
- high-dividend-only reviewed sample return was -6.64%;
- dividend yield still showed positive IC in the small sample, but the sample is too small to accept.

## Research Interpretation

V5.4f should be treated as a data-gate test, not a strategy upgrade.

Reviewed operating disclosure score is useful for:

- confirming original annual-report evidence exists;
- preventing unreviewed candidate fields from entering a strategy;
- documenting which companies have usable operating disclosure.

It is not yet useful as:

- a numeric traffic-volume factor;
- a toll-revenue growth factor;
- a remaining-concession factor;
- a platform-replication-ready trading signal.

## Instruction To Research Agent

Do not tune factor weights or selection count.

Next useful work is data repair:

```text
expand_reviewed_highway_operating_panel_2021_2025
```

Required fields:

- traffic volume, with company-level / road-level tag;
- toll revenue, with unit and company-level / road-level tag;
- toll revenue YoY where disclosed;
- remaining concession maturity or concession expiry;
- toll policy changes and fee-standard risk notes;
- visible date;
- source URL;
- local PDF path;
- original announcement checked flag.

Only after coverage is broad enough should Quant Agent rerun V5.4g.

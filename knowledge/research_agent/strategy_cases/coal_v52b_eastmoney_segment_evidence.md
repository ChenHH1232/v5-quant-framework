# Coal V5.2b Eastmoney Segment Evidence

Date: 2026-07-16

Status:

```text
research_memory_segment_evidence_partially_repaired
```

## Lesson

Financial reports do contain segment business information, and Eastmoney F10 can provide structured business-composition rows for most coal companies.

The V5.2b issue was not that segment evidence does not exist. The issue was that it had not been converted into PIT-ready structured data.

## Result

Eastmoney F10 segment runner produced:

- 6541 raw segment rows;
- 642 aggregated evidence rows;
- 561 PIT usable rows;
- 33 / 37 companies covered.

Missing companies:

- 000611.XSHE;
- 000780.XSHE;
- 600532.XSHG;
- 600652.XSHG.

## Rule

Eastmoney segment evidence is usable as a first-pass PIT business-tag source, but every row remains:

```text
eastmoney_segment_needs_spot_check
```

before formal acceptance.

## PM Implication

This improves V5.2b data quality but does not reopen the strategy candidate.

V5.2b remains archived until:

- the four missing companies are resolved;
- business tag policy is approved;
- NBS raw coal output history is completed;
- 2018 failure is repaired or accepted as a strategy rejection reason.

# Coal V5.2b Segment Reviewed Repair Result

Date: 2026-07-16

Status:

```text
research_memory_business_segment_evidence_repaired_not_accepted
```

## Lesson

Missing Eastmoney segment rows are not always ordinary data gaps.

For coal V5.2b, the four missing companies exposed three separate cases:

- real core coal history with corporate-action exit;
- coal trade exposure that should not be treated as coal operation;
- non-core / shell / transition businesses that should be excluded by PIT evidence;
- early coal history followed by business transformation.

## Research Rule

Coal trade revenue is not the same as coal mining or coal operation.

If a company reports coal as a product but the business segment is trade, medical, game/media, manufacturing, shell-like, ST, delisted, or disclosure-risk, Research Agent must keep it out of the formal core-coal universe unless a separate trade-only hypothesis is being tested.

## Four-Company Judgment

| Code | Judgment |
| --- | --- |
| `000611.XSHE` | exclude on 2022 panel dates; non-core / disclosure-risk. |
| `000780.XSHE` | include as core coal during PIT-visible periods; handle absorption/exit separately. |
| `600532.XSHG` | exclude; trade-oriented and mixed/non-core, not coal operation. |
| `600652.XSHG` | include only in early PIT coal period, exclude after game/media transition. |

## Validation Effect

After formal-universe filtering:

- panel rows fall from `1206` to `861`;
- reviewed evidence coverage becomes `37 / 37`;
- OCF yield remains the strongest factor;
- 2018 remains a weak coal-cycle year;
- V5.2b remains a research candidate, not an accepted strategy.

## Next Gate

Quant Validation Agent can continue from this repaired panel, but PM should still require:

- complete external inventory/output state;
- daily returns and rebalance signals for overfit audit;
- corporate-action handling before platform replication;
- explicit 2018 stress-case explanation.


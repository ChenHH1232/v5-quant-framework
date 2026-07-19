# Insurance V5.3 Research-Quant Loop Closeout

Date: 2026-07-17

Status:

```text
research_signal_exists_but_not_deployable_until_ev_nbv_pit_repair
```

## What The Loop Learned

The insurance line has not failed because there is no signal.

It failed because the current signal is incomplete:

- low PB has evidence;
- generic profitability and ROE factors were rejected;
- low PB + dividend was rejected;
- low PB + total investment return + solvency score was rejected;
- low PB + solvency guard was rejected;
- state diagnostics explain some stress but do not support timing.

## Why Research Must Stop Iterating Simple Variants

The next low-PB variation would likely be return tuning unless it adds new insurance-specific information.

Forbidden next steps:

- more low PB + simple quality composites;
- more solvency threshold variants;
- changing selection count to fit 2021-2026;
- turning state diagnostics into timing rules without stable ex-ante evidence.

## What Must Happen Next

Research Agent should repair multi-year PIT EV / NBV / P/EV data.

Required row-level evidence:

```text
code
report_period
embedded_value
new_business_value
source_document_title
source_url_or_file
original_announcement_date
conservative_visible_date
original_announcement_checked
field_definition_checked
```

Only after this gate may Research Agent propose:

- P/EV value hypothesis;
- EV growth franchise hypothesis;
- NBV growth franchise hypothesis;
- life-only / insurance-group subgroup comparison.

## PM Stop Rule

If EV / NBV PIT repair cannot meet coverage and audit requirements, insurance should be paused as:

```text
research_signal_exists_but_not_deployable
```


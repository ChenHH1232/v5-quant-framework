# Insurance V5.3f P/EV and NBV Data Repair Diagnostic

Date: 2026-07-17

Status:

```text
research_data_repair_partial_quant_diagnostic_only
```

## What Was Added

Research Agent added a P/EV, EV and NBV insurance valuation framework based on fxbaogao research reports.

Data repair added reviewed 2024-2025 EV/NBV rows for the five core insurance names:

- Ping An Insurance;
- China Life Insurance;
- CPIC;
- New China Life Insurance;
- PICC Group.

## Source Gate

EV/NBV-specific source audit:

```text
insurance_special_fields_source_repair_passed
```

Important caveats:

- 2024 New China Life EV/NBV exact values remain unconfirmed in this repair pass.
- 2024 CPIC row is life-only EV, while the 2025 seed is group EV; this口径 mismatch must be repaired before formal common-sample use.
- PICC uses life plus health EV/NBV because the P&C group business does not disclose embedded value.

## PIT Coverage Gate

P/EV panel status:

```text
ev_nbv_pev_panel_insufficient_history
```

Coverage:

- covered dates above 80% threshold: 5;
- covered years: 2025 and 2026 only;
- first covered date: 2025-04-01;
- last covered date: 2026-04-01.

PM decision:

```text
block_formal_validation_until_multi_year_pit_ev_nbv_history
```

## Quant Diagnostic Result

This was run as diagnostic only, not as formal strategy validation.

Observed sample:

- rows: 21;
- dates: 5;
- rolling validation: skipped due to insufficient history.

Baseline comparison:

| Case | Periods | Cumulative return | Note |
| --- | ---: | ---: | --- |
| equal_weight_covered_insurance | 5 | 6.60% | covered-sample reference |
| low_pev_top3 | 5 | 8.50% | diagnostic only |
| high_nbv_growth_top3 | 5 | -6.72% | sample too thin |
| pev_nbv_diagnostic_composite | 5 | 8.50% | effectively low P/EV because NBV growth is sparse |

Factor diagnostic:

| Factor | Observations | Dates | Mean IC | Mean RankIC | Interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| price_to_embedded_value | 21 | 5 | 0.101 | 0.020 | weak positive diagnostic signal after lower-is-better adjustment, not enough history |
| new_business_value_yoy | 4 | 1 | -0.256 | -0.200 | unusable; only one date |

## PM Conclusion

V5.3f did not create a formal insurance strategy candidate.

It did achieve the intended diagnostic purpose:

- confirmed the fxbaogao report workflow can add sector-specific knowledge;
- built a reusable EV/NBV/P/EV PIT panel runner;
- confirmed P/EV is plausible enough to justify more data repair;
- confirmed current PIT history is too short for formal Quant validation.

## Next Work

Research Agent should repair 2021-2023 original annual-report EV/NBV rows from exchange, Eastmoney, Tushare announcement links or manual reviewed PDFs.

Formal Quant may resume only after:

- 2021-2025 EV/NBV coverage is reviewed;
- CPIC group/life EV口径 is harmonized;
- 2024 New China Life exact values are confirmed;
- covered years pass the rolling-validation gate.

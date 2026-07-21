# V5.9 Gas / Water True Operating State Quant Start Packet

Date: 2026-07-21

Strategy id: `gas_water_true_operating_state_diagnostic_v59`

Decision: `quant_diagnostic_validation_started`

## PM Conclusion

Gas / water annual and semiannual reports do contain useful operating-state evidence, but mostly as unstructured text rather than clean numeric factors.

The collection path is feasible:

- CNINFO can locate and download original annual and semiannual report PDFs.
- Eastmoney is useful as first-layer F10 / announcement cross-check, but not as the stable PDF source.
- Extracted text can identify candidate evidence for gas pass-through, water tariff, connection / installation exposure, receivables / collection pressure and financing / debt pressure.

This opens Quant diagnostic validation. It does not open Engineering handoff.

## New Inputs

Evidence runner:

`src/v5/gas_water_true_operating_state_runner.py`

Diagnostic spec:

`examples/gas_water_true_operating_state_diagnostic_v59_strategy.json`

Historical PDF evidence:

`research_reports/gas_water_true_operating_state_v59_history_2020_2025/gas_water_true_operating_state_candidates.csv`

PIT-enriched panel:

`DATABASE_DIR/processed/gas_water_true_operating_state_panel_v59/panel_with_true_operating_state.csv`

Formal diagnostic validation:

`validation_formal_v59_gas_water_true_operating_state/gas_water_true_operating_state_diagnostic_v59/formal_validation_summary.json`

## Coverage

- Selected companies: `40`
- Requested report points: `390`
- Extracted PDF rows: `361`
- Evidence hit rows: `358`
- Report collection errors: `29`
- Panel rows: `746`
- Panel evidence coverage: `98.53%`
- Minimum rebalance-date coverage: `94.29%`
- 2026 coverage: `100%`

The coverage gate is passed for diagnostic validation because every rebalance date remains above the 80% minimum.

## Initial Diagnostic Result

The first formal validation run completed:

- Rows: `746`
- Rebalance dates: `20`
- PIT leakage audit: `pass`
- Status: `formal_validation_completed_not_acceptance`

Rolling results:

- 2023 cumulative return: `5.46%`
- 2024 cumulative return: `-1.62%`
- 2025 cumulative return: `12.47%`
- 2026 cumulative return: `-15.42%`

Baselines:

- Equal-weight gas/water: `42.59%`
- Low text receivables-pressure top 10: `2.58%`
- Low text financing/debt-pressure top 10: `-5.84%`
- Low text connection/install-pressure top 10: `39.15%`

## PM Interpretation

The true operating-state text variables are useful as Research Agent evidence, but they are not yet strong enough as direct selection factors.

Important signals:

- Receivables / collection and financing / debt text density have the expected negative IC direction, but the selection performance is weak.
- Connection / installation text pressure is closer to equal-weight but does not clearly improve the model.
- 2026 remains weak, so the failure is not solved by raw keyword density.

## Decision

`quant_validation_can_continue`

But:

`engineering_handoff_blocked`

## Next Quant Task

Quant Agent should continue with diagnostic validation only:

1. Compare text variables as state filters rather than positive scoring factors.
2. Split gas and water sub-industries before judging tariff/pass-through text.
3. Test reviewed numeric extraction candidates for:
   - connection / installation revenue share,
   - receivables aging or receivables-to-revenue,
   - government / sewage-treatment receivable exposure,
   - interest-bearing debt / financing-cost pressure,
   - gas purchase and sale spread where available.
4. Decide whether the Research Agent must return to manual numeric extraction.

## Guardrails

- Do not promote text keyword density into an Engineering strategy.
- Do not tune V57b weights with 2021-2026.
- Do not treat missing report rows as zero-quality companies unless Research Agent confirms the disclosure issue.
- Keep this layer as `research_pit_validation`, not `platform_replication`.

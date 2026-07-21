# Basket Formal Validation Report

- Status: `formal_validation_completed_not_acceptance`
- Panel rows: `4089`
- Signal dates: `19`
- Basket return: `0.7006712185`
- Same-pool benchmark return: `0.5300706122`

## Evidence

- The basket uses PIT-enriched sector panels and real JoinQuant daily open/close prices in the local daily simulation.
- IC/RankIC is computed on the full candidate panel after required low-vol fields are available, not only on selected holdings.
- Rolling validation is reported by calendar year; weak-year rows are diagnostics, not tuning permission.

## Weak Years

- `2021`: strategy `-0.01285624`, benchmark `-0.007352880772`, max drawdown `0.09309874`
- `2026`: strategy `0.03383952429`, benchmark `0.128638142`, max drawdown `0.07451387256`

## Governance

Basket formal validation is evidence for PM review only. The 2021-2026 window remains platform-confirmation context and is not accepted-strategy proof.

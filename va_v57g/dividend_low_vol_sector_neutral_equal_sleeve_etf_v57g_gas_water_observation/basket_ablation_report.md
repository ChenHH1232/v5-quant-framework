# Basket Ablation Report

- Status: `basket_ablation_completed_not_acceptance`
- Cases: `15`
- Common window: `2021-10-08` to `2026-05-29`

## Base

- Strategy return: `0.7006712185`
- Excess return: `0.1706006063`
- Max drawdown: `0.1214919466`
- Common-window strategy return: `0.7006712185`

## Top Cases, Raw Window

- `sector_cap_100`: return `0.7542516034`, excess `0.2241809913`, max drawdown `0.1726577215`, diff vs base `0.0535803849`
- `low_vol_ocf_only`: return `0.7146243046`, excess `0.1845536924`, max drawdown `0.1145611613`, diff vs base `0.0139530861`
- `base`: return `0.7006712185`, excess `0.1706006063`, max drawdown `0.1214919466`, diff vs base `0`
- `drop_div_yield`: return `0.7006712185`, excess `0.1706006063`, max drawdown `0.1214919466`, diff vs base `0`
- `drop_fcf_yield`: return `0.7006712185`, excess `0.1706006063`, max drawdown `0.1214919466`, diff vs base `0`
- `sector_cap_25`: return `0.7006712185`, excess `0.1706006063`, max drawdown `0.1214919466`, diff vs base `0`

## Top Cases, Common Window

- `sector_cap_100`: return `0.7542516034`, excess `0.2241809913`, max drawdown `0.1726577215`, diff vs base `0.0535803849`
- `low_vol_ocf_only`: return `0.7146243046`, excess `0.1845536924`, max drawdown `0.1145611613`, diff vs base `0.0139530861`
- `base`: return `0.7006712185`, excess `0.1706006063`, max drawdown `0.1214919466`, diff vs base `0`
- `drop_div_yield`: return `0.7006712185`, excess `0.1706006063`, max drawdown `0.1214919466`, diff vs base `0`
- `drop_fcf_yield`: return `0.7006712185`, excess `0.1706006063`, max drawdown `0.1214919466`, diff vs base `0`
- `sector_cap_25`: return `0.7006712185`, excess `0.1706006063`, max drawdown `0.1214919466`, diff vs base `0`

## Governance

Ablation re-runs basket construction and daily simulation. Use common-window metrics for factor decisions. It is still platform-confirmation evidence, not accepted-strategy proof.

# V57g Gas/Water Observation Basket PM Decision

Date: 2026-07-21

## Decision

V57g is recorded as an enhanced ETF observation basket, not a replacement for V57f.

The current main enhanced ETF candidate remains `dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f`. V57g adds `gas_water_operators` as an observable sleeve after V59b repaired PIT coverage and local daily simulation passed, but the basket-level result is weaker than V57f and therefore should not be promoted.

## Evidence

- Config: `config/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57g_gas_water_observation.json`
- Basket signals: `validation_formal_v57g_gas_water_observation_basket_constructor/basket_rebalance_signals.csv`
- Local daily simulation: `local_daily_backtests_v57g_gas_water_observation_etf/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57g_gas_water_observation/summary.json`
- Formal validation: `validation_formal_v57g_gas_water_observation_basket/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57g_gas_water_observation/basket_formal_validation_summary.json`
- Overfit audit: `overfit_audits_v57g_gas_water_observation_basket/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57g_gas_water_observation/overfit_audit_summary.json`
- Ablation: `va_v57g/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57g_gas_water_observation/basket_ablation_summary.json`
- PM gate: `pm_gate_packets_v57g_gas_water_observation/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57g_gas_water_observation/basket_pm_gate_summary.json`

## Result Snapshot

- Local return: 70.07%
- Same-pool benchmark return: 53.01%
- Excess return: 17.06%
- Annualized return: 12.63%
- Max drawdown: 12.15%
- Rebalance order health: 19/19 normal ordered
- First order date: 2021-10-08
- Dividend events: 130
- Overfit audit: 0 blockers, 1 governance review item

## Comparison With V57f

V57f remains stronger:

- V57f local return: 81.42%
- V57f excess return: 30.40%
- V57f max drawdown: 11.75%

V57g adds diversification breadth, but it reduces return and excess return while slightly increasing drawdown. This means gas/water should remain an observation sleeve, not a promoted ETF sleeve.

## Factor Read

The evidence still supports the current V5 basket research line:

- OCF remains the strongest economic anchor.
- Low volatility and trailing drawdown remain useful risk controls.
- Low PB contributes, but should not become the narrative center.
- Dividend yield remains a support variable, not the main factor.
- FCF remains disabled until capex quality and PIT coverage gates pass.

## Open Review Items

- 2021 and 2026 remain weak or underperforming years and should be monitored.
- Some ablation cases are blocked by tool/config edge cases and should not be over-interpreted.
- 2021-2026 remains platform-confirmation context, not clean out-of-sample acceptance evidence.
- No actual JoinQuant platform replication is planned because the user deferred platform testing.

## Next Gate

Keep V57f as the main enhanced ETF candidate.

Keep V57g as an observation basket and wait for a clean future forward signal window. Do not tune the gas/water sleeve by return.

# V5.8b Oil / Gas OCF-Led Low-Vol Value PM Decision V1

Date: 2026-07-20

Owner:

```text
Project Manager Agent
```

Layer:

```text
research_pit_validation
```

## PM Decision

V5.8b has opened and completed research PIT validation.

It is not approved for Engineering handoff.

Current status:

```text
research_pit_validation_completed
pit_leakage_audit_passed
ocf_signal_confirmed
composite_hypothesis_not_promoted
not_engineering_handoff
```

## Why V5.8b Was Tested

V5.8a showed:

```text
OCF-only baseline was stronger than the first composite.
Dividend was weak as a standalone signal.
FCF remained diagnostic.
Low-vol had useful RankIC but weak return spread.
```

So V5.8b tested an OCF-led hypothesis:

```text
operating cash-flow yield as the primary signal
low-volatility as support
PB / PE as valuation discipline
dividend / FCF / capex as diagnostics
```

## Validation Evidence

Inputs:

```text
knowledge/research_agent/factor_theory/oil_gas_v58b_ocf_led_hypothesis.md
examples/oil_gas_ocf_low_vol_value_v58b_strategy.json
数据库/processed/oil_gas_low_vol_panel_v58a/oil_gas_ocf_dividend_cycle_probe_v58a/panel_with_low_vol.csv
```

Outputs:

```text
validation_formal_v58b_oil_gas/oil_gas_ocf_low_vol_value_v58b/formal_validation_summary.json
validation_formal_v58b_oil_gas/oil_gas_ocf_low_vol_value_v58b/formal_validation_report.md
```

## Result Summary

Baseline results:

| Case | Cumulative Return | Positive Ratio |
| --- | ---: | ---: |
| equal-weight oil/gas pool | 39.26% | 61.11% |
| high OCF yield top8 | 80.38% | 72.22% |
| low-vol top8 | 47.41% | 72.22% |
| high OCF with low-vol top-half | 25.06% | 66.67% |
| OCF + low-vol + value composite top8 | 46.68% | 66.67% |
| high-dividend diagnostic top8 | 16.51% | 61.11% |

Rolling validation:

| Year | Cumulative Return | PM Read |
| --- | ---: | --- |
| 2024 | -1.31% | weak |
| 2025 | 33.99% | strong |
| 2026 | -4.47% | still unresolved |

Key factor evidence:

| Factor | Mean IC | Mean RankIC | PM Read |
| --- | ---: | ---: | --- |
| operating_cash_flow_yield | 0.0919 | 0.1111 | confirmed as the main research signal |
| low_vol_score | 0.0552 | 0.1191 | useful support, not enough as a hard filter |
| low_price_to_book | 0.0711 | 0.0994 | mild valuation support |
| pe_ratio | 0.0912 | 0.0931 | useful but cyclical |
| dividend_yield | 0.0569 | 0.0314 | diagnostic only |
| free_cash_flow_yield | 0.0424 | 0.0712 | diagnostic only |
| capex_burden | -0.0124 | 0.0311 | not a positive scoring variable |

## PM Interpretation

V5.8b confirms that OCF is the cleanest oil/gas research signal in the current data packet.

However, V5.8b also confirms that adding low-vol and valuation into a composite does not beat the OCF-only baseline in this window. The low-vol top-half filter also weakens the OCF signal.

Therefore:

```text
V5.8b is useful research evidence, not an engineering candidate.
```

## Decision

Do not promote V5.8b.

Allowed next action:

```text
Run focused diagnostics on why OCF-only works and why composite / low-vol filter dilutes it.
```

Blocked actions:

```text
no JoinQuant code
no local daily simulation
no platform replication
no V5.7f basket inclusion
no accepted-strategy status
```

## Required Before Any Future Promotion

1. Explain whether OCF-only is economically persistent or a 2021-2026 commodity-cycle artifact.
2. Add state-bucket diagnostics by crude / refining spread / gas proxy states.
3. Replace proxy state sources with official or reviewed spot / spread / tariff sources before formal promotion.
4. Review annual-report segment exposure.
5. Repair cash dividends.
6. Resolve 2026 failure mode.

## PM Status

```text
research_signal_confirmed_but_strategy_not_promoted
return_to_quant_diagnostics_or_research_data_repair
```

Historical performance alone is never sufficient evidence for accepting a strategy.

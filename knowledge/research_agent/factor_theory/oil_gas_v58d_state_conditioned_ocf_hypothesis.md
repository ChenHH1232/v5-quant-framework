# Oil / Gas State-Conditioned OCF Hypothesis V5.8d

Date: 2026-07-20

Owner: Research Agent

Status: `research_hypothesis_ready_for_quant_validation`

## Research Reset From V5.8c

V5.8c showed that OCF is not a universally stable oil / gas signal.

Evidence summary:

- OCF is stronger than equal weight across the full diagnostic panel.
- OCF is strongest in weak crude / weak bitumen proxy states.
- OCF weakens or turns negative in strong crude proxy states.
- Refining-spread proxy buckets show a different pattern: OCF works better when refining spread is mid or strong.
- Low PE often looks strong, but this may be a cyclical earnings artifact.

## Hypothesis

Oil / gas OCF yield should be used as a cash-generation signal only when the cycle state makes OCF economically interpretable.

When commodity-price states are weak, high OCF yield can identify resilient operators that still generate cash under stress.

When refining-spread states are supportive, high OCF yield can identify refiners / integrated operators with current cash conversion strength.

When crude or bitumen states are strong, raw OCF may reflect cyclical peak cash flow rather than sustainable value. In that state, the model should de-emphasize OCF and fall back to low-volatility defense.

## Factor Roles

| Factor | Role | Direction |
| --- | --- | --- |
| `state_conditioned_ocf_score` | Primary, active only when state supports OCF interpretation | higher is better |
| `cycle_defensive_low_vol_score` | Defensive fallback under warmup or strong commodity states | higher is better |
| `cycle_low_pe_diagnostic_score` | Diagnostic only for refining-spread state; not a main score | lower is better |
| `low_price_to_book` | Diagnostic valuation discipline | lower is better |
| `dividend_yield` | Diagnostic shareholder-return support | higher is better |

## PIT Rule

State buckets must be computed with expanding history strictly before each trade date.

No full-sample thresholds are allowed.

## Quant Test Request

Quant Validation Agent should run:

- baseline comparison against equal-weight oil / gas pool
- raw OCF baseline
- low-vol baseline
- state-conditioned OCF baseline
- state-conditioned OCF + defensive low-vol composite
- IC / RankIC
- rolling validation
- ablation
- robustness across selection count and weight scaling
- weak-year review for 2022, 2024 and 2026

## Non-Promotion Rule

Even if V5.8d improves the research result, it cannot enter Engineering handoff until source repair is complete:

- official / reviewed oil, gas, spread and tariff state sources
- reviewed annual-report business exposure
- cash dividend events
- 2026 failure explanation

Historical performance alone is never sufficient evidence for accepting a strategy.

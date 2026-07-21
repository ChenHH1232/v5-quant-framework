# V5a.2 Value, Momentum And Mean-Reversion Framework

Status: research knowledge base  
Date: 2026-07-21  
Applies to: dividend low-volatility and operating/free-cash-flow enhanced ETF roadmap  
Not a strategy acceptance document.

## One-Line PM Conclusion

For V5's enhanced ETF path, the strongest default theory is not "low PB + FCF" as a universal story. The better mainline is:

OCF / cash-flow quality + dividend sustainability + low volatility, with FCF, valuation and momentum added only when the sector's business model makes them economically clean and PIT-testable.

## Theory Layer

| Theory | Core Claim | V5 Translation | Main Risk | Required Validation |
| --- | --- | --- | --- | --- |
| Value investing | Cheap securities can earn a premium, especially when price is low relative to durable fundamentals. | Use low valuation only after checking accounting quality, dividend sustainability and industry capital intensity. | Low valuation can be distress, governance or industry decline. | Baseline, IC/RankIC, rolling, value-trap ablation, failure-year review |
| Profitability / quality | Durable profitability and quality can explain returns beyond simple cheapness. | Prefer OCF, gross profitability, ROE stability, receivables and debt quality over single-period net profit growth. | Accounting comparability varies heavily by sector. | PIT field audit, factor stability, cross-sector normalization |
| Free cash flow | FCF yield can identify firms producing cash after capex. | Use FCF where maintenance vs growth capex is interpretable; otherwise keep OCF as primary and FCF as enhancement. | Heavy capex sectors can look weak during productive investment or strong when underinvesting. | Capex-quality gate, sector-specific adjustment, ablation |
| Momentum | Recent winners can continue over intermediate horizons and can diversify value. | Use as support / state variable, not default primary factor for dividend ETF unless it improves rolling evidence without turning into timing overfit. | Can conflict with value and increase turnover. | Horizon grid, turnover audit, buy/sell timing perturbation |
| Mean reversion | Overreaction can create long-horizon reversal opportunities. | Use only with value-trap and balance-sheet guards; do not buy losers just because they fell. | Falling fundamentals can make "reversion" a trap. | Weak-year analysis, guard ablation, drawdown state audit |
| Low volatility | Low-beta / low-volatility assets may outperform on a risk-adjusted basis due to leverage aversion and benchmark constraints. | Low volatility is a core defensive sleeve filter and cross-sector basket stabilizer. | Sector bet, crowding and rate sensitivity. | 60/120/252d vol, drawdown, beta, sector-neutral and sector-aware tests |

## Research Agent Rules

1. Value must be tied to a durable economic asset or cash-flow stream.
2. Low PB alone is never enough; it needs asset-quality, balance-sheet or business-model interpretation.
3. OCF is the cross-sector starting point because it is less sensitive than FCF to capex classification.
4. FCF can become formal only after the sector passes the capex-quality gate.
5. Momentum is allowed only as a timing/support hypothesis and must be tested under turnover and robustness constraints.
6. Mean reversion must include an ex-ante reason why the bad news is temporary.
7. Dividend yield must be paired with dividend coverage, payout reasonableness and business stability.
8. Any factor that works only in one hand-picked period returns to Research Agent.

## Quant Validation Handoff

Every candidate derived from this framework must run:

- PIT visibility audit.
- Single-factor baseline.
- IC and RankIC.
- Rolling validation.
- Ablation.
- Robustness and random perturbation.
- Failure-year analysis.
- Sector-neutral and sector-aware comparison when the basket crosses industries.

## Sector Implications

| Sector Type | Default Theory Priority | FCF Status | Momentum / Mean Reversion Status |
| --- | --- | --- | --- |
| Regulated utilities, gas/water, highways | Dividend sustainability, OCF stability, low volatility, operating-state guard | Conditional enhancement | Mostly defensive state variable |
| Telecom operators | OCF stability, capex-cycle-aware FCF, dividend policy | Conditional, capex-heavy | Observation only due small sample |
| Consumer staples and home appliances | OCF, gross margin/profitability, inventory/receivables quality | More usable than heavy infrastructure sectors | Can test trend support |
| Pharma / medical services | Cash conversion, R&D/capex quality, regulatory risk | Must be adjusted for R&D/investment cycle | Momentum may reflect policy or product cycle |
| Energy / coal / oil-gas | OCF plus commodity state, not pure FCF | Blocked unless commodity and capex state is PIT | Mean reversion requires cycle-state data |
| Financials / insurance / banks | Sector-specific balance-sheet valuation, dividend sustainability, solvency/asset quality | Not directly comparable | Momentum only as market-state diagnostic |

## Core Sources

- Fama and French, 1992, "The Cross-Section of Expected Stock Returns": value and size cross-sectional evidence.
- Jegadeesh and Titman, 1993, "Returns to Buying Winners and Selling Losers": intermediate-horizon momentum evidence.
- De Bondt and Thaler, 1985, "Does the Stock Market Overreact?": long-horizon overreaction / reversal evidence.
- Asness, Moskowitz and Pedersen, 2013, "Value and Momentum Everywhere": value and momentum can coexist and diversify.
- Novy-Marx, 2013, "The Other Side of Value": profitability as a value-adjacent quality signal.
- Frazzini and Pedersen, "Betting Against Beta": low-beta anomaly and funding constraints.
- Asness, Frazzini and Pedersen, "Quality Minus Junk": quality characteristics include profitability, safety, growth and prudent management.


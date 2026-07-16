# Coal Core Factor Hypotheses

Date: 2026-07-16

Project:

```text
V5.2 Coal High-Dividend / Cycle-Value Process-Portability Test
```

Status:

```text
candidate_hypotheses_not_validated
```

## Module 1: Shareholder Return

### H1: Dividend Yield

- Intuition: mature coal assets can distribute cash when reinvestment needs are moderate.
- Formula: cash dividend per share / stock price, or vendor dividend yield if date-audited.
- Direction: higher is better.
- Failure mode: high yield appears because price has fallen ahead of dividend cuts.
- Required data: dividend announcement date, ex-date, payment date, price.
- Role: alpha candidate, must pass cycle-state robustness.

### H2: Dividend Coverage

- Intuition: dividend is more durable when covered by OCF or FCF.
- Formula: cash dividend / operating cash flow or cash dividend / free cash flow.
- Direction: lower payout burden is better after controlling for yield.
- Failure mode: FCF is noisy due to lumpy capex.
- Required data: dividend, OCF, capex.
- Role: support or filter candidate.

## Module 2: Valuation

### H3: Low PB

- Intuition: coal reserves and mine assets may be underpriced when market pessimism is excessive.
- Formula: PB ratio.
- Direction: lower is better.
- Failure mode: low PB reflects impaired assets, policy risk, or weak reserves.
- Required data: market cap, net assets.
- Role: alpha candidate.

### H4: Low PE

- Intuition: low PE may capture cheap cyclical earnings.
- Formula: PE ratio.
- Direction: lower is better.
- Failure mode: PE is lowest at the profit-cycle peak.
- Required data: price, net profit.
- Role: exploratory; must be tested with coal-price state.

### H5: Cash-Flow Yield

- Intuition: cash earnings may be more reliable than accounting PE in commodity cycles.
- Formula: operating cash flow / market cap.
- Direction: higher is better.
- Failure mode: working-capital swings distort OCF.
- Required data: OCF, market cap.
- Role: alpha candidate.

## Module 3: Cycle Profitability

### H6: Profit Growth State

- Intuition: recent profit growth may reflect coal cycle strength.
- Formula: net profit YoY or revenue YoY.
- Direction: ambiguous; high growth may be strong state or peak risk.
- Failure mode: chasing peak-cycle earnings.
- Required data: financial statements, announcement date.
- Role: state or support candidate, not standalone alpha initially.

### H7: Margin Resilience

- Intuition: margin stability may distinguish cost leaders from weaker miners.
- Formula: gross margin or operating margin change.
- Direction: higher and more stable is better.
- Failure mode: margin reflects temporary coal price rather than company quality.
- Required data: revenue, cost, profit.
- Role: support candidate.

## Module 4: Cash Flow And Capex

### H8: OCF / Net Profit

- Intuition: cash conversion helps identify accounting-profit traps.
- Formula: operating cash flow / net profit.
- Direction: higher is better, with outlier controls.
- Failure mode: working-capital timing creates false signals.
- Required data: OCF, net profit.
- Role: quality support candidate.

### H9: Capex Burden

- Intuition: high capex can reduce distributable cash and expose reserve or safety spending pressure.
- Formula: capex / operating cash flow or capex / revenue.
- Direction: lower burden is better after controlling for asset life.
- Failure mode: productive capex may improve future output.
- Required data: cash-flow statement and notes if available.
- Role: filter or risk-control candidate.

## Module 5: Leverage And Solvency

### H10: Asset-Liability Ratio

- Intuition: lower leverage can reduce down-cycle risk.
- Formula: total liabilities / total assets.
- Direction: lower is better as risk control.
- Failure mode: overly penalizes integrated SOEs with stable financing.
- Required data: balance sheet.
- Role: risk-control candidate.

### H11: Interest Coverage

- Intuition: companies that cover interest comfortably should survive down cycles better.
- Formula: EBIT / interest expense, or operating profit / finance expense proxy.
- Direction: higher is better.
- Failure mode: finance expense definitions may differ.
- Required data: income statement.
- Role: support or filter candidate.

## Module 6: External Coal-Cycle State

### H12: Thermal Coal Price State

- Intuition: thermal coal prices affect earnings for thermal coal producers and coal-power integrated firms.
- Formula: latest visible thermal coal price YoY / level / percentile.
- Direction: not directly higher-is-better; used as state.
- Failure mode: futures or current spot data leaks future information.
- Required data: source publication date, visible date.
- Role: state variable.

### H13: Coking Coal Price State

- Intuition: coking coal prices affect steel-chain coal producers differently from thermal coal producers.
- Formula: latest visible coking coal price YoY / level / percentile.
- Direction: state variable.
- Failure mode: applying coking coal state to thermal coal producers without subgroup split.
- Required data: source publication date, visible date.
- Role: state variable.

### H14: Inventory / Output State

- Intuition: inventory and production help distinguish tight supply from weak demand.
- Formula: inventory days, port inventory, or raw coal output YoY.
- Direction: context-dependent.
- Failure mode: monthly data revisions and publication lag.
- Required data: official or auditable source with visible date.
- Role: state variable.

### H15: Coal-Power Spread

- Intuition: coal-power margin affects power-integrated coal companies and power demand pressure.
- Formula: electricity price or tariff proxy minus coal cost proxy.
- Direction: higher spread supports power-integrated margins, but may not benefit pure coal producers.
- Failure mode: poorly defined proxy or mixing upstream/downstream economics.
- Required data: coal price, power price/tariff proxy, publication dates.
- Role: subgroup state variable.

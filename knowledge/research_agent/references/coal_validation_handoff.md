# Coal Validation Handoff

Date: 2026-07-16

From:

Research Agent

To:

Quant Validation Agent

Project:

```text
V5.2 Coal High-Dividend / Cycle-Value Process-Portability Test
```

## Validation Objective

Test whether coal-sector dividend, valuation, cash-flow, leverage, and external cycle-state hypotheses have PIT-valid statistical evidence.

Do not optimize on platform backtest performance.

## Required Tests

### 1. PIT Leakage Audit

Audit:

- financial announcement date;
- dividend announcement / ex-date / payment date separation;
- external state visible date;
- industry membership visible date;
- mixed-business classification date;
- no full-sample normalization.

### 2. Baselines

Run:

- equal-weight coal universe;
- high dividend yield top N;
- low PB top N;
- high operating-cash-flow-yield top N;
- high free-cash-flow-yield top N if coverage passes;
- state-conditioned baseline;
- core-coal-only baseline.

### 3. IC / RankIC

Run single-factor IC and RankIC for:

- dividend yield;
- low PB;
- low PE;
- operating cash-flow yield;
- free-cash-flow yield if available;
- profit growth YoY;
- OCF / net profit;
- capex burden;
- asset-liability ratio;
- interest coverage;
- coal price state;
- coal-power spread state.

### 4. Rolling Validation

Use rolling windows. Report whether evidence survives outside one coal boom or bust.

### 5. Ablation

Remove one module at a time:

- shareholder return;
- valuation;
- cycle profitability;
- cash flow and capex;
- leverage;
- external state.

### 6. Robustness

Required robustness checks:

- selection count 5 / 8 / 10 / 12;
- state threshold perturbation;
- factor-weight perturbation;
- excluding mixed coal-chemical companies;
- thermal coal vs coking coal subgroup split;
- rebalance month perturbation;
- random window stress;
- small execution-date shift after formal candidate approval.

## Stop Rules

Stop and report to PM if:

- external state lacks visible-date evidence;
- the only good result comes from one coal-price boom;
- high dividend works only at cycle peak and fails after coal-price decline;
- mixed-company inclusion changes the sign of evidence;
- platform-window tuning appears;
- any factor is accepted only because historical return is high.

## Output Packet

Quant Validation Agent must produce:

- leakage audit report;
- baseline report;
- IC / RankIC report;
- rolling report;
- ablation report;
- robustness report;
- PM recommendation:
  - `reject`;
  - `revise_research`;
  - `formal_strategy_candidate_ready`.

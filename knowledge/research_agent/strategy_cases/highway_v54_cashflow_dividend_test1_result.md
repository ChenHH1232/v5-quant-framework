# Highway V5.4 Test-1 Research Result

Date: 2026-07-18

## Research Question

Can highway operators support a dividend + free-cash-flow enhanced strategy that is better than simple high dividend?

## Result

Not yet.

The highway sector is promising for the long-term V5 objective of building a dividend, low-volatility and cash-flow enhanced basket. But in Test-1, the strongest evidence is simple dividend yield.

## What Worked

- The PIT highway universe can be built from JoinQuant HY03160 after 2021-12-13.
- The sample has 20 names and 18 quarterly rebalance dates from 2022 to 2026.
- Dividend yield has strong positive evidence:
  - Mean IC: 0.2225
  - Mean RankIC: 0.2298
  - Positive IC ratio: 72.22%
  - High-dividend top8 return: 78.84%

## What Failed

- Free-cash-flow yield did not add alpha.
- FCF dividend support did not add alpha.
- The composite underperformed the high-dividend baseline.
- 2026 remains weak.

## Research Interpretation

Highway operators may be valued mainly as dividend yield assets in this window.

Cash-flow and leverage fields should not be discarded, but they should initially be treated as:

```text
risk diagnostics / value-trap filters / failure-mode explainers
```

not as positive alpha score inputs.

## Next Hypothesis

V5.4b should test:

```text
Highway High Dividend With Cash-Flow Risk Diagnostics
```

Research Agent must additionally investigate:

- toll road concession maturity;
- toll policy and tariff adjustment;
- traffic volume / toll revenue trend;
- capex cycle and road expansion burden;
- whether listed companies have non-highway business contamination.

## PM Rule

Do not send V5.4 Test-1 to Engineering Agent.

Return to Research Agent and Quant Validation Agent for V5.4b.

# V5c Overlay Research Framework

## One-Line Principle

V5c should study simple portfolio-level risk overlays for V57f without changing V57f's core stock selection or sleeve design.

## Research Stack

1. Knowledge source collection.
2. Theory and practitioner cards.
3. PIT data requirement matrix.
4. Hypothesis library.
5. Quant handoff packet.
6. Only after PM approval: PIT-safe formal validation.

## Overlay Families

### Portfolio Defense

Purpose: reduce equity exposure when portfolio or market-level risk becomes visibly stressed.

Candidate states:

- portfolio drawdown from prior peak;
- broad-market long-term trend;
- realized volatility;
- market breadth, if PIT-safe;
- dividend/low-vol crowding or valuation heat, if PIT-safe.

### Profit Taking / Peak Trimming

V5c should avoid stock-level short-term profit taking. For ETF-like assets, sleeve-level rebalancing is cleaner:

- trim sleeve drift back to target;
- avoid letting one sleeve dominate risk;
- document whether trimming is periodic, threshold-based or risk-budget based.

### Rebalancing

Candidate mechanisms:

- fixed calendar rebalancing;
- sleeve drift bands;
- volatility or risk-budget rebalancing;
- cash restoration after defense.

### Cash Management

Every defensive cut must specify:

- target cash weight;
- whether cash is actual cash or a pre-approved conservative asset;
- cash drag measurement;
- restoration rule;
- difference between intentional defensive cash and failed-order cash.

### Dividend / Low-Vol Special Risk

V5c must explicitly watch:

- interest-rate stress;
- dividend traps;
- payout deterioration;
- valuation heat;
- crowded defensive trades;
- defensive underperformance in bull markets.

## Evidence Conversion Rules

- A/B evidence can support a research conclusion if source and date are recorded.
- C evidence can support framework language only.
- D evidence can generate hypotheses only.
- No source can directly provide V5c thresholds.
- All Quant handoff items require PIT fields and visible-date policy.

## Research Agent Output Standard

Every new card must include:

- source title;
- author or institution;
- publication date;
- source location;
- key claim;
- evidence type;
- confidence;
- PIT safety;
- applicable boundary;
- whether it can become a Quant hypothesis.

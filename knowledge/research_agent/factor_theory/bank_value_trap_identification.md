# Bank Stock Value Trap Identification

## Type

Research Caveat / Factor Design

## Summary

In bank stocks, low valuation can represent either mispricing or rational fear of future book-value impairment. A value strategy must identify value traps before ranking cheap banks.

## What Is A Bank Value Trap?

A bank value trap is a bank that appears cheap on P/B, P/E, or dividend yield, but whose future equity value may be impaired by credit losses, weak capital, declining profitability, poor funding quality, or unsustainable dividends.

## Common Value Trap Signals

### Asset Quality Deterioration

Observable indicators:

- rising NPL ratio;
- rising special mention loans;
- rising overdue loans;
- rising credit cost;
- rapid loan growth before NPL recognition.

Research hypothesis:

The speed of deterioration may be more predictive than the absolute level.

### Weak Provision Buffer

Observable indicators:

- falling provision coverage ratio;
- low loan-loss reserve ratio;
- provisions not keeping up with NPL growth.

Research hypothesis:

Low-PB banks with weak provision buffers underperform during credit stress.

### Capital Pressure

Observable indicators:

- declining core tier 1 capital adequacy ratio;
- fast risk-weighted asset growth;
- capital ratio close to regulatory minimum;
- equity issuance pressure.

Research hypothesis:

Capital pressure limits dividend capacity and increases dilution risk.

### Unsustainable Dividend Yield

Observable indicators:

- high dividend yield with declining ROE;
- payout ratio too high relative to capital generation;
- dividend maintained by one-off earnings;
- dividend yield high because price collapsed.

Research hypothesis:

Dividend yield must be conditioned on capital adequacy and profitability stability.

### Franchise Deterioration

Observable indicators:

- falling net interest margin;
- weak deposit growth;
- rising funding cost;
- fee income deterioration;
- cost-income ratio worsening.

Research hypothesis:

Banks with weakening franchise quality deserve lower P/B even when current book value appears intact.

## Candidate Guard Design

Do not admit a low-valuation bank into the final portfolio unless at least one quality condition is met:

- asset quality above universe median;
- provision buffer above universe median;
- capital adequacy above regulatory and universe thresholds;
- ROE stability above minimum threshold;
- no rapid deterioration in NPL or provision coverage.

## Rejection Criteria

Reject the value-trap guard if:

- it removes winners without reducing drawdown;
- it only works in one period;
- it relies on unavailable future disclosure;
- it is too strict and leaves the strategy mostly in cash;
- it does not improve low-PB factor behavior on common samples.

## Research Implication

The Research Agent should treat value-trap detection as part of the financial thesis, not as a post-backtest filter.

## Last Updated

2026-07-15

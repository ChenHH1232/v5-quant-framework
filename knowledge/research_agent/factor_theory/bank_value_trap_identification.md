# Bank Stock Value Trap Identification

## Type

Citation-Backed Research Caveat / Factor Design

## Summary

In bank stocks, low valuation can represent either mispricing or rational fear of future book-value impairment. A value strategy must identify value traps before ranking cheap banks.

Evidence level: mixed `academic_evidence`, `regulatory_definition`, `industry_disclosure`, `V5_internal_finding`, and `hypothesis_only`. Value-trap guard rules are not accepted factors until validated. See [Bank Sector Research References](../references/bank_sector_references.md).

## What Is A Bank Value Trap?

A bank value trap is a bank that appears cheap on P/B, P/E, or dividend yield, but whose future equity value may be impaired by credit losses, weak capital, declining profitability, poor funding quality, or unsustainable dividends.

Evidence trail:

- `academic_evidence`: distress-risk literature warns that cheap or distressed equities need not earn a positive premium.
- `academic_evidence`: financial-services valuation connects P/B to ROE, cost of equity and book-value credibility.
- `hypothesis_only`: bank-specific trap signals must be tested on China A-share bank data.

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

Evidence level: `regulatory_definition` for indicators; `hypothesis_only` for predictive use.

### Weak Provision Buffer

Observable indicators:

- falling provision coverage ratio;
- low loan-loss reserve ratio;
- provisions not keeping up with NPL growth.

Research hypothesis:

Low-PB banks with weak provision buffers underperform during credit stress.

Evidence level: `regulatory_definition` for provision variables; `hypothesis_only` for return and drawdown effects.

### Capital Pressure

Observable indicators:

- declining core tier 1 capital adequacy ratio;
- fast risk-weighted asset growth;
- capital ratio close to regulatory minimum;
- equity issuance pressure.

Research hypothesis:

Capital pressure limits dividend capacity and increases dilution risk.

Evidence level: `regulatory_definition` for capital ratios; `hypothesis_only` for dilution and stock-return effects.

### Unsustainable Dividend Yield

Observable indicators:

- high dividend yield with declining ROE;
- payout ratio too high relative to capital generation;
- dividend maintained by one-off earnings;
- dividend yield high because price collapsed.

Research hypothesis:

Dividend yield must be conditioned on capital adequacy and profitability stability.

Evidence level: `industry_disclosure` for dividends and payout ratio; `hypothesis_only` for dividend-yield factor behavior.

### Franchise Deterioration

Observable indicators:

- falling net interest margin;
- weak deposit growth;
- rising funding cost;
- fee income deterioration;
- cost-income ratio worsening.

Research hypothesis:

Banks with weakening franchise quality deserve lower P/B even when current book value appears intact.

Evidence level: `academic_evidence` for deposit-franchise logic; `industry_disclosure` for bank-reported NIM/deposit/funding variables; `hypothesis_only` for V5 factor use.

## Candidate Guard Design

Candidate rule for validation, not an accepted rule:

Do not admit a low-valuation bank into the final portfolio unless at least one quality condition is met:

- asset quality above universe median;
- provision buffer above universe median;
- capital adequacy above regulatory and universe thresholds;
- ROE stability above minimum threshold;
- no rapid deterioration in NPL or provision coverage.

Evidence level: `hypothesis_only`. Thresholds must be set before validation or learned only inside proper rolling training folds.

## Rejection Criteria

Reject the value-trap guard if:

- it removes winners without reducing drawdown;
- it only works in one period;
- it relies on unavailable future disclosure;
- it is too strict and leaves the strategy mostly in cash;
- it does not improve low-PB factor behavior on common samples.

## Research Implication

The Research Agent should treat value-trap detection as part of the financial thesis, not as a post-backtest filter.

## Research Agent Usage Notes

- Use this card to design guard hypotheses and failure modes.
- Do not present a guard as accepted because it improves 2021-05 to 2026-05 results.
- Every guard must be tested against a low-PB baseline on a common sample.
- Quant Validation Agent must separately report return impact, drawdown impact, turnover impact, coverage loss and stress-period behavior.

## References

- [Bank Sector Research References](../references/bank_sector_references.md)
- Campbell, Hilscher and Szilagyi distress-risk evidence.
- Basel/NFRA capital and risk indicator definitions.
- Listed-bank annual reports and dividend announcements.
- V5 platform-confirmation governance.

## Last Updated

2026-07-15

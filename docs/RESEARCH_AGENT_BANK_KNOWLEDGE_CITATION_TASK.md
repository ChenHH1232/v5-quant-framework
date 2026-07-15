# Research Agent Task: Bank Domain Knowledge With Citations

## Objective

Upgrade the Research Agent banking knowledge cards from internal hypothesis notes into citation-backed research knowledge. The goal is not to prove that Bank Value 15Y is effective, but to strengthen the financial reasoning and evidence trail behind future bank-sector factor research.

## Scope

Research Agent should work on these four knowledge cards:

- `knowledge/research_agent/factor_theory/bank_value_investing_framework.md`
- `knowledge/research_agent/factor_theory/bank_core_factor_hypotheses.md`
- `knowledge/research_agent/factor_theory/bank_value_trap_identification.md`
- `knowledge/research_agent/factor_theory/bank_defensive_macro_state_variables.md`

Research Agent may add a dedicated references file if it improves maintainability:

- `knowledge/research_agent/references/bank_sector_references.md`

## Required Source Standards

Use primary or high-quality sources where possible:

- regulatory sources: Basel Committee, central banks, financial regulators, stock exchange rules;
- company disclosure sources: listed bank annual reports, interim reports, dividend announcements;
- academic sources: peer-reviewed papers or well-known working papers for value, profitability, bank risk, and factor validation;
- data methodology sources: JoinQuant documentation, exchange data definitions, index or ETF methodology documents;
- macro sources: PBOC, NBS, NFRA, CSRC, IMF, BIS, World Bank, or similarly authoritative bodies.

Avoid using uncited blog posts, social media, promotional material, or backtest-only articles as evidence. If a weaker source is useful for context, label it as context only and do not use it as proof.

## Step Table

| Step | Research Task | Output | Acceptance Standard |
| --- | --- | --- | --- |
| 1 | Read the four current bank knowledge cards and identify every claim that needs external support. | Claim list grouped by card. | Claims are separated into financial theory, accounting/regulatory definition, empirical evidence, and V5 internal governance. |
| 2 | Build a source map for bank valuation. Focus on P/B, ROE, book value, dividend yield, and cost of equity. | Source notes for valuation logic. | At least one source supports why bank valuation often uses P/B or book-based metrics, and at least one source explains limits or risks of book value. |
| 3 | Build a source map for bank balance-sheet quality. Focus on NPL, provision coverage, credit cost, capital adequacy, and funding structure. | Source notes for asset quality and capital strength. | Sources distinguish between observed accounting ratios and forward-looking credit-risk interpretation. |
| 4 | Build a source map for dividend sustainability. Focus on dividend payout, capital constraints, profitability, and cash dividend treatment. | Source notes for dividend factor logic. | The card must avoid treating high dividend yield as automatically positive. |
| 5 | Build a source map for value traps. Focus on low P/B combined with deteriorating asset quality, weak capital, declining ROE, or unsustainable dividend yield. | Value-trap evidence notes. | Each value-trap signal is phrased as a hypothesis requiring validation, not as an accepted rule. |
| 6 | Build a source map for defensive and macro state variables. Focus on bank-sector trend, credit cycle, interest rate/NIM state, liquidity, and real estate or macro stress. | Defensive macro notes. | Defensive variables are clearly labeled as risk-control candidates, not alpha evidence. |
| 7 | Add a `References` section to each card, or create a shared reference card and link to it. | Updated markdown files. | Each major claim family has a citation trail. Links should be stable and readable. |
| 8 | Add `Evidence Level` labels where useful. Suggested labels: `regulatory_definition`, `academic_evidence`, `industry_disclosure`, `V5_internal_finding`, `hypothesis_only`. | Updated knowledge cards. | A future agent can tell whether a statement is sourced fact, empirical literature, internal finding, or untested hypothesis. |
| 9 | Add a `Research Agent Usage Notes` section to each card. | Updated usage notes. | Notes explain when Research Agent may use the card and when Quant Validation Agent must verify it. |
| 10 | Update `knowledge/research_agent/INDEX.md`. | Updated index. | Index includes any new references file and marks the four cards as citation-backed once complete. |
| 11 | Run a hygiene check for credentials and generated data. | Clean working tree diff. | No account, password, token, generated CSV, or raw data is added. |
| 12 | Summarize remaining gaps. | Short final report. | Gaps should separate missing sources from hypotheses that still require Quant Validation. |

## Rules

- Do not change strategy parameters.
- Do not claim a factor is accepted because of historical performance.
- Do not use 2021-05 to 2026-05 as a tuning or acceptance sample.
- Do not commit credentials, generated data, or raw backtest output.
- Keep the knowledge base reusable for future bank strategies, not only Bank Value 15Y.
- Use English file names and stable markdown structure.
- Chinese explanations are acceptable inside the task report if clearer for the user.

## Expected Final Deliverables

- Citation-backed updates to the four bank knowledge cards.
- Optional shared reference file under `knowledge/research_agent/references/`.
- Updated `knowledge/research_agent/INDEX.md`.
- Final summary covering:
  - sources added;
  - claims downgraded to hypothesis-only;
  - gaps that still need Quant Validation;
  - any source limitations.


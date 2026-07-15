# Bank Regulatory Definitions

Status: first-pass completed.

Evidence layer: `core_theory`

Scope: definitions and official context needed before Research Agent interprets bank valuation, profitability, asset quality, capital and dividend variables. This file is a definition layer, not a factor-validation result.

## Source Map

| Source id | Registered source | Access status | Evidence layer | Use in V5 |
| --- | --- | --- | --- | --- |
| `BIS_BASEL3_CAPITAL` | BIS / Basel Committee | `public_access` | `core_theory` | CET1, Tier 1, capital buffers, risk-weighted assets. |
| `NFRA_CAPITAL_RULES_2024` | NFRA / Commercial Bank Capital Management Measures | `public_access` | `core_theory` | China commercial-bank capital ratios and disclosure context. |
| `NFRA_SUPERVISORY_INDICATORS` | NFRA quarterly supervisory indicators | `public_access` | `core_theory` | Industry NPL, provision coverage, loan-loss reserve and capital adequacy context. |
| `PBOC_LPR` | PBOC / ChinaMoney LPR pages | `public_access` | `core_theory` | Loan pricing reference rate and rate-state variable context. |
| `CSRC_CASH_DIVIDEND_2023` | CSRC listed-company cash dividend guidance | `public_access` | `core_theory` | Dividend policy, disclosure and sustainability framing. |
| `SSE_CASH_DIVIDEND_RULES` | SSE dividend guidance and listing-rule material | `public_access` | `core_theory` | Listed-company dividend governance and disclosure timing. |
| `NBS_MACRO_DATA` | NBS data release and data portal | `public_access` / `manual_export_preferred` | `core_theory` | Macro state variables: GDP, CPI/PPI, fixed asset investment, real estate. |
| `CNINFO_DISCLOSURE` | CNINFO annual/interim reports | `manual_download_required` | `industry_research` | Bank-specific disclosure fields. Not an automated source in V5 without explicit dataset. |

## Core Definitions For Bank-Factor Research

### Price-to-book ratio and book equity

- Working V5 definition: `PB = market price or market capitalization / latest visible book equity per share or total equity`.
- Evidence layer: `core_theory` for accounting/valuation concept; `industry_research` for issuer-specific book equity from annual/interim reports.
- Point-in-time rule: the book-equity input must be visible by announcement date. A rebalance on date `t` may only use financial statements announced before `t`, with any V5 disclosure lag explicitly recorded.
- Factor implication: low PB is not automatically cheap for banks. For financial firms, PB must be interpreted together with ROE, risk, asset quality and capital constraints.
- Primary source links: Damodaran financial-service valuation notes and BIS bank PBR research are recorded in `bank_academic_theory_sources.md`.

### ROE

- Working V5 definition: `ROE = net profit attributable to ordinary shareholders / average or period-end equity`, using the issuer's disclosed accounting basis.
- Evidence layer: `core_theory` for accounting/valuation relationship, `industry_research` for bank report fields.
- Point-in-time rule: use only reported ROE or reconstruct from statements visible before the rebalance date.
- Research use: ROE can explain why one bank deserves a higher PB than another, but high ROE requires quality checks because leverage, under-provisioning or cyclically low credit costs can inflate it.

### Non-performing loan ratio

- Working V5 definition: `NPL ratio = non-performing loans / total loans`, aligned to the bank's disclosed loan-classification standard.
- Evidence layer: `core_theory` / `industry_research`.
- Official context: NFRA regularly reports commercial-bank NPL balances and NPL ratios in supervisory-indicator releases; the World Bank metadata describes NPL share as an asset-quality measure.
- Point-in-time rule: use only values disclosed in annual/interim reports or official filings visible before the rebalance date.
- Research use: lower or improving NPL ratio may indicate better asset quality; a rising ratio is a value-trap warning rather than an automatic sell signal.

### Provision coverage ratio

- Working V5 definition: `provision coverage ratio = loan-loss provisions / non-performing loans`.
- Evidence layer: `core_theory` / `industry_research`.
- Official context: NFRA quarterly supervisory indicators report provision coverage and loan provision ratios for commercial banks.
- Point-in-time rule: use only reported values visible before rebalance; do not backfill later restatements into earlier dates.
- Research use: higher provision coverage can indicate risk buffer, but extreme levels may reflect either conservatism or low recognized NPL denominator. It must be tested jointly with asset-quality trend.

### Loan-loss reserve ratio / loan provision ratio

- Working V5 definition: `loan provision ratio = loan-loss provisions / total loans`.
- Evidence layer: `core_theory` / `industry_research`.
- Research use: complements provision coverage because it is less mechanically affected by a small NPL denominator.
- Validation note: test whether provision coverage and loan provision ratio add incremental information after NPL level and NPL change.

### CET1 / core tier 1 capital adequacy ratio

- Working V5 definition: `CET1 or core tier 1 capital adequacy ratio = core/common equity tier 1 capital net amount / risk-weighted assets`.
- Evidence layer: `core_theory`.
- Official context: Basel III treats CET1 as the highest-quality going-concern capital; China's commercial-bank capital rules define capital ratios against risk-weighted assets.
- Point-in-time rule: use ratios disclosed in bank financial statements or capital adequacy disclosures visible before rebalance.
- Research use: stronger CET1 can reduce solvency and dividend-cut risk, but very high capital may also signal lower leverage and lower ROE. The expected sign must be validated.

### Capital adequacy ratio

- Working V5 definition: `capital adequacy ratio = total regulatory capital net amount / risk-weighted assets`.
- Evidence layer: `core_theory`.
- Research use: use as solvency buffer and regulatory constraint indicator. It should be interpreted with growth, dividend payout and asset-quality pressure.

### Net interest margin

- Working V5 definition: `NIM = net interest income / average interest-earning assets`, using issuer-disclosed basis.
- Evidence layer: `industry_research` for bank filings; `core_theory` for monetary-policy/rate-state context.
- Point-in-time rule: use annual/interim report values or reconstructed values from visible statements.
- Research use: falling NIM can pressure profitability and dividend sustainability, especially for banks lacking fee income or deposit-cost advantage.

### Dividend payout and cash dividend yield

- Working V5 definitions:
  - `cash dividend yield = announced cash dividend per share / reference price`.
  - `payout ratio = cash dividends / distributable or attributable profit`, with issuer-specific accounting basis recorded.
- Evidence layer: `core_theory` for CSRC/SSE dividend governance; `industry_research` for issuer announcements.
- Official context: CSRC's 2023 cash-dividend guidance emphasizes transparent and stable dividend policy, encourages higher dividends where appropriate, and also strengthens constraints on abnormal high payout when leverage and cash flow conditions are weak.
- Point-in-time rule: dividend factors must use announcement date and ex-dividend/payment information without using future dividend events.
- Research use: high dividend yield is a shareholder-return signal only when supported by profitability, capital adequacy and asset quality. Otherwise it may be a high-yield value trap caused by price decline.

### Credit cycle

- Working V5 definition: a macro-financial state describing credit expansion or contraction, measured by variables such as credit growth, credit-to-GDP gap, loan growth, social financing and real estate cycle indicators.
- Evidence layer: `core_theory`.
- Official context: BIS credit-to-GDP gap research treats the gap between credit-to-GDP and trend as a macroprudential early-warning guide. PBOC and NBS data can provide China-specific macro state variables.
- Point-in-time rule: use release-date-aware macro data. Revised full-history series cannot be treated as live data unless vintage/release timing is controlled.
- Research use: credit-cycle variables belong first in defensive/risk-state tests, not as accepted alpha until rolling validation supports them.

### Loan quality migration

- Working V5 definition: changes across normal, special-mention, overdue and non-performing loan categories, plus credit cost and write-off/disposal behavior where disclosed.
- Evidence layer: `industry_research` with regulatory context.
- Point-in-time rule: use annual/interim report fields visible by announcement date.
- Research use: deterioration speed may matter more than absolute level because investors often reprice banks when migration reveals under-recognized credit risk.

## Quant Validation Handoff

- Do not accept any definition as an alpha factor.
- For each derived factor, Quant Validation Agent must test IC, RankIC, top-minus-bottom spread, common-sample baseline, rolling stability and leave-one-factor-out ablation.
- Dividend and macro variables require explicit point-in-time release/announcement date controls.
- Banking-specific fields from annual/interim reports should carry source confidence and extraction method labels.

## References

- BIS / Basel Committee, Basel III and definition of capital materials: https://www.bis.org/bcbs/basel3.htm and https://www.bis.org/fsi/fsisummaries/defcap_b3.pdf
- NFRA, commercial-bank capital management rules and supervisory indicators: https://www.nfra.gov.cn
- PBOC LPR official page: https://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125440/3876551/index.html
- ChinaMoney LPR page: https://www.chinamoney.com.cn/chinese/bklpr/
- CSRC cash dividend guidance, 2023 revision: https://www.csrc.gov.cn/csrc/c100028/c7449654/content.shtml
- SSE cash dividend guidance and CSRC dividend PDF mirror: https://www.sse.com.cn
- NBS data and releases: https://www.stats.gov.cn/sj/ and https://data.stats.gov.cn
- CNINFO disclosure portal: https://www.cninfo.com.cn

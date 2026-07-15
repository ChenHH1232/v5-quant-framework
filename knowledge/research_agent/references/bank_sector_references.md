# Bank Sector Research References

## Purpose

This file is the shared citation map for Research Agent bank-sector knowledge cards. It supports financial reasoning and hypothesis design. It does not validate any V5 strategy or factor by itself.

## Evidence Labels

- `regulatory_definition`: accounting, capital, risk, index, or data definitions from regulators, exchanges, index providers, or official data providers.
- `academic_evidence`: peer-reviewed papers, NBER/SSRN/working papers, BIS/IMF research, or other research-grade evidence.
- `industry_disclosure`: listed-bank annual reports, fund documents, index product documents, or issuer disclosures.
- `V5_internal_finding`: findings from V5 governance, local-vs-platform checks, leakage audits, or workflow reviews.
- `hypothesis_only`: financially plausible idea that still requires V5 statistical validation.

## Regulatory And Official Definitions

1. Basel Committee on Banking Supervision, [Basel III framework](https://www.bis.org/bcbs/basel3.htm). Evidence level: `regulatory_definition`. Use for capital adequacy, risk-weighted assets, leverage, liquidity and macroprudential framing.
2. National Administration of Financial Regulation, [Commercial Bank Capital Management Measures](https://www.nfra.gov.cn/cn/view/pages/ItemDetail.html?docId=1134330&generaltype=0&itemId=917). Evidence level: `regulatory_definition`. Use for China bank capital adequacy, CET1, Tier 1, total capital and risk-weighted assets.
3. National Administration of Financial Regulation, official bank regulatory indicator releases and tables. Evidence level: `regulatory_definition`. Use for NPL ratio, provision coverage ratio, loan-loss provision ratio, liquidity and profitability indicators.
4. People's Bank of China, [Loan Prime Rate policy page](https://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125440/3876551/index.html). Evidence level: `regulatory_definition`. Use for LPR as a bank loan-pricing and interest-rate state variable.
5. National Interbank Funding Center / China Money, [LPR publication page](https://www.chinamoney.com.cn/chinese/bklpr/). Evidence level: `regulatory_definition`. Use for LPR publication mechanics and observations.
6. National Bureau of Statistics, [official statistical releases](https://www.stats.gov.cn/sj/zxfb/). Evidence level: `regulatory_definition`. Use for property sales, property investment and macro state variables.
7. BIS Data Portal, [credit-to-GDP gaps](https://data.bis.org/topics/CREDIT_GAPS). Evidence level: `regulatory_definition`. Use for excessive credit and banking-crisis early-warning state variables.

## Index, ETF, And Market Data Methodology

1. China Securities Index, [CSI index portal](https://www.csindex.com.cn/). Evidence level: `regulatory_definition`. Use for CSI bank index methodology, sample selection and index calculation context.
2. China Securities Index, [CSI bank industry index methodology PDF](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/20240510102751-000986_cn.pdf). Evidence level: `regulatory_definition`. Use for CSI bank index construction.
3. Huabao Fund, [Huabao CSI Bank ETF 512800 fund page](https://www.fsfund.com/fund/512800/fundDetail.shtml). Evidence level: `industry_disclosure`. Use for 512800 as the benchmark proxy and its tracking objective.
4. JoinQuant / jqdatasdk, [official GitHub repository](https://github.com/joinquant/jqdatasdk). Evidence level: `industry_disclosure`. Use for local data-access runner context only; platform behavior still needs direct confirmation.

## Academic And Research Evidence

1. Fama, E. F. and French, K. R. (1992), "The Cross-Section of Expected Stock Returns", Journal of Finance. [Publication reference](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1992.tb04398.x). Evidence level: `academic_evidence`. Use for book-to-market/value factor foundations.
2. Fama, E. F. and French, K. R. (1993), "Common Risk Factors in the Returns on Stocks and Bonds", Journal of Financial Economics. [Publication reference](https://doi.org/10.1016/0304-405X(93)90023-5). Evidence level: `academic_evidence`. Use for market, size and value factor framing.
3. Novy-Marx, R. (2013), "The Other Side of Value: The Gross Profitability Premium", Journal of Financial Economics. [Publication reference](https://doi.org/10.1016/j.jfineco.2013.01.003). Evidence level: `academic_evidence`. Use for profitability as a complement to valuation.
4. Campbell, J. Y., Hilscher, J. and Szilagyi, J. (2008), "In Search of Distress Risk", Journal of Finance. [Author page](https://campbell.scholars.harvard.edu/publications/search-distress-risk). Evidence level: `academic_evidence`. Use for distress-risk and value-trap caution.
5. Drehmann, M. and Tsatsaronis, K. (2014), "The credit-to-GDP gap and countercyclical capital buffers: questions and answers", BIS Quarterly Review. [BIS overview](https://www.bis.org/publ/qtrpdf/r_qt1403g.htm). Evidence level: `academic_evidence`. Use for credit-cycle and macroprudential state variables.
6. Drechsler, I., Savov, A. and Schnabl, P. (2021), "Banking on Deposits: Maturity Transformation without Interest Rate Risk", Journal of Finance. [NBER working paper](https://www.nber.org/papers/w24582). Evidence level: `academic_evidence`. Use for deposit franchise, funding stability and interest-rate sensitivity.
7. Damodaran, A., [Valuing Financial Service Firms](https://pages.stern.nyu.edu/~adamodar/pdfiles/papers/finfirm.pdf). Evidence level: `academic_evidence`. Use for why financial firms are often evaluated with book equity, ROE and cost of equity.

## Listed Bank Disclosure Examples

1. Annual and interim reports of listed Chinese banks from exchange filings or company investor-relations pages. Evidence level: `industry_disclosure`. Use for NPL, special mention loans, overdue loans, provision coverage, capital adequacy, NIM, deposit structure and dividend payout.
2. Dividend announcements and profit-distribution plans of listed Chinese banks. Evidence level: `industry_disclosure`. Use for announcement date, ex-date, payment date, payout ratio and cash-dividend sustainability.

## V5 Internal References

1. `docs/BANK_VALUE_15Y_LEAKAGE_AUDIT.md`. Evidence level: `V5_internal_finding`. Use for leakage and sample-use governance.
2. `docs/BANK_VALUE_15Y_PROCESS_REVIEW.md`. Evidence level: `V5_internal_finding`. Use for process problems found in the first Bank Value 15Y workflow.
3. `docs/BANK_VALUE_15Y_DEFENSIVE_OVERLAY_RESEARCH.md`. Evidence level: `V5_internal_finding`. Use for defensive overlay status as a risk-control candidate only.
4. `docs/governance/platform_confirmation_candidate_v1.md`. Evidence level: `V5_internal_finding`. Use for 2021-05 to 2026-05 as platform confirmation only, not tuning or acceptance evidence.

## Source Limitations

- General value-factor literature is not bank-sector-specific and is not China-specific.
- Regulatory definitions explain what ratios mean, not whether they predict returns.
- Listed-bank reports are low frequency and may lag the true credit cycle.
- ETF/index methodology supports benchmark construction but does not validate stock-selection alpha.
- V5 internal findings are governance facts, not external proof of economic validity.

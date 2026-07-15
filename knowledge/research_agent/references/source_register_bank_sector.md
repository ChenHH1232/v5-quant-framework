# Bank Sector Source Register

Status: first-pass completed for official/regulatory and academic theory sources.

Purpose: all Research Agent bank-sector knowledge cards should point back to this register before a claim is reused in factor design. Evidence labels follow the V5 SOP:

- `core_theory`: official regulation, academic papers, textbooks, official methodology.
- `industry_research`: annual reports, index/ETF material, rating/broker research, public industry reports.
- `market_views`: investor narratives, public forums, WeChat/Zhihu/Snowball/Jisilu style sources.
- `validated_findings`: V5 internal findings after Quant Validation Agent has tested them.

## Source Register

| Source name | Website or channel | Source type | Evidence layer | Access method | Crawler risk | Login required | Paid access required | Suggested manual fallback | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BIS / Basel Committee on Banking Supervision | https://www.bis.org and https://www.bis.org/bcbs/ | international banking regulator / standard setter | `core_theory` | public HTML and PDF pages | low | no | no | manually download specific standards or executive summaries | Primary source for Basel III, CET1, capital buffers, risk-weighted assets, credit-to-GDP gap, macroprudential framing. |
| BIS Credit-to-GDP Gap Data | https://data.bis.org/topics/CREDIT_GAPS | official macroprudential data | `core_theory` | public data portal | low-medium | no | no | manual CSV export from BIS data portal | Use only point-in-time/publication-aware macro state variables; do not treat revised full-history data as live signal without timestamp controls. |
| People's Bank of China (PBOC) | https://www.pbc.gov.cn | central bank / official macro | `core_theory` | public HTML/PDF pages | low-medium | no | no | manually download monetary policy reports and LPR pages | Source for monetary policy, LPR framework, credit and liquidity context. |
| China Foreign Exchange Trade System / ChinaMoney | https://www.chinamoney.com.cn | official interbank market infrastructure | `core_theory` | public HTML/data pages | medium | no | no | manual page export | Useful for LPR publication mechanics and market-rate context. |
| National Financial Regulatory Administration (NFRA, former CBIRC) | https://www.nfra.gov.cn | banking regulator | `core_theory` | public HTML/PDF pages | medium | no | no | manual page/PDF download | Source for commercial-bank capital rules and quarterly supervisory indicators such as NPL ratio, provision coverage and capital adequacy. |
| China Securities Regulatory Commission (CSRC) | https://www.csrc.gov.cn | securities regulator | `core_theory` | public HTML/PDF pages | low-medium | no | no | manual PDF download | Source for listed-company disclosure and cash-dividend rules. |
| Shanghai Stock Exchange (SSE) | https://www.sse.com.cn | exchange / disclosure rule source | `core_theory` / `industry_research` | public HTML/PDF pages | low-medium | no | no | manual PDF download | Source for disclosure rules, cash dividend guidance and Shanghai-listed bank announcements. |
| Shenzhen Stock Exchange (SZSE) | https://www.szse.cn | exchange / disclosure rule source | `core_theory` / `industry_research` | public HTML/PDF pages | medium | no | no | manual PDF download | Source for disclosure rules and Shenzhen-listed bank announcements. |
| National Bureau of Statistics (NBS) | https://www.stats.gov.cn and https://data.stats.gov.cn | official macro data | `core_theory` | public HTML/data portal | medium | no | no | manual data export | Source for GDP, CPI/PPI, real estate and macro variables. Data portal may be dynamic; record release dates. |
| CNINFO | https://www.cninfo.com.cn | official disclosure portal | `industry_research` | public website | high | usually no for browsing | no | `manual_download_required` for annual/interim reports | Dynamic pages and anti-automation risk. Store only metadata/extracted fields unless user explicitly approves raw PDFs. |
| Listed bank investor-relations pages | bank official websites | issuer disclosure | `industry_research` | public web/PDF pages | medium | no | no | manual annual/interim report download | Best source for bank-specific fields: NPL, special mention loans, overdue loans, provision coverage, NIM, CET1, capital adequacy, dividend per share. |
| CSI / SSE / fund company pages for 512800 bank ETF | exchange, index provider, fund manager websites | benchmark/index/ETF methodology | `industry_research` | public pages/PDFs | medium | no | no | manual product document download | Use for benchmark definition and ETF tracking context; do not infer alpha from benchmark construction. |
| Google Scholar | https://scholar.google.com | academic discovery | `core_theory` discovery only | search discovery | high | sometimes | no | manual search and citation capture | Do not scrape. Use only to discover papers; cite publisher/author/SSRN/BIS/IMF/World Bank pages where possible. |
| Wiley Online Library / Journal of Finance | https://onlinelibrary.wiley.com | academic publisher | `core_theory` | abstract/metadata, sometimes paywalled | medium | no for abstract | often yes for full text | cite DOI/abstract; use accessible author/NBER/SSRN versions if legal | Fama-French and Campbell distress-risk papers may require publisher access for full text. |
| SSRN | https://www.ssrn.com | working paper repository | `core_theory` | public abstracts/PDFs where available | medium | sometimes | no | manual download if public | Use abstracts and metadata; do not mass download. |
| NBER | https://www.nber.org | working paper repository | `core_theory` | public metadata/PDF where available | medium | sometimes | sometimes for some papers | cite metadata; use author page if public | Some PDFs public, others may require access. |
| BIS Working Papers / Quarterly Review | https://www.bis.org | academic/policy research | `core_theory` | public HTML/PDF | low | no | no | manual PDF download | Useful for credit cycle, bank valuation and macroprudential variables. |
| IMF / World Bank / OECD | https://www.imf.org, https://www.worldbank.org, https://www.oecd.org | policy research and data definitions | `core_theory` / `industry_research` | public pages/PDFs | low-medium | no | no | manual PDF download | Useful for NPL definitions, macro-financial stability and crisis context. |
| Broker research platforms and public broker reports | broker websites, public report portals | sell-side research | `industry_research` | public abstracts/PDFs where available | high | often | often | `manual_review_required` or user-provided reports | Do not scrape paywalled databases. Summarize only; record institution/date/URL. |
| Snowball | https://xueqiu.com | investor forum / market narrative | `market_views` | manual reading preferred | high | often | no | `manual_review_required` | Hypothesis source only; never strategy evidence. |
| WeChat public accounts | WeChat | public articles / market narrative | `market_views` | manual reading preferred | high | often app-only | no | `manual_review_required` | App-only, login and copyright constraints. Summarize only if user provides content. |
| Zhihu | https://www.zhihu.com | public articles / market narrative | `market_views` | manual reading preferred | high | often | no | `manual_review_required` | Hypothesis source only. |
| Jisilu | https://www.jisilu.cn | investor forum / market narrative | `market_views` | manual reading preferred | high | often | no | `manual_review_required` | Hypothesis source only. |

## Blocked Or Manual Review Queue

| Source | Status | Reason | Next action |
| --- | --- | --- | --- |
| CNINFO bulk annual/interim reports | `manual_download_required` | Dynamic website and report PDFs; avoid automated bulk download and do not commit raw proprietary PDFs. | Manually download selected bank reports or provide extracted field CSV. |
| Snowball / WeChat / Zhihu / Jisilu | `manual_review_required` | Login, dynamic rendering, app-only pages and anti-crawler risk are common. | User or Research Agent should manually summarize as `market_views` only. |
| Snowball high-dividend bank-stock leads | `public_access_partial` / `manual_review_required` | A small number of discussion pages exposed snippets through ordinary page access; many profile/article/stock-hot pages returned dynamic shell pages or require manual rendering. | Keep as `market_views`; manually review selected links before adding any account-specific claim beyond visible snippets. |
| Paywalled academic publisher full text | `paid_or_restricted` | Some Journal of Finance / ScienceDirect articles expose metadata but not full text. | Cite DOI/abstract; use legal public working-paper versions when available. |
| Broker research databases | `paid_or_restricted` | Copyright/paywall restrictions. | Use user-provided reports or public abstracts only. |

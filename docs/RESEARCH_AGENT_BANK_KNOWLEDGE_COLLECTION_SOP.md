# Research Agent SOP: Bank Sector Knowledge Collection

Date: 2026-07-15

## Objective

Build a reusable bank-sector knowledge base for V5. The goal is to support any bank-sector quantitative strategy derived from economic theory, not only `Bank Value 15Y` or `Bank Value Quality V2`.

This task is assigned to the Research Agent.

## Core Rule

Sources are not equal. Research Agent must tag every collected note with an evidence layer:

- `core_theory`: academic papers, textbooks, regulatory frameworks, official methodology.
- `industry_research`: broker research, bank annual reports, bank interim reports, index/ETF methodology, rating reports.
- `market_views`: Snowball, public articles, investor letters, WeChat articles, interviews.
- `validated_findings`: V5 internal findings after Quant Validation Agent has tested them.

Market views can inspire hypotheses, but cannot prove a strategy.

## Collection Order

### Step 1. Build the Source Register

Purpose:

Create `knowledge/research_agent/references/source_register_bank_sector.md`.

Required fields:

- Source name
- Website or channel
- Source type
- Evidence layer
- Access method
- Crawler risk
- Whether login is required
- Whether paid access is required
- Suggested manual fallback
- Notes

Start with sources listed in this SOP.

Output:

- One source register file.

Acceptance standard:

- Every later knowledge card must point back to at least one registered source.

### Step 2. Regulatory and Official Definitions First

Purpose:

Define the terms before interpreting them.

Recommended sources:

- Basel Committee on Banking Supervision: capital adequacy, CET1, risk-weighted assets.
- BIS: global banking risk, credit cycle, macroprudential background.
- PBOC: China monetary policy reports, loan prime rate, credit cycle.
- NFRA / former CBIRC: China banking regulation, asset quality, capital rules.
- CSRC / Shanghai Stock Exchange / Shenzhen Stock Exchange: disclosure and dividend rules.
- NBS: macro data such as GDP, CPI, credit and real estate indicators.
- ChinaBond or official yield curve sources if used for rate-state variables.

Target knowledge:

- ROE
- PB
- NPL ratio
- provision coverage ratio
- core tier 1 capital adequacy ratio
- capital adequacy ratio
- net interest margin
- dividend payout
- credit cycle
- loan quality migration

Crawler and access notes:

- Prefer official PDFs, HTML pages, or manually downloaded reports.
- Do not scrape aggressively.
- If a site has CAPTCHA, dynamic token, or blocks automated access, stop automated collection and record `manual_download_required`.
- Do not bypass login, CAPTCHA, paywall, robots restrictions, or rate limits.

Output:

- `knowledge/research_agent/references/bank_regulatory_definitions.md`

### Step 3. Academic and Textbook Theory

Purpose:

Build the theoretical base for why valuation, profitability, asset quality, and capital strength might predict bank-stock returns.

Recommended sources:

- Google Scholar
- SSRN
- NBER, if accessible
- BIS working papers
- IMF working papers
- World Bank papers
- university-hosted PDFs
- finance textbooks or accounting textbooks already available to the user

Search themes:

- bank valuation price-to-book ROE
- bank capital adequacy stock returns
- non-performing loans bank valuation
- bank dividend policy capital regulation
- profitability quality expected returns
- value trap financial institutions
- credit cycle bank equity returns

Crawler and access notes:

- Use search result pages only to discover papers.
- Prefer direct PDF pages from publishers, universities, SSRN, BIS, IMF, World Bank.
- If a paper is paywalled, record citation and abstract only; do not try to bypass.
- Do not mass-download PDFs.

Output:

- `knowledge/research_agent/references/bank_academic_theory_sources.md`

### Step 4. Listed Bank Annual Reports and Financial Disclosures

Purpose:

Connect factor hypotheses to real bank disclosure fields.

Recommended sources:

- Shanghai Stock Exchange disclosures
- Shenzhen Stock Exchange disclosures
- bank investor relations pages
- 巨潮资讯 CNINFO
- annual reports and interim reports of listed banks

Target fields:

- NPL ratio
- special mention loan ratio
- overdue loan ratio
- provision coverage ratio
- loan-loss reserve ratio
- net interest margin
- cost-to-income ratio
- CET1 ratio
- capital adequacy ratio
- dividend per share
- payout ratio
- ROE

Crawler and access notes:

- CNINFO and exchange disclosure sites may use dynamic pages, rate limits, or anti-bot checks.
- Prefer manual download or official batch exports if available.
- For automated collection, use polite low-frequency requests and stop immediately if blocked.
- Store only metadata and extracted fields needed for research; do not commit raw PDFs unless explicitly approved.

Output:

- `knowledge/research_agent/references/bank_disclosure_field_map.md`

### Step 5. Industry Research Reports

Purpose:

Collect bank-sector mechanisms, current market concerns, and factor interpretation from professional industry research.

Recommended sources:

- 券商研究所公开报告 pages
- 慧博 / 发现报告 / 东方财富研报 / 同花顺研报 / Wind or Choice if user manually exports
- brokerage public WeChat official accounts
- rating-agency reports where available
- ETF or index provider methodology documents

Search themes:

- 银行股 PB ROE 估值框架
- 银行板块 高股息 策略
- 银行 净息差 资产质量 拨备 覆盖率
- 区域银行 城商行 农商行 风险
- 银行 资本充足率 分红 可持续性
- 银行板块 价值陷阱

Crawler and access notes:

- Many research-report sites have login, anti-crawler, or copyright restrictions.
- Do not scrape paywalled report databases.
- Use manually downloaded PDFs or public abstracts when needed.
- Record report title, institution, analyst if visible, publication date, and URL/source channel.
- Avoid copying long report text. Summarize in your own words.

Output:

- `knowledge/research_agent/references/bank_industry_research_sources.md`

### Step 6. Market Views: Snowball, WeChat, Public Articles

Purpose:

Collect investor narratives and hypothesis ideas that may not appear in formal sources.

Recommended sources:

- 雪球
- 公众号文章
- 知乎专栏
- 集思录
- bank-investor blogs
- fund manager letters or public commentary

Target narratives:

- 高股息银行逻辑
- 低 PB 修复逻辑
- 中特估银行逻辑
- 区域银行分化
- 招商银行/宁波银行等高 ROE 银行溢价逻辑
- 国有大行防御属性
- 银行地产链风险
- 净息差下行压力
- 拨备反哺利润

Crawler and access notes:

- Snowball and WeChat commonly have login, dynamic rendering, rate limits, and anti-bot measures.
- Do not bypass login, CAPTCHA, paywalls, or app-only access.
- Manual reading and note-taking is preferred.
- Quote only very short excerpts if necessary; otherwise summarize.
- Treat all such material as `market_views`, never as proof.

Output:

- `knowledge/research_agent/references/bank_market_view_hypotheses.md`

### Step 7. Convert Sources Into Hypothesis Cards

Purpose:

Turn collected material into V5-usable research assets.

Update or create:

- `knowledge/research_agent/factor_theory/bank_value_investing_framework.md`
- `knowledge/research_agent/factor_theory/bank_core_factor_hypotheses.md`
- `knowledge/research_agent/factor_theory/bank_value_trap_identification.md`
- `knowledge/research_agent/factor_theory/bank_defensive_macro_state_variables.md`

Each hypothesis must include:

- hypothesis statement
- economic logic
- required data
- point-in-time rule
- expected sign
- possible failure mode
- evidence layer
- citation/source reference
- Quant Validation task

### Step 8. Build the Quant Validation Handoff

Purpose:

Make sure Research Agent does not accidentally approve a strategy.

For every factor hypothesis, write:

- IC / RankIC test requirement
- rolling validation requirement
- baseline comparison
- ablation requirement
- robustness checks
- leakage risk
- data availability risk

Output:

- `knowledge/research_agent/references/bank_factor_validation_handoff.md`

### Step 9. Update the Knowledge Index

Purpose:

Make the new material discoverable.

Update:

- `knowledge/research_agent/INDEX.md`

Add links to all new reference files and mark unfinished sections as `pending`.

### Step 10. Final Research Agent Report

Purpose:

Summarize what was collected and what remains uncertain.

Required sections:

- sources collected
- strongest theory-backed hypotheses
- market-view-only hypotheses
- likely data gaps
- crawler/access limitations encountered
- hypotheses ready for Quant Validation
- hypotheses rejected or downgraded

Output:

- `knowledge/research_agent/references/bank_knowledge_collection_report.md`

## Website Access and Anti-Crawler Policy

Research Agent must follow these rules:

1. Do not bypass CAPTCHA, login walls, paid access, app-only restrictions, or robots restrictions.
2. Do not use hidden APIs unless they are official, documented, and permitted.
3. Do not mass-download reports or PDFs.
4. Prefer manual download, official export, or user-provided files when a website is protected.
5. Record blocked sources as `manual_review_required`.
6. Keep request frequency low for public pages.
7. Do not store passwords, cookies, tokens, or session headers in the repo.
8. Do not commit raw proprietary reports unless the user explicitly approves.
9. Summarize copyrighted material; avoid long verbatim excerpts.
10. Every source note must include access status:
    - `public_access`
    - `login_required`
    - `paid_or_restricted`
    - `manual_download_required`
    - `blocked_or_unavailable`

## Recommended Initial Source List

### Official and Regulatory

- BIS: https://www.bis.org
- Basel Committee: https://www.bis.org/bcbs/
- PBOC: http://www.pbc.gov.cn
- NFRA: https://www.nfra.gov.cn
- CSRC: http://www.csrc.gov.cn
- SSE: https://www.sse.com.cn
- SZSE: https://www.szse.cn
- NBS: https://www.stats.gov.cn
- CNINFO: http://www.cninfo.com.cn

### Academic

- Google Scholar: https://scholar.google.com
- SSRN: https://www.ssrn.com
- IMF: https://www.imf.org
- World Bank: https://www.worldbank.org
- NBER: https://www.nber.org

### Industry Research and Data Context

- 东方财富研报
- 同花顺研报
- 慧博投研
- 发现报告
- 各大券商研究所公开网页或公众号
- 银行官网投资者关系页面
- 512800 银行 ETF 基金公告和产品资料

### Market Views

- 雪球
- 集思录
- 知乎
- 微信公众号
- 公开基金经理访谈或投资者信件

## Acceptance Criteria

The task is complete only when:

- the source register exists;
- at least four source-category reference files exist;
- every major bank-factor hypothesis has evidence-layer labels;
- every market-view claim is marked as hypothesis-only;
- crawler/access limitations are recorded;
- Quant Validation handoff is created;
- `knowledge/research_agent/INDEX.md` is updated.


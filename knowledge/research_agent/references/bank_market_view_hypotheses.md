# Bank Market-View Hypotheses

Status: first-pass Snowball high-dividend bank-stock market-view collection completed.

Evidence layer: `market_views`

## Rule

Market views are hypothesis sources only. They cannot prove a strategy, cannot approve a factor, and cannot override official definitions, bank disclosures, or Quant Validation Agent results.

Access rule: do not bypass login, CAPTCHA, paywalls, app-only pages, robots restrictions, rate limits, or anti-crawler systems. If Snowball pages only expose dynamic shell pages or require login/manual rendering, mark them `manual_review_required`.

## Snowball Access Notes

| Source group | Access status | Notes |
| --- | --- | --- |
| Selected public Snowball discussion pages | `public_access_partial` | A few discussion pages exposed short discussion snippets through normal page access/search snippets. Only short summaries are recorded. |
| Snowball profile pages, stock hot pages, many article pages | `manual_review_required` | Several URLs returned only dynamic shell pages or very limited text. No login/CAPTCHA/app-only restrictions were bypassed. |
| WeChat links inside Snowball discussions | `manual_review_required` | WeChat may be app-only/dynamic and copyright-constrained; not opened for automated extraction. |

## Representative Accounts / Articles

### `MV_XQ_ICE_CMB_GUZIDI`

- Account / view source: `ice_招行谷子地`.
- Snowball profile: https://xueqiu.com/n/ice_%E6%8B%9B%E8%A1%8C%E8%B0%B7%E5%AD%90%E5%9C%B0
- Public discussion lead: https://xueqiu.com/1821992043/293920794/329347422
- Search/discovery leads:
  - https://xueqiu.com/1821992043/240056796
  - https://xueqiu.com/1821992043/252357365
- Access status: `public_access_partial` for one discussion page; `manual_review_required` for profile/full articles and linked WeChat material.
- Selection decision: include as representative because the account is strongly associated with bank fundamental analysis, especially China Merchants Bank and ROE/PB/dividend-reinvestment reasoning.
- Core hypothesis extracted: high-ROE banks can justify higher PB, and long-term shareholder return should be modeled through ROE, payout ratio, buy price/PB and dividend reinvestment rather than current dividend yield alone.
- Candidate factor idea:
  - `roe_supported_dividend_capacity`: dividend yield is positive only when ROE is stable and payout is sustainable.
  - `pb_allowed_by_roe`: compare observed PB with PB implied by ROE, payout and required return.
  - `dividend_reinvestment_return_proxy`: estimate expected long-run return under stable ROE/payout assumptions.
- What to exclude:
  - Do not encode a single-stock China Merchants Bank preference as a general bank factor.
  - Do not accept personal model outputs without independent data reconstruction.
  - Do not treat controversial reputation, follower count or debate intensity as evidence.
- Required Quant Validation test:
  - Test whether ROE-supported dividend yield beats raw dividend yield under rolling common-sample validation.
  - Test whether implied PB gap adds IC/RankIC after controlling for raw PB and ROE.
  - Stress-test assumptions on payout, ROE decay and terminal PB.

### `MV_XQ_LAOKAILI_BANK_VALUATION`

- Account / view source: `老凯李`.
- Public discussion/article leads:
  - https://xueqiu.com/3921480024/121111559
  - https://xueqiu.com/1019832951/351358823/376476354
  - https://xueqiu.com/3921480024/353610256/378348383
- Access status: `public_access_partial` for search snippets and one discussion page; some pages returned dynamic shell pages and require `manual_review_required`.
- Selection decision: include because the available snippets directly discuss PB, PE, ROE, dividend yield, payout ratio, risk-free yield and bank valuation.
- Core hypothesis extracted: bank PB, PE and dividend yield can be converted into each other when ROE, payout and growth assumptions are stable; current high dividend yield loses attractiveness when yield compresses or dividend growth expectations fade.
- Candidate factor idea:
  - `dividend_yield_vs_rate_spread`: bank dividend yield minus 10-year government bond yield or wealth-management yield proxy.
  - `payout_growth_consistency`: prefer banks where payout increase is supported by earnings growth rather than temporary valuation compression.
  - `pb_pe_roe_consistency_gap`: flag inconsistent valuation where PB implies lower ROE than visible profitability.
- What to exclude:
  - Do not use fixed PB thresholds such as 1.5 PB as universal sell rules.
  - Do not infer that falling risk-free rate always raises bank valuation; bank NIM and credit-cycle channels may offset.
  - Do not take forum comments on future payout as evidence unless matched to actual dividend announcements.
- Required Quant Validation test:
  - Test dividend-yield spread versus absolute dividend yield.
  - Test PB/ROE-implied valuation gap against future returns and drawdowns.
  - Run regime split by rate environment and bank ETF trend state.

### `MV_XQ_QIANTAO_MULTIFACTOR_BANK_RANKING`

- Account / view source: `千淘投资` and related discussion participants.
- Public discussion leads:
  - https://xueqiu.com/2282072729/377417146
  - https://www.xueqiu.com/2282072729/387032535/405263364
- Access status: `public_access_partial` for the discussion page; main article/full context requires `manual_review_required`.
- Selection decision: include because the discussion highlights a practical bank-ranking problem: duplicate indicators and missing asset-quality metrics.
- Core hypothesis extracted: bank ranking should avoid double-counting near-duplicate variables such as ROA/ROE, payout/dividend yield, revenue/profit growth, and CET1/total capital; asset-quality fields such as overdue-to-NPL and loan provision ratio may add useful information.
- Candidate factor idea:
  - `deduplicated_bank_quality_score`: cluster/correlation control before combining profitability, payout, valuation, asset quality and capital factors.
  - `overdue_npl_quality_guard`: include overdue/NPL relation where disclosure is available.
  - `loan_provision_ratio_buffer`: use provision-to-loan as a supplement to provision coverage.
- What to exclude:
  - Do not use hand-made forum rankings directly as factors.
  - Do not equal-weight many overlapping sub-indicators without correlation and ablation checks.
  - Exclude short-term trading comments from long-horizon value factor design.
- Required Quant Validation test:
  - Run factor correlation matrix, feature clustering and leave-one-family-out ablation.
  - Test whether overdue/NPL and loan provision ratio add incremental IC beyond NPL ratio and provision coverage.

### `MV_XQ_MOSUO_FHY_DEEP_SZ_BANKS`

- Account / view source: `摸索fhy` and discussion replies.
- Public discussion lead: https://xueqiu.com/1152386711/251923146/287228541
- Access status: `public_access_partial`.
- Selection decision: include because it gives a clear bottom-up selection narrative for small Shenzhen-listed banks using fundamentals, dividend yield, asset quality, regional/bank-type differences and stability.
- Core hypothesis extracted: high-dividend bank selection should be filtered by basic fundamentals, asset quality, regional quality, bank type and stability; smaller rural commercial banks may need additional risk discount versus larger city commercial banks.
- Candidate factor idea:
  - `regional_bank_stability_filter`: penalize smaller or weaker regional banks unless asset quality and dividend stability are visible.
  - `dividend_plus_asset_quality_score`: combine yield with NPL/overdue/provision trend.
  - `fund_ownership_overcrowding_penalty`: test whether heavily owned/high-valuation bank leaders underperform when valuation normalizes.
- What to exclude:
  - Do not copy one investor's final stock pick into strategy rules.
  - Do not treat Shenzhen-only selection as a full A-share bank-universe rule.
  - Do not use qualitative region preference without measurable data.
- Required Quant Validation test:
  - Compare high-dividend-only versus high-dividend-plus-asset-quality within city commercial, rural commercial and national bank subgroups.
  - Test liquidity, market-cap and ownership sensitivity.

### `MV_XQ_GENERAL_HIGH_DIVIDEND_BANK_THREADS`

- Source leads:
  - https://xueqiu.com/5395069128/242361912
  - https://xueqiu.com/3559889031/315916554
  - https://xueqiu.com/3559889031/249672698
  - https://xueqiu.com/1579106064/191869272
  - https://xueqiu.com/3616204477/83821246
  - https://xueqiu.com/S/SH600036/hots?page=42
- Access status: mostly `manual_review_required`; several pages returned only dynamic shell pages or limited search snippets.
- Selection decision: include only as a review queue, not as already summarized evidence.
- Core hypothesis extracted from visible search-level context: investor demand for high-dividend banks may be driven by income substitution when bond/wealth-management yields are low, but the same yield can be a value trap if dividends fall or asset quality worsens.
- Candidate factor idea:
  - `income_substitution_state`: dividend yield relative to bond yield or wealth-management yield proxy.
  - `high_yield_trap_flag`: high dividend yield combined with falling earnings, falling payout capacity, worsening NPL/provision or falling capital ratio.
- What to exclude:
  - Exclude unsupported claims that one current dividend-yield threshold alone is sufficient.
  - Exclude Hong Kong-only bank-stock discussions unless explicitly building an H-share or AH-spread strategy.
  - Exclude anecdotal "buy for income" views unless translated into measurable and point-in-time variables.
- Required Quant Validation test:
  - Test raw high-dividend yield versus sustainable high-dividend yield.
  - Test A-share only, H-share only and AH dual-listed samples separately if cross-market data is used.

## Selected Market-View Hypotheses

| Hypothesis id | Market-view statement | Candidate factor idea | Evidence layer | Quant Validation requirement |
| --- | --- | --- | --- | --- |
| `MV_HDIV_001` | High dividend yield is attractive only when supported by stable ROE and adequate capital. | `roe_supported_dividend_capacity` | `market_views` | Compare raw dividend yield vs ROE/capital-supported yield under rolling IC/RankIC and top-minus-bottom spread. |
| `MV_HDIV_002` | Bank valuation can be framed through PB, ROE, payout and required return rather than PB alone. | `pb_allowed_by_roe`, `pb_pe_roe_consistency_gap` | `market_views` | Test implied-PB gap after controlling for raw PB, ROE and size. |
| `MV_HDIV_003` | Dividend yield should be compared with risk-free or low-risk income alternatives. | `dividend_yield_vs_rate_spread` | `market_views` | Test rate-spread factor by interest-rate regime; avoid revised macro data. |
| `MV_HDIV_004` | A high-yield bank can be a value trap if yield is caused by price decline before dividend/earnings deterioration. | `high_yield_trap_flag` | `market_views` | Test interaction of high yield with earnings growth, NPL trend, provision buffer and capital. |
| `MV_HDIV_005` | Bank multi-factor rankings should remove duplicated indicators and add asset-quality fields. | `deduplicated_bank_quality_score` | `market_views` | Run correlation clustering, family-level ablation and common-sample validation. |
| `MV_HDIV_006` | Regional banks require additional quality, size, liquidity and region-risk controls. | `regional_bank_stability_filter` | `market_views` | Validate separately for state-owned, joint-stock, city commercial and rural commercial banks. |
| `MV_HDIV_007` | Dividend reinvestment return depends on buy PB, ROE, payout and terminal valuation. | `dividend_reinvestment_return_proxy` | `market_views` | Scenario-stress ROE decay, payout changes and terminal PB; compare to realized returns. |

## Excluded Or Downgraded Views

| View type | Decision | Reason |
| --- | --- | --- |
| Single-stock conviction posts | Exclude from factor evidence | They may inspire case studies but cannot define a bank-sector strategy. |
| Pure forum popularity or big-V identity | Exclude | Popularity is not financial evidence and may introduce crowding bias. |
| Fixed PB or dividend-yield thresholds without context | Downgrade | Thresholds depend on ROE, payout, rates, capital, asset quality and regime. |
| Hong Kong-only high-dividend bank discussions | Exclude from A-share strategy unless separately scoped | Different market, tax, currency, investor base and liquidity structure. |
| Short-term T+0 or tactical trading comments | Exclude | Not aligned with V5 bank value-investing research horizon. |
| WeChat-linked long articles not publicly accessible without app/manual access | `manual_review_required` | Do not bypass app-only/dynamic access; user may provide text for summary. |

## Handoff To Research / Quant Agents

- Research Agent may use this file to propose hypotheses, not to approve factors.
- Quant Validation Agent must treat every hypothesis above as `hypothesis_only`.
- Engineering Agent must not implement Snowball-derived rules unless the Project Manager marks them as approved after statistical validation.
- Any future manual Snowball/WeChat notes must include account, date, link, access status and a short non-verbatim summary.

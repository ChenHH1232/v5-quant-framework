# Bank Academic Theory Sources

Status: first-pass completed.

Evidence layer: `core_theory`

Purpose: provide Research Agent with theory-backed source notes for bank-sector value, profitability, asset quality, capital, dividend and macro-state hypotheses. This file does not approve any factor; every hypothesis still requires Quant Validation Agent evidence.

## Source Notes

### `FAMA_FRENCH_1992_CROSS_SECTION`

- Citation: Fama, Eugene F. and Kenneth R. French, 1992, "The Cross-Section of Expected Stock Returns," Journal of Finance, 47(2), 427-465.
- URL: https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1992.tb04398.x
- Alternate metadata: https://ideas.repec.org/a/bla/jfinan/v47y1992i2p427-65.html
- Access status: `public_access` for metadata/abstract; full text may be `paid_or_restricted`.
- Evidence layer: `core_theory`.
- V5 relevance: book-to-market/valuation is a core cross-sectional return variable in the general equity literature. For banks, this supports studying PB/book value variables, but it does not prove that low PB works in A-share banks.
- Factor hypotheses supported:
  - `low_price_to_book`: lower PB may proxy for value.
  - `value_trap_guard`: value variables need quality and distress controls.
- Quant handoff: test bank-only IC/RankIC and low-PB baseline under common sample; do not infer bank-sector validity from broad-market evidence.

### `NOVY_MARX_2013_PROFITABILITY`

- Citation: Novy-Marx, Robert, 2013, "The Other Side of Value: The Gross Profitability Premium," Journal of Financial Economics, 108(1), 1-28.
- URL: https://ideas.repec.org/a/eee/jfinec/v108y2013i1p1-28.html
- SSRN / working paper: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1598056
- Access status: `public_access` for metadata/abstract/SSRN page; publisher full text may be `paid_or_restricted`.
- Evidence layer: `core_theory`.
- V5 relevance: profitability can add information beyond valuation. Bank-specific implementation should use ROE/ROA/NIM/provision-adjusted profitability rather than industrial-company gross profitability.
- Factor hypotheses supported:
  - `roe_quality`
  - `profitability_stability`
  - quality layer combined with value layer.
- Quant handoff: test whether profitability improves low-PB selection in common-sample rolling tests; reject if it only improves the 2021-2026 platform-confirmation window.

### `DAMODARAN_FINANCIAL_SERVICE_VALUATION`

- Citation: Damodaran, Aswath, "Valuing Financial Service Firms" / financial service valuation notes.
- URL: https://pages.stern.nyu.edu/~adamodar/pdfiles/papers/finfirm09.pdf
- Alternate notes: https://pages.stern.nyu.edu/~adamodar/pdfiles/eqnotes/finsvc.pdf
- Access status: `public_access`.
- Evidence layer: `core_theory`.
- V5 relevance: financial firms are different from industrial firms because debt is raw material, regulatory capital constrains growth, and equity valuation is closely tied to ROE, cost of equity, growth and risk.
- Factor hypotheses supported:
  - PB should be interpreted jointly with ROE and risk.
  - capital adequacy can constrain growth/dividend capacity.
  - dividend and retained earnings are part of regulatory-capital economics.
- Quant handoff: estimate whether PB discounts are justified by lower ROE, asset quality or capital risk before treating them as mispricing.

### `BIS_BANK_PBR_2018`

- Citation: Bogdanova, B., Fender, I. and Takats, E., 2018, "The ABCs of bank PBRs: What drives bank price-to-book ratios?", BIS Quarterly Review.
- URL: https://www.bis.org/publ/qtrpdf/r_qt1803h.htm
- Access status: `public_access`.
- Evidence layer: `core_theory`.
- V5 relevance: directly addresses bank price-to-book ratios after the global financial crisis and links low PBRs to concerns about profitability, health and business models.
- Factor hypotheses supported:
  - low PB alone may represent impairment rather than value.
  - bank valuation should include profitability, risk and business-model context.
- Quant handoff: low-PB candidate must be tested against quality-filtered low-PB and equal-bank baselines.

### `CAMPBELL_HILSCHER_SZILAGYI_2008_DISTRESS`

- Citation: Campbell, John Y., Jens Hilscher and Jan Szilagyi, 2008, "In Search of Distress Risk," Journal of Finance, 63(6), 2899-2939.
- URL: https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2008.01416.x
- NBER working paper: https://www.nber.org/system/files/working_papers/w12362/w12362.pdf
- Author page: https://campbell.scholars.harvard.edu/publications/search-distress-risk
- Access status: `public_access` for NBER/author working-paper material; publisher full text may be `paid_or_restricted`.
- Evidence layer: `core_theory`.
- V5 relevance: distress risk can be associated with poor future stock performance rather than a rewarded risk premium. This supports treating weak asset quality/capital/profitability as value-trap risk.
- Factor hypotheses supported:
  - `asset_quality_trend`
  - `capital_resilience`
  - `value_trap_guard`
- Quant handoff: test whether bank distress proxies reduce left-tail risk and drawdown without merely curve-fitting.

### `BIS_CREDIT_GAP_DREHMANN_TSATSARONIS_2014`

- Citation: Drehmann, Mathias and Kostas Tsatsaronis, 2014, "The credit-to-GDP gap and countercyclical capital buffers: questions and answers," BIS Quarterly Review.
- URL: https://www.bis.org/publ/qtrpdf/r_qt1403g.pdf
- Related BIS data: https://data.bis.org/topics/CREDIT_GAPS
- Access status: `public_access`.
- Evidence layer: `core_theory`.
- V5 relevance: credit-to-GDP gap is used in macroprudential policy as a guide to countercyclical capital buffers and credit-cycle risk.
- Factor hypotheses supported:
  - macro defensive/risk-state variables.
  - credit-cycle overlays for banks.
- Quant handoff: use release-date-aware data; validate separately as defensive risk control, not alpha evidence.

### `BIS_TOTAL_CREDIT_EARLY_WARNING_2013`

- Citation: Drehmann, Mathias, Claudio Borio and Kostas Tsatsaronis, 2013, "Total credit as an early warning indicator for systemic banking crises," BIS Quarterly Review.
- URL: https://ideas.repec.org/a/bis/bisqtr/1306f.html
- Access status: `public_access` for metadata/summary; BIS publication available through BIS.
- Evidence layer: `core_theory`.
- V5 relevance: supports credit variables as systemic banking risk indicators.
- Factor hypotheses supported:
  - credit expansion/contraction state.
  - defensive bank-sector exposure controls.
- Quant handoff: test lead/lag and publication timing; avoid future revisions.

### `BANK_CAPITAL_STOCK_RETURNS_2020`

- Citation: "Does bank capitalization matter for bank stock returns?", Journal of Financial Stability / ScienceDirect listing.
- URL: https://www.sciencedirect.com/science/article/abs/pii/S1062940820300681
- Access status: `public_access` for abstract; full text may be `paid_or_restricted`.
- Evidence layer: `core_theory`.
- V5 relevance: bank capital is theoretically central because it absorbs insolvency risk and interacts with regulatory requirements. Abstract-level evidence is enough to justify a hypothesis, not acceptance.
- Factor hypotheses supported:
  - `capital_resilience`
  - dividend sustainability under capital constraints.
- Quant handoff: because full text may be restricted, treat as theory support only and validate on A-share bank data.

### `BANK_DIVIDENDS_CAPITAL_REGULATION_2016`

- Citation: "How to regulate bank dividends? Is capital regulation an answer?", Economic Modelling, 2016.
- URL: https://ideas.repec.org/a/eee/ecmode/v57y2016icp281-293.html
- Publisher page: https://www.sciencedirect.com/science/article/abs/pii/S0264999316301250
- Access status: `public_access` for metadata/abstract; full text may be `paid_or_restricted`.
- Evidence layer: `core_theory`.
- V5 relevance: dividend policy in banks is tied to capital regulation; high dividends may signal strength or may be constrained by capital needs.
- Factor hypotheses supported:
  - `sustainable_dividend_yield`
  - high-dividend value-trap screen.
- Quant handoff: split dividend yield into announced yield, payout ratio, ROE support and capital support; test for price-decline high-yield traps.

### `NPL_ASSET_QUALITY_POLICY_SOURCES`

- Citation group: World Bank WDI NPL metadata; OECD/ECB/IMF-style NPL policy research.
- World Bank NPL metadata: https://databank.worldbank.org/metadataglossary/world-development-indicators/series/FB.AST.NPER.ZS
- OECD NPL post-COVID paper: https://www.oecd.org
- Access status: `public_access` for metadata and selected PDFs.
- Evidence layer: `core_theory` / `industry_research`.
- V5 relevance: NPLs are a standard asset-quality measure; high or rising NPLs can weaken lending capacity, profitability and investor confidence.
- Factor hypotheses supported:
  - `asset_quality_trend`
  - `provision_buffer`
  - value-trap identification.
- Quant handoff: test both level and change of NPL-related variables; require point-in-time bank disclosures.

## Hypothesis-To-Source Matrix

| V5 hypothesis | Primary theory sources | Evidence layer | Current status |
| --- | --- | --- | --- |
| Low PB may identify bank value | `FAMA_FRENCH_1992_CROSS_SECTION`, `DAMODARAN_FINANCIAL_SERVICE_VALUATION`, `BIS_BANK_PBR_2018` | `core_theory` | `hypothesis_only` |
| Low PB needs quality guard | `BIS_BANK_PBR_2018`, `CAMPBELL_HILSCHER_SZILAGYI_2008_DISTRESS`, `DAMODARAN_FINANCIAL_SERVICE_VALUATION` | `core_theory` | `hypothesis_only` |
| ROE/profitability quality can improve value selection | `NOVY_MARX_2013_PROFITABILITY`, `DAMODARAN_FINANCIAL_SERVICE_VALUATION` | `core_theory` | `hypothesis_only` |
| Asset-quality deterioration identifies value traps | `CAMPBELL_HILSCHER_SZILAGYI_2008_DISTRESS`, `NPL_ASSET_QUALITY_POLICY_SOURCES` | `core_theory` / `industry_research` | `hypothesis_only` |
| Provision buffer may reduce downside risk | `NPL_ASSET_QUALITY_POLICY_SOURCES`, `NFRA_SUPERVISORY_INDICATORS` | `core_theory` / `industry_research` | `hypothesis_only` |
| Capital resilience supports solvency and dividend sustainability | `BIS_BASEL3_CAPITAL`, `NFRA_CAPITAL_RULES_2024`, `BANK_CAPITAL_STOCK_RETURNS_2020` | `core_theory` | `hypothesis_only` |
| Sustainable dividends require profitability and capital support | `BANK_DIVIDENDS_CAPITAL_REGULATION_2016`, `CSRC_CASH_DIVIDEND_2023`, `DAMODARAN_FINANCIAL_SERVICE_VALUATION` | `core_theory` | `hypothesis_only` |
| Credit-cycle state can be a defensive variable | `BIS_CREDIT_GAP_DREHMANN_TSATSARONIS_2014`, `BIS_TOTAL_CREDIT_EARLY_WARNING_2013`, `PBOC_LPR` | `core_theory` | `risk_control_candidate` |

## Access Limitations

- Some publisher pages are abstract-only or paywalled. Mark them `paid_or_restricted`; do not bypass.
- Google Scholar is for manual discovery only and should not be scraped.
- Working-paper PDFs are useful for reading, but V5 should store only notes, citations and source ids, not raw downloaded PDFs.

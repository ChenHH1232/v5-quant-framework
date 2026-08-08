# V5c fxbaogao Two-Stage Retrieval Policy

As of 2026-07-26.

## Current API Knowledge

The local V5 documentation only confirms these search parameters:

- `keywords`
- `orgNames`
- `startTime`
- `endTime`

No local API documentation confirms support for report type filters, title-only search, body-only search, Boolean operators, exclude keywords, industry/topic filters, institution-type filters, relevance score, pagination or page size.

Research Agent must not assume undocumented parameters exist.

## Capability Matrix

| Capability | Local Documentation Status | V5c Policy |
|---|---|---|
| Report type filter | Not confirmed | Do not pass as API parameter; filter locally after title / paragraph review |
| Title contains / exact / must include | Not confirmed | Use local Stage 1 title filter |
| Title exclude keywords | Not confirmed | Use local Stage 1 title exclusion |
| Full text / paragraph / summary matching | Paragraph endpoint confirmed by `reportId` + `keyword`; full search fields not confirmed | Search first, then fetch paragraphs for accepted leads |
| Boolean AND / OR / NOT | Not confirmed | Split into multiple narrow searches and local rerank |
| Industry / topic filter | Not confirmed beyond returned `industryName` | Treat returned industry as metadata, not a search constraint |
| Institution type filter | Not confirmed | Use `orgNames` only when specific institutions are desired |
| Sort by relevance / time | Not confirmed | Use returned order only as API order; local rerank required |
| Exclude keywords | Not confirmed | Use local exclusions |
| Pagination / page size | Not confirmed | Do not rely on complete recall; run several narrow searches |

## Current Supported JSON Examples

These examples use only locally documented parameters. Noise control must happen in local Stage 1 filtering.

### A. Dividend Low-Vol Drawdown Control

```json
{
  "keywords": "红利低波 回撤控制 专题 金融工程",
  "orgNames": [],
  "endTime": "last1year"
}
```

### B. High Dividend Defense / Crowding / Profit Taking

```json
{
  "keywords": "高股息 策略 防守 拥挤 止盈",
  "orgNames": [],
  "endTime": "last1year"
}
```

### C. Rebalancing / Risk Budget / Volatility Target

```json
{
  "keywords": "组合 再平衡 风险预算 波动率目标 资产配置",
  "orgNames": [],
  "endTime": "last1year"
}
```

### D. Low-Vol Strategy Risk Management

```json
{
  "keywords": "低波动策略 风险管理 金融工程 专题",
  "orgNames": [],
  "endTime": "last1year"
}
```

After each search, run `research-report-filter` and only fetch paragraphs / PDFs for accepted source leads.

## Governance Rule

Before the API provider confirms advanced filtering, Research Agent must not use broad keywords such as `红利低波 回撤 控制`, `高股息 止盈`, `低波 防守`, or `组合回撤控制` as direct knowledge-base sources.

## Mandatory Two-Stage Retrieval

Stage 1: narrow search plus local title filter.

Required local title exclusions:

- 日报
- 周报
- 月报
- 晨会
- 快评
- 简评
- 点评
- 业绩点评
- 财报点评
- 半年度报告
- 年度报告
- 季报
- 估值表
- 基金净值
- 新发基金

Preferred title signals:

- 专题
- 深度
- 策略
- 金融工程
- 资产配置
- 基金研究
- 指数
- ETF
- 红利
- 低波
- 高股息
- 风险
- 回撤
- 防守
- 止盈
- 再平衡
- 波动率
- 风险预算
- 拥挤
- 配置

Stage 2: paragraph / PDF review.

For Stage 1 accepted reports:

1. Fetch paragraphs with targeted keywords.
2. Locally rerank by paragraph relevance.
3. Download or inspect PDF when a report may become A/B evidence.
4. Keep only thematic research, financial-engineering, strategy research, fund research and asset-allocation materials.
5. Mark `PDF_original_checked=true` before promoting to an evidence card.

## Current V5c Stage 1 Result

Existing V5c broad and narrow searches were filtered by the new strict Stage 1 rule:

- Output directory: `research_reports/fxbaogao_v5c_two_stage_filtered/`
- Scenario A accepted: 0
- Scenario B accepted: 0
- Scenario C accepted: 0
- Scenario D accepted: 0

Interpretation: the initial search batch must not be used as knowledge evidence. It remains a noisy source-lead archive only.

## Desired API JSON Examples

These examples are desired requests for API-provider confirmation. They are not confirmed API parameters.

### A. Dividend Low-Vol Drawdown Control

```json
{
  "keywords": "红利低波 回撤控制",
  "titleKeywords": ["红利低波", "回撤"],
  "excludeKeywords": ["日报", "周报", "月报", "业绩点评", "财报点评", "晨会", "快评"],
  "reportTypes": ["策略专题", "金融工程", "基金研究", "资产配置", "专题研究"],
  "searchFields": ["title", "summary", "paragraph"],
  "sortBy": "relevance",
  "pageSize": 50
}
```

### B. High Dividend Defense / Crowding / Profit Taking

```json
{
  "keywords": "高股息 策略 防守 拥挤 止盈",
  "titleKeywords": ["高股息", "红利"],
  "anyKeywords": ["防守", "止盈", "拥挤", "利率", "风险"],
  "excludeKeywords": ["日报", "周报", "月报", "业绩点评", "财报点评", "晨会", "快评"],
  "reportTypes": ["金融工程", "策略专题", "基金研究"],
  "sortBy": "relevance",
  "pageSize": 50
}
```

### C. Rebalancing / Risk Budget / Volatility Target

```json
{
  "keywords": "组合 再平衡 风险预算 波动率目标",
  "anyKeywords": ["再平衡", "风险预算", "波动率目标", "资产配置", "风险平价"],
  "excludeKeywords": ["日报", "周报", "月报", "晨会", "估值表", "基金净值"],
  "reportTypes": ["资产配置", "金融工程", "基金研究", "专题研究"],
  "searchFields": ["title", "summary", "paragraph"],
  "sortBy": "relevance",
  "pageSize": 50
}
```

### D. Low-Vol Strategy Risk Management Full-Text Match

```json
{
  "keywords": "低波动策略 风险管理",
  "searchFields": ["paragraph", "summary"],
  "paragraphContains": ["低波动", "风险管理"],
  "excludeKeywords": ["日报", "周报", "月报", "业绩点评", "财报点评", "晨会", "快评"],
  "reportTypes": ["金融工程", "策略专题", "基金研究"],
  "sortBy": "relevance",
  "pageSize": 50
}
```

## Local CLI

Stage 1 filtering is available through:

```text
python -m v5.cli research-report-filter <report_candidates.csv...> --out <out_dir> --include-any <term> --include-all <term>
```

This command writes:

- `filtered_report_candidates.csv`
- `rejected_report_candidates.csv`
- `filter_manifest.json`

Filtered rows are still source leads, not evidence cards.

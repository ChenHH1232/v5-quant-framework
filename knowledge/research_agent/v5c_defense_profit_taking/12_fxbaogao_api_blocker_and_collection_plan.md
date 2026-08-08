# fxbaogao API Blocker And Collection Plan

## Current Status

The fxbaogao API credential was found in the local vault at `D:\hh\保险箱\重要凭据.txt` and loaded only into the current process environment. The key was not printed or written to repository files.

Two search batches were completed:

- `research_reports/fxbaogao_v5c_defense_profit_taking/`
- `research_reports/fxbaogao_v5c_defense_profit_taking_narrow/`

The search API is usable, but broad keywords produce noisy latest-report results. Report candidates must be manually filtered and PDF-reviewed before they become evidence cards.

## Do Not Do

- Do not write the API key into repository files.
- Do not print the API key in logs.
- Do not hard-code the key in scripts.
- Do not use report summaries as PDF-verified evidence.

## Required Safe Setup

Use either:

- the local vault file, loaded only in memory;
- or a temporary session environment variable.

Never store the API key in project files.

## First Report Search Queries

When the credential is available, search these first:

1. 红利低波 回撤 控制
2. 高股息 策略 风险 止盈
3. 低波动 策略 择时 防守
4. 股息策略 利率上行 风险
5. 红利策略 拥挤交易
6. 再平衡收益 阈值再平衡
7. 组合回撤控制 风险预算
8. volatility targeting equity strategy
9. dividend low volatility risk management
10. risk parity rebalancing drawdown

## Required Report Register Fields

- report_id
- title
- institution
- author if available
- publish_date
- link: `https://www.fxbaogao.com/view?id=<report_id>`
- matched_query
- evidence_grade
- PDF_downloaded
- PDF_original_checked
- applicable_MECE_question

## Deep Read Rule

Only PDF-original-checked reports can become A/B evidence cards. Search snippets can only create source leads.

## 2026-07-26 Policy Update

API access is confirmed through the local vault, but V5c search recall is noisy. Before the API provider confirms advanced filtering, use the stricter policy in:

```text
knowledge/research_agent/v5c_defense_profit_taking/13_fxbaogao_two_stage_retrieval_policy.md
```

The initial Stage 1 strict title filter accepted zero V5c source leads. Therefore the broad and narrow search batches remain archives only and must not be converted into knowledge cards.

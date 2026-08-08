# Agent Loop Packet: telecom_specialist_policy_pm

- Objective: Harden V5b telecom operators specialist / capped sleeve governance policy
- Agent: `Project Manager Agent`
- Experiment layer: `pm_policy_gate`
- Timebox: `unlimited until stage gate reached`
- Decision target: `classify_telecom_as_capped_specialist_observation_or_keep_parked`
- User decision required: `False unless hard blockers are hit`

## Prompt

工作目录：
`D:\hh\codex\v5`

任务名称：
V5b 电信运营商 specialist / capped sleeve PM 治理审查

任务目标：
重新审查 `telecom_operators` 在 V5b 中的治理分类。重点纠正一个容易误判的问题：电信运营商只有三家，并不代表行业覆盖不足；中国三大运营商基本垄断市场，三家公司可以视为该行业的主要全市场代表。但从量化验证角度，三只股票的横截面样本过小，不能按普通行业 sleeve 的 IC / RankIC / 多因子排序标准晋升。

一次性执行到底，时间不限。不要每完成一个普通步骤就问用户。只有遇到明确阻塞条件时才停下来询问。

## 核心前提

1. V57f 是当前冻结主线，是 formal ETF candidate，但不是 accepted strategy，不是 live trading approved。
2. 不允许修改 V57f 核心 sleeve、权重、因子、调仓逻辑或交易时点。
3. 不允许把 `telecom_operators` 直接加入 V57f core。
4. 不允许因为电信运营商历史收益或回撤指标好就直接晋升。
5. 历史收益不能单独作为策略接受、观察 sleeve 晋升、核心纳入或参数选择依据。
6. 电信运营商三家公司可以代表行业垄断结构，但不能提供普通横截面因子统计所需样本量。
7. 电信应按 `capped_specialist_observation` 或 `specialist_sidecar` 治理，而不是普通核心行业 sleeve。

## 必须先阅读

- `docs\governance\status_registry.json`
- `enhanced_etf_governance_v5\current\enhanced_etf_governance_summary.json`
- `enhanced_etf_governance_v5\current\enhanced_etf_governance_report.md`
- `sector_extension_all_candidates_v5\current\all_candidates_status_matrix.csv`
- `sector_extension_all_candidates_v5\current\all_candidates_execution_summary.json`
- `telecom_engineering_readiness_v5\current\telecom_engineering_readiness_summary.json`
- `telecom_engineering_execution_v5\current\telecom_engineering_execution_summary.json`
- `v5b_etf_holdings_reference_audit\current\v5b_candidate_sector_priority.csv`
- `v5b_etf_pit_sector_gate_audit\current\v5b_etf_prior_sector_gate_matrix.csv`

## 审查问题

1. 电信运营商是否应因“三家公司样本少”被否决？
2. 三家公司是否足以代表中国电信运营商行业的主要垄断资产？
3. 普通行业 sleeve 验证标准是否适用于三寡头行业？
4. 如果不适用，应如何定义 `capped_specialist_observation` 规则？
5. 电信 sidecar 对 V57f 的贡献应看哪些指标？
6. 电信进入 paper tracking 前还缺哪些 PM 规则和证据？

## 建议治理结论

请优先考虑以下结论，但必须基于本地文件证据复核：

```text
telecom_operators:
  status: capped_specialist_observation
  reason: full oligopoly universe but insufficient cross-sectional sample for ordinary quant sleeve validation
  allowed:
    - V5b paper tracking
    - sidecar attribution
    - capped specialist sleeve policy review
    - forward evidence collection
  blocked:
    - ordinary V57f core sleeve promotion
    - return-driven weight tuning
    - IC / RankIC statistics treated as ordinary cross-sectional proof
    - modifying frozen V57f
  next_evidence:
    - capped sleeve PM policy
    - sidecar contribution to V57f drawdown / volatility / information ratio
    - forward paper evidence
    - order-health confirmation
    - telecom capex / regulatory / dividend policy state review
```

## 输出目录

生成或更新：
`v5b_telecom_specialist_policy\current\`

至少输出：

1. `v5b_telecom_specialist_policy_summary.json`
2. `v5b_telecom_specialist_policy_report.md`
3. `v5b_telecom_governance_decision.csv`
4. `v5b_telecom_allowed_blocked_actions.csv`
5. `v5b_telecom_next_evidence_queue.csv`
6. `v5b_telecom_agent_execution_rules.md`

## 内容要求

1. 明确区分“行业覆盖样本少”和“量化横截面样本少”。
2. 明确说明三大运营商可代表行业垄断结构。
3. 明确说明三只股票不足以支撑普通多因子横截面统计验证。
4. 给出是否保留电信为 V5b capped / specialist observation 的 PM 决策。
5. 给出电信 sidecar 的验证指标：
   - 对 V57f 总收益贡献；
   - 对最大回撤贡献；
   - 对波动率贡献；
   - 对信息比率贡献；
   - 与银行、电力、高速、港口铁路的相关性；
   - 极端市场期间防御表现；
   - 分红、自由现金流、资本开支状态稳定性。
6. 明确禁止事项：
   - 不得修改 V57f；
   - 不得把电信普通核心化；
   - 不得用历史收益直接晋升；
   - 不得用当前 ETF 持仓倒推历史；
   - 不得把三只股票的 IC / RankIC 当成普通统计证据。
7. 给后续 agent 一张清晰执行表：下一步做 sidecar attribution、paper tracking，还是继续 parked。

## 询问规则

只有以下情况才停下来问用户：

1. 需要用户提供 JoinQuant 导出文件。
2. 需要修改 V57f 核心策略。
3. 需要启动实盘、平台交易或外部联网获取数据。
4. 本地文件状态与上述治理结论发生实质冲突。
5. 找不到必须读取的关键治理文件。

其他情况不要询问，直接继续完成。

## 最终回复只汇报

1. 生成了哪些文件；
2. 电信是否保留为 capped / specialist observation；
3. 为什么“三家公司”不是行业覆盖失败，但仍不能普通核心化；
4. 下一步建议；
5. 是否存在阻塞。

## Governance Rule

Historical performance alone is never sufficient evidence for accepting a strategy.

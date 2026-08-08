# 银行黄金案例：可复现演示路径

## 用途

这是申请材料中的端到端演示，而非新的策略实验。案例从 V1-V4 银行多因子价值研究出发，展示 V5 如何将一个金融假设转为受审计的研究包。

## 输入

- 基础策略规格：`examples/bank_value_15y_strategy.json` 与 `examples/bank_high_dividend_sustainability_v3_strategy.json`。
- 研究假设：低估、分红、资产质量与低波动共同刻画银行价值与可持续性。
- 证据层：`docs/governance/bank_high_dividend_v3_research_validation_v1.md`、PIT 面板与平台复现材料。

## 流程

1. 研究 agent 写入因子方向、经济解释和不可接受的替代解释。
2. 数据层记录报告期、可见日、来源和缺失状态；不得用后续年报补当时不可见字段。
3. 统计 agent 在 2013-01-01 至 2021-04-30 内完成覆盖度、IC/RankIC、年度刷新、滚动与稳健性检查。
4. 项目经理冻结规则和比较合同；2021-05-01 至 2026-05-31 只作正式回测，不再挑选因子。
5. 工程 agent 生成回测、持仓、订单健康度、测试和来源哈希；平台适配不得改变策略合同。
6. PM 输出 candidate、diagnostic 或 blocked 决定，并将失败原因保留为可复查证据。

## 复现实验命令

```powershell
$env:PYTHONPATH = 'src'
python -m unittest tests.test_v5u_graduate_project_portfolio_runner
python scripts/run_v5_tests.ps1 -Tier Fast
python scripts/run_v5_tests.ps1 -Tier Standard
```

历史数据和生成产物不应被重新抓取或覆盖。复现者必须先对照 `v5u_golden_case_input_manifest.csv` 的 SHA256 与本地输入。

## 展示重点

展示“假设如何被证据支持或拒绝”，而不是只展示收益曲线。银行案例是最完整的领域样本；其余行业用于检验工作流的迁移性与边界。

# V5 可复现发布协议

## 目标

将申请材料与可运行研究代码分开，避免生成产物、原始资料和临时文件污染可复现的项目版本。

## 建议发布结构

1. `source-release`：`src/`、`tests/`、`config/`、`examples/`、`docs/` 和测试入口。
2. `evidence-bundle`：冻结的 CSV/JSON/PDF，附 SHA256 清单；不得被测试直接覆盖。
3. `application-bundle`：摘要、系统图、黄金案例、行业 scorecard、限制清单和 V5t 报告。
4. `raw-data-index`：只保留来源说明、可见日和哈希；不把受许可或大体量数据混入源码仓库。

## 发布门禁

- 记录 Git HEAD 与工作区状态，不在归档任务中执行 add、commit、reset 或 clean。
- Fast 必须通过；Standard 必须在匹配的本地 evidence-bundle 上通过。
- 所有报告显示研究窗、回测窗、基线、收益合同、候选状态和限制。
- 任何缺失原始文件必须写为 `unavailable`，不能用代理值冒充 exact reconstruction。

## 当前结论

V5 已可生成本地可追溯的申请包；托管 Standard CI 尚未就绪，因为其所需的历史研究产物目前被 `.gitignore` 排除且未被作为版本化 fixture 发布。

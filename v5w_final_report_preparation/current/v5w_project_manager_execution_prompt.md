# V5w 最终报告前期准备执行提示词

工作目录：`D:\hh\codex\v5`

目标：为研究生申请用途准备最终报告的可审计前置材料。报告应呈现 V1-V4 银行多因子价值基础如何被扩展为近似行业的 agent 研究流程，并最终形成受治理的个人化红利 ETF 式组合研究；不是实盘说明、募资材料或收益承诺。

固定边界：唯一正式基线为 `v57f_startup_preload_repaired_baseline`；正式窗口为 2021-05-01 至 2026-05-31，正式共同样本为 2021-05-06 至 2026-05-29 的 1,228 日；主候选为 `internal_subsleeve_mom12_70_30`，状态只能保持 `primary_forward_paper_candidate_not_accepted`。

分工：研究 agent 审查行业假设、金融解释与失败路径；量化 agent 复核所有正式图表和统计口径；工程 agent 复核输入、哈希、脚本和文件边界；PM 合并结论并阻止 diagnostics、执行工程、ETF 价格参考进入正式收益排序。

必须输出：
1. 正式 pairwise 年度收益/underwater 图和表，只含 baseline 与主候选；
2. 行业筛选漏斗，区分 shadow-pool、观察、人工研究和周期数据门；
3. 一张证据覆盖矩阵，明确 pre-2021 PIT、严格现金 NAV、QMT 合同、ETF total return 和前瞻纸面周期边界；
4. 最终报告目录、图表使用顺序、每图的一句限制说明；
5. 申请材料视角的作者贡献说明：金融解释提出假设，统计和 agent 提高研究规模与可复现性，PM 治理避免事后调参和越界升级。

禁止：不修改模型、窗口、费用、因子、权重、候选状态；不联网补数据；不运行 JoinQuant/QMT/桥接；不生成 future target；不将 validation_not_independent 写成独立验证；不将 ETF price return 写成 ETF total return。

最终交付应先让读者理解：研究发现了什么、没有证明什么、下一项证据门槛是什么。

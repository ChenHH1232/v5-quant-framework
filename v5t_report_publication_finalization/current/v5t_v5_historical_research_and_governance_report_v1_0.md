# V5 历史研究与治理报告 v1.0

**报告性质：历史研究与治理归档版。不是实盘策略说明书、募资材料、投资建议或收益承诺。**

## 执行摘要

本报告冻结 V5 在正式历史窗口 2021-05-01 至 2026-05-31 的研究事实。唯一正式基线为 `v57f_startup_preload_repaired_baseline`；唯一主候选为 `internal_subsleeve_mom12_70_30`，状态严格保持为 `primary_forward_paper_candidate_not_accepted`。正式表现正文只呈现二者在 2021-05-06 至 2026-05-29、1228 个共同交易日、同父策略与同一日度回报合同下的 pairwise comparison。

历史样本中，主候选相对于 repaired baseline 呈现正向观察，但这不构成独立验证、accepted、实盘或部署批准。以下限制同时适用于本摘要、主候选结论及限制章节：`strict_cash_nav_unavailable`；`qmt_contract_incomplete`；`ETF total-return 合同缺失`；`validation_not_independent`；`独立前瞻纸面周期尚未形成`。

## 1. 研究范围与治理边界

正式窗口为 2021-05-01 至 2026-05-31，首个有效信号日为 2021-05-06。startup preload 修复后的 V57f 基线是本报告唯一正式参照；旧 2021-10 链路不进入任何正式比较。报告只整理既有研究证据，不修改 V57f core、sleeve、因子、权重、调仓频率、候选状态或历史统计。

本报告使用的收益合同为同父策略的本地日度简单收益共同交易日序列。该比较是历史研究内部的可比性整理，`validation_not_independent`，不能表述为独立样本验证。

## 2. Startup Preload 修复后的正式基线

`v57f_startup_preload_repaired_baseline` 由银行、高速基础设施、港口铁路基础设施和电力公用事业四个核心 sleeve 构成。各行业专项研究、数据门及诊断结果均不能替代多 sleeve 组合的正式治理框架，也不因局部历史结果而自动进入正式表现比较。

## 3. 研究演进与边界

V5c 的防守、状态与行业知识工作保留为研究和数据证据；V5d 的分钟执行工程保留为执行可行性材料；V5e 的退出、现金与 proxy 工作保留为现金治理材料；QMT 回放及订单治理保留为平台和订单证据。它们均不构成与基线可排序的策略表现单元。

V5f 的内部子 sleeve 动量治理形成当前主候选。后续 V5k 至 V5m 固化了活动模型登记、工作流隔离、严格现金 NAV 与平台合同的证据边界。本报告不把这些工程过程包装为新的可投资模型。

## 4. 主候选的同合同比较

下表是唯一允许进入正式表现正文的比较。单位均为百分比或百分点；Alpha 为零无风险利率年化口径；信息比率按相对 repaired baseline 的日度主动收益计算；验证状态为 `validation_not_independent`。

| 模型 | 总收益 | 年化收益 | 最大回撤 | 年化波动率 | 夏普 | Alpha | Beta | 信息比率 | 相对基线超额 | 回撤差 | 样本 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `v57f_startup_preload_repaired_baseline` | 109.2546% | 16.3607% | 11.9303% | 15.6277% | 1.0481 | 0.0% | 1.0 | not_available | 0.0000 个百分点 | 0.0000 个百分点 | 1228 |
| `internal_subsleeve_mom12_70_30` | 120.6867% | 17.6378% | 11.8819% | 15.6836% | 1.1146 | 1.1189356415964908% | 0.9988996203525417 | 0.7281654911162793 | 11.4321 个百分点 | -0.0485 个百分点 | 1228 |

主候选的总收益、年化收益与夏普在该历史共同样本中高于 repaired baseline；最大回撤差为 -0.0485 个百分点，属于轻微改善。此处是样本内观察，不是关于未来表现的预测，也不构成升级依据。

## 5. 基准合同与 ETF 位置

正式基准合同仅为 repaired baseline 与主候选的同父策略日度回报比较。现有 ETF 序列仅能作为 economic exposure context：本地资料并未形成可追溯的 ETF NAV 加分红 total-return 合同。因此 ETF adjusted price return 不用于正式 ETF Alpha、Beta、信息比率或超额收益统计，也不与正式表现表混列。

## 6. 执行、成本、现金与平台证据

佣金、滑点、整手约束、停牌和涨跌停、partial-buy/skip、订单顺序与现金残余均是现实执行摩擦。`strict_cash_nav_unavailable` 意味着现有历史目标权重与收益序列不能合法反推完整现金状态；`qmt_contract_incomplete` 意味着历史提交脚本、配置、target、order、fill、position 与 cash 原件尚未形成完整合同链。两项缺口不否定诚实的历史研究报告，但阻塞 accepted、实盘和强收益承诺。

## 7. 未进入表现比较的研究线

V5c 诊断、V5d/V5h/V5i/V5j 的执行与技术研究、V5e 现金与退出研究、QMT 回放、订单治理，以及 ETF 经济暴露参考，都在证据附录边界内呈现。它们可能帮助解释研究过程或暴露执行问题，但没有与主候选相同的模型、窗口和回报合同，不能参与收益排名。

## 8. 主候选结论与升级门槛

`internal_subsleeve_mom12_70_30` 保持 `primary_forward_paper_candidate_not_accepted`。历史共同样本的相对改善不足以替代以下缺失证据：`strict_cash_nav_unavailable`；`qmt_contract_incomplete`；`ETF total-return 合同缺失`；`validation_not_independent`；`独立前瞻纸面周期尚未形成`。因此本报告不将其写作 accepted、live、deployment approved 或独立验证通过。

任何未来升级都应先获得授权，并从首笔纸面订单开始留存完整的 `target -> order -> fill -> position -> cash` 状态链；随后再按预先固定的治理门槛复核。本文不生成未来 target、不启动平台，也不提供下单建议。

## 9. 限制与未解证据

`strict_cash_nav_unavailable`；`qmt_contract_incomplete`；`ETF total-return 合同缺失`；`validation_not_independent`；`独立前瞻纸面周期尚未形成`。

- `strict_cash_nav_unavailable`：严格现金状态与 NAV 尚不能由既有材料合法复原。
- `qmt_contract_incomplete`：缺少历史平台执行合同原件，不能声称精确成交归因。
- `ETF total-return 合同缺失`：ETF 仅作经济暴露参考，不存在正式相对收益统计。
- `validation_not_independent`：历史比较不是独立验证。
- `独立前瞻纸面周期尚未形成`：尚没有足够的前瞻闭环证据支持候选升级。

## 10. 结论

V5 已形成一条可以归档、可追溯的历史研究主线：repaired baseline 是唯一正式基线，`internal_subsleeve_mom12_70_30` 是唯一 primary forward/paper candidate。报告证实的是有限历史合同下的相对观察和治理边界；报告没有证明策略已被独立验证、已获接受或可用于实盘。

## 附录 A：统计口径与证据索引

- 正式市场数据边界：2026-05-31。
- 正式表现样本：2021-05-06 至 2026-05-29，1228 个共同交易日。
- 数字复核来源：`v5s_numeric_reconciliation.csv`，26 个字段零冲突。
- 证据来源与 SHA256：`v5t_publication_input_manifest.csv`。
- 论断与证据：`v5t_final_claim_evidence_register.csv`。
- 诊断、执行和平台材料的附录边界：V5s/V5q 的审计文件与 V5t 的 `v5t_statistics_and_table_audit.csv`。

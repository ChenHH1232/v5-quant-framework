# 个性化红利 ETF 式组合方法说明

## 定位

这是研究型、规则驱动的个性化红利 ETF 式组合方法，不是对任何商业 ETF 的复制、推荐或总回报比较。商业 ETF 仅可作为经济暴露背景；当前本地资料没有可追溯 NAV 加分红合同，因此不计算正式 ETF Alpha、Beta、信息比率或超额收益。

## 成分与分层

- 核心 sleeve：bank、utilities_electricity、highway_infrastructure、port_rail_infrastructure。
- 行业角色：银行为金融价值与质量；其余 sleeve 为非金融现金流核心或候选。
- 因子库：operating_cash_flow_yield、dividend_yield_decimal、volatility_120d、max_drawdown_120d、capex_burden、low_price_to_book、non_performing_loan_ratio、provision_coverage_ratio、core_tier_1_capital_adequacy_ratio。
- 银行使用行业覆写的资产质量和资本充足率字段；非金融行业保留经营现金流、估值与风险字段。

## 投资组合合同

- 目标持仓数：28。
- 单行业上限：25%；单股上限：5%。
- 调仓频率：quarterly。
- 权重：equal_weight_after_sector_and_single_stock_caps。
- 调仓日：各 sleeve 合法 PIT 信号日的并集；不以未来财报或事后行业表现调整权重。

## 研究边界

`v57f_startup_preload_repaired_baseline` 是冻结的正式基线。`internal_subsleeve_mom12_70_30` 仅在已选股票池内进行 sleeve 内权重治理，不新增股票、不跨 sleeve 转移，也不替代 V57f core。历史结果不能变成 ETF 产品承诺。

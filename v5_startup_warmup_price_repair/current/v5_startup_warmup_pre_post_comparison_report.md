# V5 Startup Warmup Repair Pre/Post Comparison Report

## 结论

本次修复解决的是 V57f 部署启动时缺少部署日前历史价格导致无法初始建仓的问题。修复后，V57f shadow 链路可以在 `2021-05-06` 生成初始建仓信号并成交，不再等到 `2021-10-08`。

这不是调参，不是修改 V57f 选股逻辑，也不是策略 accepted。原 V57f core config 未覆盖；本次只生成 startup repaired shadow config 和 repaired price / panel 数据。

## 修复范围状态

| 模块 | 修复状态 | 说明 |
|---|---|---|
| V57f startup preload | completed | first_signal / first_trade 提前到 `2021-05-06` |
| V57f daily backtest | completed | 基于 repaired shadow config 重跑完成 |
| V57f execution robustness | completed | 8 个执行鲁棒性变体重跑完成 |
| ERC overlay | completed diagnostic | 基于 repaired schedule 重跑完成，仍不是 accepted |
| V5d L2 size-aware | blocked | 缺 `2021-05-06` 初始 D0 5分钟数据 |
| V5d L3 default_exception | blocked | 缺初始 D0 5分钟数据 |
| V5d L4 completion | blocked | 缺初始 D0/D1/D2 5分钟数据 |
| V5e | not started | startup 日频主修复过关后可进入 PM 决策 |

## 启动日期对比

| 项目 | 修复前 | 修复后 | 变化 |
|---|---:|---:|---:|
| deployment_date | 2021-05-01 | 2021-05-01 | 不变 |
| first_tradable_date | 2021-05-06 | 2021-05-06 | 不变 |
| first_signal | 2021-10-08 | 2021-05-06 | 提前 155 天 |
| first_trade | 2021-10-08 | 2021-05-06 | 提前 155 天 |
| first_position | 2021-10-08 | 2021-05-06 | 提前 155 天 |
| startup_gap | 160 天 | 5 天 | 减少 155 天 |

## V57f 日频结果对比

| 指标 | 修复前 | 修复后 | 变化 |
|---|---:|---:|---:|
| signal_count | 19 | 21 | +2 |
| daily_count | 1125 | 1228 | +103 |
| trade_count | 709 | 783 | +74 |
| dividend_count | 128 | 158 | +30 |
| strategy_return | 81.42% | 109.25% | +27.84 pct |
| annualized_return | 14.27% | 16.36% | +2.09 pct |
| benchmark_return | 51.01% | 79.01% | +28.00 pct |
| excess_return | 30.40% | 30.25% | -0.16 pct |
| max_drawdown | 11.75% | 11.93% | +0.18 pct |
| strategy_volatility | 15.64% | 15.62% | -0.02 pct |
| Sharpe | 0.932 | 1.049 | +0.117 |
| information_ratio | 0.444 | 0.335 | -0.109 |

主要变化来自修复后纳入 `2021-05-06` 至 `2021-10-07` 真实可交易窗口，而不是修改选股或权重。由于 benchmark 同期也被纳入，absolute return 明显增加，但 excess return 基本持平。

## ERC 对比

| 指标 | 旧 ERC | repaired ERC | 变化 |
|---|---:|---:|---:|
| equal_reference_return | 81.42% | 109.25% | +27.84 pct |
| ERC return | 82.53% | 109.44% | +26.90 pct |
| ERC vs equal_reference | +1.12 pct | +0.18 pct | -0.93 pct |
| max_drawdown | 11.75% | 11.93% | +0.18 pct |
| volatility | 15.69% | 15.52% | -0.17 pct |
| trade_count | 709 | 784 | +75 |
| risk concentration HHI delta | -0.00526 | -0.00758 | 改善扩大 |

ERC repaired 后仍是 risk-budget diagnostic。它没有被标记为 accepted，也不是 V57f replacement。

## 数据修复覆盖

| sleeve | candidate codes | repaired coverage | earliest date | latest date | rows |
|---|---:|---:|---:|---:|---:|
| bank | 42 | 42/42 | 2019-01-02 | 2026-05-29 | 71,246 |
| utilities_electricity | 128 | 128/128 | 2019-01-02 | 2026-05-29 | 221,206 |
| highway_infrastructure | 13 | 13/13 | 2019-01-02 | 2026-05-29 | 23,322 |
| port_rail_infrastructure | 21 | 21/21 | 2019-01-02 | 2026-05-29 | 36,841 |

短历史候选股已记录为 warning，主要是 2021 年后上市或部署日前不足 252 个交易日的股票。没有用未来价格填充，也没有伪造 high_limit / low_limit / paused 字段。

## 治理判断

| 项目 | 结论 |
|---|---|
| 是否修改 V57f core | 否 |
| 是否覆盖原始 V57f config | 否 |
| 是否修改 sleeve / 因子 / 权重 / cap / target_count / 调仓频率 | 否 |
| 是否使用未来数据生成部署日信号 | 否 |
| 是否启动 V5e | 否 |
| 是否标记 accepted | 否 |
| startup warmup 日频 blocker | 已解除 |
| V5d 初始分钟数据 blocker | 仍存在 |

## 下一步

第一选择：进入 startup 修复 PM review，确认 shadow config 和 repaired data gate 是否可作为后续部署工程基线。

如果要完整修复 V5d 执行层，需要先补 `2021-05-06`、D+1、D+2 的 BaoStock 5分钟数据，然后重跑 L2/L3/L4。否则不要声称 V5d 全链路已修复。

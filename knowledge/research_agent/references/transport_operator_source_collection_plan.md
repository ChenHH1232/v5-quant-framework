# Transport Operator Source Collection Plan

Date: 2026-07-19

Owner:

```text
Research Agent
```

Status:

```text
source_collection_plan
supports_v58_manual_research_queue
not_pit_factor_evidence
```

## Research Boundary

This plan covers A-share transport operators that may fit the dividend low-volatility and cash-flow basket path but are not already covered by the approved highway or port / rail sleeves.

Included candidates:

```text
airport operators
urban public transport / metro operators when listed and business-pure
toll-like transport infrastructure operators not already in highway V5.4h
```

Excluded by default:

```text
airlines
shipping
freight forwarding
express delivery
logistics trade
equipment manufacturers
non-transport conglomerates
```

## Source Priority

| Source | Use | PIT rule |
| --- | --- | --- |
| JoinQuant / DataJQ | daily prices, dividends, PIT financials, industry membership | usable as PIT vendor proxy after coverage audit |
| Annual / interim reports | business purity, route / airport / concession exposure, capex plan | must retain announcement date |
| Exchange / CNINFO announcements | original report and disclosure dates | preferred original source |
| Eastmoney F10 | first-layer business-segment clues | requires report spot check before formal handoff |
| Industry reports | business logic, operating variables, risk themes | knowledge only, not scoring data |
| Official statistics | passenger throughput, cargo throughput, traffic recovery, policy state | must record release date before factor use |

## MECE Research Questions

| Question | Judgment to verify | Search keywords | Evidence type |
| --- | --- | --- | --- |
| Business purity | Which companies are true transport operators rather than logistics / trade / airline cycle names? | 交通运输 红利资产 机场 公路 港口 铁路 运营 | annual report segment data |
| Cash-flow stability | Does operating cash flow persist through weak demand years? | 交通基础设施 现金流 分红 高速 港口 铁路 机场 | financial PIT panel, reports |
| External state | Which operating state best explains weak periods? | 机场 吞吐量 客流 货运 周期 通行费 | official statistics, reports |
| Dividend support | Is dividend yield supported by OCF and payout discipline? | 交通运输 分红比例 红利资产 现金流 | dividend records, payout data |
| Capex trap | Does expansion capex or recovery capex consume distributable cash? | 交通基础设施 capex 资本开支 REITs | capex fields, annual reports |

## Existing Report Leads

- [5313068 - 交通运输行业事项点评：HALO资产优等生，重新定价稀缺性：港口、铁路投资机遇解析](https://www.fxbaogao.com/view?id=5313068)
- [5403030 - 华创交运红利资产2025年报及2026年一季报综述：公路稳健，港口景气向上+提分红，铁路、大宗边际改善趋势强](https://www.fxbaogao.com/view?id=5403030)
- [5322100 - 快递涨价区域蔓延，避险推荐高速公路](https://www.fxbaogao.com/view?id=5322100)
- [5510356 - 基础设施行业2026年中期策略报告：关注市场风格转变，红利资产配置价值持续提升](https://www.fxbaogao.com/view?id=5510356)
- [5193718 - 交通基础设施公募REITs发行现状及堵点分析](https://www.fxbaogao.com/view?id=5193718)

## Output Required Before Quant

```text
transport_operator_universe_candidate.csv
transport_operator_business_purity_evidence.csv
transport_operator_external_state_field_map.md
transport_operator_cashflow_hypothesis.md
```

Historical performance alone is never sufficient evidence for accepting a strategy.

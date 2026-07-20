# Oil / Gas Pipeline And Integrated Energy Source Collection Plan V5.8a

Date: 2026-07-20

Owner:

```text
Research Agent
```

Status:

```text
industry_knowledge_gate_started
not_quant_ready
not_formal_modeling
```

## Research Boundary

Sector:

```text
oil_gas_pipeline_integrated
```

Scope:

```text
A-share listed oil and gas upstream, integrated oil companies, pipeline / storage / LNG infrastructure operators, and closely related energy operators that may fit a dividend low-volatility cash-flow basket.
```

Initial exclusions:

```text
pure oilfield service equipment without dividend stability
pure petrochemical commodity processors without clear shareholder-return policy
coal-chemical substitutes
trading companies without asset-operation cash-flow visibility
```

## MECE Research Questions

| Order | Question | Judgment To Validate | Search Keywords | Evidence Needed |
| ---: | --- | --- | --- | --- |
| 1 | Business exposure | Is the company exposed to upstream oil price, downstream refining spread, regulated pipeline tariff, LNG/gas demand, or mixed petrochemical cycle? | 油气 上游 下游 管道 LNG 炼化 分部收入 | annual reports, segment tables, PIT business tags |
| 2 | Cash-flow quality | Does OCF reflect durable operating cash generation, or mostly working-capital / commodity price timing? | 石油 天然气 经营现金流 营运资本 库存 | cash-flow statements, inventory / receivables notes |
| 3 | FCF / capex quality | Is capex maintenance-like, growth / reserve replacement, policy mandated, or cycle chasing? | 油气 资本开支 自由现金流 储量 开发 | capex notes, reserve replacement, project-cycle disclosures |
| 4 | Dividend sustainability | Is the dividend covered by recurring cash-flow and balance sheet capacity, not just state-owner payout policy? | 油气 高股息 分红 派息率 现金流覆盖 | dividend events, payout ratio, net debt, cash coverage |
| 5 | External state | Which ex-ante states are mandatory before Quant validation? | 油价 天然气价格 管输费 炼化价差 库存 | Brent / WTI, domestic gas price, refining spread, pipeline tariff, inventory / demand state |
| 6 | Value traps | Which high-dividend oil/gas names should be excluded or guarded? | 油气 价值陷阱 油价 下跌 资本开支 负债 | leverage, capex spike, declining reserves, refining losses, policy changes |

## First-Pass FxBaogao Searches

Local output directory:

```text
research_reports/fxbaogao_v58_oil_gas_fcf_dividend/
```

Search packets:

| Packet | Keywords | Output |
| --- | --- | --- |
| business_cashflow_capex | 油气 管道 高股息 自由现金流 资本开支 | `research_reports/fxbaogao_v58_oil_gas_fcf_dividend/business_cashflow_capex/` |
| dividend_ocf_capex | 石油 天然气 分红 经营现金流 资本开支 | `research_reports/fxbaogao_v58_oil_gas_fcf_dividend/dividend_ocf_capex/` |
| refining_spread_fcf | 炼化 价差 分红 自由现金流 | `research_reports/fxbaogao_v58_oil_gas_fcf_dividend/refining_spread_fcf/` |
| three_oils_dividend_cashflow | 三桶油 高股息 现金流 资本开支 | `research_reports/fxbaogao_v58_oil_gas_fcf_dividend/three_oils_dividend_cashflow/` |
| external_state_price_tariff | 油价 天然气价格 管输费 油气公司 现金流 | `research_reports/fxbaogao_v58_oil_gas_fcf_dividend/external_state_price_tariff/` |

## Candidate Source Register

| Role | Report | Source Use | PIT Status |
| --- | --- | --- | --- |
| Cross-industry FCF / dividend framework | [5421725 - 25年自由现金流大盘点--多行业联合红利资产4月报](https://www.fxbaogao.com/view?id=5421725) | Supports cash-flow / capex framework and notes petrochemical cash-flow recovery themes | Research-only; sector fields still need report-date PIT source rows |
| Oil/gas external state | [5540392 - 油气行业月报：6月全球油价大幅下跌，7月美伊谈判反复油价反弹](https://www.fxbaogao.com/view?id=5540392) | External oil-price regime and geopolitical state background | Research-only; must be converted to ex-ante monthly state before Quant |
| Oil/gas external state | [5411774 - 油气行业2026年4月月报：美以伊冲突持续，油价维持高位，关注霍尔木兹海峡通航情况](https://www.fxbaogao.com/view?id=5411774) | Oil-price / route-risk state background | Research-only; visible after publication date |
| Capex-cycle risk | [5332923 - 海上油气资本开支持续上行，海上油服或将持续受益](https://www.fxbaogao.com/view?id=5332923) | Shows capex cycle can be structurally rising in parts of oil/gas, so raw FCF may penalize growth / reserve investment | Research-only; not a factor input |

## Required Data Gate Before Quant

Quant Validation Agent must not run formal validation until Research / Engineering can provide:

```text
PIT business exposure tags
real daily open / close prices
cash dividends with visible dates
Brent / WTI or domestic oil-price state
domestic natural-gas price or LNG state
refining spread / downstream margin state
pipeline tariff or policy state where applicable
capex-to-OCF and capex-cycle classification
inventory / working-capital pressure where relevant
```

## Stop Rule

Stop after two Research loops if no PIT-visible external state path can be found. In that case, archive oil/gas as:

```text
workflow_prepared
blocked_by_cycle_state_data_gate
```

Hard rule:

```text
Research reports are hypothesis sources only. They are not accepted factor data.
```

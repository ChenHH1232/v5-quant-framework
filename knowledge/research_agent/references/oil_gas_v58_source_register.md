# Oil / Gas V5.8a FxBaogao Source Register

Date: 2026-07-20

Status:

```text
first_pass_report_search_completed
research_only
```

Local cache:

```text
research_reports/fxbaogao_v58_oil_gas_fcf_dividend/
```

## Search Packets

| Packet | Keywords | Status |
| --- | --- | --- |
| business_cashflow_capex | 油气 管道 高股息 自由现金流 资本开支 | completed |
| dividend_ocf_capex | 石油 天然气 分红 经营现金流 资本开支 | completed |
| refining_spread_fcf | 炼化 价差 分红 自由现金流 | completed |
| three_oils_dividend_cashflow | 三桶油 高股息 现金流 资本开支 | completed |
| external_state_price_tariff | 油价 天然气价格 管输费 油气公司 现金流 | completed |

## Selected Candidate Reports

| Report ID | Title | Organization | Use |
| --- | --- | --- | --- |
| [5421725](https://www.fxbaogao.com/view?id=5421725) | 25年自由现金流大盘点--多行业联合红利资产4月报 | 华创证券 | Cross-industry FCF / capex / dividend framework |
| [5540392](https://www.fxbaogao.com/view?id=5540392) | 油气行业月报：6月全球油价大幅下跌，7月美伊谈判反复油价反弹 | 国信证券 | Oil-price state and geopolitical state candidate |
| [5411774](https://www.fxbaogao.com/view?id=5411774) | 油气行业2026年4月月报：美以伊冲突持续，油价维持高位，关注霍尔木兹海峡通航情况 | 国信证券 | Oil-price / route-risk state candidate |
| [5332923](https://www.fxbaogao.com/view?id=5332923) | 海上油气资本开支持续上行，海上油服或将持续受益 | 国金证券 | Capex-cycle and oilfield-service exposure context |

## First-Pass Findings

1. Oil / gas has cash-flow and dividend potential, but capex and commodity-cycle state are central.
2. Cross-industry FCF reports classify petrochemical / coal / steel cash-flow recovery as cycle-sensitive rather than stable utility-like cash-flow.
3. Oil-price monthly reports are useful for state design, but the state variables must be converted into PIT monthly data before Quant validation.
4. Offshore oil/gas capex can rise structurally even when broad upstream capex weakens, so raw FCF may incorrectly penalize reserve replacement or offshore development.

## Evidence Limits

These reports may generate hypotheses only. They cannot directly become:

```text
factor values
stock weights
accepted strategy evidence
platform replication evidence
```

Formal factor data still requires:

```text
original announcement date
visible date
field definition
PIT join policy
coverage report
```

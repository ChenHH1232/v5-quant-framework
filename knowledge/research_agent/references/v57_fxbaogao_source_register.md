# V5.7 FxBaogao Source Register

Date: 2026-07-18

Owner:

```text
Research Agent
```

Status:

```text
first_pass_source_register
paragraph_screening_completed_for_core_items
PDF_review_required_before_formal_citation_or_factor_use
```

## Source Policy

FxBaogao reports are approved for:

```text
industry knowledge
hypothesis design
field discovery
source discovery
```

They are not approved for:

```text
direct PIT factor data
strategy acceptance
return tuning
```

Official reading links use:

```text
https://www.fxbaogao.com/view?id=<report_id>
```

## Collection Outputs

| Theme | Local Output |
| --- | --- |
| OCF / FCF sector coverage | `research_reports/fxbaogao_v57_ocf_fcf_sector_coverage/report_candidates.csv` |
| Telecom FCF / dividend | `research_reports/fxbaogao_v57_telecom_fcf_dividend/report_candidates.csv` |
| Telecom refreshed search | `research_reports/fxbaogao_v57_three_telecom_operators_dividend_fcf/report_candidates.csv` |
| Cross-industry FCF framework | `research_reports/fxbaogao_v57_fcf_quality_framework/report_candidates.csv` |
| Cross-industry FCF low-vol refresh | `research_reports/fxbaogao_v57_cross_industry_fcf_low_vol_framework/report_candidates.csv` |
| Gas / water FCF dividend | `research_reports/fxbaogao_v57_gas_water_fcf_dividend/report_candidates.csv` |
| Transport infrastructure FCF dividend | `research_reports/fxbaogao_v57_transport_infra_fcf_dividend/report_candidates.csv` |
| Paragraph extracts | `research_reports/fxbaogao_v57_paragraphs/` |

## Core Reports

| Priority | Report | Use In V5.7 | Current Status |
| --- | --- | --- | --- |
| Core | [5421725 - 25年自由现金流大盘点--多行业联合红利资产4月报](https://www.fxbaogao.com/view?id=5421725) | Cross-industry OCF/FCF and dividend asset framework | Paragraph screened; PDF review required for formal citation |
| Core | [5385601 - 中银中证全指自由现金流ETF投资价值分析：现金流：存量经济下企业经营范式革命](https://www.fxbaogao.com/view?id=5385601) | FCF index logic, FCF versus dividend comparison, capex-cycle interpretation | Paragraph screened; use as framework source only |
| Core | [5337413 - 公用事业行业深度跟踪：年报初窥，现金流改善分红提升，公用事业化加速推进](https://www.fxbaogao.com/view?id=5337413) | Utilities / gas / water operator cash-flow and dividend context | Paragraph screened |
| Core | [5462617 - 2026年水务行业分析：水价改革渐进式推进，关注水务企业盈利承压、债务扩张与回款风险](https://www.fxbaogao.com/view?id=5462617) | Water-operator receivables, debt and tariff risk | Paragraph screened |
| Core | [5403030 - 华创交运红利资产2025年报及2026一季报综述：公路稳健，港口景气向上+提分红，铁路、大宗边际改善趋势强](https://www.fxbaogao.com/view?id=5403030) | Highway / port / rail dividend, cash-flow and operating-state framework | Paragraph screened |
| Core | [5313068 - 交通运输行业事项点评：HALO资产优等生，重新定价稀缺性：港口、铁路投资机遇解析](https://www.fxbaogao.com/view?id=5313068) | Port / railway hard-asset moat and dividend logic | Paragraph screened |
| Specialist | [5442278 - 中国电信2025年报及2026年一季报点评：算力规模显著提升，Token经营迈入新台阶](https://www.fxbaogao.com/view?id=5442278) | Telecom operator observation sleeve, capex and cash-flow context | Paragraph screened; telecom search remains noisy |

## First-Pass Knowledge Notes

### Cross-Industry OCF / FCF

The report screen supports V5.6c's reset direction:

- FCF can be useful, but it is sensitive to capex stage and sector accounting.
- OCF is a cleaner first-layer cash-generation signal across multiple operator sectors.
- FCF should become a sector-approved enhancement only after capex-quality review.
- Dividend yield needs cash-flow coverage and debt-pressure checks.

Research implication:

```text
Do not rebuild the basket around low PB / raw FCF. Keep OCF as mainline and make FCF sector-conditional.
```

### Gas / Water

The screen confirms this is close to the utilities golden template, but not automatically clean:

- water-price reform can improve long-term earning power;
- receivables, government payment, debt expansion and project revenue can turn apparent cash-flow value into a trap;
- operator-purity review is required before modeling.

Research implication:

```text
Gas / water may be the next formal sector after a business-purity and receivables gate is built.
```

### Telecom

The search results are noisier than utilities and transport:

- direct operator cash-flow and dividend reports exist, but many hits are technology, AI or white-paper themes;
- the A-share operator universe is very small;
- capex cycle and depreciation burden matter more than simple broad IC.

Research implication:

```text
Telecom should remain an observation sleeve until PM approves a small-sample sleeve policy.
```

### Transport Infrastructure

The report screen is consistent with V5.4 and V5.5:

- highway, port and railway operators have strong dividend / hard-asset logic;
- operating-purity matters because logistics, trade and non-main-business exposure can distort cash-flow;
- external operating state is still useful, but business-source review already improves the framework.

Research implication:

```text
Transport infrastructure remains eligible for shadow-basket inclusion, with business-purity and operating-state gates preserved.
```

## Required Follow-Up

1. Download and review PDFs before using exact report quotes or numeric tables in formal documents.
2. Build `sector_fcf_capex_quality_gate_v1`.
3. For gas / water, collect PIT business-purity and receivables evidence before formal validation.
4. For telecom, create a small-sample sleeve policy before treating it as more than observation.
5. For transport infrastructure, use reports as context only; keep original annual-report business-source review as the formal evidence layer.

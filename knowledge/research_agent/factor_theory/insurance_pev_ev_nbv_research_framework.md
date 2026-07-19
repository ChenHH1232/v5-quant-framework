# Insurance P/EV, EV and NBV Research Framework

Date: 2026-07-17

Status:

```text
research_knowledge_added_not_validated_factor
```

## Research Boundary

This note supports V5.3 insurance research after the low-PB, investment-return and solvency-guard variants were rejected or blocked.

Scope:

- A-share listed core insurance companies and insurance groups.
- Life-insurance value logic first; P&C and mixed insurance groups require explicit subgroup notes.
- Research reports are used to build economic hypotheses only.
- PIT factor use still requires original annual-report or official disclosure dates.

## MECE Questions

| Question | Research use | Quant handoff |
| --- | --- | --- |
| Why not rely only on PB? | Insurance book value misses long-duration policy value and franchise value. | Compare PB vs P/EV on common PIT sample. |
| What does EV represent? | EV is a disclosed actuarial estimate of in-force policy value plus adjusted net assets. | Use only after source date and definition are reviewed. |
| What does NBV represent? | NBV measures current-period value creation from new policies. | Test NBV growth as franchise-quality variable. |
| When can low P/EV be a value trap? | Low P/EV may reflect distrust in EV assumptions, rate assumptions or future investment return. | Add state and failure-year diagnostics; do not accept low P/EV alone. |
| What makes cross-company comparison risky? | Group EV, life-only EV and life-plus-health EV are not identical. | Validate life-only, group and combined口径 separately where possible. |

## Core Findings From Reports

1. P/EV is a better insurance valuation anchor than PB when the company is primarily life-insurance driven, because EV tries to capture the economic value of in-force policies and adjusted net assets.
2. NBV is the franchise-growth layer: it indicates whether current new business is creating future embedded value.
3. P/EV below 1 is not automatically cheap. It may mean the market doubts long-term investment-return assumptions, discount-rate assumptions or expense/mortality assumptions.
4. Long-end interest-rate state matters because EV and P/EV credibility are sensitive to investment return assumptions.
5. P/EV comparability is weak unless the EV definition is consistent: group EV, life-insurance EV, and life-plus-health EV must be labeled separately.

## V5.3f Hypotheses

### H1. P/EV Replacement Hypothesis

Low P/EV should be tested against low PB on the same PIT sample.

Expected evidence:

- positive IC/RankIC after direction adjustment;
- better rolling behavior than PB-only in at least some weak years;
- no future visible-date violations.

### H2. NBV Growth Franchise Hypothesis

NBV growth may help distinguish cheap insurers with improving franchise value from low-PB value traps.

Expected evidence:

- NBV growth improves common-sample ranking versus P/EV alone;
- it should be most useful when equity and rate states are not extreme stress states.

### H3. EV Credibility State Hypothesis

P/EV discount requires state interpretation. Low P/EV may fail when long-end rates are falling, equity markets are weak, or EV assumptions are being distrusted.

Expected evidence:

- failure years 2021, 2022 and 2026 should be explainable by rate/equity/EV assumption stress before adding any timing rule.

## Data Gate

P/EV cannot enter formal validation until:

- EV and NBV rows have original announcement dates;
- conservative visible dates are no later than rebalance dates;
- at least five core insurance codes have usable EV coverage;
- coverage spans enough years for rolling validation;
- EV口径 is labeled as `group`, `life_only`, or `life_plus_health`;
- P/EV is derived from market cap available at the trade date and latest visible EV.

## Evidence Sources

- [5475175 - 保险行业深度研究报告：寻找寿险估值锚，PEV是否失效？](https://www.fxbaogao.com/view?id=5475175)
- [5485275 - 保险行业研究框架系列三：保险公司价值评估](https://www.fxbaogao.com/view?id=5485275)
- [5195616 - 2026年A股保险行业年度策略报告：重返1倍PEV修复途，资产负债两端开花](https://www.fxbaogao.com/view?id=5195616)
- [5340050 - 保险行业2025年报总结：长期资金持续入市，银保驱动价值高增](https://www.fxbaogao.com/view?id=5340050)
- [5466811 - 保险行业2026年中期策略：寻找中国保险股的阿尔法](https://www.fxbaogao.com/view?id=5466811)
- [5504121 - 保险行业2026年中期投资策略：资负管理护航长期经营，静待估值向基本面回归](https://www.fxbaogao.com/view?id=5504121)

## Research Agent Decision

Insurance research may proceed only through:

```text
EV/NBV/P/EV PIT repair -> common-sample Quant validation -> PM decision
```

It should not continue low-PB plus simple quality, simple solvency guard, or weight-tuning variants.

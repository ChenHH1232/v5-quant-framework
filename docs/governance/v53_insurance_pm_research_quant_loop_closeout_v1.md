# Governance Record: v53_insurance_pm_research_quant_loop_closeout_v1

Date: 2026-07-17

Project:

```text
V5.3 Insurance Research-Quant Iteration Closeout
```

PM decision:

```text
insurance_research_signal_exists_but_not_deployable_until_ev_nbv_pit_repair
```

## Iteration Summary

Research Agent and Quant Validation Agent completed the insurance loop after V5.3d and V5.3e.

Completed research attempts:

| Version | Research idea | Quant result | PM decision |
| --- | --- | --- | --- |
| V5.3c | low PB only | PIT signal exists, but 2021 / 2026 and concentration risk remain | diagnostic candidate only |
| V5.3d | low PB + total investment return + solvency score | composite underperformed low PB | rejected |
| V5.3e | low PB + solvency guard + state diagnostics | guard underperformed low PB; states inconclusive | rejected |

## Agent Findings

Research Agent conclusion:

```text
The next useful insurance research path is multi-year PIT EV / NBV / P/EV repair. Subgroup models should be a validation dimension after data repair, not the main path before data repair.
```

Quant Validation Agent conclusion:

```text
The existing PIT panel is not enough to formally validate life / P&C / insurance-group submodels. The cross-section is too thin.
```

Current subgroup coverage:

| Subgroup | Codes | Dates | Formal submodel status |
| --- | ---: | ---: | --- |
| insurance_group | 2 | 41 | blocked by insufficient cross-section |
| life_insurance | 2 | 41 | blocked by insufficient cross-section |
| pnc_insurance_group | 1 | 29 | blocked by insufficient cross-section |

## PM Interpretation

The insurance line has a real but incomplete signal:

- low PB has repeatable diagnostic evidence;
- low PB alone is too crude for deployment;
- simple quality factors and simple solvency guards do not solve the weak years;
- submodel validation is statistically blocked by too few securities;
- insurance-specific economic value needs EV / NBV / P/EV data.

Therefore the blocker is no longer model iteration. It is a data gate.

## Governance Status

Insurance is not:

```text
formal_strategy_candidate
platform_replication_ready
paper_trading_ready
accepted_strategy
joinquant_code_ready
```

Insurance is:

```text
research_signal_exists_but_not_deployable
blocked_until_ev_nbv_pit_repair
```

## Only Approved Next Gate

The only approved next gate is:

```text
ev_nbv_pev_multi_year_pit_data_repair
```

Required fields:

- embedded_value;
- new_business_value;
- embedded_value_yoy;
- new_business_value_yoy;
- market_cap;
- report_period;
- original_announcement_date;
- conservative_visible_date;
- source document and field-definition evidence.

After repair, Quant Agent may test:

- P/EV vs PB on the common sample;
- EV growth and NBV growth as franchise-quality variables;
- life-only / group / combined coverage separately;
- 2021 / 2022 / 2026 failure-year explanation.

If PIT EV / NBV repair fails, PM should pause insurance as:

```text
research_signal_exists_but_not_deployable
```


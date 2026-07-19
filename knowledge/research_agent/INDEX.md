# Research Agent Knowledge Index

## Governance

- [Research-Quant iteration protocol](../../docs/governance/research_quant_iteration_protocol_v1.md) - failed or weak validation returns to Research Agent for hypothesis revision, replacement, or archival.
- [Sector research knowledge gate](../../docs/governance/sector_research_knowledge_gate_v1.md) - new sectors must have a Research Agent knowledge packet before formal validation.
- [Sector data availability gate template](../../docs/governance/sector_data_availability_gate_template.md) - PM gate combining research knowledge, PIT universe, data availability, engineering data, and source access review.

## Market Structure

- [JoinQuant execution matching requires real-price data](market_structure/joinquant_execution_price_alignment.md)

## Data Sources

- [Bank sector research references](references/bank_sector_references.md)
- [Bank knowledge collection source register](references/source_register_bank_sector.md) - first-pass official/regulatory and academic source register completed; market/industry protected sources marked for manual review.
- [Utilities source collection plan](references/utilities_source_collection_plan.md) - V5.1 preparation source order and source-risk guardrails.
- [Utilities special information sources](references/utilities_special_information_sources.md) - sector-specific data layers for power, gas and water utilities.
- [Bank regulatory definitions](references/bank_regulatory_definitions.md) - first-pass official definition layer completed.
- [Bank academic theory sources](references/bank_academic_theory_sources.md) - first-pass theory source layer completed.
- [Bank disclosure field map](references/bank_disclosure_field_map.md) - pending collection.
- [Bank industry research sources](references/bank_industry_research_sources.md) - pending collection.
- [Bank market-view hypotheses](references/bank_market_view_hypotheses.md) - market views only, pending collection.
- [Bank factor validation handoff](references/bank_factor_validation_handoff.md) - pending handoff to Quant Validation Agent.
- [Utilities universe definition](references/utilities_universe_definition.md) - V5.1 operating-company universe boundary.
- [Utilities data field map](references/utilities_data_field_map.md) - required PIT fields and source risks.
- [Utilities validation handoff](references/utilities_validation_handoff.md) - Quant Validation Agent task requirements for Test-1.
- [Coal universe definition](references/coal_universe_definition.md) - V5.2 coal mining and operating-company boundary.
- [Coal data field map](references/coal_data_field_map.md) - stock-level and external coal-cycle PIT field requirements.
- [Coal source collection plan](references/coal_source_collection_plan.md) - candidate sources for coal price, output, inventory and spread state.
- [Coal validation handoff](references/coal_validation_handoff.md) - Quant Validation Agent requirements for V5.2 Test-1.
- [Cyclical sector data gate](references/cyclical_sector_data_gate.md) - required PIT commodity price, supply-demand, spread and business-exposure layers before cyclical-sector formal promotion.
- [Insurance universe definition](references/insurance_universe_definition.md) - V5.3 insurance operating-company universe boundary.
- [Insurance data field map](references/insurance_data_field_map.md) - PIT fields for valuation, EV/NBV, solvency, underwriting, investment and external rate/equity states.
- [Insurance source collection plan](references/insurance_source_collection_plan.md) - source order and PIT guardrails for V5.3 insurance.
- [Insurance validation handoff](references/insurance_validation_handoff.md) - Quant Validation Agent task requirements for V5.3 Test-1.
- [Insurance EV / NBV PIT repair plan](references/insurance_ev_nbv_pit_repair_plan.md) - required source, date and coverage gates before P/EV can enter formal validation.
- [Fxbaogao report source](references/fxbaogao_report_source.md) - VIP report-search source for Research Agent knowledge collection; not direct PIT factor evidence.
- [V5.7 external report collection plan](references/v57_external_report_collection_plan.md) - MECE report-learning tasks for gas/water, telecom, transport infrastructure and cross-industry FCF knowledge.
- [V5.7 Fxbaogao source register](references/v57_fxbaogao_source_register.md) - first-pass report source register and paragraph-screening outputs for V5.7 sector coverage.
- [V5.7 external source collection execution](../../docs/governance/v57_external_source_collection_execution_v1.md) - PM execution record for FxBaogao report collection and source-role handoff.
- [Gas / water V5.7 external state source register](references/gas_water_v57_external_state_source_register.csv) - gas procurement, pass-through, water-tariff, receivables and financing-risk report sources; research-only until PIT state fields are built.

## Factor Theory

- [Bank stock value investing framework](factor_theory/bank_value_investing_framework.md) - citation-backed, requires Quant Validation before use in strategy acceptance.
- [Bank stock core factor hypothesis list](factor_theory/bank_core_factor_hypotheses.md) - citation-backed hypotheses, not accepted factors.
- [Bank stock value trap identification](factor_theory/bank_value_trap_identification.md) - citation-backed guard hypotheses, not accepted filters.
- [Bank defensive and macro state variables](factor_theory/bank_defensive_macro_state_variables.md) - citation-backed risk-control candidates, not alpha evidence.
- [Utilities value investing preparation note](factor_theory/utilities_value_investing_preparation_note.md) - initial V5.1 utilities economic logic, not validated factors.
- [Utilities value investing framework](factor_theory/utilities_value_investing_framework.md) - V5.1 formal research-preparation framework.
- [Utilities core factor hypotheses](factor_theory/utilities_core_factor_hypotheses.md) - candidate hypotheses for PIT validation, not accepted factors.
- [Coal value investing framework](factor_theory/coal_value_investing_framework.md) - V5.2 cycle-aware high-dividend / value framework.
- [Coal core factor hypotheses](factor_theory/coal_core_factor_hypotheses.md) - candidate coal factors and external state hypotheses, not accepted factors.
- [Insurance value / quality framework](factor_theory/insurance_value_quality_framework.md) - V5.3 insurance economic logic, not validated factors.
- [Insurance core factor hypotheses](factor_theory/insurance_core_factor_hypotheses.md) - candidate insurance factors for PIT validation, not accepted factors.
- [Insurance V5.3e research hypothesis redesign](factor_theory/insurance_v53e_research_hypothesis_redesign.md) - post-V5.3d reset: solvency as guard, investment return as state diagnostic, EV/NBV as data-repair-dependent hypothesis.
- [Insurance P/EV, EV and NBV research framework](factor_theory/insurance_pev_ev_nbv_research_framework.md) - fxbaogao-backed insurance valuation framework; P/EV remains blocked until multi-year PIT EV/NBV coverage passes.
- [Cross-industry FCF / capex quality gate](factor_theory/cross_industry_fcf_capex_quality_gate_v1.md) - OCF remains the basket mainline; FCF can enter only after sector-specific capex-quality and PIT gates pass.
- [Gas / water operator cash-flow dividend framework](factor_theory/gas_water_operator_cashflow_dividend_framework_v57.md) - V5.7 preferred next sector; OCF first, FCF conditional, receivables/debt/operator-purity gates required.
- [Telecom operator observation framework](factor_theory/telecom_operator_cashflow_dividend_observation_framework_v57.md) - small-sample observation sleeve; capex-cycle-aware FCF and basket-level validation required.
- [Transport infrastructure cash-flow dividend refresh](factor_theory/transport_infrastructure_cashflow_dividend_refresh_v57.md) - report-backed refresh supporting V5.4/V5.5 transport infrastructure workflow.

## Strategy Cases

- [Bank Value 15Y defensive overlay](strategy_cases/bank_value_15y_defensive_overlay.md)
- [Utilities V5.1 Test-1 initial result](strategy_cases/utilities_v51_test1_initial_result.md) - process portability passed, current composite rejected for formal-candidate promotion.
- [Utilities V5.1b cashflow value result](strategy_cases/utilities_v51b_cashflow_value_result.md) - sub-industry cash-flow value improved clarity but still failed candidate promotion.
- [Utilities V5.1c low PB cashflow result](strategy_cases/utilities_v51c_low_pb_cashflow_result.md) - both factors work individually, static two-factor composite failed.
- [Utilities V5.1d conditional result](strategy_cases/utilities_v51d_conditional_result.md) - conditional rules improved over composite but failed to beat raw baselines.
- [Utilities V5.1 series retrospective](strategy_cases/utilities_v51_series_retrospective.md) - research reset required before further utilities strategy-candidate attempts.
- [Utilities external state panel V1](strategy_cases/utilities_external_state_panel_v1.md) - initial PIT demand-state panel populated and validated.
- [Utilities V5.1e demand-state preliminary model](strategy_cases/utilities_v51e_demand_state_preliminary_model.md) - external demand state supports an initial cash-flow / low-PB switching model, not yet a formal strategy.
- [Utilities V5.1f formal candidate](strategy_cases/utilities_v51f_quant_ready_candidate.md) - weak/mid/strong demand-state rule passed Quant, engineering contract audit, and smoke test; platform replication is still blocked.
- [Coal V5.2 quant validation result](strategy_cases/coal_v52_quant_validation_result.md) - first coal process-portability validation; cash-flow value evidence stronger than high dividend, formal candidacy blocked by state-data gaps.
- [Coal V5.2b cash-flow cycle value result](strategy_cases/coal_v52b_cashflow_cycle_value_result.md) - revised coal model improved evidence, but formal candidacy remains blocked by data audits and 2018 failure.
- [Coal V5.2b data audit blocker repair](strategy_cases/coal_v52b_data_audit_blocker_repair.md) - source import template, business-tag PIT audit, FCF/capex audit, and PM decision to keep V5.2b in the data-audit loop.
- [Coal V5.2b formal data repair result](strategy_cases/coal_v52b_formal_data_repair_result.md) - official state seed, report disclosure dates, capex-policy branch, and PM decision to keep candidacy blocked.
- [Coal V5.2b final PM decision](strategy_cases/coal_v52b_final_pm_decision.md) - V5.2b archived as workflow replication passed but strategy candidate failed.
- [Coal V5.2b Eastmoney segment evidence](strategy_cases/coal_v52b_eastmoney_segment_evidence.md) - Eastmoney F10 segment runner covers 33/37 coal companies; formal tag gate remains blocked.
- [Coal V5.2b segment reviewed repair result](strategy_cases/coal_v52b_segment_reviewed_repair_result.md) - Tushare fallback repairs 37/37 segment coverage and rebuilds a formal PIT coal universe panel.
- [Coal V5.2b final inputs audit result](strategy_cases/coal_v52b_final_inputs_audit_result.md) - daily returns and rebalance signals repaired; external raw-coal output / inventory state remains blocked, so V5.2b is not promoted.
- [Coal V5.2b PM closeout and V5.3 selection](strategy_cases/coal_v52b_pm_closeout_and_v53_selection.md) - coal paused as data-completion watchlist; insurance selected as V5.3 research-preparation track.
- [Insurance V5.3 research preparation execution](strategy_cases/insurance_v53_research_preparation_execution.md) - first universe and data-field probe completed; Quant validation blocked until universe review, 2024-2025 indicator coverage repair, EV/NBV source decision, and state panel build.
- [Insurance V5.3 Test-1 quant validation result](strategy_cases/insurance_v53_test1_quant_validation_result.md) - Test-1 ran PIT validation; low PB and dividend were useful, generic ROE/profit-growth composite was rejected, V5.3b recommended.
- [Insurance V5.3b low-PB dividend result](strategy_cases/insurance_v53b_low_pb_dividend_result.md) - real 10Y rate state added; low PB remains dominant, low-PB + dividend composite rejected, V5.3c low-PB-only review recommended.
- [Insurance V5.3c low-PB-only result](strategy_cases/insurance_v53c_low_pb_only_result.md) - low PB-only passed research PIT validation and is approved for Engineering preparation, with 2021/2026 and concentration risk still unresolved.
- [Insurance V5.3c local daily simulation result](strategy_cases/insurance_v53c_local_daily_simulation_result.md) - Engineering smoke test completed with real JoinQuant daily prices, 20% tax-adjusted cash dividends, and 399809.XSHE insurance-theme benchmark; 2026 failure needs PM review.
- [Insurance V5.3d composite rejection and research reset](strategy_cases/insurance_v53d_composite_rejection_and_research_reset.md) - PIT audit passed, but low-PB + investment-return + solvency composite failed; returns to Research Agent for hypothesis redesign.
- [Insurance V5.3e solvency guard and state diagnostic result](strategy_cases/insurance_v53e_solvency_guard_state_diagnostic_result.md) - solvency guard failed to improve low PB; state diagnostics are explanatory but not enough for timing.
- [Insurance V5.3 research-quant loop closeout](strategy_cases/insurance_v53_research_quant_loop_closeout.md) - insurance has a low-PB research signal but is blocked from deployment until multi-year PIT EV/NBV/P/EV data is repaired.
- [Insurance V5.3f P/EV and NBV data repair diagnostic](strategy_cases/insurance_v53f_pev_nbv_data_repair_diagnostic.md) - fxbaogao knowledge and 2024-2025 EV/NBV partial repair completed; P/EV diagnostic is blocked by insufficient PIT history.
- [V5.6c OCF value + volatility guard basket research reset](strategy_cases/v56c_ocf_value_vol_guard_basket_research_reset.md) - low PB / FCF basket narrative rejected; OCF primary signal with volatility guard becomes current basket research mainline.
- [V5.7 sector coverage screening result](strategy_cases/v57_sector_coverage_screening_result.md) - first batch coverage map for dividend low-vol OCF basket with sector-approved FCF enhancement.
- [Gas / water V5.7b initial model result](strategy_cases/gas_water_v57b_initial_model_result.md) - Research-Quant loop rejected OCF mainline and found a preliminary regulated-asset value + serviceability model.
- [Gas / water V5.7b business-purity and financial-evidence repair](strategy_cases/gas_water_v57b_business_purity_financial_repair_result.md) - operator-purity and direct receivables/debt fields repaired; V5.7b remains a repaired research-signal candidate, not an Engineering handoff.
- [Gas / water V5.7b coverage policy freeze](../../docs/governance/v57b_gas_water_coverage_policy_freeze_v1.md) - conservative 80% coverage rule frozen; 70% startup coverage remains diagnostic only because it was observed before rule freeze.

## Open Research Questions

- When should a strategy use adjusted total-return series versus raw price plus explicit cash dividends?
- How large is the residual gap between local and JoinQuant after using real execution prices across more strategies?
- Which factor families are robust to execution-price and dividend-treatment changes?
- Which bank-sector variables remain significant under rolling IC/RankIC, baseline, ablation and robustness validation?
- Which macro/defensive variables reduce drawdown out of sample without becoming hidden sector-timing overfit?
- Can V5.1 utilities factors remain financially explainable and statistically stable without bank-specific indicators?
- Can V5.2 coal value factors survive PIT validation after controlling for commodity-cycle state?
- Can V5.3 insurance value / quality factors transfer V5 financial-sector logic beyond banks without becoming bank-factor reuse?
- Which sectors can upgrade FCF from diagnostic support to formal factor after capex-quality and PIT visibility gates?

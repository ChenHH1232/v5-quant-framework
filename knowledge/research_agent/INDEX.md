# Research Agent Knowledge Index

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

## Open Research Questions

- When should a strategy use adjusted total-return series versus raw price plus explicit cash dividends?
- How large is the residual gap between local and JoinQuant after using real execution prices across more strategies?
- Which factor families are robust to execution-price and dividend-treatment changes?
- Which bank-sector variables remain significant under rolling IC/RankIC, baseline, ablation and robustness validation?
- Which macro/defensive variables reduce drawdown out of sample without becoming hidden sector-timing overfit?
- Can V5.1 utilities factors remain financially explainable and statistically stable without bank-specific indicators?
- Can V5.2 coal value factors survive PIT validation after controlling for commodity-cycle state?
- Can V5.3 insurance value / quality factors transfer V5 financial-sector logic beyond banks without becoming bank-factor reuse?

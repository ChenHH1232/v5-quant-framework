# Research Agent Knowledge Index

## Market Structure

- [JoinQuant execution matching requires real-price data](market_structure/joinquant_execution_price_alignment.md)

## Data Sources

- [Bank sector research references](references/bank_sector_references.md)
- [Bank knowledge collection source register](references/source_register_bank_sector.md) - first-pass official/regulatory and academic source register completed; market/industry protected sources marked for manual review.
- [Utilities source collection plan](references/utilities_source_collection_plan.md) - V5.1 preparation source order and source-risk guardrails.
- [Bank regulatory definitions](references/bank_regulatory_definitions.md) - first-pass official definition layer completed.
- [Bank academic theory sources](references/bank_academic_theory_sources.md) - first-pass theory source layer completed.
- [Bank disclosure field map](references/bank_disclosure_field_map.md) - pending collection.
- [Bank industry research sources](references/bank_industry_research_sources.md) - pending collection.
- [Bank market-view hypotheses](references/bank_market_view_hypotheses.md) - market views only, pending collection.
- [Bank factor validation handoff](references/bank_factor_validation_handoff.md) - pending handoff to Quant Validation Agent.
- [Utilities universe definition](references/utilities_universe_definition.md) - V5.1 operating-company universe boundary.
- [Utilities data field map](references/utilities_data_field_map.md) - required PIT fields and source risks.
- [Utilities validation handoff](references/utilities_validation_handoff.md) - Quant Validation Agent task requirements for Test-1.

## Factor Theory

- [Bank stock value investing framework](factor_theory/bank_value_investing_framework.md) - citation-backed, requires Quant Validation before use in strategy acceptance.
- [Bank stock core factor hypothesis list](factor_theory/bank_core_factor_hypotheses.md) - citation-backed hypotheses, not accepted factors.
- [Bank stock value trap identification](factor_theory/bank_value_trap_identification.md) - citation-backed guard hypotheses, not accepted filters.
- [Bank defensive and macro state variables](factor_theory/bank_defensive_macro_state_variables.md) - citation-backed risk-control candidates, not alpha evidence.
- [Utilities value investing preparation note](factor_theory/utilities_value_investing_preparation_note.md) - initial V5.1 utilities economic logic, not validated factors.
- [Utilities value investing framework](factor_theory/utilities_value_investing_framework.md) - V5.1 formal research-preparation framework.
- [Utilities core factor hypotheses](factor_theory/utilities_core_factor_hypotheses.md) - candidate hypotheses for PIT validation, not accepted factors.

## Strategy Cases

- [Bank Value 15Y defensive overlay](strategy_cases/bank_value_15y_defensive_overlay.md)
- [Utilities V5.1 Test-1 initial result](strategy_cases/utilities_v51_test1_initial_result.md) - process portability passed, current composite rejected for formal-candidate promotion.

## Open Research Questions

- When should a strategy use adjusted total-return series versus raw price plus explicit cash dividends?
- How large is the residual gap between local and JoinQuant after using real execution prices across more strategies?
- Which factor families are robust to execution-price and dividend-treatment changes?
- Which bank-sector variables remain significant under rolling IC/RankIC, baseline, ablation and robustness validation?
- Which macro/defensive variables reduce drawdown out of sample without becoming hidden sector-timing overfit?
- Can V5.1 utilities factors remain financially explainable and statistically stable without bank-specific indicators?

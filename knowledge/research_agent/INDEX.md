# Research Agent Knowledge Index

## Market Structure

- [JoinQuant execution matching requires real-price data](market_structure/joinquant_execution_price_alignment.md)

## Data Sources

- [Bank sector research references](references/bank_sector_references.md)
- [Bank knowledge collection source register](references/source_register_bank_sector.md) - first-pass official/regulatory and academic source register completed; market/industry protected sources marked for manual review.
- [Bank regulatory definitions](references/bank_regulatory_definitions.md) - first-pass official definition layer completed.
- [Bank academic theory sources](references/bank_academic_theory_sources.md) - first-pass theory source layer completed.
- [Bank disclosure field map](references/bank_disclosure_field_map.md) - pending collection.
- [Bank industry research sources](references/bank_industry_research_sources.md) - pending collection.
- [Bank market-view hypotheses](references/bank_market_view_hypotheses.md) - market views only, pending collection.
- [Bank factor validation handoff](references/bank_factor_validation_handoff.md) - pending handoff to Quant Validation Agent.

## Factor Theory

- [Bank stock value investing framework](factor_theory/bank_value_investing_framework.md) - citation-backed, requires Quant Validation before use in strategy acceptance.
- [Bank stock core factor hypothesis list](factor_theory/bank_core_factor_hypotheses.md) - citation-backed hypotheses, not accepted factors.
- [Bank stock value trap identification](factor_theory/bank_value_trap_identification.md) - citation-backed guard hypotheses, not accepted filters.
- [Bank defensive and macro state variables](factor_theory/bank_defensive_macro_state_variables.md) - citation-backed risk-control candidates, not alpha evidence.

## Strategy Cases

- [Bank Value 15Y defensive overlay](strategy_cases/bank_value_15y_defensive_overlay.md)

## Open Research Questions

- When should a strategy use adjusted total-return series versus raw price plus explicit cash dividends?
- How large is the residual gap between local and JoinQuant after using real execution prices across more strategies?
- Which factor families are robust to execution-price and dividend-treatment changes?
- Which bank-sector variables remain significant under rolling IC/RankIC, baseline, ablation and robustness validation?
- Which macro/defensive variables reduce drawdown out of sample without becoming hidden sector-timing overfit?

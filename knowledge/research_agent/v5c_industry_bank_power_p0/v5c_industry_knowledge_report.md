# V5c Industry Knowledge Base P0: Bank + Power

## Decision

Bank and power industry knowledge is admitted to V5c as an observation layer only.

## Scope

- Industries: bank, utilities_electricity.
- Sources: local V5 bank/power reports, V5c P2/P3/P4 packets, WeRead paraphrased book cards, and report leads.
- Output knowledge base: `knowledge\research_agent\v5c_industry_bank_power_p0`.

## Findings

- Bank: regulatory definitions and V5 bank process evidence are available, but dedicated bank industry book cards and expanded NIM/asset-quality/capital PIT panels are still needed.
- Power: electricity demand state is PIT-usable through the V51 external state panel, but coal price, tariff/capacity payment, hydro water condition and power-type utilization remain open gaps.
- Books: useful for governance and industry-analysis framing, but cannot set thresholds or trigger trades.
- Reports/articles: useful as source leads after review; raw titles or snippets cannot become evidence.

## Boundary

No V5f/V57f weight changes, no trade triggers, no accepted/live approval.

## PM Gate

`admit_bank_power_industry_knowledge_to_v5c_observation_layer_only`

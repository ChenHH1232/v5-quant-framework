# V5.8 Research Queue Execution Checkpoint V1

Date: 2026-07-19

Owner:

```text
Project Manager Agent, Research Agent
```

Status:

```text
research_queue_started
gas_water_stage_gate_reached
airport_transport_research_prepared
not_new_formal_modeling
```

## PM Summary

V5.8 broad replication continues under the agent operating protocol. This checkpoint does not promote any sector to accepted strategy or platform replication.

## 1. Gas / Water Operators

Current state:

```text
research_signal_candidate_repaired
local_joinquant_style_simulation_ready
coverage_policy_stage_gate_pending
not_formal_strategy_candidate
```

What is already repaired:

- PIT business-purity panel exists.
- Direct receivables / collection / interest-bearing debt evidence exists.
- Real JoinQuant daily prices, cash dividends and same-pool benchmark exist.
- Local daily simulation and overfit audit exist.
- External-state report leads exist.

Why it cannot silently proceed:

```text
The 80% versus 70% startup coverage policy materially changes whether the 2021-07-01 rebalance trades.
That is a PM stage-gate decision, not an Engineering or Quant parameter tweak.
```

Default PM handling:

```text
Do not tune.
Do not write JoinQuant script.
Keep gas / water as pending coverage-policy freeze.
Continue the broader Research queue instead of blocking V5.8.
```

Relevant evidence:

- `docs/governance/v57b_gas_water_business_purity_financial_repair_pm_decision_v1.md`
- `docs/governance/v57b_gas_water_local_jq_simulation_readiness_v1.md`
- `docs/engineering/v57b_gas_water_local_simulation_handoff_v1.md`
- `validation_formal_v57_gas_water_v57b_direct_financial/gas_water_value_serviceability_v57b/`
- `local_daily_backtests_v57_gas_water/gas_water_value_serviceability_v57b/`

## 2. Airport / Transport Operators

Current state:

```text
manual_research_before_formal
industry_knowledge_gate_prepared
initial_pit_panel_collected
not_quant_validation_ready
```

Newly added knowledge artifacts:

- `knowledge/research_agent/references/transport_operator_source_collection_plan.md`
- `knowledge/research_agent/factor_theory/transport_operator_cashflow_framework.md`

Initial PIT panel:

```text
数据库/processed/similar_sector_pit_panel_v58/airport_transport_operators/panel.csv
数据库/processed/similar_sector_pit_panel_v58/airport_transport_operators/collection_manifest.json
```

Initial panel result:

| Check | Result |
| --- | ---: |
| Row count | 100 |
| Rebalance dates | 20 |
| Code count | 5 |
| Collection warnings | 0 |

Initial operator codes:

```text
600009.XSHG 上海机场
600004.XSHG 白云机场
000089.XSHE 深圳机场
600897.XSHG 厦门空港
600515.XSHG 海南机场
```

Research boundary:

```text
Focus on transport operators that are not already covered by highway V5.4h or port / rail V5.5j.
Airlines, shipping, express delivery, logistics trade and equipment manufacturers are excluded by default.
```

MECE questions:

| Question | Required answer before Quant |
| --- | --- |
| Business purity | Which listed names are true transport operators, not logistics / trade / airline cycle names? |
| Cash-flow stability | Does OCF remain stable through weak demand years? |
| External state | Which state variable explains weak periods: passenger, cargo, freight, toll revenue or policy? |
| Dividend support | Is dividend supported by OCF and payout discipline? |
| FCF/capex quality | Is FCF sustainable, or inflated by delayed maintenance / expansion timing? |

Existing report leads:

- [5313068 - 交通运输行业事项点评：HALO资产优等生，重新定价稀缺性：港口、铁路投资机遇解析](https://www.fxbaogao.com/view?id=5313068)
- [5403030 - 华创交运红利资产2025年报及2026年一季报综述：公路稳健，港口景气向上+提分红，铁路、大宗边际改善趋势强](https://www.fxbaogao.com/view?id=5403030)
- [5322100 - 快递涨价区域蔓延，避险推荐高速公路](https://www.fxbaogao.com/view?id=5322100)
- [5510356 - 基础设施行业2026年中期策略报告：关注市场风格转变，红利资产配置价值持续提升](https://www.fxbaogao.com/view?id=5510356)
- [5193718 - 交通基础设施公募REITs发行现状及堵点分析](https://www.fxbaogao.com/view?id=5193718)

Next Research outputs:

```text
transport_operator_universe_candidate.csv
transport_operator_business_purity_evidence.csv
transport_operator_external_state_field_map.md
transport_operator_cashflow_hypothesis.md
```

### 2026-07-19 Business Purity Gate Update

Actions completed in this PM timebox:

- Added airport / transport operating evidence runner.
- Collected Tushare report disclosure dates for the 5-code airport operator panel.
- Collected Eastmoney F10 segment evidence as first-layer structured evidence.
- Rebuilt the airport PIT business-purity panel.
- Fixed the classifier to recognize airport-specific segment terms such as aviation revenue, aviation main business, aviation services and concession / rental revenue.
- Fixed the gate label so visible but failed evidence is marked as business contamination, not missing evidence.

Business-purity gate result:

| Check | Result |
| --- | ---: |
| Source PIT rows | 100 |
| Passed PIT rows | 80 |
| Removed PIT rows | 20 |
| Passed code count | 4 |
| Rebalance coverage | 80% on every 2021-2026 rebalance |

Passed first-layer airport operator names:

```text
600009.XSHG Shanghai Airport
600004.XSHG Baiyun Airport
000089.XSHE Shenzhen Airport
600897.XSHG Xiamen Airport
```

Removed:

```text
600515.XSHG Hainan Airport
reason=failed_non_airport_contamination
evidence=Eastmoney segment rows show airport operator revenue share below 50% on all 2021-2026 rebalance dates, with real estate / property / commercial and duty-free exposure material.
```

Artifacts:

- `数据库/processed/airport_transport_operating_evidence_v58/airport_report_disclosure_dates.csv`
- `数据库/processed/airport_transport_operating_evidence_v58/airport_segment_business_evidence_eastmoney.csv`
- `数据库/processed/airport_transport_operating_evidence_v58/business_purity_panel/panel_business_purity_passed.csv`
- `数据库/processed/airport_transport_operating_evidence_v58/business_purity_panel/removed_by_business_purity_gate.csv`
- `数据库/processed/airport_transport_operating_evidence_v58/business_purity_panel/business_purity_coverage_by_rebalance.csv`

PM interpretation:

```text
Airport / transport passed the first-layer PIT business-purity data gate, but it is not Quant-ready yet.
Eastmoney segment evidence remains first-layer evidence and still needs annual/interim report spot checks before Engineering handoff.
External operating-state fields are not joined yet, so formal validation must not start.
```

### 2026-07-19 External State Field Map Update

Research Agent prepared the airport operator external-state field map.

New artifacts:

- `knowledge/research_agent/references/airport_transport_external_state_field_map_v58.md`
- `knowledge/research_agent/references/airport_transport_operating_state_manual_template.csv`
- `knowledge/research_agent/references/airport_transport_annual_report_spot_check_template.csv`

Defined required state dimensions:

```text
passenger throughput / YoY
cargo throughput / YoY
aircraft movements / YoY
international passenger recovery
commercial rent / concession / duty-free exposure
capex-to-OCF pressure
airport fee / policy state
```

PM rule:

```text
These fields are allowed as Research hypotheses and future PIT inputs only after visible_date is recorded.
They are not allowed as scoring factors from report narratives.
Airport formal validation remains blocked until company-level operating state or a documented annual proxy is populated.
```

### 2026-07-19 Company-Level Operating Announcement Index Update

Research Agent added and ran a company-level operating announcement index collector.

New runner / test artifacts:

- `src/v5/airport_transport_operating_evidence_runner.py`
- `tests/test_airport_transport_operating_evidence_runner.py`
- CLI command: `collect-eastmoney-airport-operating-announcements`

Data artifact:

- `数据库/processed/airport_transport_operating_evidence_v58/eastmoney_airport_operating_announcement_index.csv`
- `数据库/processed/airport_transport_operating_evidence_v58/eastmoney_airport_operating_announcement_index_manifest.json`

Result:

| Check | Result |
| --- | ---: |
| matched operating announcement rows | 261 |
| matched company count | 4 |
| warnings | 0 |
| per-company month coverage | 65 months each |
| covered report months | 2020-12 to 2026-04 |

Covered companies:

```text
600009.XSHG Shanghai Airport
600004.XSHG Baiyun Airport
000089.XSHE Shenzhen Airport
600897.XSHG Xiamen Airport
```

Important repair:

```text
000089.XSHE Shenzhen Airport was not missing data. Its announcement title uses "生产经营快报", not only "生产经营数据" or "运输生产情况简报".
The collector now includes this wording and also tolerates one observed Baiyun Airport title typo.
```

PM interpretation:

```text
Airport / transport now has a credible company-level monthly operating announcement index with visible_date.
This is enough to start PDF/value extraction planning.
It is still not enough for Quant validation because passenger/cargo/aircraft movement values have not been extracted and reviewed.
```

### 2026-07-19 Operating Value Extraction Probe

Research Agent added an operating-state value candidate extractor.

New capability:

```text
CLI command: extract-airport-operating-state-values
input: eastmoney_airport_operating_announcement_index.csv
output: airport_operating_state_value_candidates.csv
```

The extractor uses the public Eastmoney announcement content endpoint to read announcement text and candidate-extract:

```text
passenger_throughput
passenger_throughput_yoy
cargo_throughput
cargo_throughput_yoy
aircraft_movements
aircraft_movements_yoy
pdf_url
```

Sample result:

| Check | Result |
| --- | ---: |
| sample rows | 4 |
| complete candidates | 4 |
| warnings | 0 |

Sample artifact:

- `数据库/processed/airport_transport_operating_evidence_v58/operating_state_values_sample4/airport_operating_state_value_candidates.csv`
- `数据库/processed/airport_transport_operating_evidence_v58/operating_state_values_sample4/airport_operating_state_value_extraction_manifest.json`

Important PM finding:

```text
The parser works on representative Shenzhen Airport operating briefings, but full-batch extraction through the Eastmoney content endpoint is not stable enough yet.
261-row full extraction and 20/40-row probes exceeded command time limits.
This is an Engineering reliability issue, not a Research hypothesis failure.
```

PM decision:

```text
Do not hand airport / transport to Quant yet.
Return this part to Engineering Agent for resumable extraction:
- cache each fetched announcement content row immediately;
- support start-after / code / month filters;
- isolate slow rows with per-row timeout status;
- reuse cached content before calling Eastmoney again;
- only then rerun full value extraction and Research spot-check.
```

### 2026-07-19 Resumable Content Cache Update

Engineering Agent added the resumable airport operating announcement content cache.

New capability:

```text
CLI command: cache-airport-operating-announcement-contents
input: eastmoney_airport_operating_announcement_index.csv
output: one cached JSON per art_code plus manifest and error CSV
```

Key behavior:

- skips already cached announcements by default;
- supports code, start_month, end_month, limit and retry_failed filters;
- writes each successful announcement immediately;
- writes failed rows to a separate error CSV;
- lets value extraction run in cache-only mode so missing rows do not trigger slow live calls.

Probe result:

| Check | Result |
| --- | ---: |
| selected rows | 8 |
| first cache success | 7 |
| isolated retry success | 1 |
| final cache-only extraction rows | 8 |
| complete candidates | 8 |
| extraction warnings | 0 |

Formal-cache first batch:

| Check | Result |
| --- | ---: |
| selected rows | 20 |
| cached rows | 20 |
| cache errors | 0 |
| cache-only extraction rows | 20 |
| complete candidates | 20 |
| extraction warnings | 0 |

Scope note:

```text
The first formal-cache batch covers the earliest 20 Shenzhen Airport monthly operating briefings.
It proves the resumable path works on real data, but it does not yet prove cross-company or full-period coverage.
```

Artifacts:

- `数据库/processed/airport_transport_operating_evidence_v58/operating_content_cache_probe8/airport_operating_content_cache_manifest.json`
- `数据库/processed/airport_transport_operating_evidence_v58/operating_state_values_cache_probe8_retry/airport_operating_state_value_candidates.csv`
- `数据库/processed/airport_transport_operating_evidence_v58/operating_state_values_cache_probe8_retry/airport_operating_state_value_extraction_manifest.json`
- `数据库/processed/airport_transport_operating_evidence_v58/operating_content_cache/airport_operating_content_cache_manifest.json`
- `数据库/processed/airport_transport_operating_evidence_v58/operating_state_values_cache20/airport_operating_state_value_candidates.csv`
- `数据库/processed/airport_transport_operating_evidence_v58/operating_state_values_cache20/airport_operating_state_value_extraction_manifest.json`

PM interpretation:

```text
The blocker has narrowed from parser/endpoint reliability to full-cache completion plus original-announcement spot-check.
This is a data availability gate improvement, not a Quant validation pass.
Airport / transport remains not_quant_ready until full 261-row content cache, full value extraction and sampled original PDF/content review are completed.
```

### 2026-07-19 Full Cache And Candidate Panel Update

Engineering Agent continued the same data-availability loop and completed the full Eastmoney operating announcement content cache.

Full-cache result:

| Check | Result |
| --- | ---: |
| announcement index rows | 261 |
| cached content rows | 261 |
| missing content rows | 0 |
| value candidate rows | 261 |
| complete candidates | 261 |
| extraction warnings | 0 |
| normalized candidate rows | 261 |
| normalization warnings | 0 |

Coverage by company:

| Code | Cached rows | Candidate rows |
| --- | ---: | ---: |
| 000089.XSHE | 65 | 65 |
| 600004.XSHG | 66 | 66 |
| 600009.XSHG | 65 | 65 |
| 600897.XSHG | 65 | 65 |

New artifacts:

- `数据库/processed/airport_transport_operating_evidence_v58/operating_content_cache/airport_operating_content_cache_coverage_summary.json`
- `数据库/processed/airport_transport_operating_evidence_v58/operating_state_values_cache_full/airport_operating_state_value_candidates.csv`
- `数据库/processed/airport_transport_operating_evidence_v58/operating_state_values_cache_full/airport_operating_state_value_extraction_manifest.json`
- `数据库/processed/airport_transport_operating_evidence_v58/operating_state_values_cache_full/airport_operating_state_value_candidates_normalized.csv`
- `数据库/processed/airport_transport_operating_evidence_v58/operating_state_values_cache_full/airport_operating_state_value_normalization_manifest.json`
- `数据库/processed/airport_transport_operating_evidence_v58/operating_state_values_cache_full/airport_operating_state_spot_check_sample.csv`

Research handoff note:

```text
All extracted operating values remain pit_usable=false.
Research Agent must spot-check original announcement/PDF rows and normalize units before Quant validation.
Observed unit issue: different companies and periods report passenger/cargo/aircraft metrics in different units such as people/person-times versus ten-thousand person-times, kg versus tonnes/ten-thousand tonnes, and aircraft movements in raw movements versus ten-thousand movements.
```

Engineering follow-up:

```text
Unit normalization was completed as a candidate layer:
passenger_throughput_10k_person_times
cargo_throughput_ton
aircraft_movements_count

The normalized rows still remain pit_usable=false until Research Agent completes original announcement/PDF spot checks.
```

### 2026-07-19 Cached Notice Text Spot-Check Update

Research Agent reviewed the 12-row airport operating-state spot-check sample against cached Eastmoney public announcement text.

Result:

| Check | Result |
| --- | ---: |
| Spot-check rows | 12 |
| Cached public notice text matches | 12 |
| Cached text failures | 0 |
| Original PDF checks completed | 0 |

Artifact:

- `数据库/processed/airport_transport_operating_evidence_v58/operating_state_values_cache_full/spot_check_review/airport_operating_state_cached_notice_spot_check_review.csv`
- `数据库/processed/airport_transport_operating_evidence_v58/operating_state_values_cache_full/spot_check_review/airport_operating_state_cached_notice_spot_check_review_summary.json`
- `docs/governance/v58_airport_transport_operating_state_spot_check_pm_decision_v1.md`

PDF blocker:

```text
Automated Eastmoney PDF downloads returned EO_Bot script files instead of valid PDF content in this environment.
This does not invalidate the cached notice text, but it prevents the Research Agent from marking original_pdf_checked=true.
```

PM decision:

```text
Airport operating-state candidates pass cached notice text review.
Eastmoney PDF download remained blocked by EO_Bot script files, but Research Agent completed CNINFO original PDF spot-check for the same 12 rows.
The field is now cleared for Quant research PIT validation, with sample-review limitations.
```

### 2026-07-19 CNINFO Original PDF Spot-Check Update

Research Agent matched the 12-row airport operating-state sample to CNINFO / exchange-style original announcement PDFs.

Result:

| Check | Result |
| --- | ---: |
| Sample rows | 12 |
| CNINFO original PDFs downloaded | 12 |
| PDF text extraction succeeded | 12 |
| Candidate values matched PDF text | 12 |
| Failed original PDF checks | 0 |

New artifacts:

- `数据库/processed/airport_transport_operating_evidence_v58/operating_state_values_cache_full/spot_check_review/airport_operating_state_cninfo_pdf_spot_check_review.csv`
- `数据库/processed/airport_transport_operating_evidence_v58/operating_state_values_cache_full/spot_check_review/airport_operating_state_cninfo_pdf_spot_check_review_summary.json`
- `数据库/processed/airport_transport_operating_evidence_v58/operating_state_values_cache_full/airport_operating_state_value_pit_reviewed_panel.csv`
- `数据库/processed/airport_transport_operating_evidence_v58/operating_state_values_cache_full/airport_operating_state_value_pit_reviewed_panel_manifest.json`

PM decision:

```text
The airport operating-state panel is now allowed for Quant research PIT validation.
This is not a full 261-row original PDF review and is not enough for platform replication, paper trading or accepted strategy status.
```

### 2026-07-19 Formal Validation Update

Quant Validation Agent ran the first airport / transport research PIT validation.

Strategy:

```text
airport_transport_cashflow_operating_state_v58
```

Artifacts:

- `examples/airport_transport_cashflow_operating_state_v58_strategy.json`
- `数据库/processed/airport_transport_formal_panel_v58/panel.csv`
- `validation_formal_v58_airport_transport/airport_transport_cashflow_operating_state_v58/formal_validation_summary.json`
- `validation_formal_v58_airport_transport/airport_transport_cashflow_operating_state_v58/formal_validation_report.md`
- `docs/governance/v58_airport_transport_formal_validation_pm_decision_v1.md`

Key evidence:

| Check | Result |
| --- | ---: |
| PIT panel rows | 80 |
| Rebalance dates | 20 |
| Operating-state coverage | 100% |
| PIT leakage audit | pass |
| Composite cumulative return | -4.99% |
| Equal-weight pool cumulative return | -17.80% |
| High-dividend top3 cumulative return | -7.35% |
| Operating-state top3 cumulative return | -21.10% |
| Operating-state mean IC | -0.1264 |

PM decision:

```text
Airport / transport data workflow replication passed.
The first cash-flow + operating-state strategy hypothesis is not promoted.
Do not hand to Engineering.
Return to Research Agent.
```

Reason:

```text
The composite improves relative to simple airport baselines but remains negative in absolute return and unstable in rolling validation.
The reviewed operating-state score is useful as an explanatory state candidate, but it is not validated as a positive alpha factor.
```

### 2026-07-19 V5.8b Research Reset And Final Airport Decision

Research Agent redesigned the rejected V5.8 hypothesis.

New research view:

```text
Airport operating YoY recovery should not be treated as a linear positive alpha factor.
For a dividend low-volatility cash-flow basket, airport operating variables should first be tested as stability / risk-state variables.
```

New artifacts:

- `knowledge/research_agent/factor_theory/airport_transport_franchise_state_framework_v58b.md`
- `examples/airport_transport_franchise_state_v58b_strategy.json`
- `数据库/processed/airport_transport_formal_panel_v58b/panel.csv`
- `validation_formal_v58b_airport_transport/airport_transport_franchise_state_v58b/formal_validation_summary.json`
- `docs/governance/v58b_airport_transport_franchise_state_pm_decision_v1.md`

V5.8b evidence:

| Check | Result |
| --- | ---: |
| Franchise state-risk composite | -5.18% |
| High-dividend top3 | -7.35% |
| Low state-instability top3 | -13.92% |
| Low commercial-exposure top3 | -5.82% |
| Operating-state instability mean IC | 0.0561 |
| Commercial-exposure risk mean IC | 0.0997 |

PM final decision for airport / transport:

```text
workflow_replication_passed
strategy_candidate_failed
blocked_until_new_domain_data
not_engineering_handoff
```

Restart only if Research Agent can add:

```text
international passenger recovery versus 2019
duty-free / commercial lease contract terms
rent concession / minimum annual guarantee changes
airport fee / policy changes
capex project cycle and capacity expansion evidence
annual-report business-purity spot-check
```

## PM Decision

Continue V5.8 by moving Research Agent from gas / water to airport / transport operators.

Do not hand gas / water to formal platform replication until the coverage-policy gate is explicitly frozen.

Do not hand airport / transport to Quant until industry knowledge and PIT data gates pass.

Airport / transport still lacks:

```text
annual-report business-purity review
company-level operating-state visible-date panel
passenger throughput / cargo throughput value extraction from operating briefings
international-route recovery state
duty-free / rental / commercial revenue exposure
airport capex-quality and policy-state review
```

Historical performance alone is never sufficient evidence for accepting a strategy.

## 2026-07-19 Telecom Small-Sample Sleeve PM Update

Project Manager Agent reviewed the existing V5.5a telecom validation packet under the V5.8 sector replication workflow.

New governance artifacts:

- `docs/governance/v58_telecom_small_sample_sleeve_policy_v1.md`
- `docs/governance/v58_telecom_observation_sleeve_pm_decision_v1.md`

Telecom evidence reviewed:

| Check | Result |
| --- | ---: |
| Core A-share operators | 3 |
| Equal-weight core telecom return | 25.24% |
| High-dividend top2 return | 26.07% |
| Composite top2 return | 48.93% |
| Rolling 2026 | -17.73% |
| Dividend yield mean IC | 0.3513 |
| Composite mean selected count | 1.5 |

PM decision:

```text
small_sample_observation_sleeve_approved_for_basket_diagnostic_not_standalone_strategy
```

Interpretation:

```text
Telecom operators have a credible dividend / cash-flow business fit, but the three-name A-share universe makes normal cross-sectional factor validation invalid.
The signal may be used for capped basket-level contribution diagnostics or paper observation, but it is not a standalone formal strategy candidate.
```

Blocked actions:

```text
Do not hand telecom to Engineering Agent.
Do not write JoinQuant code.
Do not promote telecom to formal_strategy_candidate.
Do not use broad IC / RankIC acceptance standards.
```

Allowed next work:

```text
Basket-level contribution test, paper-observation signal log, specialist telecom operating data repair, leave-one-name-out concentration diagnostic.
```

### Telecom Basket Data Gate Follow-Up

PM checked whether telecom can immediately enter basket-level contribution testing.

Current data gate:

```text
blocked_by_missing_local_basket_inputs
```

Available:

```text
数据库/processed/similar_sector_pit_panel_v55/telecom_operators/panel.csv
```

Missing:

```text
数据库/processed/telecom_joinquant_real_daily_prices.csv
数据库/processed/telecom_joinquant_cash_dividends.csv
数据库/processed/low_volatility_factors_v57/telecom_operators/panel_with_low_vol.csv
```

New artifact:

- `docs/governance/v58_telecom_basket_contribution_data_gate_v1.md`

PM decision:

```text
Do not add telecom to the V5.7f main basket yet.
Engineering Agent may repair data inputs only; no strategy implementation or return tuning.
```

### Telecom Engineering Data Repair Update

Engineering Agent repaired the local basket diagnostic inputs.

New data:

| Input | Path / Result |
| --- | --- |
| Real daily prices | `数据库/processed/telecom_joinquant_joinquant_real_daily_prices.csv` |
| Benchmark prices | `数据库/processed/telecom_joinquant_joinquant_real_benchmark_prices.csv` |
| Cash dividends | `数据库/processed/telecom_joinquant_joinquant_cash_dividends.csv` |
| Low-vol PIT panel | `数据库/processed/low_volatility_factors_v58/telecom_operators/telecom_operators_cashflow_dividend_v55a/panel_with_low_vol.csv` |

Coverage:

| Check | Result |
| --- | ---: |
| Daily price rows | 3,684 |
| Cash dividend rows | 26 |
| Low-vol panel rows | 52 |
| Low-vol enriched rows | 51 |

Updated PM gate:

```text
data_inputs_repaired_basket_contribution_diagnostic_ready
```

Next allowed action:

```text
Run a capped telecom observation-sleeve contribution diagnostic outside the frozen V5.7f main basket.
```

### Telecom Overlay Basket Contribution Diagnostic

PM ran a capped telecom observation-sleeve overlay outside the V5.7f frozen main basket.

New artifacts:

- `config/dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay.json`
- `validation_formal_v58_telecom_overlay_basket_constructor/basket_construction_summary.json`
- `local_daily_backtests_v58_telecom_overlay_matched/dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay/dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay/summary.json`
- `validation_formal_v58_telecom_overlay_matched_basket/dividend_low_vol_sector_neutral_equal_sleeve_etf_v58_telecom_overlay/basket_formal_validation_summary.json`
- `docs/governance/v58_telecom_overlay_basket_contribution_pm_decision_v1.md`

Matched comparison:

| Metric | V5.7f main basket | V5.8 telecom overlay |
| --- | ---: | ---: |
| Strategy return | 81.42% | 80.12% |
| Annualized return | 14.27% | 14.09% |
| Excess return | 30.40% | 28.67% |
| Max drawdown | 11.75% | 11.11% |
| Sharpe | 0.932 | 0.950 |
| Information ratio | 0.444 | 0.400 |
| Volatility | 15.64% | 15.08% |

PM decision:

```text
telecom_overlay_diagnostic_completed_observation_only_not_v57f_replacement
```

Interpretation:

```text
Telecom slightly improves volatility and drawdown, but it does not improve return, excess return or information ratio.
Keep V5.7f as the current main ETF candidate. Telecom remains an observation sleeve only.
```

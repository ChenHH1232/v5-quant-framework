# V5.5 Similar-Sector Replication Framework

Date: 2026-07-18

Owner:

```text
Project Manager Agent
```

Status:

```text
active_pre_v55_framework
must_pass_before_new_sector_test
```

## Purpose

V5.5 must not start by immediately opening another sector.

Before V5.5, V5 needs a repeatable similar-sector replication framework. The goal is to turn the experience from bank, utilities, coal, insurance, and transportation / highway into hard gates.

This framework answers:

```text
When can a new sector enter V5 research?
When must it be blocked?
When can it move from Research to Quant?
When can it move from Quant to Engineering?
When can it become a platform-replicated formal candidate?
```

## Lessons From Previous Sectors

| Sector line | Result | Lesson |
| --- | --- | --- |
| Bank | Main line, PIT + platform replication + paper trading | Financial logic, PIT data, and platform attribution can produce a formal candidate. |
| Utilities / electricity | Golden template | Sector knowledge and external state variables materially improved the research process. |
| Coal | Workflow replication passed, strategy candidate failed | Cyclical sectors require commodity price, output, inventory, spread, and PIT business exposure before modeling. |
| Insurance | Research signal exists, but needs EV/NBV/P/EV and subgroup logic | Similar surface valuation factors are not enough when industry-specific value metrics dominate. |
| Transportation / highway | Replication succeeded, platform replication passed | Stable cash-flow sectors with clear operating evidence are good candidates for V5 replication. |

Core PM conclusion:

```text
V5 can replicate across sectors, but only when sector knowledge and PIT data gates are passed first.
```

## Global Rule

Every new sector must pass six gates in order:

```text
Industry Knowledge Gate
        |
Data Availability Gate
        |
Hypothesis Design Gate
        |
Formal Validation Gate
        |
Engineering Replication Gate
        |
PM Decision Gate
```

No Agent may skip a gate.

No strategy can be accepted because historical return is high.

## Gate 1: Industry Knowledge Gate

Owner:

```text
Research Agent
```

Mission:

Research Agent must learn the sector before proposing a quantitative hypothesis.

Required outputs:

| Artifact | Required path pattern | Purpose |
| --- | --- | --- |
| Sector value investing framework | `knowledge/research_agent/factor_theory/{sector}_value_investing_framework.md` | Explain how the sector creates value. |
| Core factor hypothesis list | `knowledge/research_agent/factor_theory/{sector}_core_factor_hypotheses.md` | Define candidate factor logic and expected direction. |
| Value trap / failure modes | `knowledge/research_agent/factor_theory/{sector}_value_trap_framework.md` | Explain when cheap stocks are not attractive. |
| Universe definition | `knowledge/research_agent/references/{sector}_universe_definition.md` | Define inclusion / exclusion boundaries. |
| Source collection plan | `knowledge/research_agent/references/{sector}_source_collection_plan.md` | List official, filings, vendor, report, paper, and manual sources. |
| Data field map | `knowledge/research_agent/references/{sector}_data_field_map.md` | Map theory to fields, source, visible date, and missing risk. |
| Quant handoff | `knowledge/research_agent/references/{sector}_validation_handoff.md` | Tell Quant Agent what to test and what would falsify the hypothesis. |

Source priority:

1. Official definitions, exchange filings, regulator publications, and index methodology.
2. Annual reports, interim reports, prospectuses, and company announcements.
3. Academic papers, textbooks, and industry methodology documents.
4. Brokerage research and industry reports, with publication date and source recorded.
5. Investor articles and community analysis only as hypothesis inspiration, not verified data.

PM pass conditions:

- The sector business model is clear.
- Profit drivers are clear.
- Key risk variables are clear.
- Core financial statement metrics are identified.
- Candidate factors have financial explanation.
- At least one falsification condition is defined.
- Source citations are recorded.

Allowed statuses:

```text
sector_knowledge_gate_passed
sector_knowledge_gate_needs_more_sources
sector_knowledge_gate_blocked
```

Only `sector_knowledge_gate_passed` can move to the next gate.

## Gate 2: Data Availability Gate

Owner:

```text
Project Manager Agent
```

Mission:

Before Quant Agent runs validation, PM must confirm that the sector has enough PIT data to avoid data illusion.

Required checks:

| Data requirement | Required? | Notes |
| --- | --- | --- |
| PIT stock universe | yes | Must avoid today's business structure contaminating history. |
| Listing / delisting / transformation handling | yes | Delisted, shell, transformed, or mixed-business firms must be handled. |
| Announcement date / visible date | yes | Financial and operating fields must be visible before trade date. |
| Basic valuation fields | yes | PB, PE, dividend yield, cash-flow yield, or sector-specific equivalents. |
| Dividend data | yes for dividend strategy | Must define cash dividend and tax / fee treatment. |
| Daily open / close prices | yes for local simulation | Must match JoinQuant-like real price where possible. |
| Sector benchmark | yes | Prefer pure sector index / ETF; otherwise build equal-weight same-pool benchmark. |
| Sector-specific operating fields | case dependent | Required if the research hypothesis depends on them. |
| External state variables | case dependent | Required for cyclical or macro-sensitive sectors. |

Hard blockers:

- No PIT universe.
- No visible date for key fields.
- Sector classification exists only as current snapshot.
- Key industry-specific metric is unavailable but required by the hypothesis.
- External cycle state is missing for cyclical sectors.
- Source requires forced crawling against website restrictions.

Allowed statuses:

```text
data_gate_passed
data_gate_needs_manual_research
data_gate_blocked
```

Only `data_gate_passed` can move into formal research validation.

## Gate 3: Hypothesis Design Gate

Owner:

```text
Research Agent
```

Mission:

Research Agent converts industry knowledge into testable hypotheses.

Each hypothesis must include:

| Field | Required |
| --- | --- |
| hypothesis_id | yes |
| economic mechanism | yes |
| target universe | yes |
| factor list | yes |
| expected factor direction | yes |
| expected regime behavior | yes |
| value trap condition | yes |
| required data fields | yes |
| PIT visibility requirement | yes |
| falsification condition | yes |
| source citations | yes |

Research Agent must not:

- choose factors because cumulative return is high;
- tune selection count or weights after seeing validation results;
- use community articles as verified data;
- send unvalidated ideas directly to Engineering Agent.

Allowed statuses:

```text
hypothesis_ready_for_quant_validation
hypothesis_needs_more_research
hypothesis_blocked_by_data
```

## Gate 4: Formal Validation Gate

Owner:

```text
Quant Validation Agent
```

Mission:

Quant Agent tests the Research Agent's hypothesis using PIT statistical evidence.

Required tests:

| Test | Required |
| --- | --- |
| PIT leakage audit | yes |
| Sample coverage audit | yes |
| Baseline comparison | yes |
| IC / RankIC | yes |
| Rolling validation | yes |
| Ablation | yes |
| Robustness | yes |
| Weak-year / failure-mode analysis | yes |
| Data quality sensitivity | case dependent |
| State bucket validation | required for cyclical / macro-sensitive sectors |

Quant Agent must not:

- invent financial theory after seeing results;
- tune factor weights to make results pass;
- promote a weak hypothesis because cumulative return is high;
- move directly to Engineering after a failed validation.

Validation result statuses:

```text
hypothesis_supported_for_pm_review
hypothesis_needs_research_revision
hypothesis_rejected
data_gate_failed_return_to_pm
```

If validation fails:

```text
Quant Agent -> Research Agent
```

The return packet must explain:

- which claim failed;
- which tests failed;
- whether the issue is data, theory, sample, or regime;
- which years / regimes failed;
- what research questions should be revisited.

## Gate 5: Engineering Replication Gate

Owner:

```text
Engineering Agent
```

Mission:

Engineering Agent implements only frozen, PM-approved candidates.

Required work:

| Work item | Required |
| --- | --- |
| Freeze strategy spec | yes |
| Local daily simulation | yes |
| Daily open / close execution model | yes |
| Cash dividend handling | yes |
| 100-share lot handling | yes |
| Commission / minimum commission | yes |
| Paused / limit-up / limit-down handling | yes |
| Benchmark series | yes |
| Daily NAV / cash / holdings / trades / dividends logs | yes |
| JoinQuant frozen script | yes if platform replication is requested |
| Platform attribution packet | yes before platform_replication_passed |

Engineering Agent must not:

- change research conclusions;
- tune parameters for higher return;
- add defensive overlays unless PM marks them as separate risk-control candidates;
- silently change benchmark, universe, or factor logic.

Replication result statuses:

```text
engineering_smoke_test_passed
engineering_smoke_test_needs_review
platform_replication_ready
platform_replication_passed
contract_mismatch
data_gap
pending_attribution
```

## Gate 6: PM Decision Gate

Owner:

```text
Project Manager Agent
```

Mission:

PM owns final status labels and prevents experiment-layer mixing.

Allowed strategy statuses:

```text
blocked
research_signal_only
workflow_replication_passed_strategy_candidate_failed
formal_strategy_candidate
engineering_smoke_test_passed
platform_replication_passed
paper_trading
accepted_strategy
```

Important distinctions:

| Status | Meaning |
| --- | --- |
| `blocked` | Cannot continue without missing data / source / structural repair. |
| `research_signal_only` | Some evidence exists, but not enough for Engineering. |
| `formal_strategy_candidate` | Research and Quant evidence support PM review. |
| `platform_replication_passed` | Local and JoinQuant platform behavior are attributed and close enough. |
| `paper_trading` | Frozen strategy is now being observed on future signals. |
| `accepted_strategy` | Only possible after sufficient future evidence and PM approval. |

Forbidden status upgrades:

- `platform_replication_passed` -> `accepted_strategy` based only on 2021-2026 returns.
- `hypothesis_rejected` -> `engineering_smoke_test` without Research revision.
- `data_gate_blocked` -> `formal_validation` without data repair.
- `research_signal_only` -> `JoinQuant code ready` without formal validation.

## Sector Type Rules

### Stable Cash-Flow / Dividend Sectors

Examples:

```text
utilities
highway
telecom operators
water / gas operators
ports / rail infrastructure
```

Minimum required data:

- PIT universe;
- dividend history;
- valuation;
- cash-flow and debt metrics;
- operating purity;
- daily real price;
- sector / same-pool benchmark.

Preferred first hypothesis:

```text
dividend sustainability + operating purity + cash-flow coverage
```

### Financial Sectors

Examples:

```text
bank
insurance
securities
```

Additional required data:

- sector-specific value metric;
- regulatory capital / solvency / asset quality where applicable;
- interest-rate or market-state variables if economically required;
- clear subgroup boundary.

Insurance lesson:

```text
PB alone is not enough. EV/NBV/P/EV or subgroup-specific logic is needed before acceptance.
```

### Cyclical Sectors

Examples:

```text
coal
steel
nonferrous metals
chemical
oil and gas
```

Additional required data:

- commodity price state;
- production / inventory / demand state;
- spread or margin proxy;
- PIT business exposure;
- capacity cycle / capex cycle;
- state bucket validation.

Coal lesson:

```text
Do not formally model cyclical sectors before the cycle-state data gate passes.
```

## V5.5 Pre-Launch Checklist

Before opening V5.5, PM must complete:

| Checklist | Status |
| --- | --- |
| Similar-sector replication framework exists | done |
| Existing sector lessons summarized | done |
| Industry knowledge gate linked | done |
| Data availability gate linked | done |
| Research-Quant loop linked | done |
| Engineering replication gate defined | done |
| PM status labels unified | done |
| Candidate sector must pass data gate before validation | required |

## Suggested V5.5 Candidate Ordering

This framework does not open V5.5 yet, but it defines the next screening order.

Preferred candidates:

| Rank | Candidate | Reason | Main risk |
| ---: | --- | --- | --- |
| 1 | Telecom operators | High dividend, stable cash flow, close to dividend-cash-flow framework | Small A-share sample size |
| 2 | Gas / water operators | Similar to utilities, relatively stable demand | Regulatory pricing and regional differences |
| 3 | Ports / rail infrastructure | Infrastructure cash-flow logic | Business mix and cycle exposure |
| 4 | Oil and gas high dividend | Strong dividend potential | Commodity cycle data gate required |

PM recommendation:

```text
V5.5 should start only after the chosen candidate passes Industry Knowledge Gate and Data Availability Gate.
```

## Relationship To Existing Governance Files

This framework coordinates, but does not replace:

```text
docs/governance/sector_research_knowledge_gate_v1.md
docs/governance/sector_data_availability_gate_template.md
docs/governance/research_quant_iteration_protocol_v1.md
docs/governance/status_registry.json
```

## Final Rule

V5's objective is not to make every sector produce a strategy.

V5's objective is to reliably distinguish:

- explainable signal;
- data-source illusion;
- weak but interesting hypothesis;
- failed hypothesis;
- engineering replication issue;
- platform mismatch;
- formal candidate ready for future observation.

This framework is the default rulebook for V5.5 and later similar-sector replication tests.


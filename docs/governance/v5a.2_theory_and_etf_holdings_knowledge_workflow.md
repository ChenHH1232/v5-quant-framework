# V5a.2 Theory And ETF Holdings Knowledge Workflow

Status: completed initial knowledge pass  
Owner: Project Manager Agent -> Research Agent -> Quant Validation Agent  
Date: 2026-07-21  
Layer: research_knowledge_base, not strategy_validation

## Research Boundary

V5a.2 answers one upstream question before broad sector traversal:

Which economic theories, factor families and real ETF/index construction practices should guide the dividend low-volatility and operating/free-cash-flow enhanced ETF roadmap?

This packet does not validate a strategy. It sets the research prior, source hierarchy and validation contract for later V5a industry traversal.

## MECE Question And Search Matrix

| Step | Agent | Question | Evidence Type | Search / Source Keywords | Output | Gate |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | PM | What is the scope and what is out of scope? | Existing V5 governance docs | V5a.1 broad sector screening, V5 naming policy, Research-Quant protocol | This workflow | Must use V5a.x naming, not V60+ |
| 2 | Research | Why should value investing work or fail? | Academic papers, index rules, practitioner reports | value factor, book-to-market, cash-flow yield, quality, value trap | Theory framework | Must separate valuation signal from distress trap |
| 3 | Research | When does momentum complement value? | Academic papers and ETF/index methodology | cross-sectional momentum, time-series momentum, trend, value momentum correlation | Theory framework | Momentum is state/support factor, not default alpha until PIT validation |
| 4 | Research | When does mean reversion work or become a trap? | Academic papers, failure-year review | overreaction, reversal, long-term loser reversal, dividend trap | Theory framework | Must specify horizon and risk gate |
| 5 | Research | What do dividend low-vol / FCF ETFs and indices actually select? | Official ETF pages, fact sheets, index methodology, holdings pages | COWZ, VFLO, SCHD, SPHD, CSI dividend low-volatility, CNI free cash flow | ETF lessons memo + source register | Holdings snapshots must be refreshed; methodology is stronger evidence than one-day holdings |
| 6 | Research | Which sectors should V5 prioritize or block? | V5a.1 screening plus ETF sector priors | utilities, transport, telecom, gas/water, consumer staples, pharma, energy, financials | Hypothesis routing rules | Sector must pass knowledge and data availability gates before validation |
| 7 | Quant | How should these theories be tested? | PIT validation standards | IC, RankIC, rolling, ablation, baseline, robustness, failure year | Quant handoff rules | No acceptance by historical return alone |
| 8 | PM | How is this fed back to batch traversal? | Status registry, PM decision | V5a.2 references and PM decision | PM routing memo | Only changes priorities, not strategy status |

## Source Hierarchy

| Rank | Source Type | Role In V5a.2 | Can Directly Support Formal Factor? |
| --- | --- | --- | --- |
| 1 | Peer-reviewed academic papers / official index methodologies | Theory and implementation rules | Yes, as theory or construction evidence, not return proof |
| 2 | ETF issuer official pages, fact sheets and holdings files | Real-world construction priors and sector exposure checks | Yes for "copy homework" priors; holdings require refresh date |
| 3 | Exchange / index company factsheets | A-share local rule and industry exposure reference | Yes for construction priors |
| 4 | Research reports | Industry knowledge and hypothesis generation | No, unless PDF/source data is checked and translated into PIT fields |
| 5 | Xueqiu / WeChat Reading / social articles | Market narrative and investor-behavior hypotheses | No; manual review only |

## Execution Result

V5a.2 completed the initial knowledge pass:

- Built a factor-theory framework for value, momentum and mean reversion.
- Built an ETF/index "copy homework" lesson packet for dividend low-volatility and free-cash-flow construction.
- Registered academic, ETF/index and research-report sources.
- Updated Research Agent index and PM status registry.
- Routed the next broad traversal toward OCF + low-volatility as the default core, with FCF as sector-gated enhancement and low PB as a subordinate valuation support rather than the global mainline.

## PM Operating Rule

For all later V5a industry traversal, Research Agent must first produce an industry knowledge packet and data availability gate. Quant Agent may only start validation when the sector has:

- PIT universe.
- PIT financial data visibility.
- Dividend and price data.
- Sector-specific operating state if the industry requires it.
- A stated theory family: value, cash-flow quality, low-volatility, momentum support, mean-reversion support, or state-dependent guard.


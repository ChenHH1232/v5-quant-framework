# V5a.3 Theory-Gated Preliminary Sector Validation Workflow

Status: in execution  
Date: 2026-07-21  
Layer: research_pit_prevalidation  
Scope: broad dividend low-volatility, operating-cash-flow and sector-approved free-cash-flow enhanced ETF roadmap.

## Purpose

V5a.3 runs before broad formal validation. It applies the V5a.2 knowledge base to every required sector so that V5 can screen the entire dividend low-volatility / free-cash-flow opportunity set without manually getting stuck in one industry at a time.

This is not strategy acceptance, not platform replication and not live-trading approval.

## Full Workflow Table

| Stage | Agent | Objective | Inputs | Execution | Output | Stop / Gate |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | PM | Load broad sector universe | V5a.1 sector config, status registry | Copy candidate sectors into V5a.3 config | Candidate sector list | If source config missing, stop |
| 2 | PM | Apply theory gate | V5a.2 theory and ETF/index lessons | Classify value, OCF, FCF, low-vol, momentum and mean-reversion roles | Theory-gated sector CSV | No sector can skip this gate |
| 3 | Research | Industry knowledge gate | Sector knowledge cards, report/source registers, ETF lessons | Check business model, dividend support, FCF comparability, value-trap risk | Research-ready / repair / blocked | Missing knowledge returns to Research, not Quant |
| 4 | Research | Data availability gate | PIT universe, financial visibility, dividends, daily prices, business purity | Decide whether fields can be PIT-safe | Data gate decision | Hard data gate blocks modeling |
| 5 | Quant | Initial validation only for ready sectors | PIT-safe panel and hypothesis | Baseline, IC, RankIC, rolling, ablation, robustness, failure-year analysis | Initial validation packet | No tuning by historical return |
| 6 | Quant | Support factor testing | Momentum and mean-reversion hypotheses | Horizon grid, turnover audit, value-trap guard ablation | Support-factor packet | Momentum/reversion cannot become primary without evidence |
| 7 | Engineering | Frozen-candidate local simulation only | Quant-approved frozen candidate | Daily open/close, real dividends, cash, trades, holdings, rebalance_order_health | Engineering smoke packet | No factor changes by Engineering |
| 8 | PM | Route all sectors | All packets | Mark shadow pool / research repair / blocked / observation / engineering | PM decision | Strategy acceptance remains separate |

## Theory Rules

| Theory | V5a.3 Rule |
| --- | --- |
| Value investing | Cheapness must be tied to durable fundamentals; low PB is support, not global mainline. |
| OCF / cash-flow quality | Default cross-sector core because it is more comparable than raw FCF. |
| FCF | Enhancement only after capex-quality and sector comparability pass. |
| Dividend | Required sustainability gate; raw high dividend can be a trap. |
| Low volatility | Core defensive construction layer and required basket stabilizer. |
| Momentum | Support/state only; must pass horizon and turnover audit. |
| Mean reversion | Support only with ex-ante value-trap guard. |
| Cyclical state | Commodity/cycle sectors need price, output/inventory, spread and PIT exposure state before validation. |

## Execution Command

```powershell
$env:PYTHONPATH='D:\hh\codex\v5\src'
python -m v5.cli theory-gated-sector-prevalidation --config config/v5a.3_theory_gated_sector_prevalidation.json --out sector_replication_batches_v5a3/theory_gated_prevalidation_current
```

## PM Rule

Batch traversal is allowed. Strategy acceptance is not. The output is a queueing and prevalidation artifact that tells Research, Quant and Engineering where to work next.


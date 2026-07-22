# V5 Enhanced ETF Production Line Workflow

Date: 2026-07-21

Owner: Project Manager Agent

## Objective

Turn the dividend low-volatility, operating-cash-flow and sector-approved free-cash-flow roadmap into a repeatable production line.

The production line must answer four questions automatically:

1. Which sleeves are active in frozen V57f?
2. Which sleeves can be refreshed but must remain observation-only?
3. Which sectors must return to Research / Quant before Engineering?
4. Which local Engineering checks must pass before paper monitoring or platform attribution?

This workflow does not tune V57f and does not promote any strategy.

## Flow Table

| Stage | Owner | Input | Action | Output | Stop / Gate |
| --- | --- | --- | --- | --- | --- |
| 1. Load sector master table | PM Agent | `docs/governance/v5a_broad_sector_coverage_master_table.csv` | Read all V5a sector routing decisions | Full sector route list | Stop if table missing |
| 2. Load frozen V57f config | PM Agent | `config/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f.json` | Identify active sleeves and required files | Active sleeve list | Stop if active sleeve count changes unexpectedly |
| 3. Build sleeve registry | PM Agent | Master table + frozen config | Classify `core_frozen_refresh`, `observation_refresh_only`, `research_repair_queue`, `data_gate_blocked`, `archived_or_rejected`, `excluded_from_current_mandate` | `sleeve_registry.csv` | Observation sleeves cannot enter core |
| 4. Check active data files | Engineering Agent | Active panel / price / dividend paths | Check PIT panel, real daily price and dividend file presence | Data-file gate columns | Block local refresh if any active file missing |
| 5. Build refresh plan | PM Agent | Existing V57f artifacts | Create ordered runner plan from signal refresh to action route | `refresh_plan.csv` | Plan must not include JoinQuant live testing |
| 6. Verify local evidence | Engineering Agent | Daily summary and `rebalance_order_health` | Confirm every rebalance signal created orders and holdings | Order-health status | Block if no-order / no-position / blocked order exists |
| 7. Verify Quant evidence | Quant Agent | Formal validation, ablation, attribution | Confirm formal packet exists and weak-year diagnosis is not used for tuning | Validation status | Not accepted-strategy evidence |
| 8. Verify overfit / leakage gate | Engineering Agent | Overfit audit summary | Confirm blocker count is zero | Overfit gate | Block if blocker count > 0 |
| 9. PM Gate | PM Agent | Formal + daily + overfit + ablation + paper gate | Combine status and blocked actions | PM gate / dashboard / action route | No platform-replication-passed without exports |
| 10. Engineering handoff | PM Agent | Production-line summary | Hand only allowed local-refresh tasks to Engineering | Engineering boundary | Engineering cannot change frozen logic |
| 11. Future paper window | PM Agent / Engineering Agent | Next clean rebalance date | Queue future data refresh and signal generation | Paper refresh queue | No late signal can be treated as clean forward evidence |

## Production Lanes

| Lane | Meaning | Allowed owner | Can enter V57f now? |
| --- | --- | --- | --- |
| `core_frozen_refresh` | Already inside frozen V57f | Engineering Agent | Already included, refresh only |
| `observation_refresh_only` | Worth tracking but not part of frozen core | PM / Engineering for observation logs | No |
| `research_repair_queue` | Signal or domain promise exists, but data / hypothesis gate is not ready | Research / Quant | No |
| `data_gate_blocked` | Hard PIT, source, cycle-state or specialist data problem | Research Agent | No |
| `archived_or_rejected` | Previous attempt failed or not worth current effort | PM Agent | No |
| `excluded_from_current_mandate` | Outside dividend low-volatility OCF/FCF mandate | PM Agent | No |

## Current Execution Result

The first production-line run completed successfully:

- active V57f sleeves: `bank`, `highway_infrastructure`, `port_rail_infrastructure`, `utilities_electricity`;
- observation sleeves: `gas_water_operators`, `insurance`;
- engineering-ready: yes;
- local refresh evidence exists;
- `rebalance_order_health` passed;
- platform replication remains pending because JoinQuant exports are not supplied.

## Runner

```text
python -m v5.cli build-enhanced-etf-production-line \
  --master-table docs/governance/v5a_broad_sector_coverage_master_table.csv \
  --basket-config config/dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f.json \
  --status-registry docs/governance/status_registry.json \
  --out enhanced_etf_production_lines_v5/current \
  --next-clean-rebalance-date 2026-10-08
```

## Outputs

| Artifact | Purpose |
| --- | --- |
| `enhanced_etf_production_lines_v5/current/sleeve_registry.csv` | Machine-readable sleeve routing table |
| `enhanced_etf_production_lines_v5/current/sleeve_registry_summary.json` | Lane and Engineering gate counts |
| `enhanced_etf_production_lines_v5/current/refresh_plan.csv` | Ordered refresh / validation / PM gate plan |
| `enhanced_etf_production_lines_v5/current/production_line_summary.json` | Machine-readable PM decision packet |
| `enhanced_etf_production_lines_v5/current/production_line_report.md` | Human-readable report |

## Hard Rules

- V57f remains frozen.
- Do not add observation sleeves into V57f without a separate PM stage gate.
- Do not tune returns, factor weights, target count, sector caps or execution rules.
- Do not mark platform replication passed without JoinQuant daily, transaction, position and log attribution.
- Historical performance alone is never sufficient evidence for accepting a strategy.


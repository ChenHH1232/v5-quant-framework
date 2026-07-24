# Sleeve Promotion Policy V1

Purpose: define when an observation sleeve can become a V57f core candidate.

## Rules

| Rule | Category | Condition | Failure effect |
| --- | --- | --- | --- |
| `P1` | governance | No sleeve/factor/weight/timing change | `block_core_promotion` |
| `P2` | evidence | summary_path exists and dividend/order outputs are reviewed | `remain_observation_or_repair` |
| `P3` | execution | order_health_status == passed | `block_paper_and_core` |
| `P4` | forward | paper_tracking_status == paper_artifact_exists and future window is not retroactive | `remain_observation` |
| `P5` | risk | max_drawdown <= V57f max_drawdown * 1.10 | `remain_observation_or_repair` |
| `P6` | quality | information_ratio >= V57f IR * 0.90 | `remain_observation` |
| `P7` | sample | no small_sample/specialist class unless PM approves capped sleeve | `capped_observation_only` |
| `P8` | data | latest_stage not in research_or_data_repair, archived_or_failed | `block_core_promotion` |
| `P9` | mandate | required industry data gate is passed | `remain_observation_or_archive` |

## Hard Blocks

- Historical return alone cannot promote a sleeve.
- Small-sample sleeves cannot become ordinary core sleeves without a separate PM-approved capped policy.
- Order-health needs_review blocks paper tracking and core promotion.
- Archived/data-gate-failed sleeves cannot be reopened by high backtest return.
- This policy does not modify V57f or generate a 2026-10 paper runner.

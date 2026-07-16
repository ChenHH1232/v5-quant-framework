# Governance Record: v52_coal_data_probe_v1

Date: 2026-07-16

Project:

```text
V5.2 Coal High-Dividend / Cycle-Value Process-Portability Test
```

Current status:

```text
data_probe_completed_for_preparation
```

Not status:

```text
research_pit_validation_started
formal_strategy_candidate
platform_replication_candidate
accepted_strategy
```

## DataJQ / JoinQuant Industry Probe

Initial industry codes identified for coal-boundary construction:

| Source taxonomy | Code | Name | Use |
| --- | --- | --- | --- |
| JoinQuant L1 | `HY001` | energy | context only |
| JoinQuant L2 | `HY01107` | coal | candidate core universe |
| Shenwan L1 | `801950` | coal I | context only |
| Shenwan L2 | `801951` | coal mining II | candidate core universe |
| CSRC | `B06` | coal mining and washing | candidate core universe |
| CSRC exclusion | `C25` | petroleum, coal and other fuel processing | coal-chemical exclusion review |
| JoinQuant exclusion | `HY03129` | mining and metallurgy machinery | equipment exclusion review |

## Initial Candidate Universe Snapshot

The union of `HY01107`, `801951`, and `B06` on 2026-07-16 produced the following initial names for manual review:

| Code | Name | Initial tag |
| --- | --- | --- |
| `000552.XSHE` | 甘肃能化 | review_core_coal |
| `000571.XSHE` | 新大洲A | review_mixed_or_special |
| `000937.XSHE` | 冀中能源 | review_core_coal |
| `000983.XSHE` | 山西焦煤 | review_core_coal |
| `002128.XSHE` | 电投能源 | review_mixed_power_coal |
| `600121.XSHG` | 郑州煤电 | review_core_coal |
| `600123.XSHG` | 兰花科创 | review_core_coal |
| `600188.XSHG` | 兖矿能源 | review_core_coal |
| `600256.XSHG` | 广汇能源 | review_mixed_energy |
| `600348.XSHG` | 华阳股份 | review_core_coal |
| `600395.XSHG` | 盘江股份 | review_core_coal |
| `600403.XSHG` | 大有能源 | review_core_coal |
| `600508.XSHG` | 上海能源 | review_core_coal |
| `600546.XSHG` | 山煤国际 | review_core_coal |
| `600726.XSHG` | 华电能源 | review_mixed_power_coal |
| `600758.XSHG` | 辽宁能源 | review_mixed_power_coal |
| `600925.XSHG` | 苏能股份 | review_core_coal |
| `600971.XSHG` | 恒源煤电 | review_core_coal |
| `600985.XSHG` | 淮北矿业 | review_core_coal |
| `600997.XSHG` | 开滦股份 | review_mixed_coal_chemical |
| `601001.XSHG` | 晋控煤业 | review_core_coal |
| `601088.XSHG` | 中国神华 | review_integrated_coal_power_transport |
| `601101.XSHG` | 昊华能源 | review_core_coal |
| `601225.XSHG` | 陕西煤业 | review_core_coal |
| `601666.XSHG` | 平煤股份 | review_core_coal |
| `601699.XSHG` | 潞安环能 | review_core_coal |
| `601898.XSHG` | 中煤能源 | review_core_coal |
| `601918.XSHG` | 新集能源 | review_core_coal |

This is not an approved PIT universe. It is a 2026-07-16 probe snapshot that must be converted into a point-in-time universe with membership visibility rules.

## External State Candidate Sources

| Metric | Candidate source | URL | PIT status |
| --- | --- | --- | --- |
| raw coal output | National Bureau of Statistics | `https://data.stats.gov.cn/` | candidate; publication date required |
| production-material coal prices | National Bureau of Statistics releases | `https://www.stats.gov.cn/sj/zxfb/` | candidate; release-date audit required |
| thermal / coking coal prices | Ministry of Commerce business forecast | `https://cif.mofcom.gov.cn/` | candidate; series availability audit required |
| coal market index / inventory | CCTD China Coal Market | `https://www.cctd.com.cn/` | candidate; may require manual review or access |
| coal industry output / inventory | China National Coal Association | `https://www.coalchina.org.cn/` | candidate; publication-date audit required |
| coal-power spread proxy | China Electricity Council | `https://www.cec.org.cn/` | candidate; proxy definition required |
| price policy / coal inventory notes | National Development and Reform Commission | `https://www.ndrc.gov.cn/` | candidate; qualitative or numeric review required |
| thermal coal futures proxy | Zhengzhou Commodity Exchange | `http://www.czce.com.cn/` | proxy only; futures is not spot coal price |
| coking coal futures proxy | Dalian Commodity Exchange | `http://www.dce.com.cn/` | proxy only; futures is not spot coal price |

## PM Interpretation

The initial data probe supports starting V5.2 preparation, but does not yet support formal validation.

Blocking gaps before `research_pit_validation`:

- point-in-time coal universe membership;
- visible-date audit for external state;
- mixed-business classification using company reports;
- confirmation of benchmark choice;
- panel coverage check for dividend, cash flow, capex, leverage, and coal-state variables.

## Next Action

Research Agent should complete the preparation packet.

Engineering Agent may design source templates and panel contracts, but must not write strategy execution code before a formal research candidate is frozen.

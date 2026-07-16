# Coal Source Collection Plan

Date: 2026-07-16

Project:

```text
V5.2 Coal High-Dividend / Cycle-Value Process-Portability Test
```

Status:

```text
source_candidates_not_yet_pit_validated
```

## Collection Priority

1. Build PIT stock universe from JoinQuant / DataJQ industry membership and company disclosures.
2. Collect stock-level market, valuation, financial, and dividend fields from JoinQuant / DataJQ.
3. Collect external coal-cycle state from official or auditable sources.
4. Create a conservative visible-date table for every external state row.
5. Only then approve Quant Validation Agent formal tests.

## Candidate Sources

| Source | URL | Candidate metrics | Source type | PIT caution |
| --- | --- | --- | --- | --- |
| JoinQuant / DataJQ | `https://www.joinquant.com/` | stock price, valuation, finance, dividend, industry | vendor | verify field dates and membership history |
| National Bureau of Statistics data portal | `https://data.stats.gov.cn/` | raw coal output, industrial production | official | publication lag required |
| NBS statistical release page | `https://www.stats.gov.cn/sj/zxfb/` | production-material market prices, coal varieties if available | official | release date must become visible date |
| Ministry of Commerce business forecast | `https://cif.mofcom.gov.cn/` | commodity price monitoring, thermal coal / coking coal if available | official | series coverage and publication date audit required |
| CCTD China Coal Market | `https://www.cctd.com.cn/` | coal price index, port inventory, market commentary | industry association / market service | access and publication-date audit required |
| China National Coal Association | `https://www.coalchina.org.cn/` | industry output, operation reports, inventory notes | industry association | numeric data may require manual extraction |
| China Electricity Council | `https://www.cec.org.cn/` | electricity demand, generation, fuel cost context | industry association | coal-power spread may need derived proxy |
| NDRC | `https://www.ndrc.gov.cn/` | coal price policy, inventory, energy-price policy | official | often qualitative; numeric extraction must be reviewed |
| Zhengzhou Commodity Exchange | `http://www.czce.com.cn/` | thermal coal futures proxy | exchange market proxy | proxy only, not spot price |
| Dalian Commodity Exchange | `http://www.dce.com.cn/` | coking coal futures proxy | exchange market proxy | proxy only, not spot price |
| Company annual / interim reports | exchange disclosure sites and company IR | business segment revenue / profit, reserves, capex | company disclosure | report publication date required |

## Anti-Crawler / Access Notes

- Prefer official downloadable tables, APIs, or manually reviewed downloads over fragile scraping.
- Do not bypass login, paywall, robots policy, or access controls.
- If a website blocks automated access, record a manual collection task instead of forcing a scraper.
- For CCTD or other market-service sources, confirm licensing before systematic collection.
- For exchange data, prefer official CSV/download endpoints when available.

## External State Panel Template

Every external state row should use:

```text
visible_date,state_date,state_scope,metric,value,unit,source_name,source_url,source_publication_date,pit_usable,review_status,notes
```

Example metrics:

- `thermal_coal_price_yoy`;
- `thermal_coal_price_level`;
- `coking_coal_price_yoy`;
- `coking_coal_price_level`;
- `raw_coal_output_yoy`;
- `coal_inventory_days`;
- `port_coal_inventory`;
- `coal_power_spread_proxy`.

## Source Acceptance Rule

A data source is not accepted only because the value looks useful.

It becomes usable only after:

- the original source is recorded;
- the publication date is recorded;
- the visible date is conservative;
- the metric definition is stable;
- missing-data and revision behavior are documented.

# V5 Local Database

This folder is the local data handoff area for Bank Quant V5 agents.

It separates reusable local datasets from generated experiment reports:

- `raw/`: raw source pulls, such as AKShare dividend tables.
- `processed/`: normalized datasets consumed by V5 runners.
- `manifests/`: local data manifests, source notes, schemas, and warnings.

Agent ownership:

- Quant Validation Agent reads `processed/` datasets for statistical validation.
- Engineering Agent reads `processed/` datasets for panel construction, local backtests, and platform export checks.
- Project Manager Agent reads `manifests/` to decide whether a dataset is acceptable for formal use.

Current dividend contract:

- Canonical processed file: `processed/bank_cash_dividends.csv`
- Required return fields for panel construction: `code`, `ex_date`, `cash_per_share`
- Optional point-in-time field: `announce_date`
- If the price series is already pre-adjusted or total-return adjusted, do not blindly add `cash_per_share` again. Either confirm the raw price adjustment policy or use `--total-return-mode adjusted_total_return`.

Current benchmark contract:

- Canonical processed file: `processed/bank_benchmarks.csv`
- Default benchmark id: `bank_etf_512800_qfq`
- Tradable benchmark: `bank_etf_512800_qfq` from `512800` bank ETF front-adjusted prices.
- Index research benchmarks: `csi_bank_399986` and `csi_300_bank_000951`.
- Panel construction maps benchmark close levels from each `trade_date` to `next_trade_date` and writes `benchmark_return` plus `benchmark_source`.

Generated local data is intentionally git-ignored. Keep source manifests and generated CSVs local unless a specific research freeze requires archiving a small sample.

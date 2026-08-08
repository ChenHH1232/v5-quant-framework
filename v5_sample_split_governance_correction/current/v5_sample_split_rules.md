# V5 Sample Split Rules

- 2013-01-01 to 2021-04-30 is the train/test research window.
- 2021-05-01 to 2026-05-31 is the formal backtest window.
- Do not use 2021-2026 results for factor discovery, optimization, rolling validation, or independent validation.
- Recent `bank_special_mention_loan` result is backtest-scope positive only; it requires 2013-2021 PIT-clean replay before promotion.
- Keep `internal_subsleeve_mom12_70_30` as V5f primary until pre-2021 evidence supports a change.

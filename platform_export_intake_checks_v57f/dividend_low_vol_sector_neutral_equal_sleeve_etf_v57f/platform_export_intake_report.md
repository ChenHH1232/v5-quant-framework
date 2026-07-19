# Platform Export Intake Check: dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f

- Status: `platform_test_deferred_by_user_waiting_for_exports`
- User deferred: `True`
- Ready exports: `0`
- Missing exports: `4`
- Empty exports: `0`
- Allowed next action: `continue_local_paper_preflight_and_do_not_run_platform_attribution`

## Export Checks

| Export | Status | Size | Target |
| --- | --- | ---: | --- |
| daily_result | `missing` | 0 | `platform_exports_v57f\pending\result.csv` |
| transaction_detail | `missing` | 0 | `platform_exports_v57f\pending\transaction.csv` |
| position_detail | `missing` | 0 | `platform_exports_v57f\pending\position.csv` |
| full_log | `missing` | 0 | `platform_exports_v57f\pending\log.txt` |

## PM Rule

Platform replication may only proceed after all required exports are present and non-empty; summary return alone is not enough.
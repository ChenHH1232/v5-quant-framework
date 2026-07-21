# Overfit Audit Report: dividend_low_vol_sector_neutral_equal_sleeve_etf_v57g_gas_water_observation

- Status: `needs_review`
- Blockers: `0`
- Needs review: `1`

## Checks

- `survivorship_bias / spec_universe_point_in_time`: `pass` - Universe must be point-in-time rather than today's surviving constituents. Metrics: `{"point_in_time": true}`
- `survivorship_bias / panel_universe_visibility`: `pass` - Panel should expose universe/listing/membership visible dates and they must be <= trade_date. Metrics: `{"examples": "", "future_visible_date_violations": 0, "missing_ratio": 0.191, "rows": 4089, "rows_with_universe_visible_date": 3308}`
- `survivorship_bias / first_date_constituent_smell_test`: `pass` - If the first date already contains nearly all eventual securities, review for today's-universe backfill. Metrics: `{"all_code_count": 198, "date_count": 19, "first_date": "2021-10-08", "first_date_count": 165, "first_date_ratio": 0.833333}`
- `future_leakage / normalization_scope`: `pass` - Full-sample normalization is a future function. Metrics: `{"normalization_scope": "sector_adaptive"}`
- `future_leakage / factor_as_of_policy`: `pass` - Factor as_of policy must be announcement_date, report_publish_date, or trade_date_lagged. Metrics: `{"unsafe_factors": ""}`
- `future_leakage / panel_visible_dates`: `pass` - All panel visible/notice/announce dates must be <= trade_date. Metrics: `{"examples": "", "violations": 0, "visible_fields": "business_purity_visible_date;factor_visible_date;gas_water_financial_evidence_visible_date;gas_water_visible_date;highway_segment_visible_date;low_vol_factor_visible_date;reviewed_operating_visible_date;same_pool_trailing_120d_return_visible_date;same_pool_trailing_60d_drawdown_visible_date;same_pool_trailing_60d_return_visible_date;same_pool_trailing_60d_volatility_visible_date;sector_collection_cash_to_revenue_median_visible_date;sector_dividend_yield_median_visible_date;sector_interest_bearing_debt_to_assets_median_visible_date;sector_net_debt_to_assets_median_visible_date;sector_receivables_to_assets_median_visible_date;sector_receivables_to_revenue_median_visible_date;true_operating_visible_date;universe_visible_date"}`
- `future_leakage / rebalance_signal_visible_dates`: `pass` - State/timing rows in rebalance_signals must be visible no later than trade_date. Metrics: `{"examples": "", "violations": 0, "visible_fields": ""}`
- `sample_contamination / rolling_validation_required`: `pass` - Single-model validation should be rolling; platform-confirmation windows are not clean out-of-sample acceptance. Metrics: `{"validation_method": "rolling"}`
- `sample_contamination / accepted_status_guard`: `pass` - A strategy cannot be marked accepted based only on backtest/platform-confirmation evidence. Metrics: `{"meta_status": "research_pit_validation_not_accepted"}`
- `sample_contamination / platform_window_usage`: `needs_review` - The 2021-05 to 2026-05 window is platform confirmation / replication context, not clean OOS model acceptance. Metrics: `{"daily_end": "2026-05-29", "daily_start": "2021-10-08", "experiment_layer": "", "overlaps_2021_2026_confirmation_window": true}`
- `stability / daily_return_random_windows`: `pass` - Randomly change backtest sub-windows and verify the result is not dependent on one lucky date range. Metrics: `{"best_window": "2021-11-23..2026-05-15:0.812655", "median_excess_return": 0.147455, "median_strategy_return": 0.396082, "min_window_days": 252, "p10_excess_return": 0.001034, "p10_strategy_return": 0.18215, "positive_window_ratio": 1.0, "random_windows": 100, "worst_window": "2022-01-11..2023-02-16:0.048844"}`
- `stability / execution_time_shift_proxy`: `pass` - Proxy for changing buy/sell timing by shifting daily returns one day. Large sensitivity requires intraday/timing attribution. Metrics: `{"base_return": 0.700671, "max_abs_diff": 0.043701, "shift_backward_return": 0.706847, "shift_forward_return": 0.65697}`
- `stability / parameter_perturbation_contract`: `pass` - Strategy validation contract should include parameter perturbation or robustness tests before PM promotion. Metrics: `{"required_tests": ["baseline", "IC_RankIC", "rolling_validation", "ablation", "random_window_robustness", "execution_time_shift_proxy", "sector_cap_parameter_perturbation"]}`
- `stability / parameter_perturbation_from_signals`: `pass` - Review whether small parameter changes alter selected_count, state cases, or factor family unexpectedly. Metrics: `{"configured_selection_count": 28, "note": "For full parameter perturbation, rerun the strategy runner with selection_count 8/10/12 or documented thresholds.", "observed_cases": "", "observed_factors": "", "observed_selected_counts": "28"}`

## Governance

This is an Engineering Agent anti-overfitting audit. It does not accept a strategy. It blocks or flags risks before PM can promote a candidate.

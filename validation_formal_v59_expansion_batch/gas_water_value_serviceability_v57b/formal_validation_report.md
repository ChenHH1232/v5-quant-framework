# Formal Validation Report: gas_water_value_serviceability_v57b

- Status: `formal_validation_completed_not_acceptance`

## notice_date_leakage_audit

- `pit_factor_visible_date_audit`: {'check': 'pit_factor_visible_date_audit', 'status': 'pass', 'checked_rows': 746, 'missing_notice_date_rows': 0, 'future_notice_violations': 0, 'detail': 'PIT-sensitive factor fields used in formal validation must have visible_date <= trade_date.'}

## factor_ic_rankic

- `None`: {'factor': 'low_price_to_book_safe', 'direction': 'lower_is_better', 'observations': 744, 'dates': 20, 'mean_ic': -0.059040251312742674, 'mean_rankic': 0.09314374519214583, 'positive_ic_ratio': 0.45, 'top_minus_bottom_mean_return': 0.01032001435384116}
- `None`: {'factor': 'dividend_yield', 'direction': 'higher_is_better', 'observations': 746, 'dates': 20, 'mean_ic': 0.013768904265782462, 'mean_rankic': 0.09125808318582673, 'positive_ic_ratio': 0.5, 'top_minus_bottom_mean_return': 0.004475596809937365}
- `None`: {'factor': 'interest_coverage_safe', 'direction': 'higher_is_better', 'observations': 647, 'dates': 20, 'mean_ic': 0.05028414885534413, 'mean_rankic': 0.056556412502938046, 'positive_ic_ratio': 0.6, 'top_minus_bottom_mean_return': 0.0163073733510377}
- `None`: {'factor': 'debt_pressure_safe', 'direction': 'lower_is_better', 'observations': 746, 'dates': 20, 'mean_ic': -0.021801686540880265, 'mean_rankic': -0.0067168267367958, 'positive_ic_ratio': 0.45, 'top_minus_bottom_mean_return': -0.005000321181085469}
- `None`: {'factor': 'capex_burden_safe', 'direction': 'lower_is_better', 'observations': 746, 'dates': 20, 'mean_ic': -0.029334347764144324, 'mean_rankic': -0.052667285095355225, 'positive_ic_ratio': 0.6, 'top_minus_bottom_mean_return': -0.016928376323395045}

## rolling_validation

- `rolling_test_2023`: {'window': '2023', 'status': 'completed', 'case': 'rolling_test_2023', 'periods': 4, 'cum_return': 0.16549065197774393, 'mean_return': 0.039048346792725, 'positive_ratio': 1.0, 'mean_selected_count': 10}
- `rolling_test_2024`: {'window': '2024', 'status': 'completed', 'case': 'rolling_test_2024', 'periods': 4, 'cum_return': 0.12611743803162767, 'mean_return': 0.031913334378699997, 'positive_ratio': 0.75, 'mean_selected_count': 10}
- `rolling_test_2025`: {'window': '2025', 'status': 'completed', 'case': 'rolling_test_2025', 'periods': 4, 'cum_return': 0.2595253044807082, 'mean_return': 0.0607527054865, 'positive_ratio': 1.0, 'mean_selected_count': 10}
- `rolling_test_2026`: {'window': '2026', 'status': 'completed', 'case': 'rolling_test_2026', 'periods': 2, 'cum_return': -0.09604920882481371, 'mean_return': -0.04643325196685, 'positive_ratio': 0.5, 'mean_selected_count': 10}

## baseline_tests

- `equal_weight_gas_water`: {'case': 'equal_weight_gas_water', 'periods': 20, 'cum_return': 0.425902054222679, 'mean_return': 0.022126521311273635, 'positive_ratio': 0.55, 'mean_selected_count': 37.3}
- `high_dividend_top10`: {'case': 'high_dividend_top10', 'periods': 20, 'cum_return': 0.5134895676067774, 'mean_return': 0.025513933023815, 'positive_ratio': 0.5, 'mean_selected_count': 10}
- `low_pb_safe_top10`: {'case': 'low_pb_safe_top10', 'periods': 20, 'cum_return': 0.7296157013748292, 'mean_return': 0.03324097543666, 'positive_ratio': 0.65, 'mean_selected_count': 10}
- `serviceability_top10`: {'case': 'serviceability_top10', 'periods': 20, 'cum_return': 0.58640424800924, 'mean_return': 0.026026866606990003, 'positive_ratio': 0.65, 'mean_selected_count': 10}
- `v57b_value_serviceability_top10`: {'case': 'v57b_value_serviceability_top10', 'periods': 20, 'cum_return': 0.9009377431603205, 'mean_return': 0.03722114104548, 'positive_ratio': 0.75, 'mean_selected_count': 10}

## ablation_tests

- `composite_current`: {'case': 'composite_current', 'periods': 20, 'cum_return': 0.9009377431603205, 'mean_return': 0.03722114104548, 'positive_ratio': 0.75, 'mean_selected_count': 10}
- `drop_low_price_to_book_safe`: {'case': 'drop_low_price_to_book_safe', 'periods': 20, 'cum_return': 0.5929561678706057, 'mean_return': 0.02802452392743, 'positive_ratio': 0.6, 'mean_selected_count': 10}
- `drop_dividend_yield`: {'case': 'drop_dividend_yield', 'periods': 20, 'cum_return': 0.7639058774569605, 'mean_return': 0.03548624634399, 'positive_ratio': 0.5, 'mean_selected_count': 10}
- `drop_interest_coverage_safe`: {'case': 'drop_interest_coverage_safe', 'periods': 20, 'cum_return': 0.8202298888860382, 'mean_return': 0.035952219887440004, 'positive_ratio': 0.65, 'mean_selected_count': 10}
- `drop_debt_pressure_safe`: {'case': 'drop_debt_pressure_safe', 'periods': 20, 'cum_return': 0.8700313609767607, 'mean_return': 0.035638037992345, 'positive_ratio': 0.75, 'mean_selected_count': 10}
- `drop_capex_burden_safe`: {'case': 'drop_capex_burden_safe', 'periods': 20, 'cum_return': 0.9244735906136841, 'mean_return': 0.03906143072848, 'positive_ratio': 0.65, 'mean_selected_count': 10}

## robustness_tests

- `selection_count_8`: {'case': 'selection_count_8', 'periods': 20, 'cum_return': 0.8818419926134891, 'mean_return': 0.03624131391745, 'positive_ratio': 0.75, 'mean_selected_count': 8}
- `selection_count_10`: {'case': 'selection_count_10', 'periods': 20, 'cum_return': 0.9009377431603205, 'mean_return': 0.03722114104548, 'positive_ratio': 0.75, 'mean_selected_count': 10}
- `selection_count_12`: {'case': 'selection_count_12', 'periods': 20, 'cum_return': 0.6844461525585948, 'mean_return': 0.031016021008125002, 'positive_ratio': 0.65, 'mean_selected_count': 12}
- `weight_scale_0.8`: {'case': 'weight_scale_0.8', 'periods': 20, 'cum_return': 0.8235415999351456, 'mean_return': 0.03536538510113, 'positive_ratio': 0.7, 'mean_selected_count': 10}
- `weight_scale_1.0`: {'case': 'weight_scale_1.0', 'periods': 20, 'cum_return': 0.9009377431603205, 'mean_return': 0.03722114104548, 'positive_ratio': 0.75, 'mean_selected_count': 10}
- `weight_scale_1.2`: {'case': 'weight_scale_1.2', 'periods': 20, 'cum_return': 0.8241402702412537, 'mean_return': 0.034779728507485, 'positive_ratio': 0.7, 'mean_selected_count': 10}

## common_sample_interaction_tests

- `common_v57b_value_serviceability`: {'case': 'common_v57b_value_serviceability', 'periods': 20, 'cum_return': 0.6580991450281457, 'mean_return': 0.030686097558660003, 'positive_ratio': 0.65, 'mean_selected_count': 10, 'common_sample_rows': 647, 'common_sample_dates': 20, 'common_sample_securities': 40, 'required_common_fields': 'low_price_to_book_safe;dividend_yield;interest_coverage_safe;debt_pressure_safe;capex_burden_safe', 'tested_factors': 'low_price_to_book_safe;dividend_yield;interest_coverage_safe;debt_pressure_safe;capex_burden_safe', 'status': 'completed'}

## failure_mode_analysis

- `None`: {'year': '2022', 'periods': 4, 'selected_cum_return': -0.012002155295143258, 'selected_mean_return': -0.00029768458910000174, 'selected_positive_ratio': 0.5, 'all_universe_mean_return': -0.015318130496738094, 'low_pb_mean_return': 0.0023628791052750005, 'relative_to_all_universe_mean': 0.015020445907638093, 'relative_to_low_pb_mean': -0.0026605636943750023, 'selected_codes_by_date': '2022-01-04:002700.XSHE;601199.XSHG;601158.XSHG;605368.XSHG;605169.XSHG;600681.XSHG;002267.XSHE;605090.XSHG;603053.XSHG;601139.XSHG | 2022-04-01:002700.XSHE;601158.XSHG;605169.XSHG;601199.XSHG;605368.XSHG;600681.XSHG;002267.XSHE;605090.XSHG;603393.XSHG;603053.XSHG | 2022-07-01:605169.XSHG;002267.XSHE;601158.XSHG;603393.XSHG;605368.XSHG;605090.XSHG;603080.XSHG;600681.XSHG;603053.XSHG;002700.XSHE | 2022-10-10:601158.XSHG;605169.XSHG;605368.XSHG;002700.XSHE;600681.XSHG;603080.XSHG;002267.XSHE;603393.XSHG;603053.XSHG;600008.XSHG', 'factor_mean_notes': 'low_price_to_book_safe:selected_mean=1.91173,all_mean=4.00438865248227 ; dividend_yield:selected_mean=3.353055,all_mean=1.6535517730496454 ; interest_coverage_safe:selected_mean=51.85231245133,all_mean=36.72216048067691 ; debt_pressure_safe:selected_mean=0.3855156238,all_mean=0.5269968217822695 ; capex_burden_safe:selected_mean=100.5465959921225,all_mean=192.1592955186953', 'interpretation': '2022: outperformed_all_universe,underperformed_low_pb'}
- `None`: {'year': '2024', 'periods': 4, 'selected_cum_return': 0.12611743803162767, 'selected_mean_return': 0.031913334378699997, 'selected_positive_ratio': 0.75, 'all_universe_mean_return': 0.01518353364899439, 'low_pb_mean_return': 0.069993026087725, 'relative_to_all_universe_mean': 0.016729800729705605, 'relative_to_low_pb_mean': -0.038079691709025, 'selected_codes_by_date': '2024-01-02:603080.XSHG;600008.XSHG;601158.XSHG;600681.XSHG;600461.XSHG;600803.XSHG;605368.XSHG;002267.XSHE;601199.XSHG;600635.XSHG | 2024-04-01:603080.XSHG;600008.XSHG;601158.XSHG;605169.XSHG;600681.XSHG;600803.XSHG;002267.XSHE;601199.XSHG;600635.XSHG;600461.XSHG | 2024-07-01:605090.XSHG;002267.XSHE;603759.XSHG;603080.XSHG;600681.XSHG;605368.XSHG;601199.XSHG;600008.XSHG;605169.XSHG;603053.XSHG | 2024-10-08:605090.XSHG;600917.XSHG;600803.XSHG;603080.XSHG;600681.XSHG;605169.XSHG;603759.XSHG;600461.XSHG;605368.XSHG;001299.XSHE', 'factor_mean_notes': 'low_price_to_book_safe:selected_mean=1.6095975,all_mean=2.832087341772152 ; dividend_yield:selected_mean=3.8828575,all_mean=1.914426582278481 ; interest_coverage_safe:selected_mean=327.59148484344445,all_mean=107.53747166829352 ; debt_pressure_safe:selected_mean=0.4617905823525,all_mean=0.5332708696936709 ; capex_burden_safe:selected_mean=126.6333096717685,all_mean=160.31587540800234', 'interpretation': '2024: outperformed_all_universe,underperformed_low_pb'}
- `None`: {'year': '2026', 'periods': 2, 'selected_cum_return': -0.09604920882481371, 'selected_mean_return': -0.04643325196685, 'selected_positive_ratio': 0.5, 'all_universe_mean_return': -0.03422567948429486, 'low_pb_mean_return': -0.027488832389200003, 'relative_to_all_universe_mean': -0.012207572482555135, 'relative_to_low_pb_mean': -0.018944419577649994, 'selected_codes_by_date': '2026-01-05:600803.XSHG;002267.XSHE;605368.XSHG;600008.XSHG;600461.XSHG;601199.XSHG;001299.XSHE;600681.XSHG;601158.XSHG;002700.XSHE | 2026-04-01:600803.XSHG;002267.XSHE;001299.XSHE;605368.XSHG;603080.XSHG;600008.XSHG;600461.XSHG;600681.XSHG;601199.XSHG;002700.XSHE', 'factor_mean_notes': 'low_price_to_book_safe:selected_mean=1.745855,all_mean=3.2830881578947366 ; dividend_yield:selected_mean=4.91508,all_mean=2.1493128205128205 ; interest_coverage_safe:selected_mean=96.46261977616666,all_mean=62.52074100200769 ; debt_pressure_safe:selected_mean=0.438063875095,all_mean=0.5205220177571794 ; capex_burden_safe:selected_mean=0.5449993976075,all_mean=154.19729787186543', 'interpretation': '2026: underperformed_all_universe,underperformed_low_pb'}

## Governance

Do not use 2021-2026 platform-confirmation results for tuning. Single-model acceptance requires rolling validation.

Working directory:
D:\hh\codex\v5

Task name:
V5f structural rough-screen deep research packet

Objective:
Read `v5f_structural_rough_screen/current/` and promote only the rough-screen directions marked `worth_deep_research` into separate Quant specs. Use startup-preload repaired V57f as the only benchmark. Do not mark accepted, do not modify V57f, do not select full-market stocks, and do not scan parameters.

Required inputs:
- v5f_structural_rough_screen/current/v5f_structural_rough_screen_summary.json
- v5f_structural_rough_screen/current/v5f_structural_rough_screen_comparison_matrix.csv
- v5f_structural_rough_screen/current/v5f_structural_rough_screen_next_queue.csv
- v5f_repaired_baseline_overlay_comparison/current/v5f_repaired_overlay_summary.json

Decision rule:
- Worth deep research only if return is positive versus repaired baseline and max drawdown does not worsen.
- Positive return with worse drawdown stays diagnostic.
- Anything requiring full-market stock selection needs separate PM approval.

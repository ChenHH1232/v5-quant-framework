from __future__ import annotations

from pathlib import Path

from v5.io_utils import write_csv_rows
from v5.oil_gas_cycle_state_validation_runner import run_oil_gas_cycle_state_validation


def test_run_oil_gas_cycle_state_validation_writes_summary(tmp_path: Path) -> None:
    rows = []
    for index, trade_date in enumerate(["2022-01-04", "2022-04-01", "2022-07-01", "2022-10-10", "2023-01-03", "2023-04-03"]):
        for code_index in range(4):
            rows.append(
                {
                    "trade_date": trade_date,
                    "code": f"00000{code_index}.XSHG",
                    "future_return": str(0.01 * (code_index + 1)),
                    "crude_oil_price_state": str(100 + index),
                    "operating_cash_flow_yield": str(code_index + 1),
                    "low_vol_score": str(-code_index),
                    "low_price_to_book": str(2 + code_index),
                    "pe_ratio": str(10 + code_index),
                    "dividend_yield": str(code_index),
                    "free_cash_flow_yield": str(code_index / 10),
                }
            )
    panel = tmp_path / "panel.csv"
    write_csv_rows(panel, rows[0].keys(), rows)

    result = run_oil_gas_cycle_state_validation(panel, tmp_path / "out", min_history=2, selection_count=2)

    assert result.status == "cycle_state_diagnostic_completed_not_acceptance"
    assert result.state_covered_dates == 6
    assert result.panel_dates == 6
    assert result.summary_path.exists()
    assert result.report_path.exists()

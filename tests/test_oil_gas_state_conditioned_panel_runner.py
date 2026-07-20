from __future__ import annotations

from pathlib import Path

from v5.io_utils import read_csv_rows, write_csv_rows
from v5.oil_gas_state_conditioned_panel_runner import build_oil_gas_state_conditioned_panel


def test_build_oil_gas_state_conditioned_panel_adds_pit_cycle_scores(tmp_path: Path) -> None:
    rows = []
    dates = ["2022-01-04", "2022-04-01", "2022-07-01", "2022-10-10", "2023-01-03", "2023-04-03"]
    for date_index, trade_date in enumerate(dates):
        for code_index in range(4):
            rows.append(
                {
                    "trade_date": trade_date,
                    "code": f"60000{code_index}.XSHG",
                    "future_return": "0.01",
                    "operating_cash_flow_yield": str(code_index + 1),
                    "low_vol_score": str(10 - code_index),
                    "pe_ratio": str(8 + code_index),
                    "crude_oil_price_state": str(100 - date_index),
                    "bitumen_price_state": str(90 - date_index),
                    "refining_spread_proxy_state": str(50 + date_index),
                    "gas_liquid_price_state": str(70 - date_index),
                }
            )
    panel = tmp_path / "panel.csv"
    write_csv_rows(panel, rows[0].keys(), rows)

    result = build_oil_gas_state_conditioned_panel(panel, tmp_path / "out", min_history=2)

    assert result.status == "research_pit_validation_ready"
    out_rows = read_csv_rows(result.panel_path)
    assert len(out_rows) == len(rows)
    assert "oil_gas_cycle_policy" in out_rows[0]
    assert any(row["state_conditioned_ocf_score"] for row in out_rows)
    assert any(row["cycle_defensive_low_vol_score"] for row in out_rows)

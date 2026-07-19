from __future__ import annotations

from pathlib import Path

from v5.basket_joinquant_export_runner import export_basket_frozen_signals_to_joinquant


def test_export_basket_frozen_signals_to_joinquant(tmp_path: Path) -> None:
    signals = tmp_path / "basket_rebalance_signals.csv"
    signals.write_text(
        "trade_date,code,sector_id,selected_rank,target_weight\n"
        "2026-01-05,600900.XSHG,utilities_electricity,2,0.04\n"
        "2026-01-05,601398.XSHG,bank,1,0.03\n"
        "2026-04-01,600033.XSHG,highway_infrastructure,1,0.05\n",
        encoding="utf-8",
    )
    out_file = tmp_path / "frozen.py"

    result = export_basket_frozen_signals_to_joinquant(
        signals,
        out_file,
        strategy_id="test_basket",
        script_version="test_script_v1",
    )

    text = out_file.read_text(encoding="utf-8")
    assert result.signal_date_count == 2
    assert result.holding_count == 3
    assert "test_basket" in text
    assert "'2026-01-05': [('601398.XSHG', 0.030000000000, 'bank')" in text
    assert "order_target_value(code, target_value)" in text
    assert "order_target_percent(" not in text

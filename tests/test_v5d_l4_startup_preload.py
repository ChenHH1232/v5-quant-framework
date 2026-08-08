from __future__ import annotations

from pathlib import Path


def test_v5d_load_inputs_uses_deployment_window_instead_of_old_first_signal() -> None:
    source = Path("src/v5/v5d_order_scheduling_engineering_runner.py").read_text(encoding="utf-8")
    assert "first_signal = min(_load_signals(V57F_SIGNALS))" not in source
    assert 'deployment_start = str(config.get("portfolio", {}).get("start_date") or ENGINEERING_WINDOW_START)' in source


def test_v5d_l4_keeps_data_gate_blocker_for_incomplete_d0_d1_d2() -> None:
    source = Path("src/v5/v5d_l4_order_completion_engineering_runner.py").read_text(encoding="utf-8")
    assert "blocked_data_gate_not_full_pass" in source
    assert "D0/D1/D2 data coverage is not complete" in source

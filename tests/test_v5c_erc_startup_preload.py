from __future__ import annotations

from pathlib import Path


def test_v5c_erc_engineering_does_not_hardcode_old_first_signal_start_date() -> None:
    source = Path("src/v5/v5c_risk_budget_overlay_engineering_runner.py").read_text(encoding="utf-8")
    assert 'start_date = "2021-10-08"' not in source
    assert 'window.get("start_date")' in source
    assert "insufficient_prior_history_use_equal" in source

from __future__ import annotations

import json
from pathlib import Path

from v5.basket_paper_input_preflight_runner import run_basket_paper_input_preflight


def _write_config(path: Path, panel: Path, price: Path, dividend: Path) -> Path:
    payload = {
        "sectors": [
            {
                "sector_id": "utilities",
                "strategy_id": "s",
                "panel_csv": str(panel),
                "price_csv": str(price),
                "dividend_csv": str(dividend),
            }
        ],
        "portfolio": {"required_fields": ["low_vol_score", "dividend_yield"]},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_paper_input_preflight_marks_future_window_pending(tmp_path: Path) -> None:
    panel = tmp_path / "panel.csv"
    panel.write_text("trade_date,code,low_vol_score,dividend_yield\n2026-07-01,A,1,3\n", encoding="utf-8")
    price = tmp_path / "price.csv"
    price.write_text("date,code,open,close\n2026-07-18,A,1,1\n", encoding="utf-8")
    dividend = tmp_path / "dividend.csv"
    dividend.write_text("code,pay_date,net_cash_per_share\nA,2026-06-01,0.1\n", encoding="utf-8")
    config = _write_config(tmp_path / "config.json", panel, price, dividend)

    result = run_basket_paper_input_preflight(
        config_path=config,
        strategy_id="test",
        target_rebalance_date="2026-10-08",
        as_of_date="2026-07-19",
        out_dir=tmp_path / "out",
    )

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert result.status == "pending_future_data_window"
    assert summary["sector_checks"][0]["status"] == "target_panel_rows_missing"


def test_paper_input_preflight_ready_on_target_date(tmp_path: Path) -> None:
    panel = tmp_path / "panel.csv"
    panel.write_text("trade_date,code,low_vol_score,dividend_yield\n2026-10-08,A,1,3\n", encoding="utf-8")
    price = tmp_path / "price.csv"
    price.write_text("date,code,open,close\n2026-10-07,A,1,1\n", encoding="utf-8")
    dividend = tmp_path / "dividend.csv"
    dividend.write_text("code,pay_date,net_cash_per_share\nA,2026-09-30,0.1\n", encoding="utf-8")
    config = _write_config(tmp_path / "config.json", panel, price, dividend)

    result = run_basket_paper_input_preflight(
        config_path=config,
        strategy_id="test",
        target_rebalance_date="2026-10-08",
        prior_trading_date="2026-10-07",
        as_of_date="2026-10-08",
        out_dir=tmp_path / "out",
    )

    assert result.status == "ready_to_construct_clean_paper_signal"
    assert result.blocker_count == 0


def test_paper_input_preflight_blocks_missing_files_when_due(tmp_path: Path) -> None:
    config = _write_config(tmp_path / "config.json", tmp_path / "panel.csv", tmp_path / "price.csv", tmp_path / "dividend.csv")

    result = run_basket_paper_input_preflight(
        config_path=config,
        strategy_id="test",
        target_rebalance_date="2026-10-08",
        as_of_date="2026-10-08",
        out_dir=tmp_path / "out",
    )

    assert result.status == "blocked_missing_or_stale_inputs"
    assert result.blocker_count == 1

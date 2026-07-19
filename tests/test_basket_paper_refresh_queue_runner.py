from __future__ import annotations

import json
from pathlib import Path

from v5.basket_paper_refresh_queue_runner import build_basket_paper_refresh_queue


def test_refresh_queue_splits_preflight_gaps_into_tasks(tmp_path: Path) -> None:
    preflight = {
        "strategy_id": "test_basket",
        "as_of_date": "2026-07-20",
        "target_rebalance_date": "2026-10-08",
        "prior_trading_date": "2026-10-07",
        "target_date_is_future": True,
        "config": "config.json",
        "sector_checks": [
            {
                "sector_id": "bank",
                "panel_exists": True,
                "price_exists": True,
                "dividend_exists": True,
                "latest_panel_trade_date": "2026-04-01",
                "latest_price_date": "2026-05-29",
                "latest_dividend_pay_date": "2026-05-29",
                "target_panel_rows": 0,
                "target_rows_missing_required_fields": 0,
                "latest_stale_fallback_rows": 42,
                "target_stale_fallback_rows": 0,
                "panel_csv": "panel.csv",
                "price_csv": "price.csv",
                "dividend_csv": "dividend.csv",
            }
        ],
    }
    path = tmp_path / "preflight.json"
    path.write_text(json.dumps(preflight), encoding="utf-8")

    result = build_basket_paper_refresh_queue(path, tmp_path / "out")

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    queue = result.queue_path.read_text(encoding="utf-8")
    assert result.status == "queued_for_future_refresh_window"
    assert result.task_count == 6
    assert summary["task_counts_by_type"]["refresh_pit_panel"] == 1
    assert "audit_or_repair_stale_fallback" in queue
    assert "rerun_paper_input_preflight" in queue


def test_refresh_queue_handles_ready_preflight_with_global_gate_tasks(tmp_path: Path) -> None:
    preflight = {
        "strategy_id": "test_basket",
        "as_of_date": "2026-10-08",
        "target_rebalance_date": "2026-10-08",
        "prior_trading_date": "2026-10-07",
        "target_date_is_future": False,
        "config": "config.json",
        "sector_checks": [
            {
                "sector_id": "utilities",
                "panel_exists": True,
                "price_exists": True,
                "dividend_exists": True,
                "latest_panel_trade_date": "2026-10-08",
                "latest_price_date": "2026-10-07",
                "latest_dividend_pay_date": "2026-10-07",
                "target_panel_rows": 10,
                "target_rows_missing_required_fields": 0,
                "latest_stale_fallback_rows": 0,
                "target_stale_fallback_rows": 0,
                "panel_csv": "panel.csv",
                "price_csv": "price.csv",
                "dividend_csv": "dividend.csv",
            }
        ],
    }
    path = tmp_path / "preflight.json"
    path.write_text(json.dumps(preflight), encoding="utf-8")

    result = build_basket_paper_refresh_queue(path, tmp_path / "out")

    assert result.status == "refresh_tasks_required_before_signal"
    assert result.task_count == 2

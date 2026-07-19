from __future__ import annotations

import json
from pathlib import Path

from v5.basket_forward_paper_gate_runner import prepare_basket_forward_paper_gate


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_prepare_basket_forward_paper_gate_uses_calendar_for_next_rebalance(tmp_path: Path) -> None:
    signals = tmp_path / "signals.csv"
    signals.write_text("trade_date,code,target_weight\n2026-07-01,600900.XSHG,1\n", encoding="utf-8")
    paper = _write_json(
        tmp_path / "paper.json",
        {"signals_path": str(signals), "created_at_utc": "2026-07-19T05:50:49+00:00", "holding_count": 1},
    )
    pm_gate = _write_json(tmp_path / "pm_gate.json", {"status": "formal_candidate_pending_platform_exports", "needs_review_count": 3})
    config = _write_json(
        tmp_path / "config.json",
        {"sectors": [{"sector_id": "bank"}, {"sector_id": "utilities_electricity"}]},
    )
    calendar = tmp_path / "calendar.csv"
    calendar.write_text("trade_date\n2026-10-09\n2026-10-12\n", encoding="utf-8")

    result = prepare_basket_forward_paper_gate(
        strategy_id="test_basket",
        config_path=config,
        current_paper_summary=paper,
        pm_gate_summary=pm_gate,
        trading_calendar_csv=calendar,
        as_of_date="2026-07-19",
        out_dir=tmp_path / "out",
    )

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert result.status == "pending_clean_future_rebalance"
    assert result.next_rebalance_date == "2026-10-09"
    assert summary["next_quarter_start"] == "2026-10-01"
    assert summary["next_rebalance_date_source"] == "trading_calendar_csv"
    assert summary["last_record_type"] == "late_recorded_initialization"
    assert "return_tuning" in summary["blocked_actions"]


def test_prepare_basket_forward_paper_gate_blocks_past_manual_date(tmp_path: Path) -> None:
    signals = tmp_path / "signals.csv"
    signals.write_text("trade_date,code,target_weight\n2026-07-01,600900.XSHG,1\n", encoding="utf-8")
    paper = _write_json(tmp_path / "paper.json", {"signals_path": str(signals)})
    pm_gate = _write_json(tmp_path / "pm_gate.json", {"status": "formal_candidate_pending_platform_exports"})
    config = _write_json(tmp_path / "config.json", {"sectors": []})

    result = prepare_basket_forward_paper_gate(
        strategy_id="test_basket",
        config_path=config,
        current_paper_summary=paper,
        pm_gate_summary=pm_gate,
        next_rebalance_date="2026-07-01",
        as_of_date="2026-07-19",
        out_dir=tmp_path / "out",
    )

    assert result.status == "blocked_rebalance_date_not_future"

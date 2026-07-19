from __future__ import annotations

import json
from pathlib import Path

from v5.basket_pm_gate_runner import run_basket_pm_gate


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_basket_pm_gate_flags_pending_platform_exports(tmp_path: Path) -> None:
    formal = _write_json(
        tmp_path / "formal.json",
        {
            "status": "formal_validation_completed_not_acceptance",
            "signal_count": 2,
            "panel_row_count": 20,
            "weak_year_analysis": [{"year": "2026", "diagnosis_required": "yes"}],
        },
    )
    daily = _write_json(
        tmp_path / "daily.json",
        {
            "trade_count": 4,
            "dividend_count": 1,
            "metrics": {
                "strategy_return": 0.2,
                "benchmark_return": 0.1,
                "excess_return": 0.1,
                "max_drawdown": 0.08,
            },
        },
    )
    overfit = _write_json(tmp_path / "overfit.json", {"blocker_count": 0, "needs_review_count": 1})
    ablation = _write_json(tmp_path / "ablation.json", {"cases": [{"case": "base", "status": "completed"}]})
    platform = _write_json(tmp_path / "platform.json", {"status": "pending_attribution"})
    paper = _write_json(tmp_path / "paper.json", {"holding_count": 28, "note": "late-recorded initialization"})

    result = run_basket_pm_gate(
        strategy_id="test_basket",
        formal_summary=formal,
        daily_summary=daily,
        overfit_summary=overfit,
        ablation_summary=ablation,
        platform_packet=platform,
        paper_signal_summary=paper,
        out_dir=tmp_path / "out",
    )

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert result.blocker_count == 0
    assert result.status == "formal_candidate_pending_platform_exports"
    assert summary["needs_review_count"] == 4
    assert summary["metrics_snapshot"]["local_strategy_return"] == 0.2


def test_basket_pm_gate_blocks_missing_daily_trades(tmp_path: Path) -> None:
    formal = _write_json(tmp_path / "formal.json", {"status": "formal_validation_completed_not_acceptance", "signal_count": 2})
    daily = _write_json(tmp_path / "daily.json", {"trade_count": 0, "dividend_count": 0, "metrics": {}})
    overfit = _write_json(tmp_path / "overfit.json", {"blocker_count": 0, "needs_review_count": 0})

    result = run_basket_pm_gate(
        strategy_id="test_basket",
        formal_summary=formal,
        daily_summary=daily,
        overfit_summary=overfit,
        out_dir=tmp_path / "out",
    )

    assert result.status == "blocked"
    assert result.blocker_count == 1

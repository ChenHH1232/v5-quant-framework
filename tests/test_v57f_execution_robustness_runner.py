from __future__ import annotations

import csv
import json
from pathlib import Path

from v5.v57f_execution_robustness_runner import run_v57f_execution_robustness


def test_v57f_execution_robustness_generates_freeze_and_variant_matrix(tmp_path: Path) -> None:
    price_csv = tmp_path / "prices.csv"
    _write_csv(
        price_csv,
        ["date", "code", "open", "close", "high_limit", "low_limit", "paused"],
        [
            ["2021-10-08", "000001.XSHE", 10, 10.2, 11, 9, 0],
            ["2021-10-11", "000001.XSHE", 10.3, 10.4, 11.22, 9.18, 0],
            ["2021-10-12", "000001.XSHE", 10.5, 10.6, 11.44, 9.36, 0],
            ["2022-01-04", "000001.XSHE", 11, 11.1, 12.1, 9.9, 0],
            ["2022-01-05", "000001.XSHE", 11.2, 11.3, 12.21, 10.0, 0],
        ],
    )
    dividend_csv = tmp_path / "dividends.csv"
    _write_csv(dividend_csv, ["code", "ex_date", "net_cash_per_share"], [["000001.XSHE", "2022-01-05", 0.1]])
    signals_csv = tmp_path / "signals.csv"
    _write_csv(
        signals_csv,
        ["trade_date", "code", "target_weight"],
        [["2021-10-08", "000001.XSHE", 1.0], ["2022-01-04", "000001.XSHE", 1.0]],
    )
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "project": "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f",
                "portfolio": {"start_date": "2021-05-01", "end_date": "2022-01-05"},
                "sectors": [{"sector_id": "bank", "price_csv": str(price_csv), "dividend_csv": str(dividend_csv)}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    baseline_summary = tmp_path / "baseline_summary.json"
    baseline_summary.write_text(
        json.dumps(
            {
                "metrics": {"strategy_return": 0.1, "benchmark_return": 0.05, "max_drawdown": 0.02, "sharpe": 1.0},
                "trade_count": 2,
                "dividend_count": 1,
                "rebalance_order_health": {
                    "rebalance_signal_count": 2,
                    "first_executed_order_date": "2021-10-08",
                    "first_position_date": "2021-10-08",
                },
            }
        ),
        encoding="utf-8",
    )
    production_summary = tmp_path / "production_summary.json"
    production_summary.write_text(
        json.dumps(
            {
                "status": "engineering_local_refresh_ready_not_platform_replication",
                "evidence": {
                    "pm_gate_summary": {"status": "formal_candidate_paper_tracking_started_needs_review"},
                    "action_route_summary": {"status": "no_action_until_external_event"},
                },
            }
        ),
        encoding="utf-8",
    )

    result = run_v57f_execution_robustness(
        config_path=config,
        signals_csv=signals_csv,
        baseline_summary_path=baseline_summary,
        production_summary_path=production_summary,
        out_dir=tmp_path / "out",
        initial_cash=100_000,
    )

    assert result.variant_count == 8
    manifest = json.loads(result.freeze_manifest.read_text(encoding="utf-8"))
    assert manifest["freeze_status"] == "frozen_execution_robustness_candidate_not_tuned"
    assert manifest["core_sleeves"] == ["bank"]
    assert "accepted_strategy" in manifest["not_status"]

    rows = list(csv.DictReader(result.variant_matrix_csv.open("r", encoding="utf-8")))
    assert {row["execution_variant"] for row in rows} >= {"rebalance_day_open", "t_plus_1_open", "sliced_3d_open"}
    assert all(row["rebalance_order_health"] in {"pass", "needs_review"} for row in rows)
    assert all(row["conclusion"] for row in rows)

    risk_text = result.risk_control_log_csv.read_text(encoding="utf-8")
    assert "non_rebalance_no_action" in risk_text
    summary = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert summary["status"] == "execution_robustness_completed_not_tuning"
    assert "platform_replication_passed" in summary["not_status"]


def _write_csv(path: Path, fieldnames: list[str], rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fieldnames)
        writer.writerows(rows)

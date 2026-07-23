from __future__ import annotations

import csv
import json
from pathlib import Path

from v5.telecom_engineering_readiness_runner import review_telecom_engineering_readiness


def test_telecom_engineering_readiness_allows_capped_observation_only(tmp_path: Path) -> None:
    formal = tmp_path / "formal.json"
    _write_json(
        formal,
        {
            "status": "formal_validation_completed_not_acceptance",
            "row_count": 52,
            "date_count": 20,
            "rolling_validation": [{"window": "2026", "cum_return": -0.17}],
            "common_sample_interaction_tests": [{"common_sample_securities": 3}],
            "baseline_tests": [{"case": "cashflow_dividend_composite_top2", "cum_return": 0.48}],
            "factor_ic_rankic": [{"factor": "dividend_yield", "mean_rankic": 0.33}],
        },
    )
    overlay_daily = tmp_path / "overlay_daily.json"
    _write_json(
        overlay_daily,
        {
            "metrics": {
                "strategy_return": 0.80,
                "excess_return": 0.28,
                "max_drawdown": 0.11,
                "information_ratio": 0.40,
            },
            "signal_count": 19,
            "trade_count": 700,
            "dividend_count": 20,
        },
    )
    overlay_formal = tmp_path / "overlay_formal.json"
    _write_json(
        overlay_formal,
        {
            "status": "formal_validation_completed_not_acceptance",
            "sector_exposure": [{"sector_id": "telecom_operators", "avg_weight_per_rebalance": "0.07"}],
        },
    )
    v57f = tmp_path / "v57f.json"
    _write_json(v57f, {"metrics": {"strategy_return": 0.81, "max_drawdown": 0.12, "information_ratio": 0.44}})
    panel = tmp_path / "panel.csv"
    price = tmp_path / "price.csv"
    dividend = tmp_path / "dividend.csv"
    benchmark = tmp_path / "benchmark.csv"
    _write_csv(panel, ["trade_date", "code", "volatility_120d"], [["2026-04-01", "600050.XSHG", "0.2"]])
    _write_csv(price, ["date", "code", "open", "close"], [["2026-05-29", "600050.XSHG", "5", "5.1"]])
    _write_csv(dividend, ["pay_date", "code", "net_cash_per_share"], [["2026-05-29", "600050.XSHG", "0.1"]])
    _write_csv(benchmark, ["date", "benchmark_id", "close"], [["2026-05-29", "telecom", "1"]])

    result = review_telecom_engineering_readiness(
        formal_summary=formal,
        overlay_daily_summary=overlay_daily,
        overlay_formal_summary=overlay_formal,
        panel_csv=panel,
        price_csv=price,
        dividend_csv=dividend,
        benchmark_csv=benchmark,
        v57f_summary=v57f,
        out_dir=tmp_path / "out",
        agent_packet_dir=tmp_path / "packets",
    )

    assert result.status == "engineering_observation_sleeve_ready"
    payload = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert payload["pm_decision"]["can_enter_engineering"] is True
    assert payload["pm_decision"]["can_promote_standalone"] is False
    assert payload["pm_decision"]["can_join_v57f_core"] is False
    assert payload["pm_decision"]["can_enter_platform_replication"] is False
    assert payload["sample_policy"]["decision"] == "standalone_blocked_small_sample_capped_observation_only"
    queue = list(csv.DictReader(result.engineering_queue_csv.open("r", encoding="utf-8-sig")))
    assert len(queue) == 1
    assert queue[0]["owner"] == "Engineering Agent"
    assert "do_not_modify_V57f" in queue[0]["blocked_actions"]
    assert "do_not_platform_replication" in queue[0]["blocked_actions"]
    report = result.report_md.read_text(encoding="utf-8")
    assert "Detailed Flow Table" in report
    assert "capped observation sleeve" in report
    assert result.agent_packet_json.exists()


def test_telecom_engineering_readiness_blocks_missing_dividends(tmp_path: Path) -> None:
    formal = tmp_path / "formal.json"
    _write_json(
        formal,
        {
            "status": "formal_validation_completed_not_acceptance",
            "common_sample_interaction_tests": [{"common_sample_securities": 3}],
        },
    )
    overlay_daily = tmp_path / "overlay_daily.json"
    _write_json(overlay_daily, {"metrics": {"strategy_return": 0.8}})
    overlay_formal = tmp_path / "overlay_formal.json"
    _write_json(overlay_formal, {"status": "formal_validation_completed_not_acceptance"})
    v57f = tmp_path / "v57f.json"
    _write_json(v57f, {"metrics": {"strategy_return": 0.81}})
    panel = tmp_path / "panel.csv"
    price = tmp_path / "price.csv"
    dividend = tmp_path / "missing_dividend.csv"
    benchmark = tmp_path / "benchmark.csv"
    _write_csv(panel, ["trade_date", "code"], [["2026-04-01", "600050.XSHG"]])
    _write_csv(price, ["date", "code", "open", "close"], [["2026-05-29", "600050.XSHG", "5", "5.1"]])
    _write_csv(benchmark, ["date", "benchmark_id", "close"], [["2026-05-29", "telecom", "1"]])

    result = review_telecom_engineering_readiness(
        formal_summary=formal,
        overlay_daily_summary=overlay_daily,
        overlay_formal_summary=overlay_formal,
        panel_csv=panel,
        price_csv=price,
        dividend_csv=dividend,
        benchmark_csv=benchmark,
        v57f_summary=v57f,
        out_dir=tmp_path / "out",
        agent_packet_dir=tmp_path / "packets",
    )

    assert result.status == "research_or_data_repair_required_before_engineering"
    payload = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert payload["pm_decision"]["can_enter_engineering"] is False
    queue = list(csv.DictReader(result.engineering_queue_csv.open("r", encoding="utf-8-sig")))
    assert queue == []


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_csv(path: Path, fieldnames: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fieldnames)
        writer.writerows(rows)

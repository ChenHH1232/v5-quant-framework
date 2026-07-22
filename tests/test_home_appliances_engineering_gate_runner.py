from __future__ import annotations

import csv
import json
from pathlib import Path

from v5.home_appliances_engineering_gate_runner import build_home_appliances_engineering_gate


def test_home_appliances_engineering_gate_allows_local_daily_only(tmp_path: Path) -> None:
    formal = tmp_path / "formal_summary.json"
    formal.write_text(
        json.dumps(
            {
                "status": "formal_validation_completed_not_acceptance",
                "row_count": 20,
                "date_count": 4,
                "notice_date_leakage_audit": [{"check": "pit", "status": "pass"}],
                "rolling_validation": [
                    {"window": "2023", "status": "completed"},
                    {"window": "2024", "status": "completed"},
                    {"window": "2025", "status": "completed"},
                    {"window": "2026", "status": "completed"},
                ],
                "factor_ic_rankic": [{"factor": "ocf"}, {"factor": "cash_conversion"}],
            }
        ),
        encoding="utf-8",
    )
    state = tmp_path / "state_summary.json"
    state.write_text(
        json.dumps(
            {
                "status": "state_diagnostic_completed_not_engineering_handoff",
                "bucket_rows": [{"metric": "external_real_estate_climate_index"}, {"metric": "sector_inventory_to_revenue_median"}],
            }
        ),
        encoding="utf-8",
    )
    panel = tmp_path / "panel.csv"
    price = tmp_path / "price.csv"
    dividend = tmp_path / "dividend.csv"
    benchmark = tmp_path / "benchmark.csv"
    _write_csv(panel, ["trade_date", "code"], [["2026-04-01", "000001.XSHE"]])
    _write_csv(price, ["date", "code", "open", "close"], [["2026-05-29", "000001.XSHE", "1", "1"]])
    _write_csv(dividend, ["pay_date", "code", "net_cash_per_share"], [["2026-05-29", "000001.XSHE", "0.1"]])
    _write_csv(benchmark, ["date", "benchmark_id", "close"], [["2026-05-29", "home_appliances", "1"]])

    result = build_home_appliances_engineering_gate(
        formal_summary=formal,
        state_diagnostic=state,
        panel_csv=panel,
        price_csv=price,
        dividend_csv=dividend,
        benchmark_csv=benchmark,
        out_dir=tmp_path / "out",
        agent_packet_dir=tmp_path / "packets",
    )

    assert result.status == "engineering_handoff_ready_local_daily_only"
    payload = json.loads(result.summary_json.read_text(encoding="utf-8"))
    assert payload["state_policy"]["decision"] == "no_state_scoring_or_guard_policy_accepted_for_engineering_smoke_test"
    queue = list(csv.DictReader(result.engineering_queue_csv.open("r", encoding="utf-8")))
    assert len(queue) == 1
    assert queue[0]["owner"] == "Engineering Agent"
    assert "do_not_add_to_V57f" in queue[0]["blocked_actions"]
    assert "do_not_tune" in queue[0]["blocked_actions"]
    assert result.agent_packet_json.exists()
    report = result.report_path.read_text(encoding="utf-8")
    assert "Detailed Flow Table" in report
    assert "External macro state variables are diagnostic only" in report


def _write_csv(path: Path, fields: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerows(rows)

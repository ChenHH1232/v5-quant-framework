from __future__ import annotations

import csv
import json

from v5.gas_water_operating_evidence_runner import (
    _approved_gas_water_business_tag,
    _gas_water_segment_ratios,
    build_gas_water_business_purity_panel,
    collect_eastmoney_gas_water_segment_evidence,
)
from v5.io_utils import write_csv_rows


def test_gas_water_segment_ratios_classify_core_gas_operator() -> None:
    rows = [
        {"item_name": "\u5929\u7136\u6c14\u9500\u552e", "main_business_income": "800"},
        {"item_name": "\u5de5\u7a0b\u5b89\u88c5", "main_business_income": "200"},
    ]

    ratios = _gas_water_segment_ratios(rows)

    assert round(ratios["gas_revenue_share"], 4) == 0.8
    assert round(ratios["project_engineering_revenue_share"], 4) == 0.2
    assert _approved_gas_water_business_tag(ratios) == "core_gas_operator"


def test_gas_water_segment_ratios_flag_project_contamination() -> None:
    rows = [
        {"item_name": "\u6c61\u6c34\u5904\u7406\u8fd0\u8425", "main_business_income": "300"},
        {"item_name": "\u73af\u4fdd\u5de5\u7a0b\u65bd\u5de5", "main_business_income": "700"},
    ]

    ratios = _gas_water_segment_ratios(rows)

    assert round(ratios["water_revenue_share"], 4) == 0.3
    assert round(ratios["project_engineering_revenue_share"], 4) == 0.7
    assert _approved_gas_water_business_tag(ratios) == "non_operator_or_needs_review"


def test_collect_eastmoney_gas_water_segment_evidence_with_stub(tmp_path, monkeypatch) -> None:
    panel = tmp_path / "panel.csv"
    disclosure = tmp_path / "disclosure.csv"
    out_dir = tmp_path / "out"
    write_csv_rows(panel, ["trade_date", "code"], [{"trade_date": "2025-04-01", "code": "600000.XSHG"}])
    write_csv_rows(disclosure, ["code", "report_period", "notice_date"], [{"code": "600000.XSHG", "report_period": "2024-12-31", "notice_date": "2025-03-30"}])

    def fake_fetch(code: str, timeout: float):
        return [
            {"REPORT_DATE": "2024-12-31", "MAINOP_TYPE": "2", "ITEM_NAME": "\u4f9b\u6c34\u4e1a\u52a1", "MAIN_BUSINESS_INCOME": "600", "MBI_RATIO": "60"},
            {"REPORT_DATE": "2024-12-31", "MAINOP_TYPE": "2", "ITEM_NAME": "\u5de5\u7a0b\u5efa\u8bbe", "MAIN_BUSINESS_INCOME": "400", "MBI_RATIO": "40"},
        ]

    monkeypatch.setattr("v5.gas_water_operating_evidence_runner._fetch_eastmoney_segment_records", fake_fetch)

    evidence = collect_eastmoney_gas_water_segment_evidence(panel, disclosure, out_dir, sleep_seconds=0)
    rows = list(csv.DictReader(evidence.open(encoding="utf-8")))

    assert rows[0]["approved_gas_water_business_tag"] == "core_water_operator"
    assert rows[0]["pit_usable"] == "true"
    manifest = json.loads((out_dir / "eastmoney_gas_water_segment_evidence_manifest.json").read_text(encoding="utf-8"))
    assert manifest["pit_usable_rows"] == 1


def test_build_gas_water_business_purity_panel_uses_latest_visible_evidence(tmp_path) -> None:
    panel = tmp_path / "panel.csv"
    evidence = tmp_path / "evidence.csv"
    out_dir = tmp_path / "out"
    write_csv_rows(
        panel,
        ["trade_date", "code", "total_return"],
        [
            {"trade_date": "2025-03-01", "code": "600000.XSHG", "total_return": "0.01"},
            {"trade_date": "2025-04-01", "code": "600000.XSHG", "total_return": "0.02"},
        ],
    )
    write_csv_rows(
        evidence,
        [
            "code",
            "report_period",
            "visible_date",
            "gas_revenue_share",
            "water_revenue_share",
            "operator_revenue_share",
            "project_engineering_revenue_share",
            "non_operator_revenue_share",
            "approved_gas_water_business_tag",
            "pit_usable",
            "review_status",
        ],
        [
            {
                "code": "600000.XSHG",
                "report_period": "2024-12-31",
                "visible_date": "2025-03-30",
                "gas_revenue_share": "0",
                "water_revenue_share": "0.8",
                "operator_revenue_share": "0.8",
                "project_engineering_revenue_share": "0.2",
                "non_operator_revenue_share": "0.2",
                "approved_gas_water_business_tag": "core_water_operator",
                "pit_usable": "true",
                "review_status": "eastmoney_segment_needs_spot_check",
            }
        ],
    )

    passed = build_gas_water_business_purity_panel(panel, evidence, out_dir)
    rows = list(csv.DictReader(passed.open(encoding="utf-8")))

    assert len(rows) == 1
    assert rows[0]["trade_date"] == "2025-04-01"
    assert rows[0]["business_purity_gate"] == "passed"

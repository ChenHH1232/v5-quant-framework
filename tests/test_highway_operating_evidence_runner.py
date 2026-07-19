from __future__ import annotations

from v5.highway_operating_evidence_runner import (
    _approved_highway_business_tag,
    _audit_operating_row,
    _highway_segment_ratios,
    _reviewed_operating_flags,
    _to_cninfo_stock,
    build_reviewed_operating_panel,
)
from v5.io_utils import read_csv_rows, write_csv_rows


def test_highway_segment_ratios_classify_core_toll_business() -> None:
    rows = [
        {"item_name": "通行费收入", "main_business_income": "900"},
        {"item_name": "服务区租赁", "main_business_income": "100"},
    ]

    ratios = _highway_segment_ratios(rows)

    assert round(ratios["toll_revenue_ratio"], 4) == 0.9
    assert round(ratios["highway_revenue_ratio"], 4) == 0.9
    assert round(ratios["non_highway_revenue_ratio"], 4) == 0.1
    assert _approved_highway_business_tag(ratios) == "core_toll_road_operator"


def test_highway_segment_ratios_flag_non_highway_contamination() -> None:
    rows = [
        {"item_name": "通行费收入", "main_business_income": "200"},
        {"item_name": "房地产销售", "main_business_income": "800"},
    ]

    ratios = _highway_segment_ratios(rows)

    assert round(ratios["highway_revenue_ratio"], 4) == 0.2
    assert round(ratios["non_highway_revenue_ratio"], 4) == 0.8
    assert _approved_highway_business_tag(ratios) == "non_highway_contaminated"


def test_audit_operating_row_requires_original_report_fields() -> None:
    audited = _audit_operating_row(
        {
            "code": "600000.XSHG",
            "report_period": "2025-12-31",
            "visible_date": "2026-03-30",
            "source_url": "",
            "traffic_volume_yoy": "",
            "toll_revenue_yoy": "",
            "remaining_concession_years": "",
            "toll_policy_change_flag": "",
            "review_status": "template_requires_original_report_operating_data",
            "pit_usable": "false",
        }
    )

    assert audited["pit_usable_final"] == "false"
    assert "missing_traffic_volume_yoy" in audited["issues"]
    assert "missing_remaining_concession_years" in audited["issues"]


def test_cninfo_stock_code_format() -> None:
    assert _to_cninfo_stock("000429.XSHE") == "000429,gssz0000429"
    assert _to_cninfo_stock("600012.XSHG") == "600012,gssh0600012"


def test_reviewed_operating_flags_require_original_report_categories() -> None:
    rows = [
        {
            "field": "traffic_volume_yoy",
            "evidence_snippet": "2024 年车流量（万辆） 同比增减 2024 年通行费收入（万元） 同比增减 4.53%",
        },
        {
            "field": "toll_revenue_amount",
            "evidence_snippet": "通行费收入（万元） 149,526.79 较去年同期减少 1.72%",
        },
        {
            "field": "remaining_concession_years",
            "evidence_snippet": "收费期限为 25 年，经营期限至 2052 年",
        },
        {
            "field": "toll_policy_change_flag",
            "evidence_snippet": "收费政策和收费标准变化会对公司经营产生影响",
        },
    ]

    flags = _reviewed_operating_flags(rows)

    assert flags["traffic_toll_table_available"] is True
    assert flags["toll_revenue_evidence_available"] is True
    assert flags["remaining_concession_evidence_available"] is True
    assert flags["toll_policy_evidence_available"] is True


def test_reviewed_operating_panel_uses_latest_visible_pit_row(tmp_path) -> None:
    panel = tmp_path / "panel.csv"
    reviewed = tmp_path / "reviewed.csv"
    out_dir = tmp_path / "out"
    write_csv_rows(
        panel,
        ["trade_date", "code", "total_return"],
        [
            {"trade_date": "2025-03-01", "code": "000429.XSHE", "total_return": "0.01"},
            {"trade_date": "2025-04-01", "code": "000429.XSHE", "total_return": "0.02"},
        ],
    )
    write_csv_rows(
        reviewed,
        [
            "code",
            "report_period",
            "visible_date",
            "traffic_toll_table_available",
            "toll_revenue_evidence_available",
            "remaining_concession_evidence_available",
            "toll_policy_evidence_available",
            "reviewed_operating_disclosure_score",
            "pit_usable",
            "review_status",
        ],
        [
            {
                "code": "000429.XSHE",
                "report_period": "2024-12-31",
                "visible_date": "2025-03-04",
                "traffic_toll_table_available": "true",
                "toll_revenue_evidence_available": "true",
                "remaining_concession_evidence_available": "true",
                "toll_policy_evidence_available": "true",
                "reviewed_operating_disclosure_score": "1",
                "pit_usable": "true",
                "review_status": "rule_reviewed_original_report_candidates",
            }
        ],
    )

    formal_panel = build_reviewed_operating_panel(panel, reviewed, out_dir)

    rows = read_csv_rows(formal_panel)
    assert len(rows) == 1
    assert rows[0]["trade_date"] == "2025-04-01"
    assert rows[0]["reviewed_operating_data_available"] == "true"

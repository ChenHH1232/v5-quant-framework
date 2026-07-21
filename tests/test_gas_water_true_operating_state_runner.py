from __future__ import annotations

import csv

from v5.gas_water_true_operating_state_runner import (
    _select_report_candidate,
    build_gas_water_true_operating_state_panel,
    collect_gas_water_true_operating_state_evidence,
)
from v5.io_utils import write_csv_rows


def test_select_report_candidate_excludes_briefing_title() -> None:
    rows = [
        {
            "\u516c\u544a\u6807\u9898": "\u5173\u4e8e\u53c2\u52a02025\u5e74\u534a\u5e74\u5ea6\u62a5\u544a\u4e1a\u7ee9\u8bf4\u660e\u4f1a\u6d3b\u52a8\u7684\u516c\u544a",
            "\u516c\u544a\u94fe\u63a5": "http://example.invalid?announcementId=bad",
        },
        {
            "\u516c\u544a\u6807\u9898": "\u8463\u4e8b\u3001\u9ad8\u7ea7\u7ba1\u7406\u4eba\u5458\u5bf9\u516c\u53f82025\u5e74\u534a\u5e74\u5ea6\u62a5\u544a\u7684\u4e66\u9762\u786e\u8ba4\u610f\u89c1",
            "\u516c\u544a\u94fe\u63a5": "http://example.invalid?announcementId=also_bad",
        },
        {
            "\u516c\u544a\u6807\u9898": "2025\u5e74\u534a\u5e74\u5ea6\u62a5\u544a",
            "\u516c\u544a\u94fe\u63a5": "http://example.invalid?announcementId=good",
        },
    ]

    selected = _select_report_candidate(rows, "semiannual")

    assert selected is not None
    assert selected["\u516c\u544a\u94fe\u63a5"].endswith("announcementId=good")


def test_collect_true_operating_state_with_stubbed_sources(tmp_path) -> None:
    panel = tmp_path / "panel.csv"
    disclosure = tmp_path / "disclosure.csv"
    out_dir = tmp_path / "out"
    write_csv_rows(
        panel,
        ["trade_date", "code", "approved_gas_water_business_tag"],
        [{"trade_date": "2025-04-01", "code": "600000.XSHG", "approved_gas_water_business_tag": "core_water_operator"}],
    )
    write_csv_rows(
        disclosure,
        ["code", "report_period", "report_type", "notice_date"],
        [{"code": "600000.XSHG", "report_period": "2024-12-31", "report_type": "annual", "notice_date": "2025-03-30"}],
    )

    def fake_searcher(**kwargs):
        return [
            {
                "\u4ee3\u7801": "600000",
                "\u7b80\u79f0": "\u6d4b\u8bd5\u6c34\u52a1",
                "\u516c\u544a\u6807\u9898": "2024\u5e74\u5e74\u5ea6\u62a5\u544a",
                "\u516c\u544a\u65f6\u95f4": "2025-03-30",
                "\u516c\u544a\u94fe\u63a5": "http://example.invalid/detail?announcementId=123",
            }
        ]

    def fake_detail_fetcher(candidate, **kwargs):
        return {
            "fileUrl": "http://example.invalid/123.pdf",
            "announcement": {
                "announcementId": "123",
                "announcementTitle": "2024\u5e74\u5e74\u5ea6\u62a5\u544a",
                "secName": "\u6d4b\u8bd5\u6c34\u52a1",
            },
        }

    def fake_pdf_downloader(pdf_url, **kwargs):
        return b"%PDF fake"

    def fake_extract(pdf_bytes, *, max_pages):
        return "\u6c34\u4ef7\u8c03\u4ef7 \u5e94\u6536\u8d26\u9f84 \u8d22\u52a1\u8d39\u7528", 88

    import v5.gas_water_true_operating_state_runner as runner

    original_extract = runner._extract_pdf_text
    runner._extract_pdf_text = fake_extract
    try:
        output = collect_gas_water_true_operating_state_evidence(
            disclosure_csv=disclosure,
            panel_csv=panel,
            out_dir=out_dir,
            searcher=fake_searcher,
            detail_fetcher=fake_detail_fetcher,
            pdf_downloader=fake_pdf_downloader,
            sleep_seconds=0,
        )
    finally:
        runner._extract_pdf_text = original_extract

    rows = list(csv.DictReader(output.open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["original_announcement_checked"] == "true"
    assert rows[0]["pit_usable"] == "true"
    assert "water_tariff" in rows[0]["hit_groups"]
    assert "receivables_collection" in rows[0]["hit_groups"]


def test_build_true_operating_state_panel_uses_latest_visible_report(tmp_path) -> None:
    panel = tmp_path / "panel.csv"
    evidence = tmp_path / "evidence.csv"
    out_dir = tmp_path / "panel_out"
    write_csv_rows(
        panel,
        ["trade_date", "code", "future_return"],
        [
            {"trade_date": "2025-03-01", "code": "600000.XSHG", "future_return": "0.01"},
            {"trade_date": "2025-04-01", "code": "600000.XSHG", "future_return": "0.02"},
        ],
    )
    write_csv_rows(
        evidence,
        [
            "code",
            "report_period",
            "visible_date",
            "title",
            "pdf_url",
            "original_announcement_checked",
            "review_status",
            "extracted_text_length",
            "hit_terms",
        ],
        [
            {
                "code": "600000.XSHG",
                "report_period": "2024-12-31",
                "visible_date": "2025-03-30",
                "title": "2024\u5e74\u5e74\u5ea6\u62a5\u544a",
                "pdf_url": "http://example.invalid/1.pdf",
                "original_announcement_checked": "true",
                "review_status": "candidate",
                "extracted_text_length": "10000",
                "hit_terms": "water_tariff:\u6c34\u4ef7|receivables_collection:\u5e94\u6536",
            }
        ],
    )

    output = build_gas_water_true_operating_state_panel(panel, evidence, out_dir)
    rows = list(csv.DictReader(output.open(encoding="utf-8")))

    assert rows[0]["true_operating_state_available"] == "0"
    assert rows[1]["true_operating_state_available"] == "1"
    assert rows[1]["true_water_tariff_present"] == "1"
    assert rows[1]["true_receivables_collection_term_count"] == "1"

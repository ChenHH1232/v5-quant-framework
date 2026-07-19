from __future__ import annotations

import csv
from pathlib import Path

from v5.airport_transport_operating_evidence_runner import (
    build_airport_business_purity_panel,
    cache_airport_operating_announcement_contents,
    collect_eastmoney_airport_operating_announcements,
    collect_eastmoney_airport_segment_evidence,
    extract_airport_operating_state_values,
)


def test_airport_business_purity_panel_filters_non_airport_rows(tmp_path: Path) -> None:
    panel = tmp_path / "panel.csv"
    evidence = tmp_path / "evidence.csv"
    _write_rows(
        panel,
        ["trade_date", "code", "future_return"],
        [
            {"trade_date": "2022-04-01", "code": "600009.XSHG", "future_return": "0.1"},
            {"trade_date": "2022-04-01", "code": "000001.XSHE", "future_return": "0.2"},
        ],
    )
    _write_rows(
        evidence,
        [
            "code",
            "visible_date",
            "report_period",
            "aviation_service_revenue_share",
            "airport_commercial_revenue_share",
            "airport_operator_revenue_share",
            "non_airport_revenue_share",
            "approved_airport_business_tag",
            "review_status",
            "pit_usable",
        ],
        [
            {
                "code": "600009.XSHG",
                "visible_date": "2022-03-30",
                "report_period": "2021-12-31",
                "aviation_service_revenue_share": "0.7",
                "airport_commercial_revenue_share": "0.2",
                "airport_operator_revenue_share": "0.9",
                "non_airport_revenue_share": "0.1",
                "approved_airport_business_tag": "core_airport_operator",
                "review_status": "eastmoney_segment_needs_spot_check",
                "pit_usable": "true",
            },
            {
                "code": "000001.XSHE",
                "visible_date": "2022-03-30",
                "report_period": "2021-12-31",
                "aviation_service_revenue_share": "0.1",
                "airport_commercial_revenue_share": "0.0",
                "airport_operator_revenue_share": "0.1",
                "non_airport_revenue_share": "0.9",
                "approved_airport_business_tag": "non_airport_or_needs_review",
                "review_status": "needs_review_or_not_core",
                "pit_usable": "true",
            },
        ],
    )

    output = build_airport_business_purity_panel(panel, evidence, tmp_path / "out")

    rows = _read_rows(output)
    assert [row["code"] for row in rows] == ["600009.XSHG"]
    assert rows[0]["business_purity_gate"] == "passed"

    removed = _read_rows(tmp_path / "out" / "removed_by_business_purity_gate.csv")
    assert removed[0]["code"] == "000001.XSHE"
    assert removed[0]["business_purity_gate"] == "failed_non_airport_contamination"


def test_airport_business_purity_panel_reports_visible_failed_evidence(tmp_path: Path) -> None:
    panel = tmp_path / "panel.csv"
    evidence = tmp_path / "evidence.csv"
    _write_rows(
        panel,
        ["trade_date", "code", "future_return"],
        [{"trade_date": "2022-04-01", "code": "600515.XSHG", "future_return": "0.1"}],
    )
    _write_rows(
        evidence,
        [
            "code",
            "visible_date",
            "report_period",
            "aviation_service_revenue_share",
            "airport_commercial_revenue_share",
            "airport_operator_revenue_share",
            "non_airport_revenue_share",
            "approved_airport_business_tag",
            "review_status",
            "pit_usable",
        ],
        [
            {
                "code": "600515.XSHG",
                "visible_date": "2022-03-30",
                "report_period": "2021-12-31",
                "aviation_service_revenue_share": "0.2",
                "airport_commercial_revenue_share": "0.2",
                "airport_operator_revenue_share": "0.4",
                "non_airport_revenue_share": "0.6",
                "approved_airport_business_tag": "non_airport_or_needs_review",
                "review_status": "eastmoney_segment_needs_spot_check",
                "pit_usable": "false",
            },
        ],
    )

    build_airport_business_purity_panel(panel, evidence, tmp_path / "out")

    removed = _read_rows(tmp_path / "out" / "removed_by_business_purity_gate.csv")
    assert removed[0]["business_purity_gate"] == "failed_non_airport_contamination"
    assert removed[0]["airport_operator_revenue_share"] == "0.4"


def test_collect_eastmoney_airport_segments_uses_injected_fetcher(tmp_path: Path, monkeypatch) -> None:
    panel = tmp_path / "panel.csv"
    disclosure = tmp_path / "disclosure.csv"
    _write_rows(panel, ["trade_date", "code"], [{"trade_date": "2022-04-01", "code": "600009.XSHG"}])
    _write_rows(
        disclosure,
        ["code", "report_period", "notice_date"],
        [{"code": "600009.XSHG", "report_period": "2021-12-31", "notice_date": "2022-03-30"}],
    )

    from v5 import airport_transport_operating_evidence_runner as runner

    monkeypatch.setattr(
        runner,
        "_fetch_eastmoney_segment_records",
        lambda code, timeout: [
            {
                "REPORT_DATE": "2021-12-31",
                "MAINOP_TYPE": "2",
                "ITEM_NAME": "航空性服务",
                "MAIN_BUSINESS_INCOME": "70",
                "MBI_RATIO": "70",
            },
            {
                "REPORT_DATE": "2021-12-31",
                "MAINOP_TYPE": "2",
                "ITEM_NAME": "商业租赁",
                "MAIN_BUSINESS_INCOME": "20",
                "MBI_RATIO": "20",
            },
        ],
    )

    evidence = collect_eastmoney_airport_segment_evidence(panel, disclosure, tmp_path / "out", sleep_seconds=0)

    rows = _read_rows(evidence)
    assert rows[0]["approved_airport_business_tag"] == "core_airport_operator"
    assert rows[0]["pit_usable"] == "true"


def test_collect_eastmoney_airport_operating_announcements_uses_injected_fetcher(tmp_path: Path, monkeypatch) -> None:
    panel = tmp_path / "panel.csv"
    _write_rows(panel, ["trade_date", "code", "name"], [{"trade_date": "2022-04-01", "code": "600009.XSHG", "name": "Shanghai Airport"}])

    from v5 import airport_transport_operating_evidence_runner as runner

    monkeypatch.setattr(
        runner,
        "_fetch_eastmoney_announcement_records",
        lambda code, begin_date, end_date, timeout_seconds: [
            {
                "title": "600009:上海机场2021年11月运输生产情况简报",
                "notice_date": "2021-12-17 00:00:00",
                "art_code": "AN202112161534933974",
            },
            {
                "title": "600009:上海机场关于召开股东大会的通知",
                "notice_date": "2021-12-01 00:00:00",
                "art_code": "ignored",
            },
            {
                "title": "深圳机场:关于2026年4月生产经营快报的自愿性信息披露公告",
                "notice_date": "2026-05-12 00:00:00",
                "art_code": "AN202605111",
            },
            {
                "title": "白云机场:广州白云国际机场股份有限公司2024年生2月产经营数据快报",
                "notice_date": "2024-03-06 00:00:00",
                "art_code": "AN202403061",
            },
        ],
    )

    output = collect_eastmoney_airport_operating_announcements(panel, tmp_path / "out", sleep_seconds=0)

    rows = _read_rows(output)
    assert len(rows) == 3
    assert rows[0]["code"] == "600009.XSHG"
    assert rows[0]["visible_date"] == "2021-12-17"
    assert rows[0]["report_month"] == "2021-11"
    assert rows[0]["pit_usable"] == "true"
    assert rows[0]["review_status"] == "announcement_index_only_pdf_value_extraction_required"
    assert rows[1]["report_month"] == "2024-02"
    assert rows[2]["report_month"] == "2026-04"


def test_extract_airport_operating_state_values_parses_field_rows(tmp_path: Path, monkeypatch) -> None:
    index = tmp_path / "index.csv"
    _write_rows(
        index,
        ["code", "company_name", "report_month", "visible_date", "title", "art_code", "source_url"],
        [
            {
                "code": "000089.XSHE",
                "company_name": "Shenzhen Airport",
                "report_month": "2020-12",
                "visible_date": "2021-01-09",
                "title": "深圳机场生产经营快报",
                "art_code": "AN1",
                "source_url": "https://example.com/ann",
            }
        ],
    )

    from v5 import airport_transport_operating_evidence_runner as runner

    monkeypatch.setattr(
        runner,
        "_fetch_eastmoney_announcement_content",
        lambda art_code, timeout_seconds: {
            "notice_title": "深圳机场:关于2020年12月份生产经营快报的自愿性信息披露公告",
            "attach_url_web": "https://example.com/a.pdf",
            "page_size": 1,
            "notice_content": """
项目 本月实际 同比增长 本年累计 同比增长
旅客吞吐量（万人次） 383.13 -15.76% 3,791.61 -28.37%
货邮吞吐量（万吨） 14.34 17.39% 139.87 8.99%
航班起降架次（万架次） 3.15 -2.81% 32.03 -13.46%
""",
        },
    )

    output = extract_airport_operating_state_values(index, tmp_path / "out", sleep_seconds=0)

    rows = _read_rows(output)
    assert rows[0]["passenger_throughput"] == "383.13"
    assert rows[0]["passenger_unit"] == "万人次"
    assert rows[0]["cargo_throughput"] == "14.34"
    assert rows[0]["aircraft_movements"] == "3.15"
    assert rows[0]["extraction_status"] == "complete_candidate"
    assert rows[0]["pit_usable"] == "false"


def test_extract_airport_operating_state_values_parses_total_row_table(tmp_path: Path, monkeypatch) -> None:
    index = tmp_path / "index.csv"
    _write_rows(
        index,
        ["code", "company_name", "report_month", "visible_date", "title", "art_code", "source_url"],
        [{"code": "600009.XSHG", "company_name": "Shanghai Airport", "report_month": "2020-12", "visible_date": "2021-01-16", "title": "上海机场简报", "art_code": "AN2", "source_url": ""}],
    )

    from v5 import airport_transport_operating_evidence_runner as runner

    monkeypatch.setattr(
        runner,
        "_fetch_eastmoney_announcement_content",
        lambda art_code, timeout_seconds: {
            "notice_title": "上海国际机场股份有限公司2020年12月运输生产情况简报",
            "notice_content": """
项目 飞机起降架次（架次） 旅客吞吐量（万人次） 货邮吞吐量（万吨）
本月实际 同比增长 本月实际 同比增长 本月实际 同比增长
总计 24,649 -41.51% 192.51 -67.93% 35.78 7.16%
""",
        },
    )

    output = extract_airport_operating_state_values(index, tmp_path / "out", sleep_seconds=0)

    rows = _read_rows(output)
    assert rows[0]["aircraft_movements"] == "24649"
    assert rows[0]["passenger_throughput"] == "192.51"
    assert rows[0]["cargo_throughput"] == "35.78"
    assert rows[0]["aircraft_unit"] == "架次"


def test_cache_airport_operating_announcement_contents_skips_cached_rows(tmp_path: Path, monkeypatch) -> None:
    index = tmp_path / "index.csv"
    _write_rows(
        index,
        ["code", "company_name", "report_month", "visible_date", "title", "art_code", "source_url"],
        [
            {
                "code": "600009.XSHG",
                "company_name": "Shanghai Airport",
                "report_month": "2021-01",
                "visible_date": "2021-02-10",
                "title": "monthly operating briefing",
                "art_code": "AN_CACHE_1",
                "source_url": "https://example.com/ann",
            }
        ],
    )

    from v5 import airport_transport_operating_evidence_runner as runner

    calls = []

    def fake_fetch(art_code: str, timeout_seconds: float) -> dict[str, str]:
        calls.append(art_code)
        return {"notice_title": "cached title", "notice_content": "content"}

    monkeypatch.setattr(runner, "_fetch_eastmoney_announcement_content", fake_fetch)

    cache_airport_operating_announcement_contents(index, tmp_path / "cache", sleep_seconds=0)
    cache_airport_operating_announcement_contents(index, tmp_path / "cache", sleep_seconds=0)

    assert calls == ["AN_CACHE_1"]
    assert (tmp_path / "cache" / "AN_CACHE_1.json").exists()


def test_extract_airport_operating_state_values_prefers_content_cache(tmp_path: Path, monkeypatch) -> None:
    index = tmp_path / "index.csv"
    _write_rows(
        index,
        ["code", "company_name", "report_month", "visible_date", "title", "art_code", "source_url"],
        [
            {
                "code": "600009.XSHG",
                "company_name": "Shanghai Airport",
                "report_month": "2021-01",
                "visible_date": "2021-02-10",
                "title": "monthly operating briefing",
                "art_code": "AN_CACHE_2",
                "source_url": "https://example.com/ann",
            }
        ],
    )

    from v5 import airport_transport_operating_evidence_runner as runner

    monkeypatch.setattr(
        runner,
        "_fetch_eastmoney_announcement_content",
        lambda art_code, timeout_seconds: (_ for _ in ()).throw(AssertionError("live fetch should not be called")),
    )
    cache_dir = tmp_path / "cache"
    runner.write_json_file(
        cache_dir / "AN_CACHE_2.json",
        {
            "art_code": "AN_CACHE_2",
            "content": {
                "notice_title": "cached operating title",
                "notice_content": "no structured fields in this fixture",
            },
        },
    )

    output = extract_airport_operating_state_values(index, tmp_path / "out", sleep_seconds=0, content_cache_dir=cache_dir)

    rows = _read_rows(output)
    assert rows[0]["source_title"] == "cached operating title"
    assert rows[0]["extraction_status"] == "partial_candidate_needs_review"


def _write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))

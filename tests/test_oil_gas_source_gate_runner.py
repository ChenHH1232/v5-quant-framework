from __future__ import annotations

from pathlib import Path

from v5.io_utils import read_csv_rows, write_csv_rows
from v5.oil_gas_source_gate_runner import (
    CORE_V58D_STATE_METRICS,
    STATE_FIELDS,
    audit_oil_gas_source_gate,
    import_oil_gas_nbs_price_release_from_html,
    merge_oil_gas_state_sources,
    write_oil_gas_official_source_register,
    write_oil_gas_official_state_import_template,
)


def test_oil_gas_official_state_template_is_blocked_until_reviewed(tmp_path: Path) -> None:
    panel = _write_panel(tmp_path)
    template = write_oil_gas_official_state_import_template(tmp_path / "gate", start_year=2025, end_year=2025)

    result = audit_oil_gas_source_gate(template, panel_path=panel, out_dir=tmp_path / "audit")

    assert result.status == "source_repair_blocked"
    assert result.core_ready is False
    rows = read_csv_rows(template)
    assert rows
    assert {row["pit_usable"] for row in rows} == {"false"}


def test_oil_gas_source_register_records_official_candidates(tmp_path: Path) -> None:
    register = write_oil_gas_official_source_register(tmp_path / "gate")
    rows = read_csv_rows(register)

    assert {row["metric"] for row in rows} >= {"crude_oil_price_state", "bitumen_price_state", "gas_liquid_price_state"}
    assert all(row["anti_crawler_policy"] for row in rows)


def test_oil_gas_core_sources_can_open_research_review_without_promotion(tmp_path: Path) -> None:
    panel = _write_panel(tmp_path)
    state_csv = tmp_path / "official_core.csv"
    rows = []
    for metric in CORE_V58D_STATE_METRICS:
        rows.append(_state_row(metric, "2021-06-30", "10"))
    write_csv_rows(state_csv, STATE_FIELDS, rows)

    result = audit_oil_gas_source_gate(state_csv, panel_path=panel, out_dir=tmp_path / "audit")

    assert result.status == "core_state_ready_needs_promotion_sources"
    assert result.core_ready is True
    assert result.promotion_ready is False


def test_merge_oil_gas_state_sources_writes_formal_candidate(tmp_path: Path) -> None:
    panel = _write_panel(tmp_path)
    state_csv = tmp_path / "official_core.csv"
    rows = [_state_row(metric, "2021-06-30", "10") for metric in CORE_V58D_STATE_METRICS]
    write_csv_rows(state_csv, STATE_FIELDS, rows)

    merged = merge_oil_gas_state_sources(tmp_path / "merged", state_csv, panel_path=panel)

    assert merged.exists()
    assert read_csv_rows(merged)[0]["review_status"] == "exchange_official_reviewed"


def test_import_oil_gas_nbs_price_release_from_html_extracts_reviewed_rows(tmp_path: Path) -> None:
    html = """
    <html><head>
      <meta name="ArticleTitle" content="2026\u5e746\u6708\u4e2d\u65ec\u6d41\u901a\u9886\u57df\u91cd\u8981\u751f\u4ea7\u8d44\u6599\u5e02\u573a\u4ef7\u683c\u53d8\u52a8\u60c5\u51b5">
      <meta name="PubDate" content="2026/06/24 09:30">
    </head><body><table>
      <tr><td>\u6db2\u5316\u5929\u7136\u6c14\uff08LNG\uff09</td><td>\u5428</td><td>3925.1</td><td>1</td><td>0.1</td></tr>
      <tr><td>\u6db2\u5316\u77f3\u6cb9\u6c14\uff08LPG\uff09</td><td>\u5428</td><td>4288.8</td><td>1</td><td>0.1</td></tr>
      <tr><td>\u6db2\u5316\u77f3\u6cb9\u6c14\uff08LPG\uff09</td><td>\u5428</td><td>4288.8</td><td>1</td><td>0.1</td></tr>
      <tr><td>\u6c7d\u6cb9\uff0895# \u56fdVI\uff09</td><td>\u5428</td><td>9100.2</td><td>1</td><td>0.1</td></tr>
      <tr><td>\u67f4\u6cb9\uff080# \u56fdVI\uff09</td><td>\u5428</td><td>7200.3</td><td>1</td><td>0.1</td></tr>
    </table></body></html>
    """

    out = import_oil_gas_nbs_price_release_from_html(html, "https://www.stats.gov.cn/test.html", tmp_path)
    rows = read_csv_rows(out)

    assert len(rows) == 4
    assert {row["review_status"] for row in rows} == {"nbs_official_reviewed"}
    assert {row["metric"] for row in rows} >= {"gas_liquid_price_state", "domestic_gas_price_state", "refined_product_price_state"}
    assert {row["state_date"] for row in rows} == {"2026-06-20"}


def _write_panel(tmp_path: Path) -> Path:
    panel = tmp_path / "panel.csv"
    write_csv_rows(
        panel,
        ["trade_date", "code", "future_return"],
        [
            {"trade_date": "2021-07-01", "code": "600028.XSHG", "future_return": "0.01"},
            {"trade_date": "2021-10-08", "code": "600028.XSHG", "future_return": "0.01"},
        ],
    )
    return panel


def _state_row(metric: str, visible_date: str, value: str) -> dict[str, str]:
    return {
        "visible_date": visible_date,
        "state_date": "2021-06-29",
        "state_scope": "official_reviewed",
        "sub_industry": "oil_gas",
        "metric": metric,
        "value": value,
        "unit": "index",
        "source_name": "unit-test official source",
        "source_url": "https://example.com/official",
        "source_publication_date": visible_date,
        "pit_usable": "true",
        "review_status": "exchange_official_reviewed",
        "notes": "unit test reviewed row",
    }

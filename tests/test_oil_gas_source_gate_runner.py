from __future__ import annotations

from pathlib import Path

from v5.io_utils import read_csv_rows, write_csv_rows
from v5.oil_gas_source_gate_runner import (
    CORE_V58D_STATE_METRICS,
    STATE_FIELDS,
    audit_oil_gas_source_gate,
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

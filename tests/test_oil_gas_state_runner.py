from __future__ import annotations

from pathlib import Path

from v5.io_utils import write_csv_rows
from v5.oil_gas_state_runner import (
    REQUIRED_RESEARCH_METRICS,
    build_oil_gas_research_panel,
    latest_visible_state_values,
    validate_oil_gas_external_state,
)


def test_validate_oil_gas_external_state_accepts_required_proxy_metrics(tmp_path: Path) -> None:
    rows = [
        {
            "visible_date": "2021-06-30",
            "state_date": "2021-06-29",
            "state_scope": "china_futures_market",
            "sub_industry": "test",
            "metric": metric,
            "value": "1.0",
            "unit": "proxy",
            "source_name": "unit-test",
            "source_url": "https://example.com",
            "source_publication_date": "2021-06-30",
            "pit_usable": "true",
            "review_status": "preliminary_proxy",
            "notes": "",
        }
        for metric in REQUIRED_RESEARCH_METRICS
    ]
    path = tmp_path / "state.csv"
    write_csv_rows(path, rows[0].keys(), rows)

    result = validate_oil_gas_external_state(path)

    assert result["status"] == "preliminary_research_validation_ready"
    assert result["missing_usable_required_metrics"] == []


def test_latest_visible_state_values_uses_only_visible_rows(tmp_path: Path) -> None:
    path = tmp_path / "state.csv"
    rows = [
        {
            "visible_date": "2021-06-30",
            "state_date": "2021-06-29",
            "state_scope": "market",
            "sub_industry": "oil",
            "metric": "crude_oil_price_state",
            "value": "10",
            "unit": "proxy",
            "source_name": "unit-test",
            "source_url": "",
            "source_publication_date": "2021-06-30",
            "pit_usable": "true",
            "review_status": "preliminary_proxy",
            "notes": "",
        },
        {
            "visible_date": "2021-07-02",
            "state_date": "2021-07-01",
            "state_scope": "market",
            "sub_industry": "oil",
            "metric": "crude_oil_price_state",
            "value": "20",
            "unit": "proxy",
            "source_name": "unit-test",
            "source_url": "",
            "source_publication_date": "2021-07-02",
            "pit_usable": "true",
            "review_status": "preliminary_proxy",
            "notes": "",
        },
    ]
    write_csv_rows(path, rows[0].keys(), rows)

    result = latest_visible_state_values(path, ["2021-07-01", "2021-07-03"])

    assert result["2021-07-01"]["crude_oil_price_state"] == "10"
    assert result["2021-07-03"]["crude_oil_price_state"] == "20"


def test_build_oil_gas_research_panel_adds_state_and_exposure_proxy(tmp_path: Path) -> None:
    panel = tmp_path / "panel.csv"
    panel_rows = [
        {
            "trade_date": "2021-07-01",
            "code": "600028.XSHG",
            "sub_industry": "fuel_refining",
            "future_return": "0.01",
            "total_return": "0.01",
        }
    ]
    write_csv_rows(panel, panel_rows[0].keys(), panel_rows)
    state = tmp_path / "state.csv"
    state_rows = [
        {
            "visible_date": "2021-06-30",
            "state_date": "2021-06-29",
            "state_scope": "market",
            "sub_industry": "oil",
            "metric": "crude_oil_price_state",
            "value": "10",
            "unit": "proxy",
            "source_name": "unit-test",
            "source_url": "",
            "source_publication_date": "2021-06-30",
            "pit_usable": "true",
            "review_status": "preliminary_proxy",
            "notes": "",
        }
    ]
    write_csv_rows(state, state_rows[0].keys(), state_rows)

    result = build_oil_gas_research_panel(panel, state, tmp_path / "out")

    assert result.status == "research_validation_ready"
    text = result.panel_path.read_text(encoding="utf-8")
    assert "crude_oil_price_state" in text
    assert "oil_gas_business_exposure_score" in text

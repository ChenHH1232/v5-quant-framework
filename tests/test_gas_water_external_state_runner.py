from __future__ import annotations

import csv
from pathlib import Path

from v5.gas_water_external_state_runner import (
    build_gas_water_external_state_panel,
    build_gas_water_state_enriched_panel,
    run_gas_water_state_bucket_validation,
)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_gas_water_state_pipeline_opens_state_validation(tmp_path: Path) -> None:
    panel = _write_csv(
        tmp_path / "panel.csv",
        [
            _panel_row("2026-01-05", "000001.XSHE", 1.0, 4.0, 10.0, 0.30, 0.10),
            _panel_row("2026-01-05", "000002.XSHE", 2.0, 3.0, 8.0, 0.20, 0.20),
            _panel_row("2026-04-01", "000001.XSHE", 1.1, 4.2, 12.0, 0.35, -0.05),
            _panel_row("2026-04-01", "000002.XSHE", 2.2, 2.8, 9.0, 0.22, 0.03),
        ],
    )
    benchmark_rows = [{"date": f"2025-12-{day:02d}", "code": "same_pool", "close": 100 + day} for day in range(1, 32)]
    benchmark_rows.extend({"date": f"2026-01-{day:02d}", "code": "same_pool", "close": 130 + day} for day in range(1, 32))
    benchmark_rows.extend({"date": f"2026-03-{day:02d}", "code": "same_pool", "close": 150 + day} for day in range(1, 32))
    benchmark = _write_csv(tmp_path / "benchmark.csv", benchmark_rows)

    state = build_gas_water_external_state_panel(panel, benchmark, tmp_path / "state")
    assert state.status == "state_validation_ready"
    assert state.pit_usable_count > 0

    enriched = build_gas_water_state_enriched_panel(panel, state.panel_path, tmp_path / "enriched", "test_strategy")
    assert enriched.status == "state_validation_ready"
    assert enriched.state_enriched_count == 4

    validation = run_gas_water_state_bucket_validation(
        enriched.panel_path,
        tmp_path / "validation",
        "test_strategy",
        "sector_receivables_to_revenue_median",
        selection_count=1,
        min_history=1,
    )
    assert validation.status == "state_bucket_validation_completed_not_acceptance"
    assert validation.summary_path.exists()


def _panel_row(
    trade_date: str,
    code: str,
    pb: float,
    dividend: float,
    interest_coverage: float,
    receivables_to_revenue: float,
    future_return: float,
) -> dict[str, object]:
    return {
        "trade_date": trade_date,
        "code": code,
        "future_return": future_return,
        "total_return": future_return,
        "factor_visible_date": trade_date,
        "gas_water_visible_date": trade_date,
        "gas_water_financial_evidence_visible_date": trade_date,
        "low_price_to_book_safe": pb,
        "dividend_yield": dividend,
        "interest_coverage_safe": interest_coverage,
        "debt_pressure_safe": 0.4,
        "capex_burden_safe": 0.5,
        "direct_receivables_to_revenue": receivables_to_revenue,
        "direct_receivables_to_assets": 0.1,
        "direct_collection_cash_to_revenue": 1.0,
        "direct_interest_bearing_debt_to_assets": 0.3,
        "direct_net_debt_to_assets": 0.2,
    }

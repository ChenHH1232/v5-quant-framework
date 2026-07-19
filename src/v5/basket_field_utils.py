from __future__ import annotations

from typing import Any

from v5.math_utils import to_float


def enrich_basket_panel_row(row: dict[str, Any], sector_id: str) -> dict[str, Any]:
    """Add comparable basket-level fields while preserving raw source values."""
    enriched = dict(row)
    dividend = _normalized_yield(enriched.get("dividend_yield"))
    if dividend is not None:
        enriched["dividend_yield_decimal"] = dividend
        enriched["basket_dividend_yield_unit_policy"] = "if_raw_value_gt_1_divide_by_100_else_keep"

    ocf_yield = to_float(enriched.get("operating_cash_flow_yield"))
    if ocf_yield is not None:
        enriched["cash_generation_yield"] = ocf_yield
        enriched["cash_generation_yield_source"] = "operating_cash_flow_yield"
    elif sector_id in {"bank", "insurance"} and dividend is not None:
        enriched["cash_generation_yield"] = dividend
        enriched["cash_generation_yield_source"] = "financial_sector_dividend_proxy"
    return enriched


def _normalized_yield(value: Any) -> float | None:
    raw = to_float(value)
    if raw is None or raw < 0:
        return None
    return raw / 100.0 if raw > 1.0 else raw

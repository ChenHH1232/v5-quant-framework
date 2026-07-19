from __future__ import annotations

from collections import defaultdict
from typing import Any

from v5.scoring import score_weighted_composite


def score_basket_date_rows(raw_spec: dict[str, Any], date_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    scoring = raw_spec.get("signals", {}).get("scoring", {})
    if scoring.get("normalization_scope") != "sector_adaptive":
        return score_weighted_composite(raw_spec, date_rows)

    by_sector: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in date_rows:
        by_sector[str(row.get("sector_id") or "")].append(row)

    scored_rows: list[dict[str, Any]] = []
    used_factors: list[str] = []
    for sector_id, sector_rows in sorted(by_sector.items()):
        sector_spec = _sector_spec(raw_spec, sector_id)
        sector_scored, sector_used = score_weighted_composite(sector_spec, sector_rows)
        for row in sector_scored:
            enriched = dict(row)
            enriched["basket_scoring_scope"] = "sector_adaptive"
            enriched["basket_scoring_sector"] = sector_id
            scored_rows.append(enriched)
        for factor in sector_used:
            if factor not in used_factors:
                used_factors.append(factor)
    return scored_rows, used_factors


def _sector_spec(raw_spec: dict[str, Any], sector_id: str) -> dict[str, Any]:
    base_signals = raw_spec.get("signals", {})
    base_scoring = base_signals.get("scoring", {})
    overrides = base_scoring.get("sector_scoring_overrides", {})
    override = overrides.get(sector_id) or overrides.get("_default") or {}

    scoring = {
        key: value
        for key, value in base_scoring.items()
        if key not in {"sector_scoring_overrides", "default_scoring"}
    }
    scoring["normalization_scope"] = "rebalance_cross_section"
    for key, value in override.items():
        if key != "factors":
            scoring[key] = value

    return {
        "signals": {
            "factors": override.get("factors") or base_signals.get("factors", []),
            "scoring": scoring,
        }
    }

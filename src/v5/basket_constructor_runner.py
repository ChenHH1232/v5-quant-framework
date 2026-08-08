from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.basket_field_utils import enrich_basket_panel_row
from v5.basket_scoring import score_basket_date_rows
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import fmt_float, to_float
from v5.startup_preload import (
    build_startup_date_model,
    first_field_available_dates,
    first_required_candidate_date,
    first_required_field_pass_date,
    load_trading_days_from_price_files,
)


DEFAULT_CONFIG = Path("config/dividend_low_vol_fcf_basket_v56.json")
DEFAULT_OUT_DIR = Path("validation_formal_v56_basket_constructor")


@dataclass(frozen=True)
class BasketConstructionResult:
    output_dir: Path
    signals_path: Path
    summary_path: Path
    report_path: Path
    signal_count: int
    holding_count: int


def construct_dividend_low_vol_fcf_basket(
    config_path: Path = DEFAULT_CONFIG,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> BasketConstructionResult:
    config = _read_json(config_path)
    sectors = config.get("sectors", [])
    if not sectors:
        raise ValueError("basket config must include sectors")
    all_rows = _load_sector_rows(sectors)
    factors = config.get("signals", {}).get("factors", [])
    scoring = config.get("signals", {}).get("scoring", {})
    portfolio = config.get("portfolio", {})
    start_date = str(portfolio.get("start_date") or "")
    end_date = str(portfolio.get("end_date") or "")
    required_fields = [str(item) for item in portfolio.get("required_fields", [])]
    calendar_policy = str(portfolio.get("rebalance_calendar_policy") or "union")
    price_files = [Path(str(sector.get("price_csv") or "")) for sector in sectors if sector.get("price_csv")]
    trading_days = load_trading_days_from_price_files(price_files) if price_files else sorted({str(row.get("trade_date") or "")[:10] for row in all_rows if row.get("trade_date")})

    raw_spec = {"signals": {"factors": factors, "scoring": scoring}}
    target_count = int(portfolio.get("target_count", 30))
    sector_cap = float(portfolio.get("sector_weight_cap", 0.3))
    single_stock_cap = float(portfolio.get("single_stock_weight_cap", 0.08))
    all_rows = _filter_rows(all_rows, start_date, end_date, required_fields)
    rebalance_dates = _rebalance_dates(all_rows, sectors, calendar_policy)
    startup_model = build_startup_date_model(
        deployment_date=start_date,
        trading_days=trading_days,
        regular_rebalance_dates=rebalance_dates,
    ) if start_date else None

    signal_rows: list[dict[str, Any]] = []
    for trade_date in rebalance_dates:
        date_rows = [row for row in all_rows if str(row.get("trade_date") or "") == trade_date]
        scored, used_factors = score_basket_date_rows(raw_spec, date_rows)
        scored.sort(key=lambda item: to_float(item.get("score")) or -999999.0, reverse=True)
        selected = _select_with_caps(scored, target_count, sector_cap, single_stock_cap)
        selected_count = len(selected)
        for rank, item in enumerate(selected, start=1):
            signal_rows.append(
                {
                    "trade_date": trade_date,
                    "code": item.get("code", ""),
                    "sector_id": item.get("sector_id", ""),
                    "strategy_id": item.get("source_strategy_id", ""),
                    "selected_rank": rank,
                    "selected_count": selected_count,
                    "target_weight": fmt_float(item.get("target_weight")),
                    "score": fmt_float(item.get("score")),
                    "used_factors": ";".join(used_factors),
                    "basket_scoring_scope": item.get("basket_scoring_scope", ""),
                    "basket_scoring_sector": item.get("basket_scoring_sector", ""),
                    "dividend_yield": item.get("dividend_yield", ""),
                    "dividend_yield_decimal": item.get("dividend_yield_decimal", ""),
                    "cash_generation_yield": item.get("cash_generation_yield", ""),
                    "cash_generation_yield_source": item.get("cash_generation_yield_source", ""),
                    "free_cash_flow_yield": item.get("free_cash_flow_yield", ""),
                    "operating_cash_flow_yield": item.get("operating_cash_flow_yield", ""),
                    "volatility_120d": item.get("volatility_120d", ""),
                    "low_vol_score": item.get("low_vol_score", ""),
                    "business_purity_gate": item.get("business_purity_gate", ""),
                    "rebalance_event_type": "initial_rebalance_event" if startup_model and startup_model.warmup_available and trade_date == startup_model.initial_rebalance_event else "regular_rebalance",
                }
            )

    out_dir.mkdir(parents=True, exist_ok=True)
    signals_path = out_dir / "basket_rebalance_signals.csv"
    summary_path = out_dir / "basket_construction_summary.json"
    report_path = out_dir / "basket_construction_report.md"
    write_csv_rows(
        signals_path,
        [
            "trade_date",
            "code",
            "sector_id",
            "strategy_id",
            "selected_rank",
            "selected_count",
            "target_weight",
            "score",
            "used_factors",
            "basket_scoring_scope",
            "basket_scoring_sector",
            "dividend_yield",
            "dividend_yield_decimal",
            "cash_generation_yield",
            "cash_generation_yield_source",
            "free_cash_flow_yield",
            "operating_cash_flow_yield",
            "volatility_120d",
            "low_vol_score",
            "business_purity_gate",
            "rebalance_event_type",
        ],
        signal_rows,
    )
    summary = _summary(config, signal_rows, signals_path, report_path, all_rows, required_fields, startup_model)
    write_json_file(summary_path, summary)
    report_path.write_text(_report(summary, signal_rows), encoding="utf-8")
    return BasketConstructionResult(out_dir, signals_path, summary_path, report_path, len(rebalance_dates), len(signal_rows))


def _load_sector_rows(sectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sector in sectors:
        panel_path = Path(str(sector.get("panel_csv") or ""))
        if not panel_path.exists():
            raise FileNotFoundError(f"basket sector panel not found: {panel_path}")
        sector_id = str(sector.get("sector_id") or "")
        strategy_id = str(sector.get("strategy_id") or "")
        for row in read_csv_rows(panel_path):
            enriched = enrich_basket_panel_row(row, sector_id)
            enriched["sector_id"] = sector_id
            enriched["source_strategy_id"] = strategy_id
            rows.append(enriched)
    return rows


def _filter_rows(rows: list[dict[str, Any]], start_date: str, end_date: str, required_fields: list[str]) -> list[dict[str, Any]]:
    filtered = []
    for row in rows:
        trade_date = str(row.get("trade_date") or "")[:10]
        if start_date and trade_date < start_date:
            continue
        if end_date and trade_date > end_date:
            continue
        if any(row.get(field) in (None, "") for field in required_fields):
            continue
        filtered.append(row)
    return filtered


def _rebalance_dates(rows: list[dict[str, Any]], sectors: list[dict[str, Any]], calendar_policy: str) -> list[str]:
    dates_by_sector: dict[str, set[str]] = {}
    for row in rows:
        sector_id = str(row.get("sector_id") or "")
        dates_by_sector.setdefault(sector_id, set()).add(str(row.get("trade_date") or "")[:10])
    if calendar_policy == "union":
        return sorted({day for dates in dates_by_sector.values() for day in dates if day})
    if calendar_policy == "common_dates_only":
        required_sector_ids = [str(sector.get("sector_id") or "") for sector in sectors]
        date_sets = [dates_by_sector.get(sector_id, set()) for sector_id in required_sector_ids]
        if not date_sets:
            return []
        common = set(date_sets[0])
        for dates in date_sets[1:]:
            common &= dates
        return sorted(common)
    raise ValueError("rebalance_calendar_policy must be union or common_dates_only")


def _select_with_caps(scored: list[dict[str, Any]], target_count: int, sector_cap: float, single_stock_cap: float) -> list[dict[str, Any]]:
    if target_count <= 0:
        return []
    base_weight = min(single_stock_cap, 1.0 / target_count)
    sector_weights: dict[str, float] = {}
    selected: list[dict[str, Any]] = []
    for row in scored:
        sector_id = str(row.get("sector_id") or "")
        if sector_weights.get(sector_id, 0.0) + base_weight > sector_cap + 1e-12:
            continue
        item = dict(row)
        item["target_weight"] = base_weight
        selected.append(item)
        sector_weights[sector_id] = sector_weights.get(sector_id, 0.0) + base_weight
        if len(selected) >= target_count:
            break
    return selected


def _summary(
    config: dict[str, Any],
    signal_rows: list[dict[str, Any]],
    signals_path: Path,
    report_path: Path,
    filtered_rows: list[dict[str, Any]],
    required_fields: list[str],
    startup_model: Any,
) -> dict[str, Any]:
    sector_counts: dict[str, int] = {}
    for row in signal_rows:
        sector_id = str(row.get("sector_id") or "")
        sector_counts[sector_id] = sector_counts.get(sector_id, 0) + 1
    first_signal_date = min({str(row["trade_date"]) for row in signal_rows}) if signal_rows else ""
    startup = {}
    if startup_model is not None:
        field_dates = first_field_available_dates(filtered_rows, ["volatility_120d", "max_drawdown_120d", "low_vol_score", "dividend_yield"])
        startup = {
            "deployment_date": startup_model.deployment_date,
            "first_tradable_date": startup_model.first_tradable_date,
            "warmup_start_date": startup_model.warmup_start_date,
            "trade_start_date": startup_model.trade_start_date,
            "required_lookback_days": startup_model.required_lookback_days,
            "warmup_buffer_days": startup_model.warmup_buffer_days,
            "initial_rebalance_event": startup_model.initial_rebalance_event,
            "warmup_available": startup_model.warmup_available,
            "startup_ready": bool(startup_model.warmup_available and first_signal_date and first_signal_date == startup_model.initial_rebalance_event),
            "first_signal_date": first_signal_date,
            "required_fields_first_pass_date": first_required_field_pass_date(filtered_rows, required_fields),
            "required_fields_first_candidate_date": first_required_candidate_date(filtered_rows, required_fields),
            "factor_first_available_dates": field_dates,
            "startup_blocker": "" if first_signal_date == startup_model.initial_rebalance_event else "initial_rebalance_not_generated_required_fields_or_warmup_missing",
        }
    return {
        "schema_version": 1,
        "project": config.get("project", "v56_dividend_low_vol_fcf_basket"),
        "experiment_layer": config.get("experiment_layer", "research_pit_validation"),
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "signal_count": len({row["trade_date"] for row in signal_rows}),
        "holding_count": len(signal_rows),
        "sector_holding_counts": sector_counts,
        "signals_path": str(signals_path),
        "report_path": str(report_path),
        "startup_preload": startup,
        "pm_rule": "This is a basket-construction shadow signal file. It is not a backtest, platform replication or accepted strategy.",
    }


def _report(summary: dict[str, Any], signal_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Dividend Low-Vol Cash-Flow Basket Construction Report",
        "",
        f"Created at UTC: `{summary['created_at_utc']}`",
        "",
        "## PM Decision",
        "",
        "The first basket constructor generated shadow rebalance signals. This is not a performance result and not a strategy acceptance.",
        "",
        "## Summary",
        "",
        f"- Signal dates: `{summary['signal_count']}`",
        f"- Holdings across all signal dates: `{summary['holding_count']}`",
        "",
        "## Sector Holding Counts",
        "",
    ]
    for sector_id, count in sorted(summary["sector_holding_counts"].items()):
        lines.append(f"- `{sector_id}`: {count}")
    first_dates = sorted({str(row["trade_date"]) for row in signal_rows})[:3]
    lines.extend(["", "## First Signal Dates", ""])
    for day in first_dates:
        lines.append(f"- `{day}`")
    if summary.get("startup_preload"):
        startup = summary["startup_preload"]
        lines.extend(
            [
                "",
                "## Startup Preload",
                "",
                f"- `deployment_date`: `{startup.get('deployment_date')}`",
                f"- `first_tradable_date`: `{startup.get('first_tradable_date')}`",
                f"- `warmup_start_date`: `{startup.get('warmup_start_date')}`",
                f"- `initial_rebalance_event`: `{startup.get('initial_rebalance_event')}`",
                f"- `startup_ready`: `{startup.get('startup_ready')}`",
                f"- `startup_blocker`: `{startup.get('startup_blocker')}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Hard Rule",
            "",
            "Basket construction must be followed by formal validation, daily simulation, overfit audit, platform attribution and paper trading before acceptance.",
            "",
        ]
    )
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload

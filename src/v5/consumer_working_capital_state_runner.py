from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.credential_loader import load_joinquant_credentials
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import fmt_float, ratio, to_float
from v5.paths import DEFAULT_PROCESSED_DIR


DEFAULT_OUT_ROOT = DEFAULT_PROCESSED_DIR / "consumer_working_capital_state_v5a6"

DEFAULT_PANELS = {
    "food_beverage": DEFAULT_PROCESSED_DIR
    / "low_volatility_factors_v5a5"
    / "food_beverage"
    / "food_beverage_v5a5"
    / "panel_with_low_vol.csv",
    "consumer_staples_cashflow": DEFAULT_PROCESSED_DIR
    / "low_volatility_factors_v5a5"
    / "consumer_staples_cashflow"
    / "consumer_staples_cashflow_v5a5"
    / "panel_with_low_vol.csv",
    "pharma_medical_services": DEFAULT_PROCESSED_DIR
    / "low_volatility_factors_v5a5"
    / "pharma_medical_services"
    / "pharma_medical_services_v5a5"
    / "panel_with_low_vol.csv",
}

RAW_FIELDS = [
    "inventories",
    "account_receivable",
    "bill_receivable",
    "contract_assets",
    "contract_liability",
    "operating_revenue",
    "operating_cost",
    "total_current_assets",
    "total_current_liability",
]

ENRICHED_FIELDS = [
    "inventory",
    "account_receivable",
    "bill_receivable",
    "contract_assets",
    "contract_liability",
    "operating_revenue",
    "operating_cost",
    "gross_margin",
    "inventory_to_revenue",
    "receivables_to_revenue",
    "contract_asset_to_revenue",
    "contract_liability_to_revenue",
    "working_capital_pressure_to_revenue",
    "inventory_to_current_assets",
    "receivables_to_current_assets",
    "current_ratio",
    "sector_inventory_to_revenue_median",
    "sector_receivables_to_revenue_median",
    "sector_working_capital_pressure_to_revenue_median",
    "sector_current_ratio_median",
    "subindustry_inventory_to_revenue_median",
    "subindustry_receivables_to_revenue_median",
    "subindustry_working_capital_pressure_to_revenue_median",
    "subindustry_current_ratio_median",
    "high_inventory_pressure_flag",
    "high_receivables_pressure_flag",
    "high_working_capital_pressure_flag",
    "consumer_state_visible_date",
    "consumer_state_source",
]


@dataclass(frozen=True)
class ConsumerWorkingCapitalStateResult:
    panel_csv: Path
    raw_csv: Path
    summary_json: Path
    sector_id: str
    row_count: int
    status: str


def enrich_consumer_working_capital_state(
    sector_id: str,
    panel_csv: Path | None = None,
    out_root: Path = DEFAULT_OUT_ROOT,
    username_env: str = "JQDATA_USERNAME",
    password_env: str = "JQDATA_PASSWORD",
) -> ConsumerWorkingCapitalStateResult:
    panel_path = panel_csv or _default_panel(sector_id)
    rows = read_csv_rows(panel_path)
    jq = _load_authenticated_jqdata(username_env, password_env)
    fundamentals = _fetch_state_by_date(jq, rows)

    raw_rows: list[dict[str, Any]] = []
    enriched_rows: list[dict[str, str]] = []
    for row in rows:
        trade_date = str(row.get("trade_date") or "")[:10]
        code = str(row.get("code") or "")
        raw = fundamentals.get(trade_date, {}).get(code, {})
        raw_rows.append({"trade_date": trade_date, "code": code, **{key: raw.get(key, "") for key in RAW_FIELDS}})
        enriched = dict(row)
        enriched.update(_derive_fields(raw, trade_date))
        enriched_rows.append(enriched)

    _attach_group_state(enriched_rows)
    out_dir = out_root / sector_id
    out_dir.mkdir(parents=True, exist_ok=True)
    panel_out = out_dir / "panel_with_working_capital_state.csv"
    raw_out = out_dir / "working_capital_state_raw.csv"
    summary_out = out_dir / "working_capital_state_summary.json"
    write_csv_rows(panel_out, _merge_fieldnames(rows, ENRICHED_FIELDS), enriched_rows)
    write_csv_rows(raw_out, ["trade_date", "code", *RAW_FIELDS], raw_rows)
    coverage = _coverage(enriched_rows)
    status = "working_capital_state_enriched_needs_validation" if _core_coverage_passed(coverage) else "working_capital_state_needs_review"
    write_json_file(
        summary_out,
        {
            "dataset": f"{sector_id}_working_capital_state_v5a6",
            "sector_id": sector_id,
            "panel_csv": str(panel_path),
            "panel_with_working_capital_state": str(panel_out),
            "raw_csv": str(raw_out),
            "row_count": len(enriched_rows),
            "date_count": len({row.get("trade_date") for row in enriched_rows}),
            "code_count": len({row.get("code") for row in enriched_rows}),
            "coverage": coverage,
            "status": status,
            "pit_policy": "Uses jqdatasdk.get_fundamentals(date=trade_date) and carries existing factor_visible_date from the source panel.",
            "limitations": [
                "This repairs statement-derived inventory, receivables and working-capital pressure only.",
                "It does not prove brand moat, channel inventory, product mix or policy state.",
            ],
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return ConsumerWorkingCapitalStateResult(panel_out, raw_out, summary_out, sector_id, len(enriched_rows), status)


def _default_panel(sector_id: str) -> Path:
    if sector_id not in DEFAULT_PANELS:
        supported = ", ".join(sorted(DEFAULT_PANELS))
        raise ValueError(f"unsupported consumer state sector '{sector_id}'. Supported: {supported}")
    return DEFAULT_PANELS[sector_id]


def _load_authenticated_jqdata(username_env: str, password_env: str) -> Any:
    try:
        import jqdatasdk as jq
    except Exception as exc:  # pragma: no cover - optional dependency.
        raise RuntimeError("consumer working-capital state enrichment requires jqdatasdk") from exc

    username, password = load_joinquant_credentials(username_env, password_env)
    if username and password:
        jq.auth(username, password)
    if not jq.is_auth():
        raise RuntimeError("JoinQuant credentials are not available")
    return jq


def _fetch_state_by_date(jq: Any, rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, Any]]]:
    by_date: dict[str, set[str]] = {}
    for row in rows:
        trade_date = str(row.get("trade_date") or "")[:10]
        code = str(row.get("code") or "")
        if trade_date and code:
            by_date.setdefault(trade_date, set()).add(code)
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for trade_date, codes in sorted(by_date.items()):
        df = jq.get_fundamentals(
            jq.query(
                jq.valuation.code,
                jq.balance.inventories,
                jq.balance.account_receivable,
                jq.balance.bill_receivable,
                jq.balance.contract_assets,
                jq.balance.contract_liability,
                jq.income.operating_revenue,
                jq.income.operating_cost,
                jq.balance.total_current_assets,
                jq.balance.total_current_liability,
            ).filter(jq.valuation.code.in_(sorted(codes))),
            date=trade_date,
        )
        date_result: dict[str, dict[str, Any]] = {}
        if df is not None and not getattr(df, "empty", True):
            for raw in df.to_dict("records"):
                code = str(raw.get("code") or "")
                if code:
                    date_result[code] = raw
        result[trade_date] = date_result
    return result


def _derive_fields(raw: dict[str, Any], trade_date: str) -> dict[str, str]:
    inventory = to_float(raw.get("inventories"))
    account_receivable = to_float(raw.get("account_receivable"))
    bill_receivable = to_float(raw.get("bill_receivable"))
    contract_assets = to_float(raw.get("contract_assets"))
    contract_liability = to_float(raw.get("contract_liability"))
    revenue = to_float(raw.get("operating_revenue"))
    cost = to_float(raw.get("operating_cost"))
    current_assets = to_float(raw.get("total_current_assets"))
    current_liability = to_float(raw.get("total_current_liability"))
    receivables = (account_receivable or 0.0) + (bill_receivable or 0.0)
    working_pressure = (inventory or 0.0) + receivables + (contract_assets or 0.0) - (contract_liability or 0.0)
    gross_profit = (revenue - cost) if revenue is not None and cost is not None else None
    return {
        "inventory": fmt_float(inventory),
        "account_receivable": fmt_float(account_receivable),
        "bill_receivable": fmt_float(bill_receivable),
        "contract_assets": fmt_float(contract_assets),
        "contract_liability": fmt_float(contract_liability),
        "operating_revenue": fmt_float(revenue),
        "operating_cost": fmt_float(cost),
        "gross_margin": fmt_float(ratio(gross_profit, revenue)),
        "inventory_to_revenue": fmt_float(ratio(inventory, revenue)),
        "receivables_to_revenue": fmt_float(ratio(receivables, revenue)),
        "contract_asset_to_revenue": fmt_float(ratio(contract_assets, revenue)),
        "contract_liability_to_revenue": fmt_float(ratio(contract_liability, revenue)),
        "working_capital_pressure_to_revenue": fmt_float(ratio(working_pressure, revenue)),
        "inventory_to_current_assets": fmt_float(ratio(inventory, current_assets)),
        "receivables_to_current_assets": fmt_float(ratio(receivables, current_assets)),
        "current_ratio": fmt_float(ratio(current_assets, current_liability)),
        "consumer_state_visible_date": trade_date,
        "consumer_state_source": "jqdatasdk.get_fundamentals(date=trade_date)",
    }


def _attach_group_state(rows: list[dict[str, str]]) -> None:
    by_date: dict[str, list[dict[str, str]]] = {}
    by_sub: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        trade_date = str(row.get("trade_date") or "")[:10]
        sub = str(row.get("sub_industry") or "unknown")
        by_date.setdefault(trade_date, []).append(row)
        by_sub.setdefault((trade_date, sub), []).append(row)

    for row in rows:
        trade_date = str(row.get("trade_date") or "")[:10]
        sub = str(row.get("sub_industry") or "unknown")
        sector = _state_summary(by_date.get(trade_date, []))
        sub_state = _state_summary(by_sub.get((trade_date, sub), []))
        row.update(
            {
                "sector_inventory_to_revenue_median": sector["inventory_to_revenue_median"],
                "sector_receivables_to_revenue_median": sector["receivables_to_revenue_median"],
                "sector_working_capital_pressure_to_revenue_median": sector["working_capital_pressure_to_revenue_median"],
                "sector_current_ratio_median": sector["current_ratio_median"],
                "subindustry_inventory_to_revenue_median": sub_state["inventory_to_revenue_median"],
                "subindustry_receivables_to_revenue_median": sub_state["receivables_to_revenue_median"],
                "subindustry_working_capital_pressure_to_revenue_median": sub_state["working_capital_pressure_to_revenue_median"],
                "subindustry_current_ratio_median": sub_state["current_ratio_median"],
                "high_inventory_pressure_flag": "true" if (to_float(row.get("inventory_to_revenue")) or 0.0) > 0.5 else "false",
                "high_receivables_pressure_flag": "true" if (to_float(row.get("receivables_to_revenue")) or 0.0) > 0.5 else "false",
                "high_working_capital_pressure_flag": "true" if (to_float(row.get("working_capital_pressure_to_revenue")) or 0.0) > 1.0 else "false",
            }
        )


def _state_summary(rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        "inventory_to_revenue_median": fmt_float(_median_field(rows, "inventory_to_revenue")),
        "receivables_to_revenue_median": fmt_float(_median_field(rows, "receivables_to_revenue")),
        "working_capital_pressure_to_revenue_median": fmt_float(_median_field(rows, "working_capital_pressure_to_revenue")),
        "current_ratio_median": fmt_float(_median_field(rows, "current_ratio")),
    }


def _median_field(rows: list[dict[str, str]], field: str) -> float | None:
    values = sorted(value for value in (to_float(row.get(field)) for row in rows) if value is not None)
    if not values:
        return None
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2


def _coverage(rows: list[dict[str, str]]) -> dict[str, float]:
    total = len(rows)
    result: dict[str, float] = {}
    for field in [
        "inventory_to_revenue",
        "receivables_to_revenue",
        "working_capital_pressure_to_revenue",
        "current_ratio",
        "gross_margin",
    ]:
        result[field] = 0.0 if total == 0 else sum(1 for row in rows if row.get(field) not in ("", None)) / total
    return result


def _core_coverage_passed(coverage: dict[str, float]) -> bool:
    return (
        coverage.get("inventory_to_revenue", 0.0) >= 0.8
        and coverage.get("receivables_to_revenue", 0.0) >= 0.8
        and coverage.get("working_capital_pressure_to_revenue", 0.0) >= 0.8
    )


def _merge_fieldnames(rows: list[dict[str, str]], extra: list[str]) -> list[str]:
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    for key in extra:
        if key not in names:
            names.append(key)
    return names


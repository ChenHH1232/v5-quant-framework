from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.credential_loader import load_joinquant_credentials
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import fmt_float, ratio, to_float
from v5.paths import DEFAULT_PROCESSED_DIR


DEFAULT_PANEL = DEFAULT_PROCESSED_DIR / "home_appliances_state_gate_v5a5c" / "panel_with_home_appliances_state_gate.csv"
DEFAULT_OUT_DIR = DEFAULT_PROCESSED_DIR / "home_appliances_true_state_v5a5d"

TRUE_STATE_FIELDS = [
    "inventory",
    "account_receivable",
    "bill_receivable",
    "contract_assets",
    "contract_liability",
    "operating_revenue",
    "operating_cost",
    "total_current_assets",
    "total_current_liability",
    "inventory_to_revenue",
    "receivables_to_revenue",
    "contract_asset_to_revenue",
    "contract_liability_to_revenue",
    "working_capital_pressure_to_revenue",
    "inventory_to_current_assets",
    "receivables_to_current_assets",
    "current_ratio",
    "true_state_visible_date",
    "true_state_source",
]


@dataclass(frozen=True)
class HomeAppliancesTrueStateResult:
    panel_csv: Path
    raw_csv: Path
    summary_json: Path
    row_count: int
    enriched_count: int
    status: str


def enrich_home_appliances_true_state(
    panel_csv: Path = DEFAULT_PANEL,
    out_dir: Path = DEFAULT_OUT_DIR,
    username_env: str = "JQDATA_USERNAME",
    password_env: str = "JQDATA_PASSWORD",
) -> HomeAppliancesTrueStateResult:
    rows = read_csv_rows(panel_csv)
    jq = _load_authenticated_jqdata(username_env, password_env)
    fundamentals = _fetch_state_by_date(jq, rows)

    enriched_rows = []
    raw_rows = []
    for row in rows:
        trade_date = str(row.get("trade_date") or "")[:10]
        code = str(row.get("code") or "")
        raw = fundamentals.get(trade_date, {}).get(code, {})
        raw_rows.append({"trade_date": trade_date, "code": code, **{key: raw.get(key, "") for key in _RAW_FIELDS}})
        enriched = dict(row)
        enriched.update(_derive_true_state_fields(raw, trade_date))
        enriched_rows.append(enriched)

    out_dir.mkdir(parents=True, exist_ok=True)
    panel_out = out_dir / "panel_with_true_home_appliances_state.csv"
    raw_out = out_dir / "home_appliances_true_state_raw.csv"
    summary_out = out_dir / "home_appliances_true_state_summary.json"
    write_csv_rows(panel_out, _merge_fieldnames(rows, TRUE_STATE_FIELDS), enriched_rows)
    write_csv_rows(raw_out, ["trade_date", "code", *_RAW_FIELDS], raw_rows)
    coverage = _coverage(enriched_rows)
    status = "true_state_enriched_needs_validation" if coverage.get("inventory_to_revenue", 0.0) >= 0.8 else "true_state_enrichment_needs_review"
    write_json_file(
        summary_out,
        {
            "dataset": "home_appliances_true_state_v5a5d",
            "panel_csv": str(panel_csv),
            "panel_with_true_state": str(panel_out),
            "raw_csv": str(raw_out),
            "row_count": len(rows),
            "enriched_count": sum(1 for row in enriched_rows if row.get("inventory_to_revenue") not in ("", None)),
            "coverage": coverage,
            "status": status,
            "pit_policy": "Uses jqdatasdk.get_fundamentals(date=trade_date); true source report dates are not exported in this runner.",
            "limitations": [
                "This runner repairs inventory and working-capital state; export exposure is repaired by home_appliances_export_exposure_runner.",
                "Field-level original announcement dates are not available here; the source is PIT vendor snapshot on trade_date.",
            ],
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return HomeAppliancesTrueStateResult(panel_out, raw_out, summary_out, len(rows), sum(1 for row in enriched_rows if row.get("inventory_to_revenue") not in ("", None)), status)


_RAW_FIELDS = [
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


def _load_authenticated_jqdata(username_env: str, password_env: str) -> Any:
    try:
        import jqdatasdk as jq
    except Exception as exc:  # pragma: no cover - optional dependency.
        raise RuntimeError("home appliances true state enrichment requires jqdatasdk") from exc

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


def _derive_true_state_fields(raw: dict[str, Any], trade_date: str) -> dict[str, str]:
    inventory = to_float(raw.get("inventories"))
    account_receivable = to_float(raw.get("account_receivable"))
    bill_receivable = to_float(raw.get("bill_receivable"))
    contract_assets = to_float(raw.get("contract_assets"))
    contract_liability = to_float(raw.get("contract_liability"))
    revenue = to_float(raw.get("operating_revenue"))
    current_assets = to_float(raw.get("total_current_assets"))
    current_liability = to_float(raw.get("total_current_liability"))
    receivables = (account_receivable or 0.0) + (bill_receivable or 0.0)
    working_pressure = (inventory or 0.0) + receivables + (contract_assets or 0.0) - (contract_liability or 0.0)
    return {
        "inventory": fmt_float(inventory),
        "account_receivable": fmt_float(account_receivable),
        "bill_receivable": fmt_float(bill_receivable),
        "contract_assets": fmt_float(contract_assets),
        "contract_liability": fmt_float(contract_liability),
        "operating_revenue": fmt_float(revenue),
        "operating_cost": fmt_float(raw.get("operating_cost")),
        "total_current_assets": fmt_float(current_assets),
        "total_current_liability": fmt_float(current_liability),
        "inventory_to_revenue": fmt_float(ratio(inventory, revenue)),
        "receivables_to_revenue": fmt_float(ratio(receivables, revenue)),
        "contract_asset_to_revenue": fmt_float(ratio(contract_assets, revenue)),
        "contract_liability_to_revenue": fmt_float(ratio(contract_liability, revenue)),
        "working_capital_pressure_to_revenue": fmt_float(ratio(working_pressure, revenue)),
        "inventory_to_current_assets": fmt_float(ratio(inventory, current_assets)),
        "receivables_to_current_assets": fmt_float(ratio(receivables, current_assets)),
        "current_ratio": fmt_float(ratio(current_assets, current_liability)),
        "true_state_visible_date": trade_date,
        "true_state_source": "jqdatasdk.get_fundamentals(date=trade_date)",
    }


def _coverage(rows: list[dict[str, str]]) -> dict[str, float]:
    result: dict[str, float] = {}
    total = len(rows)
    for field in TRUE_STATE_FIELDS:
        if field.endswith("_source") or field.endswith("_visible_date"):
            continue
        result[field] = 0.0 if total == 0 else sum(1 for row in rows if row.get(field) not in ("", None)) / total
    return result


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

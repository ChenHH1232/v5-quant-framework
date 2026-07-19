from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from v5.credential_loader import load_joinquant_credentials


DEFAULT_OUT_DIR = Path("\u6570\u636e\u5e93") / "processed" / "gas_water_financial_evidence_v57"

DIRECT_FIELDS = [
    "direct_operating_revenue",
    "direct_total_operating_revenue",
    "direct_goods_sale_cash",
    "direct_account_receivable",
    "direct_bill_receivable",
    "direct_receivable_fin",
    "direct_contract_assets",
    "direct_longterm_receivable",
    "direct_receivables_total",
    "direct_receivables_to_revenue",
    "direct_receivables_to_assets",
    "direct_collection_cash_to_revenue",
    "direct_shortterm_loan",
    "direct_longterm_loan",
    "direct_bonds_payable",
    "direct_debt_due_within_one_year",
    "direct_interest_bearing_debt",
    "direct_interest_bearing_debt_to_assets",
    "direct_cash_equivalents",
    "direct_net_debt_to_assets",
    "direct_net_operate_cash_flow",
    "direct_ocf_to_receivables",
    "receivables_pressure_safe",
    "collection_quality_direct_safe",
    "interest_bearing_debt_pressure_safe",
    "net_debt_pressure_safe",
    "gas_water_financial_evidence_visible_date",
    "gas_water_financial_evidence_source",
]


def enrich_gas_water_financial_evidence(
    panel: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
    username_env: str = "JQDATA_USERNAME",
    password_env: str = "JQDATA_PASSWORD",
) -> Path:
    rows = _read_csv(panel)
    if not rows:
        raise RuntimeError(f"panel has no rows: {panel}")

    jq = _load_authenticated_jqdata(username_env, password_env)
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        code = str(row.get("code") or "")
        trade_date = str(row.get("trade_date") or "")
        if code and trade_date:
            grouped[trade_date].append(code)

    evidence_by_key: dict[tuple[str, str], dict[str, str]] = {}
    warnings: list[str] = []
    for trade_date, codes in sorted(grouped.items()):
        unique_codes = sorted(set(codes))
        try:
            fetched = _fetch_direct_financials(jq, unique_codes, trade_date)
        except Exception as exc:
            warnings.append(f"{trade_date}: direct financial evidence collection failed: {type(exc).__name__}: {exc}")
            fetched = {}
        for code in unique_codes:
            evidence_by_key[(trade_date, code)] = _derive_direct_metrics(fetched.get(code, {}), trade_date)

    enriched: list[dict[str, Any]] = []
    for row in rows:
        trade_date = str(row.get("trade_date") or "")
        code = str(row.get("code") or "")
        merged = dict(row)
        merged.update(evidence_by_key.get((trade_date, code), _blank_evidence(trade_date)))
        enriched.append(merged)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "panel_with_direct_financial_evidence.csv"
    fieldnames = list(rows[0].keys())
    for field in DIRECT_FIELDS:
        if field not in fieldnames:
            fieldnames.append(field)
    _write_csv(out_path, fieldnames, enriched)

    coverage_rows = _coverage_by_rebalance(enriched)
    _write_csv(out_dir / "direct_financial_evidence_coverage_by_rebalance.csv", list(coverage_rows[0].keys()) if coverage_rows else [], coverage_rows)
    _write_json(
        out_dir / "direct_financial_evidence_manifest.json",
        {
            "dataset": "gas_water_direct_financial_evidence_v57",
            "source_panel": str(panel),
            "output_panel": str(out_path),
            "row_count": len(enriched),
            "date_count": len({row.get("trade_date") for row in enriched}),
            "code_count": len({row.get("code") for row in enriched}),
            "direct_fields": DIRECT_FIELDS,
            "coverage_by_rebalance": "direct_financial_evidence_coverage_by_rebalance.csv",
            "warnings": warnings,
            "pit_policy": "jqdatasdk.get_fundamentals(date=trade_date); fields are treated as visible on the rebalance date returned by the vendor PIT interface.",
            "research_policy": "Direct receivables and debt fields are risk-evidence inputs. They must not be used for return tuning.",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    return out_path


def _fetch_direct_financials(jq: Any, codes: list[str], trade_date: str) -> dict[str, dict[str, Any]]:
    if not codes:
        return {}
    df = jq.get_fundamentals(
        jq.query(
            jq.valuation.code,
            jq.income.operating_revenue,
            jq.income.total_operating_revenue,
            jq.cash_flow.goods_sale_and_service_render_cash,
            jq.cash_flow.net_operate_cash_flow,
            jq.balance.account_receivable,
            jq.balance.bill_receivable,
            jq.balance.receivable_fin,
            jq.balance.contract_assets,
            jq.balance.longterm_receivable_account,
            jq.balance.total_assets,
            jq.balance.cash_equivalents,
            jq.balance.shortterm_loan,
            jq.balance.longterm_loan,
            jq.balance.bonds_payable,
            jq.balance.non_current_liability_in_one_year,
        ).filter(jq.valuation.code.in_(codes)),
        date=trade_date,
    )
    if df is None or getattr(df, "empty", True):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in df.to_dict("records"):
        code = str(row.get("code") or "")
        if code:
            result[code] = row
    return result


def _derive_direct_metrics(raw: dict[str, Any], trade_date: str) -> dict[str, str]:
    if not raw:
        return _blank_evidence(trade_date)
    revenue = _first_float(raw.get("total_operating_revenue"), raw.get("operating_revenue"))
    total_assets = _to_float(raw.get("total_assets"))
    goods_sale_cash = _to_float(raw.get("goods_sale_and_service_render_cash"))
    account_receivable = _to_float(raw.get("account_receivable"))
    bill_receivable = _to_float(raw.get("bill_receivable"))
    receivable_fin = _to_float(raw.get("receivable_fin"))
    contract_assets = _to_float(raw.get("contract_assets"))
    longterm_receivable = _to_float(raw.get("longterm_receivable_account"))
    receivables_total = _sum_present(account_receivable, bill_receivable, receivable_fin, contract_assets, longterm_receivable)
    shortterm_loan = _to_float(raw.get("shortterm_loan"))
    longterm_loan = _to_float(raw.get("longterm_loan"))
    bonds_payable = _to_float(raw.get("bonds_payable"))
    due_one_year = _to_float(raw.get("non_current_liability_in_one_year"))
    interest_bearing_debt = _sum_present(shortterm_loan, longterm_loan, bonds_payable, due_one_year)
    cash_equivalents = _to_float(raw.get("cash_equivalents"))
    net_operate_cash_flow = _to_float(raw.get("net_operate_cash_flow"))

    receivables_to_revenue = _ratio(receivables_total, revenue)
    receivables_to_assets = _ratio(receivables_total, total_assets)
    collection_to_revenue = _ratio(goods_sale_cash, revenue)
    debt_to_assets = _ratio(interest_bearing_debt, total_assets)
    net_debt_to_assets = _ratio(None if interest_bearing_debt is None else interest_bearing_debt - (cash_equivalents or 0.0), total_assets)
    ocf_to_receivables = _ratio(net_operate_cash_flow, receivables_total)

    return {
        "direct_operating_revenue": _fmt_float(raw.get("operating_revenue")),
        "direct_total_operating_revenue": _fmt_float(raw.get("total_operating_revenue")),
        "direct_goods_sale_cash": _fmt_float(goods_sale_cash),
        "direct_account_receivable": _fmt_float(account_receivable),
        "direct_bill_receivable": _fmt_float(bill_receivable),
        "direct_receivable_fin": _fmt_float(receivable_fin),
        "direct_contract_assets": _fmt_float(contract_assets),
        "direct_longterm_receivable": _fmt_float(longterm_receivable),
        "direct_receivables_total": _fmt_float(receivables_total),
        "direct_receivables_to_revenue": _fmt_float(receivables_to_revenue),
        "direct_receivables_to_assets": _fmt_float(receivables_to_assets),
        "direct_collection_cash_to_revenue": _fmt_float(collection_to_revenue),
        "direct_shortterm_loan": _fmt_float(shortterm_loan),
        "direct_longterm_loan": _fmt_float(longterm_loan),
        "direct_bonds_payable": _fmt_float(bonds_payable),
        "direct_debt_due_within_one_year": _fmt_float(due_one_year),
        "direct_interest_bearing_debt": _fmt_float(interest_bearing_debt),
        "direct_interest_bearing_debt_to_assets": _fmt_float(debt_to_assets),
        "direct_cash_equivalents": _fmt_float(cash_equivalents),
        "direct_net_debt_to_assets": _fmt_float(net_debt_to_assets),
        "direct_net_operate_cash_flow": _fmt_float(net_operate_cash_flow),
        "direct_ocf_to_receivables": _fmt_float(ocf_to_receivables),
        "receivables_pressure_safe": _fmt_safe_lower(receivables_to_revenue, 0.0, 5.0),
        "collection_quality_direct_safe": _fmt_safe_higher(collection_to_revenue, 0.0, 5.0),
        "interest_bearing_debt_pressure_safe": _fmt_safe_lower(debt_to_assets, 0.0, 2.0),
        "net_debt_pressure_safe": _fmt_safe_lower(net_debt_to_assets, -1.0, 2.0),
        "gas_water_financial_evidence_visible_date": trade_date,
        "gas_water_financial_evidence_source": "jqdatasdk.get_fundamentals(date=trade_date)",
    }


def _blank_evidence(trade_date: str) -> dict[str, str]:
    return {field: (trade_date if field == "gas_water_financial_evidence_visible_date" else "") for field in DIRECT_FIELDS}


def _coverage_by_rebalance(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get("trade_date") or "")].append(row)
    result = []
    for trade_date, date_rows in sorted(groups.items()):
        total = len(date_rows)
        if total == 0:
            continue
        covered = sum(1 for row in date_rows if str(row.get("direct_receivables_total") or ""))
        collection = sum(1 for row in date_rows if str(row.get("direct_collection_cash_to_revenue") or ""))
        debt = sum(1 for row in date_rows if str(row.get("direct_interest_bearing_debt_to_assets") or ""))
        result.append(
            {
                "trade_date": trade_date,
                "total_rows": total,
                "direct_receivables_rows": covered,
                "direct_receivables_coverage": _fmt_float(covered / total),
                "direct_collection_rows": collection,
                "direct_collection_coverage": _fmt_float(collection / total),
                "direct_debt_rows": debt,
                "direct_debt_coverage": _fmt_float(debt / total),
            }
        )
    return result


def _load_authenticated_jqdata(username_env: str, password_env: str):
    try:
        import jqdatasdk as jq
    except Exception as exc:
        raise RuntimeError("jqdatasdk is required for gas/water direct financial evidence collection") from exc
    username, password = load_joinquant_credentials(username_env, password_env)
    if username and password:
        jq.auth(username, password)
    if not jq.is_auth():
        raise RuntimeError("JoinQuant credentials are not available for gas/water direct financial evidence collection")
    return jq


def _first_float(*values: Any) -> float | None:
    for value in values:
        numeric = _to_float(value)
        if numeric is not None:
            return numeric
    return None


def _sum_present(*values: float | None) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present)


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _fmt_safe_lower(value: float | None, lower: float, upper: float) -> str:
    if value is None or value < lower or value > upper:
        return ""
    return _fmt_float(value)


def _fmt_safe_higher(value: float | None, lower: float, upper: float) -> str:
    if value is None or value < lower or value > upper:
        return ""
    return _fmt_float(value)


def _to_float(value: Any) -> float | None:
    if value in {None, "", "nan", "NaN", "None"}:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _fmt_float(value: Any) -> str:
    numeric = _to_float(value)
    if numeric is None:
        return ""
    return f"{numeric:.10g}"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-gas-water-financial-evidence")
    parser.add_argument("panel", type=Path)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)
    print(enrich_gas_water_financial_evidence(args.panel, out_dir=args.out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

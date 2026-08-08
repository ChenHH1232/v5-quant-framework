from __future__ import annotations

import argparse
import csv
import json
import math
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5c_core_infra_cashflow_field_repair") / "current"
PRE2021_REPAIR_DIR = Path("v5f_pre2021_factor_panel_repair") / "current"
SCOPE_START = "2013-01-01"
SCOPE_END = "2021-04-30"
FORMAL_START = "2021-05-01"
FORMAL_END = "2026-05-31"

SECTORS = {
    "highway_infrastructure": {
        "strict_panel": PRE2021_REPAIR_DIR / "v5f_pre2021_highway_v54h_strict_panel_with_low_vol.csv",
        "proxy_panel": PRE2021_REPAIR_DIR / "v5f_pre2021_highway_v54h_proxy_panel_with_low_vol.csv",
    },
    "port_rail_infrastructure": {
        "strict_panel": PRE2021_REPAIR_DIR / "v5f_pre2021_port_rail_v55j_strict_panel_with_low_vol.csv",
        "proxy_panel": PRE2021_REPAIR_DIR / "v5f_pre2021_port_rail_v55j_proxy_panel_with_low_vol.csv",
    },
}

REPAIRED_FIELDS = [
    "ocf_to_revenue",
    "cash_collection_quality",
    "operating_cash_flow_yield",
    "return_on_equity_ttm",
    "operating_cash_flow_to_net_profit",
    "interest_coverage",
    "asset_liability_ratio",
]

STILL_SOURCE_BLOCKED_FIELDS = [
    "free_cash_flow_yield",
    "capex_burden",
]

FACTOR_SPECS = [
    ("ocf_to_revenue", "higher_better", "cashflow_quality"),
    ("cash_collection_quality", "higher_better", "cashflow_quality_proxy"),
    ("operating_cash_flow_yield", "higher_better", "cashflow_yield"),
    ("operating_cash_flow_to_net_profit", "higher_better", "cash_conversion"),
    ("return_on_equity_ttm", "higher_better", "quality"),
    ("interest_coverage", "higher_better", "debt_service_quality"),
    ("asset_liability_ratio", "lower_better", "leverage"),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_v5c_core_infra_cashflow_field_repair(
    root: Path = Path("."),
    *,
    fetch_baostock: bool = True,
    start_year: int = 2017,
    end_year: int = 2020,
) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    missing = _missing_inputs(root)
    if missing:
        blockers = [
            {
                "blocker_id": "missing_pre2021_infrastructure_panel",
                "severity": "fatal",
                "scope": row["sector_id"],
                "detail": row["path"],
                "required_action": "restore v5f_pre2021_factor_panel_repair/current outputs",
            }
            for row in missing
        ]
        summary = _summary(
            status="blocked_missing_inputs",
            fetch_baostock=fetch_baostock,
            baostock_started=False,
            strict_rows=0,
            repaired_field_pass_count=0,
            capex_complete=False,
            blockers=blockers,
        )
        _write_outputs(out, summary, [], [], [], [], [], [], blockers, [])
        return summary

    panel_records = _load_panel_records(root)
    codes = sorted({row["code"] for row in panel_records if row.get("code")})
    finance_payload = _fetch_baostock_finance(codes, fetch_baostock, start_year, end_year)
    enriched = _enrich_rows(panel_records, finance_payload["records_by_code"])
    field_coverage = _field_coverage(enriched)
    pit_audit = _pit_audit(enriched)
    factor_preview = _factor_preview(enriched)
    source_audit = finance_payload["fetch_audit"]
    blockers = _blockers(field_coverage, source_audit)
    next_queue = _next_queue(blockers, field_coverage)
    sidecar_queue = _sidecar_queue()

    strict_rows = [row for row in enriched if row["scope"] == "strict_pit_universe"]
    repaired_pass = sum(
        1
        for row in field_coverage
        if row["scope"] == "strict_pit_universe"
        and row["field"] in REPAIRED_FIELDS
        and row["field_status"] == "pass"
    )
    capex_complete = all(
        row["field_status"] == "pass"
        for row in field_coverage
        if row["scope"] == "strict_pit_universe" and row["field"] in STILL_SOURCE_BLOCKED_FIELDS
    )
    status = (
        "completed_ocf_quality_repair_capex_source_blocked"
        if not capex_complete
        else "completed_ocf_quality_and_capex_repair"
    )
    summary = _summary(
        status=status,
        fetch_baostock=fetch_baostock,
        baostock_started=finance_payload["started"],
        strict_rows=len(strict_rows),
        repaired_field_pass_count=repaired_pass,
        capex_complete=capex_complete,
        blockers=blockers,
    )
    _write_outputs(
        out,
        summary,
        enriched,
        field_coverage,
        pit_audit,
        factor_preview,
        source_audit,
        next_queue,
        blockers,
        sidecar_queue,
    )
    return summary


def _missing_inputs(root: Path) -> list[dict[str, str]]:
    missing = []
    for sector_id, paths in SECTORS.items():
        for scope_name, rel in paths.items():
            if not (root / rel).exists():
                missing.append({"sector_id": sector_id, "scope": scope_name, "path": str(rel)})
    return missing


def _load_panel_records(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for sector_id, paths in SECTORS.items():
        for scope_name, rel in paths.items():
            scope = "strict_pit_universe" if scope_name == "strict_panel" else "price_universe_proxy_not_validation"
            for row in _read_csv(root / rel):
                row = dict(row)
                row["sector_id"] = sector_id
                row["scope"] = scope
                row["source_panel"] = str(rel)
                rows.append(row)
    return rows


def _fetch_baostock_finance(codes: list[str], fetch: bool, start_year: int, end_year: int) -> dict[str, Any]:
    if not fetch:
        return {
            "started": False,
            "records_by_code": {},
            "fetch_audit": [
                {
                    "source": "baostock_finance",
                    "status": "not_run",
                    "code_count": len(codes),
                    "detail": "fetch disabled",
                }
            ],
        }
    started = time.perf_counter()
    audit: list[dict[str, Any]] = []
    records_by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    try:
        import baostock as bs
    except Exception as exc:
        return {
            "started": True,
            "records_by_code": {},
            "fetch_audit": [
                {
                    "source": "baostock_finance",
                    "status": "import_error",
                    "code_count": len(codes),
                    "detail": f"{type(exc).__name__}: {exc}",
                }
            ],
        }

    login = bs.login()
    if getattr(login, "error_code", "") != "0":
        return {
            "started": True,
            "records_by_code": {},
            "fetch_audit": [
                {
                    "source": "baostock_finance",
                    "status": "login_error",
                    "code_count": len(codes),
                    "detail": str(getattr(login, "error_msg", "")),
                }
            ],
        }

    try:
        for code in codes:
            bs_code = _jq_to_baostock(code)
            for year in range(start_year, end_year + 1):
                for quarter in range(1, 5):
                    q_started = time.perf_counter()
                    merged = _fetch_one_financial_quarter(bs, bs_code, year, quarter)
                    if merged.get("status") == "pass":
                        record = merged["record"]
                        record["code"] = code
                        record["bs_code"] = bs_code
                        record["year"] = str(year)
                        record["quarter"] = str(quarter)
                        records_by_code[code].append(record)
                    audit.append(
                        {
                            "source": "baostock_finance_quarter",
                            "code": code,
                            "bs_code": bs_code,
                            "year": year,
                            "quarter": quarter,
                            "status": merged.get("status", ""),
                            "detail": merged.get("detail", ""),
                            "elapsed_sec": round(time.perf_counter() - q_started, 3),
                        }
                    )
    finally:
        bs.logout()

    audit.append(
        {
            "source": "baostock_finance",
            "status": "pass",
            "code_count": len(codes),
            "record_count": sum(len(rows) for rows in records_by_code.values()),
            "elapsed_sec": round(time.perf_counter() - started, 3),
            "detail": "query_cash_flow_data/profit_data/balance_data completed",
        }
    )
    return {"started": True, "records_by_code": dict(records_by_code), "fetch_audit": audit}


def _fetch_one_financial_quarter(bs: Any, bs_code: str, year: int, quarter: int) -> dict[str, Any]:
    cash = _query_bs(bs.query_cash_flow_data(code=bs_code, year=year, quarter=quarter))
    profit = _query_bs(bs.query_profit_data(code=bs_code, year=year, quarter=quarter))
    balance = _query_bs(bs.query_balance_data(code=bs_code, year=year, quarter=quarter))
    errors = [item["error"] for item in [cash, profit, balance] if item["error"]]
    if errors:
        return {"status": "query_error", "detail": "; ".join(errors)}
    if not cash["rows"] and not profit["rows"] and not balance["rows"]:
        return {"status": "empty", "detail": "no rows"}

    rec: dict[str, Any] = {}
    for source_id, payload in [("cash_flow", cash), ("profit", profit), ("balance", balance)]:
        row = payload["rows"][0] if payload["rows"] else {}
        if row:
            rec[f"{source_id}_pubDate"] = row.get("pubDate", "")
            rec[f"{source_id}_statDate"] = row.get("statDate", "")
        for key, value in row.items():
            if key not in {"code", "pubDate", "statDate"}:
                rec[key] = value
    pub_dates = [rec.get(key, "") for key in ["cash_flow_pubDate", "profit_pubDate", "balance_pubDate"] if rec.get(key, "")]
    stat_dates = [rec.get(key, "") for key in ["cash_flow_statDate", "profit_statDate", "balance_statDate"] if rec.get(key, "")]
    rec["pubDate"] = max(pub_dates) if pub_dates else ""
    rec["statDate"] = max(stat_dates) if stat_dates else ""
    return {"status": "pass", "record": rec, "detail": ""}


def _query_bs(result_set: Any) -> dict[str, Any]:
    rows = []
    if getattr(result_set, "error_code", "") != "0":
        return {"rows": [], "error": str(getattr(result_set, "error_msg", ""))}
    while result_set.next():
        rows.append(dict(zip(result_set.fields, result_set.get_row_data())))
    return {"rows": rows, "error": ""}


def _enrich_rows(panel_rows: list[dict[str, str]], records_by_code: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    enriched = []
    for row in panel_rows:
        item: dict[str, Any] = dict(row)
        rec = _latest_visible_financial_record(records_by_code.get(row.get("code", ""), []), row.get("trade_date", ""))
        if rec:
            close = _to_float(row.get("close"))
            shares = _to_float(rec.get("totalShare"))
            market_cap = close * shares if close is not None and shares is not None else None
            net_profit = _to_float(rec.get("netProfit"))
            cfo_to_np = _to_float(rec.get("CFOToNP"))
            cfo_proxy = net_profit * cfo_to_np if net_profit is not None and cfo_to_np is not None else None
            ocf_yield = _ratio(cfo_proxy, market_cap)

            item["ocf_to_revenue"] = _fmt(_to_float(rec.get("CFOToOR")))
            item["cash_collection_quality"] = _fmt(_to_float(rec.get("CFOToGr") or rec.get("CFOToOR")))
            item["operating_cash_flow_yield"] = _fmt(ocf_yield)
            item["return_on_equity_ttm"] = _fmt(_to_float(rec.get("roeAvg")))
            item["operating_cash_flow_to_net_profit"] = _fmt(cfo_to_np)
            item["interest_coverage"] = _fmt(_to_float(rec.get("ebitToInterest")))
            item["asset_liability_ratio"] = _fmt(_to_float(rec.get("liabilityToAsset")))
            item["free_cash_flow_yield"] = ""
            item["capex_burden"] = ""
            item["cashflow_factor_visible_date"] = rec.get("pubDate", "")
            item["cashflow_report_period"] = rec.get("statDate", "")
            item["cashflow_factor_source"] = "baostock_finance_pit_visible;ocf_yield=cfo_to_np*net_profit/(close*totalShare)"
            item["cashflow_repair_status"] = "pass_ocf_quality_capex_blocked"
            item["cashflow_repair_notes"] = "BaoStock provides OCF ratios, ROE, interest coverage and leverage, but not capex cash paid; capex_burden and FCF yield remain source-blocked."
        else:
            item["cashflow_factor_visible_date"] = ""
            item["cashflow_report_period"] = ""
            item["cashflow_factor_source"] = ""
            item["cashflow_repair_status"] = "missing_visible_baostock_finance_record"
            item["cashflow_repair_notes"] = "No BaoStock finance row with pubDate <= trade_date was available."
        enriched.append(item)
    return enriched


def _latest_visible_financial_record(records: list[dict[str, Any]], trade_date: str) -> dict[str, Any] | None:
    visible = [
        rec
        for rec in records
        if str(rec.get("pubDate", ""))[:10] <= trade_date
        and str(rec.get("statDate", ""))[:10] <= trade_date
        and str(rec.get("pubDate", ""))[:10]
    ]
    if not visible:
        return None
    visible.sort(key=lambda rec: (str(rec.get("statDate", ""))[:10], str(rec.get("pubDate", ""))[:10]))
    return visible[-1]


def _field_coverage(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = REPAIRED_FIELDS + STILL_SOURCE_BLOCKED_FIELDS
    out = []
    for (sector_id, scope), group in _groupby(rows, lambda row: (row["sector_id"], row["scope"])).items():
        row_count = len(group)
        for field in fields:
            nonempty = sum(1 for row in group if _has_value(row.get(field)))
            ratio = nonempty / row_count if row_count else 0.0
            out.append(
                {
                    "sector_id": sector_id,
                    "scope": scope,
                    "field": field,
                    "row_count": row_count,
                    "nonempty_count": nonempty,
                    "coverage_ratio": _fmt(ratio),
                    "field_status": "pass" if ratio >= 0.95 else ("partial" if ratio > 0 else "missing"),
                    "source_status": "source_blocked" if field in STILL_SOURCE_BLOCKED_FIELDS and ratio < 0.95 else "available",
                }
            )
    return out


def _pit_audit(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        visible = str(row.get("cashflow_factor_visible_date", ""))[:10]
        trade_date = str(row.get("trade_date", ""))[:10]
        status = "missing_visible_record"
        if visible:
            status = "pass" if visible <= trade_date else "fail_visible_after_trade_date"
        out.append(
            {
                "sector_id": row.get("sector_id", ""),
                "scope": row.get("scope", ""),
                "trade_date": trade_date,
                "code": row.get("code", ""),
                "cashflow_factor_visible_date": visible,
                "cashflow_report_period": row.get("cashflow_report_period", ""),
                "pit_status": status,
                "source": row.get("cashflow_factor_source", ""),
            }
        )
    return out


def _factor_preview(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    strict = [row for row in rows if row.get("scope") == "strict_pit_universe"]
    out = []
    for sector_id, sector_rows in _groupby(strict, lambda row: row["sector_id"]).items():
        for field, direction, family in FACTOR_SPECS:
            periods = []
            for trade_date, day_rows in _groupby(sector_rows, lambda row: row["trade_date"]).items():
                valid = [row for row in day_rows if _to_float(row.get(field)) is not None and _to_float(row.get("future_return")) is not None]
                if len(valid) < 4:
                    continue
                reverse = direction == "higher_better"
                valid.sort(key=lambda row: _to_float(row.get(field)) or 0.0, reverse=reverse)
                bucket = max(1, len(valid) // 3)
                top = valid[:bucket]
                bottom = valid[-bucket:]
                top_ret = _mean(_to_float(row.get("future_return")) for row in top)
                bottom_ret = _mean(_to_float(row.get("future_return")) for row in bottom)
                if top_ret is None or bottom_ret is None:
                    continue
                periods.append({"trade_date": trade_date, "spread": top_ret - bottom_ret})
            spreads = [period["spread"] for period in periods]
            out.append(
                {
                    "sector_id": sector_id,
                    "factor_id": field,
                    "family": family,
                    "direction": direction,
                    "scope": "pre2021_train_test_only",
                    "period_count": len(spreads),
                    "avg_top_minus_bottom_return": _fmt(_mean(spreads)),
                    "positive_spread_rate": _fmt(sum(1 for value in spreads if value > 0) / len(spreads) if spreads else None),
                    "preview_status": _preview_status(spreads),
                    "formal_backtest_used_as_validation": False,
                    "accepted": False,
                }
            )
    return out


def _preview_status(spreads: list[float]) -> str:
    if len(spreads) < 4:
        return "insufficient_periods_diagnostic"
    positive_rate = sum(1 for value in spreads if value > 0) / len(spreads)
    avg = _mean(spreads)
    if avg is not None and avg > 0 and positive_rate >= 0.6:
        return "pre2021_positive_needs_formal_fixed_rule_review_not_accepted"
    return "diagnostic_only_no_stable_pre2021_spread"


def _blockers(field_coverage: list[dict[str, Any]], source_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers = []
    statuses = {str(row.get("status", "")) for row in source_audit}
    if "login_error" in statuses or "import_error" in statuses:
        blockers.append(
            {
                "blocker_id": "baostock_finance_source_unavailable",
                "severity": "fatal",
                "scope": "cashflow_field_repair",
                "detail": ";".join(sorted(statuses)),
                "required_action": "retry BaoStock finance fetch or provide another PIT-clean finance export",
            }
        )
    for row in field_coverage:
        if row["scope"] == "strict_pit_universe" and row["field"] in STILL_SOURCE_BLOCKED_FIELDS and row["field_status"] != "pass":
            blockers.append(
                {
                    "blocker_id": f"{row['sector_id']}_{row['field']}_source_blocked",
                    "severity": "nonfatal",
                    "scope": row["sector_id"],
                    "detail": f"{row['field']} coverage={row['coverage_ratio']}",
                    "required_action": "extract original cash-flow statement capex line with page/table/unit/visible-date review",
                }
            )
    return blockers


def _next_queue(blockers: list[dict[str, Any]], field_coverage: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fatal = any(row["severity"] == "fatal" for row in blockers)
    return [
        {
            "priority": "P0",
            "task_id": "v5c_infra_capex_original_statement_extraction",
            "status": "ready" if not fatal else "blocked_until_finance_source_available",
            "scope": "highway_infrastructure;port_rail_infrastructure",
            "action": "extract capex paid cash and FCF from original annual/quarterly statements with PIT visible-date review",
            "allowed": "data_gate_only",
        },
        {
            "priority": "P1",
            "task_id": "v5c_infra_ocf_quality_fixed_rule_preview",
            "status": "ready" if not fatal else "blocked",
            "scope": "pre2021_train_test_only",
            "action": "review OCF quality factor preview; do not use formal 2021-2026 as discovery",
            "allowed": "quant_spec_only",
        },
        {
            "priority": "P2",
            "task_id": "v5c_cross_sector_screen_rerun_after_capex",
            "status": "waiting_capex_data_gate",
            "scope": "current_core_sleeves",
            "action": "rerun fixed pre2021 factor screen only after capex/FCF fields are source-reviewed",
            "allowed": "not_backtest_until_spec_fixed",
        },
    ]


def _sidecar_queue() -> list[dict[str, Any]]:
    return [
        {
            "priority": "S1",
            "sector_id": "gas_water_operators",
            "route": "sidecar_observation_only",
            "status": "ready_for_observation_enhancement",
            "allowed_action": "refresh state tags and paper evidence; compare contribution without V57f core entry",
            "blocked_action": "V57f_core_entry;return_tuning;accepted",
        },
        {
            "priority": "S2",
            "sector_id": "telecom_operators",
            "route": "capped_specialist_sidecar_observation_only",
            "status": "ready_for_observation_enhancement",
            "allowed_action": "refresh capped specialist policy and paper evidence",
            "blocked_action": "ordinary_cross_section_core_promotion;accepted",
        },
        {
            "priority": "S3",
            "sector_id": "oil_gas;chemical_materials;nonferrous_metals;cement",
            "route": "cycle_data_gate_only",
            "status": "do_not_backtest_before_state_gate",
            "allowed_action": "repair price/spread/inventory/demand/capex PIT state data",
            "blocked_action": "model_backtest_without_cycle_state_gate",
        },
    ]


def _summary(
    *,
    status: str,
    fetch_baostock: bool,
    baostock_started: bool,
    strict_rows: int,
    repaired_field_pass_count: int,
    capex_complete: bool,
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    fatal = [row for row in blockers if row.get("severity") == "fatal"]
    nonfatal = [row for row in blockers if row.get("severity") != "fatal"]
    return {
        "created_at_utc": now_utc(),
        "task": "v5c_core_infra_cashflow_field_repair",
        "status": status,
        "train_test_scope_start": SCOPE_START,
        "train_test_scope_end": SCOPE_END,
        "formal_backtest_scope_start": FORMAL_START,
        "formal_backtest_scope_end": FORMAL_END,
        "target_sleeves": ["highway_infrastructure", "port_rail_infrastructure"],
        "fetch_baostock_requested": fetch_baostock,
        "baostock_started": baostock_started,
        "strict_panel_rows": strict_rows,
        "repaired_fields": REPAIRED_FIELDS,
        "repaired_field_pass_count": repaired_field_pass_count,
        "still_source_blocked_fields": STILL_SOURCE_BLOCKED_FIELDS,
        "capex_complete": capex_complete,
        "v57f_core_modified": False,
        "v5f_primary_modified": False,
        "formal_backtest_used_as_validation": False,
        "accepted": False,
        "live_trading_approved": False,
        "fatal_blocker_count": len(fatal),
        "nonfatal_blocker_count": len(nonfatal),
        "pm_gate_decision": "infra_ocf_quality_repaired_capex_data_gate_open" if not fatal else "blocked_by_finance_source",
    }


def _write_outputs(
    out: Path,
    summary: dict[str, Any],
    enriched: list[dict[str, Any]],
    field_coverage: list[dict[str, Any]],
    pit_audit: list[dict[str, Any]],
    factor_preview: list[dict[str, Any]],
    source_audit: list[dict[str, Any]],
    next_queue: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    sidecar_queue: list[dict[str, Any]],
) -> None:
    strict = [row for row in enriched if row.get("scope") == "strict_pit_universe"]
    proxy = [row for row in enriched if row.get("scope") != "strict_pit_universe"]
    _write_json(out / "v5c_core_infra_cashflow_field_repair_summary.json", summary)
    _write_csv(out / "v5c_core_infra_cashflow_enriched_strict_panel.csv", strict)
    _write_csv(out / "v5c_core_infra_cashflow_enriched_proxy_panel.csv", proxy)
    _write_csv(out / "v5c_core_infra_cashflow_field_coverage.csv", field_coverage)
    _write_csv(out / "v5c_core_infra_cashflow_pit_audit.csv", pit_audit)
    _write_csv(out / "v5c_core_infra_cashflow_factor_preview.csv", factor_preview)
    _write_csv(out / "v5c_core_infra_cashflow_baostock_fetch_audit.csv", source_audit)
    _write_csv(out / "v5c_core_infra_cashflow_blockers.csv", blockers)
    _write_csv(out / "v5c_core_infra_cashflow_next_queue.csv", next_queue)
    _write_csv(out / "v5c_core_sidecar_observation_queue.csv", sidecar_queue)
    (out / "v5c_core_infra_cashflow_field_repair_report.md").write_text(_report(summary, field_coverage, factor_preview, blockers, next_queue, sidecar_queue), encoding="utf-8")
    (out / "v5c_core_infra_cashflow_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")


def _report(
    summary: dict[str, Any],
    coverage: list[dict[str, Any]],
    preview: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    next_queue: list[dict[str, Any]],
    sidecar_queue: list[dict[str, Any]],
) -> str:
    lines = [
        "# V5c Core Infrastructure Cash-Flow Field Repair",
        "",
        f"- Status: `{summary['status']}`",
        f"- PM gate: `{summary['pm_gate_decision']}`",
        f"- Scope: highway and port/rail current V57f/V5f sleeves, pre-2021 train/test only.",
        f"- Formal backtest used as validation: `{summary['formal_backtest_used_as_validation']}`",
        f"- V57f/V5f modified: `{summary['v57f_core_modified']}` / `{summary['v5f_primary_modified']}`",
        "",
        "## Field Coverage",
        "",
        "| sector | scope | field | coverage | status |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in coverage:
        if row["scope"] == "strict_pit_universe":
            lines.append(f"| {row['sector_id']} | {row['scope']} | {row['field']} | {row['coverage_ratio']} | {row['field_status']} |")
    lines.extend(["", "## Pre-2021 Factor Preview", "", "| sector | factor | periods | avg spread | positive rate | status |", "| --- | --- | ---: | ---: | ---: | --- |"])
    for row in preview:
        lines.append(
            f"| {row['sector_id']} | {row['factor_id']} | {row['period_count']} | {row['avg_top_minus_bottom_return']} | {row['positive_spread_rate']} | {row['preview_status']} |"
        )
    lines.extend(["", "## Blockers", ""])
    if blockers:
        for row in blockers:
            lines.append(f"- `{row['blocker_id']}` ({row['severity']}): {row['detail']}")
    else:
        lines.append("- none")
    lines.extend(["", "## Next Queue", ""])
    for row in next_queue:
        lines.append(f"- {row['priority']} `{row['task_id']}`: {row['action']}")
    lines.extend(["", "## Sidecar Queue", ""])
    for row in sidecar_queue:
        lines.append(f"- {row['priority']} `{row['sector_id']}`: {row['allowed_action']}")
    return "\n".join(lines) + "\n"


def _agent_rules() -> str:
    return """# Agent Execution Rules

- This packet may repair data fields and produce diagnostics only.
- Do not modify V57f core or V5f primary.
- Do not use 2021-05-01 to 2026-05-31 formal backtest as discovery/validation for new factors.
- BaoStock finance rows must satisfy `pubDate <= trade_date`.
- Do not fill capex_burden or FCF yield unless the source exposes the original capex cash-flow statement line with reviewed unit and visible date.
- Gas/water and telecom remain sidecar observation only.
- Cycle industries require state data gates before any backtest.
- No accepted or live-approved status may be emitted by this packet.
"""


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _groupby(rows: list[dict[str, Any]], key_func: Any) -> dict[Any, list[dict[str, Any]]]:
    out: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        out[key_func(row)].append(row)
    return dict(out)


def _mean(values: Any) -> float | None:
    vals = [value for value in values if value is not None and math.isfinite(value)]
    if not vals:
        return None
    return sum(vals) / len(vals)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        val = float(text)
    except ValueError:
        return None
    if not math.isfinite(val):
        return None
    return val


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _fmt(value: float | None) -> str:
    if value is None or not math.isfinite(value):
        return ""
    return f"{value:.10g}"


def _has_value(value: Any) -> bool:
    return _to_float(value) is not None


def _jq_to_baostock(code: str) -> str:
    if code.endswith(".XSHG"):
        return "sh." + code[:6]
    if code.endswith(".XSHE"):
        return "sz." + code[:6]
    if code.startswith(("sh.", "sz.")):
        return code
    prefix = "sh" if code.startswith("6") else "sz"
    return f"{prefix}.{code[:6]}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--no-baostock", action="store_true")
    parser.add_argument("--start-year", type=int, default=2017)
    parser.add_argument("--end-year", type=int, default=2020)
    args = parser.parse_args()
    summary = run_v5c_core_infra_cashflow_field_repair(
        Path(args.root),
        fetch_baostock=not args.no_baostock,
        start_year=args.start_year,
        end_year=args.end_year,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

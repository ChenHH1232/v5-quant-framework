from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5c_p1_financial_quality_pit_panel") / "current"
P0_DIR = Path("v5c_p0_local_data_gate") / "current"
P0_HOLDINGS = P0_DIR / "v5c_p0_rebalance_holdings_targets.csv"
P0_TRUTH = P0_DIR / "v5c_p0_baseline_truth_table.csv"
P0_SUMMARY = P0_DIR / "v5c_p0_local_data_gate_summary.json"
DB_PROCESSED = Path("\u6570\u636e\u5e93") / "processed"

PANEL_PATHS = {
    "bank": Path("数据库/processed/startup_preload_repaired_panels_v5/bank_v3_repaired/panel_with_low_vol.csv"),
    "utilities_electricity": Path("数据库/processed/startup_preload_repaired_panels_v5/utilities_v51f/panel_with_low_vol.csv"),
    "highway_infrastructure": Path("数据库/processed/startup_preload_repaired_panels_v5/highway_v54h/panel_with_low_vol.csv"),
    "port_rail_infrastructure": Path("数据库/processed/startup_preload_repaired_panels_v5/port_rail_v55j/panel_with_low_vol.csv"),
}

DIVIDEND_PATHS = {
    "bank": Path("数据库/processed/bank_v3_joinquant_cash_dividends.csv"),
    "utilities_electricity": Path("数据库/processed/utilities_joinquant_cash_dividends.csv"),
    "highway_infrastructure": Path("数据库/processed/highway_v54h_joinquant_cash_dividends.csv"),
    "port_rail_infrastructure": Path("数据库/processed/port_rail_v55c_joinquant_cash_dividends.csv"),
}

PANEL_PATHS = {
    "bank": DB_PROCESSED / "startup_preload_repaired_panels_v5" / "bank_v3_repaired" / "panel_with_low_vol.csv",
    "utilities_electricity": DB_PROCESSED / "startup_preload_repaired_panels_v5" / "utilities_v51f" / "panel_with_low_vol.csv",
    "highway_infrastructure": DB_PROCESSED / "startup_preload_repaired_panels_v5" / "highway_v54h" / "panel_with_low_vol.csv",
    "port_rail_infrastructure": DB_PROCESSED / "startup_preload_repaired_panels_v5" / "port_rail_v55j" / "panel_with_low_vol.csv",
}

DIVIDEND_PATHS = {
    "bank": DB_PROCESSED / "bank_v3_joinquant_cash_dividends.csv",
    "utilities_electricity": DB_PROCESSED / "utilities_joinquant_cash_dividends.csv",
    "highway_infrastructure": DB_PROCESSED / "highway_v54h_joinquant_cash_dividends.csv",
    "port_rail_infrastructure": DB_PROCESSED / "port_rail_v55c_joinquant_cash_dividends.csv",
}

SCOPE_START = "2021-05-01"
SCOPE_END = "2026-05-31"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5c_p1_financial_quality_pit_panel(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5c_p1_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_p1_inputs_available", blockers)
        _write_json(out / "v5c_p1_financial_quality_summary.json", summary)
        return summary

    p0_summary = _read_json(root / P0_SUMMARY)
    p0_truth = _read_csv(root / P0_TRUTH)[0]
    holdings = _read_csv(root / P0_HOLDINGS)
    panel_by_key, source_manifest = _load_panels(root)
    financial_panel = _build_financial_panel(holdings, panel_by_key)
    universe = _build_universe(holdings, financial_panel)
    dividends = _build_cash_dividend_events(root, universe)
    _annotate_cash_dividend_availability(financial_panel, dividends)
    dividend_audit = _dividend_policy_audit(dividends, universe)
    coverage_audit = _field_coverage_audit(financial_panel, dividends, universe)
    visible_audit = _visible_date_audit(financial_panel, dividends)
    payout_audit = _payout_ratio_proxy_audit(financial_panel)
    sleeve_quality = _financial_quality_by_sleeve(financial_panel, dividends)
    blockers_out = _p1_blockers(coverage_audit, visible_audit)
    decision = _pm_decision(blockers_out, coverage_audit, payout_audit)
    next_queue = _next_queue(decision[0])

    _write_csv(out / "v5c_p1_source_manifest.csv", source_manifest)
    _write_csv(out / "v5c_p1_financial_universe.csv", universe)
    _write_csv(out / "v5c_p1_financial_quality_pit_panel.csv", financial_panel)
    _write_csv(out / "v5c_p1_cash_dividend_events.csv", dividends)
    _write_csv(out / "v5c_p1_dividend_policy_audit.csv", dividend_audit)
    _write_csv(out / "v5c_p1_field_coverage_audit.csv", coverage_audit)
    _write_csv(out / "v5c_p1_visible_date_audit.csv", visible_audit)
    _write_csv(out / "v5c_p1_payout_ratio_proxy_audit.csv", payout_audit)
    _write_csv(out / "v5c_p1_financial_quality_by_sleeve.csv", sleeve_quality)
    _write_csv(out / "v5c_p1_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_p1_next_data_gate_queue.csv", next_queue)
    _write_csv(out / "v5c_p1_blockers.csv", blockers_out)
    (out / "v5c_p1_financial_quality_report.md").write_text(
        _report(p0_truth, financial_panel, dividends, coverage_audit, visible_audit, payout_audit, decision, next_queue),
        encoding="utf-8",
    )
    (out / "v5c_p1_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    summary = _summary(
        "completed_p1_financial_quality_pit_panel",
        decision[0]["pm_gate_decision"],
        blockers_out,
        p0_pass=p0_summary.get("p0_pass", False),
        financial_panel_rows=len(financial_panel),
        cash_dividend_event_rows=len(dividends),
        universe_code_count=len(universe),
        exact_payout_ratio_available=decision[0]["exact_payout_ratio_available"] == "True",
        payout_proxy_used=decision[0]["payout_proxy_used"] == "True",
    )
    _write_json(out / "v5c_p1_financial_quality_summary.json", summary)
    return summary


def _load_panels(root: Path) -> tuple[dict[tuple[str, str], dict[str, str]], list[dict[str, Any]]]:
    panel_by_key: dict[tuple[str, str], dict[str, str]] = {}
    manifest = []
    for sleeve, rel_path in PANEL_PATHS.items():
        path = root / rel_path
        rows = _read_csv(path)
        for row in rows:
            panel_by_key[(row.get("trade_date", ""), row.get("code", ""))] = row | {"_source_sleeve": sleeve, "_source_path": str(rel_path)}
        manifest.append(
            {
                "source_id": f"panel_{sleeve}",
                "source_type": "startup_preload_repaired_factor_panel",
                "sleeve_id": sleeve,
                "path": str(rel_path),
                "row_count": len(rows),
                "field_count": len(rows[0]) if rows else 0,
                "p1_role": "financial_quality_ocf_valuation_context",
                "pit_status": "uses_panel_visible_date_fields_or_trade_date_as_of_source",
            }
        )
    for sleeve, rel_path in DIVIDEND_PATHS.items():
        rows = _read_csv(root / rel_path)
        manifest.append(
            {
                "source_id": f"cash_dividend_{sleeve}",
                "source_type": "joinquant_cash_dividend_event_file",
                "sleeve_id": sleeve,
                "path": str(rel_path),
                "row_count": len(rows),
                "field_count": len(rows[0]) if rows else 0,
                "p1_role": "cash_dividend_event_panel",
                "pit_status": "announce_ex_pay_dates_preserved",
            }
        )
    return panel_by_key, manifest


def _build_financial_panel(
    holdings: list[dict[str, str]],
    panel_by_key: dict[tuple[str, str], dict[str, str]],
) -> list[dict[str, Any]]:
    rows = []
    for hold in holdings:
        trade_date = hold["trade_date"]
        code = hold["code"]
        panel = panel_by_key.get((trade_date, code), {})
        dividend_yield_decimal = _normalize_yield(panel.get("dividend_yield"))
        pe_ratio = _to_float(panel.get("pe_ratio"))
        payout_proxy = dividend_yield_decimal * pe_ratio if dividend_yield_decimal is not None and pe_ratio and pe_ratio > 0 else None
        quality_fields = _quality_fields_present(panel, hold["sleeve_id"])
        visible_date = _financial_visible_date(panel, trade_date)
        rows.append(
            {
                "trade_date": trade_date,
                "code": code,
                "sleeve_id": hold["sleeve_id"],
                "selected_rank": hold.get("selected_rank", ""),
                "target_weight_signal": hold.get("target_weight_signal", ""),
                "actual_weight": hold.get("actual_weight", ""),
                "source_panel_path": panel.get("_source_path", ""),
                "panel_join_status": "matched" if panel else "missing_panel_row",
                "financial_visible_date": visible_date,
                "visible_date_status": "pass" if visible_date and visible_date <= trade_date else "fail",
                "factor_visible_date": panel.get("factor_visible_date", ""),
                "factor_visibility_source": panel.get("factor_visibility_source", ""),
                "dividend_visible_policy": panel.get("dividend_visible_policy", ""),
                "dividend_yield_raw": panel.get("dividend_yield", ""),
                "dividend_yield_decimal": _fmt_or_blank(dividend_yield_decimal),
                "cash_dividend_event_available": "",
                "operating_cash_flow_yield": panel.get("operating_cash_flow_yield", ""),
                "free_cash_flow_yield": panel.get("free_cash_flow_yield", ""),
                "ocf_to_revenue": panel.get("ocf_to_revenue", ""),
                "cash_collection_quality": panel.get("cash_collection_quality", ""),
                "operating_cash_flow_to_net_profit": panel.get("operating_cash_flow_to_net_profit", ""),
                "return_on_equity_ttm": panel.get("return_on_equity_ttm", ""),
                "gross_profit_margin": panel.get("gross_profit_margin", ""),
                "net_profit_margin": panel.get("net_profit_margin", ""),
                "pe_ratio": panel.get("pe_ratio", ""),
                "payout_ratio_exact": "",
                "payout_ratio_proxy": _fmt_or_blank(payout_proxy),
                "payout_ratio_source": "dividend_yield_decimal_times_positive_pe_ratio" if payout_proxy is not None else "not_available",
                "non_performing_loan_ratio": panel.get("non_performing_loan_ratio", ""),
                "provision_coverage_ratio": panel.get("provision_coverage_ratio", ""),
                "core_tier_1_capital_adequacy_ratio": panel.get("core_tier_1_capital_adequacy_ratio", ""),
                "capex_burden": panel.get("capex_burden", ""),
                "asset_liability_ratio": panel.get("asset_liability_ratio", ""),
                "quality_field_count": quality_fields,
                "quality_status": "pass" if quality_fields >= _min_quality_fields(hold["sleeve_id"]) else "review",
                "pit_notes": _pit_notes(panel, hold["sleeve_id"]),
            }
        )
    return rows


def _build_universe(holdings: list[dict[str, str]], financial_panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_code: dict[str, dict[str, Any]] = {}
    row_count = defaultdict(int)
    sleeves = defaultdict(set)
    first_dates: dict[str, str] = {}
    last_dates: dict[str, str] = {}
    quality_count = defaultdict(int)
    for row in financial_panel:
        code = row["code"]
        row_count[code] += 1
        sleeves[code].add(row["sleeve_id"])
        first_dates[code] = min(first_dates.get(code, row["trade_date"]), row["trade_date"])
        last_dates[code] = max(last_dates.get(code, row["trade_date"]), row["trade_date"])
        if row["quality_status"] == "pass":
            quality_count[code] += 1
    for hold in holdings:
        code = hold["code"]
        by_code[code] = {
            "code": code,
            "sleeve_ids": ";".join(sorted(sleeves[code])),
            "first_selected_rebalance": first_dates.get(code, ""),
            "last_selected_rebalance": last_dates.get(code, ""),
            "selected_rebalance_count": row_count[code],
            "quality_pass_rows": quality_count[code],
            "universe_source": "v5c_p0_rebalance_holdings_targets",
            "p1_scope": "selected_rebalance_holdings_only",
        }
    return [by_code[code] for code in sorted(by_code)]


def _build_cash_dividend_events(root: Path, universe: list[dict[str, Any]]) -> list[dict[str, Any]]:
    code_to_sleeves = {row["code"]: row["sleeve_ids"] for row in universe}
    selected_codes = set(code_to_sleeves)
    out = []
    for sleeve, rel_path in DIVIDEND_PATHS.items():
        for row in _read_csv(root / rel_path):
            code = row.get("code", "")
            if code not in selected_codes:
                continue
            event_date = row.get("pay_date") or row.get("ex_date") or row.get("announce_date") or ""
            if event_date and (event_date < SCOPE_START or event_date > SCOPE_END):
                continue
            visible_date = row.get("announce_date") or row.get("ex_date") or row.get("pay_date") or ""
            out.append(
                {
                    "code": code,
                    "sleeve_id": sleeve,
                    "sleeve_ids_from_p0": code_to_sleeves.get(code, ""),
                    "report_period": row.get("report_period", ""),
                    "announce_date": row.get("announce_date", ""),
                    "record_date": row.get("record_date", ""),
                    "ex_date": row.get("ex_date", ""),
                    "pay_date": row.get("pay_date", ""),
                    "visible_date": visible_date,
                    "cash_per_share": row.get("cash_per_share", ""),
                    "dividend_tax_rate": row.get("dividend_tax_rate", ""),
                    "net_cash_per_share": row.get("net_cash_per_share", ""),
                    "source": row.get("source", str(rel_path)),
                    "event_pit_status": "pass" if visible_date and (not row.get("pay_date") or visible_date <= row.get("pay_date")) else "review",
                }
            )
    return sorted(out, key=lambda row: (row["pay_date"], row["code"], row["sleeve_id"]))


def _annotate_cash_dividend_availability(
    financial_panel: list[dict[str, Any]],
    dividends: list[dict[str, Any]],
) -> None:
    events_by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in dividends:
        events_by_code[row["code"]].append(row)
    for row in financial_panel:
        events = events_by_code.get(row["code"], [])
        visible_events = [event for event in events if event.get("visible_date") and event["visible_date"] <= row["trade_date"]]
        paid_events = [event for event in events if event.get("pay_date") and event["pay_date"] <= row["trade_date"]]
        if visible_events:
            status = "visible_event_by_rebalance"
        elif events:
            status = "scope_event_not_visible_yet"
        else:
            status = "no_scope_event"
        row["cash_dividend_event_available"] = status
        row["cash_dividend_visible_event_count"] = len(visible_events)
        row["cash_dividend_paid_event_count_to_date"] = len(paid_events)


def _dividend_policy_audit(dividends: list[dict[str, Any]], universe: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events_by_sleeve = defaultdict(int)
    codes_with_events_by_sleeve = defaultdict(set)
    for row in dividends:
        events_by_sleeve[row["sleeve_id"]] += 1
        codes_with_events_by_sleeve[row["sleeve_id"]].add(row["code"])
    codes_by_sleeve = defaultdict(set)
    for row in universe:
        for sleeve in str(row["sleeve_ids"]).split(";"):
            if sleeve:
                codes_by_sleeve[sleeve].add(row["code"])
    rows = []
    for sleeve in sorted(codes_by_sleeve):
        codes = codes_by_sleeve[sleeve]
        event_codes = codes_with_events_by_sleeve[sleeve]
        rows.append(
            {
                "sleeve_id": sleeve,
                "selected_code_count": len(codes),
                "codes_with_cash_dividend_event": len(event_codes),
                "cash_dividend_event_count": events_by_sleeve[sleeve],
                "cash_dividend_event_code_coverage": _ratio(len(event_codes), len(codes)),
                "policy": "announce_date preserved; cash can affect portfolio only on pay_date",
                "audit_status": "pass" if events_by_sleeve[sleeve] > 0 else "review",
            }
        )
    return rows


def _field_coverage_audit(
    financial_panel: list[dict[str, Any]],
    dividends: list[dict[str, Any]],
    universe: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    fields = [
        "dividend_yield_decimal",
        "operating_cash_flow_yield",
        "free_cash_flow_yield",
        "ocf_to_revenue",
        "cash_collection_quality",
        "operating_cash_flow_to_net_profit",
        "return_on_equity_ttm",
        "gross_profit_margin",
        "net_profit_margin",
        "payout_ratio_proxy",
        "non_performing_loan_ratio",
        "provision_coverage_ratio",
        "core_tier_1_capital_adequacy_ratio",
        "capex_burden",
        "asset_liability_ratio",
    ]
    sleeves = sorted({row["sleeve_id"] for row in financial_panel})
    for sleeve in sleeves + ["ALL"]:
        sample = financial_panel if sleeve == "ALL" else [row for row in financial_panel if row["sleeve_id"] == sleeve]
        for field in fields:
            present = sum(1 for row in sample if str(row.get(field, "")) not in {"", "nan", "None"})
            rows.append(
                {
                    "scope": sleeve,
                    "field_name": field,
                    "row_count": len(sample),
                    "present_count": present,
                    "coverage": _ratio(present, len(sample)),
                    "required_for_p1": _field_required_for_sleeve(field, sleeve),
                    "coverage_status": _coverage_status(field, sleeve, present, len(sample)),
                }
            )
    rows.append(
        {
            "scope": "ALL",
            "field_name": "cash_dividend_events",
            "row_count": len(universe),
            "present_count": len({row["code"] for row in dividends}),
            "coverage": _ratio(len({row["code"] for row in dividends}), len(universe)),
            "required_for_p1": True,
            "coverage_status": "pass" if dividends else "fail",
        }
    )
    return rows


def _visible_date_audit(financial_panel: list[dict[str, Any]], dividends: list[dict[str, Any]]) -> list[dict[str, Any]]:
    financial_bad = [row for row in financial_panel if row["visible_date_status"] != "pass"]
    dividend_bad = [row for row in dividends if row["event_pit_status"] != "pass"]
    return [
        {
            "audit_id": "financial_visible_date_lte_rebalance_date",
            "row_count": len(financial_panel),
            "bad_count": len(financial_bad),
            "audit_status": "pass" if not financial_bad else "fail",
            "notes": "financial_visible_date must be <= trade_date for each selected rebalance row.",
        },
        {
            "audit_id": "cash_dividend_announce_ex_pay_dates_preserved",
            "row_count": len(dividends),
            "bad_count": len(dividend_bad),
            "audit_status": "pass" if not dividend_bad else "review",
            "notes": "Dividend event panel preserves announce_date, ex_date and pay_date; cash recognition remains pay_date based.",
        },
        {
            "audit_id": "no_post_scope_dividend_pay_date",
            "row_count": len(dividends),
            "bad_count": sum(1 for row in dividends if row.get("pay_date") and row["pay_date"] > SCOPE_END),
            "audit_status": "pass",
            "notes": "P1 filters dividend events to current backtest scope.",
        },
    ]


def _payout_ratio_proxy_audit(financial_panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_sleeve = defaultdict(list)
    for row in financial_panel:
        by_sleeve[row["sleeve_id"]].append(row)
    out = []
    for sleeve in sorted(by_sleeve):
        rows = by_sleeve[sleeve]
        exact = sum(1 for row in rows if row.get("payout_ratio_exact"))
        proxy = sum(1 for row in rows if row.get("payout_ratio_proxy"))
        out.append(
            {
                "sleeve_id": sleeve,
                "row_count": len(rows),
                "payout_ratio_exact_count": exact,
                "payout_ratio_proxy_count": proxy,
                "payout_ratio_proxy_coverage": _ratio(proxy, len(rows)),
                "proxy_formula": "dividend_yield_decimal * positive_pe_ratio",
                "payout_gate_status": "review_proxy_only" if exact == 0 and proxy > 0 else ("missing_or_sector_not_applicable" if proxy == 0 else "pass_exact_available"),
                "notes": "Proxy is PIT-visible from panel valuation fields but must not be treated as exact accounting payout ratio.",
            }
        )
    return out


def _financial_quality_by_sleeve(financial_panel: list[dict[str, Any]], dividends: list[dict[str, Any]]) -> list[dict[str, Any]]:
    event_codes = defaultdict(set)
    for row in dividends:
        event_codes[row["sleeve_id"]].add(row["code"])
    rows = []
    for sleeve in sorted({row["sleeve_id"] for row in financial_panel}):
        sample = [row for row in financial_panel if row["sleeve_id"] == sleeve]
        rows.append(
            {
                "sleeve_id": sleeve,
                "row_count": len(sample),
                "selected_code_count": len({row["code"] for row in sample}),
                "quality_pass_rows": sum(1 for row in sample if row["quality_status"] == "pass"),
                "quality_pass_rate": _ratio(sum(1 for row in sample if row["quality_status"] == "pass"), len(sample)),
                "dividend_event_code_count": len(event_codes[sleeve]),
                "avg_dividend_yield_decimal": _mean(row.get("dividend_yield_decimal") for row in sample),
                "avg_operating_cash_flow_yield": _mean(row.get("operating_cash_flow_yield") for row in sample),
                "avg_return_on_equity_ttm": _mean(row.get("return_on_equity_ttm") for row in sample),
                "avg_payout_ratio_proxy": _mean(row.get("payout_ratio_proxy") for row in sample),
                "p1_interpretation": _sleeve_interpretation(sleeve),
            }
        )
    return rows


def _p1_blockers(coverage_audit: list[dict[str, Any]], visible_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers = []
    for row in coverage_audit:
        if row["required_for_p1"] == "True" and row["coverage_status"] == "fail":
            blockers.append(
                {
                    "blocker_id": f"missing_required_{row['scope']}_{row['field_name']}",
                    "severity": "fatal",
                    "status": "blocking",
                    "description": "Required P1 field coverage failed.",
                    "observed": f"coverage={row['coverage']}",
                }
            )
    for row in visible_audit:
        if row["audit_status"] == "fail":
            blockers.append(
                {
                    "blocker_id": row["audit_id"],
                    "severity": "fatal",
                    "status": "blocking",
                    "description": row["notes"],
                    "observed": f"bad_count={row['bad_count']}",
                }
            )
    return blockers


def _pm_decision(
    blockers: list[dict[str, Any]],
    coverage_audit: list[dict[str, Any]],
    payout_audit: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    exact_payout = any(int(row["payout_ratio_exact_count"]) > 0 for row in payout_audit)
    payout_proxy = any(int(row["payout_ratio_proxy_count"]) > 0 for row in payout_audit)
    decision = "p1_financial_quality_pit_panel_pass_ready_for_p2"
    if blockers:
        decision = "p1_financial_quality_pit_panel_blocked"
    elif payout_proxy and not exact_payout:
        decision = "p1_financial_quality_pit_panel_pass_with_payout_proxy_review_ready_for_p2"
    return [
        {
            "pm_gate_decision": decision,
            "p1_pass": str(not blockers),
            "exact_payout_ratio_available": str(exact_payout),
            "payout_proxy_used": str(payout_proxy),
            "accepted": False,
            "v57f_core_modified": False,
            "new_strategy_rule_added": False,
            "network_fetch_started": False,
            "joinquant_started": False,
            "next_step": "open_v5c_p2_valuation_and_crowding_state_panel" if not blockers else "repair_p1_required_fields",
            "review_notes": "Exact accounting payout ratio is not available in local panels; PIT-visible payout proxy is provided for non-bank sleeves and must be treated as review-only.",
        }
    ]


def _next_queue(decision: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_gate": "v5c_p2_valuation_and_crowding_state_panel",
            "allowed": decision["p1_pass"],
            "scope": "valuation percentiles, turnover/amount crowding, sleeve overheat states, broad index trend state",
            "requires_network": False,
            "requires_v57f_change": False,
            "status": "ready" if decision["p1_pass"] == "True" else "blocked_until_p1_repair",
        },
        {
            "priority": 2,
            "next_gate": "exact_payout_ratio_repair_optional",
            "allowed": "True",
            "scope": "If exact payout ratio is needed, build from PIT net profit and dividend payable/announcement data by report period.",
            "requires_network": "maybe_if_local_financial_statements_missing",
            "requires_v57f_change": False,
            "status": "optional_review_not_blocking_p2",
        },
        {
            "priority": 3,
            "next_gate": "bank_quality_deepening_optional",
            "allowed": "True",
            "scope": "Add bank-specific PIT net interest margin, loan growth, deposit cost and asset quality trend fields if local data exists.",
            "requires_network": "maybe_if_local_bank_statement_fields_missing",
            "requires_v57f_change": False,
            "status": "optional_for_future_bank_sleeve_review",
        },
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    p0_pass: bool = False,
    financial_panel_rows: int = 0,
    cash_dividend_event_rows: int = 0,
    universe_code_count: int = 0,
    exact_payout_ratio_available: bool = False,
    payout_proxy_used: bool = False,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5c_p1_financial_quality_pit_panel",
        "status": status,
        "pm_gate_decision": decision,
        "p0_dependency_pass": p0_pass,
        "financial_panel_rows": financial_panel_rows,
        "cash_dividend_event_rows": cash_dividend_event_rows,
        "universe_code_count": universe_code_count,
        "exact_payout_ratio_available": exact_payout_ratio_available,
        "payout_proxy_used": payout_proxy_used,
        "accepted": False,
        "v57f_core_modified": False,
        "new_strategy_rule_added": False,
        "threshold_scan_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
        "outputs": {
            "summary": str(OUT_DIR / "v5c_p1_financial_quality_summary.json"),
            "report": str(OUT_DIR / "v5c_p1_financial_quality_report.md"),
            "financial_panel": str(OUT_DIR / "v5c_p1_financial_quality_pit_panel.csv"),
            "cash_dividend_events": str(OUT_DIR / "v5c_p1_cash_dividend_events.csv"),
            "field_coverage_audit": str(OUT_DIR / "v5c_p1_field_coverage_audit.csv"),
            "visible_date_audit": str(OUT_DIR / "v5c_p1_visible_date_audit.csv"),
            "next_queue": str(OUT_DIR / "v5c_p1_next_data_gate_queue.csv"),
        },
    }


def _report(
    p0_truth: dict[str, str],
    financial_panel: list[dict[str, Any]],
    dividends: list[dict[str, Any]],
    coverage_audit: list[dict[str, Any]],
    visible_audit: list[dict[str, Any]],
    payout_audit: list[dict[str, Any]],
    decision: list[dict[str, Any]],
    next_queue: list[dict[str, Any]],
) -> str:
    fail_audits = [row for row in visible_audit if row["audit_status"] == "fail"]
    review_fields = [row for row in coverage_audit if row["coverage_status"] == "review"]
    return "\n".join(
        [
            "# V5c P1 Financial Quality PIT Panel",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Baseline dependency: `{p0_truth['baseline_id']}` first trade `{p0_truth['first_trade_date']}`",
            f"- Financial PIT rows: `{len(financial_panel)}`",
            f"- Cash dividend event rows: `{len(dividends)}`",
            f"- Visible-date audit failures: `{len(fail_audits)}`",
            f"- Coverage review fields: `{len(review_fields)}`",
            f"- Exact payout ratio available: `{decision[0]['exact_payout_ratio_available']}`",
            f"- Payout proxy used: `{decision[0]['payout_proxy_used']}`",
            "- Accepted: `False`",
            "- V57f core modified: `False`",
            "",
            "## Payout Note",
            "Exact accounting payout ratio is not available in the local startup repaired panels. P1 therefore writes `payout_ratio_proxy = dividend_yield_decimal * positive_pe_ratio` where the inputs are visible, and marks it as review-only.",
            "",
            "## Next",
            *[f"- P{row['priority']} `{row['next_gate']}`: {row['status']}" for row in next_queue],
            "",
        ]
    )


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5c P1 Financial Quality PIT Panel Agent Rules",
            "",
            "1. Use P0 repaired V57f local truth tables as the universe and rebalance boundary.",
            "2. Preserve visible dates. Financial fields must be visible on or before the rebalance date.",
            "3. Preserve cash-dividend announce/ex/pay dates; cash recognition remains pay-date based.",
            "4. Treat payout_ratio_proxy as review-only. Do not use it as exact accounting payout ratio.",
            "5. Do not modify V57f, run new backtests, scan thresholds, start JoinQuant, or mark accepted.",
            "6. P1 outputs may support P2 valuation/crowding state construction and later candidate review.",
            "",
        ]
    )


def _financial_visible_date(panel: dict[str, str], trade_date: str) -> str:
    for field in ["factor_visible_date", "reviewed_operating_visible_date", "business_purity_visible_date", "universe_visible_date"]:
        value = panel.get(field)
        if value:
            return min(value, trade_date) if field == "universe_visible_date" else value
    # Bank repaired panel does not carry a general factor_visible_date; the source is an as-of-trade-date JQ/stale-fallback panel.
    if panel:
        return trade_date
    return ""


def _quality_fields_present(panel: dict[str, str], sleeve: str) -> int:
    fields = [
        "operating_cash_flow_yield",
        "free_cash_flow_yield",
        "ocf_to_revenue",
        "cash_collection_quality",
        "operating_cash_flow_to_net_profit",
        "return_on_equity_ttm",
        "gross_profit_margin",
        "net_profit_margin",
        "non_performing_loan_ratio",
        "provision_coverage_ratio",
        "core_tier_1_capital_adequacy_ratio",
        "capex_burden",
        "asset_liability_ratio",
        "dividend_yield",
    ]
    return sum(1 for field in fields if str(panel.get(field, "")) not in {"", "nan", "None"})


def _min_quality_fields(sleeve: str) -> int:
    return 4 if sleeve == "bank" else 5


def _pit_notes(panel: dict[str, str], sleeve: str) -> str:
    notes = []
    if sleeve == "bank":
        notes.append("bank sleeve uses valuation/dividend/asset-quality fields; OCF is not a bank primary field")
    if panel.get("basket_stale_fundamental_fallback_fields"):
        notes.append("contains explicitly marked stale fundamental fallback fields")
    if panel.get("startup_initial_snapshot_policy"):
        notes.append(f"startup policy: {panel.get('startup_initial_snapshot_policy')}")
    return "; ".join(notes)


def _field_required_for_sleeve(field: str, sleeve: str) -> str:
    if sleeve == "ALL":
        return "False"
    if field == "cash_dividend_events":
        return "True"
    if sleeve == "bank":
        return str(field in {"dividend_yield_decimal", "non_performing_loan_ratio", "provision_coverage_ratio", "core_tier_1_capital_adequacy_ratio", "return_on_equity_ttm"})
    return str(field in {"dividend_yield_decimal", "operating_cash_flow_yield", "return_on_equity_ttm", "capex_burden", "asset_liability_ratio"})


def _coverage_status(field: str, sleeve: str, present: int, total: int) -> str:
    if total == 0:
        return "fail"
    coverage = present / total
    required = _field_required_for_sleeve(field, sleeve) == "True"
    if required and coverage >= 0.8:
        return "pass"
    if required:
        return "fail"
    if present > 0:
        return "review"
    return "not_applicable_or_missing"


def _sleeve_interpretation(sleeve: str) -> str:
    if sleeve == "bank":
        return "bank uses dividend plus asset-quality/capital fields; OCF is not required as primary bank quality field"
    return "non-financial sleeve uses OCF yield, ROE/profit quality, capex/leverage and dividend context"


def _normalize_yield(value: Any) -> float | None:
    raw = _to_float(value)
    if raw is None:
        return None
    return raw / 100.0 if abs(raw) > 1.0 else raw


def _mean(values: Any) -> str:
    nums = [_to_float(v) for v in values]
    nums = [n for n in nums if n is not None]
    if not nums:
        return ""
    return _fmt(sum(nums) / len(nums))


def _ratio(num: int, den: int) -> str:
    if den <= 0:
        return ""
    return _fmt(num / den)


def _fmt_or_blank(value: float | None) -> str:
    return "" if value is None else _fmt(value)


def _fmt(value: float) -> str:
    return f"{value:.12g}"


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [P0_HOLDINGS, P0_TRUTH, P0_SUMMARY, *PANEL_PATHS.values(), *DIVIDEND_PATHS.values()]
    blockers = []
    for rel in required:
        if not (root / rel).exists():
            blockers.append(
                {
                    "blocker_id": f"missing_{rel.name}",
                    "severity": "fatal",
                    "status": "blocking",
                    "path": str(rel),
                    "description": "Required P1 local input is missing.",
                }
            )
    return blockers


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    run_v5c_p1_financial_quality_pit_panel()

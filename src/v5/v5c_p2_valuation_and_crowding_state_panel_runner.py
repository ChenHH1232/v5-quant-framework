from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5c_p2_valuation_and_crowding_state_panel") / "current"
P0_DIR = Path("v5c_p0_local_data_gate") / "current"
P1_DIR = Path("v5c_p1_financial_quality_pit_panel") / "current"
DB_PROCESSED = Path("\u6570\u636e\u5e93") / "processed"

P0_SUMMARY = P0_DIR / "v5c_p0_local_data_gate_summary.json"
P0_TRUTH = P0_DIR / "v5c_p0_baseline_truth_table.csv"
P0_REBALANCE = P0_DIR / "v5c_p0_rebalance_calendar.csv"
P0_HOLDINGS = P0_DIR / "v5c_p0_rebalance_holdings_targets.csv"
P0_DAILY = P0_DIR / "v5c_p0_daily_nav_returns.csv"
P0_TRADES = P0_DIR / "v5c_p0_trade_cost_audit.csv"

P1_SUMMARY = P1_DIR / "v5c_p1_financial_quality_summary.json"
P1_PANEL = P1_DIR / "v5c_p1_financial_quality_pit_panel.csv"

PANEL_PATHS = {
    "bank": DB_PROCESSED / "startup_preload_repaired_panels_v5" / "bank_v3_repaired" / "panel_with_low_vol.csv",
    "utilities_electricity": DB_PROCESSED / "startup_preload_repaired_panels_v5" / "utilities_v51f" / "panel_with_low_vol.csv",
    "highway_infrastructure": DB_PROCESSED / "startup_preload_repaired_panels_v5" / "highway_v54h" / "panel_with_low_vol.csv",
    "port_rail_infrastructure": DB_PROCESSED / "startup_preload_repaired_panels_v5" / "port_rail_v55j" / "panel_with_low_vol.csv",
}

PRICE_PATHS = {
    "bank": DB_PROCESSED / "startup_preload_repaired_prices_v5" / "bank_v3_startup_repaired_daily_prices.csv",
    "utilities_electricity": DB_PROCESSED / "startup_preload_repaired_prices_v5" / "utilities_v51f_startup_repaired_daily_prices.csv",
    "highway_infrastructure": DB_PROCESSED / "startup_preload_repaired_prices_v5" / "highway_v54h_startup_repaired_daily_prices.csv",
    "port_rail_infrastructure": DB_PROCESSED / "startup_preload_repaired_prices_v5" / "port_rail_v55j_startup_repaired_daily_prices.csv",
}

BENCHMARK_PATHS = {
    "bank": DB_PROCESSED / "startup_warmup_bank_joinquant_real_benchmark_prices.csv",
    "utilities_electricity": DB_PROCESSED / "startup_warmup_utilities_electricity_joinquant_real_benchmark_prices.csv",
    "highway_infrastructure": DB_PROCESSED / "startup_warmup_highway_infrastructure_joinquant_real_benchmark_prices.csv",
    "port_rail_infrastructure": DB_PROCESSED / "startup_warmup_port_rail_infrastructure_joinquant_real_benchmark_prices.csv",
}


def run_v5c_p2_valuation_and_crowding_state_panel(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5c_p2_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "p2_blocked_missing_required_input", blockers)
        _write_json(out / "v5c_p2_valuation_crowding_summary.json", summary)
        return summary

    p0_summary = _read_json(root / P0_SUMMARY)
    p1_summary = _read_json(root / P1_SUMMARY)
    p0_truth = _read_csv(root / P0_TRUTH)[0]
    rebalances = _read_csv(root / P0_REBALANCE)
    holdings = _read_csv(root / P0_HOLDINGS)
    daily = _read_csv(root / P0_DAILY)
    trades = _read_csv(root / P0_TRADES)
    p1_panel = _read_csv(root / P1_PANEL)

    factor_sources = _load_factor_panels(root)
    price_sources = _load_price_sources(root)
    benchmark_sources = _load_benchmark_sources(root)
    source_manifest = _source_manifest(root, factor_sources, price_sources, benchmark_sources)

    valuation_panel = _build_valuation_state_panel(holdings, p1_panel, factor_sources)
    crowding_panel = _build_crowding_state_panel(holdings, trades, price_sources)
    broad_trend = _build_broad_index_trend_state_panel(rebalances, daily)
    sleeve_overheat = _build_sleeve_overheat_state_panel(valuation_panel, crowding_panel, benchmark_sources)
    coverage = _field_coverage_audit(valuation_panel, crowding_panel, broad_trend)
    pit_audit = _pit_leakage_audit(valuation_panel, crowding_panel, broad_trend)
    blockers_out = _p2_blockers(p0_summary, p1_summary, coverage, pit_audit)
    decision = _pm_decision(blockers_out)
    next_queue = _next_queue(decision[0])

    _write_csv(out / "v5c_p2_source_manifest.csv", source_manifest)
    _write_csv(out / "v5c_p2_valuation_state_panel.csv", valuation_panel)
    _write_csv(out / "v5c_p2_crowding_state_panel.csv", crowding_panel)
    _write_csv(out / "v5c_p2_sleeve_overheat_state_panel.csv", sleeve_overheat)
    _write_csv(out / "v5c_p2_broad_index_trend_state_panel.csv", broad_trend)
    _write_csv(out / "v5c_p2_field_coverage_audit.csv", coverage)
    _write_csv(out / "v5c_p2_pit_leakage_audit.csv", pit_audit)
    _write_csv(out / "v5c_p2_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_p2_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5c_p2_blockers.csv", blockers_out)
    (out / "v5c_p2_valuation_crowding_report.md").write_text(
        _report(p0_truth, valuation_panel, crowding_panel, sleeve_overheat, broad_trend, coverage, pit_audit, decision, next_queue),
        encoding="utf-8",
    )
    (out / "v5c_p2_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    summary = _summary(
        "completed_p2_valuation_and_crowding_state_panel",
        decision[0]["pm_gate_decision"],
        blockers_out,
        p0_dependency_pass=bool(p0_summary.get("p0_pass")),
        p1_dependency_pass=bool(p1_summary.get("fatal_blocker_count") == 0),
        valuation_rows=len(valuation_panel),
        crowding_rows=len(crowding_panel),
        sleeve_overheat_rows=len(sleeve_overheat),
        broad_trend_rows=len(broad_trend),
        valuation_overheat_watch_count=sum(1 for row in valuation_panel if row["valuation_state"] == "valuation_overheat_watch"),
        sleeve_overheat_watch_count=sum(1 for row in sleeve_overheat if row["sleeve_overheat_state"] != "normal"),
    )
    _write_json(out / "v5c_p2_valuation_crowding_summary.json", summary)
    return summary


def _load_factor_panels(root: Path) -> dict[str, Any]:
    by_sleeve: dict[str, list[dict[str, str]]] = {}
    by_key: dict[tuple[str, str], dict[str, str]] = {}
    by_code: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_sleeve_date: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for sleeve, rel_path in PANEL_PATHS.items():
        rows = _read_csv(root / rel_path)
        by_sleeve[sleeve] = rows
        for row in rows:
            enriched = row | {"_source_sleeve": sleeve, "_source_path": str(rel_path)}
            by_key[(row.get("trade_date", ""), row.get("code", ""))] = enriched
            by_code[row.get("code", "")].append(enriched)
            by_sleeve_date[(sleeve, row.get("trade_date", ""))].append(enriched)
    for rows in by_code.values():
        rows.sort(key=lambda row: row.get("trade_date", ""))
    return {"by_sleeve": by_sleeve, "by_key": by_key, "by_code": by_code, "by_sleeve_date": by_sleeve_date}


def _load_price_sources(root: Path) -> dict[str, Any]:
    by_code: dict[str, list[dict[str, str]]] = defaultdict(list)
    manifest = []
    for sleeve, rel_path in PRICE_PATHS.items():
        rows = _read_csv(root / rel_path)
        for row in rows:
            row["_source_sleeve"] = sleeve
            row["_source_path"] = str(rel_path)
            by_code[row.get("code", "")].append(row)
        manifest.append({"sleeve_id": sleeve, "path": str(rel_path), "row_count": len(rows)})
    for rows in by_code.values():
        rows.sort(key=lambda row: row.get("date", ""))
    return {"by_code": by_code, "manifest": manifest}


def _load_benchmark_sources(root: Path) -> dict[str, list[dict[str, str]]]:
    out = {}
    for sleeve, rel_path in BENCHMARK_PATHS.items():
        rows = _read_csv(root / rel_path)
        rows.sort(key=lambda row: row.get("date", ""))
        out[sleeve] = rows
    return out


def _build_valuation_state_panel(
    holdings: list[dict[str, str]],
    p1_panel: list[dict[str, str]],
    factor_sources: dict[str, Any],
) -> list[dict[str, Any]]:
    p1_by_key = {(row["trade_date"], row["code"]): row for row in p1_panel}
    factor_by_key = factor_sources["by_key"]
    factor_by_code = factor_sources["by_code"]
    factor_by_sleeve_date = factor_sources["by_sleeve_date"]
    out = []
    for hold in holdings:
        trade_date = hold["trade_date"]
        code = hold["code"]
        sleeve = hold["sleeve_id"]
        factor = factor_by_key.get((trade_date, code), {})
        p1 = p1_by_key.get((trade_date, code), {})
        own_history = [row for row in factor_by_code.get(code, []) if row.get("trade_date", "") <= trade_date]
        sleeve_cross = factor_by_sleeve_date.get((sleeve, trade_date), [])

        pb = _to_float(factor.get("low_price_to_book"))
        pe = _positive_float(factor.get("pe_ratio"))
        dividend = _normalize_yield(factor.get("dividend_yield"))
        ocf = _to_float(factor.get("operating_cash_flow_yield"))
        pb_own = _percentile_score(pb, _values(own_history, "low_price_to_book"), higher_is_better=False)
        pb_cross = _percentile_score(pb, _values(sleeve_cross, "low_price_to_book"), higher_is_better=False)
        pe_own = _percentile_score(pe, _positive_values(own_history, "pe_ratio"), higher_is_better=False)
        pe_cross = _percentile_score(pe, _positive_values(sleeve_cross, "pe_ratio"), higher_is_better=False)
        dividend_own = _percentile_score(dividend, [_normalize_yield(row.get("dividend_yield")) for row in own_history], higher_is_better=True)
        dividend_cross = _percentile_score(dividend, [_normalize_yield(row.get("dividend_yield")) for row in sleeve_cross], higher_is_better=True)
        ocf_own = _percentile_score(ocf, _values(own_history, "operating_cash_flow_yield"), higher_is_better=True)
        ocf_cross = _percentile_score(ocf, _values(sleeve_cross, "operating_cash_flow_yield"), higher_is_better=True)

        cheapness_inputs = [pb_own, pe_own, dividend_own]
        if sleeve != "bank":
            cheapness_inputs.append(ocf_own)
        cheapness = _avg(cheapness_inputs)
        overheat = None if cheapness is None else 1.0 - cheapness
        visible_date = _financial_visible_date(factor, p1, trade_date)
        out.append(
            {
                "trade_date": trade_date,
                "code": code,
                "sleeve_id": sleeve,
                "selected_rank": hold.get("selected_rank", ""),
                "target_weight_signal": hold.get("target_weight_signal", ""),
                "actual_weight": hold.get("actual_weight", ""),
                "source_panel_path": factor.get("_source_path", ""),
                "panel_join_status": "matched" if factor else "missing_panel_row",
                "financial_visible_date": visible_date,
                "visible_date_status": "pass" if visible_date and visible_date <= trade_date else "fail",
                "low_price_to_book": _fmt_or_blank(pb),
                "pe_ratio": _fmt_or_blank(pe),
                "dividend_yield_decimal": _fmt_or_blank(dividend),
                "operating_cash_flow_yield": _fmt_or_blank(ocf),
                "return_on_equity_ttm": factor.get("return_on_equity_ttm", ""),
                "payout_ratio_proxy": p1.get("payout_ratio_proxy", ""),
                "pb_cheapness_percentile_own_history": _fmt_or_blank(pb_own),
                "pb_cheapness_percentile_sleeve_cross_section": _fmt_or_blank(pb_cross),
                "pe_cheapness_percentile_own_history": _fmt_or_blank(pe_own),
                "pe_cheapness_percentile_sleeve_cross_section": _fmt_or_blank(pe_cross),
                "dividend_support_percentile_own_history": _fmt_or_blank(dividend_own),
                "dividend_support_percentile_sleeve_cross_section": _fmt_or_blank(dividend_cross),
                "ocf_support_percentile_own_history": _fmt_or_blank(ocf_own),
                "ocf_support_percentile_sleeve_cross_section": _fmt_or_blank(ocf_cross),
                "valuation_cheapness_score": _fmt_or_blank(cheapness),
                "valuation_overheat_score": _fmt_or_blank(overheat),
                "valuation_state": _valuation_state(overheat),
                "pit_status": "pass" if visible_date and visible_date <= trade_date else "fail",
                "notes": "bank sleeve excludes OCF from composite" if sleeve == "bank" else "non-bank composite includes PB, PE, dividend yield and OCF yield",
            }
        )
    return out


def _build_crowding_state_panel(
    holdings: list[dict[str, str]],
    trades: list[dict[str, str]],
    price_sources: dict[str, Any],
) -> list[dict[str, Any]]:
    trade_value = defaultdict(float)
    trade_count = defaultdict(int)
    for row in trades:
        key = (row.get("trade_date", ""), row.get("code", ""))
        value = _to_float(row.get("value")) or 0.0
        trade_value[key] += abs(value)
        trade_count[key] += 1
    prices_by_code = price_sources["by_code"]
    out = []
    for hold in holdings:
        trade_date = hold["trade_date"]
        code = hold["code"]
        price_rows = prices_by_code.get(code, [])
        idx = _last_index_before(price_rows, trade_date)
        if idx is None:
            out.append(_missing_crowding_row(hold))
            continue
        asof = price_rows[idx]
        history = price_rows[: idx + 1]
        money = _to_float(asof.get("money"))
        volume = _to_float(asof.get("volume"))
        avg20 = _avg(_to_float(row.get("money")) for row in history[-20:])
        avg60 = _avg(_to_float(row.get("money")) for row in history[-60:])
        money_pctile = _percentile_score(money, [_to_float(row.get("money")) for row in history[-252:]], higher_is_better=True)
        close = _to_float(asof.get("close"))
        ret20 = _return_from_history(history, idx, 20)
        ret60 = _return_from_history(history, idx, 60)
        order_value = trade_value[(trade_date, code)]
        order_to_avg20 = order_value / avg20 if avg20 and avg20 > 0 else None
        out.append(
            {
                "trade_date": trade_date,
                "state_asof_date": asof.get("date", ""),
                "code": code,
                "sleeve_id": hold["sleeve_id"],
                "source_price_path": asof.get("_source_path", ""),
                "price_join_status": "matched",
                "close_asof": _fmt_or_blank(close),
                "money_asof": _fmt_or_blank(money),
                "volume_asof": _fmt_or_blank(volume),
                "avg_money_20d": _fmt_or_blank(avg20),
                "avg_money_60d": _fmt_or_blank(avg60),
                "money_percentile_252d": _fmt_or_blank(money_pctile),
                "price_return_20d": _fmt_or_blank(ret20),
                "price_return_60d": _fmt_or_blank(ret60),
                "p0_rebalance_order_value": _fmt(order_value),
                "p0_rebalance_trade_count": trade_count[(trade_date, code)],
                "order_value_to_avg20_money": _fmt_or_blank(order_to_avg20),
                "crowding_state": _crowding_state(order_to_avg20, money_pctile),
                "pit_status": "pass" if asof.get("date", "") < trade_date else "fail",
                "notes": "uses previous trading day's money/volume before rebalance date",
            }
        )
    return out


def _build_sleeve_overheat_state_panel(
    valuation_panel: list[dict[str, Any]],
    crowding_panel: list[dict[str, Any]],
    benchmark_sources: dict[str, list[dict[str, str]]],
) -> list[dict[str, Any]]:
    valuation_by_group = defaultdict(list)
    crowding_by_group = defaultdict(list)
    for row in valuation_panel:
        valuation_by_group[(row["trade_date"], row["sleeve_id"])].append(row)
    for row in crowding_panel:
        crowding_by_group[(row["trade_date"], row["sleeve_id"])].append(row)
    out = []
    for key in sorted(valuation_by_group):
        trade_date, sleeve = key
        valuations = valuation_by_group[key]
        crowd = crowding_by_group.get(key, [])
        benchmark_rows = benchmark_sources.get(sleeve, [])
        idx = _last_index_before_benchmark(benchmark_rows, trade_date)
        benchmark_asof = benchmark_rows[idx] if idx is not None else {}
        benchmark_return_20d = _benchmark_return(benchmark_rows, idx, 20)
        benchmark_return_60d = _benchmark_return(benchmark_rows, idx, 60)
        avg_overheat = _avg(_to_float(row.get("valuation_overheat_score")) for row in valuations)
        avg_money_pctile = _avg(_to_float(row.get("money_percentile_252d")) for row in crowd)
        total_order = sum(_to_float(row.get("p0_rebalance_order_value")) or 0.0 for row in crowd)
        total_avg20 = sum(_to_float(row.get("avg_money_20d")) or 0.0 for row in crowd)
        sleeve_order_to_money = total_order / total_avg20 if total_avg20 > 0 else None
        overheat_names = [row["code"] for row in valuations if row["valuation_state"] == "valuation_overheat_watch"]
        state = _sleeve_overheat_state(avg_overheat, avg_money_pctile, benchmark_return_60d)
        out.append(
            {
                "trade_date": trade_date,
                "sleeve_id": sleeve,
                "holding_count": len(valuations),
                "benchmark_state_asof_date": benchmark_asof.get("date", ""),
                "avg_valuation_overheat_score": _fmt_or_blank(avg_overheat),
                "valuation_overheat_watch_count": len(overheat_names),
                "valuation_overheat_watch_codes": ";".join(overheat_names),
                "avg_money_percentile_252d": _fmt_or_blank(avg_money_pctile),
                "total_order_value": _fmt(total_order),
                "total_avg_money_20d": _fmt(total_avg20),
                "sleeve_order_value_to_avg20_money": _fmt_or_blank(sleeve_order_to_money),
                "sleeve_benchmark_return_20d": _fmt_or_blank(benchmark_return_20d),
                "sleeve_benchmark_return_60d": _fmt_or_blank(benchmark_return_60d),
                "sleeve_overheat_state": state,
                "pit_status": "pass" if benchmark_asof.get("date", "") < trade_date else "fail",
                "notes": "diagnostic state only; no defense, profit-taking, or reweighting rule is admitted",
            }
        )
    return out


def _build_broad_index_trend_state_panel(
    rebalances: list[dict[str, str]],
    daily: list[dict[str, str]],
) -> list[dict[str, Any]]:
    daily = sorted(daily, key=lambda row: row.get("trade_date", ""))
    out = []
    for rebalance in rebalances:
        trade_date = rebalance["rebalance_date"]
        idx = _last_daily_index_before(daily, trade_date)
        if idx is None:
            out.append(
                {
                    "rebalance_date": trade_date,
                    "state_asof_date": "",
                    "benchmark_return_20d": "",
                    "benchmark_return_60d": "",
                    "benchmark_return_120d": "",
                    "benchmark_drawdown_60d": "",
                    "benchmark_nav_asof": "",
                    "benchmark_nav_ma60": "",
                    "broad_trend_state": "initial_rebalance_no_prior_baseline_nav",
                    "pit_status": "review_initial_rebalance_no_prior_baseline_nav",
                }
            )
            continue
        asof = daily[idx]
        nav = _to_float(asof.get("benchmark_nav"))
        ret20 = _nav_return(daily, idx, 20)
        ret60 = _nav_return(daily, idx, 60)
        ret120 = _nav_return(daily, idx, 120)
        ma60 = _avg(_to_float(row.get("benchmark_nav")) for row in daily[max(0, idx - 59) : idx + 1])
        dd60 = _drawdown(daily[max(0, idx - 59) : idx + 1], "benchmark_nav")
        out.append(
            {
                "rebalance_date": trade_date,
                "state_asof_date": asof.get("trade_date", ""),
                "benchmark_return_20d": _fmt_or_blank(ret20),
                "benchmark_return_60d": _fmt_or_blank(ret60),
                "benchmark_return_120d": _fmt_or_blank(ret120),
                "benchmark_drawdown_60d": _fmt_or_blank(dd60),
                "benchmark_nav_asof": _fmt_or_blank(nav),
                "benchmark_nav_ma60": _fmt_or_blank(ma60),
                "broad_trend_state": _broad_trend_state(nav, ma60, ret60),
                "pit_status": "pass" if asof.get("trade_date", "") < trade_date else "fail",
            }
        )
    return out


def _field_coverage_audit(
    valuation_panel: list[dict[str, Any]],
    crowding_panel: list[dict[str, Any]],
    broad_trend: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    checks = [
        ("valuation", "panel_join_status", len(valuation_panel), sum(1 for row in valuation_panel if row["panel_join_status"] == "matched"), True),
        ("valuation", "low_price_to_book", len(valuation_panel), _present_count(valuation_panel, "low_price_to_book"), True),
        ("valuation", "dividend_yield_decimal", len(valuation_panel), _present_count(valuation_panel, "dividend_yield_decimal"), True),
        ("valuation", "valuation_cheapness_score", len(valuation_panel), _present_count(valuation_panel, "valuation_cheapness_score"), True),
        ("crowding", "price_join_status", len(crowding_panel), sum(1 for row in crowding_panel if row["price_join_status"] == "matched"), True),
        ("crowding", "money_asof", len(crowding_panel), _present_count(crowding_panel, "money_asof"), True),
        ("crowding", "avg_money_20d", len(crowding_panel), _present_count(crowding_panel, "avg_money_20d"), True),
        ("crowding", "order_value_to_avg20_money", len(crowding_panel), _present_count(crowding_panel, "order_value_to_avg20_money"), False),
        ("broad_trend", "benchmark_nav_asof", len(broad_trend), _present_count(broad_trend, "benchmark_nav_asof"), True),
        ("broad_trend", "benchmark_return_60d", len(broad_trend), _present_count(broad_trend, "benchmark_return_60d"), False),
    ]
    for scope, field, total, present, required in checks:
        coverage = present / total if total else 0.0
        status = "pass" if (coverage >= 0.95 if required else coverage > 0.0) else ("fail" if required else "review")
        rows.append(
            {
                "scope": scope,
                "field_name": field,
                "row_count": total,
                "present_count": present,
                "coverage": _fmt(coverage),
                "required_for_p2": required,
                "coverage_status": status,
            }
        )
    return rows


def _pit_leakage_audit(
    valuation_panel: list[dict[str, Any]],
    crowding_panel: list[dict[str, Any]],
    broad_trend: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    valuation_bad = [row for row in valuation_panel if row["pit_status"] != "pass"]
    crowding_bad = [row for row in crowding_panel if row["pit_status"] != "pass"]
    broad_bad = [row for row in broad_trend if row["pit_status"] == "fail"]
    return [
        {
            "audit_id": "valuation_visible_date_lte_rebalance_date",
            "row_count": len(valuation_panel),
            "bad_count": len(valuation_bad),
            "audit_status": "pass" if not valuation_bad else "fail",
            "notes": "Financial and valuation fields must be visible on or before rebalance date.",
        },
        {
            "audit_id": "crowding_uses_prior_trading_day_money_volume",
            "row_count": len(crowding_panel),
            "bad_count": len(crowding_bad),
            "audit_status": "pass" if not crowding_bad else "fail",
            "notes": "Money/volume crowding state uses the last local daily price strictly before rebalance date.",
        },
        {
            "audit_id": "broad_trend_uses_prior_daily_nav",
            "row_count": len(broad_trend),
            "bad_count": len(broad_bad),
            "audit_status": "pass" if not broad_bad else "fail",
            "notes": "Broad trend state uses repaired baseline benchmark NAV strictly before rebalance date.",
        },
    ]


def _p2_blockers(
    p0_summary: dict[str, Any],
    p1_summary: dict[str, Any],
    coverage: list[dict[str, Any]],
    pit_audit: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    blockers = []
    if not p0_summary.get("p0_pass"):
        blockers.append(_blocker("p0_dependency_not_pass", "P0 repaired baseline local data gate is not passed."))
    if p1_summary.get("fatal_blocker_count") not in (0, "0"):
        blockers.append(_blocker("p1_dependency_has_fatal_blockers", "P1 financial quality PIT panel has fatal blockers."))
    for row in coverage:
        if row["required_for_p2"] == "True" and row["coverage_status"] == "fail":
            blockers.append(_blocker(f"coverage_failed_{row['scope']}_{row['field_name']}", f"P2 required coverage failed: {row['coverage']}"))
    for row in pit_audit:
        if row["audit_status"] == "fail":
            blockers.append(_blocker(row["audit_id"], row["notes"]))
    return blockers


def _pm_decision(blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    decision = "p2_valuation_crowding_state_panel_pass_ready_for_v5c_p3_state_governance_spec"
    if blockers:
        decision = "p2_valuation_crowding_state_panel_blocked"
    return [
        {
            "pm_gate_decision": decision,
            "p2_pass": str(not blockers),
            "accepted": False,
            "v57f_core_modified": False,
            "new_strategy_rule_added": False,
            "threshold_scan_used": False,
            "network_fetch_started": False,
            "joinquant_started": False,
            "next_step": "open_v5c_p3_state_governance_quant_spec" if not blockers else "repair_p2_required_inputs",
            "review_notes": "P2 builds diagnostic PIT state panels only; it does not admit any overheat, defense, profit-taking, or reweighting rule.",
        }
    ]


def _next_queue(decision: dict[str, Any]) -> list[dict[str, Any]]:
    allowed = decision["p2_pass"]
    return [
        {
            "priority": 1,
            "next_gate": "v5c_p3_state_governance_quant_spec",
            "allowed": allowed,
            "scope": "Convert P2 valuation/crowding/overheat states into a PM-reviewed diagnostic spec; no trading rule admitted.",
            "requires_network": False,
            "requires_v57f_change": False,
            "status": "ready" if allowed == "True" else "blocked_until_p2_repair",
        },
        {
            "priority": 2,
            "next_gate": "v5c_p2_market_crowding_deepening_optional",
            "allowed": "True",
            "scope": "Optional: deepen liquidity/crowding with free-float turnover or shareholder flow if local PIT fields exist.",
            "requires_network": "maybe_if_local_fields_missing",
            "requires_v57f_change": False,
            "status": "optional_not_blocking_p3",
        },
        {
            "priority": 3,
            "next_gate": "v5c_p3_overheat_overlay_backtest_requires_separate_approval",
            "allowed": "False",
            "scope": "Engineering backtest of any overheat/defense action requires a separate approval and fixed spec.",
            "requires_network": False,
            "requires_v57f_change": False,
            "status": "blocked_by_governance_until_spec_approved",
        },
    ]


def _summary(
    status: str,
    decision: str,
    blockers: list[dict[str, Any]],
    p0_dependency_pass: bool = False,
    p1_dependency_pass: bool = False,
    valuation_rows: int = 0,
    crowding_rows: int = 0,
    sleeve_overheat_rows: int = 0,
    broad_trend_rows: int = 0,
    valuation_overheat_watch_count: int = 0,
    sleeve_overheat_watch_count: int = 0,
) -> dict[str, Any]:
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5c_p2_valuation_and_crowding_state_panel",
        "status": status,
        "pm_gate_decision": decision,
        "p0_dependency_pass": p0_dependency_pass,
        "p1_dependency_pass": p1_dependency_pass,
        "valuation_rows": valuation_rows,
        "crowding_rows": crowding_rows,
        "sleeve_overheat_rows": sleeve_overheat_rows,
        "broad_trend_rows": broad_trend_rows,
        "valuation_overheat_watch_count": valuation_overheat_watch_count,
        "sleeve_overheat_watch_count": sleeve_overheat_watch_count,
        "accepted": False,
        "v57f_core_modified": False,
        "new_strategy_rule_added": False,
        "threshold_scan_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(blockers),
        "fatal_blockers": blockers,
        "outputs": {
            "summary": str(OUT_DIR / "v5c_p2_valuation_crowding_summary.json"),
            "report": str(OUT_DIR / "v5c_p2_valuation_crowding_report.md"),
            "valuation_state_panel": str(OUT_DIR / "v5c_p2_valuation_state_panel.csv"),
            "crowding_state_panel": str(OUT_DIR / "v5c_p2_crowding_state_panel.csv"),
            "sleeve_overheat_state_panel": str(OUT_DIR / "v5c_p2_sleeve_overheat_state_panel.csv"),
            "broad_index_trend_state_panel": str(OUT_DIR / "v5c_p2_broad_index_trend_state_panel.csv"),
            "next_queue": str(OUT_DIR / "v5c_p2_next_agent_queue.csv"),
        },
    }


def _source_manifest(root: Path, factor_sources: dict[str, Any], price_sources: dict[str, Any], benchmark_sources: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    rows = [
        {"source_id": "p0_summary", "source_type": "p0_repaired_baseline_gate", "path": str(P0_SUMMARY), "row_count": 1, "p2_role": "dependency"},
        {"source_id": "p1_panel", "source_type": "p1_financial_quality_pit_panel", "path": str(P1_PANEL), "row_count": len(_read_csv(root / P1_PANEL)), "p2_role": "selected financial rows"},
    ]
    for sleeve, rel_path in PANEL_PATHS.items():
        rows.append(
            {
                "source_id": f"factor_panel_{sleeve}",
                "source_type": "startup_preload_repaired_factor_panel",
                "path": str(rel_path),
                "row_count": len(factor_sources["by_sleeve"].get(sleeve, [])),
                "p2_role": "valuation percentile history",
            }
        )
    for item in price_sources["manifest"]:
        rows.append(
            {
                "source_id": f"daily_price_{item['sleeve_id']}",
                "source_type": "startup_preload_repaired_daily_price",
                "path": item["path"],
                "row_count": item["row_count"],
                "p2_role": "money volume crowding state",
            }
        )
    for sleeve, rows_in in benchmark_sources.items():
        rows.append(
            {
                "source_id": f"sleeve_benchmark_{sleeve}",
                "source_type": "startup_warmup_sleeve_benchmark_price",
                "path": str(BENCHMARK_PATHS[sleeve]),
                "row_count": len(rows_in),
                "p2_role": "sleeve price trend context",
            }
        )
    return rows


def _report(
    p0_truth: dict[str, str],
    valuation_panel: list[dict[str, Any]],
    crowding_panel: list[dict[str, Any]],
    sleeve_overheat: list[dict[str, Any]],
    broad_trend: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    pit_audit: list[dict[str, Any]],
    decision: list[dict[str, Any]],
    next_queue: list[dict[str, Any]],
) -> str:
    coverage_fail = [row for row in coverage if row["coverage_status"] == "fail"]
    pit_fail = [row for row in pit_audit if row["audit_status"] == "fail"]
    overheat = [row for row in sleeve_overheat if row["sleeve_overheat_state"] != "normal"]
    return "\n".join(
        [
            "# V5c P2 Valuation And Crowding State Panel",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Baseline: `{p0_truth['baseline_id']}` first trade `{p0_truth['first_trade_date']}`",
            f"- Valuation rows: `{len(valuation_panel)}`",
            f"- Crowding rows: `{len(crowding_panel)}`",
            f"- Sleeve overheat rows: `{len(sleeve_overheat)}`",
            f"- Broad trend rows: `{len(broad_trend)}`",
            f"- Coverage failures: `{len(coverage_fail)}`",
            f"- PIT failures: `{len(pit_fail)}`",
            f"- Sleeve overheat/watch rows: `{len(overheat)}`",
            "- Accepted: `False`",
            "- V57f core modified: `False`",
            "",
            "## Scope",
            "P2 is a PIT data/state panel. It does not admit any defense, profit-taking, reweighting, or overheat trading rule.",
            "",
            "## Next",
            *[f"- P{row['priority']} `{row['next_gate']}`: {row['status']}" for row in next_queue],
            "",
        ]
    )


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5c P2 Agent Execution Rules",
            "",
            "1. Use repaired V57f P0 and P1 as the only universe and baseline dependency.",
            "2. Valuation fields must be PIT-visible on or before the rebalance date.",
            "3. Money/volume and broad trend states must use only dates strictly before the rebalance date.",
            "4. P2 outputs are diagnostic state panels only.",
            "5. Do not modify V57f, run backtests, scan thresholds, start JoinQuant, fetch network data, or mark accepted.",
            "",
        ]
    )


def _missing_crowding_row(hold: dict[str, str]) -> dict[str, Any]:
    return {
        "trade_date": hold["trade_date"],
        "state_asof_date": "",
        "code": hold["code"],
        "sleeve_id": hold["sleeve_id"],
        "source_price_path": "",
        "price_join_status": "missing_price_history",
        "close_asof": "",
        "money_asof": "",
        "volume_asof": "",
        "avg_money_20d": "",
        "avg_money_60d": "",
        "money_percentile_252d": "",
        "price_return_20d": "",
        "price_return_60d": "",
        "p0_rebalance_order_value": "",
        "p0_rebalance_trade_count": "",
        "order_value_to_avg20_money": "",
        "crowding_state": "missing_price_history",
        "pit_status": "fail",
        "notes": "No local repaired price row before rebalance date.",
    }


def _financial_visible_date(factor: dict[str, str], p1: dict[str, str], trade_date: str) -> str:
    if p1.get("financial_visible_date"):
        return p1["financial_visible_date"]
    for field in ["factor_visible_date", "reviewed_operating_visible_date", "business_purity_visible_date", "universe_visible_date"]:
        value = factor.get(field)
        if value:
            return min(value, trade_date) if field == "universe_visible_date" else value
    return trade_date if factor else ""


def _valuation_state(overheat: float | None) -> str:
    if overheat is None:
        return "review_missing_valuation_score"
    if overheat >= 0.75:
        return "valuation_overheat_watch"
    if overheat <= 0.25:
        return "valuation_cheap_support"
    return "neutral"


def _crowding_state(order_to_avg20: float | None, money_pctile: float | None) -> str:
    if order_to_avg20 is None and money_pctile is None:
        return "review_missing_crowding_inputs"
    states = []
    if order_to_avg20 is not None and order_to_avg20 >= 0.05:
        states.append("rebalance_liquidity_pressure_watch")
    if money_pctile is not None and money_pctile >= 0.9:
        states.append("market_attention_hot")
    if money_pctile is not None and money_pctile <= 0.1:
        states.append("market_attention_cold")
    return ";".join(states) if states else "normal"


def _sleeve_overheat_state(avg_overheat: float | None, avg_money_pctile: float | None, benchmark_return_60d: float | None) -> str:
    if avg_overheat is None:
        return "review_missing_state_inputs"
    hot_value = avg_overheat >= 0.65
    hot_flow = avg_money_pctile is not None and avg_money_pctile >= 0.70
    hot_price = benchmark_return_60d is not None and benchmark_return_60d >= 0.08
    stress_price = benchmark_return_60d is not None and benchmark_return_60d <= -0.08
    if hot_value and hot_flow and hot_price:
        return "valuation_price_flow_overheat_watch"
    if hot_value:
        return "valuation_overheat_watch"
    if stress_price:
        return "cooldown_or_stress_watch"
    return "normal"


def _broad_trend_state(nav: float | None, ma60: float | None, ret60: float | None) -> str:
    if nav is None or ma60 is None or ret60 is None:
        return "review_insufficient_history"
    if ret60 > 0 and nav >= ma60:
        return "uptrend"
    if ret60 < 0 and nav < ma60:
        return "downtrend"
    return "neutral"


def _last_index_before(rows: list[dict[str, str]], trade_date: str) -> int | None:
    found = None
    for idx, row in enumerate(rows):
        if row.get("date", "") < trade_date:
            found = idx
        else:
            break
    return found


def _last_index_before_benchmark(rows: list[dict[str, str]], trade_date: str) -> int | None:
    return _last_index_before(rows, trade_date)


def _last_daily_index_before(rows: list[dict[str, str]], trade_date: str) -> int | None:
    found = None
    for idx, row in enumerate(rows):
        if row.get("trade_date", "") < trade_date:
            found = idx
        else:
            break
    return found


def _return_from_history(rows: list[dict[str, str]], idx: int, lookback: int) -> float | None:
    if idx - lookback < 0:
        return None
    current = _to_float(rows[idx].get("close"))
    past = _to_float(rows[idx - lookback].get("close"))
    if current is None or past is None or past == 0:
        return None
    return current / past - 1.0


def _benchmark_return(rows: list[dict[str, str]], idx: int | None, lookback: int) -> float | None:
    if idx is None or idx - lookback < 0:
        return None
    current = _to_float(rows[idx].get("close"))
    past = _to_float(rows[idx - lookback].get("close"))
    if current is None or past is None or past == 0:
        return None
    return current / past - 1.0


def _nav_return(rows: list[dict[str, str]], idx: int, lookback: int) -> float | None:
    if idx - lookback < 0:
        return None
    current = _to_float(rows[idx].get("benchmark_nav"))
    past = _to_float(rows[idx - lookback].get("benchmark_nav"))
    if current is None or past is None or past == 0:
        return None
    return current / past - 1.0


def _drawdown(rows: list[dict[str, str]], field: str) -> float | None:
    peak = None
    max_dd = 0.0
    for row in rows:
        value = _to_float(row.get(field))
        if value is None:
            continue
        peak = value if peak is None else max(peak, value)
        if peak > 0:
            max_dd = min(max_dd, value / peak - 1.0)
    return max_dd


def _values(rows: list[dict[str, str]], field: str) -> list[float | None]:
    return [_to_float(row.get(field)) for row in rows]


def _positive_values(rows: list[dict[str, str]], field: str) -> list[float | None]:
    return [_positive_float(row.get(field)) for row in rows]


def _percentile_score(value: float | None, sample: list[float | None], higher_is_better: bool) -> float | None:
    clean = [item for item in sample if item is not None]
    if value is None or not clean:
        return None
    if higher_is_better:
        return sum(1 for item in clean if item <= value) / len(clean)
    return sum(1 for item in clean if item >= value) / len(clean)


def _present_count(rows: list[dict[str, Any]], field: str) -> int:
    return sum(1 for row in rows if str(row.get(field, "")) not in {"", "nan", "None"})


def _blocker(blocker_id: str, description: str) -> dict[str, Any]:
    return {"blocker_id": blocker_id, "severity": "fatal", "status": "blocking", "description": description}


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        P0_SUMMARY,
        P0_TRUTH,
        P0_REBALANCE,
        P0_HOLDINGS,
        P0_DAILY,
        P0_TRADES,
        P1_SUMMARY,
        P1_PANEL,
        *PANEL_PATHS.values(),
        *PRICE_PATHS.values(),
        *BENCHMARK_PATHS.values(),
    ]
    blockers = []
    for rel in required:
        if not (root / rel).exists():
            blockers.append(
                {
                    "blocker_id": f"missing_{rel.name}",
                    "severity": "fatal",
                    "status": "blocking",
                    "path": str(rel),
                    "description": "Required P2 local input is missing.",
                }
            )
    return blockers


def _normalize_yield(value: Any) -> float | None:
    raw = _to_float(value)
    if raw is None:
        return None
    return raw / 100.0 if abs(raw) > 1.0 else raw


def _positive_float(value: Any) -> float | None:
    num = _to_float(value)
    if num is None or num <= 0:
        return None
    return num


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _avg(values: Any) -> float | None:
    nums = [_to_float(value) for value in values]
    nums = [num for num in nums if num is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)


def _fmt_or_blank(value: float | None) -> str:
    return "" if value is None else _fmt(value)


def _fmt(value: float) -> str:
    return f"{value:.12g}"


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
    run_v5c_p2_valuation_and_crowding_state_panel()

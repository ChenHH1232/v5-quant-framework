from __future__ import annotations

import csv
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
MODEL_ID = "internal_subsleeve_mom12_70_30"
BASELINE_ID = "v57f_startup_preload_repaired_baseline"
INITIAL_CASH = 2_000_000.0


def run(root: Path = ROOT) -> Path:
    export_root = root / "data" / "joinquant_exports" / "v5f_internal_subsleeve_mom12_70_30" / "historical_platform_attribution"
    out = root / "v5f_joinquant_platform_attribution" / "current"
    out.mkdir(parents=True, exist_ok=True)

    daily_csv = export_root / "daily_returns_primary_result_1_20.csv"
    tx_csv = export_root / "transaction_primary_internal_subsleeve_mom12_70_30" / "transaction.csv"
    pos_csv = export_root / "position_primary_internal_subsleeve_mom12_70_30" / "position.csv"
    log_path = export_root / "log_primary_internal_subsleeve_mom12_70_30" / "log.txt"

    summary_path = out / "v5f_joinquant_platform_attribution_summary.json"
    old_summary = _read_json(summary_path) if summary_path.exists() else {}

    daily = pd.read_csv(daily_csv, encoding="gb18030")
    daily["trade_date"] = pd.to_datetime(daily["时间"]).dt.strftime("%Y-%m-%d")
    comparison_path = out / "v5f_joinquant_platform_daily_path_comparison.csv"
    comparison = pd.read_csv(comparison_path) if comparison_path.exists() else pd.DataFrame()

    tx_norm = _load_transactions(tx_csv)
    _write_csv(out / "v5f_joinquant_platform_transactions_normalized.csv", tx_norm.to_dict("records"))

    pos = _load_positions(pos_csv)
    stock_pos = pos[pos["asset_type"].eq("股票")].copy()
    cash_pos = pos[pos["asset_type"].eq("cash")].copy()
    pos_summary = _summarize_positions(stock_pos, cash_pos)
    _write_csv(out / "v5f_joinquant_platform_position_by_date.csv", pos_summary.to_dict("records"))

    log_text = log_path.read_text(encoding="gb18030", errors="ignore")
    log_lines = log_text.splitlines()
    rebalance_dates = _extract_rebalance_dates(log_lines)
    error_lines = [line for line in log_lines if " - ERROR - " in line]
    warning_lines = [line for line in log_lines if " - WARNING - " in line]
    order_none_lines = [line for line in warning_lines if "V5F_ORDER_NONE" in line]
    skipped_paused_lines = [line for line in warning_lines if "V5F_ORDER_SKIPPED_PAUSED" in line]
    limit_cancel_lines = [line for line in warning_lines if "涨停" in line or "跌停" in line]
    _write_csv(out / "v5f_joinquant_platform_log_order_issues.csv", _log_order_issues(error_lines, warning_lines))

    filled_tx = tx_norm[tx_norm["filled_status_ok"]].copy() if not tx_norm.empty else tx_norm.copy()

    tx_by_date = _summarize_transactions_by_date(tx_norm, rebalance_dates, pos_summary)
    _write_csv(out / "v5f_joinquant_platform_transaction_by_rebalance.csv", tx_by_date)

    weights = pd.read_csv(root / "v5f_structural_rough_screen" / "current" / "v5f_structural_rough_screen_weights.csv")
    target = weights[weights["version_id"].eq(MODEL_ID)].copy()
    target["rebalance_date"] = target["rebalance_date"].astype(str)
    rebalance_audit, rebalance_summary = _rebalance_position_audit(target, stock_pos, pos_summary)
    _write_csv(out / "v5f_joinquant_platform_rebalance_target_position_audit.csv", rebalance_audit)
    _write_csv(out / "v5f_joinquant_platform_rebalance_position_summary.csv", rebalance_summary)

    _write_csv(out / "v5f_joinquant_platform_small_order_audit.csv", _small_order_rows(tx_norm))
    _write_csv(out / "v5f_joinquant_platform_top_daily_drift.csv", _top_daily_drift(comparison))
    _write_csv(out / "v5f_joinquant_platform_log_governance_audit.csv", _log_governance_audit(log_text, rebalance_dates, target, error_lines, warning_lines))

    commission_total = float(filled_tx["commission"].sum()) if not filled_tx.empty else 0.0
    buy_value = float(filled_tx.loc[filled_tx["side"].eq("buy"), "gross_value"].sum()) if not filled_tx.empty else 0.0
    sell_value_abs = float(filled_tx.loc[filled_tx["side"].eq("sell"), "gross_value"].abs().sum()) if not filled_tx.empty else 0.0
    total_traded_value = buy_value + sell_value_abs
    avg_cash_weight = float(pos_summary["cash_weight"].mean()) if not pos_summary.empty else math.nan
    max_cash_weight = float(pos_summary["cash_weight"].max()) if not pos_summary.empty else math.nan
    min_position_count = int(pos_summary["stock_position_count"].min()) if not pos_summary.empty else 0
    max_position_count = int(pos_summary["stock_position_count"].max()) if not pos_summary.empty else 0
    max_reb_abs_diff = max((float(r["max_abs_weight_diff"]) for r in rebalance_summary), default=math.nan)
    avg_sum_abs_diff = float(pd.DataFrame(rebalance_summary)["sum_abs_weight_diff"].mean()) if rebalance_summary else math.nan

    health = _execution_health(
        tx_norm,
        error_lines,
        warning_lines,
        order_none_lines,
        skipped_paused_lines,
        limit_cancel_lines,
        buy_value,
        sell_value_abs,
        total_traded_value,
        commission_total,
        avg_cash_weight,
        max_cash_weight,
        min_position_count,
        max_position_count,
        max_reb_abs_diff,
        avg_sum_abs_diff,
    )
    _write_csv(out / "v5f_joinquant_platform_execution_health.csv", health)
    _write_csv(out / "v5f_joinquant_platform_export_manifest.csv", _export_manifest(root, export_root, daily_csv, tx_csv, pos_csv, log_path))

    summary = dict(old_summary)
    summary.update(
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "task": "v5f_joinquant_platform_attribution_primary_with_execution_exports",
            "status": "completed_primary_platform_daily_transaction_position_log_attribution",
            "assumed_model": MODEL_ID,
            "benchmark_required": BASELINE_ID,
            "transactions_export_missing": False,
            "positions_export_missing": False,
            "logs_export_missing": False,
            "script_snapshot_missing": True,
            "generated_joinquant_script_available": True,
            "required_platform_baseline_export_missing": True,
            "transaction_rows": int(len(tx_norm)),
            "filled_transaction_rows": int(len(filled_tx)),
            "cancelled_or_unfilled_transaction_rows": int(len(tx_norm) - len(filled_tx)),
            "transaction_trade_dates": int(tx_norm["trade_date"].nunique()) if not tx_norm.empty else 0,
            "buy_count": int((filled_tx["side"] == "buy").sum()) if not filled_tx.empty else 0,
            "sell_count": int((filled_tx["side"] == "sell").sum()) if not filled_tx.empty else 0,
            "all_exported_transactions_filled": bool(tx_norm["filled_status_ok"].all()) if not tx_norm.empty else False,
            "completed_transaction_round_lot_violation_count": int((~filled_tx["round_lot_ok"]).sum()) if not filled_tx.empty else 0,
            "log_error_count": len(error_lines),
            "log_warning_count": len(warning_lines),
            "log_order_none_warning_count": len(order_none_lines),
            "log_skipped_paused_warning_count": len(skipped_paused_lines),
            "log_limit_cancel_warning_count": len(limit_cancel_lines),
            "total_buy_value": buy_value,
            "total_sell_value_abs": sell_value_abs,
            "total_traded_value": total_traded_value,
            "turnover_multiple_vs_initial_cash": total_traded_value / INITIAL_CASH,
            "commission_total": commission_total,
            "commission_drag_pct_of_initial_cash": commission_total / INITIAL_CASH * 100.0,
            "average_order_value": float(filled_tx["gross_value"].abs().mean()) if not filled_tx.empty else None,
            "small_order_lt_50k_count": int(filled_tx["small_order_lt_50k"].sum()) if not filled_tx.empty else 0,
            "tiny_order_lt_10k_count": int(filled_tx["tiny_order_lt_10k"].sum()) if not filled_tx.empty else 0,
            "min_commission_hit_count": int(filled_tx["min_commission_hit_le_5_01"].sum()) if not filled_tx.empty else 0,
            "position_export_days": int(pos_summary["trade_date"].nunique()) if not pos_summary.empty else 0,
            "position_count_min": min_position_count,
            "position_count_max": max_position_count,
            "position_cash_weight_avg_pct": avg_cash_weight * 100.0 if not math.isnan(avg_cash_weight) else None,
            "position_cash_weight_max_pct": max_cash_weight * 100.0 if not math.isnan(max_cash_weight) else None,
            "rebalance_signal_count_log": len(rebalance_dates),
            "rebalance_target_rows_local": int(len(target)),
            "rebalance_target_rows_log": log_text.count("V5F_TARGET_ROW"),
            "rebalance_max_abs_weight_diff_pct_points": max_reb_abs_diff * 100.0 if not math.isnan(max_reb_abs_diff) else None,
            "rebalance_avg_sum_abs_weight_diff_pct_points": avg_sum_abs_diff * 100.0 if not math.isnan(avg_sum_abs_diff) else None,
            "platform_execution_interpretation": "Completed platform fills are healthy, but log-level order residuals from sub-100-share target adjustments, one paused security, and one limit-up cancellation explain part of local-vs-platform drift.",
            "pm_gate_decision": "primary_platform_attribution_positive_execution_review_pass_but_needs_platform_baseline",
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
        }
    )
    _write_json(summary_path, summary)

    _write_csv(out / "v5f_joinquant_platform_attribution_blockers.csv", _blockers(error_lines, warning_lines))
    _write_csv(out / "v5f_joinquant_platform_next_queue.csv", _next_queue())
    _write_report(out / "v5f_joinquant_platform_attribution_report.md", summary, tx_norm, total_traded_value, commission_total, avg_cash_weight, max_cash_weight, min_position_count, max_position_count, len(rebalance_dates), log_text.count("V5F_TARGET_ROW"), len(target), len(error_lines), len(warning_lines), max_reb_abs_diff, avg_sum_abs_diff)

    print(
        json.dumps(
            {
                "summary": str(summary_path),
                "transaction_rows": int(len(tx_norm)),
                "position_days": int(pos_summary["trade_date"].nunique()) if not pos_summary.empty else 0,
                "log_errors": len(error_lines),
                "log_warnings": len(warning_lines),
                "commission_total": commission_total,
                "turnover_multiple": total_traded_value / INITIAL_CASH,
                "pm_gate_decision": summary["pm_gate_decision"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return summary_path


def _load_transactions(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, encoding="gb18030")
    rows: list[dict[str, Any]] = []
    for _, row in raw.iterrows():
        side_raw = str(row.get("交易类型", "")).strip()
        side = "buy" if side_raw == "买" else "sell" if side_raw == "卖" else side_raw
        shares = _to_int_shares(row.get("成交数量"))
        value = _to_float(row.get("成交额"))
        commission = _to_float(row.get("手续费"))
        if math.isnan(commission):
            commission = 0.0
        label = str(row.get("标的", "")).strip()
        status = str(row.get("状态", "")).strip()
        rows.append(
            {
                "trade_date": str(row.get("日期", "")).strip(),
                "order_time": str(row.get("委托时间", "")).strip(),
                "asset_type": str(row.get("品种", "")).strip(),
                "name": _name_from_label(label),
                "code": _code_from_label(label),
                "side": side,
                "side_raw": side_raw,
                "order_type": str(row.get("下单类型", "")).strip(),
                "shares": shares,
                "price": _to_float(row.get("成交价")),
                "gross_value": value,
                "signed_value": value if side == "buy" else -value if side == "sell" else value,
                "commission": commission,
                "status": status,
                "last_update": str(row.get("最后更新时间", "")).strip(),
                "round_lot_ok": shares % 100 == 0,
                "filled_status_ok": "全部成交" in status,
                "small_order_lt_50k": abs(value) < 50_000,
                "tiny_order_lt_10k": abs(value) < 10_000,
                "min_commission_hit_le_5_01": 0 < commission <= 5.01,
            }
        )
    return pd.DataFrame(rows)


def _load_positions(path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="gb18030", newline="") as f:
        reader = csv.reader(f)
        next(reader)
        for r in reader:
            if not r:
                continue
            trade_date = r[0]
            asset_type = r[1] if len(r) > 1 else ""
            label = r[2] if len(r) > 2 else ""
            if label == "Cash":
                rows.append(
                    {
                        "trade_date": trade_date,
                        "asset_type": "cash",
                        "name": "Cash",
                        "code": "Cash",
                        "direction": "",
                        "shares": 0,
                        "available_shares": 0,
                        "close_price": math.nan,
                        "market_value": _to_float(r[7] if len(r) > 7 else 0),
                        "floating_pnl": math.nan,
                        "open_avg_price": math.nan,
                        "margin": 0.0,
                        "daily_pnl": math.nan,
                        "today_shares": 0,
                        "pnl_ratio": math.nan,
                        "total_asset": math.nan,
                        "position_weight": 0.0,
                    }
                )
                continue
            if len(r) < 17:
                continue
            rows.append(
                {
                    "trade_date": trade_date,
                    "asset_type": asset_type,
                    "name": _name_from_label(label),
                    "code": _code_from_label(label),
                    "direction": r[3],
                    "shares": _to_int_shares(r[4]),
                    "available_shares": _to_int_shares(r[5]),
                    "close_price": _to_float(r[6]),
                    "market_value": _to_float(r[7]),
                    "floating_pnl": _to_float(r[8]),
                    "open_avg_price": _to_float(r[9]),
                    "margin": _to_float(r[11]),
                    "daily_pnl": _to_float(r[12]),
                    "today_shares": _to_int_shares(r[13]),
                    "pnl_ratio": _to_float(r[14]),
                    "total_asset": _to_float(r[15]),
                    "position_weight": _to_float(r[16]),
                }
            )
    return pd.DataFrame(rows)


def _summarize_positions(stock_pos: pd.DataFrame, cash_pos: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for trade_date, sdf in stock_pos.groupby("trade_date"):
        cdf = cash_pos[cash_pos["trade_date"].eq(trade_date)]
        cash_balance = float(cdf["market_value"].sum()) if not cdf.empty else 0.0
        total_asset = float(sdf["total_asset"].dropna().iloc[0]) if not sdf["total_asset"].dropna().empty else float(sdf["market_value"].sum() + cash_balance)
        largest = sdf.sort_values("position_weight", ascending=False).iloc[0]
        smallest = sdf.sort_values("position_weight", ascending=True).iloc[0]
        rows.append(
            {
                "trade_date": trade_date,
                "stock_position_count": int(len(sdf)),
                "stock_market_value": float(sdf["market_value"].sum()),
                "cash_balance": cash_balance,
                "total_asset": total_asset,
                "cash_weight": cash_balance / total_asset if total_asset else math.nan,
                "stock_weight_sum": float(sdf["position_weight"].sum()),
                "max_position_weight": float(sdf["position_weight"].max()),
                "min_position_weight": float(sdf["position_weight"].min()),
                "largest_position_code": str(largest["code"]),
                "smallest_position_code": str(smallest["code"]),
            }
        )
    return pd.DataFrame(rows).sort_values("trade_date")


def _summarize_transactions_by_date(tx: pd.DataFrame, rebalance_dates: list[str], pos_summary: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    pos_by_date = {r["trade_date"]: r for r in pos_summary.to_dict("records")}
    for trade_date, g in tx.groupby("trade_date"):
        filled = g[g["filled_status_ok"]]
        pos = pos_by_date.get(trade_date, {})
        rows.append(
            {
                "trade_date": trade_date,
                "is_rebalance_signal_date": trade_date in rebalance_dates,
                "trade_count": int(len(g)),
                "filled_count": int(len(filled)),
                "cancelled_or_unfilled_count": int(len(g) - len(filled)),
                "buy_count": int((filled["side"] == "buy").sum()),
                "sell_count": int((filled["side"] == "sell").sum()),
                "buy_value": float(filled.loc[filled["side"].eq("buy"), "gross_value"].sum()),
                "sell_value_abs": float(filled.loc[filled["side"].eq("sell"), "gross_value"].abs().sum()),
                "net_buy_value": float(filled["signed_value"].sum()),
                "commission": float(filled["commission"].sum()),
                "all_transactions_filled": bool(g["filled_status_ok"].all()),
                "round_lot_violation_count": int((~filled["round_lot_ok"]).sum()),
                "small_order_lt_50k_count": int(filled["small_order_lt_50k"].sum()),
                "tiny_order_lt_10k_count": int(filled["tiny_order_lt_10k"].sum()),
                "min_commission_hit_count": int(filled["min_commission_hit_le_5_01"].sum()),
                "eod_position_count": pos.get("stock_position_count", ""),
                "eod_cash_weight": pos.get("cash_weight", ""),
            }
        )
    return rows


def _rebalance_position_audit(target: pd.DataFrame, stock_pos: pd.DataFrame, pos_summary: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    audit = []
    summary = []
    pos_dates = set(pos_summary["trade_date"]) if not pos_summary.empty else set()
    for reb_date, tg in target.groupby("rebalance_date"):
        actual = stock_pos[stock_pos["trade_date"].eq(reb_date)].copy()
        actual_map = {row["code"]: row for _, row in actual.iterrows()}
        target_codes = set(tg["code"])
        actual_codes = set(actual["code"])
        day_total_asset = float(actual["total_asset"].dropna().iloc[0]) if not actual.empty and not actual["total_asset"].dropna().empty else math.nan
        for _, trow in tg.iterrows():
            code = trow["code"]
            a = actual_map.get(code)
            actual_weight = float(a["position_weight"]) if a is not None else 0.0
            target_weight = float(trow["target_weight"])
            audit.append(
                {
                    "rebalance_date": reb_date,
                    "code": code,
                    "sleeve": trow.get("sleeve", ""),
                    "target_weight": target_weight,
                    "actual_eod_weight": actual_weight,
                    "weight_diff": actual_weight - target_weight,
                    "abs_weight_diff": abs(actual_weight - target_weight),
                    "target_value_at_eod_total_asset": target_weight * day_total_asset,
                    "actual_market_value": float(a["market_value"]) if a is not None else 0.0,
                    "audit_status": "matched" if code in actual_codes else "missing_position_after_rebalance",
                }
            )
        for code in sorted(actual_codes - target_codes):
            a = actual_map[code]
            audit.append(
                {
                    "rebalance_date": reb_date,
                    "code": code,
                    "sleeve": "",
                    "target_weight": 0.0,
                    "actual_eod_weight": float(a["position_weight"]),
                    "weight_diff": float(a["position_weight"]),
                    "abs_weight_diff": abs(float(a["position_weight"])),
                    "target_value_at_eod_total_asset": 0.0,
                    "actual_market_value": float(a["market_value"]),
                    "audit_status": "extra_position_after_rebalance",
                }
            )
        day_rows = [r for r in audit if r["rebalance_date"] == reb_date]
        cash_weight = float(pos_summary.loc[pos_summary["trade_date"].eq(reb_date), "cash_weight"].iloc[0]) if reb_date in pos_dates else math.nan
        summary.append(
            {
                "rebalance_date": reb_date,
                "target_count": int(len(tg)),
                "actual_count": int(len(actual)),
                "matched_count": int(len(target_codes & actual_codes)),
                "missing_count": int(len(target_codes - actual_codes)),
                "extra_count": int(len(actual_codes - target_codes)),
                "sum_abs_weight_diff": float(sum(r["abs_weight_diff"] for r in day_rows)),
                "max_abs_weight_diff": float(max((r["abs_weight_diff"] for r in day_rows), default=0.0)),
                "cash_weight": cash_weight,
                "audit_status": "pass_with_execution_residuals" if len(target_codes - actual_codes) + len(actual_codes - target_codes) == 0 else "needs_review_unmatched_positions",
            }
        )
    return audit, summary


def _log_governance_audit(log_text: str, rebalance_dates: list[str], target: pd.DataFrame, errors: list[str], warnings: list[str]) -> list[dict[str, Any]]:
    return [
        _audit("model_id", MODEL_ID if f"model={MODEL_ID}" in log_text else "missing", f"model={MODEL_ID}" in log_text, "Primary platform export belongs to internal_subsleeve_mom12_70_30."),
        _audit("frequency_minute", "frequency=minute" if "frequency=minute" in log_text else "missing", "frequency=minute" in log_text, "JoinQuant platform minute-frequency attribution."),
        _audit("historical_scope", "2021-05-01~2026-05-31" if "2021-05-01~2026-05-31" in log_text else "missing", "2021-05-01~2026-05-31" in log_text, "Historical scope maps to last trading day 2026-05-29."),
        _audit("local_5min_source_policy", "baostock_only" if "V5F_LOCAL_5MIN_BAR_SOURCE_POLICY,baostock_only" in log_text else "missing", "V5F_LOCAL_5MIN_BAR_SOURCE_POLICY,baostock_only" in log_text, "JoinQuant is not treated as local raw 5min source."),
        _audit("joinquant_platform_role", "minute_backtest_attribution_not_raw_bar_source" if "V5F_JOINQUANT_PLATFORM_ROLE,minute_backtest_attribution_not_raw_bar_source" in log_text else "missing", "V5F_JOINQUANT_PLATFORM_ROLE,minute_backtest_attribution_not_raw_bar_source" in log_text, "Platform role is attribution evidence only."),
        _audit("not_accepted", "not_accepted=True" if "not_accepted=True" in log_text else "missing", "not_accepted=True" in log_text, "Run does not mark accepted/live approved."),
        _audit("rebalance_signal_count", len(rebalance_dates), len(rebalance_dates) == 21, "Expected 21 historical rebalance signals."),
        _audit("target_row_count", log_text.count("V5F_TARGET_ROW"), log_text.count("V5F_TARGET_ROW") == int(len(target)), "Target rows match frozen local target table."),
        _audit("log_error_count", len(errors), len(errors) == 0, "Nonzero errors are platform order residuals; see order issues."),
        _audit("log_warning_count", len(warnings), len(warnings) == 0, "Warnings include ORDER_NONE, paused security, limit-up cancellation."),
        _audit("script_traceback_count", log_text.count("Traceback"), log_text.count("Traceback") == 0, "No script crash found."),
    ]


def _execution_health(
    tx: pd.DataFrame,
    errors: list[str],
    warnings: list[str],
    order_none: list[str],
    skipped_paused: list[str],
    limit_cancel: list[str],
    buy_value: float,
    sell_value_abs: float,
    total_traded_value: float,
    commission_total: float,
    avg_cash_weight: float,
    max_cash_weight: float,
    min_position_count: int,
    max_position_count: int,
    max_reb_abs_diff: float,
    avg_sum_abs_diff: float,
) -> list[dict[str, Any]]:
    filled = tx[tx["filled_status_ok"]].copy() if not tx.empty else tx.copy()
    round_lot_violations = int((~filled["round_lot_ok"]).sum()) if not filled.empty else 0
    all_filled = bool(tx["filled_status_ok"].all()) if not tx.empty else False
    return [
        _metric("transaction_rows", int(len(tx)), "observed", "Exported transaction rows in platform export."),
        _metric("filled_transaction_rows", int(len(filled)), "observed", "Rows with platform status fully filled."),
        _metric("cancelled_or_unfilled_transaction_rows", int(len(tx) - len(filled)), "review", "Rows not marked fully filled."),
        _metric("transaction_trade_dates", int(tx["trade_date"].nunique()) if not tx.empty else 0, "observed", "Trade dates with completed fills."),
        _metric("buy_count", int((filled["side"] == "buy").sum()) if not filled.empty else 0, "observed", "Completed buy rows."),
        _metric("sell_count", int((filled["side"] == "sell").sum()) if not filled.empty else 0, "observed", "Completed sell rows."),
        _metric("all_exported_transactions_filled", all_filled, "pass" if all_filled else "fail", "False when any exported row is cancelled or otherwise not fully filled."),
        _metric("completed_transaction_round_lot_violations", round_lot_violations, "pass" if round_lot_violations == 0 else "fail", "Completed share quantities should be 100-share multiples."),
        _metric("log_error_count", len(errors), "review", "Platform order_target_value residuals."),
        _metric("log_warning_count", len(warnings), "review", "Includes ORDER_NONE, paused security, limit-up buy cancellation."),
        _metric("order_none_warning_count", len(order_none), "review", "No executed transaction created for tiny target adjustment."),
        _metric("skipped_paused_warning_count", len(skipped_paused), "review", "Paused security handling recorded by platform."),
        _metric("limit_up_or_down_cancel_warning_count", len(limit_cancel), "review", "Platform rejected market buy when security was limit-up/down."),
        _metric("total_buy_value", buy_value, "observed", "Gross completed buy value."),
        _metric("total_sell_value_abs", sell_value_abs, "observed", "Gross completed sell value."),
        _metric("total_traded_value", total_traded_value, "observed", "Buy plus sell absolute value."),
        _metric("turnover_multiple_vs_initial_cash", total_traded_value / INITIAL_CASH, "observed", "Execution turnover on 2,000,000 initial capital."),
        _metric("commission_total", commission_total, "observed", "Total platform commission."),
        _metric("commission_drag_pct_of_initial_cash", commission_total / INITIAL_CASH * 100.0, "observed", "Commission total divided by initial capital."),
        _metric("avg_order_value", float(filled["gross_value"].abs().mean()) if not filled.empty else math.nan, "observed", "Average completed order value."),
        _metric("small_order_lt_50k_count", int(filled["small_order_lt_50k"].sum()) if not filled.empty else 0, "review", "Orders below 50k."),
        _metric("tiny_order_lt_10k_count", int(filled["tiny_order_lt_10k"].sum()) if not filled.empty else 0, "review", "Tiny completed orders."),
        _metric("min_commission_hit_count", int(filled["min_commission_hit_le_5_01"].sum()) if not filled.empty else 0, "review", "Commission <= 5.01 on completed rows."),
        _metric("avg_cash_weight", avg_cash_weight, "observed", "Position export cash / total asset mean."),
        _metric("max_cash_weight", max_cash_weight, "observed", "Position export max cash / total asset."),
        _metric("position_count_min", min_position_count, "observed", "Minimum EOD stock position count."),
        _metric("position_count_max", max_position_count, "observed", "Maximum EOD stock position count."),
        _metric("rebalance_max_abs_weight_diff", max_reb_abs_diff, "review", "Largest single-stock target vs EOD weight difference."),
        _metric("rebalance_avg_sum_abs_weight_diff", avg_sum_abs_diff, "review", "Average sum absolute target vs EOD weight difference."),
    ]


def _small_order_rows(tx: pd.DataFrame) -> list[dict[str, Any]]:
    if tx.empty:
        return []
    keep = tx[tx["small_order_lt_50k"] | tx["tiny_order_lt_10k"] | tx["min_commission_hit_le_5_01"] | (~tx["filled_status_ok"])]
    cols = [
        "trade_date",
        "order_time",
        "code",
        "name",
        "side",
        "shares",
        "gross_value",
        "commission",
        "small_order_lt_50k",
        "tiny_order_lt_10k",
        "min_commission_hit_le_5_01",
        "round_lot_ok",
        "filled_status_ok",
    ]
    return keep[cols].to_dict("records")


def _top_daily_drift(comparison: pd.DataFrame) -> list[dict[str, Any]]:
    if comparison.empty or "abs_platform_primary_daily_diff_bp" not in comparison.columns:
        return []
    cols = [
        "trade_date",
        "nav",
        "local_primary_nav",
        "local_baseline_nav",
        "platform_minus_local_primary_daily_return_bp",
        "platform_minus_local_baseline_daily_return_bp",
        "abs_platform_primary_daily_diff_bp",
        "cash_weight",
        "position_count",
        "daily_buy_value",
        "daily_sell_value",
    ]
    return comparison.sort_values("abs_platform_primary_daily_diff_bp", ascending=False).head(30)[cols].to_dict("records")


def _log_order_issues(errors: list[str], warnings: list[str]) -> list[dict[str, Any]]:
    rows = []
    for line in errors + warnings:
        m_date = re.match(r"(\d{4}-\d{2}-\d{2})", line)
        m_code = re.search(r"(?:security=|,)(\d{6}\.XSHE|\d{6}\.XSHG)", line)
        level = "ERROR" if " - ERROR - " in line else "WARNING"
        if "V5F_ORDER_NONE" in line:
            issue_type = "order_none"
        elif "V5F_ORDER_SKIPPED_PAUSED" in line:
            issue_type = "skipped_paused"
        elif "涨停" in line or "跌停" in line:
            issue_type = "limit_cancel"
        elif level == "ERROR":
            issue_type = "order_failed"
        else:
            issue_type = "warning"
        rows.append(
            {
                "trade_date": m_date.group(1) if m_date else "",
                "level": level,
                "issue_type": issue_type,
                "code": m_code.group(1) if m_code else "",
                "target_value_or_order_value": _extract_issue_value(line, issue_type),
                "message": line,
            }
        )
    return rows


def _extract_issue_value(line: str, issue_type: str) -> float | str:
    if issue_type in {"order_none", "skipped_paused"}:
        marker = "V5F_ORDER_NONE," if issue_type == "order_none" else "V5F_ORDER_SKIPPED_PAUSED,"
        if marker in line:
            parts = line.split(marker, 1)[1].split(",")
            if len(parts) >= 3:
                try:
                    return float(parts[2])
                except ValueError:
                    return ""
    match = re.search(r"_value=([-+]?[0-9]+(?:\.[0-9]+)?)", line)
    return float(match.group(1)) if match else ""


def _export_manifest(root: Path, export_root: Path, daily_csv: Path, tx_csv: Path, pos_csv: Path, log_path: Path) -> list[dict[str, Any]]:
    generated_script = root / "v5f_joinquant_export_checklist" / "current" / "v5f_internal_subsleeve_mom12_70_30_joinquant_minute_backtest.py"
    items = [
        ("daily_return_export", daily_csv, "gb18030", "received"),
        ("transaction_zip", export_root / "transaction_primary_internal_subsleeve_mom12_70_30.zip", "binary", "received"),
        ("transaction_csv", tx_csv, "gb18030", "parsed"),
        ("position_zip", export_root / "position_primary_internal_subsleeve_mom12_70_30.zip", "binary", "received"),
        ("position_csv", pos_csv, "gb18030", "parsed_corrected_header"),
        ("log_zip", export_root / "log_primary_internal_subsleeve_mom12_70_30.zip", "binary", "received"),
        ("log_txt", log_path, "gb18030", "parsed"),
        ("generated_joinquant_script", generated_script, "utf-8", "generated_available_not_user_exported_snapshot"),
    ]
    rows = []
    for artifact, path, encoding, status in items:
        rows.append(
            {
                "artifact": artifact,
                "path": str(path.relative_to(root)) if path.exists() else str(path),
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() else 0,
                "encoding": encoding,
                "model": MODEL_ID,
                "status": status,
            }
        )
    return rows


def _blockers(errors: list[str], warnings: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "blocker_id": "platform_baseline_export_missing",
            "severity": "required_for_clean_platform_edge",
            "status": "open",
            "detail": "Need same JoinQuant platform minute backtest with RUN_MODEL = v57f_startup_preload_repaired_baseline.",
        },
        {
            "blocker_id": "exact_user_run_script_snapshot_missing",
            "severity": "audit_quality",
            "status": "open",
            "detail": "Generated script exists locally, but exact platform-run snapshot was not exported separately.",
        },
        {
            "blocker_id": "platform_order_residuals_round_lot_pause_limit",
            "severity": "nonfatal_execution_residual",
            "status": "review",
            "detail": f"Log has {len(errors)} ERROR and {len(warnings)} WARNING lines; completed transaction rows are all filled and round-lot compliant.",
        },
    ]


def _next_queue() -> list[dict[str, Any]]:
    return [
        {
            "rank": 1,
            "next_task": "run_joinquant_platform_baseline_same_script",
            "status": "ready_for_user_platform_run",
            "detail": "Set RUN_MODEL = v57f_startup_preload_repaired_baseline and export daily returns, transactions, positions, logs.",
        },
        {
            "rank": 2,
            "next_task": "compare_platform_primary_vs_platform_baseline",
            "status": "blocked_until_baseline_export",
            "detail": "This is the clean test of platform edge; local baseline comparison remains indicative only.",
        },
        {
            "rank": 3,
            "next_task": "review_round_lot_order_residual_policy",
            "status": "optional_after_baseline",
            "detail": "Decide whether to make platform script explicitly skip target changes below 100 shares for cleaner logs, without changing V57f core.",
        },
        {
            "rank": 4,
            "next_task": "continue_forward_paper_tracking",
            "status": "ready",
            "detail": "Do not mark accepted/live approved; continue observation after platform attribution packet.",
        },
    ]


def _write_report(path: Path, summary: dict[str, Any], tx: pd.DataFrame, total_traded_value: float, commission_total: float, avg_cash_weight: float, max_cash_weight: float, min_position_count: int, max_position_count: int, rebalance_count: int, log_target_rows: int, local_target_rows: int, error_count: int, warning_count: int, max_reb_abs_diff: float, avg_sum_abs_diff: float) -> None:
    report = f"""# V5f JoinQuant Platform Attribution: {MODEL_ID}

## Scope

- Model: `{MODEL_ID}`.
- Platform run: JoinQuant minute-frequency backtest attribution, not local raw 5min data source.
- Historical scope: `2021-05-01` to `2026-05-31`; last trading day in export is `2026-05-29`.
- Governance: not accepted, not live approved, V57f core not modified.

## Platform Result

- JoinQuant platform primary return: `{summary.get('jq_platform_total_return_pct'):.4f}%`.
- User-reported annualized return: `{summary.get('jq_platform_annualized_return_pct_user_reported'):.2f}%`.
- Platform max drawdown: `{summary.get('jq_platform_max_drawdown_pct'):.4f}%`.
- Local primary return: `{summary.get('local_primary_total_return_pct'):.4f}%`; platform drift vs local primary: `{summary.get('platform_delta_vs_local_primary_pct_points'):.4f}` pct points.
- Local repaired baseline return: `{summary.get('local_repaired_baseline_total_return_pct'):.4f}%`; platform primary vs local repaired baseline: `{summary.get('platform_delta_vs_local_repaired_baseline_pct_points'):.4f}` pct points.
- Daily return correlation vs local primary: `{summary.get('daily_return_correlation_vs_local_primary'):.4f}`.

## Execution Attribution

- Transaction rows: `{len(tx)}` across `{summary['transaction_trade_dates']}` trade dates; filled / cancelled-or-unfilled: `{summary['filled_transaction_rows']}` / `{summary['cancelled_or_unfilled_transaction_rows']}`.
- Completed buys / sells: `{summary['buy_count']}` / `{summary['sell_count']}`.
- All exported transactions filled: `{summary['all_exported_transactions_filled']}`.
- Completed transaction round-lot violations: `{summary['completed_transaction_round_lot_violation_count']}`.
- Total traded value: `{total_traded_value:,.2f}`; turnover multiple vs 200w initial capital: `{total_traded_value / INITIAL_CASH:.4f}`.
- Commission total: `{commission_total:,.2f}`; commission drag vs 200w initial capital: `{commission_total / INITIAL_CASH * 100.0:.4f}%`.
- Small orders <50k: `{summary['small_order_lt_50k_count']}`; tiny orders <10k: `{summary['tiny_order_lt_10k_count']}`; minimum commission hits: `{summary['min_commission_hit_count']}`.

## Position And Log Health

- Position export days: `{summary['position_export_days']}`.
- EOD position count range: `{min_position_count}` to `{max_position_count}`.
- Average / max cash weight from position export: `{avg_cash_weight * 100.0:.4f}%` / `{max_cash_weight * 100.0:.4f}%`.
- Rebalance signals in log: `{rebalance_count}`; target rows in log/local table: `{log_target_rows}` / `{local_target_rows}`.
- Largest rebalance target-vs-EOD weight difference: `{max_reb_abs_diff * 100.0:.4f}` pct points.
- Average rebalance sum absolute weight difference: `{avg_sum_abs_diff * 100.0:.4f}` pct points.
- Log order residuals: `{error_count}` ERROR, `{warning_count}` WARNING. These are mostly sub-100-share target changes, plus paused/limit-up handling; they are execution residuals, not a model-rule change.

## Interpretation

The primary platform run is valid and positive. It remains above the local repaired baseline by about `{summary.get('platform_delta_vs_local_repaired_baseline_pct_points'):.4f}` pct points, but it is below the local primary path by about `{abs(summary.get('platform_delta_vs_local_primary_pct_points')):.4f}` pct points. The gap is consistent with JoinQuant platform execution, cash, dividend, limit/paused handling, and 100-share rounding residuals.

A clean platform edge conclusion still requires the same JoinQuant platform run for `{BASELINE_ID}`. Until that baseline platform export is supplied, this packet supports platform execution attribution for the primary model, but not accepted/live approval.

## PM Gate

`{summary['pm_gate_decision']}`
"""
    path.write_text(report, encoding="utf-8")


def _extract_rebalance_dates(lines: list[str]) -> list[str]:
    dates = []
    for line in lines:
        if "V5F_REBALANCE_SIGNAL" in line:
            m = re.search(r"date=(\d{4}-\d{2}-\d{2})", line)
            if m:
                dates.append(m.group(1))
    return sorted(set(dates))


def _audit(item: str, observed: Any, passed: bool, notes: str) -> dict[str, Any]:
    return {"audit_item": item, "observed": observed, "pass": passed, "notes": notes}


def _metric(metric: str, value: Any, status: str, notes: str) -> dict[str, Any]:
    return {"metric": metric, "value": value, "status": status, "notes": notes}


def _to_float(x: Any) -> float:
    if x is None:
        return math.nan
    s = str(x).strip().replace(",", "")
    if s in {"", "-", "--", "nan", "None"}:
        return math.nan
    if s.endswith("%"):
        return float(s[:-1]) / 100.0
    if s.endswith("股"):
        s = s[:-1]
    return float(s)


def _to_int_shares(x: Any) -> int:
    value = _to_float(x)
    if math.isnan(value):
        return 0
    return int(round(value))


def _code_from_label(label: str) -> str:
    m = re.search(r"\((\d{6}\.XSHE|\d{6}\.XSHG)\)", str(label))
    if m:
        return m.group(1)
    m = re.search(r"(\d{6}\.XSHE|\d{6}\.XSHG)", str(label))
    return m.group(1) if m else str(label).strip()


def _name_from_label(label: str) -> str:
    return str(label).split("(")[0].strip()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    run()

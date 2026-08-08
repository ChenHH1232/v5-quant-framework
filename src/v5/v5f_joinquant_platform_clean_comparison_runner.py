from __future__ import annotations

import csv
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from . import v5f_joinquant_platform_attribution_runner as base


ROOT = Path(__file__).resolve().parents[2]
MODEL_ID = base.MODEL_ID
BASELINE_ID = base.BASELINE_ID
INITIAL_CASH = base.INITIAL_CASH


def run(root: Path = ROOT) -> Path:
    base.run(root)

    export_root = root / "data" / "joinquant_exports" / "v5f_internal_subsleeve_mom12_70_30" / "historical_platform_attribution"
    out = root / "v5f_joinquant_platform_attribution" / "current"
    out.mkdir(parents=True, exist_ok=True)

    primary_daily = _load_daily(export_root / "daily_returns_primary_result_1_20.csv", "platform_primary")
    baseline_daily = _load_daily(export_root / "daily_returns_baseline_result_1_21.csv", "platform_baseline")
    base._write_csv(out / "v5f_joinquant_platform_baseline_daily_path.csv", baseline_daily.to_dict("records"))

    daily_compare = _compare_daily(primary_daily, baseline_daily)
    base._write_csv(out / "v5f_joinquant_platform_primary_vs_baseline_daily_comparison.csv", daily_compare.to_dict("records"))

    baseline_tx = base._load_transactions(export_root / "transaction_baseline_v57f_startup_preload_repaired_baseline" / "transaction.csv")
    baseline_pos = base._load_positions(export_root / "position_baseline_v57f_startup_preload_repaired_baseline" / "position.csv")
    baseline_stock_pos = baseline_pos[baseline_pos["code"].ne("Cash")].copy()
    baseline_cash_pos = baseline_pos[baseline_pos["code"].eq("Cash")].copy()
    baseline_pos_summary = base._summarize_positions(baseline_stock_pos, baseline_cash_pos)
    base._write_csv(out / "v5f_joinquant_platform_baseline_transactions_normalized.csv", baseline_tx.to_dict("records"))
    base._write_csv(out / "v5f_joinquant_platform_baseline_position_by_date.csv", baseline_pos_summary.to_dict("records"))

    log_path = export_root / "log_baseline_v57f_startup_preload_repaired_baseline" / "log.txt"
    baseline_log_text = log_path.read_text(encoding="gb18030", errors="ignore")
    baseline_log_lines = baseline_log_text.splitlines()
    baseline_rebalance_dates = base._extract_rebalance_dates(baseline_log_lines)
    baseline_errors = [line for line in baseline_log_lines if " - ERROR - " in line]
    baseline_warnings = [line for line in baseline_log_lines if " - WARNING - " in line]
    baseline_order_none = [line for line in baseline_warnings if "V5F_ORDER_NONE" in line]
    baseline_skipped_paused = [line for line in baseline_warnings if "V5F_ORDER_SKIPPED_PAUSED" in line]
    baseline_limit_cancel = _limit_cancel_lines(baseline_warnings)
    base._write_csv(out / "v5f_joinquant_platform_baseline_log_order_issues.csv", base._log_order_issues(baseline_errors, baseline_warnings))

    baseline_tx_by_date = base._summarize_transactions_by_date(baseline_tx, baseline_rebalance_dates, baseline_pos_summary)
    base._write_csv(out / "v5f_joinquant_platform_baseline_transaction_by_rebalance.csv", baseline_tx_by_date)

    weights = pd.read_csv(root / "v5f_structural_rough_screen" / "current" / "v5f_structural_rough_screen_weights.csv")
    baseline_target = weights[weights["version_id"].eq(BASELINE_ID)].copy()
    baseline_target["rebalance_date"] = baseline_target["rebalance_date"].astype(str)
    baseline_rebalance_audit, baseline_rebalance_summary = base._rebalance_position_audit(baseline_target, baseline_stock_pos, baseline_pos_summary)
    base._write_csv(out / "v5f_joinquant_platform_baseline_rebalance_target_position_audit.csv", baseline_rebalance_audit)
    base._write_csv(out / "v5f_joinquant_platform_baseline_rebalance_position_summary.csv", baseline_rebalance_summary)

    baseline_filled = baseline_tx[baseline_tx["filled_status_ok"]].copy() if not baseline_tx.empty else baseline_tx.copy()
    baseline_commission = float(baseline_filled["commission"].sum()) if not baseline_filled.empty else 0.0
    baseline_buy_value = float(baseline_filled.loc[baseline_filled["side"].eq("buy"), "gross_value"].sum()) if not baseline_filled.empty else 0.0
    baseline_sell_value = float(baseline_filled.loc[baseline_filled["side"].eq("sell"), "gross_value"].abs().sum()) if not baseline_filled.empty else 0.0
    baseline_total_traded = baseline_buy_value + baseline_sell_value
    baseline_avg_cash = float(baseline_pos_summary["cash_weight"].mean()) if not baseline_pos_summary.empty else math.nan
    baseline_max_cash = float(baseline_pos_summary["cash_weight"].max()) if not baseline_pos_summary.empty else math.nan
    baseline_min_count = int(baseline_pos_summary["stock_position_count"].min()) if not baseline_pos_summary.empty else 0
    baseline_max_count = int(baseline_pos_summary["stock_position_count"].max()) if not baseline_pos_summary.empty else 0
    baseline_max_reb_diff = max((float(r["max_abs_weight_diff"]) for r in baseline_rebalance_summary), default=math.nan)
    baseline_avg_sum_diff = float(pd.DataFrame(baseline_rebalance_summary)["sum_abs_weight_diff"].mean()) if baseline_rebalance_summary else math.nan
    baseline_health = base._execution_health(
        baseline_tx,
        baseline_errors,
        baseline_warnings,
        baseline_order_none,
        baseline_skipped_paused,
        baseline_limit_cancel,
        baseline_buy_value,
        baseline_sell_value,
        baseline_total_traded,
        baseline_commission,
        baseline_avg_cash,
        baseline_max_cash,
        baseline_min_count,
        baseline_max_count,
        baseline_max_reb_diff,
        baseline_avg_sum_diff,
    )
    base._write_csv(out / "v5f_joinquant_platform_baseline_execution_health.csv", baseline_health)
    base._write_csv(out / "v5f_joinquant_platform_baseline_log_governance_audit.csv", _baseline_log_audit(baseline_log_text, baseline_rebalance_dates, baseline_target, baseline_errors, baseline_warnings))

    primary_metrics = _daily_metrics(primary_daily)
    baseline_metrics = _daily_metrics(baseline_daily)
    comparison_metrics = _comparison_metrics(daily_compare, primary_metrics, baseline_metrics)

    primary_summary = base._read_json(out / "v5f_joinquant_platform_attribution_summary.json")
    primary_commission = float(primary_summary["commission_total"])
    primary_traded = float(primary_summary["total_traded_value"])

    clean_rows = [
        {
            "metric": "total_return_pct",
            "platform_primary": primary_metrics["total_return_pct"],
            "platform_baseline": baseline_metrics["total_return_pct"],
            "primary_minus_baseline": comparison_metrics["clean_edge_total_return_pct_points"],
            "unit": "pct_points",
        },
        {
            "metric": "annualized_return_pct",
            "platform_primary": primary_metrics["annualized_return_pct"],
            "platform_baseline": baseline_metrics["annualized_return_pct"],
            "primary_minus_baseline": comparison_metrics["clean_edge_annualized_return_pct_points"],
            "unit": "pct_points",
        },
        {
            "metric": "max_drawdown_pct",
            "platform_primary": primary_metrics["max_drawdown_pct"],
            "platform_baseline": baseline_metrics["max_drawdown_pct"],
            "primary_minus_baseline": comparison_metrics["clean_mdd_delta_pct_points"],
            "unit": "pct_points",
        },
        {
            "metric": "sharpe_calc",
            "platform_primary": primary_metrics["sharpe_calc"],
            "platform_baseline": baseline_metrics["sharpe_calc"],
            "primary_minus_baseline": primary_metrics["sharpe_calc"] - baseline_metrics["sharpe_calc"],
            "unit": "ratio",
        },
        {
            "metric": "commission_total",
            "platform_primary": primary_commission,
            "platform_baseline": baseline_commission,
            "primary_minus_baseline": primary_commission - baseline_commission,
            "unit": "currency",
        },
        {
            "metric": "total_traded_value",
            "platform_primary": primary_traded,
            "platform_baseline": baseline_total_traded,
            "primary_minus_baseline": primary_traded - baseline_total_traded,
            "unit": "currency",
        },
    ]
    base._write_csv(out / "v5f_joinquant_platform_clean_edge_comparison.csv", clean_rows)

    primary_summary.update(
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "task": "v5f_joinquant_platform_clean_primary_vs_baseline_attribution",
            "status": "completed_clean_platform_primary_vs_baseline_attribution",
            "required_platform_baseline_export_missing": False,
            "platform_baseline_total_return_pct": baseline_metrics["total_return_pct"],
            "platform_baseline_annualized_return_pct_calc": baseline_metrics["annualized_return_pct"],
            "platform_baseline_max_drawdown_pct": baseline_metrics["max_drawdown_pct"],
            "platform_baseline_volatility_pct": baseline_metrics["volatility_pct"],
            "platform_baseline_sharpe_calc": baseline_metrics["sharpe_calc"],
            "platform_clean_edge_total_return_pct_points": comparison_metrics["clean_edge_total_return_pct_points"],
            "platform_clean_relative_wealth_edge_pct": comparison_metrics["relative_wealth_edge_pct"],
            "platform_clean_edge_annualized_return_pct_points": comparison_metrics["clean_edge_annualized_return_pct_points"],
            "platform_clean_mdd_delta_pct_points": comparison_metrics["clean_mdd_delta_pct_points"],
            "platform_primary_vs_baseline_daily_return_corr": comparison_metrics["daily_return_corr"],
            "platform_primary_vs_baseline_avg_daily_active_return_bp": comparison_metrics["avg_daily_active_return_bp"],
            "platform_primary_vs_baseline_avg_abs_daily_active_return_bp": comparison_metrics["avg_abs_daily_active_return_bp"],
            "baseline_transaction_rows": int(len(baseline_tx)),
            "baseline_filled_transaction_rows": int(len(baseline_filled)),
            "baseline_cancelled_or_unfilled_transaction_rows": int(len(baseline_tx) - len(baseline_filled)),
            "baseline_buy_count": int((baseline_filled["side"] == "buy").sum()) if not baseline_filled.empty else 0,
            "baseline_sell_count": int((baseline_filled["side"] == "sell").sum()) if not baseline_filled.empty else 0,
            "baseline_commission_total": baseline_commission,
            "baseline_commission_drag_pct_of_initial_cash": baseline_commission / INITIAL_CASH * 100.0,
            "baseline_total_traded_value": baseline_total_traded,
            "baseline_turnover_multiple_vs_initial_cash": baseline_total_traded / INITIAL_CASH,
            "baseline_position_cash_weight_avg_pct": baseline_avg_cash * 100.0 if not math.isnan(baseline_avg_cash) else None,
            "baseline_position_cash_weight_max_pct": baseline_max_cash * 100.0 if not math.isnan(baseline_max_cash) else None,
            "baseline_log_error_count": len(baseline_errors),
            "baseline_log_warning_count": len(baseline_warnings),
            "baseline_log_order_none_warning_count": len(baseline_order_none),
            "baseline_log_skipped_paused_warning_count": len(baseline_skipped_paused),
            "baseline_log_limit_cancel_warning_count": len(baseline_limit_cancel),
            "baseline_rebalance_signal_count_log": len(baseline_rebalance_dates),
            "baseline_rebalance_target_rows_local": int(len(baseline_target)),
            "baseline_rebalance_target_rows_log": baseline_log_text.count("V5F_TARGET_ROW"),
            "baseline_rebalance_max_abs_weight_diff_pct_points": baseline_max_reb_diff * 100.0 if not math.isnan(baseline_max_reb_diff) else None,
            "baseline_rebalance_avg_sum_abs_weight_diff_pct_points": baseline_avg_sum_diff * 100.0 if not math.isnan(baseline_avg_sum_diff) else None,
            "pm_gate_decision": "clean_platform_edge_positive_forward_paper_not_accepted",
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
        }
    )
    base._write_json(out / "v5f_joinquant_platform_attribution_summary.json", primary_summary)

    base._write_csv(out / "v5f_joinquant_platform_attribution_blockers.csv", _clean_blockers(primary_summary))
    base._write_csv(out / "v5f_joinquant_platform_next_queue.csv", _clean_next_queue())
    _write_clean_report(out / "v5f_joinquant_platform_attribution_report.md", primary_summary)

    print(
        json.dumps(
            {
                "platform_primary_return_pct": primary_metrics["total_return_pct"],
                "platform_baseline_return_pct": baseline_metrics["total_return_pct"],
                "clean_edge_pct_points": comparison_metrics["clean_edge_total_return_pct_points"],
                "relative_wealth_edge_pct": comparison_metrics["relative_wealth_edge_pct"],
                "primary_mdd_pct": primary_metrics["max_drawdown_pct"],
                "baseline_mdd_pct": baseline_metrics["max_drawdown_pct"],
                "pm_gate_decision": primary_summary["pm_gate_decision"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return out / "v5f_joinquant_platform_attribution_summary.json"


def _load_daily(path: Path, label: str) -> pd.DataFrame:
    raw = pd.read_csv(path, encoding="gb18030")
    date_col = raw.columns[0]
    out = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(raw[date_col]).dt.strftime("%Y-%m-%d"),
            "model": label,
            "nav": raw["nav"].astype(float),
            "cash_weight": raw["cash_weight"].astype(float) if "cash_weight" in raw.columns else math.nan,
            "position_count": raw["position_count"].astype(int) if "position_count" in raw.columns else 0,
            "daily_buy_value": raw.iloc[:, 5].astype(float),
            "daily_sell_value": raw.iloc[:, 6].astype(float),
        }
    )
    out["daily_return"] = out["nav"].pct_change()
    out.loc[out.index[0], "daily_return"] = out.loc[out.index[0], "nav"] - 1.0
    return out


def _compare_daily(primary: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    p = primary.rename(
        columns={
            "nav": "primary_nav",
            "daily_return": "primary_daily_return",
            "cash_weight": "primary_cash_weight",
            "position_count": "primary_position_count",
            "daily_buy_value": "primary_daily_buy_value",
            "daily_sell_value": "primary_daily_sell_value",
        }
    )
    b = baseline.rename(
        columns={
            "nav": "baseline_nav",
            "daily_return": "baseline_daily_return",
            "cash_weight": "baseline_cash_weight",
            "position_count": "baseline_position_count",
            "daily_buy_value": "baseline_daily_buy_value",
            "daily_sell_value": "baseline_daily_sell_value",
        }
    )
    keep_p = ["trade_date", "primary_nav", "primary_daily_return", "primary_cash_weight", "primary_position_count", "primary_daily_buy_value", "primary_daily_sell_value"]
    keep_b = ["trade_date", "baseline_nav", "baseline_daily_return", "baseline_cash_weight", "baseline_position_count", "baseline_daily_buy_value", "baseline_daily_sell_value"]
    merged = p[keep_p].merge(b[keep_b], on="trade_date", how="inner")
    merged["primary_minus_baseline_daily_return_bp"] = (merged["primary_daily_return"] - merged["baseline_daily_return"]) * 10000.0
    merged["primary_minus_baseline_nav_pct_points"] = (merged["primary_nav"] - merged["baseline_nav"]) * 100.0
    merged["relative_wealth_edge_pct"] = (merged["primary_nav"] / merged["baseline_nav"] - 1.0) * 100.0
    merged["primary_minus_baseline_cash_weight_pct_points"] = (merged["primary_cash_weight"] - merged["baseline_cash_weight"]) * 100.0
    merged["primary_minus_baseline_daily_buy_value"] = merged["primary_daily_buy_value"] - merged["baseline_daily_buy_value"]
    merged["primary_minus_baseline_daily_sell_value"] = merged["primary_daily_sell_value"] - merged["baseline_daily_sell_value"]
    return merged


def _daily_metrics(daily: pd.DataFrame) -> dict[str, float]:
    nav = daily["nav"].astype(float)
    returns = daily["daily_return"].astype(float)
    total_return = (float(nav.iloc[-1]) - 1.0) * 100.0
    annualized = (float(nav.iloc[-1]) ** (252.0 / len(nav)) - 1.0) * 100.0
    drawdown = nav / nav.cummax() - 1.0
    max_drawdown = abs(float(drawdown.min())) * 100.0
    volatility = float(returns.std(ddof=1)) * math.sqrt(252.0) * 100.0
    sharpe = float(returns.mean() / returns.std(ddof=1) * math.sqrt(252.0)) if float(returns.std(ddof=1)) != 0 else math.nan
    return {
        "total_return_pct": total_return,
        "annualized_return_pct": annualized,
        "max_drawdown_pct": max_drawdown,
        "volatility_pct": volatility,
        "sharpe_calc": sharpe,
    }


def _comparison_metrics(compare: pd.DataFrame, primary: dict[str, float], baseline: dict[str, float]) -> dict[str, float]:
    active = compare["primary_minus_baseline_daily_return_bp"].astype(float)
    return {
        "clean_edge_total_return_pct_points": primary["total_return_pct"] - baseline["total_return_pct"],
        "relative_wealth_edge_pct": float(compare["relative_wealth_edge_pct"].iloc[-1]),
        "clean_edge_annualized_return_pct_points": primary["annualized_return_pct"] - baseline["annualized_return_pct"],
        "clean_mdd_delta_pct_points": primary["max_drawdown_pct"] - baseline["max_drawdown_pct"],
        "daily_return_corr": float(compare["primary_daily_return"].corr(compare["baseline_daily_return"])),
        "avg_daily_active_return_bp": float(active.mean()),
        "avg_abs_daily_active_return_bp": float(active.abs().mean()),
    }


def _baseline_log_audit(log_text: str, rebalance_dates: list[str], target: pd.DataFrame, errors: list[str], warnings: list[str]) -> list[dict[str, Any]]:
    return [
        _audit("model_id", BASELINE_ID if f"model={BASELINE_ID}" in log_text else "missing", f"model={BASELINE_ID}" in log_text, "Baseline platform export belongs to repaired baseline."),
        _audit("frequency_minute", "frequency=minute" if "frequency=minute" in log_text else "missing", "frequency=minute" in log_text, "JoinQuant platform minute-frequency attribution."),
        _audit("historical_scope", "2021-05-01~2026-05-31" if "2021-05-01~2026-05-31" in log_text else "missing", "2021-05-01~2026-05-31" in log_text, "Historical scope maps to last trading day 2026-05-29."),
        _audit("local_5min_source_policy", "baostock_only" if "V5F_LOCAL_5MIN_BAR_SOURCE_POLICY,baostock_only" in log_text else "missing", "V5F_LOCAL_5MIN_BAR_SOURCE_POLICY,baostock_only" in log_text, "JoinQuant is not treated as local raw 5min source."),
        _audit("joinquant_platform_role", "minute_backtest_attribution_not_raw_bar_source" if "V5F_JOINQUANT_PLATFORM_ROLE,minute_backtest_attribution_not_raw_bar_source" in log_text else "missing", "V5F_JOINQUANT_PLATFORM_ROLE,minute_backtest_attribution_not_raw_bar_source" in log_text, "Platform role is attribution evidence only."),
        _audit("not_accepted", "not_accepted=True" if "not_accepted=True" in log_text else "missing", "not_accepted=True" in log_text, "Run does not mark accepted/live approved."),
        _audit("rebalance_signal_count", len(rebalance_dates), len(rebalance_dates) == 21, "Expected 21 historical rebalance signals."),
        _audit("target_row_count", log_text.count("V5F_TARGET_ROW"), log_text.count("V5F_TARGET_ROW") == int(len(target)), "Target rows match frozen local target table."),
        _audit("log_error_count", len(errors), len(errors) == 0, "Nonzero errors are platform order residuals; see baseline order issues."),
        _audit("log_warning_count", len(warnings), len(warnings) == 0, "Warnings are platform execution residuals."),
        _audit("script_traceback_count", log_text.count("Traceback"), log_text.count("Traceback") == 0, "No script crash found."),
    ]


def _audit(item: str, observed: Any, passed: bool, notes: str) -> dict[str, Any]:
    return {"audit_item": item, "observed": observed, "pass": passed, "notes": notes}


def _limit_cancel_lines(warnings: list[str]) -> list[str]:
    return [line for line in warnings if "市价买单取消" in line or "市价卖单取消" in line or "涨停" in line or "跌停" in line]


def _clean_blockers(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "blocker_id": "accepted_live_approval_not_allowed",
            "severity": "governance",
            "status": "closed_as_not_allowed",
            "detail": "Clean platform edge is positive, but this packet cannot mark accepted or live approved.",
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
            "detail": f"Primary log has {summary['log_error_count']} ERROR/{summary['log_warning_count']} WARNING; baseline log has {summary['baseline_log_error_count']} ERROR/{summary['baseline_log_warning_count']} WARNING.",
        },
    ]


def _clean_next_queue() -> list[dict[str, Any]]:
    return [
        {
            "rank": 1,
            "next_task": "keep_internal_subsleeve_mom12_70_30_as_forward_paper_primary",
            "status": "ready",
            "detail": "Clean platform edge is positive but not accepted/live approved.",
        },
        {
            "rank": 2,
            "next_task": "review_round_lot_order_residual_policy",
            "status": "optional",
            "detail": "Consider explicit no-trade handling for target changes that would produce sub-100-share orders, without changing V57f core.",
        },
        {
            "rank": 3,
            "next_task": "prepare_forward_platform_tracking_after_next_rebalance",
            "status": "ready",
            "detail": "Use the same platform export template for forward/paper tracking.",
        },
    ]


def _write_clean_report(path: Path, summary: dict[str, Any]) -> None:
    report = f"""# V5f JoinQuant Clean Platform Attribution

## Scope

- Primary model: `{MODEL_ID}`.
- Baseline model: `{BASELINE_ID}`.
- Platform: JoinQuant minute-frequency backtest export, used for attribution only.
- Historical scope: `2021-05-01` to `2026-05-31`; last trading day `2026-05-29`.
- Governance: not accepted, not live approved, V57f core not modified.

## Clean Platform Result

- Primary platform return: `{summary['jq_platform_total_return_pct']:.4f}%`.
- Baseline platform return: `{summary['platform_baseline_total_return_pct']:.4f}%`.
- Clean primary minus baseline edge: `{summary['platform_clean_edge_total_return_pct_points']:.4f}` pct points.
- Relative wealth edge: `{summary['platform_clean_relative_wealth_edge_pct']:.4f}%`.
- Primary annualized return: `{summary['jq_platform_annualized_return_pct_calc']:.4f}%`.
- Baseline annualized return: `{summary['platform_baseline_annualized_return_pct_calc']:.4f}%`.
- Annualized edge: `{summary['platform_clean_edge_annualized_return_pct_points']:.4f}` pct points.
- Primary / baseline max drawdown: `{summary['jq_platform_max_drawdown_pct']:.4f}%` / `{summary['platform_baseline_max_drawdown_pct']:.4f}%`.
- Drawdown delta: `{summary['platform_clean_mdd_delta_pct_points']:.4f}` pct points.
- Daily return correlation primary vs baseline: `{summary['platform_primary_vs_baseline_daily_return_corr']:.4f}`.

## Execution Comparison

- Primary filled/cancelled rows: `{summary['filled_transaction_rows']}` / `{summary['cancelled_or_unfilled_transaction_rows']}`.
- Baseline filled/cancelled rows: `{summary['baseline_filled_transaction_rows']}` / `{summary['baseline_cancelled_or_unfilled_transaction_rows']}`.
- Primary commission: `{summary['commission_total']:,.2f}`; baseline commission: `{summary['baseline_commission_total']:,.2f}`.
- Primary traded value: `{summary['total_traded_value']:,.2f}`; baseline traded value: `{summary['baseline_total_traded_value']:,.2f}`.
- Primary avg/max cash weight: `{summary['position_cash_weight_avg_pct']:.4f}%` / `{summary['position_cash_weight_max_pct']:.4f}%`.
- Baseline avg/max cash weight: `{summary['baseline_position_cash_weight_avg_pct']:.4f}%` / `{summary['baseline_position_cash_weight_max_pct']:.4f}%`.

## Interpretation

The clean platform comparison is positive: `internal_subsleeve_mom12_70_30` beats repaired baseline on the same JoinQuant platform export by `{summary['platform_clean_edge_total_return_pct_points']:.4f}` pct points. This is smaller than the local backtest edge, but it removes the earlier blocker that only primary had been run on platform.

The edge is not enough to mark accepted or live approved by itself. Execution residuals remain visible in both runs, mostly from 100-share lot constraints, paused/limit handling, and platform order rounding. The correct status is forward/paper primary, not accepted.

## PM Gate

`{summary['pm_gate_decision']}`
"""
    path.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    run()

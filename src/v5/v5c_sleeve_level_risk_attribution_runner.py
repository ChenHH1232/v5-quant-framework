from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from v5.basket_daily_backtest_runner import _load_corporate_actions, _load_prices
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import to_float


BASELINE_DIR = Path("local_daily_backtests_v57f_etf") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
CONFIG_PATH = Path("config") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f.json"
SLEEVE_REGISTRY_PATH = Path("enhanced_etf_production_lines_v5") / "current" / "sleeve_registry.csv"
OUT_DIR = Path("v5c_sleeve_level_risk_attribution") / "current"

CORE_SLEEVES = [
    "bank",
    "utilities_electricity",
    "highway_infrastructure",
    "port_rail_infrastructure",
]


def run_v5c_sleeve_level_risk_attribution(root: Path = Path(".")) -> dict[str, Any]:
    baseline_dir = root / BASELINE_DIR
    config_path = root / CONFIG_PATH
    out_dir = root / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    required_paths = [
        baseline_dir / "summary.json",
        baseline_dir / "daily_returns.csv",
        baseline_dir / "holdings.csv",
        baseline_dir / "trades.csv",
        baseline_dir / "rebalance_signals.csv",
        config_path,
        root / SLEEVE_REGISTRY_PATH,
        root / "enhanced_etf_governance_v5" / "current" / "v57f_core_dashboard.csv",
        root / "execution_robustness_v57f" / "current" / "execution_robustness_summary.json",
        root / "v5c_overlay_engineering_comparison" / "current" / "v5c_overlay_engineering_comparison.csv",
        root / "v5c_overlay_engineering_comparison" / "current" / "v5c_overlay_engineering_blockers.csv",
        root / "v5c_profit_taking_overheat_overlay" / "current" / "v5c_profit_taking_overheat_engineering_comparison.csv",
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise FileNotFoundError("missing required governance or baseline files: " + "; ".join(missing))

    baseline_summary = _read_json(baseline_dir / "summary.json")
    config = _read_json(config_path)
    daily_rows = read_csv_rows(baseline_dir / "daily_returns.csv")
    trade_rows = read_csv_rows(baseline_dir / "trades.csv")
    signal_rows = read_csv_rows(baseline_dir / "rebalance_signals.csv")

    start_date = str(baseline_summary.get("window", {}).get("start_date") or daily_rows[0]["trade_date"])
    end_date = str(baseline_summary.get("window", {}).get("end_date") or daily_rows[-1]["trade_date"])
    price_files = [root / Path(str(sector["price_csv"])) for sector in config.get("sectors", []) if sector.get("price_csv")]
    dividend_files = [root / Path(str(sector["dividend_csv"])) for sector in config.get("sectors", []) if sector.get("dividend_csv")]
    prices_by_date = _load_prices(price_files, start_date, end_date)
    actions_by_date = _load_corporate_actions(dividend_files, start_date, end_date)
    signal_sector_by_day_code = _build_signal_sector_map(signal_rows)
    latest_signal_day_by_date = _build_latest_signal_day_by_date([row["trade_date"] for row in daily_rows], signal_sector_by_day_code)

    attribution = _replay_sleeve_books(
        daily_rows=daily_rows,
        trade_rows=trade_rows,
        prices_by_date=prices_by_date,
        actions_by_date=actions_by_date,
        signal_sector_by_day_code=signal_sector_by_day_code,
        latest_signal_day_by_date=latest_signal_day_by_date,
        initial_cash=float(baseline_summary.get("execution", {}).get("initial_cash") or 2_000_000.0),
    )

    daily_wide = attribution["daily_wide"]
    pnl_rows = attribution["pnl_rows"]
    quality_rows = attribution["quality_rows"]
    metrics_rows = _build_metrics_rows(daily_wide, daily_rows)
    correlation_rows = _build_correlation_matrix(daily_wide)
    drawdown_rows = _build_drawdown_contribution_rows(daily_wide, daily_rows, baseline_summary)
    risk_rows = _build_risk_contribution_rows(daily_wide)
    readiness_rows, blocker_rows, readiness_status = _build_readiness_rows(attribution, metrics_rows, quality_rows)

    write_csv_rows(out_dir / "v57f_core_sleeve_daily_returns.csv", _fieldnames(daily_wide), daily_wide)
    write_csv_rows(out_dir / "v57f_core_sleeve_daily_pnl.csv", _fieldnames(pnl_rows), pnl_rows)
    write_csv_rows(out_dir / "v57f_core_sleeve_metrics.csv", _fieldnames(metrics_rows), metrics_rows)
    write_csv_rows(out_dir / "v57f_core_sleeve_correlation_matrix.csv", _fieldnames(correlation_rows), correlation_rows)
    write_csv_rows(out_dir / "v57f_core_sleeve_drawdown_contribution.csv", _fieldnames(drawdown_rows), drawdown_rows)
    write_csv_rows(out_dir / "v57f_core_sleeve_risk_contribution.csv", _fieldnames(risk_rows), risk_rows)
    write_csv_rows(out_dir / "v57f_core_sleeve_data_quality_checks.csv", _fieldnames(quality_rows), quality_rows)
    write_csv_rows(out_dir / "v5c_risk_budget_overlay_readiness.csv", _fieldnames(readiness_rows), readiness_rows)
    write_csv_rows(out_dir / "v5c_sleeve_attribution_blockers.csv", _fieldnames(blocker_rows), blocker_rows)
    (out_dir / "v5c_agent_execution_rules.md").write_text(_build_agent_rules(), encoding="utf-8")

    biggest_risk = max(risk_rows, key=lambda row: abs(float(row["standalone_vol_risk_share"])))["sleeve_id"] if risk_rows else None
    biggest_dd = max(drawdown_rows, key=lambda row: abs(float(row["pnl_contribution"])))["sleeve_id"] if drawdown_rows else None
    summary = {
        "schema_version": 1,
        "project": "v5c_sleeve_level_risk_attribution",
        "status": readiness_status,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "baseline_strategy_id": baseline_summary.get("strategy_id"),
        "window": baseline_summary.get("window"),
        "v57f_core_modified": False,
        "joinquant_started": False,
        "new_overlay_tested": False,
        "core_sleeves": CORE_SLEEVES,
        "daily_count": len(daily_wide),
        "sleeve_mapping_source": "rebalance_signals.csv sector_id mapped by active rebalance date; position sectors carried through trades",
        "aggregation_check": attribution["aggregation_check"],
        "biggest_standalone_vol_risk_sleeve": biggest_risk,
        "biggest_official_drawdown_pnl_sleeve": biggest_dd,
        "risk_budget_overlay_readiness": readiness_status,
        "blocker_count": len(blocker_rows),
        "outputs": {
            "summary": str(out_dir / "v5c_sleeve_level_risk_attribution_summary.json"),
            "report": str(out_dir / "v5c_sleeve_level_risk_attribution_report.md"),
            "daily_returns": str(out_dir / "v57f_core_sleeve_daily_returns.csv"),
            "daily_pnl": str(out_dir / "v57f_core_sleeve_daily_pnl.csv"),
            "metrics": str(out_dir / "v57f_core_sleeve_metrics.csv"),
            "correlation_matrix": str(out_dir / "v57f_core_sleeve_correlation_matrix.csv"),
            "drawdown_contribution": str(out_dir / "v57f_core_sleeve_drawdown_contribution.csv"),
            "risk_contribution": str(out_dir / "v57f_core_sleeve_risk_contribution.csv"),
            "data_quality_checks": str(out_dir / "v57f_core_sleeve_data_quality_checks.csv"),
            "readiness": str(out_dir / "v5c_risk_budget_overlay_readiness.csv"),
            "blockers": str(out_dir / "v5c_sleeve_attribution_blockers.csv"),
            "agent_rules": str(out_dir / "v5c_agent_execution_rules.md"),
        },
    }
    write_json_file(out_dir / "v5c_sleeve_level_risk_attribution_summary.json", summary)
    (out_dir / "v5c_sleeve_level_risk_attribution_report.md").write_text(
        _build_report(summary, metrics_rows, risk_rows, drawdown_rows, readiness_rows, blocker_rows),
        encoding="utf-8",
    )
    return summary


def _replay_sleeve_books(
    *,
    daily_rows: list[dict[str, str]],
    trade_rows: list[dict[str, str]],
    prices_by_date: dict[str, dict[str, dict[str, float]]],
    actions_by_date: dict[str, dict[str, dict[str, float]]],
    signal_sector_by_day_code: dict[str, dict[str, str]],
    latest_signal_day_by_date: dict[str, str],
    initial_cash: float,
) -> dict[str, Any]:
    trades_by_day: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in trade_rows:
        trades_by_day[str(row.get("trade_date") or "")[:10]].append(row)

    cash = initial_cash
    positions: dict[str, int] = {}
    position_sector: dict[str, str] = {}
    last_close: dict[str, float] = {}
    previous_portfolio_value = initial_cash
    previous_sleeve_value = {sleeve: 0.0 for sleeve in CORE_SLEEVES}
    max_abs_return_gap = 0.0
    max_abs_value_gap = 0.0
    unmapped_events: list[str] = []
    daily_wide: list[dict[str, Any]] = []
    pnl_rows: list[dict[str, Any]] = []

    for row in daily_rows:
        day = str(row["trade_date"])[:10]
        price_rows = prices_by_date.get(day, {})
        open_prices = {code: item["open"] for code, item in price_rows.items()}
        close_prices = {code: item["close"] for code, item in price_rows.items()}
        trade_prices = dict(last_close)
        trade_prices.update(open_prices)

        action_pnl_by_sleeve = {sleeve: 0.0 for sleeve in CORE_SLEEVES}
        for code, action in actions_by_date.get(day, {}).items():
            current_amount = positions.get(code, 0)
            share_ratio = action.get("stock_dividend_ratio", 0.0) or 0.0
            if current_amount <= 0 or share_ratio <= 0:
                continue
            new_amount = int(round(current_amount * (1.0 + share_ratio)))
            added_amount = new_amount - current_amount
            if added_amount <= 0:
                continue
            positions[code] = new_amount
            sector = position_sector.get(code)
            if sector in action_pnl_by_sleeve:
                close_for_value = price_rows.get(code, {}).get("close") or last_close.get(code, 0.0)
                action_pnl_by_sleeve[sector] += added_amount * close_for_value

        buy_value = {sleeve: 0.0 for sleeve in CORE_SLEEVES}
        sell_value = {sleeve: 0.0 for sleeve in CORE_SLEEVES}
        commission = {sleeve: 0.0 for sleeve in CORE_SLEEVES}
        latest_signal_day = latest_signal_day_by_date.get(day)
        current_signal_map = signal_sector_by_day_code.get(latest_signal_day or "", {})
        for trade in trades_by_day.get(day, []):
            side = str(trade.get("side") or "")
            if side.endswith("_skipped"):
                continue
            code = str(trade.get("code") or "")
            amount = int(float(trade.get("amount") or 0))
            value = to_float(trade.get("value")) or 0.0
            trade_commission = to_float(trade.get("commission")) or 0.0
            if amount <= 0:
                continue
            sector = position_sector.get(code) or current_signal_map.get(code) or _lookup_signal_sector(code, day, signal_sector_by_day_code)
            if sector not in CORE_SLEEVES:
                unmapped_events.append(f"{day}:{code}:{side}")
                continue
            if side == "sell":
                positions[code] = positions.get(code, 0) - amount
                if positions[code] <= 0:
                    positions.pop(code, None)
                    position_sector.pop(code, None)
                cash += value - trade_commission
                sell_value[sector] += value
                commission[sector] += trade_commission
            elif side == "buy":
                positions[code] = positions.get(code, 0) + amount
                position_sector[code] = sector
                cash -= value + trade_commission
                buy_value[sector] += value
                commission[sector] += trade_commission

        dividend_cash = {sleeve: 0.0 for sleeve in CORE_SLEEVES}
        for code, action in actions_by_date.get(day, {}).items():
            cash_per_share = action.get("net_cash_per_share", 0.0) or 0.0
            amount = positions.get(code, 0)
            if amount <= 0 or cash_per_share <= 0:
                continue
            sector = position_sector.get(code)
            if sector in dividend_cash:
                cash_amount = amount * cash_per_share
                cash += cash_amount
                dividend_cash[sector] += cash_amount

        valuation_prices = dict(last_close)
        valuation_prices.update(close_prices)
        end_sleeve_value = {sleeve: 0.0 for sleeve in CORE_SLEEVES}
        for code, amount in positions.items():
            sector = position_sector.get(code)
            if sector in end_sleeve_value:
                end_sleeve_value[sector] += amount * valuation_prices.get(code, 0.0)

        official_value = to_float(row.get("portfolio_value")) or 0.0
        reconstructed_value = cash + sum(end_sleeve_value.values())
        value_gap = reconstructed_value - official_value
        max_abs_value_gap = max(max_abs_value_gap, abs(value_gap))

        wide_row: dict[str, Any] = {
            "trade_date": day,
            "official_strategy_return": row.get("strategy_return"),
            "sum_sleeve_contribution_return": 0.0,
            "reconstructed_portfolio_value": reconstructed_value,
            "official_portfolio_value": official_value,
            "value_gap": value_gap,
            "cash": cash,
            "cash_weight": cash / reconstructed_value if reconstructed_value > 0 else 1.0,
        }
        total_pnl = 0.0
        for sleeve in CORE_SLEEVES:
            pnl = (
                end_sleeve_value[sleeve]
                - previous_sleeve_value[sleeve]
                - buy_value[sleeve]
                + sell_value[sleeve]
                + dividend_cash[sleeve]
                + action_pnl_by_sleeve[sleeve]
                - commission[sleeve]
            )
            contribution_return = pnl / previous_portfolio_value if previous_portfolio_value > 0 else 0.0
            local_return = pnl / previous_sleeve_value[sleeve] if previous_sleeve_value[sleeve] > 0 else ""
            total_pnl += pnl
            wide_row[f"{sleeve}_pnl"] = pnl
            wide_row[f"{sleeve}_contribution_return"] = contribution_return
            wide_row[f"{sleeve}_local_return"] = local_return
            wide_row[f"{sleeve}_end_value"] = end_sleeve_value[sleeve]
            wide_row[f"{sleeve}_end_weight"] = end_sleeve_value[sleeve] / reconstructed_value if reconstructed_value > 0 else 0.0
            pnl_rows.append(
                {
                    "trade_date": day,
                    "sleeve_id": sleeve,
                    "previous_sleeve_value": previous_sleeve_value[sleeve],
                    "end_sleeve_value": end_sleeve_value[sleeve],
                    "buy_value": buy_value[sleeve],
                    "sell_value": sell_value[sleeve],
                    "commission": commission[sleeve],
                    "dividend_cash": dividend_cash[sleeve],
                    "stock_action_value": action_pnl_by_sleeve[sleeve],
                    "pnl": pnl,
                    "contribution_return": contribution_return,
                    "local_return": local_return,
                }
            )

        wide_row["sum_sleeve_contribution_return"] = total_pnl / previous_portfolio_value if previous_portfolio_value > 0 else 0.0
        return_gap = wide_row["sum_sleeve_contribution_return"] - (to_float(row.get("strategy_return")) or 0.0)
        wide_row["return_gap"] = return_gap
        max_abs_return_gap = max(max_abs_return_gap, abs(return_gap))
        daily_wide.append(wide_row)

        previous_portfolio_value = official_value
        previous_sleeve_value = end_sleeve_value
        last_close.update(close_prices)

    quality_rows = [
        _quality("required_core_sleeve_count", len(CORE_SLEEVES) == 4, str(CORE_SLEEVES)),
        _quality("daily_row_count_matches_baseline", len(daily_wide) == len(daily_rows), f"{len(daily_wide)} vs {len(daily_rows)}"),
        _quality("trade_mapping_unmapped_events_zero", not unmapped_events, ";".join(unmapped_events[:10])),
        _quality("max_abs_return_gap_below_1bp", max_abs_return_gap < 0.0001, f"{max_abs_return_gap:.12f}"),
        _quality("max_abs_value_gap_below_1_cny", max_abs_value_gap < 1.0, f"{max_abs_value_gap:.6f}"),
        _quality("old_file_mojibake_observed_not_modified", True, "summary.json and sleeve_registry.csv contain mojibake path display; new outputs use ASCII field names and UTF-8."),
    ]
    return {
        "daily_wide": daily_wide,
        "pnl_rows": pnl_rows,
        "quality_rows": quality_rows,
        "unmapped_events": unmapped_events,
        "aggregation_check": {
            "max_abs_return_gap": max_abs_return_gap,
            "max_abs_value_gap": max_abs_value_gap,
        },
    }


def _build_signal_sector_map(signal_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = defaultdict(dict)
    for row in signal_rows:
        day = str(row.get("trade_date") or "")[:10]
        code = str(row.get("code") or "")
        sector = str(row.get("sector_id") or "")
        if day and code and sector:
            result[day][code] = sector
    return dict(sorted(result.items()))


def _build_latest_signal_day_by_date(dates: list[str], signal_sector_by_day_code: dict[str, dict[str, str]]) -> dict[str, str]:
    signal_days = sorted(signal_sector_by_day_code)
    result: dict[str, str] = {}
    idx = -1
    for day in sorted(dates):
        while idx + 1 < len(signal_days) and signal_days[idx + 1] <= day:
            idx += 1
        if idx >= 0:
            result[day] = signal_days[idx]
    return result


def _lookup_signal_sector(code: str, day: str, signal_sector_by_day_code: dict[str, dict[str, str]]) -> str:
    for signal_day in sorted(signal_sector_by_day_code, reverse=True):
        if signal_day <= day and code in signal_sector_by_day_code[signal_day]:
            return signal_sector_by_day_code[signal_day][code]
    return ""


def _build_metrics_rows(daily_wide: list[dict[str, Any]], daily_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    baseline_returns = [to_float(row.get("strategy_return")) or 0.0 for row in daily_rows]
    rows: list[dict[str, Any]] = []
    for sleeve in CORE_SLEEVES:
        contribution_returns = [float(row[f"{sleeve}_contribution_return"]) for row in daily_wide]
        local_returns = [float(row[f"{sleeve}_local_return"]) for row in daily_wide if row[f"{sleeve}_local_return"] != ""]
        local_curve = _curve(local_returns)
        contribution_curve = _curve(contribution_returns)
        max_dd, dd_start, dd_end = _max_drawdown(local_curve, [row["trade_date"] for row in daily_wide if row[f"{sleeve}_local_return"] != ""])
        rows.append(
            {
                "sleeve_id": sleeve,
                "cumulative_local_return": local_curve[-1] - 1.0 if local_curve else "",
                "cumulative_contribution_return": contribution_curve[-1] - 1.0 if contribution_curve else "",
                "annualized_local_return": _annualize(local_curve[-1] - 1.0, len(local_returns), 252) if local_curve else "",
                "annualized_contribution_return": _annualize(contribution_curve[-1] - 1.0, len(contribution_returns), 252) if contribution_curve else "",
                "volatility_local": _volatility(local_returns, 252),
                "volatility_contribution": _volatility(contribution_returns, 252),
                "max_drawdown_local": max_dd,
                "max_drawdown_local_interval": f"{dd_start},{dd_end}" if dd_start and dd_end else "",
                "sharpe_local": _sharpe(local_returns, 252),
                "daily_win_rate_local": _positive_ratio(local_returns),
                "corr_with_v57f_total": _corr(local_returns[-len(baseline_returns) :], baseline_returns[-len(local_returns) :]) if local_returns else "",
                "average_end_weight": mean([float(row[f"{sleeve}_end_weight"]) for row in daily_wide]),
            }
        )
    return rows


def _build_correlation_matrix(daily_wide: list[dict[str, Any]]) -> list[dict[str, Any]]:
    local_by_sleeve = {
        sleeve: [float(row[f"{sleeve}_local_return"]) for row in daily_wide if row[f"{sleeve}_local_return"] != ""]
        for sleeve in CORE_SLEEVES
    }
    rows = []
    for left in CORE_SLEEVES:
        row = {"sleeve_id": left}
        for right in CORE_SLEEVES:
            n = min(len(local_by_sleeve[left]), len(local_by_sleeve[right]))
            row[right] = _corr(local_by_sleeve[left][-n:], local_by_sleeve[right][-n:]) if n >= 2 else ""
        rows.append(row)
    return rows


def _build_drawdown_contribution_rows(
    daily_wide: list[dict[str, Any]],
    daily_rows: list[dict[str, str]],
    baseline_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    interval = str(baseline_summary.get("metrics", {}).get("max_drawdown_interval") or "")
    if "," in interval:
        dd_start, dd_end = interval.split(",", 1)
    else:
        curve = _curve([to_float(row.get("strategy_return")) or 0.0 for row in daily_rows])
        _dd, dd_start, dd_end = _max_drawdown(curve, [row["trade_date"] for row in daily_rows])
    rows = []
    total_pnl = 0.0
    for sleeve in CORE_SLEEVES:
        pnl = sum(
            float(row[f"{sleeve}_pnl"])
            for row in daily_wide
            if dd_start <= row["trade_date"] <= dd_end
        )
        total_pnl += pnl
        rows.append(
            {
                "sleeve_id": sleeve,
                "drawdown_start": dd_start,
                "drawdown_end": dd_end,
                "pnl_contribution": pnl,
            }
        )
    for row in rows:
        row["share_of_interval_sleeve_pnl"] = float(row["pnl_contribution"]) / total_pnl if total_pnl else ""
    return rows


def _build_risk_contribution_rows(daily_wide: list[dict[str, Any]]) -> list[dict[str, Any]]:
    portfolio_returns = [float(row["sum_sleeve_contribution_return"]) for row in daily_wide]
    portfolio_variance = _variance(portfolio_returns)
    vol_by_sleeve = {}
    for sleeve in CORE_SLEEVES:
        local_returns = [float(row[f"{sleeve}_local_return"]) for row in daily_wide if row[f"{sleeve}_local_return"] != ""]
        contribution_returns = [float(row[f"{sleeve}_contribution_return"]) for row in daily_wide]
        vol_by_sleeve[sleeve] = {
            "local": _volatility(local_returns, 252) or 0.0,
            "contribution": _volatility(contribution_returns, 252) or 0.0,
            "covariance_risk": _covariance(contribution_returns, portfolio_returns) / portfolio_variance if portfolio_variance else 0.0,
        }
    total_local = sum(item["local"] for item in vol_by_sleeve.values())
    total_contribution = sum(item["contribution"] for item in vol_by_sleeve.values())
    rows = []
    for sleeve in CORE_SLEEVES:
        rows.append(
            {
                "sleeve_id": sleeve,
                "standalone_volatility": vol_by_sleeve[sleeve]["local"],
                "contribution_return_volatility": vol_by_sleeve[sleeve]["contribution"],
                "standalone_vol_risk_share": vol_by_sleeve[sleeve]["local"] / total_local if total_local else "",
                "contribution_vol_risk_share": vol_by_sleeve[sleeve]["contribution"] / total_contribution if total_contribution else "",
                "covariance_portfolio_variance_contribution": vol_by_sleeve[sleeve]["covariance_risk"],
                "average_weight": mean([float(row[f"{sleeve}_end_weight"]) for row in daily_wide]),
            }
        )
    return rows


def _build_readiness_rows(
    attribution: dict[str, Any],
    metrics_rows: list[dict[str, Any]],
    quality_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    checks = {
        row["check_id"]: row["status"] == "pass"
        for row in quality_rows
    }
    metric_complete = all(row.get("volatility_local") not in ("", None) for row in metrics_rows)
    rows = [
        _readiness("daily_sleeve_returns_complete", len(attribution["daily_wide"]) > 0 and metric_complete, "All four core sleeve return columns are present."),
        _readiness("sleeve_mapping_auditable", checks.get("trade_mapping_unmapped_events_zero", False), "Mapping uses rebalance_signals sector_id plus carried position sector."),
        _readiness("aggregation_consistent_with_v57f", checks.get("max_abs_return_gap_below_1bp", False), json.dumps(attribution["aggregation_check"])),
        _readiness("drawdown_contribution_explainable", checks.get("max_abs_return_gap_below_1bp", False), "Official V57f drawdown interval can be decomposed by sleeve PnL."),
        _readiness("ready_for_fixed_rule_risk_budget_spec", checks.get("trade_mapping_unmapped_events_zero", False) and checks.get("max_abs_return_gap_below_1bp", False) and metric_complete, "Allowed next step is fixed-rule Quant spec only; no parameter search."),
    ]
    blocker_rows = [
        {
            "blocked_item": "dividend_safety_and_fcf_ocf_reducer_engineering",
            "reason": "Still requires PIT dividend announcement dates and financial statement lag contracts.",
            "allowed_next_action": "data gate feasibility audit only",
        },
        {
            "blocked_item": "valuation_and_crowding_overheat_engineering",
            "reason": "Still lacks audited PIT valuation percentile and crowding datasets.",
            "allowed_next_action": "data gate requirement packet only",
        },
        {
            "blocked_item": "risk_budget_parameter_search",
            "reason": "Sweeping windows, caps or risk budgets against 2021-2026 would overfit.",
            "allowed_next_action": "pre-register one or two fixed simple rules before any engineering test",
        },
    ]
    if not all(row["status"] == "pass" for row in rows):
        blocker_rows.insert(
            0,
            {
                "blocked_item": "sleeve_level_attribution_readiness",
                "reason": "One or more sleeve attribution readiness checks failed.",
                "allowed_next_action": "repair mapping or reconciliation before any risk budget overlay",
            },
        )
        status = "blocked_before_risk_budget_overlay"
    else:
        status = "sleeve_level_attribution_ready_for_fixed_rule_risk_budget_spec"
    return rows, blocker_rows, status


def _build_report(
    summary: dict[str, Any],
    metrics_rows: list[dict[str, Any]],
    risk_rows: list[dict[str, Any]],
    drawdown_rows: list[dict[str, Any]],
    readiness_rows: list[dict[str, Any]],
    blocker_rows: list[dict[str, Any]],
) -> str:
    lines = [
        "# V5c Sleeve-Level Risk Attribution",
        "",
        "This packet reconstructs daily sleeve returns and PnL for the frozen V57f core. It does not modify V57f and does not test a new overlay.",
        "",
        "## Status",
        "",
        f"- Baseline: `{summary['baseline_strategy_id']}`",
        f"- Window: `{summary['window']}`",
        f"- V57f core modified: `{summary['v57f_core_modified']}`",
        f"- Risk budget readiness: `{summary['risk_budget_overlay_readiness']}`",
        f"- Aggregation max return gap: `{summary['aggregation_check']['max_abs_return_gap']:.12f}`",
        "",
        "## Sleeve Metrics",
        "",
        "| Sleeve | Local return | Local volatility | Max drawdown | Corr with V57f | Avg weight |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in metrics_rows:
        lines.append(
            "| {sleeve_id} | {ret} | {vol} | {dd} | {corr} | {weight} |".format(
                sleeve_id=row["sleeve_id"],
                ret=_pct(row.get("cumulative_local_return")),
                vol=_pct(row.get("volatility_local")),
                dd=_pct(row.get("max_drawdown_local")),
                corr=_num(row.get("corr_with_v57f_total")),
                weight=_pct(row.get("average_end_weight")),
            )
        )
    lines.extend(
        [
            "",
            "## Risk Contribution",
            "",
            "| Sleeve | Standalone vol risk share | Contribution vol risk share | Covariance risk contribution |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in risk_rows:
        lines.append(
            f"| {row['sleeve_id']} | {_pct(row['standalone_vol_risk_share'])} | "
            f"{_pct(row['contribution_vol_risk_share'])} | "
            f"{_pct(row['covariance_portfolio_variance_contribution'])} |"
        )
    lines.extend(["", "## Official Max Drawdown Contribution", "", "| Sleeve | PnL contribution | Share |", "|---|---:|---:|"])
    for row in drawdown_rows:
        lines.append(f"| {row['sleeve_id']} | {_num(row['pnl_contribution'])} | {_pct(row['share_of_interval_sleeve_pnl'])} |")
    lines.extend(["", "## Readiness", ""])
    for row in readiness_rows:
        lines.append(f"- `{row['check_id']}`: `{row['status']}` - {row['detail']}")
    lines.extend(["", "## Still Blocked", ""])
    for row in blocker_rows:
        lines.append(f"- `{row['blocked_item']}`: {row['reason']}")
    return "\n".join(lines) + "\n"


def _build_agent_rules() -> str:
    return """# V5c Sleeve Attribution Agent Rules

- Do not modify V57f core sleeves, weights, factors, rebalance logic or execution timing.
- Do not test new defense, profit-taking, overheat or CPPI thresholds from this packet.
- Use the sleeve daily returns only to draft a fixed-rule risk budget spec.
- Do not optimize risk budget windows, caps or target contributions on 2021-2026.
- Dividend safety, FCF/OCF reducers, valuation overheat and crowding remain data-gate tasks until PIT contracts exist.
- Stop and ask the user only if JoinQuant exports, external data, live trading, or a V57f core change is required.
"""


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _quality(check_id: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"check_id": check_id, "status": "pass" if passed else "fail", "detail": detail}


def _readiness(check_id: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"check_id": check_id, "status": "pass" if passed else "blocked", "detail": detail}


def _fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    return fields


def _curve(returns: list[float]) -> list[float]:
    nav = 1.0
    values = []
    for ret in returns:
        nav *= 1.0 + ret
        values.append(nav)
    return values


def _annualize(total_return: float, periods: int, annual_factor: int) -> float | None:
    if periods <= 0 or total_return <= -1:
        return None
    return (1.0 + total_return) ** (annual_factor / periods) - 1.0


def _volatility(returns: list[float], annual_factor: int) -> float | None:
    if len(returns) < 2:
        return None
    return pstdev(returns) * math.sqrt(annual_factor)


def _sharpe(returns: list[float], annual_factor: int) -> float | None:
    if len(returns) < 2:
        return None
    vol = pstdev(returns)
    return (mean(returns) / vol) * math.sqrt(annual_factor) if vol > 0 else None


def _positive_ratio(values: list[float]) -> float | None:
    return sum(1 for value in values if value > 0) / len(values) if values else None


def _corr(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    lm = mean(left)
    rm = mean(right)
    lv = sum((x - lm) ** 2 for x in left)
    rv = sum((x - rm) ** 2 for x in right)
    if lv <= 0 or rv <= 0:
        return None
    cov = sum((x - lm) * (y - rm) for x, y in zip(left, right))
    return cov / math.sqrt(lv * rv)


def _variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    center = mean(values)
    return sum((value - center) ** 2 for value in values) / len(values)


def _covariance(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 0.0
    lm = mean(left)
    rm = mean(right)
    return sum((x - lm) * (y - rm) for x, y in zip(left, right)) / len(left)


def _max_drawdown(curve: list[float], dates: list[str]) -> tuple[float | None, str | None, str | None]:
    if not curve:
        return None, None, None
    peak = curve[0]
    peak_date = dates[0]
    max_dd = 0.0
    dd_start = dates[0]
    dd_end = dates[0]
    for value, day in zip(curve, dates):
        if value > peak:
            peak = value
            peak_date = day
        if peak > 0:
            dd = value / peak - 1.0
            if dd < max_dd:
                max_dd = dd
                dd_start = peak_date
                dd_end = day
    return abs(max_dd), dd_start, dd_end


def _pct(value: Any) -> str:
    number = to_float(value)
    return "" if number is None else f"{number:.2%}"


def _num(value: Any) -> str:
    number = to_float(value)
    return "" if number is None else f"{number:.4f}"


if __name__ == "__main__":
    run_v5c_sleeve_level_risk_attribution(Path("."))

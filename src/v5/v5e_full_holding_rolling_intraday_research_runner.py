from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5e_full_holding_rolling_intraday_research") / "current"
FULL_GATE_DIR = Path("v5e_full_holding_5min_data_gate") / "current"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
MODEL_COMPARISON = Path("v5e_profit_lock_model_comparison") / "current" / "v5e_model_comparison_summary.json"
INITIAL_CAPITAL = 2_000_000.0


@dataclass(frozen=True)
class IntradayModel:
    model_id: str
    profit_threshold: float | None = None
    profit_sell_fraction: float = 0.0
    trailing_peak_threshold: float | None = None
    trailing_drawdown_threshold: float | None = None
    trailing_sell_fraction: float = 0.0


MODELS = [
    IntradayModel("intraday_profit_lock_main_20pct_sell50", profit_threshold=0.20, profit_sell_fraction=0.50),
    IntradayModel("intraday_profit_lock_conservative_30pct_sell33", profit_threshold=0.30, profit_sell_fraction=0.33),
    IntradayModel("intraday_trailing_main_peak15_drawdown8_sell50", trailing_peak_threshold=0.15, trailing_drawdown_threshold=-0.08, trailing_sell_fraction=0.50),
    IntradayModel("intraday_trailing_conservative_peak20_drawdown10_sell33", trailing_peak_threshold=0.20, trailing_drawdown_threshold=-0.10, trailing_sell_fraction=0.33),
    IntradayModel(
        "intraday_combined_main_profit_lock_plus_trailing",
        profit_threshold=0.20,
        profit_sell_fraction=0.50,
        trailing_peak_threshold=0.15,
        trailing_drawdown_threshold=-0.08,
        trailing_sell_fraction=0.50,
    ),
    IntradayModel(
        "intraday_combined_conservative_profit_lock_plus_trailing",
        profit_threshold=0.30,
        profit_sell_fraction=0.33,
        trailing_peak_threshold=0.20,
        trailing_drawdown_threshold=-0.10,
        trailing_sell_fraction=0.33,
    ),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_full_holding_rolling_intraday_research(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_full_intraday_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_full_intraday_summary.json", summary)
        return summary

    gate = json.loads((root / FULL_GATE_DIR / "v5e_full_holding_5min_summary.json").read_text(encoding="utf-8"))
    cycles = _holding_cycles(root)
    path_map = _path_map(root)
    event_log = _event_log(root, cycles, path_map)
    model_comparison = _model_comparison(event_log)
    period_model = _period_model_rows(event_log)
    rolling = _rolling_selection(period_model)
    previous = _previous_comparison(root, model_comparison, rolling)
    decision = _pm_gate_decision(model_comparison, rolling)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers = _nonfatal_blockers(event_log, gate)

    _write_csv(out / "v5e_full_intraday_event_log.csv", event_log)
    _write_csv(out / "v5e_full_intraday_model_comparison.csv", model_comparison)
    _write_csv(out / "v5e_full_intraday_period_model_result.csv", period_model)
    _write_csv(out / "v5e_full_intraday_rolling_model_selection.csv", rolling)
    _write_csv(out / "v5e_full_intraday_vs_previous_comparison.csv", previous)
    _write_csv(out / "v5e_full_intraday_pm_gate_decision.csv", decision)
    _write_csv(out / "v5e_full_intraday_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5e_full_intraday_blockers.csv", blockers)
    (out / "v5e_full_intraday_report.md").write_text(_report(model_comparison, rolling, decision), encoding="utf-8")
    (out / "v5e_full_intraday_next_prompt.md").write_text(_next_prompt(), encoding="utf-8")
    (out / "v5e_full_intraday_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    best = model_comparison[0] if model_comparison else {}
    rolling_total = sum(float(row["selected_oos_delta_value"]) for row in rolling)
    summary = _summary(
        "completed_full_holding_rolling_intraday_research",
        decision[0]["pm_gate_decision"],
        [],
        event_count=len(event_log),
        best_model_id=str(best.get("model_id", "")),
        best_model_incremental_return=float(best.get("incremental_return_vs_hold", 0.0)),
        rolling_oos_incremental_return=rolling_total / INITIAL_CAPITAL,
        full_5min_effective_coverage_rate_pct=float(gate.get("effective_coverage_rate_pct", 0.0)),
    )
    _write_json(out / "v5e_full_intraday_summary.json", summary)
    return summary


def _holding_cycles(root: Path) -> list[dict[str, Any]]:
    holdings = pd.read_csv(root / REPAIRED_RUN / "holdings.csv")
    signals = pd.read_csv(root / REPAIRED_RUN / "rebalance_signals.csv")
    rebalance_dates = sorted(signals["trade_date"].astype(str).unique().tolist())
    sleeve_map = {
        (str(row["trade_date"]), str(row["code"])): str(row.get("sector_id", ""))
        for _, row in signals.iterrows()
        if pd.notna(row.get("code", ""))
    }
    cycles = []
    for _, row in holdings.iterrows():
        start = str(row["trade_date"])
        code = str(row["code"])
        cycles.append(
            {
                "cycle_id": f"{start}|{code}",
                "holding_start_date": start,
                "next_rebalance_date": _next_rebalance(start, rebalance_dates),
                "code": code,
                "sleeve": sleeve_map.get((start, code), ""),
                "amount": float(row.get("amount", 0.0)),
                "entry_price": float(row.get("close", 0.0)),
            }
        )
    return cycles


def _path_map(root: Path) -> dict[tuple[str, str], str]:
    df = pd.read_csv(root / FULL_GATE_DIR / "v5e_full_holding_5min_available_windows.csv")
    return {(str(row["code"]), str(row["trade_date"])): str(row["path"]) for _, row in df.iterrows()}


def _event_log(root: Path, cycles: list[dict[str, Any]], path_map: dict[tuple[str, str], str]) -> list[dict[str, Any]]:
    rows = []
    for cycle in cycles:
        bars = _cycle_bars(root, cycle, path_map)
        if bars.empty:
            for model in MODELS:
                rows.append(_no_trigger_row(cycle, model, "no_minute_bars"))
            continue
        final_close = float(bars.iloc[-1]["close"])
        for model in MODELS:
            rows.append(_model_event(cycle, model, bars, final_close))
    return rows


def _cycle_bars(root: Path, cycle: dict[str, Any], path_map: dict[tuple[str, str], str]) -> pd.DataFrame:
    dates = sorted(day for code, day in path_map if code == cycle["code"] and day >= cycle["holding_start_date"] and (not cycle["next_rebalance_date"] or day < cycle["next_rebalance_date"]))
    frames = []
    for day in dates:
        path = root / Path(path_map[(cycle["code"], day)])
        if path.exists():
            df = pd.read_csv(path)
            df = df[df["code"].astype(str).eq(cycle["code"])].copy()
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    bars = pd.concat(frames, ignore_index=True)
    bars["sort_key"] = bars["trade_date"].astype(str) + " " + bars["time"].astype(str)
    bars = bars.sort_values("sort_key").reset_index(drop=True)
    return bars


def _model_event(cycle: dict[str, Any], model: IntradayModel, bars: pd.DataFrame, final_close: float) -> dict[str, Any]:
    entry = float(cycle["entry_price"])
    amount = float(cycle["amount"])
    if entry <= 0 or amount <= 0:
        return _no_trigger_row(cycle, model, "invalid_entry_or_amount")
    peak_close = entry
    trigger_idx: int | None = None
    trigger_reason = ""
    sell_fraction = 0.0
    for idx, row in bars.iterrows():
        close = float(row["close"])
        peak_close = max(peak_close, close)
        holding_return = close / entry - 1.0
        drawdown = close / peak_close - 1.0 if peak_close else 0.0
        profit_hit = model.profit_threshold is not None and holding_return >= model.profit_threshold
        trailing_hit = (
            model.trailing_peak_threshold is not None
            and peak_close / entry - 1.0 >= model.trailing_peak_threshold
            and drawdown <= float(model.trailing_drawdown_threshold)
        )
        if profit_hit or trailing_hit:
            trigger_idx = idx
            if profit_hit:
                trigger_reason = "intraday_profit_lock"
                sell_fraction = model.profit_sell_fraction
            else:
                trigger_reason = "intraday_trailing_protection"
                sell_fraction = model.trailing_sell_fraction
            break
    if trigger_idx is None:
        return _no_trigger_row(cycle, model, "no_trigger", final_close=final_close)
    execution_idx = trigger_idx + 1
    if execution_idx >= len(bars):
        return _no_trigger_row(cycle, model, "trigger_last_bar_unfilled", final_close=final_close)
    trigger = bars.iloc[trigger_idx]
    execution = bars.iloc[execution_idx]
    execution_price = float(execution["open"])
    final_return = final_close / execution_price - 1.0 if execution_price else 0.0
    exit_value = amount * sell_fraction * execution_price
    delta = -final_return * exit_value
    return {
        **_base_row(cycle, model),
        "triggered": True,
        "trigger_reason": trigger_reason,
        "trigger_datetime": str(trigger.get("datetime", "")),
        "trigger_trade_date": str(trigger.get("trade_date", "")),
        "execution_datetime": str(execution.get("datetime", "")),
        "execution_trade_date": str(execution.get("trade_date", "")),
        "execution_price": execution_price,
        "sell_fraction": sell_fraction,
        "exit_value": exit_value,
        "final_close_before_rebalance": final_close,
        "post_exit_return_if_held_sold_fraction": final_return,
        "incremental_value_vs_hold_sold_fraction": delta,
        "incremental_return_vs_hold": delta / INITIAL_CAPITAL,
        "cash_helped": delta > 0,
        "cash_hurt": delta < 0,
        "future_information_used_for_trigger": False,
        "execution_after_trigger": True,
        "accepted": False,
    }


def _no_trigger_row(cycle: dict[str, Any], model: IntradayModel, reason: str, final_close: float = 0.0) -> dict[str, Any]:
    return {
        **_base_row(cycle, model),
        "triggered": False,
        "trigger_reason": reason,
        "trigger_datetime": "",
        "trigger_trade_date": "",
        "execution_datetime": "",
        "execution_trade_date": "",
        "execution_price": "",
        "sell_fraction": 0.0,
        "exit_value": 0.0,
        "final_close_before_rebalance": final_close,
        "post_exit_return_if_held_sold_fraction": 0.0,
        "incremental_value_vs_hold_sold_fraction": 0.0,
        "incremental_return_vs_hold": 0.0,
        "cash_helped": False,
        "cash_hurt": False,
        "future_information_used_for_trigger": False,
        "execution_after_trigger": False,
        "accepted": False,
    }


def _base_row(cycle: dict[str, Any], model: IntradayModel) -> dict[str, Any]:
    return {
        "model_id": model.model_id,
        "cycle_id": cycle["cycle_id"],
        "holding_start_date": cycle["holding_start_date"],
        "next_rebalance_date": cycle["next_rebalance_date"],
        "code": cycle["code"],
        "sleeve": cycle["sleeve"],
        "amount": cycle["amount"],
        "entry_price": cycle["entry_price"],
        "threshold_status": "fixed_pre_registered_family_not_grid_scan",
        "uses_5min_trigger": True,
        "trigger_visible_at_bar_close": True,
    }


def _model_comparison(event_log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    df = pd.DataFrame(event_log)
    for model_id, group in df.groupby("model_id"):
        delta = float(group["incremental_value_vs_hold_sold_fraction"].sum())
        exit_value = float(group["exit_value"].sum())
        triggered = int(group["triggered"].sum())
        helped = int(group["cash_helped"].sum())
        hurt = int(group["cash_hurt"].sum())
        rows.append(
            {
                "model_id": model_id,
                "cycle_count": int(len(group)),
                "trigger_count": triggered,
                "cash_helped_count": helped,
                "cash_hurt_count": hurt,
                "exit_value": exit_value,
                "incremental_value_vs_hold": delta,
                "incremental_return_vs_hold": delta / INITIAL_CAPITAL,
                "incremental_return_pct_points_vs_hold": delta / INITIAL_CAPITAL * 100.0,
                "hit_rate_helped_among_triggers": helped / triggered if triggered else 0.0,
                "uses_5min_trigger": True,
                "future_information_used_for_trigger": False,
                "accepted": False,
            }
        )
    return sorted(rows, key=lambda row: float(row["incremental_value_vs_hold"]), reverse=True)


def _period_model_rows(event_log: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(event_log)
    rows = []
    for (period, model_id), group in df.groupby(["holding_start_date", "model_id"]):
        delta = float(group["incremental_value_vs_hold_sold_fraction"].sum())
        rows.append(
            {
                "holding_start_date": period,
                "model_id": model_id,
                "trigger_count": int(group["triggered"].sum()),
                "incremental_value_vs_hold": delta,
                "incremental_return_vs_hold": delta / INITIAL_CAPITAL,
            }
        )
    return sorted(rows, key=lambda row: (row["holding_start_date"], row["model_id"]))


def _rolling_selection(period_rows: list[dict[str, Any]], lookback_periods: int = 4) -> list[dict[str, Any]]:
    df = pd.DataFrame(period_rows)
    periods = sorted(df["holding_start_date"].unique().tolist())
    rows = []
    default_model = "intraday_profit_lock_main_20pct_sell50"
    for idx, period in enumerate(periods):
        if idx < lookback_periods:
            selected = default_model
            method = "warmup_default_until_4_periods"
        else:
            train_periods = periods[idx - lookback_periods : idx]
            train = df[df["holding_start_date"].isin(train_periods)]
            scores = train.groupby("model_id")["incremental_value_vs_hold"].sum().sort_values(ascending=False)
            selected = str(scores.index[0])
            method = "rolling_prior_4_periods_best_incremental_value"
        row = df[(df["holding_start_date"].eq(period)) & df["model_id"].eq(selected)].iloc[0]
        rows.append(
            {
                "holding_start_date": period,
                "selected_model_id": selected,
                "selection_method": method,
                "selected_oos_trigger_count": int(row["trigger_count"]),
                "selected_oos_delta_value": float(row["incremental_value_vs_hold"]),
                "selected_oos_incremental_return": float(row["incremental_return_vs_hold"]),
                "uses_future_information_for_selection": False,
            }
        )
    return rows


def _previous_comparison(root: Path, model_comparison: list[dict[str, Any]], rolling: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previous = json.loads((root / MODEL_COMPARISON).read_text(encoding="utf-8"))
    best = model_comparison[0]
    rolling_value = sum(float(row["selected_oos_delta_value"]) for row in rolling)
    return [
        {
            "comparison_id": "previous_v5e_profit_lock_daily_open_200w",
            "model_id": previous["candidate_id"],
            "incremental_return_pct_points": previous["daily_open_delta_return_pct_points_200w"],
            "scope": "daily close trigger and T+1 daily open proxy",
        },
        {
            "comparison_id": "previous_v5e_profit_lock_vwap_adjusted_200w",
            "model_id": previous["candidate_id"],
            "incremental_return_pct_points": previous["vwap_adjusted_delta_return_pct_points_200w"],
            "scope": "daily trigger with 5min VWAP execution proxy",
        },
        {
            "comparison_id": "best_static_full_intraday_event_model",
            "model_id": best["model_id"],
            "incremental_return_pct_points": best["incremental_return_pct_points_vs_hold"],
            "scope": "full holding-period 5min trigger event-level model versus continuing sold fraction",
        },
        {
            "comparison_id": "rolling_selected_full_intraday_model",
            "model_id": "rolling_prior_4_periods_selected_model",
            "incremental_return_pct_points": rolling_value / INITIAL_CAPITAL * 100.0,
            "scope": "rolling out-of-sample period selection using prior completed periods only",
        },
    ]


def _pm_gate_decision(model_comparison: list[dict[str, Any]], rolling: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best = model_comparison[0]
    rolling_value = sum(float(row["selected_oos_delta_value"]) for row in rolling)
    rolling_return = rolling_value / INITIAL_CAPITAL
    if rolling_return > 0 and float(best["incremental_value_vs_hold"]) > 0:
        decision = "promote_full_intraday_rolling_candidate_to_nav_engineering_not_accepted"
        next_gate = "v5e_full_intraday_nav_engineering_test"
    else:
        decision = "remain_diagnostic_or_open_sleeve_cash_policy"
        next_gate = "v5e_sleeve_cash_policy_quant_spec"
    return [
        {
            "pm_gate_decision": decision,
            "next_gate": next_gate,
            "best_static_model_id": best["model_id"],
            "best_static_incremental_return_pct_points": best["incremental_return_pct_points_vs_hold"],
            "rolling_oos_incremental_return_pct_points": rolling_return * 100.0,
            "accepted": False,
            "v57f_core_modified": False,
            "future_information_used_for_selection": False,
            "reason": "Rolling selection uses only prior completed periods. Promotion is to NAV engineering test, not acceptance.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_gate": "v5e_full_intraday_nav_engineering_test" if decision.startswith("promote") else "v5e_sleeve_cash_policy_quant_spec",
            "task": "Run complete NAV engineering for rolling-selected full intraday candidate" if decision.startswith("promote") else "Continue sleeve cash policy spec",
            "allowed": True,
        }
    ]


def _nonfatal_blockers(event_log: list[dict[str, Any]], gate: dict[str, Any]) -> list[dict[str, Any]]:
    unfilled = sum(1 for row in event_log if row["trigger_reason"] == "trigger_last_bar_unfilled")
    rows = []
    if unfilled:
        rows.append({"blocker_id": "last_bar_triggers_unfilled", "severity": "execution_model", "status": "review_required", "count": unfilled})
    if float(gate.get("effective_coverage_rate_pct", 0.0)) < 100.0:
        rows.append({"blocker_id": "full_5min_effective_coverage_below_100", "severity": "data_gate", "status": "review_required"})
    if not rows:
        rows.append({"blocker_id": "none", "severity": "none", "status": "not_blocking"})
    return rows


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    event_count: int = 0,
    best_model_id: str = "",
    best_model_incremental_return: float = 0.0,
    rolling_oos_incremental_return: float = 0.0,
    full_5min_effective_coverage_rate_pct: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_full_holding_rolling_intraday_research",
        "status": status,
        "pm_gate_decision": decision,
        "event_count": event_count,
        "best_model_id": best_model_id,
        "best_static_incremental_return_pct_points": best_model_incremental_return * 100.0,
        "rolling_oos_incremental_return_pct_points": rolling_oos_incremental_return * 100.0,
        "full_5min_effective_coverage_rate_pct": full_5min_effective_coverage_rate_pct,
        "uses_5min_trigger": True,
        "rolling_selection_used": True,
        "future_information_used_for_selection": False,
        "accepted": False,
        "v57f_core_modified": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(model_comparison: list[dict[str, Any]], rolling: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    best = model_comparison[0]
    rolling_return = sum(float(row["selected_oos_delta_value"]) for row in rolling) / INITIAL_CAPITAL * 100.0
    return "\n".join(
        [
            "# V5e Full Holding-Period Rolling Intraday Research",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Best static model: `{best['model_id']}`",
            f"- Best static event-level incremental return: {best['incremental_return_pct_points_vs_hold']:.4f} pct points",
            f"- Rolling OOS incremental return: {rolling_return:.4f} pct points",
            "- Result is research candidate only; not accepted.",
            "",
        ]
    )


def _next_prompt() -> str:
    return """工作目录：
D:\\hh\\codex\\v5

任务名称：
V5e full intraday NAV engineering test

任务目标：
基于 `v5e_full_holding_rolling_intraday_research/current/` 的 rolling selected full intraday candidate，执行完整 NAV engineering test。必须保持 rolling 选择只用过去已完成周期，不得使用未来结果，不得修改 V57f，不得 accepted。
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Full Intraday Rolling Research Rules",
            "",
            "- Use fixed candidate families only; no threshold grid scan.",
            "- Trigger is visible only after 5min bar close.",
            "- Execution occurs at the next 5min bar open.",
            "- Rolling selection uses prior completed periods only.",
            "- Research candidate only; not accepted.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        FULL_GATE_DIR / "v5e_full_holding_5min_summary.json",
        FULL_GATE_DIR / "v5e_full_holding_5min_available_windows.csv",
        REPAIRED_RUN / "holdings.csv",
        REPAIRED_RUN / "rebalance_signals.csv",
        MODEL_COMPARISON,
    ]
    return [{"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)} for path in required if not (root / path).exists()]


def _next_rebalance(day: str, rebalance_dates: list[str]) -> str:
    later = [d for d in rebalance_dates if d > day]
    return later[0] if later else ""


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    result = run_v5e_full_holding_rolling_intraday_research()
    print(json.dumps(result, ensure_ascii=False, indent=2))

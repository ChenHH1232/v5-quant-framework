from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5e_full_intraday_nav_engineering_test") / "current"
RESEARCH_DIR = Path("v5e_full_holding_rolling_intraday_research") / "current"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
PRICE_DIR = Path("数据库") / "processed" / "startup_preload_repaired_prices_v5"
PREVIOUS_COMPARISON = Path("v5e_profit_lock_model_comparison") / "current" / "v5e_model_comparison_summary.json"
INITIAL_CAPITAL = 2_000_000.0
COMMISSION_RATE = 0.0003
MIN_COMMISSION = 5.0


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_full_intraday_nav_engineering(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    run_dir = out / "runs"
    out.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_full_intraday_nav_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_full_intraday_nav_summary.json", summary)
        return summary

    baseline = pd.read_csv(root / REPAIRED_RUN / "daily_returns.csv")
    event_log = pd.read_csv(root / RESEARCH_DIR / "v5e_full_intraday_event_log.csv")
    rolling = pd.read_csv(root / RESEARCH_DIR / "v5e_full_intraday_rolling_model_selection.csv")
    closes = _close_map(root)
    selected_events = _selected_events(event_log, rolling)
    best_model_id = _best_static_model(root)
    best_static_events = event_log[event_log["model_id"].eq(best_model_id) & event_log["triggered"].eq(True)].copy()

    variants = [
        _nav_variant("v57f_repaired_baseline", baseline, pd.DataFrame(), closes),
        _nav_variant(f"full_intraday_static_{best_model_id}", baseline, best_static_events, closes),
        _nav_variant("full_intraday_rolling_selected_prior4", baseline, selected_events, closes),
    ]
    metrics = [_metrics(row["version_id"], row["daily"]) for row in variants]
    baseline_metrics = next(row for row in metrics if row["version_id"] == "v57f_repaired_baseline")
    comparison = [_comparison(row, baseline_metrics) for row in metrics]
    event_summary = _event_summary(selected_events, best_static_events)
    previous = _previous_comparison(root, comparison)
    decision = _pm_gate_decision(comparison, previous)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers = _nonfatal_blockers(selected_events)

    for variant in variants:
        vdir = run_dir / variant["version_id"]
        vdir.mkdir(parents=True, exist_ok=True)
        _write_csv(vdir / "daily_returns.csv", variant["daily"])
        _write_csv(vdir / "overlay_events.csv", variant["events"])
    _write_csv(out / "v5e_full_intraday_nav_metrics.csv", comparison)
    _write_csv(out / "v5e_full_intraday_nav_event_summary.csv", event_summary)
    _write_csv(out / "v5e_full_intraday_nav_vs_previous.csv", previous)
    _write_csv(out / "v5e_full_intraday_nav_pm_gate_decision.csv", decision)
    _write_csv(out / "v5e_full_intraday_nav_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5e_full_intraday_nav_blockers.csv", blockers)
    (out / "v5e_full_intraday_nav_report.md").write_text(_report(comparison, previous, decision), encoding="utf-8")
    (out / "v5e_full_intraday_nav_next_prompt.md").write_text(_next_prompt(), encoding="utf-8")
    (out / "v5e_full_intraday_nav_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    rolling_metrics = next(row for row in comparison if row["version_id"] == "full_intraday_rolling_selected_prior4")
    summary = _summary(
        "completed_full_intraday_nav_engineering_test",
        decision[0]["pm_gate_decision"],
        [],
        rolling_delta_return=float(rolling_metrics["delta_return_vs_baseline"]),
        rolling_delta_max_drawdown=float(rolling_metrics["delta_max_drawdown_vs_baseline"]),
        rolling_strategy_return=float(rolling_metrics["strategy_return"]),
        selected_event_count=int(event_summary[0]["rolling_selected_event_count"]),
    )
    _write_json(out / "v5e_full_intraday_nav_summary.json", summary)
    return summary


def _nav_variant(version_id: str, baseline: pd.DataFrame, events: pd.DataFrame, closes: dict[tuple[str, str], float]) -> dict[str, Any]:
    active_events = _event_records(events)
    daily_rows: list[dict[str, Any]] = []
    prev_nav = 1.0
    for _, row in baseline.iterrows():
        day = str(row["trade_date"])
        baseline_value = float(row["portfolio_value"])
        overlay_delta = 0.0
        active_count = 0
        for event in active_events:
            if day < event["execution_trade_date"] or (event["next_rebalance_date"] and day >= event["next_rebalance_date"]):
                continue
            close = closes.get((event["code"], day))
            if close is None:
                continue
            overlay_delta += event["sold_amount"] * (event["execution_price"] - close) - event["commission"]
            active_count += 1
        value = baseline_value + overlay_delta
        nav = value / INITIAL_CAPITAL
        daily_rows.append(
            {
                "trade_date": day,
                "version_id": version_id,
                "strategy_nav": nav,
                "strategy_return": nav / prev_nav - 1.0 if prev_nav else 0.0,
                "portfolio_value": value,
                "baseline_portfolio_value": baseline_value,
                "overlay_delta_value": overlay_delta,
                "active_overlay_event_count": active_count,
                "baseline_nav": float(row["strategy_nav"]),
                "rebalance": row.get("rebalance", 0),
            }
        )
        prev_nav = nav
    return {"version_id": version_id, "daily": daily_rows, "events": active_events}


def _event_records(events: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    if events.empty:
        return rows
    for _, row in events.iterrows():
        if not bool(row.get("triggered", False)):
            continue
        execution_price = float(row["execution_price"])
        sold_amount = float(row["amount"]) * float(row["sell_fraction"])
        exit_value = sold_amount * execution_price
        rows.append(
            {
                "model_id": str(row["model_id"]),
                "cycle_id": str(row["cycle_id"]),
                "code": str(row["code"]),
                "sleeve": str(row.get("sleeve", "")),
                "holding_start_date": str(row["holding_start_date"]),
                "next_rebalance_date": str(row["next_rebalance_date"]),
                "trigger_trade_date": str(row["trigger_trade_date"]),
                "execution_trade_date": str(row["execution_trade_date"]),
                "execution_price": execution_price,
                "sold_amount": sold_amount,
                "exit_value": exit_value,
                "commission": max(exit_value * COMMISSION_RATE, MIN_COMMISSION) if exit_value else 0.0,
                "future_information_used_for_trigger": False,
            }
        )
    return rows


def _metrics(version_id: str, daily_rows: list[dict[str, Any]]) -> dict[str, Any]:
    nav = [float(row["strategy_nav"]) for row in daily_rows]
    returns = [float(row["strategy_return"]) for row in daily_rows]
    final_return = nav[-1] - 1.0 if nav else 0.0
    max_dd = _max_drawdown(nav)
    vol = pd.Series(returns).std() * (252**0.5) if len(returns) > 1 else 0.0
    ann = (nav[-1] ** (252 / len(nav)) - 1.0) if nav and len(nav) else 0.0
    sharpe = ann / vol if vol else 0.0
    return {"version_id": version_id, "strategy_return": final_return, "annualized_return": ann, "max_drawdown": max_dd, "volatility": vol, "sharpe": sharpe}


def _comparison(row: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "delta_return_vs_baseline": row["strategy_return"] - baseline["strategy_return"],
        "delta_return_pct_points_vs_baseline": (row["strategy_return"] - baseline["strategy_return"]) * 100.0,
        "delta_max_drawdown_vs_baseline": row["max_drawdown"] - baseline["max_drawdown"],
        "delta_max_drawdown_pct_points_vs_baseline": (row["max_drawdown"] - baseline["max_drawdown"]) * 100.0,
        "delta_volatility_pct_points_vs_baseline": (row["volatility"] - baseline["volatility"]) * 100.0,
        "delta_sharpe_vs_baseline": row["sharpe"] - baseline["sharpe"],
        "accepted": False,
    }


def _selected_events(event_log: pd.DataFrame, rolling: pd.DataFrame) -> pd.DataFrame:
    selected = rolling.set_index("holding_start_date")["selected_model_id"].to_dict()
    df = event_log[event_log["triggered"].eq(True)].copy()
    return df[df.apply(lambda row: selected.get(str(row["holding_start_date"])) == str(row["model_id"]), axis=1)].copy()


def _best_static_model(root: Path) -> str:
    rows = pd.read_csv(root / RESEARCH_DIR / "v5e_full_intraday_model_comparison.csv")
    return str(rows.sort_values("incremental_value_vs_hold", ascending=False).iloc[0]["model_id"])


def _close_map(root: Path) -> dict[tuple[str, str], float]:
    result = {}
    for path in (root / PRICE_DIR).glob("*.csv"):
        df = pd.read_csv(path, dtype={"date": str, "code": str})
        for _, row in df.iterrows():
            result[(str(row["code"]), str(row["date"]))] = float(row["close"])
    return result


def _event_summary(selected: pd.DataFrame, best_static: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {
            "rolling_selected_event_count": int(len(selected)),
            "rolling_selected_exit_value": float(selected["exit_value"].sum()) if len(selected) else 0.0,
            "rolling_selected_models": ";".join(sorted(set(selected["model_id"].astype(str).tolist()))) if len(selected) else "",
            "best_static_event_count": int(len(best_static)),
            "best_static_exit_value": float(best_static["exit_value"].sum()) if len(best_static) else 0.0,
        }
    ]


def _previous_comparison(root: Path, comparison: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previous = json.loads((root / PREVIOUS_COMPARISON).read_text(encoding="utf-8"))
    rolling = next(row for row in comparison if row["version_id"] == "full_intraday_rolling_selected_prior4")
    static = next(row for row in comparison if row["version_id"].startswith("full_intraday_static_"))
    return [
        {
            "comparison_id": "previous_daily_open_profit_lock_200w",
            "delta_return_pct_points_vs_baseline": previous["daily_open_delta_return_pct_points_200w"],
            "delta_max_drawdown_pct_points_vs_baseline": previous["delta_max_drawdown_pct_points_200w"],
            "accepted": False,
        },
        {
            "comparison_id": "previous_vwap_adjusted_profit_lock_200w",
            "delta_return_pct_points_vs_baseline": previous["vwap_adjusted_delta_return_pct_points_200w"],
            "delta_max_drawdown_pct_points_vs_baseline": "",
            "accepted": False,
        },
        {
            "comparison_id": "full_intraday_static_nav_proxy",
            "model_id": static["version_id"],
            "delta_return_pct_points_vs_baseline": static["delta_return_pct_points_vs_baseline"],
            "delta_max_drawdown_pct_points_vs_baseline": static["delta_max_drawdown_pct_points_vs_baseline"],
            "accepted": False,
        },
        {
            "comparison_id": "full_intraday_rolling_nav_proxy",
            "model_id": rolling["version_id"],
            "delta_return_pct_points_vs_baseline": rolling["delta_return_pct_points_vs_baseline"],
            "delta_max_drawdown_pct_points_vs_baseline": rolling["delta_max_drawdown_pct_points_vs_baseline"],
            "accepted": False,
        },
    ]


def _pm_gate_decision(comparison: list[dict[str, Any]], previous: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rolling = next(row for row in comparison if row["version_id"] == "full_intraday_rolling_selected_prior4")
    if rolling["delta_return_vs_baseline"] > 0 and rolling["delta_max_drawdown_vs_baseline"] <= 0:
        decision = "promote_full_intraday_rolling_to_pm_quant_formal_review_not_accepted"
        next_gate = "v5e_full_intraday_pm_quant_formal_review"
    elif rolling["delta_return_vs_baseline"] > 0:
        decision = "remain_candidate_needs_drawdown_review"
        next_gate = "v5e_full_intraday_drawdown_review"
    else:
        decision = "downgrade_full_intraday_to_diagnostic"
        next_gate = "v5e_sleeve_cash_policy_quant_spec"
    return [
        {
            "pm_gate_decision": decision,
            "next_gate": next_gate,
            "rolling_delta_return_pct_points_vs_baseline": rolling["delta_return_pct_points_vs_baseline"],
            "rolling_delta_max_drawdown_pct_points_vs_baseline": rolling["delta_max_drawdown_pct_points_vs_baseline"],
            "accepted": False,
            "v57f_core_modified": False,
            "future_information_used": False,
            "reason": "Full intraday NAV proxy resets at regular V57f rebalance and uses rolling-selected rules from prior completed periods only.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_gate": "v5e_full_intraday_pm_quant_formal_review" if decision.startswith("promote") else "v5e_full_intraday_diagnostic_review",
            "task": "Formal PM/Quant review of rolling full intraday NAV candidate" if decision.startswith("promote") else "Diagnose full intraday NAV proxy limitations",
            "allowed": True,
        }
    ]


def _nonfatal_blockers(selected_events: pd.DataFrame) -> list[dict[str, Any]]:
    if selected_events.empty:
        return [{"blocker_id": "no_selected_events", "severity": "model", "status": "review_required"}]
    return [{"blocker_id": "none", "severity": "none", "status": "not_blocking"}]


def _max_drawdown(nav: list[float]) -> float:
    peak = nav[0] if nav else 1.0
    max_dd = 0.0
    for value in nav:
        peak = max(peak, value)
        if peak:
            max_dd = max(max_dd, 1.0 - value / peak)
    return max_dd


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    rolling_delta_return: float = 0.0,
    rolling_delta_max_drawdown: float = 0.0,
    rolling_strategy_return: float = 0.0,
    selected_event_count: int = 0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_full_intraday_nav_engineering_test",
        "status": status,
        "pm_gate_decision": decision,
        "rolling_strategy_return": rolling_strategy_return,
        "rolling_delta_return_pct_points_vs_baseline": rolling_delta_return * 100.0,
        "rolling_delta_max_drawdown_pct_points_vs_baseline": rolling_delta_max_drawdown * 100.0,
        "selected_event_count": selected_event_count,
        "accepted": False,
        "v57f_core_modified": False,
        "future_information_used": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(comparison: list[dict[str, Any]], previous: list[dict[str, Any]], decision: list[dict[str, Any]]) -> str:
    rolling = next(row for row in comparison if row["version_id"] == "full_intraday_rolling_selected_prior4")
    return "\n".join(
        [
            "# V5e Full Intraday NAV Engineering Test",
            "",
            f"- PM gate: `{decision[0]['pm_gate_decision']}`",
            f"- Rolling NAV delta return: {rolling['delta_return_pct_points_vs_baseline']:.4f} pct points",
            f"- Rolling max drawdown delta: {rolling['delta_max_drawdown_pct_points_vs_baseline']:.4f} pct points",
            "- Candidate is not accepted and not live approved.",
            "",
        ]
    )


def _next_prompt() -> str:
    return """工作目录：
D:\\hh\\codex\\v5

任务名称：
V5e full intraday PM/Quant formal review

任务目标：
复核 `v5e_full_intraday_nav_engineering_test/current/` 的 rolling full intraday NAV candidate。重点审查 rolling 选择是否 PIT、回撤改善是否稳定、是否只是事件级错配、是否允许进入 forward/paper tracking。不得 accepted，不得修改 V57f。
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Full Intraday NAV Engineering Rules",
            "",
            "- NAV proxy only; not accepted.",
            "- Rolling selection uses prior completed periods only.",
            "- No V57f modification.",
            "- No future information.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        REPAIRED_RUN / "daily_returns.csv",
        RESEARCH_DIR / "v5e_full_intraday_event_log.csv",
        RESEARCH_DIR / "v5e_full_intraday_rolling_model_selection.csv",
        RESEARCH_DIR / "v5e_full_intraday_model_comparison.csv",
        PREVIOUS_COMPARISON,
        PRICE_DIR,
    ]
    return [{"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)} for path in required if not (root / path).exists()]


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
    result = run_v5e_full_intraday_nav_engineering()
    print(json.dumps(result, ensure_ascii=False, indent=2))

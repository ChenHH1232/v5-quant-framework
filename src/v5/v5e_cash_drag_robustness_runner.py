from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5e_cash_drag_robustness_packet") / "current"
LOOP_DIR = Path("v5e_limited_engineering_loop") / "current"
PM_DIR = Path("v5e_pm_quant_formal_review") / "current"
SPEC_RULES = Path("v5e_quant_spec_single_name_exit") / "current" / "v5e_agent_execution_rules.md"
STARTUP_SUMMARY = Path("v5_startup_warmup_price_repair") / "current" / "v5_startup_warmup_price_repair_summary.json"
REPAIRED_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
PRICE_MANIFEST = Path("v5_startup_warmup_price_repair") / "current" / "v5_warmup_repaired_price_manifest.csv"

MAIN_CANDIDATE = "v5e_combined_main_profit_lock_plus_trailing"
SECONDARY_CANDIDATE = "v5e_profit_lock_main_20pct_sell50"
BASELINE = "v57f_repaired_baseline"
HORIZONS = [5, 10, 20, 60]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_cash_drag_robustness(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_blockers(root)
    if blockers:
        _write_csv(out / "v5e_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", blockers, "blocked_until_inputs_available")
        _write_json(out / "v5e_cash_drag_robustness_summary.json", summary)
        return summary

    data = _load_inputs(root)
    candidates = [MAIN_CANDIDATE, SECONDARY_CANDIDATE]
    cash_periods, cash_year, cash_rebalance = _cash_drag_tables(data, candidates)
    post_rows, until_rows, effectiveness_rows, top_events = _exit_post_return_tables(data, candidates)
    trig_year, trig_sleeve, trig_stock = _trigger_concentration_tables(data, candidates)
    drawdown_rows = _drawdown_window_contribution(data, candidates)
    stability_rows = _candidate_stability(data, candidates, effectiveness_rows, drawdown_rows)
    gate_rows = _pm_gate_decision(stability_rows)
    next_queue = _next_queue(gate_rows[0]["pm_gate_decision"])
    blockers = _nonfatal_blockers()

    _write_csv(out / "v5e_cash_periods.csv", cash_periods)
    _write_csv(out / "v5e_cash_drag_by_year.csv", cash_year)
    _write_csv(out / "v5e_cash_drag_by_rebalance_period.csv", cash_rebalance)
    _write_csv(out / "v5e_exit_post_return_5d_10d_20d_60d.csv", post_rows)
    _write_csv(out / "v5e_exit_until_next_rebalance_return.csv", until_rows)
    _write_csv(out / "v5e_exit_effectiveness_summary.csv", effectiveness_rows)
    _write_csv(out / "v5e_trigger_concentration_by_year.csv", trig_year)
    _write_csv(out / "v5e_trigger_concentration_by_sleeve.csv", trig_sleeve)
    _write_csv(out / "v5e_trigger_concentration_by_stock.csv", trig_stock)
    _write_csv(out / "v5e_top_exit_impact_events.csv", top_events)
    _write_csv(out / "v5e_drawdown_window_contribution.csv", drawdown_rows)
    _write_csv(out / "v5e_candidate_stability_review.csv", stability_rows)
    _write_csv(out / "v5e_pm_gate_decision.csv", gate_rows)
    _write_csv(out / "v5e_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5e_blockers.csv", blockers)
    (out / "v5e_next_prompt.md").write_text(_next_prompt(gate_rows[0]["pm_gate_decision"]), encoding="utf-8")
    (out / "v5e_clean_pm_quant_review_report.md").write_text(_clean_pm_report(data, gate_rows), encoding="utf-8")
    (out / "v5e_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")

    summary = _summary(
        "completed_cash_drag_robustness_packet",
        [],
        gate_rows[0]["pm_gate_decision"],
        data=data,
        output_count=20,
        stability_rows=stability_rows,
    )
    _write_json(out / "v5e_cash_drag_robustness_summary.json", summary)
    (out / "v5e_cash_drag_robustness_report.md").write_text(
        _report(summary, gate_rows, stability_rows, effectiveness_rows, drawdown_rows),
        encoding="utf-8",
    )
    return summary


def _missing_blockers(root: Path) -> list[dict[str, Any]]:
    required = [
        LOOP_DIR / "v5e_loop_summary.json",
        LOOP_DIR / "v5e_engineering_comparison.csv",
        LOOP_DIR / "v5e_variant_metrics.csv",
        LOOP_DIR / "v5e_trigger_log.csv",
        LOOP_DIR / "v5e_exit_action_log.csv",
        LOOP_DIR / "v5e_cash_drag_log.csv",
        LOOP_DIR / "v5e_failure_attribution.csv",
        LOOP_DIR / "v5e_rule_suitability_review.csv",
        LOOP_DIR / "v5e_quant_validation_review.csv",
        PM_DIR / "v5e_pm_quant_review_summary.json",
        PM_DIR / "v5e_pm_quant_variant_review.csv",
        PM_DIR / "v5e_pm_quant_candidate_checks.csv",
        PM_DIR / "v5e_pm_quant_risk_benefit_matrix.csv",
        PM_DIR / "v5e_pm_quant_next_queue.csv",
        PM_DIR / "v5e_pm_quant_blockers.csv",
        SPEC_RULES,
        STARTUP_SUMMARY,
        REPAIRED_RUN / "rebalance_signals.csv",
        PRICE_MANIFEST,
    ]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "status": "blocking",
            "path": str(path),
            "description": "Required V5e loop/formal-review/repaired data file is missing.",
        }
        for path in required
        if not (root / path).exists()
    ]


def _load_inputs(root: Path) -> dict[str, Any]:
    comparison = _read_df(root / LOOP_DIR / "v5e_engineering_comparison.csv")
    triggers = _read_df(root / LOOP_DIR / "v5e_trigger_log.csv")
    exits = _read_df(root / LOOP_DIR / "v5e_exit_action_log.csv")
    cash = _read_df(root / LOOP_DIR / "v5e_cash_drag_log.csv")
    failure = _read_df(root / LOOP_DIR / "v5e_failure_attribution.csv")
    pm_summary = _read_json(root / PM_DIR / "v5e_pm_quant_review_summary.json")
    signals = _read_df(root / REPAIRED_RUN / "rebalance_signals.csv")
    price = _load_price_frame(root)
    daily_by_version = {
        version: _read_df(root / LOOP_DIR / "runs" / version / "daily_returns.csv")
        for version in [BASELINE, MAIN_CANDIDATE, SECONDARY_CANDIDATE]
    }
    code_sleeve = _code_sleeve_map(signals)
    trading_days = list(daily_by_version[BASELINE]["trade_date"].astype(str))
    rebalance_dates = sorted(signals["trade_date"].astype(str).unique())
    return {
        "comparison": comparison,
        "triggers": triggers,
        "exits": exits,
        "cash": cash,
        "failure": failure,
        "pm_summary": pm_summary,
        "signals": signals,
        "price": price,
        "daily_by_version": daily_by_version,
        "code_sleeve": code_sleeve,
        "trading_days": trading_days,
        "rebalance_dates": rebalance_dates,
    }


def _cash_drag_tables(data: dict[str, Any], candidates: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    cash = data["cash"].copy()
    cash["trade_date"] = cash["trade_date"].astype(str)
    for col in ["cash_weight", "baseline_cash_weight", "cash_weight_delta_vs_baseline"]:
        cash[col] = pd.to_numeric(cash[col], errors="coerce").fillna(0.0)
    rows: list[dict[str, Any]] = []
    yearly: list[dict[str, Any]] = []
    period_rows: list[dict[str, Any]] = []
    for version in candidates:
        df = cash[cash["version_id"] == version].copy().reset_index(drop=True)
        df["year"] = df["trade_date"].str[:4]
        for year, g in df.groupby("year"):
            yearly.append(
                {
                    "version_id": version,
                    "year": year,
                    "avg_cash_weight": g["cash_weight"].mean(),
                    "max_cash_weight": g["cash_weight"].max(),
                    "avg_cash_drag_delta": g["cash_weight_delta_vs_baseline"].mean(),
                    "days_cash_gt_5pct": int((g["cash_weight"] > 0.05).sum()),
                    "days_cash_gt_10pct": int((g["cash_weight"] > 0.10).sum()),
                    "days_cash_gt_15pct": int((g["cash_weight"] > 0.15).sum()),
                }
            )
        active = df["cash_weight_delta_vs_baseline"] > 0.005
        start_idx = None
        for idx, is_active in enumerate(active.tolist() + [False]):
            if is_active and start_idx is None:
                start_idx = idx
            if not is_active and start_idx is not None:
                g = df.iloc[start_idx:idx]
                start, end = str(g.iloc[0]["trade_date"]), str(g.iloc[-1]["trade_date"])
                rows.append(
                    {
                        "version_id": version,
                        "period_start": start,
                        "period_end": end,
                        "trading_days": len(g),
                        "avg_cash_weight": g["cash_weight"].mean(),
                        "max_cash_weight": g["cash_weight"].max(),
                        "avg_cash_drag_delta": g["cash_weight_delta_vs_baseline"].mean(),
                        "start_year": start[:4],
                        "rebalance_period": _period_label(start, data["rebalance_dates"]),
                    }
                )
                start_idx = None
        for label, g in df.groupby(df["trade_date"].map(lambda x: _period_label(x, data["rebalance_dates"]))):
            period_rows.append(
                {
                    "version_id": version,
                    "rebalance_period": label,
                    "start_date": g["trade_date"].min(),
                    "end_date": g["trade_date"].max(),
                    "avg_cash_weight": g["cash_weight"].mean(),
                    "max_cash_weight": g["cash_weight"].max(),
                    "avg_cash_drag_delta": g["cash_weight_delta_vs_baseline"].mean(),
                    "days_cash_gt_10pct": int((g["cash_weight"] > 0.10).sum()),
                }
            )
    return rows, yearly, period_rows


def _exit_post_return_tables(data: dict[str, Any], candidates: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    exits = data["exits"][data["exits"]["version_id"].isin(candidates)].copy()
    price = data["price"]
    price_idx = {(str(r.trade_date), str(r.code)): r for r in price.itertuples(index=False)}
    day_index = {day: i for i, day in enumerate(data["trading_days"])}
    rows: list[dict[str, Any]] = []
    until_rows: list[dict[str, Any]] = []
    top_events: list[dict[str, Any]] = []
    for r in exits.itertuples(index=False):
        version, day, code = str(r.version_id), str(r.execution_date), str(r.code)
        base = price_idx.get((day, code))
        if base is None:
            continue
        exit_price = _float(getattr(r, "price", 0.0)) or _float(getattr(base, "open", 0.0))
        event: dict[str, Any] = {
            "version_id": version,
            "execution_date": day,
            "trigger_date": str(r.trigger_date),
            "code": code,
            "sleeve": data["code_sleeve"].get(code, "unknown"),
            "trigger_reason": str(r.trigger_reason),
            "exit_value": _float(r.value),
            "exit_price": exit_price,
        }
        for h in HORIZONS:
            future_day = _future_day(day, h, data["trading_days"])
            future_close = _close_on(price_idx, future_day, code)
            stock_return = future_close / exit_price - 1.0 if future_day and exit_price > 0 and future_close > 0 else None
            event[f"stock_return_{h}d"] = stock_return
            event[f"cash_return_{h}d"] = 0.0
            event[f"avoided_loss_{h}d"] = bool(stock_return is not None and stock_return < 0)
            event[f"missed_upside_{h}d"] = bool(stock_return is not None and stock_return > 0)
        rows.append(event)
        next_reb = _next_rebalance(day, data["rebalance_dates"])
        until_close = _close_on(price_idx, next_reb, code)
        until_ret = until_close / exit_price - 1.0 if next_reb and exit_price > 0 and until_close > 0 else None
        until_rows.append(
            {
                "version_id": version,
                "execution_date": day,
                "next_rebalance_date": next_reb,
                "code": code,
                "sleeve": event["sleeve"],
                "trigger_reason": event["trigger_reason"],
                "idle_trading_days_until_next_rebalance": max((_day_pos(next_reb, day_index) - _day_pos(day, day_index)), 0) if next_reb else "",
                "stock_return_until_next_rebalance": until_ret,
                "cash_return_until_next_rebalance": 0.0,
                "avoided_loss_until_next_rebalance": bool(until_ret is not None and until_ret < 0),
                "missed_upside_until_next_rebalance": bool(until_ret is not None and until_ret > 0),
                "exit_value": event["exit_value"],
            }
        )
        top_events.append(
            {
                "version_id": version,
                "execution_date": day,
                "code": code,
                "sleeve": event["sleeve"],
                "trigger_reason": event["trigger_reason"],
                "exit_value": event["exit_value"],
                "stock_return_20d": event.get("stock_return_20d"),
                "estimated_20d_opportunity_or_avoided_loss": -(_float(event["exit_value"]) or 0.0) * (_float(event.get("stock_return_20d")) or 0.0),
            }
        )
    effectiveness = _effectiveness_summary(rows, until_rows)
    top_events = sorted(top_events, key=lambda x: abs(_float(x["estimated_20d_opportunity_or_avoided_loss"]) or 0.0), reverse=True)[:50]
    return rows, until_rows, effectiveness, top_events


def _effectiveness_summary(post_rows: list[dict[str, Any]], until_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for version in sorted({r["version_id"] for r in post_rows}):
        rows = [r for r in post_rows if r["version_id"] == version]
        until = [r for r in until_rows if r["version_id"] == version]
        for reason in sorted({r["trigger_reason"] for r in rows}):
            group = [r for r in rows if r["trigger_reason"] == reason]
            until_group = [r for r in until if r["trigger_reason"] == reason]
            result.append(
                {
                    "version_id": version,
                    "trigger_reason": reason,
                    "exit_count": len(group),
                    "avoided_loss_20d_count": sum(1 for r in group if r.get("avoided_loss_20d")),
                    "missed_upside_20d_count": sum(1 for r in group if r.get("missed_upside_20d")),
                    "avg_stock_return_5d": _avg(r.get("stock_return_5d") for r in group),
                    "avg_stock_return_10d": _avg(r.get("stock_return_10d") for r in group),
                    "avg_stock_return_20d": _avg(r.get("stock_return_20d") for r in group),
                    "avg_stock_return_60d": _avg(r.get("stock_return_60d") for r in group),
                    "avg_until_next_rebalance_return": _avg(r.get("stock_return_until_next_rebalance") for r in until_group),
                    "effectiveness_read": _effectiveness_read(group),
                }
            )
    return result


def _trigger_concentration_tables(data: dict[str, Any], candidates: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    trig = data["triggers"][data["triggers"]["version_id"].isin(candidates)].copy()
    trig["year"] = trig["trigger_date"].astype(str).str[:4]
    trig["sleeve"] = trig["code"].map(lambda c: data["code_sleeve"].get(str(c), "unknown"))
    year_rows = _count_table(trig, ["version_id", "year"], "trigger_count")
    sleeve_rows = _count_table(trig, ["version_id", "sleeve"], "trigger_count")
    stock_rows = _count_table(trig, ["version_id", "code", "sleeve"], "trigger_count")
    for rows in [year_rows, sleeve_rows, stock_rows]:
        totals = defaultdict(int)
        for r in rows:
            totals[r["version_id"]] += int(r["trigger_count"])
        for r in rows:
            r["share_of_version_triggers"] = int(r["trigger_count"]) / totals[r["version_id"]] if totals[r["version_id"]] else 0
    return year_rows, sleeve_rows, sorted(stock_rows, key=lambda r: (r["version_id"], -int(r["trigger_count"])))


def _drawdown_window_contribution(data: dict[str, Any], candidates: list[str]) -> list[dict[str, Any]]:
    baseline = data["daily_by_version"][BASELINE]
    base_window = _max_drawdown_window(baseline)
    rows: list[dict[str, Any]] = []
    for version in [BASELINE] + candidates:
        daily = data["daily_by_version"][version]
        same_ret = _window_return(daily, base_window["start"], base_window["end"])
        own_window = _max_drawdown_window(daily)
        exits = data["exits"][(data["exits"]["version_id"] == version) & (data["exits"]["execution_date"].astype(str) >= base_window["start"]) & (data["exits"]["execution_date"].astype(str) <= base_window["end"])] if version != BASELINE else pd.DataFrame()
        rows.append(
            {
                "version_id": version,
                "baseline_drawdown_start": base_window["start"],
                "baseline_drawdown_end": base_window["end"],
                "return_during_baseline_dd_window": same_ret,
                "own_max_drawdown": own_window["max_drawdown"],
                "own_max_drawdown_start": own_window["start"],
                "own_max_drawdown_end": own_window["end"],
                "exit_count_in_baseline_dd_window": int(len(exits)),
                "exit_value_in_baseline_dd_window": float(pd.to_numeric(exits.get("value", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not exits.empty else 0.0,
            }
        )
    return rows


def _candidate_stability(data: dict[str, Any], candidates: list[str], effectiveness_rows: list[dict[str, Any]], drawdown_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    comp = data["comparison"].set_index("version_id")
    result: list[dict[str, Any]] = []
    for version in candidates:
        row = comp.loc[version]
        eff = [r for r in effectiveness_rows if r["version_id"] == version]
        missed = sum(int(r["missed_upside_20d_count"]) for r in eff)
        avoided = sum(int(r["avoided_loss_20d_count"]) for r in eff)
        if version == MAIN_CANDIDATE:
            decision = "retain_review_candidate_with_cash_drag_note"
            rationale = "Largest drawdown improvement and clean governance, but cash drag and return cost block acceptance."
        elif version == SECONDARY_CANDIDATE:
            decision = "secondary_candidate_not_primary_yet"
            rationale = "Return is better, but PM cannot switch primary by return alone; risk improvement is smaller and cash drag remains high."
        else:
            decision = "diagnostic"
            rationale = ""
        result.append(
            {
                "version_id": version,
                "strategy_return": row["strategy_return"],
                "delta_return_vs_baseline": row["delta_return_vs_baseline"],
                "max_drawdown": row["max_drawdown"],
                "delta_max_drawdown_vs_baseline": row["delta_max_drawdown_vs_baseline"],
                "cash_drag_delta_vs_baseline": row["cash_drag_delta_vs_baseline"],
                "avoided_loss_20d_count": avoided,
                "missed_upside_20d_count": missed,
                "stability_decision": decision,
                "rationale": rationale,
            }
        )
    return result


def _pm_gate_decision(stability_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    main = next(r for r in stability_rows if r["version_id"] == MAIN_CANDIDATE)
    secondary = next(r for r in stability_rows if r["version_id"] == SECONDARY_CANDIDATE)
    if _float(main["delta_max_drawdown_vs_baseline"]) < -0.005:
        decision = "retain_v5e_combined_main_candidate_needs_forward_or_paper"
        reason = "Combined main remains primary because it has the clearest drawdown improvement with clean governance; cash drag blocks acceptance and requires forward/paper evidence."
    elif _float(secondary["delta_max_drawdown_vs_baseline"]) < -0.003 and _float(secondary["delta_return_vs_baseline"]) > 0:
        decision = "switch_primary_to_profit_lock_main_candidate"
        reason = "Secondary profit-lock main has better risk-return balance, but switch requires candidate review and is not based on return alone."
    else:
        decision = "downgrade_to_diagnostic_only"
        reason = "Cash drag or weak drawdown stability prevents candidate retention."
    return [{"pm_gate_decision": decision, "reason": reason, "accepted": "no", "v57f_replacement": "no", "next_prompt": _prompt_name(decision)}]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    if decision == "retain_v5e_combined_main_candidate_needs_forward_or_paper":
        return [
            {"priority": 1, "next_action": "V5e formal validation / forward evidence packet", "scope": "Validate combined_main as review candidate; monitor cash drag and post-exit outcomes; no accepted marking.", "blocked_actions": "threshold_scan; V57f_modification; cash_reallocation"},
            {"priority": 2, "next_action": "V5e paper tracking template", "scope": "Record future triggers, exits, cash idle days and missed/avoided returns.", "blocked_actions": "live_trading_approval"},
        ]
    if decision == "switch_primary_to_profit_lock_main_candidate":
        return [{"priority": 1, "next_action": "PM/Quant candidate switch review", "scope": "Review whether profit_lock_main should become primary based on risk governance, not return alone.", "blocked_actions": "accepted_marking"}]
    if decision == "open_sleeve_level_profit_lock_pm_spec":
        return [{"priority": 1, "next_action": "V5e sleeve-level profit lock PM spec", "scope": "Spec boundary only; no engineering.", "blocked_actions": "direct_backtest"}]
    return [{"priority": 1, "next_action": "V5e failure attribution closeout", "scope": "Close or downgrade single-name exit line.", "blocked_actions": "new_thresholds"}]


def _summary(status: str, blockers: list[dict[str, Any]], gate: str, data: dict[str, Any] | None = None, output_count: int = 0, stability_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    summary = {
        "schema_version": 1,
        "project": "v5e_cash_drag_robustness_packet",
        "status": status,
        "created_at_utc": now_utc(),
        "main_candidate": MAIN_CANDIDATE,
        "secondary_candidate": SECONDARY_CANDIDATE,
        "pm_gate_decision": gate,
        "accepted": False,
        "v57f_replacement": False,
        "v57f_core_modified": False,
        "parameter_scan_used": False,
        "joinquant_started": False,
        "network_fetch_started": False,
        "fatal_blocker_count": len([b for b in blockers if b.get("severity") == "fatal"]),
        "output_count": output_count,
    }
    if stability_rows:
        summary["candidate_stability"] = stability_rows
    return summary


def _report(summary: dict[str, Any], gate: list[dict[str, Any]], stability: list[dict[str, Any]], effectiveness: list[dict[str, Any]], drawdown: list[dict[str, Any]]) -> str:
    lines = [
        "# V5e Cash Drag Robustness Packet",
        "",
        "## 结论",
        "",
        f"PM gate decision: `{gate[0]['pm_gate_decision']}`.",
        "",
        "本任务只复核现有主候选和次级候选，没有新增阈值、没有参数扫描、没有修改 V57f/ERC/V5d、没有启动 JoinQuant，也没有标记 accepted。",
        "",
        "## 候选稳定性",
        "",
        "| version | delta return | delta max DD | cash drag | missed 20d | avoided 20d | decision |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in stability:
        lines.append(
            f"| `{row['version_id']}` | {_pct(row['delta_return_vs_baseline'])} | {_pct(row['delta_max_drawdown_vs_baseline'])} | {_pct(row['cash_drag_delta_vs_baseline'])} | {row['missed_upside_20d_count']} | {row['avoided_loss_20d_count']} | `{row['stability_decision']}` |"
        )
    lines.extend(
        [
            "",
            "## PM Read",
            "",
            gate[0]["reason"],
            "",
            "现金拖累是主风险：combined_main 的回撤改善更强，但平均现金暴露上升明显，不能 accepted。profit_lock_main 收益更好，但不能只因收益切换 primary。",
        ]
    )
    return "\n".join(lines) + "\n"


def _clean_pm_report(data: dict[str, Any], gate: list[dict[str, Any]]) -> str:
    pm = data["pm_summary"]
    metrics = pm.get("candidate_key_metrics", {})
    return f"""# V5e PM/Quant Review Clean Report

## 状态

主候选：`{pm.get('candidate', MAIN_CANDIDATE)}`

PM gate：`{pm.get('pm_gate_decision')}`

不是 accepted，不是 V57f replacement，不是 live trading approved。

## 关键指标

- 收益：{metrics.get('strategy_return')}
- 相对 baseline 收益：{metrics.get('delta_return_vs_baseline')}
- 最大回撤：{metrics.get('max_drawdown')}
- 相对 baseline 最大回撤：{metrics.get('delta_max_drawdown_vs_baseline')}
- cash drag delta：{metrics.get('cash_drag_delta_vs_baseline')}
- trigger / exit：{metrics.get('trigger_count')} / {metrics.get('exit_action_count')}

## 下一门

`{gate[0]['pm_gate_decision']}`
"""


def _read_df(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_price_frame(root: Path) -> pd.DataFrame:
    frames = []
    manifest = _read_df(root / PRICE_MANIFEST)
    for row in manifest.itertuples(index=False):
        path = root / Path(str(getattr(row, "repaired_price_csv")))
        df = pd.read_csv(path, encoding="utf-8-sig")
        df["trade_date"] = df["date"].astype(str)
        frames.append(df[["trade_date", "code", "open", "close", "high", "low"]])
    price = pd.concat(frames, ignore_index=True).drop_duplicates(["trade_date", "code"], keep="last")
    for col in ["open", "close", "high", "low"]:
        price[col] = pd.to_numeric(price[col], errors="coerce")
    return price


def _code_sleeve_map(signals: pd.DataFrame) -> dict[str, str]:
    mapping = {}
    for row in signals.itertuples(index=False):
        mapping[str(row.code)] = str(row.sector_id)
    return mapping


def _period_label(day: str, rebalance_dates: list[str]) -> str:
    starts = [d for d in rebalance_dates if d <= day]
    start = starts[-1] if starts else "pre_start"
    end = _next_rebalance(day, rebalance_dates) or "end"
    return f"{start}_to_{end}"


def _next_rebalance(day: str, rebalance_dates: list[str]) -> str:
    for reb in rebalance_dates:
        if reb > day:
            return reb
    return ""


def _future_day(day: str, horizon: int, trading_days: list[str]) -> str:
    if day not in trading_days:
        return ""
    idx = trading_days.index(day) + horizon
    return trading_days[idx] if idx < len(trading_days) else ""


def _day_pos(day: str, day_index: dict[str, int]) -> int:
    return day_index.get(day, 0)


def _close_on(price_idx: dict[tuple[str, str], Any], day: str, code: str) -> float:
    if not day:
        return 0.0
    row = price_idx.get((day, code))
    return _float(getattr(row, "close", 0.0)) if row is not None else 0.0


def _count_table(df: pd.DataFrame, cols: list[str], count_name: str) -> list[dict[str, Any]]:
    if df.empty:
        return []
    out = df.groupby(cols).size().reset_index(name=count_name)
    return out.to_dict("records")


def _max_drawdown_window(daily: pd.DataFrame) -> dict[str, Any]:
    nav = pd.to_numeric(daily["strategy_nav"], errors="coerce").fillna(1.0).tolist()
    dates = daily["trade_date"].astype(str).tolist()
    peak = nav[0]
    peak_date = dates[0]
    max_dd = 0.0
    start = dates[0]
    end = dates[0]
    for value, day in zip(nav, dates):
        if value > peak:
            peak = value
            peak_date = day
        dd = value / peak - 1.0 if peak else 0.0
        if dd < max_dd:
            max_dd = dd
            start = peak_date
            end = day
    return {"max_drawdown": abs(max_dd), "start": start, "end": end}


def _window_return(daily: pd.DataFrame, start: str, end: str) -> float:
    d = daily.set_index("trade_date")
    if start not in d.index or end not in d.index:
        return 0.0
    return float(d.loc[end, "strategy_nav"]) / float(d.loc[start, "strategy_nav"]) - 1.0


def _effectiveness_read(rows: list[dict[str, Any]]) -> str:
    missed = sum(1 for r in rows if r.get("missed_upside_20d"))
    avoided = sum(1 for r in rows if r.get("avoided_loss_20d"))
    if avoided > missed:
        return "more_effective_profit_lock_than_missed_winner"
    if missed > avoided:
        return "more_early_winner_sales_than_loss_avoidance"
    return "mixed_or_balanced"


def _avg(values: Any) -> float:
    nums = [_float(v) for v in values]
    nums = [v for v in nums if v is not None]
    return sum(nums) / len(nums) if nums else 0.0


def _float(value: Any) -> float | None:
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _pct(value: Any) -> str:
    v = _float(value)
    return "" if v is None else f"{v:.2%}"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = _fields(rows)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _fields(rows: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    return fields


def _nonfatal_blockers() -> list[dict[str, Any]]:
    return [
        {"blocker_id": "none_fatal", "severity": "none", "status": "not_blocking", "description": "Cash drag robustness packet completed."},
        {"blocker_id": "cash_drag_high", "severity": "review_note", "status": "blocks_acceptance_not_review", "description": "High idle cash remains the central V5e candidate risk."},
    ]


def _prompt_name(decision: str) -> str:
    if decision == "retain_v5e_combined_main_candidate_needs_forward_or_paper":
        return "V5e formal validation / forward evidence packet"
    if decision == "switch_primary_to_profit_lock_main_candidate":
        return "PM/Quant candidate switch review"
    if decision == "open_sleeve_level_profit_lock_pm_spec":
        return "V5e sleeve-level profit lock PM spec"
    if decision == "open_cash_policy_review":
        return "cash policy review prompt"
    return "V5e archive or diagnostic closeout packet"


def _next_prompt(decision: str) -> str:
    return f"""# {_prompt_name(decision)}

工作目录：D:\\hh\\codex\\v5

输入：`v5e_cash_drag_robustness_packet/current/`

边界：不得新增阈值，不得参数扫描，不得修改 V57f/ERC/V5d，不得标记 accepted。

任务：根据 PM gate decision `{decision}` 继续下一门。
"""


def _agent_rules() -> str:
    return """# V5e Cash Drag Robustness Agent Rules

- Analyze only existing V5e candidates.
- Do not add thresholds or scan parameters.
- Do not modify V57f, ERC, or V5d.
- Do not start JoinQuant or fetch network data.
- Do not use 5min走势 as exit trigger.
- Do not automatically reallocate cash.
- Do not mark accepted or V57f replacement.
"""


if __name__ == "__main__":
    print(json.dumps(run_v5e_cash_drag_robustness(Path(".")), ensure_ascii=False, indent=2))

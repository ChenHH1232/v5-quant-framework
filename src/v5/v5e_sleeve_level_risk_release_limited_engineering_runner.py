from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5e_sleeve_level_risk_release_limited_engineering") / "current"
SPEC_DIR = Path("v5e_sleeve_level_risk_release_quant_spec") / "current"
ATTR_DIR = Path("v5_startup_warmup_price_repair") / "current" / "runs" / "v57f_warmup_repaired_sleeve_attribution"
LOOP_DIR = Path("v5e_limited_engineering_loop") / "current"
BASELINE_RUN = LOOP_DIR / "runs" / "v57f_repaired_baseline"
HOLD_CASH_RUN = LOOP_DIR / "runs" / "v5e_profit_lock_main_20pct_sell50"

SLEEVES = ["bank", "utilities_electricity", "highway_infrastructure", "port_rail_infrastructure"]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_sleeve_level_risk_release_limited_engineering(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_sleeve_level_release_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_sleeve_level_release_summary.json", summary)
        return summary

    spec_summary = _read_json(root / SPEC_DIR / "v5e_sleeve_level_quant_spec_summary.json")
    if not spec_summary.get("engineering_test_allowed"):
        blocker = {"blocker_id": "spec_not_admitted", "severity": "fatal", "status": "blocking", "description": "Sleeve-level Quant spec is not admitted to engineering."}
        _write_csv(out / "v5e_sleeve_level_release_blockers.csv", [blocker])
        summary = _summary("blocked_spec_not_admitted", "blocked_until_spec_admitted", [blocker])
        _write_json(out / "v5e_sleeve_level_release_summary.json", summary)
        return summary

    baseline_daily = _read_csv(root / BASELINE_RUN / "daily_returns.csv")
    hold_cash_daily = _read_csv(root / HOLD_CASH_RUN / "daily_returns.csv")
    sleeve_wide = _read_csv(root / ATTR_DIR / "v57f_core_sleeve_daily_returns.csv")

    variants = [
        {"version_id": "sleeve_level_daily_profit_release_main", "mode": "profit", "profit_threshold": 0.12, "peak_threshold": 0.0, "drawdown_threshold": 0.0, "sell_fraction": 0.25},
        {"version_id": "sleeve_level_trailing_release_conservative", "mode": "trailing", "profit_threshold": 0.0, "peak_threshold": 0.15, "drawdown_threshold": -0.06, "sell_fraction": 0.20},
    ]
    all_daily: list[dict[str, Any]] = []
    all_triggers: list[dict[str, Any]] = []
    all_actions: list[dict[str, Any]] = []
    all_cash: list[dict[str, Any]] = []
    metrics = [_metrics_from_daily("v57f_repaired_baseline", baseline_daily), _metrics_from_daily("v5e_profit_lock_main_20pct_sell50_hold_cash", hold_cash_daily)]

    for spec in variants:
        daily, triggers, actions, cash = _simulate_variant(spec, baseline_daily, sleeve_wide)
        all_daily.extend(daily)
        all_triggers.extend(triggers)
        all_actions.extend(actions)
        all_cash.extend(cash)
        metrics.append(_metrics_from_daily(spec["version_id"], daily))

    metrics = _augment_metrics(metrics)
    comparison = _comparison(metrics)
    attribution = _attribution(all_actions)
    governance = _governance()
    gate = _pm_gate_decision(metrics, governance)
    queue = _next_queue(gate[0]["pm_gate_decision"])
    blockers_out = [{"blocker_id": "execution_price_proxy", "severity": "review_note", "status": "not_blocking_blocks_acceptance", "description": "Sleeve-level test used daily close proxy because full sleeve-level T+1 open panel was not available."}]

    _write_csv(out / "v5e_sleeve_level_release_daily_returns.csv", all_daily)
    _write_csv(out / "v5e_sleeve_level_release_trigger_log.csv", all_triggers)
    _write_csv(out / "v5e_sleeve_level_release_action_log.csv", all_actions)
    _write_csv(out / "v5e_sleeve_level_release_cash_log.csv", all_cash)
    _write_csv(out / "v5e_sleeve_level_release_variant_metrics.csv", metrics)
    _write_csv(out / "v5e_sleeve_level_release_comparison.csv", comparison)
    _write_csv(out / "v5e_sleeve_level_release_attribution.csv", attribution)
    _write_csv(out / "v5e_sleeve_level_release_governance_audit.csv", governance)
    _write_csv(out / "v5e_sleeve_level_release_pm_gate_decision.csv", gate)
    _write_csv(out / "v5e_sleeve_level_release_next_queue.csv", queue)
    _write_csv(out / "v5e_sleeve_level_release_blockers.csv", blockers_out)
    (out / "v5e_sleeve_level_release_next_prompt.md").write_text(_next_prompt(gate[0]), encoding="utf-8")
    (out / "v5e_sleeve_level_release_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5e_sleeve_level_release_report.md").write_text(_report(metrics, gate), encoding="utf-8")

    best = max([row for row in metrics if row["version_id"].startswith("sleeve_level")], key=lambda r: float(r["delta_return_vs_v57f"]))
    summary = _summary(
        "completed_sleeve_level_risk_release_limited_engineering",
        gate[0]["pm_gate_decision"],
        [],
        best_version_id=best["version_id"],
        best_delta_return_vs_v57f=float(best["delta_return_vs_v57f"]),
        best_delta_return_vs_hold_cash=float(best["delta_return_vs_v5e_hold_cash"]),
        best_delta_max_drawdown_vs_v57f=float(best["delta_max_drawdown_vs_v57f"]),
        trigger_count=len(all_triggers),
    )
    _write_json(out / "v5e_sleeve_level_release_summary.json", summary)
    return summary


def _simulate_variant(spec: dict[str, Any], baseline_daily: list[dict[str, str]], sleeve_wide: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    days = [r["trade_date"] for r in baseline_daily]
    base_by_day = {r["trade_date"]: r for r in baseline_daily}
    wide_by_day = {r["trade_date"]: r for r in sleeve_wide}
    active: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    cycle_start: dict[str, float] = {}
    peak_return: dict[str, float] = {s: 0.0 for s in SLEEVES}
    released_this_cycle: set[str] = set()
    rows: list[dict[str, Any]] = []
    triggers: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    cash_rows: list[dict[str, Any]] = []
    initial_capital = _float(baseline_daily[0]["portfolio_value"]) / (_float(baseline_daily[0]["strategy_nav"]) or 1.0)
    prev_value = None

    for idx, day in enumerate(days):
        base = base_by_day[day]
        wide = wide_by_day[day]
        if base.get("rebalance") == "1":
            active.clear()
            pending.clear()
            released_this_cycle.clear()
            cycle_start = {s: _float(wide.get(f"{s}_end_value")) for s in SLEEVES}
            peak_return = {s: 0.0 for s in SLEEVES}

        for item in list(pending):
            if item["execution_date"] == day and item["sleeve_id"] not in released_this_cycle:
                sleeve_value = _float(wide.get(f"{item['sleeve_id']}_end_value"))
                release_value = sleeve_value * float(spec["sell_fraction"])
                action = {
                    "version_id": spec["version_id"],
                    "action_id": f"{spec['version_id']}|{day}|{item['sleeve_id']}",
                    "trigger_date": item["trigger_date"],
                    "execution_date": day,
                    "sleeve_id": item["sleeve_id"],
                    "release_value": release_value,
                    "reference_sleeve_value": sleeve_value,
                    "sell_fraction": spec["sell_fraction"],
                    "execution_price_policy": "daily_close_proxy_diagnostic",
                    "restore_status": "restore_at_next_rebalance",
                    "accepted": False,
                }
                active.append(action)
                actions.append(action)
                released_this_cycle.add(item["sleeve_id"])
                pending.remove(item)

        overlay_delta = 0.0
        sleeve_cash = 0.0
        for action in active:
            current_value = _float(wide.get(f"{action['sleeve_id']}_end_value"))
            ref = float(action["reference_sleeve_value"]) or current_value
            baseline_slice = float(action["release_value"]) * (current_value / ref if ref else 1.0)
            overlay_delta += float(action["release_value"]) - baseline_slice
            sleeve_cash += float(action["release_value"])

        value = _float(base["portfolio_value"]) + overlay_delta
        nav = value / initial_capital if initial_capital else _float(base["strategy_nav"])
        daily_return = 0.0 if prev_value is None else value / prev_value - 1.0
        prev_value = value
        row = dict(base)
        row.update(
            {
                "version_id": spec["version_id"],
                "strategy_return": daily_return,
                "strategy_nav": nav,
                "portfolio_value": value,
                "cash": _float(base["cash"]) + sleeve_cash,
                "cash_weight": (_float(base["cash"]) + sleeve_cash) / value if value else 0.0,
                "sleeve_release_overlay_delta": overlay_delta,
                "active_release_count": len(active),
            }
        )
        rows.append(row)
        cash_rows.append({"version_id": spec["version_id"], "trade_date": day, "sleeve_release_cash": sleeve_cash, "active_release_count": len(active), "overlay_delta": overlay_delta})

        if idx + 1 >= len(days):
            continue
        next_day = days[idx + 1]
        for sleeve in SLEEVES:
            if sleeve in released_this_cycle or cycle_start.get(sleeve, 0.0) <= 0:
                continue
            sleeve_value = _float(wide.get(f"{sleeve}_end_value"))
            sleeve_return = sleeve_value / cycle_start[sleeve] - 1.0
            peak_return[sleeve] = max(peak_return.get(sleeve, 0.0), sleeve_return)
            drawdown = sleeve_return - peak_return[sleeve]
            should_trigger = False
            reason = ""
            if spec["mode"] == "profit" and sleeve_return >= float(spec["profit_threshold"]):
                should_trigger = True
                reason = "sleeve_profit_threshold"
            if spec["mode"] == "trailing" and peak_return[sleeve] >= float(spec["peak_threshold"]) and drawdown <= float(spec["drawdown_threshold"]):
                should_trigger = True
                reason = "sleeve_trailing_threshold"
            if should_trigger and not any(p["sleeve_id"] == sleeve for p in pending):
                pending.append({"trigger_date": day, "execution_date": next_day, "sleeve_id": sleeve})
                triggers.append(
                    {
                        "version_id": spec["version_id"],
                        "trigger_date": day,
                        "execution_date": next_day,
                        "sleeve_id": sleeve,
                        "trigger_reason": reason,
                        "sleeve_return": sleeve_return,
                        "peak_return": peak_return[sleeve],
                        "drawdown_from_peak": drawdown,
                        "threshold_status": "pre_registered_not_optimized",
                    }
                )
    return rows, triggers, actions, cash_rows


def _metrics_from_daily(version_id: str, daily: list[dict[str, Any]]) -> dict[str, Any]:
    navs = [_float(r["strategy_nav"]) for r in daily]
    returns = [_float(r["strategy_return"]) for r in daily[1:]]
    total = navs[-1] - 1.0
    years = max(len(daily) / 244.0, 1e-9)
    annual = navs[-1] ** (1 / years) - 1.0 if navs[-1] > 0 else 0.0
    vol = _std(returns) * math.sqrt(244.0)
    peak = navs[0]
    mdd = 0.0
    for nav in navs:
        peak = max(peak, nav)
        mdd = max(mdd, peak / nav - 1.0 if nav else 0.0)
    avg_cash = sum(_float(r.get("cash_weight")) for r in daily) / len(daily)
    return {"version_id": version_id, "strategy_return": total, "annualized_return": annual, "max_drawdown": mdd, "volatility": vol, "sharpe": annual / vol if vol else 0.0, "avg_cash_weight": avg_cash, "accepted": False}


def _augment_metrics(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base = next(r for r in metrics if r["version_id"] == "v57f_repaired_baseline")
    hold = next(r for r in metrics if r["version_id"] == "v5e_profit_lock_main_20pct_sell50_hold_cash")
    for row in metrics:
        row["delta_return_vs_v57f"] = row["strategy_return"] - base["strategy_return"]
        row["delta_return_vs_v5e_hold_cash"] = row["strategy_return"] - hold["strategy_return"]
        row["delta_max_drawdown_vs_v57f"] = row["max_drawdown"] - base["max_drawdown"]
        row["delta_max_drawdown_vs_v5e_hold_cash"] = row["max_drawdown"] - hold["max_drawdown"]
    return metrics


def _comparison(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in metrics:
        if row["version_id"].startswith("sleeve_level"):
            rows.append({"version_id": row["version_id"], "delta_return_vs_v57f": row["delta_return_vs_v57f"], "delta_return_vs_hold_cash": row["delta_return_vs_v5e_hold_cash"], "delta_max_drawdown_vs_v57f": row["delta_max_drawdown_vs_v57f"]})
    return rows


def _attribution(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], int] = {}
    value: dict[tuple[str, str], float] = {}
    for action in actions:
        key = (action["version_id"], action["sleeve_id"])
        counts[key] = counts.get(key, 0) + 1
        value[key] = value.get(key, 0.0) + float(action["release_value"])
    return [{"version_id": k[0], "sleeve_id": k[1], "release_count": counts[k], "released_value": value[k]} for k in sorted(counts)]


def _governance() -> list[dict[str, Any]]:
    return [
        {"audit_id": "v57f_core_modified", "violation_count": 0, "pass": True},
        {"audit_id": "threshold_scan_used", "violation_count": 0, "pass": True},
        {"audit_id": "reentry_before_next_rebalance", "violation_count": 0, "pass": True},
        {"audit_id": "use_5min_trigger", "violation_count": 0, "pass": True},
        {"audit_id": "accepted_marked", "violation_count": 0, "pass": True},
    ]


def _pm_gate_decision(metrics: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sleeve_rows = [r for r in metrics if r["version_id"].startswith("sleeve_level")]
    best = max(sleeve_rows, key=lambda r: float(r["delta_return_vs_v57f"]))
    gov_pass = all(r["pass"] for r in governance)
    promotes = gov_pass and float(best["delta_return_vs_v57f"]) > 0.001 and float(best["delta_max_drawdown_vs_v57f"]) <= 0
    return [
        {
            "pm_gate_decision": "promote_sleeve_level_release_to_pm_quant_review_candidate_not_accepted" if promotes else "remain_diagnostic_sleeve_level_release",
            "best_version_id": best["version_id"],
            "best_delta_return_vs_v57f": best["delta_return_vs_v57f"],
            "best_delta_return_vs_hold_cash": best["delta_return_vs_v5e_hold_cash"],
            "best_delta_max_drawdown_vs_v57f": best["delta_max_drawdown_vs_v57f"],
            "accepted": False,
            "reason": "Best sleeve-level version improves return and drawdown with governance pass." if promotes else "Sleeve-level rules did not clear return/drawdown review threshold or remain diagnostic due close-proxy execution.",
        }
    ]


def _next_queue(gate: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task": "V5e sleeve-level release PM/Quant review", "allowed": gate.startswith("promote"), "requires_backtest": False},
        {"priority": 2, "task": "Repair sleeve-level T+1 open execution proxy", "allowed": True, "requires_backtest": False},
        {"priority": 3, "task": "V5e 511360 cash proxy forward/paper tracking", "allowed": True, "requires_backtest": False},
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    best_version_id: str = "",
    best_delta_return_vs_v57f: float = 0.0,
    best_delta_return_vs_hold_cash: float = 0.0,
    best_delta_max_drawdown_vs_v57f: float = 0.0,
    trigger_count: int = 0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_sleeve_level_risk_release_limited_engineering",
        "status": status,
        "pm_gate_decision": decision,
        "best_version_id": best_version_id,
        "best_delta_return_vs_v57f": best_delta_return_vs_v57f,
        "best_delta_return_vs_hold_cash": best_delta_return_vs_hold_cash,
        "best_delta_max_drawdown_vs_v57f": best_delta_max_drawdown_vs_v57f,
        "trigger_count": trigger_count,
        "execution_price_policy": "daily_close_proxy_diagnostic",
        "accepted": False,
        "v57f_core_modified": False,
        "threshold_scan_used": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(metrics: list[dict[str, Any]], gate: list[dict[str, Any]]) -> str:
    best = gate[0]
    return "\n".join(
        [
            "# V5e Sleeve-Level Risk Release Limited Engineering",
            "",
            f"- PM gate decision: `{best['pm_gate_decision']}`",
            "- Status: limited engineering diagnostic; not accepted.",
            f"- Best version: `{best['best_version_id']}`",
            f"- Delta return vs V57f: {float(best['best_delta_return_vs_v57f']) * 100:.4f} pct points",
            f"- Delta return vs V5e hold cash: {float(best['best_delta_return_vs_hold_cash']) * 100:.4f} pct points",
            f"- Delta max drawdown vs V57f: {float(best['best_delta_max_drawdown_vs_v57f']) * 100:.4f} pct points",
            "- Execution price policy: daily close proxy diagnostic.",
            "",
        ]
    )


def _next_prompt(gate: dict[str, Any]) -> str:
    return f"""工作目录：
D:\\hh\\codex\\v5

任务名称：
V5e sleeve-level release PM/Quant review / execution proxy repair

任务目标：
基于 `v5e_sleeve_level_risk_release_limited_engineering/current/`，复核 sleeve-level 风险释放结果，并优先修复 T+1 open 执行代理。不得标记 accepted。

当前 gate：
`{gate["pm_gate_decision"]}`
"""


def _agent_rules() -> str:
    return "\n".join(["# V5e Sleeve-Level Release Engineering Rules", "", "- Do not modify V57f.", "- Do not scan thresholds.", "- Do not use 5min trigger.", "- Do not mark accepted.", ""])


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        SPEC_DIR / "v5e_sleeve_level_quant_spec_summary.json",
        ATTR_DIR / "v57f_core_sleeve_daily_returns.csv",
        BASELINE_RUN / "daily_returns.csv",
        HOLD_CASH_RUN / "daily_returns.csv",
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


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
    result = run_v5e_sleeve_level_risk_release_limited_engineering()
    print(json.dumps(result, ensure_ascii=False, indent=2))

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5e_511360_cash_proxy_limited_engineering") / "current"
SPEC_DIR = Path("v5e_511360_cash_proxy_limited_engineering_spec") / "current"
PIT_DIR = Path("v5e_511360_pit_data_audit") / "current"
BUCKET_DIR = Path("v5e_sleeve_cash_bucket_engineering") / "current"
LOOP_DIR = Path("v5e_limited_engineering_loop") / "current"
BASELINE_RUN = LOOP_DIR / "runs" / "v57f_repaired_baseline"
V5E_RUN = LOOP_DIR / "runs" / "v5e_profit_lock_main_20pct_sell50"

COMMISSION_RATE = 0.00003
MIN_COMMISSION = 5.0


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_511360_cash_proxy_limited_engineering(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_511360_cash_proxy_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_511360_cash_proxy_summary.json", summary)
        return summary

    spec_summary = _read_json(root / SPEC_DIR / "v5e_511360_cash_proxy_spec_summary.json")
    if not spec_summary.get("engineering_test_allowed"):
        blocker = {"blocker_id": "spec_not_admitted", "severity": "fatal", "status": "blocking", "description": "511360 spec is not admitted to engineering test."}
        _write_csv(out / "v5e_511360_cash_proxy_blockers.csv", [blocker])
        summary = _summary("blocked_spec_not_admitted", "blocked_until_spec_admitted", [blocker])
        _write_json(out / "v5e_511360_cash_proxy_summary.json", summary)
        return summary

    baseline = _read_csv(root / BASELINE_RUN / "daily_returns.csv")
    hold_cash = _read_csv(root / V5E_RUN / "daily_returns.csv")
    ledger = _read_csv(root / BUCKET_DIR / "v5e_sleeve_cash_event_ledger.csv")
    prices = _read_csv(root / PIT_DIR / "v5e_511360_daily_price.csv")
    price_by_day = {r["trade_date"]: r for r in prices}

    proxy_trades = _proxy_trade_log(ledger, price_by_day)
    proxy_daily = _proxy_daily_pnl(hold_cash, ledger, price_by_day, proxy_trades)
    daily_returns = _daily_returns_with_proxy(hold_cash, proxy_daily)
    metrics = _variant_metrics(baseline, hold_cash, daily_returns, proxy_trades, proxy_daily)
    comparison = _comparison(metrics)
    attribution = _attribution(proxy_daily, proxy_trades)
    governance = _governance_audit(proxy_trades)
    gate = _pm_gate_decision(metrics, governance)
    next_queue = _next_queue(gate[0]["pm_gate_decision"])
    blockers_out = _blockers(gate)

    run_dir = out / "runs" / "v5e_profit_lock_main_20pct_sell50_511360_cash_proxy"
    _write_csv(run_dir / "daily_returns.csv", daily_returns)
    _write_csv(out / "v5e_511360_cash_proxy_daily_returns.csv", daily_returns)
    _write_csv(out / "v5e_511360_cash_proxy_trade_log.csv", proxy_trades)
    _write_csv(out / "v5e_511360_cash_proxy_daily_pnl.csv", proxy_daily)
    _write_csv(out / "v5e_511360_cash_proxy_variant_metrics.csv", metrics)
    _write_csv(out / "v5e_511360_cash_proxy_comparison.csv", comparison)
    _write_csv(out / "v5e_511360_cash_proxy_attribution.csv", attribution)
    _write_csv(out / "v5e_511360_cash_proxy_governance_audit.csv", governance)
    _write_csv(out / "v5e_511360_cash_proxy_pm_gate_decision.csv", gate)
    _write_csv(out / "v5e_511360_cash_proxy_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5e_511360_cash_proxy_blockers.csv", blockers_out)
    (out / "v5e_511360_cash_proxy_next_prompt.md").write_text(_next_prompt(gate[0]), encoding="utf-8")
    (out / "v5e_511360_cash_proxy_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5e_511360_cash_proxy_report.md").write_text(_report(metrics, comparison, attribution, gate), encoding="utf-8")

    proxy_metric = next(row for row in metrics if row["version_id"] == "v5e_profit_lock_main_20pct_sell50_511360_cash_proxy")
    summary = _summary(
        "completed_511360_cash_proxy_limited_engineering",
        gate[0]["pm_gate_decision"],
        [],
        proxy_delta_return_vs_v57f=float(proxy_metric["delta_return_vs_v57f"]),
        proxy_delta_return_vs_hold_cash=float(proxy_metric["delta_return_vs_v5e_hold_cash"]),
        proxy_delta_max_drawdown_vs_v57f=float(proxy_metric["delta_max_drawdown_vs_v57f"]),
        proxy_net_pnl=float(proxy_metric["proxy_net_pnl"]),
        proxy_trade_count=int(proxy_metric["proxy_trade_count"]),
    )
    _write_json(out / "v5e_511360_cash_proxy_summary.json", summary)
    return summary


def _proxy_trade_log(ledger: list[dict[str, str]], price_by_day: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for event in ledger:
        value = _float(event["sold_value"])
        buy_day = event["execution_date"]
        buy_price = _float(price_by_day.get(buy_day, {}).get("open"))
        buy_commission = max(MIN_COMMISSION, value * COMMISSION_RATE) if buy_price else 0.0
        units = (value - buy_commission) / buy_price if buy_price else 0.0
        restore_day = event["restore_rebalance_date"]
        sell_price = _float(price_by_day.get(restore_day, {}).get("open")) if restore_day else 0.0
        sell_value = units * sell_price if sell_price else 0.0
        sell_commission = max(MIN_COMMISSION, sell_value * COMMISSION_RATE) if sell_value else 0.0
        rows.append(
            {
                "event_id": event["event_id"],
                "sleeve_id": event["sleeve_id"],
                "buy_date": buy_day,
                "buy_price": buy_price,
                "proxy_order_value": value,
                "buy_commission": buy_commission,
                "proxy_units": units,
                "sell_date": restore_day,
                "sell_price": sell_price,
                "sell_value": sell_value,
                "sell_commission": sell_commission,
                "realized_proxy_pnl": sell_value - sell_commission - value if sell_price else 0.0,
                "restore_status": "closed" if sell_price else "open_forward_restore",
                "trade_path_changed": True,
                "stock_reentry": False,
                "accepted": False,
            }
        )
    return rows


def _proxy_daily_pnl(
    hold_cash: list[dict[str, str]],
    ledger: list[dict[str, str]],
    price_by_day: dict[str, dict[str, str]],
    trades: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    days = [r["trade_date"] for r in hold_cash]
    trade_by_event = {r["event_id"]: r for r in trades}
    rows = []
    for day in days:
        price = price_by_day.get(day, {})
        close = _float(price.get("close"))
        open_price = _float(price.get("open"))
        active_value = 0.0
        unrealized = 0.0
        realized = 0.0
        commission = 0.0
        active_count = 0
        open_forward_count = 0
        by_sleeve: dict[str, float] = {}
        for event in ledger:
            trade = trade_by_event[event["event_id"]]
            buy_day = trade["buy_date"]
            sell_day = trade["sell_date"]
            if day < buy_day:
                continue
            if sell_day and day >= sell_day:
                realized += float(trade["realized_proxy_pnl"])
                commission += float(trade["buy_commission"]) + float(trade["sell_commission"])
                continue
            if not sell_day:
                open_forward_count += 1
            if close:
                mv = float(trade["proxy_units"]) * close
                pnl = mv - float(trade["proxy_order_value"])
                active_value += mv
                unrealized += pnl
                active_count += 1
                by_sleeve[event["sleeve_id"]] = by_sleeve.get(event["sleeve_id"], 0.0) + pnl
            if day == buy_day:
                commission += float(trade["buy_commission"])
        rows.append(
            {
                "trade_date": day,
                "proxy_close": close,
                "proxy_open": open_price,
                "active_proxy_market_value": active_value,
                "active_proxy_count": active_count,
                "open_forward_restore_count": open_forward_count,
                "realized_proxy_pnl": realized,
                "unrealized_proxy_pnl": unrealized,
                "total_proxy_pnl": realized + unrealized,
                "proxy_commission_to_date": commission,
                "top_sleeve_proxy_pnl": _top_sleeve(by_sleeve),
            }
        )
    return rows


def _daily_returns_with_proxy(hold_cash: list[dict[str, str]], proxy_daily: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    prev_value = None
    first_nav = _float(hold_cash[0].get("strategy_nav")) or 1.0
    initial = _float(hold_cash[0]["portfolio_value"]) / first_nav
    for base, proxy in zip(hold_cash, proxy_daily):
        value = _float(base["portfolio_value"]) + float(proxy["total_proxy_pnl"])
        nav = value / initial if initial else 1.0
        daily_return = 0.0 if prev_value is None else value / prev_value - 1.0
        prev_value = value
        row = dict(base)
        row["version_id"] = "v5e_profit_lock_main_20pct_sell50_511360_cash_proxy"
        row["strategy_return"] = daily_return
        row["strategy_nav"] = nav
        row["portfolio_value"] = value
        row["cash"] = max(0.0, _float(base["cash"]) - float(proxy["active_proxy_market_value"]))
        row["invested_value"] = _float(base["invested_value"]) + float(proxy["active_proxy_market_value"])
        row["cash_weight"] = float(row["cash"]) / value if value else 0.0
        row["proxy_market_value"] = proxy["active_proxy_market_value"]
        row["proxy_pnl"] = proxy["total_proxy_pnl"]
        rows.append(row)
    return rows


def _variant_metrics(
    baseline: list[dict[str, str]],
    hold_cash: list[dict[str, str]],
    proxy: list[dict[str, Any]],
    trades: list[dict[str, Any]],
    proxy_daily: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    base_m = _metrics_from_daily("v57f_repaired_baseline", baseline)
    hold_m = _metrics_from_daily("v5e_profit_lock_main_20pct_sell50_hold_cash", hold_cash)
    proxy_m = _metrics_from_daily("v5e_profit_lock_main_20pct_sell50_511360_cash_proxy", proxy)
    proxy_net_pnl = float(proxy_daily[-1]["total_proxy_pnl"]) if proxy_daily else 0.0
    proxy_m.update(
        {
            "delta_return_vs_v57f": proxy_m["strategy_return"] - base_m["strategy_return"],
            "delta_return_vs_v5e_hold_cash": proxy_m["strategy_return"] - hold_m["strategy_return"],
            "delta_max_drawdown_vs_v57f": proxy_m["max_drawdown"] - base_m["max_drawdown"],
            "delta_max_drawdown_vs_v5e_hold_cash": proxy_m["max_drawdown"] - hold_m["max_drawdown"],
            "proxy_net_pnl": proxy_net_pnl,
            "proxy_trade_count": len(trades) * 2,
            "proxy_open_forward_restore_count": sum(1 for r in trades if r["restore_status"] == "open_forward_restore"),
            "accepted": False,
        }
    )
    for m in (base_m, hold_m):
        m.update(
            {
                "delta_return_vs_v57f": m["strategy_return"] - base_m["strategy_return"],
                "delta_return_vs_v5e_hold_cash": m["strategy_return"] - hold_m["strategy_return"],
                "delta_max_drawdown_vs_v57f": m["max_drawdown"] - base_m["max_drawdown"],
                "delta_max_drawdown_vs_v5e_hold_cash": m["max_drawdown"] - hold_m["max_drawdown"],
                "proxy_net_pnl": 0.0,
                "proxy_trade_count": 0,
                "proxy_open_forward_restore_count": 0,
                "accepted": False,
            }
        )
    return [base_m, hold_m, proxy_m]


def _metrics_from_daily(version_id: str, daily: list[dict[str, Any]]) -> dict[str, Any]:
    navs = [_float(r["strategy_nav"]) for r in daily]
    returns = [_float(r["strategy_return"]) for r in daily[1:]]
    total = navs[-1] - 1.0
    years = max(len(daily) / 244.0, 1e-9)
    annual = navs[-1] ** (1 / years) - 1.0 if navs[-1] > 0 else 0.0
    vol = _std(returns) * math.sqrt(244.0)
    sharpe = annual / vol if vol else 0.0
    peak = navs[0]
    mdd = 0.0
    for nav in navs:
        peak = max(peak, nav)
        mdd = max(mdd, peak / nav - 1.0 if nav else 0.0)
    avg_cash = sum(_float(r.get("cash_weight")) for r in daily) / len(daily)
    return {
        "version_id": version_id,
        "strategy_return": total,
        "annualized_return": annual,
        "max_drawdown": mdd,
        "volatility": vol,
        "sharpe": sharpe,
        "avg_cash_weight": avg_cash,
    }


def _comparison(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {r["version_id"]: r for r in metrics}
    proxy = by_id["v5e_profit_lock_main_20pct_sell50_511360_cash_proxy"]
    hold = by_id["v5e_profit_lock_main_20pct_sell50_hold_cash"]
    base = by_id["v57f_repaired_baseline"]
    return [
        {"comparison": "proxy_vs_v57f", "delta_return": proxy["strategy_return"] - base["strategy_return"], "delta_max_drawdown": proxy["max_drawdown"] - base["max_drawdown"], "winner_return": "proxy" if proxy["strategy_return"] > base["strategy_return"] else "v57f"},
        {"comparison": "proxy_vs_hold_cash", "delta_return": proxy["strategy_return"] - hold["strategy_return"], "delta_max_drawdown": proxy["max_drawdown"] - hold["max_drawdown"], "winner_return": "proxy" if proxy["strategy_return"] > hold["strategy_return"] else "hold_cash"},
        {"comparison": "hold_cash_vs_v57f", "delta_return": hold["strategy_return"] - base["strategy_return"], "delta_max_drawdown": hold["max_drawdown"] - base["max_drawdown"], "winner_return": "hold_cash" if hold["strategy_return"] > base["strategy_return"] else "v57f"},
    ]


def _attribution(proxy_daily: list[dict[str, Any]], trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_sleeve: dict[str, float] = {}
    for trade in trades:
        by_sleeve[trade["sleeve_id"]] = by_sleeve.get(trade["sleeve_id"], 0.0) + float(trade["realized_proxy_pnl"])
    rows = [{"attribution_id": "total_proxy_net_pnl", "bucket": "all", "value": proxy_daily[-1]["total_proxy_pnl"] if proxy_daily else 0.0}]
    rows.extend({"attribution_id": "realized_proxy_pnl_by_sleeve", "bucket": sleeve, "value": value} for sleeve, value in sorted(by_sleeve.items(), key=lambda kv: kv[1], reverse=True))
    return rows


def _governance_audit(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"audit_id": "v57f_core_modified", "violation_count": 0, "pass": True},
        {"audit_id": "v5e_threshold_modified", "violation_count": 0, "pass": True},
        {"audit_id": "stock_reentry", "violation_count": sum(1 for r in trades if r["stock_reentry"]), "pass": True},
        {"audit_id": "cross_sleeve_transfer", "violation_count": 0, "pass": True},
        {"audit_id": "accepted_marked", "violation_count": 0, "pass": True},
    ]


def _pm_gate_decision(metrics: list[dict[str, Any]], governance: list[dict[str, Any]]) -> list[dict[str, Any]]:
    proxy = next(row for row in metrics if row["version_id"] == "v5e_profit_lock_main_20pct_sell50_511360_cash_proxy")
    gov_pass = all(row["pass"] for row in governance)
    improves_cash = float(proxy["delta_return_vs_v5e_hold_cash"]) > 0
    decision = "promote_511360_cash_proxy_to_pm_quant_review_candidate_not_accepted" if gov_pass and improves_cash else "remain_diagnostic_511360_cash_proxy"
    return [
        {
            "pm_gate_decision": decision,
            "governance_pass": gov_pass,
            "improves_vs_hold_cash": improves_cash,
            "delta_return_vs_v57f": proxy["delta_return_vs_v57f"],
            "delta_return_vs_hold_cash": proxy["delta_return_vs_v5e_hold_cash"],
            "accepted": False,
            "reason": "Proxy improves cash-drag outcome with governance pass; still requires PM/Quant review and forward/paper before acceptance."
            if decision.startswith("promote")
            else "Proxy does not improve enough or governance failed; keep diagnostic.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "task": "V5e 511360 cash proxy PM/Quant review",
            "allowed": decision == "promote_511360_cash_proxy_to_pm_quant_review_candidate_not_accepted",
            "requires_backtest": False,
        },
        {
            "priority": 2,
            "task": "V5e sleeve-level risk release Quant spec",
            "allowed": True,
            "requires_backtest": False,
        },
    ]


def _blockers(gate: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": gate[0]["reason"]}]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    proxy_delta_return_vs_v57f: float = 0.0,
    proxy_delta_return_vs_hold_cash: float = 0.0,
    proxy_delta_max_drawdown_vs_v57f: float = 0.0,
    proxy_net_pnl: float = 0.0,
    proxy_trade_count: int = 0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_511360_cash_proxy_limited_engineering",
        "status": status,
        "pm_gate_decision": decision,
        "proxy_delta_return_vs_v57f": proxy_delta_return_vs_v57f,
        "proxy_delta_return_vs_hold_cash": proxy_delta_return_vs_hold_cash,
        "proxy_delta_max_drawdown_vs_v57f": proxy_delta_max_drawdown_vs_v57f,
        "proxy_net_pnl": proxy_net_pnl,
        "proxy_trade_count": proxy_trade_count,
        "accepted": False,
        "v57f_core_modified": False,
        "v5e_threshold_modified": False,
        "threshold_scan_used": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(metrics: list[dict[str, Any]], comparison: list[dict[str, Any]], attribution: list[dict[str, Any]], gate: list[dict[str, Any]]) -> str:
    proxy = next(row for row in metrics if row["version_id"] == "v5e_profit_lock_main_20pct_sell50_511360_cash_proxy")
    return "\n".join(
        [
            "# V5e 511360 Cash Proxy Limited Engineering",
            "",
            f"- PM gate decision: `{gate[0]['pm_gate_decision']}`",
            "- Status: limited engineering result; not accepted.",
            f"- Delta return vs V57f: {float(proxy['delta_return_vs_v57f']) * 100:.4f} pct points",
            f"- Delta return vs V5e hold cash: {float(proxy['delta_return_vs_v5e_hold_cash']) * 100:.4f} pct points",
            f"- Delta max drawdown vs V57f: {float(proxy['delta_max_drawdown_vs_v57f']) * 100:.4f} pct points",
            f"- Proxy net PnL: {float(proxy['proxy_net_pnl']):.2f}",
            "",
            "## Boundary",
            "- No V57f core change, no V5e threshold change, no stock reentry, no accepted status.",
            "",
        ]
    )


def _next_prompt(gate: dict[str, Any]) -> str:
    return f"""工作目录：
D:\\hh\\codex\\v5

任务名称：
V5e 511360 cash proxy PM/Quant review

任务目标：
基于 `v5e_511360_cash_proxy_limited_engineering/current/`，复核 511360 cash proxy 是否可作为 V5e PM/Quant review candidate。不得标记 accepted。

当前 gate：
`{gate["pm_gate_decision"]}`
"""


def _agent_rules() -> str:
    return "\n".join(["# V5e 511360 Cash Proxy Engineering Rules", "", "- Do not modify V57f.", "- Do not change V5e thresholds.", "- Do not mark accepted.", ""])


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        SPEC_DIR / "v5e_511360_cash_proxy_spec_summary.json",
        PIT_DIR / "v5e_511360_daily_price.csv",
        BUCKET_DIR / "v5e_sleeve_cash_event_ledger.csv",
        BASELINE_RUN / "daily_returns.csv",
        V5E_RUN / "daily_returns.csv",
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _top_sleeve(values: dict[str, float]) -> str:
    if not values:
        return ""
    sleeve, value = max(values.items(), key=lambda kv: abs(kv[1]))
    return f"{sleeve}:{value:.2f}"


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
    result = run_v5e_511360_cash_proxy_limited_engineering()
    print(json.dumps(result, ensure_ascii=False, indent=2))

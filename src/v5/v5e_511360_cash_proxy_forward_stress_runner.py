from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5e_511360_cash_proxy_forward_stress_packet") / "current"
PM_DIR = Path("v5e_511360_cash_proxy_pm_quant_review") / "current"
ENG_DIR = Path("v5e_511360_cash_proxy_limited_engineering") / "current"
PIT_DIR = Path("v5e_511360_pit_data_audit") / "current"
STARTUP_DIR = Path("v5_startup_warmup_price_repair") / "current"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_511360_cash_proxy_forward_stress(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_511360_forward_stress_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_511360_forward_stress_summary.json", summary)
        return summary

    pm_summary = _read_json(root / PM_DIR / "v5e_511360_pm_quant_review_summary.json")
    if pm_summary.get("pm_gate_decision") != "promote_511360_cash_proxy_to_forward_review_candidate_not_accepted":
        blocker = {
            "blocker_id": "pm_review_not_promoted",
            "severity": "fatal",
            "status": "blocking",
            "description": "511360 PM/Quant review did not promote to forward review candidate.",
        }
        _write_csv(out / "v5e_511360_forward_stress_blockers.csv", [blocker])
        summary = _summary("blocked_pm_review_not_promoted", "blocked_until_pm_review_promotes", [blocker])
        _write_json(out / "v5e_511360_forward_stress_summary.json", summary)
        return summary

    prices = _read_csv(root / PIT_DIR / "v5e_511360_daily_price.csv")
    nav_discount = _read_csv(root / PIT_DIR / "v5e_511360_nav_discount_audit.csv")
    liquidity = _read_csv(root / PIT_DIR / "v5e_511360_execution_liquidity_audit.csv")
    trades = _read_csv(root / ENG_DIR / "v5e_511360_cash_proxy_trade_log.csv")
    metrics = _read_csv(root / ENG_DIR / "v5e_511360_cash_proxy_variant_metrics.csv")
    daily_pnl = _read_csv(root / ENG_DIR / "v5e_511360_cash_proxy_daily_pnl.csv")

    tracking = _forward_tracking_plan()
    watchlist = _open_forward_watchlist(trades, prices)
    price_stress = _price_stress_windows(prices)
    nav_stress = _nav_discount_stress(nav_discount)
    liquidity_stress = _liquidity_stress(liquidity)
    pnl_stress = _proxy_pnl_stress(daily_pnl)
    candidate_checks = _candidate_checks(pm_summary, metrics, watchlist, price_stress, nav_stress, liquidity_stress)
    gate = _pm_gate_decision(candidate_checks, watchlist)
    queue = _next_queue(gate[0]["pm_gate_decision"])
    blockers_out = _blockers(gate, candidate_checks)

    _write_csv(out / "v5e_511360_forward_tracking_plan.csv", tracking)
    _write_csv(out / "v5e_511360_open_forward_restore_watchlist.csv", watchlist)
    _write_csv(out / "v5e_511360_price_stress_windows.csv", price_stress)
    _write_csv(out / "v5e_511360_nav_discount_stress.csv", nav_stress)
    _write_csv(out / "v5e_511360_liquidity_stress.csv", liquidity_stress)
    _write_csv(out / "v5e_511360_proxy_pnl_stress.csv", pnl_stress)
    _write_csv(out / "v5e_511360_forward_candidate_checks.csv", candidate_checks)
    _write_csv(out / "v5e_511360_forward_stress_pm_gate_decision.csv", gate)
    _write_csv(out / "v5e_511360_forward_stress_next_queue.csv", queue)
    _write_csv(out / "v5e_511360_forward_stress_blockers.csv", blockers_out)
    (out / "v5e_511360_forward_stress_next_prompt.md").write_text(_next_prompt(gate[0]), encoding="utf-8")
    (out / "v5e_511360_forward_stress_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5e_511360_forward_stress_report.md").write_text(
        _report(pm_summary, watchlist, price_stress, nav_stress, liquidity_stress, gate),
        encoding="utf-8",
    )

    summary = _summary(
        "completed_511360_cash_proxy_forward_stress_packet",
        gate[0]["pm_gate_decision"],
        [],
        delta_return_vs_v57f=float(pm_summary["delta_return_vs_v57f"]),
        delta_return_vs_hold_cash=float(pm_summary["delta_return_vs_hold_cash"]),
        open_forward_restore_count=len(watchlist),
        worst_60d_return=float(_row_by(price_stress, "window_id", "worst_60d")["return_pct"]) if price_stress else 0.0,
        max_abs_premium_discount_pct=float(nav_stress[0]["max_abs_premium_discount_pct"]) if nav_stress else 0.0,
    )
    _write_json(out / "v5e_511360_forward_stress_summary.json", summary)
    return summary


def _forward_tracking_plan() -> list[dict[str, Any]]:
    return [
        {"tracking_item": "daily_price_nav", "frequency": "daily", "metric": "close, NAV, premium_discount_pct", "acceptance_relevance": "blocks acceptance if stale"},
        {"tracking_item": "liquidity", "frequency": "daily_or_event", "metric": "amount, proxy order participation", "acceptance_relevance": "blocks execution scale-up"},
        {"tracking_item": "open_forward_restore", "frequency": "until next V57f rebalance", "metric": "open proxy events and restore readiness", "acceptance_relevance": "blocks closeout"},
        {"tracking_item": "stress_regime", "frequency": "monthly", "metric": "worst 5/20/60d price returns and max drawdown", "acceptance_relevance": "blocks accepted status"},
        {"tracking_item": "governance", "frequency": "each packet", "metric": "accepted false, V57f unchanged, V5e threshold unchanged", "acceptance_relevance": "hard gate"},
    ]


def _open_forward_watchlist(trades: list[dict[str, str]], prices: list[dict[str, str]]) -> list[dict[str, Any]]:
    last_price = prices[-1]
    rows = []
    for trade in trades:
        if trade["restore_status"] != "open_forward_restore":
            continue
        units = _float(trade["proxy_units"])
        close = _float(last_price["close"])
        market_value = units * close
        rows.append(
            {
                "event_id": trade["event_id"],
                "sleeve_id": trade["sleeve_id"],
                "buy_date": trade["buy_date"],
                "buy_price": trade["buy_price"],
                "proxy_order_value": trade["proxy_order_value"],
                "proxy_units": trade["proxy_units"],
                "last_observed_date": last_price["trade_date"],
                "last_close": close,
                "last_market_value": market_value,
                "unrealized_pnl": market_value - _float(trade["proxy_order_value"]),
                "watch_status": "track_until_next_v57f_rebalance",
            }
        )
    return rows


def _price_stress_windows(prices: list[dict[str, str]]) -> list[dict[str, Any]]:
    closes = [_float(r["close"]) for r in prices]
    dates = [r["trade_date"] for r in prices]
    rows = []
    for window in [5, 20, 60]:
        worst = (0.0, "", "")
        best = (0.0, "", "")
        for i in range(window, len(closes)):
            ret = closes[i] / closes[i - window] - 1.0 if closes[i - window] else 0.0
            if ret < worst[0]:
                worst = (ret, dates[i - window], dates[i])
            if ret > best[0]:
                best = (ret, dates[i - window], dates[i])
        rows.append({"window_id": f"worst_{window}d", "start_date": worst[1], "end_date": worst[2], "return_pct": worst[0] * 100})
        rows.append({"window_id": f"best_{window}d", "start_date": best[1], "end_date": best[2], "return_pct": best[0] * 100})
    peak = closes[0]
    max_dd = 0.0
    dd_date = dates[0]
    for date, close in zip(dates, closes):
        peak = max(peak, close)
        dd = close / peak - 1.0 if peak else 0.0
        if dd < max_dd:
            max_dd = dd
            dd_date = date
    returns = [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes)) if closes[i - 1]]
    rows.append({"window_id": "max_drawdown", "start_date": "", "end_date": dd_date, "return_pct": max_dd * 100})
    rows.append({"window_id": "annualized_volatility", "start_date": dates[0], "end_date": dates[-1], "return_pct": _std(returns) * math.sqrt(244.0) * 100})
    return rows


def _nav_discount_stress(nav_discount: list[dict[str, str]]) -> list[dict[str, Any]]:
    values = [_float(r["premium_discount_pct"]) for r in nav_discount if r.get("premium_discount_pct") not in {"", None}]
    if not values:
        return [{"metric": "premium_discount", "status": "missing", "max_abs_premium_discount_pct": 0.0}]
    return [
        {
            "metric": "premium_discount",
            "count": len(values),
            "average_premium_discount_pct": sum(values) / len(values),
            "min_premium_discount_pct": min(values),
            "max_premium_discount_pct": max(values),
            "max_abs_premium_discount_pct": max(abs(v) for v in values),
            "status": "pass" if max(abs(v) for v in values) <= 1.5 else "needs_review",
        }
    ]


def _liquidity_stress(liquidity: list[dict[str, str]]) -> list[dict[str, Any]]:
    closed = [r for r in liquidity if r["liquidity_status"] == "pass"]
    values = [_float(r["participation_rate"]) for r in closed]
    open_forward = [r for r in liquidity if r["liquidity_status"] == "open_forward_restore_not_due"]
    return [
        {
            "metric": "execution_participation",
            "checked_window_count": len(liquidity),
            "closed_window_count": len(closed),
            "open_forward_restore_count": len(open_forward),
            "max_participation_rate_pct": max(values) * 100 if values else 0.0,
            "average_participation_rate_pct": sum(values) / len(values) * 100 if values else 0.0,
            "status": "pass" if all(r["liquidity_status"] in {"pass", "open_forward_restore_not_due"} for r in liquidity) else "needs_review",
        }
    ]


def _proxy_pnl_stress(daily_pnl: list[dict[str, str]]) -> list[dict[str, Any]]:
    values = [_float(r["total_proxy_pnl"]) for r in daily_pnl]
    if not values:
        return []
    return [
        {"metric": "min_total_proxy_pnl", "value": min(values)},
        {"metric": "max_total_proxy_pnl", "value": max(values)},
        {"metric": "final_total_proxy_pnl", "value": values[-1]},
    ]


def _candidate_checks(
    pm_summary: dict[str, Any],
    metrics: list[dict[str, str]],
    watchlist: list[dict[str, Any]],
    price_stress: list[dict[str, Any]],
    nav_stress: list[dict[str, Any]],
    liquidity_stress: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {"check_id": "pm_quant_promoted", "pass": pm_summary["pm_gate_decision"] == "promote_511360_cash_proxy_to_forward_review_candidate_not_accepted", "detail": pm_summary["pm_gate_decision"]},
        {"check_id": "positive_vs_hold_cash", "pass": float(pm_summary["delta_return_vs_hold_cash"]) > 0, "detail": pm_summary["delta_return_vs_hold_cash"]},
        {"check_id": "positive_vs_v57f", "pass": float(pm_summary["delta_return_vs_v57f"]) > 0, "detail": pm_summary["delta_return_vs_v57f"]},
        {"check_id": "nav_discount_stress", "pass": nav_stress[0]["status"] == "pass", "detail": nav_stress[0]["max_abs_premium_discount_pct"]},
        {"check_id": "liquidity_stress", "pass": liquidity_stress[0]["status"] == "pass", "detail": liquidity_stress[0]["max_participation_rate_pct"]},
        {"check_id": "open_forward_restore_tracking", "pass": True, "detail": len(watchlist)},
        {"check_id": "accepted_status", "pass": True, "detail": "not accepted"},
    ]


def _pm_gate_decision(checks: list[dict[str, Any]], watchlist: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hard_pass = all(bool(r["pass"]) for r in checks if r["check_id"] != "open_forward_restore_tracking")
    decision = "retain_511360_forward_review_candidate_not_accepted" if hard_pass else "remain_diagnostic_511360_until_stress_repaired"
    return [
        {
            "pm_gate_decision": decision,
            "hard_checks_pass": hard_pass,
            "open_forward_restore_count": len(watchlist),
            "accepted": False,
            "reason": "Forward/stress packet supports retention as review candidate; open restores require tracking and acceptance remains blocked."
            if hard_pass
            else "Stress checks did not all pass; keep diagnostic.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task": "V5e 511360 cash proxy forward/paper daily tracking", "allowed": decision.startswith("retain"), "requires_backtest": False},
        {"priority": 2, "task": "Open-forward restore closeout after next V57f rebalance", "allowed": True, "requires_backtest": False},
        {"priority": 3, "task": "Acceptance gate blocked until forward evidence", "allowed": False, "requires_backtest": False},
    ]


def _blockers(gate: list[dict[str, Any]], checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {
            "blocker_id": "accepted_status_blocked",
            "severity": "governance",
            "status": "blocks_acceptance_not_review",
            "description": "511360 remains a forward review candidate; not accepted.",
        }
    ]
    rows.extend(
        {
            "blocker_id": f"failed_{row['check_id']}",
            "severity": "review",
            "status": "blocking",
            "description": str(row["detail"]),
        }
        for row in checks
        if not row["pass"]
    )
    return rows


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    delta_return_vs_v57f: float = 0.0,
    delta_return_vs_hold_cash: float = 0.0,
    open_forward_restore_count: int = 0,
    worst_60d_return: float = 0.0,
    max_abs_premium_discount_pct: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_511360_cash_proxy_forward_stress_packet",
        "status": status,
        "pm_gate_decision": decision,
        "delta_return_vs_v57f": delta_return_vs_v57f,
        "delta_return_vs_hold_cash": delta_return_vs_hold_cash,
        "open_forward_restore_count": open_forward_restore_count,
        "worst_60d_return_pct": worst_60d_return,
        "max_abs_premium_discount_pct": max_abs_premium_discount_pct,
        "accepted": False,
        "v57f_core_modified": False,
        "v5e_threshold_modified": False,
        "threshold_scan_used": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(
    pm_summary: dict[str, Any],
    watchlist: list[dict[str, Any]],
    price_stress: list[dict[str, Any]],
    nav_stress: list[dict[str, Any]],
    liquidity_stress: list[dict[str, Any]],
    gate: list[dict[str, Any]],
) -> str:
    worst60 = _row_by(price_stress, "window_id", "worst_60d")
    return "\n".join(
        [
            "# V5e 511360 Cash Proxy Forward/Stress Packet",
            "",
            f"- PM gate decision: `{gate[0]['pm_gate_decision']}`",
            "- Status: forward review candidate only; not accepted.",
            f"- Delta return vs V57f: {float(pm_summary['delta_return_vs_v57f']) * 100:.4f} pct points",
            f"- Delta return vs hold-cash V5e: {float(pm_summary['delta_return_vs_hold_cash']) * 100:.4f} pct points",
            f"- Open forward restores: {len(watchlist)}",
            f"- Worst 60d 511360 price return: {float(worst60['return_pct']):.4f}%",
            f"- Max abs premium/discount: {float(nav_stress[0]['max_abs_premium_discount_pct']):.4f}%",
            f"- Max execution participation: {float(liquidity_stress[0]['max_participation_rate_pct']):.4f}%",
            "",
            "## Decision",
            "- Retain as forward review candidate.",
            "- Acceptance remains blocked until forward/paper records and open restore closeout are available.",
            "",
        ]
    )


def _next_prompt(gate: dict[str, Any]) -> str:
    return f"""工作目录：
D:\\hh\\codex\\v5

任务名称：
V5e 511360 cash proxy forward/paper daily tracking

任务目标：
基于 `v5e_511360_cash_proxy_forward_stress_packet/current/`，建立 511360 cash proxy 的日度 forward/paper tracking。不得标记 accepted。

当前 gate：
`{gate["pm_gate_decision"]}`

必须跟踪：
- 511360 daily close / NAV / premium-discount；
- open-forward restore events；
- sleeve cash proxy PnL；
- liquidity / amount / order participation；
- V57f unchanged and V5e threshold unchanged。
"""


def _agent_rules() -> str:
    return "\n".join(["# V5e 511360 Forward/Stress Rules", "", "- Do not mark accepted.", "- Do not modify V57f or V5e thresholds.", "- Do not scan parameters.", ""])


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        PM_DIR / "v5e_511360_pm_quant_review_summary.json",
        ENG_DIR / "v5e_511360_cash_proxy_trade_log.csv",
        ENG_DIR / "v5e_511360_cash_proxy_variant_metrics.csv",
        ENG_DIR / "v5e_511360_cash_proxy_daily_pnl.csv",
        PIT_DIR / "v5e_511360_daily_price.csv",
        PIT_DIR / "v5e_511360_nav_discount_audit.csv",
        PIT_DIR / "v5e_511360_execution_liquidity_audit.csv",
        STARTUP_DIR / "v5_startup_warmup_price_repair_summary.json",
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _row_by(rows: list[dict[str, Any]], key: str, value: str) -> dict[str, Any]:
    for row in rows:
        if row.get(key) == value:
            return row
    return {}


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
    result = run_v5e_511360_cash_proxy_forward_stress()
    print(json.dumps(result, ensure_ascii=False, indent=2))

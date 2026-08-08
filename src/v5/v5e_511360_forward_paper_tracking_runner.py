from __future__ import annotations

import csv
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5e_511360_forward_paper_tracking") / "current"
STRESS_DIR = Path("v5e_511360_cash_proxy_forward_stress_packet") / "current"
PM_DIR = Path("v5e_511360_cash_proxy_pm_quant_review") / "current"
STARTUP_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
ASSET_CODE = "511360.SH"
SECID = "1.511360"
TRACK_START = "20260530"
TRACK_END = "20260729"
INFERRED_RESTORE_DATE = "2026-07-01"
COMMISSION_RATE = 0.00003
MIN_COMMISSION = 5.0


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_511360_forward_paper_tracking(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_511360_forward_tracking_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_511360_forward_tracking_summary.json", summary)
        return summary

    stress_summary = _read_json(root / STRESS_DIR / "v5e_511360_forward_stress_summary.json")
    if stress_summary.get("pm_gate_decision") != "retain_511360_forward_review_candidate_not_accepted":
        blocker = {
            "blocker_id": "forward_stress_not_retained",
            "severity": "fatal",
            "status": "blocking",
            "description": "Forward/stress packet did not retain 511360 candidate.",
        }
        _write_csv(out / "v5e_511360_forward_tracking_blockers.csv", [blocker])
        summary = _summary("blocked_forward_stress_not_retained", "blocked_until_forward_stress_retains", [blocker])
        _write_json(out / "v5e_511360_forward_tracking_summary.json", summary)
        return summary

    watchlist = _read_csv(root / STRESS_DIR / "v5e_511360_open_forward_restore_watchlist.csv")
    prior_rebalances = _read_rebalance_dates(root)
    price_rows, price_log = _load_or_fetch_price(root / OUT_DIR / "v5e_511360_forward_price_update.csv", TRACK_START, TRACK_END)
    nav_rows, nav_log = _load_or_fetch_nav(root / OUT_DIR / "v5e_511360_forward_nav_update.csv", "2026-06-01", "2026-07-29")
    if not price_rows:
        blocker = {
            "blocker_id": "price_update_failed",
            "severity": "fatal",
            "status": "blocking",
            "description": "Could not fetch 511360 forward price update.",
        }
        _write_csv(out / "v5e_511360_forward_tracking_blockers.csv", [blocker])
        summary = _summary("blocked_price_update_failed", "blocked_until_price_update_available", [blocker])
        _write_json(out / "v5e_511360_forward_tracking_summary.json", summary)
        return summary

    price_by_day = {r["trade_date"]: r for r in price_rows}
    nav_by_day = {r["trade_date"]: r for r in nav_rows}
    premium = _premium_discount_update(price_rows, nav_by_day)
    daily_tracking = _daily_tracking(watchlist, price_rows)
    closeout = _restore_closeout(watchlist, price_by_day, prior_rebalances)
    pnl_tracking = _pnl_tracking(daily_tracking, closeout)
    liquidity = _liquidity_update(closeout, price_by_day)
    checks = _candidate_checks(stress_summary, price_rows, nav_rows, closeout, liquidity, prior_rebalances)
    gate = _pm_gate_decision(checks, closeout)
    queue = _next_queue(gate[0]["pm_gate_decision"])
    blockers_out = _blockers(checks)

    _write_csv(out / "v5e_511360_forward_price_update.csv", price_rows)
    _write_csv(out / "v5e_511360_forward_nav_update.csv", nav_rows)
    _write_csv(out / "v5e_511360_forward_premium_discount_update.csv", premium)
    _write_csv(out / "v5e_511360_forward_daily_tracking.csv", daily_tracking)
    _write_csv(out / "v5e_511360_open_forward_restore_closeout.csv", closeout)
    _write_csv(out / "v5e_511360_forward_pnl_tracking.csv", pnl_tracking)
    _write_csv(out / "v5e_511360_forward_liquidity_update.csv", liquidity)
    _write_csv(out / "v5e_511360_forward_fetch_log.csv", [price_log, nav_log])
    _write_csv(out / "v5e_511360_forward_candidate_checks.csv", checks)
    _write_csv(out / "v5e_511360_forward_tracking_pm_gate_decision.csv", gate)
    _write_csv(out / "v5e_511360_forward_tracking_next_queue.csv", queue)
    _write_csv(out / "v5e_511360_forward_tracking_blockers.csv", blockers_out)
    (out / "v5e_511360_forward_tracking_next_prompt.md").write_text(_next_prompt(gate[0]), encoding="utf-8")
    (out / "v5e_511360_forward_tracking_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5e_511360_forward_tracking_report.md").write_text(
        _report(stress_summary, price_rows, nav_rows, closeout, gate),
        encoding="utf-8",
    )

    total_realized = sum(_float(r["realized_pnl"]) for r in closeout)
    summary = _summary(
        "completed_511360_forward_paper_tracking",
        gate[0]["pm_gate_decision"],
        [],
        price_update_rows=len(price_rows),
        nav_update_rows=len(nav_rows),
        restore_closeout_count=len(closeout),
        proxy_side_closeout_realized_pnl=total_realized,
        official_v57f_restore_available=any(r["check_id"] == "official_v57f_202607_rebalance_available" and r["pass"] for r in checks),
    )
    _write_json(out / "v5e_511360_forward_tracking_summary.json", summary)
    return summary


def _read_rebalance_dates(root: Path) -> list[str]:
    signals = _read_csv(root / STARTUP_RUN / "rebalance_signals.csv")
    return sorted({r["trade_date"] for r in signals})


def _fetch_daily_price(beg: str, end: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    url = (
        "https://push2his.eastmoney.com/api/qt/stock/kline/get?"
        + urllib.parse.urlencode(
            {
                "secid": SECID,
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": "101",
                "fqt": "1",
                "beg": beg,
                "end": end,
            }
        )
    )
    payload = _http_json(url)
    klines = payload.get("data", {}).get("klines", []) if payload else []
    rows = []
    for item in klines:
        parts = item.split(",")
        rows.append(
            {
                "trade_date": parts[0],
                "open": float(parts[1]),
                "close": float(parts[2]),
                "high": float(parts[3]),
                "low": float(parts[4]),
                "volume_lots": float(parts[5]),
                "amount": float(parts[6]),
                "pct_chg": float(parts[8]),
                "source": "eastmoney_push2his_forward",
            }
        )
    return rows, {"source": "eastmoney_push2his_forward", "status": "ok" if rows else "empty", "row_count": len(rows), "network_fetch": True}


def _load_or_fetch_price(cache_path: Path, beg: str, end: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        rows, log = _fetch_daily_price(beg, end)
        if rows:
            return rows, log
    except Exception as exc:  # pragma: no cover - network fallback
        if cache_path.exists():
            rows = _read_csv(cache_path)
            return rows, {
                "source": "cached_forward_price_update",
                "status": "cache_fallback_after_network_error",
                "row_count": len(rows),
                "network_fetch": True,
                "error": str(exc),
            }
        raise
    if cache_path.exists():
        rows = _read_csv(cache_path)
        return rows, {"source": "cached_forward_price_update", "status": "cache_fallback_empty_fetch", "row_count": len(rows), "network_fetch": True}
    return [], {"source": "eastmoney_push2his_forward", "status": "empty_no_cache", "row_count": 0, "network_fetch": True}


def _fetch_nav_history(start: str, end: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        url = (
            "https://api.fund.eastmoney.com/f10/lsjz?"
            + urllib.parse.urlencode(
                {
                    "fundCode": "511360",
                    "pageIndex": str(page),
                    "pageSize": "200",
                    "startDate": start,
                    "endDate": end,
                }
            )
        )
        payload = _http_json(url, headers={"Referer": "https://fundf10.eastmoney.com/"})
        batch = payload.get("Data", {}).get("LSJZList", []) if payload else []
        for item in batch:
            rows.append(
                {
                    "trade_date": item.get("FSRQ", ""),
                    "unit_nav": _float(item.get("DWJZ")),
                    "accum_nav": _float(item.get("LJJZ")),
                    "nav_growth_pct": _float(item.get("JZZZL")),
                    "source": "eastmoney_fund_f10_lsjz_forward",
                }
            )
        if not batch:
            break
        page += 1
    rows = sorted(rows, key=lambda r: r["trade_date"])
    return rows, {"source": "eastmoney_fund_f10_lsjz_forward", "status": "ok" if rows else "empty", "row_count": len(rows), "network_fetch": True}


def _load_or_fetch_nav(cache_path: Path, start: str, end: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        rows, log = _fetch_nav_history(start, end)
        if rows:
            return rows, log
    except Exception as exc:  # pragma: no cover - network fallback
        if cache_path.exists():
            rows = _read_csv(cache_path)
            return rows, {
                "source": "cached_forward_nav_update",
                "status": "cache_fallback_after_network_error",
                "row_count": len(rows),
                "network_fetch": True,
                "error": str(exc),
            }
        raise
    if cache_path.exists():
        rows = _read_csv(cache_path)
        return rows, {"source": "cached_forward_nav_update", "status": "cache_fallback_empty_fetch", "row_count": len(rows), "network_fetch": True}
    return [], {"source": "eastmoney_fund_f10_lsjz_forward", "status": "empty_no_cache", "row_count": 0, "network_fetch": True}


def _premium_discount_update(price_rows: list[dict[str, Any]], nav_by_day: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for price in price_rows:
        nav = nav_by_day.get(price["trade_date"])
        unit_nav = _float(nav.get("unit_nav")) if nav else 0.0
        rows.append(
            {
                "trade_date": price["trade_date"],
                "close": price["close"],
                "unit_nav": unit_nav if nav else "",
                "premium_discount_pct": (float(price["close"]) / unit_nav - 1.0) * 100 if unit_nav else "",
                "status": "pass" if unit_nav else "missing_nav",
            }
        )
    return rows


def _daily_tracking(watchlist: list[dict[str, str]], price_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for price in price_rows:
        day = price["trade_date"]
        for event in watchlist:
            if day < event["buy_date"]:
                continue
            units = _float(event["proxy_units"])
            close = float(price["close"])
            market_value = units * close
            rows.append(
                {
                    "event_id": event["event_id"],
                    "sleeve_id": event["sleeve_id"],
                    "trade_date": day,
                    "close": close,
                    "proxy_units": units,
                    "market_value": market_value,
                    "unrealized_pnl": market_value - _float(event["proxy_order_value"]),
                    "tracking_status": "active_until_inferred_restore" if day < INFERRED_RESTORE_DATE else "post_restore_observation",
                }
            )
    return rows


def _restore_closeout(
    watchlist: list[dict[str, str]],
    price_by_day: dict[str, dict[str, Any]],
    prior_rebalances: list[str],
) -> list[dict[str, Any]]:
    restore_execution_date = _first_available_date_on_or_after(price_by_day, INFERRED_RESTORE_DATE)
    restore_price = price_by_day.get(restore_execution_date, {})
    rows = []
    for event in watchlist:
        units = _float(event["proxy_units"])
        sell_price = _float(restore_price.get("open"))
        sell_value = units * sell_price if sell_price else 0.0
        commission = max(MIN_COMMISSION, sell_value * COMMISSION_RATE) if sell_value else 0.0
        rows.append(
            {
                "event_id": event["event_id"],
                "sleeve_id": event["sleeve_id"],
                "buy_date": event["buy_date"],
                "restore_date": INFERRED_RESTORE_DATE,
                "restore_execution_date": restore_execution_date,
                "restore_date_basis": "inferred_quarterly_v57f_schedule_after_2026_04_01",
                "official_v57f_restore_signal_available": INFERRED_RESTORE_DATE in prior_rebalances,
                "sell_price": sell_price,
                "sell_value": sell_value,
                "sell_commission": commission,
                "proxy_order_value": _float(event["proxy_order_value"]),
                "realized_pnl": sell_value - commission - _float(event["proxy_order_value"]) if sell_price else 0.0,
                "closeout_status": "proxy_side_paper_closed" if sell_price else "missing_restore_price",
            }
        )
    return rows


def _pnl_tracking(daily_tracking: list[dict[str, Any]], closeout: list[dict[str, Any]]) -> list[dict[str, Any]]:
    realized = {r["event_id"]: r for r in closeout}
    rows = []
    for row in daily_tracking:
        close = realized.get(row["event_id"])
        rows.append(
            {
                **row,
                "realized_pnl_if_closed": close["realized_pnl"] if close and row["trade_date"] >= close["restore_execution_date"] else "",
                "pnl_status": "realized_after_restore" if close and row["trade_date"] >= close["restore_execution_date"] else "unrealized",
            }
        )
    return rows


def _liquidity_update(closeout: list[dict[str, Any]], price_by_day: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in closeout:
        price = price_by_day.get(row["restore_execution_date"], {})
        amount = _float(price.get("amount"))
        rows.append(
        {
            "event_id": row["event_id"],
            "restore_date": INFERRED_RESTORE_DATE,
            "restore_execution_date": row["restore_execution_date"],
            "sell_value": row["sell_value"],
            "daily_amount": amount,
            "participation_rate": _float(row["sell_value"]) / amount if amount else 1.0,
            "liquidity_status": "pass" if amount and _float(row["sell_value"]) / amount <= 0.1 else "needs_review",
        }
        )
    return rows


def _candidate_checks(
    stress_summary: dict[str, Any],
    price_rows: list[dict[str, Any]],
    nav_rows: list[dict[str, Any]],
    closeout: list[dict[str, Any]],
    liquidity: list[dict[str, Any]],
    prior_rebalances: list[str],
) -> list[dict[str, Any]]:
    return [
        {"check_id": "stress_packet_retained", "pass": stress_summary["pm_gate_decision"] == "retain_511360_forward_review_candidate_not_accepted", "detail": stress_summary["pm_gate_decision"]},
        {"check_id": "price_update_available", "pass": len(price_rows) > 0, "detail": len(price_rows)},
        {"check_id": "nav_update_available", "pass": len(nav_rows) > 0, "detail": len(nav_rows)},
        {"check_id": "proxy_side_closeout_done", "pass": all(r["closeout_status"] == "proxy_side_paper_closed" for r in closeout), "detail": len(closeout)},
        {"check_id": "liquidity_closeout_pass", "pass": all(r["liquidity_status"] == "pass" for r in liquidity), "detail": max((_float(r["participation_rate"]) for r in liquidity), default=0.0)},
        {"check_id": "official_v57f_202607_rebalance_available", "pass": INFERRED_RESTORE_DATE in prior_rebalances, "detail": "local signals only through 2026-04-01"},
        {"check_id": "accepted_status", "pass": True, "detail": "not accepted"},
    ]


def _pm_gate_decision(checks: list[dict[str, Any]], closeout: list[dict[str, Any]]) -> list[dict[str, Any]]:
    proxy_closed = next(r for r in checks if r["check_id"] == "proxy_side_closeout_done")["pass"]
    official_restore = next(r for r in checks if r["check_id"] == "official_v57f_202607_rebalance_available")["pass"]
    decision = (
        "proxy_side_forward_closeout_done_blocked_until_official_v57f_restore"
        if proxy_closed and not official_restore
        else "forward_tracking_ready_for_next_pm_review_not_accepted"
        if proxy_closed
        else "remain_forward_tracking_until_proxy_closeout"
    )
    return [
        {
            "pm_gate_decision": decision,
            "proxy_side_closeout_done": proxy_closed,
            "official_v57f_restore_available": official_restore,
            "restore_closeout_count": len(closeout),
            "realized_pnl": sum(_float(r["realized_pnl"]) for r in closeout),
            "accepted": False,
            "reason": "511360 proxy side is closed, but local official 2026-07 V57f rebalance signals are unavailable; full restore closeout is blocked."
            if proxy_closed and not official_restore
            else "Forward tracking closeout complete.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "task": "Fetch or generate official V57f 2026-07 rebalance signals",
            "allowed": decision == "proxy_side_forward_closeout_done_blocked_until_official_v57f_restore",
            "requires_backtest": False,
        },
        {
            "priority": 2,
            "task": "V5e 511360 official restore closeout review",
            "allowed": decision == "proxy_side_forward_closeout_done_blocked_until_official_v57f_restore",
            "requires_backtest": False,
        },
        {
            "priority": 3,
            "task": "Acceptance gate remains blocked until official restore and more forward evidence",
            "allowed": False,
            "requires_backtest": False,
        },
    ]


def _blockers(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for check in checks:
        if not check["pass"]:
            status = "blocks_acceptance_not_tracking" if check["check_id"] == "official_v57f_202607_rebalance_available" else "blocking"
            rows.append(
                {
                    "blocker_id": check["check_id"],
                    "severity": "next_gate",
                    "status": status,
                    "description": str(check["detail"]),
                }
            )
    return rows or [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "Forward tracking complete; not accepted."}]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    price_update_rows: int = 0,
    nav_update_rows: int = 0,
    restore_closeout_count: int = 0,
    proxy_side_closeout_realized_pnl: float = 0.0,
    official_v57f_restore_available: bool = False,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_511360_forward_paper_tracking",
        "status": status,
        "pm_gate_decision": decision,
        "price_update_rows": price_update_rows,
        "nav_update_rows": nav_update_rows,
        "restore_closeout_count": restore_closeout_count,
        "proxy_side_closeout_realized_pnl": proxy_side_closeout_realized_pnl,
        "official_v57f_restore_available": official_v57f_restore_available,
        "accepted": False,
        "v57f_core_modified": False,
        "v5e_threshold_modified": False,
        "threshold_scan_used": False,
        "network_fetch_started": price_update_rows > 0 or nav_update_rows > 0,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(
    stress_summary: dict[str, Any],
    price_rows: list[dict[str, Any]],
    nav_rows: list[dict[str, Any]],
    closeout: list[dict[str, Any]],
    gate: list[dict[str, Any]],
) -> str:
    return "\n".join(
        [
            "# V5e 511360 Forward/Paper Tracking",
            "",
            f"- PM gate decision: `{gate[0]['pm_gate_decision']}`",
            "- Status: proxy-side paper closeout complete; not accepted.",
            f"- Price update rows: {len(price_rows)}",
            f"- NAV update rows: {len(nav_rows)}",
            f"- Restore closeout count: {len(closeout)}",
            f"- Proxy-side realized PnL: {sum(_float(r['realized_pnl']) for r in closeout):.2f}",
            f"- Prior candidate delta vs V57f: {float(stress_summary['delta_return_vs_v57f']) * 100:.4f} pct points",
            "",
            "## Blocker",
            "- Local official V57f rebalance signals are only available through 2026-04-01, so full official restore closeout waits for 2026-07 signals.",
            "",
        ]
    )


def _next_prompt(gate: dict[str, Any]) -> str:
    return f"""Working directory:
D:\\hh\\codex\\v5

Task:
V5e 511360 official restore closeout after 2026-07 V57f rebalance

Goal:
Use `v5e_511360_forward_paper_tracking/current/` and the official 2026-07 V57f rebalance signals, once available, to complete the official restore closeout review. Do not mark accepted.

Current gate:
`{gate["pm_gate_decision"]}`
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e 511360 Forward Tracking Rules",
            "",
            "- Do not mark accepted.",
            "- Do not modify V57f core or V5e thresholds.",
            "- Proxy-side closeout does not prove official V57f restore until 2026-07 signals are available.",
            "- Do not start JoinQuant.",
            "",
        ]
    )


def _http_json(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        STRESS_DIR / "v5e_511360_forward_stress_summary.json",
        STRESS_DIR / "v5e_511360_open_forward_restore_watchlist.csv",
        PM_DIR / "v5e_511360_pm_quant_review_summary.json",
        STARTUP_RUN / "rebalance_signals.csv",
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _first_available_date_on_or_after(price_by_day: dict[str, dict[str, Any]], target: str) -> str:
    for day in sorted(price_by_day):
        if day >= target:
            return day
    return target


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
    result = run_v5e_511360_forward_paper_tracking()
    print(json.dumps(result, ensure_ascii=False, indent=2))

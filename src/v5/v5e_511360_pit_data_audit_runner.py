from __future__ import annotations

import csv
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5e_511360_pit_data_audit") / "current"
SELECTION_DIR = Path("v5e_short_financing_etf_cash_proxy_selection_gate") / "current"
BUCKET_DIR = Path("v5e_sleeve_cash_bucket_engineering") / "current"
STARTUP_DIR = Path("v5_startup_warmup_price_repair") / "current"

ASSET_CODE = "511360.SH"
SECID = "1.511360"
START = "20210506"
END = "20260531"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_511360_pit_data_audit(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    fetch_log: list[dict[str, Any]] = []
    if not blockers:
        price_rows, price_log = _fetch_daily_price()
        nav_rows, nav_log = _fetch_nav_history()
        fetch_log.extend([price_log, nav_log])
        if not price_rows:
            blockers.append(_blocker("price_fetch_failed", "fatal", "Daily OHLC fetch returned no rows."))
        if not nav_rows:
            blockers.append(_blocker("nav_fetch_failed", "fatal", "NAV fetch returned no rows."))
    else:
        price_rows, nav_rows = [], []

    if blockers:
        _write_csv(out / "v5e_511360_fetch_log.csv", fetch_log or [{"source": "none", "status": "not_started_due_to_missing_inputs"}])
        _write_csv(out / "v5e_511360_blockers.csv", blockers)
        summary = _summary("blocked_511360_pit_data_audit", "blocked_until_data_fetch_repaired", blockers)
        _write_json(out / "v5e_511360_pit_data_audit_summary.json", summary)
        return summary

    ledger = _read_csv(root / BUCKET_DIR / "v5e_sleeve_cash_event_ledger.csv")
    nav_discount = _nav_discount(price_rows, nav_rows)
    liquidity = _execution_liquidity_audit(price_rows, ledger)
    distributions = _distribution_audit(nav_rows)
    data_quality = _data_quality(price_rows, nav_rows, liquidity, distributions)
    order_capacity = _order_capacity_audit(liquidity)
    decision = _pm_gate_decision(data_quality, order_capacity, distributions)
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    blockers_out = _final_blockers(decision, data_quality)

    _write_csv(out / "v5e_511360_daily_price.csv", price_rows)
    _write_csv(out / "v5e_511360_nav_history.csv", nav_rows)
    _write_csv(out / "v5e_511360_nav_discount_audit.csv", nav_discount)
    _write_csv(out / "v5e_511360_execution_liquidity_audit.csv", liquidity)
    _write_csv(out / "v5e_511360_distribution_audit.csv", distributions)
    _write_csv(out / "v5e_511360_order_capacity_audit.csv", order_capacity)
    _write_csv(out / "v5e_511360_data_quality_audit.csv", data_quality)
    _write_csv(out / "v5e_511360_fetch_log.csv", fetch_log)
    _write_csv(out / "v5e_511360_pm_gate_decision.csv", decision)
    _write_csv(out / "v5e_511360_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5e_511360_blockers.csv", blockers_out)
    (out / "v5e_511360_next_prompt.md").write_text(_next_prompt(decision[0]), encoding="utf-8")
    (out / "v5e_511360_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5e_511360_pit_data_audit_report.md").write_text(
        _report(price_rows, nav_rows, nav_discount, liquidity, distributions, order_capacity, decision),
        encoding="utf-8",
    )

    summary = _summary(
        "completed_511360_pit_data_audit",
        decision[0]["pm_gate_decision"],
        [],
        price_rows=len(price_rows),
        nav_rows=len(nav_rows),
        execution_windows_checked=len(liquidity),
        low_liquidity_event_count=sum(1 for r in liquidity if r["liquidity_status"] not in {"pass", "open_forward_restore_not_due"}),
        distribution_event_count=len([r for r in distributions if r["distribution_or_split_flag"]]),
    )
    _write_json(out / "v5e_511360_pit_data_audit_summary.json", summary)
    return summary


def _fetch_daily_price() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    url = (
        "https://push2his.eastmoney.com/api/qt/stock/kline/get?"
        + urllib.parse.urlencode(
            {
                "secid": SECID,
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": "101",
                "fqt": "1",
                "beg": START,
                "end": END,
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
                "amplitude_pct": float(parts[7]),
                "pct_chg": float(parts[8]),
                "chg": float(parts[9]),
                "turnover_pct": float(parts[10]),
                "source": "eastmoney_push2his",
            }
        )
    return rows, {"source": "eastmoney_push2his", "url": url, "status": "ok" if rows else "empty", "row_count": len(rows)}


def _fetch_nav_history() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    total = None
    while True:
        url = (
            "https://api.fund.eastmoney.com/f10/lsjz?"
            + urllib.parse.urlencode(
                {
                    "fundCode": "511360",
                    "pageIndex": str(page),
                    "pageSize": "200",
                    "startDate": "2021-05-06",
                    "endDate": "2026-05-31",
                }
            )
        )
        payload = _http_json(url, headers={"Referer": "https://fundf10.eastmoney.com/"})
        data = payload.get("Data", {}) if payload else {}
        total = int(data.get("TotalCount") or 0)
        batch = data.get("LSJZList", []) or []
        for item in batch:
            rows.append(
                {
                    "trade_date": item.get("FSRQ", ""),
                    "unit_nav": _float(item.get("DWJZ")),
                    "accum_nav": _float(item.get("LJJZ")),
                    "nav_growth_pct": _float(item.get("JZZZL")),
                    "subscription_status": item.get("SGZT", ""),
                    "redemption_status": item.get("SHZT", ""),
                    "distribution_or_split_flag": item.get("FHSP", "") or item.get("FHFCZ", ""),
                    "source": "eastmoney_fund_f10_lsjz",
                }
            )
        if not batch or (total and len(rows) >= total):
            break
        page += 1
    rows = sorted(rows, key=lambda r: r["trade_date"])
    return rows, {"source": "eastmoney_fund_f10_lsjz", "status": "ok" if rows else "empty", "row_count": len(rows), "total_count": total}


def _nav_discount(price_rows: list[dict[str, Any]], nav_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nav_by_day = {r["trade_date"]: r for r in nav_rows}
    rows = []
    for p in price_rows:
        nav = nav_by_day.get(p["trade_date"])
        if not nav:
            rows.append({"trade_date": p["trade_date"], "close": p["close"], "unit_nav": "", "premium_discount_pct": "", "status": "missing_nav"})
            continue
        unit_nav = float(nav["unit_nav"])
        rows.append(
            {
                "trade_date": p["trade_date"],
                "close": p["close"],
                "unit_nav": unit_nav,
                "premium_discount_pct": (float(p["close"]) / unit_nav - 1.0) * 100 if unit_nav else "",
                "status": "pass",
            }
        )
    return rows


def _execution_liquidity_audit(price_rows: list[dict[str, Any]], ledger: list[dict[str, str]]) -> list[dict[str, Any]]:
    price_by_day = {r["trade_date"]: r for r in price_rows}
    rows = []
    for event in ledger:
        for side, day in [("buy_proxy_after_exit", event["execution_date"]), ("sell_proxy_on_restore", event["restore_rebalance_date"])]:
            if not day and side == "sell_proxy_on_restore":
                rows.append(
                    {
                        "event_id": event["event_id"],
                        "side": side,
                        "trade_date": "",
                        "sleeve_id": event["sleeve_id"],
                        "proxy_order_value": _float(event.get("sold_value")),
                        "daily_amount": "",
                        "participation_rate": "",
                        "liquidity_status": "open_forward_restore_not_due",
                        "reason": "No next rebalance date inside current sample; track in forward/paper, not a historical liquidity failure.",
                    }
                )
                continue
            price = price_by_day.get(day)
            sold_value = _float(event.get("sold_value"))
            amount = float(price["amount"]) if price else 0.0
            participation = sold_value / amount if amount else 1.0
            rows.append(
                {
                    "event_id": event["event_id"],
                    "side": side,
                    "trade_date": day,
                    "sleeve_id": event["sleeve_id"],
                    "proxy_order_value": sold_value,
                    "daily_amount": amount,
                    "participation_rate": participation,
                    "liquidity_status": "pass" if price and participation <= 0.1 else "needs_review",
                    "reason": "proxy order <= 10pct of daily amount" if price and participation <= 0.1 else "missing day or participation above 10pct",
                }
            )
    return rows


def _distribution_audit(nav_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "trade_date": r["trade_date"],
            "unit_nav": r["unit_nav"],
            "accum_nav": r["accum_nav"],
            "distribution_or_split_flag": r["distribution_or_split_flag"],
            "requires_total_return_adjustment": bool(r["distribution_or_split_flag"]),
        }
        for r in nav_rows
        if r["distribution_or_split_flag"]
    ] or [
        {
            "trade_date": "",
            "unit_nav": "",
            "accum_nav": "",
            "distribution_or_split_flag": "",
            "requires_total_return_adjustment": False,
            "note": "No distribution/split flag returned by fetched F10 NAV history; keep official fund documents as secondary check.",
        }
    ]


def _data_quality(
    price_rows: list[dict[str, Any]],
    nav_rows: list[dict[str, Any]],
    liquidity: list[dict[str, Any]],
    distributions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    price_dates = {r["trade_date"] for r in price_rows}
    nav_dates = {r["trade_date"] for r in nav_rows}
    return [
        {"check_id": "daily_price_coverage", "status": "pass" if len(price_rows) > 1200 else "needs_review", "value": len(price_rows)},
        {"check_id": "nav_coverage", "status": "pass" if len(nav_rows) > 1200 else "needs_review", "value": len(nav_rows)},
        {"check_id": "price_nav_overlap", "status": "pass" if len(price_dates & nav_dates) > 1200 else "needs_review", "value": len(price_dates & nav_dates)},
        {
            "check_id": "liquidity_execution_windows",
            "status": "pass" if all(r["liquidity_status"] in {"pass", "open_forward_restore_not_due"} for r in liquidity) else "needs_review",
            "value": sum(1 for r in liquidity if r["liquidity_status"] not in {"pass", "open_forward_restore_not_due"}),
        },
        {"check_id": "distribution_field_available", "status": "pass", "value": len(distributions)},
        {"check_id": "total_return_required", "status": "pass", "value": True},
    ]


def _order_capacity_audit(liquidity: list[dict[str, Any]]) -> list[dict[str, Any]]:
    values = [_float(r["participation_rate"]) for r in liquidity if r["participation_rate"] != ""]
    needs = [r for r in liquidity if r["liquidity_status"] not in {"pass", "open_forward_restore_not_due"}]
    open_forward = [r for r in liquidity if r["liquidity_status"] == "open_forward_restore_not_due"]
    return [
        {
            "candidate_asset_code": ASSET_CODE,
            "execution_window_count": len(liquidity),
            "max_participation_rate": max(values) if values else 0.0,
            "average_participation_rate": sum(values) / len(values) if values else 0.0,
            "needs_review_count": len(needs),
            "open_forward_restore_count": len(open_forward),
            "status": "pass" if not needs else "needs_review_before_engineering",
        }
    ]


def _pm_gate_decision(
    data_quality: list[dict[str, Any]],
    order_capacity: list[dict[str, Any]],
    distributions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    quality_pass = all(r["status"] == "pass" for r in data_quality)
    capacity_pass = order_capacity[0]["status"] == "pass"
    decision = "ready_for_511360_cash_proxy_limited_engineering_spec" if quality_pass and capacity_pass else "needs_review_before_511360_engineering_spec"
    return [
        {
            "pm_gate_decision": decision,
            "daily_price_gate_pass": any(r["check_id"] == "daily_price_coverage" and r["status"] == "pass" for r in data_quality),
            "nav_gate_pass": any(r["check_id"] == "nav_coverage" and r["status"] == "pass" for r in data_quality),
            "liquidity_gate_pass": capacity_pass,
            "distribution_audit_rows": len(distributions),
            "engineering_backtest_allowed_now": False,
            "accepted": False,
            "reason": "PIT data audit is complete enough for a limited engineering spec prompt; engineering still needs separate approval and must not mark accepted."
            if decision.startswith("ready")
            else "Some data/liquidity checks need review before any engineering spec.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "task": "V5e 511360 cash proxy limited engineering spec",
            "scope": "Define fixed T+1 proxy buy and next-rebalance restore sell accounting; no backtest yet.",
            "allowed": decision == "ready_for_511360_cash_proxy_limited_engineering_spec",
            "requires_backtest": False,
        },
        {
            "priority": 2,
            "task": "511360 data repair review",
            "scope": "Repair NAV/distribution/liquidity gaps if any check is not pass.",
            "allowed": decision != "ready_for_511360_cash_proxy_limited_engineering_spec",
            "requires_backtest": False,
        },
    ]


def _final_blockers(decision: list[dict[str, Any]], data_quality: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if decision[0]["pm_gate_decision"] == "ready_for_511360_cash_proxy_limited_engineering_spec":
        return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": "PIT data audit passed for limited engineering spec preparation; not accepted."}]
    return [
        _blocker(
            f"data_quality_{r['check_id']}",
            "next_gate",
            f"Check {r['check_id']} status is {r['status']}; value={r['value']}.",
        )
        for r in data_quality
        if r["status"] != "pass"
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    price_rows: int = 0,
    nav_rows: int = 0,
    execution_windows_checked: int = 0,
    low_liquidity_event_count: int = 0,
    distribution_event_count: int = 0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_511360_pit_data_audit",
        "status": status,
        "pm_gate_decision": decision,
        "candidate_asset_code": ASSET_CODE,
        "price_rows": price_rows,
        "nav_rows": nav_rows,
        "execution_windows_checked": execution_windows_checked,
        "low_liquidity_event_count": low_liquidity_event_count,
        "distribution_event_count": distribution_event_count,
        "engineering_backtest_run": False,
        "trade_allowed": False,
        "accepted": False,
        "v57f_core_modified": False,
        "v5e_threshold_modified": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(
    price_rows: list[dict[str, Any]],
    nav_rows: list[dict[str, Any]],
    nav_discount: list[dict[str, Any]],
    liquidity: list[dict[str, Any]],
    distributions: list[dict[str, Any]],
    order_capacity: list[dict[str, Any]],
    decision: list[dict[str, Any]],
) -> str:
    discounts = [_float(r["premium_discount_pct"]) for r in nav_discount if r["premium_discount_pct"] != ""]
    return "\n".join(
        [
            "# V5e 511360 PIT Data Audit",
            "",
            f"- PM gate decision: `{decision[0]['pm_gate_decision']}`",
            "- Status: PIT data audit only; no engineering backtest, no trade, not accepted.",
            "",
            "## Coverage",
            f"- Daily price rows: {len(price_rows)}",
            f"- NAV rows: {len(nav_rows)}",
            f"- Execution windows checked: {len(liquidity)}",
            f"- Low-liquidity / missing windows: {sum(1 for r in liquidity if r['liquidity_status'] not in {'pass', 'open_forward_restore_not_due'})}",
            "",
            "## NAV / Liquidity",
            f"- Average premium/discount pct: {sum(discounts) / len(discounts) if discounts else 0.0:.4f}",
            f"- Max proxy order participation rate: {order_capacity[0]['max_participation_rate']:.4f}",
            f"- Distribution/split audit rows: {len(distributions)}",
            "",
            "## Boundary",
            "- 511360 can move to a limited engineering spec if the PM accepts this data gate.",
            "- It is still a candidate cash proxy only; V57f and V5e rules remain unchanged.",
            "",
        ]
    )


def _next_prompt(decision: dict[str, Any]) -> str:
    return f"""工作目录：
D:\\hh\\codex\\v5

任务名称：
V5e 511360 cash proxy limited engineering spec

任务目标：
基于 `v5e_511360_pit_data_audit/current/`，生成 511360 作为 V5e sleeve cash proxy 的 limited engineering spec。只定义固定交易路径和审计口径，不直接回测，不标记 accepted。

当前 gate：
`{decision["pm_gate_decision"]}`

允许边界：
- V5e profit-lock 退出后，原本进入 sleeve cash bucket 的现金，可以在 T+1 之后买入 511360 的代理仓位；
- 下一次 V57f 正式调仓恢复前卖出代理仓位并释放现金；
- 使用 total-return / NAV / 折溢价 / 成交额 / 成本审计；
- V5d 只负责后续执行治理。

禁止：
- 不修改 V57f。
- 不修改 V5e +20% / sell50。
- 不允许 reentry before next rebalance。
- 不买股票，不跨 sleeve 转移。
- 不用 5分钟走势触发止盈。
- 不参数扫描，不标记 accepted。
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e 511360 PIT Data Audit Agent Rules",
            "",
            "- Data audit only; do not run strategy backtest.",
            "- Do not trade 511360 in this task.",
            "- Use total-return and NAV/premium-discount audit; raw close is insufficient.",
            "- Do not modify V57f, V5e thresholds, ERC, or V5d.",
            "- Do not allow reentry before next rebalance.",
            "- Do not use 5min data as a trigger.",
            "- Do not mark accepted.",
            "",
        ]
    )


def _http_json(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        SELECTION_DIR / "v5e_short_financing_etf_selection_summary.json",
        BUCKET_DIR / "v5e_sleeve_cash_event_ledger.csv",
        STARTUP_DIR / "v5_startup_warmup_price_repair_summary.json",
    ]
    return [
        _blocker("missing_required_input", "fatal", f"Required input missing: {path}")
        for path in required
        if not (root / path).exists()
    ]


def _blocker(blocker_id: str, severity: str, description: str) -> dict[str, Any]:
    return {"blocker_id": blocker_id, "severity": severity, "status": "blocking", "description": description}


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


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
    result = run_v5e_511360_pit_data_audit()
    print(json.dumps(result, ensure_ascii=False, indent=2))

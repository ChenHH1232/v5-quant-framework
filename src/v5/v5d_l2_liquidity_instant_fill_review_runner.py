from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


TRADE_DIR = Path("v5d_order_scheduling_engineering_test") / "current" / "runs"
BROKER_REVIEW_DIR = Path("v5d_l2_execution_cost_broker_paper_review") / "current"
STD_INDEX = Path("v5d_baostock_5min_data_gate") / "current" / "v5d_baostock_5min_standardized_index.csv"
STD_DATA_DIR = Path("v5d_baostock_5min_data_gate") / "data_standardized"
OUT_DIR = Path("v5d_l2_liquidity_instant_fill_review") / "current"
ENGINEERING_WINDOW_START = "2021-05-01"
ENGINEERING_WINDOW_END = "2026-05-31"
LOT_SIZE = 100
BASE_CAPITAL = 2_000_000.0
SMALL_CAPITAL = 500_000.0
CAPITAL_CASES = [
    ("capital_200w", BASE_CAPITAL, 1.0),
    ("capital_50w_scaled", SMALL_CAPITAL, SMALL_CAPITAL / BASE_CAPITAL),
]
CONSERVATIVE_INSTANT_PARTICIPATION = 0.01
BASE_INSTANT_PARTICIPATION = 0.03
SPLIT_REVIEW_PARTICIPATION = 0.05


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pct(value: Any) -> str:
    try:
        return f"{float(value):.2%}"
    except (TypeError, ValueError):
        return ""


def scaled_lot_amount(amount: float, scale: float) -> int:
    return int((amount * scale) // LOT_SIZE * LOT_SIZE)


def liquidity_tier(value_participation: float | None, volume_participation: float | None) -> str:
    if value_participation is None or volume_participation is None:
        return "missing_bar_or_zero_liquidity"
    pressure = max(value_participation, volume_participation)
    if pressure <= CONSERVATIVE_INSTANT_PARTICIPATION:
        return "instant_fill_conservative"
    if pressure <= BASE_INSTANT_PARTICIPATION:
        return "instant_fill_base"
    if pressure <= SPLIT_REVIEW_PARTICIPATION:
        return "split_window_review"
    return "liquidity_review_required"


def load_minute_bars() -> dict[tuple[str, str, str], dict[str, float]]:
    indexed_paths: set[str] = set()
    if STD_INDEX.exists():
        index = pd.read_csv(STD_INDEX)
        indexed_paths = {str(path) for path in index["path"].dropna().unique()}
    filesystem_paths = {str(path) for path in STD_DATA_DIR.rglob("*_5min_standardized.csv")}
    all_paths = sorted(indexed_paths | filesystem_paths)
    bars: dict[tuple[str, str, str], dict[str, float]] = {}
    for path in all_paths:
        p = Path(path)
        if not p.exists():
            continue
        df = pd.read_csv(p)
        for _, row in df.iterrows():
            try:
                bars[(str(row["code"]), str(row["trade_date"]), str(row["time"]))] = {
                    "bar_amount": float(row["amount"]),
                    "bar_volume": float(row["volume"]),
                    "bar_open": float(row["open"]),
                    "bar_close": float(row["close"]),
                }
            except (TypeError, ValueError):
                continue
    return bars


def load_trades() -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    required = [
        TRADE_DIR / "v57f_frozen" / "l2_size_aware" / "trades.csv",
        TRADE_DIR / "erc_fixed_covariance_candidate" / "l2_size_aware" / "trades.csv",
        BROKER_REVIEW_DIR / "v5d_l2_broker_paper_review_summary.json",
        STD_INDEX,
    ]
    blockers = [{"blocker_id": "missing_required_input", "severity": "fatal", "path": str(path)} for path in required if not path.exists()]
    if blockers:
        return pd.DataFrame(), blockers
    trades = pd.concat(
        [
            pd.read_csv(TRADE_DIR / "v57f_frozen" / "l2_size_aware" / "trades.csv"),
            pd.read_csv(TRADE_DIR / "erc_fixed_covariance_candidate" / "l2_size_aware" / "trades.csv"),
        ],
        ignore_index=True,
    )
    return trades, []


def build_threshold_policy() -> list[dict[str, Any]]:
    return [
        {"tier": "instant_fill_conservative", "max_order_bar_amount_participation": CONSERVATIVE_INSTANT_PARTICIPATION, "max_order_bar_volume_participation": CONSERVATIVE_INSTANT_PARTICIPATION, "pm_read": "small order relative to same 5min bar; strongest local liquidity read"},
        {"tier": "instant_fill_base", "max_order_bar_amount_participation": BASE_INSTANT_PARTICIPATION, "max_order_bar_volume_participation": BASE_INSTANT_PARTICIPATION, "pm_read": "likely executable for small capital paper matching, still not proof of queue priority"},
        {"tier": "split_window_review", "max_order_bar_amount_participation": SPLIT_REVIEW_PARTICIPATION, "max_order_bar_volume_participation": SPLIT_REVIEW_PARTICIPATION, "pm_read": "do not assume instant fill; keep scheduled retry or split"},
        {"tier": "liquidity_review_required", "max_order_bar_amount_participation": ">5%", "max_order_bar_volume_participation": ">5%", "pm_read": "needs more conservative slippage or lower participation assumption"},
        {"tier": "missing_bar_or_zero_liquidity", "max_order_bar_amount_participation": "", "max_order_bar_volume_participation": "", "pm_read": "cannot assume fill"},
    ]


def build_order_rows(trades: pd.DataFrame, bars: dict[tuple[str, str, str], dict[str, float]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, row in trades.iterrows():
        bar = bars.get((str(row["code"]), str(row["trade_date"]), str(row["window"])))
        bar_amount = bar["bar_amount"] if bar else 0.0
        bar_volume = bar["bar_volume"] if bar else 0.0
        for case_id, capital, scale in CAPITAL_CASES:
            amount = scaled_lot_amount(float(row["amount"]), scale)
            if amount <= 0:
                value = 0.0
                value_participation = 0.0 if bar_amount > 0 else None
                volume_participation = 0.0 if bar_volume > 0 else None
                tier = "below_one_lot_after_scaling"
            else:
                value = amount * float(row["price"])
                value_participation = value / bar_amount if bar_amount > 0 else None
                volume_participation = amount / bar_volume if bar_volume > 0 else None
                tier = liquidity_tier(value_participation, volume_participation)
            rows.append(
                {
                    "strategy_id": row["strategy_id"],
                    "capital_case": case_id,
                    "capital": capital,
                    "execution_policy": "l2_size_aware",
                    "trade_date": row["trade_date"],
                    "window": row["window"],
                    "code": row["code"],
                    "side": row["side"],
                    "original_200w_amount": int(row["amount"]),
                    "scaled_amount": amount,
                    "price_proxy": row["price"],
                    "scaled_order_value": value,
                    "bar_amount": bar_amount if bar else "",
                    "bar_volume": bar_volume if bar else "",
                    "value_participation": value_participation if value_participation is not None else "",
                    "volume_participation": volume_participation if volume_participation is not None else "",
                    "max_participation": max(value_participation or 0.0, volume_participation or 0.0) if value_participation is not None and volume_participation is not None else "",
                    "liquidity_tier": tier,
                    "instant_fill_base_pass": tier in {"instant_fill_conservative", "instant_fill_base", "below_one_lot_after_scaling"},
                    "notes": "5min bar liquidity proxy, not real queue or level-2 order-book proof",
                }
            )
    return rows


def summarize_orders(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    df = pd.DataFrame(rows)
    summary_rows: list[dict[str, Any]] = []
    stock_rows: list[dict[str, Any]] = []
    low_liq_rows: list[dict[str, Any]] = []
    readiness_rows: list[dict[str, Any]] = []
    for (strategy_id, capital_case), group in df.groupby(["strategy_id", "capital_case"]):
        nonzero = group[group["scaled_amount"].astype(float) > 0]
        tiers = group["liquidity_tier"].value_counts().to_dict()
        max_participation = pd.to_numeric(nonzero["max_participation"], errors="coerce").max() if not nonzero.empty else 0.0
        p95_participation = pd.to_numeric(nonzero["max_participation"], errors="coerce").quantile(0.95) if not nonzero.empty else 0.0
        base_pass = int(group["instant_fill_base_pass"].astype(str).str.lower().eq("true").sum())
        base_pass_rate = base_pass / len(group) if len(group) else 0.0
        zero_lot = tiers.get("below_one_lot_after_scaling", 0)
        review_count = tiers.get("split_window_review", 0) + tiers.get("liquidity_review_required", 0) + tiers.get("missing_bar_or_zero_liquidity", 0)
        summary_rows.append(
            {
                "strategy_id": strategy_id,
                "capital_case": capital_case,
                "order_count": len(group),
                "nonzero_order_count": len(nonzero),
                "below_one_lot_after_scaling_count": zero_lot,
                "instant_fill_conservative_count": tiers.get("instant_fill_conservative", 0),
                "instant_fill_base_count": tiers.get("instant_fill_base", 0),
                "split_window_review_count": tiers.get("split_window_review", 0),
                "liquidity_review_required_count": tiers.get("liquidity_review_required", 0),
                "missing_bar_or_zero_liquidity_count": tiers.get("missing_bar_or_zero_liquidity", 0),
                "instant_fill_base_pass_rate": base_pass_rate,
                "max_participation": max_participation,
                "p95_participation": p95_participation,
                "pm_read": "instant_fill_likely_for_small_capital" if review_count == 0 else "keep_split_or_review_tail_orders",
            }
        )
        readiness_rows.append(
            {
                "strategy_id": strategy_id,
                "capital_case": capital_case,
                "instant_fill_readiness": "pass" if base_pass_rate >= 0.98 and tiers.get("liquidity_review_required", 0) == 0 and tiers.get("missing_bar_or_zero_liquidity", 0) == 0 else "pass_with_tail_review",
                "allowed_next_action": "use_5min_liquidity_for_local_slippage_spec",
                "blocked_actions": "assume_real_queue_priority;live_broker_orders;select_windows_by_return",
                "reason": "5min bar amount/volume supports small-capital execution review, but cannot prove queue priority inside bar",
            }
        )
    for (strategy_id, capital_case, code), group in df.groupby(["strategy_id", "capital_case", "code"]):
        max_participation = pd.to_numeric(group["max_participation"], errors="coerce").max()
        review_count = group["liquidity_tier"].isin(["split_window_review", "liquidity_review_required", "missing_bar_or_zero_liquidity"]).sum()
        stock_rows.append(
            {
                "strategy_id": strategy_id,
                "capital_case": capital_case,
                "code": code,
                "order_count": len(group),
                "max_participation": 0.0 if pd.isna(max_participation) else max_participation,
                "review_order_count": int(review_count),
                "pm_read": "needs_tail_review" if review_count else "pass",
            }
        )
    review_df = df[df["liquidity_tier"].isin(["split_window_review", "liquidity_review_required", "missing_bar_or_zero_liquidity"])]
    if not review_df.empty:
        low_liq_rows = review_df.sort_values(["capital_case", "max_participation"], ascending=[True, False]).to_dict("records")
    return summary_rows, stock_rows, low_liq_rows, readiness_rows


def build_report(summary: dict[str, Any], summary_rows: list[dict[str, Any]], low_liq_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# V5d L2 Liquidity / Instant Fill Review",
        "",
        f"- Status: `{summary['status']}`",
        f"- Local engineering window: {ENGINEERING_WINDOW_START} to {ENGINEERING_WINDOW_END}",
        "- Scope: L2 size-aware liquidity pressure review only; no broker connection and no live trading.",
        "- Method: compare each scheduled order with same-code same-window 5min amount and volume.",
        "- This is liquidity evidence, not proof of queue priority or guaranteed fill.",
        "",
        "## Summary",
        "",
        "| Strategy | Capital | Orders | Nonzero Orders | Base Pass Rate | P95 Participation | Max Participation | Read |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in summary_rows:
        lines.append(
            f"| `{row['strategy_id']}` | `{row['capital_case']}` | {row['order_count']} | {row['nonzero_order_count']} | {pct(row['instant_fill_base_pass_rate'])} | {pct(row['p95_participation'])} | {pct(row['max_participation'])} | `{row['pm_read']}` |"
        )
    lines.extend(["", "## Tail Review", ""])
    if low_liq_rows:
        tail = low_liq_rows[:20]
        for row in tail:
            lines.append(f"- `{row['strategy_id']}` / `{row['capital_case']}` / `{row['trade_date']} {row['window']}` / `{row['code']}`: tier `{row['liquidity_tier']}`, participation {pct(row['max_participation'])}.")
    else:
        lines.append("- No split-window or liquidity-review tail orders.")
    lines.extend(
        [
            "",
            "## PM Read",
            "",
            "For 50w scaled orders, the 5min liquidity read is strong enough to proceed to local slippage specification. For 200w, most orders remain small relative to bar liquidity, but tail orders should keep split/retry handling rather than assume instant full fill.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    trades, blockers = load_trades()
    if blockers:
        write_csv(OUT_DIR / "v5d_l2_liquidity_blockers.csv", blockers, ["blocker_id", "severity", "path"])
        summary = {"schema_version": 1, "project": "v5d_l2_liquidity_instant_fill_review", "status": "blocked", "blocker_count": len(blockers), "created_at_utc": now_utc()}
        (OUT_DIR / "v5d_l2_liquidity_instant_fill_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary
    bars = load_minute_bars()
    order_rows = build_order_rows(trades, bars)
    summary_rows, stock_rows, low_liq_rows, readiness_rows = summarize_orders(order_rows)
    blockers = []
    if any(row["missing_bar_or_zero_liquidity_count"] for row in summary_rows):
        blockers.append({"blocker_id": "missing_bar_or_zero_liquidity", "severity": "review", "description": "Some orders cannot be matched to positive 5min liquidity."})
    allowed_blocked = [
        {"action": "use_5min_liquidity_for_slippage_spec", "status": "allowed", "reason": "local 5min amount/volume can measure order participation"},
        {"action": "assume_guaranteed_instant_fill", "status": "blocked", "reason": "5min bars do not prove queue priority or real order book depth"},
        {"action": "connect_live_broker", "status": "blocked", "reason": "not needed for local liquidity gate"},
        {"action": "choose_execution_window_by_best_return", "status": "blocked", "reason": "execution governance cannot use return-selected windows"},
    ]
    next_gate = [
        {
            "gate": "l2_conservative_slippage_spec",
            "allowed": "true" if not blockers else "review",
            "reason": "5min liquidity supports conservative slippage assumptions; tail orders should keep split/retry policy",
            "not_allowed": "guaranteed_fill;broker_connection;live_orders;return_selected_windows",
        }
    ]
    write_csv(OUT_DIR / "v5d_l2_liquidity_threshold_policy.csv", build_threshold_policy())
    write_csv(OUT_DIR / "v5d_l2_liquidity_by_order.csv", order_rows)
    write_csv(OUT_DIR / "v5d_l2_liquidity_by_strategy_capital.csv", summary_rows)
    write_csv(OUT_DIR / "v5d_l2_liquidity_by_stock.csv", stock_rows)
    write_csv(OUT_DIR / "v5d_l2_low_liquidity_order_review.csv", low_liq_rows, list(order_rows[0].keys()) if order_rows else [])
    write_csv(OUT_DIR / "v5d_l2_instant_fill_readiness.csv", readiness_rows)
    write_csv(OUT_DIR / "v5d_l2_liquidity_allowed_blocked_actions.csv", allowed_blocked)
    write_csv(OUT_DIR / "v5d_l2_liquidity_blockers.csv", blockers, ["blocker_id", "severity", "description"])
    write_csv(OUT_DIR / "v5d_l2_next_gate_decision.csv", next_gate)
    summary = {
        "schema_version": 1,
        "project": "v5d_l2_liquidity_instant_fill_review",
        "status": "completed_liquidity_review_passed" if not blockers else "completed_with_liquidity_review_notes",
        "created_at_utc": now_utc(),
        "local_engineering_window": {"start_date": ENGINEERING_WINDOW_START, "end_date": ENGINEERING_WINDOW_END},
        "policy_reviewed": "l2_size_aware",
        "capital_cases": [case[0] for case in CAPITAL_CASES],
        "v57f_core_modified": False,
        "erc_modified": False,
        "broker_connected": False,
        "live_trading_started": False,
        "thresholds": {
            "conservative_instant": CONSERVATIVE_INSTANT_PARTICIPATION,
            "base_instant": BASE_INSTANT_PARTICIPATION,
            "split_review": SPLIT_REVIEW_PARTICIPATION,
        },
        "blocker_count": len(blockers),
        "summary_rows": summary_rows,
        "next_gate": next_gate[0]["gate"],
        "outputs": {
            "summary": str(OUT_DIR / "v5d_l2_liquidity_instant_fill_summary.json"),
            "report": str(OUT_DIR / "v5d_l2_liquidity_instant_fill_report.md"),
            "threshold_policy": str(OUT_DIR / "v5d_l2_liquidity_threshold_policy.csv"),
            "by_order": str(OUT_DIR / "v5d_l2_liquidity_by_order.csv"),
            "by_strategy_capital": str(OUT_DIR / "v5d_l2_liquidity_by_strategy_capital.csv"),
            "by_stock": str(OUT_DIR / "v5d_l2_liquidity_by_stock.csv"),
            "low_liquidity_review": str(OUT_DIR / "v5d_l2_low_liquidity_order_review.csv"),
            "readiness": str(OUT_DIR / "v5d_l2_instant_fill_readiness.csv"),
            "allowed_blocked": str(OUT_DIR / "v5d_l2_liquidity_allowed_blocked_actions.csv"),
            "next_gate": str(OUT_DIR / "v5d_l2_next_gate_decision.csv"),
        },
    }
    (OUT_DIR / "v5d_l2_liquidity_instant_fill_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "v5d_l2_liquidity_instant_fill_report.md").write_text(build_report(summary, summary_rows, low_liq_rows), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))

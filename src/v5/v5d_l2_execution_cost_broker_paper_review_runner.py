from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


IN_DIR = Path("v5d_order_scheduling_engineering_test") / "current"
PM_DIR = Path("v5d_l2_order_scheduling_pm_quant_review") / "current"
OUT_DIR = Path("v5d_l2_execution_cost_broker_paper_review") / "current"
ENGINEERING_WINDOW_START = "2021-05-01"
ENGINEERING_WINDOW_END = "2026-05-31"
BROKER_COMMISSION_RATE = 0.000095
PREVIOUS_ENGINEERING_COMMISSION_RATE = 0.0003
MIN_COMMISSION = 5.0
LOT_SIZE = 100
MAX_ORDER_SUBMISSIONS_PER_SECOND = 15


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


def commission(value: float, rate: float) -> float:
    return max(value * rate, MIN_COMMISSION) if value > 0 else 0.0


def pct(value: Any) -> str:
    try:
        return f"{float(value):.2%}"
    except (TypeError, ValueError):
        return ""


def time_with_second(window: str, second_offset: int) -> str:
    hh, mm, ss = [int(x) for x in window.split(":")]
    ss += second_offset
    mm += ss // 60
    ss %= 60
    hh += mm // 60
    mm %= 60
    return f"{hh:02d}:{mm:02d}:{ss:02d}"


def load_required() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], list[dict[str, Any]]]:
    required = [
        IN_DIR / "v5d_l2_engineering_comparison.csv",
        PM_DIR / "v5d_l2_pm_quant_review_summary.json",
        IN_DIR / "runs" / "v57f_frozen" / "l2_size_aware" / "trades.csv",
        IN_DIR / "runs" / "erc_fixed_covariance_candidate" / "l2_size_aware" / "trades.csv",
    ]
    blockers = [{"blocker_id": "missing_required_input", "severity": "fatal", "path": str(path)} for path in required if not path.exists()]
    if blockers:
        return pd.DataFrame(), pd.DataFrame(), {}, blockers
    comparison = pd.read_csv(IN_DIR / "v5d_l2_engineering_comparison.csv")
    trades = pd.concat(
        [
            pd.read_csv(IN_DIR / "runs" / "v57f_frozen" / "l2_size_aware" / "trades.csv"),
            pd.read_csv(IN_DIR / "runs" / "erc_fixed_covariance_candidate" / "l2_size_aware" / "trades.csv"),
        ],
        ignore_index=True,
    )
    return comparison, trades, read_json(PM_DIR / "v5d_l2_pm_quant_review_summary.json"), []


def build_constraint_specs() -> list[dict[str, Any]]:
    return [
        {"constraint_id": "lot_size", "constraint_value": LOT_SIZE, "unit": "shares", "paper_rule": "all equity orders must be integer board lots of 100 shares", "status": "implemented_check"},
        {"constraint_id": "commission_rate", "constraint_value": BROKER_COMMISSION_RATE, "unit": "notional", "paper_rule": "use conservative broker commission rate of 0.95 bps, i.e. 0.000095", "status": "implemented_cost_restatement"},
        {"constraint_id": "minimum_commission", "constraint_value": MIN_COMMISSION, "unit": "CNY/order", "paper_rule": "if calculated commission is below 5 CNY, charge 5 CNY", "status": "implemented_cost_restatement"},
        {"constraint_id": "settlement", "constraint_value": "T+1", "unit": "A-share equity", "paper_rule": "same-day bought shares are not available for same-day sale; L2 must keep zero same-day buy/sell violations", "status": "implemented_validation"},
        {"constraint_id": "max_order_submission_rate", "constraint_value": MAX_ORDER_SUBMISSIONS_PER_SECOND, "unit": "orders/second", "paper_rule": "stagger orders inside each fixed L2 window so submissions do not exceed 15 per second", "status": "implemented_schedule_check"},
        {"constraint_id": "cancel_policy", "constraint_value": "no_cancel_except_failed_buy_handling", "unit": "governance", "paper_rule": "avoid discretionary cancel/repost behavior; unfilled orders are logged, and failed buys may be retried only through pre-registered later windows", "status": "implemented_policy_spec"},
    ]


def build_cost_rows(comparison: pd.DataFrame, trades: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    size_comp = comparison[comparison["execution_policy"] == "l2_size_aware"]
    for strategy_id, group in trades.groupby("strategy_id"):
        total_value = float(group["value"].sum())
        previous_commission = float(group["commission"].sum())
        broker_commissions = [commission(float(v), BROKER_COMMISSION_RATE) for v in group["value"]]
        broker_commission = sum(broker_commissions)
        min_fee_count = sum(1 for c in broker_commissions if abs(c - MIN_COMMISSION) < 1e-9)
        row = size_comp[size_comp["strategy_id"] == strategy_id]
        strategy_return = float(row["strategy_return"].iloc[0]) if not row.empty else 0.0
        rows.append(
            {
                "strategy_id": strategy_id,
                "execution_policy": "l2_size_aware",
                "trade_count": len(group),
                "total_traded_value": total_value,
                "previous_engineering_commission_rate": PREVIOUS_ENGINEERING_COMMISSION_RATE,
                "previous_engineering_commission": previous_commission,
                "broker_review_commission_rate": BROKER_COMMISSION_RATE,
                "broker_review_commission": broker_commission,
                "commission_saving_vs_previous_engineering": previous_commission - broker_commission,
                "minimum_commission_order_count": min_fee_count,
                "minimum_commission_order_pct": min_fee_count / len(group) if len(group) else 0.0,
                "gross_commission_bps_on_traded_value": broker_commission / total_value if total_value > 0 else 0.0,
                "strategy_return_l2_size_aware_from_engineering": strategy_return,
                "rough_return_saving_vs_previous_engineering_on_2m_capital": (previous_commission - broker_commission) / 2_000_000.0,
                "pm_read": "existing_l2_engineering_cost_was_more_conservative_than_broker_review_rate",
            }
        )
    return rows


def build_order_rate_schedule(trades: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    breaches: list[dict[str, Any]] = []
    sort_cols = ["strategy_id", "trade_date", "window", "side", "code"]
    ordered = trades.sort_values(sort_cols).copy()
    for (strategy_id, trade_date, window), group in ordered.groupby(["strategy_id", "trade_date", "window"], sort=False):
        for idx, (_, trade) in enumerate(group.iterrows()):
            second_offset = idx // MAX_ORDER_SUBMISSIONS_PER_SECOND
            submit_second = time_with_second(str(window), second_offset)
            rows.append(
                {
                    "strategy_id": strategy_id,
                    "execution_policy": "l2_size_aware",
                    "trade_date": trade_date,
                    "window": window,
                    "submit_time": submit_second,
                    "sequence_in_window": idx + 1,
                    "code": trade["code"],
                    "side": trade["side"],
                    "amount": trade["amount"],
                    "price_proxy": trade["price"],
                    "value": trade["value"],
                    "order_rate_limit": MAX_ORDER_SUBMISSIONS_PER_SECOND,
                }
            )
    schedule_df = pd.DataFrame(rows)
    if not schedule_df.empty:
        burst = schedule_df.groupby(["strategy_id", "trade_date", "submit_time"]).size().reset_index(name="orders_this_second")
        for _, row in burst[burst["orders_this_second"] > MAX_ORDER_SUBMISSIONS_PER_SECOND].iterrows():
            breaches.append(
                {
                    "strategy_id": row["strategy_id"],
                    "trade_date": row["trade_date"],
                    "submit_time": row["submit_time"],
                    "orders_this_second": int(row["orders_this_second"]),
                    "limit": MAX_ORDER_SUBMISSIONS_PER_SECOND,
                    "severity": "fatal",
                }
            )
    return rows, breaches


def build_validations(trades: pd.DataFrame, rate_breaches: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    lot_bad = trades[(trades["amount"].astype(float) % LOT_SIZE) != 0]
    same_day_side = trades.groupby(["strategy_id", "trade_date", "code"])["side"].agg(lambda x: set(x)).reset_index()
    t_bad = same_day_side[same_day_side["side"].apply(lambda s: "buy" in s and "sell" in s)]
    t_rows = [
        {
            "strategy_id": row["strategy_id"],
            "trade_date": row["trade_date"],
            "code": row["code"],
            "violation": "same_day_buy_and_sell",
            "severity": "fatal",
        }
        for _, row in t_bad.iterrows()
    ]
    lot_rows = [
        {
            "strategy_id": row["strategy_id"],
            "trade_date": row["trade_date"],
            "code": row["code"],
            "amount": row["amount"],
            "violation": "not_board_lot_100",
            "severity": "fatal",
        }
        for _, row in lot_bad.iterrows()
    ]
    cancel_rows = [
        {"policy_item": "discretionary_cancel_repost", "status": "blocked", "reason": "cancel count governance; avoid noisy false order signals"},
        {"policy_item": "pre_registered_failed_buy_retry", "status": "allowed", "reason": "buy orders that cannot fill may retry in later pre-registered windows, then stop and log"},
        {"policy_item": "sell_cancel_for_timing", "status": "blocked", "reason": "selling is not delayed or canceled for timing views"},
        {"policy_item": "stop_at_close_and_log_unfilled", "status": "required", "reason": "no forced fills or fabricated executions"},
    ]
    return t_rows, lot_rows + rate_breaches, cancel_rows


def build_broker_matching_template(trades: pd.DataFrame) -> list[dict[str, Any]]:
    template_rows: list[dict[str, Any]] = []
    sample = trades.sort_values(["strategy_id", "trade_date", "window", "code"]).head(50)
    for i, (_, row) in enumerate(sample.iterrows(), start=1):
        template_rows.append(
            {
                "paper_order_id": f"PAPER-{i:05d}",
                "strategy_id": row["strategy_id"],
                "execution_policy": "l2_size_aware",
                "trade_date": row["trade_date"],
                "planned_window": row["window"],
                "submit_time": "",
                "code": row["code"],
                "side": row["side"],
                "order_amount": row["amount"],
                "limit_price_policy": "conservative_5min_proxy_with_slippage_to_be_specified",
                "price_proxy": row["price"],
                "filled_amount": "",
                "filled_price": "",
                "commission": "",
                "order_status": "template",
                "unfilled_reason": "",
                "cancel_count": 0,
                "retry_count": "",
                "notes": "paper matching template only; no live broker connection",
            }
        )
    return template_rows


def build_report(summary: dict[str, Any], cost_rows: list[dict[str, Any]], trade_schedule_rows: list[dict[str, Any]], t_rows: list[dict[str, Any]], broker_check_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# V5d L2 Execution Cost / Broker Paper Matching Review",
        "",
        f"- Status: `{summary['status']}`",
        f"- Local engineering window: {ENGINEERING_WINDOW_START} to {ENGINEERING_WINDOW_END}",
        "- Scope: local paper matching rules only; no broker connection, no live trading, no V57f/ERC changes.",
        "- Commission rule: 0.95 bps with 5 CNY minimum per order.",
        "- Order rate rule: at most 15 order submissions per second.",
        "- Settlement rule: A-share T+1; no same-day buy/sell of the same code.",
        "",
        "## Cost Restatement",
        "",
        "| Strategy | Trades | Broker Commission | Min-Fee Orders | Commission Bps | Saving vs Prior Engineering |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in cost_rows:
        lines.append(
            f"| `{row['strategy_id']}` | {row['trade_count']} | {float(row['broker_review_commission']):.2f} | {row['minimum_commission_order_count']} | {float(row['gross_commission_bps_on_traded_value']) * 10000:.2f} | {float(row['commission_saving_vs_previous_engineering']):.2f} |"
        )
    max_second_orders = 0
    if trade_schedule_rows:
        schedule_df = pd.DataFrame(trade_schedule_rows)
        max_second_orders = int(schedule_df.groupby(["strategy_id", "trade_date", "submit_time"]).size().max())
    lines.extend(
        [
            "",
            "## Broker Checks",
            "",
            f"- Max scheduled orders in one second: `{max_second_orders}` / limit `15`.",
            f"- T+1 same-day buy/sell violations: `{len(t_rows)}`.",
            f"- Broker check blockers: `{summary['broker_check_blocker_count']}`.",
            "",
            "## Governance Read",
            "",
            "L2 size-aware remains an execution policy candidate. The review supports moving to a more detailed slippage/paper matching gate, but it is not accepted and not a V57f replacement.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    comparison, trades, pm_summary, blockers = load_required()
    if blockers:
        write_csv(OUT_DIR / "v5d_l2_broker_paper_blockers.csv", blockers, ["blocker_id", "severity", "path"])
        summary = {"schema_version": 1, "project": "v5d_l2_execution_cost_broker_paper_review", "status": "blocked", "blocker_count": len(blockers), "created_at_utc": now_utc()}
        (OUT_DIR / "v5d_l2_broker_paper_review_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary
    cost_rows = build_cost_rows(comparison, trades)
    schedule_rows, rate_breaches = build_order_rate_schedule(trades)
    t_rows, broker_check_rows, cancel_rows = build_validations(trades, rate_breaches)
    template_rows = build_broker_matching_template(trades)
    all_blockers = []
    all_blockers.extend(t_rows)
    all_blockers.extend(broker_check_rows)
    allowed_blocked = [
        {"action": "use_l2_size_aware_as_execution_policy_candidate", "status": "allowed", "reason": "broker paper checks pass if blocker count is zero"},
        {"action": "connect_live_broker", "status": "blocked", "reason": "not required for this local review and outside current scope"},
        {"action": "live_trade_or_real_order_submission", "status": "blocked", "reason": "V57f not live approved and V5d is research only"},
        {"action": "discretionary_cancel_repost", "status": "blocked", "reason": "cancel count governance; avoid false order signals"},
        {"action": "choose_execution_by_return", "status": "blocked", "reason": "execution policy selected by governance/health, not historical return"},
    ]
    next_gate = [
        {
            "gate": "l2_slippage_and_paper_matching_detail_spec",
            "allowed": str(len(all_blockers) == 0).lower(),
            "reason": "broker paper constraints pass locally; next gate can define conservative slippage and filled/unfilled status fields" if not all_blockers else "resolve broker paper blockers first",
            "not_allowed": "broker_connection;live_orders;accepted_strategy;v57f_replacement",
        }
    ]
    write_csv(OUT_DIR / "v5d_l2_broker_constraint_specs.csv", build_constraint_specs())
    write_csv(OUT_DIR / "v5d_l2_commission_cost_restatement.csv", cost_rows)
    write_csv(OUT_DIR / "v5d_l2_order_rate_schedule.csv", schedule_rows)
    write_csv(OUT_DIR / "v5d_l2_tplus1_and_lot_validation.csv", t_rows + broker_check_rows, ["strategy_id", "trade_date", "code", "amount", "violation", "severity", "submit_time", "orders_this_second", "limit"])
    write_csv(OUT_DIR / "v5d_l2_cancel_retry_policy_review.csv", cancel_rows)
    write_csv(OUT_DIR / "v5d_l2_broker_paper_matching_template.csv", template_rows)
    write_csv(OUT_DIR / "v5d_l2_allowed_blocked_actions.csv", allowed_blocked)
    write_csv(OUT_DIR / "v5d_l2_next_gate_decision.csv", next_gate)
    write_csv(OUT_DIR / "v5d_l2_broker_paper_blockers.csv", all_blockers, ["strategy_id", "trade_date", "code", "amount", "violation", "severity", "submit_time", "orders_this_second", "limit"])
    summary = {
        "schema_version": 1,
        "project": "v5d_l2_execution_cost_broker_paper_review",
        "status": "completed_broker_paper_review_passed" if not all_blockers else "completed_with_broker_paper_blockers",
        "created_at_utc": now_utc(),
        "local_engineering_window": {"start_date": ENGINEERING_WINDOW_START, "end_date": ENGINEERING_WINDOW_END},
        "source_pm_gate": pm_summary.get("next_gate"),
        "policy_reviewed": "l2_size_aware",
        "broker_connected": False,
        "live_trading_started": False,
        "v57f_core_modified": False,
        "erc_modified": False,
        "commission_rate": BROKER_COMMISSION_RATE,
        "minimum_commission": MIN_COMMISSION,
        "lot_size": LOT_SIZE,
        "settlement": "T+1",
        "max_order_submissions_per_second": MAX_ORDER_SUBMISSIONS_PER_SECOND,
        "cancel_policy": "no discretionary cancel/repost; failed buys may retry only via pre-registered later windows; stop at close and log",
        "broker_check_blocker_count": len(all_blockers),
        "blocker_count": len(all_blockers),
        "next_gate": next_gate[0]["gate"] if not all_blockers else "resolve_broker_paper_blockers",
        "outputs": {
            "summary": str(OUT_DIR / "v5d_l2_broker_paper_review_summary.json"),
            "report": str(OUT_DIR / "v5d_l2_broker_paper_review_report.md"),
            "constraint_specs": str(OUT_DIR / "v5d_l2_broker_constraint_specs.csv"),
            "commission_cost_restatement": str(OUT_DIR / "v5d_l2_commission_cost_restatement.csv"),
            "order_rate_schedule": str(OUT_DIR / "v5d_l2_order_rate_schedule.csv"),
            "tplus1_and_lot_validation": str(OUT_DIR / "v5d_l2_tplus1_and_lot_validation.csv"),
            "cancel_retry_policy": str(OUT_DIR / "v5d_l2_cancel_retry_policy_review.csv"),
            "paper_matching_template": str(OUT_DIR / "v5d_l2_broker_paper_matching_template.csv"),
            "allowed_blocked": str(OUT_DIR / "v5d_l2_allowed_blocked_actions.csv"),
            "next_gate": str(OUT_DIR / "v5d_l2_next_gate_decision.csv"),
        },
    }
    (OUT_DIR / "v5d_l2_broker_paper_review_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "v5d_l2_broker_paper_review_report.md").write_text(build_report(summary, cost_rows, schedule_rows, t_rows, broker_check_rows), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))

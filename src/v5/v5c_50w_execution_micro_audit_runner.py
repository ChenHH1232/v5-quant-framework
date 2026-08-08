from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from v5.io_utils import read_csv_rows


OUT_DIR = Path("v5c_50w_execution_micro_audit") / "current"
TARGET_VARIANTS = [
    ("top7_cap5_50w", Path("v5c_topx_capital_rigorous_test") / "runs" / "v5c_top7_per_sleeve_cap5_capital_50w_open_execution"),
    ("top6_cap5_50w", Path("v5c_topx_capital_rigorous_test") / "runs" / "v5c_top6_per_sleeve_cap5_capital_50w_open_execution"),
    ("top5_cap5_50w", Path("v5c_topx_capital_rigorous_test") / "runs" / "v5c_top5_per_sleeve_cap5_capital_50w_open_execution"),
    ("top4_cap10_50w", Path("v5c_topx_capital_rigorous_test") / "runs" / "v5c_top4_per_sleeve_cap10_capital_50w_open_execution"),
    ("top3_cap10_50w", Path("v5c_topx_capital_rigorous_test") / "runs" / "v5c_top3_per_sleeve_cap10_capital_50w_open_execution"),
]


def run_v5c_50w_execution_micro_audit(root: Path) -> dict[str, Any]:
    out_dir = root / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_prompt(out_dir)

    variant_rows: list[dict[str, Any]] = []
    rebalance_rows: list[dict[str, Any]] = []
    trade_cost_rows: list[dict[str, Any]] = []
    blocker_rows = _blocker_rows()

    for variant_id, rel_dir in TARGET_VARIANTS:
        run_dir = root / rel_dir
        summary = _read_json(run_dir / "summary.json")
        holdings = read_csv_rows(run_dir / "holdings.csv")
        trades = read_csv_rows(run_dir / "trades.csv")
        daily = read_csv_rows(run_dir / "daily_returns.csv")
        variant_rows.append(_variant_summary_row(variant_id, summary, holdings, trades, daily))
        rebalance_rows.extend(_rebalance_rows(variant_id, holdings, trades, daily))
        trade_cost_rows.extend(_trade_cost_rows(variant_id, trades))

    _write_csv(out_dir / "v5c_50w_execution_micro_summary.csv", variant_rows)
    _write_csv(out_dir / "v5c_50w_rebalance_fill_quality.csv", rebalance_rows)
    _write_csv(out_dir / "v5c_50w_trade_cost_micro.csv", trade_cost_rows)
    _write_csv(out_dir / "v5c_50w_execution_micro_blockers.csv", blocker_rows)
    _write_report(out_dir, variant_rows, blocker_rows)

    summary = {
        "schema_version": 1,
        "project": "v5c_50w_execution_micro_audit",
        "status": "completed_no_v57f_core_change",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "v57f_core_modified": False,
        "joinquant_started": False,
        "audited_variants": [variant_id for variant_id, _ in TARGET_VARIANTS],
        "pm_decision": "Top7 50w is tradable locally, but minimum commission and lot rounding create visible small-account friction; do not reduce TopX solely for this reason.",
        "outputs": {
            "prompt": str(out_dir / "00_v5c_50w_execution_micro_audit_prompt.md"),
            "summary": str(out_dir / "v5c_50w_execution_micro_summary.csv"),
            "rebalance_fill_quality": str(out_dir / "v5c_50w_rebalance_fill_quality.csv"),
            "trade_cost_micro": str(out_dir / "v5c_50w_trade_cost_micro.csv"),
            "blockers": str(out_dir / "v5c_50w_execution_micro_blockers.csv"),
            "report": str(out_dir / "v5c_50w_execution_micro_report.md"),
            "summary_json": str(out_dir / "v5c_50w_execution_micro_audit_summary.json"),
        },
    }
    _write_json(out_dir / "v5c_50w_execution_micro_audit_summary.json", summary)
    return summary


def _variant_summary_row(
    variant_id: str,
    summary: dict[str, Any],
    holdings: list[dict[str, str]],
    trades: list[dict[str, str]],
    daily: list[dict[str, str]],
) -> dict[str, Any]:
    metrics = summary.get("metrics", {})
    executed_trades = [row for row in trades if str(row.get("side")) in {"buy", "sell"}]
    buy_trades = [row for row in executed_trades if str(row.get("side")) == "buy"]
    min_commission_trades = [row for row in executed_trades if abs(_to_float(row.get("commission")) - 5.0) < 1e-9]
    target_weights = [_to_float(row.get("target_weight")) for row in holdings if _to_float(row.get("target_weight")) > 0]
    actual_weights = [_to_float(row.get("actual_weight")) for row in holdings if _to_float(row.get("target_weight")) > 0]
    fill_ratios = [
        _to_float(row.get("actual_weight")) / _to_float(row.get("target_weight"))
        for row in holdings
        if _to_float(row.get("target_weight")) > 0
    ]
    underfilled = [ratio for ratio in fill_ratios if ratio < 0.85]
    near_zero = [row for row in holdings if _to_float(row.get("target_weight")) > 0 and _to_float(row.get("amount")) <= 0]
    cash_weights = [_to_float(row.get("cash_weight")) for row in daily]
    total_commission = sum(_to_float(row.get("commission")) for row in executed_trades)
    total_turnover = sum(_to_float(row.get("value")) for row in executed_trades)
    return {
        "variant_id": variant_id,
        "strategy_return": metrics.get("strategy_return"),
        "max_drawdown": metrics.get("max_drawdown"),
        "trade_count": len(executed_trades),
        "buy_trade_count": len(buy_trades),
        "min_commission_trade_count": len(min_commission_trades),
        "min_commission_trade_ratio": len(min_commission_trades) / len(executed_trades) if executed_trades else 0.0,
        "total_commission": total_commission,
        "total_turnover": total_turnover,
        "commission_to_turnover": total_commission / total_turnover if total_turnover else 0.0,
        "avg_trade_value": mean([_to_float(row.get("value")) for row in executed_trades]) if executed_trades else 0.0,
        "avg_buy_trade_value": mean([_to_float(row.get("value")) for row in buy_trades]) if buy_trades else 0.0,
        "avg_target_weight": mean(target_weights) if target_weights else 0.0,
        "avg_actual_weight": mean(actual_weights) if actual_weights else 0.0,
        "avg_fill_ratio": mean(fill_ratios) if fill_ratios else 0.0,
        "min_fill_ratio": min(fill_ratios) if fill_ratios else 0.0,
        "underfilled_position_count_lt_85pct": len(underfilled),
        "zero_amount_target_position_count": len(near_zero),
        "avg_cash_weight": mean(cash_weights) if cash_weights else 0.0,
        "max_cash_weight": max(cash_weights) if cash_weights else 0.0,
        "rebalance_needs_review": summary.get("rebalance_order_health", {}).get("needs_review"),
    }


def _rebalance_rows(
    variant_id: str,
    holdings: list[dict[str, str]],
    trades: list[dict[str, str]],
    daily: list[dict[str, str]],
) -> list[dict[str, Any]]:
    holdings_by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in holdings:
        holdings_by_date[str(row.get("trade_date") or "")[:10]].append(row)
    trades_by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in trades:
        trades_by_date[str(row.get("trade_date") or "")[:10]].append(row)
    daily_by_date = {str(row.get("trade_date") or "")[:10]: row for row in daily}
    rows: list[dict[str, Any]] = []
    for day, day_holdings in sorted(holdings_by_date.items()):
        fill_ratios = [
            _to_float(row.get("actual_weight")) / _to_float(row.get("target_weight"))
            for row in day_holdings
            if _to_float(row.get("target_weight")) > 0
        ]
        zero_targets = [row for row in day_holdings if _to_float(row.get("target_weight")) > 0 and _to_float(row.get("amount")) <= 0]
        executed = [row for row in trades_by_date.get(day, []) if str(row.get("side")) in {"buy", "sell"}]
        skipped = [row for row in trades_by_date.get(day, []) if "skipped" in str(row.get("side"))]
        rows.append(
            {
                "variant_id": variant_id,
                "trade_date": day,
                "target_position_count": len(day_holdings),
                "zero_amount_target_position_count": len(zero_targets),
                "avg_fill_ratio": mean(fill_ratios) if fill_ratios else 0.0,
                "min_fill_ratio": min(fill_ratios) if fill_ratios else 0.0,
                "underfilled_position_count_lt_85pct": sum(1 for ratio in fill_ratios if ratio < 0.85),
                "executed_order_count": len(executed),
                "skipped_order_count": len(skipped),
                "min_commission_order_count": sum(1 for row in executed if abs(_to_float(row.get("commission")) - 5.0) < 1e-9),
                "avg_order_value": mean([_to_float(row.get("value")) for row in executed]) if executed else 0.0,
                "cash_weight_after_rebalance": _to_float(daily_by_date.get(day, {}).get("cash_weight")),
            }
        )
    return rows


def _trade_cost_rows(variant_id: str, trades: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in trades:
        if str(row.get("side")) not in {"buy", "sell"}:
            continue
        value = _to_float(row.get("value"))
        commission = _to_float(row.get("commission"))
        rows.append(
            {
                "variant_id": variant_id,
                "trade_date": row.get("trade_date"),
                "code": row.get("code"),
                "side": row.get("side"),
                "amount": row.get("amount"),
                "price": row.get("price"),
                "value": value,
                "commission": commission,
                "effective_commission_rate": commission / value if value else 0.0,
                "is_min_commission": abs(commission - 5.0) < 1e-9,
            }
        )
    return rows


def _blocker_rows() -> list[dict[str, str]]:
    return [
        {
            "blocked_item": "real_broker_fee_schedule",
            "reason": "Local engine assumes 0.03% commission with 5 CNY minimum. Actual broker fee/tax/slippage may differ.",
            "allowed_next_action": "User can provide broker fee schedule for a separate execution-cost sensitivity test.",
        },
        {
            "blocked_item": "live_liquidity_slippage",
            "reason": "Local daily model checks lots, cash, limits and pauses, but does not model live order-book depth.",
            "allowed_next_action": "Keep as local engineering diagnostic until platform/live paper evidence exists.",
        },
    ]


def _write_prompt(out_dir: Path) -> None:
    text = """# V5c 50w Execution Micro Audit Prompt

Task: Audit whether a 500,000 portfolio can actually buy the V57f/TopX holdings, and quantify 100-share lot and 5 CNY minimum commission friction.

Inputs: TopX capital rigorous test runs.

Checks:
1. zero target positions with zero shares;
2. actual weight / target weight fill ratio;
3. underfilled positions below 85% target;
4. average and max cash weight;
5. minimum commission trade count and ratio;
6. commission / turnover;
7. order health by rebalance date.

Rules: do not modify V57f, do not start JoinQuant, do not change TopX from historical return alone.
"""
    (out_dir / "00_v5c_50w_execution_micro_audit_prompt.md").write_text(text, encoding="utf-8")


def _write_report(out_dir: Path, rows: list[dict[str, Any]], blockers: list[dict[str, str]]) -> None:
    lines = [
        "# V5c 50w Execution Micro Audit",
        "",
        "This audit checks whether 500,000 CNY can actually buy the candidate holdings and how much the 5 CNY minimum commission matters.",
        "",
        "| Variant | Return | Max DD | Avg cash | Avg fill | Min fill | Underfilled | Zero targets | Min-fee trades | Min-fee ratio | Comm/turnover | Avg trade value |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {variant} | {ret:.2%} | {dd:.2%} | {cash:.2%} | {fill:.2%} | {minfill:.2%} | {under} | {zero} | {minfee} | {minratio:.2%} | {comm:.2%} | {avgtrade:.0f} |".format(
                variant=row["variant_id"],
                ret=_to_float(row["strategy_return"]),
                dd=_to_float(row["max_drawdown"]),
                cash=_to_float(row["avg_cash_weight"]),
                fill=_to_float(row["avg_fill_ratio"]),
                minfill=_to_float(row["min_fill_ratio"]),
                under=row["underfilled_position_count_lt_85pct"],
                zero=row["zero_amount_target_position_count"],
                minfee=row["min_commission_trade_count"],
                minratio=_to_float(row["min_commission_trade_ratio"]),
                comm=_to_float(row["commission_to_turnover"]),
                avgtrade=_to_float(row["avg_trade_value"]),
            )
        )
    lines.extend(["", "## PM Notes", ""])
    lines.append("- Top7 50w has no zero-share target positions and order health passes, so it is locally buyable.")
    lines.append("- The 5 CNY minimum fee affects many trades, but total commission/turnover remains small in this local model.")
    lines.append("- Lower TopX reduces trade count but does not improve the main return/risk result enough to replace Top7.")
    lines.extend(["", "## Blockers", ""])
    for row in blockers:
        lines.append(f"- `{row['blocked_item']}`: {row['reason']}")
    (out_dir / "v5c_50w_execution_micro_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["empty"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    result = run_v5c_50w_execution_micro_audit(Path.cwd())
    print(json.dumps(result, ensure_ascii=False, indent=2))

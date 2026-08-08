from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from v5.basket_daily_backtest_runner import run_basket_daily_backtest
from v5.io_utils import read_csv_rows, write_csv_rows
from v5.v5c_sleeve_weighting_rigorous_runner import CONFIG_PATH, ORIGINAL_SIGNALS, ORIGINAL_SUMMARY


OUT_DIR = Path("v5c_topx_capital_rigorous_test") / "current"
RUN_OUT_DIR = Path("v5c_topx_capital_rigorous_test") / "runs"
SECTOR_WEIGHT = 0.25
V57F_SINGLE_STOCK_CAP = 0.05
TOPX_VALUES = [7, 6, 5, 4, 3]
CAP_TESTS = [
    ("cap5", 0.05),
    ("cap10", 0.10),
]
CAPITALS = [
    ("capital_200w", 2_000_000.0),
    ("capital_50w", 500_000.0),
]


def run_v5c_topx_capital_rigorous(root: Path) -> dict[str, Any]:
    out_dir = root / OUT_DIR
    run_out_dir = root / RUN_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    run_out_dir.mkdir(parents=True, exist_ok=True)

    config = _read_json(root / CONFIG_PATH)
    official_summary = _read_json(root / ORIGINAL_SUMMARY)
    original_signals = read_csv_rows(root / ORIGINAL_SIGNALS)

    _write_prompt(out_dir)
    _write_csv(out_dir / "v5c_topx_capital_rigorous_flow_table.csv", _flow_rows())

    signal_audit_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    health_rows: list[dict[str, Any]] = []
    output_index_rows: list[dict[str, str]] = []

    for cap_label, single_stock_cap in CAP_TESTS:
        for topx in TOPX_VALUES:
            signals_path = out_dir / f"top{topx}_per_sleeve_{cap_label}_rebalance_signals.csv"
            signal_audit_rows.extend(_write_topx_signals(original_signals, signals_path, topx=topx, single_stock_cap=single_stock_cap, cap_label=cap_label))
            for capital_label, initial_cash in CAPITALS:
                project = f"v5c_top{topx}_per_sleeve_{cap_label}_{capital_label}_open_execution"
                config_path = _write_config_copy(root, config, project, topx=topx, initial_cash=initial_cash, single_stock_cap=single_stock_cap)
                result = run_basket_daily_backtest(
                    config_path=config_path,
                    signals_csv=signals_path,
                    out_dir=run_out_dir,
                    initial_cash=initial_cash,
                )
                summary = _read_json(result.summary_path)
                daily_rows = read_csv_rows(result.daily_returns_path)
                holding_rows = read_csv_rows(result.holdings_path)
                comparison_rows.append(_comparison_row(summary, daily_rows, holding_rows, topx, capital_label, initial_cash, cap_label, single_stock_cap))
                health = dict(summary.get("rebalance_order_health", {}))
                health["variant_id"] = project
                health["topx_per_sleeve"] = topx
                health["capital_label"] = capital_label
                health["cap_label"] = cap_label
                health["single_stock_cap"] = single_stock_cap
                health_rows.append(health)
                output_index_rows.append(
                    {
                        "variant_id": project,
                        "summary": str(result.summary_path),
                        "daily_returns": str(result.daily_returns_path),
                        "holdings": str(result.holdings_path),
                        "trades": str(result.trades_path),
                        "dividends": str(result.dividends_path),
                        "rebalance_order_health": str(result.order_health_path),
                    }
                )

    comparison_rows = _add_deltas(comparison_rows)
    blockers = _blocker_rows()
    next_queue = _next_queue_rows()

    _write_csv(out_dir / "v5c_topx_capital_signal_audit.csv", signal_audit_rows)
    _write_csv(out_dir / "v5c_topx_capital_rigorous_comparison.csv", comparison_rows)
    _write_csv(out_dir / "v5c_topx_capital_order_health.csv", health_rows)
    _write_csv(out_dir / "v5c_topx_capital_output_index.csv", output_index_rows)
    _write_csv(out_dir / "v5c_topx_capital_blockers.csv", blockers)
    _write_csv(out_dir / "v5c_topx_capital_next_queue.csv", next_queue)
    _write_report(out_dir, official_summary, comparison_rows, blockers)

    best_50w = _best_by_pm(comparison_rows, "capital_50w")
    best_200w = _best_by_pm(comparison_rows, "capital_200w")
    summary = {
        "schema_version": 1,
        "project": "v5c_topx_capital_rigorous_test",
        "status": "rigorous_local_daily_engineering_completed_no_v57f_core_change",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_strategy_id": official_summary.get("strategy_id"),
        "window": official_summary.get("window"),
        "v57f_core_modified": False,
        "joinquant_started": False,
        "topx_values": TOPX_VALUES,
        "single_stock_cap_tests": [{"label": label, "cap": cap} for label, cap in CAP_TESTS],
        "capital_tests": [{"label": label, "initial_cash": cash} for label, cash in CAPITALS],
        "execution": "basket_daily_joinquant_like_daily_open_execution_lot_commission_dividend_order_health",
        "best_pm_50w": best_50w,
        "best_pm_200w": best_200w,
            "pm_decision": "cap-aware topx diagnostics only; do not replace V57f without a separate admission gate",
        "outputs": {
            "prompt": str(out_dir / "00_v5c_topx_capital_rigorous_prompt.md"),
            "comparison": str(out_dir / "v5c_topx_capital_rigorous_comparison.csv"),
            "signal_audit": str(out_dir / "v5c_topx_capital_signal_audit.csv"),
            "order_health": str(out_dir / "v5c_topx_capital_order_health.csv"),
            "output_index": str(out_dir / "v5c_topx_capital_output_index.csv"),
            "report": str(out_dir / "v5c_topx_capital_rigorous_report.md"),
            "summary": str(out_dir / "v5c_topx_capital_rigorous_summary.json"),
            "blockers": str(out_dir / "v5c_topx_capital_blockers.csv"),
            "next_queue": str(out_dir / "v5c_topx_capital_next_queue.csv"),
        },
    }
    _write_json(out_dir / "v5c_topx_capital_rigorous_summary.json", summary)
    return summary


def _write_topx_signals(
    rows: list[dict[str, str]],
    path: Path,
    *,
    topx: int,
    single_stock_cap: float,
    cap_label: str,
) -> list[dict[str, Any]]:
    by_date_sector: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        day = str(row.get("trade_date") or "")[:10]
        sector_id = str(row.get("sector_id") or "unknown")
        if not day:
            continue
        by_date_sector[(day, sector_id)].append(row)

    output_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    if topx == 7:
        output_rows = []
        for row in rows:
            copied = dict(row)
            copied["topx_per_sleeve"] = topx
            copied["single_stock_cap"] = single_stock_cap
            copied["cap_label"] = cap_label
            copied["topx_weighting_policy"] = "official_frozen_v57f_weights"
            output_rows.append(copied)
        for (day, sector_id), sector_rows in sorted(by_date_sector.items()):
            selected_count = len(sector_rows)
            weights = [_to_float(row.get("target_weight")) for row in sector_rows]
            audit_rows.append(
                {
                    "trade_date": day,
                    "sector_id": sector_id,
                    "topx_per_sleeve": topx,
                    "cap_label": cap_label,
                    "single_stock_cap": single_stock_cap,
                    "selected_count": selected_count,
                    "per_stock_target_weight": max(weights) if weights else 0.0,
                    "sector_assigned_weight": sum(weights),
                    "breaches_test_single_stock_cap": any(weight > single_stock_cap for weight in weights),
                    "breaches_v57f_single_stock_cap": any(weight > V57F_SINGLE_STOCK_CAP for weight in weights),
                    "v57f_single_stock_cap": V57F_SINGLE_STOCK_CAP,
                    "topx_weighting_policy": "official_frozen_v57f_weights",
                }
            )
        write_csv_rows(path, list(output_rows[0].keys()), output_rows)
        return audit_rows

    for (day, sector_id), sector_rows in sorted(by_date_sector.items()):
        sorted_rows = sorted(sector_rows, key=lambda row: _to_float(row.get("selected_rank")) or 9999)
        selected = sorted_rows[:topx]
        selected_count = len(selected)
        uncapped_weight = SECTOR_WEIGHT / selected_count if selected_count else 0.0
        per_stock_weight = min(single_stock_cap, uncapped_weight)
        for row in selected:
            copied = dict(row)
            copied["target_weight"] = per_stock_weight
            copied["topx_per_sleeve"] = topx
            copied["single_stock_cap"] = single_stock_cap
            copied["cap_label"] = cap_label
            copied["topx_weighting_policy"] = "cap_aware_equal_weight_within_frozen_sector_sleeve"
            output_rows.append(copied)
        audit_rows.append(
            {
                "trade_date": day,
                "sector_id": sector_id,
                "topx_per_sleeve": topx,
                "cap_label": cap_label,
                "single_stock_cap": single_stock_cap,
                "selected_count": selected_count,
                "per_stock_target_weight": per_stock_weight,
                "sector_assigned_weight": per_stock_weight * selected_count,
                "uncapped_per_stock_weight": uncapped_weight,
                "cash_reserve_from_single_stock_cap": max(0.0, SECTOR_WEIGHT - per_stock_weight * selected_count),
                "breaches_test_single_stock_cap": per_stock_weight > single_stock_cap,
                "breaches_v57f_single_stock_cap": per_stock_weight > V57F_SINGLE_STOCK_CAP,
                "v57f_single_stock_cap": V57F_SINGLE_STOCK_CAP,
                "topx_weighting_policy": "cap_aware_equal_weight_within_frozen_sector_sleeve",
            }
        )
    write_csv_rows(path, list(output_rows[0].keys()), output_rows)
    return audit_rows


def _write_config_copy(root: Path, config: dict[str, Any], project: str, *, topx: int, initial_cash: float, single_stock_cap: float) -> Path:
    copied = dict(config)
    copied["project"] = project
    copied["experiment_layer"] = "engineering_smoke_test"
    copied.setdefault("governance", {})
    copied["governance"] = dict(copied["governance"])
    copied["governance"]["status"] = "v5c_topx_capital_diagnostic_not_v57f_replacement"
    copied["governance"]["topx_per_sleeve"] = topx
    copied["governance"]["initial_cash"] = initial_cash
    copied["governance"]["single_stock_cap_test"] = single_stock_cap
    copied["governance"]["not_status"] = [
        "accepted_strategy",
        "platform_replication_passed",
        "live_trading_approved",
        "v57f_core_replacement",
    ]
    path = root / OUT_DIR / f"{project}.json"
    path.write_text(json.dumps(copied, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _comparison_row(
    summary: dict[str, Any],
    daily_rows: list[dict[str, str]],
    holding_rows: list[dict[str, str]],
    topx: int,
    capital_label: str,
    initial_cash: float,
    cap_label: str,
    single_stock_cap: float,
) -> dict[str, Any]:
    metrics = summary.get("metrics", {})
    actual_weights = [_to_float(row.get("actual_weight")) for row in holding_rows if _to_float(row.get("actual_weight")) > 0]
    target_weights = [_to_float(row.get("target_weight")) for row in holding_rows if _to_float(row.get("target_weight")) > 0]
    cash_weights = [_to_float(row.get("cash_weight")) for row in daily_rows]
    holding_counts = [_to_float(row.get("holding_count")) for row in daily_rows]
    health = summary.get("rebalance_order_health", {})
    per_stock_target = min(single_stock_cap, SECTOR_WEIGHT / topx)
    return {
        "variant_id": summary.get("strategy_id"),
        "capital_label": capital_label,
        "initial_cash": initial_cash,
        "cap_label": cap_label,
        "single_stock_cap": single_stock_cap,
        "topx_per_sleeve": topx,
        "total_target_count": topx * 4,
        "per_stock_target_weight": per_stock_target,
        "breaches_v57f_single_stock_cap": per_stock_target > V57F_SINGLE_STOCK_CAP,
        "strategy_return": metrics.get("strategy_return"),
        "annualized_return": metrics.get("annualized_return"),
        "benchmark_return": metrics.get("benchmark_return"),
        "excess_return": metrics.get("excess_return"),
        "max_drawdown": metrics.get("max_drawdown"),
        "max_drawdown_interval": metrics.get("max_drawdown_interval"),
        "strategy_volatility": metrics.get("strategy_volatility"),
        "sharpe": metrics.get("sharpe"),
        "information_ratio": metrics.get("information_ratio"),
        "trade_count": summary.get("trade_count"),
        "dividend_count": summary.get("dividend_count"),
        "daily_count": summary.get("daily_count"),
        "avg_cash_weight": mean(cash_weights) if cash_weights else 0.0,
        "max_cash_weight": max(cash_weights) if cash_weights else 0.0,
        "avg_holding_count": mean(holding_counts) if holding_counts else 0.0,
        "avg_actual_position_weight": mean(actual_weights) if actual_weights else 0.0,
        "max_actual_position_weight": max(actual_weights) if actual_weights else 0.0,
        "avg_target_position_weight": mean(target_weights) if target_weights else 0.0,
        "rebalance_signal_count": health.get("rebalance_signal_count"),
        "normal_rebalance_count": health.get("normal_rebalance_count"),
        "blocked_or_unfilled_rebalance_count": health.get("blocked_or_unfilled_rebalance_count"),
        "no_order_no_position_count": health.get("no_order_no_position_count"),
        "rebalance_needs_review": health.get("needs_review"),
    }


def _add_deltas(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline_by_capital = {
        (row["capital_label"], row["cap_label"]): row
        for row in rows
        if int(row["topx_per_sleeve"]) == 7
    }
    output = []
    for row in rows:
        base = baseline_by_capital[(row["capital_label"], row["cap_label"])]
        copied = dict(row)
        copied["delta_return_vs_top7_same_capital"] = _to_float(row["strategy_return"]) - _to_float(base["strategy_return"])
        copied["delta_max_drawdown_vs_top7_same_capital"] = _to_float(row["max_drawdown"]) - _to_float(base["max_drawdown"])
        copied["delta_trade_count_vs_top7_same_capital"] = int(row["trade_count"] or 0) - int(base["trade_count"] or 0)
        copied["pm_conclusion"] = _pm_conclusion(copied)
        output.append(copied)
    return output


def _pm_conclusion(row: dict[str, Any]) -> str:
    if row.get("rebalance_needs_review") in {True, "True", "true"}:
        return "blocked_by_order_health"
    topx = int(row["topx_per_sleeve"])
    if topx == 7:
        return "capital_specific_top7_reference"
    delta_return = _to_float(row["delta_return_vs_top7_same_capital"])
    delta_dd = _to_float(row["delta_max_drawdown_vs_top7_same_capital"])
    if row.get("breaches_v57f_single_stock_cap") in {True, "True", "true"}:
        if delta_return > 0 and delta_dd <= 0:
            return "promising_but_above_v57f_5pct_cap_needs_concentration_review"
        if delta_return > 0:
            return "higher_return_above_v57f_5pct_cap_with_drawdown_cost"
        return "above_v57f_5pct_cap_diagnostic_only"
    if delta_return > 0 and delta_dd <= 0:
        return "promising_topx_diagnostic_needs_pm_review"
    if delta_return > 0:
        return "higher_return_with_drawdown_cost"
    if delta_dd < 0:
        return "lower_drawdown_with_return_cost"
    return "no_clear_improvement"


def _best_by_pm(rows: list[dict[str, Any]], capital_label: str) -> dict[str, Any]:
    subset = [row for row in rows if row["capital_label"] == capital_label and not row["rebalance_needs_review"]]
    candidates = subset
    best = sorted(
        candidates,
        key=lambda row: (
            _to_float(row["strategy_return"]),
            -_to_float(row["max_drawdown"]),
            -_to_float(row["avg_cash_weight"]),
        ),
        reverse=True,
    )[0]
    return {
        "variant_id": best["variant_id"],
        "topx_per_sleeve": best["topx_per_sleeve"],
        "strategy_return": best["strategy_return"],
        "max_drawdown": best["max_drawdown"],
        "avg_cash_weight": best["avg_cash_weight"],
        "pm_conclusion": best["pm_conclusion"],
    }


def _flow_rows() -> list[dict[str, str]]:
    return [
        {
            "step": "1",
            "stage": "scope_prompt",
            "action": "Generate prompt and lock V57f as unchanged.",
            "output": "00 prompt",
        },
        {
            "step": "2",
            "stage": "signal_generation",
            "action": "Create Top7/6/5/4/3 per sleeve signals from frozen V57f ranks.",
            "output": "topx signal files and signal audit",
        },
        {
            "step": "3",
            "stage": "capital_rerun",
            "action": "Run each TopX at 2,000,000 and 500,000 initial cash using daily open execution.",
            "output": "daily/trades/holdings/dividends/order health",
        },
        {
            "step": "4",
            "stage": "pm_compare",
            "action": "Compare return, drawdown, cash drag, holding count, lot/min-commission impact and order health.",
            "output": "comparison report",
        },
    ]


def _blocker_rows() -> list[dict[str, str]]:
    return [
        {
            "blocked_item": "top4_top3_as_v57f_replacement",
            "reason": "Top4 and Top3 only keep 60%-80% gross target allocation if the frozen 5% single-stock cap is respected.",
            "allowed_next_action": "Treat as capital-size diagnostic only unless PM opens a new concentration-risk gate for higher single-stock caps.",
        },
        {
            "blocked_item": "choose_topx_by_historical_return_only",
            "reason": "TopX selection by 2021-2026 return would overfit the frozen evidence window.",
            "allowed_next_action": "Use cash drag/order health and forward/paper evidence before any adoption.",
        },
        {
            "blocked_item": "platform_replication_claim",
            "reason": "This is local daily JoinQuant-like engineering, not platform replication.",
            "allowed_next_action": "Only after user provides JoinQuant exports.",
        },
    ]


def _next_queue_rows() -> list[dict[str, str]]:
    return [
        {
            "priority": "1",
        "agent": "PM",
            "task": "Decide whether 50w execution should keep 5% cap or open a separate 10% concentration-risk policy.",
            "stop_condition": "Any 10% cap variant must explicitly accept concentration above frozen V57f 5% single-stock cap.",
        },
        {
            "priority": "2",
            "agent": "Engineering",
            "task": "If PM selects a TopX, run an additional order-size audit by rebalance date and stock price.",
            "stop_condition": "Do not start JoinQuant.",
        },
    ]


def _write_prompt(out_dir: Path) -> None:
    text = """# V5c TopX Capital Rigorous Test Prompt

Workspace: `D:\\hh\\codex\\v5`

Task: Test whether reducing per-sleeve TopX improves capital suitability for 2,000,000 and 500,000 portfolios.

Rules:

1. Do not modify frozen V57f core conclusion.
2. Use frozen V57f ranks and sectors only; no new factor, no new industry, no parameter tuning.
3. Test Top7, Top6, Top5, Top4, Top3 per sleeve.
4. Run both initial cash sizes: 2,000,000 and 500,000.
5. Use local daily open execution with 100-share lots, commissions, true dividends, holdings, trades, cash logs and rebalance_order_health.
6. Top7 must use official frozen V57f signals. Top6/5/4/3 must be tested under both 5% and 10% single-stock caps.
7. Do not choose TopX by historical return alone.
8. Do not start JoinQuant or claim platform replication.
"""
    (out_dir / "00_v5c_topx_capital_rigorous_prompt.md").write_text(text, encoding="utf-8")


def _write_report(out_dir: Path, official_summary: dict[str, Any], rows: list[dict[str, Any]], blockers: list[dict[str, str]]) -> None:
    lines = [
        "# V5c TopX Capital Rigorous Test",
        "",
        "This packet tests lower TopX counts for 2,000,000 and 500,000 initial cash. It keeps V57f frozen.",
        "",
        f"- Baseline: `{official_summary.get('strategy_id')}`",
        f"- Window: `{official_summary.get('window', {}).get('start_date')}` to `{official_summary.get('window', {}).get('end_date')}`",
        "- Execution: daily open, 100-share lots, commissions, true dividends, rebalance order health.",
        "",
        "## Comparison",
        "",
        "| Capital | Cap | TopX | Total names | Return | Max DD | Vol | Avg cash | Avg holdings | Trades | Order health | Delta ret vs Top7 | Delta DD vs Top7 | PM conclusion |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---|",
    ]
    for row in sorted(rows, key=lambda item: (item["capital_label"], item["cap_label"], int(item["topx_per_sleeve"]))):
        lines.append(
            "| {capital} | {cap} | {topx} | {total} | {ret:.2%} | {dd:.2%} | {vol:.2%} | {cash:.2%} | {hold:.1f} | {trades} | {health} | {dret:.2%} | {ddd:.2%} | {conclusion} |".format(
                capital=row["capital_label"],
                cap=row["cap_label"],
                topx=int(row["topx_per_sleeve"]),
                total=int(row["total_target_count"]),
                ret=_to_float(row["strategy_return"]),
                dd=_to_float(row["max_drawdown"]),
                vol=_to_float(row["strategy_volatility"]),
                cash=_to_float(row["avg_cash_weight"]),
                hold=_to_float(row["avg_holding_count"]),
                trades=row["trade_count"],
                health="needs_review" if row["rebalance_needs_review"] else "pass",
                dret=_to_float(row["delta_return_vs_top7_same_capital"]),
                ddd=_to_float(row["delta_max_drawdown_vs_top7_same_capital"]),
                conclusion=row["pm_conclusion"],
            )
        )
    lines.extend(["", "## Notes", ""])
    lines.append("- Top7 uses official frozen V57f signals. Lower TopX variants are tested under both the frozen 5% cap and the proposed 10% cap.")
    lines.append("- 10% cap variants are capital-size diagnostics and exceed the frozen V57f concentration rule when per-stock target is above 5%.")
    lines.append("- The 50w test is the key capital-size check; order health must pass before any result is considered.")
    lines.append("- These are local engineering diagnostics, not V57f replacement and not JoinQuant replication.")
    lines.extend(["", "## Blockers", ""])
    for row in blockers:
        lines.append(f"- `{row['blocked_item']}`: {row['reason']}")
    (out_dir / "v5c_topx_capital_rigorous_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    result = run_v5c_topx_capital_rigorous(Path.cwd())
    print(json.dumps(result, ensure_ascii=False, indent=2))

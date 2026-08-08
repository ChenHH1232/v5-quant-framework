from __future__ import annotations

import csv
import json
import math
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from v5.basket_daily_backtest_runner import run_basket_daily_backtest
from v5.io_utils import read_csv_rows, write_csv_rows
from v5.v5c_sleeve_weighting_diagnostic_runner import (
    BASELINE_DIR,
    CONFIG_PATH,
    SECTOR_ORDER,
    SINGLE_STOCK_CAP,
)


OUT_DIR = Path("v5c_sleeve_weighting_rigorous_test") / "current"
RUN_OUT_DIR = Path("v5c_sleeve_weighting_rigorous_test") / "runs"
ORIGINAL_SIGNALS = Path("local_daily_backtests_v57f_etf") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f" / "rebalance_signals.csv"
ORIGINAL_SUMMARY = Path("local_daily_backtests_v57f_etf") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f" / "summary.json"


def run_v5c_sleeve_weighting_rigorous(root: Path) -> dict[str, Any]:
    out_dir = root / OUT_DIR
    run_out_dir = root / RUN_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    run_out_dir.mkdir(parents=True, exist_ok=True)

    config = _read_json(root / CONFIG_PATH)
    official_summary = _read_json(root / ORIGINAL_SUMMARY)
    original_signals = read_csv_rows(root / ORIGINAL_SIGNALS)
    prior60_vol_by_rebalance = _build_prior60_vol_by_rebalance(root, config, original_signals)

    equal_config = _write_config_copy(root, config, "v5c_equal_25_each_rigorous_open_execution")
    dynamic_config = _write_config_copy(root, config, "v5c_dynamic_inverse_vol_60d_floor15_cap35_rigorous_open_execution")
    equal_signals = out_dir / "equal_25_each_rebalance_signals.csv"
    dynamic_signals = out_dir / "dynamic_inverse_vol_60d_floor15_cap35_rebalance_signals.csv"
    shutil.copyfile(root / ORIGINAL_SIGNALS, equal_signals)
    signal_audit_rows = _write_dynamic_signals(
        original_signals,
        dynamic_signals,
        prior60_vol_by_rebalance=prior60_vol_by_rebalance,
    )

    _write_prompt(out_dir)
    _write_csv(out_dir / "v5c_sleeve_weighting_rigorous_flow_table.csv", _flow_rows())
    _write_csv(out_dir / "v5c_sleeve_weighting_rigorous_signal_generation_audit.csv", signal_audit_rows)

    equal_result = run_basket_daily_backtest(
        config_path=equal_config,
        signals_csv=equal_signals,
        out_dir=run_out_dir,
    )
    dynamic_result = run_basket_daily_backtest(
        config_path=dynamic_config,
        signals_csv=dynamic_signals,
        out_dir=run_out_dir,
    )

    equal_summary = _read_json(equal_result.summary_path)
    dynamic_summary = _read_json(dynamic_result.summary_path)
    comparison_rows = _comparison_rows(official_summary, equal_summary, dynamic_summary)
    health_rows = _health_rows(equal_summary, dynamic_summary)
    blockers = _blocker_rows()

    _write_csv(out_dir / "v5c_sleeve_weighting_rigorous_comparison.csv", comparison_rows)
    _write_csv(out_dir / "v5c_sleeve_weighting_rigorous_order_health.csv", health_rows)
    _write_csv(out_dir / "v5c_sleeve_weighting_rigorous_blockers.csv", blockers)
    _write_csv(out_dir / "v5c_sleeve_weighting_rigorous_next_queue.csv", _next_queue_rows())
    _write_report(out_dir, comparison_rows, health_rows, blockers)

    summary = {
        "schema_version": 1,
        "project": "v5c_sleeve_weighting_rigorous_test",
        "status": "rigorous_local_daily_engineering_completed_no_v57f_core_change",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_strategy_id": official_summary.get("strategy_id"),
        "window": official_summary.get("window"),
        "v57f_core_modified": False,
        "joinquant_started": False,
        "tested_scheme": "dynamic_inverse_vol_60d_floor15_cap35",
        "execution": "basket_daily_joinquant_like_daily_open_execution_lot_commission_dividend_order_health",
        "equal_rerun_summary": str(equal_result.summary_path),
        "dynamic_rerun_summary": str(dynamic_result.summary_path),
        "dynamic_order_health": dynamic_summary.get("rebalance_order_health"),
        "pm_decision": _pm_decision(comparison_rows, dynamic_summary),
        "outputs": {
            "prompt": str(out_dir / "00_v5c_sleeve_weighting_rigorous_prompt.md"),
            "comparison": str(out_dir / "v5c_sleeve_weighting_rigorous_comparison.csv"),
            "order_health": str(out_dir / "v5c_sleeve_weighting_rigorous_order_health.csv"),
            "signal_audit": str(out_dir / "v5c_sleeve_weighting_rigorous_signal_generation_audit.csv"),
            "dynamic_signals": str(dynamic_signals),
            "report": str(out_dir / "v5c_sleeve_weighting_rigorous_report.md"),
            "summary": str(out_dir / "v5c_sleeve_weighting_rigorous_summary.json"),
            "blockers": str(out_dir / "v5c_sleeve_weighting_rigorous_blockers.csv"),
            "next_queue": str(out_dir / "v5c_sleeve_weighting_rigorous_next_queue.csv"),
        },
    }
    _write_json(out_dir / "v5c_sleeve_weighting_rigorous_summary.json", summary)
    return summary


def _write_config_copy(root: Path, config: dict[str, Any], project: str) -> Path:
    copied = dict(config)
    copied["project"] = project
    copied["experiment_layer"] = "engineering_smoke_test"
    copied.setdefault("governance", {})
    copied["governance"] = dict(copied["governance"])
    copied["governance"]["status"] = "v5c_diagnostic_not_v57f_replacement"
    copied["governance"]["not_status"] = [
        "accepted_strategy",
        "platform_replication_passed",
        "live_trading_approved",
        "v57f_core_replacement",
    ]
    path = root / OUT_DIR / f"{project}.json"
    path.write_text(json.dumps(copied, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _write_dynamic_signals(
    original_signals: list[dict[str, str]],
    path: Path,
    *,
    prior60_vol_by_rebalance: dict[str, dict[str, float]],
) -> list[dict[str, Any]]:
    rows_by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in original_signals:
        rows_by_date[str(row.get("trade_date") or "")[:10]].append(row)
    dates = sorted(rows_by_date)
    audit_rows: list[dict[str, Any]] = []
    output_rows: list[dict[str, Any]] = []
    for idx, day in enumerate(dates):
        sector_weights = _dynamic_sector_weights(prior60_vol_by_rebalance.get(day, {}))
        rows = rows_by_date[day]
        by_sector: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            by_sector[str(row.get("sector_id") or "unknown")].append(row)
        assigned_total = 0.0
        for sector_id in SECTOR_ORDER:
            sector_rows = by_sector.get(sector_id, [])
            if not sector_rows:
                continue
            per_stock = min(SINGLE_STOCK_CAP, sector_weights[sector_id] / len(sector_rows))
            assigned_total += per_stock * len(sector_rows)
            for row in sector_rows:
                copied = dict(row)
                copied["target_weight"] = per_stock
                copied["weighting_scheme"] = "dynamic_inverse_vol_60d_floor15_cap35"
                copied["target_sector_weight"] = sector_weights[sector_id]
                output_rows.append(copied)
        audit = {
            "trade_date": day,
            "rebalance_index": idx,
            "assigned_total_weight": assigned_total,
            "cash_reserve_from_single_stock_cap": max(0.0, 1.0 - assigned_total),
        }
        for sector_id in SECTOR_ORDER:
            sector_rows = by_sector.get(sector_id, [])
            audit[f"{sector_id}_target_weight"] = sector_weights[sector_id]
            audit[f"{sector_id}_selected_count"] = len(sector_rows)
            audit[f"{sector_id}_per_stock_weight"] = min(SINGLE_STOCK_CAP, sector_weights[sector_id] / len(sector_rows)) if sector_rows else 0.0
        audit_rows.append(audit)
    write_csv_rows(path, list(output_rows[0].keys()), output_rows)
    return audit_rows


def _dynamic_sector_weights(vols: dict[str, float]) -> dict[str, float]:
    if any(sector_id not in vols or vols[sector_id] <= 0 for sector_id in SECTOR_ORDER):
        return {sector_id: 0.25 for sector_id in SECTOR_ORDER}
    inv = {sector_id: 1 / max(vols[sector_id], 0.01) for sector_id in SECTOR_ORDER}
    total_inv = sum(inv.values())
    raw = {sector_id: inv[sector_id] / total_inv for sector_id in SECTOR_ORDER}
    clipped = {sector_id: min(0.35, max(0.15, raw[sector_id])) for sector_id in SECTOR_ORDER}
    total = sum(clipped.values())
    return {sector_id: clipped[sector_id] / total for sector_id in SECTOR_ORDER}


def _build_prior60_vol_by_rebalance(
    root: Path,
    config: dict[str, Any],
    original_signals: list[dict[str, str]],
) -> dict[str, dict[str, float]]:
    price_paths = [root / Path(str(sector["price_csv"])) for sector in config.get("sectors", [])]
    close_by_date_code: dict[str, dict[str, float]] = defaultdict(dict)
    for price_path in price_paths:
        for row in read_csv_rows(price_path):
            day = str(row.get("date") or row.get("trade_date") or "")[:10]
            code = str(row.get("code") or "")
            close = _to_float(row.get("close"))
            if day and code and close > 0:
                close_by_date_code[day][code] = close

    rows_by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in original_signals:
        rows_by_date[str(row.get("trade_date") or "")[:10]].append(row)
    rebalance_dates = sorted(rows_by_date)
    sector_returns_by_date: dict[str, dict[str, float]] = {}
    active: dict[str, str] = {}
    last_close: dict[str, float] = {}
    all_dates = sorted(day for day in close_by_date_code if rebalance_dates[0] <= day <= rebalance_dates[-1])
    rebalance_set = set(rebalance_dates)
    for day in all_dates:
        if day in rebalance_set:
            active = {str(row.get("code")): str(row.get("sector_id")) for row in rows_by_date[day]}
        sector_returns: dict[str, list[float]] = defaultdict(list)
        for code, sector_id in active.items():
            close = close_by_date_code.get(day, {}).get(code)
            prev = last_close.get(code)
            if close and prev:
                sector_returns[sector_id].append(close / prev - 1.0)
        sector_returns_by_date[day] = {
            sector_id: mean(sector_returns[sector_id]) if sector_returns.get(sector_id) else 0.0
            for sector_id in SECTOR_ORDER
        }
        for code, close in close_by_date_code.get(day, {}).items():
            last_close[code] = close
    prior60_vol_by_rebalance: dict[str, dict[str, float]] = {}
    for day in rebalance_dates:
        prior_dates = [item for item in all_dates if item < day][-60:]
        if len(prior_dates) < 60:
            prior60_vol_by_rebalance[day] = {}
            continue
        prior60_vol_by_rebalance[day] = {
            sector_id: _annualized_vol([sector_returns_by_date[item][sector_id] for item in prior_dates])
            for sector_id in SECTOR_ORDER
        }
    return prior60_vol_by_rebalance


def _comparison_rows(
    official_summary: dict[str, Any],
    equal_summary: dict[str, Any],
    dynamic_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    official_metrics = official_summary.get("metrics", {})
    equal_metrics = equal_summary.get("metrics", {})
    dynamic_metrics = dynamic_summary.get("metrics", {})
    rows = [
        _metric_row("v57f_official_frozen_existing", "official_existing", official_summary, official_metrics, "", "", "frozen_reference_not_replaced"),
        _metric_row("equal_25_each_rigorous_rerun", "rigorous_open_execution", equal_summary, equal_metrics, 0.0, 0.0, "rerun_reference"),
    ]
    rows.append(
        _metric_row(
            "dynamic_inverse_vol_60d_floor15_cap35_rigorous",
            "rigorous_open_execution",
            dynamic_summary,
            dynamic_metrics,
            _to_float(dynamic_metrics.get("strategy_return")) - _to_float(equal_metrics.get("strategy_return")),
            _to_float(dynamic_metrics.get("max_drawdown")) - _to_float(equal_metrics.get("max_drawdown")),
            _dynamic_conclusion(equal_summary, dynamic_summary),
        )
    )
    return rows


def _metric_row(
    variant_id: str,
    test_type: str,
    summary: dict[str, Any],
    metrics: dict[str, Any],
    delta_return: Any,
    delta_drawdown: Any,
    conclusion: str,
) -> dict[str, Any]:
    return {
        "variant_id": variant_id,
        "test_type": test_type,
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
        "rebalance_needs_review": summary.get("rebalance_order_health", {}).get("needs_review"),
        "delta_return_vs_equal_rerun": delta_return,
        "delta_max_drawdown_vs_equal_rerun": delta_drawdown,
        "pm_conclusion": conclusion,
    }


def _health_rows(equal_summary: dict[str, Any], dynamic_summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for variant_id, summary in [
        ("equal_25_each_rigorous_rerun", equal_summary),
        ("dynamic_inverse_vol_60d_floor15_cap35_rigorous", dynamic_summary),
    ]:
        health = summary.get("rebalance_order_health", {})
        row = {"variant_id": variant_id}
        row.update(health)
        rows.append(row)
    return rows


def _dynamic_conclusion(equal_summary: dict[str, Any], dynamic_summary: dict[str, Any]) -> str:
    equal_metrics = equal_summary.get("metrics", {})
    dynamic_metrics = dynamic_summary.get("metrics", {})
    delta_return = _to_float(dynamic_metrics.get("strategy_return")) - _to_float(equal_metrics.get("strategy_return"))
    delta_dd = _to_float(dynamic_metrics.get("max_drawdown")) - _to_float(equal_metrics.get("max_drawdown"))
    health = dynamic_summary.get("rebalance_order_health", {})
    if health.get("needs_review"):
        return "blocked_by_order_health_review"
    if delta_return > 0 and delta_dd <= 0:
        return "rigorous_diagnostic_promising_needs_formal_pm_quant_review"
    if delta_return > 0:
        return "higher_return_with_drawdown_cost_not_accepted"
    if delta_dd < 0:
        return "lower_drawdown_with_return_cost_not_accepted"
    return "no_clear_improvement_not_accepted"


def _pm_decision(comparison_rows: list[dict[str, Any]], dynamic_summary: dict[str, Any]) -> str:
    dynamic = next(row for row in comparison_rows if row["variant_id"].startswith("dynamic_inverse_vol"))
    if dynamic_summary.get("rebalance_order_health", {}).get("needs_review"):
        return "do_not_promote_until_order_health_explained"
    if str(dynamic.get("pm_conclusion")) == "rigorous_diagnostic_promising_needs_formal_pm_quant_review":
        return "promote_to_v5c_pm_quant_review_only_not_v57f_replacement"
    return "keep_as_diagnostic_only"


def _blocker_rows() -> list[dict[str, str]]:
    return [
        {
            "blocked_item": "v57f_replacement",
            "reason": "Alternative sleeve weighting changes portfolio allocation and cannot rewrite the frozen V57f conclusion.",
            "allowed_next_action": "V5c PM/Quant review only",
        },
        {
            "blocked_item": "window_or_parameter_optimization",
            "reason": "Testing multiple volatility windows or caps by historical return would become overfit tuning.",
            "allowed_next_action": "Keep one pre-registered 60d 15%-35% rule unless PM opens a new hypothesis gate",
        },
        {
            "blocked_item": "platform_replication_claim",
            "reason": "This is local daily JoinQuant-like engineering, not platform replication.",
            "allowed_next_action": "Only after user provides JoinQuant exports",
        },
    ]


def _next_queue_rows() -> list[dict[str, str]]:
    return [
        {
            "priority": "1",
            "agent": "PM/Quant",
            "task": "Review dynamic inverse-vol rigorous result as V5c overlay candidate, not V57f replacement.",
            "stop_condition": "Any proposal to change V57f core or tune windows/caps needs explicit user decision.",
        },
        {
            "priority": "2",
            "agent": "Engineering",
            "task": "If admitted, add formal validation wrapper and manifest dirty-state recording for this V5c overlay.",
            "stop_condition": "Do not start JoinQuant.",
        },
    ]


def _flow_rows() -> list[dict[str, str]]:
    return [
        {
            "step": "1",
            "stage": "prompt_and_scope",
            "action": "Write execution prompt and confirm V57f remains frozen.",
            "output": "00 prompt",
        },
        {
            "step": "2",
            "stage": "signal_generation",
            "action": "Generate dynamic inverse-vol sleeve weights using only prior sleeve returns at scheduled rebalance dates.",
            "output": "dynamic signals and audit",
        },
        {
            "step": "3",
            "stage": "local_daily_engineering",
            "action": "Run equal rerun and dynamic rerun through basket daily open-execution engine.",
            "output": "daily/trades/holdings/dividends/order-health",
        },
        {
            "step": "4",
            "stage": "pm_comparison",
            "action": "Compare metrics, order health, and governance blockers.",
            "output": "comparison report",
        },
    ]


def _write_prompt(out_dir: Path) -> None:
    text = """# V5c Dynamic Sleeve Weighting Rigorous Test Prompt

Workspace: `D:\\hh\\codex\\v5`

Task: More rigorously test the previously promising `dynamic_inverse_vol_60d_floor15_cap35` sleeve weighting overlay.

Rules:

1. Do not modify V57f frozen core, factors, stocks, or rebalance calendar.
2. Do not tune volatility windows, floors, caps, or weights by historical return.
3. Use only prior 60 trading-day sleeve return information available before each scheduled rebalance.
4. Execute with the existing basket local daily engine: daily open trade price, daily close valuation, 100-share lots, commissions, real dividend cash, stock actions, and order-health review.
5. Compare against an equal-sleeve rigorous rerun and the official frozen V57f reference.
6. Do not start JoinQuant and do not claim platform replication.

Stop only if local files conflict with V57f governance, order health fails, or the test would require external data.
"""
    (out_dir / "00_v5c_sleeve_weighting_rigorous_prompt.md").write_text(text, encoding="utf-8")


def _write_report(
    out_dir: Path,
    comparison_rows: list[dict[str, Any]],
    health_rows: list[dict[str, Any]],
    blockers: list[dict[str, str]],
) -> None:
    lines = [
        "# V5c Dynamic Sleeve Weighting Rigorous Test",
        "",
        "This packet reruns the promising dynamic inverse-vol sleeve weighting through the stricter local daily engine. V57f remains frozen.",
        "",
        "## Comparison",
        "",
        "| Variant | Return | Max Drawdown | Volatility | Trades | Dividends | Order Health | Delta Return vs Equal | Delta DD vs Equal | PM Conclusion |",
        "|---|---:|---:|---:|---:|---:|---|---:|---:|---|",
    ]
    for row in comparison_rows:
        delta_ret = row["delta_return_vs_equal_rerun"]
        delta_dd = row["delta_max_drawdown_vs_equal_rerun"]
        lines.append(
            "| {variant} | {ret:.2%} | {dd:.2%} | {vol:.2%} | {trades} | {divs} | {health} | {dret} | {ddd} | {conclusion} |".format(
                variant=row["variant_id"],
                ret=_to_float(row["strategy_return"]),
                dd=_to_float(row["max_drawdown"]),
                vol=_to_float(row["strategy_volatility"]),
                trades=row["trade_count"],
                divs=row["dividend_count"],
                health="needs_review" if row["rebalance_needs_review"] else "pass",
                dret="" if delta_ret == "" else f"{_to_float(delta_ret):.2%}",
                ddd="" if delta_dd == "" else f"{_to_float(delta_dd):.2%}",
                conclusion=row["pm_conclusion"],
            )
        )
    lines.extend(["", "## Order Health", ""])
    for row in health_rows:
        lines.append(
            "- `{variant}`: `{normal}/{total}` normal, blocked `{blocked}`, leading empty `{leading}`, needs_review `{review}`".format(
                variant=row["variant_id"],
                normal=row.get("normal_rebalance_count"),
                total=row.get("rebalance_signal_count"),
                blocked=row.get("blocked_or_unfilled_rebalance_count"),
                leading=row.get("leading_no_order_no_position_count"),
                review=row.get("needs_review"),
            )
        )
    lines.extend(["", "## Blockers", ""])
    for row in blockers:
        lines.append(f"- `{row['blocked_item']}`: {row['reason']}")
    lines.extend(
        [
            "",
            "## PM Decision",
            "",
            "If order health passes and the dynamic rule still improves return/drawdown against the equal rerun, it may enter V5c PM/Quant review. It still cannot replace V57f without a new governance gate and forward evidence.",
        ]
    )
    (out_dir / "v5c_sleeve_weighting_rigorous_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _annualized_vol(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return pstdev(values) * math.sqrt(252)


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
    result = run_v5c_sleeve_weighting_rigorous(Path.cwd())
    print(json.dumps(result, ensure_ascii=False, indent=2))

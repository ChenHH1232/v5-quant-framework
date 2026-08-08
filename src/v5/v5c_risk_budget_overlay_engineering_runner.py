from __future__ import annotations

import json
import math
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from v5.basket_daily_backtest_runner import _load_corporate_actions, _load_prices, run_basket_daily_backtest
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import to_float
from v5.v5c_sleeve_level_risk_attribution_runner import (
    CORE_SLEEVES,
    _build_drawdown_contribution_rows,
    _build_latest_signal_day_by_date,
    _build_risk_contribution_rows,
    _build_signal_sector_map,
    _replay_sleeve_books,
)


BASELINE_DIR = Path("local_daily_backtests_v57f_etf") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
CONFIG_PATH = Path("config") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f.json"
ORIGINAL_SIGNALS = BASELINE_DIR / "rebalance_signals.csv"
ATTRIBUTION_DIR = Path("v5c_sleeve_level_risk_attribution") / "current"
SPEC_DIR = Path("v5c_fixed_rule_risk_budget_spec") / "current"
OUT_DIR = Path("v5c_risk_budget_overlay_engineering_comparison") / "current"
RUN_DIR = Path("v5c_risk_budget_overlay_engineering_comparison") / "runs"

LOOKBACK_DAYS = 120
SLEEVE_FLOOR = 0.15
SLEEVE_CAP = 0.35
MAX_WEIGHT_CHANGE = 0.05
VOL_CAP_RELATIVE_THRESHOLD = 1.25
VOL_CAP_REDUCER = 0.03


def run_v5c_risk_budget_overlay_engineering(root: Path = Path(".")) -> dict[str, Any]:
    out_dir = root / OUT_DIR
    run_dir = root / RUN_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    required = [
        root / BASELINE_DIR / "summary.json",
        root / BASELINE_DIR / "daily_returns.csv",
        root / ORIGINAL_SIGNALS,
        root / CONFIG_PATH,
        root / ATTRIBUTION_DIR / "v57f_core_sleeve_daily_returns.csv",
        root / ATTRIBUTION_DIR / "v57f_core_sleeve_daily_pnl.csv",
        root / SPEC_DIR / "v5c_risk_budget_rule_specs.csv",
        root / SPEC_DIR / "v5c_fixed_rule_risk_budget_spec_summary.json",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("missing required risk budget inputs: " + "; ".join(missing))

    config = _read_json(root / CONFIG_PATH)
    official_summary = _read_json(root / BASELINE_DIR / "summary.json")
    original_signals = read_csv_rows(root / ORIGINAL_SIGNALS)
    sleeve_daily = read_csv_rows(root / ATTRIBUTION_DIR / "v57f_core_sleeve_daily_returns.csv")

    equal_signals = out_dir / "v5c_risk_budget_equal_reference_signals.csv"
    erc_signals = out_dir / "v5c_erc_fixed_covariance_signals.csv"
    vol_cap_signals = out_dir / "v5c_volatility_cap_reducer_signals.csv"
    shutil.copyfile(root / ORIGINAL_SIGNALS, equal_signals)
    erc_audit = _write_erc_signals(original_signals, sleeve_daily, erc_signals)
    vol_cap_audit = _write_vol_cap_signals(original_signals, sleeve_daily, vol_cap_signals)

    variants = [
        ("equal_reference", "v5c_risk_budget_equal_reference", equal_signals),
        ("erc_fixed_covariance", "v5c_erc_fixed_covariance_120d_floor15_cap35_max5pp", erc_signals),
        ("volatility_cap_reducer", "v5c_vol_cap_reducer_120d_125x_median_cut3pp", vol_cap_signals),
    ]
    output_index: list[dict[str, Any]] = []
    summaries: dict[str, dict[str, Any]] = {}
    for variant_id, project, signals_path in variants:
        config_path = _write_config_copy(root, config, project)
        result = run_basket_daily_backtest(config_path=config_path, signals_csv=signals_path, out_dir=run_dir)
        summaries[variant_id] = _read_json(result.summary_path)
        output_index.append(
            {
                "variant_id": variant_id,
                "summary": str(result.summary_path),
                "daily_returns": str(result.daily_returns_path),
                "holdings": str(result.holdings_path),
                "trades": str(result.trades_path),
                "dividends": str(result.dividends_path),
                "rebalance_order_health": str(result.order_health_path),
                "signals": str(signals_path),
            }
        )

    risk_rows = _build_variant_risk_rows(root, config, output_index, official_summary)
    comparison_rows = _build_comparison_rows(official_summary, summaries, risk_rows)
    order_health_rows = _build_order_health_rows(summaries)
    blockers = _build_blockers()
    pm_decision = _pm_decision(comparison_rows, order_health_rows)

    write_csv_rows(out_dir / "v5c_risk_budget_signal_generation_audit.csv", _fieldnames(erc_audit + vol_cap_audit), erc_audit + vol_cap_audit)
    write_csv_rows(out_dir / "v5c_risk_budget_engineering_comparison.csv", _fieldnames(comparison_rows), comparison_rows)
    write_csv_rows(out_dir / "v5c_risk_budget_order_health.csv", _fieldnames(order_health_rows), order_health_rows)
    write_csv_rows(out_dir / "v5c_risk_budget_risk_contribution_comparison.csv", _fieldnames(risk_rows), risk_rows)
    write_csv_rows(out_dir / "v5c_risk_budget_output_index.csv", _fieldnames(output_index), output_index)
    write_csv_rows(out_dir / "v5c_risk_budget_engineering_blockers.csv", _fieldnames(blockers), blockers)

    summary = {
        "schema_version": 1,
        "project": "v5c_risk_budget_overlay_engineering_comparison",
        "status": "fixed_rule_engineering_completed_no_v57f_core_change",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "baseline_strategy_id": official_summary.get("strategy_id"),
        "window": official_summary.get("window"),
        "v57f_core_modified": False,
        "joinquant_started": False,
        "parameter_scan_started": False,
        "tested_specs": ["V5C_RB_001", "V5C_RB_002"],
        "deferred_specs": ["V5C_RB_003"],
        "pm_decision": pm_decision,
        "outputs": {
            "summary": str(out_dir / "v5c_risk_budget_engineering_summary.json"),
            "report": str(out_dir / "v5c_risk_budget_engineering_report.md"),
            "comparison": str(out_dir / "v5c_risk_budget_engineering_comparison.csv"),
            "order_health": str(out_dir / "v5c_risk_budget_order_health.csv"),
            "risk_contribution_comparison": str(out_dir / "v5c_risk_budget_risk_contribution_comparison.csv"),
            "signal_generation_audit": str(out_dir / "v5c_risk_budget_signal_generation_audit.csv"),
            "output_index": str(out_dir / "v5c_risk_budget_output_index.csv"),
            "blockers": str(out_dir / "v5c_risk_budget_engineering_blockers.csv"),
        },
    }
    write_json_file(out_dir / "v5c_risk_budget_engineering_summary.json", summary)
    (out_dir / "v5c_risk_budget_engineering_report.md").write_text(
        _build_report(summary, comparison_rows, order_health_rows, risk_rows, blockers),
        encoding="utf-8",
    )
    return summary


def _write_erc_signals(original_signals: list[dict[str, str]], sleeve_daily: list[dict[str, str]], path: Path) -> list[dict[str, Any]]:
    daily_by_date = {str(row["trade_date"])[:10]: row for row in sleeve_daily}
    all_dates = sorted(daily_by_date)
    signal_groups = _group_signals(original_signals)
    previous_weights = {sleeve: 0.25 for sleeve in CORE_SLEEVES}
    output_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    for day in sorted(signal_groups):
        prior_dates = [item for item in all_dates if item < day][-LOOKBACK_DAYS:]
        if len(prior_dates) < LOOKBACK_DAYS:
            target_weights = {sleeve: 0.25 for sleeve in CORE_SLEEVES}
            status = "insufficient_prior_history_use_equal"
        else:
            matrix = [
                [to_float(daily_by_date[d].get(f"{sleeve}_local_return")) or 0.0 for sleeve in CORE_SLEEVES]
                for d in prior_dates
            ]
            covariance = _covariance_matrix(matrix)
            raw = _erc_weights(covariance)
            bounded = _project_to_box(raw, [SLEEVE_FLOOR] * 4, [SLEEVE_CAP] * 4)
            lower = [max(SLEEVE_FLOOR, previous_weights[sleeve] - MAX_WEIGHT_CHANGE) for sleeve in CORE_SLEEVES]
            upper = [min(SLEEVE_CAP, previous_weights[sleeve] + MAX_WEIGHT_CHANGE) for sleeve in CORE_SLEEVES]
            target_list = _project_to_box(bounded, lower, upper)
            target_weights = {sleeve: target_list[i] for i, sleeve in enumerate(CORE_SLEEVES)}
            status = "erc_fixed_covariance"
        output_rows.extend(_apply_sleeve_weights(signal_groups[day], target_weights, "erc_fixed_covariance"))
        audit_rows.append(_audit_row(day, "V5C_RB_001", status, target_weights, previous_weights))
        previous_weights = target_weights
    write_csv_rows(path, _fieldnames(output_rows), output_rows)
    return audit_rows


def _write_vol_cap_signals(original_signals: list[dict[str, str]], sleeve_daily: list[dict[str, str]], path: Path) -> list[dict[str, Any]]:
    daily_by_date = {str(row["trade_date"])[:10]: row for row in sleeve_daily}
    all_dates = sorted(daily_by_date)
    signal_groups = _group_signals(original_signals)
    output_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    previous_weights = {sleeve: 0.25 for sleeve in CORE_SLEEVES}
    for day in sorted(signal_groups):
        prior_dates = [item for item in all_dates if item < day][-LOOKBACK_DAYS:]
        target_weights = {sleeve: 0.25 for sleeve in CORE_SLEEVES}
        status = "insufficient_prior_history_use_equal"
        flagged = ""
        if len(prior_dates) >= LOOKBACK_DAYS:
            vols = {}
            for sleeve in CORE_SLEEVES:
                returns = [to_float(daily_by_date[d].get(f"{sleeve}_local_return")) or 0.0 for d in prior_dates]
                vols[sleeve] = pstdev(returns) * math.sqrt(252) if len(returns) > 1 else 0.0
            ranked = sorted(vols, key=lambda item: vols[item], reverse=True)
            top = ranked[0]
            median_vol = (sorted(vols.values())[1] + sorted(vols.values())[2]) / 2.0
            if median_vol > 0 and vols[top] > VOL_CAP_RELATIVE_THRESHOLD * median_vol:
                target_weights[top] -= VOL_CAP_REDUCER
                receivers = [sleeve for sleeve in CORE_SLEEVES if sleeve != top]
                inv = {sleeve: 1.0 / max(vols[sleeve], 0.000001) for sleeve in receivers}
                inv_total = sum(inv.values())
                for sleeve in receivers:
                    target_weights[sleeve] += VOL_CAP_REDUCER * inv[sleeve] / inv_total
                target_list = _project_to_box([target_weights[sleeve] for sleeve in CORE_SLEEVES], [SLEEVE_FLOOR] * 4, [SLEEVE_CAP] * 4)
                target_weights = {sleeve: target_list[i] for i, sleeve in enumerate(CORE_SLEEVES)}
                flagged = top
                status = "vol_cap_reducer_triggered"
            else:
                status = "vol_cap_not_triggered"
        output_rows.extend(_apply_sleeve_weights(signal_groups[day], target_weights, "volatility_cap_reducer"))
        audit = _audit_row(day, "V5C_RB_002", status, target_weights, previous_weights)
        audit["flagged_sleeve"] = flagged
        audit_rows.append(audit)
        previous_weights = target_weights
    write_csv_rows(path, _fieldnames(output_rows), output_rows)
    return audit_rows


def _group_signals(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        day = str(row.get("trade_date") or "")[:10]
        if day:
            groups[day].append(row)
    return dict(groups)


def _apply_sleeve_weights(rows: list[dict[str, str]], sleeve_weights: dict[str, float], scheme: str) -> list[dict[str, Any]]:
    by_sleeve: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_sleeve[str(row.get("sector_id") or "")].append(row)
    output: list[dict[str, Any]] = []
    for sleeve in CORE_SLEEVES:
        sleeve_rows = by_sleeve.get(sleeve, [])
        original_total = sum(to_float(row.get("target_weight")) or 0.0 for row in sleeve_rows)
        for row in sleeve_rows:
            original_weight = to_float(row.get("target_weight")) or 0.0
            copied = dict(row)
            copied["target_weight"] = sleeve_weights[sleeve] * original_weight / original_total if original_total > 0 else 0.0
            copied["risk_budget_scheme"] = scheme
            copied["target_sleeve_weight"] = sleeve_weights[sleeve]
            output.append(copied)
    return output


def _audit_row(day: str, spec_id: str, status: str, target_weights: dict[str, float], previous_weights: dict[str, float]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "trade_date": day,
        "spec_id": spec_id,
        "status": status,
        "assigned_total_weight": sum(target_weights.values()),
        "max_abs_change_vs_previous": max(abs(target_weights[s] - previous_weights[s]) for s in CORE_SLEEVES),
    }
    for sleeve in CORE_SLEEVES:
        row[f"{sleeve}_target_weight"] = target_weights[sleeve]
    return row


def _erc_weights(covariance: list[list[float]]) -> list[float]:
    n = len(covariance)
    vols = [math.sqrt(max(covariance[i][i], 0.0)) for i in range(n)]
    if any(vol <= 0 for vol in vols):
        return [1.0 / n] * n
    weights = _project_to_box([1.0 / vol for vol in vols], [SLEEVE_FLOOR] * n, [SLEEVE_CAP] * n)
    for _ in range(500):
        sigma_w = _mat_vec(covariance, weights)
        variance = sum(weights[i] * sigma_w[i] for i in range(n))
        if variance <= 0:
            break
        risk_contrib = [weights[i] * sigma_w[i] / variance for i in range(n)]
        updated = []
        for i, weight in enumerate(weights):
            rc = max(risk_contrib[i], 0.000001)
            updated.append(weight * math.sqrt((1.0 / n) / rc))
        next_weights = _project_to_box(updated, [SLEEVE_FLOOR] * n, [SLEEVE_CAP] * n)
        if max(abs(next_weights[i] - weights[i]) for i in range(n)) < 1e-8:
            weights = next_weights
            break
        weights = next_weights
    return weights


def _project_to_box(values: list[float], lower: list[float], upper: list[float]) -> list[float]:
    weights = [min(upper[i], max(lower[i], values[i])) for i in range(len(values))]
    for _ in range(100):
        residual = 1.0 - sum(weights)
        if abs(residual) < 1e-12:
            break
        if residual > 0:
            free = [i for i, weight in enumerate(weights) if weight < upper[i] - 1e-12]
            if not free:
                break
            add = residual / len(free)
            for i in free:
                weights[i] = min(upper[i], weights[i] + add)
        else:
            free = [i for i, weight in enumerate(weights) if weight > lower[i] + 1e-12]
            if not free:
                break
            sub = (-residual) / len(free)
            for i in free:
                weights[i] = max(lower[i], weights[i] - sub)
    total = sum(weights)
    return [weight / total for weight in weights] if total else [1.0 / len(values)] * len(values)


def _covariance_matrix(matrix: list[list[float]]) -> list[list[float]]:
    n = len(matrix)
    cols = len(matrix[0])
    means = [mean(row[i] for row in matrix) for i in range(cols)]
    cov = [[0.0 for _ in range(cols)] for _ in range(cols)]
    denom = max(n - 1, 1)
    for i in range(cols):
        for j in range(cols):
            cov[i][j] = sum((row[i] - means[i]) * (row[j] - means[j]) for row in matrix) / denom
    return cov


def _mat_vec(matrix: list[list[float]], vector: list[float]) -> list[float]:
    return [sum(row[i] * vector[i] for i in range(len(vector))) for row in matrix]


def _write_config_copy(root: Path, config: dict[str, Any], project: str) -> Path:
    copied = dict(config)
    copied["project"] = project
    copied["experiment_layer"] = "v5c_fixed_rule_risk_budget_engineering_diagnostic"
    copied["governance"] = dict(copied.get("governance") or {})
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


def _build_variant_risk_rows(root: Path, config: dict[str, Any], output_index: list[dict[str, Any]], official_summary: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    window = (official_summary or {}).get("window", {})
    start_date = str(window.get("start_date") or config.get("portfolio", {}).get("start_date") or "2021-05-01")
    end_date = str(window.get("end_date") or config.get("portfolio", {}).get("end_date") or "2026-05-31")
    price_files = [root / Path(str(sector["price_csv"])) for sector in config.get("sectors", []) if sector.get("price_csv")]
    dividend_files = [root / Path(str(sector["dividend_csv"])) for sector in config.get("sectors", []) if sector.get("dividend_csv")]
    prices_by_date = _load_prices(price_files, start_date, end_date)
    actions_by_date = _load_corporate_actions(dividend_files, start_date, end_date)
    rows: list[dict[str, Any]] = []
    for item in output_index:
        daily_rows = read_csv_rows(Path(str(item["daily_returns"])))
        trade_rows = read_csv_rows(Path(str(item["trades"])))
        signal_rows = read_csv_rows(Path(str(item["signals"])))
        summary = _read_json(Path(str(item["summary"])))
        signal_map = _build_signal_sector_map(signal_rows)
        latest = _build_latest_signal_day_by_date([row["trade_date"] for row in daily_rows], signal_map)
        attribution = _replay_sleeve_books(
            daily_rows=daily_rows,
            trade_rows=trade_rows,
            prices_by_date=prices_by_date,
            actions_by_date=actions_by_date,
            signal_sector_by_day_code=signal_map,
            latest_signal_day_by_date=latest,
            initial_cash=float(summary.get("execution", {}).get("initial_cash") or 2_000_000.0),
        )
        risk = _build_risk_contribution_rows(attribution["daily_wide"])
        drawdown = _build_drawdown_contribution_rows(attribution["daily_wide"], daily_rows, summary)
        drawdown_by_sleeve = {row["sleeve_id"]: row for row in drawdown}
        for row in risk:
            copied = dict(row)
            copied["variant_id"] = item["variant_id"]
            copied["drawdown_pnl_contribution"] = drawdown_by_sleeve[row["sleeve_id"]]["pnl_contribution"]
            copied["drawdown_pnl_share"] = drawdown_by_sleeve[row["sleeve_id"]]["share_of_interval_sleeve_pnl"]
            rows.append(copied)
    return rows


def _build_comparison_rows(
    official_summary: dict[str, Any],
    summaries: dict[str, dict[str, Any]],
    risk_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    equal = summaries["equal_reference"]
    equal_metrics = equal.get("metrics", {})
    risk_by_variant = _risk_summary_by_variant(risk_rows)
    rows = [
        _comparison_row("v57f_official_frozen_baseline", official_summary, official_summary.get("metrics", {}), "", "", "", "official_frozen_reference"),
    ]
    for variant_id in ["equal_reference", "erc_fixed_covariance", "volatility_cap_reducer"]:
        summary = summaries[variant_id]
        metrics = summary.get("metrics", {})
        rows.append(
            _comparison_row(
                variant_id,
                summary,
                metrics,
                (to_float(metrics.get("strategy_return")) or 0.0) - (to_float(equal_metrics.get("strategy_return")) or 0.0),
                (to_float(metrics.get("max_drawdown")) or 0.0) - (to_float(equal_metrics.get("max_drawdown")) or 0.0),
                risk_by_variant.get(variant_id, {}).get("covariance_risk_hhi_delta_vs_equal", ""),
                _variant_conclusion(variant_id, summary, metrics, equal_metrics, risk_by_variant),
            )
        )
    return rows


def _comparison_row(
    variant_id: str,
    summary: dict[str, Any],
    metrics: dict[str, Any],
    delta_return: Any,
    delta_drawdown: Any,
    delta_risk_hhi: Any,
    conclusion: str,
) -> dict[str, Any]:
    return {
        "variant_id": variant_id,
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
        "rebalance_needs_review": summary.get("rebalance_order_health", {}).get("needs_review"),
        "delta_return_vs_equal_reference": delta_return,
        "delta_max_drawdown_vs_equal_reference": delta_drawdown,
        "delta_covariance_risk_hhi_vs_equal_reference": delta_risk_hhi,
        "pm_conclusion": conclusion,
    }


def _risk_summary_by_variant(risk_rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in risk_rows:
        grouped[str(row["variant_id"])].append(row)
    result = {}
    equal_hhi = None
    for variant_id, rows in grouped.items():
        shares = [to_float(row.get("covariance_portfolio_variance_contribution")) or 0.0 for row in rows]
        hhi = sum(share * share for share in shares)
        result[variant_id] = {"covariance_risk_hhi": hhi}
        if variant_id == "equal_reference":
            equal_hhi = hhi
    if equal_hhi is not None:
        for item in result.values():
            item["covariance_risk_hhi_delta_vs_equal"] = item["covariance_risk_hhi"] - equal_hhi
    return result


def _variant_conclusion(
    variant_id: str,
    summary: dict[str, Any],
    metrics: dict[str, Any],
    equal_metrics: dict[str, Any],
    risk_by_variant: dict[str, dict[str, float]],
) -> str:
    if variant_id == "equal_reference":
        return "equal_reference_for_engineering_comparison"
    if summary.get("rebalance_order_health", {}).get("needs_review"):
        return "blocked_by_order_health"
    delta_return = (to_float(metrics.get("strategy_return")) or 0.0) - (to_float(equal_metrics.get("strategy_return")) or 0.0)
    delta_dd = (to_float(metrics.get("max_drawdown")) or 0.0) - (to_float(equal_metrics.get("max_drawdown")) or 0.0)
    delta_hhi = risk_by_variant.get(variant_id, {}).get("covariance_risk_hhi_delta_vs_equal", 0.0)
    if delta_hhi < -0.001 and delta_dd <= 0.0001 and delta_return >= 0:
        return "effective_risk_budget_diagnostic_needs_pm_quant_review_not_accepted"
    if delta_hhi < -0.001 and delta_dd <= 0.0001 and delta_return > -0.08:
        return "effective_risk_budget_diagnostic_needs_pm_quant_review_not_accepted"
    if delta_dd < 0 and delta_return > -0.05:
        return "drawdown_improved_with_acceptable_return_cost_needs_review"
    if delta_hhi < 0:
        return "risk_concentration_reduced_but_return_or_drawdown_cost_high"
    return "no_effective_improvement_diagnostic_only"


def _build_order_health_rows(summaries: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for variant_id, summary in summaries.items():
        row = {"variant_id": variant_id}
        row.update(summary.get("rebalance_order_health", {}))
        rows.append(row)
    return rows


def _pm_decision(comparison_rows: list[dict[str, Any]], order_health_rows: list[dict[str, Any]]) -> str:
    if any(str(row.get("needs_review")).lower() == "true" for row in order_health_rows):
        return "blocked_by_order_health_review"
    for row in comparison_rows:
        if row["pm_conclusion"] == "effective_risk_budget_diagnostic_needs_pm_quant_review_not_accepted":
            return f"{row['variant_id']} is effective diagnostic; promote to PM/Quant review only, not V57f replacement"
    return "no_fixed_risk_budget_variant_effective_enough; keep V57f frozen"


def _build_blockers() -> list[dict[str, str]]:
    return [
        {
            "blocked_item": "v57f_core_replacement",
            "reason": "Any risk budget overlay changes allocation behavior and cannot rewrite frozen V57f without a new PM gate.",
            "allowed_next_action": "PM/Quant review only if fixed diagnostic improves risk with acceptable return cost.",
        },
        {
            "blocked_item": "parameter_scan",
            "reason": "Changing lookback, floor, cap, max-change, relative-vol threshold or reducer after seeing results would overfit.",
            "allowed_next_action": "Freeze or reject the current fixed specs; do not tune.",
        },
        {
            "blocked_item": "drawdown_contribution_reducer",
            "reason": "Needs a prior-only boundary memo before engineering; historical max drawdown leader cannot be used directly.",
            "allowed_next_action": "PM rule-boundary memo only.",
        },
    ]


def _build_report(
    summary: dict[str, Any],
    comparison_rows: list[dict[str, Any]],
    order_health_rows: list[dict[str, Any]],
    risk_rows: list[dict[str, Any]],
    blockers: list[dict[str, str]],
) -> str:
    lines = [
        "# V5c Fixed Risk Budget Overlay Engineering Comparison",
        "",
        "This packet runs only the fixed ERC and fixed volatility-cap specs admitted by PM. It does not modify V57f, scan parameters, add sleeves, or start JoinQuant.",
        "",
        "## Comparison",
        "",
        "| Variant | Return | Max DD | Vol | Trades | Order health | Delta return | Delta DD | Delta risk HHI | PM conclusion |",
        "|---|---:|---:|---:|---:|---|---:|---:|---:|---|",
    ]
    for row in comparison_rows:
        lines.append(
            f"| {row['variant_id']} | {_pct(row['strategy_return'])} | {_pct(row['max_drawdown'])} | "
            f"{_pct(row['strategy_volatility'])} | {row['trade_count']} | "
            f"{'needs_review' if str(row['rebalance_needs_review']).lower() == 'true' else 'pass'} | "
            f"{_pct(row['delta_return_vs_equal_reference'])} | {_pct(row['delta_max_drawdown_vs_equal_reference'])} | "
            f"{_num(row['delta_covariance_risk_hhi_vs_equal_reference'])} | {row['pm_conclusion']} |"
        )
    lines.extend(["", "## Risk Budget Snapshot", ""])
    for variant_id in ["equal_reference", "erc_fixed_covariance", "volatility_cap_reducer"]:
        variant_rows = [row for row in risk_rows if row["variant_id"] == variant_id]
        lines.append(f"### {variant_id}")
        lines.append("")
        lines.append("| Sleeve | Covariance risk contribution | Avg weight | DD loss share |")
        lines.append("|---|---:|---:|---:|")
        for row in variant_rows:
            lines.append(
                f"| {row['sleeve_id']} | {_pct(row['covariance_portfolio_variance_contribution'])} | "
                f"{_pct(row['average_weight'])} | {_pct(row['drawdown_pnl_share'])} |"
            )
        lines.append("")
    lines.extend(["## Order Health", ""])
    for row in order_health_rows:
        lines.append(f"- `{row['variant_id']}`: needs_review `{row.get('needs_review')}`, normal `{row.get('normal_rebalance_count')}/{row.get('rebalance_signal_count')}`")
    lines.extend(["", "## PM Decision", "", summary["pm_decision"], "", "## Still Blocked", ""])
    for row in blockers:
        lines.append(f"- `{row['blocked_item']}`: {row['reason']}")
    return "\n".join(lines) + "\n"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    return fields


def _pct(value: Any) -> str:
    number = to_float(value)
    return "" if number is None else f"{number:.2%}"


def _num(value: Any) -> str:
    number = to_float(value)
    return "" if number is None else f"{number:.6f}"


if __name__ == "__main__":
    run_v5c_risk_budget_overlay_engineering(Path("."))

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from v5.v5c_profit_taking_overheat_runner import (
    BASELINE_DIR,
    CONFIG_PATH,
    _annualized_vol,
    _build_close_matrix,
    _build_rebalance_targets,
    _build_sector_reference_returns,
    _compute_metrics,
    _nav_series,
    _read_csv,
    _read_json,
    _read_price_rows,
    _to_float,
    _write_csv,
    _write_json,
)


OUT_DIR = Path("v5c_sleeve_weighting_diagnostic") / "current"
SECTOR_ORDER = [
    "bank",
    "utilities_electricity",
    "highway_infrastructure",
    "port_rail_infrastructure",
]
SINGLE_STOCK_CAP = 0.05


def run_v5c_sleeve_weighting_diagnostic(root: Path) -> dict[str, Any]:
    baseline_dir = root / BASELINE_DIR
    out_dir = root / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    config = _read_json(root / CONFIG_PATH)
    baseline_summary = _read_json(baseline_dir / "summary.json")
    daily_rows = _read_csv(baseline_dir / "daily_returns.csv")
    holding_rows = _read_csv(baseline_dir / "holdings.csv")
    signal_rows = _read_csv(baseline_dir / "rebalance_signals.csv")
    price_rows = _read_price_rows(root, config)

    dates = [row["trade_date"] for row in daily_rows]
    official_returns = [_to_float(row.get("strategy_return")) for row in daily_rows]
    benchmark_returns = [_to_float(row.get("benchmark_return")) for row in daily_rows]
    official_metrics = _compute_metrics(official_returns, benchmark_returns, [1.0] * len(dates), dates)

    codes = sorted({row["code"] for row in holding_rows})
    sector_by_date_code = {
        (row["trade_date"], row["code"]): row.get("sector_id", "") for row in signal_rows
    }
    rebalances = _build_rebalance_targets(holding_rows, sector_by_date_code)
    close_by_code = _build_close_matrix(dates, codes, price_rows)
    sector_reference_returns = _build_sector_reference_returns(dates, rebalances, close_by_code)

    schemes = _scheme_rows()
    _write_prompt(out_dir)
    _write_csv(out_dir / "v5c_sleeve_weighting_scheme_spec.csv", schemes)
    _write_csv(out_dir / "v5c_sleeve_weighting_flow_table.csv", _flow_rows())

    comparison_rows = [
        {
            "scheme_id": "v57f_official_frozen_baseline",
            "scheme_type": "official",
            "scheme_description": "Official frozen V57f local daily output. Reference only, not overwritten by diagnostics.",
            "bank_weight": "",
            "utilities_electricity_weight": "",
            "highway_infrastructure_weight": "",
            "port_rail_infrastructure_weight": "",
            **official_metrics,
            "average_cash_weight": _average_cash_weight(daily_rows),
            "estimated_rebalance_commission": "",
            "delta_return_vs_equal_reconstructed": "",
            "delta_max_drawdown_vs_equal_reconstructed": "",
            "pm_conclusion": "frozen_reference_not_replaced",
        }
    ]
    all_daily_rows: list[dict[str, Any]] = []
    weight_rows: list[dict[str, Any]] = []
    equal_metrics: dict[str, Any] | None = None

    for scheme in schemes:
        sim = _simulate_scheme(
            scheme=scheme,
            dates=dates,
            daily_rows=daily_rows,
            rebalances=rebalances,
            close_by_code=close_by_code,
            benchmark_returns=benchmark_returns,
            sector_reference_returns=sector_reference_returns,
        )
        if scheme["scheme_id"] == "equal_25_each_reconstructed":
            equal_metrics = sim["metrics"]
        delta_return = "" if equal_metrics is None else sim["metrics"]["strategy_return"] - equal_metrics["strategy_return"]
        delta_dd = "" if equal_metrics is None else sim["metrics"]["max_drawdown"] - equal_metrics["max_drawdown"]
        comparison_rows.append(
            {
                "scheme_id": scheme["scheme_id"],
                "scheme_type": scheme["scheme_type"],
                "scheme_description": scheme["scheme_description"],
                "bank_weight": scheme["bank_weight"],
                "utilities_electricity_weight": scheme["utilities_electricity_weight"],
                "highway_infrastructure_weight": scheme["highway_infrastructure_weight"],
                "port_rail_infrastructure_weight": scheme["port_rail_infrastructure_weight"],
                **sim["metrics"],
                "average_cash_weight": sim["average_cash_weight"],
                "estimated_rebalance_commission": sim["estimated_rebalance_commission"],
                "delta_return_vs_equal_reconstructed": delta_return,
                "delta_max_drawdown_vs_equal_reconstructed": delta_dd,
                "pm_conclusion": _pm_conclusion(scheme, sim["metrics"], equal_metrics),
            }
        )
        all_daily_rows.extend(sim["daily_rows"])
        weight_rows.extend(sim["weight_rows"])

    blocked_rows = [
        {
            "blocked_item": "accept_non_equal_sleeve_weight_as_v57f_replacement",
            "reason": "This diagnostic changes sleeve allocation, so it cannot rewrite frozen V57f without a new PM admission and forward evidence.",
            "allowed_next_action": "Quant/PM review only; keep V57f official equal-sleeve baseline frozen",
        },
        {
            "blocked_item": "optimize_sleeve_weights_by_2021_2026_return",
            "reason": "Historical return ranking would overfit the frozen V5 evidence window.",
            "allowed_next_action": "Use predeclared coarse schemes and future paper evidence only",
        },
    ]

    _write_csv(out_dir / "v5c_sleeve_weighting_engineering_comparison.csv", comparison_rows)
    _write_csv(out_dir / "v5c_sleeve_weighting_daily_nav.csv", all_daily_rows)
    _write_csv(out_dir / "v5c_sleeve_weighting_rebalance_weights.csv", weight_rows)
    _write_csv(out_dir / "v5c_sleeve_weighting_blockers.csv", blocked_rows)
    _write_report(out_dir, baseline_summary, comparison_rows, blocked_rows)

    summary = {
        "schema_version": 1,
        "project": "v5c_sleeve_weighting_diagnostic",
        "status": "engineering_diagnostic_completed_no_v57f_core_change",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_strategy_id": baseline_summary.get("strategy_id"),
        "window": baseline_summary.get("window"),
        "v57f_core_modified": False,
        "joinquant_started": False,
        "scheme_count": len(schemes),
        "backtest_type": "close_to_close_diagnostic_reconstruction_from_frozen_v57f_signals_with_alternative_sleeve_weights",
        "pm_decision": "diagnostic_only; do not replace V57f equal-sleeve freeze by historical ranking",
        "outputs": {
            "prompt": str(out_dir / "00_v5c_sleeve_weighting_diagnostic_prompt.md"),
            "flow_table": str(out_dir / "v5c_sleeve_weighting_flow_table.csv"),
            "scheme_spec": str(out_dir / "v5c_sleeve_weighting_scheme_spec.csv"),
            "comparison": str(out_dir / "v5c_sleeve_weighting_engineering_comparison.csv"),
            "daily_nav": str(out_dir / "v5c_sleeve_weighting_daily_nav.csv"),
            "rebalance_weights": str(out_dir / "v5c_sleeve_weighting_rebalance_weights.csv"),
            "blockers": str(out_dir / "v5c_sleeve_weighting_blockers.csv"),
            "report": str(out_dir / "v5c_sleeve_weighting_report.md"),
            "summary": str(out_dir / "v5c_sleeve_weighting_summary.json"),
        },
    }
    _write_json(out_dir / "v5c_sleeve_weighting_summary.json", summary)
    return summary


def _scheme_rows() -> list[dict[str, Any]]:
    return [
        {
            "scheme_id": "equal_25_each_reconstructed",
            "scheme_type": "static",
            "scheme_description": "25% each sleeve, reconstructed close-to-close reference for apples-to-apples comparison.",
            "bank_weight": 0.25,
            "utilities_electricity_weight": 0.25,
            "highway_infrastructure_weight": 0.25,
            "port_rail_infrastructure_weight": 0.25,
        },
        {
            "scheme_id": "bank_light_equal_nonfinancial_10_30_30_30",
            "scheme_type": "static",
            "scheme_description": "Bank underweight, equal nonfinancial cashflow sleeves.",
            "bank_weight": 0.10,
            "utilities_electricity_weight": 0.30,
            "highway_infrastructure_weight": 0.30,
            "port_rail_infrastructure_weight": 0.30,
        },
        {
            "scheme_id": "utilities_tilt_15_35_25_25",
            "scheme_type": "static",
            "scheme_description": "Tilt toward utilities electricity as the most cashflow-infrastructure-like sleeve.",
            "bank_weight": 0.15,
            "utilities_electricity_weight": 0.35,
            "highway_infrastructure_weight": 0.25,
            "port_rail_infrastructure_weight": 0.25,
        },
        {
            "scheme_id": "transport_infra_tilt_20_20_30_30",
            "scheme_type": "static",
            "scheme_description": "Tilt toward highway and port/rail infrastructure.",
            "bank_weight": 0.20,
            "utilities_electricity_weight": 0.20,
            "highway_infrastructure_weight": 0.30,
            "port_rail_infrastructure_weight": 0.30,
        },
        {
            "scheme_id": "bank_utilities_barbell_30_35_175_175",
            "scheme_type": "static",
            "scheme_description": "Bank plus utilities barbell, lower transport infrastructure weight.",
            "bank_weight": 0.30,
            "utilities_electricity_weight": 0.35,
            "highway_infrastructure_weight": 0.175,
            "port_rail_infrastructure_weight": 0.175,
        },
        {
            "scheme_id": "dynamic_inverse_vol_60d_floor15_cap35",
            "scheme_type": "dynamic_pit",
            "scheme_description": "At each scheduled rebalance, use prior 60 trading-day sleeve volatility inverse weights, clipped at 15%-35%. Equal weight until enough prior data exists.",
            "bank_weight": "dynamic",
            "utilities_electricity_weight": "dynamic",
            "highway_infrastructure_weight": "dynamic",
            "port_rail_infrastructure_weight": "dynamic",
        },
    ]


def _simulate_scheme(
    *,
    scheme: dict[str, Any],
    dates: list[str],
    daily_rows: list[dict[str, str]],
    rebalances: dict[str, list[dict[str, Any]]],
    close_by_code: dict[str, list[float | None]],
    benchmark_returns: list[float],
    sector_reference_returns: dict[str, list[float]],
) -> dict[str, Any]:
    positions: dict[str, int] = {}
    code_sector: dict[str, str] = {}
    cash = _to_float(daily_rows[0].get("portfolio_value"))
    previous_value: float | None = None
    returns: list[float] = []
    exposures: list[float] = []
    cash_weights: list[float] = []
    daily_out: list[dict[str, Any]] = []
    weight_rows: list[dict[str, Any]] = []
    estimated_commission = 0.0

    for idx, date in enumerate(dates):
        prices = {code: series[idx] for code, series in close_by_code.items() if series[idx] is not None}
        if date in rebalances:
            current_value = _portfolio_value(positions, cash, prices)
            if previous_value is None:
                current_value = _to_float(daily_rows[idx].get("portfolio_value"))
            sector_weights = _sector_weights_for_scheme(scheme, idx, sector_reference_returns)
            target_positions, turnover, missing_cash = _target_positions(
                current_value=current_value,
                target_rows=rebalances[date],
                sector_weights=sector_weights,
                prices=prices,
                previous_positions=positions,
            )
            commission = turnover * 0.0003
            estimated_commission += commission
            positions = target_positions
            code_sector = {row["code"]: row["sector_id"] for row in rebalances[date]}
            cash = max(0.0, current_value - _invested_value(positions, prices) - commission + missing_cash)
            for sector_id in SECTOR_ORDER:
                weight_rows.append(
                    {
                        "trade_date": date,
                        "scheme_id": scheme["scheme_id"],
                        "sector_id": sector_id,
                        "target_sector_weight": sector_weights[sector_id],
                        "selected_count": sum(1 for row in rebalances[date] if row["sector_id"] == sector_id),
                    }
                )

        cash += _scaled_dividend_cash(daily_rows[idx], positions, prices)
        value = _portfolio_value(positions, cash, prices)
        ret = 0.0 if previous_value is None or previous_value == 0 else value / previous_value - 1
        returns.append(ret)
        invested = _invested_value(positions, prices)
        exposure = invested / value if value else 0.0
        cash_weight = cash / value if value else 0.0
        exposures.append(exposure)
        cash_weights.append(cash_weight)
        previous_value = value
        daily_out.append(
            {
                "trade_date": date,
                "scheme_id": scheme["scheme_id"],
                "strategy_return": ret,
                "strategy_nav": _nav_series(returns)[-1],
                "benchmark_return": benchmark_returns[idx],
                "portfolio_value": value,
                "cash": cash,
                "cash_weight": cash_weight,
                "exposure": exposure,
            }
        )

    metrics = _compute_metrics(returns, benchmark_returns, exposures, dates)
    return {
        "metrics": metrics,
        "daily_rows": daily_out,
        "weight_rows": weight_rows,
        "average_cash_weight": mean(cash_weights) if cash_weights else 0.0,
        "estimated_rebalance_commission": estimated_commission,
    }


def _sector_weights_for_scheme(
    scheme: dict[str, Any],
    date_idx: int,
    sector_reference_returns: dict[str, list[float]],
) -> dict[str, float]:
    if scheme["scheme_type"] != "dynamic_pit":
        return {
            "bank": float(scheme["bank_weight"]),
            "utilities_electricity": float(scheme["utilities_electricity_weight"]),
            "highway_infrastructure": float(scheme["highway_infrastructure_weight"]),
            "port_rail_infrastructure": float(scheme["port_rail_infrastructure_weight"]),
        }
    if date_idx < 60:
        return {sector_id: 0.25 for sector_id in SECTOR_ORDER}
    vols: dict[str, float] = {}
    for sector_id in SECTOR_ORDER:
        series = sector_reference_returns.get(sector_id, [])
        vols[sector_id] = _annualized_vol(series[date_idx - 60:date_idx])
    inv = {sector_id: 1 / max(vols[sector_id], 0.01) for sector_id in SECTOR_ORDER}
    total_inv = sum(inv.values())
    raw = {sector_id: inv[sector_id] / total_inv for sector_id in SECTOR_ORDER}
    clipped = {sector_id: min(0.35, max(0.15, raw[sector_id])) for sector_id in SECTOR_ORDER}
    total = sum(clipped.values())
    return {sector_id: clipped[sector_id] / total for sector_id in SECTOR_ORDER}


def _target_positions(
    *,
    current_value: float,
    target_rows: list[dict[str, Any]],
    sector_weights: dict[str, float],
    prices: dict[str, float],
    previous_positions: dict[str, int],
) -> tuple[dict[str, int], float, float]:
    by_sector: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in target_rows:
        by_sector[row["sector_id"]].append(row)
    target_positions: dict[str, int] = {}
    missing_cash = 0.0
    for sector_id, rows in by_sector.items():
        selected_count = len(rows)
        if selected_count <= 0:
            continue
        raw_weight = sector_weights.get(sector_id, 0.0) / selected_count
        stock_weight = min(raw_weight, SINGLE_STOCK_CAP)
        if raw_weight > SINGLE_STOCK_CAP:
            missing_cash += (raw_weight - SINGLE_STOCK_CAP) * selected_count * current_value
        for row in rows:
            code = row["code"]
            price = prices.get(code)
            if not price or price <= 0:
                continue
            amount = int((current_value * stock_weight / price) // 100 * 100)
            if amount > 0:
                target_positions[code] = amount
    turnover = 0.0
    for code in set(previous_positions) | set(target_positions):
        price = prices.get(code)
        if not price:
            continue
        turnover += abs(target_positions.get(code, 0) - previous_positions.get(code, 0)) * price
    return target_positions, turnover, missing_cash


def _invested_value(positions: dict[str, int], prices: dict[str, float]) -> float:
    return sum(amount * prices.get(code, 0.0) for code, amount in positions.items())


def _portfolio_value(positions: dict[str, int], cash: float, prices: dict[str, float]) -> float:
    return cash + _invested_value(positions, prices)


def _scaled_dividend_cash(row: dict[str, str], positions: dict[str, int], prices: dict[str, float]) -> float:
    dividend_cash = _to_float(row.get("dividend_cash"))
    if dividend_cash <= 0:
        return 0.0
    baseline_invested = _to_float(row.get("invested_value"))
    if baseline_invested <= 0:
        return dividend_cash
    current_invested = _invested_value(positions, prices)
    return dividend_cash * max(0.0, min(1.2, current_invested / baseline_invested))


def _average_cash_weight(daily_rows: list[dict[str, str]]) -> float:
    values = [_to_float(row.get("cash_weight")) for row in daily_rows]
    return mean(values) if values else 0.0


def _pm_conclusion(scheme: dict[str, Any], metrics: dict[str, Any], equal_metrics: dict[str, Any] | None) -> str:
    if equal_metrics is None or scheme["scheme_id"] == "equal_25_each_reconstructed":
        return "diagnostic_reference_not_strategy_candidate"
    return_delta = metrics["strategy_return"] - equal_metrics["strategy_return"]
    dd_delta = metrics["max_drawdown"] - equal_metrics["max_drawdown"]
    if return_delta > 0 and dd_delta <= 0:
        return "diagnostic_promising_requires_pm_quant_review_and_forward_evidence"
    if return_delta > 0:
        return "higher_return_with_drawdown_cost_not_accepted"
    if dd_delta < 0:
        return "lower_drawdown_with_return_cost_not_accepted"
    return "no_clear_improvement_not_accepted"


def _flow_rows() -> list[dict[str, str]]:
    return [
        {
            "step": "1",
            "stage": "freeze_guard",
            "action": "Keep V57f selected stocks, factors and rebalance dates frozen.",
            "output": "scope check",
            "blocked": "core strategy modification",
        },
        {
            "step": "2",
            "stage": "scheme_spec",
            "action": "Pre-register static and dynamic sleeve weighting schemes.",
            "output": "scheme spec",
            "blocked": "choose weights by best historical return",
        },
        {
            "step": "3",
            "stage": "local_diagnostic",
            "action": "Reconstruct close-to-close daily NAV for each scheme from frozen signals and prices.",
            "output": "comparison table",
            "blocked": "claim JoinQuant/platform replication",
        },
        {
            "step": "4",
            "stage": "pm_review",
            "action": "Compare return, drawdown, volatility, cash drag and governance risk.",
            "output": "PM diagnostic conclusion",
            "blocked": "replace V57f equal sleeve freeze without forward evidence",
        },
    ]


def _write_prompt(out_dir: Path) -> None:
    text = """# V5c Sleeve Weighting Diagnostic Prompt

Task: Test several non-equal sleeve weighting schemes without modifying V57f.

Rules:

1. Keep V57f stocks, factors, score logic and rebalance dates frozen.
2. Do not use historical return to optimize weights.
3. Use only pre-registered coarse sleeve weights or prior-data dynamic inverse volatility.
4. Do not start JoinQuant or claim platform replication.
5. Compare against the reconstructed equal-sleeve baseline for apples-to-apples diagnostics; keep official V57f as the frozen reference.
6. No scheme can become accepted strategy without PM/Quant review and future/paper evidence.
"""
    (out_dir / "00_v5c_sleeve_weighting_diagnostic_prompt.md").write_text(text, encoding="utf-8")


def _write_report(
    out_dir: Path,
    baseline_summary: dict[str, Any],
    comparison_rows: list[dict[str, Any]],
    blocked_rows: list[dict[str, str]],
) -> None:
    lines = [
        "# V5c Sleeve Weighting Diagnostic",
        "",
        "This diagnostic tests whether V57f core sleeves should remain equal-weighted. It does not modify frozen V57f.",
        "",
        f"- Baseline: `{baseline_summary.get('strategy_id')}`",
        f"- Window: `{baseline_summary.get('window', {}).get('start_date')}` to `{baseline_summary.get('window', {}).get('end_date')}`",
        "- JoinQuant started: `false`",
        "- V57f core modified: `false`",
        "",
        "## Comparison",
        "",
        "| Scheme | Return | Max Drawdown | Volatility | Avg Cash | Delta Return vs Equal Recon | Delta DD vs Equal Recon | PM Conclusion |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in comparison_rows:
        delta_ret = row.get("delta_return_vs_equal_reconstructed")
        delta_dd = row.get("delta_max_drawdown_vs_equal_reconstructed")
        delta_ret_text = "" if delta_ret == "" else f"{delta_ret:.2%}"
        delta_dd_text = "" if delta_dd == "" else f"{delta_dd:.2%}"
        lines.append(
            "| {scheme} | {ret:.2%} | {dd:.2%} | {vol:.2%} | {cash} | {dret} | {ddd} | {conclusion} |".format(
                scheme=row["scheme_id"],
                ret=row["strategy_return"],
                dd=row["max_drawdown"],
                vol=row["strategy_volatility"],
                cash="" if row["average_cash_weight"] == "" else f"{row['average_cash_weight']:.2%}",
                dret=delta_ret_text,
                ddd=delta_dd_text,
                conclusion=row["pm_conclusion"],
            )
        )
    lines.extend(["", "## PM Notes", ""])
    lines.append("- Official V57f remains the equal-sleeve frozen strategy. The reconstructed equal version is only the local close-to-close comparison baseline.")
    lines.append("- Schemes that look better historically are not accepted by default; they need forward/paper evidence and a separate admission gate.")
    lines.append("- Dynamic inverse-vol uses prior 60 trading-day sleeve returns only, so it is PIT-safe in this diagnostic, but still not accepted.")
    lines.extend(["", "## Blockers", ""])
    for row in blocked_rows:
        lines.append(f"- `{row['blocked_item']}`: {row['reason']}")
    (out_dir / "v5c_sleeve_weighting_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    result = run_v5c_sleeve_weighting_diagnostic(Path.cwd())
    print(json.dumps(result, ensure_ascii=False, indent=2))

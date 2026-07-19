from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from v5.basket_constructor_runner import construct_dividend_low_vol_fcf_basket
from v5.basket_daily_backtest_runner import run_basket_daily_backtest
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import compound, fmt_float, to_float


DEFAULT_CONFIG = Path("config/dividend_low_vol_fcf_basket_v56.json")
DEFAULT_OUT_DIR = Path("validation_ablation_v56_basket")


@dataclass(frozen=True)
class BasketAblationResult:
    output_dir: Path
    summary_path: Path
    report_path: Path
    case_count: int


def run_basket_ablation(
    config_path: Path = DEFAULT_CONFIG,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> BasketAblationResult:
    base_config = _read_json(config_path)
    project = str(base_config.get("project") or "v56_dividend_low_vol_fcf_shadow_basket")
    out = out_dir / project
    out.mkdir(parents=True, exist_ok=True)

    cases = _build_cases(base_config)
    result_rows = []
    for case_id, config in cases:
        case_dir = out / "cases" / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        config_path_case = case_dir / "config.json"
        write_json_file(config_path_case, config)
        try:
            construction = construct_dividend_low_vol_fcf_basket(config_path_case, case_dir / "constructor")
            daily = run_basket_daily_backtest(config_path_case, construction.signals_path, case_dir / "daily")
            summary = _read_json(daily.summary_path)
            metrics = summary.get("metrics", {})
            result_rows.append(
                {
                    "case": case_id,
                    "status": "completed",
                    "signal_count": summary.get("signal_count"),
                    "daily_count": summary.get("daily_count"),
                    "trade_count": summary.get("trade_count"),
                    "dividend_count": summary.get("dividend_count"),
                    "corporate_action_count": summary.get("corporate_action_count"),
                    "strategy_return": fmt_float(metrics.get("strategy_return")),
                    "annualized_return": fmt_float(metrics.get("annualized_return")),
                    "benchmark_return": fmt_float(metrics.get("benchmark_return")),
                    "excess_return": fmt_float(metrics.get("excess_return")),
                    "max_drawdown": fmt_float(metrics.get("max_drawdown")),
                    "sharpe": fmt_float(metrics.get("sharpe")),
                    "information_ratio": fmt_float(metrics.get("information_ratio")),
                    "strategy_volatility": fmt_float(metrics.get("strategy_volatility")),
                    "summary_path": str(daily.summary_path),
                    "signals_path": str(construction.signals_path),
                    "error": "",
                }
            )
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            result_rows.append(
                {
                    "case": case_id,
                    "status": "blocked",
                    "signal_count": "",
                    "daily_count": "",
                    "trade_count": "",
                    "dividend_count": "",
                    "corporate_action_count": "",
                    "strategy_return": "",
                    "annualized_return": "",
                    "benchmark_return": "",
                    "excess_return": "",
                    "max_drawdown": "",
                    "sharpe": "",
                    "information_ratio": "",
                    "strategy_volatility": "",
                    "summary_path": "",
                    "signals_path": "",
                    "error": str(exc),
                }
            )

    completed_rows = [row for row in result_rows if row.get("status") == "completed"]
    base = next((row for row in completed_rows if row["case"] == "base"), completed_rows[0] if completed_rows else result_rows[0])
    base_daily_path = Path(str(base["summary_path"])).parent / "daily_returns.csv"
    base_dates = [str(row.get("trade_date") or "")[:10] for row in read_csv_rows(base_daily_path)] if base_daily_path.exists() else []
    common_start = min(base_dates) if base_dates else ""
    common_end = max(base_dates) if base_dates else ""
    for row in result_rows:
        if row.get("status") != "completed":
            row["strategy_return_diff_vs_base"] = ""
            row["excess_return_diff_vs_base"] = ""
            row["max_drawdown_diff_vs_base"] = ""
            row["common_window_start"] = common_start
            row["common_window_end"] = common_end
            row["common_window_daily_count"] = ""
            row["common_window_strategy_return"] = ""
            row["common_window_benchmark_return"] = ""
            row["common_window_excess_return"] = ""
            row["common_window_max_drawdown"] = ""
            row["common_window_sharpe"] = ""
            row["common_window_strategy_return_diff_vs_base"] = ""
            row["common_window_excess_return_diff_vs_base"] = ""
            row["common_window_max_drawdown_diff_vs_base"] = ""
            row["comparable_to_base_window"] = "blocked"
            continue
        row["strategy_return_diff_vs_base"] = fmt_float((to_float(row["strategy_return"]) or 0.0) - (to_float(base["strategy_return"]) or 0.0))
        row["excess_return_diff_vs_base"] = fmt_float((to_float(row["excess_return"]) or 0.0) - (to_float(base["excess_return"]) or 0.0))
        row["max_drawdown_diff_vs_base"] = fmt_float((to_float(row["max_drawdown"]) or 0.0) - (to_float(base["max_drawdown"]) or 0.0))
        common_metrics = _metrics_for_window(Path(str(row["summary_path"])).parent / "daily_returns.csv", common_start, common_end)
        row["common_window_start"] = common_start
        row["common_window_end"] = common_end
        row["common_window_daily_count"] = common_metrics.get("daily_count", "")
        row["common_window_strategy_return"] = fmt_float(common_metrics.get("strategy_return"))
        row["common_window_benchmark_return"] = fmt_float(common_metrics.get("benchmark_return"))
        row["common_window_excess_return"] = fmt_float(common_metrics.get("excess_return"))
        row["common_window_max_drawdown"] = fmt_float(common_metrics.get("max_drawdown"))
        row["common_window_sharpe"] = fmt_float(common_metrics.get("sharpe"))

    base_common_return = to_float(base.get("common_window_strategy_return")) or 0.0
    base_common_excess = to_float(base.get("common_window_excess_return")) or 0.0
    base_common_dd = to_float(base.get("common_window_max_drawdown")) or 0.0
    for row in result_rows:
        if row.get("status") != "completed":
            continue
        row["common_window_strategy_return_diff_vs_base"] = fmt_float((to_float(row.get("common_window_strategy_return")) or 0.0) - base_common_return)
        row["common_window_excess_return_diff_vs_base"] = fmt_float((to_float(row.get("common_window_excess_return")) or 0.0) - base_common_excess)
        row["common_window_max_drawdown_diff_vs_base"] = fmt_float((to_float(row.get("common_window_max_drawdown")) or 0.0) - base_common_dd)
        row["comparable_to_base_window"] = "yes" if row.get("common_window_daily_count") == base.get("daily_count") else "needs_review"

    rows_path = out / "basket_ablation_results.csv"
    summary_path = out / "basket_ablation_summary.json"
    report_path = out / "basket_ablation_report.md"
    write_csv_rows(rows_path, _fieldnames(result_rows), result_rows)
    summary = {
        "schema_version": 1,
        "strategy_id": project,
        "experiment_layer": "research_pit_validation",
        "status": "basket_ablation_completed_not_acceptance",
        "config": str(config_path),
        "case_count": len(result_rows),
        "results_csv": str(rows_path),
        "common_window": {
            "policy": "All cases are additionally evaluated over the base case daily simulation window.",
            "start_date": common_start,
            "end_date": common_end,
            "base_daily_count": base.get("daily_count"),
        },
        "cases": result_rows,
        "pm_note": "Ablation re-runs basket construction and daily simulation. Use common-window metrics for factor decisions. It is still platform-confirmation evidence, not accepted-strategy proof.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_json_file(summary_path, summary)
    report_path.write_text(_report(summary), encoding="utf-8")
    return BasketAblationResult(out, summary_path, report_path, len(result_rows))


def _build_cases(base_config: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    cases = [("base", _case_config(base_config, "base"))]
    drop_factor_cases = [
        ("drop_low_pb", "low_price_to_book"),
        ("drop_div_yield", "dividend_yield"),
        ("drop_div_yield_decimal", "dividend_yield_decimal"),
        ("drop_fcf_yield", "free_cash_flow_yield"),
        ("drop_low_vol_score", "low_vol_score"),
        ("drop_vol_120d", "volatility_120d"),
        ("drop_mdd_120d", "max_drawdown_120d"),
        ("drop_ocf_yield", "operating_cash_flow_yield"),
    ]
    for case_id, factor in drop_factor_cases:
        cases.append((case_id, _drop_factor(base_config, case_id, factor)))
    cases.append(
        (
            "low_vol_ocf_only",
            _keep_factors(
                base_config,
                "low_vol_ocf_only",
                ["low_vol_score", "volatility_120d", "max_drawdown_120d", "operating_cash_flow_yield"],
                {"low_vol_score": 0.35, "volatility_120d": 0.2, "max_drawdown_120d": 0.2, "operating_cash_flow_yield": 0.25},
            ),
        )
    )
    cases.append(
        (
            "value_cashflow_no_low_vol",
            _keep_factors(
                base_config,
                "value_cashflow_no_low_vol",
                ["dividend_yield", "operating_cash_flow_yield", "free_cash_flow_yield", "low_price_to_book", "capex_burden"],
                {
                    "dividend_yield": 0.25,
                    "operating_cash_flow_yield": 0.25,
                    "free_cash_flow_yield": 0.2,
                    "low_price_to_book": 0.2,
                    "capex_burden": 0.1,
                },
            ),
        )
    )
    for cap in [0.25, 0.30, 0.40, 1.0]:
        case_id = f"sector_cap_{int(cap * 100)}"
        config = _case_config(base_config, case_id)
        config["portfolio"]["sector_weight_cap"] = cap
        cases.append((case_id, config))
    return cases


def _case_config(base_config: dict[str, Any], case_id: str) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    config["project"] = f"{base_config.get('project', 'v56_basket')}_{case_id}"
    config.setdefault("governance", {})["ablation_case"] = case_id
    return config


def _drop_factor(base_config: dict[str, Any], case_id: str, factor_name: str) -> dict[str, Any]:
    config = _case_config(base_config, case_id)
    config.setdefault("governance", {})["ablation_dropped_factor"] = factor_name
    _remove_factor(config, factor_name)
    return config


def _keep_factors(base_config: dict[str, Any], case_id: str, factor_names: list[str], weights: dict[str, float]) -> dict[str, Any]:
    config = _case_config(base_config, case_id)
    keep = set(factor_names)
    config["signals"]["factors"] = [factor for factor in config["signals"]["factors"] if factor.get("name") in keep]
    config["signals"]["scoring"]["weights"] = dict(weights)
    config["signals"]["scoring"]["min_factor_count"] = min(3, len(factor_names))
    _keep_override_factors(config, keep, weights)
    config["portfolio"]["required_fields"] = [field for field in config["portfolio"].get("required_fields", []) if field in keep]
    return config


def _remove_factor(config: dict[str, Any], factor_name: str) -> None:
    config["signals"]["factors"] = [factor for factor in config["signals"]["factors"] if factor.get("name") != factor_name]
    config["signals"]["scoring"].get("weights", {}).pop(factor_name, None)
    _remove_override_factor(config, factor_name)
    required = config.get("portfolio", {}).get("required_fields", [])
    config["portfolio"]["required_fields"] = [field for field in required if field != factor_name]
    min_count = int(config["signals"]["scoring"].get("min_factor_count", 1))
    config["signals"]["scoring"]["min_factor_count"] = min(min_count, len(config["signals"]["factors"]))


def _remove_override_factor(config: dict[str, Any], factor_name: str) -> None:
    overrides = config.get("signals", {}).get("scoring", {}).get("sector_scoring_overrides", {})
    for override in overrides.values():
        override["factors"] = [factor for factor in override.get("factors", []) if factor.get("name") != factor_name]
        override.get("weights", {}).pop(factor_name, None)
        min_count = int(override.get("min_factor_count", 1))
        override["min_factor_count"] = min(min_count, len(override.get("factors", [])))


def _keep_override_factors(config: dict[str, Any], keep: set[str], weights: dict[str, float]) -> None:
    overrides = config.get("signals", {}).get("scoring", {}).get("sector_scoring_overrides", {})
    for override in overrides.values():
        override["factors"] = [factor for factor in override.get("factors", []) if factor.get("name") in keep]
        override["weights"] = {name: weight for name, weight in weights.items() if name in {factor.get("name") for factor in override.get("factors", [])}}
        override["min_factor_count"] = min(int(override.get("min_factor_count", 1)), len(override.get("factors", [])))


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    return names


def _metrics_for_window(path: Path, start_date: str, end_date: str) -> dict[str, Any]:
    rows = [
        row
        for row in read_csv_rows(path)
        if (not start_date or str(row.get("trade_date") or "")[:10] >= start_date)
        and (not end_date or str(row.get("trade_date") or "")[:10] <= end_date)
    ]
    strategy_returns = [to_float(row.get("strategy_return")) or 0.0 for row in rows]
    benchmark_returns = [to_float(row.get("benchmark_return")) or 0.0 for row in rows]
    excess_returns = [to_float(row.get("excess_return")) or 0.0 for row in rows]
    return {
        "daily_count": len(rows),
        "strategy_return": compound(strategy_returns),
        "benchmark_return": compound(benchmark_returns),
        "excess_return": (compound(strategy_returns) or 0.0) - (compound(benchmark_returns) or 0.0) if rows else None,
        "max_drawdown": _max_drawdown(strategy_returns),
        "sharpe": _sharpe(strategy_returns),
        "information_ratio": _sharpe(excess_returns),
    }


def _max_drawdown(returns: list[float]) -> float | None:
    if not returns:
        return None
    nav = 1.0
    peak = 1.0
    max_dd = 0.0
    for ret in returns:
        nav *= 1.0 + ret
        peak = max(peak, nav)
        if peak > 0:
            max_dd = min(max_dd, nav / peak - 1.0)
    return abs(max_dd)


def _sharpe(returns: list[float]) -> float | None:
    if len(returns) < 2:
        return None
    vol = pstdev(returns)
    return (mean(returns) / vol) * (252 ** 0.5) if vol > 0 else None


def _report(summary: dict[str, Any]) -> str:
    rows = list(summary["cases"])
    ordered = sorted(rows, key=lambda row: to_float(row.get("strategy_return")) or -999, reverse=True)
    common_ordered = sorted(rows, key=lambda row: to_float(row.get("common_window_strategy_return")) or -999, reverse=True)
    base = next((row for row in rows if row["case"] == "base"), None)
    lines = [
        "# Basket Ablation Report",
        "",
        f"- Status: `{summary['status']}`",
        f"- Cases: `{summary['case_count']}`",
        f"- Common window: `{summary['common_window']['start_date']}` to `{summary['common_window']['end_date']}`",
        "",
        "## Base",
        "",
    ]
    if base:
        lines.extend(
            [
                f"- Strategy return: `{base['strategy_return']}`",
                f"- Excess return: `{base['excess_return']}`",
                f"- Max drawdown: `{base['max_drawdown']}`",
                f"- Common-window strategy return: `{base['common_window_strategy_return']}`",
                "",
            ]
        )
    lines.extend(["## Top Cases, Raw Window", ""])
    for row in ordered[:6]:
        lines.append(
            f"- `{row['case']}`: return `{row['strategy_return']}`, excess `{row['excess_return']}`, "
            f"max drawdown `{row['max_drawdown']}`, diff vs base `{row['strategy_return_diff_vs_base']}`"
        )
    lines.extend(["", "## Top Cases, Common Window", ""])
    for row in common_ordered[:6]:
        lines.append(
            f"- `{row['case']}`: return `{row['common_window_strategy_return']}`, excess `{row['common_window_excess_return']}`, "
            f"max drawdown `{row['common_window_max_drawdown']}`, diff vs base `{row['common_window_strategy_return_diff_vs_base']}`"
        )
    lines.extend(["", "## Governance", "", str(summary["pm_note"]), ""])
    return "\n".join(lines)

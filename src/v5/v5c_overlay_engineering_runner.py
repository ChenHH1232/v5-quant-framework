from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


BASELINE_DIR = (
    Path("local_daily_backtests_v57f_etf")
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)
ADMISSION_DIR = Path("v5c_overlay_hypothesis_admission") / "current"
QUANT_SPEC_DIR = Path("v5c_overlay_quant_spec") / "current"
ENGINEERING_DIR = Path("v5c_overlay_engineering_comparison") / "current"


def run_v5c_overlay_quant_spec_and_engineering(root: Path) -> dict[str, Any]:
    baseline_dir = root / BASELINE_DIR
    admission_dir = root / ADMISSION_DIR
    quant_spec_dir = root / QUANT_SPEC_DIR
    engineering_dir = root / ENGINEERING_DIR
    quant_spec_dir.mkdir(parents=True, exist_ok=True)
    engineering_dir.mkdir(parents=True, exist_ok=True)

    daily_rows = _read_csv(baseline_dir / "daily_returns.csv")
    baseline_summary = _read_json(baseline_dir / "summary.json")
    admission_summary = _read_json(admission_dir / "v5c_overlay_hypothesis_admission_summary.json")

    _write_quant_spec(quant_spec_dir, baseline_summary, admission_summary)
    variant_daily_rows, comparison_rows = _run_engineering_comparison(daily_rows)
    _write_csv(engineering_dir / "v5c_overlay_engineering_daily_nav.csv", variant_daily_rows)
    _write_csv(engineering_dir / "v5c_overlay_engineering_comparison.csv", comparison_rows)

    blocked_rows = [
        {
            "blocked_item": "true_sleeve_level_risk_parity_backtest",
            "reason": "current V57f local daily output does not contain independent sleeve-level daily PnL series",
            "needed_input": "daily sleeve returns for bank, utilities_electricity, highway_infrastructure, port_rail_infrastructure before overlay decision date",
            "allowed_next_action": "build sleeve attribution dataset; do not infer sleeve PnL from total portfolio return",
        },
        {
            "blocked_item": "dividend_safety_and_fcf_ocf_reducer_engineering",
            "reason": "admission gate classed these as data-gate specs, not immediate overlay engineering variants",
            "needed_input": "PIT dividend announcement dates and financial statement lag contract",
            "allowed_next_action": "build data-gate feasibility audit",
        },
        {
            "blocked_item": "cppi_like_portfolio_insurance_engineering",
            "reason": "PM admission deferred CPPI to rule-boundary memo due floor and multiplier overfit risk",
            "needed_input": "frozen floor, multiplier, cash proxy and reset rules",
            "allowed_next_action": "write boundary memo only",
        },
    ]
    _write_csv(engineering_dir / "v5c_overlay_engineering_blockers.csv", blocked_rows)

    summary = {
        "schema_version": 1,
        "project": "v5c_overlay_engineering_comparison",
        "status": "engineering_comparison_completed_partial_no_v57f_core_change",
        "baseline_strategy_id": baseline_summary.get("strategy_id"),
        "window": baseline_summary.get("window"),
        "admission_status": admission_summary.get("status"),
        "v57f_core_modified": False,
        "backtest_type": "post_process_overlay_on_frozen_v57f_daily_returns",
        "joinquant_started": False,
        "variant_count": len(comparison_rows),
        "engineering_variant_count": len(comparison_rows) - 1,
        "best_by_pm_order": "baseline remains frozen; overlay variants are diagnostics, not accepted strategy",
        "blocked_engineering_items": len(blocked_rows),
        "outputs": {
            "quant_spec_report": str(quant_spec_dir / "v5c_overlay_quant_spec_report.md"),
            "quant_spec_rules": str(quant_spec_dir / "v5c_overlay_quant_spec_rules.csv"),
            "data_requirements": str(quant_spec_dir / "v5c_overlay_quant_data_requirements.csv"),
            "engineering_summary": str(engineering_dir / "v5c_overlay_engineering_summary.json"),
            "engineering_report": str(engineering_dir / "v5c_overlay_engineering_report.md"),
            "engineering_comparison": str(engineering_dir / "v5c_overlay_engineering_comparison.csv"),
            "engineering_daily_nav": str(engineering_dir / "v5c_overlay_engineering_daily_nav.csv"),
            "engineering_blockers": str(engineering_dir / "v5c_overlay_engineering_blockers.csv"),
        },
    }
    _write_json(engineering_dir / "v5c_overlay_engineering_summary.json", summary)
    _write_engineering_report(engineering_dir, comparison_rows, blocked_rows)
    return summary


def _write_quant_spec(quant_spec_dir: Path, baseline_summary: dict[str, Any], admission_summary: dict[str, Any]) -> None:
    rule_rows = [
        {
            "spec_id": "V5C_QS_001",
            "hypothesis_id": "V5C_PDF_H01",
            "rule_family": "portfolio_risk_budget_overlay",
            "spec_status": "data_contract_first",
            "allowed_engineering": "diagnostic_only_until_sleeve_daily_pnl_exists",
            "rule_description": "Allocate risk by sleeve contribution only after independent PIT sleeve daily return series exists.",
            "pit_inputs": "sleeve daily returns; target sleeve weights; rolling covariance; rebalance calendar",
            "forbidden": "infer sleeve PnL from total return; tune windows by historical return; change V57f core",
        },
        {
            "spec_id": "V5C_QS_002",
            "hypothesis_id": "V5C_PDF_H03",
            "rule_family": "discrete_portfolio_volatility_state_defense",
            "spec_status": "engineering_diagnostic_allowed",
            "allowed_engineering": "post_process_frozen_daily_returns",
            "rule_description": "Use prior daily returns only. When short realized volatility exceeds longer realized volatility, reduce portfolio exposure by a fixed coarse amount.",
            "pit_inputs": "V57f frozen daily strategy returns before decision day; cash proxy assumption; transaction cost placeholder",
            "forbidden": "minute timing; Barra dependency without data contract; optimize threshold or cut size",
        },
        {
            "spec_id": "V5C_QS_003",
            "hypothesis_id": "V5C_PDF_H04",
            "rule_family": "dividend_safety_data_gate",
            "spec_status": "data_gate_only",
            "allowed_engineering": "none_until_pit_dividend_contract_exists",
            "rule_description": "Require proposal, approval, implementation, record and ex-dividend dates before any dividend safety reducer can be tested.",
            "pit_inputs": "dividend proposal date; approval date; implementation date; record date; ex-date; cash dividend amount",
            "forbidden": "future dividend; current index holdings backfill; alpha factor change",
        },
        {
            "spec_id": "V5C_QS_004",
            "hypothesis_id": "V5C_PDF_H05",
            "rule_family": "fcf_ocf_quality_data_gate",
            "spec_status": "data_gate_only",
            "allowed_engineering": "none_until_financial_lag_contract_exists",
            "rule_description": "Treat OCF/FCF deterioration only as a risk reducer after report announcement-date visibility is enforced.",
            "pit_inputs": "PIT OCF; FCF; enterprise value; announcement date; dividend continuity; concentration",
            "forbidden": "return optimization; concentrated portfolio copy; core factor change",
        },
    ]
    data_rows = [
        {
            "data_id": "V5C_DATA_001",
            "required_for": "sleeve_risk_parity",
            "field": "daily_sleeve_return",
            "source_status": "missing",
            "required_before": "engineering_true_sleeve_risk_budget",
        },
        {
            "data_id": "V5C_DATA_002",
            "required_for": "portfolio_volatility_state",
            "field": "frozen_v57f_daily_strategy_return",
            "source_status": "available",
            "required_before": "diagnostic_engineering_comparison",
        },
        {
            "data_id": "V5C_DATA_003",
            "required_for": "dividend_safety",
            "field": "dividend_announcement_date_chain",
            "source_status": "not_audited",
            "required_before": "data_gate_engineering",
        },
        {
            "data_id": "V5C_DATA_004",
            "required_for": "fcf_ocf_quality",
            "field": "financial_statement_announcement_lag_contract",
            "source_status": "not_audited",
            "required_before": "data_gate_engineering",
        },
    ]
    _write_csv(quant_spec_dir / "v5c_overlay_quant_spec_rules.csv", rule_rows)
    _write_csv(quant_spec_dir / "v5c_overlay_quant_data_requirements.csv", data_rows)
    report = f"""# V5c Overlay Quant Spec

This spec follows the PM admission gate and keeps V57f frozen.

Baseline: `{baseline_summary.get("strategy_id")}`
Window: `{baseline_summary.get("window")}`
Admission status: `{admission_summary.get("status")}`

## Allowed For Engineering Now

- Discrete portfolio volatility-state defense as a post-process diagnostic on frozen V57f daily returns.

## Not Yet Allowed

- True sleeve-level risk parity, because independent sleeve daily PnL is not available.
- Dividend safety reducer, until PIT dividend-date contracts are audited.
- FCF / OCF quality reducer, until financial statement lag contracts are audited.
- CPPI-like portfolio insurance, until PM freezes floor, multiplier, reset and cash-proxy rules.

## Guardrails

- No V57f core changes.
- No threshold optimization against 2021-2026.
- No JoinQuant.
- No minute-level timing.
- No historical-return ranking of overlay variants.
"""
    (quant_spec_dir / "v5c_overlay_quant_spec_report.md").write_text(report, encoding="utf-8")


def _run_engineering_comparison(daily_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    returns = [_to_float(row.get("strategy_return")) for row in daily_rows]
    benchmark_returns = [_to_float(row.get("benchmark_return")) for row in daily_rows]
    dates = [str(row.get("trade_date")) for row in daily_rows]
    variants = [
        {
            "variant_id": "v57f_frozen_baseline",
            "description": "Frozen V57f daily returns, no V5c overlay",
            "returns": returns,
            "exposures": [1.0 for _ in returns],
        },
        {
            "variant_id": "vol_state_60_120_cut80",
            "description": "If prior 60d realized vol exceeds prior 120d realized vol, exposure is 80%; otherwise 100%",
            "returns": _apply_vol_state(returns, 60, 120, 0.80),
            "exposures": _build_vol_exposures(returns, 60, 120, 0.80),
        },
        {
            "variant_id": "vol_state_20_60_cut85",
            "description": "If prior 20d realized vol exceeds prior 60d realized vol, exposure is 85%; otherwise 100%",
            "returns": _apply_vol_state(returns, 20, 60, 0.85),
            "exposures": _build_vol_exposures(returns, 20, 60, 0.85),
        },
        {
            "variant_id": "vol_ratio_60_120_floor75",
            "description": "If prior 60d vol is above prior 120d vol, exposure scales by long_vol/short_vol with 75% floor",
            "returns": _apply_vol_ratio(returns, 60, 120, 0.75),
            "exposures": _build_vol_ratio_exposures(returns, 60, 120, 0.75),
        },
    ]
    daily_out: list[dict[str, Any]] = []
    comparison: list[dict[str, Any]] = []
    baseline_metrics: dict[str, Any] | None = None
    for variant in variants:
        navs = _nav_series(variant["returns"])
        metrics = _compute_metrics(variant["returns"], benchmark_returns, variant["exposures"], dates)
        if variant["variant_id"] == "v57f_frozen_baseline":
            baseline_metrics = metrics
        comparison.append(
            {
                "variant_id": variant["variant_id"],
                "description": variant["description"],
                **metrics,
                "delta_return_vs_baseline": "" if baseline_metrics is None else metrics["strategy_return"] - baseline_metrics["strategy_return"],
                "delta_max_drawdown_vs_baseline": "" if baseline_metrics is None else metrics["max_drawdown"] - baseline_metrics["max_drawdown"],
                "pm_conclusion": _pm_conclusion(variant["variant_id"], metrics, baseline_metrics),
            }
        )
        for idx, day in enumerate(dates):
            daily_out.append(
                {
                    "trade_date": day,
                    "variant_id": variant["variant_id"],
                    "overlay_return": variant["returns"][idx],
                    "overlay_nav": navs[idx],
                    "benchmark_return": benchmark_returns[idx],
                    "exposure": variant["exposures"][idx],
                    "baseline_return": returns[idx],
                }
            )
    return daily_out, comparison


def _apply_vol_state(returns: list[float], short_window: int, long_window: int, risk_off_exposure: float) -> list[float]:
    exposures = _build_vol_exposures(returns, short_window, long_window, risk_off_exposure)
    return [ret * exposures[idx] for idx, ret in enumerate(returns)]


def _build_vol_exposures(returns: list[float], short_window: int, long_window: int, risk_off_exposure: float) -> list[float]:
    exposures = []
    for idx in range(len(returns)):
        if idx < long_window:
            exposures.append(1.0)
            continue
        short_vol = _annualized_vol(returns[idx - short_window:idx])
        long_vol = _annualized_vol(returns[idx - long_window:idx])
        exposures.append(risk_off_exposure if short_vol > long_vol else 1.0)
    return exposures


def _apply_vol_ratio(returns: list[float], short_window: int, long_window: int, floor: float) -> list[float]:
    exposures = _build_vol_ratio_exposures(returns, short_window, long_window, floor)
    return [ret * exposures[idx] for idx, ret in enumerate(returns)]


def _build_vol_ratio_exposures(returns: list[float], short_window: int, long_window: int, floor: float) -> list[float]:
    exposures = []
    for idx in range(len(returns)):
        if idx < long_window:
            exposures.append(1.0)
            continue
        short_vol = _annualized_vol(returns[idx - short_window:idx])
        long_vol = _annualized_vol(returns[idx - long_window:idx])
        if short_vol > long_vol and short_vol > 0:
            exposures.append(max(floor, min(1.0, long_vol / short_vol)))
        else:
            exposures.append(1.0)
    return exposures


def _compute_metrics(
    returns: list[float],
    benchmark_returns: list[float],
    exposures: list[float],
    dates: list[str],
) -> dict[str, Any]:
    navs = _nav_series(returns)
    benchmark_navs = _nav_series(benchmark_returns)
    total_return = navs[-1] - 1 if navs else 0.0
    benchmark_return = benchmark_navs[-1] - 1 if benchmark_navs else 0.0
    periods = len(returns)
    annualized_return = (1 + total_return) ** (252 / periods) - 1 if periods and total_return > -1 else None
    vol = _annualized_vol(returns)
    sharpe = annualized_return / vol if annualized_return is not None and vol else None
    max_dd, dd_start_idx, dd_end_idx = _max_drawdown(navs)
    dd_start = dates[dd_start_idx] if 0 <= dd_start_idx < len(dates) else ""
    dd_end = dates[dd_end_idx] if 0 <= dd_end_idx < len(dates) else ""
    excess_returns = [ret - benchmark_returns[idx] for idx, ret in enumerate(returns)]
    information_ratio = _safe_mean(excess_returns) / pstdev(excess_returns) * math.sqrt(252) if len(excess_returns) > 1 and pstdev(excess_returns) else None
    risk_off_days = sum(1 for value in exposures if value < 0.999)
    return {
        "strategy_return": total_return,
        "annualized_return": annualized_return,
        "benchmark_return": benchmark_return,
        "excess_return": total_return - benchmark_return,
        "max_drawdown": max_dd,
        "max_drawdown_interval": f"{dd_start},{dd_end}" if dd_start and dd_end else "",
        "strategy_volatility": vol,
        "sharpe": sharpe,
        "information_ratio": information_ratio,
        "average_exposure": mean(exposures) if exposures else 1.0,
        "risk_off_days": risk_off_days,
        "risk_off_ratio": risk_off_days / len(exposures) if exposures else 0.0,
    }


def _pm_conclusion(variant_id: str, metrics: dict[str, Any], baseline: dict[str, Any] | None) -> str:
    if variant_id == "v57f_frozen_baseline":
        return "frozen_reference_not_replaced"
    if baseline is None:
        return "diagnostic_only"
    if metrics["max_drawdown"] < baseline["max_drawdown"] and metrics["strategy_return"] < baseline["strategy_return"]:
        return "drawdown_reduced_with_return_cost_quant_review_needed"
    if metrics["max_drawdown"] < baseline["max_drawdown"]:
        return "drawdown_reduced_diagnostic_promising"
    return "no_drawdown_improvement_diagnostic_only"


def _nav_series(returns: list[float]) -> list[float]:
    nav = 1.0
    output = []
    for ret in returns:
        nav *= 1 + ret
        output.append(nav)
    return output


def _max_drawdown(navs: list[float]) -> tuple[float, int, int]:
    peak = -float("inf")
    peak_idx = 0
    max_dd = 0.0
    start_idx = 0
    end_idx = 0
    for idx, nav in enumerate(navs):
        if nav > peak:
            peak = nav
            peak_idx = idx
        if peak > 0:
            dd = 1 - nav / peak
            if dd > max_dd:
                max_dd = dd
                start_idx = peak_idx
                end_idx = idx
    return max_dd, start_idx, end_idx


def _annualized_vol(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return pstdev(values) * math.sqrt(252)


def _safe_mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["empty"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_engineering_report(engineering_dir: Path, comparison_rows: list[dict[str, Any]], blocked_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# V5c Overlay Engineering Comparison",
        "",
        "This is a diagnostic post-process comparison on frozen V57f daily returns. It is not an accepted strategy, not a V57f core change, and not JoinQuant replication.",
        "",
        "## Comparison",
        "",
        "| Variant | Return | Max Drawdown | Volatility | Avg Exposure | PM Conclusion |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in comparison_rows:
        lines.append(
            "| {variant_id} | {ret:.2%} | {dd:.2%} | {vol:.2%} | {exp:.2%} | {conclusion} |".format(
                variant_id=row["variant_id"],
                ret=row["strategy_return"],
                dd=row["max_drawdown"],
                vol=row["strategy_volatility"],
                exp=row["average_exposure"],
                conclusion=row["pm_conclusion"],
            )
        )
    lines.extend(
        [
            "",
            "## Blocked Engineering Items",
            "",
        ]
    )
    for row in blocked_rows:
        lines.append(f"- `{row['blocked_item']}`: {row['reason']}")
    lines.extend(
        [
            "",
            "## PM Decision",
            "",
            "Volatility-state overlays have engineering comparison results and can be reviewed by Quant. True sleeve-level risk parity remains blocked until daily sleeve PnL is built. Baseline V57f remains frozen.",
        ]
    )
    (engineering_dir / "v5c_overlay_engineering_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    result = run_v5c_overlay_quant_spec_and_engineering(Path.cwd())
    print(json.dumps(result, ensure_ascii=False, indent=2))

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

from v5.formal_validation_runner import run_formal_validation
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import to_float
from v5.paths import DEFAULT_PROCESSED_DIR


DEFAULT_PANEL_ROOT = DEFAULT_PROCESSED_DIR / "similar_sector_pit_panel_v5a11"
DEFAULT_OUT_ROOT = Path("validation_formal_v5a11_low_priority_initial")
DEFAULT_SECTORS = [
    "securities_brokerage",
    "chemical_materials",
    "textile_apparel",
    "logistics_express",
    "retail_commerce",
    "auto_and_parts",
    "machinery_equipment",
]


@dataclass(frozen=True)
class LowPrioritySectorInitialValidationResult:
    summary_json: Path
    result_csv: Path
    report_md: Path
    status: str


def run_low_priority_sector_initial_validation(
    panel_root: Path = DEFAULT_PANEL_ROOT,
    out_root: Path = DEFAULT_OUT_ROOT,
    sectors: list[str] | None = None,
    *,
    min_dates: int = 12,
    min_median_names: int = 12,
) -> LowPrioritySectorInitialValidationResult:
    target_sectors = sectors or DEFAULT_SECTORS
    out_root.mkdir(parents=True, exist_ok=True)
    result_rows = []
    for sector in target_sectors:
        panel = _panel_path(panel_root, sector)
        if not panel.exists():
            result_rows.append(_missing_panel_row(sector, panel))
            continue
        rows = read_csv_rows(panel)
        profile = _profile(rows)
        if profile["date_count"] < min_dates or profile["median_codes_per_date"] < min_median_names:
            result_rows.append(_sample_blocked_row(sector, panel, profile, min_dates, min_median_names))
            continue
        selection_count = _selection_count(profile["median_codes_per_date"])
        has_low_vol = _has_field(rows, "low_vol_score")
        spec_path = out_root / "specs" / f"{sector}_ocf_dividend_fcf_initial_v5a11.json"
        write_json_file(spec_path, _spec(sector, selection_count, has_low_vol=has_low_vol))
        report_path = run_formal_validation(spec_path, panel, out_root / "formal")
        summary_path = report_path.with_name("formal_validation_summary.json")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        result_rows.append(_result_row(sector, panel, profile, selection_count, spec_path, summary_path, summary))

    result_csv = out_root / "low_priority_sector_initial_validation_results.csv"
    summary_json = out_root / "low_priority_sector_initial_validation_summary.json"
    report_md = out_root / "low_priority_sector_initial_validation_pm_report.md"
    write_csv_rows(result_csv, _result_fields(), result_rows)
    status = _status(result_rows)
    summary_doc = {
        "dataset": "low_priority_sector_initial_validation_v5a11",
        "experiment_layer": "research_pit_validation",
        "panel_root": str(panel_root),
        "result_csv": str(result_csv),
        "status": status,
        "sector_count": len(result_rows),
        "candidate_count": sum(1 for row in result_rows if row.get("pm_decision") == "research_signal_candidate_needs_low_vol_state_gate"),
        "result_rows": result_rows,
        "governance": "This is a low-cost research screen. It cannot approve Engineering handoff because low-volatility and sector-specific state gates are not attached.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_json_file(summary_json, summary_doc)
    report_md.write_text(_report(summary_doc), encoding="utf-8")
    return LowPrioritySectorInitialValidationResult(summary_json, result_csv, report_md, status)


def _profile(rows: list[dict[str, str]]) -> dict[str, int]:
    by_date: dict[str, set[str]] = {}
    for row in rows:
        trade_date = str(row.get("trade_date") or "")[:10]
        code = str(row.get("code") or "")
        if trade_date and code:
            by_date.setdefault(trade_date, set()).add(code)
    counts = [len(codes) for codes in by_date.values()]
    return {
        "row_count": len(rows),
        "date_count": len(by_date),
        "code_count": len({row.get("code") for row in rows if row.get("code")}),
        "median_codes_per_date": int(median(counts)) if counts else 0,
        "min_codes_per_date": min(counts) if counts else 0,
        "max_codes_per_date": max(counts) if counts else 0,
    }


def _selection_count(median_names: int) -> int:
    return max(5, min(15, int(median_names * 0.18)))


def _panel_path(panel_root: Path, sector: str) -> Path:
    canonical = panel_root / sector / "panel.csv"
    if canonical.exists():
        return canonical
    return panel_root / sector / "panel_with_low_vol.csv"


def _has_field(rows: list[dict[str, str]], field: str) -> bool:
    return bool(rows and field in rows[0] and any(row.get(field) not in (None, "") for row in rows))


def _spec(sector: str, selection_count: int, *, has_low_vol: bool = False) -> dict[str, Any]:
    strategy_id = f"{sector}_ocf_dividend_fcf_initial_v5a11"
    factors = [
        {
            "name": "operating_cash_flow_yield",
            "source": "JoinQuant/DataJQ cash_flow.net_operate_cash_flow divided by valuation.market_cap",
            "role": "primary_cash_generation",
            "direction": "higher_is_better",
            "definition": "Operating cash-flow yield on market capitalization.",
            "as_of": "trade_date_lagged",
            "disclosure_lag_days": 1,
            "missing_policy": "drop_security",
        },
        {
            "name": "dividend_yield",
            "source": "JoinQuant/DataJQ valuation.dividend_ratio as of trade_date",
            "role": "shareholder_return_support",
            "direction": "higher_is_better",
            "definition": "Dividend yield proxy available from the PIT fundamentals query.",
            "as_of": "trade_date_lagged",
            "disclosure_lag_days": 1,
            "missing_policy": "drop_security",
        },
        {
            "name": "free_cash_flow_yield",
            "source": "JoinQuant/DataJQ cash_flow.net_operate_cash_flow minus cash_flow.fix_intan_other_asset_acqui_cash divided by valuation.market_cap",
            "role": "diagnostic_cash_after_capex",
            "direction": "higher_is_better",
            "definition": "Operating cash flow less acquisition of fixed, intangible and other long-term assets, scaled by market capitalization.",
            "as_of": "trade_date_lagged",
            "disclosure_lag_days": 1,
            "missing_policy": "drop_security",
        },
    ]
    weights = {"operating_cash_flow_yield": 0.5, "dividend_yield": 0.25, "free_cash_flow_yield": 0.25}
    if has_low_vol:
        factors.append(
            {
                "name": "low_vol_score",
                "source": "V5 low_volatility_factor_runner using daily closes strictly before trade_date",
                "role": "risk_quality",
                "direction": "higher_is_better",
                "definition": "Composite low-volatility score from volatility, downside volatility and drawdown metrics.",
                "as_of": "trade_date_lagged",
                "disclosure_lag_days": 1,
                "missing_policy": "drop_security",
            }
        )
        weights = {"operating_cash_flow_yield": 0.4, "low_vol_score": 0.3, "dividend_yield": 0.15, "free_cash_flow_yield": 0.15}
    common_fields = list(weights)
    baselines = [
        {"name": f"equal_weight_{sector}", "mode": "equal_all"},
        {"name": "high_ocf", "mode": "single_factor", "factor": "operating_cash_flow_yield", "direction": "higher_is_better", "selection_count": selection_count},
        {"name": "high_dividend", "mode": "single_factor", "factor": "dividend_yield", "direction": "higher_is_better", "selection_count": selection_count},
        {"name": "high_fcf", "mode": "single_factor", "factor": "free_cash_flow_yield", "direction": "higher_is_better", "selection_count": selection_count},
    ]
    if has_low_vol:
        baselines.append({"name": "low_vol", "mode": "single_factor", "factor": "low_vol_score", "direction": "higher_is_better", "selection_count": selection_count})
    baselines.append({"name": "ocf_dividend_fcf", "mode": "composite", "selection_count": selection_count})
    common_interactions = [
        {"name": "common_high_ocf_only", "factors": ["operating_cash_flow_yield"]},
        {"name": "common_high_dividend_only", "factors": ["dividend_yield"]},
        {"name": "common_high_fcf_only", "factors": ["free_cash_flow_yield"]},
    ]
    if has_low_vol:
        common_interactions.append({"name": "common_low_vol_only", "factors": ["low_vol_score"]})
    common_interactions.append({"name": "common_ocf_dividend_fcf", "factors": common_fields})
    return {
        "meta": {
            "strategy_id": strategy_id,
            "name": f"{sector} OCF Dividend FCF Initial V5a.11",
            "objective": "Low-priority sector research screen for the dividend low-volatility OCF/FCF enhanced ETF queue; no return tuning.",
        },
        "universe": {
            "name": sector,
            "construction": "JoinQuant/DataJQ industry-code PIT panel from similar_sector_pit_panel_runner.",
            "point_in_time": True,
            "minimum_rebalance_coverage_ratio": 0.8,
        },
        "data": {
            "vendor": "JoinQuant/DataJQ",
            "price_frequency": "quarterly_signal_panel",
            "financial_as_of_policy": "vendor_get_fundamentals_date_proxy",
            "window": {"research_start": "2021-05-01", "research_end": "2026-05-31"},
        },
        "signals": {
            "factors": factors,
            "scoring": {
                "method": "weighted_composite",
                "normalization_scope": "rebalance_cross_section",
                "weights": weights,
                "min_factor_count": 2,
                "value_trap_guard": (
                    "Sector-specific state variables are not attached in V5a.11; this is a coarse research screen only."
                    if has_low_vol
                    else "Low-volatility and sector-specific state variables are not attached in V5a.11; this is a coarse research screen only."
                ),
            },
        },
        "schedule": {"signal_frequency": "quarterly", "rebalance_frequency": "quarterly"},
        "portfolio": {"selection_count": selection_count, "weighting": "equal_weight_research_candidate", "max_position_weight": 0.2},
        "risk": {"defensive_asset": "cash", "defensive_rule": {"enabled": False}},
        "validation": {
            "method": "rolling",
            "train_years": 3,
            "test_years": 1,
            "weak_years": ["2021", "2022", "2024", "2026"],
            "baselines": baselines,
            "common_sample_fields": common_fields,
            "common_sample_interactions": common_interactions,
            "robustness": {
                "selection_counts": [max(5, selection_count - 2), selection_count, selection_count + 2],
                "weight_scale_factors": common_fields,
                "weight_scales": [0.8, 1.0, 1.2],
            },
        },
        "execution": {
            "status": "not_started",
            "next_gate": "research_data_gate",
            "commission_bps": 3,
            "slippage_bps": 5,
            "suspension_policy": "skip_untradeable",
            "limit_policy": "skip_limit_blocked",
        },
        "outputs": {"save_holdings": True, "save_rebalance_signals": True, "report": "markdown"},
    }


def _result_row(
    sector: str,
    panel: Path,
    profile: dict[str, int],
    selection_count: int,
    spec_path: Path,
    summary_path: Path,
    summary: dict[str, Any],
) -> dict[str, Any]:
    baselines = {row["case"]: row for row in summary.get("baseline_tests", [])}
    equal_case = next((row for row in baselines.values() if str(row.get("case", "")).startswith("equal_weight_")), {})
    equal_return = to_float(equal_case.get("cum_return"))
    composite_return = to_float(baselines.get("ocf_dividend_fcf", {}).get("cum_return"))
    has_low_vol = "low_vol" in baselines
    rolling = summary.get("rolling_validation", [])
    negative_rolling = sum(1 for row in rolling if (to_float(row.get("cum_return")) or 0.0) < 0.0)
    return {
        "sector_id": sector,
        **profile,
        "selection_count": selection_count,
        "pm_decision": _pm_decision(equal_return, composite_return, negative_rolling),
        "equal_weight_return": equal_return,
        "high_ocf_return": to_float(baselines.get("high_ocf", {}).get("cum_return")),
        "low_vol_return": to_float(baselines.get("low_vol", {}).get("cum_return")),
        "high_dividend_return": to_float(baselines.get("high_dividend", {}).get("cum_return")),
        "high_fcf_return": to_float(baselines.get("high_fcf", {}).get("cum_return")),
        "ocf_dividend_fcf_return": composite_return,
        "negative_rolling_windows": negative_rolling,
        "mean_ic_operating_cash_flow_yield": _factor_metric(summary, "operating_cash_flow_yield", "mean_ic"),
        "mean_rankic_operating_cash_flow_yield": _factor_metric(summary, "operating_cash_flow_yield", "mean_rankic"),
        "mean_ic_dividend_yield": _factor_metric(summary, "dividend_yield", "mean_ic"),
        "mean_rankic_dividend_yield": _factor_metric(summary, "dividend_yield", "mean_rankic"),
        "mean_ic_free_cash_flow_yield": _factor_metric(summary, "free_cash_flow_yield", "mean_ic"),
        "mean_rankic_free_cash_flow_yield": _factor_metric(summary, "free_cash_flow_yield", "mean_rankic"),
        "mean_ic_low_vol_score": _factor_metric(summary, "low_vol_score", "mean_ic"),
        "mean_rankic_low_vol_score": _factor_metric(summary, "low_vol_score", "mean_rankic"),
        "panel_path": str(panel),
        "spec_path": str(spec_path),
        "summary_path": str(summary_path),
        "blocker": (
            "sector-specific state gates missing before Engineering"
            if has_low_vol
            else "low_volatility and sector-specific state gates missing before Engineering"
        ),
    }


def _pm_decision(equal_return: float | None, composite_return: float | None, negative_rolling: int) -> str:
    if equal_return is None or composite_return is None:
        return "validation_failed_missing_baseline"
    if composite_return <= equal_return or composite_return <= 0:
        return "rejected_initial_composite_not_superior"
    if negative_rolling > 1:
        return "research_signal_only_unstable_rolling"
    return "research_signal_candidate_needs_low_vol_state_gate"


def _status(rows: list[dict[str, Any]]) -> str:
    if any(row.get("pm_decision") == "research_signal_candidate_needs_low_vol_state_gate" for row in rows):
        return "initial_research_signal_found_not_engineering_handoff"
    if any(row.get("pm_decision") == "research_signal_only_unstable_rolling" for row in rows):
        return "initial_research_signal_only_needs_repair"
    return "initial_validation_no_engineering_candidate"


def _factor_metric(summary: dict[str, Any], factor: str, metric: str) -> float | None:
    for row in summary.get("factor_ic_rankic", []):
        if row.get("factor") == factor:
            return to_float(row.get(metric))
    return None


def _missing_panel_row(sector: str, panel: Path) -> dict[str, Any]:
    return {"sector_id": sector, "pm_decision": "missing_panel", "panel_path": str(panel), "blocker": "PIT panel missing"}


def _sample_blocked_row(sector: str, panel: Path, profile: dict[str, int], min_dates: int, min_median_names: int) -> dict[str, Any]:
    return {
        "sector_id": sector,
        **profile,
        "pm_decision": "sample_size_or_history_blocked",
        "panel_path": str(panel),
        "blocker": f"needs at least {min_dates} dates and median {min_median_names} names",
    }


def _result_fields() -> list[str]:
    return [
        "sector_id",
        "row_count",
        "date_count",
        "code_count",
        "median_codes_per_date",
        "min_codes_per_date",
        "max_codes_per_date",
        "selection_count",
        "pm_decision",
        "equal_weight_return",
        "high_ocf_return",
        "low_vol_return",
        "high_dividend_return",
        "high_fcf_return",
        "ocf_dividend_fcf_return",
        "negative_rolling_windows",
        "mean_ic_operating_cash_flow_yield",
        "mean_rankic_operating_cash_flow_yield",
        "mean_ic_dividend_yield",
        "mean_rankic_dividend_yield",
        "mean_ic_free_cash_flow_yield",
        "mean_rankic_free_cash_flow_yield",
        "mean_ic_low_vol_score",
        "mean_rankic_low_vol_score",
        "panel_path",
        "spec_path",
        "summary_path",
        "blocker",
    ]


def _report(summary: dict[str, Any]) -> str:
    lines = [
        "# V5a.11 Low-Priority Sector Initial Validation",
        "",
        f"Status: `{summary['status']}`",
        "",
        "This is a research screen only. No sector is approved for Engineering without low-volatility, dividend and sector-specific state gates.",
        "",
        "| Sector | PM decision | Equal | Composite | High OCF | Low vol | High dividend | High FCF | Negative rolling |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["result_rows"]:
        lines.append(
            f"| `{row.get('sector_id', '')}` | `{row.get('pm_decision', '')}` | "
            f"{row.get('equal_weight_return', '')} | {row.get('ocf_dividend_fcf_return', '')} | "
            f"{row.get('high_ocf_return', '')} | {row.get('low_vol_return', '')} | {row.get('high_dividend_return', '')} | "
            f"{row.get('high_fcf_return', '')} | {row.get('negative_rolling_windows', '')} |"
        )
    return "\n".join(lines) + "\n"

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

from v5.formal_validation_runner import run_formal_validation
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.paths import DEFAULT_PROCESSED_DIR


DEFAULT_OUT_ROOT = Path("validation_formal_v5a6_consumer_subsector")

DEFAULT_PANELS = {
    "food_beverage": DEFAULT_PROCESSED_DIR
    / "consumer_working_capital_state_v5a6"
    / "food_beverage"
    / "panel_with_working_capital_state.csv",
    "consumer_staples_cashflow": DEFAULT_PROCESSED_DIR
    / "consumer_working_capital_state_v5a6"
    / "consumer_staples_cashflow"
    / "panel_with_working_capital_state.csv",
    "pharma_medical_services": DEFAULT_PROCESSED_DIR
    / "consumer_working_capital_state_v5a6"
    / "pharma_medical_services"
    / "panel_with_working_capital_state.csv",
}


@dataclass(frozen=True)
class ConsumerSubsectorValidationResult:
    summary_json: Path
    result_csv: Path
    report_md: Path
    sector_id: str
    status: str


def run_consumer_subsector_validation(
    sector_id: str,
    panel_csv: Path | None = None,
    out_root: Path = DEFAULT_OUT_ROOT,
    min_codes_per_date: int = 8,
) -> ConsumerSubsectorValidationResult:
    panel_path = panel_csv or _default_panel(sector_id)
    rows = read_csv_rows(panel_path)
    out_dir = out_root / sector_id
    panel_dir = out_dir / "panels"
    spec_dir = out_dir / "specs"
    panel_dir.mkdir(parents=True, exist_ok=True)
    spec_dir.mkdir(parents=True, exist_ok=True)

    result_rows: list[dict[str, Any]] = []
    for sub_industry, sub_rows in sorted(_group_by_subindustry(rows).items()):
        profile = _sample_profile(sub_rows)
        if profile["date_count"] < 12 or profile["median_codes_per_date"] < min_codes_per_date:
            result_rows.append(_skipped_row(sector_id, sub_industry, profile, min_codes_per_date))
            continue
        selection_count = _selection_count(profile["median_codes_per_date"])
        sub_panel = panel_dir / f"{_safe_id(sub_industry)}.csv"
        write_csv_rows(sub_panel, _fieldnames(sub_rows), sub_rows)
        spec_path = spec_dir / f"{sector_id}_{_safe_id(sub_industry)}_ocf_quality_v5a6.json"
        write_json_file(spec_path, _spec(sector_id, sub_industry, selection_count))
        report_path = run_formal_validation(spec_path, sub_panel, out_dir / "formal")
        summary_path = report_path.with_name("formal_validation_summary.json")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        result_rows.append(_result_row(sector_id, sub_industry, profile, selection_count, spec_path, sub_panel, summary_path, summary))

    result_csv = out_dir / "consumer_subsector_validation_results.csv"
    summary_json = out_dir / "consumer_subsector_validation_summary.json"
    report_md = out_dir / "consumer_subsector_validation_pm_report.md"
    write_csv_rows(result_csv, _result_fields(), result_rows)
    status = _status(result_rows)
    summary_doc = {
        "dataset": f"{sector_id}_consumer_subsector_validation_v5a6",
        "sector_id": sector_id,
        "panel_csv": str(panel_path),
        "result_csv": str(result_csv),
        "status": status,
        "subsector_count": len(result_rows),
        "candidate_count": sum(1 for row in result_rows if row.get("pm_decision") == "research_signal_candidate_needs_state_review"),
        "result_rows": result_rows,
        "governance": "This is research PIT validation only. Subsector results do not approve Engineering handoff.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_json_file(summary_json, summary_doc)
    _write_report(report_md, summary_doc)
    return ConsumerSubsectorValidationResult(summary_json, result_csv, report_md, sector_id, status)


def _default_panel(sector_id: str) -> Path:
    if sector_id not in DEFAULT_PANELS:
        supported = ", ".join(sorted(DEFAULT_PANELS))
        raise ValueError(f"unsupported consumer subsector validation sector '{sector_id}'. Supported: {supported}")
    return DEFAULT_PANELS[sector_id]


def _group_by_subindustry(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        key = str(row.get("sub_industry") or "unknown")
        grouped.setdefault(key, []).append(row)
    return grouped


def _sample_profile(rows: list[dict[str, str]]) -> dict[str, Any]:
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


def _selection_count(median_codes_per_date: int) -> int:
    return max(3, min(8, int(median_codes_per_date * 0.35)))


def _spec(sector_id: str, sub_industry: str, selection_count: int) -> dict[str, Any]:
    strategy_id = f"{sector_id}_{_safe_id(sub_industry)}_ocf_quality_v5a6"
    return {
        "meta": {
            "strategy_id": strategy_id,
            "name": f"{sector_id} {sub_industry} OCF Quality V5a.6",
            "objective": "Subsector PIT validation for dividend low-volatility / OCF enhanced ETF queue; no return tuning.",
        },
        "universe": {
            "name": f"{sector_id}:{sub_industry}",
            "construction": "Filtered from the PIT sector panel by sub_industry.",
            "point_in_time": True,
            "minimum_rebalance_coverage_ratio": 0.8,
        },
        "data": {
            "vendor": "JoinQuant/DataJQ PIT financial fields, real daily prices, cash-dividend panel and working-capital state runner",
            "price_frequency": "quarterly_signal_panel",
            "financial_as_of_policy": "vendor_get_fundamentals_date_proxy",
            "window": {"research_start": "2021-05-01", "research_end": "2026-05-31"},
        },
        "signals": {
            "factors": [
                {
                    "name": "operating_cash_flow_yield",
                    "source": "JoinQuant/DataJQ cash_flow.net_operate_cash_flow divided by valuation.market_cap",
                    "role": "primary_cash_generation",
                    "direction": "higher_is_better",
                    "definition": "Operating cash flow yield.",
                    "as_of": "trade_date_lagged",
                    "disclosure_lag_days": 1,
                    "missing_policy": "drop_security",
                },
                {
                    "name": "operating_cash_flow_to_net_profit",
                    "source": "JoinQuant/DataJQ cash flow and income statement fields",
                    "role": "cash_conversion_quality",
                    "direction": "higher_is_better",
                    "definition": "Operating cash flow relative to net profit.",
                    "as_of": "trade_date_lagged",
                    "disclosure_lag_days": 1,
                    "missing_policy": "drop_security",
                },
            ],
            "scoring": {
                "method": "weighted_composite",
                "normalization_scope": "rebalance_cross_section",
                "weights": {"operating_cash_flow_yield": 0.7, "operating_cash_flow_to_net_profit": 0.3},
                "min_factor_count": 2,
                "value_trap_guard": "Working-capital, inventory, dividend and low-volatility are diagnostics here, not positive scoring factors.",
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
            "baselines": [
                {"name": "equal_weight_subindustry", "mode": "equal_all"},
                {
                    "name": "high_ocf",
                    "mode": "single_factor",
                    "factor": "operating_cash_flow_yield",
                    "direction": "higher_is_better",
                    "selection_count": selection_count,
                },
                {
                    "name": "ocf_to_net_profit",
                    "mode": "single_factor",
                    "factor": "operating_cash_flow_to_net_profit",
                    "direction": "higher_is_better",
                    "selection_count": selection_count,
                },
                {"name": "ocf_quality", "mode": "composite", "selection_count": selection_count},
            ],
            "common_sample_fields": ["operating_cash_flow_yield", "operating_cash_flow_to_net_profit"],
            "common_sample_interactions": [
                {"name": "common_high_ocf_only", "factors": ["operating_cash_flow_yield"]},
                {"name": "common_ocf_to_profit_only", "factors": ["operating_cash_flow_to_net_profit"]},
                {"name": "common_ocf_quality", "factors": ["operating_cash_flow_yield", "operating_cash_flow_to_net_profit"]},
            ],
            "robustness": {
                "selection_counts": [max(3, selection_count - 1), selection_count, selection_count + 1],
                "weight_scale_factors": ["operating_cash_flow_yield", "operating_cash_flow_to_net_profit"],
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
    sector_id: str,
    sub_industry: str,
    profile: dict[str, Any],
    selection_count: int,
    spec_path: Path,
    panel_path: Path,
    summary_path: Path,
    summary: dict[str, Any],
) -> dict[str, Any]:
    baselines = {row["case"]: row for row in summary.get("baseline_tests", [])}
    equal_return = _float_or_none(baselines.get("equal_weight_subindustry", {}).get("cum_return"))
    composite_return = _float_or_none(baselines.get("ocf_quality", {}).get("cum_return"))
    rolling = summary.get("rolling_validation", [])
    negative_rolling = sum(1 for row in rolling if (_float_or_none(row.get("cum_return")) or 0.0) < 0.0)
    pm_decision = _pm_decision(equal_return, composite_return, negative_rolling, profile)
    return {
        "sector_id": sector_id,
        "sub_industry": sub_industry,
        **profile,
        "selection_count": selection_count,
        "pm_decision": pm_decision,
        "equal_weight_return": equal_return,
        "high_ocf_return": _float_or_none(baselines.get("high_ocf", {}).get("cum_return")),
        "ocf_to_net_profit_return": _float_or_none(baselines.get("ocf_to_net_profit", {}).get("cum_return")),
        "ocf_quality_return": composite_return,
        "negative_rolling_windows": negative_rolling,
        "mean_ic_operating_cash_flow_yield": _factor_metric(summary, "operating_cash_flow_yield", "mean_ic"),
        "mean_rankic_operating_cash_flow_yield": _factor_metric(summary, "operating_cash_flow_yield", "mean_rankic"),
        "mean_ic_operating_cash_flow_to_net_profit": _factor_metric(summary, "operating_cash_flow_to_net_profit", "mean_ic"),
        "mean_rankic_operating_cash_flow_to_net_profit": _factor_metric(summary, "operating_cash_flow_to_net_profit", "mean_rankic"),
        "spec_path": str(spec_path),
        "panel_path": str(panel_path),
        "summary_path": str(summary_path),
    }


def _pm_decision(equal_return: float | None, composite_return: float | None, negative_rolling: int, profile: dict[str, Any]) -> str:
    if profile["median_codes_per_date"] < 8:
        return "sample_size_blocked"
    if equal_return is None or composite_return is None:
        return "validation_failed_missing_baseline"
    if composite_return <= 0 or composite_return <= equal_return:
        return "rejected_subsector_ocf_quality_not_superior"
    if negative_rolling > 1:
        return "research_signal_only_unstable_rolling"
    return "research_signal_candidate_needs_state_review"


def _skipped_row(sector_id: str, sub_industry: str, profile: dict[str, Any], min_codes_per_date: int) -> dict[str, Any]:
    return {
        "sector_id": sector_id,
        "sub_industry": sub_industry,
        **profile,
        "selection_count": "",
        "pm_decision": "sample_size_or_history_blocked",
        "equal_weight_return": "",
        "high_ocf_return": "",
        "ocf_to_net_profit_return": "",
        "ocf_quality_return": "",
        "negative_rolling_windows": "",
        "mean_ic_operating_cash_flow_yield": "",
        "mean_rankic_operating_cash_flow_yield": "",
        "mean_ic_operating_cash_flow_to_net_profit": "",
        "mean_rankic_operating_cash_flow_to_net_profit": "",
        "spec_path": "",
        "panel_path": "",
        "summary_path": "",
        "blocker": f"needs at least 12 dates and median {min_codes_per_date} codes per date",
    }


def _status(rows: list[dict[str, Any]]) -> str:
    if any(row.get("pm_decision") == "research_signal_candidate_needs_state_review" for row in rows):
        return "subsector_research_signal_found_not_engineering_handoff"
    if any(str(row.get("pm_decision", "")).startswith("research_signal_only") for row in rows):
        return "subsector_research_signal_only_needs_repair"
    return "subsector_validation_no_candidate"


def _factor_metric(summary: dict[str, Any], factor: str, metric: str) -> float | None:
    for row in summary.get("factor_ic_rankic", []):
        if row.get("factor") == factor:
            return _float_or_none(row.get(metric))
    return None


def _float_or_none(value: Any) -> float | None:
    if value in ("", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fieldnames(rows: list[dict[str, str]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    return names


def _result_fields() -> list[str]:
    return [
        "sector_id",
        "sub_industry",
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
        "ocf_to_net_profit_return",
        "ocf_quality_return",
        "negative_rolling_windows",
        "mean_ic_operating_cash_flow_yield",
        "mean_rankic_operating_cash_flow_yield",
        "mean_ic_operating_cash_flow_to_net_profit",
        "mean_rankic_operating_cash_flow_to_net_profit",
        "spec_path",
        "panel_path",
        "summary_path",
        "blocker",
    ]


def _safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value).strip("_") or "unknown"


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    rows = summary["result_rows"]
    lines = [
        f"# {summary['sector_id']} Consumer Subsector Validation",
        "",
        f"Status: `{summary['status']}`",
        "",
        "## Results",
        "",
        "| Subindustry | Decision | Equal | OCF Quality | Negative Rolling | Median Names |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| "
            f"`{row['sub_industry']}` | `{row['pm_decision']}` | "
            f"{row.get('equal_weight_return', '')} | {row.get('ocf_quality_return', '')} | "
            f"{row.get('negative_rolling_windows', '')} | {row.get('median_codes_per_date', '')} |"
        )
    lines.extend(
        [
            "",
            "## PM Rule",
            "",
            "These results may route a subsector back to Research/Quant. They do not approve Engineering handoff or platform replication.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

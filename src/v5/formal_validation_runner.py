from __future__ import annotations

import argparse
import copy
import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Any

from v5.engine import load_spec
from v5.experiment_governance import build_run_manifest, write_run_manifest
from v5.io_utils import write_csv_rows, write_json_file
from v5.math_utils import compound, pearson, ranks
from v5.scoring import apply_value_trap_guard, score_rows, to_float


def run_formal_validation(
    spec_path: Path,
    panel_path: Path,
    out_dir: Path,
    experiment_layer: str = "research_pit_validation",
) -> Path:
    if experiment_layer != "research_pit_validation":
        raise ValueError("formal validation must run as research_pit_validation")
    spec = load_spec(spec_path)
    rows = _load_panel(panel_path)
    out = out_dir / spec.strategy_id
    out.mkdir(parents=True, exist_ok=True)
    leakage_rows = _notice_date_leakage_audit(rows)
    rolling_rows = _rolling_validation(rows, spec.raw)
    baseline_rows = _baseline_tests(rows, spec.raw)
    ablation_rows = _ablation_tests(rows, spec.raw)
    robustness_rows = _robustness_tests(rows, spec.raw)
    interaction_rows = _common_sample_interaction_tests(rows, spec.raw)
    factor_rows = _factor_ic_rankic(rows, spec.raw)
    failure_rows = _failure_mode_analysis(rows, spec.raw, weak_years=_weak_years(spec.raw))
    _write_csv(out / "notice_date_leakage_audit.csv", list(leakage_rows[0].keys()) if leakage_rows else ["check", "status", "detail"], leakage_rows)
    _write_csv(out / "rolling_validation.csv", list(rolling_rows[0].keys()) if rolling_rows else ["window", "status"], rolling_rows)
    _write_csv(out / "baseline_tests.csv", list(baseline_rows[0].keys()), baseline_rows)
    _write_csv(out / "ablation_tests.csv", list(ablation_rows[0].keys()), ablation_rows)
    _write_csv(out / "robustness_tests.csv", list(robustness_rows[0].keys()), robustness_rows)
    _write_csv(out / "common_sample_interaction_tests.csv", list(interaction_rows[0].keys()), interaction_rows)
    _write_csv(out / "factor_ic_rankic.csv", list(factor_rows[0].keys()) if factor_rows else ["factor"], factor_rows)
    _write_csv(out / "failure_mode_analysis.csv", list(failure_rows[0].keys()) if failure_rows else ["year"], failure_rows)
    summary = {
        "strategy_id": spec.strategy_id,
        "experiment_layer": experiment_layer,
        "panel": str(panel_path),
        "row_count": len(rows),
        "date_count": len({row["trade_date"] for row in rows}),
        "status": "formal_validation_completed_not_acceptance",
        "notice_date_leakage_audit": leakage_rows,
        "rolling_validation": rolling_rows,
        "baseline_tests": baseline_rows,
        "ablation_tests": ablation_rows,
        "robustness_tests": robustness_rows,
        "common_sample_interaction_tests": interaction_rows,
        "factor_ic_rankic": factor_rows,
        "failure_mode_analysis": failure_rows,
        "governance": "Do not use 2021-2026 platform-confirmation results for tuning. Single-model acceptance requires rolling validation.",
    }
    _write_json(out / "formal_validation_summary.json", summary)
    write_run_manifest(
        out / "RUN_MANIFEST.json",
        build_run_manifest(
            strategy_id=spec.strategy_id,
            experiment_layer=experiment_layer,
            command_profile={"spec": str(spec_path), "panel": str(panel_path), "out": str(out_dir)},
            outputs={
                "formal_validation_summary": "formal_validation_summary.json",
                "formal_validation_report": "formal_validation_report.md",
                "notice_date_leakage_audit": "notice_date_leakage_audit.csv",
                "rolling_validation": "rolling_validation.csv",
                "baseline_tests": "baseline_tests.csv",
                "ablation_tests": "ablation_tests.csv",
                "robustness_tests": "robustness_tests.csv",
                "common_sample_interaction_tests": "common_sample_interaction_tests.csv",
                "factor_ic_rankic": "factor_ic_rankic.csv",
                "failure_mode_analysis": "failure_mode_analysis.csv",
            },
            warnings=["Formal validation output is evidence, not automatic strategy acceptance."],
        ),
    )
    _write_report(out / "formal_validation_report.md", summary)
    return out / "formal_validation_report.md"


def _notice_date_leakage_audit(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pit_sensitive_fields = [
        "asset_quality_trend",
        "provision_buffer",
        "capital_resilience",
        "non_performing_loan_ratio",
        "provision_coverage_ratio",
        "core_tier_1_capital_adequacy_ratio",
        "return_on_equity_ttm",
        "dividend_yield",
    ]
    bank_quality_fields = [
        "non_performing_loan_ratio",
        "provision_coverage_ratio",
        "core_tier_1_capital_adequacy_ratio",
        "asset_quality_trend",
        "provision_buffer",
        "capital_resilience",
    ]
    checked = 0
    missing_notice = 0
    violations = 0
    for row in rows:
        fields_present = any(row.get(name) not in {None, ""} for name in pit_sensitive_fields)
        if not fields_present:
            continue
        checked += 1
        has_bank_quality = any(row.get(name) not in {None, ""} for name in bank_quality_fields)
        if has_bank_quality:
            notice = row.get("bank_quality_notice_date") or row.get("eastmoney_quality_notice_date")
        else:
            notice = row.get("factor_visible_date") or row.get("notice_date") or row.get("announce_date")
        if not notice:
            missing_notice += 1
            continue
        if str(notice)[:10] > str(row.get("trade_date", ""))[:10]:
            violations += 1
    status = "pass" if violations == 0 and missing_notice == 0 else "needs_review"
    return [
        {
            "check": "pit_factor_visible_date_audit",
            "status": status,
            "checked_rows": checked,
            "missing_notice_date_rows": missing_notice,
            "future_notice_violations": violations,
            "detail": "PIT-sensitive factor fields used in formal validation must have visible_date <= trade_date.",
        }
    ]


def _rolling_validation(rows: list[dict[str, Any]], raw: dict[str, Any]) -> list[dict[str, Any]]:
    years = sorted({str(row["trade_date"])[:4] for row in rows if row.get("trade_date")})
    result = []
    if len(years) < 4:
        return [{"window": "insufficient_history", "status": "skipped", "cum_return": None, "positive_ratio": None, "mean_selected_count": None}]
    for index in range(2, len(years)):
        test_year = years[index]
        window_rows = [row for row in rows if str(row["trade_date"]).startswith(test_year)]
        case = _strategy_case(f"rolling_test_{test_year}", window_rows, raw, mode="composite")
        result.append({"window": test_year, "status": "completed", **case})
    return result


def _baseline_tests(rows: list[dict[str, Any]], raw: dict[str, Any]) -> list[dict[str, Any]]:
    configured = raw.get("validation", {}).get("baselines")
    if configured:
        result = []
        for item in configured:
            mode = str(item.get("mode", "composite"))
            result.append(
                _strategy_case(
                    str(item["name"]),
                    rows,
                    raw,
                    mode=mode,
                    factor=item.get("factor"),
                    selection_count=item.get("selection_count"),
                    factor_direction=item.get("direction"),
                    condition=item.get("condition"),
                )
            )
        return result
    return [
        _strategy_case("equal_weight_all_banks", rows, raw, mode="equal_all"),
        _strategy_case("low_pb_top8", rows, raw, mode="single_factor", factor="low_price_to_book"),
        _strategy_case("composite_current", rows, raw, mode="composite"),
    ]


def _ablation_tests(rows: list[dict[str, Any]], raw: dict[str, Any]) -> list[dict[str, Any]]:
    result = [_strategy_case("composite_current", rows, raw, mode="composite")]
    factors = raw["signals"]["factors"]
    for factor in factors:
        result.append(_strategy_case(f"drop_{factor['name']}", rows, raw, mode="composite", drop_factor=factor["name"]))
    return result


def _robustness_tests(rows: list[dict[str, Any]], raw: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    robustness = raw.get("validation", {}).get("robustness", {})
    selection_counts = robustness.get("selection_counts", [6, 8, 10])
    weight_scale_factors = robustness.get("weight_scale_factors", ["low_price_to_book", "dividend_yield"])
    weight_scales = robustness.get("weight_scales", [0.8, 1.0, 1.2])
    for count in selection_counts:
        result.append(_strategy_case(f"selection_count_{count}", rows, raw, mode="composite", selection_count=count))
    for scale in weight_scales:
        result.append(
            _strategy_case(
                f"weight_scale_{scale}",
                rows,
                raw,
                mode="composite",
                weight_scale={name: scale for name in weight_scale_factors},
            )
        )
    return result


def _common_sample_interaction_tests(rows: list[dict[str, Any]], raw: dict[str, Any]) -> list[dict[str, Any]]:
    validation = raw.get("validation", {})
    common_required = validation.get(
        "common_sample_fields",
        [
            "dividend_yield",
            "return_on_equity_ttm",
            "low_price_to_book",
            "provision_coverage_ratio",
            "core_tier_1_capital_adequacy_ratio",
        ],
    )
    common_rows = [row for row in rows if all(to_float(row.get(name)) is not None for name in common_required)]
    common_date_count = len({row["trade_date"] for row in common_rows})
    common_security_count = len({row["code"] for row in common_rows})
    configured_cases = validation.get("common_sample_interactions")
    if configured_cases:
        cases = [(str(item["name"]), list(item["factors"])) for item in configured_cases]
    else:
        cases = [
            ("common_high_dividend_only", ["dividend_yield"]),
            ("common_high_dividend_plus_roe", ["dividend_yield", "return_on_equity_ttm"]),
            ("common_high_dividend_plus_low_pb", ["dividend_yield", "low_price_to_book"]),
            ("common_high_dividend_plus_provision", ["dividend_yield", "provision_coverage_ratio"]),
            ("common_high_dividend_plus_capital", ["dividend_yield", "core_tier_1_capital_adequacy_ratio"]),
            (
                "common_high_dividend_plus_provision_capital",
                ["dividend_yield", "provision_coverage_ratio", "core_tier_1_capital_adequacy_ratio"],
            ),
            ("common_high_dividend_all_support", common_required),
        ]
    result = []
    for name, factors in cases:
        row = _strategy_case(name, common_rows, raw, mode="composite", use_factors=factors)
        row["common_sample_rows"] = len(common_rows)
        row["common_sample_dates"] = common_date_count
        row["common_sample_securities"] = common_security_count
        row["required_common_fields"] = ";".join(common_required)
        row["tested_factors"] = ";".join(factors)
        row["status"] = "completed" if common_date_count >= 4 else "insufficient_common_sample"
        result.append(row)
    return result


def _factor_ic_rankic(rows: list[dict[str, Any]], raw: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    factors = raw["signals"]["factors"]
    for factor in factors:
        name = factor["name"]
        direction = factor.get("direction", "higher_is_better")
        by_date: dict[str, list[tuple[float, float]]] = defaultdict(list)
        observations = 0
        for row in rows:
            value = to_float(row.get(name))
            ret = to_float(row.get("future_return"))
            if value is None or ret is None:
                continue
            adjusted = -value if direction == "lower_is_better" else value
            by_date[row["trade_date"]].append((adjusted, ret))
            observations += 1
        ic_values = []
        rank_ic_values = []
        spreads = []
        for pairs in by_date.values():
            if len(pairs) < 3:
                continue
            x = [item[0] for item in pairs]
            y = [item[1] for item in pairs]
            ic = _pearson(x, y)
            rank_ic = _pearson(_ranks(x), _ranks(y))
            spread = _top_bottom_spread(pairs)
            if ic is not None:
                ic_values.append(ic)
            if rank_ic is not None:
                rank_ic_values.append(rank_ic)
            if spread is not None:
                spreads.append(spread)
        result.append(
            {
                "factor": name,
                "direction": direction,
                "observations": observations,
                "dates": len(ic_values),
                "mean_ic": mean(ic_values) if ic_values else None,
                "mean_rankic": mean(rank_ic_values) if rank_ic_values else None,
                "positive_ic_ratio": _positive_ratio(ic_values),
                "top_minus_bottom_mean_return": mean(spreads) if spreads else None,
            }
        )
    return result


def _failure_mode_analysis(rows: list[dict[str, Any]], raw: dict[str, Any], weak_years: list[str]) -> list[dict[str, Any]]:
    result = []
    factors = raw["signals"]["factors"]
    weights = dict(raw["signals"]["scoring"].get("weights", {}))
    selection_count = int(raw["portfolio"]["selection_count"])
    for year in weak_years:
        year_rows = [row for row in rows if str(row.get("trade_date", "")).startswith(year)]
        by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in year_rows:
            by_date[row["trade_date"]].append(row)
        selected_returns = []
        all_returns = []
        low_pb_returns = []
        selected_factor_values: dict[str, list[float]] = defaultdict(list)
        all_factor_values: dict[str, list[float]] = defaultdict(list)
        selected_codes_by_date = []
        for trade_date, date_rows in sorted(by_date.items()):
            case_raw = _scoring_case_raw(raw, factors=factors, weights=weights)
            scored, _used_factors = score_rows(case_raw, date_rows)
            selected = sorted(apply_value_trap_guard(case_raw, scored), key=lambda item: item["score"], reverse=True)[:selection_count]
            low_pb = sorted(
                [row for row in date_rows if to_float(row.get("low_price_to_book")) is not None],
                key=lambda row: to_float(row.get("low_price_to_book")) or 0.0,
            )[:selection_count]
            if selected:
                selected_returns.append(mean(float(row["future_return"]) for row in selected))
                selected_codes_by_date.append(f"{trade_date}:{';'.join(row['code'] for row in selected)}")
            if date_rows:
                all_returns.append(mean(float(row["future_return"]) for row in date_rows))
            if low_pb:
                low_pb_returns.append(mean(float(row["future_return"]) for row in low_pb))
            for row in date_rows:
                for factor in factors:
                    value = to_float(row.get(factor["name"]))
                    if value is not None:
                        all_factor_values[factor["name"]].append(value)
            for row in selected:
                for factor in factors:
                    value = to_float(row.get(factor["name"]))
                    if value is not None:
                        selected_factor_values[factor["name"]].append(value)
        factor_notes = []
        for factor in factors:
            name = factor["name"]
            selected_mean = mean(selected_factor_values[name]) if selected_factor_values[name] else None
            all_mean = mean(all_factor_values[name]) if all_factor_values[name] else None
            factor_notes.append(f"{name}:selected_mean={selected_mean},all_mean={all_mean}")
        result.append(
            {
                "year": year,
                "periods": len(by_date),
                "selected_cum_return": _compound(selected_returns),
                "selected_mean_return": mean(selected_returns) if selected_returns else None,
                "selected_positive_ratio": _positive_ratio(selected_returns),
                "all_universe_mean_return": mean(all_returns) if all_returns else None,
                "low_pb_mean_return": mean(low_pb_returns) if low_pb_returns else None,
                "relative_to_all_universe_mean": (mean(selected_returns) - mean(all_returns)) if selected_returns and all_returns else None,
                "relative_to_low_pb_mean": (mean(selected_returns) - mean(low_pb_returns)) if selected_returns and low_pb_returns else None,
                "selected_codes_by_date": " | ".join(selected_codes_by_date),
                "factor_mean_notes": " ; ".join(factor_notes),
                "interpretation": _failure_interpretation(year, selected_returns, all_returns, low_pb_returns),
            }
        )
    return result


def _strategy_case(
    name: str,
    rows: list[dict[str, Any]],
    raw: dict[str, Any],
    mode: str,
    factor: str | None = None,
    drop_factor: str | None = None,
    selection_count: int | None = None,
    weight_scale: dict[str, float] | None = None,
    use_factors: list[str] | None = None,
    factor_direction: str | None = None,
    condition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_date[row["trade_date"]].append(row)
    returns = []
    selected_counts = []
    current_selection_count = int(selection_count or raw["portfolio"]["selection_count"])
    factors = [
        dict(item)
        for item in raw["signals"]["factors"]
        if item["name"] != drop_factor and (use_factors is None or item["name"] in use_factors)
    ]
    weights = dict(raw["signals"]["scoring"].get("weights", {}))
    if drop_factor:
        weights.pop(drop_factor, None)
    if weight_scale:
        for key, scale in weight_scale.items():
            if key in weights:
                weights[key] = float(weights[key]) * scale
    for _date, date_rows in sorted(by_date.items()):
        case_rows = _apply_condition(date_rows, condition)
        if mode == "equal_all":
            selected = case_rows
        elif mode == "single_factor" and factor:
            current_factor_direction = factor_direction or _factor_direction(raw, factor)
            selected = sorted(
                [row for row in case_rows if to_float(row.get(factor)) is not None],
                key=lambda row: to_float(row.get(factor)) or 0.0,
                reverse=current_factor_direction == "higher_is_better",
            )[:current_selection_count]
        else:
            case_raw = _scoring_case_raw(raw, factors=factors, weights=weights, weight_scale=weight_scale)
            scored, _used_factors = score_rows(case_raw, case_rows)
            selected = sorted(apply_value_trap_guard(case_raw, scored), key=lambda item: item["score"], reverse=True)[:current_selection_count]
        if selected:
            returns.append(mean(float(row["future_return"]) for row in selected))
            selected_counts.append(len(selected))
        else:
            returns.append(0.0)
            selected_counts.append(0)
    return {
        "case": name,
        "periods": len(returns),
        "cum_return": _compound(returns),
        "mean_return": mean(returns) if returns else None,
        "positive_ratio": sum(1 for ret in returns if ret > 0) / len(returns) if returns else None,
        "mean_selected_count": mean(selected_counts) if selected_counts else None,
    }


def _scoring_case_raw(
    raw: dict[str, Any],
    factors: list[dict[str, Any]],
    weights: dict[str, float],
    weight_scale: dict[str, float] | None = None,
) -> dict[str, Any]:
    case_raw = copy.deepcopy(raw)
    allowed_names = {factor["name"] for factor in factors}
    case_raw["signals"]["factors"] = factors
    scoring = case_raw["signals"]["scoring"]
    _adjust_min_factor_count(scoring, len(factors))
    if "weights" in scoring:
        scoring["weights"] = {
            name: float(weight)
            for name, weight in weights.items()
            if name in allowed_names
        }
    for group_name in ("value_score", "quality_score"):
        if group_name in scoring:
            scoring[group_name] = {
                name: _scaled_weight(name, float(weight), weight_scale)
                for name, weight in scoring[group_name].items()
                if name in allowed_names
            }
    return case_raw


def _adjust_min_factor_count(scoring: dict[str, Any], available_factor_count: int) -> None:
    if available_factor_count <= 0:
        scoring["min_factor_count"] = 0
        return
    original = int(scoring.get("min_factor_count", 1) or 1)
    scoring["min_factor_count"] = max(1, min(original, available_factor_count))


def _scaled_weight(name: str, weight: float, weight_scale: dict[str, float] | None) -> float:
    if weight_scale and name in weight_scale:
        return weight * float(weight_scale[name])
    return weight


def _apply_condition(rows: list[dict[str, Any]], condition: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not condition:
        return rows
    field = str(condition.get("field", ""))
    if not field:
        return rows
    direction = str(condition.get("direction", _factor_direction({"signals": {"factors": []}}, field)))
    quantile = float(condition.get("quantile", 0.5))
    keep = str(condition.get("keep", "top"))
    ranked = [row for row in rows if to_float(row.get(field)) is not None]
    if not ranked:
        return []
    ranked = sorted(
        ranked,
        key=lambda row: to_float(row.get(field)) or 0.0,
        reverse=direction == "higher_is_better",
    )
    count = max(1, int(len(ranked) * quantile))
    if keep == "bottom":
        return ranked[-count:]
    return ranked[:count]


def _load_panel(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = []
    for row in rows:
        ret = to_float(row.get("total_return"))
        if ret is None:
            ret = to_float(row.get("future_return"))
        if row.get("trade_date") and row.get("code") and ret is not None:
            item = dict(row)
            item["future_return"] = ret
            result.append(item)
    return result


_compound = compound


def _positive_ratio(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(1 for value in values if value > 0) / len(values)


_pearson = pearson


_ranks = ranks


def _top_bottom_spread(pairs: list[tuple[float, float]]) -> float | None:
    if len({value for value, _ret in pairs}) < 2:
        return None
    ordered = sorted(pairs, key=lambda item: item[0])
    group_size = max(1, len(ordered) // 3)
    bottom = ordered[:group_size]
    top = ordered[-group_size:]
    return mean(ret for _value, ret in top) - mean(ret for _value, ret in bottom)


def _failure_interpretation(year: str, selected_returns: list[float], all_returns: list[float], low_pb_returns: list[float]) -> str:
    if not selected_returns:
        return "No selected periods."
    selected_mean = mean(selected_returns)
    all_mean = mean(all_returns) if all_returns else None
    low_pb_mean = mean(low_pb_returns) if low_pb_returns else None
    notes = []
    if all_mean is not None:
        notes.append("underperformed_all_universe" if selected_mean < all_mean else "outperformed_all_universe")
    if low_pb_mean is not None:
        notes.append("underperformed_low_pb" if selected_mean < low_pb_mean else "outperformed_low_pb")
    if _positive_ratio(selected_returns) is not None and (_positive_ratio(selected_returns) or 0) < 0.5:
        notes.append("low_positive_period_ratio")
    return f"{year}: " + ",".join(notes)


def _weak_years(raw: dict[str, Any]) -> list[str]:
    years = raw.get("validation", {}).get("weak_years")
    if years:
        return [str(year) for year in years]
    return ["2018", "2021"]


def _factor_direction(raw: dict[str, Any], factor_name: str) -> str:
    for factor in raw.get("signals", {}).get("factors", []):
        if factor.get("name") == factor_name:
            return str(factor.get("direction", "higher_is_better"))
    return "higher_is_better"


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [f"# Formal Validation Report: {summary['strategy_id']}", "", f"- Status: `{summary['status']}`", ""]
    for section in [
        "notice_date_leakage_audit",
        "factor_ic_rankic",
        "rolling_validation",
        "baseline_tests",
        "ablation_tests",
        "robustness_tests",
        "common_sample_interaction_tests",
        "failure_mode_analysis",
    ]:
        lines.extend([f"## {section}", ""])
        for row in summary[section]:
            label = row.get("case") or row.get("check") or row.get("window")
            lines.append(f"- `{label}`: {row}")
        lines.append("")
    lines.extend(["## Governance", "", summary["governance"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    write_csv_rows(path, fieldnames, rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    write_json_file(path, payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-formal-validation")
    parser.add_argument("spec", type=Path)
    parser.add_argument("panel", type=Path)
    parser.add_argument("--out", type=Path, default=Path("validation_formal"))
    parser.add_argument("--experiment-layer", default="research_pit_validation")
    args = parser.parse_args(argv)
    print(run_formal_validation(args.spec, args.panel, args.out, args.experiment_layer))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

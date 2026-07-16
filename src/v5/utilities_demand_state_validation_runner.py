from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Iterable


DEFAULT_PANEL = Path("数据库") / "processed" / "utilities_cashflow_value_v51b_panel" / "panel.csv"
DEFAULT_STATE_PANEL = Path("数据库") / "processed" / "utilities_external_state" / "utilities_external_state.csv"
DEFAULT_OUT_DIR = Path("validation_formal_v51e")

FACTOR_CASES = {
    "raw_low_pb_utilities_top10": ("low_price_to_book", "lower_is_better"),
    "raw_cashflow_yield_utilities_top10": ("operating_cash_flow_yield", "higher_is_better"),
    "raw_high_dividend_utilities_top10": ("dividend_yield", "higher_is_better"),
    "subindustry_low_pb_top10": ("low_pb_subindustry_score", "higher_is_better"),
    "subindustry_cashflow_top10": ("cashflow_yield_subindustry_score", "higher_is_better"),
}

ROLLING_RULES: dict[str, Callable[[str], str]] = {
    "demand_state_cashflow_else_low_pb": lambda bucket: (
        "raw_low_pb_utilities_top10" if bucket == "strong" else "raw_cashflow_yield_utilities_top10"
    ),
    "demand_state_cashflow_subcashflow_low_pb": lambda bucket: (
        "raw_cashflow_yield_utilities_top10"
        if bucket == "weak"
        else ("subindustry_cashflow_top10" if bucket == "mid" else "raw_low_pb_utilities_top10")
    ),
    "demand_state_dividend_cashflow_low_pb": lambda bucket: (
        "raw_high_dividend_utilities_top10"
        if bucket == "weak"
        else ("raw_cashflow_yield_utilities_top10" if bucket == "mid" else "raw_low_pb_utilities_top10")
    ),
}

RULE_DESCRIPTIONS = {
    "demand_state_cashflow_else_low_pb": "Use operating cash-flow yield unless expanding electricity-demand YoY is strong; use low PB in strong-demand states. Warmup periods use cash-flow yield.",
    "demand_state_cashflow_subcashflow_low_pb": "Use cash-flow yield in weak demand, subindustry cash-flow in mid demand, and low PB in strong demand. Warmup periods use cash-flow yield.",
    "demand_state_dividend_cashflow_low_pb": "Use high dividend in weak demand, cash-flow yield in mid demand, and low PB in strong demand. Warmup periods use cash-flow yield.",
}


def run_utilities_demand_state_validation(
    panel_path: Path = DEFAULT_PANEL,
    state_panel_path: Path = DEFAULT_STATE_PANEL,
    out_dir: Path = DEFAULT_OUT_DIR,
    metric: str = "electricity_consumption_yoy",
    selection_count: int = 10,
    min_history: int = 8,
) -> Path:
    rows = _read_csv(panel_path)
    states = _read_csv(state_panel_path)
    by_date = _group_by_date(rows)
    state_by_date = _latest_visible_state_by_date(by_date, states, metric)
    if not state_by_date:
        raise RuntimeError(f"no visible external state rows found for metric={metric}")

    out = out_dir / "utilities_demand_state_v51e"
    out.mkdir(parents=True, exist_ok=True)

    coverage_rows = _coverage_rows(by_date, state_by_date)
    full_bucket_rows = _full_sample_bucket_tests(by_date, state_by_date, selection_count)
    rolling_rows, rolling_date_rows = _rolling_rule_tests(by_date, state_by_date, selection_count, min_history)
    yearly_rows = _yearly_comparison(by_date, state_by_date, selection_count, min_history)
    state_ic_rows = _state_conditioned_factor_ic(by_date, state_by_date, min_history)
    selection_robustness_rows = _selection_count_robustness(by_date, state_by_date, [8, 10, 12], min_history)
    failure_rows = _failure_year_analysis(by_date, state_by_date, min_history, selection_count)

    _write_csv(out / "state_coverage.csv", coverage_rows[0].keys(), coverage_rows)
    _write_csv(out / "full_sample_state_bucket_tests.csv", full_bucket_rows[0].keys(), full_bucket_rows)
    _write_csv(out / "rolling_state_model_tests.csv", rolling_rows[0].keys(), rolling_rows)
    _write_csv(out / "rolling_state_date_choices.csv", rolling_date_rows[0].keys(), rolling_date_rows)
    _write_csv(out / "yearly_comparison.csv", yearly_rows[0].keys(), yearly_rows)
    _write_csv(out / "state_conditioned_factor_ic.csv", state_ic_rows[0].keys(), state_ic_rows)
    _write_csv(out / "selection_count_robustness.csv", selection_robustness_rows[0].keys(), selection_robustness_rows)
    _write_csv(out / "failure_year_analysis.csv", failure_rows[0].keys(), failure_rows)

    summary = _decision_summary(
        metric,
        panel_path,
        state_panel_path,
        coverage_rows,
        full_bucket_rows,
        rolling_rows,
        yearly_rows,
        state_ic_rows,
        selection_robustness_rows,
        failure_rows,
    )
    _write_json(out / "demand_state_validation_summary.json", summary)
    _write_report(out / "demand_state_validation_report.md", summary)
    return out / "demand_state_validation_report.md"


def _coverage_rows(by_date: dict[str, list[dict[str, str]]], state_by_date: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for trade_date in sorted(by_date):
        state = state_by_date.get(trade_date)
        rows.append(
            {
                "trade_date": trade_date,
                "panel_rows": len(by_date[trade_date]),
                "has_state": str(state is not None).lower(),
                "state_visible_date": state.get("visible_date") if state else "",
                "state_date": state.get("state_date") if state else "",
                "state_value": state.get("value") if state else "",
            }
        )
    return rows


def _full_sample_bucket_tests(
    by_date: dict[str, list[dict[str, str]]],
    state_by_date: dict[str, dict[str, Any]],
    selection_count: int,
) -> list[dict[str, Any]]:
    values = sorted(float(item["value"]) for item in state_by_date.values())
    q33, q67 = _tertiles(values)
    buckets = {
        "weak": lambda value: value <= q33,
        "mid": lambda value: q33 < value < q67,
        "strong": lambda value: value >= q67,
        "all": lambda _value: True,
    }
    result = []
    for bucket_name, predicate in buckets.items():
        dates = [trade_date for trade_date, state in sorted(state_by_date.items()) if predicate(float(state["value"]))]
        for case_name in ["equal_weight_utilities", *FACTOR_CASES.keys()]:
            returns = [_case_return(by_date[trade_date], case_name, selection_count) for trade_date in dates]
            returns = [value for value in returns if value is not None]
            result.append(
                {
                    "bucket": bucket_name,
                    "case": case_name,
                    "periods": len(returns),
                    "cum_return": _compound(returns),
                    "mean_return": mean(returns) if returns else None,
                    "positive_ratio": _positive_ratio(returns),
                    "q33": q33,
                    "q67": q67,
                }
            )
    return result


def _rolling_rule_tests(
    by_date: dict[str, list[dict[str, str]]],
    state_by_date: dict[str, dict[str, Any]],
    selection_count: int,
    min_history: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    returns_by_case: dict[str, list[float]] = defaultdict(list)
    date_rows = []
    history: list[float] = []
    case_names = ["equal_weight_utilities", *FACTOR_CASES.keys(), *ROLLING_RULES.keys()]
    for trade_date, state in sorted(state_by_date.items()):
        state_value = float(state["value"])
        bucket = _expanding_bucket(history, state_value, min_history)
        choices: dict[str, str] = {}
        for case_name in ["equal_weight_utilities", *FACTOR_CASES.keys()]:
            ret = _case_return(by_date[trade_date], case_name, selection_count)
            if ret is not None:
                returns_by_case[case_name].append(ret)
        for rule_name, chooser in ROLLING_RULES.items():
            chosen_case = "raw_cashflow_yield_utilities_top10" if bucket == "warmup" else chooser(bucket)
            choices[rule_name] = chosen_case
            ret = _case_return(by_date[trade_date], chosen_case, selection_count)
            if ret is not None:
                returns_by_case[rule_name].append(ret)
        date_rows.append(
            {
                "trade_date": trade_date,
                "state_visible_date": state["visible_date"],
                "state_date": state["state_date"],
                "state_value": state_value,
                "expanding_bucket": bucket,
                "chosen_case_primary": choices.get("demand_state_cashflow_else_low_pb", ""),
                "chosen_case_secondary": choices.get("demand_state_cashflow_subcashflow_low_pb", ""),
            }
        )
        history.append(state_value)
    result = []
    for case_name in case_names:
        returns = returns_by_case.get(case_name, [])
        result.append(
            {
                "case": case_name,
                "periods": len(returns),
                "cum_return": _compound(returns),
                "mean_return": mean(returns) if returns else None,
                "positive_ratio": _positive_ratio(returns),
                "mean_selected_count": selection_count if case_name != "equal_weight_utilities" else None,
            }
        )
    return sorted(result, key=lambda row: (row["cum_return"] is not None, row["cum_return"]), reverse=True), date_rows


def _yearly_comparison(
    by_date: dict[str, list[dict[str, str]]],
    state_by_date: dict[str, dict[str, Any]],
    selection_count: int,
    min_history: int,
) -> list[dict[str, Any]]:
    history: list[float] = []
    by_year: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for trade_date, state in sorted(state_by_date.items()):
        year = trade_date[:4]
        state_value = float(state["value"])
        bucket = _expanding_bucket(history, state_value, min_history)
        primary_case = "raw_cashflow_yield_utilities_top10" if bucket == "warmup" else ROLLING_RULES["demand_state_cashflow_else_low_pb"](bucket)
        primary_ret = _case_return(by_date[trade_date], primary_case, selection_count)
        if primary_ret is not None:
            by_year[year]["demand_state_cashflow_else_low_pb"].append(primary_ret)
        for case_name in ["raw_low_pb_utilities_top10", "raw_cashflow_yield_utilities_top10"]:
            ret = _case_return(by_date[trade_date], case_name, selection_count)
            if ret is not None:
                by_year[year][case_name].append(ret)
        history.append(state_value)
    result = []
    for year, values in sorted(by_year.items()):
        primary = values.get("demand_state_cashflow_else_low_pb", [])
        low_pb = values.get("raw_low_pb_utilities_top10", [])
        cashflow = values.get("raw_cashflow_yield_utilities_top10", [])
        result.append(
            {
                "year": year,
                "periods": len(primary),
                "demand_state_cum_return": _compound(primary),
                "low_pb_cum_return": _compound(low_pb),
                "cashflow_cum_return": _compound(cashflow),
                "beats_low_pb": str((_compound(primary) or -999) > (_compound(low_pb) or -999)).lower(),
                "beats_cashflow": str((_compound(primary) or -999) > (_compound(cashflow) or -999)).lower(),
            }
        )
    return result


def _state_conditioned_factor_ic(
    by_date: dict[str, list[dict[str, str]]],
    state_by_date: dict[str, dict[str, Any]],
    min_history: int,
) -> list[dict[str, Any]]:
    history: list[float] = []
    bucket_by_date = {}
    for trade_date, state in sorted(state_by_date.items()):
        value = float(state["value"])
        bucket_by_date[trade_date] = _expanding_bucket(history, value, min_history)
        history.append(value)

    result = []
    for bucket in ["warmup", "weak", "mid", "strong", "all"]:
        dates = [trade_date for trade_date in sorted(by_date) if bucket == "all" or bucket_by_date.get(trade_date) == bucket]
        for case_name, (factor, direction) in FACTOR_CASES.items():
            ic_values = []
            rank_ic_values = []
            spreads = []
            observations = 0
            for trade_date in dates:
                pairs = []
                for row in by_date[trade_date]:
                    factor_value = _to_float(row.get(factor))
                    ret = _to_float(row.get("future_return"))
                    if factor_value is None or ret is None:
                        continue
                    adjusted = -factor_value if direction == "lower_is_better" else factor_value
                    pairs.append((adjusted, ret))
                    observations += 1
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
                    "bucket": bucket,
                    "factor_case": case_name,
                    "factor": factor,
                    "observations": observations,
                    "dates": len(ic_values),
                    "mean_ic": mean(ic_values) if ic_values else None,
                    "mean_rankic": mean(rank_ic_values) if rank_ic_values else None,
                    "positive_ic_ratio": _positive_ratio(ic_values),
                    "top_minus_bottom_mean_return": mean(spreads) if spreads else None,
                }
            )
    return result


def _selection_count_robustness(
    by_date: dict[str, list[dict[str, str]]],
    state_by_date: dict[str, dict[str, Any]],
    selection_counts: list[int],
    min_history: int,
) -> list[dict[str, Any]]:
    result = []
    for count in selection_counts:
        rolling_rows, _date_rows = _rolling_rule_tests(by_date, state_by_date, count, min_history)
        by_case = {row["case"]: row for row in rolling_rows}
        low_pb = by_case["raw_low_pb_utilities_top10"]
        cashflow = by_case["raw_cashflow_yield_utilities_top10"]
        for rule_name in ROLLING_RULES:
            candidate = by_case[rule_name]
            result.append(
                {
                    "rule": rule_name,
                    "selection_count": count,
                    "candidate_cum_return": candidate["cum_return"],
                    "low_pb_cum_return": low_pb["cum_return"],
                    "cashflow_cum_return": cashflow["cum_return"],
                    "candidate_positive_ratio": candidate["positive_ratio"],
                    "beats_low_pb": str((candidate["cum_return"] or -999) > (low_pb["cum_return"] or -999)).lower(),
                    "beats_cashflow": str((candidate["cum_return"] or -999) > (cashflow["cum_return"] or -999)).lower(),
                    "status": "pass"
                    if (candidate["cum_return"] or -999) > (low_pb["cum_return"] or -999)
                    and (candidate["cum_return"] or -999) > (cashflow["cum_return"] or -999)
                    else "needs_review",
                }
            )
    return result


def _failure_year_analysis(
    by_date: dict[str, list[dict[str, str]]],
    state_by_date: dict[str, dict[str, Any]],
    min_history: int,
    selection_count: int,
) -> list[dict[str, Any]]:
    yearly_by_rule: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    choices_by_rule_year: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    buckets_by_rule_year: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    history: list[float] = []
    for trade_date, state in sorted(state_by_date.items()):
        year = trade_date[:4]
        state_value = float(state["value"])
        bucket = _expanding_bucket(history, state_value, min_history)
        for baseline in ["raw_low_pb_utilities_top10", "raw_cashflow_yield_utilities_top10"]:
            ret = _case_return(by_date[trade_date], baseline, selection_count)
            if ret is not None:
                for rule_name in ROLLING_RULES:
                    yearly_by_rule[rule_name][year][baseline].append(ret)
        for rule_name, chooser in ROLLING_RULES.items():
            chosen = "raw_cashflow_yield_utilities_top10" if bucket == "warmup" else chooser(bucket)
            ret = _case_return(by_date[trade_date], chosen, selection_count)
            if ret is not None:
                yearly_by_rule[rule_name][year][rule_name].append(ret)
            choices_by_rule_year[rule_name][year].append(chosen)
            buckets_by_rule_year[rule_name][year].append(bucket)
        history.append(state_value)

    result = []
    for rule_name, by_year in sorted(yearly_by_rule.items()):
        for year, values in sorted(by_year.items()):
            candidate = _compound(values.get(rule_name, []))
            low_pb = _compound(values.get("raw_low_pb_utilities_top10", []))
            cashflow = _compound(values.get("raw_cashflow_yield_utilities_top10", []))
            beats_low_pb = (candidate or -999) > (low_pb or -999)
            beats_cashflow = (candidate or -999) > (cashflow or -999)
            if beats_low_pb and beats_cashflow:
                status = "pass"
                interpretation = "Demand-state switching beat both major baselines."
            elif beats_low_pb or beats_cashflow:
                status = "mixed"
                interpretation = "Demand-state switching helped versus one baseline but did not dominate."
            else:
                status = "fail"
                interpretation = "Demand-state switching did not beat the two major baselines; retain as failure-year evidence."
            result.append(
                {
                    "rule": rule_name,
                    "year": year,
                    "status": status,
                    "candidate_cum_return": candidate,
                    "low_pb_cum_return": low_pb,
                    "cashflow_cum_return": cashflow,
                    "buckets": ";".join(buckets_by_rule_year[rule_name].get(year, [])),
                    "chosen_cases": ";".join(choices_by_rule_year[rule_name].get(year, [])),
                    "interpretation": interpretation,
                }
            )
    return result


def _decision_summary(
    metric: str,
    panel_path: Path,
    state_panel_path: Path,
    coverage_rows: list[dict[str, Any]],
    full_bucket_rows: list[dict[str, Any]],
    rolling_rows: list[dict[str, Any]],
    yearly_rows: list[dict[str, Any]],
    state_ic_rows: list[dict[str, Any]],
    selection_robustness_rows: list[dict[str, Any]],
    failure_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    rolling_by_case = {row["case"]: row for row in rolling_rows}
    low_pb = rolling_by_case["raw_low_pb_utilities_top10"]
    cashflow = rolling_by_case["raw_cashflow_yield_utilities_top10"]
    positive_years = sum(1 for row in yearly_rows if row["beats_low_pb"] == "true" or row["beats_cashflow"] == "true")
    candidate_reviews = _candidate_rule_reviews(rolling_rows, state_ic_rows, selection_robustness_rows, failure_rows)
    best_candidate = candidate_reviews[0]
    selected_rule = best_candidate["rule"]
    primary = rolling_by_case[selected_rule]
    beats_both = (primary["cum_return"] or -999) > (low_pb["cum_return"] or -999) and (primary["cum_return"] or -999) > (
        cashflow["cum_return"] or -999
    )
    robustness_pass = best_candidate["selection_robustness_status"] == "pass"
    state_ic_support = best_candidate["state_ic_status"] == "pass"
    failure_count = int(best_candidate["failure_year_count"])
    status = (
        "formal_candidate_quant_ready"
        if best_candidate["beats_static_baselines"] == "true" and robustness_pass and state_ic_support and failure_count <= 2
        else "preliminary_model_candidate"
        if beats_both and positive_years >= max(1, len(yearly_rows) // 2)
        else "needs_more_evidence"
    )
    return {
        "strategy_id": "utilities_demand_state_v51e",
        "experiment_layer": "research_pit_validation",
        "status": status,
        "not_status": ["formal_strategy_candidate", "platform_replication", "accepted_strategy"],
        "metric": metric,
        "panel": str(panel_path),
        "state_panel": str(state_panel_path),
        "coverage": {
            "panel_dates": len(coverage_rows),
            "state_covered_dates": sum(1 for row in coverage_rows if row["has_state"] == "true"),
        },
        "primary_model": {
            "name": selected_rule,
            "rule": RULE_DESCRIPTIONS[selected_rule],
            "rolling_result": primary,
            "baseline_low_pb": low_pb,
            "baseline_cashflow": cashflow,
        },
        "full_sample_state_bucket_tests": full_bucket_rows,
        "rolling_state_model_tests": rolling_rows,
        "yearly_comparison": yearly_rows,
        "state_conditioned_factor_ic": state_ic_rows,
        "selection_count_robustness": selection_robustness_rows,
        "failure_year_analysis": failure_rows,
        "candidate_rule_reviews": candidate_reviews,
        "pm_review_candidate": best_candidate if status == "formal_candidate_quant_ready" else None,
        "decision": (
            "Quant evidence is strong enough to hand to Project Manager for formal-candidate review."
            if status == "formal_candidate_quant_ready"
            else "Enough PIT research evidence to record an initial demand-state model candidate."
            if status == "preliminary_model_candidate"
            else "Do not establish a model candidate yet."
        ),
        "limitations": [
            "Thresholds are expanding historical tertiles, not optimized platform parameters.",
            "This is still research validation; no JoinQuant code or platform replication is authorized.",
            "Coal price, tariff and hydrology state variables remain sparse and are not used.",
        ],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def _state_ic_supports_rule(rows: list[dict[str, Any]]) -> bool:
    by_bucket_factor = {(row["bucket"], row["factor_case"]): row for row in rows}
    weak_cashflow = by_bucket_factor.get(("weak", "raw_cashflow_yield_utilities_top10"), {})
    mid_cashflow = by_bucket_factor.get(("mid", "raw_cashflow_yield_utilities_top10"), {})
    strong_low_pb = by_bucket_factor.get(("strong", "raw_low_pb_utilities_top10"), {})
    checks = [
        _to_float(weak_cashflow.get("mean_rankic")),
        _to_float(mid_cashflow.get("mean_rankic")),
        _to_float(strong_low_pb.get("mean_rankic")),
    ]
    return all(value is not None and value > 0 for value in checks)


def _candidate_rule_reviews(
    rolling_rows: list[dict[str, Any]],
    state_ic_rows: list[dict[str, Any]],
    selection_robustness_rows: list[dict[str, Any]],
    failure_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rolling_by_case = {row["case"]: row for row in rolling_rows}
    low_pb = rolling_by_case["raw_low_pb_utilities_top10"]
    cashflow = rolling_by_case["raw_cashflow_yield_utilities_top10"]
    result = []
    for rule_name in ROLLING_RULES:
        candidate = rolling_by_case[rule_name]
        rule_robustness = [row for row in selection_robustness_rows if row["rule"] == rule_name]
        rule_failures = [row for row in failure_rows if row["rule"] == rule_name and row["status"] == "fail"]
        rule_mixed = [row for row in failure_rows if row["rule"] == rule_name and row["status"] == "mixed"]
        ic_pass = _state_ic_supports_named_rule(rule_name, state_ic_rows)
        robustness_pass = all(row["status"] == "pass" for row in rule_robustness)
        result.append(
            {
                "rule": rule_name,
                "cum_return": candidate["cum_return"],
                "positive_ratio": candidate["positive_ratio"],
                "beats_static_baselines": str(
                    (candidate["cum_return"] or -999) > (low_pb["cum_return"] or -999)
                    and (candidate["cum_return"] or -999) > (cashflow["cum_return"] or -999)
                ).lower(),
                "selection_robustness_status": "pass" if robustness_pass else "needs_review",
                "state_ic_status": "pass" if ic_pass else "needs_review",
                "failure_year_count": len(rule_failures),
                "mixed_year_count": len(rule_mixed),
                "review_status": "quant_ready"
                if robustness_pass
                and ic_pass
                and len(rule_failures) <= 2
                and (candidate["cum_return"] or -999) > (low_pb["cum_return"] or -999)
                and (candidate["cum_return"] or -999) > (cashflow["cum_return"] or -999)
                else "needs_more_research",
            }
        )
    return sorted(
        result,
        key=lambda row: (
            row["review_status"] == "quant_ready",
            -int(row["failure_year_count"]),
            row["cum_return"] or -999,
        ),
        reverse=True,
    )


def _state_ic_supports_named_rule(rule_name: str, rows: list[dict[str, Any]]) -> bool:
    required = {
        "demand_state_cashflow_else_low_pb": [
            ("weak", "raw_cashflow_yield_utilities_top10"),
            ("mid", "raw_cashflow_yield_utilities_top10"),
            ("strong", "raw_low_pb_utilities_top10"),
        ],
        "demand_state_cashflow_subcashflow_low_pb": [
            ("weak", "raw_cashflow_yield_utilities_top10"),
            ("mid", "subindustry_cashflow_top10"),
            ("strong", "raw_low_pb_utilities_top10"),
        ],
        "demand_state_dividend_cashflow_low_pb": [
            ("weak", "raw_high_dividend_utilities_top10"),
            ("mid", "raw_cashflow_yield_utilities_top10"),
            ("strong", "raw_low_pb_utilities_top10"),
        ],
    }[rule_name]
    by_bucket_factor = {(row["bucket"], row["factor_case"]): row for row in rows}
    checks = [_to_float(by_bucket_factor.get(key, {}).get("mean_rankic")) for key in required]
    return all(value is not None and value > 0 for value in checks)


def _case_return(date_rows: list[dict[str, str]], case_name: str, selection_count: int) -> float | None:
    if case_name == "equal_weight_utilities":
        values = [_to_float(row.get("future_return")) for row in date_rows]
        usable = [value for value in values if value is not None]
        return mean(usable) if usable else None
    factor, direction = FACTOR_CASES[case_name]
    usable_rows = [row for row in date_rows if _to_float(row.get(factor)) is not None and _to_float(row.get("future_return")) is not None]
    selected = sorted(
        usable_rows,
        key=lambda row: _to_float(row.get(factor)) or 0.0,
        reverse=direction == "higher_is_better",
    )[:selection_count]
    return mean(_to_float(row["future_return"]) or 0.0 for row in selected) if selected else None


def _latest_visible_state_by_date(
    by_date: dict[str, list[dict[str, str]]],
    states: list[dict[str, str]],
    metric: str,
) -> dict[str, dict[str, Any]]:
    series = []
    for row in states:
        value = _to_float(row.get("value"))
        if row.get("metric") == metric and value is not None and row.get("visible_date"):
            series.append({"visible_date": row["visible_date"], "state_date": row.get("state_date", ""), "value": value})
    series = sorted(series, key=lambda row: row["visible_date"])
    result = {}
    for trade_date in sorted(by_date):
        visible = [row for row in series if row["visible_date"] <= trade_date]
        if visible:
            result[trade_date] = visible[-1]
    return result


def _expanding_bucket(history: list[float], value: float, min_history: int) -> str:
    if len(history) < min_history:
        return "warmup"
    q33, q67 = _tertiles(sorted(history))
    if value <= q33:
        return "weak"
    if value >= q67:
        return "strong"
    return "mid"


def _tertiles(values: list[float]) -> tuple[float, float]:
    if not values:
        raise ValueError("cannot compute tertiles for empty values")
    return values[len(values) // 3], values[(2 * len(values)) // 3]


def _group_by_date(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("trade_date") and _to_float(row.get("future_return")) is not None:
            result[row["trade_date"]].append(row)
    return dict(result)


def _compound(returns: list[float]) -> float | None:
    if not returns:
        return None
    value = 1.0
    for ret in returns:
        value *= 1.0 + ret
    return value - 1.0


def _positive_ratio(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(1 for value in values if value > 0) / len(values)


def _pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) != len(y) or len(x) < 2:
        return None
    mx = mean(x)
    my = mean(y)
    numerator = sum((left - mx) * (right - my) for left, right in zip(x, y))
    denom_x = math.sqrt(sum((left - mx) ** 2 for left in x))
    denom_y = math.sqrt(sum((right - my) ** 2 for right in y))
    if denom_x == 0 or denom_y == 0:
        return None
    return numerator / (denom_x * denom_y)


def _ranks(values: list[float]) -> list[float]:
    ordered = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    index = 0
    while index < len(ordered):
        end = index
        while end + 1 < len(ordered) and ordered[end + 1][0] == ordered[index][0]:
            end += 1
        avg_rank = (index + end + 2) / 2.0
        for pos in range(index, end + 1):
            ranks[ordered[pos][1]] = avg_rank
        index = end + 1
    return ranks


def _top_bottom_spread(pairs: list[tuple[float, float]]) -> float | None:
    if len({value for value, _ret in pairs}) < 2:
        return None
    ordered = sorted(pairs, key=lambda item: item[0])
    group_size = max(1, len(ordered) // 3)
    bottom = ordered[:group_size]
    top = ordered[-group_size:]
    return mean(ret for _value, ret in top) - mean(ret for _value, ret in bottom)


def _to_float(value: Any) -> float | None:
    if value in {None, "", "nan", "NaN", "None"}:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric != numeric or numeric in {float("inf"), float("-inf")}:
        return None
    return numeric


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fieldnames: Iterable[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    primary = summary["primary_model"]
    lines = [
        "# Utilities Demand State Validation V5.1e",
        "",
        f"- Status: `{summary['status']}`",
        f"- Experiment layer: `{summary['experiment_layer']}`",
        f"- Metric: `{summary['metric']}`",
        "",
        "## Primary Model",
        "",
        primary["rule"],
        "",
        "## Rolling Evidence",
        "",
        f"- Demand-state model cumulative return: `{primary['rolling_result']['cum_return']}`",
        f"- Low-PB baseline cumulative return: `{primary['baseline_low_pb']['cum_return']}`",
        f"- Cash-flow baseline cumulative return: `{primary['baseline_cashflow']['cum_return']}`",
        f"- Demand-state positive period ratio: `{primary['rolling_result']['positive_ratio']}`",
        "",
        "## Decision",
        "",
        summary["decision"],
        "",
        "## Governance",
        "",
        "This is not a formal strategy candidate, platform replication result, or accepted strategy.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-utilities-demand-state-validation")
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--state-panel", type=Path, default=DEFAULT_STATE_PANEL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--metric", default="electricity_consumption_yoy")
    parser.add_argument("--selection-count", type=int, default=10)
    parser.add_argument("--min-history", type=int, default=8)
    args = parser.parse_args(argv)
    print(run_utilities_demand_state_validation(args.panel, args.state_panel, args.out, args.metric, args.selection_count, args.min_history))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

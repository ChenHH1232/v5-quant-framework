from __future__ import annotations

import argparse
import csv
import json
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

    _write_csv(out / "state_coverage.csv", coverage_rows[0].keys(), coverage_rows)
    _write_csv(out / "full_sample_state_bucket_tests.csv", full_bucket_rows[0].keys(), full_bucket_rows)
    _write_csv(out / "rolling_state_model_tests.csv", rolling_rows[0].keys(), rolling_rows)
    _write_csv(out / "rolling_state_date_choices.csv", rolling_date_rows[0].keys(), rolling_date_rows)
    _write_csv(out / "yearly_comparison.csv", yearly_rows[0].keys(), yearly_rows)

    summary = _decision_summary(metric, panel_path, state_panel_path, coverage_rows, full_bucket_rows, rolling_rows, yearly_rows)
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


def _decision_summary(
    metric: str,
    panel_path: Path,
    state_panel_path: Path,
    coverage_rows: list[dict[str, Any]],
    full_bucket_rows: list[dict[str, Any]],
    rolling_rows: list[dict[str, Any]],
    yearly_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    rolling_by_case = {row["case"]: row for row in rolling_rows}
    primary = rolling_by_case["demand_state_cashflow_else_low_pb"]
    low_pb = rolling_by_case["raw_low_pb_utilities_top10"]
    cashflow = rolling_by_case["raw_cashflow_yield_utilities_top10"]
    beats_both = (primary["cum_return"] or -999) > (low_pb["cum_return"] or -999) and (primary["cum_return"] or -999) > (
        cashflow["cum_return"] or -999
    )
    positive_years = sum(1 for row in yearly_rows if row["beats_low_pb"] == "true" or row["beats_cashflow"] == "true")
    status = "preliminary_model_candidate" if beats_both and positive_years >= max(1, len(yearly_rows) // 2) else "needs_more_evidence"
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
            "name": "demand_state_cashflow_else_low_pb",
            "rule": "Use operating cash-flow yield unless the expanding electricity-demand YoY state is strong; use low PB in strong-demand states. Warmup periods use cash-flow yield.",
            "rolling_result": primary,
            "baseline_low_pb": low_pb,
            "baseline_cashflow": cashflow,
        },
        "full_sample_state_bucket_tests": full_bucket_rows,
        "rolling_state_model_tests": rolling_rows,
        "yearly_comparison": yearly_rows,
        "decision": (
            "Enough PIT research evidence to record an initial demand-state model candidate."
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

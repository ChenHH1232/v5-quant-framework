from __future__ import annotations

import argparse
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.paths import DEFAULT_PROCESSED_DIR


DEFAULT_PANEL = DEFAULT_PROCESSED_DIR / "oil_gas_low_vol_panel_v58a" / "oil_gas_ocf_dividend_cycle_probe_v58a" / "panel_with_low_vol.csv"
DEFAULT_OUT_DIR = Path("validation_state_v58c_oil_gas")

FACTOR_CASES = {
    "equal_weight_oil_gas_pool": ("", "higher_is_better"),
    "high_ocf_yield_top8": ("operating_cash_flow_yield", "higher_is_better"),
    "low_vol_top8": ("low_vol_score", "higher_is_better"),
    "low_pb_top8": ("low_price_to_book", "lower_is_better"),
    "low_pe_top8": ("pe_ratio", "lower_is_better"),
    "high_dividend_top8": ("dividend_yield", "higher_is_better"),
    "high_fcf_yield_top8": ("free_cash_flow_yield", "higher_is_better"),
}


@dataclass(frozen=True)
class OilGasCycleStateValidationResult:
    report_path: Path
    summary_path: Path
    metric: str
    status: str
    state_covered_dates: int
    panel_dates: int


def run_oil_gas_cycle_state_validation(
    panel_path: Path = DEFAULT_PANEL,
    out_dir: Path = DEFAULT_OUT_DIR,
    metric: str = "crude_oil_price_state",
    selection_count: int = 8,
    min_history: int = 4,
    strategy_id: str = "oil_gas_ocf_state_diagnostic_v58c",
) -> OilGasCycleStateValidationResult:
    rows = read_csv_rows(panel_path)
    by_date = _group_by_date(rows)
    state_by_date = _state_by_date(by_date, metric)
    if not state_by_date:
        raise RuntimeError(f"no usable state values found for metric={metric}")

    out = out_dir / strategy_id / f"cycle_state_{metric}"
    out.mkdir(parents=True, exist_ok=True)
    coverage_rows = _coverage_rows(by_date, state_by_date, metric)
    bucket_rows = _rolling_bucket_by_date(state_by_date, min_history)
    state_bucket_tests = _state_bucket_tests(by_date, bucket_rows, selection_count)
    state_conditioned_ic = _state_conditioned_factor_ic(by_date, bucket_rows)
    year_rows = _yearly_state_summary(by_date, bucket_rows, selection_count)
    robustness_rows = _selection_count_robustness(by_date, bucket_rows, [6, 8, 10])
    summary = _decision_summary(
        panel_path=panel_path,
        metric=metric,
        coverage_rows=coverage_rows,
        state_bucket_tests=state_bucket_tests,
        state_conditioned_ic=state_conditioned_ic,
        year_rows=year_rows,
        robustness_rows=robustness_rows,
        strategy_id=strategy_id,
    )

    write_csv_rows(out / "state_coverage.csv", coverage_rows[0].keys(), coverage_rows)
    write_csv_rows(out / "rolling_state_buckets.csv", bucket_rows[0].keys(), bucket_rows)
    write_csv_rows(out / "state_bucket_tests.csv", state_bucket_tests[0].keys(), state_bucket_tests)
    write_csv_rows(out / "state_conditioned_factor_ic.csv", state_conditioned_ic[0].keys(), state_conditioned_ic)
    write_csv_rows(out / "yearly_state_summary.csv", year_rows[0].keys(), year_rows)
    write_csv_rows(out / "selection_count_robustness.csv", robustness_rows[0].keys(), robustness_rows)
    summary_path = out / "cycle_state_validation_summary.json"
    report_path = out / "cycle_state_validation_report.md"
    write_json_file(summary_path, summary)
    _write_report(report_path, summary)
    return OilGasCycleStateValidationResult(
        report_path=report_path,
        summary_path=summary_path,
        metric=metric,
        status=str(summary["status"]),
        state_covered_dates=int(summary["coverage"]["state_covered_dates"]),
        panel_dates=int(summary["coverage"]["panel_dates"]),
    )


def _coverage_rows(by_date: dict[str, list[dict[str, str]]], state_by_date: dict[str, float], metric: str) -> list[dict[str, Any]]:
    return [
        {
            "trade_date": trade_date,
            "panel_rows": len(by_date[trade_date]),
            "metric": metric,
            "has_state": str(trade_date in state_by_date).lower(),
            "state_value": state_by_date.get(trade_date),
        }
        for trade_date in sorted(by_date)
    ]


def _rolling_bucket_by_date(state_by_date: dict[str, float], min_history: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    history: list[float] = []
    for trade_date, value in sorted(state_by_date.items()):
        bucket = _expanding_bucket(history, value, min_history)
        rows.append(
            {
                "trade_date": trade_date,
                "state_value": value,
                "expanding_bucket": bucket,
                "history_count": len(history),
            }
        )
        history.append(value)
    return rows


def _state_bucket_tests(
    by_date: dict[str, list[dict[str, str]]],
    bucket_rows: list[dict[str, Any]],
    selection_count: int,
) -> list[dict[str, Any]]:
    bucket_by_date = {row["trade_date"]: row["expanding_bucket"] for row in bucket_rows}
    result: list[dict[str, Any]] = []
    for bucket in ["warmup", "weak", "mid", "strong", "all"]:
        dates = [trade_date for trade_date in sorted(by_date) if bucket == "all" or bucket_by_date.get(trade_date) == bucket]
        for case_name in FACTOR_CASES:
            returns = [_case_return(by_date[trade_date], case_name, selection_count) for trade_date in dates]
            usable = [value for value in returns if value is not None]
            result.append(
                {
                    "bucket": bucket,
                    "case": case_name,
                    "periods": len(usable),
                    "cum_return": _compound(usable),
                    "mean_return": mean(usable) if usable else None,
                    "positive_ratio": _positive_ratio(usable),
                }
            )
    return result


def _state_conditioned_factor_ic(by_date: dict[str, list[dict[str, str]]], bucket_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bucket_by_date = {row["trade_date"]: row["expanding_bucket"] for row in bucket_rows}
    result: list[dict[str, Any]] = []
    for bucket in ["warmup", "weak", "mid", "strong", "all"]:
        dates = [trade_date for trade_date in sorted(by_date) if bucket == "all" or bucket_by_date.get(trade_date) == bucket]
        for case_name, (factor, direction) in FACTOR_CASES.items():
            if not factor:
                continue
            ic_values: list[float] = []
            rank_ic_values: list[float] = []
            spreads: list[float] = []
            observations = 0
            for trade_date in dates:
                pairs: list[tuple[float, float]] = []
                for row in by_date[trade_date]:
                    factor_value = _to_float(row.get(factor))
                    ret = _to_float(row.get("future_return") or row.get("total_return"))
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


def _yearly_state_summary(
    by_date: dict[str, list[dict[str, str]]],
    bucket_rows: list[dict[str, Any]],
    selection_count: int,
) -> list[dict[str, Any]]:
    bucket_by_date = {row["trade_date"]: row["expanding_bucket"] for row in bucket_rows}
    by_year: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    bucket_notes: dict[str, list[str]] = defaultdict(list)
    for trade_date, date_rows in by_date.items():
        year = trade_date[:4]
        bucket_notes[year].append(bucket_by_date.get(trade_date, "missing"))
        for case_name in FACTOR_CASES:
            ret = _case_return(date_rows, case_name, selection_count)
            if ret is not None:
                by_year[year][case_name].append(ret)
    result = []
    for year, values in sorted(by_year.items()):
        result.append(
            {
                "year": year,
                "buckets": ";".join(bucket_notes[year]),
                "equal_weight_cum_return": _compound(values.get("equal_weight_oil_gas_pool", [])),
                "high_ocf_cum_return": _compound(values.get("high_ocf_yield_top8", [])),
                "low_vol_cum_return": _compound(values.get("low_vol_top8", [])),
                "low_pb_cum_return": _compound(values.get("low_pb_top8", [])),
                "low_pe_cum_return": _compound(values.get("low_pe_top8", [])),
                "high_dividend_cum_return": _compound(values.get("high_dividend_top8", [])),
                "high_fcf_cum_return": _compound(values.get("high_fcf_yield_top8", [])),
            }
        )
    return result


def _selection_count_robustness(
    by_date: dict[str, list[dict[str, str]]],
    bucket_rows: list[dict[str, Any]],
    selection_counts: list[int],
) -> list[dict[str, Any]]:
    bucket_by_date = {row["trade_date"]: row["expanding_bucket"] for row in bucket_rows}
    result: list[dict[str, Any]] = []
    for count in selection_counts:
        for bucket in ["weak", "mid", "strong", "all"]:
            dates = [trade_date for trade_date in sorted(by_date) if bucket == "all" or bucket_by_date.get(trade_date) == bucket]
            for case_name in ["high_ocf_yield_top8", "low_vol_top8", "low_pb_top8", "low_pe_top8"]:
                returns = [_case_return(by_date[trade_date], case_name, count) for trade_date in dates]
                usable = [value for value in returns if value is not None]
                result.append(
                    {
                        "selection_count": count,
                        "bucket": bucket,
                        "case": case_name,
                        "periods": len(usable),
                        "cum_return": _compound(usable),
                        "positive_ratio": _positive_ratio(usable),
                    }
                )
    return result


def _decision_summary(
    *,
    panel_path: Path,
    metric: str,
    coverage_rows: list[dict[str, Any]],
    state_bucket_tests: list[dict[str, Any]],
    state_conditioned_ic: list[dict[str, Any]],
    year_rows: list[dict[str, Any]],
    robustness_rows: list[dict[str, Any]],
    strategy_id: str,
) -> dict[str, Any]:
    all_cases = [row for row in state_bucket_tests if row["bucket"] == "all"]
    weak_cases = [row for row in state_bucket_tests if row["bucket"] == "weak"]
    mid_cases = [row for row in state_bucket_tests if row["bucket"] == "mid"]
    strong_cases = [row for row in state_bucket_tests if row["bucket"] == "strong"]
    ocf_all = _find_case(all_cases, "high_ocf_yield_top8")
    low_vol_all = _find_case(all_cases, "low_vol_top8")
    equal_all = _find_case(all_cases, "equal_weight_oil_gas_pool")
    return {
        "strategy_id": strategy_id,
        "experiment_layer": "research_pit_validation",
        "status": "cycle_state_diagnostic_completed_not_acceptance",
        "not_status": ["formal_strategy_candidate", "platform_replication", "accepted_strategy"],
        "panel": str(panel_path),
        "metric": metric,
        "coverage": {
            "panel_dates": len(coverage_rows),
            "state_covered_dates": sum(1 for row in coverage_rows if row["has_state"] == "true"),
        },
        "best_all_bucket_case": _best_case(all_cases),
        "best_weak_bucket_case": _best_case(weak_cases),
        "best_mid_bucket_case": _best_case(mid_cases),
        "best_strong_bucket_case": _best_case(strong_cases),
        "ocf_all_bucket_case": ocf_all,
        "low_vol_all_bucket_case": low_vol_all,
        "equal_weight_all_bucket_case": equal_all,
        "state_bucket_tests": state_bucket_tests,
        "state_conditioned_factor_ic": state_conditioned_ic,
        "yearly_state_summary": year_rows,
        "selection_count_robustness": robustness_rows,
        "pm_read": _pm_read(ocf_all, low_vol_all, equal_all),
        "limitations": [
            "Buckets use expanding historical tertiles, not optimized thresholds.",
            "External state metrics are futures proxies in V5.8a/V5.8c and are not official spot/spread/tariff evidence.",
            "The metric is same for all stocks on a rebalance date, so stock-level IC is interpreted within state buckets.",
            "This diagnostic can support Research/Quant iteration but cannot approve Engineering handoff.",
        ],
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def _pm_read(ocf: dict[str, Any] | None, low_vol: dict[str, Any] | None, equal: dict[str, Any] | None) -> str:
    if not ocf:
        return "OCF case unavailable; remain blocked."
    if equal and _float_or_none(ocf.get("cum_return")) is not None and _float_or_none(equal.get("cum_return")) is not None:
        if (_float_or_none(ocf["cum_return"]) or 0.0) > (_float_or_none(equal["cum_return"]) or 0.0):
            return "OCF signal remains stronger than equal-weight in this diagnostic, but source and failure-mode blockers remain."
    if low_vol and (_float_or_none(low_vol.get("cum_return")) or -999.0) > (_float_or_none(ocf.get("cum_return")) or -999.0):
        return "Low-vol dominates OCF in this diagnostic; return to Research before promoting OCF."
    return "OCF diagnostic completed; do not promote without state-source repair and failure-year explanation."


def _state_by_date(by_date: dict[str, list[dict[str, str]]], metric: str) -> dict[str, float]:
    result = {}
    for trade_date, date_rows in sorted(by_date.items()):
        values = [_to_float(row.get(metric)) for row in date_rows]
        usable = [value for value in values if value is not None]
        if usable:
            result[trade_date] = usable[0]
    return result


def _group_by_date(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("trade_date") and _to_float(row.get("future_return") or row.get("total_return")) is not None:
            result[row["trade_date"]].append(row)
    return dict(result)


def _case_return(date_rows: list[dict[str, str]], case_name: str, selection_count: int) -> float | None:
    if case_name == "equal_weight_oil_gas_pool":
        values = [_to_float(row.get("future_return") or row.get("total_return")) for row in date_rows]
        usable = [value for value in values if value is not None]
        return mean(usable) if usable else None
    factor, direction = FACTOR_CASES[case_name]
    usable_rows = [
        row
        for row in date_rows
        if _to_float(row.get(factor)) is not None and _to_float(row.get("future_return") or row.get("total_return")) is not None
    ]
    selected = sorted(
        usable_rows,
        key=lambda row: _to_float(row.get(factor)) or 0.0,
        reverse=direction == "higher_is_better",
    )[:selection_count]
    return mean(_to_float(row.get("future_return") or row.get("total_return")) or 0.0 for row in selected) if selected else None


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


def _best_case(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    usable = [row for row in rows if _float_or_none(row.get("cum_return")) is not None]
    if not usable:
        return None
    return max(usable, key=lambda row: float(row["cum_return"]))


def _find_case(rows: list[dict[str, Any]], case_name: str) -> dict[str, Any] | None:
    for row in rows:
        if row.get("case") == case_name:
            return row
    return None


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
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return numeric


def _float_or_none(value: Any) -> float | None:
    return _to_float(value)


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Oil / Gas Cycle-State Diagnostic V5.8c",
        "",
        f"- Status: `{summary['status']}`",
        f"- Experiment layer: `{summary['experiment_layer']}`",
        f"- Metric: `{summary['metric']}`",
        f"- State coverage: `{summary['coverage']['state_covered_dates']}/{summary['coverage']['panel_dates']}`",
        f"- PM read: {summary['pm_read']}",
        "",
        "## Best Cases",
        "",
        f"- All states: `{summary['best_all_bucket_case']}`",
        f"- Weak state: `{summary['best_weak_bucket_case']}`",
        f"- Mid state: `{summary['best_mid_bucket_case']}`",
        f"- Strong state: `{summary['best_strong_bucket_case']}`",
        "",
        "## OCF / Low-Vol / Equal Weight",
        "",
        f"- OCF all bucket: `{summary['ocf_all_bucket_case']}`",
        f"- Low-vol all bucket: `{summary['low_vol_all_bucket_case']}`",
        f"- Equal-weight all bucket: `{summary['equal_weight_all_bucket_case']}`",
        "",
        "## Limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in summary["limitations"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-oil-gas-cycle-state-validation")
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--metric", default="crude_oil_price_state")
    parser.add_argument("--selection-count", type=int, default=8)
    parser.add_argument("--min-history", type=int, default=4)
    parser.add_argument("--strategy-id", default="oil_gas_ocf_state_diagnostic_v58c")
    args = parser.parse_args(argv)
    print(run_oil_gas_cycle_state_validation(args.panel, args.out, args.metric, args.selection_count, args.min_history, args.strategy_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

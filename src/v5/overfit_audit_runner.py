from __future__ import annotations

import argparse
import csv
import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any


DEFAULT_OUT_DIR = Path("validation_overfit")


@dataclass(frozen=True)
class OverfitAuditResult:
    report_path: Path
    summary_path: Path
    checks_path: Path
    status: str
    blocker_count: int
    needs_review_count: int


def run_overfit_audit(
    spec_path: Path,
    out_dir: Path = DEFAULT_OUT_DIR,
    panel_path: Path | None = None,
    daily_returns_csv: Path | None = None,
    rebalance_signals_csv: Path | None = None,
    strategy_id: str | None = None,
    random_seed: int = 20260716,
    random_windows: int = 100,
    min_window_days: int = 252,
) -> OverfitAuditResult:
    spec = _read_json(spec_path)
    sid = strategy_id or spec.get("meta", {}).get("strategy_id") or spec_path.stem
    out = out_dir / sid
    out.mkdir(parents=True, exist_ok=True)

    panel_rows = _read_csv(panel_path) if panel_path else []
    daily_rows = _read_csv(daily_returns_csv) if daily_returns_csv else []
    signal_rows = _read_csv(rebalance_signals_csv) if rebalance_signals_csv else []

    checks: list[dict[str, Any]] = []
    checks.extend(_survivorship_bias_checks(spec, panel_rows, panel_path))
    checks.extend(_future_leakage_checks(spec, panel_rows, signal_rows, panel_path, rebalance_signals_csv))
    checks.extend(_sample_contamination_checks(spec, daily_rows, daily_returns_csv))
    checks.extend(_stability_checks(daily_rows, daily_returns_csv, random_seed, random_windows, min_window_days))
    checks.extend(_parameter_perturbation_checks(spec, signal_rows, rebalance_signals_csv))

    blocker_count = sum(1 for row in checks if row["severity"] == "blocker")
    needs_review_count = sum(1 for row in checks if row["severity"] == "needs_review")
    status = "blocked" if blocker_count else ("needs_review" if needs_review_count else "pass")

    summary = {
        "strategy_id": sid,
        "status": status,
        "spec": str(spec_path),
        "panel": str(panel_path) if panel_path else None,
        "daily_returns_csv": str(daily_returns_csv) if daily_returns_csv else None,
        "rebalance_signals_csv": str(rebalance_signals_csv) if rebalance_signals_csv else None,
        "check_count": len(checks),
        "blocker_count": blocker_count,
        "needs_review_count": needs_review_count,
        "pass_count": sum(1 for row in checks if row["severity"] == "pass"),
        "random_seed": random_seed,
        "random_windows": random_windows,
        "min_window_days": min_window_days,
        "governance": (
            "This is an Engineering Agent anti-overfitting audit. It does not accept a strategy. "
            "It blocks or flags risks before PM can promote a candidate."
        ),
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }

    checks_path = out / "overfit_audit_checks.csv"
    summary_path = out / "overfit_audit_summary.json"
    report_path = out / "overfit_audit_report.md"
    _write_csv(checks_path, _check_fields(), checks)
    _write_json(summary_path, summary)
    _write_report(report_path, summary, checks)
    return OverfitAuditResult(report_path, summary_path, checks_path, status, blocker_count, needs_review_count)


def _survivorship_bias_checks(spec: dict[str, Any], rows: list[dict[str, str]], panel_path: Path | None) -> list[dict[str, Any]]:
    result = []
    universe = spec.get("universe", {})
    result.append(
        _check(
            "survivorship_bias",
            "spec_universe_point_in_time",
            "pass" if universe.get("point_in_time") is True else "blocker",
            "Universe must be point-in-time rather than today's surviving constituents.",
            {"point_in_time": universe.get("point_in_time")},
        )
    )
    if not panel_path:
        result.append(_missing("survivorship_bias", "panel_universe_visibility", "panel_path missing"))
        return result
    if not rows:
        result.append(_check("survivorship_bias", "panel_universe_visibility", "blocker", "Panel is empty.", {}))
        return result

    universe_visible_fields = ["universe_visible_date", "listing_visible_date", "membership_visible_date"]
    rows_with_visible = [row for row in rows if any(row.get(field) for field in universe_visible_fields)]
    violations = _visible_date_violations(rows, universe_visible_fields)
    missing_ratio = 1.0 - (len(rows_with_visible) / len(rows)) if rows else 1.0
    severity = "pass"
    if violations:
        severity = "blocker"
    elif missing_ratio > 0.5:
        severity = "needs_review"
    result.append(
        _check(
            "survivorship_bias",
            "panel_universe_visibility",
            severity,
            "Panel should expose universe/listing/membership visible dates and they must be <= trade_date.",
            {
                "rows": len(rows),
                "rows_with_universe_visible_date": len(rows_with_visible),
                "missing_ratio": _round(missing_ratio),
                "future_visible_date_violations": len(violations),
                "examples": ";".join(violations[:5]),
            },
        )
    )

    by_date: dict[str, set[str]] = {}
    all_codes = set()
    for row in rows:
        if row.get("trade_date") and row.get("code"):
            by_date.setdefault(row["trade_date"], set()).add(row["code"])
            all_codes.add(row["code"])
    first_date = min(by_date) if by_date else ""
    first_count = len(by_date.get(first_date, set())) if first_date else 0
    all_count = len(all_codes)
    first_ratio = first_count / all_count if all_count else 0.0
    result.append(
        _check(
            "survivorship_bias",
            "first_date_constituent_smell_test",
            "needs_review" if all_count and first_ratio > 0.95 and len(by_date) > 4 else "pass",
            "If the first date already contains nearly all eventual securities, review for today's-universe backfill.",
            {
                "first_date": first_date,
                "first_date_count": first_count,
                "all_code_count": all_count,
                "first_date_ratio": _round(first_ratio),
                "date_count": len(by_date),
            },
        )
    )
    return result


def _future_leakage_checks(
    spec: dict[str, Any],
    panel_rows: list[dict[str, str]],
    signal_rows: list[dict[str, str]],
    panel_path: Path | None,
    signals_path: Path | None,
) -> list[dict[str, Any]]:
    result = []
    scope = spec.get("signals", {}).get("scoring", {}).get("normalization_scope")
    result.append(
        _check(
            "future_leakage",
            "normalization_scope",
            "blocker" if scope == "full_sample" else "pass",
            "Full-sample normalization is a future function.",
            {"normalization_scope": scope},
        )
    )
    safe_factor_as_of = {
        "announcement_date",
        "report_publish_date",
        "trade_date_lagged",
        "trade_date_market_cap_and_latest_visible_ev",
    }
    unsafe_factors = []
    for factor in spec.get("signals", {}).get("factors", []):
        if factor.get("as_of") not in safe_factor_as_of:
            unsafe_factors.append(str(factor.get("name")))
    result.append(
        _check(
            "future_leakage",
            "factor_as_of_policy",
            "blocker" if unsafe_factors else "pass",
            "Factor as_of policy must be announcement_date, report_publish_date, or trade_date_lagged.",
            {"unsafe_factors": ";".join(unsafe_factors)},
        )
    )

    if panel_path:
        fields = _visible_fields(panel_rows)
        violations = _visible_date_violations(panel_rows, fields)
        result.append(
            _check(
                "future_leakage",
                "panel_visible_dates",
                "blocker" if violations else "pass",
                "All panel visible/notice/announce dates must be <= trade_date.",
                {"visible_fields": ";".join(fields), "violations": len(violations), "examples": ";".join(violations[:5])},
            )
        )
    else:
        result.append(_missing("future_leakage", "panel_visible_dates", "panel_path missing"))

    if signals_path:
        fields = _visible_fields(signal_rows)
        violations = _visible_date_violations(signal_rows, fields)
        result.append(
            _check(
                "future_leakage",
                "rebalance_signal_visible_dates",
                "blocker" if violations else "pass",
                "State/timing rows in rebalance_signals must be visible no later than trade_date.",
                {"visible_fields": ";".join(fields), "violations": len(violations), "examples": ";".join(violations[:5])},
            )
        )
    else:
        result.append(_missing("future_leakage", "rebalance_signal_visible_dates", "rebalance_signals_csv missing"))
    return result


def _sample_contamination_checks(spec: dict[str, Any], daily_rows: list[dict[str, str]], daily_path: Path | None) -> list[dict[str, Any]]:
    result = []
    validation = spec.get("validation", {})
    result.append(
        _check(
            "sample_contamination",
            "rolling_validation_required",
            "pass" if validation.get("method") == "rolling" else "needs_review",
            "Single-model validation should be rolling; platform-confirmation windows are not clean out-of-sample acceptance.",
            {"validation_method": validation.get("method")},
        )
    )
    status_text = json.dumps(spec.get("meta", {}), ensure_ascii=False).lower()
    accepted_marker = "accepted_strategy" in status_text
    result.append(
        _check(
            "sample_contamination",
            "accepted_status_guard",
            "blocker" if accepted_marker else "pass",
            "A strategy cannot be marked accepted based only on backtest/platform-confirmation evidence.",
            {"meta_status": spec.get("meta", {}).get("status")},
        )
    )
    if not daily_path:
        result.append(_missing("sample_contamination", "platform_window_usage", "daily_returns_csv missing"))
        return result
    dates = [row.get("trade_date", "")[:10] for row in daily_rows if row.get("trade_date")]
    if not dates:
        result.append(_check("sample_contamination", "platform_window_usage", "needs_review", "Daily return file has no dates.", {}))
        return result
    start, end = min(dates), max(dates)
    overlaps_confirmation = start <= "2026-05-31" and end >= "2021-05-01"
    layer = _most_common([row.get("experiment_layer", "") for row in daily_rows if row.get("experiment_layer")])
    result.append(
        _check(
            "sample_contamination",
            "platform_window_usage",
            "needs_review" if overlaps_confirmation else "pass",
            "The 2021-05 to 2026-05 window is platform confirmation / replication context, not clean OOS model acceptance.",
            {"daily_start": start, "daily_end": end, "overlaps_2021_2026_confirmation_window": overlaps_confirmation, "experiment_layer": layer},
        )
    )
    return result


def _stability_checks(
    daily_rows: list[dict[str, str]],
    daily_path: Path | None,
    random_seed: int,
    random_windows: int,
    min_window_days: int,
) -> list[dict[str, Any]]:
    if not daily_path:
        return [_missing("stability", "daily_return_random_windows", "daily_returns_csv missing")]
    series = [(row.get("trade_date", ""), _to_float(row.get("strategy_return")), _to_float(row.get("benchmark_return"))) for row in daily_rows]
    series = [(day, ret, bm) for day, ret, bm in series if day and ret is not None and bm is not None]
    if len(series) < min_window_days:
        return [
            _check(
                "stability",
                "daily_return_random_windows",
                "needs_review",
                "Not enough daily observations for random-window stability.",
                {"daily_count": len(series), "min_window_days": min_window_days},
            )
        ]

    rng = random.Random(random_seed)
    windows = []
    for _ in range(random_windows):
        max_len = len(series)
        length = rng.randint(min_window_days, max(min_window_days, max_len))
        start = rng.randint(0, max_len - length)
        subset = series[start : start + length]
        strategy_returns = [item[1] or 0.0 for item in subset]
        benchmark_returns = [item[2] or 0.0 for item in subset]
        windows.append(
            {
                "start": subset[0][0],
                "end": subset[-1][0],
                "days": len(subset),
                "strategy_return": _compound(strategy_returns),
                "excess_return": _compound(strategy_returns) - _compound(benchmark_returns),
            }
        )
    strategy_values = [row["strategy_return"] for row in windows]
    excess_values = [row["excess_return"] for row in windows]
    p10 = _percentile(strategy_values, 0.10)
    excess_p10 = _percentile(excess_values, 0.10)
    positive_ratio = sum(1 for value in strategy_values if value > 0) / len(strategy_values)
    severity = "pass" if positive_ratio >= 0.70 and (p10 or 0.0) > -0.10 else "needs_review"
    return [
        _check(
            "stability",
            "daily_return_random_windows",
            severity,
            "Randomly change backtest sub-windows and verify the result is not dependent on one lucky date range.",
            {
                "random_windows": random_windows,
                "min_window_days": min_window_days,
                "positive_window_ratio": _round(positive_ratio),
                "median_strategy_return": _round(median(strategy_values)),
                "p10_strategy_return": _round(p10),
                "median_excess_return": _round(median(excess_values)),
                "p10_excess_return": _round(excess_p10),
                "worst_window": _window_label(min(windows, key=lambda row: row["strategy_return"])),
                "best_window": _window_label(max(windows, key=lambda row: row["strategy_return"])),
            },
        ),
        _execution_timing_proxy(series),
    ]


def _execution_timing_proxy(series: list[tuple[str, float | None, float | None]]) -> dict[str, Any]:
    strategy = [item[1] or 0.0 for item in series]
    shifted_forward = [0.0] + strategy[:-1]
    shifted_backward = strategy[1:] + [0.0]
    base = _compound(strategy)
    forward = _compound(shifted_forward)
    backward = _compound(shifted_backward)
    max_abs_diff = max(abs(forward - base), abs(backward - base))
    return _check(
        "stability",
        "execution_time_shift_proxy",
        "needs_review" if max_abs_diff > 0.25 else "pass",
        "Proxy for changing buy/sell timing by shifting daily returns one day. Large sensitivity requires intraday/timing attribution.",
        {
            "base_return": _round(base),
            "shift_forward_return": _round(forward),
            "shift_backward_return": _round(backward),
            "max_abs_diff": _round(max_abs_diff),
        },
    )


def _parameter_perturbation_checks(spec: dict[str, Any], signal_rows: list[dict[str, str]], signals_path: Path | None) -> list[dict[str, Any]]:
    required_tests = json.dumps(spec.get("validation", {}).get("required_tests", []), ensure_ascii=False).lower()
    has_parameter_contract = any(
        marker in required_tests
        for marker in ["selection_count", "parameter", "robustness", "threshold", "random"]
    )
    contract_check = _check(
        "stability",
        "parameter_perturbation_contract",
        "pass" if has_parameter_contract else "needs_review",
        "Strategy validation contract should include parameter perturbation or robustness tests before PM promotion.",
        {"required_tests": spec.get("validation", {}).get("required_tests", [])},
    )
    if not signals_path:
        return [contract_check, _missing("stability", "parameter_perturbation_from_signals", "rebalance_signals_csv missing")]
    if not signal_rows:
        return [contract_check, _check("stability", "parameter_perturbation_from_signals", "needs_review", "Signal file is empty.", {})]
    counts = [_to_float(row.get("selected_count")) for row in signal_rows]
    counts = [int(value) for value in counts if value is not None]
    configured_count = int(spec.get("portfolio", {}).get("selection_count", 0) or 0)
    count_values = sorted(set(counts))
    count_stable = configured_count in count_values and len(count_values) <= 3
    cases = sorted({row.get("case", "") for row in signal_rows if row.get("case")})
    factors = sorted({row.get("factor", "") for row in signal_rows if row.get("factor")})
    return [
        contract_check,
        _check(
            "stability",
            "parameter_perturbation_from_signals",
            "pass" if count_stable else "needs_review",
            "Review whether small parameter changes alter selected_count, state cases, or factor family unexpectedly.",
            {
                "configured_selection_count": configured_count,
                "observed_selected_counts": ";".join(str(item) for item in count_values),
                "observed_cases": ";".join(cases),
                "observed_factors": ";".join(factors),
                "note": "For full parameter perturbation, rerun the strategy runner with selection_count 8/10/12 or documented thresholds.",
            },
        )
    ]


def _visible_fields(rows: list[dict[str, str]]) -> list[str]:
    fields = set()
    for row in rows[:1000]:
        for key in row:
            lower = key.lower()
            if lower.endswith("_visible_date") or lower.endswith("_notice_date") or lower.endswith("_announce_date") or lower in {"visible_date", "notice_date", "announce_date"}:
                fields.add(key)
    return sorted(fields)


def _visible_date_violations(rows: list[dict[str, str]], fields: list[str]) -> list[str]:
    result = []
    for row in rows:
        trade_date = row.get("trade_date")
        if not trade_date:
            continue
        trade = trade_date[:10]
        for field in fields:
            value = row.get(field)
            if value and value[:10] > trade:
                result.append(f"{trade}:{row.get('code','')}:{field}={value[:10]}")
                break
    return result


def _check(category: str, check: str, severity: str, detail: str, metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "category": category,
        "check": check,
        "severity": severity,
        "detail": detail,
        "metrics_json": json.dumps(metrics, ensure_ascii=False, sort_keys=True),
    }


def _missing(category: str, check: str, detail: str) -> dict[str, Any]:
    return _check(category, check, "needs_review", detail, {})


def _read_csv(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _write_report(path: Path, summary: dict[str, Any], checks: list[dict[str, Any]]) -> None:
    lines = [
        f"# Overfit Audit Report: {summary['strategy_id']}",
        "",
        f"- Status: `{summary['status']}`",
        f"- Blockers: `{summary['blocker_count']}`",
        f"- Needs review: `{summary['needs_review_count']}`",
        "",
        "## Checks",
        "",
    ]
    for row in checks:
        lines.append(f"- `{row['category']} / {row['check']}`: `{row['severity']}` - {row['detail']} Metrics: `{row['metrics_json']}`")
    lines.extend(["", "## Governance", "", summary["governance"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _check_fields() -> list[str]:
    return ["category", "check", "severity", "detail", "metrics_json"]


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


def _compound(returns: list[float]) -> float:
    value = 1.0
    for ret in returns:
        value *= 1.0 + ret
    return value - 1.0


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * q)))
    return ordered[index]


def _round(value: Any) -> Any:
    numeric = _to_float(value)
    if numeric is None:
        return value
    return round(numeric, 6)


def _window_label(row: dict[str, Any]) -> str:
    return f"{row['start']}..{row['end']}:{_round(row['strategy_return'])}"


def _most_common(values: list[str]) -> str:
    if not values:
        return ""
    return max(sorted(set(values)), key=values.count)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-overfit-audit")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--panel", type=Path)
    parser.add_argument("--daily-returns-csv", type=Path)
    parser.add_argument("--rebalance-signals-csv", type=Path)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--strategy-id")
    parser.add_argument("--random-seed", type=int, default=20260716)
    parser.add_argument("--random-windows", type=int, default=100)
    parser.add_argument("--min-window-days", type=int, default=252)
    args = parser.parse_args(argv)
    result = run_overfit_audit(
        args.spec,
        args.out,
        panel_path=args.panel,
        daily_returns_csv=args.daily_returns_csv,
        rebalance_signals_csv=args.rebalance_signals_csv,
        strategy_id=args.strategy_id,
        random_seed=args.random_seed,
        random_windows=args.random_windows,
        min_window_days=args.min_window_days,
    )
    print(result.report_path)
    return 0 if result.blocker_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

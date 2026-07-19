from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

from v5.basket_field_utils import enrich_basket_panel_row
from v5.basket_scoring import score_basket_date_rows
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import compound, fmt_float, pearson, ranks, to_float


DEFAULT_CONFIG = Path("config/dividend_low_vol_fcf_basket_v56.json")
DEFAULT_SIGNALS = Path("validation_formal_v56_basket_constructor") / "basket_rebalance_signals.csv"
DEFAULT_DAILY_RETURNS = (
    Path("local_daily_backtests_v56_basket")
    / "v56_dividend_low_vol_fcf_shadow_basket"
    / "daily_returns.csv"
)
DEFAULT_OUT_DIR = Path("validation_formal_v56_basket")


@dataclass(frozen=True)
class BasketFormalValidationResult:
    output_dir: Path
    summary_path: Path
    report_path: Path
    combined_panel_path: Path
    status: str
    signal_count: int
    panel_row_count: int


def run_basket_formal_validation(
    config_path: Path = DEFAULT_CONFIG,
    signals_csv: Path = DEFAULT_SIGNALS,
    daily_returns_csv: Path = DEFAULT_DAILY_RETURNS,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> BasketFormalValidationResult:
    config = _read_json(config_path)
    project = str(config.get("project") or "v56_dividend_low_vol_fcf_shadow_basket")
    out = out_dir / project
    out.mkdir(parents=True, exist_ok=True)

    panel_rows = _load_combined_panel(config)
    signal_rows = read_csv_rows(signals_csv)
    daily_rows = read_csv_rows(daily_returns_csv)
    scored_panel_rows = _score_panel_rows(panel_rows, config)

    combined_panel_path = out / "combined_basket_panel_for_validation.csv"
    write_csv_rows(combined_panel_path, _fieldnames(scored_panel_rows), scored_panel_rows)

    leakage_rows = _visible_date_audit(scored_panel_rows, signal_rows)
    rolling_rows = _rolling_by_year(daily_rows)
    baseline_rows = _baseline_tests(daily_rows)
    ic_rows = _factor_ic_rankic(scored_panel_rows, config)
    ablation_rows = _ablation_proxy(ic_rows)
    robustness_rows = _robustness_checks(daily_rows, signal_rows)
    exposure_rows = _sector_exposure(signal_rows)
    weak_year_rows = _weak_years(rolling_rows)

    write_csv_rows(out / "notice_date_leakage_audit.csv", _fieldnames(leakage_rows), leakage_rows)
    write_csv_rows(out / "rolling_validation.csv", _fieldnames(rolling_rows), rolling_rows)
    write_csv_rows(out / "baseline_tests.csv", _fieldnames(baseline_rows), baseline_rows)
    write_csv_rows(out / "factor_ic_rankic.csv", _fieldnames(ic_rows), ic_rows)
    write_csv_rows(out / "ablation_proxy.csv", _fieldnames(ablation_rows), ablation_rows)
    write_csv_rows(out / "robustness_checks.csv", _fieldnames(robustness_rows), robustness_rows)
    write_csv_rows(out / "sector_exposure.csv", _fieldnames(exposure_rows), exposure_rows)
    write_csv_rows(out / "weak_year_analysis.csv", _fieldnames(weak_year_rows), weak_year_rows)

    blocker_count = sum(1 for row in leakage_rows + robustness_rows if row.get("status") == "blocker")
    needs_review_count = sum(1 for row in leakage_rows + robustness_rows if row.get("status") == "needs_review")
    status = "blocked" if blocker_count else ("needs_review" if needs_review_count else "formal_validation_completed_not_acceptance")
    summary = {
        "schema_version": 1,
        "strategy_id": project,
        "experiment_layer": "research_pit_validation",
        "status": status,
        "config": str(config_path),
        "signals_csv": str(signals_csv),
        "daily_returns_csv": str(daily_returns_csv),
        "combined_panel": str(combined_panel_path),
        "panel_row_count": len(scored_panel_rows),
        "signal_count": len({row.get("trade_date") for row in signal_rows if row.get("trade_date")}),
        "holding_signal_count": len(signal_rows),
        "rolling_validation": rolling_rows,
        "baseline_tests": baseline_rows,
        "factor_ic_rankic": ic_rows,
        "ablation_proxy": ablation_rows,
        "robustness_checks": robustness_rows,
        "sector_exposure": exposure_rows,
        "weak_year_analysis": weak_year_rows,
        "governance": (
            "Basket formal validation is evidence for PM review only. "
            "The 2021-2026 window remains platform-confirmation context and is not accepted-strategy proof."
        ),
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    summary_path = out / "basket_formal_validation_summary.json"
    report_path = out / "basket_formal_validation_report.md"
    write_json_file(summary_path, summary)
    report_path.write_text(_report(summary), encoding="utf-8")
    return BasketFormalValidationResult(out, summary_path, report_path, combined_panel_path, status, len(signal_rows), len(scored_panel_rows))


def _load_combined_panel(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sector in config.get("sectors", []):
        path = Path(str(sector.get("panel_csv") or ""))
        if not path.exists():
            raise FileNotFoundError(f"basket sector panel not found: {path}")
        sector_id = str(sector.get("sector_id") or "")
        strategy_id = str(sector.get("strategy_id") or "")
        for row in read_csv_rows(path):
            enriched = enrich_basket_panel_row(row, sector_id)
            enriched["sector_id"] = sector_id
            enriched["source_strategy_id"] = strategy_id
            rows.append(enriched)
    return rows


def _score_panel_rows(rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    required = [str(item) for item in config.get("portfolio", {}).get("required_fields", [])]
    start_date = str(config.get("portfolio", {}).get("start_date") or "")
    end_date = str(config.get("portfolio", {}).get("end_date") or "")
    raw_spec = {"signals": config.get("signals", {})}
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        day = str(row.get("trade_date") or "")[:10]
        if not day or (start_date and day < start_date) or (end_date and day > end_date):
            continue
        if any(row.get(field) in (None, "") for field in required):
            continue
        by_date[day].append(row)
    scored_rows: list[dict[str, Any]] = []
    for day, date_rows in sorted(by_date.items()):
        scored, used_factors = score_basket_date_rows(raw_spec, date_rows)
        for row in scored:
            enriched = dict(row)
            enriched["basket_used_factors"] = ";".join(used_factors)
            scored_rows.append(enriched)
    return scored_rows


def _visible_date_audit(panel_rows: list[dict[str, Any]], signal_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for name, source_rows in [("combined_panel", panel_rows), ("rebalance_signals", signal_rows)]:
        fields = _visible_fields(source_rows)
        violations = _visible_date_violations(source_rows, fields)
        rows.append(
            {
                "scope": name,
                "status": "blocker" if violations else "pass",
                "row_count": len(source_rows),
                "visible_date_fields": ";".join(fields),
                "future_visible_date_violations": len(violations),
                "examples": ";".join(violations[:5]),
                "detail": "All visible/notice/announce dates must be no later than trade_date.",
            }
        )
    return rows


def _rolling_by_year(daily_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    by_year: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in daily_rows:
        day = str(row.get("trade_date") or "")[:10]
        if day:
            by_year[day[:4]].append(row)
    result = []
    for year, rows in sorted(by_year.items()):
        strategy = [to_float(row.get("strategy_return")) or 0.0 for row in rows]
        benchmark = [to_float(row.get("benchmark_return")) or 0.0 for row in rows]
        result.append(
            {
                "year": year,
                "status": "completed",
                "days": len(rows),
                "strategy_return": fmt_float(compound(strategy)),
                "benchmark_return": fmt_float(compound(benchmark)),
                "excess_return": fmt_float((compound(strategy) or 0.0) - (compound(benchmark) or 0.0)),
                "positive_day_ratio": fmt_float(sum(1 for value in strategy if value > 0) / len(strategy) if strategy else None),
                "max_drawdown": fmt_float(_max_drawdown(strategy)),
            }
        )
    return result


def _baseline_tests(daily_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    strategy = [to_float(row.get("strategy_return")) or 0.0 for row in daily_rows]
    benchmark = [to_float(row.get("benchmark_return")) or 0.0 for row in daily_rows]
    excess = [a - b for a, b in zip(strategy, benchmark)]
    return [
        {
            "case": "basket_current",
            "status": "completed",
            "return": fmt_float(compound(strategy)),
            "max_drawdown": fmt_float(_max_drawdown(strategy)),
            "daily_win_rate": fmt_float(sum(1 for value in strategy if value > 0) / len(strategy) if strategy else None),
        },
        {
            "case": "same_pool_equal_weight_total_return_proxy",
            "status": "completed",
            "return": fmt_float(compound(benchmark)),
            "max_drawdown": fmt_float(_max_drawdown(benchmark)),
            "daily_win_rate": fmt_float(sum(1 for value in benchmark if value > 0) / len(benchmark) if benchmark else None),
        },
        {
            "case": "basket_excess_vs_same_pool",
            "status": "completed",
            "return": fmt_float((compound(strategy) or 0.0) - (compound(benchmark) or 0.0)),
            "max_drawdown": fmt_float(_max_drawdown(excess)),
            "daily_win_rate": fmt_float(sum(1 for value in excess if value > 0) / len(excess) if excess else None),
        },
    ]


def _factor_ic_rankic(rows: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    factors = list(config.get("signals", {}).get("factors", []))
    targets = ["score"] + [str(factor.get("name")) for factor in factors]
    directions = {"score": "higher_is_better"}
    directions.update({str(factor.get("name")): str(factor.get("direction") or "higher_is_better") for factor in factors})
    result = []
    for target in targets:
        by_date: dict[str, list[tuple[float, float]]] = defaultdict(list)
        for row in rows:
            future = to_float(row.get("future_return") or row.get("total_return") or row.get("price_return"))
            value = to_float(row.get(target))
            if future is None or value is None:
                continue
            if directions.get(target) == "lower_is_better":
                value = -value
            by_date[str(row.get("trade_date") or "")[:10]].append((value, future))
        ic_values = []
        rank_ic_values = []
        observations = 0
        for pairs in by_date.values():
            if len(pairs) < 3:
                continue
            x = [item[0] for item in pairs]
            y = [item[1] for item in pairs]
            ic = pearson(x, y)
            rank_ic = pearson(ranks(x), ranks(y))
            if ic is not None:
                ic_values.append(ic)
            if rank_ic is not None:
                rank_ic_values.append(rank_ic)
            observations += len(pairs)
        result.append(
            {
                "factor": target,
                "scope": "full_candidate_panel_after_required_fields",
                "date_count": len(ic_values),
                "observations": observations,
                "mean_ic": fmt_float(mean(ic_values) if ic_values else None),
                "mean_rankic": fmt_float(mean(rank_ic_values) if rank_ic_values else None),
                "positive_ic_ratio": fmt_float(sum(1 for item in ic_values if item > 0) / len(ic_values) if ic_values else None),
                "status": "completed" if ic_values else "insufficient_sample",
            }
        )
    return result


def _ablation_proxy(ic_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    score_ic = to_float(next((row.get("mean_rankic") for row in ic_rows if row.get("factor") == "score"), None))
    for row in ic_rows:
        if row.get("factor") == "score":
            continue
        rank_ic = to_float(row.get("mean_rankic"))
        rows.append(
            {
                "case": f"single_factor_signal_{row.get('factor')}",
                "status": row.get("status"),
                "mean_rankic": row.get("mean_rankic"),
                "rankic_gap_vs_composite": fmt_float((score_ic - rank_ic) if score_ic is not None and rank_ic is not None else None),
                "detail": "Proxy ablation at basket level. Full re-run ablation should be added before live deployment.",
            }
        )
    return rows


def _robustness_checks(daily_rows: list[dict[str, str]], signal_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    strategy = [(str(row.get("trade_date") or "")[:10], to_float(row.get("strategy_return")) or 0.0) for row in daily_rows]
    random_windows = _deterministic_windows(strategy, 252)
    positive_ratio = sum(1 for row in random_windows if row["return"] > 0) / len(random_windows) if random_windows else None
    counts_by_date: dict[str, int] = defaultdict(int)
    sector_weights: dict[tuple[str, str], float] = defaultdict(float)
    for row in signal_rows:
        day = str(row.get("trade_date") or "")[:10]
        counts_by_date[day] += 1
        sector_weights[(day, str(row.get("sector_id") or ""))] += to_float(row.get("target_weight")) or 0.0
    max_sector_weight = max(sector_weights.values()) if sector_weights else None
    selected_counts = sorted(set(counts_by_date.values()))
    rows = [
        {
            "check": "rolling_252d_subwindows",
            "status": "pass" if positive_ratio is not None and positive_ratio >= 0.7 else "needs_review",
            "window_count": len(random_windows),
            "positive_window_ratio": fmt_float(positive_ratio),
            "median_window_return": fmt_float(median([row["return"] for row in random_windows]) if random_windows else None),
            "worst_window": _window_label(min(random_windows, key=lambda item: item["return"])) if random_windows else "",
            "best_window": _window_label(max(random_windows, key=lambda item: item["return"])) if random_windows else "",
            "detail": "Quarterly-spaced 252 trading day windows test date-range sensitivity.",
        },
        {
            "check": "sector_weight_cap_realized",
            "status": "pass" if max_sector_weight is not None and max_sector_weight <= 0.350001 else "needs_review",
            "max_sector_weight": fmt_float(max_sector_weight),
            "detail": "Realized signal weight should respect sector cap.",
        },
        {
            "check": "selected_count_stability",
            "status": "pass" if selected_counts and min(selected_counts) >= 20 else "needs_review",
            "observed_selected_counts": ";".join(str(item) for item in selected_counts),
            "detail": "Very low selected counts can make basket results fragile.",
        },
    ]
    return rows


def _sector_exposure(signal_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    by_sector: dict[str, dict[str, Any]] = {}
    date_count = len({row.get("trade_date") for row in signal_rows if row.get("trade_date")})
    for row in signal_rows:
        sector = str(row.get("sector_id") or "")
        bucket = by_sector.setdefault(sector, {"sector_id": sector, "holding_count": 0, "weight_sum": 0.0})
        bucket["holding_count"] += 1
        bucket["weight_sum"] += to_float(row.get("target_weight")) or 0.0
    rows = []
    for sector, item in sorted(by_sector.items()):
        rows.append(
            {
                "sector_id": sector,
                "holding_count": item["holding_count"],
                "avg_weight_per_rebalance": fmt_float(item["weight_sum"] / date_count if date_count else None),
                "avg_names_per_rebalance": fmt_float(item["holding_count"] / date_count if date_count else None),
            }
        )
    return rows


def _weak_years(rolling_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(
        rolling_rows,
        key=lambda row: to_float(row.get("strategy_return")) if to_float(row.get("strategy_return")) is not None else 999,
    )
    return [
        {
            "year": row.get("year"),
            "strategy_return": row.get("strategy_return"),
            "benchmark_return": row.get("benchmark_return"),
            "excess_return": row.get("excess_return"),
            "max_drawdown": row.get("max_drawdown"),
            "diagnosis_required": "yes" if index < 2 else "no",
        }
        for index, row in enumerate(ordered)
    ]


def _visible_fields(rows: list[dict[str, Any]]) -> list[str]:
    fields = set()
    for row in rows[:1000]:
        for key in row:
            lower = key.lower()
            if (
                lower.endswith("_visible_date")
                or lower.endswith("_notice_date")
                or lower.endswith("_announce_date")
                or lower in {"visible_date", "notice_date", "announce_date"}
            ):
                fields.add(key)
    return sorted(fields)


def _visible_date_violations(rows: list[dict[str, Any]], fields: list[str]) -> list[str]:
    violations = []
    for row in rows:
        trade_date = str(row.get("trade_date") or "")[:10]
        if not trade_date:
            continue
        for field in fields:
            value = str(row.get(field) or "")[:10]
            if value and value > trade_date:
                violations.append(f"{trade_date}:{row.get('code','')}:{field}={value}")
                break
    return violations


def _deterministic_windows(series: list[tuple[str, float]], window: int) -> list[dict[str, Any]]:
    if len(series) < window:
        return []
    step = max(1, window // 4)
    rows = []
    for start in range(0, len(series) - window + 1, step):
        subset = series[start : start + window]
        values = [item[1] for item in subset]
        rows.append({"start": subset[0][0], "end": subset[-1][0], "days": len(subset), "return": compound(values) or 0.0})
    return rows


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
            max_dd = max(max_dd, 1.0 - nav / peak)
    return max_dd


def _window_label(row: dict[str, Any]) -> str:
    return f"{row['start']}..{row['end']}:{fmt_float(row['return'])}"


def _fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["status"]
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    return names


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _report(summary: dict[str, Any]) -> str:
    metrics = {row["case"]: row for row in summary["baseline_tests"]}
    current = metrics.get("basket_current", {})
    benchmark = metrics.get("same_pool_equal_weight_total_return_proxy", {})
    weak = summary["weak_year_analysis"][:2]
    lines = [
        "# Basket Formal Validation Report",
        "",
        f"- Status: `{summary['status']}`",
        f"- Panel rows: `{summary['panel_row_count']}`",
        f"- Signal dates: `{summary['signal_count']}`",
        f"- Basket return: `{current.get('return', '')}`",
        f"- Same-pool benchmark return: `{benchmark.get('return', '')}`",
        "",
        "## Evidence",
        "",
        "- The basket uses PIT-enriched sector panels and real JoinQuant daily open/close prices in the local daily simulation.",
        "- IC/RankIC is computed on the full candidate panel after required low-vol fields are available, not only on selected holdings.",
        "- Rolling validation is reported by calendar year; weak-year rows are diagnostics, not tuning permission.",
        "",
        "## Weak Years",
        "",
    ]
    for row in weak:
        lines.append(
            f"- `{row.get('year')}`: strategy `{row.get('strategy_return')}`, "
            f"benchmark `{row.get('benchmark_return')}`, max drawdown `{row.get('max_drawdown')}`"
        )
    lines.extend(["", "## Governance", "", summary["governance"], ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="v5-basket-formal-validation")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--signals", type=Path, default=DEFAULT_SIGNALS)
    parser.add_argument("--daily-returns-csv", type=Path, default=DEFAULT_DAILY_RETURNS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)
    result = run_basket_formal_validation(args.config, args.signals, args.daily_returns_csv, args.out)
    print(result.report_path)
    return 0 if result.status != "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any

from v5.engine import load_spec
from v5.scoring import apply_value_trap_guard, score_rows


@dataclass(frozen=True)
class FactorResult:
    name: str
    observations: int
    dates: int
    mean_ic: float | None
    mean_rank_ic: float | None
    positive_ic_ratio: float | None
    top_minus_bottom_mean_return: float | None


def validate_panel(spec_path: Path, panel_path: Path, out_dir: Path) -> Path:
    spec = load_spec(spec_path)
    rows = _load_panel(panel_path)
    out = out_dir / spec.strategy_id
    out.mkdir(parents=True, exist_ok=True)

    factor_results = [_factor_result(rows, factor.name, factor.direction) for factor in spec.factors]
    portfolio_rows, portfolio_summary = _portfolio_backtest(rows, spec.raw)
    fold_rows = _rolling_folds(portfolio_rows, spec.raw)

    factor_path = out / "factor_validation.csv"
    portfolio_path = out / "portfolio_periods.csv"
    fold_path = out / "rolling_folds.csv"
    summary_path = out / "validation_summary.json"
    report_path = out / "validation_report.md"

    _write_csv(
        factor_path,
        ["name", "observations", "dates", "mean_ic", "mean_rank_ic", "positive_ic_ratio", "top_minus_bottom_mean_return"],
        [result.__dict__ for result in factor_results],
    )
    _write_csv(portfolio_path, ["trade_date", "next_trade_date", "selected_count", "mean_return", "cash_weight", "selected_codes"], portfolio_rows)
    _write_csv(fold_path, ["fold_id", "start", "end", "periods", "cum_return", "mean_return", "positive_period_ratio"], fold_rows)

    summary = {
        "strategy_id": spec.strategy_id,
        "panel": str(panel_path),
        "row_count": len(rows),
        "date_count": len({row["trade_date"] for row in rows}),
        "security_count": len({row["code"] for row in rows}),
        "factor_results": [result.__dict__ for result in factor_results],
        "portfolio_summary": portfolio_summary,
        "fold_count": len(fold_rows),
        "status": "research_validation_completed",
        "limitations": [
            "Validation quality depends on the supplied panel and source labels.",
            "This runner computes factor evidence and a simple equal-weight portfolio path; platform execution confirmation is still separate.",
            "If a factor is constant on a date, IC and grouped-return spread are not computed for that date.",
            "Price adjustment policy must be confirmed before accepting long-window return statistics.",
        ],
    }
    _write_json(summary_path, summary)
    _write_report(report_path, summary, fold_rows)
    return report_path


def _load_panel(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        ret = _to_float(row.get("total_return"))
        if ret is None:
            ret = _to_float(row.get("future_return"))
        row["future_return"] = ret
    return [row for row in rows if row.get("trade_date") and row.get("code") and row["future_return"] is not None]


def _factor_result(rows: list[dict[str, Any]], factor_name: str, direction: str) -> FactorResult:
    by_date = _group_by_date(rows)
    ic_values: list[float] = []
    rank_ic_values: list[float] = []
    spreads: list[float] = []
    observations = 0

    for date_rows in by_date.values():
        pairs = []
        for row in date_rows:
            raw_value = _to_float(row.get(factor_name))
            ret = row["future_return"]
            if raw_value is None or ret is None:
                continue
            value = -raw_value if direction == "lower_is_better" else raw_value
            pairs.append((value, ret))
        if len(pairs) < 3:
            continue
        observations += len(pairs)
        x = [item[0] for item in pairs]
        y = [item[1] for item in pairs]
        ic = _pearson(x, y)
        rank_ic = _pearson(_ranks(x), _ranks(y))
        if ic is not None:
            ic_values.append(ic)
        if rank_ic is not None:
            rank_ic_values.append(rank_ic)
        spread = _top_bottom_spread(pairs)
        if spread is not None:
            spreads.append(spread)

    return FactorResult(
        name=factor_name,
        observations=observations,
        dates=len(ic_values),
        mean_ic=_safe_mean(ic_values),
        mean_rank_ic=_safe_mean(rank_ic_values),
        positive_ic_ratio=_positive_ratio(ic_values),
        top_minus_bottom_mean_return=_safe_mean(spreads),
    )


def _portfolio_backtest(rows: list[dict[str, Any]], raw_spec: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_date = _group_by_date(rows)
    selection_count = int(raw_spec["portfolio"]["selection_count"])

    period_rows: list[dict[str, Any]] = []
    returns: list[float] = []
    cash_weights: list[float] = []
    for trade_date, date_rows in sorted(by_date.items()):
        scored, _used_factors = score_rows(raw_spec, date_rows)
        eligible = apply_value_trap_guard(raw_spec, scored)
        selected = sorted(eligible, key=lambda item: item["score"], reverse=True)[:selection_count]
        if not selected:
            period_return = 0.0
            selected_codes = []
        else:
            period_return = mean(row["future_return"] for row in selected)
            selected_codes = [row["code"] for row in selected]
        cash_weight = max(0.0, 1.0 - (len(selected) / selection_count))
        returns.append(period_return)
        cash_weights.append(cash_weight)
        period_rows.append(
            {
                "trade_date": trade_date,
                "next_trade_date": selected[0].get("next_trade_date", "") if selected else "",
                "selected_count": len(selected),
                "mean_return": period_return,
                "cash_weight": cash_weight,
                "selected_codes": ";".join(selected_codes),
            }
        )

    summary = {
        "periods": len(period_rows),
        "cum_return": _compound(returns),
        "mean_period_return": _safe_mean(returns),
        "median_period_return": median(returns) if returns else None,
        "positive_period_ratio": _positive_ratio(returns),
        "mean_cash_weight": _safe_mean(cash_weights),
    }
    return period_rows, summary


def _score_date_rows(date_rows: list[dict[str, Any]], factors: list[dict[str, Any]], weights: dict[str, float]) -> list[dict[str, Any]]:
    factor_scores: dict[str, dict[str, float]] = {}
    for factor in factors:
        name = factor["name"]
        values = []
        keyed = []
        for row in date_rows:
            raw_value = _to_float(row.get(name))
            if raw_value is None:
                continue
            value = -raw_value if factor["direction"] == "lower_is_better" else raw_value
            values.append(value)
            keyed.append((row["code"], value))
        zscores = _zscores(values)
        factor_scores[name] = {code: zscores[index] for index, (code, _value) in enumerate(keyed)}

    scored = []
    for row in date_rows:
        score = 0.0
        used_weight = 0.0
        for factor in factors:
            name = factor["name"]
            factor_weight = float(weights.get(name, 1.0))
            value = factor_scores.get(name, {}).get(row["code"])
            if value is None:
                continue
            score += factor_weight * value
            used_weight += abs(factor_weight)
        if used_weight <= 0:
            continue
        enriched = dict(row)
        enriched["score"] = score / used_weight
        scored.append(enriched)
    return scored


def _apply_value_trap_guard(scored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    quality_names = [
        "non_performing_loan_ratio",
        "provision_coverage_ratio",
        "core_tier_1_capital_adequacy_ratio",
    ]
    quality_values = []
    enriched = []
    for row in scored:
        npl = _to_float(row.get("non_performing_loan_ratio"))
        provision = _to_float(row.get("provision_coverage_ratio"))
        capital = _to_float(row.get("core_tier_1_capital_adequacy_ratio"))
        if npl is None or provision is None or capital is None:
            continue
        quality = (-npl) + provision + capital
        row = dict(row)
        row["quality_guard_score"] = quality
        quality_values.append(quality)
        enriched.append(row)
    if not enriched:
        return scored
    threshold = median(quality_values)
    return [row for row in enriched if row["quality_guard_score"] >= threshold]


def _rolling_folds(period_rows: list[dict[str, Any]], raw_spec: dict[str, Any]) -> list[dict[str, Any]]:
    review_years = int(raw_spec["validation"].get("review_years", 1))
    periods_per_fold = max(1, review_years * 4)
    folds = []
    for index in range(0, len(period_rows), periods_per_fold):
        chunk = period_rows[index : index + periods_per_fold]
        if not chunk:
            continue
        returns = [float(row["mean_return"]) for row in chunk]
        folds.append(
            {
                "fold_id": f"fold_{len(folds) + 1:02d}",
                "start": chunk[0]["trade_date"],
                "end": chunk[-1]["trade_date"],
                "periods": len(chunk),
                "cum_return": _compound(returns),
                "mean_return": _safe_mean(returns),
                "positive_period_ratio": _positive_ratio(returns),
            }
        )
    return folds


def _group_by_date(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["trade_date"]].append(row)
    return grouped


def _top_bottom_spread(pairs: list[tuple[float, float]]) -> float | None:
    if len({value for value, _ret in pairs}) < 2:
        return None
    ordered = sorted(pairs, key=lambda item: item[0])
    group_size = max(1, len(ordered) // 3)
    bottom = ordered[:group_size]
    top = ordered[-group_size:]
    return mean(ret for _value, ret in top) - mean(ret for _value, ret in bottom)


def _pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) != len(y) or len(x) < 2:
        return None
    mx = mean(x)
    my = mean(y)
    numerator = sum((a - mx) * (b - my) for a, b in zip(x, y))
    denom_x = math.sqrt(sum((a - mx) ** 2 for a in x))
    denom_y = math.sqrt(sum((b - my) ** 2 for b in y))
    if denom_x == 0 or denom_y == 0:
        return None
    return numerator / (denom_x * denom_y)


def _ranks(values: list[float]) -> list[float]:
    ordered = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    idx = 0
    while idx < len(ordered):
        end = idx
        while end + 1 < len(ordered) and ordered[end + 1][0] == ordered[idx][0]:
            end += 1
        avg_rank = (idx + end + 2) / 2.0
        for pos in range(idx, end + 1):
            ranks[ordered[pos][1]] = avg_rank
        idx = end + 1
    return ranks


def _zscores(values: list[float]) -> list[float]:
    if not values:
        return []
    mu = mean(values)
    variance = sum((value - mu) ** 2 for value in values) / len(values)
    sigma = math.sqrt(variance)
    if sigma == 0:
        return [0.0 for _value in values]
    return [(value - mu) / sigma for value in values]


def _compound(returns: list[float]) -> float | None:
    if not returns:
        return None
    value = 1.0
    for ret in returns:
        value *= 1.0 + ret
    return value - 1.0


def _safe_mean(values: list[float]) -> float | None:
    return mean(values) if values else None


def _positive_ratio(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(1 for value in values if value > 0) / len(values)


def _to_float(value: Any) -> float | None:
    if value in {None, "", "nan", "NaN", "None"}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _write_report(path: Path, summary: dict[str, Any], fold_rows: list[dict[str, Any]]) -> None:
    lines = [
        f"# Validation Report: {summary['strategy_id']}",
        "",
        f"- Panel rows: `{summary['row_count']}`",
        f"- Dates: `{summary['date_count']}`",
        f"- Securities: `{summary['security_count']}`",
        f"- Portfolio cumulative return: `{summary['portfolio_summary']['cum_return']}`",
        f"- Positive period ratio: `{summary['portfolio_summary']['positive_period_ratio']}`",
        f"- Mean cash weight: `{summary['portfolio_summary']['mean_cash_weight']}`",
        "",
        "## Factor Evidence",
        "",
    ]
    for result in summary["factor_results"]:
        lines.append(
            f"- `{result['name']}`: mean IC=`{result['mean_ic']}`, mean RankIC=`{result['mean_rank_ic']}`, positive IC ratio=`{result['positive_ic_ratio']}`, spread=`{result['top_minus_bottom_mean_return']}`"
        )
    lines.extend(["", "## Rolling Folds", ""])
    for fold in fold_rows:
        lines.append(
            f"- `{fold['fold_id']}` {fold['start']} to {fold['end']}: periods=`{fold['periods']}`, cum_return=`{fold['cum_return']}`, positive_ratio=`{fold['positive_period_ratio']}`"
        )
    lines.extend(["", "## Decision", "", "This report is validation evidence, not final acceptance. Candidate governance must compare it against formal baselines on common samples."])
    lines.extend(["", "## Limitations", ""])
    for item in summary.get("limitations", []):
        lines.append(f"- {item}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-validate-research")
    parser.add_argument("spec", type=Path)
    parser.add_argument("panel", type=Path)
    parser.add_argument("--out", type=Path, default=Path("validation"))
    args = parser.parse_args(argv)
    print(validate_panel(args.spec, args.panel, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

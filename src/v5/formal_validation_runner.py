from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from v5.engine import load_spec
from v5.validation_runner import _apply_value_trap_guard, _score_date_rows, _to_float


def run_formal_validation(spec_path: Path, panel_path: Path, out_dir: Path) -> Path:
    spec = load_spec(spec_path)
    rows = _load_panel(panel_path)
    out = out_dir / spec.strategy_id
    out.mkdir(parents=True, exist_ok=True)
    baseline_rows = _baseline_tests(rows, spec.raw)
    ablation_rows = _ablation_tests(rows, spec.raw)
    robustness_rows = _robustness_tests(rows, spec.raw)
    _write_csv(out / "baseline_tests.csv", list(baseline_rows[0].keys()), baseline_rows)
    _write_csv(out / "ablation_tests.csv", list(ablation_rows[0].keys()), ablation_rows)
    _write_csv(out / "robustness_tests.csv", list(robustness_rows[0].keys()), robustness_rows)
    summary = {
        "strategy_id": spec.strategy_id,
        "panel": str(panel_path),
        "row_count": len(rows),
        "date_count": len({row["trade_date"] for row in rows}),
        "status": "formal_validation_completed_not_acceptance",
        "baseline_tests": baseline_rows,
        "ablation_tests": ablation_rows,
        "robustness_tests": robustness_rows,
        "governance": "Do not use 2021-2026 platform-confirmation results for tuning. Single-model acceptance requires rolling validation.",
    }
    _write_json(out / "formal_validation_summary.json", summary)
    _write_report(out / "formal_validation_report.md", summary)
    return out / "formal_validation_report.md"


def _baseline_tests(rows: list[dict[str, Any]], raw: dict[str, Any]) -> list[dict[str, Any]]:
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
    for count in [6, 8, 10]:
        result.append(_strategy_case(f"selection_count_{count}", rows, raw, mode="composite", selection_count=count))
    for scale in [0.8, 1.0, 1.2]:
        result.append(_strategy_case(f"value_weight_scale_{scale}", rows, raw, mode="composite", weight_scale={"low_price_to_book": scale, "dividend_yield": scale}))
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
) -> dict[str, Any]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_date[row["trade_date"]].append(row)
    returns = []
    selected_counts = []
    current_selection_count = selection_count or int(raw["portfolio"]["selection_count"])
    factors = [dict(item) for item in raw["signals"]["factors"] if item["name"] != drop_factor]
    weights = dict(raw["signals"]["scoring"].get("weights", {}))
    if drop_factor:
        weights.pop(drop_factor, None)
    if weight_scale:
        for key, scale in weight_scale.items():
            if key in weights:
                weights[key] = float(weights[key]) * scale
    for _date, date_rows in sorted(by_date.items()):
        if mode == "equal_all":
            selected = date_rows
        elif mode == "single_factor" and factor:
            selected = sorted(
                [row for row in date_rows if _to_float(row.get(factor)) is not None],
                key=lambda row: _to_float(row.get(factor)) or 0.0,
            )[:current_selection_count]
        else:
            scored = _score_date_rows(date_rows, factors, weights)
            selected = sorted(_apply_value_trap_guard(scored), key=lambda item: item["score"], reverse=True)[:current_selection_count]
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


def _load_panel(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = []
    for row in rows:
        ret = _to_float(row.get("total_return"))
        if ret is None:
            ret = _to_float(row.get("future_return"))
        if row.get("trade_date") and row.get("code") and ret is not None:
            item = dict(row)
            item["future_return"] = ret
            result.append(item)
    return result


def _compound(returns: list[float]) -> float | None:
    if not returns:
        return None
    value = 1.0
    for ret in returns:
        value *= 1.0 + ret
    return value - 1.0


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [f"# Formal Validation Report: {summary['strategy_id']}", "", f"- Status: `{summary['status']}`", ""]
    for section in ["baseline_tests", "ablation_tests", "robustness_tests"]:
        lines.extend([f"## {section}", ""])
        for row in summary[section]:
            lines.append(f"- `{row['case']}`: cum_return=`{row['cum_return']}`, positive_ratio=`{row['positive_ratio']}`, mean_selected_count=`{row['mean_selected_count']}`")
        lines.append("")
    lines.extend(["## Governance", "", summary["governance"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v5-formal-validation")
    parser.add_argument("spec", type=Path)
    parser.add_argument("panel", type=Path)
    parser.add_argument("--out", type=Path, default=Path("validation_formal"))
    args = parser.parse_args(argv)
    print(run_formal_validation(args.spec, args.panel, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

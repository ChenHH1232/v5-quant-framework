from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from v5.engine import load_spec
from v5.experiment_governance import build_run_manifest, write_run_manifest
from v5.validation_runner import _apply_value_trap_guard, _score_date_rows, _to_float


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
    _write_csv(out / "notice_date_leakage_audit.csv", list(leakage_rows[0].keys()) if leakage_rows else ["check", "status", "detail"], leakage_rows)
    _write_csv(out / "rolling_validation.csv", list(rolling_rows[0].keys()) if rolling_rows else ["window", "status"], rolling_rows)
    _write_csv(out / "baseline_tests.csv", list(baseline_rows[0].keys()), baseline_rows)
    _write_csv(out / "ablation_tests.csv", list(ablation_rows[0].keys()), ablation_rows)
    _write_csv(out / "robustness_tests.csv", list(robustness_rows[0].keys()), robustness_rows)
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
            },
            warnings=["Formal validation output is evidence, not automatic strategy acceptance."],
        ),
    )
    _write_report(out / "formal_validation_report.md", summary)
    return out / "formal_validation_report.md"


def _notice_date_leakage_audit(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checked = 0
    missing_notice = 0
    violations = 0
    for row in rows:
        fields_present = any(row.get(name) not in {None, ""} for name in ["asset_quality_trend", "provision_buffer", "capital_resilience"])
        if not fields_present:
            continue
        checked += 1
        notice = row.get("eastmoney_quality_notice_date") or row.get("notice_date") or row.get("announce_date")
        if not notice:
            missing_notice += 1
            continue
        if str(notice)[:10] > str(row.get("trade_date", ""))[:10]:
            violations += 1
    status = "pass" if violations == 0 and missing_notice == 0 else "needs_review"
    return [
        {
            "check": "bank_quality_notice_date_visibility",
            "status": status,
            "checked_rows": checked,
            "missing_notice_date_rows": missing_notice,
            "future_notice_violations": violations,
            "detail": "Quality fields used in formal validation must have notice_date <= trade_date.",
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
    for section in ["notice_date_leakage_audit", "rolling_validation", "baseline_tests", "ablation_tests", "robustness_tests"]:
        lines.extend([f"## {section}", ""])
        for row in summary[section]:
            label = row.get("case") or row.get("check") or row.get("window")
            lines.append(f"- `{label}`: {row}")
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
    parser.add_argument("--experiment-layer", default="research_pit_validation")
    args = parser.parse_args(argv)
    print(run_formal_validation(args.spec, args.panel, args.out, args.experiment_layer))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

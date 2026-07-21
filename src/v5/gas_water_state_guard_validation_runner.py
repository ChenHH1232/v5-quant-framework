from __future__ import annotations

import copy
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from v5.engine import load_spec
from v5.io_utils import read_csv_rows, write_csv_rows, write_json_file
from v5.math_utils import compound, to_float
from v5.scoring import apply_value_trap_guard, score_rows


DATABASE_DIR = Path("\u6570\u636e\u5e93")
DEFAULT_PANEL = DATABASE_DIR / "processed" / "gas_water_true_operating_state_panel_v59" / "panel_with_true_operating_state.csv"
DEFAULT_SPEC = Path("examples") / "gas_water_value_serviceability_v57b_strategy.json"
DEFAULT_OUT_DIR = Path("validation_state_v59_gas_water_true_operating_guard")
DEFAULT_STRATEGY_ID = "gas_water_v57b_text_debt_state_guard_v59b"

GUARD_FIELDS = [
    "true_financing_debt_density_per_10k",
    "true_receivables_collection_density_per_10k",
    "true_connection_install_density_per_10k",
    "same_pool_trailing_60d_return",
    "sector_receivables_to_revenue_median",
]

SUMMARY_FIELDS = [
    "case",
    "guard_field",
    "quantile",
    "min_history",
    "periods",
    "blocked_periods",
    "cum_return",
    "mean_return",
    "positive_ratio",
    "mean_selected_count",
    "return_2023",
    "return_2024",
    "return_2025",
    "return_2026",
    "status",
    "interpretation",
]

DECISION_FIELDS = [
    "case",
    "trade_date",
    "guard_field",
    "guard_value",
    "expanding_threshold",
    "blocked",
    "selected_count",
    "period_return",
    "selected_codes",
]


def run_gas_water_state_guard_validation(
    panel_csv: Path = DEFAULT_PANEL,
    base_spec: Path = DEFAULT_SPEC,
    out_dir: Path = DEFAULT_OUT_DIR,
    *,
    strategy_id: str = DEFAULT_STRATEGY_ID,
    guard_field: str = "true_financing_debt_density_per_10k",
    guard_quantile: float = 0.75,
    min_history: int = 8,
) -> Path:
    rows = _load_rows(panel_csv)
    raw = load_spec(base_spec).raw
    by_date = _group_by_date(rows)
    base_case = _run_case("base_v57b_no_state_guard", by_date, raw, guard_field=None, quantile=None, min_history=min_history)
    primary_case = _run_case(
        f"{strategy_id}_primary",
        by_date,
        raw,
        guard_field=guard_field,
        quantile=guard_quantile,
        min_history=min_history,
    )
    robustness_cases = [
        _run_case(
            f"{strategy_id}_{field}_q{str(quantile).replace('.', '_')}",
            by_date,
            raw,
            guard_field=field,
            quantile=quantile,
            min_history=min_history,
        )
        for field in GUARD_FIELDS
        for quantile in (0.67, 0.75, 0.8)
    ]
    out = out_dir / strategy_id
    out.mkdir(parents=True, exist_ok=True)
    summary_rows = [base_case["summary"], primary_case["summary"], *[case["summary"] for case in robustness_cases]]
    decision_rows = [row for case in [base_case, primary_case, *robustness_cases] for row in case["decisions"]]
    write_csv_rows(out / "state_guard_summary.csv", SUMMARY_FIELDS, summary_rows)
    write_csv_rows(out / "state_guard_rebalance_decisions.csv", DECISION_FIELDS, decision_rows)
    audit = _decision_audit(base_case["summary"], primary_case["summary"], robustness_cases, guard_field)
    write_json_file(
        out / "state_guard_validation_packet.json",
        {
            "strategy_id": strategy_id,
            "panel": str(panel_csv),
            "base_spec": str(base_spec),
            "primary_guard": {
                "field": guard_field,
                "quantile": guard_quantile,
                "min_history": min_history,
                "policy": "At each rebalance, block new equity exposure when the current guard value is above its own expanding historical percentile using prior rebalance dates only.",
            },
            "base_case": base_case["summary"],
            "primary_case": primary_case["summary"],
            "robustness_summary": [case["summary"] for case in robustness_cases],
            "audit": audit,
            "status": audit["status"],
            "pm_decision": audit["pm_decision"],
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    )
    _write_report(out / "state_guard_validation_report.md", audit, base_case["summary"], primary_case["summary"])
    return out / "state_guard_validation_packet.json"


def _load_rows(panel_csv: Path) -> list[dict[str, Any]]:
    rows = []
    for row in read_csv_rows(panel_csv):
        ret = to_float(row.get("total_return"))
        if ret is None:
            ret = to_float(row.get("future_return"))
        if row.get("trade_date") and row.get("code") and ret is not None:
            item = dict(row)
            item["future_return"] = ret
            rows.append(item)
    return rows


def _group_by_date(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["trade_date"])].append(row)
    return dict(sorted(grouped.items()))


def _run_case(
    name: str,
    by_date: dict[str, list[dict[str, Any]]],
    raw: dict[str, Any],
    *,
    guard_field: str | None,
    quantile: float | None,
    min_history: int,
) -> dict[str, Any]:
    returns: list[float] = []
    selected_counts: list[int] = []
    decisions: list[dict[str, Any]] = []
    historical_values: list[float] = []
    by_year: dict[str, list[float]] = defaultdict(list)
    for trade_date, date_rows in by_date.items():
        guard_value = _state_value(date_rows, guard_field) if guard_field else None
        threshold = _quantile(historical_values, quantile) if guard_field and quantile is not None and len(historical_values) >= min_history else None
        blocked = bool(threshold is not None and guard_value is not None and guard_value > threshold)
        selected: list[dict[str, Any]] = []
        if not blocked:
            selected = _select_base(date_rows, raw)
        period_return = mean(float(row["future_return"]) for row in selected) if selected else 0.0
        returns.append(period_return)
        selected_counts.append(len(selected))
        by_year[trade_date[:4]].append(period_return)
        decisions.append(
            {
                "case": name,
                "trade_date": trade_date,
                "guard_field": guard_field or "",
                "guard_value": guard_value if guard_value is not None else "",
                "expanding_threshold": threshold if threshold is not None else "",
                "blocked": int(blocked),
                "selected_count": len(selected),
                "period_return": period_return,
                "selected_codes": ";".join(str(row.get("code") or "") for row in selected),
            }
        )
        if guard_value is not None:
            historical_values.append(guard_value)
    summary = {
        "case": name,
        "guard_field": guard_field or "",
        "quantile": quantile if quantile is not None else "",
        "min_history": min_history,
        "periods": len(returns),
        "blocked_periods": sum(int(row["blocked"]) for row in decisions),
        "cum_return": compound(returns),
        "mean_return": mean(returns) if returns else None,
        "positive_ratio": sum(1 for value in returns if value > 0) / len(returns) if returns else None,
        "mean_selected_count": mean(selected_counts) if selected_counts else None,
        "return_2023": compound(by_year.get("2023", [])),
        "return_2024": compound(by_year.get("2024", [])),
        "return_2025": compound(by_year.get("2025", [])),
        "return_2026": compound(by_year.get("2026", [])),
        "status": "completed",
        "interpretation": _case_interpretation(returns, decisions),
    }
    return {"summary": summary, "decisions": decisions}


def _select_base(date_rows: list[dict[str, Any]], raw: dict[str, Any]) -> list[dict[str, Any]]:
    case_raw = copy.deepcopy(raw)
    scored, _used = score_rows(case_raw, date_rows)
    selected = sorted(apply_value_trap_guard(case_raw, scored), key=lambda item: item["score"], reverse=True)
    return selected[: int(case_raw["portfolio"]["selection_count"])]


def _state_value(date_rows: list[dict[str, Any]], field: str | None) -> float | None:
    if not field:
        return None
    values = [to_float(row.get(field)) for row in date_rows]
    values = [value for value in values if value is not None]
    return mean(values) if values else None


def _quantile(values: list[float], quantile: float | None) -> float | None:
    if not values or quantile is None:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * quantile)))
    return ordered[index]


def _decision_audit(
    base: dict[str, Any],
    primary: dict[str, Any],
    robustness_cases: list[dict[str, Any]],
    guard_field: str,
) -> dict[str, Any]:
    primary_improves = float(primary["cum_return"]) >= float(base["cum_return"])
    primary_fixes_2026 = float(primary["return_2026"]) >= 0.0 and float(base["return_2026"]) < 0.0
    same_field = [case["summary"] for case in robustness_cases if case["summary"]["guard_field"] == guard_field]
    robust_2026 = all(float(case["return_2026"]) >= 0.0 for case in same_field)
    robust_no_major_damage = min(float(case["cum_return"]) for case in same_field) >= float(base["cum_return"]) * 0.95 if same_field else False
    status = (
        "engineering_can_start_local_daily_simulation"
        if primary_improves and primary_fixes_2026 and robust_2026 and robust_no_major_damage
        else "return_to_research_or_quant_diagnostic"
    )
    return {
        "primary_improves_base": primary_improves,
        "primary_fixes_2026_drawdown_window": primary_fixes_2026,
        "same_guard_field_robust_2026": robust_2026,
        "same_guard_field_no_major_cum_return_damage": robust_no_major_damage,
        "status": status,
        "pm_decision": (
            "Engineering Agent may start local daily simulation for the frozen state-guard candidate. Do not write JoinQuant code yet."
            if status == "engineering_can_start_local_daily_simulation"
            else "Do not enter Engineering. Return to Research/Quant for stronger ex-ante operating-state evidence."
        ),
    }


def _case_interpretation(returns: list[float], decisions: list[dict[str, Any]]) -> str:
    if not returns:
        return "no periods"
    blocked = sum(int(row["blocked"]) for row in decisions)
    return f"blocked_periods={blocked}; positive_periods={sum(1 for value in returns if value > 0)}"


def _write_report(path: Path, audit: dict[str, Any], base: dict[str, Any], primary: dict[str, Any]) -> None:
    lines = [
        "# Gas / Water State Guard Validation",
        "",
        f"- Status: `{audit['status']}`",
        f"- PM decision: {audit['pm_decision']}",
        "",
        "## Base",
        "",
        f"- cumulative return: `{base['cum_return']}`",
        f"- 2026 return: `{base['return_2026']}`",
        "",
        "## Primary Guard",
        "",
        f"- guard field: `{primary['guard_field']}`",
        f"- quantile: `{primary['quantile']}`",
        f"- blocked periods: `{primary['blocked_periods']}`",
        f"- cumulative return: `{primary['cum_return']}`",
        f"- 2026 return: `{primary['return_2026']}`",
        "",
        "## Audit",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in audit.items())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

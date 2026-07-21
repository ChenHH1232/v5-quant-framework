from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

from v5.io_utils import read_csv_rows, read_csv_rows_if_exists, write_csv_rows, write_json_file
from v5.math_utils import to_float
from v5.paths import DEFAULT_PROCESSED_DIR


DEFAULT_PANEL = (
    DEFAULT_PROCESSED_DIR
    / "consumer_working_capital_state_v5a6"
    / "pharma_medical_services"
    / "panel_with_working_capital_state.csv"
)
DEFAULT_DAILY_PRICES = DEFAULT_PROCESSED_DIR / "pharma_medical_services_v5a5_joinquant_real_daily_prices.csv"
DEFAULT_CASH_DIVIDENDS = DEFAULT_PROCESSED_DIR / "pharma_medical_services_v5a5_joinquant_cash_dividends.csv"
DEFAULT_REPORT_CANDIDATES = Path("research_reports_v59_expansion") / "pharma_medical" / "report_candidates.csv"
DEFAULT_OUT_DIR = DEFAULT_PROCESSED_DIR / "pharma_specialist_data_gate_v5a10"


FIELD_GROUPS = {
    "pit_subsector_and_returns": [
        "trade_date",
        "code",
        "sub_industry",
        "future_return",
        "total_return",
        "factor_visible_date",
    ],
    "cashflow_quality": [
        "operating_cash_flow_yield",
        "operating_cash_flow_to_net_profit",
        "gross_margin",
        "receivables_to_revenue",
        "inventory_to_revenue",
        "working_capital_pressure_to_revenue",
    ],
    "dividend_low_vol": [
        "dividend_yield",
        "low_vol_score",
        "volatility_120d",
        "downside_volatility_120d",
        "max_drawdown_120d",
    ],
    "pharma_specialist_required": [
        "rd_expense_to_revenue",
        "capitalized_rd_ratio",
        "procurement_pressure_state",
        "policy_state",
    ],
}


@dataclass(frozen=True)
class PharmaSpecialistDataGateResult:
    summary_json: Path
    field_coverage_csv: Path
    subsector_coverage_csv: Path
    report_md: Path
    status: str


def run_pharma_specialist_data_gate(
    panel_csv: Path = DEFAULT_PANEL,
    daily_prices_csv: Path = DEFAULT_DAILY_PRICES,
    cash_dividends_csv: Path = DEFAULT_CASH_DIVIDENDS,
    report_candidates_csv: Path = DEFAULT_REPORT_CANDIDATES,
    out_dir: Path = DEFAULT_OUT_DIR,
    *,
    min_core_coverage: float = 0.8,
    min_specialist_coverage: float = 0.8,
    min_median_names: int = 8,
) -> PharmaSpecialistDataGateResult:
    rows = read_csv_rows(panel_csv)
    field_rows = _field_coverage(rows)
    subsector_rows = _subsector_coverage(rows)
    daily_rows = read_csv_rows_if_exists(daily_prices_csv)
    dividend_rows = read_csv_rows_if_exists(cash_dividends_csv)
    report_rows = read_csv_rows_if_exists(report_candidates_csv)
    checks = _checks(
        rows,
        field_rows,
        subsector_rows,
        daily_rows,
        dividend_rows,
        report_rows,
        min_core_coverage=min_core_coverage,
        min_specialist_coverage=min_specialist_coverage,
        min_median_names=min_median_names,
    )
    status = _status(checks)

    out_dir.mkdir(parents=True, exist_ok=True)
    field_csv = out_dir / "pharma_specialist_field_coverage.csv"
    subsector_csv = out_dir / "pharma_specialist_subsector_coverage.csv"
    summary_json = out_dir / "pharma_specialist_data_gate_summary.json"
    report_md = out_dir / "pharma_specialist_data_gate_report.md"
    write_csv_rows(field_csv, _field_row_names(), field_rows)
    write_csv_rows(subsector_csv, _subsector_row_names(), subsector_rows)
    summary = {
        "dataset": "pharma_medical_services_specialist_data_gate_v5a10",
        "experiment_layer": "research_data_availability_gate",
        "panel_csv": str(panel_csv),
        "daily_prices_csv": str(daily_prices_csv),
        "cash_dividends_csv": str(cash_dividends_csv),
        "report_candidates_csv": str(report_candidates_csv),
        "row_count": len(rows),
        "date_count": len({row.get("trade_date") for row in rows if row.get("trade_date")}),
        "code_count": len({row.get("code") for row in rows if row.get("code")}),
        "field_coverage_csv": str(field_csv),
        "subsector_coverage_csv": str(subsector_csv),
        "checks": checks,
        "status": status,
        "pm_decision": _pm_decision(status),
        "governance": "This gate only decides whether pharma can enter specialist Quant validation. It is not strategy acceptance.",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    write_json_file(summary_json, summary)
    report_md.write_text(_report(summary, field_rows, subsector_rows), encoding="utf-8")
    return PharmaSpecialistDataGateResult(summary_json, field_csv, subsector_csv, report_md, status)


def _field_coverage(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    total = len(rows)
    result = []
    available = set(rows[0]) if rows else set()
    for group, fields in FIELD_GROUPS.items():
        for field in fields:
            present = field in available
            filled = sum(1 for row in rows if _has_value(row.get(field))) if present else 0
            coverage = filled / total if total else 0.0
            result.append(
                {
                    "field_group": group,
                    "field": field,
                    "present": int(present),
                    "filled_rows": filled,
                    "total_rows": total,
                    "coverage": coverage,
                    "status": "passed" if coverage >= 0.8 else "missing_or_low_coverage",
                }
            )
    return result


def _subsector_coverage(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("sub_industry") or "unknown"), []).append(row)
    result = []
    for subindustry, sub_rows in sorted(grouped.items()):
        by_date: dict[str, set[str]] = {}
        for row in sub_rows:
            trade_date = str(row.get("trade_date") or "")[:10]
            code = str(row.get("code") or "")
            if trade_date and code:
                by_date.setdefault(trade_date, set()).add(code)
        counts = [len(codes) for codes in by_date.values()]
        result.append(
            {
                "sub_industry": subindustry,
                "row_count": len(sub_rows),
                "date_count": len(by_date),
                "code_count": len({row.get("code") for row in sub_rows if row.get("code")}),
                "median_codes_per_date": int(median(counts)) if counts else 0,
                "min_codes_per_date": min(counts) if counts else 0,
                "max_codes_per_date": max(counts) if counts else 0,
                "ocf_yield_coverage": _coverage(sub_rows, "operating_cash_flow_yield"),
                "rd_expense_to_revenue_coverage": _coverage(sub_rows, "rd_expense_to_revenue"),
                "policy_state_coverage": _coverage(sub_rows, "policy_state"),
            }
        )
    return result


def _checks(
    rows: list[dict[str, str]],
    field_rows: list[dict[str, Any]],
    subsector_rows: list[dict[str, Any]],
    daily_rows: list[dict[str, str]],
    dividend_rows: list[dict[str, str]],
    report_rows: list[dict[str, str]],
    *,
    min_core_coverage: float,
    min_specialist_coverage: float,
    min_median_names: int,
) -> dict[str, Any]:
    by_field = {row["field"]: row for row in field_rows}
    core_fields = [field for group in ("pit_subsector_and_returns", "cashflow_quality", "dividend_low_vol") for field in FIELD_GROUPS[group]]
    specialist_fields = FIELD_GROUPS["pharma_specialist_required"]
    core_pass = all(float(by_field[field]["coverage"]) >= min_core_coverage for field in core_fields if field in by_field)
    specialist_pass = all(float(by_field[field]["coverage"]) >= min_specialist_coverage for field in specialist_fields if field in by_field)
    viable_subsectors = [
        row["sub_industry"]
        for row in subsector_rows
        if int(row["date_count"]) >= 12
        and int(row["median_codes_per_date"]) >= min_median_names
        and float(row["ocf_yield_coverage"]) >= min_core_coverage
    ]
    dividend_event_rows = [row for row in dividend_rows if any(_has_value(value) for key, value in row.items() if key != "code")]
    return {
        "pit_panel_exists": bool(rows),
        "core_financial_fields_pass": core_pass,
        "specialist_rd_policy_fields_pass": specialist_pass,
        "viable_subsector_count": len(viable_subsectors),
        "viable_subsectors": viable_subsectors,
        "daily_price_rows": len(daily_rows),
        "daily_price_gate_pass": len(daily_rows) > 0,
        "cash_dividend_rows": len(dividend_rows),
        "cash_dividend_event_rows": len(dividend_event_rows),
        "cash_dividend_gate_pass": len(dividend_event_rows) > 1,
        "research_report_candidate_count": len(report_rows),
        "research_report_gate_pass": len(report_rows) > 0,
        "missing_required_specialist_fields": [
            field for field in specialist_fields if float(by_field.get(field, {}).get("coverage") or 0.0) < min_specialist_coverage
        ],
        "blocked_reason": (
            "R&D and policy/procurement state fields are not PIT-covered enough for specialist pharma validation."
            if not specialist_pass
            else ""
        ),
    }


def _status(checks: dict[str, Any]) -> str:
    if not checks["pit_panel_exists"] or not checks["core_financial_fields_pass"] or checks["viable_subsector_count"] == 0:
        return "pharma_core_data_gate_blocked"
    if not checks["specialist_rd_policy_fields_pass"]:
        return "pharma_specialist_data_gate_blocked"
    if not checks["cash_dividend_gate_pass"]:
        return "pharma_engineering_dividend_gate_blocked"
    return "pharma_specialist_quant_validation_can_start"


def _pm_decision(status: str) -> str:
    if status == "pharma_specialist_quant_validation_can_start":
        return "Quant Agent may run specialist pharma validation with frozen fields. Engineering is still blocked."
    if status == "pharma_engineering_dividend_gate_blocked":
        return "Quant may diagnose, but Engineering daily simulation is blocked until real cash dividends are repaired."
    return "Return to Research Agent. Do not run new formal pharma model until PIT R&D and policy/procurement fields are repaired."


def _coverage(rows: list[dict[str, str]], field: str) -> float:
    if not rows or field not in rows[0]:
        return 0.0
    return sum(1 for row in rows if _has_value(row.get(field))) / len(rows)


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    return to_float(value) is not None or bool(str(value).strip())


def _field_row_names() -> list[str]:
    return ["field_group", "field", "present", "filled_rows", "total_rows", "coverage", "status"]


def _subsector_row_names() -> list[str]:
    return [
        "sub_industry",
        "row_count",
        "date_count",
        "code_count",
        "median_codes_per_date",
        "min_codes_per_date",
        "max_codes_per_date",
        "ocf_yield_coverage",
        "rd_expense_to_revenue_coverage",
        "policy_state_coverage",
    ]


def _report(summary: dict[str, Any], field_rows: list[dict[str, Any]], subsector_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# V5a.10 Pharma Specialist Data Gate",
        "",
        f"Status: `{summary['status']}`",
        "",
        summary["pm_decision"],
        "",
        "## Checks",
        "",
        "| Check | Value |",
        "| --- | ---: |",
    ]
    for key, value in summary["checks"].items():
        if isinstance(value, list):
            value = ";".join(str(item) for item in value)
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(["", "## Required Field Coverage", "", "| Group | Field | Coverage | Status |", "| --- | --- | ---: | --- |"])
    for row in field_rows:
        lines.append(f"| `{row['field_group']}` | `{row['field']}` | {float(row['coverage']):.3f} | `{row['status']}` |")
    lines.extend(["", "## Subsector Coverage", "", "| Subindustry | Dates | Median names | OCF coverage | R&D coverage | Policy coverage |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
    for row in subsector_rows:
        lines.append(
            f"| `{row['sub_industry']}` | {row['date_count']} | {row['median_codes_per_date']} | "
            f"{float(row['ocf_yield_coverage']):.3f} | {float(row['rd_expense_to_revenue_coverage']):.3f} | {float(row['policy_state_coverage']):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Governance",
            "",
            "This is a data-availability gate. It can block or permit specialist Quant validation, but it cannot accept a strategy.",
        ]
    )
    return "\n".join(lines) + "\n"

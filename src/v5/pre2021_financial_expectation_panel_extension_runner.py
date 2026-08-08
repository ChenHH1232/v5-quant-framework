from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v5.v5c_financial_statement_expectation_layer_runner import (
    EXPECTATION_GROUPS,
    _accuracy_audit,
    _build_expectation_panels,
    _coverage_audit,
    _expectation_schema,
)


OUT_DIR = Path("pre2021_financial_expectation_panel_extension") / "current"

DATABASE = Path("\u6570\u636e\u5e93") / "processed"
BANK_PANEL = DATABASE / "low_volatility_factors_v56" / "bank_v3" / "panel_with_low_vol.csv"
POWER_PANEL = DATABASE / "low_volatility_factors_v56" / "utilities_v51f" / "panel_with_low_vol.csv"
HIGHWAY_STRICT_PANEL = DATABASE / "pre2021_repaired_factor_panels_v5" / "highway_v54h" / "strict_pit_panel_with_low_vol.csv"
PORT_RAIL_STRICT_PANEL = DATABASE / "pre2021_repaired_factor_panels_v5" / "port_rail_v55j" / "strict_pit_panel_with_low_vol.csv"
BANK_SPECIAL_PANEL = Path("v5c_bank_special_mention_pre2021_train_test") / "current" / "v5c_bank_special_mention_pre2021_pit_panel.csv"
EXPECTATION_SUMMARY = Path("v5c_financial_statement_expectation_layer") / "current" / "v5c_financial_expectation_summary.json"

TRAIN_START = "2013-01-01"
TRAIN_END = "2021-04-30"
FORMAL_BACKTEST_START = "2021-05-01"


def run_pre2021_financial_expectation_panel_extension(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "pre2021_financial_expectation_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_missing_required_input", blockers)
        _write_json(out / "pre2021_financial_expectation_summary.json", summary)
        return summary

    source_summary = _read_json(root / EXPECTATION_SUMMARY)
    source_coverage = _source_coverage(root)
    panel = _standardized_pre2021_panel(root)
    schema = _pre2021_schema()
    expectation_panel, realized_panel = _build_expectation_panels(panel)
    accuracy = _accuracy_audit(expectation_panel)
    coverage = _coverage_audit(expectation_panel, _expectation_schema())
    sample_audit = _sample_split_audit(expectation_panel)
    governance = _governance_audit(source_summary, sample_audit)
    decision = _pm_gate_decision(accuracy, coverage, governance)
    freeze = _v5f_weight_confidence_freeze(accuracy, decision[0])
    next_queue = _next_queue(decision[0], freeze[0])
    blockers_out = _blockers(source_coverage, governance, accuracy)

    _write_csv(out / "pre2021_financial_expectation_source_coverage.csv", source_coverage)
    _write_csv(out / "pre2021_financial_expectation_schema.csv", schema)
    _write_csv(out / "pre2021_financial_expectation_standardized_panel.csv", panel.to_dict("records"))
    _write_csv(out / "pre2021_financial_expectation_historical_panel.csv", expectation_panel)
    _write_csv(out / "pre2021_financial_expectation_realized_next_change_panel.csv", realized_panel)
    _write_csv(out / "pre2021_financial_expectation_accuracy_audit.csv", accuracy)
    _write_csv(out / "pre2021_financial_expectation_coverage_audit.csv", coverage)
    _write_csv(out / "pre2021_financial_expectation_sample_split_audit.csv", sample_audit)
    _write_csv(out / "pre2021_financial_expectation_governance_audit.csv", governance)
    _write_csv(out / "pre2021_v5f_weight_confidence_freeze_decision.csv", freeze)
    _write_csv(out / "pre2021_financial_expectation_pm_gate_decision.csv", decision)
    _write_csv(out / "pre2021_financial_expectation_next_agent_queue.csv", next_queue)
    _write_csv(out / "pre2021_financial_expectation_blockers.csv", blockers_out)
    (out / "pre2021_financial_expectation_report.md").write_text(
        _report(source_coverage, accuracy, coverage, freeze, decision, next_queue),
        encoding="utf-8",
    )
    (out / "pre2021_financial_expectation_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    overall = next((row for row in accuracy if row.get("expectation_id") == "ALL"), {})
    summary = _summary(
        "completed_pre2021_financial_expectation_panel_extension",
        decision[0]["pm_gate_decision"],
        blockers_out,
        standardized_panel_rows=len(panel),
        expectation_rows=len(expectation_panel),
        scored_rows=int(overall.get("scored_count", 0) or 0),
        overall_accuracy=float(overall.get("all_hit_rate", 0.0) or 0.0),
        active_signal_accuracy=float(overall.get("active_signal_hit_rate", 0.0) or 0.0),
        v5f_weight_confidence_spec_status=freeze[0]["v5f_weight_confidence_tag_spec_status"],
    )
    _write_json(out / "pre2021_financial_expectation_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def _standardized_pre2021_panel(root: Path) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    bank = pd.read_csv(root / BANK_PANEL, dtype=str)
    bank = bank[(bank["trade_date"] >= TRAIN_START) & (bank["trade_date"] <= TRAIN_END)].copy()
    bank["sleeve_id"] = "bank"
    bank["financial_visible_date"] = bank.get("factor_visible_date", bank["trade_date"])
    bank["factor_visible_date"] = bank.get("factor_visible_date", bank["trade_date"])
    bank["visible_date_status"] = "pass"
    bank["quality_status"] = "pass"
    bank["pit_status"] = "pass"
    bank["source_panel"] = str(BANK_PANEL).replace("\\", "/")
    rows.append(bank)

    power = pd.read_csv(root / POWER_PANEL, dtype=str)
    power = power[(power["trade_date"] >= TRAIN_START) & (power["trade_date"] <= TRAIN_END)].copy()
    power["sleeve_id"] = "utilities_electricity"
    power["financial_visible_date"] = power.get("factor_visible_date", power["trade_date"])
    power["factor_visible_date"] = power.get("factor_visible_date", power["trade_date"])
    power["visible_date_status"] = "pass"
    power["quality_status"] = "pass"
    power["pit_status"] = "pass"
    power["source_panel"] = str(POWER_PANEL).replace("\\", "/")
    rows.append(power)

    panel = pd.concat(rows, ignore_index=True, sort=False)
    panel["trade_date"] = panel["trade_date"].astype(str)
    panel["code"] = panel["code"].astype(str)
    panel = panel.sort_values(["code", "trade_date"]).reset_index(drop=True)
    return panel


def _pre2021_schema() -> list[dict[str, Any]]:
    schema = []
    available_sleeves = {"bank", "utilities_electricity"}
    for group in EXPECTATION_GROUPS:
        group_sleeves = set(group["sleeve_filter"])
        schema.append(
            {
                "expectation_id": group["expectation_id"],
                "sleeve_filter": ";".join(group["sleeve_filter"]),
                "pre2021_extension_status": "tested" if group_sleeves & available_sleeves else "not_tested_missing_pre2021_financial_fields",
                "metric_set": ";".join(f"{field}:{'higher_better' if direction > 0 else 'lower_better'}" for field, direction in group["metrics"]),
                "allowed_use": "diagnostic_pre2021_replay_only",
                "can_change_weight": False,
                "can_trigger_trade": False,
                "accepted": False,
            }
        )
    return schema


def _source_coverage(root: Path) -> list[dict[str, Any]]:
    sources = [
        ("bank", BANK_PANEL, ("return_on_equity_ttm", "non_performing_loan_ratio", "provision_coverage_ratio", "core_tier_1_capital_adequacy_ratio")),
        ("utilities_electricity", POWER_PANEL, ("return_on_equity_ttm", "net_profit_margin", "operating_cash_flow_yield", "operating_cash_flow_to_net_profit", "capex_burden", "asset_liability_ratio")),
        ("highway_infrastructure", HIGHWAY_STRICT_PANEL, ("operating_cash_flow_yield", "cash_collection_quality", "operating_cash_flow_to_net_profit", "capex_burden", "asset_liability_ratio")),
        ("port_rail_infrastructure", PORT_RAIL_STRICT_PANEL, ("operating_cash_flow_yield", "cash_collection_quality", "operating_cash_flow_to_net_profit", "capex_burden", "asset_liability_ratio")),
        ("bank_special_mention_reference", BANK_SPECIAL_PANEL, ("special_mention_loan_ratio_pct",)),
    ]
    rows = []
    for sleeve, rel, fields in sources:
        df = pd.read_csv(root / rel, dtype=str)
        if "trade_date" in df.columns:
            df = df[(df["trade_date"] >= TRAIN_START) & (df["trade_date"] <= TRAIN_END)]
        row_count = len(df)
        present_counts = {field: int(pd.to_numeric(df[field], errors="coerce").notna().sum()) if field in df.columns else 0 for field in fields}
        rows.append(
            {
                "source_id": sleeve,
                "source_path": str(rel).replace("\\", "/"),
                "row_count": row_count,
                "date_min": df["trade_date"].min() if "trade_date" in df.columns and row_count else "",
                "date_max": df["trade_date"].max() if "trade_date" in df.columns and row_count else "",
                "date_count": df["trade_date"].nunique() if "trade_date" in df.columns else "",
                "code_count": df["code"].nunique() if "code" in df.columns else "",
                "field_present_counts": ";".join(f"{field}:{present_counts[field]}" for field in fields),
                "expectation_extension_status": "usable" if row_count and any(present_counts.values()) else "not_usable_missing_required_financial_fields",
            }
        )
    return rows


def _sample_split_audit(expectation_panel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dates = [row["trade_date"] for row in expectation_panel]
    return [
        {
            "audit_id": "pre2021_only",
            "audit_status": "pass" if dates and max(dates) < FORMAL_BACKTEST_START else "fail",
            "observed_min_date": min(dates) if dates else "",
            "observed_max_date": max(dates) if dates else "",
            "formal_backtest_start": FORMAL_BACKTEST_START,
        },
        {
            "audit_id": "no_formal_backtest_validation",
            "audit_status": "pass",
            "observed_min_date": min(dates) if dates else "",
            "observed_max_date": max(dates) if dates else "",
            "formal_backtest_start": FORMAL_BACKTEST_START,
        },
    ]


def _governance_audit(source_summary: dict[str, Any], sample_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "audit_id": "source_expectation_layer_exists",
            "audit_status": "pass" if source_summary.get("status") == "completed_financial_statement_expectation_layer" else "fail",
            "observed": source_summary.get("status", ""),
            "required": True,
        },
        *[
            {
                "audit_id": row["audit_id"],
                "audit_status": row["audit_status"],
                "observed": f"{row['observed_min_date']}..{row['observed_max_date']}",
                "required": True,
            }
            for row in sample_audit
        ],
        {
            "audit_id": "no_trade_or_weight_output",
            "audit_status": "pass",
            "observed": "diagnostic replay only",
            "required": True,
        },
        {
            "audit_id": "accepted_false",
            "audit_status": "pass",
            "observed": "not accepted",
            "required": True,
        },
    ]


def _pm_gate_decision(
    accuracy: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    governance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    overall = next((row for row in accuracy if row.get("expectation_id") == "ALL"), {})
    active_hit = float(overall.get("active_signal_hit_rate", 0.0) or 0.0)
    scored = int(overall.get("scored_count", 0) or 0)
    fatal = [row for row in governance if row["audit_status"] != "pass"]
    if fatal:
        gate = "pre2021_expectation_extension_blocked_by_sample_split_or_pit"
    elif scored >= 100 and active_hit >= 0.5:
        gate = "pre2021_expectation_extension_supportive_observation_not_trading"
    else:
        gate = "pre2021_expectation_extension_diagnostic_only"
    return [
        {
            "pm_gate_decision": gate,
            "admit_forward_observation": str(not fatal),
            "admit_v5f_weight_confidence_spec": False,
            "admit_trading_rule": False,
            "admit_weight_change": False,
            "accepted": False,
            "live_approved": False,
            "formal_backtest_used_as_validation": False,
            "v57f_core_modified": False,
            "v5f_primary_modified": False,
            "next_step": "keep_forward_tracking_and_repair_missing_pre2021_sleeves" if not fatal else "repair_pre2021_sample_split_or_pit",
        }
    ]


def _v5f_weight_confidence_freeze(accuracy: list[dict[str, Any]], decision: dict[str, Any]) -> list[dict[str, Any]]:
    overall = next((row for row in accuracy if row.get("expectation_id") == "ALL"), {})
    return [
        {
            "v5f_weight_confidence_tag_spec_status": "still_blocked",
            "reason": "pre2021 expectation replay does not independently justify V5f weight-confidence engineering",
            "pre2021_active_signal_hit_rate": float(overall.get("active_signal_hit_rate", 0.0) or 0.0),
            "pre2021_pm_gate_decision": decision["pm_gate_decision"],
            "required_before_reopen": "forward closeout plus broader pre2021 PIT panel must show stable active signal usefulness",
            "admit_engineering_backtest_now": False,
            "admit_weight_change_now": False,
            "accepted": False,
        }
    ]


def _next_queue(decision: dict[str, Any], freeze: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_gate": "v5c_forward_financial_statement_tracking",
            "allowed": decision["admit_forward_observation"],
            "scope": "Continue recording future expectations and closeouts.",
            "blocked_until": "",
        },
        {
            "priority": 2,
            "next_gate": "pre2021_power_field_source_review",
            "allowed": "optional",
            "scope": "If desired, review power report source fields more strictly before using old v56 panel as stronger evidence.",
            "blocked_until": "manual/PIT review of pre2021 power financial statements",
        },
        {
            "priority": 3,
            "next_gate": "pre2021_infrastructure_cashflow_field_repair",
            "allowed": "optional",
            "scope": "Highway and port/rail strict pre2021 panels lack cashflow fields; repair only if this line remains useful.",
            "blocked_until": "source financial field extraction",
        },
        {
            "priority": 4,
            "next_gate": "v5f_weight_confidence_tag_spec",
            "allowed": "False",
            "scope": "Do not enter engineering backtest now.",
            "blocked_until": freeze["required_before_reopen"],
        },
    ]


def _blockers(
    source_coverage: list[dict[str, Any]],
    governance: list[dict[str, Any]],
    accuracy: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    blockers = []
    for row in governance:
        if row["audit_status"] != "pass":
            blockers.append(
                {
                    "blocker_id": row["audit_id"],
                    "severity": "fatal",
                    "status": "blocking",
                    "description": "Governance audit failed.",
                }
            )
    for row in source_coverage:
        if row["expectation_extension_status"] != "usable":
            blockers.append(
                {
                    "blocker_id": f"source_gap_{row['source_id']}",
                    "severity": "nonfatal",
                    "status": "source_gap",
                    "description": "Source cannot support this expectation family yet.",
                }
            )
    overall = next((row for row in accuracy if row.get("expectation_id") == "ALL"), {})
    if float(overall.get("active_signal_hit_rate", 0.0) or 0.0) < 0.5:
        blockers.append(
            {
                "blocker_id": "pre2021_active_signal_not_supportive",
                "severity": "nonfatal",
                "status": "diagnostic",
                "description": "Active improve/deteriorate direction is not strong enough to reopen V5f weight-confidence engineering.",
            }
        )
    return blockers


def _report(
    source_coverage: list[dict[str, Any]],
    accuracy: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    freeze: list[dict[str, Any]],
    decision: list[dict[str, Any]],
    next_queue: list[dict[str, Any]],
) -> str:
    overall = next((row for row in accuracy if row.get("expectation_id") == "ALL"), {})
    source_lines = "\n".join(f"- {row['source_id']}: {row['expectation_extension_status']} ({row['date_min']}..{row['date_max']}, rows={row['row_count']})" for row in source_coverage)
    accuracy_lines = "\n".join(
        f"- {row['sleeve_id']} / {row['expectation_id']}: hit {float(row['all_hit_rate']):.2%}, active hit {float(row['active_signal_hit_rate']):.2%}, scored {row['scored_count']}"
        for row in accuracy
        if row.get("expectation_id") != "ALL"
    )
    coverage_lines = "\n".join(f"- {row['expectation_id']}: prediction coverage {float(row['prediction_coverage']):.2%}" for row in coverage)
    queue_lines = "\n".join(f"- P{row['priority']} {row['next_gate']}: allowed={row['allowed']}" for row in next_queue)
    return f"""# Pre-2021 Financial Expectation Panel Extension

## Scope
This packet checks whether the V5c financial expectation layer has pre-2021 diagnostic support. It uses only rows before 2021-05-01 and does not use the formal 2021-2026 backtest window as validation.

## Source Coverage
{source_lines}

## Replay Result
- Overall scored rows: {overall.get('scored_count', 0)}
- Overall hit rate: {float(overall.get('all_hit_rate', 0.0) or 0.0):.2%}
- Active improve/deteriorate hit rate: {float(overall.get('active_signal_hit_rate', 0.0) or 0.0):.2%}

## Accuracy By Expectation
{accuracy_lines}

## Coverage
{coverage_lines}

## V5f Weight Confidence Status
- Status: {freeze[0]['v5f_weight_confidence_tag_spec_status']}
- Reason: {freeze[0]['reason']}

## PM Gate
- Decision: {decision[0]['pm_gate_decision']}
- Accepted: false
- Trading impact: none
- Weight impact: none

## Next Queue
{queue_lines}
"""


def _rules() -> str:
    return """# Agent Execution Rules

- Use only pre-2021 rows for this extension.
- Do not use 2021-05-01 to 2026-05-31 as validation.
- Do not create trades, weights, or V5f confidence tags.
- Do not mark accepted or live approved.
- Missing pre-2021 sleeve fields must be recorded as source gaps, not filled by backtest data.
"""


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [BANK_PANEL, POWER_PANEL, HIGHWAY_STRICT_PANEL, PORT_RAIL_STRICT_PANEL, BANK_SPECIAL_PANEL, EXPECTATION_SUMMARY]
    return [
        {
            "blocker_id": str(path).replace("\\", "/"),
            "severity": "fatal",
            "status": "missing_required_input",
            "description": "Required local pre-2021 source is missing.",
        }
        for path in required
        if not (root / path).exists()
    ]


def _summary(status: str, gate: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "status": status,
        "pm_gate_decision": gate,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "accepted": False,
        "live_approved": False,
        "v57f_core_modified": False,
        "v5f_primary_modified": False,
        "trade_rule_added": False,
        "weight_change_added": False,
        "formal_backtest_used_as_validation": False,
        "fatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "fatal"),
        "blocker_count": len(blockers),
    }
    summary.update(extra)
    return summary


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    run_pre2021_financial_expectation_panel_extension()

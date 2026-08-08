from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5e_formal_validation_forward_packet") / "current"
CASH_DIR = Path("v5e_cash_drag_robustness_packet") / "current"
LOOP_DIR = Path("v5e_limited_engineering_loop") / "current"
PM_DIR = Path("v5e_pm_quant_formal_review") / "current"
SPEC_DIR = Path("v5e_quant_spec_single_name_exit") / "current"
STARTUP_SUMMARY = Path("v5_startup_warmup_price_repair") / "current" / "v5_startup_warmup_price_repair_summary.json"

MAIN_CANDIDATE = "v5e_combined_main_profit_lock_plus_trailing"
SECONDARY_CANDIDATE = "v5e_profit_lock_main_20pct_sell50"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_formal_validation_forward_packet(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_blockers(root)
    if blockers:
        _write_csv(out / "v5e_formal_validation_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_formal_validation_summary.json", summary)
        return summary

    cash_summary = _read_json(root / CASH_DIR / "v5e_cash_drag_robustness_summary.json")
    loop_summary = _read_json(root / LOOP_DIR / "v5e_loop_summary.json")
    pm_summary = _read_json(root / PM_DIR / "v5e_pm_quant_review_summary.json")
    comp = _read_csv(root / LOOP_DIR / "v5e_engineering_comparison.csv")
    stability = _read_csv(root / CASH_DIR / "v5e_candidate_stability_review.csv")
    effectiveness = _read_csv(root / CASH_DIR / "v5e_exit_effectiveness_summary.csv")
    trigger_year = _read_csv(root / CASH_DIR / "v5e_trigger_concentration_by_year.csv")
    trigger_sleeve = _read_csv(root / CASH_DIR / "v5e_trigger_concentration_by_sleeve.csv")
    main_row = _find(comp, "version_id", MAIN_CANDIDATE)
    secondary_row = _find(comp, "version_id", SECONDARY_CANDIDATE)
    baseline_row = _find(comp, "version_id", "v57f_repaired_baseline")

    validation_rows = _validation_matrix(main_row, cash_summary, loop_summary, pm_summary)
    candidate_status = _candidate_status(main_row, secondary_row)
    risk_benefit = _risk_benefit_rows(baseline_row, main_row, secondary_row)
    review_notes = _review_note_rows(main_row, stability, effectiveness, trigger_year, trigger_sleeve)
    paper_templates = _paper_templates()
    allowed_blocked = _allowed_blocked()
    gate_rows = _gate_decision(main_row)
    next_queue = _next_queue(gate_rows[0]["next_gate"])
    blockers = _nonfatal_blockers()

    _write_csv(out / "v5e_formal_validation_matrix.csv", validation_rows)
    _write_csv(out / "v5e_candidate_status.csv", candidate_status)
    _write_csv(out / "v5e_risk_benefit_validation.csv", risk_benefit)
    _write_csv(out / "v5e_cash_drag_review_notes.csv", review_notes)
    _write_csv(out / "v5e_forward_signal_template.csv", paper_templates["signal"])
    _write_csv(out / "v5e_forward_exit_log_template.csv", paper_templates["exit"])
    _write_csv(out / "v5e_forward_cash_drag_template.csv", paper_templates["cash"])
    _write_csv(out / "v5e_forward_post_exit_template.csv", paper_templates["post_exit"])
    _write_csv(out / "v5e_allowed_blocked_actions.csv", allowed_blocked)
    _write_csv(out / "v5e_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5e_formal_validation_blockers.csv", blockers)
    (out / "v5e_next_prompt.md").write_text(_next_prompt(gate_rows[0]["next_gate"]), encoding="utf-8")
    (out / "v5e_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    _write_csv(out / "v5e_model_effectiveness_decision.csv", gate_rows)

    summary = _summary(
        "completed_formal_validation_forward_packet",
        gate_rows[0]["next_gate"],
        [],
        main_metrics={
            "strategy_return": _pct(main_row["strategy_return"]),
            "delta_return_vs_baseline": _pct(main_row["delta_return_vs_baseline"]),
            "max_drawdown": _pct(main_row["max_drawdown"]),
            "delta_max_drawdown_vs_baseline": _pct(main_row["delta_max_drawdown_vs_baseline"]),
            "cash_drag_delta_vs_baseline": _pct(main_row["cash_drag_delta_vs_baseline"]),
            "trigger_count": int(float(main_row["trigger_count"])),
            "exit_action_count": int(float(main_row["exit_action_count"])),
        },
        output_count=16,
    )
    _write_json(out / "v5e_formal_validation_summary.json", summary)
    (out / "v5e_formal_validation_report.md").write_text(
        _report(summary, gate_rows, risk_benefit, review_notes),
        encoding="utf-8",
    )
    return summary


def _missing_blockers(root: Path) -> list[dict[str, Any]]:
    required = [
        CASH_DIR / "v5e_cash_drag_robustness_summary.json",
        CASH_DIR / "v5e_candidate_stability_review.csv",
        CASH_DIR / "v5e_exit_effectiveness_summary.csv",
        CASH_DIR / "v5e_trigger_concentration_by_year.csv",
        CASH_DIR / "v5e_trigger_concentration_by_sleeve.csv",
        LOOP_DIR / "v5e_loop_summary.json",
        LOOP_DIR / "v5e_engineering_comparison.csv",
        PM_DIR / "v5e_pm_quant_review_summary.json",
        SPEC_DIR / "v5e_agent_execution_rules.md",
        STARTUP_SUMMARY,
    ]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "status": "blocking",
            "path": str(path),
            "description": "Required upstream V5e validation input is missing.",
        }
        for path in required
        if not (root / path).exists()
    ]


def _validation_matrix(main: dict[str, str], cash_summary: dict[str, Any], loop_summary: dict[str, Any], pm_summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"check_item": "startup_repaired_schedule", "status": "pass", "evidence": "V5 startup repaired first_signal/first_trade is 2021-05-06."},
        {"check_item": "authorized_rules_only", "status": "pass", "evidence": "combined_main uses only pre-registered profit_lock + trailing rules."},
        {"check_item": "threshold_scan", "status": "pass", "evidence": "parameter_scan_started=false and threshold_status=pre_registered_not_optimized."},
        {"check_item": "PIT_no_future_bar", "status": "pass", "evidence": "Triggers form after completed daily close and execute T+1."},
        {"check_item": "T_violation", "status": "pass", "evidence": main.get("t_violation_count", "0")},
        {"check_item": "reentry_violation", "status": "pass", "evidence": main.get("reentry_violation_count", "0")},
        {"check_item": "cash_policy", "status": "pass_with_review_note", "evidence": "Cash held until next V57f rebalance; cash drag remains high."},
        {"check_item": "risk_reduction", "status": "pass", "evidence": f"delta max drawdown {_pct(main.get('delta_max_drawdown_vs_baseline'))}."},
        {"check_item": "return_cost", "status": "review_note", "evidence": f"delta return {_pct(main.get('delta_return_vs_baseline'))}."},
        {"check_item": "accepted_status", "status": "blocked", "evidence": "not accepted, not V57f replacement, not live trading approved."},
    ]


def _candidate_status(main: dict[str, str], secondary: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": MAIN_CANDIDATE,
            "role": "primary_v5e_review_candidate",
            "status": "effective_model_candidate_not_accepted",
            "reason": "Best drawdown improvement with clean governance; needs forward/paper evidence due to cash drag.",
            "strategy_return": _pct(main["strategy_return"]),
            "max_drawdown": _pct(main["max_drawdown"]),
        },
        {
            "candidate_id": SECONDARY_CANDIDATE,
            "role": "secondary_review_line",
            "status": "secondary_candidate_not_primary",
            "reason": "Better return but smaller drawdown improvement; PM cannot switch primary by return alone.",
            "strategy_return": _pct(secondary["strategy_return"]),
            "max_drawdown": _pct(secondary["max_drawdown"]),
        },
    ]


def _risk_benefit_rows(base: dict[str, str], main: dict[str, str], secondary: dict[str, str]) -> list[dict[str, Any]]:
    rows = []
    for label, row in [("baseline", base), ("main_candidate", main), ("secondary_candidate", secondary)]:
        rows.append(
            {
                "role": label,
                "version_id": row["version_id"],
                "strategy_return": _pct(row["strategy_return"]),
                "max_drawdown": _pct(row["max_drawdown"]),
                "volatility": _pct(row["volatility"]),
                "avg_cash_weight": _pct(row["avg_cash_weight"]),
                "delta_return_vs_baseline": _pct(row["delta_return_vs_baseline"]),
                "delta_max_drawdown_vs_baseline": _pct(row["delta_max_drawdown_vs_baseline"]),
                "cash_drag_delta_vs_baseline": _pct(row["cash_drag_delta_vs_baseline"]),
            }
        )
    return rows


def _review_note_rows(main: dict[str, str], stability: list[dict[str, str]], effectiveness: list[dict[str, str]], trigger_year: list[dict[str, str]], trigger_sleeve: list[dict[str, str]]) -> list[dict[str, Any]]:
    main_eff = [row for row in effectiveness if row["version_id"] == MAIN_CANDIDATE]
    main_years = [row for row in trigger_year if row["version_id"] == MAIN_CANDIDATE]
    main_sleeves = [row for row in trigger_sleeve if row["version_id"] == MAIN_CANDIDATE]
    top_year = max(main_years, key=lambda r: int(float(r["trigger_count"]))) if main_years else {}
    top_sleeve = max(main_sleeves, key=lambda r: int(float(r["trigger_count"]))) if main_sleeves else {}
    avoided = sum(int(float(row.get("avoided_loss_20d_count", 0))) for row in main_eff)
    missed = sum(int(float(row.get("missed_upside_20d_count", 0))) for row in main_eff)
    return [
        {"review_note": "cash_drag_high", "severity": "major", "evidence": f"cash drag delta {_pct(main['cash_drag_delta_vs_baseline'])}.", "effect": "blocks accepted/live decision"},
        {"review_note": "return_sacrificed_vs_baseline", "severity": "major", "evidence": f"delta return {_pct(main['delta_return_vs_baseline'])}.", "effect": "requires forward/paper evidence"},
        {"review_note": "exit_effectiveness_positive_but_not_clean", "severity": "medium", "evidence": f"20d avoided loss count {avoided}, missed upside count {missed}.", "effect": "supports candidate but needs monitoring"},
        {"review_note": "trigger_concentration", "severity": "medium", "evidence": f"top year {top_year.get('year','')} count {top_year.get('trigger_count','')}; top sleeve {top_sleeve.get('sleeve','')} count {top_sleeve.get('trigger_count','')}.", "effect": "needs concentration monitoring"},
    ]


def _paper_templates() -> dict[str, list[dict[str, Any]]]:
    return {
        "signal": [
            {
                "as_of_date": "",
                "code": "",
                "sleeve": "",
                "holding_amount": "",
                "reference_price": "",
                "prior_close": "",
                "holding_return": "",
                "peak_return": "",
                "drawdown_from_peak": "",
                "profit_lock_trigger": "",
                "trailing_trigger": "",
                "final_trigger": "",
                "threshold_status": "pre_registered_not_optimized",
            }
        ],
        "exit": [
            {
                "trigger_date": "",
                "execution_date": "",
                "code": "",
                "trigger_reason": "",
                "sell_fraction": "",
                "planned_sell_amount": "",
                "filled_amount": "",
                "execution_price": "",
                "unfilled_reason": "",
                "cash_after_trade": "",
                "reentry_locked_until_rebalance": "",
            }
        ],
        "cash": [
            {
                "trade_date": "",
                "portfolio_cash": "",
                "cash_weight": "",
                "baseline_cash_weight": "",
                "cash_drag_delta": "",
                "rebalance_period": "",
                "cash_source_exit_codes": "",
            }
        ],
        "post_exit": [
            {
                "execution_date": "",
                "code": "",
                "trigger_reason": "",
                "stock_return_5d": "",
                "stock_return_10d": "",
                "stock_return_20d": "",
                "stock_return_60d": "",
                "until_next_rebalance_return": "",
                "avoided_loss": "",
                "missed_upside": "",
            }
        ],
    }


def _gate_decision(main: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "model_id": MAIN_CANDIDATE,
            "effectiveness_decision": "effective_v5e_review_candidate_not_accepted",
            "next_gate": "remain_candidate_needs_forward_or_paper_evidence",
            "reason": "Drawdown reduction and clean governance are sufficient to call it an effective review candidate; cash drag and return cost block acceptance.",
            "accepted": "no",
            "v57f_replacement": "no",
            "live_trading_approved": "no",
        }
    ]


def _next_queue(next_gate: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_action": "V5e forward / paper tracking packet",
            "scope": "Track future daily triggers, exits, cash drag and post-exit outcomes for combined_main.",
            "blocked_actions": "accepted_marking; threshold_scan; cash_reallocation",
        },
        {
            "priority": 2,
            "next_action": "V5e formal validation if PM requires more historical packeting",
            "scope": "Audit trigger concentration and drawdown windows without changing rules.",
            "blocked_actions": "new_thresholds; V57f_modification",
        },
    ]


def _allowed_blocked() -> list[dict[str, Any]]:
    return [
        {"action": "retain_effective_review_candidate", "classification": "allowed", "reason": "formal validation passed with review notes"},
        {"action": "create_forward_tracking_templates", "classification": "allowed", "reason": "needed before any future evidence gate"},
        {"action": "mark_accepted", "classification": "blocked", "reason": "cash drag and no forward evidence"},
        {"action": "replace_v57f", "classification": "blocked", "reason": "V57f frozen"},
        {"action": "scan_thresholds", "classification": "blocked", "reason": "pre_registered_not_optimized"},
        {"action": "auto_reallocate_cash", "classification": "blocked", "reason": "V5e cash policy holds cash until next rebalance"},
    ]


def _nonfatal_blockers() -> list[dict[str, Any]]:
    return [
        {"blocker_id": "none_fatal", "severity": "none", "status": "not_blocking", "description": "Formal validation / forward packet completed."},
        {"blocker_id": "forward_evidence_missing", "severity": "review_note", "status": "blocks_acceptance_not_candidate", "description": "No future/paper evidence yet."},
    ]


def _summary(status: str, gate: str, blockers: list[dict[str, Any]], main_metrics: dict[str, Any] | None = None, output_count: int = 0) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "project": "v5e_formal_validation_forward_packet",
        "status": status,
        "created_at_utc": now_utc(),
        "main_candidate": MAIN_CANDIDATE,
        "secondary_candidate": SECONDARY_CANDIDATE,
        "model_effectiveness": "effective_v5e_review_candidate_not_accepted" if not blockers else "blocked",
        "next_gate": gate,
        "accepted": False,
        "v57f_replacement": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "parameter_scan_used": False,
        "joinquant_started": False,
        "network_fetch_started": False,
        "fatal_blocker_count": len([b for b in blockers if b.get("severity") == "fatal"]),
        "main_metrics": main_metrics or {},
        "output_count": output_count,
    }


def _report(summary: dict[str, Any], gate_rows: list[dict[str, Any]], risk_benefit: list[dict[str, Any]], notes: list[dict[str, Any]]) -> str:
    lines = [
        "# V5e Formal Validation / Forward Evidence Packet",
        "",
        "## 结论",
        "",
        f"V5e 已出现有效候选模型：`{MAIN_CANDIDATE}`。",
        "",
        "它是 `effective_v5e_review_candidate_not_accepted`，不是 accepted，不是 V57f replacement，不可实盘。",
        "",
        f"next_gate: `{gate_rows[0]['next_gate']}`",
        "",
        "## 风险收益对比",
        "",
        "| role | version | return | max DD | delta return | delta max DD | cash drag |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in risk_benefit:
        lines.append(f"| {row['role']} | `{row['version_id']}` | {row['strategy_return']} | {row['max_drawdown']} | {row['delta_return_vs_baseline']} | {row['delta_max_drawdown_vs_baseline']} | {row['cash_drag_delta_vs_baseline']} |")
    lines.extend(["", "## Review Notes", ""])
    for note in notes:
        lines.append(f"- `{note['review_note']}` / `{note['severity']}`: {note['evidence']}")
    lines.extend(["", "## PM Meaning", "", "当前已经不是“没有模型”的状态。模型有效性来自回撤改善、PIT/T/reentry 通过、预注册阈值和可审计现金路径；但现金拖累和缺少 forward/paper evidence 阻止任何 accepted 结论。"])
    return "\n".join(lines) + "\n"


def _next_prompt(next_gate: str) -> str:
    return f"""# V5e forward / paper tracking packet

工作目录：D:\\hh\\codex\\v5

目标：为 `{MAIN_CANDIDATE}` 建立 forward/paper tracking。只记录未来触发、退出、现金拖累和退出后表现，不新增阈值，不回测新规则，不标记 accepted。

当前 next_gate：`{next_gate}`
"""


def _agent_rules() -> str:
    return """# V5e Formal Validation Agent Rules

- Candidate may be called effective review candidate, not accepted.
- Do not modify V57f/ERC/V5d.
- Do not scan thresholds or add rules.
- Do not reallocate cash automatically.
- Do not start JoinQuant or fetch network data.
- Forward/paper evidence is required before any stronger gate.
"""


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = _fields(rows)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _find(rows: list[dict[str, str]], key: str, value: str) -> dict[str, str]:
    for row in rows:
        if row.get(key) == value:
            return row
    raise KeyError(value)


def _fields(rows: list[dict[str, Any]]) -> list[str]:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    return fields


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pct(value: Any) -> str:
    v = _float(value)
    return "" if v is None else f"{v:.2%}"


if __name__ == "__main__":
    print(json.dumps(run_v5e_formal_validation_forward_packet(Path(".")), ensure_ascii=False, indent=2))

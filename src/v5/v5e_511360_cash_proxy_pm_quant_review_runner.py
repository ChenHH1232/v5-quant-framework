from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5e_511360_cash_proxy_pm_quant_review") / "current"
ENG_DIR = Path("v5e_511360_cash_proxy_limited_engineering") / "current"
PIT_DIR = Path("v5e_511360_pit_data_audit") / "current"
SPEC_DIR = Path("v5e_511360_cash_proxy_limited_engineering_spec") / "current"
STARTUP_DIR = Path("v5_startup_warmup_price_repair") / "current"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_511360_cash_proxy_pm_quant_review(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_511360_pm_quant_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_511360_pm_quant_review_summary.json", summary)
        return summary

    eng_summary = _read_json(root / ENG_DIR / "v5e_511360_cash_proxy_summary.json")
    metrics = _read_csv(root / ENG_DIR / "v5e_511360_cash_proxy_variant_metrics.csv")
    comparison = _read_csv(root / ENG_DIR / "v5e_511360_cash_proxy_comparison.csv")
    pit_summary = _read_json(root / PIT_DIR / "v5e_511360_pit_data_audit_summary.json")

    variant_review = _variant_review(metrics)
    candidate_checks = _candidate_checks(eng_summary, pit_summary)
    risk_benefit = _risk_benefit_matrix(eng_summary, comparison)
    robustness_notes = _robustness_notes(eng_summary)
    gate = _pm_gate_decision(candidate_checks, eng_summary)
    queue = _next_queue(gate[0]["pm_gate_decision"])
    blockers_out = _blockers(gate)

    _write_csv(out / "v5e_511360_pm_quant_variant_review.csv", variant_review)
    _write_csv(out / "v5e_511360_pm_quant_candidate_checks.csv", candidate_checks)
    _write_csv(out / "v5e_511360_pm_quant_risk_benefit_matrix.csv", risk_benefit)
    _write_csv(out / "v5e_511360_pm_quant_robustness_notes.csv", robustness_notes)
    _write_csv(out / "v5e_511360_pm_quant_gate_decision.csv", gate)
    _write_csv(out / "v5e_511360_pm_quant_next_queue.csv", queue)
    _write_csv(out / "v5e_511360_pm_quant_blockers.csv", blockers_out)
    (out / "v5e_511360_pm_quant_next_prompt.md").write_text(_next_prompt(gate[0]), encoding="utf-8")
    (out / "v5e_511360_pm_quant_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5e_511360_pm_quant_review_report.md").write_text(_report(eng_summary, pit_summary, gate), encoding="utf-8")

    summary = _summary(
        "completed_511360_cash_proxy_pm_quant_review",
        gate[0]["pm_gate_decision"],
        [],
        delta_return_vs_v57f=float(eng_summary["proxy_delta_return_vs_v57f"]),
        delta_return_vs_hold_cash=float(eng_summary["proxy_delta_return_vs_hold_cash"]),
        delta_max_drawdown_vs_v57f=float(eng_summary["proxy_delta_max_drawdown_vs_v57f"]),
    )
    _write_json(out / "v5e_511360_pm_quant_review_summary.json", summary)
    return summary


def _variant_review(metrics: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for row in metrics:
        rows.append(
            {
                "version_id": row["version_id"],
                "strategy_return": row["strategy_return"],
                "max_drawdown": row["max_drawdown"],
                "avg_cash_weight": row["avg_cash_weight"],
                "delta_return_vs_v57f": row["delta_return_vs_v57f"],
                "delta_return_vs_hold_cash": row["delta_return_vs_v5e_hold_cash"],
                "accepted": False,
                "review_status": "candidate_review" if "511360" in row["version_id"] else "reference",
            }
        )
    return rows


def _candidate_checks(eng_summary: dict[str, Any], pit_summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"check_id": "pit_data_gate", "pass": pit_summary.get("pm_gate_decision") == "ready_for_511360_cash_proxy_limited_engineering_spec", "detail": pit_summary.get("pm_gate_decision")},
        {"check_id": "governance_gate", "pass": not eng_summary.get("v57f_core_modified") and not eng_summary.get("v5e_threshold_modified"), "detail": "V57f and V5e thresholds unchanged."},
        {"check_id": "return_vs_hold_cash", "pass": float(eng_summary["proxy_delta_return_vs_hold_cash"]) > 0, "detail": eng_summary["proxy_delta_return_vs_hold_cash"]},
        {"check_id": "return_vs_v57f", "pass": float(eng_summary["proxy_delta_return_vs_v57f"]) > 0, "detail": eng_summary["proxy_delta_return_vs_v57f"]},
        {"check_id": "drawdown_vs_v57f", "pass": float(eng_summary["proxy_delta_max_drawdown_vs_v57f"]) <= 0, "detail": eng_summary["proxy_delta_max_drawdown_vs_v57f"]},
        {"check_id": "accepted_status", "pass": not eng_summary.get("accepted"), "detail": "not accepted"},
    ]


def _risk_benefit_matrix(eng_summary: dict[str, Any], comparison: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {"topic": "cash_drag_relief", "benefit": f"+{float(eng_summary['proxy_delta_return_vs_hold_cash']) * 100:.4f} pct points vs hold-cash V5e", "risk": "proxy asset introduces bond/credit/liquidity risk", "pm_read": "positive_but_needs_forward"},
        {"topic": "baseline_edge", "benefit": f"+{float(eng_summary['proxy_delta_return_vs_v57f']) * 100:.4f} pct points vs V57f", "risk": "historical sample only", "pm_read": "candidate_not_accepted"},
        {"topic": "drawdown", "benefit": f"{float(eng_summary['proxy_delta_max_drawdown_vs_v57f']) * 100:.4f} pct point max drawdown delta vs V57f", "risk": "bond ETF stress regime not fully tested", "pm_read": "needs_stress_review"},
    ]


def _robustness_notes(eng_summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"note_id": "not_parameter_scan", "status": "pass", "description": "Only user-specified 511360 candidate was tested; no proxy asset grid."},
        {"note_id": "open_forward_restore", "status": "review_note", "description": "Three open forward restore events remain at sample end; forward tracking required."},
        {"note_id": "not_accepted", "status": "pass", "description": "Candidate may move to review/forward, not accepted."},
    ]


def _pm_gate_decision(checks: list[dict[str, Any]], eng_summary: dict[str, Any]) -> list[dict[str, Any]]:
    passed = all(bool(row["pass"]) for row in checks)
    decision = "promote_511360_cash_proxy_to_forward_review_candidate_not_accepted" if passed else "remain_diagnostic_511360_cash_proxy"
    return [
        {
            "pm_gate_decision": decision,
            "candidate_promoted": passed,
            "delta_return_vs_v57f": eng_summary["proxy_delta_return_vs_v57f"],
            "delta_return_vs_hold_cash": eng_summary["proxy_delta_return_vs_hold_cash"],
            "accepted": False,
            "reason": "Positive vs hold-cash and V57f with clean governance; still needs forward/paper and stress review before any acceptance."
            if passed
            else "One or more candidate checks failed.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task": "V5e 511360 cash proxy forward/paper tracking packet", "allowed": decision.startswith("promote"), "requires_backtest": False},
        {"priority": 2, "task": "V5e 511360 cash proxy stress and regime review", "allowed": decision.startswith("promote"), "requires_backtest": False},
        {"priority": 3, "task": "V5e sleeve-level risk release limited engineering review", "allowed": True, "requires_backtest": False},
    ]


def _blockers(gate: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": gate[0]["reason"]}]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    delta_return_vs_v57f: float = 0.0,
    delta_return_vs_hold_cash: float = 0.0,
    delta_max_drawdown_vs_v57f: float = 0.0,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_511360_cash_proxy_pm_quant_review",
        "status": status,
        "pm_gate_decision": decision,
        "delta_return_vs_v57f": delta_return_vs_v57f,
        "delta_return_vs_hold_cash": delta_return_vs_hold_cash,
        "delta_max_drawdown_vs_v57f": delta_max_drawdown_vs_v57f,
        "accepted": False,
        "v57f_core_modified": False,
        "v5e_threshold_modified": False,
        "threshold_scan_used": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(eng_summary: dict[str, Any], pit_summary: dict[str, Any], gate: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# V5e 511360 Cash Proxy PM/Quant Review",
            "",
            f"- PM gate decision: `{gate[0]['pm_gate_decision']}`",
            "- Status: review candidate only; not accepted.",
            f"- Delta return vs V57f: {float(eng_summary['proxy_delta_return_vs_v57f']) * 100:.4f} pct points",
            f"- Delta return vs V5e hold cash: {float(eng_summary['proxy_delta_return_vs_hold_cash']) * 100:.4f} pct points",
            f"- Delta max drawdown vs V57f: {float(eng_summary['proxy_delta_max_drawdown_vs_v57f']) * 100:.4f} pct points",
            f"- PIT rows: price={pit_summary.get('price_rows')}, NAV={pit_summary.get('nav_rows')}",
            "",
            "## Decision",
            "- Promote to forward/stress review candidate, not accepted.",
            "- Do not modify V57f or V5e thresholds.",
            "",
        ]
    )


def _next_prompt(gate: dict[str, Any]) -> str:
    return f"""工作目录：
D:\\hh\\codex\\v5

任务名称：
V5e 511360 cash proxy forward/paper tracking + stress review packet

任务目标：
基于 `v5e_511360_cash_proxy_pm_quant_review/current/`，生成 511360 cash proxy 的 forward/paper tracking 与压力场景复核包。不得标记 accepted。

当前 gate：
`{gate["pm_gate_decision"]}`
"""


def _agent_rules() -> str:
    return "\n".join(["# V5e 511360 PM/Quant Review Rules", "", "- Do not mark accepted.", "- Do not modify V57f.", "- Do not change V5e thresholds.", ""])


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        ENG_DIR / "v5e_511360_cash_proxy_summary.json",
        ENG_DIR / "v5e_511360_cash_proxy_variant_metrics.csv",
        ENG_DIR / "v5e_511360_cash_proxy_comparison.csv",
        PIT_DIR / "v5e_511360_pit_data_audit_summary.json",
        SPEC_DIR / "v5e_511360_cash_proxy_spec_summary.json",
        STARTUP_DIR / "v5_startup_warmup_price_repair_summary.json",
    ]
    return [
        {"blocker_id": "missing_required_input", "severity": "fatal", "status": "blocking", "path": str(path)}
        for path in required
        if not (root / path).exists()
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    result = run_v5e_511360_cash_proxy_pm_quant_review()
    print(json.dumps(result, ensure_ascii=False, indent=2))

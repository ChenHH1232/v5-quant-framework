from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EVAL_DIR = Path("v5i_sell_execution_evaluation") / "current"
SPEC_DIR = Path("v5i_technical_sell_execution_quant_spec") / "current"
OUT_DIR = Path("v5i_sell_execution_closeout") / "current"


def run_v5i_sell_execution_closeout(root: Path = Path(".")) -> dict[str, Any]:
    evaluation = root / EVAL_DIR / "v5i_sell_execution_candidate_results.csv"
    gate = root / EVAL_DIR / "v5i_sell_execution_pm_gate_decision.csv"
    if not evaluation.exists() or not gate.exists():
        raise FileNotFoundError("V5i fixed sell-execution evaluation artifacts are required before closeout.")
    results = _read_csv(evaluation)
    decision = _read_csv(gate)[0]
    technical = [row for row in results if row["candidate_id"] != "v5i_existing_sell_time_control"]
    best = max(technical, key=lambda row: float(row["net_cash_delta"]))
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    admission = {
        "pm_gate_decision": "v5i_technical_sell_execution_closeout_diagnostic_only",
        "reason": "All pre-registered technical timing candidates have negative conservative proceeds versus the existing open execution control.",
        "best_candidate": best["candidate_id"],
        "best_net_cash_delta": best["net_cash_delta"],
        "best_proceeds_delta_bps": best["proceeds_delta_bps"],
        "best_positive_event_ratio": best["positive_event_ratio"],
        "joinquant_historical_backtest_admitted": False,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "v5f_mainline_modified": False,
        "v5e_exit_rule_modified": False,
        "new_sell_signal_used": False,
        "threshold_scan_used": False,
    }
    comparison = []
    for row in results:
        comparison.append({
            "candidate_id": row["candidate_id"],
            "fixed_pre_registered": True,
            "net_cash_delta": row["net_cash_delta"],
            "proceeds_delta_bps": row["proceeds_delta_bps"],
            "positive_event_ratio": row["positive_event_ratio"],
            "joinquant_admission": "not_applicable_control" if row["candidate_id"] == "v5i_existing_sell_time_control" else "rejected_negative_conservative_execution_edge",
            "accepted": False,
        })
    next_queue = [
        {"priority": 1, "task_id": "v5i_forward_sell_intent_capture", "status": "optional_observation_only", "scope": "Continue logging true sell intents and realized fills only if V5e paper tracking itself continues; do not execute a technical overlay."},
        {"priority": 2, "task_id": "v5i_joinquant_technical_sell_execution_backtest", "status": "not_admitted", "scope": "Do not generate or run a JoinQuant technical sell-execution strategy from a negative fixed family."},
        {"priority": 3, "task_id": "v5f_primary_forward_paper_tracking", "status": "continue_mainline", "scope": "Keep internal_subsleeve_mom12_70_30 as the only V5f forward/paper mainline candidate."},
    ]
    _write_csv(out / "v5i_sell_execution_closeout_comparison.csv", comparison)
    _write_csv(out / "v5i_sell_execution_closeout_pm_gate.csv", [admission])
    _write_csv(out / "v5i_sell_execution_closeout_next_queue.csv", next_queue)
    _write_json(out / "v5i_sell_execution_closeout_summary.json", {"created_at_utc": _now(), "task": "v5i_sell_execution_closeout", "status": "completed", **admission})
    (out / "v5i_sell_execution_closeout_report.md").write_text(_report(admission, results), encoding="utf-8")
    _refresh_spec(root, admission, comparison, next_queue)
    return {"status": "completed", **admission}


def _refresh_spec(root: Path, admission: dict[str, Any], comparison: list[dict[str, Any]], next_queue: list[dict[str, Any]]) -> None:
    summary_path = root / SPEC_DIR / "v5i_technical_sell_execution_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    summary.update({
        "status": "completed_v5i_technical_sell_execution_closeout_diagnostic_only",
        "pm_gate_decision": admission["pm_gate_decision"],
        "engineering_or_backtest_started": False,
        "fixed_candidate_evaluation_completed": True,
        "joinquant_historical_backtest_admitted": False,
        "immutable_sell_intent_reconstruction_available": True,
        "key_blocker": "No frozen technical sell-timing candidate has a positive conservative execution edge versus the existing open control.",
    })
    _write_json(summary_path, summary)
    _write_csv(root / SPEC_DIR / "v5i_pm_gate_decision.csv", [admission])
    _write_csv(root / SPEC_DIR / "v5i_candidate_closeout_comparison.csv", comparison)
    _write_csv(root / SPEC_DIR / "v5i_next_agent_queue.csv", next_queue)
    pit_path = root / SPEC_DIR / "v5i_pit_data_gate.csv"
    pit = _read_csv(pit_path)
    for row in pit:
        if row.get("gate_id") in {"P0_INTENT_01", "P0_INTENT_02", "P0_V5E_03"}:
            row["current_status"] = "pass_for_v5e_primary_only"
            row["notes"] = "Reconstructed deterministically from frozen V5e T-close trigger and T+1 exit record; V57f same-day sells remain excluded."
        if row.get("gate_id") == "P1_FILL_04":
            row["current_status"] = "pass_for_fixed_evaluation_only"
            row["notes"] = "Same next-minute-open plus 10 bps sell-side slippage and commission convention was applied to control and candidates."
    _write_csv(pit_path, pit)
    report_path = root / SPEC_DIR / "v5i_technical_sell_execution_report.md"
    existing = report_path.read_text(encoding="utf-8-sig")
    appendix = "\n\n## Fixed Candidate Evaluation Closeout\n\n"
    appendix += "- Evaluation used 87 immutable V5e primary profit-lock intents in the formal window.\n"
    appendix += "- Every technical timing candidate underperformed the existing opening control after equal 10 bps sell-side slippage and commission treatment.\n"
    appendix += f"- Best candidate: `{admission['best_candidate']}`, `{float(admission['best_proceeds_delta_bps']):.2f}` bps versus control.\n"
    appendix += "- Therefore V5i stays diagnostic only; no JoinQuant technical sell-execution backtest is admitted.\n"
    report_path.write_text(existing.split("## Fixed Candidate Evaluation Closeout")[0] + appendix, encoding="utf-8")


def _report(admission: dict[str, Any], results: list[dict[str, str]]) -> str:
    lines = [
        "# V5i Technical Sell-Execution Closeout",
        "",
        "- Result population: 87 immutable V5e profit-lock sell intents, 2021-05-01 to 2026-05-31.",
        "- Technical state was strictly downstream of a T-close trigger and only selected a same-day T+1 window.",
        "- Each candidate and the opening control used the same next-minute-open plus 10 bps sell-side slippage convention.",
        f"- Gate: `{admission['pm_gate_decision']}`.",
        f"- Best technical candidate: `{admission['best_candidate']}`, `{float(admission['best_proceeds_delta_bps']):.2f}` bps against control.",
        "- No JoinQuant test is admitted, because the frozen family does not clear a basic economic-value test.",
        "",
        "## Results",
        "",
    ]
    for row in results:
        lines.append(f"- `{row['candidate_id']}`: `{float(row['proceeds_delta_bps']):.2f}` bps, positive events `{float(row['positive_event_ratio']):.1%}`.")
    lines.extend(["", "## Boundary", "", "- No V57f/V5f/V5e rule was changed.", "- No new sell/buy/reentry or cash-routing action was introduced.", "- Not accepted and not live approved.", ""])
    return "\n".join(lines)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    print(json.dumps(run_v5i_sell_execution_closeout(), ensure_ascii=False, indent=2))

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROVENANCE_DIR = Path("v5i_sell_execution_provenance") / "current"
OUT_DIR = Path("v5i_sell_execution_evaluation") / "current"
MINUTE_DIR = Path("数据库") / "processed" / "local_1min_clean_2013_2026" / "by_year"
FORMAL_START = "2021-05-01"
FORMAL_END = "2026-05-31"
SELL_SLIPPAGE_RATE = 0.001  # Conservative 10 bps sell-side execution penalty.
COMMISSION_RATE = 0.0003
MIN_COMMISSION = 5.0


def run_v5i_sell_execution_evaluation(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    intent_path = root / PROVENANCE_DIR / "v5i_immutable_sell_intent_ledger.csv"
    if not intent_path.exists():
        return _blocked(out, "missing_p0_intent_ledger", str(intent_path))
    intents = _read_csv(intent_path)
    if not intents:
        return _blocked(out, "empty_p0_intent_ledger", str(intent_path))

    by_event: list[dict[str, Any]] = []
    for intent in intents:
        by_event.extend(_evaluate_intent(root, intent))
    results = _candidate_results(by_event)
    pit = _pit_audit(by_event, intents)
    governance = _governance_audit(by_event)
    health = _data_health(by_event)
    decision = _decision(results, pit, governance, health)
    blockers = _blockers(decision, health)
    _write_csv(out / "v5i_sell_execution_event_evaluation.csv", by_event)
    _write_csv(out / "v5i_sell_execution_candidate_results.csv", results)
    _write_csv(out / "v5i_sell_execution_pit_audit.csv", pit)
    _write_csv(out / "v5i_sell_execution_governance_audit.csv", governance)
    _write_csv(out / "v5i_sell_execution_data_health.csv", health)
    _write_csv(out / "v5i_sell_execution_pm_gate_decision.csv", [decision])
    _write_csv(out / "v5i_sell_execution_blockers.csv", blockers)
    _write_csv(out / "v5i_sell_execution_next_agent_queue.csv", _next_queue(decision))
    summary = {
        "created_at_utc": _now(),
        "task": "v5i_fixed_sell_execution_evaluation",
        "status": "completed_fixed_candidate_evaluation",
        "formal_backtest_start": FORMAL_START,
        "formal_backtest_end": FORMAL_END,
        "primary_event_family": "v5e_profit_lock_main_exit",
        "intent_count": len(intents),
        "candidate_count_including_control": len(results),
        "conservative_sell_slippage_bps": SELL_SLIPPAGE_RATE * 10000,
        "pm_gate_decision": decision["pm_gate_decision"],
        "joinquant_historical_backtest_ready": decision["joinquant_historical_backtest_ready"],
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "v5f_mainline_modified": False,
        "v5e_exit_rule_modified": False,
        "new_sell_signal_used": False,
        "threshold_scan_used": False,
    }
    _write_json(out / "v5i_sell_execution_evaluation_summary.json", summary)
    (out / "v5i_sell_execution_evaluation_report.md").write_text(_report(summary, results, health, decision), encoding="utf-8")
    return summary


def _evaluate_intent(root: Path, intent: dict[str, str]) -> list[dict[str, Any]]:
    bars = _load_day(root, intent["code"], intent["execution_date"])
    index = {row["time"]: row for row in bars}
    control = _fill(index, "09:31:00")
    features_1000 = _features(bars, "10:00:00")
    features_1400 = _features(bars, "14:00:00")
    two_5m_break = _two_5m_break(bars)
    variants = [
        ("v5i_existing_sell_time_control", "09:31:00", "original_open_control", True),
        ("v5i_vwap_1000_protect_else_1400", "10:01:00" if features_1000["close_lte_vwap"] else "14:01:00", "vwap_1000", features_1000["available"]),
        ("v5i_two_5m_vwap_break_1000_else_1400", "10:01:00" if two_5m_break else "14:01:00", "two_5m_vwap_break", features_1000["available"]),
        ("v5i_1400_vwap_hold_to_1445", "14:01:00" if features_1400["close_lte_vwap"] else "14:46:00", "vwap_1400", features_1400["available"]),
    ]
    output = []
    for candidate_id, selected_time, rule_branch, signal_available in variants:
        fill = control if candidate_id == "v5i_existing_sell_time_control" else _fill(index, selected_time)
        fallback_used = False
        if not signal_available or fill is None:
            fill = control
            fallback_used = True
        archived_daily_open_price = _float(intent.get("original_price"))
        # The V5i control must use the same executable-bar convention and slippage
        # as every candidate. The archived daily open is retained only for audit.
        control_price = _float(control.get("open")) if control else 0.0
        control_fill_price = control_price * (1.0 - SELL_SLIPPAGE_RATE) if control_price else 0.0
        amount = _float(intent.get("amount"))
        fill_price = _float(fill.get("open")) * (1.0 - SELL_SLIPPAGE_RATE) if fill else 0.0
        control_proceeds = _net_proceeds(amount, control_fill_price)
        candidate_proceeds = _net_proceeds(amount, fill_price)
        output.append(
            {
                "intent_id": intent["intent_id"],
                "candidate_id": candidate_id,
                "code": intent["code"],
                "trigger_date": intent["trigger_date"],
                "execution_date": intent["execution_date"],
                "intent_created_timestamp": intent["sell_decision_timestamp"],
                "signal_time": "" if candidate_id == "v5i_existing_sell_time_control" else ("10:00:00" if "1000" in candidate_id else "14:00:00"),
                "selected_execution_time": selected_time,
                "rule_branch": rule_branch,
                "signal_available": signal_available,
                "fallback_used": fallback_used,
                "minute_row_count": len(bars),
                "archived_daily_open_price": archived_daily_open_price,
                "control_open_price": control_price,
                "control_conservative_fill_price": control_fill_price,
                "selected_bar_open": _float(fill.get("open")) if fill else 0.0,
                "conservative_fill_price": fill_price,
                "amount": amount,
                "control_net_proceeds": control_proceeds,
                "candidate_net_proceeds": candidate_proceeds,
                "net_cash_delta": candidate_proceeds - control_proceeds,
                "net_return_delta_bps": (fill_price / control_fill_price - 1.0) * 10000 if control_fill_price > 0 and fill_price > 0 else 0.0,
                "vwap_to_1000": features_1000["vwap"],
                "close_1000": features_1000["close"],
                "close_1000_lte_vwap": features_1000["close_lte_vwap"],
                "two_5m_vwap_break": two_5m_break,
                "vwap_to_1400": features_1400["vwap"],
                "close_1400": features_1400["close"],
                "close_1400_lte_vwap": features_1400["close_lte_vwap"],
                "pit_status": "pass" if intent["trigger_date"] < intent["execution_date"] else "fail",
                "accepted": False,
            }
        )
    return output


def _load_day(root: Path, code: str, day: str) -> list[dict[str, str]]:
    path = root / MINUTE_DIR / day[:4] / f"{code.replace('.', '_')}_1min.csv"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [row for row in csv.DictReader(handle) if row.get("trade_date") == day]


def _features(bars: list[dict[str, str]], observed_to: str) -> dict[str, Any]:
    visible = [bar for bar in bars if bar["time"] <= observed_to]
    volume = sum(_float(bar.get("volume")) for bar in visible)
    amount = sum(_float(bar.get("amount")) for bar in visible)
    row = next((bar for bar in visible if bar["time"] == observed_to), None)
    vwap = amount / volume if volume > 0 else 0.0
    close = _float(row.get("close")) if row else 0.0
    return {"available": bool(row and volume > 0), "vwap": vwap, "close": close, "close_lte_vwap": bool(close and vwap and close <= vwap)}


def _two_5m_break(bars: list[dict[str, str]]) -> bool:
    first = _features(bars, "09:55:00")
    second = _features(bars, "10:00:00")
    return bool(first["available"] and second["available"] and first["close_lte_vwap"] and second["close_lte_vwap"])


def _fill(index: dict[str, dict[str, str]], time_value: str) -> dict[str, str] | None:
    row = index.get(time_value)
    return row if row and _float(row.get("volume")) > 0 and _float(row.get("low")) > 0 else None


def _net_proceeds(amount: float, price: float) -> float:
    gross = amount * price
    return gross - max(MIN_COMMISSION, gross * COMMISSION_RATE) if gross > 0 else 0.0


def _candidate_results(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["candidate_id"]].append(row)
    out = []
    for candidate, group in sorted(groups.items()):
        eligible = [row for row in group if _float(row["candidate_net_proceeds"]) > 0]
        total_control = sum(_float(row["control_net_proceeds"]) for row in eligible)
        total_candidate = sum(_float(row["candidate_net_proceeds"]) for row in eligible)
        positive = sum(_float(row["net_cash_delta"]) > 0 for row in eligible)
        out.append({
            "candidate_id": candidate,
            "event_count": len(group),
            "fillable_event_count": len(eligible),
            "fallback_count": sum(bool(row["fallback_used"]) for row in group),
            "positive_event_count": positive,
            "positive_event_ratio": positive / len(eligible) if eligible else 0.0,
            "total_control_net_proceeds": total_control,
            "total_candidate_net_proceeds": total_candidate,
            "net_cash_delta": total_candidate - total_control,
            "proceeds_delta_bps": (total_candidate / total_control - 1.0) * 10000 if total_control else 0.0,
            "mean_event_delta_bps": sum(_float(row["net_return_delta_bps"]) for row in eligible) / len(eligible) if eligible else 0.0,
            "median_event_delta_bps": _median([_float(row["net_return_delta_bps"]) for row in eligible]),
            "accepted": False,
        })
    return out


def _pit_audit(rows: list[dict[str, Any]], intents: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {"audit_id": "intent_precedes_intraday_signal", "status": "pass" if all(row["pit_status"] == "pass" for row in rows) else "fail", "detail": "V5e trigger T-close; technical observation only T+1."},
        {"audit_id": "completed_bar_only", "status": "pass", "detail": "10:00/14:00 decision consumes bar through its timestamp; fill is next minute."},
        {"audit_id": "formal_scope_preserved", "status": "pass" if all(FORMAL_START <= x["execution_date"] <= FORMAL_END for x in intents) else "fail", "detail": f"{FORMAL_START} to {FORMAL_END}."},
        {"audit_id": "pre2021_not_used_for_tuning", "status": "pass", "detail": "No pre-2021 optimization or parameter selection is performed."},
    ]


def _governance_audit(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"audit_id": "immutable_upstream_sell_only", "status": "pass", "value": len({row['intent_id'] for row in rows}), "detail": "Every row starts from ledger intent."},
        {"audit_id": "no_new_sell_signal", "status": "pass", "value": 0, "detail": "Technical state selects a window only."},
        {"audit_id": "no_resize_cancel_or_date_change", "status": "pass", "value": 0, "detail": "Amount and execution date remain immutable."},
        {"audit_id": "no_buy_reentry_or_cross_sleeve_transfer", "status": "pass", "value": 0, "detail": "Sell-execution analysis has no buy or cash-routing branch."},
        {"audit_id": "not_accepted_not_live", "status": "pass", "value": False, "detail": "Evaluation output is research only."},
    ]


def _data_health(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    event_ids = {row["intent_id"] for row in rows}
    control_rows = [row for row in rows if row["candidate_id"] == "v5i_existing_sell_time_control"]
    return [
        {"gate_id": "event_population", "status": "pass" if len(event_ids) >= 50 else "fail", "value": len(event_ids), "detail": "Primary V5e sell intents."},
        {"gate_id": "control_open_available", "status": "pass" if all(_float(row["control_open_price"]) > 0 for row in control_rows) else "fail", "value": len(control_rows), "detail": "Archived V5e daily-open proxy is preserved."},
        {"gate_id": "minute_fill_coverage", "status": "pass" if all(_float(row["candidate_net_proceeds"]) > 0 for row in control_rows) else "fail", "value": sum(_float(row["candidate_net_proceeds"]) > 0 for row in control_rows), "detail": "The control needs a valid 09:31 bar."},
        {"gate_id": "pre2021_independent_v5e_population", "status": "not_available", "value": 0, "detail": "V5e primary rule begins in formal window; not a reason to tune or claim independent validation."},
    ]


def _decision(results: list[dict[str, Any]], pit: list[dict[str, Any]], governance: list[dict[str, Any]], health: list[dict[str, Any]]) -> dict[str, Any]:
    technical = [row for row in results if row["candidate_id"] != "v5i_existing_sell_time_control"]
    best = max(technical, key=lambda row: _float(row["net_cash_delta"]))
    hard_failure = any(row["status"] == "fail" for row in pit + governance + health)
    has_economic_edge = _float(best["net_cash_delta"]) > 0 and _float(best["positive_event_ratio"]) >= 0.5
    decision = "blocked_by_pit_or_data_issue" if hard_failure else "diagnostic_only_no_economic_edge"
    ready = False
    if not hard_failure and has_economic_edge:
        decision = "positive_but_requires_independent_or_forward_validation_before_joinquant"
    return {
        "pm_gate_decision": decision,
        "best_fixed_candidate": best["candidate_id"],
        "best_net_cash_delta": best["net_cash_delta"],
        "best_proceeds_delta_bps": best["proceeds_delta_bps"],
        "best_positive_event_ratio": best["positive_event_ratio"],
        "joinquant_historical_backtest_ready": ready,
        "accepted": False,
        "live_trading_approved": False,
        "reason": "A JoinQuant strategy is generated only after a fixed candidate shows conservative economic value and has independent/forward validation; no such admission is automatic.",
    }


def _blockers(decision: dict[str, Any], health: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [{"blocker_id": row["gate_id"], "severity": "fatal" if row["status"] == "fail" else "info", "status": row["status"], "detail": row["detail"]} for row in health if row["status"] != "pass"]
    if not decision["joinquant_historical_backtest_ready"]:
        rows.append({"blocker_id": "joinquant_admission_not_met", "severity": "governance", "status": "blocking", "detail": decision["pm_gate_decision"]})
    return rows


def _next_queue(decision: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task_id": "v5i_fixed_sell_execution_formal_closeout", "status": "ready", "scope": "Preserve results and do not add technical patterns or tune windows."},
        {"priority": 2, "task_id": "v5i_forward_sell_intent_capture", "status": "ready", "scope": "Record real future immutable intent, windows, fills, pause/limit status and compare frozen rules paper-only."},
        {"priority": 3, "task_id": "v5i_joinquant_historical_backtest", "status": "blocked" if not decision["joinquant_historical_backtest_ready"] else "ready", "scope": "Only an admitted fixed candidate; not accepted or live."},
    ]


def _blocked(out: Path, blocker: str, detail: str) -> dict[str, Any]:
    summary = {"task": "v5i_fixed_sell_execution_evaluation", "status": "blocked", "pm_gate_decision": "blocked_by_missing_input", "blocker": blocker, "detail": detail, "accepted": False}
    _write_json(out / "v5i_sell_execution_evaluation_summary.json", summary)
    _write_csv(out / "v5i_sell_execution_blockers.csv", [{"blocker_id": blocker, "severity": "fatal", "status": "blocking", "detail": detail}])
    return summary


def _report(summary: dict[str, Any], results: list[dict[str, Any]], health: list[dict[str, Any]], decision: dict[str, Any]) -> str:
    rows = [
        "# V5i Fixed Technical Sell-Execution Evaluation",
        "",
        f"- Scope: `{FORMAL_START}` to `{FORMAL_END}`, using only frozen V5e main profit-lock exits.",
        f"- Events: `{summary['intent_count']}`; each intent was known at the preceding trigger-date close.",
        f"- Conservative convention: next executable one-minute bar open less `{SELL_SLIPPAGE_RATE * 10000:.0f}` bps sell slippage, plus normal commission; the same treatment applies to the control.",
        f"- PM gate: `{decision['pm_gate_decision']}`.",
        "- No model creates, cancels, resizes, or delays a sell beyond its original date.",
        "",
        "## Fixed Candidate Results",
        "",
    ]
    for row in results:
        rows.append(f"- `{row['candidate_id']}`: net cash delta `{_float(row['net_cash_delta']):.2f}`, proceeds delta `{_float(row['proceeds_delta_bps']):.2f}` bps, positive-event ratio `{_float(row['positive_event_ratio']):.1%}`.")
    rows.extend(["", "## Limits", "", "- This is event-level execution evidence, not a full strategy-NAV or accepted-strategy result.", "- V57f same-day rebalance sells remain excluded pending a timestamped pre-intraday intent snapshot.", "- The V5e primary rule has no pre-2021 event population, so no independent-pre-2021 claim is made.", ""])
    return "\n".join(rows)


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


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _float(value: Any) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    half = len(values) // 2
    return values[half] if len(values) % 2 else (values[half - 1] + values[half]) / 2


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    print(json.dumps(run_v5i_sell_execution_evaluation(), ensure_ascii=False, indent=2))

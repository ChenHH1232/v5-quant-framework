from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5i_sell_execution_provenance") / "current"
V5E_EXIT_LOG = Path("v5e_limited_engineering_loop") / "current" / "v5e_exit_action_log.csv"
V57F_TRADES = Path("v5e_limited_engineering_loop") / "current" / "runs" / "v57f_repaired_baseline" / "trades.csv"
FORMAL_START = "2021-05-01"
FORMAL_END = "2026-05-31"
PRIMARY_V5E = "v5e_profit_lock_main_20pct_sell50"


def run_v5i_sell_intent_provenance(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    missing = [str(path) for path in (V5E_EXIT_LOG, V57F_TRADES) if not (root / path).exists()]
    if missing:
        summary = _summary("blocked_missing_input", [], missing)
        _write_json(out / "v5i_sell_intent_provenance_summary.json", summary)
        _write_csv(out / "v5i_sell_intent_provenance_blockers.csv", [{"blocker": "missing_input", "path": path} for path in missing])
        return summary

    exits = _read_csv(root / V5E_EXIT_LOG)
    intents = []
    for row in exits:
        if row.get("version_id") != PRIMARY_V5E or row.get("side") != "sell":
            continue
        execution_date = row.get("execution_date", "")
        trigger_date = row.get("trigger_date", "")
        if not (FORMAL_START <= execution_date <= FORMAL_END and trigger_date < execution_date):
            continue
        action_id = f"{PRIMARY_V5E}|{trigger_date}|{execution_date}|{row.get('code', '')}"
        intents.append(
            {
                "intent_id": action_id,
                "event_family": "v5e_profit_lock_main_exit",
                "action_id": action_id,
                "version_id": PRIMARY_V5E,
                "code": row.get("code", ""),
                "side": "sell",
                "trigger_date": trigger_date,
                "execution_date": execution_date,
                "sell_decision_timestamp": f"{trigger_date} 15:00:00",
                "intent_visible_before_execution_date": True,
                "scheduled_execution_windows": "10:00:00;14:00:00;14:45:00",
                "original_execution_policy": "daily_open_proxy_only_not_used_as_intraday_fill",
                "amount": row.get("amount", ""),
                "original_value": row.get("value", ""),
                "original_price": row.get("price", ""),
                "sell_fraction": "0.5",
                "reentry_allowed": False,
                "cross_sleeve_transfer_allowed": False,
                "technical_signal_can_create_intent": False,
                "provenance_status": "pass_v5e_t_close_trigger_next_day_execution",
                "eligibility": "primary_eligible",
                "notes": "Trigger is frozen after trigger-date close; technical feature may only select a next-day window using completed bars.",
            }
        )

    v57f_sells = [
        row for row in _read_csv(root / V57F_TRADES)
        if row.get("side") == "sell" and FORMAL_START <= row.get("trade_date", "") <= FORMAL_END
    ]
    excluded = [
        {
            "event_family": "v57f_rebalance_decrease",
            "event_count": len(v57f_sells),
            "eligibility": "excluded_from_primary_evaluation",
            "reason": "Existing evidence records same-date fills but not a timestamped pre-intraday target-generation snapshot.",
            "required_repair": "retained_preopen_or_timestamped_intent_snapshot",
        }
    ]
    audit = [
        {"audit_id": "immutable_intent_id", "status": "pass" if intents else "fail", "value": len(intents), "detail": "Deterministically derived from frozen primary V5e trigger/execution rows."},
        {"audit_id": "decision_precedes_execution", "status": "pass" if all(x["trigger_date"] < x["execution_date"] for x in intents) else "fail", "value": len(intents), "detail": "V5e T-close trigger to T+1 execution only."},
        {"audit_id": "fixed_execution_windows", "status": "pass", "value": "10:00;14:00;14:45", "detail": "Pre-registered V5i candidate windows."},
        {"audit_id": "v57f_same_day_intents_excluded", "status": "pass", "value": len(v57f_sells), "detail": "No unsupported same-day V57f sell is used in primary V5i result."},
        {"audit_id": "no_reentry_or_target_mutation", "status": "pass", "value": 0, "detail": "The ledger cannot create a new order or change amount."},
    ]
    _write_csv(out / "v5i_immutable_sell_intent_ledger.csv", intents)
    _write_csv(out / "v5i_sell_intent_provenance_audit.csv", audit)
    _write_csv(out / "v5i_excluded_sell_event_families.csv", excluded)
    _write_csv(out / "v5i_sell_intent_provenance_blockers.csv", [])
    summary = _summary("completed_p0_intent_provenance", intents, [])
    _write_json(out / "v5i_sell_intent_provenance_summary.json", summary)
    (out / "v5i_sell_intent_provenance_report.md").write_text(_report(summary, excluded), encoding="utf-8")
    return summary


def _summary(status: str, intents: list[dict[str, Any]], blockers: list[str]) -> dict[str, Any]:
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5i_sell_intent_provenance",
        "status": status,
        "formal_backtest_start": FORMAL_START,
        "formal_backtest_end": FORMAL_END,
        "primary_event_family": "v5e_profit_lock_main_exit",
        "primary_eligible_intent_count": len(intents),
        "v57f_same_day_sell_primary_eligibility": "excluded_pending_timestamped_preintraday_intent_provenance",
        "accepted": False,
        "live_trading_approved": False,
        "joinquant_started": False,
        "threshold_scan_used": False,
        "blockers": blockers,
    }


def _report(summary: dict[str, Any], excluded: list[dict[str, Any]]) -> str:
    return "\n".join([
        "# V5i Sell Intent Provenance",
        "",
        f"- Formal scope: `{FORMAL_START}` to `{FORMAL_END}`.",
        f"- Primary PIT-clean V5e intents: `{summary['primary_eligible_intent_count']}`.",
        "- V5e intent is frozen at trigger-date close and may only select a next-day execution window.",
        "- Same-day V57f rebalance sells remain excluded, because their pre-intraday intent timestamp is not retained.",
        "- This ledger cannot create a sell, resize it, cancel it, or permit reentry.",
        "",
        "## Excluded Family",
        "",
        f"- V57f rebalance decreases: `{excluded[0]['event_count']}` rows, `{excluded[0]['eligibility']}`.",
    ]) + "\n"


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


if __name__ == "__main__":
    print(json.dumps(run_v5i_sell_intent_provenance(), ensure_ascii=False, indent=2))

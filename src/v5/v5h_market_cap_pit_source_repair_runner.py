from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5h_market_cap_pit_source_repair") / "current"
CURRENT_PANEL = Path("v5h_market_cap_pit_segmentation_gate") / "current" / "v5h_pit_market_cap_panel.csv"
V4_BANK_VALUATION_ROOT = Path("D:/hh/codex/v4/phase_1_fundamental/raw_downloads/all_banks")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5h_market_cap_pit_source_repair(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    existing_summary_path = out / "v5h_market_cap_pit_source_repair_summary.json"
    panel_path = root / CURRENT_PANEL
    if not panel_path.exists():
        blockers = [_blocker("missing_current_market_cap_panel", str(CURRENT_PANEL))]
        summary = _summary("blocked_missing_current_panel", "blocked_missing_current_market_cap_panel", blockers)
        _write_json(out / "v5h_market_cap_pit_source_repair_summary.json", summary)
        _write_csv(out / "v5h_market_cap_repair_blockers.csv", blockers)
        return summary

    panel = _read_csv(panel_path)
    missing = [
        row
        for row in panel
        if row.get("market_cap_pit_status") != "pass" or _none_float(row.get("market_cap_100m_cny")) is None
    ]
    if not missing and existing_summary_path.exists():
        existing_summary = json.loads(existing_summary_path.read_text(encoding="utf-8-sig"))
        if existing_summary.get("repair_decision") == "attempt_1_success_later_steps_skipped":
            return existing_summary
    _write_csv(out / "v5h_market_cap_missing_rows_before.csv", missing)

    attempt_order = [
        {
            "attempt_order": 1,
            "source_level": "daily_total_market_cap",
            "candidate_fields": "market_cap / total_mv",
            "status": "pending",
            "stop_if_success": True,
        },
        {
            "attempt_order": 2,
            "source_level": "daily_circulating_market_cap",
            "candidate_fields": "circulating_market_cap / circ_mv",
            "status": "pending",
            "stop_if_success": True,
        },
        {
            "attempt_order": 3,
            "source_level": "earlier_visible_share_capital",
            "candidate_fields": "share capital / equity structure reports",
            "status": "pending",
            "stop_if_success": False,
        },
    ]

    probe_rows: list[dict[str, Any]] = []
    repaired_rows: list[dict[str, Any]] = []
    decision_status = "no_missing_market_cap_rows"
    repair_decision = "no_repair_needed"
    succeeded_attempt = ""

    if missing:
        valuation_root = _find_v4_bank_valuation_root(root)
        attempt1 = _attempt_daily_total_market_cap(missing, valuation_root)
        probe_rows.append(attempt1["probe"])
        repaired_rows = attempt1["rows"]
        attempt_order[0]["status"] = "success" if attempt1["success"] else "failed"
        if attempt1["success"]:
            attempt_order[1]["status"] = "skipped_after_attempt_1_success"
            attempt_order[2]["status"] = "skipped_after_attempt_1_success"
            decision_status = "completed_attempt_1_daily_total_market_cap_repair"
            repair_decision = "attempt_1_success_later_steps_skipped"
            succeeded_attempt = "1"
        else:
            attempt_order[1]["status"] = "not_executed_in_this_runner"
            attempt_order[2]["status"] = "not_executed_in_this_runner"
            decision_status = "blocked_attempt_1_daily_total_market_cap_unresolved"
            repair_decision = "attempt_1_failed_need_attempt_2_or_3"
    else:
        for item in attempt_order:
            item["status"] = "skipped_no_missing_rows"
        probe_rows.append(
            {
                "attempt_order": 1,
                "source_level": "daily_total_market_cap",
                "source_path": "",
                "required_missing_rows": 0,
                "repaired_rows": 0,
                "status": "skipped_no_missing_rows",
                "notes": "",
            }
        )

    _write_csv(out / "v5h_market_cap_source_attempt_order.csv", attempt_order)
    _write_csv(out / "v5h_market_cap_source_probe_result.csv", probe_rows)
    _write_csv(out / "v5h_market_cap_repaired_rows.csv", repaired_rows)
    decision_rows = [
        {
            "repair_decision": repair_decision,
            "succeeded_attempt": succeeded_attempt,
            "attempt_2_executed": False,
            "attempt_3_executed": False,
            "network_fetch_started": False,
            "joinquant_started": False,
            "accepted": False,
            "notes": "Attempt order honored. Daily total market-cap source stops later repairs when complete.",
        }
    ]
    _write_csv(out / "v5h_market_cap_repair_decision.csv", decision_rows)
    blockers = (
        [{"blocker_id": "none", "severity": "none", "status": "not_blocking", "description": ""}]
        if repair_decision in {"attempt_1_success_later_steps_skipped", "no_repair_needed"}
        else [_blocker("attempt_1_unresolved", "Daily total market-cap source did not repair all missing rows.")]
    )
    _write_csv(out / "v5h_market_cap_repair_blockers.csv", blockers)
    (out / "v5h_market_cap_pit_source_repair_report.md").write_text(
        _report(missing, probe_rows, repaired_rows, decision_rows),
        encoding="utf-8",
    )
    (out / "v5h_market_cap_repair_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    summary = _summary(
        decision_status,
        repair_decision,
        blockers,
        missing_rows_before=len(missing),
        repaired_rows=len(repaired_rows),
        succeeded_attempt=succeeded_attempt,
        later_steps_skipped=repair_decision == "attempt_1_success_later_steps_skipped",
    )
    _write_json(out / "v5h_market_cap_pit_source_repair_summary.json", summary)
    return summary


def _attempt_daily_total_market_cap(missing: list[dict[str, Any]], valuation_root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if not valuation_root.exists():
        return {
            "success": False,
            "rows": rows,
            "probe": {
                "attempt_order": 1,
                "source_level": "daily_total_market_cap",
                "source_path": str(valuation_root),
                "required_missing_rows": len(missing),
                "repaired_rows": 0,
                "status": "failed_source_not_found",
                "notes": "V4 bank daily valuation directory not found locally.",
            },
        }
    for row in missing:
        trade_date = str(row.get("trade_date", ""))
        code = str(row.get("code", ""))
        valuation = _read_v4_daily_valuation_row(valuation_root, code, trade_date)
        market_cap = _none_float(valuation.get("market_cap"))
        if valuation and market_cap is not None:
            rows.append(
                {
                    "trade_date": trade_date,
                    "code": code,
                    "sleeve": row.get("sleeve", ""),
                    "market_cap_100m_cny": market_cap,
                    "market_cap_source": str(_valuation_path(valuation_root, code)),
                    "market_cap_visible_date": trade_date,
                    "market_cap_pit_method": "direct_v4_migrated_daily_valuation_market_cap",
                    "market_cap_pit_status": "pass",
                    "source_level": "daily_total_market_cap",
                    "attempt_order": 1,
                    "accepted": False,
                }
            )
    return {
        "success": len(rows) == len(missing),
        "rows": rows,
        "probe": {
            "attempt_order": 1,
            "source_level": "daily_total_market_cap",
            "source_path": str(valuation_root),
            "required_missing_rows": len(missing),
            "repaired_rows": len(rows),
            "status": "success" if len(rows) == len(missing) else "partial_or_failed",
            "notes": "Uses same-day JoinQuant-style daily valuation migrated from V4; no network/API call.",
        },
    }


def _read_v4_daily_valuation_row(valuation_root: Path, code: str, trade_date: str) -> dict[str, Any]:
    path = _valuation_path(valuation_root, code)
    for row in _read_csv(path):
        if str(row.get("day", "")) == trade_date and str(row.get("code", "")) == code:
            return row
    return {}


def _valuation_path(valuation_root: Path, code: str) -> Path:
    return valuation_root / code.replace(".", "_") / "daily_valuation.csv"


def _find_v4_bank_valuation_root(root: Path) -> Path:
    candidates = [
        V4_BANK_VALUATION_ROOT,
        root.resolve().parent / "v4" / "phase_1_fundamental" / "raw_downloads" / "all_banks",
    ]
    return next((path for path in candidates if path.exists()), candidates[0])


def _report(
    missing: list[dict[str, Any]],
    probe_rows: list[dict[str, Any]],
    repaired_rows: list[dict[str, Any]],
    decision_rows: list[dict[str, Any]],
) -> str:
    decision = decision_rows[0]
    lines = [
        "# V5h Market-Cap PIT Source Repair",
        "",
        f"- Missing rows before repair: `{len(missing)}`",
        f"- Repaired rows: `{len(repaired_rows)}`",
        f"- Repair decision: `{decision['repair_decision']}`",
        f"- Succeeded attempt: `{decision['succeeded_attempt']}`",
        "- Later attempts executed: `false`",
        "- Network/API fetch: `false`",
        "",
        "## Source Probe",
    ]
    for row in probe_rows:
        lines.append(
            f"- Attempt {row['attempt_order']} `{row['source_level']}`: `{row['status']}`, repaired `{row['repaired_rows']}/{row['required_missing_rows']}`."
        )
    lines.extend(
        [
            "",
            "The repair uses direct same-day daily valuation `market_cap` rows already present in the local V4 migration source.",
            "It does not change V57f, V5f, execution timing, or model status.",
            "",
        ]
    )
    return "\n".join(lines)


def _rules() -> str:
    return "\n".join(
        [
            "# V5h Market-Cap PIT Source Repair Rules",
            "",
            "- Execute source attempts in order: total market cap, circulating market cap, earlier visible share capital.",
            "- Stop later attempts once an earlier attempt fully repairs the required rows.",
            "- Do not use future visible share capital for a past trade date.",
            "- Do not modify V57f core or V5f mainline.",
            "- Do not mark accepted, live approved, or deployment approved.",
            "",
        ]
    )


def _summary(status: str, decision: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5h_market_cap_pit_source_repair",
        "status": status,
        "repair_decision": decision,
        "accepted": False,
        "live_trading_approved": False,
        "deployment_approved": False,
        "v57f_core_modified": False,
        "v5f_mainline_modified": False,
        "trading_frequency_increased": False,
        "new_buy_signal_used": False,
        "network_fetch_started": False,
        "joinquant_started": False,
        "fatal_blocker_count": len([row for row in blockers if row.get("status") == "blocking"]),
        "fatal_blockers": [row for row in blockers if row.get("status") == "blocking"],
        **extra,
    }


def _blocker(blocker_id: str, description: str) -> dict[str, Any]:
    return {"blocker_id": blocker_id, "severity": "fatal", "status": "blocking", "description": description}


def _none_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        text = str(value).strip()
        if text == "" or text.lower() in {"nan", "none", "null"}:
            return None
        out = float(text)
        return out if math.isfinite(out) else None
    except Exception:
        return None


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    summary = run_v5h_market_cap_pit_source_repair(Path("."))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

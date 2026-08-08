from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT = Path("v5j_pre2021_target_reconstruction_readiness") / "current"
BANK = Path("v5j_bank_2011_2012_regulatory_pdf_repair") / "current" / "v5j_bank_2011_2012_pit_coverage.csv"
ACTION = Path("v5j_material_corporate_action_notice_repair") / "current" / "v5j_material_action_original_terms_review_matrix.csv"
INFRA = Path("v5j_pre2021_infra_original_cashflow_panel") / "current" / "v5j_infra_cashflow_field_coverage.csv"
CALENDAR = Path("processed") / "pre2021_repaired_multisleeve_pit_pool_v5" / "quarterly_rebalance_calendar.csv"


def run_v5j_pre2021_target_reconstruction_readiness(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT; out.mkdir(parents=True, exist_ok=True)
    db = root / "数据库"
    required = [root / BANK, root / ACTION, root / INFRA, db / CALENDAR]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing readiness input: " + "; ".join(missing))
    bank, actions, infra, calendar = _read(root / BANK), _read(root / ACTION), _read(root / INFRA), _read(db / CALENDAR)
    readiness = _readiness(bank, actions, infra)
    snapshots = _snapshot_manifest(calendar, readiness)
    decision = _decision(readiness)
    blockers = [row for row in readiness if row["status"] != "pass"]
    summary = {
        "created_at_utc": _now(), "task": "v5j_pre2021_target_reconstruction_readiness",
        "historical_rebalance_date_count": len(snapshots), "target_snapshot_generated_count": sum(row["snapshot_status"] == "generated_exact_reconstructed_target" for row in snapshots),
        "status": decision["status"], "pm_gate_decision": decision["pm_gate_decision"],
        "accepted": False, "v57f_core_modified": False, "strategy_backtest_started": False,
    }
    _write(out / "v5j_target_reconstruction_readiness.csv", readiness)
    _write(out / "v5j_historical_target_snapshot_manifest.csv", snapshots)
    _write(out / "v5j_target_reconstruction_gate_decision.csv", [decision])
    _write(out / "v5j_target_reconstruction_blockers.csv", blockers)
    (out / "v5j_target_reconstruction_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "v5j_target_reconstruction_report.md").write_text(_report(summary, readiness), encoding="utf-8")
    return summary


def _readiness(bank: list[dict[str, str]], actions: list[dict[str, str]], infra: list[dict[str, str]]) -> list[dict[str, Any]]:
    bank_total = len(bank); bank_all = sum(_truth(row.get("all_three_candidate_terms")) for row in bank)
    # Candidate extraction is deliberately insufficient: original pages and values must be reviewed before target use.
    bank_status = "blocked_original_page_value_review_required" if bank_total else "blocked_bank_source_missing"
    action_pending = sum(row.get("review_status") == "needs_original_notice_terms_review" for row in actions)
    action_missing = sum(row.get("review_status") == "no_candidate_notice_found" for row in actions)
    action_status = "blocked_original_notice_terms_review_required" if action_pending or action_missing else "pass"
    result = [{"component": "bank_regulatory_pit", "coverage_or_count": f"{bank_all}/{bank_total}", "status": bank_status, "reason": "Machine term candidates are not source-page-reviewed values."}, {"component": "material_corporate_actions", "coverage_or_count": f"pending_review={action_pending}; no_candidate={action_missing}", "status": action_status, "reason": "Total-return terms cannot be inferred from adjustment factors."}]
    for sleeve in ("highway_infrastructure", "port_rail_infrastructure", "utilities_electricity"):
        capex = next((row for row in infra if row.get("sleeve_id") == sleeve and row.get("field") == "capex_burden"), {})
        fcf = next((row for row in infra if row.get("sleeve_id") == sleeve and row.get("field") == "free_cash_flow_yield"), {})
        capex_ratio, fcf_ratio = float(capex.get("coverage_ratio") or 0), float(fcf.get("coverage_ratio") or 0)
        status = "pass" if capex_ratio >= .95 and fcf_ratio >= .95 else "blocked_original_ocf_capex_or_fcf_coverage_incomplete"
        result.append({"component": f"{sleeve}_ocf_capex", "coverage_or_count": f"capex={capex_ratio:.2%}; fcf={fcf_ratio:.2%}", "status": status, "reason": "Exact V57f-equivalent target reconstruction needs PIT-original cashflow fields or documented historical policy."})
    return result


def _snapshot_manifest(calendar: list[dict[str, str]], readiness: list[dict[str, Any]]) -> list[dict[str, Any]]:
    passing = all(row["status"] == "pass" for row in readiness)
    dates = sorted({row.get("rebalance_date", "") for row in calendar if "2013-01-01" <= row.get("rebalance_date", "") <= "2021-04-30"})
    return [{"rebalance_date": day, "snapshot_status": "generated_exact_reconstructed_target" if passing else "blocked_before_target_generation", "baseline": "v57f_startup_preload_repaired_baseline", "reason": "all PIT repair gates passed" if passing else "at least one source-page/PIT completeness gate remains blocked", "accepted": False} for day in dates]


def _decision(readiness: list[dict[str, Any]]) -> dict[str, Any]:
    passed = all(row["status"] == "pass" for row in readiness)
    return {"pm_gate_decision": "target_reconstruction_ready_then_frozen_v5f_validation" if passed else "blocked_exact_target_reconstruction_pending_pit_repairs", "status": "ready" if passed else "blocked", "frozen_validation_permitted": passed, "proxy_target_substitution_allowed": False, "accepted": False}


def _truth(value: Any) -> bool: return str(value).lower() in {"true", "1", "yes"}
def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle: return list(csv.DictReader(handle))
def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(k for row in rows for k in row)) or ["empty"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle: writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
def _now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")
def _report(summary: dict[str, Any], readiness: list[dict[str, Any]]) -> str:
    lines = ["# Pre-2021 exact target reconstruction readiness", "", "- This gate does not substitute later reports, factor jumps, or proxies for missing PIT evidence.", "- No historical target or V5f validation is generated while any component is blocked.", ""]
    lines.extend(f"- `{row['component']}`: `{row['status']}` ({row['coverage_or_count']})." for row in readiness)
    return "\n".join(lines) + "\n"


if __name__ == "__main__": print(json.dumps(run_v5j_pre2021_target_reconstruction_readiness(), ensure_ascii=False, indent=2))

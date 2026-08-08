from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT = Path("v5j_frozen_v5f_exact_target_validation") / "current"
READINESS = Path("v5j_pre2021_target_reconstruction_readiness") / "current" / "v5j_target_reconstruction_gate_decision.csv"


def run_v5j_frozen_v5f_exact_target_validation(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT; out.mkdir(parents=True, exist_ok=True)
    path = root / READINESS
    if not path.exists(): raise FileNotFoundError(f"Missing exact target reconstruction gate: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle: decision = next(csv.DictReader(handle), {})
    permitted = str(decision.get("frozen_validation_permitted", "")).lower() == "true"
    result = {
        "validation_id": "v5f_internal_subsleeve_mom12_70_30_pre2021_exact_reconstructed_target",
        "baseline": "v57f_startup_preload_repaired_baseline",
        "research_scope_start": "2013-01-01", "research_scope_end": "2021-04-30",
        "formal_backtest_scope_start": "2021-05-01", "formal_backtest_scope_end": "2026-05-31",
        "frozen_rule": "internal_subsleeve_mom12_70_30", "target_source": "exact_pre2021_reconstructed_v57f_targets",
        "validation_status": "not_run_blocked_exact_pit_target_reconstruction" if not permitted else "ready_to_run_separate_execution",
        "reason": "Target reconstruction gate did not pass; no proxy target substitution is permitted." if not permitted else "Exact target snapshots available; run is separately queued.",
        "accepted": False, "v57f_core_modified": False, "joinquant_started": False, "strategy_backtest_started": False,
    }
    _write(out / "v5j_frozen_v5f_exact_target_validation_status.csv", [result])
    (out / "v5j_frozen_v5f_exact_target_validation_summary.json").write_text(json.dumps({"created_at_utc": _now(), "task": "v5j_frozen_v5f_exact_target_validation", **result}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "v5j_frozen_v5f_exact_target_validation_report.md").write_text("# Frozen V5f exact-target independent validation\n\n- The frozen rule was not run because exact PIT target snapshots are not available.\n- Existing proxy validation remains reference-only and cannot be relabeled as this validation.\n", encoding="utf-8")
    return result


def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle: writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
def _now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__": print(json.dumps(run_v5j_frozen_v5f_exact_target_validation(), ensure_ascii=False, indent=2))

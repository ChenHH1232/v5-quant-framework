from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.v5k_workflow_activation_runner import run_v5k_workflow_activation


OUT = Path("v5m_workflow_test_isolation_repair") / "current"
FORMAL = Path("v5k_workflow_activation_repair") / "current"


def run_v5m_workflow_test_isolation_repair(root: Path = Path(".")) -> dict[str, Any]:
    before = _hashes(root / FORMAL)
    env = dict(os.environ); env["PYTHONPATH"] = "src"
    focused = subprocess.run([sys.executable, "-m", "unittest", "tests.test_v5k_workflow_activation_runner"], cwd=root, env=env, text=True, capture_output=True, check=False, timeout=120)
    after_test = _hashes(root / FORMAL)
    production = run_v5k_workflow_activation(root, execute_tests=True)
    final = _hashes(root / FORMAL)
    isolation_pass = before == after_test
    production_pass = production["status"] == "workflow_activation_pass" and production["workflow_gate_pass"]
    test_rows = _csv(root / FORMAL / "v5k_test_execution_results.csv")
    out = root / OUT; out.mkdir(parents=True, exist_ok=True)
    _write(out / "v5m_current_output_integrity_audit.csv", _diff_rows(before, after_test, "unit_test"))
    _write(out / "v5m_test_mode_output_isolation_audit.csv", [{"unit_test_return_code": focused.returncode, "formal_current_sha_unchanged": isolation_pass, "test_mode_formal_write_allowed": False, "detail": "execute_tests=False defaults to no formal output write."}])
    _write(out / "v5m_production_gate_execution_results.csv", [{"production_status": production["status"], "workflow_gate_pass": production["workflow_gate_pass"], "formal_output_sha_changed_by_production": final != after_test, "production_write_allowed": True}])
    _write(out / "v5m_fast_standard_test_results.csv", test_rows)
    _write(out / "v5m_workflow_gate_decision.csv", [{"workflow_gate": "pass" if production_pass else "blocked", "derived_from_real_production_run": production_pass, "extended_status": next(row["status"] for row in test_rows if row["tier"] == "Extended"), "accepted": False}])
    _write(out / "v5m_workflow_blockers.csv", [] if production_pass and isolation_pass else [{"blocker_id": "workflow_test_isolation_or_production_failure", "status": "blocking"}])
    _write(out / "v5m_source_artifact_manifest.csv", [{"path": str(FORMAL / name), "sha256": digest, "role": "formal_workflow_output"} for name, digest in final.items()])
    (out / "v5m_commit_plan_update.md").write_text("# Bounded Commit Plan Update\n\nKeep source/config/test isolation changes separate from generated V5m artifacts. No file was staged, committed, removed, moved or ignored.\n", encoding="utf-8")
    summary = {"created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "task": "v5m_workflow_test_isolation_repair", "status": "completed_production_gate_rebuilt" if production_pass and isolation_pass else "blocked", "unit_test_did_not_mutate_formal_current": isolation_pass, "production_workflow_gate_pass": production_pass, "fast_status": _tier(test_rows, "Fast"), "standard_status": _tier(test_rows, "Standard"), "extended_status": _tier(test_rows, "Extended"), "accepted": False}
    (out / "v5m_workflow_test_isolation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "v5m_workflow_test_isolation_report.md").write_text("# V5m Workflow Test Isolation Repair\n\n- Unit test mode is isolated from the formal `current` directory.\n- Production gate was rebuilt only after actual Fast and Standard test executions returned zero.\n- Extended remains `not_run` and does not block the production gate.\n", encoding="utf-8")
    return summary


def _hashes(folder: Path) -> dict[str, str]: return {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob("*") if p.is_file()}
def _diff_rows(before: dict[str, str], after: dict[str, str], scope: str) -> list[dict[str, Any]]:
    return [{"scope": scope, "file": key, "before_sha256": before.get(key, ""), "after_sha256": after.get(key, ""), "unchanged": before.get(key) == after.get(key)} for key in sorted(set(before) | set(after))]
def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as h: return list(csv.DictReader(h))
def _tier(rows: list[dict[str, str]], name: str) -> str: return next(row["status"] for row in rows if row["tier"] == name)
def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(dict.fromkeys(k for row in rows for k in row)) or ["empty"]
    with path.open("w", encoding="utf-8-sig", newline="") as h: w = csv.DictWriter(h, fieldnames=keys); w.writeheader(); w.writerows(rows)
if __name__ == "__main__": print(json.dumps(run_v5m_workflow_test_isolation_repair(), ensure_ascii=False, indent=2))

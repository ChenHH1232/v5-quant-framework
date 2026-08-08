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


OUT = Path("v5k_workflow_activation_repair") / "current"
REGISTRY = Path("config") / "v5_active_model_registry.json"
CATALOG = Path("config") / "v5_experiment_catalog.json"
TIERS = Path("config") / "v5_test_tiers.json"
BOUNDARY = Path("config") / "v5_historical_operation_boundary.json"
CORE_ENTRYPOINTS = [
    Path("src/v5/v5f_internal_subsleeve_deep_engineering_runner.py"),
    Path("src/v5/v5f_internal_subsleeve_formal_review_runner.py"),
    Path("src/v5/v5f_internal_subsleeve_robustness_packet_runner.py"),
    Path("src/v5/v5j_momentum_overlay_partial_buy_skip_runner.py"),
    Path("src/v5/v5f_clean_forward_target_population_runner.py"),
    Path("src/v5/v5k_active_model_registry_runner.py"),
]
MAINLINE_IO = [
    REGISTRY, CATALOG, BOUNDARY, TIERS,
    Path("v5f_internal_subsleeve_deep_research_spec/current/v5f_internal_subsleeve_rule_spec.csv"),
    Path("v5f_internal_subsleeve_deep_engineering/current/v5f_internal_subsleeve_deep_metrics.csv"),
    Path("v5f_structural_rough_screen/current/v5f_structural_rough_screen_daily_returns.csv"),
    Path("v5f_structural_rough_screen/current/v5f_structural_rough_screen_weights.csv"),
    Path("v5j_momentum_overlay_partial_buy_skip/current/v5j_partial_buy_skip_execution_ledger.csv"),
    Path("v5_qmt_model_retest_packet/current/v5_qmt_actual_no_order_comparison.csv"),
]


def run_v5k_workflow_activation(
    root: Path = Path("."),
    execute_tests: bool = True,
    output_dir: Path | None = None,
    write_outputs: bool | None = None,
) -> dict[str, Any]:
    registry = _read_json(root / REGISTRY)
    catalog = _read_json(root / CATALOG)
    boundary = _read_json(root / BOUNDARY)
    references = _reference_audit(root, registry, catalog, boundary)
    classification = _classify_git_paths(root)
    manifest = [_manifest(root / item) for item in MAINLINE_IO]
    test_rows = _run_tiers(root) if execute_tests else _planned_tiers(root)
    gate_checks = [
        _check("one_repaired_baseline", registry["baseline"]["model_id"] == "v57f_startup_preload_repaired_baseline", registry["baseline"]["model_id"]),
        _check("one_primary_candidate", len(registry["active_models"]) == 1 and registry["active_models"][0]["model_id"] == "internal_subsleeve_mom12_70_30", len(registry["active_models"])),
        _check("formal_window_matches_boundary", registry["formal_backtest_window"]["end"] == boundary["market_data_max_date"], boundary["market_data_max_date"]),
        _check("no_reference_conflict", all(row["status"] == "pass" for row in references), sum(row["status"] != "pass" for row in references)),
        _check("all_mainline_manifest_inputs_exist", all(row["exists"] for row in manifest), sum(not row["exists"] for row in manifest)),
        _check("fast_pass", _tier_pass(test_rows, "Fast"), "Fast"),
        _check("standard_pass", _tier_pass(test_rows, "Standard"), "Standard"),
        _check("no_accepted_or_live_status", not registry["active_models"][0]["accepted"] and not registry["active_models"][0]["live_trading_approved"], False),
    ]
    gate_pass = all(row["status"] == "pass" for row in gate_checks)
    # Unit-test mode is read-only unless an explicit temporary output directory is injected.
    if write_outputs is None:
        write_outputs = execute_tests or output_dir is not None
    out = root / (output_dir or OUT)
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5k_workflow_activation_repair",
        "status": "workflow_activation_pass" if gate_pass else "workflow_activation_blocked",
        "workflow_gate_pass": gate_pass,
        "primary_candidate": registry["active_models"][0]["model_id"],
        "baseline_id": registry["baseline"]["model_id"],
        "market_data_scope_end": boundary["market_data_max_date"],
        "reference_audit_count": len(references),
        "mainline_manifest_count": len(manifest),
        "accepted": False,
        "live_trading_approved": False,
    }
    if write_outputs:
        out.mkdir(parents=True, exist_ok=True)
        _write_csv(out / "v5k_active_model_reference_audit.csv", references)
        _write_csv(out / "v5k_source_artifact_classification.csv", classification)
        _write_csv(out / "v5k_mainline_input_output_manifest.csv", manifest)
        _write_csv(out / "v5k_test_tier_coverage_matrix.csv", _coverage())
        _write_csv(out / "v5k_test_execution_results.csv", test_rows)
        _write_csv(out / "v5k_workflow_gate_decision.csv", [{"workflow_gate": "pass" if gate_pass else "blocked", "allowed_downstream": gate_pass, "accepted": False, "live_trading_approved": False}])
        _write_csv(out / "v5k_workflow_blockers.csv", [row for row in gate_checks if row["status"] != "pass"] or [{"check_id": "none", "status": "not_blocking", "observed": "all_activation_checks_pass"}])
        (out / "v5k_commit_plan.md").write_text(_commit_plan(), encoding="utf-8")
        (out / "v5k_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")
        (out / "v5k_workflow_activation_report.md").write_text(_report(gate_checks, classification), encoding="utf-8")
        (out / "v5k_workflow_activation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def _reference_audit(root: Path, registry: dict[str, Any], catalog: dict[str, Any], boundary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    expected_model = registry["active_models"][0]["model_id"]
    expected_baseline = registry["baseline"]["model_id"]
    for path in CORE_ENTRYPOINTS:
        text = (root / path).read_text(encoding="utf-8")
        registry_ref = "v5_active_model_registry" in text
        rows.append({"entrypoint": str(path), "check_id": "primary_model_reference", "status": "pass" if expected_model in text or registry_ref else "fail", "observed": expected_model})
        rows.append({"entrypoint": str(path), "check_id": "repaired_baseline_reference", "status": "pass" if expected_baseline in text or registry_ref else "fail", "observed": expected_baseline})
    status = _read_json(root / "docs/governance/status_registry.json")
    pointer = status.get("v5_active_model_registry", {})
    rows.append({"entrypoint": "docs/governance/status_registry.json", "check_id": "legacy_pointer_to_authoritative_registry", "status": "pass" if pointer.get("authoritative_path") == str(REGISTRY).replace("\\", "/") else "fail", "observed": pointer.get("authoritative_path", "")})
    rows.append({"entrypoint": "config/v5_experiment_catalog.json", "check_id": "single_active_catalog_record", "status": "pass" if sum(x["experiment_id"] == expected_model and x["status"] == "primary_forward_paper_candidate_not_accepted" for x in catalog["experiments"]) == 1 else "fail", "observed": expected_model})
    rows.append({"entrypoint": "config/v5_historical_operation_boundary.json", "check_id": "post_boundary_operations_blocked", "status": "pass" if boundary["post_boundary_market_operation"] == "blocked" else "fail", "observed": boundary["post_boundary_market_operation"]})
    return rows


def _classify_git_paths(root: Path) -> list[dict[str, Any]]:
    result = subprocess.run(["git", "status", "--porcelain=v1"], cwd=root, text=True, capture_output=True, check=False)
    rows = []
    for line in result.stdout.splitlines():
        state, path = line[:2], line[3:]
        if " -> " in path: path = path.split(" -> ", 1)[1]
        rows.append({"git_state": state, "path": path, "classification": _classify_path(path), "action": "observe_only_no_add_commit_delete_or_cleanup"})
    return rows


def _classify_path(path: str) -> str:
    p = path.replace("\\", "/")
    if p.startswith("src/"): return "source_code"
    if p.startswith("tests/"): return "test_code"
    if p.startswith("config/"): return "configuration"
    if p.startswith(("scripts/", ".github/", "docs/governance/")): return "governance_workflow"
    if p.startswith(("data/", "数据库/")): return "raw_or_processed_data"
    if p.startswith(("v5", "output/", "knowledge/")): return "generated_research_or_knowledge_artifact"
    if p.startswith((".tmp_", "logs/")): return "temporary_or_user_log"
    return "user_or_unclassified"


def _run_tiers(root: Path) -> list[dict[str, Any]]:
    tiers = _read_json(root / TIERS)["tiers"]
    rows = []
    for name in ("fast", "standard"):
        env = dict(os.environ); env["PYTHONPATH"] = "src"
        result = subprocess.run([sys.executable, "-m", "unittest", *tiers[name]], cwd=root, text=True, capture_output=True, env=env, check=False, timeout=120)
        rows.append({"tier": name.title(), "status": "pass" if result.returncode == 0 else "fail", "return_code": result.returncode, "test_modules": len(tiers[name]), "external_market_or_platform_access": False, "output_tail": (result.stdout + result.stderr)[-1000:]})
    rows.append({"tier": "Extended", "status": "not_run", "return_code": "", "test_modules": "all", "external_market_or_platform_access": False, "output_tail": "Intentionally not run: expected runtime may exceed ten minutes."})
    return rows


def _planned_tiers(root: Path) -> list[dict[str, Any]]:
    tiers = _read_json(root / TIERS)["tiers"]
    return [{"tier": name.title(), "status": "not_run_test_mode", "return_code": "", "test_modules": len(tiers[name]), "external_market_or_platform_access": False, "output_tail": "Runner unit-test mode."} for name in ("fast", "standard")]


def _tier_pass(rows: list[dict[str, Any]], tier: str) -> bool:
    return any(row["tier"] == tier and row["status"] == "pass" for row in rows)


def _manifest(path: Path) -> dict[str, Any]:
    return {"path": str(path), "exists": path.exists(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "", "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "market_data_scope_end": "2026-05-31"}


def _coverage() -> list[dict[str, str]]:
    return [
        {"chain": "startup_repaired_baseline", "tier": "Standard", "coverage": "existing repaired-baseline dependent governance chain"},
        {"chain": "v5f_primary_candidate", "tier": "Standard", "coverage": "registry, deep evidence and workflow activation"},
        {"chain": "partial_buy_skip_cash_reconciliation", "tier": "Fast", "coverage": "same-sleeve historical ledger"},
        {"chain": "qmt_no_order_packet_safety", "tier": "Standard", "coverage": "historical export manifest and no-order boundary"},
        {"chain": "active_registry_reference_audit", "tier": "Fast", "coverage": "canonical model/baseline/boundary checks"},
    ]


def _commit_plan() -> str:
    return """# Bounded Commit Plan\n\n1. Source/config/test batch: `src/v5`, `tests`, `config/v5_*`, `scripts/run_v5_tests.ps1`.\n2. Governance/workflow batch: `docs/governance/status_registry.json`, `.github/workflows`, V5k/V5l review outputs.\n3. Generated artifact manifest batch: reviewed `v5*/current` outputs and hash manifests only.\n\nNo batch is staged or committed by this task. Do not use a broad `.gitignore`; source, tests, configuration and key evidence remain visible.\n"""


def _rules() -> str:
    return """# V5k Workflow Activation Rules\n\n- `config/v5_active_model_registry.json` is authoritative for new governance work.\n- Historical status registry is a legacy reference and points to the authoritative registry.\n- Do not alter V57f, use post-2026-05-31 data, generate future targets, start a platform, or approve a model.\n- Worktree review is non-destructive: no add, commit, reset, checkout, clean, delete or move.\n"""


def _report(checks: list[dict[str, Any]], classified: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for row in classified: counts[row["classification"]] = counts.get(row["classification"], 0) + 1
    return "# V5k Workflow Activation Repair\n\n" + "\n".join(f"- `{row['check_id']}`: `{row['status']}`." for row in checks) + "\n\n## Worktree Classification\n\n" + "\n".join(f"- `{kind}`: {count}." for kind, count in sorted(counts.items())) + "\n"


def _check(check_id: str, passed: bool, observed: Any) -> dict[str, Any]:
    return {"check_id": check_id, "status": "pass" if passed else "fail", "observed": observed}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys); writer.writeheader(); writer.writerows(rows)


if __name__ == "__main__":
    print(json.dumps(run_v5k_workflow_activation(), ensure_ascii=False, indent=2))

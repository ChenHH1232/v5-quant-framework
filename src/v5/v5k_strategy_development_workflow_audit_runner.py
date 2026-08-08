from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT = Path("v5k_strategy_development_workflow_audit") / "current"
CONTEXT = Path("config") / "v5_context.json"
PROTOCOL = Path("config") / "agent_operating_protocol_v1.json"
REGISTRY = Path("docs") / "governance" / "status_registry.json"
PRIMARY = Path("v5f_internal_subsleeve_pm_quant_review") / "current" / "v5f_internal_subsleeve_review_summary.json"
FORWARD = Path("v5f_clean_forward_target_population") / "current" / "v5f_clean_forward_target_population_summary.json"
PLATFORM = Path("v5f_joinquant_platform_attribution") / "current" / "v5f_joinquant_platform_attribution_summary.json"
PLATFORM_BLOCKERS = Path("v5f_joinquant_platform_attribution") / "current" / "v5f_joinquant_platform_attribution_blockers.csv"
BRIDGE_AUDIT = Path("v5_jq_sim_to_qmt_sim_bridge") / "current" / "bridge_server" / "data" / "jq_sim_position_upload_audit.csv"
PIT_BOUNDARY = Path("v5j_pit_availability_boundary_closeout") / "current" / "v5j_pit_availability_boundary_closeout_summary.json"
CASH_PATH = Path("v5f_improvement_queue_execution") / "current" / "v5f_momentum_sell_cash_path_audit.csv"


def run_v5k_strategy_development_workflow_audit(root: Path = Path(".")) -> dict[str, Any]:
    required = [CONTEXT, PROTOCOL, REGISTRY, PRIMARY, FORWARD, PLATFORM, PLATFORM_BLOCKERS, BRIDGE_AUDIT, PIT_BOUNDARY, CASH_PATH]
    missing = [str(path) for path in required if not (root / path).exists()]
    if missing:
        raise FileNotFoundError("Missing workflow audit inputs: " + "; ".join(missing))

    context = _read_json(root / CONTEXT)
    protocol = _read_json(root / PROTOCOL)
    registry_text = (root / REGISTRY).read_text(encoding="utf-8")
    primary = _read_json(root / PRIMARY)
    forward = _read_json(root / FORWARD)
    platform = _read_json(root / PLATFORM)
    platform_blockers = _read_csv(root / PLATFORM_BLOCKERS)
    bridge = _read_csv(root / BRIDGE_AUDIT)
    pit = _read_json(root / PIT_BOUNDARY)
    cash = _read_csv(root / CASH_PATH)[0]

    findings = _findings(root, registry_text, primary, forward, platform, platform_blockers, bridge, pit, cash)
    state = _state_matrix(context, protocol, findings)
    repair = _repair_queue(findings)
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    _write_csv(out / "v5k_workflow_finding_register.csv", findings)
    _write_csv(out / "v5k_workflow_state_matrix.csv", state)
    _write_csv(out / "v5k_workflow_repair_queue.csv", repair)
    _write_csv(out / "v5k_workflow_input_manifest.csv", _manifest(root, required))
    (out / "v5k_strategy_development_workflow_audit_report.md").write_text(
        _report(context, findings, state, repair), encoding="utf-8"
    )
    (out / "v5k_workflow_execution_rules.md").write_text(_rules(), encoding="utf-8")

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5k_strategy_development_workflow_audit",
        "status": "completed_workflow_audit_repair_plan_ready",
        "initial_goal": context["mission"],
        "formal_backtest_window": "2021-05-01_to_2026-05-31",
        "primary_candidate": primary["primary_candidate"],
        "p0_count": sum(row["priority"] == "P0" for row in findings),
        "p1_count": sum(row["priority"] == "P1" for row in findings),
        "p2_count": sum(row["priority"] == "P2" for row in findings),
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "pm_gate_decision": "workflow_repair_required_before_any_candidate_promotion",
    }
    _write_json(out / "v5k_workflow_audit_summary.json", summary)
    return summary


def _findings(
    root: Path,
    registry_text: str,
    primary: dict[str, Any],
    forward: dict[str, Any],
    platform: dict[str, Any],
    platform_blockers: list[dict[str, str]],
    bridge: list[dict[str, str]],
    pit: dict[str, Any],
    cash: dict[str, str],
) -> list[dict[str, Any]]:
    dirty = _git_status(root)
    src_count = len(list((root / "src" / "v5").glob("*.py")))
    test_count = len(list((root / "tests").glob("test_*.py")))
    bridge_sources = {row.get("source", "") for row in bridge}
    return [
        {
            "finding_id": "WF_P0_CENTRAL_STATUS_REGISTRY_STALE",
            "priority": "P0",
            "stage": "governance",
            "status": "open",
            "evidence": "internal_subsleeve_mom12_70_30 is absent from docs/governance/status_registry.json despite being the active forward-paper candidate.",
            "risk": "Agents can follow an old baseline or obsolete branch because there is no single authoritative active-model record.",
            "repair": "Create a versioned active-model registry with model_id, baseline_id, formal window, state, owner, evidence paths, and allowed next action; require every runner to reference it.",
        },
        {
            "finding_id": "WF_P0_FORWARD_TARGET_AND_RECEIPT_GAP",
            "priority": "P0",
            "stage": "paper_trading",
            "status": "open",
            "evidence": f"Forward target_ready={forward.get('target_ready')}; bridge has {len(bridge)} receipts and all visible sources are tunnel/test sources: {', '.join(sorted(bridge_sources))}.",
            "risk": "The strategy may run in a platform simulation but there is no authoritative official target file plus durable actual-position receipt for a clean forward cycle.",
            "repair": "At each official rebalance, publish an immutable target snapshot and checksum, upload actual post-trade holdings, verify a receipt locally, and reconcile target/filled/position/cash before closing the cycle.",
        },
        {
            "finding_id": "WF_P0_PLATFORM_CONTRACT_INCOMPLETE",
            "priority": "P0",
            "stage": "platform_replication",
            "status": "open",
            "evidence": f"Platform/local daily correlation={platform.get('daily_return_correlation_vs_local_primary')}; exact platform script snapshot missing={platform.get('script_snapshot_missing')}; platform blockers={len(platform_blockers)}.",
            "risk": "Positive platform performance cannot yet be claimed as exact reproduction of the frozen local contract.",
            "repair": "Archive the exact submitted platform source with hash, configuration, target file hash, fee/slippage assumptions and exports; then rerun a deterministic parity check per rebalance and classify each residual.",
        },
        {
            "finding_id": "WF_P0_PRE2021_EXACT_PIT_BOUNDARY",
            "priority": "P0",
            "stage": "independent_validation",
            "status": "real_data_boundary",
            "evidence": f"PIT closeout gate={pit.get('pm_gate_decision')}; bank disclosure unavailable={pit.get('bank_genuine_disclosure_unavailable_count')}; infra unresolved={pit.get('infra_availability_registry_count')}.",
            "risk": "A proxy historical pool would create false independent validation and sample contamination.",
            "repair": "Maintain the no-proxy rule. Repair only original-page evidence and corporate-action terms where genuinely available; otherwise restrict claims to the formal window and require multi-cycle forward evidence.",
        },
        {
            "finding_id": "WF_P1_CASH_PATH_NOT_EXECUTABLE",
            "priority": "P1",
            "stage": "execution_engineering",
            "status": "open",
            "evidence": f"Same-sleeve cash reconciliation failed {cash.get('failed_period_count')} of {cash.get('reconciliation_period_count')} periods; cross-sleeve transfers remain zero.",
            "risk": "Price-only sell-timing improvements can create unfinanceable buys and overstate strategy NAV.",
            "repair": "Freeze a conservative partial-buy-on-shortfall contract, obtain PM approval, and rerun with realized sell proceeds, fees, lot rounding, fills and residual cash.",
        },
        {
            "finding_id": "WF_P1_REPRODUCIBLE_TEST_ENTRYPOINT_GAP",
            "priority": "P1",
            "stage": "engineering_quality",
            "status": "open",
            "evidence": f"src/v5 has {src_count} Python runners and tests has {test_count} test modules; unittest requires PYTHONPATH=src; no .github/workflows directory is present.",
            "risk": "Clean-machine verification and regression detection depend on local shell knowledge; full-suite runtime is not tiered.",
            "repair": "Add one documented test launcher plus fast/standard/extended test markers or manifests, pin core dependencies, and add CI for fast tests and contract checks.",
        },
        {
            "finding_id": "WF_P1_WORKTREE_AND_ARTIFACT_PROVENANCE_GAP",
            "priority": "P1",
            "stage": "reproducibility",
            "status": "open",
            "evidence": f"Current git status has {dirty['modified']} modified and {dirty['untracked']} untracked paths.",
            "risk": "It is difficult to distinguish source changes, generated artifacts, user files and the exact code that produced a result.",
            "repair": "Define artifact roots, ignore generated bulky outputs, commit source/config/test changes in bounded batches, and write a run manifest with code commit, input hashes and output hashes.",
        },
        {
            "finding_id": "WF_P2_EXPERIMENT_CATALOG_AND_TERMINOLOGY_DRIFT",
            "priority": "P2",
            "stage": "research_governance",
            "status": "open",
            "evidence": "V5c through V5j contain many independent current packets, while active V5f is not in the central registry and older baseline artifacts remain accessible.",
            "risk": "Terms such as diagnostic, candidate, platform replication and forward paper can be mixed across branches.",
            "repair": "Introduce an experiment catalog keyed by immutable experiment_id, hypothesis_id, baseline_id, data scope, layer, status and supersedes relation; render the PM queue from that catalog.",
        },
    ]


def _state_matrix(context: dict[str, Any], protocol: dict[str, Any], findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_stage = {row["stage"]: row for row in findings}
    return [
        {"workflow_stage": "research_hypothesis", "target": "Financially explainable, pre-registered hypothesis", "state": "operating", "evidence": "V5 context and agent protocol define research/quant/engineering separation."},
        {"workflow_stage": "pit_data", "target": "Timestamped source panel and visibility audit", "state": "partial_with_real_boundary", "evidence": by_stage["independent_validation"]["evidence"]},
        {"workflow_stage": "formal_backtest", "target": "Fixed 2021-05-01 to 2026-05-31 benchmarked replay", "state": "operating", "evidence": "Repaired baseline and V5f mainline have reproducible local and platform-result artifacts."},
        {"workflow_stage": "platform_replication", "target": "Exact frozen source/config/target parity", "state": "partial", "evidence": by_stage["platform_replication"]["evidence"]},
        {"workflow_stage": "execution_engineering", "target": "Filled orders, fees, cash, lots and non-fill behavior reconcile", "state": "partial", "evidence": by_stage["execution_engineering"]["evidence"]},
        {"workflow_stage": "paper_trading", "target": "Official signal, target, actual holdings and receipt close each cycle", "state": "blocked_pending_next_official_target", "evidence": by_stage["paper_trading"]["evidence"]},
        {"workflow_stage": "governance_registry", "target": "One current model/decision source", "state": "stale", "evidence": by_stage["governance"]["evidence"]},
        {"workflow_stage": "test_and_provenance", "target": "Clean-machine tests, CI and immutable run manifests", "state": "partial", "evidence": by_stage["engineering_quality"]["evidence"]},
    ]


def _repair_queue(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"priority": row["priority"], "finding_id": row["finding_id"], "repair_task": row["repair"], "exit_condition": _exit_condition(row["finding_id"]), "may_change_v57f": False, "may_mark_accepted": False}
        for row in findings
    ]


def _exit_condition(finding_id: str) -> str:
    conditions = {
        "WF_P0_CENTRAL_STATUS_REGISTRY_STALE": "Active-model registry lists repaired baseline and V5f mainline; automated reference audit passes.",
        "WF_P0_FORWARD_TARGET_AND_RECEIPT_GAP": "One official rebalance has target, accepted local receipt, target-versus-position reconciliation and closeout report.",
        "WF_P0_PLATFORM_CONTRACT_INCOMPLETE": "Platform source/config/target hashes are archived and parity residuals are classified without unexplained material drift.",
        "WF_P0_PRE2021_EXACT_PIT_BOUNDARY": "Either exact PIT targets are certified or the branch is formally limited to forward evidence with no proxy claim.",
        "WF_P1_CASH_PATH_NOT_EXECUTABLE": "Strict same-sleeve cash reconciliation passes under the approved partial-buy policy.",
        "WF_P1_REPRODUCIBLE_TEST_ENTRYPOINT_GAP": "Fast suite runs from a clean environment using one command and CI records its result.",
        "WF_P1_WORKTREE_AND_ARTIFACT_PROVENANCE_GAP": "Source/config/test changes and generated artifacts are separated with a run manifest linked to a commit.",
        "WF_P2_EXPERIMENT_CATALOG_AND_TERMINOLOGY_DRIFT": "Every active branch has one canonical experiment record and PM queue is generated from it.",
    }
    return conditions[finding_id]


def _manifest(root: Path, paths: list[Path]) -> list[dict[str, Any]]:
    return [{"path": str(path), "exists": (root / path).exists(), "bytes": (root / path).stat().st_size if (root / path).exists() else 0} for path in paths]


def _report(context: dict[str, Any], findings: list[dict[str, Any]], state: list[dict[str, Any]], repair: list[dict[str, Any]]) -> str:
    lines = [
        "# V5 Strategy Development Workflow Audit",
        "",
        "## Initial Objective",
        context["mission"],
        "",
        "## Overall Reading",
        "V5 has the intended research-to-paper-trading architecture, but its current bottleneck is operational closure rather than a lack of model ideas. The mainline remains a forward/paper candidate, not an accepted strategy.",
        "",
        "## Workflow State",
        "| Stage | State | Evidence |",
        "|---|---|---|",
    ]
    lines.extend(f"| {row['workflow_stage']} | {row['state']} | {row['evidence']} |" for row in state)
    lines.extend(["", "## Findings"])
    for row in findings:
        lines.extend([f"### {row['finding_id']}", f"- Priority: `{row['priority']}`", f"- Evidence: {row['evidence']}", f"- Risk: {row['risk']}", f"- Repair: {row['repair']}", ""])
    lines.extend(["## Repair Order"])
    lines.extend(f"{index}. `{row['finding_id']}`: {row['exit_condition']}" for index, row in enumerate(repair, start=1))
    lines.extend(["", "## Guardrails", "- Keep the formal backtest window at 2021-05-01 through 2026-05-31.", "- Do not use a proxy pool to label a pre-2021 result as exact V57f validation.", "- No workflow repair changes V57f or marks a strategy accepted."])
    return "\n".join(lines) + "\n"


def _rules() -> str:
    return """# Workflow Audit Rules\n\n1. This audit evaluates process maturity, not model return.\n2. The formal backtest window is fixed at 2021-05-01 through 2026-05-31.\n3. Pre-2021 evidence is independent validation only and cannot use proxy target substitution.\n4. No audit outcome may modify V57f, place an order, start a platform backtest, or mark a strategy accepted.\n"""


def _git_status(root: Path) -> dict[str, int]:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=False)
    lines = result.stdout.splitlines()
    return {"modified": sum(not line.startswith("??") for line in lines), "untracked": sum(line.startswith("??") for line in lines)}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ["empty"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    print(json.dumps(run_v5k_strategy_development_workflow_audit(), ensure_ascii=False, indent=2))

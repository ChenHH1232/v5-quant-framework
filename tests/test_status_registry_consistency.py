from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "governance" / "status_registry.json"


def _registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8-sig"))


def test_status_registry_evidence_paths_exist() -> None:
    missing: list[str] = []
    for strategy in _registry().get("strategies", []):
        strategy_id = strategy.get("strategy_id", "<unknown>")
        for path_text in strategy.get("evidence_paths", []):
            path = ROOT / path_text
            if not path.exists():
                missing.append(f"{strategy_id}: {path_text}")

    assert missing == []


def test_status_registry_required_strategy_fields_are_present() -> None:
    required = {"strategy_id", "sector", "current_status", "not_status", "experiment_layer", "evidence_paths", "blockers", "next_gate"}
    missing: list[str] = []
    for strategy in _registry().get("strategies", []):
        absent = sorted(required - set(strategy))
        if absent:
            missing.append(f"{strategy.get('strategy_id', '<unknown>')}: {', '.join(absent)}")

    assert missing == []


def test_accepted_strategy_requires_platform_and_paper_evidence() -> None:
    violations: list[str] = []
    for strategy in _registry().get("strategies", []):
        statuses = set(strategy.get("current_status", []))
        evidence = "\n".join(strategy.get("evidence_paths", []))
        has_platform = "platform" in evidence or "platform_replication_passed" in statuses
        has_paper = "paper" in evidence or "paper_trading" in statuses or "paper_trading_started" in statuses
        if "accepted_strategy" in statuses and not (has_platform and has_paper):
            violations.append(str(strategy.get("strategy_id")))

    assert violations == []

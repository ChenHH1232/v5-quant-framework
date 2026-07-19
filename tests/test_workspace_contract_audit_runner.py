from __future__ import annotations

import json
from pathlib import Path

from v5.workspace_contract_audit_runner import run_workspace_contract_audit


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _valid_config() -> dict:
    return {
        "schema_version": 1,
        "project": "basket",
        "sectors": [
            {
                "sector_id": "utilities",
                "strategy_id": "utilities",
                "panel_csv": "panel.csv",
                "price_csv": "price.csv",
                "dividend_csv": "dividend.csv",
            }
        ],
        "signals": {"factors": [{"name": "ocf", "direction": "higher_is_better"}], "scoring": {"method": "weighted_composite"}},
        "portfolio": {"target_count": 5},
    }


def test_workspace_contract_audit_passes_clean_minimal_workspace(tmp_path: Path) -> None:
    _write_json(tmp_path / "config" / "basket.json", _valid_config())
    evidence = tmp_path / "docs" / "evidence.md"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text("ok", encoding="utf-8")
    _write_json(
        tmp_path / "docs" / "governance" / "status_registry.json",
        {
            "schema_version": 1,
            "updated_at": "2026-07-20",
            "governance_rule": "Evidence first.",
            "strategies": [
                {
                    "strategy_id": "candidate",
                    "sector": "utilities",
                    "current_status": ["formal_strategy_candidate"],
                    "not_status": ["accepted_strategy"],
                    "experiment_layer": "research_pit_validation",
                    "evidence_paths": ["docs/evidence.md"],
                    "blockers": [],
                    "next_gate": "paper_trading",
                }
            ],
        },
    )

    result = run_workspace_contract_audit(root=tmp_path, out_dir=tmp_path / "out", registry_path=Path("docs/governance/status_registry.json"))

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert result.status == "passed"
    assert summary["blocker_count"] == 0
    assert summary["config_validation"]["passed_count"] == 1


def test_workspace_contract_audit_blocks_missing_registry_evidence(tmp_path: Path) -> None:
    _write_json(tmp_path / "config" / "basket.json", _valid_config())
    _write_json(
        tmp_path / "docs" / "governance" / "status_registry.json",
        {
            "schema_version": 1,
            "updated_at": "2026-07-20",
            "governance_rule": "Evidence first.",
            "strategies": [
                {
                    "strategy_id": "candidate",
                    "sector": "utilities",
                    "current_status": ["formal_strategy_candidate"],
                    "not_status": ["accepted_strategy"],
                    "experiment_layer": "research_pit_validation",
                    "evidence_paths": ["docs/missing.md"],
                    "blockers": [],
                    "next_gate": "paper_trading",
                }
            ],
        },
    )

    result = run_workspace_contract_audit(root=tmp_path, out_dir=tmp_path / "out", registry_path=Path("docs/governance/status_registry.json"))

    assert result.status == "blocked"
    assert result.blocker_count == 1

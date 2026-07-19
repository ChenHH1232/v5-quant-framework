from __future__ import annotations

import json
from pathlib import Path

from v5.platform_export_intake_runner import check_platform_export_intake


def _write_manifest(path: Path, export_dir: Path) -> Path:
    payload = {
        "strategy_id": "test_strategy",
        "intake_dir": str(export_dir),
        "required_exports": [
            {"name": "daily_result", "target_path": str(export_dir / "result.csv"), "required_for": "daily"},
            {"name": "transaction_detail", "target_path": str(export_dir / "transaction.csv"), "required_for": "transactions"},
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_check_platform_export_intake_waits_for_missing_exports(tmp_path: Path) -> None:
    export_dir = tmp_path / "pending"
    export_dir.mkdir()
    manifest = _write_manifest(tmp_path / "manifest.json", export_dir)

    result = check_platform_export_intake(manifest, tmp_path / "out")

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert result.status == "waiting_for_joinquant_exports"
    assert summary["missing_count"] == 2
    assert summary["ready_count"] == 0


def test_check_platform_export_intake_ready_when_files_exist(tmp_path: Path) -> None:
    export_dir = tmp_path / "pending"
    export_dir.mkdir()
    (export_dir / "result.csv").write_text("date,ret\n2026-01-01,0\n", encoding="utf-8")
    (export_dir / "transaction.csv").write_text("date,code\n2026-01-01,000001.XSHE\n", encoding="utf-8")
    manifest = _write_manifest(tmp_path / "manifest.json", export_dir)

    result = check_platform_export_intake(manifest, tmp_path / "out")

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert result.status == "ready_for_platform_attribution"
    assert summary["ready_count"] == 2
    assert summary["missing_count"] == 0


def test_check_platform_export_intake_respects_user_deferred(tmp_path: Path) -> None:
    export_dir = tmp_path / "pending"
    export_dir.mkdir()
    manifest = _write_manifest(tmp_path / "manifest.json", export_dir)

    result = check_platform_export_intake(manifest, tmp_path / "out", user_deferred=True)

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert result.status == "platform_test_deferred_by_user_waiting_for_exports"
    assert summary["allowed_next_action"] == "continue_local_paper_preflight_and_do_not_run_platform_attribution"

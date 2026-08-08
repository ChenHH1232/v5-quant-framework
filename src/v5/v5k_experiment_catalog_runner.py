from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v5.v5k_historical_operation_boundary import historical_operation_audit


OUT = Path("v5k_experiment_catalog") / "current"
CATALOG = Path("config") / "v5_experiment_catalog.json"


def run_v5k_experiment_catalog(root: Path = Path(".")) -> dict[str, Any]:
    boundary = historical_operation_audit("test_and_governance_repair_without_market_data", "2026-05-31", root)
    catalog = json.loads((root / CATALOG).read_text(encoding="utf-8-sig"))
    rows = catalog["experiments"]
    active = [row for row in rows if row["status"] == "primary_forward_paper_candidate_not_accepted"]
    out = root / OUT
    out.mkdir(parents=True, exist_ok=True)
    _write_csv(out / "v5_experiment_catalog.csv", rows)
    _write_csv(out / "v5_experiment_pm_queue.csv", [{"priority": "P0", "experiment_id": row["experiment_id"], "next_action": row["next_action"], "status": row["status"]} for row in rows])
    _write_csv(out / "v5_experiment_catalog_boundary_audit.csv", [boundary])
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5k_experiment_catalog",
        "status": "completed_catalog_for_new_governance_and_promotion_work",
        "experiment_count": len(rows),
        "active_mainline_count": len(active),
        "active_mainline": active[0]["experiment_id"] if active else "",
        "market_data_scope_end": catalog["market_data_scope_end"],
        "accepted": False,
        "live_trading_approved": False,
    }
    (out / "v5_experiment_catalog_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "v5_experiment_catalog_report.md").write_text(
        "# V5 Experiment Catalog\n\n"
        "- Canonical catalog applies to new governance and promotion work; it does not overwrite legacy research packets.\n"
        f"- Active mainline: `{summary['active_mainline']}`.\n"
        "- All entries remain non-accepted and non-live-approved.\n",
        encoding="utf-8",
    )
    return summary


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys); writer.writeheader(); writer.writerows(rows)


if __name__ == "__main__":
    print(json.dumps(run_v5k_experiment_catalog(), ensure_ascii=False, indent=2))

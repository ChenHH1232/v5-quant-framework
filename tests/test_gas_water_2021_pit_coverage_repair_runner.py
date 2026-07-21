from __future__ import annotations

import csv
import json

from v5.gas_water_2021_pit_coverage_repair_runner import REPAIR_DATE, repair_gas_water_2021_07_pit_coverage


def test_gas_water_2021_07_repair_restores_frozen_coverage(tmp_path) -> None:
    panel = repair_gas_water_2021_07_pit_coverage(out_dir=tmp_path)
    rows = list(csv.DictReader(panel.open(encoding="utf-8-sig", newline="")))
    date_rows = [row for row in rows if row["trade_date"] == REPAIR_DATE]
    repaired = [row for row in date_rows if row.get("business_purity_gate") == "passed_pit_repair_2021_07"]
    manifest = json.loads((tmp_path / "repair_manifest_2021_07.json").read_text(encoding="utf-8"))

    assert len(date_rows) == 32
    assert manifest["status"] == "coverage_contract_repaired"
    assert sorted(manifest["added_codes"]) == ["600008.XSHG", "600461.XSHG", "600635.XSHG", "601139.XSHG"]
    assert all(row["gas_water_visible_date"] <= REPAIR_DATE for row in repaired)

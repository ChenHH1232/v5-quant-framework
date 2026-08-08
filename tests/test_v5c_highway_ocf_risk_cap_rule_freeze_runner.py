from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.v5c_highway_ocf_risk_cap_rule_freeze_runner import (
    FROZEN_RULE_ID,
    run_v5c_highway_ocf_risk_cap_rule_freeze,
)


class V5cHighwayOcfRiskCapRuleFreezeRunnerTest(unittest.TestCase):
    def test_runner_blocks_when_inputs_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = run_v5c_highway_ocf_risk_cap_rule_freeze(Path(tmp))

        self.assertEqual(summary["status"], "blocked_missing_required_inputs")
        self.assertGreater(summary["fatal_blocker_count"], 0)

    def test_runner_freezes_risk_cap_only_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_inputs(root)

            summary = run_v5c_highway_ocf_risk_cap_rule_freeze(root)

            self.assertEqual(summary["status"], "completed_rule_freeze_packet")
            self.assertEqual(summary["frozen_rule_id"], FROZEN_RULE_ID)
            self.assertFalse(summary["accepted"])
            self.assertFalse(summary["v57f_core_modified"])
            self.assertFalse(summary["parameter_scan_used"])

            out = root / "v5c_highway_ocf_risk_cap_rule_freeze" / "current"
            with (out / "v5c_highway_ocf_risk_cap_frozen_rule.csv").open(
                "r", encoding="utf-8-sig", newline=""
            ) as handle:
                frozen = list(csv.DictReader(handle))[0]
            self.assertEqual(frozen["frozen_rule_id"], FROZEN_RULE_ID)
            self.assertEqual(frozen["rule_type"], "risk_cap_only")
            self.assertEqual(frozen["capex_fcf_policy"], "excluded from v1 model input; original-page review queue only")

            with (out / "v5c_highway_ocf_risk_cap_pm_gate_decision.csv").open(
                "r", encoding="utf-8-sig", newline=""
            ) as handle:
                decision = list(csv.DictReader(handle))[0]
            self.assertEqual(
                decision["pm_gate_decision"],
                "freeze_highway_ocf_risk_cap_v1_ready_for_limited_engineering_not_accepted",
            )
            self.assertEqual(decision["capex_fcf_model_use"], "False")


def _seed_inputs(root: Path) -> None:
    spec = root / "v5c_infra_ocf_quality_fixed_rule_quant_spec" / "current"
    capex = root / "v5c_infra_capex_original_statement_extraction" / "current"
    sidecar = root / "v5c_sidecar_observation_enhancement" / "current"
    cycle = root / "v5c_cycle_sector_data_gate_queue" / "current"
    for path in [spec, capex, sidecar, cycle]:
        path.mkdir(parents=True, exist_ok=True)

    (spec / "v5c_infra_ocf_quality_fixed_rule_spec_summary.json").write_text(
        json.dumps(
            {
                "pm_gate_decision": "admit_highway_ocf_quality_risk_cap_to_quant_spec_not_accepted",
                "accepted": False,
            }
        ),
        encoding="utf-8",
    )
    _write_csv(
        spec / "v5c_infra_ocf_quality_rule_spec.csv",
        [
            {
                "rule_id": "highway_ocf_yield_quality_guard",
                "sector_id": "highway_infrastructure",
                "rule_type": "risk_cap_only",
                "status": "admit_to_fixed_rule_quant_spec_not_engineering_backtest",
            }
        ],
    )
    _write_csv(
        spec / "v5c_infra_ocf_quality_pre2021_evidence_snapshot.csv",
        [
            {
                "sector_id": "highway_infrastructure",
                "factor_id": "operating_cash_flow_yield",
                "preview_status": "pre2021_positive_needs_formal_fixed_rule_review_not_accepted",
            },
            {
                "sector_id": "highway_infrastructure",
                "factor_id": "operating_cash_flow_to_net_profit",
                "preview_status": "pre2021_positive_needs_formal_fixed_rule_review_not_accepted",
            },
        ],
    )
    (capex / "v5c_infra_capex_original_statement_summary.json").write_text(
        json.dumps({"pm_gate_decision": "capex_fcf_data_gate_ready_for_fixed_rule_review"}),
        encoding="utf-8",
    )
    _write_csv(
        capex / "v5c_infra_capex_strict_panel.csv",
        [
            {
                "sector_id": "highway_infrastructure",
                "trade_date": "2020-07-01",
                "code": "600035.XSHG",
                "cashflow_report_period": "2020-03-31",
                "capex_fcf_status": "missing_pit_original_statement_extraction",
                "free_cash_flow_yield": "",
                "capex_burden": "",
            }
        ],
    )
    _write_csv(capex / "v5c_infra_capex_blockers.csv", [])
    _write_csv(
        sidecar / "v5c_sidecar_observation_enhancement_queue.csv",
        [{"sector_id": "gas_water_operators", "allowed_action": "observe", "blocked_action": "accepted"}],
    )
    _write_csv(
        cycle / "v5c_cycle_sector_data_gate_queue.csv",
        [{"sector_id": "cement", "required_state_data": "regional_price", "blocked_action": "backtest_before_PIT_state_gate"}],
    )


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()

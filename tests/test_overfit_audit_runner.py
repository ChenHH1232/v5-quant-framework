from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.overfit_audit_runner import run_overfit_audit


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _base_spec() -> dict:
    return {
        "meta": {"strategy_id": "audit_test", "status": "formal_strategy_candidate"},
        "universe": {"point_in_time": True},
        "signals": {
            "factors": [
                {"name": "factor_a", "as_of": "announcement_date"},
                {"name": "factor_b", "as_of": "trade_date_lagged"},
            ],
            "scoring": {"normalization_scope": "rebalance_cross_section"},
        },
        "portfolio": {"selection_count": 2},
        "validation": {"method": "rolling"},
    }


class OverfitAuditRunnerTests(unittest.TestCase):
    def test_future_visible_date_blocks_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = root / "spec.json"
            panel = root / "panel.csv"
            _write_json(spec, _base_spec())
            _write_csv(
                panel,
                [
                    {
                        "trade_date": "2025-04-01",
                        "code": "A",
                        "factor_visible_date": "2025-04-02",
                        "universe_visible_date": "2025-03-01",
                    }
                ],
            )

            result = run_overfit_audit(spec, root / "out", panel_path=panel)
            summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
            checks = result.checks_path.read_text(encoding="utf-8")

            self.assertEqual(summary["status"], "blocked")
            self.assertIn("panel_visible_dates", checks)
            self.assertIn("blocker", checks)

    def test_full_sample_normalization_blocks_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = _base_spec()
            spec["signals"]["scoring"]["normalization_scope"] = "full_sample"
            spec_path = root / "spec.json"
            _write_json(spec_path, spec)

            result = run_overfit_audit(spec_path, root / "out")
            checks = result.checks_path.read_text(encoding="utf-8")

            self.assertEqual(result.blocker_count, 1)
            self.assertIn("Full-sample normalization is a future function.", checks)

    def test_missing_optional_inputs_require_review_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_path = root / "spec.json"
            _write_json(spec_path, _base_spec())

            result = run_overfit_audit(spec_path, root / "out")
            summary = json.loads(result.summary_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["status"], "needs_review")
            self.assertGreater(summary["needs_review_count"], 0)
            self.assertEqual(summary["blocker_count"], 0)

    def test_random_window_stability_runs_when_daily_returns_supplied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_path = root / "spec.json"
            daily = root / "daily.csv"
            signals = root / "signals.csv"
            _write_json(spec_path, _base_spec())
            _write_csv(
                daily,
                [
                    {
                        "trade_date": f"2025-01-{day:02d}",
                        "strategy_return": "0.001",
                        "benchmark_return": "0.0002",
                        "experiment_layer": "research_pit_validation",
                    }
                    for day in range(1, 11)
                ],
            )
            _write_csv(
                signals,
                [
                    {
                        "trade_date": "2025-01-01",
                        "state_visible_date": "2024-12-31",
                        "selected_count": "2",
                        "case": "base",
                        "factor": "factor_a",
                    }
                ],
            )

            result = run_overfit_audit(
                spec_path,
                root / "out",
                daily_returns_csv=daily,
                rebalance_signals_csv=signals,
                min_window_days=3,
                random_windows=5,
            )
            checks = result.checks_path.read_text(encoding="utf-8")

            self.assertIn("daily_return_random_windows", checks)
            self.assertIn("execution_time_shift_proxy", checks)
            self.assertIn("parameter_perturbation_from_signals", checks)

    def test_accepted_strategy_marker_blocks_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = _base_spec()
            spec["meta"]["status"] = "accepted_strategy"
            spec_path = root / "spec.json"
            _write_json(spec_path, spec)

            result = run_overfit_audit(spec_path, root / "out")
            checks = result.checks_path.read_text(encoding="utf-8")

            self.assertGreaterEqual(result.blocker_count, 1)
            self.assertIn("accepted_status_guard", checks)

    def test_latest_visible_ev_market_cap_as_of_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = _base_spec()
            spec["signals"]["factors"] = [
                {
                    "name": "price_to_embedded_value",
                    "as_of": "trade_date_market_cap_and_latest_visible_ev",
                }
            ]
            spec_path = root / "spec.json"
            _write_json(spec_path, spec)

            result = run_overfit_audit(spec_path, root / "out")
            checks = result.checks_path.read_text(encoding="utf-8")

            self.assertNotIn('"unsafe_factors": "price_to_embedded_value"', checks)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.v5c_bank_special_mention_pre2021_runner import (
    BANK_PANEL,
    OUT_DIR,
    Pre2021Config,
    _parse_special_mention_line,
    run,
)


class V5cBankSpecialMentionPre2021RunnerTest(unittest.TestCase):
    def test_parse_special_mention_line_extracts_ratio_after_amount(self) -> None:
        parsed = _parse_special_mention_line("\u5173\u6ce8\u7c7b 117,063 2.58 12.29")
        self.assertIsNotNone(parsed)
        self.assertAlmostEqual(float(parsed["special_mention_loan_ratio_pct"]), 2.58)

    def test_runner_outputs_pre2021_packet_without_backtest_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fixture(root)

            summary_path = run(
                root,
                Pre2021Config(
                    download_missing=False,
                    reuse_cached_manifest=True,
                    reuse_cached_extraction=True,
                ),
            )
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["status"], "completed_pre2021_train_test_packet")
            self.assertFalse(summary["formal_backtest_used_as_validation"])
            self.assertFalse(summary["accepted"])
            self.assertFalse(summary["v57f_core_modified"])

            out = root / OUT_DIR
            decision = _read_csv(out / "v5c_bank_special_mention_pre2021_pm_gate_decision.csv")
            self.assertEqual(decision[0]["accepted"], "False")
            reconciliation = _read_csv(out / "v5c_bank_special_mention_pre2021_backtest_scope_reconciliation.csv")
            backtest_row = next(row for row in reconciliation if row["window"] == "2021-05-01_to_2026-05-31")
            self.assertEqual(backtest_row["may_promote_from_this_window"], "False")


def _write_fixture(root: Path) -> None:
    split = root / "v5_sample_split_governance_correction" / "current"
    split.mkdir(parents=True)
    (split / "v5_sample_split_rules.md").write_text("fixture", encoding="utf-8")

    preview = root / "v5f_pre2021_repaired_multisleeve_data_gate" / "current"
    preview.mkdir(parents=True)
    _write_csv(
        preview / "v5f_pre2021_candidate_signal_preview.csv",
        [
            {"preview_date": "2020-04-01", "code": "600000.XSHG", "sector_id": "bank", "selected_rank": 1, "score": 1},
            {"preview_date": "2020-04-01", "code": "600001.XSHG", "sector_id": "bank", "selected_rank": 2, "score": 1},
            {"preview_date": "2020-04-01", "code": "600002.XSHG", "sector_id": "bank", "selected_rank": 3, "score": 1},
        ],
    )

    backtest = root / "v5c_bank_power_single_factor_cross_section_test" / "current"
    backtest.mkdir(parents=True)
    (backtest / "v5c_bank_power_single_factor_summary.json").write_text(
        json.dumps(
            {
                "best_factor": "bank_special_mention_loan",
                "best_version": "single_factor_bank_special_mention_loan_overlay_10pct",
                "best_delta_return_pct_points_vs_v5f_primary": 0.68,
            }
        ),
        encoding="utf-8",
    )

    panel_path = root / BANK_PANEL
    panel_path.parent.mkdir(parents=True)
    _write_csv(
        panel_path,
        [
            _panel("2020-04-01", "600000.XSHG", 0.20),
            _panel("2020-04-01", "600001.XSHG", 0.10),
            _panel("2020-04-01", "600002.XSHG", -0.10),
            _panel("2020-07-01", "600000.XSHG", 0.15),
            _panel("2020-07-01", "600001.XSHG", 0.05),
            _panel("2020-07-01", "600002.XSHG", -0.05),
        ],
    )

    out = root / OUT_DIR
    out.mkdir(parents=True)
    _write_csv(
        out / "v5c_bank_special_mention_pre2021_cninfo_manifest.csv",
        [
            _manifest("600000.XSHG"),
            _manifest("600001.XSHG"),
            _manifest("600002.XSHG"),
        ],
    )
    _write_csv(
        out / "v5c_bank_special_mention_pre2021_extraction_panel.csv",
        [
            _extract("600000.XSHG", 1.0),
            _extract("600001.XSHG", 2.0),
            _extract("600002.XSHG", 3.0),
        ],
    )


def _panel(date: str, code: str, future_return: float) -> dict[str, object]:
    return {
        "trade_date": date,
        "code": code,
        "close": 10,
        "price_adjustment": "fixture",
        "next_trade_date": "2020-07-01",
        "price_return": future_return,
        "dividend_return": 0,
        "total_return": future_return,
        "future_return": future_return,
        "return_source": "fixture",
        "benchmark_return": 0,
        "benchmark_source": "fixture",
    }


def _manifest(code: str) -> dict[str, object]:
    return {
        "industry": "bank",
        "code": code,
        "cn_code": code.split(".")[0],
        "exchange": code.split(".")[1],
        "sec_name": "fixture",
        "org_id": "fixture",
        "announcement_title": "fixture annual report",
        "announcement_date": "2020-03-30",
        "report_period": "2019-12-31",
        "pit_visible_date": "2020-03-30",
        "pdf_url": "",
        "source": "fixture",
        "accepted": False,
    }


def _extract(code: str, ratio: float) -> dict[str, object]:
    return {
        "code": code,
        "sec_name": "fixture",
        "report_period": "2019-12-31",
        "announcement_date": "2020-03-30",
        "pit_visible_date": "2020-03-30",
        "special_mention_loan_ratio_pct": ratio,
        "special_mention_loan_amount": 1000,
        "page_number": 1,
        "sample_context": "fixture",
        "local_pdf_path": "",
        "extraction_status": "pass_extracted_from_original_pdf_text",
        "pit_source": "fixture",
        "accepted": False,
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()

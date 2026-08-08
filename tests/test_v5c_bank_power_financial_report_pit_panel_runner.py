from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from v5.v5c_bank_power_financial_report_pit_panel_runner import _metric_value, _review_candidates, MetricRule, run
from v5.v5f_structural_rough_screen_runner import PRICE_DIR, REPAIRED_RUN


class V5cBankPowerFinancialReportPitPanelRunnerTest(unittest.TestCase):
    def test_metric_value_parser_rejects_years_and_keeps_percent(self) -> None:
        rule = MetricRule("net_interest_margin_pct", "bank", "net_interest_margin", ("净息差",), "%", 0, 8)
        value, token, unit = _metric_value(
            {
                "value_candidates": "2025;1.78%;1.87%;-0.09个百分点",
                "sample_context": "净息差 1.78% 同比下降",
            },
            rule,
        )
        self.assertEqual(value, 1.78)
        self.assertEqual(token, "1.78%")
        self.assertEqual(unit, "explicit_unit")

    def test_review_candidates_requires_visible_original_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "fixture.txt"
            pdf.write_text("净息差 2.10%", encoding="utf-8")
            rows = _review_candidates(
                [
                    {
                        "industry": "bank",
                        "code": "600000.XSHG",
                        "sec_name": "浦发银行",
                        "report_period": "2024-12-31",
                        "announcement_date": "2025-03-30",
                        "pit_visible_date": "2025-03-30",
                        "field": "net_interest_margin",
                        "keyword": "净息差",
                        "page_number": "1",
                        "value_candidates": "2.10%",
                        "sample_context": "净息差 2.10%",
                        "local_pdf_path": str(pdf),
                        "pdf_url": "",
                    }
                ]
            )
            self.assertEqual(rows[0]["review_status"], "automated_original_page_review_pass")
            self.assertEqual(rows[0]["reviewed_value"], "2.1")

    def test_runner_outputs_review_only_factor_retest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fixture(root)
            summary_path = run(root)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["status"], "completed_financial_report_pit_panel_and_factor_retest")
            self.assertFalse(summary["accepted"])
            self.assertFalse(summary["v57f_core_modified"])

            out = root / "v5c_bank_power_financial_report_pit_panel" / "current"
            panel = _read_csv(out / "v5c_bank_power_rebalance_pit_field_panel.csv")
            self.assertEqual(panel[0]["matched_report_period"], "2024-12-31")

            governance = _read_csv(out / "v5c_bank_power_financial_report_governance_audit.csv")
            preserved = next(row for row in governance if row["audit_id"] == "sleeve_weight_preserved")
            self.assertEqual(preserved["status"], "pass")


def _write_fixture(root: Path) -> None:
    batch = root / "v5c_bank_power_financial_report_batch_extraction" / "current"
    batch.mkdir(parents=True)
    pdf = batch / "fixture.txt"
    pdf.write_text("净息差 2.10% 不良贷款率 1.00% 拨备覆盖率 250.00% 核心一级资本充足率 10.50%", encoding="utf-8")
    bank_candidates = [
        _candidate("bank", "600000.XSHG", "浦发银行", "2024-12-31", "2025-03-30", "net_interest_margin", "净息差", "2.10%", pdf),
        _candidate("bank", "600000.XSHG", "浦发银行", "2024-12-31", "2025-03-30", "asset_quality", "不良贷款率", "1.00%", pdf),
        _candidate("bank", "600000.XSHG", "浦发银行", "2024-12-31", "2025-03-30", "asset_quality", "拨备覆盖率", "250.00%", pdf),
        _candidate("bank", "600000.XSHG", "浦发银行", "2024-12-31", "2025-03-30", "capital_buffer", "核心一级资本充足率", "10.50%", pdf),
        _candidate("bank", "600001.XSHG", "银行B", "2024-12-31", "2025-03-30", "net_interest_margin", "净息差", "1.50%", pdf),
    ]
    power_candidates = [
        _candidate("utilities_electricity", "600011.XSHG", "华能国际", "2024-12-31", "2025-03-30", "utilization_hours", "利用小时", "4200小时", pdf),
        _candidate("utilities_electricity", "600012.XSHG", "电力B", "2024-12-31", "2025-03-30", "utilization_hours", "利用小时", "3200小时", pdf),
    ]
    _write_csv(batch / "v5c_bank_financial_report_field_candidates.csv", bank_candidates)
    _write_csv(batch / "v5c_power_financial_report_field_candidates.csv", power_candidates)

    price_dir = root / PRICE_DIR
    price_dir.mkdir(parents=True)
    price_rows = []
    for code, ret in {"600000.XSHG": 0.10, "600001.XSHG": 0.00, "600011.XSHG": 0.08, "600012.XSHG": 0.00}.items():
        price_rows.append({"date": "2025-04-30", "code": code, "close": 10.0})
        price_rows.append({"date": "2025-05-01", "code": code, "close": 10.0 * (1 + ret)})
    _write_csv(price_dir / "fixture_prices.csv", price_rows)

    run_dir = root / REPAIRED_RUN
    run_dir.mkdir(parents=True)
    signals = [
        _signal("2025-04-30", "600000.XSHG", "bank", 0.25),
        _signal("2025-04-30", "600001.XSHG", "bank", 0.25),
        _signal("2025-04-30", "600011.XSHG", "utilities_electricity", 0.25),
        _signal("2025-04-30", "600012.XSHG", "utilities_electricity", 0.25),
    ]
    _write_csv(run_dir / "rebalance_signals.csv", signals)
    _write_csv(
        run_dir / "daily_returns.csv",
        [
            {"trade_date": "2025-04-30", "strategy_return": 0.0, "strategy_nav": 1.0},
            {"trade_date": "2025-05-01", "strategy_return": 0.0, "strategy_nav": 1.0},
        ],
    )
    rough = root / "v5f_structural_rough_screen" / "current"
    rough.mkdir(parents=True)
    primary = [
        {
            "version_id": "internal_subsleeve_mom12_70_30",
            "family": "fixture",
            "rebalance_date": row["trade_date"],
            "code": row["code"],
            "sleeve": row["sector_id"],
            "base_target_weight": row["target_weight"],
            "target_weight": row["target_weight"],
            "weight_delta": 0.0,
            "bucket": "fixture",
            "sleeve_weight_preserved": True,
            "new_stock_selected": False,
            "accepted": False,
        }
        for row in signals
    ]
    _write_csv(rough / "v5f_structural_rough_screen_weights.csv", primary)


def _candidate(industry: str, code: str, name: str, period: str, date: str, field: str, keyword: str, value: str, path: Path) -> dict[str, str]:
    return {
        "industry": industry,
        "code": code,
        "sec_name": name,
        "report_period": period,
        "announcement_date": date,
        "pit_visible_date": date,
        "field": field,
        "keyword": keyword,
        "page_number": "1",
        "hit_index": "1",
        "value_candidates": value,
        "sample_context": f"{keyword} {value}",
        "local_pdf_path": str(path),
        "pdf_url": "",
        "candidate_status": "candidate_needs_original_review",
    }


def _signal(date: str, code: str, sleeve: str, weight: float) -> dict[str, object]:
    return {
        "trade_date": date,
        "code": code,
        "sector_id": sleeve,
        "strategy_id": "fixture",
        "selected_rank": 1,
        "selected_count": 4,
        "target_weight": weight,
        "score": 1,
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

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from v5.data_runner import collect_panel_from_v4_raw, write_collection_manifest
from v5.daily_backtest import _defensive_state
from v5.bank_quality_date_alignment_runner import align_bank_quality_dates
from v5.credential_loader import load_tushare_token
from v5.joinquant_availability_runner import build_joinquant_availability_proxy
from v5.benchmark_runner import _normalize_benchmark_row
from v5.dividend_runner import _normalize_akshare_dividend_row
from v5.joinquant_pit_panel_runner import _latest_visible_bank_quality, _load_bank_quality_snapshots
import v5.joinquant_real_data_runner as joinquant_real_data_runner
from v5.local_backtest import BacktestOptions, run_local_backtest
from v5.sector_rank_panel_runner import build_sector_rank_panel
from v5.utilities_daily_backtest_runner import check_utilities_daily_backtest_ready, run_utilities_daily_joinquant_like_backtest
from v5.utilities_demand_state_validation_runner import run_utilities_demand_state_validation
import v5.utilities_external_state_runner as utilities_external_state_runner
from v5.utilities_external_state_runner import (
    collect_utilities_external_state,
    validate_utilities_external_state,
    write_utilities_external_state_template,
)
from v5.utilities_pit_panel_runner import _interest_coverage, _market_cap_cny, _ratio
from v5.validation_runner import validate_panel
from v5.v4_legacy_bank_quality_runner import collect_v4_legacy_bank_quality


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "examples" / "bank_value_15y_strategy.json"


class DataValidationRunnerTests(unittest.TestCase):
    def test_collection_plan_does_not_include_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = write_collection_manifest(SPEC, Path(tmp))
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))

        serialized = json.dumps(payload, ensure_ascii=False).lower()
        self.assertEqual(payload["mode"], "plan_only")
        self.assertIn("credential_policy", payload)
        self.assertNotIn("password_value", serialized)
        self.assertNotIn("secret_value", serialized)
        self.assertNotIn("token_value", serialized)

    def test_tushare_token_can_load_from_labeled_next_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "credentials.txt"
            path.write_text("Tushare Token:\nabc123\n", encoding="utf-8")
            token = load_tushare_token("MISSING_TUSHARE_TOKEN_ENV", path)

        self.assertEqual(token, "abc123")

    def test_utilities_factor_formulas_handle_units_and_missing_interest(self) -> None:
        self.assertEqual(_market_cap_cny(12.5), 1_250_000_000.0)
        self.assertAlmostEqual(_ratio(50.0, 200.0) or 0.0, 0.25)
        self.assertAlmostEqual(_interest_coverage(100.0, 80.0, None, 20.0) or 0.0, 5.0)
        self.assertIsNone(_interest_coverage(100.0, 80.0, None, 0.0))

    def test_sector_rank_panel_builds_group_percentile_scores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            panel = tmp_path / "panel.csv"
            self._write_csv(
                panel,
                ["trade_date", "code", "sub_industry", "pb"],
                [
                    {"trade_date": "2025-01-02", "code": "A", "sub_industry": "power", "pb": "0.5"},
                    {"trade_date": "2025-01-02", "code": "B", "sub_industry": "power", "pb": "1.0"},
                    {"trade_date": "2025-01-02", "code": "C", "sub_industry": "power", "pb": "2.0"},
                ],
            )
            config = tmp_path / "config.json"
            config.write_text('[{"input":"pb","output":"low_pb_score","direction":"lower_is_better"}]', encoding="utf-8")
            out_panel = build_sector_rank_panel(panel, tmp_path / "ranked", config, min_group_size=3)
            with out_panel.open("r", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

        scores = {row["code"]: float(row["low_pb_score"]) for row in rows}
        self.assertGreater(scores["A"], scores["B"])
        self.assertGreater(scores["B"], scores["C"])

    def test_utilities_external_state_template_is_not_pit_usable_until_filled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            template = write_utilities_external_state_template(Path(tmp))
            result = validate_utilities_external_state(template)

        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["pit_usable_count"], 0)
        self.assertGreater(len(result["missing_required"]), 0)

    def test_collect_utilities_external_state_writes_valid_panel_and_manifest(self) -> None:
        def fake_electricity_rows() -> list[dict[str, str]]:
            return [
                {
                    "visible_date": "2025-02-25",
                    "state_date": "2025-01-31",
                    "state_scope": "national",
                    "sub_industry": "all_power",
                    "metric": "electricity_consumption_yoy",
                    "value": "6.8",
                    "unit": "percent",
                    "source_name": "fake akshare",
                    "source_url": "https://example.test/akshare",
                    "source_publication_date": "2025-02-25",
                    "pit_usable": "true",
                    "review_status": "conservative_proxy",
                    "notes": "test row",
                }
            ]

        def fake_nea_rows() -> list[dict[str, str]]:
            return [
                {
                    "visible_date": "2025-01-21",
                    "state_date": "2024-12-31",
                    "state_scope": "national",
                    "sub_industry": "all_power",
                    "metric": "generation_utilization_hours_total",
                    "value": "3442",
                    "unit": "hours",
                    "source_name": "fake NEA",
                    "source_url": "https://example.test/nea",
                    "source_publication_date": "2025-01-21",
                    "pit_usable": "true",
                    "review_status": "source_anchored",
                    "notes": "test row",
                }
            ]

        original_electricity = utilities_external_state_runner._collect_society_electricity_rows
        original_nea = utilities_external_state_runner._manual_nea_state_rows
        utilities_external_state_runner._collect_society_electricity_rows = fake_electricity_rows
        utilities_external_state_runner._manual_nea_state_rows = fake_nea_rows
        try:
            with tempfile.TemporaryDirectory() as tmp:
                panel = collect_utilities_external_state(Path(tmp))
                result = validate_utilities_external_state(panel)
                manifest = json.loads((Path(tmp) / "collection_manifest.json").read_text(encoding="utf-8"))
                rows = self._read_csv(panel)
        finally:
            utilities_external_state_runner._collect_society_electricity_rows = original_electricity
            utilities_external_state_runner._manual_nea_state_rows = original_nea

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(result["pit_usable_count"], 2)
        self.assertEqual(manifest["dataset"], "utilities_external_state")
        self.assertEqual(manifest["validation"]["status"], "pass")
        self.assertEqual([row["metric"] for row in rows], ["generation_utilization_hours_total", "electricity_consumption_yoy"])

    def test_utilities_demand_state_validation_writes_model_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            panel = tmp_path / "panel.csv"
            state = tmp_path / "state.csv"
            self._write_csv(
                panel,
                [
                    "trade_date",
                    "code",
                    "future_return",
                    "low_price_to_book",
                    "operating_cash_flow_yield",
                    "dividend_yield",
                    "low_pb_subindustry_score",
                    "cashflow_yield_subindustry_score",
                ],
                [
                    {"trade_date": "2020-01-02", "code": "A", "future_return": "0.02", "low_price_to_book": "0.8", "operating_cash_flow_yield": "0.04", "dividend_yield": "0.02", "low_pb_subindustry_score": "0.8", "cashflow_yield_subindustry_score": "0.3"},
                    {"trade_date": "2020-01-02", "code": "B", "future_return": "0.04", "low_price_to_book": "1.2", "operating_cash_flow_yield": "0.08", "dividend_yield": "0.03", "low_pb_subindustry_score": "0.4", "cashflow_yield_subindustry_score": "0.9"},
                    {"trade_date": "2020-04-01", "code": "A", "future_return": "0.03", "low_price_to_book": "0.7", "operating_cash_flow_yield": "0.03", "dividend_yield": "0.02", "low_pb_subindustry_score": "0.9", "cashflow_yield_subindustry_score": "0.2"},
                    {"trade_date": "2020-04-01", "code": "B", "future_return": "0.01", "low_price_to_book": "1.4", "operating_cash_flow_yield": "0.09", "dividend_yield": "0.04", "low_pb_subindustry_score": "0.3", "cashflow_yield_subindustry_score": "0.8"},
                    {"trade_date": "2020-07-01", "code": "A", "future_return": "0.05", "low_price_to_book": "0.6", "operating_cash_flow_yield": "0.02", "dividend_yield": "0.01", "low_pb_subindustry_score": "0.9", "cashflow_yield_subindustry_score": "0.2"},
                    {"trade_date": "2020-07-01", "code": "B", "future_return": "0.00", "low_price_to_book": "1.5", "operating_cash_flow_yield": "0.10", "dividend_yield": "0.05", "low_pb_subindustry_score": "0.2", "cashflow_yield_subindustry_score": "0.9"},
                ],
            )
            self._write_csv(
                state,
                ["visible_date", "state_date", "metric", "value"],
                [
                    {"visible_date": "2020-01-01", "state_date": "2019-12-31", "metric": "electricity_consumption_yoy", "value": "3.0"},
                    {"visible_date": "2020-03-25", "state_date": "2020-02-29", "metric": "electricity_consumption_yoy", "value": "4.0"},
                    {"visible_date": "2020-06-25", "state_date": "2020-05-31", "metric": "electricity_consumption_yoy", "value": "8.0"},
                ],
            )

            report = run_utilities_demand_state_validation(panel, state, tmp_path / "validation", selection_count=1, min_history=2)
            summary = json.loads((report.parent / "demand_state_validation_summary.json").read_text(encoding="utf-8"))
            report_exists = report.exists()

        self.assertTrue(report_exists)
        self.assertEqual(summary["strategy_id"], "utilities_demand_state_v51e")
        self.assertEqual(summary["coverage"]["state_covered_dates"], 3)
        self.assertIn(summary["status"], {"preliminary_model_candidate", "needs_more_evidence"})

    def test_utilities_daily_backtest_runs_from_state_switch_signals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            spec = tmp_path / "spec.json"
            spec.write_text(
                json.dumps(
                    {
                        "meta": {"strategy_id": "utilities_demand_state_v51f_test"},
                        "portfolio": {"selection_count": 1},
                    }
                ),
                encoding="utf-8",
            )
            panel = tmp_path / "panel.csv"
            state = tmp_path / "state.csv"
            prices = tmp_path / "prices.csv"
            benchmark = tmp_path / "benchmark.csv"
            self._write_csv(
                panel,
                ["trade_date", "code", "dividend_yield", "operating_cash_flow_yield", "low_price_to_book", "future_return"],
                [
                    {"trade_date": "2021-07-01", "code": "A", "dividend_yield": "0.06", "operating_cash_flow_yield": "0.02", "low_price_to_book": "1.1", "future_return": "0.01"},
                    {"trade_date": "2021-07-01", "code": "B", "dividend_yield": "0.03", "operating_cash_flow_yield": "0.08", "low_price_to_book": "0.8", "future_return": "0.02"},
                ],
            )
            self._write_csv(
                state,
                ["visible_date", "state_date", "metric", "value"],
                [{"visible_date": "2021-06-25", "state_date": "2021-05-31", "metric": "electricity_consumption_yoy", "value": "3.0"}],
            )
            self._write_csv(
                prices,
                ["date", "code", "open", "close", "high_limit", "low_limit", "paused"],
                [
                    {"date": "2021-07-01", "code": "B", "open": "10", "close": "10", "high_limit": "11", "low_limit": "9", "paused": "0"},
                    {"date": "2021-07-02", "code": "B", "open": "10", "close": "10.5", "high_limit": "11", "low_limit": "9", "paused": "0"},
                ],
            )
            self._write_csv(
                benchmark,
                ["date", "code", "close"],
                [
                    {"date": "2021-07-01", "code": "utilities_benchmark", "close": "1000"},
                    {"date": "2021-07-02", "code": "utilities_benchmark", "close": "1005"},
                ],
            )

            readiness = check_utilities_daily_backtest_ready(panel, state, prices, benchmark, start_date="2021-07-01", end_date="2021-07-02")
            report = run_utilities_daily_joinquant_like_backtest(
                spec,
                panel,
                state,
                prices,
                benchmark,
                tmp_path / "out",
                benchmark_id="utilities_benchmark",
                options=BacktestOptions(start_date="2021-07-01", end_date="2021-07-02", execution_mode="joinquant_like", initial_cash=100000),
            )
            summary = json.loads((report.parent / "summary.json").read_text(encoding="utf-8"))
            signals = self._read_csv(report.parent / "rebalance_signals.csv")
            daily = self._read_csv(report.parent / "daily_returns.csv")
            dividends_file_exists = (report.parent / "dividends.csv").exists()

        self.assertEqual(readiness["status"], "ready")
        self.assertEqual(summary["strategy_id"], "utilities_demand_state_v51f_test")
        self.assertEqual(signals[0]["selected_codes"], "B")
        self.assertEqual(daily[0]["benchmark_source"], "utilities_benchmark")
        self.assertTrue(dividends_file_exists)

    def test_joinquant_real_data_output_prefix_keeps_sector_files_separate(self) -> None:
        original_auth = joinquant_real_data_runner._load_authenticated_jqdata
        original_fetch = joinquant_real_data_runner._fetch_jq_price_rows

        def fake_auth(username_env: str, password_env: str) -> object:
            return object()

        def fake_fetch(jq: object, code: str, start_date: str, end_date: str, asset_type: str, fq: str | None = None) -> list[dict[str, str]]:
            return [
                {
                    "date": start_date,
                    "code": code,
                    "open": "1",
                    "close": "1",
                    "high": "1",
                    "low": "1",
                    "volume": "1",
                    "money": "1",
                    "high_limit": "",
                    "low_limit": "",
                    "paused": "",
                    "price_adjustment": "raw_unadjusted_real_price" if fq is None else f"{fq}_adjusted_price",
                    "source": "test",
                }
            ]

        joinquant_real_data_runner._load_authenticated_jqdata = fake_auth
        joinquant_real_data_runner._fetch_jq_price_rows = fake_fetch
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                panel = tmp_path / "panel.csv"
                self._write_csv(panel, ["trade_date", "code"], [{"trade_date": "2021-07-01", "code": "600000.XSHG"}])
                result = joinquant_real_data_runner.collect_joinquant_real_data(
                    panel,
                    database_dir=tmp_path / "db",
                    start_date="2021-07-01",
                    end_date="2021-07-02",
                    benchmark="000007.XSHG",
                    output_prefix="utilities",
                )
                manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        finally:
            joinquant_real_data_runner._load_authenticated_jqdata = original_auth
            joinquant_real_data_runner._fetch_jq_price_rows = original_fetch

        self.assertEqual(result.price_path.name, "utilities_joinquant_real_daily_prices.csv")
        self.assertEqual(result.benchmark_path.name, "utilities_joinquant_real_benchmark_prices.csv")
        self.assertEqual(result.dividend_path.name, "utilities_joinquant_cash_dividends.csv")
        self.assertEqual(manifest["output_prefix"], "utilities_")
        self.assertEqual(manifest["benchmark"], "000007.XSHG")

    def test_validate_panel_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            panel = tmp_path / "panel.csv"
            with panel.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "trade_date",
                        "code",
                        "next_trade_date",
                        "future_return",
                        "low_price_to_book",
                        "dividend_yield",
                        "return_on_equity_ttm",
                        "non_performing_loan_ratio",
                        "provision_coverage_ratio",
                        "core_tier_1_capital_adequacy_ratio",
                    ],
                )
                writer.writeheader()
                rows = [
                    ("2020-01-02", "A", 0.10, 0.8, 0.05, 12, 1.0, 200, 10),
                    ("2020-01-02", "B", 0.02, 1.2, 0.03, 8, 1.5, 150, 9),
                    ("2020-01-02", "C", -0.01, 1.5, 0.00, 6, 2.0, 100, 8),
                    ("2020-04-01", "A", 0.03, 0.9, 0.05, 11, 1.0, 205, 10),
                    ("2020-04-01", "B", 0.01, 1.1, 0.03, 8, 1.4, 160, 9),
                    ("2020-04-01", "C", -0.02, 1.6, 0.00, 5, 2.1, 90, 8),
                ]
                for trade_date, code, ret, pb, div, roe, npl, provision, capital in rows:
                    writer.writerow(
                        {
                            "trade_date": trade_date,
                            "code": code,
                            "next_trade_date": "2020-04-01",
                            "future_return": ret,
                            "low_price_to_book": pb,
                            "dividend_yield": div,
                            "return_on_equity_ttm": roe,
                            "non_performing_loan_ratio": npl,
                            "provision_coverage_ratio": provision,
                            "core_tier_1_capital_adequacy_ratio": capital,
                        }
                    )

            report_path = validate_panel(SPEC, panel, tmp_path / "validation")
            summary_path = report_path.parent / "validation_summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertTrue(report_path.name.endswith(".md"))
        self.assertEqual(summary["row_count"], 6)
        self.assertEqual(summary["portfolio_summary"]["periods"], 2)
        self.assertEqual(summary["status"], "research_validation_completed")

    def test_collect_panel_records_adjustment_and_net_cash_dividend_total_return(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            raw_root = tmp_path / "raw"
            bank_dir = raw_root / "000001_XSHE"
            bank_dir.mkdir(parents=True)
            self._write_csv(
                bank_dir / "daily_valuation.csv",
                ["day", "code", "pb_ratio"],
                [
                    {"day": "2021-01-04", "code": "000001.XSHE", "pb_ratio": "1.0"},
                    {"day": "2021-04-01", "code": "000001.XSHE", "pb_ratio": "0.9"},
                    {"day": "2021-07-01", "code": "000001.XSHE", "pb_ratio": "0.8"},
                ],
            )
            self._write_csv(
                bank_dir / "daily_price.csv",
                ["open", "close", "high", "low", "volume", "money"],
                [
                    {"open": "10", "close": "10", "high": "10", "low": "10", "volume": "1", "money": "10"},
                    {"open": "10", "close": "10", "high": "10", "low": "10", "volume": "1", "money": "10"},
                    {"open": "11", "close": "11", "high": "11", "low": "11", "volume": "1", "money": "11"},
                ],
            )
            dividend_csv = tmp_path / "dividend.csv"
            self._write_csv(
                dividend_csv,
                ["code", "ex_date", "announce_date", "cash_per_share"],
                [{"code": "000001.XSHE", "ex_date": "2021-05-01", "announce_date": "2021-04-20", "cash_per_share": "0.1"}],
            )
            benchmark_csv = tmp_path / "benchmark.csv"
            self._write_csv(
                benchmark_csv,
                ["benchmark_id", "name", "asset_type", "symbol", "date", "open", "close", "volume", "amount", "source", "adjustment"],
                [
                    {
                        "benchmark_id": "bank_etf_512800_qfq",
                        "name": "bank etf",
                        "asset_type": "tradable_etf",
                        "symbol": "512800",
                        "date": "2021-04-01",
                        "open": "1",
                        "close": "1",
                        "volume": "1",
                        "amount": "1",
                        "source": "test",
                        "adjustment": "qfq",
                    },
                    {
                        "benchmark_id": "bank_etf_512800_qfq",
                        "name": "bank etf",
                        "asset_type": "tradable_etf",
                        "symbol": "512800",
                        "date": "2021-07-01",
                        "open": "1.2",
                        "close": "1.2",
                        "volume": "1",
                        "amount": "1",
                        "source": "test",
                        "adjustment": "qfq",
                    },
                ],
            )

            panel_path = collect_panel_from_v4_raw(
                SPEC,
                raw_root,
                tmp_path / "processed",
                price_adjustment="pre_adjusted",
                dividend_csv=dividend_csv,
                benchmark_csv=benchmark_csv,
                total_return_mode="price_plus_net_cash_dividend",
            )
            with panel_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            dividend_row = next(row for row in rows if row["trade_date"] == "2021-04-01")
            manifest = json.loads((panel_path.parent / "collection_manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(dividend_row["price_adjustment"], "pre_adjusted")
        self.assertAlmostEqual(float(dividend_row["price_return"]), 0.1)
        self.assertAlmostEqual(float(dividend_row["dividend_return"]), 0.008)
        self.assertAlmostEqual(float(dividend_row["total_return"]), 0.108)
        self.assertAlmostEqual(float(dividend_row["future_return"]), 0.108)
        self.assertEqual(dividend_row["return_source"], "price_plus_net_cash_dividend")
        self.assertAlmostEqual(float(dividend_row["benchmark_return"]), 0.2)
        self.assertEqual(dividend_row["benchmark_source"], "bank_etf_512800_qfq")
        self.assertEqual(manifest["price_adjustment"], "pre_adjusted")
        self.assertEqual(manifest["dividend_event_count"], 1)
        self.assertEqual(manifest["benchmark_id"], "bank_etf_512800_qfq")

    def test_akshare_dividend_row_normalizes_to_cash_per_share(self) -> None:
        row = {
            "报告期": "2024-12-31",
            "现金分红-现金分红比例": 3.5,
            "现金分红-股息率": 0.04,
            "股权登记日": "2025-06-19",
            "除权除息日": "2025-06-20",
            "最新公告日期": "2025-06-12",
            "方案进度": "实施分配",
        }

        normalized = _normalize_akshare_dividend_row("000001.XSHE", row)

        self.assertIsNotNone(normalized)
        assert normalized is not None
        self.assertEqual(normalized["code"], "000001.XSHE")
        self.assertEqual(normalized["ex_date"], "2025-06-20")
        self.assertEqual(normalized["announce_date"], "2025-06-12")
        self.assertAlmostEqual(float(normalized["cash_per_share"]), 0.35)

    def test_bank_quality_snapshots_use_notice_date_visibility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "quality.csv"
            self._write_csv(
                path,
                [
                    "code",
                    "source_year",
                    "npl_ratio",
                    "provision_coverage_ratio",
                    "core_tier_1_capital_adequacy_ratio",
                    "notice_date",
                    "review_status",
                ],
                [
                    {
                        "code": "000001.SZ",
                        "source_year": "2024",
                        "npl_ratio": "1.06",
                        "provision_coverage_ratio": "315.02",
                        "core_tier_1_capital_adequacy_ratio": "9.12",
                        "notice_date": "2025-03-15",
                        "review_status": "needs_check",
                    },
                    {
                        "code": "000001.SZ",
                        "source_year": "2025",
                        "npl_ratio": "1.05",
                        "provision_coverage_ratio": "330.03",
                        "core_tier_1_capital_adequacy_ratio": "9.36",
                        "notice_date": "2026-03-21",
                        "review_status": "needs_check",
                    },
                ],
            )

            snapshots = _load_bank_quality_snapshots(path, "needs_check")
            early = _latest_visible_bank_quality(snapshots["000001.XSHE"], date.fromisoformat("2025-03-14"))
            visible = _latest_visible_bank_quality(snapshots["000001.XSHE"], date.fromisoformat("2025-03-15"))

        self.assertIsNone(early)
        self.assertIsNotNone(visible)
        assert visible is not None
        self.assertEqual(visible["source_year"], "2024")

    def test_collect_v4_legacy_bank_quality_uses_first_visible_rebalance_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "phase1.csv"
            self._write_csv(
                source,
                [
                    "rebalance_date",
                    "code",
                    "bank_indicator__Nonperforming_loan_rate",
                    "bank_indicator__Nonperforming_loan_rate__source_year",
                    "bank_indicator__non_performing_loan_provision_coverage",
                    "bank_indicator__core_level_capital_adequacy_ratio",
                    "bank_indicator__capital_adequacy_ratio",
                ],
                [
                    {
                        "rebalance_date": "2025-04-01",
                        "code": "000001.XSHE",
                        "bank_indicator__Nonperforming_loan_rate": "1.06",
                        "bank_indicator__Nonperforming_loan_rate__source_year": "2024",
                        "bank_indicator__non_performing_loan_provision_coverage": "315.02",
                        "bank_indicator__core_level_capital_adequacy_ratio": "9.12",
                        "bank_indicator__capital_adequacy_ratio": "13.0",
                    },
                    {
                        "rebalance_date": "2025-07-01",
                        "code": "000001.XSHE",
                        "bank_indicator__Nonperforming_loan_rate": "1.06",
                        "bank_indicator__Nonperforming_loan_rate__source_year": "2024",
                        "bank_indicator__non_performing_loan_provision_coverage": "315.02",
                        "bank_indicator__core_level_capital_adequacy_ratio": "9.12",
                        "bank_indicator__capital_adequacy_ratio": "13.0",
                    },
                ],
            )

            result = collect_v4_legacy_bank_quality(source, tmp_path)
            with result.quality_path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(result.row_count, 1)
        self.assertEqual(rows[0]["notice_date"], "2025-04-01")
        self.assertEqual(rows[0]["review_status"], "needs_check")
        self.assertEqual(rows[0]["source_year"], "2024")

    def test_bank_quality_date_alignment_blocks_missing_joinquant_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            v4_quality = tmp_path / "v4_quality.csv"
            eastmoney_quality = tmp_path / "eastmoney_quality.csv"
            self._write_csv(
                v4_quality,
                ["code", "source_year", "notice_date", "review_status", "confidence", "source_note"],
                [
                    {
                        "code": "000001.XSHE",
                        "source_year": "2024",
                        "notice_date": "2025-04-01",
                        "review_status": "needs_check",
                        "confidence": "medium",
                        "source_note": "v4 local first use",
                    }
                ],
            )
            self._write_csv(
                eastmoney_quality,
                ["code", "source_year", "notice_date", "review_status", "confidence", "source_note"],
                [
                    {
                        "code": "000001.XSHE",
                        "source_year": "2024",
                        "notice_date": "2025-03-15",
                        "review_status": "needs_check",
                        "confidence": "medium",
                        "source_note": "eastmoney annual report",
                    }
                ],
            )

            result = align_bank_quality_dates(tmp_path / "aligned", v4_quality, eastmoney_quality)
            rows = self._read_csv(result.alignment_path)

        self.assertEqual(result.row_count, 1)
        self.assertEqual(result.formal_usable_count, 0)
        self.assertEqual(rows[0]["formal_pit_usable"], "false")
        self.assertEqual(rows[0]["missing_date_types"], "joinquant_available_date")
        self.assertEqual(rows[0]["conservative_visible_date"], "2025-04-01")

    def test_bank_quality_date_alignment_uses_max_of_three_dates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            v4_quality = tmp_path / "v4_quality.csv"
            eastmoney_quality = tmp_path / "eastmoney_quality.csv"
            jq_quality = tmp_path / "jq_quality.csv"
            self._write_csv(
                v4_quality,
                ["code", "source_year", "notice_date", "review_status", "confidence", "source_note"],
                [{"code": "000001.XSHE", "source_year": "2024", "notice_date": "2025-04-01"}],
            )
            self._write_csv(
                eastmoney_quality,
                ["code", "source_year", "notice_date", "review_status", "confidence", "source_note"],
                [{"code": "000001.SZ", "source_year": "2024", "notice_date": "2025-03-15"}],
            )
            self._write_csv(
                jq_quality,
                ["code", "source_year", "joinquant_available_date", "review_status", "confidence", "source_note"],
                [{"code": "000001.XSHE", "source_year": "2024", "joinquant_available_date": "2025-03-31"}],
            )

            result = align_bank_quality_dates(tmp_path / "aligned", v4_quality, eastmoney_quality, jq_quality)
            rows = self._read_csv(result.alignment_path)

        self.assertEqual(result.formal_usable_count, 1)
        self.assertEqual(rows[0]["formal_pit_usable"], "true")
        self.assertEqual(rows[0]["date_alignment_status"], "aligned_formal_pit_ready")
        self.assertEqual(rows[0]["conservative_visible_date"], "2025-04-01")

    def test_joinquant_proxy_date_does_not_make_formal_pit_usable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            v4_quality = tmp_path / "v4_quality.csv"
            external_notice = tmp_path / "tushare_notice.csv"
            self._write_csv(
                v4_quality,
                ["code", "source_year", "notice_date", "review_status", "confidence", "source_note"],
                [{"code": "000001.XSHE", "source_year": "2024", "notice_date": "2025-04-01"}],
            )
            self._write_csv(
                external_notice,
                ["code", "source_year", "notice_date", "review_status", "confidence", "source_note"],
                [{"code": "000001.XSHE", "source_year": "2024", "notice_date": "2025-03-15", "source_note": "tushare"}],
            )

            proxy = build_joinquant_availability_proxy(v4_quality, tmp_path / "jq")
            result = align_bank_quality_dates(
                tmp_path / "aligned",
                v4_quality_csv=v4_quality,
                eastmoney_quality_csv=tmp_path / "missing_eastmoney.csv",
                joinquant_availability_csv=proxy.availability_path,
                external_notice_csv=external_notice,
            )
            rows = self._read_csv(result.alignment_path)

        self.assertEqual(rows[0]["conservative_visible_date"], "2025-04-01")
        self.assertEqual(rows[0]["formal_pit_usable"], "false")
        self.assertEqual(rows[0]["date_alignment_status"], "aligned_with_joinquant_proxy_not_formal")

    def test_benchmark_row_normalizes_close_series(self) -> None:
        spec = {
            "benchmark_id": "bank_etf_512800_qfq",
            "name": "银行ETF 512800 前复权",
            "asset_type": "tradable_etf",
            "symbol": "512800",
            "source": "akshare.fund_etf_hist_em",
            "adjustment": "qfq",
        }
        row = {"日期": "2026-05-29", "开盘": 0.76, "收盘": 0.776, "成交量": 100, "成交额": 200}

        normalized = _normalize_benchmark_row(spec, row)

        self.assertIsNotNone(normalized)
        assert normalized is not None
        self.assertEqual(normalized["benchmark_id"], "bank_etf_512800_qfq")
        self.assertEqual(normalized["date"], "2026-05-29")
        self.assertAlmostEqual(float(normalized["close"]), 0.776)

    def test_local_backtest_writes_metric_report_and_optional_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            panel = tmp_path / "panel.csv"
            self._write_sample_panel(panel)

            report_path = run_local_backtest(
                SPEC,
                panel,
                tmp_path / "local_backtests",
                BacktestOptions(save_periods=True, save_holdings=True),
            )
            summary_path = report_path.parent / "summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

            self.assertTrue(report_path.exists())
            self.assertTrue((report_path.parent / "period_returns.csv").exists())
            self.assertTrue((report_path.parent / "holdings.csv").exists())
            self.assertIn("strategy_return", summary["metrics"])
            self.assertIn("max_drawdown_interval", summary["metrics"])
            self.assertEqual(summary["window"]["start_date"], "2021-05-01")
            self.assertEqual(summary["window"]["end_date"], "2026-05-31")
            self.assertEqual(summary["source_row_count"], 12)
            self.assertEqual(summary["filtered_row_count"], 6)
            self.assertEqual(summary["period_count"], 2)
            self.assertEqual(summary["skipped_period_count"], 0)
            self.assertEqual(summary["outputs"]["period_returns"], "period_returns.csv")

    def test_local_backtest_skips_low_coverage_rebalance_periods(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            panel = tmp_path / "panel.csv"
            self._write_low_coverage_panel(panel)

            report_path = run_local_backtest(
                SPEC,
                panel,
                tmp_path / "local_backtests",
                BacktestOptions(min_coverage_ratio=0.8),
            )
            summary = json.loads((report_path.parent / "summary.json").read_text(encoding="utf-8"))

        self.assertEqual(summary["filtered_row_count"], 4)
        self.assertEqual(summary["period_count"], 1)
        self.assertEqual(summary["skipped_period_count"], 1)
        self.assertEqual(summary["skipped_periods"][0]["trade_date"], "2022-01-17")
        self.assertEqual(summary["skipped_periods"][0]["security_count"], 1)
        self.assertEqual(summary["skipped_periods"][0]["required_security_count"], 3)

    def test_local_backtest_joinquant_like_execution_uses_lot_sized_positions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            panel = tmp_path / "panel.csv"
            self._write_execution_panel(panel)

            report_path = run_local_backtest(
                SPEC,
                panel,
                tmp_path / "local_backtests",
                BacktestOptions(save_periods=True, save_holdings=True, execution_mode="joinquant_like"),
            )
            summary = json.loads((report_path.parent / "summary.json").read_text(encoding="utf-8"))
            with (report_path.parent / "holdings.csv").open("r", encoding="utf-8", newline="") as handle:
                holdings = list(csv.DictReader(handle))

        self.assertEqual(summary["execution"]["mode"], "joinquant_like")
        self.assertEqual(summary["execution"]["lot_size"], 100)
        self.assertTrue(any(int(float(row["amount"])) > 0 for row in holdings))
        self.assertTrue(all(int(float(row["amount"])) % 100 == 0 for row in holdings))

    def test_defensive_state_uses_benchmark_ma_history(self) -> None:
        risk_on_options = BacktestOptions(defensive_mode="none")
        self.assertEqual(_defensive_state([1.0, 0.9], risk_on_options), "risk_on")

        ma_options = BacktestOptions(defensive_mode="benchmark_ma", defensive_ma_days=3)
        self.assertEqual(_defensive_state([1.0, 1.1], ma_options), "risk_on")
        self.assertEqual(_defensive_state([1.0, 1.1, 0.8], ma_options), "risk_off")
        self.assertEqual(_defensive_state([1.0, 0.9, 1.2], ma_options), "risk_on")

    def _write_sample_panel(self, panel: Path) -> None:
        with panel.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "trade_date",
                    "code",
                    "next_trade_date",
                    "future_return",
                    "benchmark_return",
                    "low_price_to_book",
                    "dividend_yield",
                    "return_on_equity_ttm",
                    "non_performing_loan_ratio",
                    "provision_coverage_ratio",
                    "core_tier_1_capital_adequacy_ratio",
                ],
            )
            writer.writeheader()
            rows = [
                ("2021-04-30", "A", 0.10, 0.04, 0.8, 0.05, 12, 1.0, 200, 10),
                ("2021-04-30", "B", 0.02, 0.04, 1.2, 0.03, 8, 1.5, 150, 9),
                ("2021-04-30", "C", -0.01, 0.04, 1.5, 0.00, 6, 2.0, 100, 8),
                ("2021-05-03", "A", 0.03, 0.01, 0.9, 0.05, 11, 1.0, 205, 10),
                ("2021-05-03", "B", 0.01, 0.01, 1.1, 0.03, 8, 1.4, 160, 9),
                ("2021-05-03", "C", -0.02, 0.01, 1.6, 0.00, 5, 2.1, 90, 8),
                ("2026-05-29", "A", 0.02, 0.01, 0.9, 0.05, 11, 1.0, 205, 10),
                ("2026-05-29", "B", -0.01, 0.01, 1.1, 0.03, 8, 1.4, 160, 9),
                ("2026-05-29", "C", 0.01, 0.01, 1.6, 0.00, 5, 2.1, 90, 8),
                ("2026-06-01", "A", 0.04, 0.02, 0.8, 0.05, 12, 1.0, 200, 10),
                ("2026-06-01", "B", 0.01, 0.02, 1.2, 0.03, 8, 1.5, 150, 9),
                ("2026-06-01", "C", -0.03, 0.02, 1.5, 0.00, 6, 2.0, 100, 8),
            ]
            for trade_date, code, ret, benchmark, pb, div, roe, npl, provision, capital in rows:
                writer.writerow(
                    {
                        "trade_date": trade_date,
                        "code": code,
                        "next_trade_date": "2020-04-01",
                        "future_return": ret,
                        "benchmark_return": benchmark,
                        "low_price_to_book": pb,
                        "dividend_yield": div,
                        "return_on_equity_ttm": roe,
                        "non_performing_loan_ratio": npl,
                        "provision_coverage_ratio": provision,
                        "core_tier_1_capital_adequacy_ratio": capital,
                    }
                )

    def _write_low_coverage_panel(self, panel: Path) -> None:
        with panel.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "trade_date",
                    "code",
                    "next_trade_date",
                    "future_return",
                    "benchmark_return",
                    "low_price_to_book",
                    "dividend_yield",
                    "return_on_equity_ttm",
                    "non_performing_loan_ratio",
                    "provision_coverage_ratio",
                    "core_tier_1_capital_adequacy_ratio",
                ],
            )
            writer.writeheader()
            rows = [
                ("2022-01-04", "A", 0.03, 0.01, 0.9, 0.05, 11, 1.0, 205, 10),
                ("2022-01-04", "B", 0.01, 0.01, 1.1, 0.03, 8, 1.4, 160, 9),
                ("2022-01-04", "C", -0.02, 0.01, 1.6, 0.00, 5, 2.1, 90, 8),
                ("2022-01-17", "D", 0.50, 0.02, 0.7, 0.08, 13, 0.8, 220, 11),
            ]
            for trade_date, code, ret, benchmark, pb, div, roe, npl, provision, capital in rows:
                writer.writerow(
                    {
                        "trade_date": trade_date,
                        "code": code,
                        "next_trade_date": "2022-04-01",
                        "future_return": ret,
                        "benchmark_return": benchmark,
                        "low_price_to_book": pb,
                        "dividend_yield": div,
                        "return_on_equity_ttm": roe,
                        "non_performing_loan_ratio": npl,
                        "provision_coverage_ratio": provision,
                        "core_tier_1_capital_adequacy_ratio": capital,
                    }
                )

    def _write_execution_panel(self, panel: Path) -> None:
        with panel.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "trade_date",
                    "code",
                    "close",
                    "next_trade_date",
                    "future_return",
                    "benchmark_return",
                    "low_price_to_book",
                    "dividend_yield",
                    "return_on_equity_ttm",
                    "non_performing_loan_ratio",
                    "provision_coverage_ratio",
                    "core_tier_1_capital_adequacy_ratio",
                ],
            )
            writer.writeheader()
            rows = [
                ("2021-07-01", "A", 10.0, 0.10, 0.02, 0.8),
                ("2021-07-01", "B", 20.0, 0.02, 0.02, 0.9),
                ("2021-07-01", "C", 30.0, -0.01, 0.02, 1.0),
                ("2021-10-08", "A", 11.0, 0.01, 0.01, 0.9),
                ("2021-10-08", "B", 20.4, 0.03, 0.01, 0.8),
                ("2021-10-08", "C", 29.7, 0.04, 0.01, 0.7),
            ]
            for trade_date, code, close, ret, benchmark, pb in rows:
                writer.writerow(
                    {
                        "trade_date": trade_date,
                        "code": code,
                        "close": close,
                        "next_trade_date": "2022-01-04",
                        "future_return": ret,
                        "benchmark_return": benchmark,
                        "low_price_to_book": pb,
                        "dividend_yield": 0.05,
                        "return_on_equity_ttm": 12,
                        "non_performing_loan_ratio": 1.0,
                        "provision_coverage_ratio": 200,
                        "core_tier_1_capital_adequacy_ratio": 10,
                    }
                )

    def _write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def _read_csv(self, path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()

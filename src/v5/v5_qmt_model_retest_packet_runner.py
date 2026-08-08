from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from v5.v5f_repaired_baseline_overlay_comparison_runner import (
    _all_overlay_weights as _overlay_all_weights,
)
from v5.v5f_repaired_baseline_overlay_comparison_runner import (
    _load_prices as _overlay_load_prices,
)


OUT_DIR = Path("v5_qmt_model_retest_packet") / "current"
QMT_INPUT_DIR = OUT_DIR / "qmt_inputs"
QMT_SCRIPT_DIR = OUT_DIR / "qmt_scripts"
QMT_RESULT_DIR = OUT_DIR / "qmt_results"

STRUCTURAL_DIR = Path("v5f_structural_rough_screen") / "current"
LOCKED_DIR = Path("v5f_locked_pool_conditional_momentum") / "current"
OVERLAY_DIR = Path("v5f_repaired_baseline_overlay_comparison") / "current"
WARMUP_RUN = (
    Path("v5_startup_warmup_price_repair")
    / "current"
    / "runs"
    / "v57f_warmup_repaired_daily_backtest"
    / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f"
)

BACKTEST_START = "2021-05-01"
EFFECTIVE_FIRST_SIGNAL = "2021-05-06"
BACKTEST_END = "2026-05-31"
INITIAL_CAPITAL = 2_000_000.0
COMMISSION_RATE = 0.0003
BASELINE = "v57f_startup_preload_repaired_baseline"

READY_MODELS = [
    BASELINE,
    "internal_subsleeve_mom12_70_30",
    "internal_subsleeve_mom12_80_20",
    "locked_pool_monthly_mom12_70_30",
    "locked_pool_biweekly_mom12_70_30",
    "momentum_plus_mean_reversion_equal_blend",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5_qmt_model_retest_packet(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    qmt_inputs = root / QMT_INPUT_DIR
    qmt_scripts = root / QMT_SCRIPT_DIR
    qmt_results = root / QMT_RESULT_DIR
    for directory in [out, qmt_inputs, qmt_scripts, qmt_results]:
        directory.mkdir(parents=True, exist_ok=True)

    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5_qmt_retest_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", blockers, ready_model_count=0)
        _write_json(out / "v5_qmt_retest_summary.json", summary)
        return summary

    structural_weights = _read_csv(root / STRUCTURAL_DIR / "v5f_structural_rough_screen_weights.csv")
    structural_metrics = _read_csv(root / STRUCTURAL_DIR / "v5f_structural_rough_screen_metrics.csv")
    locked_weights = _read_csv(root / LOCKED_DIR / "v5f_locked_pool_conditional_momentum_weight_log.csv")
    locked_metrics = _read_csv(root / LOCKED_DIR / "v5f_locked_pool_conditional_momentum_metrics.csv")
    overlay_metrics = _read_csv(root / OVERLAY_DIR / "v5f_combined_overlay_repaired_result.csv")
    warmup_summary = _read_json(root / WARMUP_RUN / "summary.json")
    warmup_daily = _read_csv(root / WARMUP_RUN / "daily_returns.csv")
    warmup_signals = _read_csv(root / WARMUP_RUN / "rebalance_signals.csv")

    overlay_weights = _build_overlay_weights(root, {"momentum_plus_mean_reversion_equal_blend"})
    schedule = _target_weight_schedule(structural_weights, locked_weights, overlay_weights)
    expected_metrics = _expected_metrics(structural_metrics, locked_metrics, overlay_metrics, warmup_summary)
    model_manifest = _model_manifest(expected_metrics, schedule)
    source_manifest = _source_manifest()
    comparison = _expected_metric_comparison(expected_metrics)
    static_audit = _static_safety_audit(_qmt_nav_replay_script(qmt_inputs, qmt_results))
    import_template = _result_import_template(model_manifest)
    blockers_out = _blockers(static_audit, model_manifest, schedule)
    next_queue = _next_queue(blockers_out)

    _write_csv(qmt_inputs / "v5_qmt_model_manifest.csv", model_manifest)
    _write_csv(qmt_inputs / "v5_qmt_selected_model_metrics.csv", expected_metrics)
    _write_csv(qmt_inputs / "v5_qmt_target_weight_schedule.csv", schedule)
    _write_csv(qmt_inputs / "v5_qmt_source_file_manifest.csv", source_manifest)
    _write_csv(out / "v5_qmt_expected_metric_comparison.csv", comparison)
    _write_csv(out / "v5_qmt_no_order_static_audit.csv", static_audit)
    _write_csv(out / "v5_qmt_result_import_template.csv", import_template)
    _write_csv(out / "v5_qmt_retest_blockers.csv", blockers_out)
    _write_csv(out / "v5_qmt_retest_next_queue.csv", next_queue)

    (qmt_scripts / "v5_qmt_no_order_nav_replay.py").write_text(
        _qmt_nav_replay_script(qmt_inputs, qmt_results),
        encoding="utf-8",
    )
    (qmt_scripts / "v5_qmt_import_smoke_test.py").write_text(
        _qmt_import_smoke_script(qmt_inputs, qmt_results),
        encoding="utf-8",
    )
    (out / "v5_qmt_manual_run_checklist.md").write_text(
        _manual_checklist(qmt_scripts, qmt_inputs, qmt_results),
        encoding="utf-8",
    )
    (out / "v5_qmt_skill_candidate_spec.md").write_text(_skill_candidate_spec(), encoding="utf-8")
    (out / "v5_qmt_retest_report.md").write_text(
        _report(model_manifest, comparison, static_audit, blockers_out),
        encoding="utf-8",
    )

    summary = _summary(
        "completed_qmt_retest_packet_ready_manual_qmt_run_required",
        blockers_out,
        ready_model_count=sum(1 for row in model_manifest if row["qmt_test_status"] == "ready_for_qmt_no_order_replay"),
        selected_model_count=len(model_manifest),
        target_weight_rows=len(schedule),
        unique_qmt_stock_count=len({row["qmt_code"] for row in schedule}),
        qmt_script=str(qmt_scripts / "v5_qmt_no_order_nav_replay.py"),
        manual_checklist=str(out / "v5_qmt_manual_run_checklist.md"),
    )
    _write_json(out / "v5_qmt_retest_summary.json", summary)
    return summary


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        STRUCTURAL_DIR / "v5f_structural_rough_screen_weights.csv",
        STRUCTURAL_DIR / "v5f_structural_rough_screen_metrics.csv",
        LOCKED_DIR / "v5f_locked_pool_conditional_momentum_weight_log.csv",
        LOCKED_DIR / "v5f_locked_pool_conditional_momentum_metrics.csv",
        OVERLAY_DIR / "v5f_combined_overlay_repaired_result.csv",
        WARMUP_RUN / "summary.json",
        WARMUP_RUN / "daily_returns.csv",
        WARMUP_RUN / "rebalance_signals.csv",
    ]
    rows = []
    for path in required:
        if not (root / path).exists():
            rows.append({"blocker_id": "missing_input", "path": str(path), "fatal": True})
    return rows


def _build_overlay_weights(root: Path, selected: set[str]) -> list[dict[str, Any]]:
    prices = _overlay_load_prices(root)
    signals = pd.read_csv(root / WARMUP_RUN / "rebalance_signals.csv", dtype={"trade_date": str, "code": str})
    rows = _overlay_all_weights(signals, prices)
    out = []
    for row in rows:
        if row["version_id"] not in selected:
            continue
        out.append(
            {
                "version_id": row["version_id"],
                "family": row["overlay_family"],
                "schedule_date": row["rebalance_date"],
                "active_rebalance_date": row["rebalance_date"],
                "code": row["code"],
                "sleeve": row["sleeve"],
                "base_target_weight": row["base_target_weight"],
                "target_weight": row["tilted_target_weight"],
                "weight_delta": row["weight_delta"],
                "source": "v5f_repaired_baseline_overlay_comparison.reconstructed",
                "accepted": False,
            }
        )
    return out


def _target_weight_schedule(
    structural_weights: list[dict[str, str]],
    locked_weights: list[dict[str, str]],
    overlay_weights: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    structural_models = {BASELINE, "internal_subsleeve_mom12_70_30", "internal_subsleeve_mom12_80_20"}
    locked_models = {"locked_pool_monthly_mom12_70_30", "locked_pool_biweekly_mom12_70_30"}

    for row in structural_weights:
        if row["version_id"] not in structural_models:
            continue
        rows.append(
            _schedule_row(
                model_id=row["version_id"],
                family=row["family"],
                schedule_date=row["rebalance_date"],
                active_rebalance_date=row["rebalance_date"],
                code=row["code"],
                sleeve=row["sleeve"],
                base_weight=row["base_target_weight"],
                target_weight=row["target_weight"],
                source="v5f_structural_rough_screen_weights",
            )
        )

    for row in locked_weights:
        if row["version_id"] not in locked_models:
            continue
        rows.append(
            _schedule_row(
                model_id=row["version_id"],
                family="locked_pool_conditional_momentum",
                schedule_date=row["trade_date"],
                active_rebalance_date=row["active_rebalance_date"],
                code=row["code"],
                sleeve=row["sleeve"],
                base_weight=row["base_target_weight"],
                target_weight=row["target_weight"],
                source="v5f_locked_pool_conditional_momentum_weight_log",
            )
        )

    for row in overlay_weights:
        rows.append(
            _schedule_row(
                model_id=row["version_id"],
                family=row["family"],
                schedule_date=row["schedule_date"],
                active_rebalance_date=row["active_rebalance_date"],
                code=row["code"],
                sleeve=row["sleeve"],
                base_weight=row["base_target_weight"],
                target_weight=row["target_weight"],
                source=row["source"],
            )
        )

    rows = [row for row in rows if BACKTEST_START <= row["schedule_date"] <= BACKTEST_END]
    rows.sort(key=lambda r: (r["model_id"], r["schedule_date"], r["qmt_code"]))
    return rows


def _schedule_row(
    model_id: str,
    family: str,
    schedule_date: str,
    active_rebalance_date: str,
    code: str,
    sleeve: str,
    base_weight: Any,
    target_weight: Any,
    source: str,
) -> dict[str, Any]:
    base = _safe_float(base_weight) or 0.0
    target = _safe_float(target_weight) or 0.0
    return {
        "model_id": model_id,
        "family": family,
        "schedule_date": schedule_date,
        "active_rebalance_date": active_rebalance_date,
        "v5_code": code,
        "qmt_code": _to_qmt_code(code),
        "sleeve": sleeve,
        "base_target_weight": base,
        "target_weight": target,
        "weight_delta": target - base,
        "backtest_start": BACKTEST_START,
        "effective_first_signal": EFFECTIVE_FIRST_SIGNAL,
        "backtest_end": BACKTEST_END,
        "source": source,
        "accepted": False,
        "live_trading_approved": False,
    }


def _expected_metrics(
    structural_metrics: list[dict[str, str]],
    locked_metrics: list[dict[str, str]],
    overlay_metrics: list[dict[str, str]],
    warmup_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_version: dict[str, dict[str, Any]] = {}
    for row in structural_metrics:
        by_version[row["version_id"]] = {"source": "v5f_structural_rough_screen_metrics", **row}
    for row in locked_metrics:
        by_version[row["version_id"]] = {"source": "v5f_locked_pool_conditional_momentum_metrics", **row}
    for row in overlay_metrics:
        by_version[row["version_id"]] = {"source": "v5f_combined_overlay_repaired_result", **row}
    baseline_metric = warmup_summary["metrics"]
    by_version[BASELINE] = {
        "source": "v57f_warmup_repaired_daily_backtest_summary",
        "version_id": BASELINE,
        "family": "baseline",
        "strategy_return": baseline_metric["strategy_return"],
        "annualized_return": baseline_metric["annualized_return"],
        "max_drawdown": baseline_metric["max_drawdown"],
        "volatility": baseline_metric["strategy_volatility"],
        "sharpe_proxy": baseline_metric["sharpe"],
        "turnover_proxy": "",
        "incremental_commission_total": 0.0,
        "delta_return_pct_points_vs_repaired_baseline": 0.0,
        "delta_max_drawdown_pct_points_vs_repaired_baseline": 0.0,
    }

    for model_id in READY_MODELS:
        metric = by_version.get(model_id, {})
        rows.append(
            {
                "model_id": model_id,
                "family": metric.get("family", metric.get("overlay_family", "")),
                "expected_strategy_return_pct": _as_pct(metric.get("strategy_return")),
                "expected_annualized_return_pct": _as_pct(metric.get("annualized_return")),
                "expected_max_drawdown_pct": _as_pct(metric.get("max_drawdown")),
                "expected_volatility_pct": _as_pct(metric.get("volatility")),
                "expected_sharpe_proxy": metric.get("sharpe_proxy", ""),
                "delta_return_pct_points_vs_repaired_baseline": _safe_float(metric.get("delta_return_pct_points_vs_repaired_baseline")) or 0.0,
                "delta_max_drawdown_pct_points_vs_repaired_baseline": _safe_float(metric.get("delta_max_drawdown_pct_points_vs_repaired_baseline")) or 0.0,
                "expected_source": metric.get("source", "missing_metric"),
                "accepted": False,
                "live_trading_approved": False,
            }
        )
    return rows


def _model_manifest(expected_metrics: list[dict[str, Any]], schedule: list[dict[str, Any]]) -> list[dict[str, Any]]:
    schedule_models = {row["model_id"] for row in schedule}
    stock_counts = pd.DataFrame(schedule).groupby("model_id")["qmt_code"].nunique().to_dict() if schedule else {}
    row_counts = pd.DataFrame(schedule).groupby("model_id")["qmt_code"].count().to_dict() if schedule else {}
    roles = {
        BASELINE: "benchmark",
        "internal_subsleeve_mom12_70_30": "primary_v5f_forward_paper_candidate_not_accepted",
        "internal_subsleeve_mom12_80_20": "secondary_robustness_reference",
        "locked_pool_monthly_mom12_70_30": "adaptive_monthly_reference_not_primary",
        "locked_pool_biweekly_mom12_70_30": "best_backtest_diagnostic_reference_not_primary",
        "momentum_plus_mean_reversion_equal_blend": "older_overlay_reference",
    }
    rule_notes = {
        BASELINE: "Startup warmup repaired V57f baseline.",
        "internal_subsleeve_mom12_70_30": "Same-sleeve internal 70pct V57f base plus 30pct mom12 top-tercile allocation.",
        "internal_subsleeve_mom12_80_20": "Same architecture with 20pct momentum budget.",
        "locked_pool_monthly_mom12_70_30": "Locked V57f pool, monthly momentum target refresh.",
        "locked_pool_biweekly_mom12_70_30": "Locked V57f pool, biweekly momentum target refresh; diagnostic due drawdown/turnover governance.",
        "momentum_plus_mean_reversion_equal_blend": "Older equal blend of fixed momentum and 60d mean-reversion overlay.",
    }
    out = []
    for metric in expected_metrics:
        model_id = metric["model_id"]
        ready = model_id in schedule_models
        out.append(
            {
                "model_id": model_id,
                "role": roles.get(model_id, "reference"),
                "rule_notes": rule_notes.get(model_id, ""),
                "qmt_test_status": "ready_for_qmt_no_order_replay" if ready else "blocked_missing_weight_schedule",
                "schedule_row_count": int(row_counts.get(model_id, 0)),
                "unique_stock_count": int(stock_counts.get(model_id, 0)),
                "backtest_start": BACKTEST_START,
                "effective_first_signal": EFFECTIVE_FIRST_SIGNAL,
                "backtest_end": BACKTEST_END,
                "initial_capital": INITIAL_CAPITAL,
                "commission_rate": COMMISSION_RATE,
                "accepted": False,
                "live_trading_approved": False,
            }
        )
    return out


def _source_manifest() -> list[dict[str, Any]]:
    return [
        {"source_id": "structural_weights", "path": str(STRUCTURAL_DIR / "v5f_structural_rough_screen_weights.csv"), "purpose": "baseline, 70/30 and 80/20 target schedules"},
        {"source_id": "structural_metrics", "path": str(STRUCTURAL_DIR / "v5f_structural_rough_screen_metrics.csv"), "purpose": "expected local metrics for baseline, 70/30 and 80/20"},
        {"source_id": "locked_weights", "path": str(LOCKED_DIR / "v5f_locked_pool_conditional_momentum_weight_log.csv"), "purpose": "monthly and biweekly locked-pool target schedules"},
        {"source_id": "locked_metrics", "path": str(LOCKED_DIR / "v5f_locked_pool_conditional_momentum_metrics.csv"), "purpose": "expected local metrics for locked-pool variants"},
        {"source_id": "overlay_metrics", "path": str(OVERLAY_DIR / "v5f_combined_overlay_repaired_result.csv"), "purpose": "expected local metrics for equal blend reference"},
        {"source_id": "repaired_baseline_run", "path": str(WARMUP_RUN), "purpose": "startup warmup repaired baseline truth source"},
    ]


def _expected_metric_comparison(expected_metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in sorted(expected_metrics, key=lambda r: float(r["delta_return_pct_points_vs_repaired_baseline"]), reverse=True):
        rows.append(
            {
                "rank_by_local_delta": len(rows) + 1,
                "model_id": row["model_id"],
                "expected_strategy_return_pct": row["expected_strategy_return_pct"],
                "expected_max_drawdown_pct": row["expected_max_drawdown_pct"],
                "delta_return_pct_points_vs_repaired_baseline": row["delta_return_pct_points_vs_repaired_baseline"],
                "delta_max_drawdown_pct_points_vs_repaired_baseline": row["delta_max_drawdown_pct_points_vs_repaired_baseline"],
                "qmt_comparison_status": "pending_qmt_manual_run",
                "accepted": False,
            }
        )
    return rows


def _static_safety_audit(script_text: str) -> list[dict[str, Any]]:
    blocked_terms = [
        "passorder",
        "algo_passorder",
        "smart_algo_passorder",
        "order_shares",
        "order_target",
        "order_value",
        "buy(",
        "sell(",
        "cancel",
    ]
    lowered = script_text.lower()
    rows = []
    for term in blocked_terms:
        rows.append(
            {
                "audit_id": f"blocked_term_{term.replace('(', '').replace('_', '-')}",
                "status": "pass" if term not in lowered else "fail",
                "detail": term,
            }
        )
    rows.extend(
        [
            {"audit_id": "script_uses_context_market_data_only", "status": "pass" if "get_market_data_ex" in script_text else "fail", "detail": "QMT data read API"},
            {"audit_id": "script_exports_csv_only", "status": "pass" if "csv.DictWriter" in script_text else "fail", "detail": "output is csv file"},
            {"audit_id": "script_has_no_live_approval", "status": "pass", "detail": "packet is not accepted and not live approved"},
        ]
    )
    return rows


def _blockers(
    static_audit: list[dict[str, Any]],
    manifest: list[dict[str, Any]],
    schedule: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    if any(row["status"] == "fail" for row in static_audit):
        rows.append({"blocker_id": "qmt_script_static_safety_failed", "severity": "fatal", "detail": "No-order script contains blocked trading terms."})
    if any(row["qmt_test_status"] != "ready_for_qmt_no_order_replay" for row in manifest):
        rows.append({"blocker_id": "missing_weight_schedule", "severity": "fatal", "detail": "One or more selected models lacks QMT schedule rows."})
    if not schedule:
        rows.append({"blocker_id": "empty_qmt_weight_schedule", "severity": "fatal", "detail": "No target weights exported."})
    return rows


def _next_queue(blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if blockers:
        return [{"priority": "P0", "next_task": "repair_qmt_retest_packet_blockers", "allowed": True, "reason": "; ".join(row["blocker_id"] for row in blockers)}]
    return [
        {"priority": "P0", "next_task": "run_v5_qmt_no_order_nav_replay_in_qmt_model_research", "allowed": True, "reason": "QMT script and inputs are ready; manual QMT run required."},
        {"priority": "P1", "next_task": "import_qmt_result_csv_and_compare_to_local_metrics", "allowed": True, "reason": "After QMT output is generated, compare platform-data replay with local expected metrics."},
        {"priority": "P2", "next_task": "create_qmt_retest_skill_after_one_successful_roundtrip", "allowed": True, "reason": "Skill should be created only after QMT export and ingestion workflow is proven."},
    ]


def _result_import_template(manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "model_id": row["model_id"],
            "qmt_strategy_return_pct": "",
            "qmt_annualized_return_pct": "",
            "qmt_max_drawdown_pct": "",
            "qmt_volatility_pct": "",
            "qmt_sharpe_proxy": "",
            "qmt_output_file": "",
            "import_status": "pending",
        }
        for row in manifest
    ]


def _qmt_nav_replay_script(qmt_inputs: Path, qmt_results: Path) -> str:
    weights_path = (qmt_inputs / "v5_qmt_target_weight_schedule.csv").resolve()
    output_dir = qmt_results.resolve()
    return f'''#coding:utf-8
import csv
import math
import os

WEIGHTS_CSV = r"{weights_path}"
OUTPUT_DIR = r"{output_dir}"
START_TIME = "20210501"
END_TIME = "20260531"
DIVIDEND_TYPE = "front"


def init(ContextInfo):
    ContextInfo.v5_done = False
    ContextInfo.v5_weights, ContextInfo.v5_models, ContextInfo.v5_stocks = load_weights()
    ContextInfo.set_universe(ContextInfo.v5_stocks)
    ContextInfo.benchmark = "000300.SH"
    print("V5 QMT no-order NAV replay loaded models:", ",".join(ContextInfo.v5_models))
    print("V5 QMT no-order NAV replay stock count:", len(ContextInfo.v5_stocks))


def handlebar(ContextInfo):
    if ContextInfo.v5_done:
        return
    if hasattr(ContextInfo, "is_last_bar") and not ContextInfo.is_last_bar():
        return
    ContextInfo.v5_done = True
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    price_data = ContextInfo.get_market_data_ex(
        fields=["close"],
        stock_code=ContextInfo.v5_stocks,
        period="1d",
        start_time=START_TIME,
        end_time=END_TIME,
        count=-1,
        dividend_type=DIVIDEND_TYPE,
        fill_data=True,
        subscribe=False,
    )
    close_map, all_dates = normalize_price_data(price_data)
    rows, metrics = replay_models(ContextInfo.v5_weights, ContextInfo.v5_models, close_map, all_dates)
    write_csv(os.path.join(OUTPUT_DIR, "v5_qmt_nav_replay_daily.csv"), rows)
    write_csv(os.path.join(OUTPUT_DIR, "v5_qmt_nav_replay_metrics.csv"), metrics)
    for item in metrics:
        print("V5_QMT_METRIC", item["model_id"], item["strategy_return_pct"], item["max_drawdown_pct"], item["missing_price_count"])
    if metrics:
        ContextInfo.paint("v5_qmt_model_count", len(metrics), -1, 0)


def load_weights():
    weights = {{}}
    models = []
    stocks = set()
    with open(WEIGHTS_CSV, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            model = row["model_id"]
            date = row["schedule_date"].replace("-", "")
            code = row["qmt_code"]
            weight = safe_float(row["target_weight"])
            if model not in weights:
                weights[model] = {{}}
                models.append(model)
            weights[model].setdefault(date, {{}})[code] = weight
            stocks.add(code)
    return weights, models, sorted(stocks)


def normalize_date(value):
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits[:8] if len(digits) >= 8 else ""


def normalize_price_data(price_data):
    close_map = {{}}
    all_dates = set()
    for code, frame in price_data.items():
        series = {{}}
        if frame is None or len(frame) == 0:
            close_map[code] = series
            continue
        for idx, row in frame.iterrows():
            date = normalize_date(idx)
            if not date:
                continue
            close = safe_float(row.get("close", ""))
            if close and close > 0:
                series[date] = close
                all_dates.add(date)
        close_map[code] = series
    return close_map, sorted(d for d in all_dates if START_TIME <= d <= END_TIME)


def replay_models(weights, models, close_map, all_dates):
    daily_rows = []
    metric_rows = []
    if len(all_dates) < 2:
        return daily_rows, [
            {{"model_id": model, "strategy_return_pct": "", "annualized_return_pct": "", "max_drawdown_pct": "", "volatility_pct": "", "trade_days": 0, "missing_price_count": 1}}
            for model in models
        ]
    for model in models:
        nav = 1.0
        active = {{}}
        navs = []
        rets = []
        missing_total = 0
        for i in range(len(all_dates) - 1):
            day = all_dates[i]
            next_day = all_dates[i + 1]
            if day in weights[model]:
                active = weights[model][day].copy()
            if not active:
                continue
            ret = 0.0
            missing = 0
            for code, weight in active.items():
                c0 = close_map.get(code, {{}}).get(day)
                c1 = close_map.get(code, {{}}).get(next_day)
                if not c0 or not c1:
                    missing += 1
                    continue
                ret += weight * (c1 / c0 - 1.0)
            nav *= 1.0 + ret
            navs.append(nav)
            rets.append(ret)
            missing_total += missing
            daily_rows.append({{
                "trade_date": fmt_date(day),
                "next_trade_date": fmt_date(next_day),
                "model_id": model,
                "strategy_return": ret,
                "strategy_nav": nav,
                "active_position_count": len(active),
                "missing_price_count": missing,
            }})
        metric_rows.append(metrics_row(model, navs, rets, missing_total))
    return daily_rows, metric_rows


def metrics_row(model, navs, rets, missing_total):
    if not navs:
        return {{"model_id": model, "strategy_return_pct": "", "annualized_return_pct": "", "max_drawdown_pct": "", "volatility_pct": "", "trade_days": 0, "missing_price_count": missing_total}}
    total_return = navs[-1] - 1.0
    annualized = navs[-1] ** (252.0 / len(navs)) - 1.0
    max_dd = max_drawdown(navs)
    vol = std(rets) * math.sqrt(252.0)
    sharpe = annualized / vol if vol else 0.0
    return {{
        "model_id": model,
        "strategy_return_pct": total_return * 100.0,
        "annualized_return_pct": annualized * 100.0,
        "max_drawdown_pct": max_dd * 100.0,
        "volatility_pct": vol * 100.0,
        "sharpe_proxy": sharpe,
        "trade_days": len(navs),
        "missing_price_count": missing_total,
    }}


def max_drawdown(navs):
    peak = navs[0]
    worst = 0.0
    for nav in navs:
        if nav > peak:
            peak = nav
        if peak:
            worst = min(worst, nav / peak - 1.0)
    return abs(worst)


def std(values):
    if len(values) < 2:
        return 0.0
    avg = sum(values) / len(values)
    var = sum((x - avg) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(var)


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def safe_float(value):
    try:
        if value is None or value == "":
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def fmt_date(value):
    return value[:4] + "-" + value[4:6] + "-" + value[6:8]
'''


def _qmt_import_smoke_script(qmt_inputs: Path, qmt_results: Path) -> str:
    manifest_path = (qmt_inputs / "v5_qmt_model_manifest.csv").resolve()
    weights_path = (qmt_inputs / "v5_qmt_target_weight_schedule.csv").resolve()
    output_dir = qmt_results.resolve()
    return f'''#coding:utf-8
import csv
import os

MANIFEST_CSV = r"{manifest_path}"
WEIGHTS_CSV = r"{weights_path}"
OUTPUT_DIR = r"{output_dir}"


def init(ContextInfo):
    ContextInfo.v5_done = False


def handlebar(ContextInfo):
    if ContextInfo.v5_done:
        return
    ContextInfo.v5_done = True
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    models = read_csv(MANIFEST_CSV)
    weights = read_csv(WEIGHTS_CSV)
    rows = [{{
        "manifest_rows": len(models),
        "weight_rows": len(weights),
        "unique_models": len(set(row["model_id"] for row in weights)),
        "status": "pass" if models and weights else "fail",
    }}]
    with open(os.path.join(OUTPUT_DIR, "v5_qmt_import_smoke_test.csv"), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("V5_QMT_IMPORT_SMOKE", rows[0])


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))
'''


def _manual_checklist(qmt_scripts: Path, qmt_inputs: Path, qmt_results: Path) -> str:
    script = (qmt_scripts / "v5_qmt_no_order_nav_replay.py").resolve()
    smoke = (qmt_scripts / "v5_qmt_import_smoke_test.py").resolve()
    return f"""# V5 QMT Manual Run Checklist

Backtest window: `{BACKTEST_START}` to `{BACKTEST_END}`. Effective first signal: `{EFFECTIVE_FIRST_SIGNAL}`.

Use QMT model research / Python model. Run on daily period (`1d`) with a broad benchmark chart such as `000300.SH`.

1. First paste and run the import smoke script:
   `{smoke}`
2. Confirm QMT writes:
   `{(qmt_results / "v5_qmt_import_smoke_test.csv").resolve()}`
3. Paste and run the NAV replay script:
   `{script}`
4. Confirm QMT writes:
   `{(qmt_results / "v5_qmt_nav_replay_metrics.csv").resolve()}`
   `{(qmt_results / "v5_qmt_nav_replay_daily.csv").resolve()}`
5. Send the two QMT output CSV files back into this workspace for comparison.

Safety boundary:
- This packet is model-research / backtest replay only.
- It reads QMT daily close data and local target weights.
- It does not submit, cancel, route, or simulate live account instructions through QMT trading functions.
- No model is accepted or live approved.
"""


def _skill_candidate_spec() -> str:
    return """# QMT Retest Skill Candidate

Create this as a reusable skill only after one successful QMT roundtrip.

Target workflow:
1. Select approved-for-testing V5 model ids.
2. Export QMT target-weight schedules with QMT code conversion.
3. Generate no-order QMT model-research replay scripts.
4. Static-audit scripts for blocked trading calls.
5. Ingest QMT output CSV files.
6. Compare QMT replay metrics against local V5 expected metrics.

Current status: candidate spec only. The QMT manual run and result ingestion are still pending.
"""


def _report(
    model_manifest: list[dict[str, Any]],
    comparison: list[dict[str, Any]],
    static_audit: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> str:
    ready = [row for row in model_manifest if row["qmt_test_status"] == "ready_for_qmt_no_order_replay"]
    audit_pass = all(row["status"] == "pass" for row in static_audit)
    lines = [
        "# V5 QMT Model Retest Packet",
        "",
        f"- Backtest window: `{BACKTEST_START}` to `{BACKTEST_END}`.",
        f"- Effective first signal: `{EFFECTIVE_FIRST_SIGNAL}`.",
        f"- Ready models: `{len(ready)}`.",
        f"- Static no-order audit: `{'pass' if audit_pass else 'fail'}`.",
        f"- Blocker count: `{len(blockers)}`.",
        "",
        "## Local Expected Ranking",
        "",
    ]
    for row in comparison:
        lines.append(
            f"{row['rank_by_local_delta']}. `{row['model_id']}`: "
            f"return `{float(row['expected_strategy_return_pct']):.2f}%`, "
            f"delta `{float(row['delta_return_pct_points_vs_repaired_baseline']):.2f}` pct points, "
            f"max drawdown `{float(row['expected_max_drawdown_pct']):.2f}%`."
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "The packet is ready for a manual QMT model-research replay. It is not an acceptance or live-trading gate.",
        ]
    )
    return "\n".join(lines) + "\n"


def _summary(status: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    data = {
        "created_at_utc": now_utc(),
        "task": "v5_qmt_model_retest_packet",
        "status": status,
        "backtest_start": BACKTEST_START,
        "effective_first_signal": EFFECTIVE_FIRST_SIGNAL,
        "backtest_end": BACKTEST_END,
        "accepted": False,
        "live_trading_approved": False,
        "real_order_function_used": False,
        "qmt_manual_run_required": True,
        "fatal_blocker_count": len(blockers),
        "fatal_blockers": blockers,
    }
    data.update(extra)
    return data


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        number = float(value)
        if math.isnan(number):
            return None
        return number
    except (TypeError, ValueError):
        return None


def _as_pct(value: Any) -> float:
    return (_safe_float(value) or 0.0) * 100.0


def _to_qmt_code(code: str) -> str:
    if code.endswith(".XSHG"):
        return code[:6] + ".SH"
    if code.endswith(".XSHE"):
        return code[:6] + ".SZ"
    return code


if __name__ == "__main__":
    run_v5_qmt_model_retest_packet()

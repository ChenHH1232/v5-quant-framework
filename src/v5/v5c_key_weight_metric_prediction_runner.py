from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


OUT_DIR = Path("v5c_key_weight_metric_prediction") / "current"

P1_PANEL = Path("v5c_p1_financial_quality_pit_panel") / "current" / "v5c_p1_financial_quality_pit_panel.csv"
P2_VALUATION = Path("v5c_p2_valuation_and_crowding_state_panel") / "current" / "v5c_p2_valuation_state_panel.csv"
FIN_EXPECT_SUMMARY = Path("v5c_financial_statement_expectation_layer") / "current" / "v5c_financial_expectation_summary.json"
FORWARD_SUMMARY = Path("v5c_forward_financial_statement_tracking") / "current" / "v5c_forward_financial_statement_tracking_summary.json"
PRE2021_SUMMARY = Path("pre2021_financial_expectation_panel_extension") / "current" / "pre2021_financial_expectation_summary.json"

DATABASE = Path("\u6570\u636e\u5e93") / "processed"
PRE_BANK = DATABASE / "low_volatility_factors_v56" / "bank_v3" / "panel_with_low_vol.csv"
PRE_POWER = DATABASE / "low_volatility_factors_v56" / "utilities_v51f" / "panel_with_low_vol.csv"
PRE_HIGHWAY = DATABASE / "pre2021_repaired_factor_panels_v5" / "highway_v54h" / "strict_pit_panel_with_low_vol.csv"
PRE_PORT_RAIL = DATABASE / "pre2021_repaired_factor_panels_v5" / "port_rail_v55j" / "strict_pit_panel_with_low_vol.csv"

FORMAL_START = "2021-05-01"
FORMAL_END = "2026-05-31"
PRE2021_END = "2021-04-30"

KEY_METRICS: tuple[dict[str, Any], ...] = (
    {"metric_id": "low_pb", "field": "low_price_to_book", "direction": "lower_better", "family": "valuation", "sleeves": "all"},
    {"metric_id": "dividend_yield", "field": "dividend_yield_decimal", "pre_field": "dividend_yield", "direction": "higher_better", "family": "dividend", "sleeves": "all"},
    {"metric_id": "roe", "field": "return_on_equity_ttm", "direction": "higher_better", "family": "quality", "sleeves": "all"},
    {"metric_id": "ocf_yield", "field": "operating_cash_flow_yield", "direction": "higher_better", "family": "cashflow", "sleeves": "non_bank"},
    {"metric_id": "cash_conversion", "field": "operating_cash_flow_to_net_profit", "direction": "higher_better", "family": "cashflow_quality", "sleeves": "non_bank"},
    {"metric_id": "capex_burden", "field": "capex_burden", "direction": "lower_better", "family": "capex", "sleeves": "non_bank"},
    {"metric_id": "asset_liability", "field": "asset_liability_ratio", "direction": "lower_better", "family": "balance_sheet", "sleeves": "non_bank"},
    {"metric_id": "bank_npl", "field": "non_performing_loan_ratio", "direction": "lower_better", "family": "bank_asset_quality", "sleeves": ("bank",)},
    {"metric_id": "bank_provision", "field": "provision_coverage_ratio", "direction": "higher_better", "family": "bank_asset_quality", "sleeves": ("bank",)},
    {"metric_id": "bank_cet1", "field": "core_tier_1_capital_adequacy_ratio", "direction": "higher_better", "family": "bank_capital", "sleeves": ("bank",)},
    {"metric_id": "pcf_inverse", "field": "pcf_ncf_ttm_inverse_proxy", "direction": "higher_better", "family": "cashflow_valuation_proxy", "sleeves": ("highway_infrastructure", "port_rail_infrastructure"), "formal_allowed": False},
    {"metric_id": "cash_dividend_per_share", "field": "dividend_cash_per_share_used", "direction": "higher_better", "family": "dividend", "sleeves": ("highway_infrastructure", "port_rail_infrastructure"), "formal_allowed": False},
)


def run_v5c_key_weight_metric_prediction(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5c_key_weight_metric_prediction_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_missing_required_input", blockers)
        _write_json(out / "v5c_key_weight_metric_prediction_summary.json", summary)
        return summary

    formal_panel = _formal_panel(root)
    pre_panel = _pre2021_panel(root)
    schema = _metric_schema(formal_panel, pre_panel)
    formal_predictions = _prediction_panel(formal_panel, "formal_backtest_observation")
    pre_predictions = _prediction_panel(pre_panel, "pre2021_train_test")
    all_predictions = formal_predictions + pre_predictions
    accuracy = _accuracy(all_predictions)
    recommended = _recommended_tracking_metrics(accuracy)
    forward_ledger = _forward_key_metric_ledger(formal_predictions, accuracy)
    governance = _governance(formal_predictions, pre_predictions)
    decision = _pm_decision(accuracy, recommended, governance)
    freeze = _freeze_decision(accuracy, decision[0])
    next_queue = _next_queue(decision[0], freeze[0])
    blockers_out = _nonfatal_blockers(accuracy, recommended)

    _write_csv(out / "v5c_key_weight_metric_schema.csv", schema)
    _write_csv(out / "v5c_key_weight_metric_prediction_panel.csv", all_predictions)
    _write_csv(out / "v5c_key_weight_metric_formal_prediction_panel.csv", formal_predictions)
    _write_csv(out / "v5c_key_weight_metric_pre2021_prediction_panel.csv", pre_predictions)
    _write_csv(out / "v5c_key_weight_metric_accuracy.csv", accuracy)
    _write_csv(out / "v5c_key_weight_metric_recommended_tracking.csv", recommended)
    _write_csv(out / "v5c_key_weight_metric_forward_tracking_ledger.csv", forward_ledger)
    _write_csv(out / "v5c_key_weight_metric_governance_audit.csv", governance)
    _write_csv(out / "v5c_key_weight_metric_v5f_freeze_decision.csv", freeze)
    _write_csv(out / "v5c_key_weight_metric_pm_gate_decision.csv", decision)
    _write_csv(out / "v5c_key_weight_metric_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5c_key_weight_metric_prediction_blockers.csv", blockers_out)
    (out / "v5c_key_weight_metric_prediction_report.md").write_text(
        _report(accuracy, recommended, decision, freeze, next_queue),
        encoding="utf-8",
    )
    (out / "v5c_key_weight_metric_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    pre_overall = _find_accuracy(accuracy, "pre2021_train_test", "ALL", "ALL")
    formal_overall = _find_accuracy(accuracy, "formal_backtest_observation", "ALL", "ALL")
    summary = _summary(
        "completed_key_weight_metric_prediction",
        decision[0]["pm_gate_decision"],
        blockers_out,
        formal_rows=len(formal_predictions),
        pre2021_rows=len(pre_predictions),
        formal_bucket_hit_rate=float(formal_overall.get("bucket_hit_rate", 0.0) or 0.0),
        pre2021_bucket_hit_rate=float(pre_overall.get("bucket_hit_rate", 0.0) or 0.0),
        formal_active_direction_hit_rate=float(formal_overall.get("active_direction_hit_rate", 0.0) or 0.0),
        pre2021_active_direction_hit_rate=float(pre_overall.get("active_direction_hit_rate", 0.0) or 0.0),
        recommended_metric_count=sum(1 for row in recommended if row["recommend_forward_tracking"] == "True"),
        v5f_weight_confidence_spec_status=freeze[0]["v5f_weight_confidence_tag_spec_status"],
    )
    _write_json(out / "v5c_key_weight_metric_prediction_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def _formal_panel(root: Path) -> pd.DataFrame:
    p1 = pd.read_csv(root / P1_PANEL, dtype=str)
    p2 = pd.read_csv(root / P2_VALUATION, dtype=str)
    p2_cols = [
        "trade_date",
        "code",
        "sleeve_id",
        "low_price_to_book",
        "valuation_state",
        "valuation_cheapness_score",
        "pit_status",
    ]
    panel = p1.merge(p2[[col for col in p2_cols if col in p2.columns]], on=["trade_date", "code", "sleeve_id"], how="left", suffixes=("", "_p2"))
    panel["sample_scope"] = "formal_backtest_observation"
    panel["source_panel"] = str(P1_PANEL).replace("\\", "/")
    panel = panel[(panel["trade_date"] >= FORMAL_START) & (panel["trade_date"] <= FORMAL_END)].copy()
    return panel


def _pre2021_panel(root: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    source_specs = [
        (PRE_BANK, "bank"),
        (PRE_POWER, "utilities_electricity"),
        (PRE_HIGHWAY, "highway_infrastructure"),
        (PRE_PORT_RAIL, "port_rail_infrastructure"),
    ]
    for path, sleeve in source_specs:
        frame = pd.read_csv(root / path, dtype=str)
        frame = frame[frame["trade_date"] <= PRE2021_END].copy()
        frame["sleeve_id"] = sleeve
        frame["sample_scope"] = "pre2021_train_test"
        frame["source_panel"] = str(path).replace("\\", "/")
        if "dividend_yield_decimal" not in frame.columns and "dividend_yield" in frame.columns:
            frame["dividend_yield_decimal"] = frame["dividend_yield"]
        if "financial_visible_date" not in frame.columns:
            frame["financial_visible_date"] = frame.get("factor_visible_date", frame["trade_date"])
        if "visible_date_status" not in frame.columns:
            frame["visible_date_status"] = "pass"
        if "pit_status" not in frame.columns:
            frame["pit_status"] = frame.get("pre2021_universe_pit_status", "pass")
        frames.append(frame)
    return pd.concat(frames, ignore_index=True, sort=False)


def _prediction_panel(panel: pd.DataFrame, sample_scope: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for metric in KEY_METRICS:
        if sample_scope == "formal_backtest_observation" and metric.get("formal_allowed") is False:
            continue
        metric_panel = _metric_rows(panel, metric)
        if metric_panel.empty:
            continue
        metric_panel = _add_buckets(metric_panel, metric)
        for code, group in metric_panel.groupby("code", sort=True):
            group = group.sort_values("trade_date").reset_index(drop=True)
            for i, row in group.iterrows():
                prev_row = group.iloc[i - 1] if i > 0 else None
                next_row = group.iloc[i + 1] if i + 1 < len(group) else None
                predicted_bucket = row["current_bucket"]
                actual_bucket = "pending" if next_row is None else next_row["current_bucket"]
                predicted_direction = _prior_direction(prev_row, row)
                actual_direction = "pending" if next_row is None else _move_direction(row["oriented_value"], next_row["oriented_value"])
                rows.append(
                    {
                        "prediction_id": f"keymetric_{sample_scope}_{len(rows) + 1:07d}",
                        "sample_scope": sample_scope,
                        "trade_date": row["trade_date"],
                        "next_observation_date": "" if next_row is None else next_row["trade_date"],
                        "code": code,
                        "sleeve_id": row["sleeve_id"],
                        "metric_id": metric["metric_id"],
                        "field": row["field"],
                        "family": metric["family"],
                        "direction": metric["direction"],
                        "raw_value": row["raw_value"],
                        "favorable_percentile": row["favorable_percentile"],
                        "predicted_next_bucket": predicted_bucket,
                        "actual_next_bucket": actual_bucket,
                        "bucket_hit": _hit(predicted_bucket, actual_bucket),
                        "predicted_next_direction": predicted_direction,
                        "actual_next_direction": actual_direction,
                        "direction_hit": _hit(predicted_direction, actual_direction),
                        "source_panel": row.get("source_panel", ""),
                        "pit_status": row.get("pit_status", ""),
                        "allowed_use": "key_metric_forward_tracking_only",
                        "trade_impact": "none",
                        "weight_impact": "none",
                        "accepted": False,
                    }
                )
    return rows


def _metric_rows(panel: pd.DataFrame, metric: dict[str, Any]) -> pd.DataFrame:
    field = str(metric.get("field", ""))
    if field not in panel.columns:
        return pd.DataFrame()
    metric_panel = panel.copy()
    if not _metric_allowed_for_sleeve(metric, metric_panel):
        return pd.DataFrame()
    metric_panel = metric_panel[metric_panel["sleeve_id"].apply(lambda sleeve: _sleeve_allowed(metric, str(sleeve)))].copy()
    metric_panel["raw_value"] = pd.to_numeric(metric_panel[field], errors="coerce")
    metric_panel = metric_panel[metric_panel["raw_value"].notna()].copy()
    metric_panel["field"] = field
    return metric_panel


def _metric_allowed_for_sleeve(metric: dict[str, Any], panel: pd.DataFrame) -> bool:
    return bool(len(panel))


def _sleeve_allowed(metric: dict[str, Any], sleeve: str) -> bool:
    allowed = metric.get("sleeves")
    if allowed == "all":
        return True
    if allowed == "non_bank":
        return sleeve != "bank"
    return sleeve in set(allowed)


def _add_buckets(metric_panel: pd.DataFrame, metric: dict[str, Any]) -> pd.DataFrame:
    out = metric_panel.copy()
    direction = -1.0 if metric["direction"] == "lower_better" else 1.0
    out["oriented_value"] = out["raw_value"] * direction
    out["favorable_percentile"] = out.groupby(["trade_date", "sleeve_id"])["oriented_value"].rank(pct=True, method="average")
    out["current_bucket"] = "middle"
    out.loc[out["favorable_percentile"] >= 2 / 3, "current_bucket"] = "favorable"
    out.loc[out["favorable_percentile"] <= 1 / 3, "current_bucket"] = "unfavorable"
    out.loc[out["favorable_percentile"].isna(), "current_bucket"] = "missing"
    return out


def _prior_direction(prev_row: pd.Series | None, row: pd.Series) -> str:
    if prev_row is None:
        return "unknown"
    return _move_direction(prev_row["oriented_value"], row["oriented_value"])


def _move_direction(old: Any, new: Any) -> str:
    old_val = _safe_float(old)
    new_val = _safe_float(new)
    if old_val is None or new_val is None:
        return "unknown"
    eps = max(abs(old_val) * 0.02, 0.001)
    delta = new_val - old_val
    if abs(delta) <= eps:
        return "stable"
    return "improve" if delta > 0 else "deteriorate"


def _hit(predicted: str, actual: str) -> str:
    if predicted in {"unknown", "missing"} or actual in {"pending", "unknown", "missing"}:
        return "not_scored"
    return "hit" if predicted == actual else "miss"


def _accuracy(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    keys = sorted({(row["sample_scope"], row["sleeve_id"], row["metric_id"]) for row in rows})
    for key in keys:
        subset = [row for row in rows if (row["sample_scope"], row["sleeve_id"], row["metric_id"]) == key]
        output.append(_accuracy_row(*key, subset))
    for sample_scope in sorted({row["sample_scope"] for row in rows}):
        subset = [row for row in rows if row["sample_scope"] == sample_scope]
        output.append(_accuracy_row(sample_scope, "ALL", "ALL", subset))
    output.append(_accuracy_row("ALL", "ALL", "ALL", rows))
    return output


def _accuracy_row(sample_scope: str, sleeve_id: str, metric_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    bucket_scored = [row for row in rows if row["bucket_hit"] in {"hit", "miss"}]
    bucket_hits = sum(1 for row in bucket_scored if row["bucket_hit"] == "hit")
    direction_scored = [row for row in rows if row["direction_hit"] in {"hit", "miss"}]
    direction_hits = sum(1 for row in direction_scored if row["direction_hit"] == "hit")
    active_direction = [row for row in direction_scored if row["predicted_next_direction"] in {"improve", "deteriorate"}]
    active_hits = sum(1 for row in active_direction if row["direction_hit"] == "hit")
    favorable_scored = [row for row in bucket_scored if row["predicted_next_bucket"] == "favorable"]
    favorable_hits = sum(1 for row in favorable_scored if row["bucket_hit"] == "hit")
    return {
        "sample_scope": sample_scope,
        "sleeve_id": sleeve_id,
        "metric_id": metric_id,
        "event_count": len(rows),
        "bucket_scored_count": len(bucket_scored),
        "bucket_hit_count": bucket_hits,
        "bucket_hit_rate": _ratio(bucket_hits, len(bucket_scored)),
        "favorable_bucket_scored_count": len(favorable_scored),
        "favorable_bucket_hit_count": favorable_hits,
        "favorable_bucket_hit_rate": _ratio(favorable_hits, len(favorable_scored)),
        "direction_scored_count": len(direction_scored),
        "direction_hit_count": direction_hits,
        "direction_hit_rate": _ratio(direction_hits, len(direction_scored)),
        "active_direction_scored_count": len(active_direction),
        "active_direction_hit_count": active_hits,
        "active_direction_hit_rate": _ratio(active_hits, len(active_direction)),
        "predicted_bucket_distribution": _counter(rows, "predicted_next_bucket"),
        "actual_bucket_distribution": _counter(rows, "actual_next_bucket"),
        "role": "key_metric_prediction_not_overall_financial_state",
    }


def _recommended_tracking_metrics(accuracy: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in accuracy:
        if row["sample_scope"] not in {"pre2021_train_test", "formal_backtest_observation"} or row["metric_id"] == "ALL":
            continue
        bucket_hit = float(row["bucket_hit_rate"] or 0.0)
        fav_hit = float(row["favorable_bucket_hit_rate"] or 0.0)
        scored = int(row["bucket_scored_count"] or 0)
        tracking_tier = "diagnostic_only"
        if scored >= 50 and bucket_hit >= 0.75 and fav_hit >= 0.80:
            tracking_tier = "strong_key_metric_tracking"
        elif scored >= 50 and bucket_hit >= 0.60 and fav_hit >= 0.65:
            tracking_tier = "key_metric_tracking"
        elif scored >= 25 and bucket_hit >= 0.70 and fav_hit >= 0.75:
            tracking_tier = "small_sample_key_metric_tracking"
        recommended = tracking_tier != "diagnostic_only"
        rows.append(
            {
                "sample_scope": row["sample_scope"],
                "sleeve_id": row["sleeve_id"],
                "metric_id": row["metric_id"],
                "bucket_scored_count": scored,
                "bucket_hit_rate": bucket_hit,
                "favorable_bucket_hit_rate": fav_hit,
                "active_direction_hit_rate": row["active_direction_hit_rate"],
                "tracking_tier": tracking_tier,
                "recommend_forward_tracking": str(recommended),
                "recommend_weight_use": False,
                "reason": "track_bucket_stability_only" if recommended else "insufficient_bucket_stability_or_sample",
            }
        )
    return rows


def _forward_key_metric_ledger(formal_predictions: list[dict[str, Any]], accuracy: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in sorted(formal_predictions, key=lambda item: item["trade_date"]):
        latest_by_key[(row["code"], row["metric_id"])] = row
    accuracy_map = {(row["sample_scope"], row["sleeve_id"], row["metric_id"]): row for row in accuracy}
    ledger = []
    for idx, row in enumerate(sorted(latest_by_key.values(), key=lambda item: (item["sleeve_id"], item["code"], item["metric_id"])), start=1):
        acc = accuracy_map.get(("formal_backtest_observation", row["sleeve_id"], row["metric_id"]), {})
        ledger.append(
            {
                "tracking_id": f"keymetric_forward_{idx:06d}",
                "record_date": row["trade_date"],
                "code": row["code"],
                "sleeve_id": row["sleeve_id"],
                "metric_id": row["metric_id"],
                "field": row["field"],
                "current_bucket": row["predicted_next_bucket"],
                "current_favorable_percentile": row["favorable_percentile"],
                "predicted_next_bucket": row["predicted_next_bucket"],
                "predicted_next_direction": row["predicted_next_direction"],
                "historical_bucket_hit_rate": acc.get("bucket_hit_rate", ""),
                "historical_active_direction_hit_rate": acc.get("active_direction_hit_rate", ""),
                "actual_next_bucket": "",
                "actual_next_direction": "",
                "closeout_status": "open",
                "allowed_use": "forward_key_metric_tracking_only",
                "trade_impact": "none",
                "weight_impact": "none",
                "accepted": False,
            }
        )
    return ledger


def _metric_schema(formal_panel: pd.DataFrame, pre_panel: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for metric in KEY_METRICS:
        formal_field = metric["field"]
        pre_field = metric.get("pre_field", metric["field"])
        rows.append(
            {
                "metric_id": metric["metric_id"],
                "formal_field": formal_field,
                "pre2021_field": pre_field,
                "direction": metric["direction"],
                "family": metric["family"],
                "sleeves": metric["sleeves"] if isinstance(metric["sleeves"], str) else ";".join(metric["sleeves"]),
                "formal_available_rows": int(pd.to_numeric(formal_panel[formal_field], errors="coerce").notna().sum()) if formal_field in formal_panel.columns and metric.get("formal_allowed", True) else 0,
                "pre2021_available_rows": int(pd.to_numeric(pre_panel[pre_field], errors="coerce").notna().sum()) if pre_field in pre_panel.columns else 0,
                "prediction_target": "next_same_sleeve_metric_bucket_and_direction",
                "not_overall_financial_state": True,
                "can_change_weight": False,
                "accepted": False,
            }
        )
    return rows


def _governance(formal_predictions: list[dict[str, Any]], pre_predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    all_rows = formal_predictions + pre_predictions
    formal_dates = [row["trade_date"] for row in formal_predictions]
    pre_dates = [row["trade_date"] for row in pre_predictions]
    return [
        _audit("predicts_key_metrics_not_overall_state", True, "metric_id rows only"),
        _audit("no_trade_impact", all(row["trade_impact"] == "none" for row in all_rows), _counter(all_rows, "trade_impact")),
        _audit("no_weight_impact", all(row["weight_impact"] == "none" for row in all_rows), _counter(all_rows, "weight_impact")),
        _audit("accepted_false", all(str(row["accepted"]) == "False" for row in all_rows), _counter(all_rows, "accepted")),
        _audit("pre2021_split_clean", bool(pre_dates) and max(pre_dates) < FORMAL_START, f"{min(pre_dates) if pre_dates else ''}..{max(pre_dates) if pre_dates else ''}"),
        _audit("formal_scope_observation_only", bool(formal_dates) and min(formal_dates) >= FORMAL_START and max(formal_dates) <= FORMAL_END, f"{min(formal_dates) if formal_dates else ''}..{max(formal_dates) if formal_dates else ''}"),
    ]


def _pm_decision(
    accuracy: list[dict[str, Any]],
    recommended: list[dict[str, Any]],
    governance: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    passed = all(row["audit_status"] == "pass" for row in governance)
    pre_overall = _find_accuracy(accuracy, "pre2021_train_test", "ALL", "ALL")
    pre_bucket = float(pre_overall.get("bucket_hit_rate", 0.0) or 0.0)
    recommended_count = sum(1 for row in recommended if row["recommend_forward_tracking"] == "True")
    if not passed:
        gate = "key_metric_prediction_blocked_by_governance"
    elif recommended_count and pre_bucket >= 0.35:
        gate = "key_metric_bucket_forward_tracking_ready_not_weight_use"
    else:
        gate = "key_metric_prediction_diagnostic_only"
    return [
        {
            "pm_gate_decision": gate,
            "admit_key_metric_forward_tracking": str(passed and recommended_count > 0),
            "admit_v5f_weight_confidence_spec": False,
            "admit_trading_rule": False,
            "admit_weight_change": False,
            "accepted": False,
            "live_approved": False,
            "v57f_core_modified": False,
            "v5f_primary_modified": False,
            "next_step": "track_recommended_key_metric_buckets_only" if recommended_count else "keep_diagnostic_only",
        }
    ]


def _freeze_decision(accuracy: list[dict[str, Any]], decision: dict[str, Any]) -> list[dict[str, Any]]:
    pre_overall = _find_accuracy(accuracy, "pre2021_train_test", "ALL", "ALL")
    formal_overall = _find_accuracy(accuracy, "formal_backtest_observation", "ALL", "ALL")
    return [
        {
            "v5f_weight_confidence_tag_spec_status": "still_blocked",
            "reason": "key metric bucket tracking is more useful than overall state, but it is not yet approved to alter weights",
            "pre2021_bucket_hit_rate": pre_overall.get("bucket_hit_rate", ""),
            "formal_bucket_hit_rate": formal_overall.get("bucket_hit_rate", ""),
            "required_before_reopen": "forward closeout must show key metric bucket stability is actionable and pre-registered",
            "admit_engineering_backtest_now": False,
            "admit_weight_change_now": False,
            "accepted": False,
        }
    ]


def _next_queue(decision: dict[str, Any], freeze: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_gate": "v5c_key_weight_metric_forward_closeout",
            "allowed": decision["admit_key_metric_forward_tracking"],
            "scope": "Close out only the recommended key metric bucket predictions when next PIT fields become visible.",
            "blocked_until": "next financial/factor panel refresh",
        },
        {
            "priority": 2,
            "next_gate": "v5c_key_metric_manual_source_review",
            "allowed": "optional",
            "scope": "Review high-value metrics with original reports if a specific field is selected later.",
            "blocked_until": "",
        },
        {
            "priority": 3,
            "next_gate": "v5f_weight_confidence_tag_spec",
            "allowed": "False",
            "scope": "No engineering backtest or weight change now.",
            "blocked_until": freeze["required_before_reopen"],
        },
    ]


def _nonfatal_blockers(accuracy: list[dict[str, Any]], recommended: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers = []
    pre_overall = _find_accuracy(accuracy, "pre2021_train_test", "ALL", "ALL")
    if float(pre_overall.get("active_direction_hit_rate", 0.0) or 0.0) < 0.5:
        blockers.append(
            {
                "blocker_id": "direction_prediction_still_weak",
                "severity": "nonfatal",
                "status": "diagnostic",
                "description": "Directional improve/deteriorate prediction remains weak; use bucket tracking instead.",
            }
        )
    if not any(row["recommend_forward_tracking"] == "True" for row in recommended):
        blockers.append(
            {
                "blocker_id": "no_metric_recommended",
                "severity": "nonfatal",
                "status": "diagnostic",
                "description": "No key metric passed the minimum forward tracking threshold.",
            }
        )
    return blockers


def _report(
    accuracy: list[dict[str, Any]],
    recommended: list[dict[str, Any]],
    decision: list[dict[str, Any]],
    freeze: list[dict[str, Any]],
    next_queue: list[dict[str, Any]],
) -> str:
    formal = _find_accuracy(accuracy, "formal_backtest_observation", "ALL", "ALL")
    pre = _find_accuracy(accuracy, "pre2021_train_test", "ALL", "ALL")
    rec_lines = "\n".join(
        f"- {row['sample_scope']} / {row['sleeve_id']} / {row['metric_id']}: bucket {float(row['bucket_hit_rate']):.2%}, favorable {float(row['favorable_bucket_hit_rate']):.2%}"
        for row in recommended
        if row["recommend_forward_tracking"] == "True"
    ) or "- None"
    queue_lines = "\n".join(f"- P{row['priority']} {row['next_gate']}: allowed={row['allowed']}" for row in next_queue)
    return f"""# V5c Key Weight Metric Prediction

## Purpose
This packet replaces broad financial-state prediction with key metric prediction. It predicts each weight-relevant field's next same-sleeve bucket and metric direction separately.

## Overall Result
- Formal bucket hit rate: {float(formal.get('bucket_hit_rate', 0.0) or 0.0):.2%}
- Formal active direction hit rate: {float(formal.get('active_direction_hit_rate', 0.0) or 0.0):.2%}
- Pre-2021 bucket hit rate: {float(pre.get('bucket_hit_rate', 0.0) or 0.0):.2%}
- Pre-2021 active direction hit rate: {float(pre.get('active_direction_hit_rate', 0.0) or 0.0):.2%}

## Recommended Forward Tracking
{rec_lines}

## Governance
- This is not an overall financial statement model.
- Trading impact: none.
- Weight impact: none.
- Accepted: false.
- V5f weight confidence spec: {freeze[0]['v5f_weight_confidence_tag_spec_status']}.

## PM Gate
- Decision: {decision[0]['pm_gate_decision']}

## Next Queue
{queue_lines}
"""


def _rules() -> str:
    return """# Agent Execution Rules

- Predict only key weight metrics, not overall financial statement quality.
- Use bucket persistence and metric direction separately.
- Do not change V57f, V5f, orders, or weights.
- Do not use this packet to mark accepted or live approved.
- V5f weight-confidence engineering remains blocked until forward closeout evidence is stronger.
"""


def _find_accuracy(accuracy: list[dict[str, Any]], sample_scope: str, sleeve_id: str, metric_id: str) -> dict[str, Any]:
    return next((row for row in accuracy if row["sample_scope"] == sample_scope and row["sleeve_id"] == sleeve_id and row["metric_id"] == metric_id), {})


def _audit(audit_id: str, passed: bool, observed: str) -> dict[str, Any]:
    return {"audit_id": audit_id, "audit_status": "pass" if passed else "fail", "observed": observed, "required": True}


def _safe_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(parsed):
        return None
    return parsed


def _ratio(num: int | float, den: int | float) -> float:
    return float(num) / float(den) if den else 0.0


def _counter(rows: list[dict[str, Any]], field: str) -> str:
    counts = Counter(str(row.get(field, "")) for row in rows)
    return ";".join(f"{key}:{counts[key]}" for key in sorted(counts))


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [P1_PANEL, P2_VALUATION, FIN_EXPECT_SUMMARY, FORWARD_SUMMARY, PRE2021_SUMMARY, PRE_BANK, PRE_POWER, PRE_HIGHWAY, PRE_PORT_RAIL]
    return [
        {
            "blocker_id": str(path).replace("\\", "/"),
            "severity": "fatal",
            "status": "missing_required_input",
            "description": "Required local input is missing.",
        }
        for path in required
        if not (root / path).exists()
    ]


def _summary(status: str, gate: str, blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "status": status,
        "pm_gate_decision": gate,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "accepted": False,
        "live_approved": False,
        "v57f_core_modified": False,
        "v5f_primary_modified": False,
        "trade_rule_added": False,
        "weight_change_added": False,
        "overall_financial_state_prediction_used": False,
        "fatal_blocker_count": sum(1 for row in blockers if row.get("severity") == "fatal"),
        "blocker_count": len(blockers),
    }
    summary.update(extra)
    return summary


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    run_v5c_key_weight_metric_prediction()

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WEIGHTS = Path("v5f_pre2021_multisleeve_mainline_validation") / "current" / "v5f_pre2021_p1_mainline_weights.csv"
V5H_SUMMARY = Path("v5h_buy_execution_backtest") / "current" / "v5h_buy_execution_backtest_summary.json"
MINUTE_DIR = Path("数据库") / "processed" / "local_1min_clean_2013_2026" / "by_year"
OUT_DIR = Path("v5j_technical_existing_model_validation") / "current"
MODEL = "internal_subsleeve_mom12_70_30"
PRE_START = "2019-04-01"
PRE_END = "2020-12-31"


def run_v5j_technical_existing_model_validation(root: Path = Path(".")) -> dict[str, Any]:
    if not (root / WEIGHTS).exists() or not (root / V5H_SUMMARY).exists():
        raise FileNotFoundError("Pre-2021 V5f weights and frozen V5h backtest summary are required.")
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    weights = [row for row in _read_csv(root / WEIGHTS) if row.get("version_id") == MODEL]
    intents = _entry_proxy_intents(weights)
    evaluations = [_evaluate(root, intent) for intent in intents]
    result = _result(evaluations)
    v5h = json.loads((root / V5H_SUMMARY).read_text(encoding="utf-8-sig"))
    data_gate = _data_gate(intents, evaluations)
    governance = _governance()
    gate = _gate(result, v5h, data_gate)
    summary = {
        "created_at_utc": _now(),
        "task": "v5j_technical_existing_model_validation",
        "status": "completed_pre2021_fixed_v5h_validation",
        "primary_model": MODEL,
        "frozen_technical_rule": "pressure_positive_1000_else_1400_buy",
        "pre2021_validation_start": PRE_START,
        "pre2021_validation_end": PRE_END,
        "entry_proxy_count": len(intents),
        "pre2021_incremental_edge_bps": result["incremental_edge_bps"],
        "formal_v5h_incremental_return_pct_points": v5h.get("delta_return_pct_points_vs_v5f_primary"),
        "pm_gate_decision": gate["pm_gate_decision"],
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "v5f_mainline_modified": False,
        "new_buy_signal_used": False,
        "threshold_scan_used": False,
        "joinquant_started": False,
    }
    _write_csv(out / "v5j_pre2021_entry_proxy_intents.csv", intents)
    _write_csv(out / "v5j_pre2021_fixed_v5h_event_evaluation.csv", evaluations)
    _write_csv(out / "v5j_pre2021_fixed_v5h_result.csv", [result])
    _write_csv(out / "v5j_technical_data_gate.csv", data_gate)
    _write_csv(out / "v5j_technical_governance_audit.csv", governance)
    _write_csv(out / "v5j_technical_pm_gate_decision.csv", [gate])
    _write_csv(out / "v5j_technical_next_queue.csv", _next_queue(gate))
    _write_json(out / "v5j_technical_existing_model_validation_summary.json", summary)
    (out / "v5j_technical_existing_model_validation_report.md").write_text(_report(summary, result, gate), encoding="utf-8")
    return summary


def _entry_proxy_intents(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_date[row["rebalance_date"]].append(row)
    dates = sorted(by_date)
    out: list[dict[str, str]] = []
    prior_codes: set[str] = set()
    for index, date in enumerate(dates):
        current = by_date[date]
        current_codes = {row["code"] for row in current}
        chosen = current if index == 0 else [row for row in current if row["code"] not in prior_codes]
        for row in chosen:
            out.append({
                "intent_id": f"pre2021_entry_proxy|{date}|{row['code']}",
                "trade_date": date,
                "code": row["code"],
                "sleeve": row.get("sector_id", ""),
                "entry_proxy_type": "initial_portfolio_load" if index == 0 else "new_pool_member_only",
                "target_weight": row.get("target_weight", ""),
                "immutable_before_intraday": True,
                "technical_rule_can_create_buy": False,
            })
        prior_codes = current_codes
    return out


def _evaluate(root: Path, intent: dict[str, str]) -> dict[str, Any]:
    bars = _load_day(root, intent["code"], intent["trade_date"])
    index = {row["time"]: row for row in bars}
    pressure = _amount_pressure([row for row in bars if row["time"] <= "10:00:00"])
    pressure_positive = pressure >= 0.10
    baseline = _fill(index, "10:01:00")
    selected_time = "10:01:00" if pressure_positive else "14:01:00"
    selected = _fill(index, selected_time)
    close = _float(bars[-1].get("close")) if bars else 0.0
    baseline_price = _float(baseline.get("open")) if baseline else 0.0
    selected_price = _float(selected.get("open")) if selected else 0.0
    base_edge = close / baseline_price - 1.0 if baseline_price else 0.0
    selected_edge = close / selected_price - 1.0 if selected_price else 0.0
    return {
        **intent,
        "minute_row_count": len(bars),
        "amount_pressure_to_1000": pressure,
        "amount_pressure_bucket": "positive_pressure" if pressure_positive else "not_positive_pressure",
        "baseline_execution_time": "10:01:00",
        "selected_execution_time": selected_time,
        "baseline_price": baseline_price,
        "selected_price": selected_price,
        "day_close_outcome_only": close,
        "baseline_edge_vs_close": base_edge,
        "selected_edge_vs_close": selected_edge,
        "incremental_edge": selected_edge - base_edge,
        "pit_status": "pass" if baseline and selected else "missing_bar",
        "accepted": False,
    }


def _load_day(root: Path, code: str, day: str) -> list[dict[str, str]]:
    path = root / MINUTE_DIR / day[:4] / f"{code.replace('.', '_')}_1min.csv"
    if not path.exists():
        return []
    return [row for row in _read_csv(path) if row.get("trade_date") == day]


def _amount_pressure(rows: list[dict[str, str]]) -> float:
    if len(rows) < 2:
        return 0.0
    total = signed = 0.0
    previous = _float(rows[0].get("close"))
    for row in rows[1:]:
        amount = max(_float(row.get("amount")), 0.0)
        current = _float(row.get("close"))
        total += amount
        signed += amount if current > previous else -amount if current < previous else 0.0
        previous = current
    return signed / total if total else 0.0


def _fill(index: dict[str, dict[str, str]], time_value: str) -> dict[str, str] | None:
    row = index.get(time_value)
    return row if row and _float(row.get("open")) > 0 and _float(row.get("volume")) > 0 else None


def _result(rows: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in rows if row["pit_status"] == "pass"]
    positive = [row for row in eligible if _float(row["incremental_edge"]) > 0]
    mean = sum(_float(row["incremental_edge"]) for row in eligible) / len(eligible) if eligible else 0.0
    weighted = _weighted_mean(eligible)
    return {
        "candidate_id": "pressure_positive_1000_else_1400_buy",
        "entry_proxy_count": len(rows),
        "eligible_event_count": len(eligible),
        "positive_event_ratio": len(positive) / len(eligible) if eligible else 0.0,
        "incremental_edge_bps": mean * 10000,
        "weighted_incremental_edge_bps": weighted * 10000,
        "status": "small_pre2021_proxy_validation_only",
        "accepted": False,
    }


def _weighted_mean(rows: list[dict[str, Any]]) -> float:
    values = [(_float(row["incremental_edge"]), _float(row["target_weight"])) for row in rows]
    total = sum(weight for _, weight in values)
    return sum(value * weight for value, weight in values) / total if total else 0.0


def _data_gate(intents: list[dict[str, str]], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"gate_id": "pre2021_pool_boundary", "status": "pass", "value": len(intents), "detail": "Only stocks selected by the pre-2021 repaired V5f pool are used."},
        {"gate_id": "minute_bar_coverage", "status": "pass" if all(row["pit_status"] == "pass" for row in rows) else "fail", "value": sum(row["pit_status"] == "pass" for row in rows), "detail": "Completed 1-minute bars at 10:00, 10:01 and 14:01 are required."},
        {"gate_id": "independent_sample_size", "status": "limited", "value": len(intents), "detail": "Only two auditable pre-2021 pool construction dates exist; result cannot independently promote a model."},
    ]


def _governance() -> list[dict[str, Any]]:
    return [
        {"audit_id": "frozen_rule_only", "status": "pass", "detail": "Uses the existing pressure_positive_1000_else_1400_buy rule without new thresholds."},
        {"audit_id": "no_stock_pool_or_weight_change", "status": "pass", "detail": "Technical state selects only a same-day entry window for a pre-existing entry proxy."},
        {"audit_id": "completed_bar_and_next_bar_fill", "status": "pass", "detail": "Pressure is observed through 10:00; fills are 10:01 or 14:01."},
        {"audit_id": "no_formal_period_tuning", "status": "pass", "detail": "No 2021-2026 observation selects or changes this rule."},
        {"audit_id": "not_accepted_or_live", "status": "pass", "detail": "Research result remains forward-observation only."},
    ]


def _gate(result: dict[str, Any], formal: dict[str, Any], data_gate: list[dict[str, Any]]) -> dict[str, Any]:
    positive = _float(result["weighted_incremental_edge_bps"]) > 0
    return {
        "pm_gate_decision": "v5h_buy_execution_v1_pre2021_directional_support_forward_observation_only" if positive else "v5h_buy_execution_v1_pre2021_not_supported_keep_formal_diagnostic_only",
        "pre2021_weighted_incremental_edge_bps": result["weighted_incremental_edge_bps"],
        "formal_incremental_return_pct_points_vs_v5f": formal.get("delta_return_pct_points_vs_v5f_primary"),
        "independent_sample_size_limited": True,
        "joinquant_historical_backtest_admitted": False,
        "accepted": False,
        "live_trading_approved": False,
        "reason": "Pre-2021 result is only an entry-proxy check over two auditable dates; it cannot authorize a new JoinQuant strategy by itself.",
    }


def _next_queue(gate: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"priority": 1, "task_id": "v5h_buy_execution_v1_forward_observation", "status": "continue", "scope": "Record official planned buys and compare frozen 10:00/14:00 paper fills; no weight or stock selection change."},
        {"priority": 2, "task_id": "v5j_technical_weight_or_sell_overlay", "status": "blocked", "scope": "Do not open a new technical alpha overlay after V5i sell failure and limited pre-2021 entry sample."},
        {"priority": 3, "task_id": "v5f_mainline_joinquant_retest", "status": "separate_existing_queue", "scope": "Keep the validated V5f mainline platform retest independent from V5h execution research."},
    ]


def _report(summary: dict[str, Any], result: dict[str, Any], gate: dict[str, Any]) -> str:
    return "\n".join([
        "# V5j Technical Enhancement of Existing V5f Model",
        "",
        "- Scope: validate the already frozen V5h buy-execution rule, not create a technical stock-selection or weight model.",
        f"- Pre-2021 entry proxies: `{summary['entry_proxy_count']}` from `{PRE_START}` to `{PRE_END}`.",
        f"- Fixed rule incremental edge: `{_float(result['incremental_edge_bps']):.2f}` bps; weighted `{_float(result['weighted_incremental_edge_bps']):.2f}` bps.",
        f"- Existing formal V5h-on-V5f result: `{summary['formal_v5h_incremental_return_pct_points']}` pct points; reported separately and never used to alter the rule.",
        f"- PM gate: `{gate['pm_gate_decision']}`.",
        "- The pre-2021 sample is too small for promotion. No JoinQuant technical overlay is admitted.",
        "",
    ])


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _float(value: Any) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    print(json.dumps(run_v5j_technical_existing_model_validation(), ensure_ascii=False, indent=2))

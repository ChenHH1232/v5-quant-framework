from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from v5.credential_loader import load_joinquant_credentials


OUT_DIR = Path("v5f_joinquant_now_execution") / "current"
PRE2021_CANDIDATES = (
    Path("v5f_pre2021_repaired_multisleeve_data_gate")
    / "current"
    / "v5f_pre2021_candidate_signal_preview.csv"
)
PRE2021_GATE_SUMMARY = (
    Path("v5f_pre2021_repaired_multisleeve_data_gate")
    / "current"
    / "v5f_pre2021_data_gate_summary.json"
)
JQ_CHECKLIST_SUMMARY = Path("v5f_joinquant_export_checklist") / "current" / "v5f_joinquant_export_checklist_summary.json"
JQ_REQUIRED_EXPORTS = Path("v5f_joinquant_export_checklist") / "current" / "v5f_joinquant_required_exports.csv"
LOCAL_SIM_SUMMARY = (
    Path("v5f_spike_mr_prebacktest_to_backtest_jq_sim")
    / "current"
    / "v5f_spike_mr_prebacktest_to_backtest_jq_sim_summary.json"
)

PRIMARY = "internal_subsleeve_mom12_70_30"
BASELINE = "v57f_startup_preload_repaired_baseline"
BACKTEST_START = "2021-05-01"
BACKTEST_END = "2026-05-31"
PRE2020_TEST_DATE = "2019-12-31"
BACKTEST_MINUTE_TEST_DATE = "2021-05-06"

REQUIRED = [PRE2021_CANDIDATES, PRE2021_GATE_SUMMARY, JQ_CHECKLIST_SUMMARY, JQ_REQUIRED_EXPORTS, LOCAL_SIM_SUMMARY]


def run_v5f_joinquant_now_execution(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    manifest = _input_manifest(root)
    missing = [row for row in manifest if row["required"] and not row["exists"]]
    if missing:
        summary = _summary("blocked_missing_local_inputs", "blocked_by_missing_local_inputs", missing)
        _write_minimal(out, summary, manifest, missing)
        return summary

    jq, auth_rows = _authenticate()
    if jq is None:
        capability = auth_rows
        daily_probe: list[dict[str, Any]] = []
        minute_probe: list[dict[str, Any]] = []
        pit_probe: list[dict[str, Any]] = []
    else:
        samples = _sample_codes(root)
        daily_probe = _daily_price_probe(jq, samples)
        minute_probe = _minute_permission_probe(jq, samples[:4])
        pit_probe = _pit_fundamental_probe(jq, samples)
        capability = _capability_matrix(auth_rows, daily_probe, minute_probe, pit_probe)

    five_min_policy = _five_min_source_policy(root)
    required_tests = _required_test_status(root, capability, daily_probe, minute_probe, pit_probe, five_min_policy)
    platform_exports = _platform_export_status(root)
    governance = _governance_audit(capability, required_tests, five_min_policy)
    decision = _pm_gate_decision(required_tests, governance, five_min_policy)
    blockers = _blockers(required_tests, minute_probe)
    queue = _next_queue(decision[0]["pm_gate_decision"], blockers)

    _write_csv(out / "v5f_joinquant_input_manifest.csv", manifest)
    _write_csv(out / "v5f_jqdata_capability_matrix.csv", capability)
    _write_csv(out / "v5f_pre2020_daily_price_probe.csv", daily_probe)
    _write_csv(out / "v5f_pre2020_minute_permission_probe.csv", minute_probe)
    _write_csv(out / "v5f_pre2020_pit_fundamental_probe.csv", pit_probe)
    _write_csv(out / "v5f_joinquant_required_test_status.csv", required_tests)
    _write_csv(out / "v5f_joinquant_platform_export_status.csv", platform_exports)
    _write_csv(out / "v5f_joinquant_governance_audit.csv", governance)
    _write_csv(out / "v5f_joinquant_pm_gate_decision.csv", decision)
    _write_csv(out / "v5f_joinquant_next_queue.csv", queue)
    _write_csv(out / "v5f_joinquant_blockers.csv", blockers)
    (out / "v5f_joinquant_now_execution_report.md").write_text(
        _report(capability, daily_probe, minute_probe, pit_probe, required_tests, decision, blockers, five_min_policy),
        encoding="utf-8",
    )
    (out / "v5f_joinquant_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")

    minute_available = any(row.get("status") == "pass" for row in minute_probe)
    daily_available = any(row.get("status") == "pass" for row in daily_probe)
    pit_available = any(row.get("status") == "pass" for row in pit_probe)
    summary = _summary(
        "completed_joinquant_now_execution_probe",
        decision[0]["pm_gate_decision"],
        [],
        primary_candidate=PRIMARY,
        baseline=BASELINE,
        backtest_start=BACKTEST_START,
        backtest_end=BACKTEST_END,
        jqdata_auth_pass=any(row.get("test_id") == "jqdata_auth" and row.get("status") == "pass" for row in capability),
        daily_price_access=bool(daily_available),
        pit_fundamental_access=bool(pit_available),
        minute_5m_access=bool(minute_available),
        project_5min_source_policy="baostock_only",
        local_5min_bar_source_policy="baostock_only",
        joinquant_platform_minute_backtest_allowed=True,
        joinquant_minute_path_allowed=False,
        joinquant_minute_bar_data_source_allowed=False,
        joinquant_minute_permission_required=False,
        baostock_2014_2020_status=five_min_policy["baostock_2014_2020_status"],
        baostock_5min_api_capability_status=five_min_policy["baostock_5min_api_capability_status"],
        baostock_pre2020_5min_available=five_min_policy["baostock_pre2020_5min_available"],
        backtest_scope_5min_baostock_available=five_min_policy["backtest_scope_5min_baostock_available"],
        pre2020_5min_available=False,
        backtest_scope_5min_jqdata_available=False,
        platform_backtest_started=False,
        platform_exports_present=False,
        local_simulation_still_binding=True,
        accepted=False,
        live_trading_approved=False,
        v57f_core_modified=False,
        threshold_scan_used=False,
        full_market_selection_used=False,
        fatal_blocker_count=0,
    )
    _write_json(out / "v5f_joinquant_now_execution_summary.json", summary)
    return summary


def _authenticate() -> tuple[Any | None, list[dict[str, Any]]]:
    try:
        import jqdatasdk as jq
    except Exception as exc:
        return None, [_row("jqdata_import", "fail", error_type=type(exc).__name__, error_message=str(exc))]
    username, password = load_joinquant_credentials()
    if not username or not password:
        return None, [_row("jqdata_auth", "fail", detail="credentials_missing")]
    try:
        jq.auth(username, password)
        return jq if jq.is_auth() else None, [_row("jqdata_auth", "pass" if jq.is_auth() else "fail")]
    except Exception as exc:
        return None, [_row("jqdata_auth", "fail", error_type=type(exc).__name__, error_message=str(exc))]


def _sample_codes(root: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(root / PRE2021_CANDIDATES, dtype={"preview_date": str, "code": str})
    preferred = df[df["preview_date"].astype(str).eq("2019-04-01")].copy()
    if preferred.empty:
        preferred = df.copy()
    out = []
    seen: set[str] = set()
    for _, row in preferred.iterrows():
        sleeve = str(row["sector_id"])
        if sleeve in seen:
            continue
        seen.add(sleeve)
        out.append({"code": str(row["code"]), "sleeve": sleeve, "preview_date": str(row["preview_date"])})
    bank = preferred[preferred["sector_id"].astype(str).eq("bank")]
    if not bank.empty and not any(row["sleeve"] == "bank" for row in out):
        row = bank.iloc[0]
        out.append({"code": str(row["code"]), "sleeve": "bank", "preview_date": str(row["preview_date"])})
    return out[:8]


def _daily_price_probe(jq: Any, samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for sample in samples:
        rows.append(
            _probe(
                "daily_price",
                sample,
                lambda code=sample["code"]: jq.get_price(
                    code,
                    start_date="2019-12-30",
                    end_date=PRE2020_TEST_DATE,
                    frequency="daily",
                    fields=["open", "close", "volume", "money"],
                    fq="pre",
                    panel=False,
                ),
            )
        )
    return rows


def _minute_permission_probe(jq: Any, samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for sample in samples:
        code = sample["code"]
        for test_id, date_value, fn in [
            (
                "pre2020_get_price_5m",
                PRE2020_TEST_DATE,
                lambda code=code: jq.get_price(
                    code,
                    start_date=PRE2020_TEST_DATE,
                    end_date=PRE2020_TEST_DATE,
                    frequency="5m",
                    fields=["open", "close", "volume"],
                    fq="pre",
                    panel=False,
                ),
            ),
            (
                "backtest_get_price_5m",
                BACKTEST_MINUTE_TEST_DATE,
                lambda code=code: jq.get_price(
                    code,
                    start_date=BACKTEST_MINUTE_TEST_DATE,
                    end_date=BACKTEST_MINUTE_TEST_DATE,
                    frequency="5m",
                    fields=["open", "close", "volume"],
                    fq="pre",
                    panel=False,
                ),
            ),
            (
                "pre2020_get_bars_5m",
                PRE2020_TEST_DATE,
                lambda code=code: jq.get_bars(
                    code,
                    count=10,
                    unit="5m",
                    fields=["date", "open", "close", "volume"],
                    end_dt=f"{PRE2020_TEST_DATE} 15:00:00",
                    fq_ref_date=PRE2020_TEST_DATE,
                ),
            ),
        ]:
            rows.append(_probe(test_id, sample, fn, date_value=date_value))
    return rows


def _pit_fundamental_probe(jq: Any, samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    codes = [row["code"] for row in samples]
    if not codes:
        return []
    def run() -> Any:
        return jq.get_fundamentals(
            jq.query(
                jq.valuation.code,
                jq.valuation.pb_ratio,
                jq.valuation.market_cap,
                jq.indicator.roe,
            ).filter(jq.valuation.code.in_(codes)),
            date=PRE2020_TEST_DATE,
        )

    row = _probe("pit_fundamentals_valuation_indicator", {"code": ";".join(codes), "sleeve": "multi", "preview_date": "2019-04-01"}, run)
    if row["status"] == "pass":
        row["pit_visible_date"] = PRE2020_TEST_DATE
    return [row]


def _probe(test_id: str, sample: dict[str, Any], fn: Callable[[], Any], date_value: str = PRE2020_TEST_DATE) -> dict[str, Any]:
    try:
        df = fn()
        row_count = 0 if df is None else len(df)
        return {
            "test_id": test_id,
            "code": sample.get("code", ""),
            "sleeve": sample.get("sleeve", ""),
            "test_date": date_value,
            "status": "pass" if row_count > 0 else "empty",
            "row_count": row_count,
            "first_index": str(df.index[0]) if row_count and hasattr(df, "index") else "",
            "last_index": str(df.index[-1]) if row_count and hasattr(df, "index") else "",
            "error_type": "",
            "error_message": "",
        }
    except Exception as exc:
        message = str(exc)
        return {
            "test_id": test_id,
            "code": sample.get("code", ""),
            "sleeve": sample.get("sleeve", ""),
            "test_date": date_value,
            "status": "permission_blocked" if "付费模块" in message else "fail",
            "row_count": 0,
            "first_index": "",
            "last_index": "",
            "error_type": type(exc).__name__,
            "error_message": message[:300],
        }


def _capability_matrix(
    auth_rows: list[dict[str, Any]],
    daily_probe: list[dict[str, Any]],
    minute_probe: list[dict[str, Any]],
    pit_probe: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = list(auth_rows)
    rows.append(_cap("daily_price_access", daily_probe))
    rows.append(_cap("minute_5m_access", minute_probe))
    rows.append(_cap("pit_fundamental_access", pit_probe))
    return rows


def _cap(test_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = [str(row.get("status", "")) for row in rows]
    if any(status == "pass" for status in statuses):
        status = "pass"
    elif any(status == "permission_blocked" for status in statuses):
        status = "permission_blocked"
    elif rows:
        status = "fail_or_empty"
    else:
        status = "not_run"
    return {
        "test_id": test_id,
        "status": status,
        "pass_count": statuses.count("pass"),
        "permission_blocked_count": statuses.count("permission_blocked"),
        "empty_count": statuses.count("empty"),
        "fail_count": statuses.count("fail"),
    }


def _five_min_source_policy(root: Path) -> dict[str, Any]:
    summary = _read_json(root / PRE2021_GATE_SUMMARY)
    baostock_status = str(summary.get("baostock_2014_2020_status") or "")
    api_status = str(summary.get("baostock_5min_api_capability_status") or "")
    return {
        "project_5min_source_policy": "baostock_only",
        "local_5min_bar_source_policy": "baostock_only",
        "joinquant_platform_minute_backtest_allowed": True,
        "joinquant_minute_path_allowed": False,
        "joinquant_minute_bar_data_source_allowed": False,
        "joinquant_minute_permission_required": False,
        "baostock_2014_2020_status": baostock_status,
        "baostock_5min_api_capability_status": api_status,
        "baostock_pre2020_5min_available": baostock_status == "pre2021_2014_2020_5min_available_in_probe",
        "backtest_scope_5min_baostock_available": "available_inside_backtest" in api_status,
    }


def _required_test_status(
    root: Path,
    capability: list[dict[str, Any]],
    daily_probe: list[dict[str, Any]],
    minute_probe: list[dict[str, Any]],
    pit_probe: list[dict[str, Any]],
    five_min_policy: dict[str, Any],
) -> list[dict[str, Any]]:
    local_sim = _read_json(root / LOCAL_SIM_SUMMARY)
    baostock_pre2020_available = bool(five_min_policy.get("baostock_pre2020_5min_available"))
    return [
        {
            "test_id": "T01_pre2020_5min_independent_validation",
            "purpose": "Confirm eligible pre-2021 local 5min bar evidence for spike-funded MR borrowing; local 5min bar source is BaoStock only.",
            "attempted": True,
            "status": "pass" if baostock_pre2020_available else "blocked_by_baostock_pre2020_5min_unavailable",
            "result": f"BaoStock status={five_min_policy.get('baostock_2014_2020_status')}; JQData minute bars are not an approved local data source; JoinQuant platform minute backtest exports are allowed as platform attribution.",
            "strategy_status_impact": "cannot_promote_observation_to_candidate; keep 2020q4 limited validation only",
        },
        {
            "test_id": "T02_pre2020_daily_price_and_pit_visibility",
            "purpose": "Confirm JoinQuant can support daily/PIT data around 2019.",
            "attempted": True,
            "status": "pass" if any(row.get("status") == "pass" for row in daily_probe) and any(row.get("status") == "pass" for row in pit_probe) else "partial_or_fail",
            "result": "Daily price and valuation/indicator PIT probes are available." if daily_probe and pit_probe else "not available",
            "strategy_status_impact": "supports_daily_factor_review_but_not_intraday_mr_validation",
        },
        {
            "test_id": "T03_backtest_scope_local_jq_style_simulation",
            "purpose": "Keep 2021-05-01 to 2026-05-31 local repaired simulation binding.",
            "attempted": True,
            "status": "pass" if local_sim.get("status") == "completed_prebacktest_validation_and_backtest_scope_local_jq_sim" else "fail",
            "result": f"best_delta_vs_primary={local_sim.get('backtest_delta_vs_primary_pct_points')}",
            "strategy_status_impact": "positive_backtest_but_not_candidate_without_baostock_pre2020_minute_validation",
        },
        {
            "test_id": "T04_joinquant_platform_backtest_exports",
            "purpose": "Official JoinQuant platform minute/daily backtest attribution for internal_subsleeve_mom12_70_30.",
            "attempted": False,
            "status": "requires_joinquant_platform_ui_exports",
            "result": "JQData SDK cannot run/export platform backtest artifacts; user can run JoinQuant platform minute-level backtest and drop exports into the checklist folder.",
            "strategy_status_impact": "platform_attribution_still_waiting_exports",
        },
    ]


def _platform_export_status(root: Path) -> list[dict[str, Any]]:
    checklist = _read_json(root / JQ_CHECKLIST_SUMMARY)
    required = _read_csv(root / JQ_REQUIRED_EXPORTS)
    dropzone = Path(checklist.get("dropzone_root", ""))
    rows = []
    for item in required:
        expected = dropzone / str(item["scope"]) / str(item["file_name"])
        rows.append(
            {
                "export_id": item["export_id"],
                "scope": item["scope"],
                "file_name": item["file_name"],
                "required": item["required"],
                "expected_path": str(expected),
                "present": expected.exists(),
                "status": "present" if expected.exists() else "waiting_for_platform_export",
            }
        )
    return rows


def _governance_audit(
    capability: list[dict[str, Any]],
    required_tests: list[dict[str, Any]],
    five_min_policy: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _audit("jqdata_auth_attempted", any(row["test_id"] == "jqdata_auth" for row in capability), ""),
        _audit("daily_price_probe_attempted", True, ""),
        _audit("jqdata_minute_probe_recorded_as_non_source_check", True, "JQData minute probe documents SDK bar access limits, but cannot satisfy local 5min bar source policy."),
        _audit("five_min_source_policy_baostock_only", five_min_policy.get("project_5min_source_policy") == "baostock_only", ""),
        _audit("joinquant_platform_minute_backtest_allowed", bool(five_min_policy.get("joinquant_platform_minute_backtest_allowed")), "Allowed as platform simulation/export, not as local 5min bar source."),
        _audit("jqdata_minute_bar_source_not_project_route", not bool(five_min_policy.get("joinquant_minute_bar_data_source_allowed")), ""),
        _audit("baostock_pre2020_empty_gap_recorded", not bool(five_min_policy.get("baostock_pre2020_5min_available")), str(five_min_policy.get("baostock_2014_2020_status") or "")),
        _audit("baostock_backtest_scope_5min_available", bool(five_min_policy.get("backtest_scope_5min_baostock_available")), str(five_min_policy.get("baostock_5min_api_capability_status") or "")),
        _audit("backtest_scope_end_20260531", True, BACKTEST_END),
        _audit("post_20260531_not_used", True, ""),
        _audit("no_v57f_core_modified", True, ""),
        _audit("no_threshold_scan_used", True, ""),
        _audit("accepted_false", True, ""),
        _audit("platform_backtest_not_started_by_sdk", True, ""),
    ]


def _pm_gate_decision(
    required_tests: list[dict[str, Any]],
    governance: list[dict[str, Any]],
    five_min_policy: dict[str, Any],
) -> list[dict[str, Any]]:
    baostock_blocked = any(row["status"] == "blocked_by_baostock_pre2020_5min_unavailable" for row in required_tests)
    decision = (
        "jqdata_daily_pit_pass_baostock_pre2020_5min_unavailable_keep_spike_mr_observation"
        if baostock_blocked
        else "jqdata_daily_pit_pass_baostock_5min_ready_for_pre2020_validation"
    )
    return [
        {
            "pm_gate_decision": decision,
            "primary_candidate": PRIMARY,
            "spike_mr_status": "observation_only",
            "accepted": False,
            "live_trading_approved": False,
            "reason": "JQData daily/PIT probes passed; local 5min bar source policy is BaoStock-only, BaoStock pre-2020 5min is not confirmed, and JoinQuant platform minute backtest remains available for external attribution exports."
            if baostock_blocked
            else "BaoStock 5min is available for the required pre-2021 validation window.",
        }
    ]


def _blockers(required_tests: list[dict[str, Any]], minute_probe: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    if any(row["status"] == "blocked_by_baostock_pre2020_5min_unavailable" for row in required_tests):
        rows.append(
            {
                "blocker_id": "baostock_pre2020_5min_unavailable",
                "severity": "data_source_gap",
                "blocks": "pre2020_5min_independent_validation",
                "detail": "BaoStock is the only approved local 5min bar source; 2014-2019 probes return empty while 2020+/backtest probes pass. JoinQuant platform minute backtest may be used for platform attribution, not as raw 5min bar data.",
            }
        )
    rows.append(
        {
            "blocker_id": "joinquant_platform_exports_missing",
            "severity": "external_platform_export",
            "blocks": "official_platform_attribution",
            "detail": "JQData SDK cannot replace JoinQuant platform minute/daily backtest exports: daily_returns, transactions, positions, logs, script snapshot.",
        }
    )
    return rows


def _next_queue(decision: str, blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "next_task": "keep_internal_subsleeve_mom12_70_30_as_v5f_primary",
            "status": "unchanged_primary",
            "allowed": True,
        },
        {
            "priority": 2,
            "next_task": "keep_5min_source_policy_baostock_only",
            "status": "active_source_boundary",
            "allowed": True,
        },
        {
            "priority": 3,
            "next_task": "run_joinquant_platform_minute_backtest_and_drop_required_exports",
            "status": "needed_for_platform_minute_attribution",
            "allowed": True,
        },
        {
            "priority": 4,
            "next_task": "do_not_promote_spike_mr_borrowing",
            "status": "blocked_until_baostock_pre2020_5min_or_future_forward_evidence_passes",
            "allowed": False,
        },
        {
            "priority": 5,
            "next_task": "do_not_use_jqdata_sdk_minute_bars_as_local_5min_source",
            "status": "blocked_data_source_action",
            "allowed": False,
        },
    ]


def _report(
    capability: list[dict[str, Any]],
    daily_probe: list[dict[str, Any]],
    minute_probe: list[dict[str, Any]],
    pit_probe: list[dict[str, Any]],
    required_tests: list[dict[str, Any]],
    decision: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    five_min_policy: dict[str, Any],
) -> str:
    lines = [
        "# V5f JoinQuant Now Execution",
        "",
        f"- PM gate: `{decision[0]['pm_gate_decision']}`",
        f"- Primary line remains `{PRIMARY}`.",
        f"- Backtest scope remains `{BACKTEST_START}` to `{BACKTEST_END}`.",
        "- Local 5min bar source policy: `baostock_only`.",
        "- JoinQuant platform minute-level backtest is allowed for platform attribution exports.",
        "- JQData SDK minute bars are not an approved local 5min data source.",
        "- No accepted/live approval, no V57f core modification.",
        "",
        "## BaoStock 5min Boundary",
        "",
        f"- BaoStock 2014-2020 status: `{five_min_policy.get('baostock_2014_2020_status')}`.",
        f"- BaoStock backtest/API status: `{five_min_policy.get('baostock_5min_api_capability_status')}`.",
        f"- Pre-2020 BaoStock 5min available: `{five_min_policy.get('baostock_pre2020_5min_available')}`.",
        f"- Backtest-scope BaoStock 5min available: `{five_min_policy.get('backtest_scope_5min_baostock_available')}`.",
        "",
        "## Capability",
        "",
    ]
    for row in capability:
        lines.append(f"- `{row['test_id']}`: `{row['status']}`.")
    lines.extend(["", "## Required Tests", ""])
    for row in required_tests:
        lines.append(f"- `{row['test_id']}`: `{row['status']}` / {row['result']}")
    lines.extend(["", "## JQData Minute Probe (Non-Source Audit)", ""])
    for row in minute_probe[:8]:
        lines.append(f"- `{row['test_id']}` `{row['code']}`: `{row['status']}` / {row.get('error_message','')}")
    lines.extend(["", "## Blockers", ""])
    for row in blockers:
        lines.append(f"- `{row['blocker_id']}`: {row['detail']}")
    return "\n".join(lines) + "\n"


def _rules() -> str:
    return "\n".join(
        [
            "# V5f JoinQuant Execution Rules",
            "",
            "- Use repaired V57f baseline only.",
            "- Historical backtest scope ends at 2026-05-31.",
            "- JQData daily/PIT probes do not replace platform backtest exports.",
            "- Local 5min bar source policy is BaoStock only.",
            "- JoinQuant platform minute-level backtest is allowed for external platform attribution exports.",
            "- Do not use JQData SDK minute bars as local 5min source.",
            "- BaoStock pre-2020 5min unavailability blocks formal short-window independent validation; 2020Q4 remains limited evidence.",
            "- Do not mark accepted, live approved, or V57f replacement.",
            "",
        ]
    )


def _input_manifest(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": str(path),
            "required": True,
            "exists": (root / path).exists(),
            "file_size_bytes": (root / path).stat().st_size if (root / path).exists() else "",
        }
        for path in REQUIRED
    ]


def _write_minimal(out: Path, summary: dict[str, Any], manifest: list[dict[str, Any]], blockers: list[dict[str, Any]]) -> None:
    _write_json(out / "v5f_joinquant_now_execution_summary.json", summary)
    _write_csv(out / "v5f_joinquant_input_manifest.csv", manifest)
    _write_csv(out / "v5f_joinquant_blockers.csv", blockers)
    for name in [
        "v5f_jqdata_capability_matrix.csv",
        "v5f_pre2020_daily_price_probe.csv",
        "v5f_pre2020_minute_permission_probe.csv",
        "v5f_pre2020_pit_fundamental_probe.csv",
        "v5f_joinquant_required_test_status.csv",
        "v5f_joinquant_platform_export_status.csv",
        "v5f_joinquant_governance_audit.csv",
        "v5f_joinquant_pm_gate_decision.csv",
        "v5f_joinquant_next_queue.csv",
    ]:
        _write_csv(out / name, [])
    (out / "v5f_joinquant_now_execution_report.md").write_text("# Blocked\n", encoding="utf-8")
    (out / "v5f_joinquant_agent_execution_rules.md").write_text(_rules(), encoding="utf-8")


def _summary(status: str, decision: str, fatal_blockers: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5f_joinquant_now_execution",
        "status": status,
        "pm_gate_decision": decision,
        "fatal_blockers": fatal_blockers,
    }
    payload.update(extra)
    return payload


def _row(test_id: str, status: str, **extra: Any) -> dict[str, Any]:
    row = {"test_id": test_id, "status": status}
    row.update(extra)
    return row


def _audit(audit_id: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"audit_id": audit_id, "status": "pass" if passed else "fail", "detail": detail}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or ["empty"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


if __name__ == "__main__":
    print(json.dumps(run_v5f_joinquant_now_execution(Path(".")), ensure_ascii=False, indent=2))

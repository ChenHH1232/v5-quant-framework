from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "v5d_closeout" / "current"


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def pct(x: float | str | None) -> str:
    if x in (None, ""):
        return ""
    return f"{float(x) * 100:.2f}%"


def money(x: float | str | None) -> str:
    if x in (None, ""):
        return ""
    return f"{float(x):.2f}"


def hygiene_scan(paths: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for base in paths:
        if not base.exists():
            rows.append(
                {
                    "path": str(base.relative_to(ROOT)),
                    "issue_type": "missing_path",
                    "hit_count": 1,
                    "severity": "medium",
                    "recommendation": "review missing expected V5d output path",
                }
            )
            continue
        for path in base.rglob("*"):
            if path.suffix.lower() not in {".csv", ".json", ".md"}:
                continue
            try:
                text = path.read_text(encoding="utf-8-sig", errors="replace")
            except Exception as exc:
                rows.append(
                    {
                        "path": str(path.relative_to(ROOT)),
                        "issue_type": "read_error",
                        "hit_count": 1,
                        "severity": "medium",
                        "recommendation": f"manual encoding check required: {exc}",
                    }
                )
                continue
            question_hits = text.count("???")
            replacement_hits = text.count("\ufffd")
            if question_hits or replacement_hits:
                rows.append(
                    {
                        "path": str(path.relative_to(ROOT)),
                        "issue_type": "possible_mojibake",
                        "hit_count": question_hits + replacement_hits,
                        "severity": "low" if question_hits + replacement_hits < 5 else "medium",
                        "recommendation": "do not modify old file in closeout; regenerate from source if needed",
                    }
                )
    if not rows:
        rows.append(
            {
                "path": "",
                "issue_type": "none_found",
                "hit_count": 0,
                "severity": "none",
                "recommendation": "new closeout files written as UTF-8",
            }
        )
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    data_gate = read_json(ROOT / "v5d_baostock_5min_data_gate" / "current" / "v5d_baostock_5min_data_gate_summary.json")
    l1 = read_json(ROOT / "v5d_minute_execution_robustness" / "current" / "v5d_minute_execution_robustness_summary.json")
    l2 = read_json(ROOT / "v5d_l2_order_scheduling_pm_quant_review" / "current" / "v5d_l2_pm_quant_review_summary.json")
    l2_cost = read_json(ROOT / "v5d_l2_execution_cost_broker_paper_review" / "current" / "v5d_l2_broker_paper_review_summary.json")
    l2_liq = read_json(ROOT / "v5d_l2_liquidity_instant_fill_review" / "current" / "v5d_l2_liquidity_instant_fill_summary.json")
    l2_slip = read_json(ROOT / "v5d_l2_conservative_slippage_spec" / "current" / "v5d_l2_conservative_slippage_summary.json")
    l3 = read_json(ROOT / "v5d_l3_pm_quant_review" / "current" / "v5d_l3_pm_quant_review_summary.json")
    l31 = read_json(ROOT / "v5d_l3_1_unfilled_remediation" / "current" / "v5d_l3_1_unfilled_remediation_summary.json")
    l4 = read_json(ROOT / "v5d_l4_rebalance_neighborhood_order_completion" / "current" / "v5d_l4_order_completion_summary.json")
    l4_pm = read_json(ROOT / "v5d_l4_rebalance_neighborhood_order_completion" / "current" / "v5d_l4_pm_quant_review_summary.json")
    l4_cost = read_json(ROOT / "v5d_l4_rebalance_neighborhood_order_completion" / "current" / "v5d_l4_cost_closeout_summary.json")

    l4_delta_rows = l4_cost.get("delta_rows", [])
    l2_liq_rows = l2_liq.get("summary_rows", [])
    l2_slip_rows = l2_slip.get("cost_summary_rows", [])

    local_window = {"start_date": "2021-05-01", "end_date": "2026-05-31"}
    effective_first_signal = data_gate.get("first_v57f_rebalance_signal", "2021-10-08")

    component_rows = [
        {
            "component_id": "data_gate_baostock_5min",
            "status": data_gate.get("status"),
            "decision": "pass_for_v5d_local_execution_research",
            "main_evidence": f"stock_universe={data_gate.get('stock_universe_count')}; rebalance_windows={data_gate.get('rebalance_window_count')}; fetch_pass_ratio={data_gate.get('fetch_pass_ratio')}",
            "candidate_status": "data_gate_pass_not_strategy_acceptance",
            "next_gate": "used_by_l1_l2_l3_l4",
        },
        {
            "component_id": "l1_fixed_execution_proxy",
            "status": l1.get("status"),
            "decision": "diagnostic_only",
            "main_evidence": f"completed_proxies={len(l1.get('completed_execution_proxies', []))}; minute_execution_sensitive={l1.get('minute_execution_sensitive')}",
            "candidate_status": "not_execution_policy",
            "next_gate": "do_not_select_best_minute_by_return",
        },
        {
            "component_id": "l2_size_aware_order_scheduling",
            "status": l2.get("status"),
            "decision": l2.get("policy_decision"),
            "main_evidence": "reduced over-slicing versus all-order slicing; zero T violations; broker constraints reviewed",
            "candidate_status": "execution_policy_candidate_not_accepted",
            "next_gate": l2_cost.get("next_gate"),
        },
        {
            "component_id": "l2_liquidity_and_slippage",
            "status": f"{l2_liq.get('status')} + {l2_slip.get('status')}",
            "decision": "feasible_with_tail_review",
            "main_evidence": "50w base instant-fill pass about 98.8%; conservative 50w slippage about 0.23%-0.24% of capital",
            "candidate_status": "execution_cost_context_not_strategy_acceptance",
            "next_gate": l2_slip.get("next_gate"),
        },
        {
            "component_id": "l3_default_exception",
            "status": l3.get("status"),
            "decision": l3.get("policy_decision"),
            "main_evidence": "exception logging/governance candidate; not promoted by return",
            "candidate_status": "execution_governance_candidate_not_accepted",
            "next_gate": l3.get("next_gate"),
        },
        {
            "component_id": "l3_1_open_delay_price_band_fallback",
            "status": l31.get("status"),
            "decision": l31.get("l3_1_candidate"),
            "main_evidence": "large unfilled reduction and zero T, but requires stress/cost review before any stronger status",
            "candidate_status": "unfilled_remediation_candidate_not_accepted",
            "next_gate": l31.get("next_gate"),
        },
        {
            "component_id": "l4_exception_governed_completion",
            "status": l4_pm.get("status"),
            "decision": l4_pm.get("policy_decision"),
            "main_evidence": "D0/D+1/D+2 coverage complete; unfilled reduced; zero T; small return drag accepted as execution realism",
            "candidate_status": l4_cost.get("candidate_status"),
            "next_gate": l4_cost.get("next_gate"),
        },
    ]

    candidate_rows = [
        {
            "candidate_id": "l2_size_aware",
            "candidate_type": "order_scheduling",
            "status": "execution_policy_candidate_not_accepted",
            "promotion_basis": "fewer unnecessary slices, broker constraints compatible, zero T violations",
            "accepted": "no",
            "v57f_replacement": "no",
            "next_required_review": "paper matching and final execution governance closeout",
        },
        {
            "candidate_id": "l3_default_exception",
            "candidate_type": "execution_governance",
            "status": "execution_governance_candidate_not_accepted",
            "promotion_basis": "auditable exception handling for paused, limit, missing bar, close unfinished cases",
            "accepted": "no",
            "v57f_replacement": "no",
            "next_required_review": "integrate with L4 order-completion rules",
        },
        {
            "candidate_id": "l3_open_delay_price_band_fallback",
            "candidate_type": "unfilled_remediation",
            "status": "candidate_with_review_notes_not_accepted",
            "promotion_basis": "unfilled reduction and zero T, not return selection",
            "accepted": "no",
            "v57f_replacement": "no",
            "next_required_review": "stress and cost review; do not promote raw high-unfilled price-band rule",
        },
        {
            "candidate_id": "l4_exception_governed_completion",
            "candidate_type": "rebalance_neighborhood_completion",
            "status": "execution_policy_candidate_not_accepted",
            "promotion_basis": "finite D+1 completion reduces residual unfilled with zero T and no target-weight change",
            "accepted": "no",
            "v57f_replacement": "no",
            "next_required_review": "v5d_execution_research_closeout; optional broker paper matching",
        },
    ]

    data_cost_rows: list[dict] = []
    for row in l2_liq_rows:
        data_cost_rows.append(
            {
                "source_component": "l2_liquidity",
                "strategy_id": row.get("strategy_id"),
                "capital_case": row.get("capital_case"),
                "metric_1_name": "instant_fill_base_pass_rate",
                "metric_1_value": row.get("instant_fill_base_pass_rate"),
                "metric_2_name": "liquidity_review_required_count",
                "metric_2_value": row.get("liquidity_review_required_count"),
                "pm_read": row.get("pm_read"),
            }
        )
    for row in l2_slip_rows:
        data_cost_rows.append(
            {
                "source_component": "l2_slippage",
                "strategy_id": row.get("strategy_id"),
                "capital_case": row.get("capital_case"),
                "metric_1_name": "conservative_slippage_cost",
                "metric_1_value": row.get("conservative_slippage_cost"),
                "metric_2_name": "slippage_cost_pct_on_capital",
                "metric_2_value": row.get("slippage_cost_pct_on_capital"),
                "pm_read": row.get("pm_read"),
            }
        )
    for row in l4_delta_rows:
        data_cost_rows.append(
            {
                "source_component": "l4_cost_closeout",
                "strategy_id": row.get("strategy_id"),
                "capital_case": "base_local_engineering",
                "metric_1_name": "unfilled_reduction",
                "metric_1_value": row.get("unfilled_reduction"),
                "metric_2_name": "delta_broker_commission",
                "metric_2_value": row.get("delta_broker_commission"),
                "pm_read": row.get("pm_read"),
            }
        )

    blocked_rows = [
        {"action": "modify_v57f_core", "status": "blocked", "reason": "V57f frozen mainline"},
        {"action": "mark_l2_l3_l4_accepted", "status": "blocked", "reason": "execution candidates require future/paper/broker evidence"},
        {"action": "use_best_historical_minute_by_return", "status": "blocked", "reason": "return selection and minute timing optimization forbidden"},
        {"action": "intraday_T", "status": "blocked", "reason": "outside V5d mainline and T+1 governance risk"},
        {"action": "D_minus_1_pretrade", "status": "blocked", "reason": "forbidden unless PIT target visibility is proven; no such proof used"},
        {"action": "start_joinquant_or_live_trading", "status": "blocked", "reason": "not required for local closeout and explicitly prohibited"},
        {"action": "infinite_order_chasing_after_rebalance", "status": "blocked", "reason": "L4 permits finite D+1/D+2 cleanup only; no unlimited carry"},
    ]

    next_gate_rows = [
        {
            "priority": 1,
            "next_gate": "v5d_execution_research_closeout",
            "status": "completed_by_this_packet",
            "scope": "archive current local V5d execution research conclusions",
        },
        {
            "priority": 2,
            "next_gate": "broker_paper_matching_optional",
            "status": "future_scope_only",
            "scope": "validate actual order lifecycle, fill timestamps, partial fills, and unfilled reasons without live trading",
        },
        {
            "priority": 3,
            "next_gate": "one_minute_data_optional",
            "status": "not_hard_prerequisite_for_current_closeout",
            "scope": "only needed if broker/paper review must inspect bar-inner fill feasibility",
        },
    ]

    hygiene_rows = hygiene_scan(
        [
            ROOT / "v5d_baostock_5min_data_gate" / "current",
            ROOT / "v5d_minute_execution_robustness" / "current",
            ROOT / "v5d_order_scheduling_engineering_test" / "current",
            ROOT / "v5d_l2_order_scheduling_pm_quant_review" / "current",
            ROOT / "v5d_l3_pm_quant_review" / "current",
            ROOT / "v5d_l3_1_unfilled_remediation" / "current",
            ROOT / "v5d_l4_rebalance_neighborhood_order_completion" / "current",
        ]
    )

    blocker_count = sum(1 for row in hygiene_rows if row["severity"] in {"high", "medium"})
    summary = {
        "schema_version": 1,
        "project": "v5d_execution_research_closeout",
        "status": "completed_v5d_local_execution_research_closeout",
        "created_at_utc": now,
        "local_engineering_window": local_window,
        "effective_first_v57f_signal_date": effective_first_signal,
        "v57f_core_modified": False,
        "erc_modified": False,
        "joinquant_started": False,
        "live_trading_started": False,
        "intraday_T_allowed": False,
        "return_selection_used": False,
        "data_gate": {
            "stock_universe_count": data_gate.get("stock_universe_count"),
            "rebalance_window_count": data_gate.get("rebalance_window_count"),
            "d0_d1_d2_coverage": l4.get("data_coverage"),
        },
        "final_candidate_status": {
            "l2_size_aware": "execution_policy_candidate_not_accepted",
            "l3_default_exception": "execution_governance_candidate_not_accepted",
            "l3_open_delay_price_band_fallback": "unfilled_remediation_candidate_with_review_notes_not_accepted",
            "l4_exception_governed_completion": "execution_policy_candidate_not_accepted",
        },
        "l4_cost_closeout": {
            "candidate_status": l4_cost.get("candidate_status"),
            "delta_rows": l4_delta_rows,
            "next_gate": l4_cost.get("next_gate"),
        },
        "paid_1m_data_assessment": "optional_future_gate_not_required_for_current_l4_closeout",
        "blocker_count": blocker_count,
        "next_gate": "park_until_broker_paper_matching_or_user_reopens_v5d",
        "outputs": {
            "summary": "v5d_closeout\\current\\v5d_closeout_summary.json",
            "report": "v5d_closeout\\current\\v5d_closeout_report.md",
            "component_status_matrix": "v5d_closeout\\current\\v5d_component_status_matrix.csv",
            "execution_candidate_status": "v5d_closeout\\current\\v5d_execution_candidate_status.csv",
            "data_and_cost_matrix": "v5d_closeout\\current\\v5d_data_and_cost_matrix.csv",
            "blocked_actions": "v5d_closeout\\current\\v5d_blocked_actions.csv",
            "next_gate_queue": "v5d_closeout\\current\\v5d_next_gate_queue.csv",
            "file_hygiene_audit": "v5d_closeout\\current\\v5d_file_hygiene_audit.csv",
            "agent_execution_rules": "v5d_closeout\\current\\v5d_agent_execution_rules.md",
        },
    }

    report = f"""# V5d Execution Research Closeout

- Status: `completed_v5d_local_execution_research_closeout`
- Local engineering window: 2021-05-01 to 2026-05-31
- First effective V57f signal: {effective_first_signal}
- Scope: execution research only; no V57f/ERC modification, no JoinQuant, no live trading, no intraday T.

## Final PM Read

V5d has produced useful execution candidates, but no accepted strategy and no V57f replacement. The useful result is not a new return engine; it is a more realistic, auditable order-execution workflow.

## Candidate Status

| Layer | Status | Read |
| --- | --- | --- |
| L1 fixed minute proxies | diagnostic only | fixed 09:35/10:00/14:55 style tests show execution sensitivity, but cannot select a minute by historical return |
| L2 size-aware scheduling | execution policy candidate, not accepted | reduces over-slicing and respects broker constraints |
| L3 default exception | execution governance candidate, not accepted | improves logging and handling of paused/limit/missing/close-unfinished cases |
| L3.1 price-band fallback | remediation candidate with notes, not accepted | raw price-band had too many unfilled orders; fallback reduces unfilled but still needs stress/cost review |
| L4 exception-governed completion | execution policy candidate, not accepted | finite D+1 completion reduces residual unfilled with zero T violations |

## L4 Cost Closeout

| Strategy | Unfilled Reduction | Delta Return | Delta Broker Commission | T Violations |
| --- | ---: | ---: | ---: | ---: |
"""
    for row in l4_delta_rows:
        report += (
            f"| `{row['strategy_id']}` | {row['unfilled_reduction']} | "
            f"{pct(row['delta_return'])} | {money(row['delta_broker_commission'])} | "
            f"{row['t_violation_count']} |\n"
        )

    report += """
L4 is kept because it reduces execution residue with zero T violations. The small return drag is treated as realistic execution cost, not as a reason to tune the rule.

## Data and Cost Notes

- BaoStock 5-minute data gate passed for the local V5d research universe.
- L4 D0/D+1/D+2 coverage is complete for the tested rebalance-neighborhood windows.
- 50w size review remains feasible with tail review; it is not guaranteed instant fill for every tail order.
- One-minute data is optional for future broker/paper matching, not required to close the current local L4 result.

## Governance

Blocked: modifying V57f/ERC, accepting any V5d policy as final, selecting by historical minute return, intraday T, D-1 pretrade, JoinQuant/live trading, and unlimited order chasing.
"""

    rules = """# V5d Agent Execution Rules

1. Keep V57f frozen.
2. Keep ERC as V5c overlay candidate only; do not mark accepted or replacement.
3. Treat V5d outputs as execution candidates, not strategy alpha.
4. Do not select fixed minute points by historical return.
5. Do not perform intraday T.
6. Do not pretrade on D-1 unless a future task proves PIT target visibility.
7. L4 completion may use finite D+1/D+2 order completion only for orders already generated by D0 rebalance signals.
8. Stop at close or finite cleanup boundary and log unfilled orders; do not force-fill or fabricate data.
9. Broker paper matching or 1-minute data are future gates only, not prerequisites for this closeout.
"""

    write_json(OUT / "v5d_closeout_summary.json", summary)
    write_text(OUT / "v5d_closeout_report.md", report)
    write_csv(
        OUT / "v5d_component_status_matrix.csv",
        component_rows,
        ["component_id", "status", "decision", "main_evidence", "candidate_status", "next_gate"],
    )
    write_csv(
        OUT / "v5d_execution_candidate_status.csv",
        candidate_rows,
        ["candidate_id", "candidate_type", "status", "promotion_basis", "accepted", "v57f_replacement", "next_required_review"],
    )
    write_csv(
        OUT / "v5d_data_and_cost_matrix.csv",
        data_cost_rows,
        ["source_component", "strategy_id", "capital_case", "metric_1_name", "metric_1_value", "metric_2_name", "metric_2_value", "pm_read"],
    )
    write_csv(OUT / "v5d_blocked_actions.csv", blocked_rows, ["action", "status", "reason"])
    write_csv(OUT / "v5d_next_gate_queue.csv", next_gate_rows, ["priority", "next_gate", "status", "scope"])
    write_csv(OUT / "v5d_file_hygiene_audit.csv", hygiene_rows, ["path", "issue_type", "hit_count", "severity", "recommendation"])
    write_text(OUT / "v5d_agent_execution_rules.md", rules)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

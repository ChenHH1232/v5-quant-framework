from __future__ import annotations

import argparse
from pathlib import Path

from v5.agent_loop_packet_runner import DEFAULT_OUT_DIR as DEFAULT_AGENT_LOOP_PACKET_OUT, create_agent_loop_packet
from v5.overfit_audit_runner import run_overfit_audit
from v5.basket_pm_gate_runner import DEFAULT_OUT_DIR as DEFAULT_BASKET_PM_GATE_OUT, run_basket_pm_gate
from v5.basket_forward_paper_gate_runner import (
    DEFAULT_OUT_DIR as DEFAULT_FORWARD_PAPER_GATE_OUT,
    prepare_basket_forward_paper_gate,
)
from v5.basket_governance_dashboard_runner import (
    DEFAULT_OUT_DIR as DEFAULT_BASKET_GOVERNANCE_DASHBOARD_OUT,
    build_basket_governance_dashboard,
)
from v5.basket_pm_action_router_runner import (
    DEFAULT_OUT_DIR as DEFAULT_BASKET_PM_ACTION_ROUTE_OUT,
    route_basket_pm_action,
)
from v5.basket_paper_input_preflight_runner import (
    DEFAULT_OUT_DIR as DEFAULT_BASKET_PAPER_INPUT_PREFLIGHT_OUT,
    run_basket_paper_input_preflight,
)
from v5.basket_paper_refresh_queue_runner import (
    DEFAULT_OUT_DIR as DEFAULT_BASKET_PAPER_REFRESH_QUEUE_OUT,
    build_basket_paper_refresh_queue,
)
from v5.basket_paper_refresh_status_runner import (
    DEFAULT_OUT_DIR as DEFAULT_BASKET_PAPER_REFRESH_STATUS_OUT,
    check_basket_paper_refresh_status,
)
from v5.platform_attribution_runner import run_platform_attribution, run_position_attribution, run_transaction_attribution
from v5.platform_export_intake_runner import (
    DEFAULT_OUT_DIR as DEFAULT_PLATFORM_EXPORT_INTAKE_OUT,
    check_platform_export_intake,
)
from v5.platform_replication_runner import run_platform_replication_packet
from v5.strategy_state_gate_runner import DEFAULT_OUT_DIR as DEFAULT_STRATEGY_STATE_GATE_OUT, run_strategy_state_gate
from v5.universe_runner import build_point_in_time_universe


def register_platform_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    universe_parser = subparsers.add_parser("build-universe")
    universe_parser.add_argument("panel", type=Path)
    universe_parser.add_argument("execution_price_csv", type=Path)
    universe_parser.add_argument("--out", type=Path, default=Path("universes"))
    universe_parser.add_argument("--strategy-id", default="bank_value_15y")
    universe_parser.set_defaults(handler=_handle_build_universe)

    overfit_parser = subparsers.add_parser("overfit-audit")
    overfit_parser.add_argument("spec", type=Path)
    overfit_parser.add_argument("--panel", type=Path)
    overfit_parser.add_argument("--daily-returns-csv", type=Path)
    overfit_parser.add_argument("--rebalance-signals-csv", type=Path)
    overfit_parser.add_argument("--out", type=Path, default=Path("validation_overfit"))
    overfit_parser.add_argument("--strategy-id")
    overfit_parser.add_argument("--random-seed", type=int, default=20260716)
    overfit_parser.add_argument("--random-windows", type=int, default=100)
    overfit_parser.add_argument("--min-window-days", type=int, default=252)
    overfit_parser.set_defaults(handler=_handle_overfit_audit)

    attribution_parser = subparsers.add_parser("platform-attribution")
    attribution_parser.add_argument("local_daily_csv", type=Path)
    attribution_parser.add_argument("joinquant_daily_csv", type=Path)
    attribution_parser.add_argument("--out", type=Path, default=Path("platform_attribution"))
    attribution_parser.add_argument("--strategy-id", default="bank_value_15y")
    attribution_parser.add_argument("--local-rebalance-signals-csv", type=Path)
    attribution_parser.add_argument("--local-trades-csv", type=Path)
    attribution_parser.add_argument("--local-dividends-csv", type=Path)
    attribution_parser.set_defaults(handler=_handle_platform_attribution)

    position_parser = subparsers.add_parser("platform-position-attribution")
    position_parser.add_argument("joinquant_position_csv", type=Path)
    position_parser.add_argument("local_holdings_csv", type=Path)
    position_parser.add_argument("--out", type=Path, default=Path("platform_attribution"))
    position_parser.add_argument("--strategy-id", default="bank_value_15y")
    position_parser.set_defaults(handler=_handle_position_attribution)

    transaction_parser = subparsers.add_parser("platform-transaction-attribution")
    transaction_parser.add_argument("joinquant_transaction_csv", type=Path)
    transaction_parser.add_argument("local_trades_csv", type=Path)
    transaction_parser.add_argument("--out", type=Path, default=Path("platform_attribution"))
    transaction_parser.add_argument("--strategy-id", default="bank_value_15y")
    transaction_parser.set_defaults(handler=_handle_transaction_attribution)

    packet_parser = subparsers.add_parser("platform-replication-packet")
    packet_parser.add_argument("local_run_dir", type=Path)
    packet_parser.add_argument("--out", type=Path, default=Path("platform_replication_packets"))
    packet_parser.add_argument("--strategy-id", default="bank_value_15y")
    packet_parser.add_argument("--panel-csv", type=Path)
    packet_parser.add_argument("--joinquant-daily-csv", type=Path)
    packet_parser.add_argument("--joinquant-transaction-csv", type=Path)
    packet_parser.add_argument("--joinquant-position-csv", type=Path)
    packet_parser.add_argument("--expected-rebalance-date", action="append", default=[])
    packet_parser.add_argument("--final-strategy-diff-threshold", type=float, default=0.01)
    packet_parser.add_argument("--max-strategy-diff-threshold", type=float, default=0.03)
    packet_parser.set_defaults(handler=_handle_platform_replication_packet)

    export_intake_parser = subparsers.add_parser("check-platform-export-intake")
    export_intake_parser.add_argument("manifest", type=Path)
    export_intake_parser.add_argument("--out", type=Path, default=DEFAULT_PLATFORM_EXPORT_INTAKE_OUT)
    export_intake_parser.add_argument("--user-deferred", action="store_true")
    export_intake_parser.set_defaults(handler=_handle_platform_export_intake)

    basket_pm_gate_parser = subparsers.add_parser("basket-pm-gate")
    basket_pm_gate_parser.add_argument("--strategy-id", required=True)
    basket_pm_gate_parser.add_argument("--formal-summary", type=Path, required=True)
    basket_pm_gate_parser.add_argument("--daily-summary", type=Path, required=True)
    basket_pm_gate_parser.add_argument("--overfit-summary", type=Path, required=True)
    basket_pm_gate_parser.add_argument("--ablation-summary", type=Path)
    basket_pm_gate_parser.add_argument("--platform-packet", type=Path)
    basket_pm_gate_parser.add_argument("--paper-signal-summary", type=Path)
    basket_pm_gate_parser.add_argument("--out", type=Path, default=DEFAULT_BASKET_PM_GATE_OUT)
    basket_pm_gate_parser.set_defaults(handler=_handle_basket_pm_gate)

    forward_paper_parser = subparsers.add_parser("prepare-basket-forward-paper-gate")
    forward_paper_parser.add_argument("--strategy-id", required=True)
    forward_paper_parser.add_argument("--config", type=Path, required=True)
    forward_paper_parser.add_argument("--current-paper-summary", type=Path, required=True)
    forward_paper_parser.add_argument("--pm-gate-summary", type=Path, required=True)
    forward_paper_parser.add_argument("--out", type=Path, default=DEFAULT_FORWARD_PAPER_GATE_OUT)
    forward_paper_parser.add_argument("--as-of-date")
    forward_paper_parser.add_argument("--next-rebalance-date")
    forward_paper_parser.add_argument("--trading-calendar-csv", type=Path)
    forward_paper_parser.set_defaults(handler=_handle_prepare_basket_forward_paper_gate)

    paper_input_preflight_parser = subparsers.add_parser("basket-paper-input-preflight")
    paper_input_preflight_parser.add_argument("--strategy-id", required=True)
    paper_input_preflight_parser.add_argument("--config", type=Path, required=True)
    paper_input_preflight_parser.add_argument("--target-rebalance-date", required=True)
    paper_input_preflight_parser.add_argument("--as-of-date", required=True)
    paper_input_preflight_parser.add_argument("--prior-trading-date")
    paper_input_preflight_parser.add_argument("--out", type=Path, default=DEFAULT_BASKET_PAPER_INPUT_PREFLIGHT_OUT)
    paper_input_preflight_parser.set_defaults(handler=_handle_basket_paper_input_preflight)

    paper_refresh_queue_parser = subparsers.add_parser("basket-paper-refresh-queue")
    paper_refresh_queue_parser.add_argument("preflight_summary", type=Path)
    paper_refresh_queue_parser.add_argument("--out", type=Path, default=DEFAULT_BASKET_PAPER_REFRESH_QUEUE_OUT)
    paper_refresh_queue_parser.set_defaults(handler=_handle_basket_paper_refresh_queue)

    paper_refresh_status_parser = subparsers.add_parser("basket-paper-refresh-status")
    paper_refresh_status_parser.add_argument("queue_csv", type=Path)
    paper_refresh_status_parser.add_argument("--preflight-summary", type=Path, required=True)
    paper_refresh_status_parser.add_argument("--as-of-date", required=True)
    paper_refresh_status_parser.add_argument("--out", type=Path, default=DEFAULT_BASKET_PAPER_REFRESH_STATUS_OUT)
    paper_refresh_status_parser.set_defaults(handler=_handle_basket_paper_refresh_status)

    governance_dashboard_parser = subparsers.add_parser("basket-governance-dashboard")
    governance_dashboard_parser.add_argument("--strategy-id", required=True)
    governance_dashboard_parser.add_argument("--pm-gate-summary", type=Path)
    governance_dashboard_parser.add_argument("--platform-export-intake-summary", type=Path)
    governance_dashboard_parser.add_argument("--forward-paper-gate-summary", type=Path)
    governance_dashboard_parser.add_argument("--paper-input-preflight-summary", type=Path)
    governance_dashboard_parser.add_argument("--paper-refresh-queue-summary", type=Path)
    governance_dashboard_parser.add_argument("--paper-refresh-status-summary", type=Path)
    governance_dashboard_parser.add_argument("--out", type=Path, default=DEFAULT_BASKET_GOVERNANCE_DASHBOARD_OUT)
    governance_dashboard_parser.set_defaults(handler=_handle_basket_governance_dashboard)

    pm_action_route_parser = subparsers.add_parser("basket-pm-action-route")
    pm_action_route_parser.add_argument("governance_dashboard_summary", type=Path)
    pm_action_route_parser.add_argument("--out", type=Path, default=DEFAULT_BASKET_PM_ACTION_ROUTE_OUT)
    pm_action_route_parser.add_argument("--as-of-date")
    pm_action_route_parser.set_defaults(handler=_handle_basket_pm_action_route)

    state_gate_parser = subparsers.add_parser("strategy-state-gate")
    state_gate_parser.add_argument("--strategy-id", required=True)
    state_gate_parser.add_argument("--target-status", required=True)
    state_gate_parser.add_argument("--registry", type=Path, default=Path("docs/governance/status_registry.json"))
    state_gate_parser.add_argument("--out", type=Path, default=DEFAULT_STRATEGY_STATE_GATE_OUT)
    state_gate_parser.add_argument("--proposed-evidence", action="append", default=[])
    state_gate_parser.set_defaults(handler=_handle_strategy_state_gate)

    packet_loop_parser = subparsers.add_parser("agent-loop-packet")
    packet_loop_parser.add_argument("--packet-type", required=True, choices=["checkpoint_packet", "blocker_packet", "failure_return_packet"])
    packet_loop_parser.add_argument("--objective", required=True)
    packet_loop_parser.add_argument("--agent", required=True)
    packet_loop_parser.add_argument("--experiment-layer", required=True)
    packet_loop_parser.add_argument("--decision", required=True)
    packet_loop_parser.add_argument("--next-owner", required=True)
    packet_loop_parser.add_argument("--out", type=Path, default=DEFAULT_AGENT_LOOP_PACKET_OUT)
    packet_loop_parser.add_argument("--timebox-minutes", type=int)
    packet_loop_parser.add_argument("--artifact", action="append", default=[])
    packet_loop_parser.add_argument("--evidence", action="append", default=[])
    packet_loop_parser.add_argument("--blocker", action="append", default=[])
    packet_loop_parser.add_argument("--stop-rule-status", default="not_triggered")
    packet_loop_parser.add_argument("--user-decision-required", action="store_true")
    packet_loop_parser.add_argument("--user-decision-reason", default="")
    packet_loop_parser.add_argument("--allowed-next-action", default="")
    packet_loop_parser.add_argument("--restart-condition", default="")
    packet_loop_parser.add_argument("--skill-status-change", default="none")
    packet_loop_parser.add_argument("--loop-id")
    packet_loop_parser.set_defaults(handler=_handle_agent_loop_packet)


def _handle_build_universe(args: argparse.Namespace) -> int:
    print(build_point_in_time_universe(args.panel, args.execution_price_csv, args.out, args.strategy_id))
    return 0


def _handle_overfit_audit(args: argparse.Namespace) -> int:
    result = run_overfit_audit(
        args.spec,
        args.out,
        panel_path=args.panel,
        daily_returns_csv=args.daily_returns_csv,
        rebalance_signals_csv=args.rebalance_signals_csv,
        strategy_id=args.strategy_id,
        random_seed=args.random_seed,
        random_windows=args.random_windows,
        min_window_days=args.min_window_days,
    )
    print(result.report_path)
    return 0 if result.blocker_count == 0 else 2


def _handle_platform_attribution(args: argparse.Namespace) -> int:
    print(run_platform_attribution(args.local_daily_csv, args.joinquant_daily_csv, args.out, args.strategy_id, local_rebalance_signals_csv=args.local_rebalance_signals_csv, local_trades_csv=args.local_trades_csv, local_dividends_csv=args.local_dividends_csv))
    return 0


def _handle_position_attribution(args: argparse.Namespace) -> int:
    print(run_position_attribution(args.joinquant_position_csv, args.local_holdings_csv, args.out, args.strategy_id))
    return 0


def _handle_transaction_attribution(args: argparse.Namespace) -> int:
    print(run_transaction_attribution(args.joinquant_transaction_csv, args.local_trades_csv, args.out, args.strategy_id))
    return 0


def _handle_platform_replication_packet(args: argparse.Namespace) -> int:
    print(
        run_platform_replication_packet(
            args.local_run_dir,
            args.joinquant_daily_csv,
            args.out,
            args.strategy_id,
            panel_csv=args.panel_csv,
            joinquant_transaction_csv=args.joinquant_transaction_csv,
            joinquant_position_csv=args.joinquant_position_csv,
            expected_rebalance_dates=args.expected_rebalance_date,
            final_strategy_diff_threshold=args.final_strategy_diff_threshold,
            max_strategy_diff_threshold=args.max_strategy_diff_threshold,
        )
    )
    return 0


def _handle_platform_export_intake(args: argparse.Namespace) -> int:
    result = check_platform_export_intake(args.manifest, args.out, user_deferred=args.user_deferred)
    print(result.report_path)
    return 0 if result.status in {"ready_for_platform_attribution", "platform_test_deferred_by_user_waiting_for_exports", "waiting_for_joinquant_exports"} else 2


def _handle_basket_pm_gate(args: argparse.Namespace) -> int:
    result = run_basket_pm_gate(
        strategy_id=args.strategy_id,
        formal_summary=args.formal_summary,
        daily_summary=args.daily_summary,
        overfit_summary=args.overfit_summary,
        out_dir=args.out,
        ablation_summary=args.ablation_summary,
        platform_packet=args.platform_packet,
        paper_signal_summary=args.paper_signal_summary,
    )
    print(result.report_path)
    return 0 if result.blocker_count == 0 else 2


def _handle_prepare_basket_forward_paper_gate(args: argparse.Namespace) -> int:
    result = prepare_basket_forward_paper_gate(
        strategy_id=args.strategy_id,
        config_path=args.config,
        current_paper_summary=args.current_paper_summary,
        pm_gate_summary=args.pm_gate_summary,
        out_dir=args.out,
        as_of_date=args.as_of_date,
        next_rebalance_date=args.next_rebalance_date,
        trading_calendar_csv=args.trading_calendar_csv,
    )
    print(result.report_path)
    return 0 if result.status != "blocked_rebalance_date_not_future" else 2


def _handle_basket_paper_input_preflight(args: argparse.Namespace) -> int:
    result = run_basket_paper_input_preflight(
        config_path=args.config,
        strategy_id=args.strategy_id,
        target_rebalance_date=args.target_rebalance_date,
        as_of_date=args.as_of_date,
        out_dir=args.out,
        prior_trading_date=args.prior_trading_date,
    )
    print(result.report_path)
    return 0 if result.status != "blocked_missing_or_stale_inputs" else 2


def _handle_basket_paper_refresh_queue(args: argparse.Namespace) -> int:
    result = build_basket_paper_refresh_queue(args.preflight_summary, args.out)
    print(result.report_path)
    return 0


def _handle_basket_paper_refresh_status(args: argparse.Namespace) -> int:
    result = check_basket_paper_refresh_status(
        queue_csv=args.queue_csv,
        preflight_summary=args.preflight_summary,
        as_of_date=args.as_of_date,
        out_dir=args.out,
    )
    print(result.report_path)
    return 0 if result.status != "blocked" else 2


def _handle_basket_governance_dashboard(args: argparse.Namespace) -> int:
    result = build_basket_governance_dashboard(
        strategy_id=args.strategy_id,
        out_dir=args.out,
        pm_gate_summary=args.pm_gate_summary,
        platform_export_intake_summary=args.platform_export_intake_summary,
        forward_paper_gate_summary=args.forward_paper_gate_summary,
        paper_input_preflight_summary=args.paper_input_preflight_summary,
        paper_refresh_queue_summary=args.paper_refresh_queue_summary,
        paper_refresh_status_summary=args.paper_refresh_status_summary,
    )
    print(result.report_path)
    return 0 if result.status != "blocked" else 2


def _handle_basket_pm_action_route(args: argparse.Namespace) -> int:
    result = route_basket_pm_action(
        governance_dashboard_summary=args.governance_dashboard_summary,
        out_dir=args.out,
        as_of_date=args.as_of_date,
    )
    print(result.report_path)
    return 0


def _handle_strategy_state_gate(args: argparse.Namespace) -> int:
    result = run_strategy_state_gate(
        strategy_id=args.strategy_id,
        target_status=args.target_status,
        registry_path=args.registry,
        out_dir=args.out,
        proposed_evidence=args.proposed_evidence,
    )
    print(result.report_path)
    return 0 if result.status != "blocked" else 2


def _handle_agent_loop_packet(args: argparse.Namespace) -> int:
    result = create_agent_loop_packet(
        packet_type=args.packet_type,
        objective=args.objective,
        agent=args.agent,
        experiment_layer=args.experiment_layer,
        decision=args.decision,
        next_owner=args.next_owner,
        out_dir=args.out,
        timebox_minutes=args.timebox_minutes,
        artifacts=args.artifact,
        evidence=args.evidence,
        blockers=args.blocker,
        stop_rule_status=args.stop_rule_status,
        user_decision_required=args.user_decision_required,
        user_decision_reason=args.user_decision_reason,
        allowed_next_action=args.allowed_next_action,
        restart_condition=args.restart_condition,
        skill_status_change=args.skill_status_change,
        loop_id=args.loop_id,
    )
    print(result.report_path)
    return 0

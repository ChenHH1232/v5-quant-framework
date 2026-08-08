from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUT_DIR = Path("v5e_short_financing_etf_cash_proxy_selection_gate") / "current"
CASH_PROXY_DIR = Path("v5e_cash_proxy_asset_data_gate") / "current"
BUCKET_DIR = Path("v5e_sleeve_cash_bucket_engineering") / "current"
MODEL_DIR = Path("v5e_profit_lock_model_comparison") / "current"
CAPITAL_DIR = Path("v5e_capital_sensitivity_test") / "current"
STARTUP_DIR = Path("v5_startup_warmup_price_repair") / "current"
SHADOW_CONFIG = Path("config") / "dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f_startup_repaired_shadow.json"

ASSET_CODE = "511360.SH"
ASSET_NAME = "HFT Short Financing ETF"
FUND_FULL_NAME = "HFT CSI Short Financing ETF"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_v5e_short_financing_etf_cash_proxy_selection_gate(root: Path = Path(".")) -> dict[str, Any]:
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    blockers = _missing_inputs(root)
    if blockers:
        _write_csv(out / "v5e_short_financing_etf_blockers.csv", blockers)
        summary = _summary("blocked_missing_required_input", "blocked_until_inputs_available", blockers)
        _write_json(out / "v5e_short_financing_etf_selection_summary.json", summary)
        return summary

    bucket_summary = _read_json(root / BUCKET_DIR / "v5e_sleeve_cash_bucket_summary.json")
    model_summary = _read_json(root / MODEL_DIR / "v5e_model_comparison_summary.json")
    capital_summary = _read_json(root / CAPITAL_DIR / "v5e_capital_sensitivity_summary.json")

    profile = _candidate_profile()
    sources = _source_snapshot()
    pit_req = _pit_data_requirement()
    tradability = _tradability_liquidity_checklist()
    risk = _risk_register()
    accounting = _income_nav_accounting()
    boundaries = _v57f_boundary()
    v5d = _v5d_boundary()
    blocked = _blocked_actions()
    decision = _pm_gate_decision()
    next_queue = _next_queue(decision[0]["pm_gate_decision"])
    final_blockers = _nonfatal_blockers()

    _write_csv(out / "v5e_short_financing_etf_candidate_profile.csv", profile)
    _write_csv(out / "v5e_short_financing_etf_source_snapshot.csv", sources)
    _write_csv(out / "v5e_short_financing_etf_pit_data_requirement.csv", pit_req)
    _write_csv(out / "v5e_short_financing_etf_tradability_liquidity_checklist.csv", tradability)
    _write_csv(out / "v5e_short_financing_etf_risk_register.csv", risk)
    _write_csv(out / "v5e_short_financing_etf_income_nav_accounting.csv", accounting)
    _write_csv(out / "v5e_short_financing_etf_v57f_boundary.csv", boundaries)
    _write_csv(out / "v5e_short_financing_etf_v5d_execution_boundary.csv", v5d)
    _write_csv(out / "v5e_short_financing_etf_blocked_actions.csv", blocked)
    _write_csv(out / "v5e_short_financing_etf_pm_gate_decision.csv", decision)
    _write_csv(out / "v5e_short_financing_etf_next_agent_queue.csv", next_queue)
    _write_csv(out / "v5e_short_financing_etf_blockers.csv", final_blockers)
    (out / "v5e_short_financing_etf_next_prompt.md").write_text(_next_prompt(decision[0]), encoding="utf-8")
    (out / "v5e_short_financing_etf_agent_execution_rules.md").write_text(_agent_rules(), encoding="utf-8")
    (out / "v5e_short_financing_etf_selection_report.md").write_text(
        _report(bucket_summary, model_summary, capital_summary, decision),
        encoding="utf-8",
    )

    summary = _summary(
        "completed_short_financing_etf_cash_proxy_selection_gate",
        decision[0]["pm_gate_decision"],
        [],
        candidate_asset_code=ASSET_CODE,
        candidate_asset_name=ASSET_NAME,
        user_candidate_selected=True,
        specific_asset_selected_for_data_gate=True,
        engineering_test_allowed_now=False,
    )
    _write_json(out / "v5e_short_financing_etf_selection_summary.json", summary)
    return summary


def _candidate_profile() -> list[dict[str, Any]]:
    return [
        {
            "candidate_asset_code": ASSET_CODE,
            "candidate_asset_name": ASSET_NAME,
            "fund_full_name": FUND_FULL_NAME,
            "asset_type": "short_duration_bond_etf",
            "exchange": "SSE",
            "tracking_index": "中证短融指数",
            "candidate_role": "sleeve_cash_proxy_asset_candidate",
            "why_reasonable": "场内交易、短融指数型固收 ETF，风险收益低于权益资产，理论上可用于降低 V5e 现金空置拖累。",
            "main_caution": "不是货币基金；存在信用、利率、流动性、折溢价、跟踪误差和收益分配/折算处理风险。",
            "specific_asset_selected_for_data_gate": True,
            "trade_allowed": False,
            "accepted": False,
        }
    ]


def _source_snapshot() -> list[dict[str, Any]]:
    return [
        {
            "source_id": "sse_basic",
            "source_name": "上海证券交易所 ETF 基本信息",
            "url": "https://www.sse.com.cn/assortment/fund/list/etfinfo/basic/index.shtml?FUNDID=511360",
            "used_for": "exchange listing and share snapshot reference",
            "status": "public_reference_snapshot",
        },
        {
            "source_id": "hft_official",
            "source_name": "海富通基金产品页",
            "url": "https://www.hftfund.com/products/zhaiquan/511360/index.html",
            "used_for": "manager official product identity",
            "status": "public_reference_snapshot",
        },
        {
            "source_id": "eastmoney_profile",
            "source_name": "天天基金基金档案",
            "url": "https://fundf10.eastmoney.com/511360.html",
            "used_for": "fund type, benchmark, fee and investment-scope snapshot",
            "status": "public_reference_snapshot_requires_future_verification",
        },
        {
            "source_id": "eastmoney_dividend",
            "source_name": "天天基金分红送配",
            "url": "https://fundf10.eastmoney.com/fhsp_511360.html",
            "used_for": "dividend/split audit seed",
            "status": "public_reference_snapshot_requires_future_verification",
        },
    ]


def _pit_data_requirement() -> list[dict[str, Any]]:
    requirements = [
        ("daily_ohlc", "daily open/high/low/close, volume, amount", "trigger-free valuation and proxy return accounting"),
        ("nav_iopv_discount", "daily NAV, IOPV if available, close-to-NAV premium/discount", "execution and fair-value check"),
        ("distribution_split", "dividend, distribution, split/fold records", "total-return and sleeve bucket accounting"),
        ("tradability", "paused, limit status, exchange trading status", "T+1 execution feasibility"),
        ("fee_cost", "management fee, custody fee, commission, min fee, spread/slippage", "net cash proxy benefit audit"),
        ("minute_bars", "5min bars only on approved execution days if engineering later starts", "execution proxy only"),
        ("account_eligibility", "JoinQuant/account tradability and lot rules", "deployment feasibility"),
    ]
    return [
        {
            "candidate_asset_code": ASSET_CODE,
            "requirement_id": req_id,
            "description": desc,
            "pit_required": True,
            "allowed_usage": usage,
            "local_status": "not_verified_in_this_selection_gate",
            "blocker_if_missing_for_engineering": True,
        }
        for req_id, desc, usage in requirements
    ]


def _tradability_liquidity_checklist() -> list[dict[str, Any]]:
    checks = [
        ("listed_sse", "SSE listing active across requested history"),
        ("minimum_lot", "minimum lot and order notional compatible with V5e sleeve cash balances"),
        ("daily_turnover", "daily turnover sufficient for 50w/200w/800w cash proxy orders"),
        ("spread_discount", "spread and close-to-NAV premium/discount stable enough for execution proxy"),
        ("open_vwap_gap", "T+1 open and approved VWAP proxy do not create systematic bias"),
        ("unfilled_handling", "paused/no-print days have explicit unfilled fallback"),
    ]
    return [
        {
            "candidate_asset_code": ASSET_CODE,
            "check_id": check_id,
            "description": desc,
            "current_gate_status": "pending_pit_data_audit",
            "passed": False,
            "engineering_blocker_until_checked": True,
        }
        for check_id, desc in checks
    ]


def _risk_register() -> list[dict[str, Any]]:
    risks = [
        ("credit_risk", "短融/超短融与信用债成分带来信用风险，不等同现金。", "high"),
        ("interest_rate_risk", "短久期不代表无利率波动。", "medium"),
        ("tracking_error", "ETF 跟踪中证短融指数，抽样复制和替代策略会带来偏离。", "medium"),
        ("liquidity_discount_risk", "二级市场成交、折溢价、开盘价可能影响代理收益。", "medium"),
        ("income_accounting_risk", "分红、折算、净值和价格口径处理不当会虚增收益。", "high"),
        ("strategy_boundary_drift", "引入债券 ETF 会让 V5e 从现金持有扩展到新资产，不能视为 V57f core。", "high"),
    ]
    return [
        {
            "candidate_asset_code": ASSET_CODE,
            "risk_id": risk_id,
            "description": desc,
            "severity": severity,
            "mitigation": "PIT 数据审计、成本/流动性审计、用户批准和独立工程门。",
            "blocks_acceptance": True,
        }
        for risk_id, desc, severity in risks
    ]


def _income_nav_accounting() -> list[dict[str, Any]]:
    return [
        {
            "candidate_asset_code": ASSET_CODE,
            "accounting_topic": "total_return",
            "rule": "Engineering must use total-return accounting from price plus confirmed distributions/splits, not raw close only.",
            "required": True,
        },
        {
            "candidate_asset_code": ASSET_CODE,
            "accounting_topic": "sleeve_cash_bucket_income",
            "rule": "Any proxy income belongs to original sleeve cash bucket until next V57f rebalance.",
            "required": True,
        },
        {
            "candidate_asset_code": ASSET_CODE,
            "accounting_topic": "nav_discount",
            "rule": "Report close, NAV and premium/discount separately before comparing against cash baseline.",
            "required": True,
        },
    ]


def _v57f_boundary() -> list[dict[str, Any]]:
    return [
        {"boundary": "v57f_core", "rule": "511360 cannot be inserted into V57f core holdings.", "allowed": False},
        {"boundary": "stock_selection", "rule": "No V57f stock selection, sleeve, sector cap or target count change.", "allowed": False},
        {"boundary": "cash_proxy_status", "rule": "511360 is only a candidate cash proxy for exited sleeve cash, not accepted.", "allowed": False},
        {"boundary": "rebalance_restore", "rule": "At next V57f rebalance, official V57f target portfolio still controls restore.", "allowed": True},
    ]


def _v5d_boundary() -> list[dict[str, Any]]:
    return [
        {"component": "V5e", "responsibility": "Daily profit-lock exit remains unchanged.", "uses_5min_trigger": False},
        {"component": "511360 cash proxy", "responsibility": "May only be tested after PIT data audit and separate engineering approval.", "uses_5min_trigger": False},
        {"component": "V5d", "responsibility": "If later approved, handles execution price/unfilled governance.", "uses_5min_trigger": False},
    ]


def _blocked_actions() -> list[dict[str, Any]]:
    actions = [
        "buy_511360_in_current_task",
        "mark_511360_as_accepted_cash_proxy",
        "run_backtest_before_pit_data_audit",
        "modify_v57f_core",
        "change_v5e_profit_lock_threshold",
        "reentry_before_next_rebalance",
        "cross_sleeve_cash_transfer",
        "use_511360_intraday_trend_as_trade_trigger",
        "compare_using_price_only_without_total_return",
    ]
    return [{"action": action, "blocked": True, "reason": "Outside current selection/data-gate boundary."} for action in actions]


def _pm_gate_decision() -> list[dict[str, Any]]:
    return [
        {
            "pm_gate_decision": "short_financing_etf_511360_admit_to_pit_data_audit_not_engineering",
            "candidate_asset_code": ASSET_CODE,
            "specific_asset_selected_for_data_gate": True,
            "engineering_test_allowed_now": False,
            "requires_pit_history_fetch": True,
            "requires_total_return_audit": True,
            "accepted": False,
            "reason": "511360 is a reasonable short-duration bond ETF cash-proxy candidate, but must pass PIT price/NAV/distribution/liquidity/cost/account tradability gates before engineering.",
        }
    ]


def _next_queue(decision: str) -> list[dict[str, Any]]:
    return [
        {
            "priority": 1,
            "task": "V5e 511360 PIT data audit",
            "scope": "Fetch/audit daily price, NAV, distributions/splits, premium/discount, turnover and tradability for 511360.",
            "allowed": decision == "short_financing_etf_511360_admit_to_pit_data_audit_not_engineering",
            "requires_network_or_local_vendor_data": True,
            "requires_backtest": False,
        },
        {
            "priority": 2,
            "task": "V5e 511360 cash proxy limited engineering spec",
            "scope": "Only after PIT data audit passes; define T+1 buy/sell proxy handling without changing V57f.",
            "allowed": False,
            "requires_backtest": False,
        },
    ]


def _nonfatal_blockers() -> list[dict[str, Any]]:
    return [
        {
            "blocker_id": "pit_history_not_yet_audited",
            "severity": "next_gate",
            "status": "not_blocking_selection_blocks_engineering",
            "description": "511360 can enter PIT data audit, but engineering is blocked until history, NAV, distributions, cost and tradability pass.",
        }
    ]


def _summary(
    status: str,
    decision: str,
    fatal_blockers: list[dict[str, Any]],
    candidate_asset_code: str = "",
    candidate_asset_name: str = "",
    user_candidate_selected: bool = False,
    specific_asset_selected_for_data_gate: bool = False,
    engineering_test_allowed_now: bool = False,
) -> dict[str, Any]:
    return {
        "created_at_utc": now_utc(),
        "task": "v5e_short_financing_etf_cash_proxy_selection_gate",
        "status": status,
        "pm_gate_decision": decision,
        "candidate_asset_code": candidate_asset_code,
        "candidate_asset_name": candidate_asset_name,
        "user_candidate_selected": user_candidate_selected,
        "specific_asset_selected_for_data_gate": specific_asset_selected_for_data_gate,
        "engineering_test_allowed_now": engineering_test_allowed_now,
        "trade_allowed": False,
        "accepted": False,
        "v57f_core_modified": False,
        "v5e_threshold_modified": False,
        "reentry_allowed": False,
        "cross_sleeve_transfer_allowed": False,
        "joinquant_started": False,
        "fatal_blocker_count": len(fatal_blockers),
        "fatal_blockers": fatal_blockers,
    }


def _report(
    bucket_summary: dict[str, Any],
    model_summary: dict[str, Any],
    capital_summary: dict[str, Any],
    decision: list[dict[str, Any]],
) -> str:
    return "\n".join(
        [
            "# V5e Short Financing ETF Cash Proxy Selection Gate",
            "",
            f"- Candidate: `{ASSET_CODE}` / `{ASSET_NAME}`.",
            f"- PM gate decision: `{decision[0]['pm_gate_decision']}`",
            "- Status: selected for PIT data audit only; not accepted and not tradable in current task.",
            "",
            "## Read",
            "- Short financing ETF is directionally reasonable as a V5e sleeve cash proxy candidate because it is a listed short-duration fixed-income ETF and sits closer to cash management than equity reallocation.",
            "- It is not cash: credit risk, interest-rate risk, tracking error, premium/discount, liquidity and income accounting must be audited.",
            "",
            "## V5e Context",
            f"- Primary sleeve cash drag source: {bucket_summary.get('primary_cash_drag_sleeve')}",
            f"- V5e profit-lock VWAP adjusted delta at 200w: {model_summary.get('vwap_adjusted_delta_return_pct_points_200w')} pct points",
            f"- Capital sensitivity gate: {capital_summary.get('pm_gate_decision')}",
            "",
            "## Next",
            "- Run a PIT data audit for 511360 before any engineering comparison.",
            "- Do not modify V57f, V5e thresholds, reentry rules, or sleeve cash restoration.",
            "",
        ]
    )


def _next_prompt(decision: dict[str, Any]) -> str:
    return f"""工作目录：
D:\\hh\\codex\\v5

任务名称：
V5e 511360 short financing ETF cash proxy PIT data audit

任务目标：
基于 `v5e_short_financing_etf_cash_proxy_selection_gate/current/`，对用户指定候选 `{ASSET_CODE}` / `{ASSET_NAME}` 做 PIT 数据审计。只审计数据可用性、总收益口径、NAV/折溢价、成交流动性、费用成本和账户可交易性；不得回测，不得买入，不得标记 accepted。

当前 gate：
`{decision["pm_gate_decision"]}`

必须审计：
1. 2021-05-06 起至当前 V5e 样本结束日的 daily open/high/low/close/volume/amount；
2. NAV / IOPV / close-to-NAV premium-discount，如本地或公开源可得；
3. 分红、折算、拆分和 total-return 口径；
4. 停牌、无成交、涨跌停或异常开盘；
5. 50w / 200w / 800w 对应 sleeve cash order 的成交额覆盖；
6. 佣金、最低佣金、ETF 费用、滑点/价差代理；
7. 是否可由本地数据源、BaoStock、交易所、基金公司或平台数据补齐。

硬边界：
- 不修改 V57f / ERC / V5d。
- 不改变 V5e +20% / sell50 规则。
- 不允许 reentry before next rebalance。
- 不允许跨 sleeve 转移现金。
- 不使用 5分钟走势触发交易。
- 不工程回测，不参数扫描。
- 不把 `{ASSET_CODE}` 标记 accepted。
"""


def _agent_rules() -> str:
    return "\n".join(
        [
            "# V5e Short Financing ETF Cash Proxy Selection Gate Rules",
            "",
            "- Candidate selection/data gate only; do not trade 511360.",
            "- Do not run backtest before PIT data audit.",
            "- Do not modify V57f, ERC, V5d, or V5e thresholds.",
            "- Do not allow reentry before next rebalance.",
            "- Do not transfer cash across sleeves.",
            "- Do not use 5min data as a trigger.",
            "- Use total-return accounting; do not compare raw close only.",
            "- Do not mark accepted.",
            "",
        ]
    )


def _missing_inputs(root: Path) -> list[dict[str, Any]]:
    required = [
        CASH_PROXY_DIR / "v5e_cash_proxy_asset_data_gate_summary.json",
        CASH_PROXY_DIR / "v5e_cash_proxy_asset_candidate_type_matrix.csv",
        BUCKET_DIR / "v5e_sleeve_cash_bucket_summary.json",
        MODEL_DIR / "v5e_model_comparison_summary.json",
        CAPITAL_DIR / "v5e_capital_sensitivity_summary.json",
        STARTUP_DIR / "v5_startup_warmup_price_repair_summary.json",
        SHADOW_CONFIG,
    ]
    return [
        {
            "blocker_id": "missing_required_input",
            "severity": "fatal",
            "status": "blocking",
            "path": str(path),
            "description": "Required 511360 cash proxy selection input is missing.",
        }
        for path in required
        if not (root / path).exists()
    ]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    result = run_v5e_short_financing_etf_cash_proxy_selection_gate()
    print(json.dumps(result, ensure_ascii=False, indent=2))

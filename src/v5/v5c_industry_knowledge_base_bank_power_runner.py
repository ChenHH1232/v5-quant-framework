from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path("v5c_industry_knowledge_base_bank_power_p0") / "current"
KB_DIR = Path("knowledge") / "research_agent" / "v5c_industry_bank_power_p0"


def run(root: Path = ROOT) -> Path:
    out = root / OUT_DIR
    kb = root / KB_DIR
    out.mkdir(parents=True, exist_ok=True)
    kb.mkdir(parents=True, exist_ok=True)

    source_register = _source_register()
    knowledge_cards = _knowledge_cards()
    bank_map = _bank_driver_metric_map()
    power_map = _power_driver_metric_map()
    state_mapping = _state_tag_mapping()
    pit_requirements = _pit_requirements()
    evidence_policy = _evidence_policy()
    observation_schema = _observation_schema()
    gap_queue = _gap_queue()
    blocked_actions = _blocked_actions()
    pm_decision = _pm_decision()
    next_queue = _next_queue()

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5c_industry_knowledge_base_bank_power_p0",
        "status": "completed_p0_industry_knowledge_base",
        "industry_scope": ["bank", "utilities_electricity"],
        "source_count": len(source_register),
        "knowledge_card_count": len(knowledge_cards),
        "bank_driver_count": len(bank_map),
        "power_driver_count": len(power_map),
        "state_tag_count": len(state_mapping),
        "pit_requirement_count": len(pit_requirements),
        "knowledge_base_path": str(KB_DIR),
        "v5c_role": "industry_state_explanation_and_pm_review_only",
        "can_change_weights": False,
        "can_trigger_trade": False,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "dedicated_bank_power_book_gap": True,
        "pm_gate_decision": "admit_bank_power_industry_knowledge_to_v5c_observation_layer_only",
    }

    outputs = {
        "v5c_industry_knowledge_summary.json": summary,
        "v5c_industry_source_register.csv": source_register,
        "v5c_industry_knowledge_cards.csv": knowledge_cards,
        "v5c_bank_driver_metric_map.csv": bank_map,
        "v5c_power_driver_metric_map.csv": power_map,
        "v5c_industry_state_tag_mapping.csv": state_mapping,
        "v5c_industry_pit_data_requirements.csv": pit_requirements,
        "v5c_industry_evidence_layer_policy.csv": evidence_policy,
        "v5c_industry_forward_observation_schema.csv": observation_schema,
        "v5c_industry_gap_and_collection_queue.csv": gap_queue,
        "v5c_industry_blocked_actions.csv": blocked_actions,
        "v5c_industry_pm_gate_decision.csv": pm_decision,
        "v5c_industry_next_queue.csv": next_queue,
    }

    for name, payload in outputs.items():
        if name.endswith(".json"):
            _write_json(out / name, payload)
            _write_json(kb / name, payload)
        else:
            _write_csv(out / name, payload)
            _write_csv(kb / name, payload)

    _write_report(out / "v5c_industry_knowledge_report.md", summary)
    _write_report(kb / "v5c_industry_knowledge_report.md", summary)
    _write_rules(out / "v5c_industry_agent_execution_rules.md")
    _write_rules(kb / "v5c_industry_agent_execution_rules.md")
    _write_index(kb / "INDEX.md", summary)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return out / "v5c_industry_knowledge_summary.json"


def _source_register() -> list[dict[str, Any]]:
    return [
        {
            "source_id": "LOCAL_BANK_SOP_001",
            "industry": "bank",
            "source_type": "governance_sop",
            "source_title": "Research Agent SOP: Bank Sector Knowledge Collection",
            "source_path": "docs/RESEARCH_AGENT_BANK_KNOWLEDGE_COLLECTION_SOP.md",
            "evidence_layer": "core_governance",
            "evidence_grade": "A",
            "pit_use": "defines collection policy only",
            "review_status": "reviewed_local",
        },
        {
            "source_id": "LOCAL_BANK_V5_REPORT_001",
            "industry": "bank",
            "source_type": "internal_research_report",
            "source_title": "Bank Quant V5 Third Test Phase Report",
            "source_path": "docs/reports/Bank_Quant_V5_Third_Test_Phase_Report.md",
            "evidence_layer": "validated_findings",
            "evidence_grade": "B",
            "pit_use": "research/process evidence, not new V5c rule",
            "review_status": "local_file_available_encoding_review_needed",
        },
        {
            "source_id": "LOCAL_POWER_STATE_001",
            "industry": "utilities_electricity",
            "source_type": "state_panel_result",
            "source_title": "V5.1 Utilities External State Panel Result",
            "source_path": "docs/V51_UTILITIES_EXTERNAL_STATE_PANEL_RESULT.md",
            "evidence_layer": "validated_findings",
            "evidence_grade": "A",
            "pit_use": "demand-state source policy and coverage",
            "review_status": "reviewed_local",
        },
        {
            "source_id": "LOCAL_POWER_RETRO_001",
            "industry": "utilities_electricity",
            "source_type": "internal_research_retrospective",
            "source_title": "V5.1 Utilities Series Retrospective",
            "source_path": "docs/V51_UTILITIES_SERIES_RETROSPECTIVE.md",
            "evidence_layer": "validated_findings",
            "evidence_grade": "A",
            "pit_use": "explains why generic financial composite failed",
            "review_status": "reviewed_local",
        },
        {
            "source_id": "V5C_P2_001",
            "industry": "bank;utilities_electricity",
            "source_type": "v5c_state_panel",
            "source_title": "V5c P2 valuation and crowding state panel",
            "source_path": "v5c_p2_valuation_and_crowding_state_panel/current",
            "evidence_layer": "validated_findings",
            "evidence_grade": "A",
            "pit_use": "valuation/crowding panel dependency",
            "review_status": "reviewed_local",
        },
        {
            "source_id": "V5C_P3_001",
            "industry": "bank;utilities_electricity",
            "source_type": "v5c_governance_spec",
            "source_title": "V5c P3 state governance quant spec",
            "source_path": "v5c_p3_state_governance_quant_spec/current",
            "evidence_layer": "governance_boundary",
            "evidence_grade": "A",
            "pit_use": "defines state tag boundaries",
            "review_status": "reviewed_local",
        },
        {
            "source_id": "V5C_P4_001",
            "industry": "bank;utilities_electricity",
            "source_type": "v5c_forward_observation_packet",
            "source_title": "V5c P4 state forward observation packet",
            "source_path": "v5c_p4_state_forward_observation_packet/current",
            "evidence_layer": "forward_observation",
            "evidence_grade": "A",
            "pit_use": "observation template and watchlist seed",
            "review_status": "reviewed_local",
        },
        {
            "source_id": "WEREAD_CORE_001",
            "industry": "cross_industry",
            "source_type": "book_notes",
            "source_title": "WeRead core book note cards",
            "source_path": "knowledge/research_agent/v5c_defense_profit_taking/24_weread_core_book_note_cards.csv",
            "evidence_layer": "book_framework",
            "evidence_grade": "C",
            "pit_use": "framework only, no quantitative threshold",
            "review_status": "reviewed_paraphrase_only",
        },
        {
            "source_id": "FX_POWER_LEAD_001",
            "industry": "utilities_electricity",
            "source_type": "report_lead",
            "source_title": "电价提升开启β上行，看好电力ETF配置价值",
            "source_path": "knowledge/research_agent/v5c_defense_profit_taking/02_source_register.csv:SRC_FX_006",
            "evidence_layer": "industry_research_lead",
            "evidence_grade": "B_pending_pdf_review",
            "pit_use": "source lead only until PDF-reviewed",
            "review_status": "source_lead_needs_pdf",
        },
    ]


def _knowledge_cards() -> list[dict[str, Any]]:
    return [
        _card("BANK_KB_001", "bank", "LOCAL_BANK_SOP_001", "bank_regulatory_definitions_first", "银行行业状态标签必须先定义监管口径，再解释投资含义。核心字段包括资本充足率、核心一级资本、不良率、拨备覆盖率、净息差、分红和信用周期。", "PM/Quant state definition", "No trading trigger."),
        _card("BANK_KB_002", "bank", "LOCAL_BANK_V5_REPORT_001", "bank_quality_panel_pit_audit", "银行质量字段方向是对的，但公司级 PIT、公告可见日和字段覆盖比单纯收益更重要。V5c 只能把它们作为状态解释和数据门，不能用旧样本直接升级规则。", "Data gate and review queue", "No accepted status."),
        _card("BANK_KB_003", "bank", "WEREAD_CORE_001", "margin_of_safety_and_bank_value", "银行低 PB 和高股息只有在 ROE、资产质量、资本缓冲和分红可持续性同时可解释时，才更像安全边际；否则可能是价值陷阱。", "State explanation", "No numeric threshold from book notes."),
        _card("BANK_KB_004", "bank", "WEREAD_CORE_001", "behavioral_caution_for_high_dividend", "高股息可能吸引拥挤交易，也可能只是价格下跌后的表观高息。V5c 应记录估值、成交额、分红质量和资产质量状态，而不是追逐高息叙事。", "Crowding and PM review", "No automatic buy/sell."),
        _card("POWER_KB_001", "utilities_electricity", "LOCAL_POWER_STATE_001", "power_demand_state_available", "电力已有 PIT 可用的需求状态面板，覆盖用电量累计、同比、二产用电同比等，可支持需求强弱观察。", "Forward state tag", "Does not cover tariff/coal/water regime fully."),
        _card("POWER_KB_002", "utilities_electricity", "LOCAL_POWER_RETRO_001", "generic_composite_failed", "电力行业中通用低估值、现金流、分红、低波组合规则反复输给简单 raw baseline，说明关键不是再加静态因子，而是补燃料成本、电价机制、利用小时、来水和政策状态。", "Research direction", "Do not keep testing generic composites."),
        _card("POWER_KB_003", "utilities_electricity", "FX_POWER_LEAD_001", "power_tariff_report_lead", "电价提升、电力 ETF 配置价值等研报线索可进入报告复核队列，但未完成 PDF 逐段审阅前只能作为 source lead。", "Report review queue", "No evidence card until PDF-reviewed."),
        _card("POWER_KB_004", "utilities_electricity", "WEREAD_CORE_001", "capex_and_utility_risk", "公用事业高 capex 和高杠杆可能是行业常态。V5c 需要区分维护性资本开支、扩张性资本开支、政策投资和现金回收周期。", "State explanation", "No mechanical penalty without industry state."),
        _card("CROSS_KB_001", "bank;utilities_electricity", "WEREAD_CORE_001", "process_discipline", "书籍笔记支持流程纪律：知识只能帮助解释行业状态和设计数据门，不能把观点直接变成交易参数。", "Governance", "No direct rule."),
    ]


def _bank_driver_metric_map() -> list[dict[str, Any]]:
    return [
        _driver("bank", "net_interest_margin_pressure", "NIM, deposit cost, loan repricing, LPR/rate state", "bank_nim_pressure_watch", "company reports; PBOC rate/LPR materials; bank PIT panel", "needs_PIT_panel_expansion"),
        _driver("bank", "asset_quality_cycle", "NPL ratio, special mention loans, overdue loans, provision coverage", "bank_asset_quality_deterioration_watch", "annual/interim reports; NFRA/PBOC context", "needs_company_level_review"),
        _driver("bank", "capital_buffer", "CET1, tier1, capital adequacy, RWA growth", "bank_capital_buffer_weak_watch", "annual/interim reports; Basel/NFRA definitions", "needs_regulatory_definition_anchor"),
        _driver("bank", "dividend_sustainability", "cash dividend, payout ratio, retained earnings, capital pressure", "bank_dividend_sustainability_support_or_watch", "company dividend plans; cash dividend panel", "partially_available_in_v5c_p1"),
        _driver("bank", "valuation_profitability_alignment", "PB, ROE, ROA, dividend yield, earnings quality", "bank_valuation_roe_mismatch_watch", "startup repaired factor panels; financial PIT panels", "available_partial"),
        _driver("bank", "real_estate_and_local_debt_exposure", "mortgage/developer/local platform exposure and impairment language", "bank_credit_exposure_watch", "annual reports; interim reports; PM review notes", "manual_review_required"),
    ]


def _power_driver_metric_map() -> list[dict[str, Any]]:
    return [
        _driver("utilities_electricity", "electricity_demand", "electricity consumption yoy, secondary industry power yoy", "power_demand_strength_or_weakness", "V51 utilities external state panel", "available_PIT_conservative_proxy"),
        _driver("utilities_electricity", "fuel_cost_pressure", "thermal coal price, power coal consumption, coal power spread", "power_fuel_cost_pressure_watch", "coal price data; NEA/NBS/company reports", "P0_gap"),
        _driver("utilities_electricity", "tariff_and_capacity_payment", "marketized tariff, benchmark tariff, capacity payment, ancillary services", "power_tariff_support_or_policy_watch", "policy documents; broker reports; company filings", "P0_gap"),
        _driver("utilities_electricity", "utilization_hours", "thermal/hydro/nuclear utilization hours and generation mix", "power_utilization_state", "NEA releases; company reports", "sparse_available"),
        _driver("utilities_electricity", "hydro_water_condition", "inflow, reservoir, hydropower utilization and regional rainfall", "hydro_water_stress_or_support", "hydrology/public reports; company filings", "P0_gap"),
        _driver("utilities_electricity", "capex_debt_cashflow", "capex intensity, debt ratio, interest burden, operating cash flow", "power_capex_debt_pressure_watch", "PIT financial panel; company reports", "needs_subindustry_context"),
        _driver("utilities_electricity", "renewable_subsidy_receivables", "subsidy receivables, collection cycle, impairment risk", "renewable_subsidy_cashflow_watch", "company reports; policy documents", "manual_review_required"),
    ]


def _state_tag_mapping() -> list[dict[str, Any]]:
    return [
        _tag("bank_nim_pressure_watch", "bank", "NIM/deposit/loan repricing state suggests margin pressure.", "pm_review_only", False),
        _tag("bank_asset_quality_deterioration_watch", "bank", "Asset quality or provision state weakens dividend/valuation confidence.", "pm_review_only", False),
        _tag("bank_capital_buffer_weak_watch", "bank", "Capital buffer looks thin relative to growth/dividend pressure.", "pm_review_only", False),
        _tag("bank_dividend_sustainability_support", "bank", "Dividend appears supported by payout, capital and earnings quality evidence.", "support_context_only", False),
        _tag("bank_valuation_roe_mismatch_watch", "bank", "Low PB/high yield not matched by stable ROE or quality evidence.", "watchlist_context_only", False),
        _tag("power_demand_strength_support", "utilities_electricity", "Electricity demand state supports sector context.", "support_context_only", False),
        _tag("power_fuel_cost_pressure_watch", "utilities_electricity", "Fuel cost regime may pressure thermal power margin.", "pm_review_only", False),
        _tag("power_tariff_support_watch", "utilities_electricity", "Tariff/capacity-payment state may support earnings.", "support_context_only", False),
        _tag("hydro_water_stress_watch", "utilities_electricity", "Water condition may pressure hydropower output.", "pm_review_only", False),
        _tag("power_capex_debt_pressure_watch", "utilities_electricity", "Capex/debt/cash-flow state needs subindustry review.", "pm_review_only", False),
        _tag("renewable_subsidy_cashflow_watch", "utilities_electricity", "Subsidy/receivable state may affect cash flow quality.", "pm_review_only", False),
    ]


def _pit_requirements() -> list[dict[str, Any]]:
    return [
        _pit("bank", "bank_regulatory_definitions", "Basel/NFRA/PBOC official definitions", "definition anchor", "P0_ready_manual_register"),
        _pit("bank", "NIM_and_deposit_cost_panel", "annual/interim reports or verified data vendor with notice_date", "PIT company metric", "P1_required"),
        _pit("bank", "asset_quality_panel", "NPL, special mention, provision coverage with announcement visible date", "PIT company metric", "P1_required"),
        _pit("bank", "capital_adequacy_panel", "CET1/tier1/capital adequacy and RWA growth", "PIT company metric", "P1_required"),
        _pit("bank", "dividend_sustainability_panel", "cash dividend, payout ratio, retained earnings, OCF where relevant", "PIT company metric", "partially_ready"),
        _pit("utilities_electricity", "electricity_demand_panel", "V51 external state panel", "PIT state variable", "P0_ready"),
        _pit("utilities_electricity", "coal_price_and_fuel_cost_panel", "coal price/fuel spread with visible dates", "PIT state variable", "P1_required"),
        _pit("utilities_electricity", "tariff_capacity_policy_panel", "policy/report dates for tariffs and capacity payment", "PIT state variable", "P1_required"),
        _pit("utilities_electricity", "utilization_hours_panel", "NEA/company data by power type", "PIT state variable", "partial_sparse"),
        _pit("utilities_electricity", "hydro_water_condition_panel", "hydrology/rainfall/reservoir state with visible dates", "PIT state variable", "P1_required"),
        _pit("utilities_electricity", "capex_debt_cashflow_panel", "company financial PIT fields by subindustry", "PIT company metric", "partially_ready"),
    ]


def _evidence_policy() -> list[dict[str, Any]]:
    return [
        {"evidence_layer": "official_or_regulatory", "grade": "A", "allowed_use": "definition; PIT source anchor; state variable if dated", "blocked_use": "none, but still no direct trading without Quant gate"},
        {"evidence_layer": "validated_internal_findings", "grade": "A/B", "allowed_use": "V5c observation, PM review, data gate priority", "blocked_use": "accepted/live without forward evidence"},
        {"evidence_layer": "industry_research_report", "grade": "B", "allowed_use": "hypothesis and state explanation after PDF review", "blocked_use": "raw title/search result as evidence"},
        {"evidence_layer": "book_framework", "grade": "C", "allowed_use": "governance language and conceptual framing", "blocked_use": "numeric threshold; signal; accepted status"},
        {"evidence_layer": "market_article_or_blog", "grade": "D", "allowed_use": "source lead only", "blocked_use": "fact evidence or trading rule"},
    ]


def _observation_schema() -> list[dict[str, Any]]:
    return [
        {"field": "observation_date", "required": True, "description": "date when state is observed"},
        {"field": "industry", "required": True, "description": "bank or utilities_electricity"},
        {"field": "sleeve", "required": True, "description": "V57f sleeve id"},
        {"field": "code", "required": False, "description": "optional stock code for company-level tag"},
        {"field": "state_tag", "required": True, "description": "tag from v5c_industry_state_tag_mapping"},
        {"field": "metric_name", "required": True, "description": "source metric behind tag"},
        {"field": "metric_value", "required": False, "description": "value if available"},
        {"field": "visible_date", "required": True, "description": "PIT visible date"},
        {"field": "source_id", "required": True, "description": "source register id"},
        {"field": "evidence_grade", "required": True, "description": "A/B/C/D"},
        {"field": "allowed_role", "required": True, "description": "support_context_only, pm_review_only, diagnostic_only"},
        {"field": "changes_weight", "required": True, "description": "must be false"},
        {"field": "pm_review_required", "required": True, "description": "true when tag is a watch state"},
    ]


def _gap_queue() -> list[dict[str, Any]]:
    return [
        {"priority": "P0", "industry": "bank", "gap": "dedicated bank industry-analysis book cards missing", "next_action": "collect paraphrased notes from bank accounting/valuation books or official regulatory primers", "status": "open"},
        {"priority": "P0", "industry": "utilities_electricity", "gap": "dedicated power industry-analysis book cards missing", "next_action": "collect paraphrased notes from power market/power enterprise analysis books or policy primers", "status": "open"},
        {"priority": "P1", "industry": "bank", "gap": "NIM, asset quality, capital adequacy PIT company panels incomplete", "next_action": "extend P1 financial quality panel", "status": "ready"},
        {"priority": "P1", "industry": "utilities_electricity", "gap": "coal/tariff/hydro state panels incomplete", "next_action": "build PIT state panels before any power overlay", "status": "ready"},
        {"priority": "P2", "industry": "utilities_electricity", "gap": "electricity ETF report lead not PDF-reviewed", "next_action": "review report PDF before promoting to evidence card", "status": "queued"},
    ]


def _blocked_actions() -> list[dict[str, Any]]:
    return [
        {"action": "use_books_to_set_thresholds", "blocked": True, "reason": "Books are framework evidence only."},
        {"action": "use_report_title_as_evidence", "blocked": True, "reason": "Report leads need PDF/paragraph review."},
        {"action": "change_v5f_or_v57f_weights_from_industry_tags", "blocked": True, "reason": "Current P0 is observation only."},
        {"action": "trigger_trade_from_industry_state", "blocked": True, "reason": "Requires separate Quant spec and forward validation."},
        {"action": "mark_accepted_or_live_approved", "blocked": True, "reason": "Not allowed from knowledge-base work."},
    ]


def _pm_decision() -> list[dict[str, Any]]:
    return [
        {
            "pm_gate_decision": "admit_bank_power_industry_knowledge_to_v5c_observation_layer_only",
            "bank_status": "framework_and_data_gate_ready_PIT_panels_need_expansion",
            "power_status": "demand_state_ready_coal_tariff_hydro_gaps_open",
            "accepted": False,
            "live_trading_approved": False,
            "v57f_core_modified": False,
            "next_action": "collect_P0_dedicated_book_cards_and_P1_industry_state_panels",
        }
    ]


def _next_queue() -> list[dict[str, Any]]:
    return [
        {"rank": 1, "next_task": "v5c_bank_power_dedicated_book_card_collection", "status": "ready", "detail": "Collect paraphrased notes from bank and power industry-analysis books; no full-book ingestion."},
        {"rank": 2, "next_task": "v5c_bank_p1_nim_asset_quality_capital_panel", "status": "ready", "detail": "Extend PIT company-level bank panel."},
        {"rank": 3, "next_task": "v5c_power_p1_coal_tariff_hydro_state_panel", "status": "ready", "detail": "Extend power state variables beyond demand."},
        {"rank": 4, "next_task": "attach_bank_power_tags_to_v5f_forward_tracking", "status": "ready_after_P1", "detail": "Tags remain observation only."},
    ]


def _card(card_id: str, industry: str, source_id: str, theme: str, note: str, allowed: str, blocked: str) -> dict[str, Any]:
    return {
        "card_id": card_id,
        "industry": industry,
        "source_id": source_id,
        "theme": theme,
        "paraphrased_note": note,
        "allowed_use": allowed,
        "blocked_use": blocked,
        "evidence_status": "reviewed_p0_knowledge_card",
    }


def _driver(industry: str, driver: str, metric: str, state_tag: str, source: str, status: str) -> dict[str, Any]:
    return {
        "industry": industry,
        "driver": driver,
        "metric_or_observation": metric,
        "proposed_state_tag": state_tag,
        "source_or_panel": source,
        "coverage_status": status,
        "can_trigger_trade": False,
        "can_change_weight": False,
    }


def _tag(tag: str, industry: str, definition: str, role: str, can_trade: bool) -> dict[str, Any]:
    return {
        "state_tag": tag,
        "industry": industry,
        "definition": definition,
        "allowed_role": role,
        "can_trigger_trade": can_trade,
        "can_modify_weight": False,
        "requires_pm_review": "watch" in tag or role == "pm_review_only",
    }


def _pit(industry: str, requirement: str, source: str, use: str, status: str) -> dict[str, Any]:
    return {
        "industry": industry,
        "data_requirement": requirement,
        "preferred_source": source,
        "v5c_use": use,
        "status": status,
        "pit_visible_date_required": True,
    }


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    text = f"""# V5c Industry Knowledge Base P0: Bank + Power

## Decision

Bank and power industry knowledge is admitted to V5c as an observation layer only.

## Scope

- Industries: bank, utilities_electricity.
- Sources: local V5 bank/power reports, V5c P2/P3/P4 packets, WeRead paraphrased book cards, and report leads.
- Output knowledge base: `{summary['knowledge_base_path']}`.

## Findings

- Bank: regulatory definitions and V5 bank process evidence are available, but dedicated bank industry book cards and expanded NIM/asset-quality/capital PIT panels are still needed.
- Power: electricity demand state is PIT-usable through the V51 external state panel, but coal price, tariff/capacity payment, hydro water condition and power-type utilization remain open gaps.
- Books: useful for governance and industry-analysis framing, but cannot set thresholds or trigger trades.
- Reports/articles: useful as source leads after review; raw titles or snippets cannot become evidence.

## Boundary

No V5f/V57f weight changes, no trade triggers, no accepted/live approval.

## PM Gate

`{summary['pm_gate_decision']}`
"""
    path.write_text(text, encoding="utf-8")


def _write_rules(path: Path) -> None:
    path.write_text(
        """# V5c Industry Knowledge Base Execution Rules

- Use industry knowledge for V5c observation, PM review and data-gate design only.
- Do not change V57f or V5f trading rules.
- Do not use books to set numeric thresholds.
- Do not use report titles or snippets as evidence before PDF/paragraph review.
- Require PIT visible dates for any metric used as a state tag.
- Keep bank and power tags industry-specific; do not generalize one sleeve's logic to another sleeve without review.
- Do not mark accepted or live approved.
""",
        encoding="utf-8",
    )


def _write_index(path: Path, summary: dict[str, Any]) -> None:
    path.write_text(
        f"""# V5c Industry Bank + Power P0 Knowledge Base

Status: `{summary['status']}`

Role: `{summary['v5c_role']}`

Files:
- `v5c_industry_source_register.csv`
- `v5c_industry_knowledge_cards.csv`
- `v5c_bank_driver_metric_map.csv`
- `v5c_power_driver_metric_map.csv`
- `v5c_industry_state_tag_mapping.csv`
- `v5c_industry_pit_data_requirements.csv`

This folder is a reusable knowledge-base layer. It does not contain trading rules.
""",
        encoding="utf-8",
    )


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
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
    run()

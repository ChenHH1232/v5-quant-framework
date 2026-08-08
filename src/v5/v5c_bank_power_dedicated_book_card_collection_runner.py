from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path("v5c_bank_power_dedicated_book_card_collection") / "current"
KB_DIR = Path("knowledge") / "research_agent" / "v5c_industry_bank_power_dedicated_cards"


def run(root: Path = ROOT) -> Path:
    out = root / OUT_DIR
    kb = root / KB_DIR
    out.mkdir(parents=True, exist_ok=True)
    kb.mkdir(parents=True, exist_ok=True)

    p0_summary = root / "v5c_industry_knowledge_base_bank_power_p0" / "current" / "v5c_industry_knowledge_summary.json"
    if not p0_summary.exists():
        raise FileNotFoundError(f"Missing P0 industry knowledge summary: {p0_summary}")

    source_register = _source_register()
    bank_cards = _bank_book_cards()
    power_cards = _power_book_cards()
    report_cards = _report_article_cards()
    metric_map = _metric_extraction_map()
    pit_queue = _pit_data_gate_queue()
    state_queue = _state_tag_upgrade_queue()
    blocked = _blocked_actions()
    pm_decision = _pm_gate_decision()
    next_queue = _next_queue()

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "task": "v5c_bank_power_dedicated_book_card_collection",
        "status": "completed_dedicated_book_report_card_collection",
        "depends_on": str(p0_summary.relative_to(root)),
        "industry_scope": ["bank", "utilities_electricity"],
        "source_count": len(source_register),
        "bank_book_card_count": len(bank_cards),
        "power_book_card_count": len(power_cards),
        "report_article_card_count": len(report_cards),
        "metric_map_count": len(metric_map),
        "pit_queue_count": len(pit_queue),
        "knowledge_base_path": str(KB_DIR),
        "fxbaogao_api_key_present": bool(os.environ.get("FXBAOGAO_API_KEY")),
        "v5c_role": "dedicated_industry_framework_and_data_gate_only",
        "can_change_weights": False,
        "can_trigger_trade": False,
        "can_set_threshold": False,
        "accepted": False,
        "live_trading_approved": False,
        "v57f_core_modified": False,
        "pm_gate_decision": "admit_dedicated_bank_power_book_cards_to_v5c_observation_knowledge_base",
    }

    csv_outputs = {
        "v5c_bank_power_dedicated_source_register.csv": source_register,
        "v5c_bank_industry_book_cards.csv": bank_cards,
        "v5c_power_industry_book_cards.csv": power_cards,
        "v5c_bank_power_report_article_cards.csv": report_cards,
        "v5c_bank_power_metric_extraction_map.csv": metric_map,
        "v5c_bank_power_pit_data_gate_queue.csv": pit_queue,
        "v5c_bank_power_state_tag_upgrade_queue.csv": state_queue,
        "v5c_bank_power_blocked_actions.csv": blocked,
        "v5c_bank_power_pm_gate_decision.csv": pm_decision,
        "v5c_bank_power_next_agent_queue.csv": next_queue,
    }

    _write_json(out / "v5c_bank_power_dedicated_summary.json", summary)
    _write_json(kb / "v5c_bank_power_dedicated_summary.json", summary)
    for name, rows in csv_outputs.items():
        _write_csv(out / name, rows)
        _write_csv(kb / name, rows)

    _write_report(out / "v5c_bank_power_dedicated_report.md", summary)
    _write_report(kb / "v5c_bank_power_dedicated_report.md", summary)
    _write_rules(out / "v5c_bank_power_agent_execution_rules.md")
    _write_rules(kb / "v5c_bank_power_agent_execution_rules.md")
    _write_index(kb / "INDEX.md", summary)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return out / "v5c_bank_power_dedicated_summary.json"


def _source_register() -> list[dict[str, Any]]:
    return [
        _source(
            "BANK_BOOK_001",
            "bank",
            "book",
            "商业银行经营学（第六版）",
            "高等教育出版社产品信息；上海财经大学相关课程材料",
            "https://xuanshu.hep.com.cn/front/book/findBookDetails?bookId=61310a1cadb85dae6a2f48e2",
            "C",
            "book_framework_only",
            "reviewed_public_catalog_not_full_book",
            "经营管理、资本监管、风险管理和银行业务框架；不用于量化阈值。",
        ),
        _source(
            "BANK_BOOK_002",
            "bank",
            "book",
            "商业银行经营管理学",
            "上海财经大学出版社",
            "https://www.sufep.com/e/action/ShowInfo.php?classid=26&id=16043",
            "C",
            "book_framework_only",
            "public_catalog_lead",
            "经营目标、安全性、流动性、盈利性和风险测量框架。",
        ),
        _source(
            "BANK_OFFICIAL_001",
            "bank",
            "official_statistics",
            "商业银行主要监管指标情况表",
            "国家金融监督管理总局",
            "https://www.nfra.gov.cn/cn/view/pages/ItemList.html?itemId=954&itemName=%E7%BB%9F%E8%AE%A1%E4%BF%A1%E6%81%AF&itemPId=953&itemUrl=ItemListRightList.html",
            "A",
            "pit_data_anchor",
            "official_source_anchor",
            "行业净息差、不良率、拨备覆盖率、资本充足率等监管口径源。",
        ),
        _source(
            "BANK_REPORT_001",
            "bank",
            "industry_report",
            "2026 年商业银行行业分析",
            "联合资信",
            "https://www.lhratings.com/file/g2a76d48524.pdf",
            "B",
            "report_context_and_metric_lead",
            "pdf_available_public",
            "行业 NIM、资产质量、资本缓冲、盈利压力的报告线索。",
        ),
        _source(
            "BANK_REPORT_002",
            "bank",
            "industry_report",
            "2024 年半年度中国银行业回顾与展望",
            "普华永道中国",
            "https://www.pwccn.com/zh/banking/banking-newsletter-2024-h1.pdf",
            "B",
            "report_context_only",
            "pdf_available_public",
            "上市银行息差、资本和拨备状态的行业背景材料。",
        ),
        _source(
            "POWER_BOOK_001",
            "utilities_electricity",
            "book",
            "电力系统经济学原理（原书第2版）",
            "机械工业出版社",
            "https://www.cmpedu.com/books/book/5606781.htm",
            "C",
            "book_framework_only",
            "reviewed_public_catalog_not_full_book",
            "电能量市场、辅助服务、容量补偿、容量市场和输电投资框架。",
        ),
        _source(
            "POWER_BOOK_002",
            "utilities_electricity",
            "book",
            "电力市场手册",
            "European University Institute / public PDF",
            "https://cadmus.eui.eu/bitstreams/26b97fa0-157e-5c88-95c3-b7a76279ac2c/download",
            "C",
            "book_framework_only",
            "public_pdf_lead",
            "电力市场改革、市场设计和价格机制框架。",
        ),
        _source(
            "POWER_OFFICIAL_001",
            "utilities_electricity",
            "policy",
            "关于建立煤电容量电价机制的通知",
            "国家发展改革委 / 国家能源局",
            "https://www.ndrc.gov.cn/xxgk/zcfb/tz/202311/t20231110_1361897.html",
            "A",
            "pit_policy_anchor",
            "official_policy_reviewed",
            "煤电容量电价、固定成本回收比例和月度结算机制。",
        ),
        _source(
            "POWER_REPORT_001",
            "utilities_electricity",
            "industry_report",
            "2026 年电力行业分析",
            "联合资信",
            "https://www.lhratings.com/file/g28a8f1c695.pdf",
            "B",
            "report_context_and_metric_lead",
            "pdf_available_public",
            "用电需求、装机、利用小时、燃料成本和电价机制背景。",
        ),
        _source(
            "POWER_ARTICLE_001",
            "utilities_electricity",
            "official_media_article",
            "电力市场化改革向纵深推进 两部制电价加快煤电功能转型",
            "新华网",
            "https://www.news.cn/fortune/20240715/8f900ade01224066a61c248eeeb10f37/c.html",
            "B",
            "policy_explanation_context",
            "public_article_reviewed",
            "容量电价对煤电盈利稳定性和电力市场建设的解释材料。",
        ),
    ]


def _bank_book_cards() -> list[dict[str, Any]]:
    return [
        _book_card(
            "BANK_BOOK_CARD_001",
            "BANK_BOOK_001",
            "asset_liability_nim_engine",
            "银行盈利不是单纯高股息问题，而是资产端收益率、负债端成本、期限结构和风险定价共同形成的息差问题。V5c 应把净息差和存款成本作为银行 sleeve 状态解释的核心字段。",
            "NIM; loan_yield; deposit_cost; interest_earning_assets; funding_mix",
            "bank_nim_pressure_watch",
        ),
        _book_card(
            "BANK_BOOK_CARD_002",
            "BANK_BOOK_001",
            "credit_quality_buffer",
            "银行低估值必须同时核对不良率、关注类贷款、逾期贷款、拨备覆盖率和核销处置。低 PB 如果伴随资产质量恶化，不能被解释成安全边际。",
            "NPL_ratio; special_mention_ratio; overdue_ratio; provision_coverage; credit_cost",
            "bank_asset_quality_deterioration_watch",
        ),
        _book_card(
            "BANK_BOOK_CARD_003",
            "BANK_BOOK_001",
            "capital_and_dividend_constraint",
            "分红能力受核心一级资本、风险加权资产增速和监管资本要求约束。银行高股息应先通过资本缓冲和盈利留存审计，而不是只看股息率。",
            "CET1; tier1_capital_ratio; capital_adequacy_ratio; RWA_growth; payout_ratio",
            "bank_capital_buffer_weak_watch",
        ),
        _book_card(
            "BANK_BOOK_CARD_004",
            "BANK_BOOK_002",
            "safety_liquidity_profitability_tradeoff",
            "商业银行经营目标本身就是安全性、流动性、盈利性的平衡。V5c 观察标签应避免把短期 ROE 或股息率单独拔高为买入理由。",
            "ROE; ROA; liquidity_ratio; loan_to_deposit_ratio; dividend_yield",
            "bank_valuation_roe_mismatch_watch",
        ),
        _book_card(
            "BANK_BOOK_CARD_005",
            "BANK_BOOK_002",
            "regional_bank_difference",
            "区域银行的核心差异来自区域经济、存贷结构、客户集中度和资产质量。行业标签需要保留银行类型和区域分层，不能把大行、股份行、城商行、农商行混成一个风险状态。",
            "bank_type; region; loan_concentration; deposit_franchise; local_credit_state",
            "bank_credit_exposure_watch",
        ),
    ]


def _power_book_cards() -> list[dict[str, Any]]:
    return [
        _book_card(
            "POWER_BOOK_CARD_001",
            "POWER_BOOK_001",
            "energy_capacity_ancillary_revenue_split",
            "电力企业收益需要拆成电能量收入、容量补偿、辅助服务和政策补贴。火电在新能源渗透上升后更像支撑调节资产，不能只用发电量或静态 PE/PB 解释。",
            "energy_price; capacity_payment; ancillary_service_revenue; utilization_hours",
            "power_tariff_support_watch",
        ),
        _book_card(
            "POWER_BOOK_CARD_002",
            "POWER_BOOK_001",
            "thermal_power_fuel_spread",
            "火电盈利弹性主要受煤价、长协煤比例、上网电价、市场化电量和利用小时共同影响。V5c 应优先补煤价和电价状态，而不是继续泛化财务因子。",
            "coal_price; long_term_coal_contract_ratio; on_grid_tariff; utilization_hours",
            "power_fuel_cost_pressure_watch",
        ),
        _book_card(
            "POWER_BOOK_CARD_003",
            "POWER_BOOK_001",
            "capacity_payment_policy_state",
            "容量补偿和容量市场是稳定可靠容量收益的制度安排。电力 sleeve 的状态门应区分煤电容量价值上升与电量价格下行，避免误读单一收入项。",
            "capacity_payment_rate; eligible_capacity; monthly_settlement; compliance_penalty",
            "power_tariff_support_watch",
        ),
        _book_card(
            "POWER_BOOK_CARD_004",
            "POWER_BOOK_002",
            "market_design_and_price_signal",
            "现货、中长期、辅助服务和容量机制共同决定电力资产现金流。电力行业观察卡要记录政策生效日、区域市场进度和电源类型。",
            "spot_market_status; mid_long_term_contract_ratio; ancillary_service_market; province",
            "power_market_reform_watch",
        ),
        _book_card(
            "POWER_BOOK_CARD_005",
            "POWER_BOOK_002",
            "hydro_and_renewable_resource_state",
            "水电和新能源的产出受来水、风光资源、消纳和市场化电价影响。低波/红利逻辑必须与资源状态绑定，不能把水电、火电、核电、新能源混用同一解释。",
            "inflow; reservoir_level; wind_solar_resource; curtailment_rate; power_type",
            "hydro_water_stress_watch",
        ),
    ]


def _report_article_cards() -> list[dict[str, Any]]:
    return [
        _report_card(
            "BANK_REPORT_CARD_001",
            "BANK_OFFICIAL_001",
            "official_bank_regulatory_metric_anchor",
            "金融监管总局统计栏目是商业银行行业监管指标的首选官方锚。后续应按季度拉取净息差、不良率、拨备覆盖率、资本充足率等字段，并保留发布时间。",
            "official_quarterly_panel",
            "A",
        ),
        _report_card(
            "BANK_REPORT_CARD_002",
            "BANK_REPORT_001",
            "nim_low_level_and_profit_pressure",
            "联合资信 2026 年商业银行行业分析可作为行业背景线索：息差低位、资产质量和资本缓冲是银行高股息可持续性解释的关键。",
            "industry_report_context",
            "B",
        ),
        _report_card(
            "BANK_REPORT_CARD_003",
            "BANK_REPORT_002",
            "listed_bank_review_context",
            "上市银行报告可补充分类型银行的息差、资本和拨备变化，但要转成 V5c 面板时必须回到公告日和公司财报口径。",
            "report_context_only",
            "B",
        ),
        _report_card(
            "POWER_REPORT_CARD_001",
            "POWER_OFFICIAL_001",
            "coal_capacity_payment_policy_anchor",
            "发改价格〔2023〕1501号是煤电容量电价政策锚。它适合进入政策状态表，字段包括实施范围、固定成本标准、回收比例、月度结算和考核。",
            "official_policy_panel",
            "A",
        ),
        _report_card(
            "POWER_REPORT_CARD_002",
            "POWER_REPORT_001",
            "power_demand_utilization_fuel_state",
            "联合资信 2026 年电力行业分析提供用电需求、装机结构、利用小时、煤价和电价机制线索，可用于 P1 电力状态面板字段设计。",
            "industry_report_context",
            "B",
        ),
        _report_card(
            "POWER_REPORT_CARD_003",
            "POWER_ARTICLE_001",
            "capacity_payment_policy_explanation",
            "新华网解释材料可帮助 PM 理解容量电价为何改善煤电盈利稳定性，但只能作为政策解释，不能替代正式政策和公司级财务数据。",
            "policy_explanation_context",
            "B",
        ),
    ]


def _metric_extraction_map() -> list[dict[str, Any]]:
    rows = [
        ("bank", "BANK_REPORT_CARD_001", "net_interest_margin", "NFRA quarterly table", "bank_nim_pressure_watch", "quarterly", "industry_state_only"),
        ("bank", "BANK_REPORT_CARD_001", "NPL_ratio", "NFRA quarterly table and company annual/interim reports", "bank_asset_quality_deterioration_watch", "quarterly/semiannual", "industry_and_company_state"),
        ("bank", "BANK_REPORT_CARD_001", "provision_coverage", "NFRA quarterly table and company reports", "bank_asset_quality_deterioration_watch", "quarterly/semiannual", "industry_and_company_state"),
        ("bank", "BANK_BOOK_CARD_003", "CET1_tier1_capital_adequacy", "company reports with notice_date", "bank_capital_buffer_weak_watch", "semiannual/annual", "company_state"),
        ("bank", "BANK_BOOK_CARD_003", "payout_ratio_cash_dividend", "dividend plans and annual reports", "bank_dividend_sustainability_support", "annual", "company_state"),
        ("utilities_electricity", "POWER_REPORT_CARD_001", "capacity_payment_rate", "NDRC/provincial policy table with publish_date", "power_tariff_support_watch", "policy_event", "policy_state"),
        ("utilities_electricity", "POWER_BOOK_CARD_002", "coal_price_fuel_spread", "coal price index plus company fuel cost disclosure", "power_fuel_cost_pressure_watch", "daily/monthly/semiannual", "industry_and_company_state"),
        ("utilities_electricity", "POWER_REPORT_CARD_002", "utilization_hours_by_power_type", "NEA/CEC/company reports", "power_utilization_state", "monthly/annual", "industry_and_company_state"),
        ("utilities_electricity", "POWER_BOOK_CARD_005", "hydro_inflow_reservoir_state", "hydrology and company disclosures with visible_date", "hydro_water_stress_watch", "monthly/seasonal", "subindustry_state"),
        ("utilities_electricity", "POWER_BOOK_CARD_004", "spot_market_and_contract_state", "policy documents and provincial market notices", "power_market_reform_watch", "policy_event/monthly", "policy_state"),
    ]
    return [
        {
            "industry": industry,
            "card_id": card_id,
            "metric_name": metric,
            "preferred_source": source,
            "state_tag": tag,
            "frequency": frequency,
            "allowed_use": allowed_use,
            "pit_visible_date_required": True,
            "can_trigger_trade": False,
            "can_change_weight": False,
        }
        for industry, card_id, metric, source, tag, frequency, allowed_use in rows
    ]


def _pit_data_gate_queue() -> list[dict[str, Any]]:
    return [
        _queue("P1", "bank", "bank_nim_asset_quality_capital_panel", "Build PIT panel for NIM, NPL, special mention, provision coverage, CET1/tier1/CAR by report visible date.", "ready"),
        _queue("P1", "bank", "bank_dividend_sustainability_panel", "Link cash dividend, payout ratio, retained earnings and capital pressure; no threshold from book notes.", "ready"),
        _queue("P1", "utilities_electricity", "power_coal_tariff_capacity_panel", "Collect coal/fuel spread, capacity payment policy, marketized tariff and eligible capacity by visible date.", "ready"),
        _queue("P1", "utilities_electricity", "power_utilization_and_water_panel", "Collect utilization hours by power type, hydro inflow/reservoir and curtailment state.", "ready"),
        _queue("P2", "bank;utilities_electricity", "dedicated_pdf_original_review", "If FXBAOGAO key is available later, PDF-review bank and power report leads before promoting any B card.", "blocked_fx_api_key_missing"),
    ]


def _state_tag_upgrade_queue() -> list[dict[str, Any]]:
    return [
        {"rank": 1, "candidate_state_tag": "bank_nim_pressure_watch", "industry": "bank", "source_cards": "BANK_BOOK_CARD_001;BANK_REPORT_CARD_001", "next_step": "PIT panel only; no trade rule", "status": "ready_for_data_gate"},
        {"rank": 2, "candidate_state_tag": "bank_asset_quality_deterioration_watch", "industry": "bank", "source_cards": "BANK_BOOK_CARD_002;BANK_REPORT_CARD_001", "next_step": "PIT panel only; no trade rule", "status": "ready_for_data_gate"},
        {"rank": 3, "candidate_state_tag": "bank_capital_buffer_weak_watch", "industry": "bank", "source_cards": "BANK_BOOK_CARD_003", "next_step": "Company visible-date panel", "status": "ready_for_data_gate"},
        {"rank": 4, "candidate_state_tag": "power_fuel_cost_pressure_watch", "industry": "utilities_electricity", "source_cards": "POWER_BOOK_CARD_002;POWER_REPORT_CARD_002", "next_step": "Coal/fuel spread panel", "status": "ready_for_data_gate"},
        {"rank": 5, "candidate_state_tag": "power_tariff_support_watch", "industry": "utilities_electricity", "source_cards": "POWER_BOOK_CARD_001;POWER_BOOK_CARD_003;POWER_REPORT_CARD_001", "next_step": "Policy visible-date panel", "status": "ready_for_data_gate"},
        {"rank": 6, "candidate_state_tag": "hydro_water_stress_watch", "industry": "utilities_electricity", "source_cards": "POWER_BOOK_CARD_005", "next_step": "Hydrology/state source audit", "status": "ready_for_data_gate"},
    ]


def _blocked_actions() -> list[dict[str, Any]]:
    return [
        {"action": "use_book_card_as_numeric_threshold", "blocked": True, "reason": "Books provide framework language only."},
        {"action": "trade_or_reweight_from_industry_card", "blocked": True, "reason": "Current package is observation/data-gate only."},
        {"action": "promote_report_lead_without_pdf_review", "blocked": True, "reason": "B-grade reports require original review before evidence upgrade."},
        {"action": "change_v57f_or_v5f_core", "blocked": True, "reason": "Industry knowledge cannot modify repaired baseline or V5f primary."},
        {"action": "accepted_or_live_approved", "blocked": True, "reason": "No accepted/live status from knowledge collection."},
    ]


def _pm_gate_decision() -> list[dict[str, Any]]:
    return [
        {
            "pm_gate_decision": "admit_dedicated_bank_power_book_cards_to_v5c_observation_knowledge_base",
            "bank_status": "dedicated_framework_cards_ready_pit_panels_next",
            "power_status": "dedicated_framework_cards_ready_coal_tariff_water_panels_next",
            "reports_status": "public_report_and_policy_leads_registered_pdf_review_optional",
            "can_change_weights": False,
            "can_trigger_trade": False,
            "accepted": False,
            "next_action": "proceed_to_P1_bank_and_power_state_panels",
        }
    ]


def _next_queue() -> list[dict[str, Any]]:
    return [
        {"rank": 1, "next_task": "v5c_bank_p1_nim_asset_quality_capital_panel", "status": "ready", "detail": "Build PIT-visible bank company/industry state panel."},
        {"rank": 2, "next_task": "v5c_power_p1_coal_tariff_hydro_state_panel", "status": "ready", "detail": "Build PIT-visible power state panel beyond demand."},
        {"rank": 3, "next_task": "attach_bank_power_industry_tags_to_v5f_forward_tracking", "status": "ready_after_P1", "detail": "Observation tags only; no V5f primary change."},
        {"rank": 4, "next_task": "fxbaogao_bank_power_pdf_review_refresh", "status": "blocked_until_api_key", "detail": "FXBAOGAO_API_KEY missing in current shell."},
    ]


def _source(
    source_id: str,
    industry: str,
    source_type: str,
    source_title: str,
    author_or_institution: str,
    source_link: str,
    evidence_grade: str,
    allowed_use: str,
    review_status: str,
    note: str,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "industry": industry,
        "source_type": source_type,
        "source_title": source_title,
        "author_or_institution": author_or_institution,
        "source_link_or_location": source_link,
        "evidence_grade": evidence_grade,
        "allowed_use": allowed_use,
        "review_status": review_status,
        "note": note,
    }


def _book_card(card_id: str, source_id: str, theme: str, note: str, metrics: str, state_tag: str) -> dict[str, Any]:
    return {
        "card_id": card_id,
        "source_id": source_id,
        "theme": theme,
        "paraphrased_note": note,
        "candidate_metrics": metrics,
        "candidate_state_tag": state_tag,
        "evidence_layer": "book_framework",
        "evidence_grade": "C",
        "pit_safety": "not_pit_fact",
        "allowed_use": "industry explanation; PM review; data-gate design",
        "blocked_use": "numeric threshold; trade trigger; accepted status",
        "can_trigger_trade": False,
        "can_change_weight": False,
        "review_status": "paraphrased_catalog_framework_card",
    }


def _report_card(card_id: str, source_id: str, theme: str, note: str, use: str, grade: str) -> dict[str, Any]:
    return {
        "card_id": card_id,
        "source_id": source_id,
        "theme": theme,
        "paraphrased_note": note,
        "allowed_use": use,
        "evidence_grade": grade,
        "requires_visible_date": True,
        "requires_pdf_or_original_review_before_quant": grade != "A",
        "can_trigger_trade": False,
        "can_change_weight": False,
        "review_status": "registered_source_card",
    }


def _queue(priority: str, industry: str, task: str, detail: str, status: str) -> dict[str, Any]:
    return {"priority": priority, "industry": industry, "task": task, "detail": detail, "status": status}


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    path.write_text(
        f"""# V5c Bank + Power Dedicated Book / Report Card Collection

## Decision

Dedicated bank and power industry book/report cards are admitted to the V5c knowledge base as observation and data-gate material only.

## What Changed

- Closed the P0 gap for dedicated bank industry-analysis framework cards.
- Closed the P0 gap for dedicated power/electric-utility industry-analysis framework cards.
- Registered official/policy/report sources for PIT state-panel follow-up.
- Mirrored all outputs into `{summary['knowledge_base_path']}`.

## Bank Focus

Bank cards now separate NIM pressure, credit quality, capital/dividend constraints, valuation-quality mismatch and regional-bank differentiation.

## Power Focus

Power cards now separate energy/capacity/ancillary revenue, coal/fuel spread, capacity-payment policy, market-design state and hydro/renewable resource state.

## Boundary

This package cannot change weights, trigger trades, set thresholds, mark accepted or approve live trading.

## PM Gate

`{summary['pm_gate_decision']}`
""",
        encoding="utf-8",
    )


def _write_rules(path: Path) -> None:
    path.write_text(
        """# V5c Bank + Power Dedicated Card Execution Rules

- Use book cards as industry-analysis frameworks only.
- Use official/report cards as source leads or PIT anchors only.
- Do not convert any book sentence into a numeric threshold.
- Do not trigger trades, modify V57f/V5f weights, or change the repaired baseline.
- Require visible dates for any metric before it enters a state panel.
- Require original/PDF review before B-grade report leads become stronger evidence.
- Keep bank and power state tags observation-only until a separate Quant spec and forward validation approve otherwise.
- Do not mark accepted or live approved.
""",
        encoding="utf-8",
    )


def _write_index(path: Path, summary: dict[str, Any]) -> None:
    path.write_text(
        f"""# V5c Bank + Power Dedicated Cards

Status: `{summary['status']}`

Gate: `{summary['pm_gate_decision']}`

Role: `{summary['v5c_role']}`

Primary files:
- `v5c_bank_industry_book_cards.csv`
- `v5c_power_industry_book_cards.csv`
- `v5c_bank_power_report_article_cards.csv`
- `v5c_bank_power_metric_extraction_map.csv`
- `v5c_bank_power_pit_data_gate_queue.csv`

This knowledge-base folder is observation-only and cannot change trades.
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
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    run()

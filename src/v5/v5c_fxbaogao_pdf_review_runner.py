from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import fitz

from v5.io_utils import read_csv_rows, write_csv_rows


AB_CARD_SPECS = [
    {
        "card_id": "V5C_FX_AB_001",
        "report_id": "5281979",
        "source_grade": "A",
        "page_num": "3",
        "topic": "rebalancing",
        "key_claim": "ETF-based multi-asset allocation is framed as a way to diversify risk sources and smooth the portfolio path.",
        "evidence": "The report states that adding low-correlation assets such as equity, bonds, commodities, gold and REITs can reduce single-market systematic risk and maximum drawdown, and presents ETFs as transparent, low-cost implementation tools.",
        "applicable_to_v5c": "yes",
        "pit_safety": "safe_as_research_framework_only",
        "can_be_quant_hypothesis": "yes",
        "limitation": "Multi-asset ETF framework is not a direct V57f stock-sleeve rule and cannot set V5c parameters by itself.",
        "next_required_data": "PIT daily ETF or sleeve returns, sleeve correlations, rebalance calendar, transaction cost and cash proxy rules.",
    },
    {
        "card_id": "V5C_FX_AB_002",
        "report_id": "5281979",
        "source_grade": "A",
        "page_num": "6,8",
        "topic": "risk_budget",
        "key_claim": "Low-risk portfolio construction can use risk budget as the base, with momentum only adjusting budget rather than replacing risk control.",
        "evidence": "The report separates low-risk and high-risk objectives, uses risk budget as the base for low-risk portfolios, and explains risk parity as allocating by risk contribution rather than capital weight.",
        "applicable_to_v5c": "yes",
        "pit_safety": "needs_check_for_future_signals",
        "can_be_quant_hypothesis": "yes",
        "limitation": "The report's target-volatility and momentum settings are source-specific and cannot be copied as V5c thresholds.",
        "next_required_data": "V57f realized volatility, sleeve risk contribution, PIT momentum inputs if PM opens a later quant stage.",
    },
    {
        "card_id": "V5C_FX_AB_003",
        "report_id": "5281979",
        "source_grade": "A",
        "page_num": "10,12",
        "topic": "cash_management",
        "key_claim": "Pure cash can create long-term cash drag when volatility targeting reduces equity exposure.",
        "evidence": "The report uses short-duration bond ETF exposure as a cash substitute because leaving a large cash position idle during risk reduction can materially hurt compounding.",
        "applicable_to_v5c": "yes",
        "pit_safety": "needs_check_for_cash_proxy",
        "can_be_quant_hypothesis": "yes",
        "limitation": "Cash substitute selection requires a separate V5c policy; V57f itself must not be changed in this knowledge stage.",
        "next_required_data": "Cash yield assumptions, short-term bond proxy PIT prices, transaction costs, liquidity and drawdown behavior.",
    },
    {
        "card_id": "V5C_FX_AB_004",
        "report_id": "5346188",
        "source_grade": "A",
        "page_num": "1,6,7",
        "topic": "defense",
        "key_claim": "A two-stage overlay can combine portfolio insurance with risk budgeting, using risk features rather than return forecasts.",
        "evidence": "The report proposes CPPI-style portfolio insurance for each risk asset, then allocates across sub-portfolios by risk budget, with downside control at the sub-portfolio and aggregate levels.",
        "applicable_to_v5c": "yes",
        "pit_safety": "needs_check_for_future_signals",
        "can_be_quant_hypothesis": "yes",
        "limitation": "CPPI-like mechanics can increase complexity and must not become a multi-parameter historical fit.",
        "next_required_data": "V57f floor policy candidates, risk multiplier governance, cash proxy, daily portfolio value and drawdown state.",
    },
    {
        "card_id": "V5C_FX_AB_005",
        "report_id": "5138693",
        "source_grade": "A",
        "page_num": "8,9,10",
        "topic": "volatility",
        "key_claim": "Volatility clustering can justify a discrete defensive state instead of continuous timing.",
        "evidence": "The report identifies factor-volatility clustering and uses a short-versus-medium volatility spread to switch between a tighter ETF-like mode and a looser active-risk mode.",
        "applicable_to_v5c": "maybe",
        "pit_safety": "needs_check_for_factor_or_portfolio_volatility",
        "can_be_quant_hypothesis": "yes",
        "limitation": "The evidence comes from index-enhancement risk control, not a dividend-low-vol ETF candidate; V5c should translate it cautiously to portfolio-level volatility states.",
        "next_required_data": "PIT V57f portfolio realized volatility, core sleeve volatility, market breadth/concentration proxy if used.",
    },
    {
        "card_id": "V5C_FX_AB_006",
        "report_id": "5138693",
        "source_grade": "A",
        "page_num": "12,13,14",
        "topic": "defense",
        "key_claim": "Dynamic defensive switching can reduce drawdown but raises turnover, so execution cost must be part of the evidence contract.",
        "evidence": "The report reports lower maximum excess drawdown for the dynamic risk-control portfolio, while also showing materially higher turnover and listing model failure risks.",
        "applicable_to_v5c": "yes",
        "pit_safety": "needs_check_for_future_signals",
        "can_be_quant_hypothesis": "yes",
        "limitation": "Cannot use the report's historical performance as V5c parameter proof; cost and order-health must be tested later.",
        "next_required_data": "V57f turnover impact, tax/fee assumptions, rebalance-order health, cash/holding logs.",
    },
    {
        "card_id": "V5C_FX_AB_007",
        "report_id": "5272355",
        "source_grade": "A",
        "page_num": "1",
        "topic": "volatility",
        "key_claim": "High-volatility holdings can be managed with tighter active-weight deviation while lower-volatility holdings receive more flexibility.",
        "evidence": "The report's core view is that residual-volatility buckets can be used to tighten overweight and underweight constraints for high-volatility stocks while allowing more room for low-volatility stocks.",
        "applicable_to_v5c": "maybe",
        "pit_safety": "needs_check_for_holdings_state",
        "can_be_quant_hypothesis": "yes",
        "limitation": "The report is about index-enhancement excess-risk management; V5c can use it only as a sleeve risk-budget hypothesis, not as a stock-selection change.",
        "next_required_data": "Daily stock/sleeve volatility, current holdings weights, target weights, drift limits and rebalance dates.",
    },
    {
        "card_id": "V5C_FX_AB_008",
        "report_id": "5512765",
        "source_grade": "A",
        "page_num": "1,2,3",
        "topic": "dividend_low_vol_risk",
        "key_claim": "Dividend strategy evidence needs the actual dividend process and observable announcement dates.",
        "evidence": "The report lays out the cash-dividend workflow from proposal and shareholder approval to implementation announcement, record date and ex-dividend date, and discusses expected dividend yield versus realized dividend yield.",
        "applicable_to_v5c": "yes",
        "pit_safety": "safe_as_data_requirement",
        "can_be_quant_hypothesis": "yes",
        "limitation": "This supports PIT dividend-state requirements, not a direct profit-taking parameter.",
        "next_required_data": "Dividend proposal date, shareholder approval date, implementation announcement date, record date, ex-dividend date and cash dividend amount.",
    },
    {
        "card_id": "V5C_FX_AB_009",
        "report_id": "5512765",
        "source_grade": "A",
        "page_num": "7,10",
        "topic": "dividend_low_vol_risk",
        "key_claim": "Volatility-adjusted dividend signals can be a dividend-risk control idea, but must remain separate from V57f core factors.",
        "evidence": "The report compares dividend index construction details and discusses volatility-adjusted dividend ranking as part of high-dividend index design.",
        "applicable_to_v5c": "yes",
        "pit_safety": "needs_check_for_index_rule_dates",
        "can_be_quant_hypothesis": "maybe",
        "limitation": "Index construction evidence does not authorize changing V57f factors or sleeve weights.",
        "next_required_data": "Historical index methodology dates, PIT dividend estimates, realized volatility and rebalance-calendar alignment.",
    },
    {
        "card_id": "V5C_FX_AB_010",
        "report_id": "5066564",
        "source_grade": "B",
        "page_num": "3,4",
        "topic": "dividend_low_vol_risk",
        "key_claim": "Free cash flow can explain dividend capacity, while red-low-vol rules emphasize dividend continuity and volatility control.",
        "evidence": "The report compares free-cash-flow and red-low-vol index logic, noting that free cash flow is an upstream source of dividends while red-low-vol uses continuous dividend and low-volatility filters.",
        "applicable_to_v5c": "yes",
        "pit_safety": "needs_check_for_financial_statement_lag",
        "can_be_quant_hypothesis": "yes",
        "limitation": "Source is useful for research framing, but the report's optimized stock-count and rebalance choices must not be copied.",
        "next_required_data": "PIT FCF, OCF, dividend continuity, expected dividend yield, volatility and announcement-date contracts.",
    },
    {
        "card_id": "V5C_FX_AB_011",
        "report_id": "5066564",
        "source_grade": "B",
        "page_num": "5,6,7",
        "topic": "risk_budget",
        "key_claim": "Free-cash-flow weighting can create concentration risk, while fewer high-yield holdings can raise drawdown risk.",
        "evidence": "The report notes higher top-10 concentration for the free-cash-flow index and shows that concentrated FCF or dividend portfolios may have large maximum drawdowns.",
        "applicable_to_v5c": "yes",
        "pit_safety": "needs_check_for_weight_and_concentration",
        "can_be_quant_hypothesis": "yes",
        "limitation": "This is a risk warning for V5c, not a mandate to chase high-return concentrated variants.",
        "next_required_data": "V57f sleeve concentration, single-name caps, sector caps, drawdown contribution and liquidity constraints.",
    },
    {
        "card_id": "V5C_FX_AB_012",
        "report_id": "5058677",
        "source_grade": "B",
        "page_num": "15,16,17,18,19",
        "topic": "dividend_low_vol_risk",
        "key_claim": "High dividend is not automatically low risk; low volatility, earnings quality and rate regime can affect whether the style remains defensive.",
        "evidence": "The report builds high-dividend enhancement dimensions including stable earnings, growth, short duration and low volatility, and maps different dimensions to domestic interest-rate stages.",
        "applicable_to_v5c": "yes",
        "pit_safety": "needs_check_for_macro_state_publication",
        "can_be_quant_hypothesis": "maybe",
        "limitation": "Rate-regime framing is a research prior only; V5c must not tune thresholds to 2021-2026 history.",
        "next_required_data": "PIT 10Y yield, earnings-quality disclosures, dividend sustainability and low-volatility measures.",
    },
    {
        "card_id": "V5C_FX_AB_013",
        "report_id": "5193364",
        "source_grade": "B",
        "page_num": "2,4",
        "topic": "dividend_low_vol_risk",
        "key_claim": "Dividend sleeves may shift among stable, cyclical and quality dividend assets under different rate-liquidity states.",
        "evidence": "The report classifies dividend assets into stable dividend, cyclical dividend, quality dividend and resource dividend groups, and links rate/liquidity conditions to the relative appeal of these groups.",
        "applicable_to_v5c": "yes",
        "pit_safety": "needs_check_for_state_variables",
        "can_be_quant_hypothesis": "maybe",
        "limitation": "This is a qualitative state map; it cannot be used to add new sleeves or rewrite V57f core.",
        "next_required_data": "PIT rate, liquidity proxy, dividend group exposure and sleeve attribution.",
    },
    {
        "card_id": "V5C_FX_AB_014",
        "report_id": "5027124",
        "source_grade": "B",
        "page_num": "9,10,11,12",
        "topic": "dividend_low_vol_risk",
        "key_claim": "Dividend-low-vol index construction combines dividend continuity, payout constraints, expected dividend yield and volatility filters.",
        "evidence": "The report summarizes the A500 dividend-low-volatility index rules and compares volatility, drawdown and industry distribution against broad and dividend indexes.",
        "applicable_to_v5c": "yes",
        "pit_safety": "needs_check_for_index_methodology_dates",
        "can_be_quant_hypothesis": "maybe",
        "limitation": "ETF/product-specific investment-value material is B-grade and cannot be treated as an accepted V5c rule.",
        "next_required_data": "Historical index rule effective dates, dividend estimates, volatility windows and industry caps.",
    },
    {
        "card_id": "V5C_FX_AB_015",
        "report_id": "4974230",
        "source_grade": "B",
        "page_num": "10,14,15,16",
        "topic": "risk_budget",
        "key_claim": "Risk-budget ETF allocation depends on asset correlation and should carry an explicit model-failure warning.",
        "evidence": "The report presents macro risk parity and ETF asset allocation examples, showing selected ETF asset classes, correlations, risk metrics and explicit model-failure / theme-volatility risk warnings.",
        "applicable_to_v5c": "yes",
        "pit_safety": "needs_check_for_future_signals",
        "can_be_quant_hypothesis": "yes",
        "limitation": "The report is slide-like and should support governance requirements, not parameter transfer.",
        "next_required_data": "PIT correlation windows, sleeve return histories, model-failure audit and concentration risk monitor.",
    },
]


ACCEPTED_REPORT_IDS = {card["report_id"] for card in AB_CARD_SPECS}

REJECTION_OVERRIDES = {
    "5011349": "new_fund_issuance_material_not_allowed_for_ab_cards",
    "5097800": "weekly_macro_focus_not_v5c_overlay_method",
    "5127120": "fund_product_analysis_marketing_or_product_specific",
    "5154569": "market_observation_not_pdf_method_evidence",
    "5195591": "ai_image_timing_model_not_v5c_overlay_framework",
    "5195593": "ai_image_timing_model_not_v5c_overlay_framework",
    "5198160": "fund_flow_and_etf_recommendation_not_ab_evidence",
    "5203196": "industry_chain_short_update_not_v5c_overlay",
    "5203254": "fund_live_stream_or_marketing_transcript_not_ab_evidence",
    "5209020": "fund_live_stream_or_marketing_transcript_not_ab_evidence",
    "5216641": "monthly_strategy_noise",
    "5270199": "current_holdings_rebalance_observation_not_method_evidence",
    "5270252": "single_industry_high_dividend_strategy_not_overlay_method",
    "5302061": "single_industry_strategy_not_v5c_overlay",
    "5324456": "ai_image_timing_model_not_v5c_overlay_framework",
    "5324624": "macro_quarterly_outlook_not_v5c_overlay_method",
    "5337289": "ai_image_timing_model_not_v5c_overlay_framework",
    "5401933": "market_strategy_or_hk_high_dividend_not_v57f_overlay",
    "5406049": "insurer_holdings_study_not_v5c_overlay_method",
    "5428610": "single_industry_high_dividend_strategy_not_overlay_method",
    "5441838": "manager_profile_or_product_promotion_not_ab_evidence",
    "5477573": "leveraged_etf_market_microstructure_not_v57f_overlay",
    "5479745": "weekly_fund_flow_noise",
    "5481160": "single_industry_half_year_strategy_not_overlay_method",
    "5502069": "short_timing_model_commentary_not_ab_evidence",
    "5516384": "monthly_fund_flow_noise",
    "5544913": "ai_image_timing_model_not_v5c_overlay_framework",
    "5545741": "short_market_commentary_not_ab_evidence",
}

HYPOTHESIS_UPDATES = [
    {
        "hypothesis_id": "V5C_PDF_H01",
        "overlay_type": "risk_budget",
        "rule_description": "Study a portfolio-level risk-budget overlay for V57f using realized sleeve risk contribution and no change to stock selection.",
        "supporting_cards": "V5C_FX_AB_001;V5C_FX_AB_002;V5C_FX_AB_015",
        "economic_intuition": "Risk should be diversified by contribution rather than capital weight, especially when sleeves have different volatility.",
        "required_data": "PIT daily V57f sleeve returns, covariance/correlation windows, target weights, turnover and cost logs.",
        "pit_requirement": "All volatility/correlation inputs must be observable before the rebalance date.",
        "allowed_next_stage": "research_design_only",
        "blocked_actions": "no_backtest;no_threshold_tuning;no_v57f_core_change",
    },
    {
        "hypothesis_id": "V5C_PDF_H02",
        "overlay_type": "defense",
        "rule_description": "Study a CPPI-like portfolio-insurance concept for V57f drawdown defense with explicit floor and cash-proxy governance.",
        "supporting_cards": "V5C_FX_AB_003;V5C_FX_AB_004",
        "economic_intuition": "Portfolio insurance can preserve downside budget while retaining partial upside participation.",
        "required_data": "Daily portfolio NAV, drawdown state, floor policy, cash or short-duration proxy return series, execution cost.",
        "pit_requirement": "Portfolio NAV and cash proxy data must be known as of decision time.",
        "allowed_next_stage": "research_design_only",
        "blocked_actions": "no_cppi_parameter_copy;no_backtest;no_joinquant",
    },
    {
        "hypothesis_id": "V5C_PDF_H03",
        "overlay_type": "volatility",
        "rule_description": "Study a discrete volatility-regime switch that reduces active risk when portfolio or sleeve volatility is rising.",
        "supporting_cards": "V5C_FX_AB_005;V5C_FX_AB_006;V5C_FX_AB_007",
        "economic_intuition": "Volatility clustering means recent volatility deterioration may persist, so discrete risk tightening can reduce drawdown without continuous market timing.",
        "required_data": "PIT realized volatility, sleeve volatility, holdings weights, risk contribution and transaction costs.",
        "pit_requirement": "Volatility state must be computed from historical daily data only.",
        "allowed_next_stage": "research_design_only",
        "blocked_actions": "no_barra_dependency_without_data_contract;no_minute_timing;no_parameter_optimization",
    },
    {
        "hypothesis_id": "V5C_PDF_H04",
        "overlay_type": "dividend_safety",
        "rule_description": "Study a dividend-safety guard using dividend proposal, approval, implementation, record and ex-dividend dates.",
        "supporting_cards": "V5C_FX_AB_008;V5C_FX_AB_009;V5C_FX_AB_014",
        "economic_intuition": "Dividend strategies need a clean distinction between expected dividend yield, declared dividend and realized dividend cash flow.",
        "required_data": "Dividend proposal dates, approval dates, implementation announcements, record/ex-dividend dates, realized cash dividends.",
        "pit_requirement": "Only use dividend facts after their public announcement date.",
        "allowed_next_stage": "research_design_only",
        "blocked_actions": "no_future_dividend;no_current_index_holdings_backfill;no_core_factor_change",
    },
    {
        "hypothesis_id": "V5C_PDF_H05",
        "overlay_type": "cashflow_quality",
        "rule_description": "Study free-cash-flow and OCF deterioration as a risk-budget reducer, not as a new return-chasing selector.",
        "supporting_cards": "V5C_FX_AB_010;V5C_FX_AB_011",
        "economic_intuition": "Free cash flow supports future dividends, but FCF weighting can create concentration and drawdown risk.",
        "required_data": "PIT OCF, FCF, enterprise value, dividend continuity, concentration and sector exposure.",
        "pit_requirement": "Financial fields must use report announcement-date visibility and lag rules.",
        "allowed_next_stage": "research_design_only",
        "blocked_actions": "no_fcf_return_optimization;no_small_concentrated_portfolio_copy",
    },
    {
        "hypothesis_id": "V5C_PDF_H06",
        "overlay_type": "macro_state",
        "rule_description": "Study rate/liquidity state as a qualitative risk context for dividend sleeves, not as a direct timing trigger.",
        "supporting_cards": "V5C_FX_AB_012;V5C_FX_AB_013",
        "economic_intuition": "High-dividend assets can behave differently across rate and liquidity states, and pure high dividend may fail without low-volatility or earnings-quality support.",
        "required_data": "PIT 10Y yield, liquidity proxy, sleeve group exposures, earnings quality and dividend sustainability.",
        "pit_requirement": "Macro state must be based on historical publicly available data only.",
        "allowed_next_stage": "research_design_only",
        "blocked_actions": "no_macro_prediction_model;no_threshold_tuning;no_new_sleeve_promotion",
    },
]


def run_v5c_fxbaogao_pdf_review(root: Path) -> dict[str, Any]:
    knowledge_dir = root / "knowledge" / "research_agent" / "v5c_defense_profit_taking"
    seed_rows = read_csv_rows(knowledge_dir / "seed_report_paragraph_pdf_results.csv")
    pdf_leads = [row for row in seed_rows if row.get("pdf_path") and Path(row["pdf_path"]).exists()]
    unique_reports = _unique_by_report_id(pdf_leads)

    plan_rows = _build_plan_rows(pdf_leads)
    result_rows, rejected_rows = _build_review_results(unique_reports)
    card_rows = _build_card_rows(unique_reports)

    write_csv_rows(knowledge_dir / "14_pdf_review_plan.csv", plan_rows[0].keys(), plan_rows, encoding="utf-8-sig")
    write_csv_rows(knowledge_dir / "15_pdf_review_results.csv", result_rows[0].keys(), result_rows, encoding="utf-8-sig")
    write_csv_rows(knowledge_dir / "16_ab_evidence_cards.csv", card_rows[0].keys(), card_rows, encoding="utf-8-sig")
    write_csv_rows(knowledge_dir / "17_rejected_pdf_sources.csv", rejected_rows[0].keys(), rejected_rows, encoding="utf-8-sig")
    write_csv_rows(
        knowledge_dir / "18_v5c_overlay_hypothesis_update.csv",
        HYPOTHESIS_UPDATES[0].keys(),
        HYPOTHESIS_UPDATES,
        encoding="utf-8-sig",
    )

    summary = {
        "reviewed_pdf_lead_rows": len(pdf_leads),
        "reviewed_unique_pdf_reports": len(unique_reports),
        "ab_evidence_card_count": len(card_rows),
        "accepted_report_count": len(ACCEPTED_REPORT_IDS),
        "rejected_report_count": len(rejected_rows),
        "hypothesis_update_count": len(HYPOTHESIS_UPDATES),
        "v57f_modified": False,
        "backtest_started": False,
        "joinquant_started": False,
        "parameter_tuning_started": False,
        "blocking_status": "no_blocker",
        "note": "PDF source leads were reviewed conservatively; accepted cards remain research evidence only.",
    }
    _write_summary_report(knowledge_dir, summary)
    _update_knowledge_summary(knowledge_dir, summary)
    return summary


def _unique_by_report_id(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        report_id = row.get("report_id", "")
        if report_id in seen:
            continue
        seen.add(report_id)
        output.append(row)
    return output


def _build_plan_rows(pdf_leads: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for index, row in enumerate(pdf_leads, 1):
        rows.append(
            {
                "review_order": index,
                "report_id": row.get("report_id", ""),
                "seed_keyword": row.get("seed_keyword", ""),
                "title": row.get("title", ""),
                "institution": row.get("org_name", ""),
                "publish_date": _clean_date(row.get("pub_time_str", "")),
                "pdf_path": row.get("pdf_path", ""),
                "review_method": "PyMuPDF text extraction plus page-level original review",
                "review_gate": "PDF_original_checked_before_A_B_card",
                "duplicate_policy": "dedupe_by_report_id_for_final_decision",
                "allowed_output": "A_B_card_or_rejected_source",
            }
        )
    return rows


def _build_review_results(unique_reports: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    result_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    for row in unique_reports:
        report_id = row.get("report_id", "")
        pdf_path = row.get("pdf_path", "")
        pdf_status, page_count = _inspect_pdf(pdf_path)
        accepted = report_id in ACCEPTED_REPORT_IDS and pdf_status == "readable"
        decision = "accepted_ab_evidence" if accepted else "rejected"
        reason = "accepted_as_pdf_checked_method_or_framework_evidence" if accepted else REJECTION_OVERRIDES.get(
            report_id, "not_relevant_or_insufficient_for_v5c_ab_evidence"
        )
        grade = _grade_for_report(report_id) if accepted else ""
        matched_cards = ";".join(card["card_id"] for card in AB_CARD_SPECS if card["report_id"] == report_id)
        result = {
            "report_id": report_id,
            "decision": decision,
            "source_grade": grade,
            "title": row.get("title", ""),
            "institution": row.get("org_name", ""),
            "publish_date": _clean_date(row.get("pub_time_str", "")),
            "pdf_path": pdf_path,
            "pdf_status": pdf_status,
            "page_count": page_count,
            "matched_card_ids": matched_cards,
            "reason": reason,
            "evidence_card_allowed": "yes" if accepted else "no",
            "blocked_actions": "no_backtest;no_parameter_tuning;no_v57f_change;no_joinquant",
        }
        result_rows.append(result)
        if not accepted:
            rejected_rows.append(
                {
                    "report_id": report_id,
                    "title": row.get("title", ""),
                    "institution": row.get("org_name", ""),
                    "publish_date": _clean_date(row.get("pub_time_str", "")),
                    "pdf_path": pdf_path,
                    "pdf_status": pdf_status,
                    "page_count": page_count,
                    "rejection_reason": reason,
                    "reuse_policy": "source_lead_archive_only",
                }
            )
    return result_rows, rejected_rows


def _build_card_rows(unique_reports: list[dict[str, str]]) -> list[dict[str, Any]]:
    by_report = {row.get("report_id", ""): row for row in unique_reports}
    rows = []
    for spec in AB_CARD_SPECS:
        source = by_report[spec["report_id"]]
        rows.append(
            {
                "card_id": spec["card_id"],
                "report_id": spec["report_id"],
                "source_grade": spec["source_grade"],
                "title": source.get("title", ""),
                "institution": source.get("org_name", ""),
                "publish_date": _clean_date(source.get("pub_time_str", "")),
                "pdf_path": source.get("pdf_path", ""),
                "page_num": spec["page_num"],
                "topic": spec["topic"],
                "key_claim": spec["key_claim"],
                "evidence": spec["evidence"],
                "applicable_to_v5c": spec["applicable_to_v5c"],
                "pit_safety": spec["pit_safety"],
                "can_be_quant_hypothesis": spec["can_be_quant_hypothesis"],
                "limitation": spec["limitation"],
                "next_required_data": spec["next_required_data"],
            }
        )
    return rows


def _inspect_pdf(pdf_path: str) -> tuple[str, int | str]:
    path = Path(pdf_path)
    if not path.exists():
        return "missing", ""
    try:
        with fitz.open(path) as doc:
            return "readable", len(doc)
    except Exception as exc:
        return f"unreadable:{type(exc).__name__}", ""


def _grade_for_report(report_id: str) -> str:
    grades = {card["report_id"]: card["source_grade"] for card in AB_CARD_SPECS}
    return grades.get(report_id, "")


def _clean_date(value: str) -> str:
    return str(value or "").strip().strip("/")


def _write_summary_report(knowledge_dir: Path, summary: dict[str, Any]) -> None:
    report = f"""# V5c fxbaogao PDF Review Summary

As of 2026-07-26.

## Scope

This review checked fxbaogao PDF source leads for V5c defense / profit-taking / rebalancing overlay research. It did not modify V57f, did not run backtests, did not tune parameters, and did not start JoinQuant.

The required `knowledge/research_agent/v5c_defense_profit_taking/fxbaogao_report_source.md` path was not present. The equivalent governance file `knowledge/research_agent/references/fxbaogao_report_source.md` was used.

## Results

- Reviewed PDF lead rows: {summary["reviewed_pdf_lead_rows"]}
- Reviewed unique PDF reports: {summary["reviewed_unique_pdf_reports"]}
- Accepted reports: {summary["accepted_report_count"]}
- A/B evidence cards: {summary["ab_evidence_card_count"]}
- Rejected PDF sources: {summary["rejected_report_count"]}
- Hypothesis updates: {summary["hypothesis_update_count"]}
- Blocking status: `{summary["blocking_status"]}`

## Accepted Evidence Themes

- Risk budget and risk parity for ETF / sleeve allocation.
- CPPI-like portfolio insurance and cash-management implications.
- Volatility-regime defense and turnover-cost warning.
- Dividend-low-volatility index construction and dividend PIT date requirements.
- Free-cash-flow versus red-low-vol risk and concentration warnings.
- Rate / liquidity state as research context for dividend assets.

## Rejection Policy

Rejected sources include fund live-stream or marketing transcripts, new-fund issuance material, weekly/monthly flow notes, short market commentary, single-industry high-dividend strategy pieces, current holdings observations, and AI-image timing models that do not fit the V5c overlay scope.

## Governance

All accepted cards are research evidence only. They do not authorize V57f core changes, threshold tuning, JoinQuant execution, or historical optimization.
"""
    (knowledge_dir / "19_pdf_review_summary.md").write_text(report, encoding="utf-8")


def _update_knowledge_summary(knowledge_dir: Path, pdf_summary: dict[str, Any]) -> None:
    summary_path = knowledge_dir / "v5c_knowledge_base_summary.json"
    payload = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    payload["source_status"]["fxbaogao"] = "pdf_original_review_completed_ab_cards_created_research_only"
    for name in [
        "14_pdf_review_plan.csv",
        "15_pdf_review_results.csv",
        "16_ab_evidence_cards.csv",
        "17_rejected_pdf_sources.csv",
        "18_v5c_overlay_hypothesis_update.csv",
        "19_pdf_review_summary.md",
    ]:
        if name not in payload["file_outputs"]:
            payload["file_outputs"].append(name)
    payload["fxbaogao_pdf_review_status"] = pdf_summary
    payload["pm_decision"] = (
        "V5c may proceed to Research Agent hypothesis refinement using PDF-checked A/B cards, "
        "but Quant validation remains blocked until a separate V5c quant stage is opened."
    )
    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    result = run_v5c_fxbaogao_pdf_review(Path.cwd())
    print(json.dumps(result, ensure_ascii=False, indent=2))

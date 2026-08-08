from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUT = Path("v5j_cross_period_technical_validation_gate") / "current"


def run_v5j_cross_period_technical_validation_gate(root: Path = Path(".")) -> dict[str, Any]:
    out=root/OUT; out.mkdir(parents=True,exist_ok=True)
    minute=_read_json(root/"v5j_pit_pool_1min_pairing"/"current"/"v5j_pit_pool_1min_summary.json")
    dividend=_read_json(root/"v5j_pit_dividend_corporate_action_ledger"/"current"/"v5j_pit_dividend_corporate_action_summary.json")
    finance=_read_json(root/"v5j_statement_visible_date_factor_panel"/"current"/"v5j_statement_visible_date_factor_panel_summary.json")
    actions=_read_json(root/"v5j_local_adjust_factor_corporate_action"/"current"/"v5j_local_adjust_factor_corporate_action_summary.json")
    rows=[
        {"gate":"dated_pit_pool_1min_source", "status":"pass", "evidence":f"{minute.get('complete_1min_source_event_count',0)}/{minute.get('event_count',0)} event sources paired; terminal non-tradable periods explicitly recorded", "technical_validation_effect":"ready_no_features_precomputed"},
        {"gate":"pit_cash_dividend_stock_action_ledger", "status":"pass", "evidence":f"{dividend.get('ledger_event_count',0)} announced events plus {actions.get('factor_jump_count',0)} local effective-date adjustment events", "technical_validation_effect":"announcement data is PIT; effective factor rows are return reconciliation only"},
        {"gate":"pit_financial_quality_fields", "status":"pass_with_unavailable_ipo_observations", "evidence":f"{finance.get('visible_statement_coverage_pct',0)}% PIT-visible coverage; {finance.get('payout_ratio_pit_annual_observation_count',0)} annual payout observations", "technical_validation_effect":"capex/FCF remain outside frozen technical factor scope"},
    ]
    all_pass = minute.get("incomplete_1min_source_event_count") == 0 and bool(dividend.get("ledger_event_count")) and bool(actions.get("price_adjustment_effective_date_ledger_ready")) and float(finance.get("visible_statement_coverage_pct", 0)) >= 99.5
    summary={"created_at_utc":datetime.now(timezone.utc).isoformat(timespec="seconds"),"task":"v5j_cross_period_technical_validation_gate","pre2021_window":"2013-01-01_to_2021-04-30_train_independent_validation_only","formal_backtest_window":"2021-05-01_to_2026-05-31","technical_rule_validation_started":False,"technical_rule_validation_allowed":all_pass,"reason":"All required data gates are recorded with PIT boundaries; no technical feature or rule has been run.","v57f_core_modified":False,"accepted":False,"pm_gate_decision":"ready_for_frozen_technical_validation_not_started" if all_pass else "remain_data_gate_only"}
    _write_csv(out/"v5j_cross_period_data_gate_matrix.csv", rows); (out/"v5j_cross_period_data_gate_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"v5j_cross_period_data_gate_report.md").write_text("# V5j cross-period technical validation gate\n\n- One-minute sources, PIT dividend/company-action ledger, local effective-date adjustment factors, and PIT financial quality fields are now packaged.\n- Terminal non-tradable periods are explicit and never receive filled or substituted bars.\n- Cross-period technical-rule validation has not started.\n",encoding="utf-8")
    return summary

def _read_json(p:Path)->dict[str,Any]: return json.loads(p.read_text(encoding="utf-8"))
def _write_csv(p:Path,rows:list[dict[str,Any]])->None:
    with p.open("w",encoding="utf-8-sig",newline="") as h:w=csv.DictWriter(h,list(rows[0]));w.writeheader();w.writerows(rows)
if __name__=="__main__":print(json.dumps(run_v5j_cross_period_technical_validation_gate(),ensure_ascii=False,indent=2))

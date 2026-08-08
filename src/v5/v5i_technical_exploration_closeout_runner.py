from __future__ import annotations
import csv,json
from pathlib import Path
from datetime import datetime,timezone
from typing import Any

OUT=Path('v5i_technical_exploration_hour_packet')/'current'
SOURCES={
'v5i_sell_timing':Path('v5i_sell_execution_closeout/current/v5i_sell_execution_closeout_comparison.csv'),
'v5h_buy_timing_pre2021':Path('v5j_technical_existing_model_validation/current/v5j_pre2021_fixed_v5h_result.csv'),
'v5f_adaptive_governance':Path('v5f_adaptive_momentum_governance/current/v5f_adaptive_momentum_comparison.csv'),
'v5f_relative_zone':Path('v5f_1min_intraday_relative_zone_timing_test/current/v5f_1min_execution_timing_candidate_matrix.csv'),
}
def run(root:Path=Path('.'))->dict[str,Any]:
 out=root/OUT;out.mkdir(parents=True,exist_ok=True)
 matrix=[]
 for line,path in SOURCES.items():
  rows=_read(root/path)
  if line=='v5i_sell_timing':
   for r in rows:
    if r['candidate_id']!='v5i_existing_sell_time_control': matrix.append(_row(line,r['candidate_id'],'sell_execution',r['proceeds_delta_bps'],'formal_2021_2026','negative','rejected'))
  elif line=='v5h_buy_timing_pre2021':
   r=rows[0];matrix.append(_row(line,r['candidate_id'],'buy_execution',r['weighted_incremental_edge_bps'],'pre2021_proxy_2019_2020','negative','rejected_independent_check'))
  elif line=='v5f_adaptive_governance':
   for r in rows:
    if r['version_id']=='adaptive_monthly_momentum_70_30':matrix.append(_row(line,r['version_id'],'monthly_weight_governance',r['incremental_delta_return_vs_champion'],'formal_2021_2026','positive_but_thin','observation_only'))
  else:
   matrix.append(_row(line,'relative_zone_execution_contexts','execution_diagnostic','', 'formal_2021_2026','diagnostic_positive','not_fixed_or_independently_validated'))
 decision='no_v5i_technical_candidate_admitted_to_joinquant'
 summary={'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),'task':'v5i_technical_exploration_hour_packet','status':'completed_exploration_closeout','pm_gate_decision':decision,'joinquant_candidate_count':0,'accepted':False,'v57f_core_modified':False,'v5f_mainline_modified':False,'threshold_scan_used':False}
 _write(out/'v5i_technical_exploration_matrix.csv',matrix);_write(out/'v5i_technical_exploration_pm_gate.csv',[{'pm_gate_decision':decision,'reason':'No explored technical route has both positive conservative evidence and independent validation.','accepted':False,'joinquant_started':False}]);(out/'v5i_technical_exploration_report.md').write_text(_report(matrix),encoding='utf-8');(out/'v5i_technical_exploration_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return summary
def _row(line,candidate,scope,edge,window,evidence,decision):return {'research_line':line,'candidate_id':candidate,'scope':scope,'reported_edge':edge,'evidence_window':window,'evidence_status':evidence,'admission_decision':decision,'accepted':False}
def _read(p):
 with p.open(encoding='utf-8-sig',newline='') as h:return list(csv.DictReader(h))
def _write(p,rows):
 with p.open('w',encoding='utf-8-sig',newline='') as h:
  w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def _report(rows):
 return '# V5i Technical Exploration Closeout\n\n- No technical candidate is admitted to JoinQuant.\n- V5i sell execution was negative under conservative equal-cost fills.\n- V5h buy timing failed its available pre-2021 proxy check.\n- Adaptive monthly governance remains observation only.\n- Relative-zone results remain diagnostics pending a fixed independent validation.\n\n'+''.join(f"- `{r['candidate_id']}`: `{r['admission_decision']}`.\n" for r in rows)
if __name__=='__main__': print(json.dumps(run(),ensure_ascii=False,indent=2))

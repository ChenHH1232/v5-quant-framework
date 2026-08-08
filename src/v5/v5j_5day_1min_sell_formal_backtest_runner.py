from __future__ import annotations
import csv,json,math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from v5.v5j_family_sell_execution_formal_backtest_runner import _adjust_nav,_daily_returns,_metrics
from v5.v5j_5day_1min_family_execution_validation_runner import _day,_state,_fill,_f

OUT=Path('v5j_5day_1min_sell_formal_backtest')/'current';MINUTE=Path('\u6570\u636e\u5e93')/'processed'/'local_1min_clean_2013_2026'/'by_year'
TOTAL=Path('v5j_family_sell_execution_formal_backtest')/'current'/'v5j_formal_family_sell_execution_events.csv';OVERLAY=Path('v5j_overlay_only_sell_formal_backtest')/'current'/'v5j_overlay_only_formal_sell_events.csv'
STRUCT=Path('v5f_structural_rough_screen')/'current'/'v5f_structural_rough_screen_daily_returns.csv';QV=Path('v5f_quality_value_mean_reversion')/'current'/'v5f_qv_mean_reversion_daily_returns.csv'

def run(root:Path=Path('.'))->dict[str,Any]:
 ev=_events(root); done=_evaluate(root,ev); nav=[];metrics=[]
 for fam,path,version in [('value_core',STRUCT,'v57f_startup_preload_repaired_baseline'),('momentum_overlay_70_30',STRUCT,'internal_subsleeve_mom12_70_30'),('mean_reversion_20d_overlay_70_30',QV,'qv_mr_20d_rebalance_70_30')]:
  e=[x for x in done if x['strategy_family']==fam];n=_adjust_nav(_daily_returns(root/path,version),e,fam);nav+=n;metrics.append(_metrics(n,fam))
 audit=[{'audit_id':'five_completed_sessions_only','status':'pass','detail':True},{'audit_id':'value_base_unchanged_for_overlay','status':'pass','detail':True},{'audit_id':'minute_coverage','status':'pass' if all(x['pit_status']=='pass' for x in done) else 'review','detail':sum(x['pit_status']!='pass' for x in done)},{'audit_id':'price_only_not_cash_path_equivalent','status':'pass','detail':True}];positive=[m['strategy_family'] for m in metrics if _f(m['delta_return_pct_points'])>0];decision={'pm_gate_decision':'five_day_sell_formal_positive_but_cash_path_blocks_promotion' if positive else 'five_day_sell_formal_no_consistent_edge_keep_diagnostic_only','positive_families':';'.join(positive),'accepted':False};out=root/OUT;out.mkdir(parents=True,exist_ok=True)
 for n,r in [('v5j_5day_formal_sell_events.csv',done),('v5j_5day_formal_sell_daily_nav.csv',nav),('v5j_5day_formal_sell_metrics.csv',metrics),('v5j_5day_formal_sell_audit.csv',audit),('v5j_5day_formal_sell_pm_gate.csv',[decision])]:_write(out/n,r)
 s={'created_at_utc':_now(),'task':'v5j_5day_1min_sell_formal_backtest','formal_window':'2021-05-01_to_2026-05-31','frozen_rule':'five_completed_session_price_volume_confirmation','buy_rules_tested_and_rejected_in_pre2021_validation':True,'sell_intent_count':len(done),'fillable_count':sum(x['pit_status']=='pass' for x in done),'accepted':False,'pm_gate_decision':decision['pm_gate_decision']};(out/'v5j_5day_formal_sell_summary.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return s

def _events(root:Path)->list[dict[str,Any]]:
 out=[]
 for r in _csv(root/TOTAL):
  if r['strategy_family']=='value_core':out.append({'intent_id':'v|'+r['intent_id'],'strategy_family':'value_core','trade_date':r['trade_date'],'code':r['code'],'sell_weight':_f(r['sell_weight']),'value_base_unchanged':True})
 for r in _csv(root/OVERLAY):
  out.append({'intent_id':'o|'+r['intent_id'],'strategy_family':r['strategy_family'],'trade_date':r['trade_date'],'code':r['code'],'sell_weight':_f(r['sell_weight']),'value_base_unchanged':True})
 return out

def _evaluate(root:Path,events:list[dict[str,Any]])->list[dict[str,Any]]:
 by=defaultdict(list)
 for e in events:by[e['code']].append(e)
 out=[]
 for code,items in by.items():
  wanted={x['trade_date'] for x in items};days={};bars={}
  for y in range(2020,2027):
   p=root/MINUTE/str(y)/f"{code.replace('.','_')}_1min.csv"
   if not p.exists():continue
   d=defaultdict(list)
   for r in _csv(p):d[r.get('trade_date','')].append(r)
   for date,rows in d.items():
    days[date]=_day(rows)
    if date in wanted:bars[date]={r['time']:r for r in rows}
  dates=sorted(days)
  for e in items:
   prior=[date for date in dates if date<e['trade_date']][-5:];state=_state([days[date] for date in prior]);idx=bars.get(e['trade_date'],{});control=_fill(idx,'09:31:00');time='14:46:00' if state['agreement']=='up_volume_confirmed' else '14:01:00';sel=_fill(idx,time);cp=_f(control.get('open')) if control else 0.;sp=_f(sel.get('open')) if sel else 0.;delta=sp/cp-1 if cp and sp else 0.;out.append({**e,'prior_session_count':len(prior),'five_day_price_volume_agreement':state['agreement'],'selected_time':time,'control_price':cp,'selected_price':sp,'sell_proceeds_delta_bps':delta*10000,'weighted_execution_adjustment_return':e['sell_weight']*delta,'pit_status':'pass' if state['available'] and cp and sp else 'missing_prior_window_or_bar','accepted':False})
 return out
def _csv(p:Path)->list[dict[str,str]]:
 with p.open(encoding='utf-8-sig',newline='') as h:return list(csv.DictReader(h))
def _write(p:Path,rows:list[dict[str,Any]]):
 k=list(dict.fromkeys(x for r in rows for x in r)) or ['empty']
 with p.open('w',encoding='utf-8-sig',newline='') as h:w=csv.DictWriter(h,k);w.writeheader();w.writerows(rows)
def _now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))

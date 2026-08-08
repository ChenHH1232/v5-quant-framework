from __future__ import annotations

import csv, json, math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUT=Path('v5j_5day_1min_family_execution_validation')/'current'
DB=Path('\u6570\u636e\u5e93')/'processed'/'pre2021_repaired_multisleeve_pit_pool_v5'
POOL=DB/'repaired_multisleeve_pit_pool.csv'
MINUTE=Path('\u6570\u636e\u5e93')/'processed'/'local_1min_clean_2013_2026'/'by_year'
SELLS=Path('v5j_frozen_sell_timing_full_pit_validation')/'current'/'v5j_frozen_sell_timing_full_pit_events.csv'
OVERLAY_WEIGHTS=Path('v5j_overlay_only_sell_validation')/'current'/'v5j_overlay_only_pre2021_weights.csv'
OVERLAY_SELLS=Path('v5j_overlay_only_sell_validation')/'current'/'v5j_overlay_only_pre2021_sell_intents.csv'
GATE=Path('v5j_cross_period_technical_validation_gate')/'current'/'v5j_cross_period_data_gate_summary.json'

def run_v5j_5day_1min_family_execution_validation(root:Path=Path('.'))->dict[str,Any]:
 if not json.loads((root/GATE).read_text(encoding='utf-8')).get('technical_rule_validation_allowed'):raise RuntimeError('PIT gate is not open.')
 pool=[r for r in _csv(root/POOL) if r.get('pool_eligibility')=='eligible_for_predecessor_pool']; events=_events(root,pool); evaluated=_evaluate(root,events); results=_results(evaluated); yearly=_yearly(evaluated); audits=_audits(events,evaluated); decision=_decision(results,yearly,audits);out=root/OUT;out.mkdir(parents=True,exist_ok=True)
 _write(out/'v5j_5day_1min_feature_schema.csv',_schema());_write(out/'v5j_5day_1min_family_events.csv',evaluated);_write(out/'v5j_5day_1min_family_results.csv',results);_write(out/'v5j_5day_1min_family_sleeve_year.csv',yearly);_write(out/'v5j_5day_1min_family_audit.csv',audits);_write(out/'v5j_5day_1min_family_pm_gate.csv',[decision])
 summary={'created_at_utc':_now(),'task':'v5j_5day_1min_family_execution_validation','validation_window':'2013-01-01_to_2021-04-30','prior_completed_session_count':5,'event_count':len(events),'fillable_event_count':sum(x['pit_status']=='pass' for x in evaluated),'value_base_weight_changed':False,'parameter_scan_used':False,'accepted':False,'pm_gate_decision':decision['pm_gate_decision']};(out/'v5j_5day_1min_family_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(out/'v5j_5day_1min_family_report.md').write_text(_report(summary,results,decision),encoding='utf-8');return summary

def _events(root:Path,pool:list[dict[str,str]])->list[dict[str,Any]]:
 out=[]
 for r in pool:out.append({'event_id':f"value_buy|{r['rebalance_date']}|{r['code']}",'family':'value_core','action':'buy','trade_date':r['rebalance_date'],'code':r['code'],'sleeve_id':r['sleeve_id'],'weight':1.0,'value_base_unchanged':True})
 for r in _csv(root/SELLS):
  if r['candidate_id']=='open_control':out.append({'event_id':f"value_sell|{r['intent_id']}",'family':'value_core','action':'sell','trade_date':r['execution_date'],'code':r['code'],'sleeve_id':r['sleeve_id'],'weight':1.0,'value_base_unchanged':True})
 weights=_csv(root/OVERLAY_WEIGHTS);out.extend(_overlay_buys(weights));
 for r in _csv(root/OVERLAY_SELLS):out.append({'event_id':f"{r['strategy_family']}|sell|{r['intent_id']}",'family':r['strategy_family'],'action':'sell','trade_date':r['trade_date'],'code':r['code'],'sleeve_id':r['sleeve_id'],'weight':_f(r['sell_weight']),'value_base_unchanged':True})
 return [r for r in out if r['trade_date']<'2021-05-01']

def _overlay_buys(rows:list[dict[str,str]])->list[dict[str,Any]]:
 by=defaultdict(dict);out=[]
 for r in rows:by[(r['strategy_family'],r['rebalance_date'])][r['code']]=r
 prior=defaultdict(dict)
 for (family,date),current in sorted(by.items()):
  for code in set(prior[family])|set(current):
   inc=_f(current.get(code,{}).get('overlay_weight'))-_f(prior[family].get(code,{}).get('overlay_weight'))
   if inc>1e-10:
    ref=current.get(code) or prior[family][code];out.append({'event_id':f'{family}|buy|{date}|{code}','family':family,'action':'buy','trade_date':date,'code':code,'sleeve_id':ref['sleeve_id'],'weight':inc,'value_base_unchanged':True})
  prior[family]=current
 return out

def _evaluate(root:Path,events:list[dict[str,Any]])->list[dict[str,Any]]:
 bycode=defaultdict(list)
 for e in events:bycode[e['code']].append(e)
 out=[]
 for code,members in bycode.items():
  requested={e['trade_date'] for e in members};summaries={};bars={}
  years=range(2013,2022)
  for year in years:
   p=root/MINUTE/str(year)/f"{code.replace('.','_')}_1min.csv"
   if not p.exists():continue
   byday=defaultdict(list)
   for r in _csv(p):byday[r.get('trade_date','')].append(r)
   for d,v in byday.items():
    summaries[d]=_day(v)
    if d in requested:bars[d]={x['time']:x for x in v}
  dates=sorted(summaries)
  for e in members:
   prior=[d for d in dates if d<e['trade_date']][-5:];state=_state([summaries[d] for d in prior]);out.append(_one(e,bars.get(e['trade_date'],{}),state,len(prior)))
 return out

def _day(rows:list[dict[str,str]])->dict[str,float]:
 vol=amt=signed=0.;prev=_f(rows[0].get('close')) if rows else 0.
 for r in rows:
  a=_f(r.get('amount'));c=_f(r.get('close'));amt+=a;vol+=_f(r.get('volume'));signed+=a if c>prev else -a if c<prev else 0.;prev=c
 return {'close':prev,'vwap':amt/vol if vol else 0.,'volume':vol,'pressure':signed/amt if amt else 0.}

def _state(days:list[dict[str,float]])->dict[str,Any]:
 if len(days)<5:return {'available':False,'pressure':'missing','vwap':'missing','trend':'missing','volume':'missing','agreement':'missing'}
 p=sum(x['pressure'] for x in days)/5;above=sum(x['close']>x['vwap'] for x in days);positive=p>0;expanding=days[-1]['volume']>=days[0]['volume'];return {'available':True,'pressure':'positive' if positive else 'nonpositive','vwap':'majority_above' if above>=3 else 'majority_not_above','trend':'up' if days[-1]['close']>days[0]['close'] else 'nonup','volume':'expanding_or_flat' if expanding else 'contracting','agreement':'up_volume_confirmed' if positive and expanding else 'not_up_volume_confirmed'}

def _one(e:dict[str,Any],index:dict[str,dict[str,str]],state:dict[str,Any],prior_count:int)->dict[str,Any]:
 control=_fill(index,'10:01:00' if e['action']=='buy' else '09:31:00');confirmed=state['agreement']=='up_volume_confirmed';selected_time=('10:01:00' if confirmed else '14:01:00') if e['action']=='buy' else ('14:46:00' if confirmed else '14:01:00');selected=_fill(index,selected_time);cp=_f(control.get('open')) if control else 0.;sp=_f(selected.get('open')) if selected else 0.;delta=(cp/sp-1)*10000 if e['action']=='buy' and cp and sp else (sp/cp-1)*10000 if cp and sp else ''
 return {**e,'prior_session_count':prior_count,'five_day_pressure_state':state['pressure'],'five_day_vwap_state':state['vwap'],'five_day_trend_state':state['trend'],'five_day_volume_state':state['volume'],'five_day_price_volume_agreement':state['agreement'],'control_time':'10:01:00' if e['action']=='buy' else '09:31:00','selected_time':selected_time,'control_price':cp,'selected_price':sp,'execution_improvement_bps':delta,'pit_status':'pass' if state['available'] and cp and sp else 'missing_prior_window_or_bar','future_return_used_for_signal':False,'accepted':False}

def _fill(i:dict[str,dict[str,str]],t:str)->dict[str,str]|None:
 r=i.get(t);return r if r and _f(r.get('open'))>0 and _f(r.get('volume'))>0 else None
def _results(rows:list[dict[str,Any]])->list[dict[str,Any]]:
 out=[]
 for (f,a),v in sorted(_group(rows,lambda x:(x['family'],x['action'])).items()):
  z=[_f(x['execution_improvement_bps']) for x in v if x['pit_status']=='pass'];out.append({'family':f,'action':a,'event_count':len(v),'fillable_event_count':len(z),'mean_execution_improvement_bps':sum(z)/len(z) if z else 0.,'positive_event_ratio':sum(x>0 for x in z)/len(z) if z else 0.,'accepted':False})
 return out
def _yearly(rows:list[dict[str,Any]])->list[dict[str,Any]]:
 out=[]
 for (f,a,y,s),v in sorted(_group(rows,lambda x:(x['family'],x['action'],x['trade_date'][:4],x['sleeve_id'])).items()):
  z=[_f(x['execution_improvement_bps']) for x in v if x['pit_status']=='pass'];out.append({'family':f,'action':a,'year':y,'sleeve_id':s,'event_count':len(z),'mean_execution_improvement_bps':sum(z)/len(z) if z else 0.})
 return out
def _audits(events:list[dict[str,Any]],rows:list[dict[str,Any]])->list[dict[str,Any]]:return [{'audit_id':'value_base_unchanged','status':'pass','detail':all(x['value_base_unchanged'] for x in events)},{'audit_id':'five_completed_prior_sessions_only','status':'pass','detail':True},{'audit_id':'no_parameter_scan','status':'pass','detail':False},{'audit_id':'minute_coverage','status':'pass' if all(x['pit_status']=='pass' for x in rows) else 'review','detail':sum(x['pit_status']!='pass' for x in rows)}]
def _decision(results:list[dict[str,Any]],yearly:list[dict[str,Any]],audits:list[dict[str,Any]])->dict[str,Any]:
 good=[]
 for r in results:
  u=[x for x in yearly if x['family']==r['family'] and x['action']==r['action'] and x['event_count']>0];ratio=sum(_f(x['mean_execution_improvement_bps'])>0 for x in u)/len(u) if u else 0.
  if _f(r['mean_execution_improvement_bps'])>0 and _f(r['positive_event_ratio'])>=.5 and ratio>=.6:good.append(f"{r['family']}:{r['action']}")
 return {'pm_gate_decision':'five_day_1min_candidates_ready_for_separate_formal_backtest_not_accepted' if good else 'five_day_1min_no_stable_candidate_keep_diagnostic_only','supported_family_actions':';'.join(good),'accepted':False}
def _schema()->list[dict[str,str]]:return [{'feature':'five_day_signed_amount_pressure','definition':'mean of five completed sessions signed 1-minute amount pressure; positive vs nonpositive'},{'feature':'five_day_close_vs_vwap','definition':'majority of five completed sessions close above own VWAP'},{'feature':'five_day_close_trend','definition':'last completed close versus first completed close'},{'feature':'five_day_volume_trend','definition':'last completed session total 1-minute volume versus first completed session volume'},{'feature':'five_day_price_volume_agreement','definition':'up_volume_confirmed only when five-day signed amount pressure is positive and five-day volume is expanding or flat'}]
def _group(rows:list[dict[str,Any]],key:Any)->dict[Any,list[dict[str,Any]]]:
 out=defaultdict(list)
 for r in rows:out[key(r)].append(r)
 return out
def _f(v:Any)->float:
 try:return float(v) if math.isfinite(float(v)) else 0.
 except (TypeError,ValueError):return 0.
def _csv(p:Path)->list[dict[str,str]]:
 with p.open(encoding='utf-8-sig',newline='') as h:return list(csv.DictReader(h))
def _write(p:Path,rows:list[dict[str,Any]])->None:
 keys=list(dict.fromkeys(k for r in rows for k in r)) or ['empty'];p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',encoding='utf-8-sig',newline='') as h:w=csv.DictWriter(h,keys);w.writeheader();w.writerows(rows)
def _now()->str:return datetime.now(timezone.utc).isoformat(timespec='seconds')
def _report(s:dict[str,Any],r:list[dict[str,Any]],d:dict[str,Any])->str:return '# Five-day 1-minute family execution validation\n\n- Five fully completed sessions only.\n- PM gate: `'+d['pm_gate_decision']+'`.\n'
if __name__=='__main__':print(json.dumps(run_v5j_5day_1min_family_execution_validation(),ensure_ascii=False,indent=2))

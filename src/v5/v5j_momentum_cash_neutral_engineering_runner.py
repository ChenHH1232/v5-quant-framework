from __future__ import annotations
import csv,math
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from v5.v5j_momentum_daily_price_volume_sell_runner import _daily

OUT=Path('v5j_momentum_cash_neutral_engineering')/'current';W=Path('v5f_structural_rough_screen')/'current'/'v5f_structural_rough_screen_weights.csv';EVENTS=Path('v5j_momentum_daily_price_volume_sell')/'current'/'v5j_daily_pv_momentum_formal_events.csv';MINUTE=Path('\u6570\u636e\u5e93')/'processed'/'local_1min_clean_2013_2026'/'by_year';BASE='v57f_startup_preload_repaired_baseline';MOM='internal_subsleeve_mom12_70_30';BUY_FEE=.0003;SELL_FEE=.0013
def run(root:Path=Path('.'))->dict[str,Any]:
 raw=_csv(root/W);base=_snap(raw,BASE);mom=_snap(raw,MOM);sell_times={r['intent_id']:r for r in _csv(root/EVENTS) if r['pit_status']=='pass'};legs=_legs(base,mom,sell_times);daily=_daily(root,{r['code'] for r in legs});priced=_price(root,legs,daily);ledger=_ledger(priced);audit=_audit(ledger);decision={'pm_gate_decision':'cash_neutral_engineering_pass_ready_for_separate_execution_simulation_not_accepted' if audit['fail_count']==0 else 'cash_neutral_engineering_failed_close_v5f_technical_sell_line','technical_analysis_v5f_sell_line_closed':audit['fail_count']>0,'accepted':False};out=root/OUT;out.mkdir(parents=True,exist_ok=True)
 for n,r in [('v5j_momentum_cash_neutral_ledger.csv',priced),('v5j_momentum_cash_neutral_reconciliation.csv',ledger),('v5j_momentum_cash_neutral_audit.csv',[audit]),('v5j_momentum_cash_neutral_pm_gate.csv',[decision])]:_write(out/n,r)
 s={'created_at_utc':_now(),'task':'v5j_momentum_cash_neutral_engineering','window':'2021-05-01_to_2026-05-31','value_base_weight_changed':False,'sell_fee_rate':SELL_FEE,'buy_fee_rate':BUY_FEE,'reconciliation_count':len(ledger),'fail_count':audit['fail_count'],'accepted':False,'pm_gate_decision':decision['pm_gate_decision']};import json;(out/'v5j_momentum_cash_neutral_summary.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return s
def _snap(rows:list[dict[str,str]],version:str):
 out=defaultdict(dict)
 for r in rows:
  if r['version_id']==version and '2021-05-01'<=r['rebalance_date']<='2026-05-31':out[r['rebalance_date']][r['code']]={'w':_f(r['target_weight']),'sleeve':r['sleeve']}
 return dict(sorted(out.items()))
def _legs(base,mom,signals):
 out=[];prev={}
 for date,target in mom.items():
  ov={c:{'w':target.get(c,{'w':0})['w']-base.get(date,{}).get(c,{'w':0})['w'],'sleeve':target.get(c,base.get(date,{}).get(c,{})).get('sleeve','')} for c in set(target)|set(base.get(date,{}))}
  for code in set(prev)|set(ov):
   d=ov.get(code,{'w':0})['w']-prev.get(code,{'w':0})['w'];sl=(ov.get(code) or prev.get(code))['sleeve']
   if d< -1e-10:
    key=f'momentum_overlay_70_30|{date}|{code}';sig=signals.get(key,{});out.append({'trade_date':date,'code':code,'sleeve_id':sl,'side':'sell','overlay_weight':-d,'sell_time':sig.get('selected_time',''),'value_base_unchanged':True})
   elif d>1e-10:out.append({'trade_date':date,'code':code,'sleeve_id':sl,'side':'buy','overlay_weight':d,'buy_time':'14:47:00','value_base_unchanged':True})
  prev=ov
 return out
def _price(root,legs,daily):
 by=defaultdict(list)
 for x in legs:by[x['code']].append(x)
 for code,v in by.items():
  wanted={x['trade_date'] for x in v};bars={}
  for y in range(2021,2027):
   p=root/MINUTE/str(y)/f"{code.replace('.','_')}_1min.csv"
   if p.exists():
    for r in _csv(p):
     if r.get('trade_date') in wanted and r.get('time') in {'14:01:00','14:46:00','14:47:00'}:bars[(r['trade_date'],r['time'])]=r
  hist=daily.get(code,[])
  for x in v:
   prior=[r for r in hist if r['date']<x['trade_date']];ref=prior[-1]['close'] if prior else 0.;t=x.get('sell_time') if x['side']=='sell' else x.get('buy_time');r=bars.get((x['trade_date'],t),{});px=_f(r.get('open'));x.update({'reference_prior_close':ref,'execution_time':t,'execution_price':px,'bar_available':bool(px and _f(r.get('volume'))>0),'notional_at_prior_close':x['overlay_weight'],'cash_amount':x['overlay_weight']/ref*px*(1-SELL_FEE if x['side']=='sell' else 1+BUY_FEE) if ref and px else 0.})
 return legs
def _ledger(legs):
 g=defaultdict(list)
 for x in legs:g[(x['trade_date'],x['sleeve_id'])].append(x)
 out=[]
 for (d,s),v in sorted(g.items()):
  sells=sum(x['cash_amount'] for x in v if x['side']=='sell');buys=sum(x['cash_amount'] for x in v if x['side']=='buy');missing=sum(not x['bar_available'] for x in v);out.append({'trade_date':d,'sleeve_id':s,'overlay_sell_cash_confirmed':sells,'overlay_buy_cash_required':buys,'cash_surplus_deficit':sells-buys,'missing_leg_count':missing,'cash_neutral_pass':sells>=buys and missing==0,'cross_sleeve_transfer':False,'value_base_changed':False})
 return out
def _audit(rows):
 fail=sum(not x['cash_neutral_pass'] for x in rows);return {'audit_id':'strict_same_sleeve_cash_neutrality','status':'pass' if fail==0 else 'fail','reconciliation_count':len(rows),'fail_count':fail,'cross_sleeve_transfer_count':sum(x['cross_sleeve_transfer'] for x in rows),'value_base_change_count':sum(x['value_base_changed'] for x in rows)}
def _csv(p):
 with p.open(encoding='utf-8-sig',newline='') as h:return list(csv.DictReader(h))
def _write(p,rows):
 k=list(dict.fromkeys(x for r in rows for x in r)) or ['empty']
 with p.open('w',encoding='utf-8-sig',newline='') as h:w=csv.DictWriter(h,k);w.writeheader();w.writerows(rows)
def _f(x):
 try:return float(x) if math.isfinite(float(x)) else 0.
 except:return 0.
def _now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
if __name__=='__main__':print(run())

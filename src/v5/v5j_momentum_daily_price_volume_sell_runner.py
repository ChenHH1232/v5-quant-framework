from __future__ import annotations
import csv,io,json,math,zipfile
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from v5.v5j_family_sell_execution_formal_backtest_runner import _adjust_nav,_daily_returns,_metrics

OUT=Path('v5j_momentum_daily_price_volume_sell')/'current';PRE=Path('v5j_overlay_only_sell_validation')/'current'/'v5j_overlay_only_pre2021_sell_intents.csv';FORM=Path('v5j_overlay_only_sell_formal_backtest')/'current'/'v5j_overlay_only_formal_sell_events.csv';MINUTE=Path('\u6570\u636e\u5e93')/'processed'/'local_1min_clean_2013_2026'/'by_year';DAILY_PARTS=('\u4e00\u5206\u949f\u884c\u60c5\u6570\u636e 2000\u81f32026','\u80a1\u7968\u5168\u5468\u671fK\u7ebf\u5305','\u5386\u53f2\u6570\u636e','a\u80a1\u65e5\u7ebf.zip');STRUCT=Path('v5f_structural_rough_screen')/'current'/'v5f_structural_rough_screen_daily_returns.csv'

def run(root:Path=Path('.'))->dict[str,Any]:
 pre=[_norm(r,'pre2021') for r in _csv(root/PRE) if r['strategy_family']=='momentum_overlay_70_30'];formal=[_norm(r,'formal') for r in _csv(root/FORM) if r['strategy_family']=='momentum_overlay_70_30'];daily=_daily(root,{x['code'] for x in pre+formal});allrows=_eval(root,pre+formal,daily);p=[x for x in allrows if x['sample']=='pre2021'];f=[x for x in allrows if x['sample']=='formal'];pres=_result(p);nav=_adjust_nav(_daily_returns(root/STRUCT,'internal_subsleeve_mom12_70_30'),f,'momentum_overlay_70_30_daily_price_volume_sell');met=_metrics(nav,'momentum_overlay_70_30_daily_price_volume_sell');gate={'pm_gate_decision':'daily_price_volume_momentum_sell_positive_but_cash_path_blocks_promotion' if pres['mean_execution_improvement_bps']>0 and met['delta_return_pct_points']>0 else 'daily_price_volume_momentum_sell_not_stable_keep_diagnostic_only','accepted':False};out=root/OUT;out.mkdir(parents=True,exist_ok=True)
 for n,r in [('v5j_daily_pv_momentum_pre2021_events.csv',p),('v5j_daily_pv_momentum_pre2021_result.csv',[pres]),('v5j_daily_pv_momentum_formal_events.csv',f),('v5j_daily_pv_momentum_formal_daily_nav.csv',nav),('v5j_daily_pv_momentum_formal_metrics.csv',[met]),('v5j_daily_pv_momentum_pm_gate.csv',[gate])]:_write(out/n,r)
 s={'created_at_utc':_now(),'task':'v5j_momentum_daily_price_volume_sell','rule':'prior five completed daily bars: last close > first close AND last volume >= mean prior four volumes -> sell 14:46; else sell 14:01','pre2021_fillable':pres['fillable_event_count'],'pre2021_mean_bps':pres['mean_execution_improvement_bps'],'formal_delta_return_pct_points':met['delta_return_pct_points'],'value_base_weight_changed':False,'mean_reversion_included':False,'accepted':False,'pm_gate_decision':gate['pm_gate_decision']};(out/'v5j_daily_pv_momentum_summary.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return s
def _norm(r:dict[str,str],sample:str)->dict[str,Any]:return {'intent_id':r['intent_id'],'sample':sample,'code':r['code'],'trade_date':r['trade_date'],'sell_weight':_f(r['sell_weight']),'strategy_family':'momentum_overlay_70_30','value_base_unchanged':True}
def _daily(root:Path,codes:set[str])->dict[str,list[dict[str,float]]]:
 p=root.resolve().parent.parent.joinpath(*DAILY_PARTS);out=defaultdict(list);names={}
 with zipfile.ZipFile(p) as z:
  names={Path(n).name.upper():n for n in z.namelist() if n.endswith('.csv')}
  for code in codes:
   local=f"{code[:6]}.{'SH' if code.endswith('XSHG') else 'SZ'}";name=names.get(f'{local}.CSV')
   if not name:continue
   raw=z.read(name);text=raw.decode('gb18030');
   for r in csv.reader(io.StringIO(text)):
    if len(r)>9 and r[1].isdigit():out[code].append({'date':f'{r[1][:4]}-{r[1][4:6]}-{r[1][6:8]}','close':_f(r[5]),'volume':_f(r[9])})
 for x in out.values():x.sort(key=lambda r:r['date'])
 return out
def _eval(root:Path,events:list[dict[str,Any]],daily:dict[str,list[dict[str,float]]])->list[dict[str,Any]]:
 by=defaultdict(list)
 for e in events:by[e['code']].append(e)
 out=[]
 for code,items in by.items():
  wanted={(e['trade_date'],e['sample']) for e in items};bar={}
  for y in range(2013,2027):
   p=root/MINUTE/str(y)/f"{code.replace('.','_')}_1min.csv"
   if not p.exists():continue
   d=defaultdict(list)
   for r in _csv(p):d[r.get('trade_date','')].append(r)
   for e in items:
    if e['trade_date'] in d:bar[e['intent_id']]={r['time']:r for r in d[e['trade_date']]}
  dates=daily.get(code,[])
  for e in items:
   hist=[r for r in dates if r['date']<e['trade_date']][-5:];confirmed=len(hist)==5 and hist[-1]['close']>hist[0]['close'] and hist[-1]['volume']>=sum(r['volume'] for r in hist[:-1])/4;idx=bar.get(e['intent_id'],{});c=_fill(idx,'09:31:00');t='14:46:00' if confirmed else '14:01:00';q=_fill(idx,t);cp=_f(c.get('open')) if c else 0.;sp=_f(q.get('open')) if q else 0.;delta=sp/cp-1 if cp and sp else 0.;out.append({**e,'daily_price_volume_confirmed':confirmed,'selected_time':t,'sell_proceeds_delta_bps':delta*10000,'weighted_execution_adjustment_return':e['sell_weight']*delta,'pit_status':'pass' if len(hist)==5 and cp and sp else 'missing_daily_window_or_bar','accepted':False})
 return out
def _result(rows:list[dict[str,Any]])->dict[str,Any]:
 v=[x for x in rows if x['pit_status']=='pass'];z=[_f(x['sell_proceeds_delta_bps']) for x in v];return {'event_count':len(rows),'fillable_event_count':len(v),'mean_execution_improvement_bps':sum(z)/len(z) if z else 0.,'positive_event_ratio':sum(x>0 for x in z)/len(z) if z else 0.,'weighted_adjustment_bps':sum(_f(x['weighted_execution_adjustment_return']) for x in v)*10000,'accepted':False}
def _fill(i:dict[str,dict[str,str]],t:str):
 r=i.get(t);return r if r and _f(r.get('open'))>0 and _f(r.get('volume'))>0 else None
def _csv(p:Path):
 with p.open(encoding='utf-8-sig',newline='') as h:return list(csv.DictReader(h))
def _write(p:Path,rows:list[dict[str,Any]]):
 k=list(dict.fromkeys(x for r in rows for x in r)) or ['empty']
 with p.open('w',encoding='utf-8-sig',newline='') as h:w=csv.DictWriter(h,k);w.writeheader();w.writerows(rows)
def _f(v:Any)->float:
 try:return float(v) if math.isfinite(float(v)) else 0.
 except (ValueError,TypeError):return 0.
def _now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))

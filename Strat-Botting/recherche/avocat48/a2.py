import sys;sys.path.insert(0,'.')
import charge as c, pandas as pd, numpy as np
D={}
for f in c.files():
    k=c.preset(f).split()[0]
    if k in('45','47','48','49','50') and not (k=='45' and '4eb81' not in f): D[k]=c.trades(f)
def pf(x): return x[x>0].sum()/-x[x<0].sum()
print('== Q2')
for k in ['45','48','50']:
    t=D[k].copy();t['day']=(t.exit+pd.Timedelta(hours=1)).dt.date
    t['wk']=pd.to_datetime(t.day).dt.to_period('W')
    day=t.groupby('day').pnl.sum();wk=t.groupby('wk').pnl.sum()
    eq=day.cumsum();dd=(eq.cummax()-eq)
    # streak
    s=0;worst=0;ws=None;cur=[];best=(0,None,0)
    for i,(idx,r) in enumerate(t.iterrows()):
        if r.pnl<0:
            s+=r.pnl;cur.append(r.exit)
            if s<best[0]: best=(s,(cur[0],cur[-1]),len(cur))
        else: s=0;cur=[]
    # consecutive losers count
    run=0;mr=0
    for p in t.pnl:
        run=run+1 if p<0 else 0;mr=max(mr,run)
    w=t.loc[t.pnl.idxmin()];wd=day.idxmin();ww=wk.idxmin()
    print(k,'n',len(t),'losers',(t.pnl<0).sum(),'worst trade',w.pnl,w.exit,w.reason,'| 3 worst',t.pnl.nsmallest(3).tolist(),
      '| avg loss',t[t.pnl<0].pnl.mean().round(0),'| worst MAE',t.mae.min(),'| worst day',day.min(),wd,'| 3 worst days',day.nsmallest(3).round(0).to_dict(),
      '| worst wk',wk.min(),ww,'| worst streak $',round(best[0]),best[1],best[2],'maxrun losers',mr,
      '| maxDD closed EOD',round(dd.max()),'at',dd.idxmax(),'| days dd>1000:',(dd>1000).sum(),'>2000',(dd>2000).sum(), 'days<-1250(2m)',(day<-1250).sum(),'days<-833(3m: -1250/1.5)',(day<-1250/1.5).sum())
    print('  x1.5: trade',w.pnl*1.5,'day',day.min()*1.5,'week',wk.min()*1.5,'streak',best[0]*1.5,'maxDD',dd.max()*1.5,'days<-1250 (3m)',(day*1.5<-1250).sum(),'maxMAE',t.mae.min()*1.5)
    print('  losing days list', day[day<0].nsmallest(6).round(0).to_dict())
    print('  dist loss by reason', t[t.pnl<0].groupby('reason').pnl.agg(['count','mean','min']).round(0).to_dict('index'))
# trailing DD with lock: starts 50k, max loss 2000 from highest EOD, stops trailing at +2000? report breaches
t=D['48'].copy();t['day']=(t.exit+pd.Timedelta(hours=1)).dt.date;day=t.groupby('day').pnl.sum()
for m in [1,1.5]:
    eq=(day*m).cumsum();dd=eq.cummax()-eq;print('48 x',m,'maxDD',dd.max().round(0),'count days dd>=1500',(dd>=1500).sum())
print('== rolling 2000-DD from every possible start (account fresh): fraction of starts that breach 2000 trailing EOD within 60 trading days')
days=day.values
for m in [1,1.5]:
    b=0;N=0;worstmin=[]
    for i in range(len(days)):
        eq=np.cumsum(days[i:i+60]*m);pk=np.maximum.accumulate(np.maximum(eq,0));dd=(pk-eq)
        N+=1;b+=(dd>=2000).any();worstmin.append(dd.max())
    print(m,N,b,b/N,np.percentile(worstmin,[50,90,99,100]).round(0))

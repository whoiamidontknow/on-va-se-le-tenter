import sys;sys.path.insert(0,'.')
import charge as c, pandas as pd, numpy as np
D={}
for f in c.files():
    k=c.preset(f).split()[0]
    if k in('45','47','48','49','50') and not (k=='45' and '4eb81' not in f): D[k]=c.trades(f)
def pf(x): return x[x>0].sum()/-x[x<0].sum()
print('== Q3 (entry>=2025-10-24)')
for k in ['45','48']:
    t=D[k];t['q']=t.entry.dt.to_period('Q')
    y=t[t.entry>='2025-10-24'];o=t[t.entry<'2025-10-24']
    for nm,x in [('2 ans',o),('3e an',y)]:
        print(k,nm,len(x),round((x.pnl>0).mean()*100,1),round(pf(x.pnl),2),x.pnl.sum(),round(x.pnl.mean(),1))
    g=y.groupby('q').pnl.agg(['count','sum',lambda x:round((x>0).mean()*100,1),pf]);print(g.round(2).to_string())
    h=t.groupby('q').pnl.agg(['count','sum',lambda x:round((x>0).mean()*100,1),pf]);print(h.round(2).to_string()) if k=='48' else 0
    # last 60/100 trades
    for n in (50,100): x=t.tail(n);print(k,'last',n,round((x.pnl>0).mean()*100,1),round(pf(x.pnl),2),x.pnl.sum())
    # ytd monthly last 6 months
    m=t.groupby(t.entry.dt.to_period('M')).pnl.agg(['count','sum',lambda x:round((x>0).mean()*100,1)]);print(m.tail(8).to_string())
print('== Q4')
t=D['48'].copy()
def h(ts): return ts.dt.hour*60+ts.dt.minute
xm=h(t.exit);em=h(t.entry)
night=(xm>=20)&(xm<=480) 
tm=t.reason.str.startswith('Temps')
print('exit night all',night.sum(),night.mean(),'time-exit night',(night&tm).sum(),'of time exits',tm.sum(),'share of all trades',(night&tm).mean())
print('entry night',((em>=20)&(em<=480)).sum(),((em>=20)&(em<=480)).mean(), 'entry hour dist',t.entry.dt.hour.value_counts().sort_index().to_dict())
nt=t[night]; print('night-exit trades: n',len(nt),'win',(nt.pnl>0).mean(),'pf',pf(nt.pnl),'net',nt.pnl.sum(),'by reason',nt.reason.value_counts().to_dict())
dy=t[~night];print('day-exit trades',len(dy),(dy.pnl>0).mean(),pf(dy.pnl),dy.pnl.sum())
print('bars dist',t.bars.value_counts().sort_index().to_dict())
for lim in (1,2): 
    s=t[t.bars<lim+0];print('bars<',lim,len(s),s.pnl.sum(),(s.pnl>0).mean(),pf(s.pnl))
s=t[t.bars<=1];print('bars<=1',len(s),(s.pnl>0).mean(),s.pnl.sum(),s.reason.value_counts().to_dict())
print('entries where entry==exit time', (t.entry==t.exit).sum())
print('slippage (per trade, 2 micros, total $ = ticks*0.5*2)')
for tk in (0,2,4,8):
    cost=tk*0.5*2;p=t.pnl-cost
    # 'per side' double
    p2=t.pnl-2*cost
    print(tk,'ticks/trade: net',round(p.sum()),'PF',round(pf(p),2),'win%',round((p>0).mean()*100,1),'| if per side (x2): net',round(p2.sum()),'PF',round(pf(p2),2))
print('mean win',t[t.pnl>0].pnl.mean(),'mean loss',t[t.pnl<0].pnl.mean(),'avg pnl',t.pnl.mean())
# breakeven slippage ticks
for tk in (50,100,150,200):
    p=t.pnl-tk*0.5*2;print(tk,round(p.sum()),round(pf(p),2))
print('== Q5 guards')
w=(t.pnl>0).values;p=w.mean();print('win',p)
from scipy import stats
for N in (20,30,50,100):
    r=pd.Series(w.astype(float)).rolling(N).mean().dropna()*100
    print(N,'rolling win% pct1,5,50',np.percentile(r,[1,5,50]).round(1),'min',r.min().round(1),'binom 1%/5% count',stats.binom.ppf(0.01,N,p),stats.binom.ppf(0.05,N,p))
    rn=t.pnl.rolling(N).sum().dropna();print('   rolling net pct1,5',np.percentile(rn,[1,5]).round(0),'min',rn.min())
# longest losing runs distribution; prob of k losers in a row at p
for k in (3,4,5,6): print('P(run>=%d)'%k, 'prob at a given trade', (1-p)**k)
# time-to-recover: longest period between equity highs in trades/days
eq=t.pnl.cumsum();pk=eq.cummax();under=(eq<pk).astype(int);runl=0;mx=0
for u in under: runl=runl+1 if u else 0;mx=max(mx,runl)
print('longest underwater (trades)',mx,'trades/week',len(t)/156)
# sup of hold: stops = when to stop if observed loses; 
for N in (30,50):
    for p0 in (0.6,0.65,0.7):
        pass
print('P(win<=k of N | true p)') 
for N,k in [(30,18),(30,20),(50,32),(50,35),(100,65),(100,70)]:
    print(N,k,'p_true=.785:',round(stats.binom.cdf(k,N,.785),4),'p=.70',round(stats.binom.cdf(k,N,.70),3),'p=.60',round(stats.binom.cdf(k,N,.60),3))

import sys;sys.path.insert(0,'.')
import charge as c, pandas as pd, numpy as np
D={}
for f in c.files():
    k=c.preset(f).split()[0]
    if k in('45','48','50') and not (k=='45' and '4eb81' not in f): D[k]=c.trades(f)
def pf(x): return x[x>0].sum()/-x[x<0].sum()
t=D['48'];m=lambda ts:ts.dt.hour*60+ts.dt.minute
fast=t.bars<=1
for nm,x in [('sans trades <=1 barre',t[~fast]),('seulement <=1 barre',t[fast]),('sans entrees nuit 0:20-8:00',t[~((m(t.entry)>=20)&(m(t.entry)<=480))]),('entrees jour seulement 8-22:15',t[(m(t.entry)>480)])]:
    print(nm,len(x),round((x.pnl>0).mean()*100,1),round(pf(x.pnl),2),x.pnl.sum())
x=t[~fast]
for tk in (2,4,8): p=x.pnl-tk*1;print('sans rapides, slip',tk,round(p.sum()),round(pf(p),2))
# 3e an lissage des rapides
y=t[t.entry>='2025-10-24'];print('Y3 rapides',(y.bars<=1).sum(),y[y.bars<=1].pnl.sum(),'reste',y[y.bars>1].pnl.sum(),pf(y[y.bars>1].pnl))
# premier 1000$ -> 3 micros: nb trades pour atteindre +1000 from start, rolling
eq=t.pnl.cumsum();print('trades to +1000 from start',(eq>=1000).values.argmax()+1)
# tendance Y3 : win rate 3 derniers mois (juil-oct 2026)
z=t[t.entry>='2026-07-01'];print('Jul-Oct26',len(z),round((z.pnl>0).mean()*100,1),round(pf(z.pnl),2),z.pnl.sum(),z.groupby('side').pnl.agg(['count','sum']).to_dict())
for k in['45','48']:
    z=D[k][D[k].entry>='2026-07-01'];print(k,'Jul-Oct26',len(z),round((z.pnl>0).mean()*100,1),round(pf(z.pnl),2),z.pnl.sum())
# trend slope of quarterly win among completed quarters
# bootstrap CI of winrate Y3 & last 100
rng=np.random.default_rng(2);y=t[t.entry>='2025-10-24'].pnl.values
b=[(lambda s:(s>0).mean()*100)(y[rng.integers(0,len(y),len(y))]) for _ in range(5000)];print('Y3 win CI',np.percentile(b,[2.5,97.5]))
b=[pf(pd.Series(y[rng.integers(0,len(y),len(y))])) for _ in range(5000)];print('Y3 PF CI',np.percentile(b,[2.5,97.5]))
# test 2 ans vs 3e an win rate difference
o=t[t.entry<'2025-10-24'].pnl.values
print('diff win o-y',(o>0).mean()-(y>0).mean())
from scipy import stats
print(stats.fisher_exact([[ (o>0).sum(),(o<=0).sum()],[(y>0).sum(),(y<=0).sum()]]))

import sys; sys.path.insert(0,"/Users/jeremk/Ephore/on-va-se-le-tenter/KAIROS/recherche/tv3ans")
from base import *
a=load(); m=a[a.sym=='MNQ']
def dd(x):
    e=np.concatenate([[0],x.sort_values('sortie_t').pnl.cumsum().values]); return (np.maximum.accumulate(e)-e).max()
def st(x): return dict(n=len(x),gag=round(100*(x.pnl>0).mean(),1),Rm=round(x.pnl_R.mean(),3),PF=round(pf(x.pnl),2),net=x.pnl.sum(),dd=dd(x))
for p in ['38','39','40','42']:
    for lab,mk in [('base',m.heure>=0),('sans8-10',~m.heure.isin([8,9]))]:
        x=m[(m.pre==p)&mk]; print(p,lab,st(x))
        q=x.groupby('trim').pnl.sum(); print('   trimestres >0:',(q>0).sum(),'/',len(q),' net sans meilleur trim:',q.sum()-q.max(), 'dernier 4 trim', q.tail(4).sum())
        mm=x.entree_t.dt.to_period('M'); 
for p in ['40']:
    x=m[(m.pre==p)&~m.heure.isin([8,9])]
    for y in ['2023-24','2024-25','2025-26']:
        print(y,st(x[x.annee==y]))
    for s in 'LS': print(s,st(x[x.sens==s]))

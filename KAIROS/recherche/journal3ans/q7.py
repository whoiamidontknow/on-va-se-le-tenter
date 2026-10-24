import sys; sys.path.insert(0,"/Users/jeremk/Ephore/on-va-se-le-tenter/KAIROS/recherche/journal3ans")
from feat import *
d=prep(); dv=d[d.dev].copy()
b=(dv.dA60==1)&(dv.dA240==1)
for nm,m in [('tout',dv.F.notna()),('b',b),('b&e<=0.9',b&(dv.eA<=.9)),('b&e<=0',b&(dv.eA<=0)),('b&e>1.8',b&(dv.eA>1.8)),('~b',~b)]:
    q=dv[m]; print(nm,len(q),'durée',q.barres.value_counts(normalize=True).sort_index().round(3).head(9).to_dict())
    print('   mfeR moy %.2f maeR moy %.2f ; mae/R<-0.2 part %.2f'%(q.mfeR.mean(),q.maeR.mean(),(q.maeR>-0.1).mean()), 'pnl/R moy %.2f'%q.rr.mean())
# MAE tres faible = entrée en dessous du marché ?

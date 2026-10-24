import sys; sys.path.insert(0,"/Users/jeremk/Ephore/on-va-se-le-tenter/Strat-Botting/recherche/journal3ans")
from feat import *
d=prep(); dv=d[d.dev].copy(); dv['min']=dv.entree_t.dt.minute
for c in ['dA60','dA240','dA15','dA5','dA1','dA1D','tA60','tA240']:
    print(c); print(dv.groupby([c,'min']).apply(lambda q: pd.Series(stats(q))).round(2).unstack(0)[['win','n']].to_string())
dv['h4']=((dv.entree_t.dt.hour)%4)
print(dv[dv.dA240==1].groupby('h4').apply(lambda q: pd.Series(stats(q))).round(2))
print(dv[dv.dA240==0].groupby('h4').apply(lambda q: pd.Series(stats(q))).round(2))

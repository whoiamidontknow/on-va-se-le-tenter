import sys; sys.path.insert(0,"/Users/jeremk/Ephore/on-va-se-le-tenter/Strat-Botting/recherche/tv3ans")
from base import *
import numpy as np
a=load(); m=a[a.sym=='MNQ']
t=m[(m.pre=='40')&m.raison.str.startswith('Temps')]
b=m[m.pre=='42'].set_index(['entree_t','sens'])
j=t.join(b[['raison','pnl','barres']].add_suffix('_42'),on=['entree_t','sens']).dropna(subset=['pnl_42'])
d1=j.pnl_42-j.pnl
d2=np.where(j.pnl>0,0,j.pnl_42-j.pnl)
for n,d in [('tout garder',d1),('garder si perte',d2)]:
    d=pd.Series(np.asarray(d)); print(n,'somme',d.sum(),'ET de la somme',d.std()*np.sqrt(len(d)),'moy/trade',d.mean())
# 38 idem
t=m[(m.pre=='38')&m.raison.str.startswith('Temps')]
j=t.join(b[['raison','pnl','barres']].add_suffix('_42'),on=['entree_t','sens']).dropna(subset=['pnl_42'])
for n,d in [('38 tout garder',j.pnl_42-j.pnl),('38 garder si perte',np.where(j.pnl>0,0,j.pnl_42-j.pnl))]:
    d=pd.Series(np.asarray(d)); print(n,len(d),d.sum(),d.std()*np.sqrt(len(d)))
j['a']=j.annee
print(j.groupby('annee',observed=True).apply(lambda d:pd.Series({'p8':d.pnl.sum(),'inv':d[d.pnl>0].pnl.sum()+d[d.pnl<=0].pnl_42.sum()})))

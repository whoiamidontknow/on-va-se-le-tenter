import sys; sys.path.insert(0,"/Users/jeremk/Ephore/on-va-se-le-tenter/KAIROS/recherche/tv3ans")
from base import *
a=load(); m=a[a.sym=='MNQ']
t=m[(m.pre=='40')&m.raison.str.startswith('Temps')]
b=m[m.pre=='42'].set_index(['entree_t','sens'])
j=t.join(b[['raison','pnl','barres']].add_suffix('_42'),on=['entree_t','sens']).dropna(subset=['pnl_42'])
j['f']=j.mfe_R
for lo,hi in [(0,.4),(.4,.7),(.7,.9),(.9,9)]:
    k=j[(j.f>=lo)&(j.f<hi)]
    print(f'MFE {lo}-{hi} R: n={len(k)} pnl8={k.pnl.sum():.0f} pnl_sans_limite={k.pnl_42.sum():.0f} Obj={k.raison_42.str.startswith("Obj").sum()} Stop={k.raison_42.str.startswith("Stop").sum()} Fin={k.raison_42.str.startswith("Fin").sum()}')
# sens
for s in 'LS':
    k=j[j.sens==s]; print(s,len(k),k.pnl.sum(),k.pnl_42.sum())
# regle "garder si perte a 8, sortir si gain" vs actuelle
perte=j[j.pnl<=0]; gain=j[j.pnl>0]
print('regle inverse (sortir si gain, garder si perte):',gain.pnl.sum()+perte.pnl_42.sum(),'vs 8 bougies',j.pnl.sum(),'vs tout garder',j.pnl_42.sum())
print('annee', j.groupby('annee',observed=True).apply(lambda d:pd.Series({'n':len(d),'p8':d.pnl.sum(),'p42':d.pnl_42.sum(),'inverse':d[d.pnl>0].pnl.sum()+d[d.pnl<=0].pnl_42.sum()})))
# distribution des temps ratés vs frais

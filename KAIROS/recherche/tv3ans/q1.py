import sys; sys.path.insert(0,"/Users/jeremk/ERGON/on-va-se-le-tenter/KAIROS/recherche/tv3ans")
from base import *
a=load(); m=a[a.sym=='MNQ']
print("== Q1 sorties au temps")
for p in ['38','39','40']:
    x=m[(m.pre==p)]; t=x[x.raison.str.startswith('Temps')]; n=len(t); tr=t.dropna(subset=['R'])
    f=tr.mfe_R/TPR[p]
    print(p,'n tot',len(x),'temps',n,'avec R',len(tr),'part des trades',round(n/len(x),3),
      'gagnants au temps',round((t.pnl>0).mean(),3),'pnl moyen $',round(t.pnl.mean(),1),'net',t.pnl.sum(),
      '| >=70%',round((f>=.7).mean(),3),'>=80%',round((f>=.8).mean(),3),'>=90%',round((f>=.9).mean(),3),
      '| dont perdants parmi >=70%',round(((f>=.7)&(tr.pnl<=0)).sum()/max((f>=.7).sum(),1),3),
      '| pnl_R moyen',round(tr.pnl_R.mean(),3),'mfe_R moyen',round(tr.mfe_R.mean(),3))
# experience naturelle : memes entrees dans 42 (pas de sortie temps)
print("== 40 temps vs 42 meme entree")
for p0,p1 in [('40','42'),('38','42')]:
    t=m[(m.pre==p0)&m.raison.str.startswith('Temps')]
    b=m[m.pre==p1].set_index(['entree_t','sens'])
    j=t.join(b[['raison','pnl','barres','sortie_t']].add_suffix('_42'),on=['entree_t','sens'])
    print(p0,p1,'temps',len(t),'meme entree dans 42',j.pnl_42.notna().sum())
    jj=j.dropna(subset=['pnl_42'])
    print(' pnl 8 bougies (somme)',jj.pnl.sum(),' pnl 42 (somme)',jj.pnl_42.sum())
    print(jj.raison_42.value_counts().to_dict())
    print(' duree 42: quantiles',jj.barres_42.quantile([.25,.5,.75]).to_dict())
    gain=jj[jj.pnl>0]; print(' trades en gain a 8 bougies:',len(gain),'pnl8',gain.pnl.sum(),'pnl42',gain.pnl_42.sum(),gain.raison_42.value_counts().to_dict())
    per=jj[jj.pnl<=0]; print(' en perte a 8:',len(per),'pnl8',per.pnl.sum(),'pnl42',per.pnl_42.sum(),per.raison_42.value_counts().to_dict())
    for N in (12,16):
        fin=jj.barres_42<=N
        print(f' {N} bougies: finis avant (exact) {fin.sum()}/{len(jj)}, pnl exact de ceux-ci {jj[fin].pnl_42.sum()}, restants {jj[~fin].shape[0]} dont pnl final 42 {jj[~fin].pnl_42.sum()} vs pnl a 8 {jj[~fin].pnl.sum()}')

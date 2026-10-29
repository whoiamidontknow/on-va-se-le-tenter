import sys; sys.path.insert(0,"/Users/jeremk/ERGON/on-va-se-le-tenter/KAIROS/recherche/journal3ans"); sys.path.insert(0,"/Users/jeremk/ERGON/on-va-se-le-tenter/KAIROS/moteur")
from feat import *; from filtres import *; from regles_figees import *
import registre
d=prep()
def ddm(p):
    e=np.concatenate([[0],np.cumsum(p)]); return float((np.maximum.accumulate(e)-e).max())
def add(rec,q,pt,verd,nvar,pref=''):
    s=stats(q)
    print(registre.ajouter_test(dict(date='2026-10-17 21:00',agent='JR3',famille='journal_3ans',recette=rec,marche='MNQ1!',ut_signal=15,ut_entree=15,
      periode_debut='2023-10-24',periode_fin='2026-10-16',echantillon='tv_journal_3ans',n_variantes_testees=nvar,n_trades=s['n'],
      pct_gagnants=round(s['win'],1),r_moyen=round(q.rr.mean(),3),pf=round(s['pf'],2),gain_net_usd=int(s['net']),dd_max_usd=int(ddm(q.pnl.values)),
      p_tradeify=pt,verdict=verd,fichier='recherche/journal3ans/RESULTATS.md')))
add('Journal 3 ans, 2 micros : Dashator 60 min ET 240 min dans le sens du trade + écart HA-EMA50 <= 0,6 ATR dans le sens (tous déclencheurs, stop 2 ATR, 1R, 8 bougies). Chiffres sur le journal (1 position à la fois, ~20 % de trades en moins que le vrai run)',
 d[R_star(d)],0.956,'RECOMMANDÉ. Dev 77,3 %/PF 5,3 (348) ; test jamais vu 76,9 %/PF 5,47 (143) contre 44 : 56,9 %/1,33 ; permutation p=0,002 ; 4 semestres 75/75/80/80 % ; 3 clés Pine nouvelles ; n total journal 491 (vrai run attendu ~590, limite basse du seuil 500) ; à confirmer par un vrai run TradingView (risque de fuite non exclu)',172086)
add('Journal 3 ans, 2 micros : Dashator 60 ET 240 dans le sens + écart HA-EMA50 <= 1,5 ATR (variante volume)',d[R_alt(d)],0.956,'ALTERNATIVE volume : dev 65,9 %/PF 2,26 ; test 66,1 %/PF 2,39 ; 1 337 trades journal ; net x1,7 mais % gagnants -11 pts ; DD 2 990 $',172086)
add('Journal 3 ans, 2 micros : filtre du préréglage 44 rejoué sur le journal (référence, écart journal/vrai export chiffré)',d.loc[f44(d).index],0.770,'Référence : journal 869 trades 56,3 %/PF 1,31 contre vrai 44 : 1 049 trades 57,0 %/PF 1,35 ; 950 trades communs avec le vrai 40 à issue identique à 100 % ; seulement 10 % des trades de R* sont aussi dans le 44',1)

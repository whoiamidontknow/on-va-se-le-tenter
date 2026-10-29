import sys; sys.path.insert(0,"/Users/jeremk/ERGON/on-va-se-le-tenter/KAIROS/recherche/journal3ans"); sys.path.insert(0,"/Users/jeremk/ERGON/on-va-se-le-tenter/KAIROS/propfirm")
from feat import *; from filtres import *; from regles_figees import *
import simulateur as S, warnings; warnings.filterwarnings('ignore')
d=prep(); R=S.charge_regles()['tradeify_50k_select_flex']
def to_tp(q,scale=0.5):
    return pd.DataFrame({'entree_t':q.entree_t.values,'sortie_t':q.sortie_t.values,'sens':'x','pnl_usd':q.pnl.values*scale,'mae_usd':q.mae.values*scale,'mfe_usd':q.mfe.values*scale,
       'risque_usd':(q.Rusd.values*scale) if 'Rusd' in q else np.nan})
r40=trades(D+'Stratégie_V1_CME_MINI_MNQ1!_2026-10-17_a413e.xlsx'); r40['h']=r40.entree_t.dt.hour; r44=r40[~r40.h.isin([8,9])]
sets={'R* (journal)':d[R_star(d)],'Alt eA<=1.5 (journal)':d[R_alt(d)],'filtre 44 (journal)':d.loc[f44(d).index],'44 réel (40 sans 8-10h)':r44}
for per,fn in [('TEST',lambda x:x.entree_t>=CUT),('3 ANS',lambda x:x.entree_t>pd.Timestamp('2000-01-01'))]:
  for nm,q in sets.items():
    q=q[fn(q)]; sc=0.25 if nm.startswith('44 réel') else 0.5   # réel 4 micros -> 1 micro
    tp=to_tp(q,sc)
    out=[]
    for meth in ['bootstrap','chronologique']:
        r=S.monte_carlo(tp,R,2,instrument='micro',methode=meth,n_sim=2000)
        out.append('%s: P(réuss)=%.1f%% P(1er payout)=%.1f%% VE=%.0f$ délai méd=%s j'%(meth[:5],100*r['p_reussite'],100*r['p_1er_payout'],r.get('valeur_esperee_usd',np.nan),r.get('delai_median_jours')))
    print(per,nm,'n=',len(q),' | '.join(out))

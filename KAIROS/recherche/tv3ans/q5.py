import sys; sys.path.insert(0,"/Users/jeremk/Ephore/on-va-se-le-tenter/Strat-Botting/recherche/tv3ans"); sys.path.insert(0,"/Users/jeremk/Ephore/on-va-se-le-tenter/Strat-Botting/propfirm")
from base import *
import simulateur as S, json, time, warnings; warnings.filterwarnings('ignore')
COMM=1.30
a=load(); m=a[a.sym=='MNQ']
R=S.charge_regles()['tradeify_50k_select_flex']
def micro(x):
    n=x.qte
    return pd.DataFrame({'entree_t':x.entree_t.values,'sortie_t':x.sortie_t.values,'sens':x.sens.values,
      'pnl_usd':((x.pnl+x.comm)/n-COMM).values,'mae_usd':((x.mae+x.comm)/n-COMM).values,'mfe_usd':((x.mfe)/n-COMM).values})
AN={'2023-24':('2023-10-25','2024-10-24'),'2024-25':('2024-10-25','2025-10-24'),'2025-26':('2025-10-25','2026-10-16')}
cfg={'40':m[m.pre=='40'],'38':m[m.pre=='38'],'40 sans 8-10h':m[(m.pre=='40')&~m.heure.isin([8,9])],'38 sans 8-10h':m[(m.pre=='38')&~m.heure.isin([8,9])]}
res=[]
TAILLES=[1,2,3,4,5,6,8,10]
t0=time.time()
for k,x in cfg.items():
    tm=micro(x)
    for meth in ['bootstrap','chronologique']:
        for c in TAILLES:
            r=S.monte_carlo(tm,R,c,methode=meth,n_sim=1500,ordre='prudent')
            res.append(dict(cfg=k,per='tout',meth=meth,c=c,p=r['p_reussite'],p1=r['p_1er_payout'],ve=r['valeur_esperee_usd'],delai=r['delai_median_jours'],nuit=r['pct_traverse_fermeture'],pe=r['p_echec'],cens=r.get('p_censure')))
    for an,(d,f) in AN.items():
        for c in [2,3,4,6]:
            r=S.monte_carlo(tm,R,c,methode='chronologique',ordre='prudent',debut=d,fin=f)
            res.append(dict(cfg=k,per=an,meth='chrono',c=c,p=r['p_reussite'],p1=r['p_1er_payout'],ve=r['valeur_esperee_usd'],delai=r['delai_median_jours'],nuit=r['pct_traverse_fermeture'],pe=r['p_echec'],cens=r.get('p_censure')))
    print(k,time.time()-t0,flush=True)
pd.DataFrame(res).to_csv('prop.csv',index=False)

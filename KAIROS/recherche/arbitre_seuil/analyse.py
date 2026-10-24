import glob, os, sys, re
import numpy as np, pandas as pd
def _md(self,index=True):
    d=self.reset_index() if index else self
    h='| '+' | '.join(map(str,d.columns))+' |\n|'+'---|'*len(d.columns)+'\n'
    return h+'\n'.join('| '+' | '.join(str(v) for v in r)+' |' for r in d.values)
pd.DataFrame.to_markdown=_md
sys.path.insert(0,'/Users/jeremk/Ephore/on-va-se-le-tenter/KAIROS/propfirm')
import simulateur as S
D=os.path.expanduser('~/Ephore/KAIROS-data/slcourtoupas/58-68')
KS=[0,0.01,0.02,0.03,0.04,0.05]
def load(f):
    T=pd.read_excel(f,'Trades')
    en=T[T['Type'].str.startswith('Entrer')].set_index('Numéro de trade'); ex=T[T['Type'].str.startswith('Sortir')].set_index('Numéro de trade')
    q=ex['Taille (qté)'].astype(float)
    t=pd.DataFrame({'entree_t':pd.to_datetime(en['Date et heure']),'sortie_t':pd.to_datetime(ex['Date et heure']),'sens':en['Type'].str.replace('Entrer ',''),
      'pnl_usd':ex['P&L net USD']/q,'mae_usd':ex['Excursion adverse USD']/q,'mfe_usd':ex['Excursion favorable USD']/q,'sortie':ex['Signal'],'pnl2':ex['P&L net USD']}).dropna(subset=['pnl_usd']).reset_index(drop=True)
    return t
data={}
for f in glob.glob(D+'/*.xlsx'):
    P=pd.read_excel(f,'Propriétés'); P=dict(zip(P['name'].astype(str),P['value'].astype(str)))
    m=re.search(r'≥ ([\d,]+) ATR',P.get('Préréglage',''));k=float(m.group(1).replace(',','.')) if m else 0.0
    if k in KS: data[k]=load(f)
def stats(t):
    p=t.pnl2.values; n=len(p); g=p[p>0].sum(); l=-p[p<0].sum()
    eq=np.cumsum(p[np.argsort(t.sortie_t.values,kind='stable')]); dd=(np.maximum.accumulate(np.r_[0,eq])[1:]-eq).max()
    s=t.set_index('sortie_t').pnl2
    mo=(t.sortie_t.max()-t.sortie_t.min()).days/30.44
    return dict(n=n,tr_mois=n/mo,gagn=100*(p>0).mean(),PF=g/l,net=p.sum(),net_mois=p.sum()/mo,dd_max=dd,
      pire_jour=s.resample('D').sum().min(),pire_sem=s.resample('W').sum().min(),pire_mois=s.resample('MS').sum().min())
rows={k:stats(t) for k,t in data.items()}
A=pd.DataFrame(rows).T.sort_index(); print(A.round(2).to_string())
out=['## 1. Statistiques globales (2 micros, 25/10/2023-16/10/2026)\n',A.round(2).to_markdown(),'']
Y=pd.DataFrame({k:t.groupby(t.sortie_t.dt.year).pnl2.sum() for k,t in data.items()});out+=['## Par année (net $)\n',Y.round(0).to_markdown(),'']
Qd=pd.DataFrame({k:t.groupby(t.sortie_t.dt.to_period('Q')).pnl2.sum() for k,t in data.items()});Qd.index=Qd.index.astype(str);out+=['## Par trimestre (net $)\n',Qd.round(0).to_markdown(),'']
rec={}
for k,t in data.items():
    r=t[t.sortie_t>='2026-07-01'];p=r.pnl2
    rec[k]=dict(n=len(r),gagn=100*(p>0).mean(),PF=p[p>0].sum()/-p[p<0].sum(),net=p.sum())
out+=['## Depuis 01/07/2026\n',pd.DataFrame(rec).T.round(2).to_markdown(),'']
# sorties
ex=pd.DataFrame({k:t.sortie.value_counts() for k,t in data.items()}).fillna(0).astype(int);out+=['## Raisons de sortie\n',ex.to_markdown(),'']
# trades retirés par cran
base=data[0.0];key=lambda t:t.entree_t.astype(str)+t.sens
sets={k:set(key(t)) for k,t in data.items()}
rows=[];rem={}
for a,b in zip(KS[:-1],KS[1:]):
    ta=data[a];tb=data[b];ka=sets[a];kb=sets[b]
    r=ta[key(ta).isin(ka-kb)];ad=tb[key(tb).isin(kb-ka)]
    rem[b]=r
    rows.append(dict(cran=f'{a}->{b}',retires=len(r),net_retires=r.pnl2.sum(),gagn_retires_pct=100*(r.pnl2>0).mean() if len(r) else np.nan,moy=r.pnl2.mean() if len(r) else np.nan,
       stops=(r.sortie.str.contains('Stop|SL',case=False)).sum(),ajoutes=len(ad),net_ajoutes=ad.pnl2.sum()))
# cumul vs 0
for k in KS[1:]:
    r=base[key(base).isin(sets[0.0]-sets[k])];ad=data[k][key(data[k]).isin(sets[k]-sets[0.0])]
    rows.append(dict(cran=f'0->{k} cumul',retires=len(r),net_retires=r.pnl2.sum(),gagn_retires_pct=100*(r.pnl2>0).mean(),moy=r.pnl2.mean(),stops=(r.sortie.str.contains('Stop|SL',case=False)).sum(),ajoutes=len(ad),net_ajoutes=ad.pnl2.sum()))
R=pd.DataFrame(rows);out+=['## 2. Trades retirés\n',R.round(1).to_markdown(index=False),'']
print(R.round(1).to_string()); print(base.sortie.unique())
# bootstrap : rééchantillonne les trades du 56 (apparié), diff net / PF pour k vs 0
rng=np.random.default_rng(1);B=[]
bp=base.pnl2.values;kb=key(base)
for k in KS[1:]:
    keep=kb.isin(sets[k]).values; N=len(bp);dn=[];dpf=[]
    for _ in range(5000):
        i=rng.integers(0,N,N);p=bp[i];kk=keep[i];q=p[kk]
        dn.append(q.sum()-p.sum());dpf.append(q[q>0].sum()/-q[q<0].sum()-p[p>0].sum()/-p[p<0].sum())
    B.append(dict(k=k,d_net_moy=np.mean(dn),ic95_net=f'[{np.percentile(dn,2.5):.0f};{np.percentile(dn,97.5):.0f}]',p_net_pos=np.mean(np.array(dn)>0),d_PF=np.mean(dpf),ic95_PF=f'[{np.percentile(dpf,2.5):.3f};{np.percentile(dpf,97.5):.3f}]',p_PF_pos=np.mean(np.array(dpf)>0)))
Bt=pd.DataFrame(B);out+=['## Bootstrap apparié (5000, trades du 56 rééchantillonnés ; k vs 56)\n',Bt.round(3).to_markdown(index=False),'']
print(Bt.to_string())
# simulateur
R_=S.charge_regles();KW=dict(max_jours_eval=250,max_jours_funded=250,max_payouts=5,bloc_jours=5,n_sim=3000,ordre='heuristique')
L=[]
for k,t in data.items():
    tt=t[['entree_t','sortie_t','sens','pnl_usd','mae_usd','mfe_usd']].copy()
    tt['entree_t']=tt.entree_t.dt.tz_localize('Europe/Paris',ambiguous='NaT',nonexistent='shift_forward');tt['sortie_t']=tt.sortie_t.dt.tz_localize('Europe/Paris',ambiguous='NaT',nonexistent='shift_forward');tt=tt.dropna()
    for c in (2,3):
        r=S.monte_carlo(tt,R_['tradeify_50k_select_flex'],c,**KW)
        L.append(dict(k=k,micros=c,p_reussite=r['p_reussite'],delai_j=r['delai_median_jours'],p_1er_payout=r['p_1er_payout'],p_3_payouts=r['p_3_payouts'],ve=r.get('valeur_esperee_usd')))
Sm=pd.DataFrame(L);out+=['## Simulateur Tradeify 50k Select Flex (bootstrap blocs 5 j, 3000 sims)\n',Sm.round(3).to_markdown(index=False),'']
print(Sm.to_string())
open('tables.md','w').write('\n'.join(out))

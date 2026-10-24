import pandas as pd,numpy as np
P='/private/tmp/claude-501/-Users-jeremk-Ephore/5255c912-f232-4044-9510-5af2888db584/scratchpad/t.pkl'
TPR={'25':1,'38':1,'39':1.5,'40':1,'42':1}
VP={'MNQ':2.0,'MES':5.0}
def load():
    a=pd.read_pickle(P)
    a['Rp']=np.nan
    ok=a.pre.isin(TPR)&a.raison.isin(['Stop L','Stop S','Obj L','Obj S'])
    d=(a.px_s-a.px_e).abs()
    a.loc[ok,'Rp']=np.where(a.loc[ok,'raison'].str.startswith('Stop'),d[ok],d[ok]/a.loc[ok,'pre'].map(TPR))
    # R par instant d'entree (identique d'un preset a l'autre, meme ATR)
    mp=a[ok].groupby(['sym','entree_t']).Rp.median()
    a['R']=[mp.get((s,t),np.nan) for s,t in zip(a.sym,a.entree_t)]
    # secours : plus proche voisin dans le temps (moins de 1 jour) 
    for s in ['MNQ','MES']:
        ref=mp.loc[s].reset_index().sort_values('entree_t')
        idx=a.index[(a.sym==s)&a.R.isna()]
        if len(idx):
            q=a.loc[idx,['entree_t']].sort_values('entree_t')
            mm=pd.merge_asof(q.reset_index(),ref.rename(columns={'Rp':'Rn','entree_t':'t2'}).assign(entree_t=lambda x:x.t2),on='entree_t',direction='nearest',tolerance=pd.Timedelta('3h'))
            a.loc[mm['index'],'Rn']=mm['Rn'].values
    a['R_est']=a.R.isna()
    a['R']=a.R.fillna(a.get('Rn'))
    a['R_usd']=a.R*VP_col(a)*a.qte
    a['mfe_R']=a.mfe/a.R_usd; a['mae_R']=-a.mae/a.R_usd; a['pnl_R']=a.pnl/a.R_usd
    a['annee']=pd.cut(a.entree_t,[pd.Timestamp('2023-10-01'),pd.Timestamp('2024-10-25'),pd.Timestamp('2025-10-25'),pd.Timestamp('2026-12-31')],labels=['2023-24','2024-25','2025-26'])
    a['trim']=a.entree_t.dt.to_period('Q').astype(str)
    a['heure']=a.entree_t.dt.hour; a['jour']=a.entree_t.dt.dayofweek
    return a
def VP_col(a): return a.sym.map(VP)
def pf(x):
    g=x[x>0].sum(); l=-x[x<0].sum(); return g/l if l>0 else np.nan

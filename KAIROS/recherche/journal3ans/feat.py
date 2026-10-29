import sys; sys.path.insert(0,"/Users/jeremk/ERGON/on-va-se-le-tenter/KAIROS/recherche/journal3ans")
from charge import *
SC='/private/tmp/claude-501/-Users-jeremk-Ephore/5255c912-f232-4044-9510-5af2888db584/scratchpad/'
CUT=pd.Timestamp('2025-10-24')
def prep():
    d=pd.read_pickle(SC+'j.pkl').copy()
    s=d.sens
    d['Fa']=d.F*s; d['Ia']=d.I*s
    d['feu_dir']=np.where(s==1,d.feuL,d.feuS); d['feu_opp']=np.where(s==1,d.feuS,d.feuL)
    d['feu_net']=d.feu_dir-d.feu_opp
    for u in ['3','5','15','60','240','1D']:
        d['tA'+u]=np.where(s==1,d['t'+u],1-d['t'+u]).astype(float); d.loc[d['t'+u].isna(),'tA'+u]=np.nan
    for u in ['1','5','15','60','240','1D']:
        d['dA'+u]=np.where(s==1,d['d'+u],1-d['d'+u]).astype(float); d.loc[d['d'+u].isna(),'dA'+u]=np.nan
    d['nT']=d[[c for c in d if c.startswith('tA')]].sum(axis=1,min_count=1)
    d['nD']=d[[c for c in d if c.startswith('dA')]].sum(axis=1,min_count=1)
    d['diA']=d.di*s; d['eA']=d.e*s; d['cA']=d.c*s
    d['zz']=d.z.clip(upper=9.9)
    for k in 'FMHTNCD': d['g_'+k]=d.trig.str.contains(k).astype(int)
    d['nTrig']=d.trig.str.len()
    d['long']=(s==1).astype(int)
    d['hm']=d.entree_t.dt.hour+d.entree_t.dt.minute/60
    d['year']=np.where(d.entree_t<pd.Timestamp('2024-10-24'),1,np.where(d.entree_t<pd.Timestamp('2025-10-24'),2,3))
    d['dev']=d.entree_t<CUT
    # R-multiple
    d['rr']=d.pnl/d.Rusd
    d['mfeR']=d.mfe/d.Rusd; d['maeR']=d.mae/d.Rusd
    return d
FEATS=['Fa','Ia','feu_dir','feu_opp','feu_net','tA3','tA5','tA15','tA60','tA240','tA1D','dA1','dA5','dA15','dA60','dA240','dA1D','nT','nD',
 's15','s60','s240','s1D','adx','diA','zz','eA','v','cA','g_F','g_M','g_H','g_T','g_N','g_C','g_D','nTrig','long','hm','dow']

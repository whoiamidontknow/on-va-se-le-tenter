import sys; sys.path.insert(0,"/Users/jeremk/Ephore/on-va-se-le-tenter/Strat-Botting/recherche/journal3ans")
from feat import *
import numpy as np
def conditions(d, feats=FEATS):
    """liste de (nom, masque) : seuils aux quantiles, >= et <=, ou == pour binaires."""
    C=[]
    for f in feats:
        x=d[f].values.astype(float); u=np.unique(x[~np.isnan(x)])
        if len(u)<=1: continue
        if len(u)<=2:
            for v in u: C.append((f'{f}=={v:g}',np.nan_to_num(x==v).astype(bool)))
            continue
        if len(u)<=12: th=u
        else: th=np.unique(np.quantile(x[~np.isnan(x)],np.arange(0.1,0.95,0.1)).round(2))
        for t in th:
            m1=np.nan_to_num(x>=t,nan=0).astype(bool); m2=np.nan_to_num(x<=t,nan=0).astype(bool)
            if 0.03<m1.mean()<0.97: C.append((f'{f}>={t:g}',m1))
            if 0.03<m2.mean()<0.97: C.append((f'{f}<={t:g}',m2))
    return C
def wilson(w,n,z=1.28):
    if n==0: return 0
    p=w/n; return (p+z*z/(2*n)-z*np.sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n)
def beam(C,pnl,win,nmin,depth=4,width=150,score='wilson',pfmin=1.0):
    pos=np.where(pnl>0,pnl,0.0); neg=np.where(pnl<0,-pnl,0.0)
    def sc(m):
        n=m.sum()
        if n<nmin: return -1,0
        w=win[m].sum(); l=neg[m].sum(); pf=pos[m].sum()/l if l>0 else 9
        if pf<pfmin: return -1,pf
        return (wilson(w,n) if score=='wilson' else (pf if score=='pf' else pnl[m].sum())),pf
    N=len(C); tried=0
    level=[((),np.ones(len(pnl),bool),0)]
    best=[]
    for dep in range(depth):
        cand={}
        for names,mask,_ in level:
            for i,(nm,cm) in enumerate(C):
                if i in names: continue
                key=tuple(sorted(names+(i,)))
                if key in cand: continue
                m=mask&cm; tried+=1
                s,pf=sc(m)
                if s>=0: cand[key]=(s,m)
        lv=sorted(cand.items(),key=lambda kv:-kv[1][0])[:width]
        level=[(k,v[1],v[0]) for k,v in lv]
        best+=[(k,s) for k,(s,_) in lv[:30]]
        if not level: break
    best.sort(key=lambda t:-t[1])
    return best,tried

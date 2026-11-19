"""Jalon A : contrôles du Relevé complet (OHLC contre le Relevé 5669, bits go contre la lecture k1/k4)."""
import os, sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'dataset'))
import numpy as np, pandas as pd
from releve_complet import charger as cc, TICK
from releve import charger as c5
for ins in ('MNQ','MES'):
    B=cc(ins); R=c5(ins,controle=False)
    # continuité entre blocs
    g=B.groupby('bloc').agg(t_first=('t','first'),t_last=('t','last'),dt_first=('dt','first')).sort_values('t_first')
    ecart=(g.t_first.shift(-1)-g.t_last)/pd.Timedelta(minutes=15)
    print(f'{ins} continuité : écart entre blocs = dt de la 1re fiche suivante : {(ecart.values[:-1]==g.dt_first.values[1:]).mean():.4%}')
    pos=pd.Series(np.arange(len(B)),index=B.t)
    H=B.h.values; L=B.l.values; O=B.o.values; C=B.c.values
    ok_o=ok_hl=ok_c=n=0; manque=0
    for r in R.itertuples(index=False):
        if r.t1 not in pos.index: manque+=1; continue
        i=pos[r.t1]
        if i+16>len(B): continue
        n+=1
        ok_o+= abs(O[i]-r.o1)<1e-6
        hh=np.array([getattr(r,f'h{k}') for k in range(1,17)]); ll=np.array([getattr(r,f'l{k}') for k in range(1,17)])
        ok_hl+= np.allclose((H[i:i+16]-r.o1)/TICK,hh) and np.allclose((L[i:i+16]-r.o1)/TICK,ll)
        ok_c+= abs((C[i+15]-r.o1)/TICK-r.c16)<1e-6
    print(f'{ins} OHLC contre Relevé 5669 : {n} bougies communes (absentes {manque}) ; ouverture {ok_o/n:.3%} ; 16 hauts et bas {ok_hl/n:.3%} ; clôture b16 {ok_c/n:.3%}')
    # bits go (bougie signal) contre go56k (ligne du relevé = bougie de remplissage suivante)
    nxt=B.t.shift(-1)
    G=pd.DataFrame({'t1':nxt,'goL':B.go_L,'goS':B.go_S}).dropna().set_index('t1')
    Ri=R.set_index('t1')
    com=Ri.index.intersection(G.index)
    for s,c in (('L','goL'),('S','goS')):
        a=G.loc[com,c].astype(int); b=Ri.loc[com,f'go56k_{s}'].astype(int)
        hors=G[(G[c]==1)&~G.index.isin(Ri.index)]
        print(f'   go_{s} : bits=1 {int(G[c].sum())}, go56k=1 {int(Ri[f"go56k_{s}"].sum())} ; sur bougies communes accord {(a==b).mean():.3%}, bits seuls {int(((a==1)&(b==0)).sum())}, go56k seuls {int(((a==0)&(b==1)).sum())} ; bits=1 hors relevé 5669 {len(hors)}')

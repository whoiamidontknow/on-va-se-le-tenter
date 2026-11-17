import pickle, pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
from sklearn.ensemble import HistGradientBoostingRegressor
S=pickle.load(open("rech2.pkl","rb")); PV={"MNQ1!":2.0,"MES1!":5.0}
def out(b,T,sym):
    com=2.5/(b.sl*PV[sym]); return np.where(b.mfeR>=T, T-com, b.R)
N={("MNQ1!","15 minutes","R16"):"MNQ15",("MES1!","15 minutes","R16"):"MES15",("MNQ1!","5 minutes","R16"):"MNQ5",("MNQ1!","2 minutes","R16"):"MNQ2",("MNQ1!","15 minutes","R48"):"MNQ15-48",("MNQ1!","5 minutes","R48"):"MNQ5-48"}
def se(x): return x.std()/np.sqrt(len(x)) if len(x)>1 else np.nan
def st(x): return f"n={len(x):4d} R {x.mean():+.3f}±{1.96*se(x):.3f} réussite {100*(x>0).mean():.0f}%"
print("=== Règles connues, reconstituées (objectif 0,667 R)")
for k,nm in N.items():
    b=S[k]; b["r67"]=out(b,2/3,k[0])
    if "R48" in k: b["h"]=b.t_in.dt.hour+b.t_in.dt.minute/60; b["y"]=b.t_in.dt.year
    gb=b[(b.b1>=0.025)&(b.b4>=0.025)&(b.e.round(1)<=0.6)]; ga=b[(a:=(b.a1>=0.025)&(b.a4>=0.025))&(b.e.round(1)<=0.6)]
    print(f"{nm:9s} GOD b: {st(gb.r67)} | GOD b 13-20h: {st(gb[(gb.h>=13)&(gb.h<20)].r67)} | GOD a: {st(ga.r67)} | a ET b: {st(b[a&(b.b1>=0.025)&(b.b4>=0.025)&(b.e.round(1)<=0.6)].r67)}")
print("\n=== GODLIKE a par année (r67)")
for k,nm in N.items():
    b=S[k]; ga=b[(b.a1>=0.025)&(b.a4>=0.025)&(b.e.round(1)<=0.6)]
    print(nm," | ".join(f"{y}: {u.r67.mean():+.2f}({len(u)})" for y,u in ga.groupby(ga.t_in.dt.year)))
print("\n=== Modèle (apprentissage ≤ 2024, test 2025-2026) : R moyen en test des trades les mieux notés")
F=["a1","a4","b1","b4","e","ha","v","adx","h","dir","ntr","nd","wdn"]+[f"d_{L}" for L in "FHTNCD"]
def prep(k):
    b=S[k].copy(); b["wdn"]=b.t_in.dt.dayofweek; b["ntr"]=b.tr.astype(str).map(lambda s:s.count("1")); b["nd"]=b.d.str.len()
    for L in "FHTNCD": b[f"d_{L}"]=b.d.str.contains(L).astype(int)
    b["h"]=b.t_in.dt.hour+b.t_in.dt.minute/60; b["yy"]=b.t_in.dt.year; return b
sets={"15 min (MNQ+MES)":[("MNQ1!","15 minutes","R16"),("MES1!","15 minutes","R16")],"MNQ 5 min":[("MNQ1!","5 minutes","R16")],"MNQ 15 min R48":[("MNQ1!","15 minutes","R48")],"MNQ 5 min R48":[("MNQ1!","5 minutes","R48")]}
for nm,ks in sets.items():
    d=pd.concat([prep(k).assign(sym=k[0]) for k in ks])
    for T in (2/3,1.5,4):
        d["yv"]=np.concatenate([out(prep(k),T,k[0]) for k in ks])
        tr=d[d.yy<=2024]; te=d[d.yy>=2025]
        res=[]
        for seed in range(5):
            m=HistGradientBoostingRegressor(max_depth=3,max_iter=150,learning_rate=0.03,min_samples_leaf=60,random_state=seed).fit(tr[F],tr.yv)
            res.append(m.predict(te[F]))
        te=te.assign(p=np.mean(res,0)); q=te.p.rank(pct=True)
        print(f"{nm:18s} obj {T:.2f}R | test tous {st(te.yv)} | top 20 % {st(te[q>0.8].yv)} | top 10 % {st(te[q>0.9].yv)} | bas 20 % {te[q<0.2].yv.mean():+.3f}")

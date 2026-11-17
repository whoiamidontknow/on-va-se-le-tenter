import pickle, pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
SF=pickle.load(open("sf.pkl","rb"))
def st(t): return f"n={len(t):3d} réussite {100*(t.pm>0).mean():3.0f}% {t.pm.mean():+6.1f}$/micro total {t.pm.sum():+6.0f}" if len(t) else "n=0"
for sym in ("MNQ1!","MES1!"):
    for mode in ("b","ancien"):
        b=SF[(sym,"15 minutes",mode)].copy(); g=b[b.god].copy()
        g["h"]=g.t_in.dt.hour+g.t_in.dt.minute/60; g["ho"]=g.t_out.dt.hour+g.t_out.dt.minute/60
        print(f"\n===== {sym} 15 min GODLIKE mode {mode} : {st(g)}")
        print("  sorties :"); 
        for e,u in g.groupby("ex"): print(f"    {e:22s} {st(u)}")
        print("  heure d'entrée (Paris) :")
        for lo,hi in ((0,8),(8,13),(13,15.5),(15.5,18),(18,19),(19,20),(20,21),(21,22.5)):
            u=g[(g.h>=lo)&(g.h<hi)]; fs=u[u.ex.str.contains("séance|fenêtre",case=False)]
            print(f"    {lo:>4}-{hi:<4} {st(u)} | dont coupés en fin de séance : {len(fs)} ({fs.pm.sum():+.0f}$)")
        print("  heures de sortie des 'Fin de séance' :", g[g.ex.str.contains('séance|fenêtre',case=False)].ho.round(2).value_counts().head(5).to_dict())
        print("  par année, entrées ≥ 20h :", {y:(len(u),round(u.pm.sum())) for y,u in g[g.h>=20].groupby(g.t_in.dt.year)})
        print("  par année, entrées < 20h :", {y:(len(u),round(u.pm.sum())) for y,u in g[g.h<20].groupby(g.t_in.dt.year)})

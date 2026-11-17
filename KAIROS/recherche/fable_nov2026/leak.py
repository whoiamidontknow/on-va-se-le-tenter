import pandas as pd, numpy as np, pickle, warnings; warnings.filterwarnings("ignore")
Y=pickle.load(open("yf.pkl","rb")); T=pickle.load(open("trades.pkl","rb"))
src=open("dash.py").read(); exec("def ha"+src.split("def ha",1)[1].split("res=[]")[0])
K=0.025
def part(sym,T_utc,tfmin,H,raw15):
    # bougie HTF en cours à l'instant T (clôture de la bougie signal), reconstruite avec les bougies 15 min
    return None
rows=[]
for sym in ("MES","MNQ"):
    h1=Y[(sym,"60m")].copy(); h1.index=h1.index.tz_convert("UTC"); H1=ha(h1); h4=agg4(h1); h4.index=pd.DatetimeIndex(h4.index).tz_convert("UTC"); H4=ha(h4)
    for tf in (15,5,2):
        t=T[(sym,tf,"3y")]; t=t[t.t_in>="2026-08-20"]
        for r in t.itertuples():
            Tu=pd.Timestamp(r.t_in).tz_localize("Europe/Paris").tz_convert("UTC"); sb=Tu-pd.Timedelta(minutes=tf)
            i1=H1.index.searchsorted(sb,side="right")-1; i4=H4.index.searchsorted(sb,side="right")-1
            if i1<20 or i4<20: continue
            d=1 if r.dir=="L" else -1
            g=lambda a,b: (d*a>=K) and (d*b>=K)
            rows.append(dict(sym=sym,tf=tf,t=r.t_in,dir=r.dir,god=bool(r.god),pm=r.pnl/2,
                 k0=g(H1.r.iloc[i1],H4.r.iloc[i4]), k1=g(H1.r.iloc[i1-1],H4.r.iloc[i4-1]),
                 s0=(d*H1.r.iloc[i1]>0) and (d*H4.r.iloc[i4]>0), s1=(d*H1.r.iloc[i1-1]>0) and (d*H4.r.iloc[i4-1]>0),
                 r1_0=d*H1.r.iloc[i1], r4_0=d*H4.r.iloc[i4], r1_1=d*H1.r.iloc[i1-1], r4_1=d*H4.r.iloc[i4-1]))
R=pd.DataFrame(rows)
print("Trades de l'historique (exports du 12/11) depuis le 20/08/2026 :",len(R))
print("\nL'étiquette GODLIKE de l'historique correspond à...")
for tf,g in R.groupby("tf"):
    print(f"  {tf:2d} min (n={len(g):4d}) : bougie 1 h/4 h CONTENANT le signal, valeur finale (k0) : {100*(g.god==g.k0).mean():5.1f} % d'accord | dernière bougie clôturée (k1) : {100*(g.god==g.k1).mean():5.1f} %")
print("\nFiltre d'entrée du préréglage 56 (Dashator 1 h et 4 h dans le sens du trade) : part des trades de l'historique où...")
for tf,g in R.groupby("tf"):
    print(f"  {tf:2d} min : la bougie finale contenant le signal va dans le sens du trade (k0) : {100*g.s0.mean():5.1f} % | la dernière bougie clôturée va dans ce sens (k1) : {100*g.s1.mean():5.1f} %")
print("\nRéussite des trades de l'historique selon que la bougie 1 h/4 h CLÔTURÉE AVANT le signal était déjà GODLIKE ou non")
for tf,g in R[R.god].groupby("tf"):
    a=g[g.k1]; b=g[~g.k1]
    print(f"  {tf:2d} min GODLIKE : déjà GODLIKE sur la bougie clôturée : n={len(a):4d} réussite {100*(a.pm>0).mean():4.1f} % {a.pm.mean():6.1f} $/tr | pas encore : n={len(b):4d} réussite {100*(b.pm>0).mean():4.1f} % {b.pm.mean():6.1f} $/tr")
pickle.dump(R,open("leak.pkl","wb"))
